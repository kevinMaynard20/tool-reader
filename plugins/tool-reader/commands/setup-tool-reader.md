# /setup-tool-reader

Initialize tool-reader auto-verification in the current project with **Claude todo integration** for phase-based verification triggers.

## Usage

```
/setup-tool-reader [url]
/setup-tool-reader --tui          # Configure for Rust TUI project
/setup-tool-reader --todo-verify  # Enable todo-based verification only
```

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `url` | No | Dev server URL (auto-detected if not provided) |
| `--tui` | No | Configure for TUI/terminal app verification |
| `--todo-verify` | No | Enable Claude todo integration without visual verification |

## Examples

```
/setup-tool-reader
/setup-tool-reader http://localhost:5173
/setup-tool-reader http://localhost:3000
/setup-tool-reader --tui
```

## What It Does

1. **Check for CLAUDE.md** - Look for existing project config
2. **Detect App Type** - Scan for package.json, Cargo.toml, etc.
3. **Find Dev Server** - Check common ports (3000, 5173, 8080)
4. **Configure Todo Integration** - Enable phase-based verification triggers
5. **Add Config** - Append auto-verify config to CLAUDE.md
6. **Setup .md File Detection** - Configure detection of task instructions in .md files

## Implementation Steps

When `/setup-tool-reader` is invoked:

### Step 1: Check for existing CLAUDE.md
```python
claude_md = Path("CLAUDE.md")
if claude_md.exists():
    content = claude_md.read_text()
    if "tool-reader: auto-verify" in content:
        print("Auto-verify already configured!")
        return
```

### Step 2: Detect project type
```python
if Path("package.json").exists():
    project_type = "webapp"
    # Check for framework
    pkg = json.loads(Path("package.json").read_text())
    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
    if "next" in deps: framework = "Next.js"
    elif "vue" in deps: framework = "Vue"
    elif "react" in deps: framework = "React"
elif Path("Cargo.toml").exists():
    # Check if it's a TUI app
    cargo = Path("Cargo.toml").read_text()
    if "ratatui" in cargo or "tui" in cargo or "crossterm" in cargo:
        project_type = "tui"
        app_type = "TUI"
    else:
        project_type = "cli"
        app_type = "CLI"
```

### Step 3: Detect running dev server (for webapps)
```python
import socket
for port in [3000, 5173, 8080, 4200]:
    sock = socket.socket()
    if sock.connect_ex(('localhost', port)) == 0:
        detected_url = f"http://localhost:{port}"
        break
```

### Step 4: Generate config with todo integration
```python
config = f"""
## Tool Reader Auto-Verification

tool-reader: auto-verify
tool-reader-type: {project_type}
{"tool-reader-url: " + (url or detected_url) if project_type == "webapp" else "tool-reader-command: cargo run"}

### Claude Todo Integration

When Claude uses TodoWrite to track tasks, tool-reader automatically triggers verification at:

1. **Phase Boundaries** - When all todos in implementation/testing/build phase complete
2. **Verification Todos** - When todos with "verify", "test", "check", "build" complete
3. **Final Verification** - When all todos are marked complete

### .md File Instruction Detection

When user prompts reference .md files (e.g., "follow TASK.md", "do instructions in spec.md"):
- Parse the .md file for task checklists
- Track completion via TodoWrite
- Auto-verify at phase boundaries

### Verification Triggers

Claude should run `/verify-tool` when:
- A phase of work (implement, test, build) completes
- A todo containing verification keywords is marked done
- User explicitly requests verification
- Working through .md file instructions and completing sections

### Auto-Verify Files

After editing these files, verify changes:
{"- *.tsx, *.jsx, *.vue, *.svelte" if project_type == "webapp" else "- src/**/*.rs"}
{"- *.css, *.scss, *.sass" if project_type == "webapp" else "- Cargo.toml"}
"""
```

### Step 5: Update CLAUDE.md
```python
if claude_md.exists():
    # Append to existing
    with open(claude_md, "a") as f:
        f.write("\n" + config)
else:
    # Create new
    full_content = f"# {project_name}\n\n{config}"
    claude_md.write_text(full_content)
```

## Output

```markdown
## Tool Reader Setup Complete

**Project**: kevin-code
**Type**: tui (Rust/ratatui)
**Command**: cargo run

Added to CLAUDE.md:
```
tool-reader: auto-verify
tool-reader-type: tui
tool-reader-command: cargo run
```

### Todo Integration Enabled

Claude will auto-trigger verification when:
- Implementation phase completes
- Testing phase completes
- Build phase completes
- Any verification-related todo completes
- All todos marked complete

### .md File Instruction Support

When following instructions from .md files:
- Checklists are tracked via TodoWrite
- Verification runs at section/phase boundaries
- Progress is reported with visual confirmation

Commands available:
- `/verify-tool <task>` - Verify a task visually
- `/verify-tool <task> --check-todos` - Check if verification needed based on todos
- `/save-baseline <name>` - Save current UI/output as baseline
- `/compare-baseline <name>` - Compare against baseline
```

## TUI Verification Configuration

For Rust TUI applications (ratatui, crossterm, tui-rs):

```markdown
## TUI Verification

[tui]: cargo run

### Verification Points

Run TUI verification at:
1. End of implementation phase
2. After UI component changes
3. Before committing UI changes
4. When "verify", "test", or "check" todos complete

### Capture Method

- Runs `cargo run` with test input
- Captures terminal output
- Sends to Claude for visual analysis
- Compares against expected behavior
```

## Phase-Based Verification Rules

The setup configures these verification triggers:

| Phase | Trigger Condition | Verification Action |
|-------|-------------------|---------------------|
| Implementation | All "implement/create/add" todos done | Visual check of new UI/output |
| Testing | All "test/spec" todos done | Run tests + visual verify |
| Build | "build/compile" todo done | Build output + app verification |
| Deploy | "deploy/release" todo done | Production verification |
| Review | All todos complete | Final comprehensive check |

## .md File Instruction Detection

When Claude detects user is working from an .md instruction file:

### Detection Patterns
- "follow instructions in X.md"
- "do the tasks in SPEC.md"
- "complete TASK.md"
- "work through README.md tasks"

### Behavior
1. Parse the .md file for checklist items (`- [ ]` / `- [x]`)
2. Create corresponding TodoWrite entries
3. Track completion as items are done
4. Auto-trigger verification at:
   - Section boundaries (## headings)
   - Phase completions (all items under a heading done)
   - File completion (all items done)

### Example

User: "Complete the tasks in .claude/FEATURE.md"

Claude will:
1. Read .claude/FEATURE.md
2. Parse checklist items into todos
3. Work through each item
4. Run verification when:
   - Each section completes
   - Verification-related items complete
   - All items complete

## Notes

- Creates `.claude/` directory if it doesn't exist
- Won't duplicate config if already present
- Auto-detects Rust TUI projects (ratatui, crossterm, tui-rs)
- Auto-detects webapp frameworks (React, Vue, Next.js, Svelte)
- Todo integration works with Claude's built-in TodoWrite system
- URL/command can be overridden manually later in CLAUDE.md
- .md file detection is automatic when user references task files
