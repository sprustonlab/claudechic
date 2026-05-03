# Composability Specification -- project_team_context_review

**Author:** Composability lead.
**Status:** Draft for axis-agent expansion.
**Inputs:** `STATUS.md`, `userprompt.md`, `leadership_findings.md`, `abast_accf332_sync/*`, `claudechic/workflows/*`, `claudechic/defaults/workflows/project_team/*`, GitHub #27, #28.

This document is the architectural backbone for Specification. It locks the
axes, the compositional law, the seams, and the crystal-hole inventory. The
four axis-agents (time, place, role, gating) write deep specs against this
backbone; this document does not duplicate their work.

---

## 1. Domain restated

The workflow engine assembles each agent's system-level prompt from a small
set of *content pieces* and delivers it at a small set of *lifecycle moments*
to a small set of *recipient roles*. Today every (moment, content, role) cell
fires unconditionally. Issues #27 and #28 are two corners of the same
underlying problem: there is no expressive, configurable, role-aware control
surface over **what context arrives, where, and when**.

The user's frame is **time x place x role**. Composability adds two control
axes (**gating**, **source**) so that #27 and #28 have a structural home and
the resulting design is law-governed rather than special-cased.

---

## 2. The axes -- three coordinates + two control surfaces

**Revision note (post Terminology Q-T1/Q-T2/Q-T3 + place_axis opt-in
resolution):** the original draft enumerated 5 axes. After Terminology
challenge, the design collapses to **3 true coordinates** (time, place,
role) plus **2 control-surface design problems** (gating predicate,
per-segment freshness). `source` is a per-segment attribute, not a
coordinate. `gating` parameterises the inject predicate; it is a control
surface, not a coordinate.

**Q-T3 resolution (post-revision):** my original Tier-2 position on the
environment segment dissolved when place_axis proposed an **opt-in,
default-false, per-workflow YAML mechanism** (`environment_segment:
enabled`). The mechanism is first-class v1 (engine-level renderer + place
enum entry); only project_team opts in for v1. Skeptic R5 (other workflows
starve) is resolved by opt-in default-false: 8 of 9 bundled workflows see
zero behavior change. The crystal expands to **`5 x 4 x 16 = 320`** cells
(4 places: identity, phase, constraints, environment; 15 typed roles +
default).

Sections retain the original numbering for traceability; sec 2.4 and 2.5
are now control-surface specs, not axes.

### 2.1 Time -- *injection site*

The lifecycle moment at which a prompt is delivered to an agent.

Values:
1. `spawn` -- sub-agent creation (`mcp.spawn_agent`).
2. `activation` -- main-agent gains a workflow (`app._activate_workflow`).
3. `phase-advance-main` -- main agent transitions phase
   (`app._inject_phase_prompt_to_main_agent`).
4. `phase-advance-broadcast` -- sub-agents receive the new phase
   (`mcp._make_advance_phase` loop).
5. `post-compact` -- recovery after `/compact`
   (`agent_folders.create_post_compact_hook`).

Independence claim: each value corresponds to a distinct call site in the
engine and means a distinct intent (initial role assignment, role-already-
known refresh, recovery-after-context-loss). The set is **closed** -- new
times only enter if a new lifecycle moment is added to the SDK.

Open questions for the time-axis agent:
- Is a sixth time `pull` (agent calls an MCP tool to refresh) needed?
- Does failure mode F1 reveal that broadcast is *not yet* a real injection
  site (sub-agents missed the constraints block) -- i.e. is broadcast a
  one-value gap that must be closed before gating discussion?

### 2.2 Place -- *prompt segment*

The named content piece carried in a prompt.

Values (per terminology canon, v1, post Q-T3 opt-in resolution):
1. `identity segment` -- bundled `<role>/identity.md`.
2. `phase segment` -- bundled `<role>/<phase>.md`.
3. `constraints segment` -- live digest from `compute_digest` +
   `compute_advance_checks_digest`.
