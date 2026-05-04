# Terminology -- diff_review_ux Specification

**Author:** Terminology
**Phase:** project-team:specification
**Status:** Working draft for Coordinator + user sign-off
**Supersedes:** Vision v4/v5/v6 domain-terms blocks, all prior Leadership-phase
glossary drafts. Aligned with `SPECIFICATION.md` v6 (DiffHeader retracted;
FilesSection prune for #11/#18 added; `source command` / `DiffSource` /
`hidden count badge` removed).

This file is the **single canonical home** for project terminology. Any other
artifact (Specification.md, design docs, code comments, PR descriptions) must
**reference** these definitions, not redefine them. If a term needs to change,
edit it here first, then sweep dependents.

---

## How to read this file

- **Canonical term** -- the one and only spelling to use in artifacts and code.
- **Definition** -- the precise meaning. Read as a contract, not a hint.
- **Type / Shape** -- when the term names a code-level entity, the Python type.
- **Canonical home** -- where the binding implementation lives (or "this file"
  for terms with no code home yet).
- **Synonyms banned** -- spellings/phrasings that MUST NOT appear in artifacts.
- **Notes** -- newcomer-facing clarifications, links to related terms.

---

## 1. Screen, command, and target

### `DiffScreen`

- **Definition:** The full-screen Textual `Screen` opened by the `/diff` slash
  command. Reviews uncommitted changes (or changes vs an arbitrary git ref).
- **Type:** `class DiffScreen(Screen[list[HunkComment]])`.
- **Canonical home:** `claudechic/screens/diff.py`.
- **Synonyms banned:** "diff panel", "diff view" (when meaning the whole
  screen), "review screen", "diff window".
- **Notes:** Distinct from `DiffView` (the centre pane *inside* the screen)
  and `FileDiffPanel` (one panel *inside* `DiffView`). When in doubt about
  scope, use `DiffScreen`.

### slash command `/diff`

- **Definition:** The user invocation that pushes a `DiffScreen`. Aliased
  `/d`. Optional positional argument is the **diff target**. Also triggers
  the **FilesSection prune** (s4) on the chat screen as a side effect of
  the `_toggle_diff_mode` / `_toggle_diff_mode_for_file` entry points.
- **Canonical home:** `claudechic/commands.py:345` (dispatch).
- **Synonyms banned:** "diff command" (overloaded; see banned list),
  "/d command" (use `/diff` in prose; `/d` only when discussing the alias).

### diff target

- **Definition:** The git ref string passed to `git diff` (default `"HEAD"`).
  Carried as `target: str` on `DiffScreen.__init__`. **Used ONLY for the
  diff content; never as the prune basis** (the prune step is always
  HEAD-relative; SPEC.md s8.6).
- **Type:** `str`.
- **Canonical home:** `claudechic/screens/diff.py:49` (`target` parameter).
- **Synonyms banned:** "ref", "base", "comparison ref", "diff base". (Use
  the existing parameter name `target` everywhere.)

### `source command` -- RETRACTED (v6)

- **Status:** Retracted at v6. The earlier #18 framing as a missing
  "source command field" rendered by a new `DiffHeader` widget was
  abandoned in favour of the v6 FilesSection-prune approach (issue
  #11/#18 reframed as a chat-screen sidebar staleness bug, not a
  DiffScreen labeling gap). See SPEC.md s15 ("No source-command
  rendering") and SPEC_APPENDIX.md C.11.
- **Synonyms banned:** "diff command field", "originating command",
  "command line", "source line", "source command" (the term itself is
  retracted; do not reintroduce as a glossary entry without a fresh
  user decision).

---

## 2. Layout terms (DiffScreen children)

### `DiffHeader` -- RETRACTED (v6)

- **Status:** Retracted at v6 alongside `source command`. The widget
  is not built; no header strip is added to `DiffScreen` in v1. See
  SPEC.md s15 and SPEC_APPENDIX.md C.11.
- **Synonyms banned:** "header bar", "title bar", "metadata strip",
  "command line bar", "DiffScreen header", "DiffHeader" (the class
  name itself; do not reintroduce without a fresh user decision).

### `DiffSidebar`

- **Definition:** Left pane of `DiffScreen` listing every file in the diff
  (visible and hidden). One `DiffFileItem` per file. Hidden when terminal
  width < 100 cols (`SIDEBAR_MIN_WIDTH`).
- **Type:** `class DiffSidebar(Vertical)`.
- **Canonical home:** `claudechic/features/diff/widgets.py:152`.
- **Synonyms banned:** "file list", "left panel", "left sidebar", "the
  sidebar" (overloaded with chat-screen `FilesSection`; always qualify
  as `DiffSidebar` in artifacts).
- **Notes:** Distinct from `FilesSection` (the chat-screen sidebar listing
  edited files since session start). Hide controls live on
  `DiffSidebar`'s `DiffFileItem` entries, NOT on `FilesSection.FileItem`.

### `DiffView`

- **Definition:** Scrollable centre pane of `DiffScreen` containing one
  `FileDiffPanel` per visible file. Owns hunk-navigation state.
- **Type:** `class DiffView(VerticalScroll)`.
- **Canonical home:** `claudechic/features/diff/widgets.py:519`.
- **Synonyms banned:** "right panel" (informal user-facing prose only),
  "main panel", "diff content area", "centre pane".

### `FileDiffPanel` (a.k.a. **file panel**)

- **Definition:** Per-file section inside `DiffView`. Contains the file
  header label, optional markdown preview toggle, and the file's
  `HunkWidget`s separated by `HunkSeparator`s.
- **Type:** `class FileDiffPanel(Vertical)`.
- **Canonical home:** `claudechic/features/diff/widgets.py:403`.
- **Allowed shorthand:** "file panel" (lower-case, prose).
- **Synonyms banned:** "diff panel" (overloads `DiffScreen`), "file pane",
  "file section", "file block".

### `DiffFileItem`

