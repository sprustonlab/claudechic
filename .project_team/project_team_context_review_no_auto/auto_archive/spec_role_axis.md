# spec_role_axis.md

**Author:** role-axis agent. Specification phase v2.
**Axis:** Role -- *who* receives delivered context. Values: 15 typed roles + `default` (16 in v1 crystal).
**Glossary:** `GLOSSARY.md`. **Authority contract:** skeptic R3.
**Per-role detail:** `prompt_audit/<role>.md` (15 files: one per role + `default.md`). **Sibling specs:** `spec_time_axis.md`, `spec_place_axis.md`, `spec_gating_axis.md`. **F-numbers:** `failure_mode_map.md`. **Master:** `SPEC.md`.

---

## 0. Role-axis half of the inject predicate

The leadership-locked compositional law is:

```
inject(t, p, r) = render(p, ctx(t, r)) if gate(t, p, r) else EMPTY
```

The **role-axis half** of this predicate is:

1. **`r` is a closed enum of 16 values.** `r ∈ {coordinator, composability, terminology, skeptic, user_alignment, implementer, test_engineer, ui_designer, researcher, lab_notebook, memory_layout, sync_coordinator, binary_portability, project_integrator, default}`. (15 typed + `default`. Seg-based agents like `cluster` belong to other workflows, not project_team.)
2. **Role uniquely identifies (a) which `<role>/identity.md` and `<role>/<phase>.md` source files exist; (b) the role's authority statements and bounded-authority block; (c) the role's standing-by classification per phase.**
3. **The role-axis renderer is partitioned by role:** `_render_identity(ctx)` reads `defaults/workflows/<wf>/<role>/identity.md`; `_render_phase(ctx)` reads `defaults/workflows/<wf>/<role>/<phase>.md`. Both return `""` when the source file does not exist (place-axis empty-bytes contract; F8 / F9 closure).
4. **The constraints + environment renderers are also parametrized by role,** but their content is not authored under `<role>/` -- it is rule-projected (constraints) or platform-fact-projected (environment). Role still scopes them via `(role, phase)` filter.

**The role-axis owns:** the value set of `r`; the bundled prompt content under `<role>/`; the per-role authority statements catalog; the per-(role, phase) standing-by matrix's per-role half. **The role-axis does NOT own:** the gate predicate (gating-axis); the segment renderers themselves (place-axis); the injection-site enumeration (time-axis).

---

## 1. Is `role` alone the right partition key? (Skeptic A3 resolution)

**Yes -- `role` alone partitions the role-axis correctly. Skeptic lead's Q2 reply concurs with one clarification: A3 was about RUNTIME CONTEXT (cwd varies per sub-agent); as a CONTENT-SELECTION key (which identity/phase markdown to read), role is the right grain. cwd is substituted post-selection (inline substitution); parent/spawner collapses to workflow_id+main_role; agent_type IS role for typed agents. For default-roled agents (F8), there is no selection -- handled by separate F8 closure rather than by extending the partition key.**

**Rejected alternatives:**

| Candidate alternative | Rejected because |
|---|---|
| `(role, cwd)` | `cwd` is captured by `${CLAUDECHIC_ARTIFACT_DIR}` inline substitution (place-axis §6: inline substitution is preserved across all 9 bundled workflows). It is a renderer property, not a partition key. Different `cwd` -> different rendered bytes for the same `(role, phase)`; same partition cell. |
| `(role, parent_agent)` | `parent_agent` is the spawner's name. Today MCP's `spawn_agent` does not record this; if added, it would be a runtime field (breaks predicate purity per gating-axis §1). The spawn relationship is captured statically by `workflow_id + main_role` (always `coordinator` for project_team). |
| `(role, agent_type)` | **Redundant.** `role` IS `agent_type` (per glossary: prose form "role"; field name "agent_type"; folder name "<role>/"). The two are the same value; no partition refinement. |
| `(role, workflow_id)` | Workflow_id is implicit in the role -- different workflows have different role folders. project_team's `composability` and tutorial's `composability` (if it existed) would be different cells; but role enums are workflow-bounded by the `defaults/workflows/<wf>/<role>/` path. Role is the right grain within a workflow. |

