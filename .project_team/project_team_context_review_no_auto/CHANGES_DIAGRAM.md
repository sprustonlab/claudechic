# Changes Overview

Audience: the user. Scope verification at a glance.
Reference: SPEC_bypass.md (full operational detail).

---

## Before (current state of claudechic)

### Injection model

```
                      assemble_agent_prompt()
                      |
     spawn ---------> |  identity.md
     activation ----> |  + phase.md
     phase-advance --> |  + constraints block  (monolithic, single render)
     post-compact ---> |
                      |
                      v
                   agent prompt string  (or None for default-roled agents -- bug)
```

- No injection-site argument. Callers all produce the same shape.
- No environment segment.
- constraints block: one monolithic renderer; no stable/phase split.
- phase advance: sub-agents receive no `assemble_agent_prompt` call at all (F1 -- bug).
- Standing-by agents: identity and phase always injected even when no phase file exists.
- Default-roled agents: function returned `None`; constraints lost (F8 -- bug).
- Empty-digest: emitted a 138-char placeholder string instead of empty (F9 -- bug).
- Coordinator advance-checks visible to all roles (no coordinator-only scoping).

Three segments, no gate:

| Segment | Content | Source |
|---------|---------|--------|
| identity | role definition, prime directive, authority statements; ALSO contains `## Communication` block (tool semantics + behavioral guidance -- phase-independent, static) | `<role>/identity.md` |
| phase | phase-specific instructions for the role | `<role>/<phase>.md` |
| constraints | all rules in one block: global + role-scoped + phase-scoped; advance-checks visible to every role (not coordinator-only) | `assemble_constraints_block()` (monolithic) |
| (no environment) | -- | -- |

### Configuration surface

No user-configurable knobs for:
- which sites receive the constraints segment
- output format of the constraints segment
- environment context (segment does not exist)

### Settings UI

No "Agent prompt context" section in `SettingsScreen`.

### Identity files

14 `project_team/<role>/identity.md` files each contain a `## Communication` block
(~11-12 lines each, 145 lines total). The block covers:
- tool semantics (what `message_agent`, `interrupt_agent`, `requires_answer` do)
- behavioral guidance (when to communicate, which `requires_answer` value to use)

Placement is static in the identity file regardless of which phase the agent is in.

### MCP inspector

`mcp__chic__get_agent_info` has no `compact` parameter.
Output format is fixed.

---

## After (this spec's proposed state)

### Injection model

```
time: InjectionSite  ->  gate(time, place, role, phase, settings, manifest) -> bool
                          |
                          v
     spawn             identity  phase  constraints_stable  constraints_phase  env*
     activation        identity  phase  constraints_stable  constraints_phase  env*
     phase advance      [--]    [--]**        --            constraints_phase   --
     after compact     identity  phase  constraints_stable  constraints_phase  env*

     * env fires subject to manifest opt-in + user settings
     ** identity and phase suppressed for standing-by roles (no <role>/<phase>.md)
```

Five named segments:

| Segment | Content | Source |
|---------|---------|--------|
| `identity` | role definition, prime directive, authority statements | `<role>/identity.md` |
| `phase` | phase-specific instructions for the role in that phase | `<role>/<phase>.md` |
| `constraints_stable` | global rules + role-scoped rules; carries the `## Constraints` heading | `assemble_constraints_block(slice="stable")` |
| `constraints_phase` | phase-scoped rules; coordinator-only advance-checks appended for coordinator role only | `assemble_constraints_block(slice="phase")` |
| `environment` | tool semantics (what `message_agent`, `interrupt_agent`, `requires_answer` do) + peer roster + name routing table + MCP coordination notes; workflow overlay adds 2-sentence role summaries | `defaults/environment/base.md` + `defaults/environment/project_team.md` |

Gate is a single pure function; no structural floor.
All (site, segment, role) cells are user-configurable.

### Configuration surface

```yaml
# user or project tier config.yaml
constraints_segment:
  compact: true           # true = compact-list (default), false = markdown-table
  include_skipped: false
  scope:
    sites: [spawn, activation, phase-advance, post-compact]

environment_segment:
  enabled: true           # overrides per-workflow manifest default
  compact: false          # false = all 4 pieces, true = name routing + peer roster only
  scope:
    sites: [spawn, activation, post-compact]
```

### Settings UI

New `"Agent prompt context"` section in `SettingsScreen`:

```
---- Agent prompt context -------------------------
  Compact rules block            on     [user]
    "Compact list by default; disable for the
     formatted markdown table."
  Rules block: advanced...       >      [user]

  Team coordination context      on     [user]
    "Inject the peer roster, name routing table,
     and MCP coordination notes."
  Compact coordination context   off    [user]
    "Omit the MCP tool list and coordination patterns."
  Coordination context: advanced...  >  [user]
```

