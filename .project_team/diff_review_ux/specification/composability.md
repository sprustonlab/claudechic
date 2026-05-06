# Composability Specification -- diff_review_ux

> Historical / rationale document. Canonical naming lives in `specification/terminology.md`; this file uses some pre-lockdown draft terms (e.g. `un-hide`, `NV2`, `content_sha` in retraction context). Its operational content was merged into `specification/SPECIFICATION.md`, which is the canonical operational contract.

**Phase:** Specification
**Author:** Composability (Lead Architect)
**Status:** v1 (operational)
**Scope:** Architectural seams, axes, protocols, and module structure for the
DiffScreen changes covering GitHub issues #18, #19, #20.

---

## 1. Terms

Every term used elsewhere in this document is defined here.

- **DiffScreen** -- the existing full-page Textual screen at
  `claudechic/screens/diff.py` reached via `/diff`.
- **DiffView** -- the existing scrollable container of file panels at
  `claudechic/features/diff/widgets.py:DiffView`.
- **DiffSidebar** -- the existing left-hand file list at
  `claudechic/features/diff/widgets.py:DiffSidebar`.
- **DiffFileItem** -- the existing per-file row in the sidebar at
  `claudechic/features/diff/widgets.py:DiffFileItem`.
- **HunkWidget** -- the existing per-hunk widget that owns its hunk comment
  at `claudechic/features/diff/widgets.py:HunkWidget`.
- **FileChange** -- the existing pure data record at
  `claudechic/features/diff/git.py:FileChange`. Carries `path`, `status`,
  `hunks`. Treated as immutable in this spec.
- **target** -- the second argument to `git diff` (default `HEAD`). A
  string passed into `DiffScreen.__init__` today.
- **source command** -- the literal string `"git diff <target>"` rendered
  in the new `DiffHeader` widget. Single source of truth: produced by
  the same call site that runs `git diff`.
- **sort mode** -- one of the string values `"alphabetical"` or
  `"directory"`. Default on first run: `"directory"`.
- **hide state** -- a tuple of three string sets per repo:
  `(hide_files, hide_prefixes, force_visible)`. See section 4.4.
- **repo key** -- the `cwd: Path` value passed to `DiffScreen.__init__`,
  used verbatim. No symlink resolution, no `git rev-parse --show-toplevel`.
- **DisplayNode** -- a node in the `DisplayTree`. One of two variants:
  `FileNode(file_change: FileChange, hidden: bool)` or
  `DirectoryNode(prefix: str, children: list[DisplayNode])`.
- **DisplayTree** -- the rooted tree used by `DiffSidebar` and `DiffView`
  to render. Produced by a pure function from `(list[FileChange],
  sort_mode, hide_state)`.
- **focus key** -- the pair `(path: str, hunk_idx: int)`. The single
  identifier of "what hunk has focus". Survives sort change and hide
  toggle.

---

## 2. Axes

The implementation must treat the following as orthogonal axes. Section 3
states the compositional law that keeps them orthogonal.

| # | Axis name        | Values                                                | Lifetime              | Source of truth         |
|---|------------------|-------------------------------------------------------|-----------------------|-------------------------|
| 1 | Source data      | `list[FileChange]` produced by `get_changes(cwd, target)` | per `/diff` invocation | git                     |
| 2 | Source command   | string `"git diff <target>"`                          | per `/diff` invocation | the function in axis 1  |
| 3 | Sort mode        | `"alphabetical" \| "directory"`                       | persisted per-repo    | `SortModeStore`         |
| 4 | Hide state       | `(hide_files, hide_prefixes, force_visible)`          | session, per-repo     | `HideStore`             |
| 5 | Visibility (derived) | `bool` per file, computed from axis 4             | recomputed per render | pure function           |
| 6 | Focus key        | `(path, hunk_idx)`                                    | per `DiffView` instance | `DiffView`            |

Axes 5 is derived; it is listed because its derivation must be pure (no
state of its own).

