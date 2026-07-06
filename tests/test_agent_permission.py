"""Tests for Agent permission functionality."""

from __future__ import annotations

from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from claudechic.agent import Agent


async def empty_async_gen():
    """Empty async generator for mocking receive_response."""
    return
    yield  # unreachable - makes this an async generator


@pytest.fixture
def mock_sdk_for_agent():
    """Create a mock SDK client for agent tests."""
    mock_client = MagicMock()
    mock_client.connect = AsyncMock()
    mock_client.query = AsyncMock()
    mock_client.interrupt = AsyncMock()
    mock_client.disconnect = AsyncMock()
    mock_client.set_permission_mode = AsyncMock()
    mock_client.receive_response = lambda: empty_async_gen()
    mock_client._transport = None

    # Mock FileIndex to avoid subprocess issues
    from claudechic.file_index import FileIndex

    mock_file_index = MagicMock(spec=FileIndex)
    mock_file_index.refresh = AsyncMock()
    mock_file_index.files = []

    with ExitStack() as stack:
        stack.enter_context(
            patch("claudechic.agent.ClaudeSDKClient", return_value=mock_client)
        )
        stack.enter_context(
            patch("claudechic.agent.FileIndex", return_value=mock_file_index)
        )
        # Patch get_claude_pid_from_client to avoid process introspection
        stack.enter_context(
            patch("claudechic.processes.get_claude_pid_from_client", return_value=None)
        )
        yield mock_client


class TestPermissionModes:
    """Tests for PERMISSION_MODES set."""

    def test_bypassPermissions_in_modes(self):
        """Verify 'bypassPermissions' is in PERMISSION_MODES."""
        assert "bypassPermissions" in Agent.PERMISSION_MODES

    def test_all_expected_modes_present(self):
        """Verify all expected permission modes are present."""
        expected = {
            "default",
            "auto",
            "acceptEdits",
            "plan",
            "bypassPermissions",
        }
        assert expected == Agent.PERMISSION_MODES

    def test_permission_modes_is_set(self):
        """Verify PERMISSION_MODES is a set (not list/tuple)."""
        assert isinstance(Agent.PERMISSION_MODES, set)


class TestConnectPermissionMode:
    """Tests for SDK notification after connect."""

    @pytest.mark.asyncio
    async def test_set_permission_mode_called_after_connect_if_not_default(
        self, mock_sdk_for_agent, tmp_path
    ):
        """Verify set_permission_mode is called AFTER connect if mode != 'default'."""
        agent = Agent("test", tmp_path)
        agent.permission_mode = "acceptEdits"

        from claude_agent_sdk import ClaudeAgentOptions

        options = ClaudeAgentOptions(permission_mode="default")
        await agent.connect(options)

        # Verify connect was called first
        mock_sdk_for_agent.connect.assert_called_once()

        # Verify set_permission_mode was called with the correct mode
        mock_sdk_for_agent.set_permission_mode.assert_called_once_with("acceptEdits")

    @pytest.mark.asyncio
    async def test_set_permission_mode_not_called_if_default(
        self, mock_sdk_for_agent, tmp_path
    ):
        """Verify set_permission_mode is NOT called if permission_mode == 'default'."""
        agent = Agent("test", tmp_path)
        agent.permission_mode = "default"  # Default mode

        from claude_agent_sdk import ClaudeAgentOptions

        options = ClaudeAgentOptions(permission_mode="default")
        await agent.connect(options)

        # Verify connect was called
        mock_sdk_for_agent.connect.assert_called_once()

        # Verify set_permission_mode was NOT called
        mock_sdk_for_agent.set_permission_mode.assert_not_called()

    @pytest.mark.asyncio
    async def test_set_permission_mode_called_with_plan_mode(
        self, mock_sdk_for_agent, tmp_path
    ):
        """Verify set_permission_mode works with 'plan' mode."""
        agent = Agent("test", tmp_path)
        agent.permission_mode = "plan"

        from claude_agent_sdk import ClaudeAgentOptions

        options = ClaudeAgentOptions(permission_mode="default")
        await agent.connect(options)

        mock_sdk_for_agent.set_permission_mode.assert_called_once_with("plan")

    @pytest.mark.asyncio
    async def test_set_permission_mode_called_with_bypassPermissions(
        self, mock_sdk_for_agent, tmp_path
    ):
        """Verify set_permission_mode works with 'bypassPermissions' mode."""
        agent = Agent("test", tmp_path)
        agent.permission_mode = "bypassPermissions"

        from claude_agent_sdk import ClaudeAgentOptions

        options = ClaudeAgentOptions(permission_mode="default")
        await agent.connect(options)

        mock_sdk_for_agent.set_permission_mode.assert_called_once_with(
            "bypassPermissions"
        )


