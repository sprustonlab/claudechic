> **SUPERSEDED:** see `SPECIFICATION.md`. This file is retained as authoring history.

# Composability Spec -- pyright_cleanup

## Definitions

- **Error** -- a single pyright diagnostic line: `(file, line, col, rule_id, message)`.
- **Non-test code** -- any `.py` file outside `tests/`.
- **Test code** -- any `.py` file under `tests/`.
- **Mechanical fix** -- annotation, narrowing, scoped `# type: ignore[rule]`, or import correction with no runtime behavior change.
- **Real bug** -- error reflecting a runtime defect (None deref, wrong call signature, missing branch, etc.). Fix changes runtime behavior.
- **Stub fix** -- adjustment to handle a missing or incorrect third-party type stub: local stub file, scoped `# type: ignore`, or pyright `reportMissingTypeStubs` config.
- **Config-relax** -- a user-approved relaxation of pyright rules in `pyproject.toml`: per-rule severity downgrade or `executionEnvironments` overrides scoped to a path. Does not remove files from pyright's view.
- **Config-exclude** -- a user-rejected mechanism: removing files from pyright's view via `[tool.pyright].exclude`, or whole-file/directory `# pyright: ignore`. Forbidden everywhere by I7.
- **Manifest** -- the JSONL artifact at `specification/manifest.jsonl`; one JSON object per line, one line per pyright error, schema defined in this document.
- **Disposition** -- the assigned treatment for an error. One of: `mechanical`, `real-bug`, `config-relax`, `config-exclude`, `stub-fix`, `stub-ignore`, `dropped`.
- **Verification** -- the check that confirms a row is resolved. One of: `pyright-only`, `pyright+targeted:<pytest_node_id>`, `pyright+suite`.
- **Lane** -- the implementer that owns a row. One of: `sweep`, `bugfix`, `none`.
- **Pyright snapshot** -- the output of `uv run pyright` saved with timestamp under `specification/snapshots/`.
- **Suppression-baseline file** -- any generated file (e.g. `pyright-baseline.json`, error allowlist, ratchet file) that lets pre-commit tolerate a fixed set of pre-existing errors. Forbidden by I6.

## Axes

### Axis R -- Region

Values: `non-test`, `test`.

Independent because each region has a distinct success criterion:
- `non-test`: error count must reach 0.
- `test`: error count after relaxations must reach 0; all rows with disposition `real-bug` must be fixed.

### Axis F -- Fix kind

Values: `mechanical`, `real-bug`, `config-relax`, `config-exclude`, `stub-fix`, `stub-ignore`.

Independent because each value implies a distinct verification cost and risk profile.

### Non-axes

These are NOT axes (do not partition workstreams or implementers along them):
- `error_type` (rule_id) -- a property of the error, not a choice.
- `file` -- a unit, not a dimension.
- `verification mode` -- derived from (R, F).

## Compositional Law

Every error appears as exactly one row in the manifest with all required fields populated. All workers (config, triage, sweep, bugfix, testing) consume the manifest. No worker reads source code to discover work; work is enumerated only via manifest rows assigned to its lane.

If `error not in manifest`, no work is done on it.
If `row.status = done`, no worker re-touches it without first reverting status.

## Manifest Schema

Required fields per row:

| Field | Type | Required | Allowed values |
|---|---|---|---|
| `error_id` | string | yes | `<relpath>:<line>:<col>:<rule_id>` |
| `region` | string | yes | `non-test`, `test` |
| `rule_id` | string | yes | pyright rule (e.g. `reportArgumentType`) |
| `disposition` | string | yes | `mechanical`, `real-bug`, `config-relax`, `config-exclude`, `stub-fix`, `stub-ignore`, `dropped` |
| `lane` | string | yes | `sweep`, `bugfix`, `none` |
| `verification` | string | yes | `pyright-only`, `pyright+targeted:<node_id>`, `pyright+suite` |
| `proposed_fix` | string | yes | one-line description |
| `status` | string | yes | `pending`, `in-progress`, `done`, `dropped` |
| `audited_by` | string | conditional | agent name; required when `disposition = mechanical` AND `proposed_fix` contains `# type: ignore`; populated by a second agent before `status = done` |
| `notes` | string | conditional | free text; required for `dropped` rows (see I4) and `stub-dep` tagging (see Operational Policy) |

