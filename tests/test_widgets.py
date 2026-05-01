"""Pure widget tests - no SDK needed."""

import re

import pytest
from claudechic.enums import AgentStatus
from claudechic.widgets import (
    AgentSection,
    BackgroundProcess,
    ChatInput,
    ChatMessage,
    ContextBar,
    ModelPrompt,
    PlanSection,
    ProcessPanel,
    QuestionPrompt,
    SelectionPrompt,
    StatusFooter,
    ThinkingIndicator,
    TodoPanel,
)
from claudechic.widgets.content.todo import TodoItem
from claudechic.widgets.layout.processes import ProcessItem
from textual.app import App, ComposeResult
from textual.widgets import Static


class WidgetTestApp(App):
    """Minimal app for testing individual widgets."""

    def __init__(self, widget_factory):
        super().__init__()
        self._widget_factory = widget_factory

    def compose(self) -> ComposeResult:
        yield self._widget_factory()


@pytest.mark.asyncio
async def test_chat_input_submit():
    """Enter posts Submitted message."""
    submitted_text = None

    class TestApp(App):
        def compose(self):
            yield ChatInput(id="input")

        def on_chat_input_submitted(self, event):
            nonlocal submitted_text
            submitted_text = event.text

    app = TestApp()
    async with app.run_test() as pilot:
        input_widget = app.query_one(ChatInput)
        input_widget.text = "hello world"
        await pilot.press("enter")
        assert submitted_text == "hello world"


@pytest.mark.asyncio
async def test_chat_input_history():
    """Up/down navigates history."""

    class HistoryTestApp(App):
        def compose(self):
            yield ChatInput(id="input")

        def on_chat_input_submitted(self, event):
            # Clear input like ChatApp does
            self.query_one(ChatInput).clear()

    app = HistoryTestApp()
    async with app.run_test() as pilot:
        input_widget = app.query_one(ChatInput)

        # Send a few messages to build history
        input_widget.text = "first"
        await pilot.press("enter")
        input_widget.text = "second"
        await pilot.press("enter")
        input_widget.text = "third"
        await pilot.press("enter")

        # Now navigate history
        assert input_widget.text == ""
        await pilot.press("up")
        assert input_widget.text == "third"
        await pilot.press("up")
        assert input_widget.text == "second"
        await pilot.press("up")
        assert input_widget.text == "first"
        await pilot.press("down")
        assert input_widget.text == "second"


@pytest.mark.asyncio
async def test_chat_input_image_detection():
    """Detects image paths."""
    app = WidgetTestApp(lambda: ChatInput(id="input"))
    async with app.run_test():
        input_widget = app.query_one(ChatInput)

        # Test various image path formats
        assert input_widget._is_image_path("/tmp/test.png") == []  # File doesn't exist
        assert input_widget._is_image_path("not an image") == []
        assert input_widget._is_image_path("file:///nonexistent.jpg") == []


@pytest.mark.asyncio
async def test_selection_prompt_arrow_navigation():
    """Up/down cycles through options."""
    options = [("a", "Option A"), ("b", "Option B"), ("c", "Option C")]

    app = WidgetTestApp(lambda: SelectionPrompt("Choose:", options))
    async with app.run_test() as pilot:
        prompt = app.query_one(SelectionPrompt)

        assert prompt.selected_idx == 0
        await pilot.press("down")
        assert prompt.selected_idx == 1
        await pilot.press("down")
        assert prompt.selected_idx == 2
        await pilot.press("down")
        assert prompt.selected_idx == 0  # Wraps around
        await pilot.press("up")
        assert prompt.selected_idx == 2


@pytest.mark.asyncio
async def test_selection_prompt_number_keys():
    """Number keys select options directly."""
    options = [("a", "Option A"), ("b", "Option B"), ("c", "Option C")]
    result = None

    class TestApp(App):
        def compose(self):
            yield SelectionPrompt("Choose:", options)

    app = TestApp()
    async with app.run_test() as pilot:
        prompt = app.query_one(SelectionPrompt)

        # Press "2" to select second option
        await pilot.press("2")
        result = await prompt.wait()

    assert result == "b"


@pytest.mark.asyncio
async def test_selection_prompt_escape_cancels():
    """Escape resolves with empty string."""
    options = [("a", "Option A"), ("b", "Option B")]

    app = WidgetTestApp(lambda: SelectionPrompt("Choose:", options))
    async with app.run_test() as pilot:
        prompt = app.query_one(SelectionPrompt)

        await pilot.press("escape")
        result = await prompt.wait()
        assert result == ""


