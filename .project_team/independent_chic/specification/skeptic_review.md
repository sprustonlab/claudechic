# Specification Phase — Skeptic Review

**Author:** Skeptic (Leadership lens — completeness, correctness, simplicity, in that order)
**Phase:** Specification (entered)
**Inputs reviewed:**
- `vision.md` (binding) and `STATUS.md` §"Locked decisions" (L1–L17 + A1–A12)
- `userprompt.md` Leadership-resolution round (Q1–Q9)
- Sister lenses: `composability_eval.md` (10 axes, 7 work groups, 10 holes), `terminology_glossary.md`, `alignment_audit.md`, my own `risk_evaluation.md` (23 risks)
- Codebase reads: `workflow_engine/loader.py`, `config.py`, `hints/state.py`, `hints/triggers.py`, `app.py` (phase_context sites), `features/worktree/git.py:293–301`, `mcp.py` discovery surface

**Charge from phase prompt:** challenge assumptions in the vision; identify risks and failure modes; distinguish essential complexity from accidental; flag shortcuts disguised as simplicity; flag designs with more than 2 moving parts; check for complexity carried over from prior simplifications.

**This document is rationale, not spec (per L14).** The spec phase will produce two files: an operational spec (Implementer + Tester can execute without reading anything else) and an appendix (rationale, decisions, rejected paths). This review feeds the appendix.

---

## 1. Frame

The user has done substantial simplification work in the Leadership-phase resolution round. **A8** dropped a brittle cherry-pick. **A9** dropped startup warnings. **A7** softened L3 from absolute to primary-state-only. **A12** allowed the spec phase to postpone smaller features.

These are *user-driven simplifications*. The spec phase's job is to honor them, not to re-introduce them under new names. The dominant Skeptic risk in this phase is **complexity carryover** — over-engineering that survives a simplification by being shuffled rather than removed. §6 below has the carryover watchlist.

---

## 2. Assumption challenges (going into spec)

### AS-1 — "Restructure first" is a *preference*, not a constraint

Vision §"Open for the new team to decide" #1 expresses a user preference: restructure → cherry-pick → #23/#24. STATUS calls this "the working assumption."

**Challenge:** Is the preference load-bearing for the whole spec, or is it just the path-of-least-resistance? **Answer: it is load-bearing for `9fed0f3`, `8e46bca`, and `f9c9418` cherry-picks**, because all three touch paths or imports that the restructure changes. If the spec re-orders, those cherry-picks land at the wrong paths or against unmoved imports. **Action for spec:** state explicitly that restructure precedes cherry-picks, name the cherry-picks that depend on restructure-first (`9fed0f3`, `8e46bca`, plausibly `f9c9418`), and name those that don't (`5700ef5`, `7e30a53` are mostly orthogonal — they touch `agent.py`, `agent_manager.py`, `app.py`, `commands.py`, `footer.py`, none of which are in the file-move inventory).

### AS-2 — A4's "non-destructive touches in `.claude/` are permitted" hides a category problem

A7 + A4 read together: claudechic *primary state* must not live inside `.claude/`. *Incidental, non-destructive touches* are permitted *if* the team is confident they're non-destructive and cross-platform.

**Challenge:** What is "non-destructive"? Three interpretations exist, only one is testable:

| Interpretation | Testable? | Risk |
|---|---|---|
| (i) "Doesn't overwrite a Claude-owned file" | Yes — by name list | Spec must enumerate the Claude-owned filename set. Without the list, the test is a judgment call. |
| (ii) "Creates a file with no semantic effect on Claude's behavior" | No — semantic | Untestable; subject to drift as Claude changes. |
| (iii) "Reverts cleanly on uninstall" | Partly — needs uninstall path | Implies an uninstall surface that doesn't exist. |

**Action for spec:** pick (i). Enumerate the Claude-owned file/dir set claudechic must not overwrite (`.claude/settings.json`, `.claude/settings.local.json`, the existing files under `.claude/rules/` that the user owns, `.claude/hooks/*`, `.claude/skills/*`, `.claude/commands/*`). Any write outside that set, into `.claude/`, is a permitted A7 touch *if* it also satisfies "claudechic-namespaced filename" (e.g., `claudechic-` prefix or under `.claude/claudechic/`). **Without an enumerable test, A7 is a "trust me" rule and the boundary lint can't enforce it** — see §3 R-S1.

### AS-3 — A4's "no symlinks" prohibition rules out the simplest fix for BF7

The vision File-move inventory §"Worktree symlink (BF7)" prescribes: add a parallel `.claudechic/` symlink at `features/worktree/git.py:293–301` next to the existing `.claude/` symlink.

**A4 prohibits symlinks** — "not supported on Windows." The existing `.claude/` symlink at the same site is *also* a symlink; A4 doesn't repeal it (the existing symlink is Claude's namespace, not claudechic's, so A4 doesn't apply directly), but it does make BF7's prescribed fix impossible.

