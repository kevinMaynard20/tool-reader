#!/usr/bin/env python3
"""
Capture Hook for tool-reader.
Accepts screenshots from external sources (Playwright scripts, manual captures, etc.)
"""

import json
import shutil
import time
import hashlib
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from datetime import datetime
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent

# Try to import watchdog for directory watching
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileCreatedEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False


@dataclass
class CaptureMetadata:
    """Metadata for a captured screenshot."""
    id: str
    original_path: str
    stored_path: str
    event: str = ""
    description: str = ""
    timestamp: float = field(default_factory=time.time)
    source: str = "external"  # external, playwright, browser, etc.
    verified: bool = False
    verification_result: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    custom_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CaptureStore:
    """
    Manages storage of captures with metadata.
    """

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir) if base_dir else Path.cwd() / ".tool-reader" / "captures"
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.metadata_file = self.base_dir / "captures.json"
        self.captures: Dict[str, CaptureMetadata] = {}

        self._load_metadata()

    def _load_metadata(self):
        """Load existing metadata from file."""
        if self.metadata_file.exists():
            try:
                data = json.loads(self.metadata_file.read_text(encoding='utf-8'))
                for item in data.get("captures", []):
                    cap = CaptureMetadata(**item)
                    self.captures[cap.id] = cap
            except Exception:
                pass

    def _save_metadata(self):
        """Save metadata to file."""
        data = {
            "captures": [cap.to_dict() for cap in self.captures.values()],
            "updated": time.time()
        }
        self.metadata_file.write_text(json.dumps(data, indent=2), encoding='utf-8')

    def _generate_id(self, path: str) -> str:
        """Generate unique ID for capture."""
        content = f"{path}_{time.time()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def add_capture(
        self,
        path: str,
        event: str = "",
        description: str = "",
        source: str = "external",
        tags: Optional[List[str]] = None,
        custom_data: Optional[Dict[str, Any]] = None
    ) -> CaptureMetadata:
        """
        Add a capture to the store.

        Args:
            path: Path to the capture file
            event: Event that triggered the capture
            description: Human-readable description
            source: Source of capture (external, playwright, etc.)
            tags: Optional tags for categorization
            custom_data: Optional additional metadata

        Returns:
            CaptureMetadata for the stored capture
        """
        source_path = Path(path)
        if not source_path.exists():
            raise FileNotFoundError(f"Capture file not found: {path}")

        # Generate ID and destination path
        cap_id = self._generate_id(path)
        timestamp = int(time.time())
        ext = source_path.suffix
        dest_name = f"{cap_id}_{timestamp}{ext}"
        dest_path = self.base_dir / dest_name

        # Copy file to store
        shutil.copy2(source_path, dest_path)

        # Create metadata
        metadata = CaptureMetadata(
            id=cap_id,
            original_path=str(source_path.absolute()),
            stored_path=str(dest_path),
            event=event,
            description=description,
            source=source,
            tags=tags or [],
            custom_data=custom_data or {}
        )

        self.captures[cap_id] = metadata
        self._save_metadata()

        return metadata

    def get_capture(self, cap_id: str) -> Optional[CaptureMetadata]:
        """Get capture by ID."""
        return self.captures.get(cap_id)

    def get_all_captures(self) -> List[CaptureMetadata]:
        """Get all captures."""
        return list(self.captures.values())

    def get_pending_captures(self) -> List[CaptureMetadata]:
        """Get captures that haven't been verified yet."""
        return [c for c in self.captures.values() if not c.verified]

    def get_captures_by_tag(self, tag: str) -> List[CaptureMetadata]:
        """Get captures with specific tag."""
        return [c for c in self.captures.values() if tag in c.tags]

    def get_captures_by_source(self, source: str) -> List[CaptureMetadata]:
        """Get captures from specific source."""
        return [c for c in self.captures.values() if c.source == source]

    def mark_verified(self, cap_id: str, result: str):
        """Mark a capture as verified."""
        if cap_id in self.captures:
            self.captures[cap_id].verified = True
            self.captures[cap_id].verification_result = result
            self._save_metadata()

    def delete_capture(self, cap_id: str):
        """Delete a capture."""
        if cap_id in self.captures:
            # Delete file
            stored_path = Path(self.captures[cap_id].stored_path)
            if stored_path.exists():
                stored_path.unlink()

            del self.captures[cap_id]
            self._save_metadata()

    def clear_all(self):
        """Clear all captures."""
        for cap in self.captures.values():
            stored_path = Path(cap.stored_path)
            if stored_path.exists():
                stored_path.unlink()

        self.captures.clear()
        self._save_metadata()

    def get_capture_paths(self) -> List[str]:
        """Get paths to all stored captures."""
        return [c.stored_path for c in self.captures.values()]


