# Skeptic Review -- project_team_context_review (Specification phase)

**Author:** Skeptic
**Date:** 2026-05-01
**Phase:** project-team:specification
**Reviews:** `leadership_findings.md` (composability/terminology/skeptic/user_alignment synthesis), the user's vision (v4), and the prior-run failure modes F1-F9.

This review is the bar a Specification draft must clear, not the spec itself. It names the assumptions to challenge, the risks of the proposed direction, the essential-vs-accidental complexity calls, and the shortcuts I will reject in design. I write it now so axis-agents can absorb it before producing per-axis specs.

---

## TL;DR -- skeptic posture for specification

The leadership synthesis is strong on **diagnosis** (the 9 failure modes from `abast_accf332_sync` are correctly classified by time/place/role) and reasonable on **scope** (issues #27/#28 are correctly demoted to "tip of structural problem"). My posture is:

1. **The compositional law `inject(time, place, role) -> bytes-or-empty` is an attractive abstraction. Verify it before locking it.** A 5x4x15 = 300-cell matrix where most cells are nonsense buys nothing; a 4-segment x 5-site x 1-predicate model where the predicate reads from data we already have buys clarity.
2. **Four axis-agents is one too many.** Gating is cross-cutting, not an axis. Time and Place are entangled at the inject-helper. Recommend three axes + a gating-as-deliverable shared between them.
3. **The "agents review and suggest content" requirement (UserAlignment user-protected #3) is the largest scope risk.** Without a sharp mechanism, this becomes a meta-workflow expansion that swallows the run.
4. **"Promote environment-segment to a first-class peer" adds a 5th place where F-numbers show no failure.** Burden of proof is on whoever proposes it; I default to skip until #28's exact requirement names environment as the configurable target.
5. **Source-of-truth divergence (F4) is not represented in the 4 axes.** The `_LoaderAdapter` shim and the `_filter_load_result` projection ARE the load-bearing fix from the prior run. Any axis spec that touches reading rules/checks must declare it preserves that single source.

---

## Q1-Q6 falsification questions, applied to the leadership plan

| Q | Falsification target in this run | Verdict |
|---|---|---|
| Q1. Does this fully solve what the user asked for? | User asked: "tighten project_team by reviewing time/place/role of context delivery, ground in failure modes." Leadership plan covers all three axes + adds gating + adds source. **Risk: F2 (late framing reveal) is not directly addressed by any axis** -- it is a workflow-coordination problem, not a context-delivery problem. Either add a deliverable for workflow-level reframe handling or scope-cut F2 explicitly. | **PARTIAL** -- F2 needs a home or an explicit out-of-scope ruling. |
| Q2. Is this complete? | All 9 F-numbers must map to either (a) a proposed change or (b) an explicit non-coverage. `failure_mode_map.md` is in the deliverables list -- good -- but it must be MANDATORY before lock, not optional. F4-F6 (place / source-of-truth) sit awkwardly across the gating + place axes; declare which axis owns them. | **AT RISK** -- mandate failure_mode_map.md exists with a row per F-number. |
| Q3. Is complexity obscuring correctness? | The `inject(time, place, role)` predicate is one abstraction over five existing inject sites. If the predicate is implemented as a 30-line pure function reading bundled config + phase YAML, simpler. If it's implemented as a class hierarchy or a multi-pass engine, accidental complexity. **Demand: the predicate ships as a single pure function in `claudechic/workflows/agent_folders.py` next to `assemble_agent_prompt`, not as a new module/package.** | **WATCH** -- pin shape now to head off engineering drift. |
| Q4. Is simplicity masking incompleteness? | Composability proposes "static standing-by semantics for v1" (Q3 in leadership). Static is simpler. Risk: an agent that becomes standing-by mid-phase (e.g., its phase.md was deleted by a workflow override at runtime) would fall through. Decide whether the v1 static check is "checked at spawn" or "checked at every inject site." If only at spawn, a /compact restoration that re-reads the phase will re-fire the check anyway -- so per-site is not much costlier and is more correct. | **PUSH FOR PER-SITE STATIC CHECK** -- still pure, no extra moving parts, more complete. |
| Q5. Does a simpler in-tree change deliver 80% at 20% of the cost? | For #27 alone: a `suppress_identity: [phase_ids]` field in the workflow YAML manifest, read by `_assemble_agent_prompt`. That's ~5 lines of code and 1 line of YAML per phase. For #28 alone: a `constraints_format` enum in user-tier `~/.claudechic/config.yaml` read by `assemble_constraints_block`. Another ~5 lines. **Combined #27+#28 minimal patch: ~15 LOC.** The leadership plan's broader scope (environment segment promotion, role-axis 15-file audit, prompt_audit per role, etc.) is the user's expanded ask -- but the spec MUST answer "what is the minimum that closes #27 and #28" separately so the user can choose minimum vs. expanded. | **DEMAND a "minimum-viable #27+#28" section in SPEC.md, separate from the broader review.** |
| Q6. Does this regress a property we currently rely on? | The prior run shipped four parallel D-layers (hook / `get_applicable_rules` / `get_agent_info` / injected constraints block) bound to the same source via `_LoaderAdapter`. Any change that re-introduces a second source-of-truth path silently restores F4. **Demand: any axis spec that touches rule/check reading must explicitly cite the keystone test from `abast_accf332_sync/testing/skeptic.md` as a non-regression boundary.** | **HARD STOP** -- spec must name the keystone test as binding. |

---

## Essential vs accidental complexity calls

### Essential (must ship)

- **Per-(time, place, role) gating** of injection. The user explicitly named #27 (per-phase suppression of identity) and #28 (per-setting constraints config). Gating IS the requirement, not an avoidance.
- **Failure-mode-grounded changes.** F1, F8, F9 directly motivate #27. F4, F5, F6 motivate the source-of-truth invariant. These must drive specific code changes, not decoration.
- **Single source-of-truth for rules + checks** across the four parallel D-layers. The prior run paid for this; do not unbuild it.
- **Identity authority preservation.** Coordinator's "If user sends 'x'", Skeptic's "You CANNOT cut features" etc. are NOT delivery boilerplate; they are the agent's user-contract. Any refactor touching identity.md MUST pass an authority-preservation check (see "Authority preservation contract" below).

### Accidental (push back)

- **A new module / package / engine for "the inject predicate."** Not needed. A pure function next to `assemble_agent_prompt` is sufficient.
- **Promoting environment-segment to a first-class peer for #28.** No prior-run F-number names environment as a failure. If #28 ends up requiring a `## Environment` block, that decision should fall out of #28's resolution, not be pre-locked in glossary.
- **15 prompt_audit/`<role>`.md files**, one per project_team role. Sensible to involve role agents; over-engineering to mandate 15 separate documents. **Counter-proposal: ONE prompt_audit.md with a section per role, owned by role-axis with role agents reviewing their own section.** Same coverage, one fewer artifact dimension to keep coherent.
- **A meta-mechanism for "agents review and suggest content at all phases" (UserAlignment user-protected #3).** This is the largest scope-creep vector in the entire run. Make it concrete with one of:
  - (a) per-phase `prompt_review` step in the project_team workflow YAML where role agents emit comments on their own identity.md / phase.md before the phase advances; OR
  - (b) a one-shot review event scheduled during this run only.
  Recommend (b) for v1 -- the user can later promote to (a) if it pays off.

---

## Risks the spec must mitigate

| # | Risk | Mitigation the spec MUST encode |
|---|------|---------------------------------|
| R1 | "Standing-by" is not a tracked engine state. Naive suppression re-creates F1 (broadcast misses constraints). | Define standing-by as **"role has no `<phase>.md` for the current phase AT inject-call time"** (not "not currently the active agent"). Re-evaluate per-injection, not per-spawn. |
| R2 | Issue #28 opt-out silently re-introduces F4/F5/F7 by letting the user disable the constraints block. | #28 surface ships as **format-and-scope tweaks only, NOT an opt-out.** No "disable constraints" toggle. The spec must name this exclusion explicitly. |
| R3 | Identity authority statements lost in refactor. | Spec includes an **"authority preservation contract"**: every existing identity.md authority sentence (catalogued in `prompt_audit.md`) survives the refactor verbatim or with explicit redress. |
| R4 | Three coexisting freshness contracts (F3) silently change behavior on consolidation. | Spec picks one canonical contract per inject site type and **lists every site with its freshness verdict** (probably: spawn = freeze; phase-advance = refresh; broadcast = refresh; post-compact = refresh; MCP-call = live). |
| R5 | Tutorial / learner / other workflows starve under project_team-shaped changes. | Spec covers EVERY bundled workflow's identity.md sparseness pattern; gating defaults must produce identical behavior to today for non-project_team workflows. |
| R6 | Cross-layer divergence regression. | Spec cites the prior-run keystone test as binding; any new code path that reads rules/checks reads via `_LoaderAdapter` or its successor. |

---

## Shortcuts I will reject in axis specs

- **"We'll define standing-by during implementation."** Define it now or punt the feature.
- **"#28 is configurable via settings, details TBD."** Name the config key, the values, the consumer, the default. Otherwise it's a placeholder.
- **"Engine-only knobs, bundled prompts unchanged."** UserAlignment's drift watch-list calls this out -- it is the failure mode of the entire run if it happens. Spec must produce concrete diffs to identity.md / phase.md as part of the review.
- **"We'll handle F-numbers in implementation."** Each F-number maps to a spec change, an explicit out-of-scope, or a deferred follow-up (with rationale). No silent omissions.
- **"Add a new abstraction layer to make this clean."** If the proposal has more than 2 new moving parts (new module + new class + new enum + new YAML key), justify each in the spec or trim.
- **"Just do project_team-only for now."** UserAlignment user-protected #2 explicitly leaves "regardless of workflow vs project_team-only" open. Decide explicitly with the user; do not silently narrow.
- **"15 separate prompt_audit files."** One file with 15 role sections is strictly simpler to review and to keep in sync.

---

## Pre-existing-spec complexity audit (per phase instruction #6)

This is a fresh spec phase (no prior revision in *this* run yet), but the leadership plan has already accreted complexity beyond what the user asked for. The user asked: review time / place / role. Leadership added two axes: gating and source. **Both additions are justified** (gating IS issues #27/#28; source-of-truth IS the F4 fix). But the spec must not also accrete:

- A 6th axis ("freshness").
- A 7th axis ("authority").
- A meta-workflow for content review at every phase (push to one-shot for v1).

If any axis spec proposes a new dimension, the proposer must show which user-named requirement it satisfies.

---

## Concrete demands on axis specs

Each of `spec_time_axis.md`, `spec_place_axis.md`, `spec_role_axis.md`, `spec_gating_axis.md` must answer:

1. **One-sentence user-visible delta** with a concrete user who would notice the change. (Per Q4.)
2. **Failure-mode map**: which F-numbers from prior run does this axis own? Which are explicitly out of scope and why?
3. **Moving-parts inventory**: every new module / class / function / YAML key / settings key. >2 new moving parts requires a "why not 1?" paragraph.
4. **Authority-preservation check**: does this axis touch identity.md content? If yes, list every authority sentence affected.
5. **Source-of-truth declaration**: if the axis reads rules / checks, does it route through `_LoaderAdapter` or its successor? If not, why is divergence safe here?
6. **Standing-by semantics** (gating-axis only): one-sentence definition. The leadership terminology proposal ("role has no `<role>/<phase>.md` for the current phase") is a starting point, NOT a lock.
7. **Cross-axis dependencies**: which other axis must land first / together?

---

## Pass/fail bar for synthesis (SPEC.md)

The SPEC.md draft passes Skeptic review iff:

- [ ] A **"Minimum-viable #27 + #28"** section names the smallest patch that closes both issues. <30 LOC plus YAML/config.
- [ ] A **`failure_mode_map.md` table** maps every F-number (F1-F9) to: (a) a spec change, (b) explicit out-of-scope rationale, or (c) follow-up scope.
- [ ] A **freshness verdict per inject site** (5 sites x 1 verdict each).
- [ ] A **standing-by definition** that resolves R1.
- [ ] A **#28-is-not-an-opt-out** statement that resolves R2.
- [ ] An **authority-preservation contract** that resolves R3.
- [ ] A **source-of-truth invariant** referencing the keystone test that resolves R6.
- [ ] A **non-project_team-workflow no-regression statement** that resolves R5.
- [ ] An **answer to UserAlignment-protected #3** ("agents review and suggest content"): one-shot review for v1, recurring is a follow-up.
- [ ] An **answer to UserAlignment-protected #2** ("claudechic-environment at spawn"): explicit global vs project_team-only decision (asked of user at checkpoint, not silently picked).

A draft missing any item is incomplete, not "an early version." Send it back.

---

## What I will check at the user-checkpoint

1. Does the spec answer the user's three frame axes (time, place, role) with one-sentence user-visible deltas?
2. Does every failure-mode F-number have a fate?
3. Is the constraints-block opt-out absent (R2)?
4. Are identity authority sentences itemized (R3)?
5. Are the four parallel D-layers source-aligned (R6 / keystone)?
6. Is the broader review a meta-workflow (rejected) or a one-shot for v1 (accepted)?
7. Has any axis snuck in a 6th or 7th dimension?

---

## Closing posture

The user gave us a real architectural problem grounded in real prior-run failures. The leadership synthesis identified the right axes and the right risks. The spec phase must produce something that **closes #27 and #28 in their minimum form, addresses the prior-run failures concretely, and stays under one new abstraction**. If at user-checkpoint the SPEC.md introduces a new engine, a new module hierarchy, or a per-phase agent-review meta-loop, I will recommend redirect.
