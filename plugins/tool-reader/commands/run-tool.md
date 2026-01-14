# /tool-reader:run-tool

Execute a task definition from `.claude/<name>.md` with optional capture and verification.

## Usage

```bash
/tool-reader:run-tool <name>
/tool-reader:run-tool <name> --verify
/tool-reader:run-tool <name> --capture
/tool-reader:run-tool <name> --capture-on <events>
/tool-reader:run-tool <name> --adapter <type>
```

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `name` | Yes | Task file name in .claude/ directory |
| `--verify` | No | Verify completion after running |
| `--verify-each` | No | Verify after each item |
| `--capture` | No | Capture state during execution |
| `--capture-on` | No | Events to capture on (click, navigate, etc.) |
| `--adapter` | No | Specific adapter to use |
| `--batch` | No | Batch verify captures after completion |

## Examples

```bash
# Basic execution
/tool-reader:run-tool PLUGIN_TASK

# Run and verify at end
/tool-reader:run-tool webapp-task --verify

# Run with capture enabled
/tool-reader:run-tool user-flow --capture

# Capture on specific events
/tool-reader:run-tool user-flow --capture-on click,navigate,input

# Use specific adapter
/tool-reader:run-tool webapp-task --adapter playwright

# Run, capture, and batch verify
/tool-reader:run-tool user-flow --capture --batch
```

## Execution Flow

### Standard Execution
```
> /tool-reader:run-tool PLUGIN_TASK

Reading task: .claude/PLUGIN_TASK.md
Found 25 items (12 completed, 13 remaining)

Executing remaining items:

[13/25] Create tool-reader plugin structure
  - Creating directories...
  - Done!

[14/25] Implement /list-tools
  - Writing command file...
  - Done!

...

Task completed: 25/25 items done
```

### With Capture (--capture)
```
> /tool-reader:run-tool user-flow --capture

Reading task: .claude/user-flow.md
Found 10 items (5 completed, 5 remaining)
Target: [webapp]: http://localhost:3000
Adapter: playwright

Executing with capture enabled:

[6/10] Login page renders
  - Capturing initial state...
  - Done! (capture_001.png)

[7/10] Fill login form
  - Working...
  - Capturing after input...
  - Done! (capture_002.png)

...

Captures saved: 5 files in .tool-reader/captures/
Run: /tool-reader:verify-batch .tool-reader/captures/ to verify all
```

### With Verify (--verify)
```
> /tool-reader:run-tool webapp-task --verify

Reading task: .claude/webapp-task.md
Found 10 items (5 completed, 5 remaining)
Target: [webapp]: http://localhost:3000
Adapter: playwright

Executing remaining items...

Running visual verification...
  - Capturing with playwright adapter...
  - Sending to Claude CLI...

Verification Results:
  PASSED: Login page renders correctly
  PASSED: Form validation works
  FAILED: Dashboard loads - Still on login page

Verified: 2/3 items
Capture: .tool-reader/captures/webapp-task_123.png
```

### Capture and Batch Verify (--capture --batch)
```
> /tool-reader:run-tool user-flow --capture --batch

Reading task: .claude/user-flow.md
Executing with capture and batch verification...

[Execution output...]

Captures: 8 files saved

Running batch verification...

BATCH VERIFICATION: 8 captures
  PASSED: 7/8
  FAILED: 1/8

Issues:
  - Capture 5: Submit button not visible
```

## Adapter Selection

| Target Marker | Default Adapter |
|---------------|-----------------|
| `[webapp]:` | playwright/browser |
| `[tui]:` | tui |
| `[gui]:` | gui |
| `[cli]:` | cli |
| None | auto-detect |

Override with `--adapter`:
```bash
/tool-reader:run-tool task --adapter playwright
/tool-reader:run-tool task --adapter tui
/tool-reader:run-tool task --adapter cli
```

## Capture Events

With `--capture-on`, specify when to capture:

```bash
# Capture on clicks and navigation
/tool-reader:run-tool task --capture-on click,navigate

# Capture on all inputs
/tool-reader:run-tool task --capture-on input

# Capture on specific selector
/tool-reader:run-tool task --capture-on "click:#submit-btn"
```

Available events:
- `click` - After clicking elements
- `navigate` - After page navigation
- `input` - After form input
- `wait` - After waits
- `all` - All events

## Task File Format

```markdown
# My Task

## Target
[webapp]: http://localhost:3000

## Checklist
- [ ] Login page renders correctly
- [ ] Form validation works
- [x] Already done step
- [ ] Dashboard loads after login
```

## Invisible Capture

All captures happen without user disruption:

| Adapter | Capture Method |
|---------|----------------|
| playwright | Headless browser (--headless=new) |
| browser | Headless Chrome/Edge |
| tui | Background terminal capture |
| gui | Hidden window + PrintWindow API |
| cli | Subprocess stdout/stderr |

## Notes

- Task file must exist in .claude/ directory
- Adapters auto-detect from target markers
- Use --capture to save captures for later verification
- Use --batch to immediately batch verify captures
- All captures are invisible - no user disruption
- Captures saved to .tool-reader/captures/ by default
