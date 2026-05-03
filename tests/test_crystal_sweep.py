"""10-point integration sweep across the abast_accf332_sync 6-axis configuration space.

Each test exercises a representative point in the cartesian product of:
    workflow active/inactive  x  agent role default/main/typed
    x  effort low/medium/high/max  x  model opus/non-opus
    x  disabled rule yes/no  x  lifecycle stage
        (baseline / spawn / advance / compact / deactivate)

These are integration tests, not unit tests:
    - Real ChatApp wired through Textual's run_test pilot.
    - Real workflow YAML on disk (tmp_path).
    - Real ManifestLoader, real _filter_load_result, real _merged_hooks.
    - Real assemble_agent_prompt / assemble_constraints_block (NEVER mocked
      in the crystal sweep -- the helpers are the contract under test).
    - Real MCP tool handlers (_make_spawn_agent, _make_advance_phase,
      _make_get_applicable_rules).
    - Real ClaudeAgentOptions plumbing through SubprocessCLITransport's
      _build_command (the SDK function that turns options into argv).
The only thing mocked is the SDK client itself, via the conftest mock_sdk
fixture -- the standard pattern for ChatApp integration tests in this repo.
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
from claudechic.config import ProjectConfig
from claudechic.workflows.agent_folders import (
    assemble_agent_prompt,
    assemble_constraints_block,
)

pytestmark = [pytest.mark.asyncio, pytest.mark.timeout(60)]


# ---------------------------------------------------------------------------
# On-disk fixture helpers
# ---------------------------------------------------------------------------


def _setup_workflow_with_constraints(root: Path) -> None:
    """Lay out a workflow with global rules + role folders for crystal-sweep tests.

    Workflow id: cs_workflow (main_role=coordinator).
    Phases: design -> implement.
    Roles:
        - coordinator (identity + design + implement)
        - implementer (identity + design + implement)
    Global rules: warn_sudo, no_rm_rf -- enough for the constraints block to
    be non-empty for any role/phase combination.
    """
    global_dir = root / "global"
    global_dir.mkdir(parents=True, exist_ok=True)
    (global_dir / "rules.yaml").write_text(
        yaml.dump(
            [
                {
                    "id": "no_rm_rf",
                    "trigger": "PreToolUse/Bash",
                    "enforcement": "deny",
                    "detect": {"pattern": r"rm\s+-rf\s+/"},
                    "message": "Dangerous: rm -rf on absolute path.",
                },
                {
                    "id": "warn_sudo",
                    "trigger": "PreToolUse/Bash",
                    "enforcement": "warn",
                    "detect": {"pattern": r"^sudo\s"},
                    "message": "Using sudo -- acknowledge if intentional.",
                },
                # Phase-scoped rule. Required so T3 phase-advance broadcasts
                # carry a non-empty ``constraints_phase`` slice under the
                # new place-axis split (SPEC §3.1 / §3.2.1): at T3 only the
                # phase slice fires; phase-agnostic rules anchor at T1/T2/T4.
                {
                    "id": "implement_phase_rule",
                    "trigger": "PreToolUse/Bash",
                    "enforcement": "log",
                    "detect": {"pattern": r"^touch\s"},
                    "message": "Touch logged during implement phase.",
                    "phases": ["cs_workflow:implement"],
                },
            ]
        ),
        encoding="utf-8",
    )

    wf_dir = root / "workflows" / "cs_workflow"
    wf_dir.mkdir(parents=True, exist_ok=True)
    (wf_dir / "cs_workflow.yaml").write_text(
        yaml.dump(
            {
                "workflow_id": "cs_workflow",
                "main_role": "coordinator",
                "phases": [
                    {"id": "design", "file": "design"},
                    {"id": "implement", "file": "implement"},
                ],
            }
        ),
        encoding="utf-8",
    )

    for role in ("coordinator", "implementer"):
        rd = wf_dir / role
        rd.mkdir()
        (rd / "identity.md").write_text(f"You are the {role}.", encoding="utf-8")
        (rd / "design.md").write_text(f"{role} design phase.", encoding="utf-8")
        (rd / "implement.md").write_text(f"{role} implement phase.", encoding="utf-8")


def _setup_empty_layout(root: Path) -> None:
    """Lay out empty global/ + workflows/ dirs (no rules, no workflows)."""
    (root / "global").mkdir(parents=True, exist_ok=True)
    (root / "workflows").mkdir(parents=True, exist_ok=True)


async def _mock_prompt_chicsession_name(self, workflow_id: str) -> str | None:
    """Skip the interactive chicsession picker in tests."""
    self._chicsession_name = workflow_id
    return workflow_id


def _common_app_patches(stack: ExitStack) -> None:
    """Patches needed for a ChatApp.run_test() under the crystal sweep.

    Note: we deliberately do NOT patch claudechic.tasks.create_safe_task --
    the kickoff prompt and broadcast-loop sends rely on the task running
    so that agent.messages reflects the injected ## Constraints block.
    """
    stack.enter_context(patch("claudechic.sessions.count_sessions", return_value=1))
    stack.enter_context(
        patch.object(ChatApp, "_prompt_chicsession_name", _mock_prompt_chicsession_name)
    )


def _build_argv_for_options(options: Any) -> list[str]:
    """Run the SDK's command builder against a ClaudeAgentOptions instance.

    The crystal_3 / crystal_10 contract is "subprocess argv carries
    --effort <level>". The actual argv assembly lives in the SDK's
    SubprocessCLITransport._build_command. We invoke it directly with a
    dummy CLI path so the test doesn't depend on a real claude binary.
    """
    from claude_agent_sdk._internal.transport.subprocess_cli import (
        SubprocessCLITransport,
    )

    transport = SubprocessCLITransport(prompt="", options=options)
    transport._cli_path = "/dummy/claude"  # bypass _find_cli (no binary on host)
    return transport._build_command()


def _user_messages(agent: Agent) -> list[str]:
    """Return the text content of every user-role message on an agent."""
    return [
        m.content.text
        for m in agent.messages
        if m.role == "user" and hasattr(m.content, "text")
    ]


# ---------------------------------------------------------------------------
# Crystal 1: baseline -- no workflow, no constraints injected
# ---------------------------------------------------------------------------


async def test_crystal_1_baseline_no_workflow_no_constraints_block(
    mock_sdk, tmp_path
) -> None:
    """Default agent + no manifests => assemble_agent_prompt returns None."""
    _setup_empty_layout(tmp_path)
    app = ChatApp()

    with ExitStack() as stack:
        _common_app_patches(stack)
        async with app.run_test(size=(120, 40), notifications=True) as pilot:
            await pilot.pause()
            app._cwd = tmp_path
            app._init_workflow_infrastructure(
                global_dir=tmp_path / "global",
                workflows_dir=tmp_path / "workflows",
            )
            app._project_config = ProjectConfig()
            app._discover_workflows()
            await pilot.pause()

            # Default identity is the DEFAULT_ROLE sentinel, not a workflow role.
            agent = app._agent
            assert agent is not None
            assert agent.agent_type == DEFAULT_ROLE
            assert app._workflow_engine is None

            # No workflow_dir -> no role file. No rules in the loader -> no
            # constraints. The composition helper short-circuits to None.
            result = assemble_agent_prompt(
                DEFAULT_ROLE,
                None,
                app._manifest_loader,
                workflow_dir=None,
                disabled_rules=app._get_disabled_rules(),
            )
            assert result is None, (
                f"baseline assemble_agent_prompt should be None, got: {result!r}"
            )


# ---------------------------------------------------------------------------
# Crystal 2: workflow active -> main agent gets ## Constraints in kickoff
# ---------------------------------------------------------------------------


async def test_crystal_2_workflow_active_main_agent_has_constraints_block(
    mock_sdk, tmp_path
) -> None:
    """After /{wf} activation, the main agent's kickoff prompt embeds ## Constraints."""
    _setup_workflow_with_constraints(tmp_path)
    app = ChatApp()

    with ExitStack() as stack:
        _common_app_patches(stack)
        async with app.run_test(size=(120, 40), notifications=True) as pilot:
            await pilot.pause()
            app._cwd = tmp_path
            app._init_workflow_infrastructure(
                global_dir=tmp_path / "global",
                workflows_dir=tmp_path / "workflows",
            )
            app._project_config = ProjectConfig()
            app._discover_workflows()
            await pilot.pause()

            await app._activate_workflow("cs_workflow")
            await pilot.pause()

            agent = app._agent
            assert agent is not None
            # B3: promotion to the workflow's main_role.
            assert agent.agent_type == "coordinator"

            # The main-agent activation site (D5 #1) routed the kickoff
            # through assemble_agent_prompt. The kickoff lands on the agent
            # as a user message via _send_to_active_agent.
            msgs = _user_messages(agent)
            assert any("## Constraints" in m for m in msgs), (
                "main agent kickoff missing ## Constraints block. "
                f"messages: {[m[:120] for m in msgs]}"
            )
            # And the role+phase identity content from the workflow folder.
            assert any("coordinator" in m.lower() for m in msgs), (
                "main agent kickoff missing role identity content"
            )


