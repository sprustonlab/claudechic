"""Agent Switcher modal -- Ctrl+G to open, search and switch agents."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Input, Label, ListItem, ListView

if TYPE_CHECKING:
    from claudechic.enums import AgentStatus


class AgentSwitcherItem(ListItem):
    """A single agent entry in the switcher list."""

    DEFAULT_CSS = """
    AgentSwitcherItem {
        height: auto;
        padding: 0 1;
    }
    """

    def __init__(self, agent_id: str, name: str, status: str = "idle") -> None:
        super().__init__()
        self.agent_id = agent_id
        self.agent_name = name
        self.agent_status = status

    def compose(self) -> ComposeResult:
        indicator = "*" if self.agent_status == "busy" else "o"
        yield Label(f"  {indicator} {self.agent_name}", classes="agent-switcher-name")
        yield Label(f"({self.agent_status})", classes="agent-switcher-status")


class AgentSwitcher(ModalScreen[str | None]):
    """Modal overlay for quick agent switching.

    Displays a searchable list of agents. Enter selects, Escape dismisses.
    Dismissed with the agent_id string or None if cancelled.
    """

    BINDINGS = [
        Binding("escape", "dismiss_switcher", "Close"),
    ]

    DEFAULT_CSS = """
    AgentSwitcher {
        align: center middle;
    }

    AgentSwitcher #agent-switcher-container {
        width: 50;
        max-height: 20;
        background: $surface;
        border: tall $primary;
        padding: 1;
    }

    AgentSwitcher #agent-search {
        height: 3;
        margin-bottom: 1;
    }

    AgentSwitcher #agent-results {
        height: 1fr;
        background: transparent;
    }

    AgentSwitcher #agent-results > ListItem {
        padding: 0 0 0 1;
        height: auto;
    }

    AgentSwitcher #agent-results > ListItem:hover,
    AgentSwitcher #agent-results > ListItem.-highlight {
        background: $surface-darken-1;
        border-left: tall $primary;
    }

    AgentSwitcher .agent-switcher-status {
        color: $text-muted;
    }
    """

    class AgentSelected(Message):
        """Emitted when user selects an agent."""

        def __init__(self, agent_id: str) -> None:
            super().__init__()
            self.agent_id = agent_id

    def __init__(
        self,
        agents: "Sequence[tuple[str, str, AgentStatus | str]]",
    ) -> None:
        """Initialize with agent list.

        Args:
            agents: List of (agent_id, name, status) tuples. ``status`` is
                an ``AgentStatus`` (StrEnum) or a plain str; both work
                identically at runtime since ``AgentStatus`` is a str.
        """
        super().__init__()
        self._agents = agents

    def compose(self) -> ComposeResult:
        with Vertical(id="agent-switcher-container"):
            yield Input(placeholder="search agents...", id="agent-search")
            yield ListView(id="agent-results")

    def on_mount(self) -> None:
        self._update_list("")
        self.query_one("#agent-search", Input).focus()

    def on_key(self, event) -> None:
        """Forward navigation keys from search input to list."""
        list_view = self.query_one("#agent-results", ListView)
        if event.key == "down":
            list_view.action_cursor_down()
            event.prevent_default()
        elif event.key == "up":
            list_view.action_cursor_up()
            event.prevent_default()

    def _update_list(self, search: str) -> None:
        """Rebuild the agent list with optional fuzzy filter."""
        list_view = self.query_one("#agent-results", ListView)
        list_view.clear()

        search_lower = search.lower()
        for agent_id, name, status in self._agents:
            if search_lower and search_lower not in name.lower():
                continue
            list_view.append(AgentSwitcherItem(agent_id, name, status))

        if list_view.children:
            list_view.index = 0

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "agent-search":
            self._update_list(event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "agent-search":
            list_view = self.query_one("#agent-results", ListView)
            if list_view.index is not None and list_view.highlighted_child:
                item = list_view.highlighted_child
                list_view.post_message(
                    ListView.Selected(list_view, item, list_view.index)
                )

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if isinstance(event.item, AgentSwitcherItem):
            self.dismiss(event.item.agent_id)

    def action_dismiss_switcher(self) -> None:
        self.dismiss(None)
