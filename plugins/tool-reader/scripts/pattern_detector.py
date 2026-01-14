#!/usr/bin/env python3
"""
File Pattern Detector for Tool Reader.
Detects when edited files should trigger auto-verification.
"""

import os
import re
from pathlib import Path
from fnmatch import fnmatch
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class UICategory(Enum):
    """Category of UI file."""
    WEBAPP = "webapp"
    STYLES = "styles"
    GUI = "gui"
    TUI = "tui"
    UNKNOWN = "unknown"


# File patterns that indicate UI-related files
UI_PATTERNS: Dict[UICategory, List[str]] = {
    UICategory.WEBAPP: [
        # React
        "**/*.tsx",
        "**/*.jsx",
        # Vue
        "**/*.vue",
        # Svelte
        "**/*.svelte",
        # Astro
        "**/*.astro",
        # Next.js / Nuxt routes
        "**/pages/**/*.tsx",
        "**/pages/**/*.jsx",
        "**/pages/**/*.vue",
        "**/app/**/*.tsx",
        "**/app/**/*.jsx",
        # Components
        "**/components/**/*.tsx",
        "**/components/**/*.jsx",
        "**/components/**/*.vue",
        "**/components/**/*.svelte",
    ],
    UICategory.STYLES: [
        # CSS
        "**/*.css",
        "**/*.scss",
        "**/*.sass",
        "**/*.less",
        # Styled components
        "**/*.styled.ts",
        "**/*.styled.tsx",
        "**/*.styles.ts",
        "**/*.styles.tsx",
        # Tailwind config
        "**/tailwind.config.*",
        # Theme files
        "**/theme/**/*",
        "**/themes/**/*",
    ],
    UICategory.GUI: [
        # WPF / Avalonia (C#)
        "**/*.xaml",
        "**/*.axaml",
        # JavaFX
        "**/*.fxml",
        # Qt
        "**/*.ui",
        "**/*.qml",
        # GTK
        "**/*.glade",
        # WinForms designer
        "**/*.Designer.cs",
        # Electron
        "**/renderer/**/*.ts",
        "**/renderer/**/*.tsx",
    ],
    UICategory.TUI: [
        # CLI directories
        "**/cli/**/*.py",
        "**/cli/**/*.ts",
        "**/cli/**/*.js",
        # TUI directories
        "**/tui/**/*.py",
        "**/tui/**/*.ts",
        "**/tui/**/*.js",
        # Named files
        "**/*_cli.py",
        "**/*_tui.py",
        "**/*_cli.ts",
        "**/*_tui.ts",
        "**/cli.py",
        "**/tui.py",
    ],
}

# File content patterns that indicate TUI usage
TUI_IMPORT_PATTERNS = [
    r"import\s+curses",
    r"from\s+curses\s+import",
    r"import\s+blessed",
    r"from\s+blessed\s+import",
    r"import\s+\{.*\}\s+from\s+['\"]ink['\"]",
    r"require\(['\"]ink['\"]\)",
    r"import\s+rich",
    r"from\s+rich\s+import",
    r"import\s+textual",
    r"from\s+textual\s+import",
    r"import\s+prompt_toolkit",
    r"from\s+prompt_toolkit\s+import",
]


@dataclass
class DetectionResult:
    """Result of file pattern detection."""
    should_verify: bool
    category: UICategory
    matched_pattern: Optional[str] = None
    confidence: float = 1.0
    reason: str = ""


def normalize_path(file_path: str) -> str:
    """Normalize path separators for cross-platform matching."""
    return file_path.replace("\\", "/")


def match_pattern(file_path: str, pattern: str) -> bool:
    """
    Match a file path against a glob pattern.
    Handles ** for recursive matching.
    """
    normalized = normalize_path(file_path)
    pattern = normalize_path(pattern)

    # Handle ** patterns
    if "**" in pattern:
        # Convert to regex for more flexible matching
        regex_pattern = pattern.replace(".", r"\.")
        regex_pattern = regex_pattern.replace("**", ".*")
        regex_pattern = regex_pattern.replace("*", "[^/]*")
        regex_pattern = f"^.*{regex_pattern}$"
        return bool(re.match(regex_pattern, normalized, re.IGNORECASE))
    else:
        return fnmatch(normalized.lower(), pattern.lower())


