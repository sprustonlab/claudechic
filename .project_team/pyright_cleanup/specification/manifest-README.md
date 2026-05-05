# Manifest README

`manifest.jsonl` is the law per SPECIFICATION.md s 4. One JSON object per
line; fields per s 5.1. This README documents the operational conventions
applied during construction of the WS-B output, plus the precise sweep
edits that the row dispositions imply.

## Construction rules

### One row per pyright finding

A "finding" in s 2.1 is `(file, line, col, rule_id, message)`. Pyright
sometimes emits multiple diagnostic lines at the same `(file, line, col,
rule_id)` -- typically one line per branch of a union type
(`ConsoleRenderable | RichCast | str | Visual | SupportsVisual`, etc.).
We treat each diagnostic line as a separate finding (per s 2.1 word for
word) and create one manifest row for each, satisfying I1 exactly:

```
manifest rows == post-config snapshot finding count == 307
```

### error_id collision suffix

When N>1 findings share `(file, line, col, rule_id)`, the first row uses
the schema-prescribed pattern `<relpath>:<line>:<col>:<rule_id>` and
subsequent rows append `#2`, `#3`, ... so error_id stays unique. Example:

```
tests/test_computer_info_modal.py:163:36:reportAttributeAccessIssue
tests/test_computer_info_modal.py:163:36:reportAttributeAccessIssue#2
tests/test_computer_info_modal.py:163:36:reportAttributeAccessIssue#3
tests/test_computer_info_modal.py:163:36:reportAttributeAccessIssue#4
tests/test_computer_info_modal.py:163:36:reportAttributeAccessIssue#5
```

All five rows describe the same code-level issue and share an identical
disposition + proposed_fix. The sweep applies the fix once; verification
recognises that all five collapse together when re-snapshotted.

### Scoped suppression form (M3)

`# pyright: ignore[<rule_id>]` is the canonical form, NOT
`# type: ignore[<mypy-code>]`. Pyright does not match the bracket value
to its rule names (the selector is decorative for pyright), but using
the pyright-native rule_id makes the cited rule align with the manifest
row's `rule_id` field, which:

- Is greppable: `rg "# pyright: ignore\[reportXxx\]"` returns exactly the
  sites resolved by manifest rows of that rule.
- Survives a future move from pyright to a different type checker that
  parses the bracket value -- the next checker can pattern-match on
  pyright rule names rather than mypy codes that don't apply.

Examples (from manifest proposed_fix entries):

| Old (mypy form, REJECTED) | New (pyright form, IN USE) |
|---|---|
| `# type: ignore[attr-defined]` | `# pyright: ignore[reportAttributeAccessIssue]` |
| `# type: ignore[import-not-found]` | `# pyright: ignore[reportMissingImports]` |
| `# type: ignore[no-redef]` | `# pyright: ignore[reportRedeclaration]` |

I5 (no bare ignore) is enforced by the build_manifest validator on both
forms: any `# pyright: ignore` or legacy `# type: ignore` in proposed_fix
must carry a non-empty bracket selector.

### Negative-test reason wording (M4)

Rows that ignore a finding inside a `with pytest.raises(<exc>):` block
(verifying that a symbol is intentionally absent) use the exact reason:

```
# pyright: ignore[<rule_id>]  # negative test: <Symbol> is the assertion subject
```

A validator (build_manifest.py M7) confirms that `<Symbol>` literally
appears on the source line for each row that uses this wording. Catches
copy-paste regressions like the M1 bug where `tests/test_scope_guard.py:112`
once cited `GuardrailsModal` (the line at L74) instead of
`DiagnosticsModal` (the symbol actually on L112).

### `notes: assert-narrow` convention (M5)

Every test mechanical `reportOptionalMemberAccess` / `reportOptionalOperand`
row carries `notes: assert-narrow; ...` (no schema change; the prefix is
greppable). Lets a future audit pass select these rows specifically:

```
jq -r 'select(.notes | startswith("assert-narrow"))' manifest.jsonl
```

## Triage policy summary

Per SPECIFICATION.md s 10. Encoded by file/rule patterns in
`.project_team/pyright_cleanup/specification/build_manifest.py` for
reproducibility.

### Non-test region (46 rows)

| Disposition | Count | Notes |
|---|---:|---|
| `mechanical`  | 40 | Annotation, narrowing assert, scoped pyright ignore, or import correction. Includes 11 `scripts.audit` rows + 1 `claudechic.cluster` row reclassified per coordinator M2 (internal-runtime-resolvable, not stub-dep). |
| `real-bug`    |  6 | `cluster_dispatch.py` -- all six call sites of `_get_backend_module()` deref `mod._<method>` without a None guard |
| `stub-ignore` |  0 | No third-party stub gaps in the post-config snapshot |

`config-relax`, `config-exclude`, `dropped` -- forbidden in non-test region (I7, I9, I12).

### Test region (261 rows)

