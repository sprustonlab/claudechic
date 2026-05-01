"""InfoModal base class - reusable modal for displaying labeled info sections."""

from __future__ import annotations

from dataclasses import dataclass

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Static


@dataclass(frozen=True)
class InfoSection:
    """A single section of information to display in an InfoModal."""

    title: str
    content: str
    copyable: bool = True
    scrollable: bool = False


class InfoModal(ModalScreen):
    """Base modal for displaying labeled info sections.

    Subclasses should override ``_get_title()`` and ``_get_sections()``
    to supply data.  The base class handles rendering, copy buttons,
    and dismiss behaviour.
    """

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
    ]

    DEFAULT_CSS = """
    InfoModal {
        align: center middle;
    }

    InfoModal #info-container {
        width: auto;
        min-width: 40;
        max-width: 60;
        height: auto;
        max-height: 80%;
        background: $surface;
        border: solid $panel;
        padding: 1 2;
    }

    InfoModal #info-header {
        height: 1;
        margin-bottom: 1;
    }

    InfoModal #info-title {
        width: 1fr;
    }

    InfoModal .info-row {
        height: 1;
    }

    InfoModal .info-label {
        width: 14;
        color: $text-muted;
    }

    InfoModal .info-value {
        width: 1fr;
    }

    InfoModal .scroll-section-header {
        height: 1;
        margin-top: 1;
    }

    InfoModal .scroll-section-title {
        width: 1fr;
        color: $text-muted;
    }

    InfoModal .scroll-section-scroll {
        max-height: 12;
        height: auto;
        padding: 0 0 0 1;
    }

    InfoModal .scroll-section-content {
        height: auto;
        color: $text-muted;
    }

    InfoModal #info-footer {
        height: 1;
        margin-top: 1;
        align: center middle;
    }

    InfoModal .copy-btn {
        width: 8;
        min-width: 8;
        height: 1;
        padding: 0 1;
        margin: 0 1;
        background: transparent;
        border: none;
        color: $text-muted;
    }

    InfoModal .copy-btn:hover {
        color: $primary;
        background: transparent;
    }

    InfoModal #close-btn {
        min-width: 10;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._sections: list[InfoSection] = []

    def _get_title(self) -> str:
        """Return the modal title. Override in subclasses."""
        return "Info"

    def _get_sections(self) -> list[InfoSection]:
        """Return the sections to display. Override in subclasses."""
        return []

    def compose(self) -> ComposeResult:
        self._sections = self._get_sections()
        with Vertical(id="info-container"):
            with Horizontal(id="info-header"):
                yield Static(
                    f"[bold]{self._get_title()}[/]",
                    id="info-title",
                    markup=True,
                )
            for i, section in enumerate(self._sections):
                if section.scrollable:
                    with Horizontal(classes="scroll-section-header"):
                        yield Static(
                            f"[bold]{section.title}[/]",
                            classes="scroll-section-title",
                            markup=True,
                        )
                        if section.copyable:
                            yield Button(
                                "⧉",
                                id=f"copy-scroll-{i}",
                                classes="copy-btn",
                            )
                    if section.content:
                        with VerticalScroll(classes="scroll-section-scroll"):
                            yield Static(
                                section.content,
                                classes="scroll-section-content",
                            )
                    else:
                        yield Static(
                            "(none)",
                            classes="scroll-section-content",
                        )
                else:
                    with Horizontal(classes="info-row"):
                        yield Static(f"{section.title}:", classes="info-label")
                        yield Static(section.content, classes="info-value")
            with Horizontal(id="info-footer"):
                yield Button("Copy", id="copy-all-btn", classes="copy-btn")
                yield Button("Close", id="close-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "copy-all-btn":
            self._copy_all()
        elif event.button.id == "close-btn":
            self.dismiss()
        elif event.button.id and event.button.id.startswith("copy-scroll-"):
            idx = int(event.button.id.split("-")[-1])
            if 0 <= idx < len(self._sections) and self._sections[idx].content:
                self._copy_to_clipboard(self._sections[idx].content)
            else:
                self.notify("Nothing to copy", severity="warning")

    def _copy_all(self) -> None:
        """Copy all section content to clipboard."""
        lines = []
        for section in self._sections:
            if section.copyable:
                lines.append(f"{section.title}: {section.content}")
        text = "\n".join(lines)
        self._copy_to_clipboard(text)

    def _copy_to_clipboard(self, text: str) -> None:
        """Copy text to clipboard with notification."""
        try:
            import pyperclip

            pyperclip.copy(text)
            self.notify("Copied to clipboard")
        except Exception as e:
            self.notify(f"Copy failed: {e}", severity="error")
