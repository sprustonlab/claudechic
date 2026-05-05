# SPECIFICATION -- pyright_cleanup

Canonical operational spec. Every term used here is defined here. Rationale lives in `SPECIFICATION_APPENDIX.md` (co-maintained); historical lens reviews are cited there as immutable artifacts.

## 1. Goal and Success Criteria

**Goal.** Make pyright pre-commit usable on claudechic by clearing all non-test pyright errors and fixing genuine bugs surfaced by pyright in tests.

**Success criteria.**
- S1: `uv run pyright` exits with 0 errors on non-test code.
- S2: After test-region rule relaxation, `uv run pyright` exits with 0 errors overall, and every finding in tests classified as a genuine bug has been fixed.
- S3: `uv run pre-commit run --all-files` passes end-to-end.
- S4: No suppression-baseline file is introduced (per I6).
- S5: `git commit` pre-commit wall-clock on a representative no-op edit is not regressed vs. the pre-cleanup baseline (per I11). Both timings are recorded.
- S6: Test-region pyright handling is implemented as a relaxed ruleset via `[tool.pyright.executionEnvironments]`. `[tool.pyright].exclude` of `tests/` (or any subset) is not used.
- S7: Top-error test files (`test_phase_injection.py`, `test_computer_info_modal.py`, `test_model_selection.py`) receive the same triage as every other file; no file-level carve-outs.
- S8: A written record exists of which test errors were classified as real bugs, what was fixed, and what was deferred -- carried by `manifest.jsonl` and `real-bugs.md`.

**Failure modes** (will block sign-off):
- Pre-commit still fails on a clean tree.
- A finding classified as `mechanical` masks a real runtime defect.
- Excluding so much code that pyright becomes ceremonial.
- Scope creep into strict-mode adoption or unrelated refactoring.
- Runtime regressions introduced while fixing types.

## 2. Definitions

Section 2 is the authoritative vocabulary. Every other section uses these terms verbatim.

### 2.1 Domain terms

- **Finding** (a.k.a. **error** in this document) -- a single pyright diagnostic identified by `(file, line, col, rule_id, message)`. "Finding" is the generic noun used pre-triage.
- **Non-test code** -- any `.py` file outside `tests/`.
- **Test code** -- any `.py` file under `tests/`.
- **Mechanical fix** -- a fix that resolves a finding by annotation, narrowing (`assert isinstance` / `cast`), scoped `# type: ignore[<rule_id>]`, or import correction, **with no runtime behavior change**.
- **Real bug** -- a finding that reflects a runtime defect (None deref, wrong call signature, missing branch, etc.) reachable from a reachability anchor. Its fix changes runtime behavior.
- **Reachability anchor** -- one of: a public CLI command, a registered slash-command handler, an MCP tool entry point, a Textual screen/widget event handler, or an executed pytest node. A code path is "reachable" iff some chain of calls connects an anchor to it.
- **Stub fix** -- a fix that resolves a finding by adding or correcting a local `.pyi` stub under `[tool.pyright].stubPath`, or by switching to a maintained stub package.
- **Stub ignore** -- a finding silenced via scoped `# type: ignore[import]` or `reportMissingTypeStubs` config because no stub is feasible.
- **Config-relax** -- a user-approved relaxation of pyright rules in `pyproject.toml`: per-rule severity downgrade in `[tool.pyright.executionEnvironments]` scoped to a path. **Path remains type-checked**; specific rules are silenced.
- **Config-exclude** -- a user-rejected mechanism: removing files from pyright's view via `[tool.pyright].exclude`, or whole-file/directory `# pyright: ignore`. **Forbidden everywhere by I7.**
- **Manifest** -- the JSONL artifact at `specification/manifest.jsonl`; one JSON object per line, one line per finding, schema in s 5.
- **Disposition** -- the assigned treatment for a finding. Allowed values: `mechanical`, `real-bug`, `config-relax`, `config-exclude`, `stub-fix`, `stub-ignore`, `dropped`. (`config-exclude` is named only so triage can reject it.)
- **Verification** -- the check that confirms a manifest row is resolved. One of: `pyright-only`, `pyright+targeted:<pytest_node_id>`, `pyright+suite`.
- **Lane** -- the implementer that owns a row. One of: `sweep`, `bugfix`, `none`.
- **Pyright snapshot** -- the output of `uv run pyright` saved with timestamp under `specification/snapshots/`.
- **Suppression-baseline file** -- any generated file (e.g. `pyright-baseline.json`, error allowlist, ratchet file) that lets pre-commit tolerate a fixed set of pre-existing errors. Forbidden by I6.
- **Triage** -- the act of assigning each finding to exactly one disposition.
- **Principled suppression** -- a `# type: ignore[<rule_id>]` paired with a `mechanical` or `stub-ignore` row whose `proposed_fix` states the reason. Required form: `# type: ignore[<rule_id>]  # <reason>`.
- **Band-aid suppression** -- a bare `# type: ignore` (no rule_id selector) or one used to silence a `real-bug`. Forbidden by I5 and I2.
- **Strict-mode creep** -- adopting `strict = true`, `typeCheckingMode = "strict"`, or enabling additional rules beyond the current basic baseline. Out of scope (s 12).

