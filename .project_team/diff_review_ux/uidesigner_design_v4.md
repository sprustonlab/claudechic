# DiffScreen UX Design v4

> Historical / rationale document. Canonical naming lives in `specification/terminology.md`; this file evolves through v4 / v4.1 / v4.2 / v4.3 in place and uses earlier draft terms (e.g. `alpha`, `un-hide`, `A1`, `right panel`, `[+] Hidden (N)`) in pre-final sections. Operational contract is `specification/SPECIFICATION.md`.

**Author:** UIDesigner
**Scope:** C, E, G, H, I, J, K from revised brief (v4).
**Constraint:** ASCII-only output (no emoji, em-dash, box-drawing).
**Compositional invariants honored:** sort/hide/focus orthogonal; sort uses
in-place DOM reorder; focus keys on `(path, hunk_idx)`; sidebar must surface
hidden files; new visuals must not collide with `HunkWidget.has-comment`.

---

## C. Keybindings (Textual `BINDINGS`)

Existing DiffScreen consumers: `j k up down enter o q escape` (currently
handled in `on_key`; the new bindings go through `BINDINGS` so the footer
help renders them).

Recommended `BINDINGS` additions on `DiffScreen`:

| Key   | Action                | Footer label    | Notes                                                |
|-------|-----------------------|-----------------|------------------------------------------------------|
| `s`   | toggle sort mode      | "Sort"          | Cycles alphabetical <-> directory.                   |
| `H`   | hide current file     | "Hide file"     | Capital H, avoids lowercase-h vi-left collision.     |
| `D`   | hide current dir      | "Hide dir"      | Hides directory of currently focused file.           |
| `u`   | undo last hide        | "Undo hide"     | Pops last hide entry off a stack (file or dir).      |
| `U`   | un-hide all           | "Un-hide all"   | Clears entire in-memory hide set for current repo.   |

Rationale:
- `s` is the obvious mnemonic for sort and is otherwise unbound.
- `H` and `D` are uppercase to (a) keep lowercase `h` available for any
  future vi-left navigation, and (b) signal a destructive-feeling action
  with a deliberate shift-key gesture.
- `u`/`U` form a discoverable pair: lower-case for granular undo, upper for
  bulk reset. `U` is included because the only other un-hide affordance is
  the sidebar, which vanishes below 100 cols (see G).
- Existing `j k up down enter o q escape` handlers should be migrated from
  `on_key` to `BINDINGS` in the same change so the footer help is complete.
  Implementer call.

Conflicts checked: none of `s H D u U` collide with `j k up down enter o q
escape`. `H`/`D` capitalization sidesteps lowercase-h vi-left and lowercase-d
"delete-line" reflexes.

Open question for user:
- Confirm `s` for sort vs alternative `t` ("toggle"). I prefer `s`.
- Is `U` (un-hide all) worth a dedicated key, or should that live as a
  button in the sidebar Hidden subsection only?

---

## E. Source-command field for #18

**Placement:** new full-width header strip at the top of `DiffScreen`,
above the existing `Horizontal #diff-container`. Restructure compose tree
from `Horizontal` to `Vertical` -> [header, Horizontal(sidebar, view)].

**Content (single line):**

```
$ git diff HEAD                       sort: alpha    hidden: 0
```

- Left segment: dollar-prompt prefix plus the literal command string
  (`git diff HEAD`, `git diff <ref>`, etc.). The prefix `$ ` makes it
  obvious this is a shell-style command, not freeform text.
- Right segment: two compact status badges, right-aligned:
  - `sort: alpha` or `sort: directory`
  - `hidden: N` (omit when N == 0, or render dim).

**Visual treatment:**
- Background: `$surface` (matches `FileHeaderLabel` palette).
- Padding: `0 1`.
- Command text: `$text` color, `text-style: bold` for the command itself,
  `$text-muted` for the `$ ` prefix.
- Status badges: `$text-muted`, separated by 4 spaces.
- Height: 1 row.
- Truncation: if the command is unusually long (rare), truncate with
  trailing `...` and reveal full string via `tooltip`. Status badges remain
  pinned right.

ASCII layout sketch (no box-drawing):

```
+------------------------------------------------------------------+
| $ git diff HEAD                       sort: alpha    hidden: 0   |
+----------------+-------------------------------------------------+
|  sidebar       |  diff view                                      |
|                |                                                 |
+----------------+-------------------------------------------------+
```

**Why header strip, not subtitle/footer:**
- Subtitle is part of `Screen.sub_title` (Textual app chrome) and is too
  globally visible / not scoped to the diff content.
- Footer is reserved for `BINDINGS` help.
- A header strip is the conventional location for "what am I looking at"
  metadata (see VS Code source-control diff header, magit diff header).

**Spec phase note:** Leadership flagged that no widget today renders this
string. The header strip is a NEW widget (call it `DiffHeader`), not a fix
to an existing one. #18 is a missing-feature bug, not a wiring bug.

---

## G. Narrow-screen behavior (< 100 cols)

