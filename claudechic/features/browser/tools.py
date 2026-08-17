"""Gated browser control MCP tools (Playwright-Chromium backend).

Five tools: browser_navigate, browser_screenshot, browser_click,
browser_type, browser_scroll. Double-gated:

1. Registration requires ``experimental.browser: true`` in
   ``~/.claudechic/config.yaml`` (see create_chic_server in mcp.py).
2. Every call trips the package-tier ``global:browser_control`` deny
   rule in ``claudechic/defaults/global/rules.yaml``.

Importing claudechic.mcp at top level is safe: mcp.py imports this
package only inside create_chic_server (no import cycle).
"""

from __future__ import annotations

import base64
import logging
from typing import Any, Awaitable, Callable

from claude_agent_sdk import tool

from claudechic.features.browser.session import (
    VIEWPORT,
    BrowserMissingError,
    get_session,
    next_screenshot_path,
)
from claudechic.mcp import _error_response, _text_response, _track_mcp_tool

log = logging.getLogger(__name__)


async def _with_page(
    tool_name: str, action: Callable[[Any], Awaitable[dict[str, Any]]]
) -> dict[str, Any]:
    """Run *action(page)* under the session lock with shared error handling."""
    _track_mcp_tool(tool_name)
    session = get_session()
    async with session.lock:
        try:
            page = await session.get_page()
            return await action(page)
        except BrowserMissingError as exc:
            return _error_response(str(exc))
        except Exception as exc:
            await session.handle_error(exc)
            return _error_response(f"{tool_name} failed: {exc}")


@tool(
    "browser_navigate",
    "Navigate the shared browser to a URL and wait for the page to load. "
    "Returns the page title and final URL (after redirects).",
    {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "Absolute URL to open (e.g. https://example.com)",
            },
        },
        "required": ["url"],
    },
)
async def browser_navigate(args: dict[str, Any]) -> dict[str, Any]:
    """Navigate to a URL."""
    url = args["url"]

    async def action(page: Any) -> dict[str, Any]:
        await page.goto(url, wait_until="load")
        title = await page.title()
        return _text_response(f"Title: {title}\nURL: {page.url}")

    return await _with_page("browser_navigate", action)


@tool(
    "browser_screenshot",
    "Screenshot the shared browser page. Returns the image inline plus "
    "title/URL/viewport info and the temp-file path of the saved PNG. "
    "full_page captures the entire scrollable page and can cost MANY "
    "tokens -- prefer the default viewport-only capture.",
    {
        "type": "object",
        "properties": {
            "full_page": {
                "type": "boolean",
                "description": (
                    "Capture the full scrollable page instead of just the "
                    "viewport (default false; expensive in tokens)"
                ),
            },
        },
        "required": [],
    },
)
async def browser_screenshot(args: dict[str, Any]) -> dict[str, Any]:
    """Screenshot the current page."""
    full_page = bool(args.get("full_page", False))

    async def action(page: Any) -> dict[str, Any]:
        png = await page.screenshot(full_page=full_page)
        path = next_screenshot_path()
        path.write_bytes(png)
        title = await page.title()
        viewport = page.viewport_size or VIEWPORT
        info = (
            f"Title: {title}\n"
            f"URL: {page.url}\n"
            f"Viewport: {viewport['width']}x{viewport['height']}"
            + (" (full page capture)" if full_page else "")
            + f"\nSaved to: {path}"
        )
        return {
            "content": [
                {
                    "type": "image",
                    "data": base64.b64encode(png).decode("ascii"),
                    "mimeType": "image/png",
                },
                {"type": "text", "text": info},
            ]
        }

    return await _with_page("browser_screenshot", action)


@tool(
    "browser_click",
    "Click in the shared browser page. Pass EITHER a CSS selector OR "
    "viewport pixel coordinates (x and y together), not both. Reports the "
    "new title/URL if the click caused a navigation.",
    {
        "type": "object",
        "properties": {
            "selector": {
                "type": "string",
                "description": "CSS selector of the element to click",
            },
            "x": {
                "type": "number",
                "description": "Viewport x coordinate in pixels (requires y)",
            },
            "y": {
                "type": "number",
                "description": "Viewport y coordinate in pixels (requires x)",
            },
        },
        "required": [],
    },
)
async def browser_click(args: dict[str, Any]) -> dict[str, Any]:
    """Click via selector or coordinates."""
    selector = args.get("selector")
    x = args.get("x")
    y = args.get("y")
    if (x is None) != (y is None):
        return _error_response("browser_click coordinate clicks need BOTH x and y.")
    has_selector = selector is not None
    # Narrow coordinates here: pyright cannot propagate the has_xy check
    # into the nested closure below.
    coords = (float(x), float(y)) if x is not None and y is not None else None
    if has_selector == (coords is not None):
        return _error_response(
            "browser_click needs exactly one of: 'selector', or 'x' and 'y'."
        )

    async def action(page: Any) -> dict[str, Any]:
        url_before = page.url
        if coords is None:
            await page.click(selector)
            what = f"selector {selector!r}"
        else:
            await page.mouse.click(coords[0], coords[1])
            what = f"({x}, {y})"
        if page.url != url_before:
            title = await page.title()
            return _text_response(
                f"Clicked {what}. Navigated to:\nTitle: {title}\nURL: {page.url}"
            )
        return _text_response(f"Clicked {what}.")

    return await _with_page("browser_click", action)


@tool(
    "browser_type",
    "Type text in the shared browser page. With a selector, fills that "
    "field (replacing its contents); without, types at the current focus. "
    "Set press_enter to submit afterwards.",
    {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to type"},
            "selector": {
                "type": "string",
                "description": "CSS selector of the input to fill (optional)",
            },
            "press_enter": {
                "type": "boolean",
                "description": "Press Enter after typing (default false)",
            },
        },
        "required": ["text"],
    },
)
async def browser_type(args: dict[str, Any]) -> dict[str, Any]:
    """Type text, optionally into a selector, optionally pressing Enter."""
    text = args["text"]
    selector = args.get("selector")
    press_enter = bool(args.get("press_enter", False))

    async def action(page: Any) -> dict[str, Any]:
        if selector:
            await page.fill(selector, text)
            target = f"into {selector!r}"
        else:
            await page.keyboard.type(text)
            target = "at current focus"
        if press_enter:
            await page.keyboard.press("Enter")
        suffix = " and pressed Enter" if press_enter else ""
        return _text_response(
            f"Typed {len(text)} characters {target}{suffix}. URL: {page.url}"
        )

    return await _with_page("browser_type", action)


@tool(
    "browser_scroll",
    "Scroll the shared browser page vertically by dy pixels (positive = "
    "down, negative = up).",
    {
        "type": "object",
        "properties": {
            "dy": {
                "type": "integer",
                "description": "Vertical scroll amount in pixels",
            },
        },
        "required": ["dy"],
    },
)
async def browser_scroll(args: dict[str, Any]) -> dict[str, Any]:
    """Scroll the page vertically."""
    dy = int(args["dy"])

    async def action(page: Any) -> dict[str, Any]:
        await page.mouse.wheel(0, dy)
        return _text_response(f"Scrolled by dy={dy}. URL: {page.url}")

    return await _with_page("browser_scroll", action)


def get_browser_tools(caller_name: str | None = None) -> list[Any]:
    """Return the five browser tools for MCP server registration.

    *caller_name* is accepted for signature parity with the other tool
    factories in mcp.py; the v1 shared-browser design has no per-caller
    state.
    """
    del caller_name
    return [
        browser_navigate,
        browser_screenshot,
        browser_click,
        browser_type,
        browser_scroll,
    ]
