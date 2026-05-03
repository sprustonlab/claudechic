# Test Specification -- abast_accf332_sync

Binding test plan for the agent self-awareness substrate.

---

## Component map

| Letter | Feature | Files most affected |
|---|---|---|
| **A** | workflow template variables: `${WORKFLOW_ROOT}` token + run-time substitution + engine-cwd defaulting + two-pass advance-check executor | `workflows/engine.py`, `workflows/_substitute.py`, `checks/builtins.py` |
| **B** | dynamic roles: `agent.agent_type` runtime self-identity; promote/revert at workflow activation; survives `/compact` | `agent.py`, `agent_manager.py`, `app.py` |
| **C** | effort cycling: `agent.effort: Literal["low","medium","high","max"]`; footer EffortLabel; persistence | `agent.py`, `widgets/layout/footer.py`, `config.py`, `screens/settings.py` |
| **D** | guardrails UI (reframed as agent-aware constraints): digest projection + 4-tool MCP composite + 5-site prompt injection + source-of-truth alignment | `guardrails/digest.py`, `workflows/agent_folders.py`, `mcp.py`, `app.py` |
| **E** | `pytest_needs_timeout` warn rule (stowaway): hardened regex | `defaults/global/rules.yaml` |
| **F** | diagnostics-modal absorption (stowaway): `ComputerInfoModal` absorbs JSONL + last-compaction readers | `widgets/modals/computer_info.py`, `widgets/modals/base.py`, `widgets/modals/__init__.py`, `app.py` |

## The 5 prompt-injection sites (sub-unit D5)

1. activation -- `app.py::_activate_workflow`
2. sub-agent spawn -- `mcp.py::spawn_agent`
3. main-agent phase-advance -- `app.py::_inject_phase_prompt_to_main_agent`
4. sub-agent phase-advance broadcast -- `mcp.py::_make_advance_phase` broadcast loop
5. post-compact -- `workflows/agent_folders.py::create_post_compact_hook`

All 5 route through the single composition helper `assemble_agent_prompt(role, phase, loader, ...)`.

## Test files to create

| File | Scope |
|---|---|
| `tests/test_workflow_template_vars.py` (NEW) | A1 + A4 |
| `tests/test_advance_check_executor.py` (NEW) | A3 + A4 |
| `tests/test_agent_role_identity.py` (NEW) | B1, B2, B3, B4, B5 |
| `tests/test_effort_cycling.py` (NEW) | C1, C2, C3 |
| `tests/test_constraints_block.py` (NEW) | D1, D3, D5 sites, D6 keystone |
| `tests/test_mcp_get_agent_info.py` (NEW) | D4 |
| `tests/test_pytest_needs_timeout_regex.py` (NEW) | E (44-case parameterized) |
| `tests/test_computer_info_modal.py` (NEW) | F |
| `tests/test_crystal_sweep.py` (NEW) | 10-point integration sweep |
| `tests/test_artifact_dir.py` (existing) | D4 caller migration tests already landed |
| `tests/test_widgets.py` (existing) | C2 + F (existing tests already cover) |
| `tests/test_settings_screen.py` (existing) | C3 enum SettingKey |

---

## Keystone test (highest-priority single test)

**File:** `tests/test_constraints_block.py`
**Name:** `test_d6_loader_adapter_load_equals_filter_load_result`

**Assert:**
```
_LoaderAdapter(lambda: app._load_result, fallback_loader).load()
  ==
_filter_load_result(fallback_loader.load(), project_config, config)
```

**Variant:** with `disabled_ids = ["global:warn_sudo"]` in project config -- the disabled rule is absent from BOTH sides.

**Fixtures:** mock `app._load_result` and `fallback_loader`; mock `project_config.disabled_ids` and `config.get("disabled_ids")`.

**Catches:** drift between hook layer's filtered view and the registry layer's view -- the bug class slot 4 declared dead.

---

## Seam-protocol tests

### 1. B<->A: workflow engine reads live `agent.agent_type` via closure
**File:** `tests/test_agent_role_identity.py`
**Name:** `test_b4_guardrail_hook_closure_binds_agent_not_main_role`
**Assert:** `_guardrail_hooks(agent=mock_agent)` returns hooks whose role-resolver function returns `mock_agent.agent_type` LIVE; mutating `mock_agent.agent_type` between hook-construction and hook-fire reflects the new value.

### 2. C<->B: both flow through `_make_options(agent=)`
**File:** `tests/test_agent_role_identity.py`
**Name:** `test_b4_make_options_reads_live_agent_type_and_effort`
**Assert:** `_make_options(agent=mock_agent)` reads `mock_agent.agent_type` for `CLAUDE_AGENT_ROLE` env AND `mock_agent.effort` for `ClaudeAgentOptions(effort=...)`. Mutating either between `_make_options` calls reflects in next call's output.

