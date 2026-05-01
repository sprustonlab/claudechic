# Historian Findings — abast accf332 cluster

**Author:** historian agent
**Date:** 2026-04-29
**Phase:** Specification (triage pass)
**Cluster scope (approved by coordinator):** the 4 commits below; everything else is FLAG-only.

| # | SHA (full) | Time | Subject | Files | +/- |
|---|------------|------|---------|-------|-----|
| 1 | `accf332df9e3f1a9c13e5951bec1a064973b6c96` | 2026-04-26 17:27:45 -0400 | feat: add workflow template variables, dynamic roles, effort cycling, and guardrails UI | 30 | +975 / -279 |
| 2 | `8f99f035…` (`8f99f03`) | 2026-04-26 17:27:48 -0400 | test: update tests for template variables, engine checks, and widget refactor | 6 | +567 / -79 |
| 3 | `2f6ba2e…` (`2f6ba2e`) | 2026-04-26 17:28:00 -0400 | docs: update file map with guardrails, digest, and modal changes | 1 | +11 / -3 |
| 4 | `a60e3fe…` (`a60e3fe`) | 2026-04-26 17:47:16 -0400 | chore: stub out guardrails modal with not-yet-implemented notice | 1 | +2 / -36 |

All four are by Arco Bast; all are descendants of merge-base `285b4d1` ("feat: add clear finished tasks button to TodoPanel sidebar"), which is also the merge-base of our HEAD `a2c3779`.

---

## Triage pass

### 1. Per-commit summary and sub-feature attribution

The user-named features are:
- **A.** workflow template variables (`$STATE_DIR`, `$WORKFLOW_ROOT`)
- **B.** dynamic roles (main agent promoted to `main_role` on activation, demoted on deactivation, no SDK reconnect)
- **C.** effort cycling (model-aware effort label in footer)
- **D.** guardrails UI (new GuardrailsModal + DiagnosticsModal merged into unified InfoModal)

