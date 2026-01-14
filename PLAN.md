# Tool-Reader Agnostic Verification Plan

## Goal

Make tool-reader completely agnostic to the target being tested - works for **any GUI, TUI, webpage, or CLI**. Support Playwright integration for event-based screenshots with batch verification.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    tool-reader                               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   Capture    │  │   External   │  │    Batch     │       │
│  │   Adapters   │  │    Hooks     │  │   Verifier   │       │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │
│         │                 │                 │                │
│         ▼                 ▼                 ▼                │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Unified Capture Store                   │    │
│  │   (screenshots, terminal output, DOM snapshots)      │    │
│  └─────────────────────────────────────────────────────┘    │
│                          │                                   │
│                          ▼                                   │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Claude Verification                     │    │
│  │   (batch or single, summary or detailed)             │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Agnostic Capture Adapters

### New: `adapters/` module

Each adapter implements a common interface:

```python
class CaptureAdapter:
    """Base class for all capture adapters."""

    async def capture(self, target: str, options: dict) -> CaptureResult:
        """Capture current state of target."""
        raise NotImplementedError

    async def capture_on_event(self, target: str, event: str) -> CaptureResult:
        """Capture when specific event occurs."""
        raise NotImplementedError
```

### Adapters to Create

| Adapter | Target | Capture Method |
|---------|--------|----------------|
| `playwright_adapter.py` | Webpages | Playwright CDP screenshots |
| `browser_adapter.py` | Webpages | Headless Chrome/Edge (fallback) |
| `tui_adapter.py` | Terminal apps | PTY capture, ANSI parsing |
| `gui_adapter.py` | Desktop apps | PrintWindow API (Windows) |
| `cli_adapter.py` | CLI tools | stdout/stderr capture |
| `custom_adapter.py` | Any | User-provided capture script |

### Adapter Auto-Detection

```python
def detect_adapter(target: str) -> CaptureAdapter:
    if target.startswith("http"):
        return PlaywrightAdapter() if playwright_available() else BrowserAdapter()
    elif target.endswith(".exe") or "window:" in target:
        return GuiAdapter()
    elif "tui:" in target or is_terminal_app(target):
        return TuiAdapter()
    else:
        return CliAdapter()
```

---

## Phase 2: Playwright Integration

### Built-in Playwright Support

```python
# scripts/playwright_adapter.py

class PlaywrightAdapter(CaptureAdapter):
    def __init__(self):
        self.browser = None
        self.page = None
        self.captures = []  # Batch storage

    async def start_session(self, url: str):
        """Start browser session for capture."""
        self.browser = await playwright.chromium.launch(headless=True)
        self.page = await self.browser.new_page()
        await self.page.goto(url)

    async def capture_on_event(self, event: str, selector: str = None):
        """Capture screenshot on specific event."""
        # Events: click, navigate, input, mutation, custom

        if event == "click" and selector:
            await self.page.click(selector)

        screenshot = await self.page.screenshot()
        self.captures.append({
            "event": event,
            "timestamp": time.time(),
            "screenshot": screenshot,
            "url": self.page.url
        })
        return screenshot

    async def get_batch(self) -> List[CaptureResult]:
        """Return all captured screenshots."""
        return self.captures
```

### External Hook Support

Allow external Playwright scripts to send screenshots:

```python
# scripts/capture_hook.py

class CaptureHook:
    """Accept screenshots from external sources."""

    def __init__(self, capture_dir: str):
        self.capture_dir = Path(capture_dir)
        self.capture_dir.mkdir(exist_ok=True)

    def accept_screenshot(self, path: str, metadata: dict = None):
        """Register externally captured screenshot."""
        # Copy to capture store
        # Record metadata (event, timestamp, context)

    def watch_directory(self, dir_path: str):
        """Watch directory for new screenshots."""
        # Auto-register new images as they appear
```

### Hook Configuration in CLAUDE.md

```markdown
## Tool Reader Configuration

tool-reader: enabled
tool-reader-capture-dir: .tool-reader/captures/

### External Capture Hook

Accepts screenshots from external Playwright scripts:
- Drop screenshots in `.tool-reader/captures/`
- Or call: `/verify-tool --add-capture <path> --event "clicked login"`
```

---

## Phase 3: Event-Based Capture

### Supported Events

| Event | Description | Trigger |
|-------|-------------|---------|
| `click` | After clicking element | Selector provided |
| `navigate` | After page navigation | URL change detected |
| `input` | After form input | Input selector provided |
| `mutation` | After DOM change | MutationObserver |
| `custom` | User-defined | Script/callback |
| `interval` | Time-based backup | Optional timer |

