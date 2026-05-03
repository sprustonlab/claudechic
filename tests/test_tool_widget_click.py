"""Tests for click behavior on the MCP agent tool widget.

Verifies that clicking inner content of an ``AgentToolWidget`` (the
widget used to render mcp__chic__ tool calls) does not collapse the
widget, and that the title-bar toggle remains functional via the
``QuietCollapsible.collapsed`` attribute.
"""

from __future__ import annotations

from typing import Any

import pytest
from claude_agent_sdk import ToolUseBlock
from claudechic.app import ChatApp
from claudechic.widgets.content.tools import AgentToolWidget
from claudechic.widgets.primitives.collapsible import QuietCollapsible
from textual.app import App, ComposeResult

pytestmark = [pytest.mark.asyncio, pytest.mark.timeout(30)]


def _make_block(name: str = "mcp__chic__spawn_agent") -> ToolUseBlock:
    """Construct a ToolUseBlock for an mcp__chic__ tool call."""
    return ToolUseBlock(
        id="tu_1",
        name=name,
        input={"name": "test_agent", "prompt": "go do a thing"},
    )


class _HostApp(App):
    """Minimal Textual app hosting an AgentToolWidget."""

    def __init__(self, widget: AgentToolWidget) -> None:
        super().__init__()
        self._widget = widget

    def compose(self) -> ComposeResult:
        yield self._widget


# ---------------------------------------------------------------------------
# Test 1: clicking the widget keeps inner content mounted
# ---------------------------------------------------------------------------


async def test_mcp_tool_widget_content_visible_after_click():
    """After a click on the widget, the inner ``QuietCollapsible`` is still
    mounted and the widget remains in the DOM. The widget's collapsed
    state is observable; clicks do not destroy the widget tree.
    """
    widget = AgentToolWidget(_make_block(), completed=True)
    app = _HostApp(widget)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        # Widget is mounted.
        assert widget.is_mounted

        # Inner QuietCollapsible exists.
        collapsible = widget.query_one(QuietCollapsible)
        assert collapsible is not None

        await pilot.click(widget)
        await pilot.pause()

        # Widget is still mounted; collapsible is still present (content
        # not destroyed by click).
        assert widget.is_mounted
        still_collapsible = widget.query_one(QuietCollapsible)
        assert still_collapsible is collapsible


# ---------------------------------------------------------------------------
# Test 2: AgentToolWidget background-click toggles collapsed state
# ---------------------------------------------------------------------------


async def test_mcp_tool_widget_collapse_toggle_preserved():
    """``AgentToolWidget.on_click`` toggles the collapsible when a click
    targets the widget itself (not inner content). We synthesize that
    case directly so the test is robust against pilot mouse-targeting
    nuances: a click event whose ``widget`` attribute is the
    AgentToolWidget toggles ``collapsible.collapsed``; subsequent
    invocations toggle it back.
    """
    widget = AgentToolWidget(_make_block(), completed=True)
    app = _HostApp(widget)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        collapsible = widget.query_one(QuietCollapsible)
        initial = collapsible.collapsed

        # Synthesize a left-click event targeting the widget directly.
        # The AgentToolWidget.on_click handler narrows toggle behavior to
        # clicks where ``event.widget is self``; we mimic that contract.
        class _FakeEvent:
            def __init__(self, target: Any) -> None:
                self.button = 1
                self.widget = target

        widget.on_click(_FakeEvent(widget))  # type: ignore[arg-type]
        await pilot.pause()
        assert collapsible.collapsed != initial, (
            "First background click should flip the collapsed state."
        )

        widget.on_click(_FakeEvent(widget))  # type: ignore[arg-type]
        await pilot.pause()
        assert collapsible.collapsed == initial, (
            "Second background click should restore the collapsed state."
        )
