# UI Design — independent_chic

> **REFERENCE ARCHIVE — operational content has been merged into `SPEC.md` §7. This file is preserved for trace; not for implementation reading.**

**Author:** UIDesigner (Specification phase)
**Status:** Operational spec. Per L14, this file is strictly *what to build*. All
rationale, alternatives, postponement justifications, and terminology
decisions live in `ui_design_appendix.md`.
**Audience:** Implementer + Tester. Readable without the appendix.

**Anchored to:** `vision.md` §"Settings UI and configuration reference" (#23
deliverables) and §"What we want" #5 (workflow-picker button, #24); STATUS.md
A4 (behavioral mirror, no symlinks, no Claude-settings overwrites), A6 (auto
startup default), A7 (boundary primary-state-only), A12 (smaller-feature
delegation); terminology_glossary.md L4 (settings/config) and §3.5 (settings
UI / settings screen / settings button names).

---

## 0. Scope at a glance

In-scope UI surfaces for this run:

| # | Surface | Issue | A12-feature? | Notes |
|---|---|---|---|---|
| 1 | Settings screen (`SettingsScreen`) | #23 | — | `/settings` + footer button entry points |
| 2 | Settings button in footer | #24 | — | New `SettingsLabel` in `StatusFooter` |
| 3 | `/settings` slash command | #23 | — | New entry in `commands.py` |
| 4 | Welcome-screen "Settings" action row | #23 + #21 | A12.a — **in scope** | One new `_ActionItem` |
| 5 | Disabled-workflows multi-select subscreen | #23 | A12.b — **in scope** | Reads `app._workflow_registry` |
| 6 | Disabled-IDs multi-select subscreen | #23 | A12.c — **in scope** | Reads hint + guardrail-rule registries |
| 7 | Workflow-picker tier badges | #24 | — | Extend existing `WorkflowItem` |
| 8 | Permission-mode footer label updates for `auto` | A6 | — | Cherry-picks 5700ef5 + 7e30a53 |
| 9 | Documentation reference page (`docs/configuration.md`) — content scope | #23 | — | Implementer writes prose |

A12.d (settings-button vs `/settings`-command parity) is in scope and
satisfied by item 2 + item 3 invoking the same screen.

Postponed (this run): none. See appendix §3 for the four-question decision
log.

---

## 1. Settings screen — `SettingsScreen`

### 1.1. File and class

| Item | Value |
|---|---|
| New file | `claudechic/screens/settings.py` |
| New class | `SettingsScreen(Screen[None])` |
| Result type | `None` (changes are saved live, not on close) |
| Bindings | `escape` → `action_close` |
| CSS | Inline `DEFAULT_CSS`, mirrors `WorkflowPickerScreen` shape |

### 1.2. Existing widgets to reuse

| Reuse | From | For |
|---|---|---|
| `Screen[None]` pattern | `claudechic/screens/workflow_picker.py` | Top-level screen container |
| `Vertical` + `ListView` layout | `claudechic/screens/welcome.py` | Sectioned list with header items |
| `_make_header_item(text)` helper | `claudechic/screens/welcome.py` (export to a shared module) | Section dividers |
| `_make_separator_item()` helper | same | Visual spacing |
| `SelectionPrompt` | `claudechic/widgets/prompts.py` | Enum-valued keys (permission mode, log level, theme) |
| `QuestionPrompt` | same | Free-text keys (worktree path template, log file path) |
| `Button` primitive | `claudechic/widgets/primitives/button.py` | Inline action buttons (Save/Reset within sub-editors) |
| `QuietCollapsible` | `claudechic/widgets/primitives/collapsible.py` | "Advanced" group (currently empty; reserved for future) |
| `pyperclip` copy idiom | `claudechic/widgets/modals/base.py:_copy_all` | Copy-current-value affordance |

### 1.3. New widgets needed

| New class | File | Purpose |
|---|---|---|
| `SettingsScreen(Screen[None])` | `claudechic/screens/settings.py` | The screen itself |
| `_SettingRow(ListItem)` | same file (private) | One row: label + current value + tier badge |
| `_SettingHeader(ListItem)` | same file (private) | Disabled section header (reuses `_make_header_item` helper from welcome.py — extract that helper to `claudechic/widgets/primitives/listutil.py` and import from both screens) |
| `DisabledWorkflowsScreen(Screen[frozenset[str]])` | `claudechic/screens/disabled_workflows.py` | Sub-picker for `disabled_workflows` |
| `DisabledIdsScreen(Screen[frozenset[str]])` | `claudechic/screens/disabled_ids.py` | Sub-picker for `disabled_ids` (hints + guardrail rules) |
| `SettingsLabel(ClickableLabel)` | `claudechic/widgets/layout/footer.py` (append to existing module) | Footer "Settings" button |

