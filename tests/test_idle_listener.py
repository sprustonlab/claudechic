"""Tests for the idle-time SDK stream listener (CLI-initiated turns).

Covers the Monitor / background-task notification delivery path: the CLI
can start a turn on its own while no client request is in flight (e.g. a
Monitor tool fires). The idle listener must consume the turn, render the
injected user text and assistant reply, reset agent state, and drain any
messages queued meanwhile. See Agent._idle_listener.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from claude_agent_sdk import AssistantMessage, ResultMessage, UserMessage
from claude_agent_sdk import TextBlock as SDKTextBlock

from claudechic.agent import Agent
from claudechic.enums import AgentStatus, ResponseState

pytestmark = pytest.mark.asyncio


def _result_message(**overrides) -> ResultMessage:
    defaults = dict(
        subtype="success",
        duration_ms=1,
        duration_api_ms=1,
        is_error=False,
        num_turns=1,
        session_id="sess-1",
    )
    defaults.update(overrides)
    return ResultMessage(**defaults)


async def _wait_until(predicate, timeout: float = 2.0) -> None:
    """Poll predicate until true (or fail the test after timeout)."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while not predicate():
        if loop.time() > deadline:
            pytest.fail("condition not reached within timeout")
        await asyncio.sleep(0.01)


@pytest.fixture
def make_agent_with_scripted_stream(tmp_path):
    """Build an Agent whose mock client serves scripted receive_response turns.

    ``turns`` is a list of message lists; each receive_response() call pops
    and yields one turn. Once exhausted, further calls block forever
    (simulating an open stream with no traffic).
    """

    def _make(turns: list[list]) -> Agent:
        agent = Agent(name="idle-test", cwd=tmp_path)
        client = MagicMock()
        remaining = list(turns)

        def receive_response():
            async def _gen():
                if not remaining:
                    await asyncio.sleep(3600)  # open stream, no traffic
                    return
                for msg in remaining.pop(0):
                    yield msg

            return _gen()

        client.receive_response = receive_response
        client.query = AsyncMock()
        client.interrupt = AsyncMock()
        # Expose the script so tests can append turns (e.g. when query() is
        # called, mirroring the CLI only responding after a prompt is sent).
        client._script = remaining
        # Make _is_transport_alive() report a live subprocess
        client._query.transport._process.pid = 12345
        client._query.transport._process.returncode = None
        agent.client = client
        agent._idle_listener_enabled = True
        return agent

    return _make


class TestIdleListenerDelivery:
    """CLI-initiated turns are consumed and rendered while idle."""

    async def test_delivers_cli_initiated_turn(self, make_agent_with_scripted_stream):
        turn = [
            UserMessage(
                content=(
                    "<task-notification>Monitor fired: CI is green</task-notification>"
                )
            ),
            AssistantMessage(
                content=[SDKTextBlock(text="CI is green, proceeding.")],
                model="claude-test",
            ),
            _result_message(),
        ]
        agent = make_agent_with_scripted_stream([turn])
        observer = MagicMock()
        agent.observer = observer

        agent._start_idle_listener()
        await _wait_until(lambda: observer.on_complete.called)

        # Injected user notification recorded in history and shown in UI
        user_items = [m for m in agent.messages if m.role == "user"]
        assert any("Monitor fired" in m.content.text for m in user_items)
        observer.on_prompt_sent.assert_called_once()

        # Assistant reply rendered (envelope-text fallback path)
        assistant_items = [m for m in agent.messages if m.role == "assistant"]
        assert assistant_items
        assert "CI is green" in assistant_items[-1].content.blocks[-1].text

        # Turn completion propagated and state reset
        observer.on_complete.assert_called_once()
        await _wait_until(lambda: agent.status == AgentStatus.IDLE)
        assert agent._response_state == ResponseState.IDLE

        await agent._stop_idle_listener()

    async def test_agent_busy_while_cli_turn_streams(
        self, make_agent_with_scripted_stream
    ):
        """Status goes BUSY for the CLI-initiated turn, then back to IDLE."""
        turn = [
            UserMessage(content="notification"),
            _result_message(),
        ]
        agent = make_agent_with_scripted_stream([turn])

        # Intercept status transitions to observe BUSY during the turn
        seen_status: list[AgentStatus] = []
        original = agent._set_status

        def _spy(status):
            seen_status.append(status)
            original(status)

        agent._set_status = _spy  # type: ignore[method-assign]

        agent._start_idle_listener()
        await _wait_until(lambda: AgentStatus.BUSY in seen_status)
        await _wait_until(lambda: agent.status == AgentStatus.IDLE)
        assert agent._response_state == ResponseState.IDLE

        await agent._stop_idle_listener()

    async def test_queued_message_drained_after_cli_turn(
        self, make_agent_with_scripted_stream
    ):
        """Messages queued during a CLI-initiated turn are sent afterwards."""
        turn = [UserMessage(content="notification"), _result_message()]
        agent = make_agent_with_scripted_stream([turn])

        # The CLI only produces the response turn after query() is sent
        # (otherwise the idle listener could consume it prematurely).
        async def _on_query(prompt, session_id="default"):
            agent.client._script.append([_result_message(session_id="sess-2")])

        agent.client.query = AsyncMock(side_effect=_on_query)

        agent._pending_messages.append(("queued prompt", None))

        agent._start_idle_listener()
        await _wait_until(lambda: agent.client.query.await_count == 1)
        agent.client.query.assert_awaited_once_with("queued prompt")
        await _wait_until(lambda: agent._response_state == ResponseState.IDLE)
        assert agent._pending_messages == []

        await agent._stop_idle_listener()
        task = agent._response.task
        if task and not task.done():
            task.cancel()


class TestIdleListenerLifecycle:
    """Listener starts/stops around client-initiated responses."""

    async def test_start_response_stops_listener(self, make_agent_with_scripted_stream):
        agent = make_agent_with_scripted_stream([])  # stream open, no traffic
        agent._start_idle_listener()
        listener = agent._idle_listener_task
        assert listener is not None
        await asyncio.sleep(0)  # let listener enter receive_response

        await agent.send("hello")
        await _wait_until(lambda: listener.done())
        assert agent._idle_listener_task is None
        assert agent.client.query.await_count == 1

        # Cleanup the (blocked) response task
        task = agent._response.task
        assert task is not None
        task.cancel()
        import contextlib

        with contextlib.suppress(asyncio.CancelledError):
            await task

    async def test_listener_noop_when_disabled(self, tmp_path):
        agent = Agent(name="idle-test", cwd=tmp_path)
        agent.client = MagicMock()
        # _idle_listener_enabled defaults to False (set by connect())
        agent._start_idle_listener()
        assert agent._idle_listener_task is None

    async def test_listener_exits_on_closed_stream(
        self, make_agent_with_scripted_stream
    ):
        """An empty receive_response (closed stream) exits without spinning."""
        agent = make_agent_with_scripted_stream([[]])  # one empty iteration
        # Dead transport -> listener should report connection lost and exit
        agent.client._query.transport._process.returncode = 1
        observer = MagicMock()
        agent.observer = observer

        agent._start_idle_listener()
        listener = agent._idle_listener_task
        assert listener is not None
        await _wait_until(lambda: listener.done())
        observer.on_connection_lost.assert_called_once()
