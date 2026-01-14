# /capture

Capture current state of a target using the appropriate adapter.

## Usage

```bash
/capture --target <url|command|window>
/capture --target <target> --adapter <type>
/capture --target <target> --on <event>
/capture --target <target> --sequence "<events>"
/capture --add <path> --event "<description>"
```

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--target` | Yes* | Target to capture (URL, command, window) |
| `--adapter` | No | Specific adapter (auto-detected if not specified) |
| `--on` | No | Capture after event (click, navigate, input) |
| `--sequence` | No | Capture sequence of events |
| `--add` | No | Add external capture file |
| `--event` | No | Event description (for --add) |
| `--output` | No | Custom output path |

*Required unless using --add

## Examples

```bash
# Simple capture
/capture --target http://localhost:3000
/capture --target "cargo run"
/capture --target window:MyApp

# Specify adapter
/capture --target http://localhost:3000 --adapter playwright
/capture --target "cargo run" --adapter tui

# Event-based capture
/capture --target http://localhost:3000 --on click:#submit-btn
/capture --target http://localhost:3000 --on navigate
/capture --target http://localhost:3000 --on input:#email

# Capture sequence
/capture --target http://localhost:3000 --sequence "
  screenshot
  click:#login-btn
  input:#email=test@example.com
  click:#submit
  navigate
  screenshot
"

# Add external capture
/capture --add screenshot.png --event "After clicking login"
/capture --add terminal_output.txt --event "Build completed"
```

## Events (Playwright Adapter)

| Event | Syntax | Description |
|-------|--------|-------------|
| click | click:#selector | Click element then capture |
| navigate | navigate | Wait for navigation then capture |
| input | input:#selector=value | Fill input then capture |
| wait | wait:2 | Wait N seconds then capture |
| hover | hover:#selector | Hover element then capture |
| scroll | scroll:#selector | Scroll to element then capture |
| screenshot | screenshot | Capture without action |

## Sequence Format

```
# Each line is an event
screenshot                    # Initial state
click:#login-btn              # Click login button
input:#email=test@example.com # Fill email
input:#password=secret123     # Fill password
click:#submit                 # Click submit
navigate                      # Wait for navigation
screenshot                    # Final state
```

## Output

```
## Capture Complete

Target: http://localhost:3000
Adapter: playwright
Event: click:#login-btn

Saved: .tool-reader/captures/abc123_1234567890.png

Run: /verify-tool <task> --captures .tool-reader/captures/abc123_1234567890.png
```

## Sequence Output

```
## Capture Sequence Complete

Target: http://localhost:3000
Adapter: playwright
Captures: 7

| # | Event | Path |
|---|-------|------|
| 1 | screenshot | .tool-reader/captures/seq_001.png |
| 2 | click:#login-btn | .tool-reader/captures/seq_002.png |
| 3 | input:#email | .tool-reader/captures/seq_003.png |
| 4 | input:#password | .tool-reader/captures/seq_004.png |
| 5 | click:#submit | .tool-reader/captures/seq_005.png |
| 6 | navigate | .tool-reader/captures/seq_006.png |
| 7 | screenshot | .tool-reader/captures/seq_007.png |

Run: /verify-batch .tool-reader/captures/ to verify all
```

## Adding External Captures

External Playwright scripts or manual screenshots can be registered:

```bash
# Add single capture
/capture --add ./my_screenshot.png --event "User logged in"

# Add with tags
/capture --add ./build_output.txt --event "Build completed" --tags build,ci
```

## Adapters

| Adapter | Target Format | Capture Type |
|---------|---------------|--------------|
| playwright | http://, https:// | Screenshot, events |
| browser | http://, https:// | Screenshot only |
| tui | tui:, commands | Terminal text |
| gui | window:, .exe | Window screenshot |
| cli | commands | stdout/stderr |

## Notes

- Captures stored in .tool-reader/captures/ by default
- Playwright supports event-based and sequence capture
- Other adapters capture current state only
- Use --add to register external captures
- Captures can be batch verified with /verify-batch
