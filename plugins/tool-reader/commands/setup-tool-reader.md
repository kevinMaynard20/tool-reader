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
2. **Scan for existing testing tools** (playwright, pytest, pyte, etc.)
3. **Detect how the app runs** (dev server, cargo run, etc.)
4. Add Tool Reader Configuration section to CLAUDE.md
5. **Add Testing Tools section** with detected tools and interaction methods
6. Create .tool-reader/ directory structure
7. Create .claude/ directory for task files

## Idempotent Behavior

Before modifying CLAUDE.md:
1. Check for existing `## Tool Reader Configuration`
2. If exists: Update only what changed
3. If missing: Add full configuration block

---

## STEP 1: Scan for Testing Tools & Existing Test Infrastructure

**Before writing to CLAUDE.md, thoroughly scan the project for available testing tools and existing test configurations.**

### Why This Matters
Tool-reader's `/tool-reader:verify-tool` and `/tool-reader:verify-batch` commands can **integrate with existing testing infrastructure** in the project. If the project already has Playwright, pytest, or other testing tools configured, tool-reader should use them rather than requiring separate setup.

### Python Projects
Check these files for testing tool dependencies:
- `requirements.txt` - grep for pytest, playwright, pyte, selenium
- `pyproject.toml` - look in [project.dependencies], [project.optional-dependencies], [tool.pytest]
- `setup.py` - check install_requires
- `setup.cfg` - check [options.extras_require] for test dependencies
- `Pipfile` - check [packages] and [dev-packages]
- `conftest.py` - indicates pytest is configured
- `pytest.ini` or `pyproject.toml [tool.pytest.ini_options]` - pytest configuration

**Detection commands:**
```bash
# Check installed packages
pip list 2>/dev/null | grep -iE "pytest|playwright|pyte|selenium"

# Check if playwright browsers are installed
python -c "from playwright.sync_api import sync_playwright; print('playwright ready')" 2>/dev/null

# Check if pyte is available for TUI capture
python -c "import pyte; print('pyte available')" 2>/dev/null

# Check for pytest-playwright integration
pip show pytest-playwright 2>/dev/null
```

**Look for existing test commands in:**
- `pyproject.toml` - `[tool.pytest.ini_options]` or `[project.scripts]`
- `Makefile` - test targets
- `setup.cfg` - `[options.entry_points]`
- Package scripts that accept CLI flags for testing

### JavaScript/TypeScript Projects
Check `package.json` for:
- `playwright` or `@playwright/test` in dependencies/devDependencies
- `puppeteer` for browser automation
- `cypress` for E2E testing
- `jest` or `vitest` for unit testing
- **Scripts section** - look for test commands and their flags

**Detection commands:**
```bash
# Check if playwright is installed
npm list playwright @playwright/test --depth=0 2>/dev/null

# Check if browsers are installed
npx playwright --version 2>/dev/null

# Check package.json scripts for test commands
cat package.json | grep -A 20 '"scripts"'
```

**Important: Check for existing Playwright config:**
- `playwright.config.ts` or `playwright.config.js` - existing Playwright configuration
- Look for custom test commands, flags, and output formats

### Rust Projects
Check `Cargo.toml` for:
- `ratatui` or `crossterm` in dependencies (indicates TUI)
- `iced`, `egui`, or `tauri` in dependencies (indicates GUI)
- `[dev-dependencies]` section for test frameworks
- Test files in `tests/` directory

**Detection commands:**
```bash
# Check cargo dependencies
cargo metadata --format-version=1 2>/dev/null | grep -iE "ratatui|crossterm|iced|egui"

# List available cargo commands/aliases
cat .cargo/config.toml 2>/dev/null
```

### Detect Existing Test CLI Flags and Commands

**CRITICAL: Scan for project-specific test commands that accept CLI flags.**

Many projects define custom test scripts that accept flags. Look for:
- Package manager scripts: `npm test`, `yarn test`, `pnpm test`
- Python entry points: `python -m pytest`, custom CLI tools
- Cargo aliases: `cargo test`, custom test commands
- Makefile targets: `make test`, `make e2e`

