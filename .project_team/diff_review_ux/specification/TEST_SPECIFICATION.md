# diff_review_ux -- Test Specification

Operational test specification for the diff_review_ux project. All terms used here are defined here. The 17-test list in `SPEC_APPENDIX.md` section I and the parallel deliverable at `specification/testing.md` (Composability lens) are REFERENCE only; this document is the canonical test plan TestEngineer will execute.

## 1. Goal

Verify the user-facing behaviors promised by `SPECIFICATION.md` through full user-arc workflow tests. One test = one complete user story, end to end. Test count: 7 workflow tests plus 1 manual check.

The shape of every workflow test:
1. Build a real git repo in a real temporary directory (`tmp_path`).
2. Mount the actual `ChatApp` via Textual's `app.run_test()` pilot.
3. Drive the app with simulated keypresses and clicks just as a user would.
4. Assert against user-observable state: visible widget content, sidebar entries, footer hints, focus, file-system effects.

A workflow may bundle keyboard AND mouse interactions in a single test when the user story does (W2 mixes `f`/`d`/`r` keypresses with sidebar clicks). Splitting one user arc into "keyboard half" and "mouse half" is forbidden (s6).

## 2. Glossary

- **workflow test** -- a single async pytest function that drives one complete user journey end-to-end.
- **fixture repo** -- a real on-disk git repository under pytest's `tmp_path`, isolated from any global / system git config (s5).
- **pilot** -- the Textual `app.run_test()` async context that lets a test press keys, click widgets, and inspect mounted state.
- **real git** -- subprocess calls to the actual `git` binary against an on-disk repository. No in-memory git, no mocked git output.
- **real disk** -- `pathlib` operations on `tmp_path`. No `pyfakefs`, no in-memory filesystem.
- **agent simulation** -- direct `Path.write_text` writes plus `app.files_section.add_file(...)` calls to stand in for what Claude's Edit/Write tool path would do at runtime. The production observer that wires Edit results into `FilesSection` is not exercised by the test driver; the dict-add is the operational equivalent.
- **opaque handle** -- a widget reference obtained by querying the DOM with a class + predicate, never by hardcoding an internal id string.
- **user-observable state** -- anything a user sitting at the terminal could see or interact with: rendered widget text, CSS classes that affect rendering, tooltip strings, focused widget, sidebar list, footer-help labels, file-system contents, the `app.files_section._files` dict (carve-out per s6).
- **internal state** -- private attributes of stores or widgets (e.g. `HideState.hide_files`, `HideStore._states`, `DiffView._hunk_list`). Forbidden as assertion targets (s6).

## 3. Axes (orthogonality contract)

| # | Axis        | Encoding location  | Values                                                                                            |
|---|-------------|--------------------|---------------------------------------------------------------------------------------------------|
| 1 | Topology    | Fixture            | `single-repo` / `nested-repo` / `many-untracked-repo` / `feature-branch-repo` / `two-repos`       |
| 2 | Operation   | Test body          | filesystem write, real-git command, `/diff` invocation, pilot keypress, pilot click               |
| 3 | Capability  | Test name + asserts| prune / sort / hide / comment-preservation / empty-state / repo-isolation / prefix-inheritance    |
| 4 | Locality    | Global rule        | in-process Textual pilot driving real disk + real git subprocesses (uniform; not a variable)      |

Discipline:
- A fixture encodes ONLY topology. Fixtures never branch on capability or operation in their setup.
- A test body composes ONE topology fixture and one or more operations to assert ONE primary capability.
- The locality axis is a constant: every test uses the same in-process pilot + real-disk + real-git triple. There is no "in-memory variant" of any test.

## 4. Workflow tests (W1-W7)

Each workflow is one test. Concrete details (file names, exact key sequences, exact assertion strings) belong to testing-implementation; this section names the user story, the user-observable transitions, the assertion targets, and which user-stated requirement(s) the workflow exercises. Coverage cross-checks are in s8 and s9.

### W1. Edit, commit, /diff -- file is gone from the sidebar; externally-modified file never appears

