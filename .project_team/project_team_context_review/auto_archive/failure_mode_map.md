# Failure-Mode Map -- project_team_context_review

**Phase:** project-team:specification
**Co-owners:** Skeptic (drafted), UserAlignment (drift sweep)
**Source of failure modes:** `abast_accf332_sync/` (prior project_team run); classified by Skeptic in `leadership_findings.md` §"Failure modes from `abast_accf332_sync`".

This file is the binding map between each prior-run failure (F1-F9) and its fate in this run's spec. **Every F-number has a row. No silent omissions.**

## Fate vocabulary

- **`closed-by-spec`** -- the spec's design structurally prevents recurrence. The regression is unreachable by any valid configuration. Cell carries a regression-guard citation.
- **`pre-existing-fix`** -- the prior run (`abast_accf332_sync`) already shipped the fix. This run does not regress it. Cell carries the keystone-test or non-regression citation.
- **`accepted-risk`** -- the failure mode is acknowledged, mitigated, but not structurally eliminated. Cell names the mitigation and the residual risk.
- **`out-of-v1`** -- explicitly deferred to a v2 / follow-up. Cell names the rationale.

## Map

| F# | Description | Owner axis spec | Fate | Spec section / regression-guard |
|----|-------------|-----------------|------|----------------------------------|
| F1 | Phase-advance broadcast didn't route through `assemble_agent_prompt`; sub-agents missed the constraints segment on broadcast. | gating + time | **closed-by-spec** | `spec_gating_axis.md` §6 row F1: `structural_gate` floor pins `place == "constraints" AND time == "phase-advance-broadcast"` -> always True. No YAML key, no settings key can suppress it. `spec_time_axis.md` §1 includes phase-advance-broadcast as a v1 inject site (T4). |
| F2 | Late framing reveal: UserAlignment's reframe arrived after axis-agents had verdicted on the wrong frame; no mechanism for "framing has shifted". | (none -- workflow-coordination concern) | **out-of-v1** | `spec_gating_axis.md` §6 final paragraph: F2 belongs to a process/coordination layer (Leadership review cadence, mid-phase user checkpoints), not a (time, place, role) cell. Encoding "framing dirty" requires runtime state that breaks predicate purity. Revisit in v2 only if a static gating signal can encode it. |
| F3 | Three coexisting freshness contracts (spawn-time freeze / per-call live / post-compact refresh) -- agent has no consistent answer to "is what I'm reading current?" | time | **accepted-risk** | `spec_time_axis.md` §"Why post-compact is the canonical refresh": the substrate is NOT rewritten (Skeptic R4 honored: clean rewrite is a regression vector). T5 (post-compact) is named as the canonical full-refresh; T1-T4 stay spawn-time-frozen between events. **Residual risk:** chicsession-resume can replay a stale launch prompt if a constraints-format change landed in between. Mitigation: chicsession-resume is named as a v2 candidate inject site that would re-inject under post-compact invariants. **Concrete v2 follow-up:** open issue "F3 / chicsession resume = stale launch prompt -- promote chicsession-resume to inject site under post-compact invariants" (`spec_time_axis.md` §1, §"coordination notes"). |
| F4 | Source-of-truth divergence: hooks read raw `loader.load()`; registry/MCP read filtered `_load_result`. Same context, two answers. | gating | **pre-existing-fix** | Fixed in `abast_accf332_sync` via `_LoaderAdapter` shim + `_filter_load_result` projection (`abast_accf332_sync/STATUS.md` composability landing condition #1; SPEC §"Source-of-Truth Alignment"). `spec_gating_axis.md` §6 row F4 makes the keystone test (`abast_accf332_sync/testing/skeptic.md` §"Cross-layer assertion") binding for any new code path that reads rules/checks: gate predicate reads `manifest` + `settings` only; neither exposes a path bypassing `_LoaderAdapter`. **Non-regression boundary citation: keystone test (binding).** |
| F5 | `mcp.py` disabled_rules unwired at 4 sites -- project disable list never reached the constraints projection. | gating | **pre-existing-fix** | Fixed in `abast_accf332_sync` (M4 in slot 4 review; `b106cff` added `parse_disable_entries` + `_get_disabled_rules` at 4 sites). `spec_gating_axis.md` §6 row F5: `#28` settings layer does NOT expose a `disabled_rules` knob; existing `disabled_ids` retains the single source of truth. The constraints segment is rendered by the existing `assemble_constraints_block` -- no parallel rendering path. **Non-regression boundary: keystone test (shared with F4).** |
| F6 | `get_phase` overstated active rules: namespace filter only, not role/phase. Agent's self-query lied about its scope. | (pre-existing-fix in prior run) | **pre-existing-fix** | Fixed in `abast_accf332_sync` via the D-component substrate: `get_applicable_rules` and `get_agent_info` (the new MCP tools that replaced/supplemented `get_phase`) DO filter by role+phase via `compute_digest`. `abast_accf332_sync/STATUS.md` §"D5 / D-locked" decisions; SPEC §D component. `spec_gating_axis.md` §6 closing paragraph: predicate purity rules out runtime state queries that caused F6 -- this axis adds no risk of recurrence. **No new code in this run reads rules outside the existing projection;** any new MCP-tool surface added by gating is forbidden. |
| F7 | Falsy check on `agent.agent_type` (`mcp.py:983`) -- broadcast routed to default-roled agents incorrectly. | gating | **pre-existing-fix + structural reinforcement** | Fixed in `abast_accf332_sync` (M1; uses `== DEFAULT_ROLE`). `spec_gating_axis.md` §6 row F7 reinforces structurally: predicate explicitly accepts `role: str` and treats `"default"` as a legal value. `role == "default"` participates in gating like any other role; no falsy-string short-circuit is reachable from the predicate signature. |
| F8 | `assemble_agent_prompt` returned `None` for default-roled agents with no role dir; SPEC §D said "every agent's launch prompt", impl skipped. **Direct precursor to issue #27.** | gating + place | **closed-by-spec** | `spec_gating_axis.md` §6 row F8: place-axis returns empty per place, never short-circuits whole-prompt to `None`. `gate(time, "constraints", "default", ...)` follows the structural floor -- the constraints segment is rendered for default-roled agents whenever any global-namespace rule applies. `spec_place_axis.md` (per place rendering): identity / phase / constraints / environment are independent renderers; absent identity does not suppress constraints. |
| F9 | Empty-digest emitted 138-char placeholder ("## Constraints / _no rules apply..._" boilerplate) -- standing-by agents got noise in every prompt. **Direct precursor to issue #27.** | gating + place | **closed-by-spec** | `spec_gating_axis.md` §6 row F9: empty-digest renderer returns `""` (sec 1 of `assemble_constraints_block`); predicate output is a bool gate over a renderer that can return empty bytes, so empty-digest cells emit EMPTY by composition law -- no placeholder. `spec_gating_axis.md` §1a default-cell behavior table makes the empty-string contract explicit at the gate boundary. |

## Coverage check

- **9 F-numbers cited in `leadership_findings.md` -> 9 rows.**
- **No "TBD" fates.** Every row commits.
- **`closed-by-spec`:** F1, F8, F9 (3 rows). Each cites a structural regression guard.
- **`pre-existing-fix`:** F4, F5, F6, F7 (4 rows). Each cites the keystone test or the prior-run fix that this run does not regress.
- **`accepted-risk`:** F3 (1 row). Mitigation named (T5 canonical refresh); residual risk named (chicsession-resume); v2 follow-up named.
- **`out-of-v1`:** F2 (1 row). Rationale named (workflow-coordination, not (time, place, role)).

## Drift watch (UserAlignment to sweep)

UserAlignment's drift watch-list (leadership_findings §"User-protected priorities") flagged:
- **"Failure modes cited decoratively without driving changes."** -- THIS file is the anti-decoration artifact. Every F-number drives a specific spec section or non-regression citation.
- **"Token thrift / contrast-based framing."** -- not used here. No "fewer tokens", no "vs the prior run". Each row is grounded in code-level specifics.
- **"Quietly re-narrowing 'regardless of workflow' to project_team only."** -- not relevant to F-numbers (F-numbers are workflow-agnostic by construction; `structural_gate` operates over `(time, place, role)` independent of workflow_id).

UserAlignment: please sweep for any phrasing that backslides on the user's protected priorities, then countersign by appending a `## UserAlignment sweep` section below.

## Locked invariants surfaced by this map

- **Keystone test is binding** (`abast_accf332_sync/testing/skeptic.md` §"Cross-layer assertion"). Any axis spec that reads rules/checks must route through the existing projection or the test fails. Cited by F4, F5, F6.
- **`structural_gate` floor is unreachable from configuration.** Cited by F1, F7, F8, F9.
- **Empty-string segment contract** (renderer returns `""` rather than placeholder). Cited by F8, F9.
- **`get_phase` is closed; no new MCP rule-reading surface.** Cited by F6.

## Open coordination items

1. **Time-axis** -- confirm chicsession-resume is recorded as a v2 candidate inject site under post-compact invariants. (F3 mitigation note.)
2. **Gating-axis** -- confirm `structural_gate` documents F1/F7/F8/F9 as floor cases that no `disable: [...]` YAML or settings key can override. Already done in §6; this map cites it.
3. **Place-axis** -- confirm the four renderers (identity / phase / constraints / environment) each return `""` rather than placeholder text on empty input. (F8/F9 boundary.)
4. **UserAlignment** -- sweep for drift; countersign.

## Status

Drafted by Skeptic. UserAlignment sweep complete (see below).

---

## UserAlignment sweep

**Reviewer:** UserAlignment
**Verdict:** [OK] **ALIGNED** with v4 vision and the user-protected priorities. No required edits. Two suggested rephrasings for affirmative framing, and one cross-link the spec authors should make explicit elsewhere.

### Sweep results

| Drift watch item | Result | Notes |
|------------------|--------|-------|
| Token-thrift framing | [OK] None present | F9 row says "noise in every prompt" -- this describes the prior-run behavior of an empty-digest placeholder appearing in standing-by prompts; not a token-cost argument. Justification is signal/team-dynamics, not bytes. |
| Contrast-based framing ("vs the prior run", "fewer tokens") | [OK] None present in the comparative sense | The map has structural-invariant phrasing ("no YAML key can suppress it", "no parallel rendering path") which is *negative-form invariant*, distinct from contrast-with-prior-run. Acceptable in a regression map -- see "Suggested rephrasings" below for soft polish. |
| Failure modes cited decoratively without driving changes | [OK] Every row drives a change | F1->T4+structural floor; F2->explicit out-of-v1 with rationale; F3->T5 canonical refresh + v2 follow-up; F4/F5/F6->keystone test binding + non-regression boundary; F7->predicate signature reinforcement; F8/F9->per-place renderer + empty-string contract. No row is decorative. |
| Quiet re-narrowing of "regardless of workflow" | [OK] Preserved | Drift-watch line states explicitly: "F-numbers are workflow-agnostic by construction; `structural_gate` operates over `(time, place, role)` independent of `workflow_id`." This is the right place to assert it for the gate predicate. (Note: the user's "regardless of workflow" requirement separately applies to the **environment segment** at spawn -- that belongs in `spec_place_axis.md`, not here. Cross-link in §"Open coordination items" recommended -- see below.) |
| Issue #28 scope (format-only vs opt-out) | [OK] Honored | F5 row: "the `#28` settings layer does NOT expose a `disabled_rules` knob; existing `disabled_ids` retains the single source of truth." Matches Skeptic R2 and the hard requirement in `specification/user_alignment.md` §5.8. |
| Identity authority preservation (Skeptic R3) | [OK] Not weakened | F8's per-place renderer split makes identity / phase / constraints / environment independently gated. Identity segment content itself is unchanged by this map. Authority statements remain in their files. |
| Issue #27 precursors closed | [OK] | F8 and F9 both `closed-by-spec` with structural regression guards. |
| Failure modes traced to user quote OR `F#` | n/a (this map IS the trace) | -- |

### Suggested rephrasings (soft -- not required for sign-off)

These convert structural-invariant statements from negative-form to affirmative-form, in line with the user's *"Don't frame things by what they are not"* style note. Optional polish for spec authors when these phrases get lifted into SPEC.md.

| Current phrasing | Suggested affirmative form |
|------------------|----------------------------|
| F1: "No YAML key, no settings key can suppress it." | "Every valid YAML or settings configuration leaves the gate True." |
| F4: "neither exposes a path bypassing `_LoaderAdapter`" | "Both routes pass exclusively through `_LoaderAdapter`." |
| F5: "no parallel rendering path" | "The existing `assemble_constraints_block` is the sole rendering path." |
| F8: "never short-circuits whole-prompt to `None`" | "Always returns an assembled prompt; absent segments render as empty bytes." |
| F9: "no placeholder" | "Empty-digest cells emit empty bytes by composition law." |
| F7: "no falsy-string short-circuit is reachable from the predicate signature" | "The predicate signature treats `role` as a string with `'default'` as a legal value, so `'default'` participates in gating like any other role." |

These rewrites are stylistic, not substantive. The map can ship as-is; spec authors can pick this up when promoting these statements into SPEC.md headlines.

### Cross-link to surface elsewhere (not edits to this file)

1. **F2 ("late framing reveal") and the user's "review and suggest at all phases" requirement.**
   F2 is correctly out-of-v1 for the gating predicate -- it is a workflow-coordination concern, not a `(time, place, role)` cell. However, the user's third explicit requirement -- *"agents to also review and suggest the content of injections at all phases"* -- is itself a workflow-coordination mechanism that, if implemented, would attack the same root as F2 (no mechanism for "framing has shifted").
   **Recommendation:** the spec authors should note in `SPEC.md` (workflow-coordination section, when it lands) that the review-and-suggest mechanism is the v1 partial answer to F2's class of failure, even though F2 itself is `out-of-v1` from the gating perspective. Do not add this cross-link to `failure_mode_map.md` -- this map is bounded to (time, place, role); the cross-link belongs in SPEC.md.

2. **"Regardless of workflow" for the environment segment.**
   This map's drift-watch line preserves workflow-agnosticism for the **gate predicate**. The user's "regardless of workflow" requirement separately governs **what the environment segment delivers at spawn**. That requirement is in scope for `spec_place_axis.md`, not this file. Surface as an open coordination item if `spec_place_axis.md` has not yet pinned it.

### Sign-off

UserAlignment countersigns. The map is the anti-decoration artifact the drift watch-list called for. Ship as-is or with the optional rephrasings; either way it satisfies the user-protected priorities for this phase.