---

## 3. Compositional law

The widget layer never branches on sort mode or hide state. It consumes a
`DisplayTree` and renders it. The `DisplayTree` is built by pure
functions.

### 3.1 Pure functions (signatures)

```python
def build_tree(
    changes: list[FileChange],
    sort_mode: SortMode,
) -> DisplayTree: ...

def apply_hide(
    tree: DisplayTree,
    hide_state: HideState,
) -> DisplayTree: ...

def is_hidden(path: str, hide_state: HideState) -> bool:
    if path in hide_state.force_visible:
        return False
    if path in hide_state.hide_files:
        return True
    return any(path.startswith(p) for p in hide_state.hide_prefixes)
```

`apply_hide` walks the tree and sets `FileNode.hidden = is_hidden(...)`.
It does not remove nodes; widgets decide rendering by reading `hidden`.
This preserves `HunkWidget` instances under sort and hide changes.

### 3.2 Composition

```
changes = await get_changes(cwd, target)             # axis 1
command = f"git diff {target}"                        # axis 2
tree    = build_tree(changes, sort_mode)              # axis 3
tree    = apply_hide(tree, hide_state)                # axis 4 -> 5
DiffSidebar.render(tree)
DiffView.render(tree)
```

### 3.3 Forbidden patterns

The following are spec violations:

- `if sort_mode == ...` inside any widget `compose` method.
- `if path in hide_state.hide_files` inside any widget; widgets read
  `FileNode.hidden`.
- Adding `.hidden`, `.reviewed`, or `.sort_position` fields to
  `FileChange`.
- Rebuilding `DiffView` (re-mounting children from scratch) on sort
  change. Sort change moves existing children only.
- Producing the source command anywhere other than the call site that
  runs `git diff`.

---

## 4. Seams (protocols)

### 4.1 `DiffSource` -- axes 1 and 2 cross this seam

```python
@dataclass(frozen=True)
class DiffSource:
    changes: list[FileChange]
    command: str        # e.g. "git diff HEAD"
    target: str         # the raw target string
```

Producer: a single async function in `claudechic/features/diff/git.py`,
either `get_changes` updated to return `DiffSource`, or a new wrapper
`load_diff_source(cwd, target) -> DiffSource`. Pick one and remove the
other path.

Consumer: `DiffScreen.on_mount` only. `DiffSidebar`, `DiffView`,
`DiffHeader` receive their inputs from `DiffScreen` derived from the
same `DiffSource` instance.

### 4.2 `SortMode` and `SortModeStore`

```python
SortMode = Literal["alphabetical", "directory"]

class SortModeStore(Protocol):
    def get(self, repo_key: Path) -> SortMode: ...
    def set(self, repo_key: Path, mode: SortMode) -> None: ...
```

Persistence:
- File path: `<repo_key>/.claudechic/diff.yaml`.
- Schema:
  ```yaml
  sort_mode: directory   # or "alphabetical"
  ```
- Default when file absent or key missing: `"directory"`.
- `set` writes the file atomically (`os.replace`); creates
  `.claudechic/` if absent.
- Reads are not cached across `DiffScreen` instances; `set` always
  persists.

`SortModeStore` is the only writer of `diff.yaml`. Other systems must
not co-tenant this file in v1.

### 4.3 `HideState` (data)

```python
@dataclass
class HideState:
    hide_files:    set[str]
    hide_prefixes: set[str]
    force_visible: set[str]
```

Resolution rule (single source of truth, mirrored in `is_hidden`):

```
visible := path in force_visible
       or (path not in hide_files and no prefix in hide_prefixes matches path)
```

A "prefix match" is `path.startswith(prefix)` where `prefix` ends with
`"/"` or equals an exact directory string. Prefixes never include the
leading `./`. Empty prefix is forbidden.

### 4.4 `HideStore` (mutator + lookup)

