# Testing Vision -- project_team_context_review

This is the testing-phase contract for what the implementation must demonstrate. Synthesized from leadership input.

---

## What to test

Nine flow scenarios. Each describes a user or system action and what the test must assert about the delivered prompt.

### 1. Coordinator spawns at workflow start
All 5 segments fire: identity, phase markdown, constraints_stable (global + role-scoped rules), constraints_phase (phase-scoped rules + advance-checks), environment. The env segment resolves `${AGENT_ROLE}`, `${PEER_ROSTER}` as the merged role/name/description table (coordinator only). `${COORDINATOR_NAME}` in any phase markdown resolves to the coordinator's registered name; the literal token is absent from delivered output. Exactly one `## Constraints` heading in composed constraints output (omit_heading rule).

### 2. Sub-agent (e.g., skeptic) spawns mid-phase
Full 5-segment assembly: identity, phase markdown for (skeptic, current_phase), constraints_stable scoped to (skeptic, workflow), constraints_phase scoped to (skeptic, current_phase) without advance-checks, environment without peer roster. Advance-checks present for coordinator at the same phase but absent here. `_render_constraints_phase` called twice with identical `RenderContext` returns identical bytes (purity invariant).

### 3. Phase advances: broadcast to active typed sub-agents
Broadcast delivers phase + constraints_phase only. constraints_stable absent; identity absent; environment absent. Exactly one `## Constraints` heading (owned by constraints_phase renderer, omit_heading=False). Advance-checks absent for non-coordinator recipients.

### 4. Phase advances: broadcast to standing-by typed sub-agents
Sub-agent has no `<role>/<phase>.md` for the new phase (standing-by predicate True). Only constraints_phase fires. Identity suppressed. Phase renderer returns `""`. No placeholder in output.

### 5. User runs `/compact` on any agent
Post-compact full refresh: all 5 segments present. Identity restored. constraints_stable and constraints_phase both present, composed with a single `## Constraints` heading. Env segment fires. `assemble_constraints_block(slice="stable") + assemble_constraints_block(slice="phase", omit_heading=True)` byte-identical to monolithic `assemble_constraints_block(slice=None)` (slice-split keystone).

### 6. User changes constraints configuration at runtime
- `constraints_segment.compact: true` -> subsequent assemblies produce compact-list-formatted constraints block.
- `constraints_segment.scope.sites` excludes `post-compact` -> post-compact assembly delivers no constraints segment.
- `mcp__chic__get_agent_info` with no `compact` argument returns markdown-table form regardless of user-tier setting; with `compact=true` returns compact-list. User-tier setting is not consulted by the MCP tool.
- `scope.sites: []` -> `ConfigValidationError` raised at config-load.

### 7. User sets `environment_segment.enabled: false`
Env renderer never invoked at spawn, activation, or post-compact. No env content in any assembled prompt. `active_workflow` unset -> renderer returns `""` even when enabled. `environment_segment.compact: true` -> overlay omitted; base.md only.

### 8. User opens settings > Agent prompt context > Advanced...
`environment_segment.enabled` toggle saves to config and live-reloads. In `AdvancedConstraintsSitesScreen`: clearing the last remaining checkbox triggers a notice and reverts the toggle in place. Plain-language labels in primary column; engineering tokens in muted secondary column.

### 9. User clicks an MCP tool widget in chat
Content remains visible post-click. Existing toggle (expand/collapse) behavior preserved.

---

## How to test

### Standard
**Generalprobe** (per coordinator/testing_vision.md): every test is a full dress rehearsal against real infrastructure. No mocking, no skipping, no `xfail` markers, public API only, production-identical setup.

### Project conventions
From `CLAUDE.md` (Testing section):
- Parallel by default: `pytest tests/ -n auto -q --timeout=30`.
- `--timeout=30` required (also enforced by `global:pytest_needs_timeout`).
- Single-file form: `pytest tests/test_foo.py -v --timeout=30`.
- Full-suite form (with results captured): `TS=$(date -u +%Y-%m-%d_%H%M%S) && pytest --junitxml=.test_results/${TS}.xml --tb=short --timeout=30 2>&1 | tee .test_results/${TS}.log` (also enforced by `global:no_bare_pytest`).

### Naming conventions (terminology lead)
Style: descriptive plain (no T-codes, no D-codes).
Function template: `test_<subject>_<condition>_<outcome>`.
File granularity: one file per spec section or feature area. Suggested files:
- `tests/test_gate_predicate.py`
- `tests/test_renderer_split.py`
- `tests/test_env_segment.py`
- `tests/test_peer_roster.py`
- `tests/test_constraints_decomposition.py`
- `tests/test_settings_agent_prompt_context.py`
- `tests/test_tool_widget_click.py`

