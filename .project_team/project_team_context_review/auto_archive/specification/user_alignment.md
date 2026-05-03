# User Alignment -- Specification Phase

Source of truth: `userprompt.md` and the conversation arc captured in
`leadership_findings.md` Section "User-protected priorities".

This document locks the user's intent for Specification, flags wording
shifts that need explicit user sign-off, and gives the spec authors a
checklist to test their drafts against.

---

## 1. Original Request Summary (verbatim from the user arc)

The user opened with **"address issues #27 and #28"** and walked the team
through three expansions:

1. **"give agents claudechic-environment knowledge at spawn regardless of
   workflow."**
2. **"I want the agents to also review and suggest the content of
   injections at all phases."**
3. **"focus this on the project_team workflow ... give agents context in
   a way that enables good team dynamics in the project_team workflow
   and as a side benefit shifts some of the things mentioned here."**

Plus two style/process directives:

4. **"Don't frame things by what they are not"** -- affirmative voice.
5. **"include an analysis of common failure modes by using the last
   session as an example"** (`abast_accf332_sync`).

And one explicit decline:

6. **"I don't care about token use or chasing down statistics."**

---

## 2. Domain Terms -- user wording vs spec wording

The user's vocabulary and the team's working vocabulary have drifted in a
few places. Each row is a wording change that the user should explicitly
approve before Specification locks. None are forbidden -- they are just
flagged.

| User said | Spec is using | Status | Recommendation |
|-----------|---------------|--------|----------------|
| "context" | "injection site" / "prompt segment" | ? Wording change | Keep "context" as the user-facing term in SPEC headings, vision, and the role-agent reviews. The technical decomposition (`time x place x role`) can use `injection site` / `prompt segment` internally. |
| "context delivery" | "prompt assembly" | ? Wording change | Same -- prefer "context delivery" in user-facing sections. |
| "claudechic-environment knowledge" | "environment segment" | [OK] Acceptable | The `environment segment` name is a compatible refinement; preserve "claudechic-environment knowledge" as the description of *what it carries*. |
| "review and suggest the content of injections" | "per-role audit" / "prompt_audit/\<role\>.md" | ? Wording change | "Audit" connotes one-time inspection; the user asked for **review and suggest at all phases** -- this is ongoing co-ownership, not a phase-1 audit. Spec must name an ongoing mechanism, not just an artifact. |
| "team dynamics" | (not yet present in any draft) | [WARNING] Missing | Add "team dynamics" as a first-class success criterion in SPEC.md. The user named it as the **point** of the work. |
| "regardless of workflow" | "global vs project_team-only -- TBD" | ? Open question | This is Q1 in `leadership_findings.md`. The user said "regardless of workflow" plainly. Spec should default to global unless the user backs off. |
| "issues #27 and #28" | "issues #27 and #28" | [OK] Preserved | -- |

---

## 3. Domain-term meaning checks (gestalt, not features)

- **"Context"** -- the user means *what an agent knows when it starts to
  act*: identity, environment, the active phase, the constraints. They
  are NOT asking for a metrics/observability subsystem. The spec must
  not drift into a token-budget tool.
- **"Team dynamics"** -- implies multi-agent interaction quality:
  shared frame, well-timed handoffs, agents knowing who their teammates
  are and what authority each holds. The spec must measurably improve
  *between-agent coordination*, not just per-agent prompt content.
- **"Review and suggest"** -- implies the affected role has a voice in
  what gets injected for it. A coordinator-only edit pass does not
  satisfy this.

---

## 4. Alignment status of the proposed Specification direction

Based on `leadership_findings.md` and the four-axis decomposition.

| User-protected item | Coverage in proposed spec | Status |
|---------------------|---------------------------|--------|
| Address #27 | gating-axis (per-phase suppress predicate) | [OK] |
| Address #28 | gating-axis (settings toggle, format-only per Skeptic R2) | [OK] -- with R2 caveat |
| claudechic-environment at spawn | place-axis (environment segment promotion) | [WARNING] Scope of "regardless of workflow" still open |
| Agents review/suggest injections at all phases | role-axis (`prompt_audit/<role>.md` co-authored) | [WARNING] Mechanism undefined for "all phases" -- audit is one-shot |
| Tighten project_team via time/place/role | All four axis docs | [OK] |
| Use `abast_accf332_sync` as failure-mode source | `failure_mode_map.md` | [OK] |
| Don't frame by what they are not | (no spec drafts yet) | ? Watch during drafting |
| Decline token thrift | (not creeping so far) | [OK] |
| Team dynamics as the point | (not yet a named success criterion) | [WARNING] Add explicitly |

