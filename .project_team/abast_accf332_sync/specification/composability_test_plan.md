# Composability Axis -- Concrete Test Plan

**Author:** Composability (Lead Architect)
**Phase:** project-team:testing-specification
**Date:** 2026-05-01
**References:**
- Testing vision: `.project_team/abast_accf332_sync/testing/composability.md`
- Terminology convention: `.project_team/abast_accf332_sync/testing/terminology.md`
- Team testing vision: `.project_team/abast_accf332_sync/testing/TESTING_VISION.md`
- Covers TESTING_VISION architectural gates (criteria 7-10)

For each test this document specifies: canonical name (per terminology.md
`test_<component_letter><sub_unit>_<concept>_<expectation>` convention),
file location, assertion (1-2 sentences), fixtures/setup, and what
regression the test catches.

---

## 0. Document structure

| Section | Content |
|---------|---------|
| 1 | KEYSTONE test (dedicated section) |
| 2 | Six seam-protocol tests (criteria 7) |
| 3 | Crystal-point sweep -- 10 tests (criterion 8) |
| 4 | Axis isolation tests -- one per axis |
| 5 | Composability lint tests (criteria 9-10) |
| 6 | Full test inventory by file |
| 7 | Open-question resolutions |
| 8 | Cross-axis overlaps |
| 9 | Impl-phase-only tests |

Total test count: ~33 tests across 9 files.

---

## 1. KEYSTONE test (dedicated section)

The keystone test pins the four-layer convergence story for Component D.
If this test breaks, all four downstream projections (hook layer,
MCP `get_applicable_rules`, MCP `get_agent_info`, and the injected
`## Constraints` block) silently drift. Every other test in this plan
that relies on "rules are filtered" rides on this test being green.

### `test_d6_loader_adapter_load_equals_filter_load_result`

**File:** `tests/test_constraints_block.py`

**Assertion:**
`_LoaderAdapter(lambda: filtered_result, fallback_loader).load()` returns
the same `rules` and `injections` as `_filter_load_result(raw_loader.load(),
project_config, config)` when given the same inputs and config. The adapter
is an identity function over `_filter_load_result`'s output -- not an
independent filter and not a cache that can hold a stale pre-filter result.

**Fixtures / setup:**
```python
# 1. Build a real loader over a tmp_path rules.yaml with two rules:
#    "no_rm_rf" (not disabled) and "warn_sudo" (to be disabled).
raw_loader = _make_test_loader(tmp_path, rule_ids=["no_rm_rf", "warn_sudo"])

# 2. ProjectConfig that disables "warn_sudo"
project_config = ProjectConfig(disabled_ids=["warn_sudo"])
config = UserConfig()  # default (empty disabled_ids)

# 3. Direct path: call _filter_load_result explicitly
direct_result = _filter_load_result(
    raw_loader.load(), project_config, config
)

# 4. Adapter path: _LoaderAdapter caches the already-filtered result
from claudechic.app import _LoaderAdapter
adapter = _LoaderAdapter(
    get_load_result=lambda: direct_result,
    fallback_loader=raw_loader,
)
adapter_result = adapter.load()

# 5. Assertions -- both paths must agree
assert {r.id for r in adapter_result.rules} == {r.id for r in direct_result.rules}
assert {i.id for i in adapter_result.injections} == {i.id for i in direct_result.injections}

# 6. Specifically: "warn_sudo" must be absent from BOTH
all_rule_ids = {r.id for r in adapter_result.rules}
assert "warn_sudo" not in all_rule_ids
assert "no_rm_rf" in all_rule_ids
```

**Variant -- bare-id vs tier-prefixed disabled entry:**
```python
# ProjectConfig with tier-prefixed entry (the _get_disabled_rules bug class)
project_config_prefixed = ProjectConfig(disabled_ids=["global:warn_sudo"])
direct_prefixed = _filter_load_result(raw_loader.load(), project_config_prefixed, config)
adapter_prefixed = _LoaderAdapter(lambda: direct_prefixed, raw_loader).load()

# Both must exclude "warn_sudo" regardless of prefix form
assert "warn_sudo" not in {r.id for r in adapter_prefixed.rules}
```
This variant pins the `_get_disabled_rules` tier-prefix mismatch (slot 4
SHOULD-FIX 1) and drives the fix if the bug still exists.

**What it catches:**
- D6 source-of-truth regression: any refactor routing the hook layer
  through `self._manifest_loader` directly (bypassing `_LoaderAdapter`)
  restores the original multi-source bug class.
- `_LoaderAdapter.load()` returning stale data (snapshot-binding regression).
- `_filter_load_result` silently stopping to apply disabled-rules filtering.
- Tier-prefixed disabled entries (`"global:warn_sudo"`) not matching bare
  rule ids during membership check.

**Regression mode:**
If D6 is reverted -- e.g. the hook closure is changed to call
`self._manifest_loader.load()` directly -- the adapter result will contain
`warn_sudo` while `direct_result` excludes it. The test breaks loudly on
the `adapter_result.rules` assertion. That is the desired behavior.

---

## 2. Seam-protocol tests (criterion 7)

One test per seam listed in the composability testing-vision memo. Tests
are behavioral or static-lint as appropriate. Each lives in the file for
its PRIMARY component (per terminology.md rule 1.2).

### 2.1 B<->A seam: `test_b4_guardrail_hook_reads_agent_type_live`

**File:** `tests/test_agent_role_identity.py`

**Assertion:**
The guardrail hook closure built by `_guardrail_hooks(agent=agent)` reads
`agent.agent_type` at FIRE time via the lambda. After mutating
`agent.agent_type` without rebuilding the closure, the next hook
invocation sees the new value, not the original.

