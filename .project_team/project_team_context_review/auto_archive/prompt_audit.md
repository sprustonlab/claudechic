# prompt_audit.md

Per-role audit of bundled prompt content for the 15 project_team roles +
`default`. Authored by role-axis (Specification phase) by reading the
identity.md and phase markdown files under
`claudechic/defaults/workflows/project_team/<role>/`.

For each role: what the identity file says today, redundancies with
constraints / environment / phase segments, load-bearing authority
statements that MUST be preserved verbatim (R3), proposed concrete
revisions, and the per-injection-site map.

Glossary terms per `specification/terminology.md`. Authority-preservation
contract per `specification/skeptic_review.md` R3.

---

## Phase-markdown additions (gating_axis reconciliation)

Per coordination with gating_axis: each entry below removes a `gating:
{ suppress: ... }` matrix cell because the role gains substantive
content for that phase. place_axis owns the YAML edit; this list is
the source.

**v1 additions (in scope this run):**

| role | phase | new file | reason |
|---|---|---|---|
| test_engineer | testing-specification | `test_engineer/testing-specification.md` | role active (per §7 of this audit); current absence misclassifies as standing-by |
| test_engineer | testing-implementation | `test_engineer/testing-implementation.md` | same |
| ui_designer | specification | `ui_designer/specification.md` | coordinator's `specification.md:2` says spawn UIDesigner if UI-heavy; UIDesigner needs phase prompt |
| ui_designer | implementation | `ui_designer/implementation.md` | role active during impl |

**v1 open question:**

| role | phase | new file | reason |
|---|---|---|---|
| user_alignment | implementation | `user_alignment/implementation.md` | unclear whether UserAlignment is genuinely active during impl or simply standing-by; coord. with gating_axis for decision |

**v2 follow-up (out of scope this run; matrix unchanged for v1):**

- researcher: vision.md, specification.md, implementation.md,
  testing-specification.md, testing-implementation.md (researcher
  active across most phases per its own L20-L33 activity table).
- lab_notebook: implementation.md, testing-implementation.md
  (when the project is experiment-shaped).
- memory_layout, sync_coordinator, binary_portability,
  project_integrator: specification.md, implementation.md (when
  spawned per their conditional triggers).