**Challenge:** What replaces the symlink for `.claudechic/` propagation across worktrees? Three options:
- **(a) Bind-mount / hardlink** — Linux/macOS only, worse than symlinks for Windows.
- **(b) `git worktree add` post-hook copies `.claudechic/` into the new worktree** — works cross-platform but creates *divergent state* (each worktree has its own copy; user-tier `~/.claudechic/` is fine but project-tier `.claudechic/` becomes stale after the first edit).
- **(c) Each worktree has fresh per-worktree `.claudechic/`, no propagation** — simplest, but breaks user expectation that "settings carry over."

**Action for spec:** pick (c) and document the behavioral break, OR pick (b) and document the divergence problem and how user resolves it (e.g., the worktree's `.claudechic/` is a git-tracked subset; user-tier overrides plug holes). **The spec must commit and explain.** Punting to "the team decides" leaves the worktree feature in undefined state. This is a known consequence of A4; surface it explicitly.

### AS-4 — "Cross-pollination" (A10) is wording, not architecture

A10 reframes the abast relationship from "convergence" to "bidirectional cross-pollination." The user's intent is clear (it's a relationship, not a one-way pull program). But the spec is being asked to author file-move inventory + cherry-pick instructions, which are by nature one-way *for this run*. Future cross-pollination is hypothetical.

**Challenge:** Does A10 require any *operational* spec change, or is it pure language?

**Action for spec:** treat A10 as a language-level grep (no occurrences of "convergence," "merge program," "align abast onto our layout" in spec/docs/UI prose). Add it to the L14 self-check artifact (§5). **Do not** invent a "cross-pollination protocol" document — that's accidental complexity. The relationship is interpersonal; the operational deliverable is the cherry-pick set.

### AS-5 — A12 ("postpone if scope balloons") needs an explicit yes/no per item

A12 lets the spec phase postpone Issue #23's smaller features (welcome-screen access to settings, workflow-ID discovery for `disabled_workflows`, disabled-IDs listing, settings-button vs `/settings`-command parity). User says "fine to postpone if too much" but also "let the team decide."

**Challenge:** A12 is permissive but ambiguous. The risk is **silent inclusion** — the spec writes "we'll do all of it" without checking scope, and the implementation phase carries unmarked features.

**Action for spec:** for each smaller feature listed in #23, the spec must explicitly say "in scope this run" or "postponed, rationale: ..." with no third option. Items not listed in the spec are *implicitly out of scope* and should not appear in the implementation phase. Without the explicit bookkeeping, A12's "let the team decide" decays into "the team didn't decide and now we're shipping it anyway."

---

## 3. Spec-output risks and failure modes

These are risks specific to the spec *artifact* (the document the spec phase will produce), not to the underlying code. Each must be guarded against during spec authorship.

### R-S1 — A7 boundary-lint becomes a "trust me" check

| Severity | High (L10.d) |
|---|---|
| Likelihood | H without explicit enumeration |

If the spec says "boundary lint catches L3 violations except for non-destructive touches per A7" and *does not name what counts as non-destructive*, the lint either:
- Becomes lenient (allows any `.claude/` write that "looks claudechic-owned") — A7 violations slip through.
- Becomes strict (allows nothing in `.claude/`) — A4 permitted-touches blocked, defeating A7.

**Mitigation:** spec must include an *allowlist* — concrete file path patterns under `.claude/` that claudechic may write to, with a one-line justification per pattern. Example shape (the spec author picks the actual content):

```
allowed_in_claude_namespace:
  - pattern: ".claude/claudechic/**"
    justification: "claudechic-owned scratch space, prefix-namespaced"
  - pattern: ".claude/settings.json"
    justification: NEVER — this is Claude-owned, A4 prohibits overwrite
```

The lint reads the allowlist; anything else in `.claude/` is a finding. **The allowlist itself must be in the spec, not in a commit message or an appendix paragraph.** Operational.

### R-S2 — Spec ships a 6-item "agent awareness" plan when 1 item suffices

| Severity | High (over-engineering, L14 trap) |
|---|---|
| Likelihood | H (Composability already drafted Group D as 6 items D1–D6) |

The Composability lens decomposes "agent awareness" into D1 (spec the mechanism) + D2 (always-on injection) + D3 (first-read injection) + D4 (move phase_context to same family) + D5 (decide ContextDocsDrift fate) + D6 (decide /onboarding context_docs phase fate). That's six items.

**Skeptic challenge:** Hole 5 in `composability_eval.md` is the key insight: phase_context delivery and A3 agent awareness are *the same problem* — file-based content delivered to Claude from a `.claudechic/` location at session start. They want one mechanism, not two.

