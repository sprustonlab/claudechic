"""Test that message_agent properly injects sender identity."""

import asyncio

import pytest
from claudechic.mcp import _make_broadcast_message, _make_message_agent, set_app


class MockAgent:
    def __init__(self, name: str):
        self.name = name
        self.id = name
        self.session_id = f"session-{name}"
        self.cwd = "/tmp"
        self.status = "idle"
        self.worktree = None
        self.client = True  # truthy
        self.received_prompt = None
        # Reply-tracking state used by mcp._clear_pending_reply_if_matched.
        # broadcast_message touches these on requires_answer=False; mocking
        # them here keeps the test honest without pulling in the real Agent.
        self._pending_reply_to: str | None = None
        self._reply_nudge_count = 0
        self._nudge_generation = 0

    @property
    def analytics_id(self) -> str:
        return self.session_id or self.id

    async def send(self, prompt: str) -> None:
        self.received_prompt = prompt


class MockAgentManager:
    def __init__(self):
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
    def __init__(self):
        self.agent_mgr = MockAgentManager()

    def run_worker(self, coro):
        """Mock run_worker - close the coroutine to avoid RuntimeWarning."""
        coro.close()


@pytest.fixture
def mock_app():
    app = MockApp()
    set_app(app)  # type: ignore
    return app


@pytest.mark.asyncio
async def test_message_agent_injects_sender(mock_app):
    """When agent 'alice' asks agent 'bob' a question, bob should see it's from alice."""
    alice = MockAgent("alice")
    bob = MockAgent("bob")
    mock_app.agent_mgr.add(alice)
    mock_app.agent_mgr.add(bob)

    # Create message_agent tool bound to alice
    message_agent = _make_message_agent(caller_name="alice")

    # Call the handler directly
    await message_agent.handler({"name": "bob", "message": "What's the weather?"})

    # Let the event loop run the fire-and-forget task
    await asyncio.sleep(0)

    # Bob should have received the prompt with alice's identity and reply instruction
    assert bob.received_prompt is not None
    assert "[Question from agent 'alice'" in bob.received_prompt
    assert (
        "respond using message_agent with requires_answer=false" in bob.received_prompt
    )
    assert "What's the weather?" in bob.received_prompt


@pytest.mark.asyncio
async def test_message_agent_without_sender(mock_app):
    """When no sender is specified (legacy), prompt should pass through unchanged."""
    bob = MockAgent("bob")
    mock_app.agent_mgr.add(bob)

    # Create message_agent tool without caller name
    message_agent = _make_message_agent()

    await message_agent.handler({"name": "bob", "message": "What's the weather?"})

    # Let the event loop run the fire-and-forget task
    await asyncio.sleep(0)

    # Without sender, prompt should be unchanged
    assert bob.received_prompt == "What's the weather?"


@pytest.mark.asyncio
async def test_message_agent_nonexistent_returns_error(mock_app):
    """Asking a non-existent agent should return an error with isError=True."""
    alice = MockAgent("alice")
    mock_app.agent_mgr.add(alice)

    message_agent = _make_message_agent(caller_name="alice")

    # Ask a non-existent agent
    result = await message_agent.handler({"name": "ghost", "message": "Hello?"})

    # Should return error response with isError flag
    assert result["isError"] is True
    assert "ghost" in result["content"][0]["text"]
    assert "not found" in result["content"][0]["text"]


# ---------------------------------------------------------------------------
# broadcast_message: send same message to a list of agents at once
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_broadcast_message_delivers_to_all_targets(mock_app):
    """Each target in the list receives the same wrapped prompt."""
    alice = MockAgent("alice")
    bob = MockAgent("bob")
    carol = MockAgent("carol")
    mock_app.agent_mgr.add(alice)
    mock_app.agent_mgr.add(bob)
    mock_app.agent_mgr.add(carol)

    broadcast = _make_broadcast_message(caller_name="alice")

    result = await broadcast.handler(
        {"names": ["bob", "carol"], "message": "Standup at 10?"}
    )
    await asyncio.sleep(0)  # drain fire-and-forget tasks

    assert result.get("isError") is not True
    text = result["content"][0]["text"]
    assert "2/2 delivered" in text
    assert "bob: sent" in text
    assert "carol: sent" in text

    # Both targets see the same sender-injected prompt body.
    for target in (bob, carol):
        assert target.received_prompt is not None
        assert "[Question from agent 'alice'" in target.received_prompt
        assert "Standup at 10?" in target.received_prompt


