# Specification — UI-surface axis (axis C)

**Author:** ui_surface axis-agent
**Date:** 2026-04-29
**Phase:** project-team:specification
**Scope:** Sub-feature C (effort cycling) + the architectural-layer-axis-C
files (`widgets/modals/*`, `widgets/layout/footer.py`, `app.py`,
`styles.tcss`). The destructive `widgets/modals/diagnostics.py` deletion
and the modal-restructure changes (`computer_info.py`, `base.py`) live
on this axis.

This document recommends per-feature outcomes in the form
`(sub-feature, outcome in {adopt, adapt, skip, partial}, blocking-deps)`
per Composability's compositional law.

---

## 0. Domain understanding

The footer is a tray of independent click-handler labels (model,
permission-mode, diagnostics, sys, settings). Each label is a small
`ClickableLabel` subclass that posts a `Message` on click, handled by
`ChatApp` via Textual's `on_<label>_<message>` dispatch. This is a
clean compositional surface: each label is one independent slot in
the footer; the seam between label and `ChatApp` is the typed `Message`.

**First-use definitions (per UserAlignment C6):**
- **EffortLabel** -- the new footer widget abast adds in `accf332`. A
  `ClickableLabel` subclass that displays the current effort level
  (e.g. `effort: high`, `⚡ low`) and cycles through valid levels on
  click.
- **diagnostics modal** -- the existing `DiagnosticsModal` in
  `widgets/modals/diagnostics.py` on our base. Shows the active
  session's JSONL file path + the last compaction summary. Reached via
  the footer's `session_info` label.
- **computer-info modal** -- the existing `ComputerInfoModal` in
  `widgets/modals/computer_info.py` on our base. Shows host, OS,
  Python, SDK, claudechic versions, and CWD. Reached via the footer's
  `sys` label.
- **unified Info modal** -- accf332's renamed `ComputerInfoModal` that
  absorbs the diagnostics modal's content into one consolidated modal.
- **GuardrailsModal** -- the new modal abast adds in `accf332` listing
  all active guardrail rules and injections with per-row toggle
  checkboxes. Out of scope for this axis-agent (lives on
  guardrails-seam).

accf332 makes three orthogonal changes on this surface:

1. **Insert** a new `EffortLabel` (sub-feature C, the abast label
   "effort cycling"). Pure addition.
2. **Rename** `DiagnosticsLabel` -> `InfoLabel` and consolidate the
   diagnostics modal into the computer-info modal (sub-feature D's
   modal-restructure portion).
3. **Rename** `ComputerInfoLabel` -> `GuardrailsLabel` and re-point its
   click to a new GuardrailsModal (sub-feature D proper).

Changes 1 and 2 are mutually independent; change 3 only makes sense if D
(guardrails UI) is adopted. The footer's compositional law is "one
label = one independent click-cycle / click-prompt slot" -- accf332
respects it.

---

## 1. Sub-feature C -- effort cycling

### 1.1 Self-containment (Q1 from must-answer list)

C touches the following files in accf332:

| File | accf332 lines | Our drift | Conflict |
|------|---------------|-----------|----------|
| `widgets/layout/footer.py` | new `EffortLabel` (~95), reactive `effort` on `StatusFooter`, `watch_effort`, footer mount slot | +25 (we added `SettingsLabel`) | minor mechanical merge in the `compose()` method only |
| `widgets/__init__.py` | +EffortLabel re-export (~2 lines) | unrelated | clean |
| `widgets/layout/__init__.py` | +EffortLabel re-export (~2 lines) | unrelated | clean |
| `agent.py` | `self.effort: str = "high"` (1 line) | small (B-related, line 195) | clean (different region) |
| `app.py` | C-related ~25-30 of the +282 | +779 lines of independent evolution | local conflicts only on the regions C touches |
| `styles.tcss` | `EffortLabel:hover { background: $panel; }` (3 lines) | 0 drift | clean |

C does **NOT** touch:

- `paths.py` (A) or `workflows/engine.py` / `loader.py` /
  `agent_folders.py` (A and B).
