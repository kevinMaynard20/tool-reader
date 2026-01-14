#!/usr/bin/env python3
"""
CLI adapter for tool-reader.
Captures command-line tool output (stdout/stderr).
"""

import os
import subprocess
import time
from pathlib import Path
from typing import Optional, Tuple

from .base import (
    CaptureAdapter,
    CaptureResult,
    CaptureOptions,
    CaptureType,
    AdapterType,
)


class CliAdapter(CaptureAdapter):
    """
    Capture adapter for CLI tools.

    Runs commands and captures stdout/stderr output.
    This is the default adapter for command-line targets.
    """

    adapter_type = AdapterType.CLI
    capture_type = CaptureType.TEXT

    @classmethod
    def can_handle(cls, target: str) -> bool:
        """CLI adapter is the default fallback."""
        return True

    async def capture(self, target: str, options: Optional[CaptureOptions] = None) -> CaptureResult:
        """
        Capture CLI command output.

        Args:
            target: Command to run (e.g., "npm test", "cargo build")
            options: Optional capture options

        Returns:
            CaptureResult with command output
        """
        opts = options or self.options
        output_path = self._get_output_path(".txt")

        # Strip cli: prefix if present
        command = target[4:] if target.startswith("cli:") else target

        try:
            # Wait before capture if specified
            if opts.wait_before > 0:
                time.sleep(opts.wait_before)

            result, output, duration = self._run_command(command, opts.timeout)

            # Save output to file
            output_path.write_text(output, encoding='utf-8')

            capture_result = CaptureResult(
                success=result is not None and result.returncode == 0,
                capture_type=CaptureType.TEXT,
                content_path=str(output_path),
                content_text=output,
                metadata={
                    "command": command,
                    "exit_code": result.returncode if result else None,
                    "duration_seconds": duration,
                    "success": result.returncode == 0 if result else False
                }
            )
            self.captures.append(capture_result)
            return capture_result

        except subprocess.TimeoutExpired:
            return CaptureResult(
                success=False,
                capture_type=CaptureType.TEXT,
                error=f"Command timed out after {opts.timeout} seconds"
            )
        except Exception as e:
            return CaptureResult(
                success=False,
                capture_type=CaptureType.TEXT,
                error=str(e)
            )

    def _run_command(self, command: str, timeout: float = 30) -> Tuple:
        """
        Run command and capture output.

        Returns:
            Tuple of (CompletedProcess, output_text, duration)
        """
        start_time = time.time()

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            duration = time.time() - start_time

            # Format output
            output_parts = []

            if result.stdout:
                output_parts.append("--- STDOUT ---")
                output_parts.append(result.stdout)

            if result.stderr:
                output_parts.append("\n--- STDERR ---")
                output_parts.append(result.stderr)

            output_parts.append(f"\n--- EXIT CODE: {result.returncode} ---")
            output_parts.append(f"--- DURATION: {duration:.2f}s ---")

            output = "\n".join(output_parts)

            return result, output, duration

        except subprocess.TimeoutExpired as e:
            duration = time.time() - start_time
            output_parts = ["--- TIMEOUT ---"]

            if e.stdout:
                stdout = e.stdout.decode('utf-8', errors='replace') if isinstance(e.stdout, bytes) else e.stdout
                output_parts.append("--- PARTIAL STDOUT ---")
                output_parts.append(stdout)

            if e.stderr:
                stderr = e.stderr.decode('utf-8', errors='replace') if isinstance(e.stderr, bytes) else e.stderr
                output_parts.append("--- PARTIAL STDERR ---")
                output_parts.append(stderr)

            output_parts.append(f"\n--- TIMED OUT AFTER: {duration:.2f}s ---")

            return None, "\n".join(output_parts), duration

    async def capture_on_event(
        self,
        target: str,
        event: str,
        selector: Optional[str] = None,
        options: Optional[CaptureOptions] = None
    ) -> CaptureResult:
        """
        Capture CLI output on event.

        For CLI, events are:
        - "complete": Wait for command to complete
        - "output": Capture after specific output appears
        - "timeout": Capture after timeout
        """
        opts = options or self.options

        if event == "complete":
            # Just run and capture
            return await self.capture(target, opts)

        elif event == "output" and selector:
            # Run and check for specific output
            return await self._capture_with_output_check(target, selector, opts)

        elif event == "timeout":
            # Run with short timeout
            timeout = float(selector) if selector else 5.0
            short_opts = CaptureOptions(
                **{**opts.to_dict(), "timeout": timeout}
            )
            return await self.capture(target, short_opts)

        else:
            return await self.capture(target, opts)

    async def _capture_with_output_check(
        self,
        target: str,
        expected_output: str,
        options: CaptureOptions
    ) -> CaptureResult:
        """Run command and verify expected output appears."""
        result = await self.capture(target, options)

        if result.success and result.content_text:
            if expected_output in result.content_text:
                result.metadata["output_check"] = "found"
                result.metadata["expected"] = expected_output
            else:
                result.metadata["output_check"] = "not_found"
                result.metadata["expected"] = expected_output
                result.success = False

        return result

    async def capture_sequence(
        self,
        target: str,
        events: list,
        options: Optional[CaptureOptions] = None
    ) -> list:
        """
        Run multiple commands in sequence.

        For CLI, each event can be a separate command.
        """
        results = []
        opts = options or self.options

        for event_info in events:
            if isinstance(event_info, str):
                # Simple command
                result = await self.capture(event_info, opts)
            elif isinstance(event_info, dict):
                command = event_info.get("command", target)
                event = event_info.get("event", "complete")
                selector = event_info.get("selector")
                result = await self.capture_on_event(command, event, selector, opts)
            else:
                continue

            results.append(result)
            self.captures.append(result)

            # Stop on failure if configured
            if not result.success and event_info.get("stop_on_fail", False):
                break

        return results
