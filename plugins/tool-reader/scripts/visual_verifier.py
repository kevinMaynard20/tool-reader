#!/usr/bin/env python3
"""
Visual Verifier for Tool Reader.
Launches applications invisibly, captures screenshots, and verifies via Claude CLI.

Integrates with Claude's built-in TodoWrite/task system to trigger verification
at phase boundaries and during verification steps.
"""

import os
import sys
import json
import subprocess
import tempfile
import time
import re
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Tuple, Dict, Any
from enum import Enum

# Import todo tracker for Claude task integration
try:
    from todo_tracker import (
        TodoItem, TodoStatus, PhaseType, PhaseContext,
        parse_todos_from_context, analyze_phase_context,
        check_verification_needed, should_auto_verify,
        format_verification_prompt
    )
    TODO_TRACKER_AVAILABLE = True
except ImportError:
    TODO_TRACKER_AVAILABLE = False


class AppType(Enum):
    """Type of application being tested."""
    GUI = "gui"
    TUI = "tui"
    WEBAPP = "webapp"
    UNKNOWN = "unknown"


@dataclass
class VerificationResult:
    """Result of visual verification."""
    success: bool
    completed_items: List[str]
    failed_items: List[str]
    claude_response: str
    screenshot_path: Optional[str] = None


@dataclass
class AppConfig:
    """Configuration for launching an application."""
    app_type: AppType
    command: Optional[str] = None
    url: Optional[str] = None
    window_title: Optional[str] = None
    wait_seconds: float = 2.0
    width: int = 1280
    height: int = 720


def detect_app_type(task_content: str) -> Tuple[AppType, AppConfig]:
    """
    Detect the application type from task file content.

    Looks for markers like:
    - [webapp]: http://localhost:3000
    - [gui]: myapp.exe
    - [tui]: npm run dev
    """
    config = AppConfig(app_type=AppType.UNKNOWN)

    # Check for webapp URL pattern
    webapp_match = re.search(
        r'\[webapp\]:\s*(https?://[^\s]+)',
        task_content,
        re.IGNORECASE
    )
    if webapp_match:
        config.app_type = AppType.WEBAPP
        config.url = webapp_match.group(1)
        return config.app_type, config

    # Check for GUI executable pattern
    gui_match = re.search(
        r'\[gui\]:\s*(.+\.exe[^\n]*)',
        task_content,
        re.IGNORECASE
    )
    if gui_match:
        config.app_type = AppType.GUI
        config.command = gui_match.group(1).strip()

        # Also look for window_title
        window_title_match = re.search(
            r'\[window_title\]:\s*([^\n]+)',
            task_content,
            re.IGNORECASE
        )
        if window_title_match:
            config.window_title = window_title_match.group(1).strip()

        return config.app_type, config

    # Check for TUI command pattern
    tui_match = re.search(
        r'\[tui\]:\s*([^\n]+)',
        task_content,
        re.IGNORECASE
    )
    if tui_match:
        config.app_type = AppType.TUI
        config.command = tui_match.group(1).strip()
        return config.app_type, config

    # Auto-detect from content
    content_lower = task_content.lower()
    if any(x in content_lower for x in ['localhost', 'http://', 'https://', 'browser', 'webpage']):
        config.app_type = AppType.WEBAPP
        # Try to find URL
        url_match = re.search(r'(https?://[^\s\)]+)', task_content)
        if url_match:
            config.url = url_match.group(1)
    elif any(x in content_lower for x in ['terminal', 'console', 'cli', 'command line', 'tui']):
        config.app_type = AppType.TUI
    elif any(x in content_lower for x in ['.exe', 'window', 'gui', 'application', 'desktop']):
        config.app_type = AppType.GUI

    return config.app_type, config