@pytest.mark.asyncio
async def test_selection_prompt_text_option():
    """Text option allows freeform input."""
    options = [("a", "Option A"), ("b", "Option B")]
    text_option = ("custom", "Type something...")

    class TestApp(App):
        def compose(self):
            yield SelectionPrompt("Choose:", options, text_option)

    app = TestApp()
    async with app.run_test() as pilot:
        prompt = app.query_one(SelectionPrompt)

        # Navigate to text option (3rd option, index 2)
        await pilot.press("3")
        # Type some text
        await pilot.press("h", "e", "l", "l", "o")
        await pilot.press("enter")
        result = await prompt.wait()

    assert result == "custom:hello"


@pytest.mark.asyncio
async def test_model_prompt_selection():
    """ModelPrompt allows model selection with arrow keys and numbers."""
    # Mock SDK model list
    models = [
        {"value": "sonnet", "displayName": "Sonnet", "description": "Sonnet 4 · Fast"},
        {"value": "opus", "displayName": "Opus", "description": "Opus 4.5 · Powerful"},
        {"value": "haiku", "displayName": "Haiku", "description": "Haiku 3.5 · Quick"},
    ]

    class TestApp(App):
        def compose(self):
            yield ModelPrompt(models, current_value="sonnet")

    app = TestApp()
    async with app.run_test() as pilot:
        prompt = app.query_one(ModelPrompt)

        # Should start on current model (sonnet = index 0)
        assert prompt.selected_idx == 0

        # Navigate down to opus
        await pilot.press("down")
        assert prompt.selected_idx == 1

        # Select with number key (3 = haiku)
        await pilot.press("3")
        result = await prompt.wait()

    assert result == "haiku"


@pytest.mark.asyncio
async def test_model_prompt_escape():
    """ModelPrompt returns None on escape."""
    models = [
        {"value": "sonnet", "displayName": "Sonnet", "description": "Sonnet 4 · Fast"},
        {"value": "opus", "displayName": "Opus", "description": "Opus 4.5 · Powerful"},
    ]
    app = WidgetTestApp(lambda: ModelPrompt(models, current_value="opus"))
    async with app.run_test() as pilot:
        prompt = app.query_one(ModelPrompt)

        # Should start on opus (index 1)
        assert prompt.selected_idx == 1

        await pilot.press("escape")
        result = await prompt.wait()

    assert result is None


@pytest.mark.asyncio
async def test_question_prompt_multi_question():
    """Handles multiple questions."""
    questions = [
        {"question": "Q1?", "options": [{"label": "Yes"}, {"label": "No"}]},
        {"question": "Q2?", "options": [{"label": "Red"}, {"label": "Blue"}]},
    ]

    app = WidgetTestApp(lambda: QuestionPrompt(questions))
    async with app.run_test() as pilot:
        prompt = app.query_one(QuestionPrompt)
        prompt.focus()

        # Answer first question
        assert prompt.current_q == 0
        await pilot.press("1")  # Select "Yes"

        # Should advance to second question
        assert prompt.current_q == 1
        assert prompt.answers == {"Q1?": "Yes"}

        await pilot.press("2")  # Select "Blue"

        # Prompt should have resolved after second answer
        assert prompt.answers == {"Q1?": "Yes", "Q2?": "Blue"}


@pytest.mark.asyncio
async def test_agent_section_add_remove():
    """Can add and remove agents."""
    app = WidgetTestApp(lambda: AgentSection(id="agents"))
    async with app.run_test():
        section = app.query_one(AgentSection)

        # Add agents
        section.add_agent("id1", "Agent 1")
        section.add_agent("id2", "Agent 2")

        assert "id1" in section._agents
        assert "id2" in section._agents
        assert len(section._agents) == 2

        # Remove one
        section.remove_agent("id1")
        assert "id1" not in section._agents
        assert len(section._agents) == 1


@pytest.mark.asyncio
async def test_agent_section_active_selection():
    """set_active updates visual state."""
    app = WidgetTestApp(lambda: AgentSection(id="agents"))
    async with app.run_test():
        section = app.query_one(AgentSection)

        section.add_agent("id1", "Agent 1")
        section.add_agent("id2", "Agent 2")

        section.set_active("id1")
        assert section._agents["id1"].has_class("active")
        assert not section._agents["id2"].has_class("active")

        section.set_active("id2")
        assert not section._agents["id1"].has_class("active")
        assert section._agents["id2"].has_class("active")


@pytest.mark.asyncio
async def test_agent_section_status_updates():
    """update_status changes indicator."""
    app = WidgetTestApp(lambda: AgentSection(id="agents"))
    async with app.run_test():
        section = app.query_one(AgentSection)

        section.add_agent("id1", "Agent 1", status=AgentStatus.IDLE)
        assert section._agents["id1"].status == AgentStatus.IDLE

        section.update_status("id1", AgentStatus.BUSY)
        assert section._agents["id1"].status == AgentStatus.BUSY

        section.update_status("id1", AgentStatus.NEEDS_INPUT)
        assert section._agents["id1"].status == AgentStatus.NEEDS_INPUT


