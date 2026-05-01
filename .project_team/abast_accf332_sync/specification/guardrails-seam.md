# Guardrails-seam axis findings

**Author:** guardrails-seam axis-agent (Specification phase, second pass)
**Date:** 2026-04-29
**Cluster:** abast `accf332` + `8f99f03` + `2f6ba2e` + `a60e3fe`. Merge-base `285b4d1`. Our HEAD `a2c3779`.
**Scope owned by this axis:** sub-feature D (guardrails UI), sub-feature E (`pytest_needs_timeout` warn rule), and the out-of-cluster precursor `003408a` (advance-check messaging fix). Composability terms: data-side digest, UI-side modal, footer button repurposing, hook callback `get_disabled_rules`, the `app.py` handlers.

This pass supplements the prior `spec_guardrails_seam.md` with a tightly scoped re-read against the abast source, focused on the six composability questions in the brief.

---

## Sub-feature D: guardrails UI

### User-visible delta (one sentence)

After this lands, the user clicking the footer button labelled "guardrails" sees a modal listing every loaded `Rule` and `Injection` annotated with active/skipped status, with checkboxes that disable a rule for the rest of the current session (no persistence, resets at next launch); on `abast/main` itself, after `a60e3fe`, that same click instead toasts "Guardrails viewer not yet implemented".

### Contract-surface impact

| Surface | Before | After (without `a60e3fe`) | After (with `a60e3fe`) |
|---------|--------|---------------------------|------------------------|
| `~/.claudechic/config.yaml` schema | `disabled_ids` (persistent) | unchanged -- toggle is in-memory only | unchanged |
| `<repo>/.claudechic/config.yaml` schema | `disabled_ids` | unchanged | unchanged |
| MCP tool API | `acknowledge_warning`, `request_override` | unchanged | unchanged |
| Observer protocols | `AgentObserver`, `AgentManagerObserver` | unchanged | unchanged |
| Workflow YAML schema | `Rule`, `Injection`, hints | unchanged | unchanged |
| Hook callback signature `create_guardrail_hooks(...)` | `consume_override`, `get_phase`, `get_active_wf`, `agent_role` | **adds `get_disabled_rules: Callable[[], set[str]]`** (kwarg, default None, additive) | additive change kept; consumer dormant |
| `app.py` private attrs | `_token_store`, `_workflow_engine` | **adds `_disabled_rules: set[str]`** (private, but read by hooks via callback) | added; never written |
| `app.py` event handlers | `on_diagnostics_label_requested`, `on_computer_info_label_requested` | **renamed** to `on_info_label_requested`; **adds** `on_guardrails_label_requested`, `on_guardrail_toggled` | rename kept; new handlers stubbed out |
| Footer label set | `DiagnosticsLabel` ("session_info"), `ComputerInfoLabel` ("sys") | **renamed and repurposed:** `InfoLabel` ("info"), `GuardrailsLabel` ("guardrails") | rename kept; "guardrails" button leads to a stub toast |
| New widget message | (none) | `GuardrailToggled(rule_id: str, enabled: bool)` -- emitted by checkbox | class still exists; never received |
| New module surface | (none) | `claudechic.guardrails.digest:compute_digest`, `GuardrailEntry`; `claudechic.widgets.modals.guardrails:GuardrailsModal`, `GuardrailToggled` | files remain as orphan code |
| On-disk state | hits.jsonl | unchanged | unchanged |

Important: the brief asks "is this typed contract or implementation-specific shape?" -- it is **typed**. `digest.py` produces `list[GuardrailEntry]` (frozen dataclass). The modal accepts that list as its sole input. The toggle returns to `app.py` via a `GuardrailToggled` `Message` subclass with two named attrs. Three durable boundary types.

### Skeptic Q1-Q6 verdicts (D modal as a whole)

