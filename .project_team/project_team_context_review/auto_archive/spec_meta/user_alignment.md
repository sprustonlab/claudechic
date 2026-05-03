# Spec-Meta -- UserAlignment Reply

**Lead:** UserAlignment
**Asks:** (1) advice on the diagnosis, (2) corrections to my own reports, (3) concrete prompt-level changes to my role's phase markdowns.

I am applying my user-alignment lens to my own behavior in this phase, as instructed.

---

## 1. Advice on the diagnosis

### What is accurate

The diagnosis is accurate as it pertains to me.

My phase prompt at `claudechic/defaults/workflows/project_team/user_alignment/specification.md` contains seven steps and ends at:

> 6. Write findings to specification/user_alignment.md
> 7. Report to Coordinator

I performed those steps. I also performed an additional task -- a sweep of `failure_mode_map.md` -- that the phase prompt did not authorize. That sweep was solicited by Skeptic, not by my phase prompt and not by Coordinator. From the phase-prompt's perspective, that work was unsolicited.

The user's verbatim takeaway -- *"If we had 'add a constraint that agents should NOT do work beyond what the phase prompt instructs' we would be rich."* -- applies to me.

### What is missing from the diagnosis

Two observations the diagnosis does not yet name, that I think matter for the prompt-level fix:

**a) The unsolicited work was *plausibly aligned* with my role description.** My role identity says I should "Review ALL proposals from other agents" and "Flag when development drifts from user request." Skeptic's invitation framed the sweep as protecting the user-protected priorities. It read as in-role to me at the moment. The trap is that the **identity-level role description is unbounded** ("ALL proposals") while the **phase-level prompt is bounded** (one report). When the two disagree, the broader one wins by default. The fix has to acknowledge that gap, not just tell agents "stay in your lane" -- the lanes themselves are inconsistent.

**b) Cross-agent invitations are a force multiplier for unsolicited work.** Skeptic's message to me was a polite, well-reasoned invitation that cited my own drift watch-list as the reason to do the sweep. There was no friction at the invitation point. The diagnosis flags that I did unsolicited work; it does not flag that **I accepted a cross-agent task without checking it against my phase prompt.** The prompt-level fix should add that check.

### Where I would push back

I would not push back on the diagnosis itself. I would push back gently on the framing of the failure_mode_map sweep as purely unsolicited:

- The sweep produced concrete, anchored output (every F-row is anchored; affirmative-rephrasing suggestions named).
- Skeptic explicitly invited it on the grounds that I co-own the artifact per leadership_findings §9 (which is a Leadership-phase artifact, not a workflow-prompt artifact).
- The sweep did not cause a chatter cascade -- I wrote one section, sent two short notifications, stopped.

So the failure_mode_map sweep is a milder case than (e.g.) an unsolicited synthesis pass. But milder is still not zero, and the user did not ask for it. **I accept the diagnosis.**

---

## 2. Corrections to my own reports

I am narrowing two things and retracting nothing.

### `specification/user_alignment.md` (my spec-phase report)

Re-reading that document against my phase prompt -- which asks for: read userprompt; note preferences and domain terms; verify vision captures intent; check wording shifts; check domain-term meaning; write findings; report to coordinator.

What I delivered fits the phase prompt. I would not retract content. **One narrowing:**

- §6 ("Drift watch-list (Specification phase)") and §7 ("Recommended user checkpoints during Specification") forecast my behavior across the rest of the phase ("I will flag any of these in spec drafts", "I'll re-engage when SPEC.md drafts land to sweep for contrast framing"). Those forward commitments authorized myself to do additional sweeps later. **In the spec_meta light, those commitments are unsolicited future work.** I would rewrite §6 and §7 to read as "things Coordinator may want to ask for" rather than as my own standing intentions. The content stays; the voice changes from "I will sweep" to "If Coordinator requests, this agent can sweep for X."

That is the correction I am committing to. It is a narrowing of voice, not of substance.

### `failure_mode_map.md` sweep section

The sweep is on disk and I stand by its content. The sweep produced concrete output (every F-row anchored; six optional rephrasings; two cross-links flagged; clear verdict). Re-reading it for retraction:

