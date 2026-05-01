"""Tests for the ## Constraints block plumbing (Component D).

Covers per TEST_SPECIFICATION.md:
- D1, D3, D5 sites (assemble_constraints_block, assemble_agent_prompt)
- D6 KEYSTONE: _LoaderAdapter().load() == _filter_load_result(...)
- Seam #3 (D-projection / D-render field contract)
- Seam #4 (single composition point: all 5 inject sites route through
  ``assemble_agent_prompt``)
- Silent-regression Scenarios 1, 3, 4
- Per-feature gestalts for D (user-side + agent-side)
"""

from __future__ import annotations

import inspect
import re
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from claudechic.agent import DEFAULT_ROLE
from claudechic.config import ProjectConfig
from claudechic.guardrails.rules import Injection, Rule
from claudechic.workflows.agent_folders import (
    assemble_agent_prompt,
    assemble_constraints_block,
    create_post_compact_hook,
)
from claudechic.workflows.loader import LoadResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _StubLoader:
    """Minimal loader stand-in that returns a fixed ``LoadResult``."""

    def __init__(self, result: LoadResult) -> None:
        self._result = result

    def load(self, **_kwargs):
        return self._result


def _rule(
    *,
    id_: str,
    namespace: str = "global",
    trigger: str = "PreToolUse/Bash",
    enforcement: str = "warn",
    message: str = "",
) -> Rule:
    return Rule(
        id=id_,
        namespace=namespace,
        trigger=[trigger],
        enforcement=enforcement,
        message=message,
    )


def _injection(
    *,
    id_: str,
    namespace: str = "global",
    trigger: str = "PreToolUse/Bash",
) -> Injection:
    return Injection(id=id_, namespace=namespace, trigger=[trigger])


# ---------------------------------------------------------------------------
# D6 KEYSTONE -- _LoaderAdapter().load() == _filter_load_result(...)
# ---------------------------------------------------------------------------


def test_d6_loader_adapter_load_equals_filter_load_result():
    """KEYSTONE: the adapter's ``load()`` returns the same filtered result
    that ``_filter_load_result`` would produce against the same inputs.

    Two variants:
      (a) baseline: no rules disabled.
      (b) disabled-rule variant: ``project_config.disabled_ids`` contains
          ``"global:warn_sudo"`` -- the rule MUST be absent from BOTH sides.
    """
    from claudechic.app import _filter_load_result, _LoaderAdapter

    # Baseline: 3 rules, no disables.
    base_rules = [
        _rule(id_="global:warn_sudo", namespace="global"),
        _rule(id_="global:no_rm_rf", namespace="global"),
        _rule(id_="proj:foo", namespace="proj"),
    ]
    base_result = LoadResult(rules=base_rules)
    fallback_loader = _StubLoader(base_result)

    project_config = ProjectConfig()  # no disabled_ids

    filtered = _filter_load_result(
        fallback_loader.load(),
        project_config,
        user_disabled_workflows=None,
        user_disabled_ids=None,
    )
    adapter = _LoaderAdapter(lambda: filtered, fallback_loader)

    # Algebraic identity: adapter's load() returns the same object as
    # _filter_load_result(...).
    adapter_loaded = adapter.load()
    assert adapter_loaded == filtered
    # All 3 rules survive when nothing is disabled.
    assert {r.id for r in adapter_loaded.rules} == {
        "global:warn_sudo",
        "global:no_rm_rf",
        "proj:foo",
    }

    # ----- Disabled-rule variant -------------------------------------------
    # mock project_config.disabled_ids and config.get("disabled_ids") to
    # inject a tier-prefixed entry like "global:warn_sudo". This is the
    # exact bug class slot 4 was created to kill: the hook layer's
    # filtered view and the registry layer's view drifting on user-disabled
    # rule entries.
    project_config_disabled = ProjectConfig(
        disabled_ids=frozenset({"global:warn_sudo"}),
    )
    filtered_disabled = _filter_load_result(
        fallback_loader.load(),
        project_config_disabled,
        user_disabled_workflows=None,
        user_disabled_ids=None,
    )
    adapter_disabled = _LoaderAdapter(lambda: filtered_disabled, fallback_loader)

    adapter_disabled_loaded = adapter_disabled.load()
    # Algebraic identity holds in the disabled-rule variant too.
    assert adapter_disabled_loaded == filtered_disabled
    # The disabled rule is absent from BOTH sides.
    assert "global:warn_sudo" not in {r.id for r in adapter_disabled_loaded.rules}
    assert "global:warn_sudo" not in {r.id for r in filtered_disabled.rules}
    # Other rules are still present (we only dropped the disabled one).
    assert "global:no_rm_rf" in {r.id for r in adapter_disabled_loaded.rules}
    assert "proj:foo" in {r.id for r in adapter_disabled_loaded.rules}


