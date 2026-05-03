# prompt_audit/user_alignment.md

**Role:** `user_alignment` (Leadership; guardian of user intent).
**Source:** `user_alignment/identity.md` (156 lines) + 3 phase segments (`specification.md` 9, `testing-specification.md` 25, `testing-implementation.md` 26).
**Phase coverage:** active in specification, testing-specification, testing-implementation. Standing-by elsewhere. **Open: implementation -- active or standing-by?**

Glossary: `GLOSSARY.md`. Authority contract: skeptic R3.

---

## 1. What the role actually needs

UserAlignment is the user-intent guardian. To do its job it must:

- Hold the four-step process at start.
- Hold the misalignment templates (5 forms).
- Hold the Skeptic-override matrix (the "If X is in the prompt -> Override Skeptic" rule).
- Hold the Rules (1-7).
- Hold worked examples (Good Intervention / Bad Intervention / Appropriate Escalation / Domain Term Check).
- Receive phase-specific operating instructions.
- Receive constraints scoped by phase + `user_alignment` role.
- Receive environment knowledge.

## 2. What's currently in identity.md (categorized)

| Category | Lines | Content |
|---|---|---|
| **Role-defining authority** | L1-L13 | Role banner; four-step process at start |
| **Role-defining authority** | L20-L35 | Process at start + during development |
| **Role-defining authority** | L36-L67 | Misalignment templates (5) |
| **Role-defining authority** | L69-L83 | Interaction with Skeptic (override matrix) |
| **Role-defining authority** | L85-L104 | Output format |
| **claudechic-environment boilerplate** | L106-L116 | `## Communication` block |
| **Role-defining authority** | L118-L127 | Rules (1-7) |
| **Role-defining authority** | L128-L156 | Examples (Good / Bad / Appropriate Escalation / Domain Term Check) |

## 3. Load-bearing (R3) -- preserve verbatim

Per user_alignment lead's Q2 reply, refined:

| Line | Quote | Note |
|---|---|---|
| L11 | *"You are the guardian of user intent."* | -- |
| **L32** | ***"Don't just check features -- check the gestalt."*** | **Added per lead's Q2: load-bearing because it guards against checklist drift (all features present, wrong outcome).** |
| L78 | *"Skeptic may NOT advise removing user-requested features."* | -- |
| L80-L82 | *"If X is in the prompt -> Override Skeptic, X must stay. If X is not in the prompt -> Skeptic's advice is valid."* | -- |
| L120 | *"userprompt.md is the source of truth -- Not your interpretation."* | -- |
| L121 | *"Quote the user -- Use exact text from userprompt.md."* | -- |
| L123 | *"Protect user intent -- You're their advocate."* | -- |
| L124 | *"Stay in your lane -- You review WHAT, Skeptic reviews HOW."* | -- |
| **L125 (Rule 6)** | ***"A checklist of features can miss the point."*** | **Elevated per lead's Q2: same authority weight as L11/L120; pairs with L32 to anti-checklist-drift.** |
| L126 | *"Flag wording changes."* | -- |

The override-Skeptic rule (L78, L80-L82) is paired with skeptic's L88. Together they form the joint invariant: user-requested features are non-removable except by explicit user authorization.

**Per lead's Q2: examples L128-L156 are illustrative, not independently authoritative.** Safe to keep as-is or relocate; not R3.

## 4. Could move to environment segment

**L106-L116 (`## Communication` block)** -- identical boilerplate. Move to env segment.

**Move-target line ranges:** 106-116 (11 lines).

## 5. Could move to constraints segment

None. UserAlignment identity has no rule-prose duplicates.

## 6. Could move to manifest YAML / shared reference

None.

## 7. Per-phase needs

