# SPEC — independent_chic

**Audience:** Implementer + Tester. This is the operational entry point for the implementation phase.
**Mode:** RFC-2119 MUST/SHOULD/MAY/MUST NOT throughout. Decision history, alternatives, and rejected paths live in `SPEC_APPENDIX.md`.
**Scope:** GitHub issues sprustonlab/claudechic#23 + sprustonlab/claudechic#24, plus four cherry-picks from `abast/main` (table in §6). Excludes sprustonlab/claudechic#25 (`/fast` mode, deferred).

This SPEC integrates the loader, artifact-dirs, and boundary-test axis-specs and the UI design. Where this file references an axis-spec by §number, that referenced section is operational and binding.

---

## 0. Document conventions

### 0.1 Inputs

Two files exist as supporting reference:

| File | Purpose |
|---|---|
| `terminology_glossary.md` | Canonical term forms (chicsession, workflow run, primary state, etc.) — consult when in doubt about a term. |
| `SPEC_APPENDIX.md` | Decision history, rationale, rejected alternatives. Not required reading for implementation. |


### 0.2 Vocabulary (binding)

- Tier names: **package**, **user**, **project** — exactly these three. 
- "tier" is used in spec/code/internal docs; **"level"** is used in user-facing UI labels and helper text.
- "rules" is qualified on first mention per section: **Claude rules** (Claude's `.claude/rules/`) / **guardrail rules** (claudechic's `global/rules.yaml`).
- "merge" is qualified: **tier merge** / **git merge** / **dict merge**. Bare "merge" is forbidden.
- The mechanism in §4 is **claudechic-awareness install**.
- A **tier-targeted disable** is an entry in `disabled_workflows` or `disabled_ids` of the form `<tier>:<id>` where `<tier>` ∈ `{package, user, project}`. It disables only the named tier's record of `<id>`; lower-priority tiers' records of the same id (if any) take effect via override resolution. A **bare ID** entry (no tier prefix) disables across all tiers. Both forms are first-class; bare IDs are backward-compatible with prior config files.

### 0.3 Work group execution order

The work groups MUST land in this order. Items inside a group may parallelize; group boundaries are sequential gates.

```
Group A  (restructure)
   │
   ├──> Group B  (boundary relocation; depends on A's file paths)
   │       │
   │       └──> Group E  (artifact dirs; depends on B for .claudechic/ dir convention)
   │
   ├──> Group D  (awareness install + inline phase-prompt delivery; depends on A)
   │
   ├──> Group C  (3-tier loader; depends on A for moved file layout)
   │       │
   │       └──> Group G  (build settings UI; depends on C for tier-tagged registry)
   │
   └──> Group F  (cherry-picks; 8e46bca depends on A; the other four are orthogonal)
```

Cherry-picks `9fed0f3`, `f9c9418`, `5700ef5`, `7e30a53` MAY land at any point after Group A. Cherry-pick `8e46bca` MUST land after Group A (it touches workflow path resolution).

### 0.4 Authorial conventions

- Paths use the post-restructure layout throughout (file moves enumerated in §1.1). Pre-restructure paths appear only in §1 and §2 (the restructure spec itself and the migration boundaries).
- File-line references use the form `path:line` (e.g., `claudechic/config.py:17`). Line numbers are best-effort and may shift; the `function:` qualifier is the durable handle.
- Code-shaped pseudocode is illustrative; acceptance bullets and test invariants pin the exact contracts.

### 0.5 Path-expression placeholders

The following names appear in path expressions and code-shape examples throughout the spec. They denote runtime values, not literal directory names.

- **`project_dir`** / **`<repo_root>`** / **`<launched_repo>`** — the launched-repo root (the working directory where claudechic was invoked). Populated at runtime from `self._cwd` in `claudechic/app.py:1440` and threaded through to `ProjectConfig.load(cls, project_dir: Path)` at `claudechic/config.py:108-110`. Three names, one referent; `project_dir` is the existing parameter name in the `ProjectConfig` API and is not renamed.
- **`<chicsession_name>`** — the value of a chicsession's `name` field at `<launched_repo>/.chicsessions/<name>.json`. Note: chicsessions are distinct from workflow runs; the artifact-dir path is supplied separately by the coordinator agent via `set_artifact_dir(path)` (per §5.2), not derived from the chicsession name.
- **`<main_wt>`** / **`main_wt_info[0]`** — the absolute path of the main worktree (the originally-cloned working tree). Used in §10's symlink expressions.
- **`<worktree_dir>`** — the absolute path of any worktree (main or sibling) where claudechic-managed state may be created.

---

## 1. Group A — Restructure (file moves + import rewrites)

Reorganize the codebase so engine code lives at `claudechic/workflows/` and bundled YAML/markdown content lives at `claudechic/defaults/`. After this group lands, every later group can rely on a single import path for engine code (`from claudechic.workflows import ...`) and a single layered-content directory pattern under `claudechic/defaults/` (workflows + global + mcp_tools). The work is pure file moves plus mechanical import rewrites; the test suite passes against the new layout with no behavior changes. If a test fails for any reason other than path resolution, surface it — that signals the move missed a site.

### 1.1 git mv operations (preserve history)

```bash
# 1. Engine Python files (six files; merge __init__.py into existing claudechic/workflows/)
git mv claudechic/workflow_engine/engine.py        claudechic/workflows/engine.py
git mv claudechic/workflow_engine/loader.py        claudechic/workflows/loader.py
git mv claudechic/workflow_engine/parsers.py       claudechic/workflows/parsers.py
git mv claudechic/workflow_engine/phases.py        claudechic/workflows/phases.py
git mv claudechic/workflow_engine/agent_folders.py claudechic/workflows/agent_folders.py
# (claudechic/workflow_engine/__init__.py contents merge by hand into claudechic/workflows/__init__.py)

# 2. Bundled workflow YAML directories (nine directories)
git mv claudechic/workflows/audit              claudechic/defaults/workflows/audit
git mv claudechic/workflows/cluster_setup      claudechic/defaults/workflows/cluster_setup
git mv claudechic/workflows/codebase_setup     claudechic/defaults/workflows/codebase_setup
git mv claudechic/workflows/git_setup          claudechic/defaults/workflows/git_setup
git mv claudechic/workflows/onboarding         claudechic/defaults/workflows/onboarding
git mv claudechic/workflows/project_team       claudechic/defaults/workflows/project_team
git mv claudechic/workflows/tutorial           claudechic/defaults/workflows/tutorial
git mv claudechic/workflows/tutorial_extending claudechic/defaults/workflows/tutorial_extending
git mv claudechic/workflows/tutorial_toy_project claudechic/defaults/workflows/tutorial_toy_project

# 3. Global manifest files (two files; both move under claudechic/defaults/global/)
git mv claudechic/global/hints.yaml claudechic/defaults/global/hints.yaml
git mv claudechic/global/rules.yaml claudechic/defaults/global/rules.yaml

# 4. MCP tools directory
git mv claudechic/mcp_tools claudechic/defaults/mcp_tools

# 5. Cleanup
rmdir claudechic/workflow_engine
rmdir claudechic/global
```

The order above is the canonical execution order. Operations 1–4 are independent; operation 5 runs last.

### 1.2 Import rewrites (22 files)

Mechanical: `from claudechic.workflow_engine import ...` → `from claudechic.workflows import ...`. The set of files to rewrite is enumerated by `grep -rln 'from claudechic.workflow_engine' claudechic/ tests/` against the pre-restructure tree. Implementer SHOULD use `sed`/`ruff`/`grep -r` to apply the rewrite and to verify all sites are caught. Completion is verified by the §1.5 acceptance bullet.

### 1.3 Path-reference rewrites (5 files)

Files referencing `claudechic/workflows/` paths for bundled-content lookup MUST be updated to `claudechic/defaults/workflows/`. The five files (post-move):

```
claudechic/app.py                       (workflow discovery sites)
claudechic/mcp.py                       (workflow discovery sites)
claudechic/onboarding.py                (workflow discovery sites)
claudechic/workflows/loader.py          (manifest loader internals)
claudechic/workflows/agent_folders.py   (agent-folder assembly)
```

The detailed rewrites are interleaved with Group C (loader rewrite); Implementer MAY land Group A's path-reference rewrites empty-handed (constants only) and let Group C wire them through `TierRoots`.

### 1.4 Doc-surface rewrites (do not skip)

Sixteen sites reference the pre-move layout:

| File | Edit |
|---|---|
| `claudechic/context/workflows-system.md` | Rewrite all `workflow_engine` mentions to `workflows/` |
| `claudechic/context/hints-system.md` | Same |
| `claudechic/context/guardrails-system.md` | Same |
| `claudechic/context/claudechic-overview.md` | Same |
| `claudechic/defaults/workflows/tutorial_extending/learner/edit-yaml-config.md` | Same |
| `claudechic/defaults/workflows/tutorial_extending/learner/add-rule.md` | Same |
| `claudechic/defaults/workflows/tutorial_extending/learner/add-advance-check.md` | Same |
| `CLAUDE.md` (project-root) | Rewrite the 3 occurrences (file-map block and section heading) — `workflow_engine/` → `workflows/` |
| `claudechic/onboarding.py:6` | LEAF MODULE comment — `from workflow_engine/` → `from workflows/` (or rephrased to match the comment's exact wording) |
| `claudechic/hints/types.py:9` | Same LEAF MODULE pattern |
| `claudechic/hints/triggers.py:6` | Same |
| `claudechic/hints/state.py:10` | Same |
| `claudechic/hints/parsers.py:8` | Same |
| `claudechic/hints/engine.py:10` | Same |
| `claudechic/guardrails/rules.py:3` | Same |
| `claudechic/guardrails/hooks.py:6` | Same |

### 1.5 Acceptance for Group A

- [ ] All nine bundled-workflow-directory moves complete (per §1.1 step 2), plus all engine .py file moves, global manifest moves, mcp_tools move, and the cleanup rmdir steps.
- [ ] All import rewrites complete: `grep -rn 'from claudechic.workflow_engine' claudechic/ tests/` returns zero matches; `pyright` clean.
- [ ] All 5 path-reference sites point at `claudechic/defaults/workflows/`.
- [ ] All sixteen doc-surface sites in §1.4 free of `workflow_engine` references.
- [ ] Zero `workflow_engine` references in tracked code/doc surfaces: `grep -rn 'workflow_engine' claudechic/ tests/ CLAUDE.md` returns zero matches, with the exception of tutorial content under `claudechic/defaults/workflows/tutorial_extending/learner/*.md` if those files retain text-only references for pedagogical reasons (those references are not active code).
- [ ] `claudechic/workflow_engine/` and `claudechic/global/` directories do not exist.
- [ ] `pytest tests/ -n auto` passes (no behavioral change expected at this phase).

---

## 2. Group B — Boundary relocation (state files leave `.claude/`)

Move every claudechic primary-state file out of `.claude/` and into `.claudechic/`. After this group lands, claudechic owns its own filesystem namespace at `~/.claudechic/` (user) and `<repo>/.claudechic/` (project); `.claude/` becomes Claude Code's territory only. Per the §9 boundary rule, no primary-state writes resolve inside `.claude/`. If pre-existing user files are encountered at the old paths, surface them — but do NOT migrate them; silent loss is the accepted tradeoff for this run.

claudechic MUST NOT include any migration logic and MUST NOT emit any startup warning for pre-existing files. Existing `~/.claude/.claudechic.yaml`, `<repo>/.claude/hints_state.json`, and `<repo>/.claude/hits.jsonl` files left in place are NOT moved by claudechic code and NOT logged.

### 2.1 User config relocation

| Edit | From | To |
|---|---|---|
| `claudechic/config.py:17` `CONFIG_PATH` | `Path.home() / ".claude" / ".claudechic.yaml"` | `Path.home() / ".claudechic" / "config.yaml"` |
| `claudechic/config.py:18` `_OLD_CONFIG_PATH` | `Path.home() / ".claude" / "claudechic.yaml"` | **DELETE** the constant entirely |
| `claudechic/config.py:29-32` legacy migration `if/elif` block | active migration code | **DELETE** entire block |

The boundary-test registry entry `config.load.legacy_rename` is deleted alongside.

### 2.2 Project config relocation (file-form → directory-form)

| Edit | From | To |
|---|---|---|
| `claudechic/config.py:110` `config_path` | `project_dir / ".claudechic.yaml"` | `project_dir / ".claudechic" / "config.yaml"` |
| `ProjectConfig.save(self, project_dir)` (NEW helper per §7.5) | n/a | symmetric writer creating `.claudechic/config.yaml`, with `mkdir(parents=True, exist_ok=True)` |

### 2.3 Hint state relocation

| Edit | From | To |
|---|---|---|
| `claudechic/hints/state.py:127` `_STATE_FILE` | `".claude/hints_state.json"` | `".claudechic/hints_state.json"` |

### 2.4 hits.jsonl relocation

The path-relocation edit is at the caller in `claudechic/app.py:1494`, where `HitLogger` is constructed. `HitLogger` itself (in `claudechic/guardrails/hits.py`) is path-agnostic — it takes its hits-file path as a constructor argument — and does NOT need any edit.

| Edit | From | To |
|---|---|---|
| `claudechic/app.py:1494` (path passed to `HitLogger`) | `<project>/.claude/hits.jsonl` | `<project>/.claudechic/hits.jsonl` |

### 2.5 Worktree state propagation (parallel `.claudechic` symlink)

A parallel `.claudechic/` symlink IS added at `claudechic/features/worktree/git.py:293-301`, mirroring the existing `.claude/` symlink pattern. Project-tier `<launched_repo>/.claudechic/` content propagates from the main worktree to new worktrees. Full mechanics in §10.

### 2.6 Doc-surface rewrite — old global config path references

Seven sites hard-code the old global config path. All update to `~/.claudechic/config.yaml`:

```
CLAUDE.md:318
claudechic/theme.py:3
claudechic/theme.py:87
claudechic/errors.py:77
claudechic/context/CLAUDE.md:79
docs/privacy.md:36
claudechic/config.py:17                          (docstring)
```

### 2.7 Test fixture deltas

Pre-existing test files that construct `<tmp_path>/.claude/...` for unit-test scaffolding MUST be updated alongside the production-path migrations:

| Test file | Change |
|---|---|
| `tests/test_bug12_guardrails_detect_field.py:68,100,132,160` | `tmp_path / ".claude" / "hits.jsonl"` → `tmp_path / ".claudechic" / "hits.jsonl"` |
| `tests/test_workflow_guardrails.py:67,86,108,154,200,244,270,308,351` | Same (8 occurrences) |
| `tests/test_workflow_hits_logging.py:44,100,149` | Same (3 occurrences) |
| `tests/test_hints_integration.py:178` | `state_dir = tmp_path / ".claude"` → `tmp_path / ".claudechic"` |
| `tests/test_welcome_screen_integration.py:76` | `state_file = tmp_path / ".claude" / "hints_state.json"` → `tmp_path / ".claudechic" / "hints_state.json"` |
| `tests/test_bug16_sessions_encoding.py:36` | NO change (constructs `tmp_path / ".claude" / "projects"` to simulate Claude-owned session JSONL store; that's a Claude-owned read path, not a claudechic write). |
| `tests/test_roborev.py:402,425,439` | NO change (constructs `tmp_path / ".claude" / "skills"` to simulate Claude-owned skills; reads only). |
| `tests/conftest.py:109` | Update comment string mentioning `~/.claude/.claudechic.yaml` → `~/.claudechic/config.yaml`. |
| `tests/test_config_integration.py:56,80` and `tests/test_welcome_screen_integration.py:112` | `tmp_path / ".claudechic.yaml"` (FILE form) → `tmp_path / ".claudechic" / "config.yaml"` (DIRECTORY form). |

### 2.8 Acceptance for Group B

- [ ] Every primary-state write that previously resolved under `.claude/` now resolves under `.claudechic/` (user config, hint state, guardrail hits log).
- [ ] No code path in claudechic writes to `~/.claude/.claudechic.yaml`, `<repo>/.claude/hints_state.json`, or `<repo>/.claude/hits.jsonl`.
- [ ] Doc-surface rewrites complete (seven sites in §2.6).
- [ ] Test fixture path updates complete (per §2.7).
- [ ] No migration logic exists (no `if old_path.exists(): rename(...)`).
- [ ] No startup warning logic exists (no `if old_path.exists(): warn(...)`).

---

## 3. Group C — 3-tier loader + override resolution

Generalize the manifest loader from a single-tier scan into a three-tier walk that overlays package, user, and project content with override-by-id resolution. After this group lands, users can override workflows, rules, hints, checks, and MCP tools at user or project level without modifying the bundled package; partial overrides surface as actionable load errors. Engine logic remains tier-agnostic (rule evaluation, hint matching, phase advance MUST NOT branch on tier identity); UI surfaces consume per-id provenance maps for "defined at" displays. If implementing this group reveals a content category (e.g., a new parser) that doesn't fit override-by-id semantics, surface it — every category must agree on the resolution law.

Implementer MUST NOT consult `git show d55d8c0` or any partial-extraction approach (the cherry-pick is dropped per §6.1); the new loader is built from scratch.

### 3.1 Tier model

Three tiers, in ascending priority:

| Tier | Filesystem root | Required? |
|---|---|---|
| `package` | `claudechic/defaults/` (ships with the install) | **Yes** — fail-closed if missing |
| `user` | `~/.claudechic/` | No — skip silently if absent |
| `project` | `<launched_repo>/.claudechic/` | No — skip silently if absent |

Each tier root, when present, MUST contain the layout:

```
<root>/
├── workflows/<workflow_id>/<workflow_id>.yaml
├── workflows/<workflow_id>/<role>/{identity,phase}.md
├── global/rules.yaml
├── global/hints.yaml
└── mcp_tools/*.py
```

Subtrees MAY be missing. A missing subtree contributes zero records for that category in that tier.

`app.py` constructs the tier roots at startup: package = `<package_dir>/defaults`; user = `~/.claudechic/` if it `is_dir()`, else `None`; project = `<cwd>/.claudechic/` if it `is_dir()`, else `None`.

### 3.2 Per-category resolution (binding identity units)

Each content category has a stable identity unit. Resolution is **override-by-id, full-record replacement** — when the same identity appears in two tiers, the higher-priority tier's record wins entirely; lower-tier records of the same id are silently replaced (no field-level merging).

| Category | Identity unit | Notes |
|---|---|---|
| Workflow | `workflow_id` (YAML field, fallback to directory name) | Winning tier owns the **entire** workflow directory: identity.md, all role markdown, all phase markdown. No file-by-file mixing across tiers. |
| Rule | `Rule.id` (qualified `<namespace>:<bare_id>`) | Non-conflicting ids accumulate across tiers. |
| Injection | `Injection.id` | Non-conflicting ids accumulate. |
| Hint | `HintDecl.id` (qualified) | Lifecycle state persists across override (the lifecycle-key is the qualified id). |
| Check | `CheckDecl.id` | Non-conflicting ids accumulate. |
| Phase | `Phase.id` (qualified `<workflow_id>:<phase_id>`) | Phases belonging to a workflow whose winning tier is NOT this phase's tier are pruned (workflow override is full-record). |
| MCP tool | `tool.name` | Same override-by-id logic; non-conflicting names accumulate. |

A single generic resolution helper MUST implement the resolution for all categories; each parser supplies its identity callback (no per-parser bespoke logic).

### 3.3 Within-tier vs cross-tier duplicates

- **Within-tier duplicate id:** parser MUST emit a `LoadError(source="validation", section=<key>, item_id=<id>, message="duplicate id within tier <tier>; later occurrence dropped")`. First occurrence kept; later occurrences dropped.
- **Cross-tier duplicate id:** no error. Higher-priority tier wins; lower-priority records of the same id are silently replaced. This is the override mechanism.

### 3.4 Partial-override detection

A higher-tier directory that defines a `workflow_id` but is missing files present in a lower-tier directory for the same `workflow_id` is a **partial override** and MUST be rejected. The full file set is required for an override to take effect.

Detection rule (informal): for each `workflow_id`, compute the set of relative file paths under each tier's `workflows/<workflow_id>/`. If a higher-priority tier's set is a strict subset of a lower-priority tier's set (i.e., higher tier is missing one or more files the lower tier has), the higher tier's contribution is a partial override.

On detection, the loader MUST:

1. Emit a `LoadError(source="validation", section="workflow", item_id=<workflow_id>, message=...)` with this verbatim wording (substituting the path and missing-file list):
   *"Partial workflow override at `<higher_tier_path>`: missing `<file1>`, `<file2>`. Workflow overrides require the full file set. Copy the missing files from the lower level (package or user), or remove the partial override at `<higher_tier_path>`."*
2. **Drop** the higher tier's contribution for that workflow_id; resolution falls through to the next-lower tier.
3. Continue checking lower tiers (a lower tier may itself partial-override another tier below it).
4. Files the higher tier *adds* (present in higher but not lower) are permitted — overrides MAY extend the file set.

The error appears on `LoadResult.errors` and the TUI surfaces it through the existing error-toast pattern at `claudechic/app.py:1524-1529`. App startup is NOT blocked.

### 3.5 Tier provenance

Every parsed record carries a `tier` field set to the tier where it survived resolution. The fields are **opaque metadata for the engine**: rule evaluation, hint matching, and phase-advance logic MUST NOT branch on tier identity. UI surfaces (workflow picker, settings disabled-workflows discovery) MAY consume tier identity for display.

The loader output exposes two provenance maps:

- `workflow_provenance: dict[str, frozenset[Tier]]` — for each workflow id, every tier where it was defined (winning tier always included).
- `item_provenance: dict[str, frozenset[Tier]]` — for each item id (rule/injection/hint/check), every tier where it was defined.

UI surfaces consume these maps for "defined at: package, user" labels; the disable filter (§3.6) consults them for unknown-id detection.

### 3.6 Disable filter — tier-aware, unknown-id warn-don't-error

The disable-filter step (`_filter_load_result(result, config)` at `claudechic/app.py:150`) supports two entry shapes per the §0.2 vocabulary entry: bare IDs and tier-targeted (`<tier>:<id>`) IDs.

**Effective disable lists.** Both `disabled_workflows` and `disabled_ids` are unioned across user-config and project-config (additive across the two config tiers; an entry in either takes effect). The merged lists are split by entry shape into a *bare* set and a *tier-targeted* set keyed by `(tier, id)`.

**Tier-targeted entries** apply during per-category resolution (§3.2): the loader treats the named tier's record of `<id>` as if it did not exist; resolution proceeds normally — the next-highest tier with the same id wins, or the id falls out of the resolved set if no other tier defines it. For workflow ids, dropping a tier's contribution also removes phase/rule/hint/check records whose namespace is that workflow at that tier (same pruning as partial-override fall-through, §3.4).

**Bare-ID entries** apply post-resolution: every workflow whose id appears in the bare set is removed from the resolved workflows; every item whose id appears in the bare set is removed from the resolved rules/injections/hints/checks. Bare-ID disable also removes records whose `namespace` matches the bare workflow id (existing behavior; preserves child-record disable).

**Invalid tier prefix.** An entry of the form `<prefix>:<id>` where `<prefix>` is not in `{package, user, project}` MUST be skipped with a WARNING via `claudechic.errors.log` of the form `disabled_workflows: invalid tier prefix '<prefix>' in entry '<entry>'; valid prefixes are package, user, project` (symmetric for `disabled_ids`). The entry is treated as if it were not present (it does NOT fall back to bare-ID semantics).

**Unknown id** (a bare id not defined at any tier, or a tier-targeted `<tier>:<id>` whose `<id>` is not defined at `<tier>`): log a WARNING via `claudechic.errors.log` (`disabled_workflows: unknown workflow_id '<id>' (not defined at <tier>)` for tier-targeted; `... (not defined at any tier)` for bare). MUST NOT raise an exception, add a `LoadError`, or prevent app startup.

**Schema.** `disabled_workflows` and `disabled_ids` are flat lists of strings. Each string is either a bare id or `<tier>:<id>`. No nested per-tier sub-keys.

### 3.7 Worker-side changes

| File | Change |
|---|---|
| `claudechic/workflows/loader.py` | Replace single-tier `discover_manifests` with three-tier walk + per-category resolution + partial-override detection. Add provenance maps to load result. |
| `claudechic/workflows/parsers.py` | `PhasesParser` produces tier-tagged records and resolves across tiers. |
| `claudechic/workflows/agent_folders.py` | `assemble_phase_prompt(workflow_dir, role_name, current_phase)` takes a directly resolved workflow directory (no more multi-tier scanning); the legacy `_find_workflow_dir` helper is removed. `create_post_compact_hook(engine, agent_role, workflows_dir)` is unchanged from existing-code shape; on `/compact` the closure calls `assemble_phase_prompt(...)` to regenerate the phase prompt and returns `{"reason": prompt}`. |
| `claudechic/guardrails/parsers.py`, `claudechic/hints/parsers.py`, `claudechic/checks/parsers.py` | Each parser tags records with their tier and resolves across tiers via the shared resolution helper. |
| `claudechic/guardrails/rules.py`, `claudechic/hints/types.py`, `claudechic/checks/protocol.py`, `claudechic/workflows/phases.py` | Parsed-record dataclasses (`Rule`, `Injection`, `HintDecl`, `CheckDecl`, `Phase`) gain a `tier` field. |
| `claudechic/mcp.py` | `discover_mcp_tools` walks all three tiers; module-import isolation uses tier-namespaced `sys.modules` keys (so `package/cluster.py` and `project/cluster.py` can both import); returns tier-tagged tool wrappers; resolves overrides by `tool.name`. |
| `claudechic/app.py` | Constructs the three tier roots at startup; replaces the existing `self._workflows_dir` instance-attribute lookups with lookups against the resolved-workflow path on the load result. |

The `discover_manifests` free function is removed; callers walk the three-tier path or the single-tier helper. Documentation files referencing `discover_manifests` (the three tutorial markdown files at `claudechic/defaults/workflows/tutorial_extending/learner/*.md`) MUST be rewritten to call the new walker.

### 3.8 Error semantics

| Condition | Behavior |
|---|---|
| Package tier root missing or unreadable | Fatal: load result carries one `LoadError(source="discovery", message="package tier unreadable: ...")`; content lists are empty. App can still start (UI shows error toast); workflows/rules/hints are unavailable. |
| User or project tier root unreadable | Fail-open: `LoadError` logged; that tier contributes zero content; other tiers still load. |
| Individual manifest YAML parse error | `LoadError(source=str(path), message=...)`; that manifest skipped; other manifests still load. |
| Individual record validation error (per-record) | Logged warning; record skipped; no `LoadError` surfaced. |
| Within-tier duplicate id | `LoadError` per §3.3; first occurrence kept. |
| Cross-tier duplicate id | No error; override applied. |
| Partial override at higher tier | `LoadError` per §3.4; higher tier's contribution dropped; fall-through to lower tier. |

The loader MUST NOT consult `ProjectConfig` (no `disabled_workflows` or `disabled_ids` lookup inside the load step). Filter is applied by the caller via §3.6.

### 3.9 Acceptance for Group C

- [ ] All six parsed-record dataclasses (`Rule`, `Injection`, `HintDecl`, `Phase`, `CheckDecl`, `WorkflowData`) carry a `tier` field.
- [ ] `WorkflowData` carries both winning `tier` and `defined_at: frozenset[Tier]` (every tier where the workflow id is defined).
- [ ] Load result exposes `workflow_provenance` and `item_provenance` per §3.5.
- [ ] The free function `discover_manifests` is removed; callers use the new three-tier walker or the single-tier helper.
- [ ] `app.py` constructs the three tier roots per §3.1.
- [ ] `_filter_load_result` supports both bare-ID and tier-targeted (`<tier>:<id>`) entries per §3.6; warns (does not error) on unknown ids and on invalid tier prefixes; unions user-config and project-config disable lists.
- [ ] `discover_mcp_tools` walks all three tiers; module imports use tier-namespaced `sys.modules` keys; returns tier-tagged tools.
- [ ] All test invariants in §12.1 (override-resolution; INV-1, INV-2, INV-3, INV-4, INV-5, INV-8, INV-PO-1, INV-PO-2, INV-PO-3) have corresponding tests in `tests/test_loader_tiers.py`.
- [ ] Tier-as-opaque-metadata enforcement: `grep -rnE 'tier ==|tier !=|\.tier ==|\.tier !=' claudechic/hints/ claudechic/guardrails/ claudechic/checks/` returns zero matches. (Engine logic in those packages MUST NOT branch on tier identity; tier comparisons live exclusively in `claudechic/workflows/loader.py` and `claudechic/workflows/parsers.py`. UI surfaces under `claudechic/screens/` and `claudechic/widgets/` MAY reference tier for display.)
- [ ] Cherry-pick `d55d8c0` is NOT used (no `git cherry-pick d55d8c0`, no `git show d55d8c0`-derived code).

---

## 4. Group D — claudechic-awareness install + phase-prompt delivery

Group D delivers two independent things with different reach. First, an idempotent install routine copies `claudechic/context/*.md` into `~/.claude/rules/claudechic_*.md` at every claudechic startup, so every Claude Code session in every project — claudechic-spawned or not — auto-loads claudechic's bundled rules via the SDK. Second, claudechic-managed workflows push phase-specific instructions to the active agent: the engine assembles each phase's identity-and-instructions prompt and sends it directly to the agent on workflow activation and on each phase advance; the `PostCompact` hook regenerates the same prompt to re-inject after `/compact`. No file on disk — phase-prompt delivery is in-memory and inline-to-chat. After this group lands, a fresh Claude session in any project understands claudechic, and a claudechic-managed agent inside an active workflow always has the right phase-specific instructions for the phase it's currently in. Watch for: any code path that conflates the two — paths under `~/.claude/rules/` whose basename does NOT start with `claudechic_` belong to the user and MUST NOT be read, written, or unlinked by claudechic; if you find such a code path, stop and surface it.

### 4.1 Module to create — `claudechic/awareness_install.py`

A new small module with the install routine. The routine is also invoked by the `/onboarding context_docs` phase (which calls into this module).

```python
# claudechic/awareness_install.py — illustrative shape; Implementer adapts.

from dataclasses import dataclass
from pathlib import Path

CLAUDE_RULES_DIR = Path.home() / ".claude" / "rules"
PKG_CONTEXT_DIR = Path(__file__).parent / "context"
INSTALL_PREFIX = "claudechic_"

@dataclass(frozen=True)
class InstallResult:
    new: list[str]               # bundled <name>s newly installed
    updated: list[str]           # bundled <name>s overwritten
    skipped: list[str]           # bundled <name>s where content already matched
    deleted: list[str]           # orphan claudechic_*.md files removed (per §4.2 DELETE pass)
    skipped_disabled: bool       # True iff awareness.install is False (no I/O at all)

def install_awareness_rules(force: bool = False) -> InstallResult:
    """Idempotent NEW/UPDATE/SKIP/DELETE install of bundled context docs into
    ~/.claude/rules/claudechic_<name>.md. Honors awareness.install config
    (no-op when False unless force=True). Creates parent directory if absent.
    Removes orphan claudechic_*.md files no longer in the bundled catalog
    (DELETE pass). Skips any target that is a symlink (user-managed).
    """
```

Public API: one function `install_awareness_rules(force: bool = False) -> InstallResult`. Module is engine-isolated (no imports from `app.py`, UI widgets, or `agent.py`); only depends on `claudechic.config` (for the toggle), `claudechic.errors` (for the log channel), and stdlib.

### 4.2 Install routine semantics

**MUST:**

- Read `claudechic.config.CONFIG["awareness"]["install"]` (boolean; defaults `True`; user-tier; loaded by `claudechic/config.py` per §4.3 below). If `False` and `force=False`, return `InstallResult(new=[], updated=[], skipped=[], deleted=[], skipped_disabled=True)` immediately. **No file I/O when disabled** — including no DELETE pass.
- Create `~/.claude/rules/` parent directory if absent (`mkdir(parents=True, exist_ok=True)`).
- Compute the bundled catalog set: `bundled_names = {p.stem for p in PKG_CONTEXT_DIR.glob("*.md")}` (top-level only; no recursion into subdirectories of `claudechic/context/`).
- For each bundled file `<name>.md`:
  - Compute target path `~/.claude/rules/claudechic_<name>.md`.
  - **Symlink guard:** if `target.is_symlink()`, log a WARNING (`"awareness install: target ~/.claude/rules/claudechic_<name>.md is a symlink; treating as user-managed; skipping"`) and skip the file entirely (no NEW/UPDATE/SKIP/DELETE action). The symlink is left in place untouched. The install routine MUST NOT follow the symlink to write into its target, MUST NOT `unlink` the symlink itself, MUST NOT byte-compare via the symlink (that would follow it). The bundled `<name>` is omitted from `new`/`updated`/`skipped`/`deleted` lists.
  - If target does not exist: copy bundled content to target (NEW). Append `<name>` to `result.new`.
  - If target exists, is a regular file (not a symlink), and `target.read_bytes() == bundled.read_bytes()`: no write (SKIP). Append `<name>` to `result.skipped`.
  - If target exists, is a regular file, and content differs: copy bundled content over target (UPDATE). Append `<name>` to `result.updated`. claudechic owns `claudechic_*.md` regular-file paths; manual user edits to those filenames are clobbered. No warning is emitted; the user-facing contract is documented in `docs/configuration.md` §8.3.
- **DELETE pass** (after the per-bundled-file loop): scan direct children of `~/.claude/rules/` whose basename matches the regex `^claudechic_[^/]+\.md$`. For each match:
  - If the path is a symlink: skip it (per the symlink guard; user-managed). Do NOT `unlink`.
  - Compute `<orphan> = path.stem.removeprefix("claudechic_")`. If `<orphan>` is in `bundled_names`: skip (the file was already handled by the per-bundled-file loop above).
  - Otherwise: `path.unlink()`. Append `<orphan>` to `result.deleted`.
  - The DELETE pass MUST NOT recurse into subdirectories of `~/.claude/rules/`.
- Log diagnostic counts via `claudechic.errors.log` at INFO level (`NEW=N UPDATE=N SKIP=N DELETE=N`).
- Return the `InstallResult` with per-branch `<name>` lists.

**MUST NOT:**

- Write any file outside `~/.claude/rules/`.
- Write any file inside `~/.claude/rules/` whose basename does not match `claudechic_*.md`.
- Delete any file inside `~/.claude/rules/` whose basename does NOT match `claudechic_*.md` (the DELETE pass is bounded to the claudechic-owned namespace by basename).
- Delete or modify any symlink at any `claudechic_*.md` target (symlink guard above; user-managed inodes are never touched).
- Recurse into subdirectories of `~/.claude/rules/` for either the per-bundled-file loop OR the DELETE pass.
- Run the DELETE pass when `awareness.install=False` and `force=False` (the toggle gates the entire routine).
- Create symbolic links of any kind.
- Modify or read any other path under `~/.claude/` (no `settings.json`, no `commands/`, no `skills/`).

### 4.3 Config key — `awareness.install`

A new user-tier config key (defaults in code; lives at `~/.claudechic/config.yaml`):

| Key | Tier | Type | Default | Purpose |
|---|---|---|---|---|
| `awareness.install` | user | bool | `True` | Gates the install routine (§4.2). When `False`, the install routine no-ops on startup — no NEW writes, no UPDATE writes, no SKIP byte-compare reads, no DELETE pass. Existing installed `~/.claude/rules/claudechic_*.md` files are NOT removed by claudechic when the toggle flips `True → False`; the SDK continues to load them in every session until the user manually `rm`s them (see helper text in §7.3 + documentation in §8.3). |

`claudechic/config.py:_load()` MUST add (alongside existing `setdefault` lines around 38–47):

```python
config.setdefault("awareness", {})
config["awareness"].setdefault("install", True)
```

The Settings UI (Group G) surfaces this key per §7.3.

### 4.4 Startup invocation

`claudechic/app.py` `on_mount` (or equivalent post-init point; current `on_mount` site near line 980) MUST invoke `install_awareness_rules()` once during startup, BEFORE the first agent is spawned. Failure (any exception) MUST be logged at WARNING level and MUST NOT prevent app startup. The invocation happens regardless of whether a workflow is active. On success, log INFO with the NEW/UPDATE/SKIP/DELETE counts (skipped when `skipped_disabled` is true).

### 4.5 Drift trigger and hint — DELETED

The `ContextDocsDrift` trigger and the `context_docs_outdated` hint are DELETED.

Code edits required:

| Item | Edit |
|---|---|
| `ContextDocsDrift` class | DELETE class body and `_PKG_CONTEXT_DIR` constant from `claudechic/hints/triggers.py:25-82` and `claudechic/hints/triggers.py:22` |
| `ContextDocsDrift` import + export | DELETE `from claudechic.hints.triggers import ContextDocsDrift` from `claudechic/hints/__init__.py:8` and `"ContextDocsDrift"` from `__all__` at `claudechic/hints/__init__.py:24` |
| `ContextDocsDrift` registration | DELETE `_trigger_registry["context-docs-drift"] = ContextDocsDrift` at `claudechic/app.py:1387–1389` (and surrounding try/except) |
| `context_docs_outdated` hint | DELETE the `context_docs_outdated` declaration at `claudechic/defaults/global/hints.yaml:93–99` (plus the section comment if no other hints remain in that section) |
| `claudechic/hints/types.py:212` docstring | Update example to not reference `"context-docs-drift"` |

### 4.6 `/onboarding context_docs` phase — adapted

The `context_docs` phase (`claudechic/defaults/workflows/onboarding/onboarding_helper/context_docs.md`) and its workflow YAML entry (`claudechic/defaults/workflows/onboarding/onboarding.yaml:14-26`) are preserved. The `onboarding_helper/identity.md` "Context" section at lines 26-32 and the bullet at lines 10-11 are also preserved.

The phase doc invokes `claudechic.awareness_install.install_awareness_rules(force=True)` (e.g., via a Bash invocation `python -c "from claudechic.awareness_install import install_awareness_rules; r = install_awareness_rules(force=True); print(r)"`) and reports the result to the user via the agent's response surface.

The phase doc target dir is `~/.claude/rules/` (matches `awareness.install` user-tier config). The phase doc reflects the new dir, the prefix, and the call to the install routine.

### 4.7 Phase-prompt delivery (separate from awareness install)

Phase prompts reach the active agent in-memory and inline-to-chat — no file is written to disk. Three delivery paths:

| Event | Site | Action |
|---|---|---|
| Workflow activation | `app.py._activate_workflow` | Engine calls `assemble_phase_prompt(workflow_dir, role_name, current_phase)`; sends the result to the active agent via `_send_to_active_agent(...)` as part of the kickoff chat message. The kickoff message body IS the assembled phase prompt. |
| Phase advance | `mcp.py:_make_advance_phase` (active flow); `app.py._inject_phase_prompt_to_main_agent` retained as a callable helper. | The `advance_phase` MCP tool drives phase-advance prompt delivery: on a successful advance it calls `assemble_phase_prompt(workflow_dir, role_name, current_phase)` for the new phase and sends the result to the active agent via `_send_to_active_agent(...)`. `_inject_phase_prompt_to_main_agent` is preserved as a reusable injection helper but is NOT called from `advance_phase`'s flow (sidebar refresh routes through `_update_sidebar_workflow_info()` to avoid double-injection on the coordinator). |
| Workflow deactivation | `app.py._deactivate_workflow` | Engine clears in-memory state and notifies the sidebar/agent via the existing notification path. No file I/O. |
| `/compact` re-injection | `agent_folders.create_post_compact_hook(engine, agent_role, workflows_dir)` (existing-code shape at `agent_folders.py:147`; `workflows_dir` is the parent directory containing all workflow subdirs, per §3.7) | The closure captures `(engine, agent_role, workflows_dir)`; on `/compact` it resolves `workflow_dir = workflows_dir / engine.workflow_id`, reads `engine.get_current_phase()`, calls `assemble_phase_prompt(workflow_dir, agent_role, current_phase)`, and returns `{"reason": prompt}` if non-empty, `{}` otherwise. |

`assemble_phase_prompt(workflow_dir, role_name, current_phase)` is the single producer of phase-prompt content for all four delivery paths; the 3-arg shape (single resolved workflow directory) matches the post-Group-C signature defined in §3.7.

### 4.8 Boundary classification

The install routine's writes (NEW + UPDATE) and unlinks (DELETE pass) are one of the three explicit `.claude/`-area exceptions allowed by the §9 boundary rule (claudechic-prefixed files at `~/.claude/rules/claudechic_*.md`). The routine MUST NOT write or unlink any file in `~/.claude/rules/` whose basename does not match `claudechic_*.md`; the symlink guard in §4.2 plus the basename predicate are the binding constraints.

Group D writes no other files. Phase-prompt delivery (§4.7) is in-memory only and produces no `.claude/`-area writes.

### 4.9 Acceptance for Group D

- [ ] `claudechic/awareness_install.py` exists and exposes `install_awareness_rules(force: bool = False) -> InstallResult`. `InstallResult` carries five fields: `new`, `updated`, `skipped`, `deleted`, `skipped_disabled`.
- [ ] Install routine has four branches NEW / UPDATE / SKIP / DELETE per §4.2; the DELETE pass is bounded by basename regex `^claudechic_[^/]+\.md$` and does not recurse.
- [ ] Install routine MUST check `target.is_symlink()` before any read/write/unlink at `~/.claude/rules/claudechic_*.md` paths; symlinks are skipped with a WARNING log and are NEVER read, written, or unlinked (per §4.2 symlink guard).
- [ ] When `awareness.install=False` and `force=False`, the install routine performs zero file I/O — including no DELETE pass and no SKIP byte-comparison reads (per INV-AW-2).
- [ ] `claudechic/config.py:_load()` adds `awareness.install` (default `True`) per §4.3.
- [ ] `claudechic/app.py` `on_mount` invokes `install_awareness_rules()` once during startup; failure is logged WARNING but does not prevent startup.
- [ ] `ContextDocsDrift` class is DELETED from `claudechic/hints/triggers.py` per §4.5.
- [ ] `context_docs_outdated` hint is DELETED from `claudechic/defaults/global/hints.yaml` per §4.5.
- [ ] `from claudechic.hints.triggers import ContextDocsDrift` raises `ImportError` after Group D lands.
- [ ] `/onboarding context_docs` phase is preserved in `claudechic/defaults/workflows/onboarding/onboarding.yaml`; phase doc adapted per §4.6 to invoke `install_awareness_rules(force=True)` and to reference the `~/.claude/rules/` location.
- [ ] `claudechic/defaults/workflows/onboarding/onboarding_helper/identity.md` keeps the Context section and bullet (no deletion).
- [ ] On workflow activation, the engine sends the assembled phase prompt to the active agent via `_send_to_active_agent` (verifiable by mocking `_send_to_active_agent`); the kickoff message body IS the assembled phase prompt.
- [ ] On phase advance, the `advance_phase` MCP tool (`mcp.py:_make_advance_phase`) calls `assemble_phase_prompt` for the new phase and sends the result via `_send_to_active_agent` (no file I/O); sidebar refresh routes through `_update_sidebar_workflow_info()`. `_inject_phase_prompt_to_main_agent` remains available as a reusable injection helper but is NOT invoked from `advance_phase`'s flow.
- [ ] `agent_folders.create_post_compact_hook(engine, agent_role, workflows_dir)` retains the existing-code closure shape; the closure resolves `workflow_dir = workflows_dir / engine.workflow_id`, calls `assemble_phase_prompt(workflow_dir, agent_role, current_phase)`, and returns `{"reason": prompt}` on non-empty, `{}` otherwise. No file I/O.
- [ ] No new code path writes inside `.claude/` other than the install routine (which writes only to `~/.claude/rules/claudechic_<name>.md` paths matching the bundled catalog).
- [ ] All install-routine test invariants in §12.2.1 (INV-AW-1..5, INV-AW-10, INV-AW-11) and the phase-prompt-delivery invariants in §12.2.2 covered.

---

## 5. Group E — Workflow artifact directories

Give each workflow run a stable on-disk location where agents can pass artifacts (specs, status, plans, hand-off material) to one another. The directory path is decided by the workflow's coordinator agent during a Setup-style phase based on workflow content (e.g., a project name derived from the user's vision), not at activation, and the coordinator chooses the full path — claudechic does not impose a fixed prefix. After this group lands, the coordinator calls a new MCP tool `set_artifact_dir(path)` once per run; the engine resolves the path, creates the directory, and binds it to the run; subsequent agents see the absolute path baked into their workflow markdown via the `${CLAUDECHIC_ARTIFACT_DIR}` substitution token and may query it at runtime via the `get_artifact_dir` MCP tool. The artifact_dir is persisted in chicsession state, so on resume the engine reads it automatically — the coordinator does not need to re-call `set_artifact_dir`.

### 5.1 Engine API

| Site | Edit |
|---|---|
| `claudechic/workflows/engine.py` `WorkflowEngine.__init__` | Does NOT accept `artifact_dir` (no kwarg). Accepts a `cwd: Path \| None = None` kwarg used as the resolution base for relative paths in `set_artifact_dir`; the engine stores the value as `self._cwd` and does NOT hold a reference to the `ChatApp` instance for this purpose. |
| `claudechic/workflows/engine.py` `WorkflowEngine.artifact_dir` | Read-only property. Initial value: `None`. Becomes the resolved absolute `Path` after `set_artifact_dir(...)` succeeds. |
| `claudechic/workflows/engine.py` `WorkflowEngine.set_artifact_dir(path: str | Path) -> Path` | New method. Accepts a full path (absolute, or relative to the launched-repo root which the engine resolves via `(self._cwd / path).resolve()`). Validates: rejects empty string; rejects paths containing null bytes (`\x00`) or embedded newlines; **rejects any path that resolves inside any `.claude/` ancestor directory** (workflow content MUST NOT be smuggled into Claude's namespace). Raises `ValueError` on invalid input. Creates the directory with `mkdir(parents=True, exist_ok=True)`; stores the resolved absolute path as the engine's `artifact_dir`. **MUST trigger a chicsession persist via `engine.persist_fn` (the same mechanism that fires on phase advance) before the call returns**, so the new artifact_dir lands in the chicsession file before the next caller-visible event. Returns the path. **Idempotent on the same resolved path** (re-call returns the same path; no error; persist still fires — write is idempotent). **Calling with a different resolved path after one has been set raises `RuntimeError`** (one artifact dir per workflow run; mid-workflow path changes are not permitted by design). |
| `claudechic/workflows/engine.py` `WorkflowEngine.get_artifact_dir() -> Path | None` | New accessor. Returns the engine's `artifact_dir` value (the resolved absolute `Path` if set, else `None`). May also be reached via the `artifact_dir` property; both surfaces are equivalent. |
| `claudechic/workflows/engine.py` `WorkflowEngine.from_session_state` | Reads `artifact_dir` from saved state. If the saved field is a non-empty string, re-runs the validation predicates (rejects null bytes / embedded newlines / `.claude/`-ancestor paths — guards against tampered state) and stores the resolved path on the engine. The mkdir step from `set_artifact_dir` is NOT performed on resume: if the saved path exists on disk, just store it; if the saved path no longer exists on disk, log a WARNING (`"chicsession resume: saved artifact_dir <path> no longer exists on disk; keeping the stored path so the coordinator can decide whether to restore or relocate"`) and keep the path stored on the engine without recreating the directory (that would mask a deliberate user move/delete). The validation-failure carve-out is narrow: only tampered paths (security violations — null bytes / embedded newlines / `.claude/`-ancestor) raise on engine construction; missing-on-disk does not raise. |
| `claudechic/workflows/engine.py` `WorkflowEngine.to_session_state` | MUST include `artifact_dir` as a field in the serialized state when the engine has one set (the resolved absolute path string). MUST set the field to `null` (or omit it) when no artifact_dir has been set. |
| `claudechic/app.py` `_activate_workflow` | Does NOT compute or pass `artifact_dir`. The engine is constructed without one; `set_artifact_dir` is called later by the workflow's coordinator agent via the MCP tool. |

### 5.2 MCP tools — `set_artifact_dir` and `get_artifact_dir`

Add two new MCP tools to the in-process `chic` server (`claudechic/mcp.py`):

**`set_artifact_dir(path: str) -> str`**
- Calls `engine.set_artifact_dir(path)` on the active workflow engine and returns the resolved absolute path string. Engine errors (invalid path, `.claude/` rejection, path conflict on different-path re-call) propagate to the MCP tool surface.
- Permission gate: when no workflow is active (`self._workflow_engine is None`), the tool returns a clear error: `"No active workflow. set_artifact_dir requires an active workflow run."`
- Invocation pattern: the workflow's coordinator agent calls this exactly once per workflow run during the phase that decides the project identity (typically the Setup phase). On resume, the engine reads `artifact_dir` from saved chicsession state; the coordinator does NOT need to re-call `set_artifact_dir` (idempotent re-call is permitted but redundant).

**`get_artifact_dir() -> str | None`**
- Calls `engine.get_artifact_dir()` on the active workflow engine and returns the resolved absolute path string if set, else `None` (transmitted as JSON null on the MCP wire).
- Permission gate: when no workflow is active, the tool returns the same "No active workflow" error as `set_artifact_dir`.
- Invocation pattern: any agent (coordinator or sub-agent) MAY call this during their turn to read the current setting. Useful for sub-agents that received a fresh prompt without the substitution baked in, agents that need to verify the path before writing, or coordinator turns after resume that need to confirm the path was set in a prior session.

### 5.3 Markdown placeholder substitution

In `claudechic/workflows/agent_folders.py:_assemble_agent_prompt`, substitute the literal token `${CLAUDECHIC_ARTIFACT_DIR}` in identity.md and per-phase markdown content. **Substitution value: `str(engine.artifact_dir)` if the engine has one set; empty string otherwise.** The source is the engine reference passed into the assembler, NOT `os.environ.get` (claudechic's own process env is not the source of truth).

Pure literal string-replace; no shell-style expansion (no `$VAR`, no `~`); no other tokens.

When the engine's `artifact_dir` is `None` at assembly time (e.g., assembling a phase that runs before `set_artifact_dir` is called — typical for Phase 1 Vision and the early-Phase-2 Setup before the call): the token is replaced with the empty string. A markdown line `Write to ${CLAUDECHIC_ARTIFACT_DIR}/spec.md` becomes `Write to /spec.md` — a deliberate, visible failure mode.

### 5.4 Project_team workflow update

The `project_team` workflow's Setup phase (post-restructure path: `claudechic/defaults/workflows/project_team/coordinator/setup.md`) MUST be updated. Step 4 currently reads:

> "Create state directory with STATUS.md and userprompt.md"

Replace with:

> "Call `set_artifact_dir(<absolute_path>)` MCP tool. Choose a path for the project state directory — common conventions are `<working_dir>/.project_team/<project_name>/` (preserves the existing `.project_team/` layout) or `<working_dir>/.claudechic/runs/<project_name>/` (under `.claudechic/`). The tool resolves the path, creates it, and binds it to this run. Then create STATUS.md and userprompt.md at the resolved path. Subsequent agents spawned in Phase 3 (Leadership) see the resolved path baked into their workflow markdown via `${CLAUDECHIC_ARTIFACT_DIR}` substitution; any agent MAY also call `get_artifact_dir()` to query the path at runtime."

The workflow does NOT mandate a fixed prefix; the coordinator picks. Paths inside any `.claude/` ancestor are rejected by the tool; everywhere else is permitted.

**Advance check.** The bundled `claudechic/defaults/workflows/project_team/project_team.yaml` Setup phase MUST declare an `advance_checks` entry that fails when `engine.artifact_dir is None` (i.e., when `set_artifact_dir` has not yet been called for this run). The check uses the existing `advance_checks` mechanism on `Phase` declarations and the existing custom-check protocol in `claudechic/checks/`; the implementer adds a small check class that reads `engine.artifact_dir` and returns failure when it is `None`. The user-facing failure message, surfaced in the TUI when the check blocks advance, is: *"Artifact directory not set — call `set_artifact_dir(...)` MCP tool before advancing."* The check name and YAML schema details are at the implementer's discretion; the binding requirement is the gate behavior.

### 5.5 Lifetime, GC, migration

- **Identity:** caller-supplied `path` argument to `set_artifact_dir`, validated (no empty string; no null bytes; no embedded newlines; not inside any `.claude/` ancestor). The coordinator agent supplies the path from workflow content (e.g., a project name derived from the user's vision, plus a chosen prefix).
- **Per-workflow-run scope.** One `set_artifact_dir` call per run. Re-calling with the same resolved path is idempotent (returns the same path). Re-calling with a different resolved path after one has been set raises `RuntimeError` — the artifact dir is bound for the lifetime of the run.
- **Resume.** On workflow resume, the engine reads `artifact_dir` from saved chicsession state automatically; the coordinator does NOT need to re-call `set_artifact_dir`, and the Setup-phase advance check passes immediately. Agents see the same substitution value as on the original run. If the saved path no longer exists on disk (user moved or deleted the directory between sessions), the engine logs a WARNING but keeps the path stored; the coordinator may either restore the directory at the saved path or — if mid-workflow path changes become permissible in a future iteration — call `set_artifact_dir(<new_path>)` (currently raises `RuntimeError` per §5.1's "different path" rule, so relocation requires either restoring the saved path or deactivating + restarting the run).
- **No GC.** Artifact directories are NEVER auto-deleted by claudechic. `_deactivate_workflow` MUST NOT delete or modify the dir. Closing the application or deactivating a workflow MUST NOT delete the artifact directory.
- **No migration.** Pre-existing `.project_team/<name>/` directories from prior workflow runs are NOT migrated by claudechic code. No startup warning, no notice, no log line is emitted when claudechic detects a `.project_team/` directory. Users who want to carry forward existing artifacts do so manually.

### 5.6 Path layout reference

The artifact directory absolute path is whatever the coordinator passes to `set_artifact_dir` (after resolution). Typical patterns include:

```
<working_dir>/.project_team/<project_name>/
<working_dir>/.claudechic/runs/<project_name>/
```

The artifact dir MAY be at any path the coordinator chooses, except inside any `.claude/` ancestor (rejected by validation). Resolution is via `(self._cwd / path).resolve()` for relative paths; absolute paths are used as-is after resolve.

### 5.7 Acceptance for Group E

- [ ] `WorkflowEngine.__init__` does NOT accept `artifact_dir`; `WorkflowEngine.artifact_dir` is a read-only property whose initial value is `None`.
- [ ] `WorkflowEngine.set_artifact_dir(path)` accepts a full path (absolute, or relative to the launched-repo root); validates (rejects empty, null bytes, embedded newlines, paths inside any `.claude/` ancestor — raises `ValueError`); creates the directory at the resolved absolute path via `mkdir(parents=True, exist_ok=True)`; stores the resolved path on the engine; returns the path.
- [ ] `set_artifact_dir(path)` is idempotent on re-call with the same resolved path; raises `RuntimeError` on re-call with a different resolved path after one has been set.
- [ ] `WorkflowEngine.get_artifact_dir()` returns the engine's `artifact_dir` (the resolved absolute `Path` if set, else `None`).
- [ ] MCP tool `set_artifact_dir(path)` is exposed on the `chic` MCP server; calls the engine method; propagates engine errors; returns a "No active workflow" error when `self._workflow_engine is None`.
- [ ] MCP tool `get_artifact_dir()` is exposed on the `chic` MCP server; returns the resolved path string if set, else `None`; returns the same "No active workflow" error when no engine is active.
- [ ] `_assemble_agent_prompt` substitutes `${CLAUDECHIC_ARTIFACT_DIR}` from `engine.artifact_dir` (the resolved absolute path string when set, empty string when unset). The token is a markdown substitution marker only; claudechic does NOT inject any process env var of the same name into spawned-agent environments.
- [ ] `engine.to_session_state()` includes `artifact_dir` (the resolved absolute path string) when set; field is `null` or absent when no artifact_dir has been set.
- [ ] `engine.from_session_state(...)` reads `artifact_dir` from saved state and applies it via the same validation pipeline as `set_artifact_dir`. Invalid saved paths (e.g., `.claude/`-ancestor, null bytes) raise on construction; missing-on-disk saved paths log WARNING and keep the path stored on the engine.
- [ ] Calling `set_artifact_dir(...)` triggers `engine.persist_fn` before returning, so the chicsession file on disk reflects the new artifact_dir before the next caller-visible event.
- [ ] Resume of a chicsession that previously had `artifact_dir` set yields an engine with `artifact_dir` populated automatically (no coordinator re-call required); the Setup-phase advance check passes immediately.
- [ ] The `project_team` workflow's Setup phase calls `set_artifact_dir(<absolute_path>)` before writing STATUS.md and userprompt.md; the workflow markdown does NOT mandate a fixed prefix.
- [ ] The bundled `project_team` workflow's Setup phase has an advance check that fails when `engine.artifact_dir is None`. The check description (user-facing, surfaced in the TUI when the check blocks advance) reads: *"Artifact directory not set — call `set_artifact_dir(...)` MCP tool before advancing."*
- [ ] Grep test: no markdown file under `claudechic/defaults/workflows/**/*.md` contains a literal `\.claudechic/runs/<specific_name>/` or `\.project_team/<specific_name>/` path — workflow markdown uses the `${CLAUDECHIC_ARTIFACT_DIR}` token for path references; convention examples for prefixes (e.g., `<working_dir>/.project_team/<project_name>/`) are permitted as guidance text in the Setup phase doc only.
- [ ] No code path in `_deactivate_workflow` (or anywhere else) deletes or modifies the artifact directory.

---

## 6. Group F — Cherry-picks from `abast/main`

Pull five small fixes from the abast fork into claudechic. After this group lands, the cherry-picked behavior is in the codebase: docs clarification on `spawn_agent type=`, a workflow-path resolution fix, full model ID validation, `auto` permission-mode default on fresh install, and `auto` in the Shift+Tab cycle. Success: `git log` shows the five Pull commits and none of the Skip commits; deleting `~/.claudechic/config.yaml` and starting claudechic lands the user in `auto` permission mode by default.

Cherry-pick proposals MUST be tested against the actual post-restructure tree before being added to §6.1; transitive dependencies on abast commits not in the Pull set may not be visible from file-level diff analysis alone.

### 6.1 Cherry-pick set (binding)

| Commit | Decision | Notes |
|---|---|---|
| `9fed0f3` | **Pull** | Docs clarification on `spawn_agent type=` parameter |
| `8e46bca` | **Pull** | Fix: use resolved `workflows_dir` instead of hardcoded path. Land after Group A so it lands on post-restructure paths |
| `f9c9418` | **Pull** | Full model ID + loosened validation |
| `5700ef5` | **Pull** | Default to `auto` permission mode on startup |
| `7e30a53` | **Pull** | Add `auto` to Shift+Tab cycle. Bundled with `5700ef5` |
| `d55d8c0` | **SKIP** | Dropped; fallback discovery reimplemented in Group C |
| `26ce198` (`/fast`) | **SKIP** | Deferred to sprustonlab/claudechic#25 |
| `0ad343b` (anthropic 0.79.0 pin) | **SKIP** | Only needed for `/fast` |
| `claudechic/fast_mode_settings.json` | **SKIP** | Bundled with `/fast` |

### 6.2 Acceptance for Group F

- [ ] All five Pull commits cherry-picked and committed.
- [ ] `git log` shows none of the Skip commits.
- [ ] After `5700ef5` lands, fresh-install user gets `default_permission_mode: auto` (verified by deleting `~/.claudechic/config.yaml` and starting claudechic).
- [ ] Shift+Tab cycle includes `auto`.

---

## 7. Group G — Build settings UI (settings screen + workflow-picker level badges + auto-mode label)

Give users an in-app surface for editing claudechic configuration without hand-editing YAML files. After this group lands, the user reaches a `Settings` screen via three entry points (footer button, `/settings` command, welcome-screen action); each row edits live to the appropriate config file (`~/.claudechic/config.yaml` for user keys, `<repo>/.claudechic/config.yaml` for project keys); the workflow picker shows level badges per workflow plus a secondary line for overridden ids; auto-mode labels distinguish the three permission-mode flavors. Success: a user toggles `vi-mode` and the next keystroke uses vi bindings; a user disables a workflow via the multi-select sub-screen and the picker no longer offers it.

### 7.1 In-scope surfaces

| # | Surface | Source | File |
|---|---|---|---|
| 1 | `SettingsScreen` | #23 | `claudechic/screens/settings.py` (new) |
| 2 | `SettingsLabel` footer button | #24 | `claudechic/widgets/layout/footer.py` (append) |
| 3 | `/settings` slash command | #23 | `claudechic/commands.py` (extend `COMMANDS` + `handle_command`) |
| 4 | Welcome-screen Settings access | #23 + #21 | `claudechic/screens/welcome.py` (extend) |
| 5 | `DisabledWorkflowsScreen` subscreen | #23 | `claudechic/screens/disabled_workflows.py` (new) |
| 6 | `DisabledIdsScreen` subscreen | #23 | `claudechic/screens/disabled_ids.py` (new) |
| 7 | Workflow-picker level badges | #24 | `claudechic/screens/workflow_picker.py` (extend) |
| 8 | Auto-mode footer label updates | UX consistency | `claudechic/widgets/layout/footer.py:200` (extend `watch_permission_mode`) |
| 9 | `docs/configuration.md` content | #23 | `docs/configuration.md` (new; §8 below) |

The settings button (surface 2), the `/settings` command (surface 3), and the welcome-screen entry (surface 4) all invoke the same `_handle_settings()` method on `ChatApp` — that's the parity contract.

### 7.2 Settings screen layout and behavior

The screen is a single `Screen[None]` with two header sections (one per tier) plus a "Reference" footer row. Layout:

```
┌──────────────────────────────────────────────────────┐
│ Settings                                             │
│ Edit your claudechic settings. Changes save live.    │
│ ╭ search: [                                       ] ╮ │
│                                                      │
│ ━━ User settings (~/.claudechic/config.yaml) ━━      │
│   Default permission mode    auto         [user]     │
│   Theme                      textual-dark [user]     │
│   ... other user keys ...                            │
│                                                      │
│ ━━ Project settings (./.claudechic/config.yaml) ━━   │
│   Guardrails                 on           [project]  │
│   Disabled workflows         (3 disabled) ▸ [project]│
│   Disabled IDs               (5 disabled) ▸ [project]│
│   ... other project keys ...                         │
│                                                      │
│ ━━ Reference ━━                                      │
│   Open docs/configuration.md (full reference)        │
│                                                      │
│ esc close · / search · enter edit · r reset to default│
└──────────────────────────────────────────────────────┘
```

Each row carries: a label, the current value, and a level badge (`[user]` / `[project]`). Search filters case-insensitively against label and key name; headers always remain visible.

### 7.3 Per-key editor types

Each row has an editor type that determines the edit flow:

- **enum**: Enter mounts a `SelectionPrompt` inline below the row; current value highlighted; selection saves and re-renders.
- **bool**: Enter (or Space) toggles in place; row re-renders.
- **int**: Enter mounts a `QuestionPrompt` inline with the current value pre-filled and a range placeholder; invalid input fails with `notify("must be integer N–M", severity="error")` and the prompt stays.
- **text**: Enter mounts a `QuestionPrompt`; empty submit (for nullable keys) saves `None`. `worktree.path_template` shows three preset chips.
- **subscreen**: Enter pushes a sub-screen; on dismiss with non-`None` result, save the new value.

### 7.4 Settings screen key list

User-tier keys (10):

| Key | Editor type | Choices / validator |
|---|---|---|
| `default_permission_mode` | enum | `default` / `acceptEdits` / `plan` / `auto` / `bypassPermissions` |
| `themes` | subscreen | Push existing `/theme` flow (reuse search-and-pick) |
| `vi-mode` | bool | toggle |
| `show_message_metadata` | bool | toggle |
| `recent-tools-expanded` | int | range `[0, 20]` |
| `worktree.path_template` | text | template string or `<default>`; presets: `<default>`, `$HOME/code/worktrees/${repo_name}/${branch_name}`, `$HOME/worktrees/${repo_name}-${branch_name}` |
| `analytics.enabled` | bool | toggle |
| `logging.file` | text | path string, or empty for `None` (disable) |
| `logging.notify-level` | enum | `debug` / `info` / `warning` / `error` / `none` |
| `awareness.install` | bool | toggle (gates the install routine that copies bundled `claudechic/context/*.md` into `~/.claude/rules/claudechic_*.md` on every claudechic startup) |

**`awareness.install`** has special user-facing wording. Label: **"Install claudechic-awareness"**. Helper text:

*"Auto-install claudechic-awareness docs into `~/.claude/rules/` on every claudechic startup. **Disabling stops new installs but does not remove already-installed files** — manage `~/.claude/rules/claudechic_*.md` yourself when off (e.g., `rm ~/.claude/rules/claudechic_*.md` to remove all claudechic-installed docs)."*

The three semantic claims the helper text MUST convey: (1) auto-install on startup is the default behavior; (2) disabling stops the install routine but does NOT unlink existing files; (3) the user-owned action to actually remove influence is `rm` of the prefixed namespace. claudechic does NOT auto-remove on toggle transition `True → False` and does NOT prompt the user.

Project-tier keys (4):

| Key | Editor type | Choices / validator |
|---|---|---|
| `guardrails` | bool | toggle |
| `hints` | bool | toggle |
| `disabled_workflows` | subscreen | `DisabledWorkflowsScreen` (§7.6) |
| `disabled_ids` | subscreen | `DisabledIdsScreen` (§7.7) |

Hidden (documented in `docs/configuration.md` only): `analytics.id`, `experimental.*`.

### 7.5 Save semantics

Edits save **live**, on each edit. There is no "Save" / "Cancel" button. `esc` closes the screen unconditionally.

| Tier | Save call |
|---|---|
| user | Mutate `claudechic.config.CONFIG[key]`; call `claudechic.config.save()` (writes `~/.claudechic/config.yaml`). |
| project | Build a new frozen `ProjectConfig` from current values + the edit; call `ProjectConfig.save(self, project_dir)` (a new helper symmetric with `load`, writes `<repo>/.claudechic/config.yaml`). |

Each key has a live re-application path that runs after the save:

| Key | Re-apply on edit |
|---|---|
| `default_permission_mode` | `app.agent_mgr.set_global_permission_mode(value)`; footer reactive updates via `watch_permission_mode`. |
| `themes` | Existing `/theme` flow handles re-application. |
| `vi-mode` | Toggle `app.vi_mode_enabled`; footer updates via `update_vi_mode`. |
| `show_message_metadata` | Set `app.show_message_metadata`; existing reactives redraw. |
| `recent-tools-expanded` | Set in `CONFIG`; takes effect on next tool render. |
| `worktree.path_template` | Set in `CONFIG`; takes effect on next `/worktree`. |
| `analytics.enabled` | Reuse `_handle_analytics(app, "/analytics opt-in" / "opt-out")`. |
| `logging.*` | Set in `CONFIG`; call `errors.setup_logging()` to re-init handlers. |
| `awareness.install` | Set in `CONFIG`; toggle gates the next startup's install routine; no immediate file I/O on toggle (per §4.3). |
| `guardrails` | Set in `app.project_config.guardrails`; `app.agent_mgr.refresh_guardrails()` (Implementer adds — restart hooks). |
| `hints` | Set in `app.project_config.hints`; `app._refresh_hints()` (Implementer adds — thin wrapper around the hints-engine refresh path; no `hints_engine` attribute exists on `ChatApp` directly). |
| `disabled_workflows` | Set in `app.project_config`; `app._discover_workflows()` (existing method that re-walks the tier roots and rebuilds the workflow registry). |
| `disabled_ids` | Set in `app.project_config`; `app._refresh_hints()` and `app.guardrails.refresh()`. |

If a re-apply call raises, the save **still persists** (file write succeeded); emit `notify("Saved, but live re-apply failed: <err>", severity="warning")`.

A "Reset to defaults" row at the bottom of each tier section opens a confirm prompt (`"Reset N settings to defaults? This cannot be undone."`); on Yes, clear the keys (delete user-tier entries from `CONFIG`; replace project-tier `ProjectConfig` with a default-constructed instance) and save.

### 7.6 `DisabledWorkflowsScreen` subscreen

A multi-select sub-screen (`Screen[frozenset[str] | None]`) at `claudechic/screens/disabled_workflows.py`. The picker shows **one row per `(tier, workflow_id)` tuple** — a workflow defined at multiple tiers gets one row per tier, each independently toggleable. Layout:

```
[x] project_team             [pkg]   coordinator · 5 phases
[ ] project_team             [user]  coordinator · 5 phases  (override of pkg)
[ ] tutorial_extending       [pkg]   learner · 3 phases
[x] my_custom_flow           [user]  author · 2 phases
[ ] team_specific            [proj]  coordinator · 4 phases
```

Space toggles disable on the highlighted `(tier, id)` row. Enter accepts (dismisses with the new disabled set, encoded per §3.6 schema). Esc cancels (dismisses with `None`).

**Save encoding.** Each toggle maps to one entry in `disabled_workflows`:
- A row toggled disabled writes `<tier>:<workflow_id>` (tier-targeted).
- If the user disables every tier-instance of the same workflow id, the picker MAY collapse those entries into a single bare `<workflow_id>` (optimization; semantically equivalent).
- Re-enabling a row removes the matching entry from `disabled_workflows` (whether it was stored as bare or tier-targeted; if stored as bare, the bare entry is removed and the not-disabled tiers are re-enabled all at once).

Rows whose tier is not the winning tier (i.e., the id has a higher-priority override) are still shown; they appear with a "(override of <lower>)" or "(overridden by <higher>)" annotation so the user sees what disabling will affect.

### 7.7 `DisabledIdsScreen` subscreen

`disabled_ids` covers hint ids AND guardrail rule ids (the existing `claudechic/global/hints.yaml` + `claudechic/global/rules.yaml` namespacing; item id format `namespace:bare_id`). The disable-list entry format is the same `<tier>:<id>` / bare `<id>` shape from §3.6 — when the user disables `lab/onboarding-rule` at user tier, the saved entry is `user:lab/onboarding-rule`.

A multi-select sub-screen at `claudechic/screens/disabled_ids.py` with two grouped sections; each section shows **one row per `(tier, id)` tuple**:

```
━━ Hints ━━
[x] global:context-docs-outdated     [pkg]
[ ] global:permission-mode-tip       [pkg]
[ ] my_workflow:setup-reminder       [proj]
[ ] lab/onboarding-rule              [user]  (override of pkg)
[ ] lab/onboarding-rule              [pkg]

━━ Guardrail rules ━━
[ ] global:no-rm-rf            deny  [pkg]  Block destructive rm
[x] global:warn-on-curl-pipe   warn  [pkg]  Warn on curl|sh
[ ] my_project:protect-prod    deny  [proj] Block prod paths
```

Same Space/Enter/Esc behavior as §7.6. Same save encoding: tier-targeted by default; collapses to bare when all tier-instances of an id are disabled.

Category headers (`Hints` / `Guardrail rules`) disambiguate the type within `disabled_ids`.

Both subscreens read from the post-resolve `workflow_provenance` and `item_provenance` maps (per §3.5) to enumerate every `(tier, id)` tuple for display.

### 7.8 Settings button + `/settings` command + welcome-screen access

**Footer button** (`SettingsLabel`): mirrors the existing `DiagnosticsLabel` and `ComputerInfoLabel` pattern. Posts a `Requested` message on click. Placed in `StatusFooter.compose()` adjacent to `ComputerInfoLabel`. Lowercase label text `settings` (matches sibling labels: `sys`, `session_info`).

**`/settings` slash command**: add `("/settings", "Open settings", [])` to the `COMMANDS` list in `claudechic/commands.py` (alphabetical between `/resume` and `/shell`); add a dispatch in `handle_command()` that calls `app._handle_settings()`.

**Welcome-screen access**: add `RESULT_SETTINGS = "settings"` constant in `claudechic/screens/welcome.py`; add an `_ActionItem(RESULT_SETTINGS, "▸ Settings (/settings)")` immediately before the "Dismiss permanently" row; in the welcome dismiss handler at `claudechic/app.py:1139` add a branch that calls `self._handle_settings()` on the `RESULT_SETTINGS` result.

All three call:

```python
def _handle_settings(self) -> None:
    from claudechic.screens.settings import SettingsScreen
    self.push_screen(SettingsScreen())
```

The single method is the parity contract.

### 7.9 Workflow picker — level badges and override visibility

The workflow registry (currently `dict[str, Path]`) becomes `dict[str, WorkflowSource]` where `WorkflowSource` carries `path: Path` and `tier: Literal["package","user","project"]`. The full per-id origin list lives separately (`_workflow_origins: dict[str, list[WorkflowSource]]`); the picker uses it to show "(also at: ...)" lines for overridden workflows.

`WorkflowItem` (in `claudechic/screens/workflow_picker.py`) gains:

```
project_team   role: coordinator · 5 phases · active   [proj]
                                                          (also at: pkg)
```

Level badges: `[pkg]`, `[user]`, `[proj]`. Color mapping: package = muted (lowest priority), user = secondary blue, project = primary orange (highest priority).

Sort order: project first, then user, then package; alphabetical within tier.

A row whose workflow has overrides at lower levels shows a secondary "(also at: <levels>)" line so users can see which copies the picker is shadowing.

### 7.10 Auto permission-mode UI

After cherry-picks `5700ef5` and `7e30a53` land (per §6), the runtime supports `auto`. Three UI sites need updating:

- **Footer label** (`watch_permission_mode` in `claudechic/widgets/layout/footer.py:200`): add an `elif value == "auto":` branch with label text `"Auto: safe tools auto-approved"` (must be visibly distinct from `acceptEdits` "Auto-edit: on" and `bypassPermissions` "Bypass: all auto-approved"). Set `active` class true; set `plan-mode` and `plan-swarm-mode` classes false.
- **Permission-mode display dict** in `claudechic/app.py:610ff`: include `"auto": "Auto"`.
- **Settings-screen enum** (§7.4): `default_permission_mode` enum already lists all five modes including `auto`.

A fresh-install user gets `default_permission_mode: auto` (this is `5700ef5`'s contract; the settings UI displays whatever value is in `CONFIG`).

### 7.11 User-facing wording (binding)

- User-facing UI labels use **"level"** for the 3-level distinction; "tier" is reserved for spec/code.
- Level badges in workflow picker: `[pkg]`, `[user]`, `[proj]`.
- Workflow row with override: `<workflow_id> (defined at: <levels>)`.
- Disable-control label: **"Disabled workflows"** (NOT "Workflow disable list" / "ID blacklist").
- Disable-control tooltip: *"Disabling a workflow by ID hides it from this project regardless of which level (package / user / project) defines it."* (verbatim).
- The mechanism in §4 is referenced in user-facing prose as **"claudechic-awareness install"**.
- Loader partial-override error wording is verbatim per §3.4.

The reference doc (§8) is titled `# Configuration reference` — the technical word; the screen is "Settings" — the user-facing word.

### 7.12 Key bindings

| Binding | Where | Action |
|---|---|---|
| `escape` | `SettingsScreen` | dismiss(None) |
| `escape` | `DisabledWorkflowsScreen`, `DisabledIdsScreen` | dismiss(None) — no save |
| `enter` | row | open editor for that key |
| `space` | row (bool keys; subscreen rows) | toggle in place / toggle disable |
| `enter` | subscreen | accept current selection (dismiss(frozenset)) |
| `/` | `SettingsScreen` | focus search input |
| `r` | `SettingsScreen` | jump to next "Reset" row |

The settings UI does NOT introduce any priority binding that would override existing app bindings.

### 7.13 Acceptance for Group G

- [ ] All nine surfaces from §7.1 implemented.
- [ ] All wording obligations from §7.11 satisfied.
- [ ] `_handle_settings()` is called from all three entry points (footer button, `/settings`, welcome screen) — single method satisfies parity.
- [ ] User-facing labels use "level" (not "tier") wherever the 3-level distinction surfaces.
- [ ] `DisabledWorkflowsScreen` and `DisabledIdsScreen` show one row per `(tier, id)` tuple (per §7.6, §7.7); save encoding writes `<tier>:<id>` for tier-targeted disable and bare `<id>` only when every tier-instance is disabled.
- [ ] Auto-mode footer label distinguishes `auto` from `acceptEdits` and `bypassPermissions`.
- [ ] Settings save path writes only to `.claudechic/` paths (per the §9 boundary rule).
- [ ] Saving with a failing live-re-apply path: file write persists, `notify(..., severity="warning")` emitted.
- [ ] Workflow picker sorts by level (project > user > package), shows level badge per row, and shows "(also at: ...)" when the workflow id is defined at lower levels.

---

## 8. Author configuration reference (`docs/configuration.md`)

Give users a single ground-truth reference for every config key, environment variable, and CLI flag claudechic exposes. After this group lands, `docs/configuration.md` exists as the canonical reference document; the in-app `/settings` UI cross-links to it for "show me everything"; users finding an undocumented key in their YAML can look up its description, type, default, and example here. Success: a reader landing on `docs/configuration.md` from any cross-reference can answer "what does this key do" and "what values does it accept" without reading source code.

### 8.1 File path

`docs/configuration.md` (new file).

### 8.2 Required sections

Six sections in order:

1. **Overview** (~100 words). Pointer to `/settings` UI; statement that config is 2-tier (user + project); pointer to `~/.claudechic/config.yaml` and `<launched_repo>/.claudechic/config.yaml`; note that defaults live in code (no package-tier config file).
2. **User-tier config keys.** One subsection per key. Required content per key: canonical key path, type and accepted values, default, one-paragraph description, example YAML, whether exposed in `/settings`. Document `analytics.id` and `experimental.*` even though hidden from UI.
3. **Project-tier config keys.** Same shape. Keys: `guardrails`, `hints`, `disabled_workflows`, `disabled_ids`. For `disabled_workflows` and `disabled_ids`: include exact format (list of strings; each string is either a bare id or `<tier>:<id>` per §3.6 + §0.2 vocabulary; for `disabled_ids` the item-id grammar is `namespace:bare_id`, so a tier-targeted disable looks like `<tier>:<namespace>:<bare_id>`, e.g., `user:lab/onboarding-rule`). Document: bare vs tier-prefixed semantics; warn-on-invalid-prefix (`package`/`user`/`project` only); union-across-config-tiers behavior (entries in user-config and project-config are additive).
4. **Environment variables.** Table with columns: variable, scope, default, description. Required entries: `CLAUDECHIC_REMOTE_PORT`, `CHIC_PROFILE`, `CHIC_SAMPLE_THRESHOLD`, `CLAUDE_AGENT_NAME`, `CLAUDE_AGENT_ROLE`, `CLAUDECHIC_APP_PID`, `ANTHROPIC_BASE_URL`. Implementer greps the codebase for any additional env vars not in this list and adds them.
5. **CLI flags.** Table with columns: flag, type, default, description. Enumerate from `claudechic/__main__.py` argparse setup.
6. **Cross-references.** Pointer to `vision.md` for the 3-tier content model; pointer to `/settings` screen; pointer to `docs/privacy.md` for analytics details.

### 8.3 Required additional section: claudechic-awareness install

A section titled **"claudechic-awareness install"** covering:

1. **Mechanism summary paragraph:** *"On every claudechic startup, the bundled context docs in `claudechic/context/*.md` are copied into `~/.claude/rules/claudechic_*.md` so the Claude Agent SDK loads them as Claude rules in every session (claudechic-spawned or not). The install is idempotent: files that already match are skipped (SKIP); files that differ are updated (UPDATE); new files are added (NEW); orphan `claudechic_*.md` files no longer in the bundled catalog are removed (DELETE). The `claudechic_` prefix prevents collision with user-authored rules in the same directory."*
2. **The toggle:** the `awareness.install` user-tier config key (default `True`) gates the install. When set to `False`, the install routine no-ops on startup — including no DELETE pass; existing installed `claudechic_*` files are NOT removed by claudechic. The toggle is "should claudechic maintain `~/.claude/rules/claudechic_*.md`" — NOT "is the agent's awareness disabled." **Disabling stops new installs but does NOT remove already-installed files.** To actually stop the agent from loading claudechic-awareness content, the user MUST manually `rm ~/.claude/rules/claudechic_*.md` after disabling the toggle.
3. **What gets installed:** the bundled context docs in `claudechic/context/` — `claudechic-overview.md`, `workflows-system.md`, `hints-system.md`, `guardrails-system.md`, `checks-system.md`, `manifest-yaml.md`, `multi-agent-architecture.md`, `CLAUDE.md`. Each is installed as `~/.claude/rules/claudechic_<name>.md` (with the `claudechic_` prefix). The Implementer SHOULD enumerate the actual bundled set when authoring this section (the catalog may grow).
4. **Manual re-install:** the `/onboarding` workflow's `context_docs` phase invokes the same install routine with `force=True`, providing an explicit user-driven trigger separate from the automatic startup install. Useful when `awareness.install` is disabled but the user wants a one-time refresh.
5. **Manual user edits to `claudechic_*` regular files are clobbered on next startup** (when `awareness.install` is `True`). claudechic owns the `claudechic_` prefix namespace inside `~/.claude/rules/`. To manage rules manually, three options: (a) disable `awareness.install`; (b) author files using any filename NOT matching `claudechic_*` (those are user-owned and not touched by claudechic); (c) replace a `claudechic_*.md` regular file with a symlink — claudechic's symlink guard (per §4.2) leaves any symlink at a `claudechic_*.md` path untouched (no NEW/UPDATE/SKIP/DELETE applies; a WARNING is logged once per startup per such file).
6. **Removing claudechic-awareness install:** if the user wants to fully remove claudechic's influence on `~/.claude/rules/`: (i) set `awareness.install: false` in `~/.claudechic/config.yaml` (stops future installs and DELETE pass); (ii) `rm ~/.claude/rules/claudechic_*.md` (removes already-installed files). Step (i) without step (ii) leaves stale files loading in every session; step (ii) without step (i) is a one-shot — the next claudechic startup re-installs.
7. **Orphan cleanup is automatic when toggle is on:** when claudechic ships a smaller bundle or renames a context doc across versions, the next startup's DELETE pass automatically removes orphan `claudechic_*.md` files no longer in the bundled catalog. Users do NOT need to manually clean up after upgrades. (Users who want manual cleanup must disable the toggle first; otherwise the install routine reverses their cleanup on next startup.)
8. **No drift hint:** the install is idempotent on every claudechic startup, so when `awareness.install` is `True` the installed copies stay in sync with the bundled versions automatically — both forward-drift (bundle newer than installed) AND orphan-drift (installed file dropped from bundle) are repaired silently. No user action required, no hint fires. (Users who disable `awareness.install` manage `~/.claude/rules/claudechic_*.md` themselves; if they want a refresh, `/onboarding` is the manual trigger and runs `install_awareness_rules(force=True)`.)

### 8.4 Required additional section: overriding workflows

A section titled **"Overriding workflows"** with subsection **"Why partial overrides are not supported"**, covering:

- Example: *"To override a workflow at user or project level, copy all files of the workflow into your level's `workflows/<id>/` directory. Partial overrides (some files in your level, others in the lower level) are not supported and will surface as a loader error."*
- Brief explanation: a higher-tier directory missing files the lower-tier defines is a partial override; the loader rejects it with a `LoadError(section="workflow")` and falls through to the next-lower complete tier.

### 8.5 Title

The page's title is `# Configuration reference`. Suggested opening: *"Use the `/settings` screen for interactive editing; this page is the ground-truth reference for every config key, environment variable, and CLI flag."*

### 8.6 Wording obligations

- MUST NOT use "convergence", "converge", "merge program", "fork merge", "alignment program".
- MUST NOT use the word "rules" unqualified to describe the claudechic-awareness install content. When the install target dir or filename is named, write `~/.claude/rules/claudechic_*.md` (path-quoted) — that's a path, not a content category. Bare "rules" describing the bundled context docs is forbidden.
- User-facing text uses **"level"** (not "tier") when describing the 3-level distinction.

### 8.7 Acceptance for §8

- [ ] `docs/configuration.md` exists.
- [ ] All six core sections present.
- [ ] claudechic-awareness install section present per §8.3.
- [ ] Overriding-workflows section present per §8.4.
- [ ] Title is `# Configuration reference`.
- [ ] Zero occurrences of forbidden words from §8.6.
- [ ] `docs/privacy.md:36` reference rewrite (per §2.6) preserved.

---

## 9. Boundary rule

Claudechic writes its state under `.claudechic/` directories: user-tier at `~/.claudechic/` and project-tier at `<repo>/.claudechic/`. It does NOT write inside `.claude/`, with three explicit exceptions:

1. The existing `.claude` worktree symlink at `<worktree>/.claude → <main_wt>/.claude` (preserved at `claudechic/features/worktree/git.py:293-301`).
2. The new `.claudechic` worktree symlink at `<worktree>/.claudechic → <main_wt>/.claudechic` (added at the same site per §10).
3. The awareness install routine writing markdown files matching `~/.claude/rules/claudechic_<name>.md` (per Group D §4); the routine MUST NOT write or unlink any path in `~/.claude/rules/` whose basename does not start with `claudechic_`.

Claude-owned settings and content under `.claude/` MUST NOT be overwritten by claudechic. The protected names (which claudechic MUST NEVER open in write/append/r+ modes) include: `settings.json`, `settings.local.json`, `.credentials.json`, `history.jsonl`, `plugins/installed_plugins.json`, `projects/**/*.jsonl`, `plans/**`, `commands/**`, `skills/**`, `hooks/**`, `guardrails/**`, `agents/**`, and any file under `rules/` whose basename does not start with `claudechic_`. Claudechic also MUST NOT create symbolic links *inside* any `.claude/` directory (a symlink AT the `.claude/` directory entry, as in the worktree pattern, is permitted; a symlink BELOW a `.claude/` ancestor is forbidden).

Reading from any `.claude/` path is unrestricted.

No automated boundary test ships with this run. The rule is enforced by code review and by the design constraints encoded in Group B (§2 boundary relocation), Group D (§4 awareness install symlink guard + prefix predicate), and the worktree symlinks (§10).

---

## 10. Add worktree symlink

Make claudechic's project-tier state visible across all worktrees of a repo. After this group lands, `git worktree add` creates a `.claudechic` symlink at the new worktree's root (alongside the existing `.claude` symlink) pointing back to the main worktree's `.claudechic/` directory; workflow runs, hint state, and project config are shared across feature branches without manual copying. Success: a chicsession started in worktree A is visible in worktree B without intervention. Watch for: Windows users have no working symlink path; the symlink will fail to create and worktree creation falls back to no-state-propagation (cross-platform tracking at GitHub issue #26 — surface if a user reports state-loss on Windows).

### 10.1 Decision

A parallel `.claudechic/` symlink MUST be added at `claudechic/features/worktree/git.py:293-301`, mirroring the existing `.claude/` symlink pattern at the same site. The new symlink propagates project-tier `<launched_repo>/.claudechic/` content from the **main worktree** (the originally-cloned working tree, identified at runtime by `main_wt_info[0]`; see `terminology_glossary.md` §7.2) to each new worktree (a sibling working tree created via `git worktree add`).

**Windows portability:** the symlink requires POSIX support; cross-platform worktree state propagation is tracked at https://github.com/sprustonlab/claudechic/issues/26.

### 10.2 Code edits

| File | Edit |
|---|---|
| `claudechic/features/worktree/git.py:293-301` | Extend the existing symlink-creation block to also create a `.claudechic` symlink alongside the existing `.claude` one. Apply identical pattern: `is_dir()` guard on the source; create only if target does not already exist; symlink target = `<main_wt>/.claudechic/` resolved to absolute. |

Concrete shape (illustrative; Implementer adapts to surrounding code style):

Both the existing `.claude` block AND the new `.claudechic` block MUST use a try/except `FileExistsError` pattern (NOT a check-then-create `if not target.exists()` pattern). The existing `.claude` block at `git.py:299-301` MUST be migrated to the same pattern as part of this edit.

```python
# Existing block (migrated to race-safe form by this edit):
source_claude_dir = main_wt_info[0] / ".claude"
if source_claude_dir.is_dir():
    target = worktree_dir / ".claude"
    try:
        target.symlink_to(source_claude_dir.resolve())
    except FileExistsError:
        pass

# New parallel block (added immediately after):
source_claudechic_dir = main_wt_info[0] / ".claudechic"
if source_claudechic_dir.is_dir():
    target = worktree_dir / ".claudechic"
    try:
        target.symlink_to(source_claudechic_dir.resolve())
    except FileExistsError:
        pass
```

The new symlink lives at `<worktree_dir>/.claudechic` (the directory entry of the worktree, NOT a file inside `.claude/` or any other restricted location). It does not target `.claude/`; the symlink lives at the worktree directory entry (parent is the worktree root), so it is one of the three explicit boundary-rule exceptions (§9).

### 10.3 Acceptance

- [ ] After `git worktree add <new>`, if `<main_wt>/.claudechic/` exists, the new worktree contains a `.claudechic` symlink whose `readlink` resolves to the main worktree's `.claudechic/` directory (INV-10).
- [ ] If `<main_wt>/.claudechic/` does not exist (e.g., very fresh repo with no claudechic state yet), the symlink is NOT created (existing `is_dir()` guard pattern). Worktree creation succeeds.
- [ ] `git worktree remove` cleans the symlink as part of removing the worktree directory (no special handling required; the symlink lives inside the worktree dir).
- [ ] The new symlink is one of the three explicit `.claude/`-area exceptions allowed by the §9 boundary rule.


## 11. Verify SDK loader

### 11.1 Verification

The mechanism's runtime correctness is verified by **INV-AW-SDK-1** (§12.2.3) — a sentinel-content end-to-end test that writes a deterministic test sentinel into a tmp-`HOME`'s `~/.claude/rules/`, spawns a real Claude Agent SDK client with `setting_sources=["user","project","local"]`, and asserts the sentinel string appears in the agent's response when the agent is asked to repeat its system context. The test runs under the `live-sdk` opt-in marker (not the default pytest run) because it requires the actual SDK + Claude Code CLI subprocess; CI invokes it on a separate gate. If the test fails, the failure message points the maintainer at this section (§11.1) and at the test file's docstring describing the verification step.

### 11.2 Acceptance

- [ ] No code path under `claudechic/context_delivery/` exists (the directory is not created).
- [ ] No `SessionStart` hook is registered for awareness purposes (the existing `PostCompact` hook for phase-prompt delivery remains; that's the only pre-existing hook usage carried forward).
- [ ] No `PreToolUse` matcher targeting `.claudechic/` paths exists.
- [ ] INV-AW-SDK-1 (§12.2.3) test file exists at `tests/test_awareness_sdk_e2e.py`; runs under the `live-sdk` opt-in marker (`pytest -m live_sdk`); failure message references this section §11.1 and §12.2.3.

---

## 12. Consolidated test invariants

All test invariants the implementation MUST satisfy.

### 12.1 Override-resolution invariants

| ID | Test |
|---|---|
| INV-1 | User-tier workflow `foo` overrides package-tier `foo` (project absent); `LoadResult.workflows["foo"].tier == "user"` |
| INV-2 | Project-tier `foo` overrides user-tier and package-tier `foo`; `tier == "project"` |
| INV-3 | `TierRoots(package=p, user=None, project=None)` — system loads package-only content; no errors |
| INV-4 | Same rule id at user and project — exactly one `Rule` in `LoadResult.rules`, `tier == "project"` |
| INV-5 | Two rules with the same id in one tier's `rules.yaml` — one survives + one `LoadError(source="validation")` |
| INV-8 | Hint id at multiple tiers produces one `HintDecl`; lifecycle key in `HintStateStore` is identical (lifecycle survives override) |
| INV-PO-1 | Higher-tier directory missing files relative to lower-tier — effective workflow falls through to lower; `LoadError(section="workflow")` surfaces |
| INV-PO-2 | User has partial; project has full — project wins; partial-override `LoadError` still surfaces; project workflow unaffected |
| INV-PO-3 | Higher tier has every lower-tier file plus extras — higher wins; no partial-override error |

### 12.2 Awareness invariants

#### 12.2.1 Install routine

| ID | Test |
|---|---|
| INV-AW-1 | When `awareness.install` is `True`, `install_awareness_rules()` runs on app startup AND copies every `claudechic/context/<name>.md` to `~/.claude/rules/claudechic_<name>.md` (NEW), creating `~/.claude/rules/` if absent. The mkdir of `~/.claude/rules/` is idempotent (`parents=True, exist_ok=True`); no subdirectories are created. |
| INV-AW-2 | When `awareness.install` is `False`, `install_awareness_rules()` returns immediately with `skipped_disabled=True`; no file I/O occurs — including no DELETE pass (verifiable via `unittest.mock.patch` on `Path.write_text` / `Path.mkdir` / `Path.unlink`) |
| INV-AW-3 | Every regular-file write by the install routine has a basename matching `claudechic_*.md`; no other filename is created. The only directory the routine creates is `~/.claude/rules` itself; the routine creates no subdirectories under it. The §9 boundary rule's claudechic-prefixed exception covers both kinds of write |
| INV-AW-4 | Idempotency — running `install_awareness_rules()` twice in a row produces `InstallResult` with `new=[]`, `updated=[]`, `skipped=[<all bundled names>]`, `deleted=[]` on the second call (after first call NEW-installed everything; no orphans present) |
| INV-AW-5 | `from claudechic.hints.triggers import ContextDocsDrift` raises `ImportError`; `claudechic/defaults/global/hints.yaml` contains no hint with `id: context_docs_outdated` (per §4.5 deletion). |
| INV-AW-10 | Orphan DELETE pass — pre-create `~/.claude/rules/claudechic_obsolete.md` (basename matches `claudechic_*.md`; `obsolete` is NOT in the bundled catalog) and run `install_awareness_rules()`; assert the file is unlinked AND `result.deleted` contains `"obsolete"`. Symmetric: pre-create `~/.claude/rules/foo.md` (basename does NOT match prefix) and assert it is left untouched (DELETE pass is bounded to the claudechic-owned namespace by basename). Symmetric: pre-create `~/.claude/rules/subdir/claudechic_x.md` and assert it is left untouched (DELETE pass does not recurse). When `awareness.install=False`, the DELETE pass MUST NOT fire even if orphans exist. |
| INV-AW-11 | Symlink guard — pre-create `~/.claude/rules/claudechic_overview.md` as a symlink pointing at a regular file `~/notes/important.md` (or any path outside `~/.claude/rules/`) and run `install_awareness_rules()`; assert (a) the symlink at `~/.claude/rules/claudechic_overview.md` is unchanged (`is_symlink()` still True; `readlink` unchanged); (b) the link target file is unchanged byte-for-byte (no write through the symlink); (c) `result.new` / `result.updated` / `result.skipped` / `result.deleted` do NOT contain `"overview"`; (d) a WARNING was logged. The guard applies to both the per-bundled-file loop AND the DELETE pass (a symlink at `~/.claude/rules/claudechic_orphan.md` whose stem is NOT in the bundled catalog is also left untouched, not unlinked). |

#### 12.2.2 Phase-prompt delivery

| ID | Test |
|---|---|
| INV-AW-6 | On workflow activation, the engine sends the assembled phase prompt to the active agent via `_send_to_active_agent` (verifiable by mocking `_send_to_active_agent`); the kickoff message body IS the assembled phase prompt. No file I/O. |
| INV-AW-8 | On phase advance via the `advance_phase` MCP tool, the engine calls `assemble_phase_prompt(workflow_dir, role_name, current_phase)` for the new phase and sends the result via `_send_to_active_agent` (verifiable by mocking). No file I/O. |
| INV-AW-9 | The PostCompact hook signature is `create_post_compact_hook(engine, agent_role, workflows_dir)`; the closure resolves `workflow_dir = workflows_dir / engine.workflow_id` and calls `assemble_phase_prompt(workflow_dir, agent_role, engine.get_current_phase())`, returning `{"reason": prompt}` if non-empty, `{}` otherwise. No file I/O. |

#### 12.2.3 Live-SDK end-to-end verification

| ID | Test |
|---|---|
| INV-AW-SDK-1 | **Sentinel rule reaches a real Claude agent's system context.** Test fixture (a) creates a tmp `HOME` directory; (b) writes a deterministic sentinel file at `<tmp_home>/.claude/rules/claudechic_sdk_sentinel_v1.md` containing the verbatim string `[CLAUDECHIC_AWARENESS_SENTINEL_v1: SDK rules-loading verified 2026]` followed by a one-line marker paragraph (no YAML frontmatter); (c) spawns a real `ClaudeSDKClient` with `setting_sources=["user","project","local"]` and `env={"HOME": str(tmp_home), ...}`; (d) sends the agent a single prompt asking it to repeat any `claudechic_sdk_sentinel` text it sees in its instructions; (e) asserts the response contains the sentinel string `[CLAUDECHIC_AWARENESS_SENTINEL_v1: SDK rules-loading verified 2026]`. Failure message MUST be: `"INV-AW-SDK-1 failed: SDK did not load ~/.claude/rules/claudechic_*.md into agent context. See SPEC.md §11.1. The claudechic-awareness install mechanism depends on this loader behavior; if Anthropic's setting_sources semantics changed, escalate."` |

INV-AW-SDK-1 runs ONLY under the opt-in `live-sdk` pytest marker (`pytest -m live_sdk tests/test_awareness_sdk_e2e.py`); the default pytest collection skips it. CI MUST run the live-SDK gate on a separate scheduled job (e.g., nightly), not on every PR.

### 12.3 Artifact-dir invariants

| ID | Test |
|---|---|
| INV-10 | After `git worktree add <new>`, if `<main_wt>/.claudechic/` exists, the new worktree contains a `.claudechic` symlink whose `readlink` resolves to the source worktree's `.claudechic/` directory (per §10.3) |
| INV-12 | Workflow role markdown files contain zero hard-coded artifact-dir paths to specific projects; convention examples for prefixes are permitted only in the Setup phase doc; all path references use the `${CLAUDECHIC_ARTIFACT_DIR}` substitution token |
| I-3 | Markdown substitution: `engine.artifact_dir` is a `Path` → `${CLAUDECHIC_ARTIFACT_DIR}` token replaced with `str(path)`; `engine.artifact_dir` is `None` → token replaced with empty string. The token is a markdown substitution marker; not coupled to any process env var. |
| I-4 | Resume of a chicsession with `artifact_dir` set in saved state yields an engine where `engine.artifact_dir` returns the same resolved absolute path bytewise. No coordinator re-call required; the Setup-phase advance check passes immediately. |
| I-5 | `engine.set_artifact_dir(path)` creates the directory at the caller-supplied resolved absolute path and returns it; relative paths are resolved against `<launched_repo_root>` |
| I-6 | `engine.set_artifact_dir(path)` raises `RuntimeError` when called with a different resolved path after one has been set; same-resolved-path re-call is idempotent |
| I-7 | `engine.to_session_state()` includes `artifact_dir` (the resolved absolute path string) when set; field is `null` or absent when no artifact_dir has been set. `engine.from_session_state(...)` reads the field and applies it via the same validation as `set_artifact_dir`; tampered/invalid saved paths raise on construction; missing-on-disk saved paths log WARNING and keep the path stored. |
| I-8 | `engine.set_artifact_dir(path)` raises `ValueError` for: empty string; paths containing null bytes (`\x00`) or embedded newlines; paths that resolve inside any `.claude/` ancestor directory |
| I-9 | MCP tools `set_artifact_dir(path)` and `get_artifact_dir()` both return a "No active workflow" error when `self._workflow_engine is None`; `set_artifact_dir` returns the resolved path string on success; `get_artifact_dir` returns the resolved path string if set or `None` otherwise |
| I-10 | `engine.get_artifact_dir()` returns the same resolved absolute path that was last passed to (and accepted by) `set_artifact_dir`; returns `None` when no path has been set |
| I-11 | The bundled `project_team` workflow's Setup-phase advance check returns failure when `engine.artifact_dir is None`; returns success when `engine.artifact_dir is not None` (whether the value came from `set_artifact_dir` or from a resume load). The check fires at the engine's pre-advance evaluation pass; failure blocks the phase transition. |
| I-12 | `set_artifact_dir(...)` invocation triggers `engine.persist_fn` before returning; the chicsession file on disk reflects the new `artifact_dir` field before the next caller-visible event. |

### 12.4 Disable-filter invariants (per §3.6)

| ID | Test |
|---|---|
| INV-DF-1 | Bare-ID disable applies across all tiers — workflow at package tier disabled via `config.disabled_workflows = ["foo"]`; `foo` absent from the post-resolve workflows; rules/hints/checks whose `namespace == foo` also removed |
| INV-DF-2 | Unknown bare id in `disabled_workflows` warns (via `claudechic.errors.log`), does not raise; `LoadResult.errors` does NOT contain a related entry |
| INV-DF-3 | Unknown bare id in `disabled_ids` warns (symmetric to INV-DF-2), does not raise |
| INV-DF-4 | Tier-targeted disable filters only the named tier — workflow `foo` defined at package AND user; `config.disabled_workflows = ["user:foo"]`; the post-resolve `foo` resolves to the package version (`tier == "package"`); the user-tier record is treated as if it did not exist for resolution |
| INV-DF-5 | Tier-targeted disable produces fall-through to lower tier when one exists — symmetric for `disabled_ids`: rule `lab/onboarding-rule` defined at user AND package; `config.disabled_ids = ["user:lab/onboarding-rule"]`; the post-resolve rule resolves to the package version |
| INV-DF-6 | Invalid tier prefix warns and skips — `config.disabled_workflows = ["pkg:foo"]` (`pkg` is not a valid prefix; only `package`/`user`/`project`); a WARNING is logged; `foo` is NOT disabled at any tier (the entry does NOT fall back to bare-ID semantics); `LoadResult.errors` does NOT contain a related entry |
| INV-DF-7 | Union of user-config and project-config disable lists — user-config `disabled_workflows = ["foo"]` AND project-config `disabled_workflows = ["user:bar"]`; both entries take effect (`foo` removed everywhere; `bar` filtered at user tier only); symmetric for `disabled_ids` |

---

## 13. Acceptance gates (exit checklists)

The spec is verifiable when all three checklists pass. Each item resolves to `[OK]` or `[ESCALATE TO COORDINATOR]`. No items may be silently softened.

### 13.1 Verifiability checklist

- [ ] **Boundary rule:** §9 enumerates the boundary in narrative form; no separate allowlist file or registry is shipped.
- [ ] **Identity unit for each content category:** workflow→`workflow_id`, rule→`Rule.id`, injection→`Injection.id`, hint→`HintDecl.id`, check→`CheckDecl.id`, phase→`Phase.id`, mcp_tool→`tool.name` (per §3.2).
- [ ] **claudechic-awareness install routine location:** `claudechic/awareness_install.py` exposing `install_awareness_rules(force: bool = False) -> InstallResult` (per §4.1). No SessionStart hook; no PreToolUse hook for awareness; no per-session "fired" tracker.
- [ ] **Install-routine invocation site:** `claudechic/app.py` `on_mount` invokes the routine once during startup, gated by `awareness.install` config (per §4.4). Failure is logged WARNING; startup is not blocked.
- [ ] **Install target filename pattern:** `~/.claude/rules/claudechic_<name>.md` for each `claudechic/context/<name>.md`; cataloged set bounded by the bundled directory contents. The §9 boundary rule permits this prefix-namespace.
- [ ] **Existing `~/.claude/.claudechic.yaml` fate:** left in place; not migrated; no warning (per §2.1).
- [ ] **Worktree's main `.claudechic/` missing at worktree-add time:** symlink is NOT created (existing `is_dir()` guard pattern preserved); worktree creation succeeds; new worktree starts without `.claudechic/` until user creates content (per §10.2, §10.3).
- [ ] **Override-resolution test assertions:** enumerated in §12.1 (INV-1 through INV-PO-3).
- [ ] **Live-SDK end-to-end verification:** INV-AW-SDK-1 (§12.2.3) covers the SDK loader contract; failure escalates per the test's failure message.
- [ ] **`.claude/` writes:** the only permitted writes are the three exceptions enumerated in §9 (the two worktree symlinks and the awareness-install routine's `~/.claude/rules/claudechic_*.md` writes/unlinks plus the parent-dir mkdir of `~/.claude/rules`). Reads from `.claude/**` are unrestricted. Any write or unlink to `.claude/rules/` whose basename does NOT match `claudechic_*.md` is forbidden; any write to a symlink at a `claudechic_*.md` path is forbidden (per §4.2 symlink guard); the install routine MUST NOT recurse into subdirectories of `~/.claude/rules/` (per §4.2).
- [ ] **All four delegated UI features in scope:** welcome-screen access, workflow-ID discovery, disabled-IDs listing, settings-button vs `/settings` parity (per §7.1).
- [ ] **`git mv` command list:** §1.1 enumerates all bundled-workflow-directory moves (nine) plus engine .py, global manifest, and mcp_tools moves.
- [ ] **Cherry-pick ordering:** before restructure, none. After restructure: `8e46bca` (depends on Group A); orthogonal: `9fed0f3`, `f9c9418`, `5700ef5`, `7e30a53` (per §0.3 + §6.1).

### 13.2 UX checklist

**Coverage:**

- [ ] 3-level layout (workflows / rules+hints / mcp_tools) specced — Group C
- [ ] `.claudechic/` at user-tier (`~/.claudechic/`), project-tier (`<repo>/.claudechic/`), package-tier (`claudechic/defaults/`) — §1.1
- [ ] Workflow button UI surface specced; level distinction picked — §7.9
- [ ] Artifact-dir mechanism picked and specced — Group E
- [ ] Two-piece agent awareness specced (claudechic-awareness install + the agent-perceived session-start delivery and PostCompact refresh moments) — Group D
- [ ] Settings button at bottom + `/settings` + welcome-screen access — Group G
- [ ] Settings UI key list per §7.3
- [ ] `disabled_workflows` ID discovery + `disabled_ids` listing — §7.1 (both in scope)
- [ ] `docs/configuration.md` outline — §8
- [ ] Cherry-pick set — §6.1
- [ ] Auto default UX change — Group F + §7.1 #8
- [ ] Boundary rule with three explicit `.claude/` exceptions, documented as a narrative constraint — §9

**Wording:**

- [ ] Zero "convergence" / "merge program" in spec/docs/UI prose
- [ ] Boundary uses "primary-state writes" vs "non-destructive incidental touches"
- [ ] Agent-awareness goal stated as "behave the same"
- [ ] User-facing UI uses "level" for the 3-level distinction; not "tier" alone (per §7.11)
- [ ] User-facing UI says "settings" + "settings window/screen"; not "settings panel/dialog"
- [ ] User-facing UI says "workflow button"; not "workflow picker/menu/chooser"
- [ ] Abast relationship described in present-continuous bidirectional terms

**Scope:**

- [ ] No deferred features (`/fast`, migration logic, startup warning) have leaked into scope

### 13.3 Vocabulary checklist

- [ ] Every mention of "rules" qualifies on first mention per section
- [ ] Zero occurrences of convergence / converge / merge program / alignment merge
- [ ] Zero occurrences of "shadow" in override-resolution sense
- [ ] Every "merge" carries a qualifier
- [ ] Tier names exactly package / user / project; zero "global tier", "default tier", etc.
- [ ] "global" appears only as "global manifests" / "global rules" / "global hints" / the directory `global/` — never as a tier name
- [ ] "settings" qualified as claudechic settings or Claude settings when ambiguous
- [ ] "launched-repo root" used in prose; existing code symbols (`project_root` etc.) retained and glossed
- [ ] "chicsession" defined inline on first mention
- [ ] "artifact dir", "workflow run", "primary state", "non-destructive incidental touch" defined inline on first mention
- [ ] No bare "the boundary" / "the loader" / "the engine" / "the hook" / "the file" / "the tier" / "the symlink" / "the merge" / "the namespace"
- [ ] Path names use post-restructure layout
- [ ] Cross-fork relationship language uses cross-pollination / selective integration / coordination

---

## 14. Target file layout

After all groups land, the relevant codebase layout:

```
claudechic/
├── __init__.py
├── __main__.py
├── agent.py
├── agent_manager.py
├── analytics.py
├── app.py                          # uses TierRoots; invokes install_awareness_rules() in on_mount
├── awareness_install.py            # NEW (Group D §4.1) — install_awareness_rules() routine
├── chicsession_cmd.py
├── chicsessions.py
├── commands.py                     # /settings command added
├── compact.py
├── config.py                       # CONFIG_PATH = ~/.claudechic/config.yaml; awareness.install key added
├── checks/
├── context/                        # bundled awareness content (preserved; sourced by install routine)
│   ├── claudechic-overview.md
│   ├── workflows-system.md
│   ├── hints-system.md
│   ├── guardrails-system.md
│   ├── checks-system.md
│   ├── manifest-yaml.md
│   ├── multi-agent-architecture.md
│   └── CLAUDE.md
├── defaults/                       # NEW (package tier root)
│   ├── workflows/                  # bundled YAML
│   │   ├── audit/
│   │   ├── cluster_setup/
│   │   ├── codebase_setup/
│   │   ├── git_setup/
│   │   ├── onboarding/             # context_docs phase preserved; calls install_awareness_rules(force=True)
│   │   │   └── onboarding_helper/
│   │   ├── project_team/
│   │   ├── tutorial/
│   │   ├── tutorial_extending/
│   │   └── tutorial_toy_project/
│   ├── global/
│   │   ├── hints.yaml              # context_docs_outdated hint deleted
│   │   └── rules.yaml
│   └── mcp_tools/
├── errors.py
├── features/
│   └── worktree/
│       └── git.py                  # parallel `.claudechic` symlink added (§10.2)
├── file_index.py
├── formatting.py
├── guardrails/
│   ├── rules.py                    # Rule, Injection gain `tier` field
│   ├── parsers.py                  # gain `resolve()`
│   └── hits.py                     # writes <repo>/.claudechic/hits.jsonl
├── help_data.py
├── hints/
│   ├── engine.py
│   ├── parsers.py                  # gain `resolve()`
│   ├── state.py                    # _STATE_FILE = .claudechic/hints_state.json
│   ├── triggers.py                 # ContextDocsDrift deleted
│   ├── types.py                    # HintDecl gains `tier` field
│   └── __init__.py                 # ContextDocsDrift export deleted
├── history.py
├── mcp.py                          # discover_mcp_tools(tier_roots)
├── messages.py
├── onboarding.py
├── permissions.py
├── processes.py
├── profiling.py
├── protocols.py
├── remote.py
├── sampling.py
├── screens/
│   ├── chat.py
│   ├── chicsession.py
│   ├── diff.py
│   ├── disabled_ids.py             # NEW
│   ├── disabled_workflows.py       # NEW
│   ├── rewind.py
│   ├── session.py
│   ├── settings.py                 # NEW
│   ├── welcome.py                  # extended with Settings access
│   └── workflow_picker.py          # level badges added
├── sessions.py
├── styles.tcss                     # extended with settings + level classes
├── theme.py
├── usage.py
├── widgets/
│   └── ... (settings + auto-mode label additions)
└── workflows/                      # engine code
    ├── __init__.py                 # public API includes TierRoots, walk_tiers
    ├── agent_folders.py            # _find_workflow_dir deleted
    ├── engine.py                   # accepts artifact_dir kwarg
    ├── loader.py                   # 3-tier walk; partial-override detection
    ├── parsers.py                  # PhasesParser gains `resolve()`
    └── phases.py                   # Phase gains `tier` field

docs/
├── configuration.md                # NEW (Group G §8)
├── privacy.md                      # path reference rewritten
└── dev/

tests/
├── test_awareness_sdk_e2e.py       # NEW — live-SDK end-to-end (INV-AW-SDK-1; opt-in `live-sdk` marker; §11.1)
├── conftest.py                     # path comment updated
├── test_app.py
├── test_app_ui.py
├── test_autocomplete.py
├── test_bug12_guardrails_detect_field.py    # tmp_path/.claude → .claudechic
├── test_bug16_sessions_encoding.py          # NO change (Claude-owned read)
├── test_chicsession_actions.py
├── test_config_integration.py               # path → .claudechic/config.yaml
├── test_awareness_install.py                # NEW (Group D §12.2.1) — install routine tests
├── test_diff_preview.py
├── test_file_index.py
├── test_hints_integration.py                # tmp_path/.claude → .claudechic
├── test_loader_tiers.py                     # NEW (Group C §3)
├── test_roborev.py                          # NO change (Claude-owned read)
├── test_welcome_screen_integration.py       # tmp_path/.claude → .claudechic
├── test_widgets.py
├── test_workflow_guardrails.py              # tmp_path/.claude → .claudechic
├── test_workflow_hits_logging.py            # tmp_path/.claude → .claudechic
├── test_workflow_restore.py
└── test_yolo_flag.py
```

---

## 15. Reference materials

This SPEC is self-contained. The implementer does NOT need to read other files to know what to build. The files below exist for context/audit; they are not required reading.

| Topic | File |
|---|---|
| Glossary (canonical term forms) | `terminology_glossary.md` |
| Decision history, rationale, rejected paths, vision/STATUS error dispositions | `SPEC_APPENDIX.md` |
| Vision document (binding intent from prior team) | `vision.md` |
| Workflow state of record | `STATUS.md` |

---

*End of SPEC.md.*