def test_d6_loader_adapter_falls_back_when_cache_is_none():
    """The adapter falls back to ``fallback_loader.load()`` when the
    cached load result getter returns ``None`` (test/pre-discover path).
    """
    from claudechic.app import _LoaderAdapter

    fallback_result = LoadResult(rules=[_rule(id_="global:foo")])
    fallback_loader = _StubLoader(fallback_result)
    adapter = _LoaderAdapter(lambda: None, fallback_loader)

    loaded = adapter.load()
    assert loaded is fallback_result
    assert {r.id for r in loaded.rules} == {"global:foo"}


# ---------------------------------------------------------------------------
# Scenario 1: Empty-digest sentinel (D3)
# ---------------------------------------------------------------------------


def test_d3_assemble_constraints_block_returns_empty_string_when_digest_empty():
    """``assemble_constraints_block`` returns the empty string -- not a
    placeholder -- when there are no rules and no advance-checks.
    """
    block = assemble_constraints_block(loader=None, role="default", phase=None)
    assert block == ""
    # Specifically NOT a placeholder string.
    assert "Constraints" not in block
    assert "No rules" not in block


def test_d3_assemble_agent_prompt_skips_empty_constraints_block(tmp_path):
    """``assemble_agent_prompt`` short-circuits to ``phase_prompt`` only
    when the constraints block is empty (rather than appending an empty
    section).
    """
    # Set up a workflow_dir with a role folder that has identity.md.
    role_dir = tmp_path / "role"
    role_dir.mkdir()
    (role_dir / "identity.md").write_text("You are role.", encoding="utf-8")

    prompt = assemble_agent_prompt(
        "role",
        None,
        loader=None,  # forces empty constraints block
        workflow_dir=tmp_path,
    )
    assert prompt is not None
    assert prompt.strip() == "You are role."
    # No leading/trailing constraints heading.
    assert "## Constraints" not in prompt


# ---------------------------------------------------------------------------
# Seam #3: D-projection <-> D-render field contract
# ---------------------------------------------------------------------------


def test_d3_assemble_constraints_block_reads_via_getattr_with_defaults(
    monkeypatch,
):
    """A ``compute_digest`` mock returning entries missing optional fields
    (e.g. no ``skip_reason``) does not crash ``assemble_constraints_block``;
    defaults render as empty cells.

    Pins the field-contract: D-render reads via ``getattr(entry, ..., default)``
    so D-projection is free to add/remove optional fields without breaking
    the render path.
    """
    # Entry deliberately missing skip_reason / roles / phases attributes.
    minimal_entry = SimpleNamespace(
        id="global:partial",
        namespace="global",
        kind="rule",
        active=True,
        # NO skip_reason, NO trigger, NO message, NO enforcement.
    )

    def fake_digest(*_args, **_kwargs):
        return [minimal_entry]

    monkeypatch.setattr("claudechic.guardrails.digest.compute_digest", fake_digest)

    # Use a non-None loader so the render path attempts the digest.
    loader = _StubLoader(LoadResult())
    block = assemble_constraints_block(
        loader=loader,
        role="default",
        phase=None,
    )
    # Render does not raise. The id appears, missing fields are blank.
    assert "## Constraints" in block
    assert "global:partial" in block
    assert "### Rules (1 active)" in block

    # include_skipped path also handles missing skip_reason gracefully.
    skipped_entry = SimpleNamespace(
        id="global:skipped",
        namespace="global",
        kind="rule",
        active=False,
        # NO skip_reason -- defaults to "".
    )

    def fake_digest_skipped(*_args, **_kwargs):
        return [skipped_entry]

    monkeypatch.setattr(
        "claudechic.guardrails.digest.compute_digest", fake_digest_skipped
    )
    block_skipped = assemble_constraints_block(
        loader=loader,
        role="default",
        phase=None,
        include_skipped=True,
    )
    assert "## Constraints" in block_skipped
    assert "global:skipped" in block_skipped
    # Skip-reason column header is present (include_skipped=True).
    assert "skip_reason" in block_skipped


