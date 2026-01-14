#!/usr/bin/env python3
"""
Todo Tracker for Tool Reader.
Integrates with Claude's built-in TodoWrite/task system to trigger verification
at phase boundaries and during verification steps.
"""

import os
import re
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class TodoStatus(Enum):
    """Status values matching Claude's TodoWrite system."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class PhaseType(Enum):
    """Types of phases that can trigger verification."""
    IMPLEMENTATION = "implementation"
    TESTING = "testing"
    VERIFICATION = "verification"
    BUILD = "build"
    DEPLOY = "deploy"
    REVIEW = "review"
    UNKNOWN = "unknown"


@dataclass
class TodoItem:
    """Represents a single todo item from Claude's task system."""
    content: str
    status: TodoStatus
    active_form: str = ""
    phase: PhaseType = PhaseType.UNKNOWN
    requires_verification: bool = False


@dataclass
class PhaseContext:
    """Context for the current phase of work."""
    phase_type: PhaseType
    todos: List[TodoItem] = field(default_factory=list)
    completed_count: int = 0
    pending_count: int = 0
    in_progress_count: int = 0
    should_verify: bool = False
    verification_triggers: List[str] = field(default_factory=list)


# Keywords that indicate a todo needs verification
VERIFICATION_KEYWORDS = [
    "verify", "test", "check", "validate", "confirm", "ensure",
    "build", "run", "deploy", "launch", "render", "display",
    "ui", "visual", "screenshot", "appearance", "layout"
]

# Keywords that indicate phase boundaries
PHASE_BOUNDARY_KEYWORDS = {
    PhaseType.IMPLEMENTATION: ["implement", "create", "add", "write", "code", "develop"],
    PhaseType.TESTING: ["test", "spec", "unit", "integration", "e2e"],
    PhaseType.VERIFICATION: ["verify", "check", "validate", "confirm"],
    PhaseType.BUILD: ["build", "compile", "bundle", "package"],
    PhaseType.DEPLOY: ["deploy", "release", "publish", "ship"],
    PhaseType.REVIEW: ["review", "pr", "merge", "commit"],
}


def detect_phase(todo_content: str) -> PhaseType:
    """Detect the phase type from todo content."""
    content_lower = todo_content.lower()

    for phase, keywords in PHASE_BOUNDARY_KEYWORDS.items():
        if any(kw in content_lower for kw in keywords):
            return phase

    return PhaseType.UNKNOWN


def requires_verification(todo_content: str) -> bool:
    """Determine if a todo item requires verification after completion."""
    content_lower = todo_content.lower()
    return any(kw in content_lower for kw in VERIFICATION_KEYWORDS)


def parse_todos_from_context(context: str) -> List[TodoItem]:
    """
    Parse todo items from Claude conversation context or todo list output.

    This looks for patterns like:
    - TodoWrite tool calls with todo arrays
    - Markdown task lists (- [ ] task, - [x] task)
    - Numbered lists with status indicators
    """
    todos = []

    # Pattern 1: JSON todo arrays (from TodoWrite)
    json_pattern = r'"todos"\s*:\s*\[(.*?)\]'
    json_matches = re.findall(json_pattern, context, re.DOTALL)

    for match in json_matches:
        try:
            # Try to parse as JSON array elements
            items_text = f"[{match}]"
            items = json.loads(items_text)
            for item in items:
                if isinstance(item, dict):
                    status_str = item.get("status", "pending")
                    try:
                        status = TodoStatus(status_str)
                    except ValueError:
                        status = TodoStatus.PENDING

                    content = item.get("content", "")
                    active_form = item.get("activeForm", "")

                    todo = TodoItem(
                        content=content,
                        status=status,
                        active_form=active_form,
                        phase=detect_phase(content),
                        requires_verification=requires_verification(content)
                    )
                    todos.append(todo)
        except json.JSONDecodeError:
            continue

    # Pattern 2: Markdown task lists
    md_task_pattern = r'- \[([ xX])\]\s*(.+?)(?:\n|$)'
    md_matches = re.findall(md_task_pattern, context)

    for check, content in md_matches:
        status = TodoStatus.COMPLETED if check.lower() == 'x' else TodoStatus.PENDING
        todo = TodoItem(
            content=content.strip(),
            status=status,
            phase=detect_phase(content),
            requires_verification=requires_verification(content)
        )
        # Avoid duplicates
        if not any(t.content == todo.content for t in todos):
            todos.append(todo)

    return todos


