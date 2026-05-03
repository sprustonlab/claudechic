# Fork Diff Report — `sprustonlab/claudechic` ↔ `abast/claudechic`

**Author:** GitArchaeologist (supporting agent, project-team workflow)
**Project:** `issue_23_path_eval`
**Generated:** 2026-04-25
**Companion data file:** `fork_file_map.csv` (full per-file divergence map; 272 rows)

**Decision anchors honored:**
- D1: `mrocklin/claudechic` excluded — direct sprustonlab↔abast axis only.
- D11: Issue #23 body scope and userprompt-derived boundary scope kept distinctly labeled (§6).
- D12: Default branches only (`origin/main` ↔ `abast/main`).
- D13: Direct merge-base only (no mrocklin axis).
- D14: 3–6 themes per fork.
- D15: Top-80 by churn inline (§4); full set in `fork_file_map.csv`.
- D10: No time estimates anywhere in this report.

**Scope guardrail:** read-only fork comparison; no advocacy, no recommendation. The hazard summary (§8) is a data substrate for Skeptic, not a verdict.

---

## 1. Common Ancestor (merge-base)

| Item | Value |
|---|---|
| Merge-base SHA | `285b4d120c59bd41250ca2117864cb113b5bd9b3` |
| Merge-base date | **2026-04-20  21:52:12 -0400** |
| Merge-base subject | `feat: add clear finished tasks button to TodoPanel sidebar` |
| Author of merge-base commit | (last commit shared by both forks before divergence) |

Both forks diverged from this commit on or after 2026-04-21.

---

## 2. Scale

| Metric | sprustonlab/main | abast/main |
|---|---:|---:|
| Commits ahead of merge-base | **6** | **8** |
| Files touched | **174** | **104** |
| Lines added | **13,606** | **6,583** |
| Lines deleted | **279** | **109** |
| Net lines (added − deleted) | +13,327 | +6,474 |

**Read:** sprustonlab is roughly twice the file footprint and twice the line volume of abast since merge-base. **Both are growth-dominated** (>96% of line churn is additions on each side). Almost no deletion churn means very little explicit refactoring of pre-existing files happened on either side; the divergence is mostly *new* content.

**Caveat — most divergence is concentrated in one large commit per fork:**
- sprustonlab: `317f424` ("feat: consolidate into single pip-installable package") — **166 of 174 files**.
- abast: `d55d8c0` ("feat: bundle default guardrails, hints, and workflows with fallback discovery") — **88 of 104 files**.

Each fork is essentially "one big consolidation commit + a handful of small follow-ups."

---

## 3. Themes

### sprustonlab themes (4 clusters)