Plus a small fifth item the commit body discloses but the user didn't name:
- **E.** new `pytest_needs_timeout` warn rule in `defaults/global/rules.yaml` (not really part of the cluster's headline feature set; treat as a stowaway).

**Commit 1 (`accf332`) — the feature itself.** Implements ALL of A–E in one commit. Sub-feature breakdown by file:
- A: new `claudechic/paths.py` (+30, `compute_state_dir`, `WORKFLOW_LIBRARY_ROOT` = `~/.claudechic/workflow_library/`); `workflows/engine.py` adds `workflow_root`/`state_dir` ctor params and uniform `$STATE_DIR`/`$WORKFLOW_ROOT` expansion in `_run_single_check`; `workflows/agent_folders.py` adds a `variables` kwarg to `assemble_phase_prompt` + `create_post_compact_hook` (uniform `str.replace` expansion); `defaults/workflows/project_team/project_team.yaml` and the role markdowns are rewritten to use `$STATE_DIR`/`$WORKFLOW_ROOT`; `defaults/workflows/tutorial/tutorial.yaml` similarly.
- B: `agent.py` defaults `agent_type` to the new `"default"` sentinel string (not `None`); `workflows/agent_folders.py` declares `DEFAULT_ROLE = "default"`; `workflows/loader.py` rejects manifests with `main_role: default`; `agent_manager.py` passes the `Agent` instance into the options factory so guardrail hooks can read `agent.agent_type` dynamically (this is the key trick that lets the role flip without reconnect); `app.py` (the +282) holds the activation/deactivation flow that promotes the main agent to `main_role` and reverts on deactivation.
- C: `widgets/layout/footer.py` adds the new `EffortLabel` (model-aware levels: opus → low/med/high/max, sonnet/haiku → low/med/high), wires it into `StatusFooter`; `agent.py` adds `self.effort = "high"` instance attr; `styles.tcss` minor.
- D: NEW `widgets/modals/guardrails.py` (+186) — `GuardrailsModal` listing rules/injections with toggle checkboxes, emits `GuardrailToggled`; NEW `claudechic/guardrails/digest.py` (+128) — `compute_digest()` returns the per-agent active/skipped rules+injections list consumed by the modal; DELETED `widgets/modals/diagnostics.py` (-194); `widgets/modals/computer_info.py` is rewritten to absorb the diagnostics content (renamed conceptually to "Info modal"); `widgets/modals/base.py` adds scrollable sections (+66); `widgets/layout/footer.py` renames `DiagnosticsLabel→InfoLabel` and `ComputerInfoLabel→GuardrailsLabel` (button repurposing — same labels, different action); `app.py` wires `on_guardrails_label_requested` → `GuardrailsModal` with digest+toggle plumbing (NB: this handler is later stubbed out by commit 4).
- E: `defaults/global/rules.yaml` (+7) — adds `pytest_needs_timeout` warn rule.

**Commit 2 (`8f99f03`) — tests for the feature.** Updates 6 test files. Notably:
- `tests/test_engine.py` (+462/-…) — the bulk; tests for the new `state_dir`/`workflow_root` ctor params and `$STATE_DIR`/`$WORKFLOW_ROOT` expansion in checks.
- `tests/test_phase_injection.py` (+128/-?) — renames `test_agent_type_defaults_to_none` → `test_agent_type_defaults_to_default_sentinel`, asserts new behaviour `agent.agent_type == DEFAULT_ROLE`; rewrites Test 13 to "main agent is promoted to main_role on workflow activation" with explicit `default → main_role → default` round-trip; fixes `repo_root` path (`parents[3]` → `parents[1]`) and switches global/workflows dirs to `claudechic/defaults/...` — i.e. tests are aware of the `defaults/` package layout introduced earlier.
- `tests/test_widgets.py` (+20) — touches widget tests for the rename/addition.
- `tests/test_workflow_guardrails.py` (+18), `test_workflow_hits_logging.py` (+6), `test_app_ui.py` (+12).
- Sub-feature attribution: covers A, B, D primarily; mention of "widget refactor" maps to D's modal renames; nothing test-side for C (effort cycling).

**Commit 3 (`2f6ba2e`) — docs.** Single file: `CLAUDE.md` file-map. Adds the entire `claudechic/guardrails/` block (digest.py, hits.py, hooks.py, parsers.py, rules.py, tokens.py) and rewrites the `widgets/modals/` block: removes `diagnostics.py`, adds `guardrails.py`, retitles `computer_info.py` to "system info + session diagnostics (info button)". Pure documentation of changes already implemented in commit 1. Sub-feature attribution: D (guardrails UI / modal restructure) — the `guardrails/` package documented here is mostly pre-existing on our base (we already have `hits.py`, `hooks.py`, `parsers.py`, `rules.py`, `tokens.py` — see "Surface area" below); only `digest.py` is new from accf332.

**Commit 4 (`a60e3fe`) — partial walk-back of D.** Single file: `claudechic/app.py`. Replaces the entire `on_guardrails_label_requested` handler (and its companion `on_guardrail_toggled`) with a `self.notify("Guardrails viewer not yet implemented")`. The IMPORT/CALL of `compute_digest` and the `GuardrailsModal` push is GONE. Critically: the `GuardrailsModal` widget file and the `digest.py` module are NOT deleted by commit 4 — they remain in the tree as dead code on `abast/main`. So D ships in a *half-built* state on `abast/main`: the data plumbing exists, the modal class exists, but the button click is a no-op stub. Sub-feature attribution: walks back the runtime surface of D while leaving the supporting machinery in place. **Open question for Leadership: did the author hit a UX bug, or was this a feature flip waiting on something else?** No commit message detail beyond "stub out... with not-yet-implemented notice."

### 2. Inter-commit dependency edges

```
accf332 ───► 8f99f03         (tests assert behaviour introduced by accf332)
accf332 ───► 2f6ba2e         (docs document files added/deleted by accf332)
accf332 ───► a60e3fe         (a60e3fe edits a handler ADDED by accf332; cannot apply on bare base)
```

- `8f99f03` strictly depends on `accf332` (imports `DEFAULT_ROLE` from `agent_folders`; expects new ctor params on `WorkflowEngine`; expects renamed widgets).
- `2f6ba2e` is text-only (CLAUDE.md) and could in principle apply standalone but would document files that don't exist; semantically depends on `accf332`.
- `a60e3fe` strictly depends on `accf332` — it edits the `on_guardrails_label_requested` handler that `accf332` introduced. On our base the handler does not exist yet.
- No back-edges: nothing in `accf332` depends on the later three.

**Cherry-pick ordering (if adopted):** `accf332` → `8f99f03` → `2f6ba2e` → `a60e3fe`. Skipping `a60e3fe` is viable if Leadership wants the *full* GuardrailsModal exposed (i.e. inherit the not-yet-shipped UI rather than the stub). Skipping `2f6ba2e` is viable if our CLAUDE.md has already drifted (it has — see Surface area).

### 3. Top-3 most architecturally invasive changes in `accf332` (by blast radius on our base)

I rank these by `(diff size on our side since merge-base) × (centrality of the symbol)`. All three sit in modules where our side has independently evolved heavily.

1. **`claudechic/app.py`** — `accf332` adds +282 lines (new handlers `on_guardrails_label_requested`, `on_guardrail_toggled`, `on_info_label_requested`, effort wiring, dynamic-role activation flow). Our side has diverged by **+779 lines** on the same file since the merge-base. Concretely: our side ALREADY has `_activate_workflow`, `main_role` plumbing, `_token_store`, and a guardrails-rules pipeline (lines 401, 826, 833, 855, 1655, 1787, 1928, 1935, 2168, 2168, 2203, 2216, 2344, 2412, 3731). This is a near-certain conflict with substantial human merge work required. **Blast radius: maximum.**

2. **`claudechic/workflows/loader.py`** — `accf332` adds only +16 lines (the `main_role: default` rejection). Our side has diverged by **+891 lines** on the same file. The rejection block imports `DEFAULT_ROLE` from `agent_folders` — which does not exist on our base anymore (was reverted via `ec604bc`). Small upstream patch, but lands in a heavily rewritten file: the merge will be mechanical but must be verified against our independent loader evolution. **Blast radius: high (because of our drift, not because of the patch).**

3. **`claudechic/workflows/engine.py`** — `accf332` adds +64 lines (the `workflow_root`/`state_dir` ctor params, the two-pass auto-then-manual check execution, uniform `$STATE_DIR`/`$WORKFLOW_ROOT` expansion, the `cwd`/`base_dir` defaults pinned to `workflow_root`). Our side has diverged by **+198 lines** on the same file. This is the *substantive* part of feature A, and it interacts directly with the previously-reverted `003408a` (which also pinned check `cwd` — see the flagged-dependency findings). **Blast radius: high; this is the convergence point with the prior failed cherry-pick.**

Honourable mentions (would be #4–#6):
- `claudechic/widgets/layout/footer.py` (+121 in accf332; +25 in our drift) — the `EffortLabel` plus the `DiagnosticsLabel→InfoLabel` / `ComputerInfoLabel→GuardrailsLabel` repurposing. Tractable but the rename creates ID conflicts with our footer code.
- `claudechic/workflows/agent_folders.py` (+26 in accf332; **-90/+? in our drift after the `DEFAULT_ROLE` revert** — net +90 vs merge-base) — adding `DEFAULT_ROLE` here is the prerequisite reintroduction the revert anticipated.
- DELETION of `claudechic/widgets/modals/diagnostics.py` — this file is **still present** on our HEAD; the deletion will appear as a normal git rm during cherry-pick.

### 4. Flagged-dependency findings (003408a / 1d3f824 / our reverts)

This is the most important finding of the triage and warrants Leadership attention before committing to a full pass.

- **`003408a` (abast precursor: "improve guardrail and advance-check messaging")** — touches `claudechic/checks/builtins.py` (adds the `_resolve_against` helper and `cwd: str | Path | None = None` ctor param to `CommandOutputCheck`) and `claudechic/mcp.py` (uses `DEFAULT_ROLE`, per the revert message). `8abb2f9` is our cherry-pick of it; `18061ec` reverts it on 2026-04-28 because "003408a transitively depends on prior abast role-resolution-refactor commits NOT included in §6.1 (specifically the `DEFAULT_ROLE` sentinel, the `main_role` promotion path on workflow activation, and the broadcast-on-advance-to-typed-sub-agents subsystem)."
  - **Verdict:** `accf332` IS the commit that introduces all three of those prerequisites (`DEFAULT_ROLE` in `agent_folders.py`; the dynamic `main_role` promotion via `agent.agent_type` flip; and the two-pass auto+manual advance check ordering — though I should flag I have not yet fully verified the broadcast-on-advance subsystem is part of *this* commit specifically vs. an earlier one in the abast role-refactor lineage; that's a thorough-pass item).
  - **Implication:** if Leadership adopts `accf332`, the previously-reverted `003408a` becomes coherent and could be re-cherry-picked AT THE SAME TIME without re-triggering the test failures. The 6 stranded `tests/test_phase_injection.py` tests cited in `18061ec` are precisely the ones that `8f99f03` updates and expects to pass under `accf332`'s machinery (e.g. the renamed `test_main_agent_role_resolves_to_main_role` Test 13).
  - **Hard dep?** `accf332` does NOT import or depend on `003408a`'s `_resolve_against` helper or `CommandOutputCheck.cwd` param — it independently introduces a similar pinning via `WorkflowEngine` defaulting `params["cwd"]` to `workflow_root` at the engine level. So `accf332` works WITHOUT `003408a`. But the two are complementary: `003408a` does it at the `CommandOutputCheck` level (more robust to non-engine callers), `accf332` does it at the engine level. Re-applying `003408a` after `accf332` would be additive, not duplicative. **Re-trigger risk: NONE on the originally-reverted basis — the prerequisites are now present.** A new risk surfaces: accf332's engine-level `params.setdefault("cwd", ...)` and 003408a's ctor `cwd=` param interact (engine-level wins via `setdefault` if 003408a's ctor default is `None`). I'd want the Implementer to verify the precedence behaviour matches expectations, but no test breakage is anticipated.

- **`1d3f824` (our forward-port of `DEFAULT_ROLE`)** — single 12-line addition to `claudechic/workflows/agent_folders.py` declaring `DEFAULT_ROLE = "default"`. Reverted as part of `ec604bc` because once `003408a` was reverted, `DEFAULT_ROLE` had no caller and triggered an unused-import F401.
  - **Verdict:** `accf332` re-introduces `DEFAULT_ROLE` at the same line in the same file with the same value (`"default"`) and identical comment wording. **If we cherry-pick `accf332`, `1d3f824`'s effect is automatically restored — and now actually used (by the loader rejection rule, by `agent.py`'s default, by tests, etc.).**
  - **What broke last time:** ONLY the orphan-import lint error (no behavioural breakage). With `accf332`, the import has multiple callers and the lint error vanishes.
  - **Re-trigger risk: NONE.**

- **`ec604bc` (our combined revert + `_token_store` restoration)** — reverts `1d3f824` AND restores `self._token_store = OverrideTokenStore()` at `app.py:1564` that was accidentally dropped during the `8e46bca` conflict resolution. The `_token_store` restoration is independent of the cluster — it's a standing bug-fix to our prior conflict resolution and **must be preserved** through any future cherry-pick of `accf332`.
  - **Verdict:** ALL of `accf332`'s `app.py` edits will land on top of the post-`ec604bc` `app.py` which includes `self._token_store = OverrideTokenStore()` at the relevant location. The Implementer must verify the conflict resolution does not re-drop this line. Our HEAD currently has it (verified at line 1655 of `app.py`).

**Bottom line for the flagged-dependency picture:**
- `accf332` does not require `003408a` to apply, but it makes `003408a`'s re-application safe and possibly desirable.
- `accf332` makes `1d3f824` redundant by re-introducing `DEFAULT_ROLE` natively.
- `ec604bc`'s `_token_store` restoration is independent of the cluster; preserve it during any merge.

### 5. "Needs your eye" list — areas where Leadership disagreement is likely

Listed by likelihood of inter-agent disagreement:

1. **Should commit 4 (`a60e3fe`) be adopted?** It walks back the user-visible part of feature D. Adopting it ships a stub button labelled "guardrails" that says "not yet implemented" while leaving the modal class and digest.py orphaned in the tree. SKIPPING it ships the full GuardrailsModal even though abast deemed it not ready. This is the cluster's clearest *intent* signal — abast halted the rollout — and the team's call should be deliberate, not implicit.

2. **Should we reimplement vs. cherry-pick?** Our `app.py` has diverged by 779 lines since merge-base, much of it independent evolution of `_activate_workflow` / `main_role` / `_token_store`. A naive cherry-pick will conflict heavily and require human merge work that effectively *is* a reimplementation of feature B on top of our base. Skeptic and Composability are likely to disagree on whether to (a) accept the merge cost, (b) reimplement B from scratch using our existing activation machinery, or (c) take A+C+D and skip B.

3. **Per-feature outcome split.** I expect the team to converge on:
   - A (template variables): adopt — small, contained, big readability win for workflow YAMLs.
   - B (dynamic roles): adapt — our base has parallel machinery; need to merge, not paste.
   - C (effort cycling): adopt — clean, isolated, no conflict path.
   - D (guardrails UI): partial/skip — abast itself didn't ship it; pulling in dead code is a smell.
   - E (pytest_needs_timeout rule): adopt — stowaway, trivial.
   But I'd flag this as "likely consensus, verify don't assume."

4. **Re-cherry-pick `003408a`?** Adopting `accf332` makes `003408a` newly applicable. The team must decide: (a) re-cherry-pick `003408a` separately as a follow-up, (b) include it in the same patch series, or (c) skip it on grounds that `accf332`'s engine-level `cwd` pinning supersedes it. UserAlignment may want the user's call here since the original revert came with a "spec amendment dispatch" obligation.

5. **`tests/test_phase_injection.py` — verify the stranded 6 tests actually pass under `accf332` + `8f99f03`.** The revert message lists them by name; `8f99f03` rewrites at least Test 13 and the `test_agent_type_defaults_to_*` test. TestEngineer should run these explicitly post-merge to confirm the prediction. If any do NOT pass, the cluster is not as self-sufficient as the data suggests.

6. **`computer_info.py` rewrite.** Our HEAD's `computer_info.py` may have diverged from the merge-base version (didn't inspect this file in detail in triage). The rewrite in `accf332` absorbs the diagnostics content; if our side has independent edits there, that's another conflict surface. Flag for thorough pass.

