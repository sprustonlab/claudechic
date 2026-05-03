# Alignment Audit — independent_chic

**Lens:** UserAlignment (verification that team output matches stated user intent)
**Author:** UserAlignment leadership agent (this run)
**Phase:** Leadership
**Status:** Final for Leadership phase. Re-run before specification-phase exit.

---

## 0. Frame

This audit applies one lens: **does what the team is solving match what the user actually asked?** It is not a technical, naming, or hazard review. The binding inputs are the user's verbatim words in `userprompt.md` plus the issue text of sprustonlab/claudechic#23 and #24. Every claim or deliverable that traces only to prior-team analysis (D1–D22, BF1–BF7, the four prior lenses) is treated as **inference** unless it is also in the user's words.

**Severity tags used below:**

- `[OK]` — vision/STATUS claim is supported by user's words (#23, #24, kickoff, Q1–Q4).
- `[INFER]` — defensible interpretation of user words; user did not say it directly. Should be surfaced as a soft user check.
- `[DRIFT]` — vision/STATUS claim is not supported by user's words and may differ from what the user meant. Hard user check needed.
- `[STRETCH]` — claim takes a thin user statement and adds substantial structure not in the user's words.
- `[GAP]` — something the user wanted that no current deliverable covers.
- `[SCOPE-ADD]` — something in deliverables that the user did not ask for.

A1 ("vision is authoritative but not infallible") is the operating warrant: surfacing inferences and stretches is what A1 instructs.

---

## 1. Vision-vs-user-intent audit (section by section)

The user's words on #24 are short. Reproduced verbatim for ground truth:

> 1. We want everything to be in 3 levels:
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
> settings button in the bottom.

Plus the user's Q1–Q4 answers (in `userprompt.md`).

### 1.1 Goal sentence (vision §"Goal")

> "Restructure claudechic so that workflows, rules, hints, and MCP tools are layered across three override tiers (package, user, project — project wins), claudechic-owned state lives only in `.claudechic/` directories (never inside `.claude/`), and agents running inside claudechic understand the environment they're in."

| Clause | Status | Note |
|---|---|---|
| "workflows, rules, hints, and MCP tools…three tiers (package, user, project — project wins)" | `[OK]` | User: "everything to be in 3 levels…priority c > b > a", "all have .claudechic folder with: a) workflows b) rules and hints c) mcp_tools". |
| "claudechic-owned state lives only in `.claudechic/` directories (never inside `.claude/`)" | `[INFER]` | User said "all have .claudechic folder with…". The user did **not** say "never inside `.claude/`" — that absolute prohibition is L3, inherited from the prior team. It is a defensible reading but not user-spoken. |
| "agents running inside claudechic understand the environment they're in" | `[OK]` | User: "We want a prompt injection telling agents about claudechic." |

### 1.2 Section "Why this matters"

`[OK]` as rationale; not a deliverable; cannot drift. Notable: it asserts "claudechic today mixes its own state into Claude Code's `.claude/` namespace" — true, observable in the code. Justifies L3 indirectly.

### 1.3 §"What we want" #1 — Three-tier override system for content

| Vision claim | Status | Note |
|---|---|---|
| Three tiers (package/user/project), project wins | `[OK]` | Direct from user. |
| Tiers cover **four** categories: Workflows, Rules, Hints, MCP tools | `[INFER]` | User listed three buckets: "(a) workflows (b) rules and hints (c) mcp_tools". The vision's footnote ("Rules and hints are conceptually paired … whether they're a single directory or two siblings is a mechanism choice") preserves this. **Acceptable** — but the deliverable count language (the vision uses "four categories" and L7 says `global/{rules,hints}.yaml`) should not become a normative split that contradicts the user's pairing. |

### 1.4 §"What we want" #2 — Two-tier override system for config keys

> "Configuration keys (the things issue #23 lists for the settings UI…) are layered across user and project. There is no package config file; defaults live in code."

`[DRIFT]` — **Direct contradiction with user's "everything to be in 3 levels."**

