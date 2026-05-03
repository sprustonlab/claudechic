# Composability Specification — `independent_chic`

**Lens:** Composability (axes, seams, compositional law)
**Phase:** Specification
**Audience:** Operational-spec authors, Implementer agents, Tester agents
**Mode:** This document records normative architectural constraints derived from the Composability lens. It is one of four lens-spec inputs that the Coordinator will fold into the operational spec + appendix (per L14). Statements use **MUST**, **SHOULD**, **MAY**, **MUST NOT** in the RFC-2119 sense.

**Inputs:**
- Leadership-phase output: `composability_eval.md` (10 axes; 7-group decomposition; 10 holes/smells)
- Locked decisions L1–L17 + amendments A1–A12 (STATUS.md)
- Direct codebase reads (file:line refs preserved from Leadership phase)

**This document is rationale-light by design.** It states *what* the design must satisfy, not *why* the lens reached those conclusions. The "why" lives in `composability_eval.md` (lens analysis) and will be carried into the appendix.

---

## 1. Project type & domain frame

Per `claudechic/workflows/project_team/project_types.md`, this work matches the **Refactoring** type (signals: "refactor", "restructure"). The default Refactoring axes are:

> BeforeVsAfter, PublicVsInternal, TestCoverage, DependencyDirection, BreakingVsNonBreaking

These are useful starting points; they map as follows:

| Default Refactoring axis | Mapping to this project |
|---|---|
| **BeforeVsAfter** | Restructure preserves *behavior* (no semantic change for end-user agents); only internal layout shifts. Encoded in §6 invariant **INV-1**. |
| **PublicVsInternal** | The user-facing "public" surface = `~/.claudechic/` and `<repo>/.claudechic/` (3-tier content) + the `/settings` UI + `docs/configuration.md`. The "internal" surface = engine modules under `claudechic/`. The boundary is hard. Encoded in §6 invariant **INV-3**. |
| **TestCoverage** | Boundary enforcement test (A7-aware) and override-resolution tests are required. Encoded in §6 invariant **INV-7**. |
| **DependencyDirection** | Loader → tier walker → manifest parser is one-way. Hint state and config layers do not import workflow_engine. Encoded in §5 seam protocols. |
| **BreakingVsNonBreaking** | Breaking for state-file paths; non-breaking for content semantics. Per L17 + A9, breakage is silent (no migration, no startup warnings). Spec authors must not add migration logic. |

The actual axes (next section) are *additional to* these defaults — the Refactoring axes are about how-the-work-happens; the project-specific axes are about how-the-result-composes.

---

## 2. Axes (final, post-amendments)

The Leadership-phase eval identified **10 axes** (6 runtime + 4 process). Amendments A4–A12 closed open mechanism questions on some of these. The final axis list, with values and binding constraints:

### Runtime axes (define system behavior at execution time)

| # | Axis | Values | Binding constraints |
|---|---|---|---|
| **R1** | **Tier** — where any piece of content lives | `package` \| `user` \| `project` | L7 (paths); §1 of vision (priority order: project > user > package) |
| **R2** | **Content category** — what kind of content | `workflow` \| `rule` \| `hint` \| `mcp_tool` | §1 of vision (the four categories) |
| **R3** | **Resolution semantics** — how tiers combine for a given category | per-category override-by-id (workflows: by `workflow_id`; rules/hints: by `id`; mcp_tools: by `tool.name`) — see §3 below | Locked here as part of the spec; previously open |
| **R4** | **Config layering** | `user-tier` \| `project-tier`; defaults in code; no package-tier config file | L8 (reaffirmed by **A5**); L9 (`analytics.id` user-only) |
| **R5** | **Boundary** — what writes go where | `claudechic-primary-state-write` MUST go under `.claudechic/` (forbidden in `.claude/`); `non-destructive-incidental-write` MAY go inside `.claude/` (permitted by **A7**); `read-from-.claude/` is unrestricted; `read-from-.claudechic/` is normal | **A7** (primary-state-only boundary); **A4** (no symlinks; no overwriting Claude-owned settings) |
| **R6** | **Agent-awareness delivery** | always-on (session start) + once-per-agent-session (first read inside `.claudechic/`) | **L15 + A11** (two-piece); **A4** (behavioral mirror; no symlinks; no overwriting Claude-owned settings; non-destructive `.claude/` write permitted under A7) |
| **R7** | **Artifact-dir lifetime/scope** | per-workflow-run (recommended) \| per-chicsession \| per-launched-repo | Vision §6; mechanism still **OPEN** for spec authors; this lens recommends per-workflow-run with env-var path discovery (see §4 R7) |
| **R8** | **Worktree state propagation** | parallel-symlink-pattern (existing for `.claude/`; extends to `.claudechic/`) | Existing `git.py:293–301` pattern; symlinks-of-claudechic-state are an existing pattern, distinct from R6's prohibition (R6 forbids symlinks *as the agent-awareness delivery mechanism*; the worktree-state-propagation symlink at `git.py:293–301` is a separate, pre-existing concern that is not subject to A4's symlink prohibition) |

