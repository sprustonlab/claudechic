# STATUS -- project_team_context_review

## Vision (approved v4)

**Goal.** Tighten the `project_team` workflow by reviewing the time, place, and role of context delivery to its agents, so the team has what it needs to drive the project forward at every step.

**Value.** `project_team` runs depend on agents acting with a shared understanding of their role, their teammates, the active phase, and the bounds of their authority. Context is what builds that understanding. Reviewing when context arrives, where it arrives, and which role receives it lets us shape the workflow around how the team actually moves a project forward. Grounding the review in observed behavior -- including failure modes from the most recent run -- keeps the work tied to real team dynamics. The concerns raised in issues #27 and #28 are addressed as part of this review.

**Domain Terms.**
- **Time** -- The lifecycle moment when context is delivered to an agent (spawn, activation, phase advance, broadcast, post-compact).
- **Place** -- The prompt segment carrying the context (identity, environment, constraints, phase).
- **Role** -- The `project_team` agent receiving the context.
- **Failure mode** -- An observed pattern from a past `project_team` run where missing, late, redundant, or misplaced context degraded team dynamics.
- **Bundled prompt content** -- The identity and phase markdown shipped under `claudechic/defaults/workflows/project_team/`.

**Success Looks Like.**
- The `project_team` workflow has a reviewed, intentional design for what context each role receives, when, and from where.
- Recent `project_team` session behavior is examined for failure modes traceable to context delivery, and those findings shape the changes.
- Team agents participate in reviewing the content directed at their own role.
- Issues #27 and #28 are resolved as part of this review.
- Other bundled workflows continue to work.

**Failure Looks Like.**
- The review produces engine knobs while the bundled `project_team` prompts stay as they are.
- Failure modes from past runs are cited but not connected to specific changes.
- Authority and role definition currently in identity files weaken during the review.
- Changes intended for `project_team` destabilize other workflows.

## Source GitHub Issues

- **#27** -- Allow workflow phases to suppress identity.md injection for standing-by agents.
- **#28** -- Make injected `## Constraints` block configurable via settings.

## Working Environment

- **Working dir:** `/groups/spruston/home/moharb/claudechic`
- **Branch:** `develop`
- **Git status:** clean working tree (only untracked: `.ai-docs/fork-divergence-2026-04-29.md`, `.claudechic/`)
- **Artifact dir:** `/groups/spruston/home/moharb/claudechic/.project_team/project_team_context_review`
- **Prior session for failure-mode analysis:** `/groups/spruston/home/moharb/claudechic/.project_team/abast_accf332_sync` (has STATUS.md, leadership_findings, spec docs, testing notes)

## Current Phase

- **Specification** -- complete; awaiting user checkpoint approval to advance to Implementation.

## Phase Log

- **Vision** -- approved v4 by user.
- **Setup** -- artifact dir bound, STATUS + userprompt written, git verified, prior session located.
- **Leadership** -- 4 leads spawned (composability, terminology, skeptic, user_alignment). All replied. Synthesis at `leadership_findings.md`. Initially confirmed 5-axis decomposition (time/place/role/gating/source); compositional law `inject(time, place, role) -> bytes-or-empty`; failure-mode map drafted from `abast_accf332_sync` (F1-F9); 8 hard questions raised for the Spec user checkpoint.
- **Specification** -- 4 axis-agents spawned (time_axis, place_axis, role_axis, gating_axis). All delivered. Terminology challenge collapsed source-as-axis and gating-as-axis; crystal reduced to time x place x role. Compositional law refined to `inject(t, p, r) = render(p, ctx(t, r)) if gate(t, p, r) else EMPTY`. Skeptic + user_alignment co-authored `failure_mode_map.md`. SPEC.md and SPEC_APPENDIX.md synthesized. Three open user decisions (D1: env segment v1 status; D2: review-and-suggest mechanism; D3: tutorial co-opt-in). Ten locked decisions (L1-L10).
