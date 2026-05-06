# diff_review_ux -- STATUS

**Project:** diff_review_ux
**Working dir:** /groups/spruston/home/moharb/claudechic
**Artifact dir:** /groups/spruston/home/moharb/claudechic/.project_team/diff_review_ux
**Branch:** develop
**Created:** 2026-05-03

## Current Phase

**Testing-implementation** (CP-A/B/C four-lens GREEN; M1 manual PASS at 2026-05-04 against commit `cb87dd1`; ready to advance to documentation/sign-off).

## M1 Manual Verification

**M1 manual: PASS at 2026-05-04 by user (boazmohar / Boaz Mohar). Tested against `cb87dd1` (post-fix for `f`-skips-2). Pre-conditions: footer color (orange keybinding letters), directory headers with fold/hide, `f` advances focus by exactly 1, session-persistence within session, session-lifetime invariant (hides cleared on claudechic exit) all confirmed.**

Three production fixes shipped during testing-implementation phase that the existing 849 unit tests had missed:
- `ba94233` -- App.on_key keyboard intercept consumed `s f d r j k` on every screen.
- `3183617` -- `r`-from-empty-state didn't move focus per s6.2.
- `ddd6193` -- `get_changes` early-return short-circuited untracked scan when tracked diff was empty.

Plus three additional fixes from M1 manual verification rounds:
- `b01613f` -- DiffScreen missing Footer + Header + sidebar-click-syncs-DiffView-focus.
- `7935216` -- Footer color + directory headers (fold + hide affordances).
- `cb87dd1` -- `f`-skips-2 (focus-advance double-counting after refresh_hide).

### v6 redirect (this round)

User clarified at the Spec user-checkpoint that #18 was misframed -- the actual symptom is the chat-screen `FilesSection` accumulating files (duplicate of #11), not a missing DiffScreen widget. DiffHeader dropped entirely. Replaced with: prune `FilesSection` on `/diff` invocation. Basis = HEAD via `git status --porcelain -z`. Prune-only. Trigger = `/diff` only.

Skeptic surfaced two non-obvious traps that are now hard-locked in SPEC.md s3.1:
- R1 (P0): prune basis must be HEAD, never the user's `/diff` target.
- R2 (P1): `get_changes` and `get_file_stats` truncate untracked at `MAX_UNTRACKED_FILES` = 4; reusing either for prune would silently drop just-Written untracked files when the tree has 5+ untracked.

Composability verified R2 in code (lines 141-142 of features/diff/git.py) and proposed `get_dirty_paths(cwd)` helper running `git status --porcelain -z` directly. Adopted.

#19 (sort modes) and #20 (hide mechanism) are unchanged from v5.

## v4 locked decisions (Specification input)

- **#18 source command**: new `DiffHeader` widget at top of DiffScreen; renders `$ git diff <target>` + `sort: <mode>` + `hidden: N` (latter clickable -> un-hide all). Specification phase reproduces the bug first; #18 is most likely missing-feature, not wiring bug.
- **#19 sort**: modes `alphabetical` and `directory`. Default = `directory`. Persisted per-repo in `<repo>/.claudechic/`. Sort change uses in-place DOM reorder (`move_child`), preserving `HunkWidget` instances and their hunk comments.
- **#20 hide**: three-set state, app-scoped `dict[cwd, HideState]` where `HideState = (hide_files, hide_prefixes, force_visible)`. Resolution: file hidden iff `path in hide_files` OR (prefix match AND `path not in force_visible`).
  - In-memory only; gone on claudechic exit.
  - Repo key: raw cwd (no symlink/git-toplevel resolution; revisit if real-world breakage).
  - New descendants of hidden prefixes inherit hidden unless force-visible.
  - Hidden files: gone from DiffView (`display:false`); rendered greyed + struck-through in their natural sidebar slot.
  - Click greyed entry to un-hide (per-file: remove from `hide_files`; prefix-greyed: add to `force_visible`).
  - Sidebar items stay non-focusable in v1; granular un-hide is mouse-only. Keyboard-only escape: `r`.
