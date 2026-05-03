# UI Settings: Final Deliverables

Author: ui_designer (project_team_context_review)
Status: locked, hand-off to implementer
Companion: `ui_settings_review.md` (review + rationale)

User picked **Option A**: full adoption of the recommendation. composability is in
parallel reshaping the schema to match (`format` -> `compact: bool`, rename of
`include_skipped` -> "Show skipped rules" already accepted).

---

## 0. Resolution of the `Rules block in agent prompts` semantics question

**Drop the row. There is no master enable/disable for the constraints segment.**

Per SPEC_bypass §3 (Out of scope for v1):

> `constraints_segment.enabled: false` (full opt-out; re-introduces F4/F5/F7).

The constraints block must always render -- the structural floor (§4.10) pins
multiple cells True regardless of any user setting. Putting a "Rules block in
agent prompts: on/off" master toggle in `/settings` would:

- Be a lie for a user who unticks it (T1/T2/T4/T5 still fire).
- Re-introduce the F4/F5/F7 footguns by suggesting opt-out is a supported mode.

So the constraints segment surfaces **three** rows (compact, show-skipped,
advanced...), none of them a master enable. The environment segment surfaces
**three** rows including the master enable (`environment_segment.enabled`) since
that opt-out IS supported per §4.11.

Net: six new rows, asymmetric on purpose. The asymmetry communicates the spec.

---

## 1. Final mocks

### 1.1 New section in `/settings`

Inserted between the existing `User settings` content block and its
`Reset user settings` row.

```
━━ Agent prompt context ━━

  Compact rules block                            off       [user]
      constraints_segment.compact
      Use a denser markdown list instead of the default table.

  Show skipped rules                             off       [user]
      constraints_segment.include_skipped
      Include rules whose advance-checks were skipped this run.

  Rules block: advanced...                       ▸         [user]
      constraints_segment.scope.sites

  Team coordination context                      on        [user]
      environment_segment.enabled
      Inject peer roster, name routing table, and MCP coordination
      notes into multi-agent workflows (e.g. project_team).

  Compact coordination context                   off       [user]
      environment_segment.compact
      Omit the MCP tool list and coordination patterns.

  Coordination context: advanced...              ▸         [user]
      environment_segment.scope.sites
```

Visual notes:
- Each row keeps the existing `_SettingRow` rhythm: bold label, value, level
  badge, then helper line(s) underneath in muted text.
- The dotted config-key path is rendered on its own muted line under the label
  (just above the prose helper). This is new visual furniture not present in
  existing rows; see §3 for implementation.
- The `▸` glyph on subscreen rows matches `Theme` / `Disabled IDs` precedent.

### 1.2 Advanced subscreen: constraints sites

Title: `Rules block — Advanced`. Reached from the
`Rules block: advanced...` row.

```
Rules block — Advanced
Inject the rules block at:

  [x] when an agent starts
        spawn
  [x] when the workflow activates
        activation
  [x] on phase advance
        phase-advance
  [x] after compaction
        post-compact

  Esc to close · Space to toggle · Enter to save
```

Affordances:
- Plain-language trigger phrase is the primary label.
- Engineering token (`spawn`, `phase-advance-main`, ...) is shown on a second
  muted line so a user looking at YAML can map back.
- **Every site is freely toggleable.** No structural floor remains in v1
  (per gating-axis spec edit, the floor was removed). All four rows are plain
  checkboxes; none rendered disabled, none annotated.
- **One-row floor.** The screen guarantees at least one site stays checked.
  If the user attempts to untick the last remaining checked row, the toggle is
  reverted in place and the user sees a one-line app notice:
  `at least one site must remain checked`. (The constraint is enforced at
  toggle time, not deferred to Save.)
- Default value (matches spec §4.7): all four sites enabled.

### 1.3 Advanced subscreen: environment sites

Title: `Team coordination context — Advanced`. Reached from the
`Coordination context: advanced...` row.

```
Team coordination context — Advanced
Inject the coordination block at:

  [x] when an agent starts
        spawn
  [x] when the workflow activates
        activation
  [x] after compaction
        post-compact

  Esc to close · Space to toggle · Enter to save
```

