# Axis Spec — Workflow Artifact Directories (R7)

> **REFERENCE ARCHIVE — operational content has been merged into `SPEC.md` §5. This file is preserved for trace; not for implementation reading.**

**Lens:** Composability (axis-specific spawn for R7)
**Phase:** Specification
**Audience:** Implementer, Tester
**Mode:** Operational. Statements use **MUST**, **SHOULD**, **MAY**, **MUST NOT** in the RFC-2119 sense. Rationale is in the sibling appendix (`axis_artifact_dirs_appendix.md`).

This document specifies **only** the workflow artifact-directory axis (R7 in `specification/composability.md`). It does not respec the loader (R3), agent-awareness mechanism (R6), boundary test (R5), or worktree symlinks (R8); those are owned by other axis-spec authors. Where this axis touches another (`phase_context.md` location; the `assemble_phase_prompt` substitution site), the boundary is called out explicitly.

The terms `tier`, `chicsession`, `workflow`, `phase`, `engine`, `agent` follow the project's existing usage; see `terminology_glossary.md` and `composability.md` §2 if needed.

---

## 1. Scope of this axis

The artifact directory is the on-disk location where a **workflow run** persists files that subsequent agents in the same run must read. Examples: setup-phase output (specifications, status, plans), implementation hand-off material, test reports.

This is distinct from:
- `Chicsession.workflow_state` (in chicsession JSON) — engine state (workflow_id, current_phase). Small structured data.
- `<repo>/.claudechic/phase_context.md` — engine-authored phase prompt content delivered to Claude.
- Agent session JSONLs under `~/.claude/projects/...` — Claude-Code-owned conversation transcripts.

The artifact dir holds **agent-authored** files, not engine-authored ones.

---

## 2. Lifetime / scope decision

- **A1 [MUST]** The artifact directory MUST be scoped per **chicsession**. Identity is the chicsession name (`Chicsession.name`), as set by `_prompt_chicsession_name` or `_auto_create_chicsession` in `app.py`.
- **A2 [MUST]** Resuming a chicsession (loading an existing `Chicsession` via `ChicsessionManager.load`) MUST yield the same artifact directory path that was used during the chicsession's prior run(s). The path is a deterministic function of `(repo_root, chicsession_name)` — it is **not** stored in `Chicsession.workflow_state` and is **not** persisted anywhere on disk other than the directory's own existence.
- **A3 [MUST]** The artifact directory name MUST be the chicsession name verbatim (no timestamp, no engine-generated `run_id`, no UUID). The chicsession name is the user-visible identity of the run; the artifact dir name MUST match.
- **A4 [MUST]** Workflow activation without a chicsession MUST NOT create an artifact directory. The existing code path already requires a chicsession before constructing `WorkflowEngine` (`app.py` `_prompt_chicsession_name` is called when `_chicsession_name is None`); this spec does not change that pre-condition.
- **A5 [MUST]** Activating a different workflow under the same chicsession name (a non-typical flow; reachable only by deactivating, then re-prompting and entering the same name) MUST reuse the same artifact directory. Old files from the prior workflow remain alongside new files. The spec does NOT partition the directory by `workflow_id`; switching workflows in a chicsession is the user's choice and the artifact dir is shared.

---

## 3. Path layout

- **P1 [MUST]** The artifact directory absolute path MUST be:

  ```
  <repo_root>/.claudechic/runs/<chicsession_name>/
  ```

  where `<repo_root>` is the launched-repo root (the path returned by `_get_root` in `chicsession_cmd.py`, which is `app._cwd` for the running app), and `<chicsession_name>` is the chicsession's `name` field used verbatim as a directory name.
