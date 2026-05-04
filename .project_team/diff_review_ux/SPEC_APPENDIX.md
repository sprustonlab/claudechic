# diff_review_ux -- Specification Appendix

> Historical / rationale document. Canonical naming lives in `specification/terminology.md`; this file may use earlier draft terms (e.g. `un-hide`, `in-memory only`, `A1`, `NV2`) for rationale or chronological context. Operational contract is `specification/SPECIFICATION.md`.

Non-operational context for SPECIFICATION.md. Implementer agents do not need to read this file. Architecture rationale, rejected alternatives, and Vision history.

## A. Vision history

- **v1**: 3-issue framing approved.
- **v2**: user added directory-level checkmarks to #20 (review-state with tri-state).
- **v3**: user dropped "reviewed" semantics entirely; #20 became plain file/dir hide-show; per-repo persistence.
- **v4**: hide state moved to in-memory only (per-session); sort mode persisted per-repo. No reviewed concept.
- **v4.1**: keybindings revised to `s f d r` (no case pairs); DiffHeader mocks delivered.
- **v4.2**: hidden entries stay in their natural sidebar slot, greyed and struck (option A); separate "Hidden (N)" group rejected.
- **v4.3**: three-set hide model (`hide_files`, `hide_prefixes`, `force_visible`) with `force_visible` override only on prefix hides.
- **v6** (current, approved): user clarified at the Spec user-checkpoint that #18 was misframed as a DiffScreen bug. The actual symptom is the chat-screen `FilesSection` accumulating files without prune (same bug as #11). DiffHeader is dropped entirely. Replaced with: prune `FilesSection` on `/diff` invocation, basis = HEAD via `git status --porcelain -z`, prune-only (never adds), simple. #19 and #20 unchanged.

### A.1 Term provenance details

`hide state`, `sort mode`, `HideStore`, `SortModeStore`, `force_visible`, `hide_files`, `hide_prefixes`, `DisplayTree`, `FileNode`, `DirectoryNode`, `_to_prefix`, `_path_to_id`, `dirty path set`, `get_dirty_paths` are team-coined names. They were approved as a package by user acceptance of Vision v4 / v5 / v6 (see A above). User-facing wording uses only `hide`, `unhide`, `hidden`, `visible`, `sort by directory`, `sort alphabetically`, plus per-tooltip phrasings defined in SPECIFICATION.md s7. The internal-vs-user-facing rule itself is encoded as a forbidden pattern in SPECIFICATION.md s3.1.

## B. Why three sets, not one or two

A single `set[str]` of hidden paths cannot express "anything new under `src/` should also be hidden." The user explicitly required new descendants of a hidden directory to inherit hidden -- this is the prefix axis.

A two-set model (per-file + prefixes) cannot express "I hid `src/` but I want to keep `src/foo.py` visible." Clicking `src/foo.py` would have to either un-hide the entire prefix (option A1, rejected) or have no effect. The user explicitly chose to allow per-file overrides.

Hence three sets, with `force_visible` overriding prefix membership only.

## C. Rejected alternatives

### C.1 Persistent hide state (rejected after v3)

Original v3 proposal kept hide state per-repo on disk. User redirected to in-memory only ("when claudechic is close and open again I don't want files to stay hidden"). Removed all `content_sha`, GC, rename-detection complexity that Skeptic had flagged in v2.

### C.2 Reviewed-checkmark feature (rejected after v3)

Original v2 had files marked "reviewed", with tri-state directory rollups. User redirected to plain hide/show ("please remove the reviewed state as a feature"). All review semantics, tri-state, hide-vs-dim, and reviewed-state-invalidation work was discarded.

### C.3 Separate "Hidden (N)" sidebar group (rejected at v4.2)

UIDesigner v4/v4.1 proposed a collapsible `[+] Hidden (N)` group at sidebar bottom. User rejected: directory grouping should be respected. Adopted option A: hidden entries stay in their natural sidebar slot, greyed.

