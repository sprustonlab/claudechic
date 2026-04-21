"""Todo display widget for TodoWrite tool."""

from rich.text import Text
from textual.app import ComposeResult
from textual.message import Message
from textual.widgets import Static

from claudechic.enums import TodoStatus
from claudechic.widgets.primitives.button import Button


class TodoPanel(Static):
    """Sidebar panel for todo list - docked right when space allows."""

    can_focus = False

    class ClearFinished(Message):
        """Posted when user clicks the clear finished tasks button."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.todos: list[dict] = []

    def compose(self) -> ComposeResult:
        yield Static("Tasks", classes="todo-title")
        yield Button(
            "Clear finished",
            id="clear-finished-btn",
            classes="clear-finished-btn hidden",
        )

    def set_visible(self, visible: bool) -> None:
        """Control visibility (only shows if has todos and visible=True)."""
        if visible and self.todos:
            self.remove_class("hidden")
        else:
            self.add_class("hidden")

    def update_todos(self, todos: list[dict]) -> None:
        """Replace todos with new list. Visibility controlled by set_visible()."""
        self.todos = todos
        # Remove old items (keep title and button)
        for child in list(self.children):
            if isinstance(child, TodoItem):
                child.remove()
        # Add new items
        for todo in todos:
            self.mount(TodoItem(todo))
        # Show/hide clear button based on completed tasks
        self._update_clear_button()

    def _update_clear_button(self) -> None:
        """Show clear button only when completed tasks exist."""
        has_completed = any(t.get("status") == TodoStatus.COMPLETED for t in self.todos)
        try:
            btn = self.query_one("#clear-finished-btn", Button)
            if has_completed:
                btn.remove_class("hidden")
            else:
                btn.add_class("hidden")
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle clear finished button click."""
        if event.button.id == "clear-finished-btn":
            self.post_message(self.ClearFinished())


class TodoWidget(Static):
    """Inline display of todo list in chat stream."""

    can_focus = False

    def __init__(self, todos: list[dict]) -> None:
        super().__init__()
        self.todos = todos

    def compose(self) -> ComposeResult:
        for todo in self.todos:
            yield TodoItem(todo)

    def update_todos(self, todos: list[dict]) -> None:
        """Replace todos with new list."""
        self.todos = todos
        self.remove_children()
        for todo in todos:
            self.mount(TodoItem(todo))


class TodoItem(Static):
    """Single todo item with status icon."""

    can_focus = False

    ICONS = {
        TodoStatus.PENDING: "☐",
        TodoStatus.IN_PROGRESS: "◉",
        TodoStatus.COMPLETED: "✓",
    }

    def __init__(self, todo: dict) -> None:
        super().__init__()
        self.todo = todo
        self.add_class(todo.get("status", TodoStatus.PENDING))

    def render(self) -> Text:
        status = self.todo.get("status", TodoStatus.PENDING)
        icon = self.ICONS.get(status, "?")

        # Show activeForm for in_progress, content otherwise
        if status == TodoStatus.IN_PROGRESS:
            label = self.todo.get("activeForm", self.todo.get("content", ""))
        else:
            label = self.todo.get("content", "")

        result = Text()
        if status == TodoStatus.COMPLETED:
            result.append(f"{icon} ", style="green")
            result.append(label, style="strike dim")
        elif status == TodoStatus.IN_PROGRESS:
            result.append(f"{icon} ", style="yellow bold")
            result.append(label, style="yellow")
        else:  # pending
            result.append(f"{icon} ", style="dim")
            result.append(label, style="dim")

        return result
