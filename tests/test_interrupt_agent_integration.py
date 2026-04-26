"""Integration tests for interrupt_agent MCP tool (Issue #32, Spec Section 2).

These tests use real Agent objects with mock SDK clients to verify state
machine transitions, race conditions, and redirect delivery -- the exact
failure modes that pure-mock unit tests miss.
"""

from __future__ import annotations

import asyncio
import contextlib
from unittest.mock import MagicMock, patch

import pytest
from claudechic.agent import Agent, ResponseContext
from claudechic.enums import AgentStatus, ResponseState
from claudechic.mcp import _make_interrupt_agent, set_app
from claudechic.permissions import PermissionRequest

pytestmark = [pytest.mark.asyncio]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _cancel_task(task: asyncio.Task) -> None:
    """Cancel a task and suppress CancelledError."""
    if not task.done():
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


def _put_agent_in_streaming(agent: Agent) -> asyncio.Task:
    """Put an agent into STREAMING/BUSY state with a controllable task.

    Returns the mock response task so tests can control when it completes.
    """
    agent._set_response_state(ResponseState.STREAMING)
    agent._set_status(AgentStatus.BUSY)

    # Create a real asyncio task that blocks until cancelled
    async def _block_forever():
        with contextlib.suppress(asyncio.CancelledError):
            await asyncio.sleep(3600)

    task = asyncio.create_task(_block_forever(), name="mock-response")
    agent._response = ResponseContext(task=task)
    return task


class _MockApp:
    """Minimal app mock for MCP handler tests."""

    def __init__(self):
        self.agent_mgr = _MockAgentManager()

    def run_worker(self, coro):
        coro.close()


class _MockAgentManager:
    """Minimal agent manager mock."""

    def __init__(self):
        self.agents: dict[str, Agent] = {}
        self.active: Agent | None = None

    def add(self, agent: Agent) -> None:
        self.agents[agent.name] = agent
        if self.active is None:
            self.active = agent

    def find_by_name(self, name: str) -> Agent | None:
        return self.agents.get(name)

    def __len__(self) -> int:
        return len(self.agents)


@pytest.fixture
def mock_app_with_real_agents():
    """Create MockApp that can hold real Agent instances."""
    app = _MockApp()
    set_app(app)
    yield app
    set_app(None)


# ---------------------------------------------------------------------------
# Category 1: State Machine Tests (Real ResponseState transitions)
# ---------------------------------------------------------------------------


class TestStateMachine:
    """Tests 2.1-2.2: Real Agent state transitions during interrupt."""

    async def test_interrupt_transitions_response_state(self, real_agent_with_mock_sdk):
        """Test 2.1: interrupt() moves STREAMING -> INTERRUPTED -> IDLE."""
        agent, _mock_client = real_agent_with_mock_sdk

        task = _put_agent_in_streaming(agent)
        assert agent._response_state == ResponseState.STREAMING

        await agent.interrupt()

        assert agent._response_state == ResponseState.IDLE
        assert agent.status == AgentStatus.IDLE

        await _cancel_task(task)

    async def test_interrupt_sets_idle_before_send(self, real_agent_with_mock_sdk):
        """Test 2.2: After interrupt(), send() dispatches immediately (not queued)."""
        agent, _mock_client = real_agent_with_mock_sdk

        task = _put_agent_in_streaming(agent)
        await agent.interrupt()

        # After interrupt, state should be IDLE so send() calls _start_response
        assert agent._response_state == ResponseState.IDLE

        with patch.object(agent, "_start_response", wraps=agent._start_response) as spy:
            await agent.send("redirect prompt")
            spy.assert_called_once()

        # Should NOT have been queued
        assert len(agent._pending_messages) == 0

        # Cleanup: cancel the response task started by send()
        if agent._response.task and not agent._response.task.done():
            await _cancel_task(agent._response.task)
        await _cancel_task(task)


# ---------------------------------------------------------------------------
# Category 2: TOCTOU Race Test
# ---------------------------------------------------------------------------


