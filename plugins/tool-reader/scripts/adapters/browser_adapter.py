#!/usr/bin/env python3
"""
Browser adapter for tool-reader.
Uses headless Chrome/Edge for webpage screenshots (fallback when Playwright unavailable).
"""

import os
import subprocess
import time
from pathlib import Path
from typing import Optional, List

from .base import (
    CaptureAdapter,
    CaptureResult,
    CaptureOptions,
    CaptureType,
    AdapterType,
)


class BrowserAdapter(CaptureAdapter):
    """
    Capture adapter using headless Chrome/Edge.

    This is a fallback when Playwright is not available.
    Uses the browser's built-in --screenshot flag for capture.
    """

    adapter_type = AdapterType.BROWSER
    capture_type = CaptureType.SCREENSHOT

    def __init__(self, options: Optional[CaptureOptions] = None):
        super().__init__(options)
        self.browser_path = self._find_browser()

    def _find_browser(self) -> Optional[str]:
        """Find Edge or Chrome browser executable path."""
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

    @classmethod
    def can_handle(cls, target: str) -> bool:
        """Check if this adapter can handle the target."""
        return target.startswith("http://") or target.startswith("https://")

    async def capture(self, target: str, options: Optional[CaptureOptions] = None) -> CaptureResult:
        """
        Capture screenshot of webpage using headless browser.

        Args:
            target: URL to capture
            options: Optional capture options

        Returns:
            CaptureResult with screenshot path
        """
        opts = options or self.options

        if not self.browser_path:
            return CaptureResult(
                success=False,
                capture_type=CaptureType.SCREENSHOT,
                error="No browser found (Edge or Chrome required)"
            )

        output_path = self._get_output_path(".png")

        try:
            # Wait before capture if specified
            if opts.wait_before > 0:
                time.sleep(opts.wait_before)

            success = self._capture_with_browser(
                target,
                str(output_path),
                opts.width,
                opts.height
            )

            if success and output_path.exists():
                result = CaptureResult(
                    success=True,
                    capture_type=CaptureType.SCREENSHOT,
                    content_path=str(output_path),
                    metadata={
                        "url": target,
                        "browser": self.browser_path,
                        "width": opts.width,
                        "height": opts.height
                    }
                )
                self.captures.append(result)
                return result
            else:
                return CaptureResult(
                    success=False,
                    capture_type=CaptureType.SCREENSHOT,
                    error="Failed to capture screenshot"
                )

        except Exception as e:
            return CaptureResult(
                success=False,
                capture_type=CaptureType.SCREENSHOT,
                error=str(e)
            )

    def _capture_with_browser(
        self,
        url: str,
        output_path: str,
        width: int = 1280,
        height: int = 720
    ) -> bool:
        """
        Capture screenshot using headless browser.

        Completely invisible - no window shown.
        """
        browser_path_escaped = self.browser_path.replace("'", "''")
        output_path_escaped = output_path.replace("'", "''")

        ps_script = f'''
        $browserPath = '{browser_path_escaped}'
        $screenshotPath = '{output_path_escaped}'

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

        try:
            result = subprocess.run(
                ["powershell", "-Command", ps_script],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                timeout=60
            )

            return "SUCCESS" in result.stdout and Path(output_path).exists()

        except subprocess.TimeoutExpired:
            return False
        except Exception:
            return False

    async def capture_on_event(
        self,
        target: str,
        event: str,
        selector: Optional[str] = None,
        options: Optional[CaptureOptions] = None
    ) -> CaptureResult:
        """
        Browser adapter doesn't support event-based capture.
        Falls back to simple capture.
        """
        # Browser adapter can't do event-based capture - just capture current state
        return await self.capture(target, options)