### 1.4. Layout

```
┌──────────────────────────────────────────────────────┐
│ Settings                                          (1)│
│ Edit your claudechic settings. Changes save live.    │
│ ╭──────────────────────────────────────────────────╮ │
│ │ search: [                                      ] │ │
│ ╰──────────────────────────────────────────────────╯ │
│                                                      │
│ ━━ User settings (~/.claudechic/config.yaml) ━━      │
│   Default permission mode    auto         [user]     │
│   Auto-edit on startup       —            [user]     │
│   Theme                      textual-dark [user]     │
│   Vi mode                    off          [user]     │
│   Show message metadata      on           [user]     │
│   Recent tools expanded      2            [user]     │
│   Worktree path template     <default>    [user]     │
│   Analytics enabled          on           [user]     │
│   Log file                   ~/claudechic.log [user] │
│   Log notify-level           warning      [user]     │
│                                                      │
│ ━━ Project settings (./.claudechic/config.yaml) ━━   │
│   Guardrails                 on           [project]  │
│   Hints                      on           [project]  │
│   Disabled workflows         (3 disabled) ▸ [project]│
│   Disabled IDs               (5 disabled) ▸ [project]│
│                                                      │
│ ━━ Reference ━━                                      │
│   Open configuration.md (full reference)             │
│                                                      │
│ esc close · / search · enter edit · r reset to default│
└──────────────────────────────────────────────────────┘
```

(1) Title bar shows `Settings` left-aligned. Right side of title bar is empty
(no close button — esc handles it; chevron-back is implied by the stack).

### 1.5. Per-key editors

Each `_SettingRow` has a `key: str`, `tier: Literal["user","project"]`,
`editor_type: Literal["enum","bool","int","text","subscreen"]`, and
`enum_choices` / `text_validator` / `subscreen_class` as appropriate.

| Key | Tier | Editor type | Choices / validator |
|---|---|---|---|
| `default_permission_mode` | user | enum | `default` / `acceptEdits` / `plan` / `auto` / `bypassPermissions` |
| `themes` | user | subscreen | Push existing `app.search_themes()` flow (reuse `/theme` modal) |
| `vi-mode` | user | bool | toggle |
| `show_message_metadata` | user | bool | toggle |
| `recent-tools-expanded` | user | int | range `[0, 20]`, validator: `int(value) and 0 <= n <= 20` |
| `worktree.path_template` | user | text | `None` (default) or template string; preset choices `<default>` / `$HOME/code/worktrees/${repo_name}/${branch_name}` / `$HOME/worktrees/${repo_name}-${branch_name}` |
| `analytics.enabled` | user | bool | toggle |
| `logging.file` | user | text | path string or empty for `None` (disable) |
| `logging.notify-level` | user | enum | `debug` / `info` / `warning` / `error` / `none` |
| `guardrails` | project | bool | toggle |
| `hints` | project | bool | toggle |
| `disabled_workflows` | project | subscreen | `DisabledWorkflowsScreen` (§1.10) |
| `disabled_ids` | project | subscreen | `DisabledIdsScreen` (§1.11) |

Keys NOT exposed (per #23, hidden from this UI; documented in
`docs/configuration.md` reference only): `analytics.id`, `experimental.*`.

### 1.6. Editor flow per type

#### enum
1. User presses Enter on the row.
2. `SelectionPrompt` mounts inline below the row (see §1.4 mock — pushes
   below, list scrolls if needed).
3. Options listed; current value highlighted.
4. User selects → prompt resolves → `_save_key(key, value)` called → row
   re-renders with new value.

#### bool
1. Enter on row toggles directly (no prompt). Row re-renders.
2. Space also toggles for keyboard-only users.

#### int
1. Enter on row → `QuestionPrompt` mounts with `placeholder="0–20"` and
   current value pre-filled.
2. On submit, validator runs. If invalid: `notify("must be integer 0–20",
   severity="error")` and prompt stays.
3. On valid: save and resolve.

#### text
1. Enter on row → `QuestionPrompt` mounts with current value pre-filled.
2. Empty submit (for nullable keys) saves `None`.
3. Optional preset chips above the input for keys with common templates
   (worktree.path_template only — three preset chips inline).

