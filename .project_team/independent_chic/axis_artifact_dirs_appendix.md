# Axis Spec Appendix — Workflow Artifact Directories (R7)

**Companion to:** `axis_artifact_dirs.md`
**Mode:** Rationale only. No operational instructions; if the implementer needs a binding statement, it lives in the operational spec.
**Per L14:** the operational spec is executable without ever opening this file. This file documents *why* the chosen design was chosen, what alternatives were rejected, and what would trigger reversal.

---

## 1. Why per-chicsession scope (vs per-activation, vs engine-generated run_id)

The two competing scope choices were:

| Scope | Identity | Resume behavior | UX |
|---|---|---|---|
| **per-chicsession** (chosen) | `chicsession_name` | New activation under the same chicsession reuses the same dir | User-named identity; matches existing `Chicsession` mental model |
| per-activation | engine-generated `run_id` (timestamp/UUID) | New activation creates a new dir; old dir is orphaned on resume | User loses access to prior run's artifacts on resume; engine has to pick a fresh `run_id` even when resuming |
| per-launched-repo | repo only | All workflows in repo share one dir | Pollution across runs; no isolation when running multiple workflows |

The chicsession layer already provides the identity-and-resume primitive. `Chicsession.workflow_state` persists across stop/start of the engine and survives `app` restart. If the artifact directory used a different identity (e.g. timestamp-keyed), then the user resuming `independent_chic` would find their workflow phase intact (from `workflow_state`) but their spec / status / plan files unreachable (sitting in `runs/2026-04-26T15:30:00/` while the new activation creates `runs/2026-04-26T16:42:11/`). That is the exact failure mode `vision.md` §6 names ("Implementer or Tester agent in a workflow run can find and read the spec files the setup phase wrote").

Per-chicsession scope inherits the chicsession layer's identity and gets the resume property for free. Cost: chicsessions become slightly more "physical" (they own a filesystem directory, not just a JSON file). That cost is acceptable — the chicsessions directory `<repo>/.chicsessions/` is already a filesystem entity (`ChicsessionManager._dir`), so the model is consistent.

**Reversal trigger.** If the team later finds that users want artifact dirs to be ephemeral (e.g., scratch space that gets cleaned), the per-activation scope could be reintroduced as an additional layer (`runs/<chicsession>/<activation_id>/`). This axis-spec does not preclude that future addition; it just chooses chicsession-scope as the present default because it serves the documented use case.

---

## 2. Why `<repo>/.claudechic/runs/<chicsession_name>/` (vs other path layouts)

Three sub-decisions:

### 2.1 Why `runs/` and not `project_team/`, `artifacts/`, or `workflow_runs/`

- `project_team/` is the existing pattern but is workflow-specific. `claudechic/defaults/workflows/` ships at least seven workflow types (audit, cluster_setup, codebase_setup, git_setup, onboarding, project_team, tutorial_extending). Naming the dir after one workflow privileges that workflow.
- `artifacts/` is the most semantically accurate noun but collides with common project-root conventions (build artifacts, test artifacts) that users may already use. Even nested under `.claudechic/`, the word invites confusion.
- `workflow_runs/` is verbose. The parent directory is `.claudechic/`; the "workflow" qualifier is implicit (claudechic uses the term "workflow" exclusively for engine-orchestrated multi-phase processes).
- `runs/` is short, generic, and the parent directory carries the context. Matches `R7.2`'s suggestion in the lens-input spec.

### 2.2 Why a single layer (`runs/<chicsession_name>/`) and not nested (`runs/<workflow_id>/<chicsession_name>/`)

A two-layer scheme keyed on `(workflow_id, chicsession_name)` would partition artifacts when the same chicsession is used to run multiple workflows successively. But:

- The typical flow has one workflow per chicsession (chicsessions are commonly named after the workflow — `_prompt_chicsession_name` defaults to `workflow_id`).
- Switching workflows inside a chicsession is reachable but unusual: it requires deactivating (which clears `_chicsession_name`), then reactivating with the same name typed manually.
- A two-layer scheme would mean the typical case has a redundant path component (`runs/project-team/independent_chic/` instead of `runs/independent_chic/`).
- For the unusual case, the user's intent is ambiguous — they may want fresh artifacts (in which case they should pick a new chicsession name), or they may want to mix (in which case sharing one dir is fine).

The single-layer scheme optimizes the typical case at the cost of being conservative about the unusual one. The unusual case is documented in spec A5 with explicit semantics ("artifacts mix").

### 2.3 Why under `.claudechic/` and not at repo root