### C.4 DiffScreen-scoped HideStore (rejected at NV1)

Skeptic flagged that "hidden file reappearing in a later /diff returns hidden" requires the store to outlive a single DiffScreen instance. App-scoped store is the only consistent choice.

### C.5 Symlink / git-toplevel resolution for repo key (rejected)

User: "we don't cd into anywhere, we should just be here and not care about symlinks until we care." Repo key is the raw cwd DiffScreen receives at construction.

### C.6 Per-prefix click-un-hide variants A1 and A3 (rejected at v4.3)

A1 (clicking a prefix-greyed file removes the entire prefix): rejected -- user wanted siblings to stay hidden.
A3 (clicking expands the prefix into per-file entries for siblings, then drops the file): rejected -- it would lose the "auto-hide future descendants" property that the user wanted.
A2 won.

### C.7 Confirmation prompts on `d` for large directories (rejected)

User: "no prompts please, keep simple."

### C.8 Badge flash on toggle (rejected)

User asked to remove from v1.

### C.9 Per-action undo (`u`) (rejected at v4.1)

Replaced by reset-only (`r`). The sidebar lets the user un-hide any specific entry by clicking; per-action undo is redundant.

### C.11 DiffHeader for #18 (rejected at v6)

The earlier spec proposed a `DiffHeader` widget on DiffScreen rendering `$ git diff <target>` plus `sort: <mode>` and `hidden: N` badges. Designed in good faith based on Leadership's reading of #18 as "DiffScreen has no widget showing the originating git command." At the Spec user-checkpoint the user clarified #18 is actually about FilesSection accumulation -- a different bug on a different screen. DiffHeader was solving a problem the user did not have. Dropped entirely.

