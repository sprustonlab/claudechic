# UI Review: Settings Page Additions for `constraints_segment` + `environment_segment`

Reviewer: ui_designer (project_team_context_review)
Subject: Should the schemas in SPEC_bypass §4.7 + §4.11 be exposed in `claudechic/screens/settings.py` as drafted?

TL;DR: **Schemas are operationally correct but a poor fit for the current settings UI as specced.** The bool/enum knobs are fine. The two `scope.sites` lists are user-hostile (jargon, footguns where structural-floor pins user choices to "no effect"). The format tri-states are too detailed for the top level. The two near-identical sections will read as duplication. Recommendation: surface 3 boolean rows at the top level + 1 "Advanced..." subscreen per segment, unify vocabulary, and visually mark structurally-pinned sites.

---

## 1. Audit of the existing settings page

`SettingsScreen` is a single flat scrollable `ListView` with sections delimited by header `_ActionRow`s:

```
━━ User settings (~/.claudechic/config.yaml) ━━
  Default permission mode    auto       [user]
  Theme                      ▸          [user]
  Vi mode                    on         [user]
  ...
  ▸ Reset user settings to defaults

━━ Project settings (./.claudechic/config.yaml) ━━
  Guardrails                 on         [project]
  Hints                      on         [project]
  Disabled workflows         (0 disabled) ▸  [project]
  Disabled IDs               (0 disabled) ▸  [project]
  ▸ Reset project settings to defaults

━━ Reference ━━
  ▸ Open docs/configuration.md
```

Available editor primitives (per `SettingKey.editor`):

| editor | Widget | Fits |
|--------|--------|------|
| `bool` | Inline toggle on row click | one toggleable value |
| `enum` | `_EnumPickerModal` ListView | small fixed set, single pick |
| `int` | `_IntEditModal` | bounded integer |
| `text` | `_TextEditModal` (with presets) | free-form string |
| `subscreen` | Custom `Screen` (e.g. `DisabledIdsScreen`) | multi-select, structured data |

What works: live-save, search-by-label, level badges, single visual rhythm, modal editors keep the list compact.

What doesn't (for fine-grained per-segment knobs):
- **No multi-select primitive.** Multi-value lists currently piggyback on `subscreen` and only exist for "disable by id" semantics. There is no general checkbox-list editor.
- **One row = one key.** Nested keys (`constraints_segment.format`) work via dotted key paths but each becomes a top-level row, inflating the list.
- **No grouping affordance.** No collapsibles, no indentation. Six new rows would land flat alongside `Vi mode` and `Theme`.
- **No "Advanced" disclosure.** Power-user knobs sit at equal weight with daily ones.

## 2. Per-key UX evaluation

| Key | Type | Fit verdict |
|-----|------|-------------|
| `constraints_segment.format` | enum 3 | **Fit, but wrong altitude.** Enum editor handles it, but value names (`markdown-table` / `markdown-list` / `compact-list`) are renderer-internal. Most users never touch this. Hide. |
| `constraints_segment.include_skipped` | bool | **Trivial fit.** Bool toggle. Label is opaque ("skipped" what?) -- needs rename. |
| `constraints_segment.scope.sites` | list of 5 enum | **Footgun.** `spawn`/`activation`/`phase-advance-main`/`phase-advance-broadcast`/`post-compact` is internal injection-site jargon. Per §4.10, two of those (T4 broadcast + T5 post-compact) are pinned True regardless of setting -- the user can untick them and nothing changes. That is the textbook definition of a UI footgun. |
| `environment_segment.enabled` | bool | **Trivial fit.** But "environment segment" means nothing to a user. |
| `environment_segment.scope.sites` | list of 3 enum | **Same footgun, smaller.** T5 post-compact is structurally pinned. Of the three sites only T2 activation is freely toggleable in practice. |
| `environment_segment.format` | enum 2 | **Tri-state in the spec but binary in practice** (`default` vs `compact`). This should be a bool toggle ("Compact mode"), not an enum picker. Reduces modal pop-up cost. |

## 3. Mocks

### 3a. Naive mock (drop the schema in as-is — DO NOT SHIP)

```
━━ User settings (~/.claudechic/config.yaml) ━━
  ...
  Constraints segment format       markdown-table     [user]
  Constraints segment include skipped   off           [user]
  Constraints segment scope sites  ▸ (5 enabled)      [user]
  Environment segment enabled      on                 [user]
  Environment segment scope sites  ▸ (3 enabled)      [user]
  Environment segment format       default            [user]
```

Six new rows of opaque jargon, two of them sub-screens that do nothing for two of their entries. This is what the user is worried about. They are right to worry.

### 3b. Recommended mock

Two new sections, each surfacing only the daily knob at the top level, with detail behind a single "Advanced..." subscreen.

```
━━ Agent prompt context ━━

  Rules block in agent prompts        on             [user]
    Show the active guardrails / advance checks block when each
    agent starts or after compaction.
  Compact rules block                 off            [user]
    Use a denser markdown list instead of the default table.
  Rules block: advanced...            ▸              [user]

  Team coordination context           on             [user]
    Inject the peer roster, name routing table, and MCP coordination
    notes into multi-agent workflows (e.g. project_team).
  Compact coordination context        off            [user]
    Omit the MCP tool list and coordination patterns.
  Coordination context: advanced...   ▸              [user]
```

Top-level rows are all `bool` -- one click, no modal.

