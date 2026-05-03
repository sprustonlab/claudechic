# prompt_audit/skeptic.md

**Role:** `skeptic` (Leadership; complete > correct > simple).
**Source:** `skeptic/identity.md` (116 lines) + 5 phase segments (`specification.md` 10, `implementation.md` 8, `testing.md` 7, `testing-specification.md` 24, `testing-implementation.md` 27).
**Phase coverage:** active in specification, implementation, testing, testing-specification, testing-implementation. Standing-by elsewhere.

Glossary: `GLOSSARY.md`. Authority contract: skeptic R3 (skeptic owns this contract).

---

## 1. What the role actually needs

Skeptic is the falsifier-in-chief. To do its job it must:

- Hold the Four Questions (load-bearing falsification ladder).
- Hold The Principle (complete > correct > simple, in that order).
- Hold the explicit authority block (CAN demand / CAN push / CANNOT accept shortcuts / CANNOT cut features).
- Hold the shortcuts/complexity/verifiability/red-flags catalog.
- Receive phase-specific operating instructions for active phases (specification has the complexity-carryover check).
- Receive constraints scoped by phase + `skeptic` role.
- Receive environment knowledge for inter-agent communication.

## 2. What's currently in identity.md (categorized)

| Category | Lines | Content |
|---|---|---|
| **Role-defining authority** | L1-L6 | Role banner + "complete, correct, simple -- in that order" |
| **Role-defining authority** | L8-L31 | Insight; essential vs accidental complexity |
| **Role-defining authority** | L33-L37 | The Four Questions |
| **Role-defining authority** | L39-L82 | Shortcuts / complexity / verifiability / red flags catalog |
| **Role-defining authority** | L84-L88 | **Authority block** (CAN demand / CAN push / CANNOT accept shortcuts / CANNOT cut features) |
| **Role-defining authority** | L90-L96 | Output format |
| **Role-defining authority** | L98-L104 | The Principle (complete > correct > simple) |
| **claudechic-environment boilerplate** | L106-L116 | `## Communication` block (`message_agent`) |

## 3. Load-bearing (R3) -- preserve verbatim

Per skeptic lead's Q1 reply, refined:

| Line | Quote / range | Note |
|---|---|---|
| L1-L6 | Role banner + "complete, correct, simple -- in that order" | -- |
| L33-L37 | The Four Questions | -- |
| **L66-L82** | **Red-flags list (named rejection criteria)** | **Added per skeptic lead's Q1 reply: each entry ("Works for the common case", "We can add that later", "X is too hard, let's do Y") is a named rejection criterion the role is bound to apply. If trimmed or paraphrased, a future instance can accept shortcuts that are explicitly blacklisted here.** |
| L84-L88 | **Authority block** -- CAN demand / CAN push / CANNOT accept shortcuts / **CANNOT cut features from userprompt.md** | -- |
| L98-L104 | The Principle | -- |

R3 statements are not revisable through the role-feedback mechanism without explicit user authorization. **L88 ("CANNOT cut features from userprompt.md") is the joint Skeptic + UserAlignment override invariant -- non-revisable.**

**Refined R3 range:** L66-L82 elevated from "general body" to load-bearing-verbatim per lead's review. This is a **correction to the draft audit**, not a rephrase.

## 4. Could move to environment segment

Per skeptic lead's Q4 reply, **refined to a SPLIT, not a wholesale move:**

A. **Tool semantics (L106-L112)** -- *"Use message_agent as your default. It guarantees a response..."* and *"Use message_agent with requires_answer=false for reporting results..."* -- these are pure **platform facts** (what the tools do, their semantics). Belongs in env segment.

B. **Behavioral guidance (L113-L116)** -- the *"When to communicate:"* bullet list -- *"After completing your task / After encountering blockers / When you need a decision / When delegating a task"* -- this is **phase-dependent**. Per skeptic lead's example: behavior differs between specification review (awaiting coordinator response, `requires_answer=true`) and testing-vision (fire-and-forget memo, `requires_answer=false`). Wholesale-moving to env would flatten the per-phase variability.

**Refined move-target:**
- L106-L112 (~7 lines, tool semantics) -> environment segment.
- L113-L116 (~4 lines, when-to-communicate guidance) -> split across `skeptic/specification.md`, `skeptic/implementation.md`, `skeptic/testing*.md` per phase-specific behavior. Each phase file authored as part of v1 implementation.

**Net deletion from identity.md:** ~11 lines total (same total as draft), but split between env (platform fact) and phase mds (role-and-phase-specific behavior). Cleaner seam.

**Cross-role implication (flagged for master spec):** the same `## Communication` block appears in 14 identity files. The split-pattern proposed here applies across the team -- comm tool semantics are workflow-agnostic platform facts; comm behavior is per-(role, phase). Master spec §5 updated to capture this.

## 5. Could move to constraints segment

None. Skeptic identity has no rule-prose duplicates of guardrail rules.

## 6. Could move to manifest YAML / shared reference

None. The Leadership roster reference is implicit (L8 "complexity is the enemy" framing); skeptic doesn't list peers in identity.

## 7. Per-phase needs

