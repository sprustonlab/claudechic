"""End-to-end tests for the code-block Copy button.

``SafeMarkdown`` swaps Textual's plain code fence for
``CopyableMarkdownFence``, which renders a header bar (language +
``⧉ Copy``) above every fenced code block. These tests drive the REAL
widget path in a mounted Textual app: they confirm the copyable fence is
what actually renders, that clicking the button copies the block's raw
source (not the syntax-highlighted content), and that a fence updated
mid-stream copies the *updated* source rather than its first-seen text.
"""

from __future__ import annotations

import pytest
from claudechic.widgets.content.safe_markdown import (
    CopyableMarkdownFence,
    SafeMarkdown,
)
from claudechic.widgets.primitives.button import Button
from textual.app import App, ComposeResult
from textual.widgets import Static
from textual.widgets._markdown import MarkdownFence

pytestmark = [pytest.mark.asyncio, pytest.mark.timeout(30)]

CODE = "uv tool install claudechic\nclaudechic --yolo"
DOC = f"Here is how to install it:\n\n```bash\n{CODE}\n```\n"


class _HostApp(App):
    """Minimal app hosting a SafeMarkdown; records clipboard writes."""

    def __init__(self, markdown: str) -> None:
        super().__init__()
        self._markdown = markdown
        self.copied: list[str] = []

    def compose(self) -> ComposeResult:
        yield SafeMarkdown(self._markdown)

    def copy_to_clipboard(self, text: str) -> None:  # type: ignore[override]
        # Record instead of touching the real system clipboard / OSC-52.
        self.copied.append(text)


async def test_fence_renders_as_copyable_with_header():
    """A fenced code block renders as CopyableMarkdownFence with a header
    showing the language and a Copy button."""
    app = _HostApp(DOC)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        fence = app.query_one(CopyableMarkdownFence)
        assert fence.code.strip() == CODE

        # Language label reflects the fence info string.
        assert fence.lexer == "bash"
        lang = fence.query_one(".fence-lang", Static)
        assert "bash" in str(lang.render())

        # Exactly one Copy button, inside the fence.
        button = fence.query_one(".fence-copy", Button)
        assert button is not None


async def test_clicking_copy_button_copies_raw_code():
    """Clicking the Copy button copies the block's raw source verbatim."""
    app = _HostApp(DOC)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        button = app.query_one(".fence-copy", Button)
        await pilot.click(button)
        await pilot.pause()

        assert app.copied, "Copy button click should have copied something"
        assert app.copied[-1].strip() == CODE
        # Highlighting artifacts must not leak in -- raw source only.
        assert "\x1b" not in app.copied[-1]


async def test_copy_reflects_streamed_update():
    """A fence updated mid-stream copies the UPDATED source, not the
    first-seen text (guards the self.code refresh in _update_from_block)."""
    app = _HostApp(DOC)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        fence = app.query_one(CopyableMarkdownFence)

        # Simulate what MarkdownStream does on a later token: build a fresh
        # fence carrying new source and fold it into the mounted one.
        new_code = "echo updated"
        replacement = CopyableMarkdownFence(fence._markdown, fence._token, new_code)
        await fence._update_from_block(replacement)

        assert fence.code == new_code

        await pilot.click(app.query_one(".fence-copy", Button))
        await pilot.pause()
        assert app.copied[-1] == new_code


async def test_copy_failure_notifies_and_does_not_raise():
    """If copy_to_clipboard raises, the click is swallowed with an error
    toast rather than crashing the TUI."""

    class _BrokenApp(_HostApp):
        def copy_to_clipboard(self, text: str) -> None:  # type: ignore[override]
            raise RuntimeError("clipboard unavailable")

    app = _BrokenApp(DOC)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        # Should not raise out of the event loop.
        await pilot.click(app.query_one(".fence-copy", Button))
        await pilot.pause()


async def test_disabled_config_renders_plain_fence(monkeypatch):
    """With code_copy_button=False, fences render as the plain Textual
    MarkdownFence with no Copy button."""
    from claudechic import config

    monkeypatch.setitem(config.CONFIG, "code_copy_button", False)

    app = _HostApp(DOC)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        # No copyable fence, no copy button; still a code fence present.
        assert not app.query(CopyableMarkdownFence)
        assert not app.query(".fence-copy")
        assert app.query(MarkdownFence), "a plain code fence should still render"
