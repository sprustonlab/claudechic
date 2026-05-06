# Composability axis -- Specification synthesis

**Author:** Composability (Lead Architect)
**Phase:** project-team:specification
**Date:** 2026-04-29
**Cluster:** abast `accf332` + `8f99f03` + `2f6ba2e` + `a60e3fe`. Out-of-cluster
flagged dependency: `003408a`. Merge-base `285b4d1`. Our HEAD `a2c3779`.

This document synthesises three axis-specific deep-dives into a single
composability picture. The three axis files contain the detailed
evidence; this file contains the cross-axis findings, the recommended
crystal point, and the integration plan.

- Engine seam: `./engine-seam.md`
- Guardrails seam: `./guardrails-seam.md`
- UI surface: `./ui-surface.md`

---

## 1. Verdict-at-a-glance

Two views of the same picture: the user-visible 4-feature view (per
UserAlignment FLAG 1, abast's exact wording, used in the final report
to the user) and the implementer's slice view (engine-seam decomposed
A into 4 slices and B into 5 slices; ui-surface decomposed D's
adjacent surface; guardrails-seam decomposed D itself). Granularity
translation is intentional: the user gets one decision per named
feature; the implementer gets one cherry-pick per slice.

### User-visible (4 features + stowaway)

| # | Feature | Outcome | Owning axis |
|---|---------|---------|-------------|
| A | workflow template variables | **ADAPT** | engine-seam |
| B | dynamic roles | **ADAPT** | engine-seam |
| C | effort cycling | **ADOPT** (with a small UX adaptation -- see §3.9) | UI-surface |
| D | guardrails UI | **SKIP** (modal AND data layer AND footer rename) | guardrails-seam |
| E | `pytest_needs_timeout` warn rule (stowaway) | **ADOPT IF regex hardened** | guardrails-seam |

### Implementer slice view (the cherry-pick checklist)