### 2.2 Disposition glossary

| Disposition | Resolves a finding by | Region | Lane | Verification |
|---|---|---|---|---|
| `mechanical` | annotation, narrowing, scoped `# type: ignore[<rule_id>]`, or import correction (no runtime change) | non-test, test | sweep | pyright-only |
| `real-bug` | logic fix that changes runtime behavior | non-test, test | bugfix | `pyright+targeted:<node_id>` |
| `config-relax` | per-rule severity downgrade in `executionEnvironments`; path stays type-checked | test only (forbidden non-test by I12) | sweep | pyright-only |
| `stub-fix` | local `.pyi` under `stubPath` or maintained stub package | non-test, test | sweep | pyright-only |
| `stub-ignore` | scoped `# type: ignore[import]` or `reportMissingTypeStubs` config (no feasible stub) | non-test, test | sweep | pyright-only |
| `dropped` | not fixed in this project; structured `notes` prefix required (s 5.2) | test only (forbidden non-test by I9) | none | n/a |
| `config-exclude` | (forbidden) `[tool.pyright].exclude` or whole-file `# pyright: ignore` | none -- rejected by I7 | n/a | n/a |

### 2.3 Pyright glossary

| Term | Meaning |
|---|---|
| `rule_id` (a.k.a. error code) | pyright identifier such as `reportOptionalMemberAccess`. Always cited in `error_id` and in scoped ignores. |
| strictness level | pyright preset bundle: `off` / `basic` / `strict` / `all`. claudechic uses `basic`. Changing this is strict-mode creep (out of scope). |
| `py.typed` | empty marker file inside a package indicating its source ships inline annotations. Absence forces stubs. |
| `executionEnvironments` | `[[tool.pyright.executionEnvironments]]` block scoping rule overrides to a path. The mechanism for `config-relax`. |
| `stubPath` | `[tool.pyright].stubPath` -- directory pyright searches for local `.pyi` files. Required to use `stub-fix`. |
| `reveal_type(x)` | diagnostic call printing x's inferred type. Debug-only; never commit. |
| `cast(T, x)` | `typing.cast` -- tells pyright to treat x as T without runtime check. Acceptable inside `mechanical`; suspect when the underlying finding is really a `real-bug`. |
| `assert isinstance(x, T)` | narrowing via runtime check. Preferred over `cast` when x's type is genuinely uncertain at runtime. |
| `[tool.pyright].exclude` | removes paths from type-checking. Forbidden mechanism (`config-exclude`). |

### 2.4 Word-choice resolution

- "fix" without qualifier is ambiguous; use **logic fix** (real-bug), **mechanical fix**, or **suppression** (must be principled).
- "exclusion" / "exclude" refers to `config-exclude` only and is forbidden.
- "relaxation" / "relax" refers to `config-relax` only.
- "scoped ignore" refers to per-line `# type: ignore[<rule_id>]` and falls under `mechanical` or `stub-ignore`.
- "test exclusion" must never be used as a synonym for `config-relax`; that is the precise wording the user rejected.

## 3. Axes

### Axis R -- Region

Values: `non-test`, `test`.

Independent because each region has a distinct success criterion: non-test reaches 0 errors at baseline severity; test reaches 0 errors after relaxation, with all real-bug rows fixed.

### Axis F -- Fix kind

Values: `mechanical`, `real-bug`, `config-relax`, `config-exclude`, `stub-fix`, `stub-ignore`.

Independent because each value implies a distinct verification cost and risk profile.

### Non-axes

Not axes (do not partition workstreams or implementers along them):
- `rule_id` -- a property of a finding, not a choice.
- `file` -- a unit, not a dimension.
- verification mode -- derived from (R, F).

## 4. Compositional Law

Every finding appears as exactly one row in the manifest with all required fields populated. All workers (config, triage, sweep, bugfix, testing) consume the manifest. No worker reads source code to discover work; work is enumerated only via manifest rows assigned to its lane.

If a finding is not in the manifest, no work is done on it.
If `row.status = done`, no worker re-touches it without first reverting status.

