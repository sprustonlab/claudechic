# Skeptic Trim Proposals — SPEC.md actionability pass

**Author:** Skeptic2 (review-only; no edits made).
**Source file:** `/groups/spruston/home/moharb/claudechic/.project_team/independent_chic/SPEC.md` (1573 lines).
**Charter:** flag content the implementer does not need ("what to do, period"). Justifications, history, comparisons to rejected alternatives, restatements, navigation noise.

---

## §1 Summary

| Bucket | Count | Estimated lines if cut |
|---|---|---|
| HIGH | 7 | ~13 lines |
| MEDIUM | 22 | ~70 lines |
| LOW | 14 | ~22 lines |
| **TOTAL** | **43** | **~105 lines** |

Estimated post-trim line count: ~**1468** (HIGH only) / ~**1395** (HIGH+MEDIUM) / ~**1373** (all three) — from 1573.

All HIGH items are unambiguous cuts (justification prose or comparisons to prior states). Most MEDIUM items are background framing or repeated-elsewhere clarifications; cutting forces the reader to consult one less paragraph but loses no operational rule. LOW items are aesthetic.

---

## §2 HIGH bucket (clear cuts)

### H1 — §3.3 line 277

> *"(This inverts the current loader behavior at `claudechic/workflow_engine/loader.py:344` from "all duplicates are errors" to "within-tier-only errors".)"*

**Why:** historical residue (comparison to prior loader.py:344 behavior). Implementer does not need to know what the spec used to be.

**Replacement:** `[REMOVE — no replacement needed]`

---

### H2 — §4.1 line 366 partial sentence

Current:
> *"...an idempotent install routine (§4.1) that copies bundled `claudechic/context/*.md` into `~/.claude/rules/claudechic_<name>.md` at every claudechic startup — the Claude Agent SDK auto-loads these via the existing `setting_sources=["user","project","local"]` at `claudechic/app.py:969`; and..."*

**Why:** the em-dash clause ("the Claude Agent SDK auto-loads these via the existing `setting_sources=...`") is justification prose explaining WHY the install location works. Verification belongs to INV-AW-SDK-1 (§13.3.3); the implementer doesn't need the SDK rationale to do the install.

**Replacement:** drop the em-dash clause:
> *"...an idempotent install routine (§4.1) that copies bundled `claudechic/context/*.md` into `~/.claude/rules/claudechic_<name>.md` at every claudechic startup; and..."*

---

### H3 — §4.5 lines 472 (sentences 2–3 of opening paragraph)

Current full paragraph:
> *"The `ContextDocsDrift` trigger and the `context_docs_outdated` hint are DELETED. The install routine is idempotent on every startup with NEW/UPDATE/SKIP/DELETE semantics, so both forward-drift (bundled docs newer than installed) and orphan-drift (installed docs no longer in the bundle) are repaired silently with no user action needed. There is no action to nudge the user toward."*

**Why:** sentences 2–3 are pure justification (WHY DELETE the hint). The actionable rule is sentence 1 + the table beneath. The "no action to nudge the user toward" reads as a defense.

**Replacement:** keep sentence 1 only; the table below already directs the deletion edits:
> *"The `ContextDocsDrift` trigger and the `context_docs_outdated` hint are DELETED."*

---

### H4 — §4.6 line 488 final sentence

> *"The phase exists primarily as a manual trigger (re-install on user demand) since the startup install routine handles the automatic case."*

**Why:** justification prose explaining WHY the phase is preserved despite the new install routine. The actionable rule is the bash invocation that the phase doc invokes (preceding sentence).

**Replacement:** `[REMOVE — no replacement needed]`

---

### H5 — §7.9 line 827

> *"Vision (#24): the workflow button must let the user see and select workflows from all three levels, distinguishing where each came from."*

