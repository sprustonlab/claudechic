# Axis Spec — Loader Rewrite + Per-Category Override Resolution — Rationale Appendix

**Companion to:** `axis_loader_resolution.md`
**Audience:** Spec maintainers, reviewers, future Implementers tasked with extending the loader.
**Mode:** Rationale, alternatives considered, source-authority references, trade-offs. Per L14, this appendix is non-binding — the operational spec is executable without reading this file.

---

## 1. Decision rationale (10 charge points)

### Charge 1 — Tier-walking refactor

**Decision:** Introduce `TierRoots` (frozen dataclass with `package: Path`, `user: Path | None`, `project: Path | None`) and a free function `walk_tiers(tier_roots) -> Iterable[(tier, manifest_path)]`. Replace `discover_manifests(global_dir, workflows_dir)` with `discover_manifests_single_tier(root)` (per-tier scan) and `walk_tiers` (multiplexed scan).

**Why a dataclass and not a `dict[Tier, Path | None]`:**
- The set of tiers is closed (`package`/`user`/`project`); a typed dataclass documents that closure and prevents typos.
- `TierRoots.items()` returns tiers in canonical ascending-priority order, so consumers don't need to know `TIER_PRIORITY` to iterate correctly.
- Type-checkers (the project uses pyright) catch missing fields better with a dataclass than with a dict.

**Alternatives considered:**
- **Pass `dict[Tier, Path]` directly** — simpler but loses the documented closure. Would have permitted `dict[Tier, Path]` with `Optional` values via union types, but at the cost of every consumer needing to handle missing keys defensively.
- **Pass three separate `Path | None` arguments** — pollutes every call site. Currently five call sites construct `ManifestLoader`; a dataclass groups them.
- **Keep `discover_manifests` as the public function and add tier overloads** — would require either a magic flag or a divergent return type. The clean break is cheaper.

**Source authority:**
- `specification/composability.md` R1.1 (three tier roots are exact: package = `claudechic/defaults/`, user = `~/.claudechic/`, project = `<launched_repo>/.claudechic/`)
- `specification/composability.md` R1.2 (same directory layout at every tier)
- `specification/composability.md` Seam-A (tier walker yields `(tier, category, manifest_path, raw_yaml)` — refined here to `(tier, manifest_path)` because the parser already knows category from the YAML structure; raw_yaml is loaded inside `ManifestLoader` as today)
- Code: `claudechic/workflow_engine/loader.py:117` (current single-tier `discover_manifests`)

### Charge 2 — Tier provenance on parsed records

**Decision:** Add a `tier: Tier` field to each typed dataclass: `Rule`, `Injection`, `HintDecl`, `Phase`, `CheckDecl`, `WorkflowData`. For MCP tools (SDK objects, not claudechic dataclasses), introduce a `TieredMCPTool` wrapper.

**Why field-on-each-dataclass over a wrapper for content categories:**
- The downstream surfaces that need provenance (workflow picker UI, settings UI, diagnostics) consume these dataclasses today. A wrapper would force every consumer to unwrap before accessing existing fields — significant churn for marginal benefit.
- The `tier` field is intrinsic loader-time metadata; a wrapper suggests it's externally-attached, which it isn't.
- Frozen-dataclass `replace()` works cleanly when the field is part of the dataclass itself.

**Why a wrapper for MCP tools:**
- SDK tools are produced by the `@tool` decorator from `claude_agent_sdk`; we don't own their schema. Adding fields would require monkey-patching, which is fragile.
- The wrapper is small (3 fields) and only crosses one seam (the registration call from claudechic to the SDK MCP server).

**Alternatives considered:**
- **Single tier-tagged wrapper for all categories** — would unify the API but force universal unwrapping. Rejected.
- **Side-table dict (`tier_of: dict[id, Tier]`) maintained alongside `LoadResult`** — keeps dataclasses unchanged but requires the side-table to be passed alongside every list, doubling the seam surface.
- **`tier` as an optional field with `default = "package"`** — chosen for compatibility with construction sites that don't yet pass tier; however, parsers MUST set tier explicitly (the default exists for resilience, not as the typical path). Documented in spec §2.3.

