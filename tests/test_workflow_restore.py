"""Tests for workflow restore from chicsession.

Targets two bugs:
1. _restore_workflow_from_session() references undefined `wf_data` → NameError
2. _handle_restore() never calls _restore_workflow_from_session() → workflow lost
"""

from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml
from claudechic.app import ChatApp
from claudechic.chicsessions import Chicsession, ChicsessionEntry, ChicsessionManager

pytestmark = [pytest.mark.asyncio, pytest.mark.timeout(30)]


def _setup_workflow(root: Path) -> None:
    """Create a minimal workflow on disk."""
    (root / "global").mkdir(parents=True, exist_ok=True)
    wf_dir = root / "workflows" / "proj"
    wf_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "workflow_id": "proj",
        "main_role": "learner",
        "phases": [
            {"id": "design", "file": "design.md"},
            {"id": "implement", "file": "implement.md"},
        ],
    }
    (wf_dir / "proj.yaml").write_text(yaml.dump(manifest))


def _save_chicsession(
    root: Path, name: str, workflow_state: dict | None = None
) -> None:
    """Create a chicsession file on disk."""
    mgr = ChicsessionManager(root)
    cs = Chicsession(
        name=name,
        active_agent="main",
        agents=[ChicsessionEntry(name="main", session_id="fake-sid", cwd=str(root))],
        workflow_state=workflow_state,
    )
    mgr.save(cs)


async def _mock_prompt_chicsession_name(self, workflow_id: str) -> str | None:
    # Pre-existing tests don't exercise the restore-vs-fresh dialog.
    # _activate_workflow snapshots existing chicsessions BEFORE this runs,
    # so by setting _chicsession_name to a fresh value here (no file on
    # disk for it yet) the snapshot won't contain it -> dialog is skipped.
    self._chicsession_name = workflow_id
    return workflow_id


def _common_patches():
    """Return an ExitStack with the common patches applied."""
    stack = ExitStack()
    stack.enter_context(
        patch("claudechic.tasks.create_safe_task", return_value=MagicMock())
    )
    stack.enter_context(patch("claudechic.sessions.count_sessions", return_value=1))
    stack.enter_context(
        patch.object(ChatApp, "_prompt_chicsession_name", _mock_prompt_chicsession_name)
    )
    return stack


class TestRestoreWorkflowFromSession:
    """Bug #1: _restore_workflow_from_session references undefined wf_data."""

    async def test_restore_rebuilds_engine_from_chicsession(self, mock_sdk, tmp_path):
        """After activate + advance, saving state and calling _restore_workflow_from_session
        must rebuild the engine with correct phase. Fails if wf_data NameError."""
        _setup_workflow(tmp_path)
        app = ChatApp()

        with _common_patches():
            async with app.run_test(size=(120, 40), notifications=True) as pilot:
                await pilot.pause()

                app._cwd = tmp_path
                app._init_workflow_infrastructure(
                    global_dir=tmp_path / "global",
                    workflows_dir=tmp_path / "workflows",
                )
                app._discover_workflows()
                await app._activate_workflow("proj")
                await pilot.pause()

                engine = app._workflow_engine
                assert engine is not None

                # Advance to implement phase
                await engine.attempt_phase_advance(
                    "proj", "proj:design", "proj:implement", []
                )
                assert engine.get_current_phase() == "proj:implement"

                # Save workflow state to chicsession on disk
                _save_chicsession(
                    tmp_path,
                    app._chicsession_name,
                    workflow_state=engine.to_session_state(),
                )

                # Nuke the engine to simulate fresh resume
                app._workflow_engine = None

                # This is the method under test — must not raise NameError
                app._restore_workflow_from_session()

                # Engine should be restored at implement phase
                assert app._workflow_engine is not None, (
                    "_restore_workflow_from_session did not rebuild the engine"
                )
                assert app._workflow_engine.get_current_phase() == "proj:implement"
                assert app._workflow_engine.workflow_id == "proj"

    async def test_restore_no_op_without_chicsession(self, mock_sdk, tmp_path):
        """No chicsession name → early return, no crash."""
        _setup_workflow(tmp_path)
        app = ChatApp()

        with _common_patches():
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()

                app._cwd = tmp_path
                app._chicsession_name = None
                app._restore_workflow_from_session()
                assert app._workflow_engine is None