**Why:** cross-reference to vision document (which §0.1 / §16 marks as not-required-reading) used as motivation. Background framing. The actionable rules are in the rest of §7.9 (registry shape, badges, sort order, "(also at:)" line).

**Replacement:** `[REMOVE — no replacement needed]`

---

### H6 — §9.7 line 1046

> *"The registry's initial state — every currently-existing claudechic write site that touches a `.claude/`-relative path — covers 14 sites: user config save (3 sites: replace + mkdir + tmpfile), legacy config rename (1 site, deleted by Group B), hint state save (3 sites), phase-context write/mkdir/unlink/unlink (4 sites), guardrail hits log (2 sites: mkdir + append), and the worktree symlink (1 site)."*

**Why:** historical inventory of pre-restructure state. The implementer needs the post-restructure target (lines 1048–1056), not the prior 14-site enumeration. Cutting this also removes a source of confusion ("wait, do I need to register 14 entries or 16?").

**Replacement:** delete the sentence; the section's actionable content begins with "After Group B + Group D land, **target post-this-work-state**:".

---

### H7 — §14.2 lines 1399–1402 (Process subsection of UX checklist)

Current:
> *"**Process:***
>
> *- [ ] Two files per spec area (operational SPEC.md + appendix SPEC_APPENDIX.md)*
> *- [ ] Operational sections do not contain rationale paragraphs"*

**Why:** these are spec-authoring obligations, not implementer actions. The implementer cannot tick these checkboxes — they describe the spec itself, which the user has already accepted by reading SPEC.md. Pure scaffolding.

**Replacement:** `[REMOVE — no replacement needed]` (delete the **Process:** heading and both bullets).

---

## §3 MEDIUM bucket (defensible cuts)

### M1 — §0.1 line 20

> *"`SPEC_APPENDIX.md` | Decision history, rationale, rejected alternatives — coordinator-authored. The implementer does NOT need to read this; it exists for future maintainers."*

**Why:** the parenthetical "(The implementer does NOT need to read this; it exists for future maintainers.)" is reassurance prose. The first phrase says enough.

**Replacement:** trim to *"`SPEC_APPENDIX.md` | Decision history, rationale, rejected alternatives. Not required reading for implementation."*

---

### M2 — §0.2 line 33

> *"The mechanism in §4 is **claudechic-awareness install**. Not "rule injection", not "rules pipeline", not "claudechic-awareness injection"."*

**Why:** the rejected aliases are historical (prior names from synthesis passes). Vocabulary checklist §14.3 enforces canonical wording; the implementer just needs the canonical name.

**Replacement:** *"The mechanism in §4 is **claudechic-awareness install**."*

---

### M3 — §0.4 line 61

> *"Code-shaped pseudocode is illustrative. The axis-specs hold the exact signatures."*

**Why:** §0.1 (line 22) and §16 mark axis-specs as reference archives ("Do not consult them during implementation"). This sentence directs the implementer to the very files §0.1 told them to skip — internal contradiction + stale guidance.

**Replacement:** *"Code-shaped pseudocode is illustrative; acceptance bullets and test invariants pin the exact contracts."*

---

### M4 — §1.2 line 107 partial

Current:
> *"...Implementer SHOULD use `sed`/`ruff`/`grep -r` to apply the rewrite and to verify all sites are caught; **an unmatched import surfaces as an `ImportError` at runtime and as a pyright failure at lint time.** Completion is verified by the §1.5 acceptance bullet (zero remaining `from claudechic.workflow_engine` imports across `claudechic/` and `tests/`)."*

**Why:** the bolded clause explains WHAT HAPPENS IF you miss one — justification of the verification step. The acceptance bullet (already in §1.5) is the actionable check.

**Replacement:** drop the em-dash-to-period clause:
> *"...Implementer SHOULD use `sed`/`ruff`/`grep -r` to apply the rewrite and to verify all sites are caught. Completion is verified by the §1.5 acceptance bullet."*

---

### M5 — §3 line 229 first sentence

