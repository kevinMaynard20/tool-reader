#!/usr/bin/env python3
"""
TUI adapter for tool-reader.
Captures terminal application output with ANSI codes preserved.
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


class TuiAdapter(CaptureAdapter):
    """
    Capture adapter for terminal UI applications.

    Captures stdout/stderr from TUI apps, preserving ANSI codes
    for color and formatting analysis.
    """

    adapter_type = AdapterType.TUI
    capture_type = CaptureType.ANSI

    def __init__(self, options: Optional[CaptureOptions] = None):
        super().__init__(options)
        self._process = None

    @classmethod
    def can_handle(cls, target: str) -> bool:
        """Check if this adapter can handle the target."""
        target_lower = target.lower()
        return (
            target.startswith("tui:") or
            "ratatui" in target_lower or
            "crossterm" in target_lower or
            "tui" in target_lower
        )

    async def capture(self, target: str, options: Optional[CaptureOptions] = None) -> CaptureResult:
        """
        Capture TUI application output.

        Args:
            target: Command to run (e.g., "cargo run", "tui:cargo run")
            options: Optional capture options

        Returns:
            CaptureResult with terminal output
        """
        opts = options or self.options

        # Strip tui: prefix if present
        command = target[4:] if target.startswith("tui:") else target

        output_path = self._get_output_path(".txt")

        try:
            # Wait before capture if specified
            if opts.wait_before > 0:
                time.sleep(opts.wait_before)

            result, output_text = self._run_command(command, opts.timeout)

            if output_text:
                # Save output to file
                output_path.write_text(output_text, encoding='utf-8')

                capture_result = CaptureResult(
                    success=True,
                    capture_type=CaptureType.ANSI,
                    content_path=str(output_path),
                    content_text=output_text,
                    metadata={
                        "command": command,
                        "exit_code": result.returncode if result else None,
                        "has_ansi": self._has_ansi_codes(output_text)
                    }
                )
                self.captures.append(capture_result)
                return capture_result
            else:
                return CaptureResult(
                    success=False,
                    capture_type=CaptureType.ANSI,
                    error="No output captured from command"
                )

        except subprocess.TimeoutExpired:
            return CaptureResult(
                success=False,
                capture_type=CaptureType.ANSI,
                error=f"Command timed out after {opts.timeout} seconds"
            )
        except Exception as e:
            return CaptureResult(
                success=False,
                capture_type=CaptureType.ANSI,
                error=str(e)
            )

    def _run_command(self, command: str, timeout: float = 30) -> tuple:
        """
        Run command and capture output.

        Returns:
            Tuple of (CompletedProcess or None, output_text)
        """
        try:
            # Run command with captured output
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            # Combine stdout and stderr
            output = result.stdout
            if result.stderr:
                output += "\n\n--- STDERR ---\n" + result.stderr

            return result, output

        except subprocess.TimeoutExpired as e:
            # Try to capture partial output
            output = ""
            if e.stdout:
                output = e.stdout.decode('utf-8', errors='replace') if isinstance(e.stdout, bytes) else e.stdout
            if e.stderr:
                stderr = e.stderr.decode('utf-8', errors='replace') if isinstance(e.stderr, bytes) else e.stderr
                output += "\n\n--- STDERR ---\n" + stderr
            return None, output

    def _has_ansi_codes(self, text: str) -> bool:
        """Check if text contains ANSI escape codes."""
        return '\x1b[' in text or '\033[' in text

    async def capture_on_event(
        self,
        target: str,
        event: str,
        selector: Optional[str] = None,
        options: Optional[CaptureOptions] = None
    ) -> CaptureResult:
        """
        Capture TUI output on event.

        For TUI apps, events typically mean:
        - "input": Send input to stdin then capture
        - "wait": Wait specified time then capture
        - "key": Send keypress then capture
        """
        opts = options or self.options

        # For TUI, selector is used as input/key to send
        if event == "input" and selector:
            return await self._capture_with_input(target, selector, opts)
        elif event == "key" and selector:
            return await self._capture_with_key(target, selector, opts)
        elif event == "wait":
            # Wait extra time then capture
            wait_time = float(selector) if selector else 2.0
            time.sleep(wait_time)
            return await self.capture(target, opts)
        else:
            return await self.capture(target, opts)

    async def _capture_with_input(
        self,
        target: str,
        input_text: str,
        options: CaptureOptions
    ) -> CaptureResult:
        """Run command with stdin input and capture output."""
        command = target[4:] if target.startswith("tui:") else target
        output_path = self._get_output_path(".txt")

        try:
            result = subprocess.run(
                command,
                shell=True,
                input=input_text,
                capture_output=True,
                text=True,
                timeout=options.timeout,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            output = result.stdout
            if result.stderr:
                output += "\n\n--- STDERR ---\n" + result.stderr

            output_path.write_text(output, encoding='utf-8')

            capture_result = CaptureResult(
                success=True,
                capture_type=CaptureType.ANSI,
                content_path=str(output_path),
                content_text=output,
                event=f"input:{input_text[:20]}...",
                metadata={
                    "command": command,
                    "input": input_text,
                    "exit_code": result.returncode
                }
            )
            self.captures.append(capture_result)
            return capture_result

        except Exception as e:
            return CaptureResult(
                success=False,
                capture_type=CaptureType.ANSI,
                error=str(e)
            )

    async def _capture_with_key(
        self,
        target: str,
        key: str,
        options: CaptureOptions
    ) -> CaptureResult:
        """
        Send keypress to running TUI and capture.

        This is a simplified version - full PTY support would be better.
        """
        # For now, treat key as input
        key_map = {
            "enter": "\n",
            "tab": "\t",
            "escape": "\x1b",
            "up": "\x1b[A",
            "down": "\x1b[B",
            "left": "\x1b[D",
            "right": "\x1b[C",
        }
        input_char = key_map.get(key.lower(), key)
        return await self._capture_with_input(target, input_char, options)
