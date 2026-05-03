# Gating Axis Specification -- project_team_context_review

**Author:** gating-axis agent
**Status:** v1, Specification phase
**Owns:** sec 2.4 + sec 5.4 of `specification/composability.md`; resolves R-comp-2, R-comp-3; co-resolves R1, R2 from skeptic_review.md.

**Framing.** Per Terminology Q-T2 (Composability ratified): gating is a
**control surface** that parameterises the inject predicate, not a
coordinate axis of the crystal. The crystal is `(time, place, role)`;
gating is the predicate machinery that decides which cells fire.
**Inputs:** `STATUS.md`, `leadership_findings.md`, `specification/composability.md`, `specification/terminology.md`, `specification/skeptic_review.md`, `specification/user_alignment.md`, `claudechic/workflows/agent_folders.py`, `claudechic/config.py`, `claudechic/defaults/workflows/project_team/project_team.yaml`, GitHub #27 + #28.

This document specifies the **gating axis**: the configuration surface and pure
predicate that decides whether a `(injection site, prompt segment, role)` cell
fires. Vocabulary is the canonical glossary (`specification/terminology.md`).

---

## 1. Predicate signature

The compositional law (composability sec 4) routes every cell through one
**inject predicate** -- a pure function with no I/O and no clock.

```python
# claudechic/workflows/agent_folders.py
def gate(
    time: InjectionSite,                  # Literal["spawn","activation","phase-advance-main","phase-advance-broadcast","post-compact"]
    place: PromptSegment,                 # Literal["identity","phase","constraints","environment"]
    role: str,                            # agent_type folder name; "default" allowed
    phase: str | None,                    # qualified phase id, e.g. "project-team:testing-vision"; None when no workflow
    settings: GateSettings,               # frozen dataclass, see sec 4
    manifest: GateManifest,               # frozen dataclass, see sec 3
) -> bool:
    """True -> render and emit segment; False -> emit EMPTY."""
```

**Location.** Function lives in `claudechic/workflows/agent_folders.py`, next
to `assemble_agent_prompt`. **No new module, no class hierarchy, no engine.**
Single pure function, ~30 LOC. (Skeptic Q3: pin shape now. Skeptic spec
review reaffirmation.)

**Callers.** `assemble_agent_prompt` is the single composition point. It calls
`gate(...)` once per `(time, place)` for the assembling role and skips
`render_<place>(...)` when the gate returns False. The five existing inject
sites pass `time` through unchanged.

**Purity contract.**
- No file reads (`manifest` is pre-loaded; `settings` is pre-loaded).
- No clock, no env reads, no agent-state queries.
- Same `(time, place, role, phase, settings, manifest)` -> same `bool`. Always.

**Per-site evaluation (Composability ratification of Skeptic Q4).**
The predicate is invoked at **every** injection site; the composer in
`assemble_agent_prompt` does not memoize across sites. Standing-by is
recomputed per call by `(role, phase, manifest)` lookup. "Static" in the
Q3 lock means "pure and reads from manifest, not from agent activity" --
**not** "frozen at spawn." A `/compact` restoration or a workflow-override
that adds/removes a `<role>/<phase>.md` mid-run gets the right answer at
the next site fire. Purity makes per-site evaluation free.

**Renderer-empty vs gate-suppress (the data/policy distinction).**
Two mechanisms produce a missing segment, and they are NOT equivalent:
- **Renderer-empty (data path)** -- `render_<place>(...)` returns `b""`
  because the source content does not exist (e.g. no `<role>/<phase>.md`,
  or `compute_digest` returned no rules). The gate stays True; the
  composer skips the empty segment in the join. Owns: place-axis.
- **Gate-suppress (policy path)** -- `gate(...)` returns False because a
  `gating:` YAML entry, a `constraints_segment.scope` setting, or the
  `structural_gate` floor said so. Render is never called. Owns: this
  axis.

