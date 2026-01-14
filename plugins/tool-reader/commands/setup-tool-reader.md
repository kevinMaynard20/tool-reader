# /setup-tool-reader

Initialize tool-reader auto-verification in the current project.

## Usage

```
/setup-tool-reader [url]
```

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `url` | No | Dev server URL (auto-detected if not provided) |

## Examples

```
/setup-tool-reader
/setup-tool-reader http://localhost:5173
/setup-tool-reader http://localhost:3000
```

## What It Does

1. **Check for CLAUDE.md** - Look for existing project config
2. **Detect App Type** - Scan for package.json, Cargo.toml, etc.
3. **Find Dev Server** - Check common ports (3000, 5173, 8080)
4. **Add Config** - Append auto-verify config to CLAUDE.md

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
    project_type = "tui"  # Likely Rust TUI
```

### Step 3: Detect running dev server
```python
import socket
for port in [3000, 5173, 8080, 4200]:
    sock = socket.socket()
    if sock.connect_ex(('localhost', port)) == 0:
        detected_url = f"http://localhost:{port}"
        break
```

### Step 4: Generate config
```python
config = f"""
## Visual Verification

tool-reader: auto-verify
tool-reader-url: {url or detected_url}

After editing UI files, Claude will automatically verify changes visually.
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

**Project**: my-react-app
**Type**: webapp (React)
**URL**: http://localhost:5173

Added to CLAUDE.md:
```
tool-reader: auto-verify
tool-reader-url: http://localhost:5173
```

Commands available:
- `/verify-tool <task>` - Verify a task visually
- `/save-baseline <name>` - Save current UI as baseline
- `/compare-baseline <name>` - Compare against baseline

Auto-verification will trigger after editing:
- *.tsx, *.jsx, *.vue, *.svelte
- *.css, *.scss, *.sass
```

## Notes

- Creates `.claude/` directory if it doesn't exist
- Won't duplicate config if already present
- Auto-detects most common frameworks
- URL can be overridden manually later in CLAUDE.md
