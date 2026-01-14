"""
Capture adapters for tool-reader.

Provides target-agnostic capture capabilities for:
- Web pages (Playwright, headless browser)
- Terminal apps (TUI)
- Desktop apps (GUI)
- CLI tools
"""

from .base import (
    CaptureAdapter,
    CaptureResult,
    CaptureOptions,
    CaptureType,
    AdapterType,
    detect_adapter_type,
)

# Import all adapters
from .playwright_adapter import PlaywrightAdapter
from .browser_adapter import BrowserAdapter
from .tui_adapter import TuiAdapter
from .gui_adapter import GuiAdapter
from .cli_adapter import CliAdapter

__all__ = [
    # Base classes and types
    "CaptureAdapter",
    "CaptureResult",
    "CaptureOptions",
    "CaptureType",
    "AdapterType",
    # Utility functions
    "detect_adapter_type",
    "get_adapter",
    "get_adapter_for_target",
    # Adapters
    "PlaywrightAdapter",
    "BrowserAdapter",
    "TuiAdapter",
    "GuiAdapter",
    "CliAdapter",
]


def get_adapter(adapter_type, options=None):
    """
    Get an adapter instance by type.

    Args:
        adapter_type: AdapterType enum or string name
        options: Optional CaptureOptions

    Returns:
        CaptureAdapter instance
    """
    if isinstance(adapter_type, str):
        adapter_type = AdapterType(adapter_type.lower())

    adapters = {
        AdapterType.PLAYWRIGHT: PlaywrightAdapter,
        AdapterType.BROWSER: BrowserAdapter,
        AdapterType.TUI: TuiAdapter,
        AdapterType.GUI: GuiAdapter,
        AdapterType.CLI: CliAdapter,
        AdapterType.AUTO: None,  # Auto-detect
    }

    if adapter_type == AdapterType.AUTO:
        raise ValueError("Use get_adapter_for_target() for auto-detection")

    adapter_class = adapters.get(adapter_type)
    if not adapter_class:
        raise ValueError(f"Unknown adapter type: {adapter_type}")

    return adapter_class(options)


def get_adapter_for_target(target, options=None):
    """
    Auto-detect and return appropriate adapter for target.

    Args:
        target: Target identifier (URL, command, window name)
        options: Optional CaptureOptions

    Returns:
        CaptureAdapter instance appropriate for target
    """
    adapter_type = detect_adapter_type(target)

    # For web targets, prefer Playwright if available
    if adapter_type == AdapterType.PLAYWRIGHT:
        if PlaywrightAdapter.is_available():
            return PlaywrightAdapter(options)
        else:
            return BrowserAdapter(options)

    return get_adapter(adapter_type, options)


def list_available_adapters():
    """
    List all available adapters and their status.

    Returns:
        Dict with adapter info
    """
    return {
        "playwright": {
            "available": PlaywrightAdapter.is_available(),
            "targets": ["http://", "https://"],
            "features": ["event-based", "sequences", "dom-capture"]
        },
        "browser": {
            "available": True,
            "targets": ["http://", "https://"],
            "features": ["screenshot"]
        },
        "tui": {
            "available": True,
            "targets": ["tui:", "cargo run", "terminal apps"],
            "features": ["ansi-capture", "input", "keys"]
        },
        "gui": {
            "available": True,
            "targets": ["window:", ".exe", "gui:"],
            "features": ["screenshot", "window-capture"]
        },
        "cli": {
            "available": True,
            "targets": ["commands", "scripts"],
            "features": ["stdout", "stderr", "exit-code"]
        }
    }
