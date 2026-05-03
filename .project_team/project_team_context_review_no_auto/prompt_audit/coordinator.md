# prompt_audit/coordinator.md

**Role:** `coordinator` (main agent / `main_role`).
**Source:** `claudechic/defaults/workflows/project_team/coordinator/identity.md` (61 lines) + 10 phase segments.
**Phase coverage:** vision, setup, leadership, specification, implementation, testing_vision, testing_specification, testing_implementation, signoff, documentation. Coordinator has a `<phase>.md` for **every** phase.

Glossary: `GLOSSARY.md`. Authority contract: skeptic R3.

---

## 1. What the role actually needs

The coordinator drives the workflow. To do its job it must:

- Know its delegate-not-do mandate (Prime Directive) and the user-interrupt handle (`x`).
- Hold the canonical Leadership-roster definition (other roles cite back to coordinator/identity.md:62).
- Hold the workflow-phase roadmap as informational orientation -- the **engine** is the source of truth, but the coordinator agent is the human-facing narrator.
- Have phase-specific operating instructions (each `<phase>.md`) for the active phase.
- Receive constraints reflecting the active phase + its `coordinator` role-scoping.
- Receive environment knowledge (claudechic-runtime facts, peer roster) at spawn / activation / post-compact.

## 2. What's currently in identity.md (categorized)

| Category | Lines | Content |
|---|---|---|
| **Role-defining authority** | L7-L31 | Prime Directive ("DELEGATE, NOT DO"); the "If user sends 'x'" interrupt contract |
| **Role-defining authority** | L51-L52 | Conflict resolution -- escalate to user |
| **Role-defining authority** | L56-L62 | Key terms -- canonical home for **Leadership** definition |
| **Workflow mechanics** | L34-L47 | Workflow phase roadmap (informational mirror of `project_team.yaml:4-67`) |
| **claudechic-environment boilerplate** | (none) | Coordinator identity has no `## Communication` block today |
| **Cross-role coordination** | L20-L24 | "You do NOT: Write code / Design interfaces / Write tests / Make architecture decisions alone" -- bounded authority |

## 3. Load-bearing (R3) -- preserve verbatim

| Line | Quote |
|---|---|
| L9 | *"YOUR JOB IS TO DELEGATE, NOT TO DO."* |
| L20-L24 | The "You do NOT" enumeration |
| L26-L31 | *"If user sends 'x': ... STOP immediately. Re-read this entire file. Re-read STATUS.md. Confirm you are following the workflow before continuing."* |
| L52 | *"If agents disagree, escalate to user."* |
| L61 | **Leadership** canonical-home definition |
| `leadership.md:3` | *"THIS IS NOT OPTIONAL. DO NOT SKIP."* |
| `signoff.md:7` | *"Respect explicit user instructions about workflow pace."* |

R3 statements are not revisable through the role-feedback mechanism without explicit user authorization.

## 4. Could move to environment segment

**Nothing today.** Coordinator identity has no comm boilerplate (already lean). However, the new environment segment (place-axis §3) should additionally inject for coordinator at T1/T2/T5: claudechic-runtime facts (workflow_id, peer roster, MCP introspection tools, comms patterns). These are content **added** to coordinator's launch prompt, not moved from identity.

## 5. Could move to constraints segment

`no_direct_code_coordinator` (`project_team.yaml:70-78`, warn-level rule) already targets coordinator's `Write` tool. The bounded-authority enumeration L20-L24 is its narrative complement -- keep both.

## 6. Could move to manifest YAML / informational mirror

**L34-L47 (phase roadmap).** Duplicates `project_team.yaml:4-67`. TerminologyGuardian's "One Home" review (Q7) flagged this.

**Recommendation:** keep the lines, prepend a one-line header marking informational status: *"Informational mirror of `project_team.yaml`. Source of truth is the engine."* Removing them harms human-readability of the identity file; keeping them silent risks divergence.

## 7. Per-phase needs

