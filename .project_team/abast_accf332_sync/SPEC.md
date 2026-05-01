# Specification -- abast_accf332_sync

## Goal

Land an **agent-self-awareness substrate** in claudechic, derived from
abast's `accf332` cluster: each agent (main and sub-agent) knows its
own paths, role, compute budget, and the rules + advance-checks that
govern it -- without trial-and-error discovery and without an SDK
reconnect at workflow activation.

Six components are in scope. Four sit on existing claudechic
infrastructure; two are clean adoptions from `abast/main`.

---

## Component A. Workflow template variables (engine seam)

### WHAT

A new template-variable substitution mechanism in the workflow engine,
plus an engine-level `cwd` default for advance-check command execution,
plus a two-pass auto-then-manual check execution order.

Three discrete sub-units:

- **A1**: a single new variable `${WORKFLOW_ROOT}` substituted in
  workflow YAML manifests at run time. Resolves to the main agent's
  cwd. Syntax `${VAR}` (braced).
- **A3**: at the engine level, advance-check command-style checks
  receive `cwd` from the workflow root via
  `params.setdefault("cwd", workflow_root)`. Requires matching
  `CommandOutputCheck` ctor + factory to accept the param (~60 LOC
  including the `_resolve_against` helper and per-check kwargs;
  not in `accf332`; see Dependencies).
- **A4**: advance-check executor runs all auto-checks first, then
  any explicitly declared manual checks. Independent improvement.

Out of scope (will NOT ship from `accf332`'s A bundle):

- A2: `$STATE_DIR` token, `claudechic/paths.py`, `compute_state_dir`,
  `~/.claudechic/workflow_library/<key>/<id>/`. Superseded by our
  existing `set_artifact_dir` MCP tool.
- abast's bare `$VAR` syntax. Renamed to `${VAR}` on import.
- abast's Python identifier `workflow_root` (one-letter collision with
  our `workflows_dir`). Rename to `project_root` on import.

### WHY

- **User**: workflow YAML can write `${WORKFLOW_ROOT}/.git/HEAD` and
  the engine resolves it; sub-agent advance_phase calls from worktree
  subdirectories stop false-failing because relative paths now resolve
  against the workflow root instead of sub-agent cwd.
- **Agent**: an agent's prompt contains absolute path references
  post-substitution, baked into instructions, not resolved at runtime.

### Files

- `claudechic/workflows/engine.py`
- `claudechic/workflows/loader.py`
- `claudechic/workflows/agent_folders.py`
- `claudechic/checks/builtins.py` (for A3 -- ctor + factory; ~60 LOC, sourced from `003408a`)

### Interfaces / contracts

- **Token**: `${WORKFLOW_ROOT}` -- braced. The engine's substitution
  resolver expands at run time -- specifically, in advance-check
  param expansion (`engine._run_single_check`) and in agent-prompt
  assembly (`assemble_phase_prompt` / `assemble_constraints_block`).
  No manifest-time substitution; YAML loads with the literal token
  intact.
- **`CommandOutputCheck.__init__(command, pattern, cwd=None, base_dir=None)`**
  -- new optional `cwd` and `base_dir` kwargs. Factory respects
  `params.get("cwd")` if present; falls back to engine default
  (workflow root) via `setdefault`.
- **Two-pass executor**: in `engine.py::execute_advance_checks`,
  partition by manual-flag, run auto pass first, then manual pass.

### Constraints

- All substituted output remains string-typed.
- Convergence on `${VAR}` syntax across the codebase. Worktree path
  template (`${repo_name}`/`${branch_name}`) and Group E
  `${CLAUDECHIC_ARTIFACT_DIR}` already use braced; A1's import-time
  rename brings abast's tokens in line.
- A2 stays out: agent must have ONE answer to "where is my scratch?"
  not two. Existing `${CLAUDECHIC_ARTIFACT_DIR}` is the canonical answer.

### Dependencies

- A1, A4: independent of other components.
- A3 requires a ~60-line ctor + factory diff in
  `claudechic/checks/builtins.py` that is **NOT in `accf332`**. Per
  locked Decision 6: port the diff inline as part of A3 adoption in
  this run; the rest of the abast guardrail-messaging fix it comes
  from will be reapplied separately as a follow-up scope.
