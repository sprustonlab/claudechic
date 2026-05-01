# Engine-Seam Axis Specification

**Author:** engine-seam axis-agent (Composability lens)
**Phase:** Specification
**Scope:** sub-features A (workflow template variables) and B (dynamic
roles). Per UserAlignment scope-guard correction, `003408a` is OUT-OF-CLUSTER
and is FLAGGED-only here -- no adopt/skip recommendation. See section 3.
**Files in scope:** `claudechic/workflows/engine.py`, `claudechic/workflows/loader.py`,
`claudechic/workflows/agent_folders.py`, `claudechic/paths.py` (new in abast),
`claudechic/agent.py`, `claudechic/agent_manager.py`, plus the engine-side
of `claudechic/app.py` (`_activate_workflow`, `_deactivate_workflow`,
`_make_options`, `_merged_hooks`, `_guardrail_hooks`).

---

## 0. Executive verdict (per-feature)

| Sub-feature | Outcome | Blocking deps |
|---|---|---|
| **A1. `${WORKFLOW_ROOT}` substitution** | adopt | none |
| **A2. `$STATE_DIR` substitution + `paths.py` + `~/.claudechic/workflow_library/`** | skip | superseded by our `${CLAUDECHIC_ARTIFACT_DIR}` |
| **A3. Engine-level `params.setdefault("cwd", workflow_root)` for advance checks** | adopt (with caveat) | hard prerequisite on `claudechic/checks/builtins.py` factory + ctor changes (NOT in accf332). See section 3 flag. |
| **A4. Two-pass auto-then-manual advance check ordering** | adopt | none |
| **B1. `DEFAULT_ROLE = "default"` sentinel in `agent_folders.py`** | adopt | none |
| **B2. `Agent.agent_type` defaults to `"default"` (not `None`)** | adopt | requires test rename in `tests/test_phase_injection.py` (abast already supplies this in `8f99f03`) |
| **B3. Promote/demote `self._agent.agent_type` in `_activate_workflow`/`_deactivate_workflow`** | adapt | hand-merge into our heavily evolved activation flow |
| **B4. `agent=` param threading through `_make_options` / `_merged_hooks` / `_guardrail_hooks` / `agent_manager.create_unconnected`** | adopt | depends on B3 |
| **B5. Loader rejection of `main_role: default`** | adopt | depends on B1 |

**Headline finding (most material to the user):** abast's accf332 alone is
*partially functional* on our base. The engine-level `cwd` pinning in feature
A3 is **silently dropped** by our check-factory registry because our
`CommandOutputCheck.__init__` does not accept `cwd=`. The factory updates
that make the pinning effective do NOT live in `accf332` (verified:
`git show --stat accf332 -- claudechic/checks/` returns empty). They live
in the precursor commit `003408a`, which is OUT-OF-CLUSTER and FLAGGED-only
per the scope guard. The `tests/test_engine.py` additions in `8f99f03`
(`test_workflow_root_pins_command_check_cwd`, `test_workflow_root_pins_file_exists_check`,
`test_manifest_cwd_overrides_workflow_root`) all assume those factory updates
exist; they will FAIL on our base if we adopt accf332 without somehow
restoring the `checks/builtins.py` ctor + factory changes.

**Implication for A3 (in-cluster):** A3's adoption requires the `cwd`/`base_dir`
ctor params on `CommandOutputCheck` / `FileExistsCheck` / `FileContentCheck`
plus the factory updates that pass those params through. The user's
follow-up decision on whether to re-investigate `003408a` (out-of-cluster)
is independent. See section 3 for the flag.

---

## 1. Composability axis decomposition

Five engine-seam axes are at play, with one cross-axis crystal hole.

### Axis 1 -- Substitution mechanism (token syntax + resolver)

| Value | Origin | Token syntax | Resolved by |
|---|---|---|---|
| `${CLAUDECHIC_ARTIFACT_DIR}` | ours (Group E) | `${VAR}` | `_substitute.py::substitute_artifact_dir` (literal `str.replace`) |
| `${repo_name}`, `${branch_name}`, `$HOME` | ours (worktree) | `${VAR}` (and `$HOME` special) | `features/worktree/git.py::_expand_worktree_path` |
| `$STATE_DIR`, `$WORKFLOW_ROOT` | abast (accf332) | `$VAR` | engine `_run_single_check` + `agent_folders.assemble_phase_prompt` (literal `str.replace` over a dict) |

Three substitution mechanisms, **two syntaxes**. Worktree templates live in
a different domain (user config, expanded once at worktree-create time)
and don't conflict with workflow-token substitution. The real collision is
between `${CLAUDECHIC_ARTIFACT_DIR}` and `$STATE_DIR`.

### Axis 2 -- State location (where this run's scratch lives)

| Value | Mechanism | Path |
|---|---|---|
| Coordinator-chosen artifact dir (ours) | `set_artifact_dir` MCP tool, called in Setup phase | configurable -- typically `<repo>/.project_team/<name>/` or `<repo>/.claudechic/runs/<name>/` |
| Auto-computed workflow_library (abast) | `paths.compute_state_dir(cwd, workflow_id)` at activation | `~/.claudechic/workflow_library/<project_key>/<workflow_id>/` |
| Chicsessions (ours, separate concept) | `ChicsessionManager(<root>)` | `<repo>/.chicsessions/<name>.json` (named multi-agent snapshots) |
| Hints + hits (ours) | hardcoded | `<repo>/.claudechic/hints_state.json`, `<repo>/.claudechic/hits.jsonl` |

The first two are direct competitors -- both name "where does this workflow
run write its scratch?" with different binding strategies and different
locations. Adopting both = a 5th state location for the same concept.
Chicsessions and hints/hits are different concerns (named snapshots,
persistent hint state) and stay where they are.

### Axis 3 -- Role-resolution timing

| Value | Mechanism |
|---|---|
| Static at spawn (sub-agents on both forks) | `agent_type=` argument set once, never mutates |
| Dynamic via manifest (ours, current main agent) | guardrail-hook closure reads `self._workflow_engine.manifest.main_role` on every PreToolUse |
| Dynamic via mutable agent (abast, all agents) | guardrail-hook closure reads `agent.agent_type`; activation MUTATES `self._agent.agent_type = main_role` |

Both dynamic variants achieve the same end behavior for guardrails. abast's
also propagates to the SDK env var (`CLAUDE_AGENT_ROLE`) and the post_compact
hook on next options-build because `_make_options` reads `agent.agent_type`.

### Axis 4 -- Check resolution base (workflow root or process cwd)

