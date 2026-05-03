# Terminology -- project_team_context_review (Specification)

**Status:** v1, Specification phase. Canonical home for every term used by
SPEC.md, the three axis specs, the gating-predicate spec, the
failure-mode map, and the per-role prompt audits.

**One name, one meaning, one home.** Other Specification documents
**reference** entries here; they do not redefine.

**v1 architecture (FULLY LOCKED post Q-T1 / Q-T2 / Q-T3):**

- **3 delivery axes:** Time, Place, Role.
- **4 places in v1:** identity, phase, constraints, **environment**.
  Environment is activated **per-workflow** via a YAML opt-in field
  (`environment_segment: enabled`, default `false`). project_team is
  the sole v1 opt-in; the other 8 bundled workflows stay byte-identical
  to today.
- **Crystal:** 5 (times) x 4 (places) x 16 (roles: 15 typed +
  `default`) = **320 cells**.
- **2 control-surface specs (NOT axes):** `gate` (inject-predicate
  config surface, `spec_gating.md`), `per-segment freshness`
  (segment-vs-freshness table inside `spec_place.md`).
- **`source` is not an axis** -- it is a property of each segment
  (table in `spec_place.md`).
- **`inline substitution`** stays first-class as the renderer property
  for `${VAR}` tokens *inside* identity / phase content. Coexists with
  `environment segment` at different grain.

---

## 1. Glossary (canonical names)

### 1.1 Vision-frame terms (from userprompt.md, approved v4)

| Term | Canonical definition | Notes / status |
|------|----------------------|----------------|
| **Time** | The lifecycle moment when context is delivered to an agent. Vision-frame name for the dimension whose values are the **injection sites** (see 1.2). | Use **Time** in axis-level prose; use **injection site** when naming a specific value. |
| **Place** | The named section of the launch prompt carrying delivered context. Vision-frame name for the dimension whose values are the **prompt segments** (see 1.2). | Use **Place** in axis-level prose; use **prompt segment** when naming a specific value. |
| **Role** | The `agent_type` value identifying which `project_team` agent receives context. 15 project_team role folders + `default`. | Field name stays `agent_type`; prose says **role**; folder is `<role>/`. |
| **Failure mode** | An observed pattern from a past `project_team` run where missing, late, redundant, or misplaced context degraded team dynamics. Tracked in `failure_mode_map.md` as F1..Fn. | "Fn" is the canonical short reference (e.g. F1, F8). |
| **Bundled prompt content** | All `identity.md` + `<phase>.md` files shipped under `claudechic/defaults/workflows/project_team/`. | Distinct from engine-injected content (constraints, environment). |

### 1.2 Mechanism terms (delivery surface)