7. **Window of attention re: out-of-scope abast commits between #3 and #4.** Per the coordinator's flag-only directive, I have not investigated `1d6d432` (tell_agent merge) or `ff1c5ae` (rename ask_agent → message_agent). Noting: both touch `claudechic/agent.py`, `claudechic/mcp.py`, and many test files — i.e. some of the SAME files our cluster touches. Cherry-pick ordering of the cluster IS independent of these refactors (the cluster touches different concerns), but if the team later considers cherry-picking the MCP refactors, the order matters and I would want to investigate then.

---

## Surface area on our base — quick map

Merge-base = `285b4d1` ("feat: add clear finished tasks button to TodoPanel sidebar").
Our HEAD = `a2c3779` ("fix(test): WorkflowPickerScreen mount race on Windows CI").

**Files `accf332` touches × divergence on our side since merge-base:**

| File | accf332 ∆ | Our drift | Notes |
|------|-----------|-----------|-------|
| `claudechic/app.py` | +282/-? | **+779/-?** (heavily evolved) | Highest-conflict file; we already have `_activate_workflow`, `main_role`, `_token_store`. |
| `claudechic/workflows/loader.py` | +16 | **+891/-?** | Massive independent evolution; small upstream patch. |
| `claudechic/workflows/engine.py` | +64 | **+198/-?** | Substantive feature A; convergence point with reverted 003408a. |
| `claudechic/workflows/agent_folders.py` | +26 | -90 net relative (post-revert) | `DEFAULT_ROLE` reintroduction; previously reverted. |
| `claudechic/widgets/layout/footer.py` | +121 | +25 | EffortLabel addition + label renames; modest conflict. |
| `claudechic/agent_manager.py` | +6 | +29 | `agent=` param to options factory; small. |
| `claudechic/agent.py` | +8 | +11 | `DEFAULT_ROLE` default + `effort` attr; small. |
| `claudechic/defaults/workflows/project_team/project_team.yaml` | +6 | +102 | `$STATE_DIR` rewrite of a heavily-evolved file. |
| `claudechic/defaults/workflows/project_team/coordinator/setup.md` | +6 | +17 | `$STATE_DIR` text rewrite. |
| `claudechic/defaults/global/rules.yaml` | +7 | +31 | Stowaway `pytest_needs_timeout` rule. |
| (plus 8 other small role-md files) | minor each | unknown | Clean wins likely. |
| **NEW** `claudechic/paths.py` | +30 | (absent — clean add) | Clean apply. |
| **NEW** `claudechic/guardrails/digest.py` | +128 | (absent — clean add) | Clean apply. |
| **NEW** `claudechic/widgets/modals/guardrails.py` | +186 | (absent — clean add) | Clean apply. |
| `claudechic/widgets/modals/computer_info.py` | rewritten | unknown | Need to verify drift. |
| `claudechic/widgets/modals/base.py` | +66 | unknown | Scrollable section infra; flag for thorough pass. |
| **DELETE** `claudechic/widgets/modals/diagnostics.py` | -194 | STILL PRESENT | Will git-rm cleanly unless we have edits. |
| `claudechic/styles.tcss` | +10 | unknown | Probably clean. |