`Compact rules block` collapses the tri-state `format` into one toggle (off = `markdown-table`, on = `compact-list`). The third option (`markdown-list`) lives only on the advanced subscreen. Same pattern for `environment_segment.format` (binary already; toggle directly).

`Rules block: advanced...` opens an `AdvancedConstraintsScreen` (mock):

```
Rules block — advanced

  Format               markdown-table  ▸
                       (markdown-table | markdown-list | compact-list)

  Show skipped rules   [ ]
                       Include rules whose advance-checks were skipped
                       this run.

  Inject at:
    [x] when an agent starts                 (spawn)
    [x] when the workflow activates          (activation)
    [x] on phase advance — main agent        (phase-advance-main)
    [x] on phase advance — broadcast         always-on (T4 floor)
    [x] after compaction                     always-on (T5 floor)

  Esc to close
```

Two key affordances on the sites checklist:
1. User-facing trigger phrase first ("when an agent starts"), engineering token in muted text.
2. Always-on rows render as checked + disabled with the muted suffix `always-on (T4 floor)` so the user sees that ticking/unticking is a no-op.

`Coordination context: advanced...` mirrors the same pattern, exposing only the three sites where the segment fires (T1/T2/T5), with T5 marked always-on.

## 4. UX critique of the schema as written

1. **`scope.sites` is the wrong shape for end users.** It models the engine's five injection sites; only two of those (T1 spawn, T2 activation for constraints; T2 activation for environment) are truly user-controllable. The other three are pinned True by `structural_gate`. Exposing all five as toggleable is a lie.
2. **Names leak the implementation.** `constraints_segment`, `environment_segment`, `injection site`, `phase-advance-broadcast` are ManifestLoader / `agent_folders.py` vocabulary. None of it is in the user-facing GLOSSARY for project_team users.
3. **The two sections are structurally identical.** Same shape (enabled? + sites + format) -> two near-identical UI blocks. Combine them under one "Agent prompt context" header to communicate that they are siblings and reduce visual repetition.
4. **`format` tri-state is over-specified for top level.** A single "Compact" boolean covers the 80% case; the third value (`markdown-list`) is for users who want list-not-table -- power-user territory.
5. **`include_skipped` label is opaque.** "Show skipped rules" is the user's mental model.
6. **No empty-state guidance.** If the user disables `Team coordination context`, they should see a one-line consequence ("Sub-agents will not receive the peer roster"). The current screen has helper-text infrastructure (`SettingKey.helper`) but only some keys use it.

## 5. Recommendation

**A. Schema changes (small, optional but advised).**

1. Drop `markdown-list` from `constraints_segment.format` until a user asks for it. Keep `markdown-table` (default) and `compact-list`. Then both segments' `format` field is binary -> a `bool` named `compact: false`.
   - If kept tri-state, leave it but only surface in the advanced subscreen.
2. Keep `scope.sites` as specified -- it is the right operational primitive -- but the UI must (a) translate to plain language, (b) mark structurally-pinned sites as always-on, and (c) live behind an Advanced disclosure.
3. Rename the top-level YAML keys for user-facing match: leave `constraints_segment` and `environment_segment` as YAML identifiers, but the settings UI labels are "Rules block in agent prompts" and "Team coordination context" respectively.

**B. Settings-screen additions (concrete).**

Add one new section header `━━ Agent prompt context ━━` between the existing `User settings` content and its `Reset user settings` row. New `SettingKey` entries:

| `key` | label | editor | choices / behavior |
|-------|-------|--------|--------------------|
| `constraints_segment.enabled_view` (synthetic; always on, read-only or hidden if structural floor) | -- | -- | -- |
| `constraints_segment.compact` (or `format` mapped) | "Compact rules block" | bool | maps to `format: compact-list` vs `markdown-table` |
| `constraints_segment.advanced` | "Rules block: advanced..." | subscreen | opens new `AdvancedConstraintsScreen` |
| `environment_segment.enabled` | "Team coordination context" | bool | direct |
| `environment_segment.compact` (or `format` mapped) | "Compact coordination context" | bool | maps to `format: compact` vs `default` |
| `environment_segment.advanced` | "Coordination context: advanced..." | subscreen | opens new `AdvancedEnvironmentScreen` |

The two new subscreens reuse the `disabled_ids.py` pattern (checkbox `ListItem`s, `Enter`-to-confirm or live-save). Rows for structurally-pinned sites are rendered with `disabled=True` and an `always-on` suffix.

**C. Acceptance criteria for the settings UI.**

- No new top-level row introduces injection-site vocabulary.
- A user can disable the rules block / coordination context with one click each.
- A user who opens the Advanced subscreen sees:
  - plain-language site descriptions in the primary column,
  - engineering token names in the muted secondary column,
  - structurally-pinned sites visibly inert.
- A user who has never opened SPEC_bypass.md can correctly predict what each top-level toggle does from its label + helper alone.

**D. If the team rejects the rename + Advanced disclosure**, ship the bools at minimum (`environment_segment.enabled`, `constraints_segment.include_skipped`) and explicitly omit `scope.sites` and `format` from the settings screen. They remain editable via YAML; `docs/configuration.md` documents them. Better to ship four good rows than seven bad ones.

---

*Sign-off: ui_designer.*
*Linked: SPEC_bypass.md §4.7, §4.10, §4.11; settings.py USER_KEYS; disabled_ids.py pattern.*
