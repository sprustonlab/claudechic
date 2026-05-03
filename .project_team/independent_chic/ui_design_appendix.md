# UI Design Appendix — independent_chic

**Author:** UIDesigner (Specification phase)
**Status:** Rationale companion to `ui_design.md`. Per L14, this file
contains *why* (alternatives considered, rejected designs, postponement
rationale, terminology decisions). Operational instructions live in
`ui_design.md`.
**Audience:** Coordinator, future spec/impl agents who need to understand
*why* a design choice was made before reversing it.

---

## 1. Why these designs

### 1.1. Why a single `SettingsScreen` rather than a tabbed/paginated UI

**Decision:** One screen, two header sections (User / Project), no tabs.

**Alternatives considered:**

- **Tabbed UI (User tab / Project tab):** Tabs add a navigation step the
  user almost never wants — both tiers fit on a single page (~14 keys
  total). Tabs hide the project-tier keys behind a click; users editing
  hints/guardrails project-locally would have to learn the tab UX. The
  scrollable single-page list mirrors `WelcomeScreen`'s checklist shape
  and doesn't require new navigation primitives.

- **Two separate screens (`/usersettings`, `/projectsettings`):** Doubles
  the entry-point surface for no real benefit. The user's word in #24 was
  "settings button in the bottom" — singular. Splitting into two screens
  invents UX the user did not ask for.

- **Modal (like `DiagnosticsModal`):** Modals work for read-only display
  with copy buttons; they're cramped for editable forms with multi-line
  rows and inline editors. The full-screen `Screen` pattern (from
  `WorkflowPickerScreen`, `WelcomeScreen`) gives space for both tiers
  plus the search input plus the help bar.

**Rejected.** Pick the single-screen layout because it matches the user's
phrasing, fits all keys without paging, and reuses existing screen
primitives.

### 1.2. Why "save live" rather than "Save / Cancel"

**Decision:** Edits save immediately on confirmation in the per-key editor.

**Alternatives:**

- **Explicit Save button:** Adds a destructive-on-discard interaction (if
  user escapes by accident, edits lost). Live-save is what the user
  effectively gets today by editing `~/.claude/.claudechic.yaml` in a text
  editor — there's no "discard" semantic in the file workflow either.

- **Save-on-close (like a form):** Same risk as above. Also forces the
  user to remember which keys they touched.

**Rejected.** Live-save matches the existing mental model (config edits
are always immediate), removes a "did I save?" anxiety, and aligns with
the live-applied feedback (toggling `vi-mode` in the UI should toggle the
mode in the chat *now*, not on close).

The notification-on-failure path (saved-but-failed-to-apply) keeps the
file authoritative and the runtime state best-effort. This matches the
existing `ProjectConfig.load` "fail-open" stance.

### 1.3. Why both a footer button **and** a slash command

**Decision:** Both surfaces exist (A12.d in scope).

**Alternative:** Pick one. The user's #24 says "settings button in the
bottom"; #23 says "accessible via `/settings` or welcome screen". Both
issue threads explicitly ask for different access paths; neither says
"only this one." Shipping one and not the other is a clear gap surfaced by
the alignment lens (`alignment_audit.md` §1.7) and would require the user
to learn which surface ships and which doesn't.

Footer button serves discoverability; slash command serves keyboard
muscle memory. Welcome-screen item (§4) serves first-time users. All
three call the same `_handle_settings()` so the screens never diverge.

### 1.4. Why `disabled_workflows` and `disabled_ids` are subscreens, not inline

**Decision:** Push a dedicated `Screen` for the multi-select.

**Alternative:** Inline checklist within the row (expanding row).

Multi-select inside a list row breaks the "one row = one keybinding" model
and conflicts with the `_SettingRow` toggle semantics for boolean keys.
Inline expansion would also require nested scroll handling. A pushed
subscreen is the same pattern `WorkflowPickerScreen` uses for picking
workflows; reusing the pattern is cheaper than inventing a new one.

The subscreen approach also gives room for the tier badges (workflow
tier, hint tier, rule tier) and metadata (rule level, hint
namespace) that wouldn't fit in an inline expansion.

### 1.5. Why the workflow picker shows tier badges next to each item, not as group headers

**Decision:** Per-item badge `[pkg]` / `[user]` / `[proj]`.

**Alternatives:**

- **Group headers (collapsible by tier):** Hides workflows behind a
  click; the user would have to expand the package group to find a
  bundled workflow. Defeats discoverability. The default sort (project →
  user → package) achieves grouping visually without hiding.

- **Color-only distinction (no `[badge]`):** Color isn't accessible for
  colorblind users and isn't visible in monochrome terminals. The text
  badge complements the color and remains readable everywhere.

