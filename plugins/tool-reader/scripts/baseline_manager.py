#!/usr/bin/env python3
"""
Baseline Manager for Tool Reader.
Handles storing, loading, and comparing baseline screenshots for regression testing.
"""

import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from visual_verifier import (
    capture_screenshot_webapp,
    capture_screenshot_window,
    launch_tui_invisible,
    capture_tui_output,
    detect_app_type,
    AppType,
)


@dataclass
class BaselineEntry:
    """A single baseline screenshot entry."""
    name: str
    file: str
    created: str
    app_type: str
    url: Optional[str] = None
    command: Optional[str] = None
    description: Optional[str] = None
    width: int = 1280
    height: int = 720


@dataclass
class ComparisonResult:
    """Result of comparing current state to baseline."""
    matches: bool
    baseline_path: str
    current_path: str
    differences: List[str]
    similarity_score: float
    claude_analysis: str
    suggested_fixes: List[str]


class BaselineManager:
    """Manages baseline screenshots for a project."""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.baselines_dir = self.project_root / ".claude" / "baselines"
        self.manifest_path = self.baselines_dir / "manifest.json"
        self._ensure_dirs()

    def _ensure_dirs(self):
        """Ensure baseline directories exist."""
        self.baselines_dir.mkdir(parents=True, exist_ok=True)

    def _load_manifest(self) -> Dict[str, Any]:
        """Load the baselines manifest."""
        if self.manifest_path.exists():
            try:
                return json.loads(self.manifest_path.read_text(encoding='utf-8'))
            except json.JSONDecodeError:
                pass
        return {"baselines": [], "version": "1.0"}

    def _save_manifest(self, manifest: Dict[str, Any]):
        """Save the baselines manifest."""
        self.manifest_path.write_text(
            json.dumps(manifest, indent=2),
            encoding='utf-8'
        )

    def list_baselines(self) -> List[BaselineEntry]:
        """List all saved baselines."""
        manifest = self._load_manifest()
        return [BaselineEntry(**entry) for entry in manifest.get("baselines", [])]

    def get_baseline(self, name: str) -> Optional[BaselineEntry]:
        """Get a specific baseline by name."""
        for baseline in self.list_baselines():
            if baseline.name == name:
                return baseline
        return None

    def save_baseline(
        self,
        name: str,
        app_type: str,
        url: Optional[str] = None,
        command: Optional[str] = None,
        description: Optional[str] = None,
        width: int = 1280,
        height: int = 720,
    ) -> BaselineEntry:
        """
        Save a new baseline screenshot.

        Args:
            name: Name for this baseline (e.g., "login-page", "dashboard")
            app_type: Type of app ("webapp", "gui", "tui")
            url: URL for webapp
            command: Command for gui/tui
            description: Optional description
            width: Screenshot width
            height: Screenshot height

        Returns:
            The saved BaselineEntry
        """
        timestamp = int(time.time())

        if app_type == "tui":
            file_ext = ".txt"
        else:
            file_ext = ".png"

        filename = f"{name}_{timestamp}{file_ext}"
        screenshot_path = str(self.baselines_dir / filename)

        # Capture the screenshot based on app type
        if app_type == "webapp":
            if not url:
                raise ValueError("URL required for webapp baseline")
            success = capture_screenshot_webapp(url, screenshot_path, width, height)
            if not success:
                raise RuntimeError(f"Failed to capture webapp screenshot for {url}")

        elif app_type == "gui":
            if not command:
                raise ValueError("Command required for GUI baseline")
            # For GUI, we need window_title from the command or a separate param
            # This is a simplified version - in practice you'd parse window_title
            raise NotImplementedError("GUI baseline capture requires window_title specification")

        elif app_type == "tui":
            if not command:
                raise ValueError("Command required for TUI baseline")
            result, output_file = launch_tui_invisible(command)
            tui_output = capture_tui_output(output_file)
            if tui_output:
                Path(screenshot_path).write_text(tui_output, encoding='utf-8')
            else:
                raise RuntimeError("Failed to capture TUI output")

        else:
            raise ValueError(f"Unknown app_type: {app_type}")

        # Create entry
        entry = BaselineEntry(
            name=name,
            file=filename,
            created=datetime.utcnow().isoformat() + "Z",
            app_type=app_type,
            url=url,
            command=command,
            description=description,
            width=width,
            height=height,
        )

        # Update manifest
        manifest = self._load_manifest()

        # Remove existing baseline with same name (replace)
        manifest["baselines"] = [
            b for b in manifest["baselines"] if b["name"] != name
        ]
        manifest["baselines"].append(asdict(entry))

        self._save_manifest(manifest)

        return entry

    def delete_baseline(self, name: str) -> bool:
        """Delete a baseline by name."""
        baseline = self.get_baseline(name)
        if not baseline:
            return False

        # Delete file
        file_path = self.baselines_dir / baseline.file
        if file_path.exists():
            file_path.unlink()

        # Update manifest
        manifest = self._load_manifest()
        manifest["baselines"] = [
            b for b in manifest["baselines"] if b["name"] != name
        ]
        self._save_manifest(manifest)

        return True

    def compare_to_baseline(
        self,
        name: str,
        current_screenshot_path: Optional[str] = None,
    ) -> ComparisonResult:
        """
        Compare current state to a saved baseline.

        Args:
            name: Name of the baseline to compare against
            current_screenshot_path: Path to current screenshot (captures new if None)

        Returns:
            ComparisonResult with differences and suggested fixes
        """
        baseline = self.get_baseline(name)
        if not baseline:
            raise ValueError(f"Baseline '{name}' not found")

        baseline_path = str(self.baselines_dir / baseline.file)

        # Capture current state if not provided
        if current_screenshot_path is None:
            timestamp = int(time.time())
            if baseline.app_type == "tui":
                current_screenshot_path = str(
                    self.baselines_dir / f"current_{name}_{timestamp}.txt"
                )
            else:
                current_screenshot_path = str(
                    self.baselines_dir / f"current_{name}_{timestamp}.png"
                )

            if baseline.app_type == "webapp" and baseline.url:
                capture_screenshot_webapp(
                    baseline.url,
                    current_screenshot_path,
                    baseline.width,
                    baseline.height
                )
            elif baseline.app_type == "tui" and baseline.command:
                result, output_file = launch_tui_invisible(baseline.command)
                tui_output = capture_tui_output(output_file)
                if tui_output:
                    Path(current_screenshot_path).write_text(tui_output, encoding='utf-8')

        # Use Claude to compare
        comparison_result = self._compare_with_claude(
            baseline_path,
            current_screenshot_path,
            baseline.app_type
        )

        return comparison_result

    def _compare_with_claude(
        self,
        baseline_path: str,
        current_path: str,
        app_type: str
    ) -> ComparisonResult:
        """Use Claude CLI to compare baseline and current screenshots."""

        if app_type == "tui":
            # For TUI, read both text files
            baseline_content = Path(baseline_path).read_text(encoding='utf-8', errors='replace')
            current_content = Path(current_path).read_text(encoding='utf-8', errors='replace')

            prompt = f"""Compare these two terminal outputs and identify any differences.

## Baseline Output (Expected)
```
{baseline_content}
```

## Current Output
```
{current_content}
```

Analyze the differences and respond in this JSON format:
```json
{{
  "matches": true/false,
  "similarity_score": 0.0-1.0,
  "differences": ["list of differences found"],
  "analysis": "detailed analysis of what changed",
  "suggested_fixes": ["list of code fixes if regressions found"]
}}
```
"""
        else:
            # For visual screenshots, ask Claude to compare
            prompt = f"""I need you to compare two screenshots to detect visual regressions.

Baseline screenshot (expected state): {baseline_path}
Current screenshot: {current_path}

Please use the Read tool to view both images, then analyze:
1. Are there any visual differences?
2. Do the layouts match?
3. Are all expected elements present?
4. Are colors, fonts, and spacing consistent?

Respond in this JSON format:
```json
{{
  "matches": true/false,
  "similarity_score": 0.0-1.0,
  "differences": ["list of visual differences found"],
  "analysis": "detailed analysis of what changed",
  "suggested_fixes": ["list of code fixes if regressions found"]
}}
```
"""

        try:
            # Use Sonnet model for image analysis (comparing screenshots)
            result = subprocess.run(
                ["claude", "-p", prompt, "--output-format", "text", "--model", "sonnet"],
                capture_output=True,
                text=True,
                timeout=120,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
            )

            response_text = result.stdout.strip()

            # Parse JSON from response
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
            else:
                try:
                    data = json.loads(response_text)
                except json.JSONDecodeError:
                    data = {
                        "matches": False,
                        "similarity_score": 0.0,
                        "differences": ["Could not parse comparison result"],
                        "analysis": response_text,
                        "suggested_fixes": []
                    }

            return ComparisonResult(
                matches=data.get("matches", False),
                baseline_path=baseline_path,
                current_path=current_path,
                differences=data.get("differences", []),
                similarity_score=data.get("similarity_score", 0.0),
                claude_analysis=data.get("analysis", ""),
                suggested_fixes=data.get("suggested_fixes", [])
            )

        except Exception as e:
            return ComparisonResult(
                matches=False,
                baseline_path=baseline_path,
                current_path=current_path,
                differences=[f"Comparison error: {str(e)}"],
                similarity_score=0.0,
                claude_analysis=f"Error during comparison: {str(e)}",
                suggested_fixes=[]
            )


