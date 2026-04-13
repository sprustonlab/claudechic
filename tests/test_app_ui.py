"""App-level UI tests without SDK dependency."""

from unittest.mock import MagicMock

import pytest
from claude_agent_sdk import ToolResultBlock, ToolUseBlock
from claudechic.app import ChatApp
from claudechic.messages import (
    ResponseComplete,
    ToolResultMessage,
    ToolUseMessage,
)
from claudechic.widgets import (
    AgentSection,
    ChatInput,
    ChatMessage,
    StatusFooter,
    TodoPanel,
)

from tests.conftest import submit_command, wait_for_workers


@pytest.mark.asyncio
async def test_app_mounts_basic_widgets(mock_sdk):
    """App mounts all expected widgets on startup."""
    app = ChatApp()
    async with app.run_test():
        # Check key widgets exist
        assert app.query_one("#input", ChatInput)
        assert app.query_one("#agent-section", AgentSection)
        assert app.query_one("#todo-panel", TodoPanel)
        assert app.query_one(StatusFooter)


@pytest.mark.asyncio
async def test_permission_mode_cycle(mock_sdk):
    """Shift+Tab cycles permission mode: default -> bypassPermissions -> acceptEdits -> plan -> default.

    Note: Initial mode is 'default' (fresh install behavior).
    Cycle goes through all modes and wraps back to default.
    """
    app = ChatApp()
    async with app.run_test() as pilot:
        assert app._agent is not None
        # Initial mode is 'default' (fresh install behavior)
        assert app._agent.permission_mode == "default"

        # Cycle: default -> bypassPermissions
        await pilot.press("shift+tab")
        assert app._agent.permission_mode == "bypassPermissions"

        # Cycle: bypassPermissions -> acceptEdits
        await pilot.press("shift+tab")
        assert app._agent.permission_mode == "acceptEdits"

        # Cycle: acceptEdits -> plan
        await pilot.press("shift+tab")
        assert app._agent.permission_mode == "plan"

        # Cycle: plan -> default (back to start)
        await pilot.press("shift+tab")
        assert app._agent.permission_mode == "default"


@pytest.mark.asyncio
async def test_permission_mode_footer_updates(mock_sdk):
    """Footer reflects permission mode state."""
    app = ChatApp()
    async with app.run_test() as pilot:
        footer = app.query_one(StatusFooter)
        # Initial mode is 'default' (fresh install behavior)
        assert footer.permission_mode == "default"

        # First cycle: default -> bypassPermissions
        await pilot.press("shift+tab")
        assert footer.permission_mode == "bypassPermissions"

        # Second cycle: bypassPermissions -> acceptEdits
        await pilot.press("shift+tab")
        assert footer.permission_mode == "acceptEdits"


@pytest.mark.asyncio
async def test_clear_command(mock_sdk):
    """'/clear' removes chat messages."""
    app = ChatApp()
    async with app.run_test() as pilot:
        chat_view = app._chat_view
        assert chat_view is not None

        # Add some fake messages
        msg1 = ChatMessage("Test 1")
        msg2 = ChatMessage("Test 2")
        chat_view.mount(msg1)
        chat_view.mount(msg2)
        await pilot.pause()

        assert len(chat_view.children) == 2

        # Send /clear (which clears UI and sends to SDK)
        await submit_command(app, pilot, "/clear")
        await wait_for_workers(app)
        await pilot.pause()  # Let DOM updates complete

        # Chat view should be empty
        messages = list(chat_view.query(ChatMessage))
        assert len(messages) == 0  # Our messages were cleared


@pytest.mark.asyncio
async def test_agent_list_command(mock_sdk):
    """'/agent' lists agents."""
    app = ChatApp()
    async with app.run_test() as pilot:
        # Should have one default agent
        assert len(app.agents) == 1

        await submit_command(app, pilot, "/agent")

        # The command shows notifications - just verify we have one agent
        assert len(app.agents) == 1


@pytest.mark.asyncio
async def test_agent_create_command(mock_sdk):
    """'/agent foo' creates new agent."""
    app = ChatApp()
    async with app.run_test() as pilot:
        assert len(app.agents) == 1

        await submit_command(app, pilot, "/agent test-agent")
        await wait_for_workers(app)

        assert len(app.agents) == 2
        agent_names = [a.name for a in app.agents.values()]
        assert "test-agent" in agent_names


@pytest.mark.asyncio
async def test_agent_switch_keybinding(mock_sdk):
    """Ctrl+1-9 switches agents."""
    app = ChatApp()
    async with app.run_test() as pilot:
        # Create second agent
        await submit_command(app, pilot, "/agent second")
        await wait_for_workers(app)

        assert len(app.agents) == 2
        agent_ids = list(app.agents.keys())

        # Should be on second agent now (just created)
        assert app.active_agent_id == agent_ids[1]

        # Switch to first agent with ctrl+1
        await pilot.press("ctrl+1")
        assert app.active_agent_id == agent_ids[0]

        # Switch to second agent with ctrl+2
        await pilot.press("ctrl+2")
        assert app.active_agent_id == agent_ids[1]


@pytest.mark.asyncio
async def test_agent_close_command(mock_sdk):
    """'/agent close' closes current agent."""
    app = ChatApp()
    async with app.run_test() as pilot:
        # Create second agent first
        await submit_command(app, pilot, "/agent to-close")
        await wait_for_workers(app)

        assert len(app.agents) == 2
        assert any(a.name == "to-close" for a in app.agents.values())

        # Close current agent
        await submit_command(app, pilot, "/agent close")
        await wait_for_workers(app)
        await pilot.pause()  # Let DOM updates complete

        # Should be back to one agent
        assert len(app.agents) == 1


@pytest.mark.asyncio
async def test_cannot_close_last_agent(mock_sdk):
    """Cannot close the last remaining agent."""
    app = ChatApp()
    async with app.run_test() as pilot:
        assert len(app.agents) == 1

        await submit_command(app, pilot, "/agent close")
        await wait_for_workers(app)

        # Still have one agent
        assert len(app.agents) == 1


@pytest.mark.asyncio
async def test_sidebar_agent_selection(mock_sdk):
    """Clicking agent in sidebar switches to it."""
    app = ChatApp()
    async with app.run_test() as pilot:
        # Create second agent
        await submit_command(app, pilot, "/agent sidebar-test")
        await wait_for_workers(app)

        sidebar = app.query_one("#agent-section", AgentSection)
        agent_ids = list(app.agents.keys())

        # Second agent should be active (just created)
        assert app.active_agent_id == agent_ids[1]

        # Simulate clicking first agent
        first_agent_widget = sidebar._agents[agent_ids[0]]
        first_agent_widget.post_message(first_agent_widget.Selected(agent_ids[0]))
        await pilot.pause()

        # First agent should now be active
        assert app.active_agent_id == agent_ids[0]


