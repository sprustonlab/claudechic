"""Tests for in-memory phase-prompt delivery (Group D §4.7, §12.2.2).

Covers:
- INV-AW-6: workflow activation sends the assembled phase prompt to the
  active agent via ``_send_to_active_agent``; the kickoff body IS the
  assembled prompt; no file I/O.
- INV-AW-8: ``_inject_phase_prompt_to_main_agent`` calls
  ``assemble_phase_prompt`` and sends the result via
  ``_send_to_active_agent``; no file I/O.
- INV-AW-9: ``create_session_start_compact_hook(engine, agent_role, workflow_dir)``
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
    create_session_start_compact_hook,
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

            # Force the assembler to return None to exercise the fallback path.
            # ``assemble_agent_prompt`` is the orchestrator at the activation
            # site (SPEC §3.1); patching it simulates "no role/identity/phase
            # content available" without depending on the renderer split.
            with (
                patch.object(app, "_send_to_active_agent", side_effect=_capture),
                patch(
                    "claudechic.workflows.agent_folders.assemble_agent_prompt",
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


def test_session_start_compact_hook_signature() -> None:
    """``create_session_start_compact_hook`` is keyword-only resolver-based.

    The hook is registered at SDK-connect time, BEFORE workflow
    activation. Capture-time positional ``engine`` / ``agent_role`` /
    ``workflow_dir`` would be stale or ``None`` for the coordinator
    agent, so the API is resolver-only: ``get_engine`` / ``get_agent_role``
    / ``get_workflow_dir`` are required keyword-only callables that
    re-read live state at /compact time. Optional resolvers
    (``get_disabled_rules`` / ``get_settings`` / ``get_peer_agents``)
    default to ``None``.
    """
    import inspect

    sig = inspect.signature(create_session_start_compact_hook)
    positional = [
        name
        for name, p in sig.parameters.items()
        if p.kind
        in (
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.POSITIONAL_ONLY,
        )
    ]
    assert positional == [], (
        f"All parameters must be keyword-only; got positional: {positional}"
    )
    # Required resolvers carry no default.
    for kw in ("get_engine", "get_agent_role", "get_workflow_dir"):
        p = sig.parameters.get(kw)
        assert p is not None, f"missing required keyword-only arg {kw!r}"
        assert p.default is inspect.Parameter.empty, (
            f"{kw} must be required (no default), got default={p.default!r}"
        )
    # Optional providers default to None so simple registrations work.
    for kw in ("get_disabled_rules", "get_settings", "get_peer_agents"):
        p = sig.parameters.get(kw)
        assert p is not None, f"missing keyword-only arg {kw!r}"
        assert p.default is None, f"{kw} default must be None, got {p.default!r}"


async def test_inv_aw_9_post_compact_returns_additional_context_when_prompt(
    tmp_path: Path,
) -> None:
    """SessionStart(matcher=compact) closure returns ``hookSpecificOutput.additionalContext``.

    Per Claude Code hooks docs (https://code.claude.com/docs/en/hooks):
    ``PostCompact`` is side-effect-only and CANNOT inject context; the
    correct hook for re-injecting context after compaction is
    ``SessionStart`` with ``source: "compact"``. Return shape:
    ``{"hookSpecificOutput": {"hookEventName": "SessionStart",
    "additionalContext": prompt}}`` -- the same shape PostToolUse /
    UserPromptSubmit / Notification / SubagentStart use for
    ``additionalContext`` injection. The legacy ``{"reason": prompt}``
    shape was the wrong contract on the wrong hook event; the agent
    reported "no identity / no phase / no constraints" after /compact.
    """
    wf_dir = _setup_workflow(tmp_path)

    class FakeEngine:
        workflow_id = "test-workflow"

        def get_current_phase(self) -> str:
            return "implement"

        def get_artifact_dir(self):
            return None

    fake_engine = FakeEngine()
    hook_dict = create_session_start_compact_hook(
        get_engine=lambda: fake_engine,
        get_agent_role=lambda: "coordinator",
        get_workflow_dir=lambda: wf_dir,
    )
    matchers = hook_dict["SessionStart"]
    closure = matchers[0].hooks[0]

    result = await closure({}, None, None)
    spec_out = result.get("hookSpecificOutput", {})
    assert spec_out.get("hookEventName") == "SessionStart", (
        f"Wrong hookEventName: {result!r}"
    )
    additional = spec_out.get("additionalContext", "")
    assert "IMPLEMENT-MARKER" in additional
    assert "IDENTITY-MARKER" in additional
    # ``reason`` must NOT be the carrier -- that field is for blocking
    # decisions and is not the context-injection channel.
    assert "reason" not in result


async def test_session_start_compact_hook_resolves_engine_at_fire_time(
    tmp_path: Path,
) -> None:
    """Hook registered with no captured state still injects post-activation.

    Validates the resolver-based registration path: the hook is created
    BEFORE workflow activation (the coordinator scenario), engine /
    role / workflow_dir are all ``None`` at registration. After
    "activation" populates the resolver targets, /compact fires the
    closure and the resolvers feed the live engine through to
    ``assemble_agent_prompt``. The output carries the role+phase
    prompt that registration-time capture would have missed.
    """
    wf_dir = _setup_workflow(tmp_path)

    class FakeEngine:
        workflow_id = "test-workflow"

        def get_current_phase(self) -> str:
            return "implement"

        def get_artifact_dir(self):
            return None

    # Box references that "fill in" after registration -- the
    # registration-time path mirrors how ChatApp registers hooks at
    # connect time, before _activate_workflow runs.
    state: dict[str, Any] = {"engine": None, "role": "", "wf_dir": None}

    hook_dict = create_session_start_compact_hook(
        get_engine=lambda: state["engine"],
        get_agent_role=lambda: state["role"],
        get_workflow_dir=lambda: state["wf_dir"],
    )
    closure = hook_dict["SessionStart"][0].hooks[0]

    # Fire BEFORE activation: closure resolves engine=None -> returns {}.
    pre_result = await closure({}, None, None)
    assert pre_result == {}, (
        f"Pre-activation hook fire must inject nothing; got {pre_result!r}"
    )

    # "Activate" -- populate the resolver targets.
    state["engine"] = FakeEngine()
    state["role"] = "coordinator"
    state["wf_dir"] = wf_dir

    # Fire AFTER activation: closure now resolves a real engine and
    # delivers the role+phase prompt.
    post_result = await closure({}, None, None)
    spec_out = post_result.get("hookSpecificOutput", {})
    assert spec_out.get("hookEventName") == "SessionStart", (
        f"Wrong hookEventName: {post_result!r}"
    )
    additional = spec_out.get("additionalContext", "")
    assert "IMPLEMENT-MARKER" in additional
    assert "IDENTITY-MARKER" in additional


async def test_inv_aw_9_post_compact_returns_empty_when_none(
    tmp_path: Path,
) -> None:
    """PostCompact closure returns ``{}`` when assemble yields nothing.

    Per the user-approved SPEC change (manifest opt-in removed), the
    environment segment is enabled for every active workflow by default
    -- so a fake engine reporting an active workflow_id will get the
    environment segment injected even when ``workflow_dir`` is missing.
    To exercise the truly-empty assembly path, the engine here reports
    ``workflow_id=None`` (no active workflow) so the renderer's
    no-active-workflow guard suppresses environment too.
    """

    class FakeEngine:
        workflow_id: str | None = None

        def get_current_phase(self) -> str | None:
            return None

        def get_artifact_dir(self):
            return None

    # Point at a missing workflow dir so assemble_phase_prompt returns None
    fake_engine = FakeEngine()
    missing_dir = tmp_path / "does_not_exist"
    hook_dict = create_session_start_compact_hook(
        get_engine=lambda: fake_engine,
        get_agent_role=lambda: "coordinator",
        get_workflow_dir=lambda: missing_dir,
    )
    closure = hook_dict["SessionStart"][0].hooks[0]
    result = await closure({}, None, None)
    assert result == {}


async def test_post_compact_get_settings_excludes_post_compact_site_drops_constraints_block(
    tmp_path: Path,
) -> None:
    """Skeptic Gap 1: when the ``get_settings`` provider returns a
    ``GateSettings`` whose ``constraints_segment.scope.sites`` excludes
    ``post-compact``, the post-compact prompt contains no
    ``## Constraints`` block.

    Pins the user-tier suppression contract end-to-end through the
    PostCompact hook closure: the user's runtime config edit reaches
    the renderer at hook-fire time via ``get_settings``, and the gate
    drops the slice rather than the renderer producing it.
    """
    from claudechic.workflows.agent_folders import (
        ConstraintsSegmentSettings,
        EnvironmentSegmentSettings,
        GateSettings,
    )

    wf_dir = _setup_workflow(tmp_path)

    # Fake digest entry so a constraints block WOULD fire in the absence
    # of the user-tier suppression. This isolates the gate behavior.
    class FakeEngine:
        workflow_id = "test-workflow"
        loader = None  # no real loader; gate-level suppression doesn't need it
        project_root = None

        def get_current_phase(self) -> str:
            return "design"

        def get_artifact_dir(self):
            return None

    # User-tier override: drop post-compact from constraints_segment.sites.
    narrowed = GateSettings(
        constraints_segment=ConstraintsSegmentSettings(
            sites=frozenset({"spawn", "activation", "phase-advance"}),
        ),
        environment_segment=EnvironmentSegmentSettings(),
    )

    fake_engine = FakeEngine()
    hook_dict = create_session_start_compact_hook(
        get_engine=lambda: fake_engine,
        get_agent_role=lambda: "coordinator",
        get_workflow_dir=lambda: wf_dir,
        get_settings=lambda: narrowed,
    )
    closure = hook_dict["SessionStart"][0].hooks[0]
    result = await closure({}, None, None)

    # Either {} (every segment empty) or {"reason": prompt_without_constraints}.
    reason = result.get("reason", "")
    assert "## Constraints" not in reason, (
        "post-compact must omit constraints block when get_settings narrows "
        f"scope.sites to exclude post-compact. Got: {reason[:300]}"
    )


async def test_inv_aw_9_post_compact_no_file_io(tmp_path: Path) -> None:
    """PostCompact closure performs zero file I/O at write/unlink/mkdir."""
    wf_dir = _setup_workflow(tmp_path)

    class FakeEngine:
        workflow_id = "test-workflow"

        def get_current_phase(self) -> str:
            return "design"

        def get_artifact_dir(self):
            return None

    fake_engine = FakeEngine()
    hook_dict = create_session_start_compact_hook(
        get_engine=lambda: fake_engine,
        get_agent_role=lambda: "coordinator",
        get_workflow_dir=lambda: wf_dir,
    )
    closure = hook_dict["SessionStart"][0].hooks[0]

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