**Source authority:**
- `specification/composability.md` R3.6 ("Every parsed record MUST carry tier provenance")
- Code: `claudechic/guardrails/rules.py:17` (Rule dataclass), `:35` (Injection); `claudechic/hints/types.py:196` (HintDecl); `claudechic/workflow_engine/phases.py:17` (Phase); `claudechic/checks/protocol.py` (CheckDecl)

### Charge 3 — Per-category `resolve()` API

**Decision:** Add `resolve(items_by_tier) -> tuple[list[T], list[LoadError]]` to the `ManifestSection` protocol. Provide a generic `_resolve_by_id` helper that all four content categories use directly. Workflows resolve in a dedicated step inside `ManifestLoader.load()` (not via the parser protocol) because workflows aren't parsed via `ManifestSection`.

**Why per-parser `resolve()` over centralized resolution:**
- Seam-B (composability_eval.md §4): if resolution lived in the tier walker, every new content category would require touching the walker — non-algebraic. Per-parser resolution keeps the walker generic.
- Future categories (R2.4) can ship with their own resolution policy without touching shared code.
- All four current categories happen to use override-by-id with identical semantics; the helper `_resolve_by_id` factors that out without requiring the protocol to know the policy.

**Why a tuple return (`items, errors`) vs. raising:**
- Within-tier duplicates produce `LoadError` rather than exceptions because the existing pattern for the loader is fail-open per item; raising would break a load that has 99% valid content for one duplicate id. Consistent with `loader.py:174-180` error-handling docstring.

**Why workflows are special-cased outside the protocol:**
- Workflows aren't a YAML section key — they're identified by directory layout (`workflows/<id>/<id>.yaml`). The existing loader tracks them in `LoadResult.workflows` (a dict, not a list), distinct from the per-section parse loop.
- The override semantic for workflows is "winning tier owns the full file set" (R3.3), which crosses category boundaries — overriding a workflow drops not just the workflow YAML's contents but also the corresponding role/phase markdown files. The pruning step (`_is_pruned` in spec §5.4 Step 5) implements this and lives in the loader, not in any single parser.

**Alternatives considered:**
- **Workflow as a fifth `ManifestSection`** — would require contorting the parse signature (`raw: list[dict]` doesn't match how workflows are discovered). Rejected.
- **Resolution method on `LoadResult`** — would couple `LoadResult` to mutation and fight the existing `frozen=True` pattern.
- **Lazy resolution at consumer sites** — e.g., `LoadResult.rules` becomes a property that resolves on access. Rejected because resolution errors (within-tier dups) need to be surfaced once at load time, not on every access.

**Source authority:**
- `specification/composability.md` R3.1–R3.5
- `specification/composability.md` §3 (compositional law: parse + resolve)
- `composability_eval.md` Seam B ("each registered ManifestSection[T] parser additionally implements a resolve(items_per_tier)")

### Charge 4 — Within-tier vs cross-tier duplicate semantics

**Decision:** Within-tier duplicates emit `LoadError` (kept first; lower-occurrence dropped); cross-tier duplicates are expected (override applied; no error). The split lives in `_resolve_by_id`. The current loader.py:344 cross-manifest duplicate-id check is REMOVED from `_validate`; phase-reference validation at loader.py:362-385 is preserved in a renamed `_validate_phase_refs`.

**Why split inside `_resolve_by_id`:**
- The two kinds of duplicate are semantically distinct (one is a config error; the other is the override mechanism). Keeping them in the same code path would require contextual parameters that complicate the generic helper.
- Per-tier scope is naturally available inside `_resolve_by_id` (we iterate `items_by_tier[tier]` for each tier); the within-tier check fits there cleanly.

**Why not preserve the existing cross-manifest check in `_validate`:**
- The existing check inverts the override semantic (treats every cross-tier override as an error). Preserving it would require a tier-aware filter, which is exactly what the resolve step does — duplicating the work would be a smell.

**Alternatives considered:**
- **Make duplicate-id-error configurable via flag** — would be a temporary backward-compat fix but adds a knob with no users. Rejected.
- **Move the check entirely into a separate `validate_within_tier` step** — would re-walk every tier-list, doubling iteration. The integrated path in `_resolve_by_id` is one walk.

**Source authority:**
- `specification/composability.md` R3.5 + INV-5
- `composability_eval.md` Hole 3 ("the loader's duplicate-id logic must invert per category")
- Code: `claudechic/workflow_engine/loader.py:338-360` (current `_validate` cross-manifest)

### Charge 5 — MCP-tool tier walk

**Decision:** Replace `discover_mcp_tools(mcp_tools_dir)` with `discover_mcp_tools(tier_roots)`. Tier-namespace the loaded module names (`claudechic._mcp_tools_loaded.<tier>.<filename>`) so tier collisions don't clobber `sys.modules`. Resolve by `tool.name` using `_resolve_by_id`. Within-tier collisions are logged at WARNING (not surfaced as `LoadError` because MCP tools don't flow through `LoadResult`).

