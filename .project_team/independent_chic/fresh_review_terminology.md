# Fresh Review — Terminology Lens

**Reviewer:** TerminologyGuardian (fresh instance — independent cold read at spec-exit)
**Scope:** SPEC.md, SPEC_APPENDIX.md, STATUS.md, terminology_glossary.md, specification/terminology.md, axis_loader_resolution.md, axis_boundary_test.md, ui_design.md
**Mode:** Review-only per L14. No glossary revisions, no new terms.

---

## §1 Lens summary

The spec largely honors the four big terminology constraints — L4 (settings vs config), tier-vs-level surface split, A10 (cross-pollination, not convergence), and the rules-overload disambiguation. The glossary has been revised correctly so §6.4 is now "cross-pollination" canonical with "convergence" retired in §6.4b. However, there are three real cracks: (1) **the awareness-mechanism canonical surface name self-contradicts inside SPEC.md** — §0.2 declares "claudechic-awareness injection" canonical while §7.3/§8.3 prescribe "claudechic-awareness rules" in user-facing label and docs section title, and §8.6 explicitly forbids "rules" for awareness content while §8.3 mandates exactly that section title; (2) **A10-retired words leak into spec-phase prose** in SPEC_APPENDIX.md (twice) and ui_design.md (once); (3) **a stale cross-reference** in specification/user_alignment.md still describes the glossary as having "convergence" canonical, which it no longer does. None of these block implementation, but #1, #2 (a typo), and the A10 leaks should land before signoff.

---

## §2 Findings

### F1 [BLOCKER] Canonical surface name for the awareness mechanism self-contradicts

**Location:** SPEC.md §0.2 (line 41), §7.2 (line 645), §7.3 (line 665), §8.3 (lines 714, 716), §8.6 (line 739).

**Offending text (assembled):**
- §0.2 line 41: *"The mechanism in §5 is **claudechic-awareness injection** (canonical wording per R6-UX). Not 'rule injection', not 'rules pipeline'."*
- §7.2 line 645: *"The mechanism in §4 is referenced in user-facing prose as **'claudechic-awareness injection'** (canonical wording per R6-UX)."*
- §7.3 line 665: *"User-facing label for `awareness.install`: **'Install claudechic-awareness rules'** (TerminologyGuardian owns final wording). Helper text: 'Auto-install claudechic-awareness rules into `~/.claude/rules/`...'"*
- §8.3 line 714: *"### 8.3 Required additional section: claudechic-awareness rules install"*
- §8.3 line 716: *"A section titled **'claudechic-awareness rules'** covering:"*
- §8.6 line 739: *"MUST NOT use the word 'rules' to describe the awareness-injection content (per R6-UX wording)."*

**Severity rationale:** §8.6 forbids the very word the §8.3 section title is required to use. §0.2/§7.2 declare the mechanism's canonical user-facing surface name to be "claudechic-awareness **injection**" while §7.3 prescribes the actual user-facing label "Install claudechic-awareness **rules**". Implementer reading SPEC.md cold has no single ground-truth string to put in code. §7.3 itself explicitly defers to TerminologyGuardian to resolve this ("(TerminologyGuardian owns final wording)").

**Resolution path (Composability owns the call):** post-A13 / RESEARCH.md Option B, the mechanism is **not an injection** — it is an idempotent file install plus SDK-native auto-load. The canonical R6-UX wording "claudechic-awareness injection" predates A13 and is now operationally inaccurate. Either:
- (a) update §0.2 + §7.2 to retire "injection" and adopt "claudechic-awareness install" or "claudechic-awareness rules" as canonical; OR
- (b) keep "injection" canonical and rewrite §7.3/§8.3/§8.6 + the user-facing label to match.
- Recommend (a). The user's words at A13 ("I want to copy as default and the settings have a way to desable that") are install-shaped, not injection-shaped.

### F2 [BLOCKER] Wrong section reference in §0.2

**Location:** SPEC.md line 41.

**Offending text:** *"The mechanism in **§5** is **claudechic-awareness injection** (canonical wording per R6-UX)."*

**Canonical text:** Group D / agent awareness lives in **§4**, not §5. §5 is "Group E — Workflow artifact directories". Cross-reference §7.2 line 645 ("The mechanism in §4 is referenced in user-facing prose as...") which has the correct §4.

