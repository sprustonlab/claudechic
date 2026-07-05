"""Coalesced queue delivery: the whole message backlog drains as ONE turn.

Covers coalesce_messages (single passthrough, multi-message combining,
ordering, display_as handling) and Agent._drain_next_message (drains the
full queue in one _start_response call; re-queues the whole batch in
order on CLIConnectionError).
"""

from __future__ import annotations

from claude_agent_sdk import CLIConnectionError

from claudechic.agent import Agent, coalesce_messages


class TestCoalesceMessages:
    def test_single_message_passes_through_unchanged(self):
        assert coalesce_messages([("hello", None)]) == ("hello", None)
        assert coalesce_messages([("hello", "shown")]) == ("hello", "shown")

    def test_multi_message_combines_oldest_first(self):
        prompt, display = coalesce_messages(
            [("first msg", None), ("second msg", None), ("third msg", None)]
        )
        assert "3 messages were queued" in prompt
        assert "Queued message 1 of 3" in prompt
        assert "Queued message 3 of 3" in prompt
        # Oldest first: first before second before third.
        assert (
            prompt.index("first msg")
            < prompt.index("second msg")
            < prompt.index("third msg")
        )
        assert display is not None

    def test_multi_message_instructs_single_response(self):
        prompt, _ = coalesce_messages([("a", None), ("b", None)])
        assert "respond ONCE" in prompt
        assert "acknowledgement-only" in prompt

    def test_display_uses_display_as_when_present(self):
        _, display = coalesce_messages(
            [("raw prompt 1", "pretty 1"), ("raw prompt 2", None)]
        )
        assert display is not None
        assert "pretty 1" in display
        assert "raw prompt 1" not in display  # display_as replaces the prompt
        assert "raw prompt 2" in display  # falls back to the prompt


class TestDrainCoalesces:
    def _agent(self, tmp_path) -> Agent:
        agent = Agent(name="coalesce-test", cwd=tmp_path)
        agent._is_transport_alive = lambda: True  # type: ignore[method-assign]
        return agent

    def test_drains_whole_queue_in_one_turn(self, tmp_path):
        agent = self._agent(tmp_path)
        agent._pending_messages.extend([("m1", None), ("m2", None), ("m3", None)])

        sent: list[tuple[str, str | None]] = []

        def fake_start(prompt: str, *, display_as: str | None = None) -> None:
            sent.append((prompt, display_as))

        agent._start_response = fake_start  # type: ignore[method-assign]
        agent._drain_next_message()

        assert len(sent) == 1  # ONE turn, not three
        combined = sent[0][0]
        assert "m1" in combined and "m2" in combined and "m3" in combined
        assert agent._pending_messages == []

    def test_single_queued_message_unchanged(self, tmp_path):
        agent = self._agent(tmp_path)
        agent._pending_messages.append(("solo", "solo shown"))

        sent: list[tuple[str, str | None]] = []
        agent._start_response = lambda prompt, *, display_as=None: sent.append(  # type: ignore[method-assign]
            (prompt, display_as)
        )
        agent._drain_next_message()

        assert sent == [("solo", "solo shown")]

    def test_connection_error_requeues_whole_batch_in_order(self, tmp_path):
        agent = self._agent(tmp_path)
        batch = [("m1", None), ("m2", "shown2")]
        agent._pending_messages.extend(batch)

        def boom(prompt: str, *, display_as: str | None = None) -> None:
            raise CLIConnectionError("transport died")

        agent._start_response = boom  # type: ignore[method-assign]
        agent._drain_next_message()

        # Nothing lost, original order preserved.
        assert agent._pending_messages == batch
