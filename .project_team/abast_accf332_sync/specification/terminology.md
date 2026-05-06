# Terminology Specification -- abast_accf332_sync

**Author:** TerminologyGuardian (Leadership agent)
**Phase:** Specification
**Cluster:** `accf332`, `8f99f03`, `2f6ba2e`, `a60e3fe`
**Authority:** Composability has final say on architecture. This document
flags collisions and proposes resolutions; it does not unilaterally rename.

All canonical names below are quoted verbatim from the cluster diff. Where
abast's commit message disagrees with the source, the source wins.

---

## 1. Domain terms from `userprompt.md`

The user's literal text (preserved by UserAlignment). Each is the
top-level frame for the investigation; all later terminology nests
under one of these.

| User term | Working definition (this run) | Notes |
|---|---|---|
| **sync** | bring our `main` into deliberate alignment with `abast/main` for the cluster -- adopt, adapt, skip, or partial per feature | Per UserAlignment FLAG 2: don't slide into pure-analysis mode; destination is integration if feasible. |
| **deep dive** | per-feature read of source + tests + companion commits; not just commit-message paraphrase | Distinguishes this run from the earlier `fork-divergence-2026-04-29.md` triage. |
| **commit `accf332`** | `accf332df9e3f1a9c13e5951bec1a064973b6c96`, "feat: add workflow template variables, dynamic roles, effort cycling, and guardrails UI" | Use the short SHA in prose; full SHA at first mention per section. |
| **its companions / four-commit cluster** | `accf332` + `8f99f03` (tests) + `2f6ba2e` (docs) + `a60e3fe` (modal stub-out). NON-CONTIGUOUS on `abast/main`: two MCP-refactor commits sit between `2f6ba2e` and `a60e3fe`. | Cluster boundary decided in Leadership, see `leadership_findings.md` §1. |
| **intent (cluster-level)** | the WHY across the four commits, not the WHAT of each | Must be answerable in one paragraph. |
| **pick it up** | adopt onto our `main` (cherry-pick, merge, or rewrite) | Outcome categories per Vision: `adopt / adapt / skip / partial`. |
| **reimplement on our base** | re-derive the user-visible behaviour using our existing scaffolding rather than cherry-picking abast's code | Distinct from `adopt`; the Skeptic flagged "reimplement" can also resolve to "do nothing." |
| **the team / final call** | team produces a per-feature recommendation; user has final yes/no per feature before any implementation | UserAlignment FLAG 3: don't widen outcomes without user awareness (already widened to 4 categories, on record). |