@pytest.mark.asyncio
async def test_resume_shows_session_screen(mock_sdk):
    """'/resume' shows session screen."""
    from claudechic.screens import SessionScreen

    app = ChatApp()
    async with app.run_test() as pilot:
        await submit_command(app, pilot, "/resume")

        # Session screen should be on screen stack
        assert isinstance(app.screen, SessionScreen)


@pytest.mark.asyncio
async def test_escape_hides_session_screen(mock_sdk):
    """Escape hides session screen."""
    from claudechic.screens import SessionScreen

    app = ChatApp()
    async with app.run_test() as pilot:
        await submit_command(app, pilot, "/resume")

        assert isinstance(app.screen, SessionScreen)

        # Press escape to dismiss screen
        await pilot.press("escape")
        await pilot.pause()

        assert not isinstance(app.screen, SessionScreen)


@pytest.mark.asyncio
async def test_double_ctrl_c_quits(mock_sdk):
    """Double Ctrl+C quits app."""
    app = ChatApp()
    async with app.run_test() as pilot:
        # First Ctrl+C shows warning
        await pilot.press("ctrl+c")
        assert hasattr(app, "_last_quit_time")

        # Second quick Ctrl+C would exit (but we can't test actual exit easily)
        # Just verify the mechanism exists
        import time

        assert time.time() - app._last_quit_time < 2.0


@pytest.mark.asyncio
async def test_stream_chunk_creates_message(mock_sdk):
    """Text streaming creates ChatMessage widget."""
    app = ChatApp()
    async with app.run_test() as pilot:
        chat_view = app._chat_view
        assert chat_view is not None

        # Simulate text chunk (now direct call, not message)
        chat_view.append_text("Hello ", new_message=True, parent_tool_id=None)
        await pilot.pause()

        # Should have created a ChatMessage
        messages = list(chat_view.query(ChatMessage))
        assert len(messages) == 1
        assert messages[0].get_raw_content() == "Hello "


@pytest.mark.asyncio
async def test_stream_chunk_appends_to_message(mock_sdk):
    """Sequential text chunks append to same message."""
    app = ChatApp()
    async with app.run_test() as pilot:
        chat_view = app._chat_view
        assert chat_view is not None

        chat_view.append_text("Hello ", new_message=True, parent_tool_id=None)
        await pilot.pause()
        chat_view.append_text("world!", new_message=False, parent_tool_id=None)
        await pilot.pause()

        messages = list(chat_view.query(ChatMessage))
        assert len(messages) == 1
        assert messages[0].get_raw_content() == "Hello world!"


@pytest.mark.asyncio
async def test_stream_chunks_interleaved_with_tools(mock_sdk):
    """Text after tool use creates a new ChatMessage (not appended to first)."""
    app = ChatApp()
    async with app.run_test() as pilot:
        chat_view = app._chat_view
        assert chat_view is not None
        agent_id = app.active_agent_id

        # First text chunk
        chat_view.append_text("Planning...", new_message=True, parent_tool_id=None)
        await pilot.pause()

        # Tool use
        tool_block = ToolUseBlock(
            id="tool-1", name="Read", input={"file_path": "/test.py"}
        )
        app.post_message(ToolUseMessage(tool_block, agent_id=agent_id))
        await pilot.pause()

        # Tool result
        result_block = ToolResultBlock(
            tool_use_id="tool-1", content="file contents", is_error=False
        )
        app.post_message(ToolResultMessage(result_block, agent_id=agent_id))
        await pilot.pause()

        # Second text chunk (should be new_message=True after tool)
        chat_view.append_text("Done!", new_message=True, parent_tool_id=None)
        await pilot.pause()

        messages = list(chat_view.query(ChatMessage))
        assert len(messages) == 2, f"Expected 2 messages, got {len(messages)}"
        assert messages[0].get_raw_content() == "Planning..."
        assert messages[1].get_raw_content() == "Done!"


@pytest.mark.asyncio
async def test_response_complete_enables_input(mock_sdk):
    """ResponseComplete focuses input."""
    app = ChatApp()
    async with app.run_test() as pilot:
        agent_id = app.active_agent_id
        app.post_message(ResponseComplete(None, agent_id=agent_id))
        await pilot.pause()

        input_widget = app.query_one("#input", ChatInput)
        assert app.focused == input_widget


@pytest.mark.asyncio
async def test_sidebar_hidden_when_single_agent(mock_sdk):
    """Right sidebar hidden with single agent and no todos."""
    app = ChatApp()
    async with app.run_test(size=(100, 40)):
        sidebar = app.query_one("#right-sidebar")
        # With single agent and no todos, sidebar should be hidden
        assert sidebar.has_class("hidden")


@pytest.mark.asyncio
async def test_sidebar_shows_with_multiple_agents(mock_sdk):
    """Right sidebar shows with multiple agents when wide enough."""
    app = ChatApp()
    async with app.run_test(size=(160, 40)) as pilot:
        # Create second agent
        await submit_command(app, pilot, "/agent second")
        await wait_for_workers(app)

        # Trigger resize handling
        app._position_right_sidebar()

        sidebar = app.query_one("#right-sidebar")
        # With multiple agents and wide enough, sidebar should show
        assert sidebar.display is True


@pytest.mark.asyncio
async def test_command_output_displays(mock_sdk):
    """CommandOutputMessage displays content in chat."""
    from claudechic.messages import CommandOutputMessage

    app = ChatApp()
    async with app.run_test() as pilot:
        chat_view = app._chat_view
        assert chat_view is not None

        # Post a command output message
        agent_id = app.active_agent_id
        app.post_message(
            CommandOutputMessage("## Test Output\n\nSome content", agent_id=agent_id)
        )
        await pilot.pause()

        # Should have created a ChatMessage with system-message class
        messages = list(chat_view.query(ChatMessage))
        assert len(messages) == 1
        assert "## Test Output" in messages[0].get_raw_content()
        assert messages[0].has_class("system-message")