class TestSetPermissionModeMethod:
    """Tests for Agent.set_permission_mode() method."""

    @pytest.mark.asyncio
    async def test_updates_permission_mode_field(self, mock_sdk_for_agent, tmp_path):
        """Verify set_permission_mode updates the permission_mode field."""
        agent = Agent("test", tmp_path)
        assert agent.permission_mode == "auto"

        await agent.set_permission_mode("acceptEdits")
        assert agent.permission_mode == "acceptEdits"

        await agent.set_permission_mode("plan")
        assert agent.permission_mode == "plan"

    @pytest.mark.asyncio
    async def test_calls_sdk_if_session_exists(self, mock_sdk_for_agent, tmp_path):
        """Verify set_permission_mode calls SDK if session exists."""
        agent = Agent("test", tmp_path)

        from claude_agent_sdk import ClaudeAgentOptions

        options = ClaudeAgentOptions(permission_mode="default")
        await agent.connect(options)

        # Clear the call from connect
        mock_sdk_for_agent.set_permission_mode.reset_mock()

        # Set a session_id (simulating active session)
        agent.session_id = "test-session-123"

        await agent.set_permission_mode("acceptEdits")

        # Should call SDK since session exists
        mock_sdk_for_agent.set_permission_mode.assert_called_once_with("acceptEdits")

    @pytest.mark.asyncio
    async def test_does_not_call_sdk_if_no_session(self, tmp_path):
        """Verify set_permission_mode does NOT call SDK if no session exists."""
        agent = Agent("test", tmp_path)
        agent.client = MagicMock()
        agent.client.set_permission_mode = AsyncMock()
        agent.session_id = None  # No session

        await agent.set_permission_mode("acceptEdits")

        # Should NOT call SDK since no session
        agent.client.set_permission_mode.assert_not_called()

    @pytest.mark.asyncio
    async def test_does_not_call_sdk_if_no_client(self, tmp_path):
        """Verify set_permission_mode does NOT call SDK if no client exists."""
        agent = Agent("test", tmp_path)
        agent.client = None
        agent.session_id = "test-session-123"

        # Should not raise even with no client
        await agent.set_permission_mode("acceptEdits")
        assert agent.permission_mode == "acceptEdits"

    @pytest.mark.asyncio
    async def test_no_change_if_same_mode(self, tmp_path):
        """Verify set_permission_mode does nothing if mode unchanged."""
        agent = Agent("test", tmp_path)
        agent.permission_mode = "acceptEdits"
        agent.client = MagicMock()
        agent.client.set_permission_mode = AsyncMock()
        agent.session_id = "test-session"

        await agent.set_permission_mode("acceptEdits")

        # Should NOT call SDK since mode is unchanged
        agent.client.set_permission_mode.assert_not_called()

    @pytest.mark.asyncio
    async def test_notifies_observer(self, tmp_path):
        """Verify set_permission_mode notifies observer when mode changes."""
        agent = Agent("test", tmp_path)
        mock_observer = MagicMock()
        agent.observer = mock_observer

        await agent.set_permission_mode("plan")

        mock_observer.on_permission_mode_changed.assert_called_once_with(agent)

    @pytest.mark.asyncio
    async def test_does_not_notify_observer_if_unchanged(self, tmp_path):
        """Verify observer is NOT notified if mode unchanged."""
        agent = Agent("test", tmp_path)
        agent.permission_mode = "acceptEdits"
        mock_observer = MagicMock()
        agent.observer = mock_observer

        await agent.set_permission_mode("acceptEdits")

        mock_observer.on_permission_mode_changed.assert_not_called()

    @pytest.mark.asyncio
    async def test_invalid_mode_raises(self, tmp_path):
        """Verify invalid permission mode raises AssertionError."""
        agent = Agent("test", tmp_path)

        with pytest.raises(AssertionError, match="Invalid permission mode"):
            await agent.set_permission_mode("invalid_mode")