Coordinator is **active in every phase** (status: `A` in role-axis matrix). Never standing-by. Phase markdowns:

| phase | file | size | notes |
|---|---|---|---|
| vision | vision.md | tight | keep |
| setup | setup.md | tight | keep |
| leadership | leadership.md | short -- contains "THIS IS NOT OPTIONAL" R3 | keep |
| specification | specification.md | tight | keep |
| implementation | implementation.md | tight | keep |
| testing_vision | testing_vision.md | tight | keep |
| testing_specification | testing_specification.md | tight | keep |
| testing_implementation | testing_implementation.md | tight | keep |
| signoff | signoff.md | contains "respect user pace" R3 | keep |
| documentation | documentation.md | tight | keep |

## 8. Proposed identity.md edits

**v1 (this run):**

1. **Add header before L34:** *"Informational mirror of `project_team.yaml`. Source of truth is the workflow engine."*
2. **No deletes.** Authority statements untouched. No comm-block extraction (none exists).
3. **Inline the spec self-containment rule TEXT** directly into `coordinator/specification.md` AND `coordinator/testing_specification.md` (per user clarification 2026-05-02). NO new `conventions.md` file. NO indirection. NO edits to coordinator/identity.md. NO edits to other roles. The coordinator is the gatekeeper -- the rule is enforcement, not authoring guidance for sub-agents. Other roles do not need to see the rule.

**Rule text to paste verbatim into both phase files:**

```
## Spec self-containment

Spec-class documents (master SPEC.md and any axis spec that surfaces to the user at a Specification or Testing-Specification checkpoint) MUST be self-contained.

- Every term, code, abbreviation, or domain word used in a spec document MUST be defined inside that document.
- References to other files (axis specs, prior session artifacts, glossary files, failure-mode maps) are allowed as deeper-detail pointers, not as definitional sources.
- The user iterates on the spec document; other files are history.

Apply this when synthesizing master SPEC.md, when authoring an axis spec, and when reviewing a spec at any user checkpoint. The check applies to spec-class deliverables only -- not to chat updates, working notes, or audit files.

If a term must be referenced rather than defined inline, the spec document MUST include a one-line definition before the reference.
```

Implementation step: see `SPEC.md` build-plan step 10. Standing-by predicate handles non-spec phases automatically -- coordinator's `specification.md` and `testing_specification.md` only inject during their respective phases.

**Out of scope v1 (v2 candidate):**

- De-duplicate phase roadmap by replacing L34-L47 with an MCP-tool reference (`mcp__chic__get_phase` / `get_agent_info`). Requires confidence that the engine projection is bug-free for coordinator role. Defer.

## 9. Per-(time, place) cell map

| Time | identity | phase | constraints | environment |
|---|---|---|---|---|
| T1 spawn | n/a (coordinator is main agent, not spawned) | n/a | n/a | n/a |
| T2 activation | fires (full identity.md minus none-to-cut) | fires (current phase.md) | fires | fires (env opt-in: project_team yes) |
| T3 phase-advance.main | re-fires | fires (new phase.md) | fires | fires |
| T4 broadcast | n/a (coordinator is the broadcast caller, not recipient) | n/a | n/a | n/a |
| T5 post-compact | re-fires (full refresh) | re-fires | re-fires | re-fires |

**Standing-by:** never. Coordinator owns the workflow.

## 10. Open questions

- **Q7 (terminology):** keep informational mirror or migrate to MCP tool? **Recommended v1: keep with header.** v2: migrate.
- **Phase-segment thinness:** `documentation.md` is brief; if Documentation phase grows, may need expansion. **Out of scope v1.**

## 11. Review status

- **Leadership review of this audit:** coordinator is the recipient, not a Leadership lead. No agent-self-review owed.
- **Implementation:** implementer applies the L34 header in Implementation phase. R3 verbatim preservation verified by post-edit byte-compare.

---

*Author: role-axis. Specification phase.*
