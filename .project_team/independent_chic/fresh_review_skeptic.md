# Fresh Skeptic Review — independent_chic spec-exit

**Author:** Skeptic (fresh instance; no inherited context).
**Charter:** Independent cold risk re-evaluation of the operational specification at the spec-exit checkpoint, with explicit focus on (a) the SDK-native rules-loading dependency introduced by A13, (b) the worktree-symlink reversal at §10, (c) implementer-trap scenarios, (d) residual risks from multiple late spec revisions, (e) L10 4-sense sweep on the cherry-pick set, (f) boundary CI exit-criteria, and (g) the deletion of the drift hint.
**Mode:** Review-only per L14. Locks L1–L17 and amendments A1–A13 are USER-LOCKED — risks surfaced, no re-litigation. No time estimates per L13.

---

## §1 Lens summary

The spec is operationally well-formed and the simplification A13 buys (Group D collapses ~600 → ~50 lines) is real. Three structural concerns survive close reading:

1. **Group D's install routine has NEW/UPDATE/SKIP semantics but no DELETE — orphan `claudechic_*.md` files accumulate forever** when bundled filenames change, when claudechic is uninstalled, or when `awareness.install` is toggled off. The deleted `ContextDocsDrift` hint was the only diagnostic surface for stale awareness; with both hint and any cleanup path absent, the user has no in-app signal when their `~/.claude/rules/` is wrong.
2. **§12.2 explicitly waives end-to-end verification of the SDK behavior the entire mechanism depends on.** Combined with the "we own the `claudechic_*` prefix in `~/.claude/rules/`" unilateral-namespace claim, the spec accepts a hard external dependency without a fail-detect path.
3. **The boundary-test predicate `is_claudechic_prefixed_rules_file` is path-shape only;** the spec doesn't constrain bundle filenames, doesn't validate the install target against pre-existing user symlinks, and offers no answer to "what happens when the user manually edits a `claudechic_*` file thinking they're customizing claudechic?"

Verdict: **READY WITH FIXES** — the fixes are small implementation-phase additions, not redesigns.

---

## §2 Findings

Each finding: severity, trigger, scenario, detection, mitigation status.

### F1 — CRITICAL — Stale `claudechic_*.md` orphan accumulation in `~/.claude/rules/`

**Trigger:** A bundled context filename is renamed or removed across claudechic versions; OR a user uninstalls claudechic without manually deleting `~/.claude/rules/claudechic_*.md`; OR `awareness.install` is toggled off and the user expects "stop installing" to mean "stop influencing my agents."

**Scenario.** §4.3 MUST NOT bullet (verbatim): *"Delete any file inside `~/.claude/rules/` (including stale `claudechic_*.md` files whose bundled source has been removed; per L17/A9 silent-loss policy, deletion is the user's responsibility)."* The install routine is NEW/UPDATE/SKIP only. Concrete failure paths:

- Claudechic v1 ships `claudechic_workflows-system.md`. v2 renames to `claudechic_workflow-engine.md`. After upgrade, the install routine creates the new file (NEW) and **leaves `claudechic_workflows-system.md` in place forever.** The Claude Agent SDK loads BOTH on every session in every project; the agent gets stale outdated context. This is silent — no warning, no log, no UI surface (the `ContextDocsDrift` hint is deleted per §4.6).
- A user who installs claudechic, uses it for a month, then uninstalls the package via `pip/uv` has `~/.claude/rules/claudechic_*.md` files orphaned in EVERY future Claude Code session, in EVERY project, even unrelated ones. Plain `claude` invocations carry claudechic context forever. The user has no documented uninstall step (`docs/configuration.md` §8.3 per §4.3 reference is described but the section content per SPEC.md §8.3 does not mandate a `rm` line).
- A user toggles "Install claudechic-awareness rules" OFF expecting "claudechic stops doing this." The toggle prevents future installs (per §7.3 helper text "Disable to manage manually") but the existing files keep loading. The UX is misleading.

**L10.d (intent lost) bridge.** The user explicitly accepted "if I disable, it is on me" (per A13 user words). But "on me" presupposes that "me" knows the mechanism owns claudechic-prefixed files in a SHARED Claude Code surface that survives across all projects. A typical user reading the toggle text "Auto-install claudechic-awareness rules into `~/.claude/rules/` so Claude understands its environment. Disable to manage manually." would not infer "I have to `rm ~/.claude/rules/claudechic_*.md` to actually disable the influence." That's lost intent.