- **P2 [MUST]** The directory `<repo_root>/.claudechic/runs/` is the **only** subdirectory of `.claudechic/` reserved for artifact directories. No other axis MAY claim this subdirectory. Names other than `runs/` (e.g. `workflow_runs/`, `artifacts/`) MUST NOT be used.
- **P3 [MUST]** The chicsession-name-as-dir-name pattern requires the chicsession name to be filesystem-safe. The existing chicsession code does not validate this (see `chicsession_cmd.py` `_handle_save`). If the chicsession name contains a path separator (`/` or `\`) or starts with `.`, the engine MUST refuse to construct (raise a `ValueError` with a clear message naming the chicsession). This validation is NEW; it lives at engine construction, not at chicsession save (chicsession save is owned by another module and unchanged here).
- **P4 [MUST]** The path layout under `<repo_root>/.claudechic/` is:

  ```
  <repo_root>/.claudechic/
  ├── config.yaml          (project config; owned by R4 axis)
  ├── hints_state.json     (hint lifecycle; owned by Boundary group B3)
  ├── phase_context.md     (engine-authored phase prompt; owned by R6 axis-agent)
  ├── runs/                ★ THIS AXIS
  │   └── <chicsession_name>/
  │       └── (agent-authored files)
  ├── workflows/           (project-tier workflow content; owned by R1)
  ├── global/              (project-tier rules + hints; owned by R1)
  └── mcp_tools/           (project-tier MCP tools; owned by R1)
  ```

  This spec asserts only the position of `runs/`. Other entries are listed for context; their precise layout is owned by their respective axes. `phase_context.md` and `runs/` MUST be siblings — `phase_context.md` MUST NOT be placed inside any `runs/<chicsession_name>/` directory by this axis.

---

## 4. Engine API

- **E1 [MUST]** `WorkflowEngine.__init__` (in `claudechic/workflow_engine/engine.py`, post-restructure: `claudechic/workflows/engine.py`) MUST accept a new keyword argument `artifact_dir: Path`. The argument is required (no default).
- **E2 [MUST]** `WorkflowEngine` MUST expose a read-only property `artifact_dir: Path` returning the path passed at construction.
- **E3 [MUST]** `WorkflowEngine.__init__` MUST create the directory if it does not exist (`artifact_dir.mkdir(parents=True, exist_ok=True)`). If creation fails (e.g., `OSError` due to permissions), construction MUST raise — the engine does NOT proceed without a working artifact directory.
- **E4 [MUST]** The integration layer (`app.py` `_activate_workflow`, around line 1616 where `WorkflowEngine(...)` is constructed) MUST compute the path as:

  ```python
  artifact_dir = self._cwd / ".claudechic" / "runs" / self._chicsession_name
  ```

  and pass it to `WorkflowEngine(...)`. This computation happens **after** `_chicsession_name` is set (after the `_prompt_chicsession_name` / `_auto_create_chicsession` step) and **before** `WorkflowEngine` is constructed.
- **E5 [MUST]** `WorkflowEngine.from_session_state` (engine.py:264) MUST also accept and forward the `artifact_dir` argument, matching `__init__`. Resume code paths (`app.py` chicsession resume) that reconstruct the engine MUST compute the same path the same way and pass it through.
- **E6 [MUST NOT]** The engine MUST NOT serialize `artifact_dir` into `to_session_state()` (engine.py:254). The path is derived from `(repo_root, chicsession_name)` at every construction; persisting it would couple chicsession files to absolute paths and break resume across machines.
- **E7 [SHOULD]** When testing, callers MAY pass a temp-directory path as `artifact_dir`. The engine MUST treat it as opaque — no further validation beyond E3.

---

## 5. Spawn-time env-var injection

- **V1 [MUST]** When a workflow is active (`self._workflow_engine is not None`), `app.py` `_make_options` (around line 950–960, where the existing env-var pattern lives) MUST add to the `env` dict:

  ```python
  env["CLAUDECHIC_ARTIFACT_DIR"] = str(self._workflow_engine.artifact_dir)
  ```

- **V2 [MUST]** When no workflow is active (`self._workflow_engine is None`), `_make_options` MUST NOT set `CLAUDECHIC_ARTIFACT_DIR` in the `env` dict. The variable MUST be absent from `env` (not set to `""`, not set to a path).
- **V3 [MUST]** The variable name MUST be exactly `CLAUDECHIC_ARTIFACT_DIR`. No alternative names (e.g. `CHIC_ARTIFACT_DIR`, `CLAUDECHIC_RUN_DIR`, `WORKFLOW_ARTIFACT_DIR`) MAY be used.
- **V4 [MUST]** The value MUST be an absolute path (the engine ensures this via E3 and E4 by constructing from `self._cwd`, which is absolute).
- **V5 [SHOULD]** The injection site sits adjacent to the existing `CLAUDE_AGENT_NAME` / `CLAUDECHIC_APP_PID` / `CLAUDE_AGENT_ROLE` block (app.py:951–958). Implementers SHOULD place the new lines immediately after that block to preserve the existing visual grouping.

---

## 6. Discovery for spawned sub-agents (Seam-F)

- **D1 [MUST]** Sub-agents spawned via the `spawn_agent` MCP tool (or any other path that produces a new `ClaudeSDKClient`) inherit `CLAUDECHIC_ARTIFACT_DIR` through the same `_make_options` injection. No separate engine-to-sub-agent propagation API is needed.
- **D2 [MUST]** All spawn / reconnect / model-switch / new-session code paths in `app.py` that call `_make_options` (verified call sites: `app.py` lines 1223, 3155, 3446, 3465, 3512, 3652) MUST pick up the env var automatically by virtue of going through `_make_options`. No code change is required at those call sites for this axis.
- **D3 [MUST NOT]** No alternative propagation mechanism (e.g. passing the path through MCP tool arguments, writing it to a temp file the sub-agent reads, embedding it in chicsession JSON) MAY be added by this axis. The single path is `_make_options` → `env` → SDK → sub-agent process.
- **D4 [SHOULD]** The `spawn_agent` MCP tool's documentation (in `claudechic/mcp.py` and the `spawn_agent` tool docstring) SHOULD note that spawned agents inherit the active workflow's artifact dir via this env var. Documentation prose is delegated to TerminologyGuardian.

---

## 7. Markdown placeholder substitution (R7.4)

- **M1 [MUST]** Workflow role markdown files (under `claudechic/defaults/workflows/<workflow_id>/<role>/*.md` post-restructure, plus user-tier and project-tier overrides) MUST use the literal token `${CLAUDECHIC_ARTIFACT_DIR}` to refer to the artifact directory. Hard-coded paths (e.g. `.project_team/<name>/`, `<repo>/.claudechic/runs/<name>/`) are forbidden by INV-12.
- **M2 [MUST]** `claudechic/workflows/agent_folders.py` (post-restructure: same module under `claudechic/workflows/`) `_assemble_agent_prompt` MUST substitute `${CLAUDECHIC_ARTIFACT_DIR}` in the assembled prompt before returning it. The substitution value is the env var's value at substitution time, retrieved from `os.environ.get("CLAUDECHIC_ARTIFACT_DIR", "")`. The substitution is a literal string-replace; no shell-style expansion (`$VAR`, `~`) and no other tokens are processed.
- **M3 [MUST]** If `CLAUDECHIC_ARTIFACT_DIR` is not set in the substitution context (e.g., `assemble_phase_prompt` is called outside a workflow run, or the engine has not yet set the env var on the current process), the token MUST be replaced with the empty string `""`. Agents reading the resulting prompt see `Write your spec to /spec.md` (path begins with `/spec.md`) — this is a deliberate failure mode, not silent. Tests MUST cover this case (see I-3 below).
- **M4 [MUST]** Both substitution AND env-var injection happen — they are NOT alternatives. The env var is the canonical primary mechanism; substitution is a UX convenience that means workflow markdown reads naturally without requiring agents to call `os.environ` lookup tools. INV-12 enforces that markdown does not bypass the token by hard-coding.
- **M5 [MUST]** The substitution covers `identity.md` and the per-phase markdown file. Both are read by `_assemble_agent_prompt` (engine.py:48–79); both go through M2.
- **M6 [MUST NOT]** No other tokens MAY be introduced by this axis. (`${CLAUDE_AGENT_NAME}`, `${CLAUDECHIC_APP_PID}`, etc., are not part of this spec; if a future axis wants them, that's a separate decision.)

---

## 8. Garbage collection / cleanup

- **G1 [MUST]** Artifact directories MUST NOT be auto-deleted by claudechic. Specifically:
  - `_deactivate_workflow` (`app.py` ~line 1894) MUST NOT delete or modify `<repo>/.claudechic/runs/<chicsession_name>/`. The existing code already only clears `<repo>/.claude/phase_context.md` (post-restructure: `<repo>/.claudechic/phase_context.md`); preserve that scope.
  - Closing the application MUST NOT delete artifact directories.
  - Closing or deleting a chicsession (no current claudechic command does this; future-proofing) MUST NOT delete the artifact directory.
- **G2 [MUST]** No `/clean` or `/gc` command for artifact dirs is in scope for this run. Users who want to delete old artifacts do so manually with the OS file manager / shell.
- **G3 [SHOULD]** A future iteration MAY add an explicit, user-confirmed cleanup command. The spec for this axis does NOT preclude such a future addition; it just does not include one.

---

## 9. Migration — existing `.project_team/<name>/` directories

- **N1 [MUST]** Pre-existing directories matching `<repo>/.project_team/<name>/` (the informal pattern this very `independent_chic` run uses; see `vision.md` and `STATUS.md`) MUST NOT be migrated by claudechic code. Per L17 + A9, no migration logic is added for any state file in this run; the artifact directory is no exception.
- **N2 [MUST]** No startup warning, no notice, no log line MAY be emitted by claudechic when it detects a `.project_team/` directory in the launched repo. A9 (no startup warnings) applies.
- **N3 [SHOULD]** The user (or implementer) MAY manually `mv .project_team/<name> .claudechic/runs/<name>` if they wish to carry forward existing artifacts. This is a one-time human action, not an automated step.
- **N4 [MUST NOT]** The new artifact directory name MUST NOT be `project_team/`. The directory name is `runs/` (per P1) regardless of which workflow produced the artifacts. `project_team` is one workflow among several (per `claudechic/defaults/workflows/`); `runs/` is the generic artifact root.

---

## 10. Relationship to `Chicsession.workflow_state`

- **C1 [MUST]** `Chicsession.workflow_state` (the `dict | None` field on `Chicsession`, persisted by the engine's `persist_fn` callback in `app.py` `_make_persist_fn`) and the artifact directory are **orthogonal**. Specifically:
  - `workflow_state` carries `{workflow_id, current_phase}` (per `WorkflowEngine.to_session_state`, engine.py:254). Small, structured, lives inside the chicsession JSON file.
  - The artifact directory is a filesystem location for agent-authored content. Path is derived (not persisted in chicsession JSON).
- **C2 [MUST NOT]** `WorkflowEngine.to_session_state` MUST NOT include `artifact_dir`. The chicsession JSON MUST NOT carry the path. (See E6.)
- **C3 [MUST NOT]** Agent-authored content MUST NOT be stored inside `Chicsession.workflow_state`. The dict is for engine state only.
- **C4 [MUST]** When a chicsession is resumed (`ChicsessionManager.load(name)`), the engine is reconstructed; the artifact directory path is recomputed deterministically from `(repo_root, name)` — they MUST match the prior run's path. This is the property that makes per-chicsession scope work for resume (per A2).

---

## 11. Multi-workflow concurrency

- **K1 [MUST]** Different chicsessions in the same launched repo MUST yield different artifact directories. The directory layout `<repo>/.claudechic/runs/<chicsession_name>/` provides this isolation by construction (different `chicsession_name` ⇒ different leaf dir).
- **K2 [MUST]** A single claudechic app instance has at most one active workflow at a time (existing invariant: `self._workflow_engine` is a single field, not a collection). This axis does NOT relax that invariant.
- **K3 [SHOULD]** Two claudechic app instances on the same launched repo, each with its own active chicsession, share the parent `.claudechic/` directory but use distinct `runs/<chicsession_name>/` leaf dirs. They do NOT interfere at the artifact-dir level. (They MAY interfere at other levels — `phase_context.md`, `hints_state.json` — but that is owned by other axes; not in scope here.)
- **K4 [MUST]** Two claudechic app instances both choosing the **same** chicsession name in the same repo is undefined behavior at the chicsession layer (atomic file replace, but no coordination across processes). The artifact-dir layer inherits this property: both instances will write into the same `runs/<chicsession_name>/` directory; conflicting writes are not coordinated by this axis. The chicsession layer's existing concurrency story (or lack thereof) bounds this case.

---

## 12. Relationship to `phase_context.md`

The agent-awareness axis (R6, owned by a separate axis-agent) is moving the engine-authored phase-context delivery to a new mechanism. This artifact-dir axis treats `phase_context.md` as an **engine-authored** file, NOT an artifact-dir entry.

- **X1 [MUST]** The post-restructure location of `phase_context.md` is `<repo>/.claudechic/phase_context.md` — a sibling of `<repo>/.claudechic/runs/`, NOT a child of any `runs/<chicsession_name>/`. (See P4 layout.)
- **X2 [MUST NOT]** This artifact-dir axis MUST NOT cause `phase_context.md` to be written inside a `runs/<chicsession_name>/` directory. If the agent-awareness axis-agent later moves `phase_context.md` to a chicsession-scoped location for isolation reasons, that decision is theirs; this axis does not block it but also does not perform that move.
- **X3 [MUST]** Agents reading `<repo>/.claudechic/phase_context.md` (via Claude Code's auto-load or via the R6 hook mechanism) and agents reading `<repo>/.claudechic/runs/<chicsession_name>/...` (via the artifact dir) MUST be able to do so independently. The two paths share a parent (`.claudechic/`) but no other coupling.
- **X4 [MUST NOT]** This axis MUST NOT modify the `_write_phase_context` function (`app.py` ~line 1828) beyond what is required by the boundary work (moving the path from `.claude/` to `.claudechic/`, owned by Boundary group B). Where `_write_phase_context` lands its file is determined by the Boundary group + the R6 axis; this artifact-dir axis only asserts that the file is NOT inside `runs/<chicsession_name>/`.

---

## 13. Test points (implementer-testable invariants)

These extend INV-11 and INV-12 from `specification/composability.md`. The boundary-test axis-agent owns the test harness; this section specifies which behaviors MUST be covered.

- **I-1 [MUST]** **Env var set when active.** A claudechic app with an active workflow and an active chicsession `foo` MUST have `CLAUDECHIC_ARTIFACT_DIR` in the env passed to a freshly spawned agent, with value equal to `<repo>/.claudechic/runs/foo` as an absolute path. Test: spawn an agent in such a state; inspect the `env` dict passed to `ClaudeSDKClient`. (Covers V1, V3, V4, INV-11.)

- **I-2 [MUST]** **Env var unset when inactive.** A claudechic app with no active workflow MUST NOT have `CLAUDECHIC_ARTIFACT_DIR` in the env passed to spawned agents. Test: spawn an agent without activating a workflow; assert the key is absent. (Covers V2.)

- **I-3 [MUST]** **Markdown substitution.** Given a phase markdown file containing the literal text `Write to ${CLAUDECHIC_ARTIFACT_DIR}/spec.md`, `assemble_phase_prompt` invoked with the env var set to `/tmp/test-run` MUST return a string containing `Write to /tmp/test-run/spec.md` and NOT the raw token. With the env var unset, the same call MUST return `Write to /spec.md` (token replaced with empty string). (Covers M2, M3, M5.)

- **I-4 [MUST]** **Resume yields same dir.** Save a chicsession `foo` while a workflow is active; deactivate the workflow; resume `foo`; reactivate the same workflow. The artifact-dir path computed at the second activation MUST equal the first activation's path. Test: assert `engine.artifact_dir` is bytewise-equal across the two activations. (Covers A2, C4.)

- **I-5 [MUST]** **No hard-coded artifact-dir paths in markdown.** A grep-test over `claudechic/defaults/workflows/**/*.md` (and any tracked user-tier / project-tier markdown if discoverable in CI) MUST find zero occurrences of the regex `\.claudechic/runs/` or `\.project_team/`. Markdown files use the `${CLAUDECHIC_ARTIFACT_DIR}` token instead. (Covers M1, INV-12.)

- **I-6 [MUST]** **Engine creates dir on construction.** Constructing `WorkflowEngine` with `artifact_dir=<some/new/path>` MUST result in `<some/new/path>` existing on disk after the constructor returns. (Covers E3.)

- **I-7 [MUST]** **No serialization of artifact_dir.** `engine.to_session_state()` MUST NOT include the key `artifact_dir`. Test: assert `"artifact_dir" not in engine.to_session_state()`. (Covers E6, C2.)

- **I-8 [SHOULD]** **Unsafe chicsession name rejected.** Constructing `WorkflowEngine` with an `artifact_dir` whose final segment contains `/`, `\`, or starts with `.` (when computed from a malformed chicsession name) MUST raise `ValueError`. Test: drive the failure path explicitly. (Covers P3.)

---

## 14. What this axis-spec does NOT cover

To preserve lane separation:
- **Loader / 3-tier walk / override resolution (R3):** owned by the loader-resolution axis-agent.
- **Agent-awareness mechanism, including phase_context.md delivery (R6):** owned by the agent-awareness axis-agent. This axis only asserts X1–X4 about layout collision.
- **Boundary classification + test (R5):** owned by the boundary-test axis-agent. Note: every write site introduced by this axis (`engine.__init__` `mkdir`, agent-authored writes inside the artifact dir) is `primary-state` and resolves to `<repo>/.claudechic/runs/...`, satisfying R5.1.
- **Wording of agent-facing prose mentioning the artifact dir, including the `spawn_agent` docstring update in D4:** owned by TerminologyGuardian.
- **Worktree symlink propagation (R8):** the existing `.claudechic/` symlink work covers `runs/` for free; no additional spec needed here.
- **UI surfacing (e.g., showing the artifact dir path in the sidebar):** out of scope; no current UI surface displays it.

---

*End of axis spec for workflow artifact directories.*
