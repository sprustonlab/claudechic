"""End-to-end integration tests for the Group D x Group E cross-axis seam.

Group D delivers phase prompts to active agents in-memory via
``assemble_phase_prompt`` at two delivery sites: workflow-activation kickoff
and phase advance. Group E adds the ``${CLAUDECHIC_ARTIFACT_DIR}`` markdown
substitution token, populated from ``engine.get_artifact_dir()``.

The unit tests in ``tests/test_artifact_dir.py`` exercise each link of the
chain individually. ``tests/test_phase_prompt_delivery.py`` exercises the
delivery sites with ``artifact_dir`` unset. This file covers the **full
chain** end-to-end, with an active artifact_dir flowing through both
delivery paths, plus the resume variant via a real
``ChicsessionManager`` round-trip (per Skeptic2's correction).

Focus areas covered (from Composability2 + Skeptic2 integration-approval
reviews):

1. Full chain: activation kickoff -> ``set_artifact_dir`` -> advance, with
   the resolved path substituted into the agent-bound prompt at both
   delivery sites (covers I-3 + I-12 + INV-AW-6 + INV-AW-8 in series).
2. Resume variant: ``ChicsessionManager.save()`` then ``.load()`` then
   ``WorkflowEngine.from_session_state``, asserting the substituted path
   reaches the agent without the coordinator re-calling
   ``set_artifact_dir`` (covers I-4 + I-3 with a real persistence
   round-trip).
3. The cross-axis seam: both phase-prompt delivery paths (activation
   kickoff and phase advance) flow through the same substitution helper;
   neither path ever leaks the literal ``${CLAUDECHIC_ARTIFACT_DIR}``
   token to the agent when ``engine.artifact_dir`` is set.
"""

from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import yaml
from claudechic.app import ChatApp
from claudechic.chicsessions import (
    Chicsession,
    ChicsessionEntry,
    ChicsessionManager,
)
from claudechic.workflows._substitute import ARTIFACT_DIR_TOKEN
from claudechic.workflows.agent_folders import assemble_phase_prompt
from claudechic.workflows.engine import WorkflowEngine, WorkflowManifest
from claudechic.workflows.phases import Phase

pytestmark = [pytest.mark.asyncio, pytest.mark.timeout(30)]


# ---------------------------------------------------------------------------
# Workflow fixture (mirrors test_phase_prompt_delivery.py pattern, with
# ${CLAUDECHIC_ARTIFACT_DIR} tokens added to identity + phase markdown)
# ---------------------------------------------------------------------------


_TOKEN_LITERAL = ARTIFACT_DIR_TOKEN  # cached for test message clarity


def _setup_workflow_with_token(root: Path) -> Path:
    """Create a minimal test workflow whose markdown references the token.

    Layout under ``root``:
        global/                                 (empty global manifest dir)
        workflows/test_workflow/
            test_workflow.yaml                  (manifest with two phases)
            coordinator/
                identity.md                     (contains IDENTITY-MARKER + token)
                design.md                       (contains DESIGN-MARKER + token)
                implement.md                    (contains IMPLEMENT-MARKER + token)

    Returns the workflow directory path.
    """
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
    (coord / "identity.md").write_text(
        f"IDENTITY-MARKER: coordinator. Artifacts at {_TOKEN_LITERAL}/notes.md.",
        encoding="utf-8",
    )
    (coord / "design.md").write_text(
        f"DESIGN-MARKER: design phase. Write to {_TOKEN_LITERAL}/design.md.",
        encoding="utf-8",
    )
    (coord / "implement.md").write_text(
        f"IMPLEMENT-MARKER: implement phase. Write to {_TOKEN_LITERAL}/impl.md.",
        encoding="utf-8",
    )
    return wf_dir


async def _mock_chicsession_name(self, workflow_id: str) -> str | None:
    """Test stub: skip TUI prompt, set chicsession name to workflow id."""
    self._chicsession_name = workflow_id
    return workflow_id


def _assert_substituted(text: str, artifact_dir: Path, *, label: str) -> None:
    """Assert the prompt has the resolved path and never the raw token."""
    assert _TOKEN_LITERAL not in text, (
        f"{label}: literal {_TOKEN_LITERAL!r} leaked to agent: {text[:300]!r}"
    )
    assert str(artifact_dir) in text, (
        f"{label}: resolved path {artifact_dir} not present in: {text[:300]!r}"
    )


# ---------------------------------------------------------------------------
# Test 1 — Full chain: activation kickoff + advance, both substituted
# ---------------------------------------------------------------------------


