"""SafeMarkdown -- Markdown widget that does NOT auto-launch links.

Textual's default ``Markdown`` widget has ``open_links=True`` and
routes clicks through the app's URL-opening path, which ultimately
calls ``webbrowser`` synchronously. While the OS spawns the browser
process the entire TUI event loop is frozen. On WSL, Linux without
``$DISPLAY`` set, or remote SSH sessions the freeze can be many
seconds and there is no way to interrupt it -- escape, Ctrl+C, and
the like never reach the TUI until the synchronous launch returns.

``SafeMarkdown`` flips ``open_links`` off by default. The
``Markdown.LinkClicked`` message still bubbles up the widget tree, so
``ChatApp.on_markdown_link_clicked`` can intercept it, prompt the
user via ``URLConfirmModal``, and -- on confirm -- launch the browser
on a worker thread (no event-loop block).

Use ``SafeMarkdown`` in place of ``Markdown`` everywhere we render
content that may contain links: chat messages, tool output, plan
panels, prompt previews, file previews. Importing the bare
``textual.widgets.Markdown`` re-introduces the freeze; a comment in
each call site reminds future contributors why.

``SafeMarkdown`` also swaps Textual's plain code-fence widget for
``CopyableMarkdownFence`` (via the supported ``get_block_class`` hook),
which renders a header bar above every fenced code block with the
language on the left and a one-click ``Copy`` button on the right.
Terminal commands and snippets an agent produces are the things a user
most often wants to copy/paste, so the button copies the block's raw
(un-highlighted) source verbatim.
"""

from __future__ import annotations

import logging
from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, HorizontalScroll
from textual.widgets import Label, Markdown, Static

# ``MarkdownFence`` is the block widget Textual instantiates for fenced
# and indented code blocks. It lives in a private module, but the class
# itself is stable and is the documented target of the ``BLOCKS`` /
# ``get_block_class`` extension point we hook below. Importing it by name
# (rather than pulling it out of ``Markdown.BLOCKS`` dynamically) gives
# the type checker a concrete base class to reason about.
from textual.widgets._markdown import MarkdownBlock, MarkdownFence

from claudechic.widgets.primitives.button import Button

log = logging.getLogger(__name__)


class CopyableMarkdownFence(MarkdownFence):
    """A code fence with a header bar carrying the language + a Copy button.

    Layout::

        ┌ header ─────────────────────────────┐
        │ bash                        ⧉ Copy   │
        ├ body (horizontally scrollable) ──────┤
        │ uv tool install …                    │
        └──────────────────────────────────────┘

    The Copy button copies ``self.code`` -- the block's raw source as
    parsed by markdown-it, *not* the syntax-highlighted ``Content`` -- so
    what lands on the clipboard is exactly what you'd paste into a shell.
    ``self.code`` is refreshed on every streaming update so copies stay
    correct while an answer is still being written.
    """

    DEFAULT_CSS = """
    CopyableMarkdownFence {
        layout: vertical;
        height: auto;
        overflow: hidden;
    }
    CopyableMarkdownFence > .fence-header {
        width: 100%;
        height: 1;
        background: $panel;
    }
    CopyableMarkdownFence .fence-lang {
        width: 1fr;
        height: 1;
        padding: 0 1;
        color: $text-muted;
        text-style: dim;
    }
    CopyableMarkdownFence .fence-copy {
        width: auto;
        height: 1;
        padding: 0 1;
        color: $text-muted;
    }
    CopyableMarkdownFence .fence-copy:hover {
        color: $text;
        background: $primary 30%;
        text-style: bold;
    }
    CopyableMarkdownFence > .fence-body {
        width: 1fr;
        height: auto;
        overflow-x: auto;
        overflow-y: hidden;
        scrollbar-size-horizontal: 0;
    }
    CopyableMarkdownFence #code-content {
        width: auto;
        padding: 1 2;
    }
    """

    def _lang_label(self) -> str:
        """Human-facing language label for the header (never empty)."""
        return (self.lexer or "").strip() or "text"

    def compose(self) -> ComposeResult:
        with Horizontal(classes="fence-header"):
            yield Static(self._lang_label(), classes="fence-lang")
            yield Button("⧉ Copy", classes="fence-copy")
        # Keep the code in its own horizontal-scroll region so long lines
        # scroll independently and the header bar stays pinned. ``set_content``
        # (called by the parent during streaming) locates the Label by id, so
        # nesting it here is safe.
        with HorizontalScroll(classes="fence-body"):
            yield Label(self._highlighted_code, id="code-content")

    async def _update_from_block(self, block: MarkdownBlock) -> None:
        # Parent refreshes the highlighted Label content + lexer/token; it does
        # NOT touch ``self.code``, so a fence updated mid-stream would otherwise
        # keep copying its first-seen source. Refresh both here.
        await super()._update_from_block(block)
        if isinstance(block, MarkdownFence):
            self.code = block.code
            try:
                self.query_one(".fence-lang", Static).update(self._lang_label())
            except Exception:
                # Header not mounted yet (update raced compose); the label will
                # render from the refreshed lexer on first mount.
                pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        # Only the header Copy button lives inside a fence, so any press here is
        # a copy request. Stop it so it doesn't bubble to message-level handlers.
        event.stop()
        self._copy_code()

    def _copy_code(self) -> None:
        code = self.code or ""
        try:
            # ``App.copy_to_clipboard`` (overridden by ChatApp for OSC-52 +
            # platform fallbacks) is always present on the running app.
            self.app.copy_to_clipboard(code)
            self.app.notify("Copied to clipboard")
        except Exception:
            log.exception("Failed to copy code block to clipboard")
            self.app.notify("Copy failed", severity="error")


class SafeMarkdown(Markdown):
    """Markdown subclass with ``open_links`` defaulted to ``False``.

    Callers may still pass ``open_links=True`` explicitly if they want
    the default Textual behavior (e.g. a future controlled-environment
    use case where blocking is acceptable). The default-off posture is
    what protects every existing call site.

    Also routes code-fence blocks to :class:`CopyableMarkdownFence` so
    every fenced/indented code block gets a one-click Copy button.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("open_links", False)
        super().__init__(*args, **kwargs)

    def get_block_class(self, block_name: str) -> type[MarkdownBlock]:
        if block_name in ("fence", "code_block"):
            # Lazy import matches message.py -- avoids importing CONFIG at
            # module load and honors edits made via /settings without restart
            # (applies to code blocks rendered after the toggle changes).
            from claudechic.config import CONFIG

            if CONFIG.get("code_copy_button", True):
                return CopyableMarkdownFence
        return super().get_block_class(block_name)