class CaptureHook:
    """
    Hook for accepting captures from external sources.

    Supports:
    - Manual capture registration
    - Directory watching for auto-registration
    - Metadata association
    """

    def __init__(self, capture_dir: Optional[str] = None):
        self.store = CaptureStore(capture_dir)
        self._observer = None
        self._watch_callbacks = []

    def accept(
        self,
        path: str,
        event: str = "",
        description: str = "",
        tags: Optional[List[str]] = None
    ) -> CaptureMetadata:
        """
        Accept a capture from external source.

        Args:
            path: Path to capture file
            event: Event description (e.g., "clicked login button")
            description: Human-readable description
            tags: Optional tags

        Returns:
            CaptureMetadata for stored capture
        """
        return self.store.add_capture(
            path=path,
            event=event,
            description=description,
            source="external",
            tags=tags
        )

    def accept_batch(
        self,
        paths: List[str],
        common_tags: Optional[List[str]] = None
    ) -> List[CaptureMetadata]:
        """
        Accept multiple captures at once.

        Args:
            paths: List of capture file paths
            common_tags: Tags to apply to all captures

        Returns:
            List of CaptureMetadata
        """
        results = []
        for i, path in enumerate(paths):
            try:
                meta = self.store.add_capture(
                    path=path,
                    event=f"batch_{i+1}",
                    source="external",
                    tags=common_tags or []
                )
                results.append(meta)
            except Exception as e:
                print(f"Failed to accept {path}: {e}")
        return results

    def start_watching(
        self,
        watch_dir: Optional[str] = None,
        callback: Optional[callable] = None
    ):
        """
        Start watching a directory for new captures.

        Args:
            watch_dir: Directory to watch (defaults to capture store dir)
            callback: Optional callback when new capture detected
        """
        if not WATCHDOG_AVAILABLE:
            print("watchdog not installed. Run: pip install watchdog")
            return

        watch_path = Path(watch_dir) if watch_dir else self.store.base_dir / "incoming"
        watch_path.mkdir(parents=True, exist_ok=True)

        class CaptureHandler(FileSystemEventHandler):
            def __init__(self, hook, cb):
                self.hook = hook
                self.callback = cb

            def on_created(self, event):
                if not event.is_directory:
                    ext = Path(event.src_path).suffix.lower()
                    if ext in ['.png', '.jpg', '.jpeg', '.gif', '.txt', '.html']:
                        meta = self.hook.accept(
                            event.src_path,
                            event=f"detected:{Path(event.src_path).name}"
                        )
                        if self.callback:
                            self.callback(meta)

        handler = CaptureHandler(self, callback)
        self._observer = Observer()
        self._observer.schedule(handler, str(watch_path), recursive=False)
        self._observer.start()
        print(f"Watching {watch_path} for new captures...")

    def stop_watching(self):
        """Stop watching for new captures."""
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None

    def get_pending(self) -> List[CaptureMetadata]:
        """Get captures pending verification."""
        return self.store.get_pending_captures()

    def get_all(self) -> List[CaptureMetadata]:
        """Get all captures."""
        return self.store.get_all_captures()

    def get_paths(self) -> List[str]:
        """Get paths to all stored captures."""
        return self.store.get_capture_paths()

    def clear(self):
        """Clear all captures."""
        self.store.clear_all()


# Global hook instance for easy access
_global_hook: Optional[CaptureHook] = None


def get_hook(capture_dir: Optional[str] = None) -> CaptureHook:
    """Get or create global capture hook."""
    global _global_hook
    if _global_hook is None:
        _global_hook = CaptureHook(capture_dir)
    return _global_hook


def accept_capture(
    path: str,
    event: str = "",
    description: str = ""
) -> CaptureMetadata:
    """Convenience function to accept a capture."""
    return get_hook().accept(path, event, description)


def get_pending_captures() -> List[CaptureMetadata]:
    """Get captures pending verification."""
    return get_hook().get_pending()


def get_capture_paths() -> List[str]:
    """Get paths to all stored captures."""
    return get_hook().get_paths()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Capture hook for tool-reader")
    subparsers = parser.add_subparsers(dest="command")

    # add command
    add_parser = subparsers.add_parser("add", help="Add a capture")
    add_parser.add_argument("path", help="Path to capture file")
    add_parser.add_argument("--event", default="", help="Event description")
    add_parser.add_argument("--desc", default="", help="Description")
    add_parser.add_argument("--tags", nargs="+", help="Tags")

    # list command
    list_parser = subparsers.add_parser("list", help="List captures")
    list_parser.add_argument("--pending", action="store_true", help="Only pending")

    # watch command
    watch_parser = subparsers.add_parser("watch", help="Watch directory")
    watch_parser.add_argument("--dir", help="Directory to watch")

    # clear command
    subparsers.add_parser("clear", help="Clear all captures")

    args = parser.parse_args()
    hook = CaptureHook()

    if args.command == "add":
        meta = hook.accept(args.path, args.event, args.desc, args.tags)
        print(f"Added capture: {meta.id}")
        print(f"Stored at: {meta.stored_path}")

    elif args.command == "list":
        captures = hook.get_pending() if args.pending else hook.get_all()
        for cap in captures:
            status = "[pending]" if not cap.verified else "[verified]"
            print(f"{cap.id} {status} - {cap.event or 'no event'}")
            print(f"  Path: {cap.stored_path}")

    elif args.command == "watch":
        def on_capture(meta):
            print(f"New capture: {meta.id} - {meta.stored_path}")

        hook.start_watching(args.dir, on_capture)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            hook.stop_watching()
            print("Stopped watching")

    elif args.command == "clear":
        hook.clear()
        print("Cleared all captures")