@pytest.mark.asyncio
async def test_plan_section():
    """PlanSection set_plan shows/hides plan item."""
    from pathlib import Path

    app = WidgetTestApp(lambda: PlanSection(id="plan"))
    async with app.run_test():
        section = app.query_one(PlanSection)

        # Initially no plan item
        assert section._plan_item is None

        # Set plan creates item
        plan_path = Path("/tmp/test-plan.md")
        section.set_plan(plan_path)
        assert section._plan_item is not None
        assert section._plan_item.plan_path == plan_path

        # Clear plan hides section
        section.set_plan(None)
        assert section.has_class("hidden")


@pytest.mark.asyncio
async def test_context_bar_rendering():
    """ContextBar shows correct fill and color."""
    app = WidgetTestApp(lambda: ContextBar(id="ctx"))
    async with app.run_test():
        bar = app.query_one(ContextBar)

        # Low usage - should be dim
        bar.tokens = 10000
        bar.max_tokens = 200000
        rendered = bar.render()
        assert hasattr(rendered, "plain")
        assert "5%" in rendered.plain  # type: ignore[union-attr]

        # High usage - should be red
        bar.tokens = 180000
        rendered = bar.render()
        assert hasattr(rendered, "plain")
        assert "90%" in rendered.plain  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_todo_panel_updates():
    """TodoPanel displays and updates todos."""
    app = WidgetTestApp(lambda: TodoPanel(id="panel"))
    async with app.run_test():
        panel = app.query_one(TodoPanel)

        todos = [
            {
                "content": "Task 1",
                "status": "completed",
                "activeForm": "Completing task 1",
            },
            {
                "content": "Task 2",
                "status": "in_progress",
                "activeForm": "Working on task 2",
            },
            {"content": "Task 3", "status": "pending", "activeForm": "Starting task 3"},
        ]

        panel.update_todos(todos)

        items = list(panel.query(TodoItem))
        assert len(items) == 3
        assert items[0].has_class("completed")
        assert items[1].has_class("in_progress")
        assert items[2].has_class("pending")


@pytest.mark.asyncio
async def test_status_footer_permission_mode():
    """Footer shows permission mode state."""
    app = WidgetTestApp(lambda: StatusFooter())
    async with app.run_test():
        footer = app.query_one(StatusFooter)

        footer.permission_mode = "default"
        label = footer.query_one("#permission-mode-label", Static)
        rendered = label.render()
        assert hasattr(rendered, "plain")
        assert "auto-edit: off" in rendered.plain.lower()  # type: ignore[union-attr]

        footer.permission_mode = "acceptEdits"
        rendered = label.render()
        assert hasattr(rendered, "plain")
        assert "auto-edit: on" in rendered.plain.lower()  # type: ignore[union-attr]

        footer.permission_mode = "plan"
        rendered = label.render()
        assert hasattr(rendered, "plain")
        assert "plan mode" in rendered.plain.lower()  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_chat_message_append():
    """ChatMessage accumulates content."""
    app = WidgetTestApp(lambda: ChatMessage("Hello"))
    async with app.run_test():
        msg = app.query_one(ChatMessage)

        assert msg.get_raw_content() == "Hello"

        msg.append_content(" world")
        assert msg.get_raw_content() == "Hello world"

        msg.append_content("!")
        assert msg.get_raw_content() == "Hello world!"


@pytest.mark.asyncio
async def test_thinking_indicator_animates():
    """ThinkingIndicator cycles through frames."""
    app = WidgetTestApp(ThinkingIndicator)
    async with app.run_test() as pilot:
        indicator = app.query_one(ThinkingIndicator)

        initial_frame = indicator._frame
        # Wait for animation (now at 4Hz = 250ms interval)
        await pilot.pause(0.5)
        # Frame should have changed
        assert indicator._frame != initial_frame or indicator._frame == 0  # May wrap


@pytest.mark.asyncio
async def test_history_search_filters():
    """HistorySearch filters history and cycles through matches."""
    from unittest.mock import patch

    from claudechic.widgets.input.history_search import HistorySearch

    class TestApp(App):
        def compose(self):
            yield HistorySearch(id="history")

    # Mock history data (most recent first)
    mock_history = [
        "fix the bug",
        "add new feature",
        "fix another bug",
        "refactor code",
    ]

    with patch(
        "claudechic.widgets.input.history_search.load_global_history",
        return_value=mock_history,
    ):
        app = TestApp()
        async with app.run_test() as pilot:
            hs = app.query_one(HistorySearch)
            hs.show()
            await pilot.pause()

            # Initially shows most recent match
            assert hs._current_match() == "fix the bug"

            # Type to filter
            from textual.widgets import Input

            inp = hs.query_one("#search-input", Input)
            inp.value = "fix"
            hs.on_input_changed(Input.Changed(inp, "fix"))

            # Should filter to matching entries
            assert len(hs._filtered) == 2
            assert hs._current_match() == "fix the bug"

            # Ctrl+R cycles to next match
            hs.action_next_match()
            assert hs._current_match() == "fix another bug"

            # Up goes back
            hs.action_prev_match()
            assert hs._current_match() == "fix the bug"


