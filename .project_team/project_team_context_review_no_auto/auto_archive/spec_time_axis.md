# spec_time_axis.md

**Axis:** Time -- the lifecycle moments at which context is delivered to an agent.
**Compositional law (leadership):** `inject(time, place, role) -> bytes-or-empty`, where the inner gate predicate is `gate(time, place, role, phase, settings, manifest) -> bool` (signature locked with gating_axis: `manifest` is a separate frozen-dataclass arg because #27 lives in workflow YAML and #28 lives in settings -- different homes, different precedence). This spec fixes the **time** dimension; place_axis and gating_axis fix the others.

## 1. Canonical injection-site list

Five sites. Each is an *injection site* (glossary): a runtime moment at which the engine assembles and delivers a prompt segment to a specific agent.

| # | Site id | Trigger | Recipient(s) | Today's call site |
|---|---------|---------|--------------|-------------------|
| T1 | `spawn` | `mcp.spawn_agent` creates a sub-agent | the new sub-agent | `claudechic/mcp.py:308` |
| T2 | `activation` | main agent's workflow becomes active (fresh or restored) | main agent | `claudechic/app.py:2131` |
| T3 | `phase-advance.main` | phase advance, target = main agent | main agent (coordinator) | `claudechic/app.py:2405` |
| T4 | `phase-advance.broadcast` | phase advance, fan-out to typed sub-agents | every spawned sub-agent whose `agent_type != DEFAULT_ROLE` and whose name != caller | `claudechic/mcp.py:1026` |
| T5 | `post-compact` | SDK `PostCompact` hook fires after `/compact` | the agent whose hook fired | `claudechic/workflows/agent_folders.py:362` |

### Sites considered and excluded (resolves vision A1)

| Candidate | Decision | Reason |
|-----------|----------|--------|
| `/compactish` (claudechic-side message-shrink) | **Exclude** | Operates on already-delivered history; no new role/phase context to inject. The agent's launch + post-compact prompts are preserved in transcript. If `/compactish` ever drops the launch turn, revisit. |
| Model swap | **Exclude** | `agent.agent_type` and `agent.effort` are read live by `_make_options`; the env propagates on reconnect. No new prompt segment is owed to the agent. |
| Agent rename | **Exclude** | Identity field, no role/phase impact. |
| Chicsession resume (`_restore_workflow_from_session`) | **Exclude from v1, v2 candidate** | Resumed transcript already contains the prior launch prompt. BUT: a chicsession saved before a constraints-format change will resume a stale block (F3 freshness risk). v2 candidate site `chicsession-resume` would re-inject under the post-compact invariants. |
| Settings change (e.g. `disabled_ids` toggled mid-run) | **Exclude (gating_axis confirmed)** | Per `spec_gating_axis.md`: a mid-run settings reload applies at the next T1-T5 fire; no new site is added. Avoids the runtime-state purity break shared with F2. |
| `pull` (agent-initiated MCP refresh) | **Exclude from v1, v2 candidate** | Per composability.md §2.1 open question and §8.1 hand-off. An agent could call an MCP tool to refresh its own constraints/phase mid-turn. Out of v1 scope per Composability lead's recommendation. v2 candidate site `pull` analogous to T5 (full refresh under caller's choice). |
| Late-framing reveal (F2) | **Exclude from v1, v2 candidate** | No site exists today for "framing has shifted" updates from user_alignment. Documented as a v2 candidate site `framing-reveal`; explicitly out of v1 per composability §8.1. |

(v2 candidate sites are listed without pre-assigned numbers -- order depends on which lands first.)

## 2. Per-site invariants

Each invariant cites the failure mode (F1-F9 from `leadership_findings.md`) it prevents. Invariants are MUST -- a site that violates one is non-conformant.

### 2.0 Default segment set per site

Time-axis owns the **default segment set** each site asks for; place_axis owns the segment enum and assemblers; gating_axis evaluates the predicate over the result.

| Site | identity | phase | constraints | environment\* |
|------|----------|-------|-------------|---------------|
| T1 spawn | yes | yes | yes | (yes) |
| T2 activation | yes | yes | yes | (yes) |
| T3 phase-advance.main | no | yes | yes | no |
| T4 broadcast (typed, has phase.md) | no | yes | yes | no |
| T4 broadcast (standing-by) | no | no | yes | no |
| T5 post-compact | yes | yes | yes | (yes) |

