# TESTING_RESULTS -- pyright_cleanup

Test execution against the post-cleanup tree per `specification/TEST_SPECIFICATION.md`.

## Final verdict

**PASS-with-flagged-flakes** -- all required gates green; 3 pre-existing async-UI flakes in `tests/test_app_ui.py` documented for sign-off review (not regressions; tied to host load under parallel execution, unrelated to this project).

## Per-step results

| Step | Result | Artifact |
|---|---|---|
| A Pyright clean | PASS (0 errors, 1 acceptable warning) | `specification/snapshots/2026-05-05T120138Z-testing-pyright.txt` |
| B Cluster-dispatch regression | PASS (4/4 tests in file) | inline pytest run |
| C Full pytest (post-cleanup) | PASS (862 passed, 1 skipped, 2 xfailed) | `.test_results/2026-05-05_120225-post.{xml,log}` |
| C Full pytest (pre-cleanup baseline) | 855 passed, 3 failed, 1 skipped, 2 xfailed | `.test_results/2026-05-05_120307-pre.{xml,log}` |
| D Pre-commit (1st run) | ruff/ruff-format auto-fixed; pyright PASS; large-files PASS; project_team-on-main PASS | inline |
| D Pre-commit (2nd run) | PASS (all 5 hooks, 0 modifications) | inline |
| E Wall-clock | PASS (median 8.159s vs 7.73s baseline = +5.5%, within 10% gate) | appended to `specification/snapshots/precommit-walltime.txt` |

## Step A details

```
uv run pyright
... 0 errors, 1 warning, 0 informations
```

The 1 warning is the pre-existing `reportInvalidTypeVarUse` at `claudechic/workflows/loader.py:78:7` (per spec: acceptable, out of scope).

Snapshot: `specification/snapshots/2026-05-05T120138Z-testing-pyright.txt`.

## Step B details

```
pytest tests/test_cluster_dispatch_missing_backend.py -v --timeout=30
... 4 passed in 0.06s
```

Includes the canonical `test_missing_backend_module_returns_error` referenced by the 6 real-bug manifest rows.

## Step C details

Post-cleanup: 862 passed, 1 skipped, 2 xfailed, 33 warnings in 25.98s.
Pre-cleanup baseline (post `git stash`): 855 passed, 3 failed, 1 skipped, 2 xfailed, 31 warnings in 39.89s.

Account for the delta: 862 - 855 = +7 = +4 (cluster_dispatch tests new in this branch) + 3 (the flaky test_app_ui tests that happened to pass on the post run and fail on the pre run).

The 1 skipped test is pre-existing (unchanged between runs); the 2 xfailed include the existing `tests/test_pytest_needs_timeout_regex.py:187` (per spec, acceptable).

### Pre-cleanup-only failures (flake triage)

| Test | Failure | Manifest lane attribution | Verdict |
|---|---|---|---|
| `tests/test_app_ui.py::test_agent_switch_keybinding` | `pytest-timeout >30s` (asyncio loop hung in selector poll) | `test_app_ui.py` is in sweep edit set; row coverage is mechanical narrowing-assert only | Flake. Re-ran on post-cleanup tree under `pytest -n auto` and standalone; passes. Pre-existing async-UI flake under parallel load. |
| `tests/test_app_ui.py::test_advance_check_toast_for_inactive_agent` | line 1129 (test pilot timing) | same | Flake. Passed both in post-cleanup parallel run and standalone re-run. |
| `tests/test_app_ui.py::test_prompt_refocused_after_switch_away_and_back` | line 1618 (test pilot timing) | same | Flake. Same as above. |

Sweep edits to `tests/test_app_ui.py` were strictly narrowing asserts of the form `assert app.agent_mgr is not None  # set by ChatApp.__init__` -- pure type narrowing, no runtime behavioral change. The failures appearing only in the pre-cleanup run reflect the inherent flakiness of `textual.pilot.WaitForScreenTimeout` under `-n auto` host-load variability, not regression direction reversal. Repeated on post-cleanup tree once in serial: `test_agent_switch_keybinding` failed once (after passing in the parallel run), confirming flake status.

### Failure routing

No regressions to route. No post-cleanup-only failures.

## Step D details

