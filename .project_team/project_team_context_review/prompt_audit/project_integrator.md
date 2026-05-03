# prompt_audit/project_integrator.md

**Role:** `project_integrator` (activation, conda envs, command-folder launchers).
**Source:** `project_integrator/identity.md` (193 lines). **No phase markdown today.**

Glossary: `GLOSSARY.md`. Authority contract: skeptic R3.

---

## 1. What the role actually needs

ProjectIntegrator owns the test-launchers / activation contract. To do its job it must:

- Hold the role banner.
- Hold the activation sequence (conda / source activate / `PROJECT_ROOT`).
- Hold the environment-management rules.
- Hold the commands-folder structure + launcher creation patterns.
- Hold the review checklist.
- Hold the output format.
- Hold the interactions map.
- Hold the Rules.
- Receive constraints + environment.

## 2. What's currently in identity.md (categorized)

| Category | Lines | Content |
|---|---|---|
| **Role-defining authority** | L1-L13 | Role banner |
| **Role-defining authority** | L15-L34 | Activation sequence (`source activate`, `PROJECT_ROOT`) |
| **Role-defining authority** | L36-L77 | Environment management |
| **Role-defining authority** | L79-L130 | Commands-folder structure + launcher creation |
| **Role-defining authority** | L132-L141 | Review checklist |
| **Role-defining authority** | L143-L164 | Output format |
| **Cross-role coordination** | L166-L172 | Interactions |
| **claudechic-environment boilerplate** | L174-L184 | `## Communication` block |
| **Role-defining authority** | L186-L193 | Rules |

## 3. Load-bearing (R3) -- preserve verbatim

| Line | Quote |
|---|---|
| L117 | *"CRITICAL: Always verify the launcher works."* |
| L188 | *"Test launchers -- Don't assume they work; verify."* |
| L192 | *"Activation must work -- `source activate` is the entry point."* |

These three are the role's activation invariants.

## 4. Could move to environment segment

**L174-L184 (`## Communication` block)** -- identical boilerplate (`message_agent` patterns). Move to env segment.

**Important distinction:** L24-L34 activation sequence is **project-environment** specific (conda / `source activate` convention). The new env segment carries **claudechic-environment** facts (`CLAUDECHIC_ARTIFACT_DIR`, `WORKFLOW_ROOT`, MCP tools), NOT conda facts. **Do NOT move L24-L34 into the env segment.** Keep in identity.

## 5. Could move to constraints segment

None.

## 6. Could move to manifest YAML / shared reference

**Spawn condition:** `spawns_when:` manifest field candidate. Out of scope v1.

## 7. Per-phase needs

Specialist advisor; active per gating matrix `A**` in specification + implementation.

| phase | file (today) | role status | notes |
|---|---|---|---|
| specification | -- (gap) | active when spawned | v2 add |
| implementation | -- (gap) | active when spawned | v2 add |

## 8. Proposed identity.md edits

**v1 (this run):**

1. **Delete L174-L184** -- `## Communication` block. Replaced by env segment.

**Net change:** 193 -> ~181 lines. R3 statements (L117, L188, L192) untouched. Conda-environment content L15-L77 untouched.

## 9. Per-(time, place) cell map

| Time | identity | phase | constraints | environment |
|---|---|---|---|---|
| T1 spawn | fires | empty | fires | fires |
| T4 broadcast | suppress (#27) | empty | **fires (F1 floor)** | fires |
| T5 post-compact | re-fires | empty | re-fires | re-fires |

**Standing-by under v1 static predicate:** all phases.

## 10. Open questions

- **Phase-md adds:** **needs role-agent review during Implementation.**
- **conda content vs env segment:** clarified above. The two environments are distinct; do not conflate.

## 11. Review status

- **Self-review:** **needs role-agent review during Implementation.**

---

*Author: role-axis. Specification phase. Marked: needs role-agent review during Implementation.*
