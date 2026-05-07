"""Markdown preview widgets for diff screen and sidebar."""

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Static

from claudechic.widgets.content.safe_markdown import SafeMarkdown as Markdown

# ``Markdown`` above is ``SafeMarkdown`` (no synchronous link-open
# freeze). See widgets/content/safe_markdown.py for rationale.


class PreviewToggle(Static):
    """Toggle button: switches between diff hunks and rendered markdown."""

    can_focus = False

    DEFAULT_CSS = """
    PreviewToggle {
        width: auto;
        height: 1;
        padding: 0 1;
        color: $secondary;
        text-style: bold;
    }
    PreviewToggle:hover {
        color: $primary;
        background: $panel;
        text-style: bold underline;
    }
    """

    class Toggled(Message):
        """Posted when toggle is clicked."""

        def __init__(self, path: str, show_preview: bool) -> None:
            self.path = path
            self.show_preview = show_preview
            super().__init__()

    def __init__(self, path: str, **kwargs) -> None:
        # Use \[ to escape brackets so Rich treats them as literal characters,
        # not markup tags. Without escaping, [Preview] is consumed as an unknown
        # Rich tag and renders as empty string (width=0).
        super().__init__(r"\[Preview]", **kwargs)
        self._path = path
        self._preview_active = False

    def on_click(self, event) -> None:
        event.stop()
        self._preview_active = not self._preview_active
        label = r"\[Diff]" if self._preview_active else r"\[Preview]"
        self.update(label)
        self.post_message(self.Toggled(self._path, self._preview_active))


MAX_PREVIEW_SIZE = 50 * 1024  # 50KB


class MarkdownPreviewModal(ModalScreen):
    """Standalone modal for viewing .md files from the sidebar."""

    DEFAULT_CSS = """
    MarkdownPreviewModal {
        align: center middle;
    }
    MarkdownPreviewModal #md-modal-container {
        width: 80%;
        max-width: 100;
        height: 80%;
        background: $surface;
        border: round $primary;
        padding: 1 2;
    }
    MarkdownPreviewModal #md-modal-title {
        text-style: bold;
        margin-bottom: 1;
    }
    MarkdownPreviewModal #md-modal-close {
        dock: bottom;
        width: 100%;
        height: 1;
        content-align: center middle;
        color: $text-muted;
    }
    MarkdownPreviewModal #md-modal-close:hover {
        color: $primary;
    }
    """

    BINDINGS = [("escape", "dismiss", "Close")]

    def __init__(self, file_path: Path, cwd: Path, **kwargs) -> None:
        super().__init__(**kwargs)
        self._file_path = file_path
        self._cwd = cwd

    def compose(self) -> ComposeResult:
        yield Static(str(self._file_path), id="md-modal-title")
        full_path = self._cwd / self._file_path
        try:
            if full_path.stat().st_size > MAX_PREVIEW_SIZE:
                yield Static("File too large for preview (> 50KB)")
            else:
                content = full_path.read_text(encoding="utf-8")
                if not content.strip():
                    yield Static("(empty file)")
                else:
                    with VerticalScroll():
                        yield Markdown(content)
        except FileNotFoundError:
            yield Static("File not found")
        except UnicodeDecodeError:
            yield Static("Cannot preview file")
        # Use r"\[Close]" -- bare "[Close]" is consumed as a Rich markup tag
        # and renders as empty string, making the close button invisible.
        yield Static(r"\[Close]", id="md-modal-close")

    def on_click(self, event) -> None:
        if (
            hasattr(event, "widget")
            and event.widget
            and getattr(event.widget, "id", None) == "md-modal-close"
        ):
            self.dismiss()
