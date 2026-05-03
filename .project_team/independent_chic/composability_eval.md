# Composability Evaluation — `independent_chic` Run

**Author:** Composability (Leadership)
**Lens:** module boundaries, axes of variation, seams, compositional law
**Mode:** lens-only analysis. No advocacy beyond what this lens supports. Other Leadership lenses (Skeptic, TerminologyGuardian, UserAlignment) own their own dimensions; the Coordinator synthesizes.
**Inputs grounded in:**
- `vision.md` (binding) and `STATUS.md` (state of record, including A1–A3)
- `userprompt.md` (kickoff and Vision-phase Q&A)
- Direct codebase reads: `workflow_engine/loader.py`, `workflow_engine/agent_folders.py`, `workflow_engine/engine.py`, `config.py`, `hints/state.py`, `hints/triggers.py`, `hints/engine.py`, `app.py` (workflow activation + phase-context sites), `mcp.py` (MCP tool discovery), `features/worktree/git.py`, `workflows/onboarding/onboarding.yaml`, `workflows/onboarding/onboarding_helper/context_docs.md`, `global/hints.yaml`
- The prior run's `composability_eval.md` (treated as starting material; vision has shifted from sequencing-only to a 3-tier structural restructure plus A3 amendment, so much of the prior analysis is reframed rather than carried forward)

The prior run's analysis evaluated **Path 1 vs Path 2** (sequencing of #23 vs abast pulls). The user has now resolved that question (vision §"Open for the new team to decide" expresses preference for restructure-first, and STATUS A2 fully decides L16's cherry-pick set). The Composability question this run is no longer "which order" — it is **whether the proposed 3-tier restructure (plus A3 amendment) decomposes cleanly into independent axes, where the seams are dirty, and what the resulting work units should be**.

---

## 1. Frame

The vision proposes a structural restructure of claudechic with five interlocking pieces:

1. **3-tier content** (workflows, rules, hints, MCP tools) — package | user | project, project beats user beats package.
2. **2-tier config keys** (user + project; defaults in code; no `defaults/config.yaml`) — L8.
3. **Boundary** — claudechic writes only inside `.claudechic/` directories; never inside `.claude/` (L3, L5, L6).
4. **Agent awareness** — short always-on at session start + once-per-agent-session fuller context on first read inside `.claudechic/` (L15), with delivery mechanism mirroring `.claude/rules/` behavior subject to L3 (A3).
5. **Workflow artifact directories** — designated location where setup-phase output is visible to subsequent agents in the same workflow run.

These five pieces are not independent — they interact through shared modules (`config.py`, `app.py`, `workflow_engine/loader.py`, `hints/state.py`, `features/worktree/git.py`, `onboarding.py`) and through shared data flows (manifest discovery, prompt assembly, phase advance, worktree creation). The Composability lens asks: **do these pieces decompose into clean axes whose values can move independently, or are there bundled choices waiting to surface as "feature X requires feature Y" later?**

The codebase entering this restructure has the following composability-relevant facts (verified in source):

- **Loader is currently single-tier.** `workflow_engine/loader.py:117` `discover_manifests(global_dir, workflows_dir)` walks one global dir and one workflows dir. There is no fallback or layering. abast's `8e46bca` + `d55d8c0` (locked Pull per L16/A2) provide the 2-tier fallback pattern; extending to 3 tiers is in scope.
- **Loader returns concatenated lists, not tier-resolved content.** `LoadResult` (loader.py:95) holds flat lists: `rules`, `injections`, `checks`, `hints`, `phases`, `workflows`. There is no notion of per-tier provenance, no override-by-id logic, no merge policy. Cross-manifest validation includes "duplicate ID detection" (loader.py:344) — meaning the *current* design treats duplicate IDs across manifests as **errors**, not as **overrides**. That assumption flips under a 3-tier override model and is a load-bearing change.
- **Hint state lives at `.claude/hints_state.json`** (state.py:127) — an L3 violation that moves to `.claudechic/hints_state.json`.
- **Phase context lives at `.claude/phase_context.md`** (app.py:1848) — written on workflow activation and every phase advance, deleted on deactivation. Read by Claude Code as system-prompt context. An L3 violation; also semantically the *same problem* as A3 agent awareness (file-based context delivered to Claude as rule-equivalent).
- **`ContextDocsDrift` reads `.claude/rules/`** (hints/triggers.py:46) to detect upgrade drift. The matching install path is `workflows/onboarding/onboarding_helper/context_docs.md`, which writes into `.claude/rules/`. Both ends of this trigger are L3 violations. After the boundary work, the install site moves (or is removed under A3), and the trigger must be repurposed or retired.
- **Worktree symlinks `.claude/`** (features/worktree/git.py:293–301). No parallel `.claudechic/` symlink. After the move, `.claudechic/` state silently fails to propagate to new worktrees unless a parallel symlink is added.
- **MCP tools discovery is single-tier project-local** (mcp.py:732 `discover_mcp_tools(mcp_tools_dir)`). Walks one directory. No package-default tier exists today.
- **Config is 2-tier already** (config.py): `~/.claude/.claudechic.yaml` (user; the path violates L3 and moves to `~/.claudechic/config.yaml` per L6) and `<project>/.claudechic.yaml` (project; the file form violates L5 and becomes `<project>/.claudechic/config.yaml`). No merge logic — `ProjectConfig.load` reads project-local in isolation; user CONFIG is module-global. No notion of layered resolution.
- **Agent system prompt path used today**: `setting_sources=["user", "project", "local"]` in `app.py:969`. This is the SDK telling Claude to load the standard Claude Code settings tiers. The `.claude/rules/` auto-load is *internal to Claude Code* — it is not directly under claudechic's control. This is the central A3 mechanism question.

