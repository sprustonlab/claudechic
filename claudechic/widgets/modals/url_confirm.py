"""URLConfirmModal -- ask before opening a URL in the system browser.

Dismisses with ``True`` if the user confirms, ``False`` / ``None``
otherwise. The caller (``ChatApp.on_markdown_link_clicked``) is
responsible for actually launching the browser on confirm; this
modal only collects intent.

Why we need this: Textual's default Markdown link handler calls
``webbrowser.open`` synchronously, which freezes the TUI for several
seconds while the OS spawns a browser. A misclick on a link in chat
output therefore costs visible UI time. ``URLConfirmModal`` makes
misclicks free (cancel is one keypress) and intentional clicks
async-launchable.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static


class URLConfirmModal(ModalScreen[bool | None]):
    """Confirm prompt before opening a URL in the system browser.

    Returns ``True`` on confirm, ``False`` on explicit decline, ``None``
    if the modal is dismissed by other means (e.g. the screen stack
    being torn down). Callers should treat anything that is not
    ``True`` as "do nothing".
    """

    BINDINGS = [
        Binding("escape", "dismiss(False)", "Cancel"),
        Binding("n", "dismiss(False)", "No"),
        Binding("y", "confirm", "Yes"),
        Binding("enter", "confirm", "Open"),
    ]

    DEFAULT_CSS = """
    URLConfirmModal {
        align: center middle;
    }
    URLConfirmModal #url-confirm-container {
        width: 80%;
        max-width: 80;
        height: auto;
        background: $surface;
        border: round $primary;
        padding: 1 2;
    }
    URLConfirmModal .url-confirm-title {
        text-style: bold;
        margin-bottom: 1;
    }
    URLConfirmModal .url-confirm-url {
        color: $accent;
        margin-bottom: 1;
    }
    URLConfirmModal .url-confirm-help {
        color: $text-muted;
        margin-top: 1;
    }
    """

    def __init__(self, url: str) -> None:
        super().__init__()
        self._url = url

    @property
    def url(self) -> str:
        """Expose the URL for tests and external introspection."""
        return self._url

    def compose(self) -> ComposeResult:
        with Vertical(id="url-confirm-container"):
            yield Static("Open URL in browser?", classes="url-confirm-title")
            # Render the URL as plain text -- no markup interpretation, so
            # square brackets in the URL cannot mis-render as Rich tags.
            yield Static(self._url, classes="url-confirm-url", markup=False)
            yield Static(
                "[y / enter] Open    [n / esc] Cancel",
                classes="url-confirm-help",
            )

    def action_confirm(self) -> None:
        self.dismiss(True)
