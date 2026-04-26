# Testing Phase

1. Read the project's testing standard (CLAUDE.md, HOW_TO_WRITE_TESTS.md, or similar) before writing or fixing any test
2. Fix test failures identified by TestEngineer
3. Run only the specific test file relevant to your fix
4. Follow the testing standard and patterns established by existing tests
5. Report fixes to Coordinator

Do NOT run the full test suite -- that is TestEngineer's job.
Do NOT introduce mocks, skips, or xfails -- fix the root cause instead.