@pytest.mark.asyncio
async def test_context_report_displays(mock_sdk):
    """Context command output displays as ContextReport widget."""
    from claudechic.messages import CommandOutputMessage
    from claudechic.widgets.reports.context import ContextReport

    CONTEXT_OUTPUT = """## Context Usage

**Model:** claude-opus-4-5-20251101
**Tokens:** 81.0k / 200.0k (41%)

### Categories

| Category | Tokens | Percentage |
|----------|--------|------------|
| System prompt | 3.0k | 1.5% |
| Messages | 58.8k | 29.4% |
| Free space | 74.0k | 36.9% |
"""

    app = ChatApp()
    async with app.run_test() as pilot:
        chat_view = app._chat_view
        assert chat_view is not None

        agent_id = app.active_agent_id
        app.post_message(CommandOutputMessage(CONTEXT_OUTPUT, agent_id=agent_id))
        await pilot.pause()

        # Should have created a ContextReport, not ChatMessage
        reports = list(chat_view.query(ContextReport))
        assert len(reports) == 1

        # Verify data was parsed
        assert reports[0].data["model"] == "claude-opus-4-5-20251101"
        assert reports[0].data["tokens_used"] == 81000


@pytest.mark.asyncio
async def test_system_notification_shows_in_chat(mock_sdk):
    """SystemNotification creates SystemInfo widget in chat."""
    from claude_agent_sdk import SystemMessage
    from claudechic.messages import SystemNotification
    from claudechic.widgets import SystemInfo

    app = ChatApp()
    async with app.run_test() as pilot:
        chat_view = app._chat_view
        assert chat_view is not None

        # Create a system message (simulating SDK)
        sdk_msg = SystemMessage(
            subtype="test_notification",
            data={"content": "Test system message", "level": "info"},
        )

        # Post the notification
        app.post_message(SystemNotification(sdk_msg, agent_id=app.active_agent_id))
        await pilot.pause()

        # Should have a SystemInfo widget in chat
        info_widgets = list(chat_view.query(SystemInfo))
        assert len(info_widgets) == 1
        assert info_widgets[0]._message == "Test system message"


@pytest.mark.asyncio
async def test_system_notification_api_error(mock_sdk):
    """API error notification displays correctly."""
    from claude_agent_sdk import SystemMessage
    from claudechic.messages import SystemNotification
    from claudechic.widgets import SystemInfo

    app = ChatApp()
    async with app.run_test() as pilot:
        chat_view = app._chat_view
        assert chat_view is not None

        # Create an api_error system message
        sdk_msg = SystemMessage(
            subtype="api_error",
            data={
                "level": "error",
                "error": {"error": {"message": "Rate limited"}},
                "retryAttempt": 2,
                "maxRetries": 10,
            },
        )

        app.post_message(SystemNotification(sdk_msg, agent_id=app.active_agent_id))
        await pilot.pause()

        info_widgets = list(chat_view.query(SystemInfo))
        assert len(info_widgets) == 1
        assert "retry 2/10" in info_widgets[0]._message
        assert "Rate limited" in info_widgets[0]._message


@pytest.mark.asyncio
async def test_system_notification_compact_boundary(mock_sdk):
    """Compact boundary notification displays."""
    from claude_agent_sdk import SystemMessage
    from claudechic.messages import SystemNotification
    from claudechic.widgets import SystemInfo

    app = ChatApp()
    async with app.run_test() as pilot:
        chat_view = app._chat_view
        assert chat_view is not None

        sdk_msg = SystemMessage(
            subtype="compact_boundary",
            data={"content": "Conversation compacted", "level": "info"},
        )

        app.post_message(SystemNotification(sdk_msg, agent_id=app.active_agent_id))
        await pilot.pause()

        info_widgets = list(chat_view.query(SystemInfo))
        assert len(info_widgets) == 1
        assert "compacted" in info_widgets[0]._message.lower()


@pytest.mark.asyncio
async def test_system_notification_ignored_subtypes(mock_sdk):
    """Certain subtypes are silently ignored."""
    from claude_agent_sdk import SystemMessage
    from claudechic.messages import SystemNotification
    from claudechic.widgets import SystemInfo

    app = ChatApp()
    async with app.run_test() as pilot:
        chat_view = app._chat_view
        assert chat_view is not None

        # These subtypes should not create widgets
        for subtype in ["stop_hook_summary", "turn_duration", "local_command"]:
            sdk_msg = SystemMessage(subtype=subtype, data={"level": "info"})
            app.post_message(SystemNotification(sdk_msg, agent_id=app.active_agent_id))

        await pilot.pause()

        # No SystemInfo widgets should be created
        info_widgets = list(chat_view.query(SystemInfo))
        assert len(info_widgets) == 0


@pytest.mark.asyncio
async def test_sdk_stderr_shows_in_chat(mock_sdk):
    """SDK stderr callback routes messages to chat view."""
    from claudechic.widgets import SystemInfo

    app = ChatApp()
    async with app.run_test() as pilot:
        chat_view = app._chat_view
        assert chat_view is not None

        # Simulate SDK stderr output
        app._handle_sdk_stderr("An update to our Terms of Service")
        await pilot.pause()

        # Should create a SystemInfo widget
        info_widgets = list(chat_view.query(SystemInfo))
        assert len(info_widgets) == 1
        assert "Terms of Service" in info_widgets[0]._message


@pytest.mark.asyncio
async def test_sdk_stderr_ignores_empty(mock_sdk):
    """SDK stderr callback ignores empty/whitespace messages."""
    from claudechic.widgets import SystemInfo

    app = ChatApp()
    async with app.run_test() as pilot:
        chat_view = app._chat_view
        assert chat_view is not None

        # Simulate empty stderr output
        app._handle_sdk_stderr("")
        app._handle_sdk_stderr("   ")
        app._handle_sdk_stderr("\n")
        await pilot.pause()

        # No widgets should be created
        info_widgets = list(chat_view.query(SystemInfo))
        assert len(info_widgets) == 0


@pytest.mark.asyncio
async def test_bang_command_inline_shell(mock_sdk):
    """'!cmd' runs shell command and displays output inline."""
    from claudechic.widgets import ShellOutputWidget

    app = ChatApp()
    async with app.run_test() as pilot:
        chat_view = app._chat_view
        assert chat_view is not None

        input_widget = app.query_one("#input", ChatInput)
        input_widget.text = "!echo hello"
        await pilot.press("enter")
        await wait_for_workers(app)
        await pilot.pause()

        # Should create a ShellOutputWidget
        widgets = list(chat_view.query(ShellOutputWidget))
        assert len(widgets) == 1
        assert widgets[0].command == "echo hello"
        assert "hello" in widgets[0].stdout