### Event Capture Syntax

```bash
# Capture on specific events
/capture --url http://localhost:3000 --on click:#submit-btn
/capture --url http://localhost:3000 --on navigate
/capture --url http://localhost:3000 --on input:#email-field

# Multiple events in sequence
/capture --url http://localhost:3000 --sequence "
  click:#login-btn
  input:#email=test@example.com
  input:#password=secret
  click:#submit
  navigate
"
```

---

## Phase 4: Batch Verification

### New Command: `/verify-batch`

```bash
# Verify all captures in directory
/verify-batch .tool-reader/captures/

# Verify with task context
/verify-batch .tool-reader/captures/ --task login-flow

# Detailed per-image analysis
/verify-batch .tool-reader/captures/ --detailed

# Summary only (default)
/verify-batch .tool-reader/captures/ --summary
```

### Batch Verification Script

```python
# scripts/batch_verifier.py

class BatchVerifier:
    def __init__(self, task_items: List[str] = None):
        self.task_items = task_items or []
        self.results = []

    async def verify_batch(
        self,
        captures: List[Path],
        detailed: bool = False
    ) -> BatchResult:
        """
        Send all captures to Claude in single request.
        Returns summary + optional detailed per-image analysis.
        """

        # Build multi-image prompt
        prompt = self._build_batch_prompt(captures, detailed)

        # Single Claude call with all images
        response = await self._call_claude(prompt, captures)

        return self._parse_batch_response(response, detailed)

    def _build_batch_prompt(self, captures, detailed):
        return f"""
        Verify these {len(captures)} screenshots against the task criteria.

        ## Task Items
        {self._format_task_items()}

        ## Screenshots
        Analyze each screenshot in sequence (they represent a user flow).

        ## Response Format
        {"Provide detailed analysis for each image." if detailed else "Provide summary only."}

        ```json
        {{
            "summary": {{
                "total": {len(captures)},
                "passed": <count>,
                "failed": <count>,
                "issues": ["list of issues found"]
            }},
            {"\"details\": [{\"image\": 1, \"status\": \"pass/fail\", \"evidence\": \"...\"}]" if detailed else ""}
        }}
        ```
        """
```

### Batch Result Format

**Summary Mode (default):**
```
## Batch Verification: 5 screenshots

✓ Passed: 4/5
✗ Failed: 1/5

Issues Found:
- Screenshot 3: Submit button not visible after form fill

Task Progress: 80% complete
```

**Detailed Mode (--detailed):**
```
## Batch Verification: 5 screenshots

### Screenshot 1: Initial page load
- Status: PASS
- Evidence: Login form visible with email/password fields
- Task items verified: "Login page renders"

### Screenshot 2: After email input
- Status: PASS
- Evidence: Email field populated, no validation errors

### Screenshot 3: After submit click
- Status: FAIL
- Evidence: Submit button not visible, page scrolled
- Issue: Button may be below viewport

[... continues for each image ...]

## Summary
✓ Passed: 4/5
✗ Failed: 1/5
```

---

## Phase 5: Updated Commands

### `/verify-tool` (Updated)

```bash
# Basic verification (auto-detect target type)
/verify-tool <task-name>

# Specify target explicitly
/verify-tool <task-name> --target http://localhost:3000
/verify-tool <task-name> --target "cargo run"
/verify-tool <task-name> --target window:MyApp

# Use specific adapter
/verify-tool <task-name> --adapter playwright
/verify-tool <task-name> --adapter tui
/verify-tool <task-name> --adapter gui

# Check todos for auto-trigger
/verify-tool <task-name> --check-todos
```

### `/capture` (New)

```bash
# Single capture
/capture --target http://localhost:3000
/capture --target "cargo run"

# Event-based capture
/capture --target http://localhost:3000 --on click:#button
/capture --target http://localhost:3000 --on navigate

# Capture sequence
/capture --target http://localhost:3000 --sequence "click:#a, click:#b, navigate"

# Add external capture
/capture --add <path> --event "description of what happened"
```

### `/verify-batch` (New)

```bash
# Verify batch of captures
/verify-batch <capture-dir>
/verify-batch <capture-dir> --task <task-name>
/verify-batch <capture-dir> --detailed
/verify-batch <capture-dir> --summary
```

### `/setup-tool-reader` (Updated)

```bash
# Auto-detect and configure
/setup-tool-reader

# Specify target type hint
/setup-tool-reader --webapp http://localhost:3000
/setup-tool-reader --tui "cargo run"
/setup-tool-reader --gui "myapp.exe"

# Enable Playwright integration
/setup-tool-reader --playwright
```

---

