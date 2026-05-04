# Testing Vision Phase

The implementation is complete. Now plan the tests.

## Step 1: ASK BEFORE DRAFTING

Do NOT draft `userprompt_testing.md` until you have asked the user
what they want from this phase and received their reply. The artifact
must reflect the user's voice and intent, not your guess from the
spec or implementation.

Open-ended questions to ask (pick the relevant ones; do not interrogate):

- What would make this test phase feel successful to you? Failed?
- Rough scope: smoke test, full coverage, regression-only, exploratory?
- Manual checks, automated tests, or both? Which parts of each?
- Anything off-limits (slow tests, network, GPU, real external services)?
- Specific scenarios, edge cases, or past bugs you want covered?
- Existing test conventions in this project to follow or avoid?

Wait for the user's reply. If anything is ambiguous, ask follow-ups
before drafting. Do not assume the SPECIFICATION's scope equals the
test phase's scope.

## Step 2: Apply the testing standard

When drafting `userprompt_testing.md`, layer the Generalprobe standard
on top of the user-provided intent: every test is a full dress
rehearsal against real infrastructure. No mocking, no skipping, no
xfail, public API only, production-identical.

Also search for project-specific testing rules:
- CLAUDE.md (testing conventions section)
- HOW_TO_WRITE_TESTS.md or similar
- Existing test files (conftest.py, fixtures, naming patterns)

If the project has its own standard, incorporate it. Generalprobe
principles + project-specific rules + the user's stated intent
together form the testing standard captured in
`userprompt_testing.md`.

## Step 3: Draft, present, loop, approve

1. Read STATUS.md and SPECIFICATION.md to understand what was built.
2. Search for project-specific testing rules (see above).
3. Draft `userprompt_testing.md` from the USER'S answers in Step 1:
   - **What to test** -- concrete test cases mapped to spec sections
   - **How to test** -- real infrastructure setup (servers, VMs, processes)
   - **Testing standard** -- Generalprobe + project-specific rules
   - **Success criteria** -- "tests pass" means what? (use the user's words)
   - **Failure criteria** -- what would make these tests meaningless?
4. Present to user. Loop until approved -- incorporate feedback
   verbatim where possible rather than paraphrasing.
5. Get explicit user approval ("approved", "ship it", or equivalent)
   before advancing the phase. Do not advance on silence.

## Leadership Carries Over

The same Leadership agents from the implementation phase are still active.
They have full context on what was built. Do NOT spawn new Leadership --
inform the existing agents that we are entering the testing sub-cycle.

Ask Leadership to shift their lens:
- **Composability**: What test axes exist? What combinations matter?
- **Terminology**: What test naming conventions should we follow?
- **Skeptic**: What will be hardest to test? What will break?
- **UserAlignment**: Do the test cases cover all user requirements?