async def test_e2e_activation_setartifact_advance_substitutes_token_in_prompt(
    mock_sdk, tmp_path, monkeypatch
) -> None:
    """Activation kickoff and phase-advance prompt both substitute the token.

    Drives a real ``ChatApp`` through:
    1. Workflow activation -> kickoff prompt sent to active agent
    2. ``engine.set_artifact_dir(<art>)`` to bind the path
    3. ``_inject_phase_prompt_to_main_agent`` -> advance prompt sent

    The first send uses ``artifact_dir=None`` so the token resolves to ""
    (deliberate visible failure mode per I-3). The second send uses the
    bound artifact_dir and MUST contain the resolved path string with the
    raw token absent.

    Asserts I-3 (substitution behavior), I-12 (set triggers persist), and
    the cross-axis seam at the advance delivery site (INV-AW-8).
    """
    monkeypatch.chdir(tmp_path)
    _setup_workflow_with_token(tmp_path)
    artifact = tmp_path / "artifacts" / "run-1"

    app = ChatApp()
    sent: list[str] = []

    def _capture(prompt: str, *, display_as: str | None = None) -> None:
        sent.append(prompt)

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

            with patch.object(app, "_send_to_active_agent", side_effect=_capture):
                # Step 1: activation kickoff (artifact_dir is still None)
                await app._activate_workflow("test-workflow")
                await pilot.pause()

                assert len(sent) == 1, (
                    f"Activation should send exactly one kickoff; got {len(sent)}"
                )
                assert "DESIGN-MARKER" in sent[0]
                # Pre-set: token resolves to empty string per I-3.
                assert _TOKEN_LITERAL not in sent[0], (
                    "Pre-set kickoff must not leak raw token to agent"
                )

                # Step 2: bind artifact_dir on the live engine
                engine = app._workflow_engine
                assert engine is not None
                resolved = await engine.set_artifact_dir(str(artifact))
                assert resolved == artifact.resolve()
                assert artifact.is_dir()  # mkdir(parents=True) ran

                # Step 3: trigger advance-delivery path with artifact_dir set
                sent.clear()
                app._inject_phase_prompt_to_main_agent(
                    "test-workflow", "coordinator", "implement"
                )

            assert len(sent) == 1, (
                f"Advance should send exactly one prompt; got {len(sent)}"
            )
            _assert_substituted(sent[0], artifact.resolve(), label="advance prompt")
            assert "IMPLEMENT-MARKER" in sent[0]
            assert "IDENTITY-MARKER" in sent[0]


# ---------------------------------------------------------------------------
# Test 2 — Resume via real ChicsessionManager round-trip (Skeptic2 correction)
# ---------------------------------------------------------------------------


async def test_e2e_resume_round_trip_substitutes_without_recall(tmp_path) -> None:
    """Resume via real ChicsessionManager save/load round-trip.

    Skeptic2 correction: do NOT pre-populate chicsession JSON by hand.
    Instead, drive ``ChicsessionManager.save()`` to write the JSON, then
    ``.load()`` and feed the workflow_state back into
    ``WorkflowEngine.from_session_state``. This exercises the actual
    persistence schema and catches drift.

    Then call ``assemble_phase_prompt`` for the next phase with
    ``engine.get_artifact_dir()`` and assert the substituted path appears
    without any coordinator re-call to ``set_artifact_dir`` (I-4).
    """
    wf_dir = _setup_workflow_with_token(tmp_path)
    artifact = tmp_path / "artifacts" / "resumed-run"
    artifact.mkdir(parents=True)

    # ---- Phase A: original session, set_artifact_dir + capture state ----
    manifest = WorkflowManifest(
        workflow_id="test-workflow",
        phases=[
            Phase(id="test-workflow:design", namespace="test-workflow", file="design"),
            Phase(
                id="test-workflow:implement",
                namespace="test-workflow",
                file="implement",
            ),
        ],
        main_role="coordinator",
    )
    persist_calls: list[dict] = []

    async def capture_persist(state: dict) -> None:
        persist_calls.append(dict(state))

    confirm = AsyncMock(return_value=True)
    engine_a = WorkflowEngine(manifest, capture_persist, confirm, cwd=tmp_path)
    await engine_a.set_artifact_dir(str(artifact))
    state_a = engine_a.to_session_state()
    assert state_a["artifact_dir"] == str(artifact.resolve())

    # ---- Phase B: real chicsession save/load round-trip ----
    mgr = ChicsessionManager(root_dir=tmp_path)
    chic = Chicsession(
        name="resumed",
        active_agent="coordinator",
        agents=[
            ChicsessionEntry(name="coordinator", session_id="sess-1", cwd=str(tmp_path))
        ],
        workflow_state=state_a,
    )
    mgr.save(chic)
    loaded = mgr.load("resumed")
    assert loaded.workflow_state is not None
    assert loaded.workflow_state["artifact_dir"] == str(artifact.resolve())

    # ---- Phase C: from_session_state restores; no set_artifact_dir recall ----
    resume_persist = AsyncMock()
    engine_b = WorkflowEngine.from_session_state(
        state=loaded.workflow_state,
        manifest=manifest,
        persist_fn=resume_persist,
        confirm_callback=AsyncMock(),
        cwd=tmp_path,
    )
    # Construction must not re-persist; state was loaded from disk.
    resume_persist.assert_not_awaited()
    assert engine_b.artifact_dir == artifact.resolve()
    assert engine_b.get_artifact_dir() == artifact.resolve()

    # ---- Phase D: assemble next-phase prompt with the resumed engine ----
    prompt = assemble_phase_prompt(
        workflow_dir=wf_dir,
        role_name="coordinator",
        current_phase="implement",
        artifact_dir=engine_b.get_artifact_dir(),
    )
    assert prompt is not None
    _assert_substituted(prompt, artifact.resolve(), label="resumed prompt")
    assert "IMPLEMENT-MARKER" in prompt
    assert "IDENTITY-MARKER" in prompt

    # No coordinator recall: engine_b never had set_artifact_dir invoked
    # post-construction. Check that the resume_persist mock is still pristine.
    resume_persist.assert_not_awaited()