| Q | Verdict | Notes |
|---|---------|-------|
| Q1 problem-doesn't-apply | **YES (partial)** | We have `disabled_ids` config + `/settings` editor for persistent disable; no documented user asks for the session-ephemeral toggle. |
| Q2 breaks public contract | no | Footer-label rename and new `get_disabled_rules` kwarg are additive; not a stable surface our users program against. |
| Q3 abast-only infra dep | **YES (partial)** | The `app.py` handler relies on `agent.agent_type` resolving to a non-`None` role for D's modal to be useful (`agent_role=agent.agent_type`). Without sub-feature B (dynamic roles), main agent's `agent_type` is `None` on our base, so the digest's role-skip column would always show "role 'None' excluded" for any role-scoped rule. Adopting D-UI without B yields a half-broken modal. |
| Q4 one-sentence user delta | **NO** | Best one-sentence delta: "click 'guardrails' for a session-ephemeral checkbox view of rules." There is no concrete Spruston Lab user asking for this; our community uses persistent `disabled_ids`. With `a60e3fe` applied: even abast cannot articulate the delta. |
| Q5 simpler in-tree alternative | **YES** | A `/guardrails` slash command that calls `compute_digest()` and prints to chat delivers the introspection win at ~30 LOC, no widget CSS, no footer rename, no runtime-disable lifecycle, no `app.py` handler conflict. |
| Q6 regresses property | **YES (only with `a60e3fe`)** | Replacing the working "sys" / "session_info" buttons with a stub-toasting "guardrails" button is a UX regression; without `a60e3fe`, no regression on the modal itself but rename still imposes a relabel cost. |

### Composability verdict

`(D-modal, skip, none)` -- with or without `a60e3fe`.

Reasoning: skipping the modal on its own removes the `app.py` handler conflict (which engine-seam also touches for sub-feature B), removes the footer rename (which UI-surface owns), and removes the runtime-disable lifecycle. The `digest.py` data layer is independently adoptable but lacks a consumer; the prior `spec_guardrails_seam.md` already classified it `skip / defer`. I reaffirm that.

If the user later wants introspection, the right shape is a `/guardrails` slash command that imports `compute_digest` -- it satisfies Q5, eliminates Q3 (no `agent.agent_type` plumbing required if we just label entries by the active agent), and eliminates the `disabled_rules`-vs-`disabled_ids` semantic ambiguity (the slash command does not need to mutate state).

Per-half breakdown for the user-checkpoint:

- `(D-modal, skip, none)`
- `(D-data-layer/`digest.py`, skip-defer, none)` -- clean leaf, but no caller
- `(D-runtime-disable-plumbing-in-`hooks.py`, skip, follows-D)` -- dormant without UI
- `(D-footer-rename `Diagnostics->Info`, `ComputerInfo->Guardrails`, **owned by UI-surface**)` -- this axis defers the rename decision; UI-surface owns it. If UI-surface skips the rename, this axis's recommendation stands cleanly.

---

## Sub-feature E: pytest_needs_timeout warn rule

### User-visible delta (one sentence)

After this lands, an agent that runs `pytest tests/test_foo.py` (no `--timeout`) gets a warn-level block reading "pytest invoked without --timeout. Add --timeout=<seconds> to prevent runaway tests." and must add `--timeout=N` or call `acknowledge_warning(rule_id="pytest_needs_timeout", ...)` to proceed.

### Contract-surface impact

One additive YAML record in `claudechic/defaults/global/rules.yaml`. No code change. No new schema. No new symbol. The rule uses pre-existing infrastructure (`RulesParser`, `enforcement: warn`, `acknowledge_warning`).

The cherry-pick of accf332's rules.yaml change will fail context match on our base because abast's diff context references `no_pip_install` (which lives in abast pre-accf332 but not in our `defaults/global/rules.yaml`). Manual append is the cleanest mechanism.

### Skeptic Q1-Q6 verdicts

| Q | Verdict | Notes |
|---|---------|-------|
| Q1 | no | Pytest hangs are a real problem; we already ship `no_bare_pytest` next to it. |
| Q2 | no | Data-only addition. |
| Q3 | no | `acknowledge_warning` MCP tool predates merge-base. |
| Q4 | yes (positive sense) | Concrete user: anyone running `pytest` from an agent who has been bitten by a hung test. |
| Q5 | n/a | The rule is the simplest possible change. |
| Q6 | no | Warn rules are skippable via acknowledgment. |

