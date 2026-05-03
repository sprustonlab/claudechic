# Fresh Review — Composability lens

**Reviewer:** Composability (fresh instance; no inherited context from prior runs)
**Scope:** architectural-coherence review of the final operational spec at `SPEC.md` (post-A13).
**Mode:** review-only per L14. No operational MUSTs from this lens; recommendations only.
**Inputs read in full:** `SPEC.md`, `SPEC_APPENDIX.md`, `STATUS.md`, `RESEARCH.md`, `axis_loader_resolution.md`, `axis_artifact_dirs.md`, `axis_boundary_test.md`, `axis_awareness_delivery.md` (banner only). Source verifications against `claudechic/app.py`, `claudechic/features/worktree/git.py`, `claudechic/workflow_engine/agent_folders.py`, `claudechic/context/`.

---

## §1 Lens summary

The eight-group decomposition is sound and the cross-axis seams are mostly clean. The A13 separation of awareness install (static, eager, SDK-loaded) from phase-context delivery (dynamic, mid-session, engine-authored) is the right call — they have genuinely different lifecycles and the SPEC keeps the seam minimal. The major architectural questions — three tiers for content, two for config, partial-override fall-through, boundary primary-state-only — are coherently answered. However, two substantive contradictions and one literal-vs-effective semantic gap need fixing before implementation, plus several smaller cleanups. Verdict: **READY WITH FIXES**.

---

## §2 Findings

### F1 — [HIGH] PostCompact-hook source contradiction between §4.8 and `axis_loader_resolution.md` §8.3

**Where:** SPEC §4.8 row "`/compact` re-injection" + INV-AW-9 (§13.3.2) vs. `axis_loader_resolution.md` §8.3 (`create_post_compact_hook` new signature).

