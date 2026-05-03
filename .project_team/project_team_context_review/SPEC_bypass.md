# SPEC_bypass.md -- project_team_context_review

Operational specification produced by the BYPASS run's Specification phase.
**This document is self-contained.** Every term it uses is defined within it.
Other files (axis specs, prompt_audit, appendix) are supplemental history;
do not consult them to understand or implement this spec.

---

## 1. Goal

Tighten the `project_team` workflow by reviewing the time, place, and role of context
delivery to its agents so the team has what it needs to drive the project forward at
every step.

---

## 2. Compositional law

Every prompt-assembly decision routes through one pure predicate:

```
inject(t, p, r) = render(p, ctx(t, r))  if gate(t, p, r, phase, settings, manifest)
                  EMPTY                  otherwise   -- EMPTY = empty string ""
```

Function signature (lives in `claudechic/workflows/agent_folders.py`):

```python
def gate(
    time: InjectionSite,     # "spawn" | "activation" | "phase-advance" | "post-compact"
    place: PromptSegment,    # "identity" | "phase" | "constraints_stable"
                             # | "constraints_phase" | "environment"
    role: str,               # agent_type folder name; "default" is a legal value
    phase: str | None,       # qualified phase id, e.g. "project-team:specification"
    settings: GateSettings,  # frozen dataclass; from CONFIG + ProjectConfig
    manifest: GateManifest,  # frozen dataclass; from LoadResult
) -> bool: ...
```

Single-layer composition:

```
gate = user_gate
```

`user_gate` reads user/project-tier settings (`constraints_segment.*` and
`environment_segment.*`; §3.11) and the manifest's file-presence data for
standing-by suppression (§3.8). It is the sole gate layer; there are no
non-negotiable floor cells. The user's settings choice is honored exactly
at every (time, place, role) cell. A misconfiguration that breaks an agent
(e.g. dropping the constraints segment from the broadcast site) is the
user's choice; the engine does not override it.

No new module. No class hierarchy. Single pure function ~30 LOC.

---

## 3. Locked decisions

### 3.1 Injection sites (time axis)

An **injection site** is a code location in `claudechic/workflows/agent_folders.py`
(or its callers) that calls `assemble_agent_prompt(...)` to deliver context to an agent.
Four sites exist, closed enumeration.

