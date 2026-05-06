"""Tests for the URL-click confirmation flow.

Originally driven by the user complaint "is there a way to cancel the
in-app web browser, if I click a link by mistake it is very annoying
to wait and exit." There is no in-app browser -- the freeze is
Textual's default ``Markdown`` widget calling ``webbrowser.open``
synchronously on the event loop. The fix has three pieces, each
covered here:

1. ``SafeMarkdown`` defaults ``open_links=False`` so the ``Markdown``
   widget does not auto-launch the browser. The LinkClicked event
   bubbles up to the app instead.
2. ``ChatApp.on_markdown_link_clicked`` shows ``URLConfirmModal`` and
   only opens the URL on confirm.
3. The actual ``webbrowser.open`` call runs on a worker thread via
   ``asyncio.to_thread`` so even on confirm the event loop is never
   blocked.

The tests assert each piece in isolation plus an end-to-end flow that
mounts a real ``SafeMarkdown``, simulates a link click, and verifies
the modal shows / browser opens / cancel is honored.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from claudechic.app import ChatApp
from claudechic.widgets.content.safe_markdown import SafeMarkdown
from claudechic.widgets.modals.url_confirm import URLConfirmModal


# ---------------------------------------------------------------------------
# Unit: SafeMarkdown
# ---------------------------------------------------------------------------


def test_safe_markdown_defaults_open_links_false() -> None:
    """Without an explicit override, SafeMarkdown turns off Textual's
    auto-open behavior. This is the keystone of the fix -- if a future
    refactor flips the default, the synchronous-freeze bug returns."""
    widget = SafeMarkdown("# hi")
    assert widget._open_links is False, (
        "SafeMarkdown must default open_links=False so link clicks "
        "bubble to ChatApp.on_markdown_link_clicked instead of going "
        "through the synchronous webbrowser.open path"
    )


def test_safe_markdown_respects_explicit_open_links() -> None:
    """Callers may still opt into the default Textual behavior. The
    safety property is the *default*, not a hard prohibition."""
    widget = SafeMarkdown("# hi", open_links=True)
    assert widget._open_links is True


# ---------------------------------------------------------------------------
# Unit: URLConfirmModal
# ---------------------------------------------------------------------------


def test_url_confirm_modal_exposes_url() -> None:
    """Sanity that the URL we pass in is what the modal reports back.
    Tests further down inspect ``modal.url`` to assert that the right
    URL was offered to the user."""
    modal = URLConfirmModal("https://example.com/very/long/path?q=1")
    assert modal.url == "https://example.com/very/long/path?q=1"


# ---------------------------------------------------------------------------
# Integration: ChatApp.on_markdown_link_clicked
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_link_click_pushes_confirm_modal(mock_sdk) -> None:
    """A markdown link click pushes URLConfirmModal carrying the URL
    -- it does NOT call webbrowser.open. This is the core
    misclick-protection contract."""
    app = ChatApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        with patch("webbrowser.open") as mock_open:
            # Simulate the link-click event by invoking the handler
            # directly with a stub event object that carries .href.
            # Using the real handler path means a future refactor that
            # renames the attribute or skips event.stop() will be caught.
            event = MagicMock()
            event.href = "https://example.com/clicked"
            app.on_markdown_link_clicked(event)
            await pilot.pause()

            # Modal is now on top of the screen stack.
            top = app.screen
            assert isinstance(top, URLConfirmModal), (
                f"Expected URLConfirmModal on top of stack, got {type(top).__name__}"
            )
            assert top.url == "https://example.com/clicked"

            # Crucially, no browser was launched yet -- the user has not
            # confirmed. This is the misclick protection.
            mock_open.assert_not_called()

            # event.stop must have been called so the click does not
            # leak to other handlers (no double-modal).
            event.stop.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_confirm_modal_yes_opens_url_on_thread(mock_sdk) -> None:
    """Pressing 'y' in the confirm modal launches webbrowser.open --
    AND it goes through asyncio.to_thread so the event loop is not
    blocked. The to_thread routing is the half of the fix that prevents
    the original freeze even on intentional clicks."""
    app = ChatApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        with (
            patch("webbrowser.open") as mock_open,
            patch(
                "asyncio.to_thread",
                wraps=__import__("asyncio").to_thread,
            ) as spy_to_thread,
        ):
            event = MagicMock()
            event.href = "https://example.com/intentional"
            app.on_markdown_link_clicked(event)
            await pilot.pause()
            assert isinstance(app.screen, URLConfirmModal)

            # Press 'y' to confirm.
            await pilot.press("y")
            await pilot.pause()
            # Allow the scheduled to_thread to run.
            await pilot.pause()

            # webbrowser.open got the right URL.
            mock_open.assert_called_once_with("https://example.com/intentional")
            # And it went via to_thread (not inline on the loop). Look
            # for the call whose first positional arg is webbrowser.open.
            assert any(
                call.args and call.args[0] is __import__("webbrowser").open
                for call in spy_to_thread.call_args_list
            ), (
                "webbrowser.open must be dispatched through asyncio.to_thread "
                "to keep the OS browser-spawn off the event loop"
            )


@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_confirm_modal_escape_cancels_no_open(mock_sdk) -> None:
    """Pressing escape (or 'n') dismisses the modal without launching
    the browser. This is the misclick path -- the whole point of the
    feature."""
    app = ChatApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        with patch("webbrowser.open") as mock_open:
            event = MagicMock()
            event.href = "https://example.com/misclick"
            app.on_markdown_link_clicked(event)
            await pilot.pause()
            assert isinstance(app.screen, URLConfirmModal)

            await pilot.press("escape")
            await pilot.pause()

            # Modal is gone, browser was not launched.
            assert not isinstance(app.screen, URLConfirmModal)
            mock_open.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_link_click_with_empty_href_is_ignored(mock_sdk) -> None:
    """A pathological event with no href -- shouldn't crash and
    shouldn't pop a modal with an empty URL."""
    app = ChatApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        event = MagicMock()
        event.href = ""
        app.on_markdown_link_clicked(event)
        await pilot.pause()

        assert not isinstance(app.screen, URLConfirmModal), (
            "Empty href should not pop the confirm modal"
        )


# ---------------------------------------------------------------------------
# End-to-end: SafeMarkdown -> bubbled event -> ChatApp handler
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_e2e_safe_markdown_click_routes_through_app_handler(mock_sdk) -> None:
    """Mounts a real SafeMarkdown widget, posts a Markdown.LinkClicked
    message from it, and verifies the app's confirm flow fires. This
    catches a regression where SafeMarkdown stops bubbling the event
    or where ChatApp's handler signature changes shape."""
    from textual.widgets import Markdown as TextualMarkdown

    app = ChatApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        # Mount a SafeMarkdown into the active screen so the
        # LinkClicked message has a real bubble path to the app.
        md = SafeMarkdown("[click me](https://example.com/e2e)")
        await app.screen.mount(md)
        await pilot.pause()

        with patch("webbrowser.open") as mock_open:
            md.post_message(TextualMarkdown.LinkClicked(md, "https://example.com/e2e"))
            await pilot.pause()

            # Confirm modal arrived from the bubbled event.
            assert isinstance(app.screen, URLConfirmModal)
            assert app.screen.url == "https://example.com/e2e"

            # Misclick path: dismiss.
            await pilot.press("escape")
            await pilot.pause()
            mock_open.assert_not_called()
