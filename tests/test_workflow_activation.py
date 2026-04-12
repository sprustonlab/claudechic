"""E2E tests: Slash command activation/deactivation of workflows.

Intent: "When I type /{workflow-id}, does the workflow activate?
When I type /{workflow-id} stop, does it deactivate?"
"""

from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from claudechic.app import ChatApp

pytestmark = [pytest.mark.asyncio, pytest.mark.timeout(30)]


def _setup_workflow(root: Path) -> None:
    """Create a minimal workflow."""
    (root / "global").mkdir(parents=True, exist_ok=True)
    wf_dir = root / "workflows" / "my_proj"
    wf_dir.mkdir(parents=True, exist_ok=True)
    wf_manifest = {
        "workflow_id": "my_proj",
        "phases": [
            {"id": "design"},
            {"id": "implement"},
        ],
    }
    (wf_dir / "my_proj.yaml").write_text(yaml.dump(wf_manifest))


async def _mock_prompt_chicsession_name(self, workflow_id: str) -> str | None:
    """Test stub: skip TUI prompt, return workflow_id as session name."""
    self._chicsession_name = workflow_id
    return workflow_id


class TestWorkflowActivation:
    """Real ChatApp E2E tests for workflow slash commands."""

    async def test_activate_workflow_via_command(self, mock_sdk, tmp_path):
        """/{workflow-id} activates the workflow engine."""
        _setup_workflow(tmp_path)
        app = ChatApp()

        with ExitStack() as stack:
            stack.enter_context(
                patch("claudechic.tasks.create_safe_task", return_value=MagicMock())
            )
            stack.enter_context(
                patch("claudechic.sessions.count_sessions", return_value=1)
            )
            stack.enter_context(
                patch.object(ChatApp, "_prompt_chicsession_name", _mock_prompt_chicsession_name)
            )

            async with app.run_test(size=(120, 40), notifications=True) as pilot:
                await pilot.pause()

                app._cwd = tmp_path
                app._init_workflow_infrastructure()
                app._discover_workflows()
                await pilot.pause()

                # Directly call the handler (submit_command dispatches via run_worker
                # which is async — calling directly is more reliable for testing)
                handled = await app._handle_workflow_command("/my_proj", "")
                await pilot.pause()

                assert handled is True
                assert app._workflow_engine is not None
                assert app._workflow_engine.workflow_id == "my_proj"
                assert app._workflow_engine.get_current_phase() == "my_proj:design"

    async def test_deactivate_workflow_via_stop(self, mock_sdk, tmp_path):
        """/{workflow-id} stop deactivates and clears engine."""
        _setup_workflow(tmp_path)
        app = ChatApp()

        with ExitStack() as stack:
            stack.enter_context(
                patch("claudechic.tasks.create_safe_task", return_value=MagicMock())
            )
            stack.enter_context(
                patch("claudechic.sessions.count_sessions", return_value=1)
            )
            stack.enter_context(
                patch.object(ChatApp, "_prompt_chicsession_name", _mock_prompt_chicsession_name)
            )

            async with app.run_test(size=(120, 40), notifications=True) as pilot:
                await pilot.pause()

                app._cwd = tmp_path
                app._init_workflow_infrastructure()
                app._discover_workflows()
                await pilot.pause()

                # Activate
                await app._handle_workflow_command("/my_proj", "")
                assert app._workflow_engine is not None

                # Deactivate via stop
                handled = await app._handle_workflow_command("/my_proj", "stop")
                await pilot.pause()

                assert handled is True
                assert app._workflow_engine is None

                # Verify deactivation notification
                deactivate_notifs = [
                    n for n in app._notifications
                    if "deactivated" in n.message.lower()
                ]
                assert len(deactivate_notifs) > 0

    async def test_unknown_workflow_shows_error(self, mock_sdk, tmp_path):
        """Activating a non-existent workflow → error notification."""
        (tmp_path / "global").mkdir(parents=True)
        (tmp_path / "workflows").mkdir(parents=True)
        app = ChatApp()

        with ExitStack() as stack:
            stack.enter_context(
                patch("claudechic.tasks.create_safe_task", return_value=MagicMock())
            )
            stack.enter_context(
                patch("claudechic.sessions.count_sessions", return_value=1)
            )

            async with app.run_test(size=(120, 40), notifications=True) as pilot:
                await pilot.pause()

                app._cwd = tmp_path
                app._init_workflow_infrastructure()
                app._discover_workflows()
                await pilot.pause()

                # Try to activate non-existent workflow directly
                await app._activate_workflow("nonexistent")
                await pilot.pause()

                error_notifs = [
                    n for n in app._notifications
                    if "unknown" in n.message.lower() or n.severity == "error"
                ]
                assert len(error_notifs) > 0, (
                    f"Expected error notification, got: {[n.message for n in app._notifications]}"
                )

    async def test_double_activation_warns(self, mock_sdk, tmp_path):
        """Activating a second workflow while one is active → warning."""
        _setup_workflow(tmp_path)
        app = ChatApp()

        with ExitStack() as stack:
            stack.enter_context(
                patch("claudechic.tasks.create_safe_task", return_value=MagicMock())
            )
            stack.enter_context(
                patch("claudechic.sessions.count_sessions", return_value=1)
            )
            stack.enter_context(
                patch.object(ChatApp, "_prompt_chicsession_name", _mock_prompt_chicsession_name)
            )

            async with app.run_test(size=(120, 40), notifications=True) as pilot:
                await pilot.pause()

                app._cwd = tmp_path
                app._init_workflow_infrastructure()
                app._discover_workflows()
                await pilot.pause()

                # Activate first time
                await app._activate_workflow("my_proj")
                assert app._workflow_engine is not None

                # Try to activate again
                await app._activate_workflow("my_proj")
                await pilot.pause()

                # Should warn about deactivating first
                warn_notifs = [
                    n for n in app._notifications
                    if "deactivate" in n.message.lower()
                ]
                assert len(warn_notifs) > 0