| ID | Name | Trigger | Recipient |
|----|------|---------|-----------|
| T1 | spawn | `mcp.spawn_agent` creates a sub-agent | the new sub-agent |
| T2 | activation | main agent's workflow becomes active | main agent |
| T3 | phase-advance | phase advance fan-out (`mcp.py` advance_phase tool's async post-call broadcast loop) | all typed sub-agents |
| T4 | post-compact | SDK `SessionStart` hook with `matcher="compact"` | the compacted agent |

The coordinator's own phase-advance context update is delivered via the synchronous return value of the `advance_phase` MCP tool (an inline `assemble_phase_prompt` call in the tool response), not via this injection-site framework. The framework therefore governs sub-agent fan-out, spawn, activation, and post-compact only.

T4 (post-compact) is the canonical full-refresh site. T4 fires all four segments regardless of config.

Default segment set per site (5 places per place_axis §6.1: `constraints` is split into two first-class PLACES, `constraints_stable` and `constraints_phase`, so the per-site segment set decides slice membership without leaking time into the renderers):

| Site | identity | phase | constraints_stable | constraints_phase | environment |
|------|----------|-------|--------------------|-------------------|-------------|
| T1 spawn | yes | yes | yes | yes | yes* |
| T2 activation | yes | yes | yes | yes | yes* |
| T3 phase-advance (typed active) | no | yes | no | yes | no |
| T3 phase-advance (standing-by) | no | no | no | yes | no |
| T4 post-compact | yes | yes | yes | yes | yes* |

\* environment fires at T1/T2/T4 subject to manifest opt-in and user_gate settings (§3.11).

### 3.2 Prompt segments (place axis)

A **prompt segment** is a named section of an agent's launch prompt, assembled at
injection time. Five segments exist, closed enumeration. `constraints_stable` and
`constraints_phase` are first-class peer PLACES (place_axis §6.1); the umbrella
term "constraints segment" refers to their composition.

| Segment | Renderer | Source | Freshness |
|---------|----------|--------|-----------|
| identity | `_render_identity(ctx)` | `<workflow_dir>/<role>/identity.md` | per-call read |
| phase | `_render_phase(ctx)` | `<workflow_dir>/<role>/<bare_phase>.md` | per-call read |
| constraints_stable | `_render_constraints_stable(ctx)` -- thin wrapper that calls `assemble_constraints_block(slice="stable", omit_heading=False)` | `compute_digest` + `_LoaderAdapter` | per-call live |
| constraints_phase | `_render_constraints_phase(ctx)` -- thin wrapper that calls `assemble_constraints_block(slice="phase", omit_heading=<composer-driven>)` | `compute_digest` + `_LoaderAdapter` | per-call live |
| environment | `_render_environment(ctx)` | `defaults/environment/` bundle + runtime engine state | per-call live |

Every renderer returns `str` (never `None`). Returns `""` when source content is absent.
The composer joins non-empty segments with `"\n\n---\n\n"` (identity+phase) and
`"\n\n"` (before constraints, before environment).
Empty segments are dropped. When all gate predicates return True (no suppression active),
the composed output must preserve every rule id and produce exactly one `## Constraints`
heading: this verifies the refactor loses no information.

`RenderContext` is a frozen dataclass carrying all renderer inputs.
`assemble_agent_prompt` external signature is unchanged. All four inject-site callers
add one new keyword-only argument: `time: InjectionSite`.

### 3.2.1 Constraints decomposition (two PLACES, two pure renderers)

`constraints_stable` and `constraints_phase` are two first-class PLACES, each with its own pure renderer. **Time is invisible to the renderers** (place_axis §6.4 Place/Time seam invariant): a renderer that branches on `ctx.time` would be the same Place-into-Time leak the identity/phase split eliminated. Instead, the per-site segment set (§3.1 default segment table) decides slice membership; the gate decides per-cell suppression; the composer joins what the gate returned.

- `_render_constraints_stable(ctx) -> str` -- global rules (those without a `phase:` qualifier) plus role-scoped rules (those filtered by `(role, workflow)` but not by phase). Stable across phase advances; rarely changes within a workflow run. Emits the `## Constraints` heading.
- `_render_constraints_phase(ctx) -> str` -- phase-scoped rules (those with `phase: <current>` qualifier matching `ctx.phase`). Plus, when `ctx.role == "coordinator"`, the advance-checks declared on the current phase. The phase-scoped rules subsection emits to every role; the advance-checks subsection emits coordinator-only. Heading emission depends on whether `constraints_stable` precedes it in the same composition (omit_heading; see §3.2.2).

**Advance-checks scope.** Advance-checks gate `mcp__chic__advance_phase`, which only the coordinator calls. Sub-agents (typed and default-roled) never invoke it; the advance-checks are noise to them. `_render_constraints_phase` enforces this with one role check at the advance-checks splice point: when `ctx.role != "coordinator"`, the advance-checks subsection is omitted; the phase-scoped rules subsection emits as usual. (Option (a) per the architectural sketch -- single role check inside `_render_constraints_phase`, no second renderer.)

Both renderers route through `assemble_constraints_block(slice=..., omit_heading=...)` -> `compute_digest` -> `_LoaderAdapter` -> `_filter_load_result` (single-source invariant; F4 keystone test binding). The `slice` kwarg selects "stable" or "phase"; Every rule id present in `slice=None` output survives in the union of `slice="stable"` + `slice="phase", omit_heading=True`; exactly one `## Constraints` heading appears in the composed output (slice-split keystone). Each renderer returns `""` when its slice is empty.

**Composer rule (driven by §3.1 default segment set, NOT by renderer-side time branching):**

| Site | constraints_stable | constraints_phase | Composed output |
|------|--------------------|-------------------|-----------------|
| T1 spawn | yes | yes | full block: stable owns heading; phase appended headless |
| T2 activation | yes | yes | full block |
| T3 phase-advance | no | yes | phase delta only (owns heading) |
| T4 post-compact | yes | yes | full block (canonical refresh) |

Default-roled agents at T3 (where the broadcast loop reaches them; today they are skipped, see §3.9): `_render_constraints_phase(ctx)` returns the phase-scoped slice that applies to `role="default"` (typically empty unless a global rule applies during the new phase). The composer returns a non-`None` prompt when at least one segment is non-empty (renderers return `str`, never `None`).

### 3.2.2 omit_heading concatenation rule (no duplicate `## Constraints`)

When the composer emits both `constraints_stable` and `constraints_phase` at the same site (T1 / T2 / T4), the two slices render as ONE `## Constraints` block. The composer signals this to `_render_constraints_phase` via `omit_heading=True` (driven by composer state, not by `ctx.time`): stable owns the heading; phase appends headless content with the standard subsection separator. When `constraints_phase` emits alone (T3), it owns its own `## Constraints` heading (`omit_heading=False`).

The two renderers stay pure; the composer is the only site that knows which slices coexist. No code path produces a duplicate `## Constraints` heading.

### 3.3 Content revisions for project_team roles (role axis)

**Communication boilerplate hoist.** The `## Communication` block is removed from
14 identity files (145 lines total). The block splits into two parts:

- Tool-semantics half (~7 lines per role: what `message_agent`, `interrupt_agent`,
  `requires_answer` do) -> environment segment `base.md`. Workflow-agnostic.
- Behavioral-guidance half (~4 lines per role: when to communicate, which requires_answer
  value to use) -> per-phase markdown. Phase-dependent.

Both halves are recovered at injection time via the environment segment (T1/T2/T4) and
per-phase markdown (T3). Net prompt payload is unchanged; placement is correct.

**Authority preservation.** 22 cataloged identity authority quotes are preserved verbatim.
Byte-compare verification during Implementation is required.

**Line-count summary:**

| Role | Lines deleted | Net |
|------|--------------|-----|
| coordinator | 0 (header added) | 61 |
| composability | 11 | ~511 |
| skeptic | 11 | 105 |
| user_alignment | 11 | 145 |
| terminology | 11 | 89 |
| implementer | 11 | ~99 |
| test_engineer | 11 | ~91 |
| ui_designer | 11 | ~132 |
| researcher | 11 | ~229 |
| lab_notebook | 12 | ~340 |
| memory_layout | 12 | ~117 |
| sync_coordinator | 11 | ~108 |
| binary_portability | 11 | ~76 |
| project_integrator | 11 | ~181 |

### 3.4 New phase markdown files (role axis)

Five new files authored during Implementation (each changes a standing-by cell to active in the standing-by matrix; see SPEC_APPENDIX_bypass.md):

| File | Content directive |
|------|------------------|
| `test_engineer/testing-specification.md` | Generalprobe standard + role-specific review checklist |
| `test_engineer/testing-implementation.md` | Generalprobe standard + active-engagement directive |
| `ui_designer/specification.md` | UX lens on specification; verify D1 with UserAlignment |
| `ui_designer/implementation.md` | UX lens on implementation; surface UX-pattern violations |
| `user_alignment/implementation.md` | Scan each landed feature against userprompt.md; flag divergence immediately |

### 3.5 Role enumeration and partition key

`role` is the sole partition key for content selection. 16 values for project_team:

`coordinator`, `composability`, `terminology`, `skeptic`, `user_alignment`,
`implementer`, `test_engineer`, `ui_designer`, `researcher`, `lab_notebook`,
`memory_layout`, `sync_coordinator`, `binary_portability`, `project_integrator`,
`default`. (15 typed + `default`.)

### 3.6 Standing-by suppression mechanism

The standing-by predicate (§3.8) suppresses identity and phase automatically. No YAML
schema ships; no per-phase suppress block is parsed. The predicate evaluates the
file-system state `<workflow_dir>/<role>/<bare_phase>.md` at gate-call time.

### 3.7 Constraints-segment configurability

Settings key `constraints_segment:` accepted at user-tier (`~/.claudechic/config.yaml`)
and project-tier (`<project>/.claudechic/config.yaml`; project tier wins):

```yaml
constraints_segment:
  compact: true                 # bool; true = compact-list output (default), false = markdown-table
  include_skipped: false        # bool
  scope:
    sites: [spawn, activation, phase-advance, post-compact]  # non-empty subset
```

| Key | Default | Consumer |
|-----|---------|----------|
| `constraints_segment.compact` | `true` | renderer (`assemble_constraints_block`); `true` -> compact-list (default), `false` -> markdown-table |
| `constraints_segment.include_skipped` | `false` | renderer |
| `constraints_segment.scope.sites` | all 4 | `user_gate` |

No `enabled: false` master toggle is provided -- removing the segment everywhere is achievable by emptying `scope.sites` to a near-empty list, but `scope.sites = []` is rejected at config-load time as a likely typo (raises `ConfigValidationError`; pick one or more sites or omit the key entirely to use the default). `scope.sites` applies uniformly to all 4 sites and to both `constraints_stable` and `constraints_phase` in v1 (per-slice scope is v2):
- Removing `phase-advance` from `scope.sites` suppresses the constraints segment at T3 broadcast. Recipients receive no constraints update on phase advance until their next spawn, activation, or post-compact fire.
- Removing `post-compact` from `scope.sites` suppresses the constraints segment at T4. After `/compact` the agent's working set is rebuilt without an updated constraints segment until the next site fires.
- Removing every site is rejected (see above); shrink to one site to keep the segment alive somewhere.

The advance-checks subsection within `constraints_phase` is coordinator-only by renderer-side scoping (§3.2.1). Sub-agents never see advance-checks regardless of `scope.sites`.

**MCP inspector parameter.** `mcp__chic__get_agent_info` accepts an optional `compact: bool` input parameter (default `false`). When `compact=false` (default), constraints are rendered as a formatted markdown table regardless of the user-tier `constraints_segment.compact` setting. When `compact=true`, the compact-list form is rendered. The user-tier setting is NOT consulted; the parameter is the sole control.

### 3.8 Standing-by definition

A spawned agent is standing-by for a phase when:
`agent_type != DEFAULT_ROLE` AND `<workflow_dir>/<agent_type>/<bare_phase>.md` does not exist.

Predicate is pure: evaluated per call from `(role, phase, manifest)` where `manifest`
carries file-presence data from LoadResult. No runtime memo, no busy/idle check.

The engine auto-suppresses identity and phase for standing-by roles at T3 by construction.

Standing-by agents at T3 receive: identity suppressed (the standing-by predicate inside
`user_gate` returns False for identity at T3), phase empty (renderer-empty:
`_render_phase` returns `""` because no `<role>/<phase>.md` exists for this phase),
`constraints_phase` fires when `phase-advance` is in `scope.sites` (default),
environment segment is not relevant at T3 (environment never emits at T3 per §3.1
segment set; it fires at T1 / T2 / T4 only).

### 3.9 Default-roled agents

Default-roled agents (`agent_type == DEFAULT_ROLE`) receive: identity renderer-empty,
phase renderer-empty, constraints segment when global rules apply, environment when
opted in. `assemble_agent_prompt` returns a non-None prompt whenever at least one
segment is non-empty (closes F8; see §4). No placeholder is emitted for empty segments
(closes F9; see §4).

### 3.10 No structural floor

There are no structural floor cells. `gate = user_gate` for every (time, place, role) combination -- the user's settings choice is honored exactly at every cell. A user who narrows `constraints_segment.scope.sites` to omit `phase-advance` will have agents that miss the constraints update on phase advance; a user who omits `post-compact` will have agents whose constraints segment goes stale across `/compact`. These outcomes are the user's choice, not engine-prevented mistakes.

The single guard remaining at config-load time is `scope.sites = []` -> `ConfigValidationError`, on the grounds that the empty list is more likely a typo than an intent. Users who want to remove the segment everywhere can shrink `scope.sites` to a single site (e.g. `[spawn]`) -- the segment still emits there, leaving the agent informed at one moment in its lifecycle. (The MCP tools `get_applicable_rules` and `get_agent_info` remain available for on-demand introspection regardless of `scope.sites`.)

### 3.11 Environment segment: content and configuration

#### Content

Bundle dir: `claudechic/defaults/environment/`. Two files:

- `base.md` -- workflow-agnostic, runtime-dynamic template. Substituted tokens:
  `${AGENT_ROLE}`, `${ACTIVE_WORKFLOW}`, `${WORKFLOW_ROOT}`, `${CLAUDECHIC_ARTIFACT_DIR}`,
  `${NAME_ROUTING_TABLE}`, `${PEER_ROSTER}`, `${MCP_TOOL_LIST}`, `${COORDINATION_PATTERNS}`.

  The `${NAME_ROUTING_TABLE}` token resolves to `{agent_type -> registered_name}` from
  `agent_manager.agents` at injection time, ensuring agents can address each other by
  registered name regardless of role name.

- `project_team.md` -- workflow-static overlay. Loaded when
  `ctx.active_workflow == "project_team"`. Contains 2-sentence-per-peer summaries
  under `### Project team peers (descriptions)`. Static markdown (no tokens); sourced
  from each role's `identity.md` Prime Directive during Implementation.

#### Activation

The environment segment is enabled by default for all workflows. User-tier
`environment_segment.enabled: false` is the sole opt-out. No per-workflow manifest
field; the manifest layer has been removed (same pattern as no-structural-floor, §3.10).

**Renderer guard.** `_render_environment` returns `""` when `ctx.active_workflow` is
unset or `ctx.workflow_dir` is absent. This is renderer-side "no useful content"
behavior (consistent with the spec pattern: renderers return `""` when source content is
absent) -- an environment block built from all-empty token substitutions is noise. The
guard is NOT a gate bypass; the gate controls whether the renderer is called; the
renderer controls whether its output is non-empty.

#### User-tier configuration schema

Accepted at user-tier (`~/.claudechic/config.yaml`) and project-tier
(`<project>/.claudechic/config.yaml`; project tier wins):

```yaml
environment_segment:
  enabled: true                           # bool; default true; false to disable
  scope:
    sites: [spawn, activation, post-compact]  # subset of the 3 fire sites
  compact: false                          # bool; false = all 4 content pieces, true = name routing + peer roster only
```

| Key | Default | Consumer |
|-----|---------|----------|
| `environment_segment.enabled` | `true` (default; all workflows) | `user_gate` |
| `environment_segment.scope.sites` | `[spawn, activation, post-compact]` | `user_gate` |
| `environment_segment.compact` | `false` | `_render_environment`; `false` -> all 4 content pieces, `true` -> name routing + peer roster only |

Compact mode (`compact: true`): name routing table and peer roster only; omits MCP tool
list and coordination patterns. For token-budget-conscious runs.
Default (`compact: false`): all four content pieces -- name routing table, peer roster,
MCP tool list, coordination patterns.

`scope.sites` is bounded to the three sites where the environment segment can fire
(spawn, activation, post-compact); phase-advance is excluded from the segment
per the default segment table (§3.1). All three of those sites are user-controllable
without restriction. An empty `scope.sites` raises `ConfigValidationError` at config-load
time on the grounds that the empty list is more likely a typo than an intent (consistent
with the constraints-segment guard in §3.7).

### 3.12 User-facing settings UI

A new `"Agent prompt context"` section is added to `SettingsScreen` in
`claudechic/screens/settings.py`, placed between the existing `User settings` content
and its `Reset user settings` row. Two new subscreens follow the `disabled_ids.py`
checkbox-list pattern.

**Top-level `SettingKey` entries (all `bool`, one-click, no modal):**

| Key | Label | Editor | Helper |
|-----|-------|--------|--------|
| `constraints_segment.compact` | "Compact rules block" | bool | "Compact list by default; disable for the formatted markdown table." |
| `constraints_segment.advanced` | "Rules block: advanced..." | subscreen | opens `AdvancedConstraintsScreen` |
| `environment_segment.enabled` | "Team coordination context" | bool | "Inject the peer roster, name routing table, and MCP coordination notes." |
| `environment_segment.compact` | "Compact coordination context" | bool | "Omit the MCP tool list and coordination patterns." |
| `environment_segment.advanced` | "Coordination context: advanced..." | subscreen | opens `AdvancedEnvironmentScreen` |

No enable toggle for the rules block at the top level (the section header communicates presence). Every per-site checkbox in the Advanced subscreen is fully user-controllable; users who want to silence the constraints segment everywhere narrow `scope.sites` accordingly.

**`AdvancedConstraintsScreen`** (checkbox `ListItem`s, `Enter`-to-confirm or live-save). All four rows are enabled and toggleable; no row renders disabled or pinned.

| Checkbox | User-facing label | Engineering token |
|----------|-------------------|-------------------|
| [x] | when an agent starts | `spawn` |
| [x] | when the workflow activates | `activation` |
| [x] | on phase advance | `phase-advance` |
| [x] | after compaction | `post-compact` |

User-facing phrase in primary column; engineering token in muted secondary column. The
empty-list guard (§3.10) prevents the user from clearing every checkbox: the screen
keeps at least one site checked at save time, with a one-line notice if the user clears
the last remaining row ("at least one site must remain checked").

**`AdvancedEnvironmentScreen`** (same pattern, 3 sites; all enabled and toggleable):

| Checkbox | User-facing label | Engineering token |
|----------|-------------------|-------------------|
| [x] | when an agent starts | `spawn` |
| [x] | when the workflow activates | `activation` |
| [x] | after compaction | `post-compact` |

**Acceptance criteria:**

- No new top-level row introduces injection-site vocabulary.
- A user can enable or disable team coordination context with one click.
- A user who opens either Advanced subscreen sees plain-language site descriptions in
  the primary column and engineering token names in the muted secondary column. Every
  checkbox is toggleable; no row is pinned.
- The screen keeps at least one site checked at save time; clearing the last row
  shows a one-line notice and reverts the toggle.
- A user who has never read SPEC_bypass.md can correctly predict what each top-level
  toggle does from its label and helper text alone.

---

## 4. Failure-mode regression map

| F# | Description | Behavior | Owning axis |
|----|-------------|----------|------------|
| F1 | Phase-advance broadcast missed `assemble_agent_prompt`; sub-agents lost constraints block | Engine plumbing fix is the sole closure: broadcast routes through `assemble_agent_prompt` (preserved from prior run). Default `constraints_segment.scope.sites` includes `phase-advance`, so the `constraints_phase` slice emits at T3 to every recipient by default. A user who narrows `scope.sites` to omit `phase-advance` accepts that broadcasts will not carry an updated constraints segment. The `constraints_stable` slice anchors at T1 / T2 / T4 by §3.1 segment set and is absent from T3 -- recipients already received it and it lives in transcript. | time, gating |
| F3 | Three coexisting freshness contracts (spawn-freeze / per-call / post-compact) | Documented (§3.2). T4 (post-compact) = canonical refresh. Substrate left unchanged. | time |
| F4 | Source-of-truth divergence: hooks vs registry/MCP read different projections | Single-source invariant: constraints renderer routes exclusively through `assemble_constraints_block` -> `_LoaderAdapter` -> `_filter_load_result`. Keystone test binding. | place, gating |
| F5 | `mcp.py` disabled_rules unwired at 4 sites | T1: spawn passes merged `disabled_rules`. T3: broadcast computes once outside loop. | time, gating |
| F6 | `get_phase` overstated active rules (namespace-only filter) | Predicate purity prevents recurrence: `gate(...)` reads `manifest` and `settings` only; no live rule query. | gating |
| F7 | Falsy `agent_type` routed broadcast to default-roled agents | Predicate signature accepts `role: str`; `"default"` is a legal value. T1: spawn refuses falsy `agent_type`. | time, gating |
| F8 | `assemble_agent_prompt` returned `None` for default-roled agents; constraints lost | Renderers return `str`, never `None`. Composer returns non-None when any segment is non-empty. Default-roled agents receive constraints at T1 when global rules apply. | place, role |
| F9 | Empty-digest emitted 138-char placeholder; standing-by agents received noise | Empty-digest `assemble_constraints_block` returns `""`. Composer drops empty segments. No placeholder. | place, role |

---

## 5. Build plan (implementer hand-off)

Steps within a group are parallelizable; groups run top-to-bottom.

**Group 1 -- Core renderer split (no behavior change)**

1. Add `RenderContext` frozen dataclass in `agent_folders.py`. (~15 LOC)
2. Extract `_render_identity`, `_render_phase` from `_assemble_agent_prompt`; preserve
   `_substitute` calls. (~30 LOC added, ~30 removed)
3. Extend `assemble_constraints_block` with `slice: Literal["stable","phase",None]` and `omit_heading: bool` kwargs (~25 LOC; preserves single-source/F4 -- one resolver call shape, two output shapes). Add two thin renderer wrappers `_render_constraints_stable(ctx)` (calls `slice="stable", omit_heading=False`) and `_render_constraints_phase(ctx)` (calls `slice="phase"`; `omit_heading` driven by composer state per §3.2.2; coordinator-only advance-checks per §3.2.1). Both honor `ctx.settings.constraints_segment`. (~10 LOC each)
4. Add `_render_environment` returning `""` stub; wire activation from `ctx.settings.environment_segment.enabled` and manifest field. (~15 LOC)
5. Rewrite `assemble_agent_prompt` body as thin orchestrator over the four renderers +
   `gate(...)`. (~30 LOC net ~0 delta)
6. Thread `time: InjectionSite` keyword through 4 callers:
   `mcp.py:308` (T1 spawn), `app.py:2131` (T2 activation),
   `mcp.py:1026` (T3 phase-advance broadcast), `agent_folders.py:362` (T4 post-compact). (1 line each)
   The coordinator's phase-advance update at `app.py:2405` is the synchronous return value of the `advance_phase` MCP tool -- not an injection site -- and does not pass through `assemble_agent_prompt`.

**Group 2 -- Gating predicate**

7. Implement pure `gate(time, place, role, phase, settings, manifest) -> bool` as a single-layer `user_gate` in `agent_folders.py` (no `structural_gate`; §3.10). The predicate reads `settings.constraints_segment.scope.sites`, `settings.environment_segment.scope.sites`, and the standing-by manifest data; returns the user's choice unmodified. Default-cell constants per §3.1. (~30 LOC)

**Group 3 -- Configuration wiring**

9. Add `GateSettings` + `GateManifest` frozen dataclasses; wire from CONFIG /
   ProjectConfig / loader. Parse `constraints_segment.*` and `environment_segment.*`
   keys into `GateSettings`. (~40 LOC)
**10. Spec self-containment rule (coordinator + composability inline placement).** Paste the rule text below verbatim at the end of all four files:
- `claudechic/defaults/workflows/project_team/coordinator/specification.md`
- `claudechic/defaults/workflows/project_team/coordinator/testing_specification.md`
- `claudechic/defaults/workflows/project_team/composability/specification.md`
- `claudechic/defaults/workflows/project_team/composability/testing-specification.md`

Rule text:

    ## Spec self-containment

    - Every term used in the spec is defined inside the spec.
    - References to other files drift out of sync as the spec iterates. A reference is permitted only when you commit to keeping the referenced file in sync. If you cannot commit, inline the content or drop the reference.
    - A stale reference is a violation.

    When editing the spec -- at any phase after synthesis -- add only operational facts. Do not narrate reasoning, justify decisions, or reference prior states inline. If the rationale matters, add it to the appendix instead.
11. Bundle `claudechic/defaults/environment/base.md` and `project_team.md` with
    content per §3.11. (2 files, ~40 lines each)

**Group 4 -- Bundled content revisions**

12. Bundled-content user checkpoint. Before any edits land in
    `claudechic/defaults/workflows/project_team/`, the implementer assembles a unified
    diff (proposed edits to identity files + new phase markdown files + paste of spec
    self-containment rule). Coordinator presents the diff to the user. Bundled-content
    steps below execute only after user approval.
13. Delete `## Communication` blocks from 14 `project_team/<role>/identity.md` files.
    Authority preservation: byte-compare 22 authority quotes before and after each edit.
14. Author 5 new phase markdown files (§3.4) with content directives as listed.
15. Add coordinator identity informational-mirror header before L34.
16. Paste plain-language chat rule at the end of
    `claudechic/defaults/workflows/project_team/coordinator/identity.md`:
    "Reply to the user in plain language; define any team-internal code before
    referencing it."

**Group 6 -- Review loop**

17. Per-role transient confirmation: implementer spawns each role with
    `prompt_audit/<role>.md` + proposed revision; role confirms authority statements
    verbatim; edit applied. For D2=b: establish `role_feedback/` directory convention
    and add per-phase YAML `advance_check` line to each coordinator phase markdown.

**Group 7 -- Settings UI**

18. Add `"Agent prompt context"` section header to `SettingsScreen` in
    `claudechic/screens/settings.py`. Add the 5 top-level `SettingKey` entries per
    the §3.12 table. (~40 LOC)
19. Implement `AdvancedConstraintsScreen` following the `disabled_ids.py` pattern:
    5 checkbox `ListItem` rows bound to `constraints_segment.scope.sites`; live-save;
    every row enabled and toggleable; clearing the last remaining row triggers a
    one-line notice and reverts the toggle (per §3.12 acceptance criteria). (~80 LOC)
20. Implement `AdvancedEnvironmentScreen` with the same pattern; 3-site checkbox list
    bound to `environment_segment.scope.sites`; every row enabled; same last-row
    revert behavior. (~60 LOC)
21. Fix MCP tool-widget content disappearing on click. Symptom: clicking a rendered
    `mcp__chic__*` tool-use widget in the chat view causes the displayed content to vanish.
    Likely in `claudechic/widgets/content/tools.py`. Diagnose root cause; restore content
    visibility on click; add a UI test that asserts a click on the widget leaves content
    rendered.

**Group 8 -- Tests**

22. Regression tests are the deliverable of the testing phase; test design does not appear in this document.

Estimated totals: ~150 LOC in `agent_folders.py`; ~50 LOC in `_substitute.py`;
~80 LOC in 2 new bundle files; ~40 LOC in config parsing;
~180 LOC in new settings screens; -145 LOC from identity files.

---

## 6. Test design

Test design is the deliverable of the testing phase; no test specifications appear in this document.

---

## 7. Constraints

- The pure predicate MUST NOT reach I/O or wall-clock. Same `(time, place, role, phase,
  settings, manifest)` always returns the same bool.
- `awareness_install.py` host-side rule mechanism is preserved. The environment segment
  is in-prompt context; it is not a replacement.
- No bundled workflow other than project_team changes behavior unless its author
  adds `environment_segment: enabled` to its YAML.
- Pre-existing F4/F5/F6/F7 fixes MUST NOT regress.
- All file paths in implementation prompts MUST be absolute.

---

## 8. Pass/fail bar for Implementation

Implementation phase ships only when:
- Each F-number in the regression map (§4) matches its declared fate.
- The 22 authority quotes are byte-identical between pre-change and post-change
  identity files (or an explicit user authorization accompanies any deviation).
- Other bundled workflows (tutorial, cluster_setup, audit, codebase_setup, git_setup,
  onboarding, tutorial_extending, tutorial_toy_project) pass their existing workflow
  tests.
- D2 decision is resolved (see appendix deliberation history); D1 is locked (see §3.11).

---

*Author: BYPASS run Specification phase.*
