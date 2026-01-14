# Tool Reader - Claude Code Plugin

A Claude Code plugin that reads, executes, and visually verifies task definitions from `.claude/*.md` files.

## Features

- **Scan for Tasks**: Discover all task definition files in `.claude/` directory
- **Parse Checklists**: Parse `[ ]` and `[x]` checklist format
- **Execute Tasks**: Run tasks with progress tracking
- **Visual Verification**: Capture invisible screenshots and verify with Claude CLI
- **Track Progress**: Report completion status and percentages

## Installation

### Step 1: Add the marketplace

```
/plugin marketplace add kevinmaynard20
```

### Step 2: Install the plugin

```
/plugin install tool-reader@kevinmaynard20
```

### Alternative: From Local Path

```
/plugin install /path/to/tool-reader
```

## Commands

### /list-tools

Scan the `.claude/` directory for task definition files and display them with their status.

```
/list-tools
```

### /run-tool <name>

Execute a task definition from `.claude/<name>.md`.

```
/run-tool my-task
/run-tool my-task --verify        # Verify with screenshots
/run-tool my-task --verify-each   # Verify after each item
```

### /verify-tool <name>

Visually verify task completion using invisible screenshots.

```
/verify-tool my-task
/verify-tool my-task --status   # Status only (no visual capture)
```

## Task File Format

Task files should use markdown with checklists and optional app type markers:

```markdown
# Task Name

## Application

[webapp]: http://localhost:3000
[gui]: myapp.exe
[tui]: npm run dev

## Acceptance Criteria

- Page should load correctly
- All buttons should be visible

## Checklist

- [ ] First step
- [ ] Second step
- [x] Completed step
```

## Visual Verification

The plugin can capture screenshots invisibly (no focus steal) to verify tasks:

- **Webapp**: Headless Chrome/Edge browser
- **GUI**: PowerShell hidden window + PrintWindow API
- **TUI**: Hidden subprocess with output capture

Screenshots are sent to Claude CLI for verification against the task checklist.

## License

MIT License

## Author

kevinmaynard20
