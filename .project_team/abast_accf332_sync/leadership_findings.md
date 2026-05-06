# Leadership Phase Findings -- abast_accf332_sync

Five agents replied: composability, terminology, skeptic, user_alignment,
historian. This document preserves the substantive content for axis-agents
in Specification. STATUS.md holds the decisions and open issues.

---

## 1. Cluster boundary (DECIDED)

| # | SHA | Type | Author date | Subject |
|---|-----|------|-------------|---------|
| 1 | `accf332df9e3f1a9c13e5951bec1a064973b6c96` | feat | 2026-04-26 17:27:45 | workflow template variables, dynamic roles, effort cycling, guardrails UI |
| 2 | `8f99f03` | test | 2026-04-26 17:27:48 | tests for template variables, engine checks, widget refactor |
| 3 | `2f6ba2e` | docs | 2026-04-26 17:28:00 | file-map update |
| 4 | `a60e3fe` | chore | 2026-04-26 17:47:16 | stub out guardrails modal with not-yet-implemented notice |

Identified by historian, independently corroborated by terminology.
Composability proposed `003408a` instead of `a60e3fe`; resolved by
treating `003408a` as out-of-cluster flagged dependency.

The cluster is non-contiguous on `abast/main`: between commits 3 and 4
sit `1d6d432` and `ff1c5ae` (MCP-tool refactor: tell_agent merge +
ask_agent rename). FLAGGED, not in cluster.

---

## 2. Sub-feature decomposition (Composability)

The bundled commit title is itself a "bundled choices" smell. Decompose
into 5 candidate adopt/adapt/skip units:

1. **Workflow template variables** -- substitution in YAML manifests.
   Touches `workflows/engine.py`, `workflows/loader.py`,
   `workflows/agent_folders.py`, plus per-role `*.md` updates in
   `defaults/workflows/project_team/*` and `tutorial/learner/*`.
2. **Dynamic roles** -- runtime role assembly; depends on (1) for
   variable resolution into role identity / phase markdown. Same engine
   surface.
3. **Effort cycling** -- footer widget cycling an "effort" knob (likely
   model-aware). Lives in `app.py` + `widgets/layout/footer.py`.
4. **Guardrails UI** -- new `guardrails/digest.py` (+128),
   new `widgets/modals/guardrails.py` (+186), `widgets/modals/base.py`
   refactor, `widgets/modals/computer_info.py` extension, footer hooks,
   `defaults/global/rules.yaml` content additions.
5. **(precursor, OUT OF CLUSTER) `003408a` advance-check messaging fix**
   -- `mcp.py`, `guardrails/hooks.py`, `checks/builtins.py`. Standalone
   bug-fix; can be evaluated independently. We previously
   cherry-picked + reverted on our side -- revert reason needed.

Architectural-layer axes (the WHERE):

- A. workflow engine seam -- `workflows/engine.py`, `loader.py`,
  `agent_folders.py`. Highest collision area vs our Group C/E.
- B. guardrail layer seam -- `guardrails/`, `checks/`, `mcp.py`. Data
  side roughly orthogonal to UI side.
- C. UI / widget surface -- `widgets/modals/*`, `widgets/layout/footer.py`,
  `app.py`, `styles.tcss`. Note destructive change:
  `widgets/modals/diagnostics.py` is **deleted** (-194 lines).
- D. Defaults content -- per-role markdown updates, rules.yaml content.
  Adoptable independently if engine is sorted.
- E. Tests + docs -- mechanically pair with whichever sub-features adopt.

Compositional law: every recommendation expressed as
`(sub-feature, outcome in {adopt, adapt, skip, partial}, blocking-deps)`.

---

## 3. Working glossary (Terminology -- not final)

### workflow template variable
Working def: `$NAME` token in workflow YAML manifest, substituted by
loader at load time. Commit msg names two: `$STATE_DIR` and `$WORKFLOW_ROOT`.
State moves to `~/.claudechic/workflow_library/<project_key>/<project_name>/`
per `claudechic/paths.py::compute_state_dir`.

Open: complete variable list? substitution timing (load vs activation)?
syntax (`$VAR` vs `${VAR}`)?

Collision risk: HIGH (see section 5).

