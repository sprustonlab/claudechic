# SPEC -- project_team_context_review

Operational specification. Rationale, rejected alternatives, and historical context live in `SPEC_APPENDIX.md`. Glossary at `GLOSSARY.md`. Failure-mode map at `failure_mode_map.md`. Per-role audits at `prompt_audit/<role>.md`. Per-axis specs at `spec_time_axis.md`, `spec_place_axis.md`, `spec_role_axis.md`, `spec_gating_axis.md`.

---

## 1. Goal (operational restatement)

Tighten the `project_team` workflow by reviewing the time, place, and role of context delivery to its agents, so the team has what it needs to drive the project forward at every step. Issues #27 and #28 are addressed.

## 2. Scope of v1

In scope:
- Identity / phase split in prompt assembly so each segment is independently injectable.
- A pure gating predicate `gate(time, place, role, phase, settings, manifest) -> bool` next to `assemble_agent_prompt` in `agent_folders.py`. No new module.
- Issue #27: per-phase suppression mechanism in workflow YAML.
- Issue #28: format-and-scope-only configurability of the constraints segment in user-tier and project-tier `~/.claudechic/config.yaml`. No opt-out.
- Standing-by static matrix for `project_team` (16 roles × 10 phases).
- Bundled prompt content revisions for `project_team`: hoist `message_agent` boilerplate to a shared content source; replace pytest-policy prose with reference to constraints; preserve the 22 cataloged authority statements verbatim.
- Failure-mode regression guards for F1, F4, F5, F7, F8, F9.

Out of scope (v2 / follow-up):
- Recurring per-phase "review and suggest" loop with a structured `propose_prompt_edit` MCP tool.
- F2 (late framing reveal): requires runtime state, breaks predicate purity.
- Chicsession-resume promotion to a tracked injection site (F3 residual mitigation).
- Spawn-condition (`spawns_when:`) manifest field for non-coordinator roles.
- Per-segment freshness contracts unification.

## 3. Open decisions for the user (Spec checkpoint)

These are unresolved. The team has split positions on D1 and D2; the coordinator picked working defaults on D3 and D4 that the user may override.

### D1. Environment segment v1 status (the architectural call)

| Position | Argument | Held by |
|---|---|---|
| **A. First-class peer, default-on at spawn** | The user's "regardless of workflow" wording is honored at the mechanism level. Three concrete enablements: team-dynamics content static rules cannot deliver; post-compact recovery parity; non-empty composer return for default-roled agents. Two new parts: bundle dir + ~20 LOC pure function. Reversible per-workflow. | place_axis, time_axis, gating_axis, user_alignment |
| **B. Tier-2; v1 keeps inline `${VAR}` substitution** | No prior-run F-number names environment as a failure. Pre-promoting ships a header into all 9 bundled workflows for project_team's gain alone, risking R5 (silent behavior change for tutorial / learner). v2 promotes cleanly once Q1 is decided. | composability, skeptic |
| **C. Compromise: global-opt-in (coordinator working default)** | Mechanism global; activation per-workflow YAML field `environment_segment: enabled`, default false. project_team opts in for v1. Tutorial / cluster_setup / etc. stay false. Predicate: `inject(spawn, env, role) = workflow_yaml.get("environment_segment", False)`. User-tier `disabled_ids: global:environment-segment` always wins. | place_axis (revised); pending composability acceptance |

**Decision required.** The team has converged enough that A or C is implementable today; B requires reverting three axis specs.

### D2. Q2 mechanism for "agents review and suggest the content of injections at all phases"

| Option | Description | Held by |
|---|---|---|
| **a. One-shot** | This run's `prompt_audit/<role>.md` documents are the deliverable; revisions land in bundled content; no ongoing mechanism. | skeptic |
| **b. Lightweight (coordinator working default)** | Plus: a per-phase feedback notes file (e.g. `<artifact_dir>/role_feedback/<role>_<phase>.md`) any role agent may write to. Coordinator reads at next phase advance and decides accept/decline. No new MCP tool. | role_axis (hybrid), user_alignment |
| **c. Full** | Structured `propose_prompt_edit` MCP tool with hot-reload. | (none -- considered scope creep) |

**Working default: b (lightweight).** Override available.

### D3. Whether to also opt-in `tutorial` (only relevant if D1=C)

If D1 lands at C, project_team is the only v1 opt-in. tutorial / cluster_setup / etc. stay opted-out. Decide whether to add tutorial as a second opt-in for v1 or defer.

**Working default: project_team only.** Override available.

## 4. Locked decisions (no user action required, listed for visibility)