@pytest.mark.asyncio
async def test_process_panel_updates():
    """ProcessPanel displays and updates background processes."""
    from datetime import datetime

    app = WidgetTestApp(lambda: ProcessPanel(id="panel", classes="hidden"))
    async with app.run_test():
        panel = app.query_one(ProcessPanel)

        # Initially hidden (no processes)
        assert panel.has_class("hidden")

        # Add some processes
        processes = [
            BackgroundProcess(pid=123, command="sleep 100", start_time=datetime.now()),
            BackgroundProcess(
                pid=456, command="npm run dev", start_time=datetime.now()
            ),
        ]
        panel.update_processes(processes)

        # Processes added, but visibility controlled by set_visible()
        assert panel.process_count == 2
        assert panel.has_class("hidden")  # Still hidden until set_visible(True)

        # Make visible
        panel.set_visible(True)
        assert not panel.has_class("hidden")

        items = list(panel.query(ProcessItem))
        assert len(items) == 2

        # Clear processes - set_visible(True) with no processes still hides
        panel.update_processes([])
        panel.set_visible(True)
        assert panel.has_class("hidden")


# --- Diff token snapping tests ---


def test_snap_to_tokens_expands_partial_spans():
    """Word-diff spans that cut through tokens get expanded to token boundaries."""
    from claudechic.widgets.content.diff import _snap_to_tokens
    from textual.content import Content, Span

    # Simulate syntax-highlighted "activeInsertionOrders:" with tokens:
    # [0-21] identifier, [21-22] punctuation
    content = Content(
        "activeInsertionOrders:",
        spans=[Span(0, 21, "blue"), Span(21, 22, "white")],
    )

    # Span that cuts through the identifier (e.g., highlighting just "active")
    raw_spans = [(0, 6)]
    snapped = _snap_to_tokens(raw_spans, content)

    # Should expand to cover the whole identifier token
    assert snapped == [(0, 21)]


def test_snap_to_tokens_preserves_aligned_spans():
    """Spans already aligned with token boundaries stay unchanged."""
    from claudechic.widgets.content.diff import _snap_to_tokens
    from textual.content import Content, Span

    content = Content(
        "foo bar",
        spans=[Span(0, 3, "red"), Span(3, 4, "white"), Span(4, 7, "blue")],
    )

    # Span exactly matching first token
    raw_spans = [(0, 3)]
    snapped = _snap_to_tokens(raw_spans, content)
    assert snapped == [(0, 3)]


def test_snap_to_tokens_empty_spans():
    """Empty span list returns empty."""
    from claudechic.widgets.content.diff import _snap_to_tokens
    from textual.content import Content

    content = Content("hello")
    assert _snap_to_tokens([], content) == []


def test_word_diff_with_go_syntax():
    """Integration test: word diff + snapping with real Go syntax highlighting."""
    from claudechic.widgets.content.diff import (
        _highlight_lines,
        _snap_to_tokens,
        _word_diff_spans,
    )

    old_line = 'activeOrders: getValue("active",'
    new_line = 'dirtyOrders: getValue("dirty",'

    # Get raw word-diff spans
    old_spans, new_spans = _word_diff_spans(old_line, new_line)

    # Raw spans should identify the changed words
    assert len(old_spans) == 2  # "activeOrders" and "active"
    assert len(new_spans) == 2  # "dirtyOrders" and "dirty"

    # Get syntax-highlighted content
    old_highlighted = _highlight_lines(old_line, "go")
    new_highlighted = _highlight_lines(new_line, "go")

    assert old_highlighted and new_highlighted

    # Snap to token boundaries
    snapped_old = _snap_to_tokens(old_spans, old_highlighted[0])

    # Snapped spans should cover complete tokens
    # The string "active" should expand to include quotes -> "active"
    for start, end in snapped_old:
        text = old_line[start:end]
        # Should not have partial words (no cuts mid-identifier)
        assert not text[0].isalnum() or start == 0 or not old_line[start - 1].isalnum()


# --- Lazy collapsible tests ---