### dynamic role
Working def: agent role assigned at workflow-activation time rather than
at agent-spawn time. Commit msg: "main agent is promoted to `main_role`
on workflow activation and demoted on deactivation, no reconnect needed."
Loader gains a guard: `main_role` cannot equal `DEFAULT_ROLE` sentinel.

Open: what does "promoted" mean operationally (identity swap? prompt
re-injection?)? Does demotion clear history? How does this interact
with `spawn_agent type=`?

Collision risk: MEDIUM. `DEFAULT_ROLE` was on our tree briefly
(cherry-pick `1d3f824`, reverted in `ec604bc`); `accf332` re-introduces
it as a reserved sentinel.

### effort cycling / effort level
Working def: footer widget (`EffortLabel`) that cycles through
"model-aware effort levels." Likely maps to Anthropic SDK thinking-budget
or similar per-model settings.

Open: levels (low/med/high? numeric?)? persistence across sessions?
per-agent or app-global?

Collision risk: LOW. Watch for confusion with permission-mode cycling
(already on Shift+Tab) since both are footer-cycle UX.

### guardrails UI / GuardrailsModal
Working def: modal listing all loaded `Rule` and `Injection` objects
with per-row toggle checkboxes for runtime enable/disable. Replaces /
merges with `DiagnosticsModal` (deleted in `accf332`). Stub landed in
`a60e3fe`.

Open: does "toggle" persist (write back to `disabled_ids`?) or is it
ephemeral session state? Does it cover hints too, or only guardrails?
Does it include the `pytest_needs_timeout` warn rule added in the
same commit?

Collision risk: HIGH (see section 5).

### Bonus terms surfaced from the diff
- `workflow_library/` (new dir) vs our `chicsessions/` and
  `${CLAUDECHIC_ARTIFACT_DIR}` -- 3 "where workflow state lives"
  concepts; need a single picture.
- "unified Info modal" -- abast merged `DiagnosticsModal` into it.
  We currently have separate `InfoModal` base + `ComputerInfoModal` +
  `DiagnosticsModal`; need to pin which modals correspond.
- `guardrails/digest.py` (new file, 128 lines) -- "digest" not a current
  term. Rendering helper? Snapshot? TBD.

---

## 4. Skeptic's standing posture

### Assumptions baked into this investigation (A1-A9)

A1. The four commits are a coherent feature set -- maybe just bundled for
shipping convenience.
A2. abast's commit messages reflect their actual intent -- treat as hints,
not specs.
A3. "Sync" implies adoption is the default -- the user explicitly left
the question open; default neutral.
A4. Features composable on abast remain composable on our base -- abast
may have prerequisites we don't.
A5. Our public surface can absorb their changes without breakage --
must inventory contract surface, not just feature surface.
A6. Cargo-cult risk -- if we can't articulate user-visible "before vs
after" in one sentence per feature, we're cargo-culting.
A7. Pre-existing fork-divergence reports are still accurate -- abast HEAD
moved; re-derive against current.
A8. "Reimplement on our base" is meaningfully different from "adopt" --
sometimes the right answer is "do nothing".
A9. Tests on abast cover the features adequately for our integration
points -- adoption without test re-derivation is a hidden shortcut.

### Falsification questions (Q1-Q6) -- "yes" => skip or demote

Q1. Does the feature solve a problem that does not apply to our deployment context?
Q2. Does the feature require breaking changes to a stable public contract
(settings.json schema, MCP tool API, observer protocols, workflow YAML
schema, on-disk state file format) without a migration path?
Q3. Does the feature depend on abast-specific infrastructure that we don't
have and that would itself need to be ported first?
Q4. Can we articulate the user-visible "before vs after" in one sentence,
with a concrete user who would notice the difference? (No -> cargo-culting)
Q5. Does a simpler in-tree change deliver 80% of the benefit at 20% of the cost?
Q6. Does the feature regress a property we currently rely on?

### Standing posture for Specification

- Push back on any feature whose justification reduces to "abast has it."
- Demand a concrete user-visible delta and contract-surface impact
  inventory per feature.
- Distinguish *essential* complexity from *accidental* complexity.
- Don't let "simpler" become "incomplete".

---

## 5. Terminology collision concerns for Composability

