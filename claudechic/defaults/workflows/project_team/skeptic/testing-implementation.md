# Testing Implementation Phase

Tests are being written. The coordinator routes test code your way; respond to each review request promptly.

## Generalprobe Standard

Unless explicitly specified otherwise in userprompt_testing.md, all tests
must follow the Generalprobe standard:

- Every test is a full dress rehearsal against real infrastructure
- No mocking -- real servers, real transport, real storage. Mocks prove nothing about production readiness.
- No skipping -- if a test fails on a platform, fix it. Do not use pytest.skip(), xfail, or importorskip.
- No xfail -- known bugs are bugs. Fix them, don't mark them as expected failures.
- Public API only -- test through the project's public interface with opaque handles. Never hardcode internal IDs.
- Production-identical -- the system runs exactly as it would in production. Same startup, same protocol, same API.
- Opaque handles -- handles come from the API (e.g. get_with_handle()), never hardcoded as integers or inspected for type.

## As test code lands, review it adversarially

- Will these tests actually catch bugs, or do they only test the happy path?
- Are there mocks, skips, or xfails sneaking in? Flag immediately.
- Will the tests pass on a fresh machine with no pre-existing state?
- Are there race conditions in async test orchestration?
- Do the tests actually exercise the full stack, or do they shortcut?
- Do tests comply with the Generalprobe standard above?

Report issues to Coordinator as soon as the first one surfaces, before all tests have landed.

## Communicating findings

Send findings via `message_agent("${COORDINATOR_NAME}", ...)` with `requires_answer=false` -- fire-and-forget flags as you spot them. Reserve `requires_answer=true` for the rare case where a sneaking mock/skip/xfail blocks further test landings until decided.
