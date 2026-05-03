# Fresh Review — UserAlignment Lens

**Lens:** UserAlignment (independent cold review)
**Phase:** Specification exit checkpoint
**Inputs read in order:** `userprompt.md`, `STATUS.md`, `vision.md`, `SPEC_APPENDIX.md`, `SPEC.md`, `RESEARCH.md` (selected sections), GitHub issues #23 / #24 / #26, prior `alignment_audit.md` for comparison only.
**Author note:** This lens has no inherited context from the prior UserAlignment instance; the only ground truth used here is the user's verbatim words plus the vision the user adopted.

---

## §1 Lens summary

The spec is **substantially aligned** with the user's verbatim words and with both GitHub issues. The most user-determined decisions (A4 boundary scoping, A13 SDK-native rules install, A6 auto default, the worktree symlink reversal, "no tiers for the install", the awareness toggle) are encoded in SPEC.md with anchors traceable to exact user phrases. Minor issues are: (a) one user spec-exit utterance ("I will live with that now, if I disable, it is on me") is **not captured in `userprompt.md`** even though its operational consequence — drift hint stays deleted — is encoded; (b) two short rationale leaks in SPEC.md technically violate L14 but are bounded and point to the appendix; (c) A7's expansion from a single user word ("primary") to a multi-row permitted/forbidden table is the largest STRETCH in the run and is worth surfacing once more before signoff. None of these block the spec.

---

## §2 Amendment-by-amendment audit (A1–A13)