When the sidebar is hidden (`.hidden` class added in `on_resize`), the user
loses:
- The list of changed files.
- The Hidden subsection (see I) and any click-to-un-hide affordance.

**Plan:**
1. Header strip is **always** visible regardless of width. It carries:
   - source command (E)
   - sort mode badge
   - hidden count badge
   The `hidden: N` badge is the user's signal that hidden files exist when
   the sidebar is gone.
2. All hide / sort / un-hide actions are reachable via keybindings (C),
   which never depend on the sidebar.
3. `U` (un-hide all) exists as the narrow-screen escape hatch when the
   user can't see the Hidden subsection.

**Deliberately not adding:** a narrow-screen modal listing hidden files.
Adds modal complexity for an edge case; `U` plus widening the terminal
covers it. Defer until a user reports it as friction.

---

## H. Focus policy on hide

**Rule (file hide via `H`):**
1. Compute the next visible hunk **after** the just-hidden file in current
   sort order. Move focus there.
2. If no next visible hunk exists (the hidden file was last), fall back
   to the previous visible hunk.
3. If nothing is visible (all files hidden), display the empty-state in
   `DiffView`:

   ```
   All N files hidden.
   Press u to un-hide last, U to un-hide all,
   or use the sidebar Hidden section.
   ```

   Focus the `DiffView` container itself so keybindings still fire.

**Rule (directory hide via `D`):**
- Same algorithm, but "after the just-hidden directory" means after the
  last sort-position descendant of that directory.

**Rule (un-hide via `u` / `U`):**
- After un-hide, focus stays where it currently is (no jump). User
  triggered this from a stable focus; respect it.
- Exception: if current focus was the empty-state placeholder, focus
  the first visible hunk after un-hide.

**Why forward-bias:** matches `j` (next) being the dominant scan
direction. Falling back to previous avoids the jarring "stuck at end"
state. Empty-state explicitly tells the user how to recover.

**Composability hook:** focus key is `(path, hunk_idx)` (per Leadership
invariant). Hide actions invalidate the current focus key only when the
hidden set covers it; otherwise the same key resolves to the same
`HunkWidget` (which still exists in the DOM, just `display: false`).

---

## I. Sidebar UX for hidden files (most important)

**Recommendation:** bottom-of-sidebar collapsed group, conditionally
present.

### Layout

```
Changed Files
  M  app.py
  A  features/diff/store.py     <- focused
  M  widgets/layout/footer.py
  M  widgets/layout/sidebar.py

[+] Hidden (3)                  <- collapsed by default
```

When expanded (Enter or click on the header):

```
Changed Files
  M  app.py
  A  features/diff/store.py
  M  widgets/layout/footer.py
  M  widgets/layout/sidebar.py

[-] Hidden (3)
  .  tests/test_diff_old.py
  .  tests/legacy/snapshot.py
  .  CHANGELOG.md
```

### Behavior

- **Absent when zero hidden.** No "Hidden (0)" row at all. Keeps the
  sidebar identical to today's UX when the user hasn't hidden anything.
- **Single header row when N > 0**, default collapsed. Header text is
  `[+] Hidden (N)` (collapsed) or `[-] Hidden (N)` (expanded). The
  bracketed `+`/`-` is the disclosure indicator.
- **Click or Enter on header** toggles expansion.
- **Hidden entries** use:
  - status indicator replaced by `.` (a single dot) in `$text-muted`,
    distinct from `M`/`A`/`D`/`R`/`U`.
  - file path in `$text-muted`, no `text-style: dim` since dimmed-on-dim
    becomes unreadable on some terminals; just the muted color.
  - click on a hidden entry un-hides it (and removes from the Hidden
    subsection; if N drops to 0, subsection disappears).
- **Sticks to bottom** via a single spacer row above it (`Vertical` with
  flexible top sibling). If sidebar is short, the section sits directly
  below the visible files; that is fine.
- The Hidden subsection respects `.hidden` (sidebar narrow-screen rule);
  it disappears with the sidebar. Keybinding `U` is the escape hatch.

### Why this shape

- **Zero-impact when not in use.** The user who never hides files sees
  zero new chrome.
- **Discoverable.** The `Hidden (N)` row appears automatically the first
  time a user hides something, with the count making the action's effect
  visible.
- **Cheap to expand.** One click reveals the list; no modal, no separate
  screen.
- **Single-action recovery.** Click any hidden entry to un-hide. No
  confirmation dialog; the action is reversible by re-hiding.
- **Rejected: ghost-in-place** (hidden items remain in original
  alphabetical/directory position, dimmed). Reason: clutters the working
  list with un-actionable rows; user has to mentally filter on every
  scan; conflicts with the "hard-hide from right panel" decision (the
  sidebar would diverge from the panel).
- **Rejected: separate "Hidden" screen / modal.** Heavyweight for a list
  that is usually 0-5 items long.

### Open question for user

- Should expansion state (Hidden subsection collapsed vs expanded)
  persist across `/diff` re-runs within the session, or always start
  collapsed? My default: **always start collapsed**. Aligns with hide
  state being session-scoped, not session-persisted UI chrome.

---