| Disposition | Count | Notes |
|---|---:|---|
| `config-relax` | 200 | Per-rule downgrade in `[[tool.pyright.executionEnvironments]] root="tests"` for `reportArgumentType`, `reportAttributeAccessIssue`, `reportCallIssue`. Dominated by stub-class-as-protocol, Mock attribute access, and `SdkMcpTool[Any]` callability noise. Downgrading silences the noise without losing the signals (`reportOptionalMemberAccess`, `reportOptionalOperand`) that catch real None-derefs. **Includes 3 negative-test `reportAttributeAccessIssue` rows in `test_awareness_install.py` and `test_scope_guard.py` originally triaged as `mechanical+ignore`; reclassified post-WS-C per Composability so `disposition` reflects the actual resolving mechanism (C3) rather than the original counterfactual proposal.** |
| `mechanical`   | 61 | Mostly `reportOptionalMemberAccess` post-fixture narrowing failures (assert is-not-None); 1 negative-test `# pyright: ignore[reportMissingImports]` row in `test_scope_guard.py:53` (the only negative-test row whose rule is NOT downgraded by C3, so per-line ignore is the actual resolving mechanism) |

No test row is `dropped` or `real-bug` -- triage classifies all
`reportOptionalMemberAccess` findings in tests as mechanical because the
test currently passes (per "reachable from a pytest node" in s 2.1: a
crashing test would indicate a real bug; a passing test with a None deref
flagged by pyright is mechanical narrowing pedantry).

The 57 test `reportOptionalMemberAccess` mechanical rows are sample-audited
by Skeptic via `s3_audit_sample.md` (7 rows across 6 files); pass clears
all 57 for sweep, fail directs reclassification of failing rows.

## Sweep edits implied by config-relax rows

When the sweep processes `config-relax` rows, it amends
`pyproject.toml` `[[tool.pyright.executionEnvironments]] root="tests"`
to add:

```toml
reportArgumentType = "none"
reportAttributeAccessIssue = "none"
reportCallIssue = "none"
```

This is one config edit that resolves all 197 `config-relax` rows. The
sweep records the edit in `config-changes.md` as entry C3, references the
rows it resolves, and re-runs `uv run pyright` to capture a post-relax
snapshot per Seam 4.

## Audit-required rows (I10): 16 total

`build_manifest.py`'s validator counted 16 mechanical rows whose
`proposed_fix` includes `# pyright: ignore`. Each requires `audited_by`
populated by an agent distinct from the row's author before
`status = done` (I10). All 16 are populated with `audited_by: skeptic`
per Skeptic's verdict round.

History: count was 7 at initial triage; M2 added 12 internal-import rows
(reclassified from `stub-ignore`) bringing it to 19; Composability's
post-WS-C reclassification of the 3 C3-erased negative-test
`reportAttributeAccessIssue` rows from `mechanical` to `config-relax`
removed them from the I10 queue, settling at 16.

```
# Negative-test ignore (1; the only one whose rule is NOT covered by C3)
tests/test_scope_guard.py:53:14:reportMissingImports                # claudechic.paths

# Runtime monkey-patch / duck-type ignores (3)
claudechic/_patches.py:60:22:reportAttributeAccessIssue
claudechic/_patches.py:149:14:reportAttributeAccessIssue
claudechic/hints/engine.py:174:32:reportAttributeAccessIssue

# Internal-runtime-resolvable imports (12; reclassified from stub-ignore per M2)
claudechic/audit/audit.py:482:10:reportMissingImports
claudechic/audit/audit.py:693:10:reportMissingImports
claudechic/audit/audit.py:769:10:reportMissingImports
claudechic/audit/audit.py:783:10:reportMissingImports
claudechic/audit/audit.py:803:10:reportMissingImports
claudechic/audit/audit.py:822:10:reportMissingImports
claudechic/audit/audit.py:846:10:reportMissingImports
claudechic/audit/audit.py:875:10:reportMissingImports
claudechic/audit/audit.py:911:10:reportMissingImports
claudechic/audit/audit.py:973:10:reportMissingImports
claudechic/audit/audit.py:1006:10:reportMissingImports
claudechic/mcp.py:1747:14:reportMissingImports
```

**Removed from this list by Composability's post-WS-C reclassification**
(3 rows; these are now `config-relax` resolved by C3, not mechanical+ignore):

```
tests/test_awareness_install.py:223:47:reportAttributeAccessIssue   # ContextDocsDrift
tests/test_scope_guard.py:74:47:reportAttributeAccessIssue          # GuardrailsModal
tests/test_scope_guard.py:112:47:reportAttributeAccessIssue         # DiagnosticsModal
```

## Bug-Fix lane handoff

The 6 real-bug rows are all in
`claudechic/defaults/mcp_tools/cluster_dispatch.py`, all
`reportOptionalMemberAccess`, all caused by the same root cause:
`_get_backend_module()` can return `None` (lines 87 and 91), but the six
call sites at lines 123, 152, 231, 253, 290, 347 dereference
`mod._<method>` without a None guard.

Bug-Fix Implementer must:
1. Add a None guard at each of the six call sites that returns the same
   error response shape used elsewhere (`_error_response("backend module
   not loadable")`).
2. Author a new regression test
   `tests/test_cluster_dispatch_missing_backend.py::test_missing_backend_module_returns_error`
   simulating a missing backend file (referenced by the `verification`
   field of all six rows).
3. Fill in the `runtime_intent: raise` (return error response) and the
   fix description in `specification/real-bugs.md` per s 13.

Real-bug rate: 2.0% -- below the 30% threshold; single Bug-Fix worker
sufficient (no per-file split needed per s 8 / A17).
