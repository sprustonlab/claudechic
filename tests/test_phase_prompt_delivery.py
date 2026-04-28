"""Tests for in-memory phase-prompt delivery (Group D §4.7, §12.2.2).

Covers:
- INV-AW-6: workflow activation sends the assembled phase prompt to the
  active agent via ``_send_to_active_agent``; the kickoff body IS the
  assembled prompt; no file I/O.
- INV-AW-8: ``_inject_phase_prompt_to_main_agent`` calls
  ``assemble_phase_prompt`` and sends the result via
  ``_send_to_active_agent``; no file I/O.
- INV-AW-9: ``create_post_compact_hook(engine, agent_role, workflow_dir)``
  retains the existing-code 3-arg closure shape; the closure calls
  ``assemble_phase_prompt(workflow_dir, agent_role, current_phase)``
  and returns ``{"reason": prompt}`` if non-empty, ``{}`` otherwise.

Plus one end-to-end test (per Skeptic2 mitigation): drives a real
``ChatApp`` through workflow activation and asserts the active agent's
first user message contains the assembled phase-prompt content (not
just a call assertion).
"""

from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from claudechic.app import ChatApp
from claudechic.workflows.agent_folders import (
    assemble_phase_prompt,
    create_post_compact_hook,
)

pytestmark = [pytest.mark.asyncio, pytest.mark.timeout(30)]


# ---------------------------------------------------------------------------
# Workflow fixture (mirrors test_phase_injection.py pattern)
# ---------------------------------------------------------------------------