def launch_webapp_invisible(url: str, width: int = 1280, height: int = 720) -> subprocess.Popen:
    """
    Launch a headless browser to capture webapp.
    Uses Edge/Chrome in headless mode - completely invisible.
    """
    # Try Edge first (Windows default), then Chrome
    browsers = [
        ("msedge", ["msedge", "--headless", "--disable-gpu",
                    f"--window-size={width},{height}",
                    "--screenshot", "--hide-scrollbars"]),
        ("chrome", ["chrome", "--headless", "--disable-gpu",
                    f"--window-size={width},{height}",
                    "--screenshot", "--hide-scrollbars"]),
    ]

    for name, base_cmd in browsers:
        try:
            # Check if browser exists
            result = subprocess.run(
                ["where", name],
                capture_output=True,
                shell=True
            )
            if result.returncode == 0:
                cmd = base_cmd + [url]
                # Launch completely hidden using PowerShell
                ps_cmd = f'''
                $process = Start-Process -FilePath "{name}" -ArgumentList @(
                    "--headless=new",
                    "--disable-gpu",
                    "--window-size={width},{height}",
                    "--hide-scrollbars",
                    "{url}"
                ) -WindowStyle Hidden -PassThru
                $process.Id
                '''
                proc = subprocess.Popen(
                    ["powershell", "-Command", ps_cmd],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                return proc
        except FileNotFoundError:
            continue

    raise RuntimeError("No supported browser found (Edge or Chrome required)")


def launch_gui_invisible(command: str) -> subprocess.Popen:
    """
    Launch a GUI application without stealing focus.
    The window is created minimized to avoid disruption, but can still be captured.

    Uses SW_SHOWMINNOACTIVE to:
    - Show the window minimized
    - NOT activate it (no focus steal)
    - Allow PrintWindow to capture its content
    """
    # Parse command into executable and arguments
    parts = command.split()
    exe = parts[0]
    args = ' '.join(parts[1:]) if len(parts) > 1 else ''

    # Use PowerShell to launch without focus steal
    ps_script = f'''
    Add-Type @"
    using System;
    using System.Runtime.InteropServices;

    public class ProcessLauncher {{
        [DllImport("user32.dll")]
        public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);

        public const int SW_SHOWMINNOACTIVE = 7;
        public const int SW_RESTORE = 9;
    }}
"@

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = "{exe}"
    $psi.Arguments = "{args}"
    $psi.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Minimized
    $psi.UseShellExecute = $true

    $proc = [System.Diagnostics.Process]::Start($psi)

    # Wait for window to be created
    Start-Sleep -Milliseconds 500
    $proc.WaitForInputIdle(5000) | Out-Null

    # Restore window without activating (for PrintWindow capture)
    if ($proc.MainWindowHandle -ne [IntPtr]::Zero) {{
        [ProcessLauncher]::ShowWindow($proc.MainWindowHandle, [ProcessLauncher]::SW_RESTORE) | Out-Null
        # Immediately minimize again without activation
        Start-Sleep -Milliseconds 200
    }}

    Write-Output $proc.Id
    '''

    proc = subprocess.Popen(
        ["powershell", "-Command", ps_script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    return proc


def launch_tui_invisible(command: str, timeout: int = 30) -> Tuple[Optional[subprocess.CompletedProcess], str]:
    """
    Launch a TUI/CLI command invisibly and capture its output.
    Runs synchronously and captures output to a file.

    Args:
        command: The command to run
        timeout: Timeout in seconds

    Returns:
        Tuple of (CompletedProcess or None, output_file_path)
    """
    output_file = expand_path(tempfile.mktemp(suffix=".txt"))

    # Run command directly with subprocess and capture output
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW
        )

        # Write output to file
        output_content = result.stdout
        if result.stderr:
            output_content += "\n\nSTDERR:\n" + result.stderr

        Path(output_file).write_text(output_content, encoding='utf-8')
        return result, output_file

    except subprocess.TimeoutExpired:
        Path(output_file).write_text(f"Command timed out after {timeout} seconds", encoding='utf-8')
        return None, output_file
    except Exception as e:
        Path(output_file).write_text(f"Error running command: {str(e)}", encoding='utf-8')
        return None, output_file


def find_browser() -> Optional[str]:
    """Find Edge or Chrome browser executable path."""
    # Common browser locations on Windows
    browser_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]

    for path in browser_paths:
        if os.path.exists(path):
            return path

    return None


def capture_screenshot_webapp(url: str, output_path: str, width: int = 1280, height: int = 720) -> bool:
    """
    Capture a screenshot of a webpage using headless browser.
    Completely invisible - no window shown.
    """
    browser_path = find_browser()
    if not browser_path:
        print("No browser found (Edge or Chrome required)")
        return False

    # Escape paths for PowerShell
    browser_path_escaped = browser_path.replace("'", "''")
    output_path_escaped = output_path.replace("'", "''")

    ps_script = f'''
    $browserPath = '{browser_path_escaped}'
    $screenshotPath = '{output_path_escaped}'

    # Use headless mode with screenshot flag
    $args = @(
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--window-size={width},{height}",
        "--hide-scrollbars",
        "--screenshot=$screenshotPath",
        "{url}"
    )

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $browserPath
    $psi.Arguments = $args -join " "
    $psi.WindowStyle = "Hidden"
    $psi.CreateNoWindow = $true
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true

    try {{
        $proc = [System.Diagnostics.Process]::Start($psi)
        $proc.WaitForExit(30000)

        if (Test-Path $screenshotPath) {{
            Write-Output "SUCCESS"
        }} else {{
            Write-Output "FAILED: Screenshot not created"
        }}
    }} catch {{
        Write-Output "FAILED: $($_.Exception.Message)"
    }}
    '''

    result = subprocess.run(
        ["powershell", "-Command", ps_script],
        capture_output=True,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW
    )

    if "SUCCESS" in result.stdout:
        return Path(output_path).exists()
    else:
        print(f"Screenshot capture output: {result.stdout.strip()}")
        if result.stderr:
            print(f"Screenshot capture error: {result.stderr.strip()}")
        return False


def capture_screenshot_window(window_title: str, output_path: str) -> bool:
    """
    Capture a screenshot of a specific window by title using PrintWindow.
    This can capture windows even if they're not in the foreground.
    """
    output_path_escaped = output_path.replace("'", "''")

    ps_script = f'''
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing

    Add-Type -ReferencedAssemblies System.Drawing -TypeDefinition @"
    using System;
    using System.Drawing;
    using System.Drawing.Imaging;
    using System.Runtime.InteropServices;
    using System.Text;

    public class WindowCapture {{
        [DllImport("user32.dll")]
        public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);

        [DllImport("user32.dll")]
        public static extern bool PrintWindow(IntPtr hWnd, IntPtr hdcBlt, uint nFlags);

        [DllImport("user32.dll")]
        public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);

        [DllImport("user32.dll")]
        public static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);

        [DllImport("user32.dll")]
        public static extern bool IsWindow(IntPtr hWnd);

        [DllImport("user32.dll")]
        public static extern int GetWindowTextLength(IntPtr hWnd);

        public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

        [StructLayout(LayoutKind.Sequential)]
        public struct RECT {{
            public int Left;
            public int Top;
            public int Right;
            public int Bottom;
        }}

        public const uint PW_RENDERFULLCONTENT = 2;

        public static IntPtr FindWindowByTitle(string partialTitle) {{
            IntPtr foundHwnd = IntPtr.Zero;
            EnumWindows((hwnd, lParam) => {{
                int length = GetWindowTextLength(hwnd);
                if (length > 0) {{
                    StringBuilder sb = new StringBuilder(length + 1);
                    GetWindowText(hwnd, sb, sb.Capacity);
                    string title = sb.ToString();
                    if (title.IndexOf(partialTitle, StringComparison.OrdinalIgnoreCase) >= 0) {{
                        foundHwnd = hwnd;
                        return false;
                    }}
                }}
                return true;
            }}, IntPtr.Zero);
            return foundHwnd;
        }}

        public static Bitmap CaptureWindow(IntPtr hwnd) {{
            RECT rect;
            GetWindowRect(hwnd, out rect);
            int width = rect.Right - rect.Left;
            int height = rect.Bottom - rect.Top;

            if (width <= 0 || height <= 0) return null;

            Bitmap bmp = new Bitmap(width, height);
            using (Graphics g = Graphics.FromImage(bmp)) {{
                IntPtr hdc = g.GetHdc();
                PrintWindow(hwnd, hdc, PW_RENDERFULLCONTENT);
                g.ReleaseHdc(hdc);
            }}
            return bmp;
        }}
    }}
"@

    $targetTitle = "{window_title}"
    $hwnd = [WindowCapture]::FindWindowByTitle($targetTitle)

    if ($hwnd -eq [IntPtr]::Zero) {{
        Write-Output "WINDOW_NOT_FOUND"
        exit 1
    }}

    $bitmap = [WindowCapture]::CaptureWindow($hwnd)
    if ($bitmap -eq $null) {{
        Write-Output "CAPTURE_FAILED"
        exit 1
    }}

    $bitmap.Save('{output_path_escaped}')
    $bitmap.Dispose()

    Write-Output "SUCCESS"
    '''

    result = subprocess.run(
        ["powershell", "-Command", ps_script],
        capture_output=True,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
        timeout=30
    )

    if "SUCCESS" in result.stdout:
        return Path(output_path).exists()
    else:
        print(f"Window capture output: {result.stdout.strip()}")
        if result.stderr:
            print(f"Window capture error: {result.stderr.strip()}")
        return False


def capture_tui_output(output_file: str) -> Optional[str]:
    """Read captured TUI output from file."""
    try:
        if Path(output_file).exists():
            return Path(output_file).read_text(encoding='utf-8', errors='replace')
    except Exception:
        pass
    return None


def verify_with_claude(
    screenshot_path: str,
    task_items: List[str],
    acceptance_criteria: Optional[str] = None,
    app_type: AppType = AppType.UNKNOWN
) -> VerificationResult:
    """
    Use Claude CLI to verify task completion from screenshot.

    Args:
        screenshot_path: Path to screenshot image or TUI output text file
        task_items: List of task items to verify
        acceptance_criteria: Optional additional acceptance criteria
        app_type: Type of application being verified

    Returns:
        VerificationResult with Claude's assessment
    """
    import base64

    # Build the verification prompt
    items_list = "\n".join(f"- {item}" for item in task_items)

    base_prompt = f"""You are verifying whether tasks have been completed based on visual evidence.

## Application Type
{app_type.value.upper()}

## Tasks to Verify
{items_list}

{f"## Acceptance Criteria" + chr(10) + acceptance_criteria if acceptance_criteria else ""}

## Instructions
Analyze the provided {"screenshot" if app_type != AppType.TUI else "terminal output"} and determine which tasks appear to be completed.

For each task, respond with:
- COMPLETED: [task] - if you can see evidence the task is done
- NOT_COMPLETED: [task] - if the task does not appear to be done
- UNCERTAIN: [task] - if you cannot determine from the visual evidence

After listing each task status, provide a brief summary.

Respond in this exact JSON format:
```json
{{
  "results": [
    {{"task": "task description", "status": "COMPLETED|NOT_COMPLETED|UNCERTAIN", "evidence": "what you observed"}}
  ],
  "summary": "brief overall assessment",
  "all_completed": true/false
}}
```
"""

    # Call Claude CLI with the screenshot
    try:
        if app_type == AppType.TUI:
            # For TUI, read the text output and include it in the prompt
            tui_content = Path(screenshot_path).read_text(encoding='utf-8', errors='replace')
            full_prompt = base_prompt + f"\n\n## Terminal Output\n```\n{tui_content}\n```"
        else:
            # For GUI/webapp, encode image as base64 and include in prompt
            with open(screenshot_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')

            # Determine image type
            if screenshot_path.lower().endswith('.png'):
                mime_type = 'image/png'
            else:
                mime_type = 'image/jpeg'

            # Create a prompt that tells Claude to read the image file
            full_prompt = f"""I need you to analyze a screenshot to verify task completion.

The screenshot is saved at: {screenshot_path}

Please use the Read tool to view this image file, then answer the following:

{base_prompt}
"""

        # Use Claude CLI with the prompt
        # Write prompt to a temp file to avoid command line length issues
        prompt_file = Path(tempfile.gettempdir()) / "tool-reader-prompt.txt"
        prompt_file.write_text(full_prompt, encoding='utf-8')

        # Call Claude with the prompt file content piped in
        result = subprocess.run(
            ["claude", "-p", full_prompt, "--output-format", "text"],
            capture_output=True,
            text=True,
            timeout=120,  # 2 minute timeout
            creationflags=subprocess.CREATE_NO_WINDOW,
            cwd=Path(screenshot_path).parent  # Set working directory to screenshot location
        )

        response_text = result.stdout.strip()

        # If empty response, check stderr
        if not response_text and result.stderr:
            response_text = f"Error: {result.stderr.strip()}"

        # Parse the JSON response
        json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
        if json_match:
            try:
                response_data = json.loads(json_match.group(1))
            except json.JSONDecodeError:
                response_data = None
        else:
            # Try parsing the whole response as JSON
            try:
                response_data = json.loads(response_text)
            except json.JSONDecodeError:
                response_data = None

        if response_data is None:
            # Fallback: couldn't parse, return raw response
            return VerificationResult(
                success=False,
                completed_items=[],
                failed_items=task_items,
                claude_response=response_text if response_text else "No response from Claude CLI",
                screenshot_path=screenshot_path
            )

        # Extract results
        completed = []
        failed = []

        for item_result in response_data.get("results", []):
            task = item_result.get("task", "")
            status = item_result.get("status", "").upper()

            if status == "COMPLETED":
                completed.append(task)
            else:
                failed.append(task)

        return VerificationResult(
            success=response_data.get("all_completed", False),
            completed_items=completed,
            failed_items=failed,
            claude_response=response_text,
            screenshot_path=screenshot_path
        )

    except subprocess.TimeoutExpired:
        return VerificationResult(
            success=False,
            completed_items=[],
            failed_items=task_items,
            claude_response="Error: Claude CLI timed out",
            screenshot_path=screenshot_path
        )
    except FileNotFoundError:
        return VerificationResult(
            success=False,
            completed_items=[],
            failed_items=task_items,
            claude_response="Error: Claude CLI not found. Ensure 'claude' is in PATH.",
            screenshot_path=screenshot_path
        )
    except Exception as e:
        return VerificationResult(
            success=False,
            completed_items=[],
            failed_items=task_items,
            claude_response=f"Error: {str(e)}",
            screenshot_path=screenshot_path
        )


def expand_path(path: str) -> str:
    """Expand a path to its full form, resolving short names on Windows."""
    try:
        # Use pathlib to resolve the path
        resolved = Path(path).resolve()
        return str(resolved)
    except Exception:
        return path


def run_visual_verification(
    task_file_path: str,
    task_items: List[str],
    acceptance_criteria: Optional[str] = None,
    screenshot_dir: Optional[str] = None
) -> VerificationResult:
    """
    Main entry point for visual verification.

    1. Detects app type from task file
    2. Launches app invisibly if needed
    3. Captures screenshot
    4. Verifies with Claude CLI

    Args:
        task_file_path: Path to the task markdown file
        task_items: List of uncompleted task items to verify
        acceptance_criteria: Optional acceptance criteria text
        screenshot_dir: Optional directory for screenshots

    Returns:
        VerificationResult with Claude's assessment
    """
    # Read task file
    task_content = Path(task_file_path).read_text(encoding='utf-8')

    # Detect app type and config
    app_type, config = detect_app_type(task_content)

    if app_type == AppType.UNKNOWN:
        return VerificationResult(
            success=False,
            completed_items=[],
            failed_items=task_items,
            claude_response="Could not detect application type. Add [webapp]: URL, [gui]: command, or [tui]: command to the task file."
        )

    # Setup screenshot path - use user's temp dir with full path
    if screenshot_dir:
        screenshot_dir = Path(screenshot_dir).resolve()
    else:
        # Use a path without short names
        temp_base = os.path.expandvars(r"%TEMP%")
        screenshot_dir = Path(temp_base).resolve() / "tool-reader-screenshots"
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    timestamp = int(time.time())
    task_name = Path(task_file_path).stem

    if app_type == AppType.TUI:
        screenshot_path = expand_path(str(screenshot_dir / f"{task_name}_{timestamp}.txt"))
    else:
        screenshot_path = expand_path(str(screenshot_dir / f"{task_name}_{timestamp}.png"))

    # Capture based on app type
    try:
        if app_type == AppType.WEBAPP:
            if not config.url:
                return VerificationResult(
                    success=False,
                    completed_items=[],
                    failed_items=task_items,
                    claude_response="Webapp detected but no URL found. Add [webapp]: http://your-url to the task file."
                )

            print(f"Capturing webapp: {config.url}")
            success = capture_screenshot_webapp(
                config.url,
                screenshot_path,
                config.width,
                config.height
            )

            if not success:
                return VerificationResult(
                    success=False,
                    completed_items=[],
                    failed_items=task_items,
                    claude_response="Failed to capture webapp screenshot. Ensure Edge or Chrome is installed."
                )

        elif app_type == AppType.GUI:
            if config.command:
                print(f"Launching GUI invisibly: {config.command}")
                proc = launch_gui_invisible(config.command)
                time.sleep(config.wait_seconds)  # Wait for app to load

            if config.window_title:
                print(f"Capturing window: {config.window_title}")
                success = capture_screenshot_window(config.window_title, screenshot_path)

                if not success:
                    return VerificationResult(
                        success=False,
                        completed_items=[],
                        failed_items=task_items,
                        claude_response=f"Failed to capture GUI window '{config.window_title}'."
                    )
            else:
                return VerificationResult(
                    success=False,
                    completed_items=[],
                    failed_items=task_items,
                    claude_response="GUI detected but no window_title specified. Add window_title to config."
                )

        elif app_type == AppType.TUI:
            if not config.command:
                return VerificationResult(
                    success=False,
                    completed_items=[],
                    failed_items=task_items,
                    claude_response="TUI detected but no command found. Add [tui]: your-command to the task file."
                )

            print(f"Running TUI command invisibly: {config.command}")
            result, output_file = launch_tui_invisible(config.command)

            # Copy output to screenshot path
            tui_output = capture_tui_output(output_file)
            if tui_output and tui_output.strip():
                Path(screenshot_path).write_text(tui_output, encoding='utf-8')
            else:
                return VerificationResult(
                    success=False,
                    completed_items=[],
                    failed_items=task_items,
                    claude_response="Failed to capture TUI output."
                )

        # Verify with Claude
        print(f"Verifying with Claude CLI...")
        return verify_with_claude(
            screenshot_path,
            task_items,
            acceptance_criteria,
            app_type
        )

    except Exception as e:
        return VerificationResult(
            success=False,
            completed_items=[],
            failed_items=task_items,
            claude_response=f"Error during verification: {str(e)}"
        )


# =============================================================================
# CLAUDE TODO INTEGRATION
# =============================================================================

@dataclass
class TodoVerificationContext:
    """Context for verification triggered by todo state changes."""
    should_verify: bool
    phase: str
    progress: float
    triggers: List[str]
    task_file: Optional[str] = None


def check_todos_for_verification(
    todos_json: Optional[str] = None,
    context_text: Optional[str] = None
) -> TodoVerificationContext:
    """
    Check Claude's todo state to determine if verification should trigger.

    This function can be called:
    1. At the end of any phase (implementation, testing, build, etc.)
    2. When a verification-related todo is completed
    3. When all todos are marked complete

    Args:
        todos_json: JSON string from TodoWrite tool call
        context_text: Raw conversation context containing todo information

    Returns:
        TodoVerificationContext with verification decision and context
    """
    if not TODO_TRACKER_AVAILABLE:
        return TodoVerificationContext(
            should_verify=False,
            phase="unknown",
            progress=0,
            triggers=["Todo tracker not available"]
        )

    todos = []

    # Parse from JSON if provided
    if todos_json:
        try:
            data = json.loads(todos_json)
            if isinstance(data, dict) and "todos" in data:
                data = data["todos"]

            for item in data:
                from todo_tracker import TodoStatus, detect_phase, requires_verification
                status = TodoStatus(item.get("status", "pending"))
                content = item.get("content", "")
                todos.append(TodoItem(
                    content=content,
                    status=status,
                    active_form=item.get("activeForm", ""),
                    phase=detect_phase(content),
                    requires_verification=requires_verification(content)
                ))
        except (json.JSONDecodeError, KeyError, ValueError):
            pass

    # Parse from context text if provided and no JSON
    if not todos and context_text:
        todos = parse_todos_from_context(context_text)

    if not todos:
        return TodoVerificationContext(
            should_verify=False,
            phase="unknown",
            progress=0,
            triggers=["No todos found"]
        )

    # Check if verification is needed
    result = check_verification_needed(todos)

    return TodoVerificationContext(
        should_verify=result["needs_verification"],
        phase=result["phase"],
        progress=result["progress"],
        triggers=result["triggers"]
    )


def run_verification_with_todo_context(
    task_file_path: str,
    todos_json: Optional[str] = None,
    force: bool = False
) -> Tuple[bool, Optional[VerificationResult], TodoVerificationContext]:
    """
    Run visual verification if todo state indicates it's needed.

    This is the main integration point for tool-reader to use Claude's
    built-in task tracking for verification triggers.

    Args:
        task_file_path: Path to task markdown file
        todos_json: Optional JSON string of current todos
        force: Force verification regardless of todo state

    Returns:
        Tuple of (ran_verification, result, todo_context)
    """
    # Check todo state
    todo_context = check_todos_for_verification(todos_json=todos_json)

    if not force and not todo_context.should_verify:
        return False, None, todo_context

    # Parse task file to get items
    try:
        from parser import parse_task_file
        task = parse_task_file(Path(task_file_path))
        items = [item.text for item in task.items if not item.completed]
    except ImportError:
        # Fallback: just read the file and extract checklist items
        content = Path(task_file_path).read_text(encoding='utf-8')
        items = re.findall(r'- \[ \]\s*(.+?)(?:\n|$)', content)

    if not items:
        return False, None, todo_context

    # Run verification
    result = run_visual_verification(
        task_file_path,
        items
    )

    return True, result, todo_context


def format_todo_verification_report(
    verification_result: Optional[VerificationResult],
    todo_context: TodoVerificationContext
) -> str:
    """
    Format a comprehensive report combining todo state and verification results.
    """
    report = []
    report.append("=" * 60)
    report.append("VERIFICATION REPORT (Todo-Triggered)")
    report.append("=" * 60)

    # Todo context section
    report.append("\n## Todo State")
    report.append(f"- Phase: {todo_context.phase}")
    report.append(f"- Progress: {todo_context.progress}%")
    report.append(f"- Verification Triggered: {'Yes' if todo_context.should_verify else 'No'}")

    if todo_context.triggers:
        report.append("\n### Triggers:")
        for trigger in todo_context.triggers:
            report.append(f"  - {trigger}")

    # Verification results section
    if verification_result:
        report.append("\n## Visual Verification Results")
        report.append(f"- Success: {verification_result.success}")
        report.append(f"- Completed: {len(verification_result.completed_items)}")
        report.append(f"- Failed: {len(verification_result.failed_items)}")

        if verification_result.completed_items:
            report.append("\n### Completed Items:")
            for item in verification_result.completed_items:
                report.append(f"  [OK] {item}")

        if verification_result.failed_items:
            report.append("\n### Failed Items:")
            for item in verification_result.failed_items:
                report.append(f"  [!!] {item}")

        if verification_result.screenshot_path:
            report.append(f"\n### Screenshot: {verification_result.screenshot_path}")
    else:
        report.append("\n## Visual Verification")
        report.append("- Not run (todo state did not trigger)")

    report.append("\n" + "=" * 60)

    return "\n".join(report)


def get_verification_recommendation(todo_context: TodoVerificationContext) -> Dict[str, Any]:
    """
    Get a recommendation for whether to run verification.

    This can be used by Claude to decide whether to trigger /verify-tool.

    Returns:
        Dict with recommendation and reasoning
    """
    if todo_context.should_verify:
        # Determine priority based on triggers
        priority = "normal"
        if any("final" in t.lower() for t in todo_context.triggers):
            priority = "high"
        elif any("build" in t.lower() or "deploy" in t.lower() for t in todo_context.triggers):
            priority = "high"

        return {
            "recommend_verify": True,
            "priority": priority,
            "reason": todo_context.triggers[0] if todo_context.triggers else "Phase completed",
            "phase": todo_context.phase,
            "progress": todo_context.progress,
            "action": "Run /verify-tool to visually confirm the completed work"
        }
    else:
        return {
            "recommend_verify": False,
            "priority": "none",
            "reason": "No verification triggers detected",
            "phase": todo_context.phase,
            "progress": todo_context.progress,
            "action": "Continue with remaining tasks"
        }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Visual verification for Tool Reader")
    parser.add_argument("task_file", help="Path to task markdown file")
    parser.add_argument("--items", nargs="+", help="Task items to verify")
    parser.add_argument("--criteria", help="Acceptance criteria")
    parser.add_argument("--screenshot-dir", help="Directory for screenshots")
    parser.add_argument("--todos", help="JSON string of todos for auto-trigger check")
    parser.add_argument("--check-todos", action="store_true",
                        help="Only check if todos indicate verification needed")

    args = parser.parse_args()

    # If just checking todos
    if args.check_todos:
        todo_ctx = check_todos_for_verification(todos_json=args.todos)
        recommendation = get_verification_recommendation(todo_ctx)

        print("\n" + "=" * 50)
        print("TODO VERIFICATION CHECK")
        print("=" * 50)
        print(f"Recommend Verify: {recommendation['recommend_verify']}")
        print(f"Priority: {recommendation['priority']}")
        print(f"Phase: {recommendation['phase']}")
        print(f"Progress: {recommendation['progress']}%")
        print(f"Reason: {recommendation['reason']}")
        print(f"Action: {recommendation['action']}")
        sys.exit(0)

    # Normal verification flow
    if not args.items:
        # Parse items from task file
        from parser import parse_task_file
        task = parse_task_file(Path(args.task_file))
        items = [item.text for item in task.items if not item.completed]
    else:
        items = args.items

    result = run_visual_verification(
        args.task_file,
        items,
        args.criteria,
        args.screenshot_dir
    )

    # If todos provided, include in report
    if args.todos:
        todo_ctx = check_todos_for_verification(todos_json=args.todos)
        print(format_todo_verification_report(result, todo_ctx))
    else:
        print("\n" + "=" * 50)
        print("VERIFICATION RESULT")
        print("=" * 50)
        print(f"Success: {result.success}")
        print(f"\nCompleted Items ({len(result.completed_items)}):")
        for item in result.completed_items:
            print(f"  [DONE] {item}")
        print(f"\nFailed Items ({len(result.failed_items)}):")
        for item in result.failed_items:
            print(f"  [FAIL] {item}")
        if result.screenshot_path:
            print(f"\nScreenshot: {result.screenshot_path}")
        print(f"\nClaude Response:\n{result.claude_response}")