**Skeptic A3 closed.** Role is the partition key. Per-call evaluation (gating-axis §1 purity contract) recomputes the standing-by classification by `(role, phase, manifest)` lookup at gate-call time, but the partition itself is over `role` alone.

**Note for skeptic:** if a future requirement needs a finer partition (e.g. one role spawned with two distinct authority profiles), the right move is to introduce a **new role** (a new enum value, a new folder) rather than refine the partition key. Keeps the predicate pure and the crystal flat.

---

## 2. F-number map (role-axis perspective)

Each F-number's role-axis-specific change. Cross-references to `failure_mode_map.md` for the master fate.

| F# | Role-axis change | Audit citation |
|---|---|---|
| **F1** | Not a role-axis concern (gating + time own the broadcast routing fix). Role-axis confirms: every typed role's `prompt_audit/<role>.md` reaffirms `gate(T4, constraints, role) = True` per the F1 floor. | `prompt_audit/composability.md` §9, `skeptic.md` §9, et al. |
| **F2** | Not a role-axis concern (workflow-coordination layer; out-of-v1). Role-axis notes: the role_feedback/<role>_<phase>.md mechanism (SPEC D2 option b) is the v1 partial answer to F2's class -- agents can flag "framing has shifted" via the feedback file. | -- |
| **F3** | Not a role-axis concern (time-axis owns post-compact freshness). Role-axis confirms: at T5 post-compact, every role's identity + phase + constraints + environment re-fires from current bundled content (R3 lock). | All audits §9 (T5 row). |
| **F4** | Not a role-axis concern (gating; pre-existing-fix). | -- |
| **F5** | Not a role-axis concern (gating; pre-existing-fix). | -- |
| **F6** | Not a role-axis concern (gating; pre-existing-fix; predicate purity rules out recurrence). | -- |
| **F7** | Not a role-axis concern (gating; pre-existing-fix). Role-axis confirms: `default` is a legal role enum value with its own `prompt_audit/default.md` audit. The role-axis treats `default` like any other role at the partition layer; no falsy-string short-circuit. | `prompt_audit/default.md` §1, §4. |
| **F8** | **Role-axis owns the per-role identity rendering.** Each `prompt_audit/<role>.md` §9 cell map specifies that `_render_identity` returns `""` when no role dir exists (default-roled case) AND that the constraints renderer fires independently. F8 closure relies on the place-axis empty-bytes contract per renderer; role-axis confirms: every role audit, including `default.md`, asserts identity returns empty rather than short-circuiting whole-prompt. | `prompt_audit/default.md` §2 (F8 disposition). |
| **F9** | **Role-axis confirms** the per-segment empty-bytes contract for every typed role: standing-by phases produce empty phase segments (no placeholder), and the constraints segment short-circuits to `""` when both rules and checks are empty. | `prompt_audit/default.md` §2; all standing-by phase rows in §9 cell maps. |

**Role-axis-driven changes** (not failure-driven; user-priority-driven):