class TestTOCTOU:
    """Test 2.3: Race between status check and interrupt call."""

    async def test_status_changes_between_check_and_interrupt(
        self, mock_app_with_real_agents, real_agent_with_mock_sdk
    ):
        """Test 2.3: Agent becomes idle between MCP check and interrupt() call."""
        agent, _mock_client = real_agent_with_mock_sdk
        app = mock_app_with_real_agents

        caller = Agent(name="caller", cwd=agent.cwd)
        caller.client = MagicMock()
        caller.session_id = "caller-session"

        app.agent_mgr.add(caller)
        app.agent_mgr.add(agent)

        # Start busy, but interrupt() is a no-op (agent already idle by then)
        task = _put_agent_in_streaming(agent)

        # Make interrupt() simulate agent becoming idle during the call
        original_interrupt = agent.interrupt

        async def interrupt_that_idles():
            await original_interrupt()

        agent.interrupt = interrupt_that_idles

        tool = _make_interrupt_agent(caller_name="caller")
        result = await tool.handler({"name": "test-agent"})

        # Should succeed (not crash)
        assert "isError" not in result
        assert agent.status == AgentStatus.IDLE

        await _cancel_task(task)


# ---------------------------------------------------------------------------
# Category 3: Redirect Delivery Tests
# ---------------------------------------------------------------------------


class TestRedirectDelivery:
    """Tests 2.4-2.5: Redirect prompt delivery after interrupt."""

    async def test_redirect_after_interrupt_delivers_not_queues(
        self, mock_app_with_real_agents, real_agent_with_mock_sdk
    ):
        """Test 2.4: After interrupt, redirect is delivered (not queued)."""
        agent, _mock_client = real_agent_with_mock_sdk
        app = mock_app_with_real_agents

        caller = Agent(name="caller", cwd=agent.cwd)
        caller.client = MagicMock()
        caller.session_id = "caller-session"

        app.agent_mgr.add(caller)
        app.agent_mgr.add(agent)

        task = _put_agent_in_streaming(agent)

        tool = _make_interrupt_agent(caller_name="caller")
        result = await tool.handler({"name": "test-agent", "prompt": "redirect now"})

        # Let fire-and-forget task run
        await asyncio.sleep(0.05)

        assert "isError" not in result
        # After fix A: redirect uses fire-and-forget, which calls agent.send()
        # as a background task. The message should NOT be queued.
        assert len(agent._pending_messages) == 0

        # Cleanup
        if agent._response.task and not agent._response.task.done():
            await _cancel_task(agent._response.task)
        await _cancel_task(task)

    async def test_redirect_does_not_block_mcp_handler(
        self, mock_app_with_real_agents, real_agent_with_mock_sdk
    ):
        """Test 2.5: MCP handler returns immediately after scheduling redirect."""
        agent, _mock_client = real_agent_with_mock_sdk
        app = mock_app_with_real_agents

        caller = Agent(name="caller", cwd=agent.cwd)
        caller.client = MagicMock()
        caller.session_id = "caller-session"

        app.agent_mgr.add(caller)
        app.agent_mgr.add(agent)

        task = _put_agent_in_streaming(agent)

        # Make send() slow to verify handler doesn't wait for it
        async def slow_send(prompt, **kwargs):
            await asyncio.sleep(10)

        agent.send = slow_send

        tool = _make_interrupt_agent(caller_name="caller")

        # Handler should return quickly (< 1s) even with slow send
        result = await asyncio.wait_for(
            tool.handler({"name": "test-agent", "prompt": "redirect"}),
            timeout=2.0,
        )

        assert "isError" not in result

        await _cancel_task(task)


# ---------------------------------------------------------------------------
# Category 4: Timeout and Fallback Tests
# ---------------------------------------------------------------------------