```python
class HideStore(Protocol):
    def get(self, repo_key: Path) -> HideState: ...
    def hide_file(self, repo_key: Path, path: str) -> None: ...
    def hide_prefix(self, repo_key: Path, prefix: str) -> None: ...
    def unhide_file(self, repo_key: Path, path: str) -> None: ...
    def reset(self, repo_key: Path) -> None: ...
    def hidden_count(self, repo_key: Path, paths: Iterable[str]) -> int: ...
```

Semantics:
- `hide_file`: adds `path` to `hide_files`. Removes `path` from
  `force_visible` if present.
- `hide_prefix`: adds `prefix` to `hide_prefixes`. Removes any
  `force_visible` entries whose path matches the new prefix.
- `unhide_file`:
  - If `path in hide_files`: remove from `hide_files`.
  - Else if a prefix in `hide_prefixes` matches `path`: add `path` to
    `force_visible`.
  - Else: no-op.
- `reset`: sets all three sets to empty for `repo_key`.
- `hidden_count`: returns the number of `paths` currently resolved as
  hidden under the resolution rule. Used by `DiffHeader` to render the
  badge.

Location:
- Implementation lives on `ChatApp` (one instance per claudechic
  process), keyed by `repo_key`. Internal storage:
  `dict[Path, HideState]`.
- Exposed to `DiffScreen` via constructor injection.
- All entries are dropped when the process exits. No file persistence.

Cross-repo isolation: the `repo_key` argument is mandatory on every
method. Callers never share a `HideState` across `repo_key` values.

### 4.5 `DisplayTree` and `DisplayNode`

```python
@dataclass
class FileNode:
    file_change: FileChange
    hidden: bool

@dataclass
class DirectoryNode:
    prefix: str               # e.g. "claudechic/widgets/"
    children: list["DisplayNode"]

DisplayNode = FileNode | DirectoryNode
DisplayTree = list[DisplayNode]   # roots
```

`build_tree` rules:
- `sort_mode == "alphabetical"`: `DisplayTree` is a flat list of
  `FileNode`, sorted by `file_change.path` (lexicographic).
- `sort_mode == "directory"`: `DisplayTree` is a list whose elements are
  either `FileNode` (files at the repo root) or `DirectoryNode`
  recursively. Files inside the same parent directory share the same
  `DirectoryNode`. Directory order: lexicographic on `prefix`. File order
  inside a directory: lexicographic on `file_change.path`.
- Untracked files (`status == "untracked"`) participate uniformly in
  both modes. No special bucket.

`apply_hide` rules:
- Walks the tree; for each `FileNode`, sets `hidden =
  is_hidden(file_change.path, hide_state)`.
- Does not prune. Widgets decide whether to render hidden nodes (sidebar
  greys, view sets `display: false`).

### 4.6 `focus key`

The pair `(path, hunk_idx)`. `DiffView` stores the current focus key.
Translation to a Textual widget is via `_sanitize_id`-derived DOM ids
(see section 7 for the collision concern).

Sort change does not change focus key. Hide of the focused file moves
focus key to the next visible hunk (forward bias; fallback prev; fallback
empty-state). See section 6.

---

## 5. The crystal (combinations covered)

Sort modes (2) x hide-state shapes (3 archetypal) x source data (1) =
6 archetypal points. All must work without code branches per axis.

| # | Sort           | Hide archetype                              | Expected behavior                                |
|---|----------------|---------------------------------------------|--------------------------------------------------|
| 1 | alphabetical   | empty                                       | flat list; no greyed rows; `hidden: 0` (omitted) |
| 2 | alphabetical   | `hide_files = {a.py}`                       | `a.py` greyed in sidebar, gone from view         |
| 3 | alphabetical   | `hide_prefixes = {tests/}`                  | every `tests/...` greyed, gone from view         |
| 4 | directory      | empty                                       | grouped tree; no greyed rows                     |
| 5 | directory      | `hide_files = {x/y.py}`                     | only `y.py` greyed under `x/`                    |
| 6 | directory      | `hide_prefixes = {tests/}, force_visible = {tests/keep.py}` | every `tests/...` greyed except `tests/keep.py`  |