**Fixtures / setup:**
```python
from claudechic.agent import Agent, DEFAULT_ROLE

agent = Agent(name="a", cwd=tmp_path)
assert agent.agent_type == DEFAULT_ROLE  # starts at "default"

# stub_loader has one rule scoped to roles=["coordinator"]
stub_loader = _make_stub_loader_with_role_rule(role="coordinator", rule_id="coord_only")

# Build the hook closure (extract _guardrail_hooks to a test helper
# or call it via a minimal stub ChatApp)
hook_fn = _build_hook_closure(agent=agent, loader=stub_loader, active_wf="my_wf")

# Fire with role=DEFAULT_ROLE: "coord_only" rule is inactive (role not in list)
result_before = hook_fn(tool_name="Bash", tool_input={"command": "echo hi"})
assert "coord_only" not in _active_rule_ids(result_before)

# Mutate role -- no closure rebuild
agent.agent_type = "coordinator"

# Fire again: the closure must now see "coordinator"
result_after = hook_fn(tool_name="Bash", tool_input={"command": "echo hi"})
assert "coord_only" in _active_rule_ids(result_after)
```

**What it catches:**
Snapshot-binding regression: if a refactor replaces `lambda: agent.agent_type`
with `effective_role = agent.agent_type` (captured once at hook-creation
time), this test fails. Directly guards sub-units B4 and D6.

**Cross-axis overlap:** also TESTING_VISION criterion 2 (mid-session role
flip). See §8.

---

### 2.2 C<->B seam: `test_c1_make_options_reads_effort_and_agent_type_live`

**File:** `tests/test_effort_cycling.py`

**Assertion:**
`_make_options(agent=agent)` reads BOTH `agent.effort` and `agent.agent_type`
at call time. After mutating both attributes, a second call returns options
that reflect the new values without any reconnect or rebuilding the options
factory.

**Fixtures / setup:**
```python
from claudechic.agent import Agent, DEFAULT_ROLE

agent = Agent(name="a", cwd=tmp_path)
agent.effort = "max"
agent.agent_type = "coordinator"

stub_app = _make_minimal_stub_app(tmp_path)  # has _config, _project_config
options1 = stub_app._make_options(agent=agent)

assert options1.effort == "max"
assert options1.env.get("CLAUDE_AGENT_ROLE") == "coordinator"

# Mutate; call again
agent.effort = "low"
agent.agent_type = DEFAULT_ROLE

options2 = stub_app._make_options(agent=agent)
assert options2.effort == "low"
assert options2.env.get("CLAUDE_AGENT_ROLE") == DEFAULT_ROLE
```

**What it catches:**
Divergence between `agent_type=` kwarg (legacy path) and `agent=` (live
read). Also catches effort being baked in at Agent construction rather than
read live. Guards sub-units B4 + C1.

---

### 2.3 D-projection<->D-render seam: `test_d3_assemble_constraints_block_renders_guardrail_entry_fields`

**File:** `tests/test_constraints_block.py`

**Assertion:**
`assemble_constraints_block` reads from the exact fields defined on
`GuardrailEntry`. Renaming any field on `GuardrailEntry` without updating
the renderer causes the corresponding cell in the `## Constraints` table to
go blank (or errors), and this test breaks at the assertion level rather than
silently producing empty output.

**Fixtures / setup:**
```python
from claudechic.guardrails.digest import GuardrailEntry
from claudechic.workflows.agent_folders import assemble_constraints_block
from unittest.mock import patch

known_entry = GuardrailEntry(
    id="no_rm_rf",
    namespace="global",
    kind="rule",
    trigger=["PreToolUse/Bash"],
    enforcement="deny",
    message="Dangerous: rm -rf on absolute path. Request override if intentional.",
    active=True,
    skip_reason="",
    roles=[],
    exclude_roles=[],
    phases=[],
    exclude_phases=[],
)

with patch("claudechic.workflows.agent_folders.compute_digest", return_value=[known_entry]):
    block = assemble_constraints_block(
        loader=stub_loader,
        role="default",
        phase=None,
        engine=None,
        active_workflow=None,
        disabled_rules=frozenset(),
        include_skipped=False,
    )

# Contract strings (per terminology.md §3.2)
assert block.startswith("## Constraints")
assert "### Rules (1 active)" in block
assert "no_rm_rf" in block
assert "deny" in block
assert "PreToolUse/Bash" in block

# Variant: include_skipped=True adds skip_reason column
skipped_entry = GuardrailEntry(
    ...,
    active=False,
    skip_reason="role 'default' not in ['coordinator']",
)
with patch("claudechic.workflows.agent_folders.compute_digest",
           return_value=[known_entry, skipped_entry]):
    block_skipped = assemble_constraints_block(..., include_skipped=True)
assert "not in" in block_skipped or "skip_reason" in block_skipped
```

**What it catches:**
Field-rename regressions on `GuardrailEntry` or `AdvanceCheckEntry` that
cause the renderer to silently produce empty table cells. Guards sub-units
D1 + D2 + D3.

---

### 2.4 D-render<->D-inject seam: `test_d5_single_composition_point_no_hand_rolled_concat`

**File:** `tests/test_composability_lint.py`

**Assertion (static/grep):**
No file in `claudechic/` outside `agent_folders.py` and test files contains
a hand-rolled concatenation of phase prompt and constraints block. The only
legitimate `f"{phase_prompt}\n\n{constraints_block}"` (or equivalent) is
inside `assemble_agent_prompt` in `agent_folders.py`.

