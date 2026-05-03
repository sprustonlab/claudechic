# Vision — Independent claudechic Settings (issue #24)

**For a fresh project-team workflow run.** This document captures user intent and locked constraints. It deliberately does *not* prescribe mechanisms — implementation choices are for the new team to design.

A prior project-team run (`.project_team/issue_23_path_eval/`) explored the surrounding problem space and produced useful background (fork-diff data, four lens evaluations, a recommendation document). That run was scoped before issue #24 was fully read; it focused on the cross-fork merge sequencing and BF1 boundary work in isolation. **The new team should treat the prior run's analysis as available reference material, not as a binding plan.** Some conclusions from that run carry forward (locked decisions section below); the architectural shape from #24 changes the rest.

---

## Goal (one sentence)

Restructure claudechic so that workflows, rules, hints, and MCP tools are layered across three override tiers (package, user, project — project wins), claudechic-owned state lives only in `.claudechic/` directories (never inside `.claude/`), and agents running inside claudechic understand the environment they're in.

---

## Why this matters

claudechic today mixes its own state into Claude Code's `.claude/` namespace, has no user-tier override mechanism, and assumes every install is identical. As lab forks have diverged (sprustonlab and abast in particular), the lack of a clean layered model has caused them to solve the same problems at incompatible paths and to lose the ability to share customization without conflict. A 3-tier override system gives users a clean way to customize claudechic without modifying the package, gives projects a way to express project-specific rules without affecting other projects, and gives the package a clear role as the floor of fallback defaults.

The boundary work matters because Claude Code itself owns `.claude/`. claudechic writing into it creates coupling that will break the moment Claude Code changes its conventions, and creates confusion for users about who owns what file. Cleaning the boundary makes claudechic behave like a well-mannered tool rather than an extension of Claude.

---

## What we want (intent, not mechanism)

### 1. Three-tier override system for content

Three tiers, in order from lowest to highest priority:

- **Package tier** — defaults that ship with the claudechic Python package, available everywhere claudechic is installed.
- **User tier** — overrides per user, applied across every project that user works in.
- **Project tier** — overrides per project, applied only inside the project where they're configured.

When the same content (a workflow definition, a rule, a hint, an MCP tool) is defined at more than one tier, project beats user beats package. When content is unique to a tier, it's available regardless of what's at the other tiers.

The tiers cover four categories of content:

- Workflows
- Rules
- Hints
- MCP tools