- **U3 (UserAlignment priority #3 -- "agents review and suggest"):** addressed by the v1 one-shot audit (this run's `prompt_audit/<role>.md` documents) + future-run lightweight `role_feedback/<role>_<phase>.md` mechanism. Per-role audits in §11 record the review status (4 Leadership audits get role-agent review during Specification; 11 non-Leadership audits marked "needs role-agent review during Implementation").

---

## 3. F8 resolution -- default-roled agents and constraints

**Resolution: Q5 = YES, locked.** Default-roled agents receive the constraints segment when applicable rules exist. Per `agent_folders.py:L304-L308` post-slot-3 fix, this is already the implementation behavior. SPEC §D and impl agree. F8 is **closed-by-spec**.

**User decision presented (for visibility, not re-opening):**

| Option | Description | Verdict |
|---|---|---|
| **A. Default-roled gets constraints (current behavior)** | F8 closure preserved. SPEC §D matches impl. | **LOCKED** -- user-protected priority #2 (claudechic-environment at spawn) requires constraints + env even for default-roled agents in opted-in workflows. |
| B. Default-roled gets nothing | Re-introduces F8. | Rejected. |
| C. Default-roled gets identity placeholder | Re-introduces F9 noise. | Rejected. |

**Cell map confirmation (`prompt_audit/default.md` §4):**

- `gate(T1, identity, "default", *) = True; render returns "" (renderer-empty)`
- `gate(T1, phase, "default", *) = True; render returns ""`
- `gate(T1, constraints, "default", *) = True; render returns digest if rules apply, else ""`
- `gate(T1, environment, "default", *) = True (when workflow opted in)`
- `gate(T4, constraints, "default", *) = True (F1 floor; structural)`

The composer drops empty segments. Default-roled launch prompt: constraints + environment only (when applicable).

---

## 4. F9 resolution -- empty-digest placeholder noise

**Resolution: empty-digest renderer returns `""`, composer drops the empty segment.** No 138-char placeholder. F9 is **closed-by-spec**.

The L221-L222 short-circuit in `assemble_constraints_block` already returns `""` when both `rules_rows` and `check_rows` are empty. The place-axis spec §6 extends this to a per-segment invariant: every `render_<segment>` returns `""` when its source content is empty. The composer joins non-empty segments with `\n\n---\n\n` and drops empties.

**Role-axis contribution:** every per-role audit's §9 cell map asserts the empty-bytes outcome for standing-by phases (where `<role>/<phase>.md` is absent) and for default-roled agents (where no role dir exists).

**No noise in launch prompts.** A fully standing-by typed sub-agent at T4 broadcast receives: identity (suppressed by #27), phase (renderer-empty), constraints (renders if rules apply), environment (renders if workflow opted in). Launch payload is `constraints + environment` only -- no placeholder, no separator orphans.

---

## 5. Per-role identity edits (citations)

Concrete identity.md edits proposed by role-axis are catalogued per role in `prompt_audit/<role>.md` §8. Summary:

| Role | Edit | Lines deleted | Net post-edit |
|---|---|---|---|
| coordinator | Add header before L34 marking informational mirror | 0 (header added) | 61 lines |
| composability | Replace L7 (Leadership roster) + delete L513-L523 (comm block) | 11 | ~511 lines |
| skeptic | Delete L106-L116 (comm block) | 11 | 105 lines |
| user_alignment | Delete L106-L116 (comm block); +pending implementation.md add | 11 | 145 lines |
| terminology | Delete L82-L92 (comm block) | 11 | 89 lines |
| implementer | Delete L90-L100 (comm block). **L109 pytest rule: NO CHANGE** (rolled back per user 2026-05-02 -- "don't reference something we can gate with settings"). | 11 | ~99 lines |
| test_engineer | Delete L84-L93 (comm block). **L101-L102 pytest rule: NO CHANGE** (rolled back per user 2026-05-02). +add 2 phase mds. | 11 | ~91 lines |
| ui_designer | Delete L123-L133 (comm block); +add 2 phase mds | 11 | ~132 lines |
| researcher | Delete L165-L175 (comm block) | 11 | ~229 lines |
| lab_notebook | Delete L253-L264 (comm block) | 12 | ~340 lines |
| memory_layout | Delete L118-L129 (comm block) | 12 | ~117 lines |
| sync_coordinator | Delete L102-L112 (comm block) | 11 | ~108 lines |
| binary_portability | Delete L70-L80 (comm block) | 11 | ~76 lines |
| project_integrator | Delete L174-L184 (comm block) | 11 | ~181 lines |
| default | N/A (no folder) | -- | -- |

**Total deletions:** 145 lines of comm-boilerplate (14 identity files × ~11 lines each), recovered at injection time via the new environment segment (place-axis §3).

**Env-segment content adds** (composability lead's Q3 reply -- new for v1):

- **Agent name routing table** `{role -> registered_name}`. Required after composability lead's Leadership-phase failure: tried to message `coordinator` but registered name was `claudechic`. Dynamic per run. Place_axis owns sourcing this from runtime engine state.
- **Peer roster with 2-sentence-per-peer summaries.** Identity files name peers without descriptions; agents currently must read peer identity files to learn output shape. Static per workflow (project_team has 14 typed roles + main_role).

These are **content adds** to the env segment bundle, not deletions from identity. Place_axis coordination required (`claudechic/defaults/environment/*.md`).

**v2 follow-up (composability lead's Q1, Q4):**

- Hoist L306-L378 (HOW patterns) + L381-L422 (smells tables) of composability identity to `composability_methodology.md` env-segment-injected only at specification + implementation phases. Saves ~90 lines from composability's spawn payload.
- Hoist Generalprobe Standard duplicate (~14 lines) from `composability/testing-specification.md` + `composability/testing-implementation.md` to shared env-segment injection for testing phases.

**v1 add (per user clarification 2026-05-02 -- spec self-containment, COORDINATOR-ONLY placement):**

- Inline the spec-self-containment rule TEXT directly into `coordinator/specification.md` AND `coordinator/testing_specification.md`. NO new `conventions.md` file; NO indirection; NO identity edits; NO other roles touched. Coordinator is the gatekeeper -- the rule is enforcement (coordinator routes spec to user), not authoring guidance for sub-agents. Standing-by predicate handles non-spec phases automatically (these two phase mds inject only during their respective phases). Backfill: GLOSSARY.md becomes archive history; canonical definitions fold into SPEC.md (or successor spec docs) per the rule itself.

**Authority statements:** 22 cataloged R3 quotes preserved verbatim (full catalog in `prompt_audit/<role>.md` §3 of each file). Byte-compare verification during Implementation phase. **Skeptic lead's Q1 reply expanded the catalog: skeptic L66-L82 (red-flags list) elevated to R3 (named rejection criteria).**

**Comm-block split pattern (skeptic lead's Q4 reply -- applies cross-role):** the `## Communication` block in 14 identity files is NOT a wholesale env-segment move. It SPLITS into:

- **Tool semantics (~7 lines, e.g. skeptic L106-L112)** -> env segment (platform facts: what `message_agent` / `interrupt_agent` / `requires_answer=false` are and what they do). Workflow-agnostic.
- **Behavioral guidance (~4 lines, e.g. skeptic L113-L116, the "When to communicate" list)** -> per-phase markdown. **Phase-dependent**: e.g. skeptic in specification awaits coordinator response (`requires_answer=true`); skeptic in testing-vision sends fire-and-forget (`requires_answer=false`).

**Cross-role implication:** all 14 audits' §8 "Move to environment" entries are refined to this split. Total comm-block lines moved unchanged (~145 lines), but split between env segment (platform-fact half) and per-phase markdown (behavior half). When phase mds are added or amended (e.g. test_engineer's new testing-specification.md), they include a one-line phase-specific communication directive. **Implementer applies during Implementation; per-role agents confirm split semantics in their transient review step.**

**Phase-md additions (v1):**
- `test_engineer/testing-specification.md`
- `test_engineer/testing-implementation.md`
- `ui_designer/specification.md`
- `ui_designer/implementation.md`
- `user_alignment/implementation.md` (**Q3 RESOLVED -- user_alignment lead confirms ACTIVE.** Phase-md content: "on each substantial PR or feature landing, scan against userprompt.md; flag 'user said X, implementation is doing Y' patterns; call out features quietly deferred or shaped differently than stated.")

**Phase-md additions (out of scope v1; v2 follow-up):**
- researcher: 5 phases (vision, specification, implementation, testing-specification, testing-implementation)
- lab_notebook: 2 phases (implementation, testing-implementation when experiment-shaped)
- memory_layout / sync_coordinator / binary_portability / project_integrator: 2 phases each (specification, implementation when spawned)

**Phase-md reverse-direction sweep:** none. No existing `<role>/<phase>.md` is "really standing-by" -- every existing phase markdown carries substantive operational content. The static "no phase.md = standing-by" predicate is correct as the v1 definition.

---

## 6. Standing-by static matrix (role-axis half)

The static matrix is co-owned with gating-axis (`spec_gating_axis.md` §5 has the gating-axis half). Role-axis owns the per-role file-presence inventory.

| role | vis | set | lead | spec | impl | tv | ts | ti | doc | sgn |
|------|-----|-----|------|------|------|----|----|----|-----|-----|
| coordinator | A | A | A | A | A | A | A | A | A | A |
| composability | by | by | by | A | A | by | A | A | by | by |
| terminology | by | by | by | A | by | by | A | A | by | by |
| skeptic | by | by | by | A | A | by | A | A | by | by |
| user_alignment | by | by | by | A | **A** | by | A | A | by | by |
| implementer | -- | -- | -- | -- | A | -- | -- | A | -- | A |
| test_engineer (v1 fix) | -- | -- | -- | -- | -- | A** | A** | A** | -- | -- |
| ui_designer (v1 fix) | -- | -- | -- | A** | A** | -- | -- | -- | -- | -- |
| researcher | A** | -- | -- | A** | A** | -- | A** | A** | -- | -- |
| lab_notebook | -- | -- | -- | -- | A** | -- | -- | A** | -- | -- |
| memory_layout | -- | -- | -- | A** | A** | -- | -- | -- | -- | -- |
| sync_coordinator | -- | -- | -- | A** | A** | -- | -- | -- | -- | -- |
| binary_portability | -- | -- | -- | A** | A** | -- | -- | -- | -- | -- |
| project_integrator | -- | -- | -- | A** | A** | -- | -- | -- | -- | -- |
| default | (catch-all; never typed) |

`A` = active (phase.md exists or is added in v1); `by` = standing-by (no phase.md, suppress identity at T3/T4); `--` = not spawned in this phase. `**` = depends on §5 phase-md additions (v1) or v2 follow-up. **Q-Role-1 RESOLVED:** user_alignment lead confirms ACTIVE during implementation. New v1 phase-md `user_alignment/implementation.md` per §5.

Reconciles with gating-axis §5: each `S` cell in the gating matrix corresponds to a `by` cell here; each `.` (active) cell corresponds to `A`. The matrix is materialized as `gating: { suppress: ... }` entries in `project_team.yaml` (place-axis owns the YAML diff per place-axis §7).

---

## 7. Mechanism for "agents review and suggest" (Q2 / U3)

User priority #3: *"agents review and suggest the content of injections at all phases."* Two distinct artifacts, distinct lifecycles. Working default per coordinator (pending user override at Q2 checkpoint): **option (b) lightweight feedback notes.**

### 7a. THIS run -- one-shot audit (v1 deliverable)

**`prompt_audit/<role>.md` files** (15 in this directory) cover all 15 roles + default.

- **Proposes:** role-axis (this run) authored by reading bundled identity files + sending review messages to spawned Leadership leads.
- **Reviews:** Leadership team -- TerminologyGuardian (canonical names), Skeptic (R3 preservation), UserAlignment (intent), Composability (seam) -- AND each role lead reviews ITS OWN audit. The 4 Leadership leads were engaged via `message_agent` during this Specification phase (see `prompt_audit/<role>.md` §11 for each).
- **Decides:** user, at spec-approval checkpoint. Authority statements (§5 cited per-role §3 catalogs) non-revisable except by explicit user authorization.
- **Edits:** Implementer applies approved edits to `claudechic/defaults/workflows/project_team/<role>/identity.md` during Implementation phase. **Implementation step:** implementer spawns each role transiently with audit + proposed revision; role confirms authority statements survive verbatim; edit applied. The transient spawn is the literal "agent reviews its own content" step. For 11 non-Leadership roles, this is the first review opportunity (marked "needs role-agent review during Implementation" in each audit's §11).

This is the v1 deliverable. It does not recur.

### 7b. FUTURE runs -- lightweight per-phase feedback (v1 mechanism)

Supports the user's *"at all phases"* wording for any future project_team run. **Working default: option (b) -- file-on-disk feedback notes.** No new MCP tool.

- **Where:** per-run, per-(role, phase) markdown file at `${CLAUDECHIC_ARTIFACT_DIR}/role_feedback/<role>_<phase>.md`. Path is run-bound via the standard `${CLAUDECHIC_ARTIFACT_DIR}` substitution.
- **Who writes:** the role agent. Free-form markdown; one entry per proposal with date + brief rationale + proposed diff.
- **Who reads:** coordinator, at the next phase advance. Coordinator's phase-segment update (one line per `coordinator/<phase>.md`): *"Read `${CLAUDECHIC_ARTIFACT_DIR}/role_feedback/` and triage with Leadership before advancing."*
- **CRITICAL (per user_alignment lead's Q1 reply):** the mechanism honors the user's *"at all phases"* wording **only if** coordinator actually reads at every phase advance, not just when something breaks. **Mitigation:** add an explicit `advance_check` to each phase entry in `project_team.yaml` -- a `command-output-check` of the form `"ls ${CLAUDECHIC_ARTIFACT_DIR}/role_feedback/ 2>/dev/null | head -1"` which surfaces a non-empty result as a triage trigger. Even if no proposals exist, the check fires deterministically -- making the read step part of the phase-advance contract, not an ad-hoc scan. This is a 14-line YAML addition (one advance_check per phase) and stays inside skeptic_review.md's "one new abstraction" cap (the abstraction is the `role_feedback/` convention; the advance_check is a use-site of existing engine machinery).
- **What the coordinator does:** Accept -> delegate to implementer to write through to bundled prompt content (under R3 floor). Decline -> record reason in feedback file. Defer -> note kept; revisit at next phase advance.
- **Authority floor:** R3 statements (per-role §3 catalogs) are not revisable through this mechanism. Proposals that touch them require explicit user authorization at the next user checkpoint (parity with §7a).
- **No new engine code:** files on disk + a coordinator phase instruction + per-phase YAML advance_check. Three moving parts (directory convention + coordinator-phase line + YAML check). Stays under skeptic_review.md cap of "one new abstraction".

### 7c. Distinction (do not conflate)

§7a is the artifact for THIS run: one-shot audits flow through Implementation as concrete edits. §7b is the recurring mechanism for FUTURE runs: a directory convention + a coordinator phase instruction. Both share the R3 floor and the write-through-to-bundled-content pattern; otherwise independent.

---

## 8. Coordination (cross-axis)

- **time_axis:** the role-axis confirms time-axis's per-site invariants by confirming each per-role audit's §9 cell map is consistent with §2.0 of `spec_time_axis.md` (default segment set per site). At T4 broadcast, every typed standing-by role gets `(suppress identity, empty phase, fires constraints by F1 floor, fires environment when opted in)`. At T5 post-compact, every role gets a full refresh (R3 lock).
- **place_axis:** the role-axis depends on place-axis's split renderers (`_render_identity`, `_render_phase`, `_render_constraints`, `_render_environment`) and the per-segment empty-bytes contract. F8/F9 closure depends on this. Place-axis owns the YAML diff materializing the standing-by matrix into `project_team.yaml` `gating: suppress` entries.
- **gating_axis:** `gate(t, p, r, ...)` evaluates per-call (purity contract); role-axis supplies the canonical role list and the per-role authority catalog. The structural floor (gating-axis §6) protects F1 + F8 cells -- role-axis confirms no per-role audit proposes a configuration that would override the floor.
- **terminology:** role-axis uses canonical names from `GLOSSARY.md` -- *injection site*, *prompt segment* (identity / phase / constraints / environment), *standing-by agent*, *role* (prose) / *agent_type* (field), *Leadership* (canonical home: `coordinator/identity.md:62`).

---

## 9. Open questions (for user checkpoint)

These feed `SPEC.md`'s D-numbered user-decision list.

| ID | Question | Status |
|---|---|---|
| Q-Role-1 | UserAlignment Implementation phase: active or standing-by? | **RESOLVED: ACTIVE.** user_alignment lead confirmed (`prompt_audit/user_alignment.md` Q3). New v1 phase-md `user_alignment/implementation.md`. |
| Q-Role-2 | Per-role agent review of 11 non-Leadership audits during Implementation -- proceed as planned (transient spawn step in §7a)? | **Yes (working default).** Override available. |
| Q-Role-3 | Coordinator informational mirror L34-L47 -- keep with header, or migrate to MCP-tool reference? | **Keep with header (v1).** Migrate v2. |
| **Q-Role-4** | **Env-segment scope drift watch (user_alignment lead Q4):** does the v1 architecture (`mechanism global, activation per-workflow YAML opt-in, project_team is sole v1 opt-in`, per `GLOSSARY.md` Q-T3) honor the user's *"regardless of workflow"* protected priority #2? Lead flags this as the user-decision-blocker that maps to `SPEC.md` D1. **A** (first-class peer, default-on at spawn -- honors at *both* mechanism and activation level) and **C** (compromise -- honors at *mechanism* level only) are the live options; **B** (tier-2 inline-only) is the regression. | **REQUIRES EXPLICIT USER SIGN-OFF AT SPEC CHECKPOINT.** Lead's drift watch flag escalated. Cannot finalize Spec without D1 user decision. |

---

## 10. Verification

A. **Authority preservation:** byte-compare 22 cataloged R3 quotes pre/post identity.md edits. Test asserts byte-identical.

B. **Per-role launch-prompt parity:** for each role + phase combination, assert that the post-edit launch prompt contains the role's authority block + phase content + constraints (when rules apply) + environment (when opted in). Byte-compare structure.

C. **Standing-by matrix parity:** for project_team, verify the materialized `gating: suppress` entries produce the §6 matrix exactly. Cross-checked with `spec_gating_axis.md` §5.

D. **Default-roled regression:** test asserts default-roled spawn at T1 receives `constraints + environment` only (no identity, no phase, no placeholder). F8 + F9 + F7 covered.

E. **Comm-boilerplate hoist:** test asserts post-edit identity files do NOT contain the `## Communication` block AND the assembled launch prompt DOES contain the env-segment-rendered comm block. Round-trip.

F. **Other-workflow no-regression:** tutorial / cluster_setup / etc. byte-identical launch prompts to today (no env opt-in, no identity edits).

---

## 11. Status

**Per-role audits (15 files in `prompt_audit/`):** complete.
- Coordinator + 4 Leadership leads + default: full audits (§1-11 each).
- 9 non-Leadership roles: full audits with §11 marked "needs role-agent review during Implementation".

**Leadership-lead self-review:** initiated via `message_agent` to composability, terminology, skeptic, user_alignment during this Specification phase. Replies integrated into `prompt_audit/<role>.md` §11 of each Leadership audit when received. **One open: user_alignment x implementation cell awaits user_alignment lead's Q3 reply.**

**Files written:**
- `spec_role_axis.md` (this file).
- `prompt_audit/coordinator.md`, `composability.md`, `skeptic.md`, `user_alignment.md`, `terminology.md`, `implementer.md`, `test_engineer.md`, `ui_designer.md`, `researcher.md`, `lab_notebook.md`, `memory_layout.md`, `sync_coordinator.md`, `binary_portability.md`, `project_integrator.md`, `default.md`.

---

*References: `GLOSSARY.md`, `failure_mode_map.md`, `spec_time_axis.md`, `spec_place_axis.md`, `spec_gating_axis.md`, `SPEC.md`, `prompt_audit/<role>.md`.*

*Author: role-axis agent. Specification phase v2.*