**Fixtures / setup:**
```python
import subprocess
from pathlib import Path

repo_root = Path(__file__).parent.parent
claudechic_dir = repo_root / "claudechic"

result = subprocess.run(
    ["grep", "-r", "--include=*.py", "-l",
     r"phase_prompt.*constraints_block\|constraints_block.*phase_prompt"],
    cwd=str(claudechic_dir),
    capture_output=True, text=True,
)
offenders = [
    f for f in result.stdout.strip().splitlines()
    if not f.endswith("agent_folders.py")
]
assert offenders == [], f"Hand-rolled concat found outside agent_folders.py: {offenders}"
```

**What it catches:**
Criterion 9 regression: a future developer adding a 6th inject site may
hand-roll the concat instead of calling `assemble_agent_prompt`. This test
catches it immediately at the grep level.

---

### 2.5 D-mcp<->D-render seam: `test_d4_get_applicable_rules_matches_assemble_constraints_block`

**File:** `tests/test_mcp_agent_info.py`

**Assertion:**
The output of calling `get_applicable_rules` for agent "X" is byte-identical
(modulo trailing whitespace) to `assemble_constraints_block(loader, role_of_X,
phase, ...)` called with the same inputs. The MCP tool is a thin wrapper over
the formatter, not an independent renderer.

**Fixtures / setup:**
```python
from claudechic.workflows.agent_folders import assemble_constraints_block
from unittest.mock import MagicMock

# Stub app with known loader, engine, and one agent with role "coordinator"
stub_loader = _make_stub_loader_with_rule("no_rm_rf")
stub_engine = _make_stub_engine(current_phase="specification")
stub_agent = _make_agent_with_role("coordinator")
stub_app = MagicMock()
stub_app._workflow_engine = stub_engine
stub_app._manifest_loader = stub_loader
stub_app._load_result = _filter_load_result(stub_loader.load(), ProjectConfig(), UserConfig())
stub_app._agents = {"X": stub_agent}
stub_app._active_workflow = "project_team"

# Call the MCP tool
mcp_output = await _invoke_get_applicable_rules(stub_app, "X")

# Call the underlying formatter directly with the same inputs
direct_output = assemble_constraints_block(
    stub_loader,
    role="coordinator",
    phase="specification",
    engine=stub_engine,
    active_workflow="project_team",
    disabled_rules=frozenset(),
    include_skipped=False,
)

assert mcp_output.strip() == direct_output.strip()

# Variant: get_agent_info section 5 must match too
agent_info = await _invoke_get_agent_info(stub_app, "X")
section5 = _extract_markdown_section(agent_info, "## Applicable guardrail rules")
assert section5.strip() == direct_output.strip()
```

**What it catches:**
The slot 3 violation regressing: aggregator re-renders rules in a different
shape than `get_applicable_rules`. Slot 4 fixed it; this test pins the fix.
Guards sub-unit D4.

---

### 2.6 D6 source-of-truth seam: `test_d6_disabled_rule_absent_from_both_hook_and_registry`

**File:** `tests/test_constraints_block.py`

**Assertion:**
When a rule is listed in `disabled_ids`, both the hook layer (via
`_LoaderAdapter`) and the registry layer (via `_filter_load_result`) exclude
that rule from their results. The two layers must produce identical rule sets.

**Fixtures / setup:**
```python
raw_loader = _make_test_loader(tmp_path, rule_ids=["no_rm_rf", "warn_sudo"])
project_config = ProjectConfig(disabled_ids=["warn_sudo"])
config = UserConfig()

# Registry layer (direct _filter_load_result)
filtered = _filter_load_result(raw_loader.load(), project_config, config)
registry_ids = {r.id for r in filtered.rules}
assert "warn_sudo" not in registry_ids

# Hook layer (via adapter)
from claudechic.app import _LoaderAdapter
adapter = _LoaderAdapter(lambda: filtered, fallback_loader=raw_loader)
hook_ids = {r.id for r in adapter.load().rules}
assert "warn_sudo" not in hook_ids

# Both layers identical
assert hook_ids == registry_ids

# Constraints-block projection also excludes the disabled rule
from claudechic.guardrails.digest import compute_digest
digest = compute_digest(
    loader=adapter,
    active_wf=None,
    agent_role="default",
    current_phase=None,
    disabled_rules=frozenset(["warn_sudo"]),
)
active_digest_ids = {e.id for e in digest if e.active}
assert "warn_sudo" not in active_digest_ids
```

**What it catches:**
The three-source-of-truth bug class (slot 4 SHOULD-FIX 2). If any of the
three paths (hook layer, inject sites, MCP tools) re-diverge on which rules
are disabled, this test fails at the root.

---

### 2.7 F seam: `test_f_computer_info_modal_renders_session_jsonl_path`

**File:** `tests/test_computer_info_modal.py`

**Assertion:**
`ComputerInfoModal(cwd=some_dir, session_id=some_uuid)` renders with a
non-empty Session JSONL row and the Last Compaction section does not raise.
Specifically, the `session_id` is visible in the modal's Session section.
This is the "zero info loss" promise of SPEC Component F.

**Fixtures / setup:**
```python
from claudechic.widgets.modals.computer_info import ComputerInfoModal
import uuid

cwd = tmp_path
session_id = str(uuid.uuid4())

modal = ComputerInfoModal(cwd=cwd, session_id=session_id)
sections = modal._build_sections()  # or equivalent internal method

session_section_content = _get_section_text(sections, label="Session")
# The session_id must appear in the session section (not "(no active session)")
assert session_id in session_section_content or "jsonl" in session_section_content.lower()
# The session section must NOT be empty or contain only a placeholder
assert "(no active session)" not in session_section_content
```

