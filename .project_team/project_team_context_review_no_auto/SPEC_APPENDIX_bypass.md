# SPEC_APPENDIX_bypass.md

Supplemental history for SPEC_bypass.md. Nothing here is required reading for
implementation. Contents moved from the spec to keep the spec implementer-actionable.

---

## Deferred to v2

**workflow_gate (§2).** A third gate layer (`workflow_gate`) was evaluated but dropped
from v1. v2 may add it if a workflow needs to suppress segments for active roles (roles
that have a `<role>/<phase>.md` but whose workflow author still wants identity omitted).

**Explicit YAML suppress schema (§3.6).** v2 may add a `gating: { suppress: [...] }`
YAML block to let workflow authors opt out of identity injection for specific roles
without relying on the file-absence predicate. That case does not exist in v1 project_team.

**F2 -- Late framing reveal (§4 row, moved from spec).** Failure mode: no injection
mechanism for "framing has shifted." Out of scope: runtime state required, breaks
predicate purity. v2 candidate injection site: `framing-reveal` -- would fire when the
coordinator signals a framing shift without a full phase advance.

**F3 freshness unification (§4).** v2 candidate: unify all four segments on a per-call
live freshness contract (eliminating the spawn-freeze vs per-call vs post-compact
divergence). Deferred in v1; substrate left unchanged; T5 post-compact is the canonical
refresh for now.

---

## Deliberation history

**D1. Environment segment activation.**
Per-workflow manifest field (`environment_segment: enabled`, default `false`). In
deliberation, the question was whether to make the segment always-on or opt-in. Outcome:
per-workflow YAML opt-in. project_team.yaml ships with `enabled: true`; other 8 bundled
workflows ship without the field. User-tier `environment_segment.enabled` overrides in
either direction.

**D2. "Agents review and suggest" mechanism.**
Two options were evaluated:

| Option | Description | Position |
|--------|-------------|----------|
| **a. One-shot (this run only)** | `prompt_audit/<role>.md` files are the deliverable; approved edits land in bundled content; no recurring mechanism. | skeptic |
| **b. Lightweight per-phase feedback (working default)** | Any role agent writes `<artifact_dir>/role_feedback/<role>_<phase>.md`. Coordinator reads at each phase advance; a per-phase YAML `advance_check` surfaces non-empty result as a triage trigger. No new MCP tool. Authority preservation applies to all proposals. | role_axis; user_alignment |

Outcome: option b (working default). See SPEC_bypass.md §5 step 17 for implementation.

**D3. Tutorial opt-in.**
Resolved as a consequence of D1: add `environment_segment: enabled: true` to
`tutorial.yaml` whenever desired -- no spec change required.

---

## Standing-by matrix

Illustrative role x phase matrix for project_team. The standing-by predicate (SPEC_bypass.md §3.8) computes each cell at runtime from file presence; no YAML entries are required or shipped. This table is not required reading for implementation.

`S` = standing-by for that phase (no `<role>/<phase>.md`; identity suppressed at broadcast).
`.` = active. `--` = not spawned. `**` = active after §3.4 phase.md files are added.

| role | vis | set | lead | spec | impl | tv | ts | ti | doc | sgn |
|------|-----|-----|------|------|------|----|----|----|-----|-----|
| coordinator | . | . | . | . | . | . | . | . | . | . |
| composability | S | S | S | . | . | S | . | . | S | S |
| terminology | S | S | S | . | S | S | . | S | S | S |
| skeptic | S | S | S | . | . | S | . | . | S | S |
| user_alignment | S | S | S | . | .** | S | . | . | S | S |
| researcher | S | S | S | S | S | S | S | S | S | S |
| implementer | S | S | S | S | . | S | S | . | S | S |
| test_engineer | S | S | S | S | S | S | .** | .** | S | S |
| ui_designer | S | S | S | .** | .** | S | S | S | S | S |
| project_integrator | S | S | S | S | S | S | S | S | S | S |
| sync_coordinator | S | S | S | S | S | S | S | S | S | S |
| lab_notebook | S | S | S | S | S | S | S | S | S | S |
| memory_layout | S | S | S | S | S | S | S | S | S | S |
| binary_portability | S | S | S | S | S | S | S | S | S | S |

`coordinator` is never suppressed (owns the workflow).

---

## Deliberation history

**D4. T3/T4 constraints scope (phase delta only).**
Globals and role-scoped rules are anchored at T1 (sub-agent spawn) and T2 (main
activation); they survive in transcript. T3 / T4 fire on every phase advance -- 10
advances across project_team's 10 phases means 10 redundant copies of the global block
per agent if T3 / T4 emit the full block. Emitting the phase delta only at T3 / T4
reflects the lifecycle moment's actual content shift. T5 restores the full block because
`/compact` strips transcript context. The operational outcome is captured in the §3.1
default segment table; this note explains the lifecycle reasoning behind the T3/T4 row.