@pytest.mark.asyncio
async def test_bang_command_captures_stderr(mock_sdk):
    """'!cmd' captures stderr output (merged with stdout via PTY)."""
    from claudechic.widgets import ShellOutputWidget

    app = ChatApp()
    async with app.run_test() as pilot:
        chat_view = app._chat_view
        assert chat_view is not None

        input_widget = app.query_one("#input", ChatInput)
        input_widget.text = "!echo error >&2"
        await pilot.press("enter")
        await wait_for_workers(app)
        await pilot.pause()

        widgets = list(chat_view.query(ShellOutputWidget))
        assert len(widgets) == 1
        # PTY merges stdout/stderr, so check stdout (which contains both)
        assert "error" in widgets[0].stdout


@pytest.mark.asyncio
async def test_bang_command_shows_exit_code(mock_sdk):
    """'!cmd' shows non-zero exit code in title."""
    from claudechic.widgets import ShellOutputWidget

    app = ChatApp()
    async with app.run_test() as pilot:
        chat_view = app._chat_view
        assert chat_view is not None

        input_widget = app.query_one("#input", ChatInput)
        input_widget.text = "!exit 42"
        await pilot.press("enter")
        await wait_for_workers(app)
        await pilot.pause()

        widgets = list(chat_view.query(ShellOutputWidget))
        assert len(widgets) == 1
        assert widgets[0].returncode == 42


@pytest.mark.asyncio
async def test_hamburger_button_narrow_screen(mock_sdk):
    """Hamburger button appears on narrow screens with multiple agents."""
    from claudechic.widgets import HamburgerButton

    app = ChatApp()
    # Start narrow (below SIDEBAR_MIN_WIDTH=110)
    async with app.run_test(size=(80, 40)) as pilot:
        # Create second agent so sidebar has content
        await submit_command(app, pilot, "/agent second")
        await wait_for_workers(app)

        hamburger = app.query_one("#hamburger-btn", HamburgerButton)

        # Trigger layout update
        app._position_right_sidebar()
        await pilot.pause()

        # Hamburger should be visible on narrow screen with multiple agents
        assert hamburger.display is True

        # Sidebar should be hidden (not overlay yet)
        sidebar = app.query_one("#right-sidebar")
        assert sidebar.display is False


@pytest.mark.asyncio
async def test_hamburger_opens_sidebar_overlay(mock_sdk):
    """Clicking hamburger opens sidebar as overlay."""

    app = ChatApp()
    async with app.run_test(size=(80, 40)) as pilot:
        # Create second agent
        await submit_command(app, pilot, "/agent second")
        await wait_for_workers(app)

        app._position_right_sidebar()
        await pilot.pause()

        sidebar = app.query_one("#right-sidebar")

        # Click hamburger
        await pilot.click("#hamburger-btn")
        await pilot.pause()

        # Sidebar should now be visible as overlay
        assert sidebar.display is True
        assert sidebar.has_class("overlay")


@pytest.mark.asyncio
async def test_escape_closes_sidebar_overlay(mock_sdk):
    """Escape key closes sidebar overlay."""

    app = ChatApp()
    async with app.run_test(size=(80, 40)) as pilot:
        # Create second agent
        await submit_command(app, pilot, "/agent second")
        await wait_for_workers(app)

        app._position_right_sidebar()
        await pilot.pause()

        # Open overlay via state directly (more reliable than click in test)
        app._sidebar_overlay_open = True
        app._position_right_sidebar()
        await pilot.pause()

        sidebar = app.query_one("#right-sidebar")
        assert sidebar.display is True, (
            "Sidebar should be visible after opening overlay"
        )
        assert app._sidebar_overlay_open, "Overlay state should be True"

        # Call action_escape directly (escape key may be consumed by input widget)
        app.action_escape()
        await pilot.pause()

        # Sidebar should be hidden again
        assert not app._sidebar_overlay_open, (
            "Overlay state should be False after escape"
        )
        assert sidebar.display is False, "Sidebar should be hidden after escape"


# =============================================================================
# Agent-scoped review polling (_stop_review_polling)
# =============================================================================


@pytest.mark.asyncio
async def test_stop_review_polling_ignores_other_agent(mock_sdk):
    """Stopping polling for agent B does not cancel agent A's timer."""
    app = ChatApp()
    async with app.run_test():
        # Simulate agent A owning the poll timer
        fake_timer = MagicMock()
        app._review_poll_timer = fake_timer
        app._review_poll_agent_id = "agent-a"

        # Stopping for a different agent should be a no-op
        app._stop_review_polling("agent-b")

        fake_timer.stop.assert_not_called()
        assert app._review_poll_timer is fake_timer
        assert app._review_poll_agent_id == "agent-a"


@pytest.mark.asyncio
async def test_stop_review_polling_stops_own_agent(mock_sdk):
    """Stopping polling for the owning agent cancels the timer."""
    app = ChatApp()
    async with app.run_test():
        fake_timer = MagicMock()
        app._review_poll_timer = fake_timer
        app._review_poll_agent_id = "agent-a"

        app._stop_review_polling("agent-a")

        fake_timer.stop.assert_called_once()
        assert app._review_poll_timer is None
        assert app._review_poll_agent_id is None


@pytest.mark.asyncio
async def test_stop_review_polling_unconditional(mock_sdk):
    """Stopping polling with no agent_id cancels unconditionally."""
    app = ChatApp()
    async with app.run_test():
        fake_timer = MagicMock()
        app._review_poll_timer = fake_timer
        app._review_poll_agent_id = "agent-a"

        app._stop_review_polling()  # No agent_id

        fake_timer.stop.assert_called_once()
        assert app._review_poll_timer is None
        assert app._review_poll_agent_id is None


# =============================================================================
# /clearui command
# =============================================================================


@pytest.mark.asyncio
async def test_clearui_command_keeps_last_10(mock_sdk):
    """/clearui keeps the last 10 widgets by default."""
    app = ChatApp()
    async with app.run_test() as pilot:
        chat_view = app._chat_view
        assert chat_view is not None

        # Add 15 messages
        for i in range(15):
            msg = ChatMessage(f"Message {i}")
            chat_view.mount(msg)
        await pilot.pause()

        assert len(chat_view.children) == 15

        # Send /clearui
        await submit_command(app, pilot, "/clearui")
        await pilot.pause()

        # Should keep last 10
        assert len(chat_view.children) == 10
        # Hidden count should be updated
        assert chat_view._hidden_widget_count == 5


