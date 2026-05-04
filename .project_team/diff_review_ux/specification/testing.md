# Testing Specification -- diff_review_ux

Operational test specification for the diff_review_ux project. Supersedes `SPEC_APPENDIX.md` section I; section I is retained as historical and is not the binding test plan.

## 1. Terms

- **workflow test** -- a single `pytest` async test that drives one complete user journey end-to-end (filesystem edit, git operation, app interaction, assertion of user-observable outcome). One test per distinct user sentence.
- **fixture** -- a `pytest` fixture producing a real on-disk artifact (a `Path`) and/or a real `ChatApp` instance pointed at it. Fixtures encode topology only.
- **pilot** -- the `app.run_test()` async context manager from Textual; the test interface that drives keystrokes (`pilot.press("s")`), mouse events (`pilot.click(...)`), and time advances (`pilot.pause()`).
- **real git** -- subprocess calls to the `git` binary against an on-disk repository under `tmp_path`. No in-memory git, no mocked git output.
- **real disk** -- `pathlib.Path` operations on `tmp_path`. No `pyfakefs`, no in-memory filesystem.
- **agent simulation** -- direct `pathlib.Path.write_text` writes used to stand in for what Claude's `Edit`/`Write` tool path would do, plus a direct call to `ChatApp.files_section.add_file(...)` if the test needs the `(W1)` tool-use observer effect (the production observer is not exercised by the test driver).
- **internal state** -- attributes of `HideStore`, `HideState`, `SortModeStore`, `_hunk_list`, `_current_idx`, the three sets (`hide_files`, `hide_prefixes`, `force_visible`), or any other implementation detail not directly shown in the UI.
- **user-observable outcome** -- a property reachable from the rendered widget tree (greyed class on a sidebar item, `display` flag on a panel, presence of empty-state placeholder text, presence/absence of an entry in `FilesSection._files`, content of a comment label) or from the slot of a public callback (`get_comments()` return).

## 2. Axes

| # | Axis        | Encoding location | Values                                                                                        |
|---|-------------|-------------------|-----------------------------------------------------------------------------------------------|
| 1 | Topology    | Fixture           | single-repo / nested-repo / many-untracked-repo / two-repos                                   |
| 2 | Operation   | Test body         | filesystem write, git command, `/diff` invocation, pilot keypress, pilot click                |
| 3 | Capability  | Test name + asserts| prune / sort / hide / comment-preservation / empty-state / repo-isolation                    |
| 4 | Locality    | Global rule       | in-process Textual pilot driving real disk + real git subprocesses (uniform; not a variable) |

The widget layer never branches on capability inside fixtures, and fixtures never branch on operation inside their setup. A test body composes one fixture (topology) and one or more operations (axis 2) to assert a capability (axis 3).

## 3. Workflow inventory

Five workflow tests plus one manual check. Each workflow is one user sentence.

### 3.1 W1 -- "I edit and commit a file; on next /diff the sidebar drops it."

File: `tests/test_workflow_diff_prune.py::test_diff_prune_after_commit`.

Topology: single repo with `a.py`, `b.py`, `c.py` tracked.

Sequence:
1. App is launched against the repo. Agent is active.
2. Test simulates Claude editing `a.py` and `b.py` (write file + `files_section.add_file(...)` for each).
3. Run `/diff` via `pilot.press(*"/diff")` then `pilot.press("enter")`. DiffScreen mounts.
4. Dismiss DiffScreen (`pilot.press("escape")`).
5. Test runs `git add a.py && git commit -m "commit a"` via subprocess.
6. Run `/diff` again.

Asserts:
- After step 6, `app.files_section._files` contains `b.py` but not `a.py`.
- `c.py` was never in the section and is still absent (prune-only invariant).
- DiffScreen mounts successfully both times.

### 3.2 W2 -- "I open /diff, hide a file, hide a directory, click to unhide one, navigate with j/k."

File: `tests/test_workflow_diff_hide.py::test_diff_hide_unhide_navigate`.

Topology: nested-repo with `src/a.py`, `src/b.py`, `tests/x.py`, `README.md` tracked-modified.

Sequence:
1. App launched. `/diff` opens DiffScreen.
2. Pilot focuses the hunk for `src/a.py` (via initial mount or `j`/`k`).
3. Pilot presses `f` -- hide `src/a.py`.
4. Pilot presses `j` until focus reaches `src/b.py`. Press `d` -- hide directory `src/`.
5. Pilot presses `r` -- reset.
6. Pilot presses `f` on focused file. Then re-presses `f` is NOT needed -- click instead: `pilot.click("#sidebar-<hex>")` on the greyed entry.
7. Pilot presses `d` on `tests/x.py`. Pilot clicks `tests/x.py` greyed entry.

