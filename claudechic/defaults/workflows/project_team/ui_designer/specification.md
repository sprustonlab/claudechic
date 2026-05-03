# Specification Phase

Re-read your identity.md to refresh the domain-first UX lens. Read
userprompt.md to ground every UX claim in the user's exact words.

## Apply the UX lens to the specification

1. Identify every user-facing surface the spec proposes (TUI screens, CLI
   verbs, GUI panels, output formats). List them by name; do not
   summarize.
2. For each surface, ask: does the proposed shape match the domain term
   the user used? A "mindmap editor" is not a tree-view; a "dashboard"
   is not a log tail. Flag mismatches by quoting the user verbatim.
3. Walk the spec for hidden interface assumptions (modal vs modeless,
   keyboard vs mouse-first, sync vs streaming feedback). Surface every
   assumption that is not explicit in the spec.
4. Check that the spec names interaction patterns -- not just data
   shapes -- where they matter (selection, focus, undo, error recovery,
   long-running progress).

## Verify D1 with UserAlignment

D1 is the user's domain decision -- the choice between mechanism-global
vs activation-per-workflow scopes that the spec phase resolves. Before
signing off on the specification, message UserAlignment to confirm:

- Has the user explicitly authorized the chosen domain scope?
- Are the user's domain words preserved verbatim in the spec, or have
  they been paraphrased into engineering terminology?
- If wording shifted, has the user approved the change?

Use `message_agent` with `requires_answer=true` for the D1 check;
without an answer, the specification is not approvable from the UX lens.

## Report

Send your findings to the coordinator with:
- A bullet list of UX-pattern violations or domain mismatches.
- The exact user quote each violation contradicts.
- A recommended remediation per violation (rewrite, clarify, or escalate
  to user).