- **Keybindings (Textual `BINDINGS`)**:
  - `s` toggle sort
  - `f` hide current file
  - `d` hide directory of focused file (no confirm prompt at any size)
  - `r` un-hide all (clears all three sets)
  - Existing `j k up down enter o q escape` migrated from `on_key` to `BINDINGS` so footer help is complete.
- **Visual**: hidden = `.` status letter + `$text-muted` + strike. No collision with `HunkWidget.has-comment` border. ASCII only.
- **Focus policy**: hide -> next visible hunk (forward bias, fallback prev, fallback empty-state). Un-hide does not jump focus.
- **Empty-state DiffView text**: "All N files hidden. Click any greyed entry in the sidebar to un-hide it, or press r to reset all hides."
- **Branch**: develop.
- **Deferred to v1+1**: keyboard nav onto hidden entries for granular un-hide; clickable directory group headers; badge flash on toggle; <60-col two-row stack.

## Issues addressed

- GH #18 -- Bug: Diff panel shows content but diff command is empty
- GH #19 -- Feature: Sort by directory in diff view
- GH #20 -- Feature: Show/hide review checkmark toggle (files + directories)

## Phase log

### Vision -- APPROVED 2026-05-03 (v4 after two redirects)
- v1: initial 3-issue framing approved.
- v2: user added directory-level checkmarks to #20.
- v3 (mid-Leadership redirect): user dropped "reviewed" semantics entirely; #20 became plain file/dir hide-show.
- v4 (current, approved): hide state is in-memory only (per-session, per-repo within session); sort mode persisted per-repo. No reviewed semantics anywhere.
- UIDesigner had been spawned with v2 brief; was halted mid-design and stands by idle awaiting v4 brief.

### Setup -- IN PROGRESS 2026-05-03
- working_dir confirmed: /groups/spruston/home/moharb/claudechic
- Existing `.project_team/` projects (abast_accf332_sync, issue_23_path_eval) -- unrelated, ignored.
- Switched branch: main -> develop (clean working tree, up to date with origin/develop).
- artifact_dir set: /groups/spruston/home/moharb/claudechic/.project_team/diff_review_ux
- userprompt.md and STATUS.md created.
- Git: present, develop branch up to date with origin.

## Open questions for later phases

- (Specification) Root cause of #18 -- where does the diff-command field get populated, and why is it empty?
- (Specification) Persistence scope for sort mode + checkmark state -- per-repo or global config?
- (UIDesigner) Directory-checkmark visibility/behavior when sort mode is flat-alpha.
- (UIDesigner) Reviewed items: hard-hide vs. dim, identical or different rules for files vs. directories?

## Team roster

- Composability (Leadership) -- spawned, reported
- Terminology (Leadership) -- spawned, reported
- Skeptic (Leadership) -- spawned, reported
- UserAlignment (Leadership) -- spawned, reported
- UIDesigner (supporting) -- spawned in Leadership phase, working on design questions A-H
- Researcher -- not spawned (no prior art / external libraries needed)
- LabNotebook -- not spawned (no experiments / iterative hypothesis testing)
- Implementer(s), TestEngineer -- to be spawned in later phases

## Leadership phase summary (complete)

### Cross-Leadership agreements that survive the v3/v4 redirect

