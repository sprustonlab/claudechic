# Testing Phase

1. Review test coverage -- are all paths tested?
2. Check for tests that only exercise defaults (wiring untested)
3. Completeness matters more than elegance in tests
4. A verbose test that catches bugs is better than no test
5. Report gaps to Coordinator for TestEngineer to fix

## Communicating findings

Send gap reports via `message_agent("${COORDINATOR_NAME}", ...)` with `requires_answer=false` -- testing-phase reviews are fire-and-forget memos to the coordinator who routes to TestEngineer. Use `requires_answer=true` only when a coverage gap is severe enough to block the phase.