> *"The 3-tier loader generalizes the existing single-tier `discover_manifests` to walk three filesystem roots and tag every parsed record with its tier of origin."*

**Why:** background framing (WHAT this is rather than WHAT TO DO). The actionable content starts at §3.1. The d55d8c0 prohibition (sentence 2) is operational and stays.

**Replacement:** drop sentence 1; keep sentence 2 only:
> *"Implementer MUST NOT consult `git show d55d8c0` or any partial-extraction approach (the cherry-pick is dropped per §6.1); the new loader is built from scratch."*

---

### M6 — §4.2 line 405 second sentence

Current:
> *"...If `False` and `force=False`, return `InstallResult(...)` immediately. **No file I/O when disabled** — including no DELETE pass. With auto-install disabled, the user owns `~/.claude/rules/` entirely; claudechic does not write, update, or unlink anything there."*

**Why:** "With auto-install disabled, the user owns ... claudechic does not write, update, or unlink anything there" is a restatement of the previous clause ("No file I/O when disabled — including no DELETE pass"). The MUST already says this.

**Replacement:** drop the third sentence:
> *"...If `False` and `force=False`, return `InstallResult(...)` immediately. **No file I/O when disabled** — including no DELETE pass."*

---

### M7 — §4.2 line 413 final clause

Current:
> *"...claudechic owns `claudechic_*.md` regular-file paths; manual user edits to those filenames are clobbered. No warning is emitted for clobbered edits — the contract is documented in `docs/configuration.md` §8.3; users who want manual control disable `awareness.install` AND/OR rename their files outside the `claudechic_*` namespace AND/OR symlink them (the symlink guard preserves user files)."*

**Why:** the "users who want manual control disable... AND/OR rename... AND/OR symlink them" is user-side guidance, repeated in §7.3 helper text and §8.3 step 5. The implementer needs to know "writes are clobbered, no warning." The user-side guidance belongs in `docs/configuration.md`.

**Replacement:** drop everything after the doc cross-ref:
> *"...claudechic owns `claudechic_*.md` regular-file paths; manual user edits to those filenames are clobbered. No warning is emitted; the user-facing contract is documented in `docs/configuration.md` §8.3."*

---

### M8 — §4.3 line 439 partial

Current (from `awareness.install` row Purpose column):
> *"...the SDK continues to load them in every session until the user manually `rm`s them (see helper text in §7.3 + documentation in §8.3). The toggle is "should claudechic write/maintain `~/.claude/rules/claudechic_*.md`" — not "is the agent's awareness disabled.""*

**Why:** philosophical clarification ("the toggle is X — not Y") is restating semantics already conveyed by the preceding sentences. The implementer codes the toggle as a bool gate; the user-facing semantic interpretation belongs to the helper text (§7.3) and docs (§8.3).

**Replacement:** drop the trailing sentence ("The toggle is...").

---

### M9 — §4.4 lines 454–468 (illustrative pseudocode block)

The 15-line `try/except` block prefixed *"Illustrative; Implementer places adjacent to existing CONFIG-driven initialization in on_mount."*

**Why:** the prose at line 452 ("MUST invoke `install_awareness_rules()` once during startup, BEFORE the first agent is spawned. Failure (any exception) MUST be logged at WARNING level and MUST NOT prevent app startup. ... regardless of whether a workflow is active.") fully specifies the behavior. The pseudocode is one of many valid encodings. Acceptance §4.9 enforces the rule.

**Replacement:** delete the code fence; the prose suffices. Saves 15 lines.

---

### M10 — §4.6 line 488 partial

Current:
> *"The phase doc no longer hard-codes the install logic; it invokes `claudechic.awareness_install.install_awareness_rules(force=True)` (e.g., via a Bash invocation `python -c ...`) and reports the result..."*

**Why:** "no longer hard-codes" references prior state (historical residue).

