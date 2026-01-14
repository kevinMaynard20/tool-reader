# /tool-reader:setup-tool-reader

Initialize or update tool-reader configuration in the current project. This command is **idempotent** - run it multiple times safely.

## Usage

```bash
/tool-reader:setup-tool-reader
/tool-reader:setup-tool-reader --target <url|command>
/tool-reader:setup-tool-reader --adapter <playwright|browser|tui|gui|cli|auto>
/tool-reader:setup-tool-reader --tools <tool1,tool2,...>
```

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--target` | No | Default target (URL or command) |
| `--adapter` | No | Preferred adapter (auto-detected if not specified) |
| `--tools` | No | Comma-separated list of tools being tested |
| `--capture-dir` | No | Directory for captures (default: .tool-reader/tool-reader:captures/) |

## What This Command Does

### First Run (No existing config)
1. Detect project type from config files
2. Add Tool Reader Configuration section to CLAUDE.md
3. Create .tool-reader/ directory structure
4. Create .claude/ directory for task files

### Subsequent Runs (Config exists)
1. **Check existing configuration** in CLAUDE.md
2. **Update targets** if new tools specified via --tools
3. **Update adapter** if different one specified
4. **Add missing sections** without duplicating existing ones
5. **Preserve custom edits** user made to config

## IMPORTANT: Idempotent Behavior

Before modifying CLAUDE.md, you MUST:

1. **Read existing CLAUDE.md** to check for `## Tool Reader Configuration` section
2. **If section exists**: Update only what changed, don't duplicate
3. **If section missing**: Add the full configuration block
4. **If tools changed**: Update the tool-reader-targets list

### Check Pattern
```
Look for: "## Tool Reader Configuration" in CLAUDE.md
- Found: Parse existing config, merge changes
- Not found: Add full config block
```

## Configuration Block to Add/Update

When adding to CLAUDE.md, use this exact format:

```markdown
---

## Tool Reader Configuration

tool-reader: enabled
tool-reader-adapter: {adapter}
tool-reader-targets:
  - {target1}
  - {target2}
tool-reader-capture-dir: .tool-reader/tool-reader:captures/

### MANDATORY: Visual Verification

**YOU MUST run `/tool-reader:verify-tool` at these points:**

1. **After completing each phase** in a task file
2. **When ANY checklist item contains "verify" or "visual"**
3. **At final task completion**
4. **When TodoWrite shows all phase items complete**

This is NOT optional. Visual verification confirms work is actually done.
All verifications use Claude Sonnet for image analysis.

### How to Verify

```bash
/tool-reader:verify-tool <task-name> --target <url|command>
```

### Verification Triggers from Todos

When your TodoWrite state shows:
- All items in a phase completed → RUN `/tool-reader:verify-tool`
- Item with "verify", "test", "visual" completed → RUN `/tool-reader:verify-tool`
- All items complete → RUN final `/tool-reader:verify-tool`

### When Adding New Tools to Test

If you add a new tool/target to test:
1. Update this CLAUDE.md's `tool-reader-targets` list
2. Create a task file in `.claude/<tool-name>_TASK.md`
3. Run `/tool-reader:setup-tool-reader --tools <updated-list>` to refresh config

### Commands

| Command | Purpose |
|---------|---------|
| `/tool-reader:verify-tool <task>` | Visual verification (REQUIRED at phase ends) |
| `/tool-reader:verify-tool <task> --target <url>` | Verify specific target |
| `/tool-reader:capture --target <url>` | Capture screenshot |
| `/tool-reader:verify-batch <dir>` | Batch verify captures |
| `/tool-reader:setup-tool-reader` | Update this configuration |
```

## Auto-Detection

| Files Found | Project Type | Default Adapter |
|-------------|--------------|-----------------|
| package.json (vite/next/react) | webapp | playwright/browser |
| package.json (express/fastify) | api | browser |
| Cargo.toml (ratatui/tui-rs) | tui | tui |
| Cargo.toml (iced/egui/tauri) | gui | gui |
| Cargo.toml (other) | cli | cli |
| pyproject.toml | python | cli |
| *.sln, *.csproj | dotnet | gui/cli |

## Examples

```bash
# First time setup - auto-detect everything
/tool-reader:setup-tool-reader

# Setup with specific target
/tool-reader:setup-tool-reader --target http://localhost:3000

# Setup for TUI testing
/tool-reader:setup-tool-reader --adapter tui --target "cargo run"

# Add multiple tools to test
/tool-reader:setup-tool-reader --tools "http://localhost:3000,cargo run --bin mytui"

# Update existing config with new tool
/tool-reader:setup-tool-reader --tools "http://localhost:3000,http://localhost:8080"
```

## Implementation Steps

When executing this command:

1. **Read CLAUDE.md** (create if doesn't exist)
2. **Check for existing config**:
   ```
   Search for "## Tool Reader Configuration"
   ```
3. **If exists - UPDATE mode**:
   - Parse existing tool-reader-targets
   - Merge with new --tools if provided
   - Update adapter if --adapter provided
   - Preserve user customizations
   - DO NOT duplicate sections
4. **If not exists - CREATE mode**:
   - Detect project type
   - Add full configuration block
   - Create .tool-reader/ and .claude/ directories
5. **Output summary** of what was added/updated

## Update Logic (Pseudocode)

```
read CLAUDE.md content
if "## Tool Reader Configuration" in content:
    # UPDATE MODE
    parse existing targets from tool-reader-targets
    if --tools provided:
        merge new tools with existing (no duplicates)
        update tool-reader-targets section
    if --adapter provided and different:
        update tool-reader-adapter line
    write updated CLAUDE.md
    print "Updated existing configuration"
else:
    # CREATE MODE
    detect project type
    build full config block
    append to CLAUDE.md
    create directories
    print "Created new configuration"
```

## Output

### First Run
```
## Tool Reader Setup Complete

Created new configuration in CLAUDE.md

Project: my-project
Type: webapp
Adapter: playwright
Targets:
  - http://localhost:3000
Capture Dir: .tool-reader/tool-reader:captures/

Created directories:
  - .tool-reader/tool-reader:captures/
  - .claude/

IMPORTANT: You MUST run /tool-reader:verify-tool after each phase!
```

### Subsequent Run (Update)
```
## Tool Reader Configuration Updated

Changes:
  - Added target: http://localhost:8080
  - Adapter unchanged: playwright

Current targets:
  - http://localhost:3000
  - http://localhost:8080

No duplicate sections added.
```

### No Changes Needed
```
## Tool Reader Configuration

No changes needed - configuration is up to date.

Current targets:
  - http://localhost:3000

Run /tool-reader:verify-tool <task> to verify your work.
```

## Notes

- **Idempotent**: Safe to run multiple times
- **Merges, doesn't duplicate**: Existing config is updated, not duplicated
- **Preserves customizations**: User edits to CLAUDE.md are preserved
- **Strict enforcement**: Config emphasizes MANDATORY verification
- **Self-updating**: When new tools added, update CLAUDE.md targets