# ---------------------------------------------------------------------------
# Seam #4: Single composition point -- all 5 inject sites route through
# ``assemble_agent_prompt`` (lint-style source inspection).
# ---------------------------------------------------------------------------


def test_d5_all_inject_sites_route_through_assemble_agent_prompt():
    """Lint: every D5 prompt-injection site contains a call to
    ``assemble_agent_prompt`` -- not a hand-rolled
    ``f"{phase_prompt}\\n\\n{constraints_block}"`` concat.

    Sites:
      1. ``app.py::_activate_workflow`` (main-agent activation)
      2. ``mcp.py::_make_spawn_agent`` (sub-agent spawn -- inner closure)
      3. ``app.py::_inject_phase_prompt_to_main_agent`` (main-agent advance)
      4. ``mcp.py::_make_advance_phase`` (sub-agent broadcast loop)
      5. ``workflows/agent_folders.py::create_post_compact_hook``
    """
    from claudechic import app as app_mod
    from claudechic import mcp as mcp_mod
    from claudechic.workflows import agent_folders

    sites = {
        "_activate_workflow": app_mod.ChatApp._activate_workflow,
        "_inject_phase_prompt_to_main_agent": (
            app_mod.ChatApp._inject_phase_prompt_to_main_agent
        ),
        "_make_spawn_agent": mcp_mod._make_spawn_agent,
        "_make_advance_phase": mcp_mod._make_advance_phase,
        "create_post_compact_hook": agent_folders.create_post_compact_hook,
    }
    for site_name, fn in sites.items():
        src = inspect.getsource(fn)
        assert "assemble_agent_prompt(" in src, (
            f"Inject site '{site_name}' must call assemble_agent_prompt() -- "
            "the single composition helper. Hand-rolled concats break the "
            "5-site convergence story (Seam #4)."
        )

    # Also enforce: NO hand-rolled f"{phase_prompt}\n\n{constraints_block}"
    # outside ``assemble_agent_prompt`` itself. We grep across the union of
    # all 5 site sources.
    combined = "\n".join(inspect.getsource(fn) for fn in sites.values())
    forbidden = re.compile(r'f["\']\{phase_prompt\}\\n\\n\{constraints_block\}')
    assert not forbidden.search(combined), (
        "Found a hand-rolled f-string concat of phase_prompt + "
        "constraints_block outside assemble_agent_prompt -- this breaks the "
        "single composition point (Seam #4)."
    )


# ---------------------------------------------------------------------------
# Scenario 3: Default-roled agent skip
# ---------------------------------------------------------------------------


def test_d5_default_role_agent_receives_no_constraints_injection():
    """``assemble_agent_prompt(role=DEFAULT_ROLE, phase=None, loader=...)``
    returns ``None`` when there is nothing to inject (no role dir, and the
    loader projects to an empty constraints block).

    Intentional behavior: agents with no role wiring AND nothing to constrain
    them get NO injection. The dead-code guard in the helper -- "phase_prompt
    is None and constraints empty -> return None" -- is live.
    """
    # Empty loader -> empty rules -> empty constraints block -> None.
    loader = _StubLoader(LoadResult())
    result = assemble_agent_prompt(
        DEFAULT_ROLE,
        None,
        loader=loader,
        workflow_dir=None,  # no role dir
    )
    assert result is None


