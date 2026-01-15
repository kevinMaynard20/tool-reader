# Tool Reader Auto-Verification Configuration

Add this snippet to your project's `CLAUDE.md` to enable automatic visual verification.

---

## Minimal Configuration

Add this single line to enable auto-verify with defaults:

```markdown
tool-reader: auto-verify
```

---

## Full Configuration (Recommended)

For full control and testing tool integration, add this section to your `CLAUDE.md`:

```markdown
---

## Tool Reader Configuration

tool-reader: enabled
tool-reader-adapter: {auto|browser|tui|gui|cli}
tool-reader-target: {url or command}
tool-reader-auto-install: confirm
visual-verifier-script: ~/.claude/plugins/tool-reader/plugins/tool-reader/scripts/visual_verifier.py

---

## Testing & Interaction Tools

### Detected Tools
<!-- Auto-populated by /tool-reader:setup-tool-reader -->
- [ ] playwright - web browser automation
- [ ] pytest - Python test runner
- [ ] pyte - TUI terminal emulator (fallback capture)

### How to Start the Application
- **Command**: npm run dev / cargo run / python main.py
- **URL** (if web): http://localhost:3000
- **Adapter**: browser / tui / gui / cli

### How to Run Tests
- **Unit tests**: npm test / pytest / cargo test
- **E2E tests**: npx playwright test

### Interaction Methods

**For Web Apps (browser/playwright adapter):**
- Screenshots: Headless Chromium capture (invisible)
- Interaction: Click, type, hover via Playwright API
- No window will appear on your screen

**For TUI Apps (tui adapter):**
- Screenshots: Hidden Windows desktop + PrintWindow API
- Interaction: Send keypresses (Enter, Tab, arrows, etc.)
- The TUI runs completely invisibly
- Supported keys: enter, tab, escape, up, down, left, right, space, backspace, f1-f12

**For GUI Apps (gui adapter):**
- Screenshots: PrintWindow API (works on minimized windows)
- Interaction: Win32 input simulation
- Target format: `window:AppTitle` or `gui:command|WindowTitle`

### Auto-Install Policy

When a verification requires a tool that's not installed, Claude will:
1. Detect the missing tool
2. Ask for confirmation before installing
3. Run: `pip install <tool>` or `npm install <tool>`

Set `tool-reader-auto-install: always` to skip confirmation prompts.

---

## Visual Verification

tool-reader: auto-verify

### When to Verify
After editing UI files (.tsx, .jsx, .vue, .css, .rs for TUI), Claude will:
1. Capture a screenshot invisibly (no window popup)
2. Compare against baseline if available
3. Attempt auto-fix if issues detected
4. Report results

### TUI Capture Details

For Ratatui/Crossterm applications:
1. Creates a hidden Windows desktop (completely invisible)
2. Launches terminal with TUI command on that desktop
3. Waits for TUI to render
4. Captures via PrintWindow Win32 API
5. Cleans up hidden desktop
6. Returns PNG screenshot

**Session mode** for interactive testing:
```python
# Multiple captures with interaction
await adapter.start_session("cargo run")
await adapter.capture("cargo run")  # Initial state
await adapter.capture_on_event("cargo run", "key", "down")  # Press down
await adapter.capture_on_event("cargo run", "key", "enter")  # Press enter
await adapter.end_session()
```

### Acceptance Criteria
- All components render without errors
- Layout matches design specs
- No console errors
- TUI renders correctly in terminal
```

---

## Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `tool-reader: auto-verify` | Enable auto-verification | Required |
| `tool-reader-adapter: <type>` | Force adapter type | Auto-detect |
| `tool-reader-target: <url\|cmd>` | Override target | Auto-detect |
| `tool-reader-auto-install: <policy>` | Install missing tools | confirm |

### Adapter Types

| Adapter | Use For | Capture Method |
|---------|---------|----------------|
| `browser` | Web apps (React, Vue, etc.) | Headless Chromium |
| `tui` | Terminal UIs (Ratatui, Textual) | Hidden desktop + PrintWindow |
| `gui` | Desktop apps (Tauri, Electron) | PrintWindow API |
| `cli` | CLI tools | Text output capture |

---

## Example CLAUDE.md for a Ratatui Project

