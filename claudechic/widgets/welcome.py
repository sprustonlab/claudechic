"""Welcome screen widget for onboarding checklist.

Renders a checklist of setup facets with live status. Configured items show
a checkmark; unconfigured items are selectable and activate the corresponding
facet workflow.
"""

from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.message import Message
from textual.widgets import Static

from claudechic.onboarding import FacetStatus


class WelcomeScreen(Static):
    """Onboarding checklist shown at session start when setup is incomplete."""

    can_focus = True

    DEFAULT_CSS = """
    WelcomeScreen {
        dock: top;
        width: 100%;
        padding: 1 2;
        margin: 0 0 1 0;
        border: solid $accent;
    }
    """

    BINDINGS = [
        Binding("up", "cursor_up", "Up", show=False),
        Binding("down", "cursor_down", "Down", show=False),
        Binding("enter", "select", "Select", show=False),
        Binding("s", "skip", "Skip", show=False),
        Binding("d", "dismiss", "Don't show again", show=False),
        Binding("escape", "skip", "Skip", show=False),
    ]

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
        # Build list of selectable (unconfigured) indices
        self._selectable_indices = [
            i for i, f in enumerate(facets) if not f.configured
        ]
        self._cursor = 0  # Index into _selectable_indices

    def compose(self) -> ComposeResult:
        with Vertical(id="welcome-panel"):
            yield Static(
                Text("Your project is ready! A few things to finish setting up:\n", style="bold"),
                id="welcome-title",
            )
            for i, facet in enumerate(self.facets):
                yield _FacetItem(facet, index=i)
            yield Static("")  # spacer
            yield Static(
                Text.from_markup(
                    "Select an unconfigured item to set it up,\n"
                    "or press [bold]s[/bold] to skip, "
                    "[bold]d[/bold] to dismiss permanently."
                ),
                id="welcome-instructions",
            )

    def on_mount(self) -> None:
        """Focus self and highlight first selectable item.

        Respects steal_focus: if False (user already typing), don't grab focus
        — the user can click or tab into the welcome screen instead.
        """
        if self._steal_focus:
            self.focus()
        self._update_highlight()

    def _update_highlight(self) -> None:
        """Update visual highlight on the currently selected facet item."""
        for child in self.query(_FacetItem):
            child.remove_class("welcome-highlighted")
        if self._selectable_indices and 0 <= self._cursor < len(self._selectable_indices):
            idx = self._selectable_indices[self._cursor]
            items = list(self.query(_FacetItem))
            if idx < len(items):
                items[idx].add_class("welcome-highlighted")

    def action_cursor_up(self) -> None:
        if self._selectable_indices and self._cursor > 0:
            self._cursor -= 1
            self._update_highlight()

    def action_cursor_down(self) -> None:
        if self._selectable_indices and self._cursor < len(self._selectable_indices) - 1:
            self._cursor += 1
            self._update_highlight()

    def action_select(self) -> None:
        if self._selectable_indices:
            idx = self._selectable_indices[self._cursor]
            self.post_message(self.Selected(self.facets[idx].workflow_id))
            self.remove()

    def action_skip(self) -> None:
        self.post_message(self.Skipped())
        self.remove()

    def action_dismiss(self) -> None:
        self.post_message(self.Dismissed())
        self.remove()


class _FacetItem(Static):
    """Single facet row in the welcome screen checklist."""

    can_focus = False

    DEFAULT_CSS = """
    _FacetItem {
        height: 1;
        padding: 0 1;
    }
    _FacetItem.welcome-highlighted {
        background: $accent 20%;
    }
    _FacetItem:hover {
        background: $surface-lighten-1;
    }
    """

    def __init__(self, facet: FacetStatus, index: int) -> None:
        super().__init__()
        self.facet = facet
        self._index = index

    def render(self) -> Text:
        result = Text()
        if self.facet.configured:
            result.append("  ✔ ", style="green bold")
            result.append(self.facet.label, style="green")
            result.append(f"  — {self.facet.detail}", style="dim")
        else:
            result.append("  ○ ", style="yellow")
            result.append(self.facet.label, style="yellow bold")
            result.append(f"  — {self.facet.detail}", style="dim")
        return result

    def on_click(self) -> None:
        """Allow clicking unconfigured items to select them."""
        if not self.facet.configured:
            parent = self.ancestors_with_self
            for ancestor in parent:
                if isinstance(ancestor, WelcomeScreen):
                    ancestor.post_message(WelcomeScreen.Selected(self.facet.workflow_id))
                    ancestor.remove()
                    break