**Pre-existing on our HEAD (relevant for overlap):**
- `claudechic/guardrails/` package: has `__init__.py`, `hits.py`, `hooks.py`, `parsers.py`, `rules.py`, `tokens.py`. **MISSING:** `digest.py` (introduced by accf332).
- `claudechic/app.py` already has: `_token_store`, `_activate_workflow`, `main_role` from manifest, guardrails wiring at lines 826/833/855/1655.
- `claudechic/workflows/agent_folders.py`: `DEFAULT_ROLE` constant ABSENT (reverted via `ec604bc`).

---

## Flagged out-of-scope commits (per scope guard — NOT investigated)

These were observed during triage but NOT analysed; flagged for Leadership awareness only:

- `003408a` (abast) — fix: improve guardrail and advance-check messaging. Deeply relevant to our cluster (see §4 above); this commit precedes accf332 by 4 minutes and is the precursor to the failed cherry-pick on our side. **Recommend Leadership decide whether to re-investigate as a follow-up companion.**
- `1d6d432` (abast) — refactor: merge tell_agent into ask_agent with requires_answer kwarg. Sits chronologically between cluster commits #3 and #4 on `abast/main`. Touches `claudechic/agent.py`, `claudechic/mcp.py`, and many test files. **No action.**
- `ff1c5ae` (abast) — refactor: rename ask_agent → message_agent. Same shape as above. **No action.**
- `7dcd488` (abast HEAD) — feat: testing sub-cycle with Generalprobe standard. Workflow-content-only (16 markdown files in `defaults/workflows/project_team/`). **No action.**

