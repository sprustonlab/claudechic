# User Prompt -- Testing scope -- abast_accf332_sync

## Original guidance from the user, gathered across the testing-vision phase

> "Phase 6-8: Testing (incl. remote-control smoke test for B3+B4)"

> "This is part of testing and E2E not now."
> -- on the question of when to run the remote-control smoke test for the
> mid-session role flip; user confirmed it belongs in the Testing phase,
> not in Implementation.

> "no tests have their own phase! ... don't DEFER anything that is in the
> approved spec."
> -- on the implementation phase prompt-shape; user clarified that
> implementation does not write/commit tests, and test work belongs to
> the Testing phase. Items the team identified as "needs a test" were
> deferred here.

> "the spec is not the product of the team, the feature is."
> -- testing must verify the *feature works*, not retrospectively
> document the spec. Test artifacts target runtime behavior.

> "Worry about the current phase, not carry forward to other phases
> where you don't have instructions yet."
> -- testing scope stays focused on testing; the user-facing report,
> per-component cherry-pick archaeology, and similar retrospective
> artifacts are out of testing scope.

## Approved testing vision (consolidated 2026-05-01)

The user approved `.project_team/abast_accf332_sync/testing/TESTING_VISION.md`
which defines:

- 6 functional gates (full pytest suite passes; mid-session role flip
  via remote-control; all 5 prompt-injection sites fire; new pytest
  warn rule fires correctly; modal info parity; zero new test
  regressions vs parent commit).
- 4 architectural gates (seam-protocol tests for the 6 axis pairs; 10
  representative crystal-point configurations; single-composition-point
  lint; cross-layer source-of-truth assertion -- the keystone test).
- 2 user-intent gates (each user-named feature has both a user-side
  and an agent-side gestalt assertion; reframing fidelity for
  guardrails UI).
- 3 terminology gates (test names locatable by SPEC component;
  required contract strings asserted verbatim; canonical 5-site
  inject vocabulary).

Plus a sign-off bar of 6 conditions for a passing testing-implementation
exit.

## Out of scope (user's framing)

- Performance benchmarking / load testing.
- Cross-platform CI runs (claudechic CI handles).
- New tests for code paths outside the abast/accf332 cluster scope.
- Retrospective process documentation.
- The user-facing R4-R7 report (the user explicitly said "R4-R7 are
  history; we implemented already; we don't need to answer them now").

## Decision authority

Same as implementation phase: the team produces a recommendation; the
user makes final yes/no per gate where ambiguity exists. The TESTING_VISION
gates are user-approved as binding for this run.

## Filed feature requests (out-of-batch)

- sprustonlab/claudechic#27: per-phase identity injection suppression
  for standing-by agents.
- sprustonlab/claudechic#28: configurable `## Constraints` block
  injection.

Neither is in scope for this batch's testing.