**Severity rationale:** broken cross-reference in the document conventions section a newcomer reads first. Trivial fix (s/§5/§4/) but it must land.

### F3 [HIGH] A10 violation — "convergent" in SPEC_APPENDIX.md prose

**Location:** SPEC_APPENDIX.md line 262.

**Offending text:** *"The 3-tier layout is the **convergent** target; cherry-picks against the old layout introduce conflicts that the restructure would erase anyway."*

**Canonical replacement:** *"The 3-tier layout is the **agreed-upon** target..."* or *"...the **target** layout..."*

**Severity rationale:** A10 / SPEC.md §14.3 / terminology contract §2.3 retire "converge / convergence" in spec/docs/UI prose. SPEC_APPENDIX.md is a spec-phase deliverable. "Convergent" is a form of "converge" and falls under the retirement.

### F4 [HIGH] A10 violation — "convergence" in SPEC_APPENDIX.md prose

**Location:** SPEC_APPENDIX.md line 351.

**Offending text:** *"Three lenses interpreted 'mirror' three different ways before **convergence**:"*

**Canonical replacement:** *"Three lenses interpreted 'mirror' three different ways before **agreement**:"* or *"...before **arriving at consensus**:"*

**Severity rationale:** Same A10 retirement. Note: this passage is about the lens-process arriving at agreement, not about abast cross-fork convergence — but A10's retirement list (per terminology contract §2.3 / glossary §6.4b) is unscoped. The word is forbidden in spec prose regardless of subject.

### F5 [HIGH] A10 violation — "converge" in ui_design.md heading

**Location:** ui_design.md line 775.

**Offending text:** *"### 9.1. Entry points (three; all **converge**)"*

**Canonical replacement:** *"### 9.1. Entry points (three; all route to `_handle_settings()`)"* or *"### 9.1. Entry points (three; all open the settings screen)"*

**Severity rationale:** Same A10 retirement. ui_design.md is a spec-phase deliverable. A document section heading is in-scope for the retirement.

### F6 [MED] Stale cross-reference to pre-revision glossary state

**Location:** specification/user_alignment.md lines 106, 114.

**Offending text:**
- line 106: *"Drift in lens reports: `terminology_glossary.md` §6.4 declares 'convergence' as a **canonical** term and gives it a definition. This contradicts A10."*
- line 114: *"`? USER ALIGNMENT: terminology_glossary §6.4 lists 'convergence' as canonical. User's Q7 answer ('trim we cross polinate') explicitly retired that framing. Spec must use 'cross-pollination' / 'selective integration' instead. Glossary entry should be revised or marked superseded.`"*

**Canonical text:** the glossary §6.4 has been revised — "cross-pollination" is now canonical (line 360), and §6.4b (line 387) holds the retirement record for "convergence / merge program". user_alignment.md should be updated to either delete this drift flag or mark it as resolved.

**Severity rationale:** factual error in a spec-phase operational deliverable. A reader following user_alignment.md's pointer would find the glossary in the opposite state from what the spec describes.

### F7 [MED] User-facing settings-label uses bare "rules" without qualifier

**Location:** SPEC.md §7.3 line 665.

**Offending text:** *"User-facing label for `awareness.install`: **'Install claudechic-awareness rules'** ... Helper text: *'Auto-install claudechic-awareness rules into `~/.claude/rules/` so Claude understands its environment. Disable to manage manually.'*"*

**Canonical text:** Per terminology contract §2.1 + §3 (overloaded terms — "rules" senses are Claude rules / guardrail rules / rule-equivalent), the unqualified "claudechic-awareness rules" introduces a fourth implicit sense ("rules claudechic installs into Claude's rules dir"). Post-A13 these *are* Claude rules from the SDK's perspective, so a faithful label could be **"Install claudechic context as Claude rules"** or **"Install claudechic-awareness as Claude rules"**. Helper text: **"Auto-install claudechic context docs into Claude's `~/.claude/rules/` directory..."**

**Severity rationale:** the label is the user's first encounter with the mechanism. Using bare "rules" without specifying *whose* rules conflates this with guardrail rules (which the same settings UI exposes via `disabled_ids`). The §7.3 line itself notes "(TerminologyGuardian owns final wording)" — this lens flags it. Also relates to F1.

