# RESEARCH — Prior art for Group D (agent-awareness mechanism)

**Author:** Researcher (project_team `independent_chic`).
**Date:** 2026-04-26.
**Charter:** answer "is there anything we can use from the internet about how Claude Code does this so we don't have to reimplement everything?" before redesigning Group D. Operational tone per L14.

---

## 1. Executive summary

- **The Claude Agent SDK already loads `.claude/rules/*.md` natively.** When `ClaudeAgentOptions.setting_sources` includes `"project"` and/or `"user"`, the CLI loads project + user rules (and `CLAUDE.md`) into every session at start, with full YAML-frontmatter `paths:` glob handling, recursive subdirectory discovery, symlink resolution, and `/compact` survival — none of which Group D currently builds on.
- **claudechic already passes `setting_sources=["user", "project", "local"]`** at `claudechic/app.py:969`. Every claudechic-spawned agent is already wired to consume `.claude/rules/`. The only missing piece is **delivering the bundled `claudechic/context/*.md` files into a tier the SDK reads** (i.e., `<repo>/.claude/rules/` or `~/.claude/rules/`).
- **The current Group D spec (`axis_awareness_delivery.md`) reimplements ~70 % of what the SDK already provides** — SessionStart payload composition, tier-walk override semantics, size budgets, post-compact re-injection, recognized-filename catalog, INFO-log on unrecognized files. All of these are SDK responsibilities once files live in `.claude/rules/`.
- **Tradeoff under user's "alternative":** writing files into `.claude/rules/` is a **non-destructive incidental write inside `.claude/`** in A7's terminology. A4's "no overwriting Claude-owned settings" still holds (we own the filenames we write). A4's "no symlinks **in the agent-awareness mechanism**" still holds (we copy, don't link). But A7 is in tension with the spec's R5.1 classification of awareness content as "primary state" — that classification needs to be revisited if Option B is adopted.
- **Recommended path: Option B (restore + harden the existing `/onboarding context_docs` phase),** with a settings toggle and frontmatter pass-through. We retire the entire `claudechic/context_delivery/` package + three SDK hooks + per-session tracker + size budgets + sentinel tests. SPEC §4 (Group D), `axis_awareness_delivery.md`, and INV-AW-1…INV-AW-13 all collapse to a much smaller surface.

---

## 2. Target-by-target findings

### Target 1 — Claude-agent-sdk's rules-loading API

**T1 (official docs).** [Use Claude Code features in the SDK — code.claude.com](https://code.claude.com/docs/en/agent-sdk/claude-code-features) is authoritative. Verbatim:

> The setting sources option (`setting_sources` in Python, `settingSources` in TypeScript) controls which filesystem-based settings the SDK loads. Pass an explicit list to opt in to specific sources, or pass an empty array to disable user, project, and local settings.

> `"project"` — loads Project CLAUDE.md, `.claude/rules/*.md`, project skills, project hooks, project `settings.json`. Location: `<cwd>/.claude/` and each parent directory up to the filesystem root.
> `"user"` — loads User CLAUDE.md, `~/.claude/rules/*.md`, user skills, user settings. Location: `~/.claude/`.
> `"local"` — loads CLAUDE.local.md (gitignored), `.claude/settings.local.json`. Location: `<cwd>/`.

> Omitting `settingSources` is equivalent to `["user", "project", "local"]`.

**Behaviour SDK provides for free** (per [Memory docs](https://code.claude.com/docs/en/memory)):
- Recursive discovery: "All `.md` files are discovered recursively, so you can organize rules into subdirectories like `frontend/` or `backend/`".
- Symlink resolution: "The `.claude/rules/` directory supports symlinks ... circular symlinks are detected and handled gracefully."
- Survives `/compact`: "Project-root CLAUDE.md survives compaction: after `/compact`, Claude re-reads it from disk and re-injects it into the session." Same applies to project rules. **The current `PostCompact` hook in `claudechic/workflows/agent_folders.py:147` is for phase-context only; project rules survive `/compact` without our help.**
- Path-scoped lazy load: "Path-scoped rules trigger when Claude reads files matching the pattern, not on every tool use." This is functionally equivalent to L15 piece-2 (first-read inside `.claudechic/`) — see Target 2 caveats.
- Diagnostics: `InstructionsLoaded` hook (CLI v2.1.64+) fires per loaded instruction file with `memory_type` and `load_reason` — useful for our own observability instead of building a tracker.

**No public Python parser is exposed.** The `claude-agent-sdk-python` package (PyPI: `claude-agent-sdk`) bundles the CLI binary that does the parsing internally. [The Python SDK's source on GitHub](https://github.com/anthropics/claude-agent-sdk-python) exposes `ClaudeAgentOptions` with `setting_sources` and the related types but does not expose a `parse_rules_directory()` function or a frontmatter parser. **We get the behaviour by setting the option, not by importing a parser.**

**Verdict:** the SDK is the authoritative loader. Reimplementing it is wasted effort. Use it.

---

### Target 2 — Authoritative format documentation

**T1 (official docs).** [Memory page — Path-specific rules](https://code.claude.com/docs/en/memory#organize-rules-with-claude/rules/) is the authoritative spec. Verbatim summary:

| Field | Documented status | Stable in practice |
|---|---|---|
| `paths:` (YAML list of glob strings) | **Documented; recommended.** Examples in docs use both quoted lists and unquoted strings. | Stable for **project-level** rules on `Read`. **Two known bugs** — see below. |
| `globs:` | **Undocumented** but works. Comma-separated, unquoted. | Working community workaround for the `paths:` quoting issues — but has no Anthropic guarantee of forward-compatibility. **Do not use.** |
| `name:`, `description:`, `disable-model-invocation:`, `allowed-tools:` | **Skill frontmatter only**, NOT rules frontmatter. Rules support only `paths:`. | N/A for our use. |
| Files without frontmatter | **Documented; loaded unconditionally on session start.** | **Stable.** This is the default behaviour. |

**Authoritative GitHub-issue resolution state** for the bugs the user pre-flagged:

| Issue | State | Implication for us |
|---|---|---|
| [#13905 — Invalid YAML in docs `paths:` examples](https://github.com/anthropics/claude-code/issues/13905) | **Closed.** Docs were updated to use quoted glob strings. | Use `paths: ["**/*.md"]` form, not `paths: **/*.md`. |
| [#17204 — `paths:` with quoted strings or YAML list does not load](https://github.com/anthropics/claude-code/issues/17204) | **Open.** Reporter found that quoted `paths:` and YAML-list `paths:` silently no-op while the undocumented `globs:` works. | Bug is current. Mitigation: use frontmatter-less files for unconditional load (the path Option B takes). |
| [#21858 — `paths:` ignored in `~/.claude/rules/`](https://github.com/anthropics/claude-code/issues/21858) | **Closed (stale).** User-tier path-scoped rules were not loading. | If we want path-scoping, scope at project tier only. User-tier files must be unconditional. |
| [#23478 — `paths:` rules not injected on `Write`, only on `Read`](https://github.com/anthropics/claude-code/issues/23478) | **Closed (stale).** Fix unclear. | L15 piece-2 ("first read inside `.claudechic/`") aligns with `Read` semantics naturally. The `Write`-side gap doesn't affect us because nothing in `.claudechic/` is written by an agent before being read. |

**Bottom line:** the **frontmatter-less path** (no `paths:` field, all rules load unconditionally on session start) is bug-free and stable. The `paths:`-scoped path is real but has live bugs; if we use it, we use it as nice-to-have lazy-loading and accept that user-tier scoping doesn't work.

---

### Target 3 — Third-party libraries / patterns

**No suitable Python library to depend on.** The closest matches:

| Source | Tier | License | Tests | Relevance |
|---|---|---|---|---|
| [`python-frontmatter`](https://pypi.org/project/python-frontmatter/) | T5 | MIT | Yes | Generic YAML frontmatter parser. **Useful only if we build our own loader (Option C), which we shouldn't.** |
| [`carlrannaberg/cclint`](https://github.com/carlrannaberg/cclint) | T5 | MIT | Yes (CI) | TypeScript/Node linter for Claude Code project files. Validates `.claude/rules/`, settings, hooks, agents, MCP. **Not a Python library; not embeddable.** Useful as a developer tool for validating our bundled rules during CI; not a runtime dependency. |
| [`pdugan20/claudelint`](https://github.com/pdugan20/claudelint) | T5 | MIT | Yes | TypeScript. Same shape as cclint. Same disposition. |
| [`stbenjam/claudelint`](https://github.com/stbenjam/claudelint) | T5 | Apache-2.0 | Yes | Python-based. Targets Claude Code **plugin marketplaces**, not rules. Out of scope. |
| Claude Rules Doctor (search-result-only; URL not located) | T7 | unknown | unknown | "Detects dead `.claude/rules/` files by checking if `paths:` globs match files." Cute but we don't need it. |

**Pattern: "tools that wrap Claude Code and ship bundled rules into `.claude/rules/`."** Several community projects do this (e.g., `affaan-m/everything-claude-code`, [Claude Rules collections at clauderules.net](https://www.clauderules.net/)) but the install pattern is uniformly: an installer script that copies markdown files from `<package>/rules/` into `<repo>/.claude/rules/` (or `~/.claude/rules/` for user-tier) and then exits. **There is no published library that does this idempotently with update semantics.** That's exactly the gap our existing `/onboarding context_docs` phase fills (Target 4).

**Verdict:** no off-the-shelf library to import. The behaviour we want is a small copy operation — small enough that we own it, large enough that doing it as a one-time onboarding step (already implemented) is preferable to a startup-side reimplementation.

---

### Target 4 — Existing claudechic precedent gap analysis

The current `/onboarding context_docs` phase implements the user's "alternative" *almost completely.* What's there:

`claudechic/workflows/onboarding/onboarding_helper/context_docs.md` (35 lines):
1. Locate package context dir via Python.
2. List bundled `.md` files.
3. Diff against `.claude/rules/` (NEW / SKIP / UPDATE).
4. Show install plan.
5. Ask user to proceed.
6. Copy NEW + UPDATE files; create `.claude/rules/` if absent.
7. Tell user they can re-run after upgrading.

**Coverage matrix vs. what Group D's spec demands:**

| Spec demand | Onboarding phase as-is | Gap to close |
|---|---|---|
| "rule-equivalent content auto-loads as if it were a Claude rule" (A4) | ✅ Once copied, the SDK loads them per Target 1. | **None.** This is the whole point. |
| Two-piece L15 (always-on + first-read fuller-context) | ✅ Files without frontmatter load always-on; ✅ optional `paths: ["**/.claudechic/**"]` frontmatter delivers first-read on demand (with the Target 2 caveats). | The current bundled files have no frontmatter. **Add `paths:` frontmatter to system docs (`workflows-system.md` etc.)** if we want them lazy-loaded; leave `awareness_brief.md` / `claudechic-overview.md` / `CLAUDE.md` frontmatter-less. |
| Update semantics (NEW / UPDATE / SKIP) | ✅ Already there. | None. |
| Survives `/compact` | ✅ SDK re-injects rules after `/compact` per Target 1. | **None.** The SPEC's `PostCompact` hook for the awareness payload is unnecessary. (Phase-context is a separate write site — see below.) |
| Project-tier override of bundled docs | ✅ The user can edit `<repo>/.claude/rules/<filename>.md` after install; subsequent re-runs prompt UPDATE. | None for project tier. |
| User-tier override | ❌ Phase only writes project-tier `.claude/rules/`. | **Add `--user` flag** if user-tier install desired (low priority — see open question 4.2 below). |
| Settings toggle to disable | ❌ Phase always runs as part of `/onboarding`. | **Add `claudechic_rules_install: bool` config key** (Target 5). |
| Idempotency on re-install | ✅ SKIP for identical, UPDATE for changed. | None. |
| Version tracking (which files came from which claudechic version) | ❌ No version metadata. | **Add `<!-- claudechic-bundled: v0.X.Y -->` block-level HTML comment** at top of each bundled file. Per [Memory docs](https://code.claude.com/docs/en/memory#how-claude-md-files-load), block-level HTML comments are stripped before injection — zero context cost, full auditability. |
| Cross-platform | ✅ Pure Python file copy via Read/Write tools — no symlinks, no shell. | None. (A4's no-symlinks rule is satisfied vacuously.) |
| Boundary classification | ⚠️ Writes inside `.claude/`. **In tension with A7's "primary state" classification of awareness content per spec R5.1.** | **Re-classify the bundled rules from "primary state" to "non-destructive incidental write under A7."** This is a spec amendment, not an implementation gap — see §3 Option B. |
| Per-claudechic-agent isolation | N/A — once installed, all agents (claudechic and bare `claude` CLI) see the rules. | This is a feature, not a gap: the user's bare `claude` invocations also gain claudechic context. **Removes a long-standing UX disparity.** |

**One material extra to add: dotignore-style file ownership marking.** Per A4 "no overwriting Claude-owned files," our installer must (a) only touch files whose names match the bundled catalog, (b) never overwrite a file the user has hand-edited without consent. The current phase satisfies (a) by listing; satisfies (b) by the SKIP-if-identical / UPDATE-if-different / always-prompt design. **No code change needed.**

**Phase-context delivery is orthogonal.** The current spec unifies awareness + phase-context delivery via one `context_delivery/` package. If we adopt Option B for awareness, **phase-context delivery becomes a separate, much smaller question:** (a) keep the existing `app.py:_write_phase_context` writes to `<repo>/.claudechic/phase_context.md` (Group B already mandates the path move from `.claude/` to `.claudechic/`), and (b) keep the existing `PostCompact` hook in `agent_folders.py` for phase-context re-injection. **Group D no longer "unifies" anything; it shrinks to "phase-context lifecycle" only.** The "claudechic-awareness" half of Group D goes away.

---

### Target 5 — Settings toggle for the rule install

**Existing infrastructure** (per `claudechic/config.py`):

- **User tier** (`~/.claude/.claudechic.yaml`, parsed as the module-level `CONFIG` dict at line 81). Used today for `analytics`, `experimental`, `worktree.path_template`, `default_permission_mode`, `show_message_metadata`, `vi-mode`, `recent-tools-expanded`. Save/load via `_save()` and `_load()`. New keys land here by adding a `setdefault()` line at line 41–47.
- **Project tier** (`<repo>/.claudechic.yaml` per L5; parsed as `ProjectConfig` dataclass at line 95). Used today for `guardrails`, `hints`, `disabled_workflows`, `disabled_ids`. New keys land here by adding a field to the dataclass and a load line in `ProjectConfig.load`.

Per A5 (config keys are 2-tier; defaults in code), **the install toggle should be project-tier**:

- **Recommended key:** `install_claude_rules` (project-tier; `bool`; default `True`).
  - Project-tier because the install is a per-project action — different projects may want different opt-in states.
  - User-tier alternative (`install_claude_rules_default`) is unnecessary — `/onboarding` already runs once per project; the user explicitly drives it.
- **Spec wording per terminology:** the user-facing label is "Install claudechic rules into `.claude/rules/`" (per L4 surface = "settings"). Tooltip: "When enabled, the `/onboarding` workflow copies claudechic context docs into this project's `.claude/rules/` directory, so Claude agents understand claudechic's systems. Disable to keep `.claude/rules/` untouched."
- **Surfacing in Group G (per SPEC §7):** add as a new project-tier key in the table at SPEC §7.3, alongside `guardrails` / `hints`. Editor: bool toggle. **No subscreen needed.**
- **Default value rationale:** `True` matches the existing `/onboarding` flow (which already copies). Users who don't want it must explicitly opt out.
- **Behavior when toggled off mid-project:** `/onboarding` skips the `context_docs` phase entirely (per option B's restored phase). Already-installed rules are NOT auto-removed (per L17 / A9). The user is responsible for `rm` if they want them gone — claudechic does not own user-edited `.claude/rules/` content.

**Naming alternatives considered & rejected:**
- `claude_rules_enabled` — ambiguous with claudechic's own `guardrails` / `hints` enabled flags.
- `bundled_rules.install` — needless namespace nesting; we have one toggle.
- `install_context_docs` — uses the word "context_docs" which the existing onboarding terminology calls them, but the user-facing surface called them "rules" already; pick the surface-aligned name.

**One incidental amendment:** L17/A9's "no migration logic; no startup warnings" interacts with this toggle. If the user disables `install_claude_rules` after a previous run installed files, claudechic does **nothing** at startup — the files stay in place silently (per A9). This is consistent with the lock and requires no special handling.

---

## 3. Recommended path forward

### Option A — "Use the SDK loader directly; abandon the Group D mechanism."

**Concept:** trust the SDK to load `.claude/rules/` automatically via `setting_sources=["user", "project", "local"]` (already configured in `app.py:969`). **Don't ship any context files; rely on each user manually populating their `.claude/rules/`.**

**Spec impact:** `axis_awareness_delivery.md` collapses to ~30 lines: phase-context lifecycle only (no awareness mechanism at all). `claudechic/context_delivery/` package is not created. Three SDK hooks are not registered. The bundled `claudechic/context/*.md` files are deleted.

**Pros:** simplest possible implementation; zero touches inside `.claude/`.
**Cons:** **fails L15** — there is no claudechic-aware default. Users only see the awareness content if they manually copy files. **Reject.** This option is documented for completeness, not adopted.

### Option B — "Restore the `/onboarding context_docs` phase as the primary mechanism" **(RECOMMENDED)**

**Concept:** the bundled `claudechic/context/*.md` files (which already exist and contain the awareness/system-doc content) are copied into `<repo>/.claude/rules/` by the existing `/onboarding context_docs` phase. The SDK's existing `setting_sources=["user", "project", "local"]` (already in `app.py:969`) auto-loads them on every session. The mechanism is **install-time, not runtime.**

**Mechanics that already work for free** (no code from us):
1. **Always-on delivery (L15 piece 1).** SDK loads project rules at session start. ✅
2. **Survives `/compact`.** SDK re-injects rules after `/compact`. ✅ (No `PostCompact` hook for awareness needed.)
3. **First-read inside `.claudechic/` (L15 piece 2).** Optional `paths: ["**/.claudechic/**"]` frontmatter on the system docs (`workflows-system.md`, `hints-system.md`, etc.) gives lazy-load on `Read` of any `.claudechic/` file. ✅ (Caveat: `paths:` rules are project-tier only and only fire on `Read`; both are acceptable for this use.)
4. **Tier override.** SDK loads user-tier first, then project-tier; user-edits to `<repo>/.claude/rules/<filename>.md` ride alongside the package version (additively). The Memory docs note: *"All levels are additive: if both project and user CLAUDE.md files exist, the agent sees both."* — which differs from the current spec's "highest tier replaces" semantics, **but is closer to L15's intent**. (Open question: see §4.1.)
5. **Boundary observability.** `InstructionsLoaded` hook is available for our own diagnostics (which file was loaded, at session start vs. lazy-load). Optional; not required.

**Mechanics we own:**
1. `/onboarding context_docs` phase (already implemented at `claudechic/workflows/onboarding/onboarding_helper/context_docs.md`) — keep, harden per Target 4 gap list.
2. A new project-tier config key `install_claude_rules` (Target 5) gates the phase.
3. The `phase_context.md` write site (Group B) is unchanged: `<repo>/.claudechic/phase_context.md`, with the existing `PostCompact` hook in `agent_folders.py:147` (renamed and relocated only as far as Group A demands).
4. Add (optionally) `paths: ["**/.claudechic/**"]` YAML frontmatter to the seven system-doc files (per Target 4 gap list).
5. Add version comments (`<!-- claudechic-bundled: vX.Y.Z -->`) at top of each bundled file (Target 4).

**Spec changes needed (the buy-vs-build delta):**

| Spec section | Current state | Option B new state |
|---|---|---|
| `axis_awareness_delivery.md` §1–§8 (the entire awareness mechanism) | 8 sections, ~180 lines, three hook registrations + new module | **DELETE.** Replace with one paragraph: "claudechic context docs are installed into `<repo>/.claude/rules/` by the `/onboarding context_docs` phase; the SDK auto-loads them via `setting_sources`." |
| `axis_awareness_delivery.md` §9 (ContextDocsDrift retire) | Retire | **REVERSE.** Keep `ContextDocsDrift` as the trigger that hints "context docs out of date — re-run `/onboarding`". (This trigger is already designed for exactly this purpose.) |
| `axis_awareness_delivery.md` §10 (onboarding phase retire) | Retire | **REVERSE.** Keep the phase. Harden per Target 4. |
| `axis_awareness_delivery.md` §11 (boundary table) | Zero `.claude/` writes | **AMEND.** The `/onboarding context_docs` phase writes to `<repo>/.claude/rules/<filename>.md`. **Add allowlist entry** at SPEC §11.1: `<repo>/.claude/rules/<bundled_catalog>` — non-destructive incidental write under A7. The boundary-test spec gains one allowlist entry per filename in the bundled catalog (or one wildcard entry with the catalog as a closed list). |
| `axis_awareness_delivery.md` §13 (13 invariants) | Tests SessionStart payload, first-read tracker, etc. | **DELETE invariants AW-1, AW-1b, AW-2, AW-2b, AW-3, AW-4, AW-10, AW-11, AW-12, AW-13.** Keep AW-5 (phase-context path migrated), AW-6 (post-compact reads new path), AW-7 (ContextDocsDrift behavior — invert), AW-8 (onboarding phase shape — invert), AW-9 (phase-advance refresh — keep). Net: 13 → 5 invariants. |
| SPEC §4 (Group D) | 90 lines | **Shrinks to ~30 lines** covering only phase-context. |
| SPEC §11.1 (boundary allowlist) | No `.claude/rules/` entries | **Add:** `<repo>/.claude/rules/<filename>` for each `<filename>` in bundled catalog. Justification: "non-destructive incidental write under A7; `/onboarding context_docs` install path." |
| SPEC §11.4 (forbidden symlinks scope) | "no symlinks anywhere in agent-awareness mechanism" | **Unchanged.** Option B uses Read + Write (file copy), not symlinks. A4's prohibition is satisfied vacuously. |
| `STATUS.md` A4 | "claudechic-awareness mechanism = behavioral mirror, with explicit prohibitions" | **Amend** to note that "behavioral mirror" is achieved by **placing files where the mirror already runs**, not by reimplementing the mirror. Add: "permitted: write claudechic-owned bundled-rule files into `<repo>/.claude/rules/` and `~/.claude/rules/` per the install-time A7 carve-out." |
| `STATUS.md` A11 (two-piece) | Two-piece confirmed | **Unchanged.** Two-piece is delivered: piece 1 = frontmatter-less files; piece 2 = `paths:` files. |

**Testing impact:** `tests/test_context_delivery.py` (planned but not yet written) becomes `tests/test_context_docs_install.py` covering NEW/UPDATE/SKIP semantics + boundary allowlist + the toggle key. The two SDK-uncertainty items in SPEC §12 (SessionStart hook + PreToolUse `additionalContext`) **become non-issues** — we don't use those mechanisms.

**Risks / dependencies for this option:**
1. **A4-spec conformance.** Writing inside `.claude/rules/` is permitted under A7's "non-destructive incidental write" framing, but the current spec (R5.1 + axis §11) classifies awareness content as **primary state** to forbid this exact write. **The user must explicitly resolve this:** is the bundled-rule install a "primary-state write" (forbidden) or a "non-destructive incidental write" (permitted)? The vision-amendment language for A4/A7 was written before this option existed; it needs an A13 to settle. **This is the single biggest dependency.** [WARNING] Domain validation required — boundary-rule specifics matter.
2. **`paths:` frontmatter bug-state.** Per Target 2, project-tier `paths:` rules work but have edge-case bugs on Write-only operations and on user-tier scoping. Option B uses `paths:` at project tier only and only relies on Read-side firing — both within the supported envelope. No dependency on Anthropic fixing the bugs.
3. **Loader semantics differ from current spec.** SDK is "additive across tiers"; current spec is "highest tier replaces." This is actually a behavior **gain** (user customizations don't have to repeat the package content) but flips override semantics. Composability axis (R3) needs to acknowledge.

### Option C — "Build our own per current spec"

**Concept:** what the spec already says. `claudechic/context_delivery/` package + 3 SDK hooks + per-session tracker + size budgets + PostCompact hook + sentinel tests.

**Why we still consider it:** if A4/A7 cannot be relaxed for `.claude/rules/` writes (i.e., the user reaffirms that **all** writes inside `.claude/` are forbidden, including non-destructive ones the SDK natively expects to find there), Option B is dead and Option C is the path.

**Cost:** ~600 lines of code in `context_delivery/` + hook callbacks; 13 invariants worth of tests; the three SDK-uncertainty risks in SPEC §12 (SessionStart not in `HookEvent` literal; PostCompact not in literal; PreToolUse `additionalContext` may be ignored on older CLIs). **All three uncertainties go away in Option B.**

---

## 4. Open questions for the team

### 4.1 Tier-merge semantics

The SDK loads user + project rules **additively** (per Memory docs: "All levels are additive"). The current `axis_awareness_delivery.md` §3.3 specifies "highest tier replaces; no merging." **Option B inherits the SDK's additive semantics for free, but this contradicts the current axis spec.** Composability + user need to confirm whether additive is acceptable. Recommendation: **adopt additive** — it's the upstream semantic and gives users the better outcome (their customizations augment ours without copy-paste).

### 4.2 User-tier install

The current `/onboarding context_docs` phase only writes to `<repo>/.claude/rules/`. Should the install also offer a `--user` mode that writes to `~/.claude/rules/`? Pros: one-time install per dev machine, every project benefits. Cons: cross-project pollution; user-tier `paths:` scoping is buggy per Target 2. **Recommendation: defer — project-tier-only on first cut; revisit if users ask.**

### 4.3 ContextDocsDrift trigger semantics

If we keep the trigger (Option B reverses §9 of the axis spec), what does "drift" mean? Today's hint just compares file mtimes. With versioned bundled files (Target 4 gap "version tracking"), drift = bundled version newer than installed version. **Recommendation:** make the version comparison the trigger predicate. Hint message: "claudechic has been upgraded; re-run `/onboarding` to refresh `.claude/rules/`."

### 4.4 What about `.claudechic/` content the user authors locally?

The current spec recognized `<repo>/.claudechic/context/` and `~/.claudechic/context/` as alternate roots for the awareness content. Under Option B, **the SDK doesn't look in `.claudechic/context/`** — it looks in `.claude/rules/`. Should claudechic optionally also load files from `<repo>/.claudechic/context/*.md` and concatenate them with the bundled set during install? **Recommendation: yes, as a follow-up.** It's a small addition to the install phase: copy `<package>/context/*.md` AND `<repo>/.claudechic/context/*.md` (project additions) AND `~/.claudechic/context/*.md` (user additions) into `<repo>/.claude/rules/`. Explicit, auditable, no loader magic.

### 4.5 [WARNING] Domain validation required: A4/A7 reinterpretation

Option B's viability hinges on whether writing `<repo>/.claude/rules/<bundled_filename>.md` qualifies as a "non-destructive incidental write" under A7. The user's exact phrasing was:

> Permitted: non-destructive touches to `.claude/` (e.g., reading; writing *new*, *non-colliding*, *cross-platform* files claudechic owns).

The bundled filenames are claudechic-owned (we ship them). They are non-colliding in the sense that the catalog is closed and known. They are cross-platform (pure file I/O). **All three A4-permitted predicates are satisfied.** The conflict is with the *spec's* (not the vision's) R5.1 classification of awareness content as "primary state." This is a spec-author choice that can be revisited; it is not locked by L1–L17 or A1–A12.

**The user should confirm:** is "primary state" defined by *where the content originates* (claudechic codebase = primary) or *where the content lives at runtime* (`.claude/rules/` = SDK runtime data, secondary)? **The latter framing makes Option B legal under A7 without amendment.** The team should request explicit user resolution.

---

## 5. Sources

| Tier | Source |
|---|---|
| T1 | [Use Claude Code features in the SDK — code.claude.com/docs/en/agent-sdk/claude-code-features](https://code.claude.com/docs/en/agent-sdk/claude-code-features) |
| T1 | [How Claude remembers your project — code.claude.com/docs/en/memory](https://code.claude.com/docs/en/memory) |
| T3 | [anthropics/claude-agent-sdk-python — GitHub](https://github.com/anthropics/claude-agent-sdk-python), MIT license, CI-tested. |
| T3 | [anthropics/claude-code issue #13905 (closed)](https://github.com/anthropics/claude-code/issues/13905) — frontmatter docs fixed. |
| T3 | [anthropics/claude-code issue #17204 (open)](https://github.com/anthropics/claude-code/issues/17204) — `paths:` quoted-list bug. |
| T3 | [anthropics/claude-code issue #21858 (closed-stale)](https://github.com/anthropics/claude-code/issues/21858) — user-tier `paths:` ignored. |
| T3 | [anthropics/claude-code issue #23478 (closed-stale)](https://github.com/anthropics/claude-code/issues/23478) — `Write` doesn't fire `paths:` rules. |
| T3 | [anthropics/claude-code issue #30573 (closed)](https://github.com/anthropics/claude-code/issues/30573) — `InstructionsLoaded` hook docs. |
| T5 | [carlrannaberg/cclint](https://github.com/carlrannaberg/cclint), MIT, CI. |
| T5 | [pdugan20/claudelint](https://github.com/pdugan20/claudelint), MIT, CI. |
| T5 | [stbenjam/claudelint](https://github.com/stbenjam/claudelint), Apache-2.0, Python. |
| T5 | [`python-frontmatter` on PyPI](https://pypi.org/project/python-frontmatter/), MIT. |

---

*End of RESEARCH.md.*