## 5. Manifest Schema

`specification/manifest.jsonl` -- one JSON object per line.

### 5.1 Fields

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
| `notes` | string | conditional | free text; required for `dropped` rows (s 5.2) and for `stub-dep` tagging (s 9) |

Lane assignment rule:
- `disposition in {mechanical, stub-fix, stub-ignore, config-relax, config-exclude}` -> `lane = sweep`.
- `disposition = real-bug` -> `lane = bugfix`.
- `disposition = dropped` -> `lane = none`.

Verification assignment rule:
- `disposition in {mechanical, stub-fix, stub-ignore, config-relax, config-exclude}` -> `verification = pyright-only`.
- `disposition = real-bug AND region = non-test` -> `verification = pyright+targeted:<node_id>` (node_id required).
- `disposition = real-bug AND region = test` -> `verification = pyright+targeted:<node_id>` where `node_id` is the test itself.

`config-exclude` rows must not be created (I7). `config-relax` rows with `region = non-test` must not be created (I12). The lane/verification rules above define routing only for the case of an erroneous attempt; such rows are rejected at triage.

### 5.2 `dropped` notes-prefix convention (per I4)

Every `dropped` row's `notes` field begins with one of these prefixes, followed by a one-line justification:

| Prefix | Meaning | Required extra |
|---|---|---|
| `wontfix:` | permanently declined; will not be revisited | -- |
| `refactor-required:` | pyright is right and the truth cannot be expressed without restructuring | tracking handle (issue link, TODO ref, or follow-on project name) |
| `duplicate:` | subsumed by another manifest row | `error_id` of the canonical row |
| `false-positive:` | pyright is wrong and no scoped suppression mechanism fits | brief upstream-bug reference if applicable |

## 6. Seams

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

## 7. Crystal

| | mechanical | real-bug | config-relax | config-exclude | stub-fix | stub-ignore |
|---|---|---|---|---|---|---|
| non-test | populated | populated | forbidden (I12) | forbidden (I7) | populated | populated |
| test | populated | populated | populated | forbidden (I7) | populated | populated |

Constraints:
- `(disposition = config-exclude)` is forbidden in both regions (I7). The column exists for triage to name and reject the mechanism explicitly.
- `(region = non-test, disposition = config-relax)` is forbidden (I12). Non-test errors are fixed by code change, stub work, or scoped per-line `# type: ignore[<rule_id>]` (which is `mechanical`).

All other cells are reachable; combinations work by manifest construction.

## 8. Workstream Ordering

Hard dependencies (must precede):
1. **Config & stub policy** (sweep lane; config rows + stub-fix rows on top-N stub sources). Output: post-config pyright snapshot.
2. **Triage**. Input: post-config snapshot. Output: complete manifest.
3. **Sweep** (parallel-safe across rows) and **Bugfix** (per-row, sequential within a file).
4. **Testing**. Input: rows with `status = done`. Output: pass/fail per row.

Re-entry: if Testing fails a row, that row's `status` returns to `in-progress` and re-enters its lane.

