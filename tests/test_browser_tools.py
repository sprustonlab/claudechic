"""Unit tests for the browser control tool handlers.

Drives the real handlers against an AsyncMock-style fake page -- no
playwright, no Chromium. Also covers the missing-playwright path:
enabled-but-uninstalled must return actionable install guidance
(mirrors test_cluster_dispatch_missing_backend.py).
"""

from __future__ import annotations

import asyncio
import base64
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import claudechic.features.browser.session as browser_session
import claudechic.features.browser.tools as browser_tools

FAKE_PNG = b"\x89PNG\r\n\x1a\nfakepixels"


class FakePage:
    """Minimal stand-in for a playwright Page."""

    def __init__(self) -> None:
        self.url = "https://example.com/"
        self.viewport_size = {"width": 1280, "height": 900}
        self.goto = AsyncMock()
        self.click = AsyncMock()
        self.fill = AsyncMock()
        self.screenshot = AsyncMock(return_value=FAKE_PNG)
        self.mouse = SimpleNamespace(click=AsyncMock(), wheel=AsyncMock())
        self.keyboard = SimpleNamespace(type=AsyncMock(), press=AsyncMock())

    async def title(self) -> str:
        return "Example Domain"


class StubSession:
    """Replaces BrowserSession: hands out a fake page, never launches."""

    def __init__(self, page: FakePage) -> None:
        self.lock = asyncio.Lock()
        self._page = page
        self.errors: list[Exception] = []

    async def get_page(self) -> FakePage:
        return self._page

    async def handle_error(self, exc: Exception) -> None:
        self.errors.append(exc)


@pytest.fixture
def page(monkeypatch) -> FakePage:
    fake = FakePage()
    monkeypatch.setattr(browser_tools, "get_session", lambda: StubSession(fake))
    return fake


def _handlers() -> dict:
    return {
        t.name: t.handler for t in browser_tools.get_browser_tools(caller_name="tester")
    }


def _text_of(response: dict) -> str:
    return "\n".join(
        block.get("text", "")
        for block in response.get("content", [])
        if block.get("type") == "text"
    )


async def test_navigate_returns_title_and_url(page):
    response = await _handlers()["browser_navigate"]({"url": "https://example.com/"})
    assert response.get("isError") is not True
    text = _text_of(response)
    assert "Example Domain" in text
    assert "https://example.com/" in text
    page.goto.assert_awaited_once_with("https://example.com/", wait_until="load")


async def test_screenshot_has_image_and_text_blocks(page, monkeypatch, tmp_path):
    shot_path = tmp_path / "shot_001.png"
    monkeypatch.setattr(browser_tools, "next_screenshot_path", lambda: shot_path)
    response = await _handlers()["browser_screenshot"]({})
    assert response.get("isError") is not True

    blocks = response["content"]
    image_blocks = [b for b in blocks if b.get("type") == "image"]
    assert len(image_blocks) == 1
    assert image_blocks[0]["mimeType"] == "image/png"
    assert base64.b64decode(image_blocks[0]["data"]) == FAKE_PNG

    text = _text_of(response)
    assert "Example Domain" in text
    assert "1280x900" in text
    assert str(shot_path) in text
    # PNG is also saved to disk for user visibility / fallback.
    assert shot_path.read_bytes() == FAKE_PNG
    page.screenshot.assert_awaited_once_with(full_page=False)


async def test_screenshot_full_page_flag(page, monkeypatch, tmp_path):
    monkeypatch.setattr(
        browser_tools, "next_screenshot_path", lambda: tmp_path / "s.png"
    )
    await _handlers()["browser_screenshot"]({"full_page": True})
    page.screenshot.assert_awaited_once_with(full_page=True)


@pytest.mark.parametrize(
    "args",
    [
        {},  # neither selector nor coordinates
        {"selector": "#go", "x": 10, "y": 20},  # both
        {"x": 10},  # partial coordinates
        {"y": 20},  # partial coordinates
    ],
)
async def test_click_requires_exactly_one_target(page, args):
    response = await _handlers()["browser_click"](args)
    assert response.get("isError") is True
    page.click.assert_not_awaited()
    page.mouse.click.assert_not_awaited()


async def test_click_selector(page):
    response = await _handlers()["browser_click"]({"selector": "#go"})
    assert response.get("isError") is not True
    page.click.assert_awaited_once_with("#go")


async def test_click_coordinates(page):
    response = await _handlers()["browser_click"]({"x": 10, "y": 20})
    assert response.get("isError") is not True
    page.mouse.click.assert_awaited_once_with(10.0, 20.0)


async def test_type_fill_with_press_enter(page):
    response = await _handlers()["browser_type"](
        {"text": "SFO", "selector": "#origin", "press_enter": True}
    )
    assert response.get("isError") is not True
    page.fill.assert_awaited_once_with("#origin", "SFO")
    page.keyboard.press.assert_awaited_once_with("Enter")


async def test_type_without_enter_does_not_press(page):
    await _handlers()["browser_type"]({"text": "SFO"})
    page.keyboard.type.assert_awaited_once_with("SFO")
    page.keyboard.press.assert_not_awaited()


async def test_scroll_wheels_by_dy(page):
    response = await _handlers()["browser_scroll"]({"dy": 700})
    assert response.get("isError") is not True
    page.mouse.wheel.assert_awaited_once_with(0, 700)


async def test_page_error_returns_error_response(page):
    page.goto.side_effect = RuntimeError("net::ERR_NAME_NOT_RESOLVED")
    response = await _handlers()["browser_navigate"]({"url": "https://x.invalid"})
    assert response.get("isError") is True
    assert "browser_navigate failed" in _text_of(response)


async def test_missing_playwright_returns_install_guidance(monkeypatch):
    """Enabled-but-uninstalled: actionable guidance, not a traceback."""
    # Halt any playwright import (works whether or not it is installed).
    monkeypatch.setitem(sys.modules, "playwright", None)
    monkeypatch.setitem(sys.modules, "playwright.async_api", None)
    # Fresh real session so the lazy-import path actually runs.
    monkeypatch.setattr(browser_session, "_session", None)

    response = await browser_tools.browser_navigate.handler(
        {"url": "https://example.com"}
    )
    assert response.get("isError") is True
    text = _text_of(response)
    assert "claudechic[browser]" in text
    assert "playwright install chromium" in text
