#!/usr/bin/env python3
"""
Executor module for Tool Reader.
Executes task items and updates the task file.
Supports visual verification via invisible screenshots and Claude CLI.
"""

import re
from pathlib import Path
from typing import List, Optional, Callable
from dataclasses import dataclass

from parser import TaskFile, ChecklistItem, parse_task_file
from visual_verifier import (
    run_visual_verification,
    detect_app_type,
    AppType,
    VerificationResult
)


@dataclass
class ExecutionResult:
    """Result of executing a task item."""
    item: ChecklistItem
    success: bool
    message: str
    verification: Optional[VerificationResult] = None


def mark_item_complete(file_path: Path, line_number: int) -> bool:
    """
    Mark a checklist item as complete in the file.

    Args:
        file_path: Path to the task file
        line_number: Line number of the item to mark (1-indexed)

    Returns:
        True if successful, False otherwise
    """
    try:
        lines = file_path.read_text(encoding='utf-8').split('\n')

        if line_number < 1 or line_number > len(lines):
            return False

        line = lines[line_number - 1]

        # Replace [ ] with [x]
        new_line = re.sub(r'\[\s\]', '[x]', line, count=1)

        if new_line == line:
            return False  # No change made

        lines[line_number - 1] = new_line
        file_path.write_text('\n'.join(lines), encoding='utf-8')
        return True

    except Exception as e:
        print(f"Error marking item complete: {e}")
        return False


def execute_task_item(
    item: ChecklistItem,
    executor_fn: Optional[Callable[[str], bool]] = None
) -> ExecutionResult:
    """
    Execute a single task item.

    Args:
        item: The checklist item to execute
        executor_fn: Optional function to actually execute the task
                    If None, just marks as complete without execution

    Returns:
        ExecutionResult with success status and message
    """
    if item.completed:
        return ExecutionResult(
            item=item,
            success=True,
            message="Already completed"
        )

    try:
        if executor_fn:
            success = executor_fn(item.text)
            if not success:
                return ExecutionResult(
                    item=item,
                    success=False,
                    message="Execution failed"
                )

        return ExecutionResult(
            item=item,
            success=True,
            message="Completed successfully"
        )

    except Exception as e:
        return ExecutionResult(
            item=item,
            success=False,
            message=f"Error: {e}"
        )


def run_task(
    task: TaskFile,
    executor_fn: Optional[Callable[[str], bool]] = None,
    on_progress: Optional[Callable[[int, int, ChecklistItem], None]] = None
) -> List[ExecutionResult]:
    """
    Run all uncompleted items in a task.

    Args:
        task: The TaskFile to execute
        executor_fn: Function to execute each item
        on_progress: Callback for progress updates (current, total, item)

    Returns:
        List of ExecutionResult for each item processed
    """
    results = []
    total = task.total_items
    current = task.completed_items

    for item in task.items:
        if item.completed:
            continue

        current += 1

        if on_progress:
            on_progress(current, total, item)

        # Execute the item
        result = execute_task_item(item, executor_fn)

        if result.success:
            # Mark as complete in the file
            mark_item_complete(task.path, item.line_number)

        results.append(result)

        if not result.success:
            break  # Stop on first failure

    return results