Replaced with: prune FilesSection on `/diff` invocation (s8 of SPECIFICATION.md). The Skeptic R1 (HEAD-relative basis) and R2 (don't reuse `get_changes` because of `MAX_UNTRACKED_FILES` truncation) constraints are locked into the new spec.

### C.10 Case-sensitive keybinding pairs (rejected at v4.1)

User: "u vs U is not good." All bindings now lowercase, no case pairs.

### C.12 s8.5 rationale: FilesSection prune-only

FilesSection's semantic is "files Claude edited in this conversation", not "files currently dirty in the working tree." The prune step therefore never adds entries from `git status` that are not already tracked by FilesSection. Files modified externally (e.g. user runs `git checkout` mid-conversation) must not be added by this path. The operational rule lives in SPECIFICATION.md s8.5; this section captures the semantic motivation.

### C.13 MAX_UNTRACKED_FILES side-fix history

`claudechic/features/diff/git.py:88` defined `MAX_UNTRACKED_FILES = 4`. `get_changes` (line ~221) gated the entire untracked-append loop on `len(untracked) <= MAX_UNTRACKED_FILES`. When more than four untracked files were present, the loop was silently skipped: zero `FileChange` entries were created for any untracked file, no log, no error.

User-facing symptom: DiffScreen rendered "No uncommitted changes" even when untracked files existed, because `get_changes` returned an empty list. Reproduced at the Spec user-checkpoint with three untracked entries that recursively expanded to >4 files via `git ls-files --others --exclude-standard`.

`get_file_stats` (chat-screen sidebar caller; line ~141) had the same silent-skip cap and the same semantic.

#### Risk envelope (post-fix)

Worst case after the fix: a working tree with thousands of untracked files (e.g. missing `.gitignore` for a build-output directory) produces a multi-MB synthetic diff. The user sees a long DiffScreen rather than a misleading empty-state. This is the desired failure mode -- a missing `.gitignore` is a real-world bug the user should see, not one we should silently mask.

### C.14 _path_to_id rationale

`_sanitize_id` (the pre-fix function in `widgets.py`) mapped `/`, `.`, and ` ` to `-`. Two paths `a/b.py` and `a-b-py` collided to the same id. The DOM id space is the seam between focus key and Textual widgets; collisions cause focus-jump and click-target bugs. The hex encoding adopted in SPECIFICATION.md s13 is `[0-9a-f]+` -- a valid CSS id suffix and a bijection with the path.

### C.15 Footer help canonicality

Footer help is the canonical keyboard-discoverable surface for all DiffScreen actions (`s f d r` plus existing keys). Tooltips on DiffSidebar greyed entries are best-effort mouse-discoverability hints; they are not the primary discovery path. Keyboard-only users discover every action via the footer help. The operational rule (`BINDINGS`, not `on_key`) lives in SPECIFICATION.md s11; this section captures the discoverability rationale.

## D. Carried-forward Skeptic risks

- **P0 #18 may be wrong screen** -- mitigated: DiffHeader is a new widget; `git diff` source command is rendered there. Not a wiring fix to a phantom field.
- **P0 in-place DOM reorder** -- mitigated: SPEC s4.5 mandates `move_child`; SPEC s9.3 tests for `HunkWidget` instance identity across sort toggle.
- **P0 `_sanitize_id` collisions** -- mitigated: SPEC s8.1 mandates replacement.
- **P1 single source of truth on DiffScreen** -- mitigated: SPEC s8.7.
- **P2 narrow-screen sidebar hides un-hide affordance** -- mitigated: clickable `hidden: N` badge in DiffHeader, `r` keybinding always available.
- **P2 BINDINGS, not on_key** -- mitigated: SPEC s6.
- **P3 source command for non-default target** -- mitigated: SPEC s3.3 references `DiffScreen.target`.
- **NV2 directory snapshot vs prefix** -- decided: prefix.
- **NV3 repo key choice** -- decided: raw cwd.
- **NV5 escape valve** -- decided: `r` keybinding + clickable badge.
- **NV8 `--resume` does not preserve hides** -- documented as known non-feature.
- **NV9 hide state monotonic over session** -- accepted; `r` provides bulk reset.

## D.tris SPEC.md location

The operational spec lives at `specification/SPECIFICATION.md` (workflow advance check expects this filename). `SPEC_APPENDIX.md` (this file) remains at the artifact root.

## D.bis SPEC.md v2 merge

Composability produced a parallel architectural deliverable (`specification/composability.md`) during Specification phase. Its contributions were merged into SPEC.md v2 verbatim where operational, including: `DiffSource` frozen dataclass; `HideStore` and `SortModeStore` as Protocol classes with explicit method signatures; `DisplayTree` with `FileNode | DirectoryNode`; module split into `sort.py`, `hide.py`, `tree.py`, `header.py`; explicit import-direction rules; `_path_to_id` hex encoding; focus contract methods (`current_focus_key`, `next_visible_after`, `prev_visible_before`); crystal test table; sort-mode persistence file moved from `config.yaml` co-tenancy to a dedicated `<repo>/.claudechic/diff.yaml`. Composability's appendix rationale points (A.1-A.5 in their doc) are subsumed by C.* and the operational decisions in SPEC.md.

## E. Out-of-scope catalog

The following are not addressed by SPECIFICATION.md and require a follow-up project:

- Persisting hide state across claudechic processes.
- Rename or content_sha keying of hide state.
- Cross-repo hide state sharing.
- Hide of individual hunks (only files and prefixes are hidable).
- Reviewed-state semantics (tri-state, derived directory state).
- Keyboard navigation onto hidden sidebar entries (mouse-only unhide in v1; `r` is the keyboard escape).
- Clickable directory group headers.
- Dismiss-time "N hidden files have unsaved comments" notice.
- Rendering the originating `git diff` command anywhere (DiffHeader retracted; see C.11).
- FilesSection refresh on any trigger other than `/diff` (Bash hook, polling, separate command, all out of scope).
- FilesSection adding files from git state at `/diff` time (prune-only).

## F. Deferred to v1+1

Items the user accepted as out-of-scope-for-now:

- Keyboard navigation onto hidden entries for granular un-hide.
- Clickable directory group headers (e.g. fold/unfold).
- Visual flash on DiffHeader badges.
- Two-row stacked DiffHeader at <60 cols.
- Differentiating prefix-hidden from per-file-hidden visually (only tooltip differs in v1).

## G. Vision text (v4 final, approved)

(Inlined from `userprompt.md` for archival; do not edit here -- edit there if Vision text changes.)

> Goal: Address GitHub issues #18, #19, #20 -- fix the empty source-command field, add sort-by-directory, and add a simple file/directory hide-show mechanism.
>
> Value: Reviewers get (a) self-documenting diff metadata, (b) directory-grouped scanning, (c) ability to suppress noise within their current claudechic session.

## H. Cross-Leadership convergences (historical)

Every cross-Leadership agreement reached during the v4 redirect is encoded in SPECIFICATION.md (section refs below are from a pre-v6 numbering and may not match the current document):

- Single source of truth on DiffScreen for sort and hide -- s8.7.
- `(path, hunk_idx)` keying for focus -- implicit in s5.5 ("first hunk of the next visible file").
- In-place DOM reorder, no rebuild -- s4.5.
- `DiffSource` value pattern (single function returns `(changes, command_str)`) -- s7 ("a single helper returning `(changes, source_command)`").
- App-scoped HideStore keyed by cwd -- s5.4.
- No `.hidden` on `FileChange` -- s8.5.
- Hide visual identical regardless of source -- s5.6.

## I. Test surface (Testing-phase reference)

> Reference for the Testing-phase agent. Implementers do NOT write these tests; the Testing phase does. Implementers must satisfy the operational contracts in SPECIFICATION.md (s5.5.1 truth table, s8.8 edge-case table, s6.4 empty-state placeholder text, s7 tooltips, s10 in-place reorder rules, etc.); the test surface below is what Testing will assert against those contracts.
>
> Workflow tests reference SPEC.md sections by their current numbering; if SPEC.md numbering shifts, fix the refs here. "Absorbs prior" annotations preserve traceability to the fine-grained tests that an earlier draft listed and that this surface deliberately consolidates.

### I.1 Unit tests (pure-function contract surface)

- `test_is_hidden_truth_table`: full eight-row truth table over `(P in hide_files, prefix matches P, P in force_visible)`. Includes the lookalike row: `hide_prefixes = {"src/"}` does NOT hide `"src_old/foo.py"`.
- `test_to_prefix_helper`: `_to_prefix("src/foo.py") == "src/"`; `_to_prefix("src/sub/foo.py") == "src/sub/"`; `_to_prefix("README.md") is None`.
- `test_path_to_id_round_trip`: `_path_to_id("a/b.py")` and `_path_to_id("a-b.py")` produce distinct ids; both round-trip via `bytes.fromhex(...).decode("utf-8")`.
- `test_get_dirty_paths_parsing`: `git status --porcelain -z` output containing `R old\0new` yields `new` (destination only); subprocess failure / non-git directory yields empty set without raising.
- `test_sort_mode_store_round_trip`: `set("directory")` then `get()` returns `"directory"`; missing file -> `"directory"`; invalid YAML value -> `"directory"` plus a logged warning.

### I.2 Workflow tests (user-observable transitions)

Each test mounts DiffScreen (or the App for prune workflows) and exercises the full keyboard / click path. Internal subprocess calls are mocked at `git`'s output where applicable.

- **WF1 `test_hide_and_unhide_file_via_keyboard_and_click`**: open `/diff` with three files; focus the middle file; press `f` -> middle file is greyed in DiffSidebar, its `FileDiffPanel` has `display = False`, focus advances to the next visible file (forward-bias rule). Click the greyed entry in DiffSidebar -> file is no longer greyed, panel re-displays. Asserts: hide-file state transition, sidebar greyed render, focus-advance policy, click-unhide path. Absorbs prior `test_focus_advances_on_hide` plus per-file hide/unhide mechanics.

- **WF2 `test_directory_hide_with_force_visible_and_root_file_edge`**: tree contains `src/a.py`, `src/b.py`, `README.md`. Focus `src/a.py`, press `d` -> both `src/*` files are greyed and gone from view; `hide_prefixes = {"src/"}`. Click `src/b.py` -> only `b.py` un-greys; `a.py` stays hidden (force_visible scoped to `b.py`). Mount a fresh DiffScreen with an extra `src/c.py` and the same HideStore -> `c.py` renders hidden by default (new-descendant inheritance). Focus `README.md`, press `d` -> no-op; HideStore is unchanged; transient footer hint surfaces (root-file edge). Absorbs prior `test_new_file_under_hidden_prefix_is_hidden`, `test_root_file_d_is_noop`, plus prefix + force_visible mechanics.

- **WF3 `test_sort_toggle_preserves_focus_and_comments`**: open `/diff` with files spanning multiple directories; type a comment on a specific hunk; record `(focus_key, HunkWidget id, comment_text)`; press `s` to flip sort mode -> `HunkWidget` instance identity is preserved (same Python `id()`), comment text is preserved, focus_key still resolves to that same `HunkWidget`. Absorbs prior `test_focus_survives_sort_change`; locks the in-place reorder contract from SPEC.md s10.

- **WF4 `test_reset_clears_hides_and_restores_empty_state`**: hide every file (mix of `f` and `d`); DiffView shows the empty-state placeholder text from SPEC.md s6.4; press `r` -> all three sets cleared, every file visible, focus lands on the first hunk of the first file. Absorbs prior `test_empty_state_appears_and_clears` plus reset state-clear semantics.

- **WF5 `test_hide_store_isolation_and_survival`**: open `/diff` in cwd A, hide files, dismiss the screen; re-open `/diff` in cwd A within the same App -> hides preserved. Open `/diff` in cwd B -> no hides leaked from cwd A. Absorbs prior `test_hide_store_per_cwd_isolation` and `test_hide_store_survives_screen_close_reopen`.

- **WF6 `test_diffscreen_renders_many_untracked`**: tree with six untracked files and zero tracked changes; open `/diff` -> all six file rows render in DiffSidebar and DiffView; the "No uncommitted changes" empty-state is NOT shown. Single test exercises both `get_changes` and `get_file_stats` because both call into the s8a fixed code path. Regression for the s8a side-fix; absorbs three prior fine-grained tests covering `get_changes`, `get_file_stats`, and DiffScreen render.

- **WF7 `test_filessection_pruned_after_commit`**: Claude edits `foo.py` via the Edit tool path -> FilesSection gains a row for `foo.py`. User commits via Bash. Open `/diff` -> `_prune_files_section_to_git` runs once before `push_screen`; FilesSection no longer shows `foo.py`. If FilesSection becomes empty, the `.hidden` class is applied. Absorbs prior `test_files_section_prune_drops_stale`, `test_files_section_prune_hides_when_empty`, `test_prune_runs_on_diff_open`.

- **WF8 `test_prune_basis_is_HEAD_not_target`**: branch is N commits ahead of `origin/main`; Claude previously edited and committed `foo.py`; FilesSection still has `foo.py` (added pre-commit). Tree also has six untracked files, one of them Claude-`Write`d and tracked in FilesSection. Open `/diff` with `target="origin/main"` -> prune uses `git status --porcelain -z` (HEAD-relative); `foo.py` is pruned (clean vs HEAD even though it appears in `/diff` vs origin/main); the Claude-Written untracked file is kept (it IS in `git status`, untruncated by s8a fix). Regressions for R1 and R2.

- **WF9 `test_prune_never_adds_externally_modified_file`**: tree contains `bar.py` modified externally (never edited by Claude in this session, never in FilesSection). Open `/diff` -> FilesSection does NOT gain `bar.py`, even though it is in `git status`. Absorbs prior `test_files_section_prune_does_not_add` and `test_prune_does_not_add_externally_modified_file`.

### I.3 Visual archetypes

A small parameterized rendering test asserts the cross-product of sort mode and HideState archetype renders correctly. Two archetypes cover the rendering paths not exercised by WF1 / WF2:

| # | Sort         | HideState archetype                                                | Expected visual                                          |
|---|--------------|--------------------------------------------------------------------|----------------------------------------------------------|
| 1 | alphabetical | `hide_prefixes = {"tests/"}`                                       | every `tests/...` row greyed and gone from view; non-`tests/` files render normally in flat-alpha order |
| 2 | directory    | `hide_files = {"x/y.py"}`                                          | grouped tree under `x/`; only `y.py` greyed; sibling files in `x/` render normally |

### I.4 Manual verification

- Hide files, quit claudechic, relaunch -> all files visible (verifies session-vs-process lifetime; not automatable in unit tests).

---

## J. CP2 verdict override: directory header rendering

**Original CP2 verdict (verbatim from spec checkpoint):**

> "In `directory` mode the `DisplayTree` carries `DirectoryNode` grouping internally, but the sidebar in v1 renders flat -- files are clustered by parent directory through the sort order, but no header rows are rendered. This avoids visual chrome and keeps the click-on-directory-bulk-hide design space open for a future iteration."

**M1 manual test finding (user override):**

At M1 manual sign-off the user ran the implementation with the flat rendering and directly observed that without directory header rows the directory sort mode was indistinguishable from alphabetical sort at a glance -- the clustering benefit was invisible. The user explicitly reversed the CP2 flat-render decision:

> "directory headers should render; the whole point of directory mode is to make directory grouping visually legible."

**New operational decision (post-M1):**

Directory sort mode renders one `DiffDirectoryItem` row per `DirectoryNode`. Each row carries a `DirFoldGlyph` fold toggle (`[-]`/`[+]`) and a `DirNameLabel` that also acts as a hide-prefix click target. This is now the canonical behavior; SPECIFICATION.md s4.3 and s7.2 encode the full contract.

**Why the CP2 flat-render verdict was reasonable at the time:**

The CP2 verdict prioritized implementation simplicity and explicitly deferred the click-on-directory affordance. It was a defensible scope-cut. The M1 manual test showed that the user's mental model assumed visual headers -- the absence of them produced genuine confusion about whether directory mode was doing anything at all. This is a case where user observation during manual sign-off correctly caught a design gap that neither the spec nor the automated tests could surface.

**Implications for existing tests:**

WF3 (`test_sort_toggle_preserves_focus_and_comments`) now exercises a tree that includes `DiffDirectoryItem` rows in directory mode. Existing test infrastructure can assert `DiffDirectoryItem` presence in directory mode as part of the visual-archetype table (SPEC_APPENDIX I.3).

**Note on in-place reorder scope (P0 clarification):**

The P0 invariant from SPECIFICATION.md s10 — "no remounting on sort change" — applies specifically to `HunkWidget` instances (which own `.comment`, mutable user-input state a remount would destroy) and to `FileDiffPanel` instances (which contain `HunkWidget`s). `DiffFileItem` rows are reordered via `move_child` per s10.4 for consistency.

`DiffDirectoryItem` instances are NOT bound by the P0 constraint. Their widget-instance identity carries no user-observable state: fold state lives in `HideState.folded_prefixes`, not in the widget. A remounted `DiffDirectoryItem` reads from the same `HideState` and renders identically to the preserved original. The implementation uses a hybrid approach -- `move_child` for `DiffFileItem`, remount for `DiffDirectoryItem` -- which was forced by a real `DuplicateIds` collision when attempting full preservation. This hybrid is correct and tests confirm it (14/14 passing).
