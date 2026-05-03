# prompt_audit/lab_notebook.md

**Role:** `lab_notebook` (pre-registration; experimental record-keeping).
**Source:** `lab_notebook/identity.md` (352 lines). **No phase markdown today.**

Glossary: `GLOSSARY.md`. Authority contract: skeptic R3.

---

## 1. What the role actually needs

LabNotebook holds the pre-registration / no-modify-results contract. To do its job it must:

- Hold the role banner + insight.
- Hold activation triggers + notebook location + file naming.
- Hold the entry structure templates (sections 1-6).
- Hold special entry types (decision records, corrections).
- Hold the Rules.
- Hold INDEX.md format + tags.
- Hold the interactions map.
- Hold the **authority block** (CAN/CANNOT).
- Hold The Principle.
- Receive phase-specific operating instructions (currently absent).
- Receive constraints.
- Receive environment knowledge.

## 2. What's currently in identity.md (categorized)

| Category | Lines | Content |
|---|---|---|
| **Role-defining authority** | L1-L17 | Role banner + The Insight |
| **Role-defining authority** | L19-L31 | Activation triggers |
| **Role-defining authority** | L33-L51 | Notebook location + file naming |
| **Role-defining authority** | L53-L201 | Entry structure (sections 1-6 with templates) |
| **Role-defining authority** | L203-L249 | Special entry types |
| **claudechic-environment boilerplate** | L253-L264 | `## Communication` block |
| **Role-defining authority** | L266-L282 | Rules (1-8) |
| **Role-defining authority** | L286-L307 | INDEX.md format |
| **Role-defining authority** | L311-L320 | Tags |
| **Cross-role coordination** | L324-L335 | Interactions |
| **Role-defining authority** | L339-L347 | **Authority block** |
| **Role-defining authority** | L351-L352 | The Principle |

## 3. Load-bearing (R3) -- preserve verbatim

| Line | Quote |
|---|---|
| L267 | *"Write expected results before seeing actual results. This is non-negotiable."* |
| L273 | *"Never modify results after the fact."* |
| L341-L347 | Authority block (CAN require / CAN refuse / CAN flag / CAN request corrections / CANNOT make experimental design decisions / CANNOT suppress or modify results) |

These are the integrity invariants for experimental record-keeping.

## 4. Could move to environment segment

**L253-L264 (`## Communication` block)** -- identical boilerplate. Move to env segment.

## 5. Could move to constraints segment

None.

## 6. Could move to manifest YAML / shared reference

**L53-L201 (entry-structure templates):** could move to a separate `lab_notebook/templates.md` referenced from identity. Out of scope v1; flag.

## 7. Per-phase needs

LabNotebook is spawned only on experiment-shaped projects. When spawned, active in implementation + testing-implementation per gating matrix `A**`.

| phase | file (today) | role status | notes |
|---|---|---|---|
| implementation | -- (gap) | active when experiment-shaped | v2 add `implementation.md` |
| testing-implementation | -- (gap) | active when experiment-shaped | v2 add `testing-implementation.md` |

## 8. Proposed identity.md edits

**v1 (this run):**

1. **Delete L253-L264** -- `## Communication` block. Replaced by env segment.

**Net change:** 352 -> ~340 lines. R3 statements untouched.

**Out of scope v1 (v2):**

2. Extract L53-L201 templates to `lab_notebook/templates.md`.
3. Add phase mds for implementation + testing-implementation.

## 9. Per-(time, place) cell map

| Time | identity | phase | constraints | environment |
|---|---|---|---|---|
| T1 spawn | fires (~340 lines post-edit) | empty | fires | fires |
| T4 broadcast | suppress (#27) | empty | **fires (F1 floor)** | fires |
| T5 post-compact | re-fires | empty | re-fires | re-fires |

**Standing-by under v1 static predicate:** all phases (no `<phase>.md` files).

## 10. Open questions

- **Phase-md adds + template extraction:** **needs role-agent review during Implementation.**

## 11. Review status

- **Self-review:** **needs role-agent review during Implementation.**

---

*Author: role-axis. Specification phase. Marked: needs role-agent review during Implementation.*