def _setup_workflow(root: Path, *, with_identity: bool = True) -> Path:
    """Create a minimal test workflow under ``root``.

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
    if with_identity:
        (coord / "identity.md").write_text(
            "IDENTITY-MARKER: you are the coordinator.", encoding="utf-8"
        )
    (coord / "design.md").write_text(
        "DESIGN-MARKER: design phase instructions.", encoding="utf-8"
    )
    (coord / "implement.md").write_text(
        "IMPLEMENT-MARKER: implement phase instructions.", encoding="utf-8"
    )
    return wf_dir


async def _mock_chicsession_name(self, workflow_id: str) -> str | None:
    """Test stub: skip TUI prompt, set chicsession name to workflow id."""
    self._chicsession_name = workflow_id
    return workflow_id


# ---------------------------------------------------------------------------
# INV-AW-6: workflow activation sends assembled phase prompt
# ---------------------------------------------------------------------------


async def test_inv_aw_6_activation_sends_assembled_prompt(
    mock_sdk, tmp_path, monkeypatch
) -> None:
    """On workflow activation, the kickoff message IS the assembled phase prompt."""
    monkeypatch.chdir(tmp_path)
    _setup_workflow(tmp_path)

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

            # Patch _send_to_active_agent to capture what activation sends
            with patch.object(app, "_send_to_active_agent", side_effect=_capture):
                await app._activate_workflow("test-workflow")
                await pilot.pause()

    # Exactly one kickoff send, and it IS the assembled phase prompt
    assert len(sent) == 1, f"Expected one kickoff send, got {len(sent)}"
    body = sent[0]
    assert "IDENTITY-MARKER" in body, (
        "Kickoff body must contain identity.md content (the assembled phase prompt)."
    )
    assert "DESIGN-MARKER" in body, (
        "Kickoff body must contain the first phase's instructions."
    )

    # No phase_context.md file written
    phase_file = tmp_path / ".claude" / "phase_context.md"
    assert not phase_file.exists(), (
        "Workflow activation must NOT write .claude/phase_context.md anymore."
    )


async def test_activation_fallback_logs_warning_when_prompt_none(
    mock_sdk, tmp_path, monkeypatch, caplog
) -> None:
    """When ``assemble_phase_prompt`` returns None, a WARNING is logged + minimal notice sent."""
    import logging

    monkeypatch.chdir(tmp_path)
    _setup_workflow(tmp_path, with_identity=True)

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

            # Force the assembler to return None to exercise the fallback path
            with (
                patch.object(app, "_send_to_active_agent", side_effect=_capture),
                patch(
                    "claudechic.workflows.agent_folders.assemble_phase_prompt",
                    return_value=None,
                ),
                caplog.at_level(logging.WARNING, logger="claudechic"),
            ):
                await app._activate_workflow("test-workflow")
                await pilot.pause()

    # Fallback notice was sent
    assert len(sent) == 1
    assert "test-workflow" in sent[0]
    # WARNING was logged with role + phase identifiers
    warnings = [r for r in caplog.records if r.levelname == "WARNING"]
    assert any("Phase prompt assembled to None" in r.getMessage() for r in warnings), (
        f"No fallback WARNING in logs: {[r.getMessage() for r in warnings]}"
    )


# ---------------------------------------------------------------------------
# INV-AW-8: phase-advance injects via _send_to_active_agent
# ---------------------------------------------------------------------------


async def test_inv_aw_8_inject_calls_assembler_and_sends(
    mock_sdk, tmp_path, monkeypatch
) -> None:
    """``_inject_phase_prompt_to_main_agent`` calls assemble + _send_to_active_agent. No file I/O."""
    monkeypatch.chdir(tmp_path)
    _setup_workflow(tmp_path)

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

            await app._activate_workflow("test-workflow")
            await pilot.pause()

            # Call inject directly, capturing what gets sent
            sent.clear()
            with patch.object(app, "_send_to_active_agent", side_effect=_capture):
                app._inject_phase_prompt_to_main_agent(
                    "test-workflow", "coordinator", "implement"
                )

            # Assembler was called for the new phase; result was sent
            assert len(sent) == 1, f"Expected one send, got {len(sent)}: {sent}"
            assert "IMPLEMENT-MARKER" in sent[0], (
                "Sent prompt must contain implement-phase content."
            )
            assert "IDENTITY-MARKER" in sent[0], (
                "Sent prompt must include identity.md content."
            )

    # No phase_context.md file written
    phase_file = tmp_path / ".claude" / "phase_context.md"
    assert not phase_file.exists(), (
        "_inject_phase_prompt_to_main_agent must NOT write any file."
    )


# ---------------------------------------------------------------------------
# INV-AW-9: PostCompact hook signature + closure behavior
# ---------------------------------------------------------------------------


def test_inv_aw_9_post_compact_hook_signature() -> None:
    """``create_post_compact_hook`` keeps the 3-arg signature ``(engine, agent_role, workflow_dir)``."""
    import inspect

    sig = inspect.signature(create_post_compact_hook)
    params = list(sig.parameters.keys())
    assert params == ["engine", "agent_role", "workflow_dir"], (
        f"Signature drift: got {params}"
    )


async def test_inv_aw_9_post_compact_returns_reason_when_prompt(
    tmp_path: Path,
) -> None:
    """PostCompact closure returns ``{"reason": prompt}`` when assemble yields content."""
    wf_dir = _setup_workflow(tmp_path)

    class FakeEngine:
        workflow_id = "test-workflow"

        def get_current_phase(self) -> str:
            return "implement"

        def get_artifact_dir(self):
            return None

    hook_dict = create_post_compact_hook(
        engine=FakeEngine(),
        agent_role="coordinator",
        workflow_dir=wf_dir,
    )
    matchers = hook_dict["PostCompact"]
    closure = matchers[0].hooks[0]

    result = await closure({}, None, None)
    assert "reason" in result
    assert "IMPLEMENT-MARKER" in result["reason"]
    assert "IDENTITY-MARKER" in result["reason"]


async def test_inv_aw_9_post_compact_returns_empty_when_none(
    tmp_path: Path,
) -> None:
    """PostCompact closure returns ``{}`` when assemble yields nothing."""

    class FakeEngine:
        workflow_id = "test-workflow"

        def get_current_phase(self) -> str | None:
            return None

        def get_artifact_dir(self):
            return None

    # Point at a missing workflow dir so assemble_phase_prompt returns None
    hook_dict = create_post_compact_hook(
        engine=FakeEngine(),
        agent_role="coordinator",
        workflow_dir=tmp_path / "does_not_exist",
    )
    closure = hook_dict["PostCompact"][0].hooks[0]
    result = await closure({}, None, None)
    assert result == {}


async def test_inv_aw_9_post_compact_no_file_io(tmp_path: Path) -> None:
    """PostCompact closure performs zero file I/O at write/unlink/mkdir."""
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

    with (
        patch.object(Path, "write_bytes") as mock_write,
        patch.object(Path, "write_text") as mock_write_text,
        patch.object(Path, "unlink") as mock_unlink,
    ):
        await closure({}, None, None)

    mock_write.assert_not_called()
    mock_write_text.assert_not_called()
    mock_unlink.assert_not_called()


# ---------------------------------------------------------------------------
# E2E test (Skeptic2 mitigation): real activation, real agent, real message
# ---------------------------------------------------------------------------


async def test_e2e_activation_delivers_prompt_to_real_agent(
    mock_sdk, tmp_path, monkeypatch
) -> None:
    """E2E: drive real ChatApp through activation, assert the active agent's
    first user message contains the assembled phase-prompt content.

    Per Skeptic2: '_send_to_active_agent called with X' verifies the call,
    not that the agent actually receives X intact. This test inspects the
    active agent's actual message queue.
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

            await app._activate_workflow("test-workflow")
            # Allow the send-task to run
            await pilot.pause()
            await pilot.pause()

            agent = app.agent_mgr.active
            assert agent is not None, "Active agent must exist after activation"

            user_msgs = [m for m in agent.messages if m.role == "user"]
            assert user_msgs, (
                "Active agent must have received at least one user message"
            )

            # Assert the assembled prompt content reached the agent's queue.
            # The activation is the agent's first turn so it's the first user msg.
            joined = "\n".join(m.content.text for m in user_msgs)
            assert "IDENTITY-MARKER" in joined, (
                f"Active agent did not receive identity.md content. "
                f"Got messages: {joined[:300]}"
            )
            assert "DESIGN-MARKER" in joined, (
                f"Active agent did not receive design-phase content. "
                f"Got messages: {joined[:300]}"
            )

            # Also assert this came via the in-memory delivery path: no file
            phase_file = tmp_path / ".claude" / "phase_context.md"
            assert not phase_file.exists()


# ---------------------------------------------------------------------------
# Sanity: assembler signature
# ---------------------------------------------------------------------------


def test_assemble_phase_prompt_signature() -> None:
    """Signature: ``(workflow_dir, role_name, current_phase, artifact_dir=None)``.

    Group E (artifact directories) added the optional ``artifact_dir``
    parameter for ``${CLAUDECHIC_ARTIFACT_DIR}`` substitution. The first
    three parameters and their order are pinned; ``artifact_dir`` MUST
    have a default value so existing 3-arg callers continue to work.
    """
    import inspect

    sig = inspect.signature(assemble_phase_prompt)
    params = list(sig.parameters.keys())
    assert params[:3] == ["workflow_dir", "role_name", "current_phase"], (
        f"Signature drift on required positional params: got {params}"
    )
    if len(params) > 3:
        assert params[3] == "artifact_dir", (
            f"Group E added 'artifact_dir' as 4th param; got {params}"
        )
        assert sig.parameters["artifact_dir"].default is None, (
            "artifact_dir must default to None"
        )