`AdvancedConstraintsScreen` -- 4 checkboxes, all toggleable:

```
  [x] when an agent starts             (spawn)
  [x] when the workflow activates      (activation)
  [x] on phase advance                 (phase-advance)
  [x] after compaction                 (post-compact)
```

`AdvancedEnvironmentScreen` -- 3 checkboxes, all toggleable:

```
  [x] when an agent starts             (spawn)
  [x] when the workflow activates      (activation)
  [x] after compaction                 (post-compact)
```

No pinned rows. Clearing the last remaining checkbox triggers a one-line notice
and reverts the toggle (empty `scope.sites` is rejected at config-load time as
likely a typo; users must keep at least one site).

### Identity files

`## Communication` block removed from 14 role identity files (-145 lines total).
Content is split and re-homed:

| Part | Before | After |
|------|--------|-------|
| Tool semantics (what tools do) | identity.md | environment/base.md, injected at spawn / activation / after compact |
| Behavioral guidance (when/how) | identity.md | per-phase markdown, injected at phase advance |

Net prompt payload is unchanged; placement is phase-correct.

Five new phase markdown files are authored during Implementation:

| File | Activates when... |
|------|------------------|
| `test_engineer/testing-specification.md` | test_engineer in Specification phase |
| `test_engineer/testing-implementation.md` | test_engineer in Implementation phase |
| `ui_designer/specification.md` | ui_designer in Specification phase |
| `ui_designer/implementation.md` | ui_designer in Implementation phase |
| `user_alignment/implementation.md` | user_alignment in Implementation phase |

### MCP inspector

`mcp__chic__get_agent_info` accepts an optional `compact: bool` parameter (default `false`).

| `compact` | Output |
|-----------|--------|
| `false` (default) | formatted markdown table regardless of user-tier setting |
| `true` | compact-list form |

User-tier `constraints_segment.compact` is NOT consulted; the parameter is the sole control.

---

## Change list (concise)

### Engine (agent_folders.py)

1. Add `InjectionSite` + `PromptSegment` enumerations and `RenderContext` frozen dataclass.
2. Extract `_render_identity`, `_render_phase` from `assemble_agent_prompt`.
3. Split constraints renderer into `_render_constraints_stable` + `_render_constraints_phase`; add `slice=` and `omit_heading=` args to `assemble_constraints_block`.
4. Add `_render_environment` (stub -> implementation after environment bundle lands).
5. Rewrite `assemble_agent_prompt` as thin orchestrator over renderers + gate.
6. Thread `time: InjectionSite` keyword through 4 callers (spawn, activation, phase advance, after compact).
7. Implement `gate = user_gate` pure predicate (~30 LOC); no structural floor.

### Configuration (config.py)

8. Add `GateSettings` + `GateManifest` frozen dataclasses.
9. Parse `constraints_segment.*` and `environment_segment.*` keys into `GateSettings`.

### Bundled environment content (new)

10. `claudechic/defaults/environment/base.md` -- tool semantics + peer roster template.
11. `claudechic/defaults/environment/project_team.md` -- workflow-static peer summaries.

### Workflow YAML

12. Add `environment_segment: enabled: true` to `project_team.yaml`; extend loader to parse it.

### Bundled role content

13. Remove `## Communication` blocks from 14 identity files (coordinator exempt).
14. Author 5 new phase markdown files (test_engineer x2, ui_designer x2, user_alignment x1).
15. Add coordinator identity informational-mirror header (before L34).
16. Append plain-language chat rule to `coordinator/identity.md`.
17. Paste spec self-containment rule into 4 spec/testing files (coordinator + composability).

### Settings UI (new files)

18. Add `"Agent prompt context"` section + 5 `SettingKey` entries in `settings.py`.
19. Implement `AdvancedConstraintsScreen` (4-checkbox, live-save, last-row guard).
20. Implement `AdvancedEnvironmentScreen` (3-checkbox, same pattern).
21. Fix MCP tool-widget content disappearing on click (`widgets/content/tools.py`).

### MCP tool parameter

22. Add optional `compact: bool` input to `mcp__chic__get_agent_info` (default `false`).

### Bug closures

| Bug | Before | After |
|-----|--------|-------|
| F1 -- phase advance skipped constraints | sub-agents received no update | `constraints_phase` emits at phase advance by default |
| F8 -- default-roled agents got `None` | constraints lost | renderers return `str`, composer returns non-`None` when any segment non-empty |
| F9 -- empty-digest emitted 138-char placeholder | standing-by agents received noise | empty returns `""`, composer drops empty segments |
| F5 -- disabled_rules unwired at 4 sites | rules not applied | spawn passes merged `disabled_rules`; phase advance computes once before loop |