---

## What a thorough pass would add

If Leadership greenlights the full ~1.5 hr pass, I would deliver:
1. Line-by-line attribution of `app.py`'s 282-line accf332 patch against our 779-line drift, identifying specific conflict regions and proposed resolutions.
2. Verification that `accf332`'s machinery actually unbreaks the 6 named tests in `tests/test_phase_injection.py` (currently a strong inference, not verified).
3. A second check: does `accf332` introduce the "broadcast-on-advance-to-typed-sub-agents" subsystem cited in `18061ec`'s revert message? (I have not confirmed this is in *this* commit specifically.)
4. Full cherry-pick playbook (commit-by-commit): which conflicts to expect per file, which can be auto-resolved, which need human merge, which need our ec604bc-style fixups preserved.
5. A drift map for `widgets/modals/computer_info.py` and `widgets/modals/base.py` (skipped in triage).

---

*End of triage. Awaiting Leadership decision on (a) full thorough pass, (b) per-feature outcome category proposals to bring to Specification.*

---

## Verification pass

Two narrow follow-ups requested by coordinator after Leadership review of triage. Total time: ~15 min.

### V1. Is broadcast-on-advance in `accf332` specifically?

**Answer: NO. Broadcast-on-advance is NOT in accf332. It already lives on our base (and on abast's base — both forks have it via shared pre-merge-base history).**

Evidence:
- `accf332` does NOT touch `claudechic/mcp.py` or `claudechic/guardrails/hooks.py`. The only broadcast/advance/typed-sub-agent mention in the entire `accf332` diff body is a comment fragment in `workflows/engine.py:1927-1928` that *references* sub-agent advance ("avoids false negatives when advance_phase is called by a sub-agent whose cwd or subprocess environment has drifted") — that's the engine's `cwd` pinning rationale, not the broadcast subsystem itself.
- The broadcast subsystem lives on our base in `claudechic/mcp.py` lines 927, 960, 967, 970, 991, 1005 — explicit comments and the `_broadcast_assemble` helper.
- It was introduced on our base (and shared with abast) by:
  - `66fa580` "feat: broadcast phase prompt to all agents on advance_phase"
  - `ca003a3` "fix: sub-agent phase injection — broadcast on advance, store agent_type, remove name fallback (#37)"
  Both pre-date merge-base `285b4d1`, so both forks already have the machinery.

**Implication for the cluster:** of the 3 prerequisites cited in our `18061ec` revert message (DEFAULT_ROLE sentinel, main_role promotion, broadcast-on-advance to typed sub-agents), only TWO are introduced by `accf332` (the first two). The third is already on our base. This **strengthens** the §4 conclusion: re-applying `003408a` after `accf332` is safe because all three prerequisites are then satisfied (two via accf332, one already present). It also reduces the dependency footprint of accf332 itself — there is no broadcast-subsystem code to merge or worry about.

### V2. Drift map for `widgets/modals/computer_info.py` and `widgets/modals/base.py`

**Answer: ZERO drift on both files since merge-base. Clean apply expected.**

| File | accf332 ∆ | Our drift since `285b4d1` | Conflict assessment |
|------|-----------|---------------------------|---------------------|
| `claudechic/widgets/modals/computer_info.py` | +68/-? | **0 commits, 0 lines changed** | Clean apply. accf332 rewrites this to absorb the diagnostics content; we have not edited it independently. |
| `claudechic/widgets/modals/base.py` | +66 | **0 commits, 0 lines changed** | Clean apply. accf332 adds scrollable section infrastructure; we have not edited it. |

Verification command: `git log --oneline 285b4d1..HEAD -- claudechic/widgets/modals/computer_info.py claudechic/widgets/modals/base.py` returns empty.

**Implication for the cluster:** the UI-side surface area of feature D (`guardrails UI`) is much cleaner than the engine seam. Aside from the heavy `app.py` conflicts (where the handler wiring lives), the modal-restructure portion is essentially a textbook clean cherry-pick: 3 new files (`paths.py`, `guardrails/digest.py`, `widgets/modals/guardrails.py`) are pure additions; `widgets/modals/computer_info.py` is a clean rewrite; `widgets/modals/base.py` is a clean addition; `widgets/modals/diagnostics.py` is a clean deletion (we have not edited it either). The hard part of D is *only* the `app.py` handler wiring (and even that gets stubbed out by commit 4 if we adopt it).

---

*End of verification pass. Standing down per coordinator instruction. Available for targeted git questions from Specification-phase axis-agents.*

---

## Full divergence map (user-redirect 2026-04-29)

User scope expansion: "include ANY commit that is divergent between our repos as context." This section is research-only — no adopt/skip recommendations.

**Inputs:**
- merge-base = `285b4d1` ("feat: add clear finished tasks button to TodoPanel sidebar")
- `abast/main` HEAD = `7dcd488e`
- our HEAD = `a2c3779`

**Totals:**
- abast-only since merge-base: **16 commits**
- ours-only since merge-base: **42 commits**

**Tag legend:**
- `C` = in the 4-commit cluster
- `D` = direct dependency / strong relevance to the cluster (e.g. `003408a` and our reverts)
- `M` = might inform cluster decisions (touches related files / similar concepts / already-cherry-picked from abast)
- `-` = unrelated to the cluster

### Tag distribution

| Side | C | D | M | - | Total |
|------|---|---|---|---|-------|
| abast-only | 4 | 1 | 6 | 5 | 16 |
| ours-only | 0 | 5 | 16 | 21 | 42 |

### Part A: abast-only commits since merge-base (oldest first)

| SHA | Date | Type | Subject | Files | +/- | Tag |
|-----|------|------|---------|-------|-----|-----|
| `d55d8c0` | 2026-04-21 | feat | bundle default guardrails, hints, and workflows with fallback discovery | 88 | +6069/-2 | M |
| `8e46bca` | 2026-04-22 | fix | use resolved workflows_dir instead of hardcoded path | 1 | +5/-2 | - |
| `0ad343b` | 2026-04-22 | chore | pin anthropic to 0.79.0 for fast-mode support | 1 | +1/-1 | - |
| `f9c9418` | 2026-04-22 | feat | full model ID selection with merge helper and loosened validation | 4 | +317/-14 | M |
| `7e30a53` | 2026-04-22 | feat | "auto" permission mode to Shift+Tab cycle | 6 | +31/-16 | - |
| `5700ef5` | 2026-04-22 | feat | default to auto permission mode on startup | 12 | +78/-78 | - |
| `26ce198` | 2026-04-22 | feat | /fast command for priority processing mode | 4 | +87/-1 | - |
| `9fed0f3` | 2026-04-22 | docs | clarify spawn_agent type= parameter for workflow role matching | 2 | +6/-6 | M |
| `003408a` | 2026-04-26 | fix | improve guardrail and advance-check messaging to prevent agent retry loops | 3 | +167/-36 | D |
| `accf332` | 2026-04-26 | feat | workflow template variables, dynamic roles, effort cycling, and guardrails UI | 30 | +975/-279 | C |
| `8f99f03` | 2026-04-26 | test | tests for template variables, engine checks, and widget refactor | 6 | +567/-79 | C |
| `2f6ba2e` | 2026-04-26 | docs | file map update | 1 | +11/-3 | C |
| `1d6d432` | 2026-04-26 | refactor | merge tell_agent into ask_agent with requires_answer kwarg | 28 | +86/-114 | M |
| `ff1c5ae` | 2026-04-26 | refactor | rename ask_agent to message_agent | 28 | +134/-141 | M |
| `a60e3fe` | 2026-04-26 | chore | stub out guardrails modal with not-yet-implemented notice | 1 | +2/-36 | C |
| `7dcd488` | 2026-04-26 | feat | testing sub-cycle with Generalprobe standard | 16 | +363/-42 | M |

#### Part A — relevance notes for tagged commits

- `d55d8c0` (M, +6069 lines) — the foundational `defaults/` package bundling on the abast side. accf332 modifies many files inside `defaults/workflows/...` that this commit established. Our base independently arrived at a similar `defaults/` layout via Group A (`711be4c`); the two organisations are similar but not identical, and the cluster's `defaults/...` edits will have to land on top of *our* layout, not abast's.
- `f9c9418` (M) — full model ID selection. Already on our base via `720fa08`. Relevant because effort cycling in cluster commit `accf332` is *model-aware* (different effort levels for opus vs sonnet vs haiku); the model code underlies feature C.
- `9fed0f3` (M) — docs for `spawn_agent type=` parameter. Already on our base via `68024b3`. The role-matching concept underlies dynamic roles (cluster B).
- `003408a` (D) — covered in §4 of triage. Cherry-picked as `8abb2f9`, reverted as `18061ec`. accf332 makes it re-applicable.
- `1d6d432` + `ff1c5ae` (M) — MCP refactor (tell_agent merge + ask_agent → message_agent rename). Sit chronologically *between* cluster commits 3 and 4 on `abast/main`. Already on our base as `cf18c70` + `90c46e0` (with our own fixup `178e3dc` to restore tell_agent semantics that were lost in the rename). Relevant: both touch `claudechic/mcp.py` and the same agent/test files the cluster touches; cherry-pick ordering would have mattered if these were not already absorbed.
- `7dcd488` (M, abast HEAD) — adds workflow content (markdown) to `defaults/workflows/project_team/`. Already on our base as `65a6c78`. Same file-tree as cluster touches; no logic conflict but content overlap.
- `8e46bca`, `0ad343b`, `7e30a53`, `5700ef5`, `26ce198` (-) — already on our base or orthogonal to cluster (`8e46bca`=`00a34f2`, `7e30a53`=`2e2f98f`, `5700ef5`=`1e46230`; `0ad343b` and `26ce198` are dep pin and `/fast` feature, neither cluster-relevant).

### Part B: ours-only commits since merge-base (oldest first)

| SHA | Date | Type | Subject | Files | +/- | Tag |
|-----|------|------|---------|-------|-----|-----|
| `2675eb6` | 2026-04-21 | test | failing tests for bugs #12, #14, #16 (TDD red phase) | 3 | +352 | - |
| `7b9b3d7` | 2026-04-21 | fix | bugs #12, #14, #16 — guardrail detect field defaults, colon encoding, UTF-8 sessions | 4 | +67/-48 | - |
| `4d77fb1` | 2026-04-21 | fix | Windows compat — encoding="utf-8" + os.kill platform guards | 13 | +254/-21 | - |
| `b95313a` | 2026-04-21 | fix | test_bug16 uses encode_project_key for correct Windows path encoding | 1 | +2/-10 | - |
| `317f424` | 2026-04-23 | feat | consolidate into single pip-installable package | 166 | +12991/-260 | M |
| `711be4c` | 2026-04-27 | refactor | Group A restructure — move engine + bundled content under `defaults/` | 124 | +80/-63 | M |
| `b9023e2` | 2026-04-27 | refactor | Group B boundary relocation — state files .claude/ → .claudechic/ | 17 | +89/-57 | M |
| `6d7d919` | 2026-04-27 | feat | parallel `.claudechic/` worktree symlink (SPEC §10) | 2 | +192/-3 | M |
| `45912c2` | 2026-04-27 | test | pre-cherry-pick guard for default_permission_mode='auto' | 1 | +36 | - |
| `68024b3` | 2026-04-22 | docs | clarify spawn_agent type= parameter (cherry-pick of abast `9fed0f3`) | 2 | +6/-6 | M |
| `00a34f2` | 2026-04-22 | fix | use resolved workflows_dir (cherry-pick of abast `8e46bca`) | 1 | +1/-2 | - |
| `720fa08` | 2026-04-22 | feat | full model ID selection (cherry-pick of abast `f9c9418`) | 4 | +317/-14 | M |
| `1e46230` | 2026-04-22 | feat | default to auto permission mode (cherry-pick of abast `5700ef5`) | 12 | +80/-76 | - |
| `2e2f98f` | 2026-04-22 | feat | "auto" permission mode (cherry-pick of abast `7e30a53`) | 5 | +23/-12 | - |
| `8abb2f9` | 2026-04-26 | fix | guardrail and advance-check messaging (cherry-pick of `003408a`) | 3 | +173/-52 | D |
| `1d3f824` | 2026-04-27 | fix | forward-port DEFAULT_ROLE sentinel for cherry-pick `003408a` | 1 | +12 | D |
| `18061ec` | 2026-04-28 | revert | Revert `8abb2f9` (the `003408a` cherry-pick) | 3 | +52/-173 | D |
| `ec604bc` | 2026-04-28 | revert | Revert `1d3f824` + restore lost `_token_store` init | 2 | +1/-12 | D |
| `29f98bb` | 2026-04-28 | checkpoint | Group C WIP — tier field added to Rule/Injection/HintDecl/CheckDecl | 3 | +23/-2 | M |
| `81f0c69` | 2026-04-28 | feat | 3-tier loader with override-by-id resolution (Group C) | 12 | +1736/-273 | M |
| `d001e30` | 2026-04-28 | feat(group-d) | claudechic-awareness install + in-memory phase-prompt delivery | 14 | +1253/-180 | M |
| `e4fa9bf` | 2026-04-28 | feat(group-e) | workflow artifact directory mechanism | 9 | +1112/-15 | M |
| `f5b7225` | 2026-04-28 | feat(group-g) | settings UI + workflow-picker tier badges + configuration reference | 14 | +2802/-8 | - |
| `efc94ed` | 2026-04-28 | refactor | consolidate `${CLAUDECHIC_ARTIFACT_DIR}` substitution into shared helper | 4 | +46/-30 | M |
| `0e4b2e4` | 2026-04-28 | test | E2E Group D × Group E seam + INV-AW-SDK-1 stub | 3 | +552 | - |
| `3dc0ffd` | 2026-04-28 | test | INV-DF-1/2/3/7 + close_leadership role-scope + phase_context broad-scan | 4 | +459/-4 | - |
| `06e2caf` | 2026-04-28 | docs | refresh post-implementation; release-notes for independent_chic | 4 | +131/-23 | - |
| `7ac2a3b` | 2026-04-29 | fix(workflows) | confirm before overwriting an existing chicsession | 2 | +602/-20 | M |
| `f885cb0` | 2026-04-29 | feat(chicsession) | sort picker by mtime + show relative timestamps | 2 | +66/-10 | - |
| `b60a090` | 2026-04-29 | fix(screens) | harden label rendering and toggle bindings | 3 | +41/-12 | - |
| `20c7792` | 2026-04-29 | fix(mcp) | get_phase lists only items that can fire under active workflow | 2 | +208/-6 | M |
| `fdc9f5f` | 2026-04-29 | feat(engine) | from_session_state surfaces missing artifact-dir to UI | 1 | +14 | M |
| `9fc7337` | 2026-04-29 | test(loader) | mixed bare + tier-targeted disable_workflows entries | 1 | +66 | M |
| `65a6c78` | 2026-04-26 | feat | testing sub-cycle with Generalprobe (cherry-pick of abast `7dcd488`) | 16 | +363/-42 | - |
| `cf18c70` | 2026-04-29 | refactor | merge tell_agent into ask_agent (cherry-pick of abast `1d6d432`) | 28 | +86/-114 | M |
| `90c46e0` | 2026-04-26 | refactor | rename ask_agent to message_agent (cherry-pick of abast `ff1c5ae`) | 28 | +134/-141 | M |
| `178e3dc` | 2026-04-29 | fix(workflows) | restore tell_agent semantics lost in message_agent rename | 16 | +71/-69 | M |
| `a743423` | 2026-04-29 | fix(test) | `test_main_agent_role_resolves_to_main_role` mismatched tool_name | 1 | +7/-2 | D |
| `1e2db37` | 2026-04-29 | fix(config) | new-install path missing worktree + experimental defaults | 1 | +5/-1 | - |
| `3ac11b2` | 2026-04-29 | fix(test) | two pre-existing Windows-only flakes | 2 | +12/-1 | - |
| `fd42c3c` | 2026-04-29 | fix(test) | symlink comparison via os.path.samefile (Windows) | 1 | +9/-7 | - |
| `a2c3779` | 2026-04-29 | fix(test) | WorkflowPickerScreen mount race on Windows CI | 1 | +14/-2 | - |

#### Part B — relevance notes for tagged commits

D-tagged (5 commits — strong cluster relevance):
- `8abb2f9`, `18061ec` — our cherry-pick + revert of `003408a`. Covered in §4.
- `1d3f824`, `ec604bc` — our DEFAULT_ROLE forward-port + revert. Covered in §4.
- `a743423` — **NEW finding for axis-agents.** This commit fixes `test_main_agent_role_resolves_to_main_role`, which is one of the 6 tests that the `18061ec` revert message cited as stranded. Our base ALREADY has a working version of this test (post-MCP-rename), and the commit message confirms the test "now correctly exercises what its docstring promises" by showing "the main agent's role resolved to the workflow's main_role ('coordinator')". **Implication:** our base independently has functional main-role-resolution machinery, separate from accf332's promotion path. The engine-seam axis-agent should inspect what mechanism we use vs. what accf332 introduces, since they may collide rather than compose.

M-tagged ours-only (16 commits — context for axis-agents):
- `317f424` (+12991, M) — single-pip-installable-package consolidation. Touches everything; sets up file-tree shape that cluster patches will land into.
- `711be4c` (M) — Group A restructure to `defaults/`. **Our equivalent of abast's `d55d8c0`.** Both forks arrived at a `defaults/` package layout independently — comparing them is the engine-seam axis-agent's first task.
- `b9023e2`, `6d7d919` (M) — Group B state-file relocation to `.claudechic/` and parallel worktree symlink. **State-location overlap with cluster's `~/.claudechic/workflow_library/<project_key>/...`** (Terminology §5.4).
- `68024b3`, `720fa08`, `cf18c70`, `90c46e0` (M) — cherry-picks of abast commits already on our base. Mentioned for completeness.
- `81f0c69` (+1736, M) — **3-tier loader (Group C).** This is the +891-drift on `workflows/loader.py` that triage §3 flagged. Direct collision surface with cluster's loader patch.
- `d001e30` (+1253, M) — **claudechic-awareness install + in-memory phase-prompt delivery.** "in-memory phase-prompt delivery" is OUR mechanism in the same conceptual space as cluster's dynamic-role-on-activation prompt re-injection. Engine-seam axis-agent should compare.
- `e4fa9bf` (+1112, M) — **Group E workflow artifact directory mechanism.** This is the `${CLAUDECHIC_ARTIFACT_DIR}` substitution mechanism (Terminology §5.2 collision). Cluster adds `$STATE_DIR` / `$WORKFLOW_ROOT` (no braces). Two-syntax-world risk lives here.
- `efc94ed` (M) — consolidates `${CLAUDECHIC_ARTIFACT_DIR}` substitution into a shared helper. The substitution helper accf332 would either extend or duplicate.
- `7ac2a3b` (+602, M) — chicsession-overwrite confirmation. Touches `chicsessions/` concept (Terminology §5.4 — workflow_library vs chicsessions vs artifact-dir).
- `178e3dc` (M) — local fixup restoring tell_agent semantics lost in the MCP rename. Worth axis-agent awareness because cluster commits 3 and 4 sit on either side of the abast rename, and our base has the rename already.
- `20c7792`, `fdc9f5f`, `9fc7337`, `29f98bb` (M) — small loader/engine/get_phase work that touches the same files cluster touches.

Unrelated (-) — 21 ours-only commits — Windows compat, bug fixes, settings UI, release docs, test additions, new-install config; not on cluster's surface area. Listed in the table above for completeness; no per-commit narrative.

---

*End of full divergence map. Standing down again. Axis-agents may consult for any deeper drilldown into specific commits flagged D or M.*