---

## 2. Identified axes (10)

This run identifies **ten primary axes**. Six are runtime axes (define how the system behaves at execution time). Four are process/structural axes (define how work is decomposed and how the existing code reaches the new shape). Each axis is independent in principle; the seams §3 names the places where they touch.

| # | Axis | Type | Values | Locked by |
|---|---|---|---|---|
| 1 | **Tier** (where any piece of content lives) | runtime | package \| user \| project | L7 (paths), §1 (priority order) |
| 2 | **Content category** (what kind of content) | runtime | workflow \| rule \| hint \| mcp_tool | §1 (the four categories) |
| 3 | **Resolution semantics** (how tiers combine for one category) | runtime | override-by-id \| merge-by-list \| tier-unique-additive | **OPEN** — vision says "project beats user beats package" but does not specify per-category semantics |
| 4 | **Config layering** (separate axis from content tiering) | runtime | user-only \| project-only \| layered-merge | L8 (2-tier, defaults in code), L9 (`analytics.id` user-only) |
| 5 | **Boundary direction** (read vs write across `.claude/` ↔ `.claudechic/`) | runtime | read-`.claude/` ✓ \| write-`.claude/` ✗ \| read-`.claudechic/` ✓ \| write-`.claudechic/` ✓ | L3, L5, L6 |
| 6 | **Agent-awareness delivery** (how Claude sees claudechic context) | runtime | system-prompt-preset \| append-system-prompt \| hook-based-injection \| `additionalDirectories` exposure \| symlink-equivalent | A3 (mirror `.claude/rules/`) constrained by L3 (no writes); L15 (two-piece timing); **mechanism OPEN** |
| 7 | **Artifact-dir lifetime/scope** | runtime | per-workflow-run \| per-chicsession \| per-launched-repo | §6 (must be visible to subsequent agents); **mechanism OPEN** |
| 8 | **Worktree state propagation** | runtime | symlink-from-main \| per-worktree-fresh \| repo-tracked | Existing pattern symlinks `<main_wt>/.claude`; vision File-move §"Worktree symlink (BF7)" requires parallel `.claudechic` symlink |
| 9 | **Cross-fork integration order** (path-order of work) | process | restructure-first \| pull-first \| parallel | **Preference**: restructure-first per vision §"Open for the new team to decide"; team may deviate with justification |
| 10 | **Spec/appendix decomposition** (documentation layering) | process | unified-doc \| spec-only \| spec+appendix-split | L14 (binding: spec strictly operational; rationale in separate appendix) |