**Replacement:**
> *"The phase doc invokes `claudechic.awareness_install.install_awareness_rules(force=True)` (e.g., via a Bash invocation `python -c ...`) and reports the result..."*

---

### M11 — §4.6 line 490

Current:
> *"The phase doc target dir changes from `<repo>/.claude/rules/` to `~/.claude/rules/` (matches `awareness.install` user-tier config)."*

**Why:** "changes from X to Y" is comparison-to-prior-state framing. The actionable rule is the new target dir.

**Replacement:**
> *"The phase doc target dir is `~/.claude/rules/` (matches `awareness.install` user-tier config)."*

---

### M12 — §4.7 line 502 partial (the PostCompact row)

Current ending:
> *"...The hook does NOT call `assemble_phase_prompt` — `_write_phase_context` is the single producer; the hook is a single consumer; the file on disk is the source of truth. The reassembly logic in `assemble_phase_prompt` is preserved for `_write_phase_context`'s benefit (which produces the file content) but removed from the hook path."*

**Why:** the "single producer / single consumer / source of truth" is justification. The "reassembly logic preserved for `_write_phase_context`'s benefit" is restating §3.7's worker-side row. The actionable rule is "hook does NOT call `assemble_phase_prompt`."

**Replacement:** trim to:
> *"...The hook does NOT call `assemble_phase_prompt`; the file on disk is the source of truth. `assemble_phase_prompt` is retained for `_write_phase_context`'s use only."*

---

### M13 — §5 intro paragraph (line 536)

> *"A workflow run produces agent-authored artifacts (specifications, status, plans, hand-off material) that subsequent agents in the same run must read. This group adds a per-chicsession on-disk location for those artifacts, plus an env var and markdown-placeholder mechanism so spawned sub-agents inherit the path."*

**Why:** background paragraph framing the problem before stating the solution. Sections §5.1–§5.7 specify the actions.

**Replacement:** compress to one operational line, or `[REMOVE — no replacement needed]`. Suggested compression:
> *"This group adds a per-chicsession artifact directory at `<repo>/.claudechic/runs/<chicsession_name>/` plus an env var and markdown-placeholder mechanism for sub-agent inheritance."*

---

### M14 — §5.5 line 569

Current:
> *"**Identity = chicsession name.** The artifact dir name is the chicsession's `name` field verbatim — no timestamp, no run_id, no UUID. ..."*

**Why:** "no timestamp, no run_id, no UUID" enumerates rejected alternatives.

**Replacement:**
> *"**Identity = chicsession name.** The artifact dir name is the chicsession's `name` field verbatim. ..."*

---

### M15 — §10.1 second paragraph (line 1118)

> *"The "no symlinks" prohibition is scoped to the **claudechic-awareness install (Group D)** and does NOT apply to filesystem-state-propagation at the worktree code site. Worktree symlinks are explicitly permitted by §11.4 as `non-destructive-incidental` writes."*

**Why:** anti-confusion explanation referencing a constraint stated elsewhere (§4.2 forbids symlinks in install routine; §11.4 enumerates permitted ones). Restatement.

**Replacement:** `[REMOVE — no replacement needed]`. The §11.4 table is the canonical statement.

---

### M16 — §10.1 third paragraph (line 1120, "Windows portability")

> *"**Windows portability:** the new `.claudechic` symlink, like the existing `.claude` symlink at the same site, requires POSIX symlink support and does not work on Windows. This is a pre-existing limitation of the worktree feature, not a regression introduced here. Cross-platform worktree state propagation is tracked at https://github.com/sprustonlab/claudechic/issues/26."*

**Why:** "not a regression introduced here" is comparison-to-prior-state framing (defense). The implementer doesn't need to know whether this is or isn't a regression.

**Replacement:** trim to:
> *"**Windows portability:** the symlink requires POSIX support; cross-platform worktree state propagation is tracked at https://github.com/sprustonlab/claudechic/issues/26."*

