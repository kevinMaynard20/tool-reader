# /compare-baseline

Compare the current UI state against a saved baseline to detect visual regressions.

## Usage

```
/compare-baseline <name>
```

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `name` | Yes | Name of the baseline to compare against |

## Examples

```
/compare-baseline login-page
/compare-baseline dashboard
/compare-baseline settings-modal
```

## What It Does

1. **Load Baseline** - Retrieves saved baseline from `.claude/baselines/`
2. **Capture Current** - Takes new invisible screenshot of current state
3. **Compare with Claude** - Uses Claude CLI to analyze visual differences
4. **Report Results** - Shows diff analysis and suggested fixes

## Output

### Match (No Regressions)

```markdown
## Comparison Result

**Status**: MATCH
**Similarity**: 98.5%
**Baseline**: .claude/baselines/login-page_1705312200.png
**Current**: .claude/baselines/current_login-page_1705400000.png

No visual regressions detected. UI matches baseline.
```

### Mismatch (Regressions Found)

```markdown
## Comparison Result

**Status**: MISMATCH
**Similarity**: 72.3%
**Baseline**: .claude/baselines/login-page_1705312200.png
**Current**: .claude/baselines/current_login-page_1705400000.png

### Differences Found
- Button text changed from "Login" to "Sign In"
- Form padding reduced on left side
- Error message styling differs (red vs orange)

### Suggested Fixes
- Revert button text in LoginForm.tsx:42
- Check padding values in login.css:15
- Verify error color variable in theme.ts

### Analysis
The login form has visual changes that may be intentional updates or regressions.
The button text change appears intentional. The padding and error styling
differences may be unintended side effects of recent CSS changes.
```

## Workflow Integration

When auto-verify is enabled (`tool-reader: auto-verify` in CLAUDE.md):

1. After editing UI files, Tool Reader automatically compares against baselines
2. If regressions detected, attempts auto-fix
3. Reports results without interrupting your workflow

## Notes

- Requires baseline to exist (use `/save-baseline` first)
- Comparison uses Claude's vision capabilities
- Current screenshots saved for debugging
- All captures are invisible - no windows steal focus
