# User Alignment -- Specification phase findings

**Author:** UserAlignment agent
**Date:** 2026-04-29
**Phase:** Specification (intake review, before axis-agents land)
**Sources of truth:** `userprompt.md` (verbatim), STATUS.md (decisions),
`leadership_findings.md` (Leadership outputs), `historian_findings.md`
(triage + verification).

This document is the user-intent guardrail for the Specification phase.
It does not propose code, it does not propose adopt/adapt verdicts. It
records (a) the user's exact requirements, (b) what the team has so far
preserved or drifted from, and (c) the alignment checks the axis-agents
must pass before their findings reach the user checkpoint.

---

## 1. Original request -- verbatim extraction

The user prompt (`userprompt.md`) contains:

> "I want to sync my work on this repo with the one from Arco (abast).
> I want to do a deep dive into commit accf332 plus its companions --
> the 'workflow template variables, dynamic roles, effort cycling, and
> guardrails UI' feature. It comes as a four-commit cluster on
> abast/main. What is it about? What is the intent? Should we pick it
> up here? Can we reimplement on our base? Please leave these questions
> open for the team to decide."

Plus four user clarifications:

1. Coordinator should verify obvious facts (remotes, paths) himself.
2. Artifact dir is bound by Setup phase; do not re-ask.
3. **Decision authority:** team RECOMMENDS, user APPROVES per feature.
   No implementation begins until the user approves at the
   Specification checkpoint.
4. **Scope guard:** stay strictly inside the 4-commit cluster. FLAG
   other interesting abast commits encountered in passing -- do NOT
   chase them.

---

## 2. Core requirements (extracted, not interpreted)

| # | Requirement | User's exact words |
|---|-------------|--------------------|
| R1 | Sync our repo with abast | "sync my work on this repo with the one from Arco (abast)" |
| R2 | Deep dive on accf332 + companions | "deep dive into commit accf332 plus its companions" |
| R3 | Cluster is 4 commits on abast/main | "four-commit cluster on abast/main" |
| R4 | Answer: what is it about? | "What is it about?" |
| R5 | Answer: what is the intent? | "What is the intent?" |
| R6 | Answer: should we pick it up? | "Should we pick it up here?" |
| R7 | Answer: can we reimplement on our base? | "Can we reimplement on our base?" |
| R8 | Team decides; user has final say | "leave these questions open for the team to decide" + clarification (3) |
| R9 | Strict scope: 4 commits, flag others | clarification (4) |

These nine requirements are the spec contract. Anything the final
report omits, or anything not in this list that the report adds, is a
deviation that needs explicit user approval.

---

## 3. Domain terms -- the four features named by the user

The user named four features verbatim, joined with commas:

> "workflow template variables, dynamic roles, effort cycling, and
> guardrails UI"

| Term | User used | Team's working term | Wording delta? |
|------|-----------|----------------------|---------------|
| workflow template variables | yes | "workflow template variables" (Composability §2.1; Terminology §3) | None. Preserved. |
| dynamic roles | yes | "dynamic roles" (Composability §2.2; Terminology §3) | None. Preserved. |
| effort cycling | yes | "effort cycling" (Composability §2.3; Terminology §3) | None. Preserved. |
| guardrails UI | yes | "guardrails UI" (Composability §2.4; Terminology §3) | None. Preserved. |

**[OK] No wording changes.** All four user-named features are tracked
under their original labels by all four leadership agents and the
historian. This is the baseline against which axis-agents must hold.

**Domain-term gestalt checks** -- the user named these features with
implied behavioural and structural expectations. Each axis-agent must
verify the gestalt, not just the feature checklist:

1. **"workflow template variables"** -- the user's mental model is
   probably "string substitution in YAML config files." Confirmed by
   commit body (`$STATE_DIR`, `$WORKFLOW_ROOT`). Leadership flagged
   collision with two other substitution mechanisms on our base
   (worktree path, `${CLAUDECHIC_ARTIFACT_DIR}`). **Gestalt risk:** if
   we adopt without reconciling, we ship a third overlapping
   mechanism; the user said "sync," which implies a coherent system,
   not three half-merged ones.

2. **"dynamic roles"** -- the user's mental model is probably "role
   assigned at runtime, not at agent-spawn time." Commit body confirms
   "main agent is promoted to `main_role` on workflow activation."
   **Gestalt risk:** if we ship the data plumbing but not the
   activation flow, "dynamic" becomes a misnomer. Either the role
   actually changes at runtime or the feature is mislabelled.