**Convention:** prefer renderer-empty for "no content exists"; reserve
gate-suppress for "config says don't deliver" (#27, #28) and "structural
floor forbids/forces" (sec 6). Where both apply, gate-suppress wins by
short-circuit (the renderer is never invoked). F8/F9 closure: when a
default-roled agent has no role dir, identity/phase render-empty while
constraints render full (gate True for all). The agent receives
constraints alone; no placeholder, no silent skip.

**Sub-gate composition.** Composability sec 4 specifies
`gate = workflow_gate AND user_gate`. This spec **strengthens** that to a
three-way AND with a floor:

```python
gate(...) = structural_gate(time, place, role, phase, manifest) \
        AND workflow_gate(time, place, role, phase, manifest) \
        AND user_gate(time, place, role, phase, settings)
```

- `workflow_gate` reads phase YAML (#27).
- `user_gate` reads user/project settings (#28).
- `structural_gate` is the **non-negotiable floor**: invariants the predicate
  cannot opt out of (sec 6, regression guards). Implemented as
  `gate_result = False` early-returns for cells the floor protects
  (e.g. constraints @ phase-advance-broadcast = always True from below).

The composability sec 4 AND-rule is preserved among `workflow_gate` and
`user_gate`: either layer can suppress; neither can force injection over
the other's veto. The `structural_gate` floor is a one-way
**force-inject-or-bypass** for cells where suppression would re-introduce
F-numbers (sec 6) -- it does not allow either layer to suppress those
cells. **Confirmation, with strengthening:** confirmed.

---

## 1a. Default-cell behavior table

Per Composability sec 8.1 lock (refined). Aligned with time-axis sec 2.0.
Role-class is the runtime classification computed by `(role, phase, manifest)`
lookup at gate-call time (per-site, per the purity contract above):
- **typed active** -- `agent_type != "default"` AND `<role>/<phase>.md` exists.
- **typed standing-by** -- `agent_type != "default"` AND `<role>/<phase>.md`
  does not exist.
- **default-roled** -- `agent_type == "default"`.
- **main** -- the workflow's `main_role` (a `typed active` specialization).

| time | place | role-class | default | Mechanism | Rationale |
|------|-------|------------|---------|-----------|-----------|
| spawn | identity | typed | True | gate | role assignment |
| spawn | phase | typed | True | gate; renderer-empty when no `<phase>.md` | phase context |
| spawn | constraints | any (incl. default) | True | gate | F8 closure |
| spawn | identity | default-roled | True (gate); renderer-empty | renderer | not a gate decision -- no role dir |
| spawn | environment | * | True | gate | run-bound facts |
| activation | identity / phase / constraints / environment | main | True | gate | full launch |
| phase-advance-main | identity | main | True (config can suppress per #27) | gate | per-phase suppress |
| phase-advance-main | phase | main | True | gate | the reason this site fires |
| phase-advance-main | constraints | main | True | gate (Q4 lock; #28 may narrow `scope.sites` to other sites but floor keeps >=1) | always |
| phase-advance-main | environment | main | True | gate | -- |
| phase-advance-broadcast | identity | typed standing-by | **False** | gate-suppress (project_team.yaml) | #27 + R1 |
| phase-advance-broadcast | identity | typed active | True (config can suppress per #27) | gate | per-phase suppress |
| phase-advance-broadcast | phase | typed standing-by | False (gate); also renderer-empty | renderer-empty preferred | no `<phase>.md` to inject |
| phase-advance-broadcast | phase | typed active | True | gate | always |
| phase-advance-broadcast | constraints | any | True | **structural floor: never False** | F1 closure -- broadcast must carry constraints |
| phase-advance-broadcast | environment | any | True | gate | -- |
| post-compact | identity / phase / constraints / environment | any | True | **structural floor: never suppressible** | R3 lock -- full refresh |

**Notes.**
- "Typed standing-by" rows for `identity` are the canonical #27 use case.
  The project_team.yaml entries in sec 5 declare these via `gating: suppress`
  per phase. The gate returns False; the renderer is never called.
- "Typed standing-by" rows for `phase` are doubly-empty: gate would return
  False under the same `gating: suppress` entry, but place-axis's
  `render_phase` already returns `b""` for missing `<phase>.md`. Renderer-
  empty wins by ownership convention; gate-suppress is redundant but
  harmless. (No regression risk -- both produce identical observed bytes.)
- "Default-roled" for `identity`/`phase` is renderer-empty, not gate-False:
  the agent has no role dir, but might match global-namespace rules; the
  gate must NOT short-circuit because constraints would be lost (F8).
- All `constraints @ phase-advance-broadcast` cells are floor-True
  regardless of role class -- this is the F1 regression guard.
- All `post-compact` cells are floor-True regardless of class -- this is
  the R3 / time-axis I13 / I14 lock.

### 1b. Compact predicate matrix (5 times x 4 places x N role-classes)

The predicate's full input-output table for v1, in a single grid. Rows are
`(time, place)`; columns are role-class. **N = 4** -- per Q-T2 (GLOSSARY)
and the standing-by definition (terminology 1.3), every role of the
project_team's 16-role enumeration falls into exactly one class at
gate-call time, so the 5 x 4 x 16 = 320-cell crystal compresses
losslessly to this 5 x 4 x 4 = 80-cell matrix.

Cell values:
- `T` = gate True (segment fires).
- `F-cfg` = gate False; user/workflow YAML drives this False (#27 / #28
  scope.sites).
- `r-empty` = gate True; place-axis renderer returns empty bytes (no
  source content). Composer drops the empty segment.
- `floor-T` = `structural_gate` pins True; no configuration reaches this
  cell.

|  time \ (place, role-class) | identity / typed-active | identity / typed-standing-by | identity / default | identity / main | phase / typed-active | phase / typed-standing-by | phase / default | phase / main | constraints / typed-active | constraints / typed-standing-by | constraints / default | constraints / main | environment / typed-active | environment / typed-standing-by | environment / default | environment / main |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| spawn (T1)                  | T   | T   | r-empty | n/a* | T   | r-empty | r-empty | n/a* | T (floor-T) | T (floor-T) | T | n/a* | T | T | T | n/a* |
| activation (T2)             | n/a | n/a | n/a     | T    | n/a | n/a     | n/a     | T    | n/a | n/a | n/a | T (floor-T) | n/a | n/a | n/a | T |
| phase-advance-main (T3)     | n/a | n/a | n/a     | T or F-cfg (#27) | n/a | n/a | n/a | T   | n/a | n/a | n/a | T (floor-T at >=1 site; F-cfg via scope) | n/a | n/a | n/a | T |
| phase-advance-broadcast (T4)| T or F-cfg (#27) | F-cfg (project_team.yaml standing-by entry) | n/a** | n/a* | T   | r-empty | n/a** | n/a* | floor-T | floor-T | floor-T | n/a* | T | T | n/a** | n/a* |
| post-compact (T5)           | T (floor-T) | T (floor-T) | r-empty (floor-T gate; no source) | T (floor-T) | T (floor-T) | r-empty (floor-T gate; no source) | r-empty (floor-T gate; no source) | T (floor-T) | T (floor-T) | T (floor-T) | T (floor-T) | T (floor-T) | T (floor-T) | T (floor-T) | T (floor-T) | T (floor-T) |

\* `main` is unique by construction: it is spawned once at activation and
is the workflow's main agent throughout. `n/a*` cells correspond to "main
never receives this site." Specifically: T1 and T4 are sub-agent sites;
the main agent never appears as a recipient.

\*\* Default-roled agents are excluded from broadcast at the recipient
loop today (`mcp.py` skips `agent_type == DEFAULT_ROLE`); time-axis I10
preserves this skip. The `n/a**` entries record that the cell never
fires because the recipient loop never reaches default-roled agents at
T4. This is `gate` returning True with no caller -- not a gate-suppress.

**Reading guide.**
- Every `floor-T` cell is unreachable from any combination of YAML #27
  entries and settings #28 keys. These are the F1/F8/F9/R3 regression
  guards (sec 6).
- Every `F-cfg` cell is the configurable surface: #27 entries reach
  identity at phase-advance times; #28's `scope.sites` reaches
  constraints at sites OTHER than `phase-advance-broadcast` and
  `post-compact` (those are floor-pinned).
- Every `r-empty` cell is owned by place-axis: the gate stays True;
  the renderer returns empty bytes when source content is absent.
- The matrix matches §1a row-for-row; this view is a compact
  cross-tabulation, not a redefinition.

## 2. Configuration surface (two homes)

| Concern | Home | Schema | Scope |
|---------|------|--------|-------|
| Per-phase suppression (#27) | workflow YAML (`<workflow>.yaml` phase entry) | `gating:` block on a `Phase` (sec 3) | workflow-author authority; targets specific roles in specific phases |
| Master toggle / format / scope (#28) | user-tier `~/.claudechic/config.yaml` and project-tier `<project>/.claudechic/config.yaml` | `constraints_segment:` block (sec 4) | user/project authority; cross-workflow |

**Composability rule (R-comp-3 / Skeptic R2 / UserAlignment #5.8 /
Skeptic spec-review reaffirmation):** the master toggle is
**format-and-scope tweaks only, never an opt-out.** No `enabled: false`,
no "constraints off, MCP-only" mode. `structural_gate` enforces this
floor: at least one inject site MUST emit the constraints segment, and
the segment renderer MUST route through the same projection used today
(F4 keystone test).

---

## 3. Issue #27 mechanism (per-phase suppression)

### 3.1 YAML syntax

Add an optional `gating:` block to each phase entry. Both forms accepted by
`PhasesParser`; the block is ignored by older claudechic versions
(forward-compatibility).

```yaml
phases:
  - id: testing-vision
    file: testing_vision
    gating:
      suppress:
        - segment: identity            # required: one of identity|phase|constraints|environment
          roles: [implementer]         # required: list of role folder names; "*" = all roles
          times: [phase-advance-main, phase-advance-broadcast]  # optional; default = all phase-advance times (see 3.3)
```

**Multiple `suppress` entries** allowed; each is an independent rule. A cell
is suppressed if **any** entry matches (`(segment, role, time)` triple).

### 3.2 Resolution path (precedence)

When multiple YAML keys could apply to the same cell, evaluation order is:

1. **Direct phase entry** (this block) -- workflow-author authority.
2. **Workflow-level default** (`gating:` at top level of the workflow YAML;
   reserved for future use, not specified in v1).
3. **Engine default** -- inject (gate -> True).

A phase entry **adds** suppressions; nothing in the YAML can force a
`structural_gate` floor to False (sec 6).

### 3.3 Defaults for `times` field

When `times` is omitted, suppression applies to **`phase-advance-main` and
`phase-advance-broadcast` only** -- the re-injection moments named in #27.
`spawn` and `activation` are **never** suppressed by `gating:` (they define
the agent's role); `post-compact` is **never** suppressed (R3: post-compact
must restore the launch-time prompt or it regresses F-numbers silently).

This default closes hole #5 from composability sec 6 (broadcast routing).
Workflow authors who want different times must list them explicitly.

### 3.4 Standing-by suppression (the canonical #27 use case)

Suppression for standing-by agents (terminology 1.3: "role has no
`<role>/<phase>.md`") is **declared statically** in the YAML using sec 3.1
syntax. The engine does NOT auto-detect standing-by at runtime (R-comp-2 /
Skeptic R1 / Q3): a per-phase `phase.md`-presence check is implicit but the
**suppression decision itself remains a YAML declaration**, so workflow
authors retain authority and the predicate stays pure.

### 3.5 Defaults shipped for project_team

The static standing-by matrix from `defaults/workflows/project_team/`
(sec 5) is materialized as `gating:` entries in
`defaults/workflows/project_team/project_team.yaml`. Sec 5 lists them.

---

## 4. Issue #28 mechanism (constraints-segment configurability)

Issue #28 asks to make the always-on constraints injection configurable.
Three configurability shapes were considered. Each is named, sketched,
and weighed against the F4/F5/F7 floor (which the constraints segment
keystone-tests).

### 4.1 The three options

#### Option (a) -- format-tweak only

Visual presentation knobs over `assemble_constraints_block`. Every cell
that fires today still fires; only the rendered bytes change.

```yaml
constraints_segment:
  format: markdown-table        # markdown-table | markdown-list | compact-list
  include_skipped: false        # bool; surface the skip-reason audit column
```

- **Consumer:** the renderer (`assemble_constraints_block`).
- **Touches gate?** No. `user_gate` is the identity for #28 under this
  option; the gate stays True wherever the floor or workflow YAML say it is.
- **F4/F5/F7 surface:** zero. Every site emits the segment; the projection
  used is unchanged.
- **What it gives the user:** brevity and ordering. Resolves the "the block
  is verbose" complaint in #28's body.
- **What it does not give:** any per-site control. The user can shorten
  the block; cannot move it.

#### Option (b) -- scope-only (per-site narrowing)

A non-empty subset of injection sites carries the segment. Other sites
emit empty bytes for the constraints place. Format stays as today.

```yaml
constraints_segment:
  scope:
    sites: [spawn, activation, post-compact]   # subset; non-empty
```

- **Consumer:** `user_gate` (returns False when `time not in scope.sites`).
- **Touches gate?** Yes -- this is gate territory. Format is identity.
- **F4/F5/F7 surface:** narrow but real. Removing
  `phase-advance-broadcast` from the scope re-creates F1's symptom
  shape (broadcast recipients without an updated constraints block) --
  EXCEPT that `structural_gate` (sec 6) pins
  `(phase-advance-broadcast, constraints) = True` from below. The user
  CAN narrow scope but CANNOT empty it AND CANNOT remove the broadcast
  cell. The floor catches the obvious foot-guns.
- **What it gives the user:** "I trust my agents to call
  `get_applicable_rules` on demand at phase-advance-main; let the spawn
  prompt carry constraints and skip the rest." A legitimate posture for
  power users.
- **What it does not give:** content-level configurability or full
  opt-out.

#### Option (c) -- full opt-out master switch

A single boolean turns the segment off everywhere. The MCP tools
(`get_applicable_rules`, `get_agent_info`) remain available; the
proactive in-prompt injection vanishes.

```yaml
constraints_segment:
  enabled: false       # bool master switch
```

- **Consumer:** `user_gate` (returns False for every constraints cell).
- **Touches gate?** Yes -- catastrophically. The structural floor's
  "at least one site emits constraints" invariant becomes user-overridable.
- **F4/F5/F7 surface:** the segment is the keystone fix for all three.
  When the segment is silent at every site:
  - **F4 reappears** -- agents discover guardrails by hitting them.
    `_LoaderAdapter` still exists, but the keystone test no longer
    asserts the segment matches it (the segment is empty everywhere);
    nothing surfaces hook/registry divergence to the agent.
  - **F5 reappears for the launch path** -- `disabled_rules` may still
    plumb correctly into hooks, but the agent never sees the projected
    rule set; a user-side mistake in `disabled_ids` is invisible until
    an agent tries the disallowed action.
  - **F7 reappears as a soft regression** -- broadcast routing is fine,
    but default-roled agents that legitimately match a global rule
    (e.g. `global:no_bare_pytest`) get no warning at spawn. Skeptic
    spec-review reaffirmation: "opt-out reintroduces F4/F5/F7 silently."
- **What it gives the user:** one knob to remove the segment everywhere.
- **What it does not give:** a path to keep the F4/F5/F7 fixes while
  honoring the request.

### 4.2 Recommendation for v1: (a) + (b), reject (c)

**Recommend (a) + (b), as a unified `constraints_segment:` block.**
Defer no other options.

- (a) is independent of the gate; it cannot reach the F4/F5/F7 floor.
- (b) is gate-territory but is bounded by `structural_gate`: the floor
  pins `(phase-advance-broadcast, constraints) = True`, which is the
  single cell whose suppression most directly re-creates F1. The
  floor also enforces `len(scope.sites) >= 1` so no configuration
  silences the segment everywhere.
- (c) is the option Skeptic R2 names as a foot-gun. It silently
  re-introduces F4/F5/F7. **Defer indefinitely.** The user who wants
  fewer launch-prompt bytes is served by (a)'s `format: compact-list`
  + (b)'s `scope: [spawn]`; the user who wants no in-prompt constraints
  at all has the MCP tools.

The combined v1 schema:

```yaml
# ~/.claudechic/config.yaml or <project>/.claudechic/config.yaml
constraints_segment:
  format: markdown-table              # markdown-table | markdown-list | compact-list
  include_skipped: false              # bool, default false
  scope:
    sites: [spawn, activation, phase-advance-main,
            phase-advance-broadcast, post-compact]
    # non-empty subset; defaults to all five.
    # structural_gate guarantees:
    #   - phase-advance-broadcast is always emitted regardless of this list (F1)
    #   - post-compact is always emitted regardless of this list (R3)
    # so removing those entries narrows nothing -- documented as a no-op.
```

**Defaults** (no config present): `format: markdown-table`,
`include_skipped: false`, `scope.sites = [all 5]`. A user with no
config file sees today's behavior byte-for-byte.

### 4.3 Configurable knobs (the SHORT list)

Per Skeptic ("name the config key, the values, the consumer, the default"):

| Key | Type / Values | Default | Consumer | Purpose |
|-----|---------------|---------|----------|---------|
| `constraints_segment.format` | enum: `markdown-table` \| `markdown-list` \| `compact-list` | `markdown-table` | renderer (`assemble_constraints_block`) | Option (a) -- visual presentation |
| `constraints_segment.include_skipped` | bool | `false` | renderer | Option (a) -- surface skip-reason audit |
| `constraints_segment.scope.sites` | list of injection-site names; non-empty | all 5 | `user_gate` | Option (b) -- per-site narrowing, bounded by floor |

**Excluded by design:**
- `enabled: false` (full opt-out, option (c)) -- R-comp-3, R2.
- Per-rule toggles -- already covered by `disabled_ids` (#28 "out of scope").
- Per-message dynamic gating -- launch-prompt scope only (#28 "out of scope").
- Per-role include/exclude lists -- not requested; would re-introduce
  source-of-truth divergence pressure with `disabled_ids`.

### 4.4 Loading

`GateSettings` is loaded once at startup from `CONFIG['constraints_segment']`
(user-tier) merged with `ProjectConfig` (project-tier; project-tier wins).
The frozen dataclass is passed to `assemble_agent_prompt` via the existing
`engine` plumbing (already accepts `disabled_rules`, etc.). No global
mutable state.

---

## 5. Standing-by static matrix for project_team

Coordinated with role-axis from the role/phase folder inventory
(role_axis owns the source-of-truth audit). For each phase, the role has a
`<phase>.md` file or it does not. The matrix below shows
**where #27 fires** -- `S` = suppress identity (and phase, since phase
segment is empty anyway) at `phase-advance-{main,broadcast}` for that role.

Column headers: `vis` = vision, `set` = setup, `lead` = leadership,
`spec` = specification, `impl` = implementation, `tv` = testing-vision,
`ts` = testing-specification, `ti` = testing-implementation,
`doc` = documentation, `sgn` = signoff.

| role | vis | set | lead | spec | impl | tv | ts | ti | doc | sgn |
|------|-----|-----|------|------|------|----|----|----|-----|-----|
| coordinator | . | . | . | . | . | . | . | . | . | . |
| composability | S | S | S | . | . | S | S | . | S | S |
| terminology | S | S | S | . | S | S | . | S | S | S |
| skeptic | S | S | S | . | . | S | . | . | S | S |
| user_alignment | S | S | S | . | by* | S | . | . | S | S |
| researcher | S | S | S | S | S | S | S | S | S | S |
| implementer | S | S | S | S | . | S | S | . | S | S |
| test_engineer | S | S | S | S | S | S | . | . | S | S |
| ui_designer | S | S | S | . | . | S | S | S | S | S |
| project_integrator | S | S | S | S | S | S | S | S | S | S |
| sync_coordinator | S | S | S | S | S | S | S | S | S | S |
| lab_notebook | S | S | S | S | S | S | S | S | S | S |
| memory_layout | S | S | S | S | S | S | S | S | S | S |
| binary_portability | S | S | S | S | S | S | S | S | S | S |

**Reconciliation against role-axis (`prompt_audit.md`):**

V1 additions removed from the matrix above (these roles get a new
`<phase>.md` authored in Implementation, so they are not standing-by):
- `test_engineer x testing-specification`
- `test_engineer x testing-implementation`
- `ui_designer x specification`
- `ui_designer x implementation`

Open question: **`user_alignment x implementation`** marked `by*` --
unresolved whether UserAlignment is genuinely active or standing-by in
implementation. Defer to spec checkpoint with UserAlignment input. If
decided active, the cell becomes `.` and a new `user_alignment/implementation.md`
is authored. If decided standing-by, the cell becomes `S`. The matrix
above shows `by*` as a placeholder; `project_team.yaml` will land with
exactly one of the two states after the checkpoint.

V2 candidates (flagged in `prompt_audit.md` but matrix unchanged for v1):
researcher (5 phases), lab_notebook (2), memory_layout / sync_coordinator
/ binary_portability / project_integrator (2 each). These remain
standing-by under the v1 static definition.

Reverse-direction sweep (phase.md exists but role is really standing-by):
none identified by role-axis. The "no phase.md = standing-by" predicate
is the correct v1 definition.

Notes on `S` rows where a phase.md does NOT exist: identity remains
suppressed at `phase-advance-{main,broadcast}` per #27 -- the agent has no
phase work and does not need its identity re-stated. Agents missing
**both** identity and phase still receive the constraints segment (F8/F9
holes resolved by place-axis returning empty per-place rather than
short-circuiting at the top).

`coordinator` is never suppressed -- it owns the workflow.

These rows are written into `project_team.yaml` as 14 `gating: { suppress: ... }`
entries grouped per phase (place-axis owns the YAML diff).

---

## 6. Failure-mode regression guards

For each prior-run F-number, a one-line statement of how `structural_gate`
or the schema design preserves the existing fix. **You cannot reach a
configuration that re-introduces the failure.**

| F# | Failure | Regression guard |
|----|---------|------------------|
| F1 | Phase-advance broadcast didn't route through `assemble_agent_prompt`; sub-agents missed constraints segment | `structural_gate` floor: `place == "constraints" AND time == "phase-advance-broadcast"` -> always True. Every valid YAML or settings configuration leaves this gate True. |
| F4 | Source-of-truth divergence (hooks vs registry/MCP) | Gate predicate reads `manifest` and `settings` only; both routes pass exclusively through `_LoaderAdapter` / `_filter_load_result`. The prior-run **keystone test** (`abast_accf332_sync/testing/skeptic.md`) is binding: any new code path that reads rules/checks routes through the same projection the constraints segment uses, or the test fails. The gate selects one source, by construction. |
| F5 | `mcp.py` disabled_rules unwired | Settings layer for #28 retains `disabled_ids` as the single source of truth for per-rule scoping. The constraints segment is rendered exclusively by `assemble_constraints_block` (the existing implementation). |
| F7 | Falsy check on `agent.agent_type` | Predicate signature accepts `role: str` and treats `"default"` as a legal value, so `"default"` participates in gating like any other role. The signature itself precludes a falsy-string short-circuit. |
| F8 | `assemble_agent_prompt` returned `None` for default-roled agents -> constraints lost | Place-axis renderers return empty bytes per place; the composer always returns an assembled prompt (absent segments render as empty bytes). `gate(time, "constraints", "default", ...)` follows the structural floor (always True at minimum one site); the segment is rendered. |
| F9 | Empty-digest emitted 138-char placeholder | The empty-digest renderer already returns `""` (sec 1 of `assemble_constraints_block`). Predicate output is a bool gate over a renderer that can return empty bytes, so empty-digest cells emit empty bytes by composition law. |

Untouched failure modes (F3 freshness, F6 `get_phase` overstating rules)
are owned by other axes; the gating axis adds no risk of recurrence
(predicate purity rules out runtime state queries that caused F6).

**F2 (late framing reveal): explicit scope-cut from v1.** F2 is a
workflow-coordination failure -- UserAlignment's reframe arrived after
axis-agents had verdicted on the wrong frame. A gate-driven re-inject on
"framing has shifted" would require runtime state ("has framing
changed?") that breaks predicate purity, AND would re-inject content the
agent has already received -- a different problem from "what arrives at a
given site." F2 belongs to a process/coordination layer (Leadership
review cadence, mid-phase user checkpoints) that this spec does not
touch. Recorded as out-of-scope; revisit in v2 only if a static
gating signal can encode "framing dirty" without runtime state.

---

## 7. Coordination notes

How the other axes feed `gate(...)`:

- **time-axis** -- supplies the closed value set for `time` and pins
  `post-compact = full refresh` (sec 3.3 honors this by excluding
  post-compact from suppressible times). If time-axis adds a 6th
  injection site (e.g. `pull`), gating's domain widens by one literal;
  no schema change required.
- **place-axis** -- supplies the closed value set for `place` and the
  per-place renderers. Gating-axis depends on place-axis splitting
  `_assemble_agent_prompt` so each segment is independently
  gateable (R-comp-1). The constraints renderer's empty-string contract
  is the F9 fix at the gate boundary.
- **role-axis** -- supplies the canonical role list and authors the
  per-role audit that confirms the standing-by matrix in sec 5. Where
  role-axis recommends adding a `<phase>.md` file (filling a "S" cell),
  the matrix entry should be removed before lock; coordination is
  bidirectional.

`structural_gate` is the contract every axis must respect. It is the only
place where this axis crosses into other axes' domains, and it does so
only to enforce the regression floor in sec 6.

---

## 8. Verification (sketch)

A. **Predicate purity test** -- given fixed `(time, place, role, phase,
   settings, manifest)`, repeated calls return the same `bool` and produce
   no I/O. Mock-based check.

B. **Structural-floor tests** -- one test per row of sec 6 demonstrating
   the regression guard cannot be circumvented via any combination of
   YAML + settings.

C. **#27 phase YAML round-trip** -- parse `gating: suppress: ...`, verify
   `gate(...)` returns False for the named cells and True elsewhere.

D. **#28 settings round-trip** -- write a config file with each format
   value, confirm `assemble_constraints_block` honors it without
   touching gate-True/False.

E. **Standing-by matrix parity** -- for project_team, verify the materialized
   YAML produces the sec 5 matrix exactly.

F. **Other-workflow no-regression** -- tutorial / learner workflows
   (no `gating:` blocks) produce byte-identical launch prompts to today.

---

*End of spec body. Word count target: <800. Operational only; rationale
deferred to "Appendix candidates" in SPEC.md.*