**The minimal moving-parts shape:**
1. **A SessionStart hook** that, at every session start, reads from `<repo>/.claudechic/rules/*.md` and `<repo>/.claudechic/phase_context.md` (if present), and injects all of them as system prompt content.
2. **A short `append_system_prompt` paragraph** for the always-on awareness statement (L15 piece 1) — could even live inside one of the rules files, eliminating one piece.
3. **A PreToolUse hook on `Read`** for the once-per-agent first-read fuller injection (L15 piece 2).

Items D5 (ContextDocsDrift) and D6 (`context_docs` phase) are *removals*, not features. They should not be steps in a "what to build" plan; they should be a single line in the spec: "Delete `claudechic/hints/triggers.py:25-…` (`ContextDocsDrift` class) and `claudechic/workflows/onboarding/onboarding_helper/context_docs.md`; remove the corresponding hint from `defaults/global/hints.yaml` and the phase reference from `defaults/workflows/onboarding/onboarding.yaml`."

**Action for spec:** state the agent-awareness mechanism as 1 hook + 1 string, not 6 items. Removals are removals, not work items.

### R-S3 — Spec writes "tier provenance on every parsed item" when only workflows need it

| Severity | Med (accidental complexity) |
|---|---|
| Likelihood | M |

Composability §6 Group C item C3 says "Add tier provenance to every parsed item." The reason: G3 (workflow-button UI) needs to display where each workflow came from.

**Skeptic challenge:** G3 names *workflows* specifically. There's no UI surface for "which tier did this rule come from?" or "which tier did this hint come from?" — and there shouldn't be (rules and hints are not user-pickable; they apply silently).

**Minimal shape:** Track tier provenance only for workflows. For rules, hints, and MCP tools, the resolution is "highest tier wins by id" and the result is a flat list — no UI cares about provenance. Adding a `tier` field on every parsed object grows every dataclass and every test fixture; not free.

**Action for spec:** track tier provenance for workflows only. For other categories, resolve to a flat list and discard tier identity. If a future feature needs the provenance, add it then.

### R-S4 — Spec ships per-category `resolve()` method when one generic function suffices

| Severity | Med (accidental complexity) |
|---|---|
| Likelihood | M |

Composability §6 Group C item C4: "implement `resolve()` on each `ManifestSection[T]` parser. Workflows override by `workflow_id`; rules/hints override by `id`; mcp_tools override by `tool.name`."

**Skeptic challenge:** the four categories are identical *except* for which attribute is the identity unit. One generic function:

```python
def resolve_by_id(per_tier_items: dict[Tier, list[T]], key_fn: Callable[[T], str]) -> list[T]:
    """Project tier wins, then user, then package. Non-conflicting items accumulate."""
    by_id: dict[str, T] = {}
    for tier in (Tier.PACKAGE, Tier.USER, Tier.PROJECT):  # later tiers overwrite
        for item in per_tier_items.get(tier, []):
            by_id[key_fn(item)] = item
    return list(by_id.values())
```

Three lines of logic, one function. Each parser supplies its `key_fn` (one-line lambda); no per-parser `resolve()` method needed.

**Workflow override is slightly different** — Composability says "winning tier replaces the entire workflow definition AND its role/phase files." Even so: the entire workflow is one logical unit (the YAML manifest plus its sibling role-folder); resolving by `workflow_id` over `WorkflowData` records still uses the same generic resolver, and the role-folder lookup keys off `WorkflowData.path` which is set by the winner.

**Action for spec:** one `resolve_by_id` function, four `key_fn` definitions. No `ManifestSection.resolve` protocol method. The complexity is in the *data* (workflow vs rule has different identity), not in the *code* (the function is the same).

### R-S5 — Spec splits "restructure" into A1–A7 work units when one git mv batch suffices

| Severity | Low (cosmetic) |
|---|---|
| Likelihood | M |

Composability Group A has 7 sub-items: A1 (move 6 engine files), A2 (move 7 workflow YAML dirs), A3 (move 2 global files), A4 (move mcp_tools), A5 (update 22 imports), A6 (update 5 path refs), A7 (delete empty dirs).

**Skeptic challenge:** these are not independently testable. A4 alone breaks tests; A1+A5 together are the smallest unit that compiles. The spec should not pretend each is a standalone work item with its own gating.

**Action for spec:** present the restructure as one phase with one acceptance test ("after this batch, `pytest tests/ -n auto` passes"). The 7 sub-bullets can be a checklist *inside* the phase, but they are not separate gates.

### R-S6 — Spec attempts to verify "behavioral mirror" of `.claude/rules/` without naming the test

A3 (per A4 operationalization) says agent-awareness must "behave the same" as `.claude/rules/`. What does "the same" mean operationally?

**Concrete tests that would verify it:**

1. Place a sentinel directive in `.claudechic/rules/test_marker.md`: `"When the user asks 'what is the test marker?', reply with the literal string CHIC-TEST-7."`
2. Spawn a fresh agent in a project that has this file.
3. Send `"what is the test marker?"`.
4. Assert the response contains `CHIC-TEST-7`.