Affordances:
- Same row pattern as the constraints subscreen.
- All three sites are freely toggleable.
- **One-row floor**, same behavior as §1.2: attempting to untick the last
  checked row reverts the toggle and emits the one-line notice
  `at least one site must remain checked`.
- Default value (matches spec §4.11): all three sites enabled.

---

## 2. Final user-facing label copy

Single source of truth for the implementer.

### 2.1 Top-level rows (in `screens/settings.py` `USER_KEYS`)

| YAML key                                    | UI label                          | helper                                                                                              | editor     | choices                                                  |
|---------------------------------------------|-----------------------------------|-----------------------------------------------------------------------------------------------------|------------|----------------------------------------------------------|
| `constraints_segment.compact`               | Compact rules block               | Use a denser markdown list instead of the default table.                                            | bool       | --                                                       |
| `constraints_segment.include_skipped`       | Show skipped rules                | Include rules whose advance-checks were skipped this run.                                           | bool       | --                                                       |
| `constraints_segment.scope.sites`           | Rules block: advanced...          | Choose which moments inject the rules block.                                                        | subscreen  | (sites checklist)                                        |
| `environment_segment.enabled`               | Team coordination context         | Inject peer roster, name routing table, and MCP coordination notes into multi-agent workflows.      | bool       | --                                                       |
| `environment_segment.compact`               | Compact coordination context      | Omit the MCP tool list and coordination patterns.                                                   | bool       | --                                                       |
| `environment_segment.scope.sites`           | Coordination context: advanced... | Choose which moments inject the coordination block.                                                 | subscreen  | (sites checklist)                                        |

### 2.2 Section header

`━━ Agent prompt context ━━` -- placed in the user section, between `effort`
and the `Reset user settings...` row.

### 2.3 Sites checklist labels

All sites are freely toggleable; no `always-on` column.

Constraints subscreen (4 sites), in fixed order:

| token                          | UI primary                              |
|--------------------------------|-----------------------------------------|
| `spawn`                        | when an agent starts                    |
| `activation`                   | when the workflow activates             |
| `phase-advance`                | on phase advance                        |
| `post-compact`                 | after compaction                        |

The `phase-advance` row covers what was formerly two rows
(`phase-advance-main` + `phase-advance-broadcast`); per gating_axis,
coordinator's main-side phase advance is a synchronous tool return rather
than an injection site, so only the broadcast leg is gateable and the two
collapse to one user-facing row.

Environment subscreen (3 sites), in fixed order:

| token            | UI primary                       |
|------------------|----------------------------------|
| `spawn`          | when an agent starts             |
| `activation`     | when the workflow activates      |
| `post-compact`   | after compaction                 |

### 2.4 Footer hint string (both subscreens)

`Esc to close · Space to toggle · Enter to save`

---

## 3. Implementation hand-off

### 3.1 Files to create / edit

| File                                                            | Action  | LOC (approx) |
|-----------------------------------------------------------------|---------|--------------|
| `claudechic/screens/settings.py`                                | edit    | +70          |
| `claudechic/screens/agent_prompt_context.py` (new)              | create  | ~190         |
| `tests/test_settings_agent_prompt_context.py` (new)             | create  | ~180         |

The two Advanced subscreens share enough structure that a **single new file**
houses both, exporting two `Screen` subclasses backed by one shared `ListItem`
widget. Splitting into two files would duplicate ~80 LOC; keep them together.

### 3.2 New widget classes

In `claudechic/screens/agent_prompt_context.py`:

```python
@dataclass(frozen=True)
class _SiteSpec:
    token: str             # "spawn", "phase-advance-main", ...
    label: str             # "when an agent starts"

class _SiteRow(ListItem):
    """One site checkbox row.

    Mirrors disabled_ids._TierIdItem visually:
    `[x] <label>`
    `      <token>` (muted second line)

    All rows are plain enabled checkboxes; toggle() inverts checked state.
    """

class AdvancedConstraintsSitesScreen(Screen[frozenset[str] | None]):
    """5-row checklist; returns frozenset of enabled tokens or None."""

class AdvancedEnvironmentSitesScreen(Screen[frozenset[str] | None]):
    """3-row checklist; returns frozenset of enabled tokens or None."""
```

