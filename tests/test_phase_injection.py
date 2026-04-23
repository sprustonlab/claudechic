"""Tests for sub-agent phase injection (issue #37).

Strict TDD: EVERY test asserts desired post-fix behavior and MUST FAIL
before production code is written.

Testing rules:
- Real ChatApp (from claudechic.app) -- the ONLY app object allowed
- Real Agent, AgentManager, WorkflowEngine -- all real objects
- Real MCP handlers (_make_advance_phase, _make_spawn_agent)
- Real workflow files on disk
- Real guardrail evaluation pipeline
- ONLY the SDK client is mocked (via conftest.py mock_sdk fixture)
- Source inspection (inspect.getsource) for encoding check only (test 1)

Terminology: "agent prompt" = identity.md + phase.md content assembled
by assemble_phase_prompt(). This is the canonical term per agent_folders.py.
"""

from __future__ import annotations

import inspect
import re
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from claudechic.app import ChatApp
from claudechic.workflow_engine.agent_folders import _assemble_agent_prompt

pytestmark = [pytest.mark.asyncio, pytest.mark.timeout(30)]


# ---------------------------------------------------------------------------
# Workflow file setup
# ---------------------------------------------------------------------------


def _setup_workflow_with_roles(root: Path) -> None:
    """Create workflow directory with role folders for phase injection testing.

    Workflow: test-workflow (main_role: coordinator)
    Phases: design -> implement (no advance_checks on design)
    Roles:
      - coordinator: identity.md + implement.md
      - skeptic: identity.md + implement.md
      (no folder for "nonexistent" -- used to test missing role handling)
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

    # Coordinator role folder
    coord_dir = wf_dir / "coordinator"
    coord_dir.mkdir()
    (coord_dir / "identity.md").write_text("You are the coordinator.", encoding="utf-8")
    (coord_dir / "implement.md").write_text(
        "Coordinate implementation activities.", encoding="utf-8"
    )

    # Skeptic role folder
    skeptic_dir = wf_dir / "skeptic"
    skeptic_dir.mkdir()
    (skeptic_dir / "identity.md").write_text(
        "You are the skeptic reviewer.", encoding="utf-8"
    )
    (skeptic_dir / "implement.md").write_text(
        "Review implementation for correctness.", encoding="utf-8"
    )

    # NOTE: No folder for "nonexistent" role -- tests missing role handling


async def _mock_prompt_chicsession_name(self, workflow_id: str) -> str | None:
    """Test stub: skip TUI prompt, return workflow_id as session name."""
    self._chicsession_name = workflow_id
    return workflow_id


# ===========================================================================
# Tests 1-5: Source inspection (code-level properties)
# ===========================================================================


def test_read_text_calls_have_encoding_param() -> None:
    """Every read_text() call in _assemble_agent_prompt must pass encoding='utf-8'."""
    source = inspect.getsource(_assemble_agent_prompt)

    read_text_calls = re.findall(r"\.read_text\([^)]*\)", source)
    assert len(read_text_calls) >= 2, (
        f"Expected at least 2 read_text() calls, found {len(read_text_calls)}"
    )

    for call in read_text_calls:
        assert "encoding" in call, (
            f"read_text() call missing encoding parameter: {call}\n"
            "Cross-platform rule: all read_text() must pass encoding='utf-8'"
        )


def test_agent_accepts_agent_type_kwarg(tmp_path: Path) -> None:
    """Agent(agent_type='skeptic') must not raise and must store the value."""
    from claudechic.agent import Agent

    agent = Agent(name="TestAgent", cwd=tmp_path, agent_type="skeptic")
    assert agent.agent_type == "skeptic"


def test_agent_type_defaults_to_none(tmp_path: Path) -> None:
    """Agent() without agent_type must have agent_type attribute set to None."""
    from claudechic.agent import Agent

    agent = Agent(name="TestAgent", cwd=tmp_path)
    assert agent.agent_type is None


async def test_agent_manager_passes_agent_type_to_agent(
    mock_sdk, tmp_path, monkeypatch
) -> None:
    """AgentManager.create(agent_type=X) must store agent_type on the Agent instance."""
    monkeypatch.chdir(tmp_path)
    _setup_workflow_with_roles(tmp_path)

    from claudechic.mcp import _make_spawn_agent

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
            await app._activate_workflow("test-workflow")
            await pilot.pause()

            # Spawn agent with type= (goes through real AgentManager.create)
            caller_name = app._agent.name
            spawn_tool = _make_spawn_agent(caller_name=caller_name)
            await spawn_tool.handler(
                {
                    "name": "TypedAgent",
                    "path": str(tmp_path),
                    "prompt": "Test agent",
                    "type": "skeptic",
                }
            )
            await pilot.pause()

            agent = app.agent_mgr.find_by_name("TypedAgent")
            assert agent is not None, "TypedAgent not found"
            assert agent.agent_type == "skeptic", (
                f"Agent.agent_type should be 'skeptic' but is "
                f"{getattr(agent, 'agent_type', 'MISSING')!r}. "
                "AgentManager.create() must pass agent_type through to "
                "Agent constructor."
            )


async def test_spawn_agent_no_name_fallback(mock_sdk, tmp_path, monkeypatch) -> None:
    """Spawning without type= must NOT use agent name to find role folder."""
    monkeypatch.chdir(tmp_path)
    _setup_workflow_with_roles(tmp_path)

    from claudechic.mcp import _make_spawn_agent

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
            await app._activate_workflow("test-workflow")
            await pilot.pause()

            caller_name = app._agent.name
            spawn_tool = _make_spawn_agent(caller_name=caller_name)

            # Agent named "skeptic" but NO type= parameter.
            # If name fallback exists, it would match "skeptic" folder
            # and inject identity.md content.
            await spawn_tool.handler(
                {
                    "name": "skeptic",
                    "path": str(tmp_path),
                    "prompt": "Just a helper with a coincidental name",
                }
            )
            await pilot.pause()

            agent = app.agent_mgr.find_by_name("skeptic")
            assert agent is not None, "Agent 'skeptic' not found"

            # Check the agent's first user message does NOT contain
            # identity.md content from the skeptic role folder
            user_msgs = [m for m in agent.messages if m.role == "user"]
            assert len(user_msgs) > 0, (
                "Agent should have at least 1 user message (the prompt)"
            )

            first_msg = user_msgs[0].content.text
            assert "You are the skeptic reviewer" not in first_msg, (
                "Agent named 'skeptic' (no type=) received identity.md content. "
                "This means spawn_agent is using the agent NAME as role_name "
                f"fallback. First message was: {first_msg[:200]}"
            )


# ===========================================================================
# Test 6: spawn_agent warns when type= omitted during active workflow
#
# BEHAVIORAL: Real ChatApp, real spawn_agent handler, real workflow.
# Call spawn_agent without type= while workflow is active.
# Assert the response text contains a warning.
# FAILS: No warning emitted.
# ===========================================================================


async def test_spawn_agent_warns_when_type_missing(
    mock_sdk, tmp_path, monkeypatch
) -> None:
    """spawn_agent must warn when type= is omitted during active workflow."""
    monkeypatch.chdir(tmp_path)
    _setup_workflow_with_roles(tmp_path)

    from claudechic.mcp import _make_spawn_agent

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

            await app._activate_workflow("test-workflow")
            await pilot.pause()

            # Spawn agent WITHOUT type= parameter
            caller_name = app._agent.name
            spawn_tool = _make_spawn_agent(caller_name=caller_name)
            result = await spawn_tool.handler(
                {
                    "name": "NewAgent",
                    "path": str(tmp_path),
                    "prompt": "Do something",
                }
            )
            await pilot.pause()

            response_text = result["content"][0]["text"]
            has_warning = (
                "warning" in response_text.lower()
                or "not receive" in response_text.lower()
            )
            assert has_warning, (
                "spawn_agent should warn when type= is omitted during active workflow. "
                f"Response was: {response_text[:300]}"
            )


# ===========================================================================
# Test 7: advance_phase broadcasts agent prompt to typed sub-agents
#
# BEHAVIORAL: Real ChatApp, real spawn_agent, real advance_phase.
# Spawn a skeptic sub-agent, advance from design to implement,
# check that the skeptic received implement-phase agent prompt.
# FAILS: No broadcast loop in advance_phase.
# ===========================================================================


async def test_advance_phase_broadcasts_to_typed_sub_agents(
    mock_sdk, tmp_path, monkeypatch
) -> None:
    """After advance_phase, typed sub-agents must receive agent prompt."""
    monkeypatch.chdir(tmp_path)
    _setup_workflow_with_roles(tmp_path)

    from claudechic.mcp import _make_advance_phase, _make_spawn_agent

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

            await app._activate_workflow("test-workflow")
            await pilot.pause()

            caller_name = app._agent.name

            # Spawn skeptic sub-agent with type=
            spawn_tool = _make_spawn_agent(caller_name=caller_name)
            await spawn_tool.handler(
                {
                    "name": "Skeptic",
                    "path": str(tmp_path),
                    "prompt": "Be the skeptic",
                    "type": "skeptic",
                }
            )
            await pilot.pause()

            # Advance from design -> implement
            advance_tool = _make_advance_phase(caller_name=caller_name)
            result = await advance_tool.handler({})
            await pilot.pause()

            assert "isError" not in result, f"advance_phase failed: {result}"

            # Skeptic must have received implement-phase agent prompt
            skeptic = app.agent_mgr.find_by_name("Skeptic")
            assert skeptic is not None, "Skeptic agent not found"

            skeptic_msgs = [m for m in skeptic.messages if m.role == "user"]
            has_implement_content = any(
                "Review implementation" in m.content.text for m in skeptic_msgs
            )
            assert has_implement_content, (
                "Typed sub-agent 'Skeptic' did not receive implement-phase agent prompt "
                "after advance. advance_phase must broadcast to typed sub-agents. "
                f"Skeptic has {len(skeptic_msgs)} user message(s): "
                + "; ".join(m.content.text[:80] for m in skeptic_msgs)
            )

            # Skeptic must receive its OWN role content, not coordinator's
            implement_msgs = [
                m for m in skeptic_msgs if "Review implementation" in m.content.text
            ]
            first_implement_msg = implement_msgs[0].content.text
            assert "Coordinate implementation" not in first_implement_msg, (
                "Skeptic received coordinator's phase content instead of its own. "
                "assemble_phase_prompt must use the agent's role_name, not main_role."
            )


# ===========================================================================
# Test 8: advance_phase broadcast skips coordinator
#
# BEHAVIORAL: Coordinator must NOT receive agent prompt via broadcast
# (it already gets content in the advance_phase tool response).
# FAILS: No broadcast loop (proven via sub-agent assertion).
# ===========================================================================


async def test_advance_phase_broadcast_skips_coordinator(
    mock_sdk, tmp_path, monkeypatch
) -> None:
    """Coordinator must NOT receive agent prompt via broadcast."""
    monkeypatch.chdir(tmp_path)
    _setup_workflow_with_roles(tmp_path)

    from claudechic.mcp import _make_advance_phase, _make_spawn_agent

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

            await app._activate_workflow("test-workflow")
            await pilot.pause()

            caller_name = app._agent.name

            spawn_tool = _make_spawn_agent(caller_name=caller_name)
            await spawn_tool.handler(
                {
                    "name": "Skeptic",
                    "path": str(tmp_path),
                    "prompt": "Be the skeptic",
                    "type": "skeptic",
                }
            )
            await pilot.pause()

            # Record coordinator message count before advance
            coordinator = app._agent
            msgs_before = len([m for m in coordinator.messages if m.role == "user"])

            advance_tool = _make_advance_phase(caller_name=caller_name)
            result = await advance_tool.handler({})
            await pilot.pause()

            assert "isError" not in result

            # Prove broadcast exists: skeptic must have received implement content
            skeptic = app.agent_mgr.find_by_name("Skeptic")
            skeptic_msgs = [m for m in skeptic.messages if m.role == "user"]
            has_implement = any(
                "Review implementation" in m.content.text for m in skeptic_msgs
            )
            assert has_implement, (
                "Broadcast loop must exist: Skeptic did not receive implement-phase "
                "agent prompt"
            )

            # Coordinator must NOT have received additional broadcast messages
            msgs_after = len([m for m in coordinator.messages if m.role == "user"])
            assert msgs_after == msgs_before, (
                f"Coordinator received {msgs_after - msgs_before} broadcast "
                "prompt(s) but should receive none (phase content is already in "
                "the tool response). Broadcast must skip main_role."
            )


# ===========================================================================
# Test 9: advance_phase broadcast skips untyped agents
#
# BEHAVIORAL: Untyped agent (no type= at spawn) must NOT receive broadcast.
# FAILS: No broadcast loop (proven via sub-agent assertion).
# ===========================================================================


async def test_advance_phase_broadcast_skips_untyped_sub_agents(
    mock_sdk, tmp_path, monkeypatch
) -> None:
    """Untyped agents (spawned without type=) must NOT receive broadcast."""
    monkeypatch.chdir(tmp_path)
    _setup_workflow_with_roles(tmp_path)

    from claudechic.mcp import _make_advance_phase, _make_spawn_agent

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

            await app._activate_workflow("test-workflow")
            await pilot.pause()

            caller_name = app._agent.name
            spawn_tool = _make_spawn_agent(caller_name=caller_name)

            # Spawn typed sub-agent
            await spawn_tool.handler(
                {
                    "name": "Skeptic",
                    "path": str(tmp_path),
                    "prompt": "Be the skeptic",
                    "type": "skeptic",
                }
            )
            await pilot.pause()

            # Spawn UNtyped agent (no type= parameter)
            await spawn_tool.handler(
                {
                    "name": "Helper",
                    "path": str(tmp_path),
                    "prompt": "Be a helper",
                }
            )
            await pilot.pause()

            # Record helper messages before advance
            helper = app.agent_mgr.find_by_name("Helper")
            helper_msgs_before = len([m for m in helper.messages if m.role == "user"])

            advance_tool = _make_advance_phase(caller_name=caller_name)
            result = await advance_tool.handler({})
            await pilot.pause()

            assert "isError" not in result

            # Prove broadcast exists
            skeptic = app.agent_mgr.find_by_name("Skeptic")
            skeptic_msgs = [m for m in skeptic.messages if m.role == "user"]
            has_implement = any(
                "Review implementation" in m.content.text for m in skeptic_msgs
            )
            assert has_implement, (
                "Broadcast loop must exist: Skeptic did not receive implement-phase "
                "agent prompt"
            )

            # Untyped agent must NOT have received broadcast
            helper_msgs_after = len([m for m in helper.messages if m.role == "user"])
            assert helper_msgs_after == helper_msgs_before, (
                f"Untyped agent 'Helper' received "
                f"{helper_msgs_after - helper_msgs_before} broadcast prompt(s) "
                "but should receive none. Broadcast must skip agents without "
                "agent_type."
            )


# ===========================================================================
# Test 10: advance_phase broadcast handles missing role folder
#
# BEHAVIORAL: Agent spawned with valid type, then role folder deleted.
# Broadcast must NOT crash when assemble_phase_prompt returns None.
# FAILS: No broadcast loop (proven via sub-agent assertion).
# ===========================================================================


async def test_advance_phase_broadcast_handles_missing_role_folder(
    mock_sdk, tmp_path, monkeypatch
) -> None:
    """Broadcast must gracefully skip agents whose role folder was removed after spawn."""
    import shutil

    monkeypatch.chdir(tmp_path)
    _setup_workflow_with_roles(tmp_path)

    from claudechic.mcp import _make_advance_phase, _make_spawn_agent

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

            await app._activate_workflow("test-workflow")
            await pilot.pause()

            # Create a second role folder "reviewer" for proving broadcast works
            reviewer_dir = tmp_path / "workflows" / "test_workflow" / "reviewer"
            reviewer_dir.mkdir()
            (reviewer_dir / "identity.md").write_text(
                "You are the reviewer.", encoding="utf-8"
            )
            (reviewer_dir / "implement.md").write_text(
                "Review the implementation carefully.", encoding="utf-8"
            )

            caller_name = app._agent.name
            spawn_tool = _make_spawn_agent(caller_name=caller_name)

            # Spawn agent with valid type (folder exists at spawn time)
            await spawn_tool.handler(
                {
                    "name": "Skeptic",
                    "path": str(tmp_path),
                    "prompt": "Be the skeptic",
                    "type": "skeptic",
                }
            )
            await pilot.pause()

            # Spawn second typed agent with intact folder
            await spawn_tool.handler(
                {
                    "name": "Reviewer",
                    "path": str(tmp_path),
                    "prompt": "Be the reviewer",
                    "type": "reviewer",
                }
            )
            await pilot.pause()

            skeptic = app.agent_mgr.find_by_name("Skeptic")
            assert skeptic is not None
            skeptic_msgs_before = len([m for m in skeptic.messages if m.role == "user"])

            # DELETE the skeptic role folder AFTER spawn
            # (simulates folder removal -- assemble_phase_prompt returns None)
            skeptic_dir = tmp_path / "workflows" / "test_workflow" / "skeptic"
            shutil.rmtree(skeptic_dir)

            # Advance -- must NOT crash even though skeptic's folder is gone
            advance_tool = _make_advance_phase(caller_name=caller_name)
            result = await advance_tool.handler({})
            await pilot.pause()

            assert "isError" not in result, f"advance_phase crashed: {result}"

            # Prove broadcast exists: reviewer (intact folder) must have
            # received implement-phase content
            reviewer = app.agent_mgr.find_by_name("Reviewer")
            reviewer_msgs = [m for m in reviewer.messages if m.role == "user"]
            has_review_content = any(
                "Review the implementation" in m.content.text for m in reviewer_msgs
            )
            assert has_review_content, (
                "Broadcast loop must exist: Reviewer (intact folder) did not "
                "receive implement-phase agent prompt"
            )

            # Skeptic (deleted folder) should NOT have received broadcast
            skeptic_msgs_after = len([m for m in skeptic.messages if m.role == "user"])
            assert skeptic_msgs_after == skeptic_msgs_before, (
                f"Skeptic received {skeptic_msgs_after - skeptic_msgs_before} "
                "broadcast message(s) but its role folder was deleted. "
                "Broadcast must gracefully skip when assemble_phase_prompt "
                "returns None."
            )


# ===========================================================================
# Test 11: no double agent prompt injection for coordinator
#
# BEHAVIORAL: Coordinator gets agent prompt in the advance_phase tool
# response (inline). It must NOT also receive it via broadcast.
# The tool response must contain the phase content.
# FAILS: No broadcast loop (proven via sub-agent assertion).
# ===========================================================================


async def test_advance_phase_no_double_agent_prompt_for_coordinator(
    mock_sdk, tmp_path, monkeypatch
) -> None:
    """Coordinator must get agent prompt ONLY in tool response, not via broadcast."""
    monkeypatch.chdir(tmp_path)
    _setup_workflow_with_roles(tmp_path)

    from claudechic.mcp import _make_advance_phase, _make_spawn_agent

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

            await app._activate_workflow("test-workflow")
            await pilot.pause()

            caller_name = app._agent.name
            coordinator = app._agent

            spawn_tool = _make_spawn_agent(caller_name=caller_name)
            await spawn_tool.handler(
                {
                    "name": "Skeptic",
                    "path": str(tmp_path),
                    "prompt": "Be the skeptic",
                    "type": "skeptic",
                }
            )
            await pilot.pause()

            coord_msgs_before = len(
                [m for m in coordinator.messages if m.role == "user"]
            )

            advance_tool = _make_advance_phase(caller_name=caller_name)
            result = await advance_tool.handler({})
            await pilot.pause()

            assert "isError" not in result

            # Tool response MUST contain phase content (coordinator's inline path)
            response_text = result["content"][0]["text"]
            assert "Coordinate implementation" in response_text, (
                "advance_phase tool response must include coordinator's "
                f"implement-phase agent prompt. Got: {response_text[:200]}"
            )

            # Prove broadcast exists
            skeptic = app.agent_mgr.find_by_name("Skeptic")
            skeptic_msgs = [m for m in skeptic.messages if m.role == "user"]
            has_implement = any(
                "Review implementation" in m.content.text for m in skeptic_msgs
            )
            assert has_implement, (
                "Broadcast loop must exist: Skeptic did not receive implement-phase "
                "agent prompt"
            )

            # Coordinator must NOT have received broadcast (no double injection)
            coord_msgs_after = len(
                [m for m in coordinator.messages if m.role == "user"]
            )
            assert coord_msgs_after == coord_msgs_before, (
                f"Coordinator received {coord_msgs_after - coord_msgs_before} "
                "broadcast prompt(s). This is double injection -- coordinator "
                "already gets agent prompt in the tool response."
            )


# ===========================================================================
# Test 12: no_close_leadership rule fires via real guardrail pipeline
#
# BEHAVIORAL: Real ManifestLoader loads the REAL project_team.yaml, then
# real hooks + evaluate pipeline checks close_agent is blocked.
# Uses direct hook API because guardrails are attached at SDK options level,
# not at MCP handler level -- the MCP close_agent handler doesn't evaluate
# guardrails; the SDK does via PreToolUse hooks.
# FAILS: Rule doesn't exist in project_team.yaml yet.
# ===========================================================================


async def test_close_leadership_rule_fires_on_coordinator(tmp_path: Path) -> None:
    """no_close_leadership rule must warn-block close_agent from coordinator."""
    from claudechic.guardrails.hits import HitLogger
    from claudechic.guardrails.hooks import create_guardrail_hooks
    from claudechic.workflow_engine import register_default_parsers
    from claudechic.workflow_engine.loader import ManifestLoader

    # Load from the REAL repo manifests — rule must exist in production YAML
    repo_root = Path(__file__).resolve().parents[3]
    global_dir = repo_root / "global"
    workflows_dir = repo_root / "workflows"

    loader = ManifestLoader(global_dir=global_dir, workflows_dir=workflows_dir)
    register_default_parsers(loader)

    load_result = loader.load()
    rule_ids = [r.id for r in load_result.rules]
    assert any("no_close_leadership" in rid for rid in rule_ids), (
        f"no_close_leadership rule not found in loaded rules. "
        f"Add it to workflows/project_team/project_team.yaml. "
        f"Loaded rule IDs: {rule_ids}"
    )

    hit_logger = HitLogger(hits_path=tmp_path / "hits.jsonl")
    hooks = create_guardrail_hooks(
        loader=loader,
        hit_logger=hit_logger,
        agent_role="coordinator",
        get_phase=lambda: "project-team:specification",
        get_active_wf=lambda: "project-team",
    )

    evaluate_fn = hooks["PreToolUse"][0].hooks[0]
    hook_result = await evaluate_fn(
        {"tool_name": "mcp__chic__close_agent", "tool_input": {"name": "SomeAgent"}},
        None,
        None,
    )

    assert hook_result.get("decision") == "block", (
        f"Expected warn-level block for close_agent from coordinator, "
        f"got: {hook_result}"
    )
    assert "no_close_leadership" in hook_result.get("reason", ""), (
        f"Block reason should reference no_close_leadership rule, "
        f"got: {hook_result.get('reason', '')}"
    )


# ===========================================================================
# Test 13: main agent gets main_role for guardrail role filtering
#
# BEHAVIORAL: Real ChatApp, real workflow activation, real guardrail hooks.
# Bug: main agent connects BEFORE workflow activation, so its hooks have
# agent_role=None. Rules with `roles: [coordinator]` skip it. After
# activation, main agent must resolve to main_role from the manifest.
# FAILS: main agent's agent_role is None after workflow activation.
# ===========================================================================


async def test_main_agent_role_resolves_to_main_role(
    mock_sdk, tmp_path, monkeypatch
) -> None:
    """After workflow activation, main agent guardrails must use main_role.

    The main agent connects before the workflow is activated, so its
    guardrail hooks initially have agent_role=None. After activation,
    the main agent IS the coordinator (per main_role in the manifest).
    Rules with roles: [coordinator] must fire for the main agent.
    """
    monkeypatch.chdir(tmp_path)

    # Set up workflow with a coordinator-only rule
    (tmp_path / "global").mkdir(parents=True, exist_ok=True)
    wf_dir = tmp_path / "workflows" / "test_workflow"
    wf_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "workflow_id": "test-workflow",
        "main_role": "coordinator",
        "phases": [
            {"id": "design", "file": "design"},
            {"id": "implement", "file": "implement"},
        ],
        "rules": [
            {
                "id": "prefer_ask_agent",
                "trigger": "PreToolUse/mcp__chic__tell_agent",
                "level": "warn",
                "message": "Coordinator should use ask_agent, not tell_agent.",
                "roles": ["coordinator"],
            }
        ],
    }
    (wf_dir / "test_workflow.yaml").write_text(
        yaml.dump(manifest, default_flow_style=False), encoding="utf-8"
    )

    # Create minimal role folders
    coord_dir = wf_dir / "coordinator"
    coord_dir.mkdir()
    (coord_dir / "identity.md").write_text("You are the coordinator.", encoding="utf-8")
    (coord_dir / "design.md").write_text("Design phase.", encoding="utf-8")

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

            # BEFORE activation: main agent hooks should NOT fire
            # coordinator-only rules (no workflow active)
            pre_hooks = app._merged_hooks(agent_type=None)
            if "PreToolUse" in pre_hooks and pre_hooks["PreToolUse"]:
                for matcher in pre_hooks["PreToolUse"]:
                    for hook_fn in matcher.hooks:
                        pre_result = await hook_fn(
                            {
                                "tool_name": "mcp__chic__tell_agent",
                                "tool_input": {"name": "X", "message": "test"},
                            },
                            None,
                            None,
                        )
                        assert pre_result.get("decision") != "block", (
                            "Rule fired BEFORE workflow activation -- false positive"
                        )

            # Activate workflow
            await app._activate_workflow("test-workflow")
            await pilot.pause()

            # AFTER activation: main agent's hooks must resolve its role
            # to "coordinator" (from main_role in manifest) and fire the
            # coordinator-only rule
            post_hooks = app._merged_hooks(agent_type=None)
            assert "PreToolUse" in post_hooks, (
                "No PreToolUse hooks after workflow activation"
            )

            fired = False
            for matcher in post_hooks["PreToolUse"]:
                for hook_fn in matcher.hooks:
                    post_result = await hook_fn(
                        {
                            "tool_name": "mcp__chic__tell_agent",
                            "tool_input": {"name": "Skeptic", "message": "test"},
                        },
                        None,
                        None,
                    )
                    if post_result.get("decision") == "block":
                        fired = True
                        break

            assert fired, (
                "Rule with roles: [coordinator] did NOT fire for the main agent "
                "after workflow activation. The main agent's guardrail hooks must "
                "resolve agent_role to the workflow's main_role ('coordinator'). "
                "Currently agent_role is None because the agent connected before "
                "the workflow was activated."
            )


# ===========================================================================
# Test 14: create_unconnected() passes agent_type through to Agent
# ===========================================================================


async def test_create_unconnected_passes_agent_type(mock_sdk, tmp_path) -> None:
    """create_unconnected(agent_type=X) must store agent_type on the Agent."""
    app = ChatApp()

    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        agent = app.agent_mgr.create_unconnected(
            name="UncAgent", cwd=tmp_path, agent_type="skeptic", switch_to=False
        )
        assert agent.agent_type == "skeptic", (
            f"create_unconnected() did not pass agent_type through. "
            f"Got: {getattr(agent, 'agent_type', 'MISSING')!r}"
        )


# ===========================================================================
# Test 15: connect_agent() preserves agent_type through SDK connection
# ===========================================================================


async def test_connect_agent_preserves_agent_type(mock_sdk, tmp_path) -> None:
    """Agent.agent_type must survive the connect_agent() SDK connection."""
    app = ChatApp()

    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        agent = app.agent_mgr.create_unconnected(
            name="ConAgent", cwd=tmp_path, agent_type="skeptic", switch_to=False
        )
        assert agent.agent_type == "skeptic"

        await app.agent_mgr.connect_agent(agent)
        await pilot.pause()

        assert agent.agent_type == "skeptic", (
            f"agent_type lost after connect_agent(). "
            f"Got: {getattr(agent, 'agent_type', 'MISSING')!r}"
        )


# ===========================================================================
# Test 16: _reconnect_agent() preserves agent_type
# ===========================================================================


async def test_reconnect_agent_preserves_agent_type(mock_sdk, tmp_path) -> None:
    """agent_type must survive _reconnect_agent() (disconnect + reconnect)."""
    app = ChatApp()

    with ExitStack() as stack:
        stack.enter_context(patch("claudechic.sessions.count_sessions", return_value=1))

        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()

            agent = app.agent_mgr.create_unconnected(
                name="ReconAgent", cwd=tmp_path, agent_type="skeptic", switch_to=False
            )
            await app.agent_mgr.connect_agent(agent)
            await pilot.pause()

            assert agent.agent_type == "skeptic"

            # Simulate reconnect (e.g. after /resume or interrupt recovery)
            agent.session_id = "mock-session-001"
            await app._reconnect_agent(agent, agent.session_id)
            await pilot.pause()

            assert agent.agent_type == "skeptic", (
                f"agent_type lost after _reconnect_agent(). "
                f"Got: {getattr(agent, 'agent_type', 'MISSING')!r}"
            )