### 3. D-projection <-> D-render: field contract
**File:** `tests/test_constraints_block.py`
**Name:** `test_d3_assemble_constraints_block_reads_via_getattr_with_defaults`
**Assert:** A `compute_digest` mock returning entries missing optional fields (e.g. no `skip_reason`) does not crash `assemble_constraints_block`; defaults render as empty cells.

### 4. D-render <-> D-inject: single composition point
**File:** `tests/test_constraints_block.py`
**Name:** `test_d5_all_inject_sites_route_through_assemble_agent_prompt`
**Assert:** Spy on `assemble_agent_prompt` and verify each of the 5 inject sites calls it (not a hand-rolled concat). Sites: `_activate_workflow`, `mcp.spawn_agent`, `_inject_phase_prompt_to_main_agent`, `mcp._make_advance_phase` broadcast loop, `create_post_compact_hook`.

### 5. D-mcp <-> D-render: byte-identical output
**File:** `tests/test_mcp_get_agent_info.py`
**Name:** `test_d4_get_applicable_rules_matches_assemble_constraints_block`
**Assert:** For the same `(role, phase)`, `mcp__chic__get_applicable_rules(...)` returns markdown that contains the same content as a direct call to `assemble_constraints_block(...)`.

### 6. F seam: modal session-id wiring
**File:** `tests/test_computer_info_modal.py`
**Name:** `test_f_on_diagnostics_label_requested_forwards_session_id`
**Assert:** Triggering `on_diagnostics_label_requested` constructs `ComputerInfoModal(cwd=..., session_id=agent.session_id)`; modal renders the actual JSONL path, not "(no active session)".

---

## 10-point crystal sweep

**File:** `tests/test_crystal_sweep.py`
**Naming pattern:** `test_crystal_<n>_<config>`

| # | Test name | Configuration |
|---|---|---|
| 1 | `test_crystal_1_baseline_no_workflow_no_constraints_block` | No workflow active; `agent.agent_type == DEFAULT_ROLE`; `assemble_agent_prompt` returns `None` (no constraints block injected) |
| 2 | `test_crystal_2_workflow_active_main_agent_has_constraints_block` | Workflow active; main agent receives `## Constraints` at activation |
| 3 | `test_crystal_3_effort_max_on_opus_passes_to_sdk` | `model="opus"`; `agent.effort="max"`; `ClaudeAgentOptions(effort="max")` accepted |
| 4 | `test_crystal_4_non_opus_snaps_effort_to_medium` | Model change opus -> sonnet with `agent.effort="max"` snaps to `"medium"`; footer reactive updated |
| 5 | `test_crystal_5_sub_agent_spawn_receives_constraints` | Sub-agent spawned via `mcp.spawn_agent(type="implementer")` receives constraints block |
| 6 | `test_crystal_6_disabled_rule_absent_from_hook_and_mcp` | `disabled_ids: ["global:warn_sudo"]`; rule absent from both hook fires AND MCP `get_applicable_rules` |
| 7 | `test_crystal_7_post_compact_role_survives_and_constraints_reinjected` | Workflow active -> `/compact` -> `agent.agent_type` preserved; constraints block re-injected |
| 8 | `test_crystal_8_broadcast_phase_advance_delivers_constraints_to_sub_agents` | Typed sub-agents receive constraints block when main agent advances phase |
| 9 | `test_crystal_9_deactivation_reverts_agent_type` | Workflow deactivated -> `agent.agent_type == DEFAULT_ROLE` |
| 10 | `test_crystal_10_effort_low_propagates_to_subprocess_argv` | `agent.effort="low"`; subprocess argv contains `--effort low` |

---

## Silent-regression scenarios

### Scenario 1: Empty-digest sentinel
**File:** `tests/test_constraints_block.py`
**Names:**
- `test_d3_assemble_constraints_block_returns_empty_string_when_digest_empty`
- `test_d3_assemble_agent_prompt_skips_empty_constraints_block`

**Assert:** `assemble_constraints_block(loader=None, role="default", phase=None)` returns `""` (not the placeholder text). `assemble_agent_prompt` short-circuits to `phase_prompt` only when `constraints_block` is empty.

### Scenario 2: B5 case-insensitive rejection
**File:** `tests/test_agent_role_identity.py`
**Name:** `test_b5_main_role_rejects_case_variants_of_default`
**Parametrize over:** `["Default", "DEFAULT", " default ", "default\n", "dEfAuLt", "\tdefault"]`
**Assert:** All 6 raise `LoadError` with message referencing `main_role`.

### Scenario 3: Default-roled agent skip
**File:** `tests/test_constraints_block.py`
**Name:** `test_d5_default_role_agent_receives_no_constraints_injection`
**Assert:** `assemble_agent_prompt(role=DEFAULT_ROLE, phase=None, loader=...)` returns `None` (no injection); intentional behavior.

