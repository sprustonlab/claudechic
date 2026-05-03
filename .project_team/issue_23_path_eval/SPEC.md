# SPEC — Layout Convergence and Issue #23 Boundary Work

**For:** Implementer agents and Tester agents.
**You should be able to execute this document without reading anything else.** Background, decision history, rejected alternatives, and lens-by-lens reasoning live in `Appendix.md`. If a constraint here surprises you and you need to know why, that's where to look — but you don't need to know why to execute correctly.

---

## What you are building

Two things, in order, in this repository (`sprustonlab/claudechic`):

1. **A directory restructure** that moves engine code, bundled workflow content, and global manifests to specific new locations.
2. **A boundary refactor** that moves four claudechic-owned write paths out of the `.claude/` namespace into a new `.claudechic/` directory, plus supporting work (`/settings` TUI screen, `docs/configuration.md`, doc rewrite, worktree symlink mirror, regression test).

Between (1) and (2), Implementer pulls a small set of selected commits from `abast/claudechic`. The pull list is below.

---

## Constraints (must hold at every commit)

### Filesystem boundary

- Claudechic must never create, write, modify, or delete any path inside any `.claude/` directory (in any location: home, repo root, worktree). Reads from Claude-owned paths (`~/.claude/settings.json`, `~/.claude/projects/`, `~/.claude/history.jsonl`, `~/.claude/.credentials.json`, `~/.claude/commands/`, `~/.claude/skills/`, `~/.claude/plans/`, `.claude/commands/`, `.claude/skills/`) are permitted and must continue to work.
- The `<launched_repo>/.claude/rules/` directory is the repo owner's responsibility. Claudechic does not write to it. Claudechic's own context docs live under `<launched_repo>/.claudechic/rules/`; Claude is given access to them via the hook redirect specified in C.1.1.
- Every per-project file claudechic writes must live under `<launched_repo>/.claudechic/`. The launched-repo root contains exactly one claudechic-authored entry: the `.claudechic/` directory.
- Per-project config file: `<launched_repo>/.claudechic/config.yaml`. There is no top-level `.claudechic.yaml` file. There is no `~/.claude/.claudechic.yaml` global config (the global tier collapses into per-project).
- `analytics.id` is per-project (lives in each repo's `.claudechic/config.yaml`). There is no global analytics identity.

### Naming

- "Settings" is the user-facing umbrella term: the `/settings` TUI screen, prose in `docs/configuration.md` and `CLAUDE.md`, button labels, status-bar copy, error messages addressed to the user.
- "Config" is the technical term reserved for the YAML file format and the loader: `config.py`, `ProjectConfig`, `*.yaml` filenames, internal docstrings, code-comment references to the file format, log messages addressed to developers.
- No code-symbol renames are forced by this rule. `ProjectConfig`, `CONFIG`, `CONFIG_PATH` etc. all survive. The rule applies to user-facing prose only.

### Directory layout (after the restructure)

- Engine Python: `claudechic/workflows/{__init__,engine,loader,parsers,phases,agent_folders}.py`
- Bundled workflow YAML data: `claudechic/defaults/workflows/<workflow-name>/...`
- Bundled global manifests: `claudechic/defaults/global/{hints,rules}.yaml`
- The directories `claudechic/workflow_engine/` and `claudechic/global/` must not exist after the restructure.

### Process

- The restructure (Phase A below) lands as a single atomic PR. Do not interleave with cherry-picks.
- All cherry-picks (Phase B below) require a semantic-review checkpoint before merge — see "Acceptance criteria → Semantic review" below.
- The boundary lint step (Phase B.1) must be in place in CI before the first cherry-pick.
- The boundary regression test (Phase C.6) must be in CI before sign-off.

---

## Phase A — Restructure to converged layout

### A.1 File moves

Use `git mv` so history is preserved. Single atomic PR.

| Source | Destination |
|---|---|
| `claudechic/workflow_engine/__init__.py` | `claudechic/workflows/__init__.py` (merge with existing `workflows/__init__.py` if present) |
| `claudechic/workflow_engine/engine.py` | `claudechic/workflows/engine.py` |
| `claudechic/workflow_engine/loader.py` | `claudechic/workflows/loader.py` |
| `claudechic/workflow_engine/parsers.py` | `claudechic/workflows/parsers.py` |
| `claudechic/workflow_engine/phases.py` | `claudechic/workflows/phases.py` |
| `claudechic/workflow_engine/agent_folders.py` | `claudechic/workflows/agent_folders.py` |
| `claudechic/workflows/audit/` | `claudechic/defaults/workflows/audit/` |
| `claudechic/workflows/cluster_setup/` | `claudechic/defaults/workflows/cluster_setup/` |
| `claudechic/workflows/codebase_setup/` | `claudechic/defaults/workflows/codebase_setup/` |
| `claudechic/workflows/git_setup/` | `claudechic/defaults/workflows/git_setup/` |
| `claudechic/workflows/onboarding/` | `claudechic/defaults/workflows/onboarding/` |
| `claudechic/workflows/project_team/` | `claudechic/defaults/workflows/project_team/` |
| `claudechic/workflows/tutorial_extending/` | `claudechic/defaults/workflows/tutorial_extending/` |
| `claudechic/global/hints.yaml` | `claudechic/defaults/global/hints.yaml` |
| `claudechic/global/rules.yaml` | `claudechic/defaults/global/rules.yaml` |
| `claudechic/workflow_engine/` (now empty) | delete |
| `claudechic/global/` (now empty) | delete |

### A.2 Import updates

Files containing `workflow_engine` import references — update each `from claudechic.workflow_engine import ...` to `from claudechic.workflows import ...`:

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

Doc files mentioning `workflow_engine` (textual rewrites, not imports):

```
claudechic/context/workflows-system.md
claudechic/context/hints-system.md
claudechic/context/guardrails-system.md
claudechic/context/claudechic-overview.md
claudechic/workflows/tutorial_extending/learner/edit-yaml-config.md  (will be at defaults/workflows/...)
claudechic/workflows/tutorial_extending/learner/add-rule.md          (will be at defaults/workflows/...)
claudechic/workflows/tutorial_extending/learner/add-advance-check.md (will be at defaults/workflows/...)
```

### A.3 Path updates

Files containing `claudechic/workflows/` as a path reference (for bundled-content lookup) — update to `claudechic/defaults/workflows/`:

```
claudechic/app.py                                  (workflow discovery sites)
claudechic/mcp.py                                  (workflow discovery sites)
claudechic/onboarding.py                           (workflow discovery sites)
claudechic/workflows/loader.py        (post-move)  (manifest loader)
claudechic/workflows/agent_folders.py (post-move)  (agent-folder assembly)
```

The loader code in `claudechic/workflows/loader.py` (post-move) needs a fallback-discovery pattern: check `<cwd>` first for user-overridden workflow content, fall back to bundled `claudechic/defaults/workflows/`. If the equivalent logic from abast's commit `8e46bca` is being pulled in Phase B, write a placeholder loader change in Phase A and replace it in Phase B; otherwise implement the fallback now.

### A.4 Test updates

- All tests that import `from claudechic.workflow_engine import ...` → update to `claudechic.workflows`.
- All tests that assert paths like `claudechic/workflows/<wf>/manifest.yaml` → update to `claudechic/defaults/workflows/<wf>/manifest.yaml`.
- Add a new test `tests/test_workflow_loading_post_restructure.py` (or fold into an existing test) that:
  - Loads a workflow from `claudechic/defaults/workflows/project_team/project_team.yaml`.
  - Verifies the engine parses it.
  - Verifies `claudechic.workflows` is the import path for the engine.

### A.5 Doc updates

- Update `CLAUDE.md` file map: replace the `workflow_engine/` entry with the new layout description; update the `workflows/` entry.
- Update `claudechic/context/claudechic-overview.md` and `claudechic/context/workflows-system.md` to reflect the new layout.

### A.6 Acceptance criteria — Phase A

- `python -c "from claudechic.workflows import ManifestLoader; print(ManifestLoader)"` succeeds.
- `pytest tests/` exits 0.
- `claudechic` launches in this repo and loads workflows correctly.
- `find claudechic/workflow_engine claudechic/global -type f` returns no files (the directories should not exist).
- `find claudechic/defaults -type f | head -5` returns at least 5 bundled YAML files.
- `git status` shows no stray files in old locations.
- The PR is a single atomic commit (or one PR with a clean linear history of moves + updates).

---

## Phase B — Selective pull from abast

### B.1 Add boundary lint check (must precede first cherry-pick)

Add a CI step (or pre-merge checklist) that fails when:

- Any source file under `claudechic/` writes to a path matching `**/.claude/**` (other than reads, which are permitted).
- Any new file appears at the launched-repo root with a name starting with `.claudechic` other than the directory `.claudechic/` itself.

Implementation: a `pytest` test or a standalone CI script grep is acceptable. Must be runnable locally via `pytest` or `make lint` (or equivalent) without external setup.

### B.2 Create the non-pull register

Create file `.project_team/issue_23_path_eval/NON_PULLED.md` with seed entries:

```
| Commit | Reason | Re-evaluation trigger |
|---|---|---|
| `26ce198` (`/fast` command, abast/claudechic) | Deferred; API-key-only feature | sprustonlab/claudechic#25 outcome |
| `0ad343b` (anthropic 0.79.0 pin, abast/claudechic) | Required only by `/fast`; not pulling `/fast` | sprustonlab/claudechic#25 outcome |
| `claudechic/fast_mode_settings.json` (introduced in abast `26ce198`) | Bundled with `/fast` | sprustonlab/claudechic#25 outcome |
```

### B.3 Cherry-pick set

Add abast as a remote if not already present:

```
git remote add abast https://github.com/abast/claudechic.git
git fetch abast
```

Cherry-pick the following commits in this order. Each cherry-pick is its own commit (or own PR if reviewer cadence requires); do not squash across commits.

| Order | Commit | Description |
|---|---|---|
| 1 | `9fed0f3` | Docs: clarify `spawn_agent type=` parameter |
| 2 | `8e46bca` | Fix: use resolved `workflows_dir` instead of hardcoded path |
| 3 | (selective) `d55d8c0` — loader changes only | Manifest loader fallback-discovery logic. Cherry-pick selectively: `git cherry-pick --no-commit d55d8c0`, then unstage and revert all path additions under `claudechic/defaults/...` (we already have that content from Phase A), commit only the loader code changes. Resulting commit message: "feat: ManifestLoader fallback-discovery pattern (selective from abast d55d8c0)" |
| 4 | `f9c9418` | Full model ID + loosened validation. **Pull only if the project decides to adopt this UX feature** — flag for separate decision. |
| 5 | `5700ef5` | Default to `auto` permission mode on startup. **Pull only if the project decides to make `auto` the default startup behavior** — flag for separate decision. |
| 6 | `7e30a53` | Add `auto` to Shift+Tab cycle. **Pull only if `5700ef5` is pulled** (these are a bundle). |

Skip (these are in `NON_PULLED.md`):

- `26ce198` (`/fast`) — deferred
- `0ad343b` (anthropic 0.79.0 pin) — only needed for `/fast`

### B.4 Per-cherry-pick procedure

For each cherry-pick:

1. Run the cherry-pick: `git cherry-pick <sha>` (or `git cherry-pick --no-commit <sha>` for selective ones).
2. Resolve any textual conflicts (most should be clean post-restructure).
3. Run the test suite: `pytest tests/` exits 0.
4. Run the boundary lint (B.1): no violations.
5. Run the semantic review (see Acceptance Criteria → Semantic review below). Pass criterion must be met.
6. Commit (or finalize the PR).

### B.5 Acceptance criteria — Phase B

- All listed cherry-picks (or the subset decided by the UX-flagged decisions) are applied as their own commits with clean history.
- `pytest tests/` exits 0 after each cherry-pick.
- Boundary lint passes after each cherry-pick.
- For each cherry-pick: a semantic-review note exists meeting the pass criterion (see "Semantic review" below).
- `NON_PULLED.md` is up-to-date — every commit in abast's branch since merge-base `285b4d1` is either pulled or recorded in `NON_PULLED.md` with rationale and re-evaluation trigger.

---

## Phase C — Issue #23 boundary work

### C.1 Relocate the four `.claude/`-write paths

| Source path (today) | Destination (post-#23) | File implementing |
|---|---|---|
| `~/.claude/.claudechic.yaml` (global config) | `<launched_repo>/.claudechic/config.yaml` (per-project) | `claudechic/config.py:17` (`CONFIG_PATH`); migration in `_load`; existing project-toggle `.claudechic.yaml` content merged in |
| `<launched_repo>/.claude/hints_state.json` | `<launched_repo>/.claudechic/hints_state.json` | `claudechic/hints/state.py:127` (`_STATE_FILE`); read-old, write-new migration on first run |
| `<launched_repo>/.claude/phase_context.md` (writes) | `<launched_repo>/.claudechic/phase_context.md` | `claudechic/app.py` lines 1623, 1635, 1648, 1822, 1834 (and any other write sites under `.claude/phase_context.md`) |
| `<launched_repo>/.claude/rules/<doc>.md` (claudechic-installed context docs) | `<launched_repo>/.claudechic/rules/<doc>.md` | `claudechic/defaults/workflows/onboarding/onboarding_helper/context_docs.md` (install target); `claudechic/hints/triggers.py:25-82` (`ContextDocsDrift` compares against new location); `claudechic/defaults/global/hints.yaml:93-96` (`context_docs_outdated` hint message wording); `claudechic/defaults/workflows/onboarding/onboarding.yaml:21` (advance check path); `claudechic/defaults/workflows/onboarding/onboarding_helper/identity.md` (mention of install target); plus the access mechanism in C.1.1 below |

Claudechic does **not** write to `<launched_repo>/.claude/rules/` — that directory remains the repo owner's responsibility per D22. Claudechic's own context docs live under `<launched_repo>/.claudechic/rules/` and are surfaced to Claude via the access mechanism specified in C.1.1.

### C.1.1 Mechanism for Claude to read claudechic context docs from the new location

After relocation, Claude's normal `.claude/rules/` auto-discovery will not find claudechic's context docs (because we no longer install them there per D22). The docs need to reach Claude through a different mechanism. The selected mechanism is a **`PreToolUse` hook redirect** using claudechic's existing hook infrastructure (`claudechic/guardrails/hooks.py`), if and only if Claude's `.claude/rules/` discovery actually goes through the `Read` tool (which `PreToolUse` hooks intercept).

**Verification step required before C.1.1 can be marked complete:** Implementer must verify whether Claude Code's `.claude/rules/` auto-discovery is hookable. Concrete check: in a test repo, install a `PreToolUse` hook that logs every `Read` tool call, place a marker file at `<launched_repo>/.claude/rules/marker.md`, run a Claude session in that repo, and inspect the log for a `Read` of `marker.md`. If observed, hookable; proceed with the redirect mechanism. If not observed, the SDK uses a non-hookable discovery path (likely `SystemPromptFile`) and Implementer must escalate to Coordinator for a mechanism re-spec.

**If hookable (assumed-default mechanism):**

- Add a hook (or extend `claudechic/guardrails/hooks.py`) that fires on `Read` tool calls.
- When `tool_input.file_path` matches `<launched_repo>/.claude/rules/<filename>` AND `<filename>` is in the claudechic-context-docs allow-list (computed at startup from `claudechic/context/*.md` filenames), the hook returns `hookSpecificOutput.updatedInput` with `file_path` rewritten to `<launched_repo>/.claudechic/rules/<filename>`.
- Other reads of `.claude/rules/` (filenames not in the claudechic allow-list — e.g., user-installed third-party rule docs) **pass through unchanged.** The hook never blocks; it only redirects claudechic's own filenames.
- The allow-list is the set of filenames in `claudechic/context/*.md` (post-restructure path). Same source-of-truth as the `ContextDocsDrift` trigger uses.

**If not hookable (escalation path):** Coordinator selects an alternative mechanism (likely system-prompt injection of the docs at session start via the SDK's `SystemPromptFile` parameter). SPEC update required before Phase C continues.

### C.1.2 Update `/onboarding` to install into the new location

- In `claudechic/defaults/workflows/onboarding/onboarding.yaml` (post-restructure path; today: `claudechic/workflows/onboarding/onboarding.yaml`): change the `context_docs` phase's hint message from `"Scanning for context docs to install into .claude/rules/..."` to `"Scanning for context docs to install into .claudechic/rules/..."`. Change the advance check path from `.claude/rules/claudechic-overview.md` to `.claudechic/rules/claudechic-overview.md`. Change the `on_failure.message` accordingly.
- In `claudechic/defaults/workflows/onboarding/onboarding_helper/context_docs.md` (post-restructure path): rewrite all references to `.claude/rules/` as `.claudechic/rules/`. The install behavior is otherwise unchanged: the workflow phase still scans `claudechic/context/*.md`, asks the user, and copies NEW or UPDATED files into the target directory.
- In `claudechic/defaults/workflows/onboarding/onboarding_helper/identity.md` (post-restructure path): change the bullet "Installing context docs into `.claude/rules/` so Claude agents understand claudechic's systems." to reference `.claudechic/rules/`.

### C.1.3 Update the drift detection and hint to point at the new location

- In `claudechic/hints/triggers.py`: in the `ContextDocsDrift` class, change `rules_dir = state.root / ".claude" / "rules"` (line 46) to `rules_dir = state.root / ".claudechic" / "rules"`. Update the docstring (lines 25-38) accordingly.
- In `claudechic/defaults/global/hints.yaml` (post-restructure path; today: `claudechic/global/hints.yaml`): change the `context_docs_outdated` hint message (line 94) from `"Context docs have been updated. Run /onboarding to update your .claude/rules/ files."` to `"Context docs have been updated. Run /onboarding to update your .claudechic/rules/ files."`

### C.2 Migration logic

In `claudechic/config.py:_load`:

- On first run in a launched repo where `<cwd>/.claudechic/config.yaml` does not exist:
  - If `~/.claude/.claudechic.yaml` exists: read it, write its keys to `<cwd>/.claudechic/config.yaml`. Leave the old file in place with a deprecation warning logged on next run (do not delete during this transition).
  - If `<cwd>/.claudechic.yaml` exists: read it, merge its keys (project toggles: `guardrails`, `hints`, `disabled_workflows`, `disabled_ids`) into `<cwd>/.claudechic/config.yaml`. Leave the old file with a deprecation warning.
  - Schema merge note: project-toggle keys and former-global keys are disjoint today; no key collision logic required.

In `claudechic/hints/state.py`:

- On first read where `<cwd>/.claudechic/hints_state.json` does not exist: if `<cwd>/.claude/hints_state.json` exists, read it, write to the new path. Preserve all keys: `times_shown`, `last_shown_ts`, `dismissed`, `taught_commands`, `activation` section.

For `.claude/rules/<claudechic-doc>.md` (context docs from a prior `/onboarding` install):

- On first run after upgrade, if any filename matching `claudechic/context/*.md` is detected at `<launched_repo>/.claude/rules/`, copy each such file's content into `<launched_repo>/.claudechic/rules/` (preserving any user edits to the installed copies — copy then drift-detect, don't overwrite blindly). Then add a one-time advisory hint informing the user that the install target has moved to `.claudechic/rules/` per D22 and that the old `.claude/rules/<claudechic-doc>.md` files in their repo are no longer managed by claudechic. The hint suggests they can delete the old files (claudechic now reads from the new location); the hint does not auto-delete them — the repo owner manages `.claude/rules/`.
- The advisory hint: lifecycle `show-once`, severity `info`. Exact wording is at the implementer's discretion as long as the meaning is preserved: "Claudechic context docs have moved to `.claudechic/rules/`. The old copies at `.claude/rules/` are no longer used by claudechic — you can delete them at your discretion (we don't touch `.claude/rules/` anymore)."

### C.3 Worktree symlink mirror

In `claudechic/features/worktree/git.py` lines 293–301 (the existing `.claude/` symlink block):

- Add a parallel block: if `<main_wt>/.claudechic/` exists, symlink it into the new worktree alongside the existing `.claude/` symlink.

### C.4 `/settings` TUI screen

- Add a new screen `claudechic/screens/settings.py`.
- Wire it: register a `/settings` slash command in `claudechic/commands.py`; navigate to the new screen on invocation.
- Screen edits the YAML at `<cwd>/.claudechic/config.yaml` via the existing `ProjectConfig` loader.
- UX design is out of scope for this SPEC — Implementer follows existing screen conventions in `claudechic/screens/` for layout, key bindings, theming.

### C.5 `docs/configuration.md` reference page

- New file `docs/configuration.md`.
- Document: every key in `.claudechic/config.yaml`, its default, its behavior, valid values.
- Document: the migration paths (where keys used to live).
- Document: the boundary rule (claudechic stays out of `.claude/`).

### C.6 Doc-surface rewrite

Update each of the following references from `~/.claude/.claudechic.yaml` to `<launched_repo>/.claudechic/config.yaml` (or the appropriate canonical form for the document):

```
CLAUDE.md:318
claudechic/theme.py:3
claudechic/theme.py:87
claudechic/errors.py:77
claudechic/context/CLAUDE.md:79
docs/privacy.md:36
claudechic/config.py:17                          (docstring)
```

### C.7 Boundary regression test

Add `tests/test_boundary_compliance.py`:

- Set up: create a tmp repo (empty), `cd` into it, run claudechic (programmatically, via the test harness used elsewhere in this codebase).
- Assertion 1: after the run, the launched-repo root contains `.claudechic/` and no other claudechic-authored files (no `.claudechic.yaml` at root).
- Assertion 2: `find <tmp_repo>/.claude/ -newer <baseline_marker>` returns no claudechic-authored content (allowance for Claude-owned content if Claude itself is invoked; the test should isolate claudechic's writes).
- Assertion 3: `find ~/.claude -name '.claudechic*' -newer <baseline_marker>` is empty (no global tier created).
- Test fails loudly with diagnostics if any assertion violates.

### C.8 Acceptance criteria — Phase C

- All four relocations listed in C.1 are complete; old paths are no longer written by claudechic.
- C.1.1 mechanism verification is complete: hookable-Read assumption confirmed (or escalated and re-specified). If confirmed, hook redirect implemented and verified with a smoke test (Claude reading `.claude/rules/<claudechic-doc>` is silently served the file from `.claudechic/rules/<claudechic-doc>`). Other `.claude/rules/` reads pass through unchanged.
- C.1.2 `/onboarding` updates are complete: install target is `.claudechic/rules/`; advance check path updated; phase instruction file rewritten.
- C.1.3 drift detection updates are complete: `ContextDocsDrift` compares against `.claudechic/rules/`; hint message references the new location.
- Advisory hint about previously-installed `.claude/rules/` content (C.2) is implemented and fires once for users upgrading from a previous claudechic install. Existing `.claude/rules/<claudechic-doc>` files are copied (not moved) to `.claudechic/rules/` on first run if not already there; old files in `.claude/rules/` are not deleted by claudechic.
- Migration logic (C.2) preserves existing user state on first-run upgrade — verified by a migration test that prepares a fake old layout, runs claudechic, asserts new layout has the right keys.
- Worktree symlink mirror (C.3) works — verified by a test that creates a worktree and asserts both `.claude/` and `.claudechic/` symlinks exist.
- `/settings` TUI screen (C.4) launches, displays current config, accepts edits, persists to `.claudechic/config.yaml`.
- `docs/configuration.md` (C.5) documents every key currently in `ProjectConfig` and former-global config.
- All 7 doc-surface references (C.6) point to the new path.
- Boundary regression test (C.7) is in CI and passes — confirms claudechic does not write to `.claude/rules/` (the hook redirect modifies *Claude's* read path, not claudechic's writes).
- Boundary lint (B.1) still passes after Phase C changes.
- `pytest tests/` exits 0.

---

## Phase D — Sign-off

### D.1 Final checks

Run all of the following. All must pass; halt sign-off if any fail.

- `pytest tests/ -v` — full suite green.
- Boundary lint (B.1) — no violations.
- Boundary regression test (C.7) — passes.
- Manual smoke test:
  - Launch claudechic in a fresh tmp repo.
  - Verify `.claudechic/config.yaml` is created.
  - Verify nothing claudechic-authored appears under any `.claude/` directory.
  - Verify `.claudechic/hints_state.json` is created (after triggering at least one hint).
  - Verify `.claudechic/phase_context.md` is written when a workflow is activated.
  - Verify worktree creation copies both `.claude/` and `.claudechic/`.
  - Verify the `/settings` screen launches and edits persist.

### D.2 Documentation finalize

- `CLAUDE.md` reflects the new layout in the file map and any prose that mentioned the old layout.
- `docs/configuration.md` is current with the post-#23 schema.
- Any other doc that mentioned `~/.claude/.claudechic.yaml` or `workflow_engine/` is updated.

### D.3 Issue closure

- Close [sprustonlab/claudechic#23](https://github.com/sprustonlab/claudechic/issues/23) with a comment summarizing what shipped and linking to the merged PRs.
- Update `STATUS.md` in `.project_team/issue_23_path_eval/` to mark execution complete.

---

## Pre-conditions (must be true before each phase starts)

| Phase | Pre-condition |
|---|---|
| A | Phase 1 (abast pre-flight) is complete with confirmation answers recorded in STATUS.md. |
| A | The repo's working tree is clean (no uncommitted changes that would conflate with the restructure). |
| B | All Phase A acceptance criteria pass. The restructure PR is merged. |
| B | UX decisions on `f9c9418`, `5700ef5`, `7e30a53` have been made (or explicitly deferred — record in STATUS.md). |
| C | All Phase B acceptance criteria pass. All planned cherry-picks are merged. |
| C | The boundary lint (B.1) is in CI and passing on the post-Phase-B tree. |
| D | All Phase C acceptance criteria pass. |

---

## Acceptance criteria — semantic review (referenced from Phase B)

For each cherry-pick batch in Phase B:

- **Artifact reviewed:** the cumulative diff of the just-applied batch + the batch's commit messages + the corresponding entry in the cherry-pick plan (the table in B.3).
- **Reviewer:** a sprustonlab maintainer who did not perform the cherry-picks, paired with the implementer-of-record for any sprustonlab-side files touched by the pull.
- **Pass criterion:** a written "design diff narrative" exceeding one paragraph that names (i) what the system now does differently in observable behavior, (ii) which design invariants of either fork are now binding, (iii) any "looks fine, behaves differently" risks identified.
- **Fail criterion:** narrative is missing, is purely textual ("file X gained N lines"), or omits an invariant the reviewer can name. On fail: revert the batch, re-plan, re-apply.
- **Where the narrative is recorded:** in the PR description for the cherry-pick PR.

---

## Test plan — for Tester agents

Tests are organized by phase. Tester runs all relevant tests after each phase.

### After Phase A

- `pytest tests/` — full existing suite still passes.
- New: `tests/test_workflow_loading_post_restructure.py` (added in A.4) — passes.
- Manual smoke: launch claudechic in this repo; workflows load and activate.

### After Phase B (after each cherry-pick)

- `pytest tests/` — full suite passes.
- Boundary lint (B.1) — passes.
- Semantic review note exists in the cherry-pick PR description.

### After Phase C

- `pytest tests/` — full suite passes.
- New: `tests/test_boundary_compliance.py` (added in C.7) — passes.
- Migration test — verify old → new state migrates correctly (prepare fake old layout, run claudechic, assert new layout contents).
- Worktree symlink test — verify both `.claude/` and `.claudechic/` symlinks created in new worktrees.
- `/settings` TUI test — verify screen launches, displays current config, persists edits.

### Sign-off (Phase D)

- All Phase C tests still pass.
- Manual smoke (D.1) — all items checked.
- Documentation review — D.2 items current.

---

## Reporting

At end of each phase, Implementer (or Tester) records in `STATUS.md`:

- Phase complete (date, who).
- Acceptance criteria results: each item passed or remediated.
- Semantic-review notes (Phase B) — link to PR descriptions.
- Any deferred decisions or follow-up items.

Halt and escalate to Coordinator if:

- Any acceptance criterion fails and the remediation requires a SPEC change.
- A pre-condition turns out to be unmet at phase start.
- A cherry-pick produces conflicts beyond mechanical resolution.
- The boundary lint catches a violation in code that's required for some other reason.

---

*End of SPEC.*
