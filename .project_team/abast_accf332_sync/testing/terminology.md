# Testing Vision -- Terminology Axis

**Author:** TerminologyGuardian (`terminology_review` seat)
**Phase:** testing-vision
**Authority:** prescriptive for test-axis agents. Composability has final say
on naming-architecture conflicts.

## Purpose

Make every test in this run **locatable from cold context**. A reviewer who
has not seen the SPEC must be able to:

1. Read a test name and identify the SPEC component (A/B/C/D/E/F) and
   sub-unit (A1/A3/A4, B1-B5, C1-C3, D1-D5, E, F) it covers.
2. Read a test assertion and recognize a *contract string* (a runtime
   constant exposed to users or model) versus an internal symbol.
3. Trace a failure to the canonical glossary entry for the symbol that
   broke.

Without this discipline, regressions reintroduce the synonyms we spent
the implementation phase eliminating.

---

## 1. Test naming conventions

### Rule 1.1 -- Test name carries SPEC coordinates

Every test ships with a name of the form:

```
test_<component_letter><sub_unit>_<concept>_<expectation>
```

Examples:

| Concept | Test name |
|---|---|
| B2 default agent_type | `test_b2_agent_type_defaults_to_default_role` |
| B3 promotion on activation | `test_b3_agent_type_promotes_to_main_role_on_activation` |
| B3 revert on deactivation | `test_b3_agent_type_reverts_to_default_role_on_deactivation` |
| B4 hook closure shape | `test_b4_guardrail_hook_reads_agent_type_live` |
| C1 effort plumbing | `test_c1_effort_passed_to_claude_agent_options` |
| C2 EffortLabel cycle | `test_c2_effort_label_cycles_low_medium_high_max` |
| C2 snap to medium | `test_c2_effort_snaps_to_medium_on_non_opus_model` |
| C3 persistence | `test_c3_effort_persists_to_config_yaml` |
| D3 constraints block | `test_d3_assemble_constraints_block_includes_role_phase_scoped_rules` |
| D4 get_agent_info aggregator | `test_d4_get_agent_info_returns_eight_section_markdown` |
| D5 inject site activation | `test_d5_activation_site_routes_through_assemble_agent_prompt` |
| E pytest_needs_timeout | `test_e_pytest_needs_timeout_warn_fires_on_bare_pytest_run` |
| F modal restructure | `test_f_computer_info_modal_renders_session_jsonl_path` |

**Rationale.** A reviewer running `pytest -k "b3_"` gets all B3 tests in
one shot. `pytest -k "test_d5_activation_site"` locates the inject-site
contract test for the activation site without grepping through 9 files.

### Rule 1.2 -- File location matches component

| Component scope | Test file |
|---|---|
| A (workflow template variables) | `tests/test_workflow_engine_seam.py` (existing) |
| B (dynamic role identity) | `tests/test_agent_role_identity.py` (NEW) |
| C (effort cycling) | `tests/test_effort_cycling.py` (NEW) |
| D (constraints block + MCP) | `tests/test_constraints_block.py`, `tests/test_mcp_agent_info.py` (NEW) |
| E (pytest warn rule) | `tests/test_global_rules.py` (existing or NEW) |
| F (modal restructure) | `tests/test_computer_info_modal.py` (NEW) |

A reviewer locates the test for any SPEC component by file name alone.

---

## 2. Forbidden synonyms in test names and test prose

### Rule 2.1 -- Test names use the canonical noun

| Forbidden in test names | Required |
|---|---|
| `test_role_promotes_*` | `test_agent_type_promotes_*` |
| `test_compute_budget_*` | `test_effort_*` |
| `test_thinking_budget_*` | `test_effort_*` |
| `test_kickoff_site_*` | `test_spawn_site_*` (sub-agent) OR `test_activation_site_*` (main agent) |
| `test_diagnostics_modal_*` | `test_computer_info_modal_*` |
| `test_workflow_root_identifier_*` | `test_project_root_identifier_*` (Python identifier) |
| `test_get_phase_returns_rules_*` (post-narrowing) | `test_get_applicable_rules_*` OR `test_get_agent_info_*` |

### Rule 2.2 -- Test docstrings + comments use canonical prose

In test docstrings and inline comments:

| Forbidden | Required |
|---|---|
| "the role attribute" (ambiguous) | "the agent's runtime role (`agent.agent_type`)" or "the workflow's `main_role` field" |
| "thinking budget" / "compute budget" | "effort" or "effort level" |
| "kickoff" (overloaded -- means spawn AND activation) | "spawn" (sub-agent only) or "activation" (main agent only) |
| "the four inject sites" / "the three inject sites" | "the five inject sites" (per SPEC Decision 4: activation / spawn / phase-advance / broadcast / post-compact) |
| "max=high on Opus only" (older SPEC phrasing) | "non-Opus models snap to medium" (current SPEC) |
| "the unified modal" (ambiguous) | "the `ComputerInfoModal` (the modal that absorbed `DiagnosticsModal`)" |

### Rule 2.3 -- No commit-hash references in test prose

Per SPEC line 537: "Avoid commit-hash-only references where a one-line
description fits the slot." Test docstrings should refer to feature
components, not abast SHAs (no `accf332`, `8f99f03`, etc., except in a
test that *specifically* verifies a cherry-pick artifact).

---

## 3. Required contract strings in fixtures

A *contract string* is a literal that crosses the runtime boundary --
seen by users on screen, consumed by the SDK, or written to disk in a
format other components depend on. **Tests must assert on the exact
literal**, not a paraphrase, because production code generates the
literal and a regression that changes the literal breaks downstream
consumers silently.

### 3.1 EffortLabel display strings (locked Decision 2)

Tests that exercise the footer effort widget MUST assert on the literal
prefix `"effort: "`, not "thinking" or "quality" or "budget".

```python
# REQUIRED
assert label.renderable == "effort: high"
assert label.renderable == "effort: medium"
assert label.renderable == "effort: low"
assert label.renderable == "effort: max"   # Opus only

# FORBIDDEN
assert "thinking" in label.renderable      # paraphrase
assert "high" in label.renderable          # incomplete; passes on "thinking: high" too
```

Source of truth: `EffortLabel.EFFORT_DISPLAY` dict in
`claudechic/widgets/layout/footer.py`. Tests must NOT redefine this dict
locally.

### 3.2 Markdown section headings in agent prompts

Tests that exercise `assemble_constraints_block`,
`get_applicable_rules`, or `get_agent_info` MUST assert on the literal
heading strings -- they are part of the runtime contract the model reads.

```python
# REQUIRED literals
assert block.startswith("## Constraints")
assert "### Rules (" in block          # followed by "{n_active} active)"
assert "### Advance checks (" in block
assert "## Applicable guardrail rules" in agent_info  # NOT "## Rules"
assert "## Applicable injections" in agent_info
assert "## Advance checks for the current phase" in agent_info
assert "## Identity" in agent_info
assert "## Session" in agent_info
assert "## Active workflow + phase" in agent_info
assert "## Loader errors" in agent_info
```

Source of truth: `claudechic/workflows/agent_folders.py` for the block;
`claudechic/mcp.py` for `get_agent_info`'s 8-section structure (matches
SPEC lines 359-368 exactly).

### 3.3 Environment variable names

```python
# REQUIRED
assert env["CLAUDE_AGENT_ROLE"] == agent.agent_type
assert "CLAUDE_AGENT_NAME" in env
assert "CLAUDECHIC_APP_PID" in env

# FORBIDDEN
assert env["AGENT_ROLE"] == ...        # missing CLAUDE_ prefix
assert env["CLAUDE_ROLE"] == ...       # missing AGENT_
```

### 3.4 Template-variable tokens

```python
# REQUIRED
assert "${WORKFLOW_ROOT}" in raw_yaml          # braced
assert "${CLAUDECHIC_ARTIFACT_DIR}" in raw_yaml

# FORBIDDEN
assert "$WORKFLOW_ROOT" in raw_yaml            # bare; not the convergence target
assert "${PROJECT_ROOT}" in raw_yaml           # PROJECT_ROOT is the Python identifier, not the YAML token
```

### 3.5 MCP tool names

```python
# REQUIRED
assert "mcp__chic__whoami" in registered_tools
assert "mcp__chic__get_phase" in registered_tools
assert "mcp__chic__get_applicable_rules" in registered_tools
assert "mcp__chic__get_agent_info" in registered_tools

# FORBIDDEN
assert "mcp__chic__get_rules" in registered_tools              # not the canonical name
assert "mcp__chic__agent_info" in registered_tools             # missing get_ prefix
```