## J. Directory-level hide trigger

**Recommendation:** keybinding `D` is the canonical trigger and works
identically in both sort modes. In directory sort mode, additionally
allow click-on-directory-header in sidebar.

### Directory sort mode (sidebar shows directory headers)

```
Changed Files
v claudechic/                  <- click directory name to hide all
    M  app.py
    A  features/diff/store.py
v claudechic/widgets/layout/
    M  footer.py
    M  sidebar.py
```

- Click on a directory row hides every descendant file. The directory
  header itself disappears (since all its files are now hidden), and the
  files appear under `Hidden (N)`.
- Keybinding `D` is equivalent: hides the directory containing the
  currently focused file.

### Alphabetical mode (no directory headers in sidebar)

- No clickable directory affordance exists in the sidebar (by design;
  alphabetical mode is the flat view).
- `D` is the only trigger. The user must focus a file in the directory
  they want to hide, then press `D`.
- The header-strip `hidden: N` badge confirms the action.

### Why keybinding-primary

- One mechanism, one mental model, regardless of sort mode.
- No need to invent context-menu / right-click affordances (claudechic
  doesn't have those today).
- Click-on-directory in directory mode is a free bonus for mouse users
  because the row is already there for sort-grouping.

### Open question for user

- Should `D` ask for confirmation when the directory contains many
  files (say, > 20)? My default: **no confirmation**, undo via `u`
  is one keystroke. Adding a modal here breaks flow.

---

## K. Visual collision check

Reviewing every new visual element against the existing
`HunkWidget` border-color states:

| Existing visual                                  | New visual                                   | Collision? |
|--------------------------------------------------|----------------------------------------------|------------|
| `HunkWidget` default `border-left: tall $panel`  | (none -- hidden hunks aren't rendered)       | No         |
| `HunkWidget.has-comment` `border-left: $warning` | (none on HunkWidget)                         | No         |
| `HunkWidget:focus` `border-left: $secondary`     | (none on HunkWidget)                         | No         |
| `DiffSidebar .section-header` (bold)             | `Hidden (N)` header reuses same class        | No         |
| `DiffFileItem` (no border)                       | hidden entry uses `.` glyph + `$text-muted`  | No         |
| `DiffFileItem.active` (sidebar highlight)        | hidden entry never has `.active`             | No         |
| `FileHeaderLabel` (bg `$surface`, bold)          | `DiffHeader` reuses bg `$surface`, bold cmd  | No (different widget) |

Specific guarantees:
- No new use of `$warning` for borders anywhere on `HunkWidget` or its
  descendants. `$warning` remains exclusive to "this hunk has a comment".
- The Hidden subsection header uses the existing `.section-header` class
  to look identical to the existing `Changed Files` header.
- The `DiffHeader` widget lives outside the `Horizontal #diff-container`
  and has its own DEFAULT_CSS scope; cannot bleed into hunk styling.
- The `.` (dot) prefix on hidden entries does not conflict with any
  existing status indicator: `M A D R U ?` are the existing set.

No visual collisions detected.

---

## Summary of new UI elements

1. `DiffHeader` widget at top of `DiffScreen`.
   - Shows source command, sort badge, hidden count badge.
   - Always visible (independent of sidebar `.hidden`).
2. `DiffSidebar` gains a conditional `Hidden (N)` collapsed subsection
   at the bottom, only when N > 0.
3. `DiffFileItem` gains a hidden-entry render variant (dot prefix,
   muted color, click un-hides).
4. `DiffScreen.BINDINGS` gains `s H D u U` plus migration of existing
   `j k up down enter o q escape` from `on_key` to `BINDINGS`.
5. Empty-state placeholder for "all files hidden".

## Open questions for the user (to surface at Specification checkpoint)

1. Confirm keybindings `s H D u U`. Any preference for swapping
   capitalization (e.g. `h`/`d` if vi-left is not actually used here)?
2. Default sort mode on first run: **alphabetical** (matches today)?
3. Hidden subsection: always start collapsed across `/diff` re-runs?
4. `U` (un-hide all): keybinding plus button in Hidden subsection, or
   keybinding only?
5. `D` confirmation prompt for large directories: skip (my default) or
   threshold-based?
6. Narrow-screen modal for un-hide: skip (my default) or add later?
7. Hide-state store location (Specification checkpoint item from
   Leadership): `DiffScreen` instance vs `App`. UI design works either
   way; I have a mild preference for `App`-scoped so the count badge
   survives DiffScreen close/reopen within a session, matching user
   intent ("gone on claudechic exit", not "gone on screen dismiss").

## Cross-agent dependencies

- **Implementer:** `BINDINGS` migration of existing keys is a separable
  change; ship it first if it reduces risk.
- **Skeptic:** in-place DOM reorder (P0) is fully respected -- hide is
  `display: false`, not removal; sort is reorder of mounted children.
- **Composability:** the `DiffScreen` controller owns sort + hide state
  (P1) and the new `DiffHeader` reads from that controller. Sidebar and
  view subscribe. No direct sidebar<->view coupling.
- **Terminology:** uses canonical terms `source command`, `sort mode`,
  `hide state`. No new terms introduced.

---

# v4.1 Revisions (post-user-feedback)

User decisions applied:
- App-scoped HideStore: CONFIRMED.
- NV2 directory hide: PREFIX semantics confirmed (session `set[str]` of
  hidden prefixes; new files under a hidden prefix inherit hidden).
- Default sort mode: **directory** (overrides v4 default of alphabetical).
- Sidebar `[+] Hidden (N)` group: APPROVED.
- Keybindings: case-sensitive `u`/`U` pair REJECTED; "undo last hide"
  dropped (sidebar Hidden group covers granular un-hide).
- DiffHeader: mocks required at multiple widths.

## Revised C. Keybindings

Constraint set:
- All lowercase, no case-sensitive pairs.
- Avoid lowercase `h` (vi-left collision flagged by user).
- No collisions with existing `j k up down enter o q escape`.
- Required actions only: toggle sort, hide file, hide directory of
  focused file, un-hide all.
- Undo dropped: sidebar Hidden group provides granular un-hide; un-hide-all
  is the bulk escape.

Final binding table:

| Key | Action                              | Footer label  | Mnemonic                  |
|-----|-------------------------------------|---------------|---------------------------|
| `s` | toggle sort mode (alpha <-> dir)    | "Sort"        | Sort                      |
| `f` | hide current file                   | "Hide file"   | File                      |
| `d` | hide directory of focused file      | "Hide dir"    | Directory                 |
| `r` | un-hide all (reset hide state)      | "Reset hides" | Reset                     |

Rationale for picks:
- `s` for Sort -- only sensible mnemonic, no conflict.
- `f` for File -- clearest one-letter mnemonic for "hide this file".
  "Exclude" (`x`) was considered but `f`/`d` form a parallel pair that
  reinforces the file vs directory distinction.
- `d` for Directory -- parallels `f`. Vim "delete-line" reflex was
  considered; DiffScreen is not modal-vim (only `j k` are vim-borrowed),
  so the reflex risk is small. If the user dislikes `d`, fallback is
  `p` for "Parent dir".
- `r` for Reset -- replaces the rejected `U`. "Reset" reads as bulk
  recovery and is unambiguous. Alternatives considered: `a` (All), `c`
  (Clear) -- both have weaker semantic fit and are slightly more
  collision-prone with future bindings.

Collision check vs existing `j k up down enter o q escape`: clean.
Vi-left `h` avoided.

What about granular un-hide?
- Wide screen (>= 100 cols): click any entry in the sidebar `Hidden (N)`
  group.
- Narrow screen (< 100 cols): widen the terminal, OR press `r` to reset
  all hides (bulk escape). Per v4 G we deliberately don't add a modal.

Migration of existing on_key keys to BINDINGS:
- `j` next hunk, `k` prev hunk, `up`/`down` aliases, `enter`/`o` start
  comment, `q` back, `escape` back. All move to `BINDINGS` so the footer
  help renders the full set alongside `s f d r`. Implementer call.

Open question for user (revised):
- Confirm `s f d r`. If `d` triggers vim-delete reflex, swap to `p` (Parent).

## Revised E. DiffHeader -- ASCII width mocks

Key rendering rules adopted (revised from v4):
- `hidden: N` badge is shown ONLY when N > 0. When zero hides exist,
  the badge is absent (zero-chrome principle from sidebar Hidden group).
- `sort: <mode>` badge is always shown.
- Layout: command on left, badges on right, single line, height 1.
- Command color: `$text` bold for the command, `$text-muted` for the
  `$ ` prefix. Badges: `$text-muted`.
- Truncation: when command + minimum 4-space gap + badges exceeds width,
  truncate the command with `...` on the right; pin badges flush right.
- Below ~60 cols (degenerate): drop the `$ ` prefix to recover 2 cols;
  still truncate command if needed.

### Mock 1 -- 120 cols, fresh /diff (no hides)

Column ruler (10s digits, then 1s digits):
```
         1         2         3         4         5         6         7         8         9         0         1         2
123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890
```

```
$ git diff HEAD                                                                                       sort: directory
```

- Left: `$ git diff HEAD` ends at col 15.
- Right: `sort: directory` ends at col 120 (right-pinned).
- No `hidden: N` badge (N == 0).

### Mock 2 -- 120 cols, 5 hidden

```
$ git diff HEAD                                                                          sort: directory    hidden: 5
```

- Right block: `sort: directory    hidden: 5` (4 spaces between badges).
- Right-pinned at col 120.

### Mock 3 -- 120 cols, target=origin/main, 5 hidden

```
$ git diff origin/main                                                                   sort: directory    hidden: 5
```

### Mock 4 -- 100 cols, 5 hidden

Column ruler:
```
         1         2         3         4         5         6         7         8         9         0
12345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901
```

```
$ git diff HEAD                                                          sort: directory    hidden: 5
```

### Mock 5 -- 80 cols, 12 hidden

Column ruler:
```
         1         2         3         4         5         6         7         8
12345678901234567890123456789012345678901234567890123456789012345678901234567890
```

```
$ git diff HEAD                          sort: directory    hidden: 12
```

### Mock 6 -- 80 cols, long target, truncated

Command `git diff origin/feature/long-branch-name-that-exceeds-width` would
push past 80 cols when paired with `sort: alpha    hidden: 12` (28 chars
right block + 4 space gap = 32 chars reserved for the right). That leaves
48 cols for `$ ` + command. Truncate command with `...`:

```
$ git diff origin/feature/long-branch-...    sort: alpha        hidden: 12
```

- `$ git diff origin/feature/long-branch-...` is 41 chars (fits in left 48).
- Right block right-pinned.
- Tooltip on the truncated command shows the full string for mouse users.

### Mock 7 -- 60 cols, 3 hidden (degenerate narrow)

Column ruler:
```
         1         2         3         4         5         6
123456789012345678901234567890123456789012345678901234567890
```

```
$ git diff HEAD               sort: directory    hidden: 3
```

`$ git diff HEAD` (15) + spaces + `sort: directory    hidden: 3` (29) =
fits at 60 cols with 16 spaces between. OK.

### Mock 8 -- 60 cols, long target, very tight

```
$ git diff origin/...    sort: alpha    hidden: 3
```

The right block here uses a single-space gap variant when truly tight:
`sort: alpha    hidden: 3` (24 chars). Truncate command aggressively.

### Degradation summary

| Width   | Behavior                                                              |
|---------|-----------------------------------------------------------------------|
| >= 100  | Full command + full right block, generous spacing.                    |
| 80-99   | Full command + full right block; spacing collapses to 4-space gap.    |
| 60-79   | Truncate command with `...` if needed; right block kept intact.       |
| < 60    | Truncate command aggressively; consider dropping `$ ` prefix; right   |
|         | block kept intact (it carries actionable state).                      |

Rationale for prioritizing the right block over the command:
- Sort mode and hidden count are **state** the user actively manipulates.
- The source command is **provenance** -- nice to have, less urgent on a
  narrow terminal where the user has presumably opened `/diff` already.

### Visual treatment summary

- Background: `$surface` (matches `FileHeaderLabel`).
- Padding: `0 1`.
- Height: 1.
- Command segment: `$text-muted` for `$ `, `$text` bold for the command.
- Badge segment: `$text-muted`, plain.
- Active class on a badge if user just toggled it (200 ms flash on
  `$primary`)? OPTIONAL polish; can be a follow-up.

## Revised summary table of new UI elements

1. `DiffHeader` widget at top of `DiffScreen` (mocks above).
2. `DiffSidebar` `[+] Hidden (N)` collapsed subsection (unchanged from v4).
3. `DiffFileItem` hidden-entry render (unchanged from v4).
4. `DiffScreen.BINDINGS` adds `s f d r` plus migration of `j k up down
   enter o q escape` from `on_key`.
5. Empty-state placeholder for "all files hidden" (unchanged from v4),
   updated text:

   ```
   All N files hidden.
   Click any entry in the sidebar Hidden group to un-hide,
   or press r to reset all hides.
   ```

## Open questions still outstanding

- Confirm `s f d r` (and `d`-vs-`p` for directory hide).
- DiffHeader badge flash on toggle: include in v1 or defer?
- Below 60 cols behavior: aggressive truncate (proposed) or stack to
  two rows? My recommendation: aggressive truncate, no stacking.

---

# v4.2 Revisions (post-user-feedback round 2)

User decisions applied:
1. `s f d r` keybindings -- accepted, no swap.
2. NV2 prefix semantics -- locked earlier.
3. Default sort: directory -- locked earlier.
4. Repo key: raw cwd as DiffScreen receives it; no symlink/toplevel
   resolution.
5. App-level HideStore -- locked.
6. Badge flash on toggle -- DROPPED.
7. < 60 cols -- aggressive truncate (accepted).
8. `r` un-hide-all also reachable via DiffHeader -- accepted (clickable
   `hidden: N` badge).
9. `d` directory hide -- NEVER prompts.
10. Sidebar UX for hidden files -- **REPLACED**: in-place greyed entries
    (option A) instead of the `[+] Hidden (N)` collapsed group
    (option C, now retracted).

The `[+] Hidden (N)` collapsed-group section from v4 / v4.1 is RETRACTED.
This v4.2 replaces it.

## Sidebar in-place hidden entries (option A)

### Layout

In directory sort mode (default), hidden files stay in their natural
directory groups:

```
Changed Files
v claudechic/
    M  app.py
    A  features/diff/store.py            <- focused, normal style
v claudechic/widgets/layout/
    M  footer.py
    M  sidebar.py
v claudechic/legacy/
    .  old_helper.py                     <- hidden, greyed + strike
    .  legacy_compat.py                  <- hidden, greyed + strike
v tests/
    M  test_diff.py
    .  test_legacy.py                    <- hidden, greyed + strike
```

In alphabetical mode, hidden files sit in their alphabetical slot:

```
Changed Files
  M  app.py
  A  features/diff/store.py              <- focused
  M  features/diff/widgets.py
  .  legacy_helper.py                    <- hidden, greyed + strike
  M  screens/diff.py
  .  tests/legacy/test_old.py            <- hidden, greyed + strike
  M  widgets/layout/footer.py
```

### Visual treatment for hidden entries

| Element                | Visible (today)            | Hidden (new)                          |
|------------------------|----------------------------|---------------------------------------|
| Status letter (M/A/D/R/U) | `$primary` (or `$error` for D) | `.` dot in `$text-muted`           |
| Path text              | default `$text`            | `$text-muted` + `text-style: strike`  |
| Hunk count `(N)`       | dim                        | `$text-muted`, no strike              |
| Edit icon              | `$text-muted` (hover `$primary`) | unchanged                       |
| `.active` class        | sidebar highlight          | NEVER applied to hidden entries       |

Why dot + strike (not just colour):
- `$text-muted` alone is too subtle on some terminal palettes; strike
  guarantees visibility of the hidden state.
- The dot replaces the M/A/D/R/U status letter to signal "this is not in
  the diff right now". Strike alone on the path could be misread as a
  Markdown-style cancellation; the leading dot makes the row class
  unambiguous at a glance.
- Strike is supported by Textual via Rich's `text-style: strike` and is
  ASCII-safe (no glyph required).

### Click semantics

| Click target                     | If file visible          | If file hidden                  |
|----------------------------------|--------------------------|---------------------------------|
| Body of `DiffFileItem`           | scroll to file (existing)| un-hide the file                |
| `EditIcon`                       | open editor (existing)   | open editor (no un-hide)        |

- Clicking the body of a hidden row un-hides it. The row's `.` dot
  reverts to the status letter; strike and muted styling are removed.
- Tooltip on hidden rows: `"click to un-hide"`.
- The `EditIcon` keeps `event.stop()` so its click never reaches the
  body handler; editing a hidden file does not un-hide it.

Open question on prefix interaction:
- If the file is greyed because it matches a hidden **prefix** (NV2
  semantics, e.g. `d` on the parent), what does click-to-un-hide do?
  - **Option A1 (recommended):** remove the prefix entirely -- all
    descendants un-hide together. Cleanest data model; matches `d` as a
    bulk action being undone in bulk.
  - **Option A2:** add a per-file "force-visible" override that wins over
    the prefix. Requires a third axis (hide_files, hide_prefixes,
    force_visible). More state, more bug surface.

  My pick: **A1**. Surface to user; if user picks A2, the data model
  needs a `force_visible: set[str]` and the controller resolves
  visibility as `is_visible = path not in hide_files and (path not in
  any prefix OR path in force_visible)`.

### Keyboard navigation onto hidden entries

`DiffFileItem` is `Static` today (P2 risk: not focusable). Scope decision
for v1: **leave it Static**. Un-hide via mouse click only on the sidebar.
Keyboard-only users use `r` (reset all) for bulk recovery.

Rationale:
- Making `DiffFileItem` focusable is a bigger refactor (focus
  navigation, key bindings on the item, visual focus indicator).
- The narrow-screen escape (`r`) already covers keyboard-only un-hide.
- Granular keyboard un-hide is a clean follow-up if user requests it.

Open question for user:
- Accept "click-only un-hide for individual files in v1" or insist on
  keyboard parity? Default: click-only.

### Reconciling with `HunkWidget.has-comment` ($warning border)

Confirmed: no collision.
- Hidden styling lives on `DiffFileItem` (sidebar), which has no border.
- `$warning` is exclusive to `HunkWidget` in DiffView.
- Strike text-style is unused elsewhere on `HunkWidget` and its
  children.
- The new `.` dot is not used anywhere else as a status indicator.

### Directory group headers (directory sort mode)

In directory sort, directory rows act purely as group labels.
- Group header style stays normal regardless of how many descendants are
  hidden. (A header that greys when all children are hidden was
  considered; rejected as too subtle a signal for a state that the
  `hidden: N` badge in DiffHeader already surfaces.)
- Directory headers are NOT click targets in v1 -- only individual file
  rows handle un-hide clicks. (Click-on-directory-header to bulk un-hide
  was floated in v4 as a mirror of the `d` action; rejected for v1
  because it conflicts with future "fold/unfold directory group"
  affordances we may want.)
- The `d` keybinding remains the only way to bulk-hide a directory.

## DiffHeader -- `hidden: N` is clickable

Per user decision #8:
- When `N > 0`, the `hidden: N` badge is clickable.
- Click triggers the same action as `r` (un-hide all).
- Hover affordance: badge shows `text-style: underline` on hover and
  `tooltip="click to un-hide all"`.
- When `N == 0`, the badge is absent (no click target).
- The `sort: <mode>` badge is not clickable in v1 (could be a follow-up;
  not requested).

Rendering rule unchanged: badges right-pinned, command left-pinned,
truncate command first when tight.

## Empty-state in DiffView

DiffView placeholder when all visible files are hidden, updated text:

```
All N files hidden.
Click any greyed entry in the sidebar to un-hide it,
or press r to reset all hides.
```

Sidebar empty state ("no files in diff at all") is the existing
`#diff-empty` Static rendered by DiffScreen on mount; not affected.

## Focus policy under option A (confirmation)

When current focused file is hidden via `f`:
1. Focus moves to next visible hunk in current sort order.
2. The just-hidden file's sidebar entry remains in its natural slot,
   greyed and struck. It does NOT receive `.active` (active highlight
   moves to whichever file the new focused hunk belongs to).
3. If no next visible hunk: fall back to previous visible hunk.
4. If no visible hunks at all: empty-state placeholder, focus the
   `DiffView` container so keybindings still fire.

When `d` (directory hide via prefix):
1. Same algorithm; "after the just-hidden directory" means after the
   last sort-position descendant.
2. All descendants render greyed in the sidebar; directory group header
   stays normal.

When `r` (reset all hides):
1. All greyed entries return to normal styling.
2. Focus stays on the currently focused hunk (which is necessarily
   visible since `r` un-hides everything).
3. If focus was on the empty-state placeholder, focus the first hunk in
   sort order.

When click un-hides a single file (or, under A1, a prefix):
1. Sidebar entries return to normal styling.
2. Focus stays where it is. (User clicked; respect their stable
   keyboard focus.)

## v4.2 summary of new UI elements (consolidated)

1. `DiffHeader` widget at top of DiffScreen (mocks in v4.1).
   - Source command on left.
   - `sort: <mode>` badge (always shown).
   - `hidden: N` badge (only when N > 0; clickable -> un-hide all).
2. Sidebar `DiffFileItem` gains in-place hidden-entry render: dot +
   `$text-muted` + strike on path. Click body to un-hide.
3. `DiffScreen.BINDINGS` adds `s f d r` plus migration of existing
   `j k up down enter o q escape` from `on_key`.
4. DiffView empty-state placeholder for "all files hidden".
5. NO bottom-of-sidebar "Hidden" subsection. (Retracted from v4.)

## v4.2 open questions

1. ~~Click on a prefix-greyed file -- A1 or A2?~~ **RESOLVED in v4.3:
   user picked A2 verbatim ("I think A2, as I also wanted new files in
   a hidden folder to stay hidden"). This question is stale; refer to
   the v4.3 section below.**
2. **Keyboard parity for granular un-hide?** Default: click-only in v1.
3. **Directory group header click behavior in directory sort?**
   Default: non-interactive in v1 (preserves design space for future
   fold/unfold).
4. (Carried) DiffHeader badge flash on toggle: DROPPED per user.
5. (Carried) <60 cols: aggressive truncate, no stacking.

---

# v4.3 Revisions (post-user-feedback round 3)

User decision: Q1 resolved -- **A2 wins**. Per-file `force_visible`
overrides prefix hides. Three-set state model.

## Hide-state model (canonical)

Stored in `App`-scoped `HideStore`, keyed by raw cwd (per #4 earlier).
Per repo, three sets:

- `hide_files: set[str]` -- explicit per-file hides added by `f`.
- `hide_prefixes: set[str]` -- hidden directory prefixes added by `d`.
- `force_visible: set[str]` -- explicit per-file un-hides added by
  clicking a prefix-greyed entry.

### Visibility resolution (single source of truth)

```
def is_hidden(path: str) -> bool:
    if path in hide_files:
        return True
    matches_prefix = any(path.startswith(p) for p in hide_prefixes)
    if matches_prefix and path not in force_visible:
        return True
    return False
```

Equivalent prose: a file is hidden iff it is explicitly hidden in
`hide_files`, OR it lives under a hidden prefix and has not been
individually force-visibled.

`force_visible` only overrides prefix hides. It does NOT override
explicit `hide_files` entries -- a file in `hide_files` is hidden
regardless of `force_visible`.

## State transition rules (uniform, no per-state branching)

These rules cover every case (per-file-only, prefix-only, both, force-
visibled, etc.) without branching on prior state.

### `f` -- hide current file

1. Remove path from `force_visible` (if present).
2. Add path to `hide_files`.

Result: file is hidden regardless of prior state.

### `d` -- hide directory of focused file

1. Compute directory prefix from focused file's path (e.g.
   `claudechic/widgets/`).
2. Add prefix to `hide_prefixes`.
3. **Prune** `force_visible` entries that match this new prefix.

Result: every descendant of the new prefix is hidden, including any
previously force-visibled siblings.

Rationale for step 3: `d` is a deliberate bulk-hide action; if it left
prior force-visible overrides intact, those files would remain visible
under a freshly hidden parent, violating user intent. Pressing `d` is
the user saying "hide this whole directory now", which trumps prior
overrides under that prefix.

### Click un-hide (on a hidden DiffFileItem body)

1. Remove path from `hide_files` (if present).
2. If any prefix in `hide_prefixes` matches the path, add path to
   `force_visible`.

Result: file is visible regardless of which set(s) hid it.

This single rule covers all three click cases:
- Per-file-only hidden: step 1 removes; step 2 no-op. -> visible.
- Prefix-only hidden: step 1 no-op; step 2 adds force-visible.
  -> visible. Siblings under the prefix stay hidden.
- Both-state hidden: step 1 removes; step 2 adds force-visible.
  -> visible. Edge case explicitly confirmed.

### `r` -- reset all hides

1. Clear `hide_files`.
2. Clear `hide_prefixes`.
3. Clear `force_visible`.

Result: all files visible. (Step 3 is technically redundant given step 2
-- with no prefixes there is nothing to override -- but clearing it
keeps the store tidy.)

## Edge-case confirmations (per user prompt)

| Scenario                                                      | Behavior |
|---------------------------------------------------------------|----------|
| Click on a per-file-only hidden entry                         | Remove from `hide_files`. No prefix interaction. -> visible. |
| Click on a prefix-only hidden entry                           | Add to `force_visible`. Prefix unchanged. Siblings stay hidden. -> visible. |
| Click on a both-prefix-and-explicit-hidden entry              | Remove from `hide_files` AND add to `force_visible`. Prefix unchanged. Siblings stay hidden. -> visible. **Confirmed per user prompt.** |
| `f` on a force-visible file                                   | Remove from `force_visible`, add to `hide_files`. -> hidden. |
| `d` on a directory containing force-visible files             | Prune those entries from `force_visible`, add prefix. -> all hidden. |
| `d` on a directory whose prefix is a sub-path of an existing hidden prefix (e.g. existing `a/`, new `a/b/`) | Add the new prefix verbatim. No dedupe in v1; redundant but correct. |

## Tooltip rules per hidden state

Tooltip is computed from the file's hide state at hover time:

| State                                                | Tooltip                                                            |
|------------------------------------------------------|--------------------------------------------------------------------|
| In `hide_files`, no matching prefix                  | `click to un-hide`                                                 |
| Under matching prefix (in `hide_prefixes`), not in `hide_files` | `click to un-hide just this file (<prefix> stays hidden)` |
| In `hide_files` AND under matching prefix            | `click to un-hide just this file (<prefix> stays hidden)`          |

Wording rationale:
- Single-state per-file: short. The action is total.
- Any prefix-involved state: identical wording. Effect is the same to
  the user (this file becomes visible; siblings under the prefix stay
  hidden). The difference between "prefix-only" and "both-states" is
  internal bookkeeping, not user-visible.
- `<prefix>` is the **most-specific** (longest) matching prefix from
  `hide_prefixes`. If multiple prefixes match (e.g. `a/` and `a/b/` both
  in the set), the longest wins for tooltip wording. This matches the
  user's mental model of "the most specific group this file belongs to".

## Visual treatment unchanged from v4.2

- Greyed status `.` dot in `$text-muted`.
- Path text `$text-muted` + `text-style: strike`.
- Hunk count `$text-muted`, no strike.
- `.active` class never applied.

The visual is the same regardless of WHICH set hides the file. The user
sees "this file is hidden"; the click rule above resolves the un-hide
mechanics uniformly.

Open question: should prefix-hidden entries get a subtly different
visual from per-file-hidden entries (e.g. a `~` glyph instead of `.`)?
My recommendation: **no**. The hide visual is a UX signal of "not in
the diff right now"; the source of the hide is bookkeeping the user
doesn't need to read off the row. The tooltip carries the distinction
when relevant.

## Click semantics for click on `hidden: N` badge in DiffHeader

Unchanged from v4.2: same as `r`. Clears all three sets, restores all
files to visible.

## Empty-state placeholder text unchanged from v4.2

```
All N files hidden.
Click any greyed entry in the sidebar to un-hide it,
or press r to reset all hides.
```

## Specification handoff items (v4.3)

For Specification consolidation, the following are firm UI inputs:

1. **Three-set state model** (`hide_files`, `hide_prefixes`, `force_visible`)
   stored on `App`-scoped HideStore, keyed by raw cwd.
2. **Visibility resolution** (single function above).
3. **State transitions** for `f`, `d`, click un-hide, `r` (uniform rules).
4. **Tooltip strings** keyed off resolved state.
5. **Visual treatment** for hidden entries (dot + muted + strike).
6. **DiffHeader** layout, mocks, and clickable `hidden: N` badge.
7. **BINDINGS** `s f d r` plus migration of existing keys.
8. **Empty-state** text in DiffView.
9. **Focus policy** on hide and un-hide.

## v4.3 open questions (final round before Spec consolidation)

1. **Prefix dedupe on `d`** -- when adding a sub-prefix of an existing
   hidden prefix, do we dedupe? My recommendation: **no dedupe in v1**.
   The duplicate is harmless; dedupe is an optimization. Surface to
   user only if they care.
2. **Tooltip prefix-disambiguation** -- pick longest matching prefix.
   Confirm.
3. **Should `force_visible` GC happen on `r` reset?** It's cleared with
   the other sets. Confirmed implicitly above.
4. (Carried) Keyboard parity for granular un-hide -- click-only in v1.
5. (Carried) Directory group header click -- non-interactive in v1.