**Detection.** Zero in-product. Manual: a user notices Claude in a non-claudechic project knows about workflows/hints concepts.

**Mitigation status: spec-needs-addition.** Either:
- (a) Extend §4.3 to enumerate `~/.claude/rules/claudechic_*.md` and delete files whose bundled source no longer exists. This is L17-clean: L17/A9 forbid migration logic for state created by *prior* claudechic versions; cleaning up files claudechic itself wrote is maintenance of an owned namespace, not migration. The MUST NOT in §4.3 ("Delete any file ... including stale `claudechic_*.md`") explicitly forbids this — the spec's current stance was the user's accepted tradeoff but should be revisited.
- (b) Add a one-line `rm` instruction to `docs/configuration.md` §8.3 ("To remove all claudechic-installed rules: `rm ~/.claude/rules/claudechic_*.md`") AND update the Settings UI helper text from "Disable to manage manually" to something like "Disable to stop future installs; existing files remain. To remove: `rm ~/.claude/rules/claudechic_*.md`."

**(a) is preferable; the prefix-namespace ownership claim already implies write authority — it should imply delete authority.** Without one of these mitigations, the user's "approve option B" is a long-tail support time bomb.

---

### F2 — HIGH — `setting_sources` API surface drift; spec waives verification (§12.2)

**Trigger:** Anthropic deprecates or alters `setting_sources=["user"]` semantics, OR adds a future Claude Code release that scopes frontmatter-less files differently, OR the open issues #17204 / #21858 propagate to the unscoped-load path.

**Scenario.** §12.2 verbatim: *"No verification step required. The SDK's behavior is the contract; if Anthropic regresses the rules-load behavior in a future CLI, claudechic's mechanism degrades along with every other tool that relies on `.claude/rules/`. Out of scope for this spec."* This is accepting a hard external dependency without a fail-detect mechanism. Concrete paths:

- Anthropic ships Claude Code 2.x with a new memory format (`~/.claude/memory.toml`, etc.) and deprecates `setting_sources=["user"]` to a no-op. claudechic continues installing into `~/.claude/rules/`; the SDK silently stops loading. Agents lose claudechic awareness. claudechic emits no warning, no diagnostic.
- Open issue #17204 (`paths:` quoted-list bug) is currently "Open" per RESEARCH.md. The mitigation in Group D is "ship frontmatter-less files." But if Anthropic fixes #17204 by changing the precedence rules for unscoped files (e.g., requires `paths:` to opt-in), frontmatter-less files become silently unloaded.
- A future Claude Code release tightens `~/.claude/rules/` to "files Anthropic ships" only (the spec assumes this is unlikely, but #21858 already showed Anthropic *changes* loader behavior on this surface). claudechic's prefix-namespace claim is broken; install becomes a quiet no-op.

The deletion of `ContextDocsDrift` (§4.6) means there is also no detection from the *other* end (a stale-bundle check). With no in-process signal in either direction, the agent's awareness can be silently absent for an indefinite period.

**Detection.** None; the spec explicitly waives it.

**Mitigation status: spec-needs-addition.** A small addition is sufficient:
- Add the `InstructionsLoaded` hook (RESEARCH.md §2 Target 1 mentions it — fires per loaded instruction file). On every claudechic-spawned session, count `claudechic_*.md` files that fired the hook; if zero, log WARNING `"awareness rules not loaded by SDK; check Claude Code version compatibility"`. This satisfies "verify the documented loader is doing what we expect" without a separate Tester invariant.
- Alternatively, an INV-AW-* invariant that runs a real Claude Code subprocess in CI and asserts a sentinel string from `claudechic_overview.md` reaches the agent.

The user accepted A13's approach. They did not explicitly accept "no fail-detect." That gap is the issue.

---

### F3 — HIGH — Install routine writes through user-created symlinks at the target path

**Trigger:** A user has placed (intentionally or accidentally) a symbolic link at `~/.claude/rules/claudechic_<name>.md` that points outside `~/.claude/rules/`.

**Scenario.** §4.3 MUST NOT bullets list "Create symbolic links of any kind" but do NOT forbid traversing user-created symlinks during write. The install routine's UPDATE branch does `target.write_text(bundled_content)` (or `shutil.copyfile`) — Python's `write_text` follows symlinks for write semantics on POSIX. If the user has, intentionally or by accident, created `~/.claude/rules/claudechic_overview.md` as a symlink pointing at `~/.bashrc` (extreme example) or `~/notes/important.md` (realistic), the install routine overwrites the link target.

This is exactly the class of "non-destructive incidental" assumption the A13 prefix-namespace claim rests on (claudechic owns `claudechic_*` filenames inside `~/.claude/rules/`). But "owns the basename" is not "owns the inode." The boundary-test predicate (`is_claudechic_prefixed_rules_file`) checks the path; it cannot inspect link targets at static-analysis time.

**Detection.** Boundary CI does not catch this (it scans claudechic source, not runtime FS state). The user discovers when their unrelated file is clobbered.

**Mitigation status: spec-needs-addition.** §4.3 should add a MUST: *"If the install target exists and is a symbolic link, the install routine MUST `unlink` the link before writing the new content (the new content is a regular file). The routine MUST NOT follow the link to write into its target."* Two extra lines in `awareness_install.py`:
```python
if target.is_symlink():
    target.unlink()
target.write_text(bundled.read_text())
```

This also closes a related vector: `target.read_bytes() == bundled.read_bytes()` for SKIP follows the symlink, so a user could trick claudechic into "skipping" by symlinking their custom file to one byte-equal to the bundle.

---

### F4 — HIGH — `awareness.install=False` does not undo prior installs; UX-trap on the disable toggle

**Trigger:** User reads "Install claudechic-awareness rules: disable to manage manually" and toggles off, expecting claudechic to stop influencing agents.

**Scenario.** Reads §4.3 + §7.3:
- §4.3 — "If `False` and `force=False`, return immediately. **No file I/O when disabled.**"
- §7.3 — "Disabling does NOT remove already-installed files (per L17/A9 silent-loss policy)."

The Settings UI label is "Install claudechic-awareness rules" (per §7.3). A user who toggles this OFF reasonably expects the *behavior* to stop, not the *future writes* to stop. Existing `claudechic_*.md` files keep loading in every session, in every project, until the user manually `rm`s them. The UI text doesn't tell them this.

This compounds with F1: a user who tries to "opt out" finds they can't actually opt out without OS-level commands. The user's verbatim "if I disable, it is on me" was about not auto-installing on startup, not about the orphan-accumulation effect.

**Detection.** None until the user notices agents-in-other-projects know about claudechic.

**Mitigation status: spec-needs-addition.** Same fix space as F1:
- Either change the toggle to one-shot uninstall on transition `True → False` (a single delete pass), with the helper text "Disable removes claudechic-installed rules from `~/.claude/rules/` and stops future re-installs." This is the most user-aligned behavior.
- Or update the helper text to be honest: "Disabling stops future installs; existing files remain in `~/.claude/rules/`. Run `rm ~/.claude/rules/claudechic_*.md` to remove them."

The current helper text (§7.3 "Disable to manage manually") understates the consequence.

---

### F5 — HIGH — Implementer trap: `d55d8c0` lookalike rewrite undetectable by boundary CI

**Trigger:** Implementer reading SPEC.md §3.1 (which explicitly forbids consulting `git show d55d8c0`) reaches §6.5 of the loader axis-spec (partial-override detection), considers the cognitive load, and silently consults the dropped commit "just for context" — then transcribes its logic line-by-line.

**Scenario.** Three reinforcing conditions:
1. The 3-tier loader is described as a "small generalization" of `discover_manifests` (§3.1, axis §1). But `_resolve_by_id`, `_build_item_provenance`, `_reject_partial_overrides`, `_resolve_workflows`, `LoadResult.workflow_provenance/item_provenance`, and the `Step 1..9` pipeline of axis §5.4 are NOT small generalizations — they are new logic that the from-scratch language understates.
2. Acceptance §3.7's last bullet is self-asserted: *"Cherry-pick `d55d8c0` is NOT used (no `git cherry-pick d55d8c0`, no `git show d55d8c0`-derived code)."* This is implementer self-report; nothing tests it.
3. Boundary CI catches `git cherry-pick d55d8c0` (commit hash absent from `git log`) but does NOT catch a lookalike rewrite. There is no AST-similarity test.

**L10.d.** This is the canonical L10.d trap from the prior register's R12, with mitigation A8 dropping the cherry-pick. The mitigation is structural (no commit) but not behavioral (no lookalike check). The spec is honest about this; surfacing as residual.

**Detection.** Code review only. The implementer's coordinator must spot-check that the new loader's structure/identifiers/comments are NOT abast-derived. There's no automated signal.

**Mitigation status: accepted-as-tradeoff.** The spec is explicit. Surfaced for the user's awareness, not as a blocker. To strengthen: a §3.7 acceptance line `[ ] Implementer attests in PR description: "I have not consulted git show d55d8c0 or any partial-extraction during this work."` makes the L10.d burden explicit at PR-merge time.

---

### F6 — MEDIUM — Concurrent worktree creation race at the new `.claudechic` symlink site

**Trigger:** User invokes `git worktree add` (or claudechic's UI equivalent) twice in close succession from the same launched repo — e.g., spawns two new worktrees in parallel.

**Scenario.** §10.3 illustrative code:
```python
source_claudechic_dir = main_wt_info[0] / ".claudechic"
if source_claudechic_dir.is_dir():
    target = worktree_dir / ".claudechic"
    if not target.exists():
        target.symlink_to(source_claudechic_dir.resolve())
```

`target.exists()` is racy: if two processes interleave, both can pass the check and both call `symlink_to`. The second call raises `FileExistsError`. The wrapping `try / except Exception as e: return False, f"Error: {e}", None` (visible at `git.py:307-308` in the existing code) catches it but reports `"Error"` to the UI. The worktree directory creation succeeded; the symlink ended up valid; the UI shows a red error. Confusing.

The existing `.claude/` symlink at `git.py:299-301` has the same race; it's a pre-existing latent bug, not introduced by this spec — but §10.3 doubles the surface area without fixing the pattern.

**Detection.** Surfaces as user-visible "Error" on a worktree that actually works. Hard to repro deterministically.

**Mitigation status: spec-needs-addition.** Trivial fix: replace `if not target.exists(): target.symlink_to(...)` with `try: target.symlink_to(...); except FileExistsError: pass`. Two-line patch; the spec should specify the pattern in §10.3 (currently the illustrative code is the racy form).

---

### F7 — MEDIUM — User `rm -rf .claudechic/` (with trailing slash) traverses the worktree symlink

**Trigger:** User in a worktree wants to "clean up" what looks like a stale `.claudechic` directory; runs `rm -rf .claudechic/` (with trailing slash, important).

**Scenario.** GNU `rm -rf .claudechic` (no slash) removes the symlink itself. `rm -rf .claudechic/` (with slash) recursively follows the symlink to delete contents in the *target* — which is the main worktree's `.claudechic/`. The user loses all claudechic project-tier state (config.yaml, hints_state, runs/, phase_context.md) for the entire repo. Unrecoverable.

The `.claude/` symlink has the same hazard (pre-existing); §10 makes it a doubled surface. The Windows-portability concern at GitHub #26 is documented; the *destructive-action-via-symlink* hazard is not.

**Detection.** Catastrophic and obvious to the user *after* the fact.

**Mitigation status: spec-could-document.** `docs/configuration.md` §8 (or a new §10 worktree section) should include a warning paragraph: *"`.claude/` and `.claudechic/` in worktrees are symlinks to the main worktree's directories. `rm -rf .claudechic/` (with trailing slash) deletes the main worktree's claudechic state. Use `rm .claudechic` (no slash) to remove only the worktree's symlink."* This is user-education, not spec correctness — but the spec's silence on this is consistent with how the pre-existing `.claude` symlink was treated. Surfacing as a residual.

---

### F8 — MEDIUM — Bundle filename safety not enforced; install path can escape `~/.claude/rules/`

**Trigger:** A future claudechic version adds a context file with an unusual name — most likely a subdirectory (e.g., `claudechic/context/sdk-notes/quickstart.md`) or a name containing `..`. Alternatively, an attacker who can write to `claudechic/context/` (controlled threat model — they already have repo write access).

**Scenario.** §4.3: *"Walk `<package>/context/*.md` (every `.md` file in `claudechic/context/`)."* The glob `*.md` is top-level; subdirectories are not walked. Good.

But: §4.3 then computes `target = ~/.claude/rules/claudechic_<name>.md` where `<name>` is the bundled file's basename without extension. If a future maintainer changes the glob to `**/*.md` (recursive), the `<name>` could be `sdk-notes/quickstart` and the target becomes `~/.claude/rules/claudechic_sdk-notes/quickstart.md` — a path with TWO segments. The boundary predicate `is_claudechic_prefixed_rules_file` checks "parent is exactly `~/.claude/rules`" — `~/.claude/rules/claudechic_sdk-notes/quickstart.md` has parent `~/.claude/rules/claudechic_sdk-notes`, predicate fails, boundary CI fires.

That's GOOD — the predicate catches the violation. But: the failure surfaces only at CI time, blocking merge of an otherwise innocuous "let me organize the bundled docs into subdirectories" PR. A maintainer might respond by relaxing the predicate ("just add the new path pattern to the allowlist") — and accidentally weaken the boundary.

**Detection.** Boundary CI catches; subsequent loosening of the predicate is a separate human-review concern.

**Mitigation status: spec-needs-addition.** §4.3 should explicitly state: *"The walk MUST be top-level only (`Path.glob('*.md')`, not `rglob`); bundled files MUST NOT live in subdirectories of `claudechic/context/`. The install routine MUST validate `<name>` against `^[A-Za-z0-9_\-.]+$` before computing the target path."* Closes the recursive-glob foot-gun.

---

### F9 — MEDIUM — No drift signal post hint deletion; user with `awareness.install=False` has zero in-app diagnostic when their installed copies go stale

**Trigger:** Time. A user disabled auto-install, manually `cp`'d the bundled docs into `~/.claude/rules/` last year, upgrades claudechic, doesn't realize the bundled docs changed. Agents now run on stale awareness.

**Scenario.** §4.6 deletes both `ContextDocsDrift` trigger and `context_docs_outdated` hint. The user's verbatim acceptance was "if I disable, it is on me" — but "on me" presupposes:
- The user remembers `awareness.install=False` is set
- The user knows the docs change between releases
- The user has a way to compare bundled-vs-installed

None of these are surfaced anywhere in claudechic post-A13. The settings screen shows the toggle (`awareness.install: False`) but does not show "8 bundled docs, 3 installed copies are out of date relative to the bundle." There is NO diagnostic surface — the appendix's §9 reversal triggers list "user base grows beyond developers" as a reconsideration condition for A9 (silent-loss policy), but does not list "user disables awareness.install and develops drift confusion" as a reconsideration condition for the hint deletion.

A year from now, a user with stale awareness has no claudechic-internal way to figure out *why* their agents act dumb. Their support path is "open a GitHub issue" → maintainer says "did you `awareness.install` toggle off?" → user "yes a year ago" → maintainer "run `/onboarding context_docs` to manually re-install."

**Detection.** Out-of-band only.

**Mitigation status: spec-needs-addition (small).** No need to restore a hint. Just surface the install-routine result on the Settings screen:
- A read-only line under the `awareness.install` toggle: `"Last install: 2026-04-26 (NEW=0, UPDATE=0, SKIP=8)"` if enabled; `"Disabled. Run /onboarding context_docs to install manually."` if disabled.
- Computed from the existing `InstallResult` (already structured per §4.2).

This is one widget in `claudechic/screens/settings.py` and ~10 lines of code. The user gets a checkable signal; the hint stays deleted (per A13 user direction). The user's "on me" is preserved — they still own the action — but they have a place to look. Acceptance §7.5 doesn't require this; surfacing as a gap.

---

### F10 — MEDIUM — Line-ending fragility on cross-platform installs and source-form distributions

**Trigger:** User on Windows installs claudechic (the agent-awareness mechanism is documented as not requiring symlinks, so Group D's `awareness_install.py` ostensibly works on Windows), OR an editor-induced LF→CRLF on a developer machine, OR a source-form `uv build` from a checked-out tree where `core.autocrlf=true` flipped line endings.

**Scenario.** §4.3 SKIP test is byte-equal: `target.read_bytes() == bundled.read_bytes()`. On a system where the bundled `claudechic/context/*.md` files were LF in the package wheel but the user's `~/.claude/rules/claudechic_overview.md` got rewritten as CRLF by Claude Code or Windows file APIs (or vice versa), every claudechic startup will trigger UPDATE and rewrite the file. This is functionally idempotent (same effective content) but:
- The log line `awareness install: NEW=0 UPDATE=8 SKIP=0` repeats every startup, obscuring real updates.
- If Claude Code's loader is sensitive to line endings (RESEARCH.md issue #17204 hints at frontmatter-parsing fragility), the rewrite cycle can mask actual bugs.

**Detection.** Visible in logs as repeated UPDATE counts. The current spec doesn't surface this in the UI (per F9).

**Mitigation status: spec-needs-addition (small).** §4.3 SKIP comparison should be: `target.read_text(encoding='utf-8').replace('\r\n', '\n') == bundled.read_text(encoding='utf-8').replace('\r\n', '\n')`. Or use a checksum sidecar. Either way: SKIP should be normalized-equivalent, not bytes-equal.

---

### F11 — MEDIUM — Group A→C dependency: `_workflows_dir` removal is grep-only; latent reads break at runtime

**Trigger:** A `self._workflows_dir` reference exists at a code path not enumerated in axis_loader_resolution.md §8.4 (the spec lists `app.py:917-923` and `app.py:1840-1843`).

**Scenario.** axis_loader_resolution.md §8.4: *"The instance attribute `self._workflows_dir` (set at `app.py:1493`) is REMOVED from `app.py`. Any other reads of it MUST be replaced by lookups against `self._load_result.workflows`."* "Any other reads MUST be replaced" is open-ended. If a debug-only code path or an error-handling branch reads `self._workflows_dir`, the runtime fails with `AttributeError` only when that path runs. Tests may not exercise it.

**Detection.** Pyright catches if `_workflows_dir` is removed AND every reader is rewritten in the same PR. If a reader survives, pyright catches it. Good — but the spec doesn't *mandate* deletion (just removal of the SET site). If the implementer leaves `self._workflows_dir = ...` set "just in case," all readers continue to work and the migration is incomplete.

**Mitigation status: spec-needs-addition.** Add an acceptance bullet: *"`grep -rn '_workflows_dir' claudechic/` returns zero matches outside `app.py`'s `_load_result.workflows` migration sites."* (or zero matches total if the attribute is fully retired). One-line check.

---

### F12 — LOW — `claudechic_` prefix is a unilateral namespace claim, not a registered convention

**Trigger:** A future Anthropic Claude Code release ships rule files with names matching `claudechic_*.md`, OR another tool in the ecosystem also adopts the prefix.

**Scenario.** A13's "claudechic-owned by prefix" predicate rests on no published Anthropic agreement that `claudechic_` is reserved. Probability is low — Anthropic's naming is unlikely to collide. But the dependency exists.

**Detection.** UPDATE branch would clobber a colliding file silently.

**Mitigation status: accepted-as-tradeoff.** Documented in SPEC_APPENDIX.md §4.4. Reversal trigger should be added implicitly to §9 ("Reconsider the prefix claim if Anthropic ships colliding files").

---

### F13 — LOW — `~/.claude/` directory creation on a fresh-user system

**Trigger:** A first-time user runs claudechic before ever running `claude /login`.

**Scenario.** §4.3: *"Create `~/.claude/rules/` parent directory if absent (`mkdir(parents=True, exist_ok=True)`)."* If `~/.claude/` does not exist (user has never used Claude Code), `mkdir(parents=True)` creates it. Subsequent `claude /login` may detect the pre-existing `.claude/` and behave differently (skip onboarding, assume prior setup).

**Detection.** Only via Claude Code's first-run logic, which we don't control.

**Mitigation status: accepted-as-tradeoff (likely vacuous).** Per CLAUDE.md, claudechic requires Claude Code to be logged in — `~/.claude/` exists in any practical install path. The mkdir is a no-op in real use. Surfacing as a theoretical edge case for completeness.

---

### F14 — LOW — Late-revision residuals in SPEC_APPENDIX.md (cosmetic only)

**Trigger:** Future maintainer reads SPEC_APPENDIX.md §4.4 and §7 and is confused by historical paragraphs presented alongside current ones.

**Scenario.** SPEC_APPENDIX.md §4.4 contains paragraphs from the SUPERSEDED Group D design ("**The interim flip-flop (worth recording for transparency)...**" and "**The mid-session phase-advance failure mode...**") interleaved with the new A13 design. They're labeled as historical context but a hasty reader could conflate. SPEC_APPENDIX.md §7 has two list items both numbered "9" (the duplication is mechanical from the late edit).

**Detection.** Spot-checked here.

**Mitigation status: spec-needs-addition (cosmetic).** Re-number §7's anti-pattern list. Add a clearer demarcation in §4.4 between "current design" and "historical path." This is appendix-only; not operational.

---

### F15 — LOW — INV-AW-* coverage gaps: phase-context lifecycle invariants don't exercise the busy-agent edge case

**Trigger:** Phase advance fires while the agent is mid-tool-execution; the explicit re-read message queues but the agent's subsequent turn doesn't naturally include a Read of `.claudechic/phase_context.md`.

**Scenario.** §4.8 preserves the existing pattern (`_inject_phase_prompt_to_main_agent` sends a chat message saying "re-read your phase context"). The agent's compliance is implicit — it relies on the agent obeying the chat message. There's no MUST that the agent calls Read; if the agent doesn't, the phase advance is invisible to the next agent action.

INV-AW-8 verifies the *send* side ("sends a chat message ... that names the file"). It does not verify the *receive* side (agent eventually reads the file). The end-to-end invariant for "phase advance is observed by the agent" is not in §13.3.2.

**Detection.** End-to-end Tester acceptance, not spec'd as an invariant.

**Mitigation status: accepted-as-tradeoff.** This is a pre-existing pattern (not introduced by A13). Surfacing because the previous L15-piece-2 "first read inside `.claudechic/`" trigger (now satisfied by SDK eager-load) made the lazy-read explicit and testable; the new design relies on agent obedience to a chat message. Slightly weaker testability than the superseded design.

---

## §3 Comparison to prior risk register

### Prior risks adequately mitigated by spec/A13

| Prior risk | Mitigation in spec |
|---|---|
| R1 (phase_context regression) | Boundary CI test (Group H) catches |
| R2 (A3 mechanism writes `.claude/`) | A13 reframes — writes ARE permitted under prefix carve-out; A4 absolute prohibitions still hold |
| R3 (workflow phase docs reference `.claude/rules/`) | onboarding/context_docs RESTORED with adapted target (§4.7); identity.md context section RESTORED |
| R4 (`_STATE_FILE` regression) | §2.3 explicit |
| R5 (future contributor copy-paste) | Boundary CI gates merge |
| R8 (override edge cases) | axis_loader_resolution.md §6.5 + INV-PO-1..3 |
| R11 (cherry-pick timing) | §0.4 ordering committed |
| R12 (d55d8c0 brittleness) | A8 dropped; my F5 is the residual |
| R13 (5700ef5 collision) | Acceptance §6.2 has fresh-install verification |
| R20 (worktree symlink) | §10 reversed; my F6/F7 are residuals |
| R22 (L14 trap) | Two-file split |

### Prior risks inadequately mitigated (residual)

| Prior risk | Why still residual |
|---|---|
| R7 (A3 testability) | INV-AW-1..5 cover install routine; the "agent treats as rule-equivalent" is delegated to "SDK behavior is the contract" (§12.2). Tester acceptance is single-sentinel-string per §14.1 — adequate, but my F2 / F15 surface the SDK-trust gap. |
| R9 (schema drift across tiers) | Per-item fail-open preserved (axis §11.2). User/project YAML against package's schema-vN parser still silently drops. Spec does not address. |
| R10 (empty vs missing tier dirs) | axis §11.1 distinguishes "fail-closed" (package) from "fail-open" (user/project). No INFO log distinguishing "empty" from "missing." User confusion path unaddressed. |
| R16 (app.py initialization sequence) | Group F cherry-picks + Group A restructure + Group D install + Group G UI all touch `app.py`. Spec does not commit a canonical init sequence. Mitigated partly by group ordering (§0.4); the cumulative state of `on_mount` after all groups is composed by mechanical merge. |
| R17 (commands.py manifest test) | No commands-manifest assertion test in §13. Drop-on-merge surfaces only as user reports. |
| R21 (silent migration loss) | A9 explicitly accepts. F1 is the post-A13 reframing of this for the install-routine surface. |

### New risks introduced by A13 / late spec revisions (not in prior register)

| New risk | Source |
|---|---|
| F1 (orphan accumulation) | A13 install routine is NEW/UPDATE/SKIP only; deletes forbidden |
| F2 (SDK API drift unverified) | §12.2 explicit waiver |
| F3 (symlink-traversal write at install target) | A13 install routine does not check `is_symlink` |
| F4 (disable-doesn't-uninstall UX trap) | A13 toggle semantics + §7.3 helper text |
| F5 (d55d8c0 lookalike rewrite) | A8 drop + structural rewrite framing |
| F8 (bundle filename safety) | A13 install routine relies on `*.md` glob basename |
| F9 (no drift signal post hint deletion) | §4.6 deletes ContextDocsDrift + context_docs_outdated |
| F10 (line-ending fragility) | A13 SKIP comparison is bytes-equal |

---

## §4 Blockers vs nice-to-haves

### Blockers (CRITICAL/HIGH that should be resolved before implementation phase)

- **F1 (orphan accumulation, CRITICAL)** — needs either install-routine cleanup OR documented manual `rm` step. The spec's current "MUST NOT delete" stance creates a long-tail support tail. Resolvable via two-line spec amendment.
- **F2 (SDK API drift unverified, HIGH)** — needs a fail-detect signal. Cheapest: `InstructionsLoaded` hook listener with WARNING on zero-load. Without this, the spec accepts an external dependency with no trip-wire.
- **F3 (symlink-traversal write, HIGH)** — needs `target.is_symlink(): target.unlink()` two-line guard in §4.3. Trivial; high-impact.
- **F4 (disable-doesn't-uninstall, HIGH)** — needs honest helper text OR uninstall-on-toggle behavior. The toggle UX as currently described misleads users.

### Nice-to-haves (MEDIUM/LOW that strengthen the spec but are not gating)

- **F5 (d55d8c0 lookalike)** — PR-description attestation line.
- **F6 (worktree symlink race)** — `try/except FileExistsError`.
- **F8 (bundle filename safety)** — explicit top-level glob + name regex validation.
- **F9 (drift signal)** — settings-screen status line for install result.
- **F10 (line-ending fragility)** — normalize SKIP comparison.
- **F11 (`_workflows_dir` removal completeness)** — grep-zero acceptance bullet.

### Accepted-as-tradeoff (surfaced for user awareness only)

- **F7** (rm-rf-symlink hazard) — pre-existing for `.claude`; doubled by `.claudechic`; user-education only.
- **F12** (prefix unilateral claim) — appendix-documented; reversal-trigger candidate.
- **F13** (`.claude` mkdir on fresh-user) — vacuous in practice given Claude Code prerequisite.
- **F14** (appendix cosmetic) — non-operational.
- **F15** (busy-agent phase-advance) — pre-existing pattern.

---

## §5 Verdict

**READY WITH FIXES.**

The spec is operationally complete and the A13 simplification is the right call. The four blocker items in §4 are small, well-scoped additions to the spec text — none requires architectural redesign:

- F1 / F4 — one paragraph in §4.3 + corrected helper text in §7.3 (or a behavioral change to the toggle).
- F2 — one paragraph in §12.2 reversing the "no verification" stance, plus an `InstructionsLoaded` hook listener spec.
- F3 — two lines in §4.3 illustrative code.

The user's verbatim acceptance of A13 ("approve option B, fine with all answers. I want to copy as default and the settings have a way to desable that.") covered the install-on-default + toggle-to-disable architecture. It did not explicitly cover the orphan-accumulation, SDK-fail-detect, symlink-traversal, or honest-toggle-text aspects — those are downstream consequences the user should see flagged before the spec is locked.

If the coordinator confirms F1–F4 are out-of-scope-for-this-run, the verdict revises to **READY** with the four findings logged as known issues. If F1–F4 are in scope, they should be addressed in the spec text before implementation begins.

Per §14.3 vocabulary checklist line "lost work" enumerates all four senses on first mention in risk sections — this review's L10.d (intent lost) usage in F1 and F5 is the closest to that sense; F2 and F4 are L10.b/c (features non-functional / reverted in conflict resolution analog: the toggle's stated effect doesn't match its actual effect).

---

*End of fresh review.*
