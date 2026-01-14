#!/usr/bin/env python3
"""
Reporter module for Tool Reader.
Generates status reports for task files.
"""

from pathlib import Path
from typing import List, Optional

from parser import TaskFile, parse_task_file, list_all_tasks


def verify_task(task: TaskFile) -> str:
    """
    Generate a verification report for a task.

    Args:
        task: The TaskFile to verify

    Returns:
        Markdown-formatted verification report
    """
    lines = [
        f"## Task Verification: {task.path.name}",
        "",
        f"**Title**: {task.title}",
        f"**Status**: {task.status}",
        "",
        "| Metric | Count |",
        "|--------|-------|",
        f"| Total Items | {task.total_items} |",
        f"| Completed | {task.completed_items} |",
        f"| Remaining | {task.remaining_items} |",
        f"| Progress | {task.progress_percent:.0f}% |",
        "",
    ]

    if task.status == "COMPLETE":
        lines.append("All items completed!")
    elif task.remaining_items > 0:
        lines.extend([
            "### Remaining Items",
            "",
        ])
        count = 0
        for item in task.items:
            if not item.completed:
                count += 1
                lines.append(f"{count}. [ ] {item.text}")
        lines.append("")

    return '\n'.join(lines)


def generate_summary_report(tasks: List[TaskFile]) -> str:
    """
    Generate a summary report for all tasks.

    Args:
        tasks: List of TaskFile objects

    Returns:
        Markdown-formatted summary report
    """
    if not tasks:
        return "No task files found in .claude/ directory."

    total_items = sum(t.total_items for t in tasks)
    completed_items = sum(t.completed_items for t in tasks)
    overall_progress = (completed_items / total_items * 100) if total_items > 0 else 0

    complete = sum(1 for t in tasks if t.status == "COMPLETE")
    in_progress = sum(1 for t in tasks if t.status == "IN_PROGRESS")
    not_started = sum(1 for t in tasks if t.status == "NOT_STARTED")

    lines = [
        "# Task Summary Report",
        "",
        "## Overview",
        "",
        f"- **Total Tasks**: {len(tasks)}",
        f"- **Complete**: {complete}",
        f"- **In Progress**: {in_progress}",
        f"- **Not Started**: {not_started}",
        "",
        f"**Overall Progress**: {completed_items}/{total_items} items ({overall_progress:.0f}%)",
        "",
        "## Tasks by Status",
        "",
    ]

    # Complete tasks
    if complete > 0:
        lines.append("### Complete")
        lines.append("")
        for task in tasks:
            if task.status == "COMPLETE":
                lines.append(f"- **{task.path.name}**: {task.title}")
        lines.append("")

    # In progress tasks
    if in_progress > 0:
        lines.append("### In Progress")
        lines.append("")
        for task in tasks:
            if task.status == "IN_PROGRESS":
                lines.append(f"- **{task.path.name}**: {task.title}")
                lines.append(f"  - Progress: {task.completed_items}/{task.total_items} ({task.progress_percent:.0f}%)")
        lines.append("")

    # Not started tasks
    if not_started > 0:
        lines.append("### Not Started")
        lines.append("")
        for task in tasks:
            if task.status == "NOT_STARTED":
                lines.append(f"- **{task.path.name}**: {task.title}")
                lines.append(f"  - Items: {task.total_items}")
        lines.append("")

    # Detailed breakdown
    lines.extend([
        "## Detailed Breakdown",
        "",
        "| File | Status | Completed | Total | Progress |",
        "|------|--------|-----------|-------|----------|",
    ])

    for task in tasks:
        lines.append(
            f"| {task.path.name} | {task.status} | "
            f"{task.completed_items} | {task.total_items} | "
            f"{task.progress_percent:.0f}% |"
        )

    lines.append("")
    return '\n'.join(lines)


def check_completion(task: TaskFile, expected_count: Optional[int] = None) -> dict:
    """
    Check if a task meets completion criteria.

    Args:
        task: The TaskFile to check
        expected_count: Expected number of completed items (for validation)

    Returns:
        Dictionary with completion status and details
    """
    result = {
        'file': str(task.path),
        'title': task.title,
        'status': task.status,
        'total': task.total_items,
        'completed': task.completed_items,
        'remaining': task.remaining_items,
        'progress': task.progress_percent,
        'is_complete': task.status == "COMPLETE",
    }

    if expected_count is not None:
        result['expected'] = expected_count
        result['matches_expected'] = task.completed_items >= expected_count

    return result


if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        # List all tasks
        tasks = list_all_tasks(Path.cwd())
        print(generate_summary_report(tasks))
    else:
        task_name = sys.argv[1]

        # Find the task file
        claude_dir = Path.cwd() / '.claude'
        task_path = claude_dir / f"{task_name}.md"

        if not task_path.exists():
            task_path = claude_dir / task_name
            if not task_path.exists():
                print(f"Task file not found: {task_name}")
                sys.exit(1)

        task = parse_task_file(task_path)
        print(verify_task(task))

        # Also output JSON for programmatic use
        if '--json' in sys.argv:
            expected = None
            for arg in sys.argv:
                if arg.startswith('--expected='):
                    expected = int(arg.split('=')[1])

            result = check_completion(task, expected)
            print()
            print("JSON Output:")
            print(json.dumps(result, indent=2))
