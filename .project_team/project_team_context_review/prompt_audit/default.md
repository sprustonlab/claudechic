# prompt_audit/default.md

**Role:** `default` -- catch-all `agent_type` for sub-agents spawned without `type=`.
**Source:** **No folder. No identity.md. No phase mds.** Not a typed role; it is the absence-of-role.

Glossary: `GLOSSARY.md`. Authority contract: skeptic R3.

---

## 1. What "default-roled" agents are

Per `agent_folders.assemble_agent_prompt` (post-slot-3 fix from `abast_accf332_sync`):

- A `default-roled` agent is a sub-agent created with no explicit `agent_type`. The field is the literal string `"default"` (not `None`, not falsy -- F7 closure).
- The agent has no `<role>/identity.md` to inject.
- The agent has no `<role>/<phase>.md` to inject.
- The constraints segment fires whenever global-namespace rules apply (e.g. `global:no_rm_rf`, `global:no_bare_pytest`, `global:warn_sudo`).
- The environment segment fires when its workflow has opted in (place-axis §3; project_team opts in for v1).

## 2. F8 / F9 disposition

**F8** -- prior implementation returned `None` for default-roled agents with no role dir, dropping the constraints injection entirely. The post-slot-3 fix (`agent_folders.py:L304-L308`) now returns the constraints block alone. SPEC §D parity restored. **F8: closed-by-spec via place-axis empty-bytes contract.**

**F9** -- empty-digest emitted a 138-char placeholder ("## Constraints / _no rules apply..._") in standing-by prompts. The L221-L222 short-circuit (`if not rules_rows and not check_rows: return ''`) currently mitigates -- but only when both rules AND advance-checks are empty. The place-axis spec extends this to a per-segment empty-bytes contract: every `render_<segment>` returns `""` when its source content is empty, and the composer drops the empty segment. **F9: closed-by-spec.**

## 3. Q5 answer (LOCKED)

*"Default-roled agents (no role dir) -- do they receive constraints injection?"*

**Yes.** Per `agent_folders.py:L304-L308`, default-roled agents receive the constraints segment when applicable rules exist. SPEC §D matches impl. Prior-run "unresolved" comes from the historic `None`-return bug that has since been fixed (M-component). Q5 is closed.

## 4. Per-(time, place) cell map

| Time | identity | phase | constraints | environment |
|---|---|---|---|---|
| T1 spawn | empty (renderer-empty; no role dir) | empty (renderer-empty) | fires when applicable rules exist | fires when workflow opted in |
| T2 activation | n/a (default-roled is sub-agent, not main) | n/a | n/a | n/a |
| T3 phase-advance.main | n/a | n/a | n/a | n/a |
| T4 broadcast | empty (renderer-empty) | empty (renderer-empty) | **fires (F1 floor)** | fires when opted in |
| T5 post-compact | empty | empty | re-fires | re-fires when opted in |

**Critical invariant:** at T4 broadcast, default-roled agents receive the constraints segment via the F1 structural floor. They are NOT skipped via `agent_type == DEFAULT_ROLE` check (that fix landed in `abast_accf332_sync` M1: the broadcast loop now uses `== DEFAULT_ROLE` rather than falsy check).

**Wait, F7 nuance:** today's mcp.py:1018 broadcast skips `agent_type == DEFAULT_ROLE` recipients. Time-axis spec §3 (Q3 / F1) recommends:
- `gate(T4, identity, "default", ...) = false` (no role dir to render anyway)
- `gate(T4, phase, "default", ...) = false` (no phase.md)
- `gate(T4, constraints, "default", ...) = true` (F1 floor)
- `gate(T4, environment, "default", ...) = true` (when opted in)

This **expands** T4's recipient set: default-roled agents now receive constraints + environment on broadcast where today they're skipped entirely. Time-axis spec §4 names this as a behavioral change.

## 5. Standing-by classification

Default-roled agents are always standing-by under the v1 static definition (no `default/<phase>.md` exists or could exist). Standing-by is not a meaningful classification for them -- they receive constraints + environment regardless. Per gating-axis 1a:

- `spawn / identity / default-roled` -> renderer-empty (no role dir); gate stays True.
- `spawn / phase / default-roled` -> renderer-empty.
- `spawn / constraints / default-roled` -> True (F8 closure).
- `spawn / environment / default-roled` -> True (project_team opt-in).

## 6. Identity edits

**N/A.** No `default/identity.md` to edit. Default-roled is the absence-of-role.

## 7. Future considerations (out of scope v1)

- A `defaults/workflows/<wf>/default/identity.md` could in theory be authored to give default-roled agents a workflow-aware orientation segment. Not requested today; would conflict with the env-segment-as-platform-fact framing. Skip.

## 8. Review status

- **Self-review:** **N/A.** No agent of role `default` to engage; default-roled agents are anonymous sub-agents that don't outlive their tasks.
- **Implementer transient confirmation:** N/A (no identity.md to confirm). Verification happens through F1/F7/F8/F9 regression tests during Implementation -- a default-roled spawn receives constraints (test asserts present); a broadcast reaches default-roled recipient (test asserts present); placeholder text is absent (test asserts byte-identical empty when no rules apply).

---

*Author: role-axis. Specification phase. Q5 LOCKED. F8/F9 closed-by-spec.*
