# Terminology Contract — Specification Phase

**Author:** TerminologyGuardian
**Phase:** Specification
**Status:** Operational. This file is **binding on every spec/appendix author** for the Specification-phase deliverable.
**Authoritative reference:** `../terminology_glossary.md` (the full Leadership-phase glossary; ~50 entries with definitions, anti-definitions, and where-they-appear). **Do not duplicate definitions here** — this file pulls the canonical terms forward as an operational checklist.

---

## 0. Purpose

The Specification phase produces two files (per L14): an **operational spec** that Implementer + Tester can execute without reading anything else, and a separate **rationale appendix**. Both files have the same vocabulary obligations, defined here.

This contract:
1. Pins **domain terms** identified from `userprompt.md` to canonical forms.
2. Lists **synonyms** found across the four Leadership-phase lens reports and prescribes the resolution.
3. Lists **overloaded terms** with mandatory disambiguation rules.
4. Documents the **newcomer-simulation** findings (terms a fresh contributor would stumble on).
5. Provides a **vocabulary checklist** spec/appendix authors run before submission.

**Operating rule (binding):** if the spec uses a term not on this contract or in the glossary, the author either (a) adopts the canonical form in §6 below, (b) adds a new entry to the glossary first and references it here, or (c) escalates to Composability for an architectural-naming decision. **Do not coin new vocabulary in the spec body.**

---

## 1. Domain terms identified from `userprompt.md`

These are the terms the user actually used in the kickoff and the nine Q-resolution rounds. Each maps to a canonical form and a glossary anchor. Spec authors **use the canonical form** in their prose; quoting the user's verbatim words is permitted only inside fenced quotes from `userprompt.md`.