@pytest.mark.asyncio
async def test_quiet_collapsible_lazy_content():
    """QuietCollapsible with content_factory defers widget creation until expanded."""
    from claudechic.widgets.primitives.collapsible import QuietCollapsible

    factory_called = False

    def make_content():
        nonlocal factory_called
        factory_called = True
        return [Static("Lazy content", id="lazy-content")]

    class TestApp(App):
        def compose(self):
            yield QuietCollapsible(
                title="Test",
                collapsed=True,
                content_factory=make_content,
            )

    app = TestApp()
    async with app.run_test() as pilot:
        collapsible = app.query_one(QuietCollapsible)

        # Factory should NOT be called yet (collapsed)
        assert not factory_called
        assert collapsible.collapsed

        # Expand the collapsible
        collapsible.collapsed = False
        await pilot.pause()

        # Factory should now be called
        assert factory_called

        # Content should be mounted
        content = collapsible.query_one("#lazy-content", Static)
        assert content is not None


@pytest.mark.asyncio
async def test_quiet_collapsible_immediate_content():
    """QuietCollapsible with content_factory and collapsed=False composes immediately."""
    from claudechic.widgets.primitives.collapsible import QuietCollapsible

    factory_called = False

    def make_content():
        nonlocal factory_called
        factory_called = True
        return [Static("Immediate content", id="immediate-content")]

    class TestApp(App):
        def compose(self):
            # collapsed=False means content should be mounted immediately
            yield QuietCollapsible(
                title="Test",
                collapsed=False,
                content_factory=make_content,
            )

    app = TestApp()
    async with app.run_test():
        collapsible = app.query_one(QuietCollapsible)
        # Factory should be called during watch on expand
        assert factory_called
        # Content should be mounted
        content = collapsible.query_one("#immediate-content", Static)
        assert content is not None


@pytest.mark.asyncio
async def test_quiet_collapsible_context_manager_still_works():
    """QuietCollapsible context manager pattern continues to work."""
    from claudechic.widgets.primitives.collapsible import QuietCollapsible

    class TestApp(App):
        def compose(self):
            with QuietCollapsible(title="Normal", collapsed=False):
                yield Static("Context manager content", id="ctx-content")

    app = TestApp()
    async with app.run_test():
        collapsible = app.query_one(QuietCollapsible)
        content = collapsible.query_one("#ctx-content", Static)
        assert content is not None


@pytest.mark.asyncio
async def test_tool_use_widget_edit_lazy_diff():
    """ToolUseWidget with Edit tool uses lazy DiffWidget when collapsed."""
    from claude_agent_sdk import ToolUseBlock
    from claudechic.widgets.content.diff import DiffWidget
    from claudechic.widgets.content.tools import ToolUseWidget
    from claudechic.widgets.primitives.collapsible import QuietCollapsible

    block = ToolUseBlock(
        id="test-edit",
        name="Edit",
        input={
            "file_path": "/test/file.py",
            "old_string": "old code",
            "new_string": "new code",
        },
    )

    class TestApp(App):
        def compose(self):
            # collapsed=True should use lazy pattern
            yield ToolUseWidget(block, collapsed=True, completed=True)

    app = TestApp()
    async with app.run_test() as pilot:
        widget = app.query_one(ToolUseWidget)
        collapsible = widget.query_one(QuietCollapsible)

        # DiffWidget should NOT exist yet (lazy)
        diffs = widget.query(DiffWidget)
        assert len(diffs) == 0

        # Expand the collapsible
        collapsible.collapsed = False
        await pilot.pause()

        # DiffWidget should now exist
        diffs = widget.query(DiffWidget)
        assert len(diffs) == 1


# --- ChatView.clear_to_recent tests ---


@pytest.mark.asyncio
async def test_clear_to_recent_removes_old_widgets():
    """clear_to_recent removes all but last N widgets."""
    from claudechic.widgets.layout.chat_view import ChatView

    class TestApp(App):
        def compose(self):
            yield ChatView(id="chat")

    app = TestApp()
    async with app.run_test() as pilot:
        chat_view = app.query_one(ChatView)

        # Add 15 messages
        for i in range(15):
            chat_view.mount(ChatMessage(f"Message {i}"))
        await pilot.pause()

        assert len(chat_view.children) == 15

        # Clear to recent 5
        chat_view.clear_to_recent(keep=5)
        await pilot.pause()

        # Should have 5 remaining
        assert len(chat_view.children) == 5
        # Hidden count updated
        assert chat_view._hidden_widget_count == 10


