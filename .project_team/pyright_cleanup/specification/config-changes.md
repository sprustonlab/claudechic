# Config Changes Log -- pyright_cleanup

Tracks every `pyproject.toml` diff applied during this project, with row-id
references where applicable. Per SPECIFICATION.md s 13.

Format: one entry per change, newest at the bottom.

---

## C1 -- Pin anthropic and textual

**Date:** 2026-05-05
**Workstream:** WS-A3 (config policy)
**Spec basis:** SPECIFICATION.md s 9 Operational Policy; APPENDIX A16
**Manifest rows:** none (pre-triage; baseline change)

Diff (`pyproject.toml`, `[project].dependencies`):

```diff
-    "anthropic>=0.75.0",
+    "anthropic==0.97.0",
...
-    "textual>=7.4.0",
+    "textual==8.2.4",
```

Rationale: both libraries are heavy stub-issue sources. Pinning the exact
installed versions for the duration of pyright_cleanup ensures the manifest
reflects a single library state and prevents version-bump-induced regressions
that would invalidate stub-fix rows already done.

Effect on snapshot: none (versions were already 0.97.0 / 8.2.4 in the venv).

## C2 -- Add executionEnvironments block scoped to tests/

**Date:** 2026-05-05
**Workstream:** WS-A3 (config policy)
**Spec basis:** SPECIFICATION.md s 6 Seam 1; user_alignment.md Q1; I7+I8
**Manifest rows:** none yet (initial scaffold; future `config-relax` rows
will amend this block per Seam 1 amendment protocol)

Diff (`pyproject.toml`, end of `[tool.pyright]` region):

```diff
 [tool.pyright]
 exclude = ["build", ".venv", "dist", "site", "**/__pycache__"]
+
+# Test-region rule relaxation lives in this block (see
+# .project_team/pyright_cleanup/SPECIFICATION.md s 6 Seam 1, s 9, and
+# user_alignment.md Q1). The block is scoped to tests/ and exists so that
+# triage-driven `config-relax` manifest rows can downgrade specific rules
+# here. tests/ remains type-checked: only individual rule severities may
+# be lowered. `[tool.pyright].exclude` of tests/ is forbidden by I7+I8.
+# Initial state: no rule overrides; sweep amends per manifest.
+[[tool.pyright.executionEnvironments]]
+root = "tests"
+extraPaths = ["."]
```

Rationale: the user-locked test-handling policy is "relaxed ruleset, NOT
exclusion" (user_alignment.md Q1). The `executionEnvironments` block is the
mechanism. We register it now with NO rule overrides so the post-config
snapshot has the same error population as pre-config -- triage decides which
rules merit `config-relax` per row, and amendments to this block are then
linked to specific manifest rows in this file.

Why `extraPaths = ["."]`: setting `root = "tests"` alone causes pyright to
treat `tests/` as a separate source root, which breaks `from claudechic...`
imports inside test files (verified empirically: a first attempt without
`extraPaths` produced 582 errors). Adding the project root back via
`extraPaths` restores import resolution while keeping the per-environment
override scope intact.

Effect on snapshot: none (same 307 errors; same rule distribution).

---

## Snapshot delta summary (pre-config -> post-config)

| Region | Pre-config | Post-config | Delta |
|---|---|---|---|
| Total | 307 | 307 | 0 |
| Non-test | 46 | 46 | 0 |
| Test | 261 | 261 | 0 |

| Rule | Non-test | Test |
|---|---|---|
| reportArgumentType | 15 | 115 |
| reportAttributeAccessIssue | 4 | 65 |
| reportOptionalMemberAccess | 9 | 57 |
| reportCallIssue | 0 | 20 |
| reportMissingImports | 12 | 1 |
| reportIncompatibleVariableOverride | 2 | 0 |
| reportUndefinedVariable | 2 | 1 |
| reportOptionalOperand | 0 | 2 |
| reportRedeclaration | 1 | 0 |
| reportAssignmentType | 1 | 0 |

Note: STATUS.md initial survey reported 209 test / 98 non-test based on a
file-path heuristic. The accurate split from the parsed snapshot is
261 test / 46 non-test (some files outside `tests/` were originally
classified as tests in error). Triage operates on the accurate split.

## C3 -- Test-region per-rule downgrade

**Date:** 2026-05-05
**Workstream:** WS-C step 1 (sweep)
**Spec basis:** SPECIFICATION.md s 6 Seam 1 amendment; user_alignment.md Q1
**Manifest rows:** 200 resolved (197 `disposition: config-relax` + 3
`disposition: mechanical` whose rule was incidentally also downgraded -- see below)

Diff (`pyproject.toml`, inside the `[[tool.pyright.executionEnvironments]] root="tests"` block):

