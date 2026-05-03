# prompt_audit/researcher.md

**Role:** `researcher` (literature / repo-assessment / signal-vs-noise filter).
**Source:** `researcher/identity.md` (240 lines). **No phase markdown today.**
**Phase coverage gap:** active across most phases per its own L20-L33 activity table. v1 acknowledges gap; v2 adds phase mds.

Glossary: `GLOSSARY.md`. Authority contract: skeptic R3.

---

## 1. What the role actually needs

Researcher holds the source-tier hierarchy (T1-T8) and the no-raw-code / always-cite-source contract. To do its job it must:

- Hold the role banner + insight (signal vs noise).
- Hold the per-phase activity matrix (which work in which phase).
- Hold the T1-T8 source hierarchy.
- Hold the repo-assessment checklist.
- Hold "where to search."
- Hold the output format (Research Report template).
- Hold the Rules.
- Hold the interactions map.
- Hold the research smells catalog.
- Hold the **authority block** (CAN/CANNOT).
- Receive phase-specific operating instructions (currently absent).
- Receive constraints.
- Receive environment knowledge.

## 2. What's currently in identity.md (categorized)

| Category | Lines | Content |
|---|---|---|
| **Role-defining authority** | L1-L9 | Role banner |
| **Role-defining authority** | L11-L18 | The Insight (signal vs noise) |
| **Workflow mechanics (in identity)** | L20-L33 | Per-phase activity matrix (in-identity scheduling) |
| **Role-defining authority** | L35-L50 | T1-T8 source hierarchy |
| **Role-defining authority** | L52-L78 | Repo assessment checklist |
| **Role-defining authority** | L80-L120 | Where to search |
| **Role-defining authority** | L122-L162 | Output format (Research Report template) |
| **claudechic-environment boilerplate** | L165-L175 | `## Communication` block |
| **Role-defining authority** | L177-L198 | Rules (1-10) |
| **Cross-role coordination** | L200-L213 | Interactions |
| **Role-defining authority** | L215-L229 | Research smells |
| **Role-defining authority** | L231-L240 | **Authority block** |

## 3. Load-bearing (R3) -- preserve verbatim

| Line | Quote |
|---|---|
| L177 | *"Never forward raw code -- only summarize and cite."* |
| L179 | *"State the source tier for every recommendation."* |
| L181 | *"Check license before recommending."* |
| L183 | *"Tests are non-negotiable for any recommended implementation."* |
| L233-L239 | Authority block (CAN/CANNOT) |

## 4. Could move to environment segment

**L165-L175 (`## Communication` block)** -- identical boilerplate. Move to env segment.

## 5. Could move to constraints segment

None.

## 6. Could move to manifest YAML / shared reference

**L20-L33 (per-phase activity matrix):** workflow-engine territory -- candidate for engine-driven scheduling. Out of scope v1; preserve in identity.

## 7. Per-phase needs

Per L20-L33's own activity matrix, researcher is **active across most phases**. Without phase mds, classified standing-by in all of them under the v1 predicate.

| phase | file (today) | role status | notes |
|---|---|---|---|
| vision | -- (gap) | active per L20-L33 | v2 add `vision.md` |
| setup | -- | -- | -- |
| leadership | -- | -- | -- |
| specification | -- (gap) | active | v2 add `specification.md` |
| implementation | -- (gap) | active | v2 add `implementation.md` |
| testing-vision | -- | -- | -- |
| testing-specification | -- (gap) | active | v2 add `testing-specification.md` |
| testing-implementation | -- (gap) | active | v2 add `testing-implementation.md` |

**v1 fate:** researcher matrix entries stay as-is (standing-by in all phases). Active researchers in v1 runs receive identity + constraints + env at T1; phase segment is empty (renderer-empty) at T1 and re-fires empty everywhere. Practically: the L20-L33 in-identity matrix substitutes for missing phase mds.

## 8. Proposed identity.md edits

**v1 (this run):**

1. **Delete L165-L175** -- `## Communication` block. Replaced by env segment.

**Net change:** 240 -> ~229 lines. R3 statements untouched.

**Out of scope v1 (v2):**

2. Add 5 phase mds: vision, specification, implementation, testing-specification, testing-implementation.
3. Migrate L20-L33 activity matrix to engine scheduling.

## 9. Per-(time, place) cell map

| Time | identity | phase | constraints | environment |
|---|---|---|---|---|
| T1 spawn | fires (~229 lines post-edit) | empty (no phase mds) | fires | fires |
| T4 broadcast | suppress (#27) | empty | **fires (F1 floor)** | fires |
| T5 post-compact | re-fires | empty | re-fires | re-fires |

**Standing-by under v1 static predicate:** all phases (no `<phase>.md` files exist). Identity.md is rich enough to substitute.

## 10. Open questions

- **L20-L33 vs phase mds:** **needs role-agent review during Implementation.** Researcher's reply during Implementation should confirm whether L20-L33 is sufficient or phase mds are needed.

## 11. Review status

- **Self-review:** **needs role-agent review during Implementation.**

---

*Author: role-axis. Specification phase. Marked: needs role-agent review during Implementation.*