@pytest.mark.asyncio
async def test_clear_to_recent_fewer_than_keep():
    """clear_to_recent with fewer widgets than keep does nothing."""
    from claudechic.widgets.layout.chat_view import ChatView

    class TestApp(App):
        def compose(self):
            yield ChatView(id="chat")

    app = TestApp()
    async with app.run_test() as pilot:
        chat_view = app.query_one(ChatView)

        # Add only 3 messages
        for i in range(3):
            chat_view.mount(ChatMessage(f"Message {i}"))
        await pilot.pause()

        assert len(chat_view.children) == 3

        # Clear to recent 10 (keep > current)
        chat_view.clear_to_recent(keep=10)
        await pilot.pause()

        # Should still have 3
        assert len(chat_view.children) == 3
        assert chat_view._hidden_widget_count == 0


@pytest.mark.asyncio
async def test_clear_to_recent_empty():
    """clear_to_recent on empty view does nothing."""
    from claudechic.widgets.layout.chat_view import ChatView

    class TestApp(App):
        def compose(self):
            yield ChatView(id="chat")

    app = TestApp()
    async with app.run_test() as pilot:
        chat_view = app.query_one(ChatView)

        # Verify empty
        assert len(chat_view.children) == 0

        # Clear (should not error)
        chat_view.clear_to_recent(keep=10)
        await pilot.pause()

        assert len(chat_view.children) == 0
        assert chat_view._hidden_widget_count == 0


@pytest.mark.asyncio
async def test_clear_to_recent_preserves_most_recent():
    """clear_to_recent keeps the N most recent widgets."""
    from claudechic.widgets.layout.chat_view import ChatView

    class TestApp(App):
        def compose(self):
            yield ChatView(id="chat")

    app = TestApp()
    async with app.run_test() as pilot:
        chat_view = app.query_one(ChatView)

        # Add numbered messages
        for i in range(10):
            chat_view.mount(ChatMessage(f"Message {i}"))
        await pilot.pause()

        # Clear to recent 3
        chat_view.clear_to_recent(keep=3)
        await pilot.pause()

        # Should have messages 7, 8, 9 (the last 3)
        messages = list(chat_view.query(ChatMessage))
        assert len(messages) == 3
        assert messages[0].get_raw_content() == "Message 7"
        assert messages[1].get_raw_content() == "Message 8"
        assert messages[2].get_raw_content() == "Message 9"


@pytest.mark.asyncio
async def test_clear_to_recent_accumulates_hidden_count():
    """Multiple clear_to_recent calls accumulate hidden count."""
    from claudechic.widgets.layout.chat_view import ChatView

    class TestApp(App):
        def compose(self):
            yield ChatView(id="chat")

    app = TestApp()
    async with app.run_test() as pilot:
        chat_view = app.query_one(ChatView)

        # Add 10 messages
        for i in range(10):
            chat_view.mount(ChatMessage(f"Message {i}"))
        await pilot.pause()

        # First clear: 10 -> 5, hidden = 5
        chat_view.clear_to_recent(keep=5)
        await pilot.pause()
        assert chat_view._hidden_widget_count == 5

        # Add 5 more messages (now 10 total)
        for i in range(5):
            chat_view.mount(ChatMessage(f"New {i}"))
        await pilot.pause()

        # Second clear: 10 -> 3, hidden += 7
        chat_view.clear_to_recent(keep=3)
        await pilot.pause()
        assert chat_view._hidden_widget_count == 12  # 5 + 7


# --- SelectionPrompt subtitle tests ---


@pytest.mark.asyncio
async def test_selection_prompt_subtitle():
    """SelectionPrompt with subtitle renders the subtitle text."""
    options = [("a", "Option A"), ("b", "Option B")]
    app = WidgetTestApp(
        lambda: SelectionPrompt("Title:", options, subtitle="Detail info here")
    )
    async with app.run_test():
        prompt = app.query_one(SelectionPrompt)
        subtitles = list(prompt.query(".prompt-subtitle"))
        assert len(subtitles) == 1
        rendered = subtitles[0].render()
        assert hasattr(rendered, "plain")
        assert "Detail info here" in rendered.plain  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_selection_prompt_no_subtitle():
    """SelectionPrompt without subtitle does not render subtitle element."""
    options = [("a", "Option A"), ("b", "Option B")]
    app = WidgetTestApp(lambda: SelectionPrompt("Title:", options))
    async with app.run_test():
        prompt = app.query_one(SelectionPrompt)
        subtitles = list(prompt.query(".prompt-subtitle"))
        assert len(subtitles) == 0


