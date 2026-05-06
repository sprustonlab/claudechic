# Engine-seam axis findings

Author: engine-seam axis-agent
Date: 2026-04-29
Scope: sub-features A (workflow template variables) and B (dynamic roles)

---

## Sub-feature A: workflow template variables

### User-visible delta (one sentence)
Workflow YAML manifests and per-role markdown files can reference
`$STATE_DIR` (per-workflow scratch dir under `~/.claudechic/workflow_library/...`)
and `$WORKFLOW_ROOT` (the launched repo cwd) and the engine substitutes the
absolute paths at check execution and prompt assembly time -- so a
coordinator can write `ls $STATE_DIR/STATUS.md` in an advance check
without hardcoding paths.

Concrete user who notices: anyone running `/project_team` whose workflow
YAML or coordinator markdown contains `$STATE_DIR` -- today on our base
those tokens reach the shell unsubstituted (latent bug, see Cross-cutting
findings).

### Contract-surface impact
- `WorkflowEngine.__init__` adds two optional kwargs (`workflow_root`,
  `state_dir`) -- back-compat additive.
- `WorkflowEngine.from_session_state` adds the same two kwargs -- additive.
- New attribute / property `WorkflowEngine.state_dir` (`Path | None`).
- New module `claudechic/paths.py` exporting `WORKFLOW_LIBRARY_ROOT` and
  `compute_state_dir(workflow_root, project_name) -> Path`.
- New on-disk state location `~/.claudechic/workflow_library/<key>/<name>/`.
  See "State-dir map" -- this is a NEW state surface.
- `assemble_phase_prompt` and `create_post_compact_hook` gain a
  `variables: dict[str, str] | None` kwarg -- additive.

No change to the workflow YAML SCHEMA per se -- abast's expansion is
literal `str.replace`, not a parser-level affordance, so any string in
any check param participates with no spec-side declaration.

### Skeptic Q1-Q6 verdicts
- Q1 (deployment context): NO. Coordinator-driven workflows that need
  to write status files into a stable directory are exactly our usage.
- Q2 (breaking public contract): NO. All changes are additive; the
  unexpanded literal is a "deliberate, visible failure mode" matching
  abast's `${CLAUDECHIC_ARTIFACT_DIR}` policy.
- Q3 (abast-specific infra): NO. `paths.py` is stdlib + pathlib only.
  Reuses our existing `~/.claudechic/` boundary.
- Q4 (one-sentence delta): YES, see above.
- Q5 (simpler in-tree change at 80%): partial. We could just add a
  resolver for the existing `${CLAUDECHIC_ARTIFACT_DIR}` token everywhere
  and document that as the way to do "state dir". But the existing
  artifact-dir mechanism is COORDINATOR-SET (via `set_artifact_dir`
  MCP tool during a Setup phase) and lazy. abast's `$STATE_DIR` is
  ENGINE-COMPUTED and eager (available the moment the engine is built,
  before any Setup phase runs). Different shape -> different value.
- Q6 (regresses a property): MILD. We currently have an INV
  (Group E `_validate_artifact_path`) banning `.claude/` ancestors in
  artifact paths. abast's `$STATE_DIR` lives under
  `~/.claudechic/workflow_library/...` -- under `.claudechic/`, not
  `.claude/`, so the ban does not bite. But adopting abast's resolver
  AS-IS would mean two state surfaces with overlapping purpose; see
  Cross-cutting findings.

### Composability verdict
- Recommended outcome: **adapt**
- Blocking deps:
  - Decide ONE resolver or TWO (see substitution-mechanism crystal).
  - If TWO, document the law: which token wins which scope, and when
    each is set.
  - If ONE, pick a token name (`$STATE_DIR` vs `${CLAUDECHIC_ARTIFACT_DIR}`)
    and migrate the bundled YAML / markdown.
  - The latent dead-`$STATE_DIR` tokens already in our defaults
    (testing-specification phase additions from `65a6c78`) need
    a resolver one way or the other.
