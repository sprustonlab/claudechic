# Testing Specification Phase

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