Asserts:
- After step 3: `DiffFileItem` for `src/a.py` has the `.hidden-entry` class; its `FileDiffPanel` has `display = False`; focus advanced (current focused HunkWidget belongs to a different file).
- After step 4: both `src/*` `DiffFileItem`s carry `.hidden-entry`; both `FileDiffPanel`s have `display = False`; non-`src` files are unaffected.
- After step 5: zero `.hidden-entry` classes anywhere; zero `FileDiffPanel.display = False`.
- After step 6: clicking the greyed entry removes `.hidden-entry` and re-shows the panel.
- After step 7: `tests/x.py` clicked-unhide leaves it visible; if the prefix `tests/` was hidden, it stays in `hide_prefixes` (verified indirectly by mounting one more file under `tests/` if the test needs to assert prefix persistence -- otherwise omitted).
- `j`/`k` between hide actions never visit a hidden file.

### 3.3 W3 -- "I write a comment on a hunk, toggle sort, the comment is still there."

File: `tests/test_workflow_diff_sort.py::test_sort_toggle_preserves_comments`.

Topology: nested-repo with files in two directories so that alphabetical and directory orders differ.

Sequence:
1. `/diff` opens DiffScreen (default sort = `directory`).
2. Pilot navigates to a specific hunk (record its `(path, hunk_idx)` and the `id()` of the HunkWidget Python object).
3. Pilot presses `enter`, types a comment, presses `enter` to submit.
4. Pilot presses `s` to toggle sort to `alphabetical`.
5. Pilot presses `s` to toggle back to `directory`.

Asserts:
- The HunkWidget at `(path, hunk_idx)` after step 4 is the SAME Python object as before step 4 (`id()` match) -- in-place reorder preserved instances.
- The same widget's `.comment` attribute equals the typed text after step 4.
- After step 5, same invariants hold.
- `<repo>/.claudechic/diff.yaml` exists and contains `sort_mode: directory` after step 5.

### 3.4 W4 -- "I hide everything, see the empty state, press r, the diff returns."

File: `tests/test_workflow_diff_empty_state.py::test_hide_all_then_reset`.

Topology: single-repo with two tracked files.

Sequence:
1. `/diff` opens.
2. Pilot presses `f` once per file (advancing focus between).
3. Observe empty-state placeholder.
4. Pilot presses `r`.

Asserts:
- After step 2: every `FileDiffPanel.display == False`; a `Static` with id `diff-view-empty-state` is mounted; its plain-text content equals exactly:
  ```
  All 2 files hidden.
  Click any greyed entry in the sidebar to un-hide it,
  or press r to reset all hides.
  ```
- After step 4: empty-state Static is removed; both panels' `display` is True; current focus is on a HunkWidget belonging to the first file in current sort order.

### 3.5 W5 -- "Hides in repo A do not appear in repo B during the same session."

File: `tests/test_workflow_diff_isolation.py::test_hide_state_repo_isolation`.

Topology: two-repos -- two independent on-disk repos `repo_a/` and `repo_b/`, each with its own tracked file set.

Sequence:
1. App launched with agent in `repo_a`.
2. `/diff` opens. Pilot presses `f` to hide a file in `repo_a`.
3. Dismiss DiffScreen.
4. Test programmatically switches the active agent's `cwd` to `repo_b` (or constructs a second agent and switches via `agent_mgr`). The exact mechanism for the cwd switch is determined at testing-implementation by reading the agent-switch code path; the workflow test asserts the resulting behavior.
5. `/diff` opens for `repo_b`.

Asserts:
- After step 5: zero `.hidden-entry` classes anywhere in the new DiffScreen; zero `FileDiffPanel.display == False`.
- After dismissing and re-opening `/diff` in `repo_a` (step 6 -- asserted in same test): the previously hidden file is still greyed (per-cwd persistence within the same App instance).

### 3.6 W6 -- "I have many untracked files; Claude writes one; I commit a different one; /diff shows everything correctly."

File: `tests/test_workflow_diff_many_untracked.py::test_many_untracked_with_prune`.

Topology: many-untracked-repo -- six untracked files in the working tree, one tracked file modified.

Sequence:
1. App launched.
2. Test simulates Claude `Write`-ing `claude_new.txt` (one of the six untracked) AND modifying the tracked file. Both go through `files_section.add_file(...)`.
3. Test runs `git add tracked.txt && git commit -m "commit tracked"` via subprocess (committing the tracked-modified file but leaving the six untracked alone).
4. `/diff` opens.

Asserts:
- All six untracked files render as `DiffFileItem`s in `DiffSidebar` (s8a -- pre-fix would have dropped them when count > 4).
- The committed `tracked.txt` is NOT in `app.files_section._files` (prune dropped it).
- `claude_new.txt` IS in `app.files_section._files` (R2 -- not silently dropped despite being one of many untracked).
- `DiffView` does NOT show the "No uncommitted changes" empty-state.