Lane assignment rule:
- `disposition in {mechanical, stub-fix, stub-ignore, config-relax, config-exclude}` -> `lane = sweep`.
- `disposition = real-bug` -> `lane = bugfix`.
- `disposition = dropped` -> `lane = none`.

Verification assignment rule:
- `disposition in {mechanical, stub-fix, stub-ignore, config-relax, config-exclude}` -> `verification = pyright-only`.
- `disposition = real-bug AND region = non-test` -> `verification = pyright+targeted:<node_id>` (node_id required).
- `disposition = real-bug AND region = test` -> `verification = pyright+targeted:<node_id>` where `node_id` is the test itself.

`config-exclude` rows must not be created (I7). `config-relax` rows must not be created with `region = non-test` (I12). The lane/verification rule above defines routing only for the case of an erroneous attempt; such rows are rejected at triage.

## Seams

### Seam 1: Config -> Triage

Crosses: pyright config (`pyproject.toml [tool.pyright]`) and a fresh pyright snapshot. The pre-config snapshot also records the active `[tool.pyright].exclude` list verbatim.
Does not cross: source code edits, manifest edits.

Config changes complete before triage begins. Triage runs against the post-config snapshot. After triage starts, config may only change via a documented amendment that triggers re-triage of affected rows.

### Seam 2: Triage -> Implementers

Crosses: manifest rows with `lane in {sweep, bugfix}` and `status = pending`.
Does not cross: triage rationale, source file contents.

Implementers select rows by `lane` and `status`. Implementers must not change `disposition` or `lane`. To re-classify, an implementer sets `status = pending` and messages the triage worker.

### Seam 3: Implementers -> Testing

Crosses: rows with `status = done` and their `verification` field.
Does not cross: implementation diff details, source code.

Testing runs `pyright` and the union of `node_id`s referenced in `verification` fields. A row is accepted iff its verification passes.

### Seam 4: Stub-fix -> Manifest

Crosses: a fresh pyright snapshot after each stub-fix batch.
Does not cross: stub implementation details.

