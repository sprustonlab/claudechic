# Skeptic review -- Specification phase, diff_review_ux

> Historical / rationale document. Canonical naming lives in `specification/terminology.md`; this file uses some pre-lockdown draft terms (e.g. `un-hide` prose, `diff command field` quoting the user's bug-report wording, `content_sha` in retraction context). Its operational findings were absorbed into `specification/SPECIFICATION.md`.

**Reviewer:** Skeptic
**Inputs:** v4.2 design doc (`uidesigner_design_v4.md`), v4 STATUS locked decisions, source: `screens/diff.py`, `features/diff/widgets.py`, `features/diff/git.py`, `config.py`.

This review is structured as: (1) what to confirm in Spec, (2) findings ranked by severity, (3) required additions to the Specification exit criteria.

---

## 1. Confirmations -- v4 simplifications successfully retired old complexity

- No `content_sha` keying. No rename migration. No tri-state derivation. The "reviewed" axis is gone everywhere I can see; my P1 #4/#6/#7 from Leadership remain retired. Good.
- Hide is `display: false`, not removal. In-place DOM reorder for sort. `HunkWidget` instances and their comments survive both axes. P0 #2 honored on paper.
- App-scoped HideStore (not DiffScreen-scoped). The contradiction I flagged in NV1 is resolved. Good.
- Repo key = raw cwd, no symlink/git-toplevel resolution. Documented as "revisit if real-world breakage". Acceptable defer.
- `s f d r` lowercase, no case-sensitive pairs, no vi-left collision. Footer-help via `BINDINGS`. Good.

## 2. Findings, ranked

### S1 (P0) -- #18 reproduction is still missing

The locked decision says `DiffHeader` is the fix. The UIDesigner doc asserts "#18 is a missing-feature bug, not a wiring bug." But Leadership's binding requirement was **reproduce first, identify the actual widget, then fix**. I see no reproduction artifact in `specification/`. The whole design hangs on the UIDesigner's assumption being correct.

If the user's "diff command field appears empty" was actually about a `Bash(git diff)` ToolUseWidget in the chat rendering an empty command label, then `DiffHeader` does not address #18 at all -- it adds a new feature, leaves the actual bug live, and we close the issue under false pretenses.

**Required:** before Implementation, Spec must produce one of:
- a screenshot/transcript reproducing the user's complaint, with the affected widget identified, OR
- a one-line confirmation from the user that "the diff command field" means "DiffScreen has no widget showing the originating git command, and that is what's wrong" -- captured in the Spec checkpoint artifact.

Without this, S1 is a "shortcut disguised as simplicity": the simplest solution to a phantom field is a phantom fix.

### S2 (P0) -- Resolution rule for `is_hidden(path)` must live in exactly one place

STATUS locks: `HideState = (hide_files, hide_prefixes, force_visible)` with rule `path in hide_files OR (prefix match AND path not in force_visible)`.

This is the right escape from the "click un-hides everything under prefix" misfeature. But three sets and a two-clause rule is exactly the kind of state that gets re-implemented inconsistently across DiffSidebar (renders greyed entries), DiffView (sets `display:false`), DiffHeader (computes `hidden: N`), and the controller (handles `f`/`d`/`r`/click). If ANY of those re-implements the rule slightly differently, the UI desyncs from the data.

**Required spec rule:** a single `HideState.is_hidden(path: str) -> bool` method. Every consumer calls it. No consumer reads `hide_files` / `hide_prefixes` / `force_visible` directly. This is the verifiability lever -- one function, one truth table, one set of tests.

### S3 (P1) -- Prefix semantics need a normalization spec

`hide_prefixes` is described as a `set[str]` of "prefixes". Underspecified:
- Is `"src"` a valid prefix, or must it be `"src/"`? Without trailing-slash normalization, `"src"` matches `"src_old/foo.py"`, hiding the wrong files.
- File at repo root: `Path("README.md").parent == Path(".")`. Pressing `d` on a root-level file with naive prefix `""` hides every file in the diff. Almost certainly wrong.
- Cross-platform: paths from `git diff` are forward-slash regardless of OS; spec should say `hide_prefixes` stores forward-slash, trailing-slash strings, and matching is `path.startswith(prefix)`.

**Required:** Spec defines `_to_prefix(path) -> str | None`:
- `"src/foo.py"` -> `"src/"`
- `"src/sub/foo.py"` -> `"src/sub/"`
- `"README.md"` -> `None` (root-level files are not directory-hideable; `d` on a root-level file is a no-op with a footer hint, OR `d` on a root file targets `hide_files` instead -- pick one).

And `is_hidden` does `any(path.startswith(p) for p in hide_prefixes)`, never substring or path-component magic.

### S4 (P1) -- `hidden: N` must count visible-in-current-diff, not store size

If `hide_prefixes` contains `"tests/"` from earlier in the session and the current diff has zero files under `tests/`, `hidden: N` should read `0`, not `len(hide_files | hide_prefixes)`. Spec must say:

> N = number of `FileChange` entries in the current diff for which `HideState.is_hidden(change.path)` returns True.

Otherwise the badge lies, and the empty-state placeholder ("All N files hidden") prints incoherent counts.

### S5 (P1) -- Sort-mode persistence integration is unspecified

STATUS says: "Persisted per-repo in `<repo>/.claudechic/`". `ProjectConfig.load(project_dir)` already reads `<repo>/.claudechic/config.yaml`. Two paths:
- (a) Add `sort_mode: str = "directory"` to `ProjectConfig` dataclass. Pro: one file, existing infra. Con: `ProjectConfig` is currently scoped to gate/guardrail concerns; mixing diff UI state in is a small layering smell.
- (b) New file `<repo>/.claudechic/diff.yaml` with `{sort_mode: directory}`. Pro: separation. Con: a whole new file for one enum.

**Required spec choice + write semantics:**
- Pick (a) or (b) explicitly.
- Specify load timing: `DiffScreen.__init__` (sync) reads it, defaulting to `directory` on missing/corrupt.
- Specify write timing: `s` keypress writes synchronously (or fire-and-forget with errors logged via `log.warning`, never user-facing toast).
- Specify error mode: corrupt YAML -> default `directory`, log, no crash.

If the user already pushed back on (a), record (b) and the path. If undecided, raise it at the Spec user-checkpoint.

### S6 (P1) -- Single source of truth + update fan-out pattern

Six widgets/state-readers care about hide+sort: `DiffScreen` (controller), `DiffSidebar` (renders DiffFileItems), `DiffView` (toggles `display`), `DiffHeader` (badges), individual `DiffFileItem` (own visual state), `HideStore` (data).

If `f` on a focused file fires five imperative `widget.update(...)` calls, any missed call desyncs the UI. **Required pattern:** one `HideStateChanged` Message posted by the controller; sidebar / view / header each handle it independently and re-derive their state from `HideState.is_hidden(...)`. No sibling-to-sibling calls. (Same pattern for `SortModeChanged`.)

### S7 (P1) -- `_sanitize_id` collision is still latent and now reachable

`_sanitize_id("foo/bar.py")` and `_sanitize_id("foo-bar-py")` both return `foo-bar-py`. With sort reordering and dynamic per-file widget IDs (`#sidebar-{id}`, `#hunk-{id}-{n}`, `#panel-{id}`), Textual's `query_one` returns the first match -- silently wrong widget, silently wrong action.

**Required:** replace `_sanitize_id` with a stable index-based ID (`#sidebar-i{idx}`) or a path hash. Add a regression test that mounts two paths colliding under the current sanitizer and asserts they resolve to distinct widgets.

This was P0 in Leadership; it's not P0 here only because v4 didn't change it -- but the spec must commit to fixing it within scope or explicitly defer it with a justification.

### S8 (P2) -- `f`/`d` edge cases

The spec must define behavior for:

1. `d` on a focused file whose parent prefix is **already in** `hide_prefixes`. Idempotent? Or does it clear the focused file from `force_visible` (otherwise `d` appears to do nothing because a sibling kept the dir from being fully hidden)?
2. `f` on a focused file that is already in `force_visible`. Add to `hide_files` -- and what about `force_visible`? Leave it (override wins on `is_hidden`), or remove it (cleaner)? Both work, but pick one and test it.
3. `r` scope: clears HideStore for the **current cwd only**, not all repos. Trivial but spec it.
4. Click un-hide on a file that is in BOTH `hide_files` AND prefix-hidden: remove from `hide_files`, leave prefix; user sees it un-hide. If user expected "un-hide everything keeping this file visible", they're surprised when a sibling is still hidden. Document the per-file semantics in the tooltip ("click to un-hide this file" -- not "un-hide").

### S9 (P2) -- DiffHeader truncation hides info from keyboard / screen-reader users

Truncated source command relies on a mouse tooltip. Keyboard / screen-reader users see only `git diff origin/feature/long-...`. Acceptable for `git diff HEAD` but lossy for long refs. Mitigation: at <60 cols drop `$ ` prefix to recover 2 cols (already in design). Spec note: this is an accepted accessibility tradeoff; if a keyboard-only user needs the full ref, they widen the terminal.

### S10 (P2) -- `on_key` -> `BINDINGS` migration scope

Design says it's "implementer call", "ship first if it reduces risk". That's not a spec decision -- spec needs to call it: in-scope for v1, or deferred. If in-scope, footer help is complete; if deferred, footer advertises only `s f d r` and the j/k/o/q/etc invisible keys remain undiscoverable. Recommend: in-scope, ship together, single PR.

### S11 (P2) -- Hidden files with in-progress comments

User has unsaved comment on a file, then hides it (manually or by `d` on its parent). Comment is preserved (lives on `HunkWidget`, `display:false` doesn't destroy it) and is returned on screen dismiss. But the user can no longer see / edit it. Two acceptable behaviors:

- (a) Allow it; on screen dismiss, surface "N hidden files have unsaved comments" notice in the chat.
- (b) Disallow `f`/`d` on files-with-comments; show footer hint "file has comment; resolve first".

Pick one. (a) is consistent with "hide is presentation"; (b) is paternalistic but prevents lost-comment surprise. Recommend (a) with the dismiss-time notice.

### S12 (P3) -- `--resume` and hide state

Vision: "gone on claudechic exit". `claudechic --resume` is a fresh process, so hides are gone. Power users may expect `--resume` to restore session UI state including hides. Document explicitly in Spec so this is a known non-feature, not a future bug.

### S13 (P3) -- Hide store is monotonic over a session

A long-running claudechic accumulates hide entries forever (so reappearing files re-hide). Bounded by session lifetime; negligible RAM. Mention; the existing `r` keybinding already serves as the user's manual GC.

### S14 (P3) -- Untracked files: explicit confirmation

Spec must state: untracked files (`status="untracked"`) participate identically in sort grouping and hide. Tested.

## 3. Required additions to Spec exit criteria

Beyond the existing exit criteria from Leadership, add:

- E1. Reproduction artifact for #18 (S1).
- E2. Single `HideState.is_hidden(path) -> bool` method spec'd (S2).
- E3. Prefix normalization rule (`_to_prefix`) and root-file behavior (S3).
- E4. `hidden: N` defined as count over current diff, not store size (S4).
- E5. Sort persistence: chosen file, schema, load/write timing, error behavior (S5).
- E6. `HideStateChanged` / `SortModeChanged` Message pattern (S6).
- E7. `_sanitize_id` replacement OR documented in-scope deferral (S7).
- E8. `f`/`d`/`r`/click edge-case truth table (S8).
- E9. `on_key` -> `BINDINGS` migration scope (S10).
- E10. Hidden-files-with-comments policy (S11).
- E11. Required tests:
  - `is_hidden` truth table (eight rows over (in hide_files, prefix matches, in force_visible)).
  - prefix matching: `"src/"` does NOT match `"src_old/foo.py"`.
  - new file under hidden prefix is hidden by default.
  - `_sanitize_id` collision regression.
  - sort toggle preserves hunk comments.
  - HideStore is per-cwd (no cross-repo leak).
  - HideStore survives DiffScreen close-reopen within a single App lifetime.
  - DiffHeader truncation at 120 / 100 / 80 / 60 / 40 cols.

## 4. Net assessment

v4.2 is a substantial improvement over v3, and the locked decisions hold most of the line on Skeptic's earlier P0/P1 risks. The remaining concerns are concentrated in:

- (a) confirming #18 actually maps to "missing DiffHeader" rather than a different broken widget,
- (b) hardening the three-set HideState behind a single resolution function with explicit prefix normalization,
- (c) committing the cross-widget update pattern so renderers cannot drift from data,
- (d) the latent `_sanitize_id` bug that remains a free crash-on-collision pit.

None of these are reasons to halt; they are required additions to Spec before Implementation begins. Recommend Spec adopts the E1-E11 exit criteria above and routes each finding to the relevant downstream agent.

## 5. Routing recommendations (for Coordinator)

- S1 (#18 repro) -> Specification owner / user checkpoint.
- S2, S6 -> Composability (controller / single source of truth).
- S3, S4, S8 -> Specification (data-model spec).
- S5 -> Specification + user checkpoint (chooses (a) or (b)).
- S7 -> Implementer (treat as in-scope bug-fix, with regression test).
- S9, S12, S13, S14 -> Specification (document explicitly, no new work).
- S10 -> Specification decision; implementation by Implementer.
- S11 -> UserAlignment + UIDesigner (UX call).
- E11 (tests) -> TestEngineer when spawned.
