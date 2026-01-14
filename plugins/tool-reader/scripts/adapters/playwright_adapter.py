#!/usr/bin/env python3
"""
Playwright adapter for tool-reader.
Full-featured web capture with event-based screenshots.
"""

import asyncio
import time
from pathlib import Path
from typing import Optional, List, Dict, Any

from .base import (
    CaptureAdapter,
    CaptureResult,
    CaptureOptions,
    CaptureType,
    AdapterType,
)

# Try to import playwright
try:
    from playwright.async_api import async_playwright, Browser, Page, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class PlaywrightAdapter(CaptureAdapter):
    """
    Capture adapter using Playwright.

    Supports:
    - Headless browser screenshots
    - Event-based capture (click, navigate, input)
    - Sequence capture for user flows
    - Full page screenshots
    - DOM snapshots
    """

    adapter_type = AdapterType.PLAYWRIGHT
    capture_type = CaptureType.SCREENSHOT

    def __init__(self, options: Optional[CaptureOptions] = None):
        super().__init__(options)
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    @classmethod
    def is_available(cls) -> bool:
        """Check if Playwright is installed."""
        return PLAYWRIGHT_AVAILABLE

    @classmethod
    def can_handle(cls, target: str) -> bool:
        """Check if this adapter can handle the target."""
        if not PLAYWRIGHT_AVAILABLE:
            return False
        return target.startswith("http://") or target.startswith("https://")

    async def start_session(self, target: str) -> bool:
        """
        Start a browser session for continuous capture.

        Args:
            target: URL to navigate to

        Returns:
            True if session started successfully
        """
        if not PLAYWRIGHT_AVAILABLE:
            return False

        try:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=True
            )
            self._context = await self._browser.new_context(
                viewport={
                    "width": self.options.width,
                    "height": self.options.height
                }
            )
            self._page = await self._context.new_page()
            await self._page.goto(target, wait_until="networkidle")
            self._session_active = True
            return True

        except Exception as e:
            print(f"Failed to start Playwright session: {e}")
            return False

    async def end_session(self) -> List[CaptureResult]:
        """End browser session and return all captures."""
        try:
            if self._page:
                await self._page.close()
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception:
            pass

        self._page = None
        self._context = None
        self._browser = None
        self._playwright = None
        self._session_active = False

        return self.captures

    async def capture(self, target: str, options: Optional[CaptureOptions] = None) -> CaptureResult:
        """
        Capture screenshot of webpage.

        Args:
            target: URL to capture
            options: Optional capture options

        Returns:
            CaptureResult with screenshot path
        """
        if not PLAYWRIGHT_AVAILABLE:
            return CaptureResult(
                success=False,
                capture_type=CaptureType.SCREENSHOT,
                error="Playwright not installed. Run: pip install playwright && playwright install"
            )

        opts = options or self.options
        output_path = self._get_output_path(".png")

        try:
            # Use existing session or create new one
            if self._session_active and self._page:
                page = self._page
                if page.url != target:
                    await page.goto(target, wait_until="networkidle")
            else:
                # One-shot capture
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True)
                    context = await browser.new_context(
                        viewport={"width": opts.width, "height": opts.height}
                    )
                    page = await context.new_page()
                    await page.goto(target, wait_until="networkidle")

                    if opts.wait_before > 0:
                        await asyncio.sleep(opts.wait_before)

                    await page.screenshot(
                        path=str(output_path),
                        full_page=opts.full_page
                    )

                    await browser.close()

                    result = CaptureResult(
                        success=True,
                        capture_type=CaptureType.SCREENSHOT,
                        content_path=str(output_path),
                        metadata={
                            "url": target,
                            "width": opts.width,
                            "height": opts.height,
                            "full_page": opts.full_page
                        }
                    )
                    self.captures.append(result)
                    return result

            # Session-based capture
            if opts.wait_before > 0:
                await asyncio.sleep(opts.wait_before)

            await page.screenshot(
                path=str(output_path),
                full_page=opts.full_page
            )

            result = CaptureResult(
                success=True,
                capture_type=CaptureType.SCREENSHOT,
                content_path=str(output_path),
                metadata={
                    "url": page.url,
                    "width": opts.width,
                    "height": opts.height,
                    "full_page": opts.full_page
                }
            )
            self.captures.append(result)
            return result

        except Exception as e:
            return CaptureResult(
                success=False,
                capture_type=CaptureType.SCREENSHOT,
                error=str(e)
            )

    async def capture_on_event(
        self,
        target: str,
        event: str,
        selector: Optional[str] = None,
        options: Optional[CaptureOptions] = None
    ) -> CaptureResult:
        """
        Capture screenshot after specific event.

        Events:
        - click: Click element then capture
        - navigate: Wait for navigation then capture
        - input: Type into element then capture
        - wait: Wait specified time then capture
        - hover: Hover element then capture
        - scroll: Scroll to element then capture

        Args:
            target: URL (if no session) or ignored (if session active)
            event: Event type
            selector: CSS selector or input value
            options: Optional capture options
        """
        if not PLAYWRIGHT_AVAILABLE:
            return CaptureResult(
                success=False,
                capture_type=CaptureType.SCREENSHOT,
                error="Playwright not installed"
            )

        opts = options or self.options

        # Ensure we have a page
        if not self._session_active or not self._page:
            await self.start_session(target)

        if not self._page:
            return CaptureResult(
                success=False,
                capture_type=CaptureType.SCREENSHOT,
                error="Failed to create browser session"
            )

        try:
            output_path = self._get_output_path(".png")
            event_desc = f"{event}"

            if event == "click" and selector:
                await self._page.click(selector)
                event_desc = f"click:{selector}"

            elif event == "navigate":
                if selector:
                    await self._page.goto(selector, wait_until="networkidle")
                else:
                    await self._page.wait_for_load_state("networkidle")
                event_desc = f"navigate:{selector or 'current'}"

            elif event == "input" and selector:
                # selector format: "#element=value" or just "#element"
                if "=" in selector:
                    elem_selector, value = selector.split("=", 1)
                    await self._page.fill(elem_selector, value)
                    event_desc = f"input:{elem_selector}"
                else:
                    # Just focus the element
                    await self._page.focus(selector)
                    event_desc = f"focus:{selector}"

            elif event == "wait":
                wait_time = float(selector) if selector else 1.0
                await asyncio.sleep(wait_time)
                event_desc = f"wait:{wait_time}s"

            elif event == "hover" and selector:
                await self._page.hover(selector)
                event_desc = f"hover:{selector}"

            elif event == "scroll" and selector:
                await self._page.evaluate(f'document.querySelector("{selector}").scrollIntoView()')
                event_desc = f"scroll:{selector}"

            elif event == "screenshot":
                # Just capture, no action
                event_desc = "screenshot"

            # Small wait after action for rendering
            await asyncio.sleep(0.3)

            # Capture screenshot
            await self._page.screenshot(
                path=str(output_path),
                full_page=opts.full_page
            )

            result = CaptureResult(
                success=True,
                capture_type=CaptureType.SCREENSHOT,
                content_path=str(output_path),
                event=event_desc,
                metadata={
                    "url": self._page.url,
                    "event": event,
                    "selector": selector
                }
            )
            self.captures.append(result)
            return result

        except Exception as e:
            return CaptureResult(
                success=False,
                capture_type=CaptureType.SCREENSHOT,
                event=f"{event}:{selector}",
                error=str(e)
            )

    async def capture_sequence(
        self,
        target: str,
        events: List[Dict[str, Any]],
        options: Optional[CaptureOptions] = None
    ) -> List[CaptureResult]:
        """
        Capture a sequence of events (user flow).

        Args:
            target: Starting URL
            events: List of event dicts with 'event' and 'selector' keys
            options: Optional capture options

        Returns:
            List of CaptureResults for each event

        Example events:
        [
            {"event": "screenshot"},
            {"event": "click", "selector": "#login-btn"},
            {"event": "input", "selector": "#email=test@example.com"},
            {"event": "input", "selector": "#password=secret"},
            {"event": "click", "selector": "#submit"},
            {"event": "navigate"},
            {"event": "screenshot"}
        ]
        """
        results = []
        opts = options or self.options

        # Start session
        if not self._session_active:
            await self.start_session(target)

        for event_info in events:
            event = event_info.get("event", "screenshot")
            selector = event_info.get("selector")

            result = await self.capture_on_event(target, event, selector, opts)
            results.append(result)

            # Stop on failure if requested
            if not result.success and event_info.get("stop_on_fail", False):
                break

            # Wait between events if specified
            if "wait_after" in event_info:
                await asyncio.sleep(event_info["wait_after"])

        return results

    async def capture_dom(self, target: str) -> CaptureResult:
        """Capture DOM snapshot instead of screenshot."""
        if not self._session_active or not self._page:
            await self.start_session(target)

        if not self._page:
            return CaptureResult(
                success=False,
                capture_type=CaptureType.DOM,
                error="Failed to create browser session"
            )

        try:
            output_path = self._get_output_path(".html")
            html = await self._page.content()
            output_path.write_text(html, encoding='utf-8')

            result = CaptureResult(
                success=True,
                capture_type=CaptureType.DOM,
                content_path=str(output_path),
                content_text=html[:1000] + "..." if len(html) > 1000 else html,
                metadata={
                    "url": self._page.url,
                    "html_length": len(html)
                }
            )
            self.captures.append(result)
            return result

        except Exception as e:
            return CaptureResult(
                success=False,
                capture_type=CaptureType.DOM,
                error=str(e)
            )