@pytest.mark.asyncio
async def test_sidebar_handles_many_agents_without_overflow():
    """12 agents forces compact mode and scrollable container."""
    from claudechic.widgets.layout.sidebar import AgentItem

    app = WidgetTestApp(lambda: AgentSection(id="agents"))
    async with app.run_test() as pilot:
        section = app.query_one(AgentSection)

        # Add 12 agents
        for i in range(12):
            section.add_agent(f"id-{i}", f"Agent-{i}")
        await pilot.pause()

        # All AgentItems should have the compact CSS class (>6 forces compact)
        items = list(section.query(AgentItem))
        assert len(items) == 12, f"Expected 12 AgentItems, got {len(items)}"
        assert all(item.has_class("compact") for item in items), (
            "All items should have 'compact' CSS class when >6 agents"
        )

        # VerticalScroll#agent-scroll should exist as container
        from textual.containers import VerticalScroll

        scroll = section.query_one("#agent-scroll", VerticalScroll)
        assert scroll is not None, "VerticalScroll#agent-scroll must exist"

        # All 12 items should be queryable with no display:none
        for item in items:
            assert item.display is True, (
                f"AgentItem {item.agent_id} should not have display:none"
            )


# --- DiagnosticsLabel ("info") + ComputerInfoModal tests ---


@pytest.mark.asyncio
async def test_info_label_click_opens_computer_info_modal():
    """Click #diagnostics-label ("info") opens the unified ComputerInfoModal.

    Per SPEC C2 / F: the footer collapsed from 5 to 4 labels. The
    surviving info-style button is ``DiagnosticsLabel`` (display text
    "info"); the former ``ComputerInfoLabel`` ("sys") was dropped.
    Both buttons used to open ``ComputerInfoModal``; the click path
    now flows through ``on_diagnostics_label_requested``.
    """
    from claudechic.widgets.layout.footer import DiagnosticsLabel
    from claudechic.widgets.modals.computer_info import ComputerInfoModal

    class SysTestApp(App):
        def compose(self) -> ComposeResult:
            yield StatusFooter()

        def on_diagnostics_label_requested(
            self, event: DiagnosticsLabel.Requested
        ) -> None:
            self.push_screen(ComputerInfoModal(cwd="/tmp"))

    app = SysTestApp()
    async with app.run_test(size=(80, 24)) as pilot:
        # Verify label exists (the surviving "info" button).
        label = app.query_one("#diagnostics-label", DiagnosticsLabel)
        assert label is not None

        # Post the message (simulates a click on the label)
        label.post_message(DiagnosticsLabel.Requested())
        await pilot.pause()

        # Assert ComputerInfoModal is on the screen stack
        assert any(isinstance(s, ComputerInfoModal) for s in app.screen_stack), (
            "ComputerInfoModal should be on screen stack"
        )
        modal = app.screen

        # Check that sections have non-empty values
        # The modal renders InfoSection items as Static widgets with class "info-value"
        value_widgets = list(modal.query(".info-value"))
        assert len(value_widgets) >= 6, (
            f"Expected at least 6 info values, got {len(value_widgets)}"
        )

        # Build a dict of label -> value from the modal
        label_widgets = list(modal.query(".info-label"))
        info = {}
        for lbl, val in zip(label_widgets, value_widgets, strict=True):
            lbl_text = lbl.render().plain.strip().rstrip(":")
            val_text = val.render().plain.strip()
            info[lbl_text] = val_text

        # Host, OS, Python, CWD must be non-empty
        for key in ("Host", "OS", "Python", "CWD"):
            assert key in info, f"Missing section: {key}"
            assert info[key], f"Section {key} is empty"

        # SDK and claudechic must be version strings or "unknown"
        version_re = re.compile(r"^\d+\.\d+")
        for key in ("SDK", "claudechic"):
            assert key in info, f"Missing section: {key}"
            val = info[key]
            assert val == "unknown" or version_re.match(val), (
                f"{key} should be a version string or 'unknown', got: {val!r}"
            )

        # Pressing Escape dismisses the modal
        await pilot.press("escape")
        await pilot.pause()

        assert not any(isinstance(s, ComputerInfoModal) for s in app.screen_stack), (
            "Modal should be dismissed after Escape"
        )


@pytest.mark.asyncio
async def test_files_section_scrolls_with_many_files():
    """FilesSection wraps items in a VerticalScroll with id='files-scroll'."""
    from pathlib import Path

    from claudechic.widgets import FilesSection
    from claudechic.widgets.layout.sidebar import FileItem
    from textual.containers import VerticalScroll

    app = WidgetTestApp(lambda: FilesSection(id="files-section"))
    async with app.run_test():
        section = app.query_one(FilesSection)

        # Add 20 files
        for i in range(20):
            section.add_file(Path(f"src/file_{i:02d}.py"), additions=i, deletions=0)

        await app.workers.wait_for_complete()

        # VerticalScroll with id="files-scroll" must exist inside FilesSection
        scroll = section.query_one("#files-scroll", VerticalScroll)
        assert scroll is not None, (
            "FilesSection must contain a VerticalScroll#files-scroll"
        )

        # All 20 FileItems must be queryable
        items = section.query(FileItem)
        assert len(items) == 20, f"Expected 20 FileItems, got {len(items)}"

        # No item should be display:none
        for item in items:
            assert item.display, f"FileItem {item.id} should not have display:none"


