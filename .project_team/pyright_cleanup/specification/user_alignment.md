# User Alignment -- Specification Phase

**Project:** pyright_cleanup
**Phase:** Specification
**Author:** user_alignment
**Date:** 2026-05-04

## 1. Original Request (source of truth)

From `userprompt.md`:

> I want to know if we should invest in fixing all the pyright issues.

After investigation, user chose **Level B**:

> Fix all non-test pyright errors AND triage / fix genuine bugs surfaced by
> pyright in the test suite. Mechanical test errors may be excluded or
> relaxed via config.

Stated pain (from spawn brief):

> Pyright is failing pre-commit and slowing you down, not usable as it is now.

## 2. Core Requirements (extracted)

R1. **All non-test pyright errors fixed.** Not "most." Not "the easy ones." All.
R2. **Genuine bugs in tests are triaged and fixed.** Real-bug findings in test
    code must be corrected, not silenced.
R3. **Mechanical test errors may be excluded or relaxed via config.** This is
    a permission, not a directive -- exclusion is allowed where errors are
    purely mechanical, but it is not the goal.
R4. **Pre-commit must become usable again.** The user's pain is workflow
    friction; a green run is necessary but the spec should also avoid making
    pre-commit slower.

## 3. User's Exact Wording (watch for drift)

| User said | Meaning to preserve |
|-----------|---------------------|
| "fix" non-test errors | Code change that resolves the diagnostic. NOT `# type: ignore` blanket suppression unless the finding is provably a stub bug. |
| "triage / fix genuine bugs" in tests | Two-step: classify each test error, then fix the genuine-bug subset. Triage record must be visible. |
| "Mechanical test errors **may** be excluded" | Permissive, not mandatory. Spec should not default to wholesale `exclude = ["tests/"]` without justification. |
| "all the pyright issues" (original ask) | User's mental model is comprehensive cleanup. Anything left behind needs an explicit, recorded reason. |

**Wording-change flags for the spec authors:**

- If the spec uses **"suppress"** where the user said **"fix"** -- flag it.
- If the spec uses **"silence"** or **"ignore"** as a primary verb for non-test
  errors -- flag it. Non-test errors must be *fixed*, per R1.
- If the spec replaces **"genuine bugs"** with **"obvious bugs"** or **"easy
  bugs"** -- flag it. "Genuine" means real-at-runtime, regardless of fix
  difficulty.
- If the spec talks about a **"pyright baseline"** or **"allowlist"** file --
  flag it. The user did not authorize a baseline; this needs explicit user
  approval (see checkpoint Q2 below).

## 4. Domain Terms (verify shared understanding)

The Vision Summary defines these correctly. Re-stating for the spec:

- **Real bug** -- pyright finding that reflects a genuine runtime logic error
  (e.g. unchecked `None` access on a value that is `None` at runtime).
  *Fix the logic, do not suppress.*
- **Mechanical fix** -- annotation, narrow-the-type adjustment, or targeted
  `# type: ignore[<rule>]` with no behavior change. Allowed everywhere.
- **Stub issue** -- error from missing/incorrect third-party stubs.
  Resolution: install stubs, add narrow ignore, or report upstream.
- **Test-typing exclusion** -- pyright `exclude` entry or relaxed ruleset
  scoped to `tests/`. Permitted by R3 for *mechanical* errors only.

**Term the spec must NOT silently introduce:**

- "Strict mode adoption" -- explicitly listed as a Failure mode in Vision.
- "Type-checker swap" (mypy, pyre, etc.) -- not asked for.
- "Pyright major-version upgrade" -- not asked for.

## 5. Vision Gaps the Spec Should Close

Two Success criteria from the Vision are under-specified for the user's pain:

G1. **Regression prevention is implicit.** Vision says a working type-check
    gate "prevents regression" but Success criteria do not forbid a baseline
    file that would silently re-accumulate errors. Spec should state policy.

G2. **Developer-flow restoration is not measured.** User said "slowing you
    down." A green pre-commit that takes 90s on every commit still slows them
    down. Spec should at least note pre-commit wall-clock as non-regressing.

## 6. Scope Risks for the Spec

S1. **Default-to-exclude tests.** Easiest path to a green run, but loses the
    ~25%-real-bugs signal in 209 test errors. The user wants those triaged
    (R2). Spec must show a triage step BEFORE any exclusion.
S2. **Mass `# type: ignore` in non-test code.** Violates R1 (user said "fix").
    Allowed only for documented stub issues.
S3. **Refactoring beyond what pyright requires.** Vision lists "unrelated
    refactoring" as a Failure mode. Spec must scope changes tightly.
S4. **Adding new dependencies (stub packages).** In-scope if mechanical;
    flag any non-stub dependency addition.

## 7. User Checkpoint Answers (LOCKED 2026-05-04)

User answered all three policy questions in chat. Coordinator confirmed
these are locked and must NOT be re-litigated by spec authors.

Q1. **Test-handling policy: RELAXED RULESET, NOT EXCLUSION.**
    Use `[tool.pyright.executionEnvironments]` scoped to `tests/`. Pyright
    must continue to type-check `tests/` so real bugs surface; the ruleset
    is loosened, not the file set. Spec authors who write
    `exclude = ["tests/"]` are violating user direction.

Q2. **Baseline / allowlist file: FORBIDDEN.**
    No `pyright-baseline.json` or equivalent. Pre-commit must hard-fail
    on any new pyright error from the moment cleanup lands. This is the
    enforcement of G1 and is now a hard requirement, not a recommendation.

Q3. **Throwaway test files: NONE pre-authorized.**
    Top offenders (`test_phase_injection.py` 49, `test_computer_info_modal.py`
    35, `test_model_selection.py` 17) get the same triage as everything
    else. Real bugs in those files must be fixed; mechanical errors in
    those files are covered by Q1's relaxed ruleset, not by file-level
    exclusion.

## 8. Alignment Verdict

**Status:** [OK] ALIGNED with the approved Vision and with the three
checkpoint answers now LOCKED (section 7). Spec authors must:

1. Use the user's exact verbs ("fix", "triage") in success criteria.
2. Include an explicit Success criterion for G1: "no suppression baseline
   file introduced." (Hard requirement per Q2.)
3. Include an explicit Success criterion for G2: "normal `git commit`
   pre-commit wall-clock not regressed."
4. Use "relaxed ruleset" / `[tool.pyright.executionEnvironments]` for
   tests. Do NOT write `exclude = ["tests/"]` (per Q1).
5. Apply the same triage to `test_phase_injection.py`,
   `test_computer_info_modal.py`, `test_model_selection.py` as everywhere
   else (per Q3). No file-level carve-outs.
6. Keep strict-mode, type-checker swap, pyright major upgrade, and
   unrelated refactoring explicitly out of scope.

**Spec sign-off block:** I will not approve a SPEC.md draft missing
items 2, 3, or 4 above.

## 9. Override Note re: Skeptic

If Skeptic recommends "just exclude `tests/` and move on," that conflicts
with R2 ("triage / fix genuine bugs"). User Alignment overrides: triage
must precede exclusion. Skeptic may simplify the *implementation* of triage
but cannot remove it.
