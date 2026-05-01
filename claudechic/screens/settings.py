"""Settings screen — in-app configuration editor.

Per SPEC §7.2-§7.5: a single-screen editor that exposes user-tier and
project-tier configuration keys, saves live on each edit, and routes to
sub-screens for list-shaped values (disabled_workflows / disabled_ids).

Reached from three entry points (settings footer label / `/settings`
command / welcome screen action), all routed through the parity contract
``ChatApp._handle_settings()`` (per §7.8).

Hidden keys (``analytics.id``, ``experimental.*``) are documented in
``docs/configuration.md`` only — not surfaced in this screen.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen, Screen
from textual.widgets import Input, Label, ListItem, ListView, Static

if TYPE_CHECKING:
    from claudechic.app import ChatApp

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Key registry
# ---------------------------------------------------------------------------


_PERMISSION_MODES = ("default", "acceptEdits", "plan", "auto", "bypassPermissions")
_NOTIFY_LEVELS = ("debug", "info", "warning", "error", "none")
# SDK thinking-budget levels (SPEC C3). "max" is Opus-only; we still
# expose it in /settings so an Opus user can set the persistent default.
# The footer EffortLabel snaps to "medium" on non-Opus models even when
# config says "max".
_EFFORT_LEVELS = ("low", "medium", "high", "max")


@dataclass(frozen=True)
class SettingKey:
    """Declarative description of one configurable key.

    ``editor`` is one of ``"bool"``, ``"enum"``, ``"int"``, ``"text"``,
    ``"subscreen"``. ``tier`` is ``"user"`` or ``"project"``.
    """

    key: str
    label: str
    tier: str  # "user" | "project"
    editor: str  # "bool" | "enum" | "int" | "text" | "subscreen"
    helper: str = ""
    choices: tuple[str, ...] = ()
    int_min: int = 0
    int_max: int = 100
    presets: tuple[str, ...] = ()


USER_KEYS: tuple[SettingKey, ...] = (
    SettingKey(
        key="default_permission_mode",
        label="Default permission mode",
        tier="user",
        editor="enum",
        choices=_PERMISSION_MODES,
    ),
    SettingKey(
        key="theme",
        label="Theme",
        tier="user",
        editor="subscreen",
        helper="Open theme picker (delegates to /theme).",
    ),
    SettingKey(
        key="vi-mode",
        label="Vi mode",
        tier="user",
        editor="bool",
    ),
    SettingKey(
        key="show_message_metadata",
        label="Show message metadata",
        tier="user",
        editor="bool",
    ),
    SettingKey(
        key="recent-tools-expanded",
        label="Recent tools expanded",
        tier="user",
        editor="int",
        int_min=0,
        int_max=20,
    ),
    SettingKey(
        key="worktree.path_template",
        label="Worktree path template",
        tier="user",
        editor="text",
        presets=(
            "<default>",
            "$HOME/code/worktrees/${repo_name}/${branch_name}",
            "$HOME/worktrees/${repo_name}-${branch_name}",
        ),
    ),
    SettingKey(
        key="analytics.enabled",
        label="Analytics enabled",
        tier="user",
        editor="bool",
    ),
    SettingKey(
        key="logging.file",
        label="Logging file path",
        tier="user",
        editor="text",
        helper="Path to log file, or empty to disable.",
    ),
    SettingKey(
        key="logging.notify-level",
        label="Logging notify level",
        tier="user",
        editor="enum",
        choices=_NOTIFY_LEVELS,
    ),
    SettingKey(
        key="awareness.install",
        label="Install claudechic-awareness",
        tier="user",
        editor="bool",
        helper=(
            "Auto-install claudechic-awareness docs into ~/.claude/rules/ "
            "on every claudechic startup. Disabling stops new installs but "
            "does not remove already-installed files — manage "
            "~/.claude/rules/claudechic_*.md yourself when off (e.g., "
            "rm ~/.claude/rules/claudechic_*.md to remove all "
            "claudechic-installed docs)."
        ),
    ),
    SettingKey(
        key="effort",
        label="SDK effort level",
        tier="user",
        editor="enum",
        choices=_EFFORT_LEVELS,
        helper=(
            "SDK thinking-budget level passed to ClaudeAgentOptions. "
            "'max' is Opus-only; non-Opus models snap to 'medium' on "
            "model change. Saved here, mutated live by clicking the "
            "'effort' label in the footer."
        ),
    ),
)


PROJECT_KEYS: tuple[SettingKey, ...] = (
    SettingKey(
        key="guardrails",
        label="Guardrails",
        tier="project",
        editor="bool",
        helper=(
            "Enable guardrail rule enforcement. "
            "Changes apply to new agents; restart claudechic to apply to "
            "existing agents."
        ),
    ),
    SettingKey(
        key="hints",
        label="Hints",
        tier="project",
        editor="bool",
        helper="Enable advisory hint toasts.",
    ),
    SettingKey(
        key="disabled_workflows",
        label="Disabled workflows",
        tier="project",
        editor="subscreen",
        helper=(
            "Disabling a workflow by ID hides it from this project "
            "regardless of which level (package / user / project) defines it."
        ),
    ),
    SettingKey(
        key="disabled_ids",
        label="Disabled IDs",
        tier="project",
        editor="subscreen",
        helper="Disable hint and guardrail-rule IDs by level.",
    ),
)


# ---------------------------------------------------------------------------
# Inline editor modals (enum / text / int / confirm)
# ---------------------------------------------------------------------------


class _EnumPickerModal(ModalScreen[str | None]):
    """Pick one value from a fixed set of choices."""

    BINDINGS = [Binding("escape", "dismiss(None)", "Cancel")]

    DEFAULT_CSS = """
    _EnumPickerModal {
        align: center middle;
    }
    _EnumPickerModal #enum-picker-container {
        width: 60%;
        max-width: 70;
        height: auto;
        max-height: 80%;
        background: $surface;
        border: round $primary;
        padding: 1 2;
    }
    _EnumPickerModal .enum-title {
        text-style: bold;
        margin-bottom: 1;
    }
    _EnumPickerModal #enum-list,
    _EnumPickerModal #enum-list:focus {
        height: auto;
        max-height: 20;
        background: transparent;
    }
    _EnumPickerModal #enum-list > ListItem {
        padding: 0 1;
    }
    _EnumPickerModal #enum-list > ListItem.-highlight,
    _EnumPickerModal #enum-list > ListItem:hover {
        background: $surface-darken-1;
    }
    """

    def __init__(self, label: str, choices: tuple[str, ...], current: str) -> None:
        super().__init__()
        self._label = label
        self._choices = choices
        self._current = current

    def compose(self) -> ComposeResult:
        with Vertical(id="enum-picker-container"):
            yield Static(self._label, classes="enum-title")
            items = [
                ListItem(Label(f"{c}{' ✓' if c == self._current else ''}"))
                for c in self._choices
            ]
            yield ListView(*items, id="enum-list")

    def on_mount(self) -> None:
        lv = self.query_one("#enum-list", ListView)
        try:
            lv.index = self._choices.index(self._current)
        except ValueError:
            lv.index = 0
        lv.focus()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        idx = event.list_view.index
        if idx is None:
            self.dismiss(None)
            return
        self.dismiss(self._choices[idx])


class _TextEditModal(ModalScreen[str | None]):
    """Edit a free-form text value. Returns the typed string, or None on cancel.

    An empty submit returns the empty string; callers that treat empty as
    "unset / None" handle that translation themselves.
    """

    BINDINGS = [Binding("escape", "dismiss(None)", "Cancel")]

    DEFAULT_CSS = """
    _TextEditModal {
        align: center middle;
    }
    _TextEditModal #text-edit-container {
        width: 60%;
        max-width: 80;
        height: auto;
        background: $surface;
        border: round $primary;
        padding: 1 2;
    }
    _TextEditModal .text-edit-title {
        text-style: bold;
        margin-bottom: 1;
    }
    _TextEditModal .text-edit-helper {
        color: $text-muted;
        margin-bottom: 1;
    }
    _TextEditModal .text-edit-presets {
        color: $text-muted;
        margin-top: 1;
    }
    """

    def __init__(
        self,
        label: str,
        current: str,
        helper: str = "",
        presets: tuple[str, ...] = (),
    ) -> None:
        super().__init__()
        self._label = label
        self._current = current
        self._helper = helper
        self._presets = presets

    def compose(self) -> ComposeResult:
        with Vertical(id="text-edit-container"):
            yield Static(self._label, classes="text-edit-title")
            if self._helper:
                yield Static(self._helper, classes="text-edit-helper")
            yield Input(value=self._current, id="text-edit-input")
            if self._presets:
                presets_md = "Presets: " + " · ".join(self._presets)
                yield Static(presets_md, classes="text-edit-presets")

    def on_mount(self) -> None:
        self.query_one("#text-edit-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)


class _IntEditModal(ModalScreen[int | None]):
    """Edit an integer value with min/max validation."""

    BINDINGS = [Binding("escape", "dismiss(None)", "Cancel")]

    DEFAULT_CSS = """
    _IntEditModal {
        align: center middle;
    }
    _IntEditModal #int-edit-container {
        width: 50%;
        max-width: 60;
        height: auto;
        background: $surface;
        border: round $primary;
        padding: 1 2;
    }
    _IntEditModal .int-edit-title {
        text-style: bold;
        margin-bottom: 1;
    }
    _IntEditModal .int-edit-range {
        color: $text-muted;
        margin-bottom: 1;
    }
    """

    def __init__(self, label: str, current: int, lo: int, hi: int) -> None:
        super().__init__()
        self._label = label
        self._current = current
        self._lo = lo
        self._hi = hi

    def compose(self) -> ComposeResult:
        with Vertical(id="int-edit-container"):
            yield Static(self._label, classes="int-edit-title")
            yield Static(f"Range: {self._lo}-{self._hi}", classes="int-edit-range")
            yield Input(value=str(self._current), id="int-edit-input")

    def on_mount(self) -> None:
        self.query_one("#int-edit-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        try:
            value = int(event.value)
        except ValueError:
            self.app.notify(f"must be integer {self._lo}-{self._hi}", severity="error")
            return
        if not (self._lo <= value <= self._hi):
            self.app.notify(f"must be integer {self._lo}-{self._hi}", severity="error")
            return
        self.dismiss(value)


class _ConfirmResetModal(ModalScreen[bool | None]):
    """Confirm reset-to-defaults prompt."""

    BINDINGS = [
        Binding("escape", "dismiss(False)", "Cancel"),
        Binding("y", "confirm", "Yes"),
        Binding("n", "dismiss(False)", "No"),
    ]

    DEFAULT_CSS = """
    _ConfirmResetModal {
        align: center middle;
    }
    _ConfirmResetModal #confirm-container {
        width: 50%;
        max-width: 60;
        height: auto;
        background: $surface;
        border: round $warning;
        padding: 1 2;
    }
    _ConfirmResetModal .confirm-title {
        text-style: bold;
        margin-bottom: 1;
    }
    _ConfirmResetModal .confirm-help {
        color: $text-muted;
        margin-top: 1;
    }
    """

    def __init__(self, prompt: str) -> None:
        super().__init__()
        self._prompt = prompt

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-container"):
            yield Static(self._prompt, classes="confirm-title")
            yield Static("[y] Yes  ·  [n] No  ·  [esc] Cancel", classes="confirm-help")

    def action_confirm(self) -> None:
        self.dismiss(True)


# ---------------------------------------------------------------------------
# Setting row widget
# ---------------------------------------------------------------------------


class _SettingRow(ListItem):
    """One row in the SettingsScreen list — label + value + level badge.

    ``activate`` is invoked when the user presses Enter / Space on the row;
    the SettingsScreen owner installs this callback to drive the edit flow.
    """

    DEFAULT_CSS = """
    _SettingRow {
        height: auto;
        padding: 0 0 0 1;
    }
    _SettingRow .row-label {
        width: 1fr;
    }
    _SettingRow .row-value {
        color: $secondary;
        width: auto;
        margin: 0 1;
    }
    _SettingRow .row-badge {
        color: $text-muted;
        width: auto;
    }
    _SettingRow .row-helper {
        color: $text-muted;
        text-style: italic;
    }
    """

    def __init__(
        self,
        spec: SettingKey,
        value_text: str,
        helper_visible: bool = True,
    ) -> None:
        super().__init__()
        self.spec = spec
        self._value_text = value_text
        self._helper_visible = helper_visible

    def compose(self) -> ComposeResult:
        line = f"{self.spec.label}    {self._value_text}    [{self.spec.tier}]"
        yield Label(line, classes="row-label")
        if self._helper_visible and self.spec.helper:
            yield Label(self.spec.helper, classes="row-helper")


class _ActionRow(ListItem):
    """A non-key row (header / reset / reference)."""

    DEFAULT_CSS = """
    _ActionRow {
        height: 1;
        padding: 0 0 0 1;
    }
    _ActionRow.header {
        text-style: bold;
        opacity: 0.8;
    }
    """

    def __init__(self, action_id: str, text: str, header: bool = False) -> None:
        super().__init__(disabled=header)
        self.action_id = action_id
        self._text = text
        if header:
            self.add_class("header")

    def compose(self) -> ComposeResult:
        yield Label(self._text)


# ---------------------------------------------------------------------------
# SettingsScreen
# ---------------------------------------------------------------------------


_ACTION_RESET_USER = "reset-user"
_ACTION_RESET_PROJECT = "reset-project"
_ACTION_OPEN_REFERENCE = "open-reference"


class SettingsScreen(Screen[None]):
    """In-app settings editor.

    Edits save live (no Save / Cancel button); Esc closes the screen.
    """

    BINDINGS = [
        Binding("escape", "go_back", "Close"),
        Binding("slash", "focus_search", "Search"),
    ]

    DEFAULT_CSS = """
    SettingsScreen {
        background: $background;
        align: center top;
    }
    SettingsScreen #settings-container {
        width: 100%;
        max-width: 100;
        height: 100%;
        padding: 1 2;
    }
    SettingsScreen #settings-title {
        height: 1;
        text-style: bold;
    }
    SettingsScreen #settings-subtitle {
        height: auto;
        margin-bottom: 1;
        color: $text-muted;
    }
    SettingsScreen #settings-search {
        height: 3;
        margin-bottom: 1;
    }
    SettingsScreen #settings-list,
    SettingsScreen #settings-list:focus {
        height: 1fr;
        background: transparent;
    }
    SettingsScreen #settings-list > ListItem {
        padding: 0 0 0 1;
        height: auto;
        margin: 0;
        border-left: tall $panel;
    }
    SettingsScreen #settings-list > ListItem:hover,
    SettingsScreen #settings-list > ListItem.-highlight {
        background: $surface-darken-1;
        border-left: tall $primary;
    }
    SettingsScreen #settings-list > ListItem.-disabled {
        opacity: 0.6;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._search: str = ""

    # -- compose / mount ---------------------------------------------------

    def compose(self) -> ComposeResult:
        with Vertical(id="settings-container"):
            yield Static("Settings", id="settings-title")
            yield Static(
                "Edit your claudechic settings. Changes save live.",
                id="settings-subtitle",
            )
            yield Input(placeholder="search settings...", id="settings-search")
            with VerticalScroll():
                yield ListView(id="settings-list")

    def on_mount(self) -> None:
        self._render_list()

    def _chat_app(self) -> ChatApp:
        # ChatApp is the only Textual App subclass in this codebase.
        return self.app  # type: ignore[return-value]

    # -- list rendering ----------------------------------------------------

    def _render_list(self) -> None:
        lv = self.query_one("#settings-list", ListView)
        lv.clear()

        items: list[ListItem] = []
        items.append(
            _ActionRow(
                "header-user",
                "━━ User settings (~/.claudechic/config.yaml) ━━",
                header=True,
            )
        )
        for spec in USER_KEYS:
            if not self._matches_search(spec):
                continue
            items.append(_SettingRow(spec, self._format_value(spec)))
        items.append(
            _ActionRow(_ACTION_RESET_USER, "  ▸ Reset user settings to defaults")
        )

        items.append(_ActionRow("sep-1", "", header=True))
        items.append(
            _ActionRow(
                "header-project",
                "━━ Project settings (./.claudechic/config.yaml) ━━",
                header=True,
            )
        )
        for spec in PROJECT_KEYS:
            if not self._matches_search(spec):
                continue
            items.append(_SettingRow(spec, self._format_value(spec)))
        items.append(
            _ActionRow(_ACTION_RESET_PROJECT, "  ▸ Reset project settings to defaults")
        )

        items.append(_ActionRow("sep-2", "", header=True))
        items.append(_ActionRow("header-ref", "━━ Reference ━━", header=True))
        items.append(
            _ActionRow(
                _ACTION_OPEN_REFERENCE,
                "  ▸ Open docs/configuration.md (full reference)",
            )
        )

        for item in items:
            lv.append(item)

        # Highlight first non-disabled row
        for i, child in enumerate(lv.children):
            if isinstance(child, ListItem) and not child.disabled:
                lv.index = i
                break

    def _matches_search(self, spec: SettingKey) -> bool:
        if not self._search:
            return True
        s = self._search.lower()
        return s in spec.label.lower() or s in spec.key.lower()

    # -- value formatting --------------------------------------------------

    def _format_value(self, spec: SettingKey) -> str:
        value = self._read_value(spec)
        if spec.editor == "subscreen":
            count = len(value) if isinstance(value, (set, frozenset, list)) else 0
            return f"({count} disabled) ▸"
        if spec.editor == "bool":
            return "on" if value else "off"
        if value is None:
            return "<unset>"
        if isinstance(value, str) and not value:
            return "<empty>"
        return str(value)

    def _read_value(self, spec: SettingKey) -> Any:
        from claudechic.config import CONFIG

        app = self._chat_app()
        if spec.tier == "user":
            return _get_dotted(CONFIG, spec.key)
        # project
        pc = getattr(app, "_project_config", None)
        if pc is None:
            return None
        return getattr(pc, spec.key, None)

    # -- search ------------------------------------------------------------

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "settings-search":
            self._search = event.value.strip()
            self._render_list()

    def action_focus_search(self) -> None:
        self.query_one("#settings-search", Input).focus()

    def action_go_back(self) -> None:
        self.dismiss(None)

    # -- selection ---------------------------------------------------------

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item = event.item
        if isinstance(item, _SettingRow):
            self._activate_setting(item.spec)
            return
        if isinstance(item, _ActionRow):
            self._activate_action(item.action_id)
            return

    def _activate_action(self, action_id: str) -> None:
        if action_id == _ACTION_RESET_USER:
            self._confirm_reset("user")
        elif action_id == _ACTION_RESET_PROJECT:
            self._confirm_reset("project")
        elif action_id == _ACTION_OPEN_REFERENCE:
            self._open_reference_doc()

    # -- per-key edit dispatch --------------------------------------------

    def _activate_setting(self, spec: SettingKey) -> None:
        if spec.editor == "bool":
            self._toggle_bool(spec)
        elif spec.editor == "enum":
            self._edit_enum(spec)
        elif spec.editor == "int":
            self._edit_int(spec)
        elif spec.editor == "text":
            self._edit_text(spec)
        elif spec.editor == "subscreen":
            self._open_subscreen(spec)

    def _toggle_bool(self, spec: SettingKey) -> None:
        current = bool(self._read_value(spec))
        self._save_value(spec, not current)
        self._render_list()

    def _edit_enum(self, spec: SettingKey) -> None:
        current = self._read_value(spec) or (spec.choices[0] if spec.choices else "")

        def on_dismiss(value: str | None) -> None:
            if value is None:
                return
            self._save_value(spec, value)
            self._render_list()

        self.app.push_screen(
            _EnumPickerModal(spec.label, spec.choices, str(current)), on_dismiss
        )

    def _edit_int(self, spec: SettingKey) -> None:
        current = self._read_value(spec) or 0

        def on_dismiss(value: int | None) -> None:
            if value is None:
                return
            self._save_value(spec, value)
            self._render_list()

        self.app.push_screen(
            _IntEditModal(spec.label, int(current), spec.int_min, spec.int_max),
            on_dismiss,
        )

    def _edit_text(self, spec: SettingKey) -> None:
        current = self._read_value(spec)
        current_str = "" if current is None else str(current)

        def on_dismiss(value: str | None) -> None:
            if value is None:
                return
            # Empty string means "unset" for nullable text keys.
            saved: Any = None if value == "" else value
            # The "<default>" preset for path_template means None.
            if spec.key == "worktree.path_template" and value == "<default>":
                saved = None
            self._save_value(spec, saved)
            self._render_list()

        self.app.push_screen(
            _TextEditModal(spec.label, current_str, spec.helper, spec.presets),
            on_dismiss,
        )

    def _open_subscreen(self, spec: SettingKey) -> None:
        from claudechic.screens.disabled_ids import DisabledIdsScreen
        from claudechic.screens.disabled_workflows import DisabledWorkflowsScreen

        app = self._chat_app()

        def on_dismiss(result: frozenset[str] | None) -> None:
            if result is None:
                return
            self._save_value(spec, result)
            self._render_list()

        if spec.key == "disabled_workflows":
            self.app.push_screen(DisabledWorkflowsScreen(app), on_dismiss)
        elif spec.key == "disabled_ids":
            self.app.push_screen(DisabledIdsScreen(app), on_dismiss)
        elif spec.key == "theme":
            # Delegate to existing /theme picker; no result handler needed.
            if hasattr(app, "search_themes"):
                app.search_themes()

    # -- save + live re-apply ---------------------------------------------

    def _save_value(self, spec: SettingKey, value: Any) -> None:
        """Persist + run the live re-apply path for ``spec``.

        Per SPEC §7.5 + Leadership correction §8 (rollback on persist
        failure): if save() raises, we revert in-memory mutation AND emit a
        notify(severity="error"). If the live re-apply call raises but the
        save succeeded, the file persists and we notify(severity="warning").
        """
        from claudechic import config as cfg

        app = self._chat_app()
        try:
            if spec.tier == "user":
                # Snapshot for rollback.
                prev = _get_dotted(cfg.CONFIG, spec.key)
                _set_dotted(cfg.CONFIG, spec.key, value)
                try:
                    cfg.save()
                except Exception as err:
                    _set_dotted(cfg.CONFIG, spec.key, prev)
                    self.app.notify(f"Save failed: {err}", severity="error")
                    log.exception("user-tier config save failed for %s", spec.key)
                    return
            else:
                pc = getattr(app, "_project_config", None)
                if pc is None:
                    self.app.notify("No project config available", severity="error")
                    return
                # Build new frozen ProjectConfig.
                update_value: Any = value
                if isinstance(value, (set, frozenset)):
                    update_value = frozenset(value)
                new_pc = replace(pc, **{spec.key: update_value})
                try:
                    new_pc.save(getattr(app, "_cwd"))
                except Exception as err:
                    self.app.notify(f"Save failed: {err}", severity="error")
                    log.exception("project-tier config save failed for %s", spec.key)
                    return
                app._project_config = new_pc
        except Exception as err:  # defensive — should not reach here
            self.app.notify(f"Save failed: {err}", severity="error")
            log.exception("settings save crashed for %s", spec.key)
            return

        # Live re-apply.
        try:
            self._reapply(spec, value)
        except Exception as err:
            self.app.notify(
                f"Saved, but live re-apply failed: {err}", severity="warning"
            )
            log.exception("live re-apply failed for %s", spec.key)

    def _reapply(self, spec: SettingKey, value: Any) -> None:
        app = self._chat_app()
        if spec.key == "default_permission_mode":
            mgr = getattr(app, "agent_mgr", None)
            if mgr is not None and hasattr(mgr, "set_global_permission_mode"):
                # set_global_permission_mode is a coroutine; schedule it.
                app.run_worker(mgr.set_global_permission_mode(value), exclusive=False)
            footer = _try_get_footer(app)
            if footer is not None:
                footer.permission_mode = value
        elif spec.key == "vi-mode":
            if hasattr(app, "_update_vi_mode"):
                app._update_vi_mode(bool(value))
        elif spec.key == "show_message_metadata":
            # Reactive: existing redraws pick up CONFIG.
            pass
        elif spec.key == "recent-tools-expanded":
            pass
        elif spec.key == "worktree.path_template":
            pass
        elif spec.key == "analytics.enabled":
            # _handle_analytics handles notify; we already saved CONFIG so
            # invoke just to emit the user-visible toast.
            from claudechic.commands import _handle_analytics

            _handle_analytics(
                app, "/analytics opt-in" if value else "/analytics opt-out"
            )
        elif spec.key in ("logging.file", "logging.notify-level"):
            from claudechic import errors

            if hasattr(errors, "setup_logging"):
                errors.setup_logging()
        elif spec.key == "awareness.install":
            # Toggle gates next startup; no immediate I/O per SPEC §4.3.
            pass
        elif spec.key == "effort":
            # SPEC C3 live re-apply: push the new level into the active
            # agent (slot 4's _make_options reads agent.effort live) and
            # mirror to the footer's reactive so the displayed level
            # stays in sync.
            footer = _try_get_footer(app)
            if footer is not None:
                footer.effort = value
            agent = getattr(app, "_agent", None)
            if agent is not None and hasattr(agent, "effort"):
                agent.effort = value
        elif spec.key == "guardrails":
            mgr = getattr(app, "agent_mgr", None)
            if mgr is not None and hasattr(mgr, "refresh_guardrails"):
                mgr.refresh_guardrails()
        elif spec.key == "hints":
            if hasattr(app, "_refresh_hints"):
                app._refresh_hints()
        elif spec.key == "disabled_workflows":
            if hasattr(app, "_discover_workflows"):
                app._discover_workflows()
        elif spec.key == "disabled_ids":
            mgr = getattr(app, "agent_mgr", None)
            if mgr is not None and hasattr(mgr, "refresh_guardrails"):
                mgr.refresh_guardrails()
            if hasattr(app, "_refresh_hints"):
                app._refresh_hints()

    # -- reset / reference -------------------------------------------------

    def _confirm_reset(self, tier: str) -> None:
        if tier == "user":
            count = len(USER_KEYS)
            prompt = f"Reset {count} user settings to defaults? This cannot be undone."
        else:
            count = len(PROJECT_KEYS)
            prompt = (
                f"Reset {count} project settings to defaults? This cannot be undone."
            )

        def on_dismiss(confirmed: bool | None) -> None:
            if not confirmed:
                return
            self._do_reset(tier)
            self._render_list()

        self.app.push_screen(_ConfirmResetModal(prompt), on_dismiss)

    def _do_reset(self, tier: str) -> None:
        from claudechic import config as cfg
        from claudechic.config import ProjectConfig

        app = self._chat_app()
        if tier == "user":
            for spec in USER_KEYS:
                _del_dotted(cfg.CONFIG, spec.key)
            try:
                cfg.save()
            except Exception as err:
                self.app.notify(f"Save failed: {err}", severity="error")
                log.exception("user-tier reset save failed")
                return
            self.app.notify("User settings reset to defaults")
        else:
            new_pc = ProjectConfig()
            try:
                new_pc.save(getattr(app, "_cwd"))
            except Exception as err:
                self.app.notify(f"Save failed: {err}", severity="error")
                log.exception("project-tier reset save failed")
                return
            app._project_config = new_pc
            if hasattr(app, "_discover_workflows"):
                app._discover_workflows()
            self.app.notify("Project settings reset to defaults")

    def _open_reference_doc(self) -> None:
        from pathlib import Path

        from claudechic.widgets.content.markdown_preview import MarkdownPreviewModal

        # docs/configuration.md sits at the repo root, two levels above the
        # claudechic package directory in dev installs and inside the source
        # distribution. We resolve relative to this file's location.
        repo_root = Path(__file__).resolve().parent.parent.parent
        rel_path = Path("docs/configuration.md")
        self.app.push_screen(MarkdownPreviewModal(file_path=rel_path, cwd=repo_root))


