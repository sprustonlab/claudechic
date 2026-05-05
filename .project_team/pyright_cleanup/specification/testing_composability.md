> **SUPERSEDED:** see `TEST_SPECIFICATION.md`. This file is retained as authoring history; the operational facts and additional Skeptic + Terminology amendments live in the canonical doc.

# Testing Composability -- pyright_cleanup

Composability review of the testing approach. Operational facts only; rationale lives in `testing_composability_appendix.md`.

## Definitions

- **Verification gate** -- a single executable check that proves manifest rows resolved correctly. Five gates total in this project (G1-G5).
- **Manifest verification field** -- the `verification` value on each manifest row; one of `pyright-only`, `pyright+targeted:<node_id>`, `pyright+suite`. Defined in `SPECIFICATION.md` s 5.
- **Reachability anchor** -- as defined in `SPECIFICATION.md` s 2.1: a public CLI command, slash-command handler, MCP tool entry point, Textual screen/widget event handler, or executed pytest node.
- **Generalprobe standard** -- the test discipline defined in the phase prompt: real infrastructure, no `pytest.skip`, no `pytest.xfail`, no `importorskip`, no mocking, public API only, opaque handles, production-identical execution.
- **Mocking** (per Generalprobe) -- replacing a production component with a fake. Includes `unittest.mock`, `MagicMock`, `monkeypatch.setattr` of internal functions, and any technique that bypasses the production code path.
- **Simulated condition** -- producing an environment state (file absent, env var unset, port closed) by manipulating the environment rather than the code. Distinct from mocking.

## Test Axes

### Axis G -- Gate kind

Values: `static`, `targeted-runtime`, `suite-runtime`, `composite`, `timing`.

| Value | Mechanism | Resolves manifest rows |
|---|---|---|
| `static` | `uv run pyright` | all rows whose `verification` starts with `pyright` |
| `targeted-runtime` | a single named pytest node | rows whose `verification = pyright+targeted:<node>` |
| `suite-runtime` | full pytest suite | no specific rows; protects against runtime regression from sweep edits |
| `composite` | `uv run pre-commit run --all-files` | aggregates `static` + ruff-lint + ruff-format |
| `timing` | timed `pre-commit run --files <typical-edit>` | I11 |

### Axis S -- Scope

Values: `row-level`, `aggregate`.

`row-level` gates verify a specific manifest row by its `verification` field. `aggregate` gates verify project-wide properties not tied to any single row.

### Non-axes

- File: not an axis -- which file a test lives in is a unit, not a dimension.
- Region (test/non-test): not an axis at the test layer; region is a manifest-row property already encoded in `verification` derivation.

## Coverage Crystal

Mapping from manifest verification field to gate(s):

| Manifest `verification` | Row count | Resolving gate(s) |
|---|---:|---|
| `pyright-only` | 301 | G1 (pyright clean) |
| `pyright+targeted:tests/test_cluster_dispatch_missing_backend.py::test_missing_backend_module_returns_error` | 6 | G1 + G2 (the named pytest node) |
| `pyright+suite` | 0 | G1 + G3 (would apply if any row required full suite) |

Aggregate gates without a row mapping:

| Gate | Purpose |
|---|---|
| G3 (full pytest suite) | Detects runtime regression from any of the 100+ sweep edits, even where the manifest row's `verification = pyright-only` suffices for type-correctness. |
| G4 (pre-commit) | Composite check that all hooks (pyright, ruff, ruff-format) pass together. Closes the user-visible loop. |
| G5 (wall-clock) | I11. |

All 307 rows are covered by G1, with the 6 real-bug rows additionally covered by G2. The crystal has no holes.

## Gates

### G1 -- Pyright clean

Command: `uv run pyright`.
Pass: 0 errors. 1 pre-existing `reportInvalidTypeVarUse` warning at `claudechic/workflows/loader.py:78` is acceptable (out of scope per `userprompt_testing.md`).
Fails into: SweepImplementer if the failing row's manifest disposition is `mechanical`/`config-relax`/`stub-fix`/`stub-ignore`; BugFixImplementer if `real-bug`.

### G2 -- Cluster-dispatch regression test

Command: `pytest tests/test_cluster_dispatch_missing_backend.py --tb=short --timeout=30`.
Pass: every test in the file passes.
Resolves manifest rows: 6 (the cluster_dispatch.py real-bug rows).
Fails into: BugFixImplementer.

### G3 -- Full pytest suite

Command (per `no_bare_pytest` guardrail):
```
TS=$(date -u +%Y-%m-%d_%H%M%S) && pytest --junitxml=.test_results/${TS}.xml --tb=short --timeout=30 2>&1 | tee .test_results/${TS}.log
```
Pass: zero failing tests.
Fails into: SweepImplementer if the failing test was edited during sweep; BugFixImplementer if cluster_dispatch-related; documented-and-skipped only with Skeptic + UserAlignment sign-off if the failure is a pre-existing flake unrelated to this project.

### G4 -- Pre-commit clean

Command: `uv run pre-commit run --all-files`.
Pass: every hook reports `Passed`.
Fails into: route to the hook that fired.

### G5 -- Wall-clock not regressed

