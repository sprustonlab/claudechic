# STATUS -- pyright_cleanup

**Project:** pyright_cleanup
**Working dir:** /groups/spruston/home/moharb/claudechic
**Artifact dir:** /groups/spruston/home/moharb/claudechic/.project_team/pyright_cleanup
**Branch:** develop (clean working tree at start)
**Started:** 2026-05-04

## Vision Summary (approved)

**Goal:** Make pyright pre-commit usable on claudechic by eliminating all errors in non-test code and fixing genuine bugs surfaced by pyright in tests.

**Value:**
- Pre-commit is currently broken (307 errors), slowing every commit.
- Pyright has flagged ~25% of errors as likely real bugs worth surfacing.
- Restoring a working type-check gate prevents regression.

**Domain terms:**
- **Real bug** -- pyright finding reflecting genuine logic error (e.g. unchecked None access on a value that can be None at runtime).
- **Mechanical fix** -- annotation, `type: ignore`, or narrow-the-type adjustment with no runtime change.
- **Stub issue** -- error from missing/incorrect third-party type stubs.
- **Test-typing exclusion** -- pyright exclude or relaxed ruleset for `tests/`.

**Success looks like:**
- `uv run pyright` exits clean (0 errors) on non-test code.
- Tests excluded OR only mechanical errors remaining; all triaged real bugs in tests fixed.
- `pre-commit run --all-files` passes end-to-end.
- Written record of which test errors were classified as real bugs, what was fixed, what was deferred/excluded.
- Pyright config in `pyproject.toml` reflects chosen test-handling strategy.

**Failure looks like:**
- Pre-commit still fails on a clean tree.
- Fixes that mask real bugs with `type: ignore` instead of correcting logic.
- Excluding so much pyright becomes ceremonial.
- Scope creep into strict-mode adoption or unrelated refactoring.
- Runtime regressions introduced while fixing types.

## Initial Survey (from Vision phase research)

- **Total:** 307 errors, 1 warning, 0 info
- **Files affected:** 37 of 130 (~28%)
- **Distribution:** 209/307 (68%) in tests; 12 in `app.py`; rest spread across modules
- **Top error types:**
  - `reportArgumentType` (130, 42%)
  - `reportAttributeAccessIssue` (69, 22%)
  - `reportOptionalMemberAccess` (66, 21%)
- **Top files:**
  - test_phase_injection.py (49)
  - test_computer_info_modal.py (35)
  - test_model_selection.py (17)
  - test_constraints_decomposition.py (17)
  - test_crystal_sweep.py (12)
  - app.py (12)
- **Pyright config:** baseline strictness; excludes build/.venv/dist/site/__pycache__
- **Pre-commit:** `uv run pyright` is a hard blocker (no allowlist/threshold)
- **Complexity sample (n=20):** ~35% mechanical, ~25% real bugs, ~15% trivial, ~15% stub/import, ~10% hard

## Phase Log

- [x] **Vision** -- approved by user 2026-05-04
- [ ] **Setup** -- in progress
- [ ] Leadership
- [ ] Specification
- [ ] Implementation
- [ ] Testing
- [ ] Sign-Off