**What it catches:**
Slot 5 SHOULD-FIX 2: the app handler calling `ComputerInfoModal(cwd=cwd)`
without forwarding `session_id=agent.session_id`. If the fix is reverted,
Session JSONL shows "(no active session)" and this test fails.

---

## 3. Crystal-point sweep (criterion 8)

Ten representative configurations from the testing-vision memo §3.
Organized as a test class `TestCrystalSweep` for `pytest -k "crystal"` filtering.

**File:** `tests/test_crystal_sweep.py` (NEW)

---

### Crystal point 1: `test_crystal_1_no_workflow_no_constraints_block`

**Configuration:** `(workflow=no, main, high, opus, no_disable, no_compact)`

**Assertion:**
With no workflow active, `assemble_agent_prompt(DEFAULT_ROLE, None, None,
workflow_dir=None, ...)` returns `None` or a prompt without a `## Constraints`
block. The baseline: no workflow means no constraints injection.

**Fixtures:** `tmp_path` only; no stub loader, no engine.

**What it catches:**
Regression where the constraints block is injected even without a workflow,
polluting non-workflow agent prompts with empty or erroneous content.

---

### Crystal point 2: `test_crystal_2_workflow_active_main_agent_has_constraints_block`

**Configuration:** `(workflow=yes, main, high, opus, no_disable, no_compact)`

**Assertion:**
After workflow activation, the assembled main-agent prompt contains
`"## Constraints"` and `"### Rules ("`. D5 inject site 1 (activation) fired.

**Fixtures:**
Stub loader with one global rule; stub engine returning `main_role="coordinator"`;
stub app calling `assemble_agent_prompt` via `_activate_workflow` path.

**What it catches:**
D5 site 1 (activation) silent gap: activation inject site routes around
`assemble_agent_prompt` and returns a prompt without the constraints block.

---

### Crystal point 3: `test_crystal_3_effort_max_reaches_sdk_options`

**Configuration:** `(workflow=yes, main, max, opus, no_disable, no_compact)`

**Assertion:**
`_make_options(agent=agent)` with `agent.effort="max"` returns a
`ClaudeAgentOptions` object with `effort="max"`. The effort attribute flows
through `_make_options` to the SDK options without being truncated or ignored.

**Fixtures:**
`Agent(name="a", cwd=tmp_path)` with `effort="max"` and `agent_type="coordinator"`;
minimal stub app.

**What it catches:**
C1 plumbing gap: `agent.effort` not wired from `Agent` through `_make_options`
to `ClaudeAgentOptions`.

---

### Crystal point 4: `test_crystal_4_non_opus_snaps_effort_to_medium`

**Configuration:** `(workflow=yes, main, max, sonnet, no_disable, no_compact)`

**Assertion:**
After calling `EffortLabel.set_available_levels(("low", "medium", "high"))`
(the non-Opus set, which excludes `"max"`), an `EffortLabel` initialized
with `effort="max"` snaps to `"medium"`. The label renders `"effort: medium"`
(exact contract string, per terminology §3.1).

**Fixtures:**
`EffortLabel` instance initialized with `effort="max"`.

**What it catches:**
Decision 5 regression: if snap target changes from `"medium"` back to
`"high"`, or if `EffortLabel.set_available_levels` fails to snap when the
current level is absent from the new set, this test fails.

---

### Crystal point 5: `test_crystal_5_sub_agent_spawn_has_constraints_block`

**Configuration:** `(workflow=yes, sub-agent, medium, opus, no_disable, no_compact)`

**Assertion:**
The prompt assembled by `assemble_agent_prompt` for a sub-agent spawn with
`agent_type="analyst"` contains `"## Constraints"` and includes the
`analyst`-scoped rule but NOT the `coordinator`-scoped rule. Role scoping
is respected across agent boundaries.

**Fixtures:**
Stub loader with two rules: one scoped to `roles=["coordinator"]`, one scoped
to `roles=["analyst"]`; sub-agent with `agent_type="analyst"`.

**What it catches:**
D5 site 2 (spawn) silent gap; also role-scoping leaking across agents (an
analyst seeing coordinator rules).

---

### Crystal point 6: `test_crystal_6_disabled_rule_absent_from_constraints_block`

**Configuration:** `(workflow=yes, main, high, opus, disable=warn_sudo, no_compact)`

**Assertion:**
The assembled constraints block does NOT contain `"warn_sudo"`. AND
`_LoaderAdapter(...).load()` also excludes `warn_sudo` from its rules.
Both layers agree (D6 crystal point).

**Fixtures:**
Stub loader with `warn_sudo` rule; `ProjectConfig(disabled_ids=["warn_sudo"])`;
stub app.

**What it catches:**
D6 source-of-truth regression returning from disable; also the
`_get_disabled_rules` tier-prefix bug where `"global:warn_sudo"` fails to
match bare id `"warn_sudo"` in `compute_digest`'s membership check.

---

### Crystal point 7: `test_crystal_7_post_compact_role_and_constraints_survive`

**Configuration:** `(workflow=yes, main, high, opus, no_disable, post_compact)`

**Assertion:**
After the PostCompact hook fires, `agent.agent_type` is still `"coordinator"`
(not reset to `DEFAULT_ROLE`). The post-compact inject site (D5 site 5) also
re-injects a prompt containing `"## Constraints"` for the current role.

**Fixtures:**
Stub app with workflow active and `agent.agent_type="coordinator"`;
mock SDK PostCompact callback invocation.

**What it catches:**
B3 not surviving compact (role reset to DEFAULT_ROLE on compact); D5 site 5
(post-compact) silent gap.

---

### Crystal point 8: `test_crystal_8_broadcast_phase_advance_delivers_constraints_to_sub_agents`

