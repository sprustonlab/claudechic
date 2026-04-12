"""E2E tests: Phase lifecycle through real ChatApp.

Intent: "When I activate a workflow and advance through phases, does the
system track state correctly?"
"""

from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from claudechic.app import ChatApp

pytestmark = [pytest.mark.asyncio, pytest.mark.timeout(30)]


def _setup_workflow_with_phases(root: Path, add_check_file: bool = False) -> None:
    """Create a workflow with phases and an advance check."""
    (root / "global").mkdir(parents=True, exist_ok=True)
    wf_dir = root / "workflows" / "proj"
    wf_dir.mkdir(parents=True, exist_ok=True)

    readme_path = str(root / "README.md")
    wf_manifest = {
        "workflow_id": "proj",
        "phases": [
            {
                "id": "design",
                "file": "design.md",
                "advance_checks": [
                    {
                        "type": "file-exists-check",
                        "path": readme_path,
                        "on_failure": {
                            "message": "Create README.md first",
                            "severity": "warning",
                        },
                    }
                ],
            },
            {"id": "implement", "file": "implement.md"},
            {"id": "deploy", "file": "deploy.md"},
        ],
    }
    (wf_dir / "proj.yaml").write_text(yaml.dump(wf_manifest))

    if add_check_file:
        (root / "README.md").write_text("# Project\n")


async def _mock_prompt_chicsession_name(self, workflow_id: str) -> str | None:
    """Test stub: skip TUI prompt, return workflow_id as session name."""
    self._chicsession_name = workflow_id
    return workflow_id


class TestWorkflowPhases:
    """Real ChatApp E2E tests for phase lifecycle."""

    async def test_workflow_activation_creates_engine(self, mock_sdk, tmp_path):
        """Boot app, activate workflow → engine exists with correct first phase."""
        _setup_workflow_with_phases(tmp_path)
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

                # Activate workflow
                await app._activate_workflow("proj")
                await pilot.pause()

                # Engine should exist
                assert app._workflow_engine is not None
                assert app._workflow_engine.workflow_id == "proj"
                assert app._workflow_engine.get_current_phase() == "proj:design"

                # Activation notification should appear
                activation_notifs = [
                    n for n in app._notifications
                    if "activated" in n.message.lower()
                ]
                assert len(activation_notifs) > 0, (
                    f"Expected activation toast, got: {[n.message for n in app._notifications]}"
                )

    async def test_phase_advance_with_passing_check(self, mock_sdk, tmp_path):
        """Advance check passes → phase transitions to next."""
        _setup_workflow_with_phases(tmp_path, add_check_file=True)
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
                await app._activate_workflow("proj")
                await pilot.pause()

                # Get advance checks for design phase
                engine = app._workflow_engine
                assert engine is not None
                checks = engine.get_advance_checks_for("proj:design")
                next_phase = engine.get_next_phase("proj:design")
                assert next_phase == "proj:implement"

                # Attempt advance — README.md exists, so check passes
                result = await engine.attempt_phase_advance(
                    "proj", "proj:design", next_phase, checks
                )
                assert result.success is True
                assert engine.get_current_phase() == "proj:implement"

    async def test_phase_advance_with_failing_check(self, mock_sdk, tmp_path):
        """Advance check fails → phase does NOT transition."""
        _setup_workflow_with_phases(tmp_path, add_check_file=False)
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
                await app._activate_workflow("proj")
                await pilot.pause()

                engine = app._workflow_engine
                assert engine is not None
                checks = engine.get_advance_checks_for("proj:design")
                next_phase = engine.get_next_phase("proj:design")

                # Attempt advance — README.md does NOT exist, check fails
                result = await engine.attempt_phase_advance(
                    "proj", "proj:design", next_phase, checks
                )
                assert result.success is False
                assert engine.get_current_phase() == "proj:design"  # Still on design
                assert result.failed_check_id is not None
                assert result.hint_data is not None
                assert "README" in result.hint_data["message"]

    async def test_engine_session_state_roundtrip(self, mock_sdk, tmp_path):
        """Engine state serializes and restores correctly."""
        _setup_workflow_with_phases(tmp_path, add_check_file=True)
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
                await app._activate_workflow("proj")
                await pilot.pause()

                engine = app._workflow_engine
                assert engine is not None

                # Advance phase
                checks = engine.get_advance_checks_for("proj:design")
                await engine.attempt_phase_advance(
                    "proj", "proj:design", "proj:implement", checks
                )
                assert engine.get_current_phase() == "proj:implement"

                # Serialize
                state = engine.to_session_state()
                assert state["workflow_id"] == "proj"
                assert state["current_phase"] == "proj:implement"

                # Restore from state into a new engine
                from claudechic.workflows.engine import WorkflowEngine

                restored = WorkflowEngine.from_session_state(
                    state=state,
                    manifest=engine.manifest,
                    persist_fn=engine._persist_fn,
                    confirm_callback=engine._confirm_callback,
                )
                assert restored.get_current_phase() == "proj:implement"