| Value | Mechanism | Coverage |
|---|---|---|
| Process cwd (current behavior on our base, post-`18061ec` revert) | check ctors don't accept `cwd`/`base_dir`; `_resolve_against` helper absent | nothing pinned |
| Workflow-root pinned (003408a + accf332) | engine sets `params.setdefault("cwd", workflow_root)`, factory passes `cwd=p.get("cwd")` through, ctor stores it | command-output, file-exists, file-content |

This axis only delivers value if BOTH halves ship: engine setdefault is
inert without factory updates.

### Axis 5 -- Advance-check execution policy

| Value | Mechanism |
|---|---|
| Sequential as declared (current) | `for check in advance_checks: ...` |
| Two-pass auto-then-manual (abast) | `[*auto, *manual]` -- avoids prompting user when an automated check is already going to fail |

Cleanly independent. Pure improvement. No conflict path.

### Cross-axis crystal hole: A3 has an out-of-cluster prerequisite

abast's `accf332` adds `params.setdefault("cwd", str(self._workflow_root))`
in `engine._run_single_check` for `command-output-check`. But our factory
registration is

```python
register_check_type(
    "command-output-check",
    lambda p: CommandOutputCheck(command=p["command"], pattern=p["pattern"]),
)
```

The `cwd` key in `params` is silently ignored -- `CommandOutputCheck.__init__`
on our base accepts only `command` and `pattern`. The factory updates
that make the cwd pass-through work

```python
register_check_type(
    "command-output-check",
    lambda p: CommandOutputCheck(
        command=p["command"], pattern=p["pattern"], cwd=p.get("cwd")
    ),
)
```

are NOT in `accf332`. Verified: `git show --stat accf332 -- claudechic/checks/`
returns empty. They live in the precursor `003408a` (`83 lines` in
`claudechic/checks/builtins.py`), which is OUT-OF-CLUSTER and FLAGGED-only
per the scope guard. Same story for `file-exists-check` (`base_dir`) and
`file-content-check` (`base_dir`).

**What this means for A3:** the engine-side change in accf332
(`params.setdefault(...)`) is necessary but not sufficient. To make A3
deliver its headline UX, the implementation must also include the
factory + ctor changes in `claudechic/checks/builtins.py`. Whether those
are obtained by (a) hand-porting just the ctor + factory diff inline
during A3 implementation, or (b) the user separately re-investigating
`003408a` as a follow-up cherry-pick, is a USER decision. The engine-seam
axis flags this hard prerequisite without pre-deciding the path.

---

## 2. Per-feature analysis

### Feature A -- workflow template variables

#### A1. `${WORKFLOW_ROOT}` substitution -- ADOPT

Resolves to `self._cwd` (the launched-repo root). New token, no overlap with
existing tokens. Genuinely useful (lets workflow YAML and per-role markdown
write absolute references like `${WORKFLOW_ROOT}/.git/HEAD` without baking
in a path).

**Implementation note (compositional):** keep the `${VAR}` syntax (matches
our existing `${CLAUDECHIC_ARTIFACT_DIR}` and worktree `${repo_name}`
conventions; explicit braces avoid accidental greedy matches like
`$STATE_DIRECTORY` -> "$STATE_DIR" + "ECTORY"). Fold into
`_substitute.py` as a second entry in a token-keyed dict.

**Before vs after (Skeptic Q4):** "User authors a workflow check that
needs to grep `${WORKFLOW_ROOT}/.git/HEAD` in the user's launched repo --
previously required a brittle relative path that broke when sub-agents had
a different cwd; now resolves to an absolute path at engine load time."

**Delta vs abast's `$WORKFLOW_ROOT`:** abast uses `$VAR` syntax. We
**rename to `${WORKFLOW_ROOT}`** for consistency. Workflow YAML / per-role
markdown changes in `accf332` (3 files in `defaults/workflows/project_team/`
+ tutorial) will need a one-line s/`\$STATE_DIR`/${STATE_DIR}/g and
s/`\$WORKFLOW_ROOT`/${WORKFLOW_ROOT}/g adjustment during the merge --
modulo the A2 decision below which drops $STATE_DIR entirely.

#### A2. `$STATE_DIR` + `paths.py` + `workflow_library/` -- SKIP (superseded)

abast's mechanism: at workflow activation, the engine auto-computes
`~/.claudechic/workflow_library/<project_key>/<workflow_id>/` and binds it
as `state_dir`. Workflow YAML references `$STATE_DIR` to put scratch files
there.

Our equivalent: `set_artifact_dir(<absolute>)` MCP tool called in Setup
phase, persisted in chicsession state, substituted as
`${CLAUDECHIC_ARTIFACT_DIR}` in workflow YAML and per-role markdown.

