# Guardrails-seam Specification -- abast accf332 cluster

**Author:** guardrails_seam axis-agent
**Date:** 2026-04-29
**Phase:** Specification
**Scope:** Sub-feature **D guardrails UI** (in-cluster, abast's exact label) + sub-feature **E `pytest_needs_timeout` warn rule** (stowaway -- discovered by team, not named in the user prompt) + the architectural seam B (`claudechic/guardrails/`, `claudechic/checks/`, `claudechic/mcp.py`).

Out of scope (covered by other axis-agents): **A workflow template variables** + **B dynamic roles** (engine-seam); **C effort cycling** and the `diagnostics.py` deletion / `computer_info`+`base.py` modal restructure (UI-surface).

`003408a` is OUT-OF-CLUSTER per the user's scope guard ("stay strictly inside the 4-commit cluster; flag, don't chase"). It is surfaced ONLY in section 6 ("Flagged context") and is NOT recommended adopt/skip on this axis.

---

## TL;DR

| Sub-feature (abast label) | Type | Outcome | Blocking deps | Gestalt: "after this lands, the user sees..." |
|---------------------------|------|---------|---------------|-----------------------------------------------|
| **D guardrails UI** -- modal | named in user prompt | **skip** | -- | (no change) -- abast themselves stubbed it (`a60e3fe`); the modal+digest are dead code on `abast/main`. Picking it up rebuilds our own `app.py` wiring to expose code the upstream author flagged "not ready". Q4 fails (no concrete user). |
| **D guardrails UI** -- data layer (`digest.py` only) | named in user prompt (sub-half) | **skip / defer** | -- | (no change) -- clean leaf module, but no consumer. If a future user asks "what rules apply right now?", reimplement as a `/guardrails` slash command (~30 LOC). Q4/Q5 fail today. |
| **E `pytest_needs_timeout`** | **stowaway -- discovered by team** | **adopt** | none (data-only YAML record) | the agent runs `pytest tests/foo.py` without `--timeout=` and gets a warn-level block telling it to add `--timeout=N` (or `acknowledge_warning(...)` if it has a reason). Concrete user: anyone running `pytest` from an agent who has been bitten by a hung test. |

A note on the framing: **the question "adopt the GuardrailsModal UI" is the wrong question.** D decomposes into a clean data/UI seam, and the upstream author already split it for us by stubbing only the UI half. So the live question is: do we want the `digest.py` data layer? Answer: not yet -- without a UI consumer, it's dead code on our side too.

---

## 1. Source inspection

### 1.1 `accf332` -- what D actually adds (B-layer + UI)

Five files involved in feature D specifically:

| File | Layer | Add/Mod | Lines | Role |
|------|-------|---------|-------|------|
| `claudechic/guardrails/digest.py` | data (B) | new | +128 | Pure function `compute_digest(loader, active_wf, agent_role, current_phase, disabled_rules) -> list[GuardrailEntry]`. Imports only from `guardrails.rules`. Returns frozen dataclasses. No UI dependencies. |
| `claudechic/widgets/modals/guardrails.py` | UI (C, but pulls B types via `TYPE_CHECKING`) | new | +186 | `GuardrailsModal(ModalScreen)` listing entries with checkboxes; emits `GuardrailToggled(rule_id, enabled)` messages. |
| `claudechic/widgets/layout/footer.py` | UI (C) | mod | +121 | Renames `DiagnosticsLabel -> InfoLabel`, `ComputerInfoLabel -> GuardrailsLabel`. Repurposes the buttons. |
| `claudechic/app.py` | wiring | mod | substantial | (1) Adds `_disabled_rules: set[str]` instance attr. (2) Plumbs `get_disabled_rules` callback into `_guardrail_hooks(...)` -> `create_guardrail_hooks(...)`. (3) Adds `on_guardrails_label_requested` handler that imports `compute_digest` + `GuardrailsModal`, builds entries, pushes the modal. (4) Adds `on_guardrail_toggled` handler that mutates `_disabled_rules`. (5) Renames `on_diagnostics_label_requested -> on_info_label_requested` and rewires it to `ComputerInfoModal` (this is UI-surface axis territory). |
| `claudechic/defaults/global/rules.yaml` | data | mod | +7 | Adds `pytest_needs_timeout` warn rule. **This is sub-feature E**, included in the same commit as D but separable. |

### 1.2 `a60e3fe` -- the walk-back (single file, single function)

Inspected `git show a60e3fe`: it touches **only** `claudechic/app.py`, replaces both `on_guardrails_label_requested` AND `on_guardrail_toggled` with one stub:

```python
def on_guardrails_label_requested(self, event):
    self.notify("Guardrails viewer not yet implemented", severity="information")
```

The commit message is one line: `chore: stub out guardrails modal with not-yet-implemented notice`. No further explanation.

The two supporting files -- `claudechic/guardrails/digest.py` and `claudechic/widgets/modals/guardrails.py` -- are NOT touched. The `_disabled_rules` instance attr stays. The `get_disabled_rules` callback wiring into `create_guardrail_hooks` stays. The `GuardrailsLabel` footer button stays (still says "guardrails", still posts `Requested`).

So on abast HEAD the runtime state is:
- Click "guardrails" -> toast says "not yet implemented".
- The data-layer `compute_digest()` is importable but has no caller.
- The modal class `GuardrailsModal` is importable but never pushed.
- The `_disabled_rules` set is initialized to empty and the hook honors it -- but no UI ever mutates it. So it's effectively dormant: the runtime-disable mechanism exists end-to-end, but there's no way to flip it from the UI.

This is **the cluster's clearest intent signal.** abast shipped the plumbing, then immediately gated the user-visible surface behind a stub. Three plausible readings:

(a) **The modal had a UX bug (most likely).** The diff shows the checkbox layout (`_GuardrailRow`) packs `Checkbox`, `Static(badge)`, `Static(id)`, `Static(reason)` into a 1-row Horizontal. `Checkbox.BUTTON_INNER = " "` is monkey-patched on each row -- a hack. The `gr-cb-{e.id}` ID scheme assumes rule IDs are valid CSS selectors (they may not be: e.g. `project-team:pip_block` contains `:`). 20 minutes between accf332 and a60e3fe is consistent with "open the modal once, see it look bad or crash, stub it for the demo".

(b) **The modal worked but the checkbox semantics were undecided.** `_disabled_rules` is in-memory only -- nothing writes it back to `disabled_ids` in config, nothing reads from there. So "toggle a rule off" survives until next restart. Was that the intended semantics or a placeholder? If undecided, stubbing the user-facing button preserves the option.

(c) **Time pressure / staging the rollout.** This is cluster commit #4 of 4, 20 minutes after #1. abast may have wanted to land the data plumbing in this batch and the UX in the next.

I cannot distinguish (a) from (b)/(c) without an upstream conversation. But the conservative read for our team is: **abast is not running this UI in production. We should not be the canary.**

### 1.3 Our base -- pre-existing surface

Confirmed by file reads:

- `claudechic/guardrails/`: has `__init__.py`, `hits.py`, `hooks.py`, `parsers.py`, `rules.py`, `tokens.py`. **Missing `digest.py`** (introduced by accf332 -- clean addition, no collision).
- `claudechic/guardrails/hooks.py`: 184 lines, two-step pipeline (injections then enforcement), with `consume_override`, `get_phase`, `get_active_wf`, `agent_role` callbacks. **No `get_disabled_rules` callback** (introduced by accf332). **No "vast majority of cases" reasoning text in the warn-rule reason** (introduced by `003408a`).
- `claudechic/checks/builtins.py`: 199 lines. `CommandOutputCheck` does NOT have a `cwd` ctor param. `FileExistsCheck`/`FileContentCheck` do NOT have `base_dir`. We DO have an extra check type that abast does not -- `ArtifactDirReadyCheck` -- introduced by Group E. So our `_CHECK_REGISTRY` has 5 entries, abast's has 4; both register their own subset.
- `claudechic/mcp.py`: 100+ lines, has `_app: ChatApp | None`, `set_app`, etc. No `_get_workflows_dir` / `_get_workflow_variables` helpers (engine-seam relevant). The `spawn_agent type=` path uses `agent_type = args.get("type")` (i.e. `None` if missing) -- not the `DEFAULT_ROLE` sentinel.
- `claudechic/defaults/global/rules.yaml`: 4 rules (`no_rm_rf`, `warn_sudo`, `log_git_operations`, `no_bare_pytest`). Trailing blank line at line 32. **No `pytest_needs_timeout`. No `no_pip_install`** (which IS in abast's pre-accf332 file).
- `claudechic/widgets/modals/diagnostics.py`: 194 lines, still present on our HEAD (UI-surface axis owns the deletion call).
- `claudechic/widgets/layout/footer.py`: still has `DiagnosticsLabel` + `ComputerInfoLabel`; no `InfoLabel`/`GuardrailsLabel`/`EffortLabel`.
- `claudechic/app.py`: has `_token_store`, `_workflow_engine`, `on_diagnostics_label_requested`, `on_computer_info_label_requested`. No `_disabled_rules`. The current `_guardrail_hooks(self, agent_role=None)` signature has only the static role path; no `agent=` parameter, no dynamic role resolution.

Drift summary on the B layer specifically (not counting `app.py`):
- `claudechic/guardrails/`: 0 collisions for the `digest.py` addition. 1 mod in `hooks.py` if D is adopted (the `get_disabled_rules` plumbing).
- `claudechic/checks/`: no in-cluster changes; engine-seam owns any check-layer changes that ride with sub-feature A.
- `claudechic/mcp.py`: no in-cluster changes touching the guardrail layer specifically; engine-seam owns the in-cluster `mcp.py` work for sub-feature A (template variables) and B (dynamic roles).
- `claudechic/defaults/global/rules.yaml`: text mechanical -- the patch context references `no_pip_install` which we don't have, so the cherry-pick will fail context match and require a manual append.

---

## 2. Composability analysis

### 2.1 Domain understanding

The guardrails system is the always-active enforcement axis: every tool call passes through `PreToolUse` hooks that evaluate `Rule` and `Injection` records loaded from manifests. The system has a clear seam already (per `claudechic_guardrails-system.md`):

```
User prefs (config: disabled_ids)
        |
Manifest YAML --> ManifestLoader --> LoadResult{rules, injections}
                                              |
                                              v
                                  create_guardrail_hooks(loader, hit_logger,
                                                          agent_role, get_phase,
                                                          get_active_wf,
                                                          consume_override)
                                              |
                                              v
                                  HookMatcher closure
                                              |
                                              v   evaluated on every tool call
                                  Rule trigger/role/phase/exclude/detect filter
                                              |
                                              v
                                  Decision: allow | block(warn/deny) | log | inject
```

What sub-feature D adds is not enforcement logic -- it's an **introspection axis**: a way to ask "what rules apply here, and why don't the others?", and a runtime override knob (`disabled_rules`) that the user can flip from the UI.

### 2.2 Axes I see

The guardrails system, post-D, factors into:

1. **Rule provenance axis** (where the rule comes from): package | user | project, namespace `global` | `<workflow_id>`. Already orthogonal in our `ManifestLoader` 3-tier loader; D does not touch this.
2. **Rule kind axis**: `rule` | `injection`. Already split in our pipeline (two-step). D's `digest.py` reads both.
3. **Enforcement axis**: `deny` | `warn` | `log` (rules) + `inject` (injections). Already orthogonal; D's `digest.py` carries `enforcement` straight through.
4. **Scope axis**: phase x role x workflow-active. Already orthogonal in `should_skip_for_phase` / `should_skip_for_role` / namespace check. D's `digest.py` re-evaluates these to label entries `active` vs `skip_reason="..."`.
5. **Lifecycle axis (NEW with D)**: `enabled` | `runtime-disabled`. The new bit `_disabled_rules: set[str]` on the app. This is what the modal toggles. Currently lives only in memory; not persisted.
6. **Surface axis**: enforcement (hook) | introspection (digest) | UI (modal). **D establishes this third surface.**

The **introspection layer** (`digest.py`) is a very clean leaf: it only imports from `guardrails.rules` and uses the public `should_skip_for_role`/`should_skip_for_phase` helpers. No UI imports. No `mcp.py` imports. It's the kind of leaf we should welcome **if we want an introspection axis at all**.

### 2.3 Are data and UI cleanly separable?

**Yes -- sharply.** Evidence from inspecting the code:

| Direction | Imports |
|-----------|---------|
| `digest.py` -> | `guardrails.rules` (sibling), `dataclasses`, `typing`. **No UI imports.** |
| `widgets/modals/guardrails.py` -> | `textual.*`, `dataclasses`, and `guardrails.digest.GuardrailEntry` under `TYPE_CHECKING`. **The TYPE_CHECKING import is the only B-layer reference, and it is type-only.** At runtime the modal accepts `entries: list[GuardrailEntry]` from the caller; it never imports `compute_digest` itself. |
| `app.py` (data plumbing) -> | adds `_disabled_rules` attr; adds `get_disabled_rules` callback into `create_guardrail_hooks`. This is data wiring. |
| `app.py` (UI wiring) -> | imports `GuardrailsModal`, `GuardrailToggled`, `compute_digest` from inside the handler. Lazy import. |

The seam between D-data and D-UI is **clean**: bytes (well, `GuardrailEntry` instances) cross; assumptions don't. The data half is portable; the UI half is the consumer.

That clean seam is exactly why abast was able to stub `a60e3fe` so cleanly -- they ripped out the UI entry-point handler in 8 lines, with no need to touch `digest.py` or `GuardrailsModal`. The author's own surgery is evidence that the seam is real.

So the answer to question 1 of the brief: **the data side and UI side are cleanly separable**, and you can adopt either independently:
- Adopt data side only: import `compute_digest` from a slash command (`/guardrails`) that prints to chat; skip the modal entirely.
- Adopt UI side only: doesn't make sense (modal needs entries from somewhere).
- Adopt both: full feature.
- Adopt neither: status quo.

Note that the **runtime-disable plumbing** (`_disabled_rules` set + `get_disabled_rules` callback into hooks) is **not** the same as either of those:

- It's a new bit on the rule lifecycle.
- It only delivers value when something writes to it.
- The data layer (`digest.py`) reads from it (to label entries `active=False, skip_reason="disabled by user"`) -- but reading is read-only.
- The hook layer (`hooks.py` change in accf332) reads from it (to skip evaluation entirely).
- The UI layer (modal) writes to it (via the `GuardrailToggled` message handler).

If you adopt the data layer without the UI, the runtime-disable plumbing is dead weight (it's wired through but nothing flips it).

### 2.4 Crystal holes I foresee

Three potential holes:

(a) **Toggle persistence vs `disabled_ids` config.** Terminology already flagged this as a 5th meaning of "guardrails". The accf332 modal writes to `_disabled_rules: set[str]` in memory; our config layer has `disabled_ids: frozenset[str]` on disk. These two should be one or the other:
- **Option 1: collapse them.** Toggle in modal = write to `disabled_ids` and update the config file. This persists across sessions. Crystal closes.
- **Option 2: keep them distinct.** `disabled_ids` is the explicit config-managed list; `_disabled_rules` is a session-scoped runtime override. Both are read by hooks (additively). Document the distinction. Crystal closes if documented; otherwise this is a hole.
- abast's accf332 does neither -- it's silent on the relationship. That's a hole.

(b) **Hint coverage.** Terminology asked: "Does the modal cover hints too, or only guardrails?" Source inspection: `digest.py` enumerates `result.rules` + `result.injections`. **It does NOT enumerate hints.** So the answer is: only guardrails (i.e. `Rule` + `Injection`). Hints are a separate axis with their own state store (`HintStateStore` -> `.claudechic/hints_state.json`). If we adopt D, the modal label "guardrails" is honest, but it's a partial view of the safety/advisory surface. This is consistent with our settings pattern (separate `disabled_ids` covers both) -- but a user looking at "guardrails" for a missing hint would be confused. Note for the final report.

(c) **Workflow-dependent scoping crosstalk.** `digest.py` takes `active_wf`, `agent_role`, `current_phase` as parameters and asks the rule "would you fire here?" -- but for the **calling** agent's context. The modal shown to the user is therefore implicitly main-agent-specific (it's the main agent's role + the engine's phase). When the user has multiple agents with different roles (sub-agents), the modal shows only the main agent's view. The accf332 code uses `self._agent` for `agent_role`, so it's specifically the active agent. This is fine semantically; just not documented. Note for the final report.

### 2.5 Compositional law

The modal-vs-data seam respects two laws:

- **Law 1 (introspection law):** "everything speaks `list[GuardrailEntry]`" -- a frozen dataclass per rule/injection, annotated with `active: bool` + `skip_reason: str`. Producers (digest) and consumers (modal, future slash command, future log dump) only need to agree on this dataclass.
- **Law 2 (lifecycle law):** "enabled state lives in a callable returning `set[str]`" -- the `get_disabled_rules` callback. Anyone who wants to influence enablement only needs to provide a callable; anyone who wants to read it just calls. This is the same pattern as `get_phase`, `get_active_wf`, `agent_role`-as-callable -- callback-driven rather than passing state objects across the seam.

Both laws are minimal, explicit, and universal. The composition is algebraic.

### 2.6 Smell check on the module structure

| Smell | Found? | Where |
|-------|--------|-------|
| Bundled choices | yes (cluster level) | abast bundled D-data + D-UI + E + (B engine) into one commit. We can unbundle. |
| Axis-specific branches | no | `digest.py` is law-driven; no `if format == "arrow"`-style logic. |
| Cross-axis type checks | no | digest doesn't sniff agent type or workflow type. |
| Profile branches | no | modal has no profiles. |
| Untestable in isolation | no | `digest.py` is a pure function; testable with a mock loader. |
| Special-case composition | no | enforcement vs introspection composes via the law. |
| Giant single file | borderline | the modal is 186 lines for one screen + one row + one message dataclass. Not great but not bad. |
| Circular imports | no | `TYPE_CHECKING` import on the consumer side. |
| Project-specific imports | minimal | digest imports `claudechic.guardrails.rules` (sibling); modal imports `claudechic.guardrails.digest` under TYPE_CHECKING only. |
| UI-only operations | yes (D) | the runtime-disable knob is **only** mutable via the modal. No `/guardrails disable <id>` slash command, no MCP tool, no settings entry. So if we adopt D-data without D-UI, the knob is unreachable. |

The "UI-only operations" smell is the strongest argument for **not** adopting the data half in isolation: a feature whose only mutation surface is the UI is, in practice, the UI feature -- you can't pull the data out.

---

## 3. Skeptic Q1-Q6 application

### 3.1 Sub-feature D (modal) -- with `a60e3fe` walk-back applied

| Q | Answer | Evidence |
|---|--------|----------|
| Q1: solves a problem that does not apply to our context? | **partial yes** | The user-targeted problem is "I want to see what rules are active and toggle them off temporarily." We have not heard this complaint. Our `disabled_ids` config + `/settings` editor already solves the persistent-disable case. The only delta is the session-ephemeral toggle, for which we have no documented user. |
| Q2: breaks a stable public contract without migration? | no | Footer label rename `DiagnosticsLabel -> InfoLabel` etc. is a UI symbol rename; no user-facing contract. |
| Q3: depends on abast-specific infra we don't have? | partial yes | The `agent` instance threading through `_make_options(..., agent=...)` and `_merged_hooks(..., agent=...)` is sub-feature B (dynamic roles). D's `app.py` wiring imports the dynamic-role plumbing too. So D-UI depends on B being adopted. |
| Q4: articulate user-visible "before vs after" in one sentence with a concrete user? | **no** | "Before: click 'sys' to see system info; click 'session_info' to see diagnostics. After: click 'info' for both; click 'guardrails' to see a popup of rules with checkboxes that don't persist." The concrete user is hypothetical. We have no Lab user asking for runtime guardrail toggling; our community uses the persistent `disabled_ids` instead. |
| Q5: simpler in-tree change for 80% benefit at 20% cost? | **yes** | A one-line `/guardrails` slash command that calls `compute_digest` and pretty-prints to chat would deliver "I want to see what rules apply" without (a) the modal CSS/widget, (b) the footer button repurposing, (c) the runtime-disable lifecycle, (d) the `app.py` handler conflict. Estimated 30 LOC vs the +186 modal + 50 LOC of `app.py` wiring. |
| Q6: regress something we currently rely on? | no, but **with `a60e3fe` applied** the user is left with a button that says "guardrails" and toasts "not yet implemented" -- a worse UX than not having the button at all. |

**Skeptic verdict: SKIP D-modal.** Q1, Q4, Q5 fire. With the walk-back applied: Q6 also fires (downgrade). Without the walk-back: Q3 fires (depends on B being adopted, and the modal itself may be broken per the 17:27 -> 17:47 timeline).

### 3.2 Sub-feature D-data (`digest.py`) only

| Q | Answer |
|---|--------|
| Q1 | partial yes (no concrete demand) |
| Q2 | no |
| Q3 | no (clean leaf, depends only on `guardrails.rules`) |
| Q4 | **no** -- without a consumer, there is no user-visible delta |
| Q5 | yes (the `/guardrails` slash command is a smaller alternative that includes its own digest-equivalent inline) |
| Q6 | no |

**Skeptic verdict: SKIP D-data for now.** Q4 and Q5 fire. The data layer is genuinely well-designed (composable, leaf, testable), but adopting infrastructure that nothing uses is cargo-culting. Wait until a concrete user asks for an introspection feature.

### 3.3 Sub-feature E (`pytest_needs_timeout` warn rule)

| Q | Answer |
|---|--------|
| Q1 | no -- pytest hangs are a real problem; we already have `no_bare_pytest` shipping in our ruleset. This complements it. |
| Q2 | no -- data-only addition. Our `RulesParser` already supports `enforcement: warn`. |
| Q3 | no -- the `acknowledge_warning` MCP tool has been on our base since pre-merge-base. |
| Q4 | **yes** -- "Before: the agent runs `pytest tests/test_foo.py` and may hang for hours. After: the agent gets blocked with a warn rule asking to add `--timeout=N`; can `acknowledge_warning(...)` if it has a reason." Concrete user: anyone running `pytest` from an agent. |
| Q5 | n/a -- the rule itself is the simplest possible change. |
| Q6 | no -- warn rules are skippable via acknowledgment, so no false-positive escape hatch is missing. |

**Skeptic verdict: ADOPT E.** All Qs answered "no" except Q4 (which is the question we WANT to answer "yes"). Trivial change, real benefit.

### 3.4 Combined recommendation table

| Sub-feature (abast label) | Type | Outcome | Owns the call |
|---------------------------|------|---------|---------------|
| **D guardrails UI** -- modal | named | skip | this axis |
| **D guardrails UI** -- data layer (`digest.py` only) | named (sub-half) | skip / defer | this axis |
| **D guardrails UI** -- runtime-disable plumbing in `hooks.py` | named (sub-half) | skip (no user) | this axis |
| **E `pytest_needs_timeout`** | stowaway -- discovered by team | adopt | this axis |

---

## 4. Per-feature outcome with and without the `a60e3fe` walk-back

The brief specifically asks for D's outcome **with and without** `a60e3fe`.

### 4.1 With `a60e3fe` applied (i.e. cherry-pick the full 4-commit cluster)

- D modal: stub button that toasts "not yet implemented".
- D data layer: orphan dead code in our tree.
- D runtime-disable plumbing in hooks: dormant (no UI flips it).
- User-visible: regression -- a useless "guardrails" button replacing our "sys" button.
- **Outcome: skip the whole D bundle.** Don't pull a stub.

### 4.2 Without `a60e3fe` (i.e. pick `accf332` + `8f99f03` + `2f6ba2e`, drop `a60e3fe`)

- D modal: live, but per the timeline evidence (17:27 -> 17:47, 20 minutes to stub) the upstream author may have hit a UX bug we'd inherit.
- D data layer: live and used.
- D runtime-disable plumbing: functional end-to-end (toggle in modal -> hook honors it).
- User-visible: a "guardrails" button that opens the modal.
- Issues:
  - Q4 still weak: no concrete user demands this.
  - Q5 still strong: a slash command would be cheaper and more robust.
  - The toggle-vs-`disabled_ids` question is unresolved (Terminology flag).
  - Q3: depends on dynamic-role plumbing being live in our `app.py` (sub-feature B). If engine-seam recommends `skip` or `adapt` on B, D falls with it.
- **Outcome: still skip / defer.** Without a clear answer to "who is asking for this and what should `disabled_rules` mean wrt `disabled_ids`", we should not be the canary for a UI the upstream author themselves stubbed.

### 4.3 The middle path

Consider: we adopt **only** `digest.py` from D (clean leaf, no UI), build a `/guardrails` slash command that pretty-prints the digest in chat, and skip the modal + footer-button rename + runtime-disable lifecycle entirely. This honors:
- Q5 (simpler change).
- Composability (the data axis is independent).
- Skeptic's "essential vs accidental complexity" -- introspection is essential; runtime-toggling is accidental.

Cost: ~30 LOC for the slash command + adopt `digest.py` file as-is. Conflict surface: zero (no `app.py` handler conflict, no footer rename, no `_disabled_rules` plumbing).

**However**, applying Skeptic Q4 to the slash command itself: who asks for this? No documented user. So even the middle path fails Q4.

**Recommended position:** skip D entirely (modal AND data layer AND runtime-disable plumbing) for this cluster sync. If a future user request for "what rules are active right now?" emerges, revisit and prefer the slash-command approach over the modal.

---

## 5. Sub-feature E -- standalone analysis

### 5.1 Standalone value

**Yes, fully standalone.** The rule is a 7-line YAML addition. It uses only existing infrastructure (the `RulesParser`, the `warn` enforcement level, `acknowledge_warning`). It does not depend on D, on accf332's other sub-features, or on `003408a`.

### 5.2 Collision check

Our `defaults/global/rules.yaml` has 4 rules. None matches `pytest_needs_timeout` by id, by trigger, or by detect pattern.

The closest existing rule is `no_bare_pytest`, which has a much narrower trigger pattern (it targets bare `pytest` invocations missing certain flags like `--junitxml`, `-k`, etc.). The new `pytest_needs_timeout` rule fires on a different concern (any `pytest` without `--timeout`) and is `warn` not `deny`. They can coexist:
- `pytest --junitxml=...` (no timeout) -> passes `no_bare_pytest`, blocked by `pytest_needs_timeout` (warn).
- `pytest tests/foo.py` (no timeout) -> passes `no_bare_pytest` (because `\\.py` is in the negative lookahead's match set), blocked by `pytest_needs_timeout` (warn).
- `pytest --timeout=60 tests/foo.py` -> passes both.
- Bare `pytest` -> blocked by `no_bare_pytest` (deny) before `pytest_needs_timeout` is even reached.

The hook short-circuits on the first warn/deny match, so order matters: `no_bare_pytest` (deny) appears first in the file and will fire first; `pytest_needs_timeout` (warn) only fires when `no_bare_pytest` doesn't.

The detect pattern is conservative: `(?:^|[;&|]\\s*)(?:python\\s+-m\\s+)?pytest\\b(?!.*--timeout)`. Note that `\\b(?!.*--timeout)` is a negative lookahead for `--timeout` anywhere later in the command. This catches:
- `pytest tests/foo.py` -> match
- `pytest -k foo` -> match
- `pytest --timeout=60` -> no match (lookahead succeeds)
- `pytest tests/foo.py --timeout=10` -> no match
- `pytest --timeout-method=signal` -> no match (lookahead matches the literal `--timeout`)

The last case is a minor false negative (`--timeout-method=signal` does NOT actually set a test timeout in pytest-timeout); not worth fixing.

### 5.3 Adoption mechanics

The diff context references `no_pip_install` (which we don't have), so the cherry-pick will fail at `git cherry-pick accf332` for this file. Two options:

(a) Cherry-pick accf332 with `-X theirs` for `rules.yaml` and inspect the result manually.
(b) Skip the cherry-pick for this file and append the 7 lines manually:

```yaml
- id: pytest_needs_timeout
  trigger: PreToolUse/Bash
  enforcement: warn
  detect:
    pattern: "(?:^|[;&|]\\s*)(?:python\\s+-m\\s+)?pytest\\b(?!.*--timeout)"
  message: "pytest invoked without --timeout. Add --timeout=<seconds> to prevent runaway tests."
```

Append after `no_bare_pytest`. Order doesn't matter for behavior (different enforcement levels short-circuit differently), but matching abast's order keeps diffs small.

Option (b) is cleaner.

### 5.4 Outcome

`(E, adopt, none)`. Manual append, no engine-seam dependencies, no UI, no test changes (we have no tests asserting absence of this rule).

---

## 6. Inter-axis coordination + flagged context

### 6.1 Inter-axis coordination (in-cluster only)

There is a small `app.py` wiring overlap between this axis (D) and engine-seam (B dynamic roles):

- Sub-feature D adds `_disabled_rules: set[str]` and `get_disabled_rules` callback into `_guardrail_hooks`/`_merged_hooks`/`_make_options`.
- Sub-feature B (dynamic roles) adds an `agent: Agent | None = None` parameter to those same methods.
- They share the same `app.py` lines.

If both D and B are adopted, the `app.py` wiring conflict is shared between this axis and engine-seam. If only B is adopted (this axis's recommendation: skip D), engine-seam handles `app.py` cleanly without D's `_disabled_rules` plumbing. If neither is adopted, `app.py` stays as-is.

**Implication:** this axis's recommendation to skip D removes a conflict surface from engine-seam's `app.py` work. Net positive coordination outcome.

### 6.2 Flagged context (out-of-cluster -- NOT a recommendation)

Per the user's scope guard ("stay strictly inside the 4-commit cluster; flag, don't chase"), the out-of-cluster commit `003408a` is surfaced here as flagged context only. **This axis makes no adopt/skip recommendation on `003408a`.**

For team awareness:
- `accf332` unblocks `003408a` (per historian's V1 finding: accf332 ships the `DEFAULT_ROLE` sentinel and the `main_role` promotion path, two of the three prerequisites cited in our `18061ec` revert message; the third, broadcast-on-advance, is already on our base).
- `003408a` touches files inside this axis's surface (`guardrails/hooks.py` -- richer warn-rule reasoning text; `checks/builtins.py` -- per-check `cwd`/`base_dir` ctor params; `mcp.py` -- `DEFAULT_ROLE` sentinel handling for `spawn_agent`).
- Re-applying `003408a` after `accf332` is "additive" per historian, with no re-trigger of the original revert reason.

The user may want a follow-up investigation on `003408a` after the accf332 cluster decisions land. The team does not pre-decide this on the current axis-agent passes.

---

## 7. Contract-surface impact inventory

Per the Hand-off contract, each axis-agent must inventory contract surface:

| Surface | Affected by D? | Affected by E? |
|---------|----------------|----------------|
| `settings.json` schema | no (modal toggle is in-memory, not persisted to settings) | no |
| MCP tool API | no | no |
| Observer protocols | no | no |
| Workflow YAML schema | no | no (uses existing `Rule` schema) |
| `defaults/global/rules.yaml` schema | no | yes -- adds one record (additive, no schema change) |
| `defaults/global/rules.yaml` content | no | yes -- one new id `pytest_needs_timeout` |
| On-disk state file format | no | no |
| Hook block-message format (`hooks.py`) | no | no |
| Footer label set | yes (rename DiagnosticsLabel/ComputerInfoLabel -> InfoLabel/GuardrailsLabel) | no |
| App-level public attrs | yes (adds `_disabled_rules` -- private, but accessed from hooks via callback) | no |
| Hook callback signature (`create_guardrail_hooks`) | yes (adds `get_disabled_rules` kwarg; default `None`, additive) | no |

**Contract-surface impact for the recommended outcomes (skip D, adopt E):** zero new public API surface; one additive YAML rule. Lowest possible footprint on the cluster.

---

## 8. Essential vs accidental complexity

Per Skeptic's hand-off contract:

**Essential complexity in D:**
- Introspection law (`list[GuardrailEntry]`): clean, durable, useful for slash command / log dump / future surfaces.
- The data layer (`digest.py`): a textbook leaf module.

**Accidental complexity in D:**
- Renaming `DiagnosticsLabel -> InfoLabel` and `ComputerInfoLabel -> GuardrailsLabel`: this conflates the modal restructure (UI-surface axis) with the introspection feature.
- Per-row `Checkbox.BUTTON_INNER = " "` monkey-patch: workaround for textual layout.
- ID format `gr-cb-{e.id}` assuming rule IDs are valid CSS selectors.
- The `_disabled_rules` set as a separate concept from `disabled_ids`: split for the wrong reason (UI ergonomics rather than semantic distinction).

**Essential complexity in E:**
- The detect pattern uses an existing `Rule` shape with no schema change. The rule itself (warn-level pytest-without-`--timeout`) is essential complexity for any agent that runs tests.

**Accidental complexity in E:**
- None. 7-line YAML record, no Python changes, no other tracking required.

---

## 9. Refined glossary contributions

For the Terminology axis to update its working glossary:

- **`digest`** (proposed clarification): the result of evaluating each loaded `Rule`/`Injection` against a given `(active_wf, agent_role, current_phase, disabled_rules)` snapshot, producing a list of `GuardrailEntry` records annotated with `active: bool` + `skip_reason: str`. Static snapshot, not a live subscription. Computed on demand.
- **`disabled_rules` (accf332)** vs **`disabled_ids` (ours)**: two distinct lifecycle layers (proposed):
  - `disabled_ids` = persistent, config-managed, applies across sessions, set via `/settings`.
  - `_disabled_rules` = session-ephemeral, in-memory only, mutated via the modal.
  - Hook semantics if both adopted: rule is skipped if id is in `disabled_ids` OR `_disabled_rules`.
  - Recommendation if D is skipped: do not introduce `_disabled_rules` at all; if introspection is later added, expose only the persistent path.
- **`info modal` (accf332)** vs **`session_info` + `sys` (ours)**: UI-surface axis owns the renaming question. From this axis: the rename does not affect guardrails functionality.

---

## 10. Summary recommendations

`(sub-feature, outcome, blocking-deps)` -- in-cluster only:

1. `(D guardrails UI -- modal, skip, none)` -- abast's own walk-back signal + Q1/Q4/Q5 fail.
2. `(D guardrails UI -- data layer / digest.py, skip / defer, none)` -- clean code, no consumer, Q4/Q5 fail.
3. `(D guardrails UI -- runtime-disable plumbing in hooks, skip, follows D)` -- dormant without UI.
4. `(E pytest_needs_timeout [stowaway], adopt, none)` -- mechanical YAML append; Q4 strong.

Out-of-cluster `003408a`: not pre-decided on this axis; surfaced in section 6.2 as flagged context only.

For the final report's "Should we pick it up here?" / "Can we reimplement on our base?" sections:

- **D guardrails UI**: skip. If a future user asks for "what rules apply right now?", reimplement as a `/guardrails` slash command over `compute_digest`, ~30 LOC, no UI dependencies.
- **E `pytest_needs_timeout`** (stowaway -- discovered by team, not named in user prompt): adopt. ~7 lines of YAML, append to `defaults/global/rules.yaml`, no other changes.

### Gestalt one-sentence per recommendation (per UserAlignment C2)

- After **skipping D**, the user sees: no change. Footer keeps the existing `session_info` and `sys` buttons; no "guardrails" button appears; persistent rule disable continues via `/settings` -> `disabled_ids` as today.
- After **adopting E**, the user sees: when an agent runs `pytest tests/foo.py` (or any pytest invocation missing `--timeout=`), the agent receives a warn-level block telling it to add `--timeout=N` (or `acknowledge_warning(...)` with a stated reason). Concrete user: anyone who has been bitten by an agent's pytest run hanging indefinitely.

---

*End of original guardrails-seam Specification deliverable. Section 11 below supersedes the D portion.*

---

## 11. D reframed (user redirect 2026-04-29)

**The previous D analysis (sections 1-10) was based on a UI-centric premise -- "should we adopt abast's GuardrailsModal?" -- and recommended SKIP. The user has redirected: D is not about UI. It is about agent self-awareness of applicable constraints.**

User's verbatim words:

> "the point of D is NOT UI it is to make the current state of guardrail rules and advance checks transparent to the AGENT. If we filter into a dict for each agent what rules apply to it (using an MCP call) it could understand its role better. that should be as part of the injected prompt for launching an agent in claudechic"

This reframes D as three coupled mechanisms:

1. **Per-agent filtering** -- a projection of the loaded rules + advance_checks down to "what applies to THIS agent right now", keyed by agent identity.
2. **MCP call** -- runtime self-query so an agent can re-fetch its constraints (e.g. after phase advance).
3. **Launch-prompt injection** -- the per-agent rule set is baked into the agent's initial prompt at spawn time, so it sees its constraints from turn 1 instead of discovering them via deny/warn callbacks.

The previous SKIP verdict no longer applies. Reanalysis below.

### 11.1 Data-layer fit

I re-read `claudechic/guardrails/digest.py` (accf332). Its `compute_digest()` signature is:

```python
def compute_digest(
    loader: ManifestLoader,
    active_wf: str | None,
    agent_role: str | None,
    current_phase: str | None,
    disabled_rules: set[str] | None = None,
) -> list[GuardrailEntry]
```

Each `GuardrailEntry` carries: `id`, `namespace`, `kind` (`"rule"` | `"injection"`), `trigger`, `enforcement`, `message`, `active: bool`, `skip_reason: str`, `roles`, `exclude_roles`, `phases`, `exclude_phases`.

**Fit assessment:**
- The function ALREADY does per-agent filtering. It evaluates `should_skip_for_role` and `should_skip_for_phase` per entry. It just labels skipped entries `active=False, skip_reason=...` instead of removing them.
- For agent self-awareness we want the **active subset** -- so this is `[e for e in compute_digest(...) if e.active]` plus a one-line filter helper.
- The per-entry shape is exactly what an agent needs (id, trigger, enforcement, message). No extension needed for the rule projection.
- **MISSING from digest.py: advance_checks.** The user's redirect explicitly names "guardrail rules AND advance checks." `digest.py` only enumerates `result.rules` + `result.injections`. Advance checks live on `Phase.advance_checks` (a `list[CheckDecl]`) and are reachable via `engine.get_advance_checks_for(phase_id)`. **A sibling function `compute_advance_checks_digest()` is needed** -- ~30 LOC, similar shape, returns per-check metadata for the current phase.

So abast's `digest.py` is a partial substrate: 100% reusable as the rule projection, but does not cover advance_checks. The user's intent requires both.

### 11.2 abast's machinery vs user's design -- the gap

**accf332 builds:**
- `digest.py::compute_digest` (rule projection -- 100% reusable for user intent).
- `GuardrailsModal` UI (irrelevant to user intent).
- `_disabled_rules` runtime-disable plumbing (irrelevant to user intent; in fact orthogonal).
- Footer button rename (irrelevant).

**accf332 does NOT build:**
- Any MCP tool exposing the digest.
- Any prompt-injection hook that includes rules in the agent launch prompt.
- Any advance_checks projection.

**Verdict:** `accf332` is at best a partial substrate. The user's design substantively differs from the abast design. We adopt `digest.py` (or a small equivalent) as the substrate; we BUILD the rest fresh.

### 11.3 MCP API sketch -- REVISED 2026-04-30 per user D5 decision

User decision (D5): reject the two-tool split (`get_applicable_rules` + `get_advance_checks`). Rationale (verbatim):

> "get_phase shouldn't report rules at all. make a get_agent_info that will supersedes both. the point is to have each agent have its state including rules and phase state. It should report both session, workflow phase and rules information."

Revised design: **a single MCP tool `get_agent_info` that consolidates everything an agent needs to know about its own state, AND supersedes `get_phase`.**

#### Tool signature

```python
@tool(
    "get_agent_info",
    "Get the full state of an agent: identity, session, active workflow + phase, "
    "applicable guardrail rules, and advance_checks for the current phase. "
    "Defaults to the calling agent. In-memory lookup, no file I/O. "
    "Supersedes get_phase.",
    {
        "type": "object",
        "properties": {
            "agent_name": {
                "type": "string",
                "description": "Optional: query info for a different agent by name. "
                               "Defaults to caller.",
            },
            "include_skipped": {
                "type": "boolean",
                "description": "If true, include rules/injections that don't currently "
                               "apply to this agent, with skip_reason. "
                               "Default false (only active items).",
            },
        },
        "required": [],
    },
)
async def get_agent_info(args: dict) -> dict:
    # Resolves agent (default: caller via closure-bound caller_name, same
    # path as whoami). Returns markdown text via _text_response.
```

Placement: `claudechic/mcp.py`, alongside `whoami` / `list_agents` / (deprecated) `get_phase`. Wrapper factory `_make_get_agent_info(caller_name)` follows the closure pattern used by `_make_spawn_agent`, `_make_whoami`, etc., to bind the caller name at server-creation time.

#### Output sections (markdown)

Pretty-printed markdown text (not JSON) so the model can reason about it directly. Section order is stable so agents can grep/skim consistently:

```markdown
# Agent: <name>

## Identity
- name: <agent_name>
- role (agent_type): <role or "default"/none>
- cwd: <path>
- model: <full_model_id>
- effort: <low|medium|high|max>     # if applicable
- worktree branch: <branch or none>
- status: <idle|busy|needs_input>

## Session
- session id: <uuid or none if not yet connected>
- jsonl path: <path or none>
- last compaction summary: <first 200 chars or "none">

## Active workflow + phase
- workflow: <workflow_id or "none active">
- phase: <qualified_phase_id or "(none)">
- next phase: <qualified_phase_id or none>
- progress: <idx>/<total> (<comma-list of phase ids>)
- artifact dir: <path or "not set">

## Applicable guardrail rules (active for this role / phase / workflow)
| id | enforcement | trigger | message |
|----|-------------|---------|---------|
| no_bare_pytest | deny | PreToolUse/Bash | Bare pytest blocked. ... |
| pytest_needs_timeout | warn | PreToolUse/Bash | pytest invoked without --timeout. ... |
| log_git_operations | log | PreToolUse/Bash | Git operation logged. |

(<N> active, <M> skipped -- pass include_skipped=true to see why)

## Applicable injections
| id | trigger | inject_value |
|----|---------|--------------|
| (none) |

## Advance checks for the current phase ('specification')
- file-exists-check: `${CLAUDECHIC_ARTIFACT_DIR}/specification/coordinator.md`
- command-output-check: `gh pr list --state open` matches '...'
- manual-confirm: "Do you approve specification handoff?"

## Loader errors
(none)
```

When `include_skipped=true`, add a third column `skip_reason` to the rules / injections tables (e.g. `role 'composability' not in ['skeptic']`, `phase 'setup' excluded`).

#### Caller resolution

When `agent_name` is omitted, use the same closure-bound `caller_name` that `whoami` uses today (`_make_whoami(caller_name=caller_name)` -> closure returns `caller_name`). When `agent_name` is provided, look up the agent via `_app.agent_mgr.find_by_name(name)` and pull its state. Error if name not found. Sub-agents querying themselves will get caller_name automatically; cross-agent queries are explicit.

#### Migration of existing tools

- **`get_phase`**: **delete after one release of overlap.** The current `get_phase` returns workflow id, phase, progress, plus aggregate rule/injection counts WITHOUT per-agent role filtering. Every diagnostic it produces maps cleanly into a section of `get_agent_info` (workflow/phase -> "Active workflow + phase"; aggregate counts -> "Applicable guardrail rules" with the counts implied by the table; loader errors -> "Loader errors"). The role-aware projection is the upgrade. **Migration plan**: in the same change, mark `get_phase` description as `[deprecated] use get_agent_info instead`, keep it functional for one release; remove in the following release. Update all 9 bundled workflow role markdowns that mention `get_phase`. Tests in `test_workflow_*.py` that call `get_phase` migrate to `get_agent_info`.
- **`get_advance_checks`** (proposed in the prior draft): drop entirely. Folded into `get_agent_info`'s "Advance checks for the current phase" section.
- **`get_applicable_rules`** (proposed in the prior draft): drop entirely. Folded into `get_agent_info`'s "Applicable guardrail rules" section.
- **`whoami`**: **keep**. It's a degenerate query (just the caller's name, no app-state lookup). Some agents will still want a one-shot "who am I" without the full info dump. Cheap to keep; delete only if a strong reason emerges later.

#### Why single-tool consolidation is the right shape (Composability lens)

The user's framing identifies a **single axis** for "agent self-knowledge." Splitting it into 2-3 tools (`get_phase` + `get_applicable_rules` + `get_advance_checks`) was the wrong decomposition: those aren't independent concerns the agent ever wants separately -- they're facets of the same query "what is my current state?" Split tools force the agent to make N round-trips to assemble what is conceptually one snapshot. Single tool: one round-trip, one consistent snapshot.

The composition still respects clean seams INSIDE the tool: the markdown output is assembled from independent producers (Identity from `agent_mgr`, Session from `agent.session_id` + jsonl helper, Workflow from `engine`, Rules from `compute_digest()`, AdvanceChecks from `engine.get_advance_checks_for(phase_id)`). Each section's data comes from its own subsystem. The tool is a thin assembler; the subsystems remain orthogonal.

### 11.4 Prompt-injection plan

Two injection points exist already on our base, both call `assemble_phase_prompt(workflow_dir, role_name, current_phase, artifact_dir)`:

1. **`claudechic/mcp.py::spawn_agent`** (lines 277-307) -- when a sub-agent is spawned via MCP, the role-specific identity.md + phase.md is concatenated to the user's prompt before sending.
2. **`claudechic/app.py::_inject_phase_prompt_to_main_agent`** (line 2165) -- when the main agent advances to a new phase, fresh phase content is delivered to the active agent.

The cleanest extension: create a sibling function `assemble_constraints_block(loader, engine, role, ...) -> str` in `claudechic/workflows/agent_folders.py` that returns a markdown section like:

```markdown
## Guardrail rules active for this role/phase

| id | enforcement | trigger | message |
|----|-------------|---------|---------|
| no_bare_pytest | deny | PreToolUse/Bash | Bare pytest blocked. ... |
| pytest_needs_timeout | warn | PreToolUse/Bash | pytest invoked without --timeout. ... |
| log_git_operations | log | PreToolUse/Bash | Git operation logged. |

Use `acknowledge_warning(rule_id=..., tool_name=..., tool_input=...)` to consume warn rules.
Use `request_override(rule_id=..., ...)` to ask the user to override deny rules.

## Advance checks for the current phase ('specification')

- file-exists-check: `${CLAUDECHIC_ARTIFACT_DIR}/specification/coordinator.md` must exist
- command-output-check: `gh pr list --state open` must contain '...'
```

Then modify both injection points to call this and append:

- `mcp.py::spawn_agent`: after `folder_prompt = assemble_phase_prompt(...)`, also call `constraints_block = assemble_constraints_block(...)`. Concatenate as `f"{folder_prompt}\n\n---\n\n{constraints_block}\n\n---\n\n{prompt}"`.
- `app.py::_inject_phase_prompt_to_main_agent`: similarly append the constraints block to the assembled phase prompt.

Optionally: add an `include_constraints: bool = True` parameter to `assemble_phase_prompt` and inline the call (simpler call sites; less duplication). I recommend inlining.

The constraints block is small (typically <500 tokens for a coordinator role) and refreshes naturally on phase advance because `_inject_phase_prompt_to_main_agent` already runs then. Sub-agents get a fresh block at spawn; subsequent agent invocations need to call `get_applicable_rules` to re-check (or, optionally, the PostCompact hook can re-inject).

### 11.5 Filtering logic -- already on our base

I read `claudechic/workflows/loader.py`. Our `ManifestLoader.load() -> LoadResult` already:
- Walks the 3-tier hierarchy (package / user / project).
- Resolves overrides by id.
- Returns merged `rules: list[Rule]` and `injections: list[Injection]`.
- Each `Rule` carries `roles`, `exclude_roles`, `phases`, `exclude_phases`, `namespace`.

The filtering primitives already exist on our base in `claudechic/guardrails/rules.py`:
- `should_skip_for_role(rule, agent_role) -> bool`
- `should_skip_for_phase(rule, current_phase) -> bool`

Plus the namespace check (`rule.namespace == "global" or rule.namespace == active_wf`) is a one-liner used directly in `hooks.py`.

So the per-agent projection is mechanical: walk the loader's rules + injections, apply the three filters, return the active subset. **abast's `digest.py` is exactly this with the additional bookkeeping of `active=False` entries.** We can either:
- (a) Adopt `digest.py` from accf332 verbatim (clean leaf module, no collisions on our side; the file does not exist on our base) and call it from the MCP tool / prompt-injection hook with a `[e for e in result if e.active]` filter on the calling side.
- (b) Write our own ~30-LOC `applicable_rules_for(loader, agent_role, current_phase, active_wf) -> tuple[list[Rule], list[Injection]]` that returns only the active subset.

**Recommendation: (a) adopt `digest.py` verbatim.** Reasons:
- It's a clean leaf with no UI dependencies (the only UI consumer is `GuardrailsModal`, which we'd skip).
- Carrying the `active=False, skip_reason="..."` annotation is genuinely useful: we can expose it to the agent via `get_applicable_rules(include_skipped=True)` for debugging ("why isn't rule X firing for me?").
- It's 128 lines of high-quality code we'd otherwise rewrite at ~80% of that volume. Saves time, gives us the abast author's annotated structure.
- No collision with our base (file doesn't exist).
- Q5 (simpler change) is already passed by adopting; rewriting would be MORE work.

### 11.6 Skeptic Q1-Q6 -- fresh under the new framing

| Q | Answer | Evidence |
|---|--------|----------|
| Q1: solves a problem that does not apply to our context? | **no** | Agent self-awareness of constraints is universal. We already see this problem in our own logs: agents try `pytest tests/foo.py`, get blocked by `no_bare_pytest`, retry, get blocked again. Surfacing rules pre-emptively in the launch prompt would head this off. |
| Q2: breaks a stable public contract without migration? | **no** | New MCP tools are additive (existing tool surface unchanged). New prompt content is additive (longer launch prompt; no schema break). `digest.py` is a new file. The constraints block is markdown text, not a contract. |
| Q3: depends on abast-specific infra we don't have? | **no** | The user's design uses our existing `ManifestLoader` (Group C 3-tier), our existing `WorkflowEngine.get_current_phase()` and `get_advance_checks_for()`, our existing `spawn_agent` injection point, our existing `_inject_phase_prompt_to_main_agent`. **No dependency on accf332 sub-feature B (dynamic roles)** -- the agent's role is statically known at spawn (`type=` arg) or set on activation by our existing `_activate_workflow`. |
| Q4: articulate user-visible "before vs after" in one sentence with a concrete user? | **YES, strong** | "Before: a coordinator agent runs `pytest tests/test_foo.py`, gets a deny block, retries with a flag, gets a warn block, finally figures out the project's pytest conventions. After: at spawn time the coordinator's launch prompt includes a 'Rules active for this role' table listing `no_bare_pytest`, `pytest_needs_timeout`, plus the recommended timestamped invocation, so it gets the test command right on turn 1." Concrete user: every coordinator/sub-agent in `project_team`, `audit`, and `tutorial_toy_project` workflows. |
| Q5: simpler in-tree change for 80% benefit at 20% cost? | **the proposed adapt IS the simpler change** | (Re-asking Q5: simpler than what?) Vs adopting accf332 wholesale: yes -- skip the modal (+186), skip the runtime-disable plumbing (+~30 in hooks + app), skip the footer rename. Net ~70 LOC NEW (`digest.py` adoption ~0 LOC since clean addition; advance_checks digest sibling ~30 LOC; 2 MCP tools ~40 LOC; constraints-block formatter ~25 LOC; spawn/main-inject hook ~10 LOC) vs ~250 LOC if you adopt all of accf332's D-scope. |
| Q6: regress something we currently rely on? | **no** | Additive prompt content. Optional: behind a `awareness.constraints_in_prompt` user-tier toggle for users who don't want the verbosity. Default on. |

**All six questions PASS** under the new framing. Q4 in particular is now strongly affirmative -- we have a concrete user (coordinator agents in any of our 9 bundled workflows) and a concrete failure mode (retry loops on guardrail-violating tool calls).

### 11.7 Revised verdict and `(D, outcome, blocking-deps)`

`(D guardrails UI -- as reframed by user 2026-04-29, **adapt**, none)` -- where "adapt" means:

| Component | Outcome | Notes |
|-----------|---------|-------|
| `claudechic/guardrails/digest.py` | **adopt verbatim** from accf332 | Clean leaf, no collisions, useful annotated shape (`active` + `skip_reason`). Minor: docstring tweak to remove "no UI dependencies" framing if we want; file is otherwise as-is. |
| Sibling `compute_advance_checks_digest()` | **build new** (~30 LOC) | Not in accf332. Reads `engine.get_advance_checks_for(phase_id)` and produces per-check metadata. |
| MCP tool **`get_agent_info`** (single, supersedes `get_phase`) | **build new** (~80-100 LOC) | Per user D5. Consolidates identity / session / workflow / phase / applicable rules / applicable injections / advance_checks / loader errors into one markdown response. Wraps `compute_digest` + the advance-checks sibling. |
| Deprecate + delete `get_phase` (one-release grace) | **modify** (~5 LOC mark deprecated; -50 LOC eventual delete) | Every diagnostic it produces maps to a `get_agent_info` section. Update 9 bundled workflow role markdowns and `test_workflow_*.py` callers. |
| `assemble_constraints_block` formatter | **build new** (~25 LOC) | Not in accf332. Markdown table from digest entries + advance_checks list. Same renderer reused by `get_agent_info` and the spawn/phase-advance prompt-injection. |
| Inject in `mcp.py::spawn_agent` | **modify** (~5 LOC) | Concatenate constraints block to existing folder_prompt. |
| Inject in `app.py::_inject_phase_prompt_to_main_agent` | **modify** (~5 LOC) | Same pattern. |
| Inject in `agent_folders.py::create_post_compact_hook` | **modify** (~5 LOC) | Re-inject after `/compact` so the agent doesn't lose the constraints context on autocompact. |
| `claudechic/widgets/modals/guardrails.py` (modal) | **skip** | User explicit: "the point of D is NOT UI." |
| `claudechic/widgets/layout/footer.py` rename | **skip** | UI-surface axis (already on the rename topic). |
| `_disabled_rules` runtime-disable plumbing | **skip** | Different feature; not relevant to agent self-awareness. The user did not ask for "agents can disable their own rules at runtime." |
| `defaults/global/rules.yaml` update | **(unchanged from earlier verdict)** -- adopt for E only | Sub-feature E stays adopt; D-reframed adds nothing here. |

**Blocking deps:** none. D-reframed works on our current base. It does not require sub-feature B (dynamic roles) -- the agent's role is known statically at spawn and on workflow activation, which our base already handles. It does not require sub-feature A (template variables) -- the constraints block does not use `$STATE_DIR`/`$WORKFLOW_ROOT`. (If sub-feature A IS adopted, the advance_check params would substitute `$STATE_DIR` etc. before display, which is a bonus, not a dependency.)

**Coordination flag for engine-seam:** D-reframed adds NO new wiring to `_make_options`/`_merged_hooks`/`_guardrail_hooks`. So the prior coordination concern (D + B sharing `app.py` lines) goes away entirely. Engine-seam can decide on B independently.

### 11.8 Smell check on the reframed design

- **Per-agent filter law** (compositional law): the projection `(loader, agent_role, current_phase, active_wf) -> list[GuardrailEntry]` is a pure function. Same inputs always produce same outputs. No mutable state on the seam.
- **Surface axis** factored cleanly: enforcement (hook) | introspection-data (digest) | introspection-MCP (new tool) | prompt-injection (new formatter + 2 spots). Each consumes the digest and adds its own concern. The data layer doesn't know about MCP; MCP doesn't know about prompt-injection; prompt-injection doesn't know about MCP.
- **No UI-only operations smell** in the reframed design (the previous smell). The data layer has 3 callers: MCP tool (machine-readable), prompt-injection (human-readable markdown for the agent), and (optionally) future slash command (human-readable for the user). Each is independent.
- **No bundled choices**: adopting `digest.py` does not pull in the modal, the footer rename, or the runtime-disable plumbing. Each axis value is independent.

### 11.9 Open questions for the user (NOT pre-decided)

The reframed design still has decisions for the user / coordinator at the implementation checkpoint:

1. **Constraints-block size budget.** A coordinator role in `project_team` can have ~10-15 active rules and ~3-5 advance checks. That's ~600-1000 tokens of overhead at spawn. Acceptable? Configurable via `awareness.constraints_in_prompt` toggle (default on, off-switch available)?
2. **Refresh policy.** Re-inject on phase advance (already in `_inject_phase_prompt_to_main_agent`). Re-inject on PostCompact (existing hook can append the block). What about role mutation if dynamic roles (sub-feature B) is adopted -- should we re-inject when the main agent gets promoted?
3. **Skipped-entries inclusion in launch prompt.** I recommend `active` only in launch prompts (less noise) but allow `include_skipped=True` on `get_applicable_rules` for debugging. Confirm.
4. **Order of rules in the markdown table.** `deny` first, then `warn`, then `log`? Or alphabetical by id? I recommend by enforcement severity (most-restrictive first).

These don't block the adopt/adapt decision; they're implementation-phase choices.

### 11.10 Refined glossary contributions (update to section 9)

- **`applicable rules` / `applicable advance_checks`** (proposed): the per-agent projection of rules / advance_checks filtered to those that would currently fire for THIS agent (given its role, current phase, active workflow). Static snapshot, computed on demand.
- **`constraints block`** (proposed): a markdown section appended to the agent's launch prompt summarising applicable rules and advance_checks. Distinct from `digest` (which is the underlying data) and from `phase content` (which is the role's identity.md + phase.md).
- **`get_agent_info`** (proposed, per user D5): single MCP tool that returns the calling agent's full state -- identity, session, active workflow + phase, applicable rules / injections, advance_checks, loader errors. Supersedes `get_phase`. Markdown text response.
- **`agent self-knowledge`** (umbrella): the user's framing for D-reframed. The single axis served by `get_agent_info` and the launch-prompt constraints block.

### 11.11 Summary -- what changes in the final report

The final report's "guardrails UI" section should now read:

- **D guardrails UI** (reframed by user as "agent self-knowledge via per-agent rule/advance_check projection + a single `get_agent_info` MCP query + prompt-injection at spawn / phase-advance / PostCompact"): **adapt**. Adopt `digest.py` from accf332 verbatim as the data substrate; build a sibling `compute_advance_checks_digest()` for advance_checks; build the **single MCP tool `get_agent_info` that supersedes `get_phase`** (per user D5); build `assemble_constraints_block()` and inject at three sites (`spawn_agent`, `_inject_phase_prompt_to_main_agent`, `create_post_compact_hook`). Skip abast's modal + footer rename + runtime-disable plumbing. Total estimated work: ~150-180 LOC new code + 1 file adopted from accf332 + ~50 LOC of `get_phase` deletion across the migration tail. No blocking deps on engine-seam's sub-feature A or B.
- After this lands, the user sees: every agent in every workflow starts turn 1 already knowing the rules and advance_checks that apply to it, AND can call `get_agent_info` at any time to re-confirm its full state in a single round-trip. The legacy `get_phase` is replaced by the per-agent-aware tool. Concrete user: every coordinator and sub-agent.

---

### 11.12 Addendum -- supplemental context from historian (2026-04-29)

Coordinator surfaced two pieces of historian context after section 11 was drafted. Both **confirm and refine** the section 11 verdict; neither changes it.

**Item 1: `d001e30` (Group D, +1253 LOC) -- in-memory phase-prompt delivery.**

Inspected the commit. Two relevant facts for D-reframed:

- `_activate_workflow` already sends the assembled identity.md + phase.md prompt to the active agent via `_send_to_active_agent` (no file I/O). So the prompt-injection hook for the main agent on workflow activation is already in place.
- `_inject_phase_prompt_to_main_agent` already calls `assemble_phase_prompt` and delivers via `_send_to_active_agent` on phase advance. The 9-test `tests/test_phase_prompt_delivery.py` covers INV-AW-6/8/9 plus an end-to-end test asserting the active agent's first user message contains the assembled prompt content.

**Effect on section 11.4:** my plan called these two sites out by name. Confirmation that they are the right hooks AND that they have test coverage already. The constraints-block extension lands on top of working, tested machinery -- not on speculative integration points. Risk lower than I assumed.

There is a second injection mechanism in `d001e30` worth flagging: `claudechic/awareness_install.py` installs bundled context docs (`claudechic/context/*.md`) to `~/.claude/rules/claudechic_<name>.md` on startup, so the SDK picks them up as Claude rules in **every** Claude Code session (not just claudechic-managed ones). That has BROADER reach than in-memory injection.

A possible alternative (or complement) for D-reframed: write a generated `claudechic_constraints_<workflow>_<role>.md` to `~/.claude/rules/` on workflow activation. Pros: every Claude Code session in that role sees the rules, even outside claudechic. Cons: stale-on-disk problem (rules change but the file persists); leaks workflow state into the user's global Claude rules dir; the awareness-install module's symlink-guard / DELETE-orphan logic would need extending. **Recommendation: prefer in-memory injection (the path I proposed) for the constraints block.** The constraints block is per-agent-and-phase ephemeral; the awareness-install path is for stable cross-session content. Mixing them muddles the boundary.

**Item 2: `a743423` -- `test_main_agent_role_resolves_to_main_role` passes on our base.**

Inspected the commit. It's a test fixup (the test's hook fired with the wrong `tool_name` after the message_agent rename); the underlying behavior (main agent's role resolves to the workflow's `main_role` post-activation, which lets `roles: [coordinator]`-scoped rules fire) was already working. The fix made the test actually exercise the behavior it claims to.

**Effect on section 11:** confirms Q3 (D-reframed does NOT depend on sub-feature B dynamic roles). Our base ALREADY has a functional `main_role` resolution on workflow activation, with test coverage proving role-scoped rules fire correctly on the main agent post-activation. So `compute_digest(loader, active_wf, main_role, current_phase)` returns the right per-agent projection on our current base, today, without any of accf332's dynamic-role-flip machinery.

This strengthens the recommendation: D-reframed has no blocking deps on engine-seam at all. It can land independently of (and in parallel with) any decision the engine-seam axis-agent makes on sub-features A and B.

### 11.13 Final summary (post-addendum)

- **D guardrails UI -- as reframed (with D5 single-tool decision applied)**: **adapt**, no blocking deps.
- Substrate from accf332: adopt `claudechic/guardrails/digest.py` verbatim (~128 LOC, clean addition).
- Substrate already on our base: `_activate_workflow` + `_inject_phase_prompt_to_main_agent` (in-memory phase-prompt delivery, tested) + `mcp.py::spawn_agent` injection point + `agent_folders.py::create_post_compact_hook` + `ManifestLoader.load()` (3-tier merged) + `should_skip_for_role`/`should_skip_for_phase` (filtering primitives) + `WorkflowEngine.get_advance_checks_for(phase_id)` + functional `main_role` resolution on activation.
- New code to write: ~150-180 LOC (sibling `compute_advance_checks_digest`, single `get_agent_info` MCP tool, `assemble_constraints_block` formatter, 3 inject-site modifications -- spawn / phase-advance / PostCompact).
- Migration tail: deprecate then delete `get_phase` (one-release grace), update 9 bundled workflow role markdowns + `test_workflow_*.py` callers (~50 LOC of edits, mostly mechanical).
- Skip from accf332: `widgets/modals/guardrails.py`, footer label rename, `_disabled_rules` runtime-disable plumbing.
- **E `pytest_needs_timeout`**: unchanged -- still adopt (data-only YAML append).
- `003408a`: unchanged -- out-of-cluster, not pre-decided on this axis.

---

*End of section 11. Sections 1-10 record the original UI-centric analysis (now superseded for D); section 11 (with addendum 11.12-11.13) is the operative recommendation under the user's redirect. Sub-feature E (`pytest_needs_timeout`) is unaffected -- still adopt.*