**User story (verbatim from userprompt_testing.md):** "I edit a file, commit it, click diff, the file is gone from the sidebar."

**User story extension (UA externally-modified-not-added guard):** "Meanwhile, separately, a different file got modified outside Claude's edits. When I click diff, that externally-modified file does NOT appear in the sidebar -- the prune is remove-only."

**Topology:** `single-repo` -- three tracked files modified in working tree.

**Sequence:**
- Test simulates Claude editing `a.py` and `b.py` (`Path.write_text` + `files_section.add_file(...)` for each).
- Test ALSO modifies `c.py` directly on disk -- bypassing `add_file` entirely; `c.py` is NEVER added to FilesSection.
- `/diff` runs once -- DiffScreen mounts. Dismiss it.
- Test runs `git add a.py && git commit -m "..."` via real subprocess.
- `/diff` runs a second time.

**Asserts on:**
- Before any `/diff`: `app.files_section._files` contains `a.py` and `b.py`; does NOT contain `c.py`.
- After the second `/diff`: `app.files_section._files` contains `b.py` but NOT `a.py` (pruned because clean vs HEAD post-commit). Still does NOT contain `c.py` (prune is remove-only -- never adds an externally-modified file even though `c.py` IS in `git status`).
- DiffScreen mounts successfully both times. After the second `/diff`, DiffScreen's mounted panels include `b.py` and `c.py` (both still dirty in the working tree) but NOT `a.py`.

**Covers:** #11/#18 prune (FilesSection cleared after commit -- user verbatim); externally-modified-not-added (v6 success criterion, UA sub-flag).

### W2. Hide and unhide via keyboard and click

**User story:** "I focus a file and press `f` to hide it, I press `d` on another to hide its directory, then I click a greyed sidebar entry to unhide just that file. The directory's other files stay hidden. I press `r` to reset."

**Topology:** `nested-repo` -- `src/a.py`, `src/b.py`, `tests/x.py`, `README.md` all modified.

**Sequence (mixed keyboard + mouse, deliberately bundled):**
- `/diff` opens. Pilot navigates to a hunk in `src/a.py`. Pilot presses `f`.
- Pilot navigates to a hunk in `src/b.py`. Pilot presses `d`.
- Pilot clicks the greyed sidebar entry for `src/b.py` -- only that file un-greys; the prefix's other siblings stay hidden (A2 force_visible -- the user-named requirement).
- A file ends up in BOTH `hide_files` (via the earlier `f`) AND under a hidden prefix; testing-implementation arranges that condition via the natural arc and clicks its greyed entry -- it un-greys (C1 fix -- s5.5.1 row 6, independent-clauses unhide).
- Pilot navigates to `README.md` (root file). Pilot presses `d` -> footer hint surfaces; `README.md` remains visible.
- Pilot presses `r`.

**Asserts on:**
- After `f` on `src/a.py`: its `DiffFileItem` has `.hidden-entry`; its `FileDiffPanel.display == False`; focus advanced.
- After `d` on `src/b.py`: both `src/*` `DiffFileItem`s carry `.hidden-entry`; both panels' `display == False`. `tests/x.py` and `README.md` are unaffected.
- After click on `src/b.py`: `src/b.py` un-greys; `src/a.py` STAYS greyed (siblings under `src/` stay hidden -- A2 force_visible).
- Tooltip wording matches s7 verbatim: prefix-only case shows `click to un-hide just this file (src/ stays hidden)`; `hide_files`-only case shows `click to un-hide`.
- After C1 click: the doubly-hidden file un-greys.
- After `d` on `README.md`: footer notification with `no parent directory to hide` is present briefly; `README.md` remains visible; HideStore's user-observable proxies elsewhere are unchanged.
- After `r`: zero `.hidden-entry` classes anywhere; zero `FileDiffPanel.display == False`; focus on a hunk.
- Between hide actions, `j`/`k` navigation never visits a hidden file.

