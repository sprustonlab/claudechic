# Composability Evaluation — Path 1 vs Path 2

**Author:** Composability (Leadership)
**Lens:** architecture, module boundaries, coupling, separation of concerns
**Mode:** symmetric evaluation through this lens; no advocacy beyond what the lens supports
**Inputs grounded in:**
- `STATUS.md` (D1–D15 locked decisions, BF1–BF7 baseline findings)
- `userprompt.md`
- `fork_file_map.csv` (per-file divergence map; 272 rows)
- `fork_diff_report.md` (narrative, themes, hazards H1–H4, anomalies)
- Direct codebase reads of `config.py`, `hints/state.py`, `app.py` settings sites, `commands.py`, `sessions.py`, `usage.py`, `help_data.py`, `theme.py`, `errors.py`, `audit/audit.py`, `onboarding.py`, `hints/triggers.py`, `features/worktree/git.py`
- Cross-lens findings forwarded from Skeptic (R5, mirror-tree pattern) and TerminologyGuardian (BF1 expansion, BF7 worktree symlink)
- This document was first written against the CSV alone, then delta-passed after the narrative FDR landed; conclusion reaffirmed and refined, not flipped.

---

## 1. Frame

The proposition under evaluation is a sequencing decision over **two cooperating refactors**:

- **Refactor A — Issue #23**: establish a settings-domain boundary (claudechic settings out of any `.claude/` directory; only `.claudechic/` content under launched-repo root) and a `/settings` TUI / configuration reference.
- **Refactor B — Sync from abast**: selectively pull abast's diverged commits (D3) without losing feature work on either fork (D6).

Through the composability lens, the choice is not "merge timing." It is **which axis of variation you stabilize first** before perturbing the other. Three axes apply:

1. **Settings-domain axis** — `claude` config namespace vs `claudechic` config namespace. The current code violates this boundary (BF1; D5). #23 establishes it.
2. **Footprint/locality axis** — what claudechic writes to launched-repo root. Userprompt boundary (derived scope, D11) says *only* `.claudechic/`. Currently, `<project>/.claudechic.yaml` (a file, not a directory), `<project>/.claude/hits.jsonl`, `<project>/.claude/hints_state.json`, `<project>/.claude/phase_context.md`, and `<project>/.claude/rules/*` (installed by onboarding) all sit in launched-repo root. All but one (`.claudechic.yaml`) violate D5; the file form of `.claudechic.yaml` violates the userprompt boundary in spirit. **D17 (locked) ratifies the directory form: `.claudechic/config.yaml` inside a `<project>/.claudechic/` directory** — `.claudechic/` becomes the single permitted top-level claudechic footprint, and project config lives at `.claudechic/config.yaml` rather than as a sibling file. **Per BF1 (expanded by TerminologyGuardian), the canonical violation set is four launched-repo paths plus a wide documentation surface (`CLAUDE.md`, `theme.py`, `errors.py`, `context/CLAUDE.md`, `docs/privacy.md`, `config.py`) that references the old `~/.claude/.claudechic.yaml` location.** Per **BF7** (TerminologyGuardian), the worktree feature has built a *symlink dependency* on the violation: `features/worktree/git.py:293–301` symlinks `<main_wt>/.claude` into every new worktree so hooks/skills/local settings travel. Once #23 relocates claudechic state out of `.claude/`, the symlink no longer carries claudechic state; #23 must add a parallel `.claudechic/` symlink or the worktree feature regresses silently.
3. **Fork-divergence axis** — sprustonlab feature work vs abast feature work; the surface that selective pulls modulate.
4. **Mirror-tree axis** *(R5, originally surfaced by Skeptic; promoted here to an axis-of-variation in its own right because it is a structural composability concern, not only a risk)* — the two forks have independently produced **parallel directory structures for the same content**: `claudechic/workflows/<workflow>/<role>/...` (sprustonlab) and `claudechic/defaults/workflows/<workflow>/<role>/...` (abast). Roughly 90 CSV rows are matched pairs across this parallelism. This is a *convergence-by-parallel-divergence*: both forks needed a home for shipped workflow content and chose differently. The axis at issue is **defaults-vs-user-overrides** — i.e., does claudechic ship workflow content as immutable defaults that user-local content overrides, or as a single editable tree? This axis is *adjacent to* the settings-domain axis (axis 1) — both are about "what does claudechic ship as authority vs what does the user own?" — but it manifests in tree shape rather than in path namespace.

