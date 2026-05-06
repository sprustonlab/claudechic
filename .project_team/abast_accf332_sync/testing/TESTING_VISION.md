# Testing Vision -- abast_accf332_sync

**Run:** `abast_accf332_sync`
**Coordinator:** claudechic
**Phase:** project-team:testing-vision (consolidating Leadership input)
**Implementation commit:** `b106cff` (2050+/-448 across 27 files)
**Date:** 2026-05-01

This document consolidates the team-level draft + 4 leadership-axis memos into the binding Testing Vision Summary. Per-axis memos live alongside this file (`composability.md`, `terminology.md`, `skeptic.md`, `user_alignment.md`).

---

## Reading guide (for testers landing cold)

If you have not read `SPEC.md`, start here. Every reference below is also expanded inline on first use later in the document.

### What we shipped

The agent self-awareness substrate makes each agent (main and sub-agents) know its own paths, role, effort budget, and the rules + advance-checks that apply to it. Six components shipped together; four are the user-named features, two are stowaways the team added during scoping.

| ID | User-locked feature label | Plain-English what-it-is |
|---|---|---|
| **A** | workflow template variables | A `${WORKFLOW_ROOT}` token that resolves to the main agent's cwd, plus engine-cwd defaulting for advance-checks, plus a two-pass auto-then-manual check execution order. |
| **B** | dynamic roles | A live `agent.agent_type` attribute that flips to the workflow's `main_role` on activation and reverts to `"default"` on deactivation, surviving `/compact`. Replaces the old manifest-bound role lookup. |
| **C** | effort cycling | A footer label showing "effort: low/medium/high/max" that cycles on click and persists. `"max"` is Opus-only; non-Opus models snap to `"medium"`. |
| **D** | guardrails UI (reframed) | NOT a modal. A `## Constraints` markdown block injected into every agent's launch prompt listing the rules + advance-checks scoped to its (role, phase), plus 4 narrow MCP tools (`whoami`, `get_phase`, `get_applicable_rules`, `get_agent_info`) the agent can call mid-session. |
| **E** | (stowaway) `pytest_needs_timeout` warn rule | A new global guardrail rule that warns when `pytest` runs without `--timeout`. |
| **F** | (stowaway) diagnostics-modal absorption | The old `DiagnosticsModal` is deleted; its session-JSONL + last-compaction readers move into `ComputerInfoModal` so the footer "info" button shows everything in one scrollable modal. |

### Sub-unit notation

Each component is broken into sub-units written `<letter><digit>`. They appear in tables and dependency lists; in running prose this document expands them inline. The ones that recur most often:

| Sub-unit | What it is |
|---|---|
| **A1** | the `${WORKFLOW_ROOT}` token + braced-syntax convergence |
| **A3** | engine-cwd defaulting for advance-check commands (`params.setdefault("cwd", workflow_root)`) |
| **A4** | the two-pass auto-then-manual check executor |
| **B1** | the `DEFAULT_ROLE = "default"` sentinel constant in `agent.py` |
| **B2** | the `Agent.agent_type` instance attribute |
| **B3** | the role-promote-on-activation / revert-on-deactivation insertion in `app.py` |
| **B4** | the hook-closure swap from manifest-bound to `lambda: agent.agent_type` |
| **B5** | the loader rejecting manifests where `main_role: default` |
| **C1** | the `Agent.effort` attribute plumbed into `ClaudeAgentOptions` |
| **C2** | the `EffortLabel` footer widget |
| **C3** | persistence of effort to user-tier config (so it survives restart) |
| **D1** | `compute_digest` -- rules data projection |
| **D2** | `compute_advance_checks_digest` -- advance-checks data projection |
| **D3** | `assemble_constraints_block` -- the markdown formatter |
| **D4** | the 4-narrow-MCP-tool surface (whoami / get_phase / get_applicable_rules / get_agent_info) |
| **D5** | the 5 prompt-injection sites that wire D3 into agent prompts |
| **D6** | source-of-truth alignment so the hook layer and the registry layer (MCP / prompt) all see the same filtered rule set |

### The four parallel layers (the cross-layer convergence story)

Component D ships the same "what rules apply to me" answer through four code paths. The biggest risk this run is they silently disagree.

