# Appendix — Background, Rationale, and History

**For:** future maintainers, reviewers, and anyone reopening this work later. **NOT** required reading for Implementer or Tester agents executing `SPEC.md` — they should be able to do their job without ever opening this file.

This appendix exists because `SPEC.md` is deliberately operational-only. Everything that explains *why* the spec is what it is lives here.

---

## Why this work exists

`sprustonlab/claudechic` and `abast/claudechic` are diverged forks of `mrocklin/claudechic`. Both forks have been adding features independently for a while. As of merge-base `285b4d1` (2026-04-20):

- Sprustonlab is 6 commits ahead, +13,606 lines, 174 files (one large package-consolidation commit `317f424` plus a Windows-compatibility wave).
- abast is 8 commits ahead, +6,583 lines, 104 files (one large bundle-defaults consolidation commit `d55d8c0` plus auto-perm UX, `/fast`, and small features).

Issue #23 in `sprustonlab/claudechic` ("Settings window + configuration reference documentation") is about exposing claudechic's configuration to users via a TUI screen plus a documentation reference. While scoping it, the user added a related concern not in the issue body itself: claudechic currently writes four of its own state files inside the `.claude/` namespace, mixing claudechic's data with Claude Code's own data. That has to stop as part of #23.

This work was framed at the start as: *evaluate two paths for sequencing this work without losing feature work on either fork.* Originally:

- **Path 1:** Selectively pull from abast first → then implement #23.
- **Path 2:** Implement #23 first → then selectively pull from abast.

The full team analysis (cross-lens) and the user's review of concrete diffs led to a third path: **converge layouts first, then pull, then implement #23.** That converged-first path is what `SPEC.md` instructs. This appendix explains why.

---

## How the chosen path was reached

### The original recommendation (pre-convergence-first)

The four Leadership lens evaluations in `.project_team/issue_23_path_eval/` (`composability_eval.md`, `terminology_glossary.md`, `risk_evaluation.md`, `alignment_audit.md`) reached split conclusions:

| Lens | Recommended | Decisive argument |
|---|---|---|
| Risk (Skeptic) | Path 1 | Mirror-tree silent-collision is the dominant Path 2 hazard; the boundary contract has no settings semantics for it to filter against. |
| Architecture (Composability) | Path 2 | Boundary-as-filter for everything that carries settings semantics; abast's `defaults/` overlay would otherwise implicitly co-decide #23. |
| Naming (TerminologyGuardian) | Path 2 | Vocabulary unity preserved at every step; Path 1 imports drift, not alignment. |
| Alignment (UserAlignment) | Path 1 (marginal) | The user's stated stake is lost-work avoidance, which maps to the risk lens; Path 1's preconditions are sprustonlab-internal; forced visibility survives context loss. |

Net 2-2 split. The synthesized `RECOMMENDATION.md` chose Path 1 marginally, citing the alignment lens's read that the user's stated failure mode mapped most directly to Skeptic's matrix. The recommendation was conditional on a workflow-tree pre-decision (the risk lens called this PC1.5).

### Why we ended up not following either Path 1 or Path 2 verbatim

When the user reviewed the concrete diff data, the dominant tension became visible: both forks solved the same need (bundle defaults inside the package) at incompatible directory layouts, and ~85 of abast's files were byte-near-identical mirrors of sprustonlab files at incompatible paths. The user's read: *if we converge layouts first, the silent-collision hazard dissolves at the layout layer before any cherry-pick happens, and the rest of both lens-conclusions stop disagreeing.*

That converged-first sequencing turns the workflow-tree pre-decision (PC1.5) from "an early step inside Path 1 made under reduced information" into "the structural pre-step of the whole effort." It also changes which fork's layout wins: the user chose abast's `defaults/` layout (so sprustonlab restructures), reasoning that it's cleaner to move once than to re-path every cherry-pick from abast forever.

### What the converged-first path resolves vs what it costs

Resolves:

- The mirror-tree silent-collision risk (the largest Path 2 hazard) becomes structurally impossible — there's no parallel tree to silently collide.
- Cherry-picks land mostly cleanly because paths align between the two forks.
- The naming-lens vocabulary-unity argument is satisfied — one canonical layout from the start.
- Skeptic's PC1.5 (mirror-tree pre-decision) is satisfied in advance.

Costs (accepted):

