# User Prompt — independent_chic run

## Original kickoff

> see issue24 vision.md as we are picking up from another team

The user activated the `project-team` workflow and pointed to a hand-off document
authored by a prior team: `.project_team/issue_24/vision.md` (since renamed to
`.project_team/independent_chic/vision.md`).

## Vision-phase clarifications

Coordinator asked four questions; user's answers below.

### Q1 — Authority of the prior team's vision document

> "yes, agents can check and surface issues if they find them. we all make mistakes."

**Resolution:** `vision.md` is the source of truth. L1–L17 and the file-move
inventory are binding. Agents are expected to flag mistakes or inconsistencies
they discover — the document is authoritative but not infallible.

### Q2 — Working directory

> "directly"

**Resolution:** Operate directly in `/groups/spruston/home/moharb/claudechic`
(sprustonlab fork checkout). No worktree.

### Q3 — Disposition of L16 "UX-decision-required" cherry-picks

> "adopt"

**Resolution:** All three deferred-decision commits are pulled. The cherry-pick
table is now fully decided (no open UX gates):

| Commit | Decision |
|---|---|
| `f9c9418` (full model ID + loosened validation) | **Pull** |
| `5700ef5` (default to `auto` permission mode on startup) | **Pull** |
| `7e30a53` (add `auto` to Shift+Tab cycle) | **Pull** (bundled with `5700ef5`) |

### Q4 — Vision amendment

> "for #4 it needs to mirror the .claude/rule behavior"

**Resolution (deliverable #4 — agent awareness):**
The mechanism for surfacing claudechic context to agents must mirror Claude
Code's `.claude/rules/` behavior — file-based, auto-loaded, treated by the
agent as rule-equivalent context. The two-piece L15 semantics still apply
(short always-on at session start + once-per-agent fuller context on first
read inside a `.claudechic/` folder), but the *delivery mechanism* should
look-and-feel like `.claude/rules/` from the agent's perspective.

This is constrained by L3 (claudechic must never write any file inside any
`.claude/` directory). The new team must design how a claudechic-owned
rule-equivalent directory gets auto-loaded by Claude **without** putting
files inside `.claude/`. Mechanism is the new team's call; behavior is fixed.

## Vision approval

User explicitly approved with: "approved"

The approved vision = `vision.md` (verbatim) **plus** the Q3 cherry-pick
adoption **plus** the Q4 agent-awareness amendment.

---

## Leadership-phase user resolution round

After the four Leadership lens reports landed, nine cross-cutting questions
were surfaced. The user's verbatim answers:

### Q1 — Agent-awareness mechanism reading (rules-mirroring vs boundary)

> "it needs to behave the same, we can touch .claude in ways we are sure are
> not destructive, overwriteing a sesttings file is out. adding a symlink is
> out as it is not supported on windows."

**Captured as A4 in STATUS.md.**

### Q2 — Config layering: 2 tiers or 3?

> "config in 2 is what I want. everyhting is the other things."

**Captured as A5 in STATUS.md.** "Everything in 3 levels" referred to the
four content categories (workflows / rules / hints / MCP tools), not to
config keys.

### Q3 — Auto-mode startup default (cherry-pick `5700ef5` + `7e30a53`)

> "yes."

**Captured as A6 in STATUS.md.** Already in the A2 cherry-pick table; A6
records the explicit reaffirmation.

### Q4 — Boundary strength: absolute or primary-state-only?

> "primary."

**Captured as A7 in STATUS.md.** Combined with Q1: claudechic primary state
must not live inside `.claude/`; non-destructive incidental touches are
permitted; overwriting Claude-owned settings is prohibited; symlinks are
prohibited.

### Q5 — Selective `d55d8c0` cherry-pick: keep or drop?

> "you can drop it."

**Captured as A8 in STATUS.md.** Cherry-pick table updated; loader fallback
discovery logic re-implemented from scratch in the restructure.

### Q6 — Existing-user silent loss: warning allowed or no?

> "yes, we know what we are doing."

**Captured as A9 in STATUS.md.** No startup warning. L17 extended to forbid
warnings. Silent loss reclassified from failure mode to accepted tradeoff.

### Q7 — Vision §7 abast convergence framing

> "trim we cross polinate not just pull from one."

**Captured as A10 in STATUS.md.** Cross-pollination is bidirectional, not a
one-way merge program from claudechic's side. Spec/docs/UI language uses
"cross-pollination" / "selective integration" / "coordination", never
"convergence" or "merge program".

### Q8 — Single vs two-piece agent awareness

> "two."

**Captured as A11 in STATUS.md.** Two-piece (always-on + first-read)
confirmed; L15 stands.

### Q9 — Settings UI smaller features (welcome-screen access, workflow-ID discovery, etc.)

> "let the team decide. fine to pospond if too much."

**Captured as A12 in STATUS.md.** Spec-phase team decides scope; postponements
must be recorded with explicit rationale.

---

## Spec-exit instructions (chronological)

After the synthesis pass produced `SPEC.md` and the spec was presented for the
spec-exit user checkpoint, the user issued the following instructions in order.
Each is captured here verbatim for audit trace; rationale and operational
consequences are in `SPEC_APPENDIX.md` §1.8 and in STATUS.md A13.

### SE1 — Spec-exit response to coordinator's three confirmation items

> "1) add symlink to .cluadechic and make an issue in the repo about worktrees
> and windows. 2) please give me more detail please. 3) that is fine"