**Overall: NEEDS CLARIFICATION** -- ALIGNED on most points; two open
scope questions (Q1, Q2 from leadership_findings) and one missing
success criterion (team dynamics) must be resolved before Spec lock.

---

## 5. Hard alignment requirements for SPEC.md

These are non-negotiable in the spec drafts. They map directly to user
quotes and to the drift watch-list.

1. **SPEC.md MUST include "team dynamics" as a named success
   criterion.** Quote: *"give agents context in a way that enables good
   team dynamics in the project_team workflow."* Without it the spec
   drifts into engine plumbing.
2. **SPEC.md MUST specify a mechanism for agents to review and suggest
   the content of their own injections at all phases**, not only as a
   one-time per-role audit. Quote: *"I want the agents to also review
   and suggest the content of injections at all phases."* The audit
   document is the *artifact*; the *mechanism* (when, by whom, how
   adopted) must be named.
3. **SPEC.md MUST resolve Q1** -- "regardless of workflow" is the
   user's explicit framing. If the spec narrows it to project_team only,
   that narrowing requires explicit user approval and must be flagged in
   the user checkpoint.
4. **SPEC.md MUST connect every proposed change to a failure mode in
   `failure_mode_map.md`** OR to a user requirement quote. Untraced
   changes are drift candidates.
5. **SPEC.md MUST use affirmative framing** in headings, summaries, and
   recommendations. Per user: *"Don't frame things by what they are
   not."* Reviewer (this agent) will sweep drafts for "stop", "avoid",
   "no longer", "instead of" framing.
6. **SPEC.md MUST NOT cite token cost as a primary justification** for
   any change. Per user: *"I don't care about token use."* Reducing
   noise (F9 placeholder) is fine when justified by signal/team
   dynamics; "saves tokens" is not.
7. **Identity authority statements MUST be preserved** (Skeptic R3).
   Re-routing or gating identity injection is in scope; weakening
   coordinator's "If user sends 'x'" or skeptic's "You CANNOT cut
   features" is not. The user has not asked for authority changes.
8. **Issue #28 scope: format-only, not opt-out** (Skeptic R2). An
   opt-out toggle silently restores F4/F5/F7 -- a regression vector the
   user did not ask for. If a true opt-out is desired, the spec must
   surface that as an explicit user decision.

---

## 6. Drift watch-list (Specification phase)

I will flag any of these in spec drafts:

- [WARNING] Spec stops at engine knobs and leaves bundled `project_team`
  prompt content untouched.
- [WARNING] "Regardless of workflow" silently re-scoped to project_team only.
- [WARNING] "Review and suggest at all phases" reduced to a one-time audit.
- [WARNING] Identity authority statements removed or hollowed out under
  Skeptic / role-axis recommendations.
- [WARNING] Token-cost justification reappearing.
- [WARNING] Contrast-based or negative framing in spec prose.
- [WARNING] Failure modes from `abast_accf332_sync` cited but not mapped
  to specific changes.
- [WARNING] "Team dynamics" missing from success criteria.
- [WARNING] Wording shifts (Section 2 above) adopted in user-facing
  documents without explicit sign-off.

---

## 7. Recommended user checkpoints during Specification

1. **Mid-spec checkpoint -- Scope decisions (Q1, Q2):**
   - Confirm "regardless of workflow" is global.
   - Confirm what "review and suggest at all phases" means
     operationally (proposed: each role agent reviews its own
     identity.md and phase.md at every phase advance, with a standing
     channel to coordinator for proposed edits).
2. **Mid-spec checkpoint -- Semantics decisions (Q3, Q4, Q5, Q6 from
   leadership_findings):** standing-by + broadcast interaction; #28
   scope; default-roled constraints; freshness contract.
3. **Pre-lock checkpoint -- Failure-mode mapping:** show user the
   mapping from `abast_accf332_sync` F1-F9 to specific proposed
   changes, so they can veto any that feel off.
4. **Pre-lock checkpoint -- User wording:** show user the wording-shift
   table (Section 2) and confirm each.

---

## 8. Recommendation

Specification authors should:

- Add team dynamics as a first-class success criterion in SPEC.md.
- Specify the ongoing "review and suggest" mechanism, not only the
  audit artifact.
- Default "environment segment" to global scope; flag if narrowing.
- Use the user's vocabulary in user-facing sections; technical
  decomposition stays in axis docs.
- Trace every change to either a user quote or an `F#` failure mode.
- Run a contrast-framing sweep before lock (this agent will sweep too).

Status: **NEEDS CLARIFICATION** at the two scope questions; otherwise
the proposed Specification direction is **ALIGNED** with v4 vision.