| Theme | Commits | Centerpiece | Footprint |
|---|---|---|---|
| **S-T1: Package consolidation** | `317f424` | Move workflows + global hints/rules + context docs + audit + mcp_tools + workflow_engine into the installable `claudechic/` package; rename `claudechic/workflows/*.py` (engine code) to `claudechic/workflow_engine/*.py`; add `install.sh` and `install.ps1` at repo root | 166 files |
| **S-T2: Windows compatibility** | `4d77fb1`, `2675eb6` (test red), `b95313a` (test fix) | Add `encoding="utf-8"` to 15 file I/O sites; platform-guard 3 `os.kill` calls; encode project keys for Windows paths | ~13 + 3 test files |
| **S-T3: Guardrail field defaults** | `7b9b3d7` | Make guardrail `detect.field` default safely; fix sessions colon-encoding | 4 files |
| **S-T4: Bug-fix merge** | `936a8b7` (PR #17 merge) | Bundles S-T2 + S-T3 onto main | 0 file delta (merge commit) |

S-T1 dominates. S-T2/S-T3/S-T4 collectively are a single bug-fix wave.

### abast themes (5 clusters)

| Theme | Commits | Centerpiece | Footprint |
|---|---|---|---|
| **A-T1: Bundled defaults under `claudechic/defaults/`** | `d55d8c0`, `8e46bca` | Bundle workflows + global hints/rules under `claudechic/defaults/{workflows,global}/`; introduce fallback discovery so the package can find them | 88 + 1 files |
| **A-T2: "auto" permission mode + fast mode** | `7e30a53`, `5700ef5`, `26ce198`, `0ad343b` | Add `auto` to the Shift+Tab permission cycle; default startup to `auto`; add `/fast` command and `fast_mode_settings.json`; pin `anthropic` to 0.79.0 for fast-mode support | ~14 unique files (overlapping commits) |
| **A-T3: Full model-ID selection** | `f9c9418` | Loosen model validation; allow full model IDs with merge helper | 4 files |
| **A-T4: Workflow role-matching docs** | `9fed0f3` | Clarify `spawn_agent type=` parameter meaning in MCP tool docstring | 2 files |
| **A-T5: Path resolution fix** | `8e46bca` | Use resolved `workflows_dir` instead of hardcoded path (supports A-T1) | 1 file |

A-T1 dominates. A-T2 is the second-largest theme and the one most likely to live-touch app/commands code.

### Theme alignment between forks

The two largest themes (S-T1 and A-T1) **address the same underlying problem** — "how do we ship workflows + hints + rules inside the installable package?" — but landed on **incompatible directory layouts**:

| Concern | sprustonlab solution | abast solution |
|---|---|---|
| Bundled workflows path | `claudechic/workflows/` | `claudechic/defaults/workflows/` |
| Bundled global hints/rules path | `claudechic/global/` | `claudechic/defaults/global/` |
| Engine code separation | Split out to `claudechic/workflow_engine/` | (no equivalent split — kept inside `workflows/`) |
| Discovery mechanism | Direct package paths | "Fallback discovery" lookup |

This is the most consequential theme-level finding in the report; it drives §5, §7, and §8 below.

---

## 4. Per-File Divergence Map

**Tag legend:**
- `sprustonlab-only` — file changed since merge-base only on sprustonlab/main (168 files).
- `abast-only` — file changed since merge-base only on abast/main (98 files).
- `both` — file changed on **both** forks since merge-base; conflict surface (6 files).

**Totals across all 272 changed files:**

| Tag | Count |
|---|---:|
| sprustonlab-only | 168 |
| abast-only | 98 |
| both | **6** |
| **Total unique files** | **272** |

**⚠ Caveat — see §Anomalies.** The `sprustonlab-only` / `abast-only` counts include many *path-mirror pairs*: e.g., `claudechic/workflows/project_team/composability/identity.md` (sprustonlab-only) and `claudechic/defaults/workflows/project_team/composability/identity.md` (abast-only) are **byte-identical content at different paths**. Naïve text-merge tooling will see these as 2 unrelated additions; semantically they are the same file. The hazard summary (§8) treats path-mirror pairs as a single conflict surface, not two.

### Top 80 by total churn (inline)

Full list with all 272 rows is in `fork_file_map.csv`.

| # | File | Tag | sprustonlab (+/-) | abast (+/-) | total churn |
|---|------|-----|-------------------|-------------|-------------|
| 1 | `claudechic/audit/audit.py` | sprustonlab-only | +1184/-0 | - | 1184 |
| 2 | `claudechic/audit/db.py` | sprustonlab-only | +704/-0 | - | 704 |
| 3 | `claudechic/mcp_tools/_cluster.py` | sprustonlab-only | +633/-0 | - | 633 |
| 4 | `claudechic/defaults/workflows/project_team/composability/identity.md` | abast-only | - | +523/-0 | 523 |
| 5 | `claudechic/workflows/project_team/composability/identity.md` | sprustonlab-only | +523/-0 | - | 523 |
| 6 | `claudechic/mcp_tools/cluster_dispatch.py` | sprustonlab-only | +368/-0 | - | 368 |
| 7 | `claudechic/app.py` | **both** | +145/-41 | +154/-13 | 353 |
| 8 | `claudechic/defaults/workflows/project_team/lab_notebook/identity.md` | abast-only | - | +351/-0 | 351 |
| 9 | `claudechic/workflows/project_team/lab_notebook/identity.md` | sprustonlab-only | +351/-0 | - | 351 |
| 10 | `claudechic/mcp_tools/_lsf.py` | sprustonlab-only | +297/-0 | - | 297 |
| 11 | `claudechic/defaults/workflows/audit/judge/suggest.md` | abast-only | - | +275/-0 | 275 |
| 12 | `claudechic/workflows/audit/judge/suggest.md` | sprustonlab-only | +275/-0 | - | 275 |
| 13 | `claudechic/mcp_tools/_slurm.py` | sprustonlab-only | +250/-0 | - | 250 |
| 14 | `claudechic/screens/welcome.py` | sprustonlab-only | +246/-0 | - | 246 |
| 15 | `claudechic/defaults/workflows/project_team/researcher/identity.md` | abast-only | - | +239/-0 | 239 |
| 16 | `claudechic/workflows/project_team/researcher/identity.md` | sprustonlab-only | +239/-0 | - | 239 |
| 17 | `install.sh` | sprustonlab-only | +223/-0 | - | 223 |
| 18 | `tests/test_model_selection.py` | abast-only | - | +215/-0 | 215 |
| 19 | `docs/dev/remote-testing.md` | sprustonlab-only | +207/-0 | - | 207 |
| 20 | `claudechic/defaults/workflows/project_team/project_integrator/identity.md` | abast-only | - | +192/-0 | 192 |
| 21 | `claudechic/workflows/project_team/project_integrator/identity.md` | sprustonlab-only | +192/-0 | - | 192 |
| 22 | `docs/dev/analytics.md` | sprustonlab-only | +187/-0 | - | 187 |
| 23 | `tests/test_bug12_guardrails_detect_field.py` | sprustonlab-only | +178/-0 | - | 178 |
| 24 | `install.ps1` | sprustonlab-only | +175/-0 | - | 175 |
| 25 | `claudechic/defaults/workflows/tutorial_toy_project/tutorial_toy_project.yaml` | abast-only | - | +171/-0 | 171 |
| 26 | `claudechic/workflows/tutorial_toy_project/tutorial_toy_project.yaml` | sprustonlab-only | +171/-0 | - | 171 |
| 27 | `docs/dev/worktree.md` | sprustonlab-only | +167/-0 | - | 167 |
| 28 | `claudechic/defaults/workflows/project_team/user_alignment/identity.md` | abast-only | - | +156/-0 | 156 |
| 29 | `claudechic/workflows/project_team/user_alignment/identity.md` | sprustonlab-only | +156/-0 | - | 156 |
| 30 | `claudechic/defaults/workflows/tutorial_extending/learner/edit-yaml-config.md` | abast-only | - | +150/-0 | 150 |
| 31 | `claudechic/workflows/tutorial_extending/learner/edit-yaml-config.md` | sprustonlab-only | +150/-0 | - | 150 |
| 32 | `tests/test_encoding_static.py` | sprustonlab-only | +145/-0 | - | 145 |
| 33 | `claudechic/defaults/workflows/project_team/ui_designer/identity.md` | abast-only | - | +142/-0 | 142 |
| 34 | `claudechic/workflows/project_team/ui_designer/identity.md` | sprustonlab-only | +142/-0 | - | 142 |
| 35 | `claudechic/onboarding.py` | sprustonlab-only | +100/-39 | - | 139 |
| 36 | `claudechic/defaults/workflows/audit/critic/suggest.md` | abast-only | - | +138/-0 | 138 |
| 37 | `claudechic/workflows/audit/critic/suggest.md` | sprustonlab-only | +138/-0 | - | 138 |
| 38 | `claudechic/context/hints-system.md` | sprustonlab-only | +132/-0 | - | 132 |
| 39 | `tests/test_welcome_screen_integration.py` | sprustonlab-only | +129/-0 | - | 129 |
| 40 | `claudechic/defaults/workflows/project_team/memory_layout/identity.md` | abast-only | - | +128/-0 | 128 |
| 41 | `claudechic/workflows/project_team/memory_layout/identity.md` | sprustonlab-only | +128/-0 | - | 128 |
| 42 | `tests/test_config_integration.py` | sprustonlab-only | +120/-0 | - | 120 |
| 43 | `claudechic/defaults/workflows/project_team/sync_coordinator/identity.md` | abast-only | - | +119/-0 | 119 |
| 44 | `claudechic/workflows/project_team/sync_coordinator/identity.md` | sprustonlab-only | +119/-0 | - | 119 |
| 45 | `claudechic/mcp_tools/README.md` | sprustonlab-only | +118/-0 | - | 118 |
| 46 | `claudechic/defaults/workflows/project_team/skeptic/identity.md` | abast-only | - | +116/-0 | 116 |
| 47 | `claudechic/workflows/project_team/skeptic/identity.md` | sprustonlab-only | +116/-0 | - | 116 |
| 48 | `claudechic/defaults/workflows/tutorial_extending/learner/add-advance-check.md` | abast-only | - | +114/-0 | 114 |
| 49 | `claudechic/workflows/tutorial_extending/learner/add-advance-check.md` | sprustonlab-only | +114/-0 | - | 114 |
| 50 | `claudechic/defaults/workflows/project_team/implementer/identity.md` | abast-only | - | +109/-0 | 109 |
| 51 | `claudechic/workflows/project_team/implementer/identity.md` | sprustonlab-only | +109/-0 | - | 109 |
| 52 | `claudechic/defaults/workflows/project_team/test_engineer/identity.md` | abast-only | - | +107/-0 | 107 |
| 53 | `claudechic/workflows/project_team/test_engineer/identity.md` | sprustonlab-only | +107/-0 | - | 107 |
| 54 | `tests/test_bug16_sessions_encoding.py` | sprustonlab-only | +106/-0 | - | 106 |
| 55 | `claudechic/context/multi-agent-architecture.md` | sprustonlab-only | +104/-0 | - | 104 |
| 56 | `docs/dev/testing.md` | sprustonlab-only | +104/-0 | - | 104 |
| 57 | `claudechic/defaults/workflows/tutorial_extending/learner/edit-agent-role.md` | abast-only | - | +103/-0 | 103 |
| 58 | `claudechic/workflows/tutorial_extending/learner/edit-agent-role.md` | sprustonlab-only | +103/-0 | - | 103 |
| 59 | `claudechic/defaults/workflows/tutorial_toy_project/coordinator/implementation.md` | abast-only | - | +101/-0 | 101 |
| 60 | `claudechic/workflows/tutorial_toy_project/coordinator/implementation.md` | sprustonlab-only | +101/-0 | - | 101 |
| 61 | `claudechic/context/CLAUDE.md` | sprustonlab-only | +100/-0 | - | 100 |
| 62 | `claudechic/defaults/workflows/project_team/terminology/identity.md` | abast-only | - | +100/-0 | 100 |
| 63 | `claudechic/workflows/project_team/terminology/identity.md` | sprustonlab-only | +100/-0 | - | 100 |
| 64 | `claudechic/global/hints.yaml` | sprustonlab-only | +99/-0 | - | 99 |
| 65 | `docs/dev/session-files.md` | sprustonlab-only | +99/-0 | - | 99 |
| 66 | `claudechic/defaults/workflows/audit/audit.yaml` | abast-only | - | +98/-0 | 98 |
| 67 | `claudechic/workflows/audit/audit.yaml` | sprustonlab-only | +98/-0 | - | 98 |
| 68 | `claudechic/workflows/project_team/project_team.yaml` | sprustonlab-only | +93/-0 | - | 93 |
| 69 | `claudechic/defaults/global/hints.yaml` | abast-only | - | +89/-0 | 89 |
| 70 | `claudechic/defaults/workflows/project_team/README.md` | abast-only | - | +89/-0 | 89 |
| 71 | `claudechic/defaults/workflows/project_team/project_team.yaml` | abast-only | - | +89/-0 | 89 |
| 72 | `claudechic/workflows/project_team/README.md` | sprustonlab-only | +89/-0 | - | 89 |
| 73 | `claudechic/defaults/workflows/project_team/binary_portability/identity.md` | abast-only | - | +88/-0 | 88 |
| 74 | `claudechic/workflows/project_team/binary_portability/identity.md` | sprustonlab-only | +88/-0 | - | 88 |
| 75 | `claudechic/audit/README.md` | sprustonlab-only | +87/-0 | - | 87 |
| 76 | `claudechic/defaults/workflows/tutorial/tutorial.yaml` | abast-only | - | +87/-0 | 87 |
| 77 | `claudechic/workflows/tutorial/tutorial.yaml` | sprustonlab-only | +87/-0 | - | 87 |
| 78 | `claudechic/defaults/workflows/audit/auditor/identity.md` | abast-only | - | +86/-0 | 86 |
| 79 | `claudechic/defaults/workflows/cluster_setup/cluster_setup_helper/paths.md` | abast-only | - | +86/-0 | 86 |
| 80 | `claudechic/workflows/audit/auditor/identity.md` | sprustonlab-only | +86/-0 | - | 86 |

Top-80 tag distribution: 51 `sprustonlab-only`, 28 `abast-only`, 1 `both` (`claudechic/app.py`).

Items 192–272 in `fork_file_map.csv` are mostly zero-or-low churn (rename markers, single-line edits, binary placeholders) and not relevant to conflict prediction.

---

## 5. Hot Files (touched by **both** forks)

These are the only 6 files where text-level conflict is the *direct* concern.

| # | File | sprustonlab (+/-) | abast (+/-) | Total churn |
|---|---|---:|---:|---:|
| 1 | `claudechic/app.py` | +145/-41 | +154/-13 | 353 |
| 2 | `claudechic/commands.py` | +1/-1 | +57/-14 | 73 |
| 3 | `claudechic/config.py` | +56/-0 | +2/-2 | 60 |
| 4 | `pyproject.toml` | +16/-3 | +1/-1 | 21 |
| 5 | `claudechic/mcp.py` | +10/-8 | +1/-1 | 20 |
| 6 | `tests/conftest.py` | +6/-0 | +1/-1 | 8 |

### Per-hot-file commit attribution

| File | sprustonlab commits | abast commits |
|---|---|---|
| `claudechic/app.py` | `317f424` (consolidation), `4d77fb1` (Windows utf-8) | `26ce198` (/fast), `5700ef5` (auto perm startup), `7e30a53` (auto perm Shift-Tab), `f9c9418` (full model id), `8e46bca` (path fix), `d55d8c0` (defaults bundle) |
| `claudechic/commands.py` | `4d77fb1` (Windows utf-8) | `26ce198` (/fast), `5700ef5` (auto perm startup), `f9c9418` (full model id) |
| `claudechic/config.py` | `317f424` (consolidation) | `5700ef5` (auto perm startup) |
| `pyproject.toml` | `317f424` (consolidation, big rewrite) | `0ad343b` (pin anthropic 0.79.0) |
| `claudechic/mcp.py` | `317f424` (consolidation) | `9fed0f3` (docstring clarification) |
| `tests/conftest.py` | `317f424` (consolidation) | `5700ef5` (auto perm startup) |

### Hot-file shape commentary (purely descriptive)

- **`app.py`** is the largest hot file by far. sprustonlab's churn is mostly the consolidation + Windows utf-8 sites; abast's is the new "auto" permission UX wired into startup, Shift+Tab, `/fast`, and full-model-ID flows, plus a defaults-bundle hookup. The two changesets touch *different functions* but both insert near startup/init regions.
- **`commands.py`** — abast adds `/fast` and the auto-perm command; sprustonlab only touched it for Windows utf-8. Almost entirely an abast-side feature add.
- **`config.py`** — sprustonlab heavily added (+56 lines) during consolidation; abast made a 2-line tweak for auto-perm. Sprustonlab change pattern matches the directory layout of the consolidation theme.
- **`pyproject.toml`** — sprustonlab rewrote it (+16/−3) as part of becoming pip-installable; abast only bumped the `anthropic` pin. abast's tiny change will likely be obsolete or in-conflict against sprustonlab's rewrite.
- **`mcp.py`** — sprustonlab's churn is path adjustments; abast's is a docstring clarification.
- **`conftest.py`** — both forks added small fixtures; abast's fixture is for permission-mode tests.

---

## 6. Issue #23 Surface Characterization

Issue: `sprustonlab/claudechic#23` — "Settings window + configuration reference documentation".

### 6a. Issue body scope (what `gh issue view 23` actually names)

The issue body explicitly names the following *deliverables*:

- A `/settings` TUI screen accessible from welcome screen or via `/settings` command.
- A new doc file: `docs/configuration.md` — single-page reference of all config keys, env vars, CLI flags.

It explicitly enumerates *config keys* expected to be exposed:
- **Global config keys** (in `~/.claude/.claudechic.yaml` per the issue body's framing):
  `default_permission_mode`, `show_message_metadata`, `vi-mode`, `recent-tools-expanded`,
  `worktree.path_template`, `analytics.enabled`, `logging.file`, `logging.notify-level`, `themes`.
- **Internal-only keys** (do *not* expose): `analytics.id`, `experimental`.
- **Project config keys** (in `.claudechic.yaml`): `guardrails`, `hints`, `disabled_workflows`, `disabled_ids`.
- **Environment variables**: `CLAUDECHIC_REMOTE_PORT`, `CHIC_PROFILE`, `CHIC_SAMPLE_THRESHOLD`, `CLAUDE_AGENT_NAME`, `CLAUDE_AGENT_ROLE`, `CLAUDECHIC_APP_PID`, `ANTHROPIC_BASE_URL`.

The issue body is descriptive about *what to expose*, not *where the config files live*. The path `~/.claude/.claudechic.yaml` is referenced, but no relocation is requested by the issue body itself.

The issue body links to `#21` ("Feature: Settings page in welcome screen for `.claudechic.yaml` editing"). #21 confirms the welcome-screen entry point and `.claudechic.yaml` as the project-level toggle file. **No comments on either issue at time of writing.**

There are no explicit out-of-scope notes in the issue body other than the implicit "internal-only keys not exposed" carve-out.

### 6b. Userprompt-derived boundary scope (NOT in the issue body verbatim)

The userprompt for this evaluation introduces a *separate, additional* concern that is **not present in the issue body**:

- **Boundary rule (a):** *"Don't mix Claude settings and claudechic settings."* I.e., anything in `.claude/` or `~/.claude/` is Claude's namespace; claudechic must stay out entirely.
- **Boundary rule (b):** *"Don't put anything (except a `.claudechic/` folder) in the root of the repo we're launching the tool in."*

This implies *relocation* work that the issue body does not call out:
- `~/.claude/.claudechic.yaml` → must move out of `~/.claude/` (e.g., `~/.config/claudechic/config.yaml` or `~/.claudechic/config.yaml`).
- `.claude/hints_state.json` → must move out of any `.claude/` directory (e.g., `.claudechic/hints_state.json`).
- Any other claudechic-owned files currently dropped into `.claude/` must move under `.claudechic/`.

(BF1 in STATUS.md already records that the current code violates this rule.)

### 6c. Inferred file/module surface

#### 6c.i. Surface for §6a (issue body scope — settings screen + docs reference)

Based on `git ls-tree` over the current sprustonlab tree and `git grep` for `claudechic.yaml` / `.claude/` references, the files most likely touched by the §6a deliverables are:

| File | Why it's likely touched |
|---|---|
| `claudechic/screens/` (new file: e.g. `settings.py`) | New `/settings` screen lives here per existing screen pattern |
| `claudechic/screens/welcome.py` | Welcome-screen entry point to settings |
| `claudechic/commands.py` | `/settings` command registration |
| `claudechic/config.py` | Config-key schema, validation, defaults — must enumerate every exposed key |
| `claudechic/app.py` | Wire screen mount, command routing, startup invariants |
| `docs/configuration.md` (new) | Single-page configuration reference |
| `docs/CLAUDE.md` / `claudechic/context/CLAUDE.md` | Cross-link to the new reference page |
| `tests/test_config*.py` (existing: `test_config.py`, `test_config_integration.py`, `test_worktree_config.py`) | Settings round-trip and validation tests |
| `tests/test_welcome_screen_integration.py` | Settings entry point coverage |

#### 6c.ii. Surface for §6b (boundary scope — relocate `.claudechic.yaml` out of `~/.claude/`)

`git grep` shows the following sprustonlab files reference paths under `~/.claude/` and/or the literal `claudechic.yaml`:

| File | Reference type |
|---|---|
| `claudechic/config.py` | reads/writes `~/.claude/.claudechic.yaml` (BF1 violation) |
| `claudechic/agent.py` | references `~/.claude/` (likely SDK-side) |
| `claudechic/app.py` | references `~/.claude/` |
| `claudechic/commands.py` | references `~/.claude/` |
| `claudechic/errors.py` | references `~/.claude/` and `claudechic.yaml` |
| `claudechic/features/worktree/git.py` | references `~/.claude/` |
| `claudechic/hints/state.py` | writes `.claude/hints_state.json` and `~/.claude/...` (BF1 violation) |
| `claudechic/hints/triggers.py` | references `~/.claude/` |
| `claudechic/history.py` | reads `~/.claude/history.jsonl` (Claude-owned — should remain) |
| `claudechic/sessions.py` | reads `~/.claude/projects/...` session files (Claude-owned — should remain) |
| `claudechic/theme.py` | references `~/.claude/` and `claudechic.yaml` |
| `claudechic/usage.py` | references `~/.claude/` |

**Distinction within §6b surface:** Some `~/.claude/` references are *legitimately reading Claude's namespace* (`history.py`, `sessions.py` — reading Claude's own session/history files for display). Those should NOT be relocated by #23. The relocation surface is the *write* sites under `~/.claude/` for claudechic-owned state — primarily `config.py`, `hints/state.py`, `errors.py`, `theme.py`. (TerminologyGuardian will need to call this distinction on its own; it is not GitArchaeologist's role to draw the boundary.)

#### 6c.iii. Issue-body-named vs inferred

| Item | Status |
|---|---|
| `/settings` TUI screen | **Body-named** (existence); **inferred** (file path) |
| `docs/configuration.md` | **Body-named** (full path) |
| Config key list (the table in the issue) | **Body-named** |
| Files to modify for the screen | **Inferred** (issue body lists no target files) |
| Relocation of `~/.claude/.claudechic.yaml` | **Userprompt-derived only**, not in issue body |
| Relocation of `.claude/hints_state.json` | **Userprompt-derived only**, not in issue body |
| `~/.claude/`-reading files that should *stay* | **Inferred** (boundary judgment, not specified anywhere) |

---

## 7. Issue #23 Surface × Fork Divergence

Each row below intersects a §6c file with the divergence map (§4).

### 7a. Files in §6c that are also `both` (hot files)

| File | Surface origin | Hot-file rank |
|---|---|---|
| `claudechic/app.py` | §6c.i + §6c.ii | #1 hot file |
| `claudechic/commands.py` | §6c.i + §6c.ii | #2 hot file |
| `claudechic/config.py` | §6c.i + §6c.ii | #3 hot file |

**All three of #23's most "live" code-touch sites are already hot files.**

### 7b. Files in §6c that are `sprustonlab-only` (sprustonlab already changed since merge-base)

| File | Surface origin | Sprustonlab change kind |
|---|---|---|
| `claudechic/agent.py` | §6c.ii | (not in divergence map — unchanged on sprustonlab — see §7d) |
| `claudechic/errors.py` | §6c.ii | not in divergence map (sprustonlab-unchanged) |
| `claudechic/features/worktree/git.py` | §6c.ii | not in divergence map |
| `claudechic/hints/state.py` | §6c.ii | not in divergence map |
| `claudechic/hints/triggers.py` | §6c.ii | not in divergence map |
| `claudechic/screens/welcome.py` | §6c.i | sprustonlab-only (+246, brand-new) |
| `claudechic/theme.py` | §6c.ii | not in divergence map |
| `claudechic/usage.py` | §6c.ii | not in divergence map |
| `tests/test_config.py` | §6c.i | both (small) — actually `both` (auto-perm test on abast side) |
| `tests/test_config_integration.py` | §6c.i | sprustonlab-only (+120 — added during S-T1) |
| `tests/test_worktree_config.py` | §6c.i | not in divergence map |
| `tests/test_welcome_screen_integration.py` | §6c.i | sprustonlab-only (+129) |
| `claudechic/context/CLAUDE.md` | §6c.i | sprustonlab-only (+100) |

**Observation:** the sprustonlab-side §6c surface is concentrated in files that **were not touched in either fork's divergent commits** (the boundary-rewrite candidates: `agent.py`, `errors.py`, `theme.py`, `hints/state.py`, etc.). That means #23's relocation work mostly does **not** collide textually with abast's divergent commits — it lives in pre-merge-base code that both forks left alone.

### 7c. Files in §6c that are `abast-only`

| File | Surface origin | abast change kind |
|---|---|---|
| `tests/test_config.py` | §6c.i | (correction — actually `both`) |

(`config.py` is `both`; tests in `test_config*` see mostly sprustonlab-side adds.)

### 7d. Files in §6c that are *not in either fork's divergence map*

These are the "quiet" relocation targets that should be cheapest to rewrite under #23 (no recent contention from either fork):

- `claudechic/agent.py` (boundary surface only)
- `claudechic/errors.py`
- `claudechic/features/worktree/git.py`
- `claudechic/hints/state.py`
- `claudechic/hints/triggers.py`
- `claudechic/theme.py`
- `claudechic/usage.py`
- `claudechic/history.py` *(should NOT be relocated — reads Claude-owned history)*
- `claudechic/sessions.py` *(should NOT be relocated — reads Claude-owned sessions)*

(Inclusion in the abast divergence map was double-checked against the §4 dataset.)

### 7e. Mirror-pair surface (semantic, not textual)

Many of the §6c.i tests/screen surface files have **no mirror-pair on the abast side**, because abast's bundling lives entirely under `claudechic/defaults/` (see §3 / §8). This means:

- The *settings screen* feature (§6a) lives on sprustonlab in places abast did not touch.
- BUT abast's `claudechic/defaults/global/hints.yaml` may need to be merged with sprustonlab's `claudechic/global/hints.yaml` *first* before `#23` can describe the canonical hints surface in `docs/configuration.md`. This is a §8 hazard.

---

## 8. Hazard Summary — Path 2 conflict surface

This section is data input for Skeptic. **It is not a recommendation.** Every entry is a file (or file-set) where building issue #23 first on sprustonlab and then attempting selective pulls from abast creates a substantive integration risk.

Hazard tiers:
- **H1 (load-bearing collision):** the file/asset is on the §6c surface AND already a hot file or its mirror-pair counterpart. Path 2 work will overwrite or be overwritten.
- **H2 (semantic-layout collision):** path-mirror pair where both forks bundled the same content under different paths. Cherry-pick will not raise text conflicts but the result will be broken.
- **H3 (ambient drift):** small-but-nonzero abast-side touches in files #23 will rewrite; cherry-pick still possible but requires re-application.
- **H4 (deliberate non-pull risk, BF5):** abast feature whose code overlaps the #23 surface but which sprustonlab may *choose not to take* — must be explicitly named so Skeptic can decide.

### H1 — Load-bearing collisions (high attention)

| File | Why it's H1 |
|---|---|
| `claudechic/app.py` | #1 hot file (353 churn); listed in both §6c.i (settings screen wiring) and §6c.ii (boundary wiring). #23 must rewrite the startup region; abast has 4 of 8 commits that *also* touch the startup region (auto-perm default, Shift+Tab cycle, /fast, full-model-id). Path 2 means re-applying ~167 lines of abast feature code on top of #23's rewrite of startup. |
| `claudechic/commands.py` | #2 hot file. abast adds `/fast` and auto-perm command; #23 must add `/settings` command. Both touch the same command-registration table. |
| `claudechic/config.py` | #3 hot file. sprustonlab already rewrote +56 lines for consolidation; #23 will rewrite this file *again* for the relocation (move `~/.claude/.claudechic.yaml` → new location) and for the settings-key schema; abast's 2-line auto-perm tweak must be re-applied on top. |

### H2 — Semantic-layout collisions (the dominant Path 2 hazard)

The single largest semantic risk in this evaluation. Both forks bundled equivalent content at incompatible paths:

| sprustonlab path (S-T1) | abast path (A-T1) | Content state |
|---|---|---|
| `claudechic/global/hints.yaml` | `claudechic/defaults/global/hints.yaml` | **Drift:** sprustonlab has 10 extra trailing lines (`context_docs_outdated` upgrade-drift hint). |
| `claudechic/global/rules.yaml` | `claudechic/defaults/global/rules.yaml` | (mirror — verify byte-equality before any pull) |
| `claudechic/workflows/<wf>/...` (89 files) | `claudechic/defaults/workflows/<wf>/...` (85 files) | **Mostly identical content; ~95% mirror.** Spot-checked `composability/identity.md`, `lab_notebook/identity.md`, `tutorial/tutorial.yaml` — byte-identical. `project_team/project_team.yaml` has a small drift (sprustonlab uses `python -c "import glob; ..."`, abast uses `ls`; sprustonlab adds extra `detect.field` rules). |
| `claudechic/workflow_engine/*.py` | (no equivalent on abast — engine code stayed in `claudechic/workflows/*.py`) | **Renamed by sprustonlab** (`R080`/`R099`/`R100` rename markers in `317f424`); abast still has the old path. |

**The core hazard:** if Path 2 builds #23 first on sprustonlab (which uses the `claudechic/workflows/` + `claudechic/global/` layout) and *then* cherry-picks abast feature commits, every abast commit that touches `claudechic/defaults/...` will land at the wrong path. Cherry-picks will either:
1. Apply cleanly (because the `defaults/` paths don't yet exist on sprustonlab) and create a *parallel duplicate tree* of bundled assets at the wrong layout — silently broken (BF3 territory), or
2. Conflict with the loader code that sprustonlab wired to find assets at the consolidation paths.

D8 (abast cooperation available) is directly relevant here: re-pathing abast's `claudechic/defaults/` adds before applying them is the de-risking move.

**H2 file-set summary** (all path-mirror pairs from §4 — 87 abast-only `claudechic/defaults/...` adds, vs ~85 sprustonlab-only `claudechic/{workflows,global}/...` adds; full list in `fork_file_map.csv`).

### H3 — Ambient drift

| File | Why it's H3 |
|---|---|
| `pyproject.toml` | sprustonlab rewrote (+16/−3) for pip-install; abast bumped `anthropic` to 0.79.0. Path 2 must verify the consolidation `pyproject.toml` carries (or compatibly tightens) the `anthropic` pin abast added — otherwise `/fast` mode silently breaks. |
| `claudechic/mcp.py` | sprustonlab churn (+10/−8) is path-related; abast churn (+1/−1) is a docstring. Trivial cherry-pick after H1/H2 are settled. |
| `tests/conftest.py` | sprustonlab adds 6 lines (consolidation); abast adds 1 (auto-perm fixture). Trivial. |

### H4 — Deliberate non-pull candidates (BF5)

The team must explicitly decide what *not* to take from abast. The decision is Skeptic's, but the candidates the data substrate exposes are:

| abast change | Reason it might be a non-pull |
|---|---|
| `claudechic/fast_mode_settings.json` (new file with `{"fastMode": true}`) | Hard-coded "fast mode" toggle — overlaps with #23's settings system; pulling it as-is forces `#23` to absorb a parallel toggle file rather than designing one. |
| `26ce198` (`/fast` command) | Tightly coupled to `fast_mode_settings.json`; semantic alignment with #23's settings model needed before pulling. |
| `5700ef5` (auto perm mode default at startup) | Changes default permission semantics; userprompt-level decision. |
| `7e30a53` (auto perm Shift+Tab cycle) | UI-level UX change; may or may not align with sprustonlab's UX direction. |
| `f9c9418` (loosened model validation, full model IDs) | Validation policy change; may interact with #23's validation surface for the `themes` / `default_permission_mode` keys. |
| `0ad343b` (`anthropic==0.79.0` pin) | Required *only* if `/fast` is taken (Theme A-T2 dependency cluster); BF4 dependency-drop applies. |
| Entire `claudechic/defaults/` tree (A-T1) | If sprustonlab keeps its consolidation layout (S-T1), this whole tree should be **non-pulled** as paths and instead **content-merged** into the sprustonlab paths. |

### What this section does NOT do

- It does not rank Path 1 vs Path 2.
- It does not say which H4 items to pull or not pull.
- It does not estimate effort, complexity, or duration of any path.
- It does not assess "lost work" probability per D6.

Those are Composability / Skeptic / UserAlignment outputs; this section is their input.

---

## Anomalies (surprised me during data collection)

1. **Path-mirror double-counting.** The `sprustonlab-only` (168) and `abast-only` (98) tag counts substantially **overstate** independent surface area. Roughly 85 abast-only `claudechic/defaults/...` files are byte-near-identical mirrors of 85 sprustonlab-only `claudechic/{workflows,global}/...` files. Removing path-mirrors, abast's *truly independent* file footprint shrinks to ~13–15 files (auto-perm UX, /fast, model-ID validation, conftest, pyproject pin). Naïve diff tooling will dramatically over-estimate the divergence.
2. **Extremely few `both` files (6).** Given two forks each ~100+ files of churn, it is unusual for the conflict surface to be only 6 textually-overlapping files. This is a *deceptive* signal — the real conflict surface is the H2 layout collision (~85 mirror pairs), not the textual hot files.
3. **`workflows/` directory means different things on each side.** On sprustonlab post-consolidation, `claudechic/workflows/` is **YAML data only** (the engine code moved to `claudechic/workflow_engine/`). On abast, `claudechic/workflows/` *still contains the engine Python* (no `workflow_engine/` directory). A naïve cherry-pick of an abast commit touching `claudechic/workflows/loader.py` will land in the wrong directory on sprustonlab.
4. **abast lacks several modules sprustonlab adds:** `claudechic/audit/`, `claudechic/mcp_tools/`, `claudechic/context/`, `claudechic/workflow_engine/`, `claudechic/onboarding.py`. These are pure adds on sprustonlab; no abast-side conflict source for them.
5. **Issue #23 / userprompt scope gap is real and load-bearing (BF6 confirmed).** The settings-screen + docs reference work in the issue body and the boundary relocation work in the userprompt overlap *only at* `config.py`, `app.py`, `commands.py`, and the test files. The boundary work's biggest surface (`hints/state.py`, `errors.py`, `theme.py`, `agent.py`, etc.) is **not in the issue body at all** — Leadership should be explicit about which scope the path recommendation is sequencing.
6. **abast's `pyproject.toml` change (`anthropic==0.79.0`) is a minor pin, but `/fast` depends on it (BF4 dependency-drop concrete instance).** Pulling `26ce198` without `0ad343b` would land `/fast` against an incompatible SDK.
7. **`claudechic/screens/welcome.py` is sprustonlab-only +246 lines.** This is the entry point #21/#23 most likely modify (issue #21 explicitly says "accessible from welcome screen"). It is *also* part of the consolidation theme S-T1, so #23 will be editing brand-new sprustonlab code without abast-side history to merge.

---

## Appendix: Commands used (read-only audit trail)

```
git remote add abast https://github.com/abast/claudechic.git
git fetch abast
git fetch origin main
git merge-base origin/main abast/main
# returns 285b4d120c59bd41250ca2117864cb113b5bd9b3
git log --format="%h %ad %s" --date=short 285b4d1..origin/main
git log --format="%h %ad %s" --date=short 285b4d1..abast/main
git diff --shortstat 285b4d1 origin/main
git diff --shortstat 285b4d1 abast/main
git diff --numstat 285b4d1 origin/main > /tmp/forkdiff/spruston.numstat
git diff --numstat 285b4d1 abast/main > /tmp/forkdiff/abast.numstat
# Python: tag each file sprustonlab-only / abast-only / both, sort by total churn
git ls-tree -r --name-only origin/main claudechic/{workflows,global,defaults}/
git ls-tree -r --name-only abast/main claudechic/{workflows,global,defaults}/
git show --pretty="" --name-status 317f424   # sprustonlab consolidation
git show --pretty="" --name-status d55d8c0   # abast defaults bundle
git grep -l "\.claude/" origin/main -- 'claudechic/*.py'
git grep -l "claudechic\.yaml" origin/main -- 'claudechic/*.py'
git grep -l "\.claude/" abast/main -- 'claudechic/*.py'
# Spot-checked path-mirror pairs for byte-equality:
diff <(git show origin/main:claudechic/workflows/project_team/composability/identity.md) \
     <(git show abast/main:claudechic/defaults/workflows/project_team/composability/identity.md)
# (and similar for lab_notebook, tutorial.yaml, project_team.yaml, global/hints.yaml)
gh issue view 23 --repo sprustonlab/claudechic --comments
gh issue view 21 --repo sprustonlab/claudechic
```

No pushes, no branches created, no commits, no merges. Working tree unchanged. The only repository-state side effect is one new local git remote (`abast`) and its fetched refs, both read-only.
