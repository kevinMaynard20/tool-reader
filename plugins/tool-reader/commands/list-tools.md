# /list-tools

List task files, available adapters, and pending captures.

## Usage

```bash
/list-tools
/list-tools --adapters
/list-tools --captures
/list-tools --captures --pending
/list-tools --verbose
```

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--adapters` | No | List available capture adapters |
| `--captures` | No | List stored captures |
| `--pending` | No | Only show unverified captures (with --captures) |
| `--verbose` | No | Show detailed info including targets |

## Examples

```bash
# List task files (default)
/list-tools

# List available adapters
/list-tools --adapters

# List all captures
/list-tools --captures

# List only unverified captures
/list-tools --captures --pending

# Verbose output with targets
/list-tools --verbose
```

## Output: Task Files (Default)

```
## Task Files in .claude/

| File | Description | Status | Progress |
|------|-------------|--------|----------|
| PLUGIN_TASK.md | Create two plugins | IN_PROGRESS | 12/25 (48%) |
| AUTH_TASK.md | Add OAuth support | NOT_STARTED | 0/10 (0%) |
| DEPLOY.md | Deploy to production | COMPLETE | 5/5 (100%) |

Total: 3 task files
```

## Output: Adapters

```bash
/list-tools --adapters
```

```
## Available Adapters

| Adapter | Available | Targets | Features |
|---------|-----------|---------|----------|
| playwright | Yes | http://, https:// | Event-based, sequences, DOM |
| browser | Yes | http://, https:// | Screenshot |
| tui | Yes | tui:, commands | ANSI, input, keys |
| gui | Yes | window:, .exe | Window capture |
| cli | Yes | commands | stdout/stderr |

Note: Playwright requires: pip install playwright && playwright install
```

## Output: Captures

```bash
/list-tools --captures
```

```
## Stored Captures

| ID | Event | Source | Verified | Path |
|----|-------|--------|----------|------|
| abc123 | click:#login | playwright | No | .tool-reader/captures/abc123_1234567890.png |
| def456 | navigate | external | Yes | .tool-reader/captures/def456_1234567891.png |
| ghi789 | input:#email | playwright | No | .tool-reader/captures/ghi789_1234567892.png |

Total: 3 captures (2 pending verification)
```

## Output: Pending Captures

```bash
/list-tools --captures --pending
```

```
## Pending Captures (Unverified)

| ID | Event | Source | Path |
|----|-------|--------|------|
| abc123 | click:#login | playwright | .tool-reader/captures/abc123_1234567890.png |
| ghi789 | input:#email | playwright | .tool-reader/captures/ghi789_1234567892.png |

Total: 2 pending captures

Run: /verify-batch .tool-reader/captures/ to verify all
```

## Output: Verbose

```bash
/list-tools --verbose
```

```
## Task Files in .claude/

### PLUGIN_TASK.md
- Description: Create two plugins
- Status: IN_PROGRESS
- Progress: 12/25 (48%)
- Target: [webapp]: http://localhost:3000
- Adapter: playwright

### AUTH_TASK.md
- Description: Add OAuth support
- Status: NOT_STARTED
- Progress: 0/10 (0%)
- Target: [tui]: cargo run
- Adapter: tui

Total: 2 task files
```

## Task Detection

A file is a task definition if it contains:
- At least one `[ ]` or `[x]` checkbox
- OR a section titled "## Checklist", "## Tasks", "## Steps", "## TODO"

## Notes

- Default behavior lists task files in .claude/
- Use --adapters to see available capture methods
- Use --captures to see stored screenshots/outputs
- Combine --captures --pending to see what needs verification
- Verbose mode shows target and adapter per task
