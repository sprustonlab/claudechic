# prompt_audit/implementer.md

**Role:** `implementer` (writes the actual code).
**Source:** `implementer/identity.md` (109 lines) + 2 phase segments (`implementation.md` 10, `testing.md` 10).
**Phase coverage:** active in implementation, testing. Standing-by elsewhere (typically closed at end of testing).

Glossary: `GLOSSARY.md`. Authority contract: skeptic R3.

---

## 1. What the role actually needs

Implementer writes the code per spec. To do its job it must:

- Hold the faithful-implementation principle.
- Hold code-style, error-handling, dependency rules.
- Hold the output format.
- Hold the interaction map (handoffs to/from other roles).
- Hold the bounded-authority Rules (no scope creep / no architecture freelancing).
- Receive phase-specific operating instructions.
- Receive constraints (especially `global:no_bare_pytest` and `project-team:no_push_before_testing`).
- Receive environment knowledge.

## 2. What's currently in identity.md (categorized)

| Category | Lines | Content |
|---|---|---|
| **Role-defining authority** | L1-L20 | Role banner; faithful-implementation principle; workflow |
| **Role-defining authority** | L29-L46 | Code style; error handling; dependencies |
| **Role-defining authority** | L47-L65 | Output format |
| **Cross-role coordination** | L67-L88 | Interactions; handoffs |
| **claudechic-environment boilerplate** | L90-L100 | `## Communication` block |
| **Role-defining authority** | L102-L108 | Rules |
| **Role-defining authority** | L109 (Rule #6) | *"Run targeted tests only ... Never run the full suite during active development"* -- bad-thing-prevention rule. **Per user clarification 2026-05-02: stays in identity prose; do NOT reference constraints segment. Constraints segment is configurable via `constraints_segment.scope.sites` so a reference is fragile.** |

## 3. Load-bearing (R3) -- preserve verbatim

| Line | Quote |
|---|---|
| L1-L3 | *"You write the actual code based on the architecture and design decisions."* |
| L102 | *"Implement what's specified -- Don't add unrequested features."* |
| L103 | *"Follow the architecture -- Don't violate axis separation."* |
| L107 | *"Ask when unclear -- Better to clarify than assume."* |

These four = the bounded-authority block (analogous to skeptic L84-L88).

## 4. Could move to environment segment

**L90-L100 (`## Communication` block)** -- identical boilerplate. Move to env segment.

**Move-target line ranges:** 90-100 (11 lines).

## 5. Could move to constraints segment

**Nothing.** Per user clarification 2026-05-02 (verbatim): *"don't reference something we can gate with settings"*. The constraints segment is configurable via `constraints_segment.scope.sites` (#28); an identity reference to it is fragile. Pytest-policy prose at L109 stays unchanged. Asymmetric on purpose: comm-block is recoverable boilerplate (acceptable degradation if missed); pytest is bad-thing-prevention (must remain in-prose).

## 6. Could move to manifest YAML / shared reference

None.

## 7. Per-phase needs

| phase | file | role status | contents | notes |
|---|---|---|---|---|
| vision | -- | (not spawned) | -- | implementer not spawned this early |
| setup | -- | (not spawned) | -- | as above |
| leadership | -- | (not spawned) | -- | as above |
| specification | -- | (not spawned) | -- | as above |
| implementation | implementation.md (10) | active | tight | keep |
| testing-vision | -- | (not spawned) | -- | as above |
| testing-specification | -- | (not spawned) | -- | as above |
| testing | testing.md (10) | active | tight | keep |
| testing-implementation | -- | standing-by (or active?) | gap if active | gating-axis matrix shows `.` (active). **Coordinate.** |
| documentation | -- | active (per gating matrix `A`) | gap | optional v2 add |
| signoff | -- | (closed) | -- | -- |

**Note:** implementer is typically spawned mid-workflow. When spawned in implementation, it persists into testing. Gating-axis matrix shows implementer with `S` (suppress) in most phases -- consistent with "spawned in implementation only."

## 8. Proposed identity.md edits

**v1 (this run):**

1. **Delete L90-L100** -- `## Communication` block. Replaced by env segment.
2. **Pytest-policy rule (L109): NO CHANGE.** Per user clarification 2026-05-02, stays in-prose. Constraints reference rolled back.

**Net change:** identity.md goes from 109 lines to ~99 lines (comm-block hoist only). R3 statements (L1-L3, L102, L103, L107, **L109**) untouched and byte-identical pre/post edit.

## 9. Per-(time, place) cell map

| Time | identity | phase | constraints | environment |
|---|---|---|---|---|
| T1 spawn | fires (~99 lines post-edit) | fires (when active) | fires | fires |
| T2 activation | n/a | n/a | n/a | n/a |
| T3 phase-advance.main | n/a | n/a | n/a | n/a |
| T4 broadcast (active phase) | suppress (#27 default) | fires | **fires (F1 floor)** | fires |
| T4 broadcast (standing-by phase) | suppress | empty | **fires (F1 floor)** | fires |
| T5 post-compact | re-fires | re-fires | re-fires | re-fires |

**Standing-by:** when spawned during implementation but a non-active phase fires (e.g. broadcast to documentation phase). Closed at signoff -- not standing-by past signoff.

## 10. Open questions

- **Implementation ownership:** during this Spec phase's followon Implementation phase, the implementer applies the proposed diff. Self-review (Q1-Q4) deferred to that phase. **Marked: needs role-agent review during Implementation.**
- **L67-L88 interaction table:** pure cross-role coordination; could move to a shared "team_dynamics.md" reference. **Out of scope v1.**

## 11. Review status

- **Self-review:** **needs role-agent review during Implementation.** Implementer is not spawned during Specification. The Implementation phase coordinator delegates the transient role-agent confirmation step (per Spec §4a / §4b mechanism).
- **Implementer transient confirmation:** during Implementation, the new implementer agent confirms its own R3 statements byte-identical against this audit before the edit is applied. **This is the literal "agent reviews its own content" step.**

---

*Author: role-axis. Specification phase. Marked: needs role-agent review during Implementation.*
