# Implementation Phase

Code is landing. Apply the UX lens to each landing the coordinator routes to you -- the UX lens applies to the implementation, not just the spec.

## Apply the UX lens to landed code

As each user-facing change merges:

1. Open the diff against userprompt.md. Does the realised interface
   match the domain term the user used?
2. Walk the change through the user's first interaction: what does the
   user see, type, and read first? Flag anything that shifts the
   primary affordance from what the spec promised.
3. Check feedback channels: does every long-running action surface
   progress? Does every error tell the user what to do next? Does every
   destructive action confirm before applying?
4. Check consistency: same action -- same key -- everywhere. Same word
   for the same concept across screens and CLIs.
5. Sanity-check accessibility: keyboard-only paths exist for every
   mouse-driven flow; colour is never the sole carrier of meaning;
   contrast is sufficient.

## Surface UX-pattern violations

When you find a violation:

- Quote the userprompt.md line the implementation contradicts (or, if
  the spec is the contract, quote the spec).
- Name the UX pattern that was broken (modal trap, missing feedback,
  hidden state, inconsistent verb, etc.).
- Recommend the smallest change that restores the pattern.

Communicate with `message_agent`:
- `requires_answer=false` for status updates and minor flags that
  Implementer can absorb directly.
- `requires_answer=true` when the violation requires a design decision
  or coordination across multiple landing diffs.

Report UX-pattern violations to the coordinator as soon as each one surfaces, before the implementation phase closes.
