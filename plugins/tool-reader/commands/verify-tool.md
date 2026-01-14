# /verify-tool

Visually verify task completion from `.claude/<name>.md` using invisible screenshots and Claude CLI.

**Now integrates with Claude's built-in TodoWrite/task system** to automatically trigger verification at phase boundaries and during verification steps.

## Usage

```
/verify-tool <name>
/verify-tool <name> --visual   # Force visual verification
/verify-tool <name> --status   # Status only (no visual capture)
/verify-tool <name> --check-todos   # Check if todos indicate verification needed
/verify-tool <name> --todos '<json>'  # Provide todo state for auto-trigger
```

Examples:
```
/verify-tool PLUGIN_TASK
/verify-tool auth-task --visual
/verify-tool deploy --status
```

## What It Does

1. Reads `.claude/<name>.md` (or `.claude/<name>` if already includes extension)
2. Detects app type from markers: `[webapp]`, `[gui]`, or `[tui]`
3. **Launches application invisibly** (no window shown, no focus steal)
4. **Captures screenshot silently** using:
   - Headless Chrome/Edge for webapps
   - Hidden PowerShell process for GUI apps
   - Captured stdout for TUI apps
5. **Sends to Claude CLI** with task list for verification
6. Reports which items appear complete based on visual evidence

## Visual Verification Flow

```
> /verify-tool my-webapp-task

Reading task: .claude/my-webapp-task.md

## Task Info
- Total Items: 10
- Completed: 5
- Remaining: 5

## Application Detection
- Type: WEBAPP
- URL: http://localhost:3000

## Invisible Capture
- Launching headless browser...
- Capturing screenshot (user sees nothing)...
- Screenshot saved: /tmp/tool-reader/my-webapp-task_1234567890.png

## Claude Verification
Sending screenshot + task list to Claude CLI...

## Results

| Task | Status | Evidence |
|------|--------|----------|
| Login page renders | COMPLETED | Form fields visible |
| Submit button works | COMPLETED | Button present |
| Dashboard loads | NOT_COMPLETED | Still on login page |
| User name displays | UNCERTAIN | Cannot determine |

### Summary
- Verified Complete: 2
- Not Complete: 1
- Uncertain: 1
- Screenshot: /path/to/screenshot.png
```

## App Type Detection

The command looks for these markers in your task file:

```markdown
# For web applications
[webapp]: http://localhost:3000

# For GUI applications
[gui]: myapp.exe

# For TUI/CLI applications
[tui]: npm run dev
```

If no marker is found, it auto-detects based on content:
- URLs like `http://` or `localhost` → WEBAPP
- `.exe` or `window` mentions → GUI
- `terminal`, `cli`, `console` mentions → TUI

## Invisible Capture Techniques

### Webapps (Headless Browser)

Uses Edge or Chrome in `--headless=new` mode:
- **Completely invisible** - no browser window ever appears
- **No focus steal** - user can continue working
- **Silent** - no notifications or sounds
- Screenshot saved automatically

### GUI Apps (Hidden Window)

Uses PowerShell to launch with hidden window:
```powershell
$startInfo.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
$startInfo.CreateNoWindow = $true
```
- Window never becomes visible
- No taskbar entry
- No focus change

### TUI Apps (Background Process)

Runs command in hidden `cmd.exe`:
- Output captured to temp file
- No console window shown
- Text output sent to Claude instead of screenshot

## Task File Format

```markdown
# My Web App Task

## Application

[webapp]: http://localhost:3000

## Acceptance Criteria

- Login form should have email and password fields
- Submit button should be blue and centered
- Error messages show in red

## Checklist

- [ ] Login page renders correctly
- [ ] Form has proper validation
- [x] Already completed item
- [ ] Dashboard loads after login
```

## Output Format

### Visual Verification Output