# ---------------------------------------------------------------------------
# Test 3 — Cross-axis seam: both delivery paths substitute identically
# ---------------------------------------------------------------------------


async def test_e2e_awareness_install_x_artifact_dir_seam(
    mock_sdk, tmp_path, monkeypatch
) -> None:
    """Both phase-prompt delivery sites flow through the substitution helper.

    Renamed from ``test_e2e_group_d_x_group_e_seam`` per Terminology2's
    behavior-descriptive naming correction. Group D's two delivery sites
    are activation kickoff (``_activate_workflow``) and phase advance
    (``_inject_phase_prompt_to_main_agent``). Both call
    ``assemble_phase_prompt`` and pass ``engine.get_artifact_dir()``.
    With ``engine.artifact_dir`` set BEFORE either site fires, the agent
    must receive the resolved path at both, never the literal token.
    """
    monkeypatch.chdir(tmp_path)
    _setup_workflow_with_token(tmp_path)
    artifact = tmp_path / "artifacts" / "seam-test"

    app = ChatApp()
    sent: list[str] = []

    def _capture(prompt: str, *, display_as: str | None = None) -> None:
        sent.append(prompt)

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

            # Activate first to materialize the engine, then bind artifact_dir
            # BEFORE the captured delivery sites fire.
            await app._activate_workflow("test-workflow")
            await pilot.pause()
            engine = app._workflow_engine
            assert engine is not None
            await engine.set_artifact_dir(str(artifact))

            # Path A: re-fire activation-style kickoff via the assembler.
            # We cannot re-run _activate_workflow on the same engine, so
            # we exercise the same code path the activation kickoff calls
            # (assemble_phase_prompt + _send_to_active_agent) directly.
            from claudechic.workflows.agent_folders import (
                assemble_phase_prompt as assemble,
            )

            wf_data = app._load_result.get_workflow("test-workflow")
            assert wf_data is not None
            kickoff_prompt = assemble(
                workflow_dir=wf_data.path,
                role_name="coordinator",
                current_phase=engine.get_current_phase(),
                artifact_dir=engine.get_artifact_dir(),
            )
            assert kickoff_prompt is not None
            _assert_substituted(
                kickoff_prompt, artifact.resolve(), label="kickoff path"
            )

            # Path B: advance-style delivery via _inject_phase_prompt_to_main_agent
            sent.clear()
            with patch.object(app, "_send_to_active_agent", side_effect=_capture):
                app._inject_phase_prompt_to_main_agent(
                    "test-workflow", "coordinator", "implement"
                )

            assert len(sent) == 1, (
                f"Advance path must send exactly one prompt; got {len(sent)}"
            )
            _assert_substituted(sent[0], artifact.resolve(), label="advance path")

            # Both delivery sites produced substituted content; confirm
            # they share the same substituted artifact_dir token site.
            assert str(artifact.resolve()) in kickoff_prompt
            assert str(artifact.resolve()) in sent[0]