# ---------------------------------------------------------------------------
# Scenario 4: Broadcast site delivers constraints
# ---------------------------------------------------------------------------


def test_d5_broadcast_delivers_constraints_block_to_sub_agents():
    """The broadcast loop in ``mcp._make_advance_phase`` calls
    ``assemble_agent_prompt`` -- the source code of the factory contains
    the broadcast-site call, the call passes the sub-agent's
    ``agent_type`` (not the main role), and the assembled prompt would
    include ``## Constraints`` when rules apply.

    Spy strategy: assert at the source level that the broadcast loop
    references ``assemble_agent_prompt(`` AND that ``assemble_agent_prompt``
    embeds ``## Constraints`` content (verified against a stub loader
    with one global rule). This avoids spinning up the full TUI / SDK.
    """
    from claudechic import mcp as mcp_mod

    src = inspect.getsource(mcp_mod._make_advance_phase)
    assert "assemble_agent_prompt(" in src, (
        "Broadcast site (mcp._make_advance_phase) must call "
        "assemble_agent_prompt() to deliver constraints to typed sub-agents."
    )
    # The broadcast passes the sub-agent's agent_type (live read),
    # not the workflow's main_role.
    assert "agent.agent_type" in src, (
        "Broadcast must read each sub-agent's live agent_type (B4 contract)."
    )

    # End-to-end: assemble_agent_prompt with a loader holding one global
    # rule produces a prompt containing the ## Constraints heading.
    loader = _StubLoader(LoadResult(rules=[_rule(id_="global:warn_sudo")]))
    prompt = assemble_agent_prompt(
        "skeptic",
        None,
        loader=loader,
        workflow_dir=None,  # skeptic has no role dir for this test
        active_workflow="proj",
    )
    # Default-roled global rule with no role restriction applies to
    # 'skeptic' too. The helper returns the constraints block alone.
    assert prompt is not None
    assert "## Constraints" in prompt
    assert "global:warn_sudo" in prompt


# ---------------------------------------------------------------------------
# Per-feature gestalt: USER-side
# ---------------------------------------------------------------------------


def test_d_user_keeps_managing_disables_via_settings_unchanged(tmp_path):
    """User-side gestalt: the disabled_ids surface (the user's mechanism
    for managing which rules apply) is unchanged.

    Pins:
    - ``ProjectConfig.disabled_ids`` is a frozenset[str] field.
    - Adding an entry round-trips through save/load.
    - ``_filter_load_result`` actually drops the disabled rule from the
      LoadResult fed to the registry/digest layers.
    """
    from claudechic.app import _filter_load_result

    # 1. ProjectConfig.disabled_ids round-trips through save/load.
    pc = ProjectConfig(disabled_ids=frozenset({"global:warn_sudo"}))
    pc.save(tmp_path)
    pc_loaded = ProjectConfig.load(tmp_path)
    assert pc_loaded.disabled_ids == frozenset({"global:warn_sudo"})

    # 2. _filter_load_result drops the disabled rule.
    base = LoadResult(
        rules=[
            _rule(id_="global:warn_sudo"),
            _rule(id_="global:no_rm_rf"),
        ]
    )
    filtered = _filter_load_result(
        base,
        pc_loaded,
        user_disabled_workflows=None,
        user_disabled_ids=None,
    )
    assert "global:warn_sudo" not in {r.id for r in filtered.rules}
    assert "global:no_rm_rf" in {r.id for r in filtered.rules}


# ---------------------------------------------------------------------------
# Per-feature gestalt: AGENT-side
# ---------------------------------------------------------------------------