class TestHandleRestoreCallsWorkflowRestore:
    """Bug #2: _handle_restore() loads chicsession but never restores workflow."""

    async def test_handle_restore_restores_workflow_engine(self, mock_sdk, tmp_path):
        """After _handle_restore, the workflow engine must be rebuilt
        from the saved workflow_state in the chicsession."""
        _setup_workflow(tmp_path)
        app = ChatApp()

        with _common_patches():
            async with app.run_test(size=(120, 40), notifications=True) as pilot:
                await pilot.pause()

                app._cwd = tmp_path
                app._init_workflow_infrastructure(
                    global_dir=tmp_path / "global",
                    workflows_dir=tmp_path / "workflows",
                )
                app._discover_workflows()

                # Activate workflow, advance phase, save chicsession
                await app._activate_workflow("proj")
                await pilot.pause()

                engine = app._workflow_engine
                assert engine is not None

                await engine.attempt_phase_advance(
                    "proj", "proj:design", "proj:implement", []
                )

                # Save chicsession with workflow state
                _save_chicsession(
                    tmp_path,
                    app._chicsession_name,
                    workflow_state=engine.to_session_state(),
                )

                session_name = app._chicsession_name

                # Reset app state to simulate fresh start
                app._workflow_engine = None
                app._chicsession_name = None

                # Run _handle_restore
                from claudechic.chicsession_cmd import _handle_restore

                await _handle_restore(app, session_name)
                await pilot.pause()

                # After restore, workflow engine should be rebuilt
                assert app._workflow_engine is not None, (
                    "_handle_restore did not call _restore_workflow_from_session -- "
                    "workflow engine is None after restoring a chicsession with workflow_state"
                )
                assert app._workflow_engine.get_current_phase() == "proj:implement"


class TestRestoreSessionSidebarDisplay:
    """Issue #9: sidebar must show workflow/phase after session restore."""

    async def test_restore_session_shows_workflow_and_phase(self, mock_sdk, tmp_path):
        """After restoring a chicsession with workflow_state, the sidebar
        ChicsessionLabel must display workflow name and phase."""
        _setup_workflow(tmp_path)
        app = ChatApp()

        with _common_patches():
            async with app.run_test(size=(120, 40), notifications=True) as pilot:
                await pilot.pause()

                app._cwd = tmp_path
                app._init_workflow_infrastructure(
                    global_dir=tmp_path / "global",
                    workflows_dir=tmp_path / "workflows",
                )
                app._discover_workflows()

                # Activate workflow, advance phase, save chicsession
                await app._activate_workflow("proj")
                await pilot.pause()

                engine = app._workflow_engine
                assert engine is not None

                await engine.attempt_phase_advance(
                    "proj", "proj:design", "proj:implement", []
                )

                # Save chicsession with workflow state
                _save_chicsession(
                    tmp_path,
                    app._chicsession_name,
                    workflow_state=engine.to_session_state(),
                )

                session_name = app._chicsession_name

                # Reset app state to simulate fresh start
                app._workflow_engine = None
                app._chicsession_name = None

                # Clear sidebar labels to verify they get repopulated
                from claudechic.widgets.layout.sidebar import ChicsessionLabel

                label = app.query_one("#chicsession-label", ChicsessionLabel)
                label.workflow_text = ""
                label.phase_text = ""
                await pilot.pause()

                # Run _handle_restore (restores engine + should update sidebar)
                from claudechic.chicsession_cmd import _handle_restore

                await _handle_restore(app, session_name)
                await pilot.pause()

                # Verify sidebar label shows workflow and phase
                assert label.workflow_text == "proj", (
                    f"Expected workflow_text='proj', got '{label.workflow_text}'"
                )
                assert label.phase_text == "implement", (
                    f"Expected phase_text='implement', got '{label.phase_text}'"
                )

                # Verify the Static widgets are visible (display != none)
                wf_static = label.query_one(".chicsession-workflow")
                phase_static = label.query_one(".chicsession-phase")
                assert wf_static.display is not False
                assert phase_static.display is not False

    async def test_restore_with_missing_workflow_state(self, mock_sdk, tmp_path):
        """Restoring a chicsession WITHOUT workflow_state must not crash
        and must leave workflow/phase labels empty."""
        _setup_workflow(tmp_path)
        app = ChatApp()

        with _common_patches():
            async with app.run_test(size=(120, 40), notifications=True) as pilot:
                await pilot.pause()

                app._cwd = tmp_path
                app._init_workflow_infrastructure(
                    global_dir=tmp_path / "global",
                    workflows_dir=tmp_path / "workflows",
                )
                app._discover_workflows()

                # Activate workflow so agents exist, then save WITHOUT workflow_state
                await app._activate_workflow("proj")
                await pilot.pause()

                _save_chicsession(tmp_path, app._chicsession_name, workflow_state=None)
                session_name = app._chicsession_name

                # Reset app state to simulate fresh start
                app._workflow_engine = None
                app._chicsession_name = None

                # Run _handle_restore -- must not crash
                from claudechic.chicsession_cmd import _handle_restore

                await _handle_restore(app, session_name)
                await pilot.pause()

                # Verify no crash and empty labels
                from claudechic.widgets.layout.sidebar import ChicsessionLabel

                label = app.query_one("#chicsession-label", ChicsessionLabel)
                assert label.workflow_text == "", (
                    f"Expected empty workflow_text, got '{label.workflow_text}'"
                )
                assert label.phase_text == "", (
                    f"Expected empty phase_text, got '{label.phase_text}'"
                )