# ---------------------------------------------------------------------------
# Crystal 3: effort=max on opus passes through to SDK argv
# ---------------------------------------------------------------------------


async def test_crystal_3_effort_max_on_opus_passes_to_sdk(mock_sdk, tmp_path) -> None:
    """agent.effort='max' + model='opus' -> ClaudeAgentOptions.effort=='max'.

    Verified end-to-end through the SDK's argv builder (the real function
    that turns options into the subprocess command line).
    """
    _setup_empty_layout(tmp_path)
    app = ChatApp()

    with ExitStack() as stack:
        _common_app_patches(stack)
        async with app.run_test(size=(120, 40), notifications=True) as pilot:
            await pilot.pause()
            app._cwd = tmp_path
            app._init_workflow_infrastructure(
                global_dir=tmp_path / "global",
                workflows_dir=tmp_path / "workflows",
            )
            app._project_config = ProjectConfig()
            app._discover_workflows()
            await pilot.pause()

            agent = app._agent
            assert agent is not None
            agent.model = "opus"
            agent.effort = "max"

            options = app._make_options(
                cwd=tmp_path,
                agent_name=agent.name,
                model="opus",
                agent=agent,
            )
            assert options.effort == "max", (
                f"options.effort should be 'max', got {options.effort!r}"
            )
            argv = _build_argv_for_options(options)
            assert "--effort" in argv, f"--effort flag missing from argv: {argv}"
            i = argv.index("--effort")
            assert argv[i + 1] == "max", (
                f"expected ['--effort', 'max'] in argv, got {argv[i : i + 2]}"
            )