Command: `time uv run pre-commit run --files claudechic/__init__.py` (no-op edit), three runs, take median.
Pass: median post-cleanup wall-clock not greater than pre-cleanup baseline by more than measurement noise.
Fails into: SweepImplementer (likely candidate: an unintended config bloat or import-time regression).

## Seams

### Seam T1: Manifest -> Gates

Crosses: each manifest row's `verification` field.
Does not cross: the row's `proposed_fix`, `notes`, or `audited_by` fields.

A row is verified iff the gate(s) named by its `verification` field pass and pyright reports the row's `error_id` resolved.

### Seam T2: Gate -> Implementer (failure routing)

Crosses: gate name + failing row's `error_id` + manifest's `disposition` + `lane` for that row (or "no row mapping" for aggregate-gate failures).
Does not cross: stack traces, internal test state.

A failing gate routes to the implementer responsible for the failing row's lane; aggregate-gate failures route per `userprompt_testing.md` failure-handling table.

### Seam T3: Test result -> STATUS / TESTING_RESULTS

Crosses: gate name + pass/fail + (for G3/G5) timestamped artifact path.
Does not cross: per-test details (those live in the JUnit XML).

## Generalprobe Compliance

| Requirement | Verdict | Evidence |
|---|---|---|
| Real infrastructure | **PASS** | All 5 gates run real binaries: `uv run pyright`, `pytest`, `pre-commit`, `time`. No simulated harness. |
| No `pytest.skip` / `pytest.xfail` / `importorskip` | **PASS for the cleanup-introduced test**; **carry-over warning** | `tests/test_cluster_dispatch_missing_backend.py` contains zero matches. Repo-wide pre-existing: `tests/test_pytest_needs_timeout_regex.py` line 187 has one `@pytest.mark.xfail`, unchanged by this project (see Out of Scope). |
| Public API only | **PASS** | All gates invoke project public CLIs (pyright, pytest, pre-commit). Manifest-row verification is via reachability-anchor named pytest node, not internal hooks. |
| Opaque handles | **N/A** | This project has no opaque-handle surface; gates produce strings (rule_id, file:line) which are the project's public diagnostic vocabulary. |
| Production-identical | **PASS** | `uv run` commands execute the same toolchain as production pre-commit. |
| **No mocking** | **DEVIATION (one site, accepted)** | `tests/test_cluster_dispatch_missing_backend.py` uses `monkeypatch.setattr(mod, "_get_backend_module", lambda backend: None)` to simulate "sibling backend file missing." Strict reading: a `monkeypatch.setattr` of a project-internal function is a mock. Pragmatic reading: the simulated condition (function returns None) is exactly the production failure path; the alternative (rename `_lsf.py` on disk) is more brittle. `userprompt_testing.md` adopts this test as the canonical regression node, implicitly accepting the technique. |

The mocking deviation is recorded here but does not block testing-phase advance. Surfaced for Coordinator / UserAlignment sign-off awareness.

## Invariants

- T1: Every manifest row with `verification = pyright-only` is resolved by G1's pyright snapshot reporting 0 errors at that row's `error_id`.
- T2: Every manifest row with `verification = pyright+targeted:<node_id>` is resolved by G1 AND a passing run of `<node_id>` in G2.
- T3: G1's final-state snapshot is committed under `specification/snapshots/` with timestamp.
- T4: G3's results are committed under `.test_results/<timestamp>.{xml,log}` per the `no_bare_pytest` guardrail.
- T5: G5 records pre-cleanup baseline AND post-cleanup measurement in `specification/snapshots/precommit-walltime.txt`. I11 holds iff post-cleanup median is not greater than pre-cleanup median by more than measurement noise.
- T6: No new `pytest.skip`, `pytest.xfail`, or `importorskip` is introduced by this project's edits. Pre-existing markers in unchanged files are out of scope.
- T7: Any G3 test failure is documented in `TESTING_RESULTS.md` (or appended to STATUS.md) with route-to and resolution. A failure is not closed by `pytest.skip`; it is fixed, or signed-off as pre-existing flake.

## Out of Scope

- New tests beyond `tests/test_cluster_dispatch_missing_backend.py` (per `userprompt_testing.md`).
- Strict-mode adoption or stricter pyright config.
- Tightening the pre-existing `reportInvalidTypeVarUse` warning at `claudechic/workflows/loader.py:78`.
- Pre-existing `@pytest.mark.xfail` at `tests/test_pytest_needs_timeout_regex.py:187`.
- Replacing the `monkeypatch.setattr` in `tests/test_cluster_dispatch_missing_backend.py` with a filesystem-level simulation (sibling-file rename). Recorded as a Generalprobe deviation; UserAlignment / Coordinator sign-off authoritative.

## Artifacts Produced

- `specification/snapshots/<timestamp>-final.txt` -- pyright snapshot at gate-G1 pass.
- `.test_results/<timestamp>.xml` and `.test_results/<timestamp>.log` -- gate-G3 output.
- `specification/snapshots/precommit-walltime.txt` -- gate-G5 measurements (already exists from WS-A; appended after WS-C completion).
- `TESTING_RESULTS.md` (or appended STATUS.md section) -- per-gate verdicts.

Rationale lives in `specification/testing_composability_appendix.md`.