### Process axes (define how work decomposes)

| # | Axis | Values | Binding constraints |
|---|---|---|---|
| **P1** | **Cross-fork integration order** | restructure-first (preferred) \| pull-first \| parallel | Vision §"Open for the new team to decide"; cherry-pick set fully decided (**A2 + A8**) |
| **P2** | **Spec/appendix decomposition** | spec-only \| spec+appendix-split | **L14** (binding: spec strictly operational; rationale in appendix) |
| **P3** | **Implementer/Tester decomposable work units** | seven groups (A–G), see §7 below | Composability lens recommendation (operational; Implementer agents consume) |
| **P4** | **Lens responsibility separation** (this spec lives in the Composability lane) | Composability \| Terminology \| Skeptic \| UserAlignment | Project-team workflow shape; per-lens spec inputs assemble into one operational spec + one appendix |

### Disambiguating R8 vs A4 (worktree symlink vs no-symlink prohibition)

A4's "no symlinks anywhere in the mechanism" applies to **R6 (agent-awareness delivery)** specifically. The pre-existing worktree symlink at `features/worktree/git.py:293–301` is a **filesystem state-propagation mechanism**, not an agent-awareness delivery mechanism. The symlink is unsupported on Windows, but worktree-creation today already uses it; the spec MAY preserve the existing symlink-on-POSIX pattern for `.claudechic/` parallel symlinks **provided** Windows-platform behavior is documented (the existing `.claude/` symlink already has the same Windows limitation; adding `.claudechic/` does not worsen it). If the spec authors choose to remove the symlink in favor of a cross-platform mechanism (e.g., per-worktree fresh state, or repo-tracked state), that is permitted but is a larger change than the boundary work requires.

**Composability lens recommendation:** preserve existing pattern in this run; flag cross-platform worktree-state-propagation as a follow-up concern. Do not couple this work to R6.

---

## 3. Compositional law

The crystal of all valid configurations across R1×R2 has **3 × 4 = 12 cells** for content (plus the additional dimensions of R3–R8). For the crystal to hold without holes, every cell must yield a working system. The compositional law that guarantees this is:

**The byte-and-id law:**
> Every content category is a bag of typed records keyed by an identity unit. The tier walker (one piece of code) yields per-tier `(tier, manifest_path, raw_yaml)` triples. Each per-category parser implements two operations:
> - `parse(raw_yaml, tier) -> list[record]` — produces typed records, each tagged with provenance.
> - `resolve(records_per_tier: dict[tier, list[record]]) -> list[record]` — produces the effective set after override resolution.
>
> The tier walker does not know category semantics. The parser does not know how tiers are walked. They share only a typed-record schema and a tier-tag.

For non-content axes (R4 config, R5 boundary, R6 awareness, R7 artifact, R8 worktree) the law is narrower:

| Axis | Compositional law |
|---|---|
| R4 (config) | Each config key is a typed record with an explicit tier-pin (`user-only` or `project-only`). Resolution is per-key with code-defined fallback. No key may be tier-pinned to both. |
| R5 (boundary) | Every claudechic write call site is classified at code-review time as `primary-state` or `non-destructive-incidental`. Primary-state writes MUST resolve to a path under a `.claudechic/` root. The boundary test (CI) operates on this classification, not on path-string heuristics alone. |
| R6 (awareness) | Both pieces (always-on and first-read) source their content from `<some_root>/.claudechic/...` files (file-based law). The two pieces share a content-source contract; only the trigger differs (timing). |
| R7 (artifact dir) | The artifact dir path is exposed to spawned agents as a single canonical token (env var or system-prompt placeholder). Agents do not hard-code the path. |
| R8 (worktree) | Existing `.claude/` symlink pattern extends to `.claudechic/`. Both symlinks live inside the worktree dir (so `git worktree remove` cleans them). |

