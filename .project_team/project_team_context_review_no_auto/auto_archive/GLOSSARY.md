# GLOSSARY -- project_team_context_review

One-page canonical reference. Every Specification document (`SPEC.md`,
`spec_time.md`, `spec_place.md`, `spec_role.md`, `spec_gating.md`,
`prompt_audit.md`) cites this file on first use of any listed term.
The deeper rationale lives in `specification/terminology.md`.

**One name, one meaning, one home.** Do not redefine these terms
elsewhere; reference this file.

**v1 architecture (LOCKED post Q-T1 / Q-T2 / Q-T3):**

- **3 delivery axes:** Time, Place, Role.
- **4 places in v1:** identity, phase, constraints, **environment**.
  Environment is activated **per-workflow** via a YAML opt-in field
  (`environment_segment: enabled`, default `false`). project_team is
  the sole v1 opt-in; the other 8 bundled workflows stay byte-identical
  to today.
- **Crystal:** 5 (times) x 4 (places) x 16 (roles: 15 typed +
  `default`) = **320 cells**.
- **2 control-surface specs (NOT axes):** the **gate** predicate
  (`spec_gating.md`), per-segment freshness (table inside
  `spec_place.md`).
- **`source` is not an axis** -- it is a property of each segment
  (table in `spec_place.md`).
- **`inline substitution`** stays first-class as the renderer property
  for `${VAR}` tokens *inside* identity / phase content. Distinct from
  `environment segment` (header block).

---

## Canonical terms