---

### M17 — §10.2 entire (lines 1122–1126)

Two paragraphs describing "Behavioral consequence" of the symlink: project-tier propagation; artifact dir visibility across worktrees; chicsession-state-files asymmetry.

**Why:** describes outcomes rather than actions. Implementer's actions are in §10.3 (the code edit). The asymmetry note about `.chicsessions/<name>.json` is operational only if the implementer is tempted to symlink them — which §10.3 doesn't direct.

**Replacement:** `[REMOVE — no replacement needed]`. Saves ~5 lines.

---

### M18 — §10.3 race-rationale paragraph (line 1136)

Current:
> *"Both the existing `.claude` block AND the new `.claudechic` block MUST use a try/except `FileExistsError` pattern (NOT a check-then-create `if not target.exists()` pattern). The check-then-create form is racy: a concurrent worktree-creation invocation can interleave between the existence check and the `symlink_to` call, causing the second caller to raise an unhandled exception and surface as a misleading "Error" return from `create_worktree` even though the symlink ended up valid. The existing `.claude` block at `git.py:299-301` MUST be migrated to the same pattern as part of this edit."*

**Why:** sentence 2 ("The check-then-create form is racy: ...even though the symlink ended up valid") is justification (WHY the rule). Sentences 1 + 3 are the operational rules.

**Replacement:** drop sentence 2:
> *"Both the existing `.claude` block AND the new `.claudechic` block MUST use a try/except `FileExistsError` pattern (NOT a check-then-create `if not target.exists()` pattern). The existing `.claude` block at `git.py:299-301` MUST be migrated to the same pattern as part of this edit."*

---

### M19 — §11.5 entire (lines 1228–1230)

> *"### 11.5 Group D allowlist contribution*
>
> *Group D adds no other `.claude/` write patterns beyond the §11.1 allowlist row for `~/.claude/rules/claudechic_*.md` (cataloged by the bundled `claudechic/context/*.md` files). The phase-context lifecycle (§4.7) writes only to `<repo>/.claudechic/phase_context.md` (under Group B's `.claudechic/` root), not inside `.claude/`."*

**Why:** restates §11.1 (the allowlist row) and §4.7 (where phase_context.md lives). Pure navigation/reassurance; no new rule.

**Replacement:** `[REMOVE — no replacement needed]`. Delete §11.5 entirely; renumber §11.6 → §11.5 if desired (or leave the gap).

---

### M20 — §12 first paragraph (line 1249)

> *"The mechanism in §4 depends on the Claude Agent SDK loading `~/.claude/rules/*.md` natively when `setting_sources` includes `"user"`. claudechic passes `setting_sources=["user","project","local"]` at `claudechic/app.py:969`. This loading is documented and stable for frontmatter-less files; rules load unconditionally on session start and survive `/compact` natively."*

**Why:** background framing. The implementer doesn't change `setting_sources` (it's already set); doesn't add frontmatter (the install copies bundled files as-is); the verification is INV-AW-SDK-1. The "documented and stable for frontmatter-less files" is reassurance.

**Replacement:** `[REMOVE — no replacement needed]` and let §12.1 (Verification) carry the weight. §12 then becomes "Verify SDK loader" with subsection 12.1 "Verification" describing INV-AW-SDK-1, and 12.2 "Acceptance".

---

### M21 — §13.3.3 lines 1318–1320 (two-paragraph out-of-band justification)

Both paragraphs after the INV-AW-SDK-1 table row:

Para 1 (line 1318): *"INV-AW-SDK-1 is **out-of-band relative to the bundled awareness catalog**: ... never visible to a real install). The boundary CI test does not flag the sentinel write because the test fixture lives at `tests/boundary/test_awareness_sdk_e2e.py` and `tests/` is excluded from the static scan (per §9.1)."*