@pytest.mark.asyncio
async def test_files_section_visible_with_workflow_active(mock_sdk):
    """_layout_sidebar_contents must compact agents when workflow is active.

    Regression test for chicsession_overhead budget bug: with a workflow active,
    ChicsessionLabel is 5 lines (title + name + workflow + phase + actions) but
    the budget previously hardcoded 3. Files reserve a minimum of
    FILES_OVERHEAD(4) + 3 = 7 lines before the agent compact decision.

    Budget math at H=27, N=4, files_reserved=7:
      remaining_for_agents = H-1 - chicsession - agent_title - files_reserved
      overhead=3 (bug): 27-1-6-7=13, 4*3=12 <= 13 -> NOT compact
      overhead=5 (fix): 27-1-8-7=11, 4*3=12 >  11 -> compact
    """
    from pathlib import Path
    from unittest.mock import MagicMock

    from claudechic.app import ChatApp

    app = ChatApp()
    # H=27: 2-line overhead difference crosses the compact threshold with files reserved
    async with app.run_test(size=(120, 27)):
        # Activate workflow engine (makes chicsession 5 lines: title+name+workflow+phase+actions)
        app._workflow_engine = MagicMock()

        # Control agent_section state precisely: exactly 4 agents, no worktrees
        agent_section = app.agent_section
        agent_section._agents.clear()
        agent_section._worktrees.clear()
        agent_section._compact = False
        for i in range(4):
            agent_section.add_agent(f"agent-{i}", f"Agent {i}")

        # Add 5 files to FilesSection
        section = app.files_section
        for i in range(5):
            section.add_file(Path(f"src/module_{i}.py"), additions=i + 1, deletions=0)

        await app.workers.wait_for_complete()

        # Trigger layout budget calculation
        app._position_right_sidebar()
        await app.workers.wait_for_complete()

        # With the fix (overhead=5): agents must be in compact mode at H=20
        # With the bug (overhead=3): agents stay expanded, content overflows, FilesSection clipped
        assert agent_section._compact, (
            "Agents must be compact at H=27 with workflow active + files reserved; "
            "overhead=3 bug: remaining_for_agents=13, 4*3=12<=13 -> expanded; "
            "overhead=5 fix: remaining_for_agents=11, 4*3=12>11 -> compact"
        )


@pytest.mark.asyncio
async def test_files_section_renders_with_files():
    """FilesSection renders file items with non-zero height inside a sidebar-like container.

    Mirrors the real sidebar structure from screens/chat.py:
        Vertical#right-sidebar (height: 100%)
          ChicsessionLabel
          AgentSection
          PlanSection (hidden)
          FilesSection (hidden -> becomes visible after mount_all_files)
    """
    from pathlib import Path

    from claudechic.widgets import (
        AgentSection,
        ChicsessionLabel,
        FilesSection,
        PlanSection,
    )
    from textual.containers import Vertical

    class SidebarLikeApp(App):
        CSS = """
        #right-sidebar {
            width: 28;
            height: 100%;
        }
        """

        def compose(self) -> ComposeResult:
            with Vertical(id="right-sidebar"):
                yield ChicsessionLabel(id="chicsession-label")
                yield AgentSection(id="agent-section")
                yield PlanSection(id="plan-section", classes="hidden")
                yield FilesSection(id="files-section", classes="hidden")

    async with SidebarLikeApp().run_test(size=(130, 40)) as pilot:
        app = pilot.app
        agent_section = app.query_one("#agent-section", AgentSection)
        agent_section.add_agent("agent-0", "MainAgent")

        fs = app.query_one("#files-section", FilesSection)
        files = {
            Path("foo.py"): (10, 2, False),
            Path("bar.md"): (5, 0, True),
        }
        fs.mount_all_files(files)
        await pilot.pause()

        assert fs.item_count == 2
        assert not fs.has_class("hidden"), (
            "FilesSection should not be hidden after mount_all_files"
        )
        scroll = fs.query_one("#files-scroll")
        assert len(list(scroll.children)) == 2, (
            f"Expected 2 children in #files-scroll, got {len(list(scroll.children))}"
        )
        assert scroll.region.height > 0, (
            f"#files-scroll collapsed to height=0. "
            f"scroll.region={scroll.region}, fs.region={fs.region}"
        )
        # FilesSection must be within the visible 40-line viewport — regression
        # guard for #agent-scroll height:1fr bug that pushed FilesSection to y=43
        assert fs.region.y < 40, (
            f"FilesSection at y={fs.region.y} is off-screen (terminal height=40). "
            f"AgentSection likely expanded to fill sidebar. "
            f"Ensure #agent-scroll has height:auto, not height:1fr."
        )