- Reasoning: abast's substitution code is small and mechanical; the
  hard part is reconciling it with our existing
  `${CLAUDECHIC_ARTIFACT_DIR}` machinery. The substitution itself
  composes cleanly (uniform `str.replace` over `params` values);
  the SEAM is whether the engine should compute `state_dir` itself
  (abast: yes, eager) or have the coordinator set it via MCP tool
  (us: yes, lazy). I recommend keeping the `set_artifact_dir` tool
  and ALSO adding `$STATE_DIR` / `$WORKFLOW_ROOT` as engine-computed
  defaults -- they answer different questions (per-run artifacts vs
  per-workflow scratch) and the dead-token problem demands a
  resolver regardless.

---

## Sub-feature B: dynamic roles

### User-visible delta (one sentence)
When you activate a workflow whose manifest declares
`main_role: coordinator`, the main agent's `agent_type` flips from the
new `DEFAULT_ROLE = "default"` sentinel to `coordinator` for the
duration of the activation, so role-scoped guardrails like
`roles: [coordinator]` actually fire on the main agent's tool calls --
without dropping and re-establishing the SDK connection.

Concrete user who notices: anyone running `/project_team` whose
coordinator role has rules like `prefer_ask_agent` (currently in our
project_team.yaml, scoped to `roles: [coordinator]`) -- today our
closure-based dynamic resolution accomplishes the same effect by
reading `engine.manifest.main_role` (always returns `coordinator`
during activation), so the user-visible behaviour is largely the same.
The mechanism is different, which matters for sub-agents and for
introspection.

### Contract-surface impact
- `Agent.__init__` default for `agent_type` changes from `None` to
  `"default"`. **This IS a public-contract change** for anyone who has
  `if agent.agent_type is None` in third-party code or in
  guardrail rule predicates. Inventory needed across:
  - `mcp.py:980,983` -- `if not agent.agent_type:` falsy check
    (will now be truthy since `"default"` is truthy). Behavioural
    change required.
  - `widgets/content/tools.py:296`, `formatting.py:220` -- both
    handle empty string acceptably.
- `agent_manager.py` options factory signature gains `agent: Agent`
  parameter -- ChatApp's `_make_options` consumes it and reads
  `agent.agent_type`/`agent.effort` dynamically. Internal protocol
  change, no SDK contract impact.
- `_guardrail_hooks` adopts `agent: Agent | None` parameter and
  resolves role via `lambda: agent.agent_type` instead of via the
  workflow engine's manifest.
- `ManifestLoader` rejects `main_role: default` with a `LoadError`.
  New constraint on the workflow YAML schema -- additive (no current
  workflow uses `default` as its main_role).
- `DEFAULT_ROLE = "default"` constant exported from
  `workflows/agent_folders.py`. We previously had it (cherry-pick
  `1d3f824`, reverted in `ec604bc`); re-introducing it is part of
  this work.
- On-disk session schema: unchanged. `agent_type` is not persisted
  in chicsession entries (verified -- `ChicsessionEntry` only stores
  `name`, `session_id`, `cwd`).

### Skeptic Q1-Q6 verdicts
- Q1 (deployment context): NO. Role-scoped rules ARE the use-case.
- Q2 (breaking public contract): **YES (mild).** `agent.agent_type`
  default changes from `None` to `"default"`. Migration path: audit
  the 4 known call sites (`mcp.py` is the load-bearing one) and
  rewrite the falsy checks to `agent.agent_type in (None, "default")`
  or to `agent.agent_type != DEFAULT_ROLE`. Tests on abast's side
  (`tests/test_phase_injection.py`) cover the new semantics.
- Q3 (abast-specific infra): NO. The Agent-into-options-factory trick
  is just a parameter-passing change; we already have the
  `_options_factory` signature ourselves.
- Q4 (one-sentence delta): YES, see above. Modest given that our
  closure-based dynamic resolution already produces the same effect
  for the main agent (the visible behaviour delta is small;
  the mechanism delta is what the test infra cares about).
