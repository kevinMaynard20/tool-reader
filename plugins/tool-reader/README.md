# Tool Reader Plugin

This plugin provides commands for reading and executing task definitions from `.claude/*.md` files.

## Commands

- `/list-tools` - List all task files in .claude/ directory
- `/run-tool <name>` - Execute a task from .claude/<name>.md
- `/verify-tool <name>` - Check completion status of a task

## Skills

The tool-reader skill enables Claude to automatically find and execute task definitions.

## Triggers

- "list tasks"
- "run task"
- "show tools"
- "check progress"
