# /tool-reader:setup-tool-reader

Initialize or update tool-reader configuration in the current project. This command is **idempotent** - run it multiple times safely.

## Usage

```bash
/tool-reader:setup-tool-reader
/tool-reader:setup-tool-reader --target <url|command>
/tool-reader:setup-tool-reader --adapter <browser|tui|gui|cli>
```

## What This Command Does

1. Detect project type from config files
2. Add Tool Reader Configuration section to CLAUDE.md
3. Create .tool-reader/ directory structure
4. Create .claude/ directory for task files

## Idempotent Behavior

Before modifying CLAUDE.md:
1. Check for existing `## Tool Reader Configuration`
2. If exists: Update only what changed
3. If missing: Add full configuration block

## Configuration Block to Add to CLAUDE.md

When setting up a project, add this to CLAUDE.md:

```markdown
---

## Tool Reader Configuration

tool-reader: enabled
tool-reader-adapter: {adapter}
tool-reader-target: {target}
visual-verifier-script: ~/.claude/plugins/tool-reader/plugins/tool-reader/scripts/visual_verifier.py

---

## VISUAL VERIFICATION REQUIREMENTS

### CRITICAL: Verification Must Be a Tracked Task

**Every visual verification MUST be tracked as a separate task:**

**Option 1: Add to TodoWrite**
```
TodoWrite: [
  ...existing todos...,
  { "content": "Run visual verification for <phase>", "status": "pending", "activeForm": "Running visual verification" }
]
```

**Option 2: Create verification task file**
Create `.claude/VERIFY_<feature>.md`:
```markdown
# Visual Verification: <feature>

## Target
[webapp]: {target}

## Items to Verify
- [ ] <item 1>
- [ ] <item 2>

## Run Command
python "{visual-verifier-script}" ".claude/VERIFY_<feature>.md" --items "<items>"
```

### When to Create Verification Tasks

Create a verification task:
1. **After completing any phase** (Implementation, UI, Testing)
2. **After completing ALL items** in a task file
3. **Before marking a feature as done**

### How to Run Visual Verification

Execute this Python script (as a tracked task):

```bash
python "~/.claude/plugins/tool-reader/plugins/tool-reader/scripts/visual_verifier.py" "<task-file>" --items "<items to verify>"
```

Windows:
```bash
python "%USERPROFILE%\.claude\plugins\tool-reader\plugins\tool-reader\scripts\visual_verifier.py" "<task-file>" --items "<items to verify>"
```

### What the Script Does

1. Launches headless Edge/Chrome (COMPLETELY INVISIBLE - no window popup)
2. Captures ACTUAL PNG screenshot (no user disruption)
3. Sends PNG to Claude Sonnet for analysis
4. Returns pass/fail results

**All captures run invisibly:**
- Webapp: Headless browser (--headless=new), no window shown
- GUI: Minimized window, no focus steal, PrintWindow API
- TUI: Background subprocess, CREATE_NO_WINDOW flag

### STRICT RULES

**YOU MUST:**
- Create a tracked task (TodoWrite or .md file) for each verification
- Run the Python script as that tracked task
- Mark verification task complete only after script runs
- Let the script capture an actual PNG screenshot
- Let Sonnet analyze the image

**YOU MUST NEVER:**
- Run verification without tracking it as a task
- Use `curl` to save HTML (NOT visual verification)
- Analyze HTML source (NOT visual verification)
- Skip verification after completing a phase
- Fake verification results
- Claim verification done without running the script

---

## To Remove Tool Reader

Run `/tool-reader:stop-tool-reader` to remove this configuration from CLAUDE.md.
```

## Auto-Detection

| Files Found | Project Type | Default Adapter |
|-------------|--------------|-----------------|
| package.json (vite/next/react) | webapp | browser |
| package.json (express/fastify) | api | browser |
| Cargo.toml (ratatui/tui-rs) | tui | tui |
| Cargo.toml (iced/egui/tauri) | gui | gui |
| pyproject.toml | python | cli |

## Examples

```bash
# Auto-detect everything
/tool-reader:setup-tool-reader

# Specify target
/tool-reader:setup-tool-reader --target http://localhost:3000

# TUI project
/tool-reader:setup-tool-reader --adapter tui --target "cargo run"
```

## Output

```
## Tool Reader Setup Complete

Configuration added to CLAUDE.md

Project: my-project
Type: webapp
Adapter: browser
Target: http://localhost:3000

Visual verification MUST be tracked as a task:
- Add to TodoWrite, OR
- Create .claude/VERIFY_<feature>.md

Script: ~/.claude/plugins/tool-reader/plugins/tool-reader/scripts/visual_verifier.py

To remove: /tool-reader:stop-tool-reader
```

## Notes

- **Idempotent**: Safe to run multiple times
- **Verification is a tracked task** - must be in TodoWrite or .md file
- **Task files stay generic** - no tool-reader references needed
- **Actual screenshots** - script captures PNG, NOT curl/HTML
- **Sonnet analyzes** - image sent to Claude Sonnet model
- **To remove**: Run /tool-reader:stop-tool-reader