- Sprustonlab loses the `workflow_engine/` separation that `317f424` introduced. The engine-vs-data separation was a code-quality improvement; under this plan it reverts to engine-and-data co-resident in `claudechic/workflows/`.
- The restructure touches 22+ files for import updates and 5 files for path updates. Mechanical but high-volume.
- Phase 1 (pre-flight with abast) becomes a real gate — without abast's confirmation that they're OK with the layout convergence and will pause `defaults/` work, the plan is unsafe to execute.

### Why abast's layout (and not a third merged layout)

The user picked abast's layout (option (b) in the original UQ3) over sprustonlab's split (option (a)) and over a third invented form (option (c)). Reasoning: minimize forced re-pathing during cherry-picks, accept the engine-and-data co-residence cost. The terminology lens noted that *combining* both vocabularies (engine in `workflow_engine/` AND content in `defaults/`) would be the worst of both worlds — two contested vocabularies coexisting — so that combination was rejected.

---

## Rejected alternatives

### Path 3 — Push #23 upstream to mrocklin first

Considered. Rejected by the user explicitly: *"No mrocklin work is going to happen we want to pull from abast selectively."* No upstream-first option exists in this work.

### Path 3b — Selective cherry-pick of only abast's settings/config-adjacent commits before #23

Effectively absorbed into Path 1 once "selective pull" became the locked default mechanism for any abast integration. Not a separate option.

### Path 3c — Freeze abast as read-only reference, never sync

Considered as a contingent fallback only. Becomes an option only if (a) abast won't converge on a single workflow-tree root, AND (b) the user accepts living with parallel structure indefinitely, AND (c) the silent-collision risk under continued sync becomes unacceptable. Currently not the recommended path.

### Path 3d — Coordinate with abast on a joint settings design before either side implements

Not a separate path — a *tactic* available under any path. The pre-flight conversation captured in `SPEC.md` Phase A's pre-conditions is the concrete coordinate-with-abast action for this run.

### Original Path 1 (without layout convergence first)

Considered and recommended in `RECOMMENDATION.md`. Superseded by the converged-first path because the user's review of concrete diffs identified that resolving the layout question structurally up-front was cheaper than the original Path 1's sequencing of "pull onto incompatible layout, then resolve during cherry-pick."

### Original Path 2 (without layout convergence first)

Considered and rejected by the team's risk lens (citing the mirror-tree silent-collision hazard as VH/Critical). The architecture and naming lenses preferred it. Superseded by the converged-first path, which honors both sides' arguments: the boundary contract (architecture/naming preference) is established cleanly because cherry-picks are clean, AND the silent-collision risk (the risk lens's main objection) is dissolved structurally.

### Adopting sprustonlab's split layout (instead of abast's)

Considered. The user chose abast's `defaults/` layout instead. Reasoning: minimize forced re-pathing during ongoing cross-fork sync; sprustonlab restructures once; abast's content lands cleanly thereafter. Cost accepted: lose the `workflow_engine/` separation.

### Inventing a third merged layout (e.g., `claudechic/bundled/` or `claudechic/builtin/` plus retaining `workflow_engine/`)

Considered. Rejected — highest cost, no clear linguistic or architectural advantage, and the terminology lens noted it would risk producing two contested vocabularies coexisting if not done carefully.

---

## Why the spec's constraints look the way they do

### The "claudechic must never write inside `.claude/`" constraint

Comes from the user's "Independent settings" rule (their original statement of #23's derived scope). The user defined "Claude settings" broadly: anything in any `.claude/` directory belongs to Claude. The current write paths are baseline violations the spec is required to fix. The boundary regression test (Phase C.7) makes the rule self-enforcing.

### Why `.claude/rules/` is *not* written to (relocation to `.claudechic/rules/` with hook redirect)

The original SPEC listed four BF1 violations and said all four should relocate to `<launched_repo>/.claudechic/`. During execution planning, the user asked what `.claude/rules/<doc>.md` is for — and the answer surfaced a structural distinction worth being explicit about.

`.claude/rules/<doc>.md` is structurally different from the other three violations:

- `~/.claude/.claudechic.yaml`, `.claude/hints_state.json`, `.claude/phase_context.md` are **state files** — claudechic writes them for its own use, sitting inside Claude's namespace for historical reasons rather than design.
- `.claude/rules/<doc>.md` is **content claudechic deliberately places in Claude's namespace so Claude reads it** — `/onboarding` installs the package's context docs there because Claude Code auto-reads `.claude/rules/*.md` as part of its initialization. The file location is the mechanism.

