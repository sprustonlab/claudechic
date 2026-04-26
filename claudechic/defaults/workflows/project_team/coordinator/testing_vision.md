# Testing Vision Phase

The implementation is complete. Now plan the tests.

## Testing standard

When drafting the testing vision, apply the Generalprobe standard:
every test is a full dress rehearsal against real infrastructure.
No mocking, no skipping, no xfail, public API only, production-identical.

Also search for project-specific testing rules:
- CLAUDE.md (testing conventions section)
- HOW_TO_WRITE_TESTS.md or similar
- Existing test files (conftest.py, fixtures, naming patterns)

If the project has its own standard, incorporate it. The Generalprobe
principles and the project-specific rules together form the testing
standard for userprompt_testing.md.

## Steps

1. Read STATUS.md and SPECIFICATION.md to understand what was built.
2. Search for project-specific testing rules (see above).
3. Draft userprompt_testing.md:
   - **What to test** -- concrete test cases mapped to spec sections
   - **How to test** -- real infrastructure setup (servers, VMs, processes)
   - **Testing standard** -- Generalprobe + project-specific rules
   - **Success criteria** -- what does "tests pass" mean?
   - **Failure criteria** -- what would make these tests meaningless?
4. Present to user. Iterate until approved.

## Leadership Carries Over

The same Leadership agents from the implementation phase are still active.
They have full context on what was built. Do NOT spawn new Leadership --
inform the existing agents that we are entering the testing sub-cycle.

Ask Leadership to shift their lens:
- **Composability**: What test axes exist? What combinations matter?
- **Terminology**: What test naming conventions should we follow?
- **Skeptic**: What will be hardest to test? What will break?
- **UserAlignment**: Do the test cases cover all user requirements?
