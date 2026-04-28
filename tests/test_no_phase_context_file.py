"""Broad-scan: no ``phase_context.md`` is written by any code path.

Group D (SPEC §4.7) replaced the file-on-disk delivery model with
in-memory phase-prompt delivery. Several existing tests assert that
``<tmp_path>/.claude/phase_context.md`` does not appear after specific
operations — but those assertions are scoped to one path. This test
locks the broader contract: no ``phase_context.md`` is written to ANY
path under the test fixture root by any code path.

Exercises the three lifecycle moments where a regression to the old
file-on-disk model would surface:

1. Workflow activation kickoff
2. Phase advance (in-memory delivery via ``_inject_phase_prompt_to_main_agent``)
3. Workflow deactivation

After each moment, the test scans every directory the test fixture
touched (``tmp_path`` recursively) for any file named
``phase_context.md`` and asserts zero matches. A regression that wrote
the file under ``<tmp_path>/.claudechic/``, ``<tmp_path>/<repo>/.claude/``
or anywhere else would be caught here even though existing tests'
single-path assertions would not catch it.

Locks SE8/A15: the file-drop decision is permanent.
"""

from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from claudechic.app import ChatApp

pytestmark = [pytest.mark.asyncio, pytest.mark.timeout(30)]


# Mirrors the workflow fixture used in test_phase_prompt_delivery.py and
# test_artifact_dir_e2e.py — a minimal two-phase coordinator workflow.
def _setup_workflow(root: Path) -> Path:
    (root / "global").mkdir(parents=True, exist_ok=True)
    wf_dir = root / "workflows" / "test_workflow"
    wf_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "workflow_id": "test-workflow",
        "main_role": "coordinator",
        "phases": [
            {"id": "design", "file": "design"},
            {"id": "implement", "file": "implement"},
        ],
    }
    (wf_dir / "test_workflow.yaml").write_text(
        yaml.dump(manifest, default_flow_style=False), encoding="utf-8"
    )

    coord = wf_dir / "coordinator"
    coord.mkdir()
    (coord / "identity.md").write_text("identity content", encoding="utf-8")
    (coord / "design.md").write_text("design phase content", encoding="utf-8")
    (coord / "implement.md").write_text("implement phase content", encoding="utf-8")
    return wf_dir


async def _mock_chicsession_name(self, workflow_id: str) -> str | None:
    self._chicsession_name = workflow_id
    return workflow_id


def _scan_for_phase_context(*roots: Path) -> list[Path]:
    """Return every ``phase_context.md`` under any of the given roots.

    Uses ``rglob`` so it also catches subtree placements (e.g. under
    ``.claudechic/`` or nested workflow dirs). Symlinks are NOT followed
    by default rglob behavior, which is what we want — we only care
    about real writes by the system under test.
    """
    found: list[Path] = []
    for root in roots:
        if root.exists():
            found.extend(root.rglob("phase_context.md"))
    return found


async def test_phase_context_md_never_written_anywhere(
    mock_sdk, tmp_path, monkeypatch
) -> None:
    """SE8/A15: no ``phase_context.md`` is written under tmp_path by any
    code path during activation, advance, or deactivation.

    Existing tests in ``test_phase_prompt_delivery.py`` only check
    ``tmp_path / ".claude" / "phase_context.md"``. This test does a
    broad ``rglob`` so a regression that placed the file under
    ``.claudechic/``, the repo root, or any nested directory is caught.
    """
    monkeypatch.chdir(tmp_path)
    _setup_workflow(tmp_path)

    app = ChatApp()

    with ExitStack() as stack:
        stack.enter_context(patch("claudechic.sessions.count_sessions", return_value=1))
        stack.enter_context(
            patch.object(ChatApp, "_prompt_chicsession_name", _mock_chicsession_name)
        )

        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            app._cwd = tmp_path
            app._init_workflow_infrastructure(
                global_dir=tmp_path / "global",
                workflows_dir=tmp_path / "workflows",
            )
            app._discover_workflows()
            await pilot.pause()

            # Snapshot before any workflow activity (catches anything
            # written by infrastructure init).
            pre_activation = _scan_for_phase_context(tmp_path)
            assert pre_activation == [], (
                f"phase_context.md leaked during init: {pre_activation}"
            )

            # ── Lifecycle moment 1: activation kickoff ─────────────────
            await app._activate_workflow("test-workflow")
            await pilot.pause()
            post_activation = _scan_for_phase_context(tmp_path)
            assert post_activation == [], (
                f"phase_context.md leaked during activation: {post_activation}"
            )

            # ── Lifecycle moment 2: phase advance via in-memory inject ─
            app._inject_phase_prompt_to_main_agent(
                "test-workflow", "coordinator", "implement"
            )
            await pilot.pause()
            post_advance = _scan_for_phase_context(tmp_path)
            assert post_advance == [], (
                f"phase_context.md leaked during advance: {post_advance}"
            )

            # ── Lifecycle moment 3: deactivation ───────────────────────
            # _deactivate_workflow is sync (returns None); not awaitable.
            app._deactivate_workflow()
            await pilot.pause()
            post_deactivation = _scan_for_phase_context(tmp_path)
            assert post_deactivation == [], (
                f"phase_context.md leaked during deactivation: {post_deactivation}"
            )


async def test_phase_context_md_never_written_at_postcompact_hook(
    tmp_path,
) -> None:
    """The PostCompact hook produces an in-memory dict — no file I/O.

    Complements ``test_inv_aw_9_post_compact_no_file_io`` (which patches
    write_bytes/write_text/unlink). This test runs the closure against a
    real workflow fixture and then rgreps the tree for any file named
    ``phase_context.md``.
    """
    from claudechic.workflows.agent_folders import create_post_compact_hook

    wf_dir = _setup_workflow(tmp_path)

    class FakeEngine:
        workflow_id = "test-workflow"

        def get_current_phase(self) -> str:
            return "design"

        def get_artifact_dir(self):
            return None

    hook_dict = create_post_compact_hook(
        engine=FakeEngine(),
        agent_role="coordinator",
        workflow_dir=wf_dir,
    )
    closure = hook_dict["PostCompact"][0].hooks[0]
    result = await closure({}, None, None)
    # Hook returned a dict (in-memory delivery; no file I/O semantically).
    assert isinstance(result, dict)

    leaks = _scan_for_phase_context(tmp_path)
    assert leaks == [], f"phase_context.md leaked during PostCompact hook: {leaks}"
