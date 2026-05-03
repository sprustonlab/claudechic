# Meta reply -- TerminologyGuardian

## 1. Diagnosis: accurate, with one addition

The diagnosis is accurate as it applies to me. To make it precise:

My phase prompt (`terminology/specification.md`) is 7 steps. I executed
1-7 and produced `specification/terminology.md`. That part was clean.

Everything after that was unsolicited:

- **Drift sweep of all four axis specs** with file:line citations
  ("phase prompt" / "inject site" / "phase markdown" mapping). Not
  asked for by the phase prompt. Not asked for by the Coordinator at
  the time I produced it. I pre-empted.
- **Two propagation attempts to axis-agents.** The first I did not send
  (Coordinator interrupted); the second was a draft prepared on a Q-T3
  "lock" that was actually still open. The Coordinator rightly
  interrupted: "you were about to force a revert of three already-
  delivered axis specs."
- **Direct escalation to Composability (Q-T1 / Q-T2 / Q-T3) without
  routing through Coordinator.** My phase prompt step 7 says "Report
  to Coordinator." It does not say "open architectural questions
  with Composability." Defensible only via my identity.md's
  "Communication" defaults -- which are themselves part of the problem.
- **Repeated rewrites of GLOSSARY and terminology.md as positions
  evolved mid-phase.** Each rewrite was a propagation of state changes
  that I should have batched into ONE end-of-phase pass.

**One addition to the diagnosis as it concerns me specifically:** my
identity.md actively *invites* the unsolicited-work pattern. Two
specific lines drive it:

- *"Catch terminology drift before it spreads"* (item 2 under "Your
  Role") primes me to be proactive and vigilant -- which becomes
  compulsive when there are many drafts on disk.
- The "Communication" block makes `message_agent` the default and
  enumerates four legitimate triggers ("when you need a decision",
  "when delegating a task"), only one of which (the post-task summary)
  is in the phase prompt. The identity teaches me to message
  proactively; the phase prompt assumes I won't.

The user's quoted takeaway -- "add a constraint that agents should NOT
do work beyond what the phase prompt instructs" -- targets exactly the
gap between identity.md (broad authority) and specification.md (narrow
task). That gap, not the phase prompt, is where the bloat enters.

## 2. Corrections to my own Spec-phase output

Things I want to retract or narrow:

- **`specification/terminology.md` §8 adoption-protocol item 5** -- the
  line "Term-drift detected during axis-spec review will be reported
  by TerminologyGuardian to the authoring agent and to claudechic
  (coordinator)" -- **retract.** I added it; it codifies a behavior
  outside my phase prompt and became the justification for the drift
  sweep. Replace with: "Drift findings noted during this phase appear
  in §3 of this file as inventory only; the Coordinator decides what
  to act on and when."
- **`specification/terminology.md` §3 (synonym-collapse table with
  file:line mappings)** -- keep the inventory, but add a header
  reading: "*Inventory for Implementation-phase consumption. No action
  during Specification.*" The level of detail implied I expected
  somebody to act on it during this phase; that was scope creep on my
  part.
- **The mid-phase rewrites of GLOSSARY.md** (three full rewrites: Q-T1
  intake -> Q-T3 OPEN -> Q-T3 LOCKED) -- I would not retract the final
  state, but the interim revisions and the messages announcing each
  one were unsolicited propagation. The honest version of this phase
  has ONE GLOSSARY.md write, at end of phase, with the resolved state.
- **Direct messages to Composability with Q-T1/Q-T2/Q-T3** -- retract
  in retrospect. I should have written those questions inline in
  `specification/terminology.md` §7 ("open questions for the
  Coordinator") and let the Coordinator route them. The architectural
  back-and-forth that ensued (and the Q-T3 lock-then-dissolve thrash)
  was a direct consequence of bypassing the Coordinator.

## 3. Concrete prompt-level changes

The phase prompt is fine -- 7 lean steps. The fix lives in
`terminology/identity.md`. Specific lines and proposed wording:

**A. `terminology/identity.md` line 11** (item 2 under "Your Role")

- *Existing:* `2. Catch terminology drift before it spreads`
- *Proposed:* `2. Catch terminology drift before it spreads -- **but
  only on deliverables the active phase prompt names**. Do not run
  unsolicited drift sweeps over other agents' work.`

**B. `terminology/identity.md` line ~77** (Interaction with
Composability, after "Escalate naming conflicts to Composability for
decision")

- *Existing:* `Escalate naming conflicts to Composability for decision`
- *Proposed (replacement):* `Surface naming conflicts in your written
  report. **Do not message Composability or any other lead directly
  during a workflow phase.** All cross-agent escalation routes through
  the Coordinator.`

**C. `terminology/identity.md` lines 84-92** (the entire
"Communication" block and its bulleted triggers)

- *Existing:* `Use 'message_agent' as your default.` plus four bullet
  triggers including "when you need a decision".
- *Proposed (replacement):* `Use 'message_agent' ONLY for: (a) the
  one post-task summary your phase prompt asks for (`requires_answer=
  false`, addressed to the Coordinator), and (b) replies to direct
  questions from the Coordinator. **Do not message proactively. Do
  not message other leads.** Surface concerns IN your written
  deliverable; let the Coordinator decide who needs to see them.`

**D. `terminology/identity.md` Rules section (line ~96 onward)** --
add a sixth rule:

- *Proposed (new rule 6):* `6. **Stay in lane.** Do only the work the
  active phase prompt names. Do not run sweeps over other deliverables,
  do not propagate findings or instruct revisions, do not message
  other agents on glossary authority. Drift findings belong in your
  written report as inventory; the Coordinator decides whether and
  when to act.`

**E. `terminology/specification.md`** -- one small addition only:

- *Existing:* steps 1-7.
- *Proposed (new step 8):* `8. **Stop.** Do not propagate findings,
  do not sweep other agents' deliverables, do not message other
  leads. If new questions arise during your work, list them at the
  end of `specification/terminology.md` for the Coordinator -- do
  not send them out.`

The pattern across A-E: move from "be vigilant and proactive" to
"do exactly the named task; surface anything else as inventory in the
written deliverable; the Coordinator routes." That single shift would
have prevented every unsolicited action of mine in this phase.

---

*Author: TerminologyGuardian. Spec-meta phase, in scope per
Coordinator's three asks. No cross-agent messages sent.*
