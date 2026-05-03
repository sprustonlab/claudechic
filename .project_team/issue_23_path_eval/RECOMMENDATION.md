# Recommendation: Issue #23 Path Selection

**Project:** `issue_23_path_eval` — coordinating sprustonlab/claudechic against abast/claudechic ahead of "independent claudechic settings" work.
**Source inputs:** the four Leadership lens evaluations and the Fork Diff Report on disk at `.project_team/issue_23_path_eval/`. Every substantive claim here traces back to one of those documents and is cited inline.
**Status:** synthesized; pending alignment-lens grading; user is the final adjudicator.

---

## Headline

**Recommended path: Path 1** — selectively pull from abast first, *then* implement issue #23.
**Confidence: marginal.** The team is split 2–2 across lenses; this recommendation is honest about that and explains why one side carries more weight against your stated stake. You can override.

**Operative rule (from the risk lens, promoted to top-of-document because it governs every other choice):**

> *A path with preconditions skipped is more dangerous than the other path with preconditions met. Skipping preconditions retroactively reclassifies the choice — a "safe path executed unsafely" is, by definition, the unsafe path.*

Translation: this recommendation is *conditional* on the listed preconditions actually getting done. If you commit to Path 1 but skip the preconditions, Path 2 with its preconditions met would have been safer.

---

## Background you already locked in

