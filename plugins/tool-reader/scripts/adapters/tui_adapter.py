#!/usr/bin/env python3
"""
TUI adapter for tool-reader.
Captures TUI applications as PNG screenshots using a hidden Windows desktop.

This adapter creates an invisible desktop, launches a terminal window
running the TUI application, and captures real PNG screenshots using
the PrintWindow Win32 API.
"""

import os
import subprocess
import time
import asyncio
import json
from pathlib import Path
from typing import Optional, List, Dict, Any

from .base import (
    CaptureAdapter,
    CaptureResult,
    CaptureOptions,
    CaptureType,
    AdapterType,
)


class TuiAdapter(CaptureAdapter):
    """
    Capture adapter for terminal UI applications.

    Uses a hidden Windows desktop to:
    1. Launch a terminal window invisibly
    2. Run the TUI application
    3. Capture PNG screenshots via PrintWindow API
    4. Send keyboard input for interaction
    """

    adapter_type = AdapterType.TUI
    capture_type = CaptureType.SCREENSHOT  # Now produces PNG, not ANSI text

    def __init__(self, options: Optional[CaptureOptions] = None):
        super().__init__(options)
        self._desktop_name = f"TuiCapture_{int(time.time() * 1000)}"
        self._process_id = None
        self._window_hwnd = None
        self._session_data = None

    @classmethod
    def can_handle(cls, target: str) -> bool:
        """Check if this adapter can handle the target."""
        target_lower = target.lower()
        return (
            target.startswith("tui:") or
            "ratatui" in target_lower or
            "crossterm" in target_lower or
            "tui" in target_lower or
            # Cargo run for Rust TUI apps
            (target_lower.startswith("cargo run") and any(
                x in target_lower for x in ["--", "tui", "terminal"]
            ))
        )

    async def capture(self, target: str, options: Optional[CaptureOptions] = None) -> CaptureResult:
        """
        Capture TUI application as PNG screenshot.

        Creates a hidden desktop, launches terminal with TUI,
        and captures via PrintWindow API.

        Args:
            target: Command to run (e.g., "cargo run", "tui:cargo run")
            options: Optional capture options

        Returns:
            CaptureResult with PNG screenshot path
        """
        opts = options or self.options
        command = target[4:] if target.startswith("tui:") else target
        output_path = self._get_output_path(".png")

        try:
            # Wait before capture if specified
            if opts.wait_before > 0:
                await asyncio.sleep(opts.wait_before)

            # Single-shot capture: create desktop, capture, cleanup
            result = self._capture_tui_on_hidden_desktop(
                command=command,
                output_path=str(output_path),
                timeout=opts.timeout,
                width=opts.width,
                height=opts.height
            )

            if result.get("success") and output_path.exists():
                capture_result = CaptureResult(
                    success=True,
                    capture_type=CaptureType.SCREENSHOT,
                    content_path=str(output_path),
                    metadata={
                        "command": command,
                        "desktop_name": result.get("desktop_name"),
                        "window_title": result.get("window_title"),
                        "capture_method": "hidden_desktop_printwindow"
                    }
                )
                self.captures.append(capture_result)
                return capture_result
            else:
                return CaptureResult(
                    success=False,
                    capture_type=CaptureType.SCREENSHOT,
                    error=result.get("error", "Unknown capture error")
                )

        except Exception as e:
            return CaptureResult(
                success=False,
                capture_type=CaptureType.SCREENSHOT,
                error=str(e)
            )

    def _capture_tui_on_hidden_desktop(
        self,
        command: str,
        output_path: str,
        timeout: float = 30.0,
        width: int = 1280,
        height: int = 720
    ) -> Dict[str, Any]:
        """
        Execute the full hidden desktop capture workflow.

        Returns dict with success status and metadata.
        """
        output_path_escaped = output_path.replace("'", "''")
        command_escaped = command.replace('"', '`"').replace("'", "''")
        desktop_name = self._desktop_name

        # PowerShell script with C# for hidden desktop capture
        ps_script = f'''
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

Add-Type -ReferencedAssemblies System.Drawing -TypeDefinition @"
using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;
using System.Text;
using System.Diagnostics;
using System.Threading;

public class HiddenDesktopCapture {{
    // Desktop APIs
    [DllImport("user32.dll", SetLastError = true)]
    public static extern IntPtr CreateDesktop(
        string lpszDesktop, IntPtr lpszDevice, IntPtr pDevmode,
        uint dwFlags, uint dwDesiredAccess, IntPtr lpsa);

    [DllImport("user32.dll", SetLastError = true)]
    public static extern bool CloseDesktop(IntPtr hDesktop);

    [DllImport("user32.dll", SetLastError = true)]
    public static extern bool SetThreadDesktop(IntPtr hDesktop);

    [DllImport("user32.dll", SetLastError = true)]
    public static extern IntPtr GetThreadDesktop(uint dwThreadId);

    [DllImport("kernel32.dll")]
    public static extern uint GetCurrentThreadId();

    // Process APIs
    [DllImport("kernel32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    public static extern bool CreateProcess(
        string lpApplicationName, string lpCommandLine,
        IntPtr lpProcessAttributes, IntPtr lpThreadAttributes,
        bool bInheritHandles, uint dwCreationFlags,
        IntPtr lpEnvironment, string lpCurrentDirectory,
        ref STARTUPINFO lpStartupInfo, out PROCESS_INFORMATION lpProcessInformation);

    [DllImport("kernel32.dll")]
    public static extern bool TerminateProcess(IntPtr hProcess, uint uExitCode);

    [DllImport("kernel32.dll")]
    public static extern bool CloseHandle(IntPtr hObject);

    // Window APIs
    [DllImport("user32.dll")]
    public static extern bool EnumDesktopWindows(IntPtr hDesktop, EnumWindowsProc lpfn, IntPtr lParam);

    [DllImport("user32.dll")]
    public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);

    [DllImport("user32.dll")]
    public static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);

    [DllImport("user32.dll")]
    public static extern int GetWindowTextLength(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool IsWindowVisible(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);

    [DllImport("user32.dll")]
    public static extern bool PrintWindow(IntPtr hWnd, IntPtr hdcBlt, uint nFlags);

    [DllImport("user32.dll")]
    public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);

    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);

    // Structs
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    public struct STARTUPINFO {{
        public int cb;
        public string lpReserved;
        public string lpDesktop;
        public string lpTitle;
        public int dwX;
        public int dwY;
        public int dwXSize;
        public int dwYSize;
        public int dwXCountChars;
        public int dwYCountChars;
        public int dwFillAttribute;
        public int dwFlags;
        public short wShowWindow;
        public short cbReserved2;
        public IntPtr lpReserved2;
        public IntPtr hStdInput;
        public IntPtr hStdOutput;
        public IntPtr hStdError;
    }}

    [StructLayout(LayoutKind.Sequential)]
    public struct PROCESS_INFORMATION {{
        public IntPtr hProcess;
        public IntPtr hThread;
        public int dwProcessId;
        public int dwThreadId;
    }}

    [StructLayout(LayoutKind.Sequential)]
    public struct RECT {{
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }}

    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

    // Constants
    public const uint GENERIC_ALL = 0x10000000;
    public const uint CREATE_NEW_CONSOLE = 0x00000010;
    public const int STARTF_USESHOWWINDOW = 0x00000001;
    public const int SW_SHOW = 5;
    public const int SW_HIDE = 0;
    public const uint PW_RENDERFULLCONTENT = 2;

    private static IntPtr foundHwnd = IntPtr.Zero;
    private static int targetPid = 0;

    public static string CaptureToFile(string desktopName, string command, string outputPath, int waitMs, int width, int height) {{
        IntPtr hDesktop = IntPtr.Zero;
        IntPtr hOrigDesktop = IntPtr.Zero;
        PROCESS_INFORMATION pi = new PROCESS_INFORMATION();
        string result = "";

        try {{
            // Save original desktop
            hOrigDesktop = GetThreadDesktop(GetCurrentThreadId());

            // Create hidden desktop
            hDesktop = CreateDesktop(desktopName, IntPtr.Zero, IntPtr.Zero, 0, GENERIC_ALL, IntPtr.Zero);
            if (hDesktop == IntPtr.Zero) {{
                return "ERROR:CreateDesktop failed - " + Marshal.GetLastWin32Error();
            }}

            // Setup process on hidden desktop
            STARTUPINFO si = new STARTUPINFO();
            si.cb = Marshal.SizeOf(si);
            si.lpDesktop = desktopName;
            si.dwFlags = STARTF_USESHOWWINDOW;
            si.wShowWindow = SW_SHOW;
            si.dwXSize = width;
            si.dwYSize = height;

            // Launch cmd.exe with the TUI command
            string cmdLine = "cmd.exe /c " + command;

            bool created = CreateProcess(
                null, cmdLine,
                IntPtr.Zero, IntPtr.Zero,
                false, CREATE_NEW_CONSOLE,
                IntPtr.Zero, null,
                ref si, out pi);

            if (!created) {{
                return "ERROR:CreateProcess failed - " + Marshal.GetLastWin32Error();
            }}

            targetPid = pi.dwProcessId;

            // Wait for TUI to render
            Thread.Sleep(waitMs);

            // Switch to hidden desktop to enumerate windows
            if (!SetThreadDesktop(hDesktop)) {{
                return "ERROR:SetThreadDesktop failed - " + Marshal.GetLastWin32Error();
            }}

            // Find window by process ID
            foundHwnd = IntPtr.Zero;
            EnumWindows((hwnd, lParam) => {{
                uint windowPid;
                GetWindowThreadProcessId(hwnd, out windowPid);
                if ((int)windowPid == targetPid) {{
                    foundHwnd = hwnd;
                    return false;
                }}
                return true;
            }}, IntPtr.Zero);

            // Restore original desktop before capture
            SetThreadDesktop(hOrigDesktop);

            if (foundHwnd == IntPtr.Zero) {{
                return "ERROR:Window not found for PID " + targetPid;
            }}

            // Capture window
            RECT rect;
            GetWindowRect(foundHwnd, out rect);
            int winWidth = rect.Right - rect.Left;
            int winHeight = rect.Bottom - rect.Top;

            if (winWidth <= 0 || winHeight <= 0) {{
                return "ERROR:Invalid window dimensions";
            }}

            using (Bitmap bmp = new Bitmap(winWidth, winHeight)) {{
                using (Graphics g = Graphics.FromImage(bmp)) {{
                    IntPtr hdc = g.GetHdc();
                    PrintWindow(foundHwnd, hdc, PW_RENDERFULLCONTENT);
                    g.ReleaseHdc(hdc);
                }}
                bmp.Save(outputPath, ImageFormat.Png);
            }}

            result = "SUCCESS:" + foundHwnd.ToString() + ":" + targetPid.ToString();

        }} catch (Exception ex) {{
            result = "ERROR:" + ex.Message;
        }} finally {{
            // Cleanup
            if (pi.hProcess != IntPtr.Zero) {{
                TerminateProcess(pi.hProcess, 0);
                CloseHandle(pi.hProcess);
            }}
            if (pi.hThread != IntPtr.Zero) {{
                CloseHandle(pi.hThread);
            }}
            if (hDesktop != IntPtr.Zero) {{
                CloseDesktop(hDesktop);
            }}
        }}

        return result;
    }}
}}
"@

$result = [HiddenDesktopCapture]::CaptureToFile(
    "{desktop_name}",
    "{command_escaped}",
    "{output_path_escaped}",
    3000,
    {width},
    {height}
)

Write-Output $result
'''

        try:
            result = subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                capture_output=True,
                text=True,
                timeout=timeout + 10,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            output = result.stdout.strip()

            if output.startswith("SUCCESS:"):
                parts = output.split(":")
                return {
                    "success": True,
                    "desktop_name": desktop_name,
                    "window_hwnd": parts[1] if len(parts) > 1 else None,
                    "process_id": parts[2] if len(parts) > 2 else None
                }
            else:
                return {
                    "success": False,
                    "error": output
                }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Capture timed out after {timeout} seconds"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def start_session(self, target: str) -> bool:
        """
        Start a persistent TUI session on a hidden desktop.

        This keeps the TUI running for multiple captures and interactions.
        """
        command = target[4:] if target.startswith("tui:") else target

        result = self._start_persistent_session(
            command=command,
            width=self.options.width,
            height=self.options.height
        )

        if result.get("success"):
            self._session_active = True
            self._session_data = result
            self._process_id = result.get("process_id")
            self._window_hwnd = result.get("window_hwnd")
            return True

        return False

    def _start_persistent_session(
        self,
        command: str,
        width: int = 1280,
        height: int = 720
    ) -> Dict[str, Any]:
        """
        Start TUI on hidden desktop without terminating.

        Returns session info for later capture/interaction.
        """
        command_escaped = command.replace('"', '`"').replace("'", "''")
        desktop_name = self._desktop_name

        ps_script = f'''
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
using System.Text;

public class TuiSession {{
    [DllImport("user32.dll", SetLastError = true)]
    public static extern IntPtr CreateDesktop(
        string lpszDesktop, IntPtr lpszDevice, IntPtr pDevmode,
        uint dwFlags, uint dwDesiredAccess, IntPtr lpsa);

    [DllImport("kernel32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    public static extern bool CreateProcess(
        string lpApplicationName, string lpCommandLine,
        IntPtr lpProcessAttributes, IntPtr lpThreadAttributes,
        bool bInheritHandles, uint dwCreationFlags,
        IntPtr lpEnvironment, string lpCurrentDirectory,
        ref STARTUPINFO lpStartupInfo, out PROCESS_INFORMATION lpProcessInformation);

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    public struct STARTUPINFO {{
        public int cb;
        public string lpReserved;
        public string lpDesktop;
        public string lpTitle;
        public int dwX, dwY, dwXSize, dwYSize;
        public int dwXCountChars, dwYCountChars, dwFillAttribute, dwFlags;
        public short wShowWindow, cbReserved2;
        public IntPtr lpReserved2, hStdInput, hStdOutput, hStdError;
    }}

    [StructLayout(LayoutKind.Sequential)]
    public struct PROCESS_INFORMATION {{
        public IntPtr hProcess, hThread;
        public int dwProcessId, dwThreadId;
    }}

    public const uint GENERIC_ALL = 0x10000000;
    public const uint CREATE_NEW_CONSOLE = 0x00000010;
    public const int STARTF_USESHOWWINDOW = 0x00000001;
    public const int SW_SHOW = 5;

    public static string StartSession(string desktopName, string command, int width, int height) {{
        IntPtr hDesktop = CreateDesktop(desktopName, IntPtr.Zero, IntPtr.Zero, 0, GENERIC_ALL, IntPtr.Zero);
        if (hDesktop == IntPtr.Zero) return "ERROR:CreateDesktop";

        STARTUPINFO si = new STARTUPINFO();
        si.cb = Marshal.SizeOf(si);
        si.lpDesktop = desktopName;
        si.dwFlags = STARTF_USESHOWWINDOW;
        si.wShowWindow = SW_SHOW;
        si.dwXSize = width;
        si.dwYSize = height;

        PROCESS_INFORMATION pi;
        string cmdLine = "cmd.exe /c " + command;

        if (!CreateProcess(null, cmdLine, IntPtr.Zero, IntPtr.Zero, false, CREATE_NEW_CONSOLE, IntPtr.Zero, null, ref si, out pi)) {{
            return "ERROR:CreateProcess";
        }}

        // Return session info as JSON-like string
        return "SUCCESS:" + hDesktop.ToInt64() + ":" + pi.dwProcessId + ":" + pi.hProcess.ToInt64();
    }}
}}
"@

$result = [TuiSession]::StartSession("{desktop_name}", "{command_escaped}", {width}, {height})
Write-Output $result
'''

        try:
            result = subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                capture_output=True,
                text=True,
                timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            output = result.stdout.strip()

            if output.startswith("SUCCESS:"):
                parts = output.split(":")
                return {
                    "success": True,
                    "desktop_handle": parts[1] if len(parts) > 1 else None,
                    "process_id": int(parts[2]) if len(parts) > 2 else None,
                    "process_handle": parts[3] if len(parts) > 3 else None,
                    "desktop_name": desktop_name
                }
            else:
                return {"success": False, "error": output}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def capture_on_event(
        self,
        target: str,
        event: str,
        selector: Optional[str] = None,
        options: Optional[CaptureOptions] = None
    ) -> CaptureResult:
        """
        Capture TUI after performing an action.

        Events:
        - "key": Send keypress (selector = key name like "enter", "tab", "up")
        - "input": Send text input (selector = text to send)
        - "wait": Wait then capture (selector = seconds as string)
        """
        opts = options or self.options

        if not self._session_active:
            # Start session if not active
            await self.start_session(target)
            await asyncio.sleep(2)  # Wait for TUI to render

        # Perform the event action
        if event == "key" and selector:
            await self._send_key(selector)
            await asyncio.sleep(0.5)  # Wait for TUI to update

        elif event == "input" and selector:
            await self._send_input(selector)
            await asyncio.sleep(0.5)

        elif event == "wait" and selector:
            await asyncio.sleep(float(selector))

        # Now capture
        output_path = self._get_output_path(".png")
        success = self._capture_session_window(str(output_path))

        if success and output_path.exists():
            result = CaptureResult(
                success=True,
                capture_type=CaptureType.SCREENSHOT,
                content_path=str(output_path),
                event=f"{event}:{selector}",
                metadata={
                    "event": event,
                    "selector": selector,
                    "process_id": self._process_id
                }
            )
            self.captures.append(result)
            return result

        return CaptureResult(
            success=False,
            capture_type=CaptureType.SCREENSHOT,
            event=f"{event}:{selector}",
            error="Failed to capture after event"
        )

    async def _send_key(self, key: str) -> bool:
        """Send a keypress to the TUI window."""
        if not self._process_id:
            return False

        # Map key names to virtual key codes
        key_map = {
            "enter": "0x0D", "return": "0x0D",
            "tab": "0x09",
            "escape": "0x1B", "esc": "0x1B",
            "up": "0x26",
            "down": "0x28",
            "left": "0x25",
            "right": "0x27",
            "space": "0x20",
            "backspace": "0x08",
            "delete": "0x2E",
            "home": "0x24",
            "end": "0x23",
            "pageup": "0x21",
            "pagedown": "0x22",
            "f1": "0x70", "f2": "0x71", "f3": "0x72", "f4": "0x73",
            "f5": "0x74", "f6": "0x75", "f7": "0x76", "f8": "0x77",
            "f10": "0x79", "f11": "0x7A", "f12": "0x7B",
        }

        vk_code = key_map.get(key.lower(), None)

        # For single characters, use their ASCII value
        if not vk_code and len(key) == 1:
            vk_code = hex(ord(key.upper()))

        if not vk_code:
            return False

        ps_script = f'''
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;

public class KeySender {{
    [DllImport("user32.dll")]
    public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, UIntPtr dwExtraInfo);

    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern IntPtr FindWindow(string lpClassName, string lpWindowName);

    [DllImport("user32.dll")]
    public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);

    [DllImport("user32.dll")]
    public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);

    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

    public const uint KEYEVENTF_KEYUP = 0x0002;

    private static IntPtr targetHwnd = IntPtr.Zero;
    private static int targetPid = 0;

    public static void SendKey(int processId, byte vkCode) {{
        targetPid = processId;
        targetHwnd = IntPtr.Zero;

        // Find window by process ID
        EnumWindows((hwnd, lParam) => {{
            uint windowPid;
            GetWindowThreadProcessId(hwnd, out windowPid);
            if ((int)windowPid == targetPid) {{
                targetHwnd = hwnd;
                return false;
            }}
            return true;
        }}, IntPtr.Zero);

        if (targetHwnd != IntPtr.Zero) {{
            SetForegroundWindow(targetHwnd);
            System.Threading.Thread.Sleep(50);
            keybd_event(vkCode, 0, 0, UIntPtr.Zero);
            keybd_event(vkCode, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
        }}
    }}
}}
"@

[KeySender]::SendKey({self._process_id}, {vk_code})
'''

        try:
            subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                capture_output=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            return True
        except Exception:
            return False

    async def _send_input(self, text: str) -> bool:
        """Send text input to the TUI window."""
        # Send each character as a keypress
        for char in text:
            await self._send_key(char)
            await asyncio.sleep(0.05)
        return True

    def _capture_session_window(self, output_path: str) -> bool:
        """Capture the current session's TUI window."""
        if not self._process_id:
            return False

        output_path_escaped = output_path.replace("'", "''")

        ps_script = f'''
Add-Type -AssemblyName System.Drawing

Add-Type -TypeDefinition @"
using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;

public class SessionCapture {{
    [DllImport("user32.dll")]
    public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);

    [DllImport("user32.dll")]
    public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);

    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);

    [DllImport("user32.dll")]
    public static extern bool PrintWindow(IntPtr hWnd, IntPtr hdcBlt, uint nFlags);

    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

    [StructLayout(LayoutKind.Sequential)]
    public struct RECT {{ public int Left, Top, Right, Bottom; }}

    public const uint PW_RENDERFULLCONTENT = 2;

    private static IntPtr targetHwnd = IntPtr.Zero;
    private static int targetPid = 0;

    public static bool CaptureByPid(int processId, string outputPath) {{
        targetPid = processId;
        targetHwnd = IntPtr.Zero;

        EnumWindows((hwnd, lParam) => {{
            uint windowPid;
            GetWindowThreadProcessId(hwnd, out windowPid);
            if ((int)windowPid == targetPid) {{
                targetHwnd = hwnd;
                return false;
            }}
            return true;
        }}, IntPtr.Zero);

        if (targetHwnd == IntPtr.Zero) return false;

        RECT rect;
        GetWindowRect(targetHwnd, out rect);
        int width = rect.Right - rect.Left;
        int height = rect.Bottom - rect.Top;
        if (width <= 0 || height <= 0) return false;

        using (Bitmap bmp = new Bitmap(width, height)) {{
            using (Graphics g = Graphics.FromImage(bmp)) {{
                IntPtr hdc = g.GetHdc();
                PrintWindow(targetHwnd, hdc, PW_RENDERFULLCONTENT);
                g.ReleaseHdc(hdc);
            }}
            bmp.Save(outputPath, ImageFormat.Png);
        }}
        return true;
    }}
}}
"@

$result = [SessionCapture]::CaptureByPid({self._process_id}, "{output_path_escaped}")
Write-Output $result
'''

        try:
            result = subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                capture_output=True,
                text=True,
                timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            return "True" in result.stdout
        except Exception:
            return False

    async def end_session(self) -> List[CaptureResult]:
        """End TUI session and cleanup."""
        if self._session_data:
            # Terminate the process and close desktop
            self._cleanup_session()

        self._session_active = False
        self._session_data = None
        self._process_id = None
        self._window_hwnd = None

        return self.captures

    def _cleanup_session(self):
        """Cleanup hidden desktop and terminate process."""
        if not self._session_data:
            return

        process_handle = self._session_data.get("process_handle")
        desktop_handle = self._session_data.get("desktop_handle")

        ps_script = f'''
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;

public class TuiCleanup {{
    [DllImport("kernel32.dll")]
    public static extern bool TerminateProcess(IntPtr hProcess, uint uExitCode);

    [DllImport("kernel32.dll")]
    public static extern bool CloseHandle(IntPtr hObject);

    [DllImport("user32.dll")]
    public static extern bool CloseDesktop(IntPtr hDesktop);

    public static void Cleanup(long processHandle, long desktopHandle) {{
        if (processHandle != 0) {{
            TerminateProcess(new IntPtr(processHandle), 0);
            CloseHandle(new IntPtr(processHandle));
        }}
        if (desktopHandle != 0) {{
            CloseDesktop(new IntPtr(desktopHandle));
        }}
    }}
}}
"@

[TuiCleanup]::Cleanup({process_handle or 0}, {desktop_handle or 0})
'''

        try:
            subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                capture_output=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
        except Exception:
            pass
