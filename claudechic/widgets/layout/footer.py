"""Custom footer widget."""

import asyncio

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Static

from claudechic.processes import BackgroundProcess
from claudechic.widgets.base.clickable import ClickableLabel
from claudechic.widgets.input.vi_mode import ViMode
from claudechic.widgets.layout.indicators import ContextBar, CPUBar, ProcessIndicator


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
    branch = reactive("")

    async def on_mount(self) -> None:
        self.branch = await get_git_branch()

    async def refresh_branch(self, cwd: str | None = None) -> None:
        """Update branch from given directory (async)."""
        self.branch = await get_git_branch(cwd)

    def compose(self) -> ComposeResult:
        with Horizontal(id="footer-content"):
            yield ViModeLabel("", id="vi-mode-label", classes="hidden")
            yield ModelLabel("", id="model-label", classes="footer-label")
            yield Static("·", classes="footer-sep")
            yield PermissionModeLabel(
                "Auto-edit: off", id="permission-mode-label", classes="footer-label"
            )
            yield Static("·", classes="footer-sep")
            yield DiagnosticsLabel(
                "session_info", id="diagnostics-label", classes="footer-label"
            )
            yield Static("·", classes="footer-sep")
            yield ComputerInfoLabel(
                "sys", id="computer-info-label", classes="footer-label"
            )
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
        """Update model label when model changes."""
        if label := self.query_one_optional("#model-label", ModelLabel):
            label.update(value if value else "")

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
                label.update("Auto: classifier-gated")
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
