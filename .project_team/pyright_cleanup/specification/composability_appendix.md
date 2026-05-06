> **SUPERSEDED:** see `SPECIFICATION_APPENDIX.md`. This file is retained as authoring history.

# Composability Spec -- Appendix (Rationale)

Source: rationale extracted from `specification/composability.md`. This file holds the *why*; the spec holds the *what*. To be merged into a unified `SPEC_APPENDIX.md` once other leads contribute.

## A1 -- Why only two axes (Region, Fix-kind)

Region and Fix-kind are the only choices that change *what a worker does*. Error type (`rule_id`) and file partition the work but do not change the procedure; treating them as axes would create `N_rules x F` implementer specializations without reducing risk. They remain useful for batching within a lane, but not as compositional dimensions.

## A2 -- Why the manifest is the law

The manifest-as-law eliminates combinatorial branching: any `(region, disposition)` pair is handled by reading the row and following the `lane` and `verification` fields. Without it, every implementer would re-derive disposition from source, multiplying the chance of the same error being touched twice or by the wrong lane.

New disposition values can be added later by extending the schema and the lane/verification derivation rules; no implementer needs to learn about new error types.

## A3 -- Why config-first ordering

Exclusions and stub fixes can erase tens to hundreds of errors at once. Triaging before config-and-stub work would spend triage effort on rows that the next config commit deletes. The post-config snapshot is the stable input to triage.

## A4 -- Why split Sweep and Bugfix lanes

The cognitive modes differ:
- Sweep is batch pattern-matching: low per-row cost, parallel-safe across rows, verification by pyright snapshot delta.
- Bugfix is per-incident investigation: high per-row cost, requires understanding runtime behavior, verification by targeted test.

Mixing them in one worker makes either mode lose discipline -- sweep workers slow down on every row "just in case it's a real bug," and bugfix workers cut corners by reaching for `# type: ignore`. The lane-purity invariant (I2) enforces the split mechanically: sweep rows never carry `disposition = real-bug` and bugfix rows never carry mechanical dispositions.

## A5 -- Why JSONL for the manifest

Selected by Coordinator. JSONL gives:
- Stable git diffs (one row per line; row edits do not reflow neighbors).
- `jq`-friendly filtering by `lane`, `status`, `disposition`.
- No quoting issues when `notes` contain commas, quotes, or rule messages.

CSV was the alternative; it loses on diff stability when fields contain commas.

## A6 -- Why I5 (no bare `# type: ignore`)

A bare `# type: ignore` silences every rule on a line, including rules added by future pyright versions. Requiring `# type: ignore[<rule_id>]` keeps suppression scoped to a known signal and makes audit trivial: a grep for `type: ignore` shows exactly which rules were silenced and why (when paired with the manifest `notes` field).

## A7 -- Why I6 (no suppression-baseline file)

A baseline file lets pre-commit pass with N pre-existing errors hidden, deferring the work indefinitely. The user's stated goal is a working type-check gate, not a ratchet. Forbidding the baseline forces the cleanup to actually finish and prevents a "we'll fix it later" regression vector.

## A8 -- Why I7 (no `config-exclude` anywhere) and why `config-relax` is its own disposition

The user-approved Vision success criterion is "0 errors on non-test code." A `config-exclude` on non-test source would meet the letter of pyright but defeat that criterion. Per-line `# type: ignore[rule]` on a non-test file is permitted because it is classified as `mechanical` (a localized, reviewed annotation), not as `config-exclude` (a file- or directory-level pyright opt-out).

The user separately approved relaxed rulesets for tests but explicitly rejected exclusion. An earlier draft conflated the two as a single `config-exclude` value, which would have let a worker silently swap one mechanism for the other. Splitting into `config-relax` and `config-exclude` forces the choice into the manifest where it is reviewed.

`config-relax` (per-rule severity downgrade, `executionEnvironments` overrides) keeps files in pyright's view at a calibrated severity. `config-exclude` removes them. The semantics differ, the auditability differs, and the user's preference applies to one but not the other.

I7 forbids `config-exclude` everywhere because the test-region rationale (relax, do not hide) is identical to the non-test-region rationale.

## A9 -- Why I8 (no file-level test carve-out)

The three named files are the highest-error test files. A file-level carve-out would close most of the test backlog with one keystroke and erase the chance to find real bugs surfaced by pyright. I8 forces those errors through triage like any other.

## A10 -- Why I9 (no dropped non-test rows)

`dropped` is a triage outcome for rows that turn out to be non-issues (duplicates, false positives, deferred refactors). For non-test code the success criterion is hard zero; a `dropped` non-test row would be an error pyright still reports. I9 closes that loophole.

## A11 -- Why I4 strengthened (justification prefixes)

Free-text `notes` on dropped rows do not survive review. Prefix tokens (`wontfix:`, `refactor-required:`, `duplicate:`, `false-positive:`) make the manifest greppable for audit and make the dropping decision categorically explicit. `refactor-required:` requires a tracking handle so deferred work does not vanish.

## A12 -- Why I10 (audit on `# type: ignore` mechanicals)

`# type: ignore` is the easiest way to silence a real bug under the guise of a mechanical fix. A second-agent audit creates the cheapest possible check: the row author proposes, a different agent confirms it is genuinely mechanical (no runtime behavior hidden). The `audited_by` field makes the audit trail part of the manifest rather than a side conversation.

## A13 -- Why I11 (wall-clock not regressed)

The user's underlying complaint is that pre-commit is slow and broken. Fixing "broken" while making it slower trades one form of unusability for another. Recording timings before and after with the same trivial diff catches regressions deterministically.

## A14 -- Why `runtime_intent` on real-bug entries

Pyright surfaces a None deref but does not say what the correct runtime behavior is: should the code raise, skip, default, or propagate the None? Different answers imply different fixes and different regression tests. Forcing the author to pick one of a small enum prevents "fix" commits that silence pyright while leaving the bug.

The field is mandatory for None-narrowing fixes (the largest real-bug class per the initial survey: `reportOptionalMemberAccess` is 21% of all errors) and recommended for the rest.

## A15 -- Why pre-config snapshot records the exclude list

Pyright's effective error set depends on what is excluded. Without recording the exclude list alongside the snapshot, a future reader cannot tell whether 307 errors meant "across the whole repo" or "with X already hidden." Storing both makes the baseline reproducible and audit-friendly.

## A16 -- Why pin anthropic and textual

Both are heavy stub-issue sources. A version bump mid-cleanup would invalidate stub-fix rows already done, possibly creating new errors that look like regressions. Pinning lets the manifest reflect a single library state for the duration of the work.

## A17 -- Why parallelize Bugfix by file when real-bug rate > 30%

Bugfix is sequential within a file (one fix can change the surrounding code's types and create or eliminate other errors in the same file). Across files it is parallel-safe. The 30% threshold is the rough point at which a single bugfix worker becomes the critical path; below that, the overhead of coordination outweighs the parallelism gain.

## A18 -- Why I12 (no non-test `config-relax`)

`config-relax` exists to let tests use pyright at a calibrated lower severity (the user's approved test mechanism). Extending it to non-test code would re-open the door I7 closed: relaxing a rule until the non-test error stops being reported is functionally indistinguishable from hiding it. The non-test success criterion is "0 errors at the same baseline severity"; I12 makes that machine-checkable by forbidding the only remaining mechanism that could silently lower the bar.