def test_d3_agent_launch_prompt_contains_constraints_block(tmp_path):
    """Agent-side gestalt: an agent's launch prompt -- the output of the
    single composition helper -- contains the verbatim ``## Constraints``
    heading and the ``### Rules (N active)`` sub-heading when at least one
    rule is in scope for the (role, phase).
    """
    # Set up a role dir with identity.md.
    role_dir = tmp_path / "coordinator"
    role_dir.mkdir()
    (role_dir / "identity.md").write_text("You are the coordinator.", encoding="utf-8")

    loader = _StubLoader(
        LoadResult(
            rules=[
                _rule(
                    id_="global:warn_sudo",
                    enforcement="warn",
                    message="Using sudo -- acknowledge if intentional.",
                ),
            ]
        )
    )

    prompt = assemble_agent_prompt(
        "coordinator",
        None,
        loader=loader,
        workflow_dir=tmp_path,
        active_workflow="proj",
    )
    assert prompt is not None
    # Phase-prompt half (identity.md content).
    assert "You are the coordinator." in prompt
    # Constraints half -- locked contract strings.
    assert "## Constraints" in prompt  # exact heading
    assert "### Rules (1 active)" in prompt  # locked "N active" form
    assert "global:warn_sudo" in prompt
    # The composition shape: phase_prompt then constraints (joined by \n\n).
    idx_phase = prompt.find("You are the coordinator.")
    idx_constraints = prompt.find("## Constraints")
    assert 0 <= idx_phase < idx_constraints, (
        "phase_prompt must precede the ## Constraints block in the assembled "
        "launch prompt (composition shape locked by SPEC §4.7)."
    )


# ---------------------------------------------------------------------------
# Additional coverage: D3 + D5 site ergonomics
# ---------------------------------------------------------------------------


def test_d3_assemble_constraints_block_emits_locked_contract_strings():
    """Locked contract strings appear verbatim (per TEST_SPECIFICATION
    "Locked contract strings" table).
    """
    loader = _StubLoader(
        LoadResult(
            rules=[_rule(id_="global:foo", enforcement="warn", message="msg")],
            injections=[_injection(id_="global:bar", namespace="global")],
        )
    )
    block = assemble_constraints_block(loader=loader, role="default", phase=None)
    # Locked headings.
    assert "## Constraints" in block
    assert "### Rules (" in block
    assert "### Advance checks (" in block
    # Trigger format passes through (rendered as the list repr).
    assert "PreToolUse/Bash" in block


def test_d5_post_compact_hook_constructs_with_helper_call(tmp_path):
    """D5 site (post-compact): ``create_post_compact_hook`` registers a
    ``PostCompact`` SDK hook whose body calls ``assemble_agent_prompt``.

    Uses SDK capitalization ``"PostCompact"`` (locked contract string).
    """
    workflow_dir = tmp_path / "wf"
    workflow_dir.mkdir()
    role_dir = workflow_dir / "role"
    role_dir.mkdir()
    (role_dir / "identity.md").write_text("identity", encoding="utf-8")

    engine = MagicMock()
    engine.get_current_phase.return_value = None
    engine.get_artifact_dir.return_value = None
    engine.project_root = None
    engine.loader = None
    engine.workflow_id = "proj"

    hooks = create_post_compact_hook(engine, "role", workflow_dir)
    # SDK capitalization is locked.
    assert "PostCompact" in hooks
    # The factory references the helper -- caught at the source level.
    src = inspect.getsource(create_post_compact_hook)
    assert "assemble_agent_prompt(" in src


# ---------------------------------------------------------------------------
# D-projection guard: disabled rule does NOT appear in the constraints block
# even if the underlying loader still returns it (matches what the hook
# layer fires on).
# ---------------------------------------------------------------------------


def test_d3_disabled_rule_absent_from_constraints_block_even_when_loaded():
    """When ``disabled_rules`` contains a rule id, it must NOT render in
    the ``## Constraints`` block -- mirroring what the hook layer fires on
    (D6 alignment via the merged disabled-rules set).
    """
    loader = _StubLoader(
        LoadResult(
            rules=[
                _rule(id_="global:warn_sudo"),
                _rule(id_="global:no_rm_rf"),
            ]
        )
    )
    block = assemble_constraints_block(
        loader=loader,
        role="default",
        phase=None,
        disabled_rules=frozenset({"global:warn_sudo"}),
    )
    assert "## Constraints" in block
    assert "global:warn_sudo" not in block
    assert "global:no_rm_rf" in block
    # Active count reflects the disabled rule (1 active, not 2).
    assert "### Rules (1 active)" in block


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