- **Badge after the workflow name, in parens:** Looks like prose
  ("`tutorial (package)`"); the bracketed badge looks like a tag/chip,
  matching how the rest of the UI uses bracketed tier hints (e.g., agent
  status chips in `sidebar.py`).

**Rejected** the alternatives; per-item bracketed badge wins on
accessibility, immediacy, and consistency with existing visual idiom.

### 1.6. Why the "Auto" permission-mode label says "Auto: safe tools auto-approved"

**Decision:** Distinct prose from `acceptEdits` ("Auto-edit: on") and
`bypassPermissions` ("Bypass: all auto-approved").

**Alternatives:**

- **"Auto"** (single word): ambiguous against `acceptEdits` ("Auto-edit:
  on") and easy to misread as "Auto-edit" in peripheral vision.

- **"Auto mode"**: marginally better but doesn't tell the user *what* is
  automatic. The label real estate in the footer is small but not that
  small; spelling it out aids first-time discoverability.

- **"Auto-approve safe tools"**: redundant with the existing
  bypassPermissions wording.

**Rejected.** Keep the chosen wording. If terminology lens flags this
during their final review, defer to terminology — the spec's wording is
load-bearing only on distinctness, not on the exact phrasing.

---

## 2. Terminology decisions

### 2.1. UI label vs code symbol naming

Per L4 (`terminology_glossary.md` §3.1, §3.3, §3.5):

| Surface | Naming |
|---|---|
| Screen class | `SettingsScreen` (UI symbol — "Settings" word per L4) |
| Footer label | `SettingsLabel` (UI symbol — "Settings" word per L4) |
| Slash command | `/settings` (user-facing — "settings" per L4) |
| Footer label text | `settings` (lowercase, matches sibling labels `sys`, `session_info`) |
| Subscreen classes | `DisabledWorkflowsScreen`, `DisabledIdsScreen` (UI symbols) |
| Subscreen module names | `claudechic/screens/disabled_workflows.py`, `disabled_ids.py` (file paths use the project-tier *config-key* names — files are technical, per L4 §3.3) |
| Reference doc filename | `docs/configuration.md` (technical, per L4 §3.6 asymmetry) |
| Reference doc title | `# Configuration reference` (technical) |
| App method name | `_handle_settings()` (UI-handler, leads with the user-facing word — matches existing `_handle_welcome()`, `_handle_analytics()` pattern) |
| Config dataclass | `ProjectConfig` — unchanged, per L4 "no code-symbol renames are forced" |
| Module-level dict | `CONFIG` — unchanged |

### 2.2. The L4 §3.6 asymmetry surfaced

`terminology_glossary.md` §3.6 notes that the UI is "Settings" but the
reference *document* is `configuration.md`. The spec preserves this by
naming the file `docs/configuration.md` and titling it `# Configuration
reference` — but the first paragraph of the reference doc anchors the
asymmetry explicitly so a confused reader gets pointed at the L4 split.
This is the spec author's resolution of `terminology_glossary.md` §9.2's
warning about asymmetric naming.

### 2.3. Tier badge wording

Chose `[pkg]` / `[user]` / `[proj]` (4-char-or-less tags) over
`[package]` / `[user]` / `[project]` (full words):

- Footer width is constrained; `[pkg]` keeps the badge tight without
  truncating workflow names.
- The full words appear in the section headers (`━━ User settings ━━`,
  `━━ Project settings ━━`); the per-row badge is a reminder, not a
  primary label.

If the terminology lens prefers full-word badges, both are operationally
equivalent — only the CSS width changes (`workflow-tier { width: 8 }` →
`{ width: 12 }`).

---

## 3. A12 decision log — why all four smaller features are in scope

A12 (STATUS): *"The smaller UX gaps surfaced from issue #23 ... are
delegated to the spec-phase team. The team may include them in scope or
postpone any of them if scope balloons. Postponements must be recorded
with explicit rationale."*

The four candidate features:

### 3.1. Welcome-screen access to settings (A12.a) — IN SCOPE

**Effort cost:** One new constant (`RESULT_SETTINGS`), one new
`_ActionItem` in `WelcomeScreen.compose()`, one new branch in the welcome
dismiss handler in `app.py`. ~15 lines of code in three locations.

**Benefit:** Issue #23 explicitly asks for it ("accessible via /settings
or welcome screen"). It's also the natural discovery path for first-time
users — the welcome screen is where new installs land.

**Scope-balloon risk:** None. The welcome screen already handles 4
results via the same pattern; adding a 5th is mechanical.

**Decision:** In scope.

### 3.2. Disabled-workflows ID discovery (A12.b) — IN SCOPE

**Effort cost:** One new screen file (`disabled_workflows.py`); the
underlying registry (`app._workflow_registry`) is already populated by
the loader. The registry already needs a tier-aware shape change for the
workflow picker (#24) so this subscreen rides on that change.

**Benefit:** Without this, the user sets `disabled_workflows` blindly
(typing IDs from memory or grepping the codebase). With this, IDs are
discoverable in the UI. Issue #23 explicitly says "with workflow ID
discovery."

**Scope-balloon risk:** Low. The screen is a list-with-checkboxes pattern
that mirrors the workflow picker.

**Decision:** In scope.

### 3.3. Disabled-IDs listing (A12.c) — IN SCOPE

**Effort cost:** One new screen file (`disabled_ids.py`); reads the
hint registry (`app.hints_engine.all_hints()`) and the guardrail
registry (`app.guardrails.all_rules()`), both of which exist (or are
trivially addable to the existing engines).

**Benefit:** Same logic as A12.b — without it, `disabled_ids` is set
blindly. Issue #23 explicitly says "with available ID listing."

**Scope-balloon risk:** Slight ambiguity in *what* `disabled_ids`
covers (hints? rules? both?). This spec resolves both (§1.11 of
ui_design.md) with category headers.

**Decision:** In scope, with the dual-category resolution flagged in
ui_design.md §11.3 for coordinator review.

### 3.4. Settings-button vs `/settings`-command parity (A12.d) — IN SCOPE (REQUIRED)

**Effort cost:** Both surfaces invoke a single shared method
(`_handle_settings()`). The cost is ~5 lines for the button handler + 4
lines for the command dispatch. They cannot diverge because they're
literally the same method call.

**Benefit:** Without parity, users learn one surface and miss the other.
The two issue threads (#23 mentions `/settings`, #24 mentions
"settings button in the bottom") together unambiguously imply both must
work. UserAlignment lens flagged this explicitly (`alignment_audit.md`
§1.7: *"the spec must call out **both** the bottom button and `/settings`
command as access paths"*).

**Scope-balloon risk:** None — parity is the whole point of routing both
to one method.

**Decision:** In scope. Required by the issue text.

---

## 4. Rejected designs and why

### 4.1. Rejected: Settings as an `InfoModal` subclass

`InfoModal` (claudechic/widgets/modals/base.py) is the read-only labeled
section pattern (used by `DiagnosticsModal`, `ComputerInfoModal`,
`ProfileModal`). It supports copy buttons but not editing. Settings is
fundamentally an editor; conflating it with InfoModal would either:

- Force per-row editor flows that fight the modal's compact layout, or
- Reduce settings to a read-only display that links out to the YAML file
  (fails the "edit" verb in #23).

**Rejected.** Use `Screen[None]` (the full-screen pattern) instead. The
two patterns serve different purposes and shouldn't be unified.

### 4.2. Rejected: Settings UI exposes `analytics.id` and `experimental.*`

Issue #23 explicitly lists these as "internal" (do not expose). Hiding
them is a direct user instruction.

A "show internal settings" toggle was considered for power-user
discoverability but rejected: the toggle adds a UI affordance for
something the user can already get by reading
`~/.claudechic/config.yaml` directly. The reference doc
(`docs/configuration.md`) documents these keys for users who need to know.

### 4.3. Rejected: A separate "Reset entire config" button

The per-section `Reset` rows (§1.12 of ui_design.md) are sufficient.
Adding a "Reset everything" button creates a destructive single-click
that's easy to fire accidentally; the per-section split forces the user
to make two distinct destructive choices (user reset, project reset)
rather than one global one.

### 4.4. Rejected: Workflow-picker tier badges as colored bullets only

`●` (color-only) badges are accessibility-hostile (colorblind users,
monochrome terminals, screenshots in non-color screen-readers). The
text-plus-color combination (`[pkg]` in muted gray, `[user]` in
secondary blue, `[proj]` in primary orange) covers both audiences.

### 4.5. Rejected: Auto permission mode displayed as a single icon `⚡`

Footer real estate is small but not iconographic; the text labels
elsewhere ("Auto-edit: on", "Plan mode") are wordy on purpose so users
can read state at a glance. An icon would be inconsistent and require
a legend.

---

## 5. Open questions surfaced for the coordinator

These are spec-level resolutions where the design picked one path; the
coordinator may want to confirm with the user before implementation.

### 5.1. Is `themes` editing best routed via the existing `/theme` flow?

The settings UI (§1.5) routes the `themes` row to the existing
`app.search_themes()` flow rather than building a separate enumeration.
Issue #23 lists `themes` as a key to expose without specifying the
editor shape. If the user wanted a full theme-list view, the spec
would need a `ThemesPickerScreen` instead.

**Default:** reuse `/theme`. Cheap to change later.

### 5.2. `disabled_ids` covers hints AND guardrail rules — confirm

§1.11 covers both. If the intent of #23 was hint-only or rule-only, the
screen narrows. The dual-category UI is strictly more general; narrowing
later is mechanical.

**Default:** both, with category headers.

### 5.3. Single-screen vs separate-tier-screens for SettingsScreen

ui_design.md §11.1 surfaces this. The spec defaults to single screen
with two header sections. If the user prefers separate `/usersettings`
and `/projectsettings`, the spec splits along the section boundary —
also mechanical to refactor.

**Default:** single screen, two sections.

### 5.4. Live-save vs explicit Save button

ui_design.md §1.7. If the user prefers an explicit Save (some users want
"diff what I'm about to do"), the spec adds a Save button and a
"Discard?" prompt on Esc. This is a UX preference question, not a
correctness one.

**Default:** live save.

---

## 6. Reuse audit — cost of NOT reusing

The spec leans heavily on existing widgets. The cost of not reusing,
for transparency:

| If we built new instead | Cost |
|---|---|
| Custom `Screen` infrastructure | Reinvent the navigation/dismiss/binding wiring `WorkflowPickerScreen` already has |
| Custom prompt widgets | Reinvent `SelectionPrompt` and `QuestionPrompt` (both in `prompts.py`) |
| Custom modal-base | Reinvent `InfoModal`'s copy-to-clipboard idiom (used by `_copy_all`) |
| Custom collapsible | Reinvent `QuietCollapsible` (auto-scroll-suppression bug-fix already in there) |
| Custom click-label primitive | Reinvent `ClickableLabel` (in `widgets/base/clickable.py`) |

Reuse is cheap and well-understood. The new code in this spec is
~300 lines (estimated by file-list — three new screen modules + one new
footer label + small touches in `app.py`, `commands.py`,
`welcome.py`, `footer.py`, `workflow_picker.py`, `styles.tcss`).

---

## 7. Reversal triggers

If any of these turn out wrong post-implementation, here's where to look:

| Symptom | Likely cause | Where to revisit |
|---|---|---|
| Users can't find the settings UI | Footer label too subtle, or welcome screen not shown for returning users | §2 footer label color; §4 welcome screen visibility logic |
| Edits don't apply until restart | Live re-apply step missing for a key | §1.7 table — add the missing re-apply call |
| Two screens drift in displayed values | `_handle_settings` not actually shared by all three entry points | §2.3, §3.2, §4.3 — assert single method call |
| Workflow picker doesn't distinguish tiers | `_workflow_registry` shape change didn't ship, or loader doesn't populate `tier` | §5.2 — fix the registry shape; loader gives wrong tier |
| `disabled_ids` page is empty | Hint/rule registries not exposed via `app.hints_engine.all_hints()` etc. | §1.11 — add the missing accessor methods |
| Permission mode "auto" displays the wrong text | `watch_permission_mode` else-branch caught it | §6.2 — verify `auto` case lands above the default else |

---

## 8. Notes for the docs author

When writing `docs/configuration.md` (Implementer authors prose; this spec
defines content scope in ui_design.md §7), keep these in mind:

- Lead with the L4 distinction. The reader landing on the page will see
  "Configuration reference" and may wonder why the in-app UI says
  "Settings". One short sentence resolves this.
- Match the key descriptions to what the in-app `/settings` editor shows.
  If the editor calls `default_permission_mode` "Default permission mode",
  the docs page heading should match exactly. Drift between the two
  surfaces is a recurring user complaint vector.
- Don't duplicate the vision document. The vision explains *why* the
  3-tier model exists; the configuration reference explains *what each
  config key does*. Cross-link, don't restate.
- For each project-tier key, give a concrete example. `disabled_ids`
  especially benefits from a worked example showing the namespace format.

---

## 9. Closing alignment notes

- The spec leans on the user's verbatim asks (#23 + #24). Where the spec
  goes beyond the verbatim text, ui_design.md §11 surfaces the choices.
- Per A1, three vision-text issues are flagged in ui_design.md §11; none
  block.
- Per A12, all four sub-features are in scope; rationale for in-scoping
  each is in §3 above.
- Per L13, no time estimates appear here.
- Per L14, no operational instructions appear here — those are all in
  ui_design.md.

---

*End of ui_design_appendix.md.*
