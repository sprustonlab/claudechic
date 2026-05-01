# UI-surface axis findings

**Author:** ui-surface axis-agent
**Date:** 2026-04-29
**Phase:** project-team:specification
**Scope:** sub-feature C (effort cycling) plus the structural UI changes
in `accf332` (modal-base refactor, `widgets/modals/diagnostics.py`
deletion, `widgets/modals/computer_info.py` rewrite, footer renames,
re-export updates, `styles.tcss` snippet). The activation/role-flow
handlers in `app.py` belong to engine-seam; the
`on_guardrails_label_requested` + `on_guardrail_toggled` handlers belong
to guardrails-seam. We own `on_effort_label_cycled` and
`on_info_label_requested`.

This document supersedes nothing; it accompanies and refines
`spec_ui_surface.md` (already in the artifact dir) with explicit
answers to the 6 composability questions and the per-component Skeptic
Q1-Q6 grid the coordinator asked for.

merge-base = `285b4d1`. abast cluster head = `accf332`. our HEAD =
`a2c3779`. Verification commands cited inline.

---

## Sub-feature C: effort cycling

### User-visible delta (one sentence)

Concrete user: an Opus user mid-session who wants to flip extended
thinking on (`max`) for one hard turn, or drop to `low` for a cheap
turn. Before: no UI for the SDK `effort` parameter, must edit code or
restart. After: clicking the new `effort: high` footer label cycles
through `low / medium / high / max` (the last being Opus-only) and the
next SDK call is sent with `effort=<chosen level>`.

### Contract-surface impact

| Surface | Impact |
|---------|--------|
| settings.json schema (user/project tier) | None. Effort is session-ephemeral. |
| MCP tool API | None. |
| Observer protocols | None. |
| Workflow YAML schema | None. |
| On-disk state file format | None. |
| `Agent` public attrs | +1 (`self.effort: str = "high"`). |
| `StatusFooter` public attrs | +1 (`effort = reactive("high")`). |
| Widget-level message types | +1 (`EffortLabel.Cycled(effort)`). |
| SDK call shape | One new kwarg pass-through (`ClaudeAgentOptions(effort=...)`). Verified our SDK pin (>=0.1.40) accepts it. |
| Keybindings | None. |
| Footer slot count | +1 (one new label between Model and PermissionMode). |

This is the smallest contract footprint of any sub-feature in the
cluster. Pure additive.

### Skeptic Q1-Q6 verdicts

| Q | Verdict | One-liner |
|---|---------|-----------|
| Q1 deployment doesn't apply? | NO | SDK `effort` works in our deployment context; verified Opus accepts it. |
| Q2 breaking contract w/o migration? | NO | All additions; nothing renamed or schema-bumped. |
| Q3 abast-only infra prereq? | NO | No prereq port; widget + 1 SDK kwarg. |
| Q4 one-sentence user delta? | YES (passes) | "After: footer label cycles low/med/high (max on Opus)." Concrete user above. |
| Q5 simpler in-tree change at 80%? | PARTIAL | A bare `effort` key in `~/.claudechic/config.yaml` would deliver ~50% (no per-turn, no per-model snap, no discoverability). UI delivers material additional value. |
| Q6 regresses something we rely on? | NO | No state-shape change, no keybinding, no rule. |

No "yes" answers. Not a skip candidate.

### Composability verdict, blocking deps, reasoning

**`(C effort cycling, ADOPT, [])`**

- Blocking deps: NONE.
- Self-contained on a clean axis (footer slot + agent attr + SDK kwarg +
  app handler + style rule).
- Outstanding smell: persistence is missing -- effort resets every
  process restart and is not in `settings.json` or chicsession state.
  Recommend a follow-up to harden by writing the per-agent default to
  `~/.claudechic/config.yaml`. NOT a blocker for first-pass adoption.

---

## Structural UI change: modal restructure

This unit is the four-way bundle `(diagnostics.py deletion +
computer_info.py rewrite + base.py +66 refactor + footer
DiagnosticsLabel->InfoLabel rename)`. The `ComputerInfoLabel ->
GuardrailsLabel` rename and the `widgets/modals/guardrails.py` add
**are NOT in this unit** -- they're guardrails-seam, gated on D.

### What changes for the user