```markdown
# My TUI App

## Project Overview
A terminal UI application built with Ratatui and Crossterm.

## Commands
- `cargo run` - Run the application
- `cargo test` - Run tests
- `cargo build --release` - Build for production

---

## Tool Reader Configuration

tool-reader: enabled
tool-reader-adapter: tui
tool-reader-target: cargo run
tool-reader-auto-install: confirm

---

## Testing & Interaction Tools

### Detected Tools
- [x] cargo test (Rust built-in)
- [ ] playwright (not needed for TUI)
- [ ] pyte (optional fallback)

### How to Start the Application
- **Command**: cargo run
- **Adapter**: tui (hidden desktop capture)

### TUI Interaction
The TUI adapter will:
1. Create an invisible Windows desktop
2. Launch cmd.exe running `cargo run` on that desktop
3. Wait for the TUI to render (3 seconds default)
4. Capture the terminal window as PNG
5. Clean up the hidden desktop

For interactive testing:
- `key:enter` - Confirm selection
- `key:tab` - Switch focus
- `key:up/down` - Navigate menus
- `key:escape` - Cancel/back
- `input:text` - Type text input

---

## Visual Verification

tool-reader: auto-verify

After editing TUI components in `src/`, verify the UI renders correctly.
Focus areas:
- Main menu displays all options
- Navigation works with arrow keys
- Status bar shows correct info
- Colors and styling applied correctly
```

---

## Example CLAUDE.md for a Web Project

```markdown
# My React App

## Project Overview
A React application with TypeScript and Tailwind CSS.

## Commands
- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm test` - Run tests

---

## Tool Reader Configuration

tool-reader: enabled
tool-reader-adapter: browser
tool-reader-target: http://localhost:5173
tool-reader-auto-install: confirm

---

## Testing & Interaction Tools

### Detected Tools
- [x] playwright (@playwright/test installed)
- [x] vitest (unit testing)
- [ ] cypress (not installed)

### How to Start the Application
- **Command**: npm run dev
- **URL**: http://localhost:5173
- **Adapter**: browser (headless Chromium)

### How to Run Tests
- **Unit tests**: npm test
- **E2E tests**: npx playwright test

### Web Interaction
For visual verification:
- Click elements: `event: click, selector: #button-id`
- Type text: `event: input, selector: #input-id=text`
- Navigate: `event: navigate, selector: /page-path`

---

## Visual Verification

tool-reader: auto-verify
tool-reader-url: http://localhost:5173

After editing components in `src/components/`, verify the UI renders correctly.
Focus areas:
- Navigation menu renders all items
- Forms validate inputs properly
- Modal dialogs appear centered
- Dark mode toggle works
```

---

## How It Works

When Claude Code edits a file matching UI patterns:

1. **Detection**: Pattern matcher identifies the file as UI-related
2. **Config Check**: Reads CLAUDE.md to confirm auto-verify is enabled
3. **Adapter Selection**: Chooses browser/tui/gui based on project type
4. **Capture**: Takes invisible screenshot:
   - Web: Headless browser
   - TUI: Hidden desktop + PrintWindow
   - GUI: PrintWindow on minimized window
5. **Baseline Compare**: If baseline exists, compares for regressions
6. **Auto-Fix**: If issues found, attempts automatic code fixes
7. **Report**: Shows verification results with screenshots

All captures happen invisibly - no windows steal focus or interrupt your work.

---

## Baseline Management

Save baselines after major UI changes:

```
/save-baseline login-page
/save-baseline dashboard
/compare-baseline login-page
```

Baselines are stored in `.claude/baselines/` and tracked in `manifest.json`.

---

## Disabling Auto-Verify

To disable, remove or comment out the `tool-reader: auto-verify` line:

```markdown
<!-- tool-reader: auto-verify -->
```

Or delete the line entirely.

---

## Troubleshooting

### TUI Not Capturing
- Ensure the TUI command runs without prompts: `cargo run` should start immediately
- Check that the TUI uses Ratatui/Crossterm (adapter detection relies on this)
- Try increasing wait time in capture options

### Web Not Capturing
- Ensure dev server is running at the target URL
- Check that Playwright browsers are installed: `npx playwright install`
- Try specifying the port explicitly: `tool-reader-target: http://localhost:3000`

### Missing Testing Tools
- Run `/tool-reader:setup-tool-reader` to re-scan for tools
- Install missing tools manually or set `tool-reader-auto-install: always`