**What is wrong:** SPEC §4.8 asserts the PostCompact hook "reads `<repo>/.claudechic/phase_context.md` fresh from disk and re-injects" with "no other change" beyond Group B's path migration. INV-AW-9 testifies this verbatim ("reads `<repo>/.claudechic/phase_context.md` ... and returns `{"reason": <contents>}` if non-empty"). But the existing hook at `agent_folders.py:107-148` does NOT read `phase_context.md` — it reassembles the prompt by calling `assemble_phase_prompt(workflows_dir, workflow_id, agent_role, current_phase)`, which reads `identity.md` + per-phase markdown from the workflow's role directory. `axis_loader_resolution.md` §8.3 keeps that reassembly pattern, only swapping `workflows_dir` → `workflow_dir`. So the SPEC instructs two different mechanisms in two places. The two mechanisms produce the same content (the assembled prompt and `_write_phase_context`'s output share assembly logic), but the source of truth differs.

**Why it matters (composability):** Seam-C between Group D's phase-context lifecycle and Group C's loader semantics is currently dirty. If the hook reads `phase_context.md`, it depends on `_write_phase_context` having run; if it reassembles via `assemble_phase_prompt`, it depends on the resolved workflow directory. Implementer-of-INV-AW-9 will rewrite the hook to file-read; Implementer-of-axis-spec will preserve reassembly. Whichever one lands first owns the contract.

**Recommended fix:** Pick one. Two options:
- **(A) File-read.** Edit §8.3 of `axis_loader_resolution.md` so `create_post_compact_hook(phase_context_path: Path)` takes the file path; the closure no longer needs `workflow_dir`. Drop `assemble_phase_prompt` from the hook path. INV-AW-9 stays as written.
- **(B) Reassemble.** Edit SPEC §4.8 row to say "the hook reassembles via `assemble_phase_prompt(workflow_dir=...)`; the relocated `phase_context.md` is what `_write_phase_context` writes for the agent's `Read`-tool consumption, NOT what the PostCompact hook reads." Edit INV-AW-9 to assert reassembly behavior, or drop the file-source assertion.

Option (A) is the simpler architecture (one source of truth: the file on disk; both `_write_phase_context` writes it and the hook reads it; `assemble_phase_prompt` becomes a `_write_phase_context` helper only). Option (B) preserves more existing code. Recommend (A).

### F2 — [HIGH] L15 piece-2 semantics quietly abandoned

**Where:** SPEC §4.1; STATUS A11 + A13.

**What is wrong:** L15 is "two-piece agent awareness: always-on at session start + once-per-agent fuller-context on first read inside `.claudechic/`." A11 reaffirms the two-piece design. A13 selects a mechanism (SDK rules-load) that supports either an eager (frontmatter-less) or a lazy (`paths:`-scoped) path. SPEC §4.1 chooses eager-only — all bundled context loads at session start. SPEC §4.1 acknowledges this: *"L15 piece 2 is satisfied by eager-load... per RESEARCH.md §3 Option B, this is the user-approved trade-off — the eager guarantee is stronger than the lazy trigger."* RESEARCH.md §3 Option B mentions `paths:` frontmatter as the available piece-2 mechanism but flags two open Anthropic bugs (#17204 user-tier `paths:` ignored; #21858 user-tier scoping). The user's verbatim approval ("approve option B, fine with all answers") is plausible but does not literally settle the L15-vs-effective gap.

**Why it matters (composability):** the user's literal text in A11 ("two") and L15 ("on first read inside `.claudechic/`") prescribe lazy semantics for piece 2. The SPEC's eager-everything choice is operationally simpler but is not the same shape. A future maintainer reading L15 + A11 + the SPEC will see the discrepancy and may try to "fix" it by adding `paths:` frontmatter — which would re-introduce the SDK bugs RESEARCH.md called out.

**Recommended fix:** Add a one-paragraph note to SPEC §4.1 (or §16.1) explicitly stating: "L15 piece-2 is eager-loaded rather than lazy-on-first-read, per RESEARCH.md Option B and user approval. The `paths:`-frontmatter alternative was considered and rejected for this run because of open Anthropic issues #17204 and #21858. Re-litigate in §SPEC_APPENDIX.md §9 reversal triggers if those bugs are fixed and lazy semantics become preferred." This makes the choice explicit rather than implicit and gives future maintainers the rationale.

### F3 — [MEDIUM] Boundary registry counting inconsistency between SPEC §11.6 and `axis_boundary_test.md` §10

**Where:** SPEC §11.6 acceptance bullet vs. `axis_boundary_test.md` §10 post-restructure table + §10 enumeration sentence.

**What is wrong:** SPEC §11.6 says "Three entries total" with `accepts_dotclaude: true`: (a) two worktree directory-entry symlinks (`.claude` and `.claudechic`), (b) the install-routine site `awareness_install.install_awareness_rules`. The boundary axis-spec lists FOUR distinct sites in its registry table: `worktree.git.symlink_dotclaude`, `worktree.git.symlink_dotclaudechic`, `awareness_install.write_rule`, `awareness_install.mkdir_rules_dir`. The boundary axis post-restructure summary then says "5 non-destructive-incidental entries" (counting both worktree symlinks + both install sites + a "claude_owned_files.yaml carve-out").

Additionally, the worktree `.claudechic` symlink does NOT live inside `.claude/` (its path is `<worktree_dir>/.claudechic`, parent is the worktree root). It should NOT carry `accepts_dotclaude: true` — only `is_dotclaudechic_directory_entry: true` per the analogous-predicate framing in §11.4 + axis §8.5. SPEC §11.6's "(a) two worktree directory-entry symlinks ... [both] share the 'directory-entry symlink' classification" is loose: only the `.claude` symlink touches `.claude/`; the `.claudechic` one doesn't.

**Why it matters (composability):** the boundary CI test's classification taxonomy is the contract between the lint and every contributor adding a write site. If the SPEC and the axis-spec disagree on what's classified as `accepts_dotclaude=true`, the Implementer of the registry YAML doesn't know which entries to flag.

**Recommended fix:** Reconcile to one count. Most defensible enumeration:
- `accepts_dotclaude=true` (writes resolving to a `.claude/` ancestor): `worktree.git.symlink_dotclaude` (pre-existing); `awareness_install.write_rule` (new); `awareness_install.mkdir_rules_dir` (new). **Three entries.**
- Separately classified, `is_dotclaudechic_directory_entry=true` (write to `<worktree_dir>/.claudechic` directory entry, parent is worktree root, NOT inside `.claude/`): `worktree.git.symlink_dotclaudechic`. **One entry; not under `accepts_dotclaude`.**

Edit SPEC §11.6 to state this directly. Edit `axis_boundary_test.md` §10's post-restructure summary sentence to match.

### F4 — [MEDIUM] Cross-axis seam between worktree symlink (§10) and artifact-dir scope (§5)

**Where:** SPEC §10.2 + §5 + `axis_artifact_dirs.md` §11.3 (concurrency).

**What is wrong:** SPEC §10.2 correctly notes that the new `.claudechic` worktree symlink makes `<repo>/.claudechic/runs/<chicsession_name>/` "visible across worktrees." `axis_artifact_dirs.md` §11.3 (K3) was written before the symlink decision was reversed: it says two claudechic instances on the same launched repo "share the parent `.claudechic/` directory but use distinct `runs/<chicsession_name>/` leaf dirs ... they do NOT interfere at the artifact-dir level." That holds in single-worktree topology. With the new symlink, two **worktrees** of the same repo also share the parent. K4 ("two app instances both choosing the same chicsession name in the same repo is undefined behavior") now applies to the cross-worktree case, which the user historically expected to be isolated.

**Why it matters (composability):** worktrees were originally designed to give per-feature isolated scratch space. The `.claude` symlink already breaks that for Claude state (intentionally); the new `.claudechic` symlink extends the breakage to claudechic state. This is a deliberate choice (per user direction at spec exit), but the consequence — chicsessions started in worktree A also show up in worktree B's `.claudechic/runs/` listing — is not stated anywhere the Tester would notice.

**Recommended fix:** Add a one-sentence note to `axis_artifact_dirs.md` §11 (or SPEC §10.2): "Per SPEC.md §10.3's `.claudechic` worktree symlink, two worktrees of the same repo share the same `.claudechic/runs/` directory; chicsession names MUST be unique across all worktrees of a repo or §11.4's K4 undefined-behavior caveat applies. This is the trade-off for cross-worktree state propagation; users who want per-worktree isolation should invoke claudechic from the main worktree only." Also add an INV (or extend INV-10) covering the cross-worktree-visibility expectation.

### F5 — [MEDIUM] `awareness.install` toggle semantics are asymmetric

**Where:** SPEC §4.4 + §8.3 #2 + UI label in §7.3.

**What is wrong:** the toggle gates the install **writer** but not the SDK **loader**. When the user flips `awareness.install: false` after a previous install, claudechic's startup install routine no-ops (per §4.3), but the already-installed `~/.claude/rules/claudechic_*.md` files remain on disk and the SDK keeps loading them on every session. The user-facing label "Install claudechic-awareness rules" implies a binary on/off; the actual semantics are "install-on-startup yes/no, with a stale-files carry-over." `docs/configuration.md` §8.3 #5 documents this honestly ("To manage rules manually, disable `awareness.install`. ... Disabling does NOT remove already-installed files"). But a user reading only the settings-screen label will misread the toggle.

**Why it matters (composability):** the toggle label collapses two independent axes into one bool: (a) "should claudechic write into `~/.claude/rules/`" and (b) "should the agent see claudechic-awareness content." The user-visible single toggle implements (a) only. From a clean-axes perspective this is a fused-axes smell.

**Recommended fix:** the cleanest answer would be a two-knob design (one toggle to write, one toggle to remove on next launch), but that's scope creep for this run. Cheaper fix: change the user-facing helper text per §7.3 to be explicit: *"Auto-install claudechic-awareness rules into `~/.claude/rules/` on every claudechic startup. Disable to manage manually. Disabling does NOT remove already-installed `claudechic_*.md` files; remove them yourself if you want them gone."* — and add the second sentence to `docs/configuration.md` §8.3 #2 (it's currently in #5, separate from the toggle description).

### F6 — [MEDIUM] `awareness_install.mkdir_rules_dir` doesn't fit the "claudechic-named" non-destructive-incidental taxonomy

**Where:** `axis_boundary_test.md` §2.1.2 (classification model) vs. §10 registry row + §8.6 carve-out.

**What is wrong:** the taxonomy in §2.1.2 says non-destructive-incidental requires "the basename is unambiguously claudechic-owned (e.g., starts with `claudechic`, `_chic`, `chic_`, or matches a registered claudechic-owned filename pattern)." The `mkdir(~/.claude/rules)` write does not satisfy that — `rules` is a Claude-owned directory name. §8.6 carves it out via a special predicate `is_claude_rules_dir_mkdir` ("creating Claude's standard rules-directory if absent ... non-destructive because directory creation is idempotent and never overwrites"). That's a defensible carve-out, but it's a special case rather than a clean abstraction over §2.1.2's four conditions.

**Why it matters (composability):** the classification taxonomy is the algebraic law that lets every new write site be classified by checking four conditions. With special-case carve-outs, the law has exceptions and a future contributor can't simply "check the four conditions" — they have to know about the carve-outs.

**Recommended fix:** generalize §2.1.2 condition (2) from "basename is unambiguously claudechic-owned" to "EITHER the basename is unambiguously claudechic-owned OR the write is an idempotent `mkdir`/`mkdir(parents=True, exist_ok=True)` that creates a Claude-Code-discovered standard directory if absent." Document the rationale once in the taxonomy, and drop §8.6's special predicate. The acceptance test still covers it via the registry. Or, alternatively, accept the carve-out as deliberate and rename §8.6's predicate from a one-off to "the directory-creation carve-out" with a list of permitted target dirs (currently `~/.claude/rules`).

### F7 — [LOW] SPEC §2.4 broken cross-reference

**Where:** SPEC §2.4 ("Phase context relocation") says "Owned by Group D (§5.5); Group B SHOULD NOT independently move `phase_context.md`."

**What is wrong:** §5.5 in SPEC.md is "Chicsession name validation" inside Group E (artifact dirs). The phase-context lifecycle is in §4.8 (Group D). The reference is a stale-numbering typo from an earlier revision.

**Recommended fix:** "Owned by Group D (§4.8); Group B SHOULD NOT independently move `phase_context.md`."

### F8 — [LOW] `/onboarding context_docs` phase-doc invocation mechanism is implicit

**Where:** SPEC §4.7.

**What is wrong:** §4.7 says the restored phase doc "invokes `claudechic.awareness_install.install_awareness_rules(force=True)` and reports the result to the user via the agent's response surface." Phase docs are markdown read by an agent — the agent must execute the function via some tool (Bash with `python -c`, an MCP tool, or otherwise). The SPEC doesn't say which. The existing `context_docs.md` in the repo presumably contains Bash invocations; the post-A13 adapted version has to translate "invoke the install routine" into a concrete instruction.

**Why it matters:** the contract between the engine module (`awareness_install.install_awareness_rules`) and its agent-driven invocation site is implicit. Implementer needs to author the new phase-doc text and make a choice (Bash command? new MCP tool wrapping the function? CLI subcommand?).

**Recommended fix:** specify the agent-side trigger explicitly. Cheapest answer: phase doc instructs the agent to run `python -c "from claudechic.awareness_install import install_awareness_rules; r = install_awareness_rules(force=True); print(r)"` via the Bash tool, then to summarize `r.new`/`r.updated`/`r.skipped` to the user. Alternative: add a small `chic_install_awareness` MCP tool (in `claudechic/mcp.py`) so the phase doc just calls the MCP tool. Either is fine; pick one and write it down.

### F9 — [LOW] INV-AW-3 doesn't cover the mkdir site

**Where:** SPEC §13.3.1 INV-AW-3.

**What is wrong:** INV-AW-3 says "Every file written by the install routine has a basename matching `claudechic_*.md`; no other filename is created." This covers `write_text` calls but not the `mkdir(~/.claude/rules)` call (`awareness_install.mkdir_rules_dir`). The mkdir is implicitly enforced by the boundary registry but is not asserted in the install-routine acceptance.

**Recommended fix:** extend INV-AW-3 to: "Every file written by the install routine has a basename matching `claudechic_*.md`; no other filename is created. The only directory the routine creates is `~/.claude/rules` itself (idempotent `mkdir(parents=True, exist_ok=True)`); the routine creates no subdirectories."

### F10 — [LOW] User-authored `<repo>/.claudechic/context/*.md` is silently ignored

**Where:** SPEC §4 + RESEARCH.md §4.4 (open question, deferred).

**What is wrong:** the loader's three-tier model applies to workflows, rules, hints, and MCP tools. The awareness-install routine reads only `claudechic/context/*.md` (package). User-authored `<repo>/.claudechic/context/extra.md` (or `~/.claudechic/context/extra.md`) is not picked up by either the loader (not a known content category) or the install routine (only the package dir is scanned). Effectively dead weight if a user puts a file there.

**Why it matters (composability):** the user expects "everything in 3 levels" (per A5/Q2'). Awareness content is currently 1-level (package only). This is a deliberate trade-off per RESEARCH.md §4.4 ("Recommendation: yes, as a follow-up") — but a user who reads about 3-tier content and tries to override awareness will silently fail.

**Recommended fix:** at minimum, document in `docs/configuration.md` §8.3: "claudechic-awareness rules ship from the package only; per-user / per-project additions go directly into `~/.claude/rules/<your-name>.md` or `<repo>/.claude/rules/<your-name>.md` respectively (NOT the `claudechic_` prefix; that namespace is claudechic-owned). The loader's 3-tier model does not apply to awareness content." A future revision could extend the install routine to also walk user/project-tier `.claudechic/context/` dirs, per RESEARCH.md §4.4 — out of scope for this run, but worth documenting the deferred choice.

### F11 — [LOW] Group F naming (F1–F5) referenced but not defined

**Where:** SPEC §0.4 ("F2 = 8e46bca depends on A; F1, F3, F4, F5 are orthogonal").

**What is wrong:** the F1-F5 numbering is referenced once and never explicitly mapped. Reader has to infer F1 = `9fed0f3`, F2 = `8e46bca`, F3 = `f9c9418`, F4 = `5700ef5`, F5 = `7e30a53` from the §6.1 row order.

**Recommended fix:** either expand "F2 = 8e46bca" to list all five mappings inline, or drop the numbering and just say "Cherry-pick `8e46bca` MUST land after Group A (it touches workflow path resolution); the other four cherry-picks are orthogonal."

---

## §3 Blockers vs nice-to-haves

### Blockers (must resolve before implementation can proceed without rework)

- **F1** — PostCompact-hook source contradiction. The Implementer cannot satisfy both INV-AW-9 (file-read) and `axis_loader_resolution.md` §8.3 (reassembly) simultaneously. Pick one mechanism and update both specs to match.
- **F3** — Boundary registry counting inconsistency. The boundary-test Implementer needs an unambiguous count and predicate set. The lint blocks merge; the registry must match the lint's expectations exactly.

### Nice-to-haves (resolve before implementation OR defer to first PR follow-up)

- **F2** — L15 piece-2 semantics. The implementation works either way; the maintenance issue is rationale clarity. Adding the one-paragraph note is cheap.
- **F4** — Worktree-scope cross-axis seam. Documented behavior is fine; no implementation block. Worth one INV.
- **F5** — Toggle label asymmetry. Helper text update only; no code change.
- **F6** — Taxonomy carve-out for `mkdir_rules_dir`. Either generalize the law or accept the special case explicitly. Either is implementable.
- **F7** — Cross-reference typo. Trivial.
- **F8** — Phase-doc invocation mechanism. Implementer can pick reasonably; explicit choice would prevent inconsistency between two implementers.
- **F9** — INV-AW-3 mkdir coverage. Test addition; trivial.
- **F10** — Documentation gap for user-authored context. Doc edit only.
- **F11** — F1-F5 naming. Trivial.

---

## §4 Verdict

**READY WITH FIXES.**

Required fixes before implementation begins:

1. **F1**: Pick PostCompact-hook source-of-truth (file-read OR reassembly); update SPEC §4.8, INV-AW-9, and `axis_loader_resolution.md` §8.3 to match. (Recommend file-read; simpler architecture.)
2. **F3**: Reconcile boundary registry count between SPEC §11.6 and `axis_boundary_test.md` §10. State the three-entry vs. four-entry classification clearly and drop the muddled `.claudechic`-symlink-as-`accepts_dotclaude` framing.

The other nine findings are nice-to-haves: addressing them would tighten the spec and reduce ambiguity, but they don't block implementation start. F7 (cross-ref typo), F9 (INV-AW-3), F11 (F1-F5 naming) are zero-effort fixes worth bundling with F1+F3. F2, F4, F5, F6, F8, F10 can be addressed during implementation review.

Architectural shape is sound. The eight-group decomposition cleanly separates restructure, boundary relocation, loader, awareness install, artifact dirs, cherry-picks, UI, and boundary CI. The A13 pivot away from custom SDK hooks is the right move and the seam between awareness install (static, eager, SDK-loaded) and phase-context delivery (dynamic, mid-session, engine-authored) is clean. The 3-tier loader generalizes `discover_manifests` correctly and the partial-override fall-through resolves the cross-lens disagreement well. The boundary CI test's hybrid static-AST + runtime model is appropriate. The user-direction reversal restoring the worktree symlink scopes A4's no-symlinks rule cleanly to Group D.

---

*End of fresh_review_composability.md.*
