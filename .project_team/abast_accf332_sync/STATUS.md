# STATUS -- abast_accf332_sync

**Last updated:** 2026-04-29 (Setup phase)
**Coordinator:** claudechic
**Working directory:** `/groups/spruston/home/moharb/claudechic`
**Artifact directory:** `/groups/spruston/home/moharb/claudechic/.project_team/abast_accf332_sync`

---

## Current phase

`project-team:setup` (entering Leadership next)

## Phase progression

| # | Phase | Status |
|---|-------|--------|
| 1 | vision | done (approved) |
| 2 | setup | in progress |
| 3 | leadership | pending |
| 4 | specification * | pending |
| 5 | implementation * | pending |
| 6 | testing-vision | pending |
| 7 | testing-specification | pending |
| 8 | testing-implementation | pending |
| 9 | documentation | pending |
| 10 | signoff * | pending |

`*` = User Checkpoint

---

## Vision Summary (approved)

**Goal:** Team-driven investigation of the four-commit cluster on
`abast/main` ending at/around `accf332` ("workflow template variables,
dynamic roles, effort cycling, and guardrails UI") to determine intent
and recommend whether/how to integrate.

**Open questions (team decides; user has final call):**

1. What is each of the 4 commits about?
2. What is the intent across the cluster?
3. Should we pick it up?
4. Can we reimplement on our base?

**Per-feature outcome categories:** adopt / adapt / skip / partial.

**Scope guard:** stay strictly inside the 4-commit cluster; flag (do not
chase) other interesting abast commits encountered in passing.

---

## Repo facts (verified by coordinator in Setup)

- Branch: `main`
- Remotes:
  - `origin` -> `https://github.com/sprustonlab/claudechic.git`
  - `abast` -> `https://github.com/abast/claudechic.git`
- `abast/main` resolves to `7dcd488e17396a90622585cd5c877622e757fc42`
- `accf332` resolves to `accf332df9e3f1a9c13e5951bec1a064973b6c96`
- Working tree status:
  - untracked: `.ai-docs/fork-divergence-2026-04-29.md`
  - untracked: `.claudechic/`
  - no staged or unstaged modifications

## Pre-existing context for the team to consider

- `.ai-docs/fork-divergence-2026-04-29.md` (untracked, dated today) --
  possible prior fork analysis. Treat as input, not as authority.
- `.project_team/issue_23_path_eval/abast_executive_summary.md`
- `.project_team/issue_23_path_eval/fork_diff_report.md`
- `.project_team/issue_23_path_eval/RECOMMENDATION.md`

These pre-date this run; the team should evaluate whether they are still
accurate (the abast HEAD has moved since they were written) and either
build on them or supersede them.

---

## Decisions / open issues

### Cluster boundary -- DECIDED (Leadership phase)

The 4-commit cluster is:

| # | SHA | Type | Subject |
|---|-----|------|---------|
| 1 | `accf332df9e3f1a9c13e5951bec1a064973b6c96` | feat | workflow template variables, dynamic roles, effort cycling, guardrails UI |
| 2 | `8f99f03` | test | tests for template variables / engine checks / widget refactor |
| 3 | `2f6ba2e` | docs | file-map update |
| 4 | `a60e3fe` | chore | stub out guardrails modal with not-yet-implemented notice |

Source: historian (factual) + terminology (independent identification, same 4).
Composability proposed `003408a` instead of `a60e3fe`. Resolution: `003408a`
is treated as an OUT-OF-CLUSTER FLAGGED DEPENDENCY rather than part of the
cluster itself; historian will investigate whether `accf332` has a hard
dependency on it, and whether re-applying it would re-trigger our prior
revert (`18061ec`).

The cluster is non-contiguous on `abast/main`: between commits 3 and 4 sit
two unrelated MCP-tool refactors (`1d6d432`, `ff1c5ae`) which are FLAGGED
but not part of the cluster.

### Flagged out-of-cluster commits (do not chase)

- `003408a` (abast) -- precursor fix; we cherry-picked as `8abb2f9`, reverted
  as `18061ec`. Possible hard dep of `accf332`. Historian to surface revert
  reason from our side.
- `1d3f824` (our side) -- `DEFAULT_ROLE` forward-port, reverted as `ec604bc`.
  May be re-required by `accf332`'s dynamic-role machinery.
- `1d6d432` + `ff1c5ae` (abast) -- MCP-tool refactor (tell_agent merge,
  ask_agent rename). Sit between cluster commits 3 and 4; matter for
  cherry-pick ordering.
- `7dcd488` (abast HEAD) -- "Generalprobe standard"; flagged only.

### Vision-Summary deltas on record (UserAlignment)

- We widened the answer space from binary ("pick up?" / "reimplement?") to
  4 outcome categories (`adopt / adapt / skip / partial`). User said "leave
  these questions open for the team to decide" so this stands; defer to
  binary if user pushes back.
- "Sync" framing in the user prompt means the implicit destination is
  integration, not pure analysis -- the team should not slide into
  pure-review mode.

### Must-answer list for the final report (UserAlignment)

Use the user's exact questions as section headers:

1. "What is it about?" -- per-commit narrative for each of the 4.
2. "What is the intent?" -- cluster-level intent (the WHY).
3. "Should we pick it up here?" -- per-feature recommendation
   (workflow template variables / dynamic roles / effort cycling /
   guardrails UI), each tagged adopt/adapt/skip/partial with reasoning.
4. "Can we reimplement on our base?" -- per-feature feasibility +
   architecture conflicts + rough effort estimate.

Plus 3 addenda: cluster identification (the 4 SHAs and how we picked
them), integration plan (sequencing for adopt/adapt items), and the
flagged-not-chased list above.

### Specification-phase agent plan (Composability)

3 axis-agents (no agents for axis D content or axis E tests/docs --
those fall out of the others):

1. **engine-seam** -- covers sub-features (1) workflow template variables
   and (2) dynamic roles. Touches `workflows/engine.py`,
   `workflows/loader.py`, `workflows/agent_folders.py`. Highest collision
   risk vs our Group C 3-tier loader and Group E
   `${CLAUDECHIC_ARTIFACT_DIR}` substitution. Must answer: ONE
   substitution mechanism or two clean axes?
2. **guardrails-seam** -- covers sub-features (4) guardrails UI and
   (5, flagged) the precursor `003408a` advance-check fix. Touches
   `guardrails/`, `checks/`, `mcp.py`. Must answer: are the data side
   (digest, rules.yaml) and UI side (modal, footer) cleanly separable?
3. **UI-surface** -- covers sub-feature (3) effort cycling. Touches
   `widgets/modals/`, `widgets/layout/footer.py`, `app.py`. Must answer:
   is effort-cycling self-contained, and what does the
   `widgets/modals/diagnostics.py` deletion break on our base?

### Skeptic's standing falsification questions

Any feature that gets a "yes" on Q1-Q6 should be SKIPPED (or demoted to
partial). See `.project_team/abast_accf332_sync/STATUS.md` (this file)
section "Leadership findings" below for the full Q-list.

### Terminology collision flags

- "guardrails" already has 4 surfaces; abast's UI toggle would be a 5th.
  Decide if it duplicates `disabled_ids` or is a new meaning.
- 3 different template-variable substitution mechanisms exist on our
  combined base (worktree paths, workflow YAML `${CLAUDECHIC_ARTIFACT_DIR}`,
  abast `$STATE_DIR`/`$WORKFLOW_ROOT`) with two syntaxes (`$VAR` vs
  `${VAR}`). Converge or partition.
- "dynamic role / main_role / DEFAULT_ROLE / promote / demote" need a
  single role-lifecycle vocabulary.
- `workflow_library/` (abast) vs `chicsessions/` (ours) vs artifact dir
  -- risk of a 3rd state location with overlapping purpose.

## User redirect 2026-04-29 (post-SPEC.md presentation)

The user rejected SPEC.md as written with two specific course corrections:

### Redirect 1: scope expansion

> "you made any other commit 'out of scope' instead of understanding what
> is the goals using them. please include ANY commit that is divergent
> between our repos as context."

The original scope guard ("stay strictly inside the 4-commit cluster;
flag, don't chase") was too literal. The user wants the FULL divergence
map between `abast/main` and our HEAD as **context** (not as new
investigation targets) so the team can interpret the cluster correctly.

**Action**: historian re-engaged for the divergence map (Part A: abast-only
commits since merge-base; Part B: ours-only; Part C: relevance tags
C/D/M/- per commit).

### Redirect 2: D reframed (NOT UI, agent self-awareness)

> "the point of D is NOT UI it is to make the current state of guardrail
> rules and advance checks transparent to the AGENT. If we filter into a
> dict for each agent what rules apply to it (using an MCP call) it could
> understand its role better. that should be as part of the injected
> prompt for launching an agent in claudechic"

The team's prior convergence on **D = SKIP** was based on a UI-centric
reading. The user's actual intent is:

1. **Per-agent filtering** -- a dict keyed by agent identity, listing
   rules (and advance_checks) that apply to THAT agent.
2. **MCP call** -- an agent can query "what applies to me?" at runtime.
3. **Launch-prompt injection** -- when an agent spawns, the applicable
   rules are baked into its initial prompt so it has the context from
   turn 1.

**Actions**:
- guardrails_seam re-engaged: redo the D analysis from scratch under the
  new framing; revised `(D, outcome, blocking-deps)` recommendation.
- user_alignment re-engaged: audit whether A/B/C/E were also flattened
  to user-facing-UI-first when the user may have agent-perspective
  intents implicit; update must-answer gestalt.
- composability re-engaged: architectural fit assessment for
  agent-aware rule filtering + MCP + prompt injection.

### Status

SPEC v2 presented to user 2026-04-29; rewritten 2026-04-30 in
operational format per user critique ("not actionable, define D, move
rationale to APPENDIX").

User decisions ALL LOCKED (2026-04-30):

- D1 (per-component go/no-go) -- **LOCKED**: defaults accepted (A/B/C/D/E/F all adopt or adapt per team rec).
- D2 (C label) -- **LOCKED**: option (d) keep "effort: high" verbatim per SDK vocabulary. C ships as ADOPT-as-shipped on the on-screen label; the WHAT/WHY of C unchanged.
- D3 (D1 implementation path) -- **LOCKED**: Path X = "adopt-abast-digest" (~263 LOC, including ~128 LOC adopted from `digest.py`).
- D4 (D injection shape) -- **LOCKED**: D = A+C (proactive at 3 sites + on-demand MCP via get_agent_info).
- D5 (D MCP placement) -- **LOCKED**: `get_agent_info(agent_name?, include_skipped?) -> markdown` replaces `get_phase`. Single tool returning identity + session + workflow phase + rules + advance-checks + loader errors. Migrate ~50 LOC of mechanical caller edits; `get_phase` deprecated then deleted one release later. `whoami` retained.
- D6-1 (abast guardrail-and-advance-check messaging fix) -- **LOCKED**: reapply as follow-up scope after this run lands. ~30-line `checks/builtins.py` slice ports inline with A3 in this run.
- D6-2 (abast MCP-tool rename refactor) -- **LOCKED**: closed out permanently; sprustonlab has equivalent functionality.

### Naming convention (locked, going forward)

- "abast" / "sprustonlab" instead of "theirs" / "ours".
- Descriptive labels for follow-ups; not "Follow-up 1" / "Path X".
- Avoid commit-hash-only references where a one-line description fits.

### composability architectural fit (2026-04-29) -- delivered

Full doc: `specification/composability.md` section 12.

#### Key finding: two viable paths for D-reframed

Path X (guardrails_seam): adopt `digest.py` from accf332 (~128 LOC) +
~135 LOC new. ~263 LOC total.

Path Y (composability-implied): no code reuse from accf332; build the
~20-LOC projection helper from our existing predicates
(`should_skip_for_role`, `should_skip_for_phase`, namespace check,
trigger match) + ~135 LOC new. ~155 LOC total.

Both deliver the user's reframed-D intent. User picks at synthesis.

#### Four compositional landing conditions (binding for either path)

1. **Source-of-truth inconsistency**: hooks read raw `loader.load()`;
   `get_phase`/registry read `_load_result` (filtered by project
   disables). Cleanup needed before/with this work.
2. **Refresh semantics differ across paths**: spawn-time injection
   freezes at spawn; MCP-only reflects per-call; PostCompact refreshes
   at `/compact`. Document and pick a consistent story.
3. **Sub-agent identity is statically bound at spawn** -- per-agent
   projection is the natural shape (good, no work needed).
4. **`get_phase` overstates active rules**: already emits
   "Rules: N active (M inactive)" but applies only namespace filter,
   not role/phase scope. Orthogonal cleanup.

#### MCP placement options

- (a) deepen `get_phase` (breaks existing shape)
- (b) **add `get_applicable_rules` alongside** (lowest-risk additive;
  guardrails_seam picked this)
- (c) replace `get_phase`'s rule count entirely (cleanest, breaks callers)

#### Injection design options (cost-only)

- **A** -- MCP-only (~50 LOC total). Mid-session updates for free.
- **B** -- spawn-time injection (one concat + helper). Always-current
  frozen prompt at spawn.
- **C** -- kickoff/PostCompact injection (one concat each + helper).
- **D** (= A+B) -- proactive at spawn, on-demand mid-session.

User picks A/B/C/D at synthesis.

### engine_seam B and A reframe (2026-04-29) -- delivered

Full doc: `spec_engine_seam.md` section 10.

**Verdicts unchanged; importance reframed.** B is the substrate, not a cleanup.

#### `agent.agent_type` consumption sites (source-traced)

1. `Agent.__init__` -- defaults to "default" sentinel
2. `agent_manager` options factory -- reads live
3. `_guardrail_hooks` -- returns `lambda: agent.agent_type` to PreToolUse hooks (**substrate D queries**)
4. `_merged_hooks` / post-compact -- identity persists across `/compact`
5. `_make_options` -- propagates to `CLAUDE_AGENT_ROLE` env var (**agent introspects**)
6. `_activate_workflow` / `_deactivate_workflow` / `_restore_workflow_from_session` -- the teaching event
7. (out-of-cluster, in 003408a) `mcp.py::spawn_agent` -- validates `type=`
8. (out-of-cluster, in 003408a) `mcp.py::advance_phase` -- broadcast routing by `agent_type`

#### Skeptic Q5 reverses on B under the new framing

Manifest-bound resolution cannot support per-agent identity (sub-agents
have their own roles; manifest's `main_role` is global). No simpler
80/20 alternative.

#### Tension to resolve at synthesis: D-vs-B coupling

- guardrails_seam: D-reframed does NOT depend on B; existing
  `should_skip_for_role` + our `a743423`-confirmed main_role resolution
  suffice.
- engine_seam: B is the substrate D queries (sites 3, 5, 7, 8 above).

**Resolution**: both right within their scope. D-reframed and B are
independently shippable; together they're stronger.

- D-reframed alone -> filters using main_role / static spawn-time roles.
- D-reframed + B -> filters using per-agent `agent_type`, queryable
  across `/compact`, exposed via env var, lambda-bound to PreToolUse.

#### Gestalts (per UserAlignment C8)

| | A | B |
|---|---|---|
| **User-side** | "Workflow YAML can write `${WORKFLOW_ROOT}/.git/HEAD`; sub-agent advance_phase calls from worktree subdirs stop false-failing." | "User activates project_team and continues in their main agent; coordinator-role guardrails apply, role survives `/compact`, role exposed in `CLAUDE_AGENT_ROLE` env. No reconnect." |
| **Agent-side** | "Agent's prompt contains absolute path references post-substitution: knows where its workflow root is and where to write artifacts. Paths baked into instructions." | "Agent gains a queryable runtime self-identity (`agent.agent_type`). On workflow activation it is taught its role; on deactivation restored to default; across `/compact` it remembers. This is the substrate D queries." |

#### A2 (state-location) skip reinforced

Under agent-self-awareness lens: agent needs ONE answer to "where is
my scratch?" not two. `${CLAUDECHIC_ARTIFACT_DIR}` already teaches
that.

#### Architecture calls re-affirmed

- `${VAR}` syntax convergence: affirmed (agent doesn't perceive syntax;
  explicit braces avoid greedy matches for author).
- State-location skip: affirmed.
- A3 prerequisite framing (`checks/builtins.py` ctor + factory diff,
  ~30 LOC, port inline OR via 003408a follow-up): unchanged.

### ui_surface C reframe (2026-04-29) -- delivered

Full doc: `spec_ui_surface.md` section "C reframed -- agent-perspective trace".

#### SDK consumer trace -- VERIFIED end-to-end

`agent.effort` (instance attr) -> `_make_options(agent=)` -> `ClaudeAgentOptions(effort=effort_level)` ->
`claude_agent_sdk/_internal/transport/subprocess_cli.py::_build_command` appends
`--effort <level>` to the Claude Code subprocess argv. **Verified in SDK source.**
`AgentDefinition.effort` field also exists, confirming SDK treats this as a
per-agent compute budget. Mid-session changes take effect on next response
without reconnect.

#### Gestalts (per UserAlignment C8)

- **Agent-side**: "Each Agent instance carries a thinking-budget level
  (`agent.effort`), read on every SDK connect and passed to the model via
  `--effort <level>`; different agents in the multi-agent UI can run with
  different budgets simultaneously, and mid-session changes take effect
  on the next response."
- **User-side**: "User sees a clickable footer label that lets them step
  the SDK's thinking-budget knob mid-session; level snaps to a valid
  range when the model changes."

#### Verdict: still ADAPT, framing strengthened

The on-screen label "effort" still fails the gestalt test (one of the
3 UX adaptation options needed). But the agent-side trace strengthens
the case. Two consequences:

1. Reframe user-facing copy as "per-agent thinking-budget control,"
   not "footer widget".
2. Persistence smell now reads as a **functional gap** (cost-conscious
   users on `low` lose their setting on restart), not just polish.

#### Diagnostics / modal restructure: no agent-side framing

User-only refactor. Stated explicitly per C8.

### guardrails_seam D reframe (2026-04-29) -- delivered

Full doc: `spec_guardrails_seam.md` section 11.
**Verdict flipped from SKIP to ADAPT.**

#### Design sketch

| Component | Size | Source |
|-----------|------|--------|
| `digest.py` (rules + injections projection) | ~128 LOC | **adopt verbatim** from abast |
| `compute_advance_checks_digest()` sibling | ~30 LOC | new (abast didn't ship it) |
| `mcp__chic__get_applicable_rules(agent_name?, include_skipped?)` | ~35 LOC | new in `mcp.py`; markdown return |
| `mcp__chic__get_advance_checks(phase_id?)` | ~35 LOC | new in `mcp.py`; markdown return |
| `assemble_constraints_block` formatter | ~25 LOC | new in `agent_folders.py` |
| Injection at 2 existing sites | ~10 LOC | `mcp.py::spawn_agent` lines 277-307 + `app.py::_inject_phase_prompt_to_main_agent` line 2165 |
| **Total** | **~135 LOC new + 1 file adopted** | -- |

#### Key decoupling

**D-reframed does NOT depend on B (dynamic roles).** Roles are already
statically known at spawn or set by our existing `_activate_workflow`.
The previous D-vs-B `app.py` overlap goes away.
**Engine-seam can decide on B independently.**

#### Skeptic Q1-Q6 fresh

All 6 PASS. Q4 strongly affirmative -- concrete user: every
coordinator/sub-agent in our 9 bundled workflows; concrete failure mode:
`pytest tests/foo.py` -> deny -> retry loop.

#### Open implementation-time questions

1. Constraints-block size budget (truncate at N rows? always full?).
2. Refresh policy (per turn? per phase? per agent spawn?).
3. Skipped-inclusion default (include or exclude inactive rules?).
4. Sort order (by id? by namespace? by enforcement level?).

#### Skipped pieces

Per user's "the point of D is NOT UI": SKIP the GuardrailsModal,
SKIP the footer rename, SKIP the `_disabled_rules` runtime store /
runtime-disable plumbing. Modal is dead code under this framing.

### UserAlignment audit (2026-04-29) -- delivered

The team's initial reading of the cluster as "four bundled UI/UX
features" was wrong. The cluster's coherent throughline is
**agent self-awareness**:

| Feature | Agent-side intent | Audit verdict |
|---------|-------------------|---------------|
| A | teaches the agent its paths (`${WORKFLOW_ROOT}` resolves into agent-visible prompts/check params) | maybe-missed |
| B | teaches it its role (`agent.agent_type` as queryable runtime self-identity) | **YES MISSED -- B is the mechanism that makes D possible** |
| C | teaches it its compute budget (if SDK reads `agent.effort`) | maybe-missed |
| D | teaches it which rules govern it (agent-aware rule filtering) | YES MISSED (already being redone) |
| E | first concrete data row the agent sees in its injected rules digest | YES MISSED (downstream of D) |

`a60e3fe`'s walk-back hypothesis is reframed: abast may have stubbed
the modal because the **agent-side machinery wasn't ready**, not
because the UI was buggy.

**New binding rule C8**: every per-feature recommendation must include
BOTH a user-side gestalt AND an agent-side gestalt sentence. Failure
= team has flattened the user's framing. Axis-agents producing only
user-side gestalts are blocked from the user checkpoint.

**Sync reframed**: "absorb the agent-self-awareness work", not
"merge the patches".

**Actions** (in flight):
- engine_seam re-engaged for B (acute) and A (less acute) reframing.
- ui_surface re-engaged for C `agent.effort` SDK consumer trace.
- guardrails_seam already redoing D under the new framing (will cover E too).
- composability already doing architectural fit for the agent-aware
  rule-filtering design.

### Divergence map (historian, delivered)

Full table in `historian_findings.md` section
`## Full divergence map (user-redirect 2026-04-29)`. Headlines:

- 16 abast-only commits since merge-base; 42 ours-only.
- Tag breakdown: 4C/1D/6M/5- abast; 0C/5D/16M/21- ours.

#### Critical new findings (forwarded to axis-agents)

**`a743423`** (ours, 2026-04-29) -- fixes `test_main_agent_role_resolves_to_main_role`,
**literally one of the 6 tests cited as stranded** in `18061ec`'s revert
message. **Our base has independently functional main-role-resolution
machinery separate from accf332's promotion path.** May COLLIDE with
abast's machinery rather than compose. Forwarded to engine_seam --
likely changes B's verdict shape.

**`d001e30`** (ours, +1253) -- claudechic-awareness +
**in-memory phase-prompt delivery**. **Same conceptual space as user's
D-reframe (rules-injected-into-agent-launch-prompt).** We may already
have the prompt-injection hook the user is asking for. Forwarded to
composability and guardrails_seam.

#### Other M-tagged divergent commits worth context

abast-only:
- `d55d8c0` (+6069) -- foundational `defaults/guardrails/hints/workflows`
  bundle that `accf332` builds on
- `f9c9418` (+317) -- full model ID selection (underlies effort cycling
  model-aware logic)
- `9fed0f3` -- docs on `spawn_agent type=` (role-matching concept)
- `1d6d432`, `ff1c5ae` -- MCP tool refactor (cluster commits 3-4 sit
  between these on abast/main)
- `7dcd488` -- Generalprobe testing sub-cycle

ours-only:
- `711be4c` -- Group A defaults restructure (our equivalent of abast `d55d8c0`)
- `b9023e2`, `6d7d919` -- Group B state-file relocation
- `81f0c69` (+1736) -- **Group C 3-tier loader** (origin of the +891 loader.py drift)
- `e4fa9bf` (+1112) -- **Group E `${CLAUDECHIC_ARTIFACT_DIR}` mechanism**
- `efc94ed` -- consolidates `${CLAUDECHIC_ARTIFACT_DIR}` into shared helper
- `7ac2a3b` -- chicsession-overwrite confirmation
- `178e3dc` -- restores tell_agent semantics lost in MCP rename

## Triage findings (Historian, end of Leadership phase)

Full report: `.project_team/abast_accf332_sync/historian_findings.md`.

### Headlines

1. **`accf332` alone implements all 4 named features** (A: template variables,
   B: dynamic roles, C: effort cycling, D: guardrails UI), plus a stowaway
   5th item: `pytest_needs_timeout` warn rule (call it E).

2. **`a60e3fe` partially walks back D**: stubs the guardrails button to
   "not yet implemented" but leaves `GuardrailsModal` + `digest.py` as
   orphan code on abast/main. Strong author-intent signal that the UI
   side wasn't ready.

3. **Strict dependency chain**: `accf332 -> {8f99f03, 2f6ba2e, a60e3fe}`.
   Cherry-pick order matches. Skipping `8f99f03` is not viable; skipping
   `a60e3fe` is a real choice (full modal vs. stub).

4. **Top-3 blast radius vs our base** (drift since merge-base `285b4d1`,
   our HEAD `a2c3779`):
   - `app.py`: accf332 +282 vs **our +779**. Heavy conflict expected.
   - `workflows/loader.py`: accf332 +16 vs **our +891**. Mechanical merge
     in unfamiliar terrain.
   - `workflows/engine.py`: accf332 +64 vs **our +198**. Convergence
     point with previously-reverted `003408a`.

5. **Major flagged-dependency findings**:
   - **`003408a` is UNBLOCKED by accf332.** The revert message
     (`18061ec`) cited three missing prerequisites: DEFAULT_ROLE
     sentinel, `main_role` promotion on workflow activation, and
     broadcast-on-advance to typed sub-agents. accf332 introduces the
     first two natively; broadcast-on-advance is "likely" present
     (verification pending).
   - **accf332 does NOT hard-depend on `003408a`** -- pins check `cwd`
     at the engine level via `params.setdefault("cwd", workflow_root)`
     rather than at `CommandOutputCheck` ctor level. accf332 stands
     on its own; 003408a becomes additive.
   - **Re-trigger risk for re-applying `003408a` after accf332: NONE**
     on the originally-reverted basis. Small new risk: precedence of
     engine-level vs ctor-level `cwd` -- verify in implementation.
   - **`1d3f824` (DEFAULT_ROLE forward-port) is made redundant by
     accf332** -- same line in same file with identical wording, now
     with callers, so the F401 lint that triggered the revert vanishes.
   - **`ec604bc`'s `_token_store = OverrideTokenStore()` restoration
     must be preserved through any merge** -- independent bug-fix,
     verified still present at our HEAD `app.py:1655`.

### Historian's preview per-feature consensus (NOT a team decision)

Verify in Specification, don't assume:

| Feature | Historian's preview |
|---------|--------------------|
| A: workflow template variables | adopt |
| B: dynamic roles | adapt |
| C: effort cycling | adopt |
| D: guardrails UI | partial / skip |
| E: stowaway `pytest_needs_timeout` warn rule | adopt |

(plus 003408a as a 5th adoption candidate now that it's unblocked --
need to disambiguate from E in the next historian reply)

### Verification findings (historian, end of Leadership)

**V1 -- broadcast-on-advance is NOT in `accf332`.** It's already on our
base (and on abast's), in `claudechic/mcp.py` lines 927/960/967/970/991/1005,
introduced pre-merge-base by `66fa580` and `ca003a3` (PR #37). Both forks
share it. The only mention in the accf332 diff is a comment fragment in
`workflows/engine.py` -- rationale text, not the subsystem itself.

**Refinement to flagged-dependency findings**: of the 3 prerequisites the
`18061ec` revert cited, only TWO are introduced by `accf332` (DEFAULT_ROLE
sentinel + `main_role` promotion). The third (broadcast-on-advance) is
already on our base. So re-applying `003408a` after `accf332` is
**even safer than triage suggested** -- all three prerequisites
satisfied without any new broadcast-subsystem code to merge.

**V2 -- ZERO drift on the two skipped modal files.**
`widgets/modals/computer_info.py` and `widgets/modals/base.py` are unchanged
on our side since merge-base `285b4d1`. accf332's +68 (computer_info.py)
and +66 (base.py) will apply cleanly. UI-side surface area for D is much
cleaner than the engine seam: 3 new files are pure additions
(`paths.py`, `guardrails/digest.py`, `widgets/modals/guardrails.py`);
`computer_info.py` clean rewrite; `base.py` clean addition;
`diagnostics.py` clean deletion (we have not edited it either). The
hard conflicts for D are ONLY the `app.py` handler wiring.

### E disambiguation (confirmed)

E = the stowaway `pytest_needs_timeout` warn rule added to
`defaults/global/rules.yaml` in `accf332`. Independent adopt/skip
decision from D's modal UX (the rule is data, the modal is UX).
Composability's "5th unit" referred instead to the OUT-OF-CLUSTER
`003408a` precursor. So Specification weighs 6 candidates total:
A, B, C, D, E, plus the `003408a` re-pick decision.

### Historian stand-down

Historian standing down. Available for targeted git/blame queries
from the 3 axis-agents during Specification. Full thorough pass
(line-by-line `app.py` conflict map, per-commit cherry-pick playbook)
deferred until per-feature decisions are made.

## Hand-off notes for next phase (Specification)

The 3 axis-agents (engine-seam, guardrails-seam, UI-surface) read:
- `STATUS.md` (this file)
- `leadership_findings.md`
- `historian_findings.md`

and produce per-feature recommendations using
`(sub-feature, outcome in {adopt, adapt, skip, partial}, blocking-deps)`.

Specification ends with a user-checkpoint where the user approves per
feature before any implementation begins.

## Specification-phase course correction (UserAlignment, 2026-04-29)

UserAlignment flagged two scope-guard violations in the axis-agent
briefings, sent corrections to engine-seam, guardrails-seam, ui-surface:

### D4 -- `003408a` is out-of-cluster; no adopt/skip verdict from team

The user's clarification (4) is "stay strictly inside the 4-commit
cluster; flag, don't chase". My initial axis-agent prompts asked
engine-seam (Q8/Q9) and guardrails-seam (Q10) to produce adopt/skip
recommendations on `003408a`. Corrected:

- Use historian's V1 finding ("accf332 unblocks 003408a; re-trigger
  risk = NONE") as CONTEXT ONLY for feature B's prerequisite story.
- Do NOT produce a team adopt/skip verdict on `003408a` itself.
- Surface `003408a` only in the "Flagged-not-chased" addendum with the
  new fact and an explicit follow-up question for the user: "do you
  want a follow-up investigation on `003408a` re-pick?"

### D5 -- Stowaway feature E gets its own row

`pytest_needs_timeout` warn rule (in `accf332`'s
`defaults/global/rules.yaml`) was NOT named by the user. It is in
the cluster (in-bounds), but the user's per-feature decision authority
extends to it. guardrails-seam was instructed:

- E gets its own per-feature recommendation row, distinctly labelled
  "stowaway -- surfaced by team, user did not name."
- Do NOT silently bundle E into D's outcome.

### UserAlignment's standing checks for axis-agents (C1-C7)

- **C1.** Use abast's exact 4-feature wording.
- **C2.** Gestalt as one-sentence "after this lands, user sees X."
- **C3.** Treat `003408a` as context only, not as a recommendation.
- **C4.** Flag stowaway E separately; do not silently bundle.
- **C5.** Distinguish cherry-pick mechanical / human merge /
  reimplement from scratch when answering "can we reimplement?".
- **C6.** Define any non-user-named term on first use.
- **C7.** Per Skeptic Q4, state user-visible before/after with a
  concrete user.

### engine_seam axis report (2026-04-29)

Full file: `.project_team/abast_accf332_sync/spec_engine_seam.md`

#### Critical finding

**accf332 alone is partially broken on our base.** Feature A's
engine-level `cwd` pinning for advance_checks is silently dropped by
our check-factory registry. Our `CommandOutputCheck.__init__` accepts
only `(command, pattern)`; the factory updates that pass `cwd=p.get("cwd")`
through live in **`003408a`, not `accf332`**. Verified:
`git show --stat accf332 -- claudechic/checks/` is empty;
`git show --stat 003408a -- claudechic/checks/builtins.py` shows
83 lines. 8f99f03's `test_workflow_root_pins_command_check_cwd` will
FAIL on our base if we adopt accf332 alone. abast treats
accf332 + 003408a as one unit. So should we.

This reframes the `003408a` discussion: it is no longer a discretionary
follow-up; it is a hard prerequisite for slice A3. (UserAlignment's D4
constraint -- "no team verdict on 003408a" -- is preserved by surfacing
this coupling to the user as a *fact*, not a *recommendation*: if the
user wants A's cwd-pinning to work, A3 + 003408a are coupled.)

#### Three must-answer outcomes

1. **Substitution mechanism: converge on `${VAR}` syntax.** Adopt
   `${WORKFLOW_ROOT}` as a NEW token. Skip `$STATE_DIR` entirely
   (superseded by our existing `${CLAUDECHIC_ARTIFACT_DIR}`). Reject
   abast's bare `$VAR` syntax for consistency.
2. **State-location collapse: SKIP `paths.py` / `compute_state_dir` /
   `~/.claudechic/workflow_library/`.** Our `set_artifact_dir` MCP tool
   with coordinator-chosen path (validated, persisted in chicsession)
   is strictly more flexible than abast's auto-computed
   `~/.claudechic/workflow_library/<key>/<id>/`. Adopting both = a 5th
   state location for the same concept.
3. **003408a is FLAGGED context, not a recommendation (post D4
   correction).** A3's adoption requires matching `cwd`/`base_dir`
   ctor + factory changes in `claudechic/checks/builtins.py` (not in
   accf332; ~30 lines). Two scope-guard-compliant paths:
   - Port the ~30 lines inline as part of A3 adoption, OR
   - Coordinate with the user's eventual follow-up decision on
     out-of-cluster `003408a`.
   The team flags the prerequisite without pre-deciding the source.
   Q8 source-inspection finding (setdefault gives YAML-explicit cwd
   priority; no precedence conflict) preserved as informational only.

#### Granular per-feature outcomes

| ID | Outcome | Notes |
|----|---------|-------|
| A1 `${WORKFLOW_ROOT}` token | adopt | rename `$VAR` -> `${VAR}` |
| A2 `$STATE_DIR` + `workflow_library/` | **skip** | superseded |
| A3 engine cwd setdefault | adopt | **requires 003408a re-pick** |
| A4 two-pass auto-then-manual checks | adopt | clean independent improvement |
| B1 `DEFAULT_ROLE` sentinel | adopt | F401 risk gone (7+ callers) |
| B2 `Agent.agent_type` default="default" | adopt | 8f99f03 supplies test rename |
| B3 promote/demote on activate | **adapt** | hand-merge into our `_activate_workflow` |
| B4 `agent=` param threading | adopt | depends on B3 |
| B5 loader reject `main_role:default` | adopt | small validation |
| 003408a re-pick | strongly recommended | makes A3 functional |

#### Cross-axis flags

- **ui_surface** owns the surrounding flow of `_activate_workflow`
  (chicsession naming, restore prompt). engine_seam owns role-mutation
  insertion points only.
- **guardrails_seam** owns 003408a's `mcp.py` + `guardrails/hooks.py`
  parts; engine_seam owns `checks/builtins.py` (factory + ctors).
- This split aligns with guardrails_seam's coordination request earlier
  -- engine_seam confirms ownership of threads (i) and (iii); thread
  (ii) is owned by guardrails_seam.

### ui_surface axis report (2026-04-29)

Full file: `.project_team/abast_accf332_sync/spec_ui_surface.md`

| Unit | Verdict | One-liner |
|------|---------|-----------|
| C (effort cycling) | **ADAPT** (refined from ADOPT after C2/C7 gestalt check) | Self-contained, low/med/high (max on Opus only), default "high", session-ephemeral. No keybinding collision. **Gestalt-test fail: on-screen label "effort: high" reads as SDK jargon to a first-time user**; small UX adaptation needed (tooltip OR widget-text rename to "thinking" / "quality" -- doesn't change abast's feature label "effort cycling"). |
| diagnostics.py deletion | **ADOPT** | 4 ref sites; ComputerInfoModal absorbs jsonl_path + last_compaction with **zero info loss**. **Independent of D's outcome**. |
| Modal restructure (computer_info + base) | **ADOPT** | Independent refactor; NOT a prerequisite for GuardrailsModal (subclasses ModalScreen directly). Useful regardless of D. |

**app.py +282 split** (critical for cherry-pick planning):

| Slice | % | ~Lines |
|-------|----|--------|
| C (effort) | 10% | 25-30L |
| D (modal/footer) | 15-18% | 40-50L |
| A (state dir + template vars) | 16% | ~45L |
| B (dynamic roles) | **32%** | **~90L** |
| Formatting/other | 2-3% | -- |

The dominant slice is B (dynamic roles), not D (guardrails UI).

**Inter-axis flags F1-F6** (consequences for synthesis):

- **F1**: if D skips, dead code in `on_guardrails_label_requested` -- **don't rename ComputerInfoLabel if D skips**
- **F2**: `_disabled_rules` is the new runtime store distinct from `disabled_ids` (matches Terminology TC4)
- **F3**: `agent=` plumbing in `_make_options` is a B convenience; if B skips and C adopts, simplify to `effort_level=self._agent.effort`
- **F4**: `InfoLabel` rename is separable from `GuardrailsLabel` rename
- **F5**: **must preserve our `SettingsLabel`** in any footer cherry-pick. Proposed final layout: `ModelLabel . EffortLabel . PermissionModeLabel . InfoLabel . [GuardrailsLabel if D adopted] . SettingsLabel`
- **F6**: `widgets/modals/__init__.py` edit differs by D outcome

**Total UI effort if D deferred: 1.5-2.5h** (C + modal restructure + InfoLabel rename + footer merge preserving SettingsLabel).

### guardrails_seam axis report (2026-04-29)

Full file: `.project_team/abast_accf332_sync/spec_guardrails_seam.md`

| Sub-feature | Verdict | One-liner |
|-------------|---------|-----------|
| D modal | **SKIP** (with or without `a60e3fe`) | Fails Q1/Q4/Q5; applying `a60e3fe` triggers Q6 (regression vs no button) |
| D data layer (`digest.py` alone) | **SKIP / defer** | Clean leaf, no consumer; reimplement as `/guardrails` slash command (~30 LOC) if needed later |
| E (`pytest_needs_timeout`) | **ADOPT (manual append)** | 7-line YAML; cherry-pick context fails (refs abast's `no_pip_install` we lack); manual append is cleaner; doesn't cover hints (flag for report) |

Data-vs-UI separability **confirmed**: `digest.py` imports only
`guardrails.rules`; `GuardrailsModal` imports `GuardrailEntry` under
TYPE_CHECKING only -- the two halves are independently adoptable.

Cross-axis simplification: **skipping D removes a conflict surface from
engine_seam's app.py work** (both D and B touch `_make_options`,
`_merged_hooks`, `_guardrail_hooks`).

**UserAlignment D4 + D5 corrections applied (guardrails_seam, follow-up):**

guardrails_seam revised `spec_guardrails_seam.md`:

- All 003408a-related adopt/skip claims removed.
- 003408a now appears only in section 6.2 "Flagged context
  (out-of-cluster -- NOT a recommendation)" using the prescribed
  "accf332 unblocks 003408a; user may want follow-up" wording.
- Combined-recommendations table cut from 7 items to 4 (D-modal /
  D-data / D-runtime-disable / E).
- E surfaced separately on its own table row with explicit
  "stowaway -- discovered by team" type-tag.
- C1 / C2 / C7 standing checks all visibly applied.

Net headline unchanged: skip D, adopt E.

**Note on engine_seam's 003408a framing (preserves D4):** engine_seam
framed 003408a as a *factual coupling* (A3 cwd-pinning doesn't function
without 003408a's `checks/builtins.py` factory updates), not as a
recommendation. This honors D4 -- the team is not pre-deciding;
it is informing the user that A3 + 003408a are coupled IF A3 is
desired. The user remains free to skip A3 (which makes 003408a
moot) or adopt both as a package.

### Skeptic specification review (2026-04-29)

Full file: `.project_team/abast_accf332_sync/specification/skeptic_review.md`

| Sub | Skeptic verdict | One-line reason |
|-----|-----------------|------------------|
| A. workflow template variables | **ADAPT** | Verbatim adoption adds a 3rd substitution mechanism + 2nd syntax + new state location with no migration story. Our `${CLAUDECHIC_ARTIFACT_DIR}` already delivers the readability win. |
| B. dynamic roles | **ADAPT (small delta only)** | Our `app.py` already has `_activate_workflow` / `_deactivate_workflow` / `main_role` (17 hits). Real delta is ~3 narrow points. DO NOT cherry-pick the +282 patch wholesale. |
| C. effort cycling | **ADOPT** | Verified our SDK >=0.1.40 accepts `effort: Literal[...]`. Actually wired. Smallest blast radius in the cluster. |
| D. guardrails UI | **PARTIAL** | Skip modal/footer-rename; consider `digest.py` only with a caller. Abast themselves stubbed it (`a60e3fe`). |
| E. pytest_needs_timeout warn rule | **ADOPT IF regex hardened** | Empirically verified during the review: their own `grep -c "pytest"` triggered an existing `no_bare_pytest` rule on non-execution context. New rule will false-positive identically. |

Additional Skeptic outputs (binding for axis-agents):

- **Concrete demands on axis-specs**: (a) one-sentence user-visible delta
  with concrete user; (b) full contract-surface inventory;
  (c) moving-parts count + justification > 2; (d) name the narrow delta
  for any ADAPT verdict; (e) `(sub-feature, outcome, blocking-deps)`;
  (f) stay strictly in cluster.
- **Specific shortcuts pre-rejected** (named): "cherry-pick and resolve
  conflicts", "adopt commit 4 to be in sync", "skip D because abast did",
  "adopt E -- it's 7 lines", etc.
- **Pass/fail bar for synthesis**: per-feature breakdown, named symbols
  for ADAPT, named callers for any digest-only adoption, explicit
  exclusion of out-of-cluster commits, migration story for any
  state-location change.

Skeptic + UserAlignment **independently converged** on the `003408a`
scope-creep flag -- already corrected via D4 above.

### Terminology specification review (2026-04-29)

Full file: `.project_team/abast_accf332_sync/specification/terminology.md`

#### CRITICAL collisions (Composability calls required)

| # | Collision | Recommendation |
|---|-----------|----------------|
| TC1 | `workflow_root` (new, = main agent cwd) vs our `workflows_dir` / `_resolved_workflows_dir` (manifest discovery dir). One letter apart, completely different semantics. | Rename abast's `workflow_root` -> `project_root` before adoption. |
| TC2 | State-location proliferation: 6 distinct on-disk locations including `$STATE_DIR` and `${CLAUDECHIC_ARTIFACT_DIR}` overlapping. | Pick one or the other, not coexistence. |
| TC3 | Substitution syntax fork: abast `$VAR` (`str.replace`) vs ours `${VAR}` (braced). | Standardize on `${VAR}` for safety. |
| TC4 | `disabled_rules` (new, ephemeral in-memory) vs `disabled_ids` (existing, persisted config). | Two disable mechanisms that don't talk; pick one shape. |

#### Architectural flags

- "guardrails" is now 8-way overloaded across pre-existing + new
  meanings. Suggest a glossary anchor in `context/guardrails-system.md`.
- `ComputerInfoModal` class is NOT renamed; only the footer label is
  (`DiagnosticsLabel` -> `InfoLabel`). Synonym; defer rename.
- `a60e3fe` walks back the GuardrailsModal button to a stub. Adopting
  the cluster as-is ships dead modal code + a "not yet implemented"
  toast. **Binary call needed**: include the stub or ship the full modal.

#### Quote-grounded canonical home for each symbol

Every canonical name is cited to a specific file + line in the cluster
diff. Where commit message and source disagree (e.g. "state moves to
`~/.claudechic/workflow_library/`" -- present-tense in message, but
legacy `<repo>/.project_team/` is warned-about-not-migrated in code),
source wins; discrepancy flagged.

### UserAlignment specification review (2026-04-29)

Full file: `.project_team/abast_accf332_sync/specification/user_alignment.md`

Status: ALIGNED with corrective actions D4 + D5 above.

Domain-term gestalt risks for axis-agents:

1. **template variables** -- 3 substitution mechanisms now exist on
   combined base; "sync" implies a coherent system, not 3 half-merged.
2. **dynamic roles** -- if data plumbing ships without activation flow,
   "dynamic" is a misnomer.
3. **effort cycling** -- the user prompt does not specify what "effort"
   controls; the label's semantics must be self-evident or it fails the
   gestalt test.
4. **guardrails UI** -- `a60e3fe`'s stub is the cluster's clearest
   intent signal; recommendation MUST address full modal vs. stub vs.
   skip explicitly.

### Final-report contract (binding)

The final user-facing report must use the user's four exact questions
as section headers, plus 3 addenda:

- "What is it about?"
- "What is the intent?"
- "Should we pick it up here?"
- "Can we reimplement on our base?"
- (Addendum) Cluster identification (the 4 SHAs).
- (Addendum) Integration plan for adopt/adapt items.
- (Addendum) Flagged-not-chased list, with explicit `003408a`
  follow-up question for the user.