**Why import both modules and pick afterwards (not short-circuit):**
- Helper modules (`_*.py`) at lower tiers might be imported by tool files at higher tiers (e.g., a project-tier `cluster.py` could import `_cluster_helper` that the package ships). Short-circuiting would break that.
- Import side-effects are bounded (we control the module name). The cost of importing two modules where one is later discarded is low compared to the complexity of inter-tier import-graph analysis.

**Why tier-namespace `sys.modules`:**
- The current code uses `sys.modules[f"mcp_tools.{stem}"] = module`. With three tiers each potentially defining `cluster.py`, all three would fight for `sys.modules["mcp_tools.cluster"]`; the last writer wins, which is non-deterministic.
- The `claudechic._mcp_tools_loaded.<tier>.<stem>` namespace isolates tiers and signals (via the underscore prefix) that this is a load-time synthetic namespace.

**Why log-warning vs `LoadError` for within-tier collisions:**
- MCP tools aren't part of `LoadResult` (mcp.py:732 returns `list` directly). Adding `LoadResult` plumbing for MCP tools would require either coupling `mcp.py` to the loader or duplicating the LoadResult mechanism. Logged warnings preserve the existing fail-open MCP-tool behavior (mcp.py:780-784 already logs and continues on errors).

**Alternatives considered:**
- **Walk only the highest tier that has any `mcp_tools/`** — would short-circuit but break partial overrides (project tier defining `dispatch.py` while package keeps `other.py`). Rejected.
- **Surface MCP collisions through `LoadResult.errors`** — would require either (a) `discover_mcp_tools` to return `(tools, errors)` (changing the call shape) or (b) a side-table for MCP errors. Deferred — not currently needed.

**Source authority:**
- `specification/composability.md` R2.3 (parse-then-resolve shape; identity = `tool.name`)
- Code: `claudechic/mcp.py:732` (current single-tier walker)

### Charge 6 — Workflow-folder tier walk for `agent_folders.py`

**Decision:** `assemble_phase_prompt` no longer scans for the workflow; the caller passes `workflow_dir: Path` directly, sourced from `LoadResult.workflows[wf_id].path`. `_find_workflow_dir` (current agent_folders.py:20) is DELETED.

**Why eliminate the scan:**
- The loader already knows the winning tier's path (it's stored on `WorkflowData.path` after resolution). Re-scanning at `assemble_phase_prompt` time would either (a) repeat work the loader already did or (b) risk diverging from the loader's resolution choice if filesystem state changed mid-session.
- Single source of truth: `LoadResult.workflows` is the canonical workflow registry.

