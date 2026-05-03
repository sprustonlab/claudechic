# Terminology Review: workflow_engine_test (smoke test)

## Scope Note

This run is a workflow-engine smoke test, not a real feature build. There is
no application domain to canonicalize — the only "domain" is the claudechic
workflow engine itself, whose terms are already defined in `STATUS.md`. This
file exists to exercise the specification phase's artifact-write path.

## Domain Terms (from `userprompt.md` + `STATUS.md`)

| Term | Canonical definition | Canonical home |
|------|----------------------|----------------|
| Workflow engine | Phase-driven coordinator system in `claudechic/workflows/engine.py` | `STATUS.md` Vision section |
| Artifact dir | Bound on-disk directory holding workflow outputs (STATUS, specs, etc.) | `STATUS.md` Vision section |
| Phase | Discrete step in a workflow (Vision, Setup, Leadership, Specification, Implementation, Testing, Documentation, Sign-Off) | `STATUS.md` Vision section |
| Injection | Hook entry registered against a phase (e.g. `PreToolUse/Bash`) | `claudechic/defaults/workflows/*/manifest.yaml` |
| Rule | Guardrail entry loaded for the active phase set | `claudechic/defaults/global/rules.yaml` |

## Synonyms Found

None of concern. (`artifact dir` vs `artifact directory` appears in tool
descriptions vs prose — minor, acceptable.)

## Overloaded Terms

- "phase" is used both for the *current* engine state and for *items in the
  phase list*. In context this is unambiguous; no fix needed for a smoke test.

## Orphan Definitions

None. All terms used in `STATUS.md` are defined in `STATUS.md`.

## Canonical Home Violations

None within this artifact dir.

## Newcomer Blockers

- `tutorial:echo_injection` shows up in `get_phase` output even though the
  active workflow is `project-team`. A newcomer would ask "why is a tutorial
  injection live here?" — this is a known not-hot-reloaded artifact noted in
  the vision-phase smoke-test report; not a terminology issue.

## Recommendation

No terminology action required. Smoke-test specification phase exercised
successfully: artifact write under `specification/` works, phase advanced
from `leadership` -> `specification` cleanly.
