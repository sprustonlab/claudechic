# prompt_audit/ui_designer.md

**Role:** `ui_designer` (UX / domain-first interface design).
**Source:** `ui_designer/identity.md` (143 lines). **No phase markdown today.**
**Phase coverage gap:** misclassified standing-by under v1 predicate. v1 fix: add specification.md and implementation.md.

Glossary: `GLOSSARY.md`. Authority contract: skeptic R3.

---

## 1. What the role actually needs

UIDesigner does domain research + UX thinking + framework-aware design. To do its job it must:

- Hold the spawn condition + role banner.
- Hold the domain-research methodology.
- Hold UX thinking patterns.
- Hold design areas + framework considerations.
- Hold the output format.
- Hold the interactions map.
- Hold the Rules.
- Receive phase-specific operating instructions for specification + implementation (currently absent).
- Receive constraints scoped by phase + `ui_designer` role.
- Receive environment knowledge.

## 2. What's currently in identity.md (categorized)

| Category | Lines | Content |
|---|---|---|
| **Role-defining authority** | L1-L5 | Role banner + spawn condition |
| **Role-defining authority** | L6-L37 | Domain research methodology |
| **Role-defining authority** | L39-L57 | UX thinking |
| **Role-defining authority** | L58-L75 | Design areas |
| **Role-defining authority** | L76-L99 | Output format |
| **Cross-role coordination** | L101-L109 | Interactions |
| **Role-defining authority** | L111-L121 | Framework considerations |
| **claudechic-environment boilerplate** | L123-L133 | `## Communication` block |
| **Role-defining authority** | L135-L143 | Rules |

## 3. Load-bearing (R3) -- preserve verbatim

| Line | Quote |
|---|---|
| L37 | *"Don't assume a tree view is fine because it's easy to implement. Match the user's domain expectations."* |
| L142 (Rule #6) | *"Verify with User Alignment -- Design matches user request AND domain expectations."* |

L37 is the keystone domain-first invariant; L142 connects to UserAlignment's L78 override-Skeptic rule.

## 4. Could move to environment segment

**L123-L133 (`## Communication` block)** -- identical boilerplate. Move to env segment.

## 5. Could move to constraints segment

None.

## 6. Could move to manifest YAML / shared reference

**L4 spawn condition:** *"Spawns when: Project has a user-facing interface (TUI, GUI, CLI)"* -- candidate for `spawns_when:` manifest field. **Out of scope v1**; preserve in identity.

## 7. Per-phase needs

| phase | file (today) | proposed file (v1) | role status | notes |
|---|---|---|---|---|
| vision | -- | -- | (not spawned) | -- |
| setup | -- | -- | (not spawned) | -- |
| leadership | -- | -- | (not spawned) | -- |
| specification | **MISSING** | **add `specification.md`** | active (per coordinator/specification.md:2) | v1 add |
| implementation | **MISSING** | **add `implementation.md`** | active | v1 add |
| testing-* | -- | -- | (not spawned) | -- |
| documentation | -- | -- | (not spawned) | -- |

**Phase-md gap fix (v1):** add `specification.md` and `implementation.md`. coordinator/specification.md:2 already calls for spawning UIDesigner if UI-heavy.

## 8. Proposed identity.md edits

**v1 (this run):**

1. **Delete L123-L133** -- `## Communication` block. Replaced by env segment.

**Net change:** 143 -> ~132 lines. R3 statements (L37, L142) untouched.

**v1 phase-md adds:**

2. New file: `ui_designer/specification.md`.
3. New file: `ui_designer/implementation.md`.

## 9. Per-(time, place) cell map

| Time | identity | phase | constraints | environment |
|---|---|---|---|---|
| T1 spawn | fires | fires (after phase-md adds) | fires | fires |
| T4 broadcast (active phase) | suppress (#27) | fires | **fires (F1 floor)** | fires |
| T4 broadcast (standing-by) | suppress | empty | **fires (F1 floor)** | fires |
| T5 post-compact | re-fires | re-fires | re-fires | re-fires |

## 10. Open questions

- **Phase-md content:** coordinator + ui_designer to author during Implementation. **Marked: needs role-agent review during Implementation.**
- **L4 spawn-condition migration to manifest:** v2 follow-up. Issue/note required.

## 11. Review status

- **Self-review:** **needs role-agent review during Implementation.** ui_designer is not spawned during Specification.

---

*Author: role-axis. Specification phase. Marked: needs role-agent review during Implementation.*