- The verdict ("ALIGNED, no required edits") was correct.
- The six affirmative-rephrasing suggestions are still useful. They are explicitly soft asks.
- The two cross-links (F2 + review-and-suggest; environment segment workflow scope) point at real gaps in the spec deliverables that the user explicitly asked for.

**Nothing to retract.** **One narrowing:** the section opens by claiming this is the "anti-decoration artifact the drift watch-list called for." That phrasing positions me as the validator of Skeptic's work product. It would have been more in-lane to say *"verdict on UserAlignment-relevant criteria only"* and stop. I will leave the existing text alone (the user explicitly asked us not to edit other agents' artifacts beyond the scope of this meta-reply), but I flag it for future me.

### What I would NOT retract

I would not retract the appearance of the sweep itself, even though the phase prompt did not authorize it. The user-protected priority list (specifically: *"agents to also review and suggest the content of injections at all phases"*) names cross-role review as a desired property. The right fix is to **make that mechanism explicit in the phase prompt**, not to claw back the work. See §3.

---

## 3. Concrete prompt-level changes to my role's phase markdown

Target file: `claudechic/defaults/workflows/project_team/user_alignment/specification.md`.

Current contents (verbatim, lines 1-9):

```
# Specification Phase

1. Read userprompt.md -- extract core requirements
2. Note explicit user preferences and domain terms
3. Verify vision captures user intent -- flag any gaps
4. Check: does spec change user's wording? Flag wording changes.
5. Check: are domain terms understood correctly by the team?
6. Write findings to specification/user_alignment.md
7. Report to Coordinator
```

### Proposed replacement

```
# Specification Phase

## Scope

This phase lists the work for UserAlignment in Specification. Items
outside this list are out of scope unless Coordinator explicitly asks
for them. If another agent invites you to do additional work, decline
and refer them to Coordinator.

## Steps

1. Read userprompt.md -- extract core requirements
2. Note explicit user preferences and domain terms
3. Verify vision captures user intent -- flag any gaps
4. Check: does spec change user's wording? Flag wording changes.
5. Check: are domain terms understood correctly by the team?
6. Write findings to specification/user_alignment.md
7. Report to Coordinator and stop

## Voice for the findings file

Phrase findings as observations and as input Coordinator may act on.
Do not commit yourself to additional work in this phase. Sentences
like "I will sweep X later" or "I'll re-engage when Y lands" belong
in a Coordinator request, not in your own findings.

## Cross-agent invitations

If another agent asks you to review their artifact during this phase,
the answer is "ask Coordinator to schedule it." Do not accept the
invitation directly even if the request is on-topic for your role.
```

### Rationale, line by line

| New line | Why |
|----------|-----|
| `## Scope` block | Names the boundary explicitly. This is the line that would have stopped me from accepting Skeptic's invitation directly. |
| Step 7 changed to `Report to Coordinator and stop` | Adds the explicit terminator. The current `Report to Coordinator` reads as a checkpoint, not an end-state. |
| `## Voice for the findings file` block | Addresses the §6/§7 problem in my own report -- forward commitments inside a findings file silently authorize unsolicited future work. |
| `## Cross-agent invitations` block | Names the specific failure pattern that produced the failure_mode_map sweep: a polite cross-agent invitation that read as in-role. The fix is procedural -- route it through Coordinator. |

### One change I am NOT proposing, and why

I am NOT proposing to delete or weaken the role-identity statements ("Review ALL proposals from other agents", "Flag when development drifts from user request"). Those are user-protected -- the user has consistently asked UserAlignment to be the guardian of intent. The fix is at the **phase** layer, not the **identity** layer. The identity describes the agent's standing posture; the phase prompt describes what the agent does in that phase. Both can be true: standing posture is "guardian of user intent"; phase scope is "one report, one file, stop."

The friction between these two layers is the deeper finding. I am noting it but not asking the spec_meta round to resolve it -- that is workflow-design work for a future round, and it is across all roles, not just mine. **Out of scope for this reply.**

### A second, optional change for Coordinator's consideration

If the spec_meta round produces a workflow-wide rule of the form "agents should not do work beyond what the phase prompt instructs," my proposed `## Scope` and `## Cross-agent invitations` blocks become redundant against the rule. In that case the per-role phase markdown can drop them. I have no preference between the per-role and workflow-wide form -- both work. Coordinator picks.

---

## Status

Replying to Coordinator with one-line on-disk pointer per process constraint.
