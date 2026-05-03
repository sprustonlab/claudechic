# Risk Evaluation — Issue #23 Path Selection

**Author:** Skeptic (Leadership lens — risk, failure modes, hidden assumptions)
**Project:** `issue_23_path_eval`
**Status:** Specification phase — **finalized.** All 8 prior `[GA-PENDING]` markers cleared with data from GitArchaeologist's Fork Diff Report (`fork_diff_report.md`, §§5/7/8 in particular). One new risk row (R8) added from FDR §8 H2 hazard. Section 6 carries the final lens-recommended path with explicit cross-lens disagreement acknowledgment (Composability concludes the opposite via "boundary-as-filter"; both lenses' arguments are surfaced for the recommendation document to adjudicate).

---

## 1. Frame

**The decision is not "do we merge?" Both paths contain a merge event.** What differs is *when* the heavy collision happens and *what state the codebase is in at the moment of resolution*. The risk lens asks: which sequencing minimizes cognitive load, ambiguity, and irreversibility for whoever resolves the conflicts, and which preserves the most undo paths if a mistake is made.

"Lost work" — the user's North Star failure mode (D6) — almost never originates inside `git merge` itself. It originates in:

- **Resolution-time decisions** (a tired human accepting "ours" / "theirs" wholesale to make a tedious merge end).
- **Abandonment** (a half-merged branch left to rot because the merger lost confidence).
- **Silent semantic conflicts** (textually clean merges that produce systems nobody designed — BF3).
- **Selective-pull dependency drops** (BF4: cherry-picking commit B without prerequisite A → code that compiles and runs broken).
- **Deliberate non-pulls becoming forgotten divergence** (BF5: what we choose *not* to take from abast quietly accumulates as drift the recommendation never accounted for).

### Severity calibration against D6 (all four lost-work modes)

The matrix scores **impact** against these four modes explicitly:

| Mode | Definition | Detectability | Recoverability | Severity weight |
|---|---|---|---|---|
| **D6.a** | Commits never make it to main | High (git log diff) | High (re-cherry-pick) | **Low** — visible, recoverable |
| **D6.b** | Features non-functional post-merge | Medium (needs test coverage) | Medium (debug + repair) | **Medium** — visible if testing exists, expensive but bounded |
| **D6.c** | Features reverted in conflict resolution | Low (looks intentional in the diff) | Low (must be noticed by someone with prior knowledge) | **High** — easy to miss, hard to undo without authorial memory |
| **D6.d** | Intent lost even if code survives | **Very low** (code looks fine; behavior subtly diverges from author's design) | **Very low** (requires re-deriving the design from first principles) | **Critical** — the failure mode that motivates this entire evaluation |

**Operating principle for the matrix:** an option that looks "easier" but raises D6.c/D6.d risk is *more* dangerous than an option that looks "harder" but keeps risks in the D6.a/D6.b regime where they are visible and recoverable. Visibility and recoverability are first-class severity discounts.

---

## 2. Risk Matrix per Path

**Likelihood scale:** L (low) / M (medium) / H (high) / VH (very high). **Impact scale:** maps to D6 mode severity above (Low / Med / High / Critical).

### Data substrate (from FDR `fork_diff_report.md` §§4–8 + `fork_file_map.csv` 272 rows)

- **Hot files (FDR §5) — 6 files modified by both forks since merge-base:** `app.py` (churn 353), `commands.py` (73), `config.py` (60), `pyproject.toml` (21), `mcp.py` (20), `tests/conftest.py` (8). Direct textual overlap is sparse but **all three of #23's most live code-touch sites (`app.py`, `commands.py`, `config.py`) are hot files** (FDR §7a — confirms BF2 concretely).
- **Quiet zone (FDR §7d) — boundary-relocation surface that neither fork has touched since merge-base:** `agent.py`, `errors.py`, `theme.py`, `hints/state.py`, `hints/triggers.py`, `usage.py`, `features/worktree/git.py`. The userprompt-derived BF1-fix work lands largely in conflict-free territory regardless of path. This is a meaningful counterweight to Path 2's risks in §6.
- **H2 mirror-tree pattern (FDR §3 + §8 + Anomaly #1) — the dominant Path 2 hazard:** ~85 path-mirror pairs where both forks bundled equivalent content under incompatible roots (`claudechic/{workflows,global}/...` vs `claudechic/defaults/{workflows,global}/...`). Spot-checks show many pairs are byte-identical. Naïve text-merge tooling sees these as 2 unrelated additions; semantically they are the same file. **This is a far larger silent-conflict surface than the 6 textual hot files.**
- **`workflows/` directory has divergent semantics on each side (FDR Anomaly #3):** post-consolidation, sprustonlab's `claudechic/workflows/` is YAML-data-only (engine code moved to `claudechic/workflow_engine/`); abast's `claudechic/workflows/` still contains the engine Python. **A naïve cherry-pick of an abast commit touching `claudechic/workflows/loader.py` lands in the wrong directory on sprustonlab** — concrete BF4 dependency-drop manifestation.
- **Concrete BF4 dependency-drop instance (FDR Anomaly #6 + §8 H3):** abast's `pyproject.toml` change pinning `anthropic==0.79.0` (commit `0ad343b`) is required by `/fast` mode (commit `26ce198`). Pulling `26ce198` without `0ad343b` lands `/fast` against an incompatible SDK. This is the worked example for the dependency-drop risk row.
- **abast's truly independent footprint is small (FDR Anomaly #1):** after removing the ~85 mirrors, abast's "real" file footprint is ~13–15 files (auto-perm UX, `/fast`, model-ID validation, conftest, pyproject pin). Most of the `abast-only` count overstates contention.
- **Each fork is essentially "one big consolidation commit + small follow-ups" (FDR §2):** sprustonlab's `317f424` covers 166/174 files; abast's `d55d8c0` covers 88/104 files. The themes are concentrated, not scattered — making the H2 collision the single biggest concentration of risk.

### Matrix

| # | Risk (origin) | Path 1 Likelihood | Path 1 Impact | Path 2 Likelihood | Path 2 Impact | Notes |
|---|---|---|---|---|---|---|
| **R1** | **Hot-file collision on `app.py` / `commands.py` / `config.py`** (BF2 — FDR §5 + §7a confirms all three are hot) | M | Med (D6.b) — abast's hot-file edits land on sprustonlab's existing layout; conflicts surface during pull while #23 design hasn't yet committed; collisions remain in the textual / D6.b regime | H | High (D6.c) — #23 will rewrite all three files (settings screen wiring + boundary fix + key schema); subsequent abast cherry-picks must be *re-applied on top of* a redesigned target, raising the chance of "accept theirs" silently reverting #23 (D6.c) | FDR §5 attribution: abast touches app.py via 6 different commits (auto-perm UX, /fast, full-model-id, defaults bundle); commands.py via 3 commits (/fast, auto-perm, full-model-id); config.py via 1 commit (auto-perm). Path 2's higher likelihood derives from the *fan-in* pattern: more abast commits each requiring separate re-application against #23's rewritten file. |
| **R2** | **Silent semantic conflict** (BF3 — FDR §8 H2 substantially raises the surface) | M | High (D6.c/d) — abast's intent-decisions land in our tree before #23 design; reviewers must reverse-engineer them but at least the conflicts are *seen* | **VH** | **Critical (D6.d)** — H2 surface (~85 mirror pairs) means cherry-picks can land at incompatible paths and apply *cleanly* without any text conflict, producing a parallel duplicate tree that is silently broken (Anomaly #1 + §8). #23 ships with sprustonlab's design assumptions; later abast pulls textually merge into a system whose constraints abast never knew about. | The dominant Path 2 risk per FDR §8. The "boundary becomes a filter" argument from Composability's lens addresses *settings-territory* cherry-picks but does NOT address H2 — the layout-collision surface carries no settings semantics for the boundary contract to filter against. **D8 (abast cooperation) directly mitigates Path 1 here** — see §5. |
| **R3** | **Selective-pull dependency drop** (BF4 — Skeptic-tagged, FDR provides concrete instances) | M | Med (D6.b) — pull set is small and bounded; dependent commits identifiable; the `0ad343b` → `26ce198` chain is named by FDR §8 H3 and easily honored | M-H | Med (D6.b) — same mechanism plus a NEW concrete manifestation: a naïve cherry-pick of an abast commit touching `claudechic/workflows/loader.py` lands in the wrong directory on sprustonlab (FDR Anomaly #3). Path 2 amplifies likelihood because the exclusion set (commits skipped because they fight #23) is larger and dependency chains across an exclusion are easy to miss. | **Worked example (FDR Anomaly #6, BF4-canonical):** abast commit `0ad343b` pins `anthropic==0.79.0`; abast commit `26ce198` adds `/fast` and depends on the pin. Pulling `26ce198` without `0ad343b` lands `/fast` against an incompatible SDK — code merges textually, breaks at runtime. **Second worked example:** abast commit touching `claudechic/workflows/loader.py` cherry-picked onto post-consolidation sprustonlab — file lands at a path where the loader code no longer exists (engine moved to `workflow_engine/`); textual apply succeeds, runtime broken. |
| **R4** | **Deliberate non-pulls becoming silent divergence** (BF5 — Skeptic-tagged) | M | Med (D6.d) — non-pulls are decided once, while sprustonlab is in active design mode; easier to record rationale; the FDR §8 H4 candidate list is enumerable | H | High (D6.d) — non-pulls are decided after #23 is locked in; the rationale "this conflicts with #23" is recorded once and forgotten as #23's invariants drift over time; abast's continued evolution of those areas drifts further uncaptured | FDR §8 H4 enumerates 7 deliberate-non-pull candidates: `fast_mode_settings.json`, `/fast` command, auto-perm-default, auto-perm-Shift+Tab, full-model-id-validation, the anthropic pin (conditional on /fast), and the entire `claudechic/defaults/` tree. The ledger is now a known-finite list to seed `NON_PULLED.md` from on day one. |
| **R5** | **Parallel mirror-tree resolution — `claudechic/workflows/` vs `claudechic/defaults/workflows/`** (NEW from CSV evidence; FDR §3 + §8 H2 + Anomaly #1 substantially confirm and quantify) | H | High (D6.d) — Path 1 must decide which root wins before #23 design; this forces an early architectural commitment without #23's clarity. Mitigated by the fact that this decision is *itself* a useful rehearsal for #23's analogous "where does claudechic config live" question | **VH** | **Critical (D6.d)** — Path 2 lets #23 establish a config-layout precedent first, but the workflow-tree decision must still be made *somewhere*, and the FDR data shows the two layouts are genuinely incompatible (S-T1 chose `workflows/` + new `workflow_engine/`; A-T1 chose `defaults/workflows/` with fallback discovery and engine in old location). Without explicit pre-decision, post-#23 cherry-picks of abast's `defaults/...` adds will create a parallel duplicate tree (BF3) | This is the single largest risk amplification from the FDR. The pre-FDR weight had Path 2 as "M / High"; the FDR data raises it to "VH / Critical" because of the breadth of the H2 surface (~85 file pairs) and the fact that the loader code itself was renamed (sprustonlab's `R080`/`R099`/`R100` rename markers in `317f424`). Composability's "boundary-as-filter" argument explicitly does NOT cover this axis. |
| **R6** | **`app.py` / `commands.py` high-churn collision** (FDR §5 confirms; §5 commentary clarifies the texture) | H | Med (D6.b) — early integration; conflicts surface before #23 design and force a clean baseline. FDR §5 commentary: abast's app.py changes touch *different functions* than sprustonlab's (auto-perm UX vs Windows utf-8 / consolidation), so the conflicts are mostly insertion-collision, not edit-collision. Mechanical | H | Med-High (D6.b/c) — same conflicts surface, but later, after #23 has further changed app.py to wire the `/settings` screen. The post-#23 cherry-pick must preserve abast's edits AND #23's new wiring AND not silently revert the wiring. FDR §5 commentary holds, but Path 2 layers a third dimension on the merge | This risk is path-symmetric in *likelihood* (FDR confirms collisions inevitable in both); Path 2 widens the impact slightly because #23 is also touching these files. The asymmetry is smaller than initially estimated because abast's app.py changes are surgically isolated to startup/init regions per FDR §5. |
| **R7** | **BF1 (mixed `~/.claude/.claudechic.yaml`) re-introduced by an abast pull** (FDR confirms violation pattern in abast tree) | L | Med (D6.b) — caught by #23's boundary review which is still upcoming; sprustonlab can refuse pulls that violate the not-yet-built rule. The boundary-relocation surface (FDR §7d) is in quiet files abast hasn't touched, so the inflow risk concentrates on `fast_mode_settings.json` and the (small) abast `config.py` tweak | M | High (D6.c) — post-#23, an abast cherry-pick that touches Claude-namespace paths may textually merge but silently revert the boundary; reviewer must remember the rule when reading every pull | abast already shipped `claudechic/fast_mode_settings.json` (FDR §8 H4) — direct evidence the BF1-class violation pattern exists in their tree. Both paths must add a "boundary lint" step (see §5). |
| **R8** *(NEW from FDR §8 H2)* | **Semantic-layout collision via path-mirror pairs** (~85 pairs of identical content at incompatible paths) | M | High (D6.d) — Path 1 surfaces these as visible "same file at two paths" anomalies during the pull; the team must consciously content-merge them. Visibility is the saving grace | **VH** | **Critical (D6.d)** — Path 2's post-#23 cherry-picks of abast's `defaults/...` adds will apply *cleanly* (because the destination paths don't exist on sprustonlab post-consolidation) and create a parallel duplicate asset tree that is *silently disconnected* from sprustonlab's loader code. This is the single most dangerous scenario in the entire evaluation. | Strictly distinct from R5 in that R5 is the *meta-decision* (which root wins) while R8 is the *concrete file-level harm* if the meta-decision is deferred. Both Path 1 and Path 2 must address R5; only Path 2 carries R8 as a primary risk. **D8 mitigation: ask abast to pre-rebase their `defaults/...` adds to whichever path wins, before any cherry-pick.** |
| **D6.a** | Commits never on main | M | Low | M | Low | Symmetric. Path 2 slightly worse only because the post-#23 review burden may cause some abast commits to be triaged out and forgotten (overlaps R4). |
| **D6.b** | Features non-functional post-merge | M | Med | H | Med | Path 2 worse — more components are simultaneously in flux; FDR Anomaly #3 (workflows/ dual meaning) is a concrete D6.b case (`/fast` against wrong-version SDK, or loader.py at wrong path). |
| **D6.c** | Features reverted in conflict resolution | M | High | H | High | Path 2 substantially worse — see R1, R2, R7. |
| **D6.d** | Intent lost even if code survives | M | Critical | **VH** | **Critical** | Path 2 substantially worse — see R2, R5, R8. **This is the dominant differentiator.** |

### Aggregate read

Path 1 concentrates risk in *visible, decision-time* events (R1, R5, R6, R8 all surface early when designers are alert and have full context). Path 2 concentrates risk in *post-completion, low-attention* events (R1, R2, R4, R7, R8 surface after #23 ships, when the team feels done). The matrix is asymmetric on the dimensions that matter most (D6.c, D6.d), with Path 2 carrying greater hidden risk **principally driven by R8 (the H2 mirror-tree collision)**, which the FDR data made substantially more material than the pre-FDR draft estimated.

---

## 3. Pre-conditions for Safety

### Standing rule (top-level framing)

**A path with preconditions skipped is more dangerous than the other path with preconditions met.**

This is the operative rule the recommendation must enforce. Lens-recommended path selection is meaningless if the corresponding preconditions are not honored at execution time. A "safe path executed unsafely" is, by definition, the unsafe path. Therefore: pre-conditions are not optional caveats. They are the path. Skipping them retroactively reclassifies the choice.

A path is "safe" only if all its preconditions hold. If a precondition cannot be met, that path is *not safe to execute*, independent of its theoretical merit.

### Path 1 (selectively pull from abast → implement #23) is safe IF:

1. **PC1.1 — Cherry-pick scope is enumerated before any pull.** A written list of which abast commits / themes are in vs out, with rationale, exists *before* the first `git cherry-pick` runs. The FDR §8 H4 table is the seed for the in/out enumeration. (Mitigates R3, R4.)
2. **PC1.2 — abast cooperation is engaged for intent recovery (D8).** Specifically: abast maintainers commit to answering "what was the intent of commit X?" within a turnaround the project can tolerate. (Mitigates R2, R5.)
3. **PC1.3 — A semantic-review checkpoint is mandated after each thematic pull batch.**
   - **Artifact reviewed:** the cumulative `git diff` of the just-applied pull batch, plus the batch's commit messages, plus the corresponding entry in the pull-batch plan.
   - **Reviewer (role):** a sprustonlab maintainer who did not perform the cherry-picks, paired with the implementer of record for any sprustonlab-side files touched by the pull. (Pairing prevents single-reviewer blind spots.)
   - **Pass criterion:** a written "design diff narrative" exists, exceeding one paragraph, that names (i) what the system now *does differently* in observable behavior, (ii) which design invariants of either fork are now binding, and (iii) any "looks fine, behaves differently" risks identified.
   - **Fail criterion:** narrative is missing, is purely textual ("file X gained N lines"), or omits an invariant the reviewer can name. Failure ⇒ pull batch reverted, re-planned, re-applied. (Mitigates R2, R7.)
4. **PC1.4 — A `NON_PULLED.md` ledger is created and maintained.** Every conscious decision not to pull an abast commit is recorded with rationale and a re-evaluation trigger. Seed entries from FDR §8 H4. (Mitigates R4, BF5.)
5. **PC1.5 — The mirror-tree decision (`claudechic/workflows/` vs `claudechic/defaults/workflows/`) is resolved as an explicit early step**, with a written rationale, *before* #23 design begins. The decision must address: (i) which root wins for shipped content, (ii) what happens to the renamed engine code (`workflow_engine/`), (iii) the loader-discovery mechanism, (iv) explicit treatment of the ~85 content-mirror pairs as a single conflict surface, not 170 independent files. (Mitigates R5, R8.)
6. **PC1.6 — A boundary-lint step is added to CI** (or to the pre-merge checklist) that fails when claudechic writes inside `.claude/` or when claudechic settings files appear at repo root. (Mitigates R7, BF1.)

### Path 2 (implement #23 → selectively pull from abast) is safe IF:

1. **PC2.1 — All of PC1.1, PC1.4, PC1.6 hold.** (Symmetric prerequisites.)
2. **PC2.2 — #23 design phase explicitly enumerates abast's expected future-pull surface and designs around it.** Not just "we'll handle abast later" — a section in the #23 design doc lists "files we expect to receive abast changes to, and the contracts those changes must satisfy." This must explicitly include the H2 mirror-tree question — #23 must declare a position on which root (`workflows/` or `defaults/workflows/`) is canonical, even though #23 itself does not directly touch that tree. Without this declaration, R8 becomes uncontrolled. (Mitigates R1, R5, R8.)
3. **PC2.3 — abast cooperation is engaged at design time, not pull time** — abast reviews and signs off on #23's design as compatible with their roadmap *before* sprustonlab implements. Pull-time cooperation is not enough; by then it is too late. Includes explicit alignment on the H2 mirror-tree resolution: abast must agree to rebase their `claudechic/defaults/...` adds onto whichever root sprustonlab declares canonical, before sprustonlab cherry-picks them. (Mitigates R2, R8.)
4. **PC2.4 — A semantic-review checkpoint is mandated for every cherry-pick post-#23**, with a *higher* burden than PC1.3.
   - **Artifact reviewed:** the per-commit `git diff` of the candidate cherry-pick, the abast commit message, the #23 design document's invariants list, and the current state of `NON_PULLED.md`.
   - **Reviewer (role):** a sprustonlab maintainer (not the cherry-picker) AND a designated "#23 invariants owner" (the role that owns the #23 design document). Both must sign off; a single signoff is a fail.
   - **Pass criterion:** a written note exists that (i) confirms the cherry-pick does not violate any named #23 invariant by reference (cite the invariant), (ii) identifies any silent semantic shift (D6.d) — explicit check for the H2 wrong-path-landing pattern, (iii) confirms the change was not previously rejected for the same reason in `NON_PULLED.md`.
   - **Fail criterion:** any unanswered invariant question, any "I think it's fine" hand-wave, or absence of either signoff. Failure ⇒ cherry-pick rejected, entry added to `NON_PULLED.md` citing the violated invariant. (Mitigates R1, R2, R7, R8.)
5. **PC2.5 — A regression test suite covering #23's invariants is in place before the first post-#23 cherry-pick.** Must include a test that fails if `claudechic/defaults/workflows/` and `claudechic/workflows/` both contain workflow content (or whatever the canonical-root invariant is from PC2.2). (Mitigates R1, R7, R8 — converts D6.c/d failures into D6.b failures, which are recoverable.)
6. **PC2.6 — The non-pull ledger (PC1.4) is augmented with "rejected post-#23" entries** carrying the specific #23 invariant the rejected commit violated, so the rationale survives memory loss. (Mitigates R4, BF5.)

**Comparative observation:** Path 1's preconditions are mostly *process*. Path 2's preconditions add *cooperation timing* (PC2.3), *infrastructure* (PC2.5), *and design-time pre-declaration of a layout question that #23 does not naturally have to answer* (PC2.2 — #23's body scope is settings-screen + docs, not workflow-tree layout; forcing the declaration is asking the design to carry weight outside its native scope). Path 2 demands more of the surrounding ecosystem to be true.

---

## 4. Cheap Experiments / Probes

Probes that reduce uncertainty without committing to a path. All are reversible and produce written artifacts.

**Probe classification:**
- **Pre-flight probes (E2-revised, E4)** — to be run *before* the chosen path is executed, as conditional pre-flight steps gating execution. Listed in the recommendation document as such; results may flip the lens-recommended path.
- **Diagnostic probes (E1, E3, E5-CLEARED, E6)** — refine matrix weights and provide design substrate; not gating.
- **Probes superseded by FDR data:** E5 (issue #23 surface dry-trace) was supplied directly by FDR §6c+§7 — listed below as **CLEARED** for traceability.

### Probe E1 — Dry-run cherry-pick of abast's config-adjacent commits

**What:** On a throwaway branch, attempt `git cherry-pick --no-commit` of the abast commits that touch `claudechic/config.py` (commit `5700ef5`), `claudechic/fast_mode_settings.json` (part of the A-T2 cluster), and `tests/test_config.py`. Inspect the textual conflict count, examine `fast_mode_settings.json`'s relationship to the BF1 boundary rule, then `git cherry-pick --abort`.
**Reduces uncertainty in:** R1, R7. Reveals whether "config zone" pulls are textually trivial or already painful. FDR predicts trivial (small abast churn), but the dry-run is the cheap empirical confirmation.
**Output:** A short note recorded under `Decisions / Open Questions` in STATUS.md.

### Probe E2 (REVISED) — Mirror-tree canonical-root decision (D8 cooperation) — **PRE-FLIGHT, conditional gate**

**Status:** The original E2 question ("why did abast put workflows under `defaults/`?") is **partially answered for free** by FDR §3 + Anomaly #3: abast bundled defaults under `defaults/` to support fallback discovery; sprustonlab moved engine code to `workflow_engine/` and kept content in `workflows/`. The cause is now known. What remains uncertain is the *forward* decision: which layout should win going forward.

**What (revised):** Convene a short discussion with abast to establish forward consensus. Three questions: (i) "Are you willing to rebase your `claudechic/defaults/...` adds onto a single canonical root chosen by sprustonlab?" (ii) "Is your `defaults/` choice structural to your fallback-discovery mechanism, or is it a name we can change?" (iii) "If we choose `workflows/` as canonical, does your fallback-discovery mechanism still work?"
**Reduces uncertainty in:** R5, R8, PC1.5 / PC2.2 feasibility. Distinguishes "abast will converge if asked" from "abast's choice is structural and irreversible."
**Conditional flip rule:**
- If abast confirms convergence-willingness AND structural flexibility ⇒ R8 likelihood drops materially under both paths; the lean is unaffected (Path 1 still preferred but less urgently).
- If abast's `defaults/` is structurally entangled with fallback discovery and they will not converge ⇒ R8 stays as estimated (Critical impact under Path 2); Path 1's lean strengthens.
- If abast has no maintainer bandwidth to engage on this question ⇒ PC1.2 collapses for the purpose of mitigating R5/R8; the team is forced into a unilateral decision and Path 1 lean is unaffected.
**Output:** A verbatim record in STATUS.md `Decisions / Open Questions`, plus an explicit "R5/R8 weight reassessment" line in this risk evaluation's refinement section.

### Probe E3 — Boundary-violation inventory in abast's tree

**What:** On a read-only checkout of abast's main, `grep -r` for any path under `.claude/` that claudechic writes to, plus any new claudechic-owned files at repo root. Produces the inventory of BF1-class violations abast already carries. Partially seeded by FDR §8 H4 (which already names `fast_mode_settings.json`); E3 extends this to a full inventory.
**Reduces uncertainty in:** R7. Quantifies how much "boundary debt" Path 1 inherits in pulls vs how much Path 2 must reject post-#23.
**Output:** Inventory list appended to risk evaluation.

### Probe E4 — abast roadmap snapshot (D8 cooperation) — **PRE-FLIGHT, conditional gate**

**Classification:** Pre-flight to recommendation. To be run *before* committing to either path. Result may flip the lens-recommended path.
**What:** Ask abast: "In the next changes you plan to make, do any redesign config layout, the `.claude/` boundary, or the `/settings` screen?" Convert any "yes" answers into a list with sufficient detail to identify file scope.
**Reduces uncertainty in:** R1, R2, R5, PC2.3 feasibility. Tells us whether Path 2's "design with abast's future in mind" is even possible (you cannot design around an unknown roadmap).
**Conditional flip rules:**
- If abast confirms an imminent `/settings` redesign of their own → **the lens-recommended path may flip from Path 1 to Path 2**: pulling abast's not-yet-final design now (Path 1) risks landing a parallel design that conflicts with sprustonlab's #23 vision and abast's own near-future direction. Path 2's "design our way first, cherry-pick the compatible bits later (after abast finishes)" becomes safer.
- If abast confirms imminent `.claude/` boundary work → coordinate it with #23's BF1 fix; this likely strengthens Path 1 (joint design before either fork commits) — but only if PC1.2 cooperation is real.
- If abast has nothing imminent in this surface → Path 1 lean is unaffected.
**Output:** A roadmap-overlap addendum appended to this risk evaluation, plus an explicit lens-flip note (or no-flip confirmation) in Section 6.

### Probe E5 — Issue #23 surface dry-trace — **CLEARED by FDR §6c + §7**

**Status:** Superseded. FDR §6c (issue body and userprompt-derived #23 surface) and §7 (intersection with divergence map) supply this directly. Key result already absorbed into matrix: all 3 of #23's most-live code-touch sites are hot files (R1, R6 confirmed); the boundary-relocation surface (FDR §7d) is in quiet files (R7 likelihood reduction under Path 1).

### Probe E6 — "Lost work" tabletop (D6 stress test)

**What:** With one or two team members, walk through a hypothetical: "We executed Path X, then we discover feature Y is broken / missing / behaviorally wrong. How did we find out? What does recovery look like?" Do this once per path. Use FDR §8 H2 as the concrete failure scenario for Path 2 (parallel `defaults/` tree silently disconnected); use FDR §5 app.py attribution as the concrete failure scenario for Path 1 (abast's auto-perm changes accidentally lost during merge).
**Reduces uncertainty in:** D6.b/c/d severity weights. Tabletop exercises tend to surface the failure modes a matrix omits.
**Output:** A short "post-mortem of the future" appendix to the recommendation.

---

## 5. Mitigations per Path

For each major risk, the concrete countermeasure under each path. D8 (abast cooperation) is treated as a first-class mitigation asset throughout.

### R1 — Hot-file collision on `app.py` / `commands.py` / `config.py`

- **Path 1:** Cherry-pick abast's hot-file commits *first* in the order suggested by FDR §5 attribution: `5700ef5` (auto-perm startup, smallest single-file footprint), `7e30a53` (Shift+Tab cycle), `26ce198` (`/fast`, with its `0ad343b` prerequisite — see R3), `f9c9418` (full-model-id), `8e46bca` (path fix). Resolve textual conflicts under low semantic load. After the pull, design #23 against the merged baseline.
- **Path 2:** Defer all abast hot-file pulls until post-#23. Each pull then requires PC2.4's semantic-review checkpoint with #23-invariant citation. Rejected pulls go to `NON_PULLED.md` with the violated invariant recorded.
- **D8 leverage (both paths):** Ask abast directly which of their hot-file commits they consider load-bearing vs experimental. FDR §8 H4 already flags candidates for the non-pull conversation.

### R2 — Silent semantic conflict

- **Path 1:** Mandatory post-pull "design diff narrative" per PC1.3 — see PC1.3 above for the explicit artifact / reviewer-role / pass-fail spec. The narrative converts a textually-clean merge into an explicit design assertion that a reviewer is on the hook for.
- **Path 2:** Per PC2.4 (see Section 3 for full artifact / reviewer-role / pass-fail spec) — narrative-plus-invariant-check, dual signoff. Additionally use D8: ask abast to *review* sprustonlab's pull resolutions for their own commits, not just answer questions about original intent. Pass criterion for abast review: a written ack from an abast maintainer that the resolved diff preserves their commit's intent (or explicitly accepts the divergence).
- **D8 leverage:** Schedule a single "design alignment session" with abast — Path 1 before #23 design, Path 2 before any post-#23 cherry-picks.
   - **Artifact produced:** a shared "system invariants" document, written jointly, listing what both forks consider load-bearing about the system's behavior and structure.
   - **Reviewer (role) for the artifact:** one sprustonlab maintainer plus one abast maintainer; both must sign the document.
   - **Pass criterion:** the document names at least one invariant per major subsystem (config, screens, MCP, workflows, hints) AND lists at least one *known disagreement* between the forks (a "we differ on X" entry — its absence is suspicious; both forks have diverged for a reason). The H2 mirror-tree question must be a named disagreement.
   - **Fail criterion:** an empty disagreements section, or any subsystem with no named invariant. Failure ⇒ session reconvenes; cherry-picks blocked until pass.

### R3 — Selective-pull dependency drop

- **Path 1 and Path 2 (symmetric):** For each candidate pull, run `git log --follow` on every file touched to identify prerequisite commits. Use `git rev-list --topo-order` to find the minimum-superset of commits that preserves dependency closure. Document the closure in the pull-batch plan.
- **Worked-example treatment (FDR-supplied):** the `0ad343b` (anthropic pin) → `26ce198` (`/fast`) chain is now explicitly named. Pull-batch plan must contain a "prerequisites" column; for `26ce198` the prerequisite is `0ad343b`. Failure to include `0ad343b` is a fail criterion.
- **Workflows-loader manifestation (FDR Anomaly #3):** any abast commit that touches `claudechic/workflows/loader.py` or other engine code under `claudechic/workflows/*.py` MUST be re-pathed to `claudechic/workflow_engine/` before cherry-pick on sprustonlab post-consolidation. The reviewer must explicitly confirm path-translation occurred (this is a PC1.3 / PC2.4 narrative-pass criterion).
- **D8 leverage:** When closure is ambiguous, ask abast directly: "Does commit X depend on commit Y?" — they wrote it; they know.

### R4 — Deliberate non-pulls becoming silent divergence

- **Path 1 and Path 2 (symmetric):** Maintain `NON_PULLED.md` (per PC1.4 / PC2.6) with: commit SHA, file(s), abast author rationale (if asked), our rejection rationale, re-evaluation trigger (e.g., "revisit if #23 ships, if abast rebases, if user requests feature X"). Seed the ledger from FDR §8 H4 on day one — the 7 candidates are already enumerated.
- **Path 2 specific:** Auto-flag any abast commit whose first-line message contains config / settings / claude / `.claude` / claudechic / fast / defaults — these are highest-risk for silent BF1 reintroduction or H2 wrong-path-landing.

### R5 — Parallel mirror-tree resolution (`claudechic/workflows/` vs `claudechic/defaults/workflows/`)

- **Path 1:** Resolve as PC1.5 — explicit early decision before #23. Use revised Probe E2 (forward decision with abast input on convergence-willingness) to inform the choice. The decision establishes a precedent for where claudechic-owned content lives, which then informs #23's analogous "where does claudechic config live" question.
- **Path 2:** Resolve as PC2.2 — declared in the #23 design doc even though #23 doesn't directly touch the workflow tree. The declaration must commit to a canonical root and a migration plan for the loser-side content. Risk: #23's design naturally focuses on settings; forcing the workflow-root declaration into the same doc may dilute #23's focus or be quietly dropped.
- **D8 leverage:** Revised Probe E2 is the cheapest and highest-leverage probe in the entire evaluation. Run it regardless of path.

### R6 — `app.py` / `commands.py` high-churn collision

- **Path 1:** Pull and resolve these files in their own dedicated batch, before #23 design. FDR §5 commentary confirms abast's edits are isolated to startup/init regions touching different functions than sprustonlab's edits — the resolution is mechanical-textual, mostly insertion-collision rather than edit-collision. Document the merged behavior so #23's wiring decisions can build on it.
- **Path 2:** Defer; resolve post-#23. #23 will have added wiring (a `/settings` screen registration in app.py and a `/settings` command in commands.py); the post-#23 cherry-pick must preserve both abast's edits AND the new wiring AND not silently reorder the startup sequence in a way that breaks abast's auto-perm-default behavior. Higher cognitive load.
- **D8 leverage:** Ask abast which `app.py` / `commands.py` changes they consider stable / shippable vs experimental — drop the experimental ones from the pull set. FDR's per-hot-file commit attribution table is the input list to this conversation.

### R7 — BF1 boundary violation re-introduced by an abast pull

- **Path 1:** Add the boundary-lint step (PC1.6) *before* the first cherry-pick. Any pull violating it is auto-rejected and goes to `NON_PULLED.md` with the violation recorded. FDR §7d notes the boundary-relocation surface itself is in quiet files abast hasn't touched, so the lint-violation inflow risk concentrates on `fast_mode_settings.json` (already known per FDR §8 H4) and the small `config.py` tweak.
- **Path 2:** Same lint, but it must be in place before the first *post-#23* cherry-pick. The lint also serves as a guard that #23's own implementation does not regress (defense in depth).
- **D8 leverage:** Inform abast of the BF1 rule upstream; ask them to mark commits that may violate it. This converts a post-hoc detection problem into an opt-in self-disclosure problem.

### R8 — Semantic-layout collision via path-mirror pairs (NEW, dominant Path 2 hazard)

- **Path 1:** Subsumed under R5 / PC1.5 — once the canonical-root decision is made and abast's `defaults/...` adds are re-pathed (or rejected) before pull, R8 collapses into R5's resolution. The ~85 mirror pairs become a single decision applied uniformly.
- **Path 2:** Without PC2.2 + PC2.3, R8 is uncontrolled: abast's `defaults/...` cherry-picks land at non-existent paths on sprustonlab post-consolidation, apply textually, and create a parallel duplicate asset tree silently disconnected from sprustonlab's loader code. **Mitigation must be structural, not procedural:** PC2.5's regression test must include a check that fails if both `claudechic/defaults/workflows/` and `claudechic/workflows/` exist and contain workflow content. Procedural review (PC2.4) alone will not catch this — reviewers see a clean cherry-pick of one new file at a time and may not recognize the cumulative parallel-tree pattern until it is built.
- **D8 leverage:** Ask abast to pre-rebase their `defaults/...` adds onto whichever root sprustonlab declares canonical, *before* any cherry-pick. This converts R8 from a post-hoc detection problem into an upstream-prevention problem. This is a high-leverage cooperation request and should be one of the first asks of abast in either path.

---

## 6. Lens-Recommended Path

### Final lean

**From the risk lens, Path 1 is preferred, conditional on PC1.1–PC1.6 being achievable.**

The pre-FDR lean was Path 1; the FDR data **strengthens** rather than weakens this position. The key shift is the elevation of R8 (H2 mirror-tree semantic-layout collision) to a Critical-impact risk under Path 2, which the pre-FDR matrix did not have visibility into. This risk dominates the matrix's D6.d row — the failure mode the entire evaluation was constructed to surface.

### Rationale (FDR-confirmed)

1. **D6.d (intent loss) is the dominant differentiator.** R2, R5, and R8 all compound this mode under Path 2's sequencing. R8 is *new* from FDR §8 and has Critical impact under Path 2.
2. **Path 1 surfaces conflicts at decision-time** (designers are alert, conflicts inform design). Path 2 surfaces them at completion-time (designers feel done, conflicts feel like noise). The R8 mirror-pair collision is the worst case of the latter — silent, easy to miss, hard to undo without re-deriving the design.
3. **Path 1's preconditions are mostly process** (achievable internally). Path 2's preconditions add cooperation-timing (PC2.3), test-infrastructure (PC2.5), and a forced declaration of a layout question outside #23's native scope (PC2.2). Path 2 demands more of the surrounding ecosystem to be true.
4. **D8 (abast cooperation) is more leverage-able in Path 1** — intent-recovery requests happen while abast's commits are fresh in the puller's mind, not after #23 has further evolved the codebase.
5. **The data substrate confirms BF2 in a manageable form, not a catastrophic one** for the textual hot files — `config.py` has only 4 lines of abast churn, `commands.py` 71, `app.py` 167. Pulling these first under Path 1 is a contained operation per FDR §5 attribution. Letting them collide post-#23 under Path 2 inflates contained problems into redesign-collisions.
6. **The H2 mirror-tree hazard is the FDR's most consequential finding** and is structurally easier to address pre-#23 (Path 1, as part of PC1.5) than post-#23 (Path 2, as PC2.2 outside #23's natural scope).

### Acknowledged counter-weights from FDR

These do not flip the lean but must be acknowledged in the recommendation document:

- **FDR §7d "quiet zone":** the userprompt-derived BF1-fix surface (`agent.py`, `errors.py`, `theme.py`, `hints/state.py`, `hints/triggers.py`, `usage.py`, `features/worktree/git.py`) is in files NEITHER fork has touched since merge-base. Path 2's "design first, pull later" loses no contention on this surface — the BF1-fix work is genuinely path-independent. Path 1's advantage here is moderate, not decisive.
- **FDR Anomaly #1:** abast's "truly independent" footprint after removing the ~85 mirrors is only ~13–15 files. The volume of true contention is small, which slightly tempers the case for early pull (Path 1's cost is modest, but Path 2's cost is also modest if R8 can be controlled).
- **FDR §5 commentary:** abast's `app.py` edits touch *different functions* than sprustonlab's. R6 collisions are mostly insertion-collision rather than edit-collision — easier to merge mechanically than the raw 353-churn number suggests.

### Cross-lens disagreement (with Composability)

**Composability (architecture lens) recommends Path 2** via the "boundary-becomes-a-filter" argument: once #23 establishes the settings/boundary contract, every incoming abast cherry-pick can be evaluated against it on a principled basis (BF5 mitigation by contract, not intuition). The translation cost per cherry-pick is bounded because abast's settings-territory deltas are small. Composability acknowledges R5 (the mirror-tree axis) as an exception requiring "procedural compensation" (force consultation of GitArch's per-file map during #23 design).

**The risk lens disagrees as follows:**

- The "boundary-as-filter" argument is sound *for cherry-picks that carry settings semantics*. The FDR data confirms these are a small surface (~4 lines on `config.py`, abast's `fast_mode_settings.json`, the few config-test edits). The filter does its job here — Composability is right on this axis.
- But the dominant Path 2 risk per FDR §8 is **R8 (H2 mirror-tree)**, which carries no settings semantics — the ~85 mirror pairs are workflow content, not settings keys. The boundary contract has nothing to filter against on this axis. Composability's "procedural compensation" (consult the per-file map) is itself a reliability bet, and the risk lens does not credit reliability bets that depend on someone reading the right doc at the right moment when a structural pre-decision (Path 1's PC1.5) is available.
- The lenses agree on the *settings* axis; they disagree on the *workflow-tree* axis. The workflow-tree risk is materially larger by FDR's own data. Hence the risk lens's recommendation does not match Composability's.

**This disagreement is genuine and should be visible in the recommendation document, not buried.** The user is the ultimate adjudicator. Both lenses are operating correctly within their scope; they reach different conclusions because they weight different axes. UserAlignment may add a third weighting; the recommendation document should make all three legible.

### Conditions under which the lean reverses

- **Probe E4 reveals abast has an imminent and deeply different `/settings` redesign of their own.** Then Path 1's pull before #23 design risks landing a parallel design that conflicts with sprustonlab's #23 vision; Path 2's "design our way first, cherry-pick the compatible bits later" becomes safer.
- **Revised Probe E2 reveals abast cannot or will not converge on a single workflow root**, AND the team accepts living with the parallel structure indefinitely. Then R8 is unavoidable in either path and Path 2's "boundary-as-filter" advantage becomes load-bearing for the *remaining* settings-territory cherry-picks.
- **PC1.2 / D8 is unavailable in practice** despite being declared available. Then Path 1's R2 and R5 mitigations collapse, narrowing the gap considerably. Composability's lens does not depend on D8 in the same way; under D8-unavailable, Path 2 may become preferred.

### Non-recommendation: do not bypass the preconditions

The standing rule (promoted to Section 3 top-level framing) governs here: **a path with preconditions skipped is more dangerous than the other path with preconditions met.** Whichever path is chosen, executing it without the corresponding preconditions converts the path's known risks into unmonitored risks, and retroactively reclassifies the path as the unsafe one. The final recommendation document must surface this rule as a *headline*, not a footnote.

---

## Appendix A — Refinement Log (FDR-applied)

All eight prior `[GA-PENDING]` markers cleared:

1. **§5 hot files list confirmed:** `app.py`, `commands.py`, `config.py` are the top-3 hot files AND all three are on the #23 surface (FDR §5 + §7a). R1 expanded from "config.py only" to all three. R6 weight unchanged but commentary refined per FDR §5 (different-functions pattern).
2. **§7 #23 surface × divergence intersection absorbed:** the body-scope (settings screen + docs) and userprompt-scope (boundary fix) treated separately per BF6. The body scope intersects the hot-file set (R1, R6); the userprompt scope is in FDR §7d's quiet zone (R7 likelihood reduction under Path 1 noted).
3. **§8 hazard summary absorbed:** added R8 (H2 mirror-tree semantic-layout collision) as new matrix row — the FDR's most consequential finding for this evaluation. R5 weight raised from "H/Critical" Path 2 to "VH/Critical" Path 2 by the same data.
4. **R3 worked example added (FDR Anomaly #6 + §8 H3):** `0ad343b` → `26ce198` anthropic-pin-then-`/fast` dependency chain named verbatim.
5. **R3 second worked example added (FDR Anomaly #3):** `claudechic/workflows/loader.py` cherry-pick wrong-path-landing on post-consolidation sprustonlab named verbatim.
6. **Probe E2 restructured:** original "why" question is FDR-answered; revised E2 is a forward-convergence decision with abast input.
7. **Probe E5 cleared:** superseded by FDR §6c + §7. Marked CLEARED in Section 4 for traceability.
8. **Composability cross-lens disagreement surfaced in Section 6:** explicit treatment of the boundary-as-filter argument, where it succeeds (settings axis), where it fails (mirror-tree axis), and what this means for the recommendation document.

### Refinements pending external input (probes not yet executed)

- [ ] Probe E1 result: would refine R1, R7 likelihoods (FDR predicts trivial; empirical confirmation outstanding).
- [ ] Revised Probe E2 result: would refine R5/R8 likelihoods (forward-convergence decision pending D8 conversation).
- [ ] Probe E3 result: would quantify R7 (BF1 inventory in abast tree pending grep).
- [ ] Probe E4 result: could flip the lean (see Section 6 reversal conditions).
- [ ] Probe E6 tabletop: would refine D6.b/c/d severity weights.
- [ ] TerminologyGuardian's BF1 fix scope cross-check vs R7 mitigation.
- [ ] Composability's coupling map cross-check: their lens recommends Path 2, the risk lens recommends Path 1; UserAlignment's adjudication weighting is the next-step input.

---

*End of risk evaluation (finalized).*
