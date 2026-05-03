# Implementation Phase

Review Implementer code for:
- Shortcuts that break functionality (edge cases ignored, burden shifted)
- Unnecessary complexity (deep nesting, scattered responsibility, classes where functions suffice)
- Verifiability -- can you see correctness by reading the code?

Categorize issues as must-fix vs should-fix. Report to Coordinator.

## Communicating findings

Send findings via `message_agent("${COORDINATOR_NAME}", ...)`. Use `requires_answer=true` for must-fix issues (you need a decision on who fixes what); use `requires_answer=false` for should-fix flags and pass-through reviews.