| What you said | Practical effect on this recommendation |
|---|---|
| `mrocklin/claudechic` (the shared upstream) is out of scope. | No "push it upstream first" path exists in this analysis. |
| Pulls from abast are always selective (cherry-pick, not merge-all). | Both paths are sequenced selective pulls — they differ only in *when*. |
| Claude's namespace (`.claude/` anywhere) is off-limits to claudechic. | The boundary work has to actually move four files out of `.claude/` — see "What's already broken" below. |
| Lost work means all four kinds: commits never landing, features broken post-merge, features reverted in conflict resolution, **and** intent lost even if code survives. | Risk evaluation must score against all four; "intent lost" turns out to dominate. |
| Your fork's work and abast's work are equally valuable. | Conflicts get surfaced for you to decide; this document doesn't quietly favor one side. |
| You can talk to abast. | Several preconditions lean on this; lower-leverage if it turns out to be unavailable in practice. |
| No deadline on #23. | Nothing in this recommendation creates artificial urgency. |
| Settings/config terminology: "Settings" is the user-facing word; "config" is the YAML file. | Locked into the prescriptive glossary; doc-rewrite scope is sprustonlab-only. |
| Boundary lives at `<launched_repo>/.claudechic/config.yaml` (directory form). | The worktree feature must add a parallel `.claudechic/` symlink — see below. |
| Analytics identity is per-project. | Each repo gets its own telemetry ID under the new boundary. |
| Directory layout: keep sprustonlab's `workflow_engine/` (Python) + `workflows/` (YAML data) + `global/` split. | abast's `defaults/...` content gets re-pathed onto this layout when pulled. |
| `/fast` from abast: skip for now, deferred to [sprustonlab/claudechic#25](https://github.com/sprustonlab/claudechic/issues/25). | Removed from the cherry-pick scope of either path. |

---

## What's already broken — both paths must fix this regardless

Issue #23's "don't mix Claude and claudechic settings" rule is **already violated today**. From the terminology lens (§3.1, §3.5) and the architecture lens (§4.1):

| Path claudechic writes today | Where it must go (per your locked decisions) |
|---|---|
| `~/.claude/.claudechic.yaml` (global config) | `<launched_repo>/.claudechic/config.yaml` (per-project; global tier collapses) |
| `<launched_repo>/.claude/hints_state.json` | `<launched_repo>/.claudechic/hints_state.json` |
| `<launched_repo>/.claude/phase_context.md` | `<launched_repo>/.claudechic/phase_context.md` |
| `<launched_repo>/.claude/rules/<doc>.md` | `<launched_repo>/.claudechic/rules/<doc>.md` |

Plus a documentation surface that hard-codes the old location (`CLAUDE.md`, `theme.py`, `errors.py`, `context/CLAUDE.md`, `docs/privacy.md`, `config.py:17`) — all sprustonlab-side, all rewrite together.

Plus a worktree-feature coupling (architecture lens §4.5): `features/worktree/git.py:293–301` symlinks `.claude/` from the main worktree into every new worktree so hooks/skills/local settings carry over. Once claudechic state moves out of `.claude/`, that symlink no longer carries claudechic state. **A parallel `.claudechic/` symlink must be added or worktrees silently lose their claudechic configuration.** abast didn't touch this file (zero churn), so neither path imports a conflict here — but neither path can omit the symlink fix either.

Cross-lens position on this fix: terminology lens, architecture lens, and risk lens all agree it's path-independent and prerequisite. Aligning lens confirms the synthesis must include it as a remediation step regardless of which path you pick.

---

## The forks (just enough context for the recommendation to make sense)

Common ancestor: commit `285b4d1` (2026-04-20). Since then:
- **sprustonlab** is 6 commits / 174 files / +13,606 lines ahead. One large consolidation commit (`317f424` — bundling workflows/hints/rules into the package, splitting engine code into `workflow_engine/`) covers 166 of those files.
- **abast** is 8 commits / 104 files / +6,583 lines ahead. One large consolidation commit (`d55d8c0` — bundling defaults under `claudechic/defaults/`) covers 88 of those files.

Both consolidations addressed the same need (bundle defaults into the package) but landed at **incompatible layouts**: sprustonlab's `claudechic/{workflows,global}/` versus abast's `claudechic/defaults/{workflows,global}/`.

**Crucial caveat from the diff report (Anomaly 1):** The 168/98 raw "only" file counts dramatically overstate divergence. Roughly 85 of abast's files are byte-near-identical mirrors of sprustonlab files at different paths. **Removing the path-mirrors, abast's truly independent file footprint is only ~13–15 files.** Don't read the raw counts as the conflict surface.

**Hot files (the only six modified by both forks since the merge-base):** `app.py` (353 lines of churn), `commands.py` (73), `config.py` (60), `pyproject.toml` (21), `mcp.py` (20), `tests/conftest.py` (8). **All three of issue #23's most-live code-touch sites (`app.py`, `commands.py`, `config.py`) are hot files.**

**A subtle one (Anomaly 3) that drove half the cross-lens disagreement:** `claudechic/workflows/` means *different things on each side now*. On sprustonlab post-consolidation, it's YAML data only (engine code moved to `workflow_engine/`). On abast, it still contains the Python engine. Same path, different contents, different ontological status — and this is invisible to text-merge tooling.

**A scope distinction the diff report flagged (Anomaly 5):** Issue #23's body is about a `/settings` TUI screen and a `docs/configuration.md` reference page. The "boundary" work — moving claudechic out of `.claude/` — is a *userprompt-derived* concern, not in the issue body verbatim. Both #23 and the linked issue #21 treat the current `~/.claude/` location as canonical without questioning it. The boundary work is a scope addition; the issue-body work and the boundary work overlap *only* at `config.py`, `app.py`, `commands.py`, and the test files. The biggest boundary surface (`hints/state.py`, `errors.py`, `theme.py`, `agent.py`, `usage.py`, `features/worktree/git.py`) is in files **neither fork has touched** — the relocation work is mostly path-independent regardless of which path you pick.

---

## The two paths

- **Path 1.** Selectively pull the abast features you want into sprustonlab first, *then* design and implement issue #23 (settings TUI + boundary relocation + docs) on the merged tree.
- **Path 2.** Design and implement issue #23 in sprustonlab first, *then* selectively pull abast features onto the post-#23 tree, translating each cherry-pick to fit the new boundary contract.

Both paths require the same prerequisite zero-step (the four-violation BF1 fix above) and both end in the same conceptual place (sprustonlab + selected abast features + issue #23). They differ only in *when the heavy collisions happen*, *what state the codebase is in when those collisions get resolved*, and *which preconditions are required to execute safely*.

---

## How the four lenses analyzed this — verbatim arguments and where they disagree

The team disagrees, sharply, in a way that rewards being read carefully. The four lens evaluations are on disk; this section is the integrated read.

### Risk lens (Skeptic) → **Path 1**, conditional, reaffirmed by the diff report

Skeptic's risk evaluation is the longest of the four documents and is explicitly framed against your stated North Star ("unable to merge without losing work on other features"). Their core observation:

> *Path 1 concentrates risk in **visible, decision-time** events — designers are alert when conflicts surface and have full context. Path 2 concentrates risk in **post-completion, low-attention** events — designers feel done when conflicts surface, and conflicts feel like noise. The matrix is asymmetric on the dimensions that matter most (features reverted in conflict resolution; intent lost even if code survives), with Path 2 carrying greater hidden risk principally driven by the mirror-tree silent-collision surface.* *(Risk evaluation §2 aggregate read.)*

The decisive risk row in their matrix is one they **added after reading the diff report**: ~85 path-mirror pairs of byte-near-identical content at incompatible paths (`claudechic/workflows/...` versus `claudechic/defaults/workflows/...`). Skeptic scored this **Very High likelihood / Critical impact** under Path 2 because cherry-picking abast's `defaults/...` adds onto a sprustonlab tree where the destination paths don't exist will *apply textually cleanly* and create a parallel duplicate asset tree that is silently disconnected from sprustonlab's loader. This is "the single most dangerous scenario in the entire evaluation" in Skeptic's words (§2 R8).

Skeptic's two concrete worked examples for the dependency-drop risk:

1. abast's `pyproject.toml` change pinning `anthropic==0.79.0` (commit `0ad343b`) is a one-line pin; abast's `/fast` mode (commit `26ce198`) requires it. Pull `/fast` without the pin and the code merges textually but breaks at runtime against an incompatible SDK. *(You've already decided to skip `/fast`, but the pattern generalizes: when cherry-picking selectively, prerequisite chains have to be audited.)*
2. Any abast commit touching `claudechic/workflows/loader.py` cherry-picked onto post-consolidation sprustonlab lands the file at a path where the loader code no longer exists (engine moved to `workflow_engine/`). Textual apply succeeds, runtime broken.

Skeptic's lens conclusion (§6):

> *From the risk lens, Path 1 is preferred, conditional on its preconditions being achievable. The pre-FDR lean was Path 1; the FDR data strengthens rather than weakens this position. The mirror-tree axis is the FDR's most consequential finding and is structurally easier to address pre-#23 than post-#23 (where it falls outside the issue's natural scope).*

Skeptic explicitly names three conditions that would flip their lean to Path 2:
- abast confirms an imminent `/settings` redesign of their own;
- abast cannot or will not converge on a single workflow-tree root;
- abast cooperation turns out unavailable in practice.

Skeptic also surfaces honest counter-weights to their own lean (§6 acknowledged counter-weights): the "quiet zone" finding (most boundary-rewrite files weren't touched by either fork), the path-mirror double-counting reduction (~13–15 truly independent abast files), and the diff report's note that `app.py` collisions are mostly insertion-collision rather than edit-collision. These don't flip the lean but should be visible.

### Architecture lens (Composability) → **Path 2**, strengthened by the diff report

Composability frames the choice not as "merge timing" but as **which axis of variation you stabilize first** (§1). Their key argument:

> *The settings boundary is load-bearing — it's the contract referenced by every read/write into config space. Establishing this boundary FIRST means later decisions (which abast cherry-picks to take, where to place new settings files, how to treat abast's `defaults/workflows/` overlay) are made with the contract in hand. Establishing it LAST means those decisions are made under reduced information.* *(Composability §6 rationale point 1.)*

Their decisive worry about Path 1 is that abast's `claudechic/defaults/workflows/` overlay is itself an unstated settings-architecture decision (defaults vs. user overrides) brushing the same conceptual axis as #23. **Pulling that overlay before #23 lets it implicitly co-decide #23's design surface** rather than being adjudicated against #23's contract.

Composability did a delta-pass after the diff report landed and explicitly **resolved one of their own caveats against Path 1**:

> *My `app.py`-concentration caveat resolves AGAINST Path 1. Per FDR §5 commit attribution, abast's 167-line `app.py` churn is auto-perm UX, `/fast`, full-model-ID, and defaults-bundle hookup — not on the `.claude/`-write sites #23 must move. The collision is textually-near but semantically-tangential — translation cost under Path 2, not a settings-translation cost.* *(Composability §6 updated lens conclusion.)*

Composability honestly names Path 1's *one* genuine advantage (§6 point 5):

> *Path 1's one structural advantage over Path 2 is here: pulling abast's overlay forces the parallelism into a single working copy, where it cannot be silently overlooked. Path 2 risks #23 being designed without ever confronting the overlay if the team does not consult the diff report. This risk is procedural rather than architectural.*

Composability concludes Path 2 because three of the four architectural axes favor it and the fourth (mirror-tree forced visibility) is "procedurally compensable" via mandating diff-report consultation during #23 design — which is then mandated.

### Naming lens (TerminologyGuardian) → **Path 2**

The terminology lens applies one criterion — vocabulary unity — and finds that Path 1 breaks it during step 1 while Path 2 maintains it throughout. Their decisive observation (§5.1):

> *Path 1 step 1 produces a tree with three contested namespaces co-resident (`workflows/` + `workflow_engine/` + `defaults/`) plus a stowaway engine package, before #23 even begins. The boundary-relocation work of #23 then has to be done on top of that compromised state. Path 2 step 1 produces a tree with one canonical vocabulary and clean `.claudechic/` boundaries. Each abast cherry-pick in step 2 is a rename-and-apply against that stable target.*

A pointed counter to the Path 1 framing (§5.1):

> *abast added 7 new contested terms and re-scoped 3 more, while doing nothing to remediate the existing `.claude/` violation. Path 1's premise — "import their alignment work first" — is empirically empty; there is no alignment work on the boundary to import. Path 1 imports only drift.*

The terminology lens also addresses what looks like a Path 1 "loud failure beats silent failure" advantage and inverts it (§5.2):

> *In this specific case, en-masse merge succeeds silently on the broken case (engine Python lands in YAML directory), while cherry-pick fails loudly when the directory doesn't exist. The terminology lens prefers loud failures because they are detectable.*

### Alignment lens (UserAlignment) → **Path 1, marginal**

The alignment lens explicitly does not speak from architecture, risk, or naming — it speaks from how well each lens's recommendation traces back to *your stated stake* (§6.1). Their three reasons for Path 1, each tied to something you actually said:

> *(1) Your explicit stated failure mode is "unable to merge without losing work on other features." This maps directly onto Skeptic's matrix, particularly D6.c (features reverted in conflict resolution) and D6.d (intent lost even if code survives). The lens that maps most directly to the user's stated stake is the lens whose recommendation should win on the alignment dimension.*
>
> *(2) Path 1's preconditions are sprustonlab-internal; Path 2's preconditions add external dependencies (abast-side design-time signoff before sprustonlab implements; a regression-test suite that fails on wrong-path landing — non-trivial test infrastructure investment). Paths whose preconditions sprustonlab can satisfy alone are better-aligned with the user's framing.*
>
> *(3) Your success criterion is stated as confidence to start the chosen path **in a separate session**. A separate session is by definition a context-loss event — procedural mitigations that depend on the team remembering to consult the right document at the right moment are exactly the mitigations most likely to fail across a session boundary. Structural pre-decisions survive context loss; procedural reminders do not.*

The alignment lens is honest that the case for Path 2 is substantive (§6.2):

> *TG's vocabulary-unity argument has real intent-loss substance — a codebase with three co-resident namespaces during the #23 implementation window is itself an intent-loss scenario. Composability's boundary-as-filter is correct on the settings axis. The "quiet zone" finding favors Path 2 mildly. Net: Path 1 wins on the user's stated North Star (lost-work avoidance). Path 2 wins on architectural cleanliness end-state and on most of the truly independent footprint. The user must decide which trade dominates. The alignment lens recommends Path 1 because the user's stated stake is the stake the user actually said.*

Conditions under which the alignment lens would flip (§6.3):
- abast turns out to lack bandwidth to engage on workflow-tree convergence;
- abast has an imminent `/settings` redesign of their own;
- you clarify that "lost work" carries weight on architectural cleanliness as well — i.e., a tree with three co-resident namespaces is itself a form of lost work because intent gets buried in vocabulary fragmentation.

### The 2–2 split, tabulated

| Lens | Recommendation | Decisive argument | Wins on |
|---|---|---|---|
| **Risk** | Path 1 | Mirror-tree silent collision is the dominant Path 2 hazard; the boundary contract has no settings semantics for it to filter against | Your stated failure mode |
| **Architecture** | Path 2 | Boundary-as-filter for everything that carries settings semantics; abast's `defaults/` overlay would otherwise implicitly co-decide #23 | End-state architectural cleanliness |
| **Naming** | Path 2 | Vocabulary unity preserved at every step; Path 1 imports drift, not alignment | Reviewability and onboarding |
| **Alignment** | Path 1 (marginal) | Your stated stake is lost-work avoidance, which maps to risk lens; Path 1's preconditions are sprustonlab-internal; forced visibility survives context loss | Honoring what you actually said |

**This split is substantive content, not a problem to resolve before recommending.** Both sides are operating correctly within their lens. They reach different conclusions because they weight different axes. The recommendation below honors the alignment lens's read (your stated stake wins on the alignment dimension) while leaving you with everything you need to override.

---

## Recommendation: Path 1 (selectively pull → then implement #23)

**Confidence: marginal**, with explicit per-axis breakdown:

| Axis | Confidence in the path-1 call |
|---|---|
| Settings boundary handling | **High** regardless of path — the boundary work mostly happens in files neither fork has touched, and the prescriptive vocabulary you've locked is the same target either way. |
| Workflow-tree resolution | **Medium**, conditional on abast cooperation being available in practice. If that fails, both paths get harder; the path-1 advantage narrows. |
| Mirror-tree silent collision avoidance | **Higher under Path 1** because the parallelism is forcibly visible during pull rather than potentially overlooked post-#23. This is the load-bearing reason for the recommendation. |
| Architectural cleanliness during the transition | **Lower under Path 1** — the tree carries three co-resident vocabularies between step 1 and step 2 of Path 1. The naming lens is correctly worried; this is a real cost being accepted in exchange for the risk-lens advantage. |
| End-state code health | **Equal** between paths — both end in the same place; difference is in the intermediate state and the per-cherry-pick costs along the way. |

The recommendation is conditional on three pre-flight checks that should happen *before* you commit to executing Path 1.

---

## Pre-flight gates (run these before committing to either path; results may flip the recommendation)

These are the "if any of these come back wrong, reread before executing" items the risk lens promoted as conditional gates.

### Pre-flight 1 — Talk to abast about the workflow-tree convergence question

Three concrete questions (from risk-eval §4 revised E2):

1. *Are you willing to rebase your `claudechic/defaults/...` adds onto a single canonical root chosen by sprustonlab?*
2. *Is your `defaults/` choice structural to your fallback-discovery mechanism, or is it a name we can change?*
3. *If we choose `workflows/` as canonical, does your fallback-discovery mechanism still work?*

**What the answers do:**
- abast confirms convergence-willingness AND structural flexibility ⇒ the mirror-tree risk drops materially under both paths; Path 1 still preferred but less urgently.
- abast's `defaults/` is structurally entangled with their fallback discovery and they will not converge ⇒ mirror-tree risk stays Critical under Path 2; Path 1 lean strengthens.
- abast has no maintainer bandwidth to engage on this ⇒ structural pre-decision becomes a unilateral sprustonlab call; Path 1 lean is unaffected at the headline level, but you lose one of its mitigations.

### Pre-flight 2 — Ask abast about their roadmap

One question (from risk-eval §4 E4):

> *In the next changes you plan to make, do any redesign config layout, the `.claude/` boundary, or the `/settings` screen?*

**What the answers do:**
- Imminent `/settings` redesign on their side ⇒ **the recommendation flips to Path 2.** Pulling abast's not-yet-final design under Path 1 would land a parallel design that conflicts with both your #23 vision and abast's near-future direction. Path 2's "design our way first, take compatible bits later (after abast finishes)" becomes safer.
- Imminent `.claude/` boundary work on their side ⇒ coordinate it with #23's boundary fix before either fork commits.
- Nothing imminent in this surface ⇒ recommendation unchanged.

### Pre-flight 3 — Confirm the boundary scope

The diff report's Anomaly 5 finding: issue #23's body and linked issue #21 don't ask for the boundary relocation; that's *your* derived scope. **The boundary work is being added to #23, not implied by it.**

Practical implication for execution: the synthesis must distinguish issue-body work (the `/settings` TUI, `docs/configuration.md`) from boundary work (relocate the four files out of `.claude/`, move config to `.claudechic/config.yaml`, add the worktree symlink mirror, do the doc rewrite). They should sequence separately. The boundary work can mostly proceed in files neither fork touched (the "quiet zone").

---

## What needs to happen to execute Path 1 (the recommended path) — concrete handoff

This list is structured so a fresh agent picking up in a separate session has the order of operations and the pass/fail criteria. **No time estimates** — just what needs to happen.

### Step 0 — Pre-flight (above)

Before any code action: run pre-flight 1 and pre-flight 2. Record answers in the project's STATUS.md. If pre-flight 2 returns "imminent abast `/settings` redesign," stop and re-evaluate (this flips the recommendation to Path 2).

### Step 1 — Enumerate the cherry-pick scope

Write a list of which abast commits go in the pull set, with rationale. The diff report's hazard summary §8/H4 enumerates seven candidate "deliberate non-pulls" that seed this list:
- `fast_mode_settings.json` — already a deliberate non-pull (you skipped `/fast`).
- `/fast` command (`26ce198`) — deferred to issue #25.
- `0ad343b` — the `anthropic==0.79.0` pin — only relevant if `/fast` is on the want-to-pull list (it isn't right now).
- `5700ef5` — auto-perm-default — UX call, defer until you decide whether you want auto-perm as the default startup mode.
- `7e30a53` — auto-perm Shift+Tab cycle — bundled with the auto-perm decision.
- `f9c9418` — full-model-ID validation loosening — independent UX feature; pull or skip on its own merits.
- The entire `claudechic/defaults/` tree — handled separately by Step 2 and the workflow-tree convergence decision.

For each candidate: pull / skip / re-evaluate-after-talking-to-abast. The pull-batch plan must include a "prerequisites" column so dependency chains aren't dropped.

### Step 2 — Resolve the workflow-tree decision (the locked layout, with re-pathing)

You've already locked sprustonlab's split (`workflow_engine/` + `workflows/` + `global/`) as canonical. The pre-flight 1 conversation determines whether abast will rebase their `claudechic/defaults/...` adds onto this layout before sending. If yes: pulls become straightforward. If no: each abast `defaults/...` cherry-pick gets re-pathed at apply time (`git apply --directory` + a path-rewrite pass) — bounded mechanical work per pull. This decision is recorded in writing before any pull happens; that record is the architectural pre-decision the risk lens called load-bearing.

### Step 3 — Add the boundary lint check to CI

Before the first cherry-pick: a CI step (or pre-merge checklist) that fails if claudechic writes inside any `.claude/` directory or if claudechic settings files appear at the launched-repo root (other than the `.claudechic/` directory). This prevents pulled-from-abast code from re-introducing the existing violation pattern. If a pull violates the lint, it's auto-rejected and recorded in the non-pull register (next step) with the violation cited.

### Step 4 — Create the deliberate-non-pull register

A file (the risk lens calls it `NON_PULLED.md`) recording every conscious decision *not* to pull an abast commit. Each entry has: commit SHA, files affected, abast's rationale (if asked), your rejection rationale, and a re-evaluation trigger ("revisit if #23 ships," "revisit if abast rebases their defaults/ tree," "revisit if user requests feature X"). Seed the file with the seven candidates from Step 1's hazard summary on day one. This addresses what the risk lens called "deliberate non-pulls becoming silent divergence."

### Step 5 — Pull, resolve textually, run the post-pull semantic-review checkpoint

For each thematic pull batch:

- **Cherry-pick** the planned commits in dependency order.
- **Resolve textual conflicts** (mostly insertion-collisions per the diff report; not redesigns).
- **Run the semantic review** with these specs (verbatim from risk evaluation §3 / PC1.3):
  - **Artifact reviewed:** the cumulative diff of the just-applied batch + the batch's commit messages + the entry in the pull-batch plan.
  - **Reviewer:** a sprustonlab maintainer who did *not* perform the cherry-picks, paired with the implementer of record for any sprustonlab files touched. (Pairing prevents single-reviewer blind spots.)
  - **Pass criterion:** a written "design diff narrative," exceeding one paragraph, that names what the system now does differently in observable behavior, which design invariants of either fork are now binding, and any "looks fine, behaves differently" risks identified.
  - **Fail criterion:** narrative missing, purely textual ("file X gained N lines"), or omits an invariant the reviewer can name. Failure ⇒ batch reverted, re-planned, re-applied.

### Step 6 — Implement issue #23 on the merged tree

The four-violation BF1 fix plus the issue-body work (`/settings` TUI, `docs/configuration.md`). Most of this work happens in files neither fork has touched (`hints/state.py`, `errors.py`, `theme.py`, `agent.py`, `usage.py`, `features/worktree/git.py`) — the "quiet zone." The hot files (`app.py`, `commands.py`, `config.py`) require care because they now contain merged-from-abast contributions that #23's wiring has to coexist with. The terminology and prescriptive vocabulary you locked (D16/D17) are the targets.

Specifically what needs to happen during this step:
- Move `~/.claude/.claudechic.yaml` content to `<launched_repo>/.claudechic/config.yaml` (with migration logic in `config.py:_load`).
- Move `.claude/hints_state.json` to `.claudechic/hints_state.json` (preserve existing user state during migration).
- Move `.claude/phase_context.md` writes to `.claudechic/phase_context.md`.
- Move the `/onboarding` rules sync from `.claude/rules/` to `.claudechic/rules/`; update the hint at `global/hints.yaml:94` accordingly.
- Add a parallel `.claudechic/` symlink in `features/worktree/git.py` alongside the existing `.claude/` symlink.
- Rewrite the doc surface (`CLAUDE.md`, `theme.py`, `errors.py`, `context/CLAUDE.md`, `docs/privacy.md`, `config.py:17` docstring).
- Add a regression test that runs claudechic in a tmp repo and asserts the post-run filesystem contains exactly `.claudechic/` from claudechic and nothing else (and no claudechic-authored content under `.claude/`). The test is the canonical compliance check for the boundary rule.
- Build the `/settings` TUI screen (issue #23 body scope) and the `docs/configuration.md` reference page.

---

## What changes if you override to Path 2

The architecture and naming lenses both prefer Path 2; the alignment lens noted three flip conditions. If pre-flight 2 reveals an imminent abast `/settings` redesign, Path 2 becomes the recommendation.

If you choose Path 2, the additional preconditions are (verbatim from risk-eval §3):

- **Design-time alignment with abast.** The #23 design must be reviewed and signed off by abast as compatible with their roadmap *before* sprustonlab implements. This is more demanding than Path 1's intent-recovery cooperation; it's external dependency at design time, not after.
- **#23 design explicitly enumerates abast's expected future-pull surface.** A section in the #23 design doc lists files we expect to receive abast changes to and the contracts those changes must satisfy. Must include an explicit canonical-root declaration for the workflow tree even though #23 doesn't directly touch it (otherwise the mirror-tree risk becomes uncontrolled).
- **A regression test suite covering #23's invariants is in place before the first post-#23 cherry-pick.** Must include a test that fails if both `claudechic/defaults/workflows/` and `claudechic/workflows/` contain workflow content. The risk lens calls this "structural rather than procedural" — reviewers see clean cherry-picks one at a time and may not recognize the cumulative parallel-tree pattern until it's built.
- **Per-cherry-pick semantic review** with a *higher* burden than Path 1's: dual signoff (a sprustonlab maintainer plus a designated #23-invariants owner), per-commit invariant citation, explicit silent-shift check, mandatory non-pull-history check.

The architecture lens's argument for accepting these costs is that the boundary contract becomes a principled filter for every subsequent decision; the naming lens's argument is that vocabulary unity is preserved throughout. Both are real benefits. The alignment lens reads them as not outweighing the lost-work risk under Path 2's mirror-tree exposure, but you may weight differently.

---

## Honorable mentions (paths considered and explicitly not recommended)

These were surfaced during the alignment audit as alternatives worth at least naming.

**"Selective cherry-pick of only the alignment-relevant abast changes" (Path 3b).** Effectively absorbed into Path 1 once you decided abast pulls are always selective — selectivity is now the default mechanism for any abast integration. Not presented as a separate option.

**"Freeze abast as read-only reference; never sync" (Path 3c).** Contingent fallback. Becomes the recommendation only if pre-flight 1 reveals abast won't converge on a single workflow-tree root *and* you accept living with the parallel structure indefinitely *and* the silent-collision risk under continued sync becomes unacceptable. Not the current recommendation; named here so it's available if pre-flight comes back unfavorably.

**"Coordinate with abast on a joint settings design before either side implements" (Path 3d).** This isn't a separate path — it's a *tactic* available under either Path 1 or Path 2. The pre-flight conversations above are the concrete coordinate-with-abast actions for this run. The risk lens explicitly named "ask abast to pre-rebase their `defaults/` adds onto whichever root sprustonlab declares canonical, before any cherry-pick" as the highest-leverage cooperation request and recommends running it regardless of path.

---

## Reversal triggers — when to come back and re-evaluate

The recommendation should be revisited if any of these are true:

| Signal | What to do |
|---|---|
| Pre-flight 2 reveals abast has an imminent `/settings` redesign | Flip recommendation to Path 2. The "design our way first, take compatible bits later" framing becomes safer than pulling an unfinished design. |
| Pre-flight 1 reveals abast cannot/will not converge on a single workflow-tree root, AND you accept living with parallel structure | The mirror-tree risk becomes unavoidable in either path; the architecture lens's filter advantage becomes load-bearing for the remaining settings cherry-picks; Path 2 becomes preferred. |
| abast cooperation turns out to be unavailable in practice despite being declared available | Path 1's intent-recovery and convergence-decision mitigations weaken. Path 2's "boundary as principled filter" doesn't depend on abast in the same way. The gap narrows; Path 2 may become preferred. |
| You clarify that "lost work" includes architectural fragmentation as a first-class concept | The alignment lens's tilt toward Path 1 narrows or flips; Path 2's vocabulary-unity argument becomes weightier. |

---

## What this document deliberately did not do

- **Recommend which abast features to pull.** That's a follow-up decision per Step 1 of execution; you've already excluded `/fast`. The remaining candidates (auto-perm, full-model-ID validation, the `defaults/` tree) get individual UX/architecture calls when you start executing.
- **Decide whether `auto` should be the default permission mode startup behavior.** UX call; outside this analysis's scope.
- **Estimate how long any of this takes.** Per your standing rule.
- **Write the #23 implementation.** Out of scope; this is the recommendation, not the build.
- **Override the cross-lens disagreement.** It's surfaced honestly. You adjudicate.

---

## Where to pick this up in a future session

Read this document, then `STATUS.md` (locked decisions D1–D20, baseline findings, cross-lens conclusions), then the four lens evaluations on disk (`composability_eval.md`, `terminology_glossary.md`, `risk_evaluation.md`, `alignment_audit.md`) and the data substrate (`fork_diff_report.md`, `fork_file_map.csv`).

If you're starting execution: begin with Pre-flight 1 (the workflow-tree convergence conversation with abast) — that single conversation gates the highest-leverage decision in the whole sequence and is the one piece of work that's hardest to do later than now.

If you're re-opening the recommendation itself: the reversal triggers above are the concrete signals to look for.

---

*End of recommendation.*