Parallelism note: if post-triage `disposition = real-bug` rate exceeds 30% of total rows, sub-divide the Bugfix lane by file (one bugfix worker per file, each consuming only rows whose `error_id` starts with that file's path).

## 9. Operational Policy

- **Emergency escape valve.** `SKIP=pyright git commit` is the documented way to bypass pre-commit when truly needed. Use sparingly; record each use in the commit message.
- **Library pinning.** For the duration of this work, `pyproject.toml` pins exact versions of `anthropic` and `textual` (the two largest stub-issue sources). Version bumps are out of scope.
- **Stub-dep tagging.** Stub-dependent rows (`disposition in {stub-fix, stub-ignore}`) tag `notes: stub-dep` so future library upgrades can audit and re-evaluate.

## 10. Triage Decision Tree

A worker with a fresh pyright finding follows this tree to assign exactly one disposition.

```
1. Does pyright complain about a third-party import or attribute it cannot see?
   YES -> Can a local stub or maintained stub package fix it?
            YES -> stub-fix.
            NO  -> stub-ignore.        (scoped # type: ignore[import] + reason)
   NO  -> continue.

2. Is there a code path -- reachable from a public entry, CLI, slash command,
   MCP tool, or executed test -- that would raise at runtime, OR does the
   finding violate a documented invariant?
   YES -> real-bug.                    (logic fix; verification: pyright+targeted)
   NO  -> continue.

3. Can the truth be made visible by adding annotation / narrowing / cast / a
   scoped # type: ignore[<rule_id>] with reason, without restructuring code?
   YES -> mechanical.
   NO  -> continue.

4. Is the finding in test code, AND can a per-rule severity downgrade in an
   executionEnvironments block resolve it cleanly?
   YES -> config-relax.                (test region only; never non-test)
   NO  -> continue.

5. The finding cannot be resolved within scope.
   -> dropped, with notes prefix:
        - refactor-required:<tracker>     (pyright right; needs restructuring)
        - false-positive:<reason>         (pyright wrong; no scoped fix fits)
        - duplicate:<canonical_error_id>
        - wontfix:<reason>
```

Forbidden outcomes (Skeptic / triage rejects any row matching these):
- `disposition = config-exclude` in any region (I7).
- `disposition = config-relax` AND `region = non-test` (I12).
- `disposition = mechanical` paired with a bare `# type: ignore` (no rule_id) (I5).
- `disposition = mechanical` AND `lane = bugfix`, or `disposition = real-bug` AND `lane = sweep` (I2).
- `disposition = dropped` AND `region = non-test` (I9).
- `disposition = dropped` without one of the four notes prefixes `wontfix:` / `refactor-required:` / `duplicate:` / `false-positive:` (I4).
- File-level `# pyright: ignore` or `[tool.pyright].exclude` entry for any test file, including `test_phase_injection.py`, `test_computer_info_modal.py`, `test_model_selection.py` (I8).

## 11. Invariants

- I1: Sum of manifest rows == count of findings in the post-config snapshot at triage time, plus rows added by re-triage.
- I2: No row has `disposition = mechanical` in the bugfix lane, and no row has `disposition = real-bug` in the sweep lane.
- I3: Final pyright snapshot reports 0 errors. Final manifest has every row at `status in {done, dropped}`.
- I4: Every `dropped` row's `notes` field begins with one of `wontfix:`, `refactor-required:`, `duplicate:`, or `false-positive:`, followed by a one-line justification. `refactor-required:` rows additionally include a tracking handle (issue link, TODO ref, or follow-on project name).
- I5: No `# type: ignore` is added without a `rule_id` selector.
- I6: No suppression-baseline file is introduced. Pre-commit fails on any new error from day one.
- I7: No row has `disposition = config-exclude` in any region. Test-region config changes use `config-relax` only.
- I8: No file-level pyright carve-out (`[tool.pyright].exclude` entry, whole-file `# pyright: ignore`) is added for any test file, including `test_phase_injection.py`, `test_computer_info_modal.py`, `test_model_selection.py`.
- I9: No row with `region = non-test` may have `status = dropped` or `disposition = dropped`. Non-test errors are fixed.
- I10: Every row with `disposition = mechanical` whose `proposed_fix` contains `# type: ignore` has `audited_by` populated by an agent distinct from the row's author, before `status = done`.
- I11: `git commit` pre-commit wall-clock on a representative no-op edit is not regressed vs. pre-cleanup baseline. Both timings recorded in `specification/snapshots/precommit-walltime.txt`.
- I12: No row has `region = non-test` and `disposition = config-relax`. Non-test region accepts no rule relaxation; only `mechanical`, `real-bug`, `stub-fix`, or `stub-ignore` dispositions are valid for non-test rows.

## 12. Out of Scope

- Adopting pyright `strict` mode anywhere new.
- Refactoring beyond the minimum needed to fix a flagged finding.
- Touching files not referenced by any manifest row.
- Modifying tests for reasons unrelated to a manifest row.
- Type-checker swap (mypy, pyre, ty).
- Pyright major-version upgrade.
- `anthropic` or `textual` version bumps during this work (s 9).

## 13. Artifacts Produced

- `specification/manifest.jsonl` -- the manifest defined in s 5; one JSON object per line.
- `specification/snapshots/<timestamp>.txt` -- pyright snapshots before config, after config, after sweep, after bugfix, final. The `pre-config` snapshot additionally records the active `[tool.pyright].exclude` list verbatim alongside the error output.
- `specification/snapshots/precommit-walltime.txt` -- pre-cleanup and post-cleanup `git commit` pre-commit wall-clock timings on a representative no-op edit (per I11).
- `specification/config-changes.md` -- list of every `pyproject.toml` diff applied, with row-id references.
- `specification/real-bugs.md` -- one entry per `disposition = real-bug` row. Required columns: `error_id`, `bug` (one-line description), `fix` (one-line description), `regression_test_node_id`, `runtime_intent`. Allowed values for `runtime_intent`: `raise`, `skip`, `default:<v>`, `propagate`. Required for every fix touching `reportOptionalMemberAccess` or any None-narrowing; recommended for all real-bug rows.

Rationale for the decisions in this document lives in `SPECIFICATION_APPENDIX.md`.