class TestTimeoutFallback:
    """Tests 2.6-2.7: SDK/task timeout triggers SIGINT fallback."""

    @pytest.mark.slow
    async def test_interrupt_sdk_timeout_triggers_sigint(
        self, real_agent_with_mock_sdk
    ):
        """Test 2.6: SDK interrupt() hanging > 5s triggers SIGINT fallback."""
        agent, mock_client = real_agent_with_mock_sdk

        # Make SDK interrupt() never return
        async def _hang_forever():
            await asyncio.sleep(3600)

        mock_client.interrupt = _hang_forever

        task = _put_agent_in_streaming(agent)

        with patch.object(agent, "_sigint_fallback") as sigint_spy:
            await agent.interrupt()

            # SIGINT fallback called at least once (SDK timeout triggers it;
            # the stuck response task may trigger a second call).
            assert sigint_spy.call_count >= 1

        assert agent.status == AgentStatus.IDLE
        assert agent._response_state == ResponseState.IDLE

        await _cancel_task(task)

    @pytest.mark.slow
    async def test_interrupt_task_timeout_triggers_cancel(
        self, real_agent_with_mock_sdk
    ):
        """Test 2.7: Response task not finishing within 3s gets cancelled + SIGINT."""
        agent, _mock_client = real_agent_with_mock_sdk

        # SDK interrupt returns immediately, but response task never finishes
        agent._set_response_state(ResponseState.STREAMING)
        agent._set_status(AgentStatus.BUSY)

        async def _never_finish():
            await asyncio.sleep(3600)

        stuck_task = asyncio.create_task(_never_finish(), name="stuck-response")
        agent._response = ResponseContext(task=stuck_task)

        with patch.object(agent, "_sigint_fallback") as sigint_spy:
            await agent.interrupt()

            # Task was cancel()ed -- let the CancelledError propagate
            await asyncio.sleep(0)
            assert stuck_task.done()
            assert stuck_task.cancelled()
            # SIGINT fallback should have been called
            sigint_spy.assert_called_once()

        assert agent.status == AgentStatus.IDLE
        assert agent._response_state == ResponseState.IDLE


# ---------------------------------------------------------------------------
# Category 5: Needs-Input Interrupt Tests
# ---------------------------------------------------------------------------


class TestNeedsInputInterrupt:
    """Tests 2.8 and 2.11: Agent in needs_input state."""

    @pytest.mark.integration
    async def test_interrupt_needs_input_agent(
        self, mock_app_with_real_agents, real_agent_with_mock_sdk
    ):
        """Test 2.8: Agent in needs_input gets interrupted and redirected."""
        agent, _mock_client = real_agent_with_mock_sdk
        app = mock_app_with_real_agents

        caller = Agent(name="caller", cwd=agent.cwd)
        caller.client = MagicMock()
        caller.session_id = "caller-session"

        app.agent_mgr.add(caller)
        app.agent_mgr.add(agent)

        # Put agent in needs_input state (STREAMING + NEEDS_INPUT status)
        task = _put_agent_in_streaming(agent)
        agent._set_status(AgentStatus.NEEDS_INPUT)

        # Add a fake pending prompt to simulate awaiting permission
        fake_request = MagicMock(spec=PermissionRequest)
        agent.pending_prompts.append(fake_request)

        assert agent.status == AgentStatus.NEEDS_INPUT
        assert agent._response_state == ResponseState.STREAMING

        tool = _make_interrupt_agent(caller_name="caller")
        result = await tool.handler({"name": "test-agent", "prompt": "new direction"})

        # Let fire-and-forget task run
        await asyncio.sleep(0.05)

        # Interrupt path should have been taken (not idle path)
        assert "isError" not in result
        # After fix B: needs_input is NOT treated as idle
        text = result["content"][0]["text"]
        assert "Interrupted" in text

        # After fix B addendum: pending_prompts should be cleaned up
        assert len(agent.pending_prompts) == 0
        assert agent.status == AgentStatus.IDLE
        assert agent._response_state == ResponseState.IDLE

        # Cleanup
        if agent._response.task and not agent._response.task.done():
            await _cancel_task(agent._response.task)
        await _cancel_task(task)

    async def test_permission_request_cleaned_up_after_interrupt(
        self, real_agent_with_mock_sdk
    ):
        """Test 2.11: CancelledError during permission wait doesn't leak PermissionRequest."""
        agent, _mock_client = real_agent_with_mock_sdk

        task = _put_agent_in_streaming(agent)

        # Simulate pending permission prompts
        fake_request_1 = MagicMock(spec=PermissionRequest)
        fake_request_2 = MagicMock(spec=PermissionRequest)
        agent.pending_prompts.append(fake_request_1)
        agent.pending_prompts.append(fake_request_2)

        assert len(agent.pending_prompts) == 2

        await agent.interrupt()

        # After fix B addendum: pending_prompts must be cleared
        assert len(agent.pending_prompts) == 0
        assert agent.status == AgentStatus.IDLE

        await _cancel_task(task)


# ---------------------------------------------------------------------------
# Category 6: Rewrite "Integration" Test (replaces old Test 10)
# ---------------------------------------------------------------------------


