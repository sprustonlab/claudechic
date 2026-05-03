# STATUS — independent_chic

**Re-read this file after each compaction.**

This is the workflow state of record. The vision document
(`vision.md`) and userprompt (`userprompt.md`) are the authoritative inputs;
this file tracks where we are, what's locked, and what changes from the
prior team's hand-off.

---

## Run identity

| Field | Value |
|---|---|
| **project_name** | `independent_chic` |
| **working_dir** | `/groups/spruston/home/moharb/claudechic` |
| **state_dir** | `/groups/spruston/home/moharb/claudechic/.project_team/independent_chic/` |
| **workflow** | `project-team` |
| **current_phase** | `specification` (entered after leadership lens reports + user resolution round) |
| **resumes_from** | Fresh run; references prior team's analysis at `.project_team/issue_23_path_eval/` |
| **issue links** | sprustonlab/claudechic#23, sprustonlab/claudechic#24 |
| **deferred to** | sprustonlab/claudechic#25 (`/fast` mode) |

---

## Git baseline

| Field | Value |
|---|---|
| **repo** | `/groups/spruston/home/moharb/claudechic` |
| **branch** | `main` |
| **HEAD at run start** | `317f4244b30772a5302ae99f7b5bb16710cc9a72` |
| **working tree at run start** | clean |
| **fork** | sprustonlab/claudechic |
| **upstream merge-base with abast** | `285b4d1` (per vision §"Hot files", 2026-04-20) |

---

## Approved vision pointer

The vision was approved by the user with: **"approved"** (Vision phase exit).

Authoritative vision = `vision.md` verbatim **plus** the run-specific amendments
captured below (A1–A12).

---

## Locked decisions (binding for this run)

### From the prior team (L1–L17, do not re-litigate)

Full text in `vision.md` §"Locked constraints". One-line summaries here for
quick reference:

| ID | Summary |
|---|---|
| L1 | mrocklin/claudechic upstream is out of scope. |
| L2 | abast integration is selective only. |
| L3 | claudechic must never write any file inside any `.claude/` directory. **Softened by A7 — see below.** |
| L4 | "Settings" = user-facing umbrella; "Config" = technical term. No code-symbol renames forced. |
| L5 | Launched-repo root contains at most one claudechic-authored entry: `.claudechic/`. Replaces top-level `.claudechic.yaml`. |
| L6 | User-tier `.claudechic/` lives at `~/.claudechic/` (mirrors `~/.claude/`; not XDG). |
| L7 | Each tier's layout: `workflows/`, `global/{rules,hints}.yaml`, `mcp_tools/`. Package tier under `claudechic/defaults/...`. |
| L8 | Config keys are 2-tier (user + project). Defaults live in code. No `claudechic/defaults/config.yaml`. **Reaffirmed by A5.** |
| L9 | `analytics.id` lives at user-tier. |
| L10 | "Lost work" includes 4 senses; risk analysis must address all four. |
| L11 | abast cooperation is available; leverage it. **Reframed by A10 — bidirectional cross-pollination, not one-way pull.** |
| L12 | `/fast` mode is NOT pulled this run (filed as #25). |
| L13 | No time estimates in any deliverable. Process detail throughout. |
| L14 | **Spec docs are strictly operational. Rationale, decisions, rejected paths go in a separate appendix file.** Grading rubric must enforce this. |
| L15 | Two-piece agent awareness: always-on at session start + once-per-agent fuller-context on first read inside `.claudechic/`. **Reaffirmed by A11.** |
| L16 | Cherry-pick selection from `abast/main` is decided. **Updated by A2 + A8 — see cherry-pick table below.** |
| L17 | No upgrade-migration logic required. **Reaffirmed by A9 — no startup warnings either.** |

### Run-specific amendments

#### Vision-phase amendments (A1–A3)

**A1 — Vision is authoritative but not infallible.**
Agents discovering errors or inconsistencies in `vision.md` must surface them
to the coordinator rather than work around them silently.

**A2 — L16 cherry-pick table fully decided (Q3 = "adopt").**
The "UX-decision-required" gates from `vision.md` §L16 are resolved.
**Subsequently revised by A8** for the `d55d8c0` row. Final cherry-pick
disposition for `abast/main` commits:

| Commit | Decision | Rationale |
|---|---|---|
| `9fed0f3` | **Pull** | Docs clarification on `spawn_agent type=` parameter. |
| `8e46bca` | **Pull** | Fix: use resolved `workflows_dir` instead of hardcoded path. |
| `d55d8c0` (selective) | **SKIP** *(per A8)* | Hand-curated "loader-only" extraction is brittle (no clean git command). Re-implement fallback discovery logic from scratch in the restructure work. |
| `f9c9418` | **Pull** *(Q3)* | Full model ID + loosened validation. User adopted the UX. |
| `5700ef5` | **Pull** *(Q3, reaffirmed by A6)* | Default to `auto` permission mode on startup. |
| `7e30a53` | **Pull** *(Q3, reaffirmed by A6)* | Add `auto` to Shift+Tab cycle. Bundled with `5700ef5`. |
| `26ce198` (`/fast`) | Skip | Deferred to #25 per L12. |
| `0ad343b` (anthropic 0.79.0 pin) | Skip | Only needed for `/fast`; deferred. |
| `claudechic/fast_mode_settings.json` | Skip | Bundled with `/fast`; deferred. |

**A3 — Deliverable #4 (agent awareness) mechanism mirrors `.claude/rules/`.**
Two-piece L15 semantics unchanged. **Operationalized by A4 + A7 — see below.**

#### Leadership-phase amendments (A4–A12) — from user resolution round

After the four Leadership lens reports landed (`composability_eval.md`,
`terminology_glossary.md`, `risk_evaluation.md`, `alignment_audit.md`), nine
cross-cutting questions were surfaced to the user. The resolutions:

**A4 — Agent-awareness mechanism = behavioral mirror, with explicit prohibitions (Q1).**
The mechanism makes agents *experience* `.claudechic/` content the same way
they experience `.claude/rules/`. Implementation constraints:

- **Required:** behavioral equivalence — from the agent's perspective, the
  rule-equivalent content auto-loads as if it were a Claude rule.
- **Permitted:** non-destructive touches to `.claude/` (e.g., reading; writing
  *new*, *non-colliding*, *cross-platform* files claudechic owns).
- **Prohibited:** overwriting any Claude-owned settings/config file inside
  `.claude/`.
- **Prohibited (agent-awareness mechanism only):** symbolic links in the
  agent-awareness delivery mechanism (Group D). Symlinks are not supported on
  Windows; the agent-awareness mechanism must work cross-platform.
- **Permitted (worktree filesystem-state-propagation):** symbolic links at
  `claudechic/features/worktree/git.py:293–301` for propagating `.claudechic/`
  into new worktrees, mirroring the existing `.claude/` symlink pattern at
  the same code site. Windows portability for both symlinks is tracked at
  [sprustonlab/claudechic#26](https://github.com/sprustonlab/claudechic/issues/26)
  (revised per user instruction during spec-exit checkpoint). The new
  `.claudechic/` symlink does not introduce a regression because the
  pre-existing `.claude/` symlink also lacks Windows support.
- The team designs the specific mechanism (SDK injection, hooks, append-paths,
  or a non-destructive in-`.claude/` write) within these constraints.

**A5 — Config layering stays 2-tier (Q2).**
The user's "everything in 3 levels" intent referred to the four content
categories (workflows / rules / hints / MCP tools), **not** to config keys.
L8 stands as written: config keys are 2-tier (user + project), defaults in
code, no package-tier config file.

**A6 — Adopt `auto` as startup permission-mode default (Q3 reaffirmed).**
Cherry-picks `5700ef5` and `7e30a53` are confirmed for adoption. Startup
default permission mode flips from `default` to `auto`. Shift+Tab cycle
includes `auto`.

**A7 — Boundary rule is primary-state-only, not absolute (Q4).**
The L3 strict reading ("never write any file inside any `.claude/` directory")
is **softened**. The binding interpretation:

- **Claudechic primary state files** (config, hints state, phase context,
  session-state derivatives — the things claudechic writes during normal
  operation) **must not** live inside any `.claude/` directory. They live
  under `.claudechic/` per L5/L6.
- **Incidental, non-destructive touches** to `.claude/` are permitted *if*
  the team is confident the touch is non-destructive (creates new files
  claudechic owns; does not collide with Claude-owned files; works
  cross-platform).
- The two prohibitions from A4 (no overwrites of Claude-owned settings; no
  symlinks) are absolute.
- The boundary test (L3 enforcement) must distinguish primary-state writes
  (forbidden) from non-destructive incidental touches (allowed under A7) —
  the team designs the test to encode this distinction.

**A8 — Drop the selective `d55d8c0` cherry-pick (Q5).**
The "loader-only, not the YAML" extraction has no clean git command and
introduces merge fragility. Re-implement the fallback-discovery logic from
scratch as part of the restructure work (the team is rebuilding that loader
anyway). Recorded above in the A2 cherry-pick table.

**A9 — No startup warning for existing users (Q6).**
The user has accepted silent-loss-of-existing-state as a tradeoff: the only
existing users are the issue-author and Arco; both can move their own files
manually. L17 (no migration logic) extends to: no startup warnings either.
**This re-classifies Skeptic's "silent-loss-for-existing-users" finding from
a failure mode to an accepted tradeoff.**

**A10 — Trim "convergence" framing in vision §7; abast relationship is
bidirectional cross-pollination (Q7).**
The vision document's framing of "convergence with abast" as a one-way
deliverable from claudechic's side is corrected: the relationship is mutual
cross-pollination across both forks. Spec and docs language uses
"cross-pollination" / "selective integration" / "coordination", **not**
"convergence" or "merge program". The vision document text itself is not
rewritten (it's the prior team's hand-off artifact); spec authors honor A10
when authoring spec/docs/UI prose.

**A11 — Two-piece agent awareness confirmed (Q8).**
The user's earlier phrasing "a prompt injection" (singular) does not
override the two-piece design (always-on at session start + once-per-agent
fuller-context on first `.claudechic/` read). L15 stands.

**A12 — Settings UI smaller features delegated to spec phase (Q9).**
The smaller UX gaps surfaced from issue #23 (welcome-screen access to
settings, workflow-ID discovery for the disabled-workflows config key,
disabled-IDs listing, settings-button vs `/settings`-command parity) are
delegated to the spec-phase team. The team may include them in scope or
postpone any of them if scope balloons. Postponements must be recorded with
explicit rationale.

**A13 — Agent-awareness mechanism switched to SDK-native rules-loading.**

User approved Option B from `RESEARCH.md` at the spec-exit checkpoint:

> "approve option B, fine with all answers. I want to copy as default and the
> settings have a way to desable that. there are no tiers here right? does
> claude reads from ~/.claude/rules?"

The Claude Agent SDK already loads `.claude/rules/*.md` natively from
user/project/local tiers (claudechic enables this at `app.py:969` via
`setting_sources=["user","project","local"]`). The earlier Group D mechanism
(custom session-start hook + pre-tool-use hook + first-read tracker) is
**replaced** with a much simpler approach:

- Bundled `claudechic/context/*.md` files are **copied** into `~/.claude/rules/`
  with a `claudechic_` filename prefix (e.g., `claudechic_workflows-system.md`)
  on every claudechic startup. Idempotent NEW/UPDATE/SKIP semantics — never
  overwrites non-prefixed files.
- The Claude Agent SDK auto-loads these on every session, in every project,
  with full YAML frontmatter parsing, recursive directory walking, symlink
  following, and `/compact` survival — all natively, without claudechic
  reimplementing any of it.
- Install location is **user-tier in Claude's own tier system** (`~/.claude/rules/`),
  not project-tier. One-time install per user; applies across every project.
  Per-project overrides go into `<repo>/.claude/rules/` directly via Claude's
  own surface; claudechic does NOT touch project-level rules.
- A new user-level config key (e.g., `awareness.install`, default `true`) gates
  the install. Surfaced as a settings-screen entry. Off → install routine
  no-ops; user manages `~/.claude/rules/` themselves.
- The existing `/onboarding context_docs` phase is **restored** and adapted
  (target directory changes; install becomes available outside the onboarding
  workflow as a startup-time idempotent routine).
- The `ContextDocsDrift` trigger and `context_docs_outdated` hint stay
  **deleted** (originally marked for deletion in the synthesis spec; deletion
  preserved). A hint is a user-facing nudge prompting an action; with the
  install now idempotent on every startup, drift is repaired silently with no
  user action required. Firing a hint about a condition the system has
  already corrected would be UX noise. If a non-hint use for drift detection
  emerges later (e.g., release-engineering logging), that's a separate design,
  not a restoration.
- Phase context delivery stays separate. Static SDK rules-loading does NOT
  cover the dynamic phase-context use case (phases advance mid-session; Claude
  rules don't refresh). Phase context keeps the existing
  write-file-and-tell-agent-to-read pattern, just relocated to
  `<repo>/.claudechic/phase_context.md` per L3+A7.
- Three SDK-uncertainty risks from the earlier spec (`SessionStart` not in
  `HookEvent` literal; `PostCompact` not in literal; `PreToolUse
  additionalContext` field acceptance) become non-issues — the new mechanism
  doesn't depend on any of them. The boundary lint allowlist gains one entry
  (writes to `~/.claude/rules/claudechic_*.md`); the registry baseline
  shrinks net of awareness-mechanism write-sites.

**Boundary classification of the install** (the bookkeeping the researcher
flagged): writes of claudechic-prefixed `.md` files into `~/.claude/rules/`
are classified as **non-destructive incidental** under A7. Justification:

- Files are claudechic-owned (distinct prefix prevents collision with anything
  the user or Claude Code itself might place in the directory)
- Install is idempotent (NEW/UPDATE/SKIP semantics; no destructive overwrites
  of non-`claudechic_`-prefixed files)
- User-toggleable via settings (consensual, not silently mandatory)
- Cross-platform (regular file write — no symlink, A4-clean for Group D)
- Claude Agent SDK already loads from this location, which is the precise
  consumer pattern this write feeds

**Operational consequence on prior spec deliverables:**

- SPEC.md §4 (Group D) collapses dramatically (~600 net new lines → ~30)
- SPEC.md §11 boundary allowlist gains the install pattern
- SPEC.md §12 known SDK risks shrinks substantially
- SPEC.md §13.3 awareness invariants reduces from ~13 to ~5
- SPEC.md §15 file map: no `claudechic/context_delivery/` package;
  `claudechic/hints/triggers.py:ContextDocsDrift` deleted (no consumer);
  `claudechic/global/hints.yaml` `context_docs_outdated` deleted (no purpose
  — hints are user-facing; auto-install removes the user action that the hint
  was nudging toward); existing onboarding context_docs phase retained and
  adapted
- axis_awareness_delivery.md collapses heavily; axis_boundary_test.md gains
  one registry entry

The composability lens leads the spec revisions; coordinator authors A13
(this entry) and the corresponding `SPEC_APPENDIX.md` updates in parallel.

**A15 — Phase-prompt delivery: file-on-disk dropped (post-spec, retroactively captured).**

The original spec mandated `<repo>/.claudechic/phase_context.md` written by the
engine, read by the agent via Read tool, and re-read by PostCompact hook from
disk. During spec-exit iteration, the coordinator investigated whether the file
was actually necessary given that engine-to-agent content delivery happens for
other content via `_send_to_active_agent` without a file intermediary.

The investigation found two things: (a) the existing PostCompact hook
(`agent_folders.py:create_post_compact_hook`) already regenerated the phase
prompt from workflow files via `assemble_phase_prompt` — it did not read the
file at all; (b) the file's claimed "becomes part of the system prompt on the
next turn" auto-load assumption was almost certainly false (Claude Code
auto-loads `.claude/rules/`, not arbitrary `.claude/*.md` files); the file was
operationally a Read-tool transit medium for content that could be sent inline
via the same `_send_to_active_agent` pattern used elsewhere.

User verbatim authorization (SE8 in `userprompt.md`):

> "drop"

Final disposition (binding for this run):

- `<repo>/.claudechic/phase_context.md` is NOT created. Engine assembles the
  phase prompt via `assemble_phase_prompt` and sends it directly via
  `_send_to_active_agent` on workflow activation and phase advance.
- `_write_phase_context` helper deleted.
- PostCompact hook keeps the existing-code closure pattern: regenerates from
  workflow files; no file I/O.
- Boundary registry: five primary-state phase-context-related write sites
  removed.
- Invariants: INV-AW-6 (activation send), INV-AW-8 (phase-advance send), and
  INV-AW-9 (PostCompact regeneration) redefined; INV-AW-7 retired (no file to
  unlink).

This amendment is captured retroactively after UserAlignment2 flagged the
audit-trail gap during ImplementerD's plan review (the user-words anchor and
the post-execution amendment had not previously been formalized in either
`userprompt.md` or this file even though SPEC.md and the lens-review
deliberations all reflect the dropped-file design).

