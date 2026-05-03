# Specification Phase

1. Wait for all Leadership agents to report findings
2. If UI-heavy project, spawn UIDesigner
3. If Researcher active, request prior art investigation
4. Composability spawns axis-agents for deep review
5. Synthesize all findings into specification document
   - Keep the spec strictly operational: what to build, how it connects, what constraints apply
   - Move all non-operational content to a separate appendix file (e.g. SPEC_APPENDIX.md): architecture decision rationale, rejected alternatives, "what NOT to do" lists, and historical context
   - Research findings belong in their own files (e.g. RESEARCH.md), not in the spec or appendix
   - Implementer and test agents read the spec -- if content would confuse them or waste their attention, it belongs in the appendix or a separate file
6. Present to user

Handle user response:
- **Approve** -> proceed to implementation
- **Modify** -> incorporate feedback, re-present
- **Redirect** -> adjust approach, re-present
- **Fresh Review** -> close Leadership, spawn fresh team

## Spec self-containment

- Every term used in the spec is defined inside the spec.
- References to other files drift out of sync as the spec iterates. A reference is permitted only when you commit to keeping the referenced file in sync. If you cannot commit, inline the content or drop the reference.
- A stale reference is a violation.

When editing the spec -- at any phase after synthesis -- add only operational facts. Do not narrate reasoning, justify decisions, or reference prior states inline. If the rationale matters, add it to the appendix instead.
