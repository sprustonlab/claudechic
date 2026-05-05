"""Regression test: SDK delivers UserMessage with list[TextBlock] content.

claude-agent-sdk 0.1.68 types ``UserMessage.content`` as
``str | list[ContentBlock]``. Recent SDK versions favour the list shape,
so the SDK-side echo of ``/context`` arrives as
``[TextBlock(text="<command-name>/context</...><local-command-stdout>"
"...## Context Usage...</...>")]`` rather than a plain string.

Before this fix, ``Agent._handle_sdk_message`` only scanned the ``str``
content branch for the ``<local-command-stdout>`` envelope; the list
branch only routed ``ToolResultBlock`` entries. Result: ``/context``
showed nothing in the TUI even though the markdown still leaked into
the model's conversation transcript via the SDK.

These tests assert that BOTH content shapes are scanned for the same
two markers (``<local-command-stdout>...</local-command-stdout>`` and
``<command-name>/...</command-name>``) so the SDK's payload-shape
choice is invisible to the TUI.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from claude_agent_sdk import TextBlock, UserMessage

from claudechic.agent import Agent


class _StubObserver:
    """Minimal observer that records the calls we care about."""

    def __init__(self) -> None:
        self.command_outputs: list[tuple[Agent, str]] = []
        self.skill_loads: list[tuple[Agent, str]] = []

    def on_command_output(self, agent: Agent, content: str) -> None:
        self.command_outputs.append((agent, content))

    def on_skill_loaded(self, agent: Agent, slash_command: str) -> None:
        self.skill_loads.append((agent, slash_command))


def _make_agent(tmp_path: Path) -> tuple[Agent, _StubObserver]:
    agent = Agent(name="t", cwd=tmp_path)
    observer = _StubObserver()
    # The Agent code path under test only reads ``self.observer``; bypass
    # the full Observer protocol typing for this focused unit test.
    agent.observer = observer  # type: ignore[assignment]
    return agent, observer


CONTEXT_PAYLOAD = (
    "<command-name>/context</command-name>\n"
    "<command-message>context</command-message>\n"
    "<command-args></command-args>\n"
    "<local-command-stdout>## Context Usage\n\n"
    "**Model:** claude-opus-4-7\n"
    "**Tokens:** 233.4k / 1m (23%)\n"
    "</local-command-stdout>"
)


@pytest.mark.asyncio
async def test_user_message_str_content_routes_to_command_output(tmp_path: Path):
    """Legacy str-shape: full envelope as a single string."""
    agent, observer = _make_agent(tmp_path)
    msg = UserMessage(content=CONTEXT_PAYLOAD)

    await agent._handle_sdk_message(msg, had_tool_use={})

    assert len(observer.command_outputs) == 1, (
        "Expected on_command_output to fire exactly once for str content; "
        f"got {len(observer.command_outputs)}"
    )
    _, extracted = observer.command_outputs[0]
    assert extracted.startswith("## Context Usage")
    assert "</local-command-stdout>" not in extracted
    # The same payload also carries the <command-name> marker.
    assert observer.skill_loads == [(agent, "/context")]


@pytest.mark.asyncio
async def test_user_message_list_textblock_routes_to_command_output(tmp_path: Path):
    """SDK 0.1.68 list-shape: TextBlock(text=<full-envelope>) -- regression
    for ``/context`` silently dropping in the TUI."""
    agent, observer = _make_agent(tmp_path)
    msg = UserMessage(content=[TextBlock(text=CONTEXT_PAYLOAD)])

    await agent._handle_sdk_message(msg, had_tool_use={})

    assert len(observer.command_outputs) == 1, (
        "Expected on_command_output to fire exactly once for list[TextBlock] "
        f"content; got {len(observer.command_outputs)}. This is the bug -- "
        "the list branch was not scanning TextBlock.text for "
        "<local-command-stdout>."
    )
    _, extracted = observer.command_outputs[0]
    assert extracted.startswith("## Context Usage")
    assert "</local-command-stdout>" not in extracted
    assert observer.skill_loads == [(agent, "/context")]


@pytest.mark.asyncio
async def test_user_message_list_unrelated_textblocks_no_emit(tmp_path: Path):
    """A TextBlock without our markers must not trigger either observer call."""
    agent, observer = _make_agent(tmp_path)
    msg = UserMessage(content=[TextBlock(text="just a normal user reply")])

    await agent._handle_sdk_message(msg, had_tool_use={})

    assert observer.command_outputs == []
    assert observer.skill_loads == []