- Item 1 reversed the synthesis pass's "no symlink, per-worktree fresh state"
  decision; symlink approach restored at `git.py:293-301`; Windows-portability
  question filed as [sprustonlab/claudechic#26](https://github.com/sprustonlab/claudechic/issues/26).
  Drives SPEC.md §10 + §11 + STATUS.md A4 scope-down.
- Item 2 was a request for detail on the SDK uncertainty risks of the original
  Group D mechanism; coordinator answered in chat. No spec change directly
  from the request, but it triggered SE2 below.
- Item 3 confirmed UIDesigner's single-screen settings layout; recorded as
  approved-as-specified.

### SE2 — Rules-format mirror was not faithful

> "No, please read how .cluade/rules work as YAML file with a header and dir spec."

Pointed out that real `.claude/rules/` files use YAML frontmatter (with
`paths`/`globs` for path targeting) and that the synthesis spec's mechanism
did not reproduce this. Triggered SE3 below.

### SE3 — Research before reimplementing

> "is there anything we can use from the internet about how cluade code does
> this so we don't have to reimpliment everything? please spwqn a researched
> for that. the alternative IS to have this copied to the .calude/rules folder
> on startup and added to settings to disable"

Authorized spawning a researcher and named the alternative path explicitly:
copy bundled context docs into `.claude/rules/` on startup; toggle in settings
to disable. Drives the entire A13 redesign.

### SE4 — Option B approval

> "approve option B, fine with all answers. I want to copy as default and the
> settings have a way to desable that. there are no tiers here right? does
> claude reads from ~/.claude/rules?"

Approved RESEARCH.md's Option B (idempotent install of bundled context docs
into `~/.claude/rules/` with `claudechic_` prefix; SDK does the rest).
"Copy as default" + "settings have a way to disable" specifies the install
policy. The two questions were answered in chat: yes, Claude reads from
`~/.claude/rules/` (user tier in Claude's own tier system, alongside
`<repo>/.claude/rules/` project tier and local-tier files); no, claudechic's
3-tier system does not apply to this install (it's flat — bundle ships,
copies once). **Captured as A13 in STATUS.md.**

### SE5 — Hint clarification

> "You are confusing what is a hint, it is a user facing mechnisem"

Corrected coordinator's misunderstanding of the `hints` subsystem. A hint is
a user-facing nudge prompting an action. Drove the deletion of the
`ContextDocsDrift` trigger and `context_docs_outdated` hint from A13's
restoration list — they are NOT restored. The `/onboarding context_docs`
phase remains restored as a manual re-install trigger. Recorded inline in
STATUS.md A13.

### SE6 — Disable-by-choice tradeoff acceptance

> "I will live with that now, if I disable, it is on me."

Confirmed: if a user disables auto-install, they manage `~/.claude/rules/`
themselves; no nudge, no warning. Closes the open question from SE5 about
whether the hint should fire only in the auto-install-disabled case
(answer: no).

### SE8 — Phase-prompt delivery file dropped

> "drop"

Authorized dropping `<repo>/.claudechic/phase_context.md` (the engine-authored,
agent-read file mechanism) after the coordinator's investigation surfaced two
things: (a) the existing PostCompact hook already worked WITHOUT the file by
calling `assemble_phase_prompt` from a closure, and (b) the file's claimed
"becomes part of the system prompt on the next turn" auto-load was almost
certainly wrong (Claude auto-loads `.claude/rules/`, not arbitrary
`.claude/*.md` files). The file was a Read-tool transit medium for content
that could just as easily be sent inline via `_send_to_active_agent`.

**Captured as A15 in STATUS.md.** Drives SPEC.md §4 redesign: phase-prompt
delivery is in-memory. Engine assembles the phase prompt and sends it directly
via `_send_to_active_agent` on activation + phase advance. PostCompact hook
regenerates from workflow files via `assemble_phase_prompt`. No file on disk.

### SE7 — Fresh-review invocation

> "close all agent and spawn 4 new leadership agnet for a fresh review.
> please read your instruction as to how to guide them. show me your plan
> furst"

Invoked the workflow's "Fresh Review" option from the Specification phase
exit-handling list. Drove closure of all spec-phase agents and spawn of
four fresh leadership agents (suffixed `2` per follow-up instruction
"Give them names with a 2 at the end but the same type"). The fresh agents
performed independent cold review of the completed spec.

After plan presentation: user replied "go" to authorize execution.