**Why this is algebraic:** with these laws, you do not need to test every (tier, category) combination. You test:
1. Each parser obeys the parse/resolve law.
2. The tier walker obeys the (tier, path, raw) law.
3. Composition is by construction — adding a new tier means changing only the walker; adding a new category means writing a new parser; the cross-product cells inherit correctness from the laws.

**Smells the law eliminates** (non-exhaustive):
- "Workflows from package tier conflict with hints from project tier" — different categories are independent; one parser per category.
- "Hint state file path differs by tier" — hint state is itself a runtime concern keyed by hint id; tier of origin does not affect storage.
- "Override only works for some content categories" — every category implements `resolve()`; the spec MUST forbid categories that opt out.

---

## 4. Per-axis spec items (normative)

These are the constraints the operational spec must encode. They are **not** instructions for how to write code; they are constraints the code must satisfy.

### R1 — Tier

- **R1.1 [MUST]** The three tier roots are exactly: package = `claudechic/defaults/`, user = `~/.claudechic/`, project = `<launched_repo>/.claudechic/`. No fourth tier MAY be introduced in this work.
- **R1.2 [MUST]** Every tier MUST follow the same directory layout: `workflows/<workflow_id>/<role>/{identity,phase}.md`, `global/rules.yaml`, `global/hints.yaml`, `mcp_tools/*.py` (plus `_*.py` helpers).
- **R1.3 [MUST]** Tier presence is independent: a tier MAY be empty or absent. The system MUST function correctly when any non-package tier is missing.
- **R1.4 [MUST]** Resolution priority is `project > user > package`. This is fixed; the spec MUST NOT introduce a configuration knob that reorders tiers.

### R2 — Content category

- **R2.1 [MUST]** The four content categories are: `workflow`, `rule`, `hint`, `mcp_tool`. No fifth category MAY be introduced in this work.
- **R2.2 [MUST]** Each category MUST be loaded by a single, dedicated parser implementing the parse/resolve law (§3). No category MAY be "loaded inline" without going through this contract.
- **R2.3 [MUST]** MCP tools are loaded by Python module import, not YAML parsing. The tier-walking logic for MCP tools MAY be a separate function from the YAML tier walker, but MUST follow the same parse-then-resolve shape (parse = `import + get_tools()`; resolve = override-by-tool-name).
- **R2.4 [SHOULD]** Adding a fifth category in a future change SHOULD require only: (a) a new parser, (b) registration with the loader. No edits to the tier walker or to other parsers.

### R3 — Resolution semantics (per category)

- **R3.1 [MUST]** Each category resolves by an explicit identity unit. The mapping is fixed:
  - `workflow` → identity = `workflow_id` (the field in the workflow YAML manifest)
  - `rule` → identity = `rule.id`
  - `hint` → identity = `hint.id`
  - `mcp_tool` → identity = `tool.name`
- **R3.2 [MUST]** When the same identity appears at multiple tiers, the highest-priority tier's record fully replaces lower-tier records of the same identity. Field-level merging across tiers MUST NOT occur (no "user overrides priority but inherits message"). This rule is uniform across all four categories.
- **R3.3 [MUST]** When a workflow is overridden by identity, the override applies to the *entire* workflow including its associated role/phase markdown files. The spec MUST NOT permit a project-tier `workflow_id` whose role files come partly from package-tier and partly from project-tier — the winning tier owns the workflow's full file set.
- **R3.4 [MUST]** When identities are non-conflicting across tiers, items accumulate. (E.g., a project rule with `id: foo` and a package rule with `id: bar` both end up active; only same-id overrides.)
- **R3.5 [MUST]** Within a single tier, duplicate identities are an error (logged; lower-priority duplicate dropped). The current loader's "duplicate ID error" check (loader.py:344) MUST be preserved for **within-tier** duplicates and inverted for **cross-tier** duplicates.
- **R3.6 [MUST]** Every parsed record MUST carry tier provenance (a `tier: Literal["package","user","project"]` attribute). This provenance MUST be available to UI surfaces (workflow picker showing per-tier source) and to diagnostic tools.

### R4 — Config layering