# ---------------------------------------------------------------------------
# Crystal 4: model change opus -> sonnet snaps effort=max to medium
# ---------------------------------------------------------------------------


async def test_crystal_4_non_opus_snaps_effort_to_medium(mock_sdk, tmp_path) -> None:
    """Switching model from opus to sonnet snaps an effort=max selection to medium.

    Drives the StatusFooter.watch_model handler -- the user-visible glue
    between model selection and the effort label per SPEC Decision 5.
    """
    _setup_empty_layout(tmp_path)
    app = ChatApp()

    with ExitStack() as stack:
        _common_app_patches(stack)
        async with app.run_test(size=(120, 40), notifications=True) as pilot:
            await pilot.pause()
            app._cwd = tmp_path

            from claudechic.widgets.layout.footer import EffortLabel, StatusFooter

            footer = app.query_one(StatusFooter)
            effort_label = app.query_one("#effort-label", EffortLabel)

            # Opus admits "max"; pre-set state simulates a user who clicked
            # the EffortLabel up to "max" on Opus.
            footer.model = "opus"
            await pilot.pause()
            assert "max" in effort_label._levels, (
                "Opus must include 'max' in cycling levels"
            )
            effort_label.set_effort("max")
            footer.effort = "max"
            agent = app._agent
            if agent is not None:
                agent.effort = "max"
            await pilot.pause()

            # Switch model: sonnet drops "max" from the level set, snap to medium.
            footer.model = "sonnet"
            await pilot.pause()

            assert footer.effort == "medium", (
                f"footer.effort should snap to 'medium' on non-opus, got {footer.effort!r}"
            )
            assert effort_label._effort == "medium", (
                f"effort label should display 'medium', got {effort_label._effort!r}"
            )
            assert "max" not in effort_label._levels, (
                "non-opus model must drop 'max' from the cycling levels"
            )
            # Mirrored into the live Agent for the next _make_options call.
            if agent is not None:
                assert agent.effort == "medium", (
                    f"agent.effort should mirror to 'medium', got {agent.effort!r}"
                )


# ---------------------------------------------------------------------------
# Crystal 5: spawned typed sub-agent receives constraints block
# ---------------------------------------------------------------------------


