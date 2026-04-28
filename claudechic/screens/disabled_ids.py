"""DisabledIdsScreen — per-(level, id) toggle subscreen for hints + rules.

Consumes ``LoadResult.item_provenance`` (per SPEC §3.5 + Group C) plus
the ``LoadResult.hints`` and ``LoadResult.rules`` lists for category
classification, then lets the user toggle disable per
``(tier, item_id)`` tuple. Item ids use the
``namespace:bare_id`` grammar (e.g., ``global:context-docs-outdated``);
tier-targeted entries are saved as ``<tier>:<namespace>:<bare_id>``.

Returns ``frozenset[str]`` on Enter / ``None`` on Esc.

User-facing language uses **"level"** rather than **"tier"** (per
SPEC §7.11 + §0.2 vocabulary).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Label, ListItem, ListView, Static

if TYPE_CHECKING:
    from claudechic.app import ChatApp


_TIER_BADGE = {
    "package": "[pkg]",
    "user": "[user]",
    "project": "[proj]",
}

_TIER_ORDER = ("project", "user", "package")
_PRIORITY = {"project": 2, "user": 1, "package": 0}


class _IdHeaderItem(ListItem):
    """Disabled ListItem used for category headers."""

    DEFAULT_CSS = """
    _IdHeaderItem {
        height: 1;
        padding: 0 0 0 1;
    }
    """

    def __init__(self, text: str) -> None:
        super().__init__(disabled=True)
        self._text = text

    def compose(self) -> ComposeResult:
        yield Label(self._text, classes="bold")


class _TierIdItem(ListItem):
    """One toggleable ``(tier, item_id)`` row."""

    DEFAULT_CSS = """
    _TierIdItem {
        height: auto;
        padding: 0 0 0 1;
    }
    """

    def __init__(
        self,
        item_id: str,
        tier: str,
        category: str,  # "hint" | "rule"
        checked: bool,
        annotation: str = "",
    ) -> None:
        super().__init__()
        self.item_id = item_id
        self.tier = tier
        self.category = category
        self.checked = checked
        self._annotation = annotation

    def compose(self) -> ComposeResult:
        yield Label(self._render_text())

    def _render_text(self) -> str:
        mark = "[x]" if self.checked else "[ ]"
        badge = _TIER_BADGE.get(self.tier, f"[{self.tier}]")
        suffix = f"  {self._annotation}" if self._annotation else ""
        return f"{mark} {self.item_id}    {badge}{suffix}"

    def toggle(self) -> None:
        self.checked = not self.checked
        try:
            self.query_one(Label).update(self._render_text())
        except Exception:
            pass


class DisabledIdsScreen(Screen[frozenset[str] | None]):
    """Multi-select subscreen for ``project_config.disabled_ids``.

    Two grouped sections (Hints / Guardrail rules), one row per
    ``(tier, item_id)`` tuple from the loader's ``item_provenance``.
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "accept", "Accept"),
        Binding("space", "toggle_row", "Toggle"),
    ]

    DEFAULT_CSS = """
    DisabledIdsScreen {
        background: $background;
        align: center top;
    }
    DisabledIdsScreen #disabled-ids-container {
        width: 100%;
        max-width: 100;
        height: 100%;
        padding: 1 2;
    }
    DisabledIdsScreen #disabled-ids-title {
        height: 1;
        text-style: bold;
    }
    DisabledIdsScreen #disabled-ids-helper {
        height: auto;
        margin-bottom: 1;
        color: $text-muted;
    }
    DisabledIdsScreen #disabled-ids-list,
    DisabledIdsScreen #disabled-ids-list:focus {
        height: 1fr;
        background: transparent;
    }
    DisabledIdsScreen #disabled-ids-list > ListItem {
        padding: 0 0 0 1;
        border-left: tall $panel;
    }
    DisabledIdsScreen #disabled-ids-list > ListItem:hover,
    DisabledIdsScreen #disabled-ids-list > ListItem.-highlight {
        background: $surface-darken-1;
        border-left: tall $primary;
    }
    DisabledIdsScreen #disabled-ids-list > ListItem.-disabled {
        opacity: 0.6;
    }
    DisabledIdsScreen #disabled-ids-footer {
        height: 1;
        color: $text-muted;
        margin-top: 1;
    }
    """

    HELPER_TEXT = (
        "Toggle disable per (level, id). Entries collapse to a bare ID "
        "when every level-instance is disabled."
    )

    def __init__(self, app: ChatApp) -> None:
        super().__init__()
        self._chat_app = app

    def compose(self) -> ComposeResult:
        with Vertical(id="disabled-ids-container"):
            yield Static("Disabled IDs", id="disabled-ids-title")
            yield Static(self.HELPER_TEXT, id="disabled-ids-helper")
            with VerticalScroll():
                yield ListView(id="disabled-ids-list")
            yield Static(
                "space toggle  ·  enter accept  ·  esc cancel",
                id="disabled-ids-footer",
            )

    def on_mount(self) -> None:
        self._populate_list()
        lv = self.query_one("#disabled-ids-list", ListView)
        # Skip headers when focusing.
        for i, child in enumerate(lv.children):
            if isinstance(child, ListItem) and not child.disabled:
                lv.index = i
                break
        lv.focus()

    # -- list build --------------------------------------------------------

    def _populate_list(self) -> None:
        lv = self.query_one("#disabled-ids-list", ListView)
        lv.clear()

        provenance = self._item_provenance()
        category_map = self._category_map()
        disabled_set = self._initial_disabled_set()

        # Partition by category.
        hint_ids = sorted(
            iid for iid in provenance.keys() if category_map.get(iid) == "hint"
        )
        rule_ids = sorted(
            iid for iid in provenance.keys() if category_map.get(iid) == "rule"
        )

        if hint_ids:
            lv.append(_IdHeaderItem("━━ Hints ━━"))
            for iid in hint_ids:
                self._append_id_rows(lv, iid, "hint", provenance, disabled_set)

        if rule_ids:
            lv.append(_IdHeaderItem("━━ Guardrail rules ━━"))
            for iid in rule_ids:
                self._append_id_rows(lv, iid, "rule", provenance, disabled_set)

    def _append_id_rows(
        self,
        lv: ListView,
        iid: str,
        category: str,
        provenance: dict[str, frozenset[str]],
        disabled_set: set[tuple[str, str]],
    ) -> None:
        tiers = sorted(
            provenance[iid],
            key=lambda t: _TIER_ORDER.index(t) if t in _TIER_ORDER else 99,
        )
        for tier in tiers:
            checked = (tier, iid) in disabled_set or ("*", iid) in disabled_set
            lv.append(_TierIdItem(iid, tier, category, checked))

    # -- read app state ---------------------------------------------------

    def _item_provenance(self) -> dict[str, frozenset[str]]:
        load_result = getattr(self._chat_app, "_load_result", None)
        if load_result is None:
            return {}
        return getattr(load_result, "item_provenance", {}) or {}

    def _category_map(self) -> dict[str, str]:
        """Classify each id as ``"hint"`` or ``"rule"`` by membership.

        Rules and injections both go into ``LoadResult.rules`` /
        ``LoadResult.injections`` per Group C; this surface treats both as
        the "Guardrail rules" category. Hints come from ``LoadResult.hints``.
        """
        load_result = getattr(self._chat_app, "_load_result", None)
        if load_result is None:
            return {}
        out: dict[str, str] = {}
        for hint in getattr(load_result, "hints", []) or []:
            iid = getattr(hint, "id", None)
            if iid:
                out[iid] = "hint"
        for rule in getattr(load_result, "rules", []) or []:
            iid = getattr(rule, "id", None)
            if iid:
                out[iid] = "rule"
        for inj in getattr(load_result, "injections", []) or []:
            iid = getattr(inj, "id", None)
            if iid:
                out[iid] = "rule"
        return out

    def _initial_disabled_set(self) -> set[tuple[str, str]]:
        pc = getattr(self._chat_app, "_project_config", None)
        if pc is None:
            return set()
        raw: frozenset[str] = getattr(pc, "disabled_ids", frozenset())
        out: set[tuple[str, str]] = set()
        for entry in raw:
            tier, iid = _split_id_entry(entry)
            out.add((tier, iid))
        return out

    # -- key actions -------------------------------------------------------

    def action_toggle_row(self) -> None:
        lv = self.query_one("#disabled-ids-list", ListView)
        item = lv.highlighted_child
        if isinstance(item, _TierIdItem):
            item.toggle()

    def action_accept(self) -> None:
        self.dismiss(self._encode_result())

    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        # If selecting a toggle row, treat as "accept" per SPEC §7.12 binding.
        self.dismiss(self._encode_result())

    # -- encoding ---------------------------------------------------------

    def _encode_result(self) -> frozenset[str]:
        lv = self.query_one("#disabled-ids-list", ListView)
        rows: list[tuple[str, str, bool]] = []
        for child in lv.children:
            if isinstance(child, _TierIdItem):
                rows.append((child.tier, child.item_id, child.checked))
        return encode_disabled_id_set(rows)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def encode_disabled_id_set(rows: list[tuple[str, str, bool]]) -> frozenset[str]:
    """Encode ``[(tier, item_id, checked), ...]`` rows into a save-ready set.

    Per SPEC §7.7: tier-targeted entries write ``<tier>:<item_id>``; bare
    ``<item_id>`` collapses to "all tiers disabled". Item ids retain their
    ``namespace:bare_id`` qualification, so a tier-targeted entry has the
    final form ``<tier>:<namespace>:<bare_id>``.
    """
    out: set[str] = set()
    by_id: dict[str, list[tuple[str, bool]]] = {}
    for tier, iid, checked in rows:
        by_id.setdefault(iid, []).append((tier, checked))

    for iid, items in by_id.items():
        all_disabled = all(c for _, c in items)
        none_disabled = not any(c for _, c in items)
        if none_disabled:
            continue
        if all_disabled:
            out.add(iid)
            continue
        for tier, checked in items:
            if checked:
                out.add(f"{tier}:{iid}")
    return frozenset(out)


def _split_id_entry(entry: str) -> tuple[str, str]:
    """Parse a ``disabled_ids`` entry into ``(tier_or_*, item_id)``.

    Item ids are namespaced (``namespace:bare_id``); tier-targeted entries
    take the form ``<tier>:<namespace>:<bare_id>``. Bare entries (``namespace:bare_id``
    without a leading tier prefix) return ``("*", entry)`` to mean "applies
    to all tiers".

    A leading token is treated as a tier only if it is one of the canonical
    tier names (``package`` / ``user`` / ``project``); any other prefix is
    interpreted as the namespace of a bare qualified id (per SPEC §3.6 +
    Group C parse_disable_entries semantics).
    """
    if ":" not in entry:
        return "*", entry
    head, rest = entry.split(":", 1)
    if head in ("package", "user", "project"):
        return head, rest
    return "*", entry


__all__ = ["DisabledIdsScreen", "encode_disabled_id_set"]