### 3.7 Manual M1 -- session lifetime

Verification step performed once at sign-off, not automated:

1. Run claudechic. Open `/diff`. Hide one file via `f`.
2. Quit claudechic completely.
3. Relaunch claudechic in the same repo. Open `/diff`.
4. Verify the previously hidden file is visible (not greyed).

Records: pass/fail line in the project STATUS.md.

## 4. Fixtures

Defined in `tests/conftest.py` (extending the existing one) or in a new `tests/test_workflow_diff_*.py`-shared helpers module. Each fixture returns plain `Path` and/or `ChatApp` handles; tests do not import the fixture's internals.

### 4.1 Topology fixtures

| Fixture                 | Returns                          | Setup                                                                                              |
|-------------------------|----------------------------------|----------------------------------------------------------------------------------------------------|
| `git_repo_simple`       | `Path` (the repo root)           | `git init`; create three files; `git add`; `git commit -m "init"`; modify all three (uncommitted). |
| `git_repo_nested`       | `Path`                            | `git init`; create `src/a.py`, `src/b.py`, `tests/x.py`, `README.md`; commit all; modify all.       |
| `git_repo_many_untracked` | `Path`                          | `git init`; create one tracked file `tracked.txt`; commit; modify `tracked.txt`; create six untracked files (`u1.txt` ... `u6.txt`).  |
| `two_git_repos`         | `tuple[Path, Path]` (repo_a, repo_b) | Two independent invocations of the `git_repo_simple` setup in distinct `tmp_path` subdirectories. |

### 4.2 App fixtures

| Fixture            | Returns           | Setup                                                                                            |
|--------------------|-------------------|--------------------------------------------------------------------------------------------------|
| `app_for_repo`     | `ChatApp` (un-mounted) | Constructs a `ChatApp` configured with cwd=<topology fixture's Path>. Wraps `app.run_test()` is the test's responsibility (so the test owns the async context). |

### 4.3 Fixture composition rules

- A workflow test consumes exactly one topology fixture plus the `app_for_repo` fixture.
- `app_for_repo` is parameterized only on cwd; it does NOT take capability or operation parameters.
- Topology fixtures do NOT mount the App or push DiffScreen. The test body does that via pilot.

## 5. Forbidden patterns

The following are spec violations:

- `mock.patch`, `unittest.mock.MagicMock`, `pyfakefs`, `monkeypatch.setattr` of `subprocess` / `asyncio.create_subprocess_exec` / `Path.read_text` / `git`-related calls anywhere in the workflow tests. Real disk + real git only.
- `pytest.skip`, `pytest.importorskip`, `pytest.mark.skip`, `pytest.mark.skipif`, `pytest.mark.xfail` on any workflow test. Known issues are bugs; fix them.
- Asserting on `HideStore._states`, `HideState.hide_files` / `.hide_prefixes` / `.force_visible`, `_hunk_list`, `_current_idx`, `_files` on the chat-screen `FilesSection` (which IS user-observable -- the only exception), or any other implementation-internal attribute. Exception list: `app.files_section._files` IS the user-observable source of truth for "what's in the chat sidebar" because it directly maps to mounted `FileItem` widgets, and there is no public API for "list the file rows"; assertions on this dict membership are permitted. All other internals are forbidden.
- Per-method unit tests targeting `is_hidden`, `to_prefix`, `_path_to_id`, `_path_to_hex`, `get_dirty_paths` parsing, `SortModeStore` round-trip, `_hidden_tooltip`, `_flatten_files`, `apply_hide`, `build_tree`, or other internal functions. If a behavior is not user-visible, it does not get a test.
- Hardcoding any DOM id derived from `_path_to_hex`. Tests compute the id via `_path_to_hex(path)` and inject it into the query string; never bake `"sidebar-7372632f612e7079"` literally into the test source.
- Touching, deleting, or weakening any of the existing 849 tests to make a new test pass. New behavior implies new assertions; existing tests stand.

## 6. Crystal coverage

The six archetypes from SPECIFICATION.md s5 (sort × hide-shape) are covered as follows. No separate parameterized "visual archetypes" test is required; coverage is achieved by the listed workflows.

