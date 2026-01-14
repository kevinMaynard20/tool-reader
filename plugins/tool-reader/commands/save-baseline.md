# /save-baseline

Save the current UI state as a baseline for future regression testing.

## Usage

```
/save-baseline <name> [description]
```

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `name` | Yes | Name for this baseline (e.g., "login-page", "dashboard") |
| `description` | No | Optional description of what this baseline represents |

## Examples

```
/save-baseline login-page
/save-baseline dashboard "After adding user stats widget"
/save-baseline settings-modal "Dark mode styling complete"
```

## What It Does

1. **Detect App Type** - Reads `.claude/*.md` for `[webapp]`, `[gui]`, or `[tui]` marker
2. **Capture Screenshot** - Takes invisible screenshot using:
   - Headless Chrome/Edge for webapps
   - PrintWindow for GUI apps
   - Output capture for TUI apps
3. **Save to Baselines** - Stores in `.claude/baselines/<name>_<timestamp>.png`
4. **Update Manifest** - Records metadata in `.claude/baselines/manifest.json`

## Output

```markdown
## Baseline Saved

**Name**: login-page
**File**: login-page_1705312200.png
**Type**: webapp
**URL**: http://localhost:3000/login
**Created**: 2024-01-15T10:30:00Z

Screenshot saved to: .claude/baselines/login-page_1705312200.png
```

## Storage Structure

```
.claude/
└── baselines/
    ├── manifest.json
    ├── login-page_1705312200.png
    └── dashboard_1705312300.png
```

## Notes

- Baselines are used by `/compare-baseline` and auto-verification
- Saving a baseline with the same name replaces the previous one
- All captures are invisible - no windows steal focus
- For webapps, ensure dev server is running before saving
