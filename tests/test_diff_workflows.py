"""Workflow tests for diff_review_ux (W1-W8).

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
    DiffDirectoryItem,
    DiffFileItem,
    DirFoldGlyph,
    FileDiffPanel,
    HunkWidget,
    _dir_to_id,
    _path_to_hex,
    _path_to_id,
)
from claudechic.screens.diff import DiffScreen
from textual.widgets import Static

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


@pytest.fixture
def feature_branch_repo(tmp_path: Path) -> tuple[Path, str, list[str]]:
    """Feature-branch topology (W6, s5 B3).

    Setup:
      - ``make_repo`` base with two committed files (F.py=v1 and
        stable.py); HEAD = main.
      - ``git update-ref refs/remotes/origin/main <head_sha>`` --
        publishes the local main as ``origin/main`` (no actual
        remote, no network; the ref resolves locally).
      - Checkout feature branch; commit F.py=v2.
      - Revert F.py's working-tree content to v1 WITHOUT staging.
        Result: F.py is dirty vs HEAD (HEAD has v2, working tree has
        v1) AND identical to ``origin/main`` (also v1).
      - Six untracked files at the repo root.

    Returns ``(repo, F_path, untracked_paths)`` so the test refers
    to F and the untracked set by name without re-deriving them.

    The W6 invariants the test asserts against this topology are:
      - R1: prune basis is HEAD even when DiffScreen target !=
        HEAD. F.py is dirty vs HEAD, so prune KEEPS it -- even
        though ``git diff origin/main`` shows no hunks for F.
      - R2: untracked truncation does not corrupt the prune basis.
        6 untracked files all participate in ``get_dirty_paths``;
        a Claude-Written untracked file stays in ``FilesSection``
        across the prune step.
      - s8a: ``MAX_UNTRACKED_FILES`` count cap removed -- the 6+
        untracked all render as panels under ``/diff origin/main``.
    """
    repo = make_repo(
        tmp_path,
        name="feature_branch",
        initial={
            "F.py": "v1\n",
            "stable.py": "stable\n",
        },
    )
    # Capture the post-initial-commit SHA (HEAD = main, F.py at v1).
    head_sha_proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(repo),
        env=_git_env(),
        check=True,
        capture_output=True,
    )
    head_sha = head_sha_proc.stdout.decode("utf-8").strip()
    # Publish the current HEAD as origin/main (no actual remote /
    # network; the ref resolves locally per s5 B3).
    _run_git(repo, "update-ref", "refs/remotes/origin/main", head_sha)
    # Create feature branch and commit F.py=v2.
    _run_git(repo, "checkout", "-b", "feature")
    (repo / "F.py").write_text("v2\n", encoding="utf-8")
    _run_git(repo, "add", "F.py")
    _run_git(repo, "commit", "-m", "feature: F v2")
    # Revert F.py's WORKING-TREE content back to v1 -- dirty vs
    # HEAD (which has v2) and identical to origin/main (which has
    # v1). The revert is NOT staged.
    (repo / "F.py").write_text("v1\n", encoding="utf-8")
    # Six untracked files at the top level. Each gets a small
    # synthetic body so DiffScreen can render a non-empty hunk
    # (untracked files render as additions vs an empty old-side).
    untracked_paths = [f"u{i}.py" for i in range(1, 7)]
    for rel in untracked_paths:
        (repo / rel).write_text(f"# untracked {rel}\n", encoding="utf-8")
    return repo, "F.py", untracked_paths


@pytest.fixture
def two_repos(tmp_path: Path) -> tuple[Path, Path]:
    """Two-repos topology (W5): repo_a and repo_b in DIFFERENT subdirs.

    Each repo is independently set up via ``make_repo`` (hermetic git
    env, per-repo identity, .gitignore covers .claudechic/, one initial
    commit). Files are dirtied in both so each repo has a non-empty
    diff. Distinct cwd ``Path`` values are the input -- per-cwd
    HideStore isolation (s5.4) is the property under test.
    """
    repo_a = make_repo(
        tmp_path,
        name="repo_a",
        initial={
            "a1.py": "print('a1 v1')\n",
            "a2.py": "print('a2 v1')\n",
        },
    )
    repo_b = make_repo(
        tmp_path,
        name="repo_b",
        initial={
            "b1.py": "print('b1 v1')\n",
            "b2.py": "print('b2 v1')\n",
        },
    )
    # Dirty every file -- each repo's /diff has two 1-hunk panels.
    (repo_a / "a1.py").write_text("print('a1 v2')\n", encoding="utf-8")
    (repo_a / "a2.py").write_text("print('a2 v2')\n", encoding="utf-8")
    (repo_b / "b1.py").write_text("print('b1 v2')\n", encoding="utf-8")
    (repo_b / "b2.py").write_text("print('b2 v2')\n", encoding="utf-8")
    return repo_a, repo_b


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
    # On Python 3.11 the asyncio event-loop scheduling causes
    # ``on_chat_screen_ready`` to fire before all ChatScreen children
    # are registered in the DOM. ``files_section.clear()`` (below)
    # triggers ``_position_right_sidebar`` -> ``_layout_sidebar_contents``
    # -> ``self.process_panel.process_count`` -> ``query_one("#process-panel")``,
    # which raises ``NoMatches`` if that widget hasn't mounted yet.
    # Wait until ``#process-panel`` is queryable before proceeding.
    # Bumped from 20 to 100 iterations to cover slow CI runners where the
    # 20-tick budget (~1s) was too tight; W4/W5/W8 flakes on macOS/Windows
    # surfaced as ``NoMatches: No nodes match '#process-panel'``.
    for _ in range(100):
        if app.query("#process-panel"):
            break
        await pilot.pause()
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
# W4 -- Hide everything; see the empty-state placeholder; press r;
#       diff returns (TEST_SPECIFICATION s4 W4; SPECIFICATION s6.4
#       empty-state placeholder, s6.2 focus policy from empty-state).
# ---------------------------------------------------------------------------


@pytest.fixture
def two_file_repo(tmp_path: Path) -> Path:
    """Single-repo topology with exactly two tracked files (W4).

    Distinct from ``single_repo`` (3 files) because s6.4's verbatim
    placeholder text ("All N files hidden.") interpolates ``N`` from
    the count, and the spec example uses ``N == 2``. Two dirty files
    -> two ``FileDiffPanel``s -> ``All 2 files hidden.`` after both
    are hidden.
    """
    return make_repo(
        tmp_path,
        name="two_file",
        initial={
            "a.py": "print('a v1')\n",
            "b.py": "print('b v1')\n",
        },
    )


@pytest.mark.asyncio
async def test_w4_hide_all_show_empty_state_then_reset(
    mock_sdk, two_file_repo: Path
) -> None:
    """User hides every file in the diff, sees the s6.4 empty-state,
    presses ``r`` to recover.

    Sequence (TEST_SPECIFICATION W4):
      - ``/diff`` opens. Two files dirty.
      - Pilot presses ``f`` once per file (with ``j`` between to
        advance focus).
      - Pilot presses ``r``.

    Asserts:
      - After all hides: every ``FileDiffPanel.display`` is False; a
        ``Static`` with id ``diff-view-empty-state`` is mounted; its
        plain-text content equals exactly the s6.4 verbatim block:

            All 2 files hidden.
            Click any greyed entry in the sidebar to un-hide it,
            or press r to reset all hides.

      - After ``r``: empty-state ``Static`` is removed; both panels'
        ``display`` is True; current focus is on a hunk in the first
        visible file (s6.2: ``r`` from the empty-state moves focus to
        the first hunk of the first visible file).

    Covers: s6.4 placeholder text verbatim; reset semantics from the
    empty-state; s6.2 focus-from-empty-state carve-out.
    """
    repo = two_file_repo

    # Dirty both files so each becomes a 1-hunk diff.
    (repo / "a.py").write_text("print('a v2')\n", encoding="utf-8")
    (repo / "b.py").write_text("print('b v2')\n", encoding="utf-8")

    app = ChatApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await _redirect_active_agent(app, pilot, repo)
        screen = await _open_diff(app, pilot)

        # Sanity: two panels mounted, neither hidden initially.
        panels_initial = list(screen.query(FileDiffPanel))
        assert len(panels_initial) == 2, (
            f"two_file_repo should produce exactly two panels -- got "
            f"{[p.change.path for p in panels_initial]}"
        )
        for panel in panels_initial:
            assert panel.display is True, (
                f"panel {panel.change.path} should be visible at /diff open"
            )

        # Hide both files: f, j, f. The j between advances the focused
        # hunk so the second f hides the second file (rather than
        # idempotently re-hiding the first).
        await pilot.press("f")
        await pilot.pause()
        await pilot.press("j")
        await pilot.pause()
        await pilot.press("f")
        await pilot.pause()

        # Every panel hidden.
        for panel in screen.query(FileDiffPanel):
            assert panel.display is False, (
                f"panel {panel.change.path} should be hidden (display=False) "
                "after both 'f' presses"
            )

        # Empty-state placeholder mounted with verbatim s6.4 text.
        empty = screen.query_one("#diff-view-empty-state", Static)
        expected_text = (
            "All 2 files hidden.\n"
            "Click any greyed entry in the sidebar to un-hide it,\n"
            "or press r to reset all hides."
        )
        # ``Static.render()`` returns the renderable; ``str()`` on a
        # plain-text Static yields the literal string. The Static was
        # mounted with ``markup=False`` (per ``_show_empty_state``) so
        # there is no Rich-markup tag interpretation to strip.
        rendered = str(empty.render())
        assert rendered == expected_text, (
            f"s6.4 empty-state placeholder must match VERBATIM -- got "
            f"{rendered!r}, expected {expected_text!r}"
        )

        # Press 'r' -- reset hide state for current cwd.
        await pilot.press("r")
        await pilot.pause()

        # Empty-state Static removed.
        assert not screen.query("#diff-view-empty-state"), (
            "empty-state Static should be removed after 'r'"
        )
        # Every panel re-displays.
        for panel in screen.query(FileDiffPanel):
            assert panel.display is True, (
                f"panel {panel.change.path} should be visible after 'r'"
            )

        # Per SPECIFICATION s6.2: ``r`` from the empty-state moves
        # focus to the first hunk of the first visible file. Verify
        # via app.focused (a HunkWidget belonging to the first visible
        # file in DisplayTree order). After ``r``, sort=directory
        # (default) so the file order is alphabetical: a.py first.
        assert isinstance(app.focused, HunkWidget), (
            f"after 'r' from empty-state, focus should be on a HunkWidget "
            f"-- got {type(app.focused).__name__ if app.focused else None}"
        )
        assert app.focused.path == "a.py", (
            f"focus should be on the first visible file's hunk after 'r' "
            f"from empty-state (s6.2) -- got path={app.focused.path!r}"
        )

        await _dismiss_diff(app, pilot)


# ---------------------------------------------------------------------------
# W5 -- Two-repos isolation: hides in repo A do not appear in repo B
#       within the same session (TEST_SPECIFICATION s4 W5;
#       SPECIFICATION s5.4 per-cwd HideStore isolation, s7
#       same-cwd persistence across DiffScreen dismiss/reopen).
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_w5_two_repos_hide_isolation(
    mock_sdk, two_repos: tuple[Path, Path]
) -> None:
    """User hides a file in repo A; switches to repo B (no leakage);
    returns to repo A (hide survives).

    Sequence (TEST_SPECIFICATION W5):
      - Active agent in ``repo_a``. ``/diff`` opens. Pilot presses
        ``f`` to hide a file. Dismiss.
      - Active agent's cwd is switched to ``repo_b`` (mutation of
        ``app._agent.cwd``; the spec defers the exact mechanism to
        testing-implementation, asserting only the resulting
        behavior). ``/diff`` opens for ``repo_b``.
      - cwd is switched back to ``repo_a``. ``/diff`` opens.

    Asserts:
      - After ``/diff`` in ``repo_b``: zero ``.hidden-entry`` classes;
        zero ``FileDiffPanel.display == False``.
      - After re-opening ``/diff`` in ``repo_a``: the previously
        hidden file is still greyed (per-cwd persistence within the
        same App lifetime).

    Covers: HideStore per-cwd isolation (s5.4); same-cwd persistence
    across DiffScreen dismiss/reopen.

    cwd-switch mechanism note: the live agent's ``cwd`` attribute is
    mutated directly. This matches W1-W3's ``_redirect_active_agent``
    helper -- ``HideStore.get(repo_key)`` is keyed by the raw
    ``cwd: Path`` per s5.4 (no symlink resolution, no
    ``rev-parse --show-toplevel``), so two distinct ``Path`` values
    are independent ``HideState`` slots regardless of how the cwd was
    set. The agent-manager swap path (which would spawn a second SDK
    client) is unnecessary for this property.
    """
    repo_a, repo_b = two_repos

    app = ChatApp()
    async with app.run_test(size=(120, 40)) as pilot:
        # Initial cwd: repo_a.
        await _redirect_active_agent(app, pilot, repo_a)

        # ── Step 1: /diff in repo_a; hide a1.py via 'f'. ─────────────
        screen_a1 = await _open_diff(app, pilot)
        # Sanity: repo_a's panels are exactly {a1.py, a2.py}.
        a1_paths = {p.change.path for p in screen_a1.query(FileDiffPanel)}
        assert a1_paths == {"a1.py", "a2.py"}, (
            f"repo_a /diff should show only repo_a's files -- got {a1_paths}"
        )
        # Default focus lands on the first hunk (alphabetical first =
        # a1.py). Press 'f' to hide that file.
        await pilot.press("f")
        await pilot.pause()
        a1_item = screen_a1.query_one(f"#{_path_to_id('a1.py')}", DiffFileItem)
        assert a1_item.has_class("hidden-entry"), (
            "a1.py should be greyed in repo_a after 'f' (sanity check before "
            "the cross-repo isolation assertion)"
        )

        # Dismiss /diff -- DiffScreen pops; HideStore[repo_a] survives.
        await _dismiss_diff(app, pilot)

        # ── Step 2: switch agent's cwd to repo_b; open /diff. ────────
        # Direct mutation of the live agent's cwd. Per the test docstring
        # rationale, HideStore is keyed by raw Path so this is sufficient.
        # Mirror ``_redirect_active_agent``: set both ``agent.cwd`` and
        # ``app._cwd`` so the App's ancillary bookkeeping (workflow infra,
        # file index root) stays consistent with the diff target.
        # Composability CP-B note: ``_prune_files_section_to_git(agent)``
        # reads ``agent.cwd`` only, so for W5's narrow scope ``app._cwd``
        # is harmless either way -- but matching the helper's pattern
        # avoids a future copy-paste foot-gun.
        assert app._agent is not None  # already true post-_redirect; satisfies pyright
        app._agent.cwd = repo_b
        app._cwd = repo_b
        await pilot.pause()

        screen_b = await _open_diff(app, pilot)
        b_paths = {p.change.path for p in screen_b.query(FileDiffPanel)}
        assert b_paths == {"b1.py", "b2.py"}, (
            f"repo_b /diff should show only repo_b's files -- got {b_paths}; "
            "if repo_a's files appear, the cwd switch did not redirect "
            "get_changes correctly."
        )
        # No leakage: every DiffFileItem in repo_b is NOT greyed; every
        # FileDiffPanel is visible.
        for item in screen_b.query(DiffFileItem):
            assert not item.has_class("hidden-entry"), (
                f"{item.path} in repo_b carries .hidden-entry -- HideStore "
                "isolation broken: repo_a's hide leaked across cwd switch."
            )
        for panel in screen_b.query(FileDiffPanel):
            assert panel.display is True, (
                f"{panel.change.path} panel in repo_b is hidden -- HideStore "
                "leaked across cwd switch."
            )

        await _dismiss_diff(app, pilot)

        # ── Step 3: switch back to repo_a; verify a1.py still hidden. ─
        # Mirror the helper pattern (see Step 2 comment).
        assert app._agent is not None
        app._agent.cwd = repo_a
        app._cwd = repo_a
        await pilot.pause()

        screen_a2 = await _open_diff(app, pilot)
        # Should re-render repo_a's files.
        a2_paths = {p.change.path for p in screen_a2.query(FileDiffPanel)}
        assert a2_paths == {"a1.py", "a2.py"}, (
            f"return-to-repo_a /diff should show repo_a's files again -- got {a2_paths}"
        )
        # The earlier hide on a1.py must still apply (HideStore[repo_a]
        # is alive for the App's lifetime).
        a1_item_2 = screen_a2.query_one(f"#{_path_to_id('a1.py')}", DiffFileItem)
        assert a1_item_2.has_class("hidden-entry"), (
            "a1.py should STILL be greyed after the round-trip through "
            "repo_b -- per-cwd persistence within the App lifetime "
            "(s5.4) is broken."
        )
        a1_panel_2 = screen_a2.query_one(
            f"#panel-{_path_to_hex('a1.py')}",
            FileDiffPanel,
        )
        assert a1_panel_2.display is False, (
            "a1.py's panel should still be hidden after returning to repo_a"
        )
        # a2.py was never hidden -- still visible.
        a2_item_2 = screen_a2.query_one(f"#{_path_to_id('a2.py')}", DiffFileItem)
        assert not a2_item_2.has_class("hidden-entry"), (
            "a2.py should still be visible -- it was never hidden"
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
        (A2 force_visible: per-file unhide of prefix-greyed file --
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
            return screen.query_one(f"#panel-{_path_to_hex(path)}", FileDiffPanel)

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
        # specific to the d-on-root keypress. Textual test-API
        # convention: ``run_test(notifications=True)`` (above) enables
        # capture; ``app._notifications`` is the documented
        # introspection point for test code (Skeptic CP-A S1). Not a
        # SUT private-state read.
        prior_notifications = list(app._notifications)
        await pilot.press("d")
        await pilot.pause()
        new_notifications = [
            n for n in app._notifications if n not in prior_notifications
        ]
        # Per SPEC s5.5 the footer hint is the locked verbatim string
        # ``"no parent directory to hide"`` -- equality, not substring.
        # If Textual ever wraps the message in a way that breaks
        # equality, treat that as a regression and escalate (don't
        # carve out a substring fallback).
        assert any(
            str(n.message) == "no parent directory to hide" for n in new_notifications
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


# ---------------------------------------------------------------------------
# W6 -- Feature branch ahead of origin/main; many untracked;
#       /diff target != HEAD (TEST_SPECIFICATION s4 W6;
#       SPECIFICATION R1 prune basis is HEAD; R2 untracked-truncation
#       does not corrupt prune basis; s8a MAX_UNTRACKED_FILES cap
#       removal).
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_w6_feature_branch_diff_against_origin_main(
    mock_sdk, feature_branch_repo: tuple[Path, str, list[str]]
) -> None:
    """User on a feature branch with a working-tree file F that
    matches ``origin/main`` exactly, plus 6+ untracked files (one
    Claude-Written, the rest written outside the conversation),
    opens ``/diff origin/main``.

    Sequence (TEST_SPECIFICATION W6):
      - Test simulates Claude ``Write``-ing one of the untracked
        files (``add_file`` for it) AND tracking F in
        ``FilesSection`` (``add_file(F)``).
      - ``/diff origin/main`` opens.

    Asserts:
      - All 6 untracked files render as ``DiffFileItem`` rows in
        ``DiffSidebar``; the "No uncommitted changes" empty-state
        is NOT shown (s8a ``MAX_UNTRACKED_FILES`` cap removal).
      - The Claude-Written untracked file IS in
        ``app.files_section._files`` -- prune kept it (R2:
        ``get_dirty_paths`` reports all untracked, no truncation).
      - F IS in ``app.files_section._files`` -- prune kept it
        because it is dirty vs HEAD, even though
        ``git diff origin/main`` shows no hunks for F (R1: prune
        basis is HEAD, NOT the ``target`` argument).
      - DiffScreen does NOT render F as a ``FileDiffPanel`` (since
        F has no hunks vs ``origin/main``). The disagreement
        between FilesSection (keeps F) and DiffScreen (no F panel)
        is the user-observable demonstration of the HEAD-vs-target
        separation.

    Covers: R1 -- prune basis is HEAD, not target (UA req 1); R2 --
    untracked-truncation does not corrupt prune basis (UA req 2);
    s8a in-scope side-fix (count cap removed).
    """
    repo, f_path, untracked_paths = feature_branch_repo

    app = ChatApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await _redirect_active_agent(app, pilot, repo)

        # Simulate Claude ``Write``-ing the FIRST untracked file
        # (``add_file`` for it) AND tracking F in FilesSection.
        # The other five untracked files were created by the fixture
        # WITHOUT add_file, mirroring "files Claude did not author".
        claude_written = untracked_paths[0]
        files_section = app.files_section
        files_section.add_file(Path(claude_written))
        files_section.add_file(Path(f_path))
        await pilot.pause()

        # Pre-/diff invariant: FilesSection holds exactly the two
        # tracked-by-test entries.
        assert set(files_section._files.keys()) == {
            Path(claude_written),
            Path(f_path),
        }, (
            f"pre-/diff FilesSection should hold {{{claude_written}, {f_path}}} "
            f"only -- got {set(files_section._files.keys())}"
        )

        # Open /diff origin/main via the slash-command parser
        # (``commands.py`` parses ``/diff <target>``).
        await submit_command(app, pilot, "/diff origin/main")
        await wait_for_workers(app)
        for _ in range(6):
            await pilot.pause()
        screen = app.screen
        assert isinstance(screen, DiffScreen), (
            f"expected DiffScreen on top, got {type(screen).__name__}"
        )

        # Assert: every untracked file renders as a panel under
        # /diff origin/main. s8a verifies the count cap was lifted;
        # without the fix, only 4 of 6 would have appeared.
        rendered_paths = {p.change.path for p in screen.query(FileDiffPanel)}
        for u in untracked_paths:
            assert u in rendered_paths, (
                f"{u} should render as a panel under /diff origin/main "
                f"-- s8a MAX_UNTRACKED_FILES cap removed; got "
                f"{sorted(rendered_paths)}"
            )

        # Assert: F.py is NOT rendered as a panel -- working-tree
        # content is identical to origin/main, so git diff origin/main
        # produces no hunks for F.
        assert f_path not in rendered_paths, (
            f"{f_path} should NOT render as a panel under "
            f"/diff origin/main -- working-tree content is identical "
            f"to origin/main (no hunks); R1 demonstrates HEAD vs "
            f"target separation. Got rendered set: {sorted(rendered_paths)}"
        )

        # Assert: the "No uncommitted changes" empty-state is NOT
        # shown. With 6 untracked files + s8a cap-removal, every
        # untracked must surface.
        assert not screen.query("#diff-empty"), (
            "'No uncommitted changes' empty-state should NOT show under "
            "/diff origin/main with 6+ untracked files (s8a)"
        )

        # Assert: FilesSection prune KEPT F -- prune basis is HEAD,
        # F is dirty vs HEAD even though identical to origin/main
        # (R1, UA req 1, verbatim).
        assert Path(f_path) in files_section._files, (
            f"{f_path} must be KEPT in FilesSection -- prune basis is "
            f"HEAD per s8.6, and {f_path} is dirty vs HEAD (working "
            f"tree=v1, HEAD=v2) even though identical to origin/main. "
            f"R1 verbatim. Got: {set(files_section._files.keys())}"
        )

        # Assert: FilesSection prune KEPT the Claude-Written
        # untracked. ``get_dirty_paths`` reports all untracked
        # without truncation per R2 -- the prune step's dirty path
        # set contains every untracked, so an entry whose path is
        # untracked is never silently dropped (UA req 2 verbatim).
        assert Path(claude_written) in files_section._files, (
            f"{claude_written} must be KEPT in FilesSection -- "
            f"untruncated untracked: 6+ untracked do not silently "
            f"drop a Claude-Written one. R2 verbatim. Got: "
            f"{set(files_section._files.keys())}"
        )

        await _dismiss_diff(app, pilot)


# ---------------------------------------------------------------------------
# W7 -- Hide directory; dismiss; new file later inherits hidden
#       (TEST_SPECIFICATION s4 W7; SPECIFICATION s5: prefix
#       inheritance, UA req 4).
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_w7_hide_directory_new_file_inherits_hidden(
    mock_sdk, nested_repo: Path
) -> None:
    """User hides ``src/`` then dismisses ``/diff``; later writes a
    NEW file under ``src/``; on re-opening ``/diff`` the new file is
    greyed because it inherits the active prefix hide.

    Sequence (TEST_SPECIFICATION W7):
      - ``/diff`` opens. Pilot navigates to a hunk in ``src/a.py``.
        Pilot presses ``d`` -> ``src/`` is hidden.
      - Pilot dismisses.
      - Test writes ``src/c.py`` to disk (new untracked file; same
        App lifetime).
      - ``/diff`` re-opens.

    Asserts:
      - After re-open: ``DiffFileItem`` for ``src/c.py`` carries
        ``.hidden-entry`` (inherited from the same ``HideStore`` in
        App scope).
      - ``FileDiffPanel.display`` is False for ``src/c.py``.
      - Tooltip on ``src/c.py``'s greyed entry is the s7 verbatim
        prefix wording: ``click to un-hide just this file (src/
        stays hidden)``.
      - ``src/a.py`` is also still greyed (HideState survived
        dismiss-and-reopen).

    Covers: prefix inheritance -- "new files in a hidden folder
    stay hidden" (UA req 4 verbatim).
    """
    repo = nested_repo
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

        # Step 1: open /diff, focus src/a.py's hunk, press 'd' to hide src/.
        screen1 = await _open_diff(app, pilot)
        target_widget = screen1.query_one(f"#{_path_to_id('src/a.py', 0)}", HunkWidget)
        target_widget.focus()
        await pilot.pause()
        await pilot.press("d")
        await pilot.pause()

        # Sanity: both src/* files are greyed (prefix hide).
        assert screen1.query_one(f"#{_path_to_id('src/a.py')}", DiffFileItem).has_class(
            "hidden-entry"
        )
        assert screen1.query_one(f"#{_path_to_id('src/b.py')}", DiffFileItem).has_class(
            "hidden-entry"
        )

        # Step 2: dismiss /diff. HideStore[repo] keeps src/ in
        # hide_prefixes for the App lifetime.
        await _dismiss_diff(app, pilot)

        # Step 3: write src/c.py to disk (NEW untracked under src/).
        # The HideStore was NOT notified about this file specifically;
        # the prefix-match resolution in ``HideState.is_hidden`` is
        # what makes the inheritance fire on next /diff.
        (repo / "src" / "c.py").write_text(
            "print('src c -- newly added under hidden prefix')\n",
            encoding="utf-8",
        )

        # Step 4: re-open /diff. The fresh DisplayTree inherits the
        # active prefix hide.
        screen2 = await _open_diff(app, pilot)

        # src/c.py is rendered (it's dirty / untracked) AND greyed.
        c_paths = {p.change.path for p in screen2.query(FileDiffPanel)}
        assert "src/c.py" in c_paths, (
            f"src/c.py should render as a panel after re-open -- got {sorted(c_paths)}"
        )
        c_item = screen2.query_one(f"#{_path_to_id('src/c.py')}", DiffFileItem)
        assert c_item.has_class("hidden-entry"), (
            "src/c.py should be greyed on re-open -- prefix inheritance "
            "(UA req 4); HideStore in App scope retained src/ as a hide "
            "prefix, and src/c.py matches that prefix on next "
            "build_tree + apply_hide pass."
        )
        c_panel = screen2.query_one(f"#panel-{_path_to_hex('src/c.py')}", FileDiffPanel)
        assert c_panel.display is False, (
            "src/c.py's FileDiffPanel should be hidden (display=False) "
            "on re-open -- prefix inheritance"
        )
        # s7 tooltip wording on the inherited hide.
        assert (
            c_item.tooltip == "click to un-hide just this file (src/ stays hidden)"
        ), f"s7 tooltip wording on prefix-inherited entry -- got {c_item.tooltip!r}"

        # Sanity: src/a.py is also still greyed -- HideState survived
        # dismiss/reopen (s5.4 same-cwd persistence).
        a_item_2 = screen2.query_one(f"#{_path_to_id('src/a.py')}", DiffFileItem)
        assert a_item_2.has_class("hidden-entry"), (
            "src/a.py should still be greyed after dismiss/reopen "
            "-- HideState persistence within App lifetime"
        )

        await _dismiss_diff(app, pilot)


# ---------------------------------------------------------------------------
# W8 -- Directory header fold/hide affordances; fold and hide are orthogonal
#       axes (TEST_SPECIFICATION W8; UIDesigner items 1-4 + independence).
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_w8_directory_header_fold_and_hide(mock_sdk, nested_repo: Path) -> None:
    """User folds/unfolds src/ via glyph click; hides/unhides via name
    click; four fold x hide states visited; independence asserted at
    every transition.

    Single user arc (TEST_SPECIFICATION W8):

      State 0 (fold=F, hide=F) -- initial; all sidebar rows and DiffView
        panels visible; header NOT muted.

      Step 1: click [-] glyph -> fold (fold=T, hide=F)
        - Sidebar file rows for src/*.py collapse (display=False).
        - DiffView FileDiffPanel for src/*.py remain visible (fold is
          NOT hide -- orthogonal axes).
        - dir-header--hidden NOT on DiffDirectoryItem (fold doesn't mute).

      Step 2: click directory name (not hidden) -> hide (fold=T, hide=T)
        - DiffDirectoryItem carries dir-header--hidden (label muted).
        - DiffView panels for src/*.py now hidden (display=False).
        - Sidebar rows STILL display=False (fold state unchanged by hide).
        - Sidebar items carry hidden-entry class.

      Step 3: click [+] glyph -> unfold (fold=F, hide=T)
        - Sidebar rows reappear (display=True) as greyed hidden-entry rows.
        - DiffView panels remain hidden (unfold doesn't affect DiffView).
        - dir-header--hidden still on header (unfold doesn't unmute).

      Step 4: click directory name (hidden) -> unhide (fold=F, hide=F)
        - dir-header--hidden removed; panels return (display=True);
          rows lose hidden-entry.

    Sanity: tests/ and README.md unaffected throughout.

    Independence is asserted at every transition: glyph click only
    toggles sidebar row display; name click only toggles
    dir-header--hidden + FileDiffPanel.display.

    Covers UIDesigner items 1 (collapse glyph), 2 (expand glyph),
    3 (click name -> hide), 4 (click name -> unhide), plus fold/hide
    independence.
    """
    repo = nested_repo
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
        screen = await _open_diff(app, pilot)

        # Directory sort mode is required for DiffDirectoryItem headers.
        assert screen.sub_title == "sort: directory", (
            f"W8 requires directory sort mode -- got {screen.sub_title!r}"
        )

        # CSS id fragments and selector shortcuts.
        src_dir_id = _dir_to_id("src/")
        glyph_sel = f"#{src_dir_id} DirFoldGlyph"
        name_sel = f"#{src_dir_id} DirNameLabel"

        # Accessor helpers (public API + documented ID encodings only).
        def _dir_item() -> DiffDirectoryItem:
            return screen.query_one(f"#{src_dir_id}", DiffDirectoryItem)

        def _glyph() -> DirFoldGlyph:
            return screen.query_one(glyph_sel, DirFoldGlyph)

        def _file_item(path: str) -> DiffFileItem:
            return screen.query_one(f"#{_path_to_id(path)}", DiffFileItem)

        def _panel(path: str) -> FileDiffPanel:
            return screen.query_one(f"#panel-{_path_to_hex(path)}", FileDiffPanel)

        # ── State 0 (fold=F, hide=F): initial ─────────────────────────
        assert not _dir_item().has_class("dir-header--hidden"), (
            "src/ header must not carry dir-header--hidden at mount"
        )
        # [+] and [-] are not valid Rich markup tag starts (neither +
        # nor - is [a-zA-Z@]), so they render and are stored as literal
        # text. str(glyph.render()) returns the raw renderable string.
        assert str(_glyph().render()) == "[-]", (
            "glyph should be '[-]' (expanded) at mount"
        )
        for path in ("src/a.py", "src/b.py"):
            assert _file_item(path).display is True
            assert not _file_item(path).has_class("hidden-entry")
            assert _panel(path).display is True

        # ── Step 1: click [-] -> fold (fold=T, hide=F) ────────────────
        # Glyph click collapses sidebar file rows.
        # DiffView panels and header CSS class must be unaffected
        # (fold is orthogonal to hide -- only sidebar row display changes).
        await pilot.click(glyph_sel)
        await pilot.pause()

        assert str(_glyph().render()) == "[+]", (
            "glyph should be '[+]' (collapsed) after fold click"
        )
        assert not _dir_item().has_class("dir-header--hidden"), (
            "dir-header--hidden must not appear -- fold doesn't mute header"
        )
        for path in ("src/a.py", "src/b.py"):
            assert _file_item(path).display is False, (
                f"{path} sidebar row should be collapsed after fold click"
            )
            assert not _file_item(path).has_class("hidden-entry"), (
                f"{path} must not carry hidden-entry -- fold is orthogonal to hide"
            )
            assert _panel(path).display is True, (
                f"{path} DiffView panel must remain visible -- fold doesn't affect DiffView"
            )

        # ── Step 2: click name (not hidden) -> hide (fold=T, hide=T) ──
        # Name click triggers DiffDirectoryItem.HideToggled -> hide_prefix.
        # Fold state must be unchanged: glyph stays [+], row display stays
        # False (DiffSidebar.refresh_hide does NOT touch display).
        await pilot.click(name_sel)
        await pilot.pause()

        assert _dir_item().has_class("dir-header--hidden"), (
            "src/ header must carry dir-header--hidden after name click"
        )
        assert str(_glyph().render()) == "[+]", (
            "glyph must still be '[+]' -- name click doesn't change fold"
        )
        for path in ("src/a.py", "src/b.py"):
            assert _file_item(path).display is False, (
                f"{path} sidebar row display unchanged by name click (governed by fold)"
            )
            assert _file_item(path).has_class("hidden-entry"), (
                f"{path} must carry hidden-entry after directory hide"
            )
            assert _panel(path).display is False, (
                f"{path} DiffView panel must be hidden after directory hide"
            )

        # ── Step 3: click [+] -> unfold (fold=F, hide=T) ──────────────
        # Glyph click expands sidebar rows; they reappear as greyed
        # hidden-entry rows (still hidden, just no longer folded).
        # DiffView panels must remain hidden; header class unchanged.
        await pilot.click(glyph_sel)
        await pilot.pause()

        assert str(_glyph().render()) == "[-]", (
            "glyph should be '[-]' (expanded) after unfold click"
        )
        assert _dir_item().has_class("dir-header--hidden"), (
            "dir-header--hidden must remain -- unfold doesn't change hide"
        )
        for path in ("src/a.py", "src/b.py"):
            assert _file_item(path).display is True, (
                f"{path} sidebar row should be visible after unfold"
            )
            assert _file_item(path).has_class("hidden-entry"), (
                f"{path} must still carry hidden-entry -- unfold is orthogonal to hide"
            )
            assert _panel(path).display is False, (
                f"{path} DiffView panel must remain hidden -- unfold doesn't affect DiffView"
            )

        # ── Step 4: click name (hidden) -> unhide (fold=F, hide=F) ───
        # Name click with currently_hidden=True calls unhide_prefix.
        # DirNameLabel._hidden was set to True by set_hidden() in the
        # refresh_hide fan-out at step 2, so the label posts
        # HideToggled(currently_hidden=True) correctly.
        await pilot.click(name_sel)
        await pilot.pause()

        assert not _dir_item().has_class("dir-header--hidden"), (
            "dir-header--hidden must be removed after unhide"
        )
        assert str(_glyph().render()) == "[-]", (
            "glyph should be '[-]' (expanded) after unhide"
        )
        for path in ("src/a.py", "src/b.py"):
            assert _file_item(path).display is True
            assert not _file_item(path).has_class("hidden-entry"), (
                f"{path} must not carry hidden-entry after unhide"
            )
            assert _panel(path).display is True, (
                f"{path} DiffView panel must be visible after unhide"
            )

        # Sanity: tests/ and README.md were untouched by all four steps.
        assert _file_item("tests/x.py").display is True
        assert not _file_item("tests/x.py").has_class("hidden-entry")
        assert _panel("tests/x.py").display is True
        assert not _file_item("README.md").has_class("hidden-entry")
        assert _panel("README.md").display is True

        await _dismiss_diff(app, pilot)