Para 2 (line 1320): *"The test runs ONLY under the opt-in `live-sdk` pytest marker ... while still ensuring drift is caught within one CI cycle."*

**Why:** para 1 is a defense paragraph (why this won't interfere with orphan cleanup). The actionable rule "test writes the sentinel directly to a tmp-`HOME`'s `~/.claude/rules/` via `Path.write_text`, bypassing the install routine entirely" is already in the INV-AW-SDK-1 table row (clause (b)). Para 2 is partly operational (live-sdk marker, scheduled job) but mostly justification ("avoids gating ordinary merges...").

**Replacement:** compress to:
> *"INV-AW-SDK-1 runs ONLY under the opt-in `live-sdk` pytest marker (`pytest -m live_sdk tests/boundary/test_awareness_sdk_e2e.py`); the default pytest collection skips it. CI MUST run the live-SDK gate on a separate scheduled job (e.g., nightly), not on every PR."*

Saves ~6 lines.

---

### M22 — §16 axis-spec table rows (lines 1565–1569)

Five rows in the §16 reference table all marked "REFERENCE ARCHIVE — content merged into §X":
- `axis_loader_resolution.md`
- `axis_artifact_dirs.md`
- `axis_boundary_test.md`
- `ui_design.md`
- `axis_awareness_delivery.md`

**Why:** §0.1 already says "The four axis-spec files... are reference archives; their operational content is merged into this SPEC. Do not consult them during implementation." Re-listing them in §16 with REFERENCE ARCHIVE labels is redundant + tempts the implementer to look ("oh, these exist? let me check"). Cross-reference cleanup.

**Replacement:** drop the five axis-spec rows. Keep `terminology_glossary.md`, `SPEC_APPENDIX.md`, `vision.md`, `STATUS.md` rows (these are the real reference docs). Saves 5 table rows + clarifies §0.1's statement.

---

## §4 LOW bucket (marginal cuts)

### L1 — §0.1 lines 15–16

> *"This SPEC is self-contained. The implementer does not need to read other files to know what to build. Two files exist as supporting reference:"*

**Why:** meta-commentary about the spec itself. Helpful navigation, but stating it twice (here + in §16) is redundant.

**Replacement:** *"Supporting reference (not required reading):"*

---

### L2 — §0.4 line 59 second sentence

> *"...Pre-restructure paths appear only in §1 and §2 (the restructure spec itself and the migration boundaries)."*

**Why:** spec-organization meta-note. The implementer reading §1 sees pre-restructure paths in context.

**Replacement:** drop the second sentence; keep the first ("Paths use the post-restructure layout throughout").

---

### L3 — §1.2 line 107 closing clause

> *"Completion is verified by the §1.5 acceptance bullet (zero remaining `from claudechic.workflow_engine` imports across `claudechic/` and `tests/`)."*

**Why:** points at the acceptance bullet the implementer reads at §1.5 anyway. Navigation noise.

**Replacement:** `[REMOVE — no replacement needed]`. The §1.5 checklist is a few lines below; the implementer will see it.

---

### L4 — §1.3 line 121 ("MAY land empty-handed")

> *"The detailed rewrites are interleaved with Group C (loader rewrite); Implementer MAY land Group A's path-reference rewrites empty-handed (constants only) and let Group C wire them through `TierRoots`."*

**Why:** sequencing guidance is informational; the MAY clause makes it advisory. Not strictly noise — but if the implementer follows the work-group order in §0.3, they hit Group C before completing the path-reference rewrites anyway.

**Replacement:** `[REMOVE — no replacement needed]`, OR keep as MAY clause. Marginal.

---

### L5 — §4.9 line 526 parenthetical

> *"...`agent_folders.create_post_compact_hook(phase_context_path: Path)` reads from `<repo>/.claudechic/phase_context.md` directly **(no `assemble_phase_prompt` call inside the hook closure; `assemble_phase_prompt` retained for `_write_phase_context`'s use only).**"*

**Why:** the parenthetical reiterates §4.7's PostCompact row. Acceptance bullets should be terse.

**Replacement:** trim to:
> *"...`agent_folders.create_post_compact_hook(phase_context_path: Path)` reads from `<repo>/.claudechic/phase_context.md` directly (no `assemble_phase_prompt` call)."*

---

### L6 — §5.3 line 563 second sentence

> *"...A markdown line like `Write to ${CLAUDECHIC_ARTIFACT_DIR}/spec.md` becomes `Write to /spec.md` — a deliberate, visible failure mode."*

**Why:** "a deliberate, visible failure mode" is justification. The example itself is a useful illustration.

**Replacement:** drop the em-dash clause:
> *"...A markdown line like `Write to ${CLAUDECHIC_ARTIFACT_DIR}/spec.md` becomes `Write to /spec.md`."*

---

### L7 — §5.5 line 573 parenthetical

> *"**Activating a different workflow under the same chicsession name** (a non-typical flow; reachable only by deactivating then re-prompting and entering the same name) MUST reuse the same artifact directory."*

**Why:** the parenthetical describes how to reach the scenario. The MUST stands without it.

**Replacement:** drop the parenthetical:
> *"**Activating a different workflow under the same chicsession name** MUST reuse the same artifact directory."*

---

### L8 — §5.5 line 576 entire

> *"**Two app instances on the same repo + same chicsession name.** Undefined behavior at the chicsession layer; both writers will compete on the same files. The artifact-dir layer inherits this — not in scope to coordinate."*

**Why:** documents an edge case the spec explicitly does NOT address. "Not in scope to coordinate" is meta. Implementer needs no action here.

**Replacement:** `[REMOVE — no replacement needed]`.

---

### L9 — §5.7 line 603 (chicsession definition)

> *"A *chicsession* is the named multi-agent UI snapshot at `<launched_repo>/.chicsessions/<name>.json` storing `name`, `active_agent`, `agents: list[ChicsessionEntry]`, and opaque `workflow_state` (managed by `ChicsessionManager`; distinct from a Claude session and from a workflow run)."*

**Why:** vocabulary-glossary content; `terminology_glossary.md` covers chicsession (§0.1 cross-ref).

**Replacement:** drop the definition; the term has been used since §5 intro without it.

---

### L10 — §7.1 line 667

> *"...The settings button (surface 2), the `/settings` command (surface 3), and the welcome-screen entry (surface 4) all invoke the same `_handle_settings()` method on `ChatApp` — that's the parity contract."*

**Why:** "— that's the parity contract" is meta-commentary. The MUST is implicit in the rest of the section.

**Replacement:** drop the em-dash clause:
> *"...The settings button (surface 2), the `/settings` command (surface 3), and the welcome-screen entry (surface 4) all invoke the same `_handle_settings()` method on `ChatApp`."*

---

### L11 — §7.9 line 842

> *"A row whose workflow has overrides at lower levels shows a secondary "(also at: <levels>)" line so users can see which copies the picker is shadowing."*

**Why:** "so users can see which copies the picker is shadowing" is justification. Also the word "shadowing" is forbidden by §0.2 (in override-resolution prose; debatable here since it's UI prose, but cleaner to avoid).

**Replacement:**
> *"A row whose workflow has overrides at lower levels shows a secondary "(also at: <levels>)" line."*

---

### L12 — §7.10 line 846 first sentence

> *"After cherry-picks `5700ef5` and `7e30a53` land (per §6), the runtime supports `auto`. Three UI sites need updating:"*

**Why:** sequencing context (when this work runs). §0.3 owns the work-group order. The actionable list ("Three UI sites need updating") is the operational content.

**Replacement:**
> *"Three UI sites need updating to support the `auto` permission mode:"*

---

### L13 — §11.4 line 1226 closing

> *"Both symlinks are exempt from §11.4 (predicates: `is_dotclaude_directory_entry` and `is_dotclaudechic_directory_entry`; the symlink path lies at the worktree directory entry, not inside `.claude/`). Windows-portability tracked at https://github.com/sprustonlab/claudechic/issues/26."*

**Why:** the parenthetical "the symlink path lies at the worktree directory entry, not inside `.claude/`" is a justification of WHY the predicates work. The Windows-portability link is the same one in §10.1; mentioning it twice is redundant.

**Replacement:**
> *"Both symlinks are exempt from §11.4 via the predicates `is_dotclaude_directory_entry` / `is_dotclaudechic_directory_entry`."*

---

### L14 — §14.3 multiple bullets

The vocabulary checklist lines 1404–1417 contains items the implementer cannot easily verify (e.g., "No bare 'the boundary' / 'the loader' / 'the engine' / 'the hook' / 'the file' / 'the tier' / 'the symlink' / 'the merge' / 'the namespace'"). These are review-time constraints on doc/UI prose authors.

**Why:** the implementer writing Python code does not encounter these prose constraints. §8 implementer (writing `docs/configuration.md`) does. Splitting the checklist by audience would be cleaner.

**Replacement:** `[KEEP AS-IS]` — marginal. The user can decide whether to scope this checklist to "applicable to §8 author only."

---

## §5 Cross-document considerations

The following cross-references in SPEC.md point at non-operational documents. Each is a candidate cut as a class:

| Reference | Where in SPEC.md | Trim recommendation |
|---|---|---|
| `vision.md` (in §16 reference table; in §7.9 line 827 "Vision (#24):") | Lines 1563, 827 | The §7.9 mention is HIGH (H5). The §16 row is reasonable to keep (the document exists; future maintainers might consult it). |
| `STATUS.md` (in §16 reference table) | Line 1564 | Keep — it's the workflow state-of-record, not implementation reading. Already labeled as such. |
| `SPEC_APPENDIX.md` (in §0.1 line 20; in §16 line 1562) | Two mentions | Keep both, but trim the "implementer does NOT need to read this" reassurance per M1. |
| `terminology_glossary.md` (in §0.1 line 19; in §10.1 line 1116; in §16 line 1561) | Three mentions | Keep all three. Glossary is a lookup tool. |
| Axis-specs (`axis_loader_resolution.md`, `axis_artifact_dirs.md`, `axis_boundary_test.md`, `ui_design.md`, `axis_awareness_delivery.md`) | §16 lines 1565–1569 | All five rows are MEDIUM cuts (M22). §0.1 line 22 already states they're not consulted. Re-listing them invites the implementer to look. |
| `vision.md` §"Files with `workflow_engine` import references" | Was the original §1.2 reference; **already removed** in the Fix-2 pass | No action — confirming the prior fix held. |

**Class verdict:** axis-spec cross-references are the only cross-doc class with a unanimous trim recommendation (M22). Other cross-refs are navigationally useful.

---

## §6 Summary of replacement actions

If the user takes **all HIGH** items (H1–H7): ~13 line cut. The spec gains noticeable concision in §3.3, §4.5, §4.6, §7.9, §9.7, §14.2; one inline trim in §4.1.

If the user takes **all HIGH + MEDIUM** (H1–H7 + M1–M22): ~83 line cut. Major collapses in §10 (M15, M16, M17 together remove ~10 lines), §13.3.3 (M21 collapses two paragraphs), §11.5 (M19 entire subsection), §16 (M22 five rows).

If the user takes **all three buckets**: ~105 lines cut → ~1468 spec lines.

The most impactful cuts (highest noise-removed-per-line) are H6 (§9.7 historical inventory), M9 (§4.4 pseudocode), M17 (§10.2 entire subsection), M19 (§11.5 entire subsection), and M21 (§13.3.3 justification paragraphs).

---

*End of trim proposals.*
