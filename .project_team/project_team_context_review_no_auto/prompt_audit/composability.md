# prompt_audit/composability.md

**Role:** `composability` (Leadership; Lead Architect).
**Source:** `composability/identity.md` (523 lines) + 4 phase segments (`specification.md` 9 lines, `implementation.md` 8, `testing-specification.md` 24, `testing-implementation.md` 26).
**Phase coverage gaps:** none for active phases. Standing-by by absence in: vision, setup, leadership, signoff, documentation, testing-vision.

Glossary: `GLOSSARY.md`. Authority contract: skeptic R3.

---

## 1. What the role actually needs

Composability is the architecture authority on Crystal / Seam / Algebraic decomposition. To do its job it must:

- Hold the Crystal/Seam/Algebraic vocabulary (load-bearing methodology).
- Hold the file-structure principles + composability smells tables.
- Hold the reporting format (other agents expect this shape; downstream prompts reference it).
- Receive phase-specific operating instructions for active phases.
- Receive constraints scoped by phase + `composability` role.
- Receive environment knowledge for inter-agent communication and runtime facts.

## 2. What's currently in identity.md (categorized)

| Category | Lines | Content |
|---|---|---|
| **Role-defining authority** | L1-L11 | Role banner, "Lead Architect", Leadership reference, "first task" |
| **Role-defining authority** | L13-L26 | WHY: the monolithic-tools framing |
| **Role-defining authority** | L29-L249 | Crystal / Seam / Algebraic vocabulary (~220 lines, the methodology body) |
| **Role-defining authority** | L251-L304 | File-structure principles |
| **Role-defining authority** | L306-L378 | HOW: implementation patterns |
| **Role-defining authority** | L381-L422 | Composability smells tables |
| **Role-defining authority** | L424-L470 | Advisory questions checklist |
| **Role-defining authority** | L474-L506 | Reporting format (the agreed shape) |
| **Cross-role coordination** | L7-L9 | Leadership team reference (Composability + Terminology + Skeptic + UserAlignment) |
| **claudechic-environment boilerplate** | L513-L523 | `message_agent` / `requires_answer` "When to communicate" block |

## 3. Load-bearing (R3) -- preserve verbatim

Per composability lead's reply, refined:

| Line | Quote / range | Authority level |
|---|---|---|
| L3 | *"Role: Lead Architect"* | R3 |
| L5 | *"You ensure clean separation of concerns through algebraic composition principles."* | R3 |
| L29-L249 | Crystal / Seam / Algebraic methodology body (the **conceptual** authority) -- 10-point test, swap test, law test, concrete examples | R3 |
| L251-L304 | File-structure principles | R3 |
| L474-L506 | Reporting format (the shape downstream agents expect; coordinator consumed in Leadership without friction; **R3-protect per lead's Q2 reply**) | R3 |

The methodology body L29-L249 is the **conceptual** authority -- the *what* of the role. **Composability lead's Q1 reply distinguishes:** L306-L378 (HOW patterns) and L381-L422 (smells tables) are *reference material* (how to apply), not conceptual authority. These are R3-relaxable: candidates for shared `composability_methodology.md` injected via environment segment only at specification + implementation phases (not at spawn). Saves ~90 lines from spawn payload. See §4 below.

## 4. Could move to environment segment

**v1 (this run):**

A. **L513-L523 (`## Communication` block)** -- identical boilerplate appears in 14 of 15 identity.md files (not coordinator). Pure platform fact about MCP communication tools. Belongs in the new environment segment.
   - Move-target: lines 513-523 (11 lines).

**v1 candidate -- composability lead's Q3 reply names two missing env-segment contents:**

B. **Agent name routing table** (`{role -> registered_name}`) -- composability lead's actual session failure: messaged `coordinator` but registered name was `claudechic`. Dynamic (varies per run) -> correct home is environment segment. **Confirmed with gating_axis (per its §1a default-cell table): env fires at T1/T2/T5 for all opted-in workflows.** Project_team opts in for v1.

C. **Peer roster with 2-sentence-per-peer summaries.** Identity L7 names Leadership peers but gives no descriptions; lead currently cannot infer peer output shape without reading their identities. A short roster in env segment removes the dependency. Dynamic (varies by workflow) -> correct home is environment segment.

**v2 follow-up (composability lead's Q4 reply):**

D. **Generalprobe Standard block.** ~14 lines duplicated verbatim in `testing-specification.md` and `testing-implementation.md`. Seam smell. Move to a shared env-segment injection fired at all testing phases; slim each phase file to role-specific checklist. Saves ~28 lines (14 per file) and gives the testing standard a single canonical home.

**v2 candidate (composability lead's Q1 reply):**

E. **Reference-material methodology** -- L306-L378 (HOW patterns) + L381-L422 (smells tables). Move to a shared `composability_methodology.md` injected via env segment only at specification + implementation phases (not at spawn). Saves ~90 lines from spawn payload. Identity retains a one-liner pointer.

**Move-targets summary:**
- v1: 11 lines (A) + 2 added env contents (B, C, sourced from new env bundle).
- v2: ~28 lines (D, hoist Generalprobe) + ~90 lines (E, hoist reference methodology).

## 5. Could move to constraints segment

None. Composability identity has no rule-prose duplicates of guardrail rules. Composability does not author its own guardrails.

## 6. Could move to manifest YAML / shared reference

**L7 (Leadership roster line):** "You are part of the Leadership team together with TerminologyGuardian, Skeptic, and UserAlignment." Replace with: *"See `coordinator/identity.md:62` for the Leadership roster."* (TerminologyGuardian "One Home" rule.)

## 7. Per-phase needs

| phase | file | role status | contents | notes |
|---|---|---|---|---|
| vision | -- | standing-by | (no phase.md) | suppress identity at T3/T4 per #27 |
| setup | -- | standing-by | -- | as above |
| leadership | -- | standing-by | -- | as above |
| specification | specification.md (9 lines) | active | tight ops steps | keep |
| implementation | implementation.md (8) | active | tight | keep |
| testing-vision | -- | standing-by | -- | as above |
| testing-specification | testing-specification.md (24) | active | substantive | keep |
| testing-implementation | testing-implementation.md (26) | active | substantive | keep |
| documentation | -- | standing-by | -- | as above |
| signoff | -- | standing-by | -- | as above |

## 8. Proposed identity.md edits

**v1 (this run):**

1. **Replace L7** -- the Leadership roster line -- with: *"You are part of the Leadership team. See `coordinator/identity.md:62` for the canonical roster. Per-peer summaries delivered via environment segment."*
2. **Delete L513-L523** -- the `## Communication` block. Replaced by the new `environment segment` (place-axis §3).
3. **Add to env-segment bundle** (place-axis owns `claudechic/defaults/environment/*.md`): the agent name routing table + peer roster with 2-sentence-per-peer summaries (composability lead's Q3 reply). These are **content adds**, not deletions from identity.

**Net change to identity.md:** 523 lines -> ~511 lines. R3 statements (L3, L5, L29-L249, L251-L304, L474-L506) untouched and byte-identical pre/post edit.

**Out of scope v1 (v2 follow-up per composability lead's Q1, Q4):**

4. Hoist L306-L378 (HOW patterns) + L381-L422 (smells tables) to `composability_methodology.md` injected via env segment only at specification + implementation phases. Saves ~90 lines from spawn payload.
5. Hoist Generalprobe Standard duplicate from `testing-specification.md` + `testing-implementation.md` to shared env-segment injection for testing phases. Saves ~28 lines, single canonical home.

## 9. Per-(time, place) cell map

| Time | identity | phase | constraints | environment |
|---|---|---|---|---|
| T1 spawn | fires (511 lines, post-edit) | fires (when active) | fires | fires (env opt-in: project_team yes) |
| T2 activation | n/a (composability is sub-agent) | n/a | n/a | n/a |
| T3 phase-advance.main | n/a | n/a | n/a | n/a |
| T4 broadcast (active phase) | suppress (already at spawn; #27 default) | fires (current phase.md) | **fires (F1 floor)** | fires |
| T4 broadcast (standing-by phase) | suppress | empty (renderer-empty; no phase.md) | **fires (F1 floor)** | fires |
| T5 post-compact | re-fires (full refresh) | re-fires | re-fires | re-fires |

**Standing-by:** in phases without `<phase>.md` (vision, setup, leadership, testing-vision, signoff, documentation). Issue #27 fires here: identity suppressed at T3/T4; constraints always fires (F1 floor); phase renderer returns empty.

## 10. Open questions

- **Q1 (for composability lead):** Are there sub-sections of L29-L249 that could move to a shared `composability_methodology.md` referenced from identity, vs staying in the identity segment? **Asked; awaiting reply.**
- **Q2 (for composability lead):** Is L474-L506 reporting format treated as authority (R3) or convention? **Asked.**
- **Q3 (for composability lead):** Content currently MISSING from identity that should land in the new env segment (peer roster, dynamic team-dynamics framing)? **Asked.**

## 11. Review status

- **Self-review (Q1-Q4):** message sent to `composability` agent during Spec phase. Reply integrated below when received.
- **Implementer transient confirmation:** during Implementation, implementer spawns composability with this audit + proposed diff; agent confirms R3 statements byte-identical. Edit applied.

### Composability lead's reply

**Received. Verdict: confirmed with substantive additions.** Lead's reply integrated into §3, §4, §8 above.

Summary of lead's reply:
- **Structure + standing-by list: CONFIRM.** Active = specification, implementation, testing-specification, testing-implementation. Standing-by = vision, setup, leadership, signoff, documentation, testing-vision.
- **Q1 (R3 scope of L29-L249):** Crystal/Seam/Algebraic conceptual body L29-L249 is load-bearing R3 and stays in identity. **However**, L306-L378 (HOW patterns) + L381-L422 (smells tables) are reference material (how to apply), not conceptual authority. Candidates for env-segment injection only at specification + implementation phases. Saves ~90 lines from spawn payload. **v2 follow-up.**
- **Q2 (L474-L506 reporting format):** R3-protect. Lead used this format in Leadership; coordinator consumed without friction; other roles reference its shape. **R3 catalog updated in §3.**
- **Q3 (missing env content):** TWO concrete env-segment additions named:
  1. **Agent name routing table** `{role -> registered_name}` -- lead's session failure: messaged `coordinator` but real name was `claudechic`. Dynamic per run. Add to env segment bundle.
  2. **Peer roster** with 2-sentence-per-peer summaries. Identity L7 names peers but gives no descriptions. Add to env segment bundle.
  Confirmed with gating_axis: env fires at T1/T2/T5 for all opted-in workflows.
- **Q4 (phase file thickness):**
  - `specification.md` (9 lines), `implementation.md` (8 lines): thin but sufficient. Keep.
  - `testing-specification.md` + `testing-implementation.md`: ~14 lines of *Generalprobe Standard* duplicated verbatim. **Seam smell.** v2: hoist to shared env-segment injection for testing phases. Saves ~28 lines, single canonical home.

Composability lead: ready for Specification.

---

*Author: role-axis. Specification phase.*
