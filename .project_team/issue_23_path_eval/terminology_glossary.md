# Terminology Glossary — issue_23_path_eval

**Author:** TerminologyGuardian (Leadership lens: naming, domain terminology, boundary terms)
**Phase:** Specification
**Status:** Final — all sections complete; D16 and D17 locked into the prescriptive vocabulary.
**Anchored to:** D4, D5, D10, D16, D17, BF1, BF6, BF7 (see `STATUS.md`).
**Cross-lens position:** Skeptic favors Path 1; Composability favors Path 2; this glossary's lens (terminology) favors **Path 2** (see §5). D16/D17 sharpen §3 but do not shift the §5 verdict.

---

## 1. Frame — why terminology is load-bearing here

Issue #23's "independent claudechic settings" rule looks like a directory-layout problem, but it is a *naming-and-partitioning* problem. The rule is:

1. Claude settings and claudechic settings do not mix.
2. The launching repo's root contains nothing from us except `.claudechic/`.

Both clauses presuppose that we have already drawn — and named — three boundaries that today are blurred in the codebase:

- The boundary between **the `claude` CLI's namespace** (anything in any `.claude/` directory, per D5) and **claudechic's own namespace**.
- The boundary between **the user's project repository** (the repo claudechic is launched in) and **claudechic's own files** (which today leak into the launched repo's `.claude/`).
- The boundary between **"settings"** (the user's word, also the word in #23's body title) and **"config"** (the codebase's word, used in `config.py`, `ProjectConfig`, `.claudechic.yaml`).

Whichever path is chosen, the *terms we adopt now* dictate which directories exist, which files relocate, who owns what, and what "mixing" even means in code review. A glossary that is only descriptive lets the violation persist; a glossary that is only prescriptive cannot evaluate Path 1's import cost. Both are required, and they must be authored *before* implementation, otherwise the evaluation of Path 1 vs Path 2 is unanchored.

**Baseline finding carried forward (BF1):** sprustonlab today writes to `~/.claude/.claudechic.yaml`, `.claude/hints_state.json`, `.claude/phase_context.md`, and synchronises context docs into `.claude/rules/`. Under D5's broad reading of "Claude settings," all four are violations. Both paths must remediate this regardless of sequencing.

---

## 2. Descriptive glossary — current (mis)usage

### 2a. sprustonlab usage (current `main`)

Concrete inventory of how each contested term is used in this fork today. Sourced from `claudechic/`, `tests/`, `docs/`, `CLAUDE.md`, and `.gitignore`.

#### 2a.1. `.claude/` — Claude's namespace, but claudechic writes into it

Under D5, anything in any `.claude/` directory is Claude's namespace. sprustonlab presently uses `.claude/` (both the home-dir `~/.claude/` and the per-project `.claude/`) for both purposes — read-only consumption of Claude's own files **and** writing claudechic-owned files into the same tree.

| Path | Owner (intended) | Owner (today, sprustonlab) | Access |
|---|---|---|---|
| `~/.claude/settings.json` | Claude | Claude | claudechic reads (`help_data.py:67`) for enabled plugins |
| `~/.claude/.credentials.json` | Claude | Claude | claudechic reads (`usage.py:101`) for OAuth token |
| `~/.claude/projects/-path-to-project/*.jsonl` | Claude | Claude | claudechic reads sessions (`sessions.py:78,86`) |
| `~/.claude/history.jsonl` | Claude | Claude | claudechic reads command history (`history.py:29`) |
| `~/.claude/commands/<name>.md` | Claude | Claude | claudechic reads slash command discovery (`commands.py:360`) |
| `~/.claude/skills/<name>/SKILL.md` | Claude | Claude | claudechic reads skill discovery (`commands.py:361,370`) |
| `~/.claude/plans/<slug>.md` | Claude (plan mode) | Claude (writer) | claudechic permits Write/Edit for the SDK plan-mode tool (`agent.py:748,1239`, `app.py:676`) |
| `~/.claude/.claudechic.yaml` | claudechic | **claudechic (BF1 violation)** | claudechic reads/writes global config (`config.py:17`) |
| `.claude/hints_state.json` (per-project) | claudechic | **claudechic (BF1 violation)** | `HintStateStore` writes lifecycle + activation (`hints/state.py:127`) |
| `.claude/phase_context.md` (per-project) | claudechic | **claudechic (BF1 violation)** | workflow engine writes phase prompts (`app.py:1623,1635,1648,1822,1834`) |
| `.claude/rules/<doc>.md` (per-project) | claudechic | **claudechic (BF1 violation)** | `/onboarding` syncs `context/` docs here (`hints/triggers.py:26-31`, `global/hints.yaml:94`) |

`.gitignore` confirms three of the four violations (`.claude/hints_state.json`, `.claude/phase_context.md`) are silently expected to land in the launched repo's `.claude/`. They are gitignored precisely because today they end up there.

`features/worktree/git.py:293-301` symlinks `.claude/` from the main worktree into each new worktree "so hooks, skills, and local settings carry over." This means *the worktree feature itself depends on `.claude/` being a shared mixed-namespace directory*; relocating claudechic-owned files out of `.claude/` will require parallel changes here.

#### 2a.2. `.claudechic.yaml` and `.claudechic/` — claudechic's namespace, partially used

| Path | Today's role |
|---|---|
| `.claudechic.yaml` (launched repo root) | Per-project `ProjectConfig` — feature toggles only (`guardrails`, `hints`, `disabled_workflows`, `disabled_ids`). Loaded by `ProjectConfig.load()` in `config.py:107-136`. |
| `.claudechic/` (directory) | **Does not exist today.** No code references this path. The user's #23 boundary rule names it as the canonical container for everything claudechic puts in the launched repo. |

The asymmetry is the heart of the problem: sprustonlab already partially uses the `.claudechic` namespace at the file level (`.claudechic.yaml`) but has no `.claudechic/` directory. Everything that should live under `.claudechic/` per #23 currently lives in `.claude/`.

#### 2a.3. "settings" vs "config" in sprustonlab

The codebase distinguishes them, but inconsistently:

- "config" is the dominant internal term: `config.py`, `CONFIG`, `CONFIG_PATH`, `ProjectConfig`, `.claudechic.yaml`, "Configuration management for claudechic" (`config.py:1`), "Configuration is stored in `~/.claude/.claudechic.yaml`" (`CLAUDE.md:318`).
- "settings" is used in three distinct senses:
  1. **Claude's `settings.json`** — `help_data.py:66-72` reads `~/.claude/settings.json` for `enabledPlugins`. "settings" here = Claude's file by that name. (Under D5, this is Claude's namespace and claudechic correctly only reads it.)
  2. **User-facing surface labels** — `commands.py:111` lists "Analytics settings (opt-in/opt-out)" as a `/usage` description; `features/worktree/git.py:294` says "local settings carry over."
  3. **Issue #23's body** — per BF6, the issue title is "Settings window + configuration reference documentation," which is itself internally inconsistent (a "Settings" window for "configuration" docs).

Sprustonlab has no canonical resolution. The user's word for the whole thing is "settings"; the implementation's word is "config"; the boundary case (`settings.json`) is Claude's, not ours.

#### 2a.4. "launching repo root" / "project root" / "working dir" / "launched repo"

All four phrases appear to mean "the directory `claudechic` was invoked in" (= the repo whose code the user is working on, not claudechic's own repo), but each appears in a different register:

| Term | Where it appears | Connotation |
|---|---|---|
| "project root" / `project_root` | `hints/state.py:34,46,144` (`ProjectState.root`, `HintStateStore(project_root)`); `config.py:108` (`project_dir`) | Code-internal name. Resolves to `Path.cwd()` at app startup. |
| "working dir" / `working_dir` | `STATUS.md:4`; agent listing in `list_agents` | Operational/coordination register. |
| "launching repo" / "launched repo" | `userprompt.md:13`; this run's prose | User-facing register; only appears in conversation, never in code. |
| "main worktree" | `features/worktree/git.py` | Git-feature register; refers to the canonical clone, not the project semantics. |

There is no canonical term in code. `ProjectConfig.load(project_dir: Path)` and `ProjectState(root: Path)` use different parameter names for the same concept. Issue #23's user-facing phrasing ("the launching repo's root") matches no code symbol.

#### 2a.5. "independent" — undefined in code

The word "independent" appears in `userprompt.md` and `STATUS.md` D4/D5 but has no representation in the codebase. The two-clause definition (a) Claude vs claudechic don't mix, (b) launched repo's root contains nothing from us except `.claudechic/` is a *user-stated invariant*, not a code-asserted one. There is no test, no assertion, no docstring that declares this rule. It is enforced today only by convention — and BF1 demonstrates the convention is already broken.

#### 2a.6. Summary of sprustonlab terminology hazards

1. `~/.claude/.claudechic.yaml` is the most visible BF1 violation: a claudechic-owned file living *inside* Claude's home namespace, with the path hard-coded in `config.py:17` and documented as the canonical config location in `CLAUDE.md:318`, `theme.py:3,87`, `errors.py:77`, `context/CLAUDE.md:79`, and `docs/privacy.md:36`. **Under D17, every one of these references migrates 1-to-1 to `<launched_repo>/.claudechic/config.yaml`** — the global tier collapses into the per-project tier (see §3.4). The migration is mechanical; the documentation surface is wide. This file count plus the migration code in `config.py:_load` is the full doc-surface inventory.
2. `.claude/hints_state.json` is a second BF1 violation, with `_STATE_FILE = ".claude/hints_state.json"` in `hints/state.py:127`. State *content* must survive migration (existing user installs have `times_shown`, `dismissed`, `taught_commands` in this file).
3. `.claude/phase_context.md` is a third BF1 violation written by `app.py:1623+`. It is ephemeral per-phase — no migration concern, but multiple call sites.
4. `.claude/rules/` is a fourth BF1 violation populated by `/onboarding`. The hint at `global/hints.yaml:94` ("update your `.claude/rules/` files") will need to be re-worded.
5. The worktree symlink in `features/worktree/git.py:293-301` couples the worktree feature to `.claude/` being shared. Any relocation must update this symlink behavior to match new claudechic-owned paths (likely a second symlink for `.claudechic/`).
6. "settings" vs "config" is unresolved at the source-of-truth level. #23 names a "Settings window," but the entire implementation calls it config. Picking one is a rename across docs, code, and (ideally) the issue title.
7. There is no code symbol that names "the launched repo root" canonically. `project_root`, `project_dir`, `root`, `cwd` all appear. A canonical name should be chosen and used throughout.
8. **Issue #21 (linked from #23) canonicalizes the violation, not the boundary.** Per FDR §6a, issue #21's body says "accessible from welcome screen" and treats `.claudechic.yaml` as the de-facto project file; neither #21 nor #23's body questions the `~/.claude/.claudechic.yaml` location. The userprompt-derived boundary scope (FDR §6b) is therefore the *only* place the relocation is named. Terminology-wise, the issues themselves enshrine the violating vocabulary; #23's body does not provide cover for the rename work.

### 2b. abast usage — `claudechic/defaults/`, `fast_mode_settings.json`, engine-in-`workflows/`

Concrete inventory of how abast/main names the boundary. Sourced from FDR §3 (themes), §5 (hot files), §8 (hazards), and `fork_file_map.csv`.

#### 2b.1. `.claude/` and `~/.claude/` — abast accepts the BF1 violation as-is

abast's divergent commits (8 total, themes A-T1–A-T5) **do not relocate** anything out of `~/.claude/` and **do not introduce** any new claudechic-owned paths under `.claude/`. The two-line touch on `claudechic/config.py` (FDR §5: `+2/-2` for auto-perm startup, commit `5700ef5`) is purely a default-value tweak; the `CONFIG_PATH = Path.home() / ".claude" / ".claudechic.yaml"` literal is unchanged.

Implication: abast **inherits BF1** identically. There is no abast-side cleanup of the violation to import; nor is there any abast-side terminology that contradicts §3's prescriptive boundary.

#### 2b.2. `claudechic/defaults/` — abast's new namespace

A-T1 (FDR §3) introduces a directory **`claudechic/defaults/`** containing two subtrees:

- `claudechic/defaults/workflows/<workflow>/...` — bundled workflow YAML + role identity files (~85 files, byte-near-identical mirrors of sprustonlab's `claudechic/workflows/<workflow>/...`).
- `claudechic/defaults/global/{hints,rules}.yaml` — bundled global manifests (mirrors of sprustonlab's `claudechic/global/{hints,rules}.yaml`).

Plus a "fallback discovery" loader (commit `8e46bca`) so the package finds these paths.

The term **"defaults"** is new vocabulary that does not appear on sprustonlab as a directory name. It carries semantic weight: it implies a *default vs override* relationship between the bundled (default) content and any user override (presumably the `.claudechic.yaml` toggles). sprustonlab's S-T1 layout makes no such distinction — `claudechic/workflows/` and `claudechic/global/` are simply "where the bundled content lives," with no language of "defaults."

#### 2b.3. `claudechic/workflows/` — engine-and-data namespace on abast

abast's `claudechic/workflows/` retains the *engine code* (`engine.py`, `loader.py`, `parsers.py`, `phases.py`, `agent_folders.py`, `__init__.py`) alongside YAML data. abast performed no equivalent of sprustonlab's `S-T1` rename of these files to `claudechic/workflow_engine/`. From `fork_file_map.csv`, the `R080`/`R099`/`R100` rename markers (`claudechic/{workflows => workflow_engine}/...`) appear only on the sprustonlab side.

Therefore on `abast/main`, `claudechic/workflows/` has *two* referents simultaneously: it is the engine package **and** the data root. On `sprustonlab/main`, post-S-T1, it is *only* the data root. **Same path, different contents, different ontological status.** This is the §2c centerpiece.

#### 2b.4. `fast_mode_settings.json` — abast's new "settings" file

A-T2 (FDR §3, FDR §8 H4) introduces `claudechic/fast_mode_settings.json` (1 line on FDR row 271), containing `{"fastMode": true}`. The naming pattern is significant for the terminology lens:

- The file name uses the word **"settings"** (matching the user's umbrella vocabulary, mismatching the codebase's "config" convention).
- It lives **inside the package directory** (`claudechic/...`), not in `.claude/`, not in `.claudechic/`. Under §3 (prescriptive), this location is undefined — it is neither Claude's namespace nor claudechic's launched-repo namespace. It is "claudechic-source-code-as-runtime-data."
- It is therefore a **third class** of boundary violation: claudechic state hard-coded into the source-installed package itself. The remediation under §3 would be either (a) treat `fastMode` as a runtime toggle through the regular config system (move it into `.claudechic/...` or the global config) or (b) treat it as code (delete the JSON, move the constant to a Python module).
- The *companion* `/fast` command (`26ce198`) reads/writes this file via the package path, which means cherry-picking `/fast` cleanly *requires* taking `fast_mode_settings.json` along with it (BF4 dependency-drop applies, but as a *terminology dependency* — pulling `/fast` without `fast_mode_settings.json` produces clean code that has no settings file to read).

The naming is also internally inconsistent with abast's own `claudechic/defaults/` namespace: if "defaults" means "bundled non-user-editable content," then a *settings* file in the package root violates abast's own implicit grammar.

#### 2b.5. abast's "settings" surface

Beyond `fast_mode_settings.json`, abast contributes the following touchpoints where the word "settings" or "config" appears in divergent commits (cross-referenced from FDR §5 + per-hot-file commit attribution):

| Surface | abast change | Term used |
|---|---|---|
| `claudechic/app.py` startup region | default to `auto` permission mode | "permission mode" (no rename) |
| `claudechic/commands.py` Shift+Tab cycle | add `auto` to cycle | "permission mode" |
| `claudechic/commands.py` `/fast` command | new command reading/writing `fast_mode_settings.json` | "fast mode settings" |
| `claudechic/config.py` (+2/-2) | tweak default | "config" (unchanged) |
| `tests/conftest.py` permission fixture | new fixture | "settings" (one fixture name uses it) |

So abast's contribution is **not** to canonicalize "settings" vs "config" — they use both inconsistently, like sprustonlab. abast's *novelty* is binding the word "settings" to a JSON file at package root, which sprustonlab does not do anywhere. Path 1 must decide whether to retain the word "settings" in the file name or rename it on cherry-pick.

#### 2b.6. Files abast did NOT touch on the boundary surface

Per FDR §7d, abast left these files unchanged in their divergent commits, even though they are part of the BF1 violation surface:

- `claudechic/hints/state.py` (`.claude/hints_state.json` writer)
- `claudechic/errors.py`
- `claudechic/theme.py`
- `claudechic/usage.py`
- `claudechic/agent.py` (mostly — only +5/-4 small touch)
- `claudechic/features/worktree/git.py` (the BF7 symlink site)
- `claudechic/hints/triggers.py`

This means the largest part of the boundary-relocation surface is **uncontested** by abast. #23's relocation work mostly does not collide with abast's divergent commits at the textual level — the collision is layout-semantic (§2c) and lives in the bundled-content trees, not the boundary code.

#### 2b.7. abast's `pyproject.toml` and dependency-pin terminology

abast's `0ad343b` pins `anthropic==0.79.0` for fast-mode support. The terminology lens flags this only because it is the textbook BF4 dependency-drop instance: `/fast` depends on `fast_mode_settings.json` which depends on the SDK pin. Three artefacts, three different "settings"/"config"/"pin" words for the same conceptual thing — a runtime toggle. None is canonicalized.

#### 2b.8. Summary of abast terminology hazards

1. abast invents a new namespace word: **"defaults"** (`claudechic/defaults/`). Not present on sprustonlab. Carries default-vs-override semantics.
2. abast keeps `claudechic/workflows/` as engine + data; sprustonlab split it. **Same name, different contents.** (§2c centerpiece.)
3. abast introduces a new "settings" file (`fast_mode_settings.json`) at package root. Third class of boundary violation; uses the word "settings" the codebase otherwise reserves for Claude's `settings.json`.
4. abast does not touch the BF1 violation surface; they accept the existing terminology as-is. **No alignment work to import via Path 1.**
5. abast's `/fast` and auto-perm features braid four terms (settings, config, mode, pin) without resolving any.

### 2c. Divergence between forks — terminology side-by-side

Side-by-side table of contested terms. "Conflict mode" follows the categories named in §2b's planning header.

| # | Term / Path | sprustonlab usage | abast usage | Conflict mode |
|---|---|---|---|---|
| 1 | `~/.claude/.claudechic.yaml` | global config (BF1 violation) | identical (BF1 violation, untouched) | **Identical** — no divergence; both broken |
| 2 | `.claude/hints_state.json` | per-project hints state (BF1) | identical (untouched) | **Identical** — both broken |
| 3 | `.claude/phase_context.md` | per-project workflow phase prompts (BF1) | identical (untouched) | **Identical** — both broken |
| 4 | `.claude/rules/` | synced context docs (BF1) | identical (untouched) | **Identical** — both broken |
| 5 | `.claudechic.yaml` (project root) | per-project `ProjectConfig` toggles | identical | **Identical** |
| 6 | `.claudechic/` directory | does not exist | does not exist | **Both absent** — must be defined by §3 |
| 7 | `claudechic/workflows/` | YAML data only (engine extracted) | YAML data **+ engine Python** | **Re-scoped** ⚠ centerpiece |
| 8 | `claudechic/workflow_engine/` | engine Python (S-T1 split) | does not exist | **Newly introduced** by sprustonlab |
| 9 | `claudechic/defaults/` | does not exist | bundled workflows + global manifests | **Newly introduced** by abast |
| 10 | `claudechic/global/` | bundled hints/rules at this path | renamed to `claudechic/defaults/global/` | **Renamed** by abast (path-mirror with drift; FDR §8 H2) |
| 11 | `fast_mode_settings.json` (package root) | does not exist | abast-only "settings" file | **Newly introduced** by abast |
| 12 | `/fast` command | does not exist | abast command toggling `fast_mode_settings.json` | **Newly introduced** by abast |
| 13 | `auto` permission mode (term) | does not exist | added to Shift+Tab cycle + as startup default | **Newly introduced** by abast |
| 14 | `default_permission_mode` (config key) | exists, default `"default"` | exists, default `"auto"` | **Re-scoped** (default value differs) |
| 15 | `ProjectConfig` (dataclass) | introduced in S-T1 (`config.py:94+`) | not present in abast | **Newly introduced** by sprustonlab |
| 16 | "settings" (umbrella word) | rare in code; user-facing labels only | introduced in `fast_mode_settings.json` filename | **Re-scoped** — abast uses for a JSON file; sprustonlab uses for UX labels |
| 17 | "config" (umbrella word) | dominant internal term | unchanged | **Identical** (both use, neither canonicalized) |
| 18 | "defaults" (semantic) | not used as a namespace | active namespace (`claudechic/defaults/`) | **Newly introduced** by abast |
| 19 | "fallback discovery" | not used | abast's discovery mechanism term (commit `8e46bca`) | **Newly introduced** by abast |
| 20 | "fast mode" / `fastMode` | not used | abast feature name | **Newly introduced** by abast |
| 21 | "launching repo root" / "project root" / etc. | inconsistent across `project_root`, `project_dir`, `root`, `cwd` | identical inconsistency (no abast change) | **Identical** — both inconsistent |
| 22 | `ProjectState.root` | sprustonlab S-T1 introduction | not present (abast lacks the consolidated layout) | **Newly introduced** by sprustonlab |

#### 2c.1. The `workflows/` referent split — centerpiece

| Aspect | sprustonlab | abast |
|---|---|---|
| Path | `claudechic/workflows/` | `claudechic/workflows/` |
| Contains | YAML manifests + role-identity Markdown only | YAML manifests + role-identity Markdown **+ Python engine** (`engine.py`, `loader.py`, `parsers.py`, `phases.py`, `agent_folders.py`, `__init__.py`) |
| Counterpart bundling path | `claudechic/global/` | `claudechic/defaults/workflows/` and `claudechic/defaults/global/` |
| Engine package | `claudechic/workflow_engine/` | (engine still under `workflows/`) |
| What it imports as | `from claudechic.workflow_engine import ...` | `from claudechic.workflows import ...` |
| Consequence for cherry-pick | A naïve cherry-pick of an abast commit touching `claudechic/workflows/loader.py` lands a Python file in a directory that on sprustonlab is now YAML-only. The file will *exist* and *import-resolve* (because Python imports operate on the package, not the directory's content type), but it is a stowaway — it duplicates code in `workflow_engine/loader.py` and breaks the §3 prescription that `workflows/` is data. |

This is the highest-stakes terminology divergence in the entire evaluation. It is invisible to text-merge tooling (the merge will succeed) and only detectable by a lens that tracks *what the directory name is supposed to mean*. It is the canonical example of why this glossary exists.

#### 2c.2. The `defaults/` ↔ `global/` ↔ `workflows/` triangle

Three directory names, three forks of the same concept ("bundled content shipped with the package"):

| Concern | sprustonlab | abast |
|---|---|---|
| Bundled workflow YAML | `claudechic/workflows/<wf>/...` | `claudechic/defaults/workflows/<wf>/...` |
| Bundled global manifests | `claudechic/global/{hints,rules}.yaml` | `claudechic/defaults/global/{hints,rules}.yaml` |
| Discovery semantics | direct package paths | "fallback discovery" loader |

Under §3 (prescriptive) we must pick one of:
- **Adopt sprustonlab's S-T1 layout** — `workflow_engine/` for engine, `workflows/` for data, `global/` for global manifests. **Discard abast's "defaults" namespace word.**
- **Adopt abast's A-T1 layout** — `defaults/workflows/`, `defaults/global/`, engine stays in `workflows/`. **Discard sprustonlab's `workflow_engine/` rename and accept "defaults" as canonical.**
- **Merge into a third layout** — likely `claudechic/bundled/` or `claudechic/builtin/` plus retaining `workflow_engine/`. Highest cost; not justified without user input.

The terminology lens has no preference between the *first two layouts* on linguistic grounds alone — both "workflows + workflow_engine" and "defaults + workflows-as-engine" are coherent vocabulary systems. The lens has a strong preference against the *combination* of both vocabularies, which Path 1 risks producing if cherry-picks land abast's `defaults/` adds onto a sprustonlab tree that already has `workflows/` + `workflow_engine/`. **Vocabulary unity is the lens criterion.**

#### 2c.3. The `fast_mode_settings.json` divergence

abast: a JSON file at `claudechic/fast_mode_settings.json` containing `{"fastMode": true}`, paired with a `/fast` command. The file name uses "settings"; the contents are a single boolean toggle; the location is in the package source tree.

sprustonlab: no equivalent. Permission mode is handled through the regular config system (`config.py:CONFIG["default_permission_mode"]`).

Three options under §3:
- **Reject the file.** Move `fastMode` into the regular config (`<launched_repo>/.claudechic/config.yaml` per D17 / §3.4). Mechanical port; preserves §3.7 invariant.
- **Rename the file** to `.claudechic/fast_mode.yaml` or similar, keeping it as a per-project toggle but inside the §3.7-canonical namespace.
- **Adopt abast's pattern as a "package-level toggle" class.** Carve a new exception in §3.7 for source-tree-installed toggles. The terminology lens recommends against this — it adds a third boundary class, defeating the purpose of #23.

#### 2c.4. Conflict-mode tally

From the §2c table:

| Conflict mode | Count |
|---|---|
| Identical (no divergence) | 5 (rows 1–4, 17) |
| Identical-but-broken (BF1) | 4 (rows 1–4) |
| Both absent | 1 (row 6 — `.claudechic/`) |
| Newly introduced by sprustonlab | 4 (rows 8, 15, 22, plus implicit `audit/`, `mcp_tools/`, `context/` per FDR Anomaly 4) |
| Newly introduced by abast | 7 (rows 9, 11, 12, 13, 18, 19, 20) |
| Renamed by abast | 1 (row 10) |
| Re-scoped (same name, different content) | 3 (rows 7, 14, 16) — including the centerpiece |

abast introduces **more contested terminology** (7 new namespaces/terms + 1 rename + 3 re-scopings) than sprustonlab (4 new). This is the central asymmetry the terminology lens reports into §4.

### 2c.5. Documentation drift on the boundary

abast does not touch `CLAUDE.md`, `claudechic/context/CLAUDE.md`, or `docs/configuration.md` (which doesn't exist yet). All sprustonlab-side documentation drift is in S-T1 (consolidation) and the new `claudechic/context/` tree (sprustonlab-only). Therefore:

- The doc-surface inventory flagged earlier (`CLAUDE.md:318`, `theme.py:3,87`, `errors.py:77`, `context/CLAUDE.md:79`, `docs/privacy.md:36`, plus `claudechic/context/hints-system.md`) is **entirely sprustonlab-side**.
- Path 1's cherry-picks do not touch these doc surfaces. The doc rewrite is therefore Path-2-friendly: locking in §3 vocabulary in the docs first does not block any abast cherry-pick.

---

## 3. Prescriptive glossary — canonical post-#23 meanings

Anchored to D4 (claudechic config must move out of `~/.claude/`) and D5 (anything in any `.claude/` directory is Claude's namespace; claudechic stays out entirely). These definitions are the convergence target both paths must reach.

### 3.1. `claude` namespace — `.claude/` and `~/.claude/`

**Definition.** Every directory or file named `.claude` (in any location: home, repo root, worktree) belongs to the `claude` CLI / Anthropic tooling. claudechic may *read* from this namespace where Claude's own contract permits (e.g. `~/.claude/settings.json`, `~/.claude/projects/`, `~/.claude/history.jsonl`, `~/.claude/.credentials.json`, `.claude/commands/`, `.claude/skills/`, `~/.claude/plans/`). claudechic may **not** create, write, modify, or delete any path inside `.claude/`.

**Excluded today, must relocate (BF1):**
- `~/.claude/.claudechic.yaml` → relocate (see 3.4).
- `.claude/hints_state.json` → relocate to `.claudechic/hints_state.json` (see 3.5).
- `.claude/phase_context.md` → relocate to `.claudechic/phase_context.md` (see 3.5).
- `.claude/rules/` → relocate to `.claudechic/rules/` (see 3.5).

### 3.2. `claudechic` namespace — `.claudechic/` directory only (D17 locked)

**Definition (D17 canonical).** All claudechic-owned per-project files live under a single `.claudechic/` directory at the launched-repo root. There is no top-level `.claudechic.yaml` file. The user-editable config file is `.claudechic/config.yaml` inside the directory.

Per the user's clause (b), the launched repo's root contains exactly one claudechic-authored entry: the `.claudechic/` directory. This is the strict reading of #23 — D5 compliance is unconditional, and the directory form aligns with BF7 (the worktree symlink mechanism — symlinking a single directory is cleaner than tracking a directory + a sibling file). Composability's BF7 argument carried; this lens concurs.

### 3.3. "Settings" vs "config" — D16 locked

**D16 canonical (verbatim user resolution):**

- **"Settings"** — user-facing umbrella term. Used in: the `/settings` TUI screen, the phrase "open settings," prose in `docs/configuration.md` and `CLAUDE.md`, button labels, status-bar copy, error messages addressed to the user.
- **"Config"** — technical term reserved for the YAML file format and the loader. Used in: `config.py`, the `ProjectConfig` dataclass, `*.yaml` filenames, internal docstrings, code-comment references to the file format, log messages addressed to developers.

**Anchored definitions following D16:**

- **"Claude settings"** — per D5, the full set of files inside any `.claude/` directory, owned by the `claude` CLI / Anthropic tooling. Includes `settings.json`, `projects/`, `history.jsonl`, `.credentials.json`, `commands/`, `skills/`, `plans/`, and any future Claude artifact. This is the "settings" the user-facing claudechic UI must *not* expose for editing.
- **"claudechic settings"** — the user-facing umbrella for everything claudechic stores per project. Edited via the `/settings` TUI; serialized to `.claudechic/config.yaml` (per D17). The word "settings" in user prose always refers to this.
- **"claudechic config"** — the YAML file `.claudechic/config.yaml` and its loader code (`config.py`, `ProjectConfig`). The word "config" never appears in user prose; it is reserved for code and developer docs.

**Implications for §6a-named keys (per FDR §6a):** The `/settings` TUI screen is named "Settings" (D16); the docs page is named `docs/configuration.md` (issue #23 body verbatim — the issue title's "configuration reference" survives because it describes the *reference document*, not the user-facing UI). The YAML file the screen edits is "the config file." No code symbol should be renamed `Settings*` for D16 — `ProjectConfig` etc. stay; the rename is about user-visible prose only.

### 3.4. Global vs per-project — D17 collapses to per-project only

**D17 canonical reading (literal):** Per the Coordinator's instruction, "every reference to `~/.claude/.claudechic.yaml` becomes `.claudechic/config.yaml`". This is a 1-to-1 migration mapping with no global tier on the right-hand side. The strict interpretation: **there is no separate global config file**; what today lives in `~/.claude/.claudechic.yaml` (analytics ID, default permission mode, theme, worktree path template, etc.) lives in each launched repo's `.claudechic/config.yaml`.

This is the cleanest D5 reading — nothing in `.claude/`, nothing under `~/.config/`, nothing in `~/.claudechic/`. Every claudechic-authored byte lives under `<launched_repo>/.claudechic/`. The global tier disappears.

**Consequence for keys today scoped globally:**

| Key (today, in `~/.claude/.claudechic.yaml`) | Post-D17 home |
|---|---|
| `analytics.id` (UUID) | `<launched_repo>/.claudechic/config.yaml`, scoped per project |
| `analytics.enabled` | same |
| `default_permission_mode` | same |
| `show_message_metadata` | same |
| `vi-mode` | same |
| `recent-tools-expanded` | same |
| `worktree.path_template` | same |
| `experimental.*` | same |
| `themes` | same |
| `logging.*` | same |

**Terminology lens flag (not a re-opening of D17):** The literal D17 mapping has a behavioural side-effect — every project gets its own `analytics.id` rather than one shared identity per user. This is consistent with #23's "independent settings" rule and may be desirable, but is a behavioural change worth surfacing for UserAlignment. The terminology lens has no opinion on whether the side-effect is acceptable; it only flags that the locked vocabulary makes "global" config a dead phrase.

**Migration logic.** `config.py:29-32` already migrates from `claudechic.yaml` → `.claudechic.yaml`. Under D17, a *third* migration step is added: on first run in a launched repo, if `~/.claude/.claudechic.yaml` exists, read it, write the contents to `<cwd>/.claudechic/config.yaml`, and either delete or leave-with-deprecation-warning the old file. The migration touches `config.py:17` and `config.py:_load`.

### 3.5. Per-project claudechic settings location — full inventory under D17

**Definition (D17 canonical).** Every per-project file claudechic writes lives under `<launched_repo>/.claudechic/` at the launched-repo root. Full inventory:

| Today | Post-#23 (D17) |
|---|---|
| `~/.claude/.claudechic.yaml` (global) | `<launched_repo>/.claudechic/config.yaml` (per-project; D17 collapses global into per-project) |
| `<launched_repo>/.claudechic.yaml` (per-project toggles) | `<launched_repo>/.claudechic/config.yaml` (merged into the same file as the former global keys) |
| `<launched_repo>/.claude/hints_state.json` | `<launched_repo>/.claudechic/hints_state.json` |
| `<launched_repo>/.claude/phase_context.md` | `<launched_repo>/.claudechic/phase_context.md` |
| `<launched_repo>/.claude/rules/<doc>.md` | `<launched_repo>/.claudechic/rules/<doc>.md` |

Migration of `hints_state.json` must preserve `times_shown`, `last_shown_ts`, `dismissed`, `taught_commands`, and the `activation` section. Migration of the merged config file must reconcile schema between the former global and former project YAML — sprustonlab today has both `.claudechic.yaml` (project toggles: `guardrails`, `hints`, `disabled_workflows`, `disabled_ids`) and `~/.claude/.claudechic.yaml` (global keys above). The post-D17 file is the union of both schemas at one path. No key collision exists today (project-toggle keys and global keys are disjoint), so the merge is mechanical.

### 3.6. "launching repo root" — canonical term needed

**Recommended canonical term:** **"launched-repo root"** (noun) or `launched_repo_root` (Python identifier).

Rationale: "launching" is participial (the act of launching); "launched" is the resulting state (the repo that has been launched-into). The existing variants `project_root`, `project_dir`, `root`, `cwd` overload "project" with both "claudechic the project" and "the project the user is working on." A distinct phrase removes the ambiguity.

**Required renames if adopted:**
- `ProjectConfig.load(project_dir)` → `ProjectConfig.load(launched_repo_root)` (or equivalent).
- `ProjectState.root` → `ProjectState.launched_repo_root`.
- Userprompt phrasing and `STATUS.md` "working dir" can remain colloquial; code must be canonical.

If the user prefers "project root" because of incumbency, that is acceptable — but then the docs must explicitly disambiguate "project root" from "claudechic's own repo root."

### 3.7. "independent" — operational definition (locked under D17)

**Definition.** "Independent claudechic settings" means both:
1. **No claudechic file lives under any `.claude/` directory.** (Tested by: `find .claude/ ~/.claude/` produces no claudechic-authored content; `find . -path '*/.claude/*' -newer <baseline>` is empty after a claudechic run.)
2. **The launched-repo root contains exactly one claudechic-authored entry: `.claudechic/`.** (Tested by: after a claudechic run in a fresh repo, `git status` shows `.claudechic/` and nothing else as new from claudechic.) **No top-level `.claudechic.yaml` file exists** — D17 places the config inside the directory at `.claudechic/config.yaml`.

This is a code-asserted invariant — there should be a test that runs claudechic in a tmp repo and asserts the post-run filesystem matches §3.7.1 + §3.7.2. Today no such test exists. The test is the canonical compliance check for D5 and the user's clause (b).

### 3.8. Other contested terms canonicalized in passing

- **"workflow" / "workflow_engine" / "workflows/"** — already disambiguated in `CLAUDE.md` ("Important: workflow_engine/ vs workflows/"); no #23 impact, no rename needed. Flagged here only to note it is *not* a contested term in this evaluation.
- **"session" vs "chicsession"** — orthogonal to #23 (no `.claude/` boundary involvement). No #23 impact.
- **"hints state" vs "hints lifecycle" vs "hints activation"** — already canonicalized inside `hints/state.py` via `HintStateStore` / `ActivationConfig`. Path migration changes the *file location*, not these names. No rename needed.

---

## 4. Per-path terminology implications

This section converts §2c's divergence catalogue into per-path import cost. Two ledgers are constructed in parallel — one for each path — using identical criteria.

### 4.1. Decision criteria (symmetric, applied to both paths)

For each contested term/path in §2c, classify:

- **Vocabulary unity** — does the path produce a single coherent vocabulary, or does it leave two contested namespaces co-resident?
- **Rename volume** — how many string-level renames does the path require?
- **Rename type** — *mechanical* (literal-string replace at known sites) vs *semantic* (requires understanding intent: e.g. distinguishing "settings as user-facing label" from "settings as filename").
- **Atomicity** — can the rename be a single commit, or does it touch on-disk state that requires a migration step?
- **Drift compounding** — does the path increase the surface of contested terms, or reduce it?

The lens is symmetric: it does not assume Path 1 or Path 2 is preferred a priori. It applies the same five criteria to each.

### 4.2. Path 1 ledger — pull from abast → implement #23

For each abast contribution (rows 9–14, 18–20 of §2c), decide whether to pull and what the terminology cost is.

| Abast term / artifact | Pull decision (terminology lens) | Vocabulary impact | Rename type | Path-1 cost note |
|---|---|---|---|---|
| `claudechic/defaults/` namespace | **Conflicts with §3** if pulled as-is | Imports a third namespace word ("defaults") on top of sprustonlab's existing `workflows/` + `workflow_engine/`; produces a tree with all three vocabularies co-resident | Semantic — choice between collapsing `defaults/workflows/` into `workflows/` or vice versa is not mechanical | High; the entire A-T1 commit must be re-pathed before applying. D8 (abast cooperation) helps but does not eliminate the rename. |
| `claudechic/workflows/` engine code | **Conflicts with §3** | If pulled naïvely, lands engine Python in a directory sprustonlab now treats as YAML-only; produces *two* engine packages (`workflows/` + `workflow_engine/`) | Semantic — the cherry-pick must be re-pathed to `workflow_engine/`, not just renamed | Per FDR Anomaly 3: the merge will *succeed* textually but produce a stowaway engine. Invisible to text-merge tooling. |
| `fast_mode_settings.json` (file) | **Conflicts with §3.7** | A "settings" file at package root violates §3.7 (under D17, only `<launched_repo>/.claudechic/` is canonical; nothing else). Pulling it means accepting a third boundary class. | Mechanical to relocate; semantic (D16) to *not* keep "settings" in the new path — D16 reserves "config" for filenames, so the relocation also renames `fast_mode_settings.json` → `.claudechic/fast_mode.yaml` or merges into `config.yaml`. | Pulling and *then* rewriting in #23 means the file lives in the wrong place between Path 1 step 1 and Path 1 step 2. |
| `/fast` command | **Compatible after relocation** | Adds a new command; no namespace conflict per se, but is *coupled* to `fast_mode_settings.json` (BF4 dependency-drop) | Mechanical (assuming the dependency is taken with it and rewired) | Cost is bundled with `fast_mode_settings.json` cost. |
| `auto` permission mode | **Compatible** | Adds a vocabulary item ("auto") to an existing closed set ("default"/"auto"/"plan"); no boundary impact | Mechanical | Low; clean addition. |
| `default_permission_mode` default value change (`"default"` → `"auto"`) | **Compatible (UX call, not terminology)** | Out of scope for terminology lens | N/A | Defer to UserAlignment. |
| Full-model-id validation loosening | **Compatible** | No terminology impact | N/A | Out of scope for this lens. |
| `anthropic==0.79.0` pin | **Compatible** | No terminology impact | N/A | Out of scope. |
| `claudechic/defaults/global/{hints,rules}.yaml` | **Conflicts with §3** if pulled at the abast path | Imports the "defaults" word; cherry-pick must merge into `claudechic/global/` | Mechanical (path replace) but content drifts from sprustonlab (10-line drift on `hints.yaml`) | Each pulled YAML file requires `defaults/` → `<root>/` re-path and a content reconciliation. |

**Path 1 totals (terminology lens):**
- **3 conflicts with §3** (defaults namespace, engine-in-workflows, fast_mode_settings.json) — load-bearing
- **2 conflicts requiring semantic rename** (defaults choice, engine path)
- **1 invisible-to-text-merge collision** (engine-in-workflows; FDR Anomaly 3)
- **Drift compounding: increases.** Path 1 step 1 lands sprustonlab into a state with **three contested namespaces co-resident** (`workflows/` + `workflow_engine/` + `defaults/`) before #23 even starts. Path 1 step 2 (#23) must then converge them, AND do its own boundary-relocation work, AND ship a settings UI.

**Vocabulary unity at end of Path 1 step 1:** ❌ broken — three namespaces co-resident.
**Vocabulary unity at end of Path 1 step 2 (#23):** ✓ achievable, but requires the convergence work that step 1 just made *more* expensive.

### 4.3. Path 2 ledger — implement #23 → pull from abast

Under Path 2, sprustonlab first lands §3's prescriptive vocabulary (via #23), then cherry-picks abast on top of a stable target.

| Abast term / artifact | Cherry-pick decision (terminology lens) | Vocabulary impact | Rename type | Path-2 cost note |
|---|---|---|---|---|
| `claudechic/defaults/` namespace | **Diverged from §3** | If §3 has already canonicalized `claudechic/workflows/` (data) + `claudechic/workflow_engine/` (engine) + `claudechic/global/` (manifests), abast's `defaults/...` adds must be re-pathed at cherry-pick time | Mechanical (path-rewrite at apply time, e.g. via `git apply --directory` or a sed pass on the patch) | Per-cherry-pick rename layer; same cost as Path 1's same step, but performed *once per pull*, not en masse. |
| `claudechic/workflows/` engine code | **Diverged from §3** | §3 has separated engine and data; abast's engine commits must be re-pathed to `workflow_engine/` | Mechanical *if* the engine APIs match; semantic *if* sprustonlab's `workflow_engine/` introduced API drift during S-T1 | Per FDR row 215, 238, 268, 269, 270, 273: sprustonlab's S-T1 engine moves are mostly file renames (R080/R099/R100) with tiny line edits, so APIs are preserved. Mechanical re-path is feasible. |
| `fast_mode_settings.json` | **Diverged from §3.7** | §3.7 forbids package-root settings files; cherry-pick must relocate to `<launched_repo>/.claudechic/fast_mode.yaml` (or merge into `<launched_repo>/.claudechic/config.yaml`) before applying. D16 also forces the file rename: "settings" out, "config" or feature-name in. | Mechanical (relocation) + semantic (data-format choice: JSON-as-is vs convert to YAML for consistency with `.claudechic/config.yaml` per D17) | One-time cost paid at the moment `/fast` is pulled; does not contaminate the rest of the tree. |
| `/fast` command | **Compatible after companion relocation** | Adds command; reads from §3-canonical location once `fast_mode_settings.json` is relocated | Mechanical | Cost bundled with the JSON relocation. |
| `auto` permission mode | **Compatible** | Same as Path 1 — clean addition | Mechanical | Low. |
| `default_permission_mode` default value change | **Compatible (UX call)** | Out of scope | N/A | Defer to UserAlignment. |
| `anthropic==0.79.0` pin | **Compatible** | Out of scope | N/A | — |
| `claudechic/defaults/global/{hints,rules}.yaml` | **Diverged from §3** | Re-path on cherry-pick to `claudechic/global/`; reconcile 10-line drift on `hints.yaml` | Mechanical re-path + content review | Per-cherry-pick. |

**Path 2 totals (terminology lens):**
- **4 cherry-picks need a rename layer** (defaults adds, engine commits, fast_mode_settings.json, defaults/global YAMLs)
- **All 4 are mechanical at apply time** (D8 cooperation lets abast re-path the patches before sending; even without cooperation, `git apply --directory` + path-rewrite pass is straightforward)
- **0 invisible-to-text-merge collisions** — because sprustonlab's tree already has the §3 vocabulary, an abast cherry-pick that lands at the wrong path will *fail to apply* loudly (path doesn't exist), not succeed silently
- **Drift compounding: decreases.** Each cherry-pick converges abast content onto §3 vocabulary. After every pull, the tree is more uniform than before.

**Vocabulary unity at end of Path 2 step 1 (#23):** ✓ achieved.
**Vocabulary unity at end of Path 2 step 2 (cherry-picks):** ✓ preserved — every pull is rewritten to the canonical vocabulary at apply time.

### 4.4. Side-by-side cost summary

| Criterion | Path 1 | Path 2 |
|---|---:|---:|
| Conflicts with §3 introduced into sprustonlab tree at end of step 1 | 3 (load-bearing) | 0 |
| Renames required during step 2 | 3 + #23 surface | 0 (#23 already done) |
| Cherry-picks needing rename layer | N/A (en-masse merge instead) | 4 (one per pull) |
| Invisible-to-text-merge collisions (FDR Anomaly 3) | 1 (engine-in-workflows) | 0 |
| Vocabulary unity between steps | broken | preserved |
| Drift compounding | increases then decreases | monotonically decreases |
| D8 cooperation reduces cost? | partially (re-path before merge) | substantially (re-path before each cherry-pick) |
| Doc-surface migration ordering | doc rewrite must wait until after step 2 (no point documenting a vocabulary that will change) | doc rewrite is part of step 1 (lands once, stays) |

### 4.5. Where this lens has nothing to say

- Whether `auto` permission mode is the *right* default — UserAlignment.
- Whether the `/fast` UX is desirable — UserAlignment.
- Whether the un-pulled abast features represent a "lost work" risk per D6 — Skeptic.
- Whether the `app.py` startup-region collision is a true conflict or a code-coupling smell — Composability.
- Whether the textual conflict surface (FDR §5: 6 hot files) is small enough to treat as routine — Skeptic.
- Whether the consolidation `pyproject.toml` rewrite preserves the `anthropic` pin abast added — Skeptic + Composability (BF4 dependency-drop).

---

## 5. Lens-recommended path with rationale

**Recommendation from the terminology lens: Path 2.**

### 5.1. Rationale

The terminology lens applies a single criterion: **vocabulary unity**. A codebase with one coherent vocabulary is reviewable, documentable, and onboardable; a codebase with two co-resident vocabularies for the same concepts is none of those things.

§4.4 shows that **Path 2 maintains vocabulary unity at every step**, while Path 1 breaks it during step 1 and only re-establishes it during step 2. The cost of breaking it is real: §2c row 7 (the `workflows/` referent split) is a textually-invisible, semantically-broken merge that even careful reviewers would miss without this glossary in hand.

The asymmetry between the paths is concrete:
- **Path 1 step 1 produces a tree with three contested namespaces co-resident** (`workflows/` + `workflow_engine/` + `defaults/`) plus a stowaway engine package, *before* #23 even begins. The boundary-relocation work of #23 then has to be done on top of that compromised state.
- **Path 2 step 1 produces a tree with one canonical vocabulary** (§3 fully landed) and clean `.claudechic/` boundaries. Each abast cherry-pick in step 2 is a rename-and-apply against that stable target.

This is consistent with abast's actual contributions per §2b: abast added 7 new contested terms and re-scoped 3 more, while doing nothing to remediate BF1. Path 1's premise — "import their alignment work first" — is empirically empty; there is no alignment work on the boundary to import. Path 1 imports *only* drift.

### 5.2. The case Path 1 makes from this lens, addressed symmetrically

A Path 1 advocate could counter:

- **"Cherry-picks at apply time are higher risk than en-masse merge."** From the terminology lens: false in this specific case. The risks are inverted by §2c row 7: en-masse merge succeeds silently on the broken case (engine Python lands in YAML directory), while cherry-pick fails loudly when the directory doesn't exist. The terminology lens prefers loud failures because they are detectable.
- **"Path 2 delays abast features."** Out of scope for this lens; UserAlignment owns this.
- **"Path 1 amortises the rename across one big merge instead of N cherry-picks."** True at the rename-volume level, false at the unity level. Path 1's en-masse rename can only be performed *after* both forks' content is in the tree — i.e., only after vocabulary unity is already broken. The amortisation comes at the cost of running the codebase in a contested-vocabulary state during the entire #23 implementation window.
- **"D8 cooperation makes Path 1 cheap because abast can re-path before merging."** D8 is equally available to Path 2 (abast can re-path each cherry-pick patch). The cooperation benefit is symmetric; it does not differentially favor Path 1.

### 5.3. The case for Path 2 from this lens

- **§3 vocabulary lands on a quiet surface.** Per FDR §7d, the boundary-relocation files (`hints/state.py`, `errors.py`, `theme.py`, `agent.py`, `features/worktree/git.py`, `usage.py`, `hints/triggers.py`) are **not in either fork's divergence map**. Path 2 step 1 rewrites uncontested code; abast has nothing to lose if step 1 happens first.
- **Doc surface is sprustonlab-only (§2c.5).** Path 2 step 1 can rewrite all docs in lockstep with the code; no abast doc to merge.
- **The four BF1 violations all live in step-1-quiet files** (`config.py` is hot, but the violation is in the `CONFIG_PATH` literal at line 17, which abast's `+2/-2` does not touch). The relocation can be performed surgically.
- **Cherry-pick rename layer is a one-shot adapter, not architecture.** `git apply --directory` plus a small `sed` pass or `git filter-branch` rewrite per pull is a well-trodden pattern. Per pull, this is bounded work.
- **Skeptic's BF3 (silent semantic conflicts) is *more* likely under Path 1.** §2c row 7 is the textbook BF3: a clean text merge producing a settings system nobody designed. Path 2 turns this into a loud failure.

### 5.4. Cross-lens position

This recommendation is one input among four. The Coordinator-relayed cross-lens state is:

| Lens | Recommendation |
|---|---|
| Skeptic | Path 1 |
| Composability | Path 2 |
| **TerminologyGuardian (this glossary)** | **Path 2** |
| UserAlignment | (not yet relayed) |

Skeptic's Path 1 case (presumably: minimize the divergence surface that has to be merged when #23 lands) is a real cost that this lens does not weigh. Composability and TerminologyGuardian agree for adjacent reasons: Composability flags structural collisions (BF7 worktree symlink, layout incompatibility); TerminologyGuardian flags vocabulary collisions (`workflows/` referent split, `defaults/` namespace import, `fast_mode_settings.json` location). Both are facets of the same underlying observation — the two forks have built incompatible *systems*, not just incompatible *commits*.

### 5.5. What this lens explicitly does not claim

- That Path 2 is cheaper overall. (Cost weighting is the recommendation's synthesis pass.)
- That Path 1 is "wrong." (It is terminologically more expensive; whether that cost dominates other costs is a synthesis call.)
- That the user's preferences should be overridden. (User decides; this lens contributes evidence.)
- That the recommendation is independent of D16/D17. (D16 and D17 are now locked and have refined §3 without shifting the §5 verdict — the verdict rests on vocabulary unity, which both decisions preserve. UQ3 and UQ4 remain open and likewise do not affect the verdict; they refine §3.5/§3.6 but not §5.)

---

## Cross-references

- **STATUS.md** — D4, D5, D10 (binding), BF1, BF6, BF7 (carried forward).
- **userprompt.md** — origin of the two-clause "independent settings" definition; §3.7 operationalizes it.
- **CLAUDE.md** — current docs at `~/.claude/.claudechic.yaml` location; will need rewrite under §3.4. Per FDR Anomaly 5, doc surface is entirely sprustonlab-side and rewrites cleanly under Path 2.
- **fork_diff_report.md / fork_file_map.csv** — synthesised in §§2b, 2c, 4. Specific FDR anchors used: §3 (themes), §5 (hot files), §6 (issue surface), §7 (surface × divergence), §8 (hazards H1–H4), Anomalies 1–7.
- **Locked user decisions absorbed into §3:**
  - **D16 (was UQ1)** — "settings" vs "config" terminology resolved verbatim per the prescriptive recommendation; see §3.3.
  - **D17 (was UQ2)** — `.claudechic/config.yaml` (directory form) chosen over the file-at-root form; the global config layer collapses into per-project; see §3.2, §3.4, §3.5, §3.7.
- **Open user questions surfaced by this lens (still pending):**
  - **UQ3** (surfaced by §2c.2) — Adopt sprustonlab's `workflow_engine/` + `workflows/` (data) layout, abast's `defaults/` + `workflows/` (engine) layout, or a third merged layout? Terminology lens has no preference between the first two on linguistic grounds; strong preference *against* combining both.
  - **UQ4** (surfaced by §2c.3) — Reject `fast_mode_settings.json` as a file class, relocate it under `.claudechic/`, or carve a §3.7 exception for package-root toggles? Terminology lens recommends the first or second; against the third. Under D17, the §3.7 exception is even less attractive — the only canonical claudechic location is `<launched_repo>/.claudechic/`, so any "package-root toggle" is by definition outside the canonical namespace.