- **Definition:** Single sidebar row representing one changed file. Posts
  `Selected` (programmatic highlight) and `Clicked` (user interaction)
  messages. Renders status letter, path, hunk count, edit icon. Carries
  the **hidden render variant** (dot prefix, muted color, strike-through
  on path) when its file is in the **hide state**.
- **Type:** `class DiffFileItem(Static)`.
- **Canonical home:** `claudechic/features/diff/widgets.py:88`.
- **Synonyms banned:** "sidebar entry", "sidebar row" (informal prose
  only), "file row".
- **Notes:** Today `DiffFileItem` is `Static`, not focusable (Skeptic P2).
  v1 leaves it `Static`; granular keyboard un-hide is deferred.

### hunk

- **Definition:** A single `@@`-delimited section of unified diff output.
  Lower-case in prose; class name is `Hunk`.
- **Type:** `dataclass Hunk` (`old_start`, `old_count`, `new_start`,
  `new_count`, `old_lines`, `new_lines`).
- **Canonical home:** `claudechic/features/diff/git.py:11`.
- **Synonyms banned:** "diff section", "diff block", "chunk".

### `HunkWidget`

- **Definition:** Focusable widget rendering a single `Hunk` plus its
  optional inline comment.
- **Type:** `class HunkWidget(Static, can_focus=True)`.
- **Canonical home:** `claudechic/features/diff/widgets.py:274`.
- **Synonyms banned:** "hunk row", "hunk block".
- **Visual reservation:** `HunkWidget.has-comment` owns `border-left:
  $warning`. No new feature in this project may use `$warning` on
  `HunkWidget` or its descendants. Strike-through is unused on
  `HunkWidget` and is reserved-but-free for future use.

### `HunkComment`

- **Definition:** A reviewer's comment attached to a single `Hunk` on a
  given file path. Returned in a list when `DiffScreen` dismisses.
- **Type:** `dataclass HunkComment(path, hunk, comment)`.
- **Canonical home:** `claudechic/features/diff/git.py:23`.
- **Notes:** Sort and hide actions MUST preserve `HunkWidget` instances
  in-place so their attached comments survive (Skeptic P0). Hidden files
  retain their comments; comments from hidden hunks are still returned
  on `DiffScreen` dismiss.

---

## 3. Sort

### sort mode

- **Definition:** Ordering rule for `DiffFileItem`s in `DiffSidebar` and
  `FileDiffPanel`s in `DiffView`. Two values:
  - **`alphabetical`** -- flat, case-insensitive ascending by path. The
    pre-project legacy ordering.
  - **`directory`** -- grouped by parent directory; directory header rows
    appear in `DiffSidebar` (directory sort only); files within a group
    sorted alphabetically. **Default on first run.**
- **Type:** `Literal["alphabetical", "directory"]`.
- **Canonical home:** `claudechic/features/diff/sort.py` (per SPEC.md s12).
- **Persistence:** **per-repo**, written to **`<repo>/.claudechic/diff.yaml`**
  (a dedicated file; NO co-tenancy with `config.yaml` in v1) under the
  top-level key **`sort_mode`**. See SPEC.md s9.2 for full schema and
  fallback semantics.
- **Sidebar rendering:** in `directory` mode the `DisplayTree` carries
  `DirectoryNode` grouping and the sidebar renders one `DiffDirectoryItem`
  row per `DirectoryNode`. Each `DiffDirectoryItem` contains a `DirFoldGlyph`
  (`[-]`/`[+]`) and a `DirNameLabel` (prefix with trailing `/`). The
  `DirFoldGlyph` toggles sidebar fold state; the `DirNameLabel` click
  toggles hide state for the entire prefix. See SPEC.md s4.3 and s7.2.
  In `alphabetical` mode, no `DiffDirectoryItem` rows appear.
- **Synonyms banned:** "alpha", "flat", "flat-alphabetical", "flat-alpha",
  "grouped", "grouped-by-directory", "directory-grouped", "by directory",
  "sort order".
- **Notes:** Sort change MUST be **in-place DOM reorder** of mounted
  children -- never a `DiffView` rebuild (preserves `HunkWidget`
  instances and their comments; Skeptic P0). Sort is **orthogonal** to
  hide and focus.

### `sort badge` -- WIDGET RETRACTED (v6); content survives via sub-title (Polish #1, CP-A)

- **Status:** The **widget** is retracted alongside `DiffHeader` at v6.
  No custom right-aligned text widget renders the sort mode in v1.