The four sub-feature labels in the commit title are user-quoted (they
come from abast's title); UserAlignment FLAG 1 binds the final report
to this exact wording. **Use them verbatim in deliverables**, even
where the source code uses different identifiers internally:

> "workflow template variables, dynamic roles, effort cycling, and guardrails UI"

---

## 2. Canonical glossary (from source, this cluster only)

Each entry: name, kind, canonical home, one-line definition. Source
quoted verbatim. Where abast's commit message contradicts the code,
the code is canonical; the discrepancy is flagged in §6.

### A. Workflow template variables (sub-feature A)

| Term | Kind | Canonical home | Definition |
|---|---|---|---|
| **template variable** | concept | `claudechic/workflows/agent_folders.py::assemble_phase_prompt` docstring | A `$NAME` token in workflow YAML or role markdown that the engine substitutes by literal `str.replace`. Caller-driven: callers decide which variables exist. |
| **`$STATE_DIR`** | variable | `claudechic/app.py::_workflow_template_variables` | Per-run scratch directory, expanded to absolute path at load time. |
| **`$WORKFLOW_ROOT`** | variable | `claudechic/app.py::_workflow_template_variables` | The main agent's cwd, expanded to absolute path. |
| **state directory / `state_dir`** | path | `claudechic/paths.py::compute_state_dir` | `~/.claudechic/workflow_library/{project_key}/{project_name}/`. Returned by `compute_state_dir(workflow_root, project_name)`. |
| **`WORKFLOW_LIBRARY_ROOT`** | constant | `claudechic/paths.py` line 11 | `Path.home() / ".claudechic" / "workflow_library"`. The fixed root for all `state_dir` instances. |
| **`project_key`** | encoded identifier | `claudechic/paths.py::compute_state_dir` docstring | Lossy encoding of `workflow_root.absolute()`: replace path-sep with `-`, strip `:`, `_`, `.`. "Same lossy encoding as `sessions.py`." |
| **`workflow_root` (engine ctor)** | path | `claudechic/workflows/engine.py::WorkflowEngine.__init__` | "Pin checks to a stable working directory (typically the main agent's cwd)... avoids false negatives when advance_phase is called by a sub-agent whose cwd ... has drifted." |
| **uniform expansion** | mechanism | `claudechic/workflows/engine.py::_run_single_check` | "Every consumer gets pre-expanded absolute paths through the same mechanism." Single `for var, replacement in expansions.items(): if var in v: v = v.replace(var, replacement)` loop. |

### B. Dynamic roles (sub-feature B)

| Term | Kind | Canonical home | Definition |
|---|---|---|---|
| **`DEFAULT_ROLE`** | sentinel | `claudechic/workflows/agent_folders.py` line 22 | `"default"`. "Sentinel role for agents with no workflow-specific role wiring. The main agent starts with this role and is promoted to the workflow's `main_role` on activation. Sub-agents spawned without an explicit `type=` also get this role. Reserved -- workflow role folders must not use it." |
| **`main_role`** | manifest field | `claudechic/workflows/loader.py::ManifestLoader._parse_workflow_manifest` | Top-level YAML key in a workflow manifest. The role assumed by the main agent on activation. Loader rejects manifests where `main_role == DEFAULT_ROLE`. |
| **`agent_type`** (Agent attr) | string | `claudechic/agent.py::Agent.__init__` | The Agent's mutable role marker. Defaults to `"default"` (the `DEFAULT_ROLE` sentinel) when not provided. Read by guardrail hooks at evaluation time. |
| **promote** | verb (informal) | `claudechic/app.py::_activate_workflow` log message: "Promoted main agent ... to role ... on workflow ... activation" | Set `agent.agent_type = manifest.main_role` for the main agent on workflow activation. No SDK reconnect. |
| **demote** | verb (informal) | `claudechic/app.py::_deactivate_workflow` log message: "Demoted main agent ... from ... to ... on workflow ... deactivation" | Restore `agent.agent_type = DEFAULT_ROLE` for the main agent on workflow deactivation. No SDK reconnect. |
| **dynamic role resolution** | mechanism | `claudechic/app.py::_guardrail_hooks` docstring | Guardrail hooks read `agent.agent_type` at rule-evaluation time (not at hook-creation time) -- so role mutations take effect on the next tool call without reconnecting. |
| **`get_disabled_rules`** | callback | `claudechic/app.py::_guardrail_hooks` | Lambda passed to `create_guardrail_hooks` returning the current `self._disabled_rules` set. Read on every tool call. |

### C. Effort cycling (sub-feature C)

| Term | Kind | Canonical home | Definition |
|---|---|---|---|
| **effort level** | string | `claudechic/widgets/layout/footer.py::EffortLabel.DEFAULT_LEVELS` | One of `"low"`, `"medium"`, `"high"`, `"max"`. The `"max"` level "triggers extended thinking which is only supported by Opus." |
| **`agent.effort`** | attribute | `claudechic/agent.py::Agent.__init__` | Per-agent effort level. Default `"high"`. Forwarded to SDK as `ClaudeAgentOptions(effort=...)`. |
| **`EffortLabel`** | widget class | `claudechic/widgets/layout/footer.py::EffortLabel` | Clickable footer label that cycles available levels on click; emits `EffortLabel.Cycled(effort: str)`. |
| **model-aware levels** | mechanism | `EffortLabel.MODEL_EFFORT_LEVELS` | Per-model-family available level tuple. `haiku` and `sonnet` have `(low, medium, high)`; `opus` adds `max`. `levels_for_model(model)` matches by substring. |
| **effort cycling** | feature label | `userprompt.md` (user term) | The user-facing phrase. The implementation noun is "effort level" and the verb is "cycle." |

### D. Guardrails UI (sub-feature D)

| Term | Kind | Canonical home | Definition |
|---|---|---|---|
| **`GuardrailEntry`** | frozen dataclass | `claudechic/guardrails/digest.py` lines 25-43 | "A single rule or injection with its evaluated status." Fields: `id`, `namespace` (`"global"` or `workflow_id`), `kind` (`"rule"` or `"injection"`), `trigger`, `enforcement` (`"deny" / "warn" / "log" / "inject"`), `message`, `active`, `skip_reason`, plus scope metadata. |
| **guardrail digest** | data product | `claudechic/guardrails/digest.py::compute_digest` | A `list[GuardrailEntry]` -- one per rule and one per injection -- "annotated with `active` (would evaluate) or `skip_reason` (why not)." |
| **`compute_digest`** | function | `claudechic/guardrails/digest.py::compute_digest` | Pure function: `(loader, active_wf, agent_role, current_phase, disabled_rules) -> list[GuardrailEntry]`. |
| **`GuardrailsModal`** | widget class | `claudechic/widgets/modals/guardrails.py::GuardrailsModal` | "Modal listing all guardrails with toggleable checkboxes." Constructed from a `list[GuardrailEntry]`. |
| **`GuardrailToggled`** | message class | `claudechic/widgets/modals/guardrails.py::GuardrailToggled` | Frozen `Message` dataclass: `(rule_id: str, enabled: bool)`. Posted when a checkbox in `GuardrailsModal` is toggled. |
| **`disabled_rules`** | in-memory set | `claudechic/app.py::ChatApp._disabled_rules` | `set[str]` of rule IDs the user has toggled off at runtime. Read by hook evaluator via `get_disabled_rules` callback. **Ephemeral** -- not persisted; cleared on restart. |
| **`_GuardrailRow`** | private widget | `claudechic/widgets/modals/guardrails.py::_GuardrailRow` | "A single row: checkbox + enforcement badge + id + skip reason." |
| **enforcement badge** | display string | `claudechic/widgets/modals/guardrails.py::_ENFORCEMENT_BADGE` | Markup-rendered badge: red `deny`, yellow `warn`, dim `log`, cyan `inject`. |
| **`InfoLabel`** | widget class | `claudechic/widgets/layout/footer.py::InfoLabel` | "Clickable 'info' label that opens the unified Info modal." Replaces `DiagnosticsLabel`. |
| **`GuardrailsLabel`** | widget class | `claudechic/widgets/layout/footer.py::GuardrailsLabel` | "Clickable 'guardrails' label that opens the guardrails modal." Replaces `ComputerInfoLabel`. |
| **unified Info modal** | concept | `accf332` commit message | The result of "DiagnosticsModal merged into unified Info modal." Class is still named `ComputerInfoModal` (NOT renamed). User-visible label is `info`. See §3 synonym. |

### E. Stowaway: `pytest_needs_timeout`

| Term | Kind | Canonical home | Definition |
|---|---|---|---|
| **`pytest_needs_timeout`** | warn rule | `claudechic/defaults/global/rules.yaml` (+7 lines in accf332) | A new `warn`-level guardrail rule firing when `pytest` is invoked without `--timeout`. Not in the four-feature title. |

### Walked-back surface (`a60e3fe`)

| Term | Kind | Canonical home | Definition |
|---|---|---|---|
| **stub** | state | `claudechic/app.py::on_guardrails_label_requested` (post-`a60e3fe`) | The handler is replaced by `self.notify("Guardrails viewer not yet implemented")`. The `GuardrailsModal`, `compute_digest`, and `GuardrailEntry` machinery remain in the tree but are **dead code on `abast/main`**. |

---

## 3. Synonyms found

Output format follows the role's review template.

### Synonyms within abast's own cluster

- **"unified Info modal" / `ComputerInfoModal` / "info button" / `InfoLabel`** -> The same UI surface has four names in the cluster. The widget class is `ComputerInfoModal` (unchanged). The footer label class is `InfoLabel` (renamed from `DiagnosticsLabel`). The footer label string is `"info"`. The commit message and CLAUDE.md call it the "Info modal" / "info button." `2f6ba2e` retitles the file comment to "system info + session diagnostics (info button)."
  -> **Recommend:** leave class name `ComputerInfoModal` until a separate rename pass; name it the **"Info modal"** in user-facing prose; keep `InfoLabel` for the footer. Document the class/label mismatch as a known synonym, schedule a rename for a later commit. **Do not let the class name drift to `InfoModal` here -- our base already has a `widgets/modals/base.py::InfoModal` that is a *base class* for labeled info sections; that name is taken.**

- **"agent role" / `agent_type` / `agent_role` / `role_name` / `main_role` / `DEFAULT_ROLE`** -> Five spellings for what is conceptually one axis: the role string carried by an Agent.
  - `agent_type` (`Agent.agent_type` attr) -- the *runtime* role marker.
  - `agent_role` (kwarg name in `_guardrail_hooks`, `assemble_phase_prompt`, `create_post_compact_hook`) -- a *call-site* parameter that ends up populating `agent_type`.
  - `role_name` (kwarg in `assemble_phase_prompt`, parameter in `_assemble_agent_prompt`) -- pre-existing in `agent_folders.py`; same axis.
  - `main_role` (manifest field, on-disk YAML key) -- the role to *promote into*.
  - `DEFAULT_ROLE` -- the sentinel value `"default"` for the same string field.
  -> **Recommend:** keep `agent_type` as the canonical *attribute* name (already established on our base); keep `main_role` for the *manifest field* (different axis, justified). Rename one of the kwargs (`agent_role` vs `role_name`) to match `agent_type` so call sites are self-consistent. **Composability decision needed.**

- **"role" / "role wiring" / "role folder"** -> `agent_folders.py` docstring uses "role wiring" once and "role folder" elsewhere (`_find_workflow_dir`, `_assemble_agent_prompt` traversal). The cluster keeps both.
  -> **Recommend:** define "agent role" once in a glossary section of `claudechic/context/workflows-system.md`; use "role folder" only when discussing on-disk layout.

### Synonyms between abast's cluster and our base

- **"workflow root" (abast) vs "workflow directory" (ours).** abast adds `workflow_root` (= main agent cwd, the project under work). Our base has `_resolved_workflows_dir` and `workflows_dir` (= where workflow MANIFESTS live). **These are different concepts with confusingly close names** -- see §4 "Critical newcomer blocker."
  -> **Recommend:** if we adopt, rename abast's `workflow_root` to `project_root` (it IS the project root, semantically). Reserve any "workflow_*" prefix for the manifest-discovery axis.

- **"effort" (abast) vs "thinking budget" / "model effort" (Anthropic SDK).** abast's `effort` likely passes through to the SDK's thinking-budget knob. Source confirms `ClaudeAgentOptions(effort=effort_level)` in `_make_options`. So `effort` IS the SDK's parameter name -- aligned, not a synonym.
  -> **No action.**

- **"disabled_rules" (abast, in-memory set on `ChatApp`) vs "disabled_ids" (ours, project config list).** Both name "rules a user has turned off." See §4 overloaded-terms.
  -> **Recommend:** disambiguate in §4.

---

## 4. Overloaded terms

### "guardrails" -- now 8-way overloaded

Pre-existing on our base (4 meanings):
1. **enforcement system** -- `claudechic/guardrails/` package.
2. **rule-set** -- `defaults/global/rules.yaml` content.
3. **bool master switch** -- `guardrails: true` in `<repo>/.claudechic/config.yaml`.
4. **disable list** -- `disabled_ids: [...]` flat list in project config; covers BOTH guardrail rule IDs and hint IDs.

Added by `accf332` (4 more):
5. **guardrail digest** -- `list[GuardrailEntry]` returned by `compute_digest`. (Data product.)
6. **GuardrailsModal** -- the runtime UI listing rules + injections.
7. **`disabled_rules`** -- in-memory ephemeral set on `ChatApp`. (NOT the same as `disabled_ids`.)
8. **`GuardrailsLabel`** -- the footer label that opens the modal.

Plus a stowaway:
- The `accf332` commit body says "GuardrailsModal shows all rules/injections" -- **so the modal covers BOTH rules AND injections, not only "guardrails" in the narrow sense.** "Guardrails" is being used here as a loose umbrella for the manifest-driven enforcement+injection layer. This is a fifth shade of meaning even within `accf332` itself.

-> **Recommend:** before adoption, choose:
   - Either keep "guardrails" as the umbrella, and rename `disabled_rules` -> `runtime_disabled_rules` to disambiguate from `disabled_ids`.
   - Or rename `GuardrailsModal` -> `RulesAndInjectionsModal` (longer, but precise).
   - Either way, add a **glossary anchor** in `claudechic/context/guardrails-system.md` listing all 8 meanings + which name maps to which.

### "default" -- already overloaded; abast adds two more

Pre-existing meanings:
- A permission-mode value (`PermissionMode = "default"` in `Shift+Tab` cycle).
- An adjective ("default workflows" = bundled tier).

Added by `accf332`:
- The `DEFAULT_ROLE` sentinel string `"default"`.
- The `DEFAULT_LEVELS` constant in `EffortLabel` (the default *effort levels* tuple, not "default" in the role sense).

So a user who reads `agent.agent_type == "default"` may reasonably ask: "default what -- permission mode? role? effort?" The answer is "role," but only because of the variable name on the left.

-> **Recommend:** keep `DEFAULT_ROLE = "default"` (idiomatic) but **always reference it via the constant `DEFAULT_ROLE`, never as the string literal `"default"`** in code, tests, and docs. Currently the cluster does this consistently (`agent.py` says `agent_type if agent_type is not None else "default"`, which is the only literal-string usage; everywhere else it imports `DEFAULT_ROLE`). Tighten that one site.

### "state" -- two scopes, two homes

- `WorkflowEngine._state_dir` (per-run path, `~/.claudechic/workflow_library/.../`).
- `chicsessions/` (per-app session state, on our base).
- The verb "state" in `from_session_state` (engine restoration entry point).

Three scopes, three storage locations, and one engine method spans two of them (`from_session_state` reads `chicsessions` state but constructs an engine bound to `state_dir`).

-> **Recommend:** reserve "state directory" / `state_dir` for the **per-run scratch** scope only. Use "session state" for `chicsessions` storage. Update docstrings of `from_session_state` to call the kwarg `state` (the input session blob) and the new ctor `state_dir` (the output scratch dir) -- already correct in source; just flag for documentation.

### "rule" -- "rule" vs "guardrail rule" vs "warn rule"

Pre-existing usage on our base distinguishes:
- `Rule` (frozen dataclass, see `claudechic/guardrails/rules.py`).
- "guardrail rule" / "global rule" / "workflow rule" (the documentation-side scoping vocabulary in `context/guardrails-system.md`).

`accf332` adds:
- `pytest_needs_timeout` referred to in the commit message as "warn rule for pytest without --timeout" -- short for "guardrail rule with enforcement: warn."

-> **No new collision** if "warn rule" is read as shorthand for "guardrail rule, enforcement=warn." Recommend keeping the long form in docs; the short form is fine in commit messages.

### "info" -- now triple-meaning

- **`InfoModal`** (existing class on our base, `widgets/modals/base.py`) -- a generic *base class* for labeled info sections; subclassed by `ComputerInfoModal`, `ProcessDetailModal`, etc.
- **"Info modal"** (abast, in commit message and `2f6ba2e` doc update) -- the merged user-facing modal (which is actually `ComputerInfoModal` extended).
- **`InfoLabel`** (abast, footer) -- the clickable label that opens the above.

A reader who sees "Info modal" in the commit message may go looking for an `InfoModal` class and find a *generic base class* with completely different intent.

-> **Recommend:** in user-facing prose, say "the **Info Panel**" or "**system info modal**" (not "Info modal"). In code, leave `InfoModal` as the base class. Schedule a follow-up commit to rename the merged modal -- but NOT in this cluster's adoption.

---

## 5. Orphan definitions

- **"workflow_library"** -- the on-disk directory name `~/.claudechic/workflow_library/` is introduced in `paths.py` as `WORKFLOW_LIBRARY_ROOT` but **the noun "workflow library" is never defined.** A reader who sees `~/.claudechic/workflow_library/{project_key}/{project_name}/` could reasonably guess "library of workflows" (i.e. a set of manifests), which is wrong -- it's a library of workflow *runs* (each per-project per-workflow `state_dir`).
  -> **Recommend (Composability):** define "workflow library" in a docstring on `paths.py` line 1: "Per-project workflow run state. Each `{project_key}/{workflow_id}/` subdirectory is one workflow's scratch dir for one project."

- **"two-pass execution" / "auto checks then manual checks"** -- introduced in a comment in `engine.py::_execute_advance_checks`, but the comment is the only place the order is named. Tests in `8f99f03` reference "auto" and "manual" without further definition.
  -> **Recommend:** add a one-line docstring on `_execute_advance_checks` calling out the two-pass design. Term "auto check" should probably be "automated check" everywhere; "manual check" -> "manual-confirm check" (matching the `type` value).

- **"skip_reason"** (`GuardrailEntry.skip_reason: str`) -- format is undocumented. Source uses freeform strings ("disabled by user", "workflow 'foo' not active", "role 'bar' not in [...]"). No invariant.
  -> **Recommend:** if the modal renders these to users, document the strings (or use an enum). If not human-facing, fine to leave freeform but add a comment.

- **"effort"** vs "thinking" -- the SDK term may be "thinking budget" elsewhere; abast picks "effort." Not orphan-defined per se, but readers familiar with the SDK may not connect them.
  -> **Recommend:** in `EffortLabel` class docstring add: "Maps to `ClaudeAgentOptions(effort=...)`, which controls the SDK's thinking budget." The cluster does NOT do this -- comment only mentions "extended thinking." Tighten on adoption.

---

## 6. Canonical home violations

- **`DEFAULT_ROLE` defined in `agent_folders.py`, used in `agent.py`, `loader.py`, `app.py`, tests.** Multiple files import it correctly via `from claudechic.workflows.agent_folders import DEFAULT_ROLE`. **One** site in `agent.py::Agent.__init__` uses the string literal `"default"` directly. Almost-correct -- just one offender.
  -> **Replace with:** `from claudechic.workflows.agent_folders import DEFAULT_ROLE` and `agent_type=agent_type if agent_type is not None else DEFAULT_ROLE`. Cost: one import line.

- **Effort-level enumeration repeated.** The set `("low", "medium", "high", "max")` appears as `EffortLabel.DEFAULT_LEVELS`, in the model-family table, in `EffortLabel.EFFORT_DISPLAY` keys, in `Agent.__init__`'s comment, and in the StatusFooter `effort = reactive("high")` default. Five duplications, no single canonical source.
  -> **Recommend:** define `EFFORT_LEVELS = ("low", "medium", "high", "max")` once in `widgets/layout/footer.py` (or better, in a new `claudechic/effort.py` since `Agent` also uses it but lives in a non-UI module). Reference everywhere else.

- **`compute_digest`'s parameters mirror but do not import the role/phase scoping rules from `guardrails/rules.py`.** `digest.py` calls `should_skip_for_phase` and `should_skip_for_role` -- correct delegation. **No violation.**

- **"workflow_root" docstring repeats engine-internal rationale on every method that takes it.** The same paragraph ("Pin checks to a stable working directory ...") is in `__init__`, `from_session_state`, `_run_single_check` comment. Duplication risk.
  -> **Recommend:** put the canonical explanation on `__init__` only; reference from the others.

- **`commit message disagreement`:** the commit message says state "moves to `~/.claudechic/workflow_library/`" -- present tense, total. But `_activate_workflow` STILL emits a warning if the legacy `<repo>/.project_team/` directory is found ("Workflow state now lives at ..."). So state has moved by *convention* but the legacy path is not deleted, and `claudechic` does not migrate it. Newcomer reading the commit message would over-trust the move.
  -> **Recommend:** docstring clarify: "Workflow state lives at `state_dir`. Pre-`accf332` workflows used `<repo>/.project_team/`; `_activate_workflow` warns when that legacy directory is present but does NOT migrate it."

---

## 7. Newcomer blockers

A new contributor reading `accf332` cold (no claudechic background) will hit these in order:

1. **`paths.py::compute_state_dir` line 21-26** -- the `project_key` encoding. The docstring says "same lossy encoding as `sessions.py`" but a newcomer doesn't know what `sessions.py`'s encoding is or why it's lossy. Also: "lossy" implies collisions are possible -- a security/correctness question raised but not answered.
   -> **Clarify:** "The encoding is lossy and may collide for paths differing only in `:`, `_`, or `.`. Collisions cause two workflows to share state -- documented limitation; project layout that triggers it requires user intervention." (Or explain why this is fine.)

2. **`engine.py::_run_single_check` lines 339-352** -- the `for k, v in params.items()` mutation loop. A newcomer reads this expecting expansion to be opt-in or scoped, but it runs over **every str-typed param** of the check. There's no type marker for "expand-this-string" vs "leave-alone." If a user happens to put a literal `$STATE_DIR` in a regex pattern, it gets clobbered.
   -> **Clarify:** docstring should warn: "Expansion is unscoped -- any `$STATE_DIR` or `$WORKFLOW_ROOT` substring in any string param will be replaced. Avoid these tokens in literal patterns."

3. **`app.py::_activate_workflow` `state_dir.mkdir(parents=True, exist_ok=True)` -- silent.** The newcomer sees "we just created a directory under `~/.claudechic/`" and may not realize this is the first time the user's HOME has been written to by claudechic for this project. If the home is read-only, this raises.
   -> **Clarify:** wrap with try/except + user-facing error toast, or document explicitly.

4. **Phrase "main agent is promoted to main_role on workflow activation" (commit message)** -- pre-existing readers know "main agent" means "the first agent created at startup." Newcomers may read it as a *role* ("I'd better find out which agent is main") and search the codebase. Source is unambiguous: `self._agent` in `ChatApp` -- but the field `_agent` is not commented as "the main agent."
   -> **Clarify:** add a comment on `ChatApp._agent` field declaration: "The 'main agent' -- the first agent created at startup. Promoted to `manifest.main_role` on workflow activation."

5. **`_GuardrailRow` constructor takes `entry: GuardrailEntry` but `kind` differentiates rule vs injection** -- the badge logic, sort order ("rules first, then injections"), and `enforcement` value all depend on `kind`. A newcomer extending the modal to a third kind (say "advice") would need to touch four places. Not a current blocker but a structural smell.
   -> **No immediate action; flag for Composability** if the modal grows.

6. **`a60e3fe` stub -- intent is hidden.** The single-file commit deletes 36 lines and adds 2, replacing real handlers with `notify("Guardrails viewer not yet implemented")`. There is **no comment in the code or commit message explaining why** abast halted the rollout. A newcomer asks: "Is this temporary? Is the modal broken? Should I revert this commit and ship the modal?" -- and has no source-side answer.
   -> **Recommend:** if we adopt the cluster, **either** include `a60e3fe` AND add a code comment with our interpretation ("abast halted the UI rollout for [reason X]; we leave the stub until [condition Y]"), **or** skip `a60e3fe` and ship the full modal (with our own decision on record). Do not ship without resolving the intent.

---

## 8. Critical collisions (for Composability decision)

Listed by severity (highest first). These are the **architectural-level** collisions where naming is downstream of an open question.

### CRITICAL-1: `workflow_root` vs `workflows_dir` vs `_resolved_workflows_dir`

Three near-identical names, three different concepts:

| Name | Lives in | Means | Set when |
|---|---|---|---|
| `workflow_root` (NEW) | `WorkflowEngine`, `app.py::_activate_workflow` | The **project under work** -- the main agent's cwd | Per workflow activation |
| `_resolved_workflows_dir` (existing) | `ChatApp` | The **manifest discovery** dir (where `defaults/workflows/` or `~/.claudechic/workflows/` lives) | Once at startup |
| `workflows_dir` (existing kwarg) | `ManifestLoader.__init__`, `assemble_phase_prompt`, etc. | Same as `_resolved_workflows_dir` -- the manifest dir | Per construction |

A newcomer reading `_run_single_check` sees `params.setdefault("cwd", str(self._workflow_root))` and may think it's pinning to "where the workflows are loaded from." It is **not** -- it's pinning to the **project root**.

-> **Recommend (Composability):** if we adopt, rename `workflow_root` -> `project_root` everywhere it appears (engine ctor, `state_dir` computation, `_workflow_template_variables`, the `$WORKFLOW_ROOT` template variable). Rename the template variable to `$PROJECT_ROOT`. Cost: ~12 sites in source, 1 site in YAML manifests, 1 in role markdown. Benefit: removes the worst newcomer hazard in the cluster.
   *Counter-argument:* abast shipped this name; renaming on adoption fragments the lineage and complicates future cherry-picks.
   *Resolution:* defer to Composability. **Strongly recommend the rename**; if not, document the three names side-by-side in `context/workflows-system.md`.

### CRITICAL-2: state-location proliferation

After `accf332`, claudechic state lives in **six** distinct on-disk locations. A newcomer cannot pick the right one without a map.

| Location | Purpose | Owner | Tier |
|---|---|---|---|
| `~/.claude/rules/` | Claude Code rules (claudechic-awareness install destination) | Claude Code | global |
| `~/.claudechic/config.yaml` | User-tier config | claudechic (Group B) | user |
| `~/.claudechic/chicsessions/` | Per-app session metadata | claudechic (Group B) | user |
| `~/.claudechic/hints_state.json` | Hint lifecycle state | claudechic (Group B) | user |
| `~/.claudechic/workflow_library/{project_key}/{wf_id}/` (NEW) | Per-project workflow scratch (`state_dir`) | accf332 | user |
| `<repo>/.claudechic/config.yaml` | Project-tier config | claudechic | project |
| `<repo>/.claudechic/hits.jsonl` (moved by accf332 from `.claude/`) | Guardrail hit audit | accf332 | project |
| `${CLAUDECHIC_ARTIFACT_DIR}` (Group E) | Per-run artifact dir, manifest substitution | claudechic (Group E) | per-run |
| `<repo>/.project_team/` (LEGACY, warned-not-removed) | Pre-accf332 workflow scratch | pre-accf332 | project |

**`$STATE_DIR` (= `~/.claudechic/workflow_library/{project_key}/{wf_id}/`) and `${CLAUDECHIC_ARTIFACT_DIR}` (= per-run artifact dir) overlap in purpose.** Both are "where workflow scratch goes." Adopting `accf332` AS-IS gives us TWO mechanisms.

-> **Recommend (Composability):** before adopting sub-feature A:
   1. Decide whether `$STATE_DIR` REPLACES `${CLAUDECHIC_ARTIFACT_DIR}` or COEXISTS.
   2. If replaces: remove `${CLAUDECHIC_ARTIFACT_DIR}` machinery (Group E) and migrate manifests.
   3. If coexists: clearly document the difference (per-run vs per-project? lifetime? cleanup?) and choose ONE for `defaults/workflows/project_team/project_team.yaml`.
   4. Either way, settle the `<repo>/.project_team/` legacy: migrate, ignore, or auto-delete on activation.

### CRITICAL-3: substitution syntax forks

Three substitution mechanisms now coexist:

| Mechanism | Syntax | Scope | Resolver |
|---|---|---|---|
| Worktree path templates (existing) | `${repo_name}` `${branch_name}` | `~/.claudechic/config.yaml::worktree.path_template` | `claudechic/features/worktree/git.py` |
| Artifact dir substitution (Group E) | `${CLAUDECHIC_ARTIFACT_DIR}` | Workflow YAML manifest | engine, env-style |
| Workflow template variables (NEW, accf332) | `$STATE_DIR` `$WORKFLOW_ROOT` | Workflow YAML + role markdown | engine, `str.replace` |

`${VAR}` (braces) for some, `$VAR` (no braces) for accf332. **`str.replace` is unscoped**, so a manifest that mixes both styles risks one variable accidentally substring-matching another.

-> **Recommend:** standardize on `${VAR}` (the braced form) for all template-variable mechanisms. abast's choice of bare `$VAR` was likely a stylistic preference; the cost of converging is low (sed in the manifests + an `re.sub` in the resolver). If we adopt the cluster as-is, **at minimum require non-overlapping variable names** to defuse the substring risk.

### CRITICAL-4: `disabled_rules` (in-memory) vs `disabled_ids` (config file)

Both are "rules a user has turned off." `disabled_rules` (new) is ephemeral; `disabled_ids` (existing) is persisted in project config. They do not interact -- toggling in `GuardrailsModal` is invisible to `disabled_ids` and vice versa.

A user who toggles a rule off via `GuardrailsModal`, restarts the app, and finds it back on is confused. A user who adds an entry to `disabled_ids` in YAML and finds the modal checkbox checked (because the modal reads `compute_digest`'s `disabled_rules` arg, which on our base is a different store) is also confused.

-> **Recommend (Composability):** decide adoption shape:
   - Option 1: `GuardrailsModal` toggles **persist** to `disabled_ids` (UI for an existing config knob). Removes the in-memory `disabled_rules` entirely.
   - Option 2: `GuardrailsModal` toggles are explicitly **session-only** (rename `disabled_rules` -> `runtime_disabled_rules`; show "session only" hint in the modal). `disabled_ids` and `runtime_disabled_rules` are unioned at hook-evaluation time.
   - Option 3: skip the modal entirely (adopt only the digest data product). Defer UI to a later effort.
   The current `accf332` shape is Option 2 without the disambiguation, AND `a60e3fe` then stubs out the button -- so the user-visible behaviour is "no UI, dead code in the tree." If we adopt unchanged we ship that same half-state.

---

## 9. Hand-off to other axis-agents

Cross-references for the three axis agents named in `leadership_findings.md` §8:

### To `engine-seam` (workflow template variables + dynamic roles)
- **Use these names verbatim:** `$STATE_DIR`, `$WORKFLOW_ROOT`, `state_dir`, `workflow_root`, `WORKFLOW_LIBRARY_ROOT`, `project_key`, `DEFAULT_ROLE`, `main_role`, `agent_type`. **Do NOT** introduce `agent_role` as a new attribute name.
- **Critical collision to resolve:** §8 CRITICAL-1 (`workflow_root` vs `workflows_dir`). If you recommend adoption, please give Composability a position on whether to rename `workflow_root` -> `project_root` BEFORE the cherry-pick lands.
- **Open question to answer:** does `$STATE_DIR` replace `${CLAUDECHIC_ARTIFACT_DIR}` or coexist? See §8 CRITICAL-2.

### To `guardrails-seam` (guardrails UI + flagged 003408a)
- **Use these names verbatim:** `GuardrailEntry`, `compute_digest`, `guardrail digest`, `GuardrailsModal`, `GuardrailToggled`, `disabled_rules`, `_GuardrailRow`, `enforcement badge`.
- **Critical collision to resolve:** §8 CRITICAL-4 (`disabled_rules` vs `disabled_ids`). If you recommend adoption, please give Composability a position.
- **Newcomer blocker to resolve:** §7 item 6 (`a60e3fe` intent unexplained). Your recommendation MUST address: include the stub or include the full modal? (Skipping `a60e3fe` ships dead code.)

### To `UI-surface` (effort cycling)
- **Use these names verbatim:** `effort level`, `agent.effort`, `EffortLabel`, `EffortLabel.Cycled`, `EFFORT_LEVELS` (proposed).
- **Canonical home violation to fix on adoption:** §6 item 2 (effort-level tuple duplicated 5 times). Recommend extracting to a single constant.
- **Watch for:** §3 noted that `effort` aligns with the SDK parameter name. If our SDK pin doesn't yet support `effort=`, that's a precondition you need to identify.

### To `historian` (already complete)
- The historian's terminology is consistent with this glossary. One small note: historian uses "feature D ships in a half-built state" -- I'd prefer "ships partially walked-back" for `a60e3fe`, since the modal class is fully built; only the *button wiring* is stubbed. Cosmetic.

### To `skeptic`
- Q4 ("articulate user-visible 'before vs after'") for sub-feature D is hard to answer in the `accf332` + `a60e3fe` combined state, because the user-visible delta is "no change -- the button now says 'not yet implemented.'" Worth flagging in your standing posture: this cluster has a feature whose adopted user-visible delta is **negative-zero** (we'd add a button that announces it doesn't work).

### To `user_alignment`
- The four feature labels match abast's commit-title wording verbatim (FLAG 1 satisfied).
- The "intent (cluster-level)" question (§1 user term) needs an answer in the final report. Working hypothesis from the diff: **the cluster reorganizes WORKFLOW STATE STORAGE around per-project paths, makes ROLE-BASED guardrails work for the main agent without reconnect, and exposes the guardrails surface for runtime inspection -- then halts the inspection UI rollout.** That's three coherent improvements + one halted UI. Composability/UserAlignment to refine.

---

## 10. Recommendations summary (for Coordinator)

In priority order. Each is for **Composability decision**; this document does not unilaterally rename.

1. **CRITICAL-1: rename `workflow_root` -> `project_root`** (engine ctor, `$WORKFLOW_ROOT` -> `$PROJECT_ROOT`) before adoption. Highest newcomer-clarity win. Cost: ~14 sites.
2. **CRITICAL-2: choose one of `$STATE_DIR` vs `${CLAUDECHIC_ARTIFACT_DIR}`.** Coexistence without disambiguation is a footgun.
3. **CRITICAL-3: standardize substitution syntax** on `${VAR}` for all three mechanisms. Cost: low.
4. **CRITICAL-4: pick a `disabled_rules` semantic** (persist to `disabled_ids` / session-only / skip-modal). Required even if we just adopt `accf332` as-is.
5. **`a60e3fe` decision is binary.** Either include with a comment explaining intent, or skip and ship the modal. Do NOT ship without a recorded decision.
6. **Glossary anchor:** add a "guardrails terminology" section to `claudechic/context/guardrails-system.md` listing the 8 meanings. Add "workflow library" definition to `claudechic/paths.py`.
7. **Tighten one site:** replace string literal `"default"` in `agent.py::Agent.__init__` with `DEFAULT_ROLE` import.
8. **Use abast's labels in the final report verbatim** (UserAlignment FLAG 1).
9. **Three documentation orphans** to fix on adoption: `compute_state_dir` lossiness, two-pass check execution, `skip_reason` format.

Outstanding for Specification phase: axis-agents spawn and report back. This document refines as their findings come in -- particularly anything that reveals new symbols I haven't seen.

---

*End of terminology specification. Reply with disagreements or
new symbol surface to TerminologyGuardian via `message_agent`.*