**Configuration:** `(workflow=yes, sub-agent on phase-advance, medium, opus, no_disable, no_compact)`

**Assertion:**
When `advance_phase` fires, the broadcast loop (D5 site 4) sends each
non-`DEFAULT_ROLE` sub-agent a prompt containing `"## Constraints"` for the
NEW phase. Agents with `agent_type==DEFAULT_ROLE` are skipped in the
broadcast loop.

**Fixtures:**
Stub app with two agents: main (DEFAULT_ROLE) and sub-agent with
`agent_type="analyst"`; `message_agent` calls captured for inspection.

**What it catches:**
D5 site 4 (broadcast) silent gap. Also tests the `if agent.agent_type ==
DEFAULT_ROLE: continue` guard -- without it, the main agent receives a
duplicate broadcast.

---

### Crystal point 9: `test_crystal_9_deactivate_workflow_reverts_agent_type`

**Configuration:** `(workflow=yes -> deactivate, main, high, opus, no_disable, no_compact)`

**Assertion:**
After `_deactivate_workflow`, `agent.agent_type == DEFAULT_ROLE`. A
subsequent hook fire sees `DEFAULT_ROLE` and does NOT apply the
`coordinator`-scoped rule (which was active before deactivation).

**Fixtures:**
Stub app with workflow active and `agent.agent_type="coordinator"` after
promotion; deactivation call; same hook closure as in test 2.1.

**What it catches:**
B3 demote-on-deactivation not firing, leaving the agent "stuck" with a
workflow role after the workflow ends. B4 lambda picks up the revert without
reconnect.

---

### Crystal point 10: `test_crystal_10_effort_low_footer_label_reflects_low`

**Configuration:** `(workflow=yes, main, low, opus, no_disable, no_compact)`

**Assertion:**
`EffortLabel` initialized with `effort="low"` renders `"effort: low"` (exact
contract string per terminology §3.1). The full cycle
`low -> medium -> high -> max -> low` round-trips through all four values in
order without skipping any level.

**Fixtures:**
`EffortLabel` unit instance with `effort="low"`.

**What it catches:**
Effort cycle skip (`"low"` not in `DEFAULT_LEVELS`); also catches
`EFFORT_DISPLAY` dict missing an entry for any of the four levels.

---

## 4. Axis isolation tests

Each test verifies that an axis is independently testable without the TUI.
If a test in this section requires `ChatApp` to run, that signals a dirty
seam: find the coupling and clean it.

### 4.1 B axis: `test_b2_agent_type_defaults_to_default_role`

**File:** `tests/test_agent_role_identity.py`