class TestFilesSectionAfterRestore:
    """FilesSection must become visible after restore when uncommitted changes exist.

    Root cause: _position_right_sidebar() evaluates has_content which does NOT include
    files_section.item_count. So a single-agent session with no workflow and no worktrees
    keeps the sidebar hidden even after _async_refresh_files populates FilesSection.

    Two coupled failures:
    1. has_content ignores file changes -- _position_right_sidebar never shows sidebar
       for single-agent sessions based on file changes alone.
    2. _async_refresh_files never re-calls _position_right_sidebar after mounting files,
       so even if has_content were fixed, the sidebar wouldn't re-evaluate.
    """

    async def test_sidebar_stays_hidden_when_files_added_single_agent(
        self, mock_sdk, tmp_path
    ):
        """With 1 agent, no workflow, and no worktrees, adding files to FilesSection
        does not make the sidebar visible -- _position_right_sidebar ignores files.

        This FAILS because has_content does not include files_section.item_count.
        Fix: add `or self.files_section.item_count > 0` to has_content in
        _position_right_sidebar.
        """
        from pathlib import Path
        from unittest.mock import patch

        from claudechic.widgets.layout.sidebar import FilesSection

        app = ChatApp()
        with _common_patches():
            # Suppress create_safe_task (correct location: claudechic.app, not
            # claudechic.tasks, since app.py uses a module-level import)
            with patch("claudechic.app.create_safe_task"):
                async with app.run_test(size=(120, 40)) as pilot:
                    await pilot.pause()

                    # Force controlled state: no worktrees, no workflow, no todos
                    app.agent_section._worktrees.clear()
                    app._workflow_engine = None

                    # Verify precondition: sidebar IS hidden (has_content = False)
                    app._position_right_sidebar()
                    await pilot.pause()
                    sidebar = app.query_one("#right-sidebar")
                    assert sidebar.has_class("hidden"), (
                        "Precondition: sidebar must be hidden with 1 agent, "
                        "no workflow, no worktrees, no todos"
                    )

                    # Simulate what _async_refresh_files does when it finds changed files
                    app.files_section.add_file(Path("README.md"), 5, 2)
                    app.files_section.add_file(Path("src/main.py"), 10, 0)
                    await pilot.pause()

                    # FilesSection self-manages visibility -- it IS now visible
                    files_section = app.query_one("#files-section", FilesSection)
                    assert not files_section.has_class("hidden"), (
                        "FilesSection should show itself when it has items"
                    )
                    assert files_section.item_count == 2

                    # Call _position_right_sidebar (what should happen after files load)
                    app._position_right_sidebar()
                    await pilot.pause()

                    # FAILS: sidebar is still hidden because has_content does not
                    # include files_section.item_count. FilesSection is visible inside
                    # a hidden sidebar -- the user sees nothing.
                    assert not sidebar.has_class("hidden"), (
                        "Sidebar must be visible when FilesSection has file items. "
                        "Bug: has_content in _position_right_sidebar ignores "
                        "files_section.item_count. "
                        "Fix: add `or self.files_section.item_count > 0` to has_content."
                    )

    async def test_async_refresh_files_does_not_recheck_sidebar_visibility(
        self, mock_sdk, tmp_path
    ):
        """Even with has_content fixed, _async_refresh_files never calls
        _position_right_sidebar() after mounting files -- sidebar stays hidden.

        This FAILS because _async_refresh_files calls mount_all_files() but
        does not call self._position_right_sidebar() afterward.
        Fix: call self._position_right_sidebar() at end of _async_refresh_files
        when stats are non-empty.
        """
        from unittest.mock import AsyncMock, patch

        from claudechic.features.diff.git import FileStat
        from claudechic.widgets.layout.sidebar import FilesSection

        fake_stats = [
            FileStat(path="README.md", additions=5, deletions=2),
            FileStat(path="src/main.py", additions=10, deletions=0),
        ]

        app = ChatApp()
        with _common_patches():
            # Suppress background tasks at the correct import location
            with patch("claudechic.app.create_safe_task"):
                with patch(
                    "claudechic.features.diff.get_file_stats",
                    new=AsyncMock(return_value=fake_stats),
                ):
                    async with app.run_test(size=(120, 40)) as pilot:
                        await pilot.pause()

                        # Force controlled state: no worktrees, no workflow
                        app.agent_section._worktrees.clear()
                        app._workflow_engine = None

                        # Verify precondition: sidebar is hidden
                        app._position_right_sidebar()
                        await pilot.pause()
                        sidebar = app.query_one("#right-sidebar")
                        assert sidebar.has_class("hidden"), (
                            "Precondition: sidebar must start hidden"
                        )

                        # Run _async_refresh_files directly -- this is what
                        # create_safe_task would schedule after on_agent_switched
                        active = app.agent_mgr.active
                        assert active is not None
                        await app._async_refresh_files(active)
                        await pilot.pause()

                        # FilesSection now has items
                        files_section = app.query_one("#files-section", FilesSection)
                        assert files_section.item_count == 2, (
                            f"Expected 2 file items, got {files_section.item_count}. "
                            "Check that get_file_stats is patched correctly."
                        )

                        # FAILS: sidebar is still hidden.
                        # _async_refresh_files mounts files but never calls
                        # _position_right_sidebar() to re-evaluate sidebar visibility.
                        assert not sidebar.has_class("hidden"), (
                            "Sidebar must be visible after _async_refresh_files adds files. "
                            "Bug: _async_refresh_files does not call _position_right_sidebar(). "
                            "Fix: call self._position_right_sidebar() at the end of "
                            "_async_refresh_files when stats are non-empty."
                        )

    async def test_real_git_repo_files_section_becomes_visible(
        self, mock_sdk, tmp_path, monkeypatch
    ):
        """End-to-end: real git repo with uncommitted changes -- FilesSection must appear.

        Creates an actual git repo, makes a real uncommitted change, starts the app,
        and calls _async_refresh_files directly (deterministic, no create_safe_task
        timing dependency). Verifies the full chain:
          git diff -> get_file_stats -> mount_all_files -> remove_class("hidden")
          -> _position_right_sidebar -> sidebar visible

        This test uses real git subprocess calls (no mocked get_file_stats) to catch
        bugs in the integration between get_file_stats and the UI update chain.
        """
        import subprocess

        from claudechic.widgets.layout.sidebar import FilesSection

        # 1. Create a real git repo with an initial commit
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        readme = tmp_path / "README.md"
        readme.write_text("initial content\n", encoding="utf-8")
        subprocess.run(
            ["git", "add", "."], cwd=tmp_path, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )

        # 2. Make an uncommitted change (now `git diff HEAD --numstat` returns a result)
        readme.write_text("initial content\nmore lines added\n", encoding="utf-8")

        # 3. Start app with tmp_path as cwd
        monkeypatch.chdir(tmp_path)

        app = ChatApp()
        with _common_patches():
            # Suppress automatic background tasks so we control timing
            with patch("claudechic.app.create_safe_task"):
                async with app.run_test(size=(120, 40)) as pilot:
                    await pilot.pause()

                    # Confirm agent points at our git repo
                    active = app.agent_mgr.active
                    assert active is not None, "No active agent after startup"
                    assert Path(active.cwd) == tmp_path, (
                        f"Agent cwd mismatch: expected {tmp_path}, got {active.cwd}"
                    )

                    # Confirm sidebar starts hidden (single agent, no workflow)
                    sidebar = app.query_one("#right-sidebar")
                    app.agent_section._worktrees.clear()
                    app._workflow_engine = None
                    app._position_right_sidebar()
                    await pilot.pause()
                    assert sidebar.has_class("hidden"), (
                        "Precondition: sidebar must be hidden before files load"
                    )

                    # 4. Run file refresh -- this is what create_safe_task would schedule
                    await app._async_refresh_files(active)
                    await pilot.pause()

                    # 5. Inspect actual DOM state
                    files_section = app.query_one("#files-section", FilesSection)
                    files_hidden = files_section.has_class("hidden")
                    files_count = files_section.item_count
                    files_dict = list(files_section._files.keys())
                    sidebar_hidden = sidebar.has_class("hidden")

                    # FilesSection must have found our changed file
                    assert files_count > 0, (
                        f"FilesSection._files is empty after _async_refresh_files.\n"
                        f"  git repo: {tmp_path}\n"
                        f"  agent.cwd: {active.cwd}\n"
                        f"  FilesSection._files keys: {files_dict}\n"
                        f"  FilesSection.has_class('hidden'): {files_hidden}\n"
                        "Possible causes: get_file_stats returned empty (git command "
                        "failed), or mount_all_files was not called."
                    )

                    # FilesSection must not be hidden
                    assert not files_hidden, (
                        f"FilesSection has items ({files_count}) but is still hidden.\n"
                        f"  mount_all_files should call remove_class('hidden')."
                    )

                    # Sidebar must be visible (our Fix 1 + Fix 2)
                    assert not sidebar_hidden, (
                        f"Sidebar is still hidden after _async_refresh_files.\n"
                        f"  files_section.item_count={files_count}\n"
                        f"  files_section hidden={files_hidden}\n"
                        f"  sidebar classes={list(sidebar.classes)}\n"
                        "Check: does _async_refresh_files call _position_right_sidebar()?\n"
                        "Check: does _position_right_sidebar include files_section.item_count?"
                    )


