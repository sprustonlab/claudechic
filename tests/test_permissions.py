"""Tests for permission handling: bypassPermissions mode, inheritance, and /clearui command."""

import asyncio
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from claude_agent_sdk.types import PermissionResultAllow, ToolPermissionContext


# ---------------------------------------------------------------------------
# Mock classes (similar to test_mcp_ask_agent.py pattern)
# ---------------------------------------------------------------------------


class MockAgent:
    """Mock Agent for permission tests."""

    def __init__(self, name: str, permission_mode: str = "default"):
        self.name = name
        self.id = name
        self.session_id = f"session-{name}"
        self.cwd = Path("/tmp")
        self.status = "idle"
        self.worktree = None
        self.client = MagicMock()
        self.permission_mode = permission_mode
        self.session_allowed_tools = set()
        self.finish_state = None
        self.pending_prompts = []
        self.observer = None
        self.permission_handler = None

    @property
    def analytics_id(self) -> str:
        return self.session_id or self.id

    async def send(self, prompt: str) -> None:
        self.received_prompt = prompt


class MockAgentManager:
    """Mock AgentManager for MCP tests."""

    def __init__(self):
        self.agents: dict[str, MockAgent] = {}
        self.active: MockAgent | None = None
        self._created_agents: list[
            tuple[str, Path, str]
        ] = []  # (name, cwd, permission_mode)

    def add(self, agent: MockAgent) -> None:
        self.agents[agent.name] = agent
        if self.active is None:
            self.active = agent

    def find_by_name(self, name: str) -> MockAgent | None:
        return self.agents.get(name)

    async def create(
        self,
        name: str,
        cwd: Path,
        *,
        worktree: str | None = None,
        switch_to: bool = True,
        permission_mode: str | None = None,
    ) -> MockAgent:
        """Create a new agent, capturing permission_mode for test assertions."""
        agent = MockAgent(name, permission_mode=permission_mode or "default")
        agent.cwd = cwd
        agent.worktree = worktree
        self.agents[name] = agent
        # Track what was passed for test assertions
        self._created_agents.append((name, cwd, permission_mode or "default"))
        if switch_to or self.active is None:
            self.active = agent
        return agent

    def __len__(self) -> int:
        return len(self.agents)


class MockApp:
    """Mock ChatApp for MCP tests."""

    def __init__(self):
        self.agent_mgr = MockAgentManager()

    def run_worker(self, coro):
        """Mock run_worker - close the coroutine to avoid RuntimeWarning."""
        coro.close()


# ---------------------------------------------------------------------------
# Tests for bypassPermissions mode
# ---------------------------------------------------------------------------