**Assertion:**
`Agent(name="a", cwd=tmp_path).agent_type == DEFAULT_ROLE`. No SDK, no app,
no workflow required. Also asserts `DEFAULT_ROLE == "default"` (pinning the
sentinel's value per terminology §3.6).

**Fixtures:** `tmp_path` only.

**What it catches:**
`Agent.__init__` not setting `agent_type`, or setting it to `None` (the
pre-B1 shape that tests should no longer pass).

---

### 4.2 C axis: `test_c2_effort_label_set_available_levels_no_app`

**File:** `tests/test_effort_cycling.py`

**Assertion:**
`EffortLabel` is constructible and `set_available_levels(...)` is callable
without spawning a `ChatApp`. `EffortLabel.levels_for_model("claude-sonnet-4-5")`
returns a tuple that does NOT contain `"max"`.

**Fixtures:** None required.

**What it catches:**
`EffortLabel` importing or initializing Textual app-level state on
construction, making it untestable without a TUI.

---

### 4.3 D-projection isolation: `test_d1_compute_digest_pure_function_no_app`

**File:** `tests/test_constraints_block.py`

**Assertion:**
`compute_digest(stub_loader, "global", "coordinator", "specification", frozenset())`
returns a non-empty `list[GuardrailEntry]` with no `ChatApp`, no SDK, no TUI
in the process. The function is a pure projection over the loader's output.

**Fixtures:** Stub loader with one rule; no `ChatApp` in the test scope.

**What it catches:**
Upward import creep in `guardrails/digest.py` (leaf module violation): any
import of `app.py` or `mcp.py` from within the digest module.

---

### 4.4 D-render isolation: `test_d3_assemble_constraints_block_callable_without_tui`

**File:** `tests/test_constraints_block.py`

**Assertion:**
`assemble_constraints_block(stub_loader, "default", None, engine=None,
active_workflow=None, disabled_rules=frozenset(), include_skipped=False)`
returns a string without error. With `loader=None`, the function returns a
degenerate empty block (not an exception).

**Fixtures:** Stub loader for the non-None case; `None` for the degenerate
case.

**What it catches:**
`assemble_constraints_block` importing `ChatApp` or requiring I/O; also
verifies the function handles `None` inputs gracefully.

---

### 4.5 D-inject isolation: `test_d5_assemble_agent_prompt_callable_without_tui`

**File:** `tests/test_constraints_block.py`

**Assertion:**
`assemble_agent_prompt("coordinator", "specification", stub_loader,
workflow_dir=tmp_path, artifact_dir=None, project_root=tmp_path,
engine=None, active_workflow=None, disabled_rules=frozenset())` returns
a string without error. No SDK, no app, no TUI.

**Fixtures:** `tmp_path`, stub loader with one rule.

**What it catches:**
`assemble_agent_prompt` importing app-level state; also confirms the function
exists and accepts the exact signature the SPEC defines.

---

### 4.6 D-MCP isolation: `test_d4_get_applicable_rules_callable_with_stub_app`

**File:** `tests/test_mcp_agent_info.py`

**Assertion:**
`get_applicable_rules` can be called with a `MagicMock`-shaped `_app` (no
real SDK connect, no live agent). Returns a string starting with
`"## Constraints"` (exact contract string per terminology §3.2).

**Fixtures:**
`MagicMock` for `_app` with `_workflow_engine`, `_manifest_loader`,
`_load_result`, `_project_config`, `_config`, `_agents` attributes populated
from stubs.

**What it catches:**
MCP tool entangled with live SDK or TUI state, making it untestable without
a running application.

---

### 4.7 D6 adapter isolation: `test_d6_loader_adapter_no_app`

**File:** `tests/test_constraints_block.py`

**Assertion:**
`_LoaderAdapter(get_load_result=lambda: stub_result, fallback_loader=stub_loader).load()`
returns `stub_result` without requiring a `ChatApp` in the test scope.

**Fixtures:** `stub_result` (a `LoadResult` with one rule), `stub_loader`
(a `MagicMock` with `.load()` method).

**What it catches:**
`_LoaderAdapter` importing `ChatApp` or requiring app state at construction
or call time.

---

### 4.8 A1 substitution isolation: `test_a1_substitute_workflow_root_pure_function`

**File:** `tests/test_workflow_engine_seam.py` (EXISTING file, new test)

**Assertion:**
`substitute_workflow_root("foo${WORKFLOW_ROOT}/bar", Path("/tmp/proj"))`
returns `"foo/tmp/proj/bar"`. Pure function, no engine, no app.

**Fixtures:** None.

**What it catches:**
`${WORKFLOW_ROOT}` substitution function accidentally importing engine or
app state; also pins the exact token syntax (braced `${WORKFLOW_ROOT}` per
terminology §3.4, not bare `$WORKFLOW_ROOT`).

---

### 4.9 E rule isolation: `test_e_pytest_needs_timeout_warn_rule_exists_and_has_correct_id`

**File:** `tests/test_global_rules.py` (NEW or EXISTING)

**Assertion:**
Loading `defaults/global/rules.yaml` yields a rule with
`id="pytest_needs_timeout"` and `enforcement="warn"`. Its `detect.pattern`
matches `"pytest tests/foo.py"` and does NOT match
`"pytest --timeout=30 tests/foo.py"` or `"grep -c 'pytest' file.py"`.
The rule id and message are the exact contract strings
(`"pytest_needs_timeout"` and `"use --timeout=N (default 30) to avoid hung tests"`).

**Fixtures:**
Load the YAML from `claudechic/defaults/global/rules.yaml`. No app, no SDK.

**What it catches:**
E rule id drift (contract string regression); false-positive on grep/cat
containing the word "pytest"; rule accidentally removed from the global
rules file.

---

### 4.10 F modal isolation: `test_f_computer_info_modal_constructible_no_app`

**File:** `tests/test_computer_info_modal.py`

**Assertion:**
`ComputerInfoModal(cwd=tmp_path, session_id="abc")` is constructible without
a running `App` instance. Its `_build_sections()` method (or equivalent)
returns a collection with at least a "System" section and a "Session"
section.

**Fixtures:** `tmp_path`.

**What it catches:**
Modal entangled with live app state; also the `session_id=` parameter
absence (slot 5 SHOULD-FIX 2 -- if the constructor does not accept
`session_id`, this test fails at instantiation).

---

## 5. Composability lint tests (criteria 9-10)

**File:** `tests/test_composability_lint.py` (NEW)

Static/grep-style assertions that pin the composability invariants from the
testing-vision memo §5. Cheap (no TUI, no SDK imports) and protect against
slow-decay regressions.

### 5.1 `test_lint_no_hand_rolled_phase_constraints_concat`

**Assertion:**
Zero files in `claudechic/` (excluding `agent_folders.py` and test files)
contain a hand-rolled concat of phase prompt and constraints block.

**Pattern searched:**
`r"phase_prompt.*constraints_block|constraints_block.*phase_prompt"` in
`claudechic/**/*.py` minus `agent_folders.py`.

**What it catches:**
Criterion 9 (single-composition-point invariant). A developer adding a
6th inject site who hand-rolls the concat instead of calling
`assemble_agent_prompt`.

---

### 5.2 `test_lint_no_axis_specific_agent_type_branch`

**Assertion:**
Zero occurrences of `if agent.agent_type == "<literal_role>"` (for any
role string other than `DEFAULT_ROLE` comparison) outside resolver/validator
code (`loader.py` and its direct callers).

**Pattern searched:**
`r'if\s+\w+\.agent_type\s*==\s*["\'][a-z_]+'` in `claudechic/**/*.py`
minus `loader.py`.

**What it catches:**
Axis-specific branching smell: role should be a parameter, not a code
switch. A future helper function that hardcodes `"coordinator"` logic
breaks composition.

---

### 5.3 `test_lint_no_loader_adapter_isinstance_check`

**Assertion:**
Zero occurrences of `isinstance(..., _LoaderAdapter)` in `claudechic/guardrails/`.

**Pattern searched:**
`r"isinstance\s*\(.*_LoaderAdapter"` in `claudechic/guardrails/**/*.py`.

**What it catches:**
Duck-type violation: callers must not type-check the adapter. Any
`isinstance` check breaks the duck-type contract and makes it impossible
to substitute a different filtered-loader implementation.

---

### 5.4 `test_lint_no_bare_effort_branch`

**Assertion:**
Zero occurrences of `if effort == "max"` or `if agent.effort == "max"` or
`if self.effort == "max"` outside `widgets/layout/footer.py`.

**Pattern searched:**
`r'if\s+\w*effort\w*\s*==\s*["\']max["\']'` in `claudechic/**/*.py`
minus `widgets/layout/footer.py`.

**What it catches:**
Effort-as-code-switch smell. Only `EffortLabel` has a legitimate reason to
branch on the `"max"` literal (for snap-down). Any other file doing so is
encoding effort semantics outside the designated widget.

---

### 5.5 `test_lint_compute_digest_callers_are_sanctioned` (criterion 10)

**Assertion:**
`compute_digest(` is called only in `claudechic/workflows/agent_folders.py`,
within the four MCP tool functions in `claudechic/mcp.py`, and in test
files. No other callers.

**Implementation:**
```python
result = subprocess.run(
    ["grep", "-r", "--include=*.py", "-l", "compute_digest("],
    cwd=str(claudechic_dir),
    capture_output=True, text=True,
)
callers = [
    f for f in result.stdout.strip().splitlines()
    if not any(f.endswith(allowed) for allowed in SANCTIONED_FILES)
    and "tests/" not in f
]
assert callers == [], f"Unsanctioned compute_digest callers: {callers}"
```

**What it catches:**
Criterion 10 regression. A new caller forking the digest projection outside
the sanctioned paths creates a fifth projection path that can silently
diverge from the canonical four.

---

### 5.6 `test_lint_clean_import` (advisory)

**Assertion:**
`python -c "import claudechic"` exits with code 0 from a clean interpreter.

**Implementation:**
```python
result = subprocess.run(
    ["python", "-c", "import claudechic"],
    capture_output=True, text=True, timeout=30,
)
assert result.returncode == 0, f"Import error: {result.stderr}"
```

**Mark:** `@pytest.mark.slow` -- excluded from fast CI by default.

**What it catches:**
Module-level circular imports introduced during the A-F component additions.
Informational rather than blocking per the testing-vision memo §5.

---

## 6. Full test inventory by file

| File | Status | Tests |
|------|--------|-------|
| `tests/test_agent_role_identity.py` | NEW | `test_b2_agent_type_defaults_to_default_role`, `test_b3_agent_type_promotes_to_main_role_on_activation`, `test_b3_agent_type_reverts_to_default_role_on_deactivation`, `test_b4_guardrail_hook_reads_agent_type_live`, `test_b5_loader_rejects_main_role_default` |
| `tests/test_effort_cycling.py` | NEW | `test_c1_make_options_reads_effort_and_agent_type_live`, `test_c1_effort_passed_to_claude_agent_options`, `test_c2_effort_label_cycles_low_medium_high_max`, `test_c2_effort_snaps_to_medium_on_non_opus_model`, `test_c2_effort_label_set_available_levels_no_app`, `test_c3_effort_persists_to_config_yaml` |
| `tests/test_constraints_block.py` | NEW | `test_d1_compute_digest_pure_function_no_app`, `test_d3_assemble_constraints_block_renders_guardrail_entry_fields`, `test_d3_assemble_constraints_block_callable_without_tui`, `test_d5_assemble_agent_prompt_callable_without_tui`, **`test_d6_loader_adapter_load_equals_filter_load_result` (KEYSTONE)**, `test_d6_disabled_rule_absent_from_both_hook_and_registry`, `test_d6_loader_adapter_no_app` |
| `tests/test_mcp_agent_info.py` | NEW | `test_d4_get_applicable_rules_matches_assemble_constraints_block`, `test_d4_get_agent_info_returns_eight_section_markdown`, `test_d4_get_applicable_rules_callable_with_stub_app` |
| `tests/test_crystal_sweep.py` | NEW | `test_crystal_1_no_workflow_no_constraints_block`, `test_crystal_2_workflow_active_main_agent_has_constraints_block`, `test_crystal_3_effort_max_reaches_sdk_options`, `test_crystal_4_non_opus_snaps_effort_to_medium`, `test_crystal_5_sub_agent_spawn_has_constraints_block`, `test_crystal_6_disabled_rule_absent_from_constraints_block`, `test_crystal_7_post_compact_role_and_constraints_survive`, `test_crystal_8_broadcast_phase_advance_delivers_constraints_to_sub_agents`, `test_crystal_9_deactivate_workflow_reverts_agent_type`, `test_crystal_10_effort_low_footer_label_reflects_low` |
| `tests/test_composability_lint.py` | NEW | `test_lint_no_hand_rolled_phase_constraints_concat`, `test_lint_no_axis_specific_agent_type_branch`, `test_lint_no_loader_adapter_isinstance_check`, `test_lint_no_bare_effort_branch`, `test_lint_compute_digest_callers_are_sanctioned`, `test_lint_clean_import` (advisory) |
| `tests/test_workflow_engine_seam.py` | EXISTING | add `test_a1_substitute_workflow_root_pure_function` |
| `tests/test_global_rules.py` | NEW or EXISTING | `test_e_pytest_needs_timeout_warn_rule_exists_and_has_correct_id` |
| `tests/test_computer_info_modal.py` | NEW | `test_f_computer_info_modal_renders_session_jsonl_path`, `test_f_computer_info_modal_constructible_no_app` |

**Total: approximately 33 composability-axis tests across 9 files.**

---

## 7. Open-question resolutions

From composability testing-vision memo §8:

**Q1 -- What mechanism for "single composition point"?**
Resolved: grep-based test (`test_lint_no_hand_rolled_phase_constraints_concat`,
§5.1). Rationale: AST walk is overkill for a one-pattern invariant; grep
over `*.py` is deterministic and fast. If the pattern list needs to grow,
add more entries to the same test.

**Q2 -- Level of model-string testing for `EffortLabel.levels_for_model`?**
Resolved: pin to specific model id substrings (`"opus"` in name -> includes
`"max"`) as the production code already does. Tests import
`EffortLabel.levels_for_model` and assert on the return value. Crystal point
4 (`test_crystal_4_non_opus_snaps_effort_to_medium`) uses the concrete model
string `"claude-sonnet-4-5"` as a fixture input.

**Q3 -- `_LoaderAdapter` Protocol typing?**
Resolved: add a `LoaderProtocol` Protocol class in `claudechic/guardrails/hooks.py`
(or `claudechic/guardrails/_types.py`) so callers type-check via protocol
structural subtyping, not `isinstance`. Zero behavior change. The lint test
(`test_lint_no_loader_adapter_isinstance_check`, §5.3) pins the no-isinstance
invariant. File as a separate minor PR; not blocking testing-implementation.

**Q4 -- Disabled-rules testing with tier-prefixed entries?**
Resolved: write the test now with the expected behavior (both bare
`"warn_sudo"` and tier-prefixed `"global:warn_sudo"` must cause the rule
to be absent from the filtered result). The keystone test variant (§1) and
crystal point 6 (§3.6) cover this. If the current implementation does not
handle tier-prefixed entries, these tests fail and drive the fix.

**Q5 -- Five-site inject enumeration in tests?**
Resolved: tests enumerate all five sites by name. Crystal points 2, 5, 7, 8
cover sites 1, 2, 5, 4 respectively. Site 3 (phase-advance) is covered by
a dedicated test `test_d5_phase_advance_routes_through_assemble_agent_prompt`
in `tests/test_constraints_block.py` (implied by D-render isolation §4.5).
If a 6th site is added in a future SPEC, the crystal sweep §3 needs updating
-- add a comment in `test_crystal_sweep.py` for this.

**Q6 -- Crystal-point coverage targets?**
Resolved: 10 points as specified (§3). These cover all edge cases: both
extremes of each binary axis (workflow yes/no, opus/non-opus, disable yes/no,
compact yes/no) and all four effort values via the cycle test. Full
parametrized sweep of all 128 combinations may be added as a
`@pytest.mark.slow` parametrized test in a follow-up batch.

---

## 8. Cross-axis overlaps

Tests that span multiple leadership axes. These are the highest-value tests
in the run (TESTING_VISION: "cross-layer divergence is the dominant risk").

| Test | Composability coverage | Other axis overlap |
|------|----------------------|--------------------|
| `test_b4_guardrail_hook_reads_agent_type_live` | B<->A seam (§2.1) | Skeptic criterion 2 (mid-session role flip observable); UserAlignment B agent-side gestalt |
| `test_d6_loader_adapter_load_equals_filter_load_result` (KEYSTONE) | D6 source-of-truth (§1) | Skeptic criterion 10 (cross-layer assertion); UserAlignment D agent-side gestalt |
| `test_d4_get_applicable_rules_matches_assemble_constraints_block` | D-mcp<->D-render seam (§2.5) | UserAlignment "agent sees X" for D; Skeptic divergence scenario (aggregator re-renders) |
| `test_crystal_4_non_opus_snaps_effort_to_medium` | C axis, crystal point 4 | UserAlignment C user-side gestalt; Terminology contract string `"effort: medium"` |
| `test_crystal_8_broadcast_phase_advance_delivers_constraints_to_sub_agents` | D5 broadcast site | Skeptic criterion 3 (all 5 sites fire); Terminology 5-site inject vocabulary |
| `test_e_pytest_needs_timeout_warn_rule_exists_and_has_correct_id` | E axis isolation (§4.9) | Skeptic criterion 4 (false-positive prevention); Terminology contract strings `"pytest_needs_timeout"` and rule message |
| `test_f_computer_info_modal_renders_session_jsonl_path` | F seam (§2.7) | UserAlignment F user-side gestalt; Skeptic criterion 5 (info parity) |
| `test_crystal_2_workflow_active_main_agent_has_constraints_block` | D5 site 1 | Skeptic criterion 3 (D5 sites fire); UserAlignment D agent-side gestalt |

**Recommendation:** Tests with 3+ axis overlaps should be tagged
`@pytest.mark.integration` so the runner can filter to the critical path
without executing the full suite during rapid iteration.

---

## 9. Impl-phase-only tests

The following tests verify implementation-phase structural invariants that
are not behaviorally observable from outside the codebase. They are
composability-axis-specific and unlikely to overlap with functional gates
from other axes.

1. `test_lint_no_hand_rolled_phase_constraints_concat` -- single-composition-point code structure. No user-visible behavior change if violated; only architecture degrades.

2. `test_lint_no_loader_adapter_isinstance_check` -- duck-type discipline in `guardrails/`. No user-visible behavior.

3. `test_lint_compute_digest_callers_are_sanctioned` -- caller-set invariant for `compute_digest`. No user-visible behavior.

4. `test_d6_loader_adapter_no_app` -- unit test of adapter class in isolation. Catches import-level regressions only.

5. `test_a1_substitute_workflow_root_pure_function` -- pure-function unit test verifying one implementation detail that has no user-visible surface beyond correct template substitution.

6. `test_lint_no_axis_specific_agent_type_branch` and `test_lint_no_bare_effort_branch` -- code-structure invariants. No user-visible behavior.

These tests SHOULD be written and committed. They may be de-prioritized if
the full suite is time-constrained, but each protects a structural invariant
that prevents future composability regressions.

---

*End of Composability Axis Concrete Test Plan.*
*This document satisfies the testing-specification gate for the composability axis.*
*Testing-implementation phase picks up here: write the tests specified above,
run the full suite against commit `b106cff`, report results to coordinator.*
