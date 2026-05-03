# TEST_SPECIFICATION.md -- project_team_context_review

Test plan for the `project_team_context_review` round. Translates the
nine flow scenarios in `userprompt_testing.md` into a concrete pytest
plan honoring the Generalprobe standard.

**Self-containment.** Every term used here is defined inside this
document. Do not consult `userprompt_testing.md`, `SPEC_bypass.md`, or
the axis specs to interpret any name, fixture, or assertion below.

---

## 1. Glossary (defined here, used here)

| Term | Definition |
|------|------------|
| Generalprobe standard | Every test is a full dress rehearsal: real `assemble_agent_prompt`, real `RenderContext`, real loader, real `ProjectConfig`, real Textual pilot for UI. No `pytest.skip`, no `xfail`, no mocks of the system under test. The `mock_sdk` fixture from `tests/conftest.py` IS allowed (it stubs only the external Anthropic SDK transport, not the engine). |
| Public API | The four user-callable entry points: `assemble_agent_prompt`, `assemble_constraints_block`, `assemble_phase_prompt`, `create_session_start_compact_hook`; the `gate(...)` predicate; the `ChatApp` Textual pilot; `ProjectConfig.load/save`; the `mcp__chic__get_agent_info` MCP tool. Tests call these by import, never reach into `_render_*` private helpers except for the explicit purity invariant in scenario 2. |
| Site (a.k.a. injection site) | One of `spawn`, `activation`, `phase-advance`, `post-compact`. Engineering tokens; passed via `time=` kwarg. |
| Place (a.k.a. prompt segment) | One of `identity`, `phase`, `constraints_stable`, `constraints_phase`, `environment`. |
| `constraints_stable` | The slice produced by `assemble_constraints_block(slice="stable", omit_heading=False)`. Owns the `## Constraints` heading when emitted. |
| `constraints_phase` | The slice produced by `assemble_constraints_block(slice="phase", omit_heading=...)`. Phase-scoped rules + (coordinator-only) advance-checks. |
| `at_broadcast` | The phase-advance fan-out site (`mcp.py::_make_advance_phase`'s async post-call broadcast). |
| `post_compact` | The PostCompact SDK hook site (`create_session_start_compact_hook`). |
| `standing_by` predicate | Returns `True` when `agent_type != "default"` AND `<workflow_dir>/<agent_type>/<bare_phase>.md` does not exist. |
| `advance_checks` | The phase-scoped advance-check rows that emit only when `ctx.role == "coordinator"`. |
| `omit_heading` | The boolean kwarg threaded by the composer into `_render_constraints_phase`; `True` when stable is emitted alongside, `False` when phase emits alone (T3). |
| `slice_split_byte_identical` | The keystone invariant: `assemble_constraints_block(slice="stable") + assemble_constraints_block(slice="phase", omit_heading=True)` equals `assemble_constraints_block(slice=None)` byte-for-byte for every `RenderContext`. |
| `coordinator_only` | The visibility scope of `advance_checks` -- emitted iff `ctx.role == "coordinator"`. |
| `peer_roster` | The `${PEER_ROSTER}` token resolved as `(role, name, description)` markdown table; emitted to the coordinator only. |
| Locked contract string | A literal substring the test asserts verbatim because external surfaces depend on it: `"## Constraints"`, `"### Rules ("`, `"### Advance checks ("`, `"PostCompact"`, `"at least one site must remain checked"`, `"ConfigValidationError"`. |
| Real workflow_dir | A `tmp_path`-rooted directory built per-test that mirrors the `claudechic/defaults/workflows/<id>/` layout: a YAML manifest, one or more `<role>/identity.md`, and `<role>/<bare_phase>.md` files. |
| Real manifest | Output of `claudechic.workflows.loader.ManifestLoader(...).load()` against a real `(global_dir, workflows_dir)` pair built under `tmp_path`. |
| Live SDK harness | The HTTP control surface launched by `./scripts/claudechic-remote 9999` -- the only way to drive a real `/compact` and a real multi-agent broadcast against the live Anthropic SDK. |

---

## 2. Test file structure

One file per spec subject, mirroring the suggested files in
`userprompt_testing.md`. Files marked NEW must be created; files marked
EXTEND already exist and gain new functions per the scenario tables in
section 5.

| File | Status | Subject |
|------|--------|---------|
| `tests/test_gate_predicate.py` | NEW | The pure `gate(time, place, role, phase, settings, manifest)` predicate from `claudechic/workflows/agent_folders.py`. |
| `tests/test_renderer_split.py` | NEW | The five `_render_*` helpers and `RenderContext` purity (one input -> one output). |
| `tests/test_env_segment.py` | NEW | `_render_environment` token substitution, opt-out, `compact: true` overlay-omit, `active_workflow`-unset guard. |
| `tests/test_peer_roster.py` | NEW | `${PEER_ROSTER}` and `${COORDINATOR_NAME}` substitution; coordinator-only emission. |
| `tests/test_constraints_decomposition.py` | NEW | `slice="stable"`, `slice="phase"`, `omit_heading`, the slice-split byte-identical keystone, `advance_checks` coordinator-only scoping, single `## Constraints` heading invariant. |
| `tests/test_settings_agent_prompt_context.py` | NEW | The `Agent prompt context` settings section, `AdvancedConstraintsSitesScreen`, `AdvancedEnvironmentSitesScreen`, last-row floor, plain-language vs token columns. |
| `tests/test_tool_widget_click.py` | NEW | MCP tool widget content remains visible after click; existing toggle (expand/collapse) preserved. |
| `tests/test_phase_prompt_delivery.py` | EXTEND | Add scenario 1, 3, 4 end-to-end activation + broadcast tests. |
| `tests/test_constraints_block.py` | EXTEND | Update `test_d3_assemble_agent_prompt_skips_empty_constraints_block`, `test_d5_all_inject_sites_route_through_assemble_agent_prompt` for the new `time=` kwarg and slice plumbing. |
| `tests/test_mcp_get_agent_info.py` | EXTEND | Add `compact` MCP-input-parameter behavior (table by default, list with `compact=true`, user-tier setting NOT consulted). |
| `tests/test_config.py` | EXTEND | Add `constraints_segment` / `environment_segment` parse + validate; `scope.sites: []` -> `ConfigValidationError`. |

---

## 3. `conftest.py` additions

Add to `tests/conftest.py`. Existing fixtures are unchanged.

| Fixture | Scope | Returns | Purpose |
|---------|-------|---------|---------|
| `workflow_dir_factory` | function | `Callable[..., Path]` | Build a real workflow_dir under `tmp_path`. Args: `roles: dict[str, list[str]]` (role -> phase ids that get a `<role>/<bare_phase>.md`), `with_identity: dict[str, bool]`, `manifest_extra: dict | None`. Writes a YAML manifest matching the bundled `project_team` shape. |
| `real_manifest` | function | `LoadResult` | Run the real `ManifestLoader` over a `tmp_path/global` + `tmp_path/workflows/<id>` pair. Returns the live `LoadResult` consumed by `assemble_constraints_block`. |
| `gate_settings_factory` | function | `Callable[..., GateSettings]` | Construct a real `GateSettings` frozen dataclass from kwargs (`constraints_compact`, `constraints_sites`, `env_enabled`, `env_sites`, `env_compact`). Defaults match SPEC §3.7 / §3.11. |
| `render_context_factory` | function | `Callable[..., RenderContext]` | Construct a real `RenderContext` from `(time, place, role, phase, workflow_dir, settings, manifest, active_workflow)`. The same callable used by the inject sites in production. |
| `agent_manager_with_peers` | function | `AgentManager` | An `AgentManager` populated with a coordinator + 2 typed sub-agents and a default-roled agent so `${NAME_ROUTING_TABLE}` and `${PEER_ROSTER}` resolve to non-empty content. Reuses the existing `mock_sdk` transport. |
| `workflow_pilot` | function | async pilot | Start `ChatApp` with `mock_sdk`, drive through workflow activation, yield the Textual pilot. Mirrors the existing pattern in `tests/test_phase_prompt_delivery.py` so callers do not duplicate setup. |
| `project_config_writer` | function | `Callable[[dict], Path]` | Write a `project/.claudechic/config.yaml` under `tmp_path` and return the project root. Used by every settings-driven test. |

Naming: snake_case noun phrases, matching `real_agent_with_mock_sdk`,
`mock_sdk`, `review_job_factory`. Factories return callables; concrete
artifacts return values. No global state between tests.

---

## 4. Infrastructure requirements

Production-identical setup is mandatory. Every test below builds against
the following:

- **Real `workflow_dir`** -- built by `workflow_dir_factory`. Mirrors
  `claudechic/defaults/workflows/<id>/` exactly: YAML manifest at
  `<workflow_dir>/<workflow_id>.yaml`, role folders with `identity.md`
  and per-phase markdown. No `unittest.mock.mock_open` for filesystem.
- **Real `LoadResult`** -- built by `real_manifest`. The real
  `ManifestLoader` walks the package / user / project tiers exactly as
  it does in production. Tests that need a single rule build a
  one-rule YAML and load it; they do NOT instantiate `Rule` objects
  directly except where the existing `_StubLoader` pattern in
  `tests/test_constraints_block.py` is reused for D6 / Seam tests.
- **Real `RenderContext`** -- the production frozen dataclass. Tests
  that need to compare two assemblies build two `RenderContext` values
  with identical content and assert byte-equal `_render_*` output (the
  purity invariant).
- **Real `ProjectConfig`** -- `ProjectConfig.load(tmp_path)` and
  `ProjectConfig.save(tmp_path)`. No direct dataclass mutation in tests
  that are about persistence; round-trip through YAML.
- **Real Textual pilot** -- `app.run_test(size=(120, 40))` from
  `tests/test_app_ui.py`. UI assertions use widget queries
  (`pilot.app.query_one(...)`) and `await pilot.click(...)` /
  `await pilot.press(...)`. No `monkeypatch` of widget bodies.
- **Real Anthropic SDK** -- only via the Live SDK harness in section 6.
  In-process tests use the existing `mock_sdk` fixture, which stubs the
  HTTP transport only; the engine and prompt assembly run unchanged.
- **`pytest --timeout=30`** -- mandatory per
  `global:pytest_needs_timeout`. Per-file invocation:
  `pytest tests/test_<file>.py -v --timeout=30`.
- **No bare `pytest`** -- per `global:no_bare_pytest`. Full-suite runs
  go through the timestamped `.test_results/` form documented in
  `CLAUDE.md`.

---

## 5. Scenario coverage

Each subsection translates one scenario from `userprompt_testing.md`
into one or more files + concrete test functions. Function names follow
the `test_<subject>_<condition>_<outcome>` template and use the
canonical names (`constraints_stable`, `constraints_phase`,
`at_broadcast`, `post_compact`, `standing_by`, `advance_checks`,
`omit_heading`, `slice_split_byte_identical`, `coordinator_only`,
`peer_roster`).

### 5.1 Scenario 1 -- Coordinator spawns at workflow start

**Files:** `tests/test_phase_prompt_delivery.py` (E2E),
`tests/test_env_segment.py`, `tests/test_peer_roster.py`,
`tests/test_constraints_decomposition.py`.

| Test function | Verifies |
|---------------|----------|
| `test_coordinator_spawn_emits_all_five_segments` | Activation site assembly contains all five place markers (identity, phase, constraints_stable rule id, constraints_phase rule id, environment marker). |
| `test_coordinator_spawn_environment_resolves_agent_role_token` | `${AGENT_ROLE}` resolves to `coordinator`; the literal token is absent from the assembled prompt. |
| `test_coordinator_spawn_peer_roster_renders_role_name_description_table` | `${PEER_ROSTER}` resolves to a markdown table containing one row per registered peer with `role`, `name`, `description` columns. |
| `test_coordinator_spawn_coordinator_name_token_resolves` | `${COORDINATOR_NAME}` in any phase markdown resolves to the coordinator's registered name (e.g. `claudechic`); the literal `${COORDINATOR_NAME}` is absent. |
| `test_coordinator_spawn_omit_heading_yields_one_constraints_heading` | Exactly one `## Constraints` heading appears in the composed output (not two). |

**Fixtures:** `workflow_pilot`, `agent_manager_with_peers`,
`workflow_dir_factory`, `gate_settings_factory`.

### 5.2 Scenario 2 -- Sub-agent (e.g., skeptic) spawns mid-phase

**Files:** `tests/test_renderer_split.py`,
`tests/test_constraints_decomposition.py`.

| Test function | Verifies |
|---------------|----------|
| `test_skeptic_spawn_emits_full_five_segments_no_peer_roster` | Skeptic spawn assembly contains identity, phase, constraints_stable, constraints_phase, environment; `${PEER_ROSTER}` is empty (coordinator_only). |
| `test_skeptic_spawn_advance_checks_absent_under_coordinator_only` | The `### Advance checks (` subsection is present for `role="coordinator"` and absent for `role="skeptic"` at the same phase, same RenderContext otherwise. |
| `test_render_constraints_phase_purity_returns_identical_bytes` | Calling `_render_constraints_phase` twice with identical `RenderContext` returns byte-identical strings. |
| `test_render_constraints_phase_purity_no_io_or_clock` | Patching `time.time` and `pathlib.Path.read_text` mid-call produces no behavior change (predicate purity). |

**Fixtures:** `render_context_factory`, `real_manifest`,
`workflow_dir_factory`.

### 5.3 Scenario 3 -- Phase advances: broadcast to active typed sub-agents

**Files:** `tests/test_phase_prompt_delivery.py`,
`tests/test_constraints_decomposition.py`.

| Test function | Verifies |
|---------------|----------|
| `test_phase_advance_at_broadcast_emits_phase_and_constraints_phase_only` | Broadcast assembly to a typed sub-agent contains the phase marker and the `constraints_phase` slice; identity / `constraints_stable` / environment markers are absent. |
| `test_phase_advance_at_broadcast_constraints_phase_owns_heading` | The single `## Constraints` heading in the broadcast output comes from `constraints_phase` (`omit_heading=False`). |
| `test_phase_advance_at_broadcast_advance_checks_absent_for_non_coordinator` | Sub-agents at broadcast receive zero `### Advance checks (` subsections regardless of phase content. |

**Fixtures:** `workflow_pilot`, `agent_manager_with_peers`,
`workflow_dir_factory`.

### 5.4 Scenario 4 -- Phase advances: broadcast to standing-by typed sub-agents

**Files:** `tests/test_phase_prompt_delivery.py`,
`tests/test_gate_predicate.py`.

| Test function | Verifies |
|---------------|----------|
| `test_standing_by_predicate_true_when_role_phase_md_missing` | `gate(time="phase-advance", place="identity", role="skeptic", phase="testing-implementation", ...)` returns `False` when `<wf>/skeptic/testing-implementation.md` does not exist. |
| `test_standing_by_at_broadcast_emits_only_constraints_phase` | Assembly for the standing-by recipient contains the `constraints_phase` rule id and nothing else (no identity, no phase marker, no environment). |
| `test_standing_by_phase_renderer_returns_empty_string_no_placeholder` | `_render_phase` returns `""` (not `"# Phase\n\n(no content)"` or similar) when the role/phase markdown is missing. |

**Fixtures:** `workflow_dir_factory` (build with mixed-phase coverage),
`render_context_factory`, `real_manifest`.

### 5.5 Scenario 5 -- User runs `/compact` on any agent

**Files:** `tests/test_phase_prompt_delivery.py`,
`tests/test_constraints_decomposition.py`.

| Test function | Verifies |
|---------------|----------|
| `test_post_compact_full_refresh_all_five_segments_present` | The PostCompact closure return value contains identity, phase, `constraints_stable`, `constraints_phase`, environment markers. |
| `test_post_compact_single_constraints_heading` | Exactly one `## Constraints` heading appears in the post-compact prompt. |
| `test_constraints_slice_split_byte_identical_to_monolithic` | KEYSTONE: `assemble_constraints_block(slice="stable", omit_heading=False) + "\n\n" + assemble_constraints_block(slice="phase", omit_heading=True)` is byte-equal to `assemble_constraints_block(slice=None)` for the same `(loader, role, phase)`. |
| `test_post_compact_environment_segment_fires_when_active_workflow_set` | `_render_environment` returns non-empty content under post-compact when `ctx.active_workflow` is set. |

**Live-only complement** (section 6): `live_post_compact_real_sdk` --
the in-process `mock_sdk` cannot fire the SDK PostCompact callback;
this part of the scenario validates only against the live harness.

**Fixtures:** `workflow_dir_factory`, `real_manifest`,
`gate_settings_factory`, `render_context_factory`.

### 5.6 Scenario 6 -- User changes constraints configuration at runtime

**Files:** `tests/test_constraints_decomposition.py`,
`tests/test_config.py`, `tests/test_mcp_get_agent_info.py`.

| Test function | Verifies |
|---------------|----------|
| `test_constraints_segment_compact_true_yields_compact_list_form` | With `constraints_segment.compact: true` saved, the next assembly emits the compact-list form (no `\| id \| ... \|` table rows). |
| `test_constraints_segment_compact_false_yields_markdown_table_form` | With `compact: false`, the assembly emits the markdown-table form (header row + alignment row present). |
| `test_constraints_segment_scope_sites_excludes_post_compact_suppresses_block` | After removing `post-compact` from `scope.sites` and round-tripping through `ProjectConfig`, the post_compact assembly contains no constraints segment. |
| `test_get_agent_info_default_returns_markdown_table_ignoring_user_setting` | Calling `mcp__chic__get_agent_info` with no `compact` argument returns markdown-table form even when user-tier `constraints_segment.compact: true` is set. |
| `test_get_agent_info_compact_true_returns_compact_list` | Calling `mcp__chic__get_agent_info(compact=true)` returns the compact-list form. |
| `test_constraints_segment_scope_sites_empty_raises_config_validation_error` | Loading a project config with `scope.sites: []` raises `ConfigValidationError` at `ProjectConfig.load(...)`. |

**Fixtures:** `project_config_writer`, `gate_settings_factory`,
`render_context_factory`, `real_manifest`.

### 5.7 Scenario 7 -- User sets `environment_segment.enabled: false`

**Files:** `tests/test_env_segment.py`, `tests/test_gate_predicate.py`.

| Test function | Verifies |
|---------------|----------|
| `test_environment_segment_enabled_false_skips_renderer_at_all_three_sites` | With `environment_segment.enabled: false`, `gate(...)` returns `False` for `place="environment"` at `time in {spawn, activation, post-compact}`; assembled prompts contain no environment-segment marker. |
| `test_environment_segment_active_workflow_unset_returns_empty_string` | With `enabled: true` but `ctx.active_workflow is None`, `_render_environment` returns `""`. |
| `test_environment_segment_compact_true_omits_overlay_keeps_base` | With `compact: true`, the rendered environment contains the `base.md` markers and omits the `project_team.md` overlay markers. |
| `test_environment_segment_compact_false_includes_overlay` | With `compact: false`, both `base.md` and `project_team.md` markers are present (default behavior). |

**Fixtures:** `gate_settings_factory`, `render_context_factory`,
`workflow_dir_factory`.

### 5.8 Scenario 8 -- User opens settings > Agent prompt context > Advanced...

**Files:** `tests/test_settings_agent_prompt_context.py`.

| Test function | Verifies |
|---------------|----------|
| `test_agent_prompt_context_section_contains_five_top_level_rows` | Opening `SettingsScreen` shows a header `Agent prompt context` followed by 5 rows with the labels from SPEC §3.12 (no injection-site vocabulary). |
| `test_environment_segment_enabled_toggle_saves_and_live_reloads` | Toggling the `Team coordination context` row writes `environment_segment.enabled` to the project config and the new value is observable on the next `gate(...)` call without a restart. |
| `test_advanced_constraints_sites_screen_renders_four_rows_with_token_secondary_column` | `AdvancedConstraintsSitesScreen` shows 4 rows; primary column carries plain-language labels (`when an agent starts` etc.); secondary column carries engineering tokens (`spawn`, `activation`, `phase-advance`, `post-compact`). |
| `test_advanced_constraints_sites_screen_clearing_last_checkbox_reverts_with_notice` | Unchecking the only remaining checkbox emits the notice `at least one site must remain checked` and the checkbox returns to checked. |
| `test_advanced_environment_sites_screen_renders_three_rows` | `AdvancedEnvironmentSitesScreen` shows exactly 3 rows (no `phase-advance`). |
| `test_advanced_environment_sites_screen_last_row_floor_holds` | Same last-row revert + notice as the constraints variant. |

**Fixtures:** `workflow_pilot`, `project_config_writer`. Modeled on
`tests/test_app_ui.py` and `tests/test_settings_screen.py`.

### 5.9 Scenario 9 -- User clicks an MCP tool widget in chat

**Files:** `tests/test_tool_widget_click.py`.

| Test function | Verifies |
|---------------|----------|
| `test_mcp_tool_widget_content_visible_after_click` | After `await pilot.click(...)` on a rendered `mcp__chic__*` tool-use widget, the widget's content body is still present in the DOM and rendered (not cleared). |
| `test_mcp_tool_widget_collapse_toggle_preserved` | The pre-existing collapse/expand behavior still toggles on click (one click collapses, second click expands). |

**Fixtures:** `workflow_pilot`. Reuses widget query patterns from
`tests/test_widgets.py` and `tests/test_diff_preview.py`.

---

## 6. Live SDK remote testing

For paths the in-process pilot cannot reach, the user drives the live
harness with AI assistance. Start with:

```bash
./scripts/claudechic-remote 9999
```

Endpoints + full API live in `docs/dev/remote-testing.md`. The
following scenarios have a live-only complement; they appear in the
plan above with the in-process complement, and the live complement is
listed here.

| Live test id | Scenario covered | Why live-only |
|--------------|------------------|---------------|
| `live_post_compact_real_sdk` | 5 | The SDK PostCompact callback fires only against the real Anthropic transport; `mock_sdk` cannot trigger it. The live test runs `/compact` against a real coordinator and asserts the next user message contains all five segments. |
| `live_phase_advance_broadcast_multi_agent` | 3, 4 | A real broadcast loop touches multiple concurrent agents with mixed standing-by status. The in-process pilot covers each agent in isolation; the live test confirms ordering, no crosstalk, and that standing-by suppression holds when N >= 3 sub-agents are spawned. |
| `live_settings_ui_round_trip` | 8 | Full keyboard navigation through `SettingsScreen` -> `Agent prompt context` -> `Advanced...` with screenshots, including the notice toast on the last-row revert. |

Each live test has a checklist of HTTP calls + screenshot assertions
captured in a follow-up note during testing-implementation; they are
not pytest functions.

---

## 7. Locked contract strings (asserted verbatim)

| String | Source | Tests that assert it |
|--------|--------|----------------------|
| `## Constraints` | `assemble_constraints_block` heading | scenarios 1, 3, 5 |
| `### Rules (` | rules sub-heading prefix | scenarios 1, 5 |
| `### Advance checks (` | advance-checks sub-heading prefix | scenarios 2, 3 |
| `PostCompact` | SDK hook key (capitalization) | scenario 5, existing `tests/test_phase_prompt_delivery.py::test_inv_aw_9_*` |
| `at least one site must remain checked` | last-row floor notice | scenario 8 |
| `ConfigValidationError` | exception class name raised on `scope.sites: []` | scenario 6 |
| `${AGENT_ROLE}` / `${PEER_ROSTER}` / `${COORDINATOR_NAME}` | unsubstituted token sentinels | scenarios 1, 7 (asserted ABSENT post-substitution) |

---

## 8. Pre-existing tests at risk

To inspect during testing-implementation; update if they break under
the refactor (no skip / no xfail; fix the test or fix the code):

- `tests/test_constraints_block.py::test_d3_assemble_agent_prompt_skips_empty_constraints_block`
  -- now needs `time=` kwarg threading.
- `tests/test_constraints_block.py::test_d5_all_inject_sites_route_through_assemble_agent_prompt`
  -- enumerate the four sites with the new `time=` kwarg.
- Any caller of `assemble_agent_prompt` that omits `manifest=`. The new
  body scans the filesystem live; tests must pass a real `LoadResult`
  via `real_manifest` or accept the live read.
- Any caller of `assemble_constraints_block` without `slice=`. The
  default still matches today's monolithic form; document the
  load-bearing default in the test docstring.
- `tests/test_phase_prompt_delivery.py::test_inv_aw_9_post_compact_returns_empty_when_none`
  -- reconfirm under the new `environment_segment.enabled: true`
  default.

---

## 9. Generalprobe compliance checklist

Every test satisfies each item:

- [ ] Real infrastructure end-to-end: real `assemble_agent_prompt`,
  real `RenderContext`, real `ManifestLoader`, real `ProjectConfig`,
  real Textual pilot. The transport-only `mock_sdk` fixture from
  `tests/conftest.py` is the sole permitted stub.
- [ ] All test functions named `test_<subject>_<condition>_<outcome>`.
- [ ] Rule ids come from a real one-rule YAML loaded by `ManifestLoader`
  or the documented `_StubLoader` reused from
  `tests/test_constraints_block.py`. Public API only.
- [ ] Every test runs with `--timeout=30`.
- [ ] Per-file invocations follow `pytest tests/test_<file>.py -v --timeout=30`;
  full-suite invocations follow the timestamped `.test_results/` form
  in `CLAUDE.md`.
- [ ] One file per spec subject; no bundled files mixing scenarios.
- [ ] Error-path tests assert observable behavior
  (e.g. `ConfigValidationError` raised at `ProjectConfig.load(...)`),
  not internal raise-site identity.

---

## 10. Coverage matrix (scenario -> file)

| Scenario | File(s) | E2E? |
|----------|---------|------|
| 1. coordinator spawn | `test_phase_prompt_delivery.py`, `test_env_segment.py`, `test_peer_roster.py`, `test_constraints_decomposition.py` | Yes (existing pilot) |
| 2. skeptic mid-phase spawn | `test_renderer_split.py`, `test_constraints_decomposition.py` | No (renderer purity) |
| 3. phase-advance to active typed sub-agents | `test_phase_prompt_delivery.py`, `test_constraints_decomposition.py` | Yes |
| 4. phase-advance to standing-by sub-agents | `test_phase_prompt_delivery.py`, `test_gate_predicate.py` | Partial (in-process); live for N>=3 |
| 5. `/compact` full refresh | `test_phase_prompt_delivery.py`, `test_constraints_decomposition.py` | Live-only for the SDK callback |
| 6. constraints config at runtime | `test_constraints_decomposition.py`, `test_config.py`, `test_mcp_get_agent_info.py` | No |
| 7. `environment_segment.enabled: false` | `test_env_segment.py`, `test_gate_predicate.py` | No |
| 8. settings UI advanced | `test_settings_agent_prompt_context.py` | Yes (Textual pilot) |
| 9. MCP tool widget click | `test_tool_widget_click.py` | Yes (Textual pilot) |

---

*Author: TestEngineer, testing-specification phase.*
