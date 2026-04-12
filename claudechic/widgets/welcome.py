"""Welcome screen widget for onboarding checklist.

Renders a checklist of setup facets with live status. Configured items show
a checkmark; unconfigured items are numbered and clickable to activate the
corresponding facet workflow. Follows the SelectionPrompt / BasePrompt
pattern from widgets/prompts.py.
"""

from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.message import Message
from textual.widgets import Static

from claudechic.onboarding import FacetStatus


class WelcomeScreen(Static):
    """Onboarding checklist shown at session start when setup is incomplete.

    Unconfigured facets are numbered options (clickable, keyboard-navigable).
    Skip and Dismiss are visible buttons at the bottom.
    """

    can_focus = True

    DEFAULT_CSS = """
    WelcomeScreen {
        height: auto;
        width: 100%;
        max-width: 90;
        background: $surface;
        border-left: tall $primary;
        padding: 1 2 1 1;
    }
    """

    # --- Messages posted to the app ---

    class Selected(Message):
        """User selected an unconfigured facet to set up."""

        def __init__(self, workflow_id: str) -> None:
            self.workflow_id = workflow_id
            super().__init__()

    class Skipped(Message):
        """User chose to skip onboarding for this session."""

    class Dismissed(Message):
        """User chose to permanently dismiss onboarding."""

    def __init__(self, facets: list[FacetStatus], steal_focus: bool = True) -> None:
        super().__init__()
        self.facets = facets
        self._steal_focus = steal_focus
        # Build ordered list of selectable (unconfigured) facet indices
        self._selectable_indices = [i for i, f in enumerate(facets) if not f.configured]
        # Options: unconfigured facets + Skip + Dismiss
        self._num_options = len(self._selectable_indices) + 2
        self._skip_idx = len(self._selectable_indices)
        self._dismiss_idx = len(self._selectable_indices) + 1
        self.selected_idx = 0

    def compose(self) -> ComposeResult:
        yield Static(
            Text(
                "Your project is ready! A few things to finish setting up:\n",
                style="bold",
            ),
            classes="prompt-title",
        )
        # Configured items (not selectable, just status)
        for _i, facet in enumerate(self.facets):
            if facet.configured:
                yield _ConfiguredItem(facet)

        # Unconfigured items as numbered options
        opt_num = 0
        for facet_idx in self._selectable_indices:
            facet = self.facets[facet_idx]
            classes = "prompt-option selected" if opt_num == 0 else "prompt-option"
            yield Static(
                f"{opt_num + 1}. {facet.label}  — {facet.detail}",
                classes=classes,
                id=f"opt-{opt_num}",
            )
            opt_num += 1

        # Spacer
        yield Static("")

        # Skip and Dismiss as numbered options
        skip_classes = "prompt-option"
        yield Static(
            f"{opt_num + 1}. Skip (show again next session)",
            classes=skip_classes,
            id=f"opt-{self._skip_idx}",
        )
        dismiss_classes = "prompt-option"
        yield Static(
            f"{opt_num + 2}. Dismiss permanently",
            classes=dismiss_classes,
            id=f"opt-{self._dismiss_idx}",
        )

    def on_mount(self) -> None:
        """Focus self to capture keyboard input."""
        if self._steal_focus:
            self.focus()

    def _update_selection(self) -> None:
        """Update visual selection state across all options."""
        for i in range(self._num_options):
            opt = self.query_one_optional(f"#opt-{i}", Static)
            if opt is not None:
                if i == self.selected_idx:
                    opt.add_class("selected")
                else:
                    opt.remove_class("selected")

    def _select_option(self, idx: int) -> None:
        """Handle selection of option at index."""
        if idx == self._skip_idx:
            self.post_message(self.Skipped())
            self.remove()
        elif idx == self._dismiss_idx:
            self.post_message(self.Dismissed())
            self.remove()
        elif 0 <= idx < len(self._selectable_indices):
            facet_idx = self._selectable_indices[idx]
            self.post_message(self.Selected(self.facets[facet_idx].workflow_id))
            self.remove()

    def on_click(self, event) -> None:
        """Handle clicks on option items."""
        for i in range(self._num_options):
            opt = self.query_one_optional(f"#opt-{i}", Static)
            if opt is not None and opt is event.widget:
                self._select_option(i)
                return

    def on_key(self, event) -> None:
        """Handle keyboard navigation — same pattern as SelectionPrompt."""
        if event.key == "up":
            self.selected_idx = (self.selected_idx - 1) % self._num_options
            self._update_selection()
            event.prevent_default()
            event.stop()
        elif event.key == "down":
            self.selected_idx = (self.selected_idx + 1) % self._num_options
            self._update_selection()
            event.prevent_default()
            event.stop()
        elif event.key == "enter":
            self._select_option(self.selected_idx)
            event.prevent_default()
            event.stop()
        elif event.key == "escape":
            self.post_message(self.Skipped())
            self.remove()
            event.prevent_default()
            event.stop()
        elif event.key.isdigit():
            idx = int(event.key) - 1
            if 0 <= idx < self._num_options:
                self._select_option(idx)
                event.prevent_default()
                event.stop()


class _ConfiguredItem(Static):
    """Non-selectable row showing a configured facet with checkmark."""

    can_focus = False

    DEFAULT_CSS = """
    _ConfiguredItem {
        height: 1;
        padding: 0 0 0 1;
        color: $text-muted;
    }
    """

    def __init__(self, facet: FacetStatus) -> None:
        super().__init__()
        self.facet = facet

    def render(self) -> Text:
        result = Text()
        result.append("✔ ", style="green bold")
        result.append(self.facet.label, style="green")
        result.append(f"  — {self.facet.detail}", style="dim")
        return result