Both screens share a `_SitesScreenBase` mixin holding the bindings, the
checklist render pass, the Space/Enter/Esc handlers, and the
freezeset-build-on-Enter step.

The Space / click handler implements the **one-row floor** in place:

```python
def _try_toggle(self, row: _SiteRow) -> None:
    if row.checked:
        # User wants to uncheck. Refuse if it would leave the set empty.
        checked_rows = [r for r in self._rows if r.checked]
        if len(checked_rows) == 1 and checked_rows[0] is row:
            self.app.notify(
                "at least one site must remain checked",
                severity="warning",
            )
            return  # no toggle, no re-render
    row.toggle()
```

The constraint is enforced at toggle time so the user never reaches a state
that Enter would reject; Enter therefore has no validation path of its own.

### 3.3 Reuse of existing primitives

| Need                                | Reuse                                        |
|-------------------------------------|----------------------------------------------|
| Top-level row layout                | `_SettingRow` in `settings.py`               |
| Subscreen row layout (checked/disabled badges) | pattern from `_TierIdItem` in `disabled_ids.py` |
| Subscreen save/cancel keybindings   | `Binding("escape", ...)` precedent in `_EnumPickerModal` |
| Section header                      | `_ActionRow(..., header=True)` precedent      |
| Search filter                       | existing `_matches_search` -- new section participates automatically |

### 3.4 Edits to `screens/settings.py`

1. Add 6 new `SettingKey` entries to `USER_KEYS` (per §2.1) at the end.
2. Insert a new section header `━━ Agent prompt context ━━` in `_render_list`.
   Three options for placement; recommend **inserting BEFORE `Reset user
   settings to defaults`** rather than after it, so the new section participates
   in `User settings` reset semantics.
3. Update `_open_subscreen` dispatch to recognise the two new keys
   (`constraints_segment.scope.sites`, `environment_segment.scope.sites`) and
   push the corresponding new subscreen.
4. Update `_format_value` to handle the two new subscreen keys: render
   `(N of M sites)` instead of `(N disabled)` since the semantics are inverse
   (a list of *enabled* sites, not disabled ids).
5. Optional polish: extend `_SettingRow.compose` to render the muted config-key
   line between the label and the helper. Gate behind a new
   `SettingKey.show_key_path: bool = False` field so existing rows are
   unaffected.

### 3.5 Reapply / persistence behaviour

All six keys land in `~/.claudechic/config.yaml` via existing `_save_value` ->
`cfg.save()`. None of them needs special live-reapply; the next agent spawn /
activation reads fresh `GateSettings` (per spec §4.11). Add no-op branches in
`_reapply` so the live-reapply call doesn't notify a spurious warning.

### 3.6 Tests to write (UI level)

In `tests/test_settings_agent_prompt_context.py`. All run under Textual's
async test pilot, no mocks (Generalprobe standard).

**T-UI-1 -- Section presence.** `/settings` ListView contains an `_ActionRow`
with text `━━ Agent prompt context ━━`.

**T-UI-2 -- Six rows render.** The six new labels (per §2.1) are present in
the ListView in the documented order.

**T-UI-3 -- Helper + key-path rendering.** Each top-level row renders its
config key path on a muted line and its prose helper underneath.

**T-UI-4 -- Compact toggle persists.** Click `Compact rules block`. Assert
`CONFIG["constraints_segment"]["compact"] is True` and the YAML on disk
contains the same. Click again -> `False`.

**T-UI-5 -- Enabled toggle persists.** Toggle `Team coordination context`
off. Assert `CONFIG["environment_segment"]["enabled"] is False`.

**T-UI-6 -- Constraints subscreen renders 4 rows.** Click
`Rules block: advanced...`. The pushed screen contains exactly 4 `_SiteRow`
items in the order spawn, activation, phase-advance, post-compact.

**T-UI-7 -- Constraints rows all toggleable.** In the constraints
subscreen, all four rows render with `disabled == False`. No row carries
an `always-on` suffix.

