# Testing Implementation Phase

## Spawn TestEngineer

Spawn with `type: test_engineer` and `requires_answer: true`.

The TestEngineer's prompt MUST include:
1. The project's testing standard location (from testing vision)
2. The TEST_SPECIFICATION.md path
3. The test file locations
4. How to run the tests

## Workflow

1. Spawn TestEngineer (type: test_engineer)
2. TestEngineer writes tests per TEST_SPECIFICATION.md
3. TestEngineer runs tests, reports failures
4. Route failures to Implementer agents for fixes
5. Iterate until all tests pass AND comply with testing standard
6. Leadership reviews test code:
   - Composability: test axes covered, no cross-axis branches
   - Skeptic: anything that will break in production?
   - UserAlignment: all user test cases implemented?
   - Terminology: naming conventions followed?
7. Exit when Leadership approves AND all tests pass

Do NOT write test code yourself -- delegate to TestEngineer and Implementers.

## Testing Standard Compliance

Before marking tests as complete, verify:
- No mocks (unittest.mock, MagicMock, patch)
- No skips (pytest.skip, xfail, importorskip)
- No hardcoded handles or internal type checks
- Tests use the public API with opaque handles
- Real infrastructure (servers, VMs, transport) is exercised
- Tests follow project-specific conventions from CLAUDE.md / HOW_TO_WRITE_TESTS.md
