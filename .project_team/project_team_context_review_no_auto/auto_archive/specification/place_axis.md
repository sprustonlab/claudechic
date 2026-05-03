# Spec -- Place Axis

**Axis:** prompt segment -- *what* is delivered. Peer to time, role, gating, source.

## 1. Canonical segment list

Four first-class prompt segments, each independently gateable per `inject(time, place, role) -> bytes-or-empty`.

| segment | source | assembly entry point | current | target |
|---------|--------|----------------------|---------|--------|
| identity | `defaults/workflows/<wf>/<role>/identity.md` | `_assemble_agent_prompt` | concatenated to phase via `f"{identity}\n\n---\n\n{phase}"` | independent; gateable per `(time, role, phase)` |
| phase | `defaults/workflows/<wf>/<role>/<phase>.md` | `_assemble_agent_prompt` | concatenated to identity | independent |
| constraints | rules + advance-checks digests | `assemble_constraints_block` | live, scoped by `(role, phase, workflow, disabled_ids)` per F4/F5 | format-only configurability (§4) |
| environment | NEW: `claudechic/defaults/environment/*.md` | NEW: `assemble_environment_segment` | latent -- only via host-side `awareness_install.py`; not in `assemble_agent_prompt` | first-class peer; default-on at spawn |

## 2. Identity / phase split

Today `_assemble_agent_prompt` returns one concatenated string. Split into per-segment private renderers, **co-located in `claudechic/workflows/agent_folders.py`** (Skeptic via Coordinator: no new module, no class hierarchy):

- `_render_identity(ctx) -> str` (`""` when no role dir; F8/F9)
- `_render_phase(ctx) -> str` (`""` when no `<role>/<phase>.md`)
- `_render_constraints(ctx) -> str` (wraps existing `assemble_constraints_block`)
- `_render_environment(ctx) -> str` (Tier-2 status pending composability §2.2 vs lead-message reconciliation; if v1, returns `""` when workflow not opted in)

`assemble_agent_prompt(...)` becomes a thin orchestrator that calls `gate(time, place, role, phase, settings, manifest)` (gating §1) per segment, runs the renderer when gate is True, and joins non-empty results with `\n\n---\n\n`. Empty bytes are the gating signal -- no placeholders (F9 fix). All five callers route through the composer. Retain `assemble_phase_prompt` as a wrapper for one release.

## 3. Environment segment decision

**First-class peer. Mechanism global; activation per-workflow YAML opt-in. project_team opts in for v1** (Q1 working default = global opt-in). Honors user requirement #2 at the *mechanism* level + v4's project_team focus at the *activation* level.

**Burden of proof (skeptic: "no F-number names environment").** Conceded -- forward user requirement, not backward F-fix. Three enablements beyond convenience:

1. **Runtime/workflow-aware content host-side rules can't deliver.** `awareness_install.py` writes static markdown; cannot embed peer roster, workflow id, team-dynamics framing. UserAlignment §3 (team dynamics) requires per-spawn runtime content.
2. **Post-compact parity.** `/compact` strips SDK context; without env in the post-compact bundle, agents lose claudechic-runtime knowledge each compact (F3-adjacent).
3. **Default-roled / non-workflow spawns** (Q5/F8).

**Cost:** 2 new parts -- bundle dir `claudechic/defaults/environment/` + `render_environment(...)` (~20 LOC, pure). Opt-in by workflow YAML; non-opted workflows stay dormant at zero runtime cost.

**Carries:** claudechic-runtime facts, MCP introspection tools, comms patterns, runtime substitutions (workflow id, peer roster, cwd). **Excludes:** phase logic, role authority, project state, history (preserves Skeptic R3).

**Activation surface.** Workflow YAML field `environment_segment: enabled` (default `false`); v1 sets it true on `project_team` only. Opt-in check lives in `render_environment` (returns `""` when not opted in) -- consistent with gating's "emptiness is the renderer's decision." Gate stays default-True for env at all sites; `disabled_ids: global:environment-segment` always wins.

## 4. Constraints segment configurability (Q4)

**Format-only, no opt-out** (F4/F5/F7 + skeptic R2). Settings: `constraints.format` (`table` default | `compact` | `headings`); `constraints.include_advance_checks` (bool, default true); `constraints.include_skipped` (bool, default false). Per-rule scope opt-out lives in `disabled_ids` (existing).

## 5. Default-roled-agent injection (Q5)

**Every agent receives constraints; env follows workflow opt-in.** F8 closure: `assemble_agent_prompt` already returns constraints alone when phase_prompt is `None`; codify. Under opted-in workflow: id/phase empty, constraints + env present. No active workflow: env absent (host-side `claudechic_*.md` rules cover).

## 6. Per-segment invariants

Each renderer guarantees: **self-contained** (no cross-segment reads); **pure** of inputs (no globals); **empty-as-skip** (`""` is the gating signal; composer drops the separator; F9 fix); **single source** (identity -> `identity.md`; phase -> `<phase>.md`; constraints -> digests; structurally prevents F4); **stable separator** `\n\n---\n\n`; **idempotent** (deterministic in inputs); **inline `${VAR}` substitution preserved** (`${CLAUDECHIC_ARTIFACT_DIR}`, `${WORKFLOW_ROOT}`) for identity + phase content across all 9 bundled workflows -- R-comp-7 / Skeptic R5.

### 6.1 Per-segment freshness contract (composability §2.5, owned here)

| segment | source | freshness contract |
|---------|--------|--------------------|
| identity | bundled `<role>/identity.md` | spawn-time freeze (file-mtime per process) |
| phase | bundled `<role>/<phase>.md` | per-injection-site read (file-mtime) |
| constraints | computed digest over `LoadResult` | per-call live |
| environment (if v1) | runtime substitution from engine state (opt-in workflows) | per-engine-state-change |

F3 (three-coexisting-freshness-contracts) lives in this table, not on a separate axis. Unifying on per-call live for all places with a recompute path is recommended for v2 (Skeptic R4); v1 preserves the table as documented to avoid behavior change in non-opted workflows.

## 7. Coordination notes

- **time_axis:** identity/phase split lets time suppress identity at broadcast without F1 regression. Per-site sets (env conditional on opt-in): spawn / activation / post-compact = id+phase+con(+env); phase-advance(main) = phase+con; broadcast(typed) = phase+con; broadcast(standing-by) = con only.
- **gating_axis:** place owns the four `render_<place>` renderers + segment enum; gating owns the `gate(...)` predicate. F9 fix at the renderer seam (empty bytes, no placeholder). Place owns the YAML diffs for both the project_team `gating: suppress: [...]` standing-by matrix (per gating §3.1 schema, §5 entries) and the `environment_segment: enabled` flag.
- **role_axis:** per-role audit consumes the four-segment list.
- **terminology:** segment names verbatim per leadership glossary.

---

## Appendix candidates (rationale)

- Why split identity from phase: F8/F9 -- standing-by suppression of identity without losing phase context is impossible while concatenated.
- Why environment promotion now: user requirement #2 + closes the gap that `awareness_install.py` covers only host-side `~/.claude/rules/`, not subagent in-prompt injection.
- Why no constraints opt-out: F4/F5/F7 regression vector; per-rule `disabled_ids` is the supported opt-out path.
- Why default-roled agents get constraints: F8 closure; SPEC §D parity.