### F8 [MED] Section heading uses bare "rules" without qualifier on first mention

**Location:** SPEC.md §4 heading, line 340.

**Offending text:** *"## 4. Group D — Agent awareness via SDK-native rules + phase-context refresh"*

**Canonical text:** *"## 4. Group D — Agent awareness via SDK-loaded Claude rules + phase-context refresh"*

**Severity rationale:** terminology contract §2.1 requires "rules" be qualified on first mention per section. "SDK-native rules" is partly qualified (it implies Claude rules) but a fresh reader could read it as "rules native to claudechic's SDK usage". Adding "Claude" makes the qualifier explicit and matches §0.2's vocabulary list (line 35).

### F9 [MED] "Awareness install" / "awareness rules install" / "install routine" — multiple surface forms

**Location:** SPEC.md throughout §4 and §8.3.

**Surface forms in current spec:**
- "awareness install" (e.g., line 439, 443 — log message text; line 470 — section subheading)
- "the install routine" (frequent — e.g., lines 358, 388, 391, 416, 488, 718)
- "claudechic-awareness rules install" (line 714 — §8.3 heading)
- "Install claudechic-awareness rules" (line 665 — settings label)
- module name `awareness_install.py` and function `install_awareness_rules()`

**Canonical recommendation:** pick one **prose form** and use everywhere. Code symbols (`awareness_install`, `install_awareness_rules`) are fine to retain — L4 doesn't force renames. Suggested prose form: **"awareness-install routine"** (matches the module name; reads cleanly; sidesteps F1's injection-vs-rules ambiguity).

**Severity rationale:** four near-synonyms for the same mechanism create reader friction. Per the user's instruction ("verify the spec picks one canonical form and uses it consistently"), this is a real coherence issue, though not blocking.

### F10 [MED] "tier" appears in proposed user-facing docs section headings

**Location:** SPEC.md §8 / ui_design.md §7.2.2 + §7.2.3.

**Offending text:**
- ui_design.md line 681: *"#### 7.2.2. User-tier config keys"* (proposed section heading for `docs/configuration.md`)
- ui_design.md line 701: *"#### 7.2.3. Project-tier config keys"*

**Severity rationale:** SPEC.md §8.6 line 740 says: *"User-facing text uses 'level' (not 'tier') when describing the 3-level distinction."* The 2-tier config model is technically distinct from the 3-tier content model, so a strict reading allows "tier" here. But docs/configuration.md is the user-facing reference page; mixing "tier" (in §7.2.2/§7.2.3 headings) with "level" (in the 3-tier content model elsewhere) inside the same doc is inconsistent. Recommend rephrasing to **"User-level config keys"** / **"Project-level config keys"** or simply **"User config keys"** / **"Project config keys"**.

### F11 [LOW] Hyphenation drift on "primary-state" vs "primary state"

**Location:** SPEC.md §14.2 line 1069 vs glossary canonical form.

**Offending text:** *"Boundary uses 'primary-state writes' vs 'non-destructive incidental touches'"*

**Canonical text per terminology contract §1 lines 39-40:** "primary state" (no hyphen) and "non-destructive incidental touch" (no hyphens between non/destructive/incidental, hyphen between non-destructive). The hyphenated forms ("primary-state", "non-destructive-incidental") appear in axis_boundary_test.md as YAML enum string values — that's code-shape, OK to retain. But spec prose should use the unhyphenated glossary form.

**Severity rationale:** cosmetic drift; readability is fine; reconcile if a quick pass is happening anyway. Glossary doesn't pin hyphenation strictly, so this is more taste than violation.

### F12 [LOW / INFO] Newcomer-simulation blockers — terms used without inline definition on first mention

A cold reader of SPEC.md alone would have to grep elsewhere to understand:

- **"chicsession"** — used in §5 (artifact dirs), §10 (worktree), §16. Terminology contract §4.1 requires inline definition on first mention. SPEC.md §14.3 line 1098 acknowledges this checklist item but the spec body never executes it.
- **"rule-equivalent"** — used in §0.3 line 57 (A4 row) without inline anchor.
- **"fallback discovery"** — used in §6.1 line 598 (cherry-pick A8 row) without inline anchor.
- **"main worktree" / "main_wt"** — used in §10.3 lines 838, 845 without inline definition; relies on reader knowing git-worktree mechanics.
- **"PostCompact hook"** — used in §3.2 line 275 and §4.8 line 480 capitalized as a term without grounding.
- **"TierRoots"** — used in SPEC.md §3 throughout; defined in axis_loader_resolution.md §2.2, not in SPEC.md.

