# /tool-reader:verify-tool

Verify task completion using the agnostic capture adapter system. Works with any target: webpages, TUIs, GUIs, or CLI tools.

## Usage

```bash
/tool-reader:verify-tool <task-name>
/tool-reader:verify-tool <task-name> --target <url|command|window>
/tool-reader:verify-tool <task-name> --adapter <playwright|browser|tui|gui|cli|auto>
/tool-reader:verify-tool <task-name> --batch <capture-dir>
/tool-reader:verify-tool <task-name> --captures <path1> <path2> ...
```

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `task-name` | Yes | Task file name in .claude/ directory |
| `--target` | No | Target to verify (URL, command, window name) |
| `--adapter` | No | Capture adapter (auto-detected if not specified) |
| `--batch` | No | Directory of captures to batch verify |
| `--captures` | No | Specific capture files to verify |
| `--detailed` | No | Include per-capture analysis |
| `--check-todos` | No | Check if TodoWrite state indicates verification needed |

## Examples

```bash
# Auto-detect target from task file
/tool-reader:verify-tool login-feature

# Specify target explicitly
/tool-reader:verify-tool login-feature --target http://localhost:3000
/tool-reader:verify-tool tui-panel --target "cargo run"
/tool-reader:verify-tool desktop-app --target window:MyApp

# Use specific adapter
/tool-reader:verify-tool web-feature --adapter playwright
/tool-reader:verify-tool terminal-app --adapter tui

# Batch verify captures
/tool-reader:verify-tool user-flow --batch .tool-reader/tool-reader:captures/
/tool-reader:verify-tool user-flow --batch .tool-reader/tool-reader:captures/ --detailed

# Verify specific captures
/tool-reader:verify-tool login --captures screenshot1.png screenshot2.png

# Check if todos indicate verification needed
/tool-reader:verify-tool feature --check-todos
```

## Adapters

| Adapter | Target Types | Features |
|---------|--------------|----------|
| `playwright` | http://, https:// | Event-based, sequences, DOM capture |
| `browser` | http://, https:// | Headless screenshot (fallback) |
| `tui` | tui:, terminal apps | ANSI capture, input, keys |
| `gui` | window:, .exe | Window screenshot |
| `cli` | commands | stdout/stderr capture |
| `auto` | Any | Auto-detect based on target |

## Target Formats

```bash
# Web targets
--target http://localhost:3000
--target https://example.com

# TUI targets
--target "cargo run"
--target "tui:npm run dev"

# GUI targets
--target window:MyAppTitle
--target "gui:app.exe|Window Title"

# CLI targets
--target "cli:npm test"
--target "python script.py"
```

## Event-Based Capture

When using Playwright adapter, capture on specific events:

```bash
# Capture after clicking element
/tool-reader:verify-tool login --adapter playwright --capture-on click:#submit-btn

# Capture sequence
/tool-reader:verify-tool user-flow --adapter playwright --sequence "
  screenshot
  click:#login-btn
  input:#email=test@example.com
  input:#password=secret
  click:#submit
  navigate
  screenshot
"
```

## Batch Verification

Verify multiple captures in a single Claude call:

```bash
# Summary mode (default)
/tool-reader:verify-tool feature --batch ./tool-reader:captures/

# Detailed per-image analysis
/tool-reader:verify-tool feature --batch ./tool-reader:captures/ --detailed
```

### Batch Output (Summary)

```
BATCH VERIFICATION: 5 captures
==================================================
  PASSED:    4/5
  FAILED:    1/5

Issues Found:
  - Capture 3: Submit button not visible

Overall: partial
Recommendation: Fix viewport scroll issue
```

### Batch Output (Detailed)

```
### Capture 1: login_initial.png
Status: PASS
Evidence: Login form visible with email/password fields
Verified: [x] Login page renders

### Capture 2: login_filled.png
Status: PASS
Evidence: Form fields populated correctly

### Capture 3: login_submit.png
Status: FAIL
Evidence: Submit button below viewport
Issues: - Button may require scroll
```

## Todo Integration

Check if TodoWrite state indicates verification is needed:

```bash
/tool-reader:verify-tool feature --check-todos
```

### Verification Triggers

Verification auto-triggers when:
1. All todos in a phase (implement/test/build) completed
2. Todo containing "verify", "test", "check", "build" completed
3. All todos marked complete (final verification)

## Task File Format

```markdown
# My Feature Task

## Target
[webapp]: http://localhost:3000
# or: [tui]: cargo run
# or: [gui]: app.exe|Window Title

## Acceptance Criteria
- Login form displays email and password fields
- Submit button is visible and clickable
- Error messages appear in red

## Checklist
- [ ] Login page renders correctly
- [ ] Form validates input
- [x] Already completed item
```

## Integration with Capture Hook

Accept external screenshots for verification:

```bash
# Add external capture
python capture_hook.py add screenshot.png --event "clicked login"

# Verify all pending captures
/tool-reader:verify-tool feature --batch .tool-reader/tool-reader:captures/
```

## Notes

- **All picture verifications use Claude Sonnet model** for consistent, high-quality analysis
- Adapters auto-detect based on target format
- Playwright adapter preferred for web (falls back to browser if unavailable)
- Batch verification sends all captures in single Claude call
- Use `--detailed` for per-capture analysis
- Todo integration reads from Claude's TodoWrite state