Concrete user: a developer debugging a session who wants to see the
last `/compactish` summary AND check Python/SDK versions. Before: two
footer buttons (`session_info` -> DiagnosticsModal, `sys` ->
ComputerInfoModal), two modals, two stops. After: one footer button
(`info` -> unified ComputerInfoModal), one modal showing
Host / OS / Python / SDK / claudechic / CWD plus Session JSONL path
plus Last Compaction (the last in a scrollable section). Information
loss is exactly zero (verified by reading the rewritten
`computer_info.py` against the deleted `diagnostics.py`); information
gain is small (one less modal, one less footer slot, freed space for
the future GuardrailsLabel if D adopts).

### Skeptic Q1-Q6 verdicts

| Q | Verdict | One-liner |
|---|---------|-----------|
| Q1 deployment doesn't apply? | NO | We use both modals today; consolidation cleans the footer for us as much as for abast. |
| Q2 breaking contract w/o migration? | PARTIAL | `DiagnosticsModal` is removed from `widgets/modals/__init__.py` `__all__`. Public API for downstream importers (none we know of). One internal app.py handler renamed (`on_diagnostics_label_requested -> on_info_label_requested`). Migration is mechanical (4 ref sites total, see Q4 inventory below). |
| Q3 abast-only infra prereq? | NO | All additions are stdlib + textual primitives we already use. |
| Q4 one-sentence user delta? | YES (passes) | "Before: two buttons, two modals. After: one button, one modal, scrollable compaction." |
| Q5 simpler in-tree change at 80%? | NO | The simpler path (keep two modals, add scrollable section to base.py only) doesn't free the footer slot or reduce modal count. The whole point is the consolidation. |
| Q6 regresses something we rely on? | NO | All Diagnostics content survives in the unified modal. Tests pass after the 4-site mechanical fix. |

No blocking "yes" answers.

### Composability verdict, blocking deps, reasoning

**`(modal restructure: base.py refactor + computer_info.py rewrite + diagnostics.py deletion + DiagnosticsLabel->InfoLabel rename + on_info_label_requested handler, ADOPT, [])`**

- Blocking deps: NONE.
- **Independent of D's outcome.** Even if guardrails-modal/footer
  rename is skipped, this unit stands on its own as a refactor.
- The 4-component bundle (base.py / computer_info.py / diagnostics.py
  delete / footer label rename) IS internally indivisible (see Q2
  cross-cutting below): they all reference each other, and decoupling
  any one creates dead code or a broken reference.

---

## Cross-cutting findings

### Q1. Effort-cycling self-containment

**Question:** does `EffortLabel` know the model via clean injection or
hardcoded family branches? What does the effort value DO? Could we
cherry-pick effort-cycling alone?

**Evidence (read of accf332's `widgets/layout/footer.py` and
`app.py` diff):**

- Model is injected via `EffortLabel.set_available_levels(levels)`
  called from `app.py`'s model-change path. The label itself does NOT
  reach into the active agent for the model name. The
  `EffortLabel.MODEL_EFFORT_LEVELS` dict (`{"haiku": ..., "sonnet": ...,
  "opus": ...}`) and the `levels_for_model(model)` classmethod live on
  the widget for convenience, but the widget's `__init__` and
  `on_click` do not hardcode any family. **Verdict: clean injection.**
  The family branches are a static lookup table consumed by the
  app-side model-change handler, not by the widget's runtime cycling.
- Effort is wired to the SDK via
  `ClaudeAgentOptions(effort=effort_level, ...)` in
  `_make_options`. `effort_level` is resolved from
  `agent.effort` (or `self._agent.effort`). Verified our SDK pin
  (`claude-agent-sdk>=0.1.40`) accepts the kwarg by inspecting
  `ClaudeAgentOptions.__init__` signature. **Verdict: actually wired.**
  Not a no-op widget.
- Cherry-pick test: C is genuinely composable in isolation. The only
  shared file with B is `app.py` (and the `agent=` parameter that
  `_make_options` gains is a B convenience -- C can resolve via
  `self._agent.effort` directly without it). The footer slot insert and
  the model-change snap-back block are both C-local.
- **Seam test passes.** Effort-cycling IS self-contained.

### Q2. Modal restructure: indivisible or composable?

**Question:** is the modal restructure ONE indivisible refactor, or
could we adopt only some of (a) base.py, (b) computer_info.py rewrite,
(c) diagnostics.py deletion?

**Evidence:**

