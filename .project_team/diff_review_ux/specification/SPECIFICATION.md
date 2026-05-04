# diff_review_ux -- Specification

Operational specification for GitHub issues #11/#18 (one bug, filed twice), #19, and #20 in the claudechic repo. All terms used here are defined in this document. Rationale, alternatives, history, out-of-scope catalog, and term provenance live in `SPEC_APPENDIX.md`.

## 1. Scope

In-scope changes:

- **#11/#18** -- Prune the chat-screen `FilesSection` widget when `/diff` is opened. Removes any entry whose path is not currently dirty in the working tree relative to `HEAD`. Refresh trigger is `/diff` invocation only; no polling, no Bash post-hooks. Prune-only -- never adds files.
- **#19** -- Two sort modes for the DiffScreen file list: `alphabetical` and `directory`. Persisted per-repo. Sort mode is changed live without rebuilding the mounted widget tree (preserves `HunkWidget` instances; see s10).
- **#20** -- A session-scoped, three-set hide mechanism on `DiffScreen`. Hidden files do not render in `DiffView`; they render visually distinct in `DiffSidebar`.
- **In-scope side-fix (s8a)** -- Lift the `MAX_UNTRACKED_FILES` count cap in `claudechic/features/diff/git.py`. Tagged as a side-fix (not #18) to avoid masquerading as a primary issue in the PR description.

Out-of-scope catalog: see SPEC_APPENDIX E.

## 2. Glossary

- **DiffScreen** -- existing Textual Screen pushed by `/diff`. File: `claudechic/screens/diff.py`.
- **DiffSidebar** -- existing left pane. File: `claudechic/features/diff/widgets.py:DiffSidebar`.
- **DiffView** -- existing centre/right pane containing one `FileDiffPanel` per file. File: `claudechic/features/diff/widgets.py:DiffView`.
- **FileDiffPanel** -- existing per-file panel inside DiffView, one per visible `FileChange`. File: `claudechic/features/diff/widgets.py:FileDiffPanel`.
- **DiffFileItem** -- existing per-file row in DiffSidebar.
- **HunkWidget** -- existing per-hunk widget owning its hunk comment in `.comment`.
- **FileChange** -- existing pure data record at `claudechic/features/diff/git.py:FileChange`. Treated as immutable.
- **FilesSection** -- existing chat-screen sidebar widget at `claudechic/widgets/layout/sidebar.py:FilesSection` listing files Claude has edited during the conversation. Internal store: `_files: dict[Path, FileItem]`.
- **target** -- the `target: str` argument of DiffScreen. Default `"HEAD"`. Used ONLY for the diff content; never as the prune basis.
- **dirty path set** -- the `set[str]` of paths returned by `get_dirty_paths(cwd)`. Working-tree dirtiness vs `HEAD` from `git status --porcelain -z`, untruncated.
- **get_dirty_paths** -- new async helper in `claudechic/features/diff/git.py` returning the dirty path set for a cwd. See s8.2.
- **SortMode** -- `Literal["alphabetical", "directory"]`. Default on first run: `"directory"`.
- **HideState** -- mutable dataclass with four string sets per repo: `hide_files`, `hide_prefixes`, `force_visible`, `folded_prefixes`. See s5.
- **repo key** -- the `cwd: Path` value passed to DiffScreen, used verbatim. No symlink resolution, no `git rev-parse --show-toplevel`.
- **HideStore** -- App-scoped object holding `dict[Path, HideState]`. Lives on `ChatApp`.
- **SortModeStore** -- per-repo persistent store reading/writing `<repo>/.claudechic/diff.yaml`.
- **DisplayNode** -- one of two variants: `FileNode(file_change, hidden)` or `DirectoryNode(prefix, children)`.
- **DisplayTree** -- `list[DisplayNode]`. Produced by `build_tree`; consumed by widgets.
- **focus key** -- the pair `(path: str, hunk_idx: int)`. Single identifier of "what hunk has focus". Survives sort change and hide toggle.
- **session-scoped** -- lives in the claudechic process; cleared when claudechic exits. Combined with the per-repo keying of `HideStore` (s5.4), the full lifetime descriptor is `session-scoped, repo-keyed`.
- **greyed** -- informal synonym for the **hidden render variant** of `DiffFileItem` defined in s7 (`.` status letter, `$text-muted`, `text-style: strike`). Permitted in user-facing copy, tooltips, empty-state placeholder, and acceptance-criteria tables.
- **prefix match** -- `path.startswith(prefix)` where `prefix` ends with `/`. Empty prefix is forbidden.

## 3. Axes (orthogonality contract)

| # | Axis              | Values                                                        | Lifetime                | Source of truth         |
|---|-------------------|---------------------------------------------------------------|-------------------------|-------------------------|
| 1 | Source data       | `list[FileChange]` from `get_changes(cwd, target)`            | per `/diff` invocation  | git                     |
| 2 | Sort mode         | `"alphabetical" \| "directory"`                               | persisted per-repo      | SortModeStore           |
| 3 | Hide state        | `(hide_files, hide_prefixes, force_visible)`                  | session, per-repo       | HideStore               |
| 3a| Fold state        | `folded_prefixes: set[str]` (sidebar-visual only)             | session, per-repo       | HideStore               |
| 4 | Visibility        | `bool` per file (derived)                                     | recomputed per render   | pure function           |
| 5 | Focus key         | `(path, hunk_idx)`                                            | per DiffView instance   | DiffView                |
| 6 | Dirty path set    | `set[str]` from `get_dirty_paths(cwd)`                        | per `/diff` invocation  | git status --porcelain  |

Axis 6 is consumed only by the FilesSection prune step (s8) and is independent of axes 1-5.

The widget layer never branches on axis 2 or axis 3. It consumes a `DisplayTree` whose nodes carry a derived `hidden: bool`, and renders.

### 3.1 Forbidden patterns

- `if sort_mode == ...` inside any widget `compose` method.
- Direct set reads `if path in hide_state.*` inside any widget. This covers all four internal sets: `hide_files`, `hide_prefixes`, `force_visible`, `folded_prefixes`. Widgets call the Protocol methods instead: `is_hidden(path)`, `is_folded(prefix)`, `is_prefix_hidden(prefix)`, `longest_matching_prefix(path)`.
- Adding `.hidden`, `.reviewed`, or `.sort_position` fields to `FileChange`.
- Re-mounting `HunkWidget`s on sort change. Sort change moves existing children only.
- Computing the FilesSection prune basis from the `target` argument or from `get_changes` / `get_file_stats`. Prune basis is always `HEAD` via `get_dirty_paths` (s8). Reusing `get_changes` or `get_file_stats` for prune is forbidden because they truncate untracked files when there are more than `MAX_UNTRACKED_FILES` (=4) untracked entries.
- FilesSection prune ADDING files. The prune step is remove-only.
- Leaking implementation terms to user-visible UI. Specifically: the strings `hide_files`, `hide_prefixes`, `force_visible` must never appear in any tooltip, footer-help label, empty-state text, or other user-facing surface. User-facing wording uses only `hide`, `unhide`, `hidden`, `visible`, and per-tooltip phrasings defined in s7.

## 4. Pure functions (signatures)

```python
def build_tree(changes: list[FileChange], sort_mode: SortMode) -> DisplayTree: ...

def apply_hide(tree: DisplayTree, hide_state: HideState) -> DisplayTree: ...
```

`HideState.is_hidden` (defined in s5.1) is the single source of truth for visibility. Every consumer (DiffSidebar, DiffView, controller) calls `hide_state.is_hidden(path)`. No consumer reads `hide_files` / `hide_prefixes` / `force_visible` directly.

`apply_hide` walks the tree and sets `FileNode.hidden = hide_state.is_hidden(file_change.path)`. It does not prune nodes; widgets decide rendering by reading `FileNode.hidden`. This preserves `HunkWidget` instances under sort and hide changes.

### 4.1 Composition pipeline

`/diff` invocation in `claudechic/app.py:_toggle_diff_mode` (and `_toggle_diff_mode_for_file`):

```
# Step 1: prune chat-screen FilesSection (axis 6)
await self._prune_files_section_to_git(agent)        # see s8

# Step 2: push DiffScreen
self.push_screen(DiffScreen(cwd, target, ..., hide_store=..., sort_mode_store=...))
```

DiffScreen.on_mount:

```
changes = await get_changes(cwd, target)             # axis 1
sort_mode = sort_mode_store.get(cwd)                 # axis 2
hide_state = hide_store.get(cwd)                     # axis 3
tree = build_tree(changes, sort_mode)
tree = apply_hide(tree, hide_state)
DiffSidebar.render(tree)
DiffView.render(tree)
```

### 4.2 build_tree rules

- `alphabetical`: flat list of `FileNode`, sorted by `file_change.path` lexicographic.
- `directory`: list whose elements are `FileNode` (files at the repo root) or `DirectoryNode` recursively. Files inside the same parent share the same `DirectoryNode`. Directory order: lexicographic on `prefix`. File order inside a directory: lexicographic on `file_change.path`.
- Untracked files (`status == "untracked"`) participate uniformly in both modes. No special bucket.

### 4.3 DiffDirectoryItem in directory mode

In `directory` sort mode, `DiffSidebar` renders one `DiffDirectoryItem` row per `DirectoryNode`, immediately before that node's `DiffFileItem` children. Each `DiffDirectoryItem` contains two independent sub-components with independent click targets:

- **`DirFoldGlyph`** -- glyph `[-]` when the prefix is unfolded (children visible in sidebar); `[+]` when folded (children collapsed). Clicking this component calls `hide_store.fold_prefix(cwd, prefix)` or `hide_store.unfold_prefix(cwd, prefix)`. Fold is purely a sidebar-visual toggle.
- **`DirNameLabel`** -- the prefix string (always ends with `/`). Clicking this component toggles hide state: if the prefix is NOT currently in `hide_prefixes`, calls `hide_store.hide_prefix(cwd, prefix)`; if the prefix IS in `hide_prefixes`, calls `hide_store.unhide_prefix(cwd, prefix)`.

**Fold is orthogonal to hide.** A folded prefix's file rows are not rendered in the sidebar, but their `FileDiffPanel`s in `DiffView` are unaffected (fold does NOT set `FileNode.hidden`). `HideState.is_hidden(path)` is never consulted for fold decisions; `HideState.is_folded(prefix)` is never consulted for hide decisions. The four resulting states (folded/unfolded x hidden/not-hidden) are defined visually in s7.2.

`DiffDirectoryItem` rows do not appear in `alphabetical` mode; `build_tree` returns only `FileNode`s in that mode.

## 5. Hide state (#20)

### 5.1 Data and prefix normalization

```python
@dataclass
class HideState:
    hide_files:      set[str]
    hide_prefixes:   set[str]
    force_visible:   set[str]
    folded_prefixes: set[str]   # sidebar-visual only; does NOT affect is_hidden

    def is_hidden(self, path: str) -> bool:
        if path in self.force_visible:
            return False
        if path in self.hide_files:
            return True
        return any(path.startswith(p) for p in self.hide_prefixes)

    def is_folded(self, prefix: str) -> bool:
        """Return True if prefix is currently collapsed in the sidebar.

        Fold is orthogonal to hide: folded files remain visible in DiffView.
        DiffSidebar child rows under a folded prefix are not rendered; their
        FileDiffPanels in DiffView are unaffected.
        """
        return prefix in self.folded_prefixes

    def is_prefix_hidden(self, prefix: str) -> bool:
        """Return True if prefix is in hide_prefixes.

        Exposed as a method so DiffDirectoryItem can style DirNameLabel for
        the 'prefix is hidden' state without reading hide_prefixes directly
        (s3.1 forbids direct set access in widgets).
        """
        return prefix in self.hide_prefixes
```

A "prefix" always ends with `/`. Prefixes never include a leading `./`. Empty prefix is forbidden. Path strings use forward slashes regardless of OS, matching `git diff` output.

`folded_prefixes` is orthogonal to the three hide sets: adding or removing a prefix from `folded_prefixes` has no effect on `is_hidden(path)`. `reset` clears all four sets (s5.3).

Helper for prefix derivation:

```python
def _to_prefix(path: str) -> str | None:
    """Parent-directory prefix for path, or None if path is at the repo root."""
    if "/" not in path:
        return None
    return path.rsplit("/", 1)[0] + "/"
```

Behavior of `d` on a focused file at path P:
- If `_to_prefix(P) is None` (root-level file): `d` is a no-op. DiffScreen surfaces a transient footer hint: `no parent directory to hide`. The HideStore is not mutated. To hide a root-level file, the user presses `f`.
- Otherwise: add `_to_prefix(P)` to `hide_prefixes` (set semantics: idempotent if already present).

Prefix matching is `path.startswith(prefix)`; never substring or path-component magic. Because every prefix ends with `/`, `"src/"` does NOT match `"src_old/foo.py"`.

### 5.2 Resolution

See `HideState.is_hidden` in s5.1. Equivalently:

```
visible := path in force_visible
       or (path not in hide_files and no prefix in hide_prefixes matches path)
```

`force_visible` only overrides prefix membership; it does not override `hide_files`.

### 5.3 HideStore protocol

```python
class HideStore(Protocol):
    def get(self, repo_key: Path) -> HideState: ...
    def hide_file(self, repo_key: Path, path: str) -> None: ...
    def hide_prefix(self, repo_key: Path, prefix: str) -> None: ...
    def unhide_file(self, repo_key: Path, path: str) -> None: ...
    def unhide_prefix(self, repo_key: Path, prefix: str) -> None: ...
    def fold_prefix(self, repo_key: Path, prefix: str) -> None: ...
    def unfold_prefix(self, repo_key: Path, prefix: str) -> None: ...
    def reset(self, repo_key: Path) -> None: ...
```

Semantics:

- `get`: returns the existing HideState for `repo_key` or creates a fresh empty one.
- `hide_file`: adds `path` to `hide_files`; removes `path` from `force_visible` if present.
- `hide_prefix`: adds `prefix` to `hide_prefixes`; removes any `force_visible` entries whose path matches the new prefix.
- `unhide_file` (clauses are independent; either, neither, or both may fire):
  - If `path in hide_files`: remove from `hide_files`.
  - Then if any prefix in `hide_prefixes` matches `path`: add `path` to `force_visible`.
  - Equivalent invariant: after `unhide_file(path)` returns, `is_hidden(path)` is `False`.
- `unhide_prefix`: removes `prefix` from `hide_prefixes`; also clears any `force_visible` entries whose path starts with `prefix` (they are moot once the prefix is no longer hidden). Inverse of `hide_prefix`. Used by `DirNameLabel` click on a hidden directory header (s4.3).
- `fold_prefix`: adds `prefix` to `folded_prefixes`. Sidebar-visual only; does NOT affect `is_hidden`. Triggered by `DirFoldGlyph` click on an unfolded row (s4.3).
- `unfold_prefix`: removes `prefix` from `folded_prefixes`. Triggered by `DirFoldGlyph` click on a folded row (s4.3).
- `reset`: clears all four sets (`hide_files`, `hide_prefixes`, `force_visible`, `folded_prefixes`) for `repo_key`. Other repo keys are untouched.

### 5.4 Lifetime and isolation

- HideStore is a single instance owned by `ChatApp`. Internal storage: `dict[Path, HideState]`.
- Exposed to DiffScreen by constructor injection.
- Two DiffScreens with the same `cwd` share their HideState.
- Different `cwd` values are independent.
- All entries are dropped at process exit. No file persistence.

### 5.5 Keybinding state transitions

- `f` on focused file at path P -> `hide_store.hide_file(cwd, P)`.
- `d` on focused file at path P:
  - If `_to_prefix(P) is None`: no-op; show transient footer hint `no parent directory to hide` (s5.1).
  - Else: `hide_store.hide_prefix(cwd, _to_prefix(P))`.
- Click on a hidden DiffFileItem at path P -> `hide_store.unhide_file(cwd, P)`.
- Click on `DirFoldGlyph` for prefix Q (directory mode only):
  - If `is_folded(Q)`: `hide_store.unfold_prefix(cwd, Q)`.
  - Else: `hide_store.fold_prefix(cwd, Q)`.
- Click on `DirNameLabel` for prefix Q (directory mode only):
  - If `is_prefix_hidden(Q)`: `hide_store.unhide_prefix(cwd, Q)`.
  - Else: `hide_store.hide_prefix(cwd, Q)`.
- `r` -> `hide_store.reset(cwd)`. Clears all four sets. Affects ONLY the current `cwd`; other repo keys in the HideStore are untouched.

### 5.5.1 Edge-case truth table

| Pre-state                                                         | Action  | hide_files | hide_prefixes | force_visible | Post is_hidden(P) |
|-------------------------------------------------------------------|---------|------------|---------------|---------------|-------------------|
| P in `force_visible` only                                         | `f`     | += {P}     | unchanged     | -= {P}        | True              |
| `_to_prefix(P)` already in `hide_prefixes`                        | `d`     | unchanged  | idempotent    | -= matches    | True              |
| P in `force_visible` AND prefix in `hide_prefixes`                | `d`     | unchanged  | idempotent    | -= {P}        | True              |
| P in `hide_files` only                                            | click   | -= {P}     | unchanged     | unchanged     | False             |
| `_to_prefix(P)` in `hide_prefixes` only                           | click   | unchanged  | unchanged     | += {P}        | False             |
| P in BOTH `hide_files` AND under a prefix                         | click   | -= {P}     | unchanged     | += {P}        | False             |
| any state                                                         | `r`     | cleared    | cleared       | cleared       | False             |

Note: `DirFoldGlyph` click and `DirNameLabel` click transitions are not in this table. `DirFoldGlyph` click mutates only `folded_prefixes` (orthogonal to this table; `is_hidden` is unchanged). `DirNameLabel` click calls `hide_prefix` or `unhide_prefix` (rows covered by the prefix-related rows above). `r` clears `folded_prefixes` as well as the three hide sets.

After every transition, DiffScreen rebuilds the DisplayTree (`build_tree` + `apply_hide`), updates DiffSidebar greyed styling, updates each `FileDiffPanel.display`, and applies focus policy (s6.2).

### 5.5.2 Update fan-out

DiffScreen is the controller. After mutating the HideStore, it (a) re-runs `apply_hide` to refresh `FileNode.hidden` across the DisplayTree, then (b) triggers ONE notification (a reactive bump such as `hide_state_version: reactive[int]`, or a posted `HideStateChanged` Message). On the notification:
- DiffSidebar re-reads each `FileNode.hidden` to set greyed styling.
- DiffView re-reads each `FileNode.hidden` to toggle `FileDiffPanel.display`.

No widget reads `hide_files`, `hide_prefixes`, `force_visible`, or `folded_prefixes` directly (s3.1). Sibling-to-sibling imperative `update` calls are forbidden. Same pattern applies for `SortModeChanged`.

## 6. DiffView and focus

### 6.1 DiffView focus contract

```python
def current_focus_key(self) -> tuple[str, int] | None
def set_focus_key(self, key: tuple[str, int]) -> None
def next_visible_after(self, key: tuple[str, int]) -> tuple[str, int] | None
def prev_visible_before(self, key: tuple[str, int]) -> tuple[str, int] | None
```

`_hunk_list` is rebuilt from currently-visible `HunkWidget`s after any sort change or hide-state mutation, so j/k navigation skips hidden files.

### 6.2 Focus policy

After a hide transition causes the focused hunk's file to become hidden:

1. `new_key = view.next_visible_after(key) or view.prev_visible_before(key)`.
2. If `new_key is not None`: `view.set_focus_key(new_key)`.
3. Else: DiffView shows the empty-state placeholder (s6.4); focus moves to the DiffView container so keybindings still fire.

`r` and click unhide do NOT change focus, except that `r` from the empty-state moves focus to the first hunk of the first visible file.

### 6.3 Hidden FileDiffPanel rendering

For each `FileDiffPanel`, `display = not file_node.hidden`. Hidden panels are not rendered and are not navigable by j/k.

### 6.4 Empty-state placeholder

When all FileNodes in the DisplayTree are hidden, DiffView shows a placeholder containing exactly:

```
All N files hidden.
Click any greyed entry in the sidebar to un-hide it,
or press r to reset all hides.
```

`N` is the count of files in the diff. The placeholder is removed once any file becomes visible.

## 7. DiffSidebar visual treatment

### 7.1 DiffFileItem (hidden render variant)

For a hidden DiffFileItem:

- Status letter cell renders `.` (single ASCII dot) in `$text-muted`. Replaces the normal `M / A / D / R / U / ?` letter while hidden.
- Path text renders in `$text-muted` with `text-style: strike`.
- Hunk count `(N)` renders in `$text-muted`, no strike.
- The `.active` class is never applied to a hidden entry.
- Visual treatment is identical regardless of which set caused the hide.

Tooltip on a hidden entry, computed from the resolution path:

- Hidden by `hide_files` only: `click to un-hide`.
- Hidden by prefix membership (with or without simultaneous `hide_files` membership): `click to un-hide just this file (<prefix> stays hidden)`, where `<prefix>` is the longest matching entry of `hide_prefixes`.

Click action: see s5.5.

DiffSidebar's narrow-width behavior is unchanged: at width < 100 cols, it receives the existing `.hidden` class and is removed from layout. When the sidebar is hidden by narrow width and the user has hidden files, the only unhide path is `r` (keyboard). Mouse-only users on narrow terminals must widen the terminal to reach the greyed sidebar entries.

### 7.2 DiffDirectoryItem visual treatment (directory mode only)

`DiffDirectoryItem` rows appear only in `directory` sort mode. Each row has two independent sub-components (`DirFoldGlyph` and `DirNameLabel`) with independent visual styling driven by the two orthogonal state axes:

| State                        | DirFoldGlyph | DirNameLabel                                  |
|------------------------------|--------------|-----------------------------------------------|
| unfolded, prefix NOT hidden  | `[-]`        | prefix string, normal color                   |
| folded,   prefix NOT hidden  | `[+]`        | prefix string, normal color                   |
| unfolded, prefix IS hidden   | `[-]`        | prefix string, `$text-muted`, `text-style: strike` |
| folded,   prefix IS hidden   | `[+]`        | prefix string, `$text-muted`, `text-style: strike` |

- **`DirFoldGlyph`** is always rendered in a neutral accent color regardless of hide state. Its text is exactly `[-]` (unfolded) or `[+]` (folded); no other variants.
- **`DirNameLabel`** applies the muted / strike treatment when `is_prefix_hidden(prefix)` is True, mirroring the per-file hidden render variant on `DiffFileItem` (s7.1). Visual treatment is identical regardless of whether the prefix was hidden via `d` (keybinding) or click.
- The fold state (`is_folded`) does NOT affect `DirNameLabel` color or strike; fold affects only the glyph and whether child `DiffFileItem` rows are rendered.
- Click behavior: see s4.3 and s5.5. `DirFoldGlyph` click -> `fold_prefix` / `unfold_prefix`; `DirNameLabel` click -> `hide_prefix` / `unhide_prefix`.

## 8. FilesSection prune (#11/#18)

### 8.1 Trigger

The prune runs on every `/diff` invocation, in `claudechic/app.py`, immediately before `DiffScreen` is pushed. Both call sites are covered:

- `_toggle_diff_mode(target=None)` (the `/diff` slash-command entry).
- `_toggle_diff_mode_for_file(path, target=None)` (the focus-on-file entry).

No other trigger. No polling. No Bash post-hook. No `/refresh-files` command.

### 8.2 Data source: `get_dirty_paths`

New helper in `claudechic/features/diff/git.py`, exported from `claudechic/features/diff/__init__.py`:

```python
async def get_dirty_paths(cwd: str) -> set[str]:
    """Return paths dirty in the working tree relative to HEAD.

    Includes tracked-modified, staged, and ALL untracked entries -- no
    truncation. For renames/copies (status R / C), returns the destination
    path; the source path is dropped. On subprocess failure, returns an
    empty set so callers can fail open.
    """
```

Implementation: single subprocess call to `git status --porcelain -z`, parse NUL-terminated entries (entry layout: 2 status chars + space + path; for `R` / `C` the next entry is the source path and is consumed-but-not-included in the result). All file I/O uses `encoding="utf-8"`.

`get_dirty_paths` is the ONLY function used to compute the prune basis. Reusing `get_changes` or `get_file_stats` for prune is forbidden by s3.1 because they cap untracked files at `MAX_UNTRACKED_FILES` (=4) for UI display reasons, which would silently drop just-Written untracked files when the tree has 5+ untracked.

### 8.3 Prune method on FilesSection

New method on `claudechic/widgets/layout/sidebar.py:FilesSection`:

```python
def prune_to(self, dirty: set[Path]) -> None:
    """Remove items whose path is not in `dirty`. Never adds.

    Iterates self._files, removes mounted FileItem widgets whose key
    is not present in `dirty`, and deletes from self._files. If the
    section becomes empty, applies the `.hidden` class to mirror
    existing clear() behavior.
    """
```

Sync method (not async). Children removal does not need to be awaited for visual correctness. `self._files` is the source of truth for "files in this section."

### 8.4 App-level orchestration

New private method on `ChatApp` (`claudechic/app.py`):

```python
async def _prune_files_section_to_git(self, agent: Agent) -> None:
    from claudechic.features.diff import get_dirty_paths
    try:
        dirty_strs = await get_dirty_paths(str(agent.cwd))
    except Exception:
        return                                  # fail open; no prune
    dirty = {Path(p) for p in dirty_strs}
    self.files_section.prune_to(dirty)
```

Called via `await self._prune_files_section_to_git(agent)` from `_toggle_diff_mode` and `_toggle_diff_mode_for_file` before the DiffScreen push.

### 8.5 Prune-only invariant

The prune step never adds entries to FilesSection. Files appearing in the dirty path set that are NOT currently in `FilesSection._files` are ignored. Files modified externally (e.g. user runs `git checkout` mid-conversation) must not be added by this path.

The agent-switch path (`_async_refresh_files` in `claudechic/app.py`) continues to clear-and-rebuild FilesSection from `get_file_stats` as it does today; that path is unchanged. Prune-on-/diff and refresh-on-agent-switch are separate flows.

### 8.6 Prune basis is always HEAD

The prune basis is always the working-tree state vs `HEAD` as reported by `git status --porcelain -z`. The `target` argument that may have been passed to `DiffScreen` (e.g. `origin/main`) is never used as the prune basis. `git status` is inherently HEAD-relative; this rule is restated to prevent a future refactor from adding a `target` parameter to the prune flow.

### 8.7 Failure mode

If `get_dirty_paths` raises (subprocess error, not a git repo, etc.), the prune is silently skipped. DiffScreen still opens. FilesSection retains all current entries. Logged via `log.warning`; no user-facing toast.

### 8.8 Edge cases

| Case                                                                  | Behavior                                  |
|-----------------------------------------------------------------------|-------------------------------------------|
| File edited in-session, then committed externally before next `/diff` | Pruned at next `/diff`.                   |
| File edited in-session, `git add` then `git reset HEAD`               | Still in `git status` -> kept.            |
| Untracked file Claude wrote, then `rm`'d on disk                      | Not in `git status` -> pruned.            |
| Tree has 6 untracked files; Claude wrote one of them                  | All 6 in dirty path set; all 6 kept.      |
| Renamed file (`R old -> new` in `git status`)                         | `new` is in dirty; if FilesSection had `old`, it is pruned (old not in dirty). New is not added (s8.5). |
| File never edited in chat but appears in `git status`                 | Not added (s8.5).                         |
| `get_dirty_paths` raises                                              | Silent skip (s8.7).                       |
| FilesSection becomes empty after prune                                | `.hidden` class applied (s8.3).           |

## 8a. MAX_UNTRACKED_FILES cap removal (in-scope side-fix)

### 8a.1 Fix

Pre-fix, both `get_changes` and `get_file_stats` in `claudechic/features/diff/git.py` silently dropped all untracked entries when count > 4 due to a `len(untracked) <= MAX_UNTRACKED_FILES` gate.

Remove the `if len(untracked) <= MAX_UNTRACKED_FILES:` gate from BOTH `get_changes` and `get_file_stats`. Always iterate the full untracked list.

The companion size cap (`MAX_UNTRACKED_FILE_SIZE = 1024` bytes per file content read) remains in place and is the load-bearing protection against pathological per-file payloads. Removing the count cap does not affect the size cap.

The constant `MAX_UNTRACKED_FILES` may be deleted entirely once both callers no longer reference it.

### 8a.2 Forbidden alternatives

- Reintroducing a count cap "for safety" -- replaces the visible bug with a silent one.
- A "show only first N, with a count badge" UI variant -- new feature work outside this project's scope.

## 9. SortModeStore (#19)

### 9.1 Protocol

```python
SortMode = Literal["alphabetical", "directory"]

class SortModeStore(Protocol):
    def get(self, repo_key: Path) -> SortMode: ...
    def set(self, repo_key: Path, mode: SortMode) -> None: ...
```

### 9.2 Persistence

- File path: `<repo_key>/.claudechic/diff.yaml`. Dedicated file; no co-tenancy with `config.yaml` in v1.
- Schema:
  ```yaml
  sort_mode: directory   # or "alphabetical"
  ```
- Default when file absent or key missing: `"directory"`.
- Invalid value: log a warning, return `"directory"`.
- `set` writes the file atomically (`os.replace`); creates `.claudechic/` if absent.
- Reads are not cached across DiffScreen instances; `set` always persists.
- All file I/O uses `encoding="utf-8"`.

### 9.3 Toggle

`s` cycles between the two modes (no third mode in v1). Toggle invokes `sort_mode_store.set(cwd, new_mode)` then triggers in-place reorder (s10).

## 10. In-place reorder (sort change)

Sort change executes inside DiffView and DiffSidebar:

1. Compute new DisplayTree from `(changes, new_sort_mode)`.
2. For each existing `FileDiffPanel` and its descendant `HunkWidget`s, keep the instance.
3. Use Textual `move_child(child, before=...)` (or equivalent) to reorder existing `FileDiffPanel`s into the new sequence.
4. DiffSidebar reorders `DiffFileItem`s identically.
5. After reorder, run `apply_hide` and update each node's `display`; do not remove children.
6. Rebuild `_hunk_list` from the reordered children.

Forbidden: any code path that re-mounts `HunkWidget`s on sort change. This is what preserves in-progress hunk comments.

## 11. Keybindings

DiffScreen `BINDINGS`:

| Key      | Action                                            |
|----------|---------------------------------------------------|
| `s`      | toggle sort mode                                  |
| `f`      | hide focused file                                 |
| `d`      | hide directory of focused file (no confirmation)  |
| `r`      | reset hide state for current cwd                  |
| `j`      | next hunk (existing behavior)                     |
| `k`      | previous hunk (existing behavior)                 |
| `down`   | next hunk (existing behavior)                     |
| `up`     | previous hunk (existing behavior)                 |
| `enter`  | (existing behavior)                               |
| `o`      | (existing behavior)                               |
| `q`      | dismiss screen (existing behavior)                |
| `escape` | dismiss screen (existing behavior)                |

All bindings declared via Textual `BINDINGS`, not `on_key`, so the footer help shows them. Existing `on_key` consumers in DiffScreen are migrated.

## 12. Module structure

New / changed files under `claudechic/features/diff/`:

```
git.py        existing -- adds get_dirty_paths(cwd) helper for #11/#18 prune
sort.py       NEW     -- SortMode, SortModeStore impl, build_tree
hide.py       NEW     -- HideState, HideStore impl
tree.py       NEW     -- DisplayNode, DisplayTree, apply_hide, FileNode, DirectoryNode
widgets.py    existing -- consumes DisplayTree; greyed rendering; in-place reorder
__init__.py   existing -- export get_dirty_paths
```

Other touched files:

- `claudechic/screens/diff.py` -- BINDINGS migration; new actions for `s f d r`; integrates HideStore + SortModeStore.
- `claudechic/app.py` -- constructs singleton HideStore on `ChatApp`; passes both stores to DiffScreen; new `_prune_files_section_to_git(agent)` method (s8.4); calls it from both `_toggle_diff_mode` and `_toggle_diff_mode_for_file` before pushing DiffScreen.
- `claudechic/widgets/layout/sidebar.py` -- new `FilesSection.prune_to(dirty)` method (s8.3).
- `claudechic/styles.tcss` -- `.hidden-entry` class for greyed sidebar items; `.diff-empty-state` placeholder styling.
- Tests under `tests/` -- s14.

### 12.1 Import directions

- `tree.py` imports `git.py` (for `FileChange`). No reverse import.
- `sort.py` imports `tree.py` and `git.py`.
- `hide.py` imports nothing from `widgets.py` or `screens/`.
- `widgets.py` imports `tree.py`, `sort.py`, `hide.py`. No reverse.
- `screens/diff.py` is the only module that touches all three diff submodules.
- `app.py` imports `get_dirty_paths` from `claudechic.features.diff` (for the prune step).
- `widgets/layout/sidebar.py:FilesSection` imports nothing from `features/diff`; it receives the dirty path set as `set[Path]` from the App.

No circular imports. No widget imports a store implementation; widgets take protocols.

### 12.2 DiffScreen constructor

```python
def __init__(
    self,
    cwd: Path,
    target: str = "HEAD",
    focus_file: str | None = None,
    *,
    hide_store: HideStore,
    sort_mode_store: SortModeStore,
) -> None: ...
```

Both stores are mandatory keyword arguments. Call site in `claudechic/app.py` provides them.

## 13. _path_to_id encoding

Replace `_sanitize_id` (in `widgets.py`) with:

```python
def _path_to_id(path: str, hunk_idx: int | None = None) -> str:
    encoded = path.encode("utf-8").hex()
    return f"hunk-{encoded}-{hunk_idx}" if hunk_idx is not None else f"sidebar-{encoded}"
```

Reverse decoding: `bytes.fromhex(encoded).decode("utf-8")`.

## 14. Acceptance criteria

A change set satisfying this spec must pass:

14.1 All existing `tests/` pass with `pytest --timeout=30`.

14.2 `ruff check` clean. `ruff format` clean. `pyright` no new errors.

14.3 Test surface (unit + workflow + visual archetypes + manual): see `SPEC_APPENDIX.md` section I. Tests are written in the Testing phase, NOT by Implementers. The operational contracts those tests will assert against (s5.5.1 truth table, s8.8 edge-case table, s6.4 empty-state placeholder text, s7 tooltip strings, s10 in-place reorder rules) live in this document and are what Implementers must satisfy.

## 15. Documented behavior (not bugs)

- **`claudechic --resume` does not preserve hide state or fold state.** A fresh process means a fresh HideStore (all four sets empty). Documented; not a future bug.
- **Hide store is monotonic over a session.** Entries accumulate; a hidden path that left the diff still occupies a string in the set. Negligible RAM. `r` is the user-controlled GC.
- **Untracked files participate identically** in sort grouping and hide. Same code path as tracked files.
- **Hidden files with in-progress hunk comments**: allowed. Comments live on `HunkWidget`; `display: false` does not destroy the widget. On screen dismiss, all returned comments are surfaced regardless of hide state via the existing `get_comments()` path -- hide does not filter, transform, or otherwise affect the comment lifecycle. Implementers must NOT add a "skip hidden" filter to `get_comments()`. Future polish: dismiss-time "N hidden files have comments" notice (deferred).
- **FilesSection prune is `/diff`-triggered only.** A user who commits via Bash and never opens `/diff` will see stale FilesSection entries until the next `/diff`. Acceptable per the user's "make it SIMPLE" directive. Polling, post-commit hooks, and a separate refresh command are explicitly out of scope.
- **FilesSection prune is a snapshot, not a subscription.** It captures `git status` at the moment of `/diff` invocation; concurrent file edits in flight reflect on the next `/diff`.
- **FilesSection prune never adds.** Files appearing in `git status` that are NOT currently in `FilesSection._files` are ignored. The agent-switch refresh path (`_async_refresh_files`) is the only flow that adds files from git state; it is unchanged.
- **No source-command rendering.** The earlier DiffHeader proposal is retracted (see appendix C.11). DiffScreen has no widget displaying the originating `git diff` command in v1.

## 16. Sequencing (recommended Implementer ordering)

16.0 Side-fix (s8a): remove `MAX_UNTRACKED_FILES` cap from `get_changes` and `get_file_stats`. Drop the constant once unused.

16.1 `get_dirty_paths` helper in `features/diff/git.py` + export.

16.2 `FilesSection.prune_to` method.

16.3 `_prune_files_section_to_git` on `ChatApp`; wire into both `_toggle_diff_mode` entry points.

16.4 `_path_to_id` replacement.

16.5 `tree.py`: `DisplayNode`, `DisplayTree`, `apply_hide`.

16.6 `sort.py`: `SortMode`, `SortModeStore` impl, `build_tree`.

16.7 `hide.py`: `HideState` (with `is_hidden` method), `HideStore` impl.

16.8 DiffScreen integration: pass stores via constructor; rebuild DisplayTree on transitions; focus policy; update fan-out via reactive or Message.

16.9 Widget consumption: DiffSidebar greyed rendering; DiffView `display` toggling; in-place reorder (`move_child`); empty-state placeholder.

16.10 BINDINGS migration; footer help verification.

Testing-phase note: tests for each of the above are written in the Testing phase (see `SPEC_APPENDIX.md` section I), not by the Implementer of the same step.
