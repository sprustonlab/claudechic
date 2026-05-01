# SPEC Appendix -- abast_accf332_sync

Non-operational content moved out of `SPEC.md`: the cluster narrative,
per-component rationale, alternatives considered and rejected, historical
context, the divergence map summary, and the "what NOT to do" list.

The implementer reads `SPEC.md`. This file is for review and second-guessing.

---

## 1. Cluster identification and intent narrative

### The four-commit cluster

| # | SHA | Author date (UTC) | Type | Subject |
|---|-----|--------------------|------|---------|
| 1 | `accf332df9e3f1a9c13e5951bec1a064973b6c96` | 2026-04-26 17:27:45 | feat | workflow template variables, dynamic roles, effort cycling, guardrails UI |
| 2 | `8f99f03` | 2026-04-26 17:27:48 | test | tests for the above |
| 3 | `2f6ba2e` | 2026-04-26 17:28:00 | docs | `CLAUDE.md` file-map update |
| 4 | `a60e3fe` | 2026-04-26 17:47:16 | chore | stub out guardrails modal "not yet implemented" |

The cluster is **non-contiguous on `abast/main`**: between commits 3 and
4 sit `1d6d432` (refactor: `tell_agent` -> `ask_agent` merge) and
`ff1c5ae` (rename: `ask_agent` -> `message_agent`), which are an MCP-tool
refactor unrelated to the four feature labels.

### Cluster identification process

- Historian identified the 4 SHAs by topic-matching the user's verbatim
  feature labels in commit subjects.
- Terminology independently identified the same 4 SHAs from a glossary
  pass over the diff.
- Composability initially proposed an alternative cluster
  (`003408a, accf332, 8f99f03, 2f6ba2e`); the disagreement was resolved
  by classifying `003408a` as out-of-cluster but flagged-as-dependency.

### Intent narrative

**Make the agent self-aware**, by composing five coordinated substrates:
when a workflow activates, the main agent (and its sub-agents) should
know its own paths, role, compute budget, and the rules + advance-checks
that govern it, without trial-and-error discovery. The agent is told
who it is at the start of every turn, and it can ask the runtime "what
applies to me right now?" via an MCP call.

This intent is what `accf332` is **trying** to deliver. The piece abast
shipped is the partial substrate: A, B, C, the data layer for D
(`digest.py`), and a placeholder UI (the modal). They shipped the modal
and immediately stubbed it (`a60e3fe`) because the connective tissue --
per-agent filtering, MCP wrapper, prompt injection -- wasn't ready.

### `a60e3fe` walk-back interpretation

The `a60e3fe` stub-out 20 minutes after `accf332` is read by the team
as "abast stubbed the modal because the agent-side machinery was not
ready", not as "the UI was buggy". The full agent-self-awareness story
needs B (per-agent identity), D-reframed's projection + injection +
MCP -- and `accf332` only ships the data-layer substrate plus the
unwired UI.

---

## 2. Per-component rationale and alternatives

### Component A -- rationale

#### Why ADAPT (not adopt verbatim)

Adopting verbatim creates **three substitution mechanisms** in our
combined surface:

1. `${repo_name}` / `${branch_name}` in `~/.claudechic/config.yaml`
   (worktree path templates).
2. `${CLAUDECHIC_ARTIFACT_DIR}` in workflow YAML (Group E,
   `e4fa9bf`).
3. `accf332`'s bare `$VAR` form (`$STATE_DIR`, `$WORKFLOW_ROOT`).

Two syntaxes, three scopes -- user confusion guaranteed. Convergence
on `${VAR}` is a small import-time rename pass; the long-term clarity
win is large.

abast's `$STATE_DIR` token is also redundant with our existing
`${CLAUDECHIC_ARTIFACT_DIR}` MCP-bound mechanism, which is strictly
more flexible (coordinator-validated path, persisted in chicsession,
post-launch settable).

#### Why SKIP A2 (`paths.py` / `compute_state_dir` / `workflow_library/`)

Our `set_artifact_dir` MCP tool already provides what abast's
`compute_state_dir` provides, plus more:

- coordinator-validated path (rejects `.claude/` substrings).
- post-launch settable.
- persisted in chicsession state.
- doesn't bake the path into a global `~/.claudechic/workflow_library/`.

Adopting both = a 5th state location for the same concept (Terminology
TC2). Composability **affirmed** SKIP over its initial "tolerate both"
pre-team draft.

#### Rejected alternatives for A

- **Adopt verbatim** (rejected by skeptic, terminology, engine_seam,
  composability).
