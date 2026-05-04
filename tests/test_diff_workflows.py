"""Workflow tests for diff_review_ux (W1-W7).

One workflow = one user story end-to-end, driven through the public
``ChatApp`` pilot against a real on-disk git repo. See
``.project_team/diff_review_ux/specification/TEST_SPECIFICATION.md`` s4
for the seven workflow definitions, s5 for the fixture protocol
(hermetic git env, autocrlf disabled, ``.gitignore`` covers
``.claudechic/``), s5.1 for cross-platform discipline, and s6 for the
forbidden patterns (no ``mock.patch`` of git/disk, no ``pytest.skip``,
no internal-state assertions beyond the single ``app.files_section._files``
carve-out).

SDK-substrate reuse
-------------------
Workflow tests inherit ``mock_sdk`` for SDK-connect scaffolding only.
The SDK transport is upstream of the diff feature; it is not under
test in this project. What IS under test runs real:

  - real on-disk repos under ``tmp_path`` (s5 fixture protocol)
  - real ``git`` subprocesses (no ``mock.patch`` on subprocess)
  - real Textual widget tree mounted via ``app.run_test()`` pilot
  - real ``HideStore`` / ``SortModeStore`` instances on the real
    ``ChatApp``
  - real ``_prune_files_section_to_git``, ``get_dirty_paths``,
    ``DiffScreen``, ``DiffSidebar``, ``DiffView``,
    ``FilesSection.prune_to``.

Reuse pattern matches all 849 baseline tests; this is not a new
carve-out. The diff workflow's correctness is a function of disk +
git + UI state, all three of which remain real here. Coordinator +
Skeptic ratified the carve-out at CP-A green-light.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
from pathlib import Path

import pytest
from claudechic.app import ChatApp
from claudechic.features.diff.widgets import (
    CommentInput,
    DiffFileItem,
    FileDiffPanel,
    HunkWidget,
    _path_to_id,
)
from claudechic.screens.diff import DiffScreen

from tests.conftest import submit_command, wait_for_workers


# ---------------------------------------------------------------------------
# Fixture protocol (s5)
# ---------------------------------------------------------------------------


def _git_env() -> dict[str, str]:
    """Hermetic git env for fixture repos (s5 B1).

    Sets ``GIT_CONFIG_GLOBAL`` and ``GIT_CONFIG_SYSTEM`` to ``os.devnull``
    (resolves to ``/dev/null`` on POSIX, ``nul`` on Windows -- s5.1
    forbids hardcoding ``"/dev/null"``). Ensures no developer / CI git
    config leaks into the fixture repo.
    """
    env = os.environ.copy()
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    env["GIT_CONFIG_SYSTEM"] = os.devnull
    # Pin the initial branch name so the fixture is deterministic across
    # git versions whose default differs (master vs main).
    env["GIT_INIT_DEFAULT_BRANCH"] = "main"
    return env


def _run_git(repo: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    """Run ``git <args>`` in ``repo`` with the hermetic env (s5).

    Uses the ``subprocess.run([list, ...])`` form (no ``shell=True``)
    per s5.1 cross-platform fixture rules.
    """
    return subprocess.run(
        ["git", *args],
        cwd=str(repo),
        env=_git_env(),
        check=True,
        capture_output=True,
    )


def make_repo(
    root: Path,
    *,
    name: str = "repo",
    initial: dict[str, str] | None = None,
) -> Path:
    """Build a real on-disk git repo per the s5 fixture protocol.

    - Hermetic git env (``GIT_CONFIG_GLOBAL`` / ``GIT_CONFIG_SYSTEM`` =
      ``os.devnull`` -- s5 B1).
    - Per-repo identity (``user.email`` / ``user.name``) so ``git
      commit`` works on a fresh CI runner.
    - ``core.autocrlf false`` -- text files don't flip dirty/clean
      across platforms (s5).
    - ``.gitignore`` covers ``.claudechic/`` (s5 B2) so a sort-mode YAML
      write never appears as a dirty path and skews prune assertions.
    - At least one initial commit -- HEAD always exists.

    Returns the repo's ``Path``. The working tree is clean immediately
    after this returns; the caller dirties / commits / writes new
    files to construct the topology under test.
    """
    repo = root / name
    repo.mkdir(parents=True, exist_ok=True)
    _run_git(repo, "init", "-b", "main")
    _run_git(repo, "config", "user.email", "test@example.com")
    _run_git(repo, "config", "user.name", "Test")
    _run_git(repo, "config", "core.autocrlf", "false")
    # B2 lock: ignore .claudechic/ so a sort-mode YAML write does not
    # become a dirty path on next /diff.
    (repo / ".gitignore").write_text(".claudechic/\n", encoding="utf-8")
    for rel, content in (initial or {}).items():
        target = repo / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    _run_git(repo, "add", "--all")
    _run_git(repo, "commit", "-m", "initial")
    return repo


# ---------------------------------------------------------------------------
# Topology fixtures (s5.2): each takes ``tmp_path`` and returns a Path.
# Topology fixtures encode ONLY topology -- never capability or operation.
# ---------------------------------------------------------------------------


@pytest.fixture
def single_repo(tmp_path: Path) -> Path:
    """Single-repo topology (W1, W4): three tracked files committed clean."""
    return make_repo(
        tmp_path,
        name="single",
        initial={
            "a.py": "print('a v1')\n",
            "b.py": "print('b v1')\n",
            "c.py": "print('c v1')\n",
        },
    )


@pytest.fixture
def nested_repo(tmp_path: Path) -> Path:
    """Nested-repo topology (W2, W3, W7): files in two subdirectories plus root."""
    return make_repo(
        tmp_path,
        name="nested",
        initial={
            "src/a.py": "print('src a v1')\n",
            "src/b.py": "print('src b v1')\n",
            "tests/x.py": "print('tests x v1')\n",
            "README.md": "# v1\n",
        },
    )


# ---------------------------------------------------------------------------
# App pilot helper (s5.2 ``app_for_repo``).
#
# Constructed inline rather than as a pytest fixture because the cwd
# redirect must happen AFTER ``ChatApp.run_test()`` enters its async
# context (the agent is created by ``on_chat_screen_ready`` and is
# only available once the chat screen mounts).
# ---------------------------------------------------------------------------


async def _redirect_active_agent(app: ChatApp, pilot, repo: Path) -> None:
    """Point the active agent's cwd at ``repo`` so ``/diff`` operates
    against the fixture.

    The default agent is created by ``on_chat_screen_ready`` with
    ``cwd=Path.cwd()`` (the test runner's cwd, i.e. the real claudechic
    checkout). The agent-creation callback schedules
    ``_async_refresh_files`` which scans that pre-redirect cwd for
    dirty paths and populates ``FilesSection`` with them. Without a
    clean-slate step here, those pre-redirect entries leak into the
    test's view of FilesSection -- visible only when the refresh
    worker completes before the test reads ``files_section._files``
    (timing-dependent under ``pytest -n auto``).

    Sequence:
      1. Wait until the agent exists.
      2. Wait until the agent-creation refresh worker settles (so
         ``FilesSection`` won't repopulate AFTER our clear).
      3. Rewire ``agent.cwd`` and ``app._cwd`` to the fixture repo.
      4. Clear ``FilesSection`` -- the test owns the contents from
         here on (every entry the test cares about is added via
         ``files_section.add_file``).

    Step 2's wait is what the failing parallel-run revealed: under
    ``pytest -n auto`` the refresh worker ran to completion and
    populated FilesSection with ~20 entries from the real claudechic
    repo before our test's own ``add_file(Path("a.py"))`` calls; the
    sequential run happened to outrace it.
    """
    for _ in range(20):
        if app._agent is not None:
            break
        await pilot.pause()
    assert app._agent is not None, "active agent not created"
    # Drain the agent-creation refresh task BEFORE redirect.
    # ``_async_refresh_files`` is scheduled via ``create_safe_task``
    # (a bare asyncio.Task), NOT ``app.run_worker`` -- so
    # ``wait_for_workers`` does NOT drain it. We have to wait for the
    # named task explicitly. The task name is ``"refresh-files"`` per
    # ``app.py`` (see ``create_safe_task(..., name='refresh-files')``).
    for _ in range(40):
        pending = [
            t
            for t in asyncio.all_tasks()
            if t.get_name() == "refresh-files" and not t.done()
        ]
        if not pending:
            break
        await pilot.pause()
    app._agent.cwd = repo
    app._cwd = repo
    # Wipe whatever the pre-redirect refresh populated. The test now
    # has a known-empty FilesSection; the only adds from here on are
    # the test's own ``files_section.add_file(...)`` calls plus the
    # ``_prune_files_section_to_git`` step on each ``/diff``.
    app.files_section.clear()
    await pilot.pause()


async def _open_diff(app: ChatApp, pilot) -> DiffScreen:
    """Drive ``/diff`` end-to-end and return the mounted DiffScreen.

    Runs the slash command through the chat input (the user-realistic
    path), waits for the worker that runs ``_toggle_diff_mode`` +
    ``_prune_files_section_to_git``, then waits for ``DiffScreen.on_mount``
    to fetch ``get_changes`` and mount the sidebar / view.
    """
    await submit_command(app, pilot, "/diff")
    await wait_for_workers(app)
    # DiffScreen.on_mount is async (awaits get_changes); pump the event
    # loop several times so the screen finishes mounting before we
    # query against it. Six pauses matches test_diff_preview's idiom
    # for the same async-mount race.
    for _ in range(6):
        await pilot.pause()
    screen = app.screen
    assert isinstance(screen, DiffScreen), (
        f"expected DiffScreen on top, got {type(screen).__name__}"
    )
    return screen


async def _dismiss_diff(app: ChatApp, pilot) -> None:
    """Dismiss the active DiffScreen via the user-observable ``escape`` keypress."""
    await pilot.press("escape")
    for _ in range(4):
        await pilot.pause()


# ---------------------------------------------------------------------------
# W1 -- Edit + commit + /diff: file is gone from FilesSection;
#       externally-modified file never appears (TEST_SPECIFICATION s4 W1).
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_w1_edit_commit_diff_prunes_committed_file_keeps_externally_modified_out(
    mock_sdk, single_repo: Path
) -> None:
    """User edits a.py + b.py via Claude, c.py is modified externally.

    Sequence:
      1. Test simulates Claude editing a.py and b.py (write to disk +
         ``files_section.add_file``).
      2. Test modifies c.py directly on disk -- bypass ``add_file``;
         c.py never enters FilesSection.
      3. ``/diff`` opens DiffScreen (first time). Both a.py and b.py
         dirty in working tree; c.py also dirty but not tracked by
         FilesSection. Dismiss.
      4. Test runs ``git add a.py && git commit`` (real subprocess).
      5. ``/diff`` opens DiffScreen (second time).

    Asserts:
      - Before any /diff: ``app.files_section._files`` keys = {a.py, b.py}.
      - After 2nd /diff: keys = {b.py}; a.py pruned (clean post-commit);
        c.py still NOT in FilesSection (s8.5 prune-only invariant -- never
        adds an externally-modified file).
      - DiffScreen mounts both times; 2nd DiffScreen's panels include
        b.py and c.py (both dirty in working tree) but NOT a.py.

    Covers: #11/#18 prune (FilesSection cleared after commit; user
    verbatim); externally-modified-not-added (v6 success criterion;
    UA sub-flag).
    """
    repo = single_repo

    app = ChatApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await _redirect_active_agent(app, pilot, repo)

        # Step 1: simulate Claude edits to a.py and b.py.
        (repo / "a.py").write_text("print('a v2 by claude')\n", encoding="utf-8")
        (repo / "b.py").write_text("print('b v2 by claude')\n", encoding="utf-8")
        files_section = app.files_section
        files_section.add_file(Path("a.py"))
        files_section.add_file(Path("b.py"))
        await pilot.pause()

        # Step 2: externally-modified c.py -- bypass add_file entirely.
        (repo / "c.py").write_text("print('c v2 by external tool')\n", encoding="utf-8")

        # Pre-/diff invariants (s6 carve-out: FilesSection._files OK).
        assert set(files_section._files.keys()) == {Path("a.py"), Path("b.py")}, (
            f"pre-/diff FilesSection should hold a.py,b.py only -- got "
            f"{set(files_section._files.keys())}"
        )

        # Step 3: first /diff. DiffScreen mounts; dismiss.
        screen1 = await _open_diff(app, pilot)
        # Sanity: every dirty file appears as a panel on the first /diff.
        first_panels = {p.change.path for p in screen1.query(FileDiffPanel)}
        assert first_panels == {"a.py", "b.py", "c.py"}, (
            f"first DiffScreen should show every dirty file -- got {first_panels}"
        )
        # FilesSection still holds a.py + b.py (prune is remove-only;
        # dirty path set on first /diff = {a.py, b.py, c.py}; nothing to
        # prune from FilesSection because its keys are a subset).
        assert set(files_section._files.keys()) == {Path("a.py"), Path("b.py")}
        await _dismiss_diff(app, pilot)

        # Step 4: real-git commit of a.py.
        _run_git(repo, "add", "a.py")
        _run_git(repo, "commit", "-m", "claude commits a.py")

        # Step 5: second /diff. The prune step runs git status, sees
        # {b.py, c.py} as dirty, and removes a.py from FilesSection.
        # c.py is in dirty but NOT in FilesSection so it stays out
        # (s8.5 prune-only).
        screen2 = await _open_diff(app, pilot)

        assert set(files_section._files.keys()) == {Path("b.py")}, (
            f"post-commit FilesSection should hold b.py only -- got "
            f"{set(files_section._files.keys())}; "
            "a.py should have been pruned (clean vs HEAD); "
            "c.py should NOT have been added (prune-only)."
        )

        # The second DiffScreen still renders b.py and c.py (both dirty
        # in working tree) but NOT a.py (clean post-commit).
        second_panels = {p.change.path for p in screen2.query(FileDiffPanel)}
        assert second_panels == {"b.py", "c.py"}, (
            f"second DiffScreen should show b.py + c.py -- got {second_panels}; "
            "a.py was just committed and should be absent from the diff"
        )

        await _dismiss_diff(app, pilot)


# ---------------------------------------------------------------------------
# W3 -- Comment a hunk + toggle sort + dismiss + re-open: comment is
#       preserved across sort flip; persisted sort mode round-trips
#       (TEST_SPECIFICATION s4 W3; SPECIFICATION s9.2, s10).
# ---------------------------------------------------------------------------


def _dirty_all(repo: Path, mapping: dict[str, str]) -> None:
    """Overwrite each ``rel: content`` entry in the working tree."""
    for rel, content in mapping.items():
        target = repo / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


@pytest.mark.asyncio
async def test_w3_comment_survives_sort_toggle_and_persists(
    mock_sdk, nested_repo: Path
) -> None:
    """User comments a hunk, toggles sort twice, dismisses, reopens.

    Per TEST_SPECIFICATION W3:
      - HunkWidget instance preserved across sort flip (s10 P0,
        Skeptic-flagged): the same Python object is at ``(path,
        hunk_idx)`` after each ``s`` toggle.
      - The widget's ``.comment`` attribute equals the typed string
        after each toggle.
      - ``<repo>/.claudechic/diff.yaml`` exists on disk with
        ``sort_mode: directory`` after the second toggle (s9.2 round
        trip: directory -> alphabetical -> directory writes the file).
      - After dismiss + re-open, the freshly-mounted DiffScreen reads
        ``"directory"`` from disk -- verified via the screen's
        ``sub_title`` chrome (``"sort: directory"``), the user-visible
        sort indicator.

    Covers UA req 5 ("hunk comment preservation"), s10 in-place reorder,
    s9.2 sort-mode round-trip, s10 default sort mode = "directory".
    """
    repo = nested_repo

    # Dirty up every file so each file has at least one hunk.
    _dirty_all(
        repo,
        {
            "src/a.py": "print('src a v2')\n",
            "src/b.py": "print('src b v2')\n",
            "tests/x.py": "print('tests x v2')\n",
            "README.md": "# v2\n",
        },
    )

    app = ChatApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await _redirect_active_agent(app, pilot, repo)

        # Step 1: open /diff. Default sort mode is "directory" (s9.2).
        screen = await _open_diff(app, pilot)
        assert screen.sub_title == "sort: directory", (
            f"default sort mode should be 'directory' -- got "
            f"sub_title={screen.sub_title!r}"
        )

        # Step 2: locate the target hunk -- src/a.py's first sub-hunk.
        # Use the public ``_path_to_id`` encoding so we never bake a
        # hex literal into the test (s6 forbidden).
        target_path = "src/a.py"
        target_idx = 0
        target_hunk_id = _path_to_id(target_path, target_idx)
        target_widget = screen.query_one(f"#{target_hunk_id}", HunkWidget)
        target_widget_pyid_before = id(target_widget)

        # Focus the target hunk so screen-level ``enter`` action fires
        # CommentInput on the right widget.
        target_widget.focus()
        await pilot.pause()

        # Step 3: press enter -> CommentInput appears below the hunk.
        await pilot.press("enter")
        await pilot.pause()
        comment_input = target_widget.query_one(CommentInput)

        # Step 4: type a known comment and submit (enter inside the
        # CommentInput is bound priority=True to ``submit``).
        comment_text = "WORKFLOW3 hunk comment marker"
        comment_input.text = comment_text
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()

        # Comment landed on the HunkWidget (post-stop_editing).
        assert target_widget.comment == comment_text, (
            f"comment should have been saved on target HunkWidget -- got "
            f"{target_widget.comment!r}"
        )

        # Step 5: toggle sort twice. Each toggle MUST preserve the
        # HunkWidget instance (s10 P0); the comment MUST survive.
        await pilot.press("s")
        await pilot.pause()
        # After first toggle: alphabetical.
        assert screen.sub_title == "sort: alphabetical", (
            f"after first 's' toggle -- got sub_title={screen.sub_title!r}"
        )
        widget_after_first_toggle = screen.query_one(f"#{target_hunk_id}", HunkWidget)
        assert id(widget_after_first_toggle) == target_widget_pyid_before, (
            "HunkWidget instance must be preserved across sort change "
            "(s10 P0; Skeptic-flagged regression risk for hunk-comment loss)"
        )
        assert widget_after_first_toggle.comment == comment_text, (
            f"comment must survive sort flip -- got "
            f"{widget_after_first_toggle.comment!r} after first toggle"
        )

        await pilot.press("s")
        await pilot.pause()
        # After second toggle: back to directory.
        assert screen.sub_title == "sort: directory", (
            f"after second 's' toggle -- got sub_title={screen.sub_title!r}"
        )
        widget_after_second_toggle = screen.query_one(f"#{target_hunk_id}", HunkWidget)
        assert id(widget_after_second_toggle) == target_widget_pyid_before, (
            "HunkWidget instance must be preserved across the round-trip "
            "(directory -> alphabetical -> directory)"
        )
        assert widget_after_second_toggle.comment == comment_text, (
            f"comment must survive the round-trip -- got "
            f"{widget_after_second_toggle.comment!r} after second toggle"
        )

        # Step 6: <repo>/.claudechic/diff.yaml is on disk with
        # ``sort_mode: directory`` (the second toggle wrote it).
        yaml_path = repo / ".claudechic" / "diff.yaml"
        assert yaml_path.exists(), (
            f"sort-mode YAML should exist after toggle -- {yaml_path} missing"
        )
        yaml_text = yaml_path.read_text(encoding="utf-8")
        # Schema is ``sort_mode: directory`` per s9.2; substring match
        # avoids brittleness if PyYAML adds trailing whitespace etc.
        assert "sort_mode: directory" in yaml_text, (
            f"YAML should record sort_mode: directory -- got {yaml_text!r}"
        )

        # Step 7: dismiss DiffScreen, reopen, confirm the freshly
        # constructed DiffScreen reads "directory" from disk.
        await _dismiss_diff(app, pilot)
        screen2 = await _open_diff(app, pilot)
        assert screen2 is not screen, (
            "second /diff should mount a NEW DiffScreen instance"
        )
        assert screen2.sub_title == "sort: directory", (
            f"reopened DiffScreen should read sort_mode=directory from "
            f"the YAML -- got sub_title={screen2.sub_title!r}"
        )
        # Sanity: the four dirty files render as panels.
        panels = {p.change.path for p in screen2.query(FileDiffPanel)}
        assert panels == {"src/a.py", "src/b.py", "tests/x.py", "README.md"}, (
            f"reopened DiffScreen should render every dirty file -- got {panels}"
        )

        await _dismiss_diff(app, pilot)


# ---------------------------------------------------------------------------
# W2 -- Hide and unhide via keyboard and click; mixed kbd+mouse arc;
#       A2 force_visible; C1 doubly-hidden unhide; root-file 'd' no-op;
#       s7 tooltip wording (TEST_SPECIFICATION s4 W2).
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_w2_hide_unhide_via_keyboard_and_click(
    mock_sdk, nested_repo: Path
) -> None:
    """User hides files via keyboard, unhides via mouse click, in one arc.

    Per TEST_SPECIFICATION W2 (mixed-input single user story):
      - Press ``f`` on src/a.py -> it greys; its FileDiffPanel hides.
      - Press ``d`` on src/b.py -> src/ prefix hides; both src/* greys;
        tests/x.py and README.md unaffected.
      - Click src/b.py's greyed sidebar entry -> only b.py un-greys
        (A2 force_visible: per-file un-hide of prefix-greyed file --
        siblings stay hidden).
      - Click src/a.py's greyed sidebar entry -> the doubly-hidden
        file (in BOTH ``hide_files`` AND under the ``src/`` prefix)
        un-greys (C1 fix; SPECIFICATION s5.5.1 row 6 / independent-
        clauses unhide).
      - On a root file (README.md), press ``d`` -> footer hint
        ``no parent directory to hide`` surfaces (s5.1); README.md
        remains visible; tests/x.py and the (now visible) src/* files
        unaffected.
      - Press ``r`` -> every entry un-greys; every panel re-displays;
        focus lands on a hunk in the first visible file.

    Tooltip wording on greyed entries follows s7 verbatim:
      - prefix-only:           ``click to un-hide just this file (src/ stays hidden)``
      - hide_files-only:       ``click to un-hide``

    Covers: A2 force_visible (UA req 3); C1 fix; root-file ``d`` no-op
    + footer hint (s5.1); s7 tooltip wording; keyboard+mouse-bundling
    guard.
    """
    repo = nested_repo

    # Dirty up every file -- each becomes a 1-hunk diff.
    _dirty_all(
        repo,
        {
            "src/a.py": "print('src a v2')\n",
            "src/b.py": "print('src b v2')\n",
            "tests/x.py": "print('tests x v2')\n",
            "README.md": "# v2\n",
        },
    )

    app = ChatApp()
    async with app.run_test(size=(120, 40), notifications=True) as pilot:
        await _redirect_active_agent(app, pilot, repo)
        screen = await _open_diff(app, pilot)

        # User-observable lookup helpers (s6 forbidden: no internal
        # state; rely on rendered widget state via DOM queries).
        def _sidebar_item(path: str) -> DiffFileItem:
            return screen.query_one(f"#{_path_to_id(path)}", DiffFileItem)

        def _file_panel(path: str) -> FileDiffPanel:
            return screen.query_one(
                f"#panel-{_path_to_id(path).removeprefix('sidebar-')}",
                FileDiffPanel,
            )

        def _hunk_widget(path: str, idx: int = 0) -> HunkWidget:
            return screen.query_one(f"#{_path_to_id(path, idx)}", HunkWidget)

        # ── Step 1: ``f`` on src/a.py. ───────────────────────────────
        _hunk_widget("src/a.py").focus()
        await pilot.pause()
        await pilot.press("f")
        await pilot.pause()
        assert _sidebar_item("src/a.py").has_class("hidden-entry"), (
            "src/a.py sidebar entry should carry .hidden-entry after 'f'"
        )
        assert _file_panel("src/a.py").display is False, (
            "src/a.py panel should be hidden (display=False) after 'f'"
        )
        # Tooltip wording: hide_files-only path -- s7 verbatim.
        assert _sidebar_item("src/a.py").tooltip == "click to un-hide", (
            f"hide_files-only tooltip -- got {_sidebar_item('src/a.py').tooltip!r}"
        )
        # Other files untouched.
        assert not _sidebar_item("src/b.py").has_class("hidden-entry")
        assert not _sidebar_item("tests/x.py").has_class("hidden-entry")
        assert not _sidebar_item("README.md").has_class("hidden-entry")

        # ── Step 2: ``d`` on src/b.py -- hides src/ prefix. ──────────
        _hunk_widget("src/b.py").focus()
        await pilot.pause()
        await pilot.press("d")
        await pilot.pause()
        # Both src/* files now greyed (a.py from f-hide AND prefix;
        # b.py from prefix only).
        assert _sidebar_item("src/a.py").has_class("hidden-entry")
        assert _sidebar_item("src/b.py").has_class("hidden-entry")
        assert _file_panel("src/a.py").display is False
        assert _file_panel("src/b.py").display is False
        # tests/x.py and README.md unaffected (different / no prefix).
        assert not _sidebar_item("tests/x.py").has_class("hidden-entry")
        assert not _sidebar_item("README.md").has_class("hidden-entry")
        # Tooltip wording on the prefix-only file (s7 verbatim).
        assert (
            _sidebar_item("src/b.py").tooltip
            == "click to un-hide just this file (src/ stays hidden)"
        ), f"prefix-only tooltip -- got {_sidebar_item('src/b.py').tooltip!r}"
        # src/a.py is doubly-hidden; tooltip still uses prefix wording
        # (s7: prefix membership wins for tooltip context regardless of
        # simultaneous hide_files membership).
        assert (
            _sidebar_item("src/a.py").tooltip
            == "click to un-hide just this file (src/ stays hidden)"
        ), (
            f"doubly-hidden file tooltip should use prefix wording -- got "
            f"{_sidebar_item('src/a.py').tooltip!r}"
        )

        # ── Step 3: click src/b.py greyed entry -- A2 force_visible. ─
        b_item = _sidebar_item("src/b.py")
        await pilot.click(f"#{b_item.id}")
        await pilot.pause()
        # Only b.py un-greys; src/a.py stays hidden (UA req 3 verbatim).
        assert not _sidebar_item("src/b.py").has_class("hidden-entry"), (
            "src/b.py should un-grey after click (A2 force_visible)"
        )
        assert _file_panel("src/b.py").display is True
        assert _sidebar_item("src/a.py").has_class("hidden-entry"), (
            "src/a.py must STAY greyed -- siblings under src/ remain hidden"
        )
        assert _file_panel("src/a.py").display is False

        # ── Step 4: click src/a.py (doubly-hidden) -- C1 unhide. ─────
        a_item = _sidebar_item("src/a.py")
        await pilot.click(f"#{a_item.id}")
        await pilot.pause()
        # Doubly-hidden file un-greys (independent-clauses unhide:
        # remove from hide_files AND add to force_visible; post-condition
        # is_hidden(P) == False).
        assert not _sidebar_item("src/a.py").has_class("hidden-entry"), (
            "src/a.py must un-grey after C1 click (s5.5.1 row 6: "
            "independent-clauses unhide)"
        )
        assert _file_panel("src/a.py").display is True

        # ── Step 5: ``d`` on README.md (root) -- no-op + footer hint.
        _hunk_widget("README.md").focus()
        await pilot.pause()
        # Drain any prior notifications so the assertion below is
        # specific to the d-on-root keypress.
        prior_notifications = list(app._notifications)
        await pilot.press("d")
        await pilot.pause()
        new_notifications = [
            n for n in app._notifications if n not in prior_notifications
        ]
        assert any(
            "no parent directory to hide" in str(n.message) for n in new_notifications
        ), (
            "footer hint 'no parent directory to hide' should surface on "
            f"d-at-repo-root -- new notifications: "
            f"{[str(n.message) for n in new_notifications]}"
        )
        # README.md remains visible -- d on root is a no-op.
        assert not _sidebar_item("README.md").has_class("hidden-entry")
        assert _file_panel("README.md").display is True

        # ── Step 6: ``r`` -- reset hide state for current cwd. ───────
        await pilot.press("r")
        await pilot.pause()
        # Every entry un-greys; every panel re-displays.
        for path in ("src/a.py", "src/b.py", "tests/x.py", "README.md"):
            assert not _sidebar_item(path).has_class("hidden-entry"), (
                f"{path} should be visible after 'r'"
            )
            assert _file_panel(path).display is True, (
                f"{path}'s panel should re-display after 'r'"
            )

        await _dismiss_diff(app, pilot)