@pytest.mark.asyncio
async def test_broadcast_message_partial_failure_reports_per_target(mock_app):
    """Missing targets are reported in the result; valid ones still get sent.

    The broadcast is NOT aborted by a single missing name -- partial
    delivery is the explicit contract so a typo in one of N names doesn't
    silently drop the other N-1.
    """
    alice = MockAgent("alice")
    bob = MockAgent("bob")
    mock_app.agent_mgr.add(alice)
    mock_app.agent_mgr.add(bob)

    broadcast = _make_broadcast_message(caller_name="alice")

    result = await broadcast.handler({"names": ["bob", "ghost"], "message": "ping"})
    await asyncio.sleep(0)

    assert result.get("isError") is not True  # at least one delivered
    text = result["content"][0]["text"]
    assert "1/2 delivered" in text
    assert "bob: sent" in text
    assert "ghost:" in text and "not found" in text
    assert bob.received_prompt is not None  # bob got it


@pytest.mark.asyncio
async def test_broadcast_message_all_missing_is_error(mock_app):
    """If every target is missing, the broadcast is reported as an error."""
    alice = MockAgent("alice")
    mock_app.agent_mgr.add(alice)

    broadcast = _make_broadcast_message(caller_name="alice")

    result = await broadcast.handler(
        {"names": ["ghost1", "ghost2"], "message": "anyone?"}
    )

    assert result["isError"] is True
    text = result["content"][0]["text"]
    assert "0/2 delivered" in text


@pytest.mark.asyncio
async def test_broadcast_message_skips_self_and_dedupes(mock_app):
    """Caller's own name is skipped; duplicates collapse to a single delivery.

    Skipping self pins the documented "broadcasting to yourself is a
    noop" contract. Dedupe pins the "caller intent: send once per
    distinct name" contract.
    """
    alice = MockAgent("alice")
    bob = MockAgent("bob")
    mock_app.agent_mgr.add(alice)
    mock_app.agent_mgr.add(bob)

    broadcast = _make_broadcast_message(caller_name="alice")

    # alice broadcasts to herself + bob (twice). Expected: only bob receives,
    # exactly once. Self is reported as "skipped (self)".
    result = await broadcast.handler(
        {"names": ["alice", "bob", "bob"], "message": "ping"}
    )
    await asyncio.sleep(0)

    text = result["content"][0]["text"]
    assert "1/2 delivered" in text  # post-dedupe: 2 unique (alice, bob); 1 sent
    assert "alice: skipped (self)" in text
    assert "bob: sent" in text
    # Bob's prompt should appear only once -- not concatenated from a duplicate.
    assert bob.received_prompt is not None
    assert bob.received_prompt.count("ping") == 1


@pytest.mark.asyncio
async def test_broadcast_message_fire_and_forget_uses_tell_framing(mock_app):
    """``requires_answer=false`` propagates the no-reply framing to each target."""
    alice = MockAgent("alice")
    bob = MockAgent("bob")
    carol = MockAgent("carol")
    mock_app.agent_mgr.add(alice)
    mock_app.agent_mgr.add(bob)
    mock_app.agent_mgr.add(carol)

    broadcast = _make_broadcast_message(caller_name="alice")

    await broadcast.handler(
        {
            "names": ["bob", "carol"],
            "message": "FYI: rebased main",
            "requires_answer": False,
        }
    )
    await asyncio.sleep(0)

    for target in (bob, carol):
        assert target.received_prompt is not None
        # Fire-and-forget framing: "Message from" prefix, no reply instruction.
        assert "[Message from agent 'alice'" in target.received_prompt
        assert "respond using message_agent" not in target.received_prompt
