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
"""

from __future__ import annotations

from typing import Any

from textual.widgets import Markdown


class SafeMarkdown(Markdown):
    """Markdown subclass with ``open_links`` defaulted to ``False``.

    Callers may still pass ``open_links=True`` explicitly if they want
    the default Textual behavior (e.g. a future controlled-environment
    use case where blocking is acceptable). The default-off posture is
    what protects every existing call site.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("open_links", False)
        super().__init__(*args, **kwargs)