1. **Hook layer** -- `claudechic/guardrails/hooks.py` reads rules and fires `deny`/`warn`/`log` on tool calls.
2. **MCP `get_applicable_rules`** -- on-demand markdown projection an agent can call mid-session.
3. **MCP `get_agent_info`** -- aggregator that includes the projection alongside identity/session/phase/loader info.
4. **Injected `## Constraints` block** -- baked into the launch prompt at the 5 inject sites listed below.

The keystone test (§"Cross-layer assertion" below) pins the four layers to the same source. If that test breaks, all four layers silently drift.

### The five prompt-injection sites (sub-unit D5)

In running prose this document refers to "the 5 inject sites." They are:

1. **activation** -- main agent gets its first phase prompt when a workflow is activated (`app.py::_activate_workflow`).
2. **spawn** -- sub-agent gets its prompt at MCP `spawn_agent` time (`mcp.py::_make_spawn_agent`).
3. **phase-advance** -- main agent gets the new phase prompt when it advances (`app.py::_inject_phase_prompt_to_main_agent`).
4. **broadcast** -- typed sub-agents receive the new phase prompt when the main agent advances (`mcp.py::_make_advance_phase` broadcast loop).
5. **post-compact** -- any agent re-receives its (role, phase) prompt after `/compact` (`workflows/agent_folders.py::create_post_compact_hook`).

All five route through the single helper `assemble_agent_prompt` so the composition is in one place.

### Common shorthand used elsewhere