### 3.6 DEFAULT_ROLE sentinel

```python
# REQUIRED
from claudechic.agent import DEFAULT_ROLE
assert agent.agent_type == DEFAULT_ROLE
assert DEFAULT_ROLE == "default"

# FORBIDDEN
assert agent.agent_type == "default"     # bypasses the sentinel; if value changes, test still passes
assert agent.agent_type is None          # pre-B1 shape; should fail post-B1
```

---

## 4. Five-site inject naming convergence

SPEC Decision 4 (current) locks **five inject sites**. Tests must use
this set verbatim. The pre-Decision-4 names ("the four inject sites",
"the three inject sites") drift in older comments; tests should not
perpetuate them.

### Canonical site names (use these in test names + prose)

| # | Site | Wired in | Identifier / function |
|---|---|---|---|
| 1 | **activation** | `app.py::_activate_workflow` | inline `assemble_agent_prompt` call |
| 2 | **spawn** | `mcp.py::_make_spawn_agent` | `spawn_agent` MCP tool |
| 3 | **phase-advance** | `app.py::_inject_phase_prompt_to_main_agent` | called from `advance_phase` MCP tool |
| 4 | **broadcast** | `mcp.py::_make_advance_phase` (~line 986-1000) | broadcast loop to other agents on phase advance; **note: not yet wired to `assemble_agent_prompt` -- track in follow-up** |
| 5 | **post-compact** | `agent_folders.py::create_post_compact_hook` | SDK PostCompact hook |

### Required test names

| Test purpose | Test name |
|---|---|
| Verify activation site routes through helper | `test_d5_activation_routes_through_assemble_agent_prompt` |
| Verify spawn site routes through helper | `test_d5_spawn_routes_through_assemble_agent_prompt` |
| Verify phase-advance site routes through helper | `test_d5_phase_advance_routes_through_assemble_agent_prompt` |
| Verify broadcast site reaches other agents | `test_d5_broadcast_delivers_to_other_agents` |
| Verify post-compact site re-injects on /compact | `test_d5_post_compact_reinjects_constraints_block` |

### Forbidden test names

- `test_kickoff_*` (overloaded; use `spawn` or `activation`)
- `test_three_inject_sites_*` (stale count)
- `test_four_inject_sites_*` (stale count)
- `test_postcompact_*` (mixed-case noun; the SDK hook event IS literally
  `"PostCompact"` so a hook-event-name test may use it, but the
  inject-site noun in a test name should be `post_compact`)

---

## 5. Cross-reference: contract strings vs internal symbols

Contract strings cross the runtime boundary; internal symbols don't.
Tests must assert on contract strings; they may import internal symbols
freely.

### Runtime-boundary contract strings (assert on literals)

| Surface | Contract string(s) | Source file |
|---|---|---|
| User-visible footer text | `"effort: low"`, `"effort: medium"`, `"effort: high"`, `"effort: max"` | `widgets/layout/footer.py::EFFORT_DISPLAY` |
| Modal title | `"Info"` | `widgets/modals/computer_info.py::_get_title` |
| Constraints block top heading | `"## Constraints"` | `workflows/agent_folders.py::assemble_constraints_block` |
| Constraints block sub-headings | `"### Rules ({n_active} active)"`, `"### Advance checks ({phase})"` | same |
| `get_agent_info` section headings | 8 sections per SPEC lines 359-368 (see §3.2) | `mcp.py::_make_get_agent_info` |
| Agent env vars | `CLAUDE_AGENT_ROLE`, `CLAUDE_AGENT_NAME`, `CLAUDECHIC_APP_PID` | `app.py::_make_options` |
| YAML tokens | `${WORKFLOW_ROOT}`, `${CLAUDECHIC_ARTIFACT_DIR}` | `workflows/engine.py`, `workflows/_substitute.py` |
| MCP tool names | `mcp__chic__whoami`, `mcp__chic__get_phase`, `mcp__chic__get_applicable_rules`, `mcp__chic__get_agent_info` | `mcp.py::create_chic_server` |
| DEFAULT_ROLE value | `"default"` | `claudechic.agent::DEFAULT_ROLE` |
| Hook event key | `"PostCompact"` | SDK proper noun -- match SDK exactly |
| Rule id (E) | `"pytest_needs_timeout"` | `defaults/global/rules.yaml` |
| Rule message (E) | `"use --timeout=N (default 30) to avoid hung tests"` | `defaults/global/rules.yaml` |