| Slice | Outcome | Notes |
|-------|---------|-------|
| **A1** `${WORKFLOW_ROOT}` token | **adopt (rename `$VAR` -> `${VAR}`)** | New token; routes through our existing `_substitute.py` resolver; converges syntax (TC3). |
| **A2** `$STATE_DIR` + `paths.py` + `~/.claudechic/workflow_library/` | **SKIP** (superseded) | Our `set_artifact_dir` MCP tool is strictly more flexible. Adopting A2 = a 5th state location for the same concept (TC2). |
| **A3** engine `params.setdefault("cwd", workflow_root)` | **adopt -- but factually requires `003408a`'s `checks/builtins.py` factory updates to actually function** | Hard fact, not a recommendation (per UserAlignment D4). The user decides whether to (a) port the ~30 lines inline, or (b) re-pick `003408a` as a follow-up. Without one of those, A3 is dead code. |
| **A4** two-pass auto-then-manual checks | **adopt** | Clean independent improvement to advance-check ordering. |
| **B1** `DEFAULT_ROLE = "default"` sentinel | **adopt** | F401 risk (which caused our earlier revert) is gone -- accf332 has 7+ callers. |
| **B2** `Agent.agent_type` default flips `None` -> `"default"` | **adopt with sweep** | Mandatory: rewrite `mcp.py:980,983` falsy checks to `agent.agent_type in (None, DEFAULT_ROLE)` else broadcast filter silently changes meaning. `8f99f03` test rename pairs cleanly. |
| **B3** `_activate_workflow` promote / demote flow | **ADAPT (hand-merge)** | We already have `_activate_workflow` / `main_role` plumbing (17 hits in our `app.py`). Real delta is ~3 narrow points, NOT the +282 patch wholesale (per Skeptic). |
| **B4** `agent=` param threading into `_make_options` / `_merged_hooks` / `_guardrail_hooks` | **adopt** | Depends on B3. If C adopts but B3 doesn't, fall back to `effort_level=self._agent.effort` (per ui-surface F3). |
| **B5** loader rejects `main_role: default` | **adopt** | Small validation added per-file in our 3-tier loader's parse layer; resolution layer needs no change. |
| **C** effort cycling | **adopt** | Smallest blast radius; SDK kwarg verified. UX adaptation: tooltip OR widget-text rename to convey what "effort" means (per ui-surface gestalt review). |
| **D-modal** `GuardrailsModal` | **SKIP** | Fails Skeptic Q1/Q4/Q5; abast's own `a60e3fe` walkback; persistence ambiguity (TC4); soft dep on B for usefulness; Textual widget-ID bug for namespaced rule IDs. |
| **D-data** `digest.py` | **SKIP / defer** | Clean leaf; no caller; reimplement as `/guardrails` slash command (~30 LOC) if user later asks. |
| **D-runtime-disable** `_disabled_rules` + `get_disabled_rules` callback wiring | **SKIP** | Without modal, dead weight. Drops the TC4 ambiguity. |
| **D-footer** `ComputerInfoLabel -> GuardrailsLabel` rename | **SKIP** (and DROP slot entirely) | Per ui-surface F1: do NOT rename if D skips. The new `Info` modal absorbs everything `Sys` showed; drop the ComputerInfoLabel slot. |
| **modal restructure** `diagnostics.py` deletion + `computer_info.py` rewrite + `base.py +66` + `DiagnosticsLabel -> InfoLabel` rename | **adopt** (independent of D) | Zero info loss; zero drift on the modified files (historian V2). Frees a footer slot. |
| **E** `pytest_needs_timeout` warn rule | **adopt IF regex hardened** | Manual 7-line YAML append (cherry-pick context fails -- abast's diff refs `no_pip_install` we lack). Hardening is a precondition, not a follow-up: Skeptic empirically observed the existing `no_bare_pytest` false-positive on a non-execution `grep -c "pytest"` during this very review. |
| **003408a re-pick** (out-of-cluster) | **CONTEXT ONLY -- user decides** (per UserAlignment D4) | Three threads, three independent outcomes possible: (i) `checks/builtins.py` cwd ctor params -- needed if A3 is to function; (ii) `hooks.py` warn-message rewrite -- ~10 LOC, fully decoupled, real Q4 win; (iii) `mcp.py` DEFAULT_ROLE in spawn flow -- downstream of B1. |

Outcome key: `adopt` = take the change as-is or with a mechanical
forward-port; `adapt` = take the intent but rework on top of our
diverged surface; `skip` = decline; `partial` = take some component(s),
decline others.

**Granularity translation answer (Coordinator's question 4):** the
user-facing report uses A/B/C/D/E (their wording, their decision
unit). The slice table above is the implementer's checklist that
falls out once the user approves at the feature level. Two views of
the same crystal point; no contradiction.

**Cluster-level intent (Composability reading):** abast packaged a
workflow-engine substitution mechanism, a role-lifecycle generalisation,
a runtime UI knob (effort), and an introspection UI (guardrails)
together because they touch overlapping files. They are NOT one
indivisible feature. Decomposed, four of the five sub-features are
independently adoptable on our base; the fifth (D) was walked back by
abast themselves 20 minutes after shipping it.

---

## 2. The decomposition: why "one feature" is actually six

The commit's title bundles four arguably-independent sub-features into a
single drop. From the composability lens, that itself is a "bundled
choices" smell -- the per-feature outcome categories
(adopt/adapt/skip/partial) only become meaningful if we factor the
cluster along its real axes first.

The 6 candidate units (A, B, C, D, E, plus the 003408a re-pick decision)
each live on a separable axis:

- A and B share the workflow-engine seam and one common file
  (`workflows/agent_folders.py` for `DEFAULT_ROLE`); they should be
  cherry-picked atomically but are conceptually independent (template
  substitution vs role lifecycle).
- C is a UI knob with one SDK kwarg pass-through. Self-contained.
- D's data layer (`digest.py`) is a clean leaf with no consumer; D's
  modal needs B to be useful and would require a persistence-semantics
  decision we do not currently want to make.
- E is a 7-line YAML record using only pre-existing infra.
- The 003408a re-pick decomposes into three INDEPENDENT threads (per
  guardrails-seam), each with its own cost/benefit.

Total real units: 8 (A, B, C, D-modal, D-data, D-runtime-disable, E,
003408a-thread-ii). Of these, the cluster as shipped pretends 4. The
gap between "as shipped" and "as factored" is the composability story.

---

## 3. Cross-axis findings (the things no single axis report could see)

### 3.1 The "GuardrailsLabel rename is gated on D" coupling

The footer label renames in `accf332` are TWO renames:

1. `DiagnosticsLabel -> InfoLabel` -- couples to the modal restructure
   (UI-surface owns; ADOPT)
2. `ComputerInfoLabel -> GuardrailsLabel` -- couples to D's modal
   (guardrails-seam owns; SKIP)

If we adopt the rename in (2) but skip D, we ship a footer button with
no working handler -- worse than the `a60e3fe` "not yet implemented"
toast (which itself is a regression vs our current `Sys` button which
does something useful).

**Composability resolution:** treat each footer slot as an independent
unit. With D skipped, do NOT rename `ComputerInfoLabel`. The cleanest
end-state (per UI-surface's analysis) is to drop the slot entirely,
because the new `Info` modal already shows the system info that the
`Sys` slot used to. Final footer becomes:

```
Model . Effort . PermissionMode . Info . Settings
```

(`SettingsLabel` is OUR addition that abast doesn't have; it MUST be
preserved through any cherry-pick of `footer.py`.)

### 3.2 The `agent.agent_type` attribute is the pivot for B AND D

Sub-feature B introduces dynamic `agent_type` (DEFAULT_ROLE -> main_role
on activation). Sub-feature D's modal handler reads `agent.agent_type`
to compute the digest's role-skip column. Without B, the modal renders
every role-scoped rule as "role 'None' excluded" -- functional but
uninformative.

**Implication:** D has a SOFT DEPENDENCY on B. This further reinforces
the SKIP-D recommendation: even if we later re-evaluate D, B must land
first.

This dependency is not visible in either axis report read alone --
guardrails-seam owns D, engine-seam owns B, the dependency crosses the
axis boundary.

### 3.3 The `get_disabled_rules` callback collision (accf332 vs 003408a)

Both `accf332` and `003408a` independently add the same parameter to
`create_guardrail_hooks(...)`:

```python
get_disabled_rules: Callable[[], set[str]] | None = None
```

If both commits are picked, the second cherry-pick will conflict on
`hooks.py`. Order matters: pick `003408a` first then `accf332` (lighter
patch first), or pick `accf332` first then 003408a manually omitting
the duplicate addition. Either way, **the callback must land once, not
twice.**

This is a coordination point with the cherry-pick playbook -- not a
showstopper. With our current recommendations (003408a = CONTEXT ONLY,
accf332 = adopt sub-features), we'd land the callback addition once via
accf332 and revisit only thread ii of 003408a (which doesn't touch the
callback signature anyway, only the warn-rule message text inside the
hook). Clean.

### 3.4 The substitution-mechanism crystal

We have THREE substitution mechanisms on the combined base, plus a
fourth at config-time:

| Mechanism | Syntax | Tokens | Resolved at | Scope |
|---|---|---|---|---|
| Worktree path template | `${...}` | `${repo_name}`, `${branch_name}`, `$HOME` | Worktree creation | Filesystem path |
| Workflow artifact dir (Group E, ours) | `${...}` | `${CLAUDECHIC_ARTIFACT_DIR}` | Phase prompt + check command | Workflow content + check command |
| abast `$STATE_DIR` (engine-seam, A) | `$VAR` (no braces) | `$STATE_DIR` | Check execution + prompt assembly | Any string param + markdown |
| abast `$WORKFLOW_ROOT` (engine-seam, A) | `$VAR` (no braces) | `$WORKFLOW_ROOT` | Same as `$STATE_DIR` | Same |

**Are these ONE axis or many?** ONE composability axis (string template
substitution on workflow content), expressed inconsistently. Two
syntaxes, three resolvers, three scopes. The tokens have non-overlapping
NAMES so they don't race, but a user cannot ask "where can I use
template variables?" and get a single answer. The `${...}` vs `$...`
split is the smell.

**Compositional law (CONVERGED with engine-seam + Terminology TC3):**
all template variables go through one resolver
(`workflows/_substitute.py` becomes the law-bearer). The documented
convention is `${...}`; bare `$VAR` is REJECTED for new tokens.
Existing references to `$STATE_DIR` in our defaults (the latent
dead-token bug, see §3.5) are cleaned up either by adoption of A1 (which
also routes them through the resolver under the renamed
`${WORKFLOW_ROOT}`) or by manual cleanup.

**Two-token state, but only one of them adopted (CONVERGED with
engine-seam A2 SKIP + Terminology TC2):**

- `${WORKFLOW_ROOT}`: engine-computed, eager, the launched-repo cwd.
  ADOPTED via A1 (renamed from abast's bare `$WORKFLOW_ROOT`).
- `${CLAUDECHIC_ARTIFACT_DIR}`: coordinator-set via `set_artifact_dir`
  MCP tool, lazy, per-RUN. KEPT (Group E).
- `$STATE_DIR` and the engine-picked `~/.claudechic/workflow_library/`
  state location: SKIPPED (A2). Our `set_artifact_dir` is strictly more
  flexible; adopting both creates a 5th state location for the same
  concept (per state-dir map in §3.6).

**Earlier draft superseded:** my pre-team Leadership-phase draft
proposed "tolerate both syntaxes; keep both state locations as a
layered pair." Engine-seam and Terminology converged independently on
the stronger call: standardize on `${VAR}`, skip `workflow_library/`.
This synthesis adopts the team's convergence.

### 3.5 The latent dead-token bug

Our defaults already contain unsubstituted `$STATE_DIR` in:
- `defaults/workflows/project_team/project_team.yaml` (lines 44, 52)
- `defaults/workflows/project_team/{user_alignment, terminology, skeptic, composability}/testing-specification.md` (line 4 of each)

These came in via our cherry-pick of abast's `7dcd488` (testing
sub-cycle) but the resolver they need ships in `accf332`. Today on our
base, the tokens reach the shell as literal `$STATE_DIR/foo`, which the
shell expands against the empty environment to `/foo`.

**This converts the "should we adopt A?" question from speculative to
remedial.** If we skip A, we should AT MINIMUM clean up the dead tokens
by hand. If we adopt A, the dead tokens become live with the engine's
substitution.

### 3.6 The state-dir map and `workflow_library/`

Current state locations on the combined base:

| Location | Owner | Lifetime | Purpose |
|---|---|---|---|
| `~/.claudechic/config.yaml` | `config.py` | User | User-tier preferences |
| `~/.claudechic/chicsessions/<name>.json` | `chicsessions.py` | User | Multi-agent snapshots |
| `~/.claudechic/hints_state.json` | `hints/state.py` | User | Hint lifecycle persistence |
| `<repo>/.claudechic/config.yaml` | `config.py` | Project | Project-tier toggles |
| `<repo>/.claudechic/hits.jsonl` | `app.py` `HitLogger` | Project | Guardrail hit log |
| `<artifact_dir>/...` (coordinator-chosen) | `set_artifact_dir` | Run | Per-run workflow artifacts |
| **(NEW from abast accf332)** `~/.claudechic/workflow_library/<key>/<name>/` | `paths.compute_state_dir` | Workflow | Per-workflow scratch state |

**Composability assessment:** `workflow_library/` does NOT replace any
existing location. It overlaps semantically with the coordinator-chosen
`artifact_dir` (both want to be "where workflow STATUS.md lives"), but
they answer different questions: artifact_dir is coordinator-picked,
workflow_library is engine-picked.

**Recommendation (CONVERGED with engine-seam A2 SKIP + Terminology
TC2): SKIP `workflow_library/`.** Our `set_artifact_dir` MCP tool with
coordinator-chosen path (validated, persisted in chicsession) is
strictly more flexible than abast's auto-computed
`~/.claudechic/workflow_library/<key>/<id>/`. Adopting both = a 5th
state location for the same concept; the cluster ships no migration
story for chicsessions already on user disk.

**Earlier draft superseded:** my pre-team Leadership draft said "keep
both as a layered pair." Engine-seam's slice analysis showed
`workflow_library/` adds no capability `set_artifact_dir` doesn't
already provide -- it only adds a 5th location to keep documented and
migrated. This synthesis follows the team's call: SKIP A2.

**Consequence for A1 (`${WORKFLOW_ROOT}`):** the token is still useful
on its own (it gives YAML/markdown a stable absolute path for the
launched repo). It does not require A2 to function. Adopting A1 alone
satisfies the latent dead-token cleanup goal (§3.5) IF we also rename
the dead `$STATE_DIR` references to `${WORKFLOW_ROOT}/<subpath>` --
which is a bundled-YAML rewrite the implementer must do.

**Terminology TC1 (NEW finding):** abast's engine ctor parameter name
`workflow_root` collides one-letter with our existing `workflows_dir`
/ `_resolved_workflows_dir` (which means "manifest discovery dir").
Different semantics, similar names. **Recommend rename: `workflow_root`
-> `project_root`** (Composability concurs with Terminology TC1) before
any cherry-pick lands. Apply consistently in `engine.py`, `paths.py`
(if any of paths.py survives -- under A2 SKIP it doesn't), and the
`${WORKFLOW_ROOT}` token (rename to `${PROJECT_ROOT}` or keep
`${WORKFLOW_ROOT}` as user-facing while renaming the internal var --
implementer's micro-call).

### 3.9 Effort label gestalt risk (UI-surface + UserAlignment)

UI-surface (after applying UserAlignment's C2/C7 gestalt check) refined
the C verdict from ADOPT to ADOPT-WITH-UX-ADAPTATION: the on-screen
footer label `effort: high` reads as SDK jargon to a first-time user
(what does "effort" cycle? thinking budget? credits? request size?).
The implementer should add either a tooltip ("Effort: how hard the
model thinks. low/medium/high/max -- max enables extended thinking on
Opus") OR rename the visible widget text to "thinking" / "quality"
while keeping abast's feature label "effort cycling" unchanged in
internal symbols and documentation.

**This is a small UX adaptation, not a recommendation change.** C
remains ADOPT; the adaptation belongs in implementation. Composability
concurs.

### 3.7 The `_disabled_rules` vs `disabled_ids` semantic ambiguity

Sub-feature D would introduce a second disable mechanism:
`_disabled_rules: set[str]` (in-memory, session-ephemeral, no
persistence) alongside our existing `disabled_ids` (persistent in
`config.yaml`, accessible via `/settings`). The cluster ships these
with NO documented composition rule -- they don't talk to each other.

This is a hole. A user who toggles a rule off in the modal expects it
to stay off; a user who has it disabled in `disabled_ids` is surprised
to see it as "enabled" in the modal.

**Composability assessment:** if D were ever adopted, this ambiguity
must be resolved FIRST. Two clean shapes:
- Collapse: modal toggle writes to `disabled_ids`. Lose
  session-ephemeral capability; gain coherence.
- Layered: modal seeds `_disabled_rules` from `disabled_ids` on open;
  hook semantics is `skip_if_in(disabled_ids) OR
  skip_if_in(_disabled_rules)`; modal shows "persistent: yes/no" badge
  per row.

The cluster as shipped does neither. **This is a second reason to skip
D**: adopting it forces us to either invent a new persistence layer or
silently inherit an ambiguous one.

### 3.8 The 003408a coupling: A3 cannot function without it (FACT, not recommendation)

Per historian V1 + guardrails-seam + engine-seam (critical finding):
`accf332` natively satisfies all three prerequisites cited by the
`18061ec` revert (DEFAULT_ROLE sentinel, main_role promotion,
broadcast-on-advance). Re-trigger risk is NONE on the originally-
reverted basis.

**But:** engine-seam's source inspection found a hard fact that
reframes the discussion. `accf332`'s engine-level
`params.setdefault("cwd", workflow_root)` produces a `cwd` value in
the params dict, but the receiver -- our `CommandOutputCheck.__init__`
-- accepts only `(command, pattern)` and silently drops the extra
kwarg. The factory updates that thread `cwd=p.get("cwd")` through to
the ctor live in **`003408a`'s `checks/builtins.py`, NOT in
`accf332`.** Verified: `git show --stat accf332 -- claudechic/checks/`
returns empty; `git show --stat 003408a -- claudechic/checks/builtins.py`
shows 83 lines. `8f99f03`'s `test_workflow_root_pins_command_check_cwd`
will FAIL on our base if we adopt `accf332` alone.

**Implication:** A3 (engine cwd setdefault) requires the
`checks/builtins.py` factory updates from 003408a to actually function.
Two scope-guard-compliant paths for the implementer:

1. Port the ~30 lines of `checks/builtins.py` factory updates inline
   as part of A3 adoption, OR
2. Coordinate with the user's eventual follow-up decision on
   out-of-cluster `003408a`.

**Per UserAlignment D4: the team produces NO adopt/skip verdict on
003408a itself.** It is OUT-OF-CLUSTER. We surface the A3 coupling as
a *fact* (if the user wants A3 to function, the factory updates are
required) rather than as a *recommendation* (we don't say "adopt
003408a").

The 003408a commit decomposes into three threads:

| Thread | Where | Coupling to cluster | Cost/benefit (for user's follow-up) |
|--------|-------|---------------------|-------------------------------------|
| (i) per-check `cwd`/`base_dir` ctor params | `checks/builtins.py` | **HARD COUPLING with A3** -- A3 is dead code without this thread. | High value if A3 is adopted; mandatory in that case. |
| (ii) richer warn-rule reasoning text | `guardrails/hooks.py` | None. Fully decoupled. ~10 LOC. | High value, low cost. Real Q4 win independent of any other decision. |
| (iii) DEFAULT_ROLE handling in `mcp.py` spawn flow | `mcp.py` | Downstream of B1's DEFAULT_ROLE adoption. Adds explicit sentinel handling; removes None ambiguity. | Medium value, medium cost. |

Surface to user as a follow-up question (see §6) rather than a team
verdict.

---

## 4. Recommended crystal point

The Composability axis recommends the following point in the
configuration crystal (slice-level granularity):

```
A1 (${WORKFLOW_ROOT} token, renamed from $VAR)        = adopt
A2 ($STATE_DIR + paths.py + workflow_library/)        = SKIP   (TC2)
A3 (engine cwd setdefault)                            = adopt  (FACT: requires 003408a thread (i) factory updates to function)
A4 (two-pass auto-then-manual checks)                 = adopt
B1 (DEFAULT_ROLE sentinel)                            = adopt
B2 (Agent.agent_type default = "default")             = adopt  (with mcp.py:980,983 sweep)
B3 (_activate_workflow promote/demote)                = ADAPT  (hand-merge ~3 narrow points, NOT the +282 patch)
B4 (agent= param threading)                           = adopt
B5 (loader rejects main_role: default)                = adopt
C  (effort cycling)                                   = adopt  (with tooltip OR widget-text gestalt adaptation)
D-modal                                               = SKIP
D-data (digest.py)                                    = SKIP / defer
D-runtime-disable (_disabled_rules + callback wiring) = SKIP
D-footer (ComputerInfoLabel -> GuardrailsLabel)       = SKIP   (drop slot entirely; do NOT rename)
modal restructure (diagnostics + computer_info + base + InfoLabel) = adopt  (independent of D)
E (pytest_needs_timeout)                              = adopt IF regex hardened (precondition)
003408a re-pick                                       = CONTEXT ONLY (per UserAlignment D4)
                                                        - thread (i) coupling-fact for A3
                                                        - thread (ii) decoupled Q4 win
                                                        - thread (iii) downstream of B1
```

Plus three Terminology renames before any cherry-pick lands:
- TC1: abast's engine ctor `workflow_root` -> `project_root`
- TC3: bare `$VAR` substitution syntax -> `${VAR}`
- TC4: do NOT introduce `_disabled_rules`; keep `disabled_ids`

**Why this point is composable:**
- A1+A4 alone (no A2, no A3) deliver the user-facing "no hardcoded
  paths in YAML" win and clean up the latent dead-token bug; A3 is the
  cwd-pinning correctness fix that needs the user's 003408a follow-up
  decision to actually function.
- B1-B5 together give us proper role-lifecycle plumbing; B3's adapt
  (hand-merge) is the gating implementer task per Skeptic.
- C is a clean orthogonal addition; the gestalt adaptation belongs in
  implementation.
- The modal restructure is independent of D (UI-surface verified) and
  frees a footer slot.
- Skipping D removes: the persistence ambiguity (TC4), the soft dep on
  B for usefulness, the abast-walked-back UX, the Textual widget-ID
  bug for namespaced rule IDs, and ~40-50 lines of the conflict-prone
  `app.py +282` patch.
- E with hardening is an isolated YAML record.
- Dropping `ComputerInfoLabel` slot (rather than renaming it) keeps the
  footer coherent without a stub button.

**The 10-point crystal test:** with these decisions, ALL combinations
of (effort cycling on/off) x (workflow active/inactive) x
(coordinator-set artifact_dir vs default) x (E rule fires/doesn't) x
(003408a follow-up adopted later or not) work without special cases.
We don't need `if accf332_adopted and not D_modal_adopted: ...`
branches. Each slice is genuinely independent at the implementation
level except for the documented hard couplings (A3 needs 003408a-(i);
B4 needs B3; D-footer rename needs D-modal -- which is why we drop the
rename).

---

## 5. Integration plan (cherry-pick playbook crosswalk)

**Cherry-pick order (recommended):**

```
1. accf332           (the feature commit -- with surgical conflict resolution)
2. 8f99f03           (tests, mechanical pairing)
3. 2f6ba2e           (docs, expect heavy drift -- merge by hand)
4. (skip a60e3fe)    (we're not adopting D, so the walkback is irrelevant)
```

Then a SEPARATE manual change (not from a cherry-pick): append the
7-line `pytest_needs_timeout` rule to `defaults/global/rules.yaml`
(E). Cherry-picking won't work because abast's diff context references
`no_pip_install` which we don't have.

Then a SEPARATE follow-up commit cleaning up the dropped scope:
- Remove `_disabled_rules` attribute and `get_disabled_rules` hook
  callback wiring (D-runtime-disable plumbing).
- Remove `widgets/modals/guardrails.py` (orphan after skipping D).
- Remove `claudechic/guardrails/digest.py` (orphan after skipping D).
- Drop `ComputerInfoLabel` from footer entirely (do not rename to
  `GuardrailsLabel`); remove its handler.
- Update `widgets/modals/__init__.py` and `widgets/__init__.py`
  re-exports to drop `DiagnosticsModal` (gone) and NOT add
  `GuardrailsModal` (skipped).
- Update `styles.tcss` to drop `DiagnosticsLabel:hover` and
  `ComputerInfoLabel:hover`; add `EffortLabel:hover` and
  `InfoLabel:hover`; do NOT add `GuardrailsLabel:hover`.

**Conflict-resolution invariants to preserve through any merge:**

1. `_token_store = OverrideTokenStore()` line in `app.py` (per
   `ec604bc` -- independent bug-fix, currently at line 1655). Verified
   present at our HEAD.
2. `SettingsLabel` widget and slot in `widgets/layout/footer.py` (our
   addition that abast doesn't have).
3. The 3-tier loader's per-tier override resolution in
   `workflows/loader.py` (Group C, +891 lines). The new `main_role:
   default` rejection block lands per-file; the resolution layer
   doesn't need re-checking (per engine-seam's analysis).
4. The `${CLAUDECHIC_ARTIFACT_DIR}` substitution path in
   `workflows/_substitute.py` (Group E). The new `$STATE_DIR` resolver
   should converge with this, not parallel it.
5. `tests/test_phase_injection.py` already uses our `parents[1]` repo
   root and our `defaults/` package layout. The `8f99f03` updates
   assume the same; cherry-pick should mostly apply but verify the
   `parents` index matches our layout.
6. The `mcp.py:980,983` falsy `agent.agent_type` checks must be
   rewritten (`if not agent.agent_type:` -> `if agent.agent_type in
   (None, DEFAULT_ROLE):`). Otherwise the broadcast-on-advance filter
   silently changes meaning when the default flips from `None` to
   `"default"`.

**Estimated effort (Composability synthesis -- not implementer estimate):**

| Step | Effort | Risk |
|------|--------|------|
| Cherry-pick `accf332` with conflict resolution (skipping D) | 2-3h | High (app.py is the hot zone -- 282 vs 779 line drift) |
| Forward-port engine A+B changes against our 3-tier loader + Group E | 1-2h | Medium |
| Integrate C (effort cycling) | 30min | Low |
| Modal restructure | 1h | Low (zero drift on the modified files) |
| Drop ComputerInfoLabel slot | 15min | Low |
| Cherry-pick `8f99f03` | 30min | Low (mechanical) |
| Manual merge of `2f6ba2e` | 30min | Low |
| Manual append of E + regex hardening | 15min | Low |
| Cleanup of orphan D code | 30min | Low |
| Test the result + fix mcp.py:980,983 sweep | 1h | Medium |
| **Total** | **8-10h** | **Medium overall** |

---

## 6. Follow-up questions for the user (deferred per UserAlignment D4)

These are CONTEXT-ONLY findings that the team has decomposed but is
not auto-deciding. Surface to user at the synthesis-handoff or
implementation-checkpoint:

1. **`003408a` re-pick.** Historian shows re-trigger risk is NONE.
   Three threads, three independent outcomes possible:
   - thread (ii) -- richer warn-rule reasoning text in `hooks.py`
     (~10 LOC, fully decoupled, real Q4 win): user wants to ship?
   - thread (i) -- per-check `cwd`/`base_dir` ctor params: subsumed
     by accf332's engine-level pinning; user wants the defense-in-depth
     anyway?
   - thread (iii) -- DEFAULT_ROLE handling in `mcp.py` spawn flow:
     downstream of B's adoption; user wants explicit sentinel handling
     in spawn validation?

2. **D resurrection path.** If a future user request demands
   guardrail introspection, the recommended shape is a `/guardrails`
   slash command (~30 LOC) that calls `compute_digest()` and prints to
   chat. Question for the user: shelve the SKIP for now, revisit only
   on explicit demand?

3. **Substitution syntax convergence.** Recommend adopting `${...}` as
   the documented convention going forward (matches our existing
   worktree and artifact-dir conventions); tolerate `$VAR` for backward
   compatibility. Question for the user: enforce the convention in a
   linter / `_substitute.py` deprecation warning, or leave it
   informal?

4. **Effort persistence.** Currently effort resets at every process
   restart. UI-surface flagged a follow-up to write the per-agent
   default to `~/.claudechic/config.yaml`. Question for the user: ship
   ephemeral first and add persistence later, or require persistence
   as part of the C adoption?

---

## 7. Terminology refinements (for TerminologyGuardian)

Updates to the working glossary based on the deep-dive:

1. **template variable**: refine to "string token in workflow content
   (YAML or markdown) substituted by claudechic at expansion time."
   TWO scopes: (1) check params at engine execution time, (2) prompt
   markdown at assembly time. THREE tokens currently:
   - `${CLAUDECHIC_ARTIFACT_DIR}` (coordinator-set, lazy)
   - `$STATE_DIR` (engine-computed, eager)
   - `$WORKFLOW_ROOT` (engine-computed, eager)
   Recommend: converge on `${...}` syntax.

2. **dynamic role**: refine to "agent role attribute
   (`agent.agent_type`) that mutates at runtime; guardrail hooks read
   the live value on every rule evaluation via a closure." Distinct
   from "agent_type passed at spawn" (static).

3. **promote / demote**: refine to "set/clear `agent.agent_type` on
   workflow activation/deactivation. Promotion replaces the
   `DEFAULT_ROLE` sentinel with the workflow's `main_role`; demotion
   restores `DEFAULT_ROLE`. No SDK reconnect needed because hooks
   read the attribute lazily."

4. **DEFAULT_ROLE sentinel**: literal string `"default"` declared in
   `workflows/agent_folders.py`. Reserved -- workflows MUST NOT
   declare `main_role: default`. Carries no workflow-specific
   guardrails; agents at this role are visible to global rules only.

5. **state_dir** (NEW): per-workflow scratch directory at
   `~/.claudechic/workflow_library/<project_key>/<workflow_id>/`.
   Engine-computed at activation, available before any phase runs.
   Distinct from `artifact_dir` (coordinator-chosen, set during Setup).

6. **workflow_root** (NEW): the launched-repo cwd, captured by the
   engine at activation. Used for both `$WORKFLOW_ROOT` substitution
   and as the default `cwd` for `command-output-check` execution.

7. **EffortLabel**: click-to-cycle widget for the SDK `effort`
   parameter. Levels: `low | medium | high | max` (`max` Opus-only).
   Click cycles forward; no Shift+Tab keybinding.

8. **Agent.effort**: str instance attribute on Agent (default `high`).
   Per-agent, process-ephemeral, NOT persisted (follow-up: persist to
   `~/.claudechic/config.yaml`).

9. **Unified Info modal**: the renamed footer slot opens
   `ComputerInfoModal` (class name unchanged). Shows System rows +
   Session rows; the Last Compaction row uses `scrollable=True`. The
   footer LABEL is renamed to `info`; the modal CLASS keeps its name.

10. **InfoSection.scrollable**: new opt-in boolean on `InfoSection`
    dataclass. Enables `VerticalScroll` wrapping in `InfoModal.compose()`.

11. **`_disabled_rules` (D, NOT adopting)** vs **`disabled_ids` (ours,
    persistent)**: do NOT introduce both. Keep `disabled_ids`. If
    session-ephemeral disable is genuinely needed later, name it
    `runtime_disabled_rule_ids` and document the layered semantics
    explicitly. Either way, one mechanism or the other, not both
    silently.

12. **digest** (D-data, NOT adopting): defined for completeness only.
    Static snapshot of `(active_wf, agent_role, current_phase,
    disabled_rules)` evaluated against each `Rule`/`Injection`,
    producing `list[GuardrailEntry]`. Computed on demand. Note: a
    "guardrails" digest covers ONLY guardrails, not hints; the name
    "guardrails" is honest but partial.

---

## 8. New collisions discovered (beyond Leadership findings)

1. **The `get_disabled_rules` callback double-add** between accf332 and
   003408a (section 3.3 above). Coordination point if both are picked.

2. **Latent dead-`$STATE_DIR` tokens** in our defaults from the testing
   sub-cycle cherry-pick (section 3.5 above). Adopting A fixes; not
   adopting requires a separate cleanup pass.

3. **`HitLogger` path drift in tutorial markdown.** Tutorial markdown
   (`defaults/workflows/tutorial/learner/{graduation, rules}.md` and
   `tutorial.yaml`) still references `<cwd>/.claude/hits.jsonl` even
   though `app.py` already moved it to `<cwd>/.claudechic/hits.jsonl`.
   Minor doc drift; worth fixing alongside E adoption.

4. **`mcp.py:980,983` falsy `agent.agent_type` checks** become
   silently wrong if B's default change `None -> "default"` lands
   without sweeping these sites. Sweep is mandatory; not optional.

5. **The `ComputerInfoLabel` slot becomes redundant after the modal
   restructure** even before any guardrails-rename consideration. The
   new `Info` modal absorbs everything `Sys` used to show. Drop the
   slot.

6. **GuardrailsModal contains a Textual widget-ID bug** for namespaced
   rule IDs (per guardrails-seam): IDs like `project-team:pip_block`
   contain `:` which Textual widget IDs disallow. Would crash on first
   render of a row for any namespaced rule. accf332's bundled
   `defaults/global/rules.yaml` has only unqualified IDs so the bug
   doesn't fire there, but our project-team rules WOULD trigger it.
   This is independent evidence supporting the SKIP-D recommendation.

---

## 9. Where the cluster's intent and our base diverge

| Aspect | abast's bet | Our base's bet | Resolution |
|--------|-------------|----------------|------------|
| Workflow state location | engine-picked (`workflow_library/`) | coordinator-picked (`set_artifact_dir`) | KEEP BOTH; document the layered pair (engine baseline + coordinator override) |
| Substitution syntax | `$VAR` | `${VAR}` | TOLERATE BOTH; document `${...}` as convention |
| Role lifecycle | per-agent attribute (`agent.agent_type`) flipped at activation | closure over `engine.manifest.main_role` | ADOPT abast's: cleaner, supports sub-agents |
| Guardrail introspection UI | full modal with checkbox toggles | none (just `disabled_ids` config + `/settings` editor) | SKIP for now; revisit as `/guardrails` slash command if user demands |
| Modal organisation | one merged Info modal (system + diagnostics) | two separate (Computer Info + Diagnostics) | ADOPT abast's: cleaner, frees a footer slot |
| Effort UX | runtime cycling label | hardcoded "high" with no UI | ADOPT abast's: clean orthogonal addition |
| Test cwd robustness | engine-level `params.setdefault("cwd", workflow_root)` (in accf332) plus ctor-level `cwd=` (in 003408a) | nothing | ADOPT engine-level (via accf332); leave 003408a-thread-i to user follow-up |

---

## 10. Open recommendation: do not let "abast has it" win

Per Skeptic A2/A3/A6: assumption that abast's commit messages reflect
intent (treat as hints, not specs); assumption that "sync" implies
adoption (default neutral); cargo-cult risk if we can't articulate
user-visible "before vs after" in one sentence per feature.

The verdicts above all pass Q4 with concrete users:
- A: anyone running `/project_team` whose YAML/markdown contains
  `$STATE_DIR` (today: latent bug)
- B: anyone whose coordinator role has `roles: [coordinator]`-scoped
  rules
- C: an Opus user mid-session who wants to flip extended thinking on
- E: anyone running `pytest` from an agent who has been bitten by a
  hung test
- modal restructure: a developer debugging a session who wants to see
  Last Compaction AND Python/SDK versions in one click

D fails Q4: best one-sentence delta is "click 'guardrails' for a
session-ephemeral checkbox view of rules", and we cannot name a
concrete Spruston Lab user asking for it. Combined with the
abast-walk-back signal (`a60e3fe`) and the persistence-ambiguity hole,
SKIP is the composability-honest call.

---

## 11. Reconciliation with team consensus -- explicit answers to Coordinator's items 1-5

This section was added after reading the leadership-team specification
deliverables (Skeptic, Terminology, UserAlignment) and the first-pass
axis spec files (`spec_engine_seam.md`, `spec_guardrails_seam.md`,
`spec_ui_surface.md`) plus the consolidated decisions in `STATUS.md`.
It explicitly addresses the five items in the Coordinator's nudge.

### Item 1 -- Compositional consistency check

The 3 axis-agent recommendations compose without cycles or missing
prerequisites. Dependency graph (each `(slice, outcome, blocking-deps)`):

```
A1 -> []                                   (rename only)
A2 -> SKIP                                 (no deps; rejected on TC2)
A3 -> [003408a-(i)]                        (FACT, surfaced to user)
A4 -> []
B1 -> []
B2 -> [mcp.py:980,983 sweep]               (mandatory)
B3 -> []
B4 -> [B3]
B5 -> []
C  -> [tooltip OR widget-text adaptation]  (UX)
modal-restructure -> []                    (no D dep -- ui-surface verified)
D-* -> SKIP all                            (drops a whole subgraph)
E  -> [regex hardening]                    (Skeptic precondition)
```

No cycles. The only prerequisites that cross axes:
- A3 -> 003408a thread (i): out-of-cluster; surfaced as user follow-up.
- B2 sweep at `mcp.py:980,983`: in-cluster; mandatory.
- modal-restructure independence from D: verified by ui-surface.

**Consistent.**

### Item 2 -- Cross-axis seam audit

The most contested cross-axis surface is `_activate_workflow` /
`_make_options` / `_merged_hooks` / `_guardrail_hooks` in `app.py`.
Three axes touch it:

- engine-seam owns B3 (`_activate_workflow` promote/demote insertion
  points) and B4 (`agent=` param threading).
- ui-surface owns the surrounding flow (chicsession naming, restore
  prompt, the `_make_options` `effort_level` resolution).
- guardrails-seam owns the now-skipped D modal handlers (which would
  have lived in this same `app.py` neighborhood).

The team's consolidated proposal is coherent because **D-skip removes
guardrails-seam's claim on this surface entirely** -- the
`on_guardrails_label_requested`, `on_guardrail_toggled`,
`_disabled_rules`, and `get_disabled_rules` callback wiring all drop
out. The remaining work in this surface is just engine-seam (B3+B4)
and ui-surface (C wiring).

ui-surface F1-F6 inter-axis flags are all addressed:
- F1 (don't rename ComputerInfoLabel if D skips) -- adopted.
- F2 (`_disabled_rules` distinct from `disabled_ids`, TC4) -- D skip
  drops `_disabled_rules` entirely, no ambiguity.
- F3 (`agent=` plumbing is B convenience; if B skips and C adopts,
  fall back to `effort_level=self._agent.effort`) -- adopted.
- F4 (InfoLabel rename separable from GuardrailsLabel rename) --
  adopted.
- F5 (preserve `SettingsLabel` through any footer cherry-pick) --
  adopted as conflict-resolution invariant in §5.
- F6 (`widgets/modals/__init__.py` edit differs by D outcome) --
  adopted (D skip means drop `DiagnosticsModal` from `__all__`, do
  NOT add `GuardrailsModal`).

**Coherent.**

### Item 3 -- Architecture-level call

Composability AFFIRMS the team consensus on all three:

- **Substitution mechanism convergence (TC3 + engine-seam):** AFFIRM
  -- standardize on `${VAR}`. Bare `$VAR` rejected for new tokens.
- **State-location collapse (TC2 + engine-seam A2):** AFFIRM -- SKIP
  `~/.claudechic/workflow_library/` and `paths.py`. Our
  `set_artifact_dir` is strictly more flexible.
- **Disable-mechanism unification (TC4 + ui-surface F2 +
  guardrails-seam):** AFFIRM -- skip `_disabled_rules`. D-skip
  achieves this naturally; no second disable layer enters our base.

These three calls together close three crystal holes that the cluster
as shipped would have introduced.

### Item 4 -- Granularity translation

The user-facing report uses A/B/C/D/E (abast's exact 4-feature wording
plus the stowaway, per UserAlignment FLAG 1 -- the user's framing
question is "should we pick it up here?" at the named-feature level).

The implementer's checklist uses the slice view (A1-A4, B1-B5, plus
the D and modal-restructure decomposition). Engine-seam's
finer-than-A/B granularity is what falls out the moment we examine the
diff -- it is the implementer's fact, not a re-framing of the user's
question.

**Recommendation: present BOTH views in the user-facing report.** The
headline table uses A/B/C/D/E for the user's decision. The
"Integration plan" addendum uses the slice view for the implementer.
Two views of the same crystal point. UserAlignment FLAG 1 is honored;
Skeptic's "per-sub-feature decomposition" demand is honored.

### Item 5 -- Risk landscape

The riskiest dependency chain in the recommended crystal point:

**`B3` adapt (hand-merge of `_activate_workflow` promote/demote).**
This is the only ADAPT-with-real-merge-work in the slice list. Skeptic
flagged it specifically: our `app.py` already has 17 `main_role`
references; the abast +282 patch overlaps significantly with code we
already wrote. Risks:
1. Implementer cargo-picks the whole +282 patch and we ship duplicate /
   conflicting role-resolution paths.
2. Implementer hand-merges incorrectly and `agent.agent_type` doesn't
   actually flip on activation -- silent failure (tools see
   `agent.agent_type == DEFAULT_ROLE` always; role-scoped rules never
   fire on the main agent).
3. The `mcp.py:980,983` sweep is forgotten -- silent broadcast filter
   change.

Mitigation: B3 deserves its own line-by-line conflict map before the
implementer starts. Skeptic flagged this in Q2 completeness gates;
historian deferred to "after per-feature decisions made" -- now is
when historian's thorough-pass should fire.

Other risks (lower):
- A3 ships as dead code if user declines 003408a follow-up. Mitigation:
  surface the coupling as an explicit follow-up question (already
  in §6).
- E false-positives if regex hardening is sloppy. Mitigation: Skeptic
  documented a tighter pattern; treat as precondition.
- Conflict-resolution invariants (`_token_store`, `SettingsLabel`,
  3-tier loader) silently dropped during the +282 merge. Mitigation:
  enumerate as invariants in §5; verify post-merge.

The full +282 `app.py` patch is the throat through which most of the
work passes. Per ui-surface, it splits roughly: 32% B (dynamic roles),
15-18% D (guardrails -- skipped), 16% A (state dir + template vars),
10% C (effort), with the rest formatting/other. Skipping D removes
~15-18%; the dominant slice is B, not D. **The cherry-pick playbook
must treat the +282 patch as a series of surgical inserts, not a
wholesale apply.**

---

## 12. D reframe -- architectural fit

This section was added after the user's redirect: D is no longer
"user-facing modal" but **agent self-awareness via filtered rules per
agent, exposed via MCP and/or injected into launch prompts**. The
question for Composability is upstream architectural support -- where
do the seams live in our existing code, and what are the trade-offs
between candidate placements? guardrails-seam picks the design; this
section maps the topology.

### 12.1 Existing rule scoping is per-call, not projected

There is **no `applicable_rules(role, phase)` projection function on
our base.** `Rule` (`claudechic/guardrails/rules.py:21-39`) carries
`roles`, `exclude_roles`, `phases`, `exclude_phases`, plus `namespace`
and `tier` provenance. The four scope predicates exist as pure
functions (`should_skip_for_role` at `rules.py:185`,
`should_skip_for_phase` at `rules.py:197`, namespace check inline at
`hooks.py:91`, `matches_trigger` similarly).

The hook closure (`claudechic/guardrails/hooks.py:67-181`) iterates
the FULL rule set per tool call and applies the four predicates
inline. `loader.load()` runs FRESH per call (`hooks.py:73`, comment
"no mtime caching - NFS safe") -- not a snapshot. Building a
projection helper is mechanically straightforward: the predicates are
already factored.

**Seam:** a new `applicable_rules(load_result, role, phase, active_wf)`
helper composing the existing predicates. Place either in
`guardrails/rules.py` or in a new `guardrails/projection.py`. Cost:
additive, ~20 LOC.

### 12.2 Existing prompt-injection points -- three sites, one common path

`assemble_phase_prompt` (`claudechic/workflows/agent_folders.py:64`)
is the single function that concatenates `identity.md` +
`{phase}.md`. Three call sites flow through it:

| Site | Where | Hook nature |
|------|-------|-------------|
| Workflow activation (main agent kickoff) | `app.py:1922-1941` `_activate_workflow` | Returns the kickoff body sent via `_send_to_active_agent` |
| Sub-agent spawn | `mcp.py:277-307` (within `spawn_agent`) | Concatenates `f"{folder_prompt}\n\n---\n\n{prompt}"` -- already a concatenation point |
| PostCompact + advance-phase re-inject | `app.py:2165-2212` `_inject_phase_prompt_to_main_agent`; also `agent_folders.py:94-138` `create_post_compact_hook` | Re-runs `assemble_phase_prompt` and sends via `_send_to_active_agent` |

**Today, identity + phase markdown is the entire content surface.**
Nothing else is concatenated in. A "render rules" string built from
the projection helper above could land at any of:
- inside `assemble_phase_prompt` (signature-extending: needs loader + role + phase to flow in -- currently only `workflow_dir`, `role_name`, `current_phase`, `artifact_dir` are passed)
- at each of the three call sites (signature-preserving: build the rule block separately, concat afterward)

The signature-preserving option is structurally cleaner -- it lets
`agent_folders.py` stay loader-unaware (preserves the existing seam
between workflow content and runtime guardrail state).

**The pre-existing delivery primitive** (added by our `d001e30`
"in-memory phase-prompt delivery") is `_send_to_active_agent(prompt:
str, *, display_as: str | None = None)` at `app.py:2567-2581`. It
takes any string body and dispatches to the active agent's SDK via
`Agent.send()` -- no file I/O. Both kickoff and post-advance
re-injection already flow through it. **The user's D-reframe needs
exactly this delivery channel for the kickoff/PostCompact rule
injection** (option C in §12.5). The substrate is already in place
from our own Group D work.

### 12.3 MCP placement: `get_phase` already partially does the projection

`get_phase` (`mcp.py:1087-1164`) **already reports rule counts** --
`Rules: {N} active ({M} inactive)` (lines 1144-1147) -- but only
applies the namespace filter via an inline `_is_active(item)`
predicate (no role/phase scope filter). So:

- `get_phase`'s "8 active" overstates what would actually fire for a
  given agent (a role-scoped rule that doesn't apply to the active
  agent counts as "active" in `get_phase`'s view).
- Injections are listed at id+trigger+phases fidelity (line
  1154-1156); rules are NOT listed at the same fidelity (count only).

Three placement options:
1. **Deepen `get_phase`** to emit the role/phase-filtered rule list at
   injection-style fidelity. Same tool, richer payload. Risk: changes
   an existing tool's output shape.
2. **New `get_applicable_rules` tool** alongside `get_phase`. Two
   tools, partial overlap (`get_phase` keeps the count summary; the
   new tool gives the full per-rule view).
3. **Replace** `get_phase`'s rule count entirely with the projection
   tool's output. Cleaner end-state but breaks any caller currently
   parsing `get_phase`'s string.

guardrails-seam picks; Composability flags option (3) as the loudest
breaking change and option (2) as the lowest-risk additive choice.

### 12.4 Compositional issues -- four real ones

**(a) Ordering/availability.** Rules first parse at startup
(`app.py:1681` `_init_workflow_infrastructure`); `_discover_workflows`
calls `loader.load()` once and stores `_load_result` (`app.py:1689`).
The hook then re-invokes `loader.load()` per call (`hooks.py:73`)
without using `_load_result`. **Inconsistency**: the hook sees raw
loader output (no project-config disable filter applied); `get_phase`
and the workflow registry see `_load_result` (filtered). A projection
helper could read from either. Picking which one closes a real
correctness gap.

**(b) Live updates via `/settings`.** Toggling `disabled_ids` runs
`mgr.refresh_guardrails()` (`screens/settings.py:898-903`), which is
documented as a **no-op seam for running agents**
(`agent_manager.py:360-383`): "applies to NEW agents only --
already-running SDK clients are not re-connected." So:
- A spawn-time prompt injection (option B in §12.5) shows whatever
  rules were live at spawn -- a settings change mid-session is
  invisible to that agent's prompt until the agent is re-spawned.
- An MCP-only tool (option A) reflects current state on the next call
  -- the hook-side `loader.load()` IS re-resolved per call.
- A PostCompact injection (option C) re-renders on `/compact`, so the
  rule view refreshes at compaction time but not earlier.

This is the real composability hole: live updates and prompt-frozen
content are different semantics. Picking one or both is a design call.

**(c) Sub-agents inherit their OWN role view, not the parent's.**
`spawn_agent` validates the role folder (`mcp.py:209-230`), passes
`agent_type=...` to `agent_manager.create` (`mcp.py:259`), which
threads it into `_make_options(agent_type=...)`
(`agent_manager.py:120-174`). The hook closure (`app.py:834-835`) is
**statically bound** to the spawned sub-agent's own type. So a
coordinator that sees "rules X, Y, Z" and spawns a coordinator-typed
sub-agent will give that sub-agent the same X/Y/Z view; spawning a
skeptic-typed sub-agent gives a DIFFERENT view. Per-agent projection
is the natural shape; per-spawn-tree-inheritance is NOT.

**(d) The hook-vs-`get_phase` filter inconsistency** (point a above)
becomes a NEW user-visible bug class if D-reframe ships: the agent
reads its rule list from MCP/prompt, then a tool call fires a rule
that doesn't appear in the list (because the hook re-resolved from a
different source). Closing this requires picking one source of truth
for rule resolution and using it in both the hook and the projection.

### 12.5 Simplest-viable design space (cost only -- no recommendation)

The four points the existing architecture supports cheaply:

| Option | Files changed | Additive vs structural | Reuse |
|--------|---------------|------------------------|-------|
| **A. MCP-only** (`get_applicable_rules` tool, OR deepen `get_phase`) | `mcp.py` (+~30 LOC) + new helper in `guardrails/rules.py` or `guardrails/projection.py` (+~20 LOC) | Additive | Existing scope predicates; the `_is_active` pattern from `get_phase`; loader-load infrastructure |
| **B. Spawn-time prompt injection** | `mcp.py:294-301` (one extra concat) + `agent_folders.py` if signature changes | Additive at concat site; structural if `assemble_phase_prompt` signature gains loader/role/phase | Same projection helper |
| **C. Kickoff/PostCompact prompt injection** | `app.py:1922-1941` (one concat) + `agent_folders.py:117-134` (PostCompact already re-runs assembly) | Additive | Same projection helper; the kickoff already produces a single string body |
| **D. A + B (MCP + spawn injection)** | Union of A and B | Additive | Same helper called from two sites |

Composability observations (no recommendation):

- **All four options share one helper** (`applicable_rules(role,
  phase, active_wf)`). The seam does not depend on the placement
  decision.
- **B + C together would mean BOTH spawn-time and post-compact
  rendering** -- the agent's prompt always contains a current rule
  block. This converges with the "frozen prompt" semantic.
- **A alone gives mid-session updates for free** (per-call
  re-resolution) but requires the agent to remember to call the tool.
- **No option closes the hook-vs-`get_phase` source-of-truth
  inconsistency by itself**; that is an orthogonal cleanup that should
  precede or accompany whichever option(s) ship.

### 12.6 Pre-existing substrate from our `d001e30` (Group D)

Coordinator-supplied context: our `d001e30` ("claudechic-awareness
install + in-memory phase-prompt delivery", +1253 lines) is in the
same conceptual space as the user's D-reframe. Inventoried against
the four design points in §12.5:

**`d001e30` part (1) -- Awareness install** writes bundled
`claudechic/context/*.md` (8 files: claudechic-overview, checks-system,
guardrails-system, hints-system, manifest-yaml, multi-agent-architecture,
workflows-system, CLAUDE.md) to `~/.claude/rules/claudechic_*.md`. The
SDK loads these as Claude rules in EVERY session on the host.

This is a **CLAUDE-CODE-WIDE channel**, not per-agent: every Claude
session sees the same docs. For the D-reframe, this channel is **not
a fit** for per-agent role-filtered rules -- the docs are static and
host-scoped, not session-scoped or agent-scoped. (Could be used for a
"here's what claudechic IS" awareness layer; not for "here are the
rules that apply to YOU right now.")

**`d001e30` part (2) -- In-memory phase-prompt delivery** is the
substrate that DOES fit. Specifically:

| What `d001e30` already provides | Where | Fits which §12.5 option |
|---------------------------------|-------|-------------------------|
| `_send_to_active_agent(prompt)` -- deliver any string body to the active agent without file I/O | `app.py:2567-2581` | B (spawn injection only if extended), C (kickoff/PostCompact) |
| `_activate_workflow` calls `assemble_phase_prompt` and dispatches via `_send_to_active_agent` | `app.py:1922-1941` | C kickoff site |
| `_inject_phase_prompt_to_main_agent` re-injects after advance via the same primitive | `app.py:2165-2212` | C re-inject site |
| `create_post_compact_hook` re-runs assembly on `/compact` | `agent_folders.py:94-138` | C PostCompact site |
| `mcp.py:_make_advance_phase` delegates the inline prompt response to the tool result (no double-inject on coordinator) | `mcp.py` (touched by `d001e30`) | Means a rule block in the kickoff body wouldn't be double-rendered on advance |

So for option C (kickoff + PostCompact rule injection): **all three
call sites already exist on our base, all three already flow through
`_send_to_active_agent`, and the path-out-of-disk has been verified
end-to-end** (per `d001e30`'s `tests/test_phase_prompt_delivery.py`,
including a real-ChatApp end-to-end test that asserts the active
agent's first user message contains the assembled prompt content).
The new code for C is just (a) the projection helper (~20 LOC) and
(b) one string-append at each of two-or-three call sites.

For option B (spawn injection): `mcp.py:294-301` already concats
`f"{folder_prompt}\n\n---\n\n{prompt}"`. Adding a rule block is one
more concatenation. Independent of `d001e30` but compatible.

For option A (MCP-only): unchanged from §12.5 -- new `mcp.py` tool
plus the projection helper.

**Identity primitive availability** (Coordinator's note 4): our
`a743423` confirms `main_role` resolution works on our base via the
existing closure-based dynamic resolver (`app.py:837-841`). So:

- The MAIN agent's role is already queryable via
  `engine.manifest.main_role` after activation -- this is the identity
  primitive for filtering rules for the main agent. **Available
  before B lands.**
- SUB-agents' roles are statically bound at spawn via the `agent_type`
  parameter (closure-captured, `app.py:834-835`). Identity is also
  already queryable. Available before B lands.
- abast's B (per-agent attribute flip on `agent.agent_type`) is a
  cleaner mechanism but not a hard prerequisite for the D-reframe. The
  projection helper can read identity from either source: existing
  closure for the main agent OR `agent.agent_type` for sub-agents (or
  for the main agent post-B).

**Bottom-line update to §12.5:** the design-space cost analysis is
revised downward. The "files changed" column for option C should now
read "ZERO new infrastructure -- only projection helper + concat at
existing sites." The D-reframe is a **small extension to existing
Group D infrastructure**, not new scaffolding.

### 12.7 What this means for the cluster sync recommendation

The original D (modal + checkbox toggles + `_disabled_rules`) is
SKIPPED per §1. The reframed D (per-agent rule projection + MCP
and/or prompt injection) is **architecturally cheap and reuses zero
code from accf332** -- the new helper, the `mcp.py` tool addition,
and the `agent_folders.py` concat hook are all things we'd write
fresh in our own style, not cherry-pick from abast.

So:
- The cluster sync recommendation for D is unchanged: **SKIP** the
  abast cluster's D code.
- The user's D-reframe is a **separate piece of new work on our base**
  that the team can scope in a follow-up. It is not a sub-feature of
  the accf332 sync.

guardrails-seam holds the verdict on which option(s) to pursue and
when; Composability has handed over the seam map.

---

## 13. Pointers

- Engine-seam axis findings: `./engine-seam.md`
- Guardrails-seam axis findings: `./guardrails-seam.md`
- UI-surface axis findings: `./ui-surface.md`
- Leadership-phase consolidated: `../leadership_findings.md`
- Historian triage: `../historian_findings.md`
- Coordinator state: `../STATUS.md`

---

*End of Composability axis Specification synthesis.*