#### subscreen
1. Enter on row → `app.push_screen(<SubscreenClass>(...))`.
2. On dismiss with non-`None` result, save the new value.

### 1.7. Save semantics

Changes save **live**, on each edit. No "Save" / "Cancel" button. Esc closes
the screen unconditionally. This matches `vision.md` "Success looks like":
*"A user can edit per-user config in their `/settings` UI ... and have it
apply to every project they work in"* — application is immediate.

Save path:

| Tier | Save call |
|---|---|
| user | Mutate `claudechic.config.CONFIG[key]`; call `claudechic.config.save()` (which writes to the user-tier file at `~/.claudechic/config.yaml` post-restructure). |
| project | Build a new frozen `ProjectConfig` from current values + the edit; call a new helper `claudechic.config.ProjectConfig.save(self, project_dir)` (Implementer adds; symmetric with `load`). |

Live re-application:

| Key | What re-applies on edit |
|---|---|
| `default_permission_mode` | Call `app.agent_mgr.set_global_permission_mode(value)`; footer updates via `watch_permission_mode`. |
| `themes` | Reuse existing `/theme` flow — handles re-application. |
| `vi-mode` | Toggle `app.vi_mode_enabled`; footer updates via `update_vi_mode`. |
| `show_message_metadata` | Set `app.show_message_metadata`; existing reactive triggers redraw. |
| `recent-tools-expanded` | Set in `CONFIG`; takes effect on next tool render. |
| `worktree.path_template` | Set in `CONFIG`; takes effect on next `/worktree`. |
| `analytics.enabled` | Reuse logic in `_handle_analytics(app, "/analytics opt-in")` / `opt-out`. |
| `logging.*` | Set in `CONFIG`; call `errors.setup_logging()` to re-init handlers. |
| `guardrails` | Set in `app.project_config.guardrails`; call `app.agent_mgr.refresh_guardrails()` (Implementer adds — restart hooks). |
| `hints` | Set in `app.project_config.hints`; call `app.hints_engine.refresh()` (Implementer adds — re-evaluate triggers). |
| `disabled_workflows` | Set in `app.project_config`; call `app._reload_workflows()` (existing — repopulates `_workflow_registry`). |
| `disabled_ids` | Set in `app.project_config`; call `app.hints_engine.refresh()` and `app.guardrails.refresh()`. |

If a re-apply call raises, the save **still persists** (file write succeeded);
emit `notify("Saved, but live re-apply failed: <err>", severity="warning")`.

### 1.8. Tier badges and override visibility

Per A5: config is 2-tier. User-tier keys and project-tier keys are disjoint by
design. No overlap is expected.

If the loader nevertheless finds a key set at both tiers (e.g., a future
schema mistake): the row shows both values:

```
Default permission mode   auto    [user]
                          plan    [project] ⚠ overrides
```

A small `⚠` glyph (no popup) plus the row's secondary line. Editing the row
edits the **higher-priority** tier (project). The behavior is testable; the
spec assumes this collision should not occur in normal use.

### 1.9. Search

A single `Input` at the top filters the visible rows. Filtering is
case-insensitive substring match against the row label *and* the key name.
Headers (`_SettingHeader`) and reference rows always remain visible.

### 1.10. `DisabledWorkflowsScreen` subscreen

| Item | Value |
|---|---|
| File | `claudechic/screens/disabled_workflows.py` |
| Class | `DisabledWorkflowsScreen(Screen[frozenset[str] | None])` |
| Init args | `current: frozenset[str]`, `available: list[tuple[str, Path, str]]` (workflow_id, source_path, tier_name) |
| Result | New `frozenset` of disabled IDs, or `None` if escaped |

Layout: Title `Disabled workflows`. ListView of rows, one per available
workflow (read from `app._workflow_registry`):

```
[x] project_team             [pkg]  coordinator · 5 phases
[ ] tutorial_extending       [pkg]  learner · 3 phases
[x] my_custom_flow           [user] author · 2 phases
[ ] team_specific            [proj] coordinator · 4 phases
```

Tier badge visible. Space toggles disable. Enter accepts (dismisses with
new frozenset). Escape cancels (dismisses with `None`). The row label is the
workflow ID (the value the user puts in `disabled_workflows`).

This satisfies A12.b: ID discovery is *the listing itself*. The user sees
every available workflow ID with its source.

### 1.11. `DisabledIdsScreen` subscreen

`disabled_ids` covers hint IDs *and* guardrail rule IDs (per
`terminology_glossary.md` §3.4 and the existing `claudechic/global/hints.yaml`
+ `claudechic/global/rules.yaml` namespacing). Format: `namespace:bare_id`.

