# STATUS — workflow_engine_test

## Vision

**Goal:** Smoke-test the new claudechic workflow engine by walking through the project-team workflow phases.

**Value:** Verify that phase transitions, `set_artifact_dir`, and supporting MCP tools behave correctly in a real run.

**Domain terms:**
- *Workflow engine* — claudechic's phase-driven coordinator system (`claudechic/workflows/engine.py`)
- *Artifact dir* — bound on-disk location for workflow outputs (STATUS.md, specs, etc.)
- *Phase* — discrete step in a workflow (Vision, Setup, Leadership, ...)

**Success looks like:** Each phase advances cleanly; artifact dir is bound and readable; MCP tools respond as expected.

**Failure looks like:** Phase transitions fail, artifact dir is wrong, or coordinator behavior diverges from the workflow markdown.

## Setup

- **Working dir:** `/groups/spruston/home/moharb/claudechic`
- **Artifact dir:** `/groups/spruston/home/moharb/claudechic/.project_team/workflow_engine_test`
- **Git:** Yes — repo at `/groups/spruston/home/moharb/claudechic` (untracked: `.claudechic/`)
- **Existing project_team runs:** `issue_23_path_eval`, `independent_chic` (unrelated — fresh dir created for this run)

## Phase Log

- [x] **Vision** — User explicitly approved (described as a workflow-engine smoke test)
- [x] **Setup** — Artifact dir bound, STATUS.md + userprompt.md written
- [x] **Leadership** — All 4 agents spawned + reported in
- [ ] **Specification**
- [ ] **Implementation**
- [ ] **Testing**
- [ ] **Documentation**
- [ ] **Sign-Off**

## Engine Findings

### Bug found + fixed in `claudechic/mcp.py:1145-1151`
- **Symptom:** `get_phase` listed `tutorial:echo_injection` and counted all rules even when active workflow was `project-team`.
- **Root cause:** Display-layer in `mcp.py` did not mirror the runtime namespace filter in `guardrails/hooks.py:91`.
- **Fix:** Added `ns == "global" or ns == active_wf` filter; split count into `N active (M inactive)`.
- **Verdict:** UX bug only — runtime hook already filtered, so no functional effect.
- **Tests added:** 4 tests in `tests/test_artifact_dir.py` (new section "get_phase MCP tool — namespace filter"). All pass; `pytest -k "workflow or mcp or phase"` -> 119 passed.
- **Note:** Fix is on disk; running session still uses cached module (Python doesn't hot-reload). All 4 Leadership agents + Implementer confirmed live `get_phase` still shows old format.

### Spawn / role-injection behavior
- All 5 agents (Implementer + 4 Leadership) received **only `<role>/identity.md`** at spawn, regardless of active phase.
- Phase-specific overlays (`<role>/specification.md`, `<role>/implementation.md`, etc.) exist on disk but were NOT applied at spawn time.
- Hypothesis (Composability's): phase overlays are applied later when the engine advances phase. Untested in this run.
- All MCP tools (`whoami`, `get_phase`, `get_artifact_dir`) work correctly across all 5 agents.

### Workflow advance
- `vision -> setup -> leadership` advanced cleanly via `mcp__chic__advance_phase`.
- Phase instructions delivered correctly to coordinator at each transition.

## Notes

This run is a workflow-engine validation, not a real feature build. Subsequent phases may be exercised lightly or skipped at user direction.