**Covers:** A2 force_visible -- per-file un-hide of prefix-greyed file with siblings staying hidden (UA req 3, user verbatim); C1 fix (s5.5.1 row 6); root-file `d` no-op + footer hint (s5.1); keyboard+mouse-bundling guard.

### W3. Comment a hunk, toggle sort, dismiss, re-open -- comment intact, sort persisted

**User story:** "I type a comment on a hunk, toggle sort, my comment is still attached. I dismiss the screen and re-open `/diff`; sort is still in the toggled mode."

**Topology:** `nested-repo` (files in two directories so alphabetical and directory orders differ).

**Sequence:**
- `/diff` opens (default sort = `directory`).
- Pilot navigates to a specific hunk; record `(path, hunk_idx)` and the Python `id()` of that `HunkWidget`.
- Pilot presses `enter`, types a known string, presses `enter` to submit.
- Pilot presses `s` to toggle sort to `alphabetical`.
- Pilot presses `s` again to return to `directory`.
- Pilot dismisses (`q` or `escape`).
- Pilot re-opens `/diff`.

**Asserts on:**
- After each `s` toggle, the `HunkWidget` retrieved at `(path, hunk_idx)` is the SAME Python object as before the toggle (`id()` match) -- in-place reorder preserved instances (s10 P0).
- That widget's `.comment` attribute equals the typed string after each toggle.
- `<repo>/.claudechic/diff.yaml` exists on disk with `sort_mode: directory` after the second toggle.
- After dismiss + re-open, the freshly-mounted DiffScreen reads `directory` from disk; the visible top-level order of file rows matches directory grouping.

**Covers:** Hunk-comment preservation across sort change (UA req 5, v6 success criterion verbatim); s10 in-place reorder (Skeptic P0); s9.2 sort persistence round-trip.

### W4. Hide everything, see the empty state, press r, the diff returns

**User story:** "I hide all my files; the diff goes empty with a hint about how to recover; I press `r` and the diff comes back."

**Topology:** `single-repo` with two tracked files modified.

**Sequence:**
- `/diff` opens.
- Pilot presses `f` once per file (with `j` between to advance focus).
- Pilot presses `r`.

**Asserts on:**
- After all hides: every `FileDiffPanel.display == False`; a `Static` with id `diff-view-empty-state` is mounted; its plain-text content equals exactly:
  ```
  All 2 files hidden.
  Click any greyed entry in the sidebar to un-hide it,
  or press r to reset all hides.
  ```
- After `r`: empty-state Static is removed; both panels' `display` is True; current focus is on a hunk in the first visible file.

**Covers:** s6.4 empty-state placeholder text verbatim; reset semantics from empty-state.

### W5. Hides in repo A do not appear in repo B during the same session

**User story:** "I'm in repo A, I hide a file. I switch to repo B; nothing is hidden there. I switch back to repo A; my hide is still active."

**Topology:** `two-repos` -- two independent on-disk repos in distinct `tmp_path` subdirs, each with its own tracked file set.