async def test_crystal_5_sub_agent_spawn_receives_constraints(
    mock_sdk, tmp_path
) -> None:
    """mcp.spawn_agent(type='implementer') -> sub-agent's prompt has ## Constraints."""
    _setup_workflow_with_constraints(tmp_path)
    app = ChatApp()

    with ExitStack() as stack:
        _common_app_patches(stack)
        async with app.run_test(size=(120, 40), notifications=True) as pilot:
            await pilot.pause()
            app._cwd = tmp_path
            app._init_workflow_infrastructure(
                global_dir=tmp_path / "global",
                workflows_dir=tmp_path / "workflows",
            )
            app._project_config = ProjectConfig()
            app._discover_workflows()
            await pilot.pause()

            await app._activate_workflow("cs_workflow")
            await pilot.pause()

            from claudechic.mcp import _make_spawn_agent

            caller_name = app._agent.name
            spawn_tool = _make_spawn_agent(caller_name=caller_name)
            await spawn_tool.handler(
                {
                    "name": "Imp",
                    "path": str(tmp_path),
                    "prompt": "do the thing",
                    "type": "implementer",
                }
            )
            await pilot.pause()

            sub = app.agent_mgr.find_by_name("Imp")
            assert sub is not None, "sub-agent 'Imp' was not registered"
            assert sub.agent_type == "implementer"

            sub_msgs = _user_messages(sub)
            assert any("## Constraints" in m for m in sub_msgs), (
                "spawned sub-agent missing ## Constraints. "
                f"messages: {[m[:120] for m in sub_msgs]}"
            )
            # The role-scoped identity should also be present (D5 site #2
            # routes through assemble_agent_prompt which prepends identity.md).
            assert any("implementer" in m.lower() for m in sub_msgs)


# ---------------------------------------------------------------------------
# Crystal 6: disabled rule absent from BOTH the hook layer and MCP projection
# ---------------------------------------------------------------------------


async def test_crystal_6_disabled_rule_absent_from_hook_and_mcp(
    mock_sdk, tmp_path
) -> None:
    """disabled_ids: ['global:warn_sudo'] removes the rule from hooks AND mcp tool."""
    _setup_workflow_with_constraints(tmp_path)
    app = ChatApp()

    with ExitStack() as stack:
        _common_app_patches(stack)
        async with app.run_test(size=(120, 40), notifications=True) as pilot:
            await pilot.pause()
            app._cwd = tmp_path
            app._init_workflow_infrastructure(
                global_dir=tmp_path / "global",
                workflows_dir=tmp_path / "workflows",
            )
            # Project-tier disable BEFORE _discover_workflows so that
            # _filter_load_result strips the rule from app._load_result.
            app._project_config = ProjectConfig(
                disabled_ids=frozenset({"global:warn_sudo"})
            )
            app._discover_workflows()
            await pilot.pause()

            await app._activate_workflow("cs_workflow")
            await pilot.pause()

            # --- Hook layer: warn_sudo is gone, so 'sudo apt-get update'
            # passes the PreToolUse evaluator (no decision/block tied to that
            # rule). The deny rule no_rm_rf is still present, but the input
            # we fire doesn't trigger it.
            hooks = app._merged_hooks(agent=app._agent)
            assert "PreToolUse" in hooks
            decisions: list[Any] = []
            for matcher in hooks["PreToolUse"]:
                for hook_fn in matcher.hooks:
                    res = await hook_fn(
                        {
                            "tool_name": "Bash",
                            "tool_input": {"command": "sudo apt-get update"},
                        },
                        None,
                        None,
                    )
                    decisions.append(res)
            for res in decisions:
                # A disabled warn rule must not fire as a block reason.
                reason = (res or {}).get("reason", "") or ""
                assert "warn_sudo" not in reason, (
                    f"hook still references disabled rule warn_sudo: {res}"
                )
                assert (
                    "sudo" not in reason.lower()
                    or (res or {}).get("decision") != "block"
                ), f"hook blocked sudo despite disable: {res}"

            # --- MCP projection: get_applicable_rules markdown does not
            # mention warn_sudo. (Seam #5 -- registry layer source-of-truth.)
            from claudechic.mcp import _make_get_applicable_rules

            tool = _make_get_applicable_rules(caller_name=app._agent.name)
            result = await tool.handler({})
            text = result["content"][0]["text"]
            assert "warn_sudo" not in text, (
                f"get_applicable_rules surfaced disabled rule warn_sudo: {text}"
            )
            # ## Constraints should still be present (no_rm_rf is still active).
            assert "## Constraints" in text