Note on Skeptic's prior false-positive concern: Skeptic's review (`skeptic_review.md`) flagged that the regex may false-positive on non-execution `grep`/`echo` mentions of "pytest" because the `no_bare_pytest` regex is similarly-shaped. The same risk exists for `pytest_needs_timeout`: the detect pattern fires on any line containing the literal "pytest" (after a delimiter or at start) without a later `--timeout`. So `grep -c "pytest" file` triggers it. **Recommendation:** harden the pattern by anchoring the executable boundary, e.g. add a require-after-look-ahead for a flag, file path, or end-of-command. Concrete tighter pattern (suggestion, not blocker): `(?:^|[;&|]\s*)(?:python\s+-m\s+)?pytest(?=[\s;|&>]|$)(?!.*--timeout)`. The added `(?=[\s;|&>]|$)` ensures we matched the executable, not a substring of `pytest` inside an argument. (For consistency: apply the same hardening to `no_bare_pytest` in a follow-up; out of scope for E itself.)

### Composability verdict

`(E, adopt, none)` -- manual append of 7 YAML lines after `no_bare_pytest`. Recommend hardening the regex per above; not a blocker for adoption. **No dependency** on D or on `003408a`.

---

## (Flagged) 003408a re-pick

Per the user's D4 course-correction (UserAlignment), `003408a` is OUT-OF-CLUSTER and **does not get a team adopt/skip verdict**. This section provides flagged context only and an explicit follow-up question for the user.

