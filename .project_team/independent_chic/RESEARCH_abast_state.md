# RESEARCH — abast/claudechic current state vs. our plan

**Author:** Researcher2 (project_team `independent_chic`).
**Date:** 2026-04-27.
**Charter:** assess whether `abast/claudechic` has moved on since our cherry-pick set was locked, and what the impact is on `SPEC.md` / `STATUS.md`. Operational tone per L14.

---

## 1. Executive summary

- **Cherry-pick set (Group F) is intact.** All 9 catalogued commits exist in `abast/claudechic` with their original SHAs. No rewrites, retractions, or content edits. Our locked A2/A8 decisions can be applied as-written.
- **abast pushed 8 new commits on 2026-04-26** (one day before this research run). HEAD moved from `9fed0f3` (the latest commit our spec catalogues) to `7dcd488e`. These are NEW since our analysis.
- **abast has substantially executed our Group A restructure already.** `claudechic/global/`, root-level workflow YAML directories, and `claudechic/workflow_engine/` are gone in abast; their content lives at `claudechic/defaults/{global,workflows}/` and `claudechic/workflows/` (engine code) — the exact target shape SPEC §1.1 describes. Group A plan is now also a candidate for **adoption from abast** rather than re-execution from scratch.
- **Two of the new commits change the inter-agent MCP tool API** (`ask_agent` → `message_agent`; `tell_agent` merged into `ask_agent` with `requires_answer` kwarg). This collides with our two-tool design (used by every workflow agent today). Not in our spec. Needs a user decision on whether to track abast or hold the existing API.
- **Plan validity: needs revision.** The cherry-pick set itself is unaffected. Group A (and to a lesser extent B, C, D, E) need a rebase decision: do we still execute SPEC §1 from scratch, or fast-forward onto abast's restructured tree and re-derive the surrounding groups? The user is the right person to call this — see §7. **Strongly recommend reaching out to abast before proceeding** (per L11).

---

## 2. abast/claudechic current state