The user said "everything to be in 3 levels: a) installed package b) user c) project". The vision (and L8) carves config out into 2-tier (user + project, no package). This may be a sound engineering choice — defaults in code is normal — but it is a **carve-out from the user's universal "everything" statement** and the user has not endorsed the carve-out.

The prior-run alignment audit flagged this same tension in different form (D17 strict-reading inference, "global tier collapse"). It was flagged then for user adjudication; the user has still not adjudicated it. The user's Q3 answer ("adopt") was about cherry-picks, not about config tiering. Q4 was about agent-awareness.

**Recommend:** surface as a user checkpoint in the spec phase. Phrase: *"You said 'everything in 3 levels' — for **config keys** specifically, the team proposes 2 tiers (user + project), with package defaults in code rather than a third config file. OK?"*

### 1.5 §"What we want" #3 — The boundary

> "Claudechic must never write any file inside any `.claude/` directory…"

`[INFER]` / `[STRETCH]`. The user's words "all have .claudechic folder with…" describe the *new* organization. They do not explicitly forbid claudechic from writing inside `.claude/`. The L3 absolute prohibition is the prior team's interpretation, made into a binding lock.

It is a **reasonable** interpretation — if everything is supposed to live in `.claudechic/`, then writing into `.claude/` defeats the structure. But the user has not been asked the precise framing: "you want all claudechic state in `.claudechic/` — does that mean we must never write into `.claude/` ever, or that the *primary* claudechic state lives in `.claudechic/` while incidental `.claude/` writes (e.g., installing rules into `.claude/rules/` so Claude Code reads them) remain acceptable?"

The strong reading and the weaker reading have very different implications for A3 (mirror `.claude/rules/` behavior — see §3 below). If L3 weakens, A3 becomes trivial; if L3 holds, A3 is hard.

**Recommend:** when the team picks the A3 mechanism, explicitly state to the user: *"we read your '.claudechic/ for everything' as 'never write to .claude/'. This makes the agent-awareness mechanism more constrained. If you'd prefer to allow installing one .claude/rules/ file as the agent-awareness mechanism, the design simplifies." Get an explicit choice.*

### 1.6 §"What we want" #4 — Agent awareness

> "Always, at session start — a short prompt-level statement…"
> "Once per agent, on first read in a claudechic folder — fuller context…"
> "The 'first read only' semantics matter."

**User's words:** "We want a prompt injection telling agents about claudechic." Singular. One injection. Plus the Q4 amendment: "for #4 it needs to mirror the .claude/rule behavior."

| Vision element | Status | Note |
|---|---|---|
| "Agent should know it's in a TUI / there are guardrails / workflows / hints / .claudechic vs .claude" | `[OK]` | A faithful expansion of "telling agents about claudechic." |
| **Two pieces** of awareness (always-on + once-per-agent on first read) | `[STRETCH]` | User said "a prompt injection" (singular). The two-piece scheme is L15, prior-team. The user has not directly endorsed it. |
| "First read only" semantics, "once per agent-session, not per read" | `[INFER]` | Sensible design. Not user-spoken. |
| Q4 mechanism: "mirror `.claude/rules/` behavior" | `[OK] but ambiguous` | See §3 below for A3 audit. |

The two-piece scheme may be excellent design, but the user said one thing and the team is shipping two. Worth a flag.

**Recommend:** include the two-piece L15 scheme in the spec-phase user checkpoint, framed as: *"You asked for 'a prompt injection'. The team proposes two — a short always-on baseline plus a fuller once-per-agent-on-first-read context. Approve the two-piece, or do you want the simpler single-injection?"*

### 1.7 §"What we want" #5 — Settings UI and configuration reference (#23)

