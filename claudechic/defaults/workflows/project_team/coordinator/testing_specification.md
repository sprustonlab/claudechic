# Testing Specification Phase

## Step 0: Confirm with the user before delegating

`userprompt_testing.md` was approved at the end of testing-vision, but
days or messages may have passed. Before delegating spec synthesis to
Leadership:

1. Briefly confirm with the user that `userprompt_testing.md` still
   reflects their intent.
2. Ask if there are scoping constraints, infrastructure preferences,
   or out-of-scope items they want forwarded to Leadership.
3. Wait for the user's reply before kicking Leadership off.

This is a checkpoint, not a re-vision pass. If the user signals
significant change in intent, return to testing-vision rather than
papering over it here.

Leadership reviews the testing vision and produces a concrete test spec.

## Steps

1. Inform all Leadership agents that we are in the testing specification phase.
   They already have implementation context -- now they review test design.

2. Ask each Leadership agent to review the testing vision (userprompt_testing.md):
   - Composability: test axes, fixture composition, coverage matrix
   - Terminology: test naming conventions, term consistency
   - Skeptic: what will break, infrastructure risks, missing coverage
   - UserAlignment: do test cases cover all user requirements?

3. Synthesize Leadership findings into TEST_SPECIFICATION.md:
   - Test file structure (one file per concern)
   - conftest.py fixtures (infrastructure setup/teardown)
   - For each test file: test functions with descriptions
   - Infrastructure requirements (servers, VMs, ports, etc.)
   - Testing standard compliance checklist

4. Present to user. Iterate until approved.

The test spec is strictly operational -- what to build, how it connects,
what constraints apply. Move rationale to an appendix.

## Spec self-containment

- Every term used in the spec is defined inside the spec.
- References to other files drift out of sync as the spec iterates. A reference is permitted only when you commit to keeping the referenced file in sync. If you cannot commit, inline the content or drop the reference.
- A stale reference is a violation.

When editing the spec -- at any phase after synthesis -- add only operational facts. Do not narrate reasoning, justify decisions, or reference prior states inline. If the rationale matters, add it to the appendix instead.