| Term | Canonical definition | Replaces |
|------|----------------------|----------|
| **injection site** | A code location that calls `assemble_agent_prompt(...)` to deliver context to an agent. Five exist: (1) main-agent activation, (2) sub-agent spawn, (3) main-agent phase-advance, (4) sub-agent phase-advance broadcast, (5) post-compact. | "D5 inject site", "inject site", "prompt-injection site" |
| **prompt segment** | A named section of an agent's launch prompt. **v1 named values:** **identity segment**, **phase segment**, **constraints segment**, **environment segment**. | ad-hoc "block", "section", "header" |
| **identity segment** | Content of `<role>/identity.md`. Stable across phases. Carries role authority statements. Source: bundled markdown (with inline substitution). | "identity", "identity.md" (filename-only) |
| **phase segment** | Content of `<role>/<phase>.md`. Phase-scoped instructions. Source: bundled markdown (with inline substitution). | "phase prompt", "phase context", "phase markdown", "phase.md content" |
| **constraints segment** | The `## Constraints` markdown rendered by `assemble_constraints_block`, listing role+phase scoped rules and advance-checks. Source: computed digest. | "## Constraints block", "constraints block" |
| **environment segment** | Standalone prompt segment carrying claudechic-environment knowledge as its own header block. **Source: per-workflow YAML opt-in via `environment_segment: enabled` (default `false`).** v1 opt-in: `project_team` only; the other 8 bundled workflows do not render the segment (byte-identical to today). Source content: `claudechic/defaults/environment/*.md` (new); assembler: `assemble_environment_segment`. **Distinct from `inline substitution`** -- different grain (header block vs renderer property). | (new) |
| **inline substitution** | The bundled-markdown rendering pipeline that resolves `${CLAUDECHIC_ARTIFACT_DIR}`, `${WORKFLOW_ROOT}`, and similar tokens *inside* identity / phase content at injection time. **Property of the renderer, not a segment.** Coexists with `environment segment` at different grain. Must keep working in all 9 bundled workflows (Skeptic R5). | (new) -- previously unnamed |
| **launch prompt** | The full assembled artifact handed to an agent at an injection site: identity + phase + constraints + environment (segments that apply, after gate evaluation). | "system prompt" (reserve for SDK term), "agent prompt" |
| **inject predicate** | The pure function `inject(t, p, r) = render(p, ctx(t, r)) if gate(t, p, r) else EMPTY`. The compositional law over the 5 x 4 x 16 = 320 cells. | "the rule", "the gate", "filter" |
| **gate** | The pure predicate `gate(t, p, r) -> bool` parameterised by config (phase YAML for #27, settings.yaml for #28, runtime standing-by detect). **Property of the inject predicate, NOT an axis.** Owns its own spec (`spec_gating.md`) -- it is a real design problem (predicate signature, config schemas, default behavior table). | "the gating axis", "the toggle" |

### 1.3 Engine / scoping terms

| Term | Canonical definition | Notes |
|------|----------------------|-------|
| **scoping** | The static filter that decides whether a rule, hint, or segment applies, based on `(role, phase, workflow)`. | "applies to", "scoped to", "filtered by" -> scoping |
| **per-segment freshness** | Per-segment table mapping each prompt segment to one freshness contract: (a) **spawn-time freeze** -- frozen at spawn; (b) **per-call live** -- recomputed per MCP call; (c) **post-compact refresh** -- re-injected after `/compact`. **Owned by `spec_place.md`. NOT an axis.** | F3 in failure-mode map. Replaces the earlier "freshness contract" framing. |
| **standing-by agent** | A spawned agent whose role has **no `<role>/<phase>.md`** for the current phase. Alive, addressable, but not actively driving the phase. **Static definition, v1.** | Issue #27's target population. Distinct from **broadcast recipient** (1.4). |
| **broadcast recipient** | An agent that receives a phase-advance message via the sub-agent phase-advance broadcast injection site, regardless of whether it is standing-by. | Disambiguates from "standing-by" -- per Skeptic R1 / F1 these are independent states. |

### 1.4 Role / agent terms

| Term | Canonical definition |
|------|----------------------|
| **main agent** | The `claudechic` agent. Holds the workflow engine. `agent_type = main_role` (e.g. `coordinator`) when a workflow is active; `default` otherwise. |
| **sub-agent** | Any agent created via `mcp__chic__spawn_agent`. May be **typed** (an explicit `type=<role>`) or **default-roled** (no `type`). |
| **typed sub-agent** | A sub-agent with a non-default `agent_type` matching a `<role>/` folder under the active workflow. |
| **default-roled agent** | An agent with `agent_type = "default"`. May still receive global-namespace constraints; receives no identity/phase segments. |
| **axis-agent** | A sub-agent spawned during Specification to author a single delivery-axis spec (`spec_time.md`, `spec_place.md`, `spec_role.md`) or the gating-predicate spec (`spec_gating.md`). Process-level term, not an engine concept. |
| **role-agent** | A sub-agent spawned to review the bundled prompt content for one of the 15 project_team roles, satisfying user-protected priority #3 ("agents review and suggest the content of injections"). Output lands as one section in the consolidated `prompt_audit.md` (per Skeptic's structural decision; see §8 adoption protocol). |

### 1.5 Process / governance terms

| Term | Canonical definition |
|------|----------------------|
| **Leadership** | The four-agent set: Composability, TerminologyGuardian, Skeptic, UserAlignment. Canonical home: `coordinator/identity.md:62`. Other files reference, do not redefine. |
| **drift watch-list** | UserAlignment's enumerated set of vision-deviation patterns to flag during Specification. Owned by UserAlignment; cited by F-number-style references. |
| **user-protected priority** | A requirement the user explicitly asked for; UserAlignment guards. Numbered #1..#5 in `leadership_findings.md`. |
| **compositional law** | Composability's term: the minimal shared protocol that makes combinations work by construction. For this project: `inject(t, p, r) = render(p, ctx(t, r)) if gate(t, p, r) else EMPTY`. See `composability/identity.md`. |
| **F-number** | Short reference for a failure mode in `failure_mode_map.md` (F1..F9 currently). |
| **Q-number** | Short reference for a hard question in `leadership_findings.md` (Q1..Q8). |

### 1.6 Open and locked decisions

#### Open: place enumeration (Q-T3)

**Status:** OPEN. Coordinator is presenting both positions to the user
at the Spec checkpoint. Do not collapse on glossary authority.

| Position | Segment set | Mechanism for claudechic-environment knowledge | Crystal cells | Source |
|----------|-------------|-----------------------------------------------|---------------|--------|
| **3-place (Composability proposal)** | identity, phase, constraints | **inline substitution** -- `${VAR}` tokens inside identity / phase content; rendered by the bundled-markdown pipeline. No standalone environment block. | 5 x 3 x 15 = **225** | Composability revision note. |
| **4-place (axis-agent specs)** | identity, phase, constraints, **environment** | **environment segment** as a first-class peer -- a standalone header block injected default-on at injection sites T1 (main-agent activation), T2 (sub-agent spawn), T5 (post-compact). The predicate enumerates 4 places. | 5 x 4 x 15 = **300** | `spec_time.md`, `spec_place.md`, `spec_gating.md` -- already drafted. |

Both terms are kept as defined glossary entries (1.2) so neither
position requires a glossary edit to be writable. **TerminologyGuardian
will not instruct axis-agents to revise** -- the user adjudicates.

#### Locked (not in dispute)

| Term | Status | Rationale |
|------|--------|-----------|
| **source as an axis** | **Not an axis.** Each segment has a fixed source (identity / phase = bundled markdown; constraints = computed digest; environment, if adopted = runtime substitution). Source is a *property of the segment*, documented in the segment-source table inside `spec_place.md`. | Composability decision (Q-T1). |
| **gating as an axis** | **Not an axis.** Gating values (`always`, per-phase suppress, per-setting toggle, standing-by) are *kinds of config*, not coordinates in the crystal. The `gate` is a pure predicate parameterised by config (1.2). It still has its own spec (`spec_gating.md`); it is not a delivery axis. | Composability decision (Q-T2). |

---

## 2. Disambiguation (overloaded terms)

These terms appear in multiple Specification documents with different
meanings. **Always qualify** when used in Specification prose.

### 2.1 "context"

Three distinct senses in active use:

| Sense | Canonical phrase | Where it appears |
|-------|------------------|------------------|
| Information delivered to an agent (vision sense) | **delivered context** | userprompt.md, leadership_findings.md, every axis spec |
| The Claude token window | **context window** | engine code, F3 discussions |
| The hook callback parameter | **`ctx` parameter** | `agent_folders.create_post_compact_hook` and similar |

> **Rule:** In Specification prose, "context" alone is ambiguous and
> should be avoided. Prefer **delivered context** unless the token
> window is meant.

### 2.2 "phase"

| Sense | Canonical phrase |
|-------|------------------|
| Engine state (the `Phase` dataclass, e.g. `specification`) | **phase** (or `Phase` when referring to the dataclass) |
| The markdown file `<role>/<phase>.md` | **phase segment** (prose) / `<phase>.md` (filename) |
| The lifecycle moment of advancing | **phase advance** |

### 2.3 "axis"

| Sense | Canonical phrase | Notes |
|-------|------------------|-------|
| Composability vocabulary -- an independent dimension of a software design (Crystal/Seam framework) | **composability axis** when disambiguation needed; otherwise **axis** in `composability/identity.md` context | Defined in `composability/identity.md` |
| This Specification's **3-axis** decomposition (Time, Place, Role) | **delivery axis** when disambiguation needed; otherwise **axis** in this Specification's context | Composability ratified post-Q-T1/Q-T2: source and gating are NOT axes. Crystal cell count depends on the open Q-T3 decision (225 under 3-place, 300 under 4-place). |

> **Rule:** Within `spec_time.md` / `spec_place.md` / `spec_role.md`
> the unqualified word **axis** refers to the delivery axis. SPEC.md
> should disambiguate on first use. `spec_gating.md` is **not** an
> axis spec -- it specifies the gating predicate / control surface.

### 2.4 "broadcast"

| Sense | Canonical phrase |
|-------|------------------|
| Sub-agent phase-advance broadcast (injection site #4) | **phase-advance broadcast** |
| Generic "send to many" usage | avoid; rephrase. |

### 2.5 "identity"

| Sense | Canonical phrase |
|-------|------------------|
| The segment / content from `identity.md` | **identity segment** |
| The role authority concept ("who is this agent") | **role authority** (per Skeptic R3) |
| The file | `identity.md` |

### 2.6 "injection"

| Sense | Canonical phrase |
|-------|------------------|
| A specific delivery moment | **injection site** |
| The act of delivering content | **injection** (verb-noun, fine in context) |
| What is delivered | **delivered context** (see 2.1) |

---

## 3. Synonyms found across Leadership artifacts (collapse required)

Searched: `leadership_findings.md`, all four Leadership replies as
referenced, `userprompt.md`, `claudechic/workflows/agent_folders.py`,
`claudechic/app.py`, `claudechic/mcp.py`,
`claudechic/context/workflows-system.md`,
`claudechic/defaults/workflows/project_team/*/identity.md`.

| Synonym set | Canonical | Locations to update during Specification |
|-------------|-----------|-------------------------------------------|
| "phase prompt" / "phase context" / "phase markdown" / "phase.md content" | **phase segment** (prose) | `agent_folders.py:5,42,265,329,355,374`; `app.py:1037,1125,2160,2400,2427,2441`; `mcp.py:943,972,985,1045`. Function name `assemble_phase_prompt` may stay (engine API). |
| "D5 inject site" / "inject site" / "prompt-injection site" / "five inject sites" | **injection site** | `agent_folders.py:10,146,263,316,331`; `app.py:1775,2120,2123,2376,2379`; `mcp.py:280,282,986,990,1344,1442,1503,1518`; `context/workflows-system.md:56`. Drop "D5" prefix. |
| "launch prompt" / "system prompt" / "agent prompt" | **launch prompt** for the assembled artifact; reserve **system prompt** for the SDK literal term. | `agent_folders.py:11,266`; `app.py` various. |
| "role" / "agent_type" / "role folder" | prose: **role**; field name: `agent_type`; folder: `<role>/`. | Universal. |
| "applies to" / "scoped to" / "filtered by" | **scoping** / "scoped to" | leadership_findings.md, axis specs. |
| "the gate" / "the rule" / "the filter" (when referring to the inject predicate) | **inject predicate** (whole) / **gate** (the predicate inside it) | leadership_findings.md §"Compositional law". |
| "gating axis" / "gating dimension" | **gate** (predicate); **NOT an axis** | Composability Q-T2. |
| "source axis" / "source dimension" | drop; segment-source table only (in `spec_place.md`) | Composability Q-T1. |
| "environment" used unqualified | one of: **inline substitution** (renderer mechanism) or **environment segment** (the standalone block). Whether the latter is v1 is OPEN. | Q-T3 OPEN. |
| "freshness contract" used as an axis | **per-segment freshness** -- table in `spec_place.md`, NOT an axis | Composability Q-T1 follow-on. |
| "F1..F9" vs "Failure mode 1..9" vs "the broadcast bug" | **Fn** (e.g. F1) for short-form; **failure mode Fn** in first use | Specification artifacts. |

---

## 4. Orphan / undefined terms (require definition or removal)

| Term | Where used | Status / fix |
|------|-----------|--------------|
| **"D5"** | Throughout `agent_folders.py`, `app.py`, `mcp.py` | Slot-tracking artifact from prior cycle, defined nowhere a newcomer can find. **Drop the prefix everywhere.** |
| **"slot 3" / "slot 4"** | `agent_folders.py:146,338,339` | Same -- internal milestone references opaque to readers. **Drop or replace with a stable reference.** |
| **"post-compact"** | Used as adjective without glossary entry | **Defined here:** *the SDK lifecycle moment after `/compact` rebuilds the conversation; the post-compact hook re-runs `assemble_agent_prompt` and re-delivers the launch prompt.* |
| **"freshness contract"** | New term introduced by Skeptic F3 | **Reframed as `per-segment freshness` in 1.3** -- a table mapping each segment to one of three contracts (spawn-time freeze / per-call live / post-compact refresh), owned by `spec_place.md`. NOT an axis. |
| **"claudechic-environment"** | UserAlignment user-protected priority #2 | Currently undefined. **Open question Q1** -- scope (global vs project_team-only) is unresolved; semantic content (what facts compose claudechic-environment?) is also undefined. **Specification must pin both.** Pending: ask user. |
| **"agents review and suggest the content of injections at all phases"** | UserAlignment #3 | Mechanism undefined. **Open question Q2.** Specification must propose a concrete loop (who proposes, who decides, when). |
| **"main agent" / "sub-agent" / "typed sub-agent" / "default-roled agent"** | `mcp.py`, `app.py` throughout | **Defined in 1.4 above.** No canonical home before this document. |

---

## 5. Canonical-home violations to repair

| Term | Duplicated in | Canonical home | Action |
|------|---------------|----------------|--------|
| **"Leadership"** (the four-agent set) | `coordinator/identity.md:62` (canonical) + reiterated in `composability/identity.md:8`, `terminology/identity.md` (implicit) | `coordinator/identity.md:62` | Keep in coordinator; replace re-listings elsewhere with: *"See coordinator/identity.md for the Leadership roster."* |
| **Workflow phase list** (vision -> setup -> ... -> signoff) | `coordinator/identity.md:39-46` AND `project_team.yaml:4-67` | `project_team.yaml` (machine source of truth) | **Q7:** deduplicate against engine, or keep informational copy? Specification must decide. If kept, mark coordinator's copy as "informational mirror". |
| **Composability vocabulary** (Crystal, Seam, Algebraic) | `composability/identity.md` (canonical) | Same. No duplication observed. | OK. |
| **TerminologyGuardian rules** | `terminology/identity.md` (canonical) | Same. | OK. |

---

## 6. Newcomer simulation

I read the Leadership artifacts and bundled prompt content as if I had
never seen the project. Blockers a newcomer hits:

1. **`agent_folders.py:146`** -- "the five D5 inject sites" -- "D5" is
   undefined. Newcomer cannot anchor what "D5" denotes. -> **Drop "D5".**
2. **`agent_folders.py:339`** -- "slot 4 attaches the loader to the
   engine" -- "slot 4" is opaque. -> **Drop or replace with stable name.**
3. **`leadership_findings.md` headline** -- "every (time, place, role)
   cell of the prompt-assembly matrix fires unconditionally" assumes the
   reader already knows there is a matrix. -> SPEC.md should **introduce
   the matrix concept on first use** with a small ASCII grid example.
4. **"standing-by agent"** -- the term is used three different ways
   across the four Leadership replies. The static definition in 1.3
   resolves this, but **Specification authors must cite the glossary on
   first use of the term.**
5. **"axis"** -- without disambiguation, a newcomer reading
   `composability/identity.md` then `spec_time_axis.md` sees the same
   word for two different things. -> **Apply rule in 2.3.**
6. **"context"** -- the most overloaded term. A newcomer reading "the
   agent has wrong context" cannot tell which sense is meant. -> **Apply
   rule in 2.1: prefer "delivered context" or "context window".**
7. **"injection" vs "broadcast" vs "delivery"** -- in Skeptic's F1,
   "broadcast" is the failing site; in 1.2, "broadcast" is one of five
   injection sites. The relationship is currently implicit. -> SPEC.md
   should state explicitly: *every broadcast is an injection; not every
   injection is a broadcast.*

---

## 7. Composability decisions (Q-T1 / Q-T2 LOCKED; Q-T3 OPEN)

Q-T1 and Q-T2 are settled and drive the canonical glossary above. Q-T3
was provisionally locked but has been **reopened by the Coordinator**:
three axis specs already adopted the 4-place position before
Composability's revision arrived, and the Coordinator is escalating
both positions to the user for adjudication at the Spec checkpoint.
TerminologyGuardian holds both terms (`environment segment`,
`inline substitution`) as defined entries until the user decides.

| ID | Question | Status | Effect on glossary |
|----|----------|--------|-------------------|
| Q-T1 | Is `source` a delivery axis? | **LOCKED -- No.** Each segment has a fixed source (identity / phase = bundled markdown; constraints = computed digest). Source is a *property of the segment*. | `source` removed from axis list. Segment-source table lives in `spec_place.md`. "freshness contract" reframed as `per-segment freshness` table. |
| Q-T2 | Is `gating` a delivery axis? | **LOCKED -- No.** Gating values are *kinds of config*, not coordinates. The `gate` is a pure predicate parameterised by config. | `gating` (as an axis) removed; `gate` (as a predicate) added. `spec_gating.md` survives as a control-surface spec, not an axis spec. |
| Q-T3 | Promote `environment segment` to first-class v1 peer? | **OPEN -- user adjudicates.** Two positions on the table: 3-place (Composability proposal) with `inline substitution` as the v1 mechanism; 4-place (axis-agent specs) with `environment segment` as a first-class peer. | Both terms kept as defined glossary entries. v1 segment count is recorded as OPEN in §1.2 / §1.6. No axis-agent revision instructed on glossary authority. |

Net effect (locked portion): **3 delivery axes** (Time, Place, Role);
**2 control-surface specs** (`spec_gating.md`, per-segment freshness
inside `spec_place.md`). Net effect (open portion): place count and
crystal cell count depend on Q-T3 -- 3 places / 225 cells, or 4 places
/ 300 cells.

---

## 8. Adoption protocol

1. Every axis spec (`spec_time.md`, `spec_place.md`, `spec_role.md`)
   AND `spec_gating.md` MUST cite this file on first use of any term
   in section 1.
2. SPEC.md links to this file as the canonical glossary. SPEC.md does
   **not** redefine terms in section 1.
3. New terms introduced during Specification land here first, then the
   axis specs reference them. **No term is canon until it appears in
   this file.**
4. **Per-role prompt audits** -- canonical artifact shape per Skeptic:
   a single `prompt_audit.md` with one section per role (15 + default).
   Earlier draft used `prompt_audit/<role>.md` (15 files); that shape
   exists on disk during the in-flight transition. When the role-axis
   author consolidates, the canonical reference is `prompt_audit.md
   §<role>` (e.g. `prompt_audit.md §coordinator`). Audits inherit the
   glossary; role-specific terms land in this file under a new "1.7
   Role-specific" subsection rather than in the audit file itself.
5. Term-drift detected during axis-spec review will be reported by
   TerminologyGuardian to the authoring agent and to `claudechic`
   (coordinator).

---

*Author: TerminologyGuardian. Specification phase v1.*
