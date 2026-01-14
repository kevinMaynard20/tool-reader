# /run-tool

Execute a task definition from `.claude/<name>.md` with optional visual verification.

## Usage

```
/run-tool <name>
/run-tool <name> --verify        # Verify completion with screenshots
/run-tool <name> --verify-each   # Verify after each item
```

Examples:
```
/run-tool PLUGIN_TASK
/run-tool auth-task --verify
/run-tool deploy --verify-each
```

## What It Does

1. Reads `.claude/<name>.md` (or `.claude/<name>` if already includes extension)
2. Parses the task file for checklist items
3. Detects app type (`[webapp]`, `[gui]`, `[tui]`) for visual verification
4. Identifies uncompleted items (`[ ]`)
5. Executes each item sequentially
6. **Captures invisible screenshots** (no window shown, no focus steal)
7. **Verifies with Claude CLI** before marking complete
8. Marks items as `[x]` only when verified
9. Reports progress after each item

## Execution Flow

### Standard Execution
```
> /run-tool PLUGIN_TASK

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

### With Visual Verification (--verify)
```
> /run-tool webapp-task --verify

Reading task: .claude/webapp-task.md
Found 10 items (5 completed, 5 remaining)
Detected: [webapp] http://localhost:3000

Executing remaining items:

[6/10] Login page renders correctly
  - Working...
  - Done!

[7/10] Form validation works
  - Working...
  - Done!

Running visual verification (invisible capture)...
  - Launching headless browser...
  - Capturing screenshot (user sees nothing)...
  - Sending to Claude CLI...

Verification Results:
  ✓ Login page renders correctly - Form visible
  ✓ Form validation works - Error messages present
  ✗ Dashboard loads - Still on login page

Verified: 2/3 items
Screenshot: /tmp/tool-reader/webapp-task_1234567890.png
```

### Verify Each Item (--verify-each)
```
> /run-tool webapp-task --verify-each

Reading task: .claude/webapp-task.md
Found 5 items (2 completed, 3 remaining)
Detected: [webapp] http://localhost:3000

[3/5] Login page renders correctly
  - Working...
  - Capturing invisible screenshot...
  - Verifying with Claude...
  - ✓ Verified complete

[4/5] Dashboard loads after login
  - Working...
  - Capturing invisible screenshot...
  - Verifying with Claude...
  - ✗ Not verified - still on login page

Stopped at item 4/5 - verification failed
Screenshot: /tmp/tool-reader/webapp-task_1234567891.png
```

## Task Item Format

The plugin recognizes these checklist formats:

```markdown
- [ ] Uncompleted item
- [x] Completed item
* [ ] Also works with asterisks
* [x] Completed with asterisk

| # | Task | Done |
|---|------|------|
| 1 | Task name | [ ] |
| 2 | Another task | [x] |
```

## Behavior

- **Sequential Execution**: Items are executed in order
- **Auto-Update**: The `.md` file is updated as items complete
- **Error Handling**: If an item fails, execution stops and status is reported
- **Resumable**: Run the command again to continue from where you left off

## App Type Detection

Add markers to your task file to enable visual verification:

```markdown
# For web applications (uses headless Chrome/Edge)
[webapp]: http://localhost:3000

# For GUI applications (launches hidden window)
[gui]: myapp.exe

# For TUI/CLI applications (captures terminal output)
[tui]: npm run dev
```

## Invisible Capture Techniques

All visual captures happen **without user disruption**:

- **Webapps**: Headless Chrome/Edge (`--headless=new`) - completely invisible
- **GUI Apps**: PowerShell hidden window launch - no taskbar, no focus steal
- **TUI Apps**: Background cmd.exe with output capture - silent

The user can continue working normally while verification happens.

## Example Task File

```markdown
# My Web App Task

## Application

[webapp]: http://localhost:3000

## Acceptance Criteria

- Login form has email and password fields
- Submit button is visible and clickable
- Error messages display in red

## Checklist

- [ ] Login page renders correctly
- [ ] Form validation works
- [x] Already done step
- [ ] Dashboard loads after login
```

## Notes

- The `<name>` parameter should match the filename without `.md` extension
- If the file doesn't exist, an error is shown
- If all items are complete, a success message is shown
- Use `--verify` to enable visual verification via Claude CLI
- Use `--verify-each` to verify after each individual item
- **All visual captures are invisible** - no window shown, no focus stealing
- Screenshots are saved for debugging verification failures

## Requirements

- **Claude CLI** (`claude` command) must be in PATH for verification
- **Edge or Chrome** browser for webapp screenshots
- **PowerShell** for invisible window management (Windows)