```markdown
## Visual Verification: TASK.md

**Status**: IN_PROGRESS

| Metric | Count |
|--------|-------|
| Total Items | 10 |
| Completed | 5 |
| Remaining | 5 |

### App Configuration
- Type: WEBAPP
- URL: http://localhost:3000
- Capture: Headless Chrome (invisible)

### Verification Results

| Task | Status | Evidence |
|------|--------|----------|
| Login renders | COMPLETED | Form visible with fields |
| Form validates | COMPLETED | Error messages present |
| Dashboard loads | NOT_COMPLETE | Still on login page |

### Remaining Items (based on file):
1. [ ] Dashboard loads after login

### Screenshot
Saved: /tmp/tool-reader/TASK_1234567890.png
```

### Status-Only Output (--status flag)

```
> /verify-tool PLUGIN_TASK --status

## Task Verification: PLUGIN_TASK.md

**Status**: IN_PROGRESS

| Metric | Count |
|--------|-------|
| Total Items | 25 |
| Completed | 12 |
| Remaining | 13 |
| Progress | 48% |

### Remaining Items:
1. [ ] Create tool-reader plugin structure
2. [ ] Implement /list-tools
3. [ ] Implement /run-tool
...
```

## Status Values

- **NOT_STARTED**: 0 items completed
- **IN_PROGRESS**: Some items completed, some remaining
- **COMPLETE**: All items completed (100%)

## Requirements

- **Claude CLI** - `claude` command must be in PATH
- **Edge or Chrome** - For webapp screenshots (headless mode)
- **PowerShell** - For invisible window management (Windows)

## Claude Todo Integration

Tool-reader can now reference Claude's built-in TodoWrite/task system to determine when verification should occur. This enables **automatic verification triggers** at phase boundaries.

### When Verification Auto-Triggers

1. **Phase Completion** - When all todos in a phase (implementation, testing, build) are completed
2. **Verification Todos** - When a todo containing "verify", "test", "check", or "validate" is completed
3. **High-Priority Phases** - When build, test, or deploy phases complete
4. **Final Verification** - When all todos are marked complete

### Verification Keywords

Todos containing these keywords trigger verification when completed:
- `verify`, `test`, `check`, `validate`, `confirm`, `ensure`
- `build`, `run`, `deploy`, `launch`, `render`, `display`
- `ui`, `visual`, `screenshot`, `appearance`, `layout`

### Phase Detection

Todos are automatically categorized into phases:
- **Implementation**: implement, create, add, write, code, develop
- **Testing**: test, spec, unit, integration, e2e
- **Verification**: verify, check, validate, confirm
- **Build**: build, compile, bundle, package
- **Deploy**: deploy, release, publish, ship
- **Review**: review, pr, merge, commit

### Example: Todo-Triggered Verification

```
## Current Todos (from TodoWrite)
- [x] Implement login form
- [x] Add form validation
- [x] Verify login UI renders correctly  <- triggers verification
- [ ] Write unit tests
- [ ] Run build and fix errors

## Verification Check Output

TODO VERIFICATION CHECK
==================================================
Recommend Verify: True
Priority: normal
Phase: verification
Progress: 60%
Reason: Verification todo completed: Verify login UI renders correctly
Action: Run /verify-tool to visually confirm the completed work
```

### Programmatic Usage

```python
from visual_verifier import check_todos_for_verification, get_verification_recommendation

# Check if verification should trigger
todos_json = '{"todos": [{"content": "Build UI", "status": "completed"}, ...]}'
context = check_todos_for_verification(todos_json=todos_json)

if context.should_verify:
    recommendation = get_verification_recommendation(context)
    print(f"Verify needed: {recommendation['reason']}")
```

### CLI Usage with Todos

```bash
# Check if current todos indicate verification is needed
python visual_verifier.py task.md --check-todos --todos '{"todos":[...]}'

# Run verification with todo context in report
python visual_verifier.py task.md --todos '{"todos":[...]}'
```

## Notes

- The `<name>` parameter should match the filename without `.md` extension
- If the file doesn't exist, an error is shown
- If no app type is detected, falls back to status-only mode
- Screenshots are saved for debugging failed verifications
- **All operations are invisible** - user is never interrupted
- Use `--status` flag to skip visual verification
- Use `/run-tool` to actually execute uncompleted items
- Use `/list-tools` to see all available task files
- **Todo integration** automatically suggests when to verify based on task progress