- `guardrails/` (D, E).
- `widgets/modals/*` (D's modal restructure).
- `defaults/global/rules.yaml` (E).

**Verdict: C is genuinely independent of A, B, D, E.** The only file
that C shares with other sub-features is `app.py`, but the C-related
regions are local handlers and a small block in `_make_options` /
the model-change path -- they do not touch the `_activate_workflow` /
`_deactivate_workflow` / `_guardrail_hooks` machinery that B and D
rewrite. Implementing C without B/D would require trimming
`_make_options(agent=agent)` to a simpler `effort_level = self._agent.effort`
read; otherwise C composes onto our base unmodified.

### 1.2 Effort levels (Q2)

- **Levels:** `low | medium | high | max`. `max` is Opus-only (matches
  the SDK's `effort: Literal['low','medium','high','max']` parameter).
- **Per-model filtering:** `EffortLabel.MODEL_EFFORT_LEVELS` filters by
  family-name substring match (`opus | sonnet | haiku`). On model change,
  the label snaps to the closest valid level (descending by the global
  ordering `(low, medium, high, max)`). This logic lives inside
  `EffortLabel.set_available_levels()`.
- **Default:** `"high"` (set in `EffortLabel.__init__`, in
  `Agent.__init__`, in `StatusFooter.effort = reactive("high")`).
- **Display strings:** `"⚡ low"`, `"effort: med"`, `"effort: high"`,
  `"effort: max"`.
- **Persistence:** **NONE.** `Agent.effort` is an instance attribute
  on `Agent`. It survives agent switching (each `Agent` carries its
  own `effort`) but does NOT survive process restart. It is not written
  to `settings.json`, the chicsession state, or the session JSONL.
- **Plumbing into the SDK:** `_make_options` resolves `effort_level`
  from `agent.effort` (or `self._agent.effort`) and passes
  `ClaudeAgentOptions(effort=effort_level, ...)`. The SDK pin on our
  base already accepts the `effort` parameter (verified:
  `ClaudeAgentOptions.__init__` signature includes
  `effort: Literal['low','medium','high','max'] | None = None`).
- **Per-agent vs app-global:** per-agent. Each `Agent` has its own
  `effort`; the `StatusFooter` mirrors the active agent's effort.

### 1.3 Footer-cycle UX collision (Q3)

- **Effort cycling gesture:** click on `#effort-label`. `EffortLabel.on_click`
  advances `self._effort` to the next level in `self._levels` (mod
  length) and posts `EffortLabel.Cycled(next_effort)`.
- **Permission-mode cycling gesture:** click on `#permission-mode-label`
  *and* `Shift+Tab` keybinding. Both post `PermissionModeLabel.Toggled`.
- **No keybinding collision:** Shift+Tab does NOT cycle effort; only
  permission mode. accf332 introduces no new keybinding.
- **Vocabulary collision:** mild. Both labels are click-cycle footer
  labels with text-mutation on click. The label texts are visually
  distinct (`Auto-edit: off` / `Plan mode` / `Auto: safe ...` vs
  `effort: high` / `effort: med` / `⚡ low`), so a user discovers the
  intent from the label text. The gestural pattern is consistent
  (click footer label = step the knob).
- **Discoverability nit:** a power user accustomed to Shift+Tab cycling
  permission mode might assume Shift+Tab also cycles effort by analogy.
  This is a polish issue, not a correctness issue. Not a blocker.

Terminology's collision-risk flag (LOW) holds.

### 1.4 Skeptic Q1-Q6

| Q | Answer | Reasoning |
|---|--------|-----------|
| Q1 (problem doesn't apply?) | **No** | The SDK's `effort` parameter is real and supported on our SDK pin. Any user on Opus benefits from `max`; any user on a paid plan benefits from being able to drop to `low`. |
| Q2 (breaking contract?) | **No** | Adds an instance attr on `Agent`, one new SDK pass-through, one new widget. settings.json schema unchanged (effort is session-ephemeral). MCP API unchanged. Observer protocols unchanged. Workflow YAML schema unchanged. On-disk state file format unchanged. |
| Q3 (abast-only infra?) | **No** | Pure footer + SDK pass-through. No prerequisite ports. |
| Q4 (one-sentence delta + concrete user?) | **Yes (passes)** | "Before: no UI for the SDK `effort` knob; user must set it via code or env. After: clicking `effort: high` in the footer cycles low/med/high (and `max` on Opus); next SDK call uses the chosen effort." Concrete user: anyone on Opus who wants to flip extended thinking on/off mid-session, or anyone who wants to drop to `low` for low-stakes turns to save tokens. |
| Q5 (simpler in-tree change?) | **Partial** | A bare `effort: high` knob in `~/.claudechic/config.yaml` plumbed through `_make_options` would deliver ~50% of the value at ~10% of the cost (no UI, no per-model snapping, no per-turn control, no per-agent state). The cycling UI delivers material additional value: discoverability (the user sees the option in the footer), per-turn control without restarting the session, and per-model level filtering. **Recommend adopt with the UI**, but flag persistence as a missing piece. |
| Q6 (regresses a property we rely on?) | **No** | No state-shape change. No MCP change. No rule change. No keybinding change. |

No "yes" answers => C is not a skip candidate.

### 1.5 Domain-gestalt test for the label "effort"

(Per UserAlignment's standing-check advisory.)

The accf332 label text in the footer is literally `effort: high` (or
`⚡ low`, `effort: med`, `effort: max`). The gestalt question: does a
user looking at the footer **immediately** know what "effort" means
and which direction is "good"?

Reading the diff and comparing to neighboring labels:

| Footer label | Self-evident? |
|--------------|---------------|
| `Opus 4.6` (model) | Yes -- model name. |
| `Auto-edit: off` / `Plan mode` / `Auto: safe ...` (permission) | Yes -- says what it does. |
| `session_info` -> `info` (diagnostics) | Borderline; a click reveals a labelled list. |
| `sys` (computer info) | Borderline; a click reveals a labelled list. |
| `settings` | Yes. |
| `effort: high` (effort) | **No.** "Effort" is jargon for the SDK's thinking-budget knob (`Literal['low','medium','high','max']`). A new user seeing `effort: high` cannot tell whether "high" is good or bad, whether it costs more or less, what it controls, or that it disables on non-Opus models above `high`. The `⚡ low` glyph suggests speed, which only makes sense once you've already understood the trade-off. |

**Verdict: the label fails the one-glance gestalt test.** A concrete
user the failure costs: a first-time claudechic user on Opus who
clicks the label out of curiosity, sees their next response use
extended thinking (much slower), and does not connect cause and effect.
A sophisticated user familiar with the Anthropic SDK's `effort`
parameter passes the test trivially.

This is **NOT a blocker for adoption** -- the failure is a UX polish
issue, easily fixed in our base via:

- (a) **Tooltip on hover** describing what the level controls
  ("extended thinking budget; higher = better quality, slower, more
  tokens"), OR
- (b) **Rename** to a more user-facing term, e.g.
  `thinking: high` / `quality: high`, OR
- (c) **Notify on click** (already present: `self.notify(f"Effort: ...")`)
  could be expanded to one-shot explainer text on the first click of
  a session.

UserAlignment FLAG 1 ("use abast's exact wording") -- "effort cycling"
is a feature label and stays. The on-screen widget label `effort: high`
is a polish artifact and is fair game to refine if we adopt the
feature.

### 1.6 Per-feature recommendation for C

**`(C effort cycling, adapt, [])`**

- Outcome: **adapt** (not raw adopt). The functional axis is sound and
  has zero blocking deps, but the on-screen label fails the
  one-glance gestalt test (1.5). Adopt the wiring and the cycling
  mechanism; in implementation, add a tooltip-on-hover **or** rename
  the user-facing label so a first-time user can read the footer and
  understand the knob without prior SDK knowledge. Either is a small
  patch (1-2 lines + one CSS rule for tooltip).
- Blocking deps: NONE.
- One-sentence "after this lands, user sees X" (per UserAlignment C2):
  "The user sees a clickable label in the footer (text TBD by the
  rename/tooltip decision) that lets them step the SDK's
  thinking-budget knob mid-session; the next response uses the chosen
  level and the level snaps to a valid range when the model changes."
- Concrete user (per Skeptic Q4 / UserAlignment C7): a first-time Opus
  user who sees the footer, hovers, learns "this controls extended
  thinking quality vs speed", clicks once to drop to `low` for a
  quick lookup turn, clicks back up to `max` for a hard reasoning
  turn. Without the rename/tooltip patch, the same user sees
  `effort: high`, doesn't know what it means, and either (i) ignores
  it (feature wasted) or (ii) clicks it out of curiosity and gets a
  surprise change in response behaviour.
- One smell: persistence is missing. `Agent.effort` is process-ephemeral.
  Recommend a follow-up to harden by writing to `settings.json` or to
  the chicsession workflow_state. Not a blocker.

### 1.7 Contract surface impact for C

| Surface | Impact |
|---------|--------|
| settings.json schema | None. (Could be extended later with `effort_default: "high"`.) |
| MCP tool API | None. |
| Observer protocols | None. |
| Workflow YAML schema | None. |
| On-disk state file format | None. |

C is a pure-additive feature with zero contract churn. This is the
cleanest of the four candidate sub-features in the cluster.

---

## 2. `widgets/modals/diagnostics.py` deletion

### 2.1 Reference inventory

Grep of our base for `DiagnosticsModal`:

| File | Line(s) | Classification |
|------|---------|---------------|
| `claudechic/widgets/modals/diagnostics.py` | 47, 55-128 | (a) deletable along with the modal |
| `claudechic/widgets/modals/__init__.py` | 5 (import), 12 (`__all__`) | (a) export removed alongside |
| `claudechic/app.py` | 3641 (handler), 3643 (import), 3648 (push_screen) | (b) needs migration. accf332 replaces this handler with `on_info_label_requested` which pushes `ComputerInfoModal(cwd=cwd, session_id=session_id)`. |
| `CLAUDE.md` (project) | 150 | (a) docs line updates with the deletion (handled by accf332's commit 3 / `2f6ba2e`). |
| Tests | none | n/a |

Drift on `diagnostics.py` since merge-base `285b4d1`: **0 commits, 0 lines.**
The deletion will be a clean `git rm`.

No (c) blockers.

### 2.2 Replacement story

accf332 absorbs the diagnostics functionality into the unified Info
modal (`ComputerInfoModal`):

- `widgets/modals/computer_info.py` (rewrite, +68 lines): the modal
  ctor gains `session_id=` param. `_get_sections()` returns the existing
  System rows (Host / OS / Python / SDK / CWD / claudechic) **plus**
  two new InfoSection rows under a "Session" group:
  - `Session JSONL` (the resolved JSONL path, pulled from
    `get_project_sessions_dir(cwd)` -- same logic that lived in
    `diagnostics.py`).
  - `Last Compaction` (scrollable, from a verbatim copy of
    `_read_last_compact_summary()` from the deleted `diagnostics.py`).
- `widgets/modals/base.py` (+66 lines): adds `scrollable: bool = False`
  to `InfoSection`. When `scrollable=True`, the renderer wraps the
  content in a `VerticalScroll` with a per-section copy button. This is
  the infrastructure that lets the unified modal scroll the long
  compaction summary.

**Verdict: no info loss.** Every datum the old `DiagnosticsModal`
displayed (jsonl path + last compaction summary) is preserved in the
unified modal. The visual change is consolidation: one footer button
(`info`) opens one modal showing both system + session info, instead of
two separate buttons.

The information **gain** is small: a slightly cleaner footer (frees one
slot for `guardrails`) and one less modal class. The information
**loss** is zero.

### 2.3 Recommendation on the deletion

**`(diagnostics.py deletion + computer_info.py rewrite + base.py scrollable, adopt, [])`**

- Adopt as-is. The replacement story is complete (no info loss).
- V2 confirmed `computer_info.py` and `base.py` apply cleanly (zero
  drift on our side).
- The footer rename `DiagnosticsLabel -> InfoLabel` (label text
  `session_info -> info`) is part of this unit. Adopt it together with
  the deletion -- otherwise we have an `InfoLabel` ID mismatch with the
  app.py handler.
- Update `widgets/modals/__init__.py` to drop `DiagnosticsModal` from
  the exports.
- Update `CLAUDE.md` line 150 (handled by accf332 commit 3 / `2f6ba2e`,
  but our `CLAUDE.md` has drift; the editor needs to merge).

One-sentence "after this lands, user sees X" (per UserAlignment C2):
"The user sees one footer button labelled `info` instead of two
buttons labelled `session_info` and `sys`; clicking it opens a single
modal showing host / OS / Python / SDK / claudechic / CWD on top, then
Session JSONL path and a scrollable Last Compaction summary
underneath -- same data, fewer clicks." Concrete user: anyone who
previously had to click `session_info` to copy the JSONL path and then
click `sys` to read the SDK version sees both in the same modal now.

This recommendation is **independent of D's guardrails-modal outcome.**
Even if D is skipped, the modal-restructure unit (base.py +
computer_info.py + diagnostics.py deletion + InfoLabel rename) is a
self-contained refactor that makes our base cleaner. It is not a
prerequisite for the guardrails modal -- it merely happens to ship in
the same commit.

---

## 3. Modal restructure (`computer_info.py` + `base.py`)

### 3.1 Independent value (Q8)

The +68/+66 changes to `computer_info.py` and `base.py` are a refactor
that **stands on its own**. They are NOT a prerequisite for either C
(effort cycling, untouched) or D's GuardrailsModal (which subclasses
`ModalScreen` directly, not `InfoModal` -- see
`widgets/modals/guardrails.py:GuardrailsModal(ModalScreen)`).

What `base.py` adds:
- `InfoSection.scrollable: bool = False` field.
- `VerticalScroll` rendering branch with per-section copy button when
  `scrollable=True`.
- `_copy_to_clipboard(text)` factored out from `_copy_all`.

What `computer_info.py` adds:
- `_read_last_compact_summary` and `_resolve_jsonl_path` helpers
  (verbatim from `diagnostics.py`).
- `ComputerInfoModal.__init__` gains `session_id=` param.
- `_get_sections` returns 6 system rows + 2 session rows (one
  `scrollable=True` for the compaction summary).

These are useful for any future modal that wants a labeled-info layout
with a scrollable section. The change does not couple to guardrails or
to effort cycling.

### 3.2 Recommendation

**`(modal restructure: base.py + computer_info.py, adopt, [])`** as
part of the diagnostics.py deletion unit.

---

## 4. app.py wiring split: C vs D vs A vs B vs other

accf332 adds a NET +282 lines to `app.py` (the diff also deletes the
two `on_diagnostics_label_requested` and `on_computer_info_label_requested`
handlers, ~16 lines). Per-bucket attribution:

| Bucket | Approx share of +282 | Lines | What it covers |
|--------|---------------------|-------|----------------|
| **C (effort cycling)** | ~10% | ~25-30 | `EffortLabel` import (~1), `on_effort_label_cycled` handler (~7), `effort_level` resolution in `_make_options` (~6), `effort=effort_level` in `ClaudeAgentOptions(...)` (~1), `status_footer.effort = new_agent.effort` on agent switch (~1), `EffortLabel.set_available_levels` snap-back block in the model-change path (~10) |
| **D (guardrails UI + modal restructure)** | ~15-18% | ~40-50 | `InfoLabel`/`GuardrailsLabel` imports (~2), `_disabled_rules: set[str]` init (~1), `get_disabled_rules=...` plumbing into `create_guardrail_hooks` (~1), removed `on_diagnostics_label_requested` (-8), removed `on_computer_info_label_requested` (-8), added `on_info_label_requested` (~8), added `on_guardrails_label_requested` (~30), added `on_guardrail_toggled` (~6) |
| **A (template variables + state_dir + hits.jsonl move)** | ~16% | ~45 | `HitLogger` path move `.claude` -> `.claudechic` (~1), `compute_state_dir` import + ctor args + `state_dir.mkdir` in `_activate_workflow` (~12), `_workflow_template_variables` helper (~14), `variables=` plumbing into `assemble_phase_prompt` and `create_post_compact_hook` (~3), `from_session_state` mirror (~6), `state_dir` log line + `old_dir` warning (~9) |
| **B (dynamic roles)** | ~32% | ~90 | `GetRoleCallback` TYPE_CHECKING import (~1), `_guardrail_hooks(agent=..)` refactor + dynamic-role lambda (~20), `_merged_hooks(agent=..)` refactor (~15), `_make_options(agent=..)` refactor + agent.agent_type preference (~5), `_make_options(agent=agent)` at call sites x ~7 (~7), `create_unconnected(agent_type=DEFAULT_ROLE)` + import (~3), promote-on-activation block in `_activate_workflow` (~12), demote-on-deactivation block in `_deactivate_workflow` (~17), restore-role block in `from_session_state` (~10) |
| **Other (whitespace, formatting)** | ~2-3% | ~5-10 | line-break reformat for `self._resolved_workflows_dir`, etc. |

**Caveats on the attribution:**

- The buckets are not perfectly disjoint at the line level. The
  `_make_options(agent=agent)` plumbing serves both B (dynamic role
  resolution) and C (per-agent effort lookup). I attributed the
  threading itself to B (since that is the primary motivation), and
  attributed only the body that resolves `effort_level` and sets
  `effort=...` to C.
- `_disabled_rules` (D) is plumbed through `_guardrail_hooks` via
  `get_disabled_rules=...`. The hook itself is created via
  `create_guardrail_hooks` in `guardrails/hooks.py` -- that's
  guardrails-seam territory. The app.py-side plumbing is small.

### 4.1 Implication for cherry-pick planning

- **The C portion is small and surgical** (~25-30 lines). It can land
  with our base via a focused patch.
- **The D portion is moderate** (~40-50 lines), concentrated in
  three handler blocks. It depends on `compute_digest`, `GuardrailsModal`,
  and `_disabled_rules` (all D-axis additions).
- **A and B together account for ~135 of the +282.** They live entirely
  outside the UI-surface axis. Coordinate with engine-seam and
  guardrails-seam axis-agents.
- **Our +779 of independent app.py drift** is mostly orthogonal: settings
  / chicsessions / awareness install / 3-tier loader bootstrap.
  Conflicts will be local to the regions accf332 also touches
  (`_activate_workflow`, `_deactivate_workflow`, `_make_options`,
  `_guardrail_hooks`, `_merged_hooks`, the on_*_label_requested
  handler block, the model-change path).

---

## 5. Inter-axis dependencies and flags

| Flag | To axis | Issue |
|------|---------|-------|
| **F1** | guardrails-seam | If D (full GuardrailsModal) is SKIP/PARTIAL, the `on_guardrails_label_requested` + `on_guardrail_toggled` handler wiring on app.py is dead code (or a stub a la `a60e3fe`). Coordinate: do we still rename `ComputerInfoLabel -> GuardrailsLabel` and ship a stub button? Or keep `ComputerInfoLabel` and skip the rename? **My recommendation:** if D is SKIP, keep `ComputerInfoLabel` (no rename); if D is PARTIAL (a60e3fe stub), keep the label but the button posts a notify(). |
| **F2** | guardrails-seam | The `_disabled_rules: set[str]` set on ChatApp is a runtime-only override store that does NOT touch settings.json's `disabled_ids`. This is a NEW data store distinct from the existing `disabled_ids` mechanism. Per Terminology collision #1, decide semantics there. UI-surface impact only: the `on_guardrail_toggled` handler mutates this set. |
| **F3** | engine-seam | The `agent=agent` plumbing through `_make_options` (B work) is convenient for C (`effort_level = agent.effort`) but NOT a hard prerequisite. C can be implemented standalone with `effort_level = self._agent.effort` (read from the active agent, no per-agent options-factory routing). If B is SKIP/PARTIAL, C is still adoptable in a slightly simpler form. **My recommendation:** if B and C both adopt, take accf332's `_make_options(agent=agent)` shape; if B is SKIP and C adopts, simplify C's lookup. |
| **F4** | guardrails-seam | The renamed `DiagnosticsLabel -> InfoLabel` is part of the modal restructure and is independent of the GuardrailsModal. The renamed `ComputerInfoLabel -> GuardrailsLabel` is tied to the GuardrailsModal. Recommend the modal restructure (base.py + computer_info.py + diagnostics.py deletion + InfoLabel rename) as a separable unit from the guardrails-modal-mount. |
| **F5** | UI-surface (this axis, internal) | Our footer has a `SettingsLabel` (`settings`) that abast does NOT have. Any cherry-pick must preserve `SettingsLabel` mounting and the `on_settings_label_requested` handler at app.py:3660. accf332 reorders the footer; we must merge to keep `SettingsLabel`. **Proposed layout:** `ModelLabel . EffortLabel . PermissionModeLabel . InfoLabel . [GuardrailsLabel if D adopted] . SettingsLabel`. |
| **F6** | guardrails-seam | If D adopts the GuardrailsModal, `widgets/modals/__init__.py` needs both `GuardrailsModal` added and `DiagnosticsModal` removed. accf332 does both in one edit. If D skips and the modal-restructure adopts, only `DiagnosticsModal` is removed. |

---

## 6. Recommendations summary

| Sub-feature | Outcome | Blocking deps | One-line user delta |
|-------------|---------|---------------|---------------------|
| **C (effort cycling)** | **adapt** | none | "User sees a clickable footer label that lets them step the SDK's thinking-budget knob mid-session, with a short tooltip or rename so the meaning is self-evident on first sight." |
| **diagnostics.py deletion + computer_info.py rewrite + base.py scrollable** | **adopt** | none (independent of D) | "User sees one footer button labelled `info` instead of two; clicking it opens a single modal with system + session diagnostics in one place." |
| **Footer rename DiagnosticsLabel -> InfoLabel + handler rename** | **adopt** | (couples to deletion above) | (cosmetic relabel) |
| **Footer rename ComputerInfoLabel -> GuardrailsLabel + handler** | **defer to guardrails-seam** | depends on D outcome | (rename only meaningful if guardrails modal is also adopted) |
| **EffortLabel widget + reactive + watch** | **adapt** | none (sub of C) | (sub of C; same caveat about label-text gestalt) |

The "adapt" on C reflects the gestalt-test failure documented in 1.5
("effort: high" is jargon a first-time user cannot decode). The
adaptation is small (tooltip-on-hover OR a user-facing rename of the
on-screen text) and does NOT change abast's feature label "effort
cycling" -- only the on-screen widget text.

### 6.1 Open issues for the coordinator

1. **Pick a label-text adaptation for C.** Three options:
   (a) keep `effort: high` and add a hover tooltip explaining the knob;
   (b) rename to `thinking: high` or `quality: high`;
   (c) keep `effort: high` and accept the gestalt cost (UserAlignment
   would push back on this).
   I lean toward (a) as the smallest patch with the largest
   information gain; (b) needs UserAlignment sign-off because it
   diverges from abast's wording on-screen.
2. **C's persistence is missing.** `Agent.effort` is process-ephemeral.
   Adoption should include a follow-up to harden by writing to
   `settings.json` (or to the chicsession `workflow_state`). Not a
   blocker for first-pass adoption, but should be on the punch list.
3. **Footer ordering with our `SettingsLabel`.** Propose:
   `ModelLabel . EffortLabel . PermissionModeLabel . InfoLabel .
   [GuardrailsLabel if D adopted] . SettingsLabel`. Internal to
   UI-surface axis; no other axis input needed.
4. **Coordinate with guardrails-seam on F1, F2, F4, F6** before
   implementation begins.
5. **If we adopt C without B**, simplify the `_make_options` change to
   `effort_level = self._agent.effort` (drop the `agent=agent` parameter
   threading). Small simplification; flag for the Implementer.

### 6.4 Out-of-cluster note (per UserAlignment C3)

This axis-agent does NOT make any adopt/skip recommendation on
`003408a`. It is flagged-not-chased per the cluster scope guard.

### 6.2 Reimplement method per UI-surface unit (UserAlignment C5)

For each unit on this axis, classify how it lands on our base:

| Unit | Method | Rationale |
|------|--------|-----------|
| `EffortLabel` widget (footer.py +95) | **cherry-pick mechanical** | accf332 inserts a self-contained class; our footer.py drift is +25 lines (SettingsLabel, unrelated region). The class itself applies clean; only the `compose()` mount slot needs a one-line merge. |
| `StatusFooter.effort` reactive + `watch_effort` | **cherry-pick mechanical** | New reactive on a class we have not touched; clean apply. |
| Footer `compose()` mount of `#effort-label` | **human merge** | accf332 inserts the EffortLabel between ModelLabel and PermissionModeLabel and renames the trailing labels; our base inserts SettingsLabel after `ComputerInfoLabel`. Manual reconciliation needed (see 6.3 for the proposed layout). Trivial -- one human pass. |
| `widgets/modals/base.py` (+66) | **cherry-pick mechanical** | V2 verified zero drift on our side. Pure additive change. |
| `widgets/modals/computer_info.py` (rewrite, +68) | **cherry-pick mechanical** | V2 verified zero drift on our side. Clean rewrite; the file is replaced wholesale. |
| `widgets/modals/diagnostics.py` deletion (-194) | **cherry-pick mechanical** | Zero drift since merge-base; clean `git rm`. |
| `widgets/modals/__init__.py` exports update | **human merge** | Two distinct concerns in one edit (drop `DiagnosticsModal`, add `GuardrailsModal`); if D is deferred we only do the drop. |
| `agent.py` `self.effort = "high"` (+1 line) | **cherry-pick mechanical** | Simple addition near other instance attrs. |
| `app.py` C-related ~25-30 lines | **human merge (small)** | Three concentrated regions: import block, `_make_options` body, model-change path, and `on_effort_label_cycled` handler. Each region needs alignment with our +779 lines of independent app.py drift. Estimate 30-60 minutes of focused merge work. |
| `app.py` InfoLabel handler rename (~16 lines net) | **human merge (small)** | Replace `on_diagnostics_label_requested` body with `on_info_label_requested` body and update import line. ~10 minutes. |
| `app.py` GuardrailsLabel handler additions | **out of scope (D / guardrails-seam)** | -- |
| `styles.tcss` rules | **cherry-pick mechanical** | Zero drift; clean apply. |
| `widgets/__init__.py` + `widgets/layout/__init__.py` re-exports | **human merge (trivial)** | Add `EffortLabel` to two `__all__` lists; minor sort-order conflict possible. |
| `Agent.effort` persistence (settings.json or session save) | **reimplement from scratch** | Not in accf332 at all; the persistence smell flagged in 1.6 is a follow-up that we would design from scratch on our base (likely 1-2 lines in settings.json schema + a save hook on `EffortLabel.Cycled`). |

**Bottom line for "can we reimplement on our base?":**
- The bulk of UI-surface work is mechanical cherry-pick (clean apply).
- The genuinely human-merge regions are localised (footer `compose()`,
  app.py C and InfoLabel-rename regions, `__init__.py` exports).
- Only the persistence follow-up is reimplement-from-scratch, and it
  is optional polish.

### 6.3 Cherry-pick playbook (UI-surface portion)

If the team adopts (C + modal restructure + InfoLabel rename) and D is
deferred:

1. Take accf332's `widgets/layout/footer.py` changes for the
   `EffortLabel` class and the `StatusFooter.effort` reactive +
   `watch_effort` + footer-mount slot. Keep our `DiagnosticsLabel` /
   `ComputerInfoLabel` if D is skipped, OR rename
   `DiagnosticsLabel -> InfoLabel` and remove `ComputerInfoLabel`'s
   button label change if the modal-restructure unit is adopted but D
   skipped.
2. Take accf332's `widgets/modals/base.py` (clean add).
3. Take accf332's `widgets/modals/computer_info.py` (clean rewrite).
4. `git rm claudechic/widgets/modals/diagnostics.py`.
5. Update `widgets/modals/__init__.py`: drop `DiagnosticsModal` import
   and `__all__` entry. Add `GuardrailsModal` only if D is adopted.
6. Update `CLAUDE.md` widgets list (line 150).
7. Update `widgets/__init__.py` and `widgets/layout/__init__.py` to
   re-export `EffortLabel`.
8. Take the C-related app.py blocks: import, `on_effort_label_cycled`
   handler, `effort_level` resolution + `effort=` arg in `_make_options`
   (simplified if B is skipped), `status_footer.effort` on agent switch,
   `EffortLabel.set_available_levels` block in the model-change path.
9. Take the InfoLabel handler-rename portion of app.py: rename
   `on_diagnostics_label_requested -> on_info_label_requested`, change
   the imported modal class to `ComputerInfoModal`, pass
   `session_id=session_id` to it.
10. Add `EffortLabel:hover` rule to `styles.tcss`.
11. Add `self.effort: str = "high"` in `Agent.__init__` (line ~236).
    **Do NOT** change the `agent_type` default to `"default"` (B work).

If D is also adopted, additionally:
12. Take `widgets/modals/guardrails.py` (clean add).
13. Take the `GuardrailsLabel` rename + handler (`on_guardrails_label_requested`,
    `on_guardrail_toggled`).
14. Take `_disabled_rules` init + the `get_disabled_rules` plumbing
    line in `_guardrail_hooks`.
15. Take `guardrails/digest.py` (clean add) and `defaults/global/rules.yaml`
    (E rule).

Total UI-surface effort estimate (C + modal restructure, no D):
**1.5-2.5 hours** for an Implementer with our base context, mostly
spent on conflict resolution in the footer's `compose()` and the model
change path in `app.py`.

---

## 7. Refinements to working glossary

(Per Composability hand-off contract: refine glossary as facts come in.)

- **EffortLabel** -- click-to-cycle footer widget for the SDK
  `effort` parameter. Levels are `low | medium | high | max`; the latter
  is Opus-only. Click cycles forward; no Shift+Tab keybinding (those
  belong to permission-mode cycling).
- **Agent.effort** -- str instance attribute on `Agent` (default
  `"high"`). Per-agent, process-ephemeral, not persisted.
- **Unified Info modal** -- the renamed `ComputerInfoModal`. Shows
  System rows (Host / OS / Python / SDK / claudechic / CWD) + Session
  rows (Session JSONL path / Last Compaction, scrollable). Replaces
  the deleted `DiagnosticsModal` entirely (no info loss).
- **InfoSection.scrollable** -- new boolean field on `InfoSection`.
  When `True`, the renderer in `InfoModal.compose()` wraps the content
  in a `VerticalScroll` with a per-section copy button.

(No new collisions found beyond those already on Terminology's list.)

---

## C reframed -- agent-perspective trace (2026-04-29)

UserAlignment audited the team's framing and observed that the cluster
reads as a coherent agent-self-awareness feature set: A teaches the
agent its paths, B teaches it its role, C teaches it its compute
budget, D teaches it which rules govern it, E is concrete content for D.
This section answers: did the team read C as a footer widget when the
actual point is that the agent operates at a per-instance compute
budget?

### A.1 SDK consumer trace (does `effort` actually propagate?)

Yes. End-to-end trace for `agent.effort`:

1. **Source of truth (per-agent state):** `claudechic/agent.py` (per
   accf332 line 241): `self.effort: str = "high"` -- a string instance
   attribute on `Agent`. Per-agent, not app-global.
2. **UI write path:** `EffortLabel.on_click` posts
   `EffortLabel.Cycled(next_effort)`; `ChatApp.on_effort_label_cycled`
   in `app.py` does `agent.effort = event.effort` and
   `self.status_footer.effort = event.effort`. The Cycled event is
   the only mutation entry point (plus `set_available_levels` snapping
   on model change, which also writes through to `agent.effort`).
3. **Read path on every connect:** `ChatApp._make_options(agent=agent)`
   does `effort_level = agent.effort` (or falls back to
   `self._agent.effort`) and calls
   `ClaudeAgentOptions(..., effort=effort_level, ...)`. Every
   `agent.connect()` and `agent.reconnect()` path threads this through
   (see the call sites: `_connect_initial`, `create_unconnected -> connect`,
   `/clear` reconnect, model-change reconnect, etc.).
4. **SDK consumer (verified by reading the SDK source):**
   `claude_agent_sdk._internal.transport.subprocess_cli._build_command`
   contains, immediately after the thinking-config block:
   ```python
   if self._options.effort is not None:
       cmd.extend(["--effort", self._options.effort])
   ```
   The CLI argument `--effort <level>` is appended to the Claude Code
   subprocess argv. The Claude Code CLI propagates this to the API as
   the model's thinking-budget control (the same axis as `--thinking
   adaptive` / `--max-thinking-tokens N`, but as a discrete
   `low | medium | high | max` level).

The `effort` field is also defined on `AgentDefinition` (SDK
`types.py:98`), confirming the SDK treats effort as a per-agent compute
budget, not a global app setting.

**Verdict: C is a real agent-side budget knob.** The footer widget is
a control surface; the underlying axis is per-agent compute budget that
the model actually receives.

### A.2 Agent-side gestalt for C (per UserAlignment C8)

"Each `Agent` instance carries a thinking-budget level
(`agent.effort`), which is read on every SDK connect and passed to the
model via `--effort <level>`; mid-session changes take effect on the
next response without reconnecting because every `_make_options(agent=)`
call re-reads the live attribute. Different agents in the multi-agent
UI can run with different budgets simultaneously."

### A.3 User-side gestalt for C (unchanged from 1.6)

"The user sees a clickable label in the footer (text TBD by the
rename/tooltip decision) that lets them step the SDK's thinking-budget
knob mid-session; the next response uses the chosen level and the
level snaps to a valid range when the model changes."

### A.4 Implication for the recommendation

**Verdict on C stays at `(C effort cycling, adapt, [])`.** The
agent-side trace strengthens the *adoption* side of the case (the
feature is real and end-to-end functional, not cosmetic), but it does
NOT alter the *adaptation* trigger: the on-screen label `effort: high`
still fails the one-glance gestalt test for first-time users. The
adapt is on the user-side widget text, not the agent-side budget axis.

Two consequences from the agent-side framing:

- **Reframe C in any user-facing copy** (release notes, changelog,
  docs): C is "per-agent thinking-budget control with mid-session
  changes," not just "a footer widget." This will help users
  understand what they are clicking.
- **Persistence smell carries more weight when re-framed.** Because
  `agent.effort` is a *per-agent compute budget* the model receives,
  losing it on process restart means the agent silently reverts to
  `"high"` on next session resume even if the user had been running on
  `low` for cost reasons. The persistence follow-up is now a
  **functional gap** for cost-conscious users, not just polish.

### A.5 Diagnostics deletion / modal restructure -- agent-side framing

Agent-side gestalt: **NONE.** The diagnostics modal and the unified
Info modal are read-only viewers showing the agent's own session
JSONL path, last compaction summary, and host/Python/SDK metadata.
The agent does not consult these modals; only the human user does.
The agent's behaviour, role, budget, and rules are entirely unaffected
by this refactor. This is acceptable per UserAlignment C8 and is
stated explicitly here.

User-side gestalt (unchanged from 2.3): "The user sees one footer
button labelled `info` instead of two; clicking it opens a single
modal with system + session diagnostics in one place."

---

*End of UI-surface specification.*