- **Tolerate both syntaxes side-by-side** -- composability's pre-team
  draft suggested this; reversed after team review.
- **Migrate `${CLAUDECHIC_ARTIFACT_DIR}` -> `${STATE_DIR}`** to match
  abast -- rejected because our mechanism is strictly more flexible
  and already in production use.

### Component B -- rationale

#### Why ADAPT, framed as "proper fix" not "small delta"

Engine-seam's collision-vs-composition resolution traced
`agent.agent_type` to 8 consumption sites. Our existing path
(`a743423`-confirmed `main_role` resolution via closure) solves
**exactly 1 of 8**: the guardrail-hook role filter via
`lambda: self._workflow_engine.manifest.main_role`.

The other 7 are broken on our base today:

- `CLAUDE_AGENT_ROLE` env var: stuck at `None`.
- SDK `agent_type` parameter: `None`.
- Post-compact role-specific phase prompt for main agent: not re-injected.
- D-projection filter (hypothetical without B): nothing to filter by.
- Agent self-introspection: no programmatic identity.
- `mcp.py::spawn_agent` `type=` validation: no source of truth.
- `mcp.py::advance_phase` broadcast routing: no source of truth.

`8f99f03`'s Test 13 asserts on `main_agent.agent_type == "coordinator"`
and would FAIL on our base. Our `a743423`-passing test asserts only
on rule firing.

B is the **proper fix** for what our closure papers over. Composition,
not collision. Importance: HIGH (was undersold as "small delta" in
SPEC v1).

#### Why no wholesale +282 cherry-pick

Skeptic ranked B3 as the riskiest slice; composability named three
failure modes:

1. Cargo-pick the +282 patch wholesale -> duplicate code paths.
2. Hand-merge incorrectly -> `agent.agent_type` doesn't actually flip
   (silent failure).
3. Forget the `mcp.py:980,983` falsy-check sweep -> silent
   broadcast-filter change.

Mitigation: B3 deserves its own line-by-line conflict map. Order of
operations in SPEC's integration plan ensures B1+B2+B5 land first as
clean-apply foundation, then B3+B4 are surgical insertions.

#### Rejected alternatives for B

- **Cherry-pick the +282 patch and resolve conflicts** -- skeptic
  named this as a "specific shortcut I will reject."
- **Skip B entirely** -- rejected because B1 also unblocks `1d3f824`'s
  F401 lint risk, and B2/B3 deliver real UX (no SDK reconnect on
  activation).
- **Adopt B's data plumbing without the activation flow** -- rejected
  per UserAlignment's gestalt risk: "if data plumbing ships without
  activation flow, 'dynamic' is a misnomer."

### Component C -- rationale

#### Why ADAPT (UX adaptation, not adopt)

ui_surface initially recommended ADOPT; downgraded to ADAPT after
applying user_alignment's C2/C7 gestalt check.

The on-screen label "effort: high" reads as SDK jargon to a first-time
user. "Effort" is internal Anthropic SDK vocabulary for the
thinking-budget knob; it is not self-explanatory.

#### SDK-side trace verified

- `Agent.effort` -> `_make_options(agent=)` -> `ClaudeAgentOptions(effort=...)`
- SDK `claude_agent_sdk/_internal/transport/subprocess_cli.py::_build_command`
  appends `--effort <level>` to argv.
- `AgentDefinition.effort` field exists.
- Mid-session changes take effect on next response without reconnect.

C is genuinely a per-agent compute budget knob, not cosmetic.

#### Rejected alternatives for C

- **Skip C entirely** -- rejected because skeptic verified our SDK
  pin (`>=0.1.40`) accepts `effort: Literal[...]`, so the feature
  is genuinely wired.
- **Persist effort across sessions in v1** -- moved to C3 follow-up;
  initial scope keeps session-ephemeral default to limit blast
  radius.

### Component D -- rationale

#### Why this reframe (and the original SKIP recommendation was wrong)

The team's initial reading converged on D = SKIP because the only
visible artifact in `accf332` for D was the modal + footer button +
runtime-disable plumbing, and:

- abast themselves stubbed the modal button 20 minutes after shipping
  it (`a60e3fe`).
- Skeptic Q4 failed: no concrete user who would notice the difference
  the modal alone makes.
- `_disabled_rules` (new ephemeral) collided with our existing
  `disabled_ids` (persisted) without a reconciliation story.

The user's correction reframed D's intent away from a user-facing
modal toward **agent self-awareness**: an agent that knows what rules
apply to it. Under this reframing:

- The modal stays SKIP (it doesn't deliver agent self-awareness).
- The data layer (`digest.py`, or an equivalent helper from our
  predicates) becomes the projection function that powers the agent's
  view.
- The MCP wrapper and prompt injection are the new connective tissue
  that abast did not ship.

#### Why D-reframed has no blocking dep on B

Guardrails-seam verified that `compute_digest` (or its build-from-
primitives equivalent) takes `(loader, active_workflow, role, phase, disabled_rules)`.
The role argument can come from B (`agent.agent_type`) OR from our
existing main_role closure (`a743423`-confirmed). Both produce a
filterable role.

D-reframed is therefore independently shippable. With B also adopted,
D-reframed delivers the full 8/8 agent-self-awareness vision; without
B, D-reframed delivers a partial story (1/8 sites, the spawn-time
injection for the main agent).

#### Path X vs Path Y trade-off

| Dimension | Path X (adopt + extend) | Path Y (build + extend) |
|-----------|--------------------------|--------------------------|
| Total LOC | ~263 (128 adopted + 135 new) | ~70-100 (all new) |
| abast code reuse | yes (`digest.py` verbatim) | no |
| "Sync with abast" framing | yes | no -- this becomes a separate scope |
| Maintenance burden | tracks abast's `digest.py` evolution | independent of abast |
| Risk if abast changes `digest.py` | rebase pressure | none |

Both produce the same `list[GuardrailEntry]`. The user picks based on
strategic fit.

#### Why the modal stays SKIP under both paths

- abast stubbed it (a60e3fe).
- No concrete user wins from the modal alone.
- Q5 partial: a `/guardrails` slash command (~30 LOC) over the same
  data layer would deliver everything the modal does.
- Q6 fires under `a60e3fe`-applied: button toasts "not yet implemented",
  worse than no button.

#### Compositional landing conditions (binding)

Composability identified four issues either path must address:

1. Source-of-truth alignment (hooks vs registry).
2. Refresh policy (pick one consistent story).
3. Sub-agent identity statically bound at spawn (good, no work).
4. `get_phase` rule-count overstatement (orthogonal cleanup).

#### Three MCP placement options

- (a) deepen `get_phase` (changes existing tool's shape).
- (b) add `get_applicable_rules` alongside (lowest-risk additive --
  team default).
- (c) replace `get_phase`'s rule-count entirely (cleanest end state,
  breaks callers).

#### Four injection design options (cost-only)

- A: MCP-only (~50 LOC total). Mid-session updates for free.
- B: spawn-time injection only.
- C: kickoff + phase-advance + PostCompact injection.
- D = A + C (recommended): proactive at all 3 sites + on-demand mid-session.

### Component E -- rationale

#### Why ADOPT (manual append, harden regex)

- Q1-Q3 pass: solves a real problem; doesn't break a public contract;
  no out-of-base infrastructure dependency.
- Q4 passes: concrete user is "anyone running pytest from an agent who
  has been bitten by a hung test."
- Q5 partial: a Python pytest plugin would deliver more reliable
  enforcement, but the cost is meaningfully higher.

#### Why manual append, not cherry-pick

abast's diff places this rule adjacent to a `no_pip_install` rule
that we don't have. Cherry-pick context fails. Manual append is
cleaner.

#### Why regex hardening is mandatory

Skeptic empirically verified during the review that the existing
`no_bare_pytest` rule false-positives on `grep -c "pytest"` (Skeptic's
own `grep` call triggered the rule). The new rule will false-positive
identically unless the regex is tightened to require an actual command
invocation: word-boundary plus not-following `grep|rg|cat|less|head|tail`,
or similar.

False positives pollute the warn channel and train the agent to ignore
warns.

#### Rejected alternatives for E

- **Adopt as-is** ("it's 7 lines") -- skeptic explicitly rejected.
- **Skip E** -- the value is real and the cost is small with hardening.
- **Bundle E into D's outcome** -- UserAlignment D5 explicitly
  rejected. E is a data-layer addition independent of any UI.

### Component F (architectural by-product) -- rationale

- **Zero info loss**: `ComputerInfoModal` absorbs `jsonl_path` +
  `last_compaction` (verbatim copy of the readers).
- **Zero drift on our side** (V2 from historian): both
  `widgets/modals/computer_info.py` and `widgets/modals/base.py` are
  unchanged since merge-base `285b4d1`. accf332's +68 + +66 apply
  cleanly.
- Independent of D's outcome (D ships no modal under the reframing,
  and F's restructure is unrelated to D anyway).

---

## 3. What NOT to do during implementation

Consolidated from skeptic, terminology, composability, ui_surface,
engine_seam:

1. **Do NOT cherry-pick `accf332` wholesale.** It includes A2
   (`paths.py`/state-relocation, SKIP), the modal/footer/runtime-disable
   (SKIP), bare `$VAR` syntax (rename to `${VAR}`), and the python
   identifier `workflow_root` (rename to `project_root`).
2. **Do NOT cherry-pick the +282 `app.py` patch wholesale.** Hand-merge
   B3+B4 surgically; cherry-pick C wiring; preserve our `SettingsLabel`
   in the footer; do NOT add any `GuardrailsLabel` slot.
3. **Do NOT include `a60e3fe`.** The modal is skipped; the walk-back
   is moot.
4. **Do NOT introduce `_disabled_rules` as a runtime in-memory store.**
   Persistent disables continue via `disabled_ids` in config.
5. **Do NOT silently rely on `accf332`'s `cwd`-pinning without porting
   `claudechic/checks/builtins.py` ctor changes.** A3 is broken without
   them.
6. **Do NOT take E's regex verbatim.** Harden first.
7. **Do NOT lose `_token_store = OverrideTokenStore()` at app.py:1655**
   during any B3 hand-merge.
8. **Do NOT silently bundle E into D's outcome** (UserAlignment D5).
9. **Do NOT pre-decide on `003408a`, `1d6d432`, `ff1c5ae`, or `7dcd488`**
   beyond the structured user questions in SPEC's "Decision 6". Flag,
   don't chase.
10. **Do NOT rename component label "effort cycling"** in
    user-facing docs (UserAlignment C1). Only the on-screen widget text
    may be renamed if the user picks Decision 2 option (b) or (c).
11. **Do NOT use `awareness_install.py` as the constraints-block hook.**
    `awareness_install` writes stable cross-session files; the
    constraints block is per-agent-per-phase ephemeral. Mixing them
    muddles the boundary.
12. **Do NOT take abast's modal restructure (Component F) and the
    `widgets/modals/__init__.py` exports as a single unit.** The
    diagnostics deletion + ComputerInfoModal absorption ships
    independently of any D-related export changes.

---

## 4. Historical context

### Repo divergence

- Our base diverged from `abast/main` at merge-base `285b4d1`. Our
  HEAD is `a2c3779`; abast's HEAD is `7dcd488`.
- Since merge-base: 16 abast-only commits, 42 ours-only.
- Tag distribution (per historian's divergence map): cluster (C) = 4
  abast / 0 ours; direct dependency (D) = 1 abast / 5 ours;
  might-inform (M) = 6 abast / 16 ours; unrelated (-) = 5 abast / 21
  ours.

### Critical divergent commits surfaced

- **`d001e30`** (ours, +1253) -- claudechic-awareness +
  **in-memory phase-prompt delivery**. Three injection sites
  (`_activate_workflow` line 1922-1941, `_inject_phase_prompt_to_main_agent`
  line 2165, `create_post_compact_hook` lines 94-138) all flow through
  `_send_to_active_agent` (line 2567-2581). Tested end-to-end in
  `tests/test_phase_prompt_delivery.py` (9 tests including INV-AW-6/8/9).
  This is the substrate Component D rides on.
- **`a743423`** (ours) -- test fixup confirming `main_role` resolution
  works on our base (the underlying behavior was already working;
  the test was firing its hook with the wrong tool_name after the
  `message_agent` rename).
- **`81f0c69`** (ours, +1736) -- Group C 3-tier loader; the +891
  `loader.py` drift origin.
- **`e4fa9bf`** (ours, +1112) -- Group E
  `${CLAUDECHIC_ARTIFACT_DIR}` mechanism; the substitution-syntax
  incumbent.
- **`711be4c`** (ours) -- Group A defaults restructure; our equivalent
  layout to abast's `d55d8c0`.

### Revert history relevant to Component B

- **`8abb2f9`** (ours) -- prior cherry-pick of `003408a`.
- **`18061ec`** (ours) -- revert of `8abb2f9` citing 3 missing
  prerequisites: DEFAULT_ROLE sentinel, main_role promotion,
  broadcast-on-advance to typed sub-agents.
- **`1d3f824`** (ours) -- prior `DEFAULT_ROLE` forward-port.
- **`ec604bc`** (ours) -- revert of `1d3f824` due to F401 lint, plus
  restoration of `_token_store = OverrideTokenStore()`.

Re-state of prerequisites after `accf332`:

- DEFAULT_ROLE sentinel: `accf332` introduces (Component B1).
- main_role promotion: `accf332` introduces (Component B3).
- broadcast-on-advance: **already on our base** in `mcp.py`
  (lines 927/960/967/970/991/1005), introduced pre-merge-base by
  `66fa580` and `ca003a3` (PR #37).

So: `003408a` is now unblocked. Re-applying after `accf332` carries
no known re-trigger risk on the originally-reverted basis. The user
decides separately (SPEC Decision 6).

### Out-of-cluster abast commits flagged

- **`d55d8c0`** (+6069) -- `defaults/{guardrails,hints,workflows}`
  bundle layout. Foundational for `accf332`. Our `711be4c` is the
  equivalent layout on our side; we don't adopt `d55d8c0`.
- **`f9c9418`** (+317) -- full model ID selection. Underlies C's
  model-aware logic. Our base has equivalent model selection through
  the existing footer flow.
- **`9fed0f3`** -- docs on `spawn_agent type=`.
- **`1d6d432`** (refactor: `tell_agent` -> `ask_agent` merge).
- **`ff1c5ae`** (rename: `ask_agent` -> `message_agent`).
- **`7dcd488`** -- abast/main HEAD ("Generalprobe testing sub-cycle").
  Out of scope.

---

## 5. Process metadata

### Phases

- Vision (approved 2026-04-29).
- Setup (artifact dir bound, STATUS.md / userprompt.md created).
- Leadership (4 leadership agents + historian spawned and reported).
- Specification v1 (initial SPEC.md / SPEC_APPENDIX.md presented to user).
- User redirect 2026-04-29: scope expansion + D reframing.
- Specification v2 (this document; team re-engaged on D-reframe + scope-broadening).
- Implementation, Testing, Documentation, Sign-Off (pending).

### What changed from v1 to v2

- **Cluster intent** reframed from "four bundled UI/UX features" to
  "agent-self-awareness substrate".
- **Component D verdict** flipped from SKIP to ADAPT, with the modal
  and runtime-disable plumbing skipped while the projection + MCP +
  prompt injection are adopted/built.
- **Per-feature recommendations** now include both user-side and
  agent-side gestalt sentences (UserAlignment binding rule C8).
- **Broader divergence context** included; `d001e30` and `a743423`
  surfaced as critical infrastructure findings.
- **Three additional decisions** added: D1 implementation path
  (X vs Y), D injection shape (A/B/C/D), MCP placement (a/b/c).

### Standing checks (binding for axis-agents)

- C1: use abast's exact 4-feature wording in user-facing docs.
- C2: gestalt as one-sentence "after this lands, user sees X / agent sees X."
- C3: treat `003408a` as context only, not a recommendation.
- C4: flag stowaway E separately; do not silently bundle.
- C5: distinguish cherry-pick mechanical / human merge / reimplement
  from scratch when answering "can we reimplement?".
- C6: define any non-user-named term on first use.
- C7: per Skeptic Q4, state user-visible before/after with a
  concrete user.
- C8: every per-feature recommendation must include both a user-side
  gestalt AND an agent-side gestalt; if one is empty, state so.

### Per-axis full-detail files

- `historian_findings.md` -- raw git facts; triage pass + verification
  pass + full divergence map.
- `leadership_findings.md` -- consolidated Leadership-phase output.
- `specification/skeptic_review.md` -- Q1-Q6 falsification matrix per
  feature; "specific shortcuts I will reject" list.
- `specification/terminology.md` -- canonical glossary, 4 critical
  collisions, 8-way "guardrails" overload analysis.
- `specification/user_alignment.md` -- vision-drift checks, must-answer
  list, C1-C7 standing checks plus 2026-04-29 reframing-fidelity audit.
- `specification/composability.md` -- compositional consistency check,
  cross-axis seam audit, granularity translation, risk landscape, plus
  D-reframe architectural-fit assessment (section 12).
- `spec_engine_seam.md` -- A and B slice analysis;
  003408a-as-flagged-context section; substitution + state-location
  architecture calls; B+A reframing under agent-self-awareness lens;
  collision-vs-composition resolution.
- `spec_guardrails_seam.md` -- D-skip rationale (with and without
  `a60e3fe`); E adopt rationale; D-reframed analysis (section 11)
  including data-layer fit, MCP API sketch, prompt-injection plan,
  Q1-Q6 fresh, revised verdict.
- `spec_ui_surface.md` -- C analysis with gestalt-test follow-up;
  `app.py` +282 split estimates; F1-F6 inter-axis flags; footer
  layout proposal; C reframed under agent-perspective with verified
  SDK trace.

---

*End of appendix.*
