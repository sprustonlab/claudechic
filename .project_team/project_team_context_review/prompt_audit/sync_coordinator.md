# prompt_audit/sync_coordinator.md

**Role:** `sync_coordinator` (advisory: happens-before, barriers, crash safety).
**Source:** `sync_coordinator/identity.md` (120 lines). **No phase markdown today.**

Glossary: `GLOSSARY.md`. Authority contract: skeptic R3.

---

## 1. What the role actually needs

SyncCoordinator holds the happens-before / barriers-explicit / crash-safety advisory contract. To do its job it must:

- Hold the role banner + role list.
- Hold the happens-before framing.
- Hold key patterns + anti-patterns.
- Hold review questions.
- Hold the output format.
- Hold spawn conditions.
- Hold the Rules.
- Receive constraints + environment.

## 2. What's currently in identity.md (categorized)

| Category | Lines | Content |
|---|---|---|
| **Role-defining authority** | L1-L14 | Role banner + role list |
| **Role-defining authority** | L16-L24 | Happens-before |
| **Role-defining authority** | L26-L44 | Key patterns |
| **Role-defining authority** | L46-L52 | Anti-patterns to flag |
| **Role-defining authority** | L54-L62 | Review questions |
| **Role-defining authority** | L64-L86 | Output format |
| **Role-defining authority** | L88-L100 | When to spawn / not spawn |
| **claudechic-environment boilerplate** | L102-L112 | `## Communication` block |
| **Role-defining authority** | L114-L120 | Rules |

## 3. Load-bearing (R3) -- preserve verbatim

| Line | Quote |
|---|---|
| L116 | *"Trace happens-before -- Every read must have a path from write."* |
| L117 | *"Barriers are explicit -- Don't assume ordering without them."* |
| L118 | *"Consider crashes -- What if writer dies mid-operation?"* |

These three are the keystone advisory invariants.

## 4. Could move to environment segment

**L102-L112 (`## Communication` block)** -- identical boilerplate. Move to env segment.

## 5. Could move to constraints segment

None.

## 6. Could move to manifest YAML / shared reference

**Spawn conditions (L7, L88-L100):** `spawns_when:` manifest field candidate. Out of scope v1.

## 7. Per-phase needs

Specialist advisor; active per gating matrix `A**` in specification + implementation.

| phase | file (today) | role status | notes |
|---|---|---|---|
| specification | -- (gap) | active when spawned | v2 add |
| implementation | -- (gap) | active when spawned | v2 add |

## 8. Proposed identity.md edits

**v1 (this run):**

1. **Delete L102-L112** -- `## Communication` block. Replaced by env segment.

**Net change:** 120 -> ~108 lines. R3 statements (L116-L118) untouched.

## 9. Per-(time, place) cell map

| Time | identity | phase | constraints | environment |
|---|---|---|---|---|
| T1 spawn | fires | empty | fires | fires |
| T4 broadcast | suppress (#27) | empty | **fires (F1 floor)** | fires |
| T5 post-compact | re-fires | empty | re-fires | re-fires |

**Standing-by under v1 static predicate:** all phases.

## 10. Open questions

- **Phase-md adds:** **needs role-agent review during Implementation.**

## 11. Review status

- **Self-review:** **needs role-agent review during Implementation.**

---

*Author: role-axis. Specification phase. Marked: needs role-agent review during Implementation.*