class TestPromptWorkflowRestoreOrFresh:
    """The restore/fresh/cancel dialog helper: shape and return values."""

    @staticmethod
    def _common_app_setup(tmp_path):
        """Build the common ExitStack: silenced background tasks etc."""
        stack = ExitStack()
        stack.enter_context(
            patch("claudechic.tasks.create_safe_task", return_value=MagicMock())
        )
        stack.enter_context(patch("claudechic.sessions.count_sessions", return_value=1))
        return stack

    async def test_restore_choice_returns_restore(self, mock_sdk, tmp_path):
        """Same-workflow prior state + 'restore' choice -> returns 'restore'."""
        _setup_workflow(tmp_path)
        _save_chicsession(
            tmp_path,
            "saved",
            workflow_state={
                "workflow_id": "proj",
                "current_phase": "proj:implement",
            },
        )

        app = ChatApp()
        with self._common_app_setup(tmp_path):
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                app._cwd = tmp_path
                with patch.object(
                    app,
                    "_show_agent_prompt",
                    new=AsyncMock(return_value="restore"),
                ) as dialog:
                    result = await app._prompt_workflow_restore_or_fresh(
                        "proj", "saved"
                    )

                assert result == "restore"
                # Dialog must have been shown with all three options.
                opts = dialog.await_args.kwargs["options"]
                values = [v for v, _ in opts]
                assert values == ["restore", "fresh", "cancel"]

    async def test_fresh_choice_returns_fresh(self, mock_sdk, tmp_path):
        """Same-workflow prior state + 'fresh' choice -> returns 'fresh'."""
        _setup_workflow(tmp_path)
        _save_chicsession(
            tmp_path,
            "saved",
            workflow_state={
                "workflow_id": "proj",
                "current_phase": "proj:implement",
            },
        )

        app = ChatApp()
        with self._common_app_setup(tmp_path):
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                app._cwd = tmp_path
                with patch.object(
                    app,
                    "_show_agent_prompt",
                    new=AsyncMock(return_value="fresh"),
                ):
                    result = await app._prompt_workflow_restore_or_fresh(
                        "proj", "saved"
                    )

                assert result == "fresh"

    async def test_cancel_choice_returns_none(self, mock_sdk, tmp_path):
        """User picks 'cancel' -> returns None to signal abort."""
        _setup_workflow(tmp_path)
        _save_chicsession(
            tmp_path,
            "saved",
            workflow_state={
                "workflow_id": "proj",
                "current_phase": "proj:implement",
            },
        )

        app = ChatApp()
        with self._common_app_setup(tmp_path):
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                app._cwd = tmp_path
                with patch.object(
                    app,
                    "_show_agent_prompt",
                    new=AsyncMock(return_value="cancel"),
                ):
                    result = await app._prompt_workflow_restore_or_fresh(
                        "proj", "saved"
                    )

                assert result is None

    async def test_escape_returns_none(self, mock_sdk, tmp_path):
        """SelectionPrompt returns '' on Escape -> treat as cancel (None)."""
        _setup_workflow(tmp_path)
        _save_chicsession(
            tmp_path,
            "saved",
            workflow_state={
                "workflow_id": "proj",
                "current_phase": "proj:implement",
            },
        )

        app = ChatApp()
        with self._common_app_setup(tmp_path):
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                app._cwd = tmp_path
                with patch.object(
                    app, "_show_agent_prompt", new=AsyncMock(return_value="")
                ):
                    result = await app._prompt_workflow_restore_or_fresh(
                        "proj", "saved"
                    )

                assert result is None

    async def test_dialog_always_offers_three_options(self, mock_sdk, tmp_path):
        """Dialog always presents restore / fresh / cancel for existing
        chicsessions -- regardless of what is on disk.  The user, not
        stored state, decides the action.
        """
        _setup_workflow(tmp_path)
        _save_chicsession(tmp_path, "anything", workflow_state=None)

        app = ChatApp()
        with self._common_app_setup(tmp_path):
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                app._cwd = tmp_path
                with patch.object(
                    app,
                    "_show_agent_prompt",
                    new=AsyncMock(return_value="fresh"),
                ) as dialog:
                    result = await app._prompt_workflow_restore_or_fresh(
                        "proj", "anything"
                    )

                assert dialog.await_count == 1
                opts = dialog.await_args.kwargs["options"]
                values = [v for v, _ in opts]
                # Always three options, in this order.
                assert values == ["restore", "fresh", "cancel"]
                assert result == "fresh"

    async def test_dialog_does_not_read_chicsession_from_disk(self, mock_sdk, tmp_path):
        """Helper does not load the chicsession to decide what to show --
        a missing chicsession on disk is fine, the dialog still appears.
        """
        _setup_workflow(tmp_path)
        # Deliberately NOT saving any chicsession -- file does not exist.

        app = ChatApp()
        with self._common_app_setup(tmp_path):
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                app._cwd = tmp_path
                with patch.object(
                    app,
                    "_show_agent_prompt",
                    new=AsyncMock(return_value="restore"),
                ) as dialog:
                    result = await app._prompt_workflow_restore_or_fresh(
                        "proj", "does-not-exist"
                    )

                # Dialog ran (no disk inspection short-circuited it).
                assert dialog.await_count == 1
                assert result == "restore"


