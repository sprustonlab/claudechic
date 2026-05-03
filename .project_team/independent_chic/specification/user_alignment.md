# Spec-Phase User Alignment — independent_chic

**Lens:** UserAlignment
**Phase:** Specification (entry)
**Author:** UserAlignment
**Status:** Forward-looking guide for spec authors. Re-run as a pass over completed spec before phase exit.

---

## 0. Purpose

This document is the **alignment contract** for spec authors. It does two things:

1. **Re-baselines** the user's verbatim asks against the latest STATUS (vision + A1–A12) so spec authors don't have to reconstruct user intent from a 250-line STATUS file.
2. **Provides a checklist** the spec must satisfy before this phase can exit. The end-of-phase pass over the spec compares each spec area against this checklist.

If a spec author proposes anything outside this contract, surface to UserAlignment / Coordinator before writing it. If it's inside the contract but the spec leaves it out, this lens flags that as scope shrink.

---

## 1. The user's verbatim asks (single source of truth)

Every spec sentence traces back to one of these. Quoted with `[sic]` where the user typed casually; do not "correct" the user when quoting them in the spec.

### 1.1 From issue #24 (the kickoff body)

> "We want everything to be in 3 levels:
> a) installed package
> b) user
> c) project
> priority goes from c > b > a
>
> All have .claudechic folder with:
> a) workflows
> b) rules and hints
> c) mcp_tools
>
> workflow button can show all 3
> workflow eng has an artifact dir from setup that is added to agents
> We want a prompt injection telling agents about claudechic.
> settings button in the bottom."

### 1.2 From issue #23 (the body)

- Settings window in the TUI accessible via `/settings` **or** welcome screen.
- Specific keys to **expose**: `default_permission_mode`, `show_message_metadata`, `vi-mode`, `recent-tools-expanded`, `worktree.path_template`, `analytics.enabled`, `logging.file`, `logging.notify-level`, `themes`.
- Project keys to **expose**: `guardrails`, `hints`, `disabled_workflows` (with workflow ID discovery), `disabled_ids` (with available ID listing).
- Keys to **hide**: `analytics.id`, `experimental.*`.
- Env vars to document: `CLAUDECHIC_REMOTE_PORT`, `CHIC_PROFILE`, `CHIC_SAMPLE_THRESHOLD`, `CLAUDE_AGENT_NAME`, `CLAUDE_AGENT_ROLE`, `CLAUDECHIC_APP_PID`, `ANTHROPIC_BASE_URL`.
- Reference page: `docs/configuration.md`.
- Cross-link: issue #21 (welcome-screen settings access).

### 1.3 From the vision-phase Q&A (Q1–Q4)