- **#18 needs reproduction first.** Composability, Terminology, Skeptic all independently arrived at this. Specification MUST reproduce and identify the actual widget before any code change.
- **Sort mode persistence:** per-repo (user upgraded from "global" in v4).
- **Compositional invariant:** sort and hide are orthogonal presentation axes. Sort/visibility/focus are orthogonal.
- **Focus must key on `(path, hunk_idx)`**, not display index, to survive regrouping/hide.
- **Sort change must do in-place DOM reorder, never rebuild DiffView** -- comments live on `HunkWidget` instances and would be lost. (Still binding.)
- **Keep name `DiffScreen`** (no rename refactor).
- New canonical terms: **source command** (the `git diff HEAD` string for #18), **sort mode** (alphabetical | directory), **hide state** (per-file boolean, in-memory only).
- Hide controls live on `DiffFileItem` in `DiffSidebar`, NOT chat-screen `FileItem`.

### Cross-Leadership work invalidated by v3/v4 redirect (do NOT carry forward)

- All "reviewed state" architecture (Composability axis 4, ReviewStore protocol).
- Tri-state derivation rules (full/none/indeterminate) -- replaced by simple binary hide.
- Persistence layer for review state, content_sha keying, GC, rename migration (Skeptic P1 #4, #5, #7).
- "Reviewed visibility" hide-vs-dim term -- collapsed to single hard-hide.
- "Mark as reviewed" keybinding -- replaced by "toggle hide".
- UserAlignment gaps 1, 4 -- moot.
- Question of global vs per-repo sort -- resolved to per-repo.

### Specification user-checkpoint queue (post-v4 redirect)

When we hit the Specification user checkpoint, the user must decide / confirm:

1. **#18 repro** -- confirm the actual widget identified by Spec investigation; sign off on minimum-scope fix.
2. **Default sort mode** on first run (alphabetical was assumed; confirm).
3. **Sidebar UX for hidden files** -- UIDesigner's proposal (collapsed group / ghosted entry / dedicated "hidden" subsection / etc).
4. **Keybindings** -- UIDesigner proposes; user approves.
5. **Where hide-state in-memory store lives** -- on `DiffScreen` instance (dies on screen dismiss) vs on `App` (survives DiffScreen close, dies on claudechic exit). Both honor user's "gone on claudechic exit"; the screen-vs-app distinction affects whether closing+reopening DiffScreen within one session preserves hides.

### Skeptic risk register (filtered for v4 scope)

P0 (architecture-binding, ALL still active):
- #18 may be wrong screen.
- In-place DOM reorder for sort change (preserve `HunkWidget` instances and their comments).
- `_sanitize_id` collisions.

P1 (still active):
- DiffSidebar/DiffView source-of-truth split for changes -- a single controller on DiffScreen for sort and hide state.
- Untracked files participate uniformly in directory grouping and hide.

P2 (still active):
- Hide + focus interaction -- focus moves to next visible hunk on hide.
- Sidebar items not focusable today (`DiffFileItem` is `Static`).
- Sidebar `.hidden` below 100 cols -- toggle controls must remain reachable.
- Keybindings via `BINDINGS`, not `on_key`.
- Hidden files with in-progress comments -- comments still returned on dismiss; surface a "N hidden files have comments" hint.

P3 (still active):
- target != HEAD must be reflected in source command.
- Accessibility of any new glyph (ASCII-only).

P1/P2 retired by v4: content_sha keying; rename-detection migration; per-repo settings file design; indeterminate state interactions.

### Specification exit criteria (filtered for v4)

- Repro of #18 with the exact widget identified.
- Hide-state model: where the in-memory store lives (DiffScreen vs App), per-repo keying within session, behavior on `/diff` re-run.
- Sort-mode persistence spec: file path under `<repo>/.claudechic/`, schema, default value.
- Focus-policy spec for hide actions.
- Keybinding table for new toggles.
- Commitment to in-place reorder (preserve `HunkWidget` instances and their comments) on sort change.

### Advisories carried into downstream phases

- Directory-level hide treated as user-required, not optional (a single bulk action over descendants).
- #18 fix stays scope-minimal; no broad DiffScreen state refactor.
- UIDesigner must reconcile any new hide-state visual with `HunkWidget.has-comment` border-color (collision risk).
- Sidebar must surface hidden files (UX form delegated to UIDesigner) so user has an un-hide path.