class TestActivateWorkflowRestorePath:
    """_activate_workflow must consult _prompt_workflow_restore_or_fresh
    and rebuild the engine from saved state when the user picks 'restore'
    -- both when the chicsession is selected via the picker (case B) AND
    when the chicsession was already attached at activation time (case A).
    """

    @staticmethod
    def _common_patches(decision_value):
        """Build the common patches: silenced background tasks plus a
        mocked _prompt_workflow_restore_or_fresh that returns
        `decision_value` ("restore", "fresh", or None for cancel).
        """
        stack = ExitStack()
        stack.enter_context(
            patch("claudechic.tasks.create_safe_task", return_value=MagicMock())
        )
        stack.enter_context(patch("claudechic.sessions.count_sessions", return_value=1))
        stack.enter_context(
            patch.object(
                ChatApp,
                "_prompt_workflow_restore_or_fresh",
                new=AsyncMock(return_value=decision_value),
            )
        )
        return stack

    async def test_restore_choice_rebuilds_engine_at_saved_phase_via_picker(
        self, mock_sdk, tmp_path
    ):
        """Case B: user picks chicsession via picker, then 'restore' in dialog.
        Engine must resume at the saved phase, not start at first phase.
        """
        _setup_workflow(tmp_path)
        _save_chicsession(
            tmp_path,
            "resumed",
            workflow_state={
                "workflow_id": "proj",
                "current_phase": "proj:implement",
            },
        )

        async def mock_picker(self, workflow_id):
            self._chicsession_name = "resumed"
            return "resumed"

        app = ChatApp()
        with self._common_patches("restore") as common:
            common.enter_context(
                patch.object(ChatApp, "_prompt_chicsession_name", mock_picker)
            )
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                app._cwd = tmp_path
                app._init_workflow_infrastructure(
                    global_dir=tmp_path / "global",
                    workflows_dir=tmp_path / "workflows",
                )
                app._discover_workflows()

                await app._activate_workflow("proj")
                await pilot.pause()

                assert app._workflow_engine is not None
                assert app._workflow_engine.get_current_phase() == "proj:implement", (
                    "Restore path must rebuild engine at saved phase, "
                    "not start at the first phase."
                )

    async def test_restore_choice_works_when_chicsession_already_attached(
        self, mock_sdk, tmp_path
    ):
        """Case A: chicsession already attached when /workflow invoked,
        user picks 'restore' in dialog -> engine restores at saved phase.
        Without the dialog the prior default would have silently overwritten
        the saved state with a fresh engine.
        """
        _setup_workflow(tmp_path)
        _save_chicsession(
            tmp_path,
            "preset",
            workflow_state={
                "workflow_id": "proj",
                "current_phase": "proj:implement",
            },
        )

        app = ChatApp()
        with self._common_patches("restore"):
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                app._cwd = tmp_path
                app._init_workflow_infrastructure(
                    global_dir=tmp_path / "global",
                    workflows_dir=tmp_path / "workflows",
                )
                app._discover_workflows()
                # Simulate "user already attached to chicsession" before
                # /workflow was invoked.
                app._chicsession_name = "preset"

                await app._activate_workflow("proj")
                await pilot.pause()

                assert app._workflow_engine is not None
                assert app._workflow_engine.get_current_phase() == "proj:implement"

    async def test_fresh_choice_starts_engine_at_first_phase(self, mock_sdk, tmp_path):
        """User picks 'fresh' -> engine starts at first phase, ignoring saved state."""
        _setup_workflow(tmp_path)
        _save_chicsession(
            tmp_path,
            "ignored",
            workflow_state={
                "workflow_id": "proj",
                "current_phase": "proj:implement",
            },
        )

        async def mock_picker(self, workflow_id):
            self._chicsession_name = "ignored"
            return "ignored"

        app = ChatApp()
        with self._common_patches("fresh") as common:
            common.enter_context(
                patch.object(ChatApp, "_prompt_chicsession_name", mock_picker)
            )
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                app._cwd = tmp_path
                app._init_workflow_infrastructure(
                    global_dir=tmp_path / "global",
                    workflows_dir=tmp_path / "workflows",
                )
                app._discover_workflows()

                await app._activate_workflow("proj")
                await pilot.pause()

                assert app._workflow_engine is not None
                assert app._workflow_engine.get_current_phase() == "proj:design"

    async def test_cancel_choice_aborts_activation(self, mock_sdk, tmp_path):
        """User picks 'cancel' -> no engine created, activation aborts."""
        _setup_workflow(tmp_path)
        _save_chicsession(
            tmp_path,
            "saved",
            workflow_state={
                "workflow_id": "proj",
                "current_phase": "proj:implement",
            },
        )

        async def mock_picker(self, workflow_id):
            self._chicsession_name = "saved"
            return "saved"

        app = ChatApp()
        # decision_value=None signals cancel.
        with self._common_patches(None) as common:
            common.enter_context(
                patch.object(ChatApp, "_prompt_chicsession_name", mock_picker)
            )
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                app._cwd = tmp_path
                app._init_workflow_infrastructure(
                    global_dir=tmp_path / "global",
                    workflows_dir=tmp_path / "workflows",
                )
                app._discover_workflows()

                await app._activate_workflow("proj")
                await pilot.pause()

                # Cancellation aborts -- no engine should exist.
                assert app._workflow_engine is None

    async def test_dialog_shown_for_existing_session_without_prior_state(
        self, mock_sdk, tmp_path
    ):
        """Regression: user clicks /workflow -> project_team -> existing
        chicsession with no prior workflow_state -> dialog MUST appear.

        The decision is purely "did the chicsession file exist on disk
        before activation?"  -- not "is there workflow state inside?"
        """
        _setup_workflow(tmp_path)
        # Existing chicsession on disk with NO prior workflow_state -- the
        # most common case: user activated a workflow once but never advanced
        # phases, so persist_fn never fired.
        _save_chicsession(tmp_path, "existing", workflow_state=None)

        async def mock_picker(self, workflow_id):
            # Picker resumed an existing chicsession -- file already on disk.
            self._chicsession_name = "existing"
            return "existing"

        dialog = AsyncMock(return_value="fresh")

        app = ChatApp()
        with ExitStack() as common:
            common.enter_context(
                patch("claudechic.tasks.create_safe_task", return_value=MagicMock())
            )
            common.enter_context(
                patch("claudechic.sessions.count_sessions", return_value=1)
            )
            common.enter_context(
                patch.object(ChatApp, "_prompt_chicsession_name", mock_picker)
            )
            common.enter_context(
                patch.object(ChatApp, "_show_agent_prompt", new=dialog)
            )
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                app._cwd = tmp_path
                app._init_workflow_infrastructure(
                    global_dir=tmp_path / "global",
                    workflows_dir=tmp_path / "workflows",
                )
                app._discover_workflows()

                await app._activate_workflow("proj")
                await pilot.pause()

                # Dialog MUST have been shown (this is the bug fix).
                assert dialog.await_count == 1, (
                    "Dialog must appear when user picks an existing chicsession, "
                    "even when that chicsession has no prior workflow_state."
                )

    async def test_dialog_skipped_for_newly_created_chicsession(
        self, mock_sdk, tmp_path
    ):
        """No dialog when the user picked 'new:<name>' in the picker --
        the chicsession file did not exist before activation, so there is
        nothing to preserve.
        """
        _setup_workflow(tmp_path)
        # NOTE: NOT calling _save_chicsession -- "brand-new" is not on disk.

        async def mock_picker(self, workflow_id):
            # Simulate the "new:" path: just sets the name (the real new
            # path also writes the file, but here we want to verify that
            # _activate_workflow's "did this exist before?" snapshot is
            # the thing controlling the dialog -- not the post-picker
            # state).  The activation snapshot was taken before mock_picker
            # ran, so "brand-new" was NOT in it.
            self._chicsession_name = "brand-new"
            return "brand-new"

        dialog = AsyncMock(return_value="fresh")

        app = ChatApp()
        with ExitStack() as common:
            common.enter_context(
                patch("claudechic.tasks.create_safe_task", return_value=MagicMock())
            )
            common.enter_context(
                patch("claudechic.sessions.count_sessions", return_value=1)
            )
            common.enter_context(
                patch.object(ChatApp, "_prompt_chicsession_name", mock_picker)
            )
            common.enter_context(
                patch.object(ChatApp, "_show_agent_prompt", new=dialog)
            )
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                app._cwd = tmp_path
                app._init_workflow_infrastructure(
                    global_dir=tmp_path / "global",
                    workflows_dir=tmp_path / "workflows",
                )
                app._discover_workflows()

                await app._activate_workflow("proj")
                await pilot.pause()

                # No dialog for brand-new chicsession (file didn't exist
                # before activation).
                assert dialog.await_count == 0
                # Engine should be created fresh.
                assert app._workflow_engine is not None
                assert app._workflow_engine.get_current_phase() == "proj:design"