| Term | Canonical definition | Replaces / supersedes |
|------|----------------------|----------------------|
| **injection site** | A code location that calls `assemble_agent_prompt(...)` to deliver context to an agent. Five exist: (1) main-agent activation, (2) sub-agent spawn, (3) main-agent phase-advance, (4) sub-agent phase-advance broadcast, (5) post-compact. Vision name: **Time**. | "D5 inject site", "inject site", "prompt-injection site" |
| **prompt segment** | A named section of an agent's launch prompt. **v1 named values:** **identity segment**, **phase segment**, **constraints segment**, **environment segment**. Vision name: **Place**. | ad-hoc "block", "section", "header" |
| **identity segment** | Content of `<role>/identity.md`. Stable across phases. Carries role authority. Source: bundled markdown (with inline substitution). | "identity", "identity.md" (filename-only) |
| **phase segment** | Content of `<role>/<phase>.md`. Phase-scoped instructions. Source: bundled markdown (with inline substitution). | "phase prompt", "phase context", "phase markdown", "phase.md content" |
| **constraints segment** | The `## Constraints` markdown rendered by `assemble_constraints_block`, listing role+phase scoped rules and advance-checks. Source: computed digest. | "## Constraints block", "constraints block" |
| **environment segment** | Standalone prompt segment carrying claudechic-environment knowledge as its own header block. **Source: per-workflow YAML opt-in via `environment_segment: enabled` (default `false`).** v1 opt-in: `project_team` only; non-opted workflows do not render the segment. Source content: `claudechic/defaults/environment/*.md` (new); assembler: `assemble_environment_segment`. Distinct from **inline substitution**. | (new) |
| **inline substitution** | The bundled-markdown rendering pipeline that resolves `${CLAUDECHIC_ARTIFACT_DIR}`, `${WORKFLOW_ROOT}`, and similar tokens *inside* identity / phase content at injection time. **Property of the renderer, not a segment.** Coexists with `environment segment` -- different grain (renderer-property vs header block). Must keep working in all 9 bundled workflows (Skeptic R5). | (new) -- previously unnamed |
| **launch prompt** | The full assembled artifact handed to an agent at an injection site: identity + phase + constraints + environment (segments that apply, after gate evaluation). | "system prompt" (reserve for the SDK term), "agent prompt" |
| **inject predicate** | The pure function `inject(t, p, r) = render(p, ctx(t, r)) if gate(t, p, r) else EMPTY`. The compositional law over the 5 x 4 x 16 = 320 cells. | "the rule", "the gate", "filter" |
| **gate** | The pure predicate `gate(t, p, r) -> bool` parameterised by config (phase YAML for #27, settings.yaml for #28, runtime standing-by detect). Property of the inject predicate. **NOT an axis.** Owns its own spec (`spec_gating.md`). | "the gating axis", "the toggle" |
| **role** | The `agent_type` value identifying which `project_team` agent receives context. **15 typed roles + `default` = 16 in the v1 crystal.** Vision name: **Role**. | prose: **role**; field name: `agent_type`; folder: `<role>/` |
| **scoping** | The static filter that decides whether a rule, hint, or segment applies, based on `(role, phase, workflow)`. Static counterpart to `gate` (which is configurable). | "applies to", "scoped to", "filtered by" |
| **per-segment freshness** | Per-segment table mapping each prompt segment to one freshness contract: (a) **spawn-time freeze**, (b) **per-call live**, (c) **post-compact refresh**. Owned by `spec_place.md`. **NOT an axis.** | "freshness contract", "F3 substrate" |
| **standing-by agent** | A spawned agent whose role has **no `<role>/<phase>.md`** for the current phase. Alive, addressable, but not actively driving the phase. **Static definition, v1.** Issue #27's target population. | (new) |
| **broadcast recipient** | An agent that receives a phase-advance message via injection site #4 (sub-agent phase-advance broadcast), regardless of whether it is standing-by. Distinct state from standing-by. | -- |
| **main agent** | The `claudechic` agent. Holds the workflow engine. `agent_type = main_role` (e.g. `coordinator`) when a workflow is active; `default` otherwise. | -- |
| **sub-agent** | Any agent created via `mcp__chic__spawn_agent`. May be **typed** (explicit `type=<role>`) or **default-roled** (no `type`). | -- |
| **typed sub-agent** | A sub-agent with a non-default `agent_type` matching a `<role>/` folder under the active workflow. | -- |
| **default-roled agent** | An agent with `agent_type = "default"`. Receives constraints (when global-namespace rules apply) and environment (when its workflow has opted in); receives no identity/phase segments. | -- |
| **failure mode (Fn)** | An observed pattern from a past `project_team` run where missing/late/redundant/misplaced context degraded team dynamics. Tracked F1..Fn in `failure_mode_map.md`. | -- |
| **bundled prompt content** | All `identity.md` + `<phase>.md` files shipped under `claudechic/defaults/workflows/project_team/`. Distinct from engine-injected segments (constraints, environment). | "agent folder content", "role dir" |
| **Leadership** | The four-agent set: Composability, TerminologyGuardian, Skeptic, UserAlignment. **Canonical home: `coordinator/identity.md:62`.** Other files reference, do not re-list. | -- |

---

## Locked decisions (Q-T1 / Q-T2 / Q-T3)

| ID | Decision | Effect |
|----|----------|--------|
| **Q-T1** | `source` is **not an axis** -- it is a property of each segment (identity / phase = bundled markdown; constraints = computed digest; environment = bundled markdown under `defaults/environment/`). Documented in the segment-source table inside `spec_place.md`. | Removes one would-be axis-spec file. |
| **Q-T2** | `gating` is **not an axis** -- the `gate` is a pure predicate parameterised by config. `spec_gating.md` survives as a control-surface spec, not an axis spec. | Predicate signature locked: `gate(t, p, r, phase, settings, manifest) -> bool`. |
| **Q-T3** | `environment segment` is **first-class v1 vocabulary**, activated per-workflow via YAML opt-in (`environment_segment: enabled`, default `false`). project_team opts in for v1; other 8 bundled workflows stay byte-identical to today. **inline substitution** also stays first-class for `${VAR}` resolution inside identity / phase content. | 4 places in v1 (5 x 4 x 16 = 320 cells). Earlier "Tier-2" framing dissolved -- mechanism graduated to v1 via opt-in. |

---

## Disambiguation (always qualify)

| Word | Senses | Canonical phrases |
|------|--------|-------------------|
| **context** | (a) information delivered to an agent; (b) Claude token window; (c) hook `ctx` parameter | (a) **delivered context**; (b) **context window**; (c) **`ctx` parameter** |
| **phase** | (a) engine state / `Phase` dataclass; (b) the `<phase>.md` file; (c) lifecycle moment | (a) **phase**; (b) **phase segment** / `<phase>.md`; (c) **phase advance** |
| **axis** | (a) Composability software-design axis (Crystal/Seam); (b) this Spec's 3-axis decomposition (Time/Place/Role) | (a) **composability axis**; (b) **delivery axis**. Within `spec_time.md` / `spec_place.md` / `spec_role.md`, unqualified "axis" = delivery axis. |
| **broadcast** | (a) injection site #4; (b) generic "send to many" | (a) **phase-advance broadcast**; (b) avoid -- rephrase |
| **identity** | (a) the segment / `identity.md` content; (b) role authority concept; (c) the file | (a) **identity segment**; (b) **role authority**; (c) `identity.md` |
| **injection** | (a) a specific delivery moment; (b) the act of delivering; (c) what is delivered | (a) **injection site**; (b) **injection** (verb-noun OK); (c) **delivered context** |
| **environment** | (a) inline `${VAR}` substitution within bundled markdown (renderer property); (b) the standalone segment (header block) | (a) **inline substitution**; (b) **environment segment**. Both first-class v1 vocabulary; different grain. Use the explicit phrase in either case; never just "environment". |

> Special note: every **broadcast** is an **injection**; not every
> injection is a broadcast.

---

## Synonyms to collapse

Each row: any of the synonyms appears in current artifacts -> use the canonical form everywhere going forward.

| Synonyms in use | Canonical |
|-----------------|-----------|
| "phase prompt" / "phase context" / "phase markdown" / "phase.md content" | **phase segment** |
| "D5 inject site" / "inject site" / "prompt-injection site" / "five inject sites" | **injection site** (drop "D5" prefix everywhere) |
| "launch prompt" / "system prompt" / "agent prompt" | **launch prompt** for the assembled artifact; reserve **system prompt** for the SDK term |
| "role" / "agent_type" / "role folder" | prose: **role**; field name: `agent_type`; folder: `<role>/` |
| "applies to" / "scoped to" / "filtered by" | **scoping** / "scoped to" |
| "the gate" / "the rule" / "the filter" (when referring to the inject predicate) | **inject predicate** (whole) / **gate** (the predicate inside it) |
| "gating axis" / "gating dimension" | **gate** (predicate) -- NOT an axis |
| "source axis" / "source dimension" | drop -- segment-source table only (in `spec_place.md`) |
| "environment" used unqualified | **inline substitution** (renderer property) OR **environment segment** (the standalone block). Both first-class v1; pick the right grain. |
| "Tier-2 environment segment" / "v2 environment" | drop -- environment segment graduated to v1 via opt-in (Q-T3 LOCKED) |
| "freshness contract" used as an axis | **per-segment freshness** -- table, NOT an axis |
| "F1..F9" / "Failure mode 1..9" / "the broadcast bug" | **Fn** (e.g. F1) short-form; **failure mode Fn** on first use |
| "context" used unqualified | one of: **delivered context**, **context window**, **`ctx` parameter** |
| "5-axis decomposition" (time/place/role/gating/source) | **3-axis decomposition** (Time/Place/Role) -- post Q-T1/Q-T2 |

Specific call-sites for code/doc updates are catalogued in
`specification/terminology.md` §3 (file:line references in
`agent_folders.py`, `app.py`, `mcp.py`,
`context/workflows-system.md`).

---

*Author: TerminologyGuardian. Specification phase v1. Q-T1 / Q-T2 / Q-T3
LOCKED. Q-T3 dissolved when place_axis revised to per-workflow YAML
opt-in (default false; project_team opts in for v1) -- the architectural
conflict between Composability's Tier-2 and the axis-agents' first-class
position no longer exists. Deeper rationale and file:line-level
mappings: `specification/terminology.md`.*
