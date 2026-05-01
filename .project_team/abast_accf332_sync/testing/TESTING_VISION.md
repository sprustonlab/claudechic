# Testing Vision -- abast_accf332_sync

**Run:** `abast_accf332_sync`
**Coordinator:** claudechic
**Phase:** project-team:testing-vision (consolidating Leadership input)
**Implementation commit:** `b106cff` (2050+/-448 across 27 files)
**Date:** 2026-05-01

This document consolidates the team-level draft + 4 leadership-axis memos into the binding Testing Vision Summary. Per-axis memos live alongside this file (`composability.md`, `terminology.md`, `skeptic.md`, `user_alignment.md`).

---

## Goal

Verify the agent self-awareness substrate (commit `b106cff`) works end-to-end before sign-off. The implementation has shipped; testing must confirm the four parallel projections of "what rules apply to me" -- hook layer, MCP `get_applicable_rules`, MCP `get_agent_info`, and the injected `## Constraints` block -- all agree, and that the agent-side gestalts (paths/role/effort/rules) actually fire at runtime.

## Value

- **Catch silent runtime bugs** that inspection can't prove (closure binding, mutation visibility, /compact survival, source-of-truth alignment, regex coverage, model-snap behavior).
- **Establish a baseline** that subsequent abast follow-ups (003408a re-pick) can be measured against.
- **Cross-layer divergence** is the dominant risk now (skeptic): each layer can pass in isolation while the layers disagree. Cross-layer assertions are the highest-value test shape this run.

## Success criteria

Functional gates (coordinator):

1. **Full pytest suite passes**: `TS=$(date -u +%Y-%m-%d_%H%M%S) && pytest --junitxml=.test_results/${TS}.xml --tb=short --timeout=30 2>&1 | tee .test_results/${TS}.log`
2. **B3+B4 mid-session role flip works live**: remote-control smoke -- activate workflow -> `get_agent_info` shows promoted role -> deactivate -> reverts -> `/compact` -> survives.
3. **All 5 D5 inject sites fire correctly**: agent's launch prompt at activation / spawn / phase-advance / broadcast / post-compact contains `## Constraints` block.
4. **E warn rule fires on real `pytest` invocations + does NOT fire on grep/cat/etc.**: validate the 27-case set (impl_data_docs) and skeptic's expanded 44-case set.
5. **F modal info parity**: clicking the `info` footer button shows real Session JSONL + Last Compaction (post-slot-4 M1 fix-up).
6. **Zero new test regressions vs `b106cff`'s parent**: diff test counts; flag any new failure not present at parent.

Architectural gates (composability):

7. **Seam-protocol tests** for the six axis-pair contracts (B<->A, C<->B, D-projection<->D-render, D-render<->D-inject, D-mcp<->D-render, D6 source-of-truth, F seam).
8. **10 crystal-point sweep** covering: workflow active/not, main vs sub-agent, effort low/medium/high/max, opus vs non-opus snap, rule disabled, post-compact survival, deactivation revert, broadcast firing.
9. **Single-composition-point lint**: zero hand-rolled `f"{phase_prompt}\n\n{constraints_block}"` outside `assemble_agent_prompt`; zero direct `compute_digest` calls outside the constraints-block + MCP + inject-site set.
10. **Source-of-truth lint**: pin `_LoaderAdapter().load() ≡ _filter_load_result(loader.load(), config)` so a regression in `_filter_load_result` cannot silently restore the slot-4-killed bug class.

User-intent gates (user_alignment, C8 binding):

11. Each user-named feature (A/B/C/D, plus stowaways E/F) verified with **both a user-side gestalt assertion AND an agent-side gestalt assertion**.
12. **Reframing fidelity** for D specifically: no modal, no `_disabled_rules` runtime store, no `GuardrailsLabel` -- the constraints block + MCP introspection are the canonical D surface.

Terminology gates (terminology):

13. **Test names locatable by SPEC component letter**: every test maps to A/B/C/D/E/F + sub-unit; reviewer cold-reading tests can find the SPEC component.
14. **Required contract strings asserted verbatim**: `## Constraints`, `### Rules ({n_active} active)`, `effort: {level}`, `CLAUDE_AGENT_ROLE`, `${WORKFLOW_ROOT}`, the 4 MCP tool names.
15. **5-site inject vocabulary**: tests use `activation / spawn / phase-advance / broadcast / post-compact`, not the older 3-site or 4-site variants.

## Failure looks like

- Tests fail -> fix until green (test fixes for tests our implementation broke are in scope here).
- B3+B4 closure doesn't flip mid-session -> must-fix.
- D5 silent gap (one of 5 inject sites silently skips) -> must-fix.
- E false-positives on documented commands -> must-fix.
- Cross-layer divergence (constraints block reports rules that hooks don't fire on, or vice versa) -> must-fix.
- Pre-existing `test_agent_switch_keybinding` flake -> tracked, not fixed (not regression from this run).

## Explicitly out of scope

- Performance benchmarking / load testing.
- Cross-platform CI runs (claudechic CI handles).
- Integration with non-claudechic external tools.
- New tests for code paths outside the abast/accf332 cluster scope.
- Re-running v1/v2 leadership review on testing artifacts.

## Pre-existing context

- All 5 sub-feature must-fixes from slot reviews are LANDED in `b106cff` (skeptic verified by grep).
- The 4 `test_get_phase_*` rule-count failures from slot 3's narrowing have been migrated by impl_data_docs (M4) and now pass under `tests/test_artifact_dir.py::test_get_applicable_rules_filters_*` and `test_get_phase_omits_rule_count_line` / `test_get_phase_no_engine_reports_none_active`.
- `pytest-timeout==2.4.0` and `ruff>=0.9.0` are now declared in `pyproject.toml` dev deps.

## Cross-layer assertion (skeptic-mandated, the keystone of this test plan)

One test pins:

```
_LoaderAdapter(lambda: app._load_result, app._manifest_loader).load()
  ==
_filter_load_result(app._manifest_loader.load(), app._project_config, app._config)
```

If this assertion ever breaks, the four downstream projections (hook layer, MCP `get_applicable_rules`, MCP `get_agent_info`, injected `## Constraints` block) silently drift. This test is the "if everything else is broken, this one tells us first" test.

## Per-axis memo cross-references

| Memo | Path | Key contributions |
|------|------|-------------------|
| Composability | `testing/composability.md` | 6 seam-protocol tests, 10 crystal-point sweep, axis isolation, composability-as-lint patterns |
| Skeptic | `testing/skeptic.md` | Q1-Q6 adapted for testing, slot must-fix verification, 7 silent-regression scenarios, failure-cost matrix |
| Terminology | `testing/terminology.md` | Test naming convention, forbidden synonyms, required contract strings, 4-step newcomer test |
| UserAlignment | `testing/user_alignment.md` | Two-axis gestalt grid, 6 cross-feature user-intent failure modes, reframing fidelity for D, final-report contract reminder |

## Sign-off bar (skeptic + composability + user_alignment converged)

To exit Testing-Implementation with a passing verdict:

1. Criteria 1-15 above all met.
2. Cross-layer assertion test passes.
3. Live remote-control B3+B4 smoke check passes.
4. Failure-cost matrix HIGH-row regressions all covered by at least one test.
5. No silent feature drop (user_alignment per-feature audit clean).
6. No new stowaway code (user_alignment scope-guard re-verification).

If any of these are unmet at testing-implementation exit, slot back to fix-up before sign-off.