class TestSetPermissionModeLocal:
    """Tests for Agent._set_permission_mode_local() method."""

    def test_updates_field_without_sdk_call(self, tmp_path):
        """Verify _set_permission_mode_local updates field without SDK call."""
        agent = Agent("test", tmp_path)
        agent.client = MagicMock()
        agent.client.set_permission_mode = AsyncMock()
        agent.session_id = "test-session"

        agent._set_permission_mode_local("plan")

        assert agent.permission_mode == "plan"
        # Should NOT call SDK
        agent.client.set_permission_mode.assert_not_called()

    def test_notifies_observer(self, tmp_path):
        """Verify _set_permission_mode_local notifies observer."""
        agent = Agent("test", tmp_path)
        mock_observer = MagicMock()
        agent.observer = mock_observer

        agent._set_permission_mode_local("acceptEdits")

        mock_observer.on_permission_mode_changed.assert_called_once_with(agent)

    def test_invalid_mode_raises(self, tmp_path):
        """Verify invalid mode raises AssertionError."""
        agent = Agent("test", tmp_path)

        with pytest.raises(AssertionError, match="Invalid permission mode"):
            agent._set_permission_mode_local("not_a_valid_mode")

    def test_does_not_notify_if_unchanged(self, tmp_path):
        """Verify observer is NOT notified if mode unchanged."""
        agent = Agent("test", tmp_path)
        agent.permission_mode = "plan"
        mock_observer = MagicMock()
        agent.observer = mock_observer

        agent._set_permission_mode_local("plan")

        mock_observer.on_permission_mode_changed.assert_not_called()


class TestAutoModeAutoApproves:
    """Auto mode: _handle_permission must approve without prompting.

    The CLI normally auto-approves in auto mode and never invokes
    can_use_tool, but a mode-sync race (mode set before session_id
    exists is silently skipped) can leave the CLI in the old mode and
    routing tools through the callback while the UI shows "auto".
    """

    @pytest.mark.asyncio
    async def test_handle_permission_auto_mode_approves_all(self, tmp_path):
        from claude_agent_sdk import PermissionResultAllow

        agent = Agent("test", tmp_path)
        agent.permission_mode = "auto"

        for tool_name, tool_input in [
            ("Bash", {"command": "ls"}),
            ("Write", {"file_path": str(tmp_path / "f.txt"), "content": "x"}),
            ("WebFetch", {"url": "https://example.com"}),
        ]:
            result = await agent._handle_permission(
                tool_name, tool_input, MagicMock()
            )
            assert isinstance(result, PermissionResultAllow), tool_name
        # Nothing queued for the UI: the user was never prompted.
        assert len(agent.pending_prompts) == 0


# ---------------------------------------------------------------------------
# Plan mode enforcement
#
# The PreToolUse hook (app.py:_plan_mode_pre_tool_use_decision) is the
# primary enforcer; agent._handle_permission keeps a defense-in-depth deny
# and captures plan_path for the ExitPlanMode UI.
# ---------------------------------------------------------------------------


def _hook_input(mode: str, tool: str, **inp: object) -> dict:
    return {"permission_mode": mode, "tool_name": tool, "tool_input": inp}