**T-UI-8 -- Constraints toggle works on every row.** Press Space on the
`spawn` row. The row's checked state inverts. Repeat for each of the
other three rows.

**T-UI-9 -- Constraints toggleable row works.** Press Space on the
`phase-advance` row. The row's checked state inverts. (Folded into
T-UI-8 in practice; kept as a named test for clarity in the spec mapping.)

**T-UI-10 -- Constraints save on Enter.** Untick `phase-advance` and
`spawn`, press Enter. Assert
`CONFIG["constraints_segment"]["scope"]["sites"]` equals
`{"activation", "post-compact"}`
(frozenset semantically; YAML stores as list).

**T-UI-11 -- Constraints Esc cancels.** Toggle a row, press Esc. Config on
disk unchanged.

**T-UI-12 -- Environment subscreen renders 3 rows.** Click
`Coordination context: advanced...`. Three `_SiteRow` items in order
spawn, activation, post-compact.

**T-UI-13 -- Environment rows all toggleable.** All three rows render with
`disabled == False`. No row carries an `always-on` suffix.

**T-UI-14 -- Environment save on Enter.** Untick `spawn` and `post-compact`,
Enter. Assert `CONFIG["environment_segment"]["scope"]["sites"] == {"activation"}`.

**T-UI-14b -- Last-row-revert (constraints).** Open the constraints
subscreen with all four rows checked. Untick three rows in order. Attempt
to untick the fourth (last remaining) row. Assert: the row's checked state
remains `True`, the app notify queue contains an entry with text
`at least one site must remain checked` and severity `warning`, and the
saved YAML on Enter contains exactly that one site.

**T-UI-14c -- Last-row-revert (environment).** Same as T-UI-14b on the
environment subscreen with three rows; the last row resists unchecking.