\* **Environment column resolution (place_axis confirmed):** the environment renderer ships in v1 as a per-segment assembler `render_environment(ctx)`; the segment is **workflow-opted-in** via an `environment_segment: enabled` flag in the manifest. project_team opts in; tutorial / learner / others do not. For non-opted-in workflows, `render_environment` returns `""` and the join rule drops the empty segment -- net behavior identical to "no environment segment exists." Time-axis's default-True gate at T1/T2/T5 plus place_axis's renderer-level opt-in compose to the same observable bytes. This reconciles `spec_place_axis.md` (env as a v1 segment) with `composability.md` §2.2 (env not on by default in v1): the *renderer* is v1, the *opt-in* is per-workflow. Skeptic R5 honored (other bundled workflows unchanged).

Identity fires at T1/T2/T5 (the three "full-prompt" sites). T3 and T4 are refresh sites: they update what changed (phase + constraints) and rely on the transcript for the rest. T5 is the canonical full-refresh because `/compact` wipes the working set (F3).

### 2.1 Standing-by definition (locked for v1)

**Standing-by agent** = a spawned agent whose `agent_type != DEFAULT_ROLE` AND for whom `<workflow_dir>/<agent_type>/<bare_phase>.md` does not exist for the current phase. **Static, file-system check.** No runtime busy/idle component (skeptic R1).

This is the terminology glossary's proposed definition. Time-axis locks it for v1. If terminology renames the concept, the definition stays; only the term changes.

**T1 -- spawn**
- I1. MUST route through `assemble_agent_prompt` (single composition point). *Prevents F4/F5: divergence between this site's projection and `_filter_load_result`.*
- I2. MUST pass the merged `disabled_rules` from `_get_disabled_rules`. *Prevents F5.*
- I3. MUST refuse to inject when `agent_type` would be falsy; log WARNING and skip. *Prevents F7.*
- I4. Constraints block on empty-digest MUST be the empty string (already the contract). *Prevents F9.*

**T2 -- activation**
- I5. MUST run AFTER `agent.agent_type = wf_data.main_role` and AFTER `engine.set_loader(loader)`. *Prevents F4 on restored sessions where loader attachment was previously skipped.*
- I6. On `assemble_agent_prompt is None`, MUST log WARNING with `(workflow_id, role, phase)` and emit a one-line fallback notice. *Prevents F8 silent skip; matches existing app.py behavior.*

**T3 -- phase-advance.main**
- I7. MUST NOT double-inject when the caller is the main agent (coordinator). The tool response already carries the prompt; this site is skipped via `_update_sidebar_workflow_info()` only. *Preserves the test_advance_phase_no_double_agent_prompt_for_coordinator contract.*
- I8. MUST refresh `phase` and `constraints` segments. Identity segment refresh is OPTIONAL (already in transcript) -- defer to place_axis seam.

**T4 -- phase-advance.broadcast**
- I9. MUST iterate every agent in `agent_mgr.agents` and apply the inject predicate per-recipient. *Prevents F1: a recipient existing today is invisible to the broadcast loop only via the predicate, never via being absent from the loop.*
- I10. Recipients with `agent_type == DEFAULT_ROLE` MUST receive **constraints-only** (see §3). *Resolves F1 + Q3.*
- I11. The caller (coordinator) and the main_role agent are skipped by name/role -- not by absence-of-prompt. *Prevents F8 regression where skip-by-None-prompt also dropped the broadcast.*
- I12. `disabled_rules` MUST be computed once outside the loop and passed to every recipient. *Prevents per-recipient drift.*

**T5 -- post-compact**
- I13. **Full refresh.** MUST inject identity + phase + constraints from current engine state. *Prevents F3: post-compact is the only site that nominally guarantees the prompt and runtime are in sync.*
- I14. MUST read `loader`, `workflow_id`, `artifact_dir`, `project_root` off the engine at hook-fire time, not at hook-creation time. *Already implemented; pinned here as an invariant.*
- I15. MUST be a no-op when `assemble_agent_prompt` returns `None` -- but this no-op MUST log WARNING. *Surfaces F8 in the post-compact path.*

