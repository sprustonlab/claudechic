# TEST SPECIFICATION -- pyright_cleanup

Operational brief for TestEngineer. Vocabulary inherited from `SPECIFICATION.md` (co-maintained); no new terms introduced.

## 1. Goal

Verify that the pyright cleanup did not regress any existing behavior, and that the new regression test for the `cluster_dispatch.py` real-bug fix passes.

## 2. Workstream Legend

Workstream identifiers used in this document and in routing decisions. Full timeline in `STATUS.md`.

| ID | Phase | Owner |
|---|---|---|
| WS-A | Config & stub policy (pyproject.toml diffs C1-C2; pre-config and post-config snapshots) | SweepImplementer |
| WS-B | Triage and manifest construction (`manifest.jsonl`, 307 rows) | SweepImplementer |
| WS-C | Sweep execution (104 mechanical edits + C3 config-relax block) | SweepImplementer |
| WS-D | Real-bug lane (cluster_dispatch.py + regression test) | BugFixImplementer |

## 3. Test Artifacts

Produced during this phase. All paths relative to repo root unless noted.

| Artifact | Path | Producer step |
|---|---|---|
| Final pyright snapshot | `.project_team/pyright_cleanup/specification/snapshots/<ts>-final.txt` | A |
| Audit-grep report | `.project_team/pyright_cleanup/specification/audit_grep.txt` | B |
| Pre-cleanup baseline JUnit XML | `.test_results/<ts>-pre-cleanup.xml` | D.1 |
| Pre-cleanup baseline log | `.test_results/<ts>-pre-cleanup.log` | D.1 |
| Post-cleanup JUnit XML | `.test_results/<ts>-post-cleanup.xml` | D.2 |
| Post-cleanup log | `.test_results/<ts>-post-cleanup.log` | D.2 |
| Suite diff report | `.test_results/<ts>-suite-diff.txt` | D.3 |
| Pre-commit wall-clock measurement | append to `.project_team/pyright_cleanup/specification/snapshots/precommit-walltime.txt` under heading `## Post-cleanup measurement` | F |
| Manifest-validator report | `.project_team/pyright_cleanup/specification/manifest_validator_report.txt` | G |
| Per-step verdict summary | `.project_team/pyright_cleanup/TESTING_RESULTS.md` | end-of-phase |

`<ts>` is a UTC timestamp produced by `TS=$(date -u +%Y-%m-%d_%H%M%S)`. The same `<ts>` is used across D.1, D.2, D.3 in a single test run so artifacts pair unambiguously.

## 4. Test Execution Sequence

Steps run in order. A failed step blocks subsequent steps unless explicitly noted.

### Step A -- Pyright snapshot reports 0 errors (per I3)

Command:
```
uv run pyright 2>&1 | tee .project_team/pyright_cleanup/specification/snapshots/$(date -u +%Y-%m-%dT%H%M%SZ)-final.txt
```

Pass: pyright exits with `0 errors`. Up to 1 `reportInvalidTypeVarUse` warning at `claudechic/workflows/loader.py:78:<col>:reportInvalidTypeVarUse` is acceptable; any other warning is logged but not failing.

Fail: any error reported, OR a warning at any location other than the one named above.

### Step B -- Audit-trail grep

For each manifest row where `audited_by` is populated (16 rows total at end-of-Implementation), grep the source at the row's `error_id` location to confirm the sweep applied a `# pyright: ignore[<rule_id>]` matching the row's `rule_id`. Write the resulting report to `audit_grep.txt`.

Procedure:
```
python -c "
import json
for r in (json.loads(line) for line in open('.project_team/pyright_cleanup/specification/manifest.jsonl')):
    if r.get('audited_by'):
        f, line, *_ = r['error_id'].split(':')
        print(f'{r[\"error_id\"]} :: expect # pyright: ignore[{r[\"rule_id\"]}] at {f}:{line}')
" > .project_team/pyright_cleanup/specification/audit_grep.txt
```
Then for each line in the report, verify by `grep -n "pyright: ignore\[<rule_id>\]" <file>` that the file at the named line contains the expected ignore pragma. Append `OK` or `MISSING` per row to the report.

Pass: every audit-trail row has `OK`. The grep finds the expected pragma at the expected line for all 16 rows.

Fail: any row reports `MISSING`. The sweep claimed an audited mechanical-with-ignore fix but the source does not contain the pragma.

### Step C -- Cluster-dispatch regression test

Command:
```
pytest tests/test_cluster_dispatch_missing_backend.py -v --timeout=30
```

Pass: every test in the file passes. Must include `test_missing_backend_module_returns_error` (the canonical verification node referenced by the 6 cluster_dispatch `real-bug` rows).

Fail: any test in the file fails, errors, or is skipped.

### Step D -- Full pytest suite with pre-cleanup baseline diff