**T-UI-15 -- Empty sites is rejected at config-load (regression guard).**
Save `{}` for either scope (manually editing YAML on disk -- not via the
UI, which can't produce an empty set per T-UI-14b/c), reload the screen.
Expect `ConfigValidationError` per spec §4.7 / §4.11. This test binds the
spec-side invariant to a YAML-only attack path.

**T-UI-16 -- Search filter participation.** Type `compact` in the settings
search box. Both `Compact rules block` and `Compact coordination context`
remain visible; the `Show skipped rules` row is filtered out.

### 3.7 Build-plan addendum

Insert into SPEC_bypass §7 (Build plan) as a new sub-group between Group 3
(Configuration wiring) and Group 4 (Workflow YAML extension):

> **Group 3b -- Settings UI surface (issue-#28 + environment_segment)**
>
> 9b. Add 6 `SettingKey` entries + `━━ Agent prompt context ━━` section header
>     in `screens/settings.py`; thread `_open_subscreen` for the two new
>     subscreen keys; extend `_format_value` for the `(N of M sites)` shape;
>     extend `_SettingRow` for the muted config-key line. (~70 LOC)
>
> 9c. Create `screens/agent_prompt_context.py` exporting
>     `AdvancedConstraintsSitesScreen` and `AdvancedEnvironmentSitesScreen`
>     plus shared `_SiteRow`. (~180 LOC)
>
> 9d. Author `tests/test_settings_agent_prompt_context.py` with T-UI-1
>     through T-UI-16. (~160 LOC)

---

## 4. Acceptance criteria (TestEngineer-checkable)

Numbered to allow per-criterion pass/fail.

**AC-1.** Opening `/settings` after these changes shows a section
`━━ Agent prompt context ━━` between the existing user-tier rows and
`Reset user settings to defaults`.

**AC-2.** That section contains exactly six rows in the order:
`Compact rules block`, `Show skipped rules`, `Rules block: advanced...`,
`Team coordination context`, `Compact coordination context`,
`Coordination context: advanced...`.

**AC-3.** Each top-level row renders its config-key path on a muted line
between label and prose helper, matching §2.1 verbatim.

**AC-4.** Clicking `Compact rules block` writes
`constraints_segment: { compact: true }` (or `false`) to
`~/.claudechic/config.yaml` atomically; the toggle survives `/settings`
close + reopen.

**AC-5.** Clicking `Team coordination context` toggles
`environment_segment.enabled` on disk and the change is visible immediately
in the row's value column.

**AC-6.** Pressing `/` focuses the search box; typing `compact` filters the
list to the two `Compact ...` rows (plus headers).

**AC-7.** Clicking `Rules block: advanced...` pushes a new screen titled
`Rules block — Advanced` containing four rows with primary labels matching
§2.3 verbatim (`spawn`, `activation`, `phase-advance`, `post-compact`).
Every row is freely toggleable (`disabled == False`); no row displays an
`always-on` suffix.

**AC-8.** Pressing `Space` on any row in either subscreen inverts that row's
checked state. No row is inert.

**AC-9.** Pressing `Space` on a toggleable row inverts its checked state
visually within the same render frame. (Same surface as AC-8 in the
no-floor world; retained for spec-mapping clarity.)

**AC-10.** Pressing `Enter` in either subscreen persists the set of checked
rows as a list under the corresponding YAML key
(`constraints_segment.scope.sites` or `environment_segment.scope.sites`).
The UI guarantees the saved set is non-empty (see AC-10b), so Enter has no
validation path of its own. An empty selection authored directly in YAML
is rejected at config-load time per spec §4.7 / §4.11.

**AC-10b.** Attempting to uncheck the last remaining checked row in either
Advanced subscreen leaves the row checked and emits a one-line app notice
`at least one site must remain checked` (severity: warning). The user can
never reach an empty selection through the UI.

**AC-11.** Pressing `Esc` in either subscreen returns without modifying
config on disk; the underlying `/settings` row's value display is unchanged.

**AC-12.** Clicking `Coordination context: advanced...` pushes a screen
titled `Team coordination context — Advanced` with three rows; all three
are freely toggleable, none disabled, none annotated.

**AC-13.** A user who never reads SPEC_bypass.md can correctly predict from
the labels and helpers that:
- the rules block always renders (no master enable),
- the coordination context can be turned off entirely,
- the Advanced subscreens fine-tune *when* each block fires.
(Verified by 1-on-1 walkthrough during Implementation phase by
user_alignment.)

**AC-14.** All 18 tests T-UI-1 through T-UI-16 (including T-UI-14b and
T-UI-14c) pass under
`pytest tests/test_settings_agent_prompt_context.py -v --timeout=30`.

**AC-15.** No existing UI test in `tests/` regresses
(`pytest tests/ -n auto -q --timeout=30` is green vs. the pre-change
baseline).

---

---

## 5. Revision log

- **rev1** (initial): two structural floors honored in the Advanced
  subscreens (T1/T2/T4/T5 disabled+checked for constraints; T5 disabled+checked
  for environment).
- **rev2**: structural floors removed per gating-axis spec edit.
  Every site is now a plain enabled checkbox in both Advanced subscreens.
  Master-enable asymmetry (constraints has none, environment has `enabled`)
  is unchanged -- that asymmetry is about §3 opt-out semantics, not floors.
- **rev3**: added one-row floor enforcement at toggle time.
  Attempting to uncheck the last remaining row reverts the toggle and emits
  `at least one site must remain checked`. New tests T-UI-14b / T-UI-14c
  and acceptance criterion AC-10b cover the behavior. Empty-set rejection
  at config-load (spec §4.7 / §4.11) remains the second-line guard for
  YAML-edited paths.
- **rev4** (current): constraints subscreen drops from 5 rows to 4. Per
  gating_axis, coordinator's main-side phase advance is a synchronous tool
  return rather than an injection site, so `phase-advance-main` and
  `phase-advance-broadcast` collapse into a single `phase-advance` token /
  row labelled "on phase advance". Environment subscreen unchanged at 3
  rows. Tests T-UI-6, T-UI-7, T-UI-8, T-UI-9, T-UI-10, T-UI-14b updated;
  AC-7 updated.

*Sign-off: ui_designer.*
*Linked: SPEC_bypass.md §3 (no full opt-out for constraints), §4.7, §4.11;
settings.py; disabled_ids.py.*