The two mechanisms point at the **same axis-2 concern** ("where does this
run's scratch live?") with different binding strategies:

| | Coordinator-chosen artifact dir (ours) | Auto-computed state_dir (abast) |
|---|---|---|
| Where it lives | flexible (`<repo>/.project_team/...`, `.claudechic/runs/...`, anywhere) | always under `~/.claudechic/workflow_library/...` |
| Binding | manual (coordinator calls `set_artifact_dir`) | automatic (engine ctor) |
| Persistence | chicsession `workflow_state.artifact_dir` | implicit (recomputed from cwd + workflow_id every activation) |
| Validation | `_validate_artifact_path` blocks `.claude/` dirs, null bytes, traversal | none |
| User-visible token | `${CLAUDECHIC_ARTIFACT_DIR}` | `$STATE_DIR` |

Our coordinator-chosen approach has three properties abast's lacks: location
flexibility (a lab can keep state in-repo for git-versioning if they want),
explicit validation, and chicsession-persisted truth so resumes are stable.
Adopting both = a 5th place workflow state lives, with overlapping purpose.

**Skip recommendation rationale:**
- `paths.py` -- not adopted; we don't introduce `~/.claudechic/workflow_library/`.
- `compute_state_dir` -- not adopted.
- `_workflow_root` ctor param on `WorkflowEngine` -- adopt under a different
  name (we already have `cwd` ctor param at `engine.py:133`; reuse it).
- `_state_dir` ctor param -- not adopted.
- `$STATE_DIR` token -- not adopted; workflow YAML continues to use
  `${CLAUDECHIC_ARTIFACT_DIR}` as before.
- abast's project_team and tutorial YAML rewrites that introduce
  `$STATE_DIR` -- not adopted; our existing `${CLAUDECHIC_ARTIFACT_DIR}`
  rewrites already cover those check commands.

**Before vs after (Skeptic Q4):** N/A (skip outcome -- no change).

**Skeptic Q5 ("does a simpler in-tree change deliver 80% of the benefit at
20% of the cost?"):** Yes. Our existing `set_artifact_dir` mechanism IS the
simpler in-tree change for the same purpose. Adopting `$STATE_DIR` adds
duplication, not capability.

#### A3. Engine-level `params.setdefault("cwd", workflow_root)` -- ADOPT (with caveat)

This is the substantive UX win in feature A. Sub-agents whose cwd has
drifted no longer false-fail advance checks because the engine pins the
working directory to the launched-repo root.

**Implementation (engine side):**
```python
# in engine._run_single_check
if self._cwd is not None:  # we already have self._cwd ctor param
    if check_decl.type == "command-output-check":
        params.setdefault("cwd", str(self._cwd))
    elif check_decl.type in ("file-exists-check", "file-content-check"):
        params.setdefault("base_dir", str(self._cwd))
```

Reuses our existing `WorkflowEngine.__init__(..., cwd: Path | None = None)`
parameter (we don't introduce abast's separate `_workflow_root`). The
plumbing already exists at `engine.py:133-141` for `_validate_artifact_path`.

**HARD PREREQUISITE on `claudechic/checks/builtins.py`:** the engine-side
setdefault is inert without matching ctor + factory changes:
- `CommandOutputCheck.__init__` must accept `cwd: str | Path | None = None`
  and pass it to `asyncio.create_subprocess_shell(..., cwd=self.cwd)`.
- `FileExistsCheck.__init__` must accept `base_dir: ...` and resolve
  relative paths against it (helper: `_resolve_against`).
- `FileContentCheck.__init__` must accept `base_dir: ...` similarly.
- Factory registrations must pass `cwd=p.get("cwd")` / `base_dir=p.get("base_dir")`.

These changes do NOT live in `accf332`. They are FLAGGED separately
(see section 3). The implementer must obtain them somehow before A3
ships, otherwise A3 is a no-op for command/file checks.

**Precedence semantics:** explicit YAML `cwd:` wins (setdefault no-ops when
key exists). Then ctor reads from params. Standard fallback chain:
explicit YAML > engine workflow-root > None (process cwd). setdefault
makes this clean by construction; 8f99f03's
`test_manifest_cwd_overrides_workflow_root` codifies the precedence.
This precedence question is FLAGGED for the user's eventual
out-of-cluster review; in-cluster, setdefault gives the right behavior
either way.

**Before vs after (Skeptic Q4):** "Coordinator agent in `project_team`
spawns a sub-agent in a worktree subdir. The sub-agent's
`advance_phase('specification')` call previously false-failed the
`ls .project_team/*/SPECIFICATION.md` check because the subprocess
inherited the sub-agent's drifted cwd. After this change, the engine
pins the check's cwd to the main agent's cwd (the workflow root), so the
relative pattern resolves against a stable location and advance succeeds."

#### A4. Two-pass auto-then-manual check ordering -- ADOPT

Cleanly independent. Avoids prompting the user for confirmation when an
automated check is already going to fail. Pure improvement. Take it.

**Implementation:** 4-line change in `_advance_phase` advance-check loop.

**Before vs after (Skeptic Q4):** "User clicks 'advance phase'. Before:
manual-confirm dialog pops first, user clicks yes, then automated check
fails -- two interactions for one failure. After: automated check fails
silently, manual confirm never shown -- one interaction."

#### Skeptic Q1-Q6 for feature A (combined A1+A3+A4)

| Q | Answer | Rationale |
|---|---|---|
| Q1 (problem doesn't apply?) | No | Sub-agent cwd drift causing false advance-check failures is a real symptom on our base today. |
| Q2 (breaking changes to public contract?) | No | `${WORKFLOW_ROOT}` is a new optional token; no existing tokens removed. Engine `cwd` ctor param already exists. |
| Q3 (depends on abast-specific infra we lack?) | Partial yes | A3's engine-side change requires matching ctor + factory changes in `claudechic/checks/builtins.py` that do not live in accf332. The implementer must port those alongside A3 (or the user separately decides on the out-of-cluster `003408a` follow-up). Either path keeps A3 in-cluster; only the source of the small `checks/builtins.py` diff differs. |
| Q4 (concrete user-visible delta?) | Yes (A3 + A4) | See per-feature deltas above. |
| Q5 (simpler in-tree change at 80/20?) | Mixed | A2 yes (skip in favor of existing `set_artifact_dir`); A1+A3+A4 no (these IS the simpler change). |
| Q6 (regresses a property we rely on?) | No | A4 changes ordering of advance checks but AND semantics preserved. No persisted state changes. |

No "yes" severe enough to skip A1+A3+A4. A2 has a Q5 yes, hence skip.

### Feature B -- dynamic roles

#### B1. `DEFAULT_ROLE = "default"` sentinel -- ADOPT

12-line addition to `claudechic/workflows/agent_folders.py`. Identical to
the previously-reverted `1d3f824`. The F401 unused-import lint that
triggered `ec604bc` is now resolved -- accf332 introduces 7+ callers across
`loader.py`, `app.py`, and (post-003408a re-pick) `mcp.py`. Verified via
`git grep DEFAULT_ROLE accf332df9...` (multiple references in 3 files).

**Before vs after (Skeptic Q4):** Internal -- no direct user-visible delta.

#### B2. `Agent.agent_type` defaults to `"default"` -- ADOPT (with test rename)

Currently `self.agent_type = agent_type` at `agent.py` line 195; abast
changes to `self.agent_type = agent_type if agent_type is not None else "default"`.

**Skeptic Q2 (breaking changes?):** Mild yes -- existing tests asserting
`agent.agent_type is None` would fail. `8f99f03` already renames the test
`test_agent_type_defaults_to_none` -> `test_agent_type_defaults_to_default_sentinel`
and updates assertions. Migration burden is one rename + assertion update;
abast already supplies it. Take the test rename with the feature.

**Note (terminology + skeptic):** abast's `agent.py` uses the string
literal `"default"` rather than importing `DEFAULT_ROLE`. Slight
inconsistency in abast's own diff. Recommend our adaptation imports
`DEFAULT_ROLE` to keep the sentinel name DRY.

#### B3. Promote/demote `self._agent.agent_type` -- ADAPT (manual merge)

Abast's `_activate_workflow` (line 1742 of accf332's app.py) does:
```python
if wf_data.main_role and self._agent is not None:
    self._agent.agent_type = wf_data.main_role
```
and `_deactivate_workflow` (line 2050) reverts to `DEFAULT_ROLE`.

Our `_activate_workflow` (line 1787 of our app.py) is **substantially
evolved** since merge-base:
- Restore-vs-fresh-vs-cancel dialog (`_prompt_workflow_restore_or_fresh`)
- chicsession naming prompt (`_prompt_chicsession_name`,
  `_auto_create_chicsession`)
- Phase-prompt delivery via kickoff message body (Group D's in-memory
  approach -- no on-disk userprompt.md)
- `assemble_phase_prompt` called with `artifact_dir=...` (Group E)
- Existing `cwd=self._cwd` ctor param to `WorkflowEngine`

The activation flow is too different to cherry-pick mechanically. The
promotion is a 3-line insertion in two places (post-engine-creation in
fresh path AND in restore path), demotion is similar. Hand-merge.

**Adaptation plan:**
1. After `WorkflowEngine` construction in `_activate_workflow` (both fresh
   and restore branches), add:
   ```python
   if wf_data.main_role and self._agent is not None:
       self._agent.agent_type = wf_data.main_role
   ```
2. In `_deactivate_workflow`, before `self._workflow_engine = None`, capture
   `prior_main_role`; after, demote `self._agent.agent_type = DEFAULT_ROLE`
   if it currently equals `prior_main_role`.
3. In `_restore_workflow_from_session` (our equivalent of abast's restore
   path), replicate the promotion.

**Promote/demote semantics (terminology):**
- "Promote" = mutate `self._agent.agent_type` from `DEFAULT_ROLE` to
  `wf_data.main_role`.
- "Demote" = mutate back to `DEFAULT_ROLE`.
- **NO identity swap** -- agent name, cwd, session_id, history all preserved.
- **NO prompt re-injection** -- the kickoff prompt for the new role is
  delivered via our existing Group D in-memory phase delivery path
  (independent of role mutation).
- **NO history clear** -- demotion is a pure attribute write.
- Sub-agents spawned via `spawn_agent type=X` are unaffected; they keep
  their explicit role across activate/deactivate.
- Interaction with `spawn_agent type=` (003408a's mcp.py): on adoption of
  003408a, `spawn_agent` with no `type=` defaults to `DEFAULT_ROLE` and
  emits a warning if a workflow is active.

#### B4. `agent=` param threading -- ADOPT

Mechanical changes:
- `app.ChatApp._guardrail_hooks(agent=, agent_role=)` -- prefer
  `lambda: agent.agent_type` when `agent` is provided.
- `app.ChatApp._merged_hooks(agent=, agent_type=)` -- pass `agent` through
  to `_guardrail_hooks`.
- `app.ChatApp._make_options(..., agent=)` -- when `agent` is provided,
  read effective role from `agent.agent_type`.
- `agent_manager.AgentManager.create*` -- pass `agent=` to options factory.

**Conflict with our existing manifest-bound dynamic resolution:** our
current `_guardrail_hooks` already does dynamic role resolution, but reads
from `self._workflow_engine.manifest.main_role` (a closure over the engine).
Abast's approach reads from `agent.agent_type` (a closure over the agent).
Both deliver dynamic role for the main agent. Abast's is cleaner because
the role lives on the agent (its natural home) and no special-case for
"no agent_role provided -> read from manifest" branch is needed.

**Replace the closure**: drop the `def effective_role(): return
self._workflow_engine.manifest.main_role` branch, replace with the
agent-based variant. Sub-agents (`agent_role=` provided as string) keep
the static path.

**Inter-axis dependency flag for ui-surface axis:** B4 also threads `agent=`
through `app.py` handlers like `on_chicsession_actions_workflow_picker_requested`,
`_reconnect_agent`, etc. UI-surface axis must verify these handler call
sites get the new `agent=` arg.

#### B5. Loader rejection of `main_role: default` -- ADOPT

16-line addition to `claudechic/workflows/loader.py`. Lands cleanly --
small upstream patch, our loader has +891 lines of independent evolution
but the `main_role` parsing site is not on a hot conflict line.
Validation only; no runtime impact for valid manifests.

Adapts to TerminologyGuardian's "DEFAULT_ROLE sentinel" recommendation
(loader treats it as reserved).

#### Skeptic Q1-Q6 for feature B

| Q | Answer | Rationale |
|---|---|---|
| Q1 | No | Role-scoped guardrails (`roles: [coordinator]`) are real and used by `project_team`'s `no_push_before_testing` rule. |
| Q2 | Mild yes | `Agent.agent_type` default semantics change (`None` -> `"default"`). Mitigated by 8f99f03's test rename. No public-API contract change beyond that. |
| Q3 | No | All needed infra is internal. (003408a is recommended but not strictly required for B's role lifecycle to work.) |
| Q4 | Yes | "User activates `project_team`. Main agent now subject to coordinator-role guardrails (e.g. `no_push_before_testing`). Previously, those rules required spawning a separate typed coordinator agent." |
| Q5 | Mixed | Could keep our manifest-bound resolution and just add `agent.agent_type` mutation as a notification. But abast's storage-on-agent design is genuinely cleaner; Q5 doesn't strongly bite. |
| Q6 | No | Existing static-role behavior for sub-agents preserved. Demotion logic explicitly only touches the main agent. |

#### Inter-axis flags for B

- **B3's promote/demote calls** sit inside `_activate_workflow` /
  `_deactivate_workflow`, which the **ui-surface axis** also touches
  (those handlers connect to footer buttons, the workflow picker screen,
  and chicsession activation). UI-surface must coordinate handler call
  paths.
- **B4's `agent=` threading** ripples through `agent_manager.AgentManager`
  and the worktree-aware reconnection paths. Worktree code is owned by
  ui-surface (in this run's plan).

---

## 3. Flagged context: out-of-cluster precursor `003408a`

**Status:** OUT-OF-CLUSTER per scope guard. **No adopt/skip recommendation
from this axis.** Surfaced here only as context the user may want for a
follow-up investigation.

#### Why it shows up in this axis report

The engine-seam touches `claudechic/checks/builtins.py` indirectly: A3's
engine-side `params.setdefault("cwd", workflow_root)` requires matching
ctor + factory changes in that file. Those changes are NOT in accf332;
they are in the precursor `003408a` (which we previously cherry-picked
as `8abb2f9` and reverted as `18061ec`). Per the scope-guard, the team
does not pre-decide what to do about `003408a`. The implementer of A3
must obtain the small `checks/builtins.py` diff somehow (hand-port inline,
or wait for the user's follow-up decision on `003408a`).

#### Factual context (from historian V1; not a recommendation)

- accf332 introduces two of the three prerequisites cited in our `18061ec`
  revert message (DEFAULT_ROLE sentinel, `main_role` promotion). The third
  (broadcast-on-advance to typed sub-agents) is already on our base
  pre-merge-base. So the stated reason for the original revert is, factually,
  no longer present once accf332 lands.
- accf332 does NOT touch `claudechic/checks/builtins.py` or
  `claudechic/mcp.py` (verified via `git show --stat`). So the
  cwd-on-CommandOutputCheck ctor and the spawn_agent role-validation
  messaging in mcp.py are NOT supplied by accf332 alone.
- Source-inspection rebuts the cwd-precedence concern from triage: engine
  `setdefault("cwd", ...)` defers cleanly to a YAML-explicit `cwd:`
  (setdefault no-ops when key present). 8f99f03's
  `test_manifest_cwd_overrides_workflow_root` codifies this. Whether to
  add ctor-level `cwd` (003408a) ON TOP of engine-level `cwd` (accf332)
  is a separate question -- they don't conflict; the second is additive
  to the first. **Flagged for the user's future 003408a decision; no
  present-day recommendation from this axis.**

#### Implications for the user (informational only)

- The user may wish to re-investigate `003408a` as a follow-up after
  accf332 lands, since the original revert reasons are factually no
  longer present. Or the user may prefer to keep 003408a out of tree
  permanently and have the implementer hand-port just the `checks/builtins.py`
  diff that A3 needs. Either is consistent with the scope guard.
- Q8 (cwd precedence): no precedence conflict between engine-level and
  ctor-level `cwd` -- they layer cleanly via setdefault. **Flagged for
  the user's eventual 003408a review; no current decision required.**
- Q9 (re-pick alongside accf332?): **no recommendation -- flagged for
  user follow-up.**

---

## 4. State-location collapse story

The "right collapse" we're recommending:

| Concept | Mechanism | Path | Adopted? |
|---|---|---|---|
| User config | `CONFIG` (in `~/.claudechic/config.yaml`) | `~/.claudechic/` | yes (existing) |
| Project config | `ProjectConfig` (in `<repo>/.claudechic/config.yaml`) | `<repo>/.claudechic/` | yes (existing) |
| Project hint state | `HintStateStore` | `<repo>/.claudechic/hints_state.json` | yes (existing) |
| Project guardrail hits log | `HitLogger` | `<repo>/.claudechic/hits.jsonl` | yes (existing -- this is what `accf332`'s app.py:1656 also writes) |
| Named multi-agent snapshots | `ChicsessionManager` | `<repo>/.chicsessions/<name>.json` | yes (existing -- different concept from workflow scratch) |
| **Workflow run scratch** | `set_artifact_dir(...)` MCP tool, persisted in chicsession | flexible: `<repo>/.project_team/<name>/`, `<repo>/.claudechic/runs/<name>/`, etc. | **yes, retained -- supersedes abast's $STATE_DIR** |
| ~~User-home workflow library~~ | ~~`paths.compute_state_dir`~~ | ~~`~/.claudechic/workflow_library/...`~~ | **no -- skipped per A2** |

Five state locations, each with distinct purpose. No 6th location for
workflow_library/.

---

## 5. Compositional law (final)

After adoption, the engine seam respects:

1. **Substitution law:** every workflow YAML / per-role markdown token uses
   `${VAR}` syntax. `_substitute.py` owns the resolver; both engine
   (`_run_single_check`) and prompt assembly (`agent_folders`) call it.
   Two tokens in v1: `${CLAUDECHIC_ARTIFACT_DIR}` and `${WORKFLOW_ROOT}`.

2. **Role-storage law:** every `Agent` instance has a non-None
   `agent_type` (DEFAULT_ROLE sentinel for unspecified). All role-aware
   subsystems (guardrail hooks, post_compact hook, env var) read from
   `agent.agent_type` at evaluation time. Mutations propagate by virtue
   of read-from-source.

3. **Check-resolution law:** every advance check resolves relative paths
   against the `WorkflowEngine._cwd` (the launched repo root), unless the
   manifest explicitly overrides via `cwd:` / `base_dir:`. Pinned via
   `setdefault` at engine, threaded through factory to ctor.

4. **State-location law:** each "where does X live?" concept has exactly
   one resolver; tokens never cross domains (a worktree-template token
   never appears in workflow YAML and vice versa).

---

## 6. Cross-axis flags for other axis-agents

- **ui-surface axis** must coordinate B3 hand-merge of promote/demote into
  `_activate_workflow` / `_deactivate_workflow` / `_restore_workflow_from_session`.
  These functions also embed UI flow (chicsession naming dialog, restore
  prompt). The role mutation is pure model -- the surrounding flow is UI.
  Specifically, ui-surface owns: `_prompt_chicsession_name`,
  `_prompt_workflow_restore_or_fresh`, the kickoff prompt send.

- **ui-surface axis** must verify B4's `agent=` arg threading does not
  break worktree-aware reconnection (`_reconnect_agent`, etc.).

- **guardrails-seam axis** must verify B4 doesn't change PreToolUse hook
  contracts that other guardrail logic depends on. The lambda
  `lambda: agent.agent_type` is a callable in the same shape as our
  current closure; should be drop-in.

- **guardrails-seam axis** -- if A3 is approved by the user, the
  `claudechic/checks/builtins.py` ctor + factory diff that A3 requires
  is small (~30 lines: the `cwd` ctor param + factory passes for the
  three check types + the `_resolve_against` helper). engine-seam owns
  this diff regardless of how it is sourced. Flag for guardrails-seam:
  if you reach a similar architectural conclusion about the
  `003408a` mcp.py / guardrails/hooks.py changes, coordinate framing
  with this axis -- both are cluster-internal needs that happen to share
  a name with an out-of-cluster commit.

### Coordination response to guardrails-seam (received 2026-04-29)

guardrails-seam decomposed `003408a` into 3 threads and asked engine-seam
to confirm ownership of (i) and (iii). Per UserAlignment's D4 correction,
no thread of `003408a` carries an adopt/skip recommendation from this
axis -- threads are framed as "user decides." Ownership confirmation:

- **(i) per-check `cwd`/`base_dir` ctor params in `claudechic/checks/builtins.py`**
  -- engine-seam **CONFIRMS ownership**. This is the same ~30-line ctor +
  factory diff already flagged in section 1 (cross-axis crystal hole) and
  section 3 as A3's hard prerequisite. The implementer ports this inline
  as part of A3 adoption OR coordinates with the user's eventual
  out-of-cluster `003408a` follow-up. Engine-seam does NOT pre-decide
  whether to source it from a 003408a re-pick or hand-port.

- **(ii) richer warn-rule reasoning text in `claudechic/guardrails/hooks.py`
  (~10 LOC)** -- engine-seam **DECLINES ownership**. `guardrails/hooks.py`
  is outside engine-seam's file scope (`workflows/`, `paths.py`, the
  engine side of `app.py`). guardrails-seam owns this thread. No batching
  with engine-seam's package; it should land independently on the
  guardrails axis if/when the user approves. Engine-seam does NOT
  pre-decide adopt/skip here.

- **(iii) `DEFAULT_ROLE` in `claudechic/mcp.py`** -- engine-seam owns the
  SUPPLY (the `DEFAULT_ROLE = "default"` declaration in
  `workflows/agent_folders.py`, sub-feature B1). Engine-seam **DECLINES
  ownership of the CONSUMPTION** in `claudechic/mcp.py` -- that file is
  outside engine-seam's file scope. The consumption depends on B1 (the
  import `from claudechic.workflows.agent_folders import DEFAULT_ROLE`
  must resolve), which engine-seam supplies as part of B1's adoption.
  Beyond that, the spawn_agent role-validation logic in mcp.py is a
  separate user decision in a separate file. guardrails-seam (which
  owns mcp.py's MCP-tool surface) is the natural owner. Engine-seam
  does NOT pre-decide adopt/skip here.

- **D-modal / D-digest.py SKIP context** (informational, from
  guardrails-seam): noted. Removes a conflict surface in `app.py` since
  D's `_merged_hooks` / `_guardrail_hooks` wiring is no longer competing
  with B4's `agent=` threading on the same lines. Confirms that
  engine-seam's B4 changes can land cleanly without merging against a
  parallel D wiring effort.

---

## 7. Summary table -- per-feature outcomes

| ID | Sub-feature | Outcome | Blocking deps | One-line user delta |
|---|---|---|---|---|
| A1 | `${WORKFLOW_ROOT}` token | adopt | none | Workflow YAML can absolutely-reference launched-repo paths without baking them in |
| A2 | `$STATE_DIR` + `paths.py` + `workflow_library/` | skip | n/a | n/a (skip) |
| A3 | engine `cwd`/`base_dir` setdefault | adopt (with caveat) | matching ctor + factory diff in `claudechic/checks/builtins.py` (NOT in accf332; implementer must port inline) | Sub-agent advance_phase calls no longer false-fail when cwd has drifted |
| A4 | two-pass auto-then-manual checks | adopt | none | Manual confirm dialog skipped when an automated check is already going to fail |
| B1 | `DEFAULT_ROLE` sentinel | adopt | none | Internal (no direct UX delta) |
| B2 | `Agent.agent_type` default = "default" | adopt | 8f99f03 test rename | Internal (no direct UX delta) |
| B3 | promote/demote on activate/deactivate | adapt | hand-merge into our `_activate_workflow` | Workflow main agent immediately subject to role-scoped guardrails on activation |
| B4 | `agent=` param threading | adopt | depends on B3 | Internal (no direct UX delta) |
| B5 | loader reject `main_role: default` | adopt | depends on B1 | Author of a workflow manifest sees a clear validation error if they accidentally name `main_role: default` |
| flag | `003408a` (out-of-cluster precursor) | **no recommendation; flagged for user follow-up** | n/a | Per scope guard, this axis does not pre-decide. accf332 unblocks 003408a (revert reasons no longer present per V1); user may wish to re-investigate as a separate follow-up. |

---

## 8. Gestalt one-liner (UserAlignment C2)

After this axis lands, **a user activating `project_team` from a worktree
sees role-scoped guardrails apply to their main agent immediately
(no SDK reconnect), and sub-agent `advance_phase` calls stop false-failing
because relative paths in advance_checks resolve against the workflow
root instead of the sub-agent's drifted cwd.**

(Conditional on the implementer porting the small
`claudechic/checks/builtins.py` ctor + factory diff that A3 requires;
see section 1 cross-axis crystal hole and section 3 flag.)

---

## 9. Open items for Specification phase

- Test pass under combined adoption: does `8f99f03` + accf332's
  engine-seam parts all green on our base post-merge? Historian's stranded-6
  prediction is strong but unverified.
- Workflow YAML rewrites in defaults (project_team + tutorial): substitute
  `$STATE_DIR` -> `${CLAUDECHIC_ARTIFACT_DIR}` per A2 skip; substitute
  `$WORKFLOW_ROOT` -> `${WORKFLOW_ROOT}` per A1 adopt. Confirm coordinator
  setup.md text uses our `set_artifact_dir` flow (it already does --
  `defaults/workflows/project_team/coordinator/setup.md` line 7+).
- `ec604bc`'s `_token_store` restoration must survive the merge. Verified
  present at `app.py:1655`. Implementer must NOT drop this line.
- A3's prerequisite `checks/builtins.py` diff: implementer must port
  inline as part of A3 adoption, OR coordinate with the user's eventual
  follow-up decision on out-of-cluster `003408a`. Either path is
  scope-guard-compliant.

---

## 10. B and A reframed -- agent-self-awareness lens (2026-04-29)

UserAlignment audited the team's framing and identified a unifying
throughline missed in initial decomposition: **the cluster's coherent
intent is "give the agent runtime self-awareness."**

- A teaches the agent its **paths** (where its workflow root and artifact
  dir are, substituted into its prompt content).
- B teaches the agent its **role** (the agent has a queryable runtime
  identity: `agent.agent_type`).
- C teaches the agent its **compute budget** (effort knob, out of axis).
- D teaches the agent **which rules govern it** (modal showing rules
  filtered by its identity; out of axis but symbiotic with B).
- E is concrete content for D (also out of axis).

This re-examination focuses on B (where the small-delta verdict was
acutely under-scoped) and A (less acute).

### B reframed -- it is the substrate, not a cleanup

#### Where `agent.agent_type` is consumed in accf332 (and dependents)

Source-traced consumption sites for `agent.agent_type` in accf332's diff:

1. **`Agent.__init__`** (B2) -- defaults to `"default"` sentinel. Single
   source of identity on every agent instance.
2. **`AgentManager._wire_agent_callbacks` / `connect_agent`** (B4) --
   passes `agent=agent` to options factory; options reads live
   `agent.agent_type` rather than a static snapshot.
3. **`ChatApp._guardrail_hooks`** -- returns
   `lambda: agent.agent_type` to PreToolUse hooks. **This is the
   substrate D's modal would query for "which rules apply to this
   agent."** D's rule filtering is meaningful only because B made the
   identity queryable.
4. **`ChatApp._merged_hooks` / `create_post_compact_hook`** -- on
   `/compact`, the role-specific phase prompt is re-assembled from
   `agent.agent_type`. **Identity persists across compaction** -- the
   agent doesn't lose its role when context window collapses.
5. **`ChatApp._make_options`** -- when `agent` is passed, `agent_type =
   agent.agent_type`; this propagates to `CLAUDE_AGENT_ROLE` env var.
   **The agent's subprocess can introspect its own role from env.**
6. **`ChatApp._activate_workflow` / `_deactivate_workflow` /
   `_restore_workflow_from_session`** (B3) -- mutates
   `self._agent.agent_type` on workflow lifecycle. **The workflow
   activation event teaches the agent its new role.**
7. **(out of cluster, in 003408a) `mcp.py::spawn_agent`** -- validates
   `type=` against role folders. **Spawned sub-agents inherit a
   queryable identity at creation.**
8. **(out of cluster, in 003408a) `mcp.py::advance_phase` broadcast** --
   filters typed sub-agents by `agent.agent_type`. **Phase advance
   broadcasts are routed by identity.**

Consumption sites are NOT spread across accidental call sites; every
role-aware subsystem reads from the same single source. The compositional
law from section 5 (every Agent has a queryable `agent_type`; subsystems
read from there at evaluation time) is the substrate the cluster is
quietly building.

#### Does the small-delta verdict still hold?

The OUTCOMES (B1/B2/B4/B5 = adopt; B3 = adapt) **do not change**.
Mechanics, conflict surfaces, and effort estimates from sections 0-7 are
correct. What changes is the **IMPORTANCE** of B in the cluster narrative:

- **Before:** "abast's storage-on-agent design is genuinely cleaner; Q5
  doesn't strongly bite" (positioned as a refactor with optional
  upside).
- **After:** "B is the substrate that makes role-aware features
  (including D's agent-filtered rules, post-compact role preservation,
  env-var introspection, broadcast routing) possible. It is not optional
  for any of those; it is the foundation."

**Skeptic Q5 reverses on the new framing.** Before: "could keep our
manifest-bound resolution and just add `agent.agent_type` mutation as a
notification. Less invasive." After: the manifest-bound resolution
**cannot** support the agent-self-identity surface because there is no
single mutable source the agent can introspect. Sub-agents have their
own roles; the manifest's `main_role` is global, not per-agent. To get
per-agent identity we need per-agent storage. There is no simpler
80/20 alternative.

**Skeptic Q4 (concrete user-visible delta) shifts but does not weaken.**
Before: "user activates `project_team`, main agent now subject to
coordinator-role guardrails." After: same user delta, plus:
"after `/compact`, the main agent's role-specific phase context
re-injects correctly because identity persisted; sub-agents spawned
mid-workflow inherit a validated role; advance_phase broadcasts route
to the right typed sub-agents."

#### Revised B recommendation

Outcomes unchanged from section 0:

| Sub-feature | Outcome | Blocking deps | Importance under new framing |
|---|---|---|---|
| B1 `DEFAULT_ROLE` sentinel | adopt | none | **foundational** (sentinel for "no workflow-specific identity") |
| B2 `Agent.agent_type` default = "default" | adopt | 8f99f03 test rename | **foundational** (every agent has a non-None identity) |
| B3 promote/demote on activate/deactivate/restore | adapt | hand-merge into our `_activate_workflow` | **the teaching event** -- workflow activation IS how the agent learns its role |
| B4 `agent=` param threading | adopt | depends on B3 | **the substrate plumbing** -- subsystems read from the same single source |
| B5 loader reject `main_role: default` | adopt | depends on B1 | **invariant guard** -- preserves the sentinel's reserved meaning |

#### Gestalts (UserAlignment C8)

- **User-side (B):** "User activates `project_team` and continues working
  in their main agent. The main agent is now subject to coordinator-role
  guardrails (e.g. the `no_push_before_testing` rule), survives
  `/compact` with role-specific phase context preserved, and sees its
  role exposed in `CLAUDE_AGENT_ROLE` env. No reconnect, no spawning a
  separate typed coordinator."
- **Agent-side (B):** "Agent gains a queryable runtime self-identity
  (`agent.agent_type`). On workflow activation it is taught its role;
  on deactivation it is restored to the default sentinel; across
  `/compact` it remembers. Every role-aware subsystem (guardrail rule
  filter, post-compact prompt, env var, MCP broadcast routing) reads
  from this single source. **This is the substrate D's rule-modal
  would query** if/when D ships."

### A reframed -- path teaching, no verdict shift

#### Per-token mapping to agent-self-awareness

| Token | Teaches the agent | Verdict (unchanged) |
|---|---|---|
| `${WORKFLOW_ROOT}` (A1) | "where my workflow root is" -- absolute path baked into prompt content | adopt |
| `${CLAUDECHIC_ARTIFACT_DIR}` (existing, retained per A2 skip) | "where I write my scratch artifacts" -- absolute path baked into prompt content | n/a (keep existing) |

A3 (engine-level cwd setdefault) is engine-side reliability, NOT direct
agent self-teaching -- it pins the engine's subprocess cwd, which the
agent doesn't perceive. But A3's UX win (sub-agent advance_phase calls
stop false-failing) IS user-visible.

A4 (two-pass auto-then-manual) is pure UX, also unchanged.

#### Verdicts under the new lens

A1, A3, A4 outcomes **unchanged**. A2 (`$STATE_DIR` + `paths.py` +
`workflow_library/`) **still skipped**. The agent absolutely needs to
know "where its scratch lives" -- that is exactly what
`${CLAUDECHIC_ARTIFACT_DIR}` already teaches it. Adding `$STATE_DIR`
would teach the agent a SECOND, conflicting "where my scratch lives"
answer. One path, one resolver, one teaching. Affirmed.

#### Gestalts (UserAlignment C8)

- **User-side (A):** "User authors a workflow check that needs to grep
  the launched repo's `.git/HEAD` -- they write `${WORKFLOW_ROOT}/.git/HEAD`
  in YAML and the engine resolves it to an absolute path at load time.
  Sub-agent advance_phase calls from worktree subdirs stop false-failing
  because the engine pins relative paths to the workflow root."
- **Agent-side (A):** "Agent's prompt content (assembled from
  `identity.md` + per-phase markdown) contains absolute path references
  that survived substitution: it knows where its workflow root is
  (`${WORKFLOW_ROOT}`) and where to write its artifacts
  (`${CLAUDECHIC_ARTIFACT_DIR}`). No relative-path resolution at runtime;
  paths are baked into the agent's instructions."

### Architecture calls re-examined

- **Substitution syntax convergence on `${VAR}`:** **affirmed.** The
  agent reads token-substituted content; the syntax it sees is irrelevant
  to it (substitution is opaque from the agent's perspective). For the
  AUTHOR side, `${VAR}` remains the right pick -- explicit boundaries
  avoid greedy matches like `$STATE_DIRECTORY` -> "$STATE_DIR" + "ECTORY".
  Agent-self-awareness lens does not change this call.
- **State-location skip (`paths.py`, `workflow_library/`):** **affirmed,
  with reinforced rationale.** Under agent-self-awareness, the agent
  needs to know ONE answer to "where is my scratch?" -- not two.
  `${CLAUDECHIC_ARTIFACT_DIR}` already teaches that. Adding
  `~/.claudechic/workflow_library/` as a SECOND path the agent learns
  about would be confusing both for the agent (which path is
  authoritative for this run?) and for the user (where do I look for
  artifacts?). The skip preserves single-source clarity.

### Collision-vs-composition with our existing main_role path (post-`a743423`)

Historian flagged that commit **`a743423` (2026-04-29, ours)** fixes
`test_main_agent_role_resolves_to_main_role` -- one of the 6 tests cited
as stranded in the `18061ec` revert message. The fix proves that on our
current base, after `_activate_workflow`, a coordinator-scoped rule DOES
fire for the main agent. So our base has **independently functional
main-role-resolution machinery**. The question is whether B3+B4 collide
with it or compose with it.

#### What our `a743423`-confirmed path actually does

Source-traced (`claudechic/app.py::_guardrail_hooks` lines 833-841 +
`tests/test_phase_injection.py::test_main_agent_role_resolves_to_main_role`):

```python
# claudechic/app.py::_guardrail_hooks (current, post-a743423)
if agent_role:
    effective_role: str | None | callable = agent_role
else:
    def effective_role() -> str | None:
        if self._workflow_engine:
            return getattr(self._workflow_engine.manifest, "main_role", None)
        return None
```

The closure asks the **workflow** for the role at hook-eval time; it
does NOT touch `self._agent.agent_type`. The test passes because the
closure resolves to `"coordinator"` once the engine is active.

#### What our path does NOT produce: agent-queryable `agent.agent_type`

`self._agent.agent_type` STAYS at whatever value the agent was
constructed with (typically `None` for the main agent). It is never
mutated on workflow activation. Verified: no
`self._agent.agent_type =` assignment exists in `app.py` outside of
spawn-time construction.

This means our path solves **exactly ONE of the 8 consumption sites**
listed earlier (the guardrail-hook role filter), and only because the
closure reads from the workflow side. The other 7 consumers do NOT
get the agent's post-activation role on our base today:

| Consumer | Our base | What's missing |
|---|---|---|
| `_guardrail_hooks` | works (manifest closure) | -- |
| `_make_options` -> `CLAUDE_AGENT_ROLE` env var | broken | env var still reflects spawn-time role (`None`) |
| `_make_options` -> SDK `agent_type` | broken | SDK sees None |
| `create_post_compact_hook` (main agent) | broken | role-specific phase prompt not re-injected on `/compact` |
| `mcp.py::spawn_agent` validation | n/a (out-of-cluster) | -- |
| `mcp.py::advance_phase` broadcast filter | n/a (out-of-cluster, but already on base via 66fa580/ca003a3) | filter reads `agent.agent_type` directly; works for typed sub-agents but not for the main agent (which is None) |
| Hypothetical D modal (filter rules by agent) | broken | nothing for D to query about the main agent's identity |
| Agent self-introspection | broken | no `agent.agent_type` to read; agent has no programmatic identity |

#### 8f99f03's test rewrite confirms abast's intent

8f99f03's rewrite of Test 13 changes the assertion to:

```python
assert main_agent.agent_type == "coordinator", ...
# ... and after _deactivate_workflow():
assert main_agent.agent_type == DEFAULT_ROLE, ...
```

This asserts directly on the agent attribute -- it would FAIL on our
base today because we never write `coordinator` to `main_agent.agent_type`.
Our `a743423`-passing test asserts only on rule firing, not on the
attribute itself. **The two tests test two different things**: ours
verifies the closure resolves correctly; 8f99f03's verifies the
agent's identity attribute carries the role. Both must be true under
the agent-self-awareness substrate; only the first is true on our
base today.

#### Collision-vs-composition verdict

- **B3 (promote/demote `self._agent.agent_type`) is NOT redundant.** Our
  existing path does NOT set `agent.agent_type`. B3 supplies the missing
  attribute mutation. **B3 composes** with our existing closure rather
  than colliding.
- **B4 (`agent=` threading)** REPLACES our manifest-bound closure with
  an agent-bound closure (`lambda: agent.agent_type`). The end result
  for guardrail-hook role resolution is identical (after B3 mutates
  the attribute, the new closure produces "coordinator" just like the
  old closure did via the workflow). **The collision is at exactly one
  site and is a clean swap.**
- **Test sequencing:** if we adopt B3+B4 we MUST also apply 8f99f03's
  test rewrites in the same merge. Our `a743423`-fixed test calls
  `_merged_hooks(agent_type=None)`, which under abast's signature
  becomes `_guardrail_hooks(agent=None, agent_role=None)` and falls
  back to the static path producing role=None. Test would break.
  8f99f03's rewrite passes `agent=main_agent` and asserts on
  `main_agent.agent_type`. The two changes are atomic.
- **No behavioral regression:** every assertion our `a743423`-fixed test
  makes (rule fires for main agent post-activation) ALSO holds under
  abast's path. Our test is a strict subset of 8f99f03's test.

#### Net effect on B's importance

Our existing path is a PARTIAL solution that solves the narrow
guardrail-hook case via a workflow-side closure. It does NOT provide
the agent-self-awareness substrate. **B3+B4 are the missing piece.**
Without them, 7 of the 8 consumption sites for `agent.agent_type` lack
the post-activation role. Hypothesized D's modal would have nothing
to filter by.

The historian's collision-vs-composition question resolves to:
**composition.** B3 supplies a state our base does not have. B4 swaps
the closure source by one site, with a strict-subset behavioral
contract. No verdict shifts; the importance UPLIFTS further -- our
existing partial solution makes the substrate's importance more
visible, not less.

### Summary of reframing impact

| Item | Outcome before | Outcome after | Change |
|---|---|---|---|
| A1 `${WORKFLOW_ROOT}` | adopt | adopt | none (importance: minor uplift) |
| A2 state-location | skip | skip | none (rationale reinforced) |
| A3 engine cwd setdefault | adopt | adopt | none (UX framing unchanged) |
| A4 two-pass checks | adopt | adopt | none |
| B1 `DEFAULT_ROLE` | adopt | adopt | importance: foundational |
| B2 `agent_type` default | adopt | adopt | importance: foundational |
| B3 promote/demote | adapt | adapt | importance: this IS the teaching event |
| B4 `agent=` threading | adopt | adopt | importance: substrate plumbing |
| B5 loader rejection | adopt | adopt | importance: invariant guard |

No verdict reversals. Three architecture calls (syntax, state-location
skip, A3 prerequisite framing) all re-affirmed under the new lens.

---

*End of engine-seam axis specification.*
