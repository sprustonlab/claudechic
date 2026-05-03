# spec_place_axis.md

**Axis:** Place -- the prompt segments carrying delivered context.
**Author:** place-axis agent. Specification phase, v1.
**Reports to:** coordinator (`message_agent("claudechic", ...)`).
**Compositional law:** `inject(t, p, r) = render(p, ctx(t, r)) if gate(t, p, r, phase, settings, manifest) else EMPTY`. This spec fixes the **place** dimension (`p`).
**Inputs read:** `STATUS.md`, `leadership_findings.md`, `failure_mode_map.md`, prior-run `abast_accf332_sync/{SPEC,spec_engine_seam,spec_guardrails_seam}.md`, `claudechic/workflows/agent_folders.py`, `claudechic/workflows/engine.py`, `claudechic/workflows/_substitute.py`, `claudechic/defaults/workflows/project_team/<role>/identity.md` (15 files), `specification/{composability,terminology,place_axis,skeptic_review,user_alignment}.md`, GitHub #27, #28.

This spec supersedes the earlier draft at `specification/place_axis.md` and the v0 at `spec_place_axis.md`. It is the canonical place-axis spec. Per-segment renderers, environment-segment promotion, and the constraints on/off seam are answered in operational form (signatures, shapes, file diffs) rather than narrative form.

---

## 0. Quick map -- six required answers

| § | Question | One-line answer |
|---|----------|-----------------|
| 1 | Identity / phase split | Five private renderers `_render_<segment>(ctx) -> str` (identity, phase, constraints_stable, constraints_phase, environment); `assemble_agent_prompt` becomes a thin orchestrator returning `str | None`; external API + callers unchanged. Constraints split per gating-axis user-driven semantics (§1.3, T3 phase-delta-only). Time enum per gating-axis: 4 sites (spawn, activation, phase-advance, post-compact). |
| 2 | Environment promotion | First-class peer; minimum content pinned in §2.4 with **two activation options** (workflow-agnostic A1 vs project_team-only A2) for the user's D1 decision. |
| 3 | #28 on/off seam | `format-tweak` and `scope-only` ship in v1; `opt-out` is not exposed (no `enabled: false` key in schema). Per BYPASS (SPEC_bypass.md §3.10), gate is single-layer `gate = user_gate` -- no engine floors. Settings keys + schema guard in §3. |
| 4 | F4 resolution | Single-source invariant per segment: every renderer reads through exactly one resolver; for both constraints slices that resolver is `assemble_constraints_block(..., slice=...)` -> `_LoaderAdapter` -> `_filter_load_result` -- no parallel rule-reading path is admissible (§4). |
| 5 | F-number map | One row per F1..F9 with this axis's verdict (§5). |
| 6 | Predicate half | Place-axis contract: `place ∈ {identity, phase, constraints_stable, constraints_phase, environment}`, each segment has a `render_<place>` returning `str` (`""` = empty), purity + single-source per §6. |

---

## 1. Identity / phase split (R-comp-1, F8, F9, #27 enabler)

### 1.1 Why we split

Today (`agent_folders.py:75-78`) identity and phase concatenate inside `_assemble_agent_prompt`:

```python
if phase_content:
    combined = f"{identity}\n\n---\n\n{phase_content}"
else:
    combined = identity
```

Issue #27 wants **identity-only suppression at phase-advance for standing-by agents** without dropping phase content. Today this is impossible without:
(a) a "suppress identity" flag threaded into the assembler (Place-into-Time leak), or
(b) post-processing the returned string by the caller (Place-into-callers leak).

Both leak the place axis into adjacent axes. The compositional law (composability §4) requires segments be independently retrievable at the seam. The split is the F8/F9 enabler at the place boundary.

### 1.2 New module shape (single file, no new module, no class hierarchy)

All four renderers and the orchestrator live **in `claudechic/workflows/agent_folders.py`**. Skeptic shape constraint preserved: no `claudechic/workflows/segments/` package; no class hierarchy; private module-level helpers. Total LOC delta: ~80 lines added, ~30 lines removed (`_assemble_agent_prompt` body shrinks; orchestrator adds 4 calls + join).

### 1.3 Renderer signatures (lock)

Each renderer is a pure function over a frozen `RenderContext` dataclass. **Purity is the contract**: same inputs -> same bytes; no I/O outside the resolver named for that segment; no clock; no globals.

```python
# claudechic/workflows/agent_folders.py

@dataclass(frozen=True)
class RenderContext:
    """Frozen inputs for a single render call. Pure from this point down."""
    role: str                           # agent_type, "default" allowed
    phase: str | None                   # qualified phase id or None
    workflow_dir: Path | None           # winning-tier workflow dir; None if no workflow
    artifact_dir: Path | None           # for ${CLAUDECHIC_ARTIFACT_DIR}
    project_root: Path | None           # for ${WORKFLOW_ROOT}
    loader: ManifestLoader | None       # for constraints projection
    engine: Any | None                  # for advance-checks digest + env facts
    active_workflow: str | None         # workflow id
    disabled_rules: frozenset[str]      # never None; empty frozenset is the unset value
    settings: GateSettings              # frozen; from CONFIG + ProjectConfig (gating §4)
    manifest: GateManifest              # frozen; from LoadResult (gating §3)


def _render_identity(ctx: RenderContext) -> str:
    """Read <workflow_dir>/<role>/identity.md and apply inline ${VAR} substitution.

    Returns "" when:
      - ctx.workflow_dir is None (no active workflow), OR
      - <workflow_dir>/<ctx.role>/identity.md does not exist (default-roled or
        unconfigured role).
    Never returns None. Never short-circuits the wider prompt to None.
    """

def _render_phase(ctx: RenderContext) -> str:
    """Read <workflow_dir>/<role>/<bare_phase>.md and apply inline ${VAR} substitution.

    Returns "" when:
      - ctx.phase is None, OR
      - ctx.workflow_dir is None, OR
      - the per-phase markdown does not exist (standing-by case).
    """

def _render_constraints_stable(ctx: RenderContext) -> str:
    """Render the global + role-scoped slice of the ## Constraints block.

    Routes through assemble_constraints_block(..., slice="stable") -- the
    helper accepts a slice kwarg that filters compute_digest's output to
    rules with no `phase:` qualifier (i.e. global-namespace rules and
    workflow-rules scoped only by `roles:`, NOT by `phases:`). Advance
    checks are NEVER part of the stable slice (they are phase-bound by
    nature).
    Honors #28 settings: ctx.settings.constraints_segment.format /
    include_skipped (table format applies; scope.sites is consumed by
    user_gate, not by the renderer).
    Returns "" when the stable slice is empty (today's empty-digest
    contract -- F9 floor).
    """

def _render_constraints_phase(ctx: RenderContext) -> str:
    """Render the phase-scoped slice of the ## Constraints block.

    Routes through assemble_constraints_block(..., slice="phase") --
    rules whose scoping includes `phases: [<ctx.phase>]` PLUS the
    advance-checks for ctx.phase. This is the slice that changes
    phase-to-phase and is the phase-advance "delta" carrying the
    actual scope change at T3 (phase-advance).
    Same #28 settings honored as _render_constraints_stable.
    Returns "" when no phase-scoped rules apply AND no advance-checks
    exist for the phase. F1 closure is engine-plumbing only (BYPASS):
    T3 phase-advance routes through assemble_agent_prompt -> this
    renderer when "phase-advance" is in user's scope.sites. No gate-
    layer floor force-injects T3 against the user's settings choice.
    """

def _render_environment(ctx: RenderContext) -> str:
    """Render the environment-segment markdown.

    Returns "" when:
      - ctx.engine is None (no engine attached), OR
      - the active workflow has not opted in (D1=A2 path), unless mechanism
        is workflow-agnostic (D1=A1 path), OR
      - ctx.settings.environment.enabled is False (user-tier opt-out for
        the segment).
    See §2 for content + activation options.
    """
```