- **R4.1 [MUST]** Config keys are 2-tier (user, project). There is no package-tier config file (no `claudechic/defaults/config.yaml`). Defaults live in code (`ProjectConfig` dataclass defaults at `config.py:94` and equivalents for user-tier).
- **R4.2 [MUST]** Each config key is tier-pinned. The pinning is canonical and lives in one place (recommended: a single registry at `config.py` module scope). Per L9, `analytics.id` is user-tier; per vision §2 the user-tier set includes `analytics.enabled`, `default_permission_mode`, `worktree.path_template`, `themes`, `show_message_metadata`; the project-tier set includes `guardrails`, `hints`, `disabled_workflows`, `disabled_ids`. The spec MUST publish the canonical list.
- **R4.3 [MUST]** A config key MUST NOT be settable at both tiers. If a future need arises, it MUST be split into two keys (or the design re-considered).
- **R4.4 [MUST]** Config resolution is per-key: read project value if present and project-pinned; else user value if present and user-pinned; else dataclass default.
- **R4.5 [SHOULD]** R4 logic MUST NOT share code with R3 (content tier walker). They have different shapes; one generic mechanism with conditionals would be a smell.

### R5 — Boundary (per A7)

- **R5.1 [MUST]** Every claudechic write site MUST be classified at code-review time as exactly one of:
  - `primary-state` — config files, hint state, phase context, session-state derivatives, artifact-dir contents. These MUST resolve to a path under `.claudechic/` (one of the three tier roots).
  - `non-destructive-incidental` — newly-created, claudechic-named files inside `.claude/` that do not collide with Claude-owned files. These MAY exist; their presence MUST NOT prevent Claude Code from operating normally.
- **R5.2 [MUST]** No write site MAY overwrite a Claude-owned settings file inside `.claude/` (e.g., `settings.json`, `settings.local.json`). Per A4 absolute prohibition.
- **R5.3 [MUST]** No mechanism in this work MAY create symbolic links inside `.claude/` (per A4 absolute prohibition; cross-platform). The R8 worktree symlink at `features/worktree/git.py:293–301` already creates a symlink targeting `.claude/`, but that symlink lives *inside the worktree dir*, not inside `.claude/`; this is permitted (pre-existing pattern).
- **R5.4 [MUST]** The boundary CI test MUST distinguish R5.1's two classes. A path-string-only test is insufficient under A7. Recommended encoding: a registry mapping each known write site (file:line, or a callable identity) to its R5.1 classification, and an enforcement that all primary-state classifications resolve to `.claudechic/` paths.
- **R5.5 [MUST]** Reads from `.claude/` are unrestricted and MUST continue to work for legitimate introspection (sessions JSONL, OAuth credentials, settings.json, plugin info). The boundary test MUST NOT regress these reads.

### R6 — Agent-awareness delivery (per A4 + L15 + A11)

- **R6.1 [MUST]** Two pieces:
  - **always-on:** every claudechic-spawned agent MUST receive a short claudechic-awareness statement at session start. The exact prose is delegated to TerminologyGuardian and the operational spec; the Composability lens does not specify the wording.
  - **first-read:** every claudechic-spawned agent MUST receive a fuller-context injection on the *first* tool-read of any path under any `.claudechic/` directory in that agent's session. Subsequent reads in the same session MUST NOT re-inject.
- **R6.2 [MUST]** "First read" tracking is per-agent-session, in-memory state (no on-disk persistence). A new agent session is a new tracking instance.
- **R6.3 [MUST]** The fuller-context content MUST be sourced from files (not hard-coded prompt text). The recommended source root is `claudechic/defaults/context/` (the existing `claudechic/context/` directory, post-restructure). The spec MAY allow project-tier overrides (`<repo>/.claudechic/context/`) but is not required to in this run.
- **R6.4 [MUST]** No symbolic links anywhere in this mechanism (A4). No overwrite of Claude-owned settings files (A4). No primary-state writes inside `.claude/` (A7 + R5.1).
- **R6.5 [MUST]** The R6 mechanism and the existing `phase_context.md` delivery (currently at `.claude/phase_context.md`, app.py:1848) MUST share an implementation. Both deliver file-sourced content from `.claudechic/` to a Claude session via a non-`.claude/`-write mechanism. Two parallel implementations would be a smell.
- **R6.6 [SHOULD]** Mechanism choice is delegated to the operational spec, but MUST be one of:
  - SDK `append_system_prompt` for always-on; SDK hook (PreToolUse on Read tool) for first-read.
  - SDK SessionStart hook for always-on + phase context; SDK PreToolUse hook for first-read.
  - A non-destructive-incidental write inside `.claude/` (A7-permitted) that Claude Code auto-loads natively, *if* the team is confident the write is non-colliding and cross-platform. (This option is permitted by A4+A7 but is the highest-risk path for unintended Claude Code coupling; the Skeptic lens should weigh in.)
