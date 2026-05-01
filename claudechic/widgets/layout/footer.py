"""Custom footer widget."""

import asyncio
import logging

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Static

from claudechic.processes import BackgroundProcess
from claudechic.widgets.base.clickable import ClickableLabel
from claudechic.widgets.input.vi_mode import ViMode
from claudechic.widgets.layout.indicators import ContextBar, CPUBar, ProcessIndicator

log = logging.getLogger(__name__)


class DiagnosticsLabel(ClickableLabel):
    """Clickable diagnostics label."""

    class Requested(Message):
        """Emitted when user clicks to open diagnostics."""

    def on_click(self, event) -> None:
        self.post_message(self.Requested())


class ComputerInfoLabel(ClickableLabel):
    """Clickable 'sys' label that opens ComputerInfoModal."""

    class Requested(Message):
        """Emitted when user clicks to open computer info."""

    def on_click(self, event) -> None:
        self.post_message(self.Requested())


class SettingsLabel(ClickableLabel):
    """Clickable 'settings' label that opens SettingsScreen.

    Mirrors DiagnosticsLabel and ComputerInfoLabel: posts a Requested
    message on click. The handler in app.py routes to the shared
    _handle_settings() entry point (parity with /settings command and
    welcome-screen Settings action per SPEC §7.8).
    """

    class Requested(Message):
        """Emitted when user clicks to open settings."""

    def on_click(self, event) -> None:
        self.post_message(self.Requested())