- (b) computer_info.py rewrite uses `InfoSection(scrollable=True)` --
  the new field added by (a). **(b) requires (a).**
- (b) absorbs the entire content of diagnostics.py
  (`_read_last_compact_summary`, JSONL path resolution, Last Compaction
  section with `scrollable=True`). If we adopt (b) without (c),
  diagnostics.py becomes dead code AND the footer still has both
  `session_info` and `sys` buttons but the `sys` button now opens a
  modal that contains everything `session_info` shows. **Adopting (b)
  without (c) is technically possible but ugly.**
- (a) base.py +66 alone is genuinely independent -- it adds optional
  `scrollable` to InfoSection. Backward-compatible: existing
  ComputerInfoModal sections without `scrollable=True` render
  identically. **(a) is adoptable alone.**
- The footer label rename (DiagnosticsLabel -> InfoLabel) and the
  `on_info_label_requested` handler are coupled to (c): they reference
  the deleted button and the new unified modal.

**Composability verdict:** the bundle is NOT a single indivisible
refactor. The clean cleavage is:
- (a) base.py +66 -- adoptable alone (useful for future modals).
- (a)+(b)+(c)+footer-rename+handler-rename -- the meaningful
  user-visible unit. Adoptable as one.
- Adopting subsets (e.g. (a)+(b) without (c)) creates dead
  code -- not recommended but not breaking.

The historian's V2 finding (zero drift on `computer_info.py` and
`base.py` since merge-base) means the swap is mechanical for (a)+(b).
The diagnostics.py deletion is also mechanical (we have not edited it
either; verified via `git log --oneline 285b4d1..HEAD --
claudechic/widgets/modals/diagnostics.py` -> empty).

### Q3. Footer button-slot repurposing

**Question:** is the slot rename clean or a footgun? If we adopt only
C (effort) but not D (guardrails UI), what does GuardrailsLabel do?

**Evidence (read of accf332's `widgets/layout/footer.py:compose()` and
`a60e3fe`):**

abast's accf332 footer composes:
```
Model · Effort · PermissionMode · Info · Guardrails
```
- `Info` is the renamed DiagnosticsLabel. It opens the unified
  ComputerInfoModal. Clean repurpose: same widget class machinery, new
  name and target.
- `Guardrails` is the renamed ComputerInfoLabel. Originally opened
  ComputerInfoModal; in accf332 it opens GuardrailsModal. **`a60e3fe`
  then walks the handler back to a `notify("not yet implemented")`
  stub** -- so on `abast/main`, the `Guardrails` button ships as a
  no-op toast.

**The footgun:** if our team adopts C + modal restructure (the InfoLabel
side) but skips D, the `GuardrailsLabel` rename is dead-code: the
widget, the styles entry, and the slot exist but the handler is
either missing or a stub. The user sees a button that does nothing.

**Composability resolution -- footer slots as independent units:**
the footer's compositional law is "one label widget = one independent
click slot". We respect that law by treating each rename as its own
unit:

| Slot rename | Owner axis | Adoption gate |
|-------------|-----------|---------------|
| DiagnosticsLabel -> InfoLabel + new handler | UI-surface (this axis) | adopt with modal restructure |
| ComputerInfoLabel -> GuardrailsLabel + new handler | guardrails-seam | adopt only if D adopts |

If D skips entirely: keep `ComputerInfoLabel` slot (do NOT rename to
`GuardrailsLabel`). The user sees `Model · Effort · PermissionMode ·
Info · Sys · Settings`, where `Sys` opens... well, a strict reading
would have it open ComputerInfoModal. But the new ComputerInfoModal
already shows everything `Sys` used to plus the diagnostics content,
so `Sys` becomes redundant with `Info`.

**Recommendation if D skips:** drop the `Sys` slot entirely (delete
`ComputerInfoLabel` mounting AND its handler), keep only the renamed
`Info` slot. The footer becomes:
```
Model · Effort · PermissionMode · Info · Settings
```
This is also the cleanest end-state per F5 in `spec_ui_surface.md`
(SettingsLabel is OUR addition that abast doesn't have; we MUST
preserve it through any cherry-pick).

**Recommendation if D adopts (full modal):**
```
Model · Effort · PermissionMode · Info · Guardrails · Settings
```

**Recommendation if D adopts only the `a60e3fe` stub:** same layout
but Guardrails toasts "not yet implemented" -- a regression vs. our
current `Sys` button which does something useful. This is the
deliberate intent signal Leadership flagged; the team decides.