- **Content survival:** The user-visible string format `sort: <mode>`
  -- previously carried by this retracted widget -- SURVIVES at a
  different rendering surface as **`sort sub-title`** below (Polish
  #1, accepted at CP-A). The retraction was specifically about the
  widget surface (`DiffHeader` was the user's grievance, not the
  string content).
- **Synonyms banned:** "sort indicator" (the widget term),
  "mode label", "sort label". Use **`sort sub-title`** for the
  surviving sub-title chrome surface.

### `sort sub-title` (Polish #1, accepted at CP-A)

- **Definition:** A user-visible string of the form `f"sort: {mode}"`
  (concretely `"sort: directory"` or `"sort: alphabetical"`)
  rendered via Textual's built-in `Screen.sub_title` chrome on
  `DiffScreen`. Updated whenever the active sort mode changes (on
  mount, on `s` keypress). NOT a custom widget -- this is Textual's
  framework-provided Screen-chrome surface, distinct from the
  retracted `DiffHeader` / `sort badge` widget.
- **Type:** the string assigned to `Screen.sub_title: str` on
  `claudechic/screens/diff.py:DiffScreen`. SPEC.md still says "no
  source-command rendering" (s15); the sort sub-title is a separate,
  additive surface that does NOT carry the retracted **`source
  command`** content.
- **User-observable:** Yes. Tests assert exact-equality on
  `screen.sub_title == "sort: directory"` etc. (`tests/test_diff_workflows.py`
  W3).
- **Synonyms banned:** "sort badge" (refers to the retracted widget;
  use `sort sub-title` for the sub-title surface), "sort label",
  "sort indicator", "subtitle" (one word -- use the hyphenated
  `sub-title` to match Textual's `Screen.sub_title` attribute).
- **Notes:** This is the only on-screen indicator of the active sort
  mode in v1. The footer help label `"Sort"` is the keyboard
  affordance for changing it (s11); the sub-title is the read-only
  status indicator for the current value. Together they cover both
  the action and the state.

---

## 4. Hide

### hide / unhide (verbs)

- **Definition:**
  - **hide** -- mark a file or directory so its `FileDiffPanel` and
    `HunkWidget`s are not rendered in `DiffView`; the `DiffFileItem`
    in `DiffSidebar` is rendered with the **hidden render variant**.
  - **unhide** -- the inverse. Restore normal rendering.
- **Spelling rule:** **`unhide`** (one word) in prose, identifiers,
  section headings, and method names (`hide_store.unhide_file(...)`).
  The hyphenated form **`un-hide`** is permitted ONLY inside literal
  user-facing display strings -- tooltips and the empty-state placeholder
  body in `DiffView` (per SPEC.md s6.4, s7, s8.4) -- where the hyphen
  improves readability.
- **Synonyms banned:** "show", "reveal", "vanish", "exclude", "filter
  out", "hide flag" (use `hidden` as the state word). "show" is reserved
  for unrelated UI patterns and is too ambiguous as the inverse of "hide".

### hidden / visible (states)

- **Definition:** The two values of a file's **hide state**. A file is
  either `hidden` or `visible`. There are no other states. Directories
  are not states; they have no stored state (see **directory hide
  action**).
- **Synonyms banned:** "shown", "displayed", "revealed", "active",
  "filtered" (for either value).

### hide state (a.k.a. `HideState`)

- **Definition:** The current visibility decisions and sidebar fold state
  for one repo within one claudechic process. Concretely a `dataclass`
  of four string sets: `hide_files`, `hide_prefixes`, `force_visible`,
  `folded_prefixes`. Resolution rule for visibility: see **`is_hidden`**
  (SPEC.md s4 / s5.2). A file is `hidden` iff `path not in force_visible
  AND (path in hide_files OR any prefix in hide_prefixes matches path)`.
  `folded_prefixes` is orthogonal: it affects only the sidebar fold glyph
  and child-row visibility in DiffSidebar; it does NOT affect `is_hidden`.
- **Type:** `dataclass HideState(hide_files: set[str], hide_prefixes:
  set[str], force_visible: set[str], folded_prefixes: set[str])` per
  SPEC.md s5.1.
- **Canonical home:** `claudechic/features/diff/hide.py` (per SPEC.md s12).
- **Persistence:** **none.** Cleared when claudechic exits. See
  **session-scoped, repo-keyed**.
- **Synonyms banned:** "hide flags", "hidden files map", "review state",
  "hide list", "hide map".

### `is_hidden`, `is_folded`, `is_prefix_hidden`, `longest_matching_prefix` (HideState methods)

- **`is_hidden(path: str) -> bool`** -- single source of truth for
  visibility (SPEC.md s4 / s5.1 / s5.2). Resolution: `path in
  force_visible -> False`; else `path in hide_files -> True`; else any
  prefix in `hide_prefixes` matches `path`. Every consumer (widgets,
  controller, `apply_hide`) calls this method; no consumer reads the
  four sets directly (s3.1 / s4).
- **`is_folded(prefix: str) -> bool`** -- returns True if `prefix` is
  in `folded_prefixes`. Called by `DiffSidebar` to drive `DirFoldGlyph`
  glyph and child-row visibility. Fold is orthogonal to hide; calling
  this method does not change the return value of `is_hidden`.
- **`is_prefix_hidden(prefix: str) -> bool`** -- returns True if
  `prefix` is in `hide_prefixes`. Called by `DiffDirectoryItem` to
  style `DirNameLabel` (muted+strike when True) without reading
  `hide_prefixes` directly (s3.1 compliance).
- **`longest_matching_prefix(path: str) -> str | None`** -- returns
  the longest entry of `hide_prefixes` matching `path`, or `None` if
  no prefix matches. Used by `_hidden_tooltip` in `widgets.py` to
  render the "click to un-hide just this file (`<prefix>` stays
  hidden)" tooltip text without dipping into `hide_prefixes`. Added
  at CP3 to keep widgets compliant with s3.1 / s4.
- **Canonical home:** `claudechic/features/diff/hide.py:HideState`,
  with matching declarations on `HideStateProtocol` (below).
- **Synonyms banned:** "hidden_for", "matches_path", "is_visible"
  (negated form -- prefer `not is_hidden(...)`), "longest_prefix"
  (drop the qualifier; the qualifier IS the meaning),
  "is_collapsed", "is_expanded" (use `is_folded` and `not is_folded`),
  "prefix_hidden" (use `is_prefix_hidden`).

### `HideStateProtocol` (CP3; extended post-M1)

- **Definition:** Type-only `Protocol` covering the read-side of
  `HideState`: `is_hidden(path)`, `is_folded(prefix)`,
  `is_prefix_hidden(prefix)`, and `longest_matching_prefix(path)`.
  Distinct from `HideStoreProtocol` (which covers store-level
  mutators). Widgets and the tooltip helper take `HideStateProtocol`
  rather than concrete `HideState` so tests can substitute fakes.
- **Canonical home:** `claudechic/features/diff/hide.py`.
- **Convention:** Same `Protocol` suffix as `HideStoreProtocol` /
  `SortModeStoreProtocol`. Internal name only; never user-facing.
- **Synonyms banned:** "IHideState", "AbstractHideState",
  "HideStateBase", "HideStateView", "HideStateReader". Use the
  `Protocol` suffix only.

### `HideStore` / `HideStoreProtocol` (split, accepted at CP2)

- **Definition:** SPEC.md s5.3 uses the single name `HideStore` for both
  the `typing.Protocol` and its concrete implementation. At
  implementation time CP2 split this into two distinct names:
  - **`HideStoreProtocol`** -- the type-only `Protocol` consumed by
    widgets and tests for dependency injection (SPEC.md s12.1: "widgets
    take protocols"). Methods: `get`, `hide_file`, `hide_prefix`,
    `unhide_file`, `unhide_prefix`, `fold_prefix`, `unfold_prefix`,
    `reset`.
  - **`HideStore`** -- the concrete in-memory implementation owning
    `dict[Path, HideState]` on `ChatApp`.
- **Canonical home:** Both live in `claudechic/features/diff/hide.py`.
- **Convention:** The `Protocol` suffix is a recognized Python idiom
  (PEP 544 style). Used identically for **`SortModeStore`** /
  **`SortModeStoreProtocol`** in `claudechic/features/diff/sort.py`.
- **Synonyms banned:** "IHideStore" (Hungarian-style prefix),
  "AbstractHideStore", "HideStoreBase". Use the `Protocol` suffix only.
- **Notes:** Internal names only; neither appears in user-visible UI.
  When SPEC.md / docs say "HideStore" without qualification, they
  generally mean either the protocol or the concrete class
  interchangeably, which is the intended behavior of dependency-injected
  storage. Code that needs to disambiguate (e.g. tests) uses the
  explicit `Protocol`-suffixed name.

### `hide_files` / `hide_prefixes` / `force_visible` / `folded_prefixes` (the four sets)

- **`hide_files: set[str]`** -- individually hidden file paths. Entries
  never end with `/` (real file paths don't). Added by keybinding `f`.
- **`hide_prefixes: set[str]`** -- hidden directory prefixes. Entries
  ALWAYS end with `/` (the trailing slash IS the file/prefix
  disambiguator). Empty prefix is forbidden. No leading `./`. Added by
  keybinding `d`.
- **`force_visible: set[str]`** -- per-file overrides that win against
  prefix membership but NOT against `hide_files` membership. Added when
  a user clicks a hidden `DiffFileItem` whose hidden state came from a
  prefix (A2 click resolution; SPEC.md s5.3 `unhide_file`).
- **`folded_prefixes: set[str]`** -- sidebar fold state. Entries are
  directory prefixes currently collapsed in `DiffSidebar`. A folded
  prefix's `DiffFileItem` children are not rendered in the sidebar; its
  `FileDiffPanel`s in `DiffView` are unaffected. `folded_prefixes` is
  orthogonal to the three hide sets; its entries have NO effect on
  `is_hidden(path)`. Added / removed by `fold_prefix` / `unfold_prefix`
  (DirFoldGlyph click); cleared by `reset`.
- **Canonical home:** `HideState` dataclass in
  `claudechic/features/diff/hide.py`.
- **Synonyms banned:** "blacklist", "whitelist", "exclude set", "include
  set", "force-show set", "collapsed_prefixes" (use `folded_prefixes`),
  "fold_state" (the set is called `folded_prefixes`).

### prefix match

- **Definition:** Boolean test `path.startswith(prefix)` where `prefix`
  is an entry of `hide_prefixes` (always ends with `/`). Empty prefix is
  forbidden. SPEC.md s2.
- **Synonyms banned:** "prefix hit", "subtree match", "directory match".

### directory hide action

- **Definition:** A user action that adds a directory prefix to
  `hide_prefixes`. Two triggers in v1:
  - Keybinding `d` on the focused file -- adds `to_prefix(path)` to
    `hide_prefixes` (or no-op + transient hint for root-level files).
  - Click on `DirNameLabel` in a `DiffDirectoryItem` (directory sort mode
    only) -- adds the row's prefix to `hide_prefixes` if not already
    hidden; removes it if already hidden (toggle via `unhide_prefix`).
  Directories carry no stored state of their own beyond `hide_prefixes`
  membership; visibility is computed from descendant file states on render
  via `is_hidden(path)`.
- **Root-level no-op:** if the focused file is at the repo root
  (`to_prefix(path)` returns `None`), `d` is a no-op and DiffScreen
  surfaces a transient hint via `self.notify(...)` with the locked
  message **`no parent directory to hide`** (SPEC.md s5.5; verbatim
  string).
- **Synonyms banned:** "bulk hide", "directory hide flag", "group hide",
  "hide directory" (when used as a noun for the action -- use the full
  three-word phrase or "the `d` action").
- **Notes:** "bulk hide" is permitted as an *explanatory gloss* in prose,
  never as a section heading or code identifier.

### `to_prefix` (renamed from `_to_prefix` at CP3)

- **Definition:** Helper that returns the direct-parent prefix of a
  path (always ending with `/`), or `None` for repo-root files (no
  `/` separator). The prefix string is what `d` adds to
  `hide_prefixes`.
- **Canonical home:** `claudechic/features/diff/tree.py` (moved from
  `hide.py` at CP3 per Skeptic S2 cleanup; consolidates with
  `DisplayTree` types).
- **Naming history:** Was `_to_prefix` (private) in CP2; promoted to
  public `to_prefix` at CP3 because `screens/diff.py:DiffScreen.action_hide_dir`
  now imports it. The leading underscore is dropped to signal the
  cross-module API role.
- **Synonyms banned:** "parent_dir", "parent_prefix", "dirname_prefix",
  "_to_parent_prefix" (the duplicate that briefly lived in `sort.py`
  at CP2; removed at CP3).

### hide controls

- **Definition:** The set of UI affordances and keybindings that mutate
  **hide state** (transitions defined in SPEC.md s5.5):
  - keybinding `f` -> `hide_store.hide_file(repo_key, path)`
  - keybinding `d` -> if `_to_prefix(path)` is None (root-level file):
    no-op + transient footer hint `no parent directory to hide`; else
    `hide_store.hide_prefix(repo_key, _to_prefix(path))`
  - keybinding `r` -> `hide_store.reset(repo_key)` (clears all four sets)
  - click on hidden `DiffFileItem` -> `hide_store.unhide_file(repo_key,
    path)` (**A2 semantics**: independent clauses -- if path is in
    `hide_files`, remove it; then if a prefix matches, add `path` to
    `force_visible`; post-condition `is_hidden(path) == False`)
  - click on `DirNameLabel` (directory mode, prefix NOT hidden) ->
    `hide_store.hide_prefix(repo_key, prefix)`
  - click on `DirNameLabel` (directory mode, prefix IS hidden) ->
    `hide_store.unhide_prefix(repo_key, prefix)` (removes prefix from
    `hide_prefixes` and clears any `force_visible` entries under it)
  - click on `DirFoldGlyph` -> `fold_prefix` / `unfold_prefix` (fold
    is sidebar-visual only; does NOT mutate the three hide sets)
- **Canonical home:** `DiffScreen.BINDINGS` plus `DiffFileItem.on_click`.
- **Notes:** v6 has NO clickable `hidden: N` badge (DiffHeader retracted).
  The only unhide path on a narrow terminal (sidebar collapsed) is
  keybinding `r`; users must widen the terminal to use the click-to-unhide
  affordance on individual entries.

### `fold_prefix` / `unfold_prefix` / `unhide_prefix` (HideStore mutators)

- **`fold_prefix(repo_key, prefix)`** -- adds `prefix` to
  `folded_prefixes`. Sidebar-visual only. Triggered by `DirFoldGlyph`
  click on an unfolded row (SPEC.md s5.5). Does NOT affect `is_hidden`.
- **`unfold_prefix(repo_key, prefix)`** -- removes `prefix` from
  `folded_prefixes`. Triggered by `DirFoldGlyph` click on a folded row.
- **`unhide_prefix(repo_key, prefix)`** -- removes `prefix` from
  `hide_prefixes` and clears any `force_visible` entries whose path
  starts with `prefix` (they are moot once the prefix is un-hidden).
  Triggered by `DirNameLabel` click on a hidden directory header
  (SPEC.md s5.5). Inverse of `hide_prefix`.
- **Canonical home:** `claudechic/features/diff/hide.py:HideStore`.
- **Synonyms banned:** "collapse_prefix" (use `fold_prefix`),
  "expand_prefix" (use `unfold_prefix`), "show_prefix" (use
  `unhide_prefix`), "clear_prefix" (ambiguous).

### `DiffDirectoryItem` / `DirFoldGlyph` / `DirNameLabel`

- **`DiffDirectoryItem`** -- widget class rendered in `DiffSidebar`
  for each `DirectoryNode` in `directory` sort mode. One row per
  directory group. Contains exactly two sub-components: `DirFoldGlyph`
  and `DirNameLabel`. Does NOT appear in `alphabetical` sort mode.
- **`DirFoldGlyph`** -- sub-component of `DiffDirectoryItem`. Renders
  `[-]` (unfolded) or `[+]` (folded). Clicking calls
  `fold_prefix` / `unfold_prefix`. Color is always the neutral accent;
  it does NOT change when the prefix is hidden.
- **`DirNameLabel`** -- sub-component of `DiffDirectoryItem`. Renders
  the directory prefix string (always ends with `/`). Clicking toggles
  hide state: `hide_prefix` (when not hidden) or `unhide_prefix` (when
  hidden). Visual treatment: normal color when not hidden; `$text-muted`
  + `text-style: strike` when `is_prefix_hidden(prefix)` is True. See
  SPEC.md s7.2 for the full four-state table.
- **Canonical home:** `claudechic/features/diff/widgets.py`.
- **Synonyms banned:** "directory header", "dir header row",
  "DirectoryHeader", "FoldGlyph" (missing `Dir` prefix),
  "DirectoryNameLabel" (use `DirNameLabel`).

### hidden render variant

- **Definition:** The visual treatment of a `DiffFileItem` whose file is
  `hidden`: status letter replaced by a `.` dot in `$text-muted`; path
  text in `$text-muted` with `text-style: strike`; hunk count `(N)` in
  `$text-muted` (no strike); `EditIcon` unchanged; `.active` class never
  applied. Visual treatment is identical regardless of which set caused
  the hide (per SPEC.md s7).
- **Canonical home:** `DiffFileItem.compose()` (modified) plus the
  `.hidden-entry` CSS class declared in `claudechic/styles.tcss`.
- **Allowed alias:** **`greyed`** -- informal one-word synonym used in
  user-facing copy (tooltips, empty-state text, acceptance-criteria
  tables in SPEC.md s14.4). When `greyed` appears in artifacts it MUST
  refer to this entry; do not use it for any other dimmed/de-emphasized
  state.
- **Synonyms banned:** "ghost entry", "dimmed entry", "strike-through
  item", "faded entry".
- **Notes:** v4.2 retracts the bottom-of-sidebar `[+] Hidden (N)`
  collapsed group from v4/v4.1. Hidden entries are now rendered
  in-place in their natural sort slot.

### `hidden count badge` -- RETRACTED (v6)

- **Status:** Retracted alongside `DiffHeader` at v6. No on-screen
  hidden-count widget in v1; no clickable badge surfaces "unhide all".
  See SPEC.md s15 / SPEC_APPENDIX.md C.11.
- **Synonyms banned:** "hide counter", "N hidden label", "hidden: N
  badge".

### unhide all (display-string form: `un-hide all`)

- **Definition:** A single user action that empties the current repo's
  `HideState` (clears all three sets: `hide_files`, `hide_prefixes`,
  `force_visible`). Triggered by keybinding `r` only
  (`hide_store.reset(repo_key)`). v6 has no badge or button alternative
  (see retracted `hidden count badge`).
- **Allowed alias:** "reset hides" (footer label for `r`, per SPEC.md
  s11).
- **Synonyms banned:** "clear hides" ("clear" is ambiguous), "show
  all", "reveal all".

---

## 4a. FilesSection prune (#11/#18, v6)

### `FilesSection`

- **Definition:** Existing chat-screen sidebar widget that lists files
  Claude has edited during the conversation. Lives on the chat screen,
  NOT inside `DiffScreen`. Distinct from `DiffSidebar`.
- **Type:** `class FilesSection(SidebarSection)`.
- **Canonical home:**
  `claudechic/widgets/layout/sidebar.py:FilesSection`.
- **Internal state:** `_files: dict[Path, FileItem]` is the source of
  truth for "files currently in this section."
- **Synonyms banned:** "files panel", "edit list", "file list" (when
  meaning the chat-screen widget; reserve "DiffSidebar" for the
  DiffScreen file list).
- **Notes:** Newcomer disambiguation -- "Files" and "DiffSidebar" both
  list files, but in different contexts. The **FilesSection prune**
  step (below) only mutates `FilesSection`; it never touches
  `DiffSidebar`.

### `FilesSection prune` (verb / step) (NEW for v6)

- **Definition:** The remove-only operation that runs on every `/diff`
  invocation (in `claudechic/app.py:_toggle_diff_mode` and
  `_toggle_diff_mode_for_file`) immediately before `DiffScreen` is
  pushed. Removes any entry from `FilesSection._files` whose path is
  not in the current **dirty path set**. Never adds files. Failure of
  the underlying subprocess is silent (fail open; SPEC.md s8.7).
- **Canonical home:** `ChatApp._prune_files_section_to_git(agent)`
  (orchestrator) calling `FilesSection.prune_to(dirty: set[Path])`
  (mutator). SPEC.md s8.3 / s8.4.
- **Synonyms banned:** "trim", "filter out", "clean up", "refresh"
  (FilesSection has a separate `_async_refresh_files` flow on
  agent-switch; do not conflate), "sync", "reconcile".
- **Notes:** Prune-only invariant (SPEC.md s8.5): the step NEVER adds
  entries. Files appearing in the dirty path set that are NOT currently
  in `FilesSection._files` are ignored. The agent-switch flow remains
  the sole add-path.

### dirty path set

- **Definition:** The `set[str]` of paths returned by
  `get_dirty_paths(cwd)`. Represents working-tree dirtiness vs `HEAD`
  via `git status --porcelain -z`. Includes tracked-modified, staged,
  AND all untracked entries (NO truncation, unlike `get_changes` /
  `get_file_stats` which cap untracked at `MAX_UNTRACKED_FILES`).
  Renames and copies (`R` / `C` status) yield the destination path
  only; the source path is dropped.
- **Type:** `set[str]` (forward-slash paths, matching `git` output).
  Coerced to `set[Path]` at the App-orchestration boundary before
  passing to `FilesSection.prune_to`.
- **Canonical home:** Returned by **`get_dirty_paths`** in
  `claudechic/features/diff/git.py`.
- **Synonyms banned:** "dirty set", "modified set", "changed set",
  "diff set", "stat set".

### `get_dirty_paths`

- **Definition:** New async helper added in v6.
  Signature: `async def get_dirty_paths(cwd: str) -> set[str]`. Single
  subprocess to `git status --porcelain -z`; parses NUL-terminated
  entries; on subprocess failure returns the empty set so callers can
  fail open. UTF-8 throughout. SPEC.md s8.2.
- **Canonical home:** `claudechic/features/diff/git.py`, exported via
  `claudechic/features/diff/__init__.py`.
- **Synonyms banned:** "list_dirty", "get_changed_paths", "get_diff_paths",
  "scan_working_tree".
- **Notes:** This is the ONLY function used to compute the prune
  basis. SPEC.md s3.1 forbids reusing `get_changes` or `get_file_stats`
  for prune (they truncate untracked).

### prune basis

- **Definition:** The reference state used by FilesSection prune to
  decide which entries to drop. **Always `HEAD`** (SPEC.md s8.6); never
  the `target` argument that `DiffScreen` may have received.
  `git status` is inherently HEAD-relative; this rule is restated to
  prevent a future refactor from threading `target` into the prune
  flow.
- **Synonyms banned:** "diff base for prune", "prune target",
  "prune ref".

---

## 5. Persistence and scoping

### session-scoped, repo-keyed

- **Definition:** A storage property: data lives only in memory inside one
  claudechic process, partitioned by repo. Specifically, the App-level
  `HideStore` holds `dict[Path, HideState]` keyed by **`repo key`**.
  Lifetime: one claudechic process. Visibility: only entries for the
  current `repo key` are read by a `DiffScreen` instance. Cross-repo
  bleed is impossible (per SPEC.md s5.4).
- **Synonyms banned:** "in-memory only", "non-persisted", "per-session,
  per-repo", "ephemeral".
- **Notes:** This phrasing replaces the looser "in-memory only / per-repo
  within session" used in v4 prose. Use the canonical compound phrase
  verbatim in artifacts. SPEC.md s2 defines `session-scoped` as the
  lifetime half alone; the keying half is supplied by **`repo key`**.

### claudechic-process-scoped

- **Definition:** Synonym for the **lifetime** half of session-scoped,
  repo-keyed; named explicitly when contrasted with "DiffScreen-scoped"
  (which would die on screen dismiss). The **hide state** is
  **claudechic-process-scoped**, not DiffScreen-scoped: closing and
  reopening `DiffScreen` within one claudechic session preserves hides.
- **Synonyms banned:** "app-scoped" (correct in code, but in prose use
  the explicit phrase to remind readers what dies and when),
  "claudechic-scoped" (ambiguous between process and install).

### per-repo (sort mode persistence)

- **Definition:** Stored in **`<repo>/.claudechic/diff.yaml`** (a
  dedicated file; no co-tenancy with `config.yaml` in v1) under the
  top-level key `sort_mode`. Survives claudechic exit. Distinct from
  `~/.claudechic/config.yaml` (user-tier preferences) and from
  `<repo>/.claudechic/config.yaml` (project-tier general config). Sort
  mode lives at the repo tier so different repositories can carry
  different defaults. Full schema and fallback rules: SPEC.md s9.2.
- **Synonyms banned:** "global config" (incorrect for sort mode),
  "project config" (potentially confusing with `.project_team/`),
  "<repo>/.claudechic/config.yaml" (wrong file for sort mode in v1).

### `repo key`

- **Definition:** The repo-keying primitive used by both `HideStore` and
  `SortModeStore`. **Locked decision (SPEC.md s2):** the **raw `cwd:
  Path`** as `DiffScreen` receives it (i.e., the value passed to
  `DiffScreen.__init__`, generally the active agent's `cwd`). No
  symlink resolution. No `git rev-parse --show-toplevel` call. Two
  invocations whose `cwd` paths differ are treated as different repos,
  even if they share a git toplevel.
- **Type:** `Path`.
- **Synonyms banned:** "repo path", "git toplevel", "repo root",
  "repo_cwd" (the earlier draft name -- this entry supersedes it).
- **Notes:** Was an open question through Leadership; locked by user
  decision at the v4.2 round. SPEC.md SPEC_APPENDIX.md should document
  the trade-off (worktree split, subdirectory invocations) for
  downstream readers.

---

## 6. Keybindings (Specification-locked)

The canonical binding table for `DiffScreen.BINDINGS` is:

| Key   | Action                              | Footer label    | Term                  |
|-------|-------------------------------------|-----------------|-----------------------|
| `s`   | toggle sort mode                    | "Sort"          | sort mode             |
| `f`   | hide focused file                   | "Hide file"     | hide                  |
| `d`   | directory hide action               | "Hide dir"      | directory hide action |
| `r`   | un-hide all (current repo)          | "Reset hides"   | un-hide all           |

Migration of `j k up down enter o q escape` from `on_key` to `BINDINGS` is
implementer-driven and uses the existing terms (no new vocabulary).

- **Synonyms banned:** "Mark as reviewed" (any), "Toggle review" (any),
  "Show file", "Reveal file".

---

## 7. State semantics on `/diff` re-run within one claudechic session

These are *not* new terms; they are a contract that uses the terms above.
Reproduced here so artifacts referring to them have one canonical statement:

- A file in the previous diff that was **hidden** and is still in the new
  diff: **hidden** (its `hide_files` entry, or the `hide_prefixes` entry
  matching it, survives).
- A file new to this diff (not previously seen): **visible** -- unless its
  path matches an existing `hide_prefixes` entry, in which case it
  inherits **hidden**.
- A file that left the diff and later returns within the same session:
  **hidden** if any matching `hide_files` or `hide_prefixes` entry
  survives in the repo's `HideState`.
- Closing claudechic: the `HideStore` is destroyed; all `HideState`
  entries (`hide_files`, `hide_prefixes`, `force_visible`,
  `folded_prefixes`) are gone.

---

## 8. Dropped (do NOT reintroduce)

### Dropped from v3

The following terms were proposed in v2/v3 and are RETRACTED. Any artifact
mentioning them is stale and must be rewritten:

- "review checkmark", "reviewed-checkmark", "review checkbox"
- "review state", "review state map"
- "directory review state"
- "reviewed visibility", "hide-vs-dim"
- "indeterminate", "full / none / indeterminate"
- "content_sha", "rename migration", "GC of stale entries"
- "Mark as reviewed" keybinding
- `ReviewStore` protocol (Composability axis 4 from v3)
- Bottom-of-sidebar `[+] Hidden (N)` collapsed group (retracted at v4.2
  in favour of in-place hidden render variant)

### Dropped at v6 (DiffHeader retraction)

Retracted alongside the v6 redirect that reframed #18 as a FilesSection
prune problem. Earlier drafts referenced these as live terms; v6 has no
custom widget rendering them. **Note on same-content / different-surface
survival:** the `sort: <mode>` string previously carried by `sort badge`
SURVIVES as **`sort sub-title`** (Polish #1, accepted at CP-A) via
Textual's built-in `Screen.sub_title` chrome -- a different rendering
surface, not a re-introduction of the retracted widget. The
`source command` string and the `hidden: N` badge content do NOT
survive in v1.

- `DiffHeader` (the custom widget itself)
- `source command` (the rendered `git diff <target>` string -- not
  surfaced anywhere in v1)
- `DiffSource` (the producer dataclass; no longer needed)
- `sort badge` (the right-aligned widget text element in DiffHeader;
  the `sort: <mode>` STRING content survives at the sub-title surface
  -- see `sort sub-title` in section 3)
- `hidden count badge` (clickable `hidden: N` element in DiffHeader;
  not surfaced anywhere in v1, no equivalent surface)
- "load_diff_source" helper (was the proposed factory; not needed in v6)

---

## 9. Newcomer simulation

A new contributor reading `userprompt.md` + this glossary cold should be able
to answer:

| Question                                          | Answer (and term used)                           |
|---------------------------------------------------|--------------------------------------------------|
| What does `/diff` open?                           | A `DiffScreen`.                                  |
| Where is the file list?                           | The `DiffSidebar` (left pane of `DiffScreen`).   |
| Where is the actual diff content?                 | The `DiffView` (centre pane of `DiffScreen`).    |
| Is there a header strip showing the git command?  | No. The earlier `DiffHeader` proposal was retracted at v6. DiffScreen has no metadata strip in v1. |
| What happens when I press `f`?                    | The focused file is **hidden** (its **hide state** flips). It greys out in the `DiffSidebar` and disappears from the `DiffView`. |
| What happens when I press `d`?                    | The **directory hide action** runs: the focused file's parent directory (with trailing `/`) is added to `hide_prefixes`; every descendant file is now hidden via **prefix match**. |
| What happens when I press `r`?                    | **unhide all** for the current repo (`HideState.reset` clears all three sets). |
| Do my hides survive closing claudechic?           | No. The **hide state** is **session-scoped, repo-keyed**. |
| Does my sort choice survive closing claudechic?   | Yes. **Sort mode** is persisted **per-repo** in `<repo>/.claudechic/diff.yaml` under key `sort_mode`. |
| What is the difference between `DiffScreen` and `DiffView`? | `DiffScreen` is the whole screen; `DiffView` is just the centre pane inside it. The bare word "panel" is banned to avoid this confusion. |
| What is a "file panel"?                           | A `FileDiffPanel`: the per-file section inside `DiffView`. |
| What does the dot `.` mean in front of a sidebar entry? | That file is **hidden** (the **hidden render variant** of `DiffFileItem`). |
| Why does the chat-screen Files panel sometimes lose entries when I open `/diff`? | The **FilesSection prune** step: every `/diff` invocation removes any `FilesSection` entry whose path is not in the current **dirty path set** (`get_dirty_paths(cwd)`). Prune-only -- never adds. Failure of `git status` is silent (fail open). |
| Is the `target` argument ever used as the prune basis? | No. The **prune basis** is always `HEAD`. `target` only controls the diff content shown by `DiffView`. |

If a downstream artifact uses any term not in this file, or uses a banned
synonym, that artifact MUST be edited before Specification exit.

---

## 10. Open glossary dependencies (all four CLOSED)

All four open dependencies from earlier drafts are now resolved by SPEC.md:

1. **`HideStore` module location** -- LOCKED to
   `claudechic/features/diff/hide.py` (SPEC.md s12). Reflected in
   **hide state** and **`HideState`** entries.
2. **Prefix-vs-file disambiguator** -- LOCKED in SPEC.md s5.1. Two
   separate sets (`hide_files`, `hide_prefixes`); the trailing `/`
   distinguishes prefixes; empty prefix forbidden; no leading `./`.
   Reflected in the **`hide_files` / `hide_prefixes` / `force_visible`**
   entry and **prefix match**.
3. **Sort mode config path** -- LOCKED to `<repo>/.claudechic/diff.yaml`
   (dedicated file; no co-tenancy with `config.yaml` in v1) under
   top-level key `sort_mode` (SPEC.md s9.2). Reflected in **sort mode**
   and **per-repo (sort mode persistence)** entries.
4. **Click-on-prefix-greyed-file resolution** -- LOCKED to **A2**
   (`force_visible` override). Ratified by user. Reflected in **hide
   controls** and the new **`force_visible`** entry.

No open glossary dependencies remain.

---

## 11. Banned-synonyms quick reference

For the lint-style sweep at Specification exit, search artifacts for these
strings; each occurrence MUST be rewritten:

```
alpha (as a sort-mode value)
flat-alphabetical
flat-alpha
grouped-by-directory
directory-grouped
sort order
diff command (use: slash command /diff OR target; "source command" is retracted at v6)
diff command field
diff panel (use: DiffScreen OR FileDiffPanel)
right panel (artifacts only; informal prose OK)
the sidebar (when unqualified -- always say DiffSidebar in artifacts)
review checkmark
reviewed-checkmark
review checkbox
review state
reviewed visibility
indeterminate
full/none/indeterminate
content_sha
hide flag
hide flags
in-memory only (use: session-scoped, repo-keyed)
non-persisted
per-session, per-repo
bulk hide (heading or code identifier)
show (as inverse of hide)
reveal
vanish
un-hide (PROSE only; allowed inside literal user-facing display strings)
greyed entry (heading -- use "hidden render variant" or licensed alias "greyed")
ghost entry
dimmed entry (heading)
ReviewStore
Mark as reviewed
repo_cwd (use "repo key")
<repo>/.claudechic/config.yaml for sort mode (use diff.yaml)
NV2 (the term "NV2 prefix semantics" was internal; use "prefix match" + the three-set HideState model)
hide list
hide map
A1 (use the locked A2 semantics)
blacklist / whitelist (for hide sets)
exclude set / include set
force-show set (use force_visible)
prefix hit / subtree match / directory match (use "prefix match")
IHideStore / ISortModeStore / IHideState (Hungarian-style prefix; use the Protocol suffix)
AbstractHideStore / HideStoreBase / HideStateBase (use the Protocol-suffixed type)
HideStateView / HideStateReader (use HideStateProtocol)
hidden_for / matches_path / is_visible (use is_hidden, negated)
longest_prefix (use longest_matching_prefix; the qualifier is the meaning)
parent_dir / parent_prefix / dirname_prefix / _to_parent_prefix (use to_prefix)
DirectoryHeader (use DiffDirectoryItem)
collapsed_prefixes (use folded_prefixes)
fold_state (use folded_prefixes -- the set's canonical name)
collapse_prefix / expand_prefix (use fold_prefix / unfold_prefix)
show_prefix / clear_prefix (use unhide_prefix)
is_collapsed / is_expanded (use is_folded / not is_folded)
prefix_hidden (use is_prefix_hidden)
DiffHeader (retracted at v6; do not use as a live term)
source command (retracted at v6; do not use as a live term)
DiffSource (retracted at v6)
sort badge (the WIDGET is retracted at v6; the `sort: <mode>` STRING content survives at the sub-title surface -- use "sort sub-title" for that surface)
sort label / sort indicator (use "sort sub-title" -- the canonical name for the v1 sub-title-chrome surface)
subtitle (one word; use "sub-title" with the hyphen to match Textual's `Screen.sub_title` attribute)
hidden count badge (retracted at v6)
hidden: N (the badge text -- now refers to nothing on screen)
files panel (use FilesSection)
edit list (use FilesSection)
trim / filter out / clean up / sync / reconcile (for the prune step; use "FilesSection prune")
refresh (when meaning the v6 prune; the agent-switch _async_refresh_files is a separate flow and may keep "refresh")
dirty set / modified set / changed set / diff set / stat set (use "dirty path set")
list_dirty / get_changed_paths / get_diff_paths (use get_dirty_paths)
diff base for prune / prune target / prune ref (use "prune basis"; always HEAD)
```

---

End of canonical terminology for diff_review_ux.