| User's word(s) | Canonical form | Glossary anchor | Notes |
|---|---|---|---|
| "everything in 3 levels" / "3 levels", "priority c > b > a" | **3-tier override system** with **package tier** / **user tier** / **project tier** | §1.1–§1.4 | Per A5, "3 levels" applies to **content only** (workflows / rules / hints / MCP tools), not to config keys. |
| "a) workflows b) rules and hints c) mcp_tools" | **content categories**: workflows, rules, hints, MCP tools | §1.5 | "Rules and hints" = the `global/{rules,hints}.yaml` pair (§2.3b for guardrail rules, §2.4 for hints). The single user phrase "rules and hints" must always expand to the two distinct concepts in spec prose. |
| ".claudechic folder" | **`.claudechic/` namespace** at user tier (`~/.claudechic/`) and project tier (`<launched_repo>/.claudechic/`); content also lives at package tier inside `claudechic/defaults/` | §2.2, §7.4 | The user's "folder" is a directory in **two of three tiers**; the package tier is the **package-source** directory `claudechic/defaults/...`, not a literal `.claudechic/` directory. Spec must state this explicitly. |
| "settings" (in user prose: "settings file", "settings UI") | **settings** (umbrella, L4) | §3.1 | User-facing word only. Internal symbols stay "config". |
| "config" (when user said "config in 2 is what I want") | **config keys**, **config file**, **config tier** (the 2-tier user/project system) | §3.3, §3.4 | Per A5/L8: 2-tier (user + project), defaults in code, no package config file. |
| "a prompt injection telling agents about claudechic" (Q4) | **agent awareness** (umbrella); the claudechic-side mechanism is **claudechic-awareness install** (§4.6a, post-A13); the agent-perceived delivery moments remain **session-start injection** + **first-read injection** | §4.1, §4.2, §4.3, §4.6, §2.6, §2.7 | User said singular ("a prompt injection"); A11 confirms two agent-perceived pieces. Per A13, the *claudechic-side* mechanism is install-based (file copy + SDK auto-load), not in-process injection — the prior canonical "claudechic-awareness injection" is retired (glossary §4.6b). |
| "mirror the .claude/rule behavior" (Q4) | **mirror `.claude/rules/`** behaviorally; the resulting content is **rule-equivalent**; delivery is **auto-loaded** (Claude reads on its own) | §2.5a, §2.8, §2.9 | A4 added: behavioral equivalence is required, **symlinks are forbidden** (Windows), **overwriting Claude-owned files is forbidden**. |
| ".claude/rules/" (the path) | **`.claude/rules/`** (literal path, code-quoted) | §2.3a | When discussing the path in prose, prefix with "Claude's" on first mention per section: "Claude's `.claude/rules/` directory". |
| "non-destructive" (Q1) | **non-destructive incidental touch** (the A7 carve-out) | §2.1 + STATUS.md A7 | The spec must define "non-destructive" operationally: creates a new file claudechic owns, does not collide with any Claude-owned filename, works cross-platform. |
| "primary" (Q4 boundary strength) | **primary state** (= claudechic's normal-operation writes: config, hints state, phase context, session-state derivatives). Forbidden inside `.claude/`. | STATUS.md A7 | The contrast term is "non-destructive incidental touch" (above). The spec must enumerate which files are "primary state" by name. |
| "drop it" (Q5, re d55d8c0) | **re-implement fallback discovery from scratch** | STATUS.md A8 + glossary §1.8 | Spec uses "fallback discovery" (abast's term, kept canonical) — never "shadowing" or "loader walk" without anchor. |
| "we know what we are doing" (Q6) | **silent-loss-of-existing-state is an accepted tradeoff** (no migration code, no startup warning) | STATUS.md A9 + L17 | Spec must not propose migration helpers or warning toasts. |
| "we cross polinate not just pull from one" (Q7) | **cross-pollination** (bidirectional) — replaces "convergence" / "merge program" | STATUS.md A10 + glossary §6.4 | **The word "convergence" is RETIRED in spec prose.** Use "cross-pollination", "selective integration" (§6.3), or "coordination". |
| "two" (Q8) | **two-piece agent awareness** (session-start + first-read) | STATUS.md A11 + glossary §4.2/§4.3 | Reaffirms L15. Spec must not collapse into "single injection". |
| "let the team decide. fine to pospond if too much" (Q9) | **scope-deferrable settings UI features** (welcome-screen access, workflow-ID discovery, disabled-IDs listing, `/settings`-vs-button parity) | STATUS.md A12 | Spec lists each item as either **In scope** or **Postponed (with rationale)**. |

---

## 2. Synonym proliferation across lens reports

Cross-scan of `composability_eval.md`, `risk_evaluation.md`, `alignment_audit.md` against the canonical glossary. The lens reports themselves were authored before the glossary's final pass; they contain mild drift the spec must correct, not perpetuate.

### 2.1. "rules" — used unqualified in stale-doc and risk references

- **Where it drifts:**
  - `risk_evaluation.md:106-110` references `.claude/rules/` install sites and ContextDocsDrift hint without saying "Claude rules" (the §2.3a sense).
  - `alignment_audit.md:55, 106, 249` quotes user "rules and hints" and references `.claude/rules/` without the "Claude" qualifier.
  - `composability_eval.md:33` introduces "rule-equivalent" without inline anchor (forward-reference to glossary §2.8).
- **Resolution in spec:** every paragraph that mentions "rules" must qualify on first mention as **Claude rules** (§2.3a, the Markdown context files Claude reads), **guardrail rules** (§2.3b, the YAML enforcement gates), or **rule-equivalent** (§2.8, the A3 auto-loaded content). After the first qualified mention in a section, bare "rules" is acceptable **only if the section is unambiguously about one of the three**.
- **Specifically forbidden in spec:** sentences like "we sync rules into `.claude/rules/`" (which sense?) or "the rules system". Use either "Claude rules" or "guardrail rules" by name.

### 2.2. "injection" — collapsed across L15's two pieces

- **Where it drifts:**
  - `alignment_audit.md:220, 263` quotes user "prompt injection" and discusses A3 + L3 tension without using the L15 piece-1 vs piece-2 vocabulary.
  - `risk_evaluation.md:91, 139` discusses `append_system_prompt` and `PreToolUse` injection mechanisms without consistently labeling which L15 piece each implements.
- **Resolution in spec:** every mention of injection specifies which piece — **session-start injection** (always-on, glossary §2.6, §4.2) or **first-read injection** (once-per-agent, glossary §2.7, §4.3). The umbrella "agent awareness" (§4.1) is acceptable when referring to both pieces collectively.
- **Forbidden:** "the injection" as a singular noun for the whole mechanism. The mechanism is two pieces; the noun must be plural ("the injections") or qualified.
- **Disambiguate from the security sense:** when the spec needs to reference prompt-injection attacks (it shouldn't have to, but for completeness), use **prompt-injection attack** (hyphenated). The unqualified phrase "prompt injection" is **forbidden in spec prose** because it's ambiguous between the L15 mechanism and the attack class.

### 2.3. "convergence" / "merge program" — RETIRED per A10

- **Where to scan in the spec:** any sentence about the abast relationship, fork alignment, or layout coordination.
- **Resolution:** use **cross-pollination** (per A10, the bidirectional framing), **selective integration** (the strategy umbrella, glossary §6.3), or **coordination** (the relationship label).
- **Forbidden in spec:** "converge", "convergence", "merge program", "alignment merge", "join the trees".

### 2.4. "shadow" — RETIRED in favour of "override"/"fallback"

- **Where it might drift:** loader prose (especially when authors are explaining override resolution to readers).
- **Resolution:** use **override** (§1.6) for "the higher tier replaces the lower tier", **fallback** (§1.8) for "no higher tier defines this; use the lower one". **Never use "shadow"** — it's a near-synonym used inconsistently across loader literature; the spec retires it.

### 2.5. "merge" — only with qualifier

- **Where it drifts:** several reports use "merge" loosely — sometimes meaning git merge, sometimes meaning content combination.
- **Resolution:** every spec use of "merge" carries a qualifier: **tier merge** (the loader operation when policy permits combining content across tiers, §1.7), **git merge** (the git operation, vs cherry-pick), **dict merge** (the Python operation in the loader). Bare "merge" is **forbidden in spec prose**.

### 2.6. "tier" vs "level" vs "namespace" vs "scope"

All four words appear in the codebase as layering/partitioning words. They mean different things; the spec must not substitute.

| Canonical | Used for | Forbidden as substitute for |
|---|---|---|
| **tier** | Override resolution (package/user/project for content; user/project for config) | level, layer, scope, namespace |
| **level** | Guardrail enforcement (`deny`/`warn`/`log`) | tier, severity (a separate concept) |
| **id namespace** (qualified) | YAML id qualifier, `namespace:bare_id` format | filesystem namespace |
| **filesystem namespace** (qualified) | The `.claude/` vs `.claudechic/` boundary | id namespace |
| **scope** | Guardrail rule scoping by **roles** / **phases** / **exclude_roles** / **exclude_phases** | tier, level |

When the spec mentions "namespace" without a qualifier and both senses are in the same paragraph, the prose is **non-conformant** and must be fixed before submission.

### 2.7. "global" — forbidden as a tier name

- **Where it drifts:** historical "global config" referred to `~/.claude/.claudechic.yaml` (now retired). The L7 layout retains a directory `global/{rules,hints}.yaml` per tier — `global` here means **always-active across workflows**, not a tier name.
- **Resolution:** **never use "global tier"** in spec prose. The three tier names are **package / user / project** — period. When referring to the `global/` directory, say **global manifests** (the `rules.yaml` + `hints.yaml` pair) or **global rules** / **global hints** (the workflow-scope sense, glossary §8.1, §2.3b).

### 2.8. "settings" — Claude's vs claudechic's vs the abast pattern

- Three meanings of "settings" coexist:
  1. **claudechic settings** — user-facing umbrella (L4, glossary §3.1).
  2. **Claude settings** — Claude Code's `~/.claude/settings.json` (glossary §3.2).
  3. (out of scope this run) abast's `fast_mode_settings.json` package-root pattern.
- **Resolution in spec:** **always qualify** when both could be meant in the same sentence ("Claude settings" vs "claudechic settings"). The `/settings` TUI screen is the **claudechic settings UI**. Reading from `~/.claude/settings.json` is reading **Claude settings**.
- **`docs/configuration.md`** (the reference page) is named for the technical **config** surface; the TUI is named **settings**. The asymmetry is deliberate (per L4 + the issue body verbatim) and the spec's first paragraph that mentions both must anchor it.

### 2.9. "launched-repo root" — adopt in prose; existing code symbols stay

- **Where it drifts:** `composability_eval.md` and `alignment_audit.md` use "launched repo" idiomatically (correct); existing code uses `project_root`, `project_dir`, `cwd`, `root` (also correct — L4 forbids forced renames).
- **Resolution in spec prose:** use **launched-repo root** when describing the directory `claudechic` was invoked in. When citing existing code, retain the existing symbol name and gloss it: "`project_root` (= the launched-repo root)".
- **New code introduced in implementation** may use `launched_repo_root` for new symbols; renaming existing symbols is **out of scope**.

---

## 3. Overloaded terms — mandatory disambiguation rules

| Overloaded word | Senses that coexist | Spec rule |
|---|---|---|
| **rules** | Claude rules / guardrail rules / rule-equivalent | Always qualify on first mention per section (§2.1 above). |
| **override** | Tier override / guardrail `request_override()` token | Qualify when both could be meant in the same paragraph: **tier override** vs **guardrail override token**. |
| **merge** | tier merge / git merge / dict merge | Always qualify (§2.5 above). |
| **session** | Claude session / chicsession / workflow run / shell session | Always qualify; **chicsession** is a single word, no hyphen, lowercase. |
| **namespace** | filesystem namespace (`.claude/` vs `.claudechic/`) / id namespace (YAML `namespace:bare_id`) | Qualify when both are in the same paragraph (§2.6 above). |
| **injection** | session-start injection / first-read injection / guardrail tool-input injection / prompt-injection attack | Always qualify (§2.2 above). |
| **settings** | claudechic settings / Claude settings | Qualify when ambiguous (§2.8 above). |
| **state** | hint lifecycle state (in `hints_state.json`) / hint activation state (in same file, separate section) / workflow phase state (in chicsession) / config state | Qualify; the spec must list per-file what each "state" file holds. |
| **config** | config keys (the leaf YAML fields, §3.4) / config tier (the 2-tier user/project system) / config file (`config.yaml`) / `ProjectConfig` (the dataclass) | Use the most specific form. "Config" alone is acceptable only when the broader topic is unambiguous. |
| **defaults** | the **package tier**'s on-disk location `claudechic/defaults/` / the in-code `setdefault()` calls in `_load()` / "default values" in prose | When discussing the directory, say **`claudechic/defaults/`** (with the path); when discussing the package tier as a resolution layer, say **package tier**. **Never use "defaults tier" or "default tier"** as a tier name. |

---

## 4. Newcomer simulation — terms a fresh reader will stumble on

A simulated read of the four lens reports as if I had never seen the project. Terms flagged below either lack inline anchoring or use jargon without ground.

### 4.1. Terms that must be defined inline on first use in the spec

| Term | Why a newcomer stumbles | Spec rule |
|---|---|---|
| **chicsession** | Looks like a typo for "chic session"; non-obvious that it's `<repo>/.chicsessions/<name>.json` and orthogonal to workflow run. | First spec mention: "**chicsession** (the named multi-agent UI snapshot at `<launched_repo>/.chicsessions/<name>.json` — distinct from a Claude session and from a workflow run; see glossary §5.5)". |
| **workflow run** | Easy to conflate with "workflow" (the YAML definition) or "phase" (one stage). | First mention: "**workflow run** (one end-to-end execution of a workflow from setup to signoff, identified by run name like `independent_chic`; produces an artifact dir)". |
| **artifact dir** | Two prior runs called this "phase output" / "team folder" / "scratchpad". | First mention: "**artifact dir** (the designated directory the workflow's setup phase writes hand-off material to and subsequent phases read from; e.g., `.project_team/independent_chic/` for this run)". |
| **rule-equivalent** | New compound; meaning is "the agent treats it as if it were a Claude rule". | First mention: "**rule-equivalent** (content the agent perceives the same way it perceives a Claude `.claude/rules/` file — auto-loaded standing context, not a synthetic per-turn nudge)". |
| **fallback discovery** | Loader-internal term from abast's `8e46bca`. | First mention: "**fallback discovery** (the loader's walk through tiers in priority order, returning content from the first tier that defines it; see glossary §1.8)". |
| **mirror** | A3's verb; means "produces the same agent-perceived behaviour as", **not** copy-or-symlink. | First mention: "**mirror `.claude/rules/`** = produces the same agent-perceived behaviour without writing inside `.claude/`. (Symlinks are forbidden per A4; copies are forbidden per L3.)". |
| **primary state** | A7's term carving the boundary; meaning is "the files claudechic writes during normal operation". | First mention: enumerate the files by name (config.yaml, hints_state.json, phase_context.md, etc.) so the contrast with "non-destructive incidental touch" is concrete. |
| **non-destructive incidental touch** | The A7 carve-out; ambiguous unless the criteria are spelled out. | First mention: list the three criteria together — (1) creates a **new** file claudechic owns, (2) does **not collide** with any Claude-owned filename or convention, (3) works **cross-platform** (no symlinks). |
| **lost work** | Has four senses per L10. | First mention in the risk-related sections: enumerate the four — commit-lost / post-merge-broken / conflict-reverted / intent-lost. |

### 4.2. Implicit-context phrases to avoid

A newcomer cannot resolve these without prior context. The spec replaces each with the bracketed canonical form.

- "the boundary" → **the L3/A7 boundary between `.claude/` and `.claudechic/`**
- "the loader" → **the manifest loader (`ManifestLoader` in `claudechic/workflows/loader.py`)** (post-restructure path)
- "the engine" → **the workflow engine (`WorkflowEngine` in `claudechic/workflows/engine.py`)** (post-restructure path)
- "the hook" → **the `PreToolUse` hook** (or the specific hook by name)
- "the rules" → **Claude rules** OR **guardrail rules** (§2.1)
- "the file" → name the file with its post-restructure path
- "the tier" → name the tier (package / user / project)
- "the symlink" → forbidden per A4; if discussing the historical worktree `.claude` symlink, say "the legacy `.claude/` worktree symlink (BF7 site)"
- "the injection" → **session-start injection** OR **first-read injection** (§2.2)
- "the merge" → **tier merge** OR **git merge** (§2.5)
- "the namespace" → **filesystem namespace** OR **id namespace** (§2.6)

### 4.3. Jargon that needs grounding before use

| Jargon | Grounding sentence the spec must include on first use |
|---|---|
| **MCP tool** | "an MCP (Model Context Protocol) tool — a Python script registered with claudechic's MCP server that exposes callable tools to spawned agents". |
| **PreToolUse hook** | "a SDK hook fired by Claude Code before every tool invocation; claudechic uses it for guardrail enforcement". |
| **PostCompact hook** | "a SDK hook fired after `/compact`; claudechic uses it to re-inject phase context". |
| **chicsession** | (see §4.1) |
| **fallback discovery** | (see §4.1) |
| **append_system_prompt** | "the SDK option that appends a string to the agent's system prompt at session start". |

---

## 5. Cross-references to other lens reports

| If the spec needs to reference… | Cite this file |
|---|---|
| The 10 design axes / 7-group decomposition | `../composability_eval.md` |
| The full term list, anti-definitions, and where-each-term-appears | `../terminology_glossary.md` |
| The 23 numbered risks (esp. R1–R6 critical) and the four senses of "lost work" | `../risk_evaluation.md` |
| The user-intent drift items and the rationale behind A4–A12 | `../alignment_audit.md` |
| Locked decisions (L1–L17, A1–A12) | `../STATUS.md` |
| Authoritative goal statement and file-move inventory | `../vision.md` |

The spec **never restates** content from these files; it **references** them. This honors the "one canonical home" principle and L14 (operational spec; rationale lives elsewhere).

---

## 6. Vocabulary checklist (run before submitting spec or appendix)

Spec/appendix authors run this checklist on their drafts before submission. Every "no" is a blocker.

- [ ] Every mention of "rules" qualifies as **Claude rules** / **guardrail rules** / **rule-equivalent** on first mention per section (§2.1).
- [ ] Every mention of injection specifies **session-start injection** or **first-read injection** (or "agent awareness" for both collectively); no bare "the injection" (§2.2).
- [ ] Zero occurrences of **convergence**, **converge**, **merge program**, **alignment merge** (§2.3, A10).
- [ ] Zero occurrences of **shadow** in the override-resolution sense (§2.4).
- [ ] Every "merge" carries a qualifier — **tier merge** / **git merge** / **dict merge** (§2.5).
- [ ] Tier names are exactly **package / user / project** — zero occurrences of **global tier**, **default tier**, **defaults tier**, **bundled tier**, **home tier**, **repo tier**, **local tier** (§2.7, §1.1–§1.4).
- [ ] **global** appears only as **global manifests** / **global rules** / **global hints** / the directory path **`global/`** — never as a tier name (§2.7).
- [ ] **settings** is qualified as **claudechic settings** or **Claude settings** when both could be meant (§2.8).
- [ ] **launched-repo root** is used in prose; existing code symbols (`project_root` etc.) are retained and glossed (§2.9).
- [ ] **chicsession** (single word, lowercase) is defined inline on first mention (§4.1).
- [ ] **artifact dir**, **workflow run**, **rule-equivalent**, **fallback discovery**, **mirror**, **primary state**, **non-destructive incidental touch** are defined inline on first mention (§4.1).
- [ ] **lost work** enumerates all four senses on first mention in risk-related sections (§4.1, L10).
- [ ] No bare "the boundary", "the loader", "the engine", "the hook", "the file", "the tier", "the symlink", "the injection", "the merge", "the namespace" — each replaced with the canonical disambiguated phrase (§4.2).
- [ ] No new vocabulary coined in the spec body (operating rule §0). New terms enter through the glossary first, then the spec references them.
- [ ] Path names use the **post-restructure** layout: `claudechic/workflows/` for engine code, `claudechic/defaults/workflows/` for bundled YAML, `claudechic/defaults/global/{rules,hints}.yaml`, `claudechic/defaults/mcp_tools/`, `~/.claudechic/...`, `<launched_repo>/.claudechic/...`. Pre-restructure paths (`claudechic/workflow_engine/`, `claudechic/global/`, `claudechic/mcp_tools/`) appear **only** in §"File-move inventory"-equivalent sections that explicitly describe the move.
- [ ] Cross-fork relationship language uses **cross-pollination** / **selective integration** / **coordination** (A10), and abast/sprustonlab are lowercase.
- [ ] Cherry-pick disposition language matches the A2-as-revised-by-A8 table verbatim.

---

## 7. Top-3 terminology risks the spec authors must keep in mind

These are the highest-impact drift hazards based on the leadership-phase scan:

1. **"Rules" overload across Claude rules / guardrail rules / rule-equivalent.** Highest risk because A3's mechanism *behaves like* a Claude rule but **is not** a Claude rule (it lives outside `.claude/`). Drift here produces either an L3 violation in implementation or an A3 violation in behaviour. Always qualify.

2. **"Injection" collapsed into a single mechanism.** The user said "a prompt injection" (singular); the design ships two pieces (session-start + first-read). The spec must keep them lexically distinct or downstream agents will under-implement piece 2 (the first-read trigger and the rule-equivalent shape).

3. **"Tier" vs "level" vs "namespace" vs "scope"** — four layering words for four different concepts. Substituting one for another in the spec body produces silently wrong implementations (e.g., a guardrail rule scoped to the wrong "level", a config key landing in the wrong "tier", a YAML id collision under the wrong "namespace").

---

*End of terminology contract.*
