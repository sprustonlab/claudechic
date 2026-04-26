# Testing Implementation Phase

Tests are being written. Stay actively engaged -- do not wait to be asked.

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

## As test code lands, scan for

- Banned terms from the project glossary
- Inconsistent test naming (file names, function names)
- Test docstrings that use ambiguous or overloaded terms
- Any terminology drift from what was established in the specification phase
- Terms that contradict the Generalprobe standard (e.g. "mock", "stub", "skip")

Report violations to Coordinator immediately.