## 3. The broadcast question (Q3 / F1)

**Question.** When a phase-advance broadcast (T4) reaches a *standing-by agent* (glossary: a spawned agent whose role has no `<role>/<phase>.md` for the current phase), what fires?

**Recommendation.** **Constraints segment fires; phase segment does not; identity segment does not.**

**Rationale.**
- F1's root cause was that broadcast did not route through `assemble_agent_prompt` at all -- typed sub-agents missed their constraints block. The fix landed; we MUST NOT re-create it by gating broadcast on "has phase prompt content."
- Issue #27 (suppress identity at standing-by) is real but distinct: identity is already in the agent's transcript from T1, so re-injecting it on every phase-advance is redundant noise.
- The constraints block reflects (role, phase) and CHANGES on phase advance. A standing-by agent that does not receive it advertises stale rules to itself -- the precise high-cost regression in skeptic's failure-cost matrix.

**Concrete predicate (gating_axis confirmed; signature is `gate(time, place, role, phase, settings, manifest)`):**
```
gate(T4, identity,    role, phase, settings, manifest) = false   # already in transcript
gate(T4, phase,       role, phase, settings, manifest) = phase_md_exists(role, phase)
                                                          # OR: place's render_phase returns empty bytes when missing
                                                          # (place-axis seam -- gate may unconditionally fire)
gate(T4, constraints, role, phase, settings, manifest) = true    # structurally locked True (gating_axis structural_gate
                                                                  # floor, F1 regression guard -- no config can suppress)
gate(T4, environment, role, phase, settings, manifest) = false   # already in transcript (or N/A if v2)
```
A standing-by agent thus receives `constraints` only at T4 -- a non-empty, role+phase-scoped, short prompt. A typed agent with phase markdown receives `phase + constraints`.

**Wrapping.** The current `mcp.py:1040` wraps the prompt as `"--- Phase Update: {next_phase} ---\n\n{agent_prompt}"`. This wrapper MUST remain at T4 regardless of which segments fire (so the recipient can distinguish a constraints-only refresh from an idle ping).

## 3.5 Compositional-law constraints (composability.md §4, §5.1)

Time-axis design adheres to the law `inject(t, p, r) = render(p, ctx(t, r)) if gate(t, p, r) else EMPTY`:

- **Time MUST NOT leak into `render`.** `render_identity(ctx)` produces the same bytes whether called at T1, T2, or T5. The site differs only in *which* segments it asks for and *what* the gate decides; not in how a segment renders. Time-axis invariants above are expressed as the **default segment set** per site and as **gate-predicate cells**, never as render-side branching.
- **Architectural shape (composability + skeptic).** The per-time gating clauses MUST live as a single pure function next to `assemble_agent_prompt` in `claudechic/workflows/agent_folders.py`. No new module/class hierarchy. The five inject sites continue to call `assemble_agent_prompt(role, phase, loader, ...)` -- only its internals change to thread the predicate.
- **No "constraints-off" mode (R-comp-3).** Time-axis MUST NOT introduce any site whose default drops the constraints segment. (T4-broadcast-to-standing-by fires constraints-only; that is the *opposite* of constraints-off.) Issue #28 is format/scope only -- never opt-out -- per composability §8.1 ruling for gating_axis.
- **Gap: F2 (no late-framing reveal mechanism).** Documented and **out of v1**. The five sites do not include "framing has shifted" as a trigger. A v2 follow-up could add T7 = `framing-reveal` driven by user_alignment, but v1 ships without it. Cited per composability §8.1 instruction to "document F2 gap but don't fix in v1."

## 4. Behavioral changes vs status quo

**Added:**
- T4 explicit handling of standing-by recipients: today they are skipped at `agent_type == DEFAULT_ROLE` (mcp.py:1018) and silently skipped via `assemble_agent_prompt` returning `None` for missing role dir. This spec replaces both with the predicate above. **DEFAULT_ROLE recipients still skipped; non-DEFAULT-ROLE-but-no-phase-md (= "standing-by") recipients now get constraints.** This expands T4's recipient set.
- T1 invariant I3 (refuse falsy `agent_type`) is now formal. Today this is implicit via the broadcast skip but spawn does not check.
- T5 invariant I15 (WARNING on None) is added. Today the post-compact hook silently returns `{}`.