**Document any CLI flags the existing tools support:**
- Common pytest flags: `--headed`, `--browser`, `--slowmo`, `--video`
- Common Playwright flags: `--project`, `--grep`, `--reporter`
- Project-specific flags defined in package.json scripts or pyproject.toml

These flags should be usable with tool-reader verification commands.

---

## STEP 2: Detect How the App Runs

**Identify the command to start the application:**

### Web Applications
- Check `package.json` scripts for: `dev`, `start`, `serve`
- Common patterns:
  - Vite: `npm run dev` → `http://localhost:5173`
  - Next.js: `npm run dev` → `http://localhost:3000`
  - Create React App: `npm start` → `http://localhost:3000`
  - Express: `npm start` or `node server.js`

### TUI Applications (Ratatui/Crossterm)
- Check `Cargo.toml` for binary name
- Run command: `cargo run` or `cargo run --release`
- **CRITICAL**: TUI apps need the hidden desktop adapter for PNG capture

### GUI Applications
- Check for main entry point
- May need window title for capture: `window:AppName`

### Python Applications
- Check for `main.py`, `app.py`, or entry point in `pyproject.toml`
- Run command: `python main.py` or `python -m package_name`

---

## STEP 2.5: Integration with Existing Testing Tools

**CRITICAL: If the project has existing playwright, pytest, or other testing tools, tool-reader should integrate with them.**

### Integration with /tool-reader:verify-tool and /tool-reader:verify-batch

When existing testing tools are detected, document how to use them alongside tool-reader commands:

#### If Playwright is Found (JS/TS)
```markdown
### Using Existing Playwright with Tool-Reader

The project has Playwright configured. You can:

1. **Run existing Playwright tests:**
   ```bash
   npx playwright test
   npm run test:e2e  # if defined in package.json
   ```

2. **Use Playwright's screenshot capabilities with tool-reader verification:**
   ```bash
   # Run playwright test that generates screenshots
   npx playwright test --screenshot=on

   # Verify the captured screenshots with tool-reader
   /tool-reader:verify-batch ./test-results/ --task <task-name>
   ```

3. **Pass existing CLI flags to tests:**
   - Use the flags already defined in your playwright config
   - Any project-specific flags from package.json scripts
   - Example: `npx playwright test --headed --slowmo=500`
```

#### If pytest-playwright is Found (Python)
```markdown
### Using Existing pytest-playwright with Tool-Reader

The project has pytest with playwright integration. You can:

1. **Run existing tests:**
   ```bash
   pytest tests/
   python -m pytest  # with any configured flags
   ```

2. **Generate screenshots during test runs:**
   ```bash
   pytest --screenshot=on --output=./test-results
   ```

3. **Verify captured screenshots:**
   ```bash
   /tool-reader:verify-batch ./test-results/ --task <task-name>
   ```

4. **Use project-specific CLI flags:**
   - Check pyproject.toml for configured pytest options
   - Check conftest.py for custom fixtures and flags
   - Use any flags your test suite accepts
```

#### Generic Integration Pattern
```markdown
### Integrating Any Testing Tool with Tool-Reader

If your project has testing tools that can capture screenshots:

1. **Run your tests with screenshot output:**
   ```bash
   <your-test-command> <flags-for-screenshots> --output=./captures
   ```

2. **Register external captures with tool-reader:**
   ```bash
   /tool-reader:capture --add ./captures/screenshot.png --event "After test step"
   ```

3. **Batch verify all captures:**
   ```bash
   /tool-reader:verify-batch ./captures/ --task <task-name>
   ```
```

---

## STEP 2.6: Tool Installation Policy

**When required tools are missing, follow this installation policy:**

### Auto-Install with Confirmation (Default)

Set in CLAUDE.md:
```markdown
tool-reader-auto-install: confirm
```

**Behavior:**
1. When a verification command needs a missing tool, Claude will detect it
2. Claude MUST ask the user for confirmation before installing
3. Display the exact command that will be run
4. Only proceed if user approves

