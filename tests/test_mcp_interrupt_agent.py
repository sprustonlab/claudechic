"""Tests for the interrupt_agent MCP tool.

Covers all 9 unit tests and 1 integration test from the spec (Issue #10, Section 8).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from claudechic.mcp import _make_interrupt_agent, set_app

pytestmark = [pytest.mark.asyncio]


# ---------------------------------------------------------------------------
# Mock helpers (follows test_mcp_ask_agent.py patterns)
# ---------------------------------------------------------------------------


class MockAgent:
    """Minimal agent mock for MCP tool tests."""

    def __init__(self, name: str, status: str = "idle"):
        self.name = name
        self.id = name
        self.session_id = f"session-{name}"
        self.cwd = "/tmp"
        self.status = status
        self.worktree = None
        self.client = True  # truthy
        self.received_prompt: str | None = None
        self._pending_reply_to: str | None = None
        self._reply_nudge_count = 0
        self._nudge_generation = 0

        # Async mocks for interrupt and send
        self.interrupt = AsyncMock()
        self.send = AsyncMock(side_effect=self._capture_send)

    @property
    def analytics_id(self) -> str:
        return self.session_id or self.id

    async def _capture_send(self, prompt: str) -> None:
        self.received_prompt = prompt


class MockAgentManager:
    """Minimal agent manager mock."""

    def __init__(self) -> None:
        self.agents: dict[str, MockAgent] = {}
        self.active: MockAgent | None = None

    def add(self, agent: MockAgent) -> None:
        self.agents[agent.name] = agent
        if self.active is None:
            self.active = agent

    def find_by_name(self, name: str) -> MockAgent | None:
        return self.agents.get(name)

    def __len__(self) -> int:
        return len(self.agents)


class MockApp:
    """Minimal app mock."""

    def __init__(self) -> None:
        self.agent_mgr = MockAgentManager()

    def run_worker(self, coro: Any) -> None:
        """Close coroutine to avoid RuntimeWarning."""
        coro.close()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_app():
    """Create a MockApp and register it via set_app."""
    app = MockApp()
    set_app(app)  # type: ignore[arg-type]
    yield app
    set_app(None)  # type: ignore[arg-type]


@pytest.fixture
def two_agents(mock_app):
    """Set up two agents: 'alice' (caller) and 'bob' (target)."""
    alice = MockAgent("alice")
    bob = MockAgent("bob", status="idle")
    mock_app.agent_mgr.add(alice)
    mock_app.agent_mgr.add(bob)
    return alice, bob


# ---------------------------------------------------------------------------
# Unit Tests
# ---------------------------------------------------------------------------


class TestBusyAgent:
    """Tests 1-2: Busy agent interrupt scenarios."""

    async def test_busy_no_redirect(self, two_agents):
        """Test 1: Busy agent, no redirect -- interrupt() called, correct message."""
        _alice, bob = two_agents
        bob.status = "busy"

        tool = _make_interrupt_agent(caller_name="alice")
        result = await tool.handler({"name": "bob"})

        bob.interrupt.assert_awaited_once()
        bob.send.assert_not_awaited()
        assert result["content"][0]["text"] == "Interrupted 'bob'"
        assert "isError" not in result

    async def test_busy_with_redirect(self, two_agents):
        """Test 2: Busy agent, with redirect -- interrupt() then fire-and-forget."""
        _alice, bob = two_agents
        bob.status = "busy"

        tool = _make_interrupt_agent(caller_name="alice")
        with patch("claudechic.mcp._send_prompt_fire_and_forget") as mock_fire:
            result = await tool.handler({"name": "bob", "prompt": "Do something else"})

        bob.interrupt.assert_awaited_once()
        # Redirect uses fire-and-forget with pre-wrapped prefix
        mock_fire.assert_called_once()
        sent_prompt = mock_fire.call_args[0][1]
        assert "[Redirected by agent 'alice']" in sent_prompt
        assert "Do something else" in sent_prompt
        assert result["content"][0]["text"] == "Interrupted 'bob' and sent new prompt"
        assert "isError" not in result


class TestIdleAgent:
    """Tests 3-4: Idle agent scenarios."""

    async def test_idle_no_redirect(self, two_agents):
        """Test 3: Idle agent, no redirect -- interrupt() NOT called."""
        _alice, bob = two_agents
        bob.status = "idle"

        tool = _make_interrupt_agent(caller_name="alice")
        result = await tool.handler({"name": "bob"})

        bob.interrupt.assert_not_awaited()
        bob.send.assert_not_awaited()
        assert result["content"][0]["text"] == "Agent 'bob' is not currently busy"
        assert "isError" not in result

    async def test_idle_with_redirect(self, two_agents):
        """Test 4: Idle agent, with redirect -- uses _send_prompt_fire_and_forget."""
        _alice, bob = two_agents
        bob.status = "idle"

        tool = _make_interrupt_agent(caller_name="alice")
        with patch("claudechic.mcp._send_prompt_fire_and_forget") as mock_fire:
            result = await tool.handler({"name": "bob", "prompt": "New task"})

        bob.interrupt.assert_not_awaited()
        mock_fire.assert_called_once_with(bob, "New task", caller_name="alice")
        assert result["content"][0]["text"] == "Agent 'bob' was idle; sent new prompt"
        assert "isError" not in result


class TestErrorCases:
    """Tests 5-8: Error handling scenarios."""

    async def test_self_interrupt_prevention(self, two_agents):
        """Test 5: Agent cannot interrupt itself."""
        tool = _make_interrupt_agent(caller_name="alice")
        result = await tool.handler({"name": "alice"})

        assert result["isError"] is True
        assert "cannot interrupt itself" in result["content"][0]["text"]

    async def test_agent_not_found(self, mock_app):
        """Test 6: Non-existent agent returns error."""
        tool = _make_interrupt_agent(caller_name="alice")
        result = await tool.handler({"name": "ghost"})

        assert result["isError"] is True
        assert "ghost" in result["content"][0]["text"]
        assert "not found" in result["content"][0]["text"]

    async def test_interrupt_failure(self, two_agents):
        """Test 7: interrupt() raises -- error returned, send() NOT called."""
        _alice, bob = two_agents
        bob.status = "busy"
        bob.interrupt = AsyncMock(side_effect=RuntimeError("SDK timeout"))

        tool = _make_interrupt_agent(caller_name="alice")
        result = await tool.handler({"name": "bob", "prompt": "Redirect"})

        assert result["isError"] is True
        assert "Failed to interrupt 'bob'" in result["content"][0]["text"]
        assert "SDK timeout" in result["content"][0]["text"]
        bob.send.assert_not_awaited()

    async def test_redirect_uses_fire_and_forget(self, two_agents):
        """Test 8: Redirect after interrupt uses fire-and-forget (can't raise)."""
        _alice, bob = two_agents
        bob.status = "busy"

        tool = _make_interrupt_agent(caller_name="alice")
        with patch("claudechic.mcp._send_prompt_fire_and_forget") as mock_fire:
            result = await tool.handler({"name": "bob", "prompt": "Redirect"})

        bob.interrupt.assert_awaited_once()
        # Fire-and-forget handles errors internally -- no partial-success path
        mock_fire.assert_called_once()
        assert result["content"][0]["text"] == "Interrupted 'bob' and sent new prompt"
        assert "isError" not in result


class TestRedirectPrefix:
    """Test 9: Redirect message prefix."""

    async def test_redirect_prefix_with_caller(self, two_agents):
        """Test 9: Verify [Redirected by agent '...'] prefix when caller_name set."""
        _alice, bob = two_agents
        bob.status = "busy"

        tool = _make_interrupt_agent(caller_name="alice")
        with patch("claudechic.mcp._send_prompt_fire_and_forget") as mock_fire:
            await tool.handler({"name": "bob", "prompt": "Focus on section 3"})

        mock_fire.assert_called_once()
        sent_prompt = mock_fire.call_args[0][1]
        assert sent_prompt.startswith("[Redirected by agent 'alice']")
        assert "Focus on section 3" in sent_prompt

    async def test_redirect_prefix_without_caller(self, two_agents):
        """No prefix when caller_name is None."""
        _alice, bob = two_agents
        bob.status = "busy"

        tool = _make_interrupt_agent(caller_name=None)
        with patch("claudechic.mcp._send_prompt_fire_and_forget") as mock_fire:
            await tool.handler({"name": "bob", "prompt": "Focus on section 3"})

        mock_fire.assert_called_once()
        sent_prompt = mock_fire.call_args[0][1]
        # Without caller, prompt should be sent as-is
        assert sent_prompt == "Focus on section 3"


# ---------------------------------------------------------------------------
# Integration Test
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestInterruptIntegration:
    """Test 10: Full flow with mock SDK -- two agents, interrupt mid-response."""

    async def test_full_interrupt_and_redirect_flow(self, mock_app):
        """Two agents: coordinator interrupts a busy researcher and redirects."""
        coordinator = MockAgent("coordinator")
        researcher = MockAgent("researcher", status="busy")
        mock_app.agent_mgr.add(coordinator)
        mock_app.agent_mgr.add(researcher)

        # Simulate interrupt transitioning status to idle
        async def interrupt_side_effect():
            researcher.status = "idle"

        researcher.interrupt = AsyncMock(side_effect=interrupt_side_effect)

        tool = _make_interrupt_agent(caller_name="coordinator")
        with patch("claudechic.mcp._send_prompt_fire_and_forget") as mock_fire:
            result = await tool.handler(
                {"name": "researcher", "prompt": "Switch to section 3 analysis"}
            )

        # Verify the full sequence
        researcher.interrupt.assert_awaited_once()

        # Redirect uses fire-and-forget with pre-wrapped prefix
        mock_fire.assert_called_once()
        sent_prompt = mock_fire.call_args[0][1]
        assert "[Redirected by agent 'coordinator']" in sent_prompt
        assert "Switch to section 3 analysis" in sent_prompt

        assert (
            result["content"][0]["text"]
            == "Interrupted 'researcher' and sent new prompt"
        )
        assert "isError" not in result