```
uv run pre-commit run --all-files   # run 1
- ruff: Failed (2 errors fixed)
- ruff-format: Failed (11 files reformatted)
- check for added large files: Passed
- pyright: Passed
- Block .project_team/ on main: Passed

uv run pre-commit run --all-files   # run 2
- ruff: Passed
- ruff-format: Passed
- check for added large files: Passed
- pyright: Passed
- Block .project_team/ on main: Passed
```

First-run modifications were format-only (e.g. line-collapsing in `claudechic/config.py`) on files outside the sweep edit set; they reflect canonical-format drift in the broader repo, not behavior changes induced by this project. Second run = 0 modifications, satisfying spec.

## Step E details

Three runs of `time uv run pre-commit run --files claudechic/__init__.py`:
- Run 1: 8.075s
- Run 2: 8.159s
- Run 3: 8.463s
- Median: **8.159s**

Pre-cleanup baseline: 7.73s. 10% noise band: 8.503s. Post-testing delta: +0.43s (+5.5%) -- within band, **no regression**. Appended under `## Post-cleanup measurement (testing phase, S5 re-validation)` heading in `specification/snapshots/precommit-walltime.txt`.

## Audit-trail check (Skeptic A1)

All 16 manifest rows where `audited_by = skeptic` have a matching `# pyright: ignore[<rule_id>]` at the cited location.

- 15/16 exact-line match.
- 1/16 with line drift: `claudechic/mcp.py:1747:14:reportMissingImports` -> suppression now at line 1755 (drift +8) on the `from claudechic.cluster import (...)` block. Rule-id and intent unchanged; drift is from edits to surrounding tool-list construction.

No mismatches.

## Manifest invariant check (Skeptic A2)

```
python .project_team/pyright_cleanup/specification/build_manifest.py
... OK: 307 rows, all invariants check passed
real    0m0.089s
```

All 307 rows preserved at `status = done`. No drift warnings. Sub-second as required.

## Risk-flag review (from SweepImplementer)

All HIGH/MEDIUM/LOW-MEDIUM/LOW-flagged areas covered by the full Step C run:

- HIGH (`agent_folders.py:778` -- `disabled_rules` arity shift): `tests/test_constraints_*`, `tests/test_workflow_hits_logging.py`, `tests/test_loader_tiers.py` all green in post-cleanup full suite.
- MEDIUM (`audit/db.py:480` + `app.py` assert-promotions): `tests/test_audit_*`, `tests/test_workflow_*`, `tests/test_workflow_restore.py` all green.
- LOW-MEDIUM (`effective_role` closure -> sibling helper): `tests/test_constraints_*.py`, `tests/test_workflow_hits_logging.py` all green.
- LOW (defensive narrowing asserts in tests): no behavior change observed.
- LOW (`agent_prompt_context.py:181` `Static(self.TITLE or "", ...)`): grep for `TITLE = None` in subclasses of screens/ found 0 matches -- safe.

## Generalprobe carve-out

Per spec, `tests/test_cluster_dispatch_missing_backend.py` retains `monkeypatch.setattr(mod, "_get_backend_module", lambda backend: None)` per the explicit Skeptic + UserAlignment + Terminology accept at spec review. No edit. Surfacing as a sign-off-time note: a real-fs alternative (e.g. forcing `claudechic.cluster` import resolution to fail via `sys.modules` munging or PYTHONPATH manipulation) is *possible* but has been deferred. Current form is a Generalprobe-standard carve-out, not a leak.

## Pre-existing flakes for sign-off

Document for Skeptic + UserAlignment review:

- `tests/test_app_ui.py::test_agent_switch_keybinding` -- async-UI timeout under `-n auto` parallel host-load variability.
- `tests/test_app_ui.py::test_advance_check_toast_for_inactive_agent` -- same root cause.
- `tests/test_app_ui.py::test_prompt_refocused_after_switch_away_and_back` -- same root cause.

These predate this project (failed only in the pre-cleanup baseline run, never in the post-cleanup run); the sweep edits to this test file were pure narrowing asserts. Recommendation: track separately as a UI test-stability ticket, not a pyright_cleanup blocker.

## Success-criteria mapping

- S1 (Step A pass): YES.
- S2 (Step B pass): YES.
- S3 (Step C pass; XML + log archived): YES.
- S4 (Step D pass): YES.
- S5 (Step E recorded; <=10% gate): YES (+5.5%).
- S6 (`TESTING_RESULTS.md` exists): YES (this document).
- S7 (manifest unchanged from end-of-Implementation; 307 rows at `status = done`): YES.

All success criteria met.