| Field | Value |
|---|---|
| **GitHub coordinates** | `abast/claudechic` (https://github.com/abast/claudechic) |
| **Owner** | `abast` (Arco Bast, basta@hhmi.org) |
| **Visibility** | Public |
| **License** | MIT |
| **Default branch** | `main` |
| **HEAD SHA** | `7dcd488e17396a90622585cd5c877622e757fc42` |
| **HEAD message** | `feat: testing sub-cycle with Generalprobe standard` |
| **HEAD date** | 2026-04-26 22:23 UTC |
| **Branch protection** | Off (no required checks; not protected) |
| **Note** | A second public repo `abast/claudechic-1` (a fork; last push 2026-02-27) also exists and is **not** the active fork. The active fork is `abast/claudechic` (a non-fork sibling repo). |

The merge-base reference `285b4d1` (`feat: add clear finished tasks button to TodoPanel sidebar`, 2026-04-21 01:52) is reachable from HEAD; it is the parent of `d55d8c0` and the chain extends through all 9 cherry-pick candidates and the 8 new 2026-04-26 commits.

---

## 3. Cherry-pick verification

All 9 SHAs from STATUS A2/A8 + SPEC §6.1 verified against `abast/main` HEAD. Each commit is present, unchanged, and reachable from HEAD.

| Short SHA | Full SHA | Date | Decision (locked) | Status |
|---|---|---|---|---|
| `9fed0f3` | `9fed0f334a9349f0ab533e74e81f80679ceb9c91` | 2026-04-22 04:22 | Pull | Unchanged |
| `8e46bca` | `8e46bca4710a77adbd0af620256cf9616d43fa94` | 2026-04-22 04:04 | Pull | Unchanged |
| `d55d8c0` | `d55d8c025f779fd747acabedad16aa6fc7808f62` | 2026-04-21 14:31 | Skip (A8) | Unchanged |
| `f9c9418` | `f9c9418727ccf8b08b12b64bcfb8c68ec3c3025c` | 2026-04-22 04:08 | Pull | Unchanged |
| `5700ef5` | `5700ef55e245f2d3d96598f247d3bbb0f2567629` | 2026-04-22 04:14 | Pull | Unchanged |
| `7e30a53` | `7e30a53a127fb3a462a756b1235f934911236990` | 2026-04-22 04:09 | Pull | Unchanged |
| `26ce198` | `26ce198c2f57ca0d2aebb30ce142beb8d47412b6` | 2026-04-22 04:16 | Skip (L12) | Unchanged |
| `0ad343b` | `0ad343bde0d7e1c22165f3a70ba639c7e26e2bff` | 2026-04-22 04:05 | Skip | Unchanged |
| `claudechic/fast_mode_settings.json` | (file shipped by `26ce198`) | 2026-04-22 04:16 | Skip | Unchanged |

**Cherry-pickability:** the 5 Pull commits were authored on 2026-04-22, before abast's restructure (2026-04-26). They apply against pre-restructure paths. Our HEAD `317f4244` (sprustonlab) is also pre-restructure. **Cherry-pick should apply cleanly; no rebase required.** `8e46bca` still touches workflow path resolution and SPEC §0.3 still applies (must land after Group A).

---

## 4. New commits since the catalogue cutoff

Eight new commits between abast's prior HEAD (`9fed0f3`, 2026-04-22) and current HEAD (`7dcd488e`, 2026-04-26). All authored by Arco Bast.

| Short SHA | Date | Message | Files | Classification |
|---|---|---|---|---|
| `7dcd488e` | 2026-04-26 22:23 | `feat: testing sub-cycle with Generalprobe standard` | 16 (project_team workflow files only) | **Out of scope** for this run (workflow content; orthogonal to #23/#24) — but **of interest** since it shows abast is iterating on `project_team` workflow design. |
| `a60e3fe4` | 2026-04-26 21:47 | `chore: stub out guardrails modal with not-yet-implemented notice` | 1 (`app.py`, −36 / +2) | **Conflicts** with `accf332d` (same chain, partial revert of new GuardrailsModal wiring). Indicates that `accf332d`'s GuardrailsModal landed unfinished in abast and was stubbed out within hours. |
| `ff1c5aec` | 2026-04-26 21:36 | `refactor: rename ask_agent to message_agent` | 28 (mcp.py + every project_team identity.md + tests + CLAUDE.md) | **Conflicts** with our spec. We use `ask_agent` and `tell_agent` constantly. Public MCP tool API rename. NOT mentioned in SPEC. |
| `1d6d4327` | 2026-04-26 21:32 | `refactor: merge tell_agent into ask_agent with requires_answer kwarg` | 28 (same surface as above) | **Conflicts** with our spec. End-state is one tool with `requires_answer` kwarg. NOT mentioned in SPEC. Bundle with `ff1c5aec`. |
| `2f6ba2e5` | 2026-04-26 21:28 | `docs: update file map with guardrails, digest, and modal changes` | 1 (`CLAUDE.md` only) | **Out of scope** (downstream doc update for `accf332d`). |
| `8f99f03f` | 2026-04-26 21:27 | `test: update tests for template variables, engine checks, and widget refactor` | 6 (test files only; `+567/−79`) | **Bundle** with `accf332d` (test coverage for the same feature). |
| `accf332d` | 2026-04-26 21:27 | `feat: add workflow template variables, dynamic roles, effort cycling, and guardrails UI` | 30 (NEW: `paths.py`, `guardrails/digest.py`, `widgets/modals/guardrails.py`; DELETED: `widgets/modals/diagnostics.py`; modified: `app.py +244/−38`, `footer.py +110/−11`, `engine.py`, `loader.py`, `agent_folders.py`, `agent_manager.py`, defaults/global/rules.yaml, etc.) | **Major overlap with our Group A + Group E + Group G**. Introduces `$STATE_DIR`/`$WORKFLOW_ROOT` template variables, moves state to `~/.claudechic/workflow_library/{project_key}/{project_name}/`, adds `claudechic/paths.py` for centralized path computation. **This is half of the work we plan for Groups B + E**. |
| `003408ac` | 2026-04-26 21:23 | `fix: improve guardrail and advance-check messaging to prevent agent retry loops` | 3 (`checks/builtins.py +70/−13`, `guardrails/hooks.py +22/−1`, `mcp.py +75/−22`) | **Potentially-pull candidate**. Looks like a UX fix for guardrail/advance-check messages. Touches files our work will also touch (`mcp.py`); needs evaluation. |

**No `/fast` follow-up commits.** `26ce198` is the most recent `/fast` change in abast; no fixes or improvements have landed since. Deferral to sprustonlab/claudechic#25 remains clean.

---

## 5. abast's own restructure status

abast has substantially executed the file moves SPEC §1.1 plans for Group A.

| SPEC §1.1 plan | abast/main current state | Status |
|---|---|---|
| `claudechic/workflow_engine/*.py` → `claudechic/workflows/*.py` | `claudechic/workflow_engine/` does not exist; `claudechic/workflows/` contains engine code (engine.py, loader.py, agent_folders.py modified by `accf332d`). | **Done in abast.** |
| Root `workflows/{audit,cluster_setup,codebase_setup,git_setup,onboarding,project_team,tutorial_extending}` → `claudechic/defaults/workflows/...` | `claudechic/defaults/workflows/{audit, cluster_setup, codebase_setup, git_setup, project_team, tutorial, tutorial_extending, tutorial_toy_project}` exists. **No `onboarding` directory** (abast moved onboarding to `claudechic/onboarding.py` Python module). **Adds `tutorial` and `tutorial_toy_project`** (not in our plan). | **Done with deltas.** |
| `claudechic/global/{hints,rules}.yaml` → `claudechic/defaults/global/...` | `claudechic/defaults/global/{hints.yaml, rules.yaml}` exists. `claudechic/global/` does not exist. | **Done in abast.** |
| `claudechic/mcp_tools` → `claudechic/defaults/mcp_tools` | `claudechic/defaults/mcp_tools/` does not exist (404). `claudechic/mcp_tools/` also does not exist in abast — appears deleted. | **Diverges.** abast removed `mcp_tools/` entirely; our plan moves it under `defaults/`. |

**Additional abast deltas vs. our spec:**

- **`claudechic/paths.py` (new file in abast).** 30 lines. Defines `WORKFLOW_LIBRARY_ROOT = ~/.claudechic/workflow_library` and `compute_state_dir(workflow_root, project_name) → ~/.claudechic/workflow_library/{project_key}/{project_name}/`. This is abast's user-tier state layout. **Differs from our SPEC's `~/.claudechic/` mirroring `~/.claude/`** (L6) — abast nests further under `workflow_library/{project_key}/`. This is a meaningful semantic difference: we plan a flat user-tier; abast has a per-project user-tier carve-out for workflow state.
- **`$STATE_DIR` / `$WORKFLOW_ROOT` template variables** added to workflow YAML manifests (in `accf332d`). Substitution happens in the loader. **Overlaps with our Group E artifact-dir substitution** (SPEC §5.3); needs reconciliation.
- **No `claudechic/context/` directory** in abast (we have one; bundled `.md` files for Group D's awareness install live there in our plan).
- **No `claudechic/audit/` directory** in abast (we have one).

**Bottom line:** abast has pushed roughly the layered-defaults shape of SPEC §1.1 forward, *plus* a workflow-state relocation that overlaps with SPEC §5 and §2. Exact target trees diverge in three places (`onboarding/`, `mcp_tools/`, user-tier nesting). This means our plan's Group A is no longer pure file-moves; it's now a **diff-and-reconcile** against abast's restructure.

---

## 6. Open PRs / issues in abast/claudechic

| # | State | Title | Relevance |
|---|---|---|---|
| #6 | Closed | `fix: /resume broken on Windows — wrong session path + encoding crash` (closed 2026-04-22) | Out of scope (Windows compat already addressed on sprustonlab side). |
| #8 | Open | `Feature: Markdown viewer for diff view` (opened 2026-04-09) | Out of scope. |
| #9 | Closed | `Advance check UX: show context and auto-focus agent` (closed 2026-04-11) | Out of scope (delivered by sprustonlab/claudechic upstream). |

No open PRs. The 7 historical PRs are all closed/merged from sprustonlab→abast directions, none active.

**No abast-side discussion of our restructure.** abast has been moving fast independently; no signals that they are aware of `independent_chic` or coordinating on it. **Direct outreach is the only way to coordinate per L11.**

---

## 7. Recommended impact on our plan

### 7.1 Cherry-picks needing re-verification

**None.** All 9 commits are unchanged; the 5 Pull commits cherry-pick cleanly onto our pre-restructure HEAD.

### 7.2 New commits worth considering

In rough priority order:

1. **`accf332d` — workflow template variables + paths.py + guardrails UI** — this is the biggest decision. abast has implemented a pattern that overlaps with our Groups A/B/E in non-trivial ways (`$STATE_DIR`/`$WORKFLOW_ROOT` substitution, user-tier `~/.claudechic/workflow_library/` layout, `paths.py` centralization). The team should evaluate whether to adopt the pattern, the structure, or neither. **Conflict with SPEC §5.3** (artifact-dir substitution mechanism) and **SPEC L6** (user-tier flat layout).
2. **`003408ac` — guardrail / advance-check messaging fix** — small (3 files, ~165 LOC). Independent UX improvement. Likely worth pulling regardless of other decisions.
3. **`a60e3fe4` — guardrails modal stub revert** — only useful if `accf332d` is adopted (it's a follow-up that backs the modal out). Bundle/skip together with `accf332d`.
4. **`ff1c5aec` + `1d6d4327` — `ask_agent`/`tell_agent` API change** — public MCP tool surface change. **Reject by default** unless the user wants to track abast's API. Adopting this is a breaking change for every workflow that uses these tools. Our team uses both extensively.
5. **`7dcd488e` — testing sub-cycle in `project_team` workflow** — orthogonal to #23/#24. Out of current scope but signals abast is iterating on the project_team workflow we're using. Should be tracked, not pulled this run.
6. **`8f99f03f`, `2f6ba2e5`** — bundle with `accf332d` (test + doc updates). Adopt with parent or skip.

### 7.3 SPEC sections that need updating (conditional on user decision)

If user decides to **continue with the locked plan as-is** (ignore new abast commits beyond cherry-picks):
- No SPEC changes required. Cherry-pick set is intact. Group A re-executes from scratch on our pre-restructure HEAD.

If user decides to **adopt abast's restructure as the Group A starting point**:
- **§1.1** (file moves) → replace with "merge abast/main commit-range `285b4d1..accf332d` into our main; reconcile three deltas" (`onboarding/`, `mcp_tools/`, `tutorial`/`tutorial_toy_project` additions).
- **§1.5** (Group A acceptance) → adjust acceptance bullets to verify post-merge tree.
- **§2** (Group B) → re-evaluate. abast's `paths.py` already centralizes some of the path computation Group B intends to add. Group B may shrink or split.
- **§5** (Group E artifact dirs) → reconcile against abast's `$STATE_DIR`/`$WORKFLOW_ROOT` substitution. May share substring of mechanism.
- **§6.1** (cherry-picks) → mark `8e46bca` as **already-applied** (it's reachable from abast's HEAD; pulling abast's restructure includes it).
- **§7.1** (Group G UI surfaces) → factor in abast's new `EffortLabel` in footer and the (stubbed) `GuardrailsModal`.
- **STATUS A2/A8/A13** → no change to cherry-pick decisions; A13's `~/.claude/rules/` install is independent of restructure-merge.
- **STATUS L6** → potentially revisit. abast's `~/.claudechic/workflow_library/{project_key}/{project_name}/` nests one level deeper than L6's flat-mirror plan.

If user decides to **adopt abast's MCP tool API change too** (`message_agent` with `requires_answer`):
- Every `tell_agent` and `ask_agent` reference in workflow markdown files updates. Multiple SPEC sections reference these. Estimate: ~15 spec edits. **Strongly recommend rejecting** unless user explicitly wants the unified API.

### 7.4 Cross-fork strategy reconsideration

L11 frames abast cooperation as a bidirectional cross-pollination. Right now we are cherry-picking from abast; abast is not pulling from us (no open PRs from sprustonlab into abast since the closed PR #5 in 2026-04-02). The new `accf332d` adds restructure work that **could** land in sprustonlab via a bulk merge, **could** be re-implemented by us, or **could** stay one-directional indefinitely.

**Recommendation: switch from "cherry-pick five commits" to "either bulk-merge abast/main up to a chosen SHA, or coordinate explicitly".** The cherry-pick model assumed abast had a small fixed set of fixes for us. That's no longer accurate; abast has done partial restructure work that overlaps with three of our work groups. Coordinating directly is now meaningfully cheaper than re-deriving the same restructure on our side.

### 7.5 Outreach recommendation (per L11)

**Yes — the user should reach out to abast before this run continues.** Specific questions for abast that would change our plan:

1. Is the `claudechic/defaults/{global,workflows}/` layout intended as the long-term shape, or experimental? (Determines whether we adopt or fork.)
2. Is `~/.claudechic/workflow_library/{project_key}/{project_name}/` intended as the user-tier convention, or transitional? (Determines whether SPEC L6 needs updating.)
3. Is the `message_agent` rename + `requires_answer` merge intended to be the canonical inter-agent API? (Determines whether our workflow content adopts it.)
4. Is `claudechic/paths.py` intended as the centralized path module? (Determines whether our Group B work merges into it or stays separate.)
5. Is abast open to a bulk merge of restructure-related commits in either direction? (Determines whether we keep the cherry-pick model or shift to merge.)

A 30-minute conversation will save substantial spec-revision work.

### Not Recommended (and why)

- **Adopting abast's `message_agent` rename without explicit user approval** — breaking API change; collides with all workflow `tell_agent`/`ask_agent` directives.
- **Merging abast/main wholesale** without understanding the `accf332d` semantics — `accf332d` includes a `GuardrailsModal` that was stubbed out 24 minutes after landing (`a60e3fe4`), suggesting it's not stable. Take the file-move skeleton; defer the runtime additions.
- **Pulling `accf332d` as a cherry-pick** rather than a merge — too large (30 files, ~600 LOC) to apply atomically with confidence.

### [WARNING] Domain validation required

Two domain-critical reconciliations need expert review (Composability + Skeptic) before any structural decision:

1. **State-dir nesting semantics.** SPEC L6 mirrors `~/.claude/`'s flat layout. abast nests as `~/.claudechic/workflow_library/{project_key}/{project_name}/`. The two cannot both be true; one of them is the user-tier convention. Composability owns this call.
2. **Loader-substitution ownership.** SPEC §5.3 (artifact-dir substitution) and abast's `$STATE_DIR`/`$WORKFLOW_ROOT` substitution are different mechanisms for adjacent problems. If both ship, the loader has two substitution passes. Composability + Implementer should reconcile.

---

## 8. Sources

| Tier | Source |
|---|---|
| T3 | `gh api repos/abast/claudechic` (repo metadata) |
| T3 | `gh api repos/abast/claudechic/branches/main` (HEAD `7dcd488e`) |
| T3 | `gh api repos/abast/claudechic/commits` (commit history; per_page=50) |
| T3 | `gh api repos/abast/claudechic/commits/<sha>` (per-commit file lists, ×8 new commits + ×9 catalogued commits) |
| T3 | `gh api repos/abast/claudechic/contents/...?ref=main` (tree shape verification) |
| T3 | `gh api repos/abast/claudechic/git/trees/main?recursive=1` (full tree under `claudechic/defaults/`) |
| T3 | `gh issue list --repo abast/claudechic --state all`; `gh pr list --repo abast/claudechic --state all` |
| T3 | `gh api repos/sprustonlab/claudechic/commits` (sprustonlab side commits since merge-base) |
| Internal | `.project_team/independent_chic/SPEC.md` §0.3, §1.1, §5, §6.1 |
| Internal | `.project_team/independent_chic/STATUS.md` (locks L11, L12; amendments A2, A8, A13) |
| Internal | `.project_team/independent_chic/RESEARCH.md` (merge-base reference, prior context) |

---

*End of RESEARCH_abast_state.md.*