**A14 — Cross-fork state assessment outcome (post-spec).**

After SPEC.md was finalized, the user flagged that `abast/claudechic` may have moved on. Researcher2 investigated and produced
`/groups/spruston/home/moharb/claudechic/.project_team/independent_chic/RESEARCH_abast_state.md`.

Findings:

- All 9 catalogued commit SHAs (the 5 Pull + 4 Skip in A2 + A8) are unchanged in `abast/main`. The locked cherry-pick set remains valid.
- 8 new abast commits since our analysis (all 2026-04-26, all by Arco Bast).

User's verbatim disposition decisions on the 8 new commits:

> "accept our plan and skip the accf332d bundle"
> "0034 can be added"

Initial disposition (later revised — see post-execution finding below):

- **Pull (added):** `003408ac` — guardrail and advance-check messaging fix.

**Post-execution revision: `003408ac` reverted.** During Group F execution, ImplementerB
discovered that `003408ac` transitively depends on prior abast role-resolution-refactor
commits not in the cherry-pick set: it imports `DEFAULT_ROLE` from
`claudechic.workflows.agent_folders` (introduced by an earlier abast commit), and even
with that constant forward-ported, 6 tests in `tests/test_phase_injection.py` fail
because `003408ac` rewrites the role-resolution / advance-phase-broadcast subsystem
assuming abast's prior refactor is in place. User direction at the moment of discovery:

> "revert."

Final disposition (binding for this run):

- **Skip (reverted post-execution):** `003408ac` — transitive dependency on abast
  commits not in scope; reverted in commits made after the cherry-pick attempt.
- Total cherry-pick count: **5 Pull** (the original locked set; `003408ac` not added).
- **Skip:** the `accf332d` bundle (`accf332d`, `8f99f03f`, `2f6ba2e5`, `a60e3fe4`) — major restructure-overlap and new-mechanism work; not absorbed this run.
- **Skip (assumed):** `ff1c5aec` + `1d6d4327` — `ask_agent`/`tell_agent` API rename to `message_agent` with `requires_answer` kwarg. Breaking change for our actively-used MCP API. Not adopted.
- **Skip (assumed):** `7dcd488e` — workflow-content iteration on the project_team workflow. Out of scope for this run.

Cross-fork strategy (per L11): coordination with abast remains available for future runs but is not a blocker for shipping this spec. The cross-fork divergence on the four skipped items is documented in `RESEARCH_abast_state.md` for future reference.

---

## Phase log

| Phase | Status | Notes |
|---|---|---|
| `vision` | ✓ Complete | Approved by user. Vision = `vision.md` + A1 + A2 + A3. |
| `setup` | ✓ Complete | State directory + `userprompt.md` + this STATUS.md written. State dir renamed `issue_24` → `independent_chic`. |
| `leadership` | ✓ Complete | All 4 Leadership lens reports landed (`composability_eval.md`, `terminology_glossary.md`, `risk_evaluation.md`, `alignment_audit.md`). User resolution round delivered amendments A4–A12. |
| `specification` | ✓ Complete (user approved) | * User checkpoint passed. Final operational deliverable: `SPEC.md` (1330 lines, self-contained). Companion: `SPEC_APPENDIX.md` (rationale; coordinator-authored). Cross-fork research recorded in A14 + `RESEARCH_abast_state.md`. Final work-group count: 8 (A through G + docs reference). Five jargon-and-history greps all pass with zero hits. Approval verbatim: "approve". |
| `implementation` | ✓ Complete (Leadership approved) | All 8 work groups landed: A `711be4c`, B + §10 + 5 cherry-picks `b9023e2`–`2e2f98f`, `003408a` cherry-pick + revert (kept in history; A14 reverted post-execution; net no-op), C checkpoint `29f98bb` + final `81f0c69`, D `d001e30`, E `e4fa9bf`, G + §8 `f5b7225`, follow-up substitution-helper consolidation `efc94ed`. Spec text cleanups landed via Composability2's batch pass. All 4 Leadership lenses returned APPROVED FOR IMPLEMENTATION COMPLETION. |
| `testing` | ✓ Complete (user approved) | * User checkpoint passed. Approval verbatim: "advance to documentation". Two test commits + YAML role-filter scope fix on `no_close_leadership`. Final: 621 passing serially / 0 failing; 3 Textual-pilot timing flakes intermittent under parallel mode (pass serially). HEAD post-test: `3dc0ffd`. |
| `documentation` | ✓ Complete | Single commit `06e2caf`. Refreshed: `docs/configuration.md` (added `ArtifactDirReadyCheck` sentence); project-root `CLAUDE.md` (file map for post-restructure layout, broken section header fixed, Shift+Tab cycle, `/settings` command, `awareness.install` toggle mention); `claudechic/context/CLAUDE.md` (CRITICAL fix: disabled_ids schema corrected from nested to flat — agent-facing file installed via awareness install). New file: `docs/release-notes/independent_chic.md`. HEAD: `06e2caf`. Approval verbatim: "advance to signoff". |
| `implementation` | Pending | * User checkpoint. |
| `testing` | Pending | * User checkpoint. |
| `signoff` | Pending | * User checkpoint. |

