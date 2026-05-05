# TEST SPECIFICATION -- Appendix (Rationale)

Source: rationale for `TEST_SPECIFICATION.md`. This file holds the *why*; that file holds the *what*.

## TA1 -- Why only two test axes

For 5 verification gates resolving 307 manifest rows, more than two axes (Gate kind, Scope) would create empty cells. Region (test/non-test) is already encoded in each row's `verification` field via the spec's derivation rule, so re-introducing it at the test layer would duplicate state. File and rule_id are units, not dimensions.

## TA2 -- Why the manifest's `verification` field is the law

Each row carries its own verification spec; the test phase aggregates rows by `verification` value and runs the implied gate(s). This is the same manifest-as-law principle as the spec phase: workers do not re-derive what to test from source, they read the field. Adding new verification kinds in the future (e.g. `pyright+integration:<env>`) extends the map without changing the gate-routing structure.

## TA3 -- Why G3 (full suite) covers no specific manifest rows

A `verification = pyright-only` row asserts type-correctness, not behavior preservation. Sweep edited 100+ files; most edits are mechanical (annotation, narrowing, scoped ignore) but each one is still a code change. G3 is the safety net that catches accidental behavior regression even when the manifest row's `verification` field, taken in isolation, would have been satisfied by G1 alone.

The cost is one full pytest run; the alternative (per-row targeted tests for every mechanical edit) would be combinatorial overkill and would invent test cases for changes designed not to alter behavior.

## TA4 -- Why the `monkeypatch.setattr` in the cluster_dispatch test is recorded as a Generalprobe deviation

Strict reading of Generalprobe: replacing a project-internal function with a lambda is mocking. The standard says "mocks prove nothing about production readiness."

Pragmatic reading: the simulated state (`_get_backend_module(backend)` returns `None`) IS exactly the production failure mode. The function is documented to return None when the sibling `_<backend>.py` file is missing or its importlib spec/loader is None. Whether the None comes from a deleted file or a monkeypatched lookup, the downstream code path is identical -- the regression test exercises the real `_require_backend_module`, real `BackendNotAvailable`, real `_error_response`, and real MCP-tool handler code.

The filesystem alternative (rename `_lsf.py` on disk during the test, restore in teardown) is more "real" by Generalprobe's letter but has cross-test interaction risk: a test interrupted between rename and restore leaves the repo in a broken state for subsequent runs. The monkeypatch approach is process-local and self-cleaning.

`userprompt_testing.md` adopts the test as canonical without amendment, which is implicit authorization. Recording the deviation explicitly here so future readers see that the choice was deliberate and reviewed, not accidental.

## TA5 -- Why I11 (wall-clock) is a separate gate

Pyright correctness and pre-commit speed are independent dimensions of "pre-commit usable." A green pyright run that takes 30 seconds on every commit is a different kind of broken than a 7s run that fails. G5 measures the second axis. Conflating G4 (pre-commit clean) and G5 (pre-commit fast) into a single check would lose the ability to diagnose which dimension regressed.

## TA6 -- Why aggregate-gate failures route to lane-specific implementers

Per `userprompt_testing.md` failure handling: G3 (suite) failure is attributed to the lane whose edit most plausibly broke the test. Since sweep edits dominate volume (104 mechanical fixes vs 6 real-bug fixes), the routing default is SweepImplementer for sweep-touched files and BugFixImplementer for cluster_dispatch-related failures. Pre-existing flakes route to nobody; they get documented and signed off.

This preserves the lane-purity discipline established at the spec phase: the testing layer does not blur the line between mechanical and real-bug ownership.