The `force_visible` mechanism is the third axis-set introduced to make
"un-hide one file under a hidden prefix" possible without removing the
prefix. Combinations 6 must work without bespoke code in widgets.

Untracked-file participation: each archetype above is also valid when
some files have `status == "untracked"`. No additional code path.

---

## 6. Focus-policy contract

`DiffView` owns focus and exposes:

```python
def current_focus_key(self) -> tuple[str, int] | None
def set_focus_key(self, key: tuple[str, int]) -> None
def next_visible_after(self, key: tuple[str, int]) -> tuple[str, int] | None
def prev_visible_before(self, key: tuple[str, int]) -> tuple[str, int] | None
```

Hide actions on `DiffScreen` call:

```python
key = view.current_focus_key()
hide_store.hide_file(repo_key, focused_path)         # or hide_prefix
view.rerender_visibility(hide_state)                 # apply_hide pass
if key is not None and key was just hidden:
    new_key = view.next_visible_after(key) or view.prev_visible_before(key)
    if new_key is not None:
        view.set_focus_key(new_key)
    else:
        view.show_empty_state()
```

`r` (reset) and click-to-unhide do not move focus, except when current
focus is the empty-state placeholder, in which case focus moves to the
first visible hunk in current sort order.

---

## 7. Module structure

New files:

```
claudechic/features/diff/
    git.py                  # existing; updated to return DiffSource
    sort.py                 # NEW: SortMode, SortModeStore, build_tree
    hide.py                 # NEW: HideState, HideStore, is_hidden
    tree.py                 # NEW: DisplayNode, DisplayTree, apply_hide
    widgets.py              # existing; consumes DisplayTree
    header.py               # NEW: DiffHeader widget
```

New attribute on `ChatApp`:

```python
self.diff_hide_store: HideStore   # constructed once at app init
```

Updated `DiffScreen.__init__` signature:

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

Both stores are mandatory keyword arguments. `ChatApp._toggle_diff_mode`
passes them.

Import directions:
- `tree.py` imports `git.py` (for `FileChange`). No reverse import.
- `sort.py` imports `tree.py` and `git.py`.
- `hide.py` imports nothing from `widgets.py`.
- `widgets.py` imports `tree.py`, `sort.py`, `hide.py`. No reverse.
- `header.py` imports `sort.py` and `hide.py` (for state types only).
- `screens/diff.py` is the only module that touches all four.

No circular imports. No widget imports a store implementation; widgets
take protocols.

---

## 8. _sanitize_id collision (P0 carryover)

`_sanitize_id` in `widgets.py` collapses `/`, `.`, and ` ` to `-`. Two
files `a/b.py` and `a-b-py` both map to `a-b-py`. The DOM id space is
the seam between focus key and Textual widgets.

Spec mandates: replace `_sanitize_id` with a collision-free encoding
before issue #19/#20 ship.

Recommended encoding:

```python
def _path_to_id(path: str, hunk_idx: int | None = None) -> str:
    encoded = path.encode("utf-8").hex()
    return f"hunk-{encoded}-{hunk_idx}" if hunk_idx is not None else f"sidebar-{encoded}"
```

`hex()` output is `[0-9a-f]+`, a valid CSS id suffix, and a bijection
with the path. Reverse decoding: `bytes.fromhex(encoded).decode("utf-8")`.

---

## 9. In-place reorder contract (P0 carryover)

Sort change executes inside `DiffView`:

1. Compute new `DisplayTree` from `(changes, new_sort_mode)`.
2. For each existing `FileDiffPanel` and its descendant `HunkWidget`s,
   keep the instance.
3. Use Textual `move_child(child, before=...)` to reorder existing
   `FileDiffPanel`s into the new sequence.
