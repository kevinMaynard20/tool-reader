# /setup-tool-reader

Initialize tool-reader in the current project. Configures CLAUDE.md with adapter settings and todo-based verification triggers.

## Usage

```bash
/setup-tool-reader
/setup-tool-reader --target <url|command>
/setup-tool-reader --adapter <playwright|browser|tui|gui|cli|auto>
/setup-tool-reader --capture-dir <path>
```

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--target` | No | Default target (URL or command) |
| `--adapter` | No | Preferred adapter (auto-detected if not specified) |
| `--capture-dir` | No | Directory for captures (default: .tool-reader/captures/) |
| `--playwright` | No | Enable Playwright with settings |

## Examples

```bash
# Auto-detect everything
/setup-tool-reader

# Specify target
/setup-tool-reader --target http://localhost:3000
/setup-tool-reader --target "cargo run"

# Specify adapter
/setup-tool-reader --adapter playwright
/setup-tool-reader --adapter tui

# Configure capture directory
/setup-tool-reader --capture-dir ./screenshots

# Full configuration
/setup-tool-reader --target http://localhost:5173 --adapter playwright --capture-dir ./captures
```

## What It Does

1. **Detect Project Type** - Scan for package.json, Cargo.toml, etc.
2. **Select Adapter** - Auto-detect or use specified adapter
3. **Configure Capture Dir** - Set up capture storage location
4. **Add to CLAUDE.md** - Append tool-reader configuration
5. **Setup Todo Integration** - Configure verification triggers

## Auto-Detection

| Files Found | Project Type | Default Adapter |
|-------------|--------------|-----------------|
| package.json | webapp | playwright/browser |
| Cargo.toml (ratatui) | tui | tui |
| Cargo.toml (iced/egui) | gui | gui |
| Cargo.toml (other) | cli | cli |
| pyproject.toml | python | cli |
| Other | unknown | cli |

## Configuration Added to CLAUDE.md

```markdown
---

## Tool Reader Configuration

tool-reader: enabled
tool-reader-adapter: auto
tool-reader-target: http://localhost:3000
tool-reader-capture-dir: .tool-reader/captures/

### Adapters Available

| Adapter | Targets | Features |
|---------|---------|----------|
| playwright | http://, https:// | Event-based, sequences |
| browser | http://, https:// | Headless screenshot |
| tui | tui:, commands | ANSI capture |
| gui | window:, .exe | Window capture |
| cli | commands | stdout/stderr |

### Read From Todos

Claude should check TodoWrite state for verification triggers:

**Run `/verify-tool` when:**
1. All todos in phase (implement/test/build) completed
2. Todo with "verify", "test", "check", "build" completed
3. All todos marked complete

**Phase Keywords:**
- Implementation: implement, create, add, write
- Testing: test, spec, unit, integration
- Build: build, compile, bundle
- Deploy: deploy, release, publish

### .md File Instructions

When following .md file instructions:
1. Parse checklist items into TodoWrite
2. Trigger verification at section boundaries
3. Run final verification when complete

### Commands

- `/verify-tool <task>` - Verify with auto-detected adapter
- `/verify-tool <task> --adapter <type>` - Use specific adapter
- `/verify-tool <task> --batch <dir>` - Batch verify captures
- `/capture --target <target>` - Capture current state
- `/verify-batch <dir>` - Batch verify captures
- `/list-tools --captures` - List pending captures
```

## Output

```
## Tool Reader Setup Complete

**Project**: my-project
**Type**: webapp
**Adapter**: playwright
**Target**: http://localhost:5173
**Capture Dir**: .tool-reader/captures/

Configuration added to CLAUDE.md

Available commands:
- /verify-tool <task>
- /capture --target <url|cmd>
- /verify-batch <capture-dir>
- /list-tools --adapters
```

## Notes

- Auto-detects project type from config files
- Playwright preferred for web (falls back to browser)
- Creates .tool-reader/captures/ for storing captures
- Todo integration uses Claude's built-in TodoWrite
- Configuration can be edited manually in CLAUDE.md