```diff
 [[tool.pyright.executionEnvironments]]
 root = "tests"
 extraPaths = ["."]
+# C3 (per .project_team/pyright_cleanup/specification/config-changes.md):
+# downgrade three rules in tests/ to silence stub-class-as-protocol noise
+# (`_StubLoader` / `SimpleNamespace` / `_MockApp` substituted for typed
+# parameters), Mock attribute access, and `SdkMcpTool[Any]` callability.
+# Resolves the 197 manifest rows tagged `disposition: config-relax`.
+# `reportOptionalMemberAccess` and `reportOptionalOperand` stay at error
+# severity so genuine None-derefs continue to surface in tests.
+reportArgumentType = "none"
+reportAttributeAccessIssue = "none"
+reportCallIssue = "none"
```

Rationale: per SPECIFICATION.md s 10 step 4, test-region findings whose
fix is a per-rule severity downgrade get `disposition: config-relax`. The
197 rows tagged accordingly in the manifest are dominated by:

- `reportArgumentType` (115): stub-class-as-protocol pattern -- `_StubLoader`
  / `SimpleNamespace` / `_MockApp` substituted for `ManifestLoader` /
  `ChatApp` / `Agent`. These are deliberate test fakes; pyright correctly
  flags the type mismatch but the test pattern is intended.
- `reportAttributeAccessIssue` (62): Mock attribute access on
  `MagicMock` / `AsyncMock` instances + union-narrowing noise on textual /
  rich `RenderableType` (`.plain`, `.text` accesses on
  `ConsoleRenderable | RichCast | str | Visual | SupportsVisual`).
- `reportCallIssue` (20): `SdkMcpTool[Any]` instances are callable at
  runtime via the SDK's `tool` decorator but pyright sees the resulting
  type as not-callable.

The two rules that catch genuine runtime defects in tests
(`reportOptionalMemberAccess`, `reportOptionalOperand`) stay at error
severity, so any None-deref the tests would actually crash on continues
to surface as a pyright finding -- preserving the user-locked Q1
contract that "tests must continue to type-check; the ruleset is
loosened, not the file set".

### Erased mechanical rows (Seam 4 analogue for config-relax)

Three rows originally tagged `disposition: mechanical` are also erased
by C3 because their `rule_id` is among the three downgraded rules and
their `region` is `test`. These had been triaged as per-line negative-test
ignores (`# pyright: ignore[reportAttributeAccessIssue]  # negative test:
<Symbol> is the assertion subject`); the C3 downgrade silences them
project-wide in `tests/` ahead of the per-line edit. Per Seam 4 logic
(spec text refers to `stub-fix`; same principle applies to `config-relax`
erasure), these rows are marked `status: done` with `disposition`
unchanged from `mechanical` -- the original triage decision describes
how they were classified, the `notes` field records that the actual
resolution mechanism was C3 rather than the per-line ignore. (Defensive
per-line ignores are NOT added; if C3 is ever reverted, these three rows
would correctly re-surface in a fresh snapshot and re-enter the manifest
via re-triage.)

The three rows:

```
tests/test_awareness_install.py:223:47:reportAttributeAccessIssue   # ContextDocsDrift
tests/test_scope_guard.py:74:47:reportAttributeAccessIssue          # GuardrailsModal
tests/test_scope_guard.py:112:47:reportAttributeAccessIssue         # DiagnosticsModal
```

(The 4th negative-test row, `tests/test_scope_guard.py:53:14:reportMissingImports`,
is NOT erased by C3 -- `reportMissingImports` was not downgraded.
That row remains pending and gets the per-line ignore in a later batch.)

### Effect on snapshot

Pyright total: **307 -> 101** (-206).

| Bucket | Pre-C3 | Post-C3 | Delta | Resolved by |
|---|---:|---:|---:|---|
| Non-test total | 46 | 40 | -6 | Bug-Fix Implementer (cluster_dispatch.py x6, parallel) |
| Test config-relax rules (3 rules combined) | 200 | 0 | -200 | C3 |
| Other test rules | 61 | 61 | 0 | (mechanical sweep batches) |
| Total | 307 | 101 | -206 | |

I10 audit queue effect: -3 rows (the three erased negative-test mechanical
rows had `# pyright: ignore` proposed_fixes that are no longer applied).
New audit queue size: 16 rows. Will report to coordinator after the
batch-resolved-rows status update lands in the manifest.

## Stub-fix evaluation (WS-A4)

No proactive stub-fix candidates were applied in WS-A. Rationale:

- The 12 non-test `reportMissingImports` errors target internal modules
  (`scripts.audit`, `claudechic.cluster`), not third-party stubs. They are
  candidates for `mechanical` (scoped `# type: ignore[import]`) or
  `real-bug` triage, not `stub-fix`.
- The 1 test-region `reportMissingImports` is `tests.conftest`, also
  internal.
- Remaining errors come from pyright correctly using anthropic / textual /
  rich stubs and finding type mismatches at use sites; no missing or
  incomplete stub to install.
- Per Seam 4, any `stub-fix` rows discovered during triage will trigger a
  fresh snapshot batch when applied.

`[tool.pyright].stubPath` is not yet configured. If triage produces any
`stub-fix` rows, that directory and config entry must be added before sweep
can apply them (per APPENDIX open-item 2).