- Q5 (simpler in-tree change at 80%): YES, partially. Our existing
  closure already resolves the main agent's role to
  `engine.manifest.main_role` dynamically. The remaining gap is
  introspection (`agent.agent_type` outside the hook closure -- e.g.
  `mcp.py` reads it for filtering broadcast targets) and the
  DEFAULT_ROLE sentinel for explicit "no role" semantics. A minimal
  in-tree change (just flip `agent.agent_type` in `_activate_workflow`
  and accept the `agent.agent_type is None` -> `agent.agent_type == "default"`
  call-site sweep) would deliver 80%+ without the options-factory
  refactor.
- Q6 (regresses a property): NO meaningful regression provided the
  4 call-site sweep is done. The `agent_type=None` -> `"default"`
  change is intentional, with the loader's `main_role: default`
  rejection preserving the role/sentinel disjointness.

### Composability verdict
- Recommended outcome: **adapt**
- Blocking deps:
  - Sub-feature A is NOT a hard blocker (no shared code path), but
    `DEFAULT_ROLE` lives in `workflows/agent_folders.py` which A
    also touches; for atomicity adopt them in one commit series.
  - The 4 call-site sweep for `agent.agent_type` semantics.
  - Decision on whether to keep our closure-based main-role
    resolution alongside abast's per-agent flip (see Cross-cutting
    finding "Dynamic roles vs in-memory phase delivery").
  - Tests in `tests/test_phase_injection.py` already updated by
    `8f99f03` -- cherry-pick them with the feature.
- Reasoning: the abast mechanism is cleaner (per-agent state on the
  Agent itself, hooks read that state) and supports introspection
  beyond the hook closure. Our closure-based dynamic resolution
  works for the main agent only because exactly one main agent
  exists per app instance; it does NOT generalise to sub-agents.
  abast's mechanism does. Adopting A+B together fixes the latent
  dead-`$STATE_DIR` bug AND aligns role lifecycle with sub-agent
  introspection in one go.

---

## Cross-cutting findings

### Substitution-mechanism crystal (Q1)

We have THREE substitution mechanisms on the combined base, plus a
fourth (worktree path templates) at config-time:

| Mechanism | Syntax | Token(s) | Resolved at | Resolved by | Scope |
|---|---|---|---|---|---|
| Worktree path template | `${...}` | `${repo_name}`, `${branch_name}`, `$HOME`, `~` | Worktree creation | `features/worktree/` config helper | Filesystem path string |
| Workflow artifact dir (Group E) | `${...}` | `${CLAUDECHIC_ARTIFACT_DIR}` | Phase prompt assembly + command-output check | `workflows/_substitute.py` | Markdown content + check `command` strings |
| abast `$STATE_DIR` | `$VAR` (no braces) | `$STATE_DIR` | Check execution + prompt assembly | `WorkflowEngine._run_single_check` + `assemble_phase_prompt` | Any string param of any check; markdown |
| abast `$WORKFLOW_ROOT` | `$VAR` (no braces) | `$WORKFLOW_ROOT` | Same as `$STATE_DIR` | Same | Same |

**Are these ONE axis or many?** ONE axis (string template substitution
on workflow content), expressed inconsistently. Two syntaxes
(`$VAR` vs `${VAR}`), three resolvers (`features/worktree/`,
`workflows/_substitute.py`, `WorkflowEngine._run_single_check` +
`assemble_phase_prompt`), three SCOPES (filesystem path, workflow
content + check command, workflow content + any check param).

**Compositional law that lets them compose:** none currently. The
tokens have non-overlapping NAMES (no two resolvers race for the
same token), but the syntactic inconsistency means a user cannot
ask "where can I use template variables?" and get a single answer.
The `${...}` vs `$...` split is the smell.

**Does abast's `$STATE_DIR` make `${CLAUDECHIC_ARTIFACT_DIR}` redundant
(or vice versa)?** They answer different questions:
- `$STATE_DIR` is engine-computed, eager, per-WORKFLOW (one per
  workflow_id × project_root).