def format_baseline_list(baselines: List[BaselineEntry]) -> str:
    """Format baselines list for display."""
    if not baselines:
        return "No baselines saved."

    lines = ["## Saved Baselines\n"]
    lines.append("| Name | Type | Created | Description |")
    lines.append("|------|------|---------|-------------|")

    for b in baselines:
        created = b.created[:10] if b.created else "Unknown"
        desc = b.description or "-"
        lines.append(f"| {b.name} | {b.app_type} | {created} | {desc} |")

    return "\n".join(lines)


def format_comparison_result(result: ComparisonResult) -> str:
    """Format comparison result for display."""
    lines = ["## Comparison Result\n"]

    status = "MATCH" if result.matches else "MISMATCH"
    lines.append(f"**Status**: {status}")
    lines.append(f"**Similarity**: {result.similarity_score:.1%}")
    lines.append(f"**Baseline**: {result.baseline_path}")
    lines.append(f"**Current**: {result.current_path}")

    if result.differences:
        lines.append("\n### Differences Found")
        for diff in result.differences:
            lines.append(f"- {diff}")

    if result.suggested_fixes:
        lines.append("\n### Suggested Fixes")
        for fix in result.suggested_fixes:
            lines.append(f"- {fix}")

    if result.claude_analysis:
        lines.append(f"\n### Analysis\n{result.claude_analysis}")

    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python baseline_manager.py <command> [args]")
        print("Commands:")
        print("  list <project_root>")
        print("  save <project_root> <name> <app_type> [url_or_command]")
        print("  compare <project_root> <name>")
        print("  delete <project_root> <name>")
        sys.exit(1)

    command = sys.argv[1]
    project_root = sys.argv[2] if len(sys.argv) > 2 else os.getcwd()

    manager = BaselineManager(project_root)

    if command == "list":
        baselines = manager.list_baselines()
        print(format_baseline_list(baselines))

    elif command == "save":
        if len(sys.argv) < 5:
            print("Usage: save <project_root> <name> <app_type> [url_or_command]")
            sys.exit(1)
        name = sys.argv[3]
        app_type = sys.argv[4]
        url_or_cmd = sys.argv[5] if len(sys.argv) > 5 else None

        kwargs = {"name": name, "app_type": app_type}
        if app_type == "webapp":
            kwargs["url"] = url_or_cmd
        else:
            kwargs["command"] = url_or_cmd

        entry = manager.save_baseline(**kwargs)
        print(f"Baseline saved: {entry.file}")

    elif command == "compare":
        if len(sys.argv) < 4:
            print("Usage: compare <project_root> <name>")
            sys.exit(1)
        name = sys.argv[3]
        result = manager.compare_to_baseline(name)
        print(format_comparison_result(result))

    elif command == "delete":
        if len(sys.argv) < 4:
            print("Usage: delete <project_root> <name>")
            sys.exit(1)
        name = sys.argv[3]
        if manager.delete_baseline(name):
            print(f"Baseline '{name}' deleted.")
        else:
            print(f"Baseline '{name}' not found.")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