- `8f99f03` supplies tests for A1 + A3 + A4. Cherry-pick the relevant
  tests with each slice.

---

## Component B. Dynamic role identity (agent_type primitive)

### WHAT

A queryable per-agent runtime self-identity attribute, mutated on
workflow activation/deactivation, persisted across `/compact`,
exposed in env and propagated to the SDK.

Five discrete sub-units:

- **B1**: `DEFAULT_ROLE = "default"` sentinel constant in
  `claudechic/agent.py` (next to `Agent.agent_type`).
  `claudechic/workflows/agent_folders.py` and other workflow code
  import it from `agent.py`. Replaces `None`/empty string ad-hoc
  usage as "no role set."
- **B2**: `Agent.agent_type` instance attribute, default
  `DEFAULT_ROLE`, set in `Agent.__init__`. Public read.
- **B3**: in `app.py::_activate_workflow`, mutate the active agent's
  `agent_type` to the workflow's `main_role`; in
  `_deactivate_workflow` and `_restore_workflow_from_session`, restore
  to `DEFAULT_ROLE`. Hand-merged into existing methods (do not take
  the +282 patch wholesale).
- **B4**: thread `agent=` kwarg through
  `_make_options` / `_merged_hooks` / `_guardrail_hooks`. Hook
  closures capture `lambda: agent.agent_type` instead of the current
  manifest-bound `lambda: self._workflow_engine.manifest.main_role`.
  Single-site closure binding swap.
- **B5**: `loader.py` validation rejects manifests where
  `main_role: default`. ~5 LOC.

### WHY

- **User**: activating a workflow promotes the main agent to its role
  without an SDK reconnect; deactivating restores the default; role
  exposed via `CLAUDE_AGENT_ROLE` env var; role survives `/compact`.
- **Agent**: gains a queryable runtime self-identity (`agent.agent_type`)
  that is the substrate component D queries to compute "rules that
  apply to me". Without B, the agent's identity exists only in a
  workflow-side label, breaking 7 of 8 downstream consumption sites.

### Files

- `claudechic/agent.py` (B1: `DEFAULT_ROLE` constant; B2: `Agent.agent_type` attr)
- `claudechic/workflows/agent_folders.py` (imports `DEFAULT_ROLE` from `agent.py`)
- `claudechic/app.py` (B3, B4 -- surgical edits)
- `claudechic/agent_manager.py` (B4 -- options-factory reads live `agent.agent_type`)
- `claudechic/workflows/loader.py` (B5)

### Interfaces / contracts

- **`DEFAULT_ROLE: Literal["default"]`** in `agent.py`. Public.
  Imported by `workflows/agent_folders.py` and other workflow code.
- **`Agent.agent_type: str`** instance attr. Default `DEFAULT_ROLE`.
  Mutated only by `_activate_workflow` / `_deactivate_workflow` /
  `_restore_workflow_from_session`. Read by `_make_options`,
  `_merged_hooks`, `_guardrail_hooks`, env propagation, and (later)
  Component D's projection.
- **Env var `CLAUDE_AGENT_ROLE`** carries the live `agent_type` value
  to the model on every `_make_options` call.
- **Hook closure shape**: `lambda: agent.agent_type` (B4) replaces
  `lambda: self._workflow_engine.manifest.main_role` at one site.

### Constraints

- B3 + B4 must land **atomically** with `8f99f03`'s test rewrites.
  Our `a743423` test calls `_merged_hooks(agent_type=None)` which
  under abast's signature falls back to `role=None`.
- Preserve `_token_store = OverrideTokenStore()` at `app.py:1655`
  through any B3 hand-merge (independent bug-fix from `ec604bc`).
- No wholesale cherry-pick of the +282 `app.py` patch from `accf332`.
  Engine-seam axis estimates B at ~32% of that delta (~90 lines);
  surgical inserts only.

### Dependencies

- B1 unblocks the `1d3f824` F401 lint that previously triggered our
  `ec604bc` revert (B1 has 7+ callers post-adoption).
- B2 supplies the runtime identity primitive that B3, B4, and
  Component D's projection depend on.
- B3 depends on B2.
- B4 depends on B2, B3.
- B5 is independent.
- Test sequencing: B3 + B4 + 8f99f03's 6 phase-injection tests must
  land in one merge.

---