| # | Sort         | Hide archetype                                          | Covering workflow                              |
|---|--------------|----------------------------------------------------------|------------------------------------------------|
| 1 | alphabetical | empty                                                    | W3 (sort toggled to alphabetical, no hides yet) |
| 2 | alphabetical | `hide_files = {a.py}`                                    | W3 with one hide before second toggle (folded)  |
| 3 | alphabetical | `hide_prefixes = {tests/}`                               | covered structurally via W2 + W3 sort flip; if not exercised in W3 timeline, add an explicit assert in W2 after a sort toggle |
| 4 | directory    | empty                                                    | W1 (default sort = directory, no hides)         |
| 5 | directory    | `hide_files = {x/y.py}`                                  | W2 step 3 (focus + `f` under directory sort)    |
| 6 | directory    | `hide_prefixes = {src/}, force_visible = {src/b.py}`     | W2 steps 4 and 6 (`d` then click-unhide one)    |

Untracked-file uniformity: covered by W6 (six untracked render uniformly in directory sort).

## 7. Skeptic and spec invariants -- workflow mapping

| Invariant                                                                              | Source            | Workflow |
|----------------------------------------------------------------------------------------|-------------------|----------|
| HunkWidget instance preserved across sort change; comment text preserved.               | s10 / Skeptic P0  | W3       |
| `_path_to_id` collision-free across distinct paths (e.g. `a/b.py` vs `a-b.py`).         | s13 / Skeptic P0  | W2 (use both names in fixture if exercised; otherwise structural via implementation) |
| Prune basis is HEAD even when DiffScreen target != HEAD.                                | s8.6 / R1         | W6 if extended OR a dedicated assertion in W1 (push DiffScreen with `target="origin/main"`) |
| Untruncated untracked: 5+ untracked do not silently drop the just-Written one.          | s8a / R2          | W6       |
| Per-cwd HideStore isolation; same-cwd persistence across screen dismiss/reopen.         | s5.4              | W5       |
| FilesSection prune is remove-only (never adds externally-modified files).               | s8.5              | W1 + W6  |
| Empty-state placeholder text matches s6.4 verbatim.                                     | s6.4              | W4       |

If a specific row's coverage is structurally absent in the listed workflow's natural arc, the testing-implementation phase is responsible for adding the minimal extension to that workflow rather than spawning a new test. The cap is six workflow files (W1-W6); growth beyond that requires a spec amendment.

## 8. Acceptance criteria

A change set satisfying this spec must pass:

- All six workflow tests (W1-W6) pass under `pytest tests/test_workflow_diff_*.py --timeout=30`.
- All existing 849 tests continue to pass under `pytest tests/ -n auto -q --timeout=30`.
- M1 manual check is performed once at sign-off; result recorded in STATUS.md.
- `ruff check` and `ruff format` clean. `pyright` no new errors.
- No `mock`, no `skip`, no `xfail` anywhere in the workflow test files (grep verification).

## 9. Out of scope

- Property-based / hypothesis-style tests of `is_hidden`, `to_prefix`, `_path_to_hex`. Not user-observable.
- Visual-snapshot tests of rendered terminal output. Not requested.
- Performance / load tests of `build_tree` or `apply_hide` at large file counts.
- Tests of the agent-switch refresh path (`_async_refresh_files`); orthogonal to /diff prune and unchanged in this project.
- Tests of FilesSection state survival across claudechic process restarts. Documented behavior (s15) is fresh state on launch.

---

## Appendix A. Rationale (non-binding)

A.1 Why six workflows, not seventeen.
The userprompt_testing.md vision rescopes around user sentences ("I do X, the system shows Y"). Each sentence is one workflow test. The six listed exhaust the distinct user sentences for this project; finer granularity (per-method, per-state-transition) is explicitly rejected by the user.

A.2 Why no unit tests on pure functions.
`is_hidden`, `to_prefix`, `_path_to_hex`, `apply_hide`, `build_tree`, `get_dirty_paths` parsing, and `SortModeStore` round-trip have no user-observable surface in isolation. They are exercised through workflow tests by virtue of being on the path between user keystroke and rendered widget. If a workflow test fails because one of these functions is wrong, the failure points to the function; the workflow test serves as the regression.

A.3 Why `app.files_section._files` is a permitted assertion target.
There is no public "list rows" API on FilesSection; the only way to assert "the row for `a.py` was pruned" without rendering and inspecting the DOM is to read the dict. `_files` directly mirrors mounted `FileItem` widgets one-to-one; reading it is equivalent to a DOM walk and is operationally user-observable. Other store internals (`HideStore._states`, `HideState.hide_files`, etc.) are NOT permitted because they have user-observable proxies (greyed class, panel display flag).

A.4 Why the agent-switch path is out of scope.
SPECIFICATION.md s8.5 is explicit: the agent-switch refresh (`_async_refresh_files`) is unchanged by this project. Its existing tests in the 849-test suite continue to cover it.

A.5 Why M1 is manual.
Process restart cannot be expressed inside `app.run_test()`. The session-lifetime invariant is "fresh process means fresh HideStore"; a one-shot manual verification at sign-off is cheaper than a subprocess-per-test runner harness.