---

## Lens deliverables (Leadership phase outputs)

In this directory:

| File | Lens | Author |
|---|---|---|
| `composability_eval.md` | Composability | identifies 10 design axes (6 runtime + 4 process); recommends 7-group decomposition for spec; flags A3↔L3 tension and per-category resolution-semantics gap. |
| `terminology_glossary.md` | TerminologyGuardian | ~50 entries across 11 sections; pins L4 surface-vs-internals; flags "rules" overload and "tier" vs "level" vs "namespace" risks. |
| `risk_evaluation.md` | Skeptic | 23 numbered risks (6 Critical, 10 High, 6 Med, 1 Low); flagged 3 vision/STATUS errors (A3↔L3 tension, my V-ERR-2 phase log inconsistency [now fixed], silent-loss failure mode [reclassified by A9 as accepted tradeoff]). |
| `alignment_audit.md` | UserAlignment | 2 HIGH + 4 MEDIUM + 4 LOW drift items; led to the resolution round captured in A4–A12. |

---

## Reference materials (not required reading)

Prior project-team run at `.project_team/issue_23_path_eval/`:

| File | Use |
|---|---|
| `vision.md` (this dir) | Authoritative vision for THIS run. |
| `../issue_23_path_eval/RECOMMENDATION.md` | Cross-lens recommendation from prior run. |
| `../issue_23_path_eval/fork_diff_report.md` | Diff between sprustonlab and abast since merge-base. |
| `../issue_23_path_eval/fork_file_map.csv` | File-level fork delta map. |
| `../issue_23_path_eval/composability_eval.md` | Prior Composability lens analysis. |
| `../issue_23_path_eval/terminology_glossary.md` | Prior Terminology lens analysis. |
| `../issue_23_path_eval/risk_evaluation.md` | Prior Skeptic lens analysis. |
| `../issue_23_path_eval/alignment_audit.md` | Prior UserAlignment lens analysis. |
| `../issue_23_path_eval/STATUS.md` | Prior locked decisions D1–D22. |
| `../issue_23_path_eval/Appendix.md` | Prior rationale and rejected paths. |
| `../issue_23_path_eval/abast_executive_summary.md` | Coordination artifact for abast (superseded by current vision). |

---

## Open mechanism questions (status after Leadership phase)

From `vision.md` §"Open for the new team to decide", with current state:

1. **Path order for the work.** User preference: restructure first → cherry-pick from abast → implement #23 / #24. *Still open for spec authors; preference is the working assumption.*
2. **Override-resolution mechanism** in the loader. *Composability flagged that priority order is locked but per-category resolution mechanics are not. Spec phase decides per-category policy (especially the loader's current "duplicate IDs are errors" check at `claudechic/workflow_engine/loader.py:344`, which must invert per category).*
3. **Injection mechanism** for agent awareness. *Constrained by A4 (behavioral mirror), A7 (boundary primary-state-only), A11 (two-piece). Spec phase picks the specific mechanism within those constraints. **The composability lens flagged this is the same problem as the existing `phase_context.md` write site — one mechanism solves both.***
4. **Artifact-dir mechanism** for surfacing workflow setup output to subsequent agents. *Still open; spec phase decides.*
5. **Test strategy** — what tests exist, what's needed for boundary enforcement (with A7's distinction baked in), what's needed for override-resolution verification. *Still open; spec phase decides.*

---

*End of STATUS.md.*
