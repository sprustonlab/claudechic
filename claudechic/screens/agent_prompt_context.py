"""Advanced subscreens for the ``Agent prompt context`` settings section.

Two screens, one per segment, sharing the same checklist + one-row-floor
behavior. Per ``ui_settings_final.md`` rev4 (locked):

- :class:`AdvancedConstraintsSitesScreen` -- 4 rows
  (``spawn`` / ``activation`` / ``phase-advance`` / ``post-compact``)
  bound to ``constraints_segment.scope.sites``.
- :class:`AdvancedEnvironmentSitesScreen` -- 3 rows
  (``spawn`` / ``activation`` / ``post-compact``) bound to
  ``environment_segment.scope.sites``.

Both screens enforce the **one-row floor** at toggle time: attempting to
uncheck the last remaining row reverts the toggle and emits the notice
``at least one site must remain checked`` (severity ``warning``). Empty
``scope.sites`` is also rejected at config-load time per
:class:`claudechic.config.ConfigValidationError` -- the UI catches it
early so the user never reaches a state ``Enter`` would refuse.

The screens return ``frozenset[str]`` of enabled site tokens on
``Enter`` / ``None`` on ``Esc``. Caller (settings.py) is responsible for
turning the frozenset into a sorted list before persisting (YAML stores
lists, not sets).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Label, ListItem, ListView, Static

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class _SiteSpec:
    """Declarative description of one site row.

    ``token`` is the engineering token that lands in YAML; ``label`` is
    the user-facing primary text shown in the checklist.
    """

    token: str
    label: str


# Fixed orderings per ui_settings_final.md §2.3.
_CONSTRAINTS_SITES: tuple[_SiteSpec, ...] = (
    _SiteSpec("spawn", "when an agent starts"),
    _SiteSpec("activation", "when the workflow activates"),
    _SiteSpec("phase-advance", "on phase advance"),
    _SiteSpec("post-compact", "after compaction"),
)

_ENVIRONMENT_SITES: tuple[_SiteSpec, ...] = (
    _SiteSpec("spawn", "when an agent starts"),
    _SiteSpec("activation", "when the workflow activates"),
    _SiteSpec("post-compact", "after compaction"),
)


_FOOTER_HINT = "Space to toggle  ·  Enter / Esc to close (saves)"
_LAST_ROW_NOTICE = "at least one site must remain checked"


class _SiteRow(ListItem):
    """One toggleable site checkbox row.

    Mirrors :class:`disabled_ids._TierIdItem` visually:
    ``[x] <label>`` on the primary line, ``<token>`` on a muted second
    line so a user reading YAML can map back. All rows are plain enabled
    checkboxes; :meth:`toggle` inverts the checked state.
    """

    DEFAULT_CSS = """
    _SiteRow {
        height: auto;
        padding: 0 0 0 1;
    }
    _SiteRow .row-label {
        width: 1fr;
    }
    _SiteRow .row-token {
        color: $text-muted;
        padding: 0 0 0 6;
    }
    """

    def __init__(self, spec: _SiteSpec, checked: bool) -> None:
        super().__init__()
        self.spec = spec
        self.checked = checked

    def compose(self) -> ComposeResult:
        yield Label(self._render_label(), classes="row-label", markup=False)
        yield Label(self.spec.token, classes="row-token", markup=False)

    def _render_label(self) -> str:
        mark = "[x]" if self.checked else "[ ]"
        return f"{mark} {self.spec.label}"

    def toggle(self) -> None:
        self.checked = not self.checked
        try:
            self.query_one(".row-label", Label).update(self._render_label())
        except Exception as e:  # pragma: no cover -- defensive
            log.debug("toggle re-render failed: %s", e)


class _SitesScreenBase(Screen[frozenset[str] | None]):
    """Shared base for both Advanced subscreens.

    Subclasses set :attr:`SITES`, :attr:`TITLE`, :attr:`HELPER`. The base
    handles compose / mount / Space-toggle / Enter-save / Esc-cancel and
    the one-row-floor enforcement.
    """

    SITES: tuple[_SiteSpec, ...] = ()
    TITLE: str = ""
    HELPER: str = ""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "accept", "Accept"),
        Binding("space", "toggle_row", "Toggle", priority=True),
    ]

    DEFAULT_CSS = """
    _SitesScreenBase {
        background: $background;
        align: center top;
    }
    _SitesScreenBase #sites-container {
        width: 100%;
        max-width: 100;
        height: 100%;
        padding: 1 2;
    }
    _SitesScreenBase #sites-title {
        height: 1;
        text-style: bold;
    }
    _SitesScreenBase #sites-helper {
        height: auto;
        margin-bottom: 1;
        color: $text-muted;
    }
    _SitesScreenBase #sites-list,
    _SitesScreenBase #sites-list:focus {
        height: 1fr;
        background: transparent;
    }
    _SitesScreenBase #sites-list > ListItem {
        padding: 0 0 0 1;
        border-left: tall $panel;
    }
    _SitesScreenBase #sites-list > ListItem:hover,
    _SitesScreenBase #sites-list > ListItem.-highlight {
        background: $surface-darken-1;
        border-left: tall $primary;
    }
    _SitesScreenBase #sites-footer {
        height: 1;
        color: $text-muted;
        margin-top: 1;
    }
    """

    def __init__(self, enabled: frozenset[str]) -> None:
        super().__init__()
        self._initial_enabled = enabled

    def compose(self) -> ComposeResult:
        with Vertical(id="sites-container"):
            yield Static(self.TITLE, id="sites-title")
            yield Static(self.HELPER, id="sites-helper")
            with VerticalScroll():
                yield ListView(id="sites-list")
            yield Static(_FOOTER_HINT, id="sites-footer")

    def on_mount(self) -> None:
        self._populate_list()
        lv = self.query_one("#sites-list", ListView)
        if lv.children:
            lv.index = 0
        lv.focus()

    def _populate_list(self) -> None:
        lv = self.query_one("#sites-list", ListView)
        lv.clear()
        for spec in self.SITES:
            checked = spec.token in self._initial_enabled
            lv.append(_SiteRow(spec, checked))

    # -- toggle / save / cancel -------------------------------------------

    def _rows(self) -> list[_SiteRow]:
        lv = self.query_one("#sites-list", ListView)
        return [c for c in lv.children if isinstance(c, _SiteRow)]

    def _try_toggle(self, row: _SiteRow) -> None:
        """One-row-floor: refuse to uncheck the last remaining checked row."""
        if row.checked:
            checked_rows = [r for r in self._rows() if r.checked]
            if len(checked_rows) == 1 and checked_rows[0] is row:
                self.app.notify(_LAST_ROW_NOTICE, severity="warning")
                return
        row.toggle()

    def action_toggle_row(self) -> None:
        lv = self.query_one("#sites-list", ListView)
        item = lv.highlighted_child
        if isinstance(item, _SiteRow):
            self._try_toggle(item)

    def action_accept(self) -> None:
        self.dismiss(self._encode_result())

    def action_cancel(self) -> None:
        # Live-save semantics: closing the screen (Esc) commits the
        # current set of checked rows. There is no transactional
        # "discard" in this screen -- the spec does not define one and
        # users intuitively expect their toggles to persist when they
        # navigate back to /settings (live remote testing showed this
        # was the source of the "stale count" complaint).
        self.dismiss(self._encode_result())

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        # Enter / mouse-click on a row commits and dismisses. This is
        # ListView's default Enter binding firing -- routing it through
        # _try_toggle made Enter a second toggle key, which contradicts
        # the spec's footer ("Space to toggle"). Toggling lives behind
        # the Space binding (action_toggle_row) only.
        self.dismiss(self._encode_result())

    def _encode_result(self) -> frozenset[str]:
        return frozenset(r.spec.token for r in self._rows() if r.checked)


class AdvancedConstraintsSitesScreen(_SitesScreenBase):
    """4-row checklist bound to ``constraints_segment.scope.sites``."""

    SITES = _CONSTRAINTS_SITES
    TITLE = "Rules block — Advanced"
    HELPER = "Inject the rules block at:"


class AdvancedEnvironmentSitesScreen(_SitesScreenBase):
    """3-row checklist bound to ``environment_segment.scope.sites``."""

    SITES = _ENVIRONMENT_SITES
    TITLE = "Team coordination context — Advanced"
    HELPER = "Inject the coordination block at:"


__all__ = [
    "AdvancedConstraintsSitesScreen",
    "AdvancedEnvironmentSitesScreen",
]