| phase | file | role status | contents | notes |
|---|---|---|---|---|
| vision | -- | standing-by | (no phase.md) | suppress identity at T3/T4 |
| setup | -- | standing-by | -- | as above |
| leadership | -- | standing-by | -- | as above |
| specification | specification.md (10) | active | includes complexity-carryover check (load-bearing) | keep |
| implementation | implementation.md (8) | active | tight | keep |
| testing | testing.md (7) | active | tight | keep |
| testing-vision | -- | standing-by | -- | as above |
| testing-specification | testing-specification.md (24) | active | substantive | keep |
| testing-implementation | testing-implementation.md (27) | active | substantive | keep |
| documentation | -- | standing-by | -- | as above |
| signoff | -- | standing-by | -- | as above |

## 8. Proposed identity.md edits

**v1 (this run):**

1. **Delete L106-L112** -- tool-semantics half of the `## Communication` block. Replaced by env segment (platform fact).
2. **Migrate L113-L116** -- *"When to communicate:"* behavioral guidance -- to per-phase markdown for skeptic. Each phase file (specification.md, implementation.md, testing.md, testing-specification.md, testing-implementation.md) gets a 1-2-line entry calibrated to the phase's actual communication pattern (per skeptic lead's Q4 example: spec = await coordinator response; testing-vision = fire-and-forget memo).

**Net change:** identity.md goes from 116 lines to 105 lines. R3 statements (L1-L6, L33-L37, **L66-L82**, L84-L88, L98-L104) untouched and byte-identical pre/post edit. **L66-L82 added to the verbatim-preserve range per lead's Q1 reply.**

## 9. Per-(time, place) cell map

| Time | identity | phase | constraints | environment |
|---|---|---|---|---|
| T1 spawn | fires (105 lines post-edit) | fires (when active) | fires | fires |
| T2 activation | n/a | n/a | n/a | n/a |
| T3 phase-advance.main | n/a | n/a | n/a | n/a |
| T4 broadcast (active phase) | suppress (#27 default) | fires | **fires (F1 floor)** | fires |
| T4 broadcast (standing-by phase) | suppress | empty (renderer-empty) | **fires (F1 floor)** | fires |
| T5 post-compact | re-fires | re-fires | re-fires | re-fires |

**Standing-by:** in phases without `<phase>.md`. Issue #27 fires here.

## 10. Open questions

- **Q1 (for skeptic lead):** R3 ranges -- anything missed? **Asked.**
- **Q2 (A3 from leadership_findings):** is **role** alone the right partition key, or do we need (role + cwd + parent + agent_type)? My take: role alone; cwd is captured by `${CLAUDECHIC_ARTIFACT_DIR}` substitution; parent/spawner is workflow_id + main_role; agent_type IS role. **Asked for skeptic concur/push.**
- **Q3 (for skeptic lead):** F8/F9 disposition with current post-slot-3 fix + place-axis empty-bytes contract -- anything weakened? **Asked.**
- **Q4 (for skeptic lead):** is the env-segment the right home for comm boilerplate, or should it be a separate "communication" segment? **Asked.**

## 11. Review status

- **Self-review (Q1-Q4):** message sent to `skeptic` agent during Spec phase. Reply integrated below when received.
- **Implementer transient confirmation:** during Implementation, implementer spawns skeptic with this audit + proposed diff; agent confirms R3 statements byte-identical. Edit applied.

### Skeptic lead's reply

**Received. Verdict: confirmed with one R3 expansion + one move-pattern refinement.** Lead's reply integrated into §3, §4, §8 above.

Summary of lead's reply:
- **Q1 R3:** **Red-flags list L66-L82 elevated to R3.** Each entry ("Works for the common case", "We can add that later", "X is too hard, let's do Y") is a named rejection criterion the role is bound to apply. Trimming or paraphrasing would let a future instance accept blacklisted shortcuts. **Correction integrated into §3.**
- **Q2 partition key (A3 closure):** **Concur** with role-alone partition. Clarification: A3 was about RUNTIME CONTEXT (cwd varies per sub-agent). As a CONTENT-SELECTION key (which identity/phase markdown to read), role is correct -- cwd is substituted post-selection; parent/spawner collapses to workflow_id+main_role; agent_type IS role for typed agents. **For default-roled agents (F8), there is no selection to make -- handled by separate F8 closure rather than partition refinement.** spec_role_axis.md §1 reasoning vindicated.
- **Q3 F8/F9 + empty-bytes:** **Mostly sound; precision required.** "Empty-bytes contract" MUST mean **skip injection if empty, not inject empty.** F9 was 138-char placeholder noise. If the per-segment contract is "each segment signals absent vs present" (compose drops empties), strict improvement. If it means "always inject, possibly empty," F9 returns at finer granularity. **Confirm:** place-axis §6 says *"empty-as-skip (`\"\"` is the gating signal; composer drops the separator; F9 fix)"* -- skip-on-empty. **No regression**; lead's precision check passes.
- **Q4 comm boilerplate:** **Partial concur -- SPLIT, not wholesale move.** Tool semantics (L106-L112) -> env segment (platform facts). When-to-communicate bullets (L113-L116) -> per-phase markdown (phase-dependent behavior; spec example: spec.md await-coordinator vs testing.md fire-and-forget). **Refined move-target integrated into §4 and §8.**

Skeptic lead: ready for Specification, with R3 catalog correction noted.

---

*Author: role-axis. Specification phase.*