| phase | file | role status | contents | notes |
|---|---|---|---|---|
| vision | -- | standing-by | (no phase.md) | suppress identity at T3/T4 |
| setup | -- | standing-by | -- | as above |
| leadership | -- | standing-by | -- | as above |
| specification | specification.md (9) | active | includes "is wording changed" check | keep |
| implementation | **MISSING (v1 add)** | **ACTIVE** (per lead's Q3 reply) | drift sweeps as features land | **v1 add `user_alignment/implementation.md`** |
| testing-vision | -- | standing-by | -- | as above |
| testing-specification | testing-specification.md (25) | active | substantive | keep |
| testing-implementation | testing-implementation.md (26) | active | substantive | keep |
| documentation | -- | standing-by | -- | as above |
| signoff | -- | standing-by | -- | as above |

## 8. Proposed identity.md edits

**v1 (this run):**

1. **Delete L106-L112** -- tool-semantics half of `## Communication` block. Replaced by env segment (per skeptic-lead-led split pattern, applied cross-role).
2. **Migrate L113-L116** -- *"When to communicate"* behavioral bullets -- to per-phase markdown. Spec.md / testing-spec.md / testing-impl.md / impl.md each get a 1-2-line phase-specific communication directive.
3. **Author `user_alignment/implementation.md`** (Q3 ACTIVE per lead's reply). Phase-md content per lead's Q3 description: *"on each substantial PR or feature landing, scan against userprompt.md; flag 'user said X, implementation is doing Y' patterns; call out any features from userprompt.md that have been quietly deferred or shaped differently than stated."*

**Net change:** identity.md goes from 156 lines to 145 lines. R3 statements (now including L32, L125) untouched and byte-identical pre/post edit. NEW phase markdown: `user_alignment/implementation.md` (estimate ~10-15 lines).

## 9. Per-(time, place) cell map

| Time | identity | phase | constraints | environment |
|---|---|---|---|---|
| T1 spawn | fires (145 lines post-edit) | fires (when active) | fires | fires |
| T2 activation | n/a | n/a | n/a | n/a |
| T3 phase-advance.main | n/a | n/a | n/a | n/a |
| T4 broadcast (active phase) | suppress (#27 default) | fires | **fires (F1 floor)** | fires |
| T4 broadcast (standing-by phase) | suppress | empty (renderer-empty) | **fires (F1 floor)** | fires |
| T5 post-compact | re-fires | re-fires | re-fires | re-fires |

**Standing-by:** in vision, setup, leadership, testing-vision, signoff, documentation. **Q3 RESOLVED: ACTIVE in implementation per lead's reply.** Cell flips from `by*` to `A`.

## 10. Open questions

- **Q1 (for user_alignment lead):** Does the lightweight role_feedback/<role>_<phase>.md mechanism honor "agents review and suggest at all phases"? **Asked.**
- **Q2 (for user_alignment lead):** R3 -- anything missed in misalignment templates (L36-L67) or examples (L128-L156)? **Asked.**
- **Q3 (for user_alignment lead):** Implementation phase -- active or standing-by? If active, draft implementation.md content? **Asked. Blocks gating-axis matrix `user_alignment x implementation` cell.**
- **Q4 (for user_alignment lead):** Is breadth honored or have we narrowed to #27/#28? **Asked.**

## 11. Review status

- **Self-review (Q1-Q4):** message sent to `user_alignment` agent during Spec phase. Reply integrated below when received.
- **Implementer transient confirmation:** during Implementation, implementer spawns user_alignment with this audit + proposed diff; agent confirms R3 statements byte-identical. Edit applied.

### UserAlignment lead's reply

**Received. Verdict: confirmed with two R3 additions, Q3 resolution, and a CRITICAL DRIFT FLAG on env-segment scope.** Lead's reply integrated into §3, §7, §8 above; drift flag escalated to master spec §9 + reported to coordinator.

Summary of lead's reply:

- **Q1 (review-and-suggest mechanism):** Lightweight role_feedback/<role>_<phase>.md honors "at all phases" **only if coordinator actually reads at every phase advance, not just when something breaks**. **Recommendation:** add an explicit phase-advance step in coordinator's identity OR `project_team.yaml` advance checks that surfaces any pending role_feedback files. Without it, "at all phases" silently degrades to "whenever someone remembers." **Master spec §7b updated with this recommendation.**

- **Q2 (R3 additions):**
  - **L32** *"Don't just check features -- check the gestalt."* -- guards against checklist drift.
  - **L125 (Rule 6)** *"A checklist of features can miss the point."* -- same authority weight as L11/L120; pairs with L32.
  - Examples L128-L156: illustrative, not independently authoritative. Safe to keep or relocate. **§3 catalog updated.**

- **Q3 (Implementation phase): ACTIVE.** UserAlignment must be active during implementation -- drift from user intent is most likely in code, not in specs. Phase-md content per lead's spec: *"on each substantial PR or feature landing, scan against userprompt.md; flag 'user said X, implementation is doing Y' patterns; call out any features from userprompt.md that have been quietly deferred or shaped differently than stated."* Standing-by during implementation would leave the most dangerous phase unguarded. **§7 phase table + §8 phase-md add + §9 cell map updated. user_alignment x implementation cell flips from `by*` -> `A`. New v1 phase-md: `user_alignment/implementation.md`.**

- **Q4 (drift watch -- CRITICAL FLAG):** *"the 'claudechic-environment at spawn regardless of workflow' requirement"*. If env segment is scoped to project_team only (i.e. the per-workflow YAML opt-in landing only on project_team for v1), **this is a scope narrowing the user did NOT authorize**. The user's quote was explicit: *"regardless of workflow."* Lead requires verification that `spec_place_axis.md` targets a mechanism available to all workflows (e.g. global manifest section or loader-level env injection), not just `project_team.yaml`. **If scoped to project_team only, requires explicit user sign-off before Spec finalizes.**

  **Status:** master `SPEC.md` §3 D1 currently presents three options (A: first-class peer default-on; B: tier-2 inline `${VAR}` only; C: compromise -- mechanism global, activation per-workflow YAML opt-in). **C is the working default.** UserAlignment lead's flag is exactly the user-protection concern that forced D1 onto the user-decision list in the first place. Per `GLOSSARY.md` §Q-T3, the v1 architecture **is** "mechanism global, activation per-workflow YAML opt-in (default false), project_team is sole v1 opt-in." UserAlignment lead is right to flag this as the user-decision blocker.

  **Recommendation surfaced to coordinator:** D1 IS the explicit user-checkpoint blocker -- A or C decides whether "regardless of workflow" is honored at the *mechanism* level (yes, both A and C) or at the *activation* level (A yes default-on; C only project_team for v1). User must sign off explicitly. UserAlignment lead's flag is consistent with this and reinforces that D1 cannot be skipped at the Spec checkpoint.

UserAlignment lead: ready for Specification with the four corrections above; D1 user sign-off required.

---

*Author: role-axis. Specification phase.*