def run_task_with_visual_verification(
    task: TaskFile,
    executor_fn: Optional[Callable[[str], bool]] = None,
    on_progress: Optional[Callable[[int, int, ChecklistItem], None]] = None,
    acceptance_criteria: Optional[str] = None,
    screenshot_dir: Optional[str] = None,
    verify_each_item: bool = False
) -> List[ExecutionResult]:
    """
    Run task items with visual verification via Claude CLI.

    This launches applications invisibly, captures screenshots, and uses
    Claude CLI to verify task completion without disturbing the user.

    Args:
        task: The TaskFile to execute
        executor_fn: Function to execute each item
        on_progress: Callback for progress updates (current, total, item)
        acceptance_criteria: Optional acceptance criteria for verification
        screenshot_dir: Directory to save screenshots
        verify_each_item: If True, verify after each item. If False, verify at end.

    Returns:
        List of ExecutionResult with verification results
    """
    results = []
    total = task.total_items
    current = task.completed_items

    # Detect app type from task file
    task_content = task.path.read_text(encoding='utf-8')
    app_type, config = detect_app_type(task_content)

    # Extract acceptance criteria from task file if not provided
    if not acceptance_criteria:
        criteria_match = re.search(
            r'## Acceptance Criteria\s*\n(.*?)(?=\n##|\Z)',
            task_content,
            re.DOTALL | re.IGNORECASE
        )
        if criteria_match:
            acceptance_criteria = criteria_match.group(1).strip()

    # Collect items to verify
    items_to_verify = []

    for item in task.items:
        if item.completed:
            continue

        current += 1

        if on_progress:
            on_progress(current, total, item)

        # Execute the item
        result = execute_task_item(item, executor_fn)

        if result.success:
            items_to_verify.append(item)

            if verify_each_item:
                # Verify this single item
                verification = run_visual_verification(
                    str(task.path),
                    [item.text],
                    acceptance_criteria,
                    screenshot_dir
                )
                result.verification = verification

                if verification.success and item.text in verification.completed_items:
                    mark_item_complete(task.path, item.line_number)
                else:
                    result.success = False
                    result.message = f"Visual verification failed: {verification.claude_response}"

        results.append(result)

        if not result.success:
            break

    # Final verification of all items at once (if not verifying each)
    if not verify_each_item and items_to_verify:
        print("\nRunning visual verification (invisible capture)...")

        verification = run_visual_verification(
            str(task.path),
            [item.text for item in items_to_verify],
            acceptance_criteria,
            screenshot_dir
        )

        # Update results with verification
        for result in results:
            if result.item.text in verification.completed_items:
                result.verification = verification
                mark_item_complete(task.path, result.item.line_number)
            elif result.item.text in verification.failed_items:
                result.success = False
                result.message = "Visual verification: NOT COMPLETED"
                result.verification = verification

        # Add summary result
        if verification.success:
            print(f"\n✓ All {len(verification.completed_items)} items verified complete")
        else:
            print(f"\n✗ Verification: {len(verification.completed_items)} complete, "
                  f"{len(verification.failed_items)} failed")
            if verification.screenshot_path:
                print(f"  Screenshot saved: {verification.screenshot_path}")

    return results


def format_execution_report(task: TaskFile, results: List[ExecutionResult]) -> str:
    """Format execution results as a report."""
    lines = [
        f"## Execution Report: {task.path.name}",
        "",
    ]

    if not results:
        lines.append("No items to execute (all complete or none found)")
        return '\n'.join(lines)

    successful = sum(1 for r in results if r.success)
    failed = len(results) - successful

    lines.extend([
        f"- **Executed**: {len(results)} items",
        f"- **Successful**: {successful}",
        f"- **Failed**: {failed}",
        "",
        "### Results",
        "",
    ])

    for result in results:
        status = "Done" if result.success else "FAILED"
        lines.append(f"- [{status}] {result.item.text}")
        if not result.success:
            lines.append(f"  - Error: {result.message}")

    # Show final status
    task = parse_task_file(task.path)  # Re-parse to get updated status
    lines.extend([
        "",
        f"### Final Status: {task.status}",
        f"Progress: {task.completed_items}/{task.total_items} ({task.progress_percent:.0f}%)",
    ])

    return '\n'.join(lines)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: executor.py <task_file.md>")
        sys.exit(1)

    task_path = Path(sys.argv[1])
    if not task_path.exists():
        print(f"File not found: {task_path}")
        sys.exit(1)

    task = parse_task_file(task_path)
    print(f"Task: {task.title}")
    print(f"Status: {task.status}")
    print(f"Progress: {task.completed_items}/{task.total_items}")
    print()

    if task.remaining_items == 0:
        print("All items already complete!")
        sys.exit(0)

    print(f"Executing {task.remaining_items} remaining items...")
    print()

    def progress_callback(current: int, total: int, item: ChecklistItem):
        print(f"[{current}/{total}] {item.text}")

    # Dry run - just mark items complete without actual execution
    results = run_task(task, on_progress=progress_callback)

    print()
    print(format_execution_report(task, results))
