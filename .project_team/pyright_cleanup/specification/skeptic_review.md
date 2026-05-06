# Skeptic Review -- composability.md

Reviewer: skeptic
Date: 2026-05-04
Subject: `specification/composability.md` (Composability spec for pyright_cleanup)

## Summary

The manifest-as-single-source-of-truth design is sound and addresses several of my pre-spec risks. Lane separation (sweep vs bugfix), the Crystal's forbidden cell (`non-test, config-exclude`), and Seam 4's stub-fix re-snapshot are real gains. Below: what is closed, what remains open, and minimal amendments.

## Risks closed by the spec

- **S4 (test exclusion forfeits signal):** CLOSED. `config-exclude` is a per-row disposition, not a wholesale tests/ exclude. Each test error is triaged. Signal preserved.
- **I1 (count integrity):** Strong -- manifest sum == snapshot count.
- **I3 (no non-test config-exclude):** Strong -- forces real fixes in production code.

## Risks NOT addressed (ranked by severity)

### G1 -- HIGH: No review gate on `disposition = mechanical` that resolves via `# type: ignore`

I6 requires a rule_id selector but nothing prevents the triage worker from labeling a real bug as `mechanical` with `proposed_fix = "add # type: ignore[reportOptionalMemberAccess]"`. I2 keeps lanes pure but does not audit the classification itself. **The moral hazard is in disposition assignment, which I2 does not protect.**

### G2 -- HIGH: `real-bugs.md` does not require runtime semantic intent

Spec says entries are "bug, fix, regression test node_id." A None-narrowing fix can mean raise / skip / default with very different runtime behavior. Without explicit intent, fixes silently change behavior. (S3 unaddressed.)

### G3 -- MEDIUM: No emergency escape, no library pin policy

S5 + S7 not in spec. Once pyright is a hard pre-commit blocker, contributors need a documented escape valve and stub regressions on upgrade need a policy.

### G4 -- LOW: Bugfix lane bottleneck if real-bug rate is high

S1 partial. Manifest is robust to any bug rate, but Workstream Ordering says Bugfix is "per-row, sequential within a file." If the re-sample reveals >40% real bugs, this lane becomes the critical path with no parallelism plan.

### G5 -- LOW: Current pyright excludes not enumerated

S6 unaddressed. `build/.venv/dist/site/__pycache__` are mentioned in STATUS.md but not pinned in the spec. Future drift goes unnoticed.

## Lane-purity invariant I2 -- is it strong enough?

**No.** I2 prevents lane *contamination* (a row in the wrong lane) but not lane *misrouting* (a row classified into the wrong disposition). The classification step has no second eye. Recommend adding a triage-audit invariant.

## Minimal amendments proposed

1. **Add invariant I7 (audit gate):** "Every row with `disposition = mechanical` whose `proposed_fix` contains `# type: ignore` requires a second-agent audit field `audited_by: <agent>`. Audit confirms the error is not a real bug suppressed."
2. **Strengthen Artifacts -- `real-bugs.md`:** add required column `runtime_intent` -- one of `raise`, `skip`, `default:<value>`, `propagate`. Reject entries without it.
3. **Add Out-of-Spec -> Out-of-Scope clarifier OR new section "Operational policy":** document (a) `SKIP=pyright` emergency escape, (b) anthropic/textual version pinning during this work, (c) stub-dependent rows tagged with `notes: stub-dep` for upgrade-PR audit.
4. **Add Snapshot enumeration:** the first snapshot (`pre-config`) must record the active `[tool.pyright].exclude` list verbatim so future drift is visible in diff.
5. **Add to Workstream Ordering note:** "If post-triage real-bug count > 30% of total, Bugfix lane is sub-divided by file to enable parallel implementers."

These are minimal: no new artifacts, no new agents, no new phases. Each is one field or one sentence.

## What I am NOT proposing

- No new layer of agents.
- No restructuring of seams.
- No expansion of scope.
- No second manifest format.

The spec's bones are right; the gaps are at the edges.