Run the suite twice (pre-cleanup baseline, then post-cleanup) and diff the JUnit XMLs. A test failure that appears in both runs is a pre-existing flake; a failure that appears only in the post-cleanup run is a regression introduced by this project.

#### Step D.1 -- Pre-cleanup baseline

Stash the current working tree and check out the develop HEAD that immediately precedes WS-A (this project's first commit). Then run the suite per the `no_bare_pytest` guardrail:

```
git stash push -u -m "pyright_cleanup-test-baseline"
git checkout <develop-pre-WS-A-sha>
TS=$(date -u +%Y-%m-%d_%H%M%S) && pytest --junitxml=.test_results/${TS}-pre-cleanup.xml --tb=short --timeout=30 2>&1 | tee .test_results/${TS}-pre-cleanup.log
git checkout -
git stash pop
```

The pre-WS-A SHA is the parent of the first commit landing the cleanup branch; TestEngineer resolves it with `git log --oneline -- .project_team/pyright_cleanup/` and selects the commit immediately before the project artifacts appeared.

Record `<ts>` from `$TS` for use in D.2 and D.3.

Pass: the suite executed; XML produced. Failures within D.1 are not failures of D.1 -- they are the baseline.

Fail: stash, checkout, or pytest invocation aborts with a non-pytest error.

#### Step D.2 -- Post-cleanup suite

With working tree restored:

```
TS=<same ts as D.1> && pytest --junitxml=.test_results/${TS}-post-cleanup.xml --tb=short --timeout=30 2>&1 | tee .test_results/${TS}-post-cleanup.log
```

Pass: the suite executed; XML produced.

Fail: pytest invocation aborts with a non-pytest error.

#### Step D.3 -- Diff

Compute the symmetric difference of failing/erroring test ids between D.1 and D.2. Write to `<ts>-suite-diff.txt` with three sections: `# Pre-existing flakes (failed in both)`, `# Regressions (failed only in post)`, `# Net-fixed (failed only in pre)`.

Pass: `# Regressions` section is empty. Pre-existing `@pytest.mark.xfail` at `tests/test_pytest_needs_timeout_regex.py:187` reported as expected failure does not count toward any section.

Fail: `# Regressions` section has at least one entry. Each regression routes per §6. A regression may be excluded from the failure list only via the Generalprobe `skip` exception (sign-off-gated): both Skeptic and UserAlignment sign off in `TESTING_RESULTS.md`.

### Step E -- `uv run pre-commit run --all-files` exits 0 on second consecutive run

Pre-commit must converge: a SECOND consecutive invocation reports zero modifications and every hook `Passed`. The first run may auto-fix (ruff, ruff-format) without counting as a failure.

Commands:
```
uv run pre-commit run --all-files
uv run pre-commit run --all-files
```

Pass: the SECOND invocation reports every hook `Passed` and modifies zero files.

Fail: the second invocation reports any hook `Failed`, OR modifies any file (auto-fix loop did not converge on the first run).

### Step F -- Pre-commit wall-clock measurement (per I11)

Commands (three runs, take median; representative no-op file is `claudechic/__init__.py`):
```
time uv run pre-commit run --files claudechic/__init__.py
time uv run pre-commit run --files claudechic/__init__.py
time uv run pre-commit run --files claudechic/__init__.py
```

Append the three `real` timings and the median to `.project_team/pyright_cleanup/specification/snapshots/precommit-walltime.txt` under a new `## Post-cleanup measurement` heading, including the current pyright config state.

Pass: post-cleanup median is not greater than the recorded pre-cleanup median (7.73s, per `precommit-walltime.txt`) by more than 10% (the empirical noise band for that file). Document the comparison in the appended section.

Fail: post-cleanup median exceeds pre-cleanup median by more than 10%.

### Step G -- Manifest invariant validator

Command:
```
python .project_team/pyright_cleanup/specification/build_manifest.py --validate-only \
  > .project_team/pyright_cleanup/specification/manifest_validator_report.txt
```

(If `--validate-only` is not implemented, run the validator subset of `build_manifest.py` directly and capture the output.)

Pass: report asserts I1-I12 hold and reports `0 drift warnings`. Sub-second runtime.

Fail: any invariant violation, OR any drift warning, OR validator exits non-zero.

## 5. Pass/Fail Decision Rules

| Step | Pass | Fail blocks next step? | Re-run on fix |
|---|---|---|---|
| A Pyright snapshot 0 errors | 0 errors, ≤1 named warning | yes | A only |
| B Audit-grep | all 16 rows `OK` | yes | A then B |
| C Regression test | all in-file tests pass | yes | A then B then C |
| D.1 Baseline pytest | suite executed | yes | D.1 only |
| D.2 Post-cleanup pytest | suite executed | yes | D.2 only |
| D.3 Diff | empty regressions section | yes | from the implementer-fix step onward, then D.2 then D.3 (D.1 reused) |
| E Pre-commit converges | second run: every hook passes, 0 modifications | yes | from the failed hook's owning step onward |
| F Wall-clock | post-median ≤ 1.10 × pre-median | no -- record-only at this stage | F only |
| G Manifest validator | I1-I12 hold, 0 drift | yes (final gate) | from the affected manifest-author step onward |

A re-run after a fix repeats every step from the affected step onward, never just the failing step in isolation. D.1 is the exception: the baseline is captured once and reused across D.3 re-runs.

## 6. Failure Routing Matrix

Failure attribution uses the manifest `lane` field as the source of truth. The working tree is uncommitted at the time of testing; `git blame` is not authoritative.

| Failure mode | Route to |
|---|---|
| Step A: pyright error at a manifest-row `error_id` whose `lane = sweep` | SweepImplementer |
| Step A: pyright error at a manifest-row `error_id` whose `lane = bugfix` | BugFixImplementer |
| Step A: pyright error at a location not in the manifest | Composability + Coordinator (manifest drift) |
| Step B: any `MISSING` row | SweepImplementer (audited fix not applied to source) |
| Step C: regression-test failure | BugFixImplementer |
| Step D.3: regression in a file whose manifest rows are all `lane = sweep` | SweepImplementer |
| Step D.3: regression in `claudechic/defaults/mcp_tools/cluster_dispatch.py` or `tests/test_cluster_dispatch_missing_backend.py` | BugFixImplementer |
| Step D.3: regression in a file with no manifest rows | Composability + Coordinator (out-of-manifest edit; investigate source) |
| Step D.3: pre-existing flake unrelated to this project (failure present in BOTH D.1 and D.2) | document in `TESTING_RESULTS.md` under the Generalprobe `skip` exception (sign-off-gated); no implementer route required |
| Step E: hook other than pyright fails on second run | route to whichever hook fired (ruff -> SweepImplementer; ruff-format -> SweepImplementer; pyright -> route via Step A rules) |
| Step F: wall-clock regression | SweepImplementer |
| Step G: invariant violation or drift warning | route to the lane whose disposition class triggered the violation (`lane` field of the offending row); manifest drift unrelated to a row routes to Composability |

A re-classified manifest row that resurfaces (e.g. a `config-relax` row that pyright still reports) routes to SweepImplementer for re-triage of the disposition decision.

## 7. Out of Scope

- New tests beyond `tests/test_cluster_dispatch_missing_backend.py`.
- Strict-mode adoption or stricter pyright config.
- Tightening the pre-existing warning at `claudechic/workflows/loader.py:78:<col>:reportInvalidTypeVarUse`.
- Investigating the pre-existing `@pytest.mark.xfail` at `tests/test_pytest_needs_timeout_regex.py:187`.
- Replacing the `monkeypatch.setattr` in `tests/test_cluster_dispatch_missing_backend.py` with a filesystem-level simulation (covered by §8 carve-out).
- `SKIP=pyright` escape-valve verification (deferred to Sign-Off phase).
- `pytest -n auto` parallelism (TestEngineer discretion; not required).

## 8. Generalprobe Carve-outs

Deliberate exceptions to the Generalprobe standard, signed off by the named leads. Each carve-out is scoped narrowly and applies only to the named site.

**Generalprobe carve-out: error-path injection on internal helpers.**

When a real failure condition (e.g. a missing module file in the source tree) cannot be staged without polluting the host repo, monkeypatching the immediate boundary (e.g. `_get_backend_module` returning None) is acceptable IF every layer downstream of that boundary remains real (real exception class, real handler, real envelope).

Applies to: `tests/test_cluster_dispatch_missing_backend.py` use of `monkeypatch.setattr(mod, "_get_backend_module", lambda backend: None)`.

Signed off by: UserAlignment, Skeptic, Terminology.

## 9. Success Criteria

Testing phase exits successfully iff all of:

- S1: Step A passes (pyright 0 errors, ≤1 named warning).
- S2: Step B passes (all 16 audit-trail rows `OK`).
- S3: Step C passes (cluster_dispatch regression test green).
- S4: Step D passes (D.3 regressions section empty; both JUnit XMLs and the diff report archived).
- S5: Step E passes (second consecutive `uv run pre-commit run --all-files` exits 0 with 0 modifications).
- S6: Step F recorded; post-cleanup median documented vs pre-cleanup baseline. A regression beyond 10% blocks success.
- S7: Step G passes (I1-I12 hold, 0 drift warnings).
- S8: `TESTING_RESULTS.md` exists with per-step verdict (PASS / FAIL with route-to + resolution) and references to the timestamped artifacts.
- S9: Manifest state unchanged from end-of-Implementation (all 307 rows at `status = done`); the testing phase does not edit the manifest unless a Step A / D / G failure routes to an Implementer who then re-flips a row.
