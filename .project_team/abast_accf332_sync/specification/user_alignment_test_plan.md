# User Alignment Test Plan -- testing-specification phase

**Author:** UserAlignment agent
**Date:** 2026-05-01
**Phase:** testing-specification
**Sources of truth:** userprompt.md (verbatim), SPEC.md (locked decisions), specification/user_alignment.md (C1-C8 standing checks), testing/user_alignment.md (testing-vision gestalt grid)

This document translates the two-axis gestalt grid from the testing-vision memo into concrete test specifications: named tests, target files, and precise assertions. For each feature the C8 binding rule applies -- both gestalts must be specified; if one is absent, the absence is stated explicitly.

**Final-report contract:** all six features appear in the user-facing pass/fail report using the user's verbatim feature labels. Where the implementation was reframed (D), the label stays "guardrails UI" with a one-sentence reframed-implementation note. E and F carry the "stowaway -- not user-named" tag.

---

## 1. Six-feature x two-axis table

| Feature (user's label) | Status tag | User-side gestalt test | Agent-side gestalt test |
|------------------------|------------|------------------------|------------------------|
| workflow template variables | user-named | `test_workflow_root_resolves_in_rendered_prompt` | `test_workflow_root_substituted_in_check_params` |
| dynamic roles | user-named | `test_role_flip_no_sdk_reconnect` | `test_agent_type_propagates_to_hook_closure` |
| effort cycling | user-named | `test_effort_cycles_and_persists_across_restart` | `test_effort_reaches_sdk_subprocess_argv` |
| guardrails UI (reframed: agent-aware constraints) | user-named (reframed) | `test_no_guardrails_modal_or_runtime_store` | `test_constraints_block_in_all_four_inject_sites` |
| pytest_needs_timeout warn rule | stowaway | `test_pytest_warn_fires_on_invocation_not_on_grep` | `test_pytest_rule_appears_in_constraints_block` |
| diagnostics-modal absorption | stowaway | `test_unified_info_modal_has_session_jsonl_and_compaction` | (none -- F has no agent-side gestalt per C8) |

---

## 2. Per-feature test specifications

### 2.1 "workflow template variables"

#### User-side gestalt test

**Name:** `test_workflow_root_resolves_in_rendered_prompt`
**File:** `tests/test_workflow_template_vars.py` (new) or `tests/test_agent_folders.py` (existing, extend)
**What it asserts:**

```python
def test_workflow_root_resolves_in_rendered_prompt(tmp_path):
    """${WORKFLOW_ROOT} in a role identity.md is replaced with the
    resolved absolute path by the time the prompt reaches the caller.
    No literal token remains in the output."""
    # Arrange: write identity.md containing the token
    role_dir = tmp_path / "my_workflow" / "coordinator"
    role_dir.mkdir(parents=True)
    (role_dir / "identity.md").write_text(
        "Your workspace is ${WORKFLOW_ROOT}.", encoding="utf-8"
    )
    from claudechic.workflows.agent_folders import assemble_phase_prompt

    # Act
    result = assemble_phase_prompt(
        workflow_dir=tmp_path / "my_workflow",
        role_name="coordinator",
        current_phase=None,
        artifact_dir=None,
        project_root=tmp_path,
    )

    # Assert: resolved path present; token gone
    assert str(tmp_path) in result
    assert "${WORKFLOW_ROOT}" not in result
```

**Why this catches the quiet failure:** a test of `substitute_workflow_root()` alone proves the helper works; this test proves the substitution is applied on the path from YAML through to the output the caller (and thus the agent) receives.

#### Agent-side gestalt test

**Name:** `test_workflow_root_substituted_in_check_params`
**File:** `tests/test_workflow_engine.py` (existing, extend) or `tests/test_workflow_template_vars.py`
**What it asserts:**

```python
async def test_workflow_root_substituted_in_check_params(tmp_path):
    """The engine substitutes ${WORKFLOW_ROOT} in command-output-check
    command params before passing them to the check factory.
    The check's subprocess receives an absolute path, not the token."""
    # Arrange: a CheckDecl with ${WORKFLOW_ROOT} in the command
    from claudechic.workflows.engine import WorkflowEngine
    # ... construct engine with cwd=tmp_path
    # ... construct check_decl with params={"command": "ls ${WORKFLOW_ROOT}"}
    # Act: run _run_single_check (or equivalent)
    # Assert: the command that reaches the subprocess uses str(tmp_path), not the token
    # (mock subprocess to capture argv)
```

**Note:** this verifies A3's `setdefault("cwd", ...)` AND A1's token expansion in check params.

---

### 2.2 "dynamic roles"

#### User-side gestalt test

**Name:** `test_role_flip_no_sdk_reconnect`
**File:** `tests/test_phase_injection.py` (existing) or `tests/test_dynamic_roles.py` (new)
**What it asserts:**

```python
async def test_role_flip_no_sdk_reconnect(monkeypatch, tmp_path):
    """Activating a workflow flips the main agent's role to main_role
    WITHOUT an SDK reconnect. The existing transport reference survives."""
    from claudechic.agent import Agent, DEFAULT_ROLE
    agent = Agent(name="main", cwd=tmp_path)
    initial_client_ref = object()  # sentinel for "connection established"
    agent.client = initial_client_ref

    # Simulate _activate_workflow's B3 mutation
    agent.agent_type = "coordinator"  # what app.py does

    # Assert: role flipped
    assert agent.agent_type == "coordinator"
    # Assert: client reference unchanged (no reconnect)
    assert agent.client is initial_client_ref

    # Simulate deactivation
    agent.agent_type = DEFAULT_ROLE
    assert agent.agent_type == DEFAULT_ROLE
    assert agent.client is initial_client_ref  # still no reconnect
```

For the smoke test, the remote-control path must verify `agent._client` (or equivalent transport reference) is unchanged across `_activate_workflow` -- not just that the attribute mutated.

#### Agent-side gestalt test

**Name:** `test_agent_type_propagates_to_hook_closure`
**File:** `tests/test_phase_injection.py` or `tests/test_dynamic_roles.py`
**What it asserts:**

```python
def test_agent_type_propagates_to_hook_closure(tmp_path):
    """The hook closure's role-resolver reads agent.agent_type live.
    After the role flips mid-session, the NEXT hook fire sees the new role."""
    from claudechic.agent import Agent, DEFAULT_ROLE

    agent = Agent(name="test", cwd=tmp_path)
    assert agent.agent_type == DEFAULT_ROLE

    # Capture the closure
    resolved_roles = []
    closure = lambda: agent.agent_type  # mirrors B4 shape
    resolved_roles.append(closure())

    # Flip role (B3)
    agent.agent_type = "coordinator"
    resolved_roles.append(closure())  # same closure, new value

    assert resolved_roles == [DEFAULT_ROLE, "coordinator"]

    # Additional: CLAUDE_AGENT_ROLE env propagation
    # (verify _make_options emits env["CLAUDE_AGENT_ROLE"] = agent.agent_type)
```

**[WARNING] carry-forward:** B5 (loader rejects `main_role: default`) should also be tested via `test_loader_rejects_default_main_role` -- verify a manifest with `main_role: default` produces a LoadError and `main_role` is set to None.

---

### 2.3 "effort cycling"

**[WARNING] SPEC contract deviation still unresolved:** SPEC C1 Interfaces locks `Literal["low","medium","high"]` (3 values). Implementation ships 4 values ("max" added). User has NOT explicitly ratified. Test plan records both paths:

- If user ratifies 4-value: tests use `("low", "medium", "high", "max")`
- If user reverts to 3-value: tests use `("low", "medium", "high")` and "max" is removed

The snap target is "medium" per SPEC C2 (correctly implemented in EffortLabel; incorrectly documented in agent.py:251 which should be fixed).

#### User-side gestalt test

**Name:** `test_effort_cycles_and_persists_across_restart`
**File:** `tests/test_effort_cycling.py` (new) or `tests/test_widgets.py` (existing)
**What it asserts:**

```python
async def test_effort_snaps_to_medium_on_non_opus(app_pilot):
    """Switching from Opus to Sonnet snaps the effort level from
    'max' to 'medium' -- per SPEC C2 locked value (NOT 'high')."""
    from claudechic.widgets.layout.footer import EffortLabel
    label = EffortLabel("effort: max")
    label._effort = "max"
    label._levels = ("low", "medium", "high", "max")  # Opus levels

    # Switch to Sonnet (non-Opus)
    sonnet_levels = EffortLabel.levels_for_model("claude-sonnet-4-5")
    label.set_available_levels(sonnet_levels)

    # SPEC C2: snap to "medium"
    assert label._effort == "medium", (
        f"Expected 'medium' per SPEC C2 but got '{label._effort}'. "
        "agent.py:251 docstring says 'high' but SPEC says 'medium'."
    )


def test_effort_persists_across_config(tmp_path, monkeypatch):
    """Effort level set via footer click is persisted to
    ~/.claudechic/config.yaml and restored on next startup."""
    import claudechic.config as cfg
    cfg.CONFIG["effort"] = "low"
    cfg.save()
    # Reload
    cfg.CONFIG.clear()
    cfg._load()
    assert cfg.CONFIG.get("effort") == "low"
```

#### Agent-side gestalt test

**Name:** `test_effort_reaches_sdk_subprocess_argv`
**File:** `tests/test_effort_cycling.py` or `tests/test_app_ui.py`
**What it asserts:**

```python
async def test_effort_reaches_sdk_subprocess_argv(monkeypatch, tmp_path):
    """agent.effort is forwarded to ClaudeAgentOptions(effort=...)
    which the SDK transport appends as --effort <level> to subprocess argv."""
    from claudechic.agent import Agent

    captured_options = {}

    def mock_options_factory(**kwargs):
        captured_options.update(kwargs)
        return None  # or a mock

    agent = Agent(name="test", cwd=tmp_path)
    agent.effort = "low"

    # Via the app._make_options path (slot 4 wiring):
    # ClaudeAgentOptions receives effort=agent.effort
    # Verify ClaudeAgentOptions constructor is called with effort="low"
    # (mock ClaudeAgentOptions and assert effort kwarg)
    # This is the testable contract; SDK subprocess behavior is out of scope.
    assert agent.effort == "low"  # at minimum: attribute confirmed
    # Stronger: assert via monkeypatched ClaudeAgentOptions:
    # assert captured_options.get("effort") == "low"
```

**Note on C2/C3 coordination:** tests for the `/settings` knob (C3) should also verify the live re-apply path writes BOTH `footer.effort` AND `agent.effort`.

---

### 2.4 "guardrails UI" (reframed: agent-aware constraints)

**Final-report label:** "guardrails UI" with note: *"Implemented as agent-aware constraints injected into launch prompts and exposed via MCP tools, per user's 2026-04-29 reframing redirect. No modal or footer button."*

#### User-side gestalt test (negative existence + disabled_ids passthrough)

**Name:** `test_no_guardrails_modal_or_runtime_store`
**File:** `tests/test_guardrails_ui_reframe.py` (new)
**What it asserts:**

```python
def test_no_guardrails_modal_in_codebase():
    """Verify the GuardrailsModal class was NOT shipped.
    Per user's reframing: D is agent-aware constraints, not a UI modal."""
    import importlib
    with pytest.raises(ImportError):
        importlib.import_module("claudechic.widgets.modals.guardrails")


def test_no_disabled_rules_runtime_store_on_app(tmp_path):
    """ChatApp must NOT have a _disabled_rules runtime in-memory store.
    Persistent disables use disabled_ids in config (not a runtime toggle)."""
    from claudechic.app import ChatApp
    app = ChatApp.__new__(ChatApp)
    assert not hasattr(app, "_disabled_rules"), (
        "ChatApp has _disabled_rules -- this is the runtime-disable store "
        "the SPEC explicitly rejects. Persistent disables must use disabled_ids."
    )


def test_no_guardrails_label_in_footer():
    """The footer must NOT have a GuardrailsLabel slot."""
    import ast
    import pathlib
    footer_src = pathlib.Path("claudechic/widgets/layout/footer.py").read_text(encoding="utf-8")
    assert "GuardrailsLabel" not in footer_src
```

#### Agent-side gestalt test (the most critical test in the entire plan)

**Name:** `test_constraints_block_in_all_four_inject_sites`
**File:** `tests/test_guardrails_ui_reframe.py` or `tests/test_phase_injection.py`
**What it asserts:**

```python
async def test_constraints_block_present_at_all_inject_sites(monkeypatch, tmp_path):
    """The ## Constraints block must appear in the agent's prompt at
    ALL FOUR inject sites:
    (1) workflow activation kickoff (app.py::_activate_workflow)
    (2) sub-agent spawn (mcp.py::spawn_agent -> assemble_agent_prompt)
    (3) main-agent phase advance (app.py::_inject_phase_prompt_to_main_agent)
    (4) /compact re-injection (agent_folders.py::create_post_compact_hook)
    """
    # For each site: verify the assembled prompt string contains "## Constraints"
    from claudechic.workflows.agent_folders import assemble_agent_prompt
    # ... construct a minimal loader + engine + workflow_dir ...
    # ... with at least one rule scoped to the role ...
    result = assemble_agent_prompt(
        role="coordinator",
        phase="project-team:specification",
        loader=mock_loader,
        workflow_dir=workflow_dir,
        engine=mock_engine,
        active_workflow="project-team",
    )
    assert "## Constraints" in result


def test_disabled_rules_source_of_truth_equivalence(monkeypatch, tmp_path):
    """CRITICAL: The launch-prompt constraints block and the
    mcp__chic__get_applicable_rules response must agree on which rules
    are 'active' when a rule is in disabled_ids.

    This is the slot-4 source-of-truth bug: mcp.py passes
    disabled_rules=None; app.py D5 sites pass _get_disabled_rules().
    A disabled rule must be absent from BOTH outputs, not just one."""
    # Arrange: one rule in rules.yaml + same rule in disabled_ids config
    # Act (path 1): assemble_agent_prompt with disabled_rules={rule.id}
    # Act (path 2): call get_applicable_rules MCP tool
    # Assert: rule absent from BOTH outputs
    # This test WILL FAIL until the mcp.py 3-site fix is applied.
    pass  # implementation left to test author


def test_refresh_policy_equivalence(tmp_path):
    """Spawn / MCP / PostCompact produce same output for same state.
    Verifies SPEC compositional landing condition #2 (refresh policy)."""
    # Arrange: same (role, phase, loader, engine, active_workflow) state
    # Act: call assemble_agent_prompt (spawn/phase-advance), get_applicable_rules (MCP), post-compact hook
    # Assert: all three produce identical ## Constraints sections
    pass
```

---

### 2.5 pytest_needs_timeout warn rule (stowaway -- not user-named)

#### User-side gestalt test (regex correctness)

**Name:** `test_pytest_warn_fires_on_invocation_not_on_grep`
**File:** `tests/test_guardrails_rules.py` (new) or `tests/test_workflow_guardrails.py` (existing)
**What it asserts:**

```python
import re

PATTERN = r"(?:^|[;&|]\s*)(?:(?:python\d?|uv\s+run|poetry\s+run)\s+(?:-m\s+)?)?pytest\b(?!.*--timeout)"


@pytest.mark.parametrize("cmd,should_match", [
    # TRUE positives (must fire)
    ("pytest tests/", True),
    ("uv run pytest tests/", True),
    ("python -m pytest tests/", True),
    ("echo done; pytest tests/foo.py", True),
    # TRUE negatives (must NOT fire)
    ("pytest tests/ --timeout=30", False),
    ("grep -c 'pytest' output.txt", False),
    ("cat pytest_results.log", False),
    ("head pytest.ini", False),
    ("rg 'pytest'", False),
    ("echo 'run pytest for testing'", False),
])
def test_pytest_timeout_rule_regex(cmd, should_match):
    """The pytest_needs_timeout rule must fire on real pytest invocations
    and NOT fire on grep/cat/head or other read-only commands containing
    the literal string 'pytest'."""
    pattern = re.compile(PATTERN, re.MULTILINE)
    matched = bool(pattern.search(cmd))
    assert matched == should_match, (
        f"Pattern {'should' if should_match else 'should NOT'} match {cmd!r}"
    )
```

**[WARNING] Additional test required:** Verify the rule's prescribed fix actually works. Today `--timeout=30` fails because `pytest-timeout` is not in dev deps. Either:
- `test_pytest_timeout_fix_is_satisfiable`: verify `pytest-timeout` is in `pyproject.toml` dependency-groups.dev, OR
- `test_pytest_rule_message_is_actionable`: verify the rule message guides the user to a fix that works in this project

#### Agent-side gestalt test

**Name:** `test_pytest_rule_appears_in_constraints_block`
**File:** `tests/test_guardrails_rules.py`
**What it asserts:**

```python
def test_pytest_rule_appears_in_constraints_block(tmp_path):
    """E (pytest_needs_timeout) + D (constraints block) together:
    the agent's injected ## Constraints block contains the pytest rule.
    This is the tightest cross-feature validation in the plan -- it proves
    E flows into D's projection and the agent learns the rule pre-failure."""
    from claudechic.workflows.agent_folders import assemble_constraints_block
    # Arrange: a loader that returns the global rules.yaml (which includes pytest_needs_timeout)
    # Act: assemble_constraints_block for any role+phase
    block = assemble_constraints_block(loader=real_loader, role="coordinator", phase=None)
    # Assert: the rule appears by id
    assert "pytest_needs_timeout" in block
```

---

### 2.6 diagnostics-modal absorption (stowaway -- not user-named)

**Agent-side gestalt:** NONE explicitly. Per C8: "F has no agent-side gestalt -- it is a user-facing read-only UI consolidation."

#### User-side gestalt test (zero info loss + session_id wiring)

**Name:** `test_unified_info_modal_has_session_jsonl_and_compaction`
**File:** `tests/test_diff_preview.py` (existing modal tests) or `tests/test_computer_info_modal.py` (new)
**What it asserts:**

```python
def test_computer_info_modal_shows_session_info(tmp_path):
    """ComputerInfoModal must show the JSONL path and last compaction
    summary when session_id is supplied -- zero info loss vs deleted
    DiagnosticsModal."""
    import json
    from claudechic.widgets.modals.computer_info import ComputerInfoModal

    # Write a fake JSONL with a compaction summary
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    session_id = "test-session-123"
    jsonl = sessions_dir / f"{session_id}.jsonl"
    jsonl.write_text(
        json.dumps({"isCompactSummary": True, "message": {"content": "Summary here"}}) + "\n",
        encoding="utf-8"
    )

    modal = ComputerInfoModal(cwd=tmp_path, session_id=session_id)
    sections = modal._get_sections()
    titles = [s.title for s in sections]
    contents = {s.title: s.content for s in sections}

    assert "Session JSONL" in titles
    assert "Last Compaction" in titles
    assert str(jsonl) in contents["Session JSONL"]
    assert "Summary here" in contents["Last Compaction"]


def test_on_diagnostics_label_requested_passes_session_id(monkeypatch):
    """REGRESSION TEST: slot 4's call site must forward session_id to
    ComputerInfoModal. Without this, the modal renders '(no active session)'
    -- a feature regression vs the deleted DiagnosticsModal.

    This test currently FAILS (the slot 4 call site only forwards cwd).
    It is the acceptance criterion for the pending 1-line fix in app.py:3866."""
    # Arrange: fake app with an active agent with session_id
    # Monkeypatch ComputerInfoModal to capture kwargs
    captured = {}
    # Act: call on_diagnostics_label_requested
    # Assert: ComputerInfoModal received session_id=agent.session_id
    # EXPECTED TO FAIL until app.py:3866 is fixed
    pass
```

---

## 3. Scope-guard re-verification tests

Per userprompt.md clarification (4): "stay strictly inside the 4-commit cluster. FLAG any other interesting abast commits encountered in passing -- do not chase them."

### 3.1 A2 stayed out (no paths.py / compute_state_dir / workflow_library/)

**Name:** `test_a2_paths_module_absent`
**File:** `tests/test_scope_guard.py` (new)
**What it asserts:**

```python
def test_paths_module_not_imported():
    """A2 (paths.py / compute_state_dir / workflow_library/) was explicitly
    SKIPPED. No such module must exist in the shipped codebase."""
    import importlib
    with pytest.raises(ImportError):
        importlib.import_module("claudechic.workflows.paths")


def test_compute_state_dir_not_in_codebase():
    """compute_state_dir must NOT exist anywhere in the codebase."""
    import subprocess
    import sys
    result = subprocess.run(
        [sys.executable, "-c",
         "import ast, pathlib; "
         "[exit(1) for f in pathlib.Path('claudechic').rglob('*.py') "
         "for n in ast.walk(ast.parse(f.read_text(encoding='utf-8'))) "
         "if isinstance(n, ast.Name) and n.id == 'compute_state_dir']"],
        capture_output=True
    )
    assert result.returncode == 0, "compute_state_dir found in codebase -- A2 leaked"
```

### 3.2 User-named features all present

**Name:** `test_all_user_named_features_shipped`
**File:** `tests/test_scope_guard.py`
**What it asserts:**

```python
def test_feature_a_shipped():
    """A: workflow template variables -- ${WORKFLOW_ROOT} substitution exists."""
    from claudechic.workflows.engine import WORKFLOW_ROOT_TOKEN, substitute_workflow_root
    assert WORKFLOW_ROOT_TOKEN == "${WORKFLOW_ROOT}"


def test_feature_b_shipped():
    """B: dynamic roles -- DEFAULT_ROLE sentinel + agent_type attribute."""
    from claudechic.agent import DEFAULT_ROLE, Agent
    assert DEFAULT_ROLE == "default"
    import pathlib
    a = Agent(name="t", cwd=pathlib.Path("."))
    assert hasattr(a, "agent_type")
    assert a.agent_type == DEFAULT_ROLE


def test_feature_c_shipped():
    """C: effort cycling -- Agent.effort attribute + EffortLabel widget."""
    from claudechic.agent import Agent
    import pathlib
    a = Agent(name="t", cwd=pathlib.Path("."))
    assert hasattr(a, "effort")
    from claudechic.widgets.layout.footer import EffortLabel
    assert hasattr(EffortLabel, "EFFORT_DISPLAY")


def test_feature_d_shipped():
    """D (guardrails UI, reframed): digest.py + MCP tools registered."""
    from claudechic.guardrails.digest import compute_digest, GuardrailEntry
    from claudechic.guardrails.checks_digest import compute_advance_checks_digest
    from claudechic.workflows.agent_folders import assemble_constraints_block


def test_feature_e_shipped():
    """E (stowaway): pytest_needs_timeout rule in global rules.yaml."""
    import pathlib
    rules_yaml = pathlib.Path("claudechic/defaults/global/rules.yaml").read_text(encoding="utf-8")
    assert "pytest_needs_timeout" in rules_yaml
    assert "enforcement: warn" in rules_yaml


def test_feature_f_shipped():
    """F (stowaway): diagnostics.py deleted + ComputerInfoModal enhanced."""
    import pathlib
    assert not pathlib.Path("claudechic/widgets/modals/diagnostics.py").exists()
    from claudechic.widgets.modals.computer_info import ComputerInfoModal
    import inspect
    sig = inspect.signature(ComputerInfoModal.__init__)
    assert "session_id" in sig.parameters
```

### 3.3 No new stowaway beyond E and F

**Name:** `test_no_new_stowaway_modules`
**File:** `tests/test_scope_guard.py`
**What it asserts:**

```python
def test_guardrails_modal_not_shipped():
    """The GuardrailsModal class must NOT exist -- it was explicitly SKIPPED."""
    import importlib
    with pytest.raises(ImportError):
        importlib.import_module("claudechic.widgets.modals.guardrails")


def test_disabled_rules_runtime_store_absent():
    """_disabled_rules runtime in-memory store must NOT exist on ChatApp."""
    from claudechic.app import ChatApp
    app = ChatApp.__new__(ChatApp)
    assert not hasattr(app, "_disabled_rules")
```

---

## 4. Carry-forward open items (sign-off blockers)

The following items prevent honest PASS marks in the user-facing report.
Each must be resolved before testing can exit green:

| # | Item | Test | Status |
|---|------|------|--------|
| 1 | 4 broken tests in test_artifact_dir.py (D4 migration) | `pytest tests/test_artifact_dir.py -k get_phase` -> 4 FAILED | Empirically confirmed |
| 2 | mcp.py disabled_rules source-of-truth (3 sites) | `test_disabled_rules_source_of_truth_equivalence` above | Will FAIL until fixed |
| 3 | ComputerInfoModal session_id not threaded (app.py:3866) | `test_on_diagnostics_label_requested_passes_session_id` above | Will FAIL until fixed |
| 4 | E rule's prescribed fix --timeout=N not satisfiable | `test_pytest_timeout_fix_is_satisfiable` | Will FAIL until pytest-timeout added or message updated |
| 5 | C1 4-value Literal unratified | User decision required | Cannot be tested, only ratified |
| 6 | D4 2-tool design unratified | User decision required | Cannot be tested, only ratified |
| 7 | F 5-label footer unratified | User decision required | Cannot be tested, only ratified |

---

*End of user_alignment_test_plan.md*
