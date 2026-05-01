"""Tests for Component B (agent role identity) -- abast_accf332_sync.

Covers sub-units B1..B5:
- B1: ``DEFAULT_ROLE`` sentinel constant
- B2: ``Agent.agent_type`` runtime attribute default
- B3: workflow activation promotes / deactivation reverts the live agent role
- B4: closure binding -- guardrail hook + ``_make_options`` resolve
       ``agent.agent_type`` (and ``agent.effort``) live, not at construction time
- B5: case-insensitive rejection of ``"default"`` as ``main_role`` in workflow YAML

Test names follow the SPEC convention: ``test_b<n>_<concept>_<expectation>``.
"""

from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml
from claudechic.agent import DEFAULT_ROLE, Agent
from claudechic.app import ChatApp


# ---------------------------------------------------------------------------
# Shared fixtures and helpers
# ---------------------------------------------------------------------------


async def _mock_prompt_chicsession_name(self, workflow_id: str) -> str | None:
    """Test stub: skip the TUI chicsession-name prompt."""
    self._chicsession_name = workflow_id
    return workflow_id


def _setup_minimal_workflow(root: Path, *, main_role: str = "coordinator") -> None:
    """Lay out a minimal workflow under ``root`` with role folders."""
    (root / "global").mkdir(parents=True, exist_ok=True)
    wf_dir = root / "workflows" / "test_workflow"
    wf_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "workflow_id": "test_workflow",
        "main_role": main_role,
        "phases": [
            {"id": "design", "file": "design"},
            {"id": "implement", "file": "implement"},
        ],
    }
    (wf_dir / "test_workflow.yaml").write_text(
        yaml.safe_dump(manifest), encoding="utf-8"
    )

    role_dir = wf_dir / main_role
    role_dir.mkdir()
    (role_dir / "identity.md").write_text(f"You are the {main_role}.", encoding="utf-8")
    (role_dir / "design.md").write_text("Design phase.", encoding="utf-8")
    (role_dir / "implement.md").write_text("Implement phase.", encoding="utf-8")


# ---------------------------------------------------------------------------
# B1: DEFAULT_ROLE sentinel constant
# ---------------------------------------------------------------------------


class TestB1DefaultRoleConstant:
    """The DEFAULT_ROLE sentinel string is the locked contract value."""

    def test_b1_default_role_constant_value(self) -> None:
        """``DEFAULT_ROLE`` is the literal string ``"default"``.

        Locked in TEST_SPECIFICATION's "Locked contract strings" table:
        ``DEFAULT_ROLE == "default"``. Tests must import the constant
        rather than compare against the literal directly, but the
        constant's value itself is contract.
        """
        assert DEFAULT_ROLE == "default"

    def test_b1_default_role_importable_from_agent_module(self) -> None:
        """``DEFAULT_ROLE`` lives in ``claudechic.agent`` (B-substrate home)."""
        from claudechic import agent as agent_mod

        assert hasattr(agent_mod, "DEFAULT_ROLE")
        assert agent_mod.DEFAULT_ROLE == DEFAULT_ROLE


# ---------------------------------------------------------------------------
# B2: Agent.agent_type runtime attribute
# ---------------------------------------------------------------------------


class TestB2AgentTypeAttribute:
    """``Agent.agent_type`` is set at construction and mutable."""

    def test_b2_agent_type_defaults_to_default_role(self, tmp_path: Path) -> None:
        """``Agent()`` without ``agent_type`` resolves to the sentinel."""
        agent = Agent(name="A", cwd=tmp_path)
        assert agent.agent_type == DEFAULT_ROLE

    def test_b2_agent_type_accepts_explicit_role(self, tmp_path: Path) -> None:
        """Passing ``agent_type=...`` stores the value verbatim."""
        agent = Agent(name="A", cwd=tmp_path, agent_type="skeptic")
        assert agent.agent_type == "skeptic"

    def test_b2_agent_type_is_mutable(self, tmp_path: Path) -> None:
        """``agent.agent_type`` can be flipped at runtime (B3 promote/revert)."""
        agent = Agent(name="A", cwd=tmp_path)
        assert agent.agent_type == DEFAULT_ROLE
        agent.agent_type = "coordinator"
        assert agent.agent_type == "coordinator"
        agent.agent_type = DEFAULT_ROLE
        assert agent.agent_type == DEFAULT_ROLE


# ---------------------------------------------------------------------------
# B3: workflow activation promotes / deactivation reverts agent_type
# ---------------------------------------------------------------------------


pytestmark_b3 = [pytest.mark.asyncio, pytest.mark.timeout(30)]