(Rules and hints are conceptually paired — together they make up the "global" manifest section in the existing codebase. Whether they're a single directory or two siblings is a mechanism choice.)

### 2. Two-tier override system for config keys

Configuration keys (the things issue #23 lists for the settings UI — `default_permission_mode`, `analytics.enabled`, `worktree.path_template`, `themes`, etc.) are layered across user and project. There is no package config file; defaults live in code.

User-level config keys (which apply across all projects) include things like analytics identity, default permission mode, theme, logging, worktree path template. Project-level config keys (which apply only in the launched repo) include feature toggles like `guardrails`, `hints`, `disabled_workflows`, `disabled_ids`.

### 3. The boundary

Claudechic must never write any file inside any `.claude/` directory — at home, in the launched repo, in worktrees, anywhere. Reading from Claude-owned paths (`~/.claude/settings.json`, the projects-history JSONL files, OAuth credentials, Claude's own command/skill/rule directories) is fine and must continue to work.

The launched repo's root must contain at most one claudechic-authored entry: a `.claudechic/` directory. The existing top-level `.claudechic.yaml` file pattern is replaced by `.claudechic/config.yaml` inside the directory.

When the package needs to make claudechic-shipped content visible to Claude (currently done by installing context docs into `<launched_repo>/.claude/rules/`), it does so without writing into `.claude/`. claudechic does not touch `.claude/rules/` — that directory belongs to the repo owner. Whatever mechanism the team picks for surfacing claudechic context to agents must respect this boundary.

### 4. Agent awareness

When an agent runs inside claudechic, it should understand:

- It's running inside a TUI wrapper around Claude Code (not bare Claude).
- claudechic adds **guardrails** that may intercept its tool calls.
- claudechic adds **workflows** with **phases** — multi-step coordinated processes the agent may be part of.
- claudechic adds **hints** — short user-facing nudges.
- claudechic-owned content lives under `.claudechic/`; `.claude/` is Claude Code's namespace.

Two pieces of awareness are needed, with different timing:

- **Always, at session start** — a short prompt-level statement of the above (a few sentences), so every agent starts with baseline claudechic-awareness without conditioning on file reads.
- **Once per agent, on first read in a claudechic folder** — fuller context (the package's own documentation about workflows, hints, guardrails) injected the first time that agent reads a file inside a claudechic-owned directory. After the first such read, no further injections to that agent. The intent is "give the agent the deeper context the moment it actually needs it, but don't repeat."

The "first read only" semantics matter. The new team should not implement per-read injection (that would be noisy); the trigger is once-per-agent-session.

### 5. Settings UI and configuration reference (issue #23 deliverables)

Two artifacts ship as part of this work:

- **A `/settings` TUI screen** (or "settings button at the bottom" of the chat UI per #24) that exposes user-facing configuration keys for editing. Issue #23 enumerates which keys to expose and which to keep internal (`analytics.id`, `experimental.*`).
- **A configuration reference page** at `docs/configuration.md` documenting every config key, every environment variable, and every CLI flag claudechic responds to.

Plus a "workflow button" surface (per #24) that lets the user see and select workflows from all three tiers, distinguishing where each came from.

### 6. Workflow artifact directories

Workflows often have a setup phase that produces files (specifications, status documents, plans, hand-off material) for downstream agents to read. The setup phase needs a designated artifact directory to write those files to, and the workflow engine needs to make that directory visible to subsequent agents in the workflow run.

The new team will need to decide where artifact dirs live, how they're named, how they survive across phases, and how they're surfaced to spawned agents. The intent is that an Implementer or Tester agent in a workflow run can find and read the spec files the setup phase wrote, without the user having to plumb that manually.

### 7. Selective integration with abast

The abast/claudechic fork has diverged from sprustonlab/claudechic, and abast has independently built a layered-defaults pattern (`claudechic/defaults/...`) that overlaps with what we're building here. We want to:

- Selectively pull useful features abast has shipped (auto-permission UX improvements, model-ID validation work, documentation clarifications) onto our tree.
- Not pull `/fast` mode for now (deferred to issue #25).
- Coordinate with abast on convergence so we don't drift further. abast has indicated willingness to align on layout direction during this work.

How exactly to do this — restructure first then pull, pull first then restructure, abast rebases their work onto our layout, etc. — is the new team's call. The prior run's RECOMMENDATION.md analyzed several sequencing options and may be useful background.

---

## Success looks like

- A user can put files in `~/.claudechic/workflows/foo/` and have them override the package's `foo` workflow without modifying any project. They can also put a `<launched_repo>/.claudechic/workflows/foo/` to override at project scope, and that beats the user-level override. The same is true for rules, hints, and MCP tools.
- A user can edit per-user config in their `/settings` UI (or directly in `~/.claudechic/config.yaml`) and have it apply to every project they work in. They can edit per-project config and have it apply only there.
- After the work, claudechic creates and modifies files only inside `.claudechic/` directories. The boundary holds in CI (an automated test catches any new violation).
- An agent's first message inside a claudechic session contains a short statement that it's in a TUI with guardrails / workflows / hints. The first time the agent reads from inside any `.claudechic/` folder, it receives fuller context about how those folders are structured.
- The settings TUI screen exposes the keys issue #23 enumerates. The `docs/configuration.md` reference page documents the full configuration surface.
- Issue #23 and issue #24 can both be closed.
- abast's selected commits are in our tree; the unselected ones are recorded with rationale; abast is not surprised by anything we did.
- The new team can hand off to Implementer + Tester agents who execute the spec without needing to read the recommendation document or the lens evaluations.

## Failure looks like

- The 3 tiers exist in the file system but resolution doesn't actually layer (e.g., user-level overrides don't apply, or project-level doesn't beat user-level).
- Config keys land in the wrong tier (project-level keys leaking into user-level, or vice versa).
- claudechic still writes to `.claude/` after the work — even one file, even one path.
- Agents have no idea they're in a TUI; the prompt injection either doesn't fire or contains too much / too little.
- The "once per agent" semantics for the first-read-context injection slip into per-read (noisy) or never (useless).
- Settings UI only exposes some of the keys issue #23 lists, or exposes internal keys that should be hidden.
- The cross-fork merge with abast loses feature work (commits get reverted in conflict resolution, behavior subtly changes after merge, abast's intent gets lost).
- The artifact dir mechanism is so awkward that workflow authors avoid it.
- The new team produces a spec that mixes operational instructions with rationale (Implementer/Tester can't execute without reading the appendix) — this is a known anti-pattern from the prior run; the new team's grading rubric should catch it.

---

## Locked constraints (do not re-litigate)

These are decisions the user has already made. The new team should treat them as binding and proceed.

- **L1.** mrocklin/claudechic upstream is out of scope. No upstream-first option exists.
- **L2.** Integration with abast is selective only — never an all-or-nothing merge.
- **L3.** Claudechic must never write any file inside any `.claude/` directory.
- **L4.** "Settings" is the user-facing umbrella term (TUI screen, prose, button labels). "Config" is the technical term (YAML file, loader code, dataclass names). No code-symbol renames are forced.
- **L5.** The launched-repo's root contains at most one claudechic-authored entry: a `.claudechic/` directory. The existing top-level `.claudechic.yaml` file is replaced by `.claudechic/config.yaml`.
- **L6.** User-tier `.claudechic/` lives at `~/.claudechic/` (mirrors Claude's `~/.claude/` pattern; not XDG).
- **L7.** Each tier's `.claudechic/` directory follows the layout abast already adopted: `workflows/`, `global/` (containing `rules.yaml` and `hints.yaml`), `mcp_tools/`. The package tier under the existing `claudechic/defaults/...` pattern.
- **L8.** Config keys are 2-tier (user + project). Defaults live in code. There is no `claudechic/defaults/config.yaml`.
- **L9.** `analytics.id` lives at user-tier (stable across projects).
- **L10.** "Lost work" includes all four senses (commits never on main; features non-functional post-merge; features reverted in conflict resolution; intent lost even if code survives). Risk analysis must address all four.
- **L11.** abast cooperation is available and should be leveraged. abast has indicated willingness to converge on layout direction.
- **L12.** `/fast` mode from abast is not being pulled in this run (filed at sprustonlab/claudechic#25).
- **L13.** No time estimates in any deliverable. Process detail throughout.
- **L14.** Spec documents are strictly operational (Implementer + Tester can execute without reading anything else). Rationale, decisions, rejected paths, and reversal triggers go in a separate appendix file. Recommendation/deliberation documents and spec documents are different files for different audiences. The grading rubric must enforce this.
- **L15.** Two-piece agent awareness: short always-on injection at session start, plus once-per-agent fuller-context injection on first read in a `.claudechic/` folder. "Once per agent" means once per agent-session, not per read.
- **L16.** Cherry-pick selection from `abast/main` is decided. The new team does **not** re-survey or re-decide.

  **Pull (decided):**
  | Commit | What it does |
  |---|---|
  | `9fed0f3` | Docs clarification on `spawn_agent type=` parameter |
  | `8e46bca` | Fix: use resolved `workflows_dir` instead of hardcoded path |
  | `d55d8c0` (selective) | Manifest loader fallback-discovery logic only — the loader code, not the bundled YAML content (sprustonlab gets the YAML through the restructure, not from this commit) |

  **Skip (decided, with rationale):**
  | Commit | Reason |
  |---|---|
  | `26ce198` (`/fast` command) | Deferred to [sprustonlab/claudechic#25](https://github.com/sprustonlab/claudechic/issues/25) |
  | `0ad343b` (anthropic 0.79.0 pin) | Only needed for `/fast`; deferred with `/fast` |
  | `claudechic/fast_mode_settings.json` (introduced in `26ce198`) | Bundled with `/fast`; deferred with `/fast` |

  **UX-decision-required (not yet decided; user will resolve before pull execution; new team treats as a known gate, not a design question):**
  | Commit | Description |
  |---|---|
  | `f9c9418` | Full model ID + loosened validation — pull only if user decides to adopt this UX feature |
  | `5700ef5` | Default to `auto` permission mode on startup — pull only if user decides to make `auto` the default |
  | `7e30a53` | Add `auto` to Shift+Tab cycle — bundled with `5700ef5`; pull-or-skip together |
- **L17.** No upgrade-migration logic is required. claudechic's only current users are the issue-author and Arco (abast); both can manually move files if needed. The new team should not spend design effort on automatic migration of existing `~/.claude/.claudechic.yaml`, `<repo>/.claude/hints_state.json`, etc. into the new layout.

---

## Open for the new team to decide (mechanisms)

Everything not in the locked list is fair game. Specifically:

- **The path order for the work.** **User preference: restructure first** — restructure sprustonlab to the converged 3-tier layout, then selectively pull from abast (per L16), then implement #23 / #24. The new team can deviate from this preference but should justify any deviation in their analysis (the prior run's recommendation also pointed to layout-convergence-first; #24's 3-tier model is a further reason to converge layouts before any pull).
- **The override-resolution mechanism** in the loader — how exactly the 3 tiers are walked, how merging works for content like rules and hints, what happens when a tier defines content the lower tiers don't know about.
- **The injection mechanism** for agent awareness — the SDK has multiple extension points (system prompt presets, append parameters, hooks). The new team picks. Constraint: must implement L15's two-piece semantics.
- **The artifact-dir mechanism** for surfacing workflow setup output to subsequent agents.
- **Test strategy** — what tests exist today, what's needed to enforce the boundary, what's needed to verify override resolution works correctly.

---

## File-move inventory (factual data — do not re-survey)

The prior run did the codebase walk and produced this inventory. The new team uses it directly; no re-discovery needed. If the codebase has drifted significantly since the vision was written, the new team should re-validate, but the structure should be stable.

### Engine .py files to move (sprustonlab → converged layout)

Use `git mv` to preserve history. Six files.

| From | To |
|---|---|
| `claudechic/workflow_engine/__init__.py` | `claudechic/workflows/__init__.py` (merge with any existing) |
| `claudechic/workflow_engine/engine.py` | `claudechic/workflows/engine.py` |
| `claudechic/workflow_engine/loader.py` | `claudechic/workflows/loader.py` |
| `claudechic/workflow_engine/parsers.py` | `claudechic/workflows/parsers.py` |
| `claudechic/workflow_engine/phases.py` | `claudechic/workflows/phases.py` |
| `claudechic/workflow_engine/agent_folders.py` | `claudechic/workflows/agent_folders.py` |
| `claudechic/workflow_engine/` (now empty) | delete |

### Bundled workflow YAML directories to move

Seven directories (each contains workflow YAML manifests + role identity files).

| From | To |
|---|---|
| `claudechic/workflows/audit/` | `claudechic/defaults/workflows/audit/` |
| `claudechic/workflows/cluster_setup/` | `claudechic/defaults/workflows/cluster_setup/` |
| `claudechic/workflows/codebase_setup/` | `claudechic/defaults/workflows/codebase_setup/` |
| `claudechic/workflows/git_setup/` | `claudechic/defaults/workflows/git_setup/` |
| `claudechic/workflows/onboarding/` | `claudechic/defaults/workflows/onboarding/` |
| `claudechic/workflows/project_team/` | `claudechic/defaults/workflows/project_team/` |
| `claudechic/workflows/tutorial_extending/` | `claudechic/defaults/workflows/tutorial_extending/` |

### Global manifest files to move

Two files.

| From | To |
|---|---|
| `claudechic/global/hints.yaml` | `claudechic/defaults/global/hints.yaml` |
| `claudechic/global/rules.yaml` | `claudechic/defaults/global/rules.yaml` |
| `claudechic/global/` (now empty) | delete |

### MCP tools directory

| From | To |
|---|---|
| `claudechic/mcp_tools/` | `claudechic/defaults/mcp_tools/` |

### `.claude/`-write sites to relocate

Three claudechic state-file write sites that today live inside `.claude/`. All move into `<launched_repo>/.claudechic/`.

| Source path (today) | Destination | Files implementing |
|---|---|---|
| `~/.claude/.claudechic.yaml` (global config) | `~/.claudechic/config.yaml` (per-user) | `claudechic/config.py:17` (`CONFIG_PATH`); the new install branch in `_load`; project-toggle keys merged into per-project equivalent |
| `<launched_repo>/.claude/hints_state.json` | `<launched_repo>/.claudechic/hints_state.json` | `claudechic/hints/state.py:127` (`_STATE_FILE`) |
| `<launched_repo>/.claude/phase_context.md` | `<launched_repo>/.claudechic/phase_context.md` | `claudechic/app.py` lines 1623, 1635, 1648, 1822, 1834 |

Plus the `.claude/rules/` write site (currently the `/onboarding` `context_docs` install phase writes claudechic context docs there). Per L3, claudechic must stop writing to `.claude/rules/`. Where the docs go and how Claude sees them is a new-team design decision (see L15 for the agent-awareness mechanism intent).

### Files with `workflow_engine` import references — update to `workflows`

22 files. The change is mechanical: `from claudechic.workflow_engine import ...` → `from claudechic.workflows import ...`.

```
claudechic/app.py
claudechic/mcp.py
claudechic/onboarding.py
claudechic/chicsession_cmd.py
claudechic/hints/engine.py
claudechic/hints/parsers.py
claudechic/hints/state.py
claudechic/hints/triggers.py
claudechic/hints/types.py
claudechic/guardrails/rules.py
claudechic/guardrails/hooks.py
claudechic/workflows/__init__.py        (post-move; was workflow_engine/__init__.py)
claudechic/workflows/engine.py          (post-move; internal references)
claudechic/workflows/loader.py          (post-move; internal references)
claudechic/workflows/parsers.py         (post-move; internal references)
```

Doc files (textual rewrite, not imports — these mention `workflow_engine` as a concept):

```
claudechic/context/workflows-system.md
claudechic/context/hints-system.md
claudechic/context/guardrails-system.md
claudechic/context/claudechic-overview.md
claudechic/workflows/tutorial_extending/learner/edit-yaml-config.md  (will be at defaults/workflows/...)
claudechic/workflows/tutorial_extending/learner/add-rule.md          (will be at defaults/workflows/...)
claudechic/workflows/tutorial_extending/learner/add-advance-check.md (will be at defaults/workflows/...)
```

### Files with `claudechic/workflows/` path references — update to `claudechic/defaults/workflows/`

5 files reference workflow YAML paths for bundled-content lookup:

```
claudechic/app.py                                  (workflow discovery sites)
claudechic/mcp.py                                  (workflow discovery sites)
claudechic/onboarding.py                           (workflow discovery sites)
claudechic/workflows/loader.py        (post-move)  (manifest loader)
claudechic/workflows/agent_folders.py (post-move)  (agent-folder assembly)
```

The loader will need a 3-tier fallback-discovery walk (per L7). abast's `8e46bca` provides the 2-tier pattern; extending to 3 tiers is a new-team design call.

### Doc-surface rewrite — `~/.claude/.claudechic.yaml` references

Six files hard-code the old global config path. All update to the new path under L6 (`~/.claudechic/config.yaml`):

```
CLAUDE.md:318
claudechic/theme.py:3
claudechic/theme.py:87
claudechic/errors.py:77
claudechic/context/CLAUDE.md:79
docs/privacy.md:36
claudechic/config.py:17                          (docstring)
```

### Worktree symlink (BF7)

`claudechic/features/worktree/git.py:293-301` symlinks `<main_wt>/.claude` into each new worktree so hooks/skills/local settings carry over. After the boundary work, claudechic state no longer rides this symlink. A parallel `.claudechic/` symlink must be added in the same code site (lines 293-301) or the worktree feature silently regresses (claudechic state stops carrying over to new worktrees). abast did not touch this file (zero churn) so no merge conflict expected.

### Hot files (modified by both forks since merge-base `285b4d1`, 2026-04-20)

These are the files where both forks have edited. Cherry-picks of abast's commits will collide with sprustonlab's existing edits at these paths. Merge resolution is mechanical (different functions per FDR §5 commentary); no semantic redesign expected.

| File | sprustonlab churn | abast churn |
|---|---|---|
| `claudechic/app.py` | 186 | 167 |
| `claudechic/commands.py` | (low) | 73 |
| `claudechic/config.py` | 56 | 4 |
| `pyproject.toml` | (small) | 21 |
| `claudechic/mcp.py` | (small) | 20 |
| `tests/conftest.py` | (small) | 8 |

### `/onboarding` workflow surface

Two phase-instruction files plus a workflow YAML:

```
claudechic/workflows/onboarding/onboarding.yaml                       (post-move: defaults/...)
claudechic/workflows/onboarding/onboarding_helper/identity.md         (post-move: defaults/...)
claudechic/workflows/onboarding/onboarding_helper/orientation.md      (post-move: defaults/...)
claudechic/workflows/onboarding/onboarding_helper/context_docs.md     (post-move: defaults/...) — fate is new-team's call per L15
```

The `context_docs` phase currently installs claudechic context docs into `<launched_repo>/.claude/rules/`. Per L3 + L15, this must change. Whether the phase is removed, repurposed, or replaced is the new team's call within L15's intent.

### Hints-pipeline surface

```
claudechic/hints/triggers.py                  (ContextDocsDrift class — fate is new-team's call per L15)
claudechic/global/hints.yaml                  (post-move: defaults/...) — context_docs_outdated hint at lines 93-96, fate is new-team's call per L15
```

---

## Background available (not required reading)

The prior project-team run produced these artifacts in `.project_team/issue_23_path_eval/`:

- `RECOMMENDATION.md` — original cross-lens recommendation document.
- `fork_diff_report.md` and `fork_file_map.csv` — concrete diff between sprustonlab and abast since their merge-base.
- `composability_eval.md`, `terminology_glossary.md`, `risk_evaluation.md`, `alignment_audit.md` — four Leadership lens analyses.
- `STATUS.md` — locked decisions (D1–D22) and baseline findings.
- `Appendix.md` — rationale, rejected paths, decision history.
- `abast_executive_summary.md` — coordination artifact for the abast fork (pre-flight for the prior run; superseded by this vision).

Plus issue #25 (the deferred `/fast` discussion) on sprustonlab/claudechic.

The new team is welcome to read any of these. They are not required reading. The locked-constraints list above captures everything the new team needs from the prior run; the rest is context.

---

*End of vision.*
