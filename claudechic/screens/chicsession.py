"""Chicsession picker screen for /chicsession restore and workflow activation."""

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Label, ListItem, ListView, Input, Static

from claudechic.chicsessions import ChicsessionManager


class NewSessionItem(ListItem):
    """Special list item for creating a new chicsession."""

    DEFAULT_CSS = """
    NewSessionItem {
        pointer: pointer;
    }
    """

    def __init__(self, default_name: str) -> None:
        super().__init__()
        self.default_name = default_name

    def compose(self) -> ComposeResult:
        yield Label("New session", classes="chicsession-title")
        yield Label(
            f"Type a name in the search bar, or use default: {self.default_name}",
            classes="chicsession-meta",
        )


class ChicsessionItem(ListItem):
    """A chicsession entry in the picker list."""

    DEFAULT_CSS = """
    ChicsessionItem {
        pointer: pointer;
    }
    """

    def __init__(self, name: str, agent_count: int, agent_names: list[str],
                 *, workflow_match: bool = False) -> None:
        super().__init__()
        self.chicsession_name = name
        self.agent_count = agent_count
        self.agent_names = agent_names
        self.workflow_match = workflow_match

    def compose(self) -> ComposeResult:
        yield Label(self.chicsession_name, classes="chicsession-title")
        agents_str = ", ".join(self.agent_names) if self.agent_names else "\u2014"
        meta = f"{self.agent_count} agent{'s' if self.agent_count != 1 else ''} \u00b7 {agents_str}"
        if self.workflow_match:
            meta += " [matching workflow]"
        yield Label(meta, classes="chicsession-meta")


class ChicsessionScreen(Screen[str | None]):
    """Full-screen picker for restoring a chicsession.

    Args:
        root_dir: Root directory for .chicsessions/ storage.
        workflow_id: If set, enables workflow-activation mode with a
            "New session" item at the top and returns "new:<name>"
            for new sessions or the chicsession name for existing ones.
    """

    def __init__(self, root_dir: Path, workflow_id: str | None = None) -> None:
        super().__init__()
        self._root_dir = root_dir
        self._workflow_id = workflow_id

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
    ]

    DEFAULT_CSS = """
    ChicsessionScreen {
        background: $background;
        align: center top;
    }

    ChicsessionScreen #chicsession-container {
        width: 100%;
        max-width: 80;
        height: 100%;
        padding: 1 2;
    }

    ChicsessionScreen #chicsession-title {
        height: 1;
        margin-bottom: 1;
        text-style: bold;
    }

    ChicsessionScreen #chicsession-search {
        height: 3;
        margin-bottom: 1;
    }

    ChicsessionScreen #chicsession-list,
    ChicsessionScreen #chicsession-list:focus {
        height: 1fr;
        background: transparent;
    }

    ChicsessionScreen #chicsession-list > ListItem {
        padding: 0 0 0 1;
        height: auto;
        margin: 0 0 1 0;
        border-left: tall $panel;
    }

    ChicsessionScreen #chicsession-list > ListItem:hover,
    ChicsessionScreen #chicsession-list > ListItem.-highlight {
        background: $surface-darken-1;
        border-left: tall $primary;
    }

    ChicsessionScreen .chicsession-meta {
        color: $text-muted;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="chicsession-container"):
            if self._workflow_id:
                title_text = f"Session for workflow '{self._workflow_id}'"
                placeholder = f"Search or type new session name (default: {self._workflow_id})..."
            else:
                title_text = "Restore Chicsession"
                placeholder = "Search chicsessions..."
            yield Static(title_text, id="chicsession-title")
            yield Input(placeholder=placeholder, id="chicsession-search")
            yield ListView(id="chicsession-list")

    def on_mount(self) -> None:
        self._update_list("")
        self.query_one("#chicsession-search", Input).focus()

    def on_key(self, event) -> None:
        """Forward navigation keys to list."""
        list_view = self.query_one("#chicsession-list", ListView)
        if event.key == "down":
            list_view.action_cursor_down()
            event.prevent_default()
        elif event.key == "up":
            list_view.action_cursor_up()
            event.prevent_default()

    def action_go_back(self) -> None:
        self.dismiss(None)

    def _update_list(self, search: str) -> None:
        mgr = ChicsessionManager(self._root_dir)
        names = mgr.list_chicsessions()

        search_lower = search.lower()
        if search_lower:
            names = [n for n in names if search_lower in n.lower()]

        list_view = self.query_one("#chicsession-list", ListView)
        list_view.clear()

        title = self.query_one("#chicsession-title", Static)

        # In workflow mode, add the "New session" item at the top
        if self._workflow_id:
            new_name = search.strip() if search.strip() else self._workflow_id
            list_view.append(NewSessionItem(new_name))

            count_label = f" + {len(names)} existing" if names else ""
            title.update(
                f"Session for workflow '{self._workflow_id}' (new{count_label})"
            )
        else:
            if not names:
                title.update("No chicsessions found")
                return
            title.update(f"Restore Chicsession ({len(names)})")

        for cs_name in names:
            try:
                cs = mgr.load(cs_name)
                agent_names = [a.name for a in cs.agents]
                workflow_match = bool(
                    self._workflow_id
                    and cs.workflow_state
                    and cs.workflow_state.get("workflow_id") == self._workflow_id
                )
                list_view.append(
                    ChicsessionItem(
                        cs_name, len(cs.agents), agent_names,
                        workflow_match=workflow_match,
                    )
                )
            except (ValueError, FileNotFoundError):
                list_view.append(ChicsessionItem(cs_name, 0, []))

        # Select first item
        if list_view.children:
            list_view.index = 0

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "chicsession-search":
            self._update_list(event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "chicsession-search":
            list_view = self.query_one("#chicsession-list", ListView)
            if list_view.index is not None and list_view.highlighted_child:
                item = list_view.highlighted_child
                list_view.post_message(
                    ListView.Selected(list_view, item, list_view.index)
                )

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if isinstance(event.item, NewSessionItem):
            # Return "new:<name>" — caller parses the prefix
            search = self.query_one("#chicsession-search", Input).value.strip()
            name = search if search else event.item.default_name
            self.dismiss(f"new:{name}")
        elif isinstance(event.item, ChicsessionItem):
            if self._workflow_id:
                # In workflow mode, return "resume:<name>" for existing sessions
                self.dismiss(f"resume:{event.item.chicsession_name}")
            else:
                # In restore mode, return the name directly (backward compat)
                self.dismiss(event.item.chicsession_name)