Path 1 perturbs axis 3 first, then axes 1+2 (and axis 4 lands inside the pull). Path 2 perturbs axes 1+2 first, then axis 3 (and axis 4 lands either as part of #23's scope or is deferred). The composability question: **which sequencing leaves a smaller and better-isolated coupling surface in flight at any moment?**

The settings-domain and footprint/locality axes are *coupled to each other* (they are largely co-resident in the same modules — `config.py`, `app.py`, `hints/state.py`, `onboarding.py`) and #23 should treat them as a single refactor. They are *partially decoupled* from the fork-divergence axis: the intersection of "files #23 must rewrite" with "files abast diverged on" is small but non-empty (see §4).

---

## 2. Path 1 evaluation — selectively pull from abast → implement #23

### Axis-by-axis disturbance under Path 1

**Settings-domain axis:** stable through the pull phase, then perturbed by #23. The relocation contract (where claudechic config moves to under D4) is designed *after* abast's deltas have already landed in the relevant files. The refactor sees one codebase that contains both forks' contributions to settings-territory modules (notably `config.py` ±2/-2 from abast, plus minor footprint in `app.py`).

**Footprint/locality axis:** stable through the pull phase. Anything abast pulls in that writes into `.claude/` or into launched-repo root joins the existing violations and is relocated together by #23.

**Fork-divergence axis:** perturbed first. Selective pulls (D3) operate against the *current* (boundary-violating) settings layout. Cherry-picks are textually clean against present file shape but encode the OLD settings model. Each cherry-pick lands as-authored.

### Architectural costs (composability lens)

- **Single relocation event.** The settings boundary is drawn once, with full information from both forks. There is no "re-derive the boundary per cherry-pick" cost.
- **Enlarged refactor scope.** The #23 refactor surface now also contains abast's contributions. abast's churn on settings-territory files is small (config.py ±4 lines total, hints/state.py 0, tests/test_config.py +28/-29) but non-zero, so the scope expansion is real but bounded.
- **Pre-existing violations are pulled-and-then-fixed.** Anything abast wrote into `.claude/` (e.g., new write paths, new state files) becomes part of the BF1 fix-list. This is fine in principle but means BF1's "must include a fix" obligation now covers abast's additions too.
- **Unresolved meta-decision pulled in early.** abast introduced a parallel `claudechic/defaults/workflows/...` overlay (visible across ~90 rows of the CSV with `abast-only` tag, mirroring sprustonlab's `claudechic/workflows/...` paths). This is itself an unstated settings-architecture decision — *defaults vs. user overrides* — that brushes the same conceptual axis as #23. Pulling this overlay before #23 forces #23 to either honor it, contradict it, or carve around it. **This is the largest hidden coupling under Path 1.**
- **abast's `claudechic/fast_mode_settings.json` (in-package settings file) needs adjudication BEFORE the new boundary exists** — i.e., placement is decided ad hoc and may need to be moved again under #23.

### Coupling surfaces opened/closed under Path 1

- **Opened (during pull phase):** every cherry-pick that crosses settings-territory introduces a textual-but-not-semantic merge surface (BF3). Coupling to old settings layout encoded in pulled commits.
- **Opened (during #23 phase):** the relocation now binds against a larger working set; design decisions for #23 must accommodate abast's `defaults/workflows/` overlay decision (unless explicitly carved out).
- **Closed (after #23):** settings-domain and footprint/locality boundaries established as a single coherent contract.

### Sequencing of design decisions under Path 1

```
1. Decide selective-pull set (which abast commits to take) ──────── against OLD layout
2. Decide deliberate non-pulls (BF5)                                against OLD layout
3. Pull. Resolve textual + semantic conflicts (BF3)                 against OLD layout
4. Decide #23 target locations (D4)                                 with full information
5. Decide #23 migration semantics                                   with full information
6. Relocate. Update tests.                                          against pulled+sprustonlab union
```

Decisions 1–3 are made before the new boundary exists; decisions 4–6 are made after the new boundary is conceived. The decisions in 1–3 cannot be informed by the decisions in 4–6, so they are made under reduced information.

---

## 3. Path 2 evaluation — implement #23 → selectively pull from abast

### Axis-by-axis disturbance under Path 2

**Settings-domain axis:** perturbed first against a single-fork codebase (sprustonlab only). The relocation contract is drawn against present sprustonlab state without abast's contributions in scope. The refactor surface is smaller.

**Footprint/locality axis:** perturbed first, alongside settings-domain. After #23, the launched-repo-root contract is enforceable.

**Fork-divergence axis:** perturbed second. Selective pulls (D3) now target a codebase whose settings layout has changed. Each cherry-pick that touches settings-territory files (config.py, hints/state.py, app.py settings sites, onboarding.py, test_config.py) was authored against the OLD layout and must be **re-projected** onto the new layout before landing.

### Architectural costs (composability lens)

- **Smaller refactor scope.** #23 sees only sprustonlab's deltas. The relocation is designed against a smaller working set with fewer competing constraints.
- **Per-cherry-pick translation cost.** Every abast commit that touches a settings-territory file requires manual semantic translation when later landed. The cost is distributed across cherry-picks rather than concentrated. From the CSV: abast's settings-territory churn is `config.py` (4), `app.py` (167 of which an unknown subset is settings-related — `commands.py` reads + plans dir + agent_manager-style work likely dominates), `agent.py` (9, plans-dir territory), `tests/test_config.py` (57). Translation cost is bounded but real.
- **New boundary becomes a filter.** Once the contract exists, every incoming cherry-pick can be evaluated against it. "Deliberate non-pulls" (BF5) can be reasoned about with the contract in hand: a pull that contradicts the boundary is rejected on principle.
- **abast's `defaults/workflows/` overlay** is evaluated *after* the settings architecture is set. If the overlay's defaults-vs-overrides intent is compatible with the new boundary, it is pulled; if not, it is rejected or rewritten. The decision is made with the boundary in scope.
- **abast's `claudechic/fast_mode_settings.json`** is placed by the new rule, not ad hoc.

### Coupling surfaces opened/closed under Path 2

- **Opened (during #23 phase):** the relocation binds against a smaller working set. No abast-derived coupling.
- **Opened (during pull phase):** each cherry-pick crossing the settings perimeter has BOTH textual and semantic translation requirements (worse than Path 1's textual-only conflicts in the same files), but on a per-commit basis with the boundary as a known contract.
- **Closed (after #23):** settings-domain and footprint/locality boundaries established before any abast integration. Boundary is a **gating contract** for subsequent pulls.

### Sequencing of design decisions under Path 2

```
1. Decide #23 target locations (D4)                                 against sprustonlab only
2. Decide #23 migration semantics                                   against sprustonlab only
3. Relocate. Update tests.                                          against sprustonlab only
4. Decide selective-pull set (which abast commits to take)          with new contract in hand
5. Decide deliberate non-pulls (BF5)                                with new contract in hand
6. Pull. Translate each settings-touching cherry-pick onto new layout
```

Decisions 1–3 are made against a smaller, more legible codebase. Decisions 4–6 are made with the new contract available as a filter.

---

## 4. Cross-cutting architectural concerns — modules most affected

Drawing the file-level intersection of (a) modules that must change under #23 and (b) modules abast diverged on. The full per-file map is in `fork_file_map.csv`; relevant subset reproduced here.

### 4.1. Settings-domain modules — currently violating D5 (BF1)

| Module | Violation | sprustonlab churn | abast churn | Tag |
|---|---|---:|---:|---|
| `claudechic/config.py` | Writes `~/.claude/.claudechic.yaml` (line 17). Migrates from old path (lines 28–32). | 56 | 4 | both |
| `claudechic/hints/state.py` | Writes `<project>/.claude/hints_state.json` (line 127). Sole owner of that file by design (line 8 docstring). | 81 | 0 | sprustonlab-only |
| `claudechic/app.py` | Writes `<project>/.claude/hits.jsonl` (line 1492); writes/deletes `<project>/.claude/phase_context.md` (lines 1848, 1925). | 186 | 167 | both |
| `claudechic/onboarding.py` | Installs context docs into `<project>/.claude/rules/` (per `workflows/onboarding/`). Indirect: drives writes into Claude's namespace. | 139 | 0 | sprustonlab-only |
| `claudechic/hints/triggers.py` | Reads `<project>/.claude/rules/` to detect drift (lines 26–46). Indirect: depends on the install location chosen by onboarding. | 82 | 0 | sprustonlab-only |
| `claudechic/theme.py` | References `~/.claude/.claudechic.yaml` indirectly via `config.CONFIG`. | 0 | 0 | unchanged |
| `claudechic/errors.py` | Mentions `~/.claude/.claudechic.yaml` in docstring (line 77). | 0 | 0 | unchanged |
| `claudechic/context/CLAUDE.md` | Documents the violating path to users (line 79). | 100 | 0 | sprustonlab-only |
| `claudechic/features/worktree/git.py` | **BF7.** Symlinks `<main_wt>/.claude` into new worktrees (lines 293–301). After #23, claudechic state no longer rides this symlink; a parallel `.claudechic/` symlink must be added or worktrees silently lose claudechic state. | 6 (+4/-2) | 0 | sprustonlab-only |
| Doc surface (BF1 expanded) | `CLAUDE.md` (root), `claudechic/theme.py`, `claudechic/errors.py`, `claudechic/context/CLAUDE.md`, `docs/privacy.md`, `claudechic/config.py` docstrings — all reference `~/.claude/.claudechic.yaml`. Migration must update these in lockstep. | mixed | mixed | mixed |

### 4.2. Modules that read Claude's namespace legitimately (out-of-scope for #23 relocation, but boundary-relevant)

Per D5, these **stay** — they are claudechic *introspecting* Claude Code's data, not writing into it:

| Module | Reads | sprustonlab | abast | Notes |
|---|---|---:|---:|---|
| `claudechic/sessions.py` | `~/.claude/projects/`, `~/.claude/plans/` | 28 | 0 | Claude Code session JSONL discovery |
| `claudechic/history.py` | `~/.claude/history.jsonl` | low | low | Claude command history |
| `claudechic/usage.py` | `~/.claude/.credentials.json` | 2 | 0 | Claude OAuth token |
| `claudechic/help_data.py` | `~/.claude/settings.json`, `~/.claude/plugins/installed_plugins.json` | 6 | 0 | Claude config introspection |
| `claudechic/commands.py` | `~/.claude/commands/`, `<project>/.claude/commands/`, `~/.claude/skills/`, `<project>/.claude/skills/` | 2 | 71 | **abast added significant resolution logic here** |
| `claudechic/agent.py` | Allows writes to `~/.claude/plans/` (Claude Code-owned) | 0 | 9 | abast touched plans-dir permission code |
| `claudechic/audit/audit.py` | `~/.claude/projects/` | 1184 | 0 | sprustonlab-only large addition |
| `claudechic/features/worktree/git.py` | Symlinks `<main_wt>/.claude` into worktrees (legitimate Claude-namespace passthrough). | 0 | 0 | unchanged |

These modules are **not** rewritten by #23 (they read Claude's namespace, which remains Claude's). However, they sit on the boundary and any policy change about how `.claude/` is treated must be communicated to them (e.g., to ensure they aren't rewritten by zealous boundary enforcement).

### 4.3. Tests in the settings perimeter

| Test file | sprustonlab churn | abast churn | Tag | Implication |
|---|---:|---:|---|---|
| `tests/test_config.py` | (small) | (small) | **both** *(corrected from CSV-only earlier read; FDR §7b confirms `both`)* | abast's contribution is auto-perm-mode test infrastructure (`5700ef5`), **not** config-relocation-related. Path 2 still needs to translate, but the translation surface is smaller than the CSV-only-read suggested. |
| `tests/test_config_integration.py` | 120 | 0 | sprustonlab-only | sprustonlab integration tests for current config behavior; #23 must update these regardless. |
| `tests/test_yolo_flag.py` | 0 | 40 (+22/-18) | abast-only | abast tests for a flag mechanism — FDR confirms this is part of A-T2 auto-perm cluster; orthogonal to #23. |

### 4.4. Mirror-tree axis (R5) — the `workflows/` ↔ `defaults/workflows/` parallelism

This is the **fourth architectural axis** named in §1; treated here as a cross-cutting module-set concern.

**The pattern (refined by FDR §3, §8, and Anomalies 1 & 3).** The CSV shows ~85 pairs of files where:

- abast has `claudechic/defaults/workflows/<workflow>/<role>/...` (`abast-only` tag)
- sprustonlab has `claudechic/workflows/<workflow>/<role>/...` (`sprustonlab-only` tag)

The two trees describe *the same workflows* under different directory shapes. They are not "abast added new workflows" or "sprustonlab added new workflows"; they are **the same content set** with different parent paths. **FDR Anomaly 1** confirms: "roughly 85 abast-only `claudechic/defaults/...` files are byte-near-identical mirrors of 85 sprustonlab-only `claudechic/{workflows,global}/...` files. Removing path-mirrors, abast's *truly independent* file footprint shrinks to ~13–15 files." This is the textbook signature of mirror-tree divergence: independent solutions to a shared need, selected differently because no boundary existed at the point of divergence.

**FDR §3 confirms the mirror is theme-driven, not file-by-file.** Both forks responded to the same need ("how do we ship workflows + hints + rules inside the installable package?") via dominant themes — sprustonlab's S-T1 ("package consolidation") and abast's A-T1 ("bundled defaults under `claudechic/defaults/`"). FDR §3 names this as "the most consequential theme-level finding in the report; it drives §5, §7, and §8 below."

**FDR Anomaly 3 — the path is not just shape, it is also content type.** On sprustonlab post-S-T1, `claudechic/workflows/` is **YAML data only** — engine code moved to `claudechic/workflow_engine/*.py`. On abast, `claudechic/workflows/` *still contains the engine Python* (no `workflow_engine/` directory). **The same path means different *kinds of content* on each fork.** This elevates the mirror-tree axis from "two shapes for the same content" to "two shapes for *partially different* content" — a strictly more architectural divergence. A naïve cherry-pick of an abast commit touching `claudechic/workflows/loader.py` lands in the wrong directory on sprustonlab (the file no longer exists at that path).

**Why this is an architectural axis, not just a structural anomaly.** The choice of `defaults/workflows/` vs flat `workflows/` is a **defaults-vs-user-overrides decision**. If abast's `defaults/workflows/` is read as "shipped defaults that project-local content overrides," then abast has introduced an *override semantics* — implicitly. If sprustonlab's flat `workflows/` is the model, then there is no override layer and the user edits the shipped tree directly. These are *different mental models for who owns what*. This is a settings-architecture concern, just one expressed in directory shape rather than in dotfile namespace.

**Why neither path collapses the mirror automatically.**

- **Under Path 1**: the pull mechanism (selective cherry-pick, D3) creates the duplication if naively applied: now both `claudechic/workflows/...` and `claudechic/defaults/workflows/...` exist in one repo, describing the same content. Resolution happens *during* the pull conversation: cherry-pick selectively to skip the structural change; or accept duplication and collapse during #23; or declare abast's overlay a "deliberate non-pull" (BF5). **The mirror-tree axis is forcibly visible** under Path 1, but it is resolved *without* a defaults-vs-overrides contract because that contract is part of #23, which has not yet happened.

- **Under Path 2**: #23 establishes the settings-domain contract first. As part of that work, #23 may (a) explicitly include a defaults-vs-overrides contract for shipped workflow content (within scope: the same axis), or (b) explicitly defer it. When abast's cherry-picks land, the `defaults/workflows/` overlay either maps onto the contract (kept, possibly with translation), is rewritten to fit, or is deliberately non-pulled (BF5). Resolution happens **with the contract in hand**.

**Implications for §6 conclusion.**

- The mirror-tree axis is a *sub-axis* of the broader settings-domain axis (axis 1 in the frame). Both ask "what does claudechic ship as authority vs what does the user own?" — axis 1 in path namespace, axis 4 in tree shape.
- Path 2's "boundary becomes a filter" advantage applies here too: the same contract that gates abast's settings-territory cherry-picks gates abast's `defaults/workflows/` overlay.
- **Path 1 has one genuine advantage on this axis**: the parallelism is *forcibly visible* in the diff and cannot be silently overlooked. Path 2 risks #23 being designed without ever seeing the overlay if the team doesn't read GitArch's report. This is mitigated by the existence of GitArch's per-file map (CSV) and the narrative report (when broadcast).

**Modules affected (CSV-grounded subset, FDR-confirmed).** Every pair of `claudechic/defaults/workflows/<X>` ↔ `claudechic/workflows/<X>` rows in the CSV is part of the mirror-tree axis surface. Largest pairs by churn: `project_team/composability/identity.md` (523 each), `project_team/lab_notebook/identity.md` (351 each), `audit/judge/suggest.md` (275 each), `project_team/researcher/identity.md` (239 each), `project_team/project_integrator/identity.md` (192 each), and ~25 more pairs with churn ≥ 50 each. Plus parallel `defaults/global/hints.yaml` (89, abast, **with byte-drift** — FDR §8 H2: sprustonlab has 10 extra trailing lines for `context_docs_outdated`) ↔ `global/hints.yaml` (99, sprustonlab) and `defaults/global/rules.yaml` (38, abast) ↔ `global/rules.yaml` (31, sprustonlab) — meaning the mirror-tree extends *beyond* `workflows/` to the always-active manifests too. **`project_team.yaml` has further drift** (per FDR §8 H2): sprustonlab's version uses `python -c "import glob; ..."` while abast's uses `ls`, plus sprustonlab adds extra `detect.field` rules. Spot-checks (FDR appendix) confirm `composability/identity.md`, `lab_notebook/identity.md`, and `tutorial/tutorial.yaml` are byte-identical across the mirror; drift exists but is content-localized.

### 4.5. Worktree symlink coupling (BF7)

`features/worktree/git.py` symlinks `<main_wt>/.claude` into each new worktree so that hooks, skills, and local Claude settings travel with the worktree (lines 293–301). The CSV shows abast did not touch this file (`sprustonlab-only`, +4/-2). Three implications:

- **The coupling is path-independent.** #23 must add a parallel symlink for the new claudechic state location (or relocate claudechic state to a path that *does* travel with the worktree by some other mechanism — e.g., living in the repo itself rather than a sibling dotdir). This obligation exists under both Path 1 and Path 2.
- **Path 1 does not pull conflicting abast logic into this file** (abast churn = 0). The symlink-mirror addition lands on top of a file abast did not modify; no merge surface.
- **The coupling makes the settings-domain axis less local.** What looked in §1 like a refactor confined to `config.py`, `hints/state.py`, `app.py`, and `onboarding.py` now also touches `features/worktree/git.py` and any test that exercises worktree creation. Concretely: the new `.claudechic/` location must be a path that the worktree feature can reasonably symlink (i.e., a directory, not just a file at root). **D17 ratifies this form**: `.claudechic/config.yaml` inside `<project>/.claudechic/`. The directory form is now the user-locked boundary, not just an architectural inference; the worktree symlink target is a real directory at a known path.

### 4.6. abast's in-package settings file

`claudechic/fast_mode_settings.json` (abast-only, +1 line). This is a settings file *inside the package*. It exists outside the entire `~/.claude/` vs `.claudechic/` discussion. Its placement is a separate architectural question (is package-internal config a third namespace?) that #23 may need to address. Under Path 1 the file lands and #23 must adjudicate; under Path 2 #23 establishes the boundary and the file is placed by it.

---

## 5. Architectural cost comparison (symmetric, no time estimates)

Format: per-axis, what work is concentrated where, and what is the resulting coupling exposure.

| Axis | Path 1: pull-then-#23 | Path 2: #23-then-pull |
|---|---|---|
| **Settings-domain (D4, D5)** | Refactor scope grows to include abast deltas to `config.py` (4 lines, auto-perm), `tests/test_config.py` (auto-perm fixture). One coherent boundary draw with full information. Risk: abast's `defaults/workflows/` overlay implicitly co-decides part of the boundary before #23 owns it. | Refactor scope is sprustonlab-only. Boundary draw uses smaller working set. **FDR §7d: most boundary-rewrite candidates (`agent.py`, `errors.py`, `theme.py`, `hints/state.py`, `hints/triggers.py`, `usage.py`, `features/worktree/git.py`) are NOT in either fork's divergence map** — meaning the relocation work mostly does *not* collide textually with abast's divergent commits at all. Settings-territory cherry-picks needing translation: `config.py` (+2/-2 abast for auto-perm), `tests/test_config.py` (auto-perm fixture). Per-cherry-pick translation cost is **smaller than the CSV-only read suggested**. |
| **Footprint/locality (userprompt boundary, D5)** | Currently launched-repo root contains `.claudechic.yaml` (file, not directory), `.claude/hits.jsonl`, `.claude/hints_state.json`, `.claude/phase_context.md`, `.claude/rules/*`. Pull phase may add abast's variant footprint (unknown without narrative report). #23 relocates them all in one event. | #23 relocates them first, against sprustonlab footprint. New contract gates which abast cherry-picks can land unchanged vs which must be translated. Onboarding's `.claude/rules/` install path is decided once. |
| **Fork-divergence (D3 selective pull, D6 lost-work)** | Pulls happen against present (boundary-violating) layout. Textual conflicts low for most abast files. **FDR Anomaly 1 reveals the divergence map is misleading at face value:** removing path-mirrors, abast's *truly independent* footprint shrinks to ~13–15 files (auto-perm UX, `/fast`, model-ID validation, conftest, pyproject pin). The "fork-divergence" cost is much smaller than the raw 98-file abast-only count suggests — for *both* paths. | Same Anomaly 1 reduction applies. Cherry-picks of the ~13–15 truly independent abast features are mostly orthogonal to #23 (auto-perm is permission UX, not settings-storage; `/fast` is a parallel toggle that needs adjudication; model-ID validation lives in `commands.py`/`config.py` near but not on the BF1 surfaces). The one substantive Path 2 translation cost in this row is `app.py` (per H1 below). |
| **Test surface coupling** | `tests/test_config.py` (corrected to `both`, abast contribution is auto-perm fixture) lands first against old config.py. Then breaks under #23. The break informs #23 design but is also a sunk-cost. `tests/test_config_integration.py` (sprustonlab) is rewritten as part of #23. | `tests/test_config_integration.py` rewritten as part of #23. `tests/test_config.py` abast-side auto-perm fixture translated as a cherry-pick under the new contract; small surface. |
| **`app.py` startup-region collision (caveat resolved by FDR §5)** | abast's 167-line `app.py` churn is **NOT** on `.claude/`-write sites (`hits.jsonl` line 1492, `phase_context.md` lines 1623+/1848+/1925) — it is on auto-perm UX, `/fast`, full-model-ID, and defaults-bundle hookup (FDR §5 commit attribution, §8 H1). All of abast's `app.py` work is **textually near** the same startup/init region #23 will rewrite, but **semantically tangential** to the BF1 surface. Path 1 absorbs this textual nearness as part of the one-shot refactor — fine in principle, but enlarges the surface. | Path 2's translation cost on `app.py` is bounded to **textual re-application of feature commits onto a rewrite that did not change their semantics**. This is BF3 territory (textual-not-semantic) — concretely: place auto-perm hooks, `/fast` registration, model-ID-loosening, and defaults-bundle hookup back onto the post-#23 startup region. Per-commit cost is "find the new home for the same logic," not "rewrite the logic to fit the new boundary." **My prior caveat — "if abast's `app.py` churn concentrates on `.claude/`-write sites, Path 1 strengthens" — resolves NEGATIVE in favor of Path 2.** |
| **Mirror-tree axis (R5) — `workflows/` ↔ `defaults/workflows/` parallelism (FDR §3 + §8 H2 + Anomaly 3)** | Forcibly visible: pull creates duplication in one repo. Resolution happens *during* pull, *without* a defaults-vs-overrides contract (#23 hasn't drawn one). Three resolution strategies (skip the structural change, accept-then-collapse, declare BF5) all decided ad hoc. **Path 1 advantage:** the parallelism cannot be overlooked; the diff itself surfaces the question. | Hidden during #23 unless the team consults FDR (now broadcast — mitigation is procedural and satisfied). Resolution happens *after* #23, with the defaults-vs-overrides contract in hand. **FDR §8 names this as the dominant Path 2 hazard (H2), but also names D8 (abast cooperation available) as the de-risking move:** "re-pathing abast's `claudechic/defaults/` adds before applying them is the de-risking move." So the Path 2 cost is bounded by a known intervention. **Compounded by FDR Anomaly 3:** sprustonlab's `claudechic/workflows/` is YAML-data-only (engine moved to `claudechic/workflow_engine/`); abast's `claudechic/workflows/` still contains the Python engine. **The same path means different content types on each fork.** This means: under either path, *direct* cherry-pick of abast commits touching `claudechic/workflows/*.py` would land in the wrong place on sprustonlab; D8-mediated re-pathing is required regardless of path order. Path 2 advantage: the boundary contract gives a principled basis for the re-pathing decision. |
| **In-package settings (`fast_mode_settings.json`)** | Pulled before boundary exists; placement ad hoc. May need to move again under #23. | Pulled after boundary exists; placement governed by the boundary. |
| **Worktree symlink mirror (BF7)** | Path-independent obligation. abast churn on `features/worktree/git.py` = 0; no conflicting pull. Path 1 lands the mirror addition into the same #23 refactor moment. | Path-independent obligation. The mirror is added as part of #23 against sprustonlab-only state. Subsequent abast pulls do not touch this file. **Slight Path 2 advantage:** the new claudechic state location is decided *with the symlink target requirement in scope* (i.e., #23 designs the new location to be symlink-friendly — a directory, not just a top-level file). Under Path 1, the location is decided with the same constraint, but in a larger surface, increasing the chance the symlink obligation is recognized late. |
| **Coupling exposure during transition** | One large concentrated refactor moment (#23) operating on dual-fork code. Higher peak surface area, single resolution event. | Two refactor moments (#23, then per-cherry-pick translation). Lower peak surface area, distributed resolution. Boundary serves as filter. |
| **Information available when each decision is made** | #23 design decisions made with full fork information. Pull decisions made without #23 information. | #23 design decisions made with sprustonlab-only information. Pull decisions made with #23 contract in hand. |

### Symmetry note

Neither path strictly dominates the other on coupling. They make **different bets**:

- Path 1 bets that one-shot resolution with full information beats per-cherry-pick translation cost. Bet pays off when abast's settings-territory churn is *substantial enough* that re-projecting it later is expensive but *not so structural* that it co-decides the boundary.
- Path 2 bets that establishing the boundary first and using it as a filter beats one-shot resolution. Bet pays off when the boundary is *load-bearing for subsequent decisions* (i.e., when many later choices key off it) and when settings-territory abast deltas are *small enough* that per-cherry-pick translation is bounded.

---

## 6. Lens-recommended path with rationale

**Through the composability lens only — Path 2 is preferred, with a caveat.**

### Rationale

The composability lens evaluates which sequencing leaves a smaller and better-isolated coupling surface in flight at any moment, and which sequencing makes design decisions with maximum relevant information at each step.

1. **The settings boundary is load-bearing.** It is the contract referenced by every read/write into config space — a small set of modules but invoked across many call sites. Once drawn, it serves as a filter for all subsequent integration decisions. Establishing this boundary FIRST (Path 2) means later decisions (selective-pull set, deliberate non-pulls under BF5, where to place abast's `fast_mode_settings.json`, how to treat abast's `defaults/workflows/` overlay) are made with the contract in hand. Establishing it LAST (Path 1) means those decisions are made under reduced information.

2. **abast's settings-territory churn is small enough to translate — and FDR strengthens this point further.** The per-cherry-pick translation cost Path 2 incurs is bounded: `config.py` is +4 abast lines (auto-perm only, FDR §5), `hints/state.py` is +0, `tests/test_config.py` (corrected to `both`) is auto-perm fixture only. The major abast-only divergence (workflows content tree, model-ID validation, `/fast`, in-package settings file) is largely orthogonal to the settings *boundary*. **FDR Anomaly 1 strengthens this further:** removing path-mirrors, abast's *truly independent* file footprint shrinks to ~13–15 files, of which only `app.py` and `commands.py` brush #23's surface. **FDR §7d strengthens it again:** most boundary-rewrite candidates (`agent.py`, `errors.py`, `theme.py`, `hints/state.py`, `hints/triggers.py`, `usage.py`, `features/worktree/git.py`) were touched in *neither* fork's divergent commits — Path 2's relocation work mostly does not collide textually with abast at all. Path 1's "do once" advantage is therefore even smaller than I assessed pre-FDR.

3. **abast's `defaults/workflows/` overlay is the decisive coupling concern — and FDR confirms it is even more architectural than R5 suggested.** This overlay is itself a settings-architecture decision (defaults vs. user overrides) that brushes the same conceptual axis as #23. Pulling it before #23 (Path 1) lets it implicitly co-decide part of #23's design surface; the overlay's premise becomes a constraint on #23 rather than a candidate evaluated against #23. Path 2 reverses this: #23 establishes the user-vs-defaults contract, then the overlay is adjudicated against the contract. **FDR §3 names this as "the most consequential theme-level finding in the report; it drives §5, §7, and §8."** **FDR Anomaly 3** elevates the concern: the parallel paths do not just hold the same content — they hold *different content types* (sprustonlab's `claudechic/workflows/` is YAML data only post-S-T1; abast's still contains Python engine code). The "mirror" is partly content-mirror and partly a structural type-mismatch, which means a defaults-vs-overrides contract from #23 must adjudicate not only "where does shipped content live" but also "what types of content live there" — exactly the question #23 should own.

4. **Path 2 turns the boundary into a filter.** Under Path 2, the settings boundary becomes a principled basis for "deliberate non-pulls" (BF5) — abast cherry-picks that contradict the contract are rejected on principle, not on intuition. Under Path 1, the same decisions are made before the contract exists.

5. **The mirror-tree axis (R5) is genuinely two-sided.** Path 1's *one structural advantage* over Path 2 is here: pulling abast's overlay forces the parallelism into a single working copy, where it cannot be silently overlooked. Path 2 risks #23 being designed without ever confronting the overlay if the team does not consult GitArch's per-file map. This risk is procedural rather than architectural — the data is on disk; consulting it is mandatory under the Specification phase — but it is real. The composability lens still favors Path 2 (the boundary becomes the filter that adjudicates the overlay), but acknowledges that on this axis Path 1 has a genuine forced-visibility advantage that Path 2 must compensate for via process.

6. **BF7 reinforces the boundary-is-load-bearing argument — and D17 has now ratified it concretely.** The worktree feature's symlink dependency means the chosen new location must be *symlinkable* (directory-shaped, not a single file at root). This is itself a constraint #23 must absorb. **D17 (user-locked, directly ratifying the BF7-driven architectural argument)** makes the form concrete: `.claudechic/config.yaml` inside a `.claudechic/` directory. The constraint is path-independent in cost, but it is *better recognized* under Path 2: when the boundary is the first decision and the worktree feature is one of the modules that consumes it, the symlinkability requirement is in scope from the start. Under Path 1, the boundary is decided amid abast's deltas, and the symlink consumer (which abast did not touch) is correctly visible but easier to overlook. With D17 ratifying the directory form, the recognition is no longer a Composability inference — it is the locked target.

### Updated lens conclusion after R5 integration

R5 does not flip the conclusion. Path 2 remains preferred on three of the four named axes (settings-domain, footprint/locality, fork-divergence). On the mirror-tree axis (axis 4), Path 1 has a genuine but procedural advantage (forced visibility of the parallel structure during pull), which Path 2 compensates for by mandating consultation of GitArch's per-file map during #23 design. Net: Path 2 preferred, with the procedural compensation explicitly required.

### Updated lens conclusion after FDR delta-pass

The narrative FDR **reaffirms and slightly strengthens** the Path 2 conclusion. No backtrack:

- **My `app.py` caveat resolved against Path 1.** Per FDR §5 commit attribution, abast's `app.py` churn is auto-perm UX, `/fast`, full-model-ID, and defaults-bundle hookup — *not* on `.claude/`-write sites. Path 2's translation cost on `app.py` is BF3-textual, not semantic. Path 1's "concentrated resolution with full information" advantage on the `app.py` axis is therefore *not* invoked.
- **FDR Anomaly 1 (path-mirror double-counting) shrinks the fork-divergence cost.** abast's truly independent footprint is ~13–15 files. Per-cherry-pick translation cost under Path 2 is correspondingly smaller than my pre-FDR assessment.
- **FDR §7d (quiet-relocation insight) strengthens Path 2's settings-domain advantage.** The bulk of #23's boundary-rewrite candidates were not touched in either fork's divergent commits, meaning the relocation work occurs largely outside the divergence map.
- **FDR Anomaly 3 deepens the architectural argument for Path 2.** The mirror-tree axis is no longer just "same content, different shape" — it is "different content types at the same path between forks." This makes a #23-owned defaults-vs-overrides contract more load-bearing, not less, and reinforces the case for stabilizing it first.
- **FDR §8 H2 names the mirror-tree as the dominant Path 2 hazard, but also names D8 (abast cooperation) as the de-risking move.** The Path 2 cost is bounded by a known, available intervention.
- **The one Path 1 advantage on axis 4 (forced visibility) is procedurally compensated by FDR being broadcast and read.** The mitigation requirement is now satisfied — the data is on disk, it has been consulted, and the mirror-tree is in scope of every Leadership lens.

Net: Path 2 preferred through the composability lens; the FDR refines the cost table downward for Path 2 and upward for Path 1 (Path 1's surface enlarges by abast's mirror-tree decision and pull-resolution-without-contract risk).

### Caveat (the lens does not erase)

Path 2 distributes per-cherry-pick translation cost. This cost is real and unavoidable under Path 2. If subsequent integration is high-volume or the team is wary of distributed cost, Path 1's concentrated-cost profile may be preferred for non-composability reasons (e.g., schedule, reviewer load). Those reasons are outside this lens.

Additionally, **Path 2 is sensitive to the narrative report**. If GitArch's `fork_diff_report.md` reveals that abast's settings-territory churn is **larger or more entangled with the overlay than the file-level CSV suggests** — for example, if `app.py`'s 167 abast lines turn out to be heavily concentrated on the very `.claude/`-write sites #23 must move — then Path 1's "concentrated resolution with full information" advantage grows and the lens becomes more balanced. This evaluation should be revisited when the narrative report lands.

### Boundaries of this conclusion

- This conclusion is from the composability lens only. Skeptic owns risk weighting (BF2/BF3/BF4/BF5 may shift the answer). UserAlignment owns alignment with user intent. TerminologyGuardian owns the naming-and-namespace consequence of the boundary draw. Synthesis happens at coordinator level.
- D7 (value asymmetry equal) is honored: this evaluation does not advocate one fork's work over the other.
- D9/D10 (no time pressure, no time estimates) is honored: cost descriptions are concrete process statements, not durations.
- The conclusion is conditional on D3 (selective pull, never all-or-nothing). If that decision changed (which it has not), Path 1's calculus would shift toward worse, not better.

---

*End of Composability evaluation.*