- **R6.7 [MUST NOT]** The mechanism MUST NOT involve writing into `.claude/rules/` (Claude-owned; even non-destructive writes are risky here because Claude Code reads everything in this directory as authoritative rules — collision risk with user's own rules is high). This is a tighter prohibition than R5 for this directory specifically.

### R7 — Artifact-dir lifetime/scope

- **R7.1 [MUST]** Workflows that produce artifacts in a setup phase MUST have access to a designated artifact dir. The spec MUST specify the lifetime/scope.
- **R7.2 [SHOULD]** Recommended lifetime: per-workflow-run, rooted at `<repo>/.claudechic/runs/<run_id>/` (or equivalent). Rationale: clean isolation, garbage-collectable, name-stable across phase transitions.
- **R7.3 [MUST]** The artifact dir path MUST be exposed to spawned agents via a single canonical token. Recommended: env var `CLAUDECHIC_ARTIFACT_DIR` set in the spawn env at agent creation (extending the existing env-var pattern in `app.py` `_make_options`, which already sets `CLAUDE_AGENT_NAME`, `CLAUDECHIC_APP_PID`, `CLAUDE_AGENT_ROLE` at app.py:951–958).
- **R7.4 [MUST NOT]** Workflow role markdown files MUST NOT hard-code artifact dir paths. They reference the canonical token (e.g., `${CLAUDECHIC_ARTIFACT_DIR}` or equivalent placeholder that `agent_folders.py` substitutes). Hard-coded paths break R1.3 (tier independence) — a project-tier override of the workflow inherits the wrong path.
- **R7.5 [MUST]** Artifact dir creation is the engine's responsibility (at workflow activation), not the agent's. The dir MUST exist before the first phase agent reads from it.

### R8 — Worktree state propagation

- **R8.1 [MUST]** A parallel `.claudechic/` symlink MUST be added at `features/worktree/git.py:293–301`, mirroring the existing `.claude/` symlink. The symlink target is `<main_wt>/.claudechic/`.
- **R8.2 [MUST]** Symlinks live *inside the worktree directory*, not inside `.claude/` (consistent with R5.3). `git worktree remove` cleans them implicitly.
- **R8.3 [MUST]** The symlink creation is `is_dir()`-guarded (existing pattern). If `<main_wt>/.claudechic/` does not exist (e.g., very fresh repo with no claudechic state yet), the symlink MUST NOT be created.
- **R8.4 [MAY]** A future change MAY replace this symlink-based approach with a cross-platform alternative. Such a change is out of scope for this run.

---

## 5. Seam protocols (operational interface specs)

Where two axes meet, the seam MUST allow data to cross while preventing implementation details and assumptions from crossing. Each seam below is a code interface the spec MUST encode.

### Seam-A: Tier walker ↔ Manifest parser (R1 ↔ R2)

```
TierWalker.walk(tier_roots: dict[tier, Path]) -> Iterable[(tier, category, manifest_path, raw_yaml)]
ManifestParser[T].parse(raw_yaml, tier, source_path) -> list[T]  # T tagged with tier
ManifestParser[T].resolve(items_per_tier: dict[tier, list[T]]) -> list[T]
```

**What crosses:** typed records, tier provenance, raw YAML, source paths.
**What does NOT cross:** parser-internal logic, tier-walker discovery details.
**Swap test:** changing the tier walker (e.g., adding a fourth tier later) MUST NOT require touching any parser. Changing a parser (e.g., new resolution policy for hints) MUST NOT require touching the tier walker.

### Seam-B: Content loader ↔ Engine consumers (R2 → engine, hints, app)

```
LoadResult { rules, injections, checks, hints, phases, workflows, errors }   # post-resolve
LoadResult.rules : list[Rule]   # tier-tagged, override-resolved
LoadResult.workflows : dict[workflow_id, WorkflowData]   # tier-tagged
```

**What crosses:** the post-resolve flat collections + per-workflow data.
**What does NOT cross:** per-tier source paths into engine code (engine doesn't know where a rule "came from"); tier-walking logic.
**Spec MUST encode:** `LoadResult` items MUST carry tier provenance for UI display, but engine logic (rule evaluation, hint matching, phase advance) MUST treat tier-tag as opaque metadata, not a control switch.

### Seam-C: Agent-awareness mechanism ↔ phase-context delivery (R6 ↔ legacy phase_context)

```
ContextSource.read(path: Path) -> str | None
ContextDelivery.always_on(content: str)         # session-start hook contract
ContextDelivery.on_first_claudechic_read(content: str)   # PreToolUse hook contract
```

**What crosses:** file content (str).
**What does NOT cross:** phase-context-specific assumptions; agent-awareness-specific assumptions. Both are file-content delivery to Claude.
**Spec MUST encode:** the same `ContextDelivery` implementation services both phase-context (read from `<repo>/.claudechic/phase_context.md`) and agent-awareness (read from `claudechic/defaults/context/*.md`). One mechanism; two registrations.

### Seam-D: Hint state ↔ hint identity (R3 ↔ hint pipeline)

The current `HintStateStore` (state.py:131) keys lifecycle records by hint `id`. Under R3.2 (override-by-id), an overridden hint at user/project tier KEEPS the same id. Lifecycle state MUST therefore continue to apply across overrides without reset.

**What crosses:** hint id, lifecycle record.
**What does NOT cross:** tier provenance (lifecycle state is tier-agnostic by design — a "show-once" hint stays show-once whether the package or user defined it).
**Spec MUST encode:** hint state JSON schema is unchanged. Tier provenance is loader-time only; the runtime hint pipeline sees override-resolved hints.

### Seam-E: Boundary test ↔ write-site classification (R5)

```
WriteClassification = Literal["primary-state", "non-destructive-incidental"]
classify(write_site: WriteSite) -> WriteClassification    # human-curated registry
test_no_primary_state_in_dot_claude(repo) -> None         # CI assertion
```

**What crosses:** write-site identity (file:line or callable), classification.
**What does NOT cross:** path string heuristics (insufficient under A7).
**Spec MUST encode:** the registry of every claudechic write site, with classification. The test enforces R5.1.

### Seam-F: Engine-spawned agent ↔ artifact-dir token (R7)

```
ENV: CLAUDECHIC_ARTIFACT_DIR=<absolute path>   # set at spawn time, read by agent
agent_folders._assemble_agent_prompt(...)   # may substitute ${CLAUDECHIC_ARTIFACT_DIR} in markdown
```

**What crosses:** an absolute path (string).
**What does NOT cross:** workflow-internal layout assumptions (the agent doesn't know "this is a per-run dir under runs/"); engine-internal scheduling.
**Spec MUST encode:** the env var name is canonical. Markdown substitution is optional but MUST NOT be the only way to discover the path (env var is the primary mechanism).

---

## 6. Crystal-test invariants

The spec MUST encode the following invariants. Each invariant is a one-line property that the test suite (and a careful code review) can verify.

| ID | Invariant |
|---|---|
| **INV-1** | A user adding `~/.claudechic/workflows/foo/` MUST be able to override a package-tier `foo` workflow without modifying any project file. (R1, R3.3) |
| **INV-2** | A project adding `<repo>/.claudechic/workflows/foo/` MUST override both user-tier and package-tier `foo`. (R1.4, R3.3) |
| **INV-3** | The system MUST function with no user tier (`~/.claudechic/` absent) and no project tier (`<repo>/.claudechic/` absent) — package-only operation. (R1.3) |
| **INV-4** | The same `id` at two tiers for any content category MUST resolve to exactly one record (the higher-priority tier's). (R3.2) |
| **INV-5** | The same `id` at the same tier MUST surface as a load error. (R3.5) |
| **INV-6** | No claudechic write site classified as `primary-state` resolves to a path under `.claude/`. (R5.1, R5.4) |
| **INV-7** | The boundary test (INV-6) and the override-resolution tests (INV-1, INV-2, INV-4, INV-5) MUST exist in the test suite at the close of the implementation phase. (P3, Refactoring/TestCoverage axis) |
| **INV-8** | Hint lifecycle state survives override (a project-tier hint with the same id as a package-tier hint inherits the package-tier hint's `times_shown` and `dismissed` state). (Seam-D) |
| **INV-9** | Phase-context delivery and agent-awareness delivery share an implementation (one `ContextDelivery` impl, two registrations). (Seam-C, R6.5) |
| **INV-10** | Worktree creation in a repo with `<main_wt>/.claudechic/` results in the new worktree containing both `.claude` and `.claudechic` symlinks pointing into the main worktree. (R8.1, R8.3) |
| **INV-11** | Spawning an agent inside an active workflow run results in `CLAUDECHIC_ARTIFACT_DIR` being set in the agent's env to an absolute path that exists. (R7.3, R7.5) |
| **INV-12** | Workflow role markdown files in the repo MUST NOT contain a literal path string `<repo>/.claudechic/runs/` (or whatever the artifact-root pattern is) — they MUST use the env-var token. A grep-test enforces this. (R7.4) |

These twelve invariants are the **10-point test** for this crystal: if any one fails, the design has a hole and the relevant axis decomposition needs review.

---

## 7. Decomposable work units (operational handoff to Implementer/Tester)

The spec MAY structure implementation in seven groups (carried forward from `composability_eval.md` §6, updated for A4–A12). Each group is an independent work unit; dependencies are minimal.

| Group | Scope | Depends on |
|---|---|---|
| **A. Restructure (file moves, no behavior change)** | git-mv engine Python (workflow_engine → workflows); git-mv bundled YAML (workflows → defaults/workflows); git-mv globals (global → defaults/global); git-mv mcp_tools → defaults/mcp_tools; update 22 import sites; update 5 path-reference sites; delete empty dirs. Per File-move inventory in vision. | — |
| **B. Boundary relocation (state files)** | Move user config (`~/.claude/.claudechic.yaml` → `~/.claudechic/config.yaml`); move project config to `<repo>/.claudechic/config.yaml`; move hint state to `<repo>/.claudechic/hints_state.json`; move phase context to `<repo>/.claudechic/phase_context.md`; add parallel `.claudechic/` symlink at `git.py:293–301`; doc-surface rewrite (six files). Per L17/A9: no migration logic, no startup warnings. | — |
| **C. 3-tier loader + override resolution** | Refactor `discover_manifests` into a tier walker; add tier provenance to parsed records; implement per-category `resolve()` per R3.1–R3.6; invert duplicate-id-error to within-tier-only; generalize `discover_mcp_tools` to walk three tiers; reimplement fallback-discovery logic from scratch (per A8 — d55d8c0 NOT cherry-picked). | A |
| **D. Agent-awareness mechanism** | Implement R6.1–R6.7. Reuse mechanism for phase-context delivery (R6.5). Decide fate of `ContextDocsDrift` trigger and `context_docs` onboarding phase (recommended: retire both). | A, B |
| **E. Artifact dirs** | Per R7.1–R7.5. Engine creates dir at workflow activation; sets `CLAUDECHIC_ARTIFACT_DIR` env var at agent spawn; phase docs use canonical token. | A |
| **F. Cherry-picks (non-restructure abast commits)** | Land 9fed0f3 (docs), 8e46bca (resolved workflows_dir), f9c9418 (full model ID), 5700ef5 + 7e30a53 (auto permission default + Shift+Tab). NOT d55d8c0 (per A8). | A (8e46bca only) |
| **G. UI + docs (#23 deliverables)** | `/settings` TUI screen exposing R4-pinned user keys; `docs/configuration.md` reference page; workflow-button surface showing tier provenance per R3.6. | A, B, C |

**Dependency graph (minimal):**
```
A ──> B ──> D
 │      │
 ├──> C ──> G
 │      │
 └──> E
        │
F (mostly orthogonal; F includes one item depending on A)
```

The spec MAY assign each group to a separate Implementer agent. The dependency arrows are minimal; the spec MAY impose stricter ordering for review-load reasons.

---

## 8. Recommended deep-dive review areas

The Composability lens flags three areas that warrant focused spec authoring or focused review by another lens:

### 8.1 R6 mechanism choice (Composability + Skeptic + UserAlignment together)

R6.6 lists three permitted mechanism families. Each carries different tradeoffs:

| Mechanism | Composability fit | Risk profile (defer to Skeptic) | UX fit (defer to UserAlignment) |
|---|---|---|---|
| `append_system_prompt` (always-on) + PreToolUse hook (first-read) | Good — separates the two pieces cleanly into two hooks | Low (no `.claude/` writes; uses documented SDK extension points) | "Behavioral mirror" achieved: agent sees rule-equivalent context delivered automatically |
| SessionStart hook for both always-on and phase-context | Good — single hook entry point unifies R6 and phase-context (best Seam-C composition) | Low | Same as above |
| Non-destructive-incidental write inside `.claude/` (A7-permitted) | Possible — but couples to Claude Code's auto-load semantics, which claudechic does not control | Medium — Claude-Code-version-coupling risk; collision risk if Claude adds files with similar names | Closest literal mirror of `.claude/rules/`, but most fragile |

**Composability recommendation:** the second option (SessionStart hook unification). Composability lens does not own the final call; Skeptic and UserAlignment should weigh in.

### 8.2 R3 within-category fine print (Composability owns)

R3.1–R3.6 lock identity-unit and override-vs-merge per category. Two sub-questions remain:

- **`disabled_workflows` and `disabled_ids` semantics** (Hole 8 from `composability_eval.md`): if the project config disables workflow `foo`, does that disable `foo` at all tiers or only the project-tier `foo`? **Spec answer (this lens recommends):** disable-by-id is tier-agnostic — disabling `foo` removes it from the effective set regardless of which tier defined it. Rationale: feature-toggles are about *whether the user wants the feature*, not about *which copy of it*.
- **Workflow role-file partial overrides** (R3.3): the spec already forbids partial overrides (winning tier owns the full file set). The operational spec must call this out *loudly* in the user-facing documentation, since users may try `~/.claudechic/workflows/onboarding/onboarding_helper/identity.md` (just one file) expecting it to override only that file. The system MUST treat that as a partial workflow definition and either (a) reject it with an error, or (b) document that the user must copy *all* files of the workflow they wish to override. Recommendation: option (b) with a clear documentation note.

### 8.3 R8 cross-platform worktree symlink (deferred / out of scope)

Existing `.claude/` symlink uses POSIX `symlink_to` (git.py:301). Same applies to the new `.claudechic/` symlink. Windows users currently lose worktree-state-propagation for `.claude/` and will lose it for `.claudechic/`. This is an **existing** issue, not introduced by this work. The spec MAY note this as a known limitation; redesigning worktree state propagation cross-platform is **out of scope** for this run.

---

## 9. What this lens does NOT spec

To stay in the Composability lane (P4), the following are explicitly delegated:

| Concern | Owning lens |
|---|---|
| Wording of the always-on agent-awareness statement; naming of `.claudechic/` subdirectories beyond L7; user-facing labels in `/settings` UI; "tier" vs "level" vs "namespace" word choice | **TerminologyGuardian** |
| Risk weighting of R6 mechanism choices; classification rigor of R5 boundary test; failure-mode coverage; A7 boundary-softening risk surface; lost-work auditing | **Skeptic** |
| Whether R6.6 mechanism choice "feels like" `.claude/rules/` from user perspective; whether the `/settings` UI (G) hides what it should hide; A12 settings-UI scope decisions | **UserAlignment** |
| Final operational spec assembly + appendix authoring per L14; cross-lens conflict resolution | **Coordinator** |

If conflicts surface across lenses (e.g., TerminologyGuardian wants `tier` but UserAlignment wants `level`), the Coordinator resolves; the Composability lens has no direct vote.

---

## 10. Crystal completeness check (final)

Apply the 10-point test to this design:

- **Total cells in (R1 × R2):** 3 × 4 = **12**.
- **Additional axes (R3–R8):** R3 is fully determined by R2 (per-category policy); R4–R8 are lower-dimension (each adds at most a few values).
- **Sample 10 points (chosen to exercise edges):**

| # | Point | Works? |
|---|---|---|
| 1 | (R1=package, R2=workflow, override absent) | YES — pure-package operation, INV-3 |
| 2 | (R1=user, R2=workflow, no project override) | YES — user overrides package per R3.3 |
| 3 | (R1=project, R2=workflow, no user override) | YES — project overrides package per R3.3 |
| 4 | (R1=project, R2=workflow, user override present) | YES — project beats user per R1.4 |
| 5 | (R1=user, R2=hint, lifecycle in flight) | YES — INV-8: lifecycle state survives override |
| 6 | (R1=project, R2=mcp_tool, name collides with package) | YES — R3.1: override by `tool.name` |
| 7 | (R1=user, R2=rule, project tier defines DIFFERENT rule with different id) | YES — R3.4: non-conflicting items accumulate |
| 8 | (R1=project, R2=rule, same id appears twice in same project file) | NO (correctly): R3.5 surfaces as load error |
| 9 | (R1=user, R2=workflow, partial role-file override) | NO (correctly): R3.3 forbids; spec documents this |
| 10 | (R6=on, agent never reads `.claudechic/` in session) | YES — always-on piece fires; first-read piece never fires; R6.1 |

All 10 points yield the expected behavior. **The crystal is complete** under R3.1–R3.6, R5.1–R5.5, and R6.1–R6.7 as specified.

The only "NO" cells (8 and 9) are deliberate — R3.5 and R3.3 are *exclusion* rules, not crystal holes. They surface as well-defined errors, not as silent failures.

---

*End of Composability specification for `independent_chic` run.*
