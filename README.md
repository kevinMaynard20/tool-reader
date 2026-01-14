# Tool Reader - Claude Code Plugin

A Claude Code plugin that reads and executes task definitions from `.claude/*.md` files.

## Features

- **Scan for Tasks**: Discover all task definition files in `.claude/` directory
- **Parse Checklists**: Parse `[ ]` and `[x]` checklist format
- **Execute Tasks**: Run tasks with progress tracking
- **Track Progress**: Report completion status and percentages

## Installation

```bash
# Clone the repository
git clone https://github.com/kmaynardrpp/tool-reader.git

# Or install via Claude Code
/plugin install tool-reader@kmaynardrpp
```

## Commands

### /list-tools

Scan the `.claude/` directory for task definition files and display them with their status.

```
/list-tools
```

Output:
- Filename
- Description (from first heading)
- Completion status (if checklist present)

### /run-tool <name>

Execute a task definition from `.claude/<name>.md`.

```
/run-tool PLUGIN_TASK
```

This will:
1. Parse the `.md` file
2. Extract checklist items
3. Execute each uncompleted item
4. Mark items as `[x]` when completed
5. Report progress

### /verify-tool <name>

Check completion status of a task file without executing.

```
/verify-tool PLUGIN_TASK
```

Output:
- Total items count
- Completed items count
- Remaining items count
- Status: COMPLETE / IN_PROGRESS / NOT_STARTED

## Task File Format

Task files should use markdown with checklists:

```markdown
# Task Name

## Description
What this task does...

## Checklist

- [ ] First step
- [ ] Second step
- [x] Completed step
```

## License

MIT License - See LICENSE for details.

## Author

kmaynardrpp