| Vision claim | Status | Note |
|---|---|---|
| `/settings` TUI screen exposing user-facing keys per #23 | `[OK]` | Direct from #23. |
| `docs/configuration.md` reference page | `[OK]` | Direct from #23. |
| "settings button at the bottom of the chat UI per #24" | `[OK]` | User's #24 wording. |
| "workflow button surface (per #24)…distinguishing where each came from" | `[INFER, mild]` | User said "workflow button can show all 3". User did not specify the "distinguishing where each came from" UX detail, but it is the natural reading of "show all 3" and is hard to dispute. |

**Wording check (rule #7 in my charter):** User said "settings **button** in the bottom" (#24) and "settings **window**" / "`/settings`" (#23). Vision combines as "TUI screen (or 'settings button at the bottom')". These are *probably* the same thing (a button at the bottom that opens a screen) but the team should not ship a screen accessible only by typing `/settings` and ignore the bottom button. Both surfaces should exist.

**Recommend:** spec must call out **both** the bottom button and `/settings` command as access paths to the settings UI.

### 1.8 §"What we want" #6 — Workflow artifact directories

User said: *"workflow eng has an artifact dir from setup that is added to agents"*

Vision: faithful expansion. `[OK]`.

**Note:** this is one of the more underspecified asks. "Artifact dir from setup" leaves open: (a) is it one dir per workflow run, or one per phase? (b) Does "added to agents" mean injected into prompt, or just made discoverable via env var? (c) Where on disk? — these are mechanism choices the team will make, but the user should sanity-check the design before implementation. Recommend a checkpoint.

### 1.9 §"What we want" #7 — Selective integration with abast

> "The abast/claudechic fork has diverged…we want to: selectively pull useful features…"

`[SCOPE-ADD] / [INFER]`. **The user has not mentioned abast in this run's kickoff or in any of Q1–Q4.** The user's only kickoff was *"see issue24 vision.md as we are picking up from another team."* Q3 ("adopt") referred to **three specific commits** that the team had teed up; the user did not endorse the broader "selective integration with abast" deliverable.

The "we are picking up from another team" framing is the closest user signal. It can be read as implicit endorsement of the prior team's framing, including abast integration. But it can also be read narrowly as "use the prior team's vision document; pick up where they left off on whatever overlaps with #24." The user did not say "and also do the abast convergence work."

**This is the largest scope question in the audit.** Two interpretations:

- **Strict:** Issues #23 and #24 do not mention abast. The user has not asked for abast convergence in this run. The L16 cherry-picks (which the user adopted via Q3) are a narrow scope: pull six specific commits. The vision §7 deliverable is broader than that ("not pull /fast", "coordinate with abast on convergence", "abast is not surprised"). The broader deliverable is scope creep.
- **Permissive:** The user said "we are picking up from another team." The prior team's vision included abast integration. By approving "vision.md" the user implicitly approved §7.

**Recommend:** ask the user to confirm scope. *"Vision §7 says we will (a) pull the L16-decided cherry-picks, (b) defer /fast to #25, (c) coordinate with abast so they aren't surprised. Items (a) and (b) you've adopted. Item (c) — coordinating with abast on the cross-fork layout convergence — is an active piece of work. Is (c) in scope this run, or only (a) and (b)?"*

### 1.10 §"Success looks like"

| Item | Status | Note |
|---|---|---|
| User can put files in `~/.claudechic/workflows/foo/` to override package's `foo`; project beats user beats package; same for rules/hints/MCP tools | `[OK]` | Direct from user "everything in 3 levels…priority c > b > a". |
| User can edit per-user config in `/settings` UI…per-project config… | `[INFER]` | User said "settings button" (#24) and "settings window" (#23). User did not explicitly say "user config edits via /settings, project config edits via /settings". Whether the settings UI edits both tiers in a single panel or only one tier is a design call. |
| Boundary holds in CI (automated test catches violations) | `[INFER]` | User did not ask for CI enforcement. Defensible (L3 can't hold without enforcement) but not user-spoken. |
| Agent's first message contains short statement + first-read fuller context | `[STRETCH]` | Two-piece L15 (see §1.6); user said one injection. |
| `/settings` exposes #23's keys; `docs/configuration.md` documents config surface | `[OK]` | Direct from #23. |
| Issue #23 and #24 can be closed | `[OK]` | The motivating goal. |
| "abast's selected commits are in our tree…abast is not surprised" | `[SCOPE-ADD]` | See §1.9. User has not endorsed "abast not surprised" as a success criterion. |
| Spec is executable without reading recommendation/lens evaluations | `[INFER]` | L14, prior-team. User has not addressed. Defensible quality bar. |

### 1.11 §"Failure looks like"

Mostly `[OK]`. One flag: *"The artifact dir mechanism is so awkward that workflow authors avoid it"* is a quality bar the user did not state, but it's a reasonable inference from "workflow eng has an artifact dir from setup that is added to agents" — if it's awkward, it isn't really "added to agents."

### 1.12 §"Locked constraints" L1–L17

All inherited from prior team. None except A2 and A3 trace to direct user words in this run. Per A1, the team is allowed to surface mistakes; this audit treats L1–L17 as binding for spec/impl unless the user says otherwise, but flags that several of them (L8 especially) sit on thin user signal.

| Lock | User-words support | Note |
|---|---|---|
| L1 (no mrocklin) | None this run; inherited | OK; user has previously said upstream is out of scope. |
| L2 (selective abast) | None this run; inherited | Tied to §1.9 scope question. |
| L3 (never write `.claude/`) | None this run; inferred from "everything in .claudechic" | Ambiguous strength — see §1.5. |
| L4 (Settings vs Config) | None this run; inferred | User used "settings button" / "settings window"; never said "config" terminologically distinct. Cosmetic. |
| L5 (one `.claudechic/` at repo root, replaces `.claudechic.yaml`) | Inferred from "all have .claudechic folder" | OK reading. |
| L6 (`~/.claudechic/`, not XDG) | None | Path choice not user-discussed. |
| L7 (each tier: `workflows/`, `global/{rules,hints}.yaml`, `mcp_tools/`) | Maps to user's three-bucket list | OK reading; "rules and hints" pairing preserved. |
| **L8** (config keys 2-tier; no package config) | **Contradicts** "everything in 3 levels" | **`[DRIFT]`** — see §1.4. |
| L9 (`analytics.id` user-tier) | None | Resolves prior-run UQ5 (per-project analytics.id concern). User has not seen the resolution. |
| L10 (4 senses of lost work) | None this run | Inherited skeptic discipline. |
| L11 (abast cooperation available) | None this run | Tied to §1.9 scope question. |
| L12 (no `/fast` this run) | Adjacent — Q3 covered three commits, not `/fast` | OK; user has previously deferred `/fast` to #25. |
| L13 (no time estimates) | None this run | Inherited; harmless. |
| L14 (spec strictly operational) | None this run | Inherited quality bar. See §5. |
| L15 (two-piece agent awareness) | User said "a prompt injection" (singular) | **`[STRETCH]`** — see §1.6. |
| L16 (cherry-pick selection) | Q3 = "adopt" covers the three UX commits | OK after A2; see §4. |
| L17 (no migration logic) | None this run | OK — claudechic users are user + abast; both can move files manually. |

### 1.13 §"File-move inventory"

`[OK]` as factual data. Caveat: the inventory was produced by the prior team. A1 grants license to surface errors; the implementer/tester should re-validate against current HEAD (`317f424`) before relying on it.

---

## 2. Issue #23 and #24 deliverable coverage

### 2.1 Issue #23 deliverable coverage

| #23 ask | Vision coverage | Status |
|---|---|---|
| `/settings` TUI screen | §5 explicitly | `[OK]` |
| Welcome-screen accessibility (#21 cross-link) | Not mentioned | **`[GAP]`** — #23 says "accessible via `/settings` or welcome screen" and links to #21. Vision says "TUI screen (or settings button at the bottom)". Welcome-screen access is unaddressed. |
| Specific keys to **expose**: `default_permission_mode`, `show_message_metadata`, `vi-mode`, `recent-tools-expanded`, `worktree.path_template`, `analytics.enabled`, `logging.file`, `logging.notify-level`, `themes` | "issue #23 enumerates which keys to expose" | `[OK]` (delegates to #23 — ensure spec inherits this list verbatim) |
| Keys to **hide**: `analytics.id`, `experimental` | "issue #23 enumerates…which to keep internal (`analytics.id`, `experimental.*`)" | `[OK]` |
| Project config keys: `guardrails`, `hints`, `disabled_workflows`, `disabled_ids` | Mentioned at §"What we want" #2 | `[OK]` |
| `disabled_workflows` with **workflow ID discovery** (per #23) | Not mentioned in vision | **`[GAP]`** — UX detail #23 specifies. Spec must include. |
| `disabled_ids` with **available ID listing** (per #23) | Not mentioned in vision | **`[GAP]`** — same. |
| Env vars listed in #23 (`CLAUDECHIC_REMOTE_PORT`, `CHIC_PROFILE`, `CHIC_SAMPLE_THRESHOLD`, `CLAUDE_AGENT_NAME`, `CLAUDE_AGENT_ROLE`, `CLAUDECHIC_APP_PID`, `ANTHROPIC_BASE_URL`) — to be documented in `docs/configuration.md` | "every config key, every environment variable, and every CLI flag" — generic | `[OK]` (delegates) |
| `docs/configuration.md` page | §5 explicitly | `[OK]` |

### 2.2 Issue #24 deliverable coverage

| #24 ask (verbatim) | Vision coverage | Status |
|---|---|---|
| "everything to be in 3 levels (a/b/c, c>b>a)" | §"What we want" #1 | `[OK]` for content; `[DRIFT]` for config — see §1.4 |
| "all have .claudechic folder with workflows / rules and hints / mcp_tools" | L7 | `[OK]` |
| "workflow button can show all 3" | §5 | `[OK]` |
| "workflow eng has an artifact dir from setup that is added to agents" | §"What we want" #6 | `[OK]` |
| "We want a prompt injection telling agents about claudechic" | §"What we want" #4 + L15 | `[OK]` for the ask; `[STRETCH]` for the two-piece elaboration |
| "settings button in the bottom" | §5 ("settings button at the bottom of the chat UI per #24") | `[OK]` (with wording flag — see §1.7) |

### 2.3 Things in the vision NOT in #23 or #24

| Deliverable | Source | Status |
|---|---|---|
| L3 absolute boundary ("never write inside `.claude/`") | Prior team (D5) | `[INFER]` — see §1.5 |
| L4 "Settings"/"Config" terminology distinction | Prior team (D16) | `[INFER]` — cosmetic |
| L8 2-tier config carve-out | Prior team (D17) | `[DRIFT]` — see §1.4 |
| Selective abast integration as a deliverable | Prior team | `[SCOPE-ADD]` — see §1.9 |
| Boundary CI test | Prior team failure-mode | `[INFER]` |
| L14 spec/appendix separation | Prior team failure-mode | `[INFER]` — quality bar |
| L17 no migration logic | Prior team | `[INFER]` |

### 2.4 Things in #23 / #24 that the vision under-specifies

- `/settings` welcome-screen accessibility (#23 cross-links #21).
- `disabled_workflows` ID discovery UX (#23).
- `disabled_ids` available-ID listing UX (#23).

These need to land in the spec.

---

## 3. A3 user-intent verification

**User's exact words (Q4):** *"for #4 it needs to mirror the .claude/rule behavior"*

**A3's interpretation:** *"The mechanism for surfacing claudechic context to agents must mirror Claude Code's `.claude/rules/` behavior — file-based, auto-loaded, treated by the agent as rule-equivalent context. The two-piece L15 semantics still apply…but the *delivery mechanism* should look-and-feel like `.claude/rules/` from the agent's perspective."*

**Audit:**

The Coordinator's interpretation is **plausible but not the only reading**. Three candidate readings:

1. **Behavioral mirror (Coordinator's reading):** mechanism must be file-based + auto-loaded, like `.claude/rules/`.
2. **Effect mirror:** the *effect on the agent* should be the same as `.claude/rules/` (rule-equivalent context, auto-applied), but the mechanism could be a hook, a system-prompt preset, an `append_system_prompt`, etc. — any approach where the agent treats the content as rules.
3. **Look-and-feel for the user, not the agent:** user should be able to author a folder of files that gets treated like rules, like the user authors `.claude/rules/` today. The agent doesn't need to know.

The Coordinator picked (1)+(3). Reading (2) is also defensible.

**Tension with L3:** A3 + L3 together are constraining. Mirroring `.claude/rules/` *as a mechanism* means a directory of markdown files that Claude auto-loads. But Claude's auto-load is rooted in `.claude/rules/`. To mirror it without writing to `.claude/`, the team must either:

- (a) Use Claude Code's settings to point at a non-`.claude/` directory (if such a setting exists).
- (b) Use SDK extension points (system prompt preset, append_system_prompt, hooks) that mirror the *behavior* but not the *file-location convention*.
- (c) Write a single pointer file into `.claude/` that loads from `.claudechic/` (violates L3).
- (d) Have claudechic *read* `.claudechic/` and *inject* the content via the SDK on session start (mirrors behavior, not mechanism).

If Claude Code provides no extension point that allows loading a directory of files as rules from outside `.claude/`, then A3-as-mechanism is not implementable under L3. The team should sanity-check this before A3 becomes a hard lock.

**Recommend:**

1. Ask the user to confirm reading. Phrase: *"You said 'mirror the .claude/rule behavior'. We're reading this as 'a folder of files that Claude auto-loads as rules, just located outside .claude/'. Alternative reading: 'whatever mechanism, but the agent should treat the content as rule-equivalent.' Which do you mean?"*
2. Before A3 becomes a binding spec input, the team should confirm Claude Code has an extension point that lets `.claudechic/`-located files be auto-loaded as rules without writing to `.claude/`. If not, A3-as-mechanism conflicts with L3 and one must yield.

This is also a **missing user checkpoint** (see §6).

---

## 4. Q3 user-intent verification

**User's exact word (Q3):** *"adopt"*

**Coordinator's interpretation:** all three "UX-decision-required" commits are pulled — `f9c9418` (full model ID + loosened validation), `5700ef5` (default to `auto` permission mode), `7e30a53` (add `auto` to Shift+Tab cycle).

**Audit:**

The user was shown a table of three commits with descriptions and asked to disposition them. "Adopt" is a clean signal **for the set as presented**. Coordinator's mapping is faithful.

**However**, two of the three commits have non-trivial downstream UX implications the user may not have fully grokked from the one-line descriptions:

- **`5700ef5` (default to `auto` permission mode on startup)** — this changes the default behavior every time claudechic starts. Today's default is `default` (per-tool permission prompts); the new default would be `auto` (auto-approve safe tools, prompt only for risky ones). For users who are conservative about permissions, this is a meaningful behavior change. The user said "adopt" once; they may not have weighed this specifically.
- **`f9c9418` (full model ID + loosened validation)** — changes how model strings are validated. Loosened validation means typos that were rejected today may now silently succeed (or vice versa). Worth confirming the user wanted this loosening, not just the "full model ID" feature.

`7e30a53` is bundled with `5700ef5` and is mechanically necessary if `5700ef5` is pulled — no separate user signal needed.

**Recommend:** before the cherry-pick is executed, surface a one-line confirmation to the user: *"Pulling `5700ef5` makes 'auto' the default permission mode on every startup — this changes today's per-tool prompt behavior. Confirming this is the intended UX?"* Treat the cherry-pick execution as an implicit user checkpoint.

---

## 5. L14 audit

**L14:** "Spec documents are strictly operational (Implementer + Tester can execute without reading anything else). Rationale, decisions, rejected paths, and reversal triggers go in a separate appendix file. Recommendation/deliberation documents and spec documents are different files for different audiences. The grading rubric must enforce this."

**Concrete signal that this run is or isn't honoring L14:**

- **No spec exists yet** (current phase = Leadership). L14 cannot be violated by the vision (vision is by definition strategy + rationale, not spec).
- **The four leadership lens documents** that will land this phase are *not* specs by intent; they're analysis. Mixing rationale into them is fine.
- **Risk vector:** when the Specification phase begins, the team must produce two artifacts per spec area (spec + appendix), not one. The grading rubric must be defined **before** the spec is written, not after — otherwise the "rationale leakage" anti-pattern from the prior run repeats.

**What an Implementer needs to be able to execute the spec without context:**

- Concrete file paths (where to create, where to edit, where to delete).
- Concrete code-level instructions (which functions to add, which to refactor, with signatures).
- Concrete test instructions (what to assert, which test files).
- Acceptance criteria (when is each piece done).
- **Not** rationale, **not** rejected paths, **not** "we considered X but chose Y because Z."

**Concrete recommendations:**

1. **Define the spec/appendix template before specification phase opens.** A two-file template per spec area (`<area>_spec.md` + `<area>_appendix.md`) with explicit headers in each. The spec contains only operational sections; the appendix contains rationale, rejected paths, reversal triggers.
2. **Grading rubric must include a "rationale leak" check** — a Tester reading only the spec must confirm: "I could execute this without reading anything else" (yes/no).
3. **The vision document itself is appendix-shaped** — it explains why, not how. That's appropriate. The team should not feel pressure to make `vision.md` operational; it isn't supposed to be.

L14 is currently honored by virtue of no spec existing. The risk is at the boundary into specification phase. Recommend the Coordinator add a Specification-phase entry condition: *"Two-file template defined; grading rubric includes rationale-leak check; rubric ratified before any spec author starts writing."*

---

## 6. Gaps — what user wanted, no deliverable; deliverables not user-asked

### 6.1 User wanted; no deliverable yet

| User ask | Coverage status | Severity |
|---|---|---|
| `/settings` accessible from welcome screen (per #23 + #21) | Not mentioned in vision | `[GAP]` — moderate |
| `disabled_workflows` UX with workflow ID discovery (#23) | Not mentioned | `[GAP]` — minor (UX detail) |
| `disabled_ids` UX with available-ID listing (#23) | Not mentioned | `[GAP]` — minor |
| Env vars surfaced in `docs/configuration.md` (specific list in #23) | Implicit only | `[GAP]` — minor (delegated to spec) |
| Settings **button in the bottom** as a UI surface (distinct from `/settings` command) | Mentioned alongside `/settings` but treated as alternates | `[GAP]` — verify both exist in spec |

### 6.2 In deliverable list; user did not ask

| Deliverable | User signal | Severity |
|---|---|---|
| L3 absolute boundary on `.claude/` writes | Inferred from "everything in .claudechic" | `[INFER]` — defensible but worth confirming |
| L4 "Settings" / "Config" terminology distinction | None | `[INFER]` — cosmetic, low risk |
| L8 2-tier config carve-out (no package config) | Contradicts "everything in 3 levels" | **`[DRIFT]`** — needs explicit user adjudication |
| Selective abast integration as a primary deliverable (vision §7) | None this run; "we are picking up from another team" is the closest signal | `[SCOPE-ADD]` — needs explicit confirmation |
| Two-piece L15 agent awareness | User said "a prompt injection" (singular) | `[STRETCH]` — confirm |
| Boundary CI test | None | `[INFER]` — sensible but not asked |
| L14 spec/appendix separation enforced via grading rubric | None | `[INFER]` — quality bar |
| `analytics.id` at user-tier (L9) | None | `[INFER]` — resolves prior-run question; user has not seen resolution |

---

## 7. Missing user checkpoints

The phase list shows `*` checkpoints at vision/spec/impl/test/signoff. The following sub-decisions inside phases should also be user checkpoints:

| Sub-decision | Phase | Why a checkpoint |
|---|---|---|
| **L8 — config 2-tier vs 3-tier** | Specification | Direct contradiction with user's "everything in 3 levels". Explicit yes/no needed. |
| **A3 mechanism choice** (which extension point delivers the rule-equivalent behavior under L3) | Specification | Mechanism is hard given L3 + A3 together; user should see the chosen mechanism and confirm it matches "mirror the .claude/rule behavior". |
| **L15 two-piece vs single injection** | Specification | User said singular; team is shipping plural. |
| **Vision §7 abast scope** (cherry-picks only vs full convergence coordination) | Specification | The "coordinate with abast" deliverable is not in #23 / #24. Explicit yes/no needed. |
| **Cherry-pick execution moment, especially `5700ef5`** (default permission mode change) | Implementation | One-line confirmation before the auto-default UX change lands. |
| **Artifact-dir mechanism** (location, scope per workflow run vs per phase, surfacing mechanism) | Specification | User's ask is terse; design space is wide; UX surface (does the user see artifact dirs in the file tree?) matters. |
| **L3 strength check** (absolute prohibition vs primary-state-only) | Specification | Affects A3's feasibility. Worth one user sentence. |

**Recommend:** Coordinator should batch these into a single user-question batch at the start of the Specification phase, **before** spec authors begin writing. Asking after the spec is written wastes work.

---

## 8. Summary — drift findings by severity

### High severity (block / require explicit user adjudication before spec)

1. **L8 config 2-tier carve-out vs user's "everything in 3 levels"** (§1.4). Direct contradiction in user's own words. Resolution: ask the user.
2. **Vision §7 / L11 abast convergence as a deliverable** (§1.9). User has not endorsed beyond the L16 cherry-picks. Resolution: ask the user whether "coordinate with abast" is in scope.

### Medium severity (flag for user; team can proceed if user agrees)

3. **L15 two-piece agent awareness vs user's "a prompt injection"** (§1.6). User said one; team plans two. Resolution: surface for approval.
4. **A3 mechanism interpretation** (§3). Coordinator chose one of three plausible readings of "mirror the .claude/rule behavior". Resolution: ask the user to confirm.
5. **L3 strength** (§1.5). Absolute boundary vs primary-state-only. Affects A3 feasibility.
6. **Q3 cherry-pick `5700ef5` UX implication** (§4). User said "adopt" — but the auto-default-permission-mode change is a meaningful UX shift. Resolution: confirmation at execution moment.

### Low severity (gap to fill in spec; no user check needed unless team wants one)

7. `/settings` welcome-screen accessibility per #23+#21 — close in spec.
8. `disabled_workflows` ID discovery UX — close in spec.
9. `disabled_ids` listing UX — close in spec.
10. Settings *button* vs `/settings` *command* — verify both surfaces ship.

### Verify-only (sound but inferred)

- L3, L4, L6, L7, L9, L10, L13, L14, L17 — all reasonable inferences from prior team's work, but not user-spoken this run. Per A1 the team can proceed; flag if any becomes load-bearing.

---

## 9. Lens recommendation summary

The vision faithfully covers the explicit asks in #23 and #24 plus the user's Q1–Q4 amendments. **No user-asked feature is being dropped.** The risks are at the edges:

- Two **drift** items (L8, vision §7) where the team is shipping more or different than the user said.
- Three **stretch** items (L15, A3 mechanism, L3 strength) where the team is interpreting thin user signal liberally.
- Several minor **gaps** in #23 UX detail to close in the spec.
- L14 is not yet violated and won't be unless the team enters spec phase without a two-file template + rubric.

**One alignment-protective action stands out:** before the Specification phase exits its setup, the Coordinator should run a single user-question batch covering items 1–5 in §8. This costs one user round-trip and prevents writing a spec that the user later rejects on grounds the team could have asked about in advance.

---

*End of alignment audit.*