- `${CLAUDECHIC_ARTIFACT_DIR}` is coordinator-set via
  `set_artifact_dir` MCP tool during the Setup phase, lazy,
  per-RUN (one per workflow run). The coordinator can choose where
  it lives; it can be NOT under `~/.claudechic/`.

So **NOT redundant** -- they are two distinct semantics that
unfortunately got two distinct syntaxes. Recommendation:

- **Adopt one resolver** that handles both `$STATE_DIR` and
  `${CLAUDECHIC_ARTIFACT_DIR}` (and `$WORKFLOW_ROOT`) uniformly,
  with a documented "what each token means" table at the seam.
- **Pick one syntax going forward** (`${...}` is portable shell
  syntax and matches our existing convention) and DEPRECATE the
  bare-`$VAR` form. Bundled YAML can keep `$STATE_DIR` for now
  with the resolver tolerating both -- only the docs need updating.
- **Or** treat `$STATE_DIR` and `$WORKFLOW_ROOT` as a recognised
  exception (different semantic class -- engine-computed vs
  coordinator-set) and accept the two-syntax law as a feature.
  Less clean but lower-churn.

### State-dir map (Q2)

Current state locations on the combined base (engine-seam scope only):

| Location | Owner | Lifetime | Purpose |
|---|---|---|---|
| `~/.claudechic/config.yaml` | `config.py` | User | User-tier preferences |
| `~/.claudechic/chicsessions/<name>.json` | `chicsessions.py` | User | Multi-agent snapshots |
| `~/.claudechic/hints_state.json` | `hints/state.py` | User | Hint lifecycle persistence |
| `<repo>/.claudechic/config.yaml` | `config.py` | Project | Project-tier toggles |
| `<repo>/.claudechic/hits.jsonl` | `app.py` `HitLogger` | Project | Guardrail hit log |
| `<repo>/.chicsessions/<name>.json` | `chicsessions.py` | Project | (alt save location) |
| `<artifact_dir>/...` (coordinator-chosen) | `WorkflowEngine.set_artifact_dir` | Run | Per-run workflow artifacts |
| **(NEW from abast)** `~/.claudechic/workflow_library/<key>/<name>/` | `paths.compute_state_dir` | Workflow | Per-workflow scratch state |

**Does `workflow_library/` overlap, replace, or duplicate any of these?**
- Does NOT replace `chicsessions/` -- different shape (one dir per
  workflow vs one file per session).
- Does NOT replace `hints_state.json` -- different scope (per-
  workflow vs per-user globally).
- DOES overlap with the coordinator-chosen `artifact_dir` semantically
  -- both want to be "the place where the workflow's STATUS.md and
  userprompt.md live". The difference is who picks the path:
  - artifact_dir: coordinator picks (any path under `cwd`, not under
    any `.claude/`).
  - workflow_library: engine picks (`~/.claudechic/workflow_library/<key>/<name>/`).
- Hole: there is no "where should workflow scratch state live"
  convention. Group E gave the coordinator the choice; abast
  takes the choice away and centralises it. Both are defensible;
  picking one matters for documentation and for the dead-`$STATE_DIR`
  bug fix.

**Recommendation:** keep `set_artifact_dir` (the coordinator can choose
to override with a path that makes sense for the project), AND add
abast's `compute_state_dir` as the DEFAULT location so `$STATE_DIR`
has a value before Setup runs. Document that `$STATE_DIR` is the
"baseline" and `${CLAUDECHIC_ARTIFACT_DIR}` is the "coordinator
override". Both expand identically through the same resolver. The
two-token redundancy is the price of supporting both eager and
lazy semantics.

### Dynamic roles vs in-memory phase delivery (Group D) -- Q3

Our Group D law: phase prompts are assembled in-memory via
`assemble_phase_prompt(workflow_dir, role_name, current_phase, artifact_dir)`
and sent to the active agent as the kickoff message body
(`_send_to_active_agent`). No on-disk userprompt.md write. The
PostCompact hook re-runs `assemble_phase_prompt` on `/compact` to
re-inject context. See `app.py:1922-1958` for the kickoff path.

