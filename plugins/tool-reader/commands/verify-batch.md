# /verify-batch

Verify multiple captures in a single Claude call.

## Usage

```bash
/verify-batch <capture-dir>
/verify-batch <capture-dir> --task <task-name>
/verify-batch <capture-dir> --detailed
/verify-batch <path1> <path2> ...
```

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `capture-dir` | Yes | Directory containing captures OR list of paths |
| `--task` | No | Task file to verify against |
| `--detailed` | No | Include per-capture analysis |
| `--summary` | No | Summary only (default) |
| `--json` | No | Output as JSON |

## Examples

```bash
# Verify all captures in directory (summary)
/verify-batch .tool-reader/captures/

# Verify with task context
/verify-batch .tool-reader/captures/ --task login-feature

# Detailed per-capture analysis
/verify-batch .tool-reader/captures/ --detailed

# Verify specific files
/verify-batch screenshot1.png screenshot2.png screenshot3.png

# JSON output for automation
/verify-batch .tool-reader/captures/ --json
```

## Output: Summary Mode (Default)

```
============================================================
BATCH VERIFICATION: 5 captures
============================================================

  PASSED:    4/5
  FAILED:    1/5

Issues Found:
  - Capture 3: Submit button not visible after form fill

------------------------------------------------------------
Overall: partial
Recommendation: Fix viewport scroll issue before submit
============================================================
```

## Output: Detailed Mode

```
============================================================
BATCH VERIFICATION: 5 captures
============================================================

  PASSED:    4/5
  FAILED:    1/5

Issues Found:
  - Capture 3: Submit button not visible

------------------------------------------------------------
DETAILED RESULTS
------------------------------------------------------------

### Capture 1: login_initial.png
Status: PASS
Evidence: Login form visible with email and password fields
Verified:
  [x] Login page renders correctly
  [x] Form fields present

### Capture 2: login_email.png
Status: PASS
Evidence: Email field populated with test@example.com

### Capture 3: login_submit.png
Status: FAIL
Evidence: Submit button below viewport, not visible
Issues:
  - Button may require scroll to view
  - Viewport height may be insufficient

### Capture 4: login_error.png
Status: PASS
Evidence: Error message displayed in red as expected
Verified:
  [x] Error messages show in red

### Capture 5: login_success.png
Status: PASS
Evidence: Dashboard visible after successful login
Verified:
  [x] Successful login redirects to dashboard

------------------------------------------------------------
Overall: partial
Recommendation: Increase viewport height or scroll before submit
============================================================
```

## Output: JSON Mode

```json
{
  "total": 5,
  "passed": 4,
  "failed": 1,
  "uncertain": 0,
  "issues": ["Capture 3: Submit button not visible"],
  "details": [
    {
      "image": "login_initial.png",
      "status": "pass",
      "evidence": "Login form visible",
      "verified": ["Login page renders"],
      "issues": []
    },
    ...
  ],
  "summary": "Overall: partial\nRecommendation: Fix viewport"
}
```

## Task Context

When --task is provided, verification uses the task's acceptance criteria:

```bash
/verify-batch .tool-reader/captures/ --task login-feature
```

The task file (.claude/login-feature.md) provides:
- Checklist items to verify
- Acceptance criteria
- Expected behavior

## How It Works

1. Collects all capture files from directory or args
2. Builds verification prompt with task criteria
3. Sends all images to Claude in single request
4. Parses response into pass/fail per capture
5. Returns summary + optional detailed analysis

## Supported File Types

| Extension | Type | Handling |
|-----------|------|----------|
| .png, .jpg, .jpeg | Image | Visual analysis |
| .gif, .webp | Image | Visual analysis |
| .txt | Text | Content analysis |
| .html | DOM | Structure analysis |

## Notes

- **All picture verifications use Claude Sonnet model** for consistent, high-quality analysis
- Single Claude call for efficiency (vs multiple calls)
- Summary mode is default (faster, less detail)
- Use --detailed for per-capture analysis
- JSON mode useful for CI/automation
- Task context improves verification accuracy