4. `environment segment` -- standalone header block carrying claudechic-
   environment knowledge. **Opt-in per-workflow** via the YAML field
   `environment_segment: enabled` (default `false`). Only project_team
   opts in for v1; other bundled workflows render byte-identical to today
   (Skeptic R5 closed by opt-in default-false). Distinct from `inline
   substitution`, which is a renderer property of identity/phase content
   and stays in v1 unchanged.

Independence claim: each segment has a distinct **purpose** (who-am-I,
what-now, what-bounds-me, where-am-I) and a distinct freshness contract.
They can be assembled, gated, and updated independently. Each segment also
has a **source attribute** (see sec 2.5) -- a property, not a coordinate.

Crystal-hole risk: today identity and phase are **string-concatenated** in
`agent_folders._assemble_agent_prompt` as `f"{identity}\n\n---\n\n{phase}"`.
Issue #27 wants identity-only suppression at phase-advance time; the current
shape forces a Place-into-Time leak (a "suppress identity" flag must travel
through the Time API). The composition law (sec 4) requires segments to be
independently retrievable.

### 2.3 Role -- *recipient*

The agent receiving the prompt.

Values for project_team: `coordinator`, `composability`, `terminology`,
`skeptic`, `user_alignment`, `researcher`, `implementer`, `test_engineer`,
`ui_designer`, `project_integrator`, `sync_coordinator`, `lab_notebook`,
`memory_layout`, `binary_portability`, `default`. (15.)

Independence claim: roles are folder-keyed; adding a role is a folder add.
Today's role-axis tooling is mostly file lookup. Roles do **not** independently
choose their own content -- this is one of the user-protected priorities
(LF section 6, item 3): the agents themselves should "review and suggest"
their content.

### 2.4 Gating -- *control surface, not a coordinate*

**Per Terminology Q-T2 decision: gating is NOT an axis.** It is the
predicate machinery that parameterises `inject(t, p, r)`. The user does not
pick a "gating value" at fixed (time, place, role); the (time, place, role)
cell IS the coordinate, and the gate is what makes it fire or not. Gating
"values" (`always`, `per-phase suppress`, `per-setting toggle`,
`standing-by`) are *kinds of config*, not coordinates.

Gating remains its own **spec doc** (`spec_gating.md`) because the design
problems are real:
- predicate signature -- `gate(time, place, role, phase, settings, manifest)
  -> bool`, pure, no side effects.