abast's `accf332` does the same in spirit but with one extra trigger:
on `_activate_workflow` it ALSO flips `agent.agent_type = main_role`,
which means subsequent guardrail hook evaluations (which read
`agent.agent_type` dynamically via the closure
`lambda: agent.agent_type`) start applying the coordinator's
role-scoped rules immediately.

**Do they compose?** YES, additively.
- Group D's in-memory delivery is unaffected by abast's role flip --
  delivery is content (the markdown), the role flip is metadata
  (the `agent.agent_type` attribute).
- The PostCompact hook has BOTH our in-memory re-assembly AND
  abast's `variables=` kwarg threading -- merge cleanly: assemble
  with the variables dict to get expansion for free.
- No re-injection path is needed when the role flips -- the role
  flip is independent of phase content. The only re-injection
  trigger is `/compact` (PostCompact hook), unchanged from our
  current behaviour.

**Where they collide:** `_merged_hooks` and `_make_options` need to
take an optional `agent: Agent | None` to thread the agent into the
guardrail closure. Our current code threads only `agent_type: str`
(see `app.py:1028,1062`). The change is mechanical but the diff is
moderate.

### 3-tier loader (Group C) vs `main_role: default` rejection -- Q4

Abast's loader rejection is per-FILE, applied during dict-based
parsing in `loader.py:256-272`. The check is:

```python
if main_role == DEFAULT_ROLE:
    errors.append(LoadError(...))
    main_role = None
```

Our 3-tier loader pulls `main_role` from the WINNING tier's manifest
at resolution time (`loader.py:861-866`). So the rejection rule needs
to apply per-file (lower tiers' overridden manifests still might
have invalid `main_role: default`) AND at the resolved layer (the
final `WorkflowData.main_role`).

**Override pattern that the rejection rule breaks:** none. `default`
is reserved by the loader; users who write a workflow with
`main_role: default` get a `LoadError` regardless of tier. There is
no override pattern that DEMOTES `main_role` to `default` (i.e. you
can't "un-promote" the main agent via a YAML override) -- if a
project-tier override drops the `main_role` key entirely, the
loader resolves to `None` (no flip).

**Question: if a user-tier override sets `main_role: foo` over a
package-tier `main_role: default` -- what happens?** The package-tier
manifest is rejected at parse time (LoadError); the user-tier
manifest sets `main_role: foo` and wins. Net result: `foo` is the
resolved main_role and the package-tier file has a parse error
visible in `LoadResult.errors`. Reasonable behaviour.

**Recommendation:** apply the rejection at parse time in our
3-tier loader -- one block in the dict-parsing branch, similar to
abast's. The resolution-layer code in `_resolve_workflows` does NOT
need to re-check (the per-file check is sufficient because rejected
manifests have `main_role = None` after rejection, and that value
is what propagates to `WorkflowData`).

### Agent-into-options-factory contract surface (Q5)

abast adds `agent: Agent` to:

- `AgentManager._options_factory(...)` callsite (in
  `agent_manager.py:160` and `:201`).
- `ChatApp._make_options(...)` (in `app.py:984`).
- `ChatApp._merged_hooks(...)` and `ChatApp._guardrail_hooks(...)`.

Then inside the guardrail hook closure: `lambda: agent.agent_type`
replaces our `lambda: engine.manifest.main_role`.

**Does this change `AgentObserver`, `PermissionHandler`, MCP tool
schemas, or on-disk session schema?** NO.
- `AgentObserver` -- not touched. The observer still receives status
  / text / tool events; nothing role-related.
- `PermissionHandler` -- not touched. Permission dispatch is by tool
  name; role plays no part there.
- MCP tool schemas (`spawn_agent`, `message_agent`, etc.) -- not
  touched. `spawn_agent type=` already exists on our base.
- On-disk session / chicsession schema -- not touched.
  `ChicsessionEntry` does not persist `agent_type` (verified in
  `chicsessions.py`); on resume the engine re-promotes the main
  agent in `_restore_workflow_from_session`.

**Inventory of consumers of `agent.agent_type`:**
- `mcp.py:201,209,217,225,259,270,280,296` -- spawn flow uses it
  to validate role folders exist + assemble role prompts.
- `mcp.py:980,983,993` -- broadcast-on-advance uses it to filter
  targets and assemble per-role phase prompts.
- `widgets/content/tools.py:296`, `formatting.py:220` -- task widget
  display uses `subagent_type` from tool input (different attribute,
  unrelated).
- (post-abast) guardrail hook closure -- reads it on every rule
  evaluation.

The `mcp.py:980,983` paths are the load-bearing ones for the
default-change semantics (Q2 above).

### `003408a` re-pick recommendation (Q6)

Historian established: `accf332` does NOT hard-depend on `003408a`
(engine-level `params.setdefault("cwd", workflow_root)` works
without the `CommandOutputCheck.cwd=` ctor param). And `accf332`
satisfies all three of `18061ec`'s revert prerequisites (DEFAULT_ROLE,
main_role promotion, broadcast-on-advance).

