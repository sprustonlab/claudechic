# Composability Analysis -- workflow_engine_test

## Scope note

This run is a **smoke test of the claudechic workflow engine** (per
`STATUS.md` and `userprompt.md`), not a real product specification. STATUS.md
explicitly allows that "subsequent phases may be exercised lightly." This
document therefore exercises the specification-phase machinery (file write
under `specification/`) without inventing a fictitious product to dissect.

If the user wants a genuine composability analysis of a real target, they
should restart with a vision other than "test the workflow engine."

## Domain understanding

Stated domain: the claudechic workflow engine itself (phase transitions,
artifact-dir binding, MCP tools, manifest loading). The engine is what is
under test, but the *deliverable* of this run is observational
("does the engine behave?"), not architectural.

## Latent axes (workflow engine, for the record)

If we did treat the engine as the subject, the natural axes visible from
the codebase layout (`claudechic/workflows/`, `claudechic/defaults/`,
`claudechic/hints/`, `claudechic/checks/`, `claudechic/guardrails/`) are:

1. **Manifest tier** -- package | user | project (3-tier loader walk).
2. **System** -- workflow | rule/guardrail | hint | check (each a leaf
   module with declared import boundary).
3. **Phase lifecycle** -- the ordered list of phase IDs in a workflow.
4. **Enforcement level** (rules) -- deny | warn | log.
5. **Transport** (agent comms) -- ask_agent | tell_agent | interrupt_agent.

The compositional law that already holds: **frozen dataclasses /
Protocol ABCs at every system seam** (`CheckResult`, `HintSpec`, `Rule`,
`Phase`, `LoadResult`). Data crosses; mutable state does not.

## Crystal holes / smells observed during this smoke test

- **Hot-reload hole:** Disk edits to manifests (e.g., the
  `tutorial:echo_injection` fix) are not picked up by an already-running
  session. `get_phase` still reports the stale injection. This is a
  legitimate **leaky seam between persistence (disk) and runtime
  (in-memory registry)** -- changing one side does not propagate to the
  other without a restart. Worth tracking even if out of scope here.
- **Phase-prompt assembly:** During the leadership phase I received only
  `composability/identity.md`; phase-specific overlays
  (`specification.md`, `implementation.md`) appeared on phase advance.
  This is the intended algebraic composition (identity + phase = prompt)
  and confirms the seam is clean.

## Recommendation

No deep-dive Composability sub-agents needed for this run. If the user
later wants the workflow engine itself audited, the obvious target is
the **disk -> in-memory registry** seam (the hot-reload hole).
