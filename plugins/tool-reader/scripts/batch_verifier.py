#!/usr/bin/env python3
"""
Batch Verifier for tool-reader.
Sends multiple captures to Claude in a single request for efficient verification.
"""

import json
import subprocess
import base64
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class VerificationStatus(Enum):
    """Status of a single verification."""
    PASS = "pass"
    FAIL = "fail"
    UNCERTAIN = "uncertain"
    ERROR = "error"


@dataclass
class ImageVerification:
    """Result of verifying a single image."""
    image_path: str
    status: VerificationStatus
    evidence: str = ""
    task_items_verified: List[str] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)


@dataclass
class BatchResult:
    """Result of batch verification."""
    total: int
    passed: int
    failed: int
    uncertain: int
    issues: List[str] = field(default_factory=list)
    details: List[ImageVerification] = field(default_factory=list)
    summary: str = ""
    raw_response: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "uncertain": self.uncertain,
            "issues": self.issues,
            "details": [
                {
                    "image": d.image_path,
                    "status": d.status.value,
                    "evidence": d.evidence,
                    "verified": d.task_items_verified,
                    "issues": d.issues
                }
                for d in self.details
            ],
            "summary": self.summary
        }


class BatchVerifier:
    """
    Verifies multiple captures against task criteria in a single Claude call.

    Supports:
    - Multiple screenshots in one request
    - Summary mode (default) or detailed per-image analysis
    - Task item verification tracking
    - User flow sequence analysis
    """

    def __init__(
        self,
        task_items: Optional[List[str]] = None,
        acceptance_criteria: Optional[str] = None
    ):
        self.task_items = task_items or []
        self.acceptance_criteria = acceptance_criteria

    def verify_batch(
        self,
        capture_paths: List[str],
        detailed: bool = False,
        task_context: Optional[str] = None
    ) -> BatchResult:
        """
        Verify multiple captures in a single Claude call.

        Args:
            capture_paths: List of paths to capture files (images or text)
            detailed: If True, provide per-image analysis
            task_context: Optional additional context about the task

        Returns:
            BatchResult with verification results
        """
        if not capture_paths:
            return BatchResult(
                total=0,
                passed=0,
                failed=0,
                uncertain=0,
                summary="No captures to verify"
            )

        # Build the prompt
        prompt = self._build_prompt(capture_paths, detailed, task_context)

        # Call Claude
        response = self._call_claude(prompt, capture_paths)

        # Parse response
        return self._parse_response(response, capture_paths, detailed)

    def _build_prompt(
        self,
        capture_paths: List[str],
        detailed: bool,
        task_context: Optional[str]
    ) -> str:
        """Build the verification prompt."""
        task_items_text = "\n".join(f"- {item}" for item in self.task_items) if self.task_items else "No specific items"

        criteria_text = self.acceptance_criteria or "Verify the captures show expected behavior"

        prompt = f"""You are verifying {len(capture_paths)} captures against task criteria.

## Task Items to Verify
{task_items_text}

## Acceptance Criteria
{criteria_text}

{f"## Additional Context{chr(10)}{task_context}" if task_context else ""}

## Captures
You will be shown {len(capture_paths)} captures in sequence. They may represent:
- A user flow (sequential steps)
- Multiple states of the same feature
- Different features to verify

## Instructions
Analyze each capture and determine:
1. Which task items appear to be satisfied
2. Any issues or problems visible
3. Overall verification status

{"For each capture, provide detailed analysis." if detailed else "Provide a summary of all captures."}

## Response Format
Respond with valid JSON in this format:
```json
{{
    "summary": {{
        "total": {len(capture_paths)},
        "passed": <count of captures that pass>,
        "failed": <count of captures that fail>,
        "uncertain": <count where you can't determine>,
        "overall_status": "pass|fail|partial",
        "issues": ["list of issues found across all captures"]
    }},
    {'"details": [' if detailed else ''}
    {'''
        {
            "image_index": 1,
            "status": "pass|fail|uncertain",
            "evidence": "what you observed",
            "task_items_verified": ["items this capture verifies"],
            "issues": ["any issues in this capture"]
        }
    ],''' if detailed else ''}
    "recommendation": "brief recommendation for next steps"
}}
```
"""
        return prompt

    def _call_claude(self, prompt: str, capture_paths: List[str]) -> str:
        """Call Claude CLI with captures."""

        # For images, we need to include them in the prompt
        # Claude CLI can read images via the Read tool internally

        # Build a prompt that references the image files
        image_refs = []
        for i, path in enumerate(capture_paths, 1):
            ext = Path(path).suffix.lower()
            if ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
                image_refs.append(f"Capture {i}: [Image at {path}]")
            elif ext in ['.txt', '.html']:
                # Read text content
                try:
                    content = Path(path).read_text(encoding='utf-8', errors='replace')
                    # Truncate if too long
                    if len(content) > 2000:
                        content = content[:2000] + "\n... [truncated]"
                    image_refs.append(f"Capture {i}:\n```\n{content}\n```")
                except Exception:
                    image_refs.append(f"Capture {i}: [Error reading {path}]")

        full_prompt = f"""{prompt}

## Capture Contents

{chr(10).join(image_refs)}

Please analyze these captures and provide your verification response in JSON format.
"""

        try:
            # Call Claude CLI with Sonnet model for image verification
            # Using Sonnet for all picture verifications as required
            result = subprocess.run(
                ["claude", "-p", full_prompt, "--output-format", "text", "--model", "sonnet"],
                capture_output=True,
                text=True,
                timeout=180,  # 3 minute timeout for batch
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            return result.stdout.strip() if result.stdout else result.stderr

        except subprocess.TimeoutExpired:
            return '{"error": "Claude CLI timed out"}'
        except FileNotFoundError:
            return '{"error": "Claude CLI not found"}'
        except Exception as e:
            return f'{{"error": "{str(e)}"}}'

    def _parse_response(
        self,
        response: str,
        capture_paths: List[str],
        detailed: bool
    ) -> BatchResult:
        """Parse Claude's response into BatchResult."""
        import re

        # Try to extract JSON from response
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try parsing whole response as JSON
            json_str = response

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            # Couldn't parse JSON - return error result
            return BatchResult(
                total=len(capture_paths),
                passed=0,
                failed=0,
                uncertain=len(capture_paths),
                issues=["Failed to parse Claude response"],
                summary="Verification failed - could not parse response",
                raw_response=response
            )

        # Check for error
        if "error" in data:
            return BatchResult(
                total=len(capture_paths),
                passed=0,
                failed=0,
                uncertain=len(capture_paths),
                issues=[data["error"]],
                summary=f"Error: {data['error']}",
                raw_response=response
            )

        # Extract summary
        summary_data = data.get("summary", {})

        # Extract details if present
        details = []
        if detailed and "details" in data:
            for i, detail in enumerate(data["details"]):
                status_str = detail.get("status", "uncertain").lower()
                try:
                    status = VerificationStatus(status_str)
                except ValueError:
                    status = VerificationStatus.UNCERTAIN

                img_path = capture_paths[i] if i < len(capture_paths) else f"image_{i+1}"

                details.append(ImageVerification(
                    image_path=img_path,
                    status=status,
                    evidence=detail.get("evidence", ""),
                    task_items_verified=detail.get("task_items_verified", []),
                    issues=detail.get("issues", [])
                ))

        recommendation = data.get("recommendation", "")
        overall = summary_data.get("overall_status", "uncertain")

        summary_text = f"Overall: {overall}"
        if recommendation:
            summary_text += f"\nRecommendation: {recommendation}"

        return BatchResult(
            total=summary_data.get("total", len(capture_paths)),
            passed=summary_data.get("passed", 0),
            failed=summary_data.get("failed", 0),
            uncertain=summary_data.get("uncertain", 0),
            issues=summary_data.get("issues", []),
            details=details,
            summary=summary_text,
            raw_response=response
        )

    def format_result(self, result: BatchResult, detailed: bool = False) -> str:
        """Format BatchResult as readable text."""
        lines = []

        # Header
        lines.append("=" * 60)
        lines.append(f"BATCH VERIFICATION: {result.total} captures")
        lines.append("=" * 60)

        # Summary stats
        lines.append("")
        if result.passed > 0:
            lines.append(f"  PASSED:    {result.passed}/{result.total}")
        if result.failed > 0:
            lines.append(f"  FAILED:    {result.failed}/{result.total}")
        if result.uncertain > 0:
            lines.append(f"  UNCERTAIN: {result.uncertain}/{result.total}")

        # Issues
        if result.issues:
            lines.append("")
            lines.append("Issues Found:")
            for issue in result.issues:
                lines.append(f"  - {issue}")

        # Detailed results
        if detailed and result.details:
            lines.append("")
            lines.append("-" * 60)
            lines.append("DETAILED RESULTS")
            lines.append("-" * 60)

            for i, detail in enumerate(result.details, 1):
                lines.append("")
                lines.append(f"### Capture {i}: {Path(detail.image_path).name}")
                lines.append(f"Status: {detail.status.value.upper()}")

                if detail.evidence:
                    lines.append(f"Evidence: {detail.evidence}")

                if detail.task_items_verified:
                    lines.append("Verified:")
                    for item in detail.task_items_verified:
                        lines.append(f"  [x] {item}")

                if detail.issues:
                    lines.append("Issues:")
                    for issue in detail.issues:
                        lines.append(f"  - {issue}")

        # Summary
        lines.append("")
        lines.append("-" * 60)
        lines.append(result.summary)
        lines.append("=" * 60)

        return "\n".join(lines)


def verify_captures(
    capture_paths: List[str],
    task_items: Optional[List[str]] = None,
    detailed: bool = False,
    task_context: Optional[str] = None
) -> BatchResult:
    """
    Convenience function to verify captures.

    Args:
        capture_paths: Paths to capture files
        task_items: Optional list of task items to verify
        detailed: Whether to include per-image details
        task_context: Optional additional context

    Returns:
        BatchResult
    """
    verifier = BatchVerifier(task_items=task_items)
    return verifier.verify_batch(capture_paths, detailed, task_context)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Batch verify captures")
    parser.add_argument("captures", nargs="+", help="Paths to capture files")
    parser.add_argument("--task", nargs="+", help="Task items to verify")
    parser.add_argument("--detailed", action="store_true", help="Include per-image details")
    parser.add_argument("--context", help="Additional task context")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    verifier = BatchVerifier(task_items=args.task)
    result = verifier.verify_batch(args.captures, args.detailed, args.context)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(verifier.format_result(result, args.detailed))