### Internal symbols (import + use freely; not contract strings)

| Symbol | Home | Notes |
|---|---|---|
| `Agent.agent_type` | `claudechic/agent.py` | Attr name; tests access directly. |
| `Agent.effort` | `claudechic/agent.py` | Attr name. |
| `DEFAULT_ROLE` | `claudechic/agent.py` | Import the constant; do NOT compare to literal `"default"`. |
| `EffortLabel`, `EffortLabel.DEFAULT_LEVELS`, `EffortLabel.EFFORT_DISPLAY` | `widgets/layout/footer.py` | Import for assertions on the dict. |
| `ComputerInfoModal` | `widgets/modals/computer_info.py` | Import + instantiate. |
| `WorkflowEngine.project_root`, `WorkflowEngine.set_loader`, `WorkflowEngine.loader` | `workflows/engine.py` | Methods/properties. |
| `assemble_constraints_block`, `assemble_agent_prompt`, `assemble_phase_prompt` | `workflows/agent_folders.py` | Import + call. |
| `compute_digest`, `compute_advance_checks_digest` | `guardrails/digest.py`, `guardrails/checks_digest.py` | Import + call. Pass positional args to bypass the `active_wf` vs `active_workflow` parameter-name drift. |
| `_LoaderAdapter` | `claudechic/app.py` | Internal; tests that need it import directly. |
| `_get_disabled_rules` | `claudechic/app.py` | Internal helper. |

---

## 6. Newcomer test (apply before merging any test file)

Before submitting a test file:

1. **Read your test names aloud as a stranger.** Can you locate the
   SPEC component without opening the spec?
2. **Grep for forbidden synonyms in your file.** `rg -i 'thinking|kickoff|workflow_root\b|DiagnosticsModal' tests/test_<your_file>.py` should return no hits in test names or prose. (Hits inside the imported production code are out of scope here -- only test-side prose counts.)
3. **Check every literal-string assertion against §3.** If you wrote a
   string literal in an assertion, is it in the contract-string table?
   If not, ask: should it be? If yes, add it to the table in the next
   docs-phase pass.
4. **Confirm test names use the 5-site vocabulary** (§4). No "kickoff",
   no "three sites", no "four sites".

---

## 7. Open issues this memo cannot resolve

The following items are tracked by the broader test plan and are NOT
terminology-axis decisions:

- **`broadcast` site (#4) is not yet wired** through `assemble_agent_prompt`. SPEC says 5 sites; production has 4 wired. A test asserting "5 sites are wired" will fail. Either: (a) wire site #4 in this run, OR (b) write the test with `pytest.mark.xfail(reason="broadcast wiring deferred to follow-up")`. Composability picks.
- **`_get_disabled_rules` -> `mcp.py` integration** (open bug carried from slot 4 review). Tests for `get_applicable_rules` and `get_agent_info` should assert that user-disabled rules ARE filtered out. Without the wire-up, that test fails. Recommend writing the test now and using it to drive the fix.
- **`session_id` forwarding to `ComputerInfoModal`** (open bug carried from slot 5 review). A test that clicks the footer "info" button and then asserts the Session JSONL row contains the active session id will fail until `app.py:3870` is fixed. Recommend writing the test now and using it to drive the fix.

---

## TL;DR for test-axis agents

1. Test names: `test_<letter><sub>_<concept>_<expectation>`.
2. Don't rename canonical concepts in test prose. Use `agent_type`,
   `effort`, `Constraints block`, `guardrail rule`, `activation /
   spawn / phase-advance / broadcast / post-compact`.
3. Assert on contract-string literals (§3, §5). Import internal
   symbols; do not redefine them.
4. Never use `kickoff`, `thinking budget`, `compute budget`,
   `DiagnosticsModal`, "the four inject sites".
5. Every test must be locatable by SPEC letter at a glance.