Run the same test with the file under `.claude/rules/` to confirm the comparison anchor works. If both pass, the mirror behaves equivalently. If only `.claude/rules/` works, A3 is not satisfied.

**Action for spec:** include this concrete test (or one isomorphic to it) as a Tester acceptance criterion. Without it, the Tester has no way to fail the implementation; "behavioral mirror" is a phrase, not a check.

### R-S7 — Spec mixes "operational" with "rationale" via passive omission (L14 trap, restated)

The L14 trap is well-known from the prior run. My `risk_evaluation.md` §R22 named the test: standalone-implementer test (can the Implementer act on the spec without opening the appendix?) and diff test (does each paragraph survive deletion of its first sentence as still-operational?).

**Spec phase will produce two files.** The appendix is allowed to mix things; the spec is not. **The way L14 fails most often is by *omission* — operational specificity that the author thought "any reasonable implementer would know," when actually the answer is in the rationale.** Examples to watch:

- "The boundary lint catches `.claude/` writes." — *What* counts as a write? *What* are the allowlist patterns? *Where* does the lint run (CI? pre-commit? both)? *What* file does it live in?
- "The 3-tier loader walks package then user then project." — *What* is the order semantics? Last-write-wins? First-non-error-wins? *Where* is the walk function?
- "Migrate hint state to `.claudechic/`." — *Move* the file? *Recreate* it? Per L17, no auto-migration — what about the existing `.claude/hints_state.json`? Leave it? Delete it? Document for the user? (A9 says no warnings — answer must be "leave it; user is on their own per L17.")

**Action for spec author:** the L14 self-check is not optional. It is a deliverable artifact. The grading rubric for the spec must require it.

---

## 4. Essential vs accidental complexity

Per the phase prompt: "If the user explicitly asks for X and X is complex, the complexity is essential."

### Essential (do not avoid)

