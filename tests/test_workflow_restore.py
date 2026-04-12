"""Tests for workflow restore from chicsession.

Targets two bugs:
1. _restore_workflow_from_session() references undefined `wf_data` → NameError
2. _handle_restore() never calls _restore_workflow_from_session() → workflow lost
"""

from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from claudechic.app import ChatApp
from claudechic.chicsessions import Chicsession, ChicsessionEntry, ChicsessionManager

pytestmark = [pytest.mark.asyncio, pytest.mark.timeout(30)]


def _setup_workflow(root: Path) -> None:
    """Create a minimal workflow on disk."""
    (root / "global").mkdir(parents=True, exist_ok=True)
    wf_dir = root / "workflows" / "proj"
    wf_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "workflow_id": "proj",
        "main_role": "learner",
        "phases": [
            {"id": "design", "file": "design.md"},
            {"id": "implement", "file": "implement.md"},
        ],
    }
    (wf_dir / "proj.yaml").write_text(yaml.dump(manifest))


def _save_chicsession(
    root: Path, name: str, workflow_state: dict | None = None
) -> None:
    """Create a chicsession file on disk."""
    mgr = ChicsessionManager(root)
    cs = Chicsession(
        name=name,
        active_agent="main",
        agents=[ChicsessionEntry(name="main", session_id="fake-sid", cwd=str(root))],
        workflow_state=workflow_state,
    )
    mgr.save(cs)


async def _mock_prompt_chicsession_name(self, workflow_id: str) -> str | None:
    self._chicsession_name = workflow_id
    return workflow_id


def _common_patches():
    """Return an ExitStack with the common patches applied."""
    stack = ExitStack()
    stack.enter_context(
        patch("claudechic.tasks.create_safe_task", return_value=MagicMock())
    )
    stack.enter_context(patch("claudechic.sessions.count_sessions", return_value=1))
    stack.enter_context(
        patch.object(ChatApp, "_prompt_chicsession_name", _mock_prompt_chicsession_name)
    )
    return stack


class TestRestoreWorkflowFromSession:
    """Bug #1: _restore_workflow_from_session references undefined wf_data."""

    async def test_restore_rebuilds_engine_from_chicsession(self, mock_sdk, tmp_path):
        """After activate + advance, saving state and calling _restore_workflow_from_session
        must rebuild the engine with correct phase. Fails if wf_data NameError."""
        _setup_workflow(tmp_path)
        app = ChatApp()

        with _common_patches():
            async with app.run_test(size=(120, 40), notifications=True) as pilot:
                await pilot.pause()

                app._cwd = tmp_path
                app._init_workflow_infrastructure()
                app._discover_workflows()
                await app._activate_workflow("proj")
                await pilot.pause()

                engine = app._workflow_engine
                assert engine is not None

                # Advance to implement phase
                await engine.attempt_phase_advance(
                    "proj", "proj:design", "proj:implement", []
                )
                assert engine.get_current_phase() == "proj:implement"

                # Save workflow state to chicsession on disk
                _save_chicsession(
                    tmp_path,
                    app._chicsession_name,
                    workflow_state=engine.to_session_state(),
                )

                # Nuke the engine to simulate fresh resume
                app._workflow_engine = None

                # This is the method under test — must not raise NameError
                app._restore_workflow_from_session()

                # Engine should be restored at implement phase
                assert app._workflow_engine is not None, (
                    "_restore_workflow_from_session did not rebuild the engine"
                )
                assert app._workflow_engine.get_current_phase() == "proj:implement"
                assert app._workflow_engine.workflow_id == "proj"

    async def test_restore_no_op_without_chicsession(self, mock_sdk, tmp_path):
        """No chicsession name → early return, no crash."""
        _setup_workflow(tmp_path)
        app = ChatApp()

        with _common_patches():
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()

                app._cwd = tmp_path
                app._chicsession_name = None
                app._restore_workflow_from_session()
                assert app._workflow_engine is None


class TestHandleRestoreCallsWorkflowRestore:
    """Bug #2: _handle_restore() loads chicsession but never restores workflow."""

    async def test_handle_restore_restores_workflow_engine(self, mock_sdk, tmp_path):
        """After _handle_restore, the workflow engine must be rebuilt
        from the saved workflow_state in the chicsession."""
        _setup_workflow(tmp_path)
        app = ChatApp()

        with _common_patches():
            async with app.run_test(size=(120, 40), notifications=True) as pilot:
                await pilot.pause()

                app._cwd = tmp_path
                app._init_workflow_infrastructure()
                app._discover_workflows()

                # Activate workflow, advance phase, save chicsession
                await app._activate_workflow("proj")
                await pilot.pause()

                engine = app._workflow_engine
                assert engine is not None

                await engine.attempt_phase_advance(
                    "proj", "proj:design", "proj:implement", []
                )

                # Save chicsession with workflow state
                _save_chicsession(
                    tmp_path,
                    app._chicsession_name,
                    workflow_state=engine.to_session_state(),
                )

                session_name = app._chicsession_name

                # Reset app state to simulate fresh start
                app._workflow_engine = None
                app._chicsession_name = None

                # Run _handle_restore
                from claudechic.chicsession_cmd import _handle_restore

                await _handle_restore(app, session_name)
                await pilot.pause()

                # After restore, workflow engine should be rebuilt
                assert app._workflow_engine is not None, (
                    "_handle_restore did not call _restore_workflow_from_session — "
                    "workflow engine is None after restoring a chicsession with workflow_state"
                )
                assert app._workflow_engine.get_current_phase() == "proj:implement"