### 1.4 Orchestrator signature (external API unchanged)

The public `assemble_agent_prompt(...)` signature **does not change**. The five injection-site callers see the same call shape they see today (composability constraint §4: "Existing inject-site call signatures should not change").

```python
def assemble_agent_prompt(
    role: str,
    phase: str | None,
    loader: ManifestLoader | None,
    *,
    workflow_dir: Path | None = None,
    artifact_dir: Path | None = None,
    project_root: Path | None = None,
    engine: Any | None = None,
    active_workflow: str | None = None,
    disabled_rules: frozenset[str] | None = None,
) -> str | None:
    """Single composition point for every injection site.

    1. Build a RenderContext from the kwargs + (settings, manifest) read from
       CONFIG/ProjectConfig and loader respectively. (One read; passed by
       reference into renderers; never re-read inside renderers.)
    2. For each place in PLACES = [identity, phase, constraints_stable,
       constraints_phase, environment]:
         segment = render_<place>(ctx) if gate(time, place, ...) else ""
       The composer treats "" as "skip"; the gate is the policy seam (gating
       §1) and the renderer's "" is the data seam. **No renderer reads
       ctx.time** -- the per-site segment-set decision lives entirely in the
       gate (time-axis §2.0 default segment set; gating §1a default-cell
       table).
    3. Join non-empty segments with SEPARATOR = "\n\n---\n\n" between
       identity and phase, JOIN_TAIL = "\n\n" before each constraints slice
       and before environment. Adjacent constraints_stable + constraints_phase
       slices in the same emission render as ONE continuous "## Constraints"
       block (the renderer of the first slice owns the heading; the second
       slice appends without a duplicate heading -- §1.7).
    4. Return the joined string, or None when ALL five segments are empty
       AND no active workflow attaches (preserves prior None-on-fully-empty
       semantics for callers that test truthiness).

    The current helper's signature is preserved for the five callers below.
    The 'time' value is read from a new keyword-only parameter introduced in
    a non-breaking way (see §1.5).
    """
```

### 1.5 Caller updates (4 sites)

The four injection sites call `assemble_agent_prompt(...)` today. Each call gains **one** new keyword-only argument: `time: InjectionSite`. The argument has no default in v1 (callers must pass it), but the change is non-breaking because all four sites are inside this repo and updated atomically with the renderer split.

| Site | File:line (today) | Change |
|------|-------------------|--------|
| T1 spawn | `claudechic/mcp.py:308` | add `time="spawn"` |
| T2 activation | `claudechic/app.py:2131` | add `time="activation"` |
| T3 phase-advance | `claudechic/mcp.py:1026` | add `time="phase-advance"` |
| T4 post-compact | `claudechic/workflows/agent_folders.py:362` | add `time="post-compact"` |

The orchestrator threads `time` into `gate(time, place, ...)`. Callers do **not** pass per-segment flags; gating is the only policy seam.

**Removed from the v0 enumeration:** `phase-advance.main` (was synchronous `advance_phase` tool return value -- the main agent reads its phase context off the tool reply, not via an injection-site call). `phase-advance.broadcast` is renamed to `phase-advance` since broadcast is now the single phase-advance injection moment.

### 1.6 Compatibility wrapper (one release)

`assemble_phase_prompt(...)` (currently used by `_inject_phase_prompt_to_main_agent`) stays as a thin wrapper for one release, then is removed in v2. The wrapper calls `assemble_agent_prompt(...)` with no `time=` argument; its return value flows back as the synchronous `advance_phase` tool reply, NOT as an injection-site assembly. The wrapper preserves the byte shape `_inject_phase_prompt_to_main_agent` expects without claiming that path is an injection site.

### 1.7 Return-shape parity

The current public output shape is `f"{phase_prompt}\n\n{constraints}"` (composability sec 4 compatibility constraint). The new orchestrator must produce **byte-identical** output for the all-gates-True case at T1/T2/T4 (the three full-block sites) so the law-parity test (composability §10 plan A) passes. Concretely:

```
SEPARATOR = "\n\n---\n\n"   # the existing identity/phase separator
JOIN_TAIL = "\n\n"          # constraints joins with two newlines
```