| Item | Value |
|---|---|
| File | `claudechic/screens/disabled_ids.py` |
| Class | `DisabledIdsScreen(Screen[frozenset[str] | None])` |
| Init args | `current: frozenset[str]`, `hints: list[tuple[str, str, str]]` (id, lifecycle, tier), `rules: list[tuple[str, str, str, str]]` (id, level, tier, summary) |
| Result | New `frozenset` of disabled IDs, or `None` if escaped |

Layout: Two grouped sections within one ListView:

```
━━ Hints ━━
[x] global:context-docs-outdated     [pkg]
[ ] global:permission-mode-tip       [pkg]
[ ] my_workflow:setup-reminder       [proj]

━━ Guardrail rules ━━
[ ] global:no-rm-rf            deny  [pkg]  Block destructive rm
[x] global:warn-on-curl-pipe   warn  [pkg]  Warn on curl|sh
[ ] my_project:protect-prod    deny  [proj] Block prod paths
```

Same interaction as §1.10. Category labels (`Hints` / `Guardrail rules`)
disambiguate the type within `disabled_ids`. Per
`terminology_glossary.md` §2.4, hints and guardrail rules are different
things; the section headers preserve that.

This satisfies A12.c: ID listing is *the listing itself*.

### 1.12. Reset-to-default

A `Reset` row at the bottom of each section:

```
  [ Reset all user settings to defaults ]
  [ Reset all project settings to defaults ]
```

Activating brings up a `SelectionPrompt`: *"Reset N settings to defaults? This
cannot be undone."* with `Yes` / `No`. On Yes: clear keys (delete entries
from `CONFIG` for user-tier, replace `ProjectConfig` with default-constructed
instance for project-tier), then save.

### 1.13. CSS

Reuse the `WorkflowPickerScreen` CSS pattern verbatim, then add:

```tcss
SettingsScreen .setting-label    { width: 30; }
SettingsScreen .setting-value    { width: 1fr; color: $text; }
SettingsScreen .setting-tier-user    { width: 9; color: $text-muted; }
SettingsScreen .setting-tier-project { width: 9; color: $secondary; }
SettingsScreen .setting-badge-warn   { color: $warning; }
SettingsScreen .setting-help-bar { height: 1; color: $text-muted; }
```

Add to `claudechic/styles.tcss`, not inline (matches existing convention for
screen-level styling — though `WorkflowPickerScreen` uses `DEFAULT_CSS` as
inline; either is acceptable, prefer `styles.tcss` for new screens).

---

## 2. Settings button in footer — `SettingsLabel`

### 2.1. File and class

Append to `claudechic/widgets/layout/footer.py`:

```python
class SettingsLabel(ClickableLabel):
    """Clickable 'Settings' label in the footer."""

    class Requested(Message):
        """Emitted when user clicks to open settings."""

    def on_click(self, event) -> None:
        self.post_message(self.Requested())
```

Mirrors the existing `DiagnosticsLabel` and `ComputerInfoLabel` pattern
verbatim.

### 2.2. Footer integration

Edit `StatusFooter.compose()` to add `SettingsLabel` next to
`ComputerInfoLabel` (the "sys" button is the closest existing cousin):

```python
yield ComputerInfoLabel("sys", id="computer-info-label", classes="footer-label")
yield Static("·", classes="footer-sep")
yield SettingsLabel("settings", id="settings-label", classes="footer-label")
```

Label text is lowercase `settings` (matches sibling labels: `sys`,
`session_info`).

### 2.3. App handler

Add to `claudechic/app.py` (next to `on_diagnostics_label_requested` and
`on_computer_info_label_requested`):

```python
def on_settings_label_requested(
    self,
    event: SettingsLabel.Requested,  # noqa: ARG002
) -> None:
    """Handle Settings button - open settings screen."""
    self._handle_settings()

def _handle_settings(self) -> None:
    """Push the settings screen."""
    from claudechic.screens.settings import SettingsScreen
    self.push_screen(SettingsScreen())
```

`_handle_settings` is the single entry point shared by the footer button,
the `/settings` command (§3), and the welcome screen (§4) — A12.d parity is
satisfied by all three calling this method.

---

## 3. `/settings` slash command

### 3.1. Registry entry

Edit `claudechic/commands.py`. Add to the `COMMANDS` list (alphabetical
insertion between `/resume` and `/shell` — keeps existing visual ordering):

