"""DisabledWorkflowsScreen — per-(level, id) toggle subscreen.

Consumes ``LoadResult.workflow_provenance`` (per SPEC §3.5 + Group C) and
the current ``app._project_config.disabled_workflows`` set, and lets the
user toggle disable per ``(tier, workflow_id)`` tuple. Saves an encoded
``frozenset[str]`` of ``<tier>:<id>`` and bare ``<id>`` entries per the
SPEC §3.6 schema (collapse-to-bare when every tier-instance of an id is
disabled, expand-from-bare when any single tier is unchecked).

Returns ``frozenset[str]`` on Enter / ``None`` on Esc.

User-facing language uses **"level"** rather than **"tier"** (per
SPEC §7.11 + §0.2 vocabulary).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Label, ListItem, ListView, Static

if TYPE_CHECKING:
    from claudechic.app import ChatApp

log = logging.getLogger(__name__)


_TIER_BADGE = {
    "package": "[pkg]",
    "user": "[user]",
    "project": "[proj]",
}

# Display priority — highest priority first.
_TIER_ORDER = ("project", "user", "package")


class _TierIdItem(ListItem):
    """One toggleable ``(tier, id)`` row."""

    DEFAULT_CSS = """
    _TierIdItem {
        height: auto;
        padding: 0 0 0 1;
    }
    """

    def __init__(
        self,
        wf_id: str,
        tier: str,
        checked: bool,
        annotation: str = "",
    ) -> None:
        super().__init__()
        self.wf_id = wf_id
        self.tier = tier
        self.checked = checked
        self._annotation = annotation

    def compose(self) -> ComposeResult:
        yield Label(self._render_text(), markup=False)

    def _render_text(self) -> str:
        mark = "[x]" if self.checked else "[ ]"
        badge = _TIER_BADGE.get(self.tier, f"[{self.tier}]")
        suffix = f"  {self._annotation}" if self._annotation else ""
        return f"{mark} {self.wf_id}    {badge}{suffix}"

    def toggle(self) -> None:
        self.checked = not self.checked
        # Re-render in place.
        try:
            self.query_one(Label).update(self._render_text())
        except Exception as e:
            # Defensive — widget may not be fully mounted yet.
            log.debug("toggle re-render failed: %s", e)


class DisabledWorkflowsScreen(Screen[frozenset[str] | None]):
    """Multi-select subscreen for ``project_config.disabled_workflows``.

    One row per ``(tier, workflow_id)`` tuple from the loader's
    ``workflow_provenance`` map. Space toggles disable on the highlighted
    row. Enter accepts (dismisses with the encoded set). Esc cancels.
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "accept", "Accept"),
        Binding("space", "toggle_row", "Toggle", priority=True),
    ]

    DEFAULT_CSS = """
    DisabledWorkflowsScreen {
        background: $background;
        align: center top;
    }
    DisabledWorkflowsScreen #disabled-wf-container {
        width: 100%;
        max-width: 90;
        height: 100%;
        padding: 1 2;
    }
    DisabledWorkflowsScreen #disabled-wf-title {
        height: 1;
        text-style: bold;
    }
    DisabledWorkflowsScreen #disabled-wf-helper {
        height: auto;
        margin-bottom: 1;
        color: $text-muted;
    }
    DisabledWorkflowsScreen #disabled-wf-list,
    DisabledWorkflowsScreen #disabled-wf-list:focus {
        height: 1fr;
        background: transparent;
    }
    DisabledWorkflowsScreen #disabled-wf-list > ListItem {
        padding: 0 0 0 1;
        border-left: tall $panel;
    }
    DisabledWorkflowsScreen #disabled-wf-list > ListItem:hover,
    DisabledWorkflowsScreen #disabled-wf-list > ListItem.-highlight {
        background: $surface-darken-1;
        border-left: tall $primary;
    }
    DisabledWorkflowsScreen #disabled-wf-footer {
        height: 1;
        color: $text-muted;
        margin-top: 1;
    }
    """

    HELPER_TEXT = (
        "Disabling a workflow by ID hides it from this project "
        "regardless of which level (package / user / project) defines it."
    )

    def __init__(self, app: ChatApp) -> None:
        super().__init__()
        self._chat_app = app

    def compose(self) -> ComposeResult:
        with Vertical(id="disabled-wf-container"):
            yield Static("Disabled workflows", id="disabled-wf-title")
            yield Static(self.HELPER_TEXT, id="disabled-wf-helper")
            with VerticalScroll():
                yield ListView(id="disabled-wf-list")
            yield Static(
                "space toggle  ·  enter accept  ·  esc cancel",
                id="disabled-wf-footer",
            )

    def on_mount(self) -> None:
        self._populate_list()
        lv = self.query_one("#disabled-wf-list", ListView)
        lv.focus()

    # -- list build --------------------------------------------------------

    def _populate_list(self) -> None:
        lv = self.query_one("#disabled-wf-list", ListView)
        lv.clear()

        provenance = self._workflow_provenance()
        winning = self._winning_tiers()
        disabled_set = self._initial_disabled_set()

        # Sort: workflow_id alphabetic, then by display tier order
        # (project > user > package).
        sorted_ids = sorted(provenance.keys())
        for wf_id in sorted_ids:
            tiers = sorted(
                provenance[wf_id],
                key=lambda t: _TIER_ORDER.index(t) if t in _TIER_ORDER else 99,
            )
            for tier in tiers:
                checked = (tier, wf_id) in disabled_set or (
                    "*",
                    wf_id,
                ) in disabled_set
                annotation = self._annotate(tier, wf_id, winning)
                lv.append(_TierIdItem(wf_id, tier, checked, annotation))

        if lv.children:
            lv.index = 0

    def _annotate(self, tier: str, wf_id: str, winning: dict[str, str]) -> str:
        """Return a tier-context annotation per SPEC §7.6."""
        win = winning.get(wf_id)
        if win is None or tier == win:
            return ""
        return (
            f"(override of {win})" if _is_lower(tier, win) else f"(overridden by {win})"
        )

    # -- read app state ---------------------------------------------------

    def _workflow_provenance(self) -> dict[str, frozenset[str]]:
        load_result = getattr(self._chat_app, "_load_result", None)
        if load_result is None:
            return {}
        return getattr(load_result, "workflow_provenance", {}) or {}

    def _winning_tiers(self) -> dict[str, str]:
        load_result = getattr(self._chat_app, "_load_result", None)
        if load_result is None:
            return {}
        wfs = getattr(load_result, "workflows", {}) or {}
        return {wf_id: wf.tier for wf_id, wf in wfs.items() if hasattr(wf, "tier")}

    def _initial_disabled_set(self) -> set[tuple[str, str]]:
        """Decode current ``disabled_workflows`` into ``(tier_or_*, id)`` tuples."""
        pc = getattr(self._chat_app, "_project_config", None)
        if pc is None:
            return set()
        raw: frozenset[str] = getattr(pc, "disabled_workflows", frozenset())
        out: set[tuple[str, str]] = set()
        for entry in raw:
            tier, wf_id = _split_entry(entry)
            out.add((tier, wf_id))
        return out

    # -- key actions -------------------------------------------------------

    def action_toggle_row(self) -> None:
        lv = self.query_one("#disabled-wf-list", ListView)
        item = lv.highlighted_child
        if isinstance(item, _TierIdItem):
            item.toggle()
        else:
            log.debug(
                "action_toggle_row: highlighted_child is %r, not _TierIdItem",
                type(item).__name__ if item is not None else None,
            )

    def action_accept(self) -> None:
        self.dismiss(self._encode_result())

    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Enter on the list — accept current selection (per SPEC §7.12)."""
        # Dismiss with the encoded result.
        self.dismiss(self._encode_result())

    # -- encoding ---------------------------------------------------------

    def _encode_result(self) -> frozenset[str]:
        lv = self.query_one("#disabled-wf-list", ListView)
        rows: list[tuple[str, str, bool]] = []
        for child in lv.children:
            if isinstance(child, _TierIdItem):
                rows.append((child.tier, child.wf_id, child.checked))
        return encode_disabled_set(rows)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def encode_disabled_set(rows: list[tuple[str, str, bool]]) -> frozenset[str]:
    """Encode ``[(tier, id, checked), ...]`` rows into a save-ready set.

    Per SPEC §7.6: tier-targeted entries write ``<tier>:<id>``; if every
    tier-instance of the same id is disabled, the encoder collapses to a
    bare ``<id>``. Untouched ids contribute no entries.
    """
    out: set[str] = set()
    by_id: dict[str, list[tuple[str, bool]]] = {}
    for tier, wf_id, checked in rows:
        by_id.setdefault(wf_id, []).append((tier, checked))

    for wf_id, items in by_id.items():
        all_disabled = all(c for _, c in items)
        none_disabled = not any(c for _, c in items)
        if none_disabled:
            continue
        if all_disabled:
            out.add(wf_id)
            continue
        for tier, checked in items:
            if checked:
                out.add(f"{tier}:{wf_id}")
    return frozenset(out)


def _split_entry(entry: str) -> tuple[str, str]:
    """Parse a ``disabled_workflows`` entry into ``(tier, id)``.

    Bare entries (no ``<tier>:`` prefix or unknown prefix) return
    ``("*", entry)`` to mean "applies to all tiers".
    """
    if ":" not in entry:
        return "*", entry
    head, rest = entry.split(":", 1)
    if head in ("package", "user", "project"):
        return head, rest
    return "*", entry


_PRIORITY = {"project": 2, "user": 1, "package": 0}


def _is_lower(tier: str, other: str) -> bool:
    return _PRIORITY.get(tier, -1) < _PRIORITY.get(other, -1)


__all__ = ["DisabledWorkflowsScreen", "encode_disabled_set"]