- two config homes -- phase YAML (#27) and user/project settings (#28),
  composed via AND so neither layer can force injection over the other's
  veto.
- default-cell behavior table -- which cells default to `True` when no
  config exists.

Independence claim withdrawn -- gating is not orthogonal to the three
coordinates; it operates over them.

### 2.5 Source -- *attribute of a segment, not a coordinate*

**Per Terminology Q-T1 decision: source is NOT an axis.** Each segment has
exactly one source today:

| Segment | Source | Freshness contract |
|---------|--------|--------------------|
| identity | bundled markdown | spawn-time freeze (file-mtime per process) |
| phase | bundled markdown | per-injection-site read (file-mtime) |
| constraints | computed digest over `LoadResult` | per-call live |
| environment | runtime substitution from engine state (opt-in workflows) | per-engine-state-change |

Two segments share `bundled markdown`, so source is not even
unique-per-segment. The source mapping is a per-segment attribute; what
matters compositionally is the **freshness contract** column, which the
place-axis spec must document and reconcile (failure mode F3 -- three
coexisting freshness contracts -- lives on this table, not on a separate
axis).

No `spec_source.md` exists. The freshness table above is owned by the
place-axis spec.

---

## 3. Crystal: 5 x 4 x 16 = 320 base cells

(time, place, role) are the only coordinates. Gating is the predicate
parameterisation; source is a per-segment attribute. Place expanded from
3 to 4 post-Q-T3 opt-in resolution (environment segment is now first-class
v1, opt-in default-false). Role count is 15 typed + 1 default. Of the 320:

- **Most cells should fire `always`.** A coordinator at activation receives
  identity + phase + constraints + environment.
- **A small number of cells fire `never`-by-default.** Failure mode F8 says
  default-roled agents have no role dir, so identity/phase = empty. Today
  `assemble_agent_prompt` returns `None` and the constraints block is lost.
  This is an unsupported-combination crystal hole.
- **#27's target cells** are `(phase-advance-main, identity, R)` and
  `(phase-advance-broadcast, identity, R)` for standing-by `R` -- workflow-
  author wants these to fire `never` when `R` has no `<phase>.md`.
- **#28's target cells** are `(*, constraints, *)` -- user-controlled toggle.

The 10-point test (sec 6) finds 4 holes today.

---

## 4. Compositional law

```
inject(time, place, role) -> bytes | EMPTY
  where the assembly is:
    inject(t, p, r) = render(p, ctx(t, r))   if gate(t, p, r) else EMPTY
  and the prompt delivered at time t to role r is:
    PROMPT(t, r) = SEPARATOR.join(
        inject(t, p, r) for p in PLACES
        if inject(t, p, r) is not EMPTY
    )
```

Where:
- `render(place, ctx)` is the segment assembler (one per place).
- `ctx(time, role)` is the runtime context (engine, loader, artifact_dir,
  workflow_id) -- read-only inputs.
- `gate(time, place, role)` is a **pure predicate** over `(time, place, role,
  phase, settings, manifest)`. Default: `True`.
- `SEPARATOR` is the canonical between-segment join (today: `"\n\n"`).

**Why the law is algebraic.** Adding a new place doesn't change the time API.
Adding a new time doesn't change the place API. Adding a role doesn't change
either. Adding a gate clause (from #27 or #28) only modifies `gate` -- never
`render` or `ctx`. M^N composition by construction.

**Why this maps to the existing code.** Today there is one composition point
(`assemble_agent_prompt`) and 5 callers. The law preserves this shape. The
only structural change required is splitting `_assemble_agent_prompt` so each
place is a separate `render_<place>(ctx) -> bytes` call, and routing a
`gate(...)` predicate through the helper.

**Compatibility constraint:** the existing public output shape
`f"{phase_prompt}\n\n{constraints}"` must remain producible from the new
law (verified by parity test). Existing inject-site call signatures should
not change.

---

## 5. Seams

### 5.1 Time / Place seam (clean today, must stay clean)

**Crosses the seam:** the named place + the resolved context.
**Must not cross:** which time is calling. `render_identity(ctx)` should
produce the same bytes whether called at spawn or at phase-advance.

**Today's leak:** identity + phase are concatenated inside
`_assemble_agent_prompt`. Any caller that wants "phase only" must either
post-process the string or thread a flag in. Both are leaks. **Fix:** split
into per-place renderers.

### 5.2 Place / Source seam (mostly clean; freshness leak)

**Crosses the seam:** bytes (the rendered segment).
**Must not cross:** how the source resolves freshness.

**Today's leak (F3):** consumers see different freshness behavior per place
(spawn-time freeze for identity, per-call live for constraints, post-compact
refresh for everything). The user can't predict "is what I'm reading
current?" **Fix candidate (out of v1 scope):** unify on a single freshness
contract -- recommend per-call live for all places that have a recompute
path, with explicit caching only as an optimization. Skeptic R4 flags this
as a regression risk; v1 should at least *document* the contract per place
and not silently change it.

### 5.3 Role / Place seam (clean except for default-role hole)

**Crosses:** role name (a folder key).
**Must not cross:** role-specific *logic* in place renderers.

**Today's hole (F8):** `assemble_agent_prompt` returns `None` for default-
roled agents, so the constraints segment is dropped. The constraints place
is supposed to be role-agnostic at the segment-render level. **Fix:** make
the renderer return-segment-or-empty per place, never short-circuit at the
top level.

### 5.4 Gating / Everything seam (the new seam to design)

The gating axis is the new control surface. The seam contract:

**Gate input:** `(time, place, role, phase, settings, manifest)`.
**Gate output:** `bool`.
**Gate side effects:** none.

**Must not cross the gate seam:** assembled bytes, agent state beyond
`agent_type`, runtime per-message conditions. (The latter rules out "smart"
gates that look at recent agent activity to decide standing-by status. v1 is
static.)

The gate is composed of independent sub-gates so config sources don't fight:
```
gate(t, p, r) = workflow_gate(t, p, r) AND user_gate(t, p, r)
```
- `workflow_gate` reads phase YAML (#27).
- `user_gate` reads user/project settings (#28).
The AND means either layer can suppress; neither can force injection over the
other's veto. (Discuss with gating-axis whether SHOULD vs MUST suppress
behavior is needed.)

### 5.5 Source / Sub-system seam

The four sources already correspond to leaf modules
(checks, hints, guardrails, defaults bundle). The Place axis must read sources
through their existing seam objects (`LoadResult`, digest functions, engine
substitution). **Do not** introduce a new bypass path for any place.

---

## 6. Crystal holes (10-point audit)

Random selection across `time x place x role`:

| # | Cell | Today | Issue |
|---|------|-------|-------|
| 1 | (spawn, identity, coordinator) | OK | -- |
| 2 | (spawn, constraints, default) | EMPTY | F8 -- segment lost (hole) |
| 3 | (activation, environment, coordinator) | OK | substituted in identity |
| 4 | (phase-advance-main, identity, coordinator) | always fires | #27 wants opt-out for standing-by |
| 5 | (phase-advance-broadcast, constraints, implementer) | absent | F1 -- broadcast not yet routed through helper (hole) |
| 6 | (phase-advance-broadcast, identity, implementer in testing-vision) | always fires | #27 target -- hole |
| 7 | (post-compact, identity, ui_designer) | OK -- full refresh | must stay (R3) |
| 8 | (any, constraints, any) | always fires | #28 wants user toggle |
| 9 | (any, constraints, default) | EMPTY placeholder | F9 -- 138-char noise (hole) |
| 10 | (spawn, environment, coordinator) in opt-in workflow | not in v1 prior to opt-in mechanism; project_team renders post-resolution | resolved by Q-T3 opt-in (place_axis YAML field) |

**Holes found: 4** post-Q-T3 opt-in resolution. (#2, #5, #9, #10.) Row #10
is now a v1 hole closed by place_axis's environment-segment opt-in mechanism
for project_team. Two more rows (#4 and #6) are not holes but unsupported-
by-config gaps that #27 fills. #8 is a UX gap that #28 fills.

---

## 7. Entanglement risks

R-comp-1. **Place-into-Time leak via concatenated assembly.** Discussed in
sec 5.1. Must be resolved before #27 can be cleanly implemented.

R-comp-2. **Standing-by as runtime state.** Skeptic R1: an agent can be
standing-by and a broadcast recipient simultaneously. v1 pins standing-by
to the **static** definition (terminology canon: "a spawned agent whose
role has no `<role>/<phase>.md` for the current phase"). This makes gating
a pure predicate; runtime agent-state detection is a v2 conversation.

**Refinement (Skeptic Q4, accepted):** "static" means the predicate is
**pure** and reads `(role, phase, manifest)` at evaluation time. It does
NOT mean "frozen at spawn." Standing-by is **re-evaluated per inject site**
because (a) `/compact` re-reads `(role, phase, manifest)` anyway, so
per-site costs no more than spawn-freeze, and (b) it is more correct when
a workflow override changes the phase.md set mid-run. Still pure -- no
agent-state inspection, no recent-activity reads. Owned by gating_axis.

R-comp-3. **Constraints opt-out reintroducing F4/F5/F7.** Skeptic R2.
Issue #28 should be **scope-limited**: format/scope yes, full opt-out no.
The gating-axis agent must not expose a "constraints off, MCP-only" mode in
v1 -- the constraints block is the load-bearing fix from `abast_accf332_sync`.

R-comp-4. **Identity authority preservation.** Skeptic R3. The role-axis
agent must read every `<role>/identity.md` for *load-bearing* statements
("If user sends 'x'", "You CANNOT cut features") and preserve them across
any restructure. This is a content invariant, not just an interface
invariant.

R-comp-5. **Other workflows starve.** Skeptic R5. Bundled tutorial / learner
workflows have sparser identity content. Any change to assembly defaults
must be opt-in for project_team or behavior-equivalent for others. Concrete
test: tutorial integration test (existing) must pass unchanged.

R-comp-6. **Source-axis freshness drift.** F3 + F4. Out of v1 scope as a
unification, but the spec MUST document the per-place freshness contract so
agents can answer "is what I'm reading current?". TerminologyGuardian and
the place-axis agent co-own this documentation.

R-comp-7. **Inline `${VAR}` substitution must keep working** alongside the
new environment segment. The two mechanisms coexist in v1: inline
substitution stays as a renderer property of identity/phase content
(matching today's behavior), and the environment segment is a separate
opt-in header block (Q-T3 resolution). Place-axis must guarantee that
splitting `_assemble_agent_prompt` into per-segment renderers preserves
substitution for `${CLAUDECHIC_ARTIFACT_DIR}` and `${WORKFLOW_ROOT}` in
identity and phase content for all 9 bundled workflows (R5). The 8 non-
opt-in workflows render byte-identical to today.

---

## 8. Hand-off contract for axis-agents

Each axis-agent receives this document as input and must:

1. **Adhere to the law in sec 4.** No design that requires `gate` to read
   bytes, or `render` to know which time it is, will pass review.
2. **Resolve at least one hole from sec 6.**
3. **Address the relevant entanglement risks from sec 7.**
4. **Coordinate with TerminologyGuardian** before introducing any new term;
   the canonical glossary is the source of truth.
5. **Express recommendations** as `(axis, change, blocking-deps,
   compatibility-impact)` per leadership_findings sec 9 (Compositional
   handoff contract from prior session).
6. **Verify each change against the failure-mode map** that
   skeptic+user_alignment will produce -- if a change does not resolve a
   cited F-number or gap, justify why.

### 8.1 Per-axis assignments

**time-axis agent.**
- Owns: sec 2.1, sec 5.1.
- Resolves: hole #5 (broadcast routing through helper); F1; F2 (no late-
  framing mechanism is out of v1, but document the gap).
- Locks: post-compact = full refresh (R3 / sec 5.4).
- Decides: is `pull` (agent-initiated MCP refresh) a 6th time or a v2 item?

**place-axis agent.**
- Owns: sec 2.2, sec 5.1, sec 5.2, the per-segment freshness table in sec 2.5.
- Resolves: R-comp-1 (split `_assemble_agent_prompt`); freshness-contract
  documentation (R-comp-6); R-comp-7 (preserve inline `${VAR}` substitution
  alongside the new environment segment).
- Decides: identity vs phase split point inside `agent_folders.py`. Per
  Skeptic shape constraint (locked by Coordinator), per-segment renderers
  ship as private module-level helpers (`_render_identity`,
  `_render_phase`, `_render_constraints`, `_render_environment`) inside
  `claudechic/workflows/agent_folders.py`. **No new module / no class
  hierarchy.**
- Resolves: hole #2, #9 (default-roled agent constraints injection -- F8/F9);
  hole #10 (environment segment opt-in for project_team).
- Owns the YAML schema: `environment_segment: enabled` (default `false`)
  per-workflow opt-in. Project_team is the sole v1 opt-in.

**role-axis agent.**
- Owns: sec 2.3, sec 5.3.
- Engages role agents directly (user-protected priority #3 in LF).
- Produces: **a single `prompt_audit.md`** with one section per role
  (Skeptic counter-proposal accepted). Cross-role observations -- duplicate
  authority statements, redundant phase-list mirrors -- surface in one
  read pass. The artifact dimension stays small.
- Preserves: identity authority statements (R-comp-4).
- Surfaces: redundancy (e.g. coordinator/identity.md phase list duplication
  with engine -- LF Q7).

**gating-axis agent.**
- Owns: sec 2.4, sec 5.4.
- Designs: phase YAML schema for #27; settings.yaml schema for #28.
- Pins: standing-by = static (R-comp-2).
- Decides: scope of #28 (format/scope only, NOT opt-out -- R-comp-3).
- Produces: gate predicate spec; default-cell behavior table.

**Source** is a per-segment attribute, not an axis (Q-T1). The freshness
table in sec 2.5 is owned by the place-axis spec; no separate agent.

**Gating** is the predicate-machinery spec (Q-T2). The gating-axis agent
designs the predicate, the two config homes (phase YAML, settings.yaml), and
the default-cell behavior table. Not a coordinate of the crystal, but a
real design problem.

---

## 8.2 Minimum-viable vs broader-review framing (Skeptic Q5)

Skeptic demands SPEC.md include a **"Minimum-viable #27 + #28"** section
(<30 LOC plus YAML/config) separate from the broader review. Composability
endorses this:

- A minimum patch makes the user's choice explicit -- "ship #27+#28 alone"
  vs "do the broader project_team context-delivery review."
- It pressure-tests the abstractions: if the inject law plus per-site
  gating predicate cannot land #27+#28 in <30 LOC, the abstractions are
  too heavy.
- It honours user-protected priority #1 (issues land) without locking the
  user into the expanded scope.

The minimum-viable patch fits naturally into the law in sec 4: a pure
`workflow_gate` predicate reading a new `suppress_identity: [phase_ids]`
field in workflow YAML (#27) and a pure `user_gate` reading a
`constraints.format` enum in `~/.claudechic/config.yaml` (#28). No new
module. No new abstraction. The broader review (segment split, default-
roled-agent constraints, freshness reconciliation, prompt audit) is the
expansion the user can opt into.

Coordinator owns SPEC.md; Composability commits to ensuring the law,
seams, and crystal in this document support the minimum-viable patch
without restructuring.

## 9. SPEC.md responsibilities (Composability's contributions)

Composability owns these SPEC.md sections in the master document:
- "Compositional law" (sec 4 of this doc).
- "Seam discipline" (sec 5).
- "Crystal hole inventory + resolutions" (sec 6, joined to the
  failure-mode map).
- "v1 scope vs v2 scope" boundaries on standing-by, freshness, and
  constraints opt-out.

Co-owned with other Leadership leads:
- "Glossary" with TerminologyGuardian.
- "Hard questions for user before Spec lock" with skeptic + user_alignment.
- "User-protected priorities preservation" with user_alignment.

---

## 10. Verification plan (sketch)

A. **Law parity test** -- existing prompt output for each of the 5 inject
sites must be reproducible from the new `inject(t, p, r)` law with all
gates `True`. Byte-for-byte parity against a captured fixture.

B. **Per-axis swap tests** -- change one place's renderer, verify other
places' renderers don't change. Same for time, role, gate.

C. **Hole closure tests** -- one test per hole in sec 6 demonstrating it is
closed.

D. **Failure-mode regression tests** -- one test per F-number in
`leadership_findings.md` sec 4 demonstrating the failure does not recur.

E. **Other-workflow tests** -- existing tutorial / learner workflow tests
pass unchanged (R5).

The test_engineer agent owns the test plan. This section is a sketch of
what Composability will require during testing-spec review.