```python
("/settings", "Open settings", []),
```

### 3.2. Dispatch

Edit `handle_command()`. Add (place near `/welcome` and `/theme` handlers,
before the bare-`/exit` block):

```python
if cmd == "/settings":
    _track_command(app, "settings")
    app._handle_settings()
    return True
```

### 3.3. Autocomplete

`get_autocomplete_commands()` reads `COMMANDS` automatically; no further
change needed.

---

## 4. Welcome-screen Settings access (A12.a)

### 4.1. Add result constant

Edit `claudechic/screens/welcome.py`:

```python
RESULT_SETTINGS = "settings"
```

### 4.2. Add action item

In `WelcomeScreen.compose()`, immediately before the "Dismiss permanently"
row:

```python
items.append(_ActionItem(RESULT_SETTINGS, "▸ Settings (/settings)"))
items.append(_ActionItem(RESULT_DISMISS, "▸ Dismiss permanently"))
```

### 4.3. App-side dismiss handler

Edit the welcome-screen dismiss callback in `claudechic/app.py` around line
1139 (the existing `await self.push_screen_wait(welcome)` site). Add a
branch for `RESULT_SETTINGS`:

```python
result = await self.push_screen_wait(welcome)
if result == "settings":
    self._handle_settings()
elif result == "dismiss":
    ...  # existing dismiss path
elif result == "tutorial":
    ...
elif result == "picker":
    ...
```

The exact placement matches the existing if-chain at app.py:1139ff (read
that block; preserve order).

---

## 5. Workflow picker — tier badges (#24)

### 5.1. Constraint from A12 / vision §"What we want" #5

Vision §5 (verbatim): *"a 'workflow button' surface (per #24) that lets the
user see and select workflows from all three tiers, distinguishing where each
came from."* Spec must distinguish tier source visibly.

### 5.2. Workflow registry shape change

Edit `claudechic/app.py` (workflow discovery sites — see vision.md
§"File-move inventory" *Files with `claudechic/workflows/` path references*).

Today: `_workflow_registry: dict[str, Path]`.

After this work: `_workflow_registry: dict[str, WorkflowSource]` where
`WorkflowSource` is:

```python
@dataclass(frozen=True)
class WorkflowSource:
    path: Path
    tier: Literal["package", "user", "project"]
```

Defined in `claudechic/workflows/loader.py` (post-restructure location, per
vision.md "File-move inventory"). Loader populates `tier` based on which of
the three tiers it discovered the workflow at (see Composability eval for
override-resolution rules; UI just consumes `tier`).

If the same workflow ID exists at multiple tiers: the registry stores the
*winning* tier (project > user > package per L7) but exposes the full list
via a separate `_workflow_origins: dict[str, list[WorkflowSource]]`. The
picker uses `_workflow_origins` to show overrides (see §5.4).

### 5.3. `WorkflowItem` extension

Edit `claudechic/screens/workflow_picker.py`:

```python
class WorkflowItem(ListItem):
    def __init__(
        self,
        workflow_id: str,
        main_role: str = "",
        phase_count: int = 0,
        is_active: bool = False,
        tier: str = "package",         # new
        overridden_at: list[str] = None,  # new — list of tiers this also exists at
    ) -> None:
        ...
```

`compose()`:

```python
yield Label(self.workflow_id, classes="workflow-name")
parts = []
if self.main_role:
    parts.append(f"role: {self.main_role}")
parts.append(f"{self.phase_count} phase{'s' if self.phase_count != 1 else ''}")
if self.is_active:
    parts.append("active")
else:
    parts.append("available")
yield Label(" . ".join(parts), classes="workflow-meta")
yield Label(_tier_badge(self.tier), classes=f"workflow-tier tier-{self.tier}")
if self.overridden_at:
    yield Label(
        f"(also at: {', '.join(self.overridden_at)})",
        classes="workflow-meta workflow-overrides",
    )
```

Where `_tier_badge`:

```python
_TIER_BADGES = {"package": "[pkg]", "user": "[user]", "project": "[proj]"}
def _tier_badge(tier: str) -> str:
    return _TIER_BADGES.get(tier, f"[{tier}]")
```

### 5.4. Tier-source CSS

Add to `claudechic/styles.tcss`:

```tcss
WorkflowPickerScreen .workflow-tier         { width: 8; }
WorkflowPickerScreen .tier-package          { color: $text-muted; }
WorkflowPickerScreen .tier-user             { color: $secondary; }
WorkflowPickerScreen .tier-project          { color: $primary; }
WorkflowPickerScreen .workflow-overrides    { color: $text-muted; }
```