**Example interaction:**
```
Claude: The verification requires Playwright, which is not installed.

Would you like me to install it?
- Command: npm install -D @playwright/test && npx playwright install chromium
- This will install Playwright Test and Chromium browser

[User confirms]

Claude: Installing Playwright...
```

### Installation Commands by Tool

| Tool | Detection | Install Command |
|------|-----------|-----------------|
| playwright (Node) | `npm list @playwright/test` | `npm install -D @playwright/test && npx playwright install` |
| playwright (Python) | `pip show playwright` | `pip install playwright && playwright install` |
| pytest-playwright | `pip show pytest-playwright` | `pip install pytest-playwright` |
| pyte | `pip show pyte` | `pip install pyte` |
| puppeteer | `npm list puppeteer` | `npm install puppeteer` |
| selenium | `pip show selenium` | `pip install selenium` |

### Browser Installation

**Playwright browsers require separate installation:**
```bash
# Install all browsers
npx playwright install

# Install specific browser only
npx playwright install chromium
npx playwright install firefox
npx playwright install webkit

# Python
playwright install chromium
```

### Install Policy Options

| Policy | Behavior |
|--------|----------|
| `confirm` (default) | Ask user before installing anything |
| `always` | Auto-install without asking (for CI/automation) |
| `never` | Never install, fail if tool missing |
| `suggest` | Only suggest commands, never run them |

### What to Add to CLAUDE.md

```markdown
### Auto-Install Policy
tool-reader-auto-install: confirm

When verification requires a missing tool:
1. Claude will detect what's missing
2. Ask for confirmation with the exact install command
3. Only proceed if approved
4. Verify installation succeeded before continuing

**Supported auto-installs:**
- Playwright and browsers: `npm install -D @playwright/test && npx playwright install`
- pytest-playwright: `pip install pytest-playwright`
- pyte (TUI fallback): `pip install pyte`

To disable prompts, set: `tool-reader-auto-install: never`
To auto-install without prompts: `tool-reader-auto-install: always`
```

---

## STEP 3: Configuration Block for CLAUDE.md

When setting up a project, add this to CLAUDE.md:

