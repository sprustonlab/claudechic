# Leadership Phase Findings -- project_team_context_review

Synthesis of replies from composability, terminology, skeptic, user_alignment.

## Headline

The team converges on the user's `time x place x role` frame and treats issues #27 and #28 as the visible tip of a deeper structural question: today, every (time, place, role) cell of the prompt-assembly matrix fires unconditionally, and the engine has no expressive control surface for gating. The work the user described -- reviewing time, place, and role of context delivery to drive `project_team` forward -- is real architectural work, not a config patch.

## Confirmed axes (Composability)

Five axes, refining the user's three:

1. **Time** -- spawn, activation, phase-advance (main), phase-advance broadcast, post-compact.
2. **Place** -- identity, phase, constraints, environment.
3. **Role** -- 15 project_team role folders + `default`.
4. **Gating** -- always / per-phase suppress (#27) / per-setting toggle (#28) / runtime standing-by detect.
5. **Source** -- bundled markdown / manifest YAML / computed digest / runtime substitution.

**Compositional law:** `inject(time, place, role) -> bytes-or-empty`, gated by a pure predicate over `(time, place, role, phase, settings)`. If the law holds, all 5 x 4 x 15 cells compose by construction.

## Canonical glossary (Terminology)

Canonical names to use across Specification:
- **injection site** (Time)
- **prompt segment** (Place) -- with named values: `identity segment`, `phase segment`, `constraints segment`, `environment segment`
- **role** in prose; `agent_type` as the field name
- **scoping** -- the filter on `(role, phase, workflow)`
- **standing-by agent** -- *a spawned agent whose role has no `<role>/<phase>.md` for the current phase* (proposed; needs user/skeptic confirmation)
- **bundled prompt content** -- everything under `claudechic/defaults/workflows/project_team/`

Naming collapses required: "D5 inject site / inject site / prompt-injection site" -> **injection site**; multiple names for "phase prompt" -> **phase segment**; etc.

Open call: do we promote **environment segment** to a first-class peer segment now? Recommended yes -- makes #28 cleaner.

## Failure modes from `abast_accf332_sync` (Skeptic)

Cited from prior-run artifacts. Map to the time/place/role frame.

**Time:**
- F1. Phase-advance broadcast didn't route through `assemble_agent_prompt` -- sub-agents missed their `## Constraints` block. A delivery moment was simply absent from the inject site list.
- F2. Late framing reveal: UserAlignment's reframe arrived after axis-agents had produced verdicts on the wrong frame. No mechanism for "framing has shifted."
- F3. Three coexisting freshness contracts: spawn-time freezes, MCP-call reflects per-call, post-compact refreshes. Agent has no consistent answer to "is what I'm reading current?"

**Place:**
- F4. Source-of-truth divergence: hooks read raw `loader.load()`; registry/MCP read filtered `_load_result`. Same context, two answers.
- F5. `mcp.py` disabled_rules unwired at 4 sites -- project disable list never reached the constraints projection.
- F6. `get_phase` overstated active rules (namespace filter only, not role/phase). Agent's self-query lied about its scope.

**Role:**
- F7. Falsy check on `agent.agent_type` -- broadcast routed to default-roled agents incorrectly.
- F8. `assemble_agent_prompt` returns `None` for default-roled agents with no role dir. SPEC says "every agent"; impl skips. **Direct precursor to #27.**
- F9. Empty-digest emits 138-char placeholder -- standing-by agents get noise in every prompt. **Direct precursor to #27.**

## Risks (Skeptic)

- R1. "Standing-by" is not a distinct state today. An agent can be standing-by AND a broadcast recipient simultaneously -- naive suppression re-creates F1.
- R2. The constraints block is the hard-won fix for F4/F5/F7. Issue #28 must be scoped: format-tweak yes, opt-out no. Opt-out silently restores prior failures.
- R3. Identity files contain load-bearing authority statements (e.g. coordinator's "If user sends 'x'", skeptic's "You CANNOT cut features"). NOT boilerplate. Refactor without losing them.
- R4. The 3-freshness-contract substrate is inconsistent-but-functioning; "clean" rewrite is a regression vector.
- R5. Other bundled workflows (tutorial, learner) rely on sparser identity content -- changes for project_team must not starve them.

## User-protected priorities (UserAlignment)

The user explicitly asked for and we MUST preserve:
1. Issues #27 and #28 land.
2. Spawn-time claudechic-environment knowledge for agents -- **scope question still open: regardless-of-workflow vs project_team-only**.
3. **Agents review and suggest the content of injections at all phases** -- the team co-owns its own context. Mechanism still undefined.
4. Tighten project_team via time/place/role review.
5. Use `abast_accf332_sync` as the failure-mode source.

Explicitly declined: token thrift, contrast-based framing.

Drift watch-list:
- Treating #27/#28 as the deliverable, burying the broader review.
- Engine knobs without touching bundled prompt content.
- Quietly re-narrowing "regardless of workflow" to project_team only.
- Removing identity authority on complexity grounds.
- Failure modes cited decoratively without driving changes.

## Hard questions for the user before Spec lock

Aggregated from skeptic + user_alignment. These will be brought to the Spec checkpoint:

**Scope:**
- Q1. Is "claudechic-environment at spawn" global (all workflows) or project_team-only?
- Q2. What does "agents review and suggest the content of injections at all phases" look like concretely? Mechanism for proposing edits to identity.md / phase markdown -- to whom, when, how decided?

**Semantics:**
- Q3. When a standing-by agent receives a phase-advance broadcast, does identity suppression apply? (If yes -> F1 risk. If no -> "standing-by" and "broadcast recipient" are distinct tracked states.)
- Q4. Issue #28 scope: opt-out, format-only, or scope-only? Opt-out reintroduces F4/F5/F7 silently.
- Q5. Default-roled agents (no role dir) -- do they receive constraints injection? SPEC §D says yes, impl says no, prior run left this unresolved.
- Q6. Freshness contract: pick one of {spawn-time freeze, per-call live, post-compact refresh} as canonical, or keep three? Behavior change either way.

**Process:**
- Q7. Should `coordinator/identity.md`'s phase-list be deduplicated against the engine, or kept as informational?
- Q8. Identity content de-duplication in scope, or only the injection mechanism?

## Recommended axis-agents for Specification

Per composability:

1. **time-axis** -- audit the 5 injection sites against `abast_accf332_sync` failure modes; lock post-compact as a full refresh; resolve F1 risk for broadcast.
2. **place-axis** -- split identity-vs-phase assembly so each segment is independently gateable; specify the constraints-block on/off seam (#28); decide on environment-segment promotion.
3. **role-axis** -- per-role audit of identity.md + phase.md across project_team's 15 roles; surface redundancies and gaps; **engage role agents directly** to satisfy the user's "agents review and suggest" requirement.
4. **gating-axis** -- design the configuration surface (phase YAML for #27, settings.yaml for #28); pin standing-by semantics (recommend: static for v1); specify the `inject(time, place, role)` predicate.

Composability also recommends a coordination loop between role-axis and gating-axis on overloaded terms ("context", "standing-by", "identity injection") with TerminologyGuardian.

## Proposed deliverables for Specification phase

- `GLOSSARY.md` (TerminologyGuardian, day 1).
- `SPEC.md` -- master spec covering the inject predicate, segment boundaries, gating surface, environment-segment decision.
- `spec_time_axis.md`, `spec_place_axis.md`, `spec_role_axis.md`, `spec_gating_axis.md`.
- `failure_mode_map.md` -- mapping of `abast_accf332_sync` F-numbers to specific proposed changes (skeptic + user_alignment co-own; user_alignment's drift watch-list says this map MUST exist).
- `prompt_audit/<role>.md` -- per-role review documents authored with the role agents themselves (satisfies user requirement #3).

## Status

Leadership phase complete. Ready to advance to Specification.
