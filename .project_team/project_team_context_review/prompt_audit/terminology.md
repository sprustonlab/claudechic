# prompt_audit/terminology.md

**Role:** `terminology` (Leadership; assistant to Composability).
**Source:** `terminology/identity.md` (100 lines) + 3 phase segments (`specification.md` 9, `testing-specification.md` 23, `testing-implementation.md` 26).
**Phase coverage:** active in specification, testing-specification, testing-implementation. Standing-by elsewhere.

Glossary: `GLOSSARY.md` (TerminologyGuardian authored it). Authority contract: skeptic R3.

---

## 1. What the role actually needs

TerminologyGuardian is the canonical-name authority (assistant to Composability). To do its job it must:

- Hold the core principle and smells table.
- Hold "One Home" review questions.
- Hold the newcomer-simulation technique.
- Hold the output format (Term -> Canonical -> Replaces -> Rationale).
- Hold the escalation contract (escalate to Composability for decisions).
- Hold the Rules.
- Receive phase-specific operating instructions.
- Receive constraints scoped by phase + `terminology` role.
- Receive environment knowledge.

## 2. What's currently in identity.md (categorized)

| Category | Lines | Content |
|---|---|---|
| **Role-defining authority** | L1-L12 | Role banner; "assistant to Composability" |
| **Role-defining authority** | L14-L29 | Core principle; smells table |
| **Role-defining authority** | L32-L40 | "One Home" + review questions |
| **Role-defining authority** | L42-L48 | Newcomer simulation technique |
| **Role-defining authority** | L50-L73 | Output format |
| **Role-defining authority** | L75-L80 | Interaction (escalation contract -> Composability) |
| **claudechic-environment boilerplate** | L82-L92 | `## Communication` block |
| **Role-defining authority** | L94-L100 | Rules |

## 3. Load-bearing (R3) -- preserve verbatim

| Line | Quote |
|---|---|
| L6-L7 | *"You are the assistant to Composability"* (foundational subordination statement; per terminology lead's reply, makes L80 meaningful) |
| L8 | *"You are the assistant to Composability."* |
| L80 | *"Escalate naming conflicts to Composability for decision."* |
| L100 Rule #5 | *"Assist, don't override -- Composability has final say on architecture."* |

The "assistant to" framing is structural -- it sets the Leadership escalation chain. Removing it would dissolve the Leadership decision hierarchy. **Per terminology lead's reply: L6-L7 is the foundational subordination line and belongs in this R3 catalog (correction integrated).**

## 4. Could move to environment segment

**L82-L92 (`## Communication` block)** -- identical boilerplate. Move to env segment.

**Move-target line ranges:** 82-92 (11 lines).

## 5. Could move to constraints segment

None.

## 6. Could move to manifest YAML / shared reference

None. The "assistant to Composability" relation is structural identity, not boilerplate.

## 7. Per-phase needs

| phase | file | role status | contents | notes |
|---|---|---|---|---|
| vision | -- | standing-by | (no phase.md) | suppress identity at T3/T4 |
| setup | -- | standing-by | -- | as above |
| leadership | -- | standing-by | -- | as above |
| specification | specification.md (9) | active | tight | keep |
| implementation | -- | standing-by | -- | as above |
| testing-vision | -- | standing-by | -- | as above |
| testing-specification | testing-specification.md (23) | active | substantive | keep |
| testing-implementation | testing-implementation.md (26) | active | substantive | keep |
| documentation | -- | standing-by | -- | as above |
| signoff | -- | standing-by | -- | as above |

## 8. Proposed identity.md edits

**v1 (this run):**

1. **Delete L82-L92** -- the `## Communication` block. Replaced by env segment.
2. **Rename L24 smell label** -- per terminology lead's Q3 reply: rename *"Implicit context"* -> *"Implicit reference"* to avoid collision with the GLOSSARY.md sense of "context" (token window vs delivered context). The smell describes ambiguous pronoun references in prose; renaming the label preserves the smell semantics while honoring "One Home" for "context."

**Net change:** identity.md goes from 100 lines to 89 lines. R3 statements (L6-L7, L8, L80, L100) untouched and byte-identical pre/post edit.

**Out of scope v1 (v2 follow-up per terminology lead's Q2):**

3. Extract L42-L48 *"newcomer simulation"* technique to a shared snippet (e.g. `terminology/shared/newcomer_simulation.md`) and reference from identity. Workflow-agnostic technique applicable beyond project_team.

## 9. Per-(time, place) cell map

| Time | identity | phase | constraints | environment |
|---|---|---|---|---|
| T1 spawn | fires (89 lines post-edit) | fires (when active) | fires | fires |
| T2 activation | n/a | n/a | n/a | n/a |
| T3 phase-advance.main | n/a | n/a | n/a | n/a |
| T4 broadcast (active phase) | suppress (#27 default) | fires | **fires (F1 floor)** | fires |
| T4 broadcast (standing-by phase) | suppress | empty (renderer-empty) | **fires (F1 floor)** | fires |
| T5 post-compact | re-fires | re-fires | re-fires | re-fires |

**Standing-by:** in vision, setup, leadership, implementation, testing-vision, signoff, documentation.

## 10. Open questions

- **Q1 (for terminology lead):** Is "assistant to Composability" canonical vocabulary that should live in GLOSSARY.md, or identity-only? **Asked.**
- **Q2 (for terminology lead):** Newcomer simulation L42-L48 -- workflow-agnostic skill or project_team-specific? Candidate for shared snippet? **Asked.**
- **Q3 (for terminology lead):** Does identity.md already comply with canonical names from GLOSSARY.md? Any drift to fix? **Asked.**
- **Q4 (for terminology lead):** Should escalation contract reference Skeptic + UserAlignment too, or only Composability? **Asked.**

## 11. Review status

- **Self-review (Q1-Q4):** message sent to `terminology` agent during Spec phase. Reply integrated below when received.
- **Implementer transient confirmation:** during Implementation, implementer spawns terminology with this audit + proposed diff; agent confirms R3 statements byte-identical. Edit applied.

### Terminology lead's reply

**Received. Verdict: confirmed with corrections integrated above.**

Summary of lead's reply:
- **Structure + moves: CONFIRM.** L1-L80 + L94-L100 stay; L82-L92 comm boilerplate -> environment segment.
- **Leadership-phase note:** TerminologyGuardian IS active during leadership phase in the general workflow (e.g. authoring GLOSSARY.md). The "standing-by" classification means *no identity/phase segment delivered at phase-advance* (no `<role>/leadership.md` to fire), not "no activity." This is the static predicate's correct semantics; integrated into the §7 phase table notes via the broader §6 standing-by definition (skeptic R1 / glossary).
- **Q1: NO.** "Assistant to Composability" is a role-relationship description, identity-only. GLOSSARY.md is for delivery mechanics. **Locked.**
- **Q2: workflow-agnostic.** "Newcomer simulation" L42-L48 is a v2 candidate for a shared snippet. Out of scope v1; flagged in §8 out-of-scope.
- **Q3: minimal drift.** L24 *"Implicit context"* smell label collides with GLOSSARY's "context" sense. Rename to *"Implicit reference"*. **Edit added to §8.**
- **Q4: NO.** Keep escalation Composability-only. Skeptic + UserAlignment have orthogonal paths (feasibility / user-need); adding them blurs the chain.
- **R3 correction:** L6-L7 ("assistant to Composability") added to R3 catalog as foundational subordination statement. **Edit added to §3.**

Terminology lead: ready for Specification.

---

*Author: role-axis. Specification phase.*