4. `DiffSidebar` does the same for `DiffFileItem`s.
5. After reorder, run `apply_hide` and update each node's `display`
   property; do not remove children.

Forbidden: any code path that re-mounts `HunkWidget`s on sort change.
This is what preserves in-progress hunk comments.

---

## 10. Source command (#18)

`DiffHeader` is the only widget that renders the source command. Its
constructor takes a `DiffSource` and a callback to read current sort
mode + hidden count. It does not run `git diff`. It does not infer the
command from `target`.

Render contract (one line, height 1):
- Left segment: `f"$ {source.command}"`.
- Right segment: `"sort: {mode}    hidden: {N}"`, where `hidden: N` is
  omitted when `N == 0`.
- The `hidden: N` text is a click target wired to `HideStore.reset`.

Truncation rules and width breakpoints are specified in
`uidesigner_design_v4.md` v4.1/v4.2 sections E and "DiffHeader -- ASCII
width mocks" and are inlined here as a binding reference: when total
required width exceeds available, truncate the command with trailing
`...`; right-pin the badges; below 60 cols, drop the `$ ` prefix.

---

## 11. Crystal-hole tests (Specification exit criteria)

The test suite must include, at minimum, one test per row of the table
in section 5, plus:

- `test_focus_survives_sort_change`: focus key before == focus key
  after, sort change preserves `HunkWidget` instance identity, and the
  hunk's comment text is preserved.
- `test_focus_advances_on_hide`: hide of focused file advances focus to
  next visible hunk.
- `test_force_visible_under_prefix`: file under hidden prefix appears
  visible after `unhide_file` adds it to `force_visible`.
- `test_repo_isolation`: `HideStore` operations under one `repo_key` do
  not affect another `repo_key`.
- `test_sanitize_id_no_collision`: `a/b.py` and `a-b.py` produce
  different DOM ids (under the new encoding).
- `test_sort_mode_persistence_roundtrip`: write `directory`, reread,
  observe `directory`.

---

## 12. Out of scope

The following are explicitly not addressed by v1 and require a new
project to introduce:

- Persisting hide state across claudechic process restarts.
- Rename / content_sha keying of hide state.
- Cross-repo hide state sharing.
- Hide of individual hunks (only files / prefixes are hidable).
- Reviewed-state semantics (tri-state, derived directory state).
- Keyboard navigation onto hidden sidebar entries (mouse-only un-hide
  in v1; `r` is the keyboard escape).

---

## Appendix A. Rationale (non-binding)

A.1 Why three-set hide state instead of single set.
The three-set form `(hide_files, hide_prefixes, force_visible)` is the
minimal state that supports user decision NV2 (prefix hides cascade to
new descendants) plus user decision allowing per-file un-hide of a
prefix-greyed entry without removing the whole prefix. Two sets are
insufficient; four are redundant.

A.2 Why widgets read `FileNode.hidden` instead of querying `HideStore`.
Centralizing the resolution in `apply_hide` ensures a single
implementation of `is_hidden`. Widgets cannot drift from the store
because they never see it directly. This is the seam that makes axis 4
swappable without touching widget code.

A.3 Why `repo_key = cwd` verbatim.
Symlink and `git rev-parse --show-toplevel` resolution introduce IO and
edge cases (submodules, symlinked worktrees) for which there is no
reported user pain. Defer until reported.

A.4 Why `_sanitize_id` replacement is in-scope for v1.
Issue #19 (directory sort) plus issue #20 (hide) both increase the
likelihood of distinct paths colliding to the same DOM id, since the
sidebar now renders directory rows alongside file rows in directory
sort mode. Fixing the encoding is cheaper than diagnosing intermittent
focus-jump bugs later.

A.5 Why no axis-specific deep-dive agent spawned.
The v4 simplification (drop reviewed semantics, drop persistence of
hide state) collapsed two axes to one and removed the persistence-shape
question that previously warranted a deep dive. The remaining seams are
small enough to specify here directly.
