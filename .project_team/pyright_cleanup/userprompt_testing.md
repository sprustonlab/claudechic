# Testing Vision -- pyright_cleanup

> User: "Sure lets do this quickly this is the vision and the spec. please advance to implementation" (2026-05-05)

Approved testing scope for the pyright_cleanup project.

## Goal

Verify that the pyright cleanup did not regress any existing behavior, and that the new regression test for the `cluster_dispatch.py` real-bug fix passes.

## In scope

1. **Pyright clean** -- `uv run pyright` returns 0 errors on the final tree (1 pre-existing warning is acceptable).
2. **New regression test passes** -- `tests/test_cluster_dispatch_missing_backend.py` (the canonical verification node for the 6 real-bug rows).
3. **Full pytest suite passes** -- no regressions from the 100+ source/test edits during sweep. Run with timestamped results per the `no_bare_pytest` guardrail:
   ```
   TS=$(date -u +%Y-%m-%d_%H%M%S) && pytest --junitxml=.test_results/${TS}.xml --tb=short --timeout=30 2>&1 | tee .test_results/${TS}.log
   ```
4. **Pre-commit clean** -- `uv run pre-commit run --all-files` passes end-to-end.
5. **Wall-clock spot-check** -- `pre-commit run --files <typical-edit>` median wall-clock has not further regressed since WS-C completion (current 7.75s).

## Out of scope

- New tests beyond the cluster_dispatch regression test (already added in WS-D).
- Strict-mode adoption or stricter pyright config (s 12 out-of-scope).
- Tightening the pre-existing `reportInvalidTypeVarUse` warning at `workflows/loader.py:78` (Skeptic flagged for follow-up).

## Failure handling

- Pyright failure -> investigate, route to appropriate Implementer (lane purity preserved).
- Pre-commit failure -> route to whichever hook fired.
- Test failure attributable to a sweep edit -> route to SweepImplementer.
- Test failure attributable to the cluster_dispatch refactor -> route to BugFixImplementer.
- Test failure unrelated to this project (pre-existing flake) -> document and skip with Skeptic + UserAlignment sign-off.

## Success looks like

- Pyright 0 errors.
- Full pytest suite green; results saved under `.test_results/<timestamp>.xml` + `.log`.
- pre-commit green.
- Brief Testing summary appended to STATUS.md (or new `TESTING_RESULTS.md` artifact).