Canonical names to use verbatim in test names: `constraints_stable`, `constraints_phase`, `at_broadcast`, `post_compact`, `standing_by`, `advance_checks`, `omit_heading`, `slice_split_byte_identical`, `coordinator_only`, `peer_roster`.

Fixture names: snake_case, noun-phrase, matching existing patterns (`real_agent_with_mock_sdk`, `mock_sdk`, `review_job_factory` style).

### Hardest paths (skeptic lead)
The following surfaces have known testing difficulty and may need partial coverage or manual smoke tests:

- **Post-compact path** -- the SDK PostCompact callback is hard to fire in-process. Live SDK session may be needed for full coverage of the hook's `disabled_rules` and `settings` resolution. Plan for partial coverage; flag explicitly any uncovered cell.
- **Phase-advance broadcast standing-by suppression** -- requires a multi-agent fixture with mixed phase-markdown presence. Slow and brittle; budget extra time.
- **Settings UI live behavior** -- Textual interaction tests need a pilot harness; the existing pattern in `tests/test_app_ui.py` is the model.
- **`compute_digest` phase-equality check** -- skeptic flagged a potential silent drop if `compute_digest` returns bare phase IDs while `ctx.phase` is qualified. Test with real phase-qualified rules to expose.
- **Live `/compact`** -- not testable in-process; use live SDK remote testing (see below).

### Live SDK remote testing
For hard paths the in-process harness cannot cover (post-compact, multi-agent broadcast, live UI flows): run claudechic with the HTTP control surface enabled (`./scripts/claudechic-remote 9999`). The server exposes endpoints for sending messages, taking screenshots, and reading state; full API at `docs/dev/remote-testing.md`. The user is in the loop -- they trigger and observe with AI assistance, confirming behavior that automated assertions cannot reach.

### Pre-existing tests at risk (skeptic lead)
Inspect and update if they break under the refactor:
- `test_d3_assemble_agent_prompt_skips_empty_constraints_block`
- `test_d5_all_inject_sites_route_through_assemble_agent_prompt`
- Any test calling `assemble_agent_prompt` without `manifest` passed (now scans filesystem live).
- Any test calling `assemble_constraints_block` without `slice=` (defaults still match; document the load-bearing default).

---

## Coverage map (user-alignment lens)

| User ask | Scenario covering it |
|---|---|
| GitHub issue #27 (standing-by suppression) | Scenario 4: standing-by broadcast suppresses identity/phase; only constraints_phase fires |
| GitHub issue #28 (constraints configurability) | Scenario 6: config parsing, ConfigValidationError, scope.sites honored, settings UI |
| Spawn-time environment knowledge | Scenarios 1, 2: env fires at spawn; coordinator-only peer roster; coordinator_name substitution |
| Tighten project_team via time/place/role review | Scenarios 1-5: per-site segment set; broadcast narrowing; post-compact full refresh |
| Failure-mode analysis from prior run | Documentation deliverable -- not a code-behavior test; covered by `STATUS.md` and `SPEC_bypass.md` |

---

## Gaps (user-alignment lens)

Coverage paths that don't exist:

1. **Prompt-audit content.** "Agents review and suggest content of injections" is validated by the `prompt_audit/<role>.md` artifacts and the `role_feedback/` advance-check, not by automated tests. Verify-file-exists is possible; verifying content correctness is editorial. Note this explicitly as accepted.
2. **`role_feedback/` advance-check behavior.** Structurally testable (the check appears in `project_team.yaml`) but full behavior needs a live run. Accepted as run-validated.

---

## Success criteria

- All 9 flow scenarios have at least their representative cases written and passing.
- `pytest tests/ -n auto -q --timeout=30` exit code 0 (or 1-flake parallel-load tolerance for known-flaky `test_app_ui` cases that pass sequentially).
- Skeptic's "what will break first" predictions are either captured by tests (and pass) or explicitly documented as out-of-scope for this round.

## Failure criteria (what makes this testing meaningless)

- Tests that mock `assemble_agent_prompt`, `assemble_constraints_block`, or any renderer -- the Generalprobe standard forbids it. Tests must call the real functions with real `RenderContext`.
- Tests that skip or `xfail` the hard cases (post-compact, broadcast standing-by, settings UI) without an explicit user-acknowledged exception.
- Tests that re-introduce removed scope (structural floor, `enabled` toggle for constraints, token-cost assertions).
- Tests that produce a green pass without exercising the new code paths (e.g., a smoke test that asserts existence rather than behavior).

---

## Standing by for user approval. Iteration welcome before the testing-implementation phase opens.