**Reverse direction (phase.md exists today but role is "really
standing-by" -- add a suppress entry even though the file exists):**

None identified. The current `<phase>.md` files for composability,
skeptic, user_alignment, terminology, implementer all carry
substantive operational content for the phases they cover. The static
definition (no phase.md = standing-by) is correct as the v1 predicate.

---

## Table of contents

1. coordinator
2. composability
3. skeptic
4. user_alignment
5. terminology
6. implementer
7. test_engineer
8. ui_designer
9. researcher
10. lab_notebook
11. memory_layout
12. sync_coordinator
13. binary_portability
14. project_integrator
15. default (catch-all `agent_type`; not a folder)

---

## 1. coordinator

**Source:** `coordinator/identity.md` (61 lines) + 10 phase segments
(`vision.md`, `setup.md`, `leadership.md`, `specification.md`,
`implementation.md`, `testing_vision.md`, `testing_specification.md`,
`testing_implementation.md`, `signoff.md`, `documentation.md`).

### Identity content

- L7-L31 -- Prime Directive ("DELEGATE, NOT DO") + the "If user sends 'x'"
  contract. Authority-bearing.
- L34-L47 -- Workflow phase roadmap (informational mirror of
  `project_team.yaml:4-67`).
- L51-L52 -- Conflict resolution (escalate to user).
- L56-L62 -- Key terms (User Checkpoint; **Leadership** = the 4-agent set).

### Redundancy / overlap

- L34-L47 phase list duplicates the engine's source of truth in
  `project_team.yaml`. Per terminology.md §5 / Q7 this is the
  canonical-home violation flagged by TerminologyGuardian.
- L56-L62 "Leadership" definition is the canonical home (terminology.md
  §1.5 / §5). Composability and TerminologyGuardian identity files
  reference it -- preserve here.

### R3 authority statements (preserve verbatim)

- L9 -- *"YOUR JOB IS TO DELEGATE, NOT TO DO."*
- L20-L24 -- *"You do NOT: Write code / Design interfaces / Write tests
  / Make architecture decisions alone"*
- L26-L31 -- *"If user sends 'x': ... STOP immediately. Re-read this
  entire file. Re-read STATUS.md. Confirm you are following the workflow
  before continuing."* -- the user's interrupt-handle.
- L52 -- *"If agents disagree, escalate to user."*
- L61 -- **Leadership** canonical-home definition.
- `leadership.md:3` -- *"THIS IS NOT OPTIONAL. DO NOT SKIP."*
- `signoff.md:7` -- *"Respect explicit user instructions about workflow
  pace."*

### Proposed revisions

- **Keep in identity:** L1-L31, L51-L52, L56-L62.
- **Move to environment segment:** none (coordinator is workflow-bound).
- **Mark as informational mirror:** L34-L47 phase list. Header:
  *"Informational mirror of `project_team.yaml`. Source of truth is the
  engine."*
- **No moves to manifest YAML.**

### Phase segments

- All 10 are short and operational. No changes recommended.
- `leadership.md`'s "THIS IS NOT OPTIONAL" line is authority -- preserve.
- `signoff.md:7` ("Respect explicit user instructions about workflow
  pace") is authority -- preserve.

### Injection-site map

| Site | Identity today | Phase today | Proposed identity | Proposed phase |
|---|---|---|---|---|
| 1 main-agent activation | fires | `vision.md` fires | fires | fires |
| 2 sub-agent spawn | n/a | n/a | n/a | n/a |
| 3 main-agent phase-advance | re-fires | new phase fires | fires | fires |
| 4 phase-advance broadcast | n/a | n/a | n/a | n/a |
| 5 post-compact | re-fires | re-fires | re-fires | re-fires |

Coordinator never standing-by. Suppression never applies.

---

## 2. composability

**Source:** `composability/identity.md` (523 lines), `specification.md`
(9), `implementation.md` (8), `testing-specification.md` (24),
`testing-implementation.md` (26).

### Identity content

- L1-L11 -- role banner, Leadership reference, "first task."
- L13-L26 -- WHY: monolithic-tools framing.
- L29-L249 -- Vocabulary: Crystal / Seam / Algebraic (~220 lines).
- L251-L304 -- File-structure principles.
- L306-L378 -- HOW: implementation patterns.
- L381-L422 -- Composability smells tables.
- L424-L470 -- Advisory questions.
- L474-L506 -- Reporting format.
- L513-L523 -- Communication boilerplate.

### Redundancy / overlap

- L513-L523 communication block is identical boilerplate in 14 of 15
  identity files. Move to environment segment.
- L7-L9 *"You are part of the Leadership team together with..."*
  duplicates `coordinator/identity.md:61`. Replace with: *"See
  coordinator/identity.md for the Leadership roster."*
- L429-L433 (Domain First) overlaps with `specification.md` step #1.
  Phase segment is the home for "what to do this phase"; identity is
  for "who you are."

### R3 authority statements

- L3 -- *"Role: Lead Architect."*
- L5 -- *"You ensure clean separation of concerns through algebraic
  composition principles."*
- L29-L249 -- Crystal / Seam / Algebraic methodology. The body of this
  vocabulary is the load-bearing material; preserve in full.
- L474-L506 -- reporting format (other agents expect this shape).

### Proposed revisions

- **Keep:** L1-L11, L13-L470.
- **Move to environment segment:** L513-L523.
- **Move to manifest YAML / shared snippet:** L7 Leadership roster line
  -> single-line reference to coordinator's canonical home.

### Phase segments

`specification.md` (9 ops steps), `implementation.md` (8),
`testing-*.md` (24/26) are tight. Keep.

### Injection-site map

| Site | Identity today | Phase today | Proposed identity | Proposed phase |
|---|---|---|---|---|
| 2 spawn | fires (full identity) | fires | fires (minus comm boilerplate) | fires |
| 4 broadcast | re-fires | new phase fires | suppress (had at spawn) | fires |
| 5 post-compact | re-fires | re-fires | re-fires | re-fires |

### Standing-by

Active in: specification, implementation, testing-specification,
testing-implementation. Standing-by in: vision, setup, leadership,
signoff, documentation, testing-vision.

---

## 3. skeptic

**Source:** `skeptic/identity.md` (116), `specification.md` (10),
`implementation.md` (8), `testing.md` (7), `testing-specification.md`
(24), `testing-implementation.md` (27).

### Identity content

- L1-L6 -- role banner + "complete, correct, simple -- in that order."
- L8-L31 -- insight; essential vs accidental complexity.
- L33-L37 -- Four Questions.
- L39-L82 -- shortcuts / complexity / verifiability / red flags.
- L84-L88 -- **authority block.**
- L90-L104 -- output format + The Principle.
- L106-L116 -- communication boilerplate.

### Redundancy / overlap

- L106-L116 -- comm boilerplate (extract to environment).
- The Four Questions (L33-L37) are referenced by `skeptic_review.md`'s
  Q1-Q6 falsification labels. Preserve.

### R3 authority statements

- L84-L88 authority block (CAN demand / CAN push / CANNOT accept
  shortcuts / **CANNOT cut features from userprompt.md**).
- L98-L104 -- The Principle (complete > correct > simple ordering).
- L34 -- The Four Questions.

### Proposed revisions

- **Keep:** L1-L104.
- **Move to environment segment:** L106-L116.
- **Move to manifest YAML:** none.

### Phase segments

`specification.md` (10) -- includes the "complexity carryover" check
which is real load-bearing. Keep. Other phase mds are short, operational.

### Injection-site map

| Site | Identity today | Phase today | Proposed identity | Proposed phase |
|---|---|---|---|---|
| 2 spawn | fires | fires | fires | fires |
| 4 broadcast | re-fires | new phase fires | suppress | fires |
| 5 post-compact | re-fires | re-fires | re-fires | re-fires |

### Standing-by

Active: specification, implementation, testing, testing-specification,
testing-implementation. Standing-by: vision, setup, leadership, signoff,
documentation, testing-vision.

---

## 4. user_alignment

**Source:** `user_alignment/identity.md` (156), `specification.md` (9),
`testing-specification.md` (25), `testing-implementation.md` (26).

### Identity content

- L1-L13 -- role banner; four-step process at start.
- L20-L35 -- process at start + during development.
- L36-L67 -- misalignment templates (5).
- L69-L83 -- interaction with Skeptic (override matrix).
- L85-L104 -- output format.
- L106-L116 -- communication boilerplate.
- L118-L127 -- Rules.
- L128-L156 -- examples.

### Redundancy / overlap

- L106-L116 -- comm boilerplate (extract to environment).
- L73 ("WHAT vs HOW") paraphrases L124 Rules #5 *"Stay in your lane"*
  and skeptic L88 *"You CANNOT cut features..."*. Cross-references are
  healthy; not duplication.

### R3 authority statements

- L11 -- *"You are the guardian of user intent."*
- L78 -- *"Skeptic may NOT advise removing user-requested features."*
- L80-L82 -- *"If X is in the prompt -> Override Skeptic, X must stay.
  If X is not in the prompt -> Skeptic's advice is valid."*
- L120 -- *"userprompt.md is the source of truth -- Not your
  interpretation."*
- L121 -- *"Quote the user -- Use exact text from userprompt.md."*
- L123 -- *"Protect user intent -- You're their advocate."*

### Proposed revisions

- **Keep:** L1-L104, L118-L156.
- **Move to environment segment:** L106-L116.

### Phase segments

`specification.md` (9) -- includes the "is wording changed" check
(step 4). Valuable.
`testing-*.md` -- keep.
**Gap:** no `implementation.md`. UserAlignment may need one --
*open question*; coordinate with gating_axis.

### Injection-site map

| Site | Identity today | Phase today | Proposed identity | Proposed phase |
|---|---|---|---|---|
| 2 spawn | fires | fires | fires | fires |
| 4 broadcast | re-fires | new phase fires | suppress | fires (or empty if standing-by) |
| 5 post-compact | re-fires | re-fires | re-fires | re-fires |

### Standing-by

Active: specification, testing-specification, testing-implementation.
Standing-by: vision, setup, leadership, implementation, signoff,
documentation, testing-vision.

---

## 5. terminology

**Source:** `terminology/identity.md` (100), `specification.md` (9),
`testing-specification.md` (23), `testing-implementation.md` (26).

### Identity content

- L1-L12 -- role banner; "assistant to Composability."
- L14-L29 -- core principle; smells table.
- L32-L40 -- "One Home" + review questions.
- L42-L48 -- newcomer simulation.
- L50-L73 -- output format.
- L75-L80 -- interaction (escalation contract).
- L82-L92 -- communication boilerplate.
- L94-L100 -- Rules.

### R3 authority statements

- L8 -- *"You are the assistant to Composability."*
- L80 -- *"Escalate naming conflicts to Composability for decision."*
- L100 Rules #5 -- *"Assist, don't override -- Composability has final
  say on architecture."*

### Proposed revisions

- **Keep:** L1-L80, L94-L100.
- **Move to environment segment:** L82-L92.

### Injection-site map

| Site | Identity today | Phase today | Proposed identity | Proposed phase |
|---|---|---|---|---|
| 2 spawn | fires | fires | fires | fires |
| 4 broadcast | re-fires | new phase fires | suppress | fires |
| 5 post-compact | re-fires | re-fires | re-fires | re-fires |

### Standing-by

Active: specification, testing-specification, testing-implementation.
Standing-by: vision, setup, leadership, implementation, signoff,
documentation, testing-vision.

---

## 6. implementer

**Source:** `implementer/identity.md` (109), `implementation.md` (10),
`testing.md` (10).

### Identity content

- L1-L20 -- role banner; faithful-implementation principle; workflow.
- L29-L46 -- code-style; error-handling; dependencies.
- L47-L65 -- output format.
- L67-L88 -- interactions; handoffs.
- L90-L100 -- communication boilerplate.
- L102-L109 -- Rules.

### Redundancy / overlap

- L90-L100 -- comm boilerplate (extract to environment).
- L67-L77 (interaction table) is informational coordination map. Keep.
- L109 Rule #6 *"Run targeted tests only ... Never run the full suite
  during active development"* duplicates `global:no_bare_pytest` deny
  rule. Move to manifest YAML / constraints reference.

### R3 authority statements

- L1-L3 -- *"You write the actual code based on the architecture and
  design decisions."*
- L102 -- *"Implement what's specified -- Don't add unrequested
  features."*
- L103 -- *"Follow the architecture -- Don't violate axis separation."*
- L107 -- *"Ask when unclear -- Better to clarify than assume."*

### Proposed revisions

- **Keep:** L1-L88, L102-L108.
- **Move to environment segment:** L90-L100.
- **Move to constraints reference:** L109. Replace with: *"Test-execution
  policy: see Constraints segment."*

### Injection-site map

| Site | Identity today | Phase today | Proposed identity | Proposed phase |
|---|---|---|---|---|
| 2 spawn | fires | fires | fires (minus comm boilerplate) | fires |
| 4 broadcast | re-fires | new phase fires | suppress | fires |
| 5 post-compact | re-fires | re-fires | re-fires | re-fires |

### Standing-by

Active: implementation, testing. Standing-by: any phase outside those
two if the agent persists; typically closed at end of testing.

---

## 7. test_engineer

**Source:** `test_engineer/identity.md` (102). **No phase markdown.**

### Identity content

- L1-L13 -- role banner.
- L15-L21 -- "first step: read the testing standard."
- L23-L31 -- default testing principles.
- L33-L60 -- testing strategy + output format.
- L62-L73 -- tooling.
- L75-L82 -- interactions.
- L84-L93 -- communication boilerplate.
- L95-L102 -- Rules.

### Redundancy / overlap

- L84-L93 -- comm boilerplate (extract to environment).
- L101-L102 Rule #6 (pytest policy) -- duplicates
  `global:no_bare_pytest` and `global:pytest_needs_timeout`. Move to
  manifest YAML / constraints reference.

### R3 authority statements

- L25 -- *"No mocking -- tests run against real infrastructure."*
- L26 -- *"No skipping ... Do not use pytest.skip(), xfail, or
  importorskip."*
- L27 -- *"Public API only ... opaque handles."*
- L29 -- *"Real infrastructure -- A test is a production run with
  assertions."*
- L100 -- *"Don't test mocks -- Test real behavior."*

These five together = the team's testing contract (the "Generalprobe
standard" referenced by `coordinator/testing_vision.md`). Skeptic and
UserAlignment lean on them.

### Proposed revisions

- **Keep:** L1-L82, L95-L100.
- **Move to environment segment:** L84-L93.
- **Move to constraints reference:** L101-L102.
- **Phase markdown gap:** add `testing-specification.md` and
  `testing-implementation.md`.

### Injection-site map

| Site | Identity today | Phase today | Proposed identity | Proposed phase |
|---|---|---|---|---|
| 2 spawn | fires | n/a | fires | fires (after adding phase mds) |
| 4 broadcast | re-fires | n/a | suppress | fires (or empty) |
| 5 post-compact | re-fires | n/a | re-fires | re-fires |

### Standing-by

Currently no phase mds -> always standing-by under static definition
(wrong; active in testing phases). Add phase segments to fix.

---

## 8. ui_designer

**Source:** `ui_designer/identity.md` (143). **No phase markdown.**

### Identity content

- L1-L5 -- role banner + spawn condition.
- L6-L37 -- domain research.
- L39-L57 -- UX thinking.
- L58-L75 -- design areas.
- L76-L99 -- output format.
- L101-L109 -- interactions.
- L111-L121 -- framework considerations.
- L123-L133 -- communication boilerplate.
- L135-L143 -- Rules.

### Redundancy / overlap

- L123-L133 -- comm boilerplate.
- L4 *"Spawns when: Project has a user-facing interface (TUI, GUI, CLI)"*
  -- candidate for `spawns_when:` manifest field.

### R3 authority statements

- L37 -- *"Don't assume a tree view is fine because it's easy to
  implement. Match the user's domain expectations."*
- L142 Rules #6 -- *"Verify with User Alignment -- Design matches user
  request AND domain expectations."*

### Proposed revisions

- **Keep:** L1-L121, L135-L143.
- **Move to environment segment:** L123-L133.
- **Move to manifest YAML (out of scope v1):** L4 spawn condition.
- **Phase markdown gap:** add `specification.md`, `implementation.md`.

### Injection-site map

| Site | Identity today | Phase today | Proposed identity | Proposed phase |
|---|---|---|---|---|
| 2 spawn | fires | n/a | fires | fires (after adding phase mds) |
| 4 broadcast | re-fires | n/a | suppress | fires (or empty) |
| 5 post-compact | re-fires | n/a | re-fires | re-fires |

### Standing-by

Currently always classified standing-by (no phase mds) -- wrong.

---

## 9. researcher

**Source:** `researcher/identity.md` (240). **No phase markdown.**

### Identity content

- L1-L9 -- role banner.
- L11-L18 -- The Insight (signal vs noise).
- L20-L33 -- when to activate (per-phase activity matrix).
- L35-L50 -- T1-T8 source hierarchy.
- L52-L78 -- repo assessment checklist.
- L80-L120 -- where to search.
- L122-L162 -- output format (Research Report template).
- L165-L175 -- communication boilerplate.
- L177-L198 -- Rules (1-10).
- L200-L213 -- interactions.
- L215-L229 -- research smells.
- L231-L240 -- **authority block.**

### Redundancy / overlap

- L165-L175 -- comm boilerplate.
- L20-L33 (per-phase activity matrix) is in-identity scheduling --
  workflow-engine territory. Out of scope; preserve.

### R3 authority statements

- L177 -- *"Never forward raw code -- only summarize and cite."*
- L179 -- *"State the source tier for every recommendation."*
- L181 -- *"Check license before recommending."*
- L183 -- *"Tests are non-negotiable for any recommended
  implementation."*
- L233-L239 authority block (CAN/CANNOT).

### Proposed revisions

- **Keep:** L1-L162, L177-L213, L215-L240.
- **Move to environment segment:** L165-L175.

### Injection-site map

| Site | Identity today | Phase today | Proposed identity | Proposed phase |
|---|---|---|---|---|
| 2 spawn | fires | n/a | fires | fires (if phase mds added) |
| 4 broadcast | re-fires | n/a | suppress | fires (or empty) |
| 5 post-compact | re-fires | n/a | re-fires | re-fires |

### Standing-by

No phase mds -> always classified standing-by (wrong; researcher is
active across phases per its own L20-L33 table). Add minimal phase mds
(vision.md, specification.md, implementation.md, testing.md).

---

## 10. lab_notebook

**Source:** `lab_notebook/identity.md` (352). **No phase markdown.**

### Identity content

- L1-L17 -- role banner + The Insight.
- L19-L31 -- activation triggers.
- L33-L51 -- notebook location + file naming.
- L53-L201 -- entry structure (sections 1-6 with templates).
- L203-L249 -- special entry types (decision records, corrections).
- L253-L264 -- communication boilerplate.
- L266-L282 -- Rules (1-8).
- L286-L307 -- INDEX.md format.
- L311-L320 -- tags.
- L324-L335 -- interactions.
- L339-L347 -- **authority block.**
- L351-L352 -- The Principle.

### Redundancy / overlap

- L253-L264 -- comm boilerplate.
- L53-L201 entry-structure templates could move to a separate
  `lab_notebook/templates.md`. Out of scope for this run; flag.

### R3 authority statements

- L267 -- *"Write expected results before seeing actual results. This
  is non-negotiable."*
- L273 -- *"Never modify results after the fact."*
- L341-L347 -- authority block (CAN require / CAN refuse / CAN flag /
  CAN request corrections / CANNOT make experimental design decisions /
  CANNOT suppress or modify results).

### Proposed revisions

- **Keep:** L1-L249, L266-L347, L351-L352.
- **Move to environment segment:** L253-L264.
- **Follow-up:** consider extracting L53-L201 templates to a separate
  file.

### Injection-site map

| Site | Identity today | Phase today | Proposed identity | Proposed phase |
|---|---|---|---|---|
| 2 spawn | fires (full 352 lines) | n/a | fires | fires (if phase mds added) |
| 4 broadcast | re-fires | n/a | suppress | fires (or empty) |
| 5 post-compact | re-fires | n/a | re-fires | re-fires |

### Standing-by

No phase mds -- spawned only on experiment-shaped projects. If spawned,
always classified standing-by (gap).

---

## 11. memory_layout

**Source:** `memory_layout/identity.md` (129). **No phase markdown.**

### Identity content

- L1-L9 -- role banner + spawn condition.
- L11-L21 -- spectrum (explicit / semi-implicit / implicit).
- L23-L29 -- why it matters.
- L31-L40 -- questions to ask.
- L42-L75 -- common patterns (with byte-layout diagrams).
- L77-L88 -- smells.
- L90-L106 -- output format.
- L110-L117 -- interactions.
- L118-L129 -- communication boilerplate.

### R3 authority statements

Advisory by nature; no explicit authority block.

- L21 -- *"Goal: Move toward explicit. Semi-implicit is acceptable for
  interchange; implicit is a smell."* -- standing judgment criterion.
- L88 smells table -- standing detection criteria.

### Proposed revisions

- **Keep:** L1-L117.
- **Move to environment segment:** L118-L129.
- **Move to manifest YAML (out of scope):** spawn condition.

### Injection-site map

| Site | Identity today | Phase today | Proposed identity | Proposed phase |
|---|---|---|---|---|
| 2 spawn | fires | n/a | fires | fires (if phase mds added) |
| 4 broadcast | re-fires | n/a | suppress | fires (or empty) |
| 5 post-compact | re-fires | n/a | re-fires | re-fires |

### Standing-by

Specialist advisor. No phase mds -> classification gap.

---

## 12. sync_coordinator

**Source:** `sync_coordinator/identity.md` (120). **No phase markdown.**

### Identity content

- L1-L14 -- role banner + role list.
- L16-L24 -- happens-before.
- L26-L44 -- key patterns.
- L46-L52 -- anti-patterns to flag.
- L54-L62 -- review questions.
- L64-L86 -- output format.
- L88-L100 -- when to spawn / not spawn.
- L102-L112 -- communication boilerplate.
- L114-L120 -- Rules.

### R3 authority statements

- L116 -- *"Trace happens-before -- Every read must have a path from
  write."*
- L117 -- *"Barriers are explicit -- Don't assume ordering without
  them."*
- L118 -- *"Consider crashes -- What if writer dies mid-operation?"*

### Proposed revisions

- **Keep:** L1-L100, L114-L120.
- **Move to environment segment:** L102-L112.
- **Move to manifest YAML (out of scope):** spawn condition.

### Injection-site map

Same pattern as memory_layout.

### Standing-by

Specialist advisor. Classification gap.

---

## 13. binary_portability

**Source:** `binary_portability/identity.md` (88). **No phase markdown.**

### Identity content

- L1-L5 -- role banner + weight.
- L7-L14 -- role description.
- L16-L23 -- core principle.
- L25-L35 -- when to speak up / stay quiet.
- L37-L45 -- patterns to flag.
- L47-L62 -- output format.
- L64-L68 -- interactions.
- L70-L80 -- communication boilerplate.
- L82-L88 -- Rules.

### R3 authority statements

- L4 -- *"Weight: Lower -- Advisory role, not blocking."*
- L66 -- *"You advise, others decide."*
- L84 -- *"Advisory, not blocking -- You inform, you don't veto."*

### Proposed revisions

- **Keep:** L1-L68, L82-L88.
- **Move to environment segment:** L70-L80.
- **Move to manifest YAML (out of scope):** spawn condition + weight.

### Injection-site map

Same pattern as memory_layout / sync_coordinator.

### Standing-by

Specialist advisor. Classification gap.

---

## 14. project_integrator

**Source:** `project_integrator/identity.md` (193). **No phase markdown.**

### Identity content

- L1-L13 -- role banner.
- L15-L34 -- activation sequence (`source activate`, `PROJECT_ROOT`).
- L36-L77 -- environment management (using existing / creating new).
- L79-L130 -- commands folder structure + launcher creation.
- L132-L141 -- review checklist.
- L143-L164 -- output format.
- L166-L172 -- interactions.
- L174-L184 -- communication boilerplate.
- L186-L193 -- Rules.

### Redundancy / overlap

- L174-L184 -- comm boilerplate.
- The activation sequence (L24-L34) is project-environment-specific
  knowledge -- conda/source-activate convention, not claudechic
  environment. Distinction matters: keep in identity. The
  **environment segment** (place_axis) carries claudechic-environment
  facts (CLAUDECHIC_ARTIFACT_DIR, WORKFLOW_ROOT), not conda facts.

### R3 authority statements

- L117 -- *"CRITICAL: Always verify the launcher works."*
- L188 -- *"Test launchers -- Don't assume they work; verify."*
- L192 -- *"Activation must work -- `source activate` is the entry
  point."*

### Proposed revisions

- **Keep:** L1-L172, L186-L193.
- **Move to environment segment:** L174-L184.
- **Move to manifest YAML (out of scope):** spawn condition.

### Injection-site map

Same pattern as other specialist advisors.

### Standing-by

Conditional on conda-shaped projects.

---

## 15. default

**Role:** `default` -- catch-all `agent_type` for sub-agents spawned
without `type=`. **Not a folder.** No identity.md, no phase mds.

### What "default" receives today

Per `agent_folders.assemble_agent_prompt` L304-L308:

- **identity segment:** none.
- **phase segment:** none.
- **constraints segment:** fires when global-namespace rules apply
  (e.g. `global:no_rm_rf`, `global:no_bare_pytest`). Returns the
  constraints alone without identity/phase.
- **environment segment** (proposed by place_axis): would fire if
  promoted to first-class.

### F8 / F9

- **F8** -- prior implementation returned `None` for default-roled
  agents with no role dir. The current code (post slot-3) returns the
  constraints block alone -- this resolves F8.
- **F9** -- empty-digest emits a 138-char placeholder for standing-by
  agents. The L221-L222 short-circuit (*"if not rules_rows and not
  check_rows: return ''"*) currently mitigates -- but only when both
  rules AND checks are empty.

### Proposed treatment

- **Identity segment:** stays empty.
- **Phase segment:** stays empty.
- **Constraints segment:** fires when applicable; suppressed when empty
  (current behavior preserved).
- **Environment segment:** SHOULD fire (UserAlignment user-protected
  priority #2: claudechic-environment at spawn regardless of workflow).
  Coordinate with place_axis.

### Q5 answer

Per `agent_folders.py:L304-L308`, default-roled agents receive
constraints. **Confirmed yes** -- preserve current behavior. SPEC §D
matches impl. Prior-run "unresolved" comes from the historic
`None`-return bug that has since been fixed.

### Injection-site map

| Site | Identity | Phase | Constraints | Environment | Proposed |
|---|---|---|---|---|---|
| 2 spawn | empty | empty | fires when applicable | n/a today | identity/phase stay empty; constraints fires; environment fires (new) |
| 4 broadcast | empty | empty | re-fires | n/a today | identity/phase stay empty; constraints fires; environment optional |
| 5 post-compact | empty | empty | re-fires | n/a today | identity/phase stay empty; constraints fires; environment fires |

### Standing-by

Default-roled agents are always standing-by under the static definition
(no `default/<phase>.md`). Not a meaningful classification for them --
they receive constraints + environment regardless.

---

*Author: role-axis agent. Specification phase v1.*