# ---------------------------------------------------------------------------
# Crystal 7: post-compact -- role survives, constraints re-injected
# ---------------------------------------------------------------------------


async def test_crystal_7_post_compact_role_survives_and_constraints_reinjected(
    mock_sdk, tmp_path
) -> None:
    """SessionStart(source=compact) hook: agent.agent_type unchanged AND constraints re-injected.

    Per Claude Code hooks docs, ``PostCompact`` is side-effect-only --
    it cannot inject context. Post-compact context is delivered via
    ``SessionStart`` with ``matcher="compact"``.
    """
    _setup_workflow_with_constraints(tmp_path)
    app = ChatApp()

    with ExitStack() as stack:
        _common_app_patches(stack)
        async with app.run_test(size=(120, 40), notifications=True) as pilot:
            await pilot.pause()
            app._cwd = tmp_path
            app._init_workflow_infrastructure(
                global_dir=tmp_path / "global",
                workflows_dir=tmp_path / "workflows",
            )
            app._project_config = ProjectConfig()
            app._discover_workflows()
            await pilot.pause()

            await app._activate_workflow("cs_workflow")
            await pilot.pause()

            agent = app._agent
            assert agent is not None
            assert agent.agent_type == "coordinator"

            # Pull the merged hooks for this agent and locate the
            # SessionStart(matcher=compact) closure registered by
            # create_session_start_compact_hook.
            hooks = app._merged_hooks(agent=agent)
            assert "SessionStart" in hooks, (
                f"SessionStart hook missing from merged hooks; got keys: "
                f"{list(hooks.keys())}"
            )
            # Find the matcher whose source is "compact" (we may have
            # multiple SessionStart matchers if other systems register
            # too -- our compact-only one filters by matcher="compact").
            pc_matcher = next(
                (m for m in hooks["SessionStart"] if m.matcher == "compact"),
                None,
            )
            assert pc_matcher is not None, (
                f"No SessionStart matcher with matcher='compact'; got: "
                f"{[m.matcher for m in hooks['SessionStart']]}"
            )
            pc_hook = pc_matcher.hooks[0]

            # Fire the hook the way the SDK would on /compact.
            payload = await pc_hook({}, None, None)

            # B contract: role survives /compact (no SDK reconnect).
            assert agent.agent_type == "coordinator", (
                f"agent.agent_type lost across post-compact: {agent.agent_type!r}"
            )
            # Re-injected prompt contains ## Constraints. The hook
            # returns ``additionalContext`` under ``hookSpecificOutput``
            # with ``hookEventName: "SessionStart"`` (the documented
            # Claude Code post-compact context-injection channel).
            spec_out = payload.get("hookSpecificOutput", {})
            assert spec_out.get("hookEventName") == "SessionStart", (
                f"Wrong hookEventName: {payload!r}"
            )
            additional = spec_out.get("additionalContext", "")
            assert "## Constraints" in additional, (
                f"post-compact reinjection missing ## Constraints. payload={payload!r}"
            )


# ---------------------------------------------------------------------------
# Crystal 8: phase-advance broadcast delivers constraints to typed sub-agents
# ---------------------------------------------------------------------------