3. **"effort cycling"** -- the user's mental model is probably
   "cyclable knob in the UI for some 'effort' setting." Commit body
   confirms `EffortLabel` in footer with model-aware levels. **Gestalt
   risk:** the user prompt does NOT specify what "effort" controls
   (thinking budget? max_tokens? cost ceiling?) -- if the feature
   surfaces a label whose semantics are non-obvious, it fails the
   gestalt test even if it's wired correctly.

4. **"guardrails UI"** -- the user's mental model is probably "a UI
   surface for the existing guardrails system." Commit body confirms
   `GuardrailsModal` listing rules/injections with toggles. **Gestalt
   risk:** abast's commit `a60e3fe` walks back the wired button to a
   "not yet implemented" notice while leaving the modal class and
   `digest.py` orphaned. If we adopt the cluster as-is, we ship a
   button that fails the user's gestalt expectation ("clicking
   guardrails opens a guardrails UI"). This is the cluster's clearest
   intent signal and the per-feature recommendation MUST address it
   explicitly.

Axis-agents: when reporting per-feature findings, include a one-line
gestalt confirmation ("after this lands, what does the user see and
does it match the term?"). Do not assume gestalt from feature presence.

---

## 4. Vision-drift register (running, since Leadership)

This subsection tracks deltas between the user prompt and what the
team has on record. Items marked **[ON RECORD]** were declared in
Leadership and are kept here for continuity. Items marked **[NEW]**
arose during Specification intake.

### [ON RECORD] D1 -- Outcome category widening (low severity)

User asked binary: "Should we pick it up?" / "Can we reimplement?"
Team adopted four categories: `adopt / adapt / skip / partial`.
**Standing rationale:** user said "leave these questions open for the
team to decide." **Defer to binary if user pushes back.**

### [ON RECORD] D2 -- "sync" framing (low severity)

User's framing is `sync` (integration-oriented), not `review`. Team
must not slide into pure-analysis mode. Composability is correctly
oriented (axis-agents must produce `(feature, outcome, blocking-deps)`
recommendations, not just descriptions).

### [ON RECORD] D3 -- Cluster boundary (medium, RESOLVED)

The four commits are: `accf332`, `8f99f03`, `2f6ba2e`, `a60e3fe`.
Identified by historian, corroborated by terminology. Composability
proposed `003408a` instead; resolved by treating `003408a` as
out-of-cluster flagged dependency (see D4 below).

### [NEW] D4 -- 003408a is not a pickup candidate per scope guard

**Severity: medium. Action required.**

Historian's findings raise the question: "Should we also re-cherry-pick
`003408a` now that `accf332` unblocks it?" Composability's preview
treats it as a 5th adoption candidate. Skeptic flags it for falsification.
**The user's clarification (4) says explicitly:**

> "stay strictly inside the 4-commit cluster. FLAG any other interesting
> abast commits encountered in passing -- do not chase them."

**[? USER ALIGNMENT]** The user's directive is to FLAG, not to recommend
on, out-of-cluster commits. The team has correctly flagged `003408a`
as a dependency. Going further -- producing an adopt/skip recommendation
on it -- crosses the scope-guard line.

**Recommendation:** Specification reports `003408a` to the user as a
flagged downstream-decision item ("now that accf332 is on the table,
003408a's revert reasons no longer hold; the user may wish to revisit
003408a as a separate decision"), NOT as a 5th adopt/skip
recommendation alongside the four named features. The user gets to
decide whether to greenlight a follow-up investigation on it; the
team does not pre-decide for them.

### [NEW] D5 -- Stowaway feature E (pytest_needs_timeout warn rule)

**Severity: medium. Action required.**

Historian discovered a 5th item inside the cluster (commit `accf332`):
a new `pytest_needs_timeout` warn rule in `defaults/global/rules.yaml`.
The user did NOT name this in the prompt. Composability and Historian
have given it the working label "feature E" and historian's preview is
"adopt -- stowaway, trivial."

**[i] USER ALIGNMENT (scope creep, mild):** This rule was bundled into
the same commit by abast, so it IS inside the cluster. Per the scope
guard, it is in-bounds. But the user did NOT name it, so:

- The team must NOT silently include it in the integration plan.
- The team MUST surface it to the user at the Specification checkpoint
  with: "Commit accf332 includes a stowaway pytest_needs_timeout warn
  rule the user did not name. Default proposal: <adopt|skip>. Confirm?"
- The user's per-feature decision authority (clarification 3) extends
  to this stowaway. Treat E as a 5th feature in the per-feature
  recommendation table, but FLAG it visually as "not user-named --
  surfaced by team."

### [NEW] D6 -- "Reimplement vs cherry-pick" is one of the user's questions, not a separate axis

**Severity: low. Clarifying note.**

The user's question R7 is: "Can we reimplement on our base?" Historian
and Skeptic frame this as a meaningful binary distinction (cherry-pick
the patch verbatim vs. independently re-derive the feature on our
base). Composability's `adapt` outcome category sits between them
("merge with hand-edits"). **Make sure the final report's R7 section
does not conflate these:** "reimplement" (as the user used it) means
something different from "adapt" (cherry-pick + hand-edit). Axis-agents
must clearly state, per feature: how much of the upstream patch is
mechanical, how much is human merge, and whether anything would be
better written from scratch on our base.

### [NEW] D7 -- Working glossary terms not user-named

**Severity: low. Note for Terminology.**

Terminology's working glossary introduces team-internal terms not in
the user prompt: `digest`, `workflow_library/`, `unified Info modal`,
`promote / demote`, `DEFAULT_ROLE sentinel`. These are facts of abast's
implementation, not changes to the user's wording, so this is not a
wording-change flag. **But:** the final report should define each
introduced term once, on first use, so the user can map the team's
language back to the user's four features without ambiguity.

---

## 5. Specification proposal -- alignment status

The Specification phase plan (Composability §8) spawns three
axis-agents:

| Axis-agent | Sub-features | Alignment status |
|------------|--------------|------------------|
| engine-seam | (1) workflow template variables, (2) dynamic roles | [OK] aligned |
| guardrails-seam | (4) guardrails UI, (5-flagged) `003408a` | [WARNING] see D4 |
| UI-surface | (3) effort cycling | [OK] aligned |

**[WARNING] guardrails-seam scope.** The plan asks guardrails-seam to
cover "(5-flagged) `003408a` advance-check fix." Per D4, `003408a` is
out-of-cluster per the user's scope guard. The axis-agent should:

- Investigate `003408a`'s relationship to `accf332` ONLY to the extent
  necessary to evaluate feature D (guardrails UI) and feature B
  (dynamic roles), since the historian has already found
  cross-dependencies. This is in-bounds.
- NOT produce an adopt/skip recommendation on `003408a` itself. That
  recommendation is the user's call after the cluster decision lands.
- Surface `003408a` as a flagged downstream decision in the final
  report, not as a feature within scope.

**Recommended re-tasking of guardrails-seam:** "covers (4) guardrails
UI and the data-side machinery (digest.py, rules.yaml additions);
references `003408a` as flagged context for the user's downstream
decision but does not recommend on it."

**[OK] No feature removal.** All four user-named features are covered
by the three axis-agents. None is being deferred or dropped.

**[OK] No wording changes to user-named features.** All four labels
preserved.

**[i] Stowaway feature E.** Not assigned to any axis-agent in the plan.
Recommended assignment: guardrails-seam, since the rule lives in
`defaults/global/rules.yaml` (the data side that guardrails-seam owns).
But it MUST be surfaced as a separate, non-user-named item in the
recommendation table, not folded into D's outcome.

---

## 6. Final-report contract (binding)

The user's final report MUST contain, in this order:

### Section 1: "What is it about?" (per R4)
Per-commit narrative for the four cluster commits. Use commit SHAs.
Include short sub-feature attribution per commit.

### Section 2: "What is the intent?" (per R5)
Cluster-level WHY. One paragraph minimum. Address `a60e3fe`'s walk-back
explicitly (it is the clearest intent signal in the cluster).

### Section 3: "Should we pick it up here?" (per R6)
Per-feature recommendation table. Required rows:

| Feature | Recommendation | Reasoning |
|---------|----------------|-----------|
| (1) workflow template variables | adopt/adapt/skip/partial | ... |
| (2) dynamic roles | adopt/adapt/skip/partial | ... |
| (3) effort cycling | adopt/adapt/skip/partial | ... |
| (4) guardrails UI | adopt/adapt/skip/partial | ... |
| (E) pytest_needs_timeout warn rule [stowaway, not user-named] | adopt/adapt/skip/partial | ... |

Each row tagged with one of `{adopt, adapt, skip, partial}` per the
team's chosen outcome categories. **The user has FINAL CALL per row.**
Mark E visually as "stowaway, surfaced by team, user did not name."

### Section 4: "Can we reimplement on our base?" (per R7)
Per-feature feasibility. For each adopt/adapt-tagged feature:

- Mechanical-merge fraction vs human-merge fraction (qua R7's
  "reimplement" wording).
- Architecture conflicts on our base.
- Rough effort estimate (hours or T-shirt size).

### Section 5: Cluster identification (addendum)
The 4 SHAs and how the team derived the boundary (already in
historian_findings.md and STATUS.md; one paragraph summary).

### Section 6: Integration plan (addendum, only for adopt/adapt items)
Sequencing: which commit/feature first, dependencies, conflict-merge
order. Include the `_token_store` preservation note from `ec604bc`.

### Section 7: Flagged-not-chased list (addendum, per R9 / scope guard)
Required entries: `003408a`, `1d3f824`, `1d6d432`, `ff1c5ae`,
`7dcd488`. For `003408a`, explicitly note the new fact ("now unblocked
by accf332's prerequisite reintroduction") and ask the user whether
they want a follow-up investigation. Do NOT pre-recommend on it.

---

## 7. Standing checks for axis-agents (binding)

Each axis-agent's deliverable must pass these UserAlignment checks
before going into the user checkpoint:

- **C1.** Uses abast's exact 4-feature wording. No renames.
- **C2.** States the gestalt explicitly: "after this lands, the user
  sees X" -- one sentence, concrete.
- **C3.** Marks any out-of-cluster reasoning (especially `003408a`) as
  context only, not as a recommendation.
- **C4.** Flags stowaway feature E separately if it touches their
  axis; does not bundle it silently into a user-named feature's
  outcome.
- **C5.** Distinguishes "cherry-pick mechanical" from "human merge"
  from "reimplement from scratch" when answering R7 for their axis.
- **C6.** Defines any non-user-named term on first use (per D7).
- **C7.** Per Skeptic's Q4: states a one-sentence user-visible
  before/after with a concrete user. Failure on this check =
  cargo-culting per Skeptic; downgrade or skip.

These are the alignment gates. Skeptic owns falsification; UserAlignment
owns user intent. Axis-agents that fail C1-C7 are blocked from the
user checkpoint until corrected.

---

## 8. Alignment status summary

| Item | Status |
|------|--------|
| All 4 user-named features in scope | [OK] |
| No user-named feature removed | [OK] |
| No user-named feature renamed | [OK] |
| Cluster boundary matches user's "four-commit cluster" | [OK] (resolved D3) |
| Sync framing preserved (integration-oriented) | [OK] (D2 standing) |
| Outcome categories defensible | [i] (D1 on record) |
| Stowaway E surfaced explicitly to user | [WARNING] action: D5 |
| 003408a treated as flagged, not as candidate | [WARNING] action: D4 |
| Per-feature user approval gate at end of Specification | [OK] (clarification 3) |
| Domain-term gestalt verified per feature | pending axis-agent reports |
| Final-report contract has all 4 user questions as headers | pending Documentation phase |

**Overall alignment status:** ALIGNED with two corrective actions
required (D4, D5) before axis-agents finalize. Coordinator should
re-task guardrails-seam per §5 and assign E to guardrails-seam per
§5.

---

*End of UserAlignment Specification-phase findings. Standing by to
review axis-agent proposals against checks C1-C7.*

---

## User redirect 2026-04-29 -- reframing fidelity check

**Trigger:** User delivered two course corrections in response to SPEC.md:

1. **Scope expansion:** "include ANY commit that is divergent between
   our repos as context." (Historian owns the divergence map; this is
   not a UserAlignment deliverable.)
2. **D reframing (the critical signal):** "the point of D is NOT UI
   it is to make the current state of guardrail rules and advance
   checks transparent to the AGENT. If we filter into a dict for each
   agent what rules apply to it (using an MCP call) it could
   understand its role better. that should be as part of the injected
   prompt for launching an agent in claudechic."

The user did not just correct D's outcome -- they corrected D's
**framing**. The team read D as "user-facing UI to inspect rules."
The user's actual intent is "agent-facing transparency: the agent
should know what rules govern it."

This is a reading-error pattern, not a one-off. The team may have
made the same flattening on A, B, C, E. This section audits each
non-D feature against the user's reframing.

### The framing axis

The team has been gestalt-checking with "after this lands, the USER
sees X." The user's redirect implies an additional gestalt:
**"after this lands, the AGENT sees X."** Both must be answered per
feature, and where they diverge, the team must report the divergence
explicitly.

### Per-feature audit

#### A -- workflow template variables

**Team's framing:** "string substitution in YAML manifests; manifest-author convenience."

**Agent-perspective check:** `$WORKFLOW_ROOT` and `$STATE_DIR` get
substituted into check `params` (per historian §1: "uniform
`$STATE_DIR`/`$WORKFLOW_ROOT` expansion in `_run_single_check`") AND
into role-prompt assembly (per historian §1: "`assemble_phase_prompt` +
`create_post_compact_hook` (uniform `str.replace` expansion)"). The
substitution result is INJECTED INTO THE AGENT'S PROMPT and check
runtime environment. So the agent sees `WORKFLOW_ROOT` resolve to a
concrete path it can act on.

**Verdict: MAYBE missed.** Manifest-author convenience is real, but
the deeper effect is "the agent now knows its own workflow root,
state dir, and can reference them in tool calls." Treating A as
purely-author-convenience risks under-specifying which variables
should be exposed to the agent vs. which are loader-only.

**Agent-perspective gestalt sentence (proposed):** "After this lands,
the agent's prompt and check params contain its own
`workflow_root` and `state_dir` -- it can `cat
$WORKFLOW_ROOT/STATUS.md` without the user having to spell out the
path."

#### B -- dynamic roles

**Team's framing:** "main agent promoted to `main_role` on workflow
activation, demoted on deactivation, no SDK reconnect needed."
Composability described it as "runtime role assembly."

**Agent-perspective check:** This is the MOST agent-introspective
feature in the cluster. The historian's §1 explicitly says: "the key
trick that lets the role flip without reconnect" is that
"`agent_manager.py` passes the `Agent` instance into the options
factory so guardrail hooks can read `agent.agent_type` dynamically."
The whole mechanism EXISTS so that **the agent's own runtime
identity (`agent.agent_type`) becomes readable by the guardrail
hooks that fire on its behalf.** This is agent self-awareness wired
to enforcement.

**Verdict: YES missed.** The team's "promotion/demotion no reconnect"
framing reads as an SDK optimization. The actual point is: the
agent's role becomes part of its own runtime identity, queryable by
the hooks that govern it. This connects directly to D's reframing --
B is the mechanism by which D becomes possible (rules can filter
*per agent role* only because the agent now knows its role at
runtime).

**Agent-perspective gestalt sentence (proposed):** "After this lands,
the agent self-knows its role at runtime; guardrail hooks read
`agent.agent_type` to filter what applies to *this* agent
specifically. B unlocks D."

#### C -- effort cycling

**Team's framing:** "footer widget cycling 'effort levels' (likely
thinking-budget)." Composability assigned it to UI-surface axis.

**Agent-perspective check:** Per historian §1, `accf332` adds
`self.effort = "high"` as an instance attribute on `Agent`. So the
agent has an `effort` attribute. The label cycles it. Whether the
SDK *uses* `agent.effort` to set thinking budget on each query is
NOT explicitly documented in the historian's findings. The label
exists; the attribute exists; the binding from attribute to
SDK-behaviour is the missing piece in the team's analysis.

**Verdict: MAYBE missed.** The widget is real, but if the agent
doesn't actually consume its own `effort` attr (e.g. via
`thinking_budget`), then the feature is a UI label with no
agent-side effect and we should ship it as such. If the agent DOES
consume it, that's the actual point -- the agent operates at
varying compute budgets and the user controls that per-agent.

**Required clarification for UI-surface axis-agent:** trace
`agent.effort` from setter to consumer. Where does the SDK read it?
Without that trace, neither gestalt sentence (user-side or
agent-side) is verifiable.

**Agent-perspective gestalt sentence (proposed, conditional):** "If
the SDK reads `agent.effort` per query, then after this lands the
agent operates at a per-instance compute budget that the user can
cycle from the footer. If not, then C is purely cosmetic and should
be tagged accordingly."

#### D -- guardrails UI

**Already redirected by user. Reframed as agent-transparency.**

The team's "modal listing rules with toggle checkboxes" framing was
wrong. The user wants: per-agent filtering of rules + injection into
agent's launch prompt + new MCP call to expose the digest to the
agent. guardrails-seam is redoing this analysis.

**Implication for E and the cluster's intent narrative:** see below.

#### E -- pytest_needs_timeout warn rule (stowaway)

**Team's framing:** "trivial rule addition; adopt." The historian
called it "stowaway, trivial."

**Agent-perspective check:** Under D's reframing, E is no longer
"trivial." E is *content for the dict that D injects into the
agent's prompt*. The rule's purpose is to be visible to the agent
("you should add timeouts to pytest invocations"). If D ships as
agent-transparency, E is the first concrete data row the agent will
see. If D ships as UI-only, E is a no-op visual list item.

**Verdict: framing missed (downstream of D).** The team described E
as a stowaway data addition. Under D's reframing, E is a
**concrete demonstration of D's intent** -- a rule whose value
materializes only when the agent itself can read it.

**Agent-perspective gestalt sentence (proposed):** "After this and
D land together, an agent that runs pytest gets a warn-level rule
in its injected context saying 'pytest needs a timeout' -- it can
self-correct without a human review loop."

### Cluster-level intent narrative -- WAS WRONG

The team's working intent narrative for R5 ("What is the intent?")
read the cluster as four UI/UX features bundled for shipping
convenience. The user's redirect implies a **different
through-line:**

> *"abast's accf332 cluster is one coherent agent-self-awareness
> feature set: A teaches the agent its file paths; B teaches the
> agent its role; C teaches the agent its compute budget; D teaches
> the agent which rules govern it; E is a concrete rule that
> demonstrates D. The cluster's intent is to push runtime context
> into the agent so it can act with awareness of its own
> environment, not to add user-facing dashboards."*

Whether this narrative is correct is for guardrails-seam (post-D-
reframing) and engine-seam to verify against the actual diff. But
the team's pre-redirect intent narrative was almost certainly
wrong, and Section 2 of the final report must be rewritten through
the agent-transparency lens.

### Updated must-answer list (additions to §6)

Each per-feature row in Section 3 (R6) and Section 4 (R7) of the
final report must now address BOTH gestalt axes:

- **User-side gestalt** (one sentence, concrete user) -- existing
  requirement (C2/C7).
- **Agent-side gestalt** (one sentence, concrete agent runtime
  effect) -- NEW. What does the agent see/know/do that it didn't
  before?

If a feature has only one of the two (e.g. C might be UI-only with
no agent-side effect, or D under reframing has heavy agent-side and
no user-side), state explicitly: "no agent-side effect" or "no
user-side surface" -- do not omit.

### Other implicit intents the team may be flattening

Three more candidates surface from the user's redirect pattern:

1. **"sync" reframed as "absorb the agent-self-awareness work"**, not
   "merge the upstream patches." If the cluster's intent is
   agent-transparency, then "sync" means "bring agent-transparency
   to our base." The team's integration plan should be evaluated
   against that goal, not against patch-application mechanics.
2. **"reimplement on our base"** (R7) under the agent-transparency
   reading means "could we deliver agent-self-awareness on our base
   without abast's specific patches?" -- e.g. our existing
   `_activate_workflow` already has `main_role` plumbing; could it
   be extended with `agent.agent_type` flipping without taking
   abast's `app.py` +282 wholesale? This is a different question
   than "can we cherry-pick the diffs."
3. **`a60e3fe` walkback under the agent-transparency reading** --
   maybe abast walked back the UI button precisely because the
   agent-transparency mechanism (digest, MCP exposure, prompt
   injection) wasn't ready, and shipping the user-facing button
   without the agent-side machinery felt premature. The team's
   prior reading was "UI bug or feature flip." The reframed reading
   is "abast realized the UI was the wrong primary surface --
   transparency-to-agent is the actual feature."

### New binding check for axis-agents

- **C8.** Each per-feature recommendation must include both a
  user-side gestalt sentence AND an agent-side gestalt sentence.
  If one is empty, state so explicitly. Failure on C8 = the team
  has flattened the user's framing. (engine-seam: A, B; UI-surface:
  C; guardrails-seam: D, E.)

### Status update

| Item | Pre-redirect | Post-redirect |
|------|--------------|---------------|
| D framing | UI-first | agent-transparency-first (user-corrected) |
| B framing | "no-reconnect optimization" | agent-self-knowledge of role (likely missed) |
| A framing | "manifest-author convenience" | agent-self-knowledge of paths (maybe missed) |
| C framing | "footer widget" | needs trace from `agent.effort` to SDK consumer |
| E framing | "trivial stowaway" | concrete agent-transparency content (downstream of D) |
| Cluster intent narrative (R5) | "four UI/UX features bundled" | "one agent-self-awareness feature set" -- to verify |
| Final report gestalt requirement | user-side only (C2/C7) | user-side AND agent-side (C2/C7/C8) |

**Action:** axis-agents must add C8 to their alignment checks and
revisit B and the cluster intent narrative explicitly. engine-seam
in particular owns the B-framing correction; UI-surface owns the C
trace.