A user-facing settings UI (the `/settings` button per #24) and the `docs/configuration.md` reference page are not separate axes — they are projections of axes 4 and 5 onto a UI surface and a documentation surface respectively. They compose by reading from the existing config layers.

---

## 3. Per-axis composability assessment

### Axis 1 — Tier (package | user | project)

**Status:** Cleanly orthogonal in the file system. L7 fixes the layout shape (`workflows/`, `global/{rules,hints}.yaml`, `mcp_tools/`) at every tier; L6 fixes user-tier path (`~/.claudechic/`); L5 fixes project-tier path (`<repo>/.claudechic/`); the package tier lives at `claudechic/defaults/...` (per L7 + the File-move inventory).

**What composes well:** The same directory shape at every tier is the textbook clean-axis design. A user adding a workflow at `~/.claudechic/workflows/foo/` requires no change anywhere in the package or in any project. The crystal point (`tier=user`, `category=workflow`, `id=foo`) is reachable independently of the values on other axes.

**What couples:** The tier axis is meaningless without a resolution semantics decision (axis 3). "Project beats user beats package" tells you *which* wins in a conflict but not *what counts as a conflict*. Without resolution semantics, this axis is half-defined.

### Axis 2 — Content category (workflow | rule | hint | mcp_tool)

**Status:** Currently four code paths with different shapes:

- Workflows: discovered as `workflows/<name>/<name>.yaml` directories (loader.py:144); engine assembles role prompts from `<workflow>/<role>/{identity,phase}.md` siblings (agent_folders.py).
- Rules + hints: discovered as `global/*.yaml` files (loader.py:134), parsed by registered ManifestSection parsers.
- MCP tools: discovered as `mcp_tools/*.py` Python plugins via `discover_mcp_tools` (mcp.py:732); not part of `ManifestLoader` at all.

**What composes well:** Each category is parsed by a registered `ManifestSection[T]` parser (loader.py:32) — the loader is generic. This is good algebraic structure: adding a new category means implementing the protocol and registering. The byte-law equivalent here is "everything is a list of typed records keyed by ID".

**What couples:** MCP tools are off the main loader path (Python module discovery, not YAML manifest parsing). The 3-tier walk has to be implemented twice — once for YAML-based content (loader-driven) and once for Python plugins (importlib-driven). This is essential coupling (Python modules vs. YAML data are genuinely different shapes), so it is acceptable; but the *tier-walk policy* should be factored out so that "tier walking" is its own axis-aware module that both YAML loading and Python discovery call into.

### Axis 3 — Resolution semantics (OPEN)

**This is the highest-leverage open question in the design.** "Project beats user beats package" is locked at the priority level, but semantics are not. The four content categories likely require *different* semantics:

| Category | Natural identity unit | Likely resolution |
|---|---|---|
| Workflows | `workflow_id` (string in YAML, currently constrained to match dir name in some sites — agent_folders.py:35) | Override by full workflow_id (winning tier replaces the entire workflow definition AND its role/phase files). Otherwise role-files merge across tiers, which would be hard to reason about. |
| Rules | `rule.id` | Override by id within `rules.yaml`; rules from non-conflicting ids accumulate from all tiers. |
| Hints | `hint.id` | Override by id; non-conflicting hints accumulate. (Lifecycle state in hints_state.json keyed by id — must continue to work with overridden hints.) |
| MCP tools | `tool.name` | Override by tool name; non-conflicting tools accumulate. |

**Composability concern:** the *current* loader treats duplicate IDs as **errors** (loader.py:347–357 "duplicate ID — first in {seen[iid]}"). Under the new model, duplicate IDs across tiers are the **expected mechanism** for override. This requires inverting the loader's duplicate-id logic and adding tier-provenance to every parsed item so resolution can happen as a post-pass.

**Smell flagged (Hole 3):** Without an explicit resolution-semantics decision, the composability of axes 1+2 is undefined. The team must spec, per category, exactly: (a) what the identity unit is, (b) override or merge semantics, (c) what happens to associated files (role/phase markdown, `mcp_tool` helper modules).

### Axis 4 — Config layering (separate, intentionally 2-tier)

**Status:** L8 explicitly chose a different decomposition than axis 1. Config keys are 2-tier (user + project), defaults live in code. This is *not* a contradiction — config and content have genuinely different shapes:

- Content has many independent items (each rule/hint/workflow is a discrete object). Override-by-id makes sense.
- Config has fixed keys with typed values. Merge-by-key with a default fallback in code is the standard pattern (cf. `ProjectConfig` dataclass at config.py:94).

**What composes well:** `ProjectConfig.load(project_dir)` already does a partial merge — missing keys default to dataclass defaults. Extending this to per-key user/project resolution is straightforward (project value wins if present; else user value if present; else dataclass default).

**What couples:** Axis 5 (config key tier-pinning) is a separate sub-decision: which keys *can* be set at user vs. project. L9 pins `analytics.id` to user-tier. Vision lists `default_permission_mode`, `analytics.enabled`, `worktree.path_template`, `themes` as user-tier; `guardrails`, `hints`, `disabled_workflows`, `disabled_ids` as project-tier. The team should make this list canonical (it appears partially in vision §2 and partially in current `ProjectConfig` — they need to be reconciled in the spec).

**Composability win:** because axis 4 is intentionally different from axis 1, the team **should not** try to share the tier-walk implementation between content and config. Two separate, smaller modules is cleaner than one generic mechanism with conditional behavior.

### Axis 5 — Boundary (read-vs-write across `.claude/` ↔ `.claudechic/`)

**Status:** L3 makes the boundary asymmetric and hard. The boundary is not "claudechic owns `.claudechic/` and Claude owns `.claude/`" — it is **"claudechic *writes* only into `.claudechic/`; claudechic *reads* from `.claude/` freely"**. The asymmetry is intentional: claudechic must continue to introspect Claude state (sessions JSONL, OAuth credentials, settings.json, plugin info) without writing back.

**What composes well:** The asymmetry is testable. A single CI check that grep-filters write sites for `.claude/` paths catches every regression. The boundary is *load-bearing for Axis 6* — every mechanism choice for agent awareness must respect it.

**What couples:** Several legitimate reads are *path-shape-coupled* to claudechic's old write sites:
- `ContextDocsDrift` (hints/triggers.py:46) reads `.claude/rules/` because that is where the matching install site (`onboarding/context_docs.md`) writes. Both ends are coupled. After the install site moves, the trigger must move with it; the seam is currently dirty (the read knows the write's location).
- `phase_context.md` is *written* by claudechic into `.claude/` so Claude *reads* it as system prompt context. After L3, the write moves to `.claudechic/` — but the read (by Claude Code, not by claudechic) continues to expect `.claude/`. **This breaks the read.** Fixing it requires a new mechanism (Axis 6); the same mechanism that solves A3 also solves phase_context.

**Composability insight:** Axes 5 and 6 are deeply coupled. Phase context delivery and agent-awareness delivery are two flavors of the same problem — *file-based context delivered to Claude from a `.claudechic/` location*. A single mechanism choice serves both. Treating them as separate problems will produce two implementations where one suffices.

### Axis 6 — Agent-awareness delivery (OPEN, A3-constrained)

**This is the most architecturally constrained open question.** A3 requires the mechanism to mirror `.claude/rules/` from the agent's perspective: file-based, auto-loaded, rule-equivalent. L3 forbids writing into `.claude/`. L15 requires two-piece timing (always-on short statement + once-per-agent fuller context on first read inside a `.claudechic/` folder).

**What `.claude/rules/` actually does (verified):** Claude Code itself auto-loads `.md` files from `.claude/rules/` into the system prompt when it starts. claudechic does *not* implement this auto-load — Claude Code does. From outside Claude Code, the SDK gives claudechic four extension surfaces:

1. `setting_sources=["user", "project", "local"]` (currently used at app.py:969) — points at Claude's own settings tiers; does not add custom directories.
2. `append_system_prompt` / system-prompt presets — text injection. Not file-based from the agent's perspective; doesn't mirror `.claude/rules/` shape.
3. Hooks (PreToolUse, PostToolUse, UserPromptSubmit, SessionStart) — can dynamically inject context based on triggers. Could implement L15's "first read inside `.claudechic/`" by intercepting Read tool calls.
4. `additionalDirectories` (Claude Code SDK option, if exposed) — exposes directories to the agent's read scope but does not auto-load them as rules.

**The composability tension:** No single SDK extension surface is both file-based-auto-loaded *and* honors L3. A literal mirror of `.claude/rules/` would require either symlinking `.claudechic/rules/` *into* `.claude/rules/` (violates L3, since the symlink itself is a file inside `.claude/`) or convincing Claude Code to load from a custom dir (no public mechanism for this). The team's mechanism choice will be a creative combination — most likely:

- **Always-on (L15 piece 1):** `append_system_prompt` with a short paragraph at every agent spawn. Simple, file-independent, works today.
- **Once-per-agent on first `.claudechic/` read (L15 piece 2):** PreToolUse hook on the Read tool that checks "is this path under `.claudechic/`?" and, if yes and not yet fired for this agent session, returns an injection containing the full context document. Tracking "fired this session" is per-agent in-memory state.
- **Phase-context delivery (Axis 5 byproduct):** SessionStart hook (or first-turn injection) that reads `<repo>/.claudechic/phase_context.md` and injects it. Same mechanism family.

**Composability assessment:** This mechanism choice is *not literally* a `.claude/rules/` mirror — but it satisfies A3's *intent* (file-based source of truth, auto-injected without explicit user action, treated by the agent as authoritative context). The team should be explicit in the spec that the mechanism is hook-mediated injection sourcing from `.claudechic/` files, *not* a literal directory mirror.

**Smell flagged (Hole 1):** A3 as written ("must mirror `.claude/rules/` behavior") is not literally achievable subject to L3. The team must operationalize A3 as **behavioral mirror** (file-based, auto-injected, rule-equivalent in the prompt) rather than **mechanism mirror** (Claude Code's own auto-load applied to a custom directory). The Skeptic and UserAlignment lenses should validate that this operationalization preserves user intent.

### Axis 7 — Artifact-dir lifetime/scope (OPEN)

**Status:** No formal artifact-dir mechanism exists today. Workflow state is persisted via the `persist_fn` callback (engine.py) into the chicsession JSON; per-phase prompt content is read from the workflow's role directory at agent-spawn time. The current `project-team` workflow uses `.project_team/<project_name>/` as a de-facto artifact dir (this run lives there) but that path is not engine-aware — the workflow phase docs hard-code the path in markdown.

**Choices for the team:**
- **Per-workflow-run** (`<repo>/.claudechic/runs/<run_id>/`): clean isolation, garbage-collectable, but every workflow author must know the path convention. Spawn-time injection of the path into agent identity is straightforward.
- **Per-chicsession** (`<repo>/.claudechic/chicsessions/<session_name>/`): aligns with existing chicsession storage, persists across workflow stop/start within the same session.
- **Per-launched-repo** (`<repo>/.claudechic/state/<workflow_id>/`): simplest, but cross-run pollution risk.

**Composability concern:** Whatever the team picks, the *path* must be discoverable by spawned agents. Hard-coding paths in role markdown (the current pattern) does not compose: a workflow can't be moved between tiers (axis 1) without rewriting its phase docs. The clean fix is a small env-var or system-prompt token (e.g., `${CLAUDECHIC_ARTIFACT_DIR}`) that the engine sets at spawn time and that role docs reference. This is a small but real change to `agent_folders.py` and to the role-markdown convention.

### Axis 8 — Worktree state propagation

**Status:** The `<main_wt>/.claude` symlink (features/worktree/git.py:293–301) is the only state-propagation mechanism today. After the boundary work, claudechic state no longer rides this symlink (it lives in `.claudechic/`). User-tier state at `~/.claudechic/` propagates trivially (home dir is not worktree-scoped). Project-tier state at `<main_wt>/.claudechic/` requires a parallel symlink.

**Composability win:** The pattern is already there — same symlink site, same condition (`is_dir()` check), same target shape. Adding the parallel symlink is mechanically identical and lands in a file abast did not touch (zero merge surface). This axis is well-isolated and clean.

**Smell flagged (Hole 7):** If the symlink is only added to `worktree_create` but not also handled in `worktree_finish` / `worktree_remove`, dangling-symlink behavior across worktree lifecycle should be checked. The current code does not handle removal explicitly (`git worktree remove` cleans the worktree dir; the symlink is inside that dir so it dies with it). New code should preserve this property.

### Axis 9 — Cross-fork integration order (process axis)

**Preference: restructure-first** (vision §"Open for the new team to decide"). The Composability lens supports this preference for the same reason the prior run reached it (boundary-as-filter for cherry-pick decisions). With the user's L16 cherry-pick set fully decided per A2, the only Composability concern in this axis is **re-pathing of the d55d8c0 loader-fallback commit**. abast's commit was authored against the 2-tier `claudechic/defaults/` pattern; sprustonlab's restructure target is 3-tier with `claudechic/defaults/` as the package tier. The fallback-discovery code should land *after* the 3-tier scaffolding is in place, so the imported logic plugs into a 3-tier walk rather than a 2-tier walk.

**Recommended decomposition (work units; details in §6):**
1. Restructure work units (axes 1, 2, 5, 8) — independent of cherry-picks.
2. d55d8c0 cherry-pick — depends on (1) being far enough that the 3-tier scaffold exists.
3. The remaining L16 cherry-picks (auto-perm, model-ID, /spawn_agent doc fix) — orthogonal to (1) and (2); can land independently.

### Axis 10 — Spec/appendix decomposition (process axis)

**Status:** L14 binds. The Composability lens applies to documents as much as to code: spec readers (Implementer, Tester) are the "downstream tier" and the spec is the "byte interface" they consume. Mixing rationale into the spec is the document equivalent of a dirty seam — implementation knowledge leaks into operational instruction.

**Recommendation:** the team's grading rubric (vision §Failure: "this is a known anti-pattern from the prior run; the new team's grading rubric should catch it") should test the spec by asking: **can a new agent execute the spec without ever opening the appendix?** If yes, the seam is clean. If no, find what was rationale-leaking and move it.

---

## 4. Cross-axis seams (where independence is at risk)

The axes above are independent in principle. They touch in five places, and each touch is a seam that needs explicit policy:

### Seam A — Loader ↔ Tier-walk (axis 1 ↔ axis 2)

`ManifestLoader` today knows about two shapes (`global/*.yaml` and `workflows/*/*.yaml`). After the restructure, it must walk three tiers, each with the same shape. The clean refactor: factor a `TierWalker` that yields `(tier, manifest_path)` pairs, then the loader runs its existing per-manifest parse over the union. Tier provenance must be preserved on every parsed item so that the resolution post-pass (axis 3) can apply.

**Risk if seam is dirty:** if tier provenance is *not* tracked per item, the override semantics cannot be implemented; the loader is forced into either "first wins" or "last wins" without recourse.

### Seam B — Loader ↔ Resolution semantics (axis 2 ↔ axis 3)

Different content categories want different semantics (workflows: override-by-workflow-id; rules: override-by-rule-id with merge of non-conflicting; hints: same as rules; mcp_tools: override-by-tool-name). A clean factoring: each registered `ManifestSection[T]` parser additionally implements a `resolve(items_per_tier: dict[Tier, list[T]]) -> list[T]` method. The loader then calls `parser.resolve(...)` after parsing, and each parser owns its resolution policy. This keeps category-specific logic out of the tier walker.

**Risk if seam is dirty:** if resolution lives in the tier walker (a single `if category == "workflow": ... elif category == "rule": ...` block), every new content category requires touching the tier walker — non-algebraic composition.

### Seam C — phase_context.md ↔ agent-awareness (axis 5 ↔ axis 6)

These are the same seam, observed twice. A clean factoring delivers both with one mechanism. A dirty factoring delivers them with two mechanisms that drift over time.

**Risk if seam is dirty:** two parallel hook implementations, each with its own "have I fired yet?" tracking, each reading from `.claudechic/` with its own conventions. Future contributors won't know which to extend.

### Seam D — ContextDocsDrift trigger ↔ install site (axis 5)

Currently the trigger reads `.claude/rules/` because the install site writes there. After A3 + L3, the install site changes (or the install phase is removed). The trigger has three possible fates:
1. Removed entirely (no more docs to drift; agent awareness is hook-injected at runtime so there is no on-disk copy to drift from).
2. Repurposed to detect drift between the package's bundled docs and a `<repo>/.claudechic/installed_context_docs/` snapshot, if the team chooses to keep an on-disk install for transparency.
3. Re-pointed at `<repo>/.claudechic/rules/` if the team chooses to keep a literal mirror (unlikely under A3's hook-mediated mechanism).

**Vision marks this as "fate is new-team's call per L15"** (File-move inventory §Hints-pipeline surface). The Composability lens recommends fate (1): under the A3 mechanism, there is no installed copy on disk, so there is nothing to drift. Removing the trigger removes a coupling.

### Seam E — Workflow YAML files ↔ engine code path (axis 1 ↔ axis 2 ↔ FDR Anomaly 3)

The post-restructure layout has `claudechic/workflows/` containing **engine Python** (the moved `workflow_engine/` files) and `claudechic/defaults/workflows/` containing **bundled YAML content**. The same path token (`workflows/`) now means *different content types* depending on the parent (`claudechic/` vs `claudechic/defaults/`). This is the FDR Anomaly 3 architectural divergence the prior run flagged, now resolved by giving the two content types different parents.

**Risk if seam is unclear:** new contributors may put YAML into `claudechic/workflows/` or Python into `claudechic/defaults/workflows/`. The spec should make this distinction explicit and the directory-level naming should signal it. (One option: keep engine code at `claudechic/workflow_engine/` and put bundled YAML at `claudechic/defaults/workflows/`. The vision File-move inventory chose to move engine to `claudechic/workflows/`; that is locked, but the spec should warn loudly about the meaning of the `workflows/` path token.)

---

## 5. Holes / smells

Numbered for cross-reference. (Hole numbering matches the inline references in §§3–4.)

| # | Hole / Smell | Severity | Source | Resolution |
|---|---|---|---|---|
| 1 | A3's "mirror `.claude/rules/`" is not literally achievable under L3 | High | Vision §A3 + L3 | Operationalize A3 as *behavioral* mirror (file-based, auto-injected, rule-equivalent prompt content) sourced from `.claudechic/`, delivered via SDK hook + `append_system_prompt`. The mechanism is hook-mediated, not symlink-mediated. Skeptic + UserAlignment should validate. |
| 2 | 3-tier content vs. 2-tier config = two separate tier-walk modules | Low (intentional) | L7 vs L8 | Do not try to share the tier-walk implementation. Two small modules is cleaner than one generic with conditional logic. Spec should make this explicit. |
| 3 | Resolution semantics (axis 3) per category not specified | High | Vision §1 (priority order only) | Spec must state, per category: identity unit, override-or-merge policy, fate of associated files (role/phase markdown, mcp helper modules). Loader's current "duplicate IDs are errors" logic must invert per category. |
| 4 | `claudechic/workflows/` post-move means *engine Python*, not *workflow content* | Medium | File-move inventory | Spec must call this out. Consider whether engine should stay at `workflow_engine/` (keeps "workflows" as a content-type token everywhere) — but inventory locks the move, so the spec should warn loudly. |
| 5 | phase_context.md write is the same problem as A3 agent-awareness | Medium → win if recognized | app.py:1848 + A3 | Treat as one problem; one mechanism serves both. Don't ship two parallel implementations. |
| 6 | ContextDocsDrift trigger no longer makes sense under A3 hook-mediated awareness | Medium | hints/triggers.py:25 + A3 | Recommend retiring the trigger. If kept, it must be re-pointed at a `.claudechic/` source — but under hook-mediated A3 there is no installed-copy disk artifact to drift from. |
| 7 | Worktree symlink lifecycle (creation handled; removal implicit) | Low | features/worktree/git.py:293–301 | Verify that `.claudechic/` symlink is inside the worktree dir (so `git worktree remove` cleans it). The current `.claude` symlink follows this; preserve it. |
| 8 | `disabled_workflows` config key compounds with axis 1 (tier) | Medium | config.py:104 + vision §1 | If a workflow is disabled by id, does it disable that workflow at *all tiers* or only at the tier where the user configured the disable? The natural answer is "at all tiers" (it is a feature-toggle, not a content reference) but the spec must say so. Without specification, the resolution-semantics post-pass behavior is ambiguous. |
| 9 | MCP tools 3-tier walk: package-default tier doesn't exist today | Medium | mcp.py:732 (single-dir walk) | Vision §1 names mcp_tools as a 3-tier content category. Today there is no `claudechic/defaults/mcp_tools/` — abast introduced this layout, sprustonlab does not yet have it. Restructure must create the package tier and refactor `discover_mcp_tools` to walk all three. |
| 10 | Workflow artifact-dir path discoverability (axis 7) | Medium | engine.py + agent_folders.py | If the artifact dir is hard-coded in role markdown, the workflow can't be moved between tiers without editing the markdown. Spec should adopt a conventional token (env var or system-prompt placeholder) that the engine sets at spawn. |

---

## 6. Recommended decomposition (work units)

The Composability lens recommends the spec organize implementation into the following independently-addressable work units. Each can be Implementer-tested in isolation; the dependency graph is shallow.

**Group A — Restructure (file moves, no behavior change)**
- A1. `git mv` the six engine Python files from `workflow_engine/` to `workflows/` (per File-move inventory).
- A2. `git mv` the seven bundled-workflow YAML directories from `workflows/` to `defaults/workflows/`.
- A3. `git mv` the two global manifest files from `global/` to `defaults/global/`.
- A4. `git mv` the `mcp_tools/` directory to `defaults/mcp_tools/`.
- A5. Update the 22 import sites from `claudechic.workflow_engine` to `claudechic.workflows`.
- A6. Update the 5 path-reference sites from `claudechic/workflows/` to `claudechic/defaults/workflows/`.
- A7. Delete the now-empty `workflow_engine/` and `global/` directories.

Independence: A1–A4 are file moves; A5–A6 are mechanical text rewrites; A7 is cleanup. None depend on Group B–E.

**Group B — Boundary relocation (state files move out of `.claude/`)**
- B1. Move user config from `~/.claude/.claudechic.yaml` to `~/.claudechic/config.yaml` (config.py:17). No migration logic per L17.
- B2. Move project config from `<repo>/.claudechic.yaml` (file) to `<repo>/.claudechic/config.yaml` (in directory) (config.py:110).
- B3. Move hint state from `<repo>/.claude/hints_state.json` to `<repo>/.claudechic/hints_state.json` (hints/state.py:127).
- B4. Add parallel `.claudechic/` symlink to `features/worktree/git.py:293–301`.
- B5. Doc-surface rewrite of the six files referencing the old config paths (per File-move inventory §"Doc-surface rewrite").

Independence: B1–B5 are independent of one another and of Group A. B4 depends on B1+B2 only in the sense that there must be a `.claudechic/` to symlink — but the symlink is `is_dir()`-guarded so it is forward-safe.

**Group C — Loader 3-tier walk + resolution semantics**
- C1. Cherry-pick d55d8c0 (loader fallback discovery) onto the post-A1–A7 code. This is the locked Pull per L16/A2; landing it after Group A puts it on the right paths.
- C2. Generalize the fallback walk from 2-tier to 3-tier (package, user, project).
- C3. Add tier provenance to every parsed item (`tier: Literal["package","user","project"]` field on each typed record).
- C4. Per-category resolution: implement `resolve()` on each `ManifestSection[T]` parser. Workflows override by `workflow_id`; rules/hints override by `id`; mcp_tools override by `tool.name`.
- C5. Invert the "duplicate ID error" check (loader.py:344) so cross-tier duplicates are *expected* (override) but within-tier duplicates remain errors.
- C6. Generalize `discover_mcp_tools` to walk three tiers (mcp.py:732).

Dependency: C1 depends on Group A. C2–C5 depend on C1. C6 is independent of C1–C5 (different code path) but depends on Group A.

**Group D — Agent awareness mechanism (A3 + L15 + Axis 5/6 unification)**
- D1. Spec the chosen mechanism (hook-based recommended; see §3 axis 6).
- D2. Implement always-on session-start injection (short paragraph; `append_system_prompt` or SessionStart hook).
- D3. Implement once-per-agent-on-first-`.claudechic/`-read injection (PreToolUse hook on Read tool, with per-agent-session "fired" tracking).
- D4. Move `phase_context.md` out of `.claude/` (app.py:1848) and into the same hook-mediated injection family as D3 — same SessionStart hook reads `<repo>/.claudechic/phase_context.md`. Update workflow activation/deactivation/advance sites (app.py:1623, 1635, 1648, 1822, 1834, 1925).
- D5. Decide fate of `ContextDocsDrift` trigger and `context_docs_outdated` hint. Recommended: retire both; agent awareness is hook-mediated and there is no installed-copy artifact to drift.
- D6. Decide fate of the `/onboarding` `context_docs` phase. Recommended: remove (or replace with a no-op that explains the agent will see context automatically).

Dependency: D depends on Groups A and B. D2–D6 are independent of each other. D5 and D6 are paired (the trigger and the install phase are two ends of the same coupling).

**Group E — Artifact dirs (Axis 7)**
- E1. Decide lifetime/scope (recommended: per-workflow-run under `<repo>/.claudechic/runs/<run_id>/`).
- E2. Add engine support to create the artifact dir at workflow activation, expose its path to agents (env var `CLAUDECHIC_ARTIFACT_DIR` set in the spawn env per app.py `_make_options`; or a placeholder in role markdown that `agent_folders.py` substitutes).
- E3. Update phase docs in `defaults/workflows/<workflow>/<role>/*.md` to use the placeholder rather than hard-coded paths where applicable.

Dependency: E depends on Group A (files moved). Otherwise independent.

**Group F — Other L16 cherry-picks (auto-perm, model-ID, /spawn_agent doc)**
- F1. Cherry-pick 9fed0f3 (docs).
- F2. Cherry-pick 8e46bca (resolved workflows_dir).
- F3. Cherry-pick f9c9418 (full model ID + loosened validation).
- F4. Cherry-pick 5700ef5 (default to `auto`).
- F5. Cherry-pick 7e30a53 (add `auto` to Shift+Tab).

Dependency: F1, F3–F5 are orthogonal to all other groups. F2 should land after Group A (it touches workflow path resolution). F4–F5 are paired per L16.

**Group G — UI & docs (Issue #23 deliverables)**
- G1. `/settings` TUI screen exposing user-facing config keys.
- G2. `docs/configuration.md` reference page (every config key, env var, CLI flag).
- G3. Workflow-button surface (per #24) listing workflows from all three tiers with provenance labels.

Dependency: G1 depends on Group B. G3 depends on Groups A and C. G2 is independent and can land any time.

**Suggested execution order (one feasible path; not the only one):**
A → B → C(C1-C5) → C6 → D → E → F2 → F1,F3,F4,F5 → G

The grouping is structural, not temporal. Many work units inside a group are independent and can be assigned to separate Implementer agents. The dependency arrows above are *minimal* dependencies; the team may choose stricter ordering for review-load reasons.

---

## 7. Vision errors / inconsistencies flagged (per A1)

Per A1, surface rather than work around. Three items:

1. **Vision §"What we want" §1 says "Whether they're a single directory or two siblings is a mechanism choice"** for rules+hints layout. **L7 already locks this**: `global/` containing `rules.yaml` and `hints.yaml`. The "mechanism choice" framing in §1 is inconsistent with L7's lock. Recommendation: treat as locked (per L7) and ignore the §1 framing. Not blocking.

2. **L7 framing — "the layout abast already adopted"** is slightly imprecise. Both forks have `global/{rules,hints}.yaml`; the difference is the *parent* path (sprustonlab: `claudechic/global/`, abast: `claudechic/defaults/global/`). Recommendation: spec should say "the *parent* layout abast adopted (`claudechic/defaults/`)" to avoid confusion. Not blocking.

3. **Path-token reuse (Hole 4 / Seam E)**: post-move, `claudechic/workflows/` holds Python engine code; `claudechic/defaults/workflows/` holds YAML content. The same path token now means different content types depending on parent. The vision File-move inventory states the moves explicitly but does not call out the semantic shift. Recommendation: spec should warn loudly about this; the team may also reconsider whether to keep engine code at `workflow_engine/` (keeping "workflows" semantically pure) — though the inventory lists the move as part of the locked file-move set, so the team should treat the move as binding unless surfacing this as an explicit revisit. Worth flagging but not blocking.

No errors that flip the analysis. The vision is internally consistent on the binding constraints.

---

## 8. Top concerns (composability lens, in priority order)

1. **(Hole 1) A3 mechanism design.** The "mirror `.claude/rules/`" requirement is behaviorally tractable but mechanism-constrained under L3. The spec must operationalize A3 as a hook-mediated, file-sourced injection — not a literal directory mirror. This is the single most architecturally constrained open question, and it composes with the phase_context.md relocation (Hole 5). Get it right and one mechanism solves both; get it wrong and the codebase grows two parallel injection systems.

2. **(Hole 3) Resolution semantics per content category.** "Project beats user beats package" is locked; what "beats" means per category is not. The loader's current "duplicate IDs are errors" logic must invert in a category-aware way. Without a per-category resolution policy spec, the entire 3-tier model is half-defined.

3. **(Hole 5) Recognize phase_context and agent-awareness as the same problem.** Both deliver file-based context from `.claudechic/` to a Claude session via a non-`.claude/` path. One mechanism for both keeps the codebase clean and matches the byte-law principle (everything is "file under `.claudechic/` → injection into prompt").

4. **(Hole 8) `disabled_workflows` semantics across tiers.** Project disables a workflow named `foo`. Does that disable `foo` at all tiers, or only `foo` at the project tier (allowing the user-tier or package-tier `foo` to "fall through")? Natural answer is the former; spec must say so explicitly because the resolution-semantics post-pass is otherwise ambiguous.

These are the four design decisions where being explicit in the spec preserves composability; being implicit creates "feature X requires feature Y" coupling later.

---

*End of Composability evaluation for `independent_chic` run.*