| Term | Meaning |
|---|---|
| **slot review** | a per-implementer review pass during the implementation phase (6 slots: agent, engine, guardrails+mcp, app, widgets, data+docs) |
| **must-fix** | a defect found in a slot review that must land before sign-off; numbered M1, M4, etc. by skeptic |
| **stowaway** | a component the team added during scoping that the user did not name in the original 4 features (currently: E and F) |
| **gestalt assertion** | a test that proves the user-visible OR agent-visible *whole* of a feature works, not just one of its parts in isolation |
| **axis pair** | a contract between two leadership-axis specs (e.g. B touches A's engine seam; "B<->A axis pair" is the test that pins their interface) |
| **keystone test** | the single cross-layer assertion that, if it ever breaks, surfaces silent drift across all four parallel D layers |

---

## Goal

Verify the agent self-awareness substrate (commit `b106cff`) works end-to-end before sign-off. The implementation has shipped; testing must confirm the four parallel projections of "what rules apply to me" -- the hook layer, MCP `get_applicable_rules`, MCP `get_agent_info`, and the injected `## Constraints` block -- all agree, and that the agent-side experience (paths, role, effort, rules) actually fires at runtime.

## Value

- **Catch silent runtime bugs** that inspection cannot prove: hook closures that bind too early, mutations that never reach observers, prompt content that does not survive `/compact`, layers that read from different sources of truth, regex rules that fire on documentation, snap-down behavior that misfires when models change.
- **Establish a baseline** that subsequent abast follow-ups (e.g., the `003408a` re-pick) can be measured against.
- **Cross-layer divergence is the dominant risk now** (per skeptic): each of the four D layers can pass in isolation while the layers disagree with each other. Tests that span two or more layers are therefore the highest-value shape this run.

## Success criteria

### Functional gates (coordinator-owned)

1. **Full pytest suite passes**: `TS=$(date -u +%Y-%m-%d_%H%M%S) && pytest --junitxml=.test_results/${TS}.xml --tb=short --timeout=30 2>&1 | tee .test_results/${TS}.log`

2. **Mid-session role flip works live (Component B: dynamic roles).** Smoke check via remote control: activate a workflow -> confirm the active agent's role flipped (call `mcp__chic__get_agent_info`, see the promoted role under `## Identity`) -> deactivate -> confirm the role reverted to `"default"` -> run `/compact` -> confirm the role survives. This exercises the role-promote/revert insertion (sub-unit B3) plus the live hook-closure binding (sub-unit B4) end-to-end.

3. **All five prompt-injection sites fire correctly (Component D, sub-unit D5).** The agent's launch prompt at each of the five sites -- main-agent activation, sub-agent spawn, main-agent phase-advance, sub-agent phase-advance broadcast, and post-compact re-injection -- contains the `## Constraints` markdown block. (The 5-site list lives in the Reading guide above and matches SPEC Decision 4.)

4. **The new `pytest_needs_timeout` warn rule (Component E) fires on real `pytest` invocations and does NOT fire on documentation/grep/cat false-positives.** Validate against two regex test sets: the 27-case set the implementer (`impl_data_docs`) shipped, and skeptic's expanded 44-case set from the slot-6 review. Both must pass.

5. **The unified `ComputerInfoModal` shows real session data (Component F: diagnostics-modal absorption).** Clicking the footer "info" button opens the modal with a populated Session JSONL row and a populated Last Compaction section -- both reading the active agent's session id. (This was the post-slot-4 cross-implementer fix that wired `session_id=agent.session_id` into the modal call site.)

6. **Zero new test regressions vs `b106cff`'s parent**: diff test counts; flag any new failure not present at the parent commit.

### Architectural gates (composability-owned)

7. **Six seam-protocol tests** -- one per axis pair listed in `composability.md`. An "axis pair" is the contract between two leadership axes; if either axis changes its half of the contract independently, the seam test fails. The six pairs are: dynamic-roles touching workflow-template-variables (B<->A), effort-cycling reading dynamic-roles (C<->B), the rules data projection meeting the markdown formatter (D-projection<->D-render), the markdown formatter meeting the inject sites (D-render<->D-inject), the MCP surface meeting the markdown formatter (D-mcp<->D-render), and the diagnostics-modal absorption seam (F seam).

8. **Crystal-point sweep (10 representative test points)** covering every dimension that can branch behavior: workflow active vs not, main agent vs sub-agent, effort `low / medium / high / max`, Opus vs non-Opus snap, rule-disabled vs not, post-compact survival, deactivation revert, and the broadcast site firing on phase advance.

9. **Single-composition-point lint**: zero hand-rolled `f"{phase_prompt}\n\n{constraints_block}"` outside `assemble_agent_prompt`; zero direct `compute_digest` calls outside the constraints-block formatter, the MCP tools, and the inject sites. Anything else is a parallel composition path that breaks the convergence story.

10. **Source-of-truth lint**: pin the equivalence

    ```
    _LoaderAdapter(lambda: app._load_result, app._manifest_loader).load()
      ==
    _filter_load_result(app._manifest_loader.load(), app._project_config, app._config)
    ```

    so a regression in `_filter_load_result` cannot silently restore the source-of-truth bug class that sub-unit D6 was created to kill.

### User-intent gates (user_alignment, two-axis gestalt rule)

The user_alignment memo's "two-axis gestalt rule" is binding for this run: every component verified by testing must have **both** a user-side gestalt assertion (the user can see/use the feature working) **and** an agent-side gestalt assertion (the agent receives/exercises the feature) -- except where the SPEC explicitly says one side is N/A (Component F has no agent-side: agents do not consult read-only modals).

11. Each user-named feature (workflow template variables / dynamic roles / effort cycling / guardrails UI -- A, B, C, D) plus each stowaway (E, F) is verified with both a user-side gestalt assertion and an agent-side gestalt assertion, except where the SPEC explicitly marks a side N/A.

12. **Reframing fidelity for guardrails UI (Component D).** No modal, no `_disabled_rules` runtime in-memory store, no `GuardrailsLabel` in the footer. The `## Constraints` block plus the 4 narrow MCP tools are the canonical D surface. (The SPEC reframing of Component D from a modal to agent-aware constraint visibility is binding; tests must not introduce assertions that assume the original modal exists.)

### Terminology gates (terminology-owned)

13. **Test names locatable by SPEC component letter**: every test maps to A/B/C/D/E/F + sub-unit. A reviewer cold-reading the test suite can find the SPEC component without grepping. (Convention is `test_<component_letter><sub_unit>_<concept>_<expectation>`; full list in `terminology.md`.)

14. **Required contract strings asserted verbatim** -- not paraphrased: `## Constraints`, `### Rules ({n_active} active)`, `effort: {level}`, `CLAUDE_AGENT_ROLE`, `${WORKFLOW_ROOT}`, and the 4 MCP tool names (`whoami`, `get_phase`, `get_applicable_rules`, `get_agent_info`).

15. **Five-site inject vocabulary**: tests describe the inject sites as `activation / spawn / phase-advance / broadcast / post-compact`, not the older 3-site or 4-site naming that drifts in some pre-implementation comments.

## Failure looks like

- Tests fail -> fix until green. (Test fixes for tests our implementation legitimately broke are in scope here.)
- The role-promote/revert insertion plus the hook-closure swap (sub-units B3 + B4) fail to make the main agent's role visibly flip mid-session -> must-fix.
- Any of the five prompt-injection sites silently skips the `## Constraints` block (a "D5 silent gap") -> must-fix.
- The `pytest_needs_timeout` warn rule (Component E) false-positives on documented commands like `grep -c "pytest"` -> must-fix.
- Cross-layer divergence: the injected `## Constraints` block reports rules that the hook layer does not fire on, or vice versa -> must-fix.
- The pre-existing `test_agent_switch_keybinding` flake -> tracked, not fixed (not a regression introduced by this run).

## Explicitly out of scope

- Performance benchmarking / load testing.
- Cross-platform CI runs (claudechic CI handles).
- Integration with non-claudechic external tools.
- New tests for code paths outside the abast/`accf332` cluster scope.
- Re-running v1/v2 leadership review on testing artifacts.

## Pre-existing context

- All cross-implementer must-fixes from the slot reviews are LANDED in `b106cff` (skeptic verified by grep). In particular, the two open bugs flagged at the end of the implementation phase are now closed:
  - The `_get_disabled_rules` helper is now actually called from `mcp.py` so the MCP digest tools project against the same disabled-rule set as the inject sites.
  - The handler that opens the unified Info modal now forwards `session_id=agent.session_id` so Session JSONL and Last Compaction render real data.
- The four `test_get_phase_*` tests that broke when `get_phase` lost its rule-count line (skeptic must-fix #4 from the slot-3 review) have been migrated by `impl_data_docs` and now pass under their renamed siblings in `tests/test_artifact_dir.py` (`test_get_applicable_rules_filters_*`, `test_get_phase_omits_rule_count_line`, `test_get_phase_no_engine_reports_none_active`).
- `pytest-timeout==2.4.0` and `ruff>=0.9.0` are now declared in `pyproject.toml` dev deps.

## Cross-layer assertion (the keystone test, skeptic-mandated)

One test pins the equivalence

```
_LoaderAdapter(lambda: app._load_result, app._manifest_loader).load()
  ==
_filter_load_result(app._manifest_loader.load(), app._project_config, app._config)
```

If this assertion ever breaks, the four downstream projections (hook layer, MCP `get_applicable_rules`, MCP `get_agent_info`, and the injected `## Constraints` block) silently drift. This is the "if everything else is broken, this one tells us first" test for the run.

## Per-axis memo cross-references

| Memo | Path | Key contributions |
|------|------|-------------------|
| Composability | `testing/composability.md` | The six seam-protocol tests, the 10-point crystal sweep, axis isolation guidance, "composability-as-lint" patterns |
| Skeptic | `testing/skeptic.md` | Skeptic's six review questions adapted for testing, slot must-fix verification, seven silent-regression scenarios, the failure-cost matrix |
| Terminology | `testing/terminology.md` | Test naming convention, forbidden synonyms, required contract strings, the four-step newcomer pre-merge test |
| UserAlignment | `testing/user_alignment.md` | The two-axis gestalt grid, six cross-feature user-intent failure modes, reframing fidelity for guardrails UI, the final-report contract reminder |

## Sign-off bar (skeptic + composability + user_alignment converged)

To exit testing-implementation with a passing verdict:

1. Criteria 1-15 above all met.
2. The cross-layer keystone assertion test passes.
3. The live remote-control mid-session role-flip smoke check (criterion 2) passes.
4. Every HIGH-row regression in skeptic's failure-cost matrix is covered by at least one test.
5. No silent feature drop -- the user_alignment per-feature audit is clean.
6. No new stowaway code -- the user_alignment scope-guard re-verification is clean.

If any of these are unmet at testing-implementation exit, slot back to fix-up before sign-off.