### Scenario 4: Broadcast site delivers constraints
**File:** `tests/test_constraints_block.py`
**Name:** `test_d5_broadcast_delivers_constraints_block_to_sub_agents`
**Assert:** Spy on `assemble_agent_prompt` in `mcp.py::_make_advance_phase` broadcast loop. With 1+ typed sub-agent active and a phase-advance, `assemble_agent_prompt.call_count >= 1` and the prompt sent to each sub-agent contains `## Constraints`.

(The mid-session role-flip closure-binding scenario lives as Seam #1 above. The cross-layer source-of-truth scenario is the keystone test above. The regex coverage scenario is the 44-case test below.)

---

## 44-case regex test (Component E)

**File:** `tests/test_pytest_needs_timeout_regex.py` (NEW)

**Setup:** Read the regex from `claudechic/defaults/global/rules.yaml` at runtime (do NOT redefine in the test file). The test fails if the rule is missing or the regex changes without updating the case list.

**Test name:** `test_e_pytest_needs_timeout_regex` (parameterized)

**Parameters (44 cases, 3 categories):**

**MUST_MATCH (23):**
- `pytest`
- `pytest tests/foo.py`
- `pytest -v`
- `pytest -k foo`
- `python -m pytest`
- `python3 -m pytest`
- `python3.11 -m pytest`
- `python3.12 -m pytest -v`
- `uv run pytest`
- `uv run pytest tests/`
- `uvx pytest tests/`
- `poetry run pytest`
- `cd subdir && pytest`
- `cd subdir; pytest`
- `( cd subdir && pytest )`
- `time pytest`
- `ENV=1 pytest`
- `xargs pytest`
- `make pytest`
- `hatch run pytest`
- `nox -s pytest`
- `pytest --timeout-method=signal`  (not a timeout value; warn fires)
- `pytest --timeoutblahblah=30`     (not exact --timeout; warn fires)

**MUST_NOT_MATCH (19):**
- `pytest --timeout=30`
- `pytest -v --timeout=10`
- `uv run pytest --timeout=5`
- `python -m pytest --timeout=30 -v`
- `pytest --timeout=30 tests/`
- `grep pytest .`
- `grep -c "pytest"`
- `grep -rn pytest claudechic/`
- `rg pytest`
- `rg -n pytest claudechic/`
- `cat docs/pytest.md`
- `head pytest_log.txt`
- `tail -n 100 pytest_log.txt`
- `# run pytest later`
- `echo "pytest"`
- `ls pytest_helpers/`
- `pytester`         (word-boundary check)
- `pytest_log.txt`   (word-boundary check on `pytest_log` fragment)
- `find . -name pytest_helper.py`

**KNOWN_LIMIT (2, marked xfail; structurally hard):**
- `bash -c "pytest"`                 (quote char not in leading anchor `[;&|]`; widening risks false-positives on grep "pytest")
- `pytest && pytest --timeout=30`    (whole-line lookahead; second invocation's --timeout suppresses warn for first)

---

## Manual smoke check (live remote-control)

NOT a pytest test. Runs against a live claudechic instance via the HTTP API at `localhost:9999`.

**Procedure:**
```
1. Start: ./scripts/claudechic-remote 9999
2. POST /message: "/project_team"
3. POST /message: "call mcp__chic__get_agent_info"
   ASSERT: response markdown ## Identity contains the workflow's main_role (NOT "default")
4. POST /message: "/project_team close"
5. POST /message: "call mcp__chic__get_agent_info"
   ASSERT: response markdown ## Identity shows agent_type: default
6. POST /message: "/compact"
7. POST /message: "call mcp__chic__get_agent_info"
   ASSERT: response markdown ## Identity shows agent_type: default (unchanged from step 5)
```

**Capture:** save the response markdown from steps 3, 5, 7 to a log file; attach to sign-off.

---

## Per-feature gestalt tests

| Feature | Test file | User-side gestalt | Agent-side gestalt |
|---|---|---|---|
| A | `tests/test_workflow_template_vars.py` | `test_a1_workflow_yaml_workflow_root_resolved_in_check_command` | `test_a1_assembled_agent_prompt_substitutes_workflow_root` |
| B | `tests/test_agent_role_identity.py` | `test_b3_workflow_activation_promotes_agent_no_sdk_reconnect` | `test_b3_agent_can_query_own_role_via_get_agent_info` |
| C | `tests/test_effort_cycling.py` | `test_c2_clicking_effort_label_cycles_visible_text` | `test_c1_effort_propagates_to_subprocess_argv_effort_flag` |
| D | `tests/test_constraints_block.py` | `test_d_user_keeps_managing_disables_via_settings_unchanged` | `test_d3_agent_launch_prompt_contains_constraints_block` |
| E | `tests/test_pytest_needs_timeout_regex.py` | `test_e_warn_channel_surfaces_pytest_timeout_nudge` | `test_e_constraints_block_lists_pytest_needs_timeout_rule` |
| F | `tests/test_computer_info_modal.py` | `test_f_info_button_shows_session_jsonl_in_unified_modal` | (none -- read-only viewer) |

---

## Scope-guard tests

**File:** `tests/test_scope_guard.py` (NEW)

| Test | Assert |
|---|---|
| `test_a2_paths_module_absent` | `import claudechic.paths` raises `ImportError`; `compute_state_dir` is not importable |
| `test_no_guardrails_modal_shipped` | `claudechic/widgets/modals/guardrails.py` does not exist; no `_disabled_rules` attribute on `ChatApp`; no `GuardrailsLabel` in `widgets.layout` |
| `test_no_diagnostics_module_shipped` | `claudechic/widgets/modals/diagnostics.py` does not exist; `from claudechic.widgets.modals import DiagnosticsModal` raises `ImportError` |
| `test_all_user_named_features_shipped` | 6 sub-tests: `Agent.agent_type` exists, `Agent.effort` exists, `EffortLabel` importable, `compute_digest` importable, `pytest_needs_timeout` rule loadable, `ComputerInfoModal` importable |

---

## Locked contract strings (assert verbatim)

Tests must assert these strings exactly, not paraphrased.

| String | Context |
|---|---|
| `"effort: low"` / `"effort: medium"` / `"effort: high"` / `"effort: max"` | EffortLabel display |
| `"## Constraints"` | constraints block heading |
| `"### Rules ("` | rules sub-heading prefix; full form `"### Rules (N active)"` |
| `"### Advance checks ("` | advance-checks sub-heading prefix |
| `"## Identity"` | get_agent_info |
| `"## Session"` | get_agent_info |
| `"## Active workflow + phase"` | get_agent_info |
| `"## Applicable guardrail rules"` | get_agent_info |
| `"## Applicable injections"` | get_agent_info |
| `"## Advance checks for the current phase"` | get_agent_info |
| `"## Loader errors"` | get_agent_info |
| `"CLAUDE_AGENT_ROLE"` | env var name |
| `"CLAUDE_AGENT_NAME"` | env var name |
| `"CLAUDECHIC_APP_PID"` | env var name |
| `"${WORKFLOW_ROOT}"` | yaml token (braced; NOT bare `$WORKFLOW_ROOT`) |
| `"${CLAUDECHIC_ARTIFACT_DIR}"` | yaml token |
| `"mcp__chic__whoami"` | MCP tool name |
| `"mcp__chic__get_phase"` | MCP tool name |
| `"mcp__chic__get_applicable_rules"` | MCP tool name |
| `"mcp__chic__get_agent_info"` | MCP tool name |
| `"pytest_needs_timeout"` | rule id |
| `"use --timeout=N (default 30) to avoid hung tests"` | rule message verbatim (lowercase, no terminal period) |
| `"PostCompact"` | SDK hook event key (match SDK capitalization) |
| `DEFAULT_ROLE == "default"` | import the constant; never compare to literal `"default"` directly |

---

## Test naming convention

Pattern: `test_<component_letter><sub_unit_digit>_<concept>_<expectation>`

Examples:
- `test_b3_agent_type_promotes_to_main_role_on_activation`
- `test_d5_broadcast_delivers_constraints_block_to_sub_agents`
- `test_c2_effort_snaps_to_medium_on_non_opus_model`

`pytest -k "b3_"` finds all B3 tests; `pytest -k "test_d5_activation_site"` finds a single inject-site test.

Forbidden synonyms in test names:
- `role_promotes` (use `agent_type_promotes`)
- `compute_budget` / `thinking_budget` (use `effort`)
- `kickoff` (use `spawn` for sub-agent or `activation` for main agent)
- `diagnostics_modal` (use `computer_info_modal`)
- `four_inject_sites` / `three_inject_sites` (use `five_inject_sites`)

---

## Sign-off bar

Testing-implementation exits with PASS when:
1. Full `pytest --timeout=30` suite passes.
2. Keystone test passes.
3. 10-point crystal sweep all pass.
4. 7 silent-regression scenarios all green.
5. 44-case regex parameterization green (2 residual KNOWN_LIMIT cases xfail as documented).
6. Per-feature gestalt tests green (12 tests = 6 features x 2 gestalts, minus F's empty agent-side).
7. Live 6-step manual smoke check passes; log captured and attached.
8. Pre-existing `test_agent_switch_keybinding` flake unchanged-status (flaky in isolation, passes on retry; same as parent commit).
