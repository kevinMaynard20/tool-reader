# /tool-reader:verify-tool

Visual verification using ACTUAL SCREENSHOTS analyzed by Claude Sonnet.

## CRITICAL: How This Works

**YOU MUST run the visual_verifier.py script. DO NOT manually curl HTML or fake verification.**

```bash
# Run the Python script - this captures a REAL screenshot
python <plugin-path>/scripts/visual_verifier.py <task-file> --target <url>
```

The script will:
1. Launch headless Chrome/Edge (COMPLETELY INVISIBLE - no window popup)
2. Capture an actual PNG screenshot (no user disruption)
3. Pass the PNG to `claude --model sonnet` for visual analysis
4. Return verification results

**All captures run invisibly:**
- Webapp: Headless browser (--headless=new), no window shown
- GUI: Minimized window, no focus steal, PrintWindow API
- TUI: Background subprocess, CREATE_NO_WINDOW flag

**NEVER:**
- Use `curl` to save HTML (this is NOT visual verification)
- Manually analyze HTML source
- Skip the screenshot capture step
- Fake verification results

## Usage

```bash
/tool-reader:verify-tool <task-name>
/tool-reader:verify-tool <task-name> --target <url>
```

## Implementation Steps

When this command is invoked, execute these steps:

### Step 1: Locate the script
```bash
# The script is in the tool-reader plugin directory
# Usually: plugins/tool-reader/scripts/visual_verifier.py
```

### Step 2: Run the script
```bash
python visual_verifier.py ".claude/<task-name>.md" --target "http://localhost:3000"
```

### Step 3: The script captures screenshot
The script uses headless browser to capture actual PNG:
- Uses Edge or Chrome in `--headless=new` mode
- Saves screenshot to temp directory
- Screenshot is a real rendered image, NOT HTML

### Step 4: Script sends to Sonnet
The script calls:
```bash
claude -p "<verification prompt with image path>" --model sonnet
```

### Step 5: Return results
Script outputs verification results showing which items passed/failed.

## Example Execution

```
> /tool-reader:verify-tool API_FEATURE_TASK --target http://localhost:3000

Running visual verification...
  Script: visual_verifier.py
  Task: .claude/API_FEATURE_TASK.md
  Target: http://localhost:3000

Step 1: Capturing screenshot with headless browser...
  Browser: Edge (headless)
  Screenshot: C:\Users\...\screenshot_1234.png
  Size: 1280x720

Step 2: Sending to Claude Sonnet for analysis...
  Model: sonnet
  Image: screenshot_1234.png

Step 3: Verification Results:
==================================================
  PASSED: Search form visible on dashboard
  PASSED: Search results section present
  PASSED: Input field and button rendered
==================================================
  Overall: 3/3 items verified visually
  Screenshot saved: .tool-reader/captures/API_FEATURE_TASK_1234.png
```

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `task-name` | Yes | Task file name in .claude/ directory |
| `--target` | No | URL to capture (reads from task file if not specified) |

## Script Location

The visual_verifier.py script is at:
```
~/.claude/plugins/tool-reader/plugins/tool-reader/scripts/visual_verifier.py
```

On Windows:
```
%USERPROFILE%\.claude\plugins\tool-reader\plugins\tool-reader\scripts\visual_verifier.py
```

If the script is not found, inform the user to install the tool-reader plugin.

## What the Script Does (visual_verifier.py)

```python
# 1. Find browser (Edge or Chrome)
browser_path = find_browser()  # Returns path to msedge.exe or chrome.exe

# 2. Capture screenshot with headless browser
# Uses --headless=new --screenshot flags
capture_screenshot_webapp(url, output_path)  # Saves actual PNG

# 3. Call Claude CLI with Sonnet model
subprocess.run([
    "claude", "-p", prompt,
    "--output-format", "text",
    "--model", "sonnet"  # MUST use Sonnet for image analysis
])

# 4. Parse and return results
```

## Troubleshooting

**"Screenshot not created"**
- Ensure Edge or Chrome is installed
- Check browser path in script output

**"Claude CLI not found"**
- Ensure `claude` is in PATH
- Run `claude --version` to verify

**"Sonnet model error"**
- Ensure you have access to Sonnet model
- Check Claude CLI authentication

## Notes

- **ALWAYS captures actual PNG screenshot** - never HTML
- **ALWAYS uses Claude Sonnet** for image analysis
- Screenshot saved to .tool-reader/captures/ for reference
- Headless browser runs invisibly (no window popup)
- Works with Edge or Chrome on Windows
