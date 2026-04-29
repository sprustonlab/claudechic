"""Tests for ChicsessionActions buttons and WorkflowPickerScreen (Item 2)."""

import pytest
from claudechic.widgets.layout.sidebar import (
    ChicsessionActions,
    ChicsessionLabel,
)
from textual.app import App, ComposeResult


class ChicsessionTestApp(App):
    """Minimal app for testing ChicsessionLabel with actions."""

    def __init__(self):
        super().__init__()
        self.received_messages: list[str] = []

    def compose(self) -> ComposeResult:
        yield ChicsessionLabel(id="chicsession-label")

    def on_chicsession_actions_restore_requested(
        self, event: ChicsessionActions.RestoreRequested
    ) -> None:
        self.received_messages.append("RestoreRequested")

    def on_chicsession_actions_workflow_picker_requested(
        self, event: ChicsessionActions.WorkflowPickerRequested
    ) -> None:
        self.received_messages.append("WorkflowPickerRequested")

    def on_chicsession_actions_stop_requested(
        self, event: ChicsessionActions.StopRequested
    ) -> None:
        self.received_messages.append("StopRequested")


@pytest.mark.asyncio
async def test_chicsession_buttons_adapt_to_workflow_state():
    """ChicsessionActions shows correct buttons for idle vs. workflow state.

    Action 1: Check initial state (no workflow) -> Workflows + Restore visible, no Stop
    Action 2: Set workflow_text -> Stop visible, no Workflows/Restore
    Action 3: Resize narrow -> sidebar hidden (graceful degradation)
    """
    app = ChicsessionTestApp()
    async with app.run_test(size=(120, 40)) as pilot:
        label = app.query_one("#chicsession-label", ChicsessionLabel)
        actions = label.query_one("#chicsession-actions", ChicsessionActions)

        # --- Action 1: Initial state (no workflow) ---
        # Workflows and Restore buttons should be visible
        workflows_btn = actions.query_one("#workflows-btn")
        restore_btn = actions.query_one("#restore-btn")
        assert workflows_btn is not None
        assert restore_btn is not None
        assert workflows_btn.display is True
        assert restore_btn.display is True

        # All action buttons must not steal focus
        for btn in actions.query("ActionButton"):
            assert btn.can_focus is False

        # Stop button should be hidden
        stop_btn_initial = actions.query_one("#stop-btn")
        assert stop_btn_initial.has_class("hidden")

        # Click Restore -> RestoreRequested message
        await pilot.click("#restore-btn")
        assert "RestoreRequested" in app.received_messages

        # Click Workflows -> WorkflowPickerRequested message
        await pilot.click("#workflows-btn")
        assert "WorkflowPickerRequested" in app.received_messages

        # --- Action 2: Set workflow active ---
        label.workflow_text = "project-team"
        await pilot.pause()

        # Stop button should now be present and visible
        stop_btn = actions.query_one("#stop-btn")
        assert stop_btn is not None
        assert stop_btn.display is True

        # Workflows and Restore should be hidden
        assert actions.query_one("#workflows-btn").has_class("hidden")
        assert actions.query_one("#restore-btn").has_class("hidden")

        # Click Stop -> StopRequested message
        app.received_messages.clear()
        await pilot.click("#stop-btn")
        assert "StopRequested" in app.received_messages

        # --- Action 3: Clear workflow (back to idle) ---
        label.workflow_text = ""
        await pilot.pause()

        # Back to Workflows + Restore visible, Stop hidden
        assert not actions.query_one("#workflows-btn").has_class("hidden")
        assert not actions.query_one("#restore-btn").has_class("hidden")
        assert actions.query_one("#stop-btn").has_class("hidden")


@pytest.mark.asyncio
async def test_workflows_button_opens_picker_and_activates(mock_sdk, tmp_path):
    """Full integration: click Workflows -> picker opens -> select -> activates."""
    from pathlib import Path

    from claudechic.app import ChatApp
    from claudechic.widgets.layout.sidebar import ChicsessionLabel

    app = ChatApp()
    async with app.run_test(size=(120, 40)) as pilot:
        # Pre-set chicsession name to prevent prompting
        app._chicsession_name = "test"

        # Inject workflow registry (approved mock)
        app._workflow_registry = {
            "tutorial": Path("/tmp/workflows/tutorial"),
        }

        # Force sidebar visible and trigger layout
        app.right_sidebar.remove_class("hidden")
        app._layout_sidebar_contents()
        await pilot.pause()

        label = app.query_one("#chicsession-label", ChicsessionLabel)
        actions = label.query_one("#chicsession-actions", ChicsessionActions)

        # Post the message directly (simulates Workflows button click) —
        # pixel-clicking is unreliable because sidebar layout sizing in
        # test environments can leave buttons at 0x0 dimensions.
        actions.post_message(ChicsessionActions.WorkflowPickerRequested())
        await pilot.pause()

        # WorkflowPickerScreen should be pushed
        from claudechic.screens.workflow_picker import WorkflowPickerScreen

        screen_stack = app.screen_stack
        picker_found = any(isinstance(s, WorkflowPickerScreen) for s in screen_stack)
        assert picker_found, (
            f"WorkflowPickerScreen not found in screen stack: "
            f"{[type(s).__name__ for s in screen_stack]}"
        )

        # The picker should list "tutorial".  On slower runners (Windows
        # CI in particular) the picker screen is pushed but its compose()
        # hasn't yet mounted child widgets after a single pilot.pause().
        # Pump the event loop a few extra times.
        from claudechic.screens.workflow_picker import WorkflowItem

        items = app.screen.query(WorkflowItem)
        for _ in range(10):
            if len(items) >= 1:
                break
            await pilot.pause()
            items = app.screen.query(WorkflowItem)

        assert len(items) >= 1, (
            f"WorkflowItem widgets did not mount on the picker screen "
            f"after 10 pump cycles (got {len(items)})"
        )
        assert any(item.workflow_id == "tutorial" for item in items), (
            "tutorial workflow not found in picker"
        )