class TestPlanModeHook:
    """Tests for the plan-mode PreToolUse hook decision function."""

    def test_allows_bash(self):
        """Bash is read-only-friendly and must NOT be blocked in plan mode.

        Regression: we used to block all Bash, which broke Explore
        subagents that rely on Bash for `find`, `git ls-files`, etc.
        """
        from claudechic.app import _plan_mode_pre_tool_use_decision

        out = _plan_mode_pre_tool_use_decision(
            _hook_input("plan", "Bash", command="git status")
        )
        assert out == {}

    def test_denies_edit_with_modern_shape(self):
        """Edit on a non-plan file is denied via the modern hookSpecificOutput shape."""
        from claudechic.app import _plan_mode_pre_tool_use_decision

        out = _plan_mode_pre_tool_use_decision(
            _hook_input(
                "plan", "Edit", file_path="/tmp/foo.py", old_string="a", new_string="b"
            )
        )
        assert "decision" not in out  # legacy shape is gone
        spec = out["hookSpecificOutput"]
        assert spec["hookEventName"] == "PreToolUse"
        assert spec["permissionDecision"] == "deny"
        assert "plan mode" in spec["permissionDecisionReason"]

    def test_denies_write_and_notebook_edit(self):
        from claudechic.app import _plan_mode_pre_tool_use_decision

        for tool in ("Write", "NotebookEdit"):
            out = _plan_mode_pre_tool_use_decision(
                _hook_input("plan", tool, file_path="/tmp/foo")
            )
            assert out["hookSpecificOutput"]["permissionDecision"] == "deny", tool

    def test_allows_writes_to_plan_file(self, tmp_path, monkeypatch):
        """Writes under ~/.claude/plans/ are the one carve-out."""
        from claudechic.app import _plan_mode_pre_tool_use_decision

        monkeypatch.setattr("claudechic.app.Path.home", lambda: tmp_path)
        plan_file = tmp_path / ".claude" / "plans" / "my-plan.md"
        plan_file.parent.mkdir(parents=True)
        out = _plan_mode_pre_tool_use_decision(
            _hook_input("plan", "Write", file_path=str(plan_file), content="...")
        )
        assert out == {}

    def test_rejects_lookalike_plans_dir(self, tmp_path, monkeypatch):
        """startswith would match ~/.claude/plans-evil/; is_relative_to must not."""
        from claudechic.app import _plan_mode_pre_tool_use_decision

        monkeypatch.setattr("claudechic.app.Path.home", lambda: tmp_path)
        sneaky = tmp_path / ".claude" / "plans-evil" / "x.md"
        sneaky.parent.mkdir(parents=True)
        out = _plan_mode_pre_tool_use_decision(
            _hook_input("plan", "Write", file_path=str(sneaky), content="x")
        )
        assert out["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_passthrough_outside_plan_mode(self):
        """Hook is a no-op when not in plan mode."""
        from claudechic.app import _plan_mode_pre_tool_use_decision

        for mode in ("default", "acceptEdits", "auto"):
            out = _plan_mode_pre_tool_use_decision(
                _hook_input(
                    mode, "Edit", file_path="/tmp/foo", old_string="a", new_string="b"
                )
            )
            assert out == {}, mode


class TestPlanModeHandlePermission:
    """Agent-side plan-mode behavior (defense-in-depth + plan_path capture)."""

    @pytest.mark.asyncio
    async def test_bash_not_blocked_by_plan_branch(self, tmp_path):
        """Plan-mode Bash falls through to the normal permission queue.

        It must NOT be denied outright (read-only Bash is legitimate in
        plan mode); it reaches the normal prompt flow instead.
        """
        from claudechic.permissions import PermissionResponse
        from claudechic.enums import PermissionChoice

        agent = Agent("test", tmp_path)
        agent.permission_mode = "plan"

        async def approve(agent_, request):
            return PermissionResponse(PermissionChoice.ALLOW)

        agent.permission_handler = approve
        result = await agent._handle_permission(
            "Bash", {"command": "git status"}, MagicMock()
        )
        from claude_agent_sdk import PermissionResultAllow

        assert isinstance(result, PermissionResultAllow)

    @pytest.mark.asyncio
    async def test_plan_file_write_captures_plan_path(self, tmp_path, monkeypatch):
        """Plan-file Write is auto-approved and captures agent.plan_path."""
        from claude_agent_sdk import PermissionResultAllow

        monkeypatch.setattr("claudechic.agent.Path.home", lambda: tmp_path)
        plan_file = tmp_path / ".claude" / "plans" / "session.md"
        plan_file.parent.mkdir(parents=True)

        agent = Agent("test", tmp_path)
        agent.permission_mode = "plan"
        result = await agent._handle_permission(
            "Write", {"file_path": str(plan_file), "content": "..."}, MagicMock()
        )

        assert isinstance(result, PermissionResultAllow)
        assert agent.plan_path == plan_file.resolve()

    @pytest.mark.asyncio
    async def test_defense_in_depth_denies_edit(self, tmp_path):
        """If the hook misfires and a non-plan-file Edit reaches can_use_tool, deny."""
        from claude_agent_sdk import PermissionResultDeny

        agent = Agent("test", tmp_path)
        agent.permission_mode = "plan"
        result = await agent._handle_permission(
            "Edit",
            {"file_path": "/tmp/not-a-plan.py", "old_string": "a", "new_string": "b"},
            MagicMock(),
        )
        assert isinstance(result, PermissionResultDeny)
        assert "plan mode" in result.message

    @pytest.mark.asyncio
    async def test_lookalike_plans_dir_denied(self, tmp_path, monkeypatch):
        """~/.claude/plans-evil/ must not pass the plan-file carve-out."""
        from claude_agent_sdk import PermissionResultDeny

        monkeypatch.setattr("claudechic.agent.Path.home", lambda: tmp_path)
        sneaky = tmp_path / ".claude" / "plans-evil" / "x.md"
        sneaky.parent.mkdir(parents=True)

        agent = Agent("test", tmp_path)
        agent.permission_mode = "plan"
        result = await agent._handle_permission(
            "Write", {"file_path": str(sneaky), "content": "x"}, MagicMock()
        )
        assert isinstance(result, PermissionResultDeny)
