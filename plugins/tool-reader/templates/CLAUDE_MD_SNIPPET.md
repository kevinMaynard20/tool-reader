# Tool Reader Auto-Verification Configuration

Add this snippet to your project's `CLAUDE.md` to enable automatic visual verification.

---

## Minimal Configuration

Add this single line to enable auto-verify with defaults:

```markdown
tool-reader: auto-verify
```

---

## Full Configuration

For more control, add this section to your `CLAUDE.md`:

```markdown
## Visual Verification

tool-reader: auto-verify
tool-reader-url: http://localhost:3000
tool-reader-port: 3000

### When to Verify
After editing UI files (.tsx, .jsx, .vue, .css, etc.), Claude will:
1. Capture a screenshot invisibly (no window popup)
2. Compare against baseline if available
3. Attempt auto-fix if issues detected
4. Report results

### App Configuration
- **Webapp**: Runs at http://localhost:3000
- **Dev command**: `npm run dev`

### Acceptance Criteria
- All components render without errors
- Layout matches design specs
- No console errors in browser
```

---

## Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `tool-reader: auto-verify` | Enable auto-verification | Required |
| `tool-reader-url: <url>` | Override webapp URL | Auto-detect |
| `tool-reader-port: <port>` | Specify dev server port | 3000 |

---

## Example CLAUDE.md

Here's a complete example for a React project:

```markdown
# My React App

## Project Overview
A React application with TypeScript and Tailwind CSS.

## Commands
- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm test` - Run tests

## Visual Verification

tool-reader: auto-verify
tool-reader-url: http://localhost:5173

After editing components in `src/components/`, verify the UI renders correctly.
Focus areas:
- Navigation menu renders all items
- Forms validate inputs properly
- Modal dialogs appear centered
- Dark mode toggle works

## Code Style
- Use functional components with hooks
- Prefer Tailwind over inline styles
- Keep components under 200 lines
```

---

## How It Works

When Claude Code edits a file matching UI patterns:

1. **Detection**: Pattern matcher identifies the file as UI-related
2. **Config Check**: Reads CLAUDE.md to confirm auto-verify is enabled
3. **Server Detection**: Finds running dev server or uses configured URL
4. **Capture**: Takes invisible screenshot using headless browser
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