**Sequence:**
- App launched with active agent in `repo_a`. `/diff` opens. Pilot presses `f` to hide a file. Dismiss.
- The active cwd is switched to `repo_b` (mechanism determined at testing-implementation; the test asserts the resulting behavior, not the switch's internals).
- `/diff` opens for `repo_b`.
- The cwd is switched back to `repo_a`. `/diff` opens.

**Asserts on:**
- After `/diff` in `repo_b`: zero `.hidden-entry` classes; zero `FileDiffPanel.display == False`.
- After re-opening `/diff` in `repo_a`: the previously hidden file is still greyed (per-cwd persistence within the same App lifetime).

**Covers:** HideStore per-cwd isolation (s5.4); same-cwd persistence across DiffScreen dismiss/reopen.

### W6. Feature branch ahead of origin/main, many untracked, /diff target != HEAD

**User story:** "I'm on a feature branch with a file I edited locally that happens to match `origin/main` exactly, plus 6+ untracked files (one of which is in my edits-tracking sidebar). I open `/diff origin/main`. The diff shows all my untracked files. The sidebar still shows my edited file (because it's dirty in my working tree, regardless of what `/diff` is comparing against) and still shows my untracked file (because the untracked count is no longer silently capped)."

**Topology:** `feature-branch-repo` -- `git init`, initial commit, `git update-ref refs/remotes/origin/main HEAD` (publishes the fake-remote ref locally; no second repo, no network), then a feature branch with one or more local commits, plus a working-tree file F that is dirty vs HEAD AND identical in content to its `origin/main` version (commit a change to F on the feature branch, then revert F's content in the working tree to its `origin/main` value without staging the revert), plus 6+ untracked files.

**Sequence:**
- Test simulates Claude `Write`-ing one of the six untracked files (`add_file` for it) AND tracking F in `FilesSection` (`add_file(F)`).
- `/diff origin/main` opens.

**Asserts on:**
- All 6+ untracked files render as `DiffFileItem` rows in `DiffSidebar`; the "No uncommitted changes" empty-state is NOT shown (s8a `MAX_UNTRACKED_FILES` cap removal in `get_changes`).
- The Claude-Written untracked file IS in `app.files_section._files` -- prune kept it (R2: `get_dirty_paths` reports all untracked, no truncation).
- F IS in `app.files_section._files` -- prune kept it because it's dirty vs HEAD, even though `git diff origin/main` shows no hunks for F (R1: prune basis is HEAD, NOT the `target` argument).
- DiffScreen does NOT render F as a `FileDiffPanel` (since it has no hunks vs `origin/main`). The disagreement between FilesSection (keeps F) and DiffScreen (no F panel) is the user-observable demonstration of the HEAD-vs-target separation.

**Covers:** R1 -- prune basis is HEAD, not target (UA req 1, v6 failure list); R2 -- untracked-truncation does not corrupt prune basis (UA req 2, v6 failure list); s8a in-scope side-fix.

### W7. Hide a directory, return later, new files in that directory inherit hidden

**User story:** "I hide the `src/` directory because I want to focus elsewhere. I dismiss `/diff`. Later I add a new file under `src/`. When I re-open `/diff`, the new file in `src/` is also hidden -- my hide settings carried forward within this session."

**Topology:** `nested-repo` (with `src/a.py` plus other files).

**Sequence:**
- `/diff` opens. Pilot navigates to a hunk in `src/a.py`. Pilot presses `d` -> `src/` is hidden.
- Pilot dismisses.
- Test writes `src/b.py` to disk (new untracked file; same App lifetime).
- `/diff` re-opens.

**Asserts on:**
- After re-open: `DiffFileItem` for `src/b.py` carries `.hidden-entry` (inherited from the same `HideStore` in App scope).
- `FileDiffPanel.display` is False for `src/b.py`.
- Tooltip on `src/b.py`'s greyed entry includes the prefix `src/` per s7 (`click to un-hide just this file (src/ stays hidden)`).
- `src/a.py` is also still greyed (HideState survived dismiss-and-reopen).

**Covers:** Prefix inheritance -- "new files in a hidden folder stay hidden" (UA req 4, user verbatim).

## 5. Fixture protocol

A real on-disk git repo in pytest's `tmp_path`. NO `mock.patch`, NO fake filesystems, NO in-memory git substitutes. Topology fixtures live in `tests/conftest.py` (or a workflow-test-local module); shape and exact names are TestEngineer's call at testing-implementation.

The fixture protocol must guarantee:

- **Hermetic git environment.** `GIT_CONFIG_GLOBAL` and `GIT_CONFIG_SYSTEM` set to `os.devnull` so no developer/CI git config leaks in. `os.devnull` resolves to `nul` on Windows and `/dev/null` on POSIX -- DO NOT hardcode `/dev/null` (it does not exist on Windows). (Locked at user-checkpoint as B1.)
- **Per-repo identity.** `user.email` and `user.name` configured per fixture, otherwise `git commit` fails on fresh machines.
- **Disable autocrlf.** `git config core.autocrlf false` per fixture so committed-then-checked text files don't flip dirty/clean across platforms.
- **`.gitignore` covers `.claudechic/`.** Without ignoring this directory, the W3 sort toggle's YAML write would itself become a dirty path and skew prune assertions. (Locked at user-checkpoint as B2.)
- **Initial commit.** Always at least one commit so HEAD exists.
- **Branch-ahead-of-`origin/main` (W6 only).** `git update-ref refs/remotes/origin/main <sha>` publishes a fake-remote ref locally. No actual remote round-trip; no second repo. The remote ref is real (`git diff origin/main` resolves), only the network traversal is omitted. The "modified vs HEAD, identical to origin/main" file F is set up by committing a change to F on the feature branch, then reverting F's content in the working tree to its `origin/main` value (without staging the revert). (Locked at user-checkpoint as B3.)

### 5.1 Cross-platform fixture rules

Linux, macOS, AND Windows are ALL required (s10). The fixture protocol must explicitly observe the project-wide cross-platform rules from `CLAUDE.md`:

- **Path separators.** All path manipulation in fixture and test code uses `pathlib.Path`. String concatenation with `/` to build filesystem paths is forbidden. Assertions on path strings call `.as_posix()` so cross-platform fixture paths normalize to forward slashes -- matching `git status` / `git diff` output, which is always forward-slash regardless of OS.
- **Hermetic git env (cross-platform).** `GIT_CONFIG_GLOBAL` and `GIT_CONFIG_SYSTEM` are set via `os.devnull` (do NOT hardcode `/dev/null`).
- **Atomic file writes.** Fixture code that writes to disk and needs atomic semantics uses `os.replace()` (NOT `Path.rename()`, which fails on Windows when the target exists). The production code already follows this discipline; fixtures inherit it.
- **Encoding.** Every `open()` / `read_text()` / `write_text()` in fixture code passes `encoding="utf-8"` explicitly. Platform-default encoding usage is forbidden.
- **Subprocess shell.** Fixture subprocess calls use `subprocess.run([list, of, args])` form, never `shell=True` with shell-specific syntax. Cross-platform quote handling differs.
- **NUL byte parsing.** `git status --porcelain -z` NUL-terminated output is portable across platforms. Tests do not need to second-guess the parser per platform.
- **ASCII-only test source.** No emoji, em-dash, box-drawing characters in test source (matches the project-wide rule).

### 5.2 Composition rules

A workflow test consumes exactly one topology fixture plus the `app_for_repo` fixture. `app_for_repo` is parameterized only on cwd; it does NOT take capability or operation parameters. Topology fixtures do NOT mount the App or push DiffScreen -- the test body owns the pilot.

## 6. Forbidden patterns

The following are spec violations:

- `unittest.mock.patch`, `unittest.mock.MagicMock`, `pyfakefs`, `monkeypatch.setattr` of `subprocess` / `asyncio.create_subprocess_exec` / `Path.read_text` / `open` / any git invocation, anywhere in workflow tests. Real disk + real git only.
- `pytest.skip`, `pytest.importorskip`, `pytest.mark.skip`, `pytest.mark.skipif`, `pytest.mark.xfail` on any workflow test. Known issues are bugs; fix them.
- Granular per-method unit tests targeting `is_hidden`, `to_prefix`, `_path_to_id`, `_path_to_hex`, `get_dirty_paths` parsing, `SortModeStore` round-trip in isolation, `_hidden_tooltip`, `_flatten_files`, `apply_hide`, or `build_tree`. These invariants are exercised through the workflows that depend on them.
- Splitting one user story into a "keyboard half" and "mouse half" (e.g. `test_hide_via_click` vs `test_hide_via_keyboard`). Workflows that mix inputs MUST stay as one test (W2 is the canonical example).
- Hardcoded internal widget ids baked into source. Tests compute the id via `_path_to_hex(path)` and inject it into the query string when needed; never bake `"sidebar-7372632f612e7079"` literally into a test. Even better: use class + predicate queries via `app.query(DiffFileItem)`.
- **Assertions on internal state.** Forbidden shapes:
  - `assert hide_store.get(cwd).hide_files == {"foo.py"}`
  - `assert "src/" in hide_state.hide_prefixes`
  - `getattr(store, "_states")` or any other reach into a leading-underscore attribute.
  - Iterating `HideState`'s sets directly (`for p in hide_state.hide_files: ...`).
  - Reading `DiffView._hunk_list`, `DiffSidebar._tree`, `DiffView._current_idx`, or any private attribute of widgets / stores.
  Replace with assertions on rendered widget state -- the `DiffFileItem` for `"foo.py"` has the `.hidden-entry` class, or its tooltip is the s7 string, or its `FileDiffPanel` has `display` False.

  **Single carve-out:** `app.files_section._files` IS a permitted assertion target. There is no public "list rows" API on `FilesSection`; the dict mirrors mounted `FileItem` widgets one-to-one and reading it is operationally equivalent to a DOM walk. Other store / widget internals have user-observable proxies (`.hidden-entry` class, `display` flag, tooltip strings) and MUST be asserted via those proxies.
- **Cross-platform sub-flags** (additional spec violations under the Linux+macOS+Windows requirement, s10):
  - Hardcoded `"/dev/null"` (use `os.devnull`).
  - Hardcoded `"\\"` or `"/"` path separators in test strings (use `pathlib.Path`; convert to forward-slash for assertions via `.as_posix()`).
  - `subprocess.run(..., shell=True)` with shell-specific syntax inside test code or fixtures.
  - `open()` / `read_text()` / `write_text()` without `encoding="utf-8"`.
  - Non-ASCII characters in test source (emoji, em-dash, box-drawing).
- Touching, weakening, or rewriting any of the existing 849 tests to make a new test pass. New behavior implies new assertions; existing tests stand.

## 7. Manual verification

Items that cannot reasonably be exercised in a workflow test stay manual. The single manual check at sign-off:

- **Session-lifetime hide loss / `--resume` non-restoration.** Hide some files, quit claudechic entirely, relaunch (with or without `--resume`); all files are visible again, hide state is gone. Process restart cannot be expressed inside `app.run_test()`; a one-shot manual verification is cheaper than a subprocess-per-test runner harness.

The check is recorded once at sign-off in STATUS.md and does not run in CI.

## 8. Crystal coverage

The six sort × hide-shape archetypes from `SPECIFICATION.md` are all exercised by the listed workflows. No separate parameterized "visual archetypes" test is required.

| # | Sort         | Hide archetype                                                | Covering workflow                              |
|---|--------------|---------------------------------------------------------------|------------------------------------------------|
| 1 | alphabetical | empty                                                         | W3 (during the alphabetical phase of the toggle, before any hides) |
| 2 | alphabetical | `hide_files`                                                  | W3 + W4 sort flip (testing-impl extension if needed) |
| 3 | alphabetical | `hide_prefixes`                                               | W2 + W3 sort flip (testing-impl may add a single sort-flip assertion at W2 finale) |
| 4 | directory    | empty                                                         | W1 (default sort = directory, no hides)         |
| 5 | directory    | `hide_files`                                                  | W2 (`f` on focused file under directory sort)   |
| 6 | directory    | `hide_prefixes` + `force_visible`                             | W2 (`d` then click sibling)                     |

Untracked-file uniformity: covered by W6 (six untracked render uniformly under directory sort).

## 9. Spec invariants -- workflow mapping

Cross-check that every P0/P1 invariant in `SPECIFICATION.md`, every Skeptic risk-register item, and every user-stated requirement (UA req 1-5 plus three guards) maps to at least one workflow.

| Invariant / requirement                                                          | Source                          | Workflow |
|----------------------------------------------------------------------------------|---------------------------------|----------|
| HunkWidget instance preserved across sort change; comment text preserved.         | s10 / Skeptic P0 / v6 success / UA req 5 | W3 |
| `_path_to_id` collision-free across distinct paths.                               | s13 / Skeptic P0                | Structural via implementation; W2 fixture may include `a/b.py` plus `a-b.py` if exercised |
| Prune basis is HEAD even when DiffScreen `target != HEAD`.                        | s8.6 / R1 / UA req 1            | W6       |
| Untruncated untracked: 5+ untracked do not silently drop a Claude-Written one.    | s8a / R2 / UA req 2             | W6       |
| Per-cwd HideStore isolation; same-cwd persistence across screen dismiss/reopen.   | s5.4                            | W5, W7   |
| FilesSection prune is remove-only (never adds externally-modified files).         | s8.5 / v6 success / UA guard    | W1       |
| Empty-state placeholder text matches s6.4 verbatim.                               | s6.4                            | W4       |
| A2 force_visible (per-file un-hide of prefix-greyed file; siblings stay hidden).  | s5.3 / UA req 3                 | W2       |
| C1 fix (independent-clauses unhide; doubly-hidden file un-greys on click).        | s5.5.1 row 6                    | W2       |
| Prefix inheritance (new files in hidden folder stay hidden).                      | user verbatim / UA req 4        | W7       |
| Root-file `d` is a no-op + footer hint.                                            | s5.1                            | W2       |
| Sort-mode persistence round-trip via `<repo>/.claudechic/diff.yaml`.              | s9.2                            | W3       |
| Tooltip wording on greyed entries matches s7.                                      | s7                              | W2, W7   |
| Keyboard + mouse mixed-input arc in a single test.                                 | userprompt_testing example      | W2       |

If a row's coverage is structurally absent in the listed workflow's natural arc, testing-implementation extends that workflow rather than spawning a new test. The cap is seven workflow tests; growth beyond requires a spec amendment.

## 10. Acceptance gates

A change set satisfying this test specification must pass:

- All seven workflow tests (W1-W7) pass under `pytest --timeout=30`.
- All existing 849 tests continue to pass under `pytest tests/ -n auto -q --timeout=30`. Baseline count must not drop.
- M1 manual check is performed once at sign-off; result recorded in STATUS.md.
- `ruff check` clean. `ruff format` clean. `pyright` no new errors against the post-CP3 baseline.
- No `mock`, no `skip`, no `xfail` anywhere in the workflow test files (grep verification).
- **Cross-platform matrix REQUIRED.** Linux, macOS, AND Windows ALL pass. Every workflow test (W1-W7) must pass on all three platforms in the CI matrix; a Windows failure is NOT best-effort and BLOCKS merge. Workflow tests are platform-agnostic by construction (s5.1 cross-platform fixture rules); a platform-specific failure is a bug against the implementation OR the fixture, not a candidate for `pytest.mark.skipif`. Skip-marks remain forbidden (s6).
- **CI matrix execution.** The CI matrix executes the workflow test suite on Linux, macOS, AND Windows runners. Every workflow test passes on every runner. The 849 baseline must also pass on every runner (verify pre-existing CI matrix already does this; if not, escalate at testing-implementation per s11).

## 11. What is NOT in this document

The following are deferred to testing-implementation and are NOT specified here:

- Specific test function names.
- Specific fixture helper function names.
- Exact assertion strings or expected widget-text beyond W4's empty-state placeholder (verbatim copy from `SPECIFICATION.md` s6.4).
- Pilot timing idioms (`await pilot.pause()` vs polling vs explicit wait-for).
- Test-file layout under `tests/` (one file per workflow vs grouped).
- Per-test pytest markers.
- The exact mechanism for switching active-agent cwd in W5; testing-implementation reads the agent-switch code path and uses it.
- **CI matrix verification.** TestEngineer at testing-implementation phase verifies pre-existing CI configuration (typically `.github/workflows/*.yml` or equivalent) executes the suite on the required Linux+macOS+Windows matrix. If matrix coverage is missing, TestEngineer flags it as in-scope for testing-implementation rather than punting to a separate project.

These choices land at testing-implementation when TestEngineer reads recent test commits in `git log` for repo style.
