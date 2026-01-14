#!/usr/bin/env python3
"""
Base adapter class for tool-reader capture system.
All capture adapters implement this interface for target-agnostic verification.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Union
from pathlib import Path
from enum import Enum
import time


class CaptureType(Enum):
    """Type of capture produced by adapter."""
    SCREENSHOT = "screenshot"      # Image file (PNG, JPG)
    TEXT = "text"                  # Plain text output
    ANSI = "ansi"                  # Terminal output with ANSI codes
    DOM = "dom"                    # HTML/DOM snapshot
    MIXED = "mixed"                # Multiple types


class AdapterType(Enum):
    """Available adapter types."""
    PLAYWRIGHT = "playwright"
    BROWSER = "browser"
    TUI = "tui"
    GUI = "gui"
    CLI = "cli"
    CUSTOM = "custom"
    AUTO = "auto"


@dataclass
class CaptureResult:
    """Result of a capture operation."""
    success: bool
    capture_type: CaptureType
    content_path: Optional[str] = None      # Path to captured file
    content_text: Optional[str] = None      # Text content (for CLI/TUI)
    timestamp: float = field(default_factory=time.time)
    event: Optional[str] = None             # Event that triggered capture
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "capture_type": self.capture_type.value,
            "content_path": self.content_path,
            "content_text": self.content_text,
            "timestamp": self.timestamp,
            "event": self.event,
            "metadata": self.metadata,
            "error": self.error
        }


@dataclass
class CaptureOptions:
    """Options for capture operations."""
    # Output settings
    output_dir: Optional[Path] = None
    output_name: Optional[str] = None

    # Viewport/size
    width: int = 1280
    height: int = 720

    # Timing
    wait_before: float = 0.5        # Wait before capture
    wait_after: float = 0.0         # Wait after capture
    timeout: float = 30.0           # Max wait time

    # Capture settings
    full_page: bool = False         # Full page screenshot (web)
    include_cursor: bool = False    # Include cursor in capture

    # Event settings
    events: List[str] = field(default_factory=list)  # Events to capture on
    selector: Optional[str] = None  # CSS selector for event target

    def to_dict(self) -> Dict[str, Any]:
        return {
            "output_dir": str(self.output_dir) if self.output_dir else None,
            "output_name": self.output_name,
            "width": self.width,
            "height": self.height,
            "wait_before": self.wait_before,
            "wait_after": self.wait_after,
            "timeout": self.timeout,
            "full_page": self.full_page,
            "include_cursor": self.include_cursor,
            "events": self.events,
            "selector": self.selector
        }


class CaptureAdapter(ABC):
    """
    Base class for all capture adapters.

    Each adapter handles a specific type of target (web, TUI, GUI, CLI)
    and provides a consistent interface for capturing state.
    """

    adapter_type: AdapterType = AdapterType.AUTO
    capture_type: CaptureType = CaptureType.SCREENSHOT

    def __init__(self, options: Optional[CaptureOptions] = None):
        self.options = options or CaptureOptions()
        self.captures: List[CaptureResult] = []
        self._session_active = False

    @abstractmethod
    async def capture(self, target: str, options: Optional[CaptureOptions] = None) -> CaptureResult:
        """
        Capture current state of target.

        Args:
            target: Target identifier (URL, command, window name)
            options: Optional capture options override

        Returns:
            CaptureResult with captured content
        """
        pass

    async def capture_on_event(
        self,
        target: str,
        event: str,
        selector: Optional[str] = None,
        options: Optional[CaptureOptions] = None
    ) -> CaptureResult:
        """
        Capture when specific event occurs.

        Override in subclasses that support event-based capture.

        Args:
            target: Target identifier
            event: Event type (click, navigate, input, etc.)
            selector: Optional CSS selector for event target
            options: Optional capture options

        Returns:
            CaptureResult with captured content
        """
        # Default: just capture immediately
        return await self.capture(target, options)

    async def capture_sequence(
        self,
        target: str,
        events: List[Dict[str, Any]],
        options: Optional[CaptureOptions] = None
    ) -> List[CaptureResult]:
        """
        Capture a sequence of events.

        Args:
            target: Target identifier
            events: List of event dicts with 'event' and optional 'selector'
            options: Optional capture options

        Returns:
            List of CaptureResults for each event
        """
        results = []
        for event_info in events:
            event = event_info.get("event", "capture")
            selector = event_info.get("selector")
            result = await self.capture_on_event(target, event, selector, options)
            results.append(result)
            self.captures.append(result)
        return results

    async def start_session(self, target: str) -> bool:
        """
        Start a capture session for continuous capture.

        Override in subclasses that support persistent sessions.

        Args:
            target: Target identifier

        Returns:
            True if session started successfully
        """
        self._session_active = True
        return True

    async def end_session(self) -> List[CaptureResult]:
        """
        End capture session and return all captures.

        Returns:
            List of all captures from this session
        """
        self._session_active = False
        return self.captures

    def get_captures(self) -> List[CaptureResult]:
        """Get all captures from current session."""
        return self.captures

    def clear_captures(self):
        """Clear all stored captures."""
        self.captures = []

    @classmethod
    def can_handle(cls, target: str) -> bool:
        """
        Check if this adapter can handle the given target.

        Override in subclasses to implement target detection.

        Args:
            target: Target identifier

        Returns:
            True if this adapter can handle the target
        """
        return False

    def _generate_filename(self, prefix: str = "capture") -> str:
        """Generate unique filename for capture."""
        timestamp = int(time.time() * 1000)
        return f"{prefix}_{timestamp}"

    def _get_output_path(self, extension: str = ".png") -> Path:
        """Get output path for capture file."""
        output_dir = self.options.output_dir or Path.cwd() / ".tool-reader" / "captures"
        output_dir.mkdir(parents=True, exist_ok=True)

        name = self.options.output_name or self._generate_filename()
        if not name.endswith(extension):
            name += extension

        return output_dir / name


def detect_adapter_type(target: str) -> AdapterType:
    """
    Detect the appropriate adapter type for a target.

    Args:
        target: Target identifier (URL, command, window name)

    Returns:
        AdapterType for the target
    """
    target_lower = target.lower()

    # Web targets
    if target.startswith("http://") or target.startswith("https://"):
        return AdapterType.PLAYWRIGHT

    if target.startswith("localhost:") or target.startswith("127.0.0.1:"):
        return AdapterType.PLAYWRIGHT

    # Window targets
    if target.startswith("window:") or target.endswith(".exe"):
        return AdapterType.GUI

    # TUI targets
    if target.startswith("tui:") or "ratatui" in target_lower or "crossterm" in target_lower:
        return AdapterType.TUI

    # CLI/command targets
    if " " in target or target.startswith("cli:"):
        # Check for known TUI indicators
        if any(x in target_lower for x in ["cargo run", "npm run", "python"]):
            # Could be either - default to CLI, can be overridden
            return AdapterType.CLI

    return AdapterType.CLI  # Default to CLI for commands


def get_adapter(adapter_type: Union[AdapterType, str], options: Optional[CaptureOptions] = None) -> CaptureAdapter:
    """
    Get an adapter instance by type.

    Args:
        adapter_type: AdapterType enum or string name
        options: Optional capture options

    Returns:
        CaptureAdapter instance
    """
    if isinstance(adapter_type, str):
        adapter_type = AdapterType(adapter_type.lower())

    # Import adapters here to avoid circular imports
    from .playwright_adapter import PlaywrightAdapter
    from .browser_adapter import BrowserAdapter
    from .tui_adapter import TuiAdapter
    from .gui_adapter import GuiAdapter
    from .cli_adapter import CliAdapter

    adapters = {
        AdapterType.PLAYWRIGHT: PlaywrightAdapter,
        AdapterType.BROWSER: BrowserAdapter,
        AdapterType.TUI: TuiAdapter,
        AdapterType.GUI: GuiAdapter,
        AdapterType.CLI: CliAdapter,
    }

    adapter_class = adapters.get(adapter_type)
    if not adapter_class:
        raise ValueError(f"Unknown adapter type: {adapter_type}")

    return adapter_class(options)


def get_adapter_for_target(target: str, options: Optional[CaptureOptions] = None) -> CaptureAdapter:
    """
    Auto-detect and return appropriate adapter for target.

    Args:
        target: Target identifier
        options: Optional capture options

    Returns:
        CaptureAdapter instance appropriate for target
    """
    adapter_type = detect_adapter_type(target)
    return get_adapter(adapter_type, options)