# ---------------------------------------------------------------------------
# Helpers — dotted-key access on plain dicts
# ---------------------------------------------------------------------------


def _get_dotted(d: dict, key: str) -> Any:
    parts = key.split(".")
    cur: Any = d
    for p in parts:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(p)
        if cur is None:
            return None
    return cur


def _set_dotted(d: dict, key: str, value: Any) -> None:
    parts = key.split(".")
    cur: dict = d
    for p in parts[:-1]:
        nxt = cur.get(p)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[p] = nxt
        cur = nxt
    cur[parts[-1]] = value


def _del_dotted(d: dict, key: str) -> None:
    parts = key.split(".")
    cur: Any = d
    for p in parts[:-1]:
        if not isinstance(cur, dict):
            return
        cur = cur.get(p)
        if cur is None:
            return
    if isinstance(cur, dict):
        cur.pop(parts[-1], None)


def _try_get_footer(app: Any) -> Any:
    try:
        from claudechic.widgets.layout.footer import StatusFooter

        return app.query_one(StatusFooter)
    except Exception:
        return None


# Public alias so tests / other modules can reference the registry without
# importing the dataclasses directly.
ALL_KEYS: tuple[SettingKey, ...] = USER_KEYS + PROJECT_KEYS


__all__ = [
    "ALL_KEYS",
    "PROJECT_KEYS",
    "USER_KEYS",
    "SettingKey",
    "SettingsScreen",
]
