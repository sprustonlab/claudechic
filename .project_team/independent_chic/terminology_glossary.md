# Terminology Glossary — independent_chic

**Author:** TerminologyGuardian (Leadership lens)
**Phase:** Leadership
**Anchored to:** `vision.md` §"Goal" / §"What we want" / §"Locked constraints" L1–L17; `STATUS.md` A1, A2, A3.
**Audience:** Composability, Skeptic, UserAlignment, the Specification phase (Implementer + Tester downstream), and any new contributor reading the spec cold.
**Status:** Reference material. This is **not** the spec (per L14). The spec consumes these definitions; it does not duplicate them.

---

## 0. How to read this glossary

Each entry has four fields:

- **Canonical form** — the exact phrase to use in spec, docs, code symbols, and UI prose.
- **Definition** — what it means.
- **Anti-definition** — what it does **not** mean. The most common confusion the term has historically caused.
- **Where it appears** — concrete sites in code (`*.py`), data (`*.yaml`), UI (TUI labels, toasts, status bar), prose (`docs/`, `CLAUDE.md`, prompts), or the workflow itself (vision/STATUS/spec).

When two terms have appeared in the codebase or the prior run for the same concept, the entry lists the alternates under **Retired alternates** and the spec must use the canonical form going forward. No code-symbol renames are forced (L4); rename pressure applies to user-visible prose, new code, and new doc surfaces.

The glossary is organized by topic, not alphabetically, because related terms only make sense together.

---

## 1. Tier vocabulary (the 3-tier override system)

### 1.1. tier

