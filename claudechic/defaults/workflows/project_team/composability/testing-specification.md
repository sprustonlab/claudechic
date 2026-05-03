# Testing Specification Phase

Read ${CLAUDECHIC_ARTIFACT_DIR}/userprompt_testing.md to understand what tests are planned.

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

## Review the testing vision through your lens

- What are the test axes? (locality, capability, operation, topology)
- Does the proposed test file structure reflect those axes cleanly?
- Are fixture compositions clean? (no cross-axis branches in test code)
- Is the coverage matrix complete? Any crystal holes?

## Spec self-containment

- Every term used in the spec is defined inside the spec.
- References to other files drift out of sync as the spec iterates. A reference is permitted only when you commit to keeping the referenced file in sync. If you cannot commit, inline the content or drop the reference.
- A stale reference is a violation.

When editing the spec -- at any phase after synthesis -- add only operational facts. Do not narrate reasoning, justify decisions, or reference prior states inline. If the rationale matters, add it to the appendix instead.