def check_file_content_for_tui(file_path: str) -> bool:
    """
    Check if file content contains TUI-related imports.
    """
    try:
        content = Path(file_path).read_text(encoding='utf-8', errors='ignore')
        for pattern in TUI_IMPORT_PATTERNS:
            if re.search(pattern, content):
                return True
    except Exception:
        pass
    return False


def should_auto_verify(file_path: str, check_content: bool = True) -> DetectionResult:
    """
    Determine if an edited file should trigger auto-verification.

    Args:
        file_path: Path to the file that was edited
        check_content: Whether to check file content for TUI patterns

    Returns:
        DetectionResult with verification decision and metadata
    """
    normalized = normalize_path(file_path)

    # Check each category's patterns
    for category, patterns in UI_PATTERNS.items():
        for pattern in patterns:
            if match_pattern(normalized, pattern):
                return DetectionResult(
                    should_verify=True,
                    category=category,
                    matched_pattern=pattern,
                    confidence=1.0,
                    reason=f"File matches {category.value} pattern: {pattern}"
                )

    # Check file content for TUI imports (if enabled and file is code)
    if check_content:
        code_extensions = ['.py', '.ts', '.tsx', '.js', '.jsx']
        if any(file_path.endswith(ext) for ext in code_extensions):
            if check_file_content_for_tui(file_path):
                return DetectionResult(
                    should_verify=True,
                    category=UICategory.TUI,
                    matched_pattern="content:tui-import",
                    confidence=0.9,
                    reason="File contains TUI library imports"
                )

    return DetectionResult(
        should_verify=False,
        category=UICategory.UNKNOWN,
        reason="File does not match any UI patterns"
    )


def get_verification_config(project_root: str) -> Optional[Dict]:
    """
    Read verification configuration from project's CLAUDE.md.

    Returns config dict if auto-verify is enabled, None otherwise.
    """
    claude_md_paths = [
        Path(project_root) / "CLAUDE.md",
        Path(project_root) / ".claude" / "CLAUDE.md",
    ]

    for claude_md in claude_md_paths:
        if claude_md.exists():
            try:
                content = claude_md.read_text(encoding='utf-8')

                # Check for tool-reader: auto-verify
                if re.search(r'tool-reader:\s*auto-verify', content, re.IGNORECASE):
                    config = {
                        "enabled": True,
                        "source": str(claude_md),
                    }

                    # Parse optional config
                    url_match = re.search(r'tool-reader-url:\s*(\S+)', content)
                    if url_match:
                        config["url"] = url_match.group(1)

                    port_match = re.search(r'tool-reader-port:\s*(\d+)', content)
                    if port_match:
                        config["port"] = int(port_match.group(1))

                    return config
            except Exception:
                pass

    return None


def detect_running_server(ports: List[int] = None) -> Optional[Tuple[str, int]]:
    """
    Detect if a development server is running on common ports.

    Returns (url, port) if server found, None otherwise.
    """
    import socket

    if ports is None:
        ports = [3000, 3001, 5173, 5174, 8080, 8000, 4200, 4000]

    for port in ports:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.1)
        result = sock.connect_ex(('localhost', port))
        sock.close()

        if result == 0:
            return (f"http://localhost:{port}", port)

    return None


def get_app_type_for_file(file_path: str) -> str:
    """
    Determine the appropriate app type marker for a file.

    Returns: "webapp", "gui", or "tui"
    """
    result = should_auto_verify(file_path)

    if result.category in [UICategory.WEBAPP, UICategory.STYLES]:
        return "webapp"
    elif result.category == UICategory.GUI:
        return "gui"
    elif result.category == UICategory.TUI:
        return "tui"
    else:
        # Default to webapp for unknown
        return "webapp"


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python pattern_detector.py <file_path> [project_root]")
        sys.exit(1)

    file_path = sys.argv[1]
    project_root = sys.argv[2] if len(sys.argv) > 2 else os.getcwd()

    # Check if file should trigger verification
    result = should_auto_verify(file_path)
    print(f"File: {file_path}")
    print(f"Should verify: {result.should_verify}")
    print(f"Category: {result.category.value}")
    print(f"Matched pattern: {result.matched_pattern}")
    print(f"Confidence: {result.confidence}")
    print(f"Reason: {result.reason}")

    # Check project config
    config = get_verification_config(project_root)
    if config:
        print(f"\nAuto-verify enabled: {config}")
    else:
        print("\nAuto-verify not enabled in CLAUDE.md")

    # Check for running server
    server = detect_running_server()
    if server:
        print(f"\nDev server detected: {server[0]}")
    else:
        print("\nNo dev server detected")