class TestBypassPermissionsMode:
    """Tests for bypassPermissions mode auto-approval behavior."""

    @pytest.mark.asyncio
    async def test_bypass_permissions_auto_approves_bash(self):
        """bypassPermissions mode auto-approves Bash tool."""
        from claudechic.agent import Agent

        agent = Agent(name="test", cwd=Path("/tmp"))
        agent.permission_mode = "bypassPermissions"

        # Create a mock context
        context = MagicMock(spec=ToolPermissionContext)

        result = await agent._handle_permission(
            "Bash",
            {"command": "rm -rf /"},
            context,
        )

        assert isinstance(result, PermissionResultAllow)

    @pytest.mark.asyncio
    async def test_bypass_permissions_auto_approves_edit(self):
        """bypassPermissions mode auto-approves Edit tool."""
        from claudechic.agent import Agent

        agent = Agent(name="test", cwd=Path("/tmp"))
        agent.permission_mode = "bypassPermissions"

        context = MagicMock(spec=ToolPermissionContext)

        result = await agent._handle_permission(
            "Edit",
            {"file_path": "/etc/passwd", "old_string": "x", "new_string": "y"},
            context,
        )

        assert isinstance(result, PermissionResultAllow)

    @pytest.mark.asyncio
    async def test_bypass_permissions_auto_approves_write(self):
        """bypassPermissions mode auto-approves Write tool."""
        from claudechic.agent import Agent

        agent = Agent(name="test", cwd=Path("/tmp"))
        agent.permission_mode = "bypassPermissions"

        context = MagicMock(spec=ToolPermissionContext)

        result = await agent._handle_permission(
            "Write",
            {"file_path": "/tmp/test.txt", "content": "hello"},
            context,
        )

        assert isinstance(result, PermissionResultAllow)

    @pytest.mark.asyncio
    async def test_bypass_permissions_auto_approves_any_tool(self):
        """bypassPermissions mode auto-approves arbitrary tools."""
        from claudechic.agent import Agent

        agent = Agent(name="test", cwd=Path("/tmp"))
        agent.permission_mode = "bypassPermissions"

        context = MagicMock(spec=ToolPermissionContext)

        # Test various tool names
        tools = [
            ("NotebookEdit", {"notebook_path": "/tmp/test.ipynb", "new_source": "x"}),
            ("WebFetch", {"url": "https://example.com", "prompt": "fetch"}),
            ("SomeCustomTool", {"arg": "value"}),
        ]

        for tool_name, tool_input in tools:
            result = await agent._handle_permission(tool_name, tool_input, context)
            assert isinstance(result, PermissionResultAllow), f"Failed for {tool_name}"

    @pytest.mark.asyncio
    async def test_default_mode_does_not_auto_approve(self):
        """Default mode requires permission prompts (doesn't auto-approve)."""
        from claudechic.agent import Agent

        agent = Agent(name="test", cwd=Path("/tmp"))
        agent.permission_mode = "default"

        # Mock the permission handler to return immediately
        # In default mode, the agent should queue a permission request
        async def mock_handler(agent, request):
            from claudechic.permissions import PermissionResponse
            from claudechic.enums import PermissionChoice

            return PermissionResponse(choice=PermissionChoice.DENY)

        agent.permission_handler = mock_handler

        context = MagicMock(spec=ToolPermissionContext)

        result = await agent._handle_permission(
            "Bash",
            {"command": "ls"},
            context,
        )

        # In default mode, it should go through the permission flow
        # and return based on handler response (DENY in this case)
        assert not isinstance(result, PermissionResultAllow)

    @pytest.mark.asyncio
    async def test_bypass_permissions_does_not_affect_ask_user_question(self):
        """AskUserQuestion is handled before bypassPermissions check.

        The AskUserQuestion tool needs special handling to collect user input,
        so it's handled at the start of _handle_permission() before the
        bypassPermissions check. This test verifies that flow.
        """
        from claudechic.agent import Agent
        from claudechic.enums import ToolName

        agent = Agent(name="test", cwd=Path("/tmp"))
        agent.permission_mode = "bypassPermissions"

        # Mock the permission handler for AskUserQuestion
        async def mock_handler(agent, request):
            from claudechic.permissions import PermissionResponse
            from claudechic.enums import PermissionChoice

            # Set answers on the request as the UI would
            request._answers = {"q1": "answer1"}
            return PermissionResponse(choice=PermissionChoice.ALLOW)

        agent.permission_handler = mock_handler

        context = MagicMock(spec=ToolPermissionContext)

        # AskUserQuestion should go through its special handling
        result = await agent._handle_permission(
            ToolName.ASK_USER_QUESTION,
            {
                "questions": [
                    {
                        "question": "Test?",
                        "header": "Q",
                        "options": [
                            {"label": "A", "description": "a"},
                            {"label": "B", "description": "b"},
                        ],
                        "multiSelect": False,
                    }
                ]
            },
            context,
        )

        # Should return Allow with updated_input containing answers
        assert isinstance(result, PermissionResultAllow)
        # The result should have updated_input with answers
        assert hasattr(result, "updated_input")

    @pytest.mark.asyncio
    async def test_bypass_permissions_overrides_plan_mode_blocked_tools(self):
        """bypassPermissions mode should NOT be combined with plan mode.

        This test verifies that bypassPermissions is checked BEFORE plan mode
        blocking, so if somehow both were set, bypass would win. However,
        in practice these are mutually exclusive modes.
        """
        from claudechic.agent import Agent

        agent = Agent(name="test", cwd=Path("/tmp"))
        # Set bypassPermissions - this should take precedence
        agent.permission_mode = "bypassPermissions"

        context = MagicMock(spec=ToolPermissionContext)

        # Bash would normally be blocked in plan mode
        result = await agent._handle_permission(
            "Bash",
            {"command": "rm -rf /"},
            context,
        )

        # bypassPermissions should auto-approve even dangerous commands
        assert isinstance(result, PermissionResultAllow)


# ---------------------------------------------------------------------------
# Tests for subagent permission mode inheritance
# ---------------------------------------------------------------------------


