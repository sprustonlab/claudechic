"""Welcome screen shown on first install when setup is incomplete.

Read-only screen -- NEVER writes files or creates directories.
Dismissal persistence is handled by the caller (app.py) via HintStateStore.
"""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Label, ListItem, ListView, Static

from claudechic.onboarding import FacetStatus

# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

RESULT_DISMISS = "dismiss"
RESULT_TUTORIAL = "tutorial"
RESULT_PICKER = "picker"
RESULT_SETTINGS = "settings"


# ---------------------------------------------------------------------------
# List items
# ---------------------------------------------------------------------------


class _FacetItem(ListItem):
    """A facet row in the checklist -- configured or unconfigured."""

    DEFAULT_CSS = """
    _FacetItem {
        height: auto;
        padding: 0 0 0 1;
    }
    """

    def __init__(self, facet: FacetStatus) -> None:
        super().__init__(disabled=facet.configured)
        self.facet = facet

    def compose(self) -> ComposeResult:
        mark = "✔" if self.facet.configured else "○"
        style = "dim" if self.facet.configured else ""
        yield Label(f"{mark} {self.facet.label}  — {self.facet.detail}", classes=style)


class _ActionItem(ListItem):
    """A quick-action row at the bottom of the welcome screen."""

    DEFAULT_CSS = """
    _ActionItem {
        height: auto;
        padding: 0 0 0 1;
    }
    """

    def __init__(self, action_id: str, text: str) -> None:
        super().__init__()
        self.action_id = action_id
        self._text = text

    def compose(self) -> ComposeResult:
        yield Label(self._text)


# ---------------------------------------------------------------------------
# WelcomeScreen
# ---------------------------------------------------------------------------


class WelcomeScreen(Screen[str | None]):
    """Full-screen welcome overlay for new installs.

    Shows a health-check checklist, available workflows, and quick actions.
    Returns a result string indicating the user's choice, or None if escaped.

    Result values:
        None        -- escaped (skip for this session)
        "dismiss"   -- permanently dismiss
        "tutorial"  -- start the tutorial workflow
        "picker"    -- open the workflow picker
    """

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
    ]

    DEFAULT_CSS = """
    WelcomeScreen {
        background: $background;
        align: center top;
    }

    WelcomeScreen #welcome-container {
        width: 100%;
        max-width: 80;
        height: 100%;
        padding: 1 2;
    }

    WelcomeScreen #welcome-title {
        height: 1;
        margin-bottom: 1;
        text-style: bold;
    }

    WelcomeScreen #welcome-subtitle {
        height: auto;
        margin-bottom: 1;
        color: $text-muted;
    }

    WelcomeScreen #checklist-header {
        height: 1;
        margin-top: 1;
        text-style: bold;
    }

    WelcomeScreen #actions-header {
        height: 1;
        margin-top: 1;
        text-style: bold;
    }

    WelcomeScreen #welcome-list,
    WelcomeScreen #welcome-list:focus {
        height: 1fr;
        background: transparent;
    }

    WelcomeScreen #welcome-list > ListItem {
        padding: 0 0 0 1;
        height: auto;
        margin: 0 0 0 0;
        border-left: tall $panel;
    }

    WelcomeScreen #welcome-list > ListItem:hover,
    WelcomeScreen #welcome-list > ListItem.-highlight {
        background: $surface-darken-1;
        border-left: tall $primary;
    }

    WelcomeScreen #welcome-list > ListItem.-disabled {
        opacity: 0.6;
    }

    WelcomeScreen .separator {
        height: 1;
        margin: 0;
    }
    """

    def __init__(
        self,
        facets: list[FacetStatus],
        workflows: dict[str, Path] | None = None,
    ) -> None:
        """Initialize the welcome screen.

        Args:
            facets: Health-check results from onboarding.check_onboarding().
            workflows: Available workflow registry (workflow_id -> directory).
        """
        super().__init__()
        self._facets = facets
        self._workflows = workflows or {}

    def compose(self) -> ComposeResult:
        with Vertical(id="welcome-container"):
            yield Static("✦ Welcome", id="welcome-title")
            yield Static(
                "Your project is ready. Here is the setup status:",
                id="welcome-subtitle",
            )

            items: list[ListItem] = []

            # -- Checklist section --
            if self._facets:
                items.append(_make_header_item("━━ Setup checklist ━━"))
                for facet in self._facets:
                    items.append(_FacetItem(facet))

            # -- Separator --
            items.append(_make_separator_item())

            # -- Quick actions --
            items.append(_make_header_item("━━ Quick actions ━━"))

            # Tutorial action (only if tutorial workflow exists)
            if "tutorial" in self._workflows:
                items.append(
                    _ActionItem(RESULT_TUTORIAL, "▸ Start tutorial (/tutorial)")
                )

            items.append(_ActionItem(RESULT_PICKER, "▸ Browse workflows"))
            items.append(_ActionItem(RESULT_SETTINGS, "▸ Settings (/settings)"))
            items.append(_ActionItem(RESULT_DISMISS, "▸ Dismiss permanently"))

            yield ListView(*items, id="welcome-list")

    def on_mount(self) -> None:
        """Focus the list for keyboard navigation."""
        lv = self.query_one("#welcome-list", ListView)
        # Skip to the first selectable (non-disabled, non-header) item
        for i, child in enumerate(lv.children):
            if isinstance(child, ListItem) and not child.disabled:
                lv.index = i
                break
        lv.focus()

    def action_go_back(self) -> None:
        """Escape pressed -- skip for this session."""
        self.dismiss(None)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle selection of a list item."""
        item = event.item
        if isinstance(item, _ActionItem):
            self.dismiss(item.action_id)
        elif isinstance(item, _FacetItem) and not item.facet.configured:
            # Selecting an unconfigured facet activates its setup workflow
            self.dismiss(item.facet.workflow_id)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_header_item(text: str) -> ListItem:
    """Create a disabled ListItem used as a visual section header."""
    item = ListItem(Label(text, classes="bold"), disabled=True)
    return item


def _make_separator_item() -> ListItem:
    """Create a disabled ListItem used as a visual spacer."""
    item = ListItem(Static("", classes="separator"), disabled=True)
    return item
