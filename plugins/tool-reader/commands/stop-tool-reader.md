# /tool-reader:stop-tool-reader

Remove tool-reader configuration from CLAUDE.md. This disables automatic visual verification for the current project.

## Usage

```bash
/tool-reader:stop-tool-reader
/tool-reader:stop-tool-reader --keep-captures
/tool-reader:stop-tool-reader --keep-tools
```

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--keep-captures` | No | Keep .tool-reader/captures/ directory (default: remove) |
| `--keep-tools` | No | Keep installed testing tools (default: don't uninstall) |

## What This Command Does

1. Read CLAUDE.md
2. Find and remove the `## Tool Reader Configuration` section
3. Find and remove the `## Testing & Interaction Tools` section
4. Find and remove the `## VISUAL VERIFICATION REQUIREMENTS` section
5. Optionally remove .tool-reader/ directory
6. Keep .claude/ directory (contains task files user may want)
7. **Does NOT uninstall testing tools** (playwright, etc.) by default

## Sections Removed from CLAUDE.md

This command removes ALL tool-reader related sections:

| Section | Purpose |
|---------|---------|
| `## Tool Reader Configuration` | Core config (adapter, target, script path) |
| `## Testing & Interaction Tools` | Detected tools, interaction methods, install policy |
| `## VISUAL VERIFICATION REQUIREMENTS` | Rules for visual verification tasks |

## Implementation Steps

When executing this command:

### Step 1: Read CLAUDE.md
```bash
Read the current CLAUDE.md file
```

### Step 2: Remove Tool Reader sections
Remove these sections from CLAUDE.md:
- Everything from `## Tool Reader Configuration` to the next `---` or `##`
- Everything from `## Testing & Interaction Tools` to the next `---` or `##`
- Everything from `## VISUAL VERIFICATION REQUIREMENTS` to the next `---` or `##`

**Look for these markers:**
```markdown
tool-reader: enabled
tool-reader-adapter:
tool-reader-target:
tool-reader-auto-install:
visual-verifier-script:
```

### Step 3: Clean up directories (unless --keep-captures)
```bash
# Remove captures directory
rm -rf .tool-reader/captures/

# Remove .tool-reader/ if empty
rmdir .tool-reader/ 2>/dev/null || true
```

### Step 4: Write updated CLAUDE.md
Save the file without the tool-reader sections.

## Example

**Before:**
```markdown
# My Project

Some project info...

---

## Tool Reader Configuration

tool-reader: enabled
tool-reader-adapter: browser
tool-reader-target: http://localhost:3000
tool-reader-auto-install: confirm
visual-verifier-script: ~/.claude/plugins/tool-reader/...

---

## Testing & Interaction Tools

### Detected Tools
- [x] playwright (installed)
- [x] pytest (installed)

### How to Start the Application
- **Command**: npm run dev
- **URL**: http://localhost:3000

### Auto-Install Policy
tool-reader-auto-install: confirm

---

## VISUAL VERIFICATION REQUIREMENTS

### CRITICAL: Verification Must Be a Tracked Task
...rules...

---

## Other Section

Other content...
```

**After:**
```markdown
# My Project

Some project info...

---

## Other Section

Other content...
```

## Output

```
## Tool Reader Removed

Removed from CLAUDE.md:
  - Tool Reader Configuration section
  - Testing & Interaction Tools section
  - Visual Verification Requirements section

Removed directories:
  - .tool-reader/captures/

Kept:
  - .claude/ (contains your task files)
  - Installed testing tools (playwright, etc.)

To re-enable: /tool-reader:setup-tool-reader
```

### With --keep-captures

```
## Tool Reader Removed

Removed from CLAUDE.md:
  - Tool Reader Configuration section
  - Testing & Interaction Tools section
  - Visual Verification Requirements section

Kept:
  - .tool-reader/captures/ (--keep-captures flag)
  - .claude/ (contains your task files)
  - Installed testing tools (playwright, etc.)

To re-enable: /tool-reader:setup-tool-reader
```

## What This Command Does NOT Do

- **Does NOT uninstall testing tools** - Playwright, pytest-playwright, pyte, etc. remain installed
- **Does NOT remove .claude/ directory** - Your task files are preserved
- **Does NOT remove existing test files** - Your tests in tests/ or __tests__/ are untouched
- **Does NOT modify package.json or pyproject.toml** - Dependencies stay as-is

## Reinstalling

If you removed tool-reader and want it back:

```bash
/tool-reader:setup-tool-reader
```

This will:
1. Re-scan for testing tools (will find previously installed ones)
2. Re-add configuration sections to CLAUDE.md
3. Preserve any existing captures if you used --keep-captures

## Notes

- **Safe**: Only removes tool-reader specific sections from CLAUDE.md
- **Preserves .claude/**: Task files are kept
- **Preserves testing tools**: No uninstallation unless explicitly requested
- **Reversible**: Run /tool-reader:setup-tool-reader to re-enable
- **Optional capture retention**: Use --keep-captures to keep screenshots