| Item | Why essential |
|---|---|
| 3-tier override for {workflows, rules, hints, mcp_tools} | User asked for this in vision §1. The complexity is the user's requirement. |
| 2-tier config (separate from content tiering) | L8 explicit; the user wants config and content layered differently. |
| Boundary (L3 + A7 primary-state-only) | User requirement; tradeoff already negotiated. |
| Two-piece agent awareness (L15 + A11) | User said "two" explicitly. |
| Behavioral mirror of `.claude/rules/` (A3 + A4) | User requirement; tradeoff negotiated through A4 (no symlinks, no Claude-settings overwrite). |
| Cherry-pick set (A2/A8) | User decided. |
| Worktree state propagation (BF7) | User-feature; whatever shape it takes, the feature must work in worktrees. |
| L14 spec-vs-appendix split | User-binding (and the prior run's specific failure). |

### Accidental (eliminate)

| Item | Why accidental | What to do |
|---|---|---|
| Two parallel injection systems (one for phase_context, one for agent awareness) | They're the same problem (Hole 5). | Spec one mechanism. |
| Per-parser `resolve()` method | Four parsers do the same thing modulo `key_fn`. | One generic resolver, four `key_fn`s. |
| Tier provenance on every parsed item | Only workflows need it (G3 UI). | Track for workflows only. |
| Hand-curated cherry-pick of `d55d8c0` | A8 dropped this. | Confirmed gone. **Watch for re-introduction as "implement fallback discovery as a faithful re-creation of d55d8c0's logic" — see §6 below.** |
| 7 work units for "move files + update imports" | They're one batch with one test gate. | Present as one phase. |
| Per-platform symlink workarounds for BF7 | A4 prohibits symlinks. | Pick (b) or (c) from AS-3 and commit. |
| "Cross-pollination protocol" document | A10 is language; no operational deliverable required. | Don't author one. Add a string lint instead. |
| 6 items for agent awareness (Composability D1–D6) | 4 items are work, 2 are removals. Of the 4, D2+D4 collapse via Hole 5. | Spec as 1 hook + 1 prompt-append + 1 removal line. |
| Migration logic | L17 + A9 explicit. | Confirmed gone. **Watch for re-introduction as "we add a tiny detection-and-warn" — already considered and rejected (A9).** |
| "Trust-me" boundary lint without an allowlist | A7 demands the allowlist exists. | Allowlist in spec; lint reads it. |

---

## 5. Shortcuts disguised as simplicity

These are simplifications to *resist* — they remove apparent complexity but don't solve the user's actual requirement.

### SH-1 — "Use `additionalDirectories` and call it done"

**Tempting:** the SDK has an `additionalDirectories` option (per `composability_eval.md` §3 axis 6). Setting it to `~/.claudechic/rules/` looks like a file-based, auto-loaded mechanism. One-liner.

**Why it's a shortcut:** `additionalDirectories` adds directories to the agent's *read scope* (what it's allowed to access), not to the auto-loaded rule set. The agent doesn't *automatically* read those files; it can *choose* to. From the agent's perspective, this is not `.claude/rules/` behavior — `.claude/rules/` is auto-loaded into the system prompt without the agent doing anything. Skipping the hook step in favor of `additionalDirectories` does not satisfy A3.

**Detection:** R-S6 acceptance test (the sentinel directive) fails — the agent doesn't see the marker because it never read the file.

### SH-2 — "Just delete ContextDocsDrift, don't replace it"

**Tempting:** Composability D5 says retire it. R-S2 says it's a removal.

**Why it might be a shortcut:** the trigger answers a real user question — "do my installed claudechic context docs match the package version?" Under the new A3 mechanism, there are no "installed" docs (they live in `.claudechic/rules/` and are read directly), so there's nothing to drift from. **This is genuinely a removal** — the question disappears with the install step. **Not a shortcut**; flagging only because the spec might pause here unnecessarily.

### SH-3 — "Check primary-state writes only; assume incidental touches are fine"

**Tempting:** A7 says incidental touches are permitted. So just exempt them from the lint.

**Why it's a shortcut:** "Incidental" is not lint-friendly. Without an allowlist (R-S1), the lint either:
- Catches nothing in `.claude/` (over-permissive, drifts back to L3 violation).
- Catches everything in `.claude/` (matches strict L3, defeats A7).

The shortcut is to pick over-permissive and defer the question. The non-shortcut is to write the allowlist and update it as touches are added. Allowlist size is small — at most a handful of entries.

### SH-4 — "Test the loader produces a non-empty list"

**Tempting:** add a test like `assert load(project_root).workflows` and call resolution covered.

**Why it's a shortcut:** project-level fixture has at least one workflow (the project's own); test passes trivially. Doesn't verify *which tier won*. Override resolution is a logic that needs *adversarial* tests:

- Same workflow_id at all 3 tiers, different bodies — assert project's body wins.
- Same workflow_id at user + package, none at project — assert user's wins.
- Same workflow_id at package + project, partial role-folder at user — assert project's role-folder wins (or whatever the resolution rule says).

These are the tests R-S6 generalizes. Without them, the loader can have arbitrary bugs and the test suite is silent.

### SH-5 — "Defer the `disabled_workflows` cross-tier semantics question"

Composability Hole 8: "Project disables workflow `foo`. Does that disable `foo` at all tiers, or only at the project tier?"

**Tempting:** the natural answer is "at all tiers" (it's a feature toggle, not a content reference); leave it implicit.

**Why it's a shortcut:** implicit decisions in a multi-tier system grow into "feature X requires feature Y" coupling. The spec must say so. **Action: spec answers this in one sentence.**

### SH-6 — "Settings UI exposes whatever keys are easy"

A12 lets the spec phase postpone smaller features. **Tempting:** include only the keys that already have getter/setter logic and postpone the rest.

**Why it's a shortcut:** the user listed specific keys in vision §5 / issue #23. Postponing under A12 is fine *if recorded with rationale*. Selecting based on "which is easy to ship" without a rationale entry is the shortcut. Action: each in-scope key is named; each postponed key is named with a one-line rationale; nothing is silently dropped.

---

## 6. Carryover-complexity watchlist

The user simplified four times in the resolution round (A7, A8, A9, A12). The Skeptic-lens job here: check that the simplifications survive into the spec, not that they get re-introduced under another name.

### CW-1 — A8 dropped `d55d8c0`. Watch: "implement fallback discovery from scratch."

A8 says drop the cherry-pick because the loader-only extraction is brittle. The natural replacement is "re-implement fallback discovery from scratch as part of the restructure work."

**Risk:** "from scratch" silently means "carefully transcribe `d55d8c0`'s logic line by line into the new loader," reproducing the original cherry-pick's complexity by another name. The simplification A8 intended (avoid the brittle hand-extraction) gets undone by writing the *same* code under a different commit message.

**Action for spec:** the new loader's 3-tier walk is a *direct generalization* of the existing single-tier walk in `loader.py:117 discover_manifests`. Specifically:
- Today: `discover_manifests(global_dir, workflows_dir)` walks one global+workflows pair.
- New: `discover_manifests(tiers: list[(global_dir, workflows_dir)])` walks each pair, returns paths annotated with their tier.
- Resolution semantics live in §R-S4's generic `resolve_by_id`.

This is a small refactor of an existing function, not a re-creation of `d55d8c0`. **Spec should describe it that way.** If the spec invokes "fallback discovery" or "checks cwd first, falls back to bundled defaults" (the language of `d55d8c0`'s commit message), the carryover is happening; revise.

### CW-2 — A9 dropped startup warnings. Watch: "minimal one-line notice."

A9 forbids startup warnings for migration. It's tempting (per my own R21 in `risk_evaluation.md`) to say "but a one-line print is so cheap, let's add it anyway."

**Action for spec:** the spec contains *no* code path that prints anything migration-related at startup. The README/PR description may mention the manual `mv` commands as documentation; the running binary does not. Delineation is sharp.

### CW-3 — A7 softened L3. Watch: "two boundary tests" or "graduated severity."

A7 made L3 primary-state-only. The risk is that the spec interprets this as "we have two boundary tests now: a strict one for primary state and a lenient one for incidental touches" — which is two moving parts where one suffices.

**Action for spec:** one boundary test, with one allowlist (per R-S1). The allowlist is the only knob. There is no "graduated severity" — a write either matches the allowlist or it's a violation.

### CW-4 — A12 allowed postponement. Watch: silent inclusion.

Already covered by AS-5. The spec must enumerate the in-scope and postponed feature lists explicitly.

### CW-5 — Composability split work into 7 groups (A–G) totaling ~30 sub-items. Watch: spec adopts the decomposition without checking if items collapse.

`composability_eval.md` §6 has a fine-grained work breakdown. The Composability lens correctly identifies dependencies; what it does not do (it's not its job) is challenge whether each item is independently necessary. R-S2 / R-S3 / R-S4 / R-S5 are the consolidations Skeptic flags. **Spec author should treat Composability's group structure as a starting point, not a finished plan.** Several items collapse:

| Composability item | Skeptic note |
|---|---|
| C1 (cherry-pick d55d8c0) | DROPPED per A8. Remove from list. |
| D1–D6 (six items for awareness) | Collapses to 1 hook + 1 string + 1 removal line per R-S2. |
| C3 (tier provenance) | Workflows-only per R-S3. |
| C4 (per-parser resolve()) | One generic function per R-S4. |
| A1–A7 (seven file-move sub-items) | One phase, one test per R-S5. |
| F1–F5 (five cherry-picks) | Three are orthogonal one-liners; can be one PR with five commits. |

After consolidation: the spec is closer to **5 phases**, not 7 groups × ~30 items.

---

## 7. >2 moving parts → can it be 1?

Per phase prompt #5: "If a proposal has more than 2 moving parts, ask: can this be done with 1?"

| Proposal | Moving parts | Can it be 1? |
|---|---|---|
| Agent-awareness mechanism | SessionStart hook + PreToolUse hook + `append_system_prompt` + `phase_context` separate write site | **Down to 2:** SessionStart hook (handles always-on + phase_context together) + PreToolUse hook on Read (handles first-read-fuller-context). The "always-on" can be a fixed `.claudechic/rules/_baseline.md` read by the SessionStart hook; no separate `append_system_prompt` needed. |
| 3-tier override resolution | Tier walker + per-parser resolver + tier provenance + duplicate-id-error inversion | **Down to 1:** generic `resolve_by_id` post-pass over a dict-of-list-per-tier. Provenance is a single field on workflow records only. Duplicate-id within tier remains an error; across tier becomes the override mechanism. |
| Boundary enforcement | Static lint + runtime `can_use_tool` guard + allowlist | **Down to 2:** one lint that consults the allowlist (covers static violations); one runtime guard (covers tool-emitted writes that the static lint can't see). The allowlist is data, not a "moving part." |
| Worktree propagation | Symlink + post-hook copy + per-worktree fresh | **Down to 1:** pick one shape and commit. AS-3 above narrows to (b) or (c); the spec picks. |
| Boundary fix for `phase_context.md` | Move write site + update read mechanism + update unlink site | **Down to 1:** the agent-awareness SessionStart hook reads the file from its new `.claudechic/` location. The `app.py` write/unlink sites update path strings (mechanical). One mechanism. |

The minimal overall design has **two hooks** (SessionStart + PreToolUse), **one resolver function**, **one boundary lint with one allowlist**, **one runtime guard**, and **one decision per outstanding axis** (worktree, artifact-dir, etc). Nothing inherent to the user's requirements demands more.

---

## 8. Verifiability checklist for the spec

The spec is verifiable when an Implementer can execute it without discretion and a Tester can pass/fail it without judgment. Concrete questions the spec must answer with operational specificity:

- [ ] What is the exact path of the boundary-lint allowlist file? Answer it.
- [ ] What is the exact `key_fn` for each of the four content categories?
- [ ] Where does the SessionStart hook live (which file, which entry point in the SDK config)?
- [ ] Where does the PreToolUse hook live?
- [ ] How does the PreToolUse hook track "already-fired this agent session"? (In-memory dict keyed by what?)
- [ ] What is the exact filename pattern for `.claudechic/rules/*.md` files? (Subset? All `.md`? With a manifest?)
- [ ] What happens to the existing `~/.claude/.claudechic.yaml` if it exists when the user runs the new code? (A9: nothing. State explicitly.)
- [ ] What happens when the worktree's main `.claudechic/` is missing at worktree-add time?
- [ ] What is the exact assertion of the override-resolution test for each of the 6 scenarios in `risk_evaluation.md` R8?
- [ ] What is the sentinel-directive test (R-S6) phrased as a Tester acceptance criterion?
- [ ] Which `.claude/` paths are in the allowlist (per AS-2)?
- [ ] Which #23 smaller features are in scope this run (per AS-5)? Which are postponed with rationale?
- [ ] What is the exact list of `git mv` commands for the restructure phase?
- [ ] Which cherry-picks land before the restructure, which after, and why? (AS-1)

If any of these is missing from the spec, the spec is incomplete. The L14 self-check artifact must include a row for each, marked answered or N/A.

---

## 9. Top-3 spec-phase risks (for the user)

1. **Two parallel injection systems instead of one** (R-S2, CW-5): the spec adopts Composability's 6-item Group D verbatim without recognizing that phase_context delivery and A3 awareness are the same problem. Spec becomes longer than necessary; future contributors maintain two hook trees that drift.
2. **Boundary lint without an allowlist** (R-S1, CW-3): A7 softened L3, but if the lint's allowlist is not in the spec (it must be a list of explicit `.claude/` paths), the lint is "trust me" and L3 regressions land silently.
3. **Carryover from `d55d8c0`** (CW-1): A8 dropped the cherry-pick; the natural replacement is "re-implement fallback discovery from scratch," which is an invitation to copy `d55d8c0`'s logic line-by-line under a different commit message. The spec should describe the new loader as a *small generalization of the existing single-tier walk*, not as a fresh "fallback discovery system."

---

## § Cross-lens: R6 risk weighting

**Trigger:** Composability's specification (`specification/composability.md`) lists three permitted R6 mechanisms in §R6.6 + §8.1 and recommends **SessionStart-hook unification** (option 2: SessionStart hook delivers always-on awareness AND phase-context; PreToolUse hook on `Read` delivers L15 first-read fuller context). Composability flagged this for Skeptic risk weighting before synthesis.

**Skeptic conclusion:** **CONCUR with Composability's recommendation.** SessionStart-hook unification is the lowest-risk mechanism among the three permitted by R6.6, *provided* the spec encodes the mitigations below for the four failure modes named in §10.5. Rationale + alternatives weighed in the parallel `skeptic_review_appendix.md`.

### 10.1 Operational MUST/SHOULDs

- **MR6.1 [MUST]** The R6 mechanism MUST be a SessionStart hook (or SDK-equivalent session-init hook) plus a PreToolUse hook on the `Read` tool. The SessionStart hook MUST deliver both the always-on awareness statement (L15 piece 1) and the phase-context content from `<repo>/.claudechic/phase_context.md` (replacing the current `app.py:1822` write-then-Claude-auto-loads pattern). The PreToolUse hook MUST deliver the once-per-agent-session fuller-context injection on first tool-read of any path under any `.claudechic/` directory (L15 piece 2).
- **MR6.2 [MUST]** Phase advance during an active session MUST refresh the agent's phase context. Two acceptable shapes:
  - (a) `app.py`'s phase-advance code (currently `_write_phase_context` at app.py:1822) MUST send an explicit message to the active agent prompting a re-read of `.claudechic/phase_context.md`, OR
  - (b) The implementation MUST use a longer-lived hook surface (e.g., UserPromptSubmit or per-turn injection) that re-evaluates the file each turn rather than relying on session-start one-shot delivery.
  The spec MUST pick one and state which. Without this, phase advances mid-session leave the agent operating on stale phase context.
- **MR6.3 [MUST]** SessionStart hook failure (exception, timeout, missing file) MUST NOT prevent the session from starting. Failure MUST be logged at WARNING level to a claudechic log channel and MUST surface in the StatusFooter or equivalent UI indicator on the active agent. Silent loss of always-on awareness is forbidden.
- **MR6.4 [MUST]** SessionStart hook output size MUST be bounded. Combined always-on + phase-context payload MUST NOT exceed 8000 tokens (or equivalent character budget — spec authors set the exact number). On overflow, the hook MUST truncate the *fuller-context* portion first, preserve the always-on statement, and log the truncation. This prevents context-window exhaustion on workflows with large phase docs.
- **MR6.5 [MUST]** PreToolUse first-read tracking MUST be per-`Agent` instance (per-`ClaudeSDKClient` session), held in-memory only, and MUST reset when the `Agent` is recreated. No on-disk persistence; no cross-agent sharing.
- **MR6.6 [MUST]** The R6 mechanism MUST NOT write any file inside `.claude/`. Per A4 + A7 + R5.1, even the "non-destructive incidental write inside `.claude/`" path (Composability R6.6 option 3) MUST NOT be selected for R6 in this run — the awareness/phase-context content is *primary state* per R5.1 (claudechic generates and updates it during normal operation), and primary-state writes are forbidden inside `.claude/`.
- **MR6.7 [SHOULD]** The PreToolUse hook SHOULD trigger on read of any file *under* a `.claudechic/` root (recursive). Triggering only on direct children is under-coverage; triggering on every Read tool call regardless of path is over-coverage and wastes budget.
- **MR6.8 [MUST]** The Tester acceptance criterion for R6 MUST include the sentinel-directive test from `skeptic_review.md` §R-S6: place a marker in `<repo>/.claudechic/rules/test_marker.md` (or equivalent), spawn a fresh agent, query for the marker, assert the marker appears in the response. Both pieces of L15 (always-on AND first-read) MUST have a sentinel test.

### 10.2 Allowlist patterns for the boundary lint (per R-S1, given MR6.1–MR6.6)

**With SessionStart-hook unification chosen, the boundary lint allowlist requires NO `.claude/` write patterns for R6.** This is the cleanest outcome: the lint enforces strict L3 (no claudechic writes inside `.claude/` of any kind), and A7's "non-destructive incidental writes" stays as a *latent permission* that this run does not exercise.

The lint MUST permit:
- **Reads** from `.claude/**` (unrestricted; necessary for sessions JSONL, OAuth credentials, settings introspection, plugin info — preserved by R5.5).
- **Writes** to `~/.claudechic/**` and `<repo>/.claudechic/**` (claudechic's own roots).
- **Writes** to `<repo>/.claude` *as a symlink target* at `features/worktree/git.py:301` (the existing `.claude` worktree symlink); this is a write to the *worktree dir*, not into `.claude/`, and per R5.3 + R8.2 is permitted.

The lint MUST forbid:
- Any write whose resolved destination is under any `.claude/` directory (regardless of filename).
- Any `symlink_to` whose source path (the symlink itself) is under any `.claude/` directory.
- Any write to `.claude/settings.json`, `.claude/settings.local.json`, or files under `.claude/{rules,hooks,skills,commands}/` regardless of any future allowlist relaxation.

If a future feature requires an A7 non-destructive incidental write (out of scope this run), it MUST be added to the allowlist as an explicit `.claude/<pattern>` entry with a one-line justification, not granted by silent omission.

### 10.3 Top failure modes for SessionStart-hook unification

The spec authors MUST address each:

| # | Failure | Mitigation |
|---|---|---|
| F1 | **Phase advance mid-session leaves agent on stale phase-context.** SessionStart fires once; phase-context updates after that are invisible. | MR6.2: pick explicit-re-read-message OR per-turn-rehydration. |
| F2 | **Hook crashes silently** — session starts without injected content; agent operates with no claudechic awareness. | MR6.3: log + UI indicator. |
| F3 | **Hook output blows context budget** on workflows with large phase docs + many awareness rules. | MR6.4: bounded payload, truncate fuller-context first. |
| F4 | **PreToolUse "first-read" tracking misclassifies cross-agent sessions** if implemented globally instead of per-Agent. | MR6.5: per-`ClaudeSDKClient` in-memory only. |
| F5 | **`.claudechic/rules/` content collides with user's `.claude/rules/` content** — both reach the model's system prompt; user can't tell which is winning. | Out of scope for the lint; addressed by docs (TerminologyGuardian / UserAlignment surface) explaining the precedence. Skeptic flags as known UX wart, not a correctness bug. |

### 10.4 Detection: how the spec MUSTs are verified

- **MR6.1 + MR6.6** verified by the boundary lint (R-S1): zero `.claude/` writes in the diff.
- **MR6.2** verified by an integration test: spawn agent in active workflow, advance phase, send a turn that exercises phase-specific behavior, assert behavior reflects the new phase (not the old).
- **MR6.3** verified by a unit test that injects a hook exception and asserts (a) session starts, (b) WARNING is logged, (c) UI indicator surfaces.
- **MR6.4** verified by a unit test with oversize `.claudechic/rules/` corpus; assert truncation occurs and always-on statement is preserved.
- **MR6.5** verified by a unit test: spawn two `Agent` instances; trigger first-read on agent A; assert agent B still receives first-read injection on its own first read.
- **MR6.8** verified by the sentinel-directive integration test (named in MR6.8 itself).

### 10.5 Why not the alternatives (one-line each; details in appendix)

- **Composability R6.6 option 1** (`append_system_prompt` for always-on + PreToolUse for first-read): viable, marginally simpler for the always-on piece, but does NOT unify with phase-context — leaves phase-context as a separate mechanism, violating Composability's INV-9. Reject for that reason alone.
- **Composability R6.6 option 3** (non-destructive write inside `.claude/` that Claude Code auto-loads): MR6.6 forbids — phase-context is primary state per R5.1. Even if R5.1 were relaxed, this option couples claudechic's behavior to Claude Code's `.claude/`-auto-load semantics, which can change between Claude versions. Highest-risk path for L10.d (intent loss) on a future Claude upgrade.

---

*End of Specification-phase Skeptic review.*
