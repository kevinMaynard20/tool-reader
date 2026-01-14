# Tool Reader - Claude Code Plugin

A Claude Code skill that automatically verifies GUI, TUI, and webapp changes with invisible screenshots and auto-fix capabilities.

## Features

- **Visual Verification**: Capture invisible screenshots and verify with Claude CLI
- **Auto-Verify**: Automatically verify after editing UI files (when enabled)
- **Auto-Fix**: Attempt automatic code fixes when issues are detected
- **Baseline Comparison**: Save and compare screenshots for regression testing
- **Multi-Platform**: Works with webapps, desktop GUI, and TUI/CLI apps

## Installation

### Step 1: Add the marketplace

```
/plugin marketplace add kevinMaynard20/tool-reader
```

### Step 2: Install the plugin

```
/plugin install tool-reader@kevinMaynard20-tool-reader
```

## Quick Start

### Enable Auto-Verification in Your Project

Add this line to your project's `CLAUDE.md`:

```markdown
tool-reader: auto-verify
```

Now Claude will automatically verify UI changes after you edit `.tsx`, `.vue`, `.css`, and other UI files.

### Manual Verification

```
/verify-tool my-task
```

## Commands

| Command | Description |
|---------|-------------|
| `/list-tools` | List all task files in `.claude/` with status |
| `/run-tool <name>` | Execute a task with optional verification |
| `/verify-tool <name>` | Visually verify task completion |
| `/save-baseline <name>` | Save current UI state as baseline |
| `/compare-baseline <name>` | Compare current state against baseline |
| `/setup-tool-reader` | Configure auto-verify in current project |

### /list-tools

Scan the `.claude/` directory for task files and display status.

```
/list-tools
```

### /run-tool <name>

Execute a task from `.claude/<name>.md`.

```
/run-tool my-task
/run-tool my-task --verify        # Verify with screenshots
/run-tool my-task --verify-each   # Verify after each item
```

### /verify-tool <name>

Visually verify task completion using invisible screenshots.

```
/verify-tool my-task
```

### /save-baseline <name>

Save current UI state as a baseline for regression testing.

```
/save-baseline login-page
/save-baseline dashboard "After adding stats widget"
```

### /compare-baseline <name>

Compare current state against a saved baseline.

```
/compare-baseline login-page
```

### /setup-tool-reader

Initialize auto-verification in the current project.

```
/setup-tool-reader
/setup-tool-reader http://localhost:5173
```

## Task File Format

Create task files in `.claude/` with checklists and app type markers:

```markdown
# Task Name

## Application

[webapp]: http://localhost:3000
[gui]: myapp.exe --window-title "My App"
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

All screenshots are captured **invisibly** - no windows steal focus or interrupt your work:

| App Type | Method |
|----------|--------|
| **Webapp** | Headless Chrome/Edge (`--headless=new`) |
| **GUI** | PowerShell hidden window + PrintWindow API |
| **TUI** | Hidden subprocess with output capture |

## Auto-Verification

When enabled (`tool-reader: auto-verify` in CLAUDE.md), verification triggers after editing:

- `*.tsx`, `*.jsx`, `*.vue`, `*.svelte`, `*.astro`
- `*.css`, `*.scss`, `*.sass`, `*.less`
- `*.xaml`, `*.axaml`, `*.fxml`, `*.qml`
- Files in `**/cli/**`, `**/tui/**`

### Auto-Fix Workflow

If verification detects issues:
1. Claude analyzes the screenshot
2. Identifies the source file and line
3. Proposes and applies a fix
4. Re-verifies to confirm
5. Reports results

## Baseline Management

Save baselines after major UI changes for regression testing:

```
.claude/
└── baselines/
    ├── manifest.json
    ├── login-page_1705312200.png
    └── dashboard_1705312300.png
```

## Requirements

- **Claude CLI** (`claude` command) in PATH
- **Edge or Chrome** browser for webapp screenshots
- **PowerShell** for GUI window management (Windows)

## License

MIT License

## Author

kevinMaynard20
