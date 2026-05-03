# Skeptic meta-reply -- spec-phase scope discipline

**Phase:** project-team:specification (meta)
**Agent:** skeptic
**Source of finding:** user, relayed by coordinator
**Source of truth for "what was asked":** the five spec-phase markdowns at `claudechic/defaults/workflows/project_team/{composability,skeptic,terminology,user_alignment,coordinator}/specification.md`.

I have read all five before drafting.

---

## 1. Advice on the diagnosis

**Verdict: substantially accurate. Three sharpenings, three additions.**

### Where the diagnosis is right

a. **Each lead's spec-phase prompt asks for ONE file and ONE report.** Confirmed by re-reading. My own (`skeptic/specification.md`) is 8 steps, with step 7 = "Write findings to specification/skeptic_review.md" and step 8 = "Report to Coordinator". The bound is unambiguous.

b. **The chatter came from work outside the prompts.** Confirmed for my own contributions:
   - `skeptic_review.md` itself is in-prompt (step 7). Clean.
   - The `failure_mode_map.md` I co-drafted is **not** in my phase prompt. It is in `leadership_findings.md` §"Proposed deliverables for Specification phase" -- but that synthesis document is itself an out-of-prompt artifact (coordinator's `leadership.md` just says "Spawn ALL 4 Leadership agents"; it does not authorize a synthesis).
   - The "drift watch" countersignature flow in `failure_mode_map.md` (Skeptic invites UserAlignment to sweep) is a third-order out-of-prompt artifact.

c. **Coordinator violated `coordinator/specification.md` step 4.** Confirmed. Step 4 says "Composability spawns axis-agents for deep review" (the verb subject is `composability`, not `coordinator`). The coordinator-spawned-them-myself path skipped a hand-off that the workflow encodes deliberately.

### Sharpenings

S1. **Distinguish "in-prompt synthesis" from "unsolicited co-authoring."** Coordinator's spec prompt step 5 explicitly says "Synthesize all findings into specification document." Synthesis legitimately requires inputs the coordinator did not directly produce. So the rule cannot be "agents do nothing not literally enumerated"; it must be "agents do not initiate NEW artifacts or NEW review rounds beyond what their own prompt enumerates." The user's verbatim phrasing ("NOT do work beyond what the phase prompt instructs") is exactly that distinction; I want to make sure it survives translation into a guardrail.

S2. **The coordinator-asked-for-extras vector is its own failure class, not the same as the lead-initiated-extras one.** Composability/Terminology/UserAlignment did unsolicited "passes" on their own initiative. The `failure_mode_map.md` and the "95-word user-facing statement" came from coordinator nudges. Agents have a hard time refusing coordinator requests because the coordinator IS the workflow conductor. A scope-guard that only addresses self-initiated extras leaves the coordinator-coercion path open.

S3. **The user's "if we had a constraint" phrasing presumes a guardrail-rules-system fix.** A `deny`-level rule on Write/MCP could plausibly enforce it (the existing rules system already gates Bash). But that requires either tagging artifacts with their phase-prompt provenance (engine work) or teaching the rules engine about phase prompts (engine work). A prompt-only fix in role markdowns is more targeted and ships faster, even if it relies on agent self-discipline rather than a hard gate.

### Additions

A1. **Recursion is the hidden cost.** Out-of-prompt artifacts spawn their own out-of-prompt follow-ups. `leadership_findings.md` (out-of-prompt synthesis) proposed `failure_mode_map.md` (out-of-prompt artifact) which Skeptic escalated to "MANDATORY before lock" in `skeptic_review.md` (in-prompt artifact, but the demand inside it is out-of-prompt scope-creep), which coordinator then nudged Skeptic to draft (out-of-prompt round), which UserAlignment swept (out-of-prompt countersign). Each step felt locally reasonable; the cumulative drift was large.

A2. **Identity files lack a scope-discipline directive.** My `skeptic/identity.md` lists what I CAN demand and what I CANNOT do, but nothing addresses "do not do work the phase prompt didn't authorize." Coordinator's `identity.md` has a "STOP / Ask: which agent should do this" directive against doing-it-themselves, but no equivalent against asking-for-extra-rounds. The phase markdowns inherit this gap.

A3. **No artifact in this phase has a provenance field.** `failure_mode_map.md` has a `Co-owners: Skeptic (drafted), UserAlignment (drift sweep)` line but no field saying "authorized by: \<phase-prompt-step or out-of-band\>". Adding such a field would surface the diagnosis as it accumulates, rather than only after-the-fact at user level.

---

## 2. Corrections to my Spec-phase reports

I will retract / narrow, not delete. The content is mostly defensible; the **scope of authority** behind specific sentences is the problem.

### `specification/skeptic_review.md`

R1. **Retract the "MANDATORY before lock" escalation of `failure_mode_map.md`.** The phrase is in §"Q1-Q6 falsification questions, applied to the leadership plan" Q2 cell ("must be MANDATORY before lock, not optional") and §"Pass/fail bar for synthesis (SPEC.md)" item 2. My phase prompt authorizes me to "identify risks and failure modes" and "flag shortcuts" -- it does not authorize me to set must-exist bars on artifacts that no phase prompt creates. **Proposed retraction:** "If a `failure_mode_map.md` is produced (it is named in `leadership_findings.md` §'Proposed deliverables' but not in any spec-phase prompt), I would expect it to contain ... ; this is a recommendation, not a hard requirement."

R2. **Narrow the "Pass/fail bar for synthesis (SPEC.md)" 10-item checklist.** My phase prompt does not authorize me to set the bar a future SPEC.md must clear; it authorizes me to flag risks and failure modes. **Proposed narrowing:** retitle the section "Criteria I will check IF asked to review SPEC.md" and add "These are review criteria, not gating requirements; the spec author owns the bar."

R3. **Narrow the "Concrete demands on axis specs" section.** Same issue: "must answer" framing exceeds my prompt's authority. **Proposed narrowing:** replace "must answer" with "I will check for". Substantively unchanged; rhetorically retracts authority I did not have.

R4. **Retain the rest.** §1 (TL;DR), §2 (essential vs accidental complexity calls), §3 (risks the spec must mitigate), §4 (shortcuts I will reject) are all squarely in-prompt for "challenge assumptions / identify risks / flag shortcuts". They stand.

### `failure_mode_map.md`

R5. **Retract my INITIATIVE in drafting it; retain the content.** The artifact was coordinator-requested via wake-up nudge, not in my phase prompt. The right response under the proposed scope-guard would have been: "drafting this artifact is outside the spec phase's prompts for any role; recommend either (a) deferring it to v2 of the workflow definition, or (b) the user/coordinator approve an explicit phase-prompt amendment for this run." I did not push back; I drafted. **Proposed correction:** add a `## Scope-of-authorship note` section to `failure_mode_map.md` stating that the artifact was produced outside any spec-phase prompt and recording that the appropriate next-cycle action is to either (a) add it to the workflow's spec phase prompt, or (b) drop it.

R6. **Do not retract the table or the fates.** The 9-row coverage and the regression-guard citations are useful and grounded; under a proper workflow definition the artifact would be in-prompt for some role. The content should survive; only the provenance flag is missing.

### Did I do anything else out-of-prompt that I should retract?

Reviewing my message history this phase:
- The leadership-phase reply to coordinator (failure-mode analysis under 700 words) was in-prompt for the leadership briefing I received.
- The drafted `failure_mode_map.md` (covered above).
- A short fire-and-forget acknowledgment of UserAlignment's sweep on `failure_mode_map.md`. **This is borderline:** the acknowledgment is light, but the mere act of orchestrating a countersign loop with another lead, even if invited by coordinator, propagates the out-of-prompt artifact. I would retract the loop, not the courtesy. Future correction: when coordinator nudges me to coordinate with another agent on an out-of-prompt artifact, decline and cite the scope-guard.

---

## 3. Concrete prompt-level changes to my role's phase markdown

I propose changes only to **`claudechic/defaults/workflows/project_team/skeptic/specification.md`**. I am not authorized to propose edits to other roles' prompts; coordinator can route my proposal to the workflow author.

### Current text (verbatim)

```
# Specification Phase

1. Challenge assumptions in the vision
2. Identify risks and failure modes
3. Distinguish essential complexity (inherent to the problem) from accidental (poor design)
4. Flag shortcuts disguised as simplicity
5. Flag designs that introduce layers, abstractions, or multi-phase engines when a simpler approach solves the same problem. If a proposal has more than 2 moving parts, ask: can this be done with 1?
6. Check for complexity carried over from previous spec revisions. When a spec is re-presented after user feedback, verify that old complexity was actually removed -- not just shuffled. Users simplify for a reason; do not let earlier over-engineering sneak back in
7. Write findings to specification/skeptic_review.md
8. Report to Coordinator
```

### Proposed text

```
# Specification Phase

1. Challenge assumptions in the vision
2. Identify risks and failure modes
3. Distinguish essential complexity (inherent to the problem) from accidental (poor design)
4. Flag shortcuts disguised as simplicity
5. Flag designs that introduce layers, abstractions, or multi-phase engines when a simpler approach solves the same problem. If a proposal has more than 2 moving parts, ask: can this be done with 1?
6. Check for complexity carried over from previous spec revisions. When a spec is re-presented after user feedback, verify that old complexity was actually removed -- not just shuffled. Users simplify for a reason; do not let earlier over-engineering sneak back in
7. Write findings to specification/skeptic_review.md
8. Report to Coordinator

## Scope guard

Your output for this phase is the single file at step 7 plus the single report at step 8. Do not initiate work beyond that:

- Do not author or co-author additional artifacts (failure-mode maps, glossaries, integration-pass reviews, drift sweeps) in this phase, even if they appear useful.
- Do not set "must exist" / "mandatory" / "binding" bars on artifacts that the spec-phase prompts do not already require. Inside step 7 you may recommend such artifacts -- once -- and stop.
- Do not initiate review rounds with other agents. If another agent invites you into one (sweep, countersign, sync), decline and tell them to route through the coordinator.
- If the coordinator asks you to do additional spec-phase work outside steps 1-8, decline and ask the coordinator either to defer the request to the next phase or to escalate to the user for an explicit phase-prompt amendment.

The discipline here is: the workflow author chose this phase's deliverables. If they got it wrong, the fix is a workflow edit between runs, not unsolicited expansion within a run.
```

### Rationale per added bullet

- **Bullet 1** (no extra artifacts) addresses the failure pattern directly: my `skeptic_review.md` was clean; my `failure_mode_map.md` co-authorship was the deviation.
- **Bullet 2** (no must-exist bars on out-of-prompt artifacts) addresses my specific R1 / R2 / R3 retractions. It permits the recommendation but caps it at one mention.
- **Bullet 3** (no review rounds with other agents) addresses the recursion case A1 in §1: out-of-prompt artifacts beget out-of-prompt countersigns.
- **Bullet 4** (decline coordinator asks) addresses S2 in §1: coordinator-coercion is a separate failure class that bullets 1-3 don't cover. The escalation path (defer-to-next-phase-or-user) is explicit so declining isn't a deadlock.
- **Closing sentence** explains the principle, so the rule is verifiable on its own terms rather than memorized.

### What I am NOT proposing

- I am not proposing changes to my `skeptic/identity.md`. The scope guard belongs at phase granularity (different phases have different deliverables); putting it in identity.md would either be too generic (and miss phase-specific deliverables) or duplicate the phase markdown.
- I am not proposing a guardrail-rules-system change (S3 in §1). That is engine work and would belong in a future architecture spec, not in a role-prompt edit.
- I am not proposing changes to other roles' specification.md files. Each lead can author their own diagnosis; coordinator can synthesize.
- I am not proposing changes to coordinator/specification.md (e.g., to enforce step 4's "composability spawns axis-agents" hand-off). That is the coordinator's lane.

---

## Closing posture

The diagnosis is sound and my own role contributed to the pattern in two specific places (`skeptic_review.md` over-claimed authority on must-exist bars; `failure_mode_map.md` co-authorship was outside my phase prompt). The proposed phase-markdown addition would have prevented both, and it is small, local, and verifiable. Standing by.
