"""Playwright-Chromium session management for the gated browser tools.

One shared browser + page per app process (documented v1 limitation).
ALL playwright imports are lazy (inside methods) so this module always
imports, even when the optional ``claudechic[browser]`` extra is absent.

Import boundary: config only -- no imports from app/, widgets/, mcp.py.
"""

from __future__ import annotations

import asyncio
import logging
import tempfile
from pathlib import Path
from typing import Any

from claudechic.config import CONFIG

log = logging.getLogger(__name__)

NAV_TIMEOUT_MS = 30_000
ACTION_TIMEOUT_MS = 10_000
VIEWPORT = {"width": 1280, "height": 900}
SHUTDOWN_TIMEOUT_S = 5

INSTALL_HINT = (
    "Playwright is not installed. Install the browser extra with: "
    'pip install "claudechic[browser]" (or: uv sync --extra browser), '
    "then run: playwright install chromium, and restart claudechic."
)
CHROMIUM_HINT = (
    "Chromium browser binary is missing. Run: playwright install chromium, then retry."
)

# Substrings in playwright error text that mean the browser process is
# gone and the session must be relaunched on the next call.
_DEAD_MARKERS = (
    "target closed",
    "browser has been closed",
    "connection closed",
    "browser closed",
    "has been closed",
)


class BrowserMissingError(RuntimeError):
    """Playwright or its Chromium binary is unavailable."""


class BrowserSession:
    """Holds the shared playwright driver, browser, and page."""

    def __init__(self) -> None:
        self._playwright: Any = None
        self._browser: Any = None
        self._page: Any = None
        self.lock = asyncio.Lock()

    async def get_page(self) -> Any:
        """Return the live page, launching Chromium on first use.

        Raises BrowserMissingError with install guidance when playwright
        or the Chromium binary is absent.
        """
        if self._page is not None:
            try:
                if not self._page.is_closed():
                    return self._page
            except Exception:
                # Driver died mid-check; fall through to relaunch.
                log.debug("Browser page liveness check failed", exc_info=True)
            await self.close()
        return await self._start()

    async def _start(self) -> Any:
        try:
            from playwright.async_api import (  # pyright: ignore[reportMissingImports]  # optional claudechic[browser] extra, lazily imported
                async_playwright,
            )
        except ImportError as exc:
            raise BrowserMissingError(INSTALL_HINT) from exc

        headless = bool(CONFIG.get("experimental", {}).get("browser_headless", True))
        try:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=headless)
            self._page = await self._browser.new_page(viewport=VIEWPORT)
        except Exception as exc:
            await self.close()
            text = str(exc)
            if "Executable doesn't exist" in text or "playwright install" in text:
                raise BrowserMissingError(CHROMIUM_HINT) from exc
            raise
        self._page.set_default_navigation_timeout(NAV_TIMEOUT_MS)
        self._page.set_default_timeout(ACTION_TIMEOUT_MS)
        log.info("Browser session started (headless=%s)", headless)
        return self._page

    async def handle_error(self, exc: Exception) -> None:
        """Reset the session if *exc* indicates the browser died.

        The next tool call then relaunches instead of failing forever.
        """
        text = str(exc).lower()
        if any(marker in text for marker in _DEAD_MARKERS):
            log.info("Browser appears dead; resetting session: %s", exc)
            await self.close()

    async def close(self) -> None:
        """Best-effort teardown of browser and playwright driver."""
        browser, playwright = self._browser, self._playwright
        self._page = None
        self._browser = None
        self._playwright = None
        if browser is not None:
            try:
                await asyncio.wait_for(browser.close(), SHUTDOWN_TIMEOUT_S)
            except Exception:
                log.debug("Browser close failed", exc_info=True)
        if playwright is not None:
            try:
                await asyncio.wait_for(playwright.stop(), SHUTDOWN_TIMEOUT_S)
            except Exception:
                log.debug("Playwright stop failed", exc_info=True)


# Module-global session, same pattern as _app in claudechic/mcp.py.
_session: BrowserSession | None = None

# Monotonic counter for screenshot filenames within this process.
_shot_counter = 0


def get_session() -> BrowserSession:
    """Return the process-wide BrowserSession, creating it lazily."""
    global _session
    if _session is None:
        _session = BrowserSession()
    return _session


async def shutdown_browser() -> None:
    """Close the shared browser if one was ever started.

    No-op when the session was never created -- never imports playwright
    for non-users.
    """
    global _session
    if _session is None:
        return
    session = _session
    _session = None
    await session.close()


def next_screenshot_path() -> Path:
    """Return the next screenshot save path under the temp directory."""
    global _shot_counter
    _shot_counter += 1
    shot_dir = Path(tempfile.gettempdir()) / "claudechic_browser"
    shot_dir.mkdir(parents=True, exist_ok=True)
    return shot_dir / f"shot_{_shot_counter:03d}.png"
