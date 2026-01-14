# Tool Reader Plugin

This plugin provides commands for reading and executing task definitions from `.claude/*.md` files.

**New:** Integrates with Claude's built-in TodoWrite/task system for automatic verification triggers at phase boundaries.

## Commands

- `/list-tools` - List all task files in .claude/ directory
- `/run-tool <name>` - Execute a task from .claude/<name>.md
- `/verify-tool <name>` - Check completion status of a task (with todo integration)

## Features

### Claude Todo Integration

Tool-reader can reference Claude's built-in todos/tasks to determine when verification should occur:

- **Phase Completion** - Auto-verify when implementation/testing/build phases complete
- **Verification Todos** - Trigger when todos with "verify", "test", "check" complete
- **Final Verification** - Run when all todos are marked complete

```bash
# Check if todos indicate verification needed
/verify-tool my-task --check-todos

# Run verification with todo context
/verify-tool my-task --todos '{"todos":[...]}'
```

### Scripts

- `todo_tracker.py` - Parses and analyzes Claude's TodoWrite state
- `visual_verifier.py` - Screenshot capture and Claude CLI verification
- `parser.py` - Task file parsing
- `executor.py` - Task execution

## Skills

The tool-reader skill enables Claude to automatically find and execute task definitions.

## Triggers

- "list tasks"
- "run task"
- "show tools"
- "check progress"
- "verify behavior" (new - triggers todo-aware verification)