### Q4. diagnostics.py deletion blast inventory on our base

Grep against our HEAD for `DiagnosticsModal | DiagnosticsLabel`:

| Site | Lines | Classification |
|------|-------|---------------|
| `claudechic/widgets/modals/diagnostics.py` | whole file | (a) deleted as the unit |
| `claudechic/widgets/modals/__init__.py` | line 5 (import), line 12 (`__all__`) | (a) drop both lines |
| `claudechic/widgets/layout/footer.py` | lines 17-24 (class), line 192 (mount) | (a) replaced by InfoLabel mount |
| `claudechic/styles.tcss` | line 88 (`DiagnosticsLabel:hover`) | (a) replaced by `EffortLabel/InfoLabel/GuardrailsLabel:hover` per accf332's tcss diff |
| `claudechic/app.py` | line 117 (import `DiagnosticsLabel`), line 3641-3648 (handler `on_diagnostics_label_requested`) | (b) handler renamed to `on_info_label_requested`, modal class swapped to `ComputerInfoModal(cwd, session_id=...)` |
| `tests/test_widgets.py` | line 971-1003 (`test_sys_label_click_opens_computer_info_modal`) | (b) test still works -- it imports `ComputerInfoLabel` and pushes `ComputerInfoModal(cwd="/tmp")`. After the rename, this test references a DELETED label. Migration: rewrite to use `InfoLabel` and `ComputerInfoModal(cwd, session_id=...)`. |
| `CLAUDE.md` | line 150 | (a) remove diagnostics.py line; abast's commit 3 (`2f6ba2e`) handles this but our CLAUDE.md has drift; the editor must merge. |

No `DiagnosticsModal` references in tests, no keybinding, no
`/diagnostics` slash command, no remote-test endpoint that opens it.

**Classification summary:** 5 sites are class (a) safe-clean-deletion;
2 sites are class (b) mechanical-fix-with-rename. Zero sites are
class (c) feature-loss. The deletion is safe.

The historian's V2 finding (zero drift on diagnostics.py) means the
file itself is byte-for-byte the merge-base version, so the deletion
is a pure `git rm`.

### Q5. modal/base.py refactor as a new compositional law

**Question:** is base.py +66 a new abstraction that other modals should
also use? Does it create a "law" for modals?

