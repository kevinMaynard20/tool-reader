#!/usr/bin/env python3
"""
GUI adapter for tool-reader.
Captures desktop application windows using Windows APIs.
"""

import os
import subprocess
import time
from pathlib import Path
from typing import Optional

from .base import (
    CaptureAdapter,
    CaptureResult,
    CaptureOptions,
    CaptureType,
    AdapterType,
)


class GuiAdapter(CaptureAdapter):
    """
    Capture adapter for desktop GUI applications.

    Uses Windows PrintWindow API to capture window contents
    without requiring the window to be in foreground.
    """

    adapter_type = AdapterType.GUI
    capture_type = CaptureType.SCREENSHOT

    def __init__(self, options: Optional[CaptureOptions] = None):
        super().__init__(options)
        self._launched_process = None

    @classmethod
    def can_handle(cls, target: str) -> bool:
        """Check if this adapter can handle the target."""
        return (
            target.startswith("window:") or
            target.endswith(".exe") or
            target.startswith("gui:")
        )

    async def capture(self, target: str, options: Optional[CaptureOptions] = None) -> CaptureResult:
        """
        Capture GUI application window.

        Args:
            target: Window title (window:Title) or executable path
            options: Optional capture options

        Returns:
            CaptureResult with screenshot path
        """
        opts = options or self.options
        output_path = self._get_output_path(".png")

        # Parse target
        if target.startswith("window:"):
            window_title = target[7:]
            command = None
        elif target.startswith("gui:"):
            # gui:command|window_title
            parts = target[4:].split("|")
            command = parts[0]
            window_title = parts[1] if len(parts) > 1 else None
        else:
            command = target
            window_title = None

        try:
            # Launch app if command provided
            if command:
                self._launched_process = await self._launch_gui_app(command)
                time.sleep(opts.wait_before or 2.0)  # Wait for app to load

                # Try to detect window title from process if not provided
                if not window_title:
                    window_title = self._get_window_title_from_process()

            if not window_title:
                return CaptureResult(
                    success=False,
                    capture_type=CaptureType.SCREENSHOT,
                    error="Window title required. Use 'window:Title' or 'gui:command|Title'"
                )

            # Capture window
            success = self._capture_window(window_title, str(output_path))

            if success and output_path.exists():
                result = CaptureResult(
                    success=True,
                    capture_type=CaptureType.SCREENSHOT,
                    content_path=str(output_path),
                    metadata={
                        "window_title": window_title,
                        "command": command
                    }
                )
                self.captures.append(result)
                return result
            else:
                return CaptureResult(
                    success=False,
                    capture_type=CaptureType.SCREENSHOT,
                    error=f"Failed to capture window '{window_title}'"
                )

        except Exception as e:
            return CaptureResult(
                success=False,
                capture_type=CaptureType.SCREENSHOT,
                error=str(e)
            )

    async def _launch_gui_app(self, command: str) -> Optional[subprocess.Popen]:
        """
        Launch a GUI application without stealing focus.
        """
        parts = command.split()
        exe = parts[0]
        args = ' '.join(parts[1:]) if len(parts) > 1 else ''

        ps_script = f'''
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = "{exe}"
        $psi.Arguments = "{args}"
        $psi.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Minimized
        $psi.UseShellExecute = $true

        $proc = [System.Diagnostics.Process]::Start($psi)
        Start-Sleep -Milliseconds 500
        $proc.WaitForInputIdle(5000) | Out-Null

        Write-Output $proc.Id
        '''

        proc = subprocess.Popen(
            ["powershell", "-Command", ps_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        return proc

    def _get_window_title_from_process(self) -> Optional[str]:
        """Try to get window title from launched process."""
        # This would require more complex Win32 API calls
        # For now, return None and require explicit window title
        return None

    def _capture_window(self, window_title: str, output_path: str) -> bool:
        """
        Capture a screenshot of a specific window by title using PrintWindow.
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

            [DllImport("user32.dll")]
            public static extern bool IsWindowVisible(IntPtr hWnd);

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
                    if (!IsWindowVisible(hwnd)) return true;

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

        try:
            result = subprocess.run(
                ["powershell", "-Command", ps_script],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                timeout=30
            )

            return "SUCCESS" in result.stdout and Path(output_path).exists()

        except Exception:
            return False

    async def end_session(self):
        """End session and cleanup launched process."""
        if self._launched_process:
            try:
                self._launched_process.terminate()
            except Exception:
                pass
        return await super().end_session()