| Q | User words [sic] | Bound as |
|---|---|---|
| Q1 (vision authority) | "yes, agents can check and surface issues if they find them. we all make mistakes." | A1 |
| Q2 (workdir) | "directly" | Working directly in `/groups/spruston/home/moharb/claudechic` |
| Q3 (cherry-picks) | "adopt" | A2 + A6 |
| Q4 (#4 mechanism) | "for #4 it needs to mirror the .claude/rule behavior" | A3 (operationalized by A4 + A7) |

### 1.4 From the leadership-phase resolution round (Q1–Q9)

| Q | User words [sic] | Bound as |
|---|---|---|
| Q1 (mechanism reading) | "it needs to behave the same, we can touch .claude in ways we are sure are not destructive, overwriteing a sesttings file is out. adding a symlink is out as it is not supported on windows." | A4 |
| Q2 (config tiers) | "config in 2 is what I want. everyhting is the other things." | A5 |
| Q3 (auto default) | "yes." | A6 |
| Q4 (boundary) | "primary." | A7 |
| Q5 (`d55d8c0`) | "you can drop it." | A8 |
| Q6 (silent loss) | "yes, we know what we are doing." | A9 |
| Q7 (abast framing) | "trim we cross polinate not just pull from one." | A10 |
| Q8 (one or two pieces) | "two." | A11 |
| Q9 (settings UI smaller features) | "let the team decide. fine to pospond if too much." | A12 |

---

## 2. Verification: do A4–A12 faithfully capture the user's words?

I re-checked each amendment against the user's verbatim answer. Verdicts:

| Amendment | User words | Verdict |
|---|---|---|
| **A4** (mechanism = behavioral mirror; non-destructive `.claude/` touches OK; no symlinks; no overwriting Claude settings) | "it needs to behave the same, we can touch .claude in ways we are sure are not destructive, overwriteing a sesttings file is out. adding a symlink is out as it is not supported on windows." | **Faithful.** The four constraints (behavioral equivalence; non-destructive touches permitted; no overwrites; no symlinks) all map to user's sentence. |
| **A5** (config 2-tier; "everything in 3" = the four content categories) | "config in 2 is what I want. everyhting is the other things." | **Faithful.** "Everything is the other things" is the user explicitly carving config out of "everything in 3". |
| **A6** (`5700ef5` + `7e30a53` confirmed; auto becomes startup default) | "yes." (in response to "make `auto` the startup default and add to Shift+Tab cycle") | **Faithful** — the question framed the UX change clearly; "yes" is unambiguous. |
| **A7** (boundary primary-state-only) | "primary." | **Faithful.** Combined with Q1, gives the binding A4+A7 reading. |
| **A8** (drop `d55d8c0`) | "you can drop it." | **Faithful.** |
| **A9** (no startup warning; silent loss accepted) | "yes, we know what we are doing." | **Faithful.** Note the framing "we know what we are doing" — user explicitly accepts the risk; spec must not re-introduce a warning to "be safe". |
| **A10** (cross-pollination, not convergence) | "trim we cross polinate not just pull from one." | **Faithful** but creates a wording obligation — see §3.1. |
| **A11** (two-piece) | "two." | **Faithful.** |
| **A12** (smaller features delegated) | "let the team decide. fine to pospond if too much." | **Faithful.** Spec authors have authority to scope; postponements need rationale. |

**Conclusion:** the resolution round was clean. A4–A12 are honest renderings of the user's words. No re-litigation needed.

---

## 3. Wording drift watch (for spec authors)

The user's answers introduced specific words that the spec / docs / UI prose **must** honor. Where lens reports use different words, the user's words win.

### 3.1 "Cross-pollination" — not "convergence" or "merge program" (A10)

**User:** *"trim we cross polinate not just pull from one."*

**Drift in lens reports (RESOLVED):** an earlier draft of `terminology_glossary.md` §6.4 declared "convergence" as a canonical term. The glossary has since been revised: §6.4 is now **"cross-pollination"** canonical, and §6.4b holds the retirement record for "convergence / merge program / alignment merge / join the trees". This drift item is resolved at the glossary level; the spec-author obligations below stand as written.

**Required spec behavior:**
- In spec body, docs, UI labels, comments, and commit messages, use **"cross-pollination"** (the user's word, normalized spelling), or "selective integration" / "coordination".
- Do **not** use "convergence", "converge", "merge program", "fork merge", "alignment program" in spec/docs/UI.
- Code symbols (variable names, module names) are not user-facing and therefore not bound by this — but if spec authors are introducing new symbols here, prefer the cross-pollination vocabulary anyway.

`USER ALIGNMENT [RESOLVED]: terminology_glossary §6.4 has been revised — "cross-pollination" is now canonical, "convergence" lives in §6.4b retirement record. Spec authors use "cross-pollination" / "selective integration" / "coordination". Earlier glossary state is superseded.`

### 3.2 "Primary" — the user's boundary word (A7)

**User:** *"primary."* (in response to "boundary strength: absolute or primary-state-only?")

**Required spec behavior:**
- When the spec describes the boundary rule, use the phrase **"primary-state writes"** (forbidden inside `.claude/`) versus **"non-destructive incidental touches"** (permitted under A7).
- Avoid the absolute formulation ("never write any file inside `.claude/`") — that was the pre-A7 reading. L3 has been softened.
- Boundary CI test must encode the **primary-vs-incidental** distinction, not a blanket-no-write rule.

### 3.3 "Behave the same" — the agent-awareness goal phrasing (A4)

**User:** *"it needs to behave the same, we can touch .claude in ways we are sure are not destructive…"*

**Required spec behavior:**
- The agent-awareness section's goal statement should be: *"agents experience `.claudechic/` content the same way they experience `.claude/rules/` content."* "Behave the same" is the user's frame — the spec is not licensed to interpret this as "feels different but achieves a similar effect." Behavior parity from the agent's perspective is the bar.
- The two prohibitions (no overwriting Claude settings; no symlinks) must be stated in the spec verbatim and carried into the implementation acceptance criteria. The user gave both reasons explicitly ("overwriteing a sesttings file is out", "not supported on windows").

### 3.4 "Settings button in the bottom" + `/settings` (#23 + #24)

**User (#24):** *"settings button in the bottom."*
**User (#23):** *"accessible via `/settings` or welcome screen"* + cross-link to #21.

**Required spec behavior:**
- The settings UI must be reachable from **all three** access surfaces: (a) a button at the bottom of the chat UI; (b) the `/settings` slash command; (c) the welcome screen (per #21 cross-link).
- A12 lets the team postpone any of these if scope balloons — but each postponement requires written rationale referencing A12.
- Wording check: the *thing the button opens* is a "settings window" (#23) or "settings TUI screen" — these are interchangeable, **but** "settings panel" or "settings dialog" are different UI gestalts and should not appear in spec/docs unless deliberate.

### 3.5 "Levels" vs "tiers"

**User (#24):** *"everything to be in 3 **levels**: a) installed package b) user c) project"*

**Team usage:** consistently "tier" (vision §1, L1–L17, lens reports).

**Verdict:** Acceptable as long as user-facing prose uses "level" (or both). Code/internal docs may use "tier". The terminology lens flagged "tier vs level vs namespace" risk — spec authors should pick one user-facing word and stick to it. **Recommend:** user-facing "level" (matches user's word); internal "tier" (matches team's existing usage).

`? USER ALIGNMENT: User said "3 levels"; team writes "3 tiers". These are synonyms here, but the user-facing labels in the workflow button + settings UI should use "level" (the user's word) so the user recognizes their own framing.`

### 3.6 "Workflow button can show all 3"

**User (#24):** *"workflow button can show all 3"*

**Required spec behavior:**
- A "workflow button" UI surface that exposes workflows from all three levels (package, user, project).
- The user did not specify *how* the three sources are distinguished in the UI. The vision says "distinguishing where each came from" (an inference). Spec can pick any reasonable affordance — label, badge, color, grouping — but should pick **one** and document it.
- Wording check: "workflow button" is the user's term; do not relabel as "workflow picker", "workflow chooser", or "workflow menu" in user-facing prose without explicit reason.

### 3.7 "Rules and hints" (paired)

**User (#24):** *"All have .claudechic folder with: a) workflows b) rules and hints c) mcp_tools"*

**Required spec behavior:**
- Rules and hints are paired in the user's mental model. The team's L7 layout (`global/{rules,hints}.yaml`) honors this. Spec must not split them into independently-resolved categories without reflecting the pairing somewhere visible (e.g., a single `global/` directory containing both files; resolution discussion that names them together).
- Independent override resolution per category is OK (Composability axes 2/3); pairing is a presentation/conceptual obligation, not a resolution-mechanism constraint.

---

## 4. Domain terms — does the team share the user's mental model?

### 4.1 ".claude/rules/" (Claude Code's rules system)

**User said:** *"mirror the .claude/rule behavior"* (singular "rule" — minor typo for "rules"; user means the rule mechanism Claude Code provides).

**Domain check:** `.claude/rules/` in Claude Code is a directory of markdown files that Claude auto-loads into context as rule-equivalent. The behavior includes: (a) auto-load on session start; (b) treated by the agent as authoritative; (c) file-based (so users can edit by editing files, not by changing settings). The team's mechanism for `.claudechic/`-equivalent must satisfy (a), (b), (c) from the agent's perspective per A4. Spec authors should validate the chosen mechanism against all three properties, not just one.

`? USER ALIGNMENT: "mirror the .claude/rule behavior" implies (auto-load + treated as authoritative + file-based). Spec mechanism must satisfy all three from the agent's perspective. If the chosen mechanism breaks any of them (e.g., requires a programmatic injection that the user can't influence by editing files), flag for user review.`

### 4.2 "Auto" permission mode

**User said:** *"yes."* (to "make `auto` the startup default")

**Domain check:** "Auto" mode is one of three Claude Code permission modes (`default`, `auto`, `plan`). Auto auto-approves "safe" tools and prompts only on risky ones. The user's "yes" is informed by their existing usage — they know what `auto` does. Spec must not re-introduce the prior `default` mode as a fallback "for safety" without user signoff (would re-litigate A6).

### 4.3 "Settings" vs "config"

**Team convention (L4):** "Settings" = user-facing umbrella term (UI, prose); "Config" = technical term (YAML files, code). User did not endorse this distinction explicitly; user used "settings" naturally in both #23 ("settings window") and #24 ("settings button"). L4 is a defensible team convention. Spec authors should follow L4 in user-facing prose (use "settings"); technical sections may use "config" (e.g., `~/.claudechic/config.yaml`).

### 4.4 "Artifact dir" (workflow setup output)

**User said:** *"workflow eng has an artifact dir from setup that is added to agents"*

**Domain check:** "Added to agents" is the underspecified phrase. Possible team readings:
- (i) The directory path is injected into agent prompts (env var or system-prompt block).
- (ii) The directory is auto-listed in tool-result context.
- (iii) The directory is a known location agents are taught to look at via the agent-awareness rules.

The user did not pick. Composability axis 7 calls this "OPEN — spec phase decides". Spec authors should pick one of (i)/(ii)/(iii) (or compose) and **briefly** state the choice; the user can object if it's wrong.

`? USER ALIGNMENT: "added to agents" is ambiguous between (a) prompt injection of the dir path, (b) auto-listed in context, (c) discoverable via agent-awareness rules. Spec must pick one and surface the choice for user check at spec-phase exit.`

### 4.5 "Cross-pollination" (the user's relationship word for abast)

**User said (Q7):** *"trim we cross polinate not just pull from one."*

**Domain check:** "Cross-pollination" implies bidirectional, ongoing, organic exchange — distinct from "convergence" (which implies a target end-state) and "merge" (which implies a one-time operation). Spec authors should describe the abast relationship in present-continuous, bidirectional terms ("we cross-pollinate selectively with abast", "selected commits flow in both directions"), not in goal-state terms ("we converge our forks").

---

## 5. Scope contract for the spec phase

### 5.1 Must be in spec (user explicitly asked, or A4–A12 ratified)

| Item | Source | Notes |
|---|---|---|
| 3-level layout for workflows / rules+hints / MCP tools, package/user/project, c>b>a | #24, A5 | The four content categories. Config is separately handled (5.2). |
| `.claudechic/` directory at each level | #24 | `~/.claudechic/` (user); `<repo>/.claudechic/` (project); `claudechic/defaults/...` (package). |
| Workflow button shows all 3 levels | #24 | Some UI affordance distinguishing source level. |
| Workflow artifact dir from setup phase, "added to agents" | #24 | Spec picks the "added" mechanism (§4.4). |
| Two-piece agent-awareness injection (always-on at start + once-per-agent first-read) | #24, A11 | Mechanism honors A4 (behavioral mirror, no symlinks, no Claude-settings overwrite). |
| Settings button at the bottom of chat UI | #24 | Plus `/settings` command (#23) plus welcome-screen access (#21). All three under A12 — postponements need rationale. |
| Settings UI exposes #23's nine global keys + four project keys; hides `analytics.id`, `experimental.*` | #23 | Verbatim list. |
| `disabled_workflows` UX with workflow ID discovery; `disabled_ids` with available-ID listing | #23 | A12 lets team postpone with rationale. |
| `docs/configuration.md` reference page covering all config keys, env vars, CLI flags | #23 | Env var list in #23 is authoritative starting point. |
| Cherry-picks from abast: `9fed0f3`, `8e46bca`, `f9c9418`, `5700ef5`, `7e30a53` | A2, A6 | `d55d8c0` skipped (A8); `/fast`-related skipped (L12). |
| `auto` becomes startup permission-mode default; `auto` in Shift+Tab cycle | A6 | UX change is intended; do not gate behind a setting. |
| Boundary rule: claudechic primary state never inside `.claude/`; non-destructive incidental touches OK; no overwrites of Claude settings; no symlinks | A4 + A7 | The two absolute prohibitions stay absolute. |
| Cross-pollination vocabulary (not "convergence") in spec/docs/UI | A10 | See §3.1. |
| Two-file spec format (operational + appendix) | L14 | See §6. |

### 5.2 Spec-author authority (under A12 / open mechanism questions)

The team may choose mechanism freely on these — but each choice needs a one-line rationale in the spec or appendix:

- Override-resolution semantics per content category (workflows, rules, hints, MCP tools) — Composability axis 3.
- Specific agent-awareness injection mechanism within A4's constraints (SDK system-prompt presets / hooks / append paths / non-destructive `.claude/` write).
- Artifact-dir location, naming, lifetime, scope (per-run vs per-phase), surfacing mechanism (§4.4).
- Cherry-pick execution order vs restructure order (user preference: restructure first, but team can deviate with rationale).
- Test strategy specifics (boundary CI test must encode A7's primary-vs-incidental distinction).

### 5.3 NOT in spec (user has not asked, or has explicitly deferred)

- `/fast` mode — L12, deferred to #25.
- Migration/upgrade logic for existing `.claude/.claudechic.yaml`, `.claude/hints_state.json` — L17.
- Startup warning for existing users about state-file relocation — A9.
- mrocklin/claudechic upstream coordination — L1.
- Any abast change not in the A2/A6/A8 cherry-pick table.
- Auto-restoration of pre-A7 absolute boundary (would re-litigate user's "primary." answer).
- Re-litigation of any A4–A12 amendment.

If a spec author wants to pull anything from §5.3 in, they must ask the user via Coordinator.

---

## 6. L14 enforcement (spec/appendix split)

L14 is the most likely process failure of this phase (per prior-run anti-pattern). Spec authors must:

1. **Two files per spec area**, not one. Suggested naming:
   - `<area>_spec.md` — operational only. File paths to create/edit/delete; function/class signatures to add/modify; test assertions to add; acceptance criteria.
   - `<area>_appendix.md` — rationale, rejected paths, reversal triggers, lens-disagreement notes.
2. **Operational sections** in the spec: `Files to create`, `Files to edit`, `Files to delete`, `Functions/classes to add`, `Tests to add`, `Acceptance criteria`. **Not** `Why we chose this`, `Alternatives considered`, `Trade-offs`.
3. **Rationale-leak self-check before publishing each spec.** A reader of *only* the spec file should be able to answer "could I implement this without reading anything else?" with "yes". If "no", move the missing-but-needed content **into the spec** (it was operational); if "no, but only because I wanted to know why" — move that to the appendix.
4. **The grading rubric** (per L14) should be defined and ratified by the Coordinator before any spec area is written, not after.

This lens (UserAlignment) will not grade L14 directly — that's Skeptic / Composability territory. But L14 violations can mask alignment issues (rationale paragraphs that quietly redefine user's words). So if the spec/appendix split slips, this lens's exit pass becomes harder.

---

## 7. Spec-exit acceptance checklist (this lens runs over the completed spec)

When spec authors believe they're done, this lens runs the following pass. Spec is not user-aligned until every item is `[OK]`.

### 7.1 Coverage (no scope shrink)

For each item in §5.1, the spec must have a corresponding operational section:

- [ ] 3-level layout (workflows / rules+hints / mcp_tools) specced for resolution
- [ ] `.claudechic/` at user-tier (`~/.claudechic/`), project-tier (`<repo>/.claudechic/`), package-tier (`claudechic/defaults/`)
- [ ] Workflow button UI surface specced; level distinction picked and documented
- [ ] Artifact-dir mechanism picked and specced ("added to agents" disambiguated)
- [ ] Two-piece agent-awareness injection specced (mechanism + always-on payload + first-read payload + A4 prohibitions encoded)
- [ ] Settings button at bottom of chat UI specced; `/settings` command specced; welcome-screen access either specced or postponement rationale present
- [ ] Settings UI key list matches #23 verbatim (9 global expose + 4 project + 2 hide)
- [ ] `disabled_workflows` ID discovery + `disabled_ids` listing either specced or postponement rationale present
- [ ] `docs/configuration.md` outline specced (full key list + env vars + CLI flags)
- [ ] Cherry-pick set matches A2/A6/A8 table
- [ ] Auto default UX change specced
- [ ] Boundary rule specced as primary-state-only with the two absolute prohibitions
- [ ] Boundary CI test specced; encodes primary-vs-incidental distinction

### 7.2 Wording (no drift)

- [ ] No "convergence" / "merge program" in spec/docs/UI prose (see §3.1)
- [ ] Boundary uses "primary-state writes" vs "non-destructive incidental touches" (see §3.2)
- [ ] Agent-awareness goal stated as "behave the same" (see §3.3)
- [ ] User-facing UI uses "level" (or both "level" and "tier") for the 3-level distinction; not "tier" alone (see §3.5)
- [ ] User-facing UI says "settings" + "settings window/screen"; not "settings panel/dialog" (see §3.4)
- [ ] User-facing UI says "workflow button"; not "workflow picker/menu/chooser" (see §3.6)
- [ ] Abast relationship described in present-continuous bidirectional terms (see §4.5)

### 7.3 Scope (no creep)

- [ ] Nothing from §5.3 has slipped into spec (`/fast`, migration logic, startup warning, mrocklin, non-table cherry-picks, re-litigations)
- [ ] If any §5.2 mechanism choice was made, a one-line rationale appears in the spec or appendix

### 7.4 Process (L14)

- [ ] Two files per spec area (operational + appendix)
- [ ] Operational sections do not contain rationale paragraphs
- [ ] Spec authors ran the rationale-leak self-check (declared in spec metadata)

---

## 8. Recommended user checkpoint at spec-phase exit

Before the Coordinator presents the spec to the user for checkpoint approval, batch the following one-line confirmations:

1. **Artifact-dir mechanism choice.** "We picked [mechanism] for 'added to agents'. OK?" (per §4.4)
2. **Workflow-button level distinction affordance.** "We distinguish package/user/project workflows in the button via [label/badge/color/group]. OK?"
3. **Welcome-screen access.** "Settings is reachable from chat-bottom button + `/settings` + welcome screen [or: welcome-screen access postponed because X]. OK?"
4. **Agent-awareness mechanism.** "We picked [SDK preset / hook / append-path / non-destructive `.claude/` write] within A4 constraints. The agent's experience matches `.claude/rules/` because [reason]. OK?"
5. **Override-resolution semantics per category.** "Workflows resolve [scalar/list-merge/etc.]; rules resolve [...]; hints resolve [...]; MCP tools resolve [...]. OK?"

These are not new questions about user intent — A4–A12 settle intent. They are **mechanism confirmations** so the user sees what they're signing off on at spec exit.

---

## 9. Outstanding lens-flagged drift items (from previous audit)

For traceability — items I flagged in `alignment_audit.md` and how they stand now:

| # | Item | Status |
|---|---|---|
| HIGH 1 | L8 config 2-tier vs "everything in 3 levels" | **Resolved by A5.** User: "everyhting is the other things." |
| HIGH 2 | Vision §7 abast convergence as deliverable | **Resolved by A10.** User: "trim we cross polinate". Vision text unchanged but A10 binds. **Wording obligation §3.1 active.** |
| MED 3 | L15 two-piece vs user's singular "a prompt injection" | **Resolved by A11.** User: "two." |
| MED 4 | A3 mechanism reading | **Resolved by A4.** User: "behave the same…non-destructive…no overwriting…no symlinks." |
| MED 5 | L3 strength | **Resolved by A7.** User: "primary." |
| MED 6 | Q3 cherry-pick `5700ef5` UX implication | **Resolved by A6.** User: "yes." |
| LOW 7 | `/settings` welcome-screen access | **Delegated to spec under A12.** Spec must include or document postponement. |
| LOW 8 | `disabled_workflows` ID discovery UX | **Delegated to spec under A12.** Same. |
| LOW 9 | `disabled_ids` listing UX | **Delegated to spec under A12.** Same. |
| LOW 10 | Settings button vs `/settings` command parity | **Both required under A12.** Spec must address. |

No outstanding HIGH or MEDIUM drift items for the spec phase to entry. All scope questions are settled. Spec authors operate under a clean contract.

---

## § Cross-lens: UX validation of Composability §R6, §R3 disable, §R3 partial-override

This section is a UX-faithfulness pass on three items the Composability spec (`composability.md`) flagged for UserAlignment review. Each item gets: a verdict (agree / agree-with-modification / disagree); operational MUST/SHOULD requirements per L14; and prescribed user-facing wording per §3 obligations.

### Item 1 — R6 mechanism: SessionStart-hook unification (Composability §8.1)

**Composability's recommendation:** SessionStart hook for both always-on awareness and phase-context (one mechanism, two registrations per Seam-C / R6.5); PreToolUse hook on Read for first-read injection.

**Verdict: AGREE.**

**Three-criterion check** (per this doc's §4.1 — `.claude/rules/` parity from agent's perspective requires auto-load + treated-as-authoritative + file-based):

| Criterion | SessionStart hook satisfies? | Note |
|---|---|---|
| (a) Auto-load on session start | YES | SessionStart hook is, by name, exactly this. |
| (b) Treated by the agent as authoritative | YES | SessionStart hook payloads enter the agent's context as system-level injection (system-reminder envelope). The agent treats system-level content as authoritative — same effective weight as `.claude/rules/` content. |
| (c) File-based (user edits files; next session sees the change) | YES, with one caveat | Per R6.3, the hook reads from `claudechic/defaults/context/*.md` (and may extend to `<repo>/.claudechic/context/`). User edits files → next session reads them. The caveat: claudechic owns the loading convention, not Claude Code, so a user adding a file in a non-recognized subdir fails silently unless claudechic recognizes it. This is a discoverability concern, not a "behave the same" concern. |

**Operational requirements:**

- **R6-UX.1 [MUST]** The SessionStart hook payload MUST be assembled from on-disk files (R6.3); it MUST NOT inline hardcoded prompt text. The user must be able to influence the always-on awareness content by editing files, not by editing claudechic source.
- **R6-UX.2 [MUST]** The recognized source root for content files MUST be documented in `docs/configuration.md` (the canonical location: `claudechic/defaults/context/`, with optional `<repo>/.claudechic/context/` override). A user adding a file outside the recognized roots gets no effect; the docs MUST state this.
- **R6-UX.3 [SHOULD]** When claudechic detects a file under `<some_tier>/.claudechic/context/` that the loader does not know how to use (unknown filename, unsupported extension), it SHOULD log an info-level message, not silently ignore. This addresses the (c) caveat.
- **R6-UX.4 [MUST]** The first-read PreToolUse hook MUST trigger only on the first tool-read of a path **inside any `.claudechic/` directory** in that agent's session (per R6.1 / R6.2). Subsequent reads in the same agent session MUST NOT re-inject. From the user's perspective, "the agent sees the deeper context the moment it actually needs it, but doesn't repeat" — the user's intent statement.

**Prescribed user-facing wording (per A10 + §3 obligations):**

- In `docs/configuration.md` and the spec, describe the mechanism as: *"claudechic agents receive a short claudechic-awareness statement at session start, and fuller context the first time they read inside a `.claudechic/` directory. Both pieces are loaded from on-disk files, so users can edit the content by editing files."*
- Do NOT use "convergence" or "merge program" anywhere in this section (per A10).
- The agent-awareness goal phrasing MUST be: *"agents experience `.claudechic/` content the same way they experience `.claude/rules/` content"* (per §3.3 — "behave the same" is the user's frame).
- Do NOT call this mechanism a "rules pipeline" or "rule injection". Per **A13** (RESEARCH.md Option B; user-approved at spec-exit), the claudechic-side mechanism is now an **install** (file copy + SDK auto-load), not an in-process injection. Use **"claudechic-awareness install"** as the canonical phrase for the mechanism (`terminology_glossary.md` §4.6a). The agent-perceived delivery moments — **session-start injection** and **first-read injection** — keep their canonical names; "claudechic-awareness injection" as a name for the *whole mechanism* is retired (`terminology_glossary.md` §4.6b). Reserve "rules" for the actual `rules/` content category (per the §4 domain-term check on "rules" overload).

### Item 2 — `disabled_workflows` / `disabled_ids` semantics: tier-agnostic disable (Composability §8.2 first sub-question)

**Composability's recommendation:** Disable-by-id is tier-agnostic. Disabling `foo` removes it from the effective set regardless of which tier defined it. Rationale: feature-toggles are about *whether the user wants the feature*, not about *which copy of it*.

**Verdict: AGREE WITH MODIFICATION.** Tier-agnostic disable for the toggle action is correct UX. But the **discovery** UI must surface tier provenance so the user understands what they are disabling.

**Why agree on the toggle action:** When a project owner adds `disabled_workflows: ["foo"]` to project config, the natural reading is "I don't want `foo` in this project, regardless of where it comes from." Asking the user to think "is this the package `foo` or the user `foo`?" leaks the tier abstraction into a feature-toggle context where it doesn't belong. The user's #24 framing is feature-categorical ("workflows / rules and hints / mcp_tools"), not tier-categorical. Disable-by-id matches that mental model.

**Why modify on the discovery UI:** The user said in #24 "workflow button can show all 3" — meaning the user IS aware of the 3 levels in some UI surfaces. When the settings UI presents "available workflow IDs to disable", the user benefits from seeing which levels each ID exists at, even though the disable action is flat. This satisfies §3.5 (user-facing UI uses "level" for the 3-level distinction) without contradicting tier-agnostic disable semantics.

**Operational requirements:**

- **R3-UX.1 [MUST]** The disable action is tier-agnostic. The config schema is `disabled_workflows: list[str]` (a flat list of workflow IDs); same for `disabled_ids`. The schema MUST NOT introduce per-tier sub-keys (e.g., `disabled_workflows: {package: [...], user: [...]}`).
- **R3-UX.2 [MUST]** Resolution semantics: the loader's effective-workflow set is computed first (per R3.1–R3.6), then `disabled_workflows` is applied as a filter that removes any effective workflow whose `workflow_id` matches an entry. Same applies to `disabled_ids` for rules/hints. The disable filter operates *after* override resolution, not before. (A workflow defined only at the package tier is disabled if its id is in `disabled_workflows`, even though no user/project tier override exists.)
- **R3-UX.3 [MUST]** The settings UI's discovery surface for `disabled_workflows` MUST present each available `workflow_id` together with the tier(s) where it is defined. Example display: `onboarding (package, user)` — meaning the workflow is defined at both package and user levels, and disabling it disables the effective (user-tier-winning) version.
- **R3-UX.4 [SHOULD]** When a user enters an unknown workflow ID into `disabled_workflows`, the settings UI SHOULD warn (not error) — the ID may refer to a workflow that hasn't been installed yet, or that exists in a tier the user cannot inspect at edit time. Behavior: warn at edit-time; ignore the unknown ID silently at load-time (no functional effect).
- **R3-UX.5 [MUST]** Symmetric requirement for `disabled_ids` (rules/hints): flat list; tier-agnostic disable; discovery surface lists per-id with tier provenance.
- **R3-UX.6 [SHOULD]** A12 permits postponement of the discovery-UX features (workflow ID listing with tier provenance, available-ID listing for `disabled_ids`). If postponed, the postponement rationale MUST reference A12 and MUST state the fallback (e.g., "users edit YAML directly until v2"). Postponing the disable action itself is NOT permitted (it's a #23 baseline).

**Prescribed user-facing wording (per A10 + §3 obligations):**

- In the settings UI, the disable controls are labeled **"Disabled workflows"** and **"Disabled rules / hints"** (NOT "Workflow disable list" / "ID blacklist" — these would change the user's wording from #23).
- The discovery surface labels each entry as `<id> (defined at: package | user | project)` — "defined at" is the operative phrase. Use the word **"level"** for the tier identifier in user-facing labels (per §3.5: user said "level"), e.g., the helper text reads: *"This workflow is defined at the package level. Disabling it will hide it everywhere in this project."*
- The disable action's tooltip / help text uses the phrasing: **"Disabling a workflow by ID hides it from this project regardless of which level (package / user / project) defines it."**
- Do NOT use "tier" in user-facing UI text. "Tier" is reserved for spec/code (per §3.5 + L4).

### Item 3 — Workflow partial-override: forbid + discovery mechanism (Composability §8.2 second sub-question + R3.3)

**Composability's recommendation:** Forbid partial workflow overrides (R3.3 — winning tier owns full file set). For discovery: option (b) — *"document that the user must copy all files of the workflow they wish to override."*

**Verdict: DISAGREE.** Doc-only discovery is a foot-gun. The R3.3 prohibition MUST be enforced by the loader with a loud error, not by documentation alone. Option (a) (reject with an error) MUST be the primary mechanism; documentation is an explanation, not the discovery surface.

**Why disagree:** A user who reads `~/.claudechic/workflows/onboarding/` and sees subfolders like `onboarding_helper/` reasonably tries to drop in just `identity.md` to tweak that one file. Documentation requires the user to read documentation *before* trying — many won't. A loader that silently ignores the partial drop, or silently degrades to lower-tier, gives the user no signal that their edit didn't take effect. The user's debugging path is: edit file → restart → notice no change → try again → eventually read docs → realize they need the full set. That's a long debugging loop for what should be a one-shot error message.

This is exactly the failure mode `vision.md` §"Failure looks like" warns about: *"The artifact dir mechanism is so awkward that workflow authors avoid it."* Generalize the warning: *any* mechanism where the user puts a file and gets no feedback when it doesn't take effect is a UX foot-gun. R3.3's "MUST NOT permit" is a strong commitment; the loader is the right place to enforce it.

**Operational requirements:**

- **R3-UX.7 [MUST]** When the loader walks a tier's `workflows/<workflow_id>/` directory and finds the file set to be incomplete relative to the workflow's definition (manifest present but role identity files missing; or vice-versa; or any subset short of "every file the manifest references"), the loader MUST emit a loud error message and MUST refuse to use that tier's partial definition. The error MUST include: (a) the offending tier path, (b) the missing files (by name), (c) one-line guidance: *"Workflow overrides require the full file set. Either copy all files from the lower tier, or remove the partial override at <path>."*
- **R3-UX.8 [MUST]** The loud error MUST surface in the TUI (not only in log files). Recommended surface: an indicator/notification on app start, pointing to the diagnostics modal or the log path. A user must not be able to "miss" this error.
- **R3-UX.9 [SHOULD]** When the loader detects the partial override, it SHOULD fall through to the next tier (so the system stays usable) — but the error from R3-UX.7 MUST still be visible. Silent fall-through with no error is a foot-gun; error + fall-through is acceptable.
- **R3-UX.10 [MUST]** `docs/configuration.md` MUST document the full-file-set rule with an example: *"To override a workflow at user or project level, copy all files of the workflow into your tier's `workflows/<id>/` directory. Partial overrides (some files in your tier, others in the lower tier) are not supported and will surface as a loader error."*
- **R3-UX.11 [SHOULD]** The settings UI's workflow discovery surface (per R3-UX.3) SHOULD include a one-click "Override this workflow" affordance that copies the full file set from the winning tier into the user or project tier. This is the "happy path" that prevents the partial-override mistake from happening in the first place. If postponed under A12, the postponement rationale MUST reference A12 and the fallback documentation.

**Prescribed user-facing wording (per A10 + §3 obligations):**

- The loader error message uses the phrasing: *"Partial workflow override at `<path>`: missing `<file1>`, `<file2>`. Workflow overrides require the full file set. Copy the missing files from the lower level (package or user), or remove the partial override."* (Use "level" not "tier" — §3.5.)
- The docs section is titled **"Overriding workflows"**, with a subsection **"Why partial overrides are not supported"** (briefly explains the R3.3 rationale).
- Do NOT use the phrasing "blacklist", "blocklist", "denylist" anywhere — these are not user words and overload terminology with `disabled_workflows`. The relevant verb is **"override"** (or "disable" for the toggle in Item 2). Keep them distinct.

---

*End of cross-lens UX validation. Items 1, 2, 3 dispositions: AGREE / AGREE-WITH-MODIFICATION / DISAGREE.*

---

*End of spec-phase user_alignment.md.*