Color mapping: package = muted (lowest priority), user = secondary blue,
project = primary orange (highest priority, eye-catching). Matches the
existing visual language (orange for active/user-most-relevant, blue for
assistant/secondary, gray/muted for ambient).

### 5.5. Sort order

Sort the picker list by tier (project first, then user, then package),
secondary-sort alphabetical within tier. Override the existing
`_update_list` method's `filtered = sorted(...)` line:

```python
def _tier_sort_key(wf_id: str) -> tuple[int, str]:
    tier = self._workflows[wf_id].get("tier", "package")
    order = {"project": 0, "user": 1, "package": 2}.get(tier, 3)
    return (order, wf_id)

filtered = sorted(self._workflows.keys(), key=_tier_sort_key)
```

### 5.6. App handler updates

Edit `app.py:3306-3367` (`on_chicsession_actions_workflow_picker_requested`).
The `picker_data` dict assembly must include `tier` and `overridden_at`:

```python
picker_data[wf_id] = {
    "main_role": wf_data.main_role if wf_data else "",
    "phase_count": phase_count,
    "is_active": bool(...),
    "tier": self._workflow_registry[wf_id].tier,
    "overridden_at": [
        s.tier for s in self._workflow_origins.get(wf_id, [])
        if s.tier != self._workflow_registry[wf_id].tier
    ],
}
```

---

## 6. Auto permission-mode UI updates (A6 cherry-picks 5700ef5 + 7e30a53)

### 6.1. Cherry-pick semantics expected

The two abast commits (per STATUS A2/A6):
- `5700ef5` — adds `auto` to permission modes; sets it as the default-on-fresh-install for `default_permission_mode`.
- `7e30a53` — extends Shift+Tab cycle to include `auto`.