@pytest.mark.asyncio
async def test_clearui_command_custom_keep(mock_sdk):
    """/clearui 3 keeps only last 3 widgets."""
    app = ChatApp()
    async with app.run_test() as pilot:
        chat_view = app._chat_view
        assert chat_view is not None

        # Add 10 messages
        for i in range(10):
            msg = ChatMessage(f"Message {i}")
            chat_view.mount(msg)
        await pilot.pause()

        assert len(chat_view.children) == 10

        # Send /clearui 3
        await submit_command(app, pilot, "/clearui 3")
        await pilot.pause()

        # Should keep last 3
        assert len(chat_view.children) == 3
        assert chat_view._hidden_widget_count == 7


@pytest.mark.asyncio
async def test_clearui_command_fewer_than_keep(mock_sdk):
    """/clearui with fewer widgets than keep count does nothing."""
    app = ChatApp()
    async with app.run_test() as pilot:
        chat_view = app._chat_view
        assert chat_view is not None

        # Add only 5 messages (less than default 10)
        for i in range(5):
            msg = ChatMessage(f"Message {i}")
            chat_view.mount(msg)
        await pilot.pause()

        assert len(chat_view.children) == 5

        # Send /clearui (default keep=10)
        await submit_command(app, pilot, "/clearui")
        await pilot.pause()

        # Should keep all 5 (less than 10)
        assert len(chat_view.children) == 5
        assert chat_view._hidden_widget_count == 0


@pytest.mark.asyncio
async def test_clearui_command_empty_view(mock_sdk):
    """/clearui on empty view does nothing."""
    app = ChatApp()
    async with app.run_test() as pilot:
        chat_view = app._chat_view
        assert chat_view is not None

        # Verify empty
        assert len(chat_view.children) == 0

        # Send /clearui
        await submit_command(app, pilot, "/clearui")
        await pilot.pause()

        # Still empty, no error
        assert len(chat_view.children) == 0
        assert chat_view._hidden_widget_count == 0


@pytest.mark.asyncio
async def test_clearui_all_agents(mock_sdk):
    """/clearui clears UI for all agents."""
    app = ChatApp()
    async with app.run_test() as pilot:
        # Create second agent
        await submit_command(app, pilot, "/agent second")
        await wait_for_workers(app)

        assert len(app.agents) == 2
        agent_ids = list(app.agents.keys())

        # Add messages to both chat views
        for agent_id in agent_ids:
            chat_view = app._chat_views.get(agent_id)
            if chat_view:
                for i in range(15):
                    msg = ChatMessage(f"Message {i}")
                    chat_view.mount(msg)
        await pilot.pause()

        # Verify both have 15 messages
        for agent_id in agent_ids:
            chat_view = app._chat_views.get(agent_id)
            if chat_view:
                assert len(chat_view.children) == 15

        # Send /clearui (should affect all agents)
        await submit_command(app, pilot, "/clearui")
        await pilot.pause()

        # Both should be reduced to 10
        for agent_id in agent_ids:
            chat_view = app._chat_views.get(agent_id)
            if chat_view:
                assert len(chat_view.children) == 10


# =============================================================================
# Toast debounce unit tests (fast marker)
# =============================================================================


@pytest.mark.asyncio
async def test_should_show_toast_none_key(mock_sdk):
    """_should_show_toast(None) always returns True (no debounce)."""
    app = ChatApp()
    async with app.run_test():
        assert app._should_show_toast(None) is True
        assert app._should_show_toast(None) is True
        assert app._should_show_toast(None) is True


@pytest.mark.asyncio
async def test_should_show_toast_cooldown(mock_sdk):
    """Same key within 10s returns False; after 10s returns True."""
    from unittest.mock import patch

    app = ChatApp()
    async with app.run_test():
        fake_time = 1000.0

        with patch("time.monotonic", return_value=fake_time):
            assert app._should_show_toast("agent-1:advance") is True

        # Within cooldown window (5s later)
        with patch("time.monotonic", return_value=fake_time + 5.0):
            assert app._should_show_toast("agent-1:advance") is False

        # After cooldown expires (11s later)
        with patch("time.monotonic", return_value=fake_time + 11.0):
            assert app._should_show_toast("agent-1:advance") is True


@pytest.mark.asyncio
async def test_should_show_toast_independent_keys(mock_sdk):
    """Different keys have independent cooldowns."""
    from unittest.mock import patch

    app = ChatApp()
    async with app.run_test():
        fake_time = 1000.0

        with patch("time.monotonic", return_value=fake_time):
            assert app._should_show_toast("agent-1:advance") is True

        # Different key should still return True even immediately after
        with patch("time.monotonic", return_value=fake_time + 0.1):
            assert app._should_show_toast("agent-1:no_pip_install") is True

        # Original key still in cooldown
        with patch("time.monotonic", return_value=fake_time + 0.2):
            assert app._should_show_toast("agent-1:advance") is False