## Component C. Per-agent thinking budget (effort cycling)

### WHAT

A footer widget that cycles the agent's thinking-budget level
(low/medium/high/max), plumbed end-to-end into the SDK.

Three sub-units:

- **C1**: an `Agent.effort: Literal["low","medium","high","max"]`
  instance attribute, default `"high"`, plumbed through
  `_make_options(agent=)` into `ClaudeAgentOptions(effort=...)`.
  `"max"` is Opus-only; non-Opus models snap to `"medium"` on model
  change.
- **C2**: an `EffortLabel` widget in
  `claudechic/widgets/layout/footer.py` that displays the current
  agent's effort and, on click, cycles to the next valid level for
  the current model (`"max"` is Opus-only; non-Opus models snap to
  `"medium"` on model change). **On-screen label uses "effort" verbatim
  per SDK vocabulary** (locked decision).
- **C3** (small follow-up; ~30 LOC): persistence to `settings.json`
  so the level survives restart.

### WHY

- **User**: a clickable footer label lets the user step the SDK's
  thinking-budget knob mid-session; level snaps to a valid range
  when the model changes.
- **Agent**: each `Agent` instance carries a thinking-budget level
  (`agent.effort`) read on every SDK connect and passed via
  `--effort <level>` to the Claude Code subprocess. Different agents
  in the multi-agent UI can run with different budgets simultaneously.

### Files