**From a composability lens, do they belong on the SAME axis or two
complementary axes?** Same axis (cwd-pinning for advance checks),
expressed at TWO LAYERS (engine-level vs ctor-level). This is a
defence-in-depth pattern -- the engine-level `setdefault` is
sufficient for the typical case (engine builds the check), but the
ctor-level default protects callers who construct
`CommandOutputCheck` directly (unit tests, hypothetical custom
check builders). Not a duplication smell -- a layered defence.

**Engine-level vs ctor-level precedence:** `params.setdefault("cwd", ...)`
fills in a value ONLY if the key is missing. So the precedence is:
1. Manifest YAML `cwd:` param wins over both.
2. Engine-level `workflow_root` wins over ctor-level `cwd=None`.
3. Ctor-level explicit `cwd=` wins over... nothing, because the engine
   builds the check via `_build_check(augmented_decl)` which reads
   `params` -- it doesn't pass `cwd=` to the ctor as a kwarg.

So in the engine code path, ctor-level `cwd` is dead. It only matters
for non-engine callers (tests). No precedence collision risk.

**Recommendation: re-pick `003408a` AS PART OF this work.** The
prerequisites are now natively satisfied by accf332. Re-applying it
gives us:
- Defence-in-depth on the cwd pinning (tests can construct
  CommandOutputCheck directly without losing cwd).
- The original guardrail/advance-check messaging improvements
  (which are useful independent of the cwd pinning).
- A coherent test-suite (the 6 stranded `tests/test_phase_injection.py`
  tests pass under accf332 + 8f99f03; re-applying 003408a does not
  break anything new).

The re-pick should be a separate cherry-pick AFTER the accf332
cluster lands, not bundled with it -- keeps the cluster boundary
clean and matches the historian's "additive, not duplicative"
characterisation.

---

## Terminology refinements

Updates to working glossary:

- **template variable**: refine to "string token in workflow content
  (YAML or markdown) substituted by claudechic at expansion time."
  TWO scopes: (1) check params at engine execution time, (2) prompt
  markdown at assembly time. THREE tokens currently:
  `${CLAUDECHIC_ARTIFACT_DIR}` (coordinator-set, lazy),
  `$STATE_DIR` (engine-computed, eager),
  `$WORKFLOW_ROOT` (engine-computed, eager).

- **dynamic role**: refine to "agent role attribute (`agent.agent_type`)
  that mutates at runtime; guardrail hooks read the live value on
  every rule evaluation via a closure." Distinct from "agent_type
  passed at spawn" (static).

- **promote / demote**: refine to "set/clear `agent.agent_type` on
  workflow activation/deactivation. Promotion replaces the
  `DEFAULT_ROLE` sentinel with the workflow's `main_role`; demotion
  restores `DEFAULT_ROLE`. No SDK reconnect needed because hooks
  read the attribute lazily."

