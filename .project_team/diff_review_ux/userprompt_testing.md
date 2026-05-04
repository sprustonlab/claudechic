# Testing Vision -- diff_review_ux

## What I want

**Behaviors of users tested.** Not coverage. Not implementation details.

A test is one complete thing a user does. End-to-end. The kind of sentence I'd say in plain English:

> "I have these files, I click diff, I click hide, I unhide, I use the keyboard."

That is one test. The whole arc. Not separate tests for hide-via-keyboard, hide-via-click, unhide, navigation -- those are a single user workflow, so they're a single test.

Another sentence is another test:

> "I edit a file, commit it, click diff, the file is gone from the sidebar."

That's one test (covers #11/#18).

The number of tests = the number of distinct user workflows. Probably small.

## What I do NOT want

- **Coverage.** I don't care which lines are exercised. Tests motivated by "this branch isn't covered" are not what we're building.
- **Mocking.** Tests use a real directory on disk and real git. If the implementation runs `git status`, the test runs `git status` against a real repo fixture. No `mock.patch`, no fake filesystems, no in-memory git.
- **Granular per-method unit tests.** A test for `is_hidden`'s truth table or `_to_prefix`'s edge cases is below the goal. If a user can't see a behavior change, it's not what we're testing.
- **The 17-test plan from `SPEC_APPENDIX.md` section I treated as a literal manifest.** That plan was an early exhaustive enumeration; this vision rescopes around user workflows. Some of the workflow tests in that appendix probably align; revisit at testing-specification.

## What I might still want manual

The session-lifetime check (close claudechic, reopen, hide state is gone) is reasonable to do once by hand at sign-off rather than automate. Other manual items only if a workflow truly cannot be expressed as code-driving-the-app.

## Inspiration

At testing-implementation phase, TestEngineer reads the recent test commits in `git log` to match the repo's style for behavior-style tests. NOT now -- not at the vision stage.

## What would make this phase feel like a failure

- TestEngineer mocks the filesystem or git rather than using a real directory.
- The test count balloons to 17+ fine-grained units.
- Tests pass but a user driving the real `/diff` flow finds an obvious bug the suite missed.
- Tests assert on internal state (e.g. `HideState.hide_files` set membership) instead of user-observable outcomes.
- Existing 849 tests are touched / weakened to make new tests pass.

## What success looks like

- A handful of user-workflow tests. Each one named for the workflow it walks.
- A user reading the test names can tell immediately which user-flows are covered.
- Real-disk, real-git fixtures. Deterministic, reasonable runtime.
- Existing 849 tests still pass.