**Severity rationale:** terminology contract §4.1 prescribes inline definition. SPEC.md treats axis-spec cross-references as "operational and binding" (line 7), so a newcomer can follow the pointer — but the §14.3 checklist self-claim ("**chicsession** defined inline on first mention") is not satisfied.

### F13 [INFO] Workflow-button vs workflow-picker — code/spec uses "picker", user-facing should say "button"

**Status:** correctly handled at the boundary between code and UI.

- Code symbols use "workflow picker" (`WorkflowPickerScreen`, `screens/workflow_picker.py`, `ui_design.md` §5 heading) — OK per L4.
- The user's word per #24 is "workflow button" — preserved in vision.md and SPEC.md §14.2 checklist line 1073.
- ui_design.md §5.1 line 459 quotes the vision verbatim ("a 'workflow button' surface"). Good.

**Risk:** ui_design.md mock-UIs do not show the actual on-screen button label, so the implementer could land "workflow picker" in user-facing text by inertia from the code symbols. The §14.2 checklist line 1073 will catch it at exit, but flagging here for awareness.

### F14 [INFO] Vision/STATUS terminology — vision.md retains "convergence" / "converge"; STATUS.md retains "convergence" only inside A10's retirement record

**Vision.md:** lines 96, 141, 176, 188 use "convergence" / "converge" / "converged" / "convergent". Per A10's instruction to preserve vision.md verbatim (STATUS.md A10: *"The vision document text itself is not rewritten (it's the prior team's hand-off artifact)"*), these are in-scope-allowed. Not a finding; flagged here per A1 transparency.

**STATUS.md:** "convergence" appears at lines 176, 178, 182 — all inside A10's retirement record itself (the canonical home for the retirement). Glossary §6.4b explicitly permits the term inside retirement records. Not a finding.

---

## §3 Blockers vs nice-to-haves

### Blockers (resolve before spec signoff)
- **F1** — canonical wording self-contradiction across §0.2 / §7.2 / §7.3 / §8.3 / §8.6.
- **F2** — §5 vs §4 cross-reference typo in §0.2 line 41.
- **F3, F4, F5** — three A10-violating words ("convergent", "convergence", "converge") in spec-phase prose.

### Nice-to-haves (can ride into implementation; resolve when convenient)
- **F6** — stale cross-reference in user_alignment.md to pre-revision glossary state.
- **F7** — user-facing settings label uses bare "rules" (related to F1).
- **F8** — §4 heading qualifies "rules" only loosely as "SDK-native".
- **F9** — multiple surface forms for the awareness-install mechanism.
- **F10** — "User-tier config keys" / "Project-tier config keys" headings in docs/configuration.md user-facing prose.
- **F11** — hyphenation drift on "primary-state" / "primary state".
- **F12** — newcomer-simulation: several terms used without inline definition despite §14.3 self-claim.
- **F13** — workflow-button-vs-picker risk at the implementation boundary.

---

## §4 Verdict

**READY WITH FIXES.**

The spec's vocabulary contract is sound and the glossary revision (cross-pollination canonical) is properly threaded through the spec body, the terminology contract, and the exit checklists. The three A10 word-leaks (F3, F4, F5) and the awareness-mechanism canonical-name self-contradiction (F1, F2) are real but cosmetically scoped — they can be resolved with a focused pass that touches the named lines, not a structural revision.

**Top vocabulary risks for the run:**

1. **F1 — awareness-mechanism canonical surface name** is the highest-impact issue. The spec hands the implementer two contradictory strings ("Install claudechic-awareness rules" vs "claudechic-awareness injection") for the same user-facing surface. Pick one. Post-A13 reality favors the rules / install framing; the "injection" canonical from R6-UX is operationally stale.
2. **F3-F5 — A10 leakage** through "convergent" / "convergence" / "converge" in spec-phase prose. These are exactly the words the §14.3 zero-occurrences checklist is supposed to catch. A grep pre-merge will find them in 30 seconds.

---

*End of fresh_review_terminology.md.*