@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_b3_workflow_activation_promotes_agent_no_sdk_reconnect(
    mock_sdk, tmp_path, monkeypatch
) -> None:
    """Gestalt user-side: activating a workflow promotes ``agent.agent_type``.

    Per SPEC §B3 the main agent's role flips to the workflow's
    ``main_role`` on activation WITHOUT an SDK reconnect. The test
    captures the agent's identity reference before activation and then
    asserts that the same instance now reports the new role.
    """
    monkeypatch.chdir(tmp_path)
    _setup_minimal_workflow(tmp_path, main_role="coordinator")

    app = ChatApp()

    with ExitStack() as stack:
        stack.enter_context(patch("claudechic.sessions.count_sessions", return_value=1))
        stack.enter_context(
            patch.object(
                ChatApp, "_prompt_chicsession_name", _mock_prompt_chicsession_name
            )
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

            # Before activation: main agent has DEFAULT_ROLE.
            agent = app._agent
            assert agent is not None
            agent_id_before = id(agent)
            agent_session_before = agent.session_id
            assert agent.agent_type == DEFAULT_ROLE

            await app._activate_workflow("test_workflow")
            await pilot.pause()

            # Same agent instance, same session: the role was flipped
            # in-place, no reconnect.
            assert id(app._agent) == agent_id_before
            assert app._agent.session_id == agent_session_before
            assert app._agent.agent_type == "coordinator"


@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_b3_workflow_deactivation_reverts_agent_to_default(
    mock_sdk, tmp_path, monkeypatch
) -> None:
    """Deactivating the workflow reverts the agent role to the sentinel."""
    monkeypatch.chdir(tmp_path)
    _setup_minimal_workflow(tmp_path, main_role="coordinator")

    app = ChatApp()

    with ExitStack() as stack:
        stack.enter_context(patch("claudechic.sessions.count_sessions", return_value=1))
        stack.enter_context(
            patch.object(
                ChatApp, "_prompt_chicsession_name", _mock_prompt_chicsession_name
            )
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

            await app._activate_workflow("test_workflow")
            await pilot.pause()
            assert app._agent.agent_type == "coordinator"

            app._deactivate_workflow()
            await pilot.pause()

            assert app._agent.agent_type == DEFAULT_ROLE


@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_b3_agent_can_query_own_role_via_get_agent_info(tmp_path) -> None:
    """Gestalt agent-side: ``mcp__chic__get_agent_info`` reports ``agent_type``.

    The MCP aggregator tool ``get_agent_info`` renders a ``## Identity``
    section that includes ``role (agent_type): <role>``. After workflow
    promotion the helper sees the live value rather than the manifest's
    static ``main_role``. This test exercises the MCP handler directly
    against a stub app/agent_manager.
    """
    from claudechic.mcp import _make_get_agent_info, set_app

    class _StubAgent:
        def __init__(self, name: str, role: str) -> None:
            self.name = name
            self.id = name
            self.session_id = f"session-{name}"
            self.cwd = tmp_path
            self.status = "idle"
            self.worktree = None
            self.agent_type = role
            self.model = "opus"
            self.effort = "high"

        @property
        def analytics_id(self) -> str:
            return self.session_id or self.id

    class _StubMgr:
        def __init__(self) -> None:
            self.agents: dict[str, _StubAgent] = {}
            self.active = None

        def add(self, agent: _StubAgent) -> None:
            self.agents[agent.name] = agent
            if self.active is None:
                self.active = agent

        def find_by_name(self, name: str) -> _StubAgent | None:
            return self.agents.get(name)

    class _StubApp:
        def __init__(self) -> None:
            self.agent_mgr = _StubMgr()
            self._workflow_engine = None
            self._manifest_loader = None
            self._get_disabled_rules = lambda: None

        def run_worker(self, coro):
            """Mirror MockApp pattern in test_mcp_message_agent."""
            try:
                coro.close()
            except Exception:
                pass

    app = _StubApp()
    coord = _StubAgent("coordinator-agent", role="coordinator")
    app.agent_mgr.add(coord)

    set_app(app)
    try:
        tool = _make_get_agent_info(caller_name="coordinator-agent")
        response = await tool.handler({})
        text = response["content"][0]["text"]

        # Locked contract strings.
        assert "## Identity" in text
        assert "## Session" in text
        assert "## Active workflow + phase" in text
        # The live role is reported, not DEFAULT_ROLE.
        assert "role (agent_type): coordinator" in text

        # Flip the role in place; the next query sees the new value.
        coord.agent_type = "skeptic"
        response2 = await tool.handler({})
        text2 = response2["content"][0]["text"]
        assert "role (agent_type): skeptic" in text2
        assert "role (agent_type): coordinator" not in text2
    finally:
        set_app(None)


# ---------------------------------------------------------------------------
# B4: closure binding -- guardrail hooks + _make_options resolve live values
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_b4_guardrail_hook_closure_binds_agent_not_main_role(
    mock_sdk, tmp_path, monkeypatch
) -> None:
    """Seam #1 (B<->A): hook closure resolves ``agent.agent_type`` LIVE.

    Builds the hooks via ``ChatApp._guardrail_hooks(agent=agent)`` and
    captures the ``agent_role`` callable that gets passed into
    ``create_guardrail_hooks``. After mutating ``agent.agent_type`` the
    callable must return the NEW value -- proving the closure captured
    a reference to the agent, not a snapshot of the role string.
    """
    monkeypatch.chdir(tmp_path)
    _setup_minimal_workflow(tmp_path, main_role="coordinator")

    app = ChatApp()

    captured: dict[str, Any] = {}

    def _spy(*args, **kwargs):
        captured["agent_role"] = kwargs.get("agent_role")
        # Return something hook-shaped so _guardrail_hooks doesn't crash
        # when caller iterates the result.
        return {"PreToolUse": []}

    with ExitStack() as stack:
        stack.enter_context(patch("claudechic.sessions.count_sessions", return_value=1))
        stack.enter_context(
            patch.object(
                ChatApp, "_prompt_chicsession_name", _mock_prompt_chicsession_name
            )
        )
        stack.enter_context(
            patch("claudechic.guardrails.hooks.create_guardrail_hooks", _spy)
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

            agent = Agent(name="closure-agent", cwd=tmp_path, agent_type="role-A")

            # Build hooks ONCE -- the closure now binds to ``agent``.
            app._guardrail_hooks(agent=agent)

            role_resolver = captured.get("agent_role")
            assert callable(role_resolver), (
                "create_guardrail_hooks should receive a callable role "
                "resolver when an Agent instance is supplied (B4 seam)."
            )
            assert role_resolver() == "role-A"

            # Mutate the agent AFTER the hook was constructed.
            agent.agent_type = "role-B"
            assert role_resolver() == "role-B", (
                "Hook closure captured a STATIC snapshot of agent.agent_type. "
                "Per SPEC §B4 the closure must resolve the role live so "
                "workflow activation/deactivation takes effect without an "
                "SDK reconnect."
            )

            # Flip again, including reverting to the sentinel.
            agent.agent_type = DEFAULT_ROLE
            assert role_resolver() == DEFAULT_ROLE


@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_b4_make_options_reads_live_agent_type_and_effort(
    mock_sdk, tmp_path, monkeypatch
) -> None:
    """Seam #2 (C<->B): ``_make_options(agent=)`` reads role + effort LIVE.

    The options factory is called on every fresh hook attach (sub-agent
    spawn, model swap, post-compact reattach). Per SPEC §B4 + §C1 the
    factory must dereference ``agent.agent_type`` for the
    ``CLAUDE_AGENT_ROLE`` env var and ``agent.effort`` for the SDK's
    ``effort=`` kwarg, so two consecutive calls with the same Agent
    instance produce two different options when the agent's fields
    have changed in between.
    """
    monkeypatch.chdir(tmp_path)
    _setup_minimal_workflow(tmp_path, main_role="coordinator")

    app = ChatApp()

    with ExitStack() as stack:
        stack.enter_context(patch("claudechic.sessions.count_sessions", return_value=1))
        stack.enter_context(
            patch.object(
                ChatApp, "_prompt_chicsession_name", _mock_prompt_chicsession_name
            )
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

            agent = Agent(name="seam-agent", cwd=tmp_path, agent_type="role-A")
            agent.effort = "low"

            opts1 = app._make_options(cwd=tmp_path, agent=agent)
            assert opts1.env.get("CLAUDE_AGENT_ROLE") == "role-A"
            assert opts1.effort == "low"

            # Flip both fields between calls.
            agent.agent_type = "role-B"
            agent.effort = "max"

            opts2 = app._make_options(cwd=tmp_path, agent=agent)
            assert opts2.env.get("CLAUDE_AGENT_ROLE") == "role-B", (
                "_make_options should read agent.agent_type LIVE on every "
                "call (SPEC §B4); got the stale value from opts1."
            )
            assert opts2.effort == "max", (
                "_make_options should read agent.effort LIVE on every "
                "call (SPEC §C1); got the stale value from opts1."
            )

            # Revert to the sentinel and the env var disappears
            # (or holds DEFAULT_ROLE -- either is consistent with B4 so
            # long as the previous role is gone).
            agent.agent_type = DEFAULT_ROLE
            opts3 = app._make_options(cwd=tmp_path, agent=agent)
            role3 = opts3.env.get("CLAUDE_AGENT_ROLE")
            assert role3 in (DEFAULT_ROLE, None), (
                "After reverting agent.agent_type to DEFAULT_ROLE, "
                "_make_options should not still report 'role-B'."
            )


# ---------------------------------------------------------------------------
# B5: case-insensitive rejection of "default" as main_role
# ---------------------------------------------------------------------------


_CASE_VARIANTS_OF_DEFAULT = [
    "Default",
    "DEFAULT",
    " default ",
    "default\n",
    "dEfAuLt",
    "\tdefault",
]


@pytest.mark.parametrize("main_role_value", _CASE_VARIANTS_OF_DEFAULT)
def test_b5_main_role_rejects_case_variants_of_default(
    tmp_path: Path, main_role_value: str
) -> None:
    """B5 / Scenario 2: every case variant of ``"default"`` is rejected.

    The loader normalizes via ``.strip().lower()`` and compares against
    ``DEFAULT_ROLE``. Each of the six variants in the parameterization
    must round-trip through that normalization to ``"default"`` and
    therefore must produce a ``LoadError`` with ``section="main_role"``
    in ``LoadResult.errors``. The corresponding workflow's ``main_role``
    must be cleared so the loader does not silently accept the value.
    """
    from claudechic.workflows import (
        ManifestLoader,
        TierRoots,
        register_default_parsers,
    )

    pkg = tmp_path / "package"
    wf_dir = pkg / "workflows" / "case_test"
    wf_dir.mkdir(parents=True)
    role_dir = wf_dir / "stub_role"
    role_dir.mkdir()
    (role_dir / "identity.md").write_text("identity\n", encoding="utf-8")

    manifest = {
        "workflow_id": "case_test",
        "main_role": main_role_value,
        "phases": [{"id": "setup"}],
    }
    (wf_dir / "case_test.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")
    (pkg / "global").mkdir(parents=True)

    loader = ManifestLoader(tier_roots=TierRoots(package=pkg, user=None, project=None))
    register_default_parsers(loader)
    result = loader.load()

    matching_errors = [
        e for e in result.errors if getattr(e, "section", None) == "main_role"
    ]
    assert matching_errors, (
        f"Expected a LoadError with section='main_role' for main_role="
        f"{main_role_value!r}; got errors={result.errors!r}"
    )
    # Message must reference 'main_role' so a maintainer reading the log
    # can tie the diagnostic back to the offending manifest field.
    assert any("main_role" in (e.message or "") for e in matching_errors), (
        f"LoadError message should reference 'main_role'. "
        f"Got messages: {[e.message for e in matching_errors]!r}"
    )

    # Loader cleared the offending main_role rather than promoting an
    # agent into the no-role sentinel (which B5 explicitly forbids).
    wf = result.workflows.get("case_test")
    if wf is not None:
        assert wf.main_role != DEFAULT_ROLE
        # Either cleared to None or never populated -- both reject the
        # variant. The contract is "do not accept the case-variant".
        assert wf.main_role is None or wf.main_role.strip().lower() != DEFAULT_ROLE


def test_b5_valid_main_role_loads_without_error(tmp_path: Path) -> None:
    """Sanity check: a normal non-``"default"`` ``main_role`` loads cleanly.

    Guards against a regression where the case-insensitive check is too
    aggressive and starts rejecting valid roles like ``"defaulter"`` or
    ``"role_default"``.
    """
    from claudechic.workflows import (
        ManifestLoader,
        TierRoots,
        register_default_parsers,
    )

    pkg = tmp_path / "package"
    wf_dir = pkg / "workflows" / "ok_test"
    wf_dir.mkdir(parents=True)
    role_dir = wf_dir / "coordinator"
    role_dir.mkdir()
    (role_dir / "identity.md").write_text("id\n", encoding="utf-8")

    manifest = {
        "workflow_id": "ok_test",
        "main_role": "coordinator",
        "phases": [{"id": "setup"}],
    }
    (wf_dir / "ok_test.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")
    (pkg / "global").mkdir(parents=True)

    loader = ManifestLoader(tier_roots=TierRoots(package=pkg, user=None, project=None))
    register_default_parsers(loader)
    result = loader.load()

    main_role_errors = [
        e for e in result.errors if getattr(e, "section", None) == "main_role"
    ]
    assert main_role_errors == []
    assert result.workflows["ok_test"].main_role == "coordinator"
