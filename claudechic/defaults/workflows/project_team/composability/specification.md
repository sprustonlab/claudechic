# Specification Phase

1. Review userprompt.md through the composability lens
2. Identify axes relevant to this project
3. Test orthogonality -- do choices on one axis constrain others?
4. Find and define clean seams between axes
5. Report to Coordinator: axes, laws, potential crystal holes
6. Spawn axis-specific agents for deep review if needed
7. Write findings to specification/composability.md

## Spec self-containment

- Every term used in the spec is defined inside the spec.
- References to other files drift out of sync as the spec iterates. A reference is permitted only when you commit to keeping the referenced file in sync. If you cannot commit, inline the content or drop the reference.
- A stale reference is a violation.

When editing the spec -- at any phase after synthesis -- add only operational facts. Do not narrate reasoning, justify decisions, or reference prior states inline. If the rationale matters, add it to the appendix instead.