A stub fix may erase other rows. After applying a stub-fix batch, regenerate the snapshot and mark erased rows `status = done, disposition = stub-fix` (grouped under the resolving stub-fix row's id in `notes`).

## Crystal

| | mechanical | real-bug | config-relax | config-exclude | stub-fix | stub-ignore |
|---|---|---|---|---|---|---|
| non-test | populated | populated | forbidden (I12) | forbidden (I7) | populated | populated |
| test | populated | populated | populated | forbidden (I7) | populated | populated |

Constraints:
- `(disposition = config-exclude)` is forbidden in both regions (I7). The column exists for triage to name and reject the mechanism explicitly.
- `(region = non-test, disposition = config-relax)` is forbidden (I12). Non-test errors are fixed by code change, stub work, or scoped per-line `# type: ignore[rule]` (which is `mechanical`).

All other cells are reachable; combinations work by manifest construction.

## Workstream Ordering

Hard dependencies (must precede):
1. **Config & stub policy** (sweep lane, config rows + stub-fix rows on top-N stub sources). Output: post-config pyright snapshot.
2. **Triage**. Input: post-config snapshot. Output: complete manifest.
3. **Sweep** (parallel-safe across rows) and **Bugfix** (per-row, sequential within a file).
4. **Testing**. Input: rows with `status = done`. Output: pass/fail per row.

Re-entry: if Testing fails a row, that row's `status` returns to `in-progress` and re-enters its lane.

Parallelism note: if post-triage `disposition = real-bug` rate exceeds 30% of total rows, sub-divide the Bugfix lane by file (one bugfix worker per file, each consuming only rows whose `error_id` starts with that file's path).

## Operational Policy

- Emergency escape valve: `SKIP=pyright git commit` is the documented way to bypass pre-commit when truly needed. Use sparingly; record each use in commit message.
- For the duration of this work, `pyproject.toml` pins exact versions of `anthropic` and `textual` (the two largest stub-issue sources). Version bumps are out of scope.
- Stub-dependent rows (`disposition in {stub-fix, stub-ignore}`) tag `notes: stub-dep` so future library upgrades can audit and re-evaluate.

## Invariants

- I1: Sum of manifest rows == count of errors in the post-config snapshot at triage time, plus rows added by re-triage.
- I2: No row has `disposition = mechanical` in the bugfix lane, and no row has `disposition = real-bug` in the sweep lane.
- I3: Final pyright snapshot reports 0 errors. Final manifest has every row at `status in {done, dropped}`.
- I4: Every `dropped` row's `notes` field begins with one of `wontfix:`, `refactor-required:`, `duplicate:`, or `false-positive:`, followed by a one-line justification. `refactor-required:` rows additionally include a tracking handle (issue link, TODO ref, or follow-on project name).
- I5: No `# type: ignore` is added without a `rule_id` selector.
- I6: No suppression-baseline file is introduced. Pre-commit fails on any new error from day one.
- I7: No row has `disposition = config-exclude` in any region. Test-region config changes use `config-relax` only.
- I8: No file-level pyright carve-out (`exclude` entry, whole-file `# pyright: ignore`) is added for any test file, including `test_phase_injection.py`, `test_computer_info_modal.py`, `test_model_selection.py`.
- I9: No row with `region = non-test` may have `status = dropped` or `disposition = dropped`. Non-test errors are fixed.
- I10: Every row with `disposition = mechanical` whose `proposed_fix` contains `# type: ignore` has `audited_by` populated by an agent distinct from the one that authored the row, before `status = done`.
- I11: `git commit` pre-commit wall-clock on a representative no-op edit is not regressed vs. pre-cleanup baseline. Both timings recorded in `specification/snapshots/precommit-walltime.txt`.
- I12: No row has `region = non-test` and `disposition = config-relax`. Non-test region accepts no rule relaxation; only `mechanical`, `real-bug`, `stub-fix`, or `stub-ignore` dispositions are valid for non-test rows.

## Out of Scope

- Adopting pyright `strict` mode anywhere new.
- Refactoring beyond the minimum needed to fix a flagged error.
- Touching files not referenced by any manifest row.
- Modifying tests for reasons unrelated to a manifest row.
- Type-checker swap (mypy, pyre, ty).
- Pyright major-version upgrade.

## Artifacts Produced

- `specification/manifest.jsonl` -- the manifest defined above; one JSON object per line, fields per the schema table.
- `specification/snapshots/<timestamp>.txt` -- pyright snapshots before config, after config, after sweep, after bugfix, final. The `pre-config` snapshot additionally records the active `[tool.pyright].exclude` list verbatim alongside the error output.
- `specification/snapshots/precommit-walltime.txt` -- pre-cleanup and post-cleanup `git commit` pre-commit wall-clock timings on a representative no-op edit (per I11).
- `specification/config-changes.md` -- list of every pyproject.toml diff applied, with row-id references.
- `specification/real-bugs.md` -- one entry per `disposition = real-bug` row. Required columns: `error_id`, `bug` (one-line description), `fix` (one-line description), `regression_test_node_id`, `runtime_intent`. Allowed values for `runtime_intent`: `raise`, `skip`, `default:<v>`, `propagate`. Required for every fix touching `reportOptionalMemberAccess` or any None-narrowing; recommended for all real-bug rows.

Rationale for decisions in this spec lives in `specification/composability_appendix.md` (later merged into a unified `SPEC_APPENDIX.md`).
