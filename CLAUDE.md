# Tool Reader

A Claude Code plugin for reading, executing, and visually verifying task definitions from `.claude/*.md` files.

## Codebase Overview

This plugin parses markdown checklist files, executes tasks with progress tracking, and verifies completion using invisible screenshots sent to Claude CLI. The architecture separates parsing (parser.py), execution (executor.py), visual capture (visual_verifier.py), and reporting (reporter.py).

**Stack**: Python 3, PowerShell (Windows), Headless Chrome/Edge

**Structure**:
- `.claude-plugin/` - Plugin manifest and marketplace config
- `plugins/tool-reader/commands/` - Command documentation
- `plugins/tool-reader/scripts/` - Core Python modules
- `plugins/tool-reader/skills/` - Agent instructions

For detailed architecture, see [docs/CODEBASE_MAP.md](docs/CODEBASE_MAP.md).

## Key Commands

- `/list-tools` - List all task files in .claude/
- `/run-tool <name>` - Execute a task with optional `--verify` flag
- `/verify-tool <name>` - Verify task completion via screenshot

## Development

The plugin uses invisible window techniques to capture screenshots without user disruption:
- Webapps: Headless browser
- GUI apps: PrintWindow API
- TUI/CLI: Hidden subprocess