- **L1.** Three delivery axes: time × place × role. Place enumeration is D1 above.
- **L2.** Compositional law: `inject(t, p, r) = render(p, ctx(t, r)) if gate(t, p, r) else EMPTY`. Pure predicate. Single-function shape next to `assemble_agent_prompt`. No new module.
- **L3.** Issue #28 scope: format-and-scope only; no `enabled: false`. Settings keys: `constraints.format`, `constraints.include_skipped`, `constraints.scope.sites`. `structural_gate` enforces a floor: at least one injection site MUST emit constraints AND route through the same projection that hooks read.
- **L4.** Issue #27 home: `gating: { suppress: [{segment, roles, times}] }` block per phase entry in workflow YAML. spawn / activation / post-compact never suppressible by config. Default times = `[phase-advance-main, phase-advance-broadcast]`.
- **L5.** Standing-by definition: a role with no `<role>/<phase>.md` for the active phase. Predicate is pure (file-system check, no runtime memo). Evaluated per call, not frozen at spawn.
- **L6.** Identity / phase split: `assemble_agent_prompt` becomes a thin orchestrator over private renderers (`_render_identity`, `_render_phase`, `_render_constraints`, possibly `_render_environment` per D1) inside `agent_folders.py`. Composer joins non-empty segments with `\n\n---\n\n`. Empty segments dropped.
- **L7.** Default-roled agents receive the constraints segment when global rules apply. They receive identity and phase as empty. Environment depends on D1.
- **L8.** Authority preservation: 22 cataloged identity quotes (see `spec_role_axis.md` §2) preserved verbatim. Removal requires explicit user authorization.
- **L9.** Five injection sites: T1 spawn, T2 activation, T3 phase-advance.main, T4 phase-advance.broadcast, T5 post-compact. T5 is canonical full refresh.
- **L10.** Issue #27 resolution cell: `gate(phase-advance-broadcast, identity, typed standing-by) = False`. Single cell of the gating default-cell table.

## 5. Build plan (Implementation phase preview)

Implementer tasks, in dependency order:

1. **Identity / phase renderer split** (`agent_folders.py`). L6.
2. **Pure gating predicate** (`agent_folders.py`). L2.
3. **Default-cell table** materialized as data in `agent_folders.py` (constants).
4. **Workflow YAML schema extension** for `gating.suppress` (L4) and `environment_segment` if D1 lands at A or C.
5. **Settings schema extension** for `constraints.*` (L3).
6. **Standing-by static matrix** for project_team materialized from existing role-folder file presence.
7. **Failure-mode regression tests** for F1, F4, F5, F7, F8, F9 (one test each, each tied to a regression guard).
8. **Bundled content revisions** for project_team (Content Move A: communication boilerplate to shared source; Content Move B: pytest prose to constraints reference). Authority preservation per L8.
9. **Per-role transient confirmation** during Implementation: implementer spawns each role with its `prompt_audit/<role>.md` + proposed revision; role confirms authority statements survive verbatim; edit applied. (D2=b adds a `role_feedback/` dir for ongoing notes.)

If D1=A: also bundle dir `claudechic/defaults/environment/` + `_render_environment` ~20 LOC.
If D1=C: same bundle dir + per-workflow YAML opt-in field.

## 6. Constraints

- All paths absolute in implementation prompts.
- The pure predicate MUST NOT reach for I/O or wall-clock.
- `assemble_agent_prompt` external API unchanged. Existing 5 inject-site callers see no signature change.
- `awareness_install.py` host-side rule mechanism is preserved. The environment segment (if D1=A or C) is in-prompt, not a replacement.
- No bundled workflow other than project_team changes behavior in v1 unless its author opts in via the YAML field (D1=C path) or directly modifies its content (no plan to do so).
- Pre-existing fixes from `abast_accf332_sync` (F4, F5, F6, F7) MUST NOT regress. The keystone test from `abast_accf332_sync/testing/skeptic.md` is binding.

## 7. Pass/fail bar for the implementation

Implementation phase ships only when:
- All 9 build-plan tasks pass tests.
- Each F-number from `failure_mode_map.md` matches its declared fate (closed-by-spec test exists; pre-existing-fix has no regression; out-of-v1 / accepted-risk are documented but not implemented).
- The 22 authority quotes are byte-identical between pre-change and post-change `identity.md` files (or have an accompanying user authorization).
- Other bundled workflows (tutorial, cluster_setup, audit, codebase_setup, git_setup, onboarding, tutorial_extending, tutorial_toy_project) pass their existing workflow tests.
