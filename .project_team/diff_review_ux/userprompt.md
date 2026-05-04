# User Prompt

Original request: "pull up the issues on github and lets address diff related issues for the vision"

Refined target: address the three open diff-related GitHub issues in claudechic together.

## In-scope issues

- **#18 (Bug) = duplicate of #11.** User clarified at the Spec user-checkpoint that #18 is NOT about DiffScreen -- it is about the chat-screen `FilesSection` (right-side panel of the main window) accumulating files without pruning after commit. Same bug as #11. Filed twice.
- **#11 (Bug)** -- `FilesSection` sidebar accumulates every edited file across a session (no cap / no prune). Closes with #18 in this project.
- **#19 (Feature)** -- Add a "sort by directory" option to the diff view, alongside the existing alphabetical ordering. Default on first run: `directory`.
- **#20 (Feature)** -- Add a hide/show mechanism for files and directories in the diff view. **Simplified scope: plain hide/show, NOT a "reviewed" tracker.** Hidden files vanish from `DiffView`; they render greyed-and-struck in their natural slot in `DiffSidebar` so they can be un-hidden by click. Hide state is session-scoped (in-memory only; cleared when claudechic exits) and repo-keyed within the session.

## User decisions captured (v5)

1. **Scope:** all three issues in one project.
2. **Sort mode (#19) persistence:** per-repo, written to `<repo>/.claudechic/diff.yaml` (dedicated file; not co-tenant with `config.yaml`). Default on first run: `directory`.
3. **Hide state (#20) persistence:** session-scoped, in-memory only. App-scoped `dict[cwd, HideState]` on `ChatApp`. Resets on claudechic exit. Within a session, hide state persists across `/diff` re-runs in the same repo. No cross-repo leakage.
4. **Hide state model:** three sets per repo -- `hide_files` (per-file hides via `f`), `hide_prefixes` (directory prefixes via `d`; new descendants of a hidden prefix inherit hidden), and `force_visible` (per-file un-hides via clicking a prefix-greyed entry; overrides prefix membership only, not `hide_files`).
5. **State semantics on `/diff` re-run within one session:**
   - Previously hidden file still in the diff -> stays hidden.
   - File new to the diff and NOT under any hidden prefix -> starts visible.
   - File new to the diff AND under a hidden prefix -> starts hidden (inherits via prefix).
   - Closing claudechic -> all hide state gone.
6. **Hide visual treatment:** hidden files gone from `DiffView` (`display: false`); rendered in-place in `DiffSidebar` as greyed-and-struck (`.` status letter, `$text-muted`, `text-style: strike`). Click any greyed entry to un-hide. No separate "Hidden (N)" sidebar group.
7. **Directory-hide is single-key, no confirmation prompt at any size.** `d` adds the focused file's parent directory (with trailing `/`) to `hide_prefixes`.
8. **No "reviewed" semantics.** No tri-state checkmarks. No content_sha. No rename migration.
9. **Branch:** work on `develop`.
10. **Keybindings (Textual `BINDINGS`)**:
    - `s` toggle sort mode (alphabetical <-> directory)
    - `f` hide focused file
    - `d` hide directory of focused file
    - `r` reset hide state (clears all three sets)
    - existing `j k up down enter o q escape` migrated from `on_key` to `BINDINGS` so footer help is complete
    - no case-sensitive pairs; no lowercase `h` (vi-left collision)
11. **FilesSection prune (#11/#18):** when DiffScreen is opened via `/diff`, prune the chat-screen `FilesSection` widget by removing any entry whose path is not currently dirty in the working tree. Refresh trigger is `/diff` invocation only -- no polling, no Bash post-hooks, no separate refresh command. Prune basis is **always `HEAD`** (working-tree dirtiness via `git status --porcelain -z`), independent of the `/diff` `target` argument. Prune-only -- never adds files to FilesSection from this path. Stale-until-next-/diff is an accepted limitation.
12. **Repo key (for #20 hide state):** raw `cwd` as DiffScreen receives it. No symlink resolution, no `git rev-parse --show-toplevel`. Trade-off: a single repo accessed via different paths within one session would have separate hide states; user accepted this.
13. **DiffHeader removed.** The earlier DiffHeader spec was solving a problem the user did not actually have. Dropped from this project entirely. No source-command rendering anywhere in v1.

(Spec document is at `specification/SPECIFICATION.md`.)

## Vision Summary (approved v6)

**Goal:** Address GitHub issues #11/#18 (one duplicate bug), #19, and #20 -- prune the chat-screen `FilesSection` when `/diff` is opened, add directory-grouped sort to DiffScreen, and add a simple file/directory hide-show mechanism inside DiffScreen.

**Value:** Reviewers get (a) a `FilesSection` that doesn't grow forever -- committed files disappear from the chat sidebar at the next `/diff`, (b) directory-grouped scanning inside DiffScreen, (c) ability to suppress noise inside DiffScreen within their current claudechic session.

**Domain terms (canonical):**
- **DiffScreen** -- the `/diff` full-page Textual Screen.
- **DiffSidebar** -- left pane file list inside DiffScreen.
- **DiffView** -- centre/right pane containing one `FileDiffPanel` per file.
- **FilesSection** -- chat-screen sidebar widget at `claudechic/widgets/layout/sidebar.py:FilesSection` listing files Claude edited during the conversation.
- **dirty path set** -- the `set[str]` of paths returned by `get_dirty_paths(cwd)` -- working-tree dirtiness vs `HEAD` via `git status --porcelain -z`. Untruncated. Used as the prune basis for FilesSection.
- **sort mode** -- `alphabetical` or `directory`. Persisted per-repo.
- **hide state** -- per-repo `(hide_files, hide_prefixes, force_visible)`. Session-scoped, in-memory only.
- **HideStore** -- App-scoped object holding `dict[cwd, HideState]`.
- **directory hide action** -- single key (`d`) that adds the focused file's parent directory to `hide_prefixes`.

**Success looks like:**
- #11/#18: opening `/diff` removes from `FilesSection` any entry whose path is not in the dirty path set. Files committed/reverted disappear from the chat sidebar at the next `/diff`. Untracked files Claude wrote (even when there are >4 untracked in the tree) are NOT pruned. Files modified externally that Claude never touched are NOT added.
- #19: user toggles between alphabetical and directory sort with `s`; choice persists per-repo in `<repo>/.claudechic/diff.yaml`; sort change preserves in-progress hunk comments via in-place DOM reorder.
- #20: user hides files (`f`) or prefixes (`d`); new descendants of hidden prefixes inherit hidden; per-file un-hide via click adds to `force_visible`; hidden files gone from DiffView, greyed-in-place in DiffSidebar; `r` clears all three sets; state gone on claudechic exit.
- All three pass tests, ruff, pyright; no regression in existing DiffScreen behavior; no regression in existing FilesSection add behavior.

**Failure looks like:**
- Sort change losing hunk comments.
- Hide state surviving claudechic exit (violates user intent).
- Hide state from one repo bleeding into another within the same session.
- Prune over-deletes -- e.g. drops a just-Written untracked file because the tree has >4 untracked (R2).
- Prune basis depends on the user's `/diff` target instead of HEAD (R1).
- Prune adds files Claude never touched (e.g. after `git checkout` mid-conversation).
- Keybinding clashes with existing DiffScreen bindings.
- Scope creep beyond these issues.

## Vision history

- v1: initial 3-issue framing approved.
- v2: user added directory-level checkmarks to #20.
- v3: user redirected -- drop "reviewed" semantics entirely; replace with plain hide/show; per-repo persistence proposed.
- v4: hide state moved to in-memory only (session-scoped, repo-keyed within session); sort mode persisted per-repo. No reviewed concept.
- v4.1: keybindings revised to `s f d r` (no case pairs).
- v4.2: hidden entries stay in their natural sidebar slot, greyed and struck (option A); separate "Hidden (N)" group rejected.
- v4.3 / v5: three-set hide model with `force_visible` override (option A2). Sort persistence file is dedicated `<repo>/.claudechic/diff.yaml`. DiffHeader proposed as the home for the source command. Repo key is raw cwd.
  - Verbatim user authorization for A2: *"I think A2, as I also wanted new files in a hidden folder to stay hidden"* -- locks both the `force_visible` override (per-file un-hide of a prefix-greyed entry leaves siblings hidden) AND the prefix-inheritance semantics (new descendants of a hidden prefix start hidden).
- v6 (current, approved): user clarified at Spec user-checkpoint that #18 is actually about FilesSection accumulation (duplicate of #11), NOT about DiffScreen. **DiffHeader dropped entirely.** Replaced with: prune FilesSection on `/diff` invocation. Refresh trigger is `/diff` only; basis is HEAD via `git status --porcelain -z`; prune-only (never adds). #19 and #20 unchanged.
  - Verbatim user redirect: *"This might be about the side panel on the RIGHT of the main screen, showing the changed files. they are always added but never pruned. when I commit these don't go away."* and *"Path A, we update when we press the diff button, make it SIMPLE"*.
