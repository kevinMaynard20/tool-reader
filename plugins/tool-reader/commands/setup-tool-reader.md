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
visual-verifier-script: {plugins-dir}/tool-reader/plugins/tool-reader/scripts/visual_verifier.py

---

## AUTOMATIC VISUAL VERIFICATION

**YOU MUST AUTOMATICALLY run visual verification at these points:**

1. **After completing any phase** (Implementation, UI, Testing, etc.)
2. **After completing ALL items** in a task file
3. **When target is a webapp/URL** - verify the UI renders correctly

### How to Run Visual Verification

Execute this Python script:

```bash
python "{visual-verifier-script}" "<task-file>" --items "<items to verify>"
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

### CRITICAL RULES

**YOU MUST:**
- Run the script automatically after each phase completes
- Run the script when all task items are done
- Let the script capture an actual PNG screenshot
- Let Sonnet analyze the image

**YOU MUST NEVER:**
- Use `curl` to save HTML (NOT visual verification)
- Analyze HTML source (NOT visual verification)
- Skip verification after completing a phase
- Fake verification results

---

## Phase Detection

When working on task files, detect phases by looking for:
- Headers like "### Implementation Phase", "### UI Phase", "### Testing Phase"
- Groups of related checklist items
- Section boundaries

After completing all items in a phase, AUTOMATICALLY run visual verification.
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

Visual verification will run AUTOMATICALLY:
- After each phase completes
- When all items are done
- Using actual PNG screenshots analyzed by Sonnet

Script: <plugins-dir>/tool-reader/plugins/tool-reader/scripts/visual_verifier.py
```

## Notes

- **Idempotent**: Safe to run multiple times
- **Task files stay generic** - no tool-reader references needed in task files
- **CLAUDE.md triggers verification** - tells Claude when to auto-verify
- **Actual screenshots** - script captures PNG, NOT curl/HTML
- **Sonnet analyzes** - image sent to Claude Sonnet model