- `claudechic/agent.py` (C1)
- `claudechic/widgets/layout/footer.py` (C2)
- `claudechic/app.py` (C2 wiring; coordinator picks C-related
  ~25-30 lines from `accf332`'s `app.py` +282)
- `claudechic/widgets/__init__.py` (re-exports)
- `claudechic/styles.tcss` (+3 lines)
- `claudechic/config.py` and `claudechic/screens/settings.py` (C3, follow-up)

### Interfaces / contracts

- **`Agent.effort: Literal["low","medium","high","max"]`** -- public read.
  `"max"` is Opus-only; non-Opus models snap to `"medium"` on model change.
- **SDK propagation**: `_make_options(agent=)` reads
  `agent.effort` live; passed to `ClaudeAgentOptions(effort=...)`;
  the SDK subprocess transport appends `--effort <level>` to argv
  (verified end-to-end in `claude_agent_sdk/_internal/transport/subprocess_cli.py`).
- **Widget label text**: see User decisions required for the
  user-facing string. Internal symbol `EffortLabel` may rename if the
  user picks (b) or (c).
- **Footer layout (final)**: `ModelLabel . EffortLabel . PermissionModeLabel . InfoLabel . SettingsLabel`.
  Preserve our existing `SettingsLabel`. NO `GuardrailsLabel` slot
  (Component D ships no footer widget).

### Constraints

- On-screen label text matches SDK vocabulary verbatim ("effort"
  not "thinking" or "quality"). User locked this -- do not paraphrase.
- Persistence (C3) is a small follow-up but a real functional gap if
  skipped: cost-conscious users on `low` lose their setting on
  restart.

### Dependencies

- C1, C2 independent of A, B, D, E.
- C3 (persistence) depends on C1.
- C requires the rename `${WORKFLOW_ROOT}` etc. from A1 only if
  workflow YAML refers to effort, which it does not. So C is
  effectively decoupled.

---

## Component D. guardrails UI

(reframed by the user 2026-04-29 as agent-aware constraint
visibility, NOT a user-facing modal)

### WHAT

The agent's view of "rules and advance-checks that apply to me right
now," delivered via two channels:

1. A **markdown `## Constraints` block** appended to every agent's
   launch prompt, listing rules and advance-checks scoped to the
   agent's role + phase. Injected at five sites: main agent
   activation, sub-agent spawn, main agent phase-advance, sub-agent
   phase-advance broadcast, post-compact.
2. **MCP surface that COMPOSES four narrow tools**, not one
   monolith:
   - **`mcp__chic__whoami`** -- existing, narrow, retained as-is.
   - **`mcp__chic__get_phase`** -- existing, kept narrow (workflow
     id, phase id, next phase, progress, loader errors). Rule
     count line is removed since the per-agent projection lives
     in `get_applicable_rules`.
   - **`mcp__chic__get_applicable_rules(agent_name?, include_skipped?)`**
     -- NEW, narrow. Returns the role+phase scoped projection of
     rules and advance-checks as markdown.
   - **`mcp__chic__get_agent_info(agent_name?)`** -- NEW,
     aggregator. Internally calls the three narrow tools above and
     returns a unified markdown report (identity, session,
     workflow+phase, applicable rules + advance-checks, loader
     errors). Convenience tool; no logic of its own beyond
     assembly.

Sub-units:

- **D1 (data projection -- rules)**: adopt
  `claudechic/guardrails/digest.py` from `abast/main` verbatim
  (~128 LOC, clean leaf, sibling-only imports, zero collision on
  sprustonlab base). Provides
  `compute_digest(loader, active_workflow, agent_role, current_phase, disabled_rules) -> list[GuardrailEntry]`.
  Includes annotated `active: bool` and `skip_reason: str | None`
  fields used by `include_skipped=True`.
- **D2 (data projection -- advance-checks)**: build a sibling
  `compute_advance_checks_digest(engine, phase_id) -> list[AdvanceCheckEntry]`
  (~30 LOC; not present on abast's side; new on sprustonlab).
- **D3 (markdown formatter)**: `assemble_constraints_block(loader, role, phase) -> str`
  in `claudechic/workflows/agent_folders.py` (~25 LOC). Pure
  function, no I/O. Output goes into the launch prompt at the five
  injection sites (via `assemble_agent_prompt`, see D5) and into
  `get_applicable_rules`'s response.
- **D4 (MCP surface)**: in `claudechic/mcp.py`:
  - Add `get_applicable_rules`. ~35 LOC.
  - Add `get_agent_info` aggregator. ~30 LOC (mostly orchestration).
  - Remove the rule-count line from `get_phase`'s output (the
    per-agent projection now lives in `get_applicable_rules`).
    `get_phase` itself is retained narrow; do NOT delete or
    deprecate.
  - Markdown return on all tools (model reads directly; not JSON).
- **D5 (prompt injection)**: hook the constraints block into the
  five existing in-memory phase-prompt delivery sites added by
  sprustonlab's awareness work. All five flow through
  `_send_to_active_agent` (or its fire-and-forget sibling for the
  broadcast) and dispatch through `assemble_phase_prompt`:
  - main agent activation in `claudechic/app.py::_activate_workflow` (line 1787; assembly at line 1933, dispatch at line 1941)
  - sub-agent spawn in `claudechic/mcp.py::spawn_agent` (lines 277-307)
  - main agent phase-advance in `claudechic/app.py::_inject_phase_prompt_to_main_agent` (line 2165)
  - sub-agent phase-advance broadcast in `claudechic/mcp.py::_make_advance_phase` (broadcast loop over typed sub-agents on `advance_phase`)
  - post-compact in `claudechic/workflows/agent_folders.py::create_post_compact_hook`

  All five sites call a single helper
  `assemble_agent_prompt(role, phase, loader, ...) -> str` that
  composes `assemble_phase_prompt` output with
  `assemble_constraints_block`. The helper IS the contract; the five
  sites do not concat by hand.

- **D6 (source-of-truth alignment, prerequisite)**: before D1-D5
  land, align the rule resolution path so the hook layer
  (`hooks.py`, reading raw `loader.load()`) and the registry layer
  (`get_phase` and friends, reading filtered `_load_result`) agree
  on which rules are active. Without this, the agent's prompt and
  the hook fire on different rule sets — a new bug class. This is
  the implementer's first concrete step; do not ship D-render or
  D-mcp on top of the inconsistent foundation.

The original abast UI surface is **NOT in scope**:

- `claudechic/widgets/modals/guardrails.py` (the modal)
- `_disabled_rules` runtime in-memory store
- footer "guardrails" button + label
- the `a60e3fe` "not yet implemented" stub

### WHY

- **User**: no new modal or footer button. User keeps managing
  persistent disables via `/settings` and `disabled_ids`. Agents
  become more useful because they self-correct earlier.
- **Agent**: receives a `## Constraints` block in its launch prompt
  listing the rules and advance-checks that apply to it, scoped by
  role + phase. Can call `mcp__chic__get_applicable_rules` mid-session
  to re-query when state may have changed.

### Files

- `claudechic/guardrails/digest.py` (D1: created by adoption OR by
  build; user picks path -- see decisions)
- `claudechic/guardrails/checks_digest.py` (D2: new; not present on abast)
- `claudechic/workflows/agent_folders.py` (D3: new function)
- `claudechic/mcp.py` (D4: add `get_applicable_rules` + `get_agent_info`,
  narrow `get_phase` by removing rule-count line, retain `whoami` unchanged;
  D5: two inject sites -- sub-agent spawn in `spawn_agent`, sub-agent
  phase-advance broadcast in `_make_advance_phase`)
- `claudechic/app.py` (D5: two inject sites -- main agent activation
  in `_activate_workflow`, main agent phase-advance in
  `_inject_phase_prompt_to_main_agent`)

### Interfaces / contracts

- **`compute_digest`** (from adopted `digest.py`): signature
  `compute_digest(loader, active_workflow, agent_role, current_phase, disabled_rules) -> list[GuardrailEntry]`.
  `GuardrailEntry` carries id, namespace, kind, trigger, enforcement,
  message, active, skip_reason, role+phase scopes.
- **`compute_advance_checks_digest(engine: WorkflowEngine, phase_id: str | None = None) -> list[AdvanceCheckEntry]`**
  -- new sibling. Returns checks for the active phase when `phase_id`
  is omitted.
- **`assemble_constraints_block(loader, role: str, phase: str | None) -> str`**
  -- pure function. Output:

  ```
  ## Constraints

  ### Rules ({n_active} active)

  | id | enforcement | trigger | message |
  |----|-------------|---------|---------|
  | global:no_bare_pytest | warn | Bash matching ^pytest\b | use uv run pytest ... |
  | ...

  ### Advance checks ({phase_id})

  - <id> -- <command> (manual? yes/no)
  ```

  When called from `get_agent_info(include_skipped=True)`, the rules
  table gains a `skip_reason` column and inactive rows are included.

- **MCP surface (four narrow tools that compose):**

  - **`whoami() -> str`** -- existing, retained verbatim. Degenerate
    one-shot identity. Unchanged.

  - **`get_phase() -> str`** -- existing, kept narrow. Returns
    workflow id, phase id, next phase, progress (idx/total), artifact
    dir, loader errors. **Modified only by removal of the rule-count
    summary line**, which moves to `get_applicable_rules` (the
    per-agent role+phase projection lives there). `get_phase` is NOT
    deprecated, NOT deleted; existing callers keep working.

  - **`get_applicable_rules(agent_name: str | None = None, include_skipped: bool = False) -> str`**
    -- NEW, narrow. Closure-bound caller resolution (same pattern as
    `whoami` / `spawn_agent`). When `agent_name` omitted -> the
    calling agent's name; otherwise looked up via
    `agent_mgr.find_by_name`. Returns the markdown produced by
    `assemble_constraints_block(loader, role, phase)`: the
    `## Constraints` block with `### Rules` (role+phase scoped via
    `compute_digest`) and `### Advance checks` (from
    `compute_advance_checks_digest`). `include_skipped=True` adds a
    `skip_reason` column and inactive rows.

  - **`get_agent_info(agent_name: str | None = None) -> str`** -- NEW,
    aggregator. Internally calls `whoami`, `get_phase`, and
    `get_applicable_rules` (resolving the same `agent_name` argument
    through each) and concatenates their markdown into a single
    report with stable section order:

    1. `# Agent: <name>`
    2. `## Identity` -- from `whoami` (name, role/`agent_type`, cwd,
       model, effort, worktree, status)
    3. `## Session` -- jsonl path, session id, last compaction
       summary (first 200 chars)
    4. `## Active workflow + phase` -- from `get_phase` (workflow id,
       phase, next phase, progress, artifact dir)
    5. `## Applicable rules and advance-checks` -- from
       `get_applicable_rules`
    6. `## Loader errors` -- from `get_phase`

    The aggregator owns no rule-resolution or phase-resolution logic
    of its own; it is purely an assembly tool over the three narrow
    tools. Callers that want one of the sub-views call the narrow
    tool directly.

- **Inject contract**: the five inject sites (main agent activation,
  sub-agent spawn, main agent phase-advance, sub-agent phase-advance
  broadcast, post-compact) all call the
  `assemble_agent_prompt(role, phase, loader, ...) -> str` helper
  (D5). The helper composes `assemble_phase_prompt` output with
  `assemble_constraints_block` via the
  `f"{phase_prompt}\n\n{constraints_block}"` pattern. The
  constraints block always begins with `## Constraints`. The five
  sites do not concat by hand -- the helper is the single point of
  composition; future inject sites call it too.

### Constraints

Four compositional landing conditions (binding regardless of D1 path):

1. **Source-of-truth alignment** -- ship as D6 prerequisite (see
   sub-units above). Before any of D1-D5 lands, the hook layer and
   registry layer must agree on which rules are active, so the
   agent's `## Constraints` block matches what hooks actually fire
   on.
2. **Refresh policy**: pick ONE consistent story for "when does the
   constraints block get recomputed?". Recommended: at each of the
   five inject sites (activation / spawn / phase-advance / broadcast
   / post-compact), and live on every `get_applicable_rules` MCP
   call. Document the choice.
3. **Sub-agent identity**: statically bound at spawn -- per-agent
   projection is the natural shape. No work needed.
4. **`get_phase` rule-count line removal**: `get_phase` currently
   emits "Rules: N active (M inactive)" applying only the namespace
   filter, not role/phase scope. The per-agent projection moves to
   `get_applicable_rules` (D4); `get_phase` loses the rule-count line
   in the same change to avoid two tools reporting different "active"
   counts.

### Dependencies

- B supplies the runtime identity primitive (`agent.agent_type`)
  that D's projection requires. Order: B before D5, or D5 ships only
  the main agent activation site (which has identity via the
  existing `main_role` closure, `a743423`-confirmed) and lights up
  the other four sites as B lands. Implementer picks the order.
- D lands on tested machinery: 9 tests in
  `tests/test_phase_prompt_delivery.py` cover the inject sites'
  delivery primitive (`_send_to_active_agent`).
- D and engine-seam (A, B) can land in parallel where their files
  don't overlap.

---

## Component E. pytest-needs-timeout warn rule

### WHAT

A new warn-level guardrail rule in `defaults/global/rules.yaml`,
appended manually (not cherry-picked -- abast's diff context refers to
a `no_pip_install` rule we don't have). Regex hardened before commit.

### WHY

- **User**: when an agent runs `pytest` without `--timeout`, the warn
  channel surfaces a nudge; the user sees the rule fire and the agent
  retries with a timeout.
- **Agent**: first concrete data row in its injected `## Constraints`
  block: "when running pytest, include --timeout=N to avoid hangs."
  The agent learns the constraint pre-failure rather than rediscovering
  it through a hung test.

### Files

- `claudechic/defaults/global/rules.yaml`

### Interfaces / contracts

- Rule shape (YAML):
  ```yaml
  - id: pytest_needs_timeout
    namespace: global
    enforcement: warn
    trigger:
      tool: Bash
      pattern: "<hardened pytest invocation regex>"
    message: "use --timeout=N (default 30) to avoid hung tests"
  ```
- The regex must match real `pytest` command invocations and **not**
  match `grep` / `rg` / `cat` / `head` / `tail` / docs / comments
  containing the literal string `pytest`. Skeptic empirically verified
  the existing `no_bare_pytest` rule false-positives on
  `grep -c "pytest"`; the new rule must not.

### Constraints

- Manual append, not cherry-pick.
- Regex hardening is mandatory; ship without and the warn channel
  pollutes and trains the agent to ignore warns.

### Dependencies

- Independent. Adopts cleanly without A, B, C, D.
- Becomes most valuable in the agent's view if Component D is also
  adopted: D's constraints block surfaces the rule pre-failure.

---

## Component F. Modal restructure / diagnostics deletion (architectural by-product)

### WHAT

Mechanical adoption of:

- New `widgets/modals/computer_info.py` (clean rewrite, +68 LOC).
- New scrollable `InfoSection` in `widgets/modals/base.py` (+66 LOC).
- Deletion of `widgets/modals/diagnostics.py` (-194 LOC).
- Migration of 4 reference sites: `widgets/modals/__init__.py`
  exports, `app.py` lines 3641-3648 handler block, `CLAUDE.md`
  line 150.

### WHY

- **User**: the existing `session_info` button now consolidates JSONL
  path + last-compaction summary in one scrollable modal. Zero info
  loss vs the deleted diagnostics modal.
- **Agent**: none -- agent does not consult read-only viewers.

### Files

- `claudechic/widgets/modals/computer_info.py` (clean apply)
- `claudechic/widgets/modals/base.py` (clean apply)
- `claudechic/widgets/modals/__init__.py` (export update)
- `claudechic/widgets/modals/diagnostics.py` (delete)
- `claudechic/app.py` (4 reference sites)
- `CLAUDE.md` (file-map line)

### Interfaces / contracts

- `ComputerInfoModal` absorbs `jsonl_path` + `last_compaction` readers
  verbatim from `diagnostics.py`. Public surface unchanged for
  callers that use `ComputerInfoModal`; callers of `DiagnosticsModal`
  must migrate.

### Constraints

- ZERO drift on `computer_info.py` and `base.py` since merge-base
  `285b4d1` (verified). Clean apply expected.

### Dependencies

- Independent of A, B, C, D, E. Lands first per integration plan.

---

## Decisions locked (2026-04-30)

| # | Decision | Locked outcome |
|---|----------|----------------|
| 1 | Per-component go/no-go | Adopt or adapt all six components (A, B, C, D, E, F) per team recommendation. |
| 2 | C widget on-screen label | Verbatim "effort" -- match SDK vocabulary. No rename, no tooltip-only paraphrase. (Internal `EffortLabel` symbol unchanged.) |
| 3 | D1 implementation path | **Adopt-abast-digest** -- adopt `claudechic/guardrails/digest.py` from `abast/main` verbatim (~128 LOC) + extend (~135 LOC) for ~263 LOC total. |
| 4 | D injection shape | Proactive injection at all 5 sites (activation / spawn / phase-advance / broadcast / post-compact) + on-demand mid-session via MCP. |
| 5 | D MCP placement | Four narrow tools that compose: `whoami` (retained), `get_phase` (retained, narrow -- only the rule-count line is removed), new `get_applicable_rules` (role+phase scoped projection), new `get_agent_info` (aggregator that internally calls the three narrow tools and concatenates their markdown). `get_phase` is NOT deprecated. |
| 6 | Out-of-cluster follow-ups | (a) **abast guardrail-and-advance-check messaging fix** -- reapply (full re-application as a follow-up scope; the ~60-line `checks/builtins.py` slice still ports inline as part of A3 in this run). (b) **abast MCP-tool rename refactor** -- close out (sprustonlab already has equivalent functionality). |

### Naming conventions (going forward)

- Use `abast` and `sprustonlab` as fork identifiers, not "ours" / "theirs".
- Use descriptive labels for follow-ups (e.g. "abast guardrail-messaging fix")
  rather than abstract numbering.
- Avoid commit-hash-only references where a one-line description fits
  the slot.

---

## Out of scope (this run)

- The original `accf332` modal (`widgets/modals/guardrails.py`,
  `GuardrailsModal` class, footer "guardrails" button label).
- `_disabled_rules` runtime in-memory store.
- The `a60e3fe` modal walk-back stub.
- A2 (`paths.py`, `compute_state_dir`,
  `~/.claudechic/workflow_library/`).
- All abast commits outside the four-commit cluster except where
  explicitly cited above as a dependency or context.

## Follow-up scope (after this run lands)

- **abast guardrail-and-advance-check messaging fix -- reapply.**
  sprustonlab previously cherry-picked this fix and reverted it
  because three prerequisites were missing. After this run lands,
  two of those prerequisites are introduced by Component B
  (`DEFAULT_ROLE` sentinel + `main_role` promotion) and the third is
  already on sprustonlab base; reapplication is safe. The ~60-line
  `claudechic/checks/builtins.py` slice ports inline with A3 in
  *this* run; the rest of the fix lands in the follow-up. Open a
  scoped follow-up after Sign-Off here.

## Closed out (will not be revisited)

- **abast MCP-tool rename refactor** (`tell_agent` merged into
  `ask_agent`, then `ask_agent` renamed to `message_agent`).
  sprustonlab already has equivalent functionality under
  `message_agent`; no adoption value.

Detailed rationale, alternatives considered and rejected, historical
context, the full divergence map, the 4-commit cluster identification
narrative, and the "what NOT to do" list are in `SPEC_APPENDIX.md`.