- **Canonical form:** **tier**
- **Definition:** One of the three layers at which content (workflows, rules, hints, MCP tools) can be defined. The three tiers are **package tier**, **user tier**, and **project tier**, in increasing order of priority. When the same content is defined at more than one tier, the higher-priority tier wins.
- **Anti-definition:** Not "level" (overloaded with guardrail enforcement levels: `deny`/`warn`/`log`). Not "layer" (overloaded with software-architecture layering). Not "scope" (overloaded with rule-scoping by role/phase). Not a synonym for "namespace" (which is the YAML `namespace:bare_id` qualifier).
- **Where it appears:** `vision.md` §"Three-tier override system"; spec; loader docstring; `docs/configuration.md`; the workflow-picker UI label that distinguishes workflow origin (per #24).

### 1.2. package tier

- **Canonical form:** **package tier**
- **Definition:** The lowest-priority tier. Content shipped inside the installed `claudechic` Python package, available everywhere claudechic is installed. Lives under `claudechic/defaults/...` (per L7). Equivalent to "fallback defaults the package always provides."
- **Anti-definition:** Not "global tier" (the prior run used "global" for the `~/.claude/.claudechic.yaml` file, which is now retired). Not "default tier" — "default" is the *role* of this tier, not its name; calling it the "default tier" creates ambiguity with `default_permission_mode` and with abast's `claudechic/defaults/` namespace word. Not synonymous with `claudechic/defaults/` the *directory* (the directory is the **storage location**; the tier is the **resolution layer**).
- **Where it appears:** `claudechic/defaults/workflows/`, `claudechic/defaults/global/{rules,hints}.yaml`, `claudechic/defaults/mcp_tools/`; loader resolution code; `docs/configuration.md`; spec.
- **Retired alternates:** "global tier" (old meaning), "bundled tier", "builtin tier", "default tier" — none survive into the spec.

### 1.3. user tier

- **Canonical form:** **user tier**
- **Definition:** The middle-priority tier. Content placed under `~/.claudechic/...` (per L6). Applies across every project that user works in. Beats package tier; loses to project tier.
- **Anti-definition:** Not "global tier" (retired — historically meant `~/.claude/.claudechic.yaml`, which is exactly what user tier replaces, but the *term* "global" is being retired to avoid carrying forward the wrong namespace). Not "home tier" (colloquial; non-standard). Not "machine tier" — different machines may share a home directory (NFS), and conversely a single machine may have multiple users.
- **Where it appears:** `~/.claudechic/workflows/`, `~/.claudechic/global/{rules,hints}.yaml`, `~/.claudechic/mcp_tools/`, `~/.claudechic/config.yaml`; spec; settings UI labels ("user-level"); `docs/configuration.md`.
- **Retired alternates:** "global config", "home config", "user-global tier".

### 1.4. project tier

- **Canonical form:** **project tier**
- **Definition:** The highest-priority tier. Content placed under `<launched_repo>/.claudechic/...` (per L5). Applies only inside the project where it lives. Beats user tier and package tier.
- **Anti-definition:** Not "repo tier" (claudechic itself is also a repo; "repo tier" creates ambiguity). Not "local tier" (overloaded with "local settings" in `features/worktree/git.py`). Not "per-project config" — that phrase is the *2-tier config* meaning (see §3.4); "project tier" is the *3-tier content* meaning. Not "workspace tier".
- **Where it appears:** `<launched_repo>/.claudechic/workflows/`, `<launched_repo>/.claudechic/global/{rules,hints}.yaml`, `<launched_repo>/.claudechic/mcp_tools/`, `<launched_repo>/.claudechic/config.yaml`; spec; settings UI labels ("project-level"); workflow-picker badges.

### 1.5. content (vs config)

- **Canonical form:** **content**
- **Definition:** The four categories that participate in the 3-tier override system: **workflows**, **rules**, **hints**, and **MCP tools**. Files that define behaviour an agent or the engine consumes (YAML manifests, role-identity Markdown, phase Markdown, MCP tool scripts).
- **Anti-definition:** Not "configuration" — config keys (§3.4) live in a separate 2-tier system. Not "settings" (umbrella user-facing word, §3.1). Not "data" (overloaded). Not the body of a workflow YAML manifest's `phases:` list — that's a *manifest section*, not "content" in this sense.
- **Where it appears:** spec §"3-tier system"; loader code; `vision.md` §"What we want" item 1.

### 1.6. override

- **Canonical form:** **override** (verb and noun)
- **Definition:** When the same logical item (a workflow named `tutorial`, a rule with id `global:no-rm-rf`, a hint with id `global:context-docs-outdated`, an MCP tool named `cluster_dispatch`) is defined at multiple tiers, the higher-priority tier's definition is used in place of the lower-priority tier's. The lower-priority definition is said to be **overridden**; the higher-priority definition is the **override**.
- **Anti-definition:** Not "merge" (§1.7). Not "shadow" (a near-synonym used inconsistently in some loader prose; retire). Not the guardrail concept of `request_override()` / `consume_override` callback — that is a *one-time authorization token* for a `deny` rule, totally unrelated to tier resolution. **The spec must disambiguate "tier override" from "guardrail override" everywhere both appear in the same paragraph.**
- **Where it appears:** loader resolution code; spec §"Override resolution"; `docs/configuration.md`.

### 1.7. merge

- **Canonical form:** **merge**
- **Definition:** Reserved for future loader semantics where the team decides that a given content category combines (rather than replaces) across tiers. The default semantics are **override** (§1.6); merge is opt-in and category-specific. As of this glossary, the team has not committed to any merge semantics; the spec must explicitly state per-category whether each is override-only or merge-capable.
- **Anti-definition:** Not "git merge" (the cross-fork integration is "selective integration" / "cherry-pick", §6). Not "override" (the default). Not "concatenate" (one possible merge semantic among several).
- **Where it appears:** spec §"Override resolution" (open question to be answered there); loader code if and where merge is implemented.
- **Risk:** "Merge" is the most overloaded word in the run (git merge, content merge, dict merge, manifest merge). When the spec uses it, it must always be qualified: "tier merge" vs "git merge".

### 1.8. shadow / fallback

- **Canonical form:** **fallback** (preferred); avoid **shadow**.
- **Definition:** **Fallback** is the loader's behaviour when content is *not* defined at a higher tier — it falls back to the next-lower tier's definition, ultimately to the package tier. "Fallback discovery" is abast's term (commit `8e46bca`) for the loader walking multiple paths in priority order; sprustonlab adopts the same term.
- **Anti-definition:** "Shadow" (as in "the user-tier file shadows the package-tier file") is a synonym for **override** (§1.6) used inconsistently in some prose. **Retire "shadow"** — use "override" for the act of replacing, "fallback" for the act of not finding and going lower.
- **Where it appears:** loader code (`fallback_discovery` function name from abast's `8e46bca`, kept on import); spec; `docs/configuration.md`.

### 1.9. tier-unique content

- **Canonical form:** **tier-unique content**
- **Definition:** Content defined at one tier and not at any other. The loader makes it available regardless of the absence at other tiers — it does not require all three tiers to define an item. The user tier can define a workflow that the package does not ship; the project tier can define a rule unique to that project.
- **Anti-definition:** Not "missing" (the lower tiers don't have a hole; they simply don't define this item). Not "exclusive" (suggests "only this tier may use it" — wrong; tier-unique means "only this tier *defines* it, but anyone can consume it").
- **Where it appears:** spec §"Override resolution"; loader code (the resolution walk must distinguish "lower tier defines it differently → override" from "lower tier doesn't know about it → tier-unique").

---

## 2. Boundary vocabulary (the `.claude/` vs `.claudechic/` separation)

### 2.1. `.claude/` namespace

- **Canonical form:** **`.claude/` namespace** (or **Claude Code's namespace**, **Claude's namespace** in prose)
- **Definition:** Every directory or file named `.claude` (in any location: `~/.claude/`, `<launched_repo>/.claude/`, `<worktree>/.claude/`) belongs to Claude Code / Anthropic tooling. claudechic *reads* from this namespace where Claude's contract permits (`~/.claude/settings.json`, `~/.claude/projects/`, `~/.claude/history.jsonl`, `~/.claude/.credentials.json`, `<repo>/.claude/commands/`, `<repo>/.claude/skills/`, `~/.claude/plans/`, and Claude's `<repo>/.claude/rules/`). claudechic **never writes** to this namespace (L3, hard constraint).
- **Anti-definition:** Not "Claude settings" (overloaded — see §3.2). Not synonymous with `~/.claude/settings.json` (which is one file inside the namespace). Not the full set of files Claude Code interacts with (Claude reads from the OS, the network, the filesystem; the `.claude/` namespace is specifically the tree it owns on disk).
- **Where it appears:** vision.md §"The boundary"; spec §"L3 enforcement"; `docs/configuration.md`; CI boundary test.

### 2.2. `.claudechic/` namespace

- **Canonical form:** **`.claudechic/` namespace**
- **Definition:** Every directory named `.claudechic` (at `~/.claudechic/` for user tier, at `<launched_repo>/.claudechic/` for project tier) belongs to claudechic. claudechic creates, reads, and modifies files inside this namespace. The package tier is stored *inside the package* under `claudechic/defaults/...` (not in any `.claudechic/` directory); the namespace word "claudechic" applies only to the user and project tiers' on-disk locations.
- **Anti-definition:** Not "the `.claudechic.yaml` file" (retired, L5: replaced by `.claudechic/config.yaml`). Not the package source directory `claudechic/` (the leading dot matters). Not the package tier's storage path `claudechic/defaults/...` (different location, different ownership: package source vs user/project on-disk state).
- **Where it appears:** vision.md §"The boundary"; spec; `docs/configuration.md`; CI boundary test (must assert no claudechic write outside this namespace).
- **Sub-paths under `.claudechic/`:** `workflows/`, `global/{rules,hints}.yaml`, `mcp_tools/`, `config.yaml`, plus per-project state (`hints_state.json`, `phase_context.md`, possibly `rules/` for the A3 mirror — see §4.3).

### 2.3. rules (Claude's) vs `rules.yaml` (claudechic's)

This is the single most dangerous overload in the codebase. Two distinct concepts share the word "rules":

#### 2.3a. Claude rules

- **Canonical form:** **Claude rules** (in prose); the path is **`.claude/rules/`**.
- **Definition:** Markdown files inside any `.claude/rules/` directory that Claude Code auto-loads as part of an agent's context. Claude owns this directory; claudechic must not write to it (L3). Claude treats each file as standing context the agent always sees.
- **Anti-definition:** Not the same as guardrail rules (§2.3b). Not the same as workflow rules. Not configuration. Not enforced — they are *context*, not *gates*.
- **Where it appears:** under `~/.claude/rules/` and `<repo>/.claude/rules/`; consumed by Claude Code, not by claudechic; referenced in `vision.md` §"Agent awareness" and §A3 (the mirror requirement).

#### 2.3b. guardrail rules

- **Canonical form:** **guardrail rules** (in prose); **`Rule`** (in code: the dataclass in `claudechic/guardrails/rules.py`); the file is **`rules.yaml`**.
- **Definition:** YAML-defined enforcement rules that intercept tool calls via a `PreToolUse` hook. Each rule has a level (`deny`/`warn`/`log`), a trigger (`PreToolUse/<Tool>`), a detect pattern, and optional scoping (roles, phases, exclude). Defined in `<tier>/global/rules.yaml` (always-active) or in `<tier>/workflows/<wf>/<wf>.yaml` under a `rules:` section (workflow-scoped).
- **Anti-definition:** Not Claude rules (§2.3a). Not "guardrails" the directory — `claudechic/guardrails/` is the *engine package* that evaluates rules; the rules themselves live in YAML manifests. Not "always-active rules" (a *category* of guardrail rules, not a synonym).
- **Where it appears:** `claudechic/guardrails/rules.py`; `<tier>/global/rules.yaml`; workflow YAML `rules:` sections; spec; `docs/configuration.md`.

#### 2.3c. The disambiguation rule

- **Spec must say "Claude rules" or "guardrail rules" — never bare "rules"** in any sentence where both could be referenced. In sections that are unambiguously about one or the other (e.g., the guardrail engine docs), bare "rules" is acceptable after the section's first qualified mention.
- **The path `.claude/rules/` is for Claude rules.** The path `<tier>/global/rules.yaml` is for guardrail rules. They never share storage.

### 2.4. context docs vs guardrail rules vs hints

These are three different ways claudechic surfaces information to agents/users. They are systematically confused; the spec must keep them apart.

| Term | What it is | Audience | Storage | How it reaches the audience |
|---|---|---|---|---|
| **context doc** | Markdown reference (e.g., `claudechic/context/workflows-system.md`) describing how a claudechic system works. | Agent (read on demand) and human contributor. | `claudechic/context/*.md` (package tier); A3 says these mirror through to a rule-equivalent location agents auto-load. | Today: synced into `<repo>/.claude/rules/` by the `/onboarding` workflow's `context_docs` phase (BF1 violation; must change per L3). Future (per A3): mirrored into a claudechic-owned, agent-auto-loaded location (mechanism is open per §"Open mechanism questions" #3). |
| **guardrail rule** | YAML-defined enforcement gate intercepting tool calls. | Agent (enforced at runtime). | `<tier>/global/rules.yaml` or workflow YAML. | `PreToolUse` SDK hook; agent never reads the file. |
| **hint** | Short user-facing nudge (toast). Two patterns: pipeline (YAML) and event-driven (code). | User (visual toast); not the agent. | `<tier>/global/hints.yaml` (pipeline hints) or inline in `app.py` (event-driven). | `app.notify()` toast in the TUI. |

- **Anti-definitions:**
  - A context doc is **not** a rule (Claude or guardrail). It informs; it does not enforce.
  - A guardrail rule is **not** a hint. It blocks/warns/logs; it does not appear in the TUI as a toast (though a hint may be raised when a rule denies).
  - A hint is **not** addressed to the agent. The agent does not see hints; the user sees them. (Exception: event-driven hints inside agent-facing prompts — but these are separately authored.)
- **Where it appears:** spec §"Agent awareness" must distinguish all three; `docs/configuration.md` must keep their config keys separate (`hints.disabled_ids` vs `guardrails.disabled_ids` vs the future A3 context-docs config).

### 2.5. auto-loaded vs injected

A3 turns this distinction load-bearing:

#### 2.5a. auto-loaded

- **Canonical form:** **auto-loaded** (hyphenated). Synonyms in this glossary: **rule-equivalent**, **mirror `.claude/rules/` behaviour**.
- **Definition:** Content that Claude Code reads as standing agent context without any in-session prompt insertion or hook trigger. Claude's `.claude/rules/` is the canonical example: Claude finds the directory, reads the files, makes them part of every agent's context for the session. Per A3, claudechic's per-session and per-first-read awareness *delivery mechanism* must mirror this shape — file-based, discovered by Claude, treated as rule-equivalent — without claudechic writing inside `.claude/` (L3).
- **Anti-definition:** Not "injected" (§2.5b). Not "loaded by claudechic" — the auto-load is performed by Claude Code, not by claudechic; claudechic only places the file at a discoverable path. Not "always-on" — auto-loaded content is on whenever the agent has it in context, but it's not necessarily reasserted at every turn (that would be injection).
- **Where it appears:** spec §"Agent awareness — first-read injection mechanism"; A3 in STATUS.md; `docs/configuration.md`.

#### 2.5b. injected / injection

- **Canonical form:** **injected** (verb), **injection** (noun), **prompt injection** when disambiguation is needed.
- **Definition:** Content inserted into an agent's prompt by claudechic at a specific moment (session start, first read, tool-call augmentation). Distinct from auto-loaded content because injection is an *active* claudechic action (via SDK system-prompt presets, append parameters, hooks, or a guardrail-style `Injection`). The agent receives injected content as part of its message stream or system prompt.
- **Anti-definition:** Not the security term "prompt injection attack" (a malicious external user trying to subvert an agent — different topic; spec should never use the bare phrase "prompt injection" without qualifying which sense).
  - **Disambiguation rule:** for the security sense, use **"prompt-injection attack"** (hyphenated); for the claudechic mechanism, use **"injection"** alone or **"awareness injection"** / **"session-start injection"** / **"first-read injection"**.
- Not the same as guardrail `Injection` (the dataclass in `guardrails/`) — that one mutates `tool_input` in-place before a tool call, also via SDK hook. The terminology overlap is real and the spec must qualify: **"awareness injection"** for L15/A3, **"tool-input injection"** for the guardrail mechanism.
- **Where it appears:** spec §"Agent awareness"; SDK terminology; guardrails code (`Injection` dataclass — keep, but qualify in prose).

### 2.6. session-start injection (the always-on piece)

- **Canonical form:** **session-start injection**
- **Definition:** Per L15 piece 1: a short prompt-level statement (a few sentences) inserted at the start of every claudechic-spawned agent session, conveying baseline awareness — that the agent runs in a TUI, that guardrails may intercept tool calls, that workflows/phases/hints exist, that `.claudechic/` is claudechic-owned and `.claude/` is Claude's. Always fires; does not condition on any file read.
- **Anti-definition:** Not the same as "first-read injection" (§2.7). Not auto-loaded — this is genuinely injected (active insertion at session start). Not "the system prompt" (it may be implemented via system prompt presets, but the canonical term refers to *content at this trigger*, not the SDK mechanism).
- **Where it appears:** spec §"Agent awareness — piece 1"; whatever SDK mechanism the team picks (system prompt preset, append parameter, etc.).

### 2.7. first-read injection (the once-per-agent piece)

- **Canonical form:** **first-read injection**
- **Definition:** Per L15 piece 2: fuller context (claudechic's own documentation about workflows, hints, guardrails, the `.claudechic/` layout) delivered the first time an agent reads a file inside any `.claudechic/` directory. Once per agent-session, never repeated. **Per A3, the *delivery mechanism* must mirror `.claude/rules/` shape** — file-based, agent-auto-loaded, treated as rule-equivalent context — rather than relying purely on a hook that re-fires per read. The "once-per-agent" trigger sits on top of (or replaces) the auto-load semantics, but the agent's experience must feel like reading a rule, not receiving a synthetic nudge.
- **Anti-definition:** Not "per-read injection" (would be noisy; explicitly forbidden by L15). Not "session-start injection" (§2.6 — different timing, different content size). Not synonymous with `.claude/rules/` (which would be an L3 violation; the mechanism mirrors the *behaviour* without writing into `.claude/`).
- **Where it appears:** spec §"Agent awareness — piece 2"; the new A3-mandated mechanism design.

### 2.8. rule-equivalent

- **Canonical form:** **rule-equivalent** (adjective)
- **Definition:** Used by A3 to describe context that the agent treats *as if it were* a `.claude/rules/` file — standing context, auto-loaded, not a synthetic insertion. The first-read-injection content (§2.7) is "rule-equivalent" in that an agent reading it should perceive it the same way it perceives a `.claude/rules/` file.
- **Anti-definition:** Not "a guardrail rule" (§2.3b). Not literally "a Claude rule" (§2.3a — would require writing into `.claude/`, an L3 violation). The qualifier "equivalent" is doing all the work: it captures the *behavioural target* without committing to the storage location.
- **Where it appears:** STATUS.md A3; spec §"Agent awareness"; cross-references in `docs/configuration.md`.

### 2.9. mirror

- **Canonical form:** **mirror** (verb: "mirror `.claude/rules/`")
- **Definition:** A3's verb for "produces the same agent-perceived behaviour as", applied to the relationship between claudechic's auto-loaded directory and Claude's `.claude/rules/`. Mirroring covers behaviour, not storage location: the goal is that the agent treats the mirrored directory as it would a Claude rules directory. The mechanism may differ (a symlink, a Claude Code config redirect, an SDK hook, a registered MCP-served context source — open per §"Open mechanism questions" #3).
- **Anti-definition:** Not "copy" (would mean writing into `.claude/`, L3 violation). Not "fork" (the prior run's word for creating divergent versions). Not "alias".
- **Where it appears:** STATUS.md A3; spec §"Agent awareness — delivery mechanism".

---

## 3. Settings vs Config (L4 surface-vs-internals split)

L4 is binding: **"settings" is the user-facing umbrella, "config" is the technical term.** This section pins exactly where each appears.

### 3.1. settings (user-facing umbrella)

- **Canonical form:** **settings** (lowercase in prose; **Settings** at the start of a sentence or in a UI label)
- **Definition:** The user's word for everything claudechic stores per user or per project that they may want to view or edit. This is the umbrella term in TUI labels, button copy, prose addressed to users, and issue-thread discussion.
- **Anti-definition:** Not "config" (the YAML/dataclass word, §3.3). Not "Claude settings" (§3.2 — Claude's `~/.claude/settings.json` and the broader `.claude/` namespace). Not the guardrail enforcement-level word.
- **Where it appears:**
  - **TUI labels:** the `/settings` slash command, the "Settings" button at the bottom of the chat UI (per #24), the workflow-picker's "Settings" affordance.
  - **Prose:** `vision.md` §"Settings UI", `docs/configuration.md` ("…edit your settings…"), error messages addressed to users ("Could not save your settings.").
  - **Issue text:** sprustonlab/claudechic#23 body (which uses both, inconsistently — the spec aligns to L4).
- **Retired alternates:** "preferences", "options", "configuration UI" (now "Settings UI"), "config screen" (now "settings screen").

### 3.2. Claude settings (the disambiguation case)

- **Canonical form:** **Claude settings** when referring to Claude Code's own `settings.json`; **`.claude/` namespace** when referring to the broader Claude-owned tree (§2.1).
- **Definition:** Claude Code's `~/.claude/settings.json` and related files inside `.claude/` that Claude itself owns. claudechic reads `enabledPlugins` from this file and other Claude-owned data; claudechic never writes to it.
- **Anti-definition:** Not "claudechic settings" (§3.1). Not "config" (§3.3). The qualifier "Claude" is mandatory in any prose where ambiguity is possible.
- **Where it appears:** `claudechic/help_data.py:67` (read site); spec §"L3 boundary"; `docs/configuration.md` ("claudechic does not modify your Claude settings.").

### 3.3. config (technical term)

- **Canonical form:** **config**
- **Definition:** The YAML file format and the Python loader code. Used in code symbols (`config.py`, `CONFIG`, `CONFIG_PATH`, `ProjectConfig`), in YAML filenames (`config.yaml`), in internal docstrings, in code comments, and in log messages addressed to developers.
- **Anti-definition:** Not "settings" (the user-facing word, §3.1). Not "manifest" (manifests are workflow/global YAML files containing `phases:`, `rules:`, `hints:` sections — different category, different loader).
- **Where it appears:**
  - **Code:** `claudechic/config.py`, `ProjectConfig` dataclass, `CONFIG_PATH` constant, `_load()`, `_save()`.
  - **YAML filenames:** `~/.claudechic/config.yaml` (user tier), `<launched_repo>/.claudechic/config.yaml` (project tier).
  - **CLI flags / env vars:** any future `CLAUDECHIC_CONFIG=...` env var or `--config <path>` flag uses "config".
  - **Internal docs:** `claudechic/context/CLAUDE.md`, `claudechic/context/claudechic-overview.md`, `CLAUDE.md` (root).
- **L4 explicitly does not force code-symbol renames.** `ProjectConfig` stays. `CONFIG_PATH` stays. The relocation work (vision.md §"File-move inventory" → `~/.claudechic/config.yaml`) updates the *path string* and the *docstring*, not the symbol name.

### 3.4. config keys (the 2-tier system)

- **Canonical form:** **config key**
- **Definition:** A leaf field in the config YAML (e.g., `analytics.enabled`, `worktree.path_template`, `default_permission_mode`, `themes`, `guardrails`, `hints`, `disabled_workflows`, `disabled_ids`). Config keys participate in a **2-tier** system (user + project) per L8 — *not* the 3-tier system that content uses. There is no `claudechic/defaults/config.yaml` (L8); defaults live in code (`config.py:_load()` setdefaults).
- **Anti-definition:** Not "content" (§1.5 — content is workflows/rules/hints/MCP tools). Not "settings" in the umbrella sense (§3.1 — though users edit config keys *through* the settings UI). The 2-tier vs 3-tier distinction is load-bearing: a contributor seeing "tier" in the spec must be able to tell which tier-system the sentence is about.
- **Where it appears:** `claudechic/config.py`; `~/.claudechic/config.yaml`; `<launched_repo>/.claudechic/config.yaml`; `docs/configuration.md` (the reference page enumerating every key); spec §"Config tier system".
- **User-tier keys (per vision.md §"Two-tier override system for config keys"):** `analytics.id` (L9), `analytics.enabled`, `default_permission_mode`, `themes`, `logging.*`, `worktree.path_template`, `show_message_metadata`, `vi-mode`, `recent-tools-expanded`, `experimental.*`.
- **Project-tier keys:** `guardrails` (bool), `hints` (bool), `disabled_workflows`, `disabled_ids`.

### 3.5. settings UI / settings screen / settings button

- **Canonical form:** **settings UI** (general); **settings screen** (the `/settings` TUI screen — when one is added); **settings button** (per #24, the bottom-of-chat affordance).
- **Definition:** The TUI surface where users edit the user-facing config keys (§3.4). Issue #23 enumerates which keys are exposed and which stay internal (`analytics.id`, `experimental.*` hidden).
- **Anti-definition:** Not "config screen" (the user word is "settings"). Not "preferences" (retired). Not the workflow picker (which is a separate "workflow button" surface per #24).
- **Where it appears:** spec §"Settings UI deliverable"; the `/settings` slash command; `docs/configuration.md` references it.

### 3.6. configuration reference page

- **Canonical form:** **configuration reference page** (in prose); **`docs/configuration.md`** (the path).
- **Definition:** The deliverable that documents every config key, every environment variable, and every CLI flag claudechic responds to. Per issue #23.
- **Anti-definition:** Not "settings reference" — the *file* is reference documentation about config keys (the technical surface), so "configuration" is correct. Note the asymmetry: the **UI** is "Settings"; the **reference document** is "configuration". This is awkward but locked by L4 + the issue body verbatim.
- **Where it appears:** `docs/configuration.md`; spec §"Deliverables".

---

## 4. Agent awareness vocabulary (A3 + L15)

A3 introduced the requirement that the awareness mechanism *mirror `.claude/rules/` behaviour*. The vocabulary below pins the resulting language.

### 4.1. agent awareness

- **Canonical form:** **agent awareness** (the umbrella concept)
- **Definition:** What an agent running inside claudechic understands about its environment — that it's in a TUI with guardrails, that workflows and phases exist, that hints are user-facing toasts, that `.claudechic/` is claudechic-owned. Delivered in two pieces (§4.2, §4.3) per L15.
- **Anti-definition:** Not "context" alone (overloaded). Not "agent identity" (the role-identity Markdown is a different thing — that defines *who the agent is in the workflow*, not *what claudechic is*).
- **Where it appears:** vision.md §"Agent awareness"; STATUS.md L15 + A3; spec.

### 4.2. piece 1: session-start injection

See §2.6. The vocabulary is **session-start injection**, fires always, short (a few sentences), implementation may be SDK system-prompt preset / append parameter / hook — open mechanism question.

### 4.3. piece 2: first-read injection (mirrored, rule-equivalent, auto-loaded)

See §2.7, §2.5a, §2.8, §2.9. The vocabulary is **first-read injection**, content is **rule-equivalent**, delivery **mirrors `.claude/rules/` behaviour**, mechanism is **auto-loaded** (Claude Code reads it as standing context). Trigger semantics: **once per agent-session**, fires on first read inside any `.claudechic/` directory.

### 4.4. claudechic-aware

- **Canonical form:** **claudechic-aware**
- **Definition:** Adjective for an agent that has received the session-start injection. After `claudechic-awareness` is established, the agent knows it's in a TUI with guardrails/workflows/hints. After the first-read injection, the agent additionally knows the `.claudechic/` layout in detail.
- **Anti-definition:** Not "claudechic-enabled" (suggests a feature flag — wrong). Not "claudechic-spawned" (which is a fact about the agent's launch, not its knowledge state).
- **Where it appears:** spec; rationale documents.

### 4.5. baseline awareness (vs deeper awareness)

- **Canonical form:** **baseline awareness** (after session-start injection, §4.2); **deeper awareness** or **fuller-context awareness** (after first-read injection, §4.3).
- **Definition:** Two distinct knowledge states distinguishing what L15's two pieces deliver. Baseline = the few-sentences statement; deeper = the package's documentation about how `.claudechic/` is structured.
- **Anti-definition:** Not "shallow" / "deep" (value-loaded). Not "L15 piece 1 awareness" / "L15 piece 2 awareness" (verbose; reserve for cross-references).
- **Where it appears:** spec §"Agent awareness"; cross-references.

### 4.6. claudechic-awareness install (canonical) / RETIRED: claudechic-awareness injection

Per **STATUS.md A13** (RESEARCH.md Option B; user-approved at spec-exit), the agent-awareness mechanism switched from a custom in-process injection (SessionStart hook + PreToolUse hook + first-read tracker, all in a `claudechic/context_delivery/` package) to an idempotent file-install routine that copies bundled `claudechic/context/*.md` into `~/.claude/rules/claudechic_*.md`. The Claude Agent SDK then loads those files natively as Claude rules. The mechanism is **install + SDK auto-load**, not **injection**.

#### 4.6a. claudechic-awareness install (canonical)

- **Canonical form:** **claudechic-awareness install** (noun, the mechanism); **install claudechic-awareness** (verb form, in user-facing labels and prose).
- **Definition:** The idempotent NEW/UPDATE/SKIP routine that copies bundled context docs (`claudechic/context/*.md`) into `~/.claude/rules/claudechic_<name>.md` on every claudechic startup. Gated by the user-tier `awareness.install` config key (default `True`). The Claude Agent SDK then loads the installed files as Claude rules in every session, achieving the L15 + A4 "behave the same as `.claude/rules/`" goal by *being* `.claude/rules/` content (claudechic-prefixed namespace).
- **Anti-definition:** Not "claudechic-awareness injection" (RETIRED, §4.6b — no in-process injection happens; the SDK does the load). Not "claudechic-awareness rules" (overloads with Claude rules / guardrail rules — see §2.3a, §2.3b). Not the same as **session-start injection** (§2.6) or **first-read injection** (§2.7) — those terms describe the *agent-perceived* delivery moments; "claudechic-awareness install" describes the *file-placement mechanism* that makes those deliveries happen via the SDK.
- **Where it appears:** SPEC.md §0.2, §4 (Group D), §7.2, §7.3 user-facing label, §8.3 docs section title; `claudechic/awareness_install.py` module name; `install_awareness_rules()` function name; STATUS.md A13; SPEC_APPENDIX.md §4.4.
- **User-facing label form:** **"Install claudechic-awareness"** (verb action). Helper text describes the install target (`~/.claude/rules/`) and the SDK consumption pattern.

#### 4.6b. RETIRED: claudechic-awareness injection

The phrase "claudechic-awareness injection" was the original R6-UX canonical wording (predates A13). Per **A13** (STATUS.md), the mechanism changed from injection-based to install-based. The wording is **retired** in spec / docs / UI prose for the remainder of this run.

- **claudechic-awareness injection** (noun)
  - **Why retired:** the mechanism no longer injects content into agent prompts. The Claude Agent SDK loads `~/.claude/rules/claudechic_*.md` files as Claude rules at session start; claudechic only places the files. There is no in-process injection. Calling the mechanism "injection" misleads implementers about the moving parts and contradicts §4.6a's install framing.
  - **Replace with:** **claudechic-awareness install** (§4.6a). For the agent-perceived delivery moments, the unchanged terms **session-start injection** (§2.6) and **first-read injection** (§2.7) remain canonical — they describe *when the agent sees the content*, not *how claudechic placed it*. The L15 two-piece semantics are unchanged in agent-perceived terms; only the claudechic-side mechanism word changes.
  - **Anti-definition:** does NOT describe a SessionStart hook (there isn't one for awareness); does NOT describe a `system_prompt`/`append_system_prompt` injection (the SDK handles loading natively); does NOT describe a per-tool-use injection (no PreToolUse hook for awareness in the install design).

**Where these retired terms must NOT appear:** SPEC.md body (post-A13 edit), SPEC_APPENDIX.md non-historical sections, `docs/configuration.md`, TUI labels and helper text, the `awareness.install` user-facing label, hint text.

**Where these retired terms MAY still appear (read-only):** the SUPERSEDED `axis_awareness_delivery.md` (preserved as historical artifact); STATUS.md A13's narrative explanation of what changed; SPEC_APPENDIX.md §4.4's "Historical note for future maintainers" (which describes why the change happened); quotations from the original R6-UX wording in retirement records (this entry, §4.6b).

**Where it appears (this glossary):** here only, as a retirement record.

---

## 5. Workflow artifact vocabulary

### 5.1. artifact dir

- **Canonical form:** **artifact dir** (or **artifact directory** in formal prose)
- **Definition:** Per vision.md §"Workflow artifact directories": the designated directory a workflow's setup phase writes files (specs, status documents, plans, hand-off material) to, and which subsequent agents in the same workflow run read from. Location, naming, and persistence semantics are open mechanism questions (the spec must answer them).
- **Anti-definition:** Not "phase output" — that phrase is overloaded with the per-tool output of a phase's last command. Not "scratch" — artifacts persist across phases. Not "session state" — that's the engine's serialized phase position, not the human-readable spec/status files. Not "the chicsession" — chicsession is a JSON snapshot of multi-agent UI state at `<repo>/.chicsessions/<name>.json`, totally separate.
- **Where it appears:** vision.md §"Workflow artifact directories"; spec §"Artifact dir mechanism" (open question to be answered there); the `project-team` workflow's setup phase already writes to `.project_team/<run>/` which is the de-facto artifact dir convention today.
- **Retired alternates:** "phase output dir", "workflow scratch", "team folder", "run folder".

### 5.2. workflow run

- **Canonical form:** **workflow run** (a single end-to-end execution of a workflow); **workflow run dir** (the artifact dir for that run, when the team needs to be specific).
- **Definition:** One activation of a workflow from setup to signoff. Has a stable identity (a name, like `independent_chic`), a state file, a phase log, and an artifact dir. Multiple runs of the same workflow can coexist (separate artifact dirs, separate state).
- **Anti-definition:** Not "session" (overloaded with Claude session, chicsession). Not "instance" (object-oriented connotation). Not "workflow execution" (verbose; reserve for formal contexts).
- **Where it appears:** spec §"Artifact dir"; the `project-team` workflow's setup phase; `docs/configuration.md` (when documenting workflow state).

### 5.3. hand-off material

- **Canonical form:** **hand-off material** (in prose; the artifact dir contains it).
- **Definition:** Files the setup phase writes for downstream phases to read — typically the spec, the STATUS, the appendix, the lens analyses. The phrase emphasizes the *purpose* (passing context to a later agent) rather than the *file type* (any of: Markdown, YAML, JSON).
- **Anti-definition:** Not "deliverable" (deliverables are the *external* output of the workflow; hand-off material is *internal* between phases). Not "spec" (the spec is one piece of hand-off material).
- **Where it appears:** vision.md §"Workflow artifact directories"; spec.

### 5.4. setup phase output / phase output

- **Canonical form:** **setup phase output** when specifically referring to what the setup phase writes; otherwise prefer **artifact** or **hand-off material** (§5.3).
- **Definition:** The contents of the artifact dir that the setup phase produced (typically: `vision.md`, `STATUS.md`, `userprompt.md`, then any lens evaluations).
- **Anti-definition:** "Phase output" alone is too vague (could mean tool stdout, agent message stream, written files). Always qualify: "setup phase output" or "implementation phase output."
- **Where it appears:** spec §"Artifact dir mechanism".

### 5.5. chicsession (orthogonal — keep separate)

- **Canonical form:** **chicsession**
- **Definition:** A named multi-agent UI snapshot at `<launched_repo>/.chicsessions/<name>.json`, storing `name`, `active_agent`, `agents: list[ChicsessionEntry]`, and `workflow_state: dict | None` (opaque, owned by the workflow engine). Saved/loaded by `ChicsessionManager`.
- **Anti-definition:** Not a workflow run (§5.2 — though a chicsession may carry workflow state for one). Not a Claude session. Not the artifact dir (chicsessions live in `.chicsessions/`, artifact dirs live in `.project_team/<run>/` or wherever the spec puts them).
- **Where it appears:** `claudechic/screens/chicsession.py`, `claudechic/chicsession_cmd.py`, `.chicsessions/` directory, `claudechic/context/workflows-system.md` §"Chicsessions".
- **Risk note:** if the spec uses the words "session" and "run" loosely, contributors will conflate Claude session, chicsession, workflow run, and shell session. Keep them separated by always qualifying.

---

## 6. Cross-fork vocabulary (sprustonlab ↔ abast)

### 6.1. fork

- **Canonical form:** **fork**
- **Definition:** A diverged copy of the upstream `claudechic` repo, maintained by a different lab. Two forks are in scope: **sprustonlab/claudechic** (the working tree this run operates on) and **abast/claudechic** (the cooperating fork). mrocklin/claudechic upstream is out of scope (L1).
- **Anti-definition:** Not "branch" (forks are full repos; branches are within a repo). Not "tier" (the tier system is intra-fork; forks are external).
- **Where it appears:** spec; vision.md §"Selective integration with abast"; STATUS.md.

### 6.2. cherry-pick

- **Canonical form:** **cherry-pick**
- **Definition:** The git operation `git cherry-pick <commit>` applied to bring a single abast commit onto the sprustonlab tree. Per L16, the cherry-pick set is **fully decided** for this run (table in STATUS.md A2); the team does not re-survey or re-decide which commits to take.
- **Anti-definition:** Not "merge" (a merge brings an entire branch's history; a cherry-pick brings a single commit). Not "rebase" (rebase replays a chain on a new base). Not "selective integration" alone (which is the *strategy*, of which cherry-pick is the *mechanism*).
- **Where it appears:** spec §"Cherry-pick execution"; vision.md §L16; STATUS.md A2; commit attribution in the appendix.

### 6.3. selective integration

- **Canonical form:** **selective integration**
- **Definition:** The strategy of pulling specific commits or features from a sister fork rather than performing an all-or-nothing merge. Per L2, integration with abast is selective only. Cherry-pick (§6.2) is the primary mechanism.
- **Anti-definition:** Not "merge" (rejected by L2). Not "rebase". Not "vendoring" (vendoring would copy abast's tree wholesale; we copy individual decided commits).
- **Where it appears:** vision.md §"Selective integration with abast"; STATUS.md L2; spec §"Cross-fork strategy".

### 6.4. cross-pollination

- **Canonical form:** **cross-pollination** (noun); **cross-pollinate** (verb)
- **Definition:** The **bidirectional** flow of feature work, layout decisions, and vocabulary between sprustonlab/claudechic and abast/claudechic. Each fork contributes to and absorbs from the other; neither leads the other. Per A10 (STATUS.md), this is the canonical framing for the abast relationship: sprustonlab pulls selected abast commits *and* abast pulls selected sprustonlab commits, both forks evolve, neither subordinates to the other. The mechanism is **selective integration** (§6.3); the relationship is cross-pollination; the ongoing dialogue that sustains it is **coordination** (§6.4a).
- **Anti-definition:**
  - Does **NOT** mean "convergence" (RETIRED, §6.4b) — cross-pollination does not require the forks to end up identical or to share a single layout. The forks can stay independently maintained while exchanging commits.
  - Does **NOT** mean a **one-way claudechic-led merge program** — both directions matter; sprustonlab does not "lead" abast onto a layout.
  - Does **NOT** mean **unification of forks under a single layout** — each fork retains independence.
  - Not "synchronization" (sync implies state mirroring; cross-pollination is selective and asymmetric per pull).
  - Not "vendoring" (vendoring is one-way wholesale; cross-pollination is selective and bidirectional).
- **Where it appears:**
  - **Spec / docs / UI prose:** "cross-pollination with abast", "cross-pollinated commits", "the abast cross-pollination set". Used wherever the prior framing said "convergence".
  - **STATUS.md:** A10 captures the user's verbatim direction ("we cross polinate not just pull from one"); A10's reframing of L11 anchors the term.
  - **Code symbols:** none forced (per L4 spirit). No existing symbol uses "convergence"; no rename pressure.
  - **Coordination artifact** (when authored for abast): describes this run's cross-pollination set and invites abast's reciprocal selection.

### 6.4a. coordination

- **Canonical form:** **coordination** (noun); **coordinate with abast** (verb phrase)
- **Definition:** The ongoing dialogue between the two forks' maintainers that sustains cross-pollination (§6.4) — surfaces what each fork has shipped, agrees on which commits flow which way, flags structural decisions before they're made. Channel: GitHub issues, PRs, direct contact. Per L11, abast cooperation is available and should be leveraged.
- **Anti-definition:**
  - Not "convergence" (RETIRED, §6.4b) — coordination is the *process* of dialogue, not an outcome of unification.
  - Not "merge program" (RETIRED, §6.4b) — coordination has no scheduled merges; it produces selective-integration opportunities both directions.
  - Not "selective integration" (§6.3) — selective integration is the *act* of cherry-picking specific commits; coordination is the surrounding *conversation*.
  - Not "cross-pollination" (§6.4) — cross-pollination is the bidirectional *flow* of work; coordination is the *dialogue* enabling it. Cross-pollination is the noun for *what happens*; coordination is the noun for *how the forks talk*.
- **Where it appears:** spec / docs / UI prose; STATUS.md L11 (reframed by A10); the coordination artifact (when authored); GitHub issue/PR comments referencing inter-fork work.

### 6.4b. RETIRED: convergence / merge program

The following terms previously appeared in this glossary and in early spec drafts. Per **A10** (STATUS.md, user resolution to Vision-phase Q7: *"trim we cross polinate not just pull from one"*) they are **retired** from spec, docs, and UI prose for the remainder of this run.

- **convergence** (noun) / **converge** (verb)
  - **Why retired:** implies a one-directional outcome where both forks end up under a shared layout that sprustonlab leads. The user's framing is bidirectional and selective, not outcome-driven (the forks can stay distinct while exchanging commits).
  - **Replace with:** **cross-pollination** (§6.4) for the bidirectional flow; **coordination** (§6.4a) for the dialogue; **selective integration** (§6.3) for the act of pulling commits.
  - **Anti-definition:** does NOT mean a **one-way claudechic-led merge program**; does NOT mean **unification of forks under a single layout**; does NOT mean a synchronized layout.
- **merge program** (noun)
  - **Why retired:** suggests a scheduled, comprehensive integration of abast's tree into sprustonlab (or vice versa). Per L2, integration is selective only; per A10, it is bidirectional. There is no "program".
  - **Replace with:** **selective integration** (§6.3) for the strategy; **cherry-pick** (§6.2) for the per-commit mechanism; **cross-pollination** (§6.4) for the bidirectional framing.
  - **Anti-definition:** does NOT describe any planned merge of branches; does NOT describe any one-way absorption of abast's tree.
- **alignment merge** (noun) — historically used as a softer variant of "merge program"; same retirement rationale.
- **join the trees** (verb phrase) — colloquial; same retirement rationale.

**Where these retired terms must NOT appear:** spec body, appendix body, `docs/configuration.md`, TUI labels, button copy, status-bar prose, error messages, hint text, the coordination artifact, PR descriptions for cross-pollinated commits.

**Where these retired terms MAY still appear (read-only):** quotations from the prior project-team run's documents (`.project_team/issue_23_path_eval/*.md`); quotations from `vision.md` (which is the prior team's hand-off and is not rewritten — A10 explicitly preserves vision.md text and asks spec authors to honor A10 in their own prose); historical commit messages.

**Where it appears (this glossary):** here only, as a retirement record.

### 6.5. merge-base

- **Canonical form:** **merge-base** (the git term)
- **Definition:** The most recent common ancestor commit between two branches. For sprustonlab/main and abast/main, the merge-base is `285b4d1` (2026-04-20) per STATUS.md "Git baseline". Used to scope what each fork has changed since their divergence.
- **Anti-definition:** Not "fork point" (vague). Not "common ancestor" alone (every commit pair has many common ancestors; the merge-base is the *most recent* one).
- **Where it appears:** STATUS.md "Git baseline"; spec §"Cross-fork strategy"; the prior run's `fork_diff_report.md`.

### 6.6. abast / sprustonlab (referring to the forks consistently)

- **Canonical form:** lowercase **abast** and **sprustonlab** when used as fork names. The full GitHub references are **abast/claudechic** and **sprustonlab/claudechic**. The branches are **abast/main** and **sprustonlab/main**.
- **Definition:** abast = the cooperating fork. sprustonlab = the fork this run operates on. Both are downstream of mrocklin/claudechic (out of scope, L1).
- **Anti-definition:** Don't use "the abast fork" / "the sprustonlab fork" repeatedly; "abast" and "sprustonlab" are nouns. Don't mix capitalization ("Abast", "Sprustonlab" — wrong; these are GitHub org names, lowercase canonical).
- **Where it appears:** spec; STATUS.md; vision.md; commit attribution.

### 6.7. lost work (4 senses)

- **Canonical form:** **lost work** (with the qualifier when needed: **commit-lost**, **post-merge-broken**, **conflict-reverted**, **intent-lost**)
- **Definition:** Per L10, "lost work" includes four distinct senses:
  1. **Commit-lost** — commits that never make it onto our main branch (skipped cherry-picks).
  2. **Post-merge-broken** — features that exist as code post-merge but are non-functional (silent breakage).
  3. **Conflict-reverted** — features whose code was reverted during conflict resolution.
  4. **Intent-lost** — features whose code survives but whose authorial intent was misunderstood and re-implemented incorrectly during integration.
- **Anti-definition:** Not "regression" (regression is one possible *symptom* of lost work). The Skeptic lens must address all four senses (L10).
- **Where it appears:** Skeptic's risk evaluation (§"Lost work"); spec §"Cross-fork risk surface"; appendix.

---

## 7. Path / location vocabulary

### 7.1. launched-repo root (canonical for "the directory claudechic was invoked in")

- **Canonical form:** **launched-repo root** (in prose); **`launched_repo_root`** (in new Python identifiers when relevant). Existing identifiers (`project_root`, `project_dir`, `cwd`, `root`) are not forced to rename (L4 spirit).
- **Definition:** The directory `claudechic` was invoked in — the repo whose code the user is working on, **not** claudechic's own source repo. Resolves to `Path.cwd()` at app startup.
- **Anti-definition:** Not "claudechic's repo" (which is the source-installed package). Not "the working dir" (overloaded with shell working dir, agent working dir). Not "project root" alone (overloaded with "claudechic the project"). When existing code uses `project_root` / `project_dir`, prose should still say "launched-repo root".
- **Where it appears:** spec, prose, `docs/configuration.md`. New code may use `launched_repo_root` if introducing a new symbol; existing code retained.

### 7.2. main worktree / worktree

- **Canonical form:** **main worktree** (the canonical clone) vs **worktree** (any git worktree, including the main one in the broad sense; in the narrow sense, a non-main worktree created via `git worktree add`).
- **Definition:** From the git-worktree feature (`claudechic/features/worktree/`). The main worktree is the originally-cloned working tree. Worktrees are sibling working trees git creates to support parallel branches without re-cloning. claudechic's worktree feature symlinks `<main_wt>/.claude` and (post-vision-work) `<main_wt>/.claudechic` into each new worktree so state carries over.
- **Anti-definition:** Not the same as "branch" (worktrees and branches are independent: many worktrees can exist for one branch in different states). Not the same as "clone" (clones are repository-level; worktrees share the underlying repo).
- **Where it appears:** `claudechic/features/worktree/git.py`; spec §"Worktree symlink (BF7)".

### 7.3. package source vs package tier

- **Canonical form:** **package source** = the `claudechic/` Python source tree (lowercase, no leading dot). **Package tier** = the override-resolution tier whose content lives at `claudechic/defaults/...` inside the package source.
- **Definition:** The package source is the installed Python package directory. The package tier is the *role* of the bundled-content subset of the package source in the 3-tier system.
- **Anti-definition:** Don't conflate. The package source contains both engine code (e.g., `claudechic/workflows/loader.py` post-move) **and** bundled content (`claudechic/defaults/workflows/...`). Only the latter is "package tier"; the engine code is just code.
- **Where it appears:** spec; loader code; `vision.md` §L7.

### 7.4. `~/.claudechic/` vs `~/.claude/`

- **Canonical form:** Both are paths; the spec must always render them with the trailing slash and the leading dot to avoid confusion with the package source `claudechic/`.
- **Definition:** `~/.claude/` = Claude's home namespace (read-only for claudechic). `~/.claudechic/` = claudechic's user-tier home namespace (per L6, mirrors `~/.claude/` pattern; not XDG). The two are siblings under `$HOME`; neither is inside the other.
- **Anti-definition:** Not the same. Not nested. Not interchangeable.
- **Where it appears:** spec; `docs/configuration.md`; the migration text in `config.py` after relocation.

---

## 8. Other terms carried forward and refined

### 8.1. workflow / phase / role / namespace

These are not contested by this run; they were canonicalized in `claudechic/context/workflows-system.md` and remain stable. Brief restatement:

- **workflow** — a YAML-defined orchestration with phases, advance checks, and (typically) per-role agent prompts. Identified by `workflow_id`.
- **phase** — a stage within a workflow (e.g., `setup`, `leadership`, `specification`). Has advance checks.
- **role** — an agent's identity within a workflow (e.g., `coordinator`, `composability`, `terminologyguardian`, `skeptic`, `useralignment`, `implementer`, `tester`).
- **namespace** — the YAML id qualifier; format is `namespace:bare_id`. Global manifests use `"global"`; workflow manifests use `workflow_id`. Unrelated to the `.claude/`/`.claudechic/` *namespace* word — disambiguate as **id namespace** vs **filesystem namespace** in any sentence where both appear.
- **Risk:** "namespace" is overloaded (filesystem boundary vs id qualifier). Prefer **id namespace** for the YAML-id sense whenever filesystem boundaries are also under discussion.

### 8.2. checks / advance check / setup check

- **check** — async verification protocol (`Check.check() -> CheckResult`). Leaf module.
- **advance check** — a check run when attempting to advance from one phase to the next; AND-semantics, short-circuit on first failure.
- **setup check** — a check run during a phase's setup (e.g., a workflow's startup); all checks execute, all failures reported (no short-circuit).
- **Where it appears:** `claudechic/checks/`; `claudechic/workflow_engine/engine.py`; workflow YAML `advance_checks:` and `setup:` sections.
- **Anti-definition:** Not a "guardrail rule" (§2.3b). Not a "hint trigger" (a `TriggerCondition`).

### 8.3. hint lifecycle / hint activation / hint state

- **hint lifecycle** — the per-hint records (`times_shown`, `last_shown_ts`, `dismissed`, `taught_commands`) tracked across sessions; managed by `HintStateStore`.
- **hint activation** — the on/off state of the hints pipeline as a whole and the per-id disable list (`{"enabled": True, "disabled_hints": [...]}`).
- **hint state** — colloquial term for the JSON file containing both. The file is `hints_state.json`, relocated from `<repo>/.claude/hints_state.json` to `<repo>/.claudechic/hints_state.json` per vision.md §"File-move inventory".
- **Anti-definition:** "Hint state" is *not* the in-memory `HintRecord` alone; it's the persisted pair (lifecycle + activation).

### 8.4. MCP tool

- **Canonical form:** **MCP tool** (capitalized M-C-P; this is a protocol name)
- **Definition:** A Python script (or set of scripts) registered with an MCP server that exposes callable tools to Claude. claudechic's bundled MCP tools live at `claudechic/defaults/mcp_tools/` (post-restructure); user-tier at `~/.claudechic/mcp_tools/`; project-tier at `<launched_repo>/.claudechic/mcp_tools/`.
- **Anti-definition:** Not "command" (slash commands are different; they're TUI-side). Not "skill" (Claude skills are separate). Not "hook" (hooks are SDK-level callbacks).
- **Where it appears:** `claudechic/mcp.py`; `claudechic/mcp_tools/` (current) → `claudechic/defaults/mcp_tools/` (post-restructure); spec §"MCP tools as content".

---

## 9. Vision-document terminology issues flagged (per A1)

A1 says agents must surface vision/STATUS terminology issues rather than work around them. Three flagged here:

### 9.1. "global" used in two senses inside vision.md §"What we want"

vision.md §1 says "Rules and hints are conceptually paired — together they make up the 'global' manifest section in the existing codebase. Whether they're a single directory or two siblings is a mechanism choice." This sentence retains "global" with its existing-codebase meaning (= "always-active across workflows"), and the L7 layout says each tier's directory contains a `global/{rules,hints}.yaml`. **But** "global" elsewhere has historically meant "user tier / `~/.claude/.claudechic.yaml`" (the prior run's terminology, now retired).

- **Risk:** A reader of the spec hitting "global tier" ambiguously imports either meaning. The spec must use **"global manifests"** for the "always-active across workflows" sense (preserving the L7 directory name `global/`), and **never use "global tier"** (which would re-introduce the retired user-tier confusion). The 3-tier names are *package / user / project* (§1.1–§1.4) — no "global tier" exists.

### 9.2. "settings" in §"Settings UI and configuration reference"

The vision section header pairs "Settings UI" (umbrella, L4 user-facing) with "configuration reference" (L4 technical). This is internally consistent under L4, but a reader missing L4 may infer that "settings" and "configuration" are interchangeable in vision prose. The spec must lead with the L4 distinction in its first paragraph that mentions either word, so the asymmetry between "Settings UI" and "configuration reference page" is anchored before contributors hit it.

### 9.3. "the worktree feature silently regresses"

vision.md §"Worktree symlink (BF7)" says claudechic state "stops carrying over to new worktrees" if the parallel `.claudechic/` symlink isn't added. The phrase "claudechic state" is undefined here — does it mean *all* `.claudechic/` content, or only state files like `hints_state.json` and `phase_context.md`? The spec must answer this: the BF7 site needs a *behavioural* spec ("symlink the entire `.claudechic/` directory of the main worktree into each new worktree, equivalent to the existing `.claude/` symlink semantics") rather than the colloquial phrase.

These flags are **for the team's awareness**; they do not block. The spec author should resolve them inline when writing the relevant sections.

---

## 10. Top terminology risks for the team to watch

Three load-bearing risks the team must keep in mind through specification, implementation, and testing:

1. **"Rules" overload (Claude rules vs guardrail rules vs the Markdown content auto-loaded under A3).** A3 makes this acute — the new auto-loaded directory delivers content that Claude treats *as if* it were a rules file but which we call **rule-equivalent** to keep it distinct from both Claude rules (§2.3a) and guardrail rules (§2.3b). The spec must use the qualified term every time. A drift here produces an L3 violation (writing into `.claude/rules/`) or an A3 violation (auto-loaded content not actually rule-equivalent).

2. **"Tier" vs guardrail "level" vs id "namespace" vs filesystem "namespace".** All four are layering / partitioning words; the spec must use **tier** (override resolution), **level** (`deny`/`warn`/`log`), **id namespace** (YAML `namespace:bare_id`), and **filesystem namespace** (`.claude/` vs `.claudechic/`) — never one for another.

3. **"Settings" vs "config" vs "Claude settings".** L4 pins the surface-vs-internals split, but the existence of `~/.claude/settings.json` (Claude's own file) means three meanings of "settings" coexist: the user-facing umbrella (§3.1), Claude's `settings.json` (§3.2), and the abast pattern of using "settings" in a JSON filename (`fast_mode_settings.json`, deferred to #25 per L12 — out of scope this run, but watch for it if any reference sneaks in). The spec must use the L4 split everywhere, and qualify "Claude settings" whenever ambiguity is possible.

---

## 11. Cross-references

- `vision.md` — authoritative source for L1–L17 and the goal statement. This glossary definitions for tier/content/`.claudechic/`/awareness derive from there verbatim.
- `STATUS.md` — A1 (this glossary's escalation channel for vision/STATUS errors), A2 (cherry-pick table), A3 (mirror `.claude/rules/` requirement).
- `userprompt.md` — Q4 (A3's origin) and Q3 (cherry-pick adoption).
- `.project_team/issue_23_path_eval/terminology_glossary.md` — prior run; useful for context but **superseded** by this glossary anywhere they conflict (the 3-tier model and A3 introduce vocabulary the prior run's "D17 collapses to per-project only" assumption excluded).
- `.project_team/issue_23_path_eval/composability_eval.md`, `risk_evaluation.md`, `alignment_audit.md` — prior lens analyses; vocabulary touchpoints carried forward where compatible.
- `claudechic/context/workflows-system.md`, `hints-system.md`, `guardrails-system.md`, `claudechic-overview.md` — current system docs; the spec's "deeper awareness" content (§4.3) draws from these.

---

*End of terminology_glossary.md.*
