# SPEC_APPENDIX -- project_team_context_review

Non-operational content separated out of `SPEC.md` per phase guidance.

---

## A. Why three axes, not five

The Leadership phase opened with a 5-axis frame (time, place, role, gating, source). TerminologyGuardian challenged this in the Specification phase:

- **Source is not an axis.** Each segment has exactly one source. Two segments never share a source. Source is a per-segment attribute, not a coordinate the user picks at fixed (time, place, role).
- **Gating is not an axis.** The (time, place, role) cell IS the coordinate. Gating is the predicate machinery that decides whether the cell fires. Gating gets its own spec doc (the control surface) but is not a coordinate.

Composability accepted both points. The crystal collapses to time × place × role. Cell count: 5 × 3 × 15 = 225 (Tier-2 environment) or 5 × 4 × 15 = 300 (first-class environment).

## B. Why the compositional law lives in a single function

Skeptic challenged composability's initial sketch of a `claudechic/workflows/segments/` module with per-segment files. Composability accepted the pushback:

- A new module implies an axis worth physically isolating. v1 has 3 segments inside one composition point. The seam is logical (per-segment renderers as separate functions), not physical.
- Existing 5 inject-site callers see no API change.
- R-comp-7 (preserve inline `${VAR}` substitution for all 9 bundled workflows) is easier to verify in one file.
- If environment promotion lands in v2, that is when a `segments/` module earns its place.

## C. Why issue #28 is format-only, not opt-out

The constraints segment is the v0 fix for failure modes F4 (source-of-truth divergence), F5 (`mcp.py` disabled_rules unwired), and F7 (broadcast routed to default-roled agents). Allowing `enabled: false` would silently re-introduce these. Per-rule disable is already supported via `disabled_ids`; that is the right scope-level opt-out surface. The user-tier `constraints.format`, `constraints.include_skipped`, and `constraints.scope.sites` keys cover the legitimate configurability use cases without exposing the failure surface.

## D. Why standing-by is static, not runtime

R1 risk: an agent can be standing-by AND a broadcast recipient at the same call. A runtime "is standing by" check would either need a side-effecting state or break predicate purity. Static definition (the role has no `<role>/<phase>.md` for the current phase) is a pure file-system check, evaluable per call without memoization. The same predicate is correct under `/compact` restoration and mid-run manifest changes.

## E. Why F2 is out of v1

F2 (late framing reveal) is a workflow-coordination failure, not a (time, place, role) cell. Gating it would require runtime state encoding "framing dirty." That breaks predicate purity (L2). Recorded as out-of-v1 in `failure_mode_map.md`. v2 path: a static gating signal that encodes "framing dirty" without runtime state, e.g. a manifest flag re-evaluated per phase advance.

## F. Why F3 is accepted-risk

F3 (three coexisting freshness contracts: spawn-time freezes, MCP-call reflects per-call, post-compact refreshes) is not closed by the v1 work. Mitigation: T5 (post-compact) is canonical full-refresh. Residual risk: chicsession-resume can replay a stale launch prompt. v2 follow-up: promote chicsession-resume to a tracked injection site under post-compact invariants.

## G. Why content moves preserve authority

Content move A (communication boilerplate to shared source) is delivery boilerplate, not authority. The 14 affected identity files lose ~10 lines of `message_agent` examples each; the same content lives once in the shared source and is referenced. No authority quote is among the moved content (verified against the 22-item authority preservation list in `spec_role_axis.md` §2).

Content move B (pytest-policy prose to constraints reference) replaces narrative duplication of the `global:no_bare_pytest` rule with a one-line reference. The rule itself is unchanged.

## H. Rejected alternatives

- **`segments/` module** (rejected: premature, no API change benefit, R-comp-7 friction).
- **Runtime standing-by detection** (rejected: breaks predicate purity, no v1 caller needs runtime state).
- **`enabled: false` opt-out for constraints** (rejected: silently re-introduces F4/F5/F7).
- **15 separate `prompt_audit/<role>.md` files vs 1 file with 15 sections** (deferred / inconsistent: role_axis delivered the 16-file form despite the recommendation; both forms work; SPEC.md treats either as acceptable).
- **Recurring per-phase `propose_prompt_edit` MCP tool** (rejected for v1: scope creep; deferred to v2 as D2=c).
- **Promoting chicsession-resume to v1 injection site** (rejected: F3 mitigation only, not closure; recorded as v2 path in `failure_mode_map.md`).
- **Spawn-condition (`spawns_when:`) manifest field** (deferred to v2: useful but orthogonal to the time/place/role review).

## I. Historical context

The work originated as GitHub issues #27 (suppress identity injection for standing-by agents) and #28 (configurable constraints block). The user expanded scope twice: first to include a workflow-agnostic environment segment at spawn; then to a tighter framing of "review the time, place, and role of context delivery to drive the project_team forward, with failure modes from the prior session as evidence." The two issues remain in the deliverable as L4 and L3 / D1.

The prior session referenced is `abast_accf332_sync` -- the run that originally surfaced #27 and #28 and produced the F1-F9 catalog (see `failure_mode_map.md`).

## J. Drift watch-list (UserAlignment, active for Implementation phase)

- Engine-knobs deliverable without bundled-content revisions.
- Quietly re-narrowing "regardless of workflow" to project_team-only without explicit user decision.
- Removing identity authority on complexity grounds (L8 protects this).
- Failure modes cited without driving changes (`failure_mode_map.md` ties each to a fate).
- "Team dynamics" disappearing from success criteria (named in §1 of SPEC.md).
- Token-thrift framing reappearing as primary justification.
- Contrast / "do not" / "stop X" framing reappearing in user-facing prose.

## K. Term-drift cleanups deferred to Implementation

TerminologyGuardian's drift sweep flagged mechanical synonym-collapses across `spec_*` files (e.g. "phase prompt" → "phase segment", "inject site" → "injection site"). These are non-architectural rewrites. Implementation will absorb them when bundled prompt content is revised.

The duplicate `specification/place_axis.md` vs root `spec_place_axis.md` will be reconciled by deleting the specification/ copy or replacing its body with a pointer.