The prior `spec_guardrails_seam.md` decomposed `003408a` into three threads and went beyond the D4 boundary by pre-recommending one. I keep the decomposition (useful for the user's follow-up decision) but mark the verdicts as "context only, user decides."

### What it changes (concrete deltas)

Three independent threads in one commit:

(i) **`claudechic/checks/builtins.py`** -- adds `_resolve_against(path, base_dir)` helper; adds `cwd: str | Path | None` ctor param to `CommandOutputCheck`; adds `base_dir: str | Path | None` ctor param to `FileExistsCheck` and `FileContentCheck`; rewrites `ManualConfirm`'s decline-evidence text to instruct the agent NOT to retry without first asking the user; updates the three `register_check_type(...)` factories to forward the new ctor params from manifest decl `params`. Net effect: relative paths in check manifests resolve against the workflow root rather than the Python process cwd.

(ii) **`claudechic/guardrails/hooks.py`** -- adds a `get_disabled_rules` callback parameter (NOTE: this is **the same callback shape that accf332 also adds** -- see "New collisions discovered" below); rewrites the warn-rule block message to add three explanatory paragraphs telling the agent why not to just retry and how to acknowledge. Net effect: warn rules give the agent a richer rationale before the suggested `acknowledge_warning(...)` snippet.

(iii) **`claudechic/mcp.py`** -- adds `_get_workflows_dir()` and `_get_workflow_variables()` helpers; rewrites `_make_spawn_agent` to default `agent_type` to `DEFAULT_ROLE` instead of `None`, to reject `type=DEFAULT_ROLE` explicitly, to skip role-folder validation/prompt-injection for DEFAULT_ROLE; updates `_make_advance_phase` to use the new helpers and to include `DEFAULT_ROLE` in the broadcast skip-list. Net effect: sub-agent role wiring becomes explicit (DEFAULT_ROLE sentinel rather than None ambiguity), and template variables (`$STATE_DIR`, `$WORKFLOW_ROOT`) flow into all three places that re-assemble role prompts.

### Why it broke last time (recap from historian, not a re-derivation)

Our `8abb2f9` cherry-pick was reverted as `18061ec` because three prerequisites were missing on our base at the time:

1. `DEFAULT_ROLE` sentinel (was added by our `1d3f824` then reverted)
2. `main_role` promotion path on workflow activation
3. Broadcast-on-advance to typed sub-agents

`003408a`'s thread (iii) imports `DEFAULT_ROLE` from `agent_folders.py`; with our revert of `1d3f824`, that import is unsatisfiable -- F401 / ImportError in tests.

### Why it works now (or doesn't)

Per historian V1: of the three prerequisites, **two are introduced natively by `accf332`** (DEFAULT_ROLE; main_role promotion via dynamic `agent.agent_type`), and **one is already on our base** (broadcast-on-advance, present pre-merge-base via `66fa580`/`ca003a3`). So if `accf332` (or just the DEFAULT_ROLE half of B) lands, all three prerequisites are met and `003408a` becomes safely re-applicable.

Re-trigger risk on the originally-reverted basis: NONE (per historian).

New risk surface after re-application: precedence between accf332's engine-level `params.setdefault("cwd", workflow_root)` and 003408a's ctor-level `cwd=p.get("cwd")`. With `setdefault`, the engine pre-populates `cwd` so the ctor receives a non-None value -- engine-level wins. This is the desirable outcome (uniform pinning at the engine layer); test to verify in implementation.

### Skeptic Q1-Q6 verdicts (per thread, context only)

**Thread (i) -- per-check `cwd`/`base_dir` ctor params:**

| Q | Verdict |
|---|---------|
| Q1 | no -- check-cwd drift is a real bug; symptom on our base today is intermittent advance failures depending on which agent triggered them. |
| Q2 | no -- additive ctor kwargs with defaults. |
| Q3 | yes -- depends on `accf332` (or a smaller equivalent) being in place to feed `cwd=workflow_root` from the engine. Without that, the new params are dead args. |
| Q4 | yes (positive) -- "Before: `tests/test_foo.py` resolves against process cwd which may have drifted. After: resolves against the workflow root, period." |
| Q5 | yes -- engine-level pinning via `params.setdefault` (which `accf332` does) supersedes most of (i)'s value. (i) is then a defense-in-depth layer for non-engine callers. |
| Q6 | no |

Composability note: this thread is **subsumed-but-not-redundant** under accf332. Engine-seam owns the call.

**Thread (ii) -- richer warn-rule reasoning text in `hooks.py`:**

| Q | Verdict |
|---|---------|
| Q1 | no -- agent retry loops on warn rules are a real failure mode. |
| Q2 | no -- the warn-rule reason string is consumed by Claude as natural language, not parsed by a public client. |
| Q3 | no -- pure additive text in the existing warn block; no other prerequisites. |
| Q4 | yes (positive) -- "Before: the agent sees `<rule message>\nTo acknowledge: acknowledge_warning(...)`. After: the agent additionally sees three paragraphs telling it WHY to think before acknowledging and inviting it to first reason about user intent." |
| Q5 | n/a -- the change is itself ~10 LOC. |
| Q6 | no |

Composability note: this thread sits **squarely on this axis**. It is the only `003408a` thread that has zero dependency on the rest of the cluster -- it can be cherry-picked or retyped manually as a 10-line patch to `hooks.py` regardless of the D, E, A, or B decisions. Net Q4 win; trivial cost.

**Thread (iii) -- DEFAULT_ROLE in `mcp.py`:**

| Q | Verdict |
|---|---------|
| Q1 | no -- the silent "type omitted" path is a real ambiguity (untyped vs DEFAULT_ROLE). |
| Q2 | no -- `spawn_agent type=` is an MCP tool kwarg; documented; new sentinel value is additive. |
| Q3 | YES -- depends on `DEFAULT_ROLE` existing in `claudechic.workflows.agent_folders`, which is sub-feature B's territory. |
| Q4 | yes (positive) -- "Before: `spawn_agent` with no type silently emits a warning toast about generic agents. After: the agent type is set to the sentinel `DEFAULT_ROLE` and the warning explains that role-scoped rules will not apply." |
| Q5 | partial -- if engine-seam adopts B's DEFAULT_ROLE constant only, an alternative is to reuse the `type or "default"` shape inline in `mcp.py` without importing the symbol. Less clean; defeats the point. |
| Q6 | no |

Composability note: engine-seam owns this thread (it is downstream of the B decision).

### Composability verdict (CONTEXT ONLY -- user decides)

The prior `spec_guardrails_seam.md` proposed `(003408a-ii, adopt, none)` and "coordinate-with-engine-seam" on (i)/(iii). I keep the same shape and surface to the user as a follow-up question rather than a team verdict, per UserAlignment D4:

> **Follow-up question for the user** (to be surfaced at synthesis): after the accf332 cluster decisions land, do you want a follow-up investigation on re-picking `003408a`? The historian's V1 finding shows re-trigger risk is NONE. The 10-line warn-message rewrite (thread ii) is fully decoupled and could ship on this axis even if engine-seam declines threads (i) and (iii).

---

## Cross-cutting findings

### Data/UI seam (Q1)

**Yes, the seam is clean.** Three pieces of evidence:

1. `digest.py` imports only `claudechic.guardrails.rules` (sibling) and stdlib (`dataclasses`, `typing`). No UI imports. Pure function.
2. `widgets/modals/guardrails.py` imports `GuardrailEntry` under `TYPE_CHECKING` only. At runtime it accepts `entries: list[GuardrailEntry]` from any caller; it never imports `compute_digest`.
3. The cross-seam types are durable: `GuardrailEntry` (frozen dataclass) for data flow downward; `GuardrailToggled(rule_id, enabled)` (frozen `Message` subclass) for events flowing upward.

**Adoptability matrix:**

| Half adopted | Status |
|--------------|--------|
| data only (`digest.py`) | adoptable as a leaf; today has no caller, hence dead weight |
| UI only (`GuardrailsModal`) | does not stand alone -- needs entries from somewhere |
| both | full feature |
| neither | status quo |

**Where would `compute_digest()` plug in?** Today: only the `on_guardrails_label_requested` handler in `app.py` (which `a60e3fe` then stubs out). On our base: it has no consumer. The only sane way to actually use the data layer in isolation is to add a `/guardrails` slash command at ~30 LOC. That's the prior spec's "middle path" recommendation; I reaffirm that even the middle path fails Q4 today (no documented user asking for it).

### GuardrailToggled persistence semantics (Q2)

**Confirmed: option (a) -- ephemeral session state.**

Read of accf332's `app.py` `on_guardrail_toggled` (before `a60e3fe` stubbed it):

```python
def on_guardrail_toggled(self, event) -> None:
    """Handle checkbox toggle in guardrails modal."""
    if event.enabled:
        self._disabled_rules.discard(event.rule_id)
    else:
        self._disabled_rules.add(event.rule_id)
```

That is the entire handler. Three observations:

1. **No write to `disabled_ids`**: nothing touches `self.config` or the project-tier YAML. The toggle vanishes at process exit.
2. **No interaction with our `disabled_ids`**: nothing reads `self.config.disabled_ids` to seed `_disabled_rules` either. The two lifecycle layers do not talk.
3. **No persistence schema change**: `_disabled_rules: set[str]` is initialized empty in `ChatApp.__init__` (line 319 of accf332's app.py). No on-disk file format change.

**Assessment:** this introduces a **second disable mechanism** that does not duplicate `disabled_ids` exactly -- it adds a session-ephemeral layer above the persistent layer. Whether that is justified depends on the user's view, but the cluster as shipped is silent on the relationship. From the composability lens: this is a hole. Two layers without explicit composition rules invite confusion ("I disabled it from the modal but it came back" / "I disabled it in `disabled_ids` but the modal shows it as enabled"). If we ever adopt D, we should pick ONE shape:

- **Collapse:** modal toggle writes to `disabled_ids`; persistent. Lose session-ephemeral capability; gain coherence.
- **Layered:** modal toggle is session-ephemeral; hook semantics: `skip_if_in(disabled_ids) OR skip_if_in(_disabled_rules)`; modal seeds `_disabled_rules` from `disabled_ids` on open and shows "persistent: yes/no" badge per row. More complex; closes the hole.

The accf332 cluster does neither. **This axis recommends: do not adopt the ambiguous shape.**

### Info-modal merge interaction (Q3)

**The Guardrails button is NOT semantically dependent on the info-modal merge.** Verified by reading abast's footer.py:

- `InfoLabel` ("info") -> opens `ComputerInfoModal` (which abast renamed conceptually but kept the class name; absorbs the diagnostics content)
- `GuardrailsLabel` ("guardrails") -> opens `GuardrailsModal`
- `EffortLabel` ("effort: high") -> cycles effort

Two separate buttons, two separate modals, two separate handlers in `app.py`. The "Info modal absorbs diagnostics" merge is a UI-surface concern (UI-surface axis owns it). The Guardrails button is a parallel addition.

The info modal does NOT absorb anything guardrail-related: read of accf332's `widgets/modals/computer_info.py` (lines 73-100) shows the sections are: Host, OS, Python, SDK, claudechic, CWD, Session JSONL, Last Compaction. No "list of active rules" appears. So the data-side digest does not need to feed two places; it only ever feeds the modal.

**Implication:** D's adopt/skip decision is independent of UI-surface's decision on the diagnostics-deletion / info-modal merge. We can skip D without disturbing UI-surface, and vice versa. No coupling.

### a60e3fe interpretation (Q4)

**Most likely: interpretation (a)** -- they hit a UX or correctness bug. Three pieces of evidence:

1. **Timing.** Cluster commits 1->4 took 20 minutes total (`accf332` at 17:27, `a60e3fe` at 17:47). Twenty minutes is consistent with "open the modal, see it look broken or crash, stub it."

2. **Code smells in the modal that would be visible at first run:**
   - `Checkbox.BUTTON_INNER = " "` is monkey-patched on each row instance (line 67 of abast's `widgets/modals/guardrails.py`). It mutates a class attribute from an instance method -- standing footgun.
   - The checkbox ID format `f"gr-cb-{e.id}"` and the parsing `cb_id[len("gr-cb-"):]` assume rule IDs are valid widget ID fragments. Our rule IDs include qualified names like `project-team:pip_block` which contain `:`. Textual widget IDs do not allow `:` -- this would raise on first attempt to mount a row for any namespaced rule. accf332's `defaults/global/rules.yaml` has only unqualified IDs (`no_rm_rf`, `warn_sudo`, etc.), so the first-render bug would only fire when a workflow with namespaced rules is active.
   - `_GuardrailRow` uses `Horizontal` with a fixed `height: 1` and four child widgets (Checkbox, Static badge, Static id, Static reason). Textual's default Checkbox height is >1 in many themes; visual overflow is plausible.

3. **No tests added for the modal in `8f99f03`.** The test commit (commit 2 of the cluster) updates 6 test files but adds zero tests for `digest.py`, `GuardrailsModal`, or `_disabled_rules`. The `digest` module gets no coverage. If the author tested the feature, they did so manually.

I cannot rule out interpretations (b) "wanted to ship the wiring without the user feature" or (c) "missing dep on a later commit", but (a) is the most likely. There is no in-tree TODO referencing another module.

**Composability lens:** under (a), the right action is to skip D and let abast finish it before we adopt. Under (b), the right action is to skip the user-visible half but consider the data half (which is what the prior spec proposed). Under (c), the right action is to wait for the abast follow-up. **All three readings converge on "skip D for now."**

### 003408a messaging-seam analysis (Q5)

The commit subject says "improve guardrail and advance-check messaging to prevent agent retry loops." The user-visible delta after re-pick:

- **Warn rules** (in `hooks.py` thread ii): the agent gets three additional paragraphs of explanation in the block reason text -- "this warning was implemented by the user...", "before proceeding, reason about the user's intent", "generally, you should use tools as intended." This addresses the failure mode where the agent immediately calls `acknowledge_warning` and retries without thinking.

- **Manual-confirm advance checks** (in `checks/builtins.py`, `ManualConfirm.check`): the failure evidence changes from `"User declined"` to a paragraph telling the agent to *converse* with the user before retrying -- "Ask the user what needs to be addressed before advancing. Do not rerun this tool in an attempt to advance before having a conversation with the user." This addresses the retry-loop where the agent calls `advance_phase` again immediately after a user decline.

- **Subprocess cwd pinning** (in `checks/builtins.py`, the new `cwd`/`base_dir` ctor params): not user-visible per se; a robustness fix. The reported error string for `CommandOutputCheck` failure does change to include `(cwd=...)` in the evidence, which helps debugging.

- **DEFAULT_ROLE handling in `mcp.py`**: not user-visible directly; changes the warning text for `spawn_agent` without `type=` to be explicit about role wiring.

**Verifying the test coverage from `8f99f03`:** the rewritten `test_main_agent_role_resolves_to_main_role` (Test 13) explicitly exercises the `default -> main_role -> default` round-trip via `_activate_workflow` and `_deactivate_workflow`. This is the exact case that the original `18061ec` revert cited as broken on our base. The renamed `test_agent_type_defaults_to_default_sentinel` covers the new sentinel default. So if we re-pick `003408a` after `accf332`, the previously-stranded tests pass under `accf332`'s machinery.

**Conclusion:** the `003408a` re-pick on the `messaging` seam (thread ii in `hooks.py` and the `ManualConfirm` rewrite in `checks/builtins.py`) is the lowest-risk, highest-Q4 portion of the commit. Per the user's D4 rule, this remains a **flagged context** finding for the user to decide on as a follow-up.

### Stowaway rule independence (Q6)

**Confirmed: E is fully standalone.** The 7-line YAML record uses only:

- `id` (existing)
- `trigger: PreToolUse/Bash` (existing)
- `enforcement: warn` (existing)
- `detect.pattern` (existing)
- `message` (existing)

It does NOT reference any symbol or check-type that only exists in accf332. The detect pattern is a regex; the message is a literal string. Adoption mechanic: append the 7 lines to `claudechic/defaults/global/rules.yaml`.

The adopt/skip decision for E is **independent of D's UX outcome and of accf332's other sub-features**. Recommend: adopt as a manual append. (Cherry-pick will fail context match because abast's diff context references `no_pip_install`, which is in their pre-accf332 file but not in our `defaults/global/rules.yaml`.)

Caveat (from Skeptic's review): the regex shares the false-positive shape of `no_bare_pytest`. Recommend tightening (see E section above). Not a blocker for adoption.

---

## Terminology refinements

For the Terminology axis to fold into the working glossary:

1. **`digest`** = the result of evaluating each loaded `Rule`/`Injection` against a snapshot `(active_wf, agent_role, current_phase, disabled_rules)`, producing `list[GuardrailEntry]` annotated with `active: bool` + `skip_reason: str`. **Static snapshot, not a live subscription.** Computed on demand by `compute_digest`. Consumes hints? **No -- guardrails only** (`Rule` + `Injection`); hints are a separate axis with their own state store. Note for the final report: a "guardrails" modal that shows guardrails-only is honest but partial -- a user looking for hint introspection would be confused.

2. **`_disabled_rules` (accf332, in-memory) vs `disabled_ids` (ours, persistent)** -- two distinct lifecycle layers. Recommendation: do NOT adopt `_disabled_rules` in this cluster sync. If a future user request demands an introspection feature, prefer the persistent path (`disabled_ids`) over inventing a session-ephemeral layer. If session-ephemeral is genuinely needed later, name it `runtime_disabled_rule_ids` and document the layered semantics explicitly. Either way, **one or the other, not both silently.**

3. **`GuardrailToggled`** is a Textual `Message` subclass on the modal -> app channel. Two attrs (`rule_id: str`, `enabled: bool`). Frozen dataclass. **Persistence semantics: ephemeral (per question Q2).** If the user-checkpoint approves D, this naming is fine; if D is skipped, this name vanishes from our codebase.

4. **`GuardrailEntry`** is the per-rule/per-injection digest record. 12 fields including the `tier` provenance, scope metadata (roles/exclude_roles/phases/exclude_phases), and the `active`/`skip_reason` annotation. Public surface from `claudechic.guardrails.digest` (if D-data is adopted). If D-data is skipped, this name is not introduced.

5. **InfoLabel / GuardrailsLabel rename** (footer): UI-surface axis owns. From this axis: the rename does not affect guardrails functionality. Do NOT couple this axis's D-skip recommendation to UI-surface's rename decision.

6. **Workflow-context scoping of the digest**: `digest.py` takes the active agent's `(role, phase, active_wf)` -- so the modal shown to the user is implicitly main-agent-specific. With multi-agent setups (sub-agents with different `agent_type`), the modal does not show per-sub-agent views. Note for documentation; not a blocker.

---

## New collisions discovered

Three findings beyond what `leadership_findings.md` and the prior `spec_guardrails_seam.md` documented:

1. **`get_disabled_rules` callback is added by BOTH `accf332` AND `003408a`.** Both commits independently add the same callback parameter to `create_guardrail_hooks(...)` with the same `Callable[[], set[str]]` signature. (Sources: accf332's `claudechic/guardrails/hooks.py` change is the same shape as `003408a`'s.) **Implication:** if both `003408a` and `accf332` are picked, the second cherry-pick will conflict on `hooks.py`. Order matters: pick `003408a` first (smaller patch) then `accf332` (which would conflict only on the callback line, easy resolution); or pick `accf332` first then `003408a` (which becomes a partial reapply of the same change). Either way, the hooks.py change should land **once**, not twice. **This axis flags this as a coordination point with the cherry-pick playbook.** (Note: this collision was not explicit in the historian's findings; the historian listed both as touching `hooks.py` but did not call out that they make the same callback addition.)

2. **`agent.agent_type` resolution path is shared between sub-features B and D.** Sub-feature B introduces dynamic `agent_type` (DEFAULT_ROLE -> main_role on activation); sub-feature D's modal handler reads `agent.agent_type` to compute the digest's role-skip column. **Implication:** D-modal's user-visible quality depends on B being live. Without B (i.e., on our current base where `agent.agent_type` is `None` for the main agent), D-modal would show every role-scoped rule as "role 'None' excluded" -- functional but uninformative. **This axis flags D as having a soft dep on B.** Engine-seam owns the B decision.

3. **`a60e3fe` leaves `_disabled_rules` initialized to empty set with no mutator.** The hook still consults `_disabled_rules` (because the `get_disabled_rules` callback is wired in `_guardrail_hooks` and a60e3fe doesn't touch that wiring), but no UI ever flips it. **Implication:** on `abast/main` HEAD, the runtime-disable mechanism is end-to-end functional but unreachable. Dead-but-correct code. If we adopt the cluster as-is (including a60e3fe), we inherit the dead-but-correct shape. **This axis flags this for the cherry-pick playbook:** if D is adopted with a60e3fe, prune the `_disabled_rules` attribute and the `get_disabled_rules` callback during conflict resolution to match -- otherwise we ship dead code.

---

## Per-feature recommendation summary

| Feature | Outcome | Blocking deps | One-line reason |
|---------|---------|---------------|-----------------|
| **D guardrails UI -- modal** | **skip** | -- | Q1 (no concrete user) + Q4 (no one-sentence delta) + Q5 (slash command is 30 LOC vs 186-line modal); abast's own `a60e3fe` walk-back is the cluster's clearest intent signal that the UI is not ready. |
| **D guardrails UI -- data layer (`digest.py`)** | **skip / defer** | -- | Clean leaf; no caller; adopting infra without users is cargo-culting. Reimplement as `/guardrails` slash command (~30 LOC) when a user actually asks. |
| **D guardrails UI -- runtime-disable plumbing in `hooks.py`** | **skip** | follows D | Without the modal, nothing flips `_disabled_rules`; the wiring is dead weight. |
| **D guardrails UI -- footer label rename** | **owned by UI-surface** | n/a | This axis defers to UI-surface; D-modal skip is independent of the rename decision. |
| **E `pytest_needs_timeout` warn rule** | **adopt (manual append)** | none | 7-line YAML record, uses only existing infra, real Q4 win. Cherry-pick context fails (refs abast's `no_pip_install` we lack); manual append is cleaner. Recommend hardening regex to anchor executable boundary. |
| **(flagged) `003408a` re-pick** | **CONTEXT ONLY (no team verdict per UserAlignment D4)** | none for thread ii; thread iii depends on B | Thread ii (warn-message rewrite in `hooks.py`) is decoupled from the cluster, ~10 lines, Q4 win, no deps. Thread i (per-check `cwd`/`base_dir`) is mostly subsumed by accf332's engine-level `params.setdefault("cwd", ...)`. Thread iii (DEFAULT_ROLE in `mcp.py`) is downstream of engine-seam's B decision. Surface to user as follow-up question: "after the cluster lands, do you want a follow-up investigation on `003408a`?" |

---

*End of guardrails-seam axis Specification deliverable (second pass).*
