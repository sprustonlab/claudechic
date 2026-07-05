"""Guards panel widget for displaying guardrail rules in the sidebar.

Shows every guardrail RULE (injections excluded) with a tri-state ASCII
marker and lets the user toggle per-agent runtime overrides by clicking:

    [x]  active     (would fire naturally)
    [x]* forced on  (user override: fires despite workflow/role/phase)
    [ ]* forced off (user override: suppressed despite matching scope)
    [.]  dormant    (workflow/role/phase mismatch or disabled)

Click semantics are handled by the app (ChatApp.on_guard_item_toggled):
an existing override is cleared; otherwise the opposite of the natural
state is set (active -> "off", dormant -> "on").
"""

from __future__ import annotations

from dataclasses import dataclass

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Static


@dataclass(frozen=True)
class GuardRow:
    """Display model for one guardrail rule."""

    rule_id: str  # fully qualified (e.g. "global:no_rm_rf")
    display_id: str  # "global:" prefix stripped; workflow prefix kept
    enforcement: str  # "deny" | "warn" | "log"
    state: str  # "active" | "forced_on" | "forced_off" | "dormant"
    message: str  # rule message (tooltip)


# state -> (marker, style)
_STATE_MARKERS: dict[str, tuple[str, str]] = {
    "active": ("[x] ", "green"),
    "forced_on": ("[x]*", "yellow"),
    "forced_off": ("[ ]*", "yellow"),
    "dormant": ("[.] ", "dim"),
}


class GuardItem(Static):
    """Single guard row: state marker, rule id, enforcement level."""

    DEFAULT_CSS = """
    GuardItem {
        height: 1;
        pointer: pointer;
    }
    GuardItem:hover {
        background: $panel;
    }
    """

    can_focus = True

    class Toggled(Message):
        """Posted when a guard row is clicked (user wants to toggle it)."""

        def __init__(self, row: GuardRow) -> None:
            self.row = row
            super().__init__()

    # Fallback front-truncation budget for rule ids, used before the widget
    # has been laid out (content_size unknown). Once a width is known, the
    # budget adapts to it so a wider sidebar shows more of the id. Rows are
    # height 1; without truncation a long id word-wraps onto a clipped second
    # line and the visible row shows only the marker.
    max_id_length = 18
    # Never truncate below this many chars (keeps ".." + a few chars readable).
    min_id_length = 6

    def __init__(self, row: GuardRow) -> None:
        super().__init__()
        self.row = row
        self.tooltip = row.message

    def _truncate_front(self, name: str, budget: int) -> str:
        """Truncate from the front (the trailing rule name disambiguates)."""
        if len(name) > budget:
            return ".." + name[-(budget - 2) :]
        return name

    def _id_budget(self) -> int:
        """Chars available for the rule id, derived from the rendered width.

        Width is shared between the state marker (marker + separator space),
        the id, and the trailing ``" (enforcement)"`` suffix. Falls back to
        ``max_id_length`` before the widget has a known content width.
        """
        marker = _STATE_MARKERS.get(self.row.state, ("[?] ", "dim"))[0]
        overhead = len(marker) + 1 + len(f" ({self.row.enforcement})")
        avail = self.content_size.width
        if avail <= 0:
            return self.max_id_length
        return max(self.min_id_length, avail - overhead)

    def render(self) -> Text:
        marker, style = _STATE_MARKERS.get(self.row.state, ("[?] ", "dim"))
        id_style = "dim" if self.row.state == "dormant" else ""
        text = Text.assemble(
            (marker + " ", style),
            (self._truncate_front(self.row.display_id, self._id_budget()), id_style),
            (f" ({self.row.enforcement})", "dim"),
        )
        text.no_wrap = True
        text.overflow = "ellipsis"
        return text

    def on_resize(self, event) -> None:  # noqa: ARG002
        # Re-render so the id truncation budget tracks the sidebar width
        # (the panel grows into unused horizontal space).
        self.refresh()

    def on_click(self, event) -> None:  # noqa: ARG002
        self.post_message(self.Toggled(self.row))


class GuardsPanel(Widget):
    """Sidebar panel listing guardrail rules with per-agent toggle state."""

    DEFAULT_CSS = """
    GuardsPanel {
        width: 100%;
        height: auto;
        border-top: solid $panel;
        padding: 1;
    }
    GuardsPanel.hidden {
        display: none;
    }
    GuardsPanel .guards-title {
        color: $text-muted;
        text-style: bold;
        padding: 0 0 1 0;
    }
    GuardsPanel #guards-scroll {
        /* height: auto -- NOT the Textual default 1fr. Same rationale as
           FilesSection #files-scroll: 1fr would try to fill the parent's
           allocated space, but GuardsPanel itself is height: auto, so the
           1fr child gets undefined space and can collapse to 0. auto sizes
           to the mounted GuardItem children (height: 1 each). max-height
           is set dynamically by _layout_sidebar_contents(). */
        height: auto;
    }
    """

    can_focus = False

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._rows: list[GuardRow] = []
        self._scroll: VerticalScroll | None = None

    @property
    def guard_count(self) -> int:
        """Number of guard rows currently displayed."""
        return len(self._rows)

    def compose(self) -> ComposeResult:
        yield Static("Guards", classes="guards-title")
        yield VerticalScroll(id="guards-scroll")

    def _get_scroll(self) -> VerticalScroll:
        """Return the scroll container, caching the reference."""
        if self._scroll is None:
            self._scroll = self.query_one("#guards-scroll", VerticalScroll)
        return self._scroll

    def set_visible(self, visible: bool) -> None:
        """Control visibility (only shows if it has rows and visible=True)."""
        if visible and self._rows:
            self.remove_class("hidden")
        else:
            self.add_class("hidden")

    def update_guards(self, rows: list[GuardRow]) -> None:
        """Replace guard rows. Active/forced rows sort first, dormant last."""

        def sort_key(row: GuardRow) -> tuple[int, str]:
            group = 1 if row.state == "dormant" else 0
            return (group, row.display_id)

        self._rows = sorted(rows, key=sort_key)
        for item in self.query(GuardItem):
            item.remove()
        scroll = self._get_scroll()
        scroll.mount(*[GuardItem(row) for row in self._rows])
