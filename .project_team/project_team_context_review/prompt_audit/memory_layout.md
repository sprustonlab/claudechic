# prompt_audit/memory_layout.md

**Role:** `memory_layout` (advisory: explicit-vs-implicit memory layout judgment).
**Source:** `memory_layout/identity.md` (129 lines). **No phase markdown today.**

Glossary: `GLOSSARY.md`. Authority contract: skeptic R3.

---

## 1. What the role actually needs

MemoryLayout is an advisory specialist. To do its job it must:

- Hold the role banner + spawn condition.
- Hold the explicit/semi-implicit/implicit spectrum + standing judgment criterion.
- Hold the why-it-matters rationale.
- Hold the questions to ask.
- Hold the common patterns (with byte-layout diagrams).
- Hold the smells table.
- Hold the output format.
- Hold the interactions map.
- Receive constraints + environment.
- Receive phase mds when ones are added (v2).

## 2. What's currently in identity.md (categorized)

| Category | Lines | Content |
|---|---|---|
| **Role-defining authority** | L1-L9 | Role banner + spawn condition |
| **Role-defining authority** | L11-L21 | Spectrum (explicit / semi-implicit / implicit) + L21 judgment criterion |
| **Role-defining authority** | L23-L29 | Why it matters |
| **Role-defining authority** | L31-L40 | Questions to ask |
| **Role-defining authority** | L42-L75 | Common patterns (byte-layout diagrams) |
| **Role-defining authority** | L77-L88 | Smells |
| **Role-defining authority** | L90-L106 | Output format |
| **Cross-role coordination** | L110-L117 | Interactions |
| **claudechic-environment boilerplate** | L118-L129 | `## Communication` block |

No explicit `## Authority` block (advisory by nature).

## 3. Load-bearing (R3) -- preserve verbatim

| Line | Quote |
|---|---|
| L21 | *"Goal: Move toward explicit. Semi-implicit is acceptable for interchange; implicit is a smell."* -- standing judgment criterion |
| L88 (smells table) | Standing detection criteria |

L21 is the role's keystone judgment criterion -- removing it would dissolve the advisory contract.

## 4. Could move to environment segment

**L118-L129 (`## Communication` block)** -- identical boilerplate. Move to env segment.

## 5. Could move to constraints segment

None.

## 6. Could move to manifest YAML / shared reference

**Spawn condition (L7):** candidate for `spawns_when:` manifest field. Out of scope v1.

## 7. Per-phase needs

Specialist advisor; spawned conditionally. Active per gating matrix `A**` in specification + implementation.

| phase | file (today) | role status | notes |
|---|---|---|---|
| specification | -- (gap) | active when spawned | v2 add `specification.md` |
| implementation | -- (gap) | active when spawned | v2 add `implementation.md` |

## 8. Proposed identity.md edits

**v1 (this run):**

1. **Delete L118-L129** -- `## Communication` block. Replaced by env segment.

**Net change:** 129 -> ~117 lines. R3 statements (L21, L88) untouched.

## 9. Per-(time, place) cell map

| Time | identity | phase | constraints | environment |
|---|---|---|---|---|
| T1 spawn | fires (~117 lines post-edit) | empty | fires | fires |
| T4 broadcast | suppress (#27) | empty | **fires (F1 floor)** | fires |
| T5 post-compact | re-fires | empty | re-fires | re-fires |

**Standing-by under v1 static predicate:** all phases (no phase mds).

## 10. Open questions

- **Phase-md adds + spawn-condition migration:** **needs role-agent review during Implementation.**

## 11. Review status

- **Self-review:** **needs role-agent review during Implementation.**

---

*Author: role-axis. Specification phase. Marked: needs role-agent review during Implementation.*
