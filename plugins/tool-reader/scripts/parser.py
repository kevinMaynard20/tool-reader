#!/usr/bin/env python3
"""
Parser module for Tool Reader.
Parses task definition files and extracts checklist items.
"""

import re
from pathlib import Path
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class ChecklistItem:
    """Represents a checklist item from a task file."""
    line_number: int
    text: str
    completed: bool
    raw_line: str


@dataclass
class TaskFile:
    """Represents a parsed task file."""
    path: Path
    title: str
    description: str
    items: List[ChecklistItem]

    @property
    def total_items(self) -> int:
        return len(self.items)

    @property
    def completed_items(self) -> int:
        return sum(1 for item in self.items if item.completed)

    @property
    def remaining_items(self) -> int:
        return self.total_items - self.completed_items

    @property
    def progress_percent(self) -> float:
        if self.total_items == 0:
            return 0.0
        return (self.completed_items / self.total_items) * 100

    @property
    def status(self) -> str:
        if self.total_items == 0:
            return "NO_ITEMS"
        elif self.completed_items == 0:
            return "NOT_STARTED"
        elif self.completed_items == self.total_items:
            return "COMPLETE"
        else:
            return "IN_PROGRESS"


# Patterns for matching checklist items
CHECKLIST_PATTERNS = [
    # Standard markdown checkboxes
    re.compile(r'^(\s*[-*]\s*)\[([xX ])\]\s*(.+)$'),
    # Table-based checkboxes
    re.compile(r'^\|[^|]*\|\s*\[([xX ])\]\s*\|?\s*$'),
    re.compile(r'^\|[^|]*\|[^|]*\|\s*\[([xX ])\]\s*\|?\s*$'),
]

# Pattern for extracting title
TITLE_PATTERN = re.compile(r'^#\s+(.+)$', re.MULTILINE)


def parse_checklist_line(line: str) -> Optional[Tuple[str, bool]]:
    """
    Parse a line to extract checklist item if present.

    Returns:
        Tuple of (item_text, is_completed) or None if not a checklist line
    """
    line = line.rstrip()

    # Standard markdown checkbox: - [ ] or * [ ] or - [x]
    match = re.match(r'^(\s*[-*]\s*)\[([xX ])\]\s*(.+)$', line)
    if match:
        completed = match.group(2).lower() == 'x'
        text = match.group(3).strip()
        return (text, completed)

    # Table-based checkbox in last column: | Task | [ ] |
    match = re.match(r'^\|(.+)\|\s*\[([xX ])\]\s*\|?\s*$', line)
    if match:
        completed = match.group(2).lower() == 'x'
        # Extract task text from previous columns
        columns = match.group(1).split('|')
        text = columns[-1].strip() if columns else line
        return (text, completed)

    return None


def parse_task_file(file_path: Path) -> TaskFile:
    """
    Parse a task definition file and extract its contents.

    Args:
        file_path: Path to the .md task file

    Returns:
        TaskFile object with parsed contents
    """
    try:
        content = file_path.read_text(encoding='utf-8')
    except Exception as e:
        return TaskFile(
            path=file_path,
            title=file_path.stem,
            description=f"Error reading file: {e}",
            items=[]
        )

    lines = content.split('\n')

    # Extract title
    title = file_path.stem
    title_match = TITLE_PATTERN.search(content)
    if title_match:
        title = title_match.group(1).strip()

    # Extract description (first paragraph after title)
    description = ""
    in_description = False
    for line in lines:
        if line.startswith('# '):
            in_description = True
            continue
        if in_description:
            if line.strip() == '':
                if description:
                    break
            elif line.startswith('#'):
                break
            else:
                if description:
                    description += ' '
                description += line.strip()

    # Extract checklist items
    items = []
    for line_num, line in enumerate(lines, 1):
        result = parse_checklist_line(line)
        if result:
            text, completed = result
            items.append(ChecklistItem(
                line_number=line_num,
                text=text,
                completed=completed,
                raw_line=line
            ))

    return TaskFile(
        path=file_path,
        title=title,
        description=description[:200] if description else "No description",
        items=items
    )


def find_task_files(claude_dir: Path) -> List[Path]:
    """
    Find all task definition files in .claude/ directory.

    Args:
        claude_dir: Path to .claude/ directory

    Returns:
        List of paths to task files
    """
    if not claude_dir.exists():
        return []

    task_files = []
    for md_file in claude_dir.glob('*.md'):
        # Skip certain files
        if md_file.name.startswith('.'):
            continue
        if md_file.name.lower() in ('readme.md', 'changelog.md'):
            continue

        # Check if it has checklist items
        try:
            content = md_file.read_text(encoding='utf-8')
            if '[ ]' in content or '[x]' in content or '[X]' in content:
                task_files.append(md_file)
        except Exception:
            continue

    return sorted(task_files)


def list_all_tasks(project_root: Path) -> List[TaskFile]:
    """
    List all task files in a project's .claude/ directory.

    Args:
        project_root: Path to project root

    Returns:
        List of parsed TaskFile objects
    """
    claude_dir = project_root / '.claude'
    task_files = find_task_files(claude_dir)

    return [parse_task_file(f) for f in task_files]


def format_task_list(tasks: List[TaskFile]) -> str:
    """Format task list as markdown table."""
    if not tasks:
        return "No task files found in .claude/ directory."

    lines = [
        "## Task Files in .claude/",
        "",
        "| File | Description | Status | Progress |",
        "|------|-------------|--------|----------|",
    ]

    for task in tasks:
        progress = f"{task.completed_items}/{task.total_items} ({task.progress_percent:.0f}%)"
        lines.append(f"| {task.path.name} | {task.description[:40]}... | {task.status} | {progress} |")

    lines.extend([
        "",
        f"Total: {len(tasks)} task file(s)",
    ])

    return '\n'.join(lines)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
        if path.is_file():
            task = parse_task_file(path)
            print(f"Title: {task.title}")
            print(f"Description: {task.description}")
            print(f"Status: {task.status}")
            print(f"Progress: {task.completed_items}/{task.total_items} ({task.progress_percent:.0f}%)")
            print(f"\nItems:")
            for item in task.items:
                marker = '[x]' if item.completed else '[ ]'
                print(f"  {marker} {item.text}")
        else:
            tasks = list_all_tasks(path)
            print(format_task_list(tasks))
    else:
        tasks = list_all_tasks(Path.cwd())
        print(format_task_list(tasks))
