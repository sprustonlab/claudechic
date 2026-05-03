# Alignment Audit — issue_23_path_eval

**Author:** UserAlignment (Leadership lens — alignment with stated user intent)
**Phase:** Specification
**Status:** Sections 1, 3, 5 written pre-output. Sections 2, 4, 6 to be completed once Composability, TerminologyGuardian, Skeptic, and the formal GitArchaeologist Fork Diff Report deliverables land.

---

## 1. Frame

### Role of this audit

This audit applies a single lens: **does what the team produces match what the user actually asked for?** It is not a technical review (Composability covers that), nor a hazard review (Skeptic), nor a naming review (TerminologyGuardian), nor a fork-divergence read (GitArchaeologist). It is an alignment check that verifies the four Leadership outputs and the synthesized recommendation trace back to the user's stated success and failure criteria — and that no scope has been added, dropped, or reshaped without an explicit user decision.

### Source of truth

The following items in STATUS.md are treated as the binding contract for this run and are quoted/referenced throughout:

- **Vision Summary → Goal.** The deliverable is a Leadership-evaluated written recommendation choosing between Path 1 (selectively pull from abast → implement #23) and Path 2 (implement #23 → selectively pull from abast).
- **Vision Summary → Success looks like.** Five success items: (a) Fork Diff Report; (b) independent evaluations from the four Leadership lenses; (c) risk analysis on merge conflicts, lost work, settings boundary; (d) clear recommended path with rationale; (e) user has confidence to start chosen path in a separate session. Plus two no-go items: no code changes, no time estimates.
- **Vision Summary → Failure looks like.** Six failure items: recommendation without diffs; blurred claude-vs-claudechic boundary; recommendation triggers loss of feature work; Coordinator does the analysis; scope creep into implementing #23; time estimates leaking in.
- **Locked Decisions D1–D15** and **Baseline Findings BF1–BF6** as captured in STATUS.md.
- **userprompt.md** as the verbatim user words — referenced when checking that locked decisions did not drift from the original ask.

### What this audit will not do

- It will not re-litigate a locked decision. D1–D15 are settled. If a Leadership output contradicts one, that is a fire-alarm escalation to Coordinator, not a debate within this audit.
- It will not advocate for a path until Section 6, where lens-conclusion is allowed.
- It will not contact the user.
- It will not estimate time.

### How findings are graded

For each Leadership output (Section 2) and for the synthesized recommendation (Section 5), four checks apply:

- **(a) Addresses the user's actual ask** — the output answers a question the user asked or that the Vision Summary requires, not an adjacent problem.
- **(b) Respects locked decisions D1–D15** — no decision is silently re-opened.
- **(c) Honors symmetric evaluation** — until the synthesis step, no advocacy; both paths are weighed through the agent's own lens.
- **(d) Avoids time estimates** — per D10.

Findings are tagged `[OK]`, `[GAP]`, `[DRIFT]`, or `[FIRE-ALARM]`.

---

## 2. Per-Leadership-Output Audit

> Awaiting deliverables. This section will be filled in once each output lands. Each subsection will apply the four-check grade and flag any contradictions with D1–D15 immediately to Coordinator (per the spawn-phase fire-alarm instruction).

### 2.1 GitArchaeologist — Fork Diff Report

**Status:** FINAL. Graded.
**Artifact:** `fork_diff_report.md` + companion `fork_file_map.csv` (272 rows).
**Headline:** `[OK]` on every criterion within FDR's responsibility. No fire-alarm. The FDR also actively reinforces C20/C27 via Anomaly 5 ("Issue #23 / userprompt scope gap is real and load-bearing — BF6 confirmed").

**Grading (criterion → status → evidence):**

| Criterion | Status | Evidence |
|---|---|---|
| **C1** (Fork Diff Report exists with per-file map, #23 surface, hazard summary) | `[OK]` | §4 per-file map (top-80 inline + CSV), §6 #23 surface read (6a/6b/6c), §8 hazard summary (H1–H4 tiers). |
| **C10** (no scope creep into implementing #23) | `[OK]` | §8 closes with explicit "What this section does NOT do" — disclaims ranking paths, recommending non-pulls, estimating effort, assessing lost-work probability. Stays inside its lane. |
| **C11/C19** (no time estimates) | `[OK]` | Decision-anchor list cites D10 explicitly. Spot-checked the document: no week/day/sprint/ETA/duration language anywhere. |
| **C20** (issue body scope vs userprompt-derived boundary scope kept distinct, both addressed) | `[OK] — strong` | §6a is *only* body scope. §6b is *only* userprompt-derived. §6c.iii is an explicit "Issue-body-named vs inferred vs userprompt-derived only" mapping table. Anomaly 5 names BF6 by ID and confirms it. This is exactly the structure D11 mandated. |
| **C21 (D12)** (default branches only, `origin/main` ↔ `abast/main`) | `[OK]` | Decision-anchor list and Appendix command trail (`git fetch origin main`, `git fetch abast`, `git merge-base origin/main abast/main`) confirm. |
| **C21 (D13)** (direct merge-base only, no mrocklin axis) | `[OK]` | Merge-base `285b4d120c59bd41250ca2117864cb113b5bd9b3` named. No mrocklin remote added; appendix command trail confirms. |
| **C21 (D14)** (3–6 themes per fork) | `[OK]` | sprustonlab: 4 themes (S-T1 through S-T4). abast: 5 themes (A-T1 through A-T5). Both within bounds. |
| **C21 (D15)** (top-N=80 by churn inline, full set in CSV) | `[OK]` | §4 table lists items 1–80; companion `fork_file_map.csv` (272 rows) cited. |
| **C23** (BF2 acknowledgment — abast likely already touched #23 files) | `[OK] — substrate` | §7a confirms all three of #23's most "live" code-touch sites (`app.py`, `commands.py`, `config.py`) are already hot files; §8/H1 quantifies the collision. Skeptic must operationalize this; FDR provides the substrate cleanly. |
| **C25** (BF4 dependency-drop addressed) | `[OK] — substrate` | §8/H4 explicitly identifies the concrete case: pulling `26ce198` (`/fast`) without `0ad343b` (`anthropic==0.79.0` pin) is a BF4 instance. Anomaly 6 reinforces. Skeptic must operationalize the prerequisite-chain audit. |
| **C26** (BF5 deliberate non-pull register) | `[OK] — substrate` | §8/H4 enumerates non-pull candidates with rationale (`fast_mode_settings.json`, `26ce198`, `5700ef5`, `7e30a53`, `f9c9418`, `0ad343b`, the `claudechic/defaults/` tree). The *register* — its written form, ownership, update cadence — is Skeptic's to specify. FDR substrate is sufficient. |
| **C27** (issue body scope vs derived scope distinguished where it matters) | `[OK] — strong` | Same evidence as C20. Additionally, §6c.ii distinguishes within the boundary surface itself (legitimate Claude-namespace reads in `history.py`/`sessions.py` should NOT relocate; write-sites should). |

**Criteria GitArch's FDR is *not* responsible for (cross-listed as inputs to other Leadership outputs):**

- **C2** (all four lenses cited in synthesis): not yet — synthesis pass.
- **C3** (risk analysis covers the three Vision risk surfaces): substrate provided in §8; Skeptic's deliverable.
- **C4/C5/C32/C33** (recommended path, confidence, handoff): synthesis pass.
- **C6** (recommendation inspects actual fork diffs): partly — FDR is the inspection. Synthesis must visibly cite it.
- **C7** (claude vs claudechic boundary not blurred): TG-led; FDR doesn't author the glossary.
- **C8** (no lost work): Skeptic-led; FDR substrate informs.
- **C9** (synthesis not analysis): N/A to FDR (FDR is analysis from a delegated agent — the prime directive is the *Coordinator* not authoring analysis, which is honored as long as Coordinator does not rewrite this).
- **C12–C18** (locked decisions D1–D8): mostly N/A to FDR; D11 already covered under C20.
- **C22** (BF1 remediation): TG/Composability/Skeptic ownership; FDR §6c.ii provides the surface map but doesn't claim ownership of the remediation step.
- **C24** (semantic-review checkpoints with artifacts/reviewer/pass-fail): Skeptic-led; FDR §8 hazard tiers (especially H2) provide what the checkpoints need to look at, not the checkpoint specification itself.
- **C28–C31** (honorable-mention path framing, form): synthesis pass.

**Section 4 gap status from FDR alone:**
- Gap "BF1 remediation ownership" — still open; FDR does not claim it (correctly).
- Gap "BF3 semantic-review checkpoint specification" — substrate present (H2 = the canonical case); awaiting Skeptic to specify checkpoint shape.
- Gap "BF5 non-pull register" — substrate present; awaiting Skeptic to specify the register.
- Gap "D6 four-fold lost-work coverage" — N/A to FDR.
- Gap "D7 conflict surfacing" — N/A to FDR (synthesis pass).
- Gap "explicit confidence" — N/A to FDR.

**Notable strengths worth preserving in synthesis:**

- The **path-mirror double-counting anomaly** (Anomaly 1, ~85 mirror pairs collapsing 168+98 into ~13–15 truly independent abast files) reframes "how divergent are these forks textually" — the synthesis must not quote the raw 168/98 numbers without this caveat or it will mislead the user.
- The **H2 layout collision** (`claudechic/workflows/` vs `claudechic/defaults/workflows/`) is described as "the dominant Path 2 hazard." This finding is load-bearing for any path comparison and should appear verbatim in synthesis under D7's conflict-surfacing mandate.
- The **scope-gap reinforcement of BF6** (Anomaly 5) tells synthesis exactly which files belong to which scope — recommendation should sequence boundary-relocation (`hints/state.py`, `errors.py`, `theme.py`, `agent.py`) separately from issue-body work (`/settings` screen, `docs/configuration.md`).

**No fire-alarm. No contradiction with D1–D15 or BF1–BF7. Grading complete for §2.1.**

### 2.2 Composability — architecture & module coupling evaluation

**Status:** FINAL (post-FDR delta-pass). Graded.
**Artifact:** `composability_eval.md` (lens-conclusion: Path 2).
**Headline:** `[OK]` on every applicable criterion. No fire-alarm. The `app.py` concentration check resolved against Path 1 in the open; the lens-conclusion was reaffirmed, not flipped — exactly the discipline C9 calls for.

| Criterion | Status | Evidence |
|---|---|---|
| **C2** (lens contribution traceable) | `[OK]` — substrate | §1 names four axes of variation; §6 ties conclusion to axes 1, 2, 3 (with axis 4 as caveat). Synthesis can cite this verbatim. |
| **C3** (settings boundary risk surface) | `[OK]` — substrate | §4.1 enumerates D5/BF1 violation modules with sprustonlab vs abast churn. Risk surface mapped per-module. |
| **C7** (claude vs claudechic boundary not blurred) | `[OK]` — strong | §1 lists three explicit boundaries; §3 enforces D5 via "boundary as filter"; §4.1 cleanly separates relocation targets from §4.2 "modules that read Claude's namespace legitimately." |
| **C8** (no lost-work in any D6 sense) | `[OK]` — substrate | Path 1 vs Path 2 cost table (§5) frames coupling exposure as a proxy for D6.b/c/d risk; defers explicit D6 four-fold treatment to Skeptic appropriately. |
| **C10** (no scope creep into implementing #23) | `[OK]` | No code changes proposed; no #23 implementation specs; only architectural reasoning about sequencing. |
| **C11/C19** (no time estimates) | `[OK]` | Verified — process-detail form throughout. §6 explicitly cites D9/D10 honored. |
| **C13** (D2/D3 selective-pull semantics on both paths) | `[OK]` | §3 names "selective pull (D3)" as the integration mechanism; no all-or-nothing language. |
| **C14** (D4 — `~/.claude/.claudechic.yaml` named as relocation target) | `[OK]` | §4.1 row 1 names the violation explicitly. |
| **C15** (D5 — claudechic does not write to any `.claude/` in end state) | `[OK]` — strong | §1 axis 1 enforces this; §4.1 enumerates current violations; §4.2 distinguishes legitimate Claude-namespace reads. |
| **C17** (D7 conflicts surfaced; equal-fork-value preserved) | `[OK]` | §6 "Boundaries of this conclusion" explicitly cites D7; the lens does not advocate one fork's work over the other. |
| **C18** (D8 abast cooperation leveraged) | `[OK]` — substrate | §4.4 invokes D8 ("re-pathing abast's `claudechic/defaults/` adds before applying them is the de-risking move"). |
| **C20/C27** (issue body scope vs derived scope distinguished) | `[OK]` | §1 axes 1+2 separate footprint/locality (derived) from settings-domain (issue body adjacent); §4.1/§4.2 maintain the distinction. |
| **C22** (BF1 remediation) | `[OK]` — strong | §4.1 enumerates the 4-path BF1 violation set with file:line evidence. |
| **C23** (BF2 acknowledgment) | `[OK]` — substrate | §5 cost table integrates FDR §5 hot-file attribution; §4 maps abast contribution per module. |
| **C24** (BF3 semantic-review checkpoints) | `[OK]` — substrate | §3 acknowledges "BF3 territory" by name; checkpoint *specification* delegated to Skeptic appropriately. |
| **C25** (BF4 dependency-drop) | `[OK]` — substrate | §1 axis 4 mirror-tree concern includes Anomaly 3's "wrong-path-landing" dependency-drop case. |
| **C26** (BF5 deliberate-non-pull register) | `[OK]` — substrate | §3 invokes BF5 in the cost framework; explicit register specification delegated to Skeptic. |
| **C29** (Path 3c contingent fallback handled) | `[N/A — synthesis]` | Out of lens scope. |
| **C30** (Path 3d coordinate-with-abast tactic) | `[OK]` — substrate | §6 cites D8 as "load-bearing" advantage shared by both paths; §4.5 anchors the de-risking action concretely. |

**Notable strengths preserved for synthesis:**
- §4.6 / §6 absorb D17 explicitly: "*D17 ratifies this form*" — the lens recognizes the user's lock as ratification of an inferred constraint.
- Disagreement-handling discipline: §6 names where Path 1 has a *genuine* advantage (axis 4 forced-visibility) without abandoning the lens conclusion. This is the symmetry C17 requires.
- §6 "Caveat (the lens does not erase)" explicitly acknowledges where the lens does not deliver the answer — exactly the lens-discipline C9/C17 demand.

**No fire-alarm. No D1–D17 / BF1–BF7 contradictions.**

### 2.3 TerminologyGuardian — naming & boundary terms

**Status:** Substantively FINAL (post-FDR + D16/D17 lock). Graded as-is. The Coordinator-flagged "small D16/D17 edit" appears to be already integrated (§3.3 has D16 verbatim; §3.2/3.4/3.5/3.7 reference D17). One alignment-relevant inference flagged for user adjudication — see below.
**Artifact:** `terminology_glossary.md` (lens-conclusion: Path 2).
**Headline:** `[OK]` on every applicable criterion. No fire-alarm. One inference under D17 — the "global tier disappears" reading — is correctly flagged by TG itself for UserAlignment, and is surfaced here as an alignment-lens question.

| Criterion | Status | Evidence |
|---|---|---|
| **C2** (lens contribution traceable) | `[OK]` — strong | §2 (descriptive), §3 (prescriptive), §4 (per-path cost ledger), §5 (lens-conclusion). Each section's contribution is independently citable. |
| **C7** (claude vs claudechic boundary not blurred) | `[OK]` — strong | §3.1 / §3.2 / §3.7 give the canonical D5 reading; §2c and §4 enumerate the violations and their cost. The strongest single output on this criterion. |
| **C10** (no scope creep) | `[OK]` | No code changes; vocabulary specification only. |
| **C11/C19** (no time estimates) | `[OK]` | Verified — cost-form ("rename volume," "vocabulary unity") not duration-form. |
| **C13** (D2/D3 selective-pull semantics) | `[OK]` | §4.2/§4.3 ledgers operate on per-cherry-pick basis. |
| **C14** (D4) | `[OK]` — strong | §3.1 lists the relocation; §3.4/§3.5 specifies the new homes. |
| **C15** (D5) | `[OK]` — strong | §3.1 + §3.7 give the operational definition; §3.7 specifies a code-asserted invariant test. |
| **C16** (D6 four-fold lost-work) | `[N/A — Skeptic-owned]` | TG defers to Skeptic appropriately (§4.5). |
| **C17** (D7 conflicts surfaced) | `[OK]` — strong | §5.4 cross-lens position table names the disagreement; §5.2 addresses each Path 1 advocate's counter symmetrically. |
| **C18** (D8 leverage) | `[OK]` | §4.2/§4.3 ledgers and §5.2/§5.3 invoke D8 cooperation symmetrically. |
| **C20/C27** (issue body vs derived scope) | `[OK]` — strong | §2a.6 item 8 and §3.3 distinguish issue body's "Settings window + configuration reference documentation" from userprompt-derived boundary rule (BF6 cited verbatim). |
| **C22** (BF1 remediation) | `[OK]` — strong | §3.1 lists all four BF1 violations with their post-#23 homes. |
| **C24/C25/C26** (BF3/BF4/BF5) | `[OK] — substrate` | TG acknowledges and points to Skeptic for operational specification (§4.5). |
| **C28** (Path 3b — selective-pull absorbed under D3) | `[OK]` — implicit | §4.2/§4.3 only operate on selective-pull semantics; "merge all of abast" framing absent. |

**D16/D17 absorption:**
- **D16:** §3.3 quotes the user resolution verbatim and gives the operational rules (where each word lives in code vs prose).
- **D17:** §3.2 names "D17 canonical"; §3.4 carries the migration mapping; §3.5 gives the full inventory; §3.7 makes "no top-level `.claudechic.yaml` file" a code-asserted invariant.

**Alignment-relevant inference flagged for user adjudication (NOT a fire-alarm):**
- §3.4 reads D17 as collapsing the global config tier into per-project — i.e., every project gets its own `analytics.id`, `default_permission_mode`, `themes`, etc. TG explicitly flags this as a "Terminology lens flag (not a re-opening of D17)" and surfaces the behavioural side-effect for UserAlignment review.
- **My alignment-lens read:** D17 as locked specifies *location* of config (directory form, inside `<launched_repo>/.claudechic/`). It does not unambiguously specify *whether a global tier exists* (it could exist at a different location, e.g., `~/.claudechic/config.yaml` outside any `.claude/`). TG's strict reading — "every reference to `~/.claude/.claudechic.yaml` becomes `.claudechic/config.yaml`" — is one defensible interpretation, but per-project `analytics.id` is a real behavioural change worth a user check. **Flagging as a candidate UQ5 for the next user batch — not a fire-alarm against D17.** (If user confirms TG's reading, lens-conclusions are unaffected.)
- **C20 implication:** under TG's reading, the "global config" notion the issue body alludes to (`~/.claude/.claudechic.yaml` per FDR §6a, §3.4 mapping) goes away; the recommendation must explain this end-state to the user clearly.

**No fire-alarm. No D1–D17 / BF1–BF7 contradictions.** The D17 strict-reading inference is surfaced for user check.

### 2.4 Skeptic — risk, failure modes, merge hazards

**Status:** FINAL (post-FDR; all 8 prior `[GA-PENDING]` markers cleared; R8 added from FDR §8 H2). Graded.
**Artifact:** `risk_evaluation.md` (lens-conclusion: Path 1).
**Headline:** `[OK]` on every applicable criterion, with `[OK] — strong` on C16 (D6 four-fold), C24 (BF3 checkpoint specification), C25 (BF4), C26 (BF5). No fire-alarm. Skeptic's lens output is the most rubric-saturated of the four — directly addresses every BF and four of the most load-bearing locked decisions.

| Criterion | Status | Evidence |
|---|---|---|
| **C2** (lens contribution traceable) | `[OK]` — strong | §1 frame; §2 matrix; §3 PCs; §4 probes; §5 mitigations; §6 conclusion + §6 reversal triggers. Every line in §6 traces back to a row or PC. |
| **C3** (risk on merge conflicts, lost work, settings boundary) | `[OK]` — strong | All three Vision-named risk surfaces explicitly addressed: hot-file collision (R1, R6), four flavors of lost work (D6 matrix + R2/R5/R7/R8), settings boundary re-introduction (R7) with BF1-named instance. |
| **C8** (no lost work in any D6 sense) | `[OK]` — strong | §1 elevates D6 to operating principle ("visibility and recoverability are first-class severity discounts"); §2 matrix scores D6.a/b/c/d explicitly per path. |
| **C10** (no scope creep) | `[OK]` | No #23 specs; only sequencing analysis. |
| **C11/C19** (no time estimates) | `[OK]` | Verified — process-detail form throughout. PC artifacts/reviewer-roles/pass-fail in process language. |
| **C13** (D2/D3) | `[OK]` | Selective pull integral to PC1.1 / PC2.1; no all-or-nothing language. |
| **C14** (D4) | `[OK]` — strong | R7 explicitly names BF1 boundary; PC1.6 boundary-lint includes the relocation literal. |
| **C15** (D5) | `[OK]` | PC1.6 lint criterion: "claudechic writes inside `.claude/` or claudechic settings files appear at repo root → fail." |
| **C16** (D6 four-fold lost-work) | `[OK]` — strong | §1 dedicated calibration matrix on D6.a/b/c/d with detectability + recoverability + severity weights; matrix rows tagged with which D6 mode each impacts. **The reference treatment of C16.** |
| **C17** (D7 conflicts surfaced) | `[OK]` — strong | §6 "Cross-lens disagreement" subsection names Composability's argument verbatim, identifies the axis on which the lenses agree (settings) and disagree (workflow-tree), and explicitly preserves the user's adjudication right. **The reference treatment of C17.** |
| **C18** (D8 leverage) | `[OK]` — strong | §5 mitigations all invoke "D8 leverage" rows; PC1.2 / PC2.3 lock D8 cooperation as a precondition; revised E2 uses D8 for forward decision. |
| **C20/C27** (issue body vs derived scope) | `[OK]` | §2 matrix data substrate references FDR §6c (body vs derived); §6 BF1 fix surface (FDR §7d quiet zone) treated as derived-scope. |
| **C22** (BF1 remediation) | `[OK]` | R7 + PC1.6 specify boundary-lint as remediation gate. |
| **C23** (BF2) | `[OK]` — strong | R1 quantifies "all three of #23's most-live code-touch sites are hot files" via FDR §7a; matrix likelihood weights derived from FDR §5 attribution. |
| **C24** (BF3 semantic-review checkpoints with artifact/reviewer/pass-fail) | `[OK]` — strong | **PC1.3 and PC2.4 specify all four required dimensions verbatim:** "Artifact reviewed," "Reviewer (role)," "Pass criterion," "Fail criterion." This is the **C24 reference specification** — a model the synthesis can adopt directly. |
| **C25** (BF4 dependency-drop) | `[OK]` — strong | R3 names two concrete worked examples: `0ad343b` → `26ce198` anthropic-pin chain; abast `claudechic/workflows/loader.py` cherry-pick wrong-path-landing. PC1.1 enumerates pull-set with prerequisites column. |
| **C26** (BF5 deliberate-non-pull register) | `[OK]` — strong | PC1.4 / PC2.6 specify `NON_PULLED.md` ledger with: commit SHA, files, abast author rationale, our rejection rationale, re-evaluation trigger. Seeded from FDR §8 H4. **The C26 reference specification.** |
| **C29** (Path 3c contingent fallback) | `[OK]` — implicit | §6 "Conditions under which the lean reverses" lists triggers; if all triggers fire and PC1.2/D8 collapses, the freeze-abast option is implicit in "Path 1's R2 and R5 mitigations collapse." Synthesis can make 3c explicit if needed. |
| **C30** (Path 3d coordinate-with-abast tactic) | `[OK]` — strong | §5 mitigations + revised E2 + PC1.2 / PC2.3 give concrete coordinate-with-abast actions per risk row. |

**No fire-alarm. No D1–D17 / BF1–BF7 contradictions.**

**Skeptic's "standing rule" worth promoting in synthesis:** "A path with preconditions skipped is more dangerous than the other path with preconditions met." This is the critical safety rail for whichever path wins — recommendation document must surface it as a headline, not a footnote (per Skeptic §6 "Non-recommendation" subsection).

---

## 3. Honorable-Mention Paths

The orientation phase surfaced four alternatives (Path 3, 3b, 3c, 3d). D1 closed Path 3 (mrocklin upstream). D2/D3 absorbed Path 3b (selective cherry-pick) into the default mechanism for both Paths 1 and 2. The remaining two are assessed here for whether they should be visible in the final recommendation document.

### Path 3b — Selective cherry-pick (originally distinct from full merge)

**Status: absorbed, not standalone.** Under D3, "selective pull" is the default integration mechanism for both Path 1 and Path 2. Path 3b is therefore no longer a third path — it is the mechanism inside both paths. The recommendation should state this explicitly so a future reader understands that the original Path 1/Path 2 framing has been tightened, and that Skeptic's BF4/BF5 sub-risks (dependency-drop, deliberate non-pulls) apply to both paths equally rather than only to a hypothetical "Path 3b."

**Recommendation visibility:** Surface as a one-sentence note in the framing section ("Path 1 and Path 2 both use selective pull (D3); the original 'merge all of abast first' framing has been retired"), not as a separate option.

### Path 3c — Freeze abast, never sync

**Status: legitimate contingent fallback.** D7 establishes equal value between forks; D8 confirms abast cooperation is available; D6 makes "lost work" a four-fold concept. If Skeptic's hazard analysis concludes that any abast sync — even selective — has unacceptable lost-work exposure (per any of D6 a–d), then "do not sync at all; fork sprustonlab forward independently" becomes the safety-rail option. This contradicts the user's stated framing ("merge any changes from abast first" or "make the changes here and then sync"), so it should not appear as a co-equal option, but it should appear as a clearly-flagged fallback that fires only if specific hazard thresholds are met.

**Recommendation visibility:** Surface in the risk-analysis section as a contingent fallback, with explicit triggering conditions ("if Skeptic finding X is realized, freeze-abast becomes preferable to either Path 1 or Path 2"). Do not list it among the primary options being chosen between.

### Path 3d — Coordinate with abast on joint settings design before either side implements

**Status: tactic, not path.** D8 confirms abast cooperation is available. This is not a competing third path; it is a de-risking lever that applies to both Path 1 and Path 2 and that becomes more valuable under BF2 (abast has likely already touched #23's files), BF3 (silent semantic conflicts), and BF4 (dependency-drop). Examples of what to coordinate: agreed-upon settings file location and schema; agreed-upon migration story for `~/.claude/.claudechic.yaml`; identification of which abast commits are prerequisite chains vs. independently cherry-pickable.

**Recommendation visibility:** Surface as a concrete pre-flight action in the recommended path's "what needs to happen" detail, regardless of which path wins. Phrase as actions, not durations (per D10).

---

## 4. Gap Analysis

Six gaps were pre-flagged in Section 2 as candidates. Status post-grading:

| Gap | Status | Owner / evidence |
|---|---|---|
| **BF1 remediation ownership** | `[CLOSED]` | Collectively owned. TG §3.1 enumerates all four BF1 violations with their post-#23 homes; Composability §4.1 maps the violation surface to modules with churn data; Skeptic R7 + PC1.6 specifies the boundary-lint remediation step. The synthesis must cite all three. |
| **D6 four-fold lost-work coverage** | `[CLOSED]` | Skeptic §1 + matrix §2 give the reference treatment — D6.a/b/c/d severity-calibrated with detectability + recoverability discounts. Synthesis must inherit this matrix. |
| **BF3 semantic-review checkpoint specification** | `[CLOSED]` — strong | Skeptic PC1.3 / PC2.4 specify artifact / reviewer-role / pass criterion / fail criterion verbatim. **C24 reference specification.** Synthesis must adopt or strengthen, never weaken. |
| **BF5 deliberate-non-pull register** | `[CLOSED]` — strong | Skeptic PC1.4 / PC2.6 specify `NON_PULLED.md` ledger structure (commit SHA, files, rationale, re-evaluation trigger), seeded from FDR §8 H4. **C26 reference specification.** |
| **D7 conflict surfacing** | `[CLOSED] at lens level — STILL ACTIVE for synthesis` | Skeptic §6 cross-lens subsection, TG §5.4 cross-lens position table, and Composability §6 boundaries-of-conclusion all name the disagreement. The synthesis must preserve this — papering over the disagreement (Skeptic→Path 1, Composability+TG→Path 2) is a C9/C17 failure. |
| **Explicit confidence statement** | `[OPEN — synthesis-side]` | All three lens-conclusions are stated with hedging ("preferred, conditional on…", "preferred, with a caveat", "Recommendation from the terminology lens: Path 2"). None states a confidence level explicitly (high/medium/low or %). The synthesis must add a single overall confidence statement on the recommended path per C32, ideally with axis-by-axis breakdown ("high confidence on settings boundary; medium on workflow-tree resolution conditional on D8"). |

**Additional gaps surfaced during Section 2 grading (not pre-flagged):**

| New gap | Status | Notes |
|---|---|---|
| **D17 strict-reading inference (global tier collapse)** | `[OPEN — surface to user]` | TG §3.4 reads D17 as eliminating the global config tier; per-project `analytics.id` is a real behavioural change. Lens-conclusions are unaffected if user adjudicates either way, but the recommendation document must surface this consequence for confirmation. **Recommend Coordinator add as UQ5 in next user batch.** |
| **Standing rule surfacing** | `[OPEN — synthesis-side]` | Skeptic's "a path with preconditions skipped is more dangerous than the other path with preconditions met" must surface as a headline in the recommendation, not a footnote. Ratifies C5/C33 (concrete handoff with confidence) — if preconditions aren't named load-bearing, the user cannot start the path safely in a separate session. |
| **UQ3 (workflow-tree canonical layout) status** | `[OPEN — pre-flight]` | TG/Composability/Skeptic all consider this load-bearing for their respective lens-conclusions; revised Probe E2 (Skeptic) explicitly gates this on D8 cooperation. The recommendation document must either (a) defer the recommended path to an answer on UQ3, or (b) recommend conditionally with UQ3 as a named pre-flight gate. The user has not yet adjudicated UQ3. |
| **UQ4 (`fast_mode_settings.json` treatment) status** | `[OPEN — conditional]` | TG explicitly notes UQ4 only matters if `/fast` is on the want-to-pull list. Synthesis must either rule on `/fast` first or carry UQ4 forward as a conditional question. |

---

## 5. Final Recommendation Framing — Acceptance Criteria

When the Coordinator's synthesized recommendation document is drafted, this audit will perform one alignment pass. The pass applies the following acceptance criteria. A recommendation that fails any non-optional criterion gets sent back, not waved through.

### Required content (from Vision success criteria)

- **C1** Fork Diff Report referenced and visibly informing the path comparison (per-file divergence map, #23 surface read, hazard summary).
- **C2** All four Leadership lenses (Composability, TerminologyGuardian, Skeptic, UserAlignment) cited as inputs, with each lens's contribution traceable to the recommendation's rationale.
- **C3** Risk analysis present and addresses the three Vision-named risk surfaces: merge conflicts, lost work, settings boundary.
- **C4** A single recommended path is named with rationale.
- **C5** Recommendation gives the user enough concrete next-step detail to start the chosen path in a separate session with confidence (the "what needs to happen" register, not how long it takes).

### Required avoidances (from Vision failure criteria)

- **C6** Recommendation does not issue without inspecting actual fork diffs (cross-check: Section 2.1 must have graded the GitArch report `[OK]` on substance).
- **C7** Claude-vs-claudechic settings boundary is not blurred anywhere in the document (cross-check against D5 and BF1).
- **C8** Recommendation does not produce a path that, when later executed, will lose feature work in any of D6's four senses.
- **C9** Recommendation is the synthesis, not the analysis. If the document contains primary diff/hazard/architecture analysis written by the Coordinator rather than by a Leadership agent, that's a failure.
- **C10** No scope creep into implementing #23 (no actual config refactor specs, no PRs, no code changes referenced as completed in this run).
- **C11** No time estimates anywhere — durations, ETAs, "this should take," "by next week," or week/sprint counts. Replace with concrete process detail.

### Locked-decision compliance

- **C12** D1 honored — mrocklin upstream not surfaced as an option.
- **C13** D2/D3 honored — both paths use selective pull semantics; no language like "merge all of abast first."
- **C14** D4 honored — `~/.claude/.claudechic.yaml` is named as a thing that must move out under #23.
- **C15** D5 honored — claudechic does not write to any `.claude/` directory in the recommended end state.
- **C16** D6 honored — lost work is treated in all four senses, not collapsed to "merge conflicts."
- **C17** D7 honored — conflicts between Leadership outputs are surfaced explicitly, not papered over. Equal value of forks is preserved in framing.
- **C18** D8 honored — abast cooperation is leveraged in the recommended path's pre-flight detail.
- **C19** D9/D10 honored — no time pressure language, no time estimates.
- **C20** D11/BF6 honored — issue #23 body scope (`/settings` TUI + `docs/configuration.md`) and derived scope (userprompt boundary) are kept distinct, both addressed.
- **C21** D12/D13/D14/D15 honored in the Fork Diff Report's role within the recommendation.

### Baseline-finding integration

- **C22** BF1 — recommendation includes a remediation step for the existing violation (`~/.claude/.claudechic.yaml`, `.claude/hints_state.json`).
- **C23** BF2 — recommendation acknowledges abast has likely already touched #23's files and explains how the chosen path handles the collision.
- **C24** BF3 — recommendation specifies explicit semantic-review checkpoints (not just textual merge cleanliness).
- **C25** BF4 — recommendation addresses dependency-drop risk in selective pulls (e.g., a "prerequisite-chain audit" step before any cherry-pick).
- **C26** BF5 — recommendation specifies a deliberate-non-pull register or equivalent tracking mechanism for ongoing divergence.
- **C27** BF6 — recommendation distinguishes issue body scope from derived/userprompt boundary scope wherever this matters.

### Honorable-mention paths

- **C28** Path 3b is noted as absorbed into the framing under D3, not presented as a separate option.
- **C29** Path 3c is presented as a contingent fallback with explicit triggering conditions, not as a co-equal option.
- **C30** Path 3d is presented as a tactic available to the chosen path, with concrete coordinate-with-abast actions specified.

### Form

- **C31** Document is written in process-detail form, not duration form.
- **C32** Confidence level on the recommended path is stated explicitly, not implied.
- **C33** Clear handoff: "to start this path in a separate session, do these things in this order" — concrete enough that a fresh agent could pick it up.

---

## 6. Lens-Recommended Path with Rationale

**Through the alignment lens only — Path 1 is preferred, marginally, conditional on PC1.1–PC1.6 being achievable.** The cross-lens disagreement is genuine and must be surfaced in synthesis, not papered over.

### 6.1. Why Path 1 through this lens

The alignment lens evaluates which path most directly satisfies the user's stated success and failure criteria as captured in `userprompt.md` and the Vision Summary. Three considerations are decisive.

**(1) The user's explicit stated failure mode is "unable to merge without losing work on other features."**

This maps directly onto Skeptic's D6 matrix, particularly D6.c (features reverted in conflict resolution) and D6.d (intent lost even if code survives). Skeptic's post-FDR matrix scores Path 2 as worse on D6.d (VH/Critical) primarily because of R8 (the H2 mirror-tree silent-collision risk). Path 2's strongest counter — Composability's "boundary-as-filter" — is a sound argument *for cherry-picks that carry settings semantics*, but Skeptic correctly observes the H2 mirror-tree axis carries no settings semantics for the contract to filter against. The R8 elevation post-FDR is data-driven (FDR §8 H2, ~85 path-mirror pairs, FDR Anomaly 3 type-mismatch), not preference. The lens that maps most directly to the user's stated stake is the lens whose recommendation should win on the alignment dimension.

**(2) Path 1's preconditions are sprustonlab-internal; Path 2's preconditions add external dependencies.**

PC1.1 (cherry-pick scope written first), PC1.3 (semantic-review checkpoint), PC1.4 (`NON_PULLED.md` ledger), PC1.5 (mirror-tree pre-decision), PC1.6 (boundary lint) are all process steps sprustonlab can execute alone. PC1.2 (D8 intent-recovery) is an external dependency, but it is *one* dependency and asymmetrically lighter than Path 2's PC2.3 (abast-side design-time signoff before sprustonlab implements) and PC2.5 (regression-test suite that fails on H2 wrong-path-landing — a non-trivial test infrastructure investment). From the alignment lens: paths whose preconditions sprustonlab can satisfy alone are better-aligned with the user's framing ("we — sprustonlab — making the choice now"), and reduce the gap between "recommended path" and "executable path" per Skeptic's standing rule ("a path with preconditions skipped is more dangerous than the other path with preconditions met").

**(3) Path 1's forced-visibility advantage maps to D7 and the success criterion "user has confidence to start the chosen path in a separate session."**

Composability acknowledges Path 1's "one genuine advantage on this axis" — the mirror-tree parallelism is forcibly visible in the diff under Path 1; under Path 2 it can be silently overlooked unless the team consults the FDR. Composability's mitigation is procedural (consult the FDR); Skeptic disputes this as a reliability bet that should not be credited when a structural pre-decision (PC1.5) is available. The alignment lens sides with Skeptic here for a specific reason: the user's success criterion is stated as confidence to start the path *in a separate session*. A separate session is by definition a context-loss event — procedural mitigations that depend on the team remembering to consult the right document at the right moment are exactly the mitigations most likely to fail across a session boundary. Structural pre-decisions survive context loss; procedural reminders do not.

### 6.2. Why this conclusion is marginal

The disagreement among the four lenses is sharp and the case for Path 2 is substantive. The alignment lens does not dismiss it; the conclusion is "Path 1 by a small margin given the user's stated stake," not "Path 2 is wrong." Specifically:

- **TG's "vocabulary unity" argument has real D6.d substance.** A codebase with three co-resident namespaces (`workflows/` + `workflow_engine/` + `defaults/`) during the #23 implementation window is itself an intent-loss scenario — reviewers reading the post-pull pre-#23 tree will encounter incoherent conventions and may misinterpret what each directory is for. TG quantifies the asymmetry: "abast added 7 new contested terms and re-scoped 3 more, *without* remediating BF1." Path 1 step 1 imports drift; Path 2 step 1 produces a single canonical vocabulary.
- **Composability's "boundary-as-filter" argument is correct on the settings axis.** For settings-semantic cherry-picks (`config.py` 4-line abast change, `fast_mode_settings.json`, the auto-perm fixture), the contract does what Composability claims. The argument fails only on the workflow-tree axis where there is no settings semantic for the boundary to gate against. So Path 2's filter advantage covers most of abast's truly independent footprint (~13–15 files per FDR Anomaly 1) effectively; the failure case is the mirror-tree, not the typical case.
- **FDR §7d's "quiet zone" finding favors Path 2 mildly.** The bulk of the BF1-fix surface (`agent.py`, `errors.py`, `theme.py`, `hints/state.py`, `hints/triggers.py`, `usage.py`, `features/worktree/git.py`) was touched by neither fork. Path 2's #23 step does most of its work in conflict-free territory regardless of path order. Path 1's "do it once with full information" advantage is reduced (though not eliminated — it still applies to the hot files `app.py`, `commands.py`, `config.py`).

Net: Path 1 wins on the user's *stated* North Star (lost-work avoidance, D6.c/d). Path 2 wins on architectural cleanliness end-state and on most of the truly independent footprint. The user must decide which trade dominates. The alignment lens recommends Path 1 because the user's stated stake is the stake the user actually said.

### 6.3. Conditions under which the alignment-lens conclusion would flip

- **If revised Probe E2 reveals abast has no maintainer bandwidth to engage on the workflow-tree convergence question** (PC1.2 / D8 collapses for the purpose of mitigating R5/R8), Path 1's structural advantage on the mirror-tree axis weakens. PC1.5 becomes a unilateral sprustonlab decision made without abast input. Path 2's "boundary-as-filter" + "loud failure on wrong-path-landing" becomes more attractive.
- **If Probe E4 reveals abast has an imminent `/settings` redesign of their own**, pulling abast's not-yet-final design under Path 1 risks landing a parallel design that conflicts with sprustonlab's #23 vision. Path 2's "design our way first, take the compatible bits later" becomes safer, and the alignment-lens conclusion flips to Path 2.
- **If the user clarifies that "lost work" carries weight on architectural cleanliness as well** — i.e., a tree with three co-resident namespaces is itself a form of lost work because intent gets buried in vocabulary fragmentation — the conclusion narrows further toward indeterminate or flips to Path 2.

### 6.4. What the synthesis must do regardless of which path the user chooses

Per the cross-lens disagreement (D7) and the C-criteria, the recommendation document must:

- Surface the cross-lens disagreement verbatim, not paper over it. **Skeptic prefers Path 1; Composability and TG prefer Path 2; UserAlignment prefers Path 1 marginally with explicit acknowledgment of the disagreement.** The synthesis must state this 2:2 split (counting UA's marginal Path-1 lean) and the precise axis on which each lens's argument applies.
- Promote Skeptic's standing rule to headline status: "A path with preconditions skipped is more dangerous than the other path with preconditions met." Whichever path the user chooses, the corresponding preconditions are not optional caveats — they are the path. This is also a C5/C33 satisfaction (concrete handoff, fresh-agent-resumable).
- Surface UQ3 (workflow-tree canonical layout) and UQ4 (`fast_mode_settings.json` treatment) as pre-flight gates regardless of chosen path.
- Add UQ5 if Coordinator agrees: TG's strict-D17 reading collapses the global config tier into per-project; user should confirm this is intended (per-project `analytics.id` is a real behavioural change).
- State an explicit confidence level on the recommended path per C32, including an axis-by-axis breakdown (high confidence on settings-boundary handling regardless of path; medium confidence on workflow-tree resolution conditional on D8 cooperation; lower confidence on Path 2's R8 mitigation absent PC2.5 infrastructure).
- Carry the BF1 four-violation set (TG §3.1) and the boundary-lint specification (Skeptic PC1.6) as a prerequisite zero-step before either path's main work begins. The user's stated independence rule is *already* violated; the recommendation must name fixing this as a non-optional first step in either path.