```markdown
---

## Tool Reader Configuration

tool-reader: enabled
tool-reader-adapter: {adapter}
tool-reader-target: {target}
visual-verifier-script: ~/.claude/plugins/tool-reader/plugins/tool-reader/scripts/visual_verifier.py

---

## Testing & Interaction Tools

### Detected Tools
<!-- Auto-populated by setup command -->
- [x] playwright (installed) - web browser automation
- [x] pytest (installed) - Python test runner
- [ ] pyte (not installed) - TUI terminal emulator

### How to Start the Application
- **Command**: {start_command}
- **URL** (if web): {url}
- **Adapter**: {adapter}

### How to Run Tests
- **Unit tests**: {test_command}
- **E2E tests**: {e2e_command}

### Interaction Methods

**For Web Apps (playwright adapter):**
- Screenshots: Headless browser capture
- Interaction: Click, type, hover via Playwright API
- Example: `npx playwright test` or via visual_verifier.py

**For TUI Apps (tui adapter):**
- Screenshots: Hidden Windows desktop + PrintWindow API
- Interaction: Send keypresses (Enter, Tab, arrows, etc.)
- The TUI runs invisibly - no window will appear on your screen
- Example capture: `python visual_verifier.py --adapter tui --target "cargo run"`

**For GUI Apps (gui adapter):**
- Screenshots: PrintWindow API (captures minimized windows)
- Interaction: Win32 input simulation
- Example: `window:MyAppTitle`

### Auto-Install Policy
tool-reader-auto-install: confirm

When a verification requires a tool that's not installed:
1. Claude will detect the missing tool
2. Ask for confirmation before installing
3. Run the appropriate install command:
   - Python: `pip install <tool>`
   - Node: `npm install <tool>`
   - Playwright browsers: `npx playwright install`

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

1. Launches appropriate adapter based on target type:
   - **Web**: Headless browser (COMPLETELY INVISIBLE)
   - **TUI**: Hidden Windows desktop + terminal (INVISIBLE)
   - **GUI**: PrintWindow API (no focus steal)
2. Captures ACTUAL PNG screenshot
3. Sends PNG to Claude Sonnet for analysis
4. Returns pass/fail results

### TUI-Specific Instructions

For Ratatui/Crossterm TUI applications:

1. **Capture Method**: Hidden desktop approach
   - Creates invisible Windows desktop
   - Launches terminal with TUI command
   - Captures via PrintWindow API
   - Cleans up desktop after capture

2. **Interaction**: Send keypresses
   - `key:enter` - Press Enter
   - `key:tab` - Press Tab
   - `key:up/down/left/right` - Arrow keys
   - `key:escape` - Press Escape
   - `input:text` - Type text

3. **Session Mode**: For multiple interactions
   ```python
   # Start session
   adapter.start_session("cargo run")

   # Capture initial state
   await adapter.capture("cargo run")

   # Send key and capture
   await adapter.capture_on_event("cargo run", "key", "down")

   # End session
   await adapter.end_session()
   ```

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

---

## Auto-Detection Tables

### Project Type Detection

| Files Found | Project Type | Default Adapter | Default Target |
|-------------|--------------|-----------------|----------------|
| package.json (vite) | webapp | browser | http://localhost:5173 |
| package.json (next) | webapp | browser | http://localhost:3000 |
| package.json (react) | webapp | browser | http://localhost:3000 |
| package.json (express/fastify) | api | browser | http://localhost:3000 |
| Cargo.toml (ratatui/crossterm) | tui | tui | cargo run |
| Cargo.toml (iced/egui/tauri) | gui | gui | cargo run |
| pyproject.toml (textual) | tui | tui | python -m {package} |
| pyproject.toml (flask/django) | webapp | browser | http://localhost:5000 |
| pyproject.toml | python | cli | python main.py |

### Testing Tool Detection

| Tool | File to Check | Detection Pattern |
|------|---------------|-------------------|
| playwright | package.json | `"playwright"` or `"@playwright/test"` in deps |
| playwright (py) | requirements.txt | `playwright` |
| pytest | requirements.txt, pyproject.toml | `pytest` |
| pyte | requirements.txt | `pyte` |
| cypress | package.json | `"cypress"` in deps |
| puppeteer | package.json | `"puppeteer"` in deps |
| selenium | requirements.txt | `selenium` |

---

## Examples

```bash
# Auto-detect everything
/tool-reader:setup-tool-reader

# Specify target for web app
/tool-reader:setup-tool-reader --target http://localhost:3000

# TUI project with specific command
/tool-reader:setup-tool-reader --adapter tui --target "cargo run --release"

# GUI project with window title
/tool-reader:setup-tool-reader --adapter gui --target "window:MyApp"
```

---

## Output

After running setup, you should see:

```
## Tool Reader Setup Complete

Configuration added to CLAUDE.md

Project: my-project
Type: tui (ratatui detected)
Adapter: tui
Target: cargo run

### Detected Testing Tools
- [x] No external testing tools found
- [ ] playwright - not installed (optional for web testing)
- [ ] pyte - not installed (optional for TUI capture fallback)

### App Interaction
- Start command: cargo run
- Capture method: Hidden desktop + PrintWindow
- Input method: Win32 keybd_event

Visual verification MUST be tracked as a task:
- Add to TodoWrite, OR
- Create .claude/VERIFY_<feature>.md

Script: ~/.claude/plugins/tool-reader/plugins/tool-reader/scripts/visual_verifier.py

To remove: /tool-reader:stop-tool-reader
```

---

## Notes

- **Idempotent**: Safe to run multiple times
- **Testing tools detected**: Scans for playwright, pytest, pyte, etc.
- **Interaction methods documented**: How to start, test, and interact with the app
- **TUI uses hidden desktop**: PNG screenshots without visible windows
- **Auto-install with confirmation**: Missing tools can be installed on demand
- **Verification is a tracked task** - must be in TodoWrite or .md file
- **Actual screenshots** - script captures PNG, NOT curl/HTML
- **To remove**: Run /tool-reader:stop-tool-reader