async def test_crystal_8_broadcast_phase_advance_delivers_constraints_to_sub_agents(
    mock_sdk, tmp_path
) -> None:
    """advance_phase broadcast (D5 site #4) delivers ## Constraints to sub-agents."""
    _setup_workflow_with_constraints(tmp_path)
    app = ChatApp()

    with ExitStack() as stack:
        _common_app_patches(stack)
        async with app.run_test(size=(120, 40), notifications=True) as pilot:
            await pilot.pause()
            app._cwd = tmp_path
            app._init_workflow_infrastructure(
                global_dir=tmp_path / "global",
                workflows_dir=tmp_path / "workflows",
            )
            app._project_config = ProjectConfig()
            app._discover_workflows()
            await pilot.pause()

            await app._activate_workflow("cs_workflow")
            await pilot.pause()

            from claudechic.mcp import _make_advance_phase, _make_spawn_agent

            caller_name = app._agent.name
            spawn_tool = _make_spawn_agent(caller_name=caller_name)
            await spawn_tool.handler(
                {
                    "name": "Imp",
                    "path": str(tmp_path),
                    "prompt": "join",
                    "type": "implementer",
                }
            )
            await pilot.pause()

            sub = app.agent_mgr.find_by_name("Imp")
            assert sub is not None
            spawn_msgs = list(_user_messages(sub))

            # Advance design -> implement.
            advance_tool = _make_advance_phase(caller_name=caller_name)
            advance_result = await advance_tool.handler({})
            await pilot.pause()
            assert "isError" not in advance_result, (
                f"advance_phase failed: {advance_result}"
            )

            broadcast_msgs = [m for m in _user_messages(sub) if m not in spawn_msgs]
            assert broadcast_msgs, (
                "broadcast did not deliver any new message to sub-agent"
            )
            assert any("## Constraints" in m for m in broadcast_msgs), (
                "phase-advance broadcast missing ## Constraints. "
                f"new messages: {[m[:120] for m in broadcast_msgs]}"
            )


# ---------------------------------------------------------------------------
# Crystal 9: deactivation reverts agent_type to DEFAULT_ROLE
# ---------------------------------------------------------------------------


async def test_crystal_9_deactivation_reverts_agent_type(mock_sdk, tmp_path) -> None:
    """/{wf} stop reverts the active agent's agent_type to DEFAULT_ROLE."""
    _setup_workflow_with_constraints(tmp_path)
    app = ChatApp()

    with ExitStack() as stack:
        _common_app_patches(stack)
        async with app.run_test(size=(120, 40), notifications=True) as pilot:
            await pilot.pause()
            app._cwd = tmp_path
            app._init_workflow_infrastructure(
                global_dir=tmp_path / "global",
                workflows_dir=tmp_path / "workflows",
            )
            app._project_config = ProjectConfig()
            app._discover_workflows()
            await pilot.pause()

            await app._activate_workflow("cs_workflow")
            await pilot.pause()
            agent = app._agent
            assert agent is not None
            assert agent.agent_type == "coordinator"

            handled = await app._handle_workflow_command("/cs_workflow", "stop")
            await pilot.pause()
            assert handled is True
            assert app._workflow_engine is None
            assert agent.agent_type == DEFAULT_ROLE, (
                f"agent.agent_type should revert to DEFAULT_ROLE on /{{wf}} stop, "
                f"got {agent.agent_type!r}"
            )


# ---------------------------------------------------------------------------
# Crystal 10: effort=low propagates to subprocess argv
# ---------------------------------------------------------------------------


async def test_crystal_10_effort_low_propagates_to_subprocess_argv(
    mock_sdk, tmp_path
) -> None:
    """agent.effort='low' surfaces as ['--effort', 'low'] in the SDK argv."""
    _setup_empty_layout(tmp_path)
    app = ChatApp()

    with ExitStack() as stack:
        _common_app_patches(stack)
        async with app.run_test(size=(120, 40), notifications=True) as pilot:
            await pilot.pause()
            app._cwd = tmp_path
            app._init_workflow_infrastructure(
                global_dir=tmp_path / "global",
                workflows_dir=tmp_path / "workflows",
            )
            app._project_config = ProjectConfig()
            app._discover_workflows()
            await pilot.pause()

            agent = app._agent
            assert agent is not None
            agent.model = "sonnet"
            agent.effort = "low"

            options = app._make_options(
                cwd=tmp_path,
                agent_name=agent.name,
                model="sonnet",
                agent=agent,
            )
            assert options.effort == "low", (
                f"options.effort should be 'low', got {options.effort!r}"
            )

            argv = _build_argv_for_options(options)
            assert "--effort" in argv, f"--effort flag missing from argv: {argv}"
            i = argv.index("--effort")
            assert argv[i + 1] == "low", (
                f"expected ['--effort', 'low'] in argv, got {argv[i : i + 2]}"
            )

            # Sanity: assemble_constraints_block on a default agent + no
            # rules in the test layout returns empty -- crystal_10 stays
            # focused on the SDK-argv propagation, no constraints noise.
            assert (
                assemble_constraints_block(app._manifest_loader, DEFAULT_ROLE, None)
                == ""
            )