These cherry-picks land *before* this UI work per the run's preferred order
(restructure → cherry-pick → #23/#24). After they land, this spec extends
the UI.

### 6.2. Footer label extension

Edit `claudechic/widgets/layout/footer.py:200`
(`watch_permission_mode`). The existing if-chain handles `planSwarm`,
`plan`, `acceptEdits`, `bypassPermissions`, default. Add `auto` between
`bypassPermissions` and the default else-branch:

```python
elif value == "auto":
    label.update("Auto: safe tools auto-approved")
    label.set_class(True, "active")
    label.set_class(False, "plan-mode")
    label.set_class(False, "plan-swarm-mode")
```

The label string must distinguish `auto` from `acceptEdits` ("Auto-edit:
on") and from `bypassPermissions` ("Bypass: all auto-approved"). Wording:
`Auto: safe tools auto-approved` is acceptably distinct.

### 6.3. Cycle order

Verify the cherry-picked `action_cycle_permission_mode` matches:

```python
modes = ["bypassPermissions", "acceptEdits", "auto", "plan", "default"]
```

If the cherry-pick lands a different ordering, keep abast's. The notification
`display` dict in `app.py:610ff` must include the `auto` entry:

```python
display = {
    "default": "Default",
    "acceptEdits": "Auto-edit",
    "auto": "Auto",
    "plan": "Plan",
    "bypassPermissions": "Bypass",
    "planSwarm": "Plan swarm",
}
```

### 6.4. Settings-screen integration

The `default_permission_mode` enum (§1.5) includes `auto`. The
`SelectionPrompt` choices must list all five modes; selecting `auto` and
saving causes a fresh-install user to land in the same state as A6 intends
(default `auto`).

### 6.5. New-install path

Per A6, on a fresh install the config defaults to `default_permission_mode:
auto`. This is `5700ef5`'s responsibility, not this spec's. The settings UI
displays whatever value is in `CONFIG`. The `Reset` action (§1.12) on
`default_permission_mode` resets to `auto` (the new default), matching the
cherry-picked default.

---

## 7. Documentation reference page (`docs/configuration.md`) — content scope

This spec defines *what content* belongs in `docs/configuration.md`. An
Implementer authors the prose.

### 7.1. File path

`docs/configuration.md` (new file).

### 7.2. Content scope

Six sections, in order:

#### 7.2.1. Overview (~100 words)

- Pointer to `/settings` UI for interactive editing.
- Statement of the 2-tier config model (user / project) per L8/A5.
- Pointer to `~/.claudechic/config.yaml` (user) and
  `<launched_repo>/.claudechic/config.yaml` (project) as the on-disk
  locations (post-restructure paths per L5/L6).
- Note: defaults live in code (no package-tier config file).

#### 7.2.2. User-tier config keys

One subsection per key:

| Required content per key |
|---|
| Canonical key path (e.g., `default_permission_mode`, `analytics.enabled`) |
| Type and accepted values |
| Default |
| One-paragraph description |
| Example YAML |
| Whether exposed in `/settings` (yes/no) |

Keys to document (per #23 + this spec):
`default_permission_mode`, `show_message_metadata`, `vi-mode`,
`recent-tools-expanded`, `worktree.path_template`, `analytics.enabled`,
`analytics.id` (documented but not exposed), `logging.file`,
`logging.notify-level`, `themes`, `experimental` (documented but not
exposed).

#### 7.2.3. Project-tier config keys

Same shape as §7.2.2. Keys: `guardrails`, `hints`, `disabled_workflows`,
`disabled_ids`. For `disabled_workflows` and `disabled_ids`: include the
exact format (list of strings; for `disabled_ids` the `namespace:bare_id`
format with examples).

#### 7.2.4. Environment variables

Table with columns: variable, scope, default, description.

Required entries (per #23):
- `CLAUDECHIC_REMOTE_PORT`
- `CHIC_PROFILE`
- `CHIC_SAMPLE_THRESHOLD`
- `CLAUDE_AGENT_NAME`
- `CLAUDE_AGENT_ROLE`
- `CLAUDECHIC_APP_PID`
- `ANTHROPIC_BASE_URL`

Implementer must grep the codebase for any *additional* env vars not in
this list and add them.

#### 7.2.5. CLI flags

Table with columns: flag, type, default, description.

Required entries: enumerate from `claudechic/__main__.py` argparse setup
(currently includes `--resume`, `-s`, others). Implementer reads
`__main__.py` to get the full list.

#### 7.2.6. Cross-references

- Pointer to `vision.md` for the 3-tier content model (workflows / rules /
  hints / MCP tools — *content*, not *config*).
- Pointer to the in-app `/settings` screen.
- Pointer to `docs/privacy.md` for analytics details.

### 7.3. Terminology guardrail (binding L4)

The page's title is `# Configuration reference` — the *technical* word per
L4 §3.6 (asymmetry: UI is "Settings"; reference doc is "configuration").
First paragraph must lead with the L4 distinction so a reader landing here
understands why "Settings" appears in cross-references and why the file is
named `configuration.md`. Suggested opening sentence (Implementer may
rephrase):

> Use the `/settings` screen for interactive editing; this page is the
> ground-truth reference for every config key, environment variable, and
> CLI flag.

---

## 8. Key bindings summary

| Binding | Where | Action |
|---|---|---|
| `escape` | `SettingsScreen` | `action_close` (`self.dismiss(None)`) |
| `escape` | `DisabledWorkflowsScreen`, `DisabledIdsScreen` | `dismiss(None)` (no save) |
| `enter` | `_SettingRow` | open editor for that key |
| `space` | `_SettingRow` (bool keys only) | toggle in place |
| `space` | row in `DisabledWorkflowsScreen` / `DisabledIdsScreen` | toggle disable |
| `enter` | `DisabledWorkflowsScreen` / `DisabledIdsScreen` | accept current selection (`dismiss(frozenset)`) |
| `/` | `SettingsScreen` | focus search input |
| `r` | `SettingsScreen` | jump to next "Reset" row |
| Existing `shift+tab` | global | unchanged; cherry-picked code already cycles `auto` |

The settings UI does **not** introduce any priority binding that would
override existing app bindings.

---

## 9. Navigation flow

### 9.1. Entry points (three; all route to `_handle_settings()`)

```
[chat screen footer]   ──click "settings"──┐
[/settings command]    ──dispatch ─────────┤──> ChatApp._handle_settings()
[welcome screen]       ──"Settings" item──┘                │
                                                            ▼
                                            push_screen(SettingsScreen())
```

### 9.2. Within SettingsScreen

```
SettingsScreen
  │
  ├─[enter on enum row]──> SelectionPrompt (inline) ──save──> back to list
  ├─[enter on bool row]──> toggle in place
  ├─[enter on int/text]──> QuestionPrompt (inline) ──save──> back to list
  ├─[enter on subscreen row]──> push DisabledWorkflowsScreen / DisabledIdsScreen
  │                                          │
  │                                          └─[esc | enter]──> dismiss to list
  ├─[enter on "Open configuration.md"]──> notify("see docs/configuration.md")
  └─[esc]──> dismiss(None) → back to chat
```

### 9.3. Welcome → Settings

When the welcome screen dismisses with `RESULT_SETTINGS`, the app handler
pushes `SettingsScreen` directly. The welcome screen does **not** stay
underneath; the standard pattern is welcome dismisses first, then
`_handle_settings()` is invoked. This matches existing handling for
`tutorial` and `picker` results.

---

## 10. Constraint mapping (A4 / A6 / A7 / A12)

| Constraint | How this UI design respects it |
|---|---|
| **A4** (behavioral mirror; no symlinks; no Claude-settings overwrites) | The settings UI does **not** edit `~/.claude/settings.json`. The `analytics.id` key is hidden (per #23) but stored in `~/.claudechic/config.yaml` only — no spillover into `.claude/`. No design element of this spec writes anywhere under `.claude/`. |
| **A6** (auto-mode startup default) | §6 covers the footer label, the cycle, and the settings-screen enum. The default is set by cherry-pick `5700ef5`; the UI displays it. |
| **A7** (boundary primary-state-only) | The settings UI's primary state is the user/project config files at `~/.claudechic/config.yaml` and `<launched_repo>/.claudechic/config.yaml`. No primary state lives in `.claude/`. |
| **A12** (smaller features delegated) | All four sub-features in scope (§4 welcome access; §1.10 disabled_workflows discovery; §1.11 disabled_ids listing; §2+§3+§4 button/command parity). See appendix §3 for in-scope rationale. |
| **L4** (settings vs config terminology) | All UI labels say "Settings" / "settings". Code symbols continue to use "config" (`SettingsScreen` is a UI symbol; `CONFIG` and `ProjectConfig` are internal). The reference doc is `configuration.md` per the L4 §3.6 asymmetry. |
| **L13** (no time estimates) | No timing language anywhere in this spec. |
| **L14** (operational only) | This file contains layout, widget references, file paths, key bindings, save semantics, navigation. Rationale, alternatives, postponement decisions, and terminology adjudication are in `ui_design_appendix.md`. |

---

## 11. Vision/STATUS errors flagged (per A1)

### 11.1. Vision §"Success looks like" — single-vs-dual config edit ambiguity

Vision says: *"A user can edit per-user config in their `/settings` UI ...
and have it apply to every project they work in. They can edit per-project
config and have it apply only there."* This is faithful to L8/A5 (2-tier
config), but it doesn't say whether `/settings` exposes both tiers in one
screen or pushes separate screens.

This spec resolves to **one screen with both tiers visible** (§1.4 mock,
two header sections). This is the natural reading of the user's words —
"settings button in the bottom" is one button, one screen — but it is a
spec-level choice not in the vision. Surfacing for the coordinator's
awareness; the design proceeds on this resolution unless otherwise
directed.

### 11.2. Issue #23 — `themes` editor under-specified

Issue #23 lists `themes` as a key to expose in settings, but the existing
`/theme` command is a search-and-pick flow, not a "set theme = X"
operation. This spec routes `themes` editing to the existing `/theme`
flow rather than building a redundant editor. If the intent of #23 was to
*enumerate available themes* (rather than reuse the search), the spec
needs a different approach. Surfacing for confirmation; default reading is
"reuse `/theme`".

### 11.3. Issue #23 — `disabled_ids` ambiguity (hints? rules? both?)

Issue #23 lists `disabled_ids` as a project-tier key with "available ID
listing" but does not say whether it covers hint IDs, guardrail rule IDs,
or both. The existing `claudechic/global/hints.yaml` and `rules.yaml` both
use namespaced IDs. This spec covers **both** in `DisabledIdsScreen`
(§1.11) with category headers. If the intent was hint-only or rule-only,
the spec narrows accordingly. Surfacing for confirmation.

---

## 12. Test surface (delegated to test-strategy spec)

This UI design produces these testability hooks. The test-strategy spec
(separate document) consumes them:

- `SettingsScreen` and its subscreens are pure `Screen[T]` with no live
  agent dependency; testable via Textual's `Pilot`.
- `_handle_settings()` is one method; assert it's called from all three
  entry points (footer button click, `/settings` dispatch, welcome
  `RESULT_SETTINGS`).
- The config save path is the *only* place writes occur; assert it writes
  to `.claudechic/` paths only (boundary lint, per Skeptic R1/R5).
- The workflow-picker tier badges are deterministic given a registry
  snapshot; assert each tier renders correctly.
- The permission-mode footer label has six states (six display strings);
  assert each.

---

*End of ui_design.md.*
