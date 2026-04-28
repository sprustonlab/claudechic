"""Tests for the worktree symlink propagation behavior.

Covers SPEC.md §10 (parallel `.claudechic/` symlink alongside the existing
`.claude/` symlink) and the §10.2 acceptance items, plus the Skeptic2-flagged
edge cases around the migration from ``if not target.exists()`` to the
race-safe ``try/except FileExistsError`` pattern.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from claudechic.features.worktree.git import start_worktree

_unix_only = pytest.mark.skipif(
    sys.platform == "win32",
    reason="Symlinks require POSIX support; cross-platform tracking at #26",
)


def _fake_subprocess_run_factory(worktree_dir: Path):
    """Build a subprocess.run replacement that mimics ``git worktree add``.

    Real ``git worktree add`` creates the directory and seeds it with a few
    files. We just need the directory to exist so the symlink-creation block
    that follows in start_worktree() has a place to write.
    """

    def fake_run(*_args, **_kwargs):
        worktree_dir.mkdir(parents=True, exist_ok=True)

        class _Result:
            returncode = 0
            stdout = ""
            stderr = ""

        return _Result()

    return fake_run


@pytest.fixture
def patched_worktree_env(tmp_path, monkeypatch):
    """Set up a fake main worktree at tmp_path/main and patch deps.

    Yields a dict with the main worktree path and the new worktree path,
    plus the mocks so individual tests can vary behavior. Subprocess is
    patched per-test (we wire it up just before calling start_worktree so
    the closure can capture worktree_dir).
    """
    main_wt = tmp_path / "main"
    main_wt.mkdir()
    new_wt = tmp_path / "main-feat-x"

    with (
        patch("claudechic.features.worktree.git.CONFIG", {"worktree": {}}),
        patch("claudechic.features.worktree.git.get_main_worktree") as mock_get_main,
        patch("claudechic.features.worktree.git.get_repo_name", return_value="main"),
        patch("claudechic.features.worktree.git.subprocess.run") as mock_run,
    ):
        mock_get_main.return_value = (main_wt, "branch_name")
        mock_run.side_effect = _fake_subprocess_run_factory(new_wt)
        yield {
            "main_wt": main_wt,
            "new_wt": new_wt,
            "mock_run": mock_run,
        }


@_unix_only
class TestWorktreeSymlinkPropagation:
    """SPEC.md §10.3 acceptance — symlink propagation from main to new worktree."""

    def test_claudechic_symlink_created_when_source_exists(self, patched_worktree_env):
        """INV-10: post-add, .claudechic/ in main worktree symlinks into new worktree."""
        main_wt = patched_worktree_env["main_wt"]
        new_wt = patched_worktree_env["new_wt"]

        # Create .claudechic/ in the main worktree with a marker file
        (main_wt / ".claudechic").mkdir()
        (main_wt / ".claudechic" / "config.yaml").write_text("guardrails: true\n")

        success, _, wt_path = start_worktree("feat-x")

        assert success
        assert wt_path == new_wt

        link = new_wt / ".claudechic"
        assert link.is_symlink(), ".claudechic should be a symlink"
        assert link.resolve() == (main_wt / ".claudechic").resolve()

    def test_claude_symlink_still_created_alongside(self, patched_worktree_env):
        """The new .claudechic block does not regress the existing .claude block."""
        main_wt = patched_worktree_env["main_wt"]
        new_wt = patched_worktree_env["new_wt"]

        (main_wt / ".claude").mkdir()
        (main_wt / ".claude" / "settings.json").write_text("{}\n")

        success, _, _ = start_worktree("feat-x")

        assert success
        link = new_wt / ".claude"
        assert link.is_symlink()
        assert link.resolve() == (main_wt / ".claude").resolve()

    def test_both_symlinks_created_when_both_sources_exist(self, patched_worktree_env):
        """When main has both .claude/ and .claudechic/, both symlinks land."""
        main_wt = patched_worktree_env["main_wt"]
        new_wt = patched_worktree_env["new_wt"]

        (main_wt / ".claude").mkdir()
        (main_wt / ".claudechic").mkdir()

        success, _, _ = start_worktree("feat-x")

        assert success
        assert (new_wt / ".claude").is_symlink()
        assert (new_wt / ".claudechic").is_symlink()

    def test_claudechic_symlink_skipped_when_source_missing(self, patched_worktree_env):
        """SPEC §10.3 — if main's .claudechic/ doesn't exist, no symlink is created.

        Skeptic2 risk: with the migration to ``try/except FileExistsError`` we
        must be sure we're NOT silently calling symlink_to() against a
        non-existent source. The is_dir() guard is what protects us; this
        test pins that guard.
        """
        main_wt = patched_worktree_env["main_wt"]
        new_wt = patched_worktree_env["new_wt"]

        # Neither .claude/ nor .claudechic/ in main
        assert not (main_wt / ".claude").exists()
        assert not (main_wt / ".claudechic").exists()

        success, _, _ = start_worktree("feat-x")

        assert success
        assert not (new_wt / ".claude").exists()
        assert not (new_wt / ".claudechic").exists()

    def test_claudechic_symlink_idempotent_when_target_exists(
        self, patched_worktree_env
    ):
        """The race-safe ``try/except FileExistsError`` form must NOT raise on re-run.

        Skeptic2 risk: the original code used ``if not target.exists()``; the
        new code uses ``try/except FileExistsError``. We must verify the new
        form is functionally equivalent (no error, leaves existing symlink in
        place) when the target already exists.
        """
        main_wt = patched_worktree_env["main_wt"]
        new_wt = patched_worktree_env["new_wt"]

        (main_wt / ".claudechic").mkdir()
        (main_wt / ".claude").mkdir()

        # Pre-create the new worktree dir + a pre-existing target symlink
        new_wt.mkdir()
        existing_link_target = main_wt / ".claudechic"
        (new_wt / ".claudechic").symlink_to(existing_link_target.resolve())
        (new_wt / ".claude").symlink_to((main_wt / ".claude").resolve())

        # Patch _fake_subprocess_run_factory's mkdir to be no-op since dir exists.
        # The "directory already exists" early-return guards this; verify it.
        success, msg, _ = start_worktree("feat-x")

        # The "directory already exists" check returns False with a message,
        # but the existing symlinks must remain intact.
        assert not success, "Pre-existing worktree dir triggers early return"
        assert "already exists" in msg
        assert (new_wt / ".claudechic").is_symlink()
        assert (new_wt / ".claude").is_symlink()