1. **"guardrails" is overloaded already.** Already 4 meanings in our tree
   (enforcement system / rule-set / bool master switch / disable list).
   abast's `GuardrailsModal` adds a 5th: runtime per-rule toggle.
   Decision needed: does the toggle duplicate `disabled_ids` (then say so)
   or is it a new meaning (then 4-way ambiguity)?
   *Recommendation:* pick the toggle's semantics and name accordingly
   (`runtime_enabled` vs `disabled_ids`).

2. **"template variable" overlaps with worktree path template.** We
   already have `${repo_name}` / `${branch_name}` substitution in worktree
   path config; Group E added `${CLAUDECHIC_ARTIFACT_DIR}` for workflow
   YAML; abast adds `$STATE_DIR` and `$WORKFLOW_ROOT`. Three substitution
   mechanisms, two syntaxes (`$VAR` vs `${VAR}`), three scopes.
   *Recommendation:* converge on one syntax and one resolver, or
   explicitly document them as three distinct substitution domains with
   non-overlapping variable names.

3. **role-lifecycle vocabulary fragmented.** We say "agent role" loosely;
   abast adds "main_role / promote / demote / DEFAULT_ROLE sentinel".
   *Recommendation:* if adopt, define a single role-lifecycle glossary
   (states + transitions) before any code lands.

4. **`workflow_library/` vs `chicsessions/` vs artifact dir.** abast hasn't
   seen our Group B/E. Picking up `accf332` as-is would add a third state
   location with overlapping purpose.
   *Recommendation:* draw the state-dir map and decide adopt/adapt/skip
   per-feature with this in mind.

---

## 6. Vision-drift flags (UserAlignment)

- **FLAG 1 -- domain terms (medium).** Use abast's exact 4-feature wording
  in the final report; flag any rename and require user approval.
- **FLAG 2 -- "sync" framing (low).** User's framing is `sync`, not
  `review`. Implicit destination is integration. Don't slide into pure
  analysis mode.
- **FLAG 3 -- outcome categories (low).** We widened binary -> 4 categories
  (adopt/adapt/skip/partial). On record. Defer to binary if user pushes back.
- **FLAG 4 -- cluster boundary (medium).** Resolved (see section 1).

## 7. Must-answer list (UserAlignment) -- final report structure

Use user's exact questions as section headers:

1. "What is it about?" -- per-commit narrative.
2. "What is the intent?" -- cluster-level WHY.
3. "Should we pick it up here?" -- per-feature recommendation.
4. "Can we reimplement on our base?" -- per-feature feasibility +
   conflicts + effort estimate.

Plus addenda: (5) cluster identification, (6) integration plan for
adopt/adapt items, (7) flagged-not-chased list.

---

## 8. Specification-phase plan (Composability)

3 axis-agents to spawn (no separate agents for content axis D or
tests/docs axis E -- they fall out of the others):

| Agent | Sub-features | Layer axes | Must answer |
|-------|--------------|------------|-------------|
| **engine-seam** | (1) workflow template variables, (2) dynamic roles | A | ONE substitution mechanism vs. two clean axes? Does dynamic-role assembly collide with our in-memory phase delivery? |
| **guardrails-seam** | (4) guardrails UI, (5-flagged) `003408a` advance-check fix | B | Are data side (digest, rules.yaml) and UI side (modal, footer) cleanly separable? |
| **UI-surface** | (3) effort cycling | C | Is effort-cycling self-contained? What does `widgets/modals/diagnostics.py` deletion break? |

---

## 9. Hand-off contract for Specification-phase axis-agents

Each axis-agent must, per Skeptic:

- Articulate user-visible "before vs after" in one sentence per
  sub-feature, with a concrete user who would notice.
- Inventory contract-surface impact (settings.json, MCP API, observer
  protocols, workflow YAML schema, on-disk state).
- Apply Q1-Q6 falsification questions; report any "yes" answers.
- Distinguish essential vs accidental complexity.

Each axis-agent must, per Composability:

- Express recommendation as
  `(sub-feature, outcome in {adopt, adapt, skip, partial}, blocking-deps)`.
- Surface inter-feature dependencies (does X need Y on the same axis?).

Each axis-agent must, per UserAlignment:

- Use abast's exact feature labels.
- Avoid sliding into pure-analysis mode -- destination is integration if
  feasible.

Each axis-agent must, per Terminology:

- Refine the working glossary as facts come in.
- Surface any new collisions discovered during deep-dive.