# =============================================================================
# Integration tests: Advance check UX (issue #21)
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_advance_check_prompt_shows_phase_context(mock_sdk):
    """Confirm prompt displays phase name and progress."""

    app = ChatApp()
    async with app.run_test(size=(120, 40)) as pilot:
        from claudechic.widgets.prompts import SelectionPrompt

        ctx = {
            "phase_id": "proj:review",
            "phase_index": 2,
            "phase_total": 4,
            "check_id": "proj:review:advance:0",
        }

        # Launch the prompt in a task so we can inspect it
        import asyncio

        prompt_task = asyncio.create_task(
            app._show_advance_check_prompt("Ready to review?", context=ctx)
        )
        await pilot.pause()
        await pilot.pause()

        # Find the SelectionPrompt widget
        prompts = list(app.query(SelectionPrompt))
        assert len(prompts) >= 1, "Expected SelectionPrompt to be mounted"
        prompt = prompts[-1]

        # Check title contains phase context
        assert "Phase 2/4" in prompt.title
        assert "review" in prompt.title
        assert "[Advance check]" in prompt.title

        # Check subtitle is the question
        assert prompt.subtitle == "Ready to review?"

        # Dismiss
        prompt._resolve("allow")
        result = await prompt_task
        assert result is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_advance_check_sets_needs_input(mock_sdk):
    """Requesting agent gets NEEDS_INPUT status during prompt, restored after."""
    from claudechic.enums import AgentStatus

    app = ChatApp()
    async with app.run_test(size=(120, 40)) as pilot:
        import asyncio

        agent = app._agent
        assert agent is not None

        ctx = {
            "phase_id": "proj:design",
            "phase_index": 1,
            "phase_total": 3,
            "check_id": "proj:design:advance:0",
        }

        prompt_task = asyncio.create_task(
            app._show_advance_check_prompt("Advance?", context=ctx, agent=agent)
        )
        await pilot.pause()
        await pilot.pause()

        # Agent should be NEEDS_INPUT while prompt is showing
        assert agent.status == AgentStatus.NEEDS_INPUT

        # Dismiss prompt
        from claudechic.widgets.prompts import SelectionPrompt

        prompts = list(app.query(SelectionPrompt))
        assert len(prompts) >= 1
        prompts[-1]._resolve("allow")
        await prompt_task
        await pilot.pause()

        # Status should be restored
        assert agent.status != AgentStatus.NEEDS_INPUT


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(60)
async def test_advance_check_toast_for_inactive_agent(mock_sdk):
    """Toast shown when advance check fires for a non-active agent."""
    app = ChatApp()
    async with app.run_test(size=(120, 40)) as pilot:
        from tests.conftest import submit_command, wait_for_workers

        # Create second agent
        await submit_command(app, pilot, "/agent background")
        await wait_for_workers(app)

        agent_ids = list(app.agents.keys())
        assert len(agent_ids) == 2

        # Switch to first agent via API (avoids flaky WaitForScreenTimeout)
        first_id = agent_ids[0]
        app.agent_mgr.switch(first_id)
        await pilot.pause()
        second_agent = app.agents[agent_ids[1]]
        assert app.active_agent_id == first_id

        import asyncio

        notif_count_before = len(app._notifications)

        ctx = {
            "phase_id": "proj:design",
            "phase_index": 1,
            "phase_total": 3,
            "check_id": "proj:design:advance:0",
        }

        prompt_task = asyncio.create_task(
            app._show_advance_check_prompt("Advance?", context=ctx, agent=second_agent)
        )
        await pilot.pause()
        await pilot.pause()

        # Toast should have been shown for the non-active agent
        notifs_after = list(app._notifications)[notif_count_before:]
        toast_messages = [n.message for n in notifs_after]
        assert any("background" in msg.lower() for msg in toast_messages), (
            f"Expected toast mentioning 'background' agent, got: {toast_messages}"
        )

        # Dismiss
        from claudechic.widgets.prompts import SelectionPrompt

        prompts = list(app.query(SelectionPrompt))
        if prompts:
            prompts[-1]._resolve("deny")
        await prompt_task


