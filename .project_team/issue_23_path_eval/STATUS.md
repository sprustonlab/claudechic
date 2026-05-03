# STATUS — issue_23_path_eval

**Last updated:** 2026-04-25
**Working dir:** `/groups/spruston/home/moharb/claudechic`
**Git remote:** `https://github.com/sprustonlab/claudechic.git`
**Active workflow:** `project-team`
**Current phase:** `specification`

---

## Vision Summary (approved)

### Goal
Produce a Leadership-evaluated written recommendation choosing between **Path 1** (selectively pull from abast first, then implement #23) and **Path 2** (implement #23 first, then selectively pull from abast), so we address "independent claudechic settings" without losing divergent feature work on either fork.

### Value
sprustonlab and abast both forked `mrocklin/claudechic` and have diverged significantly. Issue #23 is non-trivial (touches config layout and the launching repo's root). Picking the wrong sequence risks un-mergeable conflicts that destroy feature work on either side. A structured, multi-perspective evaluation *before* any code moves is dramatically cheaper than an aborted merge.

### Domain terms
- **sprustonlab/claudechic** — Our fork (this repo).
- **abast/claudechic** — Sibling fork; significantly diverged.
- **mrocklin/claudechic** — Shared upstream. **Out of scope** for this run.
- **Issue #23** — sprustonlab issue. Body title: "Settings window + configuration reference documentation." Userprompt boundary concern (don't mix Claude vs claudechic settings; only `.claudechic/` in launched-repo root) is *derived scope*, not in the issue body verbatim.
- **Independent settings** — (a) Claude and claudechic settings do not mix; (b) launched repo's root contains nothing from us except `.claudechic/`.
- **Path 1** — Selectively pull from abast → implement #23.
- **Path 2** — Implement #23 → selectively pull from abast.
- **Selective pull** — Cherry-pick or equivalent; not all-or-nothing merge. Default mechanism for any abast integration.

### Success looks like
- A written recommendation document including:
  - Fork Diff Report (per-file divergence map; #23 surface read; hazard summary).
  - Independent evaluations from Leadership (Composability, TerminologyGuardian, Skeptic, UserAlignment).
  - Risk analysis on merge conflicts, lost work, settings boundary.
  - Clear recommended path with rationale.
- User has confidence to start the chosen path in a separate session.
- **No code changes** in this run.
- **No time estimates** in any deliverable — describe details of what needs to happen, not how long.

### Failure looks like
- Recommendation issued without inspecting actual fork diffs.
- claude-vs-claudechic settings boundary blurred.
- Recommendation triggers loss of feature work when later executed.
- Coordinator does the diff/analysis instead of delegating.
- Scope creep into implementing #23.
- Time estimates leaking into deliverables.

---

## Locked Decisions (User Resolutions)

| # | Topic | Resolution |
|---|---|---|
| D1 | mrocklin upstream as destination | **Out of scope.** Path 3 dead. |
| D2 | Sync direction in Path 2 | **Selective pull from abast** (not push, not upstream). |
| D3 | abast integration mechanism | **Selective pull only**, never all-or-nothing. Applies to both paths. |
| D4 | `~/.claude/.claudechic.yaml` status | **Mixed under #23.** Claudechic config must move out of `~/.claude/`. |
| D5 | "Claude settings" definition | **Broad.** Anything in any `.claude/` directory is Claude's namespace; claudechic stays out entirely. |
| D6 | "Lost work" definition | **All four:** (a) commits never on main, (b) features non-functional post-merge, (c) features reverted in conflict resolution, (d) intent lost even if code survives. |
| D7 | Value asymmetry (sprustonlab vs abast) | **Equal.** Surface conflicts in the recommendation; user decides. |
| D8 | abast cooperation | **Available.** Team should plan to leverage it (de-risk cherry-picks, avoid duplicate work, recover intent on conflicts). |
| D9 | Time pressure on #23 | **None / irrelevant.** |
| D10 | Time estimates in deliverables | **Banned.** Describe what needs to happen in detail, not how long. |
| D11 | Issue #23 body vs userprompt boundary | **Distinct.** GitArchaeologist labels userprompt boundary as "derived scope" alongside the body's named scope. |
| D12 | GitArch branch selection | **Default branches only** (`sprustonlab/main` vs `abast/main`). |
| D13 | GitArch merge-base baseline | **Direct sprustonlab↔abast merge-base only** (no mrocklin axis). |
| D14 | GitArch theme granularity | **3-6 clusters per fork.** |
| D15 | GitArch per-file map volume | **Inline truncate at top-N=80 by churn**, full set in `fork_file_map.csv`. |
| D16 | Settings vs config terminology | **"Settings"** = user-facing umbrella term (the `/settings` TUI screen, "open settings", documentation prose). **"Config"** = technical term reserved for the YAML file format and the loader (`config.py`, `ProjectConfig`, `*.yaml`). |
| D17 | `.claudechic.yaml` location | **Option B — directory form.** Config lives at `.claudechic/config.yaml` inside a `.claudechic/` directory in the launched repo's root. Strict D5 compliance; aligns with Composability's BF7 worktree-symlink design. |
| D18 | `analytics.id` scope | **Per-project.** No global analytics identity. Each repo gets its own `analytics.id` in `<launched_repo>/.claudechic/config.yaml`. (User's local analytics is `enabled: false` regardless.) |
| ~~D19~~ | ~~Directory layout: sprustonlab's split~~ | **REVERSED 2026-04-25 by user after reviewing concrete diffs.** See D19'. |
| **D19'** | Directory layout (revised) | **Adopt abast's `defaults/` layout.** Move sprustonlab's `claudechic/workflow_engine/` back into `claudechic/workflows/` (engine + data); move sprustonlab's bundled YAML data from `claudechic/workflows/` and `claudechic/global/` into `claudechic/defaults/workflows/` and `claudechic/defaults/global/`. Sprustonlab restructures FIRST (before any abast pull) so the mirror-tree collapses at the layout layer rather than at cherry-pick time. Trade-off accepted: lose the `workflow_engine/` separation introduced in `317f424`. |
| D21 | Path order (revised) | **Layout convergence FIRST, then pull from abast, then implement #23.** A variant of Path 1 with a structural pre-step that dissolves the mirror-tree collision risk before any cherry-pick. Skeptic's PC1.5 (mirror-tree pre-decision) is satisfied by D19' rather than deferred. |
| D22 | `.claude/rules/` ownership | **Claudechic does NOT write to `<launched_repo>/.claude/rules/`.** That directory is the repo owner's responsibility. Claudechic's own context docs relocate to `<launched_repo>/.claudechic/rules/` (claudechic's namespace, claudechic-managed). Claude continues to access the docs via a `PreToolUse` hook redirect: when Claude reads a path under `.claude/rules/` matching a claudechic context-doc filename, the hook rewrites the read to `.claudechic/rules/<filename>`. Other reads of `.claude/rules/` (third-party rule docs the repo owner installs themselves) pass through unchanged. The hook mechanism depends on Claude's `.claude/rules/` discovery being hookable; Implementer must verify this in SPEC.md C.1.1 before completing the redirect (escalate to Coordinator with mechanism re-spec if not hookable). The `/onboarding` workflow's `context_docs` install phase **stays** but installs into `.claudechic/rules/`; `ContextDocsDrift` trigger and `context_docs_outdated` hint **stay** but check the new location. |
| D20 | `/fast` from abast | **Skip for now.** Decision deferred pending discussion with abast. Captured in [sprustonlab/claudechic#25](https://github.com/sprustonlab/claudechic/issues/25). |

---

## Baseline Findings (path-independent)

These are facts about the present state of the codebase that hold regardless of which path is chosen.

- **BF1** *(TerminologyGuardian, expanded during Spec pre-work)* — claudechic currently writes to **four** paths inside Claude's namespace, all of which **violate** D5 (`.claude/` is off-limits to claudechic):
  1. `~/.claude/.claudechic.yaml` (config; `config.py:17`)
  2. `.claude/hints_state.json` (hints state)
  3. `.claude/phase_context.md` (workflow engine; `app.py:1623+`)
  4. `.claude/rules/<claudechic-doc>.md` (synced by `/onboarding`; `global/hints.yaml:94`)
  All four must be relocated to `<launched_repo>/.claudechic/`. Per D22, the relocation target for the fourth is `<launched_repo>/.claudechic/rules/`, and claudechic does **not** write to `<launched_repo>/.claude/rules/` thereafter — Claude is given access to the docs at the new location via a hook-based read redirect (per SPEC.md C.1.1). The user-facing prose docs that hard-code `~/.claude/.claudechic.yaml` (CLAUDE.md:318, theme.py:3,87, errors.py:77, context/CLAUDE.md:79, docs/privacy.md:36, config.py:17) are part of the migration surface.
- **BF2** *(Skeptic)* — Issue #23 redesigns config layout; lab forks customarily customize config first; abast has therefore most likely already touched the same files #23 will rewrite. Path 2 sequencing brings these into collision at the worst point.
- **BF3** *(Skeptic)* — Silent semantic conflicts are textually invisible: a clean `git merge` can produce a settings system nobody designed. Both paths must include explicit semantic-review checkpoints.
- **BF4** *(Skeptic, post-D3)* — Selective pull introduces a new sub-risk: dependency-drop (pull commit B without prerequisite A → clean code that runs broken).
- **BF5** *(Skeptic, post-D3)* — What we deliberately *don't* pull from abast is itself a divergence surface; the recommendation must handle "deliberate non-pulls" explicitly.
- **BF6** *(GitArchaeologist)* — Issue #23 body is primarily about a `/settings` TUI screen + `docs/configuration.md`. The "boundary" concern from userprompt is a *derived/parallel* concern, not in the issue body verbatim.
- **BF7** *(TerminologyGuardian, Spec pre-work)* — `features/worktree/git.py:293-301` symlinks `.claude/` from the main worktree into each new worktree explicitly so "hooks, skills, and local settings carry over." Any #23 implementation must add a parallel `.claudechic/` symlink or the worktree feature silently regresses. Path-independent — both paths must address.

---

## Cross-Lens Conclusions (D7 — surface in synthesis, do not paper over)

| Lens | Lens-level conclusion | Decisive argument |
|---|---|---|
| **Skeptic (risk)** | **Path 1** (post-FDR, reaffirmed and strengthened) | Boundary-as-filter (Composability's argument) addresses settings-territory cherry-picks (small surface, real benefit) but does NOT address the H2 mirror-tree axis (~85 path-mirror pairs, large surface, no settings semantics for the contract to filter against). R8 (H2 mirror-tree semantic-layout collision) added with VH/Critical impact under Path 2. Standing rule: "a path with preconditions skipped is more dangerous than the other path with preconditions met." Reversal triggers: E4 reveals imminent abast `/settings` redesign; revised E2 reveals abast won't converge; D8 unavailable in practice. |
| **Composability (architecture)** | **Path 2** (post-FDR, strengthened) | abast's `claudechic/defaults/workflows/` overlay is itself a defaults-vs-overrides settings decision; pulling it before #23 lets it *implicitly co-decide* #23's design surface. `app.py` concentration check resolved tangential — Path 1's textual-collision argument dissolved. |
| **TerminologyGuardian (naming)** | **Path 2** (post-FDR, D16/D17 absorbed) | Path 1's premise ("import abast's alignment work") is empirically empty — abast added 7 new contested terms and re-scoped 3 more *without* remediating BF1. Path 2 step 1 produces tree with one canonical vocabulary; Path 1 step 1 produces tree with three contested namespaces co-resident. **D17 side-effect surfaced:** `analytics.id` becomes per-project under D17 (collapse of global tier); flagged for UA review. |
| **UserAlignment (audit)** | **Path 1 (marginal)** | The user's explicit stated failure mode ("lost work") maps directly onto Skeptic's D6.d matrix. Path 1's preconditions are sprustonlab-internal; Path 2's preconditions add external dependencies (abast design-time signoff, regression infrastructure). Path 1's forced-visibility advantage maps to the success criterion "user has confidence to start the chosen path in a separate session." Counter-weights honored: TG's vocabulary-unity argument has D6.d substance; Composability's filter advantage covers ~13-15-file truly-independent footprint effectively; FDR §7d quiet-zone favors Path 2 mildly. |

**Synthesis directive (for self):** the recommendation document must show both reasonings verbatim per C9, name the conflict per C17, and resolve it with explicit confidence per C32. The user retains the right to override per D7.

---

## Open Questions for User

- ~~**UQ3**~~ — RESOLVED as D19 (sprustonlab's split).
- ~~**UQ4**~~ — RESOLVED as D20 (skip `/fast` for now; deferred to sprustonlab/claudechic#25).
- ~~**UQ5**~~ — RESOLVED as D18 (per-project).

---

## Team Status

| Agent | Role | Status |
|---|---|---|
| Composability | Leadership — architecture & module coupling | Spec pre-work; absorbed BF1 expansion + BF7 |
| TerminologyGuardian | Leadership — naming & boundary terms | Spec pre-work complete (§1, §2a, §3); idle on GitArch |
| Skeptic | Leadership — risk, failure modes, merge hazards | Spec kickoff received; pre-work in progress |
| UserAlignment | Leadership — alignment with user intent | Spec pre-work complete (§1, §3, §5: C1-C33 rubric); idle on Leadership outputs |
| GitArchaeologist | Supporting — fork diff data substrate | Spec kickoff received; data substrate first in line |

---

## Phase Log

- **2026-04-25** — Vision phase: drafted, approved by user.
- **2026-04-25** — Setup phase: working_dir confirmed, no prior state, git OK, state dir created.
- **2026-04-25** — Leadership phase: 4 Leadership agents + GitArchaeologist spawned; orientation replies received from all 5; user resolutions captured (D1-D15); 6 baseline findings (BF1-BF6) promoted.
- **2026-04-25** — Specification phase: kickoff broadcast complete to all 5 agents.
- **2026-04-25** — Spec pre-work: TerminologyGuardian completed independent sections; expanded BF1 (4 paths, not 2) and surfaced BF7 (worktree symlink coupling); UQ1+UQ2 queued for next user batch. UserAlignment completed §1/§3/§5 with C1-C33 acceptance rubric.
- **2026-04-25** — User reviewed concrete diffs and revised D19: adopting abast's `defaults/` layout instead of sprustonlab's split. New D21 path: layout convergence → abast pull → #23. plan.md + abast_executive_summary.md authored.
- **2026-04-25** — Phase 1 (pre-flight with abast) **complete**. abast answers: (1) OK with adopting `defaults/` layout, will pause `defaults/` work; (2) nothing imminent on `/settings`, `.claude/` boundary, or config layout; (3) leave `/fast` out for now (other commits stable); (4) no special dependencies/ordering beyond what we already noted. **All reversal triggers cleared. Phase 2 (restructure) unblocked.**
- **2026-04-25** — User feedback: plan.md was conflating "spec" with "plan." Refactored into SPEC.md (operational only, for Implementer/Tester) + Appendix.md (rationale, rejected paths, decision history). plan.md deleted. Rubric-gap feedback sent to UserAlignment (proposed C34/C35 for future grading: "spec is operational only" / "documents are typed by audience").
- **2026-04-25** — User confirmed `.claude/rules/` scope (D22): claudechic stops *writing* to `.claude/rules/`, but the context docs **do** relocate to `<launched_repo>/.claudechic/rules/` (claudechic-managed); Claude accesses them via a `PreToolUse` hook redirect. The `/onboarding` install phase, `ContextDocsDrift` trigger, and `context_docs_outdated` hint all **stay** with their target paths updated. BF1 stays at 4 violations (Coordinator initially mis-applied as 3 — corrected). SPEC.md C.1 restored to 4 relocations; new sub-sections C.1.1 (hook redirect mechanism with hookable-Read verification step), C.1.2 (`/onboarding` install-target update), C.1.3 (drift-detection / hint update). Appendix.md updated with the (b)-not-(c) framing and hook-mechanism rationale.
- **2026-04-25** — Pre-FDR: Skeptic delivered Path 1 lean; Composability delivered Path 2 lean. Cross-lens conflict surfaced for synthesis (D7).
- **2026-04-25** — GitArch FDR FINAL. Headline findings: all 3 of #23's most-live code-touch sites are hot files; dominant Path 2 hazard is ~85 path-mirror pairs (not 6 textual hot files); `workflows/` referent split between forks; concrete BF4 instance (`anthropic==0.79.0` pin → `/fast` dependency). Finalize broadcasts sent to TG/Composability/Skeptic/UA.