| ID | User-words anchor | SPEC encoding location | Alignment | Commentary |
|----|-------------------|------------------------|-----------|------------|
| A1 | "yes, agents can check and surface issues if they find them. we all make mistakes." (Vision Q1) | SPEC.md §16.1 (seven flags); SPEC_APPENDIX.md §6 | **FAITHFUL** | Operationalized exactly. Lens reports each have vision-flag sections; consolidated in §16.1. |
| A2 | "adopt" (Vision Q3) | SPEC.md §6.1 | **FAITHFUL** | Three deferred cherry-picks pulled. The cherry-pick table matches Q3 + A8 revision. |
| A3 | "for #4 it needs to mirror the .claude/rule behavior" (Vision Q4) | Superseded by A13; rationale chain at SPEC_APPENDIX.md §1.2 + §4.4 | **FAITHFUL** | A3 was the intent; A13 is the mechanism that delivers the intent more faithfully than the original synthesis (which the user's spec-exit research instruction caught). |
| A4 | "it needs to behave the same, we can touch .claude in ways we are sure are not destructive, overwriteing a sesttings file is out. adding a symlink is out as it is not supported on windows." (Leadership Q1') | SPEC.md §0.3 row A4, §11.1, §11.3, §11.4; spec-exit follow-up scopes symlink rule to Group D only | **FAITHFUL** | The four-clause user instruction is encoded clause-for-clause. The spec-exit "add symlink to .claudechic" instruction correctly **scoped** (not removed) the symlink prohibition. |
| A5 | "config in 2 is what I want. everyhting is the other things." (Leadership Q2') | SPEC.md §0.3 row L8, §3, §4.4, §7.3 | **FAITHFUL** | 2-tier config preserved. The user's parenthetical "everything is the other things" is correctly translated as: 3-tier applies to the four content categories only, not to config. |
| A6 | "yes." (Leadership Q3') | SPEC.md §6.1 (5700ef5 + 7e30a53 pulled), §6.2 acceptance, §7.3 default_permission_mode key | **FAITHFUL** | Auto becomes startup default; Shift+Tab cycle includes auto. |
| A7 | "primary." (single word, Leadership Q4') | SPEC.md §0.3 row A7, §11 boundary allowlist (full table) | **STRETCH** | Largest interpretive leap in the run. One-word user answer expanded into a multi-row permitted/forbidden classification with predicates. The expansion is defensible (the team needed an operational form) and the user later approved Option B which depends on this softening, but the spec's structural elaboration goes well beyond what "primary" literally says. Worth one-sentence user reaffirmation before signoff: *"A7's spec encoding has predicates `is_claudechic_prefixed_rules_file`, `is_dotclaudechic_directory_entry`, and a permitted/forbidden table. Approve as the operational form of 'primary'?"* |
| A8 | "you can drop it." (Leadership Q5') | SPEC.md §6.1 (d55d8c0 marked SKIP), §3.1 framing as "small generalization" | **FAITHFUL** | Direct user assent; spec encoding clean. |
| A9 | "yes, we know what we are doing." (Leadership Q6') | SPEC.md §2 preamble, §2.6 acceptance, §4.3 "no warning is emitted for clobbered edits" | **FAITHFUL** | Silent loss accepted as tradeoff. Skeptic's failure-mode finding correctly reclassified. |
| A10 | "trim we cross polinate not just pull from one." (Leadership Q7') | SPEC.md §0.2 vocabulary, §8.6 wording obligations, §14.3 terminology checklist | **FAITHFUL** | The terminology contract is enforced verbatim through the checklist. |
| A11 | "two." (single word, Leadership Q8') | SPEC.md §0.3 row L15; §4.1 two-piece table | **STRETCH** (mild) | The single word is faithful to L15's two-piece intent; under A13's SDK-native install the lazy "first-read" trigger becomes eager (SDK loads at session start), which §4.1 explicitly notes as a user-approved trade-off ("the eager guarantee is stronger than the lazy trigger" — RESEARCH.md §3 Option B). Operationally fine; just worth noting that strict L15 said "once per agent on first read inside `.claudechic/`" and the eager-load doesn't condition on a `.claudechic/` read at all. The user's Option B approval covers this. |
| A12 | "let the team decide. fine to pospond if too much." (Leadership Q9') | SPEC.md §7.1 (all four IN SCOPE; zero postponed) | **FAITHFUL** | User explicitly delegated; UIDesigner exercised the delegation. The opposite call (postpone all four) would have been equally faithful. |
| A13 | "approve option B, fine with all answers. I want to copy as default and the settings have a way to desable that. there are no tiers here right? does claude reads from ~/.claude/rules?" (spec-exit) | SPEC.md §4 (Group D entirely rewritten), §11.1, §11.5; SPEC_APPENDIX.md §4.4 | **FAITHFUL** | Every clause is encoded: "copy as default" → install routine on every startup; "settings have a way to disable that" → `awareness.install` toggle; "no tiers here right?" → §4.4 + SPEC_APPENDIX.md §4.4 explicitly state install is flat (no claudechic tiers); "does claude reads from ~/.claude/rules?" → answered yes in §4 + §12.2 + research. Excellent encoding. |

**Summary counts (A1–A13):** FAITHFUL 11; STRETCH 2; DRIFT 0; VIOLATED 0.

---

## §3 Late-spec-exit instructions audit

Per the dispatch's enumeration. SPEC_APPENDIX.md §1.8 captures items 1–4 of the spec-exit user instructions; userprompt.md does **not** include any of these (its "Leadership-phase user resolution round" ends at Q9). This is a userprompt.md completeness gap, not a spec gap, but flagged as a process finding.

| Spec-exit instruction (verbatim) | Spec encoding | Status | Commentary |
|----------------------------------|---------------|--------|------------|
| "add symlink to .claudechic and make an issue in the repo about worktrees and windows." | SPEC.md §10 (symlink restored at `git.py:293-301`); SPEC.md §11.4 (A4 scoped to Group D only); SPEC.md §16.1 banner; GitHub issue #26 created and referenced from SPEC.md §10.1, §11.4, SPEC_APPENDIX.md §1.6 / §1.8 / §6.1 | **FAITHFUL** | All three sub-instructions executed: symlink added, issue created, A4 scoped down. Issue #26 verified to exist on GitHub and to reference SPEC.md §10. |
| "please give me more detail please." | Conversational; no spec change required | **N/A** | Triggered the SDK-mechanism explanation that revealed the rules-format gap (next item). |
| "No, please read how .cluade/rules work as YAML file with a header and dir spec." | RESEARCH.md spawned; RESEARCH.md §2 maps the actual `.claude/rules/` format; finding drives A13. SPEC.md §4 + §12.2 reference RESEARCH.md as authoritative source. | **FAITHFUL** | Research happened; finding documented; A13 redesign is the response. The user's "YAML file with a header and dir spec" specifically calls out frontmatter; SPEC.md §12.2 explicitly notes the install ships frontmatter-less files which is the correct minimal mirror. |
| "approve option B, fine with all answers. I want to copy as default and the settings have a way to desable that. there are no tiers here right? does claude reads from ~/.claude/rules?" | A13 in STATUS.md; SPEC.md §4 entirely rewritten; §4.4 toggle; §4.10 boundary classification; SPEC_APPENDIX.md §4.4 | **FAITHFUL** | Best-encoded user instruction in the run. Both questions explicitly answered (in SPEC_APPENDIX.md §1.8 last paragraph). |
| "I will live with that now, if I disable, it is on me." | SPEC.md §4.6 (drift hint stays DELETED); SPEC_APPENDIX.md §4.4 (deletion preserved) | **FAITHFUL operationally; UNCAPTURED in userprompt.md** | The user's words are not in `userprompt.md`. SPEC §4.6 says "per coordinator correction" rather than quoting the user. Behaviorally the spec encodes the user's choice; documentationally the trail is incomplete. **Recommend** adding the verbatim quote to `userprompt.md` §"Spec-exit instructions" so the audit chain is complete. |

**Summary counts (spec-exit):** FAITHFUL 4; N/A 1; trail-incomplete 1.

---

## §4 Drift findings

### §4.1 Scope creep (things in spec the user didn't ask for)

| Item | Severity | Anchor / commentary |
|------|----------|---------------------|
| Group H — Boundary CI test (`tests/boundary/...`, hybrid AST + runtime, two YAML configs, six failure templates) | LOW | The user did not ask for a CI test. However, vision §"Success looks like" ("the boundary holds in CI — an automated test catches any new violation") was adopted via the user's "approved" of the vision document. That vision-level approval pulls Group H into scope legitimately. No drift. |
| Heavy axis-spec apparatus (4 axis-specs + 4 axis-appendices + UI-design + UI-appendix on top of SPEC.md + SPEC_APPENDIX.md) | LOW | The user said "B" to the full Specification team shape (SPEC_APPENDIX.md §1.7). This delegated authority over team size; the multi-spec output is faithful to the user's "B" choice. Worth noting that 96kb SPEC.md + 55kb appendix + multiple axis-specs may exceed an Implementer's actual reading bandwidth — but that is a process concern, not a user-alignment concern. |
| `awareness.install` settings entry copy: "Auto-install claudechic-awareness rules into `~/.claude/rules/`..." | LOW | User said "I want to copy as default and the settings have a way to desable that." UI label "Install claudechic-awareness rules" is faithful. Helper text adds detail beyond user's words but is descriptive of the user-approved behavior, not a new feature. |

### §4.2 Scope cuts (things user wanted that spec doesn't deliver)

| Item | Severity | Anchor / commentary |
|------|----------|---------------------|
| L15 strict "once per agent, on first read inside `.claudechic/`" semantics | LOW | A11 reaffirmed two-piece, but A13's eager-load delivery does not condition on a `.claudechic/` read. SPEC.md §4.1 acknowledges this as a deliberate user-approved trade-off (Option B). Behavioral effect: agents see the fuller context **earlier** than strict L15 would dictate — strictly more, not less. The user explicitly approved this trade-off. No remediation needed; flagging because the strict L15 wording in vision.md still reads as if first-read-conditional, and a future reader of the vision alone might be confused. **Recommend** a one-line note in the vision (or in STATUS.md A11) saying L15 piece-2 timing is satisfied eagerly under A13. |
| Drift-detection observability for releases | NIL | The user's "I will live with that now, if I disable, it is on me" explicitly accepts the loss of drift detection. SPEC_APPENDIX.md §9 reversal-trigger note covers when to revisit. |
| `analytics.id` and `experimental.*` UI surfacing | NIL | Issue #23 explicitly says "No (internal)" for `analytics.id` and `experimental`. SPEC.md §7.3 keeps both hidden but documented in `docs/configuration.md`. Faithful. |

### §4.3 Wording-change checks (spec replacing user phrases with different terms)

| User word | Spec word | Status |
|-----------|-----------|--------|
| "prompt injection" (#24) | "claudechic-awareness injection" (canonical per R6-UX) | OK — qualifier is required because "injection" alone is overloaded; canonical form preserves user intent. |
| "settings button in the bottom" (#24) | "footer Settings button" / `SettingsLabel` | OK — same surface; "footer" and "bottom" are synonymous in TUI vocabulary. |
| "workflow button can show all 3" (#24) | "workflow-picker tier badges" / "workflow row with `(defined at: <levels>)`" | OK — the spec delivers the user's intent (visible distinction across all 3 levels). The user's "show all 3" is encoded as tier badges per row, not a separate "all 3" view; this is a defensible interpretation of the user's words. |
| "rules and hints" (#24, paired) | "global/{rules,hints}.yaml" two siblings | OK — vision §1's "single dir or two siblings is mechanism choice" + L7's lock at two siblings is internally inconsistent (SPEC.md §16.1 #2 records this); SPEC follows the lock. The user's pairing intent is preserved (still grouped under `global/`). |

---

## §5 Blockers vs nice-to-haves

### Blockers (must address before READY)

**None.** The spec is operationally executable as written.

### Nice-to-haves (should address but not gating)

1. **Capture the spec-exit user words in `userprompt.md`.** The five spec-exit user utterances appear in SPEC_APPENDIX.md §1.8 but not in `userprompt.md`. Future audits cannot cleanly trace amendments to `userprompt.md` alone. Specifically missing: "add symlink to .claudechic...", "please give me more detail please.", "No, please read how .cluade/rules work as YAML file with a header and dir spec.", "is there anything we can use from the internet about how cluade code does this so we don't have to reimpliment everything? please spwqn a researched for that...", "approve option B, fine with all answers...", "I will live with that now, if I disable, it is on me." Add a §"Spec-exit instructions" section with verbatim quotes.

2. **A7 reaffirmation prompt.** Single word "primary" → structured permitted/forbidden table is a STRETCH. Worth a one-sentence reaffirmation: *"A7's spec form is a permitted/forbidden table with predicates. Approve as the operational interpretation of 'primary'?"* If user says yes, lock; if no, the spec needs adjustment.

3. **Two minor L14 rationale leaks in SPEC.md.** Lines 488 ("Rationale (one line): the SDK already does this work for free..."), 492 ("...because (a) files are claudechic-owned..."), and 921 ("Both symlinks are exempt from §11.4 because..."). Each is short and points to the appendix; not a serious violation, but L14 grading is binary. Either trim to bare statements ("See SPEC_APPENDIX.md §4.4") or accept the L14-MINOR.

4. **STATUS.md A4 paragraph order.** STATUS.md A4 entry now interleaves the original Q1' bullet list with a parenthetical spec-exit reversal mid-list. Readable but cluttered. Cosmetic only.

5. **Vision file text is not rewritten despite A10.** A10 retires "convergence" language in spec/docs/UI prose, but vision.md §7 still uses "convergence" twice ("Coordinate with abast on convergence"). STATUS.md A10 explicitly says "the vision document text itself is not rewritten (it's the prior team's hand-off artifact)" — this is a deliberate decision, not drift. Worth confirming once more that the user is OK with vision.md retaining the retired wording. Probably fine; flagging for completeness.

---

## §6 Verdict

**READY WITH FIXES (cosmetic).**

The spec is alignment-ready. None of the findings above block implementation. The two STRETCHes (A7 and A11) were both approved downstream by user instructions that depended on the team's interpretation (A7 underpins A4's Option B which the user approved; A11's eager-load is part of the Option B approval). The trail to the user's words is solid for every binding decision in the spec.

**Recommended pre-signoff steps (non-blocking):**

1. Capture the spec-exit user utterances verbatim in `userprompt.md` (§5 nice-to-have #1).
2. One-sentence user reaffirmation of A7's structured form (§5 nice-to-have #2).
3. Decide on the L14-MINOR rationale leaks at SPEC.md lines 488 / 492 / 921 (§5 nice-to-have #3) — trim or accept.

If those three are handled, the spec is fully READY for implementation.

---

*End of fresh_review_useralignment.md.*