@pytest.mark.integration
@pytest.mark.asyncio
async def test_advance_check_deny_feedback(mock_sdk):
    """Post-deny toast: 'Phase advance blocked...'"""
    app = ChatApp()
    async with app.run_test(size=(120, 40), notifications=True) as pilot:
        import asyncio

        ctx = {
            "phase_id": "proj:design",
            "phase_index": 1,
            "phase_total": 3,
            "check_id": "proj:design:advance:0",
        }

        prompt_task = asyncio.create_task(
            app._show_advance_check_prompt("Advance?", context=ctx)
        )
        await pilot.pause()
        await pilot.pause()

        from claudechic.widgets.prompts import SelectionPrompt

        prompts = list(app.query(SelectionPrompt))
        assert len(prompts) >= 1

        notif_count_before = len(app._notifications)
        prompts[-1]._resolve("deny")
        result = await prompt_task
        await pilot.pause()

        assert result is False
        # Check post-deny notification
        notifs_after = list(app._notifications)[notif_count_before:]
        deny_messages = [n.message for n in notifs_after]
        assert any("blocked" in msg.lower() for msg in deny_messages), (
            f"Expected 'blocked' in deny feedback, got: {deny_messages}"
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_advance_check_no_auto_switch(mock_sdk):
    """Active agent does NOT change when another agent's advance check fires."""
    app = ChatApp()
    async with app.run_test(size=(120, 40)) as pilot:
        from tests.conftest import submit_command, wait_for_workers

        # Create second agent
        await submit_command(app, pilot, "/agent background")
        await wait_for_workers(app)

        agent_ids = list(app.agents.keys())
        # Switch to first agent via API (avoids flaky WaitForScreenTimeout)
        first_id = agent_ids[0]
        app.agent_mgr.switch(first_id)
        await pilot.pause()
        second_agent = app.agents[agent_ids[1]]
        assert app.active_agent_id == first_id

        import asyncio

        ctx = {
            "phase_id": "proj:design",
            "phase_index": 1,
            "phase_total": 3,
            "check_id": "proj:design:advance:0",
        }

        prompt_task = asyncio.create_task(
            app._show_advance_check_prompt("Advance?", context=ctx, agent=second_agent)
        )
        await pilot.pause()
        await pilot.pause()

        # Active agent should still be the first one
        assert app.active_agent_id == first_id

        from claudechic.widgets.prompts import SelectionPrompt

        prompts = list(app.query(SelectionPrompt))
        if prompts:
            prompts[-1]._resolve("allow")
        await prompt_task


@pytest.mark.integration
@pytest.mark.asyncio
async def test_override_prompt_shows_rule_context(mock_sdk):
    """Override prompt displays [Override] Rule: {rule_id} title + description as subtitle."""
    app = ChatApp()
    async with app.run_test(size=(120, 40)) as pilot:
        import asyncio

        from claudechic.widgets.prompts import SelectionPrompt

        description = (
            "Agent wants to run blocked action:\n"
            "  Tool: Bash\n"
            "  Input: pip install foo\n"
            "  Blocked by: global:no_pip_install\n"
            "Approve this specific action?"
        )

        prompt_task = asyncio.create_task(
            app._show_override_prompt("global:no_pip_install", description)
        )
        await pilot.pause()
        await pilot.pause()

        prompts = list(app.query(SelectionPrompt))
        assert len(prompts) >= 1
        prompt = prompts[-1]

        assert "[Override]" in prompt.title
        assert "no_pip_install" in prompt.title
        assert prompt.subtitle == description

        prompt._resolve("deny")
        await prompt_task


@pytest.mark.integration
@pytest.mark.asyncio
async def test_override_prompt_sets_needs_input(mock_sdk):
    """Requesting agent gets NEEDS_INPUT status during override prompt."""
    from claudechic.enums import AgentStatus

    app = ChatApp()
    async with app.run_test(size=(120, 40)) as pilot:
        import asyncio

        agent = app._agent
        assert agent is not None

        prompt_task = asyncio.create_task(
            app._show_override_prompt("global:no_pip_install", "Block?", agent=agent)
        )
        await pilot.pause()
        await pilot.pause()

        assert agent.status == AgentStatus.NEEDS_INPUT

        from claudechic.widgets.prompts import SelectionPrompt

        prompts = list(app.query(SelectionPrompt))
        assert len(prompts) >= 1
        prompts[-1]._resolve("deny")
        await prompt_task
        await pilot.pause()

        assert agent.status != AgentStatus.NEEDS_INPUT


@pytest.mark.integration
@pytest.mark.asyncio
async def test_override_prompt_toast_for_inactive_agent(mock_sdk):
    """Toast shown when override fires for a non-active agent."""
    app = ChatApp()
    async with app.run_test(size=(120, 40)) as pilot:
        from tests.conftest import submit_command, wait_for_workers

        await submit_command(app, pilot, "/agent background")
        await wait_for_workers(app)

        agent_ids = list(app.agents.keys())
        # Use agent_mgr.switch to avoid flaky WaitForScreenTimeout
        app.agent_mgr.switch(agent_ids[0])
        await pilot.pause()
        second_agent = app.agents[agent_ids[1]]
        assert app.active_agent_id == agent_ids[0]

        import asyncio

        notif_count_before = len(app._notifications)

        prompt_task = asyncio.create_task(
            app._show_override_prompt(
                "global:no_pip_install", "Block?", agent=second_agent
            )
        )
        await pilot.pause()
        await pilot.pause()

        notifs_after = list(app._notifications)[notif_count_before:]
        toast_messages = [n.message for n in notifs_after]
        assert any("background" in msg.lower() for msg in toast_messages), (
            f"Expected toast for 'background' agent, got: {toast_messages}"
        )

        from claudechic.widgets.prompts import SelectionPrompt

        prompts = list(app.query(SelectionPrompt))
        if prompts:
            prompts[-1]._resolve("deny")
        await prompt_task


@pytest.mark.integration
@pytest.mark.asyncio
async def test_override_prompt_no_emoji(mock_sdk):
    """Override prompt title contains no non-ASCII characters."""
    app = ChatApp()
    async with app.run_test(size=(120, 40)) as pilot:
        import asyncio

        from claudechic.widgets.prompts import SelectionPrompt

        prompt_task = asyncio.create_task(
            app._show_override_prompt("global:no_pip_install", "Blocked")
        )
        await pilot.pause()
        await pilot.pause()

        prompts = list(app.query(SelectionPrompt))
        assert len(prompts) >= 1
        title = prompts[-1].title

        # Verify ASCII only
        assert all(ord(c) < 128 for c in title), (
            f"Non-ASCII characters in override title: {title!r}"
        )

        prompts[-1]._resolve("deny")
        await prompt_task


@pytest.mark.integration
@pytest.mark.asyncio
async def test_toast_debounce_suppresses_repeat(mock_sdk):
    """Second override prompt for same agent+rule within 10s does NOT fire a toast.

    Uses a single prompt flow + _should_show_toast state check to avoid
    TUI sequencing issues with mounting multiple sequential prompts.
    """
    app = ChatApp()
    async with app.run_test(size=(120, 40)) as pilot:
        from tests.conftest import submit_command, wait_for_workers

        await submit_command(app, pilot, "/agent background")
        await wait_for_workers(app)

        agent_ids = list(app.agents.keys())
        # Use agent_mgr.switch to avoid flaky ctrl+1 WaitForScreenTimeout
        app.agent_mgr.switch(agent_ids[0])
        await pilot.pause()
        second_agent = app.agents[agent_ids[1]]
        assert app.active_agent_id == agent_ids[0]

        import asyncio

        # First prompt -- toast should fire (sets debounce timestamp)
        notif_count_before = len(app._notifications)
        prompt_task = asyncio.create_task(
            app._show_override_prompt(
                "global:no_pip_install", "Block?", agent=second_agent
            )
        )
        await pilot.pause()
        await pilot.pause()

        notifs_first = list(app._notifications)[notif_count_before:]
        assert len(notifs_first) > 0, "Expected toast on first prompt"

        from claudechic.widgets.prompts import SelectionPrompt

        prompts = list(app.query(SelectionPrompt))
        assert len(prompts) >= 1
        prompts[-1]._resolve("deny")
        await prompt_task
        await pilot.pause()

        # Verify debounce state: same key should be suppressed
        toast_key = f"{second_agent.id}:global:no_pip_install"
        assert app._should_show_toast(toast_key) is False, (
            "Expected debounce to suppress repeat toast for same key"
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_toast_debounce_allows_different_keys(mock_sdk):
    """Two override prompts for same agent but different rule_ids both fire toasts.

    Uses a single prompt flow + _should_show_toast state check.
    """
    app = ChatApp()
    async with app.run_test(size=(120, 40)) as pilot:
        from tests.conftest import submit_command, wait_for_workers

        await submit_command(app, pilot, "/agent background")
        await wait_for_workers(app)

        agent_ids = list(app.agents.keys())
        # Use agent_mgr.switch to avoid flaky WaitForScreenTimeout
        app.agent_mgr.switch(agent_ids[0])
        await pilot.pause()
        second_agent = app.agents[agent_ids[1]]

        import asyncio

        # First prompt with rule A -- fires toast for key "agent:no_pip_install"
        notif_count_before = len(app._notifications)
        task1 = asyncio.create_task(
            app._show_override_prompt(
                "global:no_pip_install", "Block A?", agent=second_agent
            )
        )
        await pilot.pause()
        await pilot.pause()

        notifs1 = list(app._notifications)[notif_count_before:]
        assert len([n for n in notifs1 if "background" in n.message.lower()]) > 0, (
            "Expected toast for first rule"
        )

        from claudechic.widgets.prompts import SelectionPrompt

        prompts = list(app.query(SelectionPrompt))
        assert len(prompts) >= 1
        prompts[-1]._resolve("deny")
        await task1
        await pilot.pause()

        # Different rule key should NOT be suppressed
        different_key = f"{second_agent.id}:global:no_shell_exec"
        assert app._should_show_toast(different_key) is True, (
            "Expected independent cooldown for different rule key"
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_toast_debounce_expires_after_cooldown(mock_sdk):
    """After 10s cooldown, same agent+rule fires toast again.

    Verifies debounce expiry by seeding the timestamp dict directly and
    calling _should_show_toast with mocked time. Uses a real running app
    to ensure integration with the ChatApp instance.
    """
    from unittest.mock import patch

    app = ChatApp()
    async with app.run_test(size=(120, 40)):
        agent = app._agent
        assert agent is not None

        fake_time = 1000.0
        toast_key = f"{agent.id}:global:no_pip_install"

        # Seed a timestamp as if a toast was shown at t=1000
        app._toast_timestamps[toast_key] = fake_time

        # Within cooldown (t=1005): should be suppressed
        with patch("claudechic.app.time.monotonic", return_value=fake_time + 5.0):
            assert app._should_show_toast(toast_key) is False, (
                "Expected toast to be suppressed within cooldown"
            )

        # After cooldown (t=1012): should be allowed
        with patch("claudechic.app.time.monotonic", return_value=fake_time + 12.0):
            assert app._should_show_toast(toast_key) is True, (
                "Expected toast to be allowed after cooldown expiry"
            )


# =============================================================================
# Prompt focus on agent switch (TDD -- written before fix)
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(60)
async def test_prompt_visible_and_focused_after_agent_switch(mock_sdk):
    """Switching to an agent with a pending prompt must NOT focus chat_input.

    Bug: on_agent_switched unconditionally calls chat_input.focus() at
    the end, even when an active prompt exists.  This steals focus from
    the prompt.  (In practice on_blur fights back, but the spurious
    focus call causes a visible flicker and is wrong by contract.)

    Fix: chat_input.focus() must be conditional -- skipped when an
    active prompt is being shown.
    """
    from unittest.mock import patch

    app = ChatApp()
    async with app.run_test(size=(120, 40)) as pilot:
        from tests.conftest import submit_command, wait_for_workers

        await submit_command(app, pilot, "/agent prompted")
        await wait_for_workers(app)
        await pilot.pause()

        agent_ids = list(app.agents.keys())
        first_id, second_id = agent_ids[0], agent_ids[1]
        second_agent = app.agents[second_id]

        # Make first agent active so second is inactive
        app.agent_mgr.switch(first_id)
        await pilot.pause()

        import asyncio

        # Mount a prompt on the inactive second agent
        prompt_task = asyncio.create_task(
            app._show_override_prompt(
                "global:test_rule", "Approve?", agent=second_agent
            )
        )
        await pilot.pause()
        await pilot.pause()

        from claudechic.widgets.prompts import SelectionPrompt

        prompts = list(app.query(SelectionPrompt))
        assert len(prompts) >= 1
        prompt = prompts[-1]
        assert prompt.has_class("hidden")

        # Spy on chat_input.focus during the switch
        chat_input_focus_calls: list[bool] = []
        original_ci_focus = app.chat_input.focus

        def spy_ci_focus(*a, **kw):
            chat_input_focus_calls.append(True)
            return original_ci_focus(*a, **kw)

        with patch.object(app.chat_input, "focus", side_effect=spy_ci_focus):
            app.agent_mgr.switch(second_id)
            await pilot.pause()
            await pilot.pause()

        # Prompt should be visible
        assert not prompt.has_class("hidden"), (
            "Prompt should be visible after switching to its agent"
        )

        # Contract: chat_input.focus() must NOT be called when a prompt
        # is active.  The buggy code calls it unconditionally.
        assert len(chat_input_focus_calls) == 0, (
            f"chat_input.focus() called {len(chat_input_focus_calls)} time(s) "
            f"during switch -- should not be called when active prompt exists"
        )

        prompt._resolve("deny")
        await prompt_task


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(60)
async def test_prompt_refocused_after_switch_away_and_back(mock_sdk):
    """After switch-back, prompt.focus() must happen AFTER refresh_css().

    Bug: on_agent_switched calls active_prompt.focus() BEFORE
    refresh_css(), so focus targets an element whose CSS display has
    not been recomputed yet.

    Fix: move the prompt.focus() call to AFTER refresh_css().
    """
    from unittest.mock import patch

    app = ChatApp()
    async with app.run_test(size=(120, 40)) as pilot:
        from tests.conftest import submit_command, wait_for_workers

        await submit_command(app, pilot, "/agent other")
        await wait_for_workers(app)
        await pilot.pause()

        agent_ids = list(app.agents.keys())
        first_id, second_id = agent_ids[0], agent_ids[1]
        first_agent = app.agents[first_id]

        app.agent_mgr.switch(first_id)
        await pilot.pause()

        import asyncio

        # Mount a prompt on the active first agent
        prompt_task = asyncio.create_task(
            app._show_override_prompt("global:test_rule", "Approve?", agent=first_agent)
        )
        await pilot.pause()
        await pilot.pause()

        from claudechic.widgets.prompts import SelectionPrompt

        prompts = list(app.query(SelectionPrompt))
        assert len(prompts) >= 1
        prompt = prompts[-1]
        assert not prompt.has_class("hidden")

        # Switch away
        app.agent_mgr.switch(second_id)
        await pilot.pause()
        assert prompt.has_class("hidden")

        # Record call order during switch-back
        call_order: list[str] = []
        orig_refresh = app.refresh_css
        orig_pfocus = prompt.focus

        def spy_refresh(*a, **kw):
            call_order.append("refresh_css")
            return orig_refresh(*a, **kw)

        def spy_pfocus(*a, **kw):
            call_order.append("prompt_focus")
            return orig_pfocus(*a, **kw)

        with (
            patch.object(app, "refresh_css", side_effect=spy_refresh),
            patch.object(prompt, "focus", side_effect=spy_pfocus),
        ):
            app.agent_mgr.switch(first_id)
            await pilot.pause()
            await pilot.pause()

        assert not prompt.has_class("hidden"), (
            "Prompt should be visible after switching back"
        )

        # prompt.focus() must appear in the call log
        assert "prompt_focus" in call_order, (
            f"prompt.focus() never called during switch-back: {call_order}"
        )
        assert "refresh_css" in call_order, (
            f"refresh_css() never called during switch-back: {call_order}"
        )

        # And it must come AFTER refresh_css
        assert call_order.index("prompt_focus") > call_order.index("refresh_css"), (
            f"prompt.focus() called BEFORE refresh_css() -- "
            f"focus must happen after CSS recomputation. Order: {call_order}"
        )

        prompt._resolve("deny")
        await prompt_task