Two options were considered:
- **(b)** Relocate the docs to `.claudechic/rules/` (claudechic-managed namespace), don't write to `.claude/rules/`, use claudechic's existing `PreToolUse` hook infrastructure to redirect Claude's reads of `.claude/rules/<claudechic-doc>` to the new location.
- **(c)** Stop installing context docs at all; leave the install / discovery problem to the repo owner.

The user picked **(b)**. Reasoning:
- Claudechic's hook infrastructure (`claudechic/guardrails/hooks.py`) already intercepts tool calls via `PreToolUse` — that's how guardrails work. Extending the hook to redirect reads of `.claude/rules/<claudechic-doc>` is incremental, not new infrastructure.
- (b) preserves the user-facing behavior (Claude becomes claudechic-aware automatically when claudechic is in use) while honoring the boundary (claudechic doesn't write to `.claude/rules/`).
- (b) keeps the install + drift-detection mechanism in claudechic's hands (so claudechic-managed docs stay current); only the storage location moves and the access mechanism changes.

The hook redirect mechanism depends on Claude Code's `.claude/rules/` discovery going through the `Read` tool (which `PreToolUse` hooks intercept). A spot-check of the Claude Agent SDK suggests the discovery may be loaded via `SystemPromptFile` instead, which would not fire `PreToolUse` hooks. **The SPEC requires Implementer to verify hookability before completing C.1.1**; if the assumption fails, escalate to Coordinator with a re-spec (likely shifting to `SystemPromptFile`-based mechanism instead).

Concrete consequences captured in `SPEC.md` C.1.1 / C.1.2 / C.1.3:
- Context docs relocate from `<launched_repo>/.claude/rules/<doc>.md` to `<launched_repo>/.claudechic/rules/<doc>.md`.
- The `/onboarding` workflow's `context_docs` phase **stays** but installs into `.claudechic/rules/`; the advance check path updates accordingly.
- The `ContextDocsDrift` trigger **stays** but compares against `.claudechic/rules/`.
- The `context_docs_outdated` hint **stays** but its message references the new location.
- A hook (extending or alongside `claudechic/guardrails/hooks.py`) intercepts `Read` of `.claude/rules/<claudechic-doc-name>` and rewrites the path to `.claudechic/rules/<claudechic-doc-name>` via `hookSpecificOutput.updatedInput`. Other reads of `.claude/rules/` (filenames not matching claudechic's allow-list) pass through unchanged.
- A migration step on first run after upgrade copies any pre-existing `.claude/rules/<claudechic-doc>.md` files into `.claudechic/rules/` (so user-edited installed copies aren't lost), and emits a one-time advisory hint that the install location has moved (the user can delete the stale `.claude/rules/<claudechic-doc>.md` files at their discretion; claudechic does not auto-delete them since `.claude/rules/` is the repo owner's directory).

This is recorded as **D22** in `STATUS.md`. It refines D5's reading: the rule is "claudechic stops *writing* into Claude's namespace," not "claudechic stops *reading* from it" — Claude's read of `.claude/rules/` (intercepted by claudechic's hook) is read-only behavior on Claude's side, even though the result is content claudechic generated. The boundary regression test (Phase C.7) checks for *writes* by claudechic into `.claude/`, which the hook redirect doesn't perform.

### The directory-form (`.claudechic/`) over file-form (`.claudechic.yaml`)

Architecture lens flagged that the worktree symlink mechanism (`features/worktree/git.py:293-301` mirrors `.claude/` into worktrees) prefers symlinking a directory to symlinking a file at root. The user picked the directory form. The symlink mirror in Phase C.3 is part of the same architectural concern.

### The "Settings vs Config" terminology rule

User-confirmed prescriptive split: "Settings" is user-facing umbrella, "Config" is technical. Codebase symbol renames (`ProjectConfig` etc.) are NOT forced — the rule applies to user-facing prose only. Came out of the terminology lens noticing that the codebase used "config" while the user and issue #23 body used "settings" inconsistently.

### Per-project `analytics.id` (no global tier)

Falls out of the strict reading of the boundary directory form. If everything claudechic-authored lives under `<launched_repo>/.claudechic/`, there's nowhere to put a global config — and the user explicitly accepted per-project analytics identity rather than introducing a new global location like `~/.config/claudechic/`. The user's local analytics is currently disabled, so the practical impact of this decision is academic for them, but it locks the design rule for future users.

### Why `/fast` is deferred (not pulled)

The `/fast` mode requires Anthropic API key billing (does not work with the Max/Pro subscription claudechic typically runs on). It also requires pinning `anthropic==0.79.0`. Plus its `fast_mode_settings.json` placement (inside the package directory) is itself a boundary-violation pattern that warrants discussion. Filed as `sprustonlab/claudechic#25` for follow-up with abast.

### The "single atomic restructure PR" constraint

Comes from a process concern: the restructure touches 27+ files. If interleaved with cherry-picks or split across multiple PRs, reviewers can't see the full picture and bisect can't isolate it. Single atomic PR is the easiest way to keep the change reviewable and revertable.

### The "boundary lint must precede first cherry-pick" constraint

Catches the case where a pulled abast commit re-introduces a `.claude/` write that we've just decided we don't allow. Without the lint in CI before the first cherry-pick, a violating commit could merge silently.

---

## Reversal triggers — when to halt and re-evaluate

These are conditions that, if they become true during execution, mean the chosen path is no longer the right one. Implementer/Tester should escalate to Coordinator if any of these arise.

| Trigger | Why it's a problem | What to do |
|---|---|---|
| Pre-flight conversation with abast reveals an imminent `/settings` redesign of their own | Pulling abast's not-yet-final design under any path risks landing a parallel design that conflicts with sprustonlab's #23 vision and abast's own near-future direction. | Stop. Reopen conversation about coordinating a joint design. |
| abast won't pause `defaults/` work during sprustonlab's restructure window | Restructuring to match a moving target wastes work. | Re-plan; either negotiate a freeze or accept reconciling against further drift. |
| Phase A sanity checks fail | Restructure has a problem; further phases will compound it. | Halt; diagnose; do not proceed to Phase B. |
| Cherry-picks produce unexpected conflicts despite layout convergence | The model assumption (layout convergence makes cherry-picks clean) is wrong somewhere. | Pause; inspect; find the model failure before continuing. |
| Boundary lint catches a violation in a pulled abast commit | Pulling that commit would re-introduce the boundary problem we're trying to fix. | Reject the pull; add to `NON_PULLED.md` with the violation cited. |
| Phase C reveals the boundary surface is bigger than the four BF1 violations + `/settings` TUI | Original scoping missed something. | Pause; re-scope; update the spec. |
| abast cooperation turns out to be unavailable in practice despite being declared available at pre-flight | Several preconditions weakened (intent recovery on cherry-picks, convergence-decision support). | Re-evaluate whether to continue, freeze the fork, or invent a new approach. |

---

## Decision history (D1–D21)

The full table lives in `STATUS.md`. Quick reference:

| ID | Decision |
|---|---|
| D1 | mrocklin upstream is out of scope. |
| D2 | "Sync" in any path means selective pull from abast (not push, not upstream). |
| D3 | abast integration is selective only, never all-or-nothing. |
| D4 | `~/.claude/.claudechic.yaml` must move out of `~/.claude/`. |
| D5 | `.claude/` is broadly off-limits to claudechic (any `.claude/` dir is Claude's namespace). |
| D6 | "Lost work" includes all four senses: commits never on main, features non-functional post-merge, features reverted in conflict resolution, intent lost even if code survives. |
| D7 | Sprustonlab and abast are equal value; surface conflicts in recommendation; user adjudicates. |
| D8 | abast cooperation is available; team should plan to leverage it. |
| D9 | No deadline on #23. |
| D10 | No time estimates in any deliverable. Process detail only. |
| D11 | Issue #23's body scope and userprompt-derived boundary scope are distinct; both addressed, distinguished. |
| D12 | Fork diff: default branches only (`origin/main` vs `abast/main`). |
| D13 | Fork diff: direct merge-base only, no mrocklin axis. |
| D14 | Fork diff: 3-6 thematic clusters per fork. |
| D15 | Fork diff: top-N=80 by churn inline + full set in CSV. |
| D16 | "Settings" = user-facing umbrella; "Config" = technical (YAML file format and loader). No code-symbol renames forced. |
| D17 | Boundary location: `<launched_repo>/.claudechic/config.yaml` (directory form, not file at root). |
| D18 | `analytics.id` is per-project. No global analytics identity. |
| ~~D19~~ | (Reversed) Original choice of sprustonlab's split layout. |
| D19' | Adopt abast's `defaults/` layout. Engine in `claudechic/workflows/`; bundled content in `claudechic/defaults/{workflows,global}/`. |
| D20 | `/fast` from abast: skip for now; deferred to sprustonlab/claudechic#25. |
| D21 | Path order: layout convergence FIRST, then abast pull, then issue #23. |
| D22 | Claudechic does not write to `<launched_repo>/.claude/rules/`. Context docs relocate to `<launched_repo>/.claudechic/rules/`; `/onboarding` install phase and drift detection target the new location; Claude accesses them via a `PreToolUse` hook redirect (verification of hookability required during execution). |

---

## Files referenced and their roles

- `SPEC.md` — operational spec for Implementer and Tester. Authoritative for execution.
- `Appendix.md` — this file. Background, rationale, rejected alternatives, decision history.
- `RECOMMENDATION.md` — the original cross-lens recommendation document, before the converged-first path was decided. Historical artifact; superseded operationally by `SPEC.md`. Useful for understanding the reasoning chain that led to D21.
- `STATUS.md` — current state of the project run, locked decisions, baseline findings, phase log.
- `userprompt.md` — the user's original request and clarifications.
- `fork_diff_report.md` and `fork_file_map.csv` — the diff data substrate. Generated once; should not need to be regenerated unless the forks have meaningfully drifted since.
- `composability_eval.md`, `terminology_glossary.md`, `risk_evaluation.md`, `alignment_audit.md` — the four Leadership lens evaluations. Useful for understanding *why* specific constraints in `SPEC.md` are what they are.
- `abast_executive_summary.md` — coordination artifact sent to abast for Phase 1 pre-flight.
- `specification/SPECIFICATION.md` — thin pointer file required by the workflow's advance check; points to `SPEC.md` and `Appendix.md`.
- `NON_PULLED.md` (created during Phase B) — the deliberate-non-pull register.

---

## Historical context

This work was scoped on 2026-04-25 in a project-team workflow run within sprustonlab/claudechic. The team consisted of:

- **Coordinator** (the claudechic agent operating the workflow).
- **Composability** — architecture lens.
- **TerminologyGuardian** — naming lens.
- **Skeptic** — risk lens.
- **UserAlignment** — alignment-with-user-intent lens.
- **GitArchaeologist** — the (non-Leadership) supporting agent that produced the Fork Diff Report.

The user is `boazmohar@gmail.com` (sprustonlab maintainer). The work was scoped through several rounds of clarification, including:
- An initial decision to defer mrocklin upstream as a destination (D1).
- A late-stage user feedback that "BF1 is jargon — please avoid" — which led to dropping internal team labels from user-facing prose (the Coordinator switched from labels like "BF1," "D7," "PC1.5" to plain language for the user).
- A late-stage user feedback that the recommendation document conflated "spec" with "plan" — which led to this `SPEC.md` + `Appendix.md` split. (The original `plan.md` was deleted; its operational content lives in `SPEC.md`, its rationale lives here.)
- A late-stage refinement of `.claude/rules/` scope: the original SPEC said claudechic relocates `.claude/rules/<doc>.md` to `.claudechic/rules/<doc>.md` straightforwardly. The user clarified the boundary more precisely — claudechic does not *write* to `.claude/rules/` (that's the repo owner's directory), but the docs themselves still relocate to `<launched_repo>/.claudechic/rules/` and Claude accesses them via a `PreToolUse` hook redirect (since claudechic already has hook infrastructure). The Coordinator initially misread this as "stop installing context docs entirely" (option (c)) and was corrected to (b). Recorded as D22.

The Phase 1 pre-flight conversation with abast was confirmed complete with answers: (1) OK with adopting `defaults/` layout, will pause `defaults/` work; (2) nothing imminent on `/settings`, `.claude/` boundary, or config layout; (3) leave `/fast` out for now (other commits stable); (4) no special dependencies/ordering beyond what's already noted. All reversal triggers cleared.

---

*End of appendix.*
