# /tool-reader:stop-tool-reader

Remove tool-reader configuration from CLAUDE.md. This disables automatic visual verification for the current project.

## Usage

```bash
/tool-reader:stop-tool-reader
/tool-reader:stop-tool-reader --keep-captures
```

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--keep-captures` | No | Keep .tool-reader/captures/ directory (default: remove) |

## What This Command Does

1. Read CLAUDE.md
2. Find and remove the `## Tool Reader Configuration` section
3. Find and remove the `## VISUAL VERIFICATION REQUIREMENTS` section
4. Optionally remove .tool-reader/ directory
5. Keep .claude/ directory (contains task files user may want)

## Implementation Steps

When executing this command:

### Step 1: Read CLAUDE.md
```bash
Read the current CLAUDE.md file
```

### Step 2: Remove Tool Reader sections
Remove these sections from CLAUDE.md:
- Everything from `## Tool Reader Configuration` to the next `---` or `##`
- Everything from `## VISUAL VERIFICATION REQUIREMENTS` to the next `---` or `##`

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
...

---

## VISUAL VERIFICATION REQUIREMENTS

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
  - Visual Verification Requirements section

Removed directories:
  - .tool-reader/captures/

Kept:
  - .claude/ (contains your task files)

To re-enable: /tool-reader:setup-tool-reader
```

### With --keep-captures

```
## Tool Reader Removed

Removed from CLAUDE.md:
  - Tool Reader Configuration section
  - Visual Verification Requirements section

Kept:
  - .tool-reader/captures/ (--keep-captures flag)
  - .claude/ (contains your task files)

To re-enable: /tool-reader:setup-tool-reader
```

## Notes

- **Safe**: Only removes tool-reader specific sections
- **Preserves .claude/**: Task files are kept
- **Reversible**: Run /tool-reader:setup-tool-reader to re-enable
- **Optional capture retention**: Use --keep-captures to keep screenshots