**Removed:**
- Nothing. All five sites continue to exist and continue to route through `assemble_agent_prompt`.

**Preserved:**
- Single composition point. `assemble_agent_prompt` remains the only assembly entry. Per-site code does not concat segments by hand.
- Empty-digest contract: `assemble_constraints_block` returns `""` when there are no rules and no checks; sites skip injection.
- Three-freshness-contracts substrate (F3) is NOT rewritten. T5 is the canonical refresh; T1-T4 stay spawn-time-frozen between events. Skeptic R4 honored.

## 4.5 F-number to time-axis change map (deliverable #5)

Consolidated mapping of every failure mode in `leadership_findings.md` §"Failure modes" to the specific time-axis change (or non-change) that addresses it. Time-axis owns rows tagged **TIME**; **NON-TIME** rows are flagged for sister-axis ownership and listed for completeness.

| F# | Description | Tag | Time-axis change |
|----|-------------|-----|-------------------|
| F1 | Broadcast missed `assemble_agent_prompt`; sub-agents lost constraints block | **TIME** | T4 invariants I9-I12 + §3 predicate. T4 routes every recipient through `assemble_agent_prompt`; constraints gate is structurally locked True (no config can suppress). Standing-by recipients now receive constraints-only instead of being silently skipped. |
| F2 | Late framing reveal: no "framing has shifted" injection mechanism | **TIME (deferred)** | Documented gap (§3.5). v2 candidate site `framing-reveal`. v1 explicitly out-of-scope per composability §8.1. The five-site enumeration MUST NOT silently absorb F2 into an existing site. |
| F3 | Three coexisting freshness contracts (spawn-freeze / per-call / post-compact) | **TIME** | T5 invariant I13 locks post-compact as canonical full refresh; §4 "Preserved" point honors skeptic R4 by NOT rewriting the substrate. T1-T4 stay spawn-time-frozen between events; T5 is the only refresh. Documented, not "fixed." |
| F4 | Source-of-truth divergence: hooks vs registry/MCP read different projections | NON-TIME (place_axis / gating_axis) | T2 invariant I5 (loader attached before activation fires) is the time-axis contribution. Underlying `_LoaderAdapter` alignment is place/gating concern. |
| F5 | `mcp.py` disabled_rules unwired at 4 sites | **TIME** | T1 invariant I2 (spawn MUST pass merged `disabled_rules`); T4 invariant I12 (broadcast computes once, threads to every recipient). Locks the seam at every time-axis site. |
| F6 | `get_phase` overstated active rules (namespace-only filter) | NON-TIME (gating_axis / MCP surface) | Not a time-axis concern. `get_phase` is an MCP query, not an injection site. Listed for completeness. |
| F7 | Falsy check on `agent.agent_type` routed broadcast to default-roled agents | **TIME** | T1 invariant I3 (refuse falsy at spawn); T4 invariant I11 (skip by name/role, not by None-prompt). Closes the regression class at both ingress and broadcast sites. |
| F8 | `assemble_agent_prompt` returns `None` for default-roled agents (#27 precursor) | NON-TIME (place_axis + gating_axis) | T2/T5 invariants I6/I15 add WARNING surfacing so silent skips become visible. The empty-prompt semantics itself is a place_axis (segment composition) and gating_axis (#27) concern. |
| F9 | Empty-digest 138-char placeholder noise (#27 precursor) | NON-TIME (place_axis) | T1 invariant I4 cites the empty-string contract for the constraints assembler. Time-axis depends on it; place_axis owns it. |

**Reading guide:** TIME rows are the time-axis deliverable. NON-TIME rows show where the time-axis spec interlocks with sister axes -- a time-axis invariant exists in each NON-TIME row precisely to pin the seam, but the underlying fix lives elsewhere.

## 4.6 Time-axis half of `inject(time, place, role)` (deliverable #6)

The compositional law is `inject(t, p, r) = render(p, ctx(t, r)) if gate(t, p, r) else EMPTY`. Time-axis fixes the **`t`** dimension to the closed enum:

```
Time = { T1_spawn, T2_activation, T3_phase_advance_main,
         T4_phase_advance_broadcast, T5_post_compact }
```

Time-axis contributes three structural commitments to the predicate:

1. **Default segment set per `t`** -- §2.0 table. Time decides *which* segments are even candidates at site `t` (e.g. T3 never asks for identity).
2. **Per-`t` invariants** -- §2 I1-I15. Time decides *what must be true at the call site* before `gate(t, p, r)` is consulted (loader attached, role promoted, disabled_rules merged once).
3. **Closed enumeration** -- the five-site list is closed for v1. New time values (e.g. `T6_chicsession_resume`, `T7_framing_reveal`, `T8_pull`) MUST land via the documented v2 candidate path; they MUST NOT be silently absorbed into T1-T5 by stretching an existing site's semantics.

Place-axis contributes the segment enum + render functions. Gating-axis contributes the suppression configuration surface and evaluates `gate(t, p, r)` as a pure function over `(t, p, r, phase, settings, manifest)`. The three axes compose by construction: every `(t, p, r)` cell has exactly one render path, exactly one gate path, and exactly one site of invocation.

## 5. Coordination notes (cross-axis couplings)

- **place_axis (mostly aligned; one open item).** Aligned via `spec_place_axis.md` on the segment-set-as-seam pattern: place owns the segment enum and per-segment assemblers; time-axis owns the default segment set per site (§2.0); the seam is `segments_to_inject: set[Segment]` filtered before composition. **Open: environment-as-v1-segment.** place_axis says yes; composability §2.2 says v2. Time-axis is neutral; coordinator decides. Either way the time-axis invariants below stand.
- **gating_axis (resolved).** Predicate signature locked: `gate(time, place, role, phase, settings, manifest) -> bool` over the closed time enum {T1..T5} and the closed segment enum. Hard pins from `spec_gating_axis.md` honored: T5 never suppressible; (T4, constraints) structurally locked True; #27 default suppress = {T3, T4}; T1/T2/T5 never suppress identity. Per-segment granularity in `gating: { suppress: [{segment, roles, times}] }` makes my I8 (T3 phase-only) and I10 (T4 constraints-only) first-class. Time-axis and gating-axis specs are cross-checked consistent.
- **role_axis.** "Standing-by" is defined per-role: a role with no `coordinator/specification.md` is standing-by *for that phase*. Role_axis's per-role audit determines how many cells of the 15-roles x N-phases grid are standing-by. T4 invariant I10 fires for every standing-by cell -- so the constraints projection MUST be cheap. **Soft coupling.**
- **terminology.** This spec uses *injection site*, *prompt segment*, *standing-by agent*, *constraints segment* per the proposed glossary. If the glossary lands different terms, I'll rename verbatim.
- **skeptic.** Excluded `chicsession-resume` candidate (§1) is a v2 surface. Recommend skeptic's `failure_mode_map.md` add a row "F3 / chicsession resume = stale launch prompt" linking to a v2 follow-up issue.

---

## Appendix candidates

(Coordinator: lift into SPEC_APPENDIX.md as needed. Not part of the operational spec.)

- **Why five sites and not four?** Pre-b106cff, T4 (broadcast) did not exist as a constraints-injecting site -- F1. The fifth site is a fix, not an addition by symmetry.
- **Why post-compact is the canonical refresh.** SDK `PostCompact` is the only event whose semantics promise "the agent's working set was just rebuilt." Any other "freshness" site (settings-change, model-swap) lacks that contract.
- **Rejected: a settings-change inject site.** Considered for `disabled_ids` mid-run edits. Rejected for v1 because (a) no UI today triggers a mid-run settings change without a restart, and (b) gating-axis can fold it into the predicate later without changing the time-axis enumeration.
- **Rejected: collapsing T2 and T1.** Activation (T2) of a fresh main agent looks similar to spawn (T1), but the recipient differs (existing main agent vs newly-created sub-agent), the kickoff-prompt-is-the-prompt contract differs, and the role-promotion ordering differs. Keeping them distinct preserves the per-site invariant table.