**Evidence (read of accf332's `widgets/modals/base.py`):**

The +66 adds:
1. `InfoSection.scrollable: bool = False` (1 line on the dataclass).
2. A render branch in `InfoModal.compose()` that, when
   `scrollable=True`, wraps content in a `VerticalScroll` with a
   per-section copy button.
3. `_copy_to_clipboard(text)` factored out of `_copy_all` so the
   per-section copy button can call it.

This is a backward-compatible enhancement, not a new abstraction layer.
Existing modals that subclass `InfoModal` (just `ComputerInfoModal` on
our base) work unchanged because `scrollable` defaults to `False`.

**Does it become a "law" for modals?** Mildly. Any future modal that
wants a labeled-info layout with a scrollable text panel can subclass
`InfoModal` and pass `InfoSection(scrollable=True)`. The interface is
shallow: 1 dataclass field + 1 render branch. There is no
"all info-style modals MUST use scrollable sections" obligation; it's
opt-in.

**Modals on our base that could BENEFIT from this:**
- `ComputerInfoModal` -- yes, that's the whole point. Adopts here.
- `ProcessModal`, `ProcessDetailModal` -- they have their own custom
  layout (table-like). Not labeled-info. No benefit.
- `ProfileModal` -- profiling stats, custom layout. No benefit.
- `AgentSwitcher` -- modal but interactive (search box). No benefit.
- `DiagnosticsModal` (going away) -- the JSONL path + scrollable
  compaction section IS the canonical use case. Already absorbed.

**Verdict:** the refactor is genuinely useful for the absorbed-
diagnostics view; future modals can opt in. It does NOT create a
binding new law. ADOPT as part of the modal-restructure unit.

### Q6. Effort vs permission-mode cycling collision

**Question:** is there a real keybinding collision between effort
cycling and permission-mode cycling on Shift+Tab?

**Evidence (read of accf332's `widgets/layout/footer.py:EffortLabel`
and `EffortLabel.on_click`; grep for `Shift+Tab` bindings):**

- `EffortLabel` has NO keybinding. Cycling is purely click-driven
  (`on_click` -> advance `self._effort` to next in `self._levels` ->
  post `EffortLabel.Cycled`).
- `PermissionModeLabel` has BOTH a click handler AND a Shift+Tab
  keybinding (the keybinding is on `ChatScreen`, not on the label
  itself; the label posts the same `Toggled` message).
- accf332 introduces no new keybinding.

**Verdict: NO real collision.** Mild gestural overlap (both are
click-cycle footer labels) is harmless because the label texts are
visually distinct (`effort: high` vs. `Auto-edit: off` /
`Plan mode` / etc.) and cycling is local to each label. A power user
who tries Shift+Tab expecting effort to cycle gets the existing
permission-mode behaviour -- mildly surprising but not broken.

Terminology's collision-risk LOW flag holds.

---

## Terminology refinements

### What name should the merged modal have?

**Pinned name:** `ComputerInfoModal` (the class) with footer label
`info`. abast renames the FOOTER LABEL `DiagnosticsLabel ->
InfoLabel`, but the modal CLASS remains `ComputerInfoModal`. We adopt
both names as-is.

Alternative `InfoModal` (the base class) is already taken on our base
by `widgets/modals/base.py:InfoModal`. Calling the merged modal
`InfoModal` would shadow the base class.

`DiagnosticsModal` is dead.

Recommend a CLAUDE.md/file-map line update: "`computer_info.py` --
ComputerInfoModal: system info + session diagnostics (info button)".

### What's the right label for the footer slot when its action is stubbed?

If `a60e3fe` stub is adopted (D PARTIAL), the slot is labelled
`guardrails` and clicking notifies "not yet implemented." This is a
regression vs. our current `Sys` button (which DOES do something).

**Recommendation:** if D PARTIAL/SKIP, do NOT rename
`ComputerInfoLabel -> GuardrailsLabel`. Either keep `Sys` (and the
ComputerInfoModal mount) or drop the slot entirely (since the new
`Info` modal already shows the system info). Do not ship a stub label
that has been stubbed out by abast themselves.

### Other refinements

- **EffortLabel** -- click-to-cycle widget for the SDK `effort`
  parameter. Levels: `low | medium | high | max` (`max` Opus-only).
  Click cycles forward; no Shift+Tab keybinding.
- **Agent.effort** -- str instance attribute on Agent (default `high`).
  Per-agent, process-ephemeral, NOT persisted.
- **Unified Info modal** -- the renamed footer slot opens
  `ComputerInfoModal` (class name unchanged). Shows System rows + Session
  rows; the Last Compaction row uses `scrollable=True`.
- **InfoSection.scrollable** -- new opt-in boolean on `InfoSection`
  dataclass. Enables `VerticalScroll` wrapping in `InfoModal.compose()`.

---

## New collisions discovered

None beyond what Terminology already flagged. Specifically:

- The `InfoModal` base-class name vs. an `InfoModal`-named modal slot
  is NOT a collision because abast keeps the modal class name
  `ComputerInfoModal`. Only the footer LABEL is renamed to `info`.
- No new state-location collision (effort doesn't write to disk).
- No new substitution-syntax collision (effort doesn't use templates).
- The `EffortLabel.MODEL_EFFORT_LEVELS` dict family-name keys
  (`opus`, `sonnet`, `haiku`) are looked up by substring against the
  full model string -- benign and consistent with how
  `PromptCachingChatModel` and other parts of our base disambiguate
  models.

---

## Per-component recommendation summary

| Component | Outcome | Blocking deps | One-line reason |
|-----------|---------|--------------|-----------------|
| C: effort cycling | **ADOPT** | none | Smallest contract surface in the cluster; clean injection of model awareness; SDK kwarg verified on our pin. |
| modal-base.py refactor (+66) | **ADOPT** | none (independently useful) | Backward-compatible scrollable opt-in; mild new compositional pattern, not a binding law. |
| diagnostics.py deletion | **ADOPT** | computer_info.py rewrite | Zero info loss (verified); 5 sites class (a), 2 sites class (b); historian V2 confirms clean delete. |
| computer_info.py rewrite | **ADOPT** | base.py refactor | Absorbs all diagnostics content; clean rewrite (zero drift on our side). |
| footer DiagnosticsLabel -> InfoLabel rename + handler | **ADOPT** | computer_info rewrite + diagnostics deletion | Bundle-internal -- ships together. |
| footer ComputerInfoLabel -> GuardrailsLabel rename + handler | **DEFER to guardrails-seam (gated on D)** | D outcome | If D SKIP, do NOT rename; either drop ComputerInfoLabel slot or keep it. |
| widgets/__init__.py + widgets/layout/__init__.py re-exports | **ADOPT** | EffortLabel adoption | `+EffortLabel` (1-line each `__all__` + 1-line each import). |
| widgets/modals/__init__.py re-exports | **PARTIAL ADOPT** | depends on D | Drop `DiagnosticsModal` always; add `GuardrailsModal` only if D adopts. |
| styles.tcss snippet | **ADOPT** (with conditional) | mirrors footer renames | Drop `DiagnosticsLabel:hover`; add `EffortLabel:hover`; add `InfoLabel:hover`; add `GuardrailsLabel:hover` only if D adopts. |

### Cherry-pick playbook (UI-surface portion only) -- D deferred

1. Take `widgets/layout/footer.py` `EffortLabel` class verbatim from
   accf332.
2. In our `footer.py`, rename `DiagnosticsLabel` -> `InfoLabel`
   (rename class + label widget id `diagnostics-label` -> `info-label`
   + the displayed text `session_info` -> `info`). Leave SettingsLabel
   intact. If D skips, leave ComputerInfoLabel as-is; if also adopting
   the cleaner end-state, delete ComputerInfoLabel.
3. Update `StatusFooter`: add `effort = reactive("high")` reactive,
   add `watch_effort`, insert `EffortLabel(...)` in `compose()`
   between Model and PermissionMode.
4. Take `widgets/modals/base.py` from accf332 (clean overwrite -- zero
   drift on our side per V2).
5. Take `widgets/modals/computer_info.py` from accf332 (clean
   overwrite -- zero drift on our side per V2).
6. `git rm claudechic/widgets/modals/diagnostics.py`.
7. Update `widgets/modals/__init__.py`: drop `DiagnosticsModal` import
   + `__all__` entry. Do NOT add `GuardrailsModal` (D skipped).
8. Update `widgets/__init__.py` and `widgets/layout/__init__.py` to
   re-export `EffortLabel`.
9. Update `styles.tcss`: replace `DiagnosticsLabel:hover` with
   `EffortLabel:hover` and `InfoLabel:hover`. Do NOT add
   `GuardrailsLabel:hover` (D skipped).
10. Add `self.effort: str = "high"` to `Agent.__init__` (line ~236).
11. Take the C-related `app.py` blocks (~25-30 lines):
    - Import `EffortLabel, InfoLabel` (replacing `DiagnosticsLabel,
      ComputerInfoLabel` if D skipped).
    - `on_effort_label_cycled` handler (~7 lines).
    - `on_info_label_requested` handler (~8 lines, replacing
      `on_diagnostics_label_requested`).
    - `effort_level` resolution + `effort=effort_level` kwarg in
      `_make_options` (~6 lines). If B is also skipped/adapted, simplify
      to `effort_level = self._agent.effort` (drop the `agent=` param
      threading -- that's a B convenience).
    - `status_footer.effort = new_agent.effort` on agent switch
      (~1 line).
    - `EffortLabel.set_available_levels` snap-back block in the
      model-change path (~10 lines).
12. Update `tests/test_widgets.py` `test_sys_label_click_opens_computer_info_modal`
    to use `InfoLabel` instead of `ComputerInfoLabel` and pass
    `session_id=...` to `ComputerInfoModal`.
13. Update `CLAUDE.md` line 150 to drop the diagnostics.py entry.

Total UI-surface effort if D deferred: **1.5-2.5h**.

If D ALSO adopts (full modal), additionally take from accf332:
- `widgets/modals/guardrails.py` (clean add).
- `widgets/layout/footer.py` `GuardrailsLabel` class + slot mount.
- `app.py` `_disabled_rules` init, `get_disabled_rules` plumbing,
  `on_guardrails_label_requested` handler, `on_guardrail_toggled`
  handler.
- `widgets/modals/__init__.py` `+GuardrailsModal` re-export.
- `styles.tcss` `GuardrailsLabel:hover` snippet.

These are guardrails-seam responsibilities; we coordinate the wiring
but don't own the data side.

---

*End of UI-surface specification.*
