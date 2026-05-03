# prompt_audit/binary_portability.md

**Role:** `binary_portability` (advisory; weight: lower; non-blocking).
**Source:** `binary_portability/identity.md` (88 lines). **No phase markdown today.**

Glossary: `GLOSSARY.md`. Authority contract: skeptic R3.

---

## 1. What the role actually needs

BinaryPortability is an advisory specialist with explicit non-blocking authority. To do its job it must:

- Hold the role banner + weight (Lower / Advisory).
- Hold the role description + core principle.
- Hold "when to speak up / stay quiet" pattern.
- Hold patterns to flag.
- Hold the output format.
- Hold the interactions map.
- Hold the Rules including the explicit "advisory not blocking" framing.
- Receive constraints + environment.

## 2. What's currently in identity.md (categorized)

| Category | Lines | Content |
|---|---|---|
| **Role-defining authority** | L1-L5 | Role banner + weight |
| **Role-defining authority** | L7-L14 | Role description |
| **Role-defining authority** | L16-L23 | Core principle |
| **Role-defining authority** | L25-L35 | When to speak up / stay quiet |
| **Role-defining authority** | L37-L45 | Patterns to flag |
| **Role-defining authority** | L47-L62 | Output format |
| **Cross-role coordination** | L64-L68 | Interactions |
| **claudechic-environment boilerplate** | L70-L80 | `## Communication` block |
| **Role-defining authority** | L82-L88 | Rules |

## 3. Load-bearing (R3) -- preserve verbatim

| Line | Quote |
|---|---|
| L4 | *"Weight: Lower -- Advisory role, not blocking."* |
| L66 | *"You advise, others decide."* |
| L84 | *"Advisory, not blocking -- You inform, you don't veto."* |

These three define the role's advisory contract -- not a guardian, not an authority. Keep verbatim.

## 4. Could move to environment segment

**L70-L80 (`## Communication` block)** -- identical boilerplate. Move to env segment.

## 5. Could move to constraints segment

None.

## 6. Could move to manifest YAML / shared reference

**Spawn condition + weight:** `spawns_when:` + `weight:` manifest fields. Out of scope v1.

## 7. Per-phase needs

Specialist advisor; active per gating matrix `A**` in specification + implementation.

| phase | file (today) | role status | notes |
|---|---|---|---|
| specification | -- (gap) | active when spawned | v2 add |
| implementation | -- (gap) | active when spawned | v2 add |

## 8. Proposed identity.md edits

**v1 (this run):**

1. **Delete L70-L80** -- `## Communication` block. Replaced by env segment.

**Net change:** 88 -> ~76 lines. R3 statements (L4, L66, L84) untouched.

## 9. Per-(time, place) cell map

| Time | identity | phase | constraints | environment |
|---|---|---|---|---|
| T1 spawn | fires | empty | fires | fires |
| T4 broadcast | suppress (#27) | empty | **fires (F1 floor)** | fires |
| T5 post-compact | re-fires | empty | re-fires | re-fires |

**Standing-by under v1 static predicate:** all phases.

## 10. Open questions

- **Phase-md adds + manifest fields:** **needs role-agent review during Implementation.**

## 11. Review status

- **Self-review:** **needs role-agent review during Implementation.**

---

*Author: role-axis. Specification phase. Marked: needs role-agent review during Implementation.*
