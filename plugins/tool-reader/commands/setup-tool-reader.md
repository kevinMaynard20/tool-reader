# /setup-tool-reader

Initialize tool-reader in the current project. Configures CLAUDE.md to **read from Claude's TodoWrite** and trigger verification based on todo state.

## Usage

```
/setup-tool-reader [url|command]
```

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `url` or `command` | No | Dev server URL or run command (auto-detected if not provided) |

## Examples

```
/setup-tool-reader
/setup-tool-reader http://localhost:5173
/setup-tool-reader "cargo run"
/setup-tool-reader "npm run dev"
```

## What It Does

1. **Detect Project Type** - Scan for package.json, Cargo.toml, pyproject.toml, etc.
2. **Find Dev Server/Command** - Auto-detect URL or run command
3. **Configure Todo Integration** - Tell CLAUDE.md to read from TodoWrite for verification triggers
4. **Add Config** - Append tool-reader config to CLAUDE.md

## Implementation Steps

When `/setup-tool-reader` is invoked:

### Step 1: Check for existing config
```python
claude_md = Path("CLAUDE.md")
if claude_md.exists():
    content = claude_md.read_text()
    if "tool-reader:" in content:
        print("Tool-reader already configured!")
        return
```

### Step 2: Detect project type and command
```python
# Auto-detect based on project files
if Path("package.json").exists():
    project_type = "webapp"
    pkg = json.loads(Path("package.json").read_text())
    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

    # Detect framework and default port
    if "next" in deps:
        run_command = "npm run dev"
        default_url = "http://localhost:3000"
    elif "vite" in deps:
        run_command = "npm run dev"
        default_url = "http://localhost:5173"
    else:
        run_command = "npm start"
        default_url = "http://localhost:3000"

elif Path("Cargo.toml").exists():
    project_type = "rust"
    cargo = Path("Cargo.toml").read_text()
    if any(x in cargo for x in ["ratatui", "tui", "crossterm"]):
        app_type = "tui"
    elif "iced" in cargo or "egui" in cargo:
        app_type = "gui"
    else:
        app_type = "cli"
    run_command = "cargo run"

elif Path("pyproject.toml").exists() or Path("setup.py").exists():
    project_type = "python"
    run_command = "python -m app" # or detected entry point

else:
    project_type = "unknown"
    run_command = None
```

### Step 3: Generate config
```python
config = f"""
---

## Tool Reader Configuration

tool-reader: enabled
tool-reader-type: {project_type}
{f"tool-reader-url: {url or default_url}" if project_type == "webapp" else f"tool-reader-command: {run_command}" if run_command else ""}

### Read From Todos

Claude should check its TodoWrite state to determine when verification is needed:

**Verification Triggers** - Run `/verify-tool` when:
1. All todos in a phase (implement/test/build) are completed
2. A todo containing "verify", "test", "check", "build", "run" is completed
3. All todos are marked complete (final verification)
4. User explicitly requests verification

**Phase Keywords**:
- Implementation: implement, create, add, write, code, develop
- Testing: test, spec, unit, integration, e2e
- Build: build, compile, bundle, package
- Deploy: deploy, release, publish

### .md File Instructions

When user asks to follow instructions from an .md file:
1. Parse checklist items (`- [ ]` / `- [x]`) into TodoWrite
2. Work through items, marking complete as done
3. Trigger verification at section boundaries (## headings)
4. Run final verification when all items complete

### Commands

- `/verify-tool <task>` - Run verification for a task file
- `/verify-tool <task> --check-todos` - Check if todos indicate verification needed
- `/list-tools` - List available task files
"""
```

### Step 4: Update CLAUDE.md
```python
if claude_md.exists():
    with open(claude_md, "a") as f:
        f.write("\n" + config)
else:
    full_content = f"# {project_name}\n\n{config}"
    claude_md.write_text(full_content)
```

## Output

```markdown
## Tool Reader Setup Complete

**Project**: my-project
**Type**: webapp (React/Vite)
**URL**: http://localhost:5173

Added to CLAUDE.md:
- tool-reader: enabled
- Todo-based verification triggers
- .md file instruction support

Claude will now read from TodoWrite to determine when to run verification.
```

## How Todo Reading Works

When Claude uses TodoWrite, tool-reader monitors for these patterns:

```
TodoWrite called with:
[
  {"content": "Implement login form", "status": "completed"},
  {"content": "Add validation", "status": "completed"},
  {"content": "Test login flow", "status": "completed"},  <- Testing phase done
  {"content": "Build and deploy", "status": "in_progress"}
]

-> Testing phase completed -> Trigger verification
```

### Verification Decision Flow

```
1. Claude marks todo as completed
2. Check: Does todo contain verification keywords?
   - Yes -> Run /verify-tool
3. Check: Are all todos in current phase complete?
   - Yes -> Run /verify-tool
4. Check: Are all todos complete?
   - Yes -> Run final /verify-tool
5. Otherwise -> Continue working
```

## Phase-Based Triggers

| Phase | Trigger When | Action |
|-------|--------------|--------|
| Implementation | All "implement/create/add" todos done | Verify new functionality |
| Testing | All "test/spec" todos done | Run tests + verify |
| Build | "build/compile" todo done | Verify build output |
| Deploy | "deploy/release" todo done | Verify deployment |
| Complete | All todos done | Final verification |

## Notes

- Auto-detects: React, Vue, Next.js, Vite, Rust (TUI/GUI/CLI), Python
- Configures CLAUDE.md to read from TodoWrite for verification triggers
- Works with any project type - just provide URL or command if auto-detect fails
- Todo integration uses Claude's built-in TodoWrite system
- Creates `.claude/` directory if needed for task files