- **DEFAULT_ROLE sentinel**: the literal string `"default"` declared
  in `workflows/agent_folders.py`. Reserved -- workflows MUST NOT
  declare `main_role: default`. Carries no workflow-specific
  guardrails; agents at this role are visible to global rules only.

- **state_dir** (NEW): per-workflow scratch directory at
  `~/.claudechic/workflow_library/<project_key>/<workflow_id>/`.
  Engine-computed at activation, available before any phase runs.
  Distinct from `artifact_dir` (coordinator-chosen, set during Setup).

- **workflow_root** (NEW): the launched-repo cwd, captured by the
  engine at activation. Used for both `$WORKFLOW_ROOT` substitution
  and as the default `cwd` for `command-output-check` execution
  (Pinning).

---

## New collisions discovered

1. **Latent dead `$STATE_DIR` tokens on our base.** Our defaults
   already contain unsubstituted `$STATE_DIR` in:
   - `defaults/workflows/project_team/project_team.yaml` (lines 44, 52)
   - `defaults/workflows/project_team/{user_alignment,terminology,skeptic,composability}/testing-specification.md`
     (line 4 of each)
   These came in via the cherry-pick of abast's `7dcd488` (testing
   sub-cycle, `65a6c78` on our side) but the resolver they need
   ships in `accf332`. **Adopting accf332 fixes this latent bug.**
   Skipping it leaves the dead tokens behind -- they'd reach the
   shell as literal `$STATE_DIR/foo`, which the shell would then
   expand against the empty environment, producing `/foo` -- the
   "deliberate, visible failure mode" from `_substitute.py` but
   without the explicit empty-string contract.

2. **`mcp.py:980,983` falsy `agent.agent_type` checks.** With the
   default change `None` -> `"default"`, these become unconditionally
   truthy and the broadcast-target filter logic changes meaning.
   Worth verifying with a test before merge.

3. **Group E artifact-dir validation rejects `.claude/` ancestors but
   NOT `.claudechic/` ancestors.** abast's `compute_state_dir` writes
   into `~/.claudechic/workflow_library/...`, which is fine. But if
   we converge on a single resolver that handles both scopes, the
   `_validate_artifact_path` rule needs to be re-examined: should
   it allow paths under `~/.claudechic/workflow_library/` (where
   abast wants state to live) or not? Not a hard collision but a
   policy decision.

4. **`HitLogger` path moved** in abast's app.py from
   `<cwd>/.claude/hits.jsonl` to `<cwd>/.claudechic/hits.jsonl`.
   We already have it at `<cwd>/.claudechic/hits.jsonl` (verified
   in `app.py:1656`), so this is a clean alignment. Tutorial
   markdown still references `.claude/hits.jsonl` (3 hits in
   `defaults/workflows/tutorial/learner/{graduation,rules}.md` and
   `tutorial.yaml`) -- minor doc drift; worth fixing under the
   E sub-feature.

---

## Per-feature recommendation summary

| Feature | Outcome | Blocking deps | One-line reason |
|---------|---------|--------------|-----------------|
| A: workflow template variables | adapt | resolver convergence decision; bundled-YAML rewrite | Fixes a latent dead-token bug we already shipped; mechanism is sound but composes awkwardly with our `${CLAUDECHIC_ARTIFACT_DIR}`. |
| B: dynamic roles | adapt | `mcp.py:980,983` falsy-check sweep; tests cherry-picked from `8f99f03` | Cleaner mechanism than our closure-based main-role resolution; supports sub-agent introspection; minor public-contract change for `agent.agent_type` default. |
| (003408a re-pick) | adopt (after A+B land) | none -- accf332 satisfies the prerequisites that originally caused the revert | Defence-in-depth for cwd pinning; restores the guardrail-messaging improvements; the 6 stranded `test_phase_injection.py` tests pass under accf332+8f99f03+003408a. |
