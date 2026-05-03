# Testing Specification Phase

Re-read your identity.md to refresh your testing-standard lens.
Read ${CLAUDECHIC_ARTIFACT_DIR}/userprompt_testing.md to understand what
tests are planned.

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

## Review checklist (TestEngineer lens)

Walk the proposed test specification and answer each:

- Does every planned test exercise real infrastructure end-to-end? Flag any that drop into mocks, fakes, or in-process stubs.
- Is each test reachable through the public API alone? Flag any that hardcode internal IDs or inspect implementation types.
- Are fixtures composed once at the right scope (session / module / function)? Flag duplicated setup or teardown gaps.
- Do error-path tests assert on observable behavior, not exception classes from internal modules?
- Are timeouts and pytest invocation conventions present (per `global:pytest_needs_timeout`, `global:no_bare_pytest`)?
- Does the coverage matrix list one test file per concern? Flag bundled files that hide axes.

Report gaps to the coordinator with the failing checklist item and the
proposed remediation. Use `message_agent` with `requires_answer=false`
for findings; use `requires_answer=true` only when a decision is needed.