**Why a path argument over a tier dict + workflow_id:**
- The function's job is "read identity.md + phase.md from a directory" — passing the directory directly matches the function's responsibility.
- Callers already have `LoadResult` (or the engine's stored workflow_id + the loader); the lookup is one indexing operation.

**Alternatives considered:**
- **Keep the scan but make it tier-aware** — would duplicate workflow-resolution logic. Rejected.
- **Pass `LoadResult` to `assemble_phase_prompt`** — couples the function to the loader's return type unnecessarily. Path is the minimal contract.

**Source authority:**
- `specification/composability.md` R3.3 (winning tier owns the full file set)
- `specification/composability.md` R1.3 (tier independence — partial overrides forbidden)
- Code: `claudechic/workflow_engine/agent_folders.py:20-45` (current `_find_workflow_dir`); `claudechic/app.py:917-923, 1840-1843` (callers)

### Charge 7 — `disabled_workflows` / `disabled_ids` interaction

**Decision:** Filtering is applied AFTER resolution, by the existing `_filter_load_result` in `app.py`. The loader does NOT consult `ProjectConfig`. Disable-by-id is tier-agnostic: a disabled id is removed regardless of which tier it came from; no fallback promotion to a lower tier.

**Why filter after resolve:**
- Seam-B (loader → engine consumers): the loader's job is "produce the effective content set"; the app's job is "filter by user preference". Mixing these creates a dirty seam — one module owns two policies.
- Filtering before resolve would require the filter to know per-tier provenance (which copy is being filtered?). Filtering after resolve operates on the single resolved record, simpler.

**Why no fallback promotion:**
- "Disabled" semantically means "the user does not want this feature". Promoting a lower-tier copy when the user disabled it would defeat the user's intent.
- The user can express "disable just the project-tier override and let user/package fall through" by removing the project-tier override file directly (per L17, no migration logic; the user manages files manually).
- This matches the existing `_filter_load_result` behavior at `app.py:162-164` (filter by namespace + id, no fallback).

**Alternatives considered:**
- **Tier-scoped disable** (e.g., `disabled_workflows: ["foo@project"]`) — adds expressive power but no current user need. Out of scope.
- **Filter inside the loader** — would couple loader to ProjectConfig. Rejected per Seam-B.

**Source authority:**
- `specification/composability.md` §8.2 (disabled_workflows tier-agnostic recommendation)
- `composability_eval.md` Hole 8
- Code: `claudechic/app.py:150-178` (current `_filter_load_result`); `claudechic/config.py:104` (`disabled_workflows`, `disabled_ids` definitions)

### Charge 8 — Loader API surface (post-rewrite)

**Decision:** `ManifestLoader(tier_roots: TierRoots)`. `LoadResult.workflows[wf_id]` is `WorkflowData` with `tier: Tier` provenance. `register_default_parsers` is unchanged in shape. `discover_manifests` is removed; `walk_tiers` and `discover_manifests_single_tier` are added.

**Why a constructor change vs. a setter:**
- The tier roots are intrinsic to the loader's identity — a loader with different tier roots is a different loader. Constructor injection matches that.
- `ProjectConfig` is per-launched-repo state; the loader's tier roots don't change during a session. No need for mutability.

**Why preserve `LoadResult` shape (lists per category + workflows dict):**
- Engine consumers (`hints/engine.py`, `guardrails/hooks.py`, `app.py`) iterate these lists today. Changing the shape would force a wide refactor for no benefit — the override resolution lives behind these lists; consumers see the resolved set.
- Tier provenance is added as a field on each record; consumers that don't care about it remain untouched.

**Alternatives considered:**
- **Make `ManifestLoader` a singleton constructed once globally** — current pattern allows test injection (`tests/test_workflow_guardrails.py:35`). Rejected.
- **Replace `LoadResult` with a richer object that exposes per-tier views** — adds API surface for diagnostic-only use cases. Deferred until a UI surface needs it.

**Source authority:**
- `specification/composability.md` Seam-B (LoadResult shape preserved; tier provenance added)
- Code: `claudechic/workflow_engine/loader.py:159-194` (current ManifestLoader); `claudechic/app.py:1494-1497` (current construction site)

### Charge 9 — Error semantics

**Decision:**
- Package tier missing/unreadable → fatal LoadError, empty content (fail closed; preserves loader.py:186-194).
- Non-package tier missing → silent skip.
- Non-package tier unreadable → LoadError logged, that tier contributes empty (fail open).
- Per-manifest YAML error → preserved (LoadError + skip).
- Per-item validation error → preserved (warning + skip).
- Within-tier duplicate id → new LoadError (kept first; later dropped).
- Cross-tier duplicate id → no error (override applied).

**Why fail-closed for package only:**
- Without the package tier, claudechic ships no defaults — the system has nothing to fall back to. This is a deployment error, not a user-config error. The current loader's "fail closed if global/ unreadable" matches this intent (it was de-facto the only tier).
- For user/project, absence is the normal case (most users have no `~/.claudechic/`). Failure to read should not block the package's bundled content.

**Why "missing" and "unreadable" are different:**
- Missing tier = user simply hasn't created it; no error message would be useful.
- Unreadable tier (permissions, broken symlink, etc.) = something is wrong; surface it so the user can fix it.

**Alternatives considered:**
- **Always fail closed on any tier error** — would surface false positives for users who deleted `~/.claudechic/` mid-session. Rejected.
- **Always fail open** — would mask real config errors. Rejected.

**Source authority:**
- `specification/composability.md` R1.3 ("MUST function correctly when any non-package tier is missing")
- Code: `claudechic/workflow_engine/loader.py:174-180` (existing error-handling docstring); `:186-194` (existing fail-closed pattern)

### Charge 10 — A8 reimplementation note

**Decision:** Drop the cherry-pick of `d55d8c0`'s loader logic per A8. The fallback-discovery pattern is reimplemented from scratch in §5.4 of the operational spec, generalized from 2-tier to 3-tier. The `app.py:1493-1497` fallback selector is replaced by `TierRoots` construction.

**What abast's pattern was (reference only — not consulted by Implementer):**

abast's `d55d8c0` modified `app.py` (visible at `git show d55d8c0 -- claudechic/app.py`):

```python
_defaults = Path(__file__).parent / "defaults"
_global_dir = self._cwd / "global"
if not _global_dir.is_dir():
    _global_dir = _defaults / "global"
_workflows_dir = self._cwd / "workflows"
if not _workflows_dir.is_dir():
    _workflows_dir = _defaults / "workflows"
```

Two-tier logic: project (cwd) overrides if present; else fallback to bundled defaults. No layering — the project tier either fully replaces the package or contributes nothing (per content type).

**Why the 3-tier reimplementation differs structurally:**
- abast's pattern is "either-or" per directory. The new model is "all tiers contribute; conflicts resolve by priority". This is a structural change, not a generalization of the existing logic.
- abast's pattern operates at the path level (which directory does the loader scan). The new model operates at the record level (which records survive resolution). The path-level pattern can't express "user adds new rules without losing package rules"; the record-level pattern can.
- The cherry-pick was always going to need substantial rewriting (the YAML content abast bundled isn't being pulled per L16; only the loader code was nominally targeted). With the loader code being structurally different anyway, A8 retired the cherry-pick.

**What carries forward in spirit (not in code):**
- The principle "package tier ships defaults; user/project layer on top" — preserved (and made richer).
- The principle "claudechic works out of the box without user/project setup" — preserved as INV-3.
- The path layout `claudechic/defaults/{global,workflows,mcp_tools}` — preserved (already the L7 layout).

**Source authority:**
- STATUS.md A8 (drop the selective cherry-pick; reimplement from scratch)
- STATUS.md A2 cherry-pick table (`d55d8c0` → SKIP per A8)
- abast commit `d55d8c0` (reference only; `git show d55d8c0` to inspect — Implementer SHOULD NOT consult)

---

## 2. Trade-offs surfaced

### Trade-off A: parser-protocol coupling vs. clean seams

The protocol now mandates `resolve()` on every parser. This is a small extra burden for parser authors but locks in algebraic composition (Seam-B). The alternative — a single centralized resolver in the loader — would have been simpler to write but would couple the loader to category semantics (every new category requires loader edits). Composability favored the protocol burden.

### Trade-off B: tier provenance as field vs. wrapper

Adding `tier` to every record dataclass touches more files than a wrapper would. We accept the wider surface for a cleaner downstream API (no unwrapping at consumer sites). The MCP-tool case is the exception (wrapper used) because the SDK type isn't ours to modify.

### Trade-off C: workflow resolution outside the parser protocol

Workflows resolve in dedicated loader code (Step 4 + Step 5 of `load()`), not via a `ManifestSection` parser. This breaks symmetry with rules/hints/etc. but reflects the genuine asymmetry of workflows (directory-identified rather than YAML-section-identified, with cross-category file-set ownership per R3.3). Forcing workflows into the `ManifestSection` shape would require contortions for marginal API uniformity.

### Trade-off D: `_filter_load_result` stays in `app.py`

We could have moved the filter into a shared module (`workflows/filter.py`) since other entry points might want it. Today only `app.py` constructs `ManifestLoader` for the running app, so the filter stays where it is. If a CLI / non-TUI entry point appears, the filter MAY be promoted then.

### Trade-off E: MCP-tool errors not in `LoadResult`

MCP-tool collisions log warnings rather than appearing in `LoadResult.errors`. This preserves the existing fail-open MCP behavior but means the settings UI / diagnostic surfaces won't show MCP-tool collisions in the same place they show YAML loading errors. If the unified-diagnostic surface becomes important, a future change MAY route MCP errors through `LoadResult` (would require restructuring `mcp.py`'s call shape).

---

## 3. Vision / lens-input inconsistencies surfaced (per A1)

### 3.1 None blocking

The lens-input (`specification/composability.md`) and STATUS amendments are internally consistent for this axis's scope. R3.1–R3.6 don't contradict any L#/A# constraint.

### 3.2 Minor clarifications worth recording

- **Phase-resolution policy is implicit in lens-input.** R3.1 lists `workflow`, `rule`, `hint`, `mcp_tool` as the four content categories. Phases (and Injections, Checks) are not explicitly enumerated as categories with identity units. This spec treats them as workflow-internal types that ride along with workflow resolution and additionally apply override-by-id within their own list (consistent with R3.4). If the lens-input intended phases/injections/checks to be opaque-to-resolution (only workflow-as-a-whole resolves), Implementer would need to drop §4.5–§4.6 — but this would create a hole: an injection at the user tier wouldn't override a same-id injection at the package tier, leading to duplicate execution. The override-by-id treatment chosen here matches user intent ("user can customize without modifying the package") and is consistent with R3.4's accumulation rule.

- **`disabled_workflows` interaction with the within-tier duplicate-error case** is not addressed in the lens-input. Spec §9 + §4 together imply: if a disabled workflow has within-tier duplicates, the duplicate-id error fires (it's a load-time error, not a runtime presentation concern); the disable filter then removes the workflow from `LoadResult.workflows`. The error is preserved on `LoadResult.errors`. This matches the existing `_filter_load_result` shape (`errors=result.errors` is passed through unchanged at `app.py:172`).

- **Tutorial markdown files reference the old API.** Three files at `claudechic/defaults/workflows/tutorial_extending/learner/{edit-yaml-config.md,add-rule.md,add-advance-check.md}` contain `loader = ManifestLoader(Path('global'), Path('workflows'))` examples (per `Grep` results during spec authoring). These MUST be rewritten to the `TierRoots` API. Operational spec §5.2 and §10.2 mark this as required; this appendix records that the rewrites are documentation-only (no behavior change, but they're tested by the tutorial-extending workflow if anyone runs it).

### 3.3 Cross-lens consistency check after Finding 2 integration

Finding 2 (partial-override loader enforcement) introduces a new error surface (§6.5.4 LoadError with `source="validation"`, `section="workflow"`). This surface is consumed by the existing app.py:1524-1529 toast pattern (which iterates `LoadResult.errors` and surfaces each to the TUI as a warning). No new TUI plumbing is needed for R3-UX.8; the existing pattern carries the message.

The verbatim wording in the LoadError (R3-UX.7) uses "level" rather than "tier" in the user-visible message text (per the user-facing wording rule). The internal `Tier` literal values happen to be `"package"` / `"user"` / `"project"`, which double as user-facing labels in this specific case — the surrounding helper text is what differs ("level" vs "tier" in instructional sentences). Consistent with R3-UX wording.

### 3.4 vision.md File-move inventory observation

The vision File-move inventory (vision.md §"Files with `claudechic/workflows/` path references — update to `claudechic/defaults/workflows/`") names 5 files including `claudechic/workflows/loader.py` (post-move) as needing the path-reference update. The actual update inside loader.py is structural (the `discover_manifests` body changes shape) rather than a string substitution; the inventory's framing of "mechanical text rewrite" understates the scope of the loader change. This is consistent with the inventory's separate note that "the loader will need a 3-tier fallback-discovery walk (per L7)" — a structural change, called out separately. No inconsistency, just a note that Group A and Group C overlap at this file: Group A moves the file; Group C rewrites its body.

---

## 4. Source-authority cross-reference

| Spec section | Authority |
|---|---|
| §1 module layout | vision.md File-move inventory; `specification/composability.md` §7 Group A |
| §2.1 `Tier`, `TIER_PRIORITY` | vision.md §1 (priority order); `specification/composability.md` R1.4 |
| §2.2 `TierRoots` | `specification/composability.md` R1.1 (three roots), R1.3 (independence) |
| §2.3 tier-tagged dataclasses | `specification/composability.md` R3.6 |
| §2.4 `TieredMCPTool` | `specification/composability.md` R2.3 + R3.6 |
| §3 `ManifestSection` revised | `specification/composability.md` Seam-A; `composability_eval.md` Seam B |
| §4.1 workflow resolution | `specification/composability.md` R3.3; INV-1, INV-2 |
| §4.2–§4.4 rule/injection/hint resolve | `specification/composability.md` R3.1, R3.2, R3.4 |
| §4.5 check resolve | inferred from R3 generality + existing CheckDecl id format |
| §4.6 phase resolve + workflow-scoped pruning | `specification/composability.md` R3.3 (full file set ownership); `composability_eval.md` Hole 3 |
| §5.4 load() pipeline | composite of `composability_eval.md` §4 Seam A + B; `specification/composability.md` §3 compositional law |
| §6 within-tier vs cross-tier duplicates | `specification/composability.md` R3.5; INV-4, INV-5 |
| §7 MCP-tool tier walk | `specification/composability.md` R2.3 |
| §8 agent_folders changes | `specification/composability.md` R3.3 |
| §9 disabled_workflows tier-agnostic | `specification/composability.md` §8.2 |
| §10 public API | composite |
| §11 error semantics | `specification/composability.md` R1.3; loader.py:174-194 (preserved patterns) |
| §12 A8 reimplementation | STATUS.md A8 |

---

## 4.5 Cross-lens integration (UserAlignment)

After the initial draft of this axis spec landed, UserAlignment delivered a cross-lens UX-faithfulness pass (`specification/user_alignment.md` §"Cross-lens: UX validation", clauses R3-UX.1 through R3-UX.11). Two findings overlap with this axis's scope:

### 4.5.1 Finding 1 — Tier-agnostic disable + per-id tier provenance for discovery (AGREE-WITH-MODIFICATION)

**Composability lens-input position:** disable-by-id is tier-agnostic; filter applies post-resolution.

**UserAlignment additions:**
- R3-UX.3: discovery surface MUST show per-id tier provenance (`<id> (defined at: package | user)`).
- R3-UX.4: unknown ids in disable lists warn-don't-error.
- R3-UX.5: symmetric for `disabled_ids` (rules/hints/etc.).
- User-facing labels say **"level"**, not "tier" (spec/code retains "tier").

**Disposition: integrated as MUSTs.**
- §2.3 — `WorkflowData.defined_at: frozenset[Tier]`.
- §2.4 — `TieredMCPTool.defined_at: frozenset[Tier]`.
- §5.3 — `LoadResult.workflow_provenance` and `LoadResult.item_provenance` maps.
- §9.6 — unknown-id warning behavior in `_filter_load_result` (warn at WARNING level; do not surface on `LoadResult.errors`).
- §9.7 — UI consumes provenance maps; verbatim user-facing wording prescribed; "tier" forbidden in user-facing labels.

No technical conflict with the original Composability lens-input. UserAlignment refines what the loader must expose to UI surfaces; the underlying override semantics are unchanged.

### 4.5.2 Finding 2 — Partial-override loader enforcement (DISAGREE → resolved in UserAlignment's favor)

**Composability lens-input position (R3.3 + §8.2):** partial workflow overrides are forbidden per R3.3, with §8.2 recommending option (b) — *"document that the user must copy all files of the workflow they wish to override."* Doc-only enforcement.

**UserAlignment position (R3-UX.7 through R3-UX.11):** doc-only is a foot-gun. Loader MUST detect partial overrides and emit a loud error; error MUST surface in the TUI; loader SHOULD fall through to the next tier; docs explain rationale; UI offers a one-click override affordance.

**Disposition: integrated in UserAlignment's favor.** No pushback — UserAlignment's UX argument is correct, and loader-level enforcement is technically achievable (see §1.6.5 of the operational spec for the detection algorithm).

**Why not push back:**
1. The Composability lens-input itself flagged option (a) (loader-level rejection) as an alternative — UserAlignment's stricter choice is within the option space the lens already framed.
2. The detection algorithm is bounded in complexity. The rule "files in lower tier minus files in higher tier must be empty for an override to be valid" is a well-defined set operation against `Path.rglob("*")` results. Implementation cost is moderate.
3. The UX failure mode (silent partial override → user spends an hour debugging why their file edit didn't take effect) is exactly the foot-gun pattern `vision.md` §"Failure looks like" warns against. Loader-level enforcement closes the foot-gun.
4. R3-UX.9's fall-through pattern (error + use lower tier) is strictly more usable than either silent-fall-through (current Composability proposal) or hard-fail (would block app startup). The combination satisfies the "system stays usable" axis (INV-3) AND the "user gets a signal" UX requirement.
5. No vision constraint conflicts. L17/A9 ("no migration logic, no startup warnings") refers to migration of existing user state; the partial-override warning is an active configuration error, distinct category.

**Operational spec changes for Finding 2:**
- §3.5 of the load() pipeline (`_reject_partial_overrides`) — new step inserted between per-tier parse (Step 2) and workflow resolution (Step 4).
- §6.5 — full detection algorithm, error format, fall-through behavior.
- §6.5.6 — three new INV-PO-* invariants in the test surface.
- §13 test surface — three corresponding test cases.

**Trade-off accepted:**
The partial-override detection performs a `Path.rglob("*")` on every tier's workflow directory at load time. This adds I/O proportional to the total number of files under all tier-specific `workflows/` subtrees. For a typical install with O(100) files total this is negligible. For very large workflow sets it could become a small load-time cost; a future optimization MAY cache the per-tier file set across loads if measurement shows it matters. This is acceptable; the UX win is large.

**Source authority for the integration:**
- `specification/user_alignment.md` R3-UX.1–R3-UX.11 (verbatim text in operational spec where prescribed)
- `specification/composability.md` §8.2 (the original framing that offered options (a) and (b))
- Coordinator (`claudechic`) message, this run — explicit "integrate or push back" choice; integrated.

---

## 5. Future-maintainer notes

### When you add a fifth content category

1. Define a new dataclass with an `id` field and a `tier: Tier` field.
2. Implement a `ManifestSection`-conforming parser with `parse(..., tier=tier)` and `resolve(items_by_tier)` (use `_resolve_by_id` if override-by-id semantics suffice).
3. Register it via `register_default_parsers` (or a separate registration site).
4. Add the new collection field to `LoadResult`.
5. Add the new section to `_filter_load_result` (so disable-by-namespace and disable-by-id apply).

R2.4 in `specification/composability.md` mandates that step 1–3 are sufficient (no walker edits, no other-parser edits).

### When you add a fourth tier

1. Extend `Tier = Literal["package", "user", "project", <new>]`.
2. Add the field to `TierRoots` (typed `Path | None`).
3. Insert into `TIER_PRIORITY` at the correct priority position.
4. Update `TierRoots.items()` to include the new tier conditionally.

That should be it. The walker, parsers, resolvers, and consumers all derive tier order from `TIER_PRIORITY` and field presence.

### When you change resolution semantics

If a category needs a non-by-id resolution policy (e.g., "merge fields across tiers" — currently forbidden by R3.2 but might come up), implement the parser's `resolve()` directly without `_resolve_by_id`. The protocol allows arbitrary logic; the helper is just convenience.

### When you debug an override that "didn't apply"

Inspect `LoadResult.<category>` items and check `tier` field. The `_resolve_by_id` helper guarantees: if record id X is in the list, its tier is the highest tier that defined X. If you expected project-tier and got package-tier, the project-tier file is missing or its parsing failed (check `LoadResult.errors` for that path).

---

*End of rationale appendix.*