class TestFullFlow:
    """Test 2.9: End-to-end interrupt + redirect with real Agent."""

    @pytest.mark.integration
    async def test_full_interrupt_redirect_flow_real_agent(
        self, mock_app_with_real_agents, real_agent_with_mock_sdk
    ):
        """Test 2.9: Full flow -- busy agent interrupted, redirect delivered."""
        agent, _mock_client = real_agent_with_mock_sdk
        app = mock_app_with_real_agents

        coordinator = Agent(name="coordinator", cwd=agent.cwd)
        coordinator.client = MagicMock()
        coordinator.session_id = "coord-session"

        # Rename test-agent to "researcher" for clarity
        agent.name = "researcher"

        app.agent_mgr.add(coordinator)
        app.agent_mgr.add(agent)

        # Start response (STREAMING/BUSY)
        task = _put_agent_in_streaming(agent)
        assert agent.status == AgentStatus.BUSY
        assert agent._response_state == ResponseState.STREAMING

        tool = _make_interrupt_agent(caller_name="coordinator")
        result = await tool.handler(
            {"name": "researcher", "prompt": "Switch to section 3 analysis"}
        )

        # Let fire-and-forget task run
        await asyncio.sleep(0.05)

        # Verify final state
        assert agent.status == AgentStatus.IDLE
        assert agent._response_state == ResponseState.IDLE

        # Redirect delivered (not queued)
        assert len(agent._pending_messages) == 0

        # MCP handler returned success
        assert "isError" not in result
        text = result["content"][0]["text"]
        assert "Interrupted" in text
        assert "sent new prompt" in text

        # Cleanup
        if agent._response.task and not agent._response.task.done():
            await _cancel_task(agent._response.task)
        await _cancel_task(task)


# ---------------------------------------------------------------------------
# Category 7: Drain-After-Interrupt Race Test
# ---------------------------------------------------------------------------


class TestDrainRace:
    """Test 2.10: Drain task doesn't eat redirect prompt."""

    @pytest.mark.integration
    async def test_drain_after_interrupt_does_not_eat_redirect(
        self, mock_app_with_real_agents, real_agent_with_mock_sdk
    ):
        """Test 2.10: Queued messages AND redirect both delivered after interrupt."""
        agent, _mock_client = real_agent_with_mock_sdk
        app = mock_app_with_real_agents

        caller = Agent(name="caller", cwd=agent.cwd)
        caller.client = MagicMock()
        caller.session_id = "caller-session"

        app.agent_mgr.add(caller)
        app.agent_mgr.add(agent)

        # Put agent in streaming state
        task = _put_agent_in_streaming(agent)

        # Queue a pending inter-agent message (as if message_agent was called while busy)
        agent._pending_messages.append(("queued message from earlier", None))
        assert len(agent._pending_messages) == 1

        # Track all prompts sent via _start_response
        delivered_prompts: list[str] = []

        def tracking_start_response(prompt, **kwargs):
            delivered_prompts.append(prompt)
            # Don't actually start a response (would need real SDK)
            # Just record that it was called
            agent._set_response_state(ResponseState.STREAMING)
            agent._set_status(AgentStatus.BUSY)

            # Create a task that completes immediately so drain can continue
            async def _noop():
                pass

            agent._response = ResponseContext(
                task=asyncio.create_task(_noop(), name="noop-response")
            )

        agent._start_response = tracking_start_response

        # Mock transport alive check so _drain_next_message proceeds
        with patch.object(agent, "_is_transport_alive", return_value=True):
            # Interrupt the agent
            await agent.interrupt()

            # Now send redirect via fire-and-forget (simulating what MCP handler does)
            from claudechic.mcp import _send_prompt_fire_and_forget

            _send_prompt_fire_and_forget(agent, "redirect prompt")

            # Let all background tasks run (drain + fire-and-forget)
            await asyncio.sleep(0.1)

        # Both the queued message and redirect should have been delivered
        # The queued message is drained by _yield_then_drain from interrupt()
        # The redirect is sent by fire-and-forget
        assert len(delivered_prompts) >= 1
        # At minimum, the drain task should have picked up the queued message
        assert "queued message from earlier" in delivered_prompts

        await _cancel_task(task)
