#!/usr/bin/env python3
"""
Auto-Fixer for Tool Reader.
Detects visual issues and attempts automatic code fixes.
"""

import json
import os
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

from visual_verifier import (
    run_visual_verification,
    VerificationResult,
    AppType,
)
from pattern_detector import (
    should_auto_verify,
    get_verification_config,
    detect_running_server,
    UICategory,
)


@dataclass
class FixAttempt:
    """Record of a fix attempt."""
    issue: str
    file_path: str
    line_number: Optional[int]
    original_code: str
    fixed_code: str
    success: bool
    verification_after: Optional[VerificationResult] = None


@dataclass
class AutoFixResult:
    """Result of auto-fix workflow."""
    issues_found: List[str]
    fixes_attempted: List[FixAttempt]
    all_fixed: bool
    final_verification: Optional[VerificationResult]
    screenshots: List[str]


MAX_FIX_ATTEMPTS = 3


class AutoFixer:
    """Handles automatic fixing of visual issues."""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.fix_attempts: List[FixAttempt] = []
        self.screenshots: List[str] = []

    def analyze_issue(
        self,
        screenshot_path: str,
        issue_description: str,
        edited_files: List[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Use Claude to analyze a visual issue and propose a fix.

        Args:
            screenshot_path: Path to screenshot showing the issue
            issue_description: Description of what's wrong
            edited_files: List of recently edited files (likely sources)

        Returns:
            Dict with fix proposal or None if can't determine fix
        """
        # Read the content of edited files
        file_contents = {}
        for file_path in edited_files[:5]:  # Limit to 5 files
            try:
                full_path = self.project_root / file_path
                if full_path.exists():
                    content = full_path.read_text(encoding='utf-8', errors='ignore')
                    # Limit content size
                    if len(content) > 10000:
                        content = content[:10000] + "\n... (truncated)"
                    file_contents[file_path] = content
            except Exception:
                pass

        files_section = ""
        for path, content in file_contents.items():
            files_section += f"\n### {path}\n```\n{content}\n```\n"

        prompt = f"""You are debugging a visual issue in a UI application.

## Issue Description
{issue_description}

## Screenshot
The screenshot showing the issue is at: {screenshot_path}
Please use the Read tool to view it.

## Recently Edited Files
These files were recently edited and may contain the bug:
{files_section}

## Task
1. Analyze the screenshot to understand the visual issue
2. Identify which file and line contains the bug
3. Propose a specific code fix

Respond in this JSON format:
```json
{{
  "issue_identified": "specific description of what's wrong",
  "root_cause": "why this is happening",
  "file_to_fix": "path/to/file.tsx",
  "line_number": 42,
  "original_code": "the exact code that needs changing",
  "fixed_code": "the corrected code",
  "confidence": 0.0-1.0,
  "explanation": "why this fix should work"
}}
```

If you cannot determine a fix, respond with:
```json
{{
  "issue_identified": "description",
  "root_cause": "unknown or complex",
  "file_to_fix": null,
  "confidence": 0.0,
  "explanation": "why a fix cannot be automatically determined"
}}
```
"""

        try:
            # Use Sonnet model for image analysis (analyzing screenshots for issues)
            result = subprocess.run(
                ["claude", "-p", prompt, "--output-format", "text", "--model", "sonnet"],
                capture_output=True,
                text=True,
                timeout=120,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
            )

            response = result.stdout.strip()

            # Parse JSON
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            else:
                try:
                    return json.loads(response)
                except json.JSONDecodeError:
                    return None

        except Exception as e:
            print(f"Error analyzing issue: {e}")
            return None

    def apply_fix(
        self,
        file_path: str,
        original_code: str,
        fixed_code: str
    ) -> bool:
        """
        Apply a code fix to a file.

        Args:
            file_path: Path to the file to fix
            original_code: The original code to replace
            fixed_code: The fixed code

        Returns:
            True if fix was applied successfully
        """
        try:
            full_path = self.project_root / file_path
            if not full_path.exists():
                print(f"File not found: {full_path}")
                return False

            content = full_path.read_text(encoding='utf-8')

            if original_code not in content:
                # Try with normalized whitespace
                normalized_original = ' '.join(original_code.split())
                normalized_content = ' '.join(content.split())
                if normalized_original not in normalized_content:
                    print(f"Original code not found in {file_path}")
                    return False
                # Can't do simple replace with normalized, would need smarter approach
                print(f"Code found but whitespace differs, skipping auto-fix")
                return False

            new_content = content.replace(original_code, fixed_code, 1)
            full_path.write_text(new_content, encoding='utf-8')

            return True

        except Exception as e:
            print(f"Error applying fix: {e}")
            return False

    def run_auto_fix_workflow(
        self,
        task_file_path: str,
        edited_files: List[str],
        app_url: Optional[str] = None,
    ) -> AutoFixResult:
        """
        Run the full auto-fix workflow.

        1. Verify current state
        2. If issues found, analyze and propose fixes
        3. Apply fixes
        4. Re-verify
        5. Repeat until fixed or max attempts reached

        Args:
            task_file_path: Path to task definition file
            edited_files: List of recently edited files
            app_url: Optional URL override for webapp

        Returns:
            AutoFixResult with all fix attempts and final state
        """
        issues_found = []
        fixes_attempted = []
        attempt_count = 0

        # Initial verification
        verification = run_visual_verification(
            task_file_path,
            task_items=["Verify UI renders correctly"],
            acceptance_criteria="No visual issues or regressions"
        )

        if verification.screenshot_path:
            self.screenshots.append(verification.screenshot_path)

        if verification.success:
            return AutoFixResult(
                issues_found=[],
                fixes_attempted=[],
                all_fixed=True,
                final_verification=verification,
                screenshots=self.screenshots
            )

        # Extract issues from verification
        issues_found = verification.failed_items.copy()
        if not issues_found and not verification.success:
            issues_found = ["Visual verification failed - see screenshot"]

        # Attempt fixes
        while attempt_count < MAX_FIX_ATTEMPTS and not verification.success:
            attempt_count += 1
            print(f"\n=== Fix Attempt {attempt_count}/{MAX_FIX_ATTEMPTS} ===")

            # Analyze the issue
            issue_desc = verification.claude_response or "; ".join(issues_found)
            analysis = self.analyze_issue(
                verification.screenshot_path or "",
                issue_desc,
                edited_files
            )

            if not analysis or not analysis.get("file_to_fix"):
                print("Could not determine fix, stopping auto-fix")
                break

            if analysis.get("confidence", 0) < 0.5:
                print(f"Low confidence fix ({analysis.get('confidence')}), stopping auto-fix")
                break

            # Record the fix attempt
            fix_attempt = FixAttempt(
                issue=analysis.get("issue_identified", "Unknown"),
                file_path=analysis.get("file_to_fix", ""),
                line_number=analysis.get("line_number"),
                original_code=analysis.get("original_code", ""),
                fixed_code=analysis.get("fixed_code", ""),
                success=False
            )

            # Apply the fix
            if fix_attempt.original_code and fix_attempt.fixed_code:
                applied = self.apply_fix(
                    fix_attempt.file_path,
                    fix_attempt.original_code,
                    fix_attempt.fixed_code
                )

                if applied:
                    print(f"Applied fix to {fix_attempt.file_path}")

                    # Wait for hot reload if applicable
                    time.sleep(2)

                    # Re-verify
                    verification = run_visual_verification(
                        task_file_path,
                        task_items=["Verify UI renders correctly"],
                        acceptance_criteria="No visual issues or regressions"
                    )

                    if verification.screenshot_path:
                        self.screenshots.append(verification.screenshot_path)

                    fix_attempt.success = verification.success
                    fix_attempt.verification_after = verification

                    if verification.success:
                        print("Fix verified successfully!")
                else:
                    print("Failed to apply fix")

            fixes_attempted.append(fix_attempt)

        return AutoFixResult(
            issues_found=issues_found,
            fixes_attempted=fixes_attempted,
            all_fixed=verification.success if verification else False,
            final_verification=verification,
            screenshots=self.screenshots
        )


def format_auto_fix_result(result: AutoFixResult) -> str:
    """Format auto-fix result for display."""
    lines = ["## Auto-Fix Result\n"]

    status = "ALL FIXED" if result.all_fixed else "ISSUES REMAIN"
    lines.append(f"**Status**: {status}")

    if result.issues_found:
        lines.append("\n### Issues Found")
        for issue in result.issues_found:
            lines.append(f"- {issue}")

    if result.fixes_attempted:
        lines.append("\n### Fix Attempts")
        for i, fix in enumerate(result.fixes_attempted, 1):
            status_icon = "" if fix.success else ""
            lines.append(f"\n#### Attempt {i} {status_icon}")
            lines.append(f"**Issue**: {fix.issue}")
            lines.append(f"**File**: {fix.file_path}:{fix.line_number or '?'}")
            if fix.original_code and fix.fixed_code:
                lines.append("**Change**:")
                lines.append("```diff")
                for line in fix.original_code.split('\n'):
                    lines.append(f"- {line}")
                for line in fix.fixed_code.split('\n'):
                    lines.append(f"+ {line}")
                lines.append("```")

    if result.screenshots:
        lines.append("\n### Screenshots")
        for ss in result.screenshots:
            lines.append(f"- {ss}")

    return "\n".join(lines)


def run_proactive_verification(
    edited_file: str,
    project_root: str,
    task_file: Optional[str] = None,
) -> Optional[AutoFixResult]:
    """
    Run proactive verification after a file edit.

    This is the main entry point for auto-verification triggered by file edits.

    Args:
        edited_file: Path to the file that was just edited
        project_root: Root of the project
        task_file: Optional task file path (auto-detected if not provided)

    Returns:
        AutoFixResult if verification was run, None if skipped
    """
    from pattern_detector import should_auto_verify, get_verification_config

    # Check if this file should trigger verification
    detection = should_auto_verify(edited_file)
    if not detection.should_verify:
        print(f"Skipping verification - {detection.reason}")
        return None

    # Check if project has auto-verify enabled
    config = get_verification_config(project_root)
    if not config or not config.get("enabled"):
        print("Auto-verify not enabled in CLAUDE.md")
        return None

    print(f"Auto-verifying after edit to {edited_file}")
    print(f"Detected category: {detection.category.value}")

    # Find or create task file
    if not task_file:
        claude_dir = Path(project_root) / ".claude"
        task_file = str(claude_dir / "auto-verify-task.md")

        # Create a minimal task file if needed
        if not Path(task_file).exists():
            claude_dir.mkdir(parents=True, exist_ok=True)

            # Detect app type and URL
            server = detect_running_server()
            if server:
                app_marker = f"[webapp]: {server[0]}"
            elif detection.category == UICategory.TUI:
                app_marker = "[tui]: echo 'No TUI command configured'"
            else:
                app_marker = "[webapp]: http://localhost:3000"

            task_content = f"""# Auto-Verification Task

## Application
{app_marker}

## Checklist
- [ ] UI renders correctly after changes
- [ ] No visual regressions
"""
            Path(task_file).write_text(task_content, encoding='utf-8')

    # Run auto-fix workflow
    fixer = AutoFixer(project_root)
    result = fixer.run_auto_fix_workflow(
        task_file,
        edited_files=[edited_file],
    )

    return result


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python auto_fixer.py <edited_file> <project_root> [task_file]")
        sys.exit(1)

    edited_file = sys.argv[1]
    project_root = sys.argv[2]
    task_file = sys.argv[3] if len(sys.argv) > 3 else None

    result = run_proactive_verification(edited_file, project_root, task_file)

    if result:
        print(format_auto_fix_result(result))
    else:
        print("Verification skipped")