def analyze_phase_context(todos: List[TodoItem]) -> PhaseContext:
    """
    Analyze the current todos to determine phase context and verification needs.

    Returns PhaseContext with:
    - Current phase type
    - Todo counts by status
    - Whether verification should trigger
    - What verification triggers were detected
    """
    if not todos:
        return PhaseContext(phase_type=PhaseType.UNKNOWN)

    # Count by status
    completed = [t for t in todos if t.status == TodoStatus.COMPLETED]
    pending = [t for t in todos if t.status == TodoStatus.PENDING]
    in_progress = [t for t in todos if t.status == TodoStatus.IN_PROGRESS]

    # Determine current phase from in-progress or most recent
    current_phase = PhaseType.UNKNOWN
    if in_progress:
        current_phase = in_progress[0].phase
    elif completed:
        current_phase = completed[-1].phase

    # Determine if verification should trigger
    should_verify = False
    verification_triggers = []

    # Trigger 1: Phase boundary - all items in a phase completed
    phase_todos = [t for t in todos if t.phase == current_phase]
    phase_completed = [t for t in phase_todos if t.status == TodoStatus.COMPLETED]
    if phase_todos and len(phase_completed) == len(phase_todos):
        should_verify = True
        verification_triggers.append(f"Phase '{current_phase.value}' completed")

    # Trigger 2: Verification-requiring todo completed
    for todo in completed:
        if todo.requires_verification:
            should_verify = True
            verification_triggers.append(f"Verification todo completed: {todo.content[:50]}")

    # Trigger 3: Build/test/deploy phase completed
    high_priority_phases = [PhaseType.BUILD, PhaseType.TESTING, PhaseType.DEPLOY]
    for phase in high_priority_phases:
        phase_items = [t for t in todos if t.phase == phase]
        phase_done = [t for t in phase_items if t.status == TodoStatus.COMPLETED]
        if phase_items and len(phase_done) == len(phase_items):
            should_verify = True
            verification_triggers.append(f"High-priority phase '{phase.value}' completed")

    # Trigger 4: All todos completed (final verification)
    if len(completed) == len(todos) and todos:
        should_verify = True
        verification_triggers.append("All todos completed - final verification")

    return PhaseContext(
        phase_type=current_phase,
        todos=todos,
        completed_count=len(completed),
        pending_count=len(pending),
        in_progress_count=len(in_progress),
        should_verify=should_verify,
        verification_triggers=verification_triggers
    )


def check_verification_needed(
    todos: List[TodoItem],
    last_completed_todo: Optional[TodoItem] = None
) -> Dict[str, Any]:
    """
    Check if verification is needed based on current todo state.

    This is the main entry point for tool-reader to determine if
    it should trigger verification.

    Args:
        todos: Current list of todos from Claude's task system
        last_completed_todo: The todo that was just completed (if any)

    Returns:
        Dict with:
        - needs_verification: bool
        - reason: str explaining why
        - phase: current phase name
        - progress: completion percentage
        - triggers: list of what triggered verification
    """
    context = analyze_phase_context(todos)

    # Additional check: if specific todo was just completed
    if last_completed_todo and last_completed_todo.requires_verification:
        context.should_verify = True
        context.verification_triggers.append(
            f"Just completed verification-requiring todo: {last_completed_todo.content[:50]}"
        )

    total = len(todos) if todos else 0
    progress = (context.completed_count / total * 100) if total > 0 else 0

    return {
        "needs_verification": context.should_verify,
        "reason": context.verification_triggers[0] if context.verification_triggers else "No verification needed",
        "phase": context.phase_type.value,
        "progress": round(progress, 1),
        "completed": context.completed_count,
        "pending": context.pending_count,
        "in_progress": context.in_progress_count,
        "triggers": context.verification_triggers
    }


def format_verification_prompt(
    context: PhaseContext,
    task_file: Optional[str] = None
) -> str:
    """
    Format a prompt for Claude to trigger verification.

    This generates a message that tool-reader can use to invoke
    visual verification based on the current phase context.
    """
    if not context.should_verify:
        return ""

    triggers_list = "\n".join(f"  - {t}" for t in context.verification_triggers)

    prompt = f"""## Verification Trigger

Based on the current todo state, verification is recommended:

**Phase**: {context.phase_type.value}
**Progress**: {context.completed_count}/{len(context.todos)} completed

**Triggers**:
{triggers_list}

"""

    if task_file:
        prompt += f"**Task File**: {task_file}\n\n"
        prompt += "Run `/verify-tool` to visually verify the current state.\n"
    else:
        prompt += "Consider running visual verification to confirm the completed work.\n"

    return prompt


# Example usage for integration with visual_verifier.py
def should_auto_verify(todos_json: str) -> bool:
    """
    Quick check if auto-verification should trigger.

    Args:
        todos_json: JSON string of todos from TodoWrite

    Returns:
        True if verification should auto-trigger
    """
    try:
        todos_data = json.loads(todos_json)
        if isinstance(todos_data, dict) and "todos" in todos_data:
            todos_data = todos_data["todos"]

        todos = []
        for item in todos_data:
            status = TodoStatus(item.get("status", "pending"))
            content = item.get("content", "")
            todos.append(TodoItem(
                content=content,
                status=status,
                active_form=item.get("activeForm", ""),
                phase=detect_phase(content),
                requires_verification=requires_verification(content)
            ))

        result = check_verification_needed(todos)
        return result["needs_verification"]

    except (json.JSONDecodeError, KeyError, ValueError):
        return False


if __name__ == "__main__":
    # Test with sample todos
    sample_todos = [
        TodoItem("Implement login form", TodoStatus.COMPLETED, phase=PhaseType.IMPLEMENTATION),
        TodoItem("Add form validation", TodoStatus.COMPLETED, phase=PhaseType.IMPLEMENTATION),
        TodoItem("Verify login UI renders correctly", TodoStatus.COMPLETED,
                 phase=PhaseType.VERIFICATION, requires_verification=True),
        TodoItem("Write unit tests", TodoStatus.IN_PROGRESS, phase=PhaseType.TESTING),
        TodoItem("Run build and fix errors", TodoStatus.PENDING, phase=PhaseType.BUILD),
    ]

    result = check_verification_needed(sample_todos)

    print("=" * 50)
    print("TODO TRACKER CHECK")
    print("=" * 50)
    print(f"Needs Verification: {result['needs_verification']}")
    print(f"Phase: {result['phase']}")
    print(f"Progress: {result['progress']}%")
    print(f"Reason: {result['reason']}")
    print("\nAll Triggers:")
    for trigger in result['triggers']:
        print(f"  - {trigger}")