class AgentLabel(ClickableLabel):
    """Clickable agent name label in the footer.

    Shows the active agent name (truncated to 12 chars). Hidden when
    only one agent is active. Clicking opens the AgentSwitcher modal.
    """

    can_focus = False

    class SwitcherRequested(Message):
        """Emitted when user clicks to open the agent switcher."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._display_name: str = ""

    @property
    def renderable(self) -> str:
        """Return the current display text."""
        return self._display_name

    def on_click(self, event) -> None:
        self.post_message(self.SwitcherRequested())

    def update_agent(self, name: str, visible: bool) -> None:
        """Update the displayed agent name and visibility.

        Args:
            name: Active agent name (truncated to 12 chars for display).
            visible: Whether to show the label (False when single agent).
        """
        display_name = name[:12] if len(name) > 12 else name
        self._display_name = display_name
        self.update(display_name)
        self.set_class(not visible, "hidden")


class PermissionModeLabel(ClickableLabel):
    """Clickable permission mode status label."""

    class Toggled(Message):
        """Emitted when permission mode is toggled."""

    def on_click(self, event) -> None:
        self.post_message(self.Toggled())


class ModelLabel(ClickableLabel):
    """Clickable model label."""

    class ModelChangeRequested(Message):
        """Emitted when user wants to change the model."""

    def on_click(self, event) -> None:
        self.post_message(self.ModelChangeRequested())


class EffortLabel(ClickableLabel):
    """Clickable effort label - cycles through valid SDK ``effort`` levels.

    The on-screen label text uses the literal string ``"effort"`` to match
    SDK vocabulary (per SPEC Decision 2). The level cycles
    ``low -> medium -> high -> max -> low`` on click; ``max`` is Opus-only,
    so non-Opus models snap the displayed level to ``"medium"`` on model
    change (per SPEC locked Decision 5 from slot 1 review).

    On click the widget mutates ``app._agent.effort`` directly (the
    options factory reads ``agent.effort`` live) and persists the new
    level to ``~/.claudechic/config.yaml`` so the choice survives a
    restart (SPEC C3).
    """

    # Global ordering used to snap a current level into a smaller subset
    # when the model changes. Members of ``_levels`` always preserve this
    # relative ordering.
    DEFAULT_LEVELS: tuple[str, ...] = ("low", "medium", "high", "max")

    # Per-model effort levels.  ``max`` triggers extended thinking which
    # is only supported on Opus.
    MODEL_EFFORT_LEVELS: dict[str, tuple[str, ...]] = {
        "haiku": ("low", "medium", "high"),
        "sonnet": ("low", "medium", "high"),
        "opus": ("low", "medium", "high", "max"),
    }

    EFFORT_DISPLAY: dict[str, str] = {
        "low": "effort: low",
        "medium": "effort: medium",
        "high": "effort: high",
        "max": "effort: max",
    }

    class Cycled(Message):
        """Emitted after the user clicks to cycle effort level.

        Carries the new level so observers (tests, app handlers) can
        react. The widget itself has already updated its display and
        mutated ``app._agent.effort`` before posting.
        """

        def __init__(self, effort: str) -> None:
            super().__init__()
            self.effort = effort

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._effort: str = "high"
        self._levels: tuple[str, ...] = self.DEFAULT_LEVELS

    def on_click(self, event) -> None:  # noqa: ARG002
        levels = self._levels
        if not levels:
            return
        idx = levels.index(self._effort) if self._effort in levels else len(levels) - 1
        next_effort = levels[(idx + 1) % len(levels)]
        self.set_effort(next_effort)

        # Per-agent runtime state: mutate the active agent's effort live.
        # The options factory in app.py reads agent.effort on every
        # _make_options call (slot 4 wiring), so the next SDK turn picks
        # up the new level without reconnecting.
        app = self.app
        agent = getattr(app, "_agent", None)
        if agent is not None and hasattr(agent, "effort"):
            agent.effort = next_effort

        # Mirror to the parent StatusFooter's reactive so external
        # writers (agent switch, model change) stay in sync.
        ancestor = self.parent
        while ancestor is not None and not isinstance(ancestor, StatusFooter):
            ancestor = getattr(ancestor, "parent", None)
        if ancestor is not None:
            ancestor.effort = next_effort

        # Persist as the default for the next session (SPEC C3).
        # Best-effort: if the config write fails the cycle still works
        # for the current session.
        try:
            from claudechic import config as cfg

            cfg.CONFIG["effort"] = next_effort
            cfg.save()
        except Exception:
            log.exception("failed to persist effort level to config")

        self.post_message(self.Cycled(next_effort))

    def set_effort(self, effort: str) -> None:
        """Update the displayed effort level."""
        self._effort = effort
        self.update(self.EFFORT_DISPLAY.get(effort, f"effort: {effort}"))

    def set_available_levels(self, levels: tuple[str, ...]) -> None:
        """Update the set of effort levels available for cycling.

        If the current level is not in the new set, snap to the closest
        valid level by descending the global ordering. Used when the
        model changes (e.g., switching from Opus to Sonnet drops
        ``"max"`` and the current level snaps from ``"max"`` to
        ``"medium"`` per SPEC Decision 5).
        """
        if not levels:
            return
        self._levels = levels
        if self._effort in levels:
            return
        # SPEC Decision 5: non-Opus models snap to "medium" when the
        # current level is unavailable. We honour this when "medium"
        # is in the new set; otherwise fall back to the highest valid
        # level <= current position in the global ordering.
        if "medium" in levels:
            self.set_effort("medium")
            return
        global_order = self.DEFAULT_LEVELS
        try:
            cur_idx = global_order.index(self._effort)
        except ValueError:
            cur_idx = len(global_order) - 1
        best = levels[0]
        for lvl in levels:
            try:
                if global_order.index(lvl) <= cur_idx:
                    best = lvl
            except ValueError:
                pass
        self.set_effort(best)

    # Fallback for unknown model strings: the safer subset without
    # ``"max"`` (which is Opus-only and rejected by other families).
    UNKNOWN_MODEL_LEVELS: tuple[str, ...] = ("low", "medium", "high")

    @classmethod
    def levels_for_model(cls, model: str | None) -> tuple[str, ...]:
        """Return the valid effort levels for a model string.

        Matches against known model families by checking if ``model``
        contains a known alias (``opus`` / ``sonnet`` / ``haiku``).
        Unknown model strings (or empty) fall back to
        ``UNKNOWN_MODEL_LEVELS`` -- the safer subset without ``"max"``,
        since ``"max"`` is Opus-only and would be rejected by any
        non-Opus family the alias-match missed.
        """
        if not model:
            return cls.UNKNOWN_MODEL_LEVELS
        model_lower = model.lower()
        for family, levels in cls.MODEL_EFFORT_LEVELS.items():
            if family in model_lower:
                return levels
        return cls.UNKNOWN_MODEL_LEVELS


class ViModeLabel(Static):
    """Shows current vim mode: INSERT, NORMAL, VISUAL."""

    DEFAULT_CSS = """
    ViModeLabel {
        width: auto;
        padding: 0 1;
        text-style: bold;
        &.vi-insert { color: $success; }
        &.vi-normal { color: $primary; }
        &.vi-visual { color: $warning; }
    }
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._mode: ViMode | None = None
        self._enabled: bool = False

    def set_mode(self, mode: ViMode | None, enabled: bool = True) -> None:
        """Update the displayed mode."""
        self._mode = mode
        self._enabled = enabled

        self.remove_class("vi-insert", "vi-normal", "vi-visual", "hidden")

        if not enabled:
            self.add_class("hidden")
            return

        if mode == ViMode.INSERT:
            self.update("INSERT")
            self.add_class("vi-insert")
        elif mode == ViMode.NORMAL:
            self.update("NORMAL")
            self.add_class("vi-normal")
        elif mode == ViMode.VISUAL:
            self.update("VISUAL")
            self.add_class("vi-visual")


