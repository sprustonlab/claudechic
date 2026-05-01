# Testing Specification Phase

Re-read your identity.md to refresh your terminology lens.
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

- What test naming conventions should be used? (file names, function names)
- Are terms in the testing vision consistent with the project glossary?
- Any ambiguous or overloaded terms in test descriptions?