The composer joins identity + phase with `SEPARATOR` (matching today), then handles the constraints pair specially: when **both** stable and phase slices are non-empty AND emitted at the same site, it joins them as `JOIN_TAIL + stable_text + "\n\n" + phase_text` to produce ONE continuous `## Constraints` block (same byte shape as today's monolithic block). The phase-only renderer emits its own `## Constraints` heading when stable is absent (T3 phase-advance), so the slice is independently well-formed when emitted alone. Environment appends with `JOIN_TAIL` after constraints. The fixture-byte-parity test in `tests/test_phase_injection.py` is the regression guard at T1/T2/T4; a new `tests/test_phase_advance_constraints_delta.py` covers the T3 phase-only delta shape.

**Stable + phase concatenation correctness:** the helper `assemble_constraints_block(..., slice=...)` accepts an additional kwarg `omit_heading: bool` so the second-slice render skips the leading `## Constraints` line when it is being concatenated to a stable slice. The composer sets `omit_heading=True` for the phase slice when both fire at the same site (T1/T2/T4); otherwise both slices render their own heading (which is only ever observed at T3 with stable absent, so no duplicate-heading regression is reachable).

---

## 2. Environment as a first-class peer segment (D1)

### 2.1 What the environment segment is

A **standalone prompt segment** carrying claudechic-runtime knowledge as its own header block in the launch prompt. Distinct from inline `${VAR}` substitution (which is a renderer property of identity/phase content -- see §6). Distinct from `awareness_install.py` (host-side `~/.claude/rules/claudechic_*.md`, written once at startup).

The user requirement is priority #2 from `leadership_findings.md`: *"Spawn-time claudechic-environment knowledge for agents -- regardless-of-workflow vs project_team-only is open"*. This segment is the in-prompt half of the user's "agents know they live in claudechic" requirement.

### 2.2 Why promote now (vs keep latent inline `${VAR}`)

Four concrete enablements that latent substitution cannot deliver:

1. **Runtime/peer/team-dynamics content host-side rules cannot deliver.** `awareness_install.py` writes static markdown. The segment can carry: workflow id, peer roster (live agent list at spawn), MCP tool reference scoped to active workflow, runtime-substituted cwd / artifact_dir / project_root, team-dynamics framing.
2. **Agent name routing.** Prior-session concrete failure (surfaced by role-axis): composability lead called `message_agent(name="coordinator")` but the main agent's registered name was `claudechic`. The role-vs-registered-name disambiguation is runtime-only data -- no static markdown can carry it. The `${NAME_ROUTING_TABLE}` token in §2.4.1 is the closure.
3. **Post-compact recovery parity.** `/compact` strips SDK context; without an environment segment in the post-compact bundle, agents lose claudechic-runtime knowledge each compact (F3-adjacent residual risk).
4. **Default-roled / non-workflow-agent coverage.** Default-roled agents have empty identity + empty phase. Today they receive only the constraints segment when global rules apply; they have no "you are inside claudechic" surface. A workflow-agnostic environment segment fills this gap.

Enablement 2 is the closest thing to a backward F-fix this list carries -- the failure was a real prior-session miss, not yet catalogued as F1-F9. The other three are forward user-requirement enablements.

### 2.3 Two activation options (the D1 decision)

The team has converged that the **mechanism** is first-class v1; the **activation** scope is a user decision.

| Option | Mechanism | Activation default | Crystal cells | Held by |
|--------|-----------|--------------------|----|---------|
| **A1. Workflow-agnostic (always-on)** | `_render_environment(ctx)` always non-empty when `ctx.engine is not None`; non-workflow spawn falls back to `engine=None` -> empty | always-on; user-tier `disabled_ids: global:environment-segment` opts out | 4 × 5 × 16 = 320 | place_axis, time_axis, gating_axis, user_alignment |
| **A2. Workflow opt-in (default false)** | Same renderer; renderer reads `manifest.environment_segment_enabled` and returns `""` when False; activates per-workflow YAML field `environment_segment: enabled` | project_team opts in; tutorial / cluster_setup / etc. stay opted-out | 4 × 5 × 16 = 320 (mechanism), effective for project_team | composability (post-Q-T3), skeptic |

Both options ship the **same renderer** and the **same content source** (§2.4); they differ only in the activation default. Skeptic R5 is honored under either: A2 by construction (8 of 9 workflows render byte-identical to today); A1 by `disabled_ids` opt-out + an empty fallback when no engine attaches.

**Recommended call (place-axis position):** **A2** for v1 -- not because A1 is wrong (the user explicitly asked for "regardless of workflow"), but because A2 is the smaller behavior change and lets v1 ship the full mechanism while leaving the per-workflow expansion to v2 PRs that don't fight Skeptic R5. The user can pick A1 at the Spec checkpoint and the implementation flips one default.

### 2.4 Pinned minimum content (v1, both options)

The environment segment renders this content **always** (when active per the chosen option). Workflow-agnostic content lives in `base.md`; workflow-specific overlays live in `<workflow>.md`. Both append into the same single segment.

#### 2.4.1 `base.md` -- workflow-agnostic content (runtime-dynamic)

```
## Environment

You are an agent inside claudechic, a TUI wrapper around the Claude Agent SDK.

- Workflow: ${ACTIVE_WORKFLOW}            (or "(none)" if no workflow)
- Role: ${AGENT_ROLE}                     (your agent_type)
- cwd: ${WORKFLOW_ROOT}                   (the launched-repo root)
- Artifact dir: ${CLAUDECHIC_ARTIFACT_DIR} (run-bound; "(unset)" if no
                                           set_artifact_dir call yet)

### Agent name routing (this run)

When you call `message_agent(name=...)`, use the **registered name**, NOT
the role. The registered name may differ from the role (e.g. the main
agent's role is `coordinator` but its registered name is `claudechic`).

| role          | registered name        |
|---------------|------------------------|
${NAME_ROUTING_TABLE}

### Peers (this run)

${PEER_ROSTER}                            (registered names, newline-separated)

### Available claudechic MCP tools (relevant subset for your role)

${MCP_TOOL_LIST}

### Coordination

${COORDINATION_PATTERNS}

Re-read this block after each /compact (it is re-injected automatically).
```

**The agent name routing table closes a concrete prior-session failure surfaced by role-axis** (composability lead messaged `coordinator` but actual registered name was `claudechic`). The table is computed at injection time from `agent_manager.agents`: `{agent.agent_type -> agent.name}` where `agent.agent_type != DEFAULT_ROLE`. The main agent appears as `(coordinator -> claudechic)` -- the canonical router-vs-role disambiguator.

#### 2.4.2 `project_team.md` -- workflow-static overlay (peer summaries)

Loaded only when `ctx.active_workflow == "project_team"`. Appended to the base segment under a `### Project team peers (descriptions)` heading. **2 sentences per peer**, sourced from each role's `identity.md` Prime Directive / opening section -- not the full identity content (Skeptic R3: identity authority statements stay in identity files; this overlay carries summaries only).

```
### Project team peers (descriptions)

- **coordinator** -- Delegates work; reads STATUS.md and routes to the right
  role. Owns workflow phase advance.
- **composability** -- Architectural lens. Owns crystal/seam/algebraic decomposition
  of any spec-level decision.
- **terminology** -- Canonical-glossary lens. Owns one-name-one-meaning across
  Specification artifacts.
- **skeptic** -- Adversarial reviewer. CAN demand pushback; CANNOT cut features
  the user requested.
- **user_alignment** -- Vision-guardian. Quotes user verbatim; CAN override
  Skeptic on user-protected features.
- **researcher** -- Literature / prior-art lens. Investigates published work
  before designs commit.
- **implementer** -- Writes code. Bound authority: no scope creep, no
  architecture freelancing.
- **test_engineer** -- Writes tests. No-mock / no-skip / public-API / real-infra.
- **ui_designer** -- UX lens. Domain-first; verifies with UserAlignment.
- **lab_notebook** -- Pre-registration + reproducibility lens. Records
  decisions before they execute.
- **researcher / lab_notebook / memory_layout / sync_coordinator /
  binary_portability / project_integrator** -- domain specialists; spawned
  only when the active phase needs their lens.

(Full role authority lives in each role's identity.md; the bullet above is
a pointer, not a substitute.)
```

The actual sentence content for each role is sourced one-time during Implementation by the role-axis agent (per role-axis §4a one-shot audit) from each `<role>/identity.md`. The overlay is **static** content (compiled-in markdown), not runtime-substituted -- updates flow through bundled-content edits.

#### 2.4.3 Substitution resolver and bundle dir

Bundle dir: `claudechic/defaults/environment/`. v1 ships exactly **two files**:

- `claudechic/defaults/environment/base.md` -- runtime-dynamic template (§2.4.1). Read by `_render_environment` and substituted via `_substitute.py` (extended with `AGENT_ROLE_TOKEN`, `ACTIVE_WORKFLOW_TOKEN`, `PEER_ROSTER_TOKEN`, `NAME_ROUTING_TABLE_TOKEN`, `MCP_TOOL_LIST_TOKEN`, `COORDINATION_PATTERNS_TOKEN`).
- `claudechic/defaults/environment/project_team.md` -- workflow-static overlay (§2.4.2). Pure markdown, no tokens. Concatenated to `base.md` output by `_render_environment` when `ctx.active_workflow == "project_team"`.

**The 6 tokens in `base.md` are pure runtime substitution from engine state** -- the renderer asks the engine for its workflow id, the agent_manager for the peer roster + name routing table (`{agent_type: name}` map), and the MCP server for the tool list. All read-only; no mutation. The rendering is per-injection-site live (§6.1 freshness contract).

**Excludes (Skeptic R3 preserved):** phase logic, role authority statements (identity files own these), project state, message history. The segment carries claudechic-runtime facts and peer-discovery aids only.

### 2.5 Why a separate segment vs inline `${VAR}`

Inline `${VAR}` has three structural limits the environment segment removes:

| Limit | Inline `${VAR}` | Environment segment |
|-------|-----------------|---------------------|
| Per-author opt-in | Each role file must opt in by adding `${VAR}` references to its content | Once-per-workflow opt-in (or workflow-agnostic) |
| Runtime content beyond paths | Only path-like substitution (file system handle); peer roster, MCP tool list, team dynamics not expressible | Full markdown header with computed values |
| Default-roled agent coverage | None -- no role file means no inline references | Renderer fires for default-roled agents too |
| Post-compact parity | Survives compact (it is in the agent's transcript already) | Survives compact (re-injected by T4 post-compact) |
| Audit/discoverability | Diffuse across 15 role files | One bundle dir, one renderer |

The first three drove the user's request; the last two are organizational wins. Inline `${VAR}` stays as-is alongside (R-comp-7).

---

## 3. Constraints segment configurability (#28 on/off seam)

### 3.1 Skeptic R2 is binding

The constraints segment is the v0 fix for F4/F5/F7. R2 from `leadership_findings.md`: *"opt-out reintroduces F4/F5/F7 silently."* This axis names three options for the seam and pins their consequences explicitly.

| Option | Description | Consequence |
|--------|-------------|-------------|
| **format-tweak** | User picks how the block renders (markdown table vs list vs compact-list); content unchanged | F4/F5/F7 unchanged. Visual presentation only. |
| **scope-only** | User picks **which injection sites** carry the segment (subset of T1-T4); content unchanged | F4/F5/F7 routing remains engine-plumbed: every in-scope site routes through `assemble_constraints_block` -> `_LoaderAdapter` -> `_filter_load_result`. Single-source invariant holds for every cell the user keeps; a user who narrows `scope.sites` to omit phase-advance accepts the consequence (agents miss the constraints delta on phase advance) -- per BYPASS authorization (SPEC_bypass.md §3.10), this is the user's call, not an engine-prevented mistake. |
| **opt-out** | User toggles `enabled: false` to remove the segment entirely | **F4/F5/F7 re-introduced silently.** Hooks would still fire (loader projection still active), but the agent's prompt would not advertise its scoped rules. **Schema-excluded:** the `enabled` key is not in the config schema (§3.2 "Excluded by design"); a user who wants the segment off must narrow `scope.sites` instead, which is observable, not silent. |

**Decision (locked, Skeptic R2 + R-comp-3 + UserAlignment §5.8, with BYPASS update):** ship `format-tweak` and `scope-only`. `opt-out` is not exposed because no `enabled: false` key exists in the schema (§3.2 "Excluded by design"). The user can narrow scope to a subset of sites; they cannot toggle the segment off entirely, because that key is not in the config schema. Per BYPASS authorization (SPEC_bypass.md §3.10), the engine does not floor-pin any specific cell to True; the schema-level absence of `enabled: false` is the only mechanism keeping opt-out off the surface. A user who sets `scope.sites: [spawn]` (only) and accepts F1-class regression on phase-advance is making a documented, authorized choice.

### 3.2 Settings keys

Both user-tier (`~/.claudechic/config.yaml`) and project-tier (`<project>/.claudechic/config.yaml`) accept the same shape; project-tier overrides user-tier (existing claudechic precedence).

```yaml
constraints_segment:
  format: markdown-table             # markdown-table | markdown-list | compact-list
  include_skipped: false             # bool, default false
  scope:
    sites: [spawn, activation, phase-advance, post-compact]
```

**Excluded by design:**
- `enabled: false` -- R-comp-3 / Skeptic R2.
- `disabled_rules` -- already covered by `disabled_ids` (single source).
- Per-rule include lists -- would re-introduce source-of-truth divergence pressure with `disabled_ids`.
- Per-role include / exclude lists -- not requested; would create three sources.

### 3.3 Semantics (gate seam)

The orchestrator (§1.4) reads the loaded `GateSettings` once at startup. Both `_render_constraints_stable(ctx)` and `_render_constraints_phase(ctx)` honor `format` and `include_skipped` directly (same setting applies to both slices uniformly). The `scope.sites` list is consumed by `user_gate(time, "constraints_stable" | "constraints_phase", ...)`. v1 ships **one** `scope.sites` setting under `constraints_segment.scope.sites` that applies to both slices identically; per-slice `scope.sites` is out of v1.

**Gate is single-layer (BYPASS, SPEC_bypass.md §3.10).** `gate = user_gate` for every `(time, place, role)` combination. The user's `scope.sites` choice is honored exactly at every cell -- there is no `structural_gate` floor that force-injects a cell against the user's setting.

**Default cells (recommended, not enforced).** When the user accepts the shipped default `scope.sites = [spawn, activation, phase-advance, post-compact]`, the cells fire as:

| time | constraints_stable | constraints_phase |
|------|-------------------|-------------------|
| T1 spawn | True (full block) | True |
| T2 activation | True | True |
| T3 phase-advance | False (delta-only by composer rule §1.7) | True |
| T4 post-compact | True (full refresh) | True |

A user who narrows `scope.sites` to a subset accepts the documented consequence: omitting `phase-advance` means agents miss the constraints delta on phase advance; omitting `post-compact` means the constraints segment goes stale across `/compact`. Per BYPASS authorization, these are user choices, not engine-prevented mistakes.

**The only config-load guard** is a typo guard, not a floor: `constraints_segment.scope.sites = []` raises `ConfigValidationError` at startup (a setting cannot mean "the segment lives in the schema but never fires" -- that is the opt-out path the schema deliberately doesn't expose).

**F1 closure is engine-plumbing, not gate-pinning.** The phase-advance injection site (T3) routes through `assemble_agent_prompt` which routes through `_render_constraints_phase` which routes through `assemble_constraints_block(..., slice="phase")` which routes through `_LoaderAdapter` -> `_filter_load_result`. F1's regression cause was that the broadcast loop bypassed the helper entirely; under the BYPASS-era engine plumbing it cannot. If the user puts T3 in `scope.sites`, the constraints delta is delivered through the canonical projection. If the user removes T3, the delta is not delivered -- but the routing remains canonical for every site that IS in scope. F1 cannot recur via a parallel projection; it can only recur if the user explicitly authorizes the absence by narrowing scope.

### 3.4 Format renderers (consumer detail)

Both `_render_constraints_stable` and `_render_constraints_phase` accept `ctx.settings.constraints_segment.format` (uniformly). v1 ships three format functions inside `assemble_constraints_block`:

| format value | Output shape | Purpose |
|--------------|--------------|---------|
| `markdown-table` (default) | Today's `\| id \| enforcement \| trigger \| message \|` table | Existing behavior; F-fix parity. |
| `markdown-list` | `- **id** (enforcement, trigger): message` per rule | Per Skeptic note "easier to scan in narrow contexts" |
| `compact-list` | `- id [enforcement, trigger]` (no message body) | For high-rule-count workflows |

`include_skipped` is a separate bool that adds the audit `skip_reason` column (already exists in the helper for `get_agent_info` use); now exposed via config.

---

## 4. Resolving F4 (source-of-truth divergence)

### 4.1 The F4 invariant (single-source per segment)

F4's prior-run fix in `abast_accf332_sync` was `_LoaderAdapter` -- a shim that routes the guardrail hook layer's rule reads through the same `_filter_load_result` projection used by the registry layer. The keystone test (binding) verifies hooks and registry produce identical projections.

This axis adds the **per-segment single-source invariant**: each `_render_<place>` reads through exactly one resolver, and no other code path may produce that segment's bytes. The invariant is structural (per-renderer, not per-call):

| segment | sole resolver | also consumed by | F-fix |
|---------|--------------|-------------------|-------|
| identity | bundled markdown read of `<workflow_dir>/<role>/identity.md` (with `_substitute`) | nothing -- `_render_identity` is the only assembler | F8 (per-segment, never short-circuit None) |
| phase | bundled markdown read of `<workflow_dir>/<role>/<phase>.md` (with `_substitute`) | nothing -- `_render_phase` is the only assembler | F8 (same) |
| constraints_stable | `assemble_constraints_block(..., slice="stable")` -> filtered `compute_digest` (no `phase:` qualifier); upstream of `_LoaderAdapter` -> `_filter_load_result` | guardrail hooks (via `_LoaderAdapter`); `get_applicable_rules` MCP tool (full projection) | **F4 single-source invariant** -- the `slice=` kwarg is a filter on the SAME projection, never a parallel resolver |
| constraints_phase | `assemble_constraints_block(..., slice="phase")` -> filtered `compute_digest` (rules with `phases: [<phase>]`) + `compute_advance_checks_digest`; same upstream | same as above | **F4 + F5 closure** -- `disabled_rules` flow through the same `compute_digest` call regardless of slice. **F1 closure -- engine-plumbing only:** T3 phase-advance routes through `assemble_agent_prompt` -> this renderer -> `_LoaderAdapter`. If T3 is in `scope.sites`, the delta is delivered via the canonical projection; if the user narrows scope to omit T3, F1-class regression is the user's authorized choice (SPEC_bypass.md §3.10). No gate-level floor force-injects T3. |
| environment | engine state read (`engine.workflow_id`, `agent_manager.agents`) + bundle markdown overlay | nothing | (no F-fix; new) |

**Slice-split single-source invariant.** The two constraints renderers share **one resolver call shape** (`assemble_constraints_block(..., slice=<value>)`) and one upstream projection (`_LoaderAdapter` -> `_filter_load_result`). The F4 keystone test is extended from "hooks projection == registry projection" to additionally cover "stable + phase slices, when concatenated, equal the full projection a hook would surface for the same `(role, phase)`". Concretely: `assemble_constraints_block(..., slice="stable") + assemble_constraints_block(..., slice="phase")` MUST equal `assemble_constraints_block(..., slice=None)` modulo the omit_heading concatenation rule (§1.7). This is the slice-split keystone invariant.

### 4.2 What the invariant forbids

A new code path would violate the invariant if it:

- (a) Renders a `## Constraints` block from anything other than `assemble_constraints_block(..., slice=...)`. **Forbidden.** Any new MCP tool wanting to expose rules must call the same helper (with `slice=None` for the full projection) -- the same path `get_agent_info` uses today.
- (b) Reads identity / phase markdown from a path other than `_render_identity` / `_render_phase` (e.g. a stash of role authority statements duplicated into a workflow-coordination doc). **Forbidden** for the launch prompt; advisory docs are fine, but they MUST NOT be assembled into the launch prompt by any other route.
- (c) Bypasses `_LoaderAdapter` for rule reads. **Forbidden.** Keystone test binding (failure_mode_map.md row F4).
- (d) Implements slice filtering anywhere other than inside `assemble_constraints_block`. The two renderers (`_render_constraints_stable`, `_render_constraints_phase`) MUST call the helper with their `slice=` kwarg and not post-filter the returned bytes. Post-filtering would be a parallel projection in disguise.

### 4.3 What the invariant guarantees

For every segment, the answer to *"where do these bytes come from?"* is one file path (a function in `agent_folders.py`). The keystone test extends naturally: hooks / registry / launch prompt all produce identical projections for the rules they each surface. F4 cannot recur because the gate predicate (per gating §1 purity contract) reads `manifest` and `settings` only -- neither exposes a parallel rule-reading path.

### 4.4 Inline `${VAR}` substitution single-source

The four renderers consume `_substitute.substitute_artifact_dir` and `_substitute.substitute_workflow_root` (extending in v1 with environment-segment tokens per §2.4). `_substitute.py` is the **only** substitution resolver in the workflow path. The engine's `_run_single_check` and the agent_folders renderers both call into this module; no second substitution mechanism is admissible. R-comp-7 / Skeptic R5 hold structurally.

---

## 5. F-number map (place-axis verdicts)

For each F-number in `leadership_findings.md`, this table states whether the failure is a **place-axis concern** and how this spec addresses it. The canonical fate is in `failure_mode_map.md`; this column is the place-axis-specific contribution.

| F# | Place-axis concern? | Place-axis change |
|----|--------------------|-------------------|
| F1 | **No** (time-axis owns phase-advance routing) | Place provides per-segment renderers so time-axis can compose `constraints_phase` only at T3 (phase-advance) without the F1 short-circuit. With the slice split, T3 carries `constraints_phase` (the actual phase-advance delta). **F1 closure is engine-plumbing only** (BYPASS, SPEC_bypass.md §3.10): T3 routes through `assemble_agent_prompt` -> `_render_constraints_phase` -> `_LoaderAdapter`. The original F1 cause (broadcast loop bypassed the helper entirely) cannot recur via a parallel projection. F1 CAN recur via user-authorized scope narrowing (`scope.sites` omitting `phase-advance`); per BYPASS, that is the user's call. |
| F2 | **No** (workflow-coordination concern) | Out-of-v1 per `failure_mode_map.md`. No place-axis change. |
| F3 | **Partial** (per-segment freshness table is owned here; unification is v2) | §6.1 documents the per-segment freshness contracts. v1 does not unify (Skeptic R4); v2 candidate is unify on per-call live for renderable segments. |
| F4 | **Yes** | §4.1: per-segment single-source invariant. Both constraints renderers route exclusively through `assemble_constraints_block(..., slice=...)`. No parallel path. Slice-split keystone invariant: `stable + phase == full` (§4.1). |
| F5 | **Yes** (constraints renderers' projection) | §4.1: `disabled_rules` flow through `compute_digest` regardless of slice. The settings layer (§3) does NOT expose a parallel `disabled_rules` knob; existing `disabled_ids` retains source. |
| F6 | **No** (`get_phase` is owned by the MCP / D-component substrate) | Pre-existing-fix in `abast_accf332_sync`. Place-axis adds no risk: renderers read manifest and engine state through the same projection D-component uses. |
| F7 | **No** (gating predicate signature owns this) | Place provides `_render_constraints_*` for default-roled agents whenever global rules apply; the F7 fix is the predicate's `role: str` signature (gating §6 row F7). Place is not the home. |
| F8 | **Yes** (the direct precursor to #27) | §1.3 + §1.4: renderers return `""`, never None; orchestrator returns `None` only when ALL FIVE segments are empty. The constraints slices fire for default-roled agents whenever applicable rules exist. F8 closed by construction. |
| F9 | **Yes** (the direct precursor to #27) | §1.3 + §1.7: both constraints renderers return `""` on empty digest (today's contract preserved); composer drops empty segments. No 138-char placeholder. F9 closed by construction. |

**Sweep result:** F4, F5 (partial via constraints renderer), F8, F9 are place-axis-owned. F1 is composed-by-place but owned by time. F2, F6, F7 are not place-axis concerns. F3 is partial (documentation only in v1).

---

## 6. Place-axis half of the compositional predicate

The full predicate is `inject(t, p, r) = render(p, ctx(t, r)) if gate(t, p, r, phase, settings, manifest) else EMPTY`. The **place-axis half** specifies the closed `place` value set, the per-segment `render` contract, and the seam invariants that make the whole law algebraic.

### 6.1 Closed place value set

```python
PLACES: Final[tuple[str, ...]] = (
    "identity",
    "phase",
    "constraints_stable",     # global + role-scoped rules; T1/T2/T4 only
    "constraints_phase",      # phase-scoped rules + advance-checks; T1..T4
    "environment",
)
```

Set is closed under v1. **Five places.** Cell count: 4 times × 5 places × 16 roles = **320 cells**. New places enter only by:
1. New segment with a distinct purpose (who-am-I, what-now, what-bounds-me-stably, what-bounds-me-this-phase, where-am-I).
2. Distinct freshness contract.
3. Distinct source resolver, OR explicit shared-source justification.

The two constraints slices share a resolver (`assemble_constraints_block(..., slice=...)`) but pass distinct slice arguments and have distinct per-site default sets (T3 emits `constraints_phase` only; T1/T2/T4 emit both). The shared-source justification: the slice split is a **content-decomposition** justified by gating-axis's user-driven semantics (T3 phase-advance delta vs T1/T2/T4 full bounds). Single-source invariant (§4.1) is preserved by routing both renderers through the same helper.

`environment` is the v1 fifth member (D1 decision).

### 6.2 Per-segment render contract (the place-axis half)

For every `p in PLACES`, the place-axis pledges:

1. **Closed signature.** `render_<p>(ctx: RenderContext) -> str`. Never returns None. Never raises (errors caught and logged; render returns `""` on error so the gate -> empty -> drop path wins).
2. **Empty-as-skip.** `""` is the gating-of-data signal. The composer drops empty segments. No renderer returns a placeholder.
3. **Self-contained.** `_render_p` does NOT read another segment's bytes. Cross-segment composition is only at the orchestrator.
4. **Pure of inputs.** No globals; no clock; no env reads beyond what `ctx` carries explicitly.
5. **Single source.** `_render_p` reads through exactly one resolver (§4.1 table). No fallback path that reaches a different source.
6. **Stable separator.** Renderers do not include leading or trailing separators. The composer adds `SEPARATOR = "\n\n---\n\n"` between identity and phase, and `JOIN_TAIL = "\n\n"` before constraints + environment, matching today's bytes (§1.7).
7. **Idempotent.** Same `RenderContext` -> same bytes. Always.
8. **Inline `${VAR}` preserved.** `_render_identity` and `_render_phase` apply `substitute_artifact_dir` + `substitute_workflow_root` to their content. `_render_environment` applies the extended substitution set (§2.4). No other tokens. R-comp-7 / R5.

### 6.3 Per-segment freshness contract (F3 documentation, v1)

| segment | source | freshness contract | recompute trigger |
|---------|--------|--------------------|--------------------|
| identity | bundled `<role>/identity.md` | spawn-time freeze (file-mtime per process) | re-read on each injection-site fire (cheap; no cache) |
| phase | bundled `<role>/<phase>.md` | per-injection-site read (file-mtime) | re-read on each injection-site fire |
| constraints_stable | filtered `compute_digest` (no `phase:` qualifier) | per-call live | every `_render_constraints_stable` invocation re-runs the helper with `slice="stable"` |
| constraints_phase | filtered `compute_digest` (rules with `phases: [<phase>]`) + `compute_advance_checks_digest` | per-call live | every `_render_constraints_phase` invocation re-runs the helper with `slice="phase"` |
| environment | runtime substitution from engine state + bundled overlay | per-engine-state-change | every `_render_environment` invocation reads engine + agent_manager + MCP tool list |

F3 (three coexisting freshness contracts) is **documented, not unified**. Skeptic R4 flagged unification as a regression vector for v1. v2 candidate: unify on per-call live for all renderable segments; this is the natural path because renderers are already pure and per-call live is the strongest contract.

### 6.4 Seam invariants

Stated as composability rules:

- **Place / Time seam (§5.1 of composability).** `render_<p>(ctx)` produces the same bytes whether called at T1, T2, T3, or T4. Time is invisible to renderers. Time differs only in the **set of places it asks for** (time-axis §2.0 default segment set) and in **what the gate decides** -- never in how a segment renders. Place-axis enforcement: `RenderContext` has no `time` field.
- **Place / Source seam (§5.2).** Bytes cross the seam; freshness does not. Each segment has a documented contract (§6.3); consumers do not query freshness (the gate evaluates per-call already).
- **Place / Role seam (§5.3).** Role names cross the seam (folder keys); role-specific logic does not enter renderers. `_render_identity` does not have a "if role is coordinator" branch; it reads `<workflow_dir>/<role>/identity.md` and returns its bytes.
- **Place / Gate seam (§5.4).** The renderer returns bytes (or `""`); the gate returns `bool`. The two compose at the orchestrator: `segment = render_<p>(ctx) if gate(...) else ""`. Renderer-empty and gate-suppress are independently observable and produce the same composed result (drop the segment), but they are NOT equivalent: renderer-empty means "no data exists" (place-axis owns); gate-suppress means "config says don't deliver" (gating-axis owns). Where both apply, gate-suppress wins by short-circuit (the renderer is never invoked).

---

## 7. Build plan (place-axis slice; cross-checked vs SPEC.md §5)

Implementer tasks for this axis, in dependency order:

1. **Add `RenderContext` frozen dataclass** in `agent_folders.py`. Pure data carrier; ~15 LOC.
2. **Extract `_render_identity`, `_render_phase`** from `_assemble_agent_prompt`; preserve `_substitute` calls per-renderer. ~30 LOC.
3. **Extend `assemble_constraints_block`** with `slice: Literal["stable", "phase", None]` and `omit_heading: bool` kwargs. The `slice` kwarg filters `compute_digest`'s output (`"stable"` -> rules without `phase:` qualifier; `"phase"` -> rules with `phases: [<phase>]` + advance-checks; `None` -> full projection, today's behavior). Slice-split keystone invariant: `slice="stable"` + `slice="phase"` (with `omit_heading=True` on the second) MUST equal `slice=None` modulo concatenation. ~25 LOC. Add `_render_constraints_stable` and `_render_constraints_phase` wrappers (~10 LOC each). Total ~45 LOC.
4. **Add `_render_environment`** stub returning `""` plus the activation-option flip per D1. ~15 LOC. (Full content per §2.4 lands in step 8.)
5. **Rewrite `assemble_agent_prompt` body** as a thin orchestrator over the four renderers + `gate(...)`. ~30 LOC; `-30 LOC` removed from old body. Net ~0.
6. **Thread `time: InjectionSite` keyword through 5 callers** (table §1.5). One-line change at each.
7. **Extend `_substitute.py`** with environment-segment tokens (`AGENT_ROLE`, `ACTIVE_WORKFLOW`, `PEER_ROSTER`, `MCP_TOOL_LIST`, `COORDINATION_PATTERNS`). ~30 LOC.
8. **Bundle `claudechic/defaults/environment/{base,project_team}.md`** with content per §2.4. Two files.
9. **Wire `GateSettings` plumbing** to read `constraints_segment` + `environment` keys from CONFIG / ProjectConfig. Frozen dataclass; ~30 LOC.
10. **Parity test (byte-identical for all-True gate)** against captured fixtures from each of the 5 inject sites pre-change vs post-change.
11. **F8/F9 regression tests**: default-roled agent at T1/T3 receives constraints alone (constraints_phase at T3, both slices at T1); standing-by agent at T3 receives constraints_phase alone; no 138-char placeholder anywhere.
12. **R-comp-7 regression test**: tutorial / cluster_setup / etc. produce byte-identical launch prompts when `environment_segment: enabled` is unset (A2 path) or when `disabled_ids: global:environment-segment` is set (A1 path).

Estimated total: ~150 LOC added in `agent_folders.py`, ~50 LOC in `_substitute.py`, ~80 LOC in two new bundle files. No new module. No class hierarchy.

---

## 8. Coordination notes

- **time-axis (`spec_time_axis.md`).** Aligned post 4-site enum (gating-axis collapse: T3 phase-advance.main removed as it was always the synchronous tool return, never an injection-site call; T4 phase-advance.broadcast renamed to T3 phase-advance; T5 post-compact renumbered to T4). Place owns the five `render_<place>` renderers + segment enum + freshness table. Time owns the default segment set per site (§2.0 of time-axis). The seam is `time` -> default segment set + gate predicate inputs; place renders. Time-axis §2.0 environment column resolution (D1=A2 working default) matches §2.3 here; if D1=A1 lands, time-axis flips one row to "True at T1/T2/T4 always."
- **gating-axis (`spec_gating_axis.md` -> superseded by SPEC_bypass.md §3.10).** Aligned. Place owns the renderer-empty data path; gating owns the gate-suppress policy path. **Per BYPASS the gate is single-layer** (`gate = user_gate`); no `structural_gate` floor. The place-axis YAML diff for `environment_segment: enabled` lives in this axis. The per-segment renderer-empty contract is the F8/F9 fix at the gate boundary; F1 closure is engine-plumbing only (canonical routing through `_LoaderAdapter`), not floor-pinning.
- **role-axis (`spec_role_axis.md`).** Aligned. Per-role audit consumes the four-segment list (§1.3 of role-axis). Default pattern (13 of 16 roles) maps to `identity / phase / constraints / environment` cleanly. Authority preservation (§2 of role-axis) does not touch place-axis renderers; it touches the bundled markdown content.
- **terminology (`specification/terminology.md`).** Segment names verbatim per glossary §1.2. Inline substitution stays first-class as a renderer property; environment segment is the standalone-block grain. No renames needed.
- **skeptic.** R-comp-3 (constraints opt-out re-introduces F4/F5/F7) and R3 (identity authority preservation) are honored: §3 rejects opt-out structurally; §2.4 environment content excludes role authority.
- **user_alignment.** Priority #2 (claudechic-environment knowledge regardless of workflow) is preserved at the **mechanism** level (renderer is workflow-agnostic v1) and surfaced at the **activation** level (D1 decision A1 vs A2). Priority #3 (review and suggest) is out-of-axis (workflow-coordination, role-axis §4).

---

## 9. What this spec does NOT do (out-of-v1)

- **Unify per-segment freshness contracts** (F3 closure). Documented (§6.3); unification is v2.
- **Promote `chicsession-resume` to an injection site** (F3 residual mitigation). Owned by time-axis as v2 candidate.
- **`spawns_when:` manifest field** for non-coordinator roles (role-axis §3 Content Move B). Out-of-v1.
- **`propose_prompt_edit` MCP tool** (recurring per-phase review-and-suggest). Out-of-v1; lightweight per-phase feedback is the v1 mechanism (role-axis §4b).
- **`segments/` Python package**. Rejected per Skeptic shape constraint; v1 ships single-file renderers.
- **Constraints `enabled: false` opt-out**. Rejected per R-comp-3 / R2 (§3.1).
- **Per-rule include/exclude in constraints settings**. Existing `disabled_ids` is the source.

---

## 10. Verification checklist

- [ ] Law parity (T1/T2/T4): captured fixtures byte-match new orchestrator output when all gates True. The concatenated `constraints_stable + constraints_phase` slices must equal the today-monolithic `## Constraints` block byte-for-byte (omit_heading rule, §1.7).
- [ ] Phase-advance delta shape (T3): new fixture asserts the phase-advance prompt at T3 contains the phase-scoped slice ONLY, with its own `## Constraints` heading; no global rules from `constraints_stable` leak into the T3 phase-advance.
- [ ] Slice-split keystone invariant: for every `(role, phase)` pair under project_team, `assemble_constraints_block(..., slice="stable") + assemble_constraints_block(..., slice="phase", omit_heading=True) == assemble_constraints_block(..., slice=None)` byte-for-byte.
- [ ] F8 closed: default-roled agent at T1 / T3 receives non-None prompt containing constraints when global rules apply (T1: both slices; T3: constraints_phase).
- [ ] F9 closed: empty-digest agent at any site receives no `## Constraints` placeholder; the segment is dropped.
- [ ] F4 invariant: keystone test (binding) passes; no parallel rule-reading path admitted.
- [ ] R-comp-7: 8 of 9 bundled workflows render byte-identical launch prompts (D1=A2) or byte-identical-when-disabled (D1=A1).
- [ ] R3: 22 cataloged authority quotes byte-identical between pre-change and post-change `identity.md` (this spec touches no role file content).
- [ ] Per-segment purity: each `_render_<p>(ctx)` is deterministic and reads only its named source.
- [ ] Place / Time seam: `render_<p>(ctx)` produces same bytes at T1, T2, T4 (the three full-prompt sites) for the same `(role, phase, workflow)`.
- [ ] #28 scope semantics (BYPASS): `scope.sites = []` raises `ConfigValidationError` at config-load time (typo guard, NOT a structural floor). `scope.sites` omitting T3 results in agents NOT receiving the constraints delta at phase-advance -- documented user choice, no engine override (SPEC_bypass.md §3.10). Test asserts the omission-at-T3 outcome is observable, not silently overridden.
- [ ] Environment minimum content: `_render_environment(ctx)` produces the §2.4.1 template with all 6 tokens substituted from engine state, and (when active workflow is project_team) appends the §2.4.2 overlay verbatim.
- [ ] Name routing closure: `${NAME_ROUTING_TABLE}` resolves to a populated table from `agent_manager.agents`; the row `(coordinator -> claudechic)` (or whatever the main agent's name is) is present.

---

*End of spec_place_axis.md. Word count target: <800 lines. Operational only; rationale lives in `SPEC_APPENDIX.md`.*