async def get_git_branch(cwd: str | None = None) -> str:
    """Get current git branch name (async)."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "git",
            "branch",
            "--show-current",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=1)
        return stdout.decode().strip() or "detached"
    except Exception:
        return ""


class StatusFooter(Static):
    """Footer showing git branch, model, auto-edit status, and resource indicators."""

    can_focus = False
    permission_mode = reactive("auto")  # auto, default, acceptEdits, plan
    model = reactive("")
    # SDK thinking-budget level mirrored into the footer EffortLabel.
    # External writers (agent switch, model change, settings re-apply)
    # set this; ``watch_effort`` then updates the visible label.
    effort = reactive("high")
    branch = reactive("")

    async def on_mount(self) -> None:
        self.branch = await get_git_branch()
        # Hydrate effort from persisted config so the footer shows the
        # saved level on startup (SPEC C3). Best-effort: fall back to
        # the reactive's default ("high") if config is unreadable.
        try:
            from claudechic import config as cfg

            saved_effort = cfg.CONFIG.get("effort", "high")
        except Exception:
            saved_effort = "high"
        if saved_effort != self.effort:
            self.effort = saved_effort
        else:
            # Force a label paint even when value matches the default,
            # since the reactive only fires on change.
            if label := self.query_one_optional("#effort-label", EffortLabel):
                label.set_effort(saved_effort)
        # Propagate the saved level to the active agent if one already
        # exists. Agents created later will pick up the value when the
        # caller assigns ``agent.effort`` on first use; until then they
        # carry the Agent default ("high") set in slot 1.
        app = self.app
        agent = getattr(app, "_agent", None)
        if agent is not None and hasattr(agent, "effort"):
            agent.effort = saved_effort

    async def refresh_branch(self, cwd: str | None = None) -> None:
        """Update branch from given directory (async)."""
        self.branch = await get_git_branch(cwd)

    def compose(self) -> ComposeResult:
        with Horizontal(id="footer-content"):
            yield ViModeLabel("", id="vi-mode-label", classes="hidden")
            yield ModelLabel("", id="model-label", classes="footer-label")
            yield Static("·", classes="footer-sep")
            # SPEC C2: EffortLabel sits between ModelLabel and
            # PermissionModeLabel. The literal string "effort" is the
            # SDK vocabulary (Decision 2); first paint comes from
            # on_mount's hydrate-from-config.
            yield EffortLabel("effort: high", id="effort-label", classes="footer-label")
            yield Static("·", classes="footer-sep")
            yield PermissionModeLabel(
                "Auto-edit: off", id="permission-mode-label", classes="footer-label"
            )
            yield Static("·", classes="footer-sep")
            # DiagnosticsLabel keeps its class name so the existing
            # ``on_diagnostics_label_requested`` handler in app.py (slot 4)
            # still dispatches; the visible text is "info" reflecting the
            # SPEC F consolidation (Diagnostics + ComputerInfo -> single
            # InfoModal). The accompanying ``ComputerInfoLabel`` was
            # dropped per SPEC C2 (footer is now 4 labels: Model · Effort
            # · Permission · Info · Settings). Slot 4 will drop the now-
            # orphaned ``on_computer_info_label_requested`` handler in a
            # follow-up.
            yield DiagnosticsLabel(
                "info", id="diagnostics-label", classes="footer-label"
            )
            yield Static("·", classes="footer-sep")
            yield SettingsLabel("settings", id="settings-label", classes="footer-label")
            yield Static("", id="footer-spacer")
            yield ProcessIndicator(id="process-indicator", classes="hidden")
            yield AgentLabel("", id="agent-label", classes="footer-label hidden")
            yield ContextBar(id="context-bar")
            yield CPUBar(id="cpu-bar")
            yield Static("", id="branch-label", classes="footer-label")

    def watch_branch(self, value: str) -> None:
        """Update branch label when branch changes."""
        if label := self.query_one_optional("#branch-label", Static):
            label.update(f"⎇ {value}" if value else "")

    def watch_model(self, value: str) -> None:
        """Update model label when model changes.

        Also snaps the effort label to the new model's valid level set
        (SPEC C2 / Decision 5) so a user on Opus picking ``"max"`` and
        switching to Sonnet does not send an unsupported level to the
        SDK on the next turn. Mirrors the snap into the active agent
        so ``_make_options`` reads the new value live.
        """
        if label := self.query_one_optional("#model-label", ModelLabel):
            label.update(value if value else "")
        if eff := self.query_one_optional("#effort-label", EffortLabel):
            eff.set_available_levels(EffortLabel.levels_for_model(value))
            # Mirror the post-snap level back into the reactive + the
            # active agent so downstream readers see the corrected
            # value. set_available_levels already wrote the new level
            # into eff._effort via set_effort.
            self.effort = eff._effort
            app = self.app
            agent = getattr(app, "_agent", None)
            if agent is not None and hasattr(agent, "effort"):
                agent.effort = eff._effort

    def watch_effort(self, value: str) -> None:
        """Update effort label when the reactive changes.

        Acts as the bridge between external writers (agent switch,
        model change, settings re-apply) and the visible label. The
        EffortLabel's own ``on_click`` cycles also flow through here
        via the ``ancestor.effort = next_effort`` write to keep the
        reactive in sync, so this watcher must be idempotent.
        """
        if label := self.query_one_optional("#effort-label", EffortLabel):
            label.set_effort(value)

    def watch_permission_mode(self, value: str) -> None:
        """Update permission mode label when setting changes."""
        if label := self.query_one_optional(
            "#permission-mode-label", PermissionModeLabel
        ):
            if value == "planSwarm":
                label.update("Plan swarm")
                label.set_class(False, "active")
                label.set_class(False, "plan-mode")
                label.set_class(True, "plan-swarm-mode")
            elif value == "plan":
                label.update("Plan mode")
                label.set_class(False, "active")
                label.set_class(True, "plan-mode")
                label.set_class(False, "plan-swarm-mode")
            elif value == "auto":
                label.update("Auto: safe tools auto-approved")
                label.set_class(True, "active")
                label.set_class(False, "plan-mode")
                label.set_class(False, "plan-swarm-mode")
            elif value == "acceptEdits":
                label.update("Auto-edit: on")
                label.set_class(True, "active")
                label.set_class(False, "plan-mode")
                label.set_class(False, "plan-swarm-mode")
            elif value == "bypassPermissions":
                label.update("Bypass: all auto-approved")
                label.set_class(True, "active")
                label.set_class(False, "plan-mode")
                label.set_class(False, "plan-swarm-mode")
            else:  # default
                label.update("Auto-edit: off")
                label.set_class(False, "active")
                label.set_class(False, "plan-mode")
                label.set_class(False, "plan-swarm-mode")

    def update_processes(self, processes: list[BackgroundProcess]) -> None:
        """Update the process indicator."""
        if indicator := self.query_one_optional("#process-indicator", ProcessIndicator):
            indicator.update_processes(processes)

    def update_agent_label(self, name: str, visible: bool) -> None:
        """Update the agent label in the footer."""
        if label := self.query_one_optional("#agent-label", AgentLabel):
            label.update_agent(name, visible)

    def update_vi_mode(self, mode: ViMode | None, enabled: bool = True) -> None:
        """Update the vi-mode indicator."""
        if label := self.query_one_optional("#vi-mode-label", ViModeLabel):
            label.set_mode(mode, enabled)