## Phase 6: Configuration Schema

### CLAUDE.md Configuration

```markdown
## Tool Reader Configuration

tool-reader: enabled

### Target (auto-detected or specified)
tool-reader-target: http://localhost:3000
# or: tool-reader-target: cargo run
# or: tool-reader-target: window:MyApp

### Adapter (auto-detected or specified)
tool-reader-adapter: auto
# options: auto, playwright, browser, tui, gui, cli, custom

### Capture Settings
tool-reader-capture-dir: .tool-reader/captures/
tool-reader-capture-on: [click, navigate, input]

### Playwright Settings (if using playwright adapter)
tool-reader-playwright-headless: true
tool-reader-playwright-viewport: 1280x720

### Batch Settings
tool-reader-batch-default: summary
# options: summary, detailed

### Read From Todos
[... existing todo integration ...]
```

---

## Files to Create/Modify

### New Files

| File | Purpose |
|------|---------|
| `scripts/adapters/__init__.py` | Adapter module |
| `scripts/adapters/base.py` | Base CaptureAdapter class |
| `scripts/adapters/playwright_adapter.py` | Playwright integration |
| `scripts/adapters/browser_adapter.py` | Headless browser fallback |
| `scripts/adapters/tui_adapter.py` | Terminal app capture |
| `scripts/adapters/gui_adapter.py` | Desktop app capture |
| `scripts/adapters/cli_adapter.py` | CLI output capture |
| `scripts/capture_hook.py` | External capture acceptance |
| `scripts/batch_verifier.py` | Batch verification logic |
| `commands/capture.md` | /capture command docs |
| `commands/verify-batch.md` | /verify-batch command docs |

### Existing Command Updates

#### `/verify-tool` (commands/verify-tool.md)

**Current**: Hardcoded for webapp/gui/tui detection
**Updated**:
```bash
# Agnostic target specification
/verify-tool <task> --target <url|command|window>
/verify-tool <task> --adapter <playwright|browser|tui|gui|cli|auto>

# Batch support
/verify-tool <task> --batch <capture-dir>
/verify-tool <task> --batch <capture-dir> --detailed

# External captures
/verify-tool <task> --captures <path1> <path2> ...

# Event capture during verify
/verify-tool <task> --capture-on click:#submit
```

#### `/setup-tool-reader` (commands/setup-tool-reader.md)

**Current**: Auto-detects project type, configures todo reading
**Updated**:
```bash
# Adapter selection
/setup-tool-reader --adapter playwright
/setup-tool-reader --adapter tui
/setup-tool-reader --adapter auto

# Target configuration
/setup-tool-reader --target http://localhost:3000
/setup-tool-reader --target "cargo run"

# Playwright settings
/setup-tool-reader --playwright --headless --viewport 1280x720

# Capture directory
/setup-tool-reader --capture-dir .tool-reader/captures/
```

#### `/list-tools` (commands/list-tools.md)

**Current**: Lists .claude/*.md task files
**Updated**:
```bash
# List task files (existing)
/list-tools

# List available adapters
/list-tools --adapters

# List captures
/list-tools --captures
/list-tools --captures --pending  # Not yet verified

# List with target info
/list-tools --verbose  # Shows target type per task
```

#### `/run-tool` (commands/run-tool.md)

**Current**: Executes task from .claude/<name>.md
**Updated**:
```bash
# Run with capture enabled
/run-tool <task> --capture
/run-tool <task> --capture-on click,navigate,input

# Run with specific adapter
/run-tool <task> --adapter playwright

# Run and verify
/run-tool <task> --verify  # Run then verify
/run-tool <task> --verify --batch  # Batch verify after run
```

### Modified Files

| File | Changes |
|------|---------|
| `commands/verify-tool.md` | Add adapter/target/batch options |
| `commands/setup-tool-reader.md` | Add adapter/playwright configuration |
| `commands/list-tools.md` | Add --adapters, --captures flags |
| `commands/run-tool.md` | Add --capture, --verify flags |
| `scripts/visual_verifier.py` | Use adapter system |
| `README.md` | Document new capabilities |

---

## Implementation Order

1. **Phase 1**: Create adapter base + refactor existing capture into adapters
2. **Phase 2**: Add Playwright adapter + external hook support
3. **Phase 3**: Implement event-based capture
4. **Phase 4**: Build batch verifier
5. **Phase 5**: Update commands
6. **Phase 6**: Update configuration/documentation

---

## Questions Resolved

- **Screenshot intervals**: Event-based (on action)
- **Playwright integration**: Both built-in + external hooks
- **Batch reporting**: Summary default, --detailed flag for per-image