L5 binds: at most one claudechic-authored entry under launched-repo root, named `.claudechic/`. Any artifact-dir location MUST be inside `.claudechic/`. No alternative.

---

## 3. Why env-var injection AND markdown substitution (not one or the other)

The lens-input spec R7.3 names env-var as the primary mechanism. R7.4 says role markdown MUST NOT hard-code paths. The composability argument for both:

- **Env-var alone:** agents must call `os.environ` (typically via a Bash tool call) to discover the path. The first such call costs a turn. Multiple agents in a workflow each pay this cost.
- **Substitution alone:** the path appears in the prompt verbatim, but agents have no programmatic way to discover it without re-reading the prompt. Tools that don't go through the prompt (e.g. an agent calling a sub-tool that needs the path) have no source.
- **Both:** prompts read naturally (`Write to /home/.../runs/foo/spec.md`) AND tools / sub-agents can introspect the env. The two mechanisms reinforce.

The cost of "both" is small — the env-var injection is two lines in `_make_options`, and the substitution is one `str.replace` in `_assemble_agent_prompt`. The risk that the two diverge is bounded — they read from the same source-of-truth (engine's `artifact_dir`), and `assemble_phase_prompt` reads `os.environ` rather than maintaining its own copy.

INV-12 (the grep test) ensures markdown does not bypass the token. Without that test, the discipline would slowly erode as workflow authors hard-code paths "just this once."

---

## 4. Why `${CLAUDECHIC_ARTIFACT_DIR}` and not `$CLAUDECHIC_ARTIFACT_DIR` or other forms

- `${VAR}` (curly braces) is unambiguous against neighboring text — `${CLAUDECHIC_ARTIFACT_DIR}/spec.md` parses cleanly; `$CLAUDECHIC_ARTIFACT_DIR/spec.md` could be misread by a human as a single token if read quickly.
- It is the same form Bash uses for parameter expansion, so users have intuition for it.
- It does NOT trigger any actual shell expansion — the substitution is a literal string-replace done by `_assemble_agent_prompt`. The prompt is markdown text, not a shell command.
- Other forms considered: `{{VAR}}` (Mustache-style; risks collision with template engines), `<VAR>` (XML-ish; risks colliding with HTML), `%VAR%` (Windows-style; unfamiliar to most users on POSIX).

Only one token is defined. If future axes want more, they choose a token form at that time; nothing in this axis precludes the same `${...}` family being extended.

---

## 5. Why no automatic garbage collection

- The existing `.project_team/<name>/` pattern has set an expectation that artifacts persist. Users who have run prior workflows have artifacts they may still reference.
- Setup-phase output (specifications) is high-value: it represents documentation work that took the team's attention. Auto-deletion is hostile.
- The space cost is small (text files, typically a few MB per run).
- Auto-deletion at `_deactivate_workflow` time would be especially surprising — a user pausing a workflow to switch context would lose data.
- A future explicit `/clean` command (out of scope here) is the right place for cleanup, because it makes the destructive action visible.

The composability argument: garbage collection is a separate axis (lifetime management) that does NOT need to be solved to make the artifact-dir mechanism work. Adding it now couples this axis to a policy that may not be the right one. The cost of deferring is bounded — disk usage grows linearly with run count, and users with strong opinions can `rm -rf .claudechic/runs/foo/` themselves.

---

## 6. Why no migration of existing `.project_team/<name>/`

L17 + A9 are binding here. The user has accepted silent loss. The composability argument: migration code is its own axis (migrations are a separate dimension of variation — when, what, with what rollback), and adding it would couple the artifact-dir axis to a migration mechanism that doesn't exist anywhere else in the spec. Better to keep the axis clean.

The IRONY worth noting: this very `independent_chic` run lives at `.project_team/independent_chic/`. The spec it produces describes its own orphaning. The implementer who acts on this spec will need to manually `mv .project_team/independent_chic .claudechic/runs/independent_chic` if they want this run's artifacts to remain accessible to the post-restructure workflow. This is acceptable per A9 — the implementer is one of the only two existing claudechic users — and is called out in spec N3.

---

## 7. Why `Chicsession.workflow_state` and the artifact dir are kept orthogonal

Both store "stuff related to the workflow run." But they live at different levels of the system:

- `workflow_state` is engine internal state. It is small (~50 bytes), structured, JSON-serializable, and exists to let the engine survive restart. The engine reads it via `from_session_state` and writes it via `persist_fn`. No human or agent reads it directly.
- The artifact dir is human-readable file storage. Files inside are agent-authored and human-reviewed. The engine never reads them; agents do.

The two have different access patterns, different schemas, different persistence mechanisms (chicsession JSON vs filesystem directory), and different consumers. Coupling them would mean either:
- Storing artifact-dir content inside chicsession JSON (would balloon the JSON; would force agent file writes to go through engine API).
- Storing engine state inside artifact-dir files (would force the engine to do file I/O; would lose the atomic-write property `ChicsessionManager` provides).

Both are worse than the orthogonal design. The link between them — that the artifact-dir path is *derived from* the chicsession name, not the other way around — is one-way and minimal. The chicsession layer doesn't know the artifact dir exists; the engine layer derives the path at construction.

---

## 8. Possible vision / STATUS / spec inconsistencies (per A1)

Per A1, the agent must surface inconsistencies rather than silently work around them.

### 8.1 vision.md §6 framing vs lens-input spec R7

`vision.md` §6 says the team will decide "where artifact dirs live, how they're named, how they survive across phases." The lens-input spec `composability.md` R7.2 names a recommended path (`<repo>/.claudechic/runs/<run_id>/`) and recommends per-workflow-run scope. This axis-spec **deviates** from R7.2's `run_id` recommendation by choosing chicsession-name keying instead. Reasoning: R7.2 says "per-workflow-run" without specifying what identifies a run, and `run_id` is shown as one example. Chicsession-name is a more user-visible, resume-friendly identifier for what `vision.md` calls a "workflow run." This is a refinement of R7.2, not a contradiction.

If the lens lead disagrees and prefers an engine-generated `run_id`, this axis-spec can be amended to layer `runs/<chicsession>/<run_id>/` — but the user-facing observation is the same (the typical user resumes their chicsession and finds their files), and the simpler layout serves it.

### 8.2 Chicsession-name as filesystem identifier (P3)

The existing chicsession code (`chicsessions.py` and `chicsession_cmd.py`) treats chicsession names as opaque strings: it uses them as JSON filename stems via `f"{name}.json"`. There is no validation. If a user names their chicsession `../evil` or `a/b/c`, the existing chicsession `save` will create unexpected paths. This bug pre-exists and is not introduced by this axis.

The artifact-dir axis introduces P3 (engine refuses to construct with unsafe `chicsession_name`). This adds *new* validation at engine construction time — strictly stronger than current behavior. Two tradeoffs:

- It moves one bug-class (path traversal via chicsession name) from "silent acceptance" to "loud refusal." That is a strict improvement.
- It validates at engine construction, not at chicsession save. So a malicious chicsession on disk (created by a previous bug) would be loadable by `ChicsessionManager.load` but unusable for workflow activation. Users would see workflow-activation fail with a clear error.

A more principled fix would push the validation into `ChicsessionManager.save` itself. That is out of scope here (it would be a chicsession-axis change), but worth noting as a follow-up.

### 8.3 STATUS Open Mechanism Q4 vs Locked decisions

STATUS Open Mechanism Q4 ("Artifact-dir mechanism for surfacing workflow setup output to subsequent agents") is open. No lock conflicts with this axis-spec's choices. The lock-set L1–L17 + A1–A12 does not constrain artifact-dir layout beyond L5 (must live under `.claudechic/`) and L17 (no migration). Both are satisfied.

### 8.4 None of the above is blocking

The axis-spec is internally consistent and consistent with all binding constraints. The R7.2 deviation (8.1) is a refinement; the chicsession-name validation (8.2) is a strictly-improving side effect; STATUS Q4 (8.3) is the question this axis-spec answers.

---

## 9. Two issues NOT fully resolved

These two areas are not blocking but warrant the lens lead's attention during synthesis:

### 9.1 Multi-process concurrency on same chicsession

K4 in the operational spec explicitly leaves "two app instances on same chicsession" as undefined behavior, deferring to the chicsession layer's existing properties. The chicsession layer uses `os.replace` for atomic JSON writes but does NOT use file locks. Concurrent writes to the artifact dir are also unguarded. For a pair of users who share a project on the same filesystem, this is a real edge case — if both accidentally activate workflow `foo` against chicsession `bar`, they will quietly clobber each other's artifacts.

The resolution path is at the chicsession layer (file locks, lockfile, or per-app PID assertion in the chicsession JSON). It is NOT at the artifact-dir axis. Flagging for the lens lead because it touches the user-facing story for "what happens when I share a repo."

### 9.2 Artifact dir survival across `git worktree`

The R8 worktree-symlink work (per SPEC.md §10.3, restored after the synthesis's initial AS-3 deviation was reversed by user direction) symlinks `<main_wt>/.claudechic/` into each new worktree. So a worktree gets the parent's `runs/` for free.

**Residual asymmetry — scoped to `.chicsessions/` only.** Chicsession files live at `<repo>/.chicsessions/`, NOT under `.claude/` or `.claudechic/`. Only `.claude/` and (per SPEC.md §10.3) `.claudechic/` are symlinked at the worktree code site; `.chicsessions/` is NOT symlinked.

Consequence: a chicsession `foo` created in worktree A is visible in worktree B via the artifact files at `<wt_B>/.claudechic/runs/foo/` (symlink resolves to `<main_wt>/.claudechic/runs/foo/`), but the chicsession JSON at `<wt_B>/.chicsessions/foo.json` is NOT (each worktree has its own `.chicsessions/` directory). The asymmetry is: artifact files cross worktrees; the chicsession identity does not.

The fix is at the chicsessions layer (move chicsessions inside `.claudechic/chicsessions/`, picking up the symlink for free) or at the worktree layer (add a third symlink for `.chicsessions/`). Either is out of scope for this run; the issue exists today and was not introduced by this axis. Flagging because the artifact-dir axis surfaces it (artifacts becoming visible in other worktrees while their identifying chicsession is not).

The cross-platform Windows-portability concern for both `.claude` and `.claudechic` symlinks is tracked at https://github.com/sprustonlab/claudechic/issues/26.

---

## 10. Reversal triggers

If any of the following becomes true, the axis-spec should be revisited:

- **Users want fresh artifact dirs per activation, not per chicsession.** Symptom: users complain that resuming a chicsession surfaces stale specs alongside fresh ones. Fix: layer `<activation_id>/` under `runs/<chicsession>/`. Backwards-compatible with the current layout.
- **Workflow authors want isolated dirs per workflow_id within a chicsession.** Symptom: A6's "artifacts mix" semantics confuse users running multiple workflows in one chicsession. Fix: layer `<workflow_id>/` under `runs/<chicsession>/`. Backwards-compatible.
- **Artifact dirs grow large.** Symptom: disk-usage complaints. Fix: add explicit `/clean` command. Out-of-scope today; not blocked by this spec.
- **Cross-platform workflow authoring fails.** Symptom: workflows authored on POSIX use `/`-paths in markdown that break on Windows. Mitigation: this is bounded — the substitution returns absolute paths from `engine.artifact_dir`, which is a `Path` and renders platform-correctly when stringified. Markdown that hard-codes path separators around the token (e.g. `${CLAUDECHIC_ARTIFACT_DIR}/spec.md`) inherits the host platform's separator from `Path.__str__`. No-fix needed unless reports surface.

---

## 11. Compositional law check (sanity)

The axis-spec must compose with the other axes without dirty seams. Checking:

| Touched axis | This axis's interaction | Seam clean? |
|---|---|---|
| R1 (Tier) | None — artifact dirs live at project tier always (under `<repo>/.claudechic/`). User and package tiers do not have artifact dirs (artifacts are workflow-run-specific, not content). | ✓ Clean |
| R2 (Content category) | None — artifacts are not content, they are run output. | ✓ Clean |
| R3 (Resolution) | None — artifact dirs are not resolved across tiers. | ✓ Clean |
| R4 (Config) | None — no config keys introduced; no config keys consumed. | ✓ Clean |
| R5 (Boundary) | All write sites this axis introduces are `primary-state` and resolve to `<repo>/.claudechic/runs/...` paths. R5.1 satisfied by construction. | ✓ Clean |
| R6 (Awareness) | Layout collision avoided per X1–X4. Substitution-and-env mechanism is independent of R6 hook mechanism. | ✓ Clean (with explicit X1–X4 boundary) |
| R7 (this axis) | — | — |
| R8 (Worktree) | Free benefit from existing R8 symlink work. No code change requested in R8 scope. | ✓ Clean |
| Chicsession layer | One-way derivation: artifact-dir path is derived from chicsession name; chicsession layer is unaware. | ✓ Clean (A1 8.2 flags pre-existing chicsession-name-validation gap as out-of-scope follow-up) |

No dirty seams introduced. The axis composes algebraically with existing axes via:
- The byte-and-id law: artifact dir is identified by `(repo_root, chicsession_name)`; the engine derives one from the other deterministically.
- The injection law: env var is set at one site (`_make_options`), inherited automatically by all child-process spawns through the SDK's env mechanism. No special-case branching on agent type, workflow type, or chicsession.

---

*End of artifact-dir axis-spec appendix.*