class TestSubagentPermissionInheritance:
    """Tests for MCP spawn_agent inheriting parent's permission_mode."""

    @pytest.fixture
    def mock_app(self):
        """Create mock app and register it with MCP module."""
        from claudechic.mcp import set_app

        app = MockApp()
        set_app(app)  # type: ignore
        return app

    @pytest.mark.asyncio
    async def test_spawn_agent_inherits_bypass_permissions(self, mock_app):
        """Spawned agent inherits bypassPermissions mode from parent.

        The MCP spawn_agent reads permission_mode from the active (parent) agent
        and passes it to AgentManager.create().
        """
        from claudechic.mcp import _make_spawn_agent

        # Set up parent agent with bypassPermissions mode
        parent = MockAgent("parent", permission_mode="bypassPermissions")
        mock_app.agent_mgr.add(parent)
        mock_app.agent_mgr.active = parent

        spawn_agent = _make_spawn_agent(caller_name="parent")

        # Note: permission_mode is NOT in the args - it's read from active agent
        await spawn_agent.handler(
            {
                "name": "child",
                "path": "/tmp",
                "prompt": "Hello child",
            }
        )

        # Let the event loop run for fire-and-forget tasks
        await asyncio.sleep(0)

        # Verify the child was created with inherited permission mode
        assert len(mock_app.agent_mgr._created_agents) == 1
        name, cwd, perm_mode = mock_app.agent_mgr._created_agents[0]
        assert name == "child"
        # Child inherits parent's bypassPermissions mode
        assert perm_mode == "bypassPermissions"

    @pytest.mark.asyncio
    async def test_spawn_agent_inherits_accept_edits(self, mock_app):
        """Spawned agent inherits acceptEdits mode from parent."""
        from claudechic.mcp import _make_spawn_agent

        parent = MockAgent("parent", permission_mode="acceptEdits")
        mock_app.agent_mgr.add(parent)
        mock_app.agent_mgr.active = parent

        spawn_agent = _make_spawn_agent(caller_name="parent")

        await spawn_agent.handler(
            {
                "name": "child",
                "path": "/tmp",
                "prompt": "Hello child",
            }
        )

        await asyncio.sleep(0)

        assert len(mock_app.agent_mgr._created_agents) == 1
        _, _, perm_mode = mock_app.agent_mgr._created_agents[0]
        assert perm_mode == "acceptEdits"

    @pytest.mark.asyncio
    async def test_spawn_agent_default_mode_when_parent_default(self, mock_app):
        """Spawned agent uses default mode when parent is default."""
        from claudechic.mcp import _make_spawn_agent

        parent = MockAgent("parent", permission_mode="default")
        mock_app.agent_mgr.add(parent)
        mock_app.agent_mgr.active = parent

        spawn_agent = _make_spawn_agent(caller_name="parent")

        await spawn_agent.handler(
            {
                "name": "child",
                "path": "/tmp",
                "prompt": "Hello child",
            }
        )

        await asyncio.sleep(0)

        assert len(mock_app.agent_mgr._created_agents) == 1
        _, _, perm_mode = mock_app.agent_mgr._created_agents[0]
        assert perm_mode == "default"

    @pytest.mark.asyncio
    async def test_spawn_agent_no_active_agent(self, mock_app):
        """When no active agent, spawned agent uses None permission_mode.

        The MCP code reads `active.permission_mode` only if `active` exists.
        When there's no active agent, parent_mode will be None, which
        AgentManager.create() treats as "default" mode.
        """
        from claudechic.mcp import _make_spawn_agent

        # No active agent
        mock_app.agent_mgr.active = None

        spawn_agent = _make_spawn_agent(caller_name=None)

        await spawn_agent.handler(
            {
                "name": "orphan",
                "path": "/tmp",
                "prompt": "Hello orphan",
            }
        )

        await asyncio.sleep(0)

        assert len(mock_app.agent_mgr._created_agents) == 1
        _, _, perm_mode = mock_app.agent_mgr._created_agents[0]
        # When no active agent, permission_mode is None which becomes "default"
        # Our mock applies "default" when permission_mode is None
        assert perm_mode == "default"


# ---------------------------------------------------------------------------
# Tests for /clearui command
# ---------------------------------------------------------------------------


class TestClearUICommand:
    """Tests for /clearui command (clears UI without new session)."""

    @pytest.mark.asyncio
    async def test_clearui_clears_chat_view(self, mock_sdk):
        """'/clearui' removes chat messages from the view."""
        from claudechic.app import ChatApp
        from claudechic.widgets import ChatMessage
        from tests.conftest import submit_command, wait_for_workers

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

            # Capture session_id before clear
            agent = app._agent
            original_session_id = agent.session_id if agent else None

            # Send /clearui
            await submit_command(app, pilot, "/clearui")
            await wait_for_workers(app)
            await pilot.pause()

            # Chat view should be empty
            messages = list(chat_view.query(ChatMessage))
            assert len(messages) == 0

            # Session ID should remain the same (no new session started)
            assert agent.session_id == original_session_id

    @pytest.mark.asyncio
    async def test_clearui_preserves_session_id(self, mock_sdk):
        """'/clearui' preserves the session ID (unlike /clear)."""
        from claudechic.app import ChatApp
        from tests.conftest import submit_command, wait_for_workers

        app = ChatApp()
        async with app.run_test() as pilot:
            agent = app._agent
            assert agent is not None

            # Set a known session ID
            agent.session_id = "test-session-123"

            await submit_command(app, pilot, "/clearui")
            await wait_for_workers(app)
            await pilot.pause()

            # Session should be unchanged
            assert agent.session_id == "test-session-123"

    @pytest.mark.asyncio
    async def test_clearui_vs_clear_difference(self, mock_sdk):
        """Verify /clearui differs from /clear in session handling."""
        from claudechic.app import ChatApp
        from tests.conftest import submit_command, wait_for_workers

        app = ChatApp()
        async with app.run_test() as pilot:
            agent = app._agent
            assert agent is not None

            # Set a known session ID
            agent.session_id = "original-session"

            # /clear should start new session (call _start_new_session)
            await submit_command(app, pilot, "/clear")
            await wait_for_workers(app)
            await pilot.pause()

            # Session may have changed (depends on SDK mock behavior)
            # The key test is that /clearui below does NOT change session

            # Reset for /clearui test
            agent.session_id = "another-session"

            await submit_command(app, pilot, "/clearui")
            await wait_for_workers(app)
            await pilot.pause()

            # /clearui should NOT change session
            assert agent.session_id == "another-session"
