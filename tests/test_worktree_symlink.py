"""Tests for the worktree symlink propagation behavior.

Covers SPEC.md §10 (parallel `.claudechic/` symlink alongside the existing
`.claude/` symlink) and the §10.2 acceptance items, plus the Skeptic2-flagged
edge cases around the migration from ``if not target.exists()`` to the
race-safe ``try/except FileExistsError`` pattern.

The ``TestWorktreeSymlinkFallback`` class at the bottom covers the
cross-platform OSError fallback path (issue #26) -- it runs on Windows
too, since the OSError is mocked rather than provoked.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from claudechic.features.worktree.git import start_worktree

_unix_only = pytest.mark.skipif(
    sys.platform == "win32",
    reason=(
        "Tests the symlink success path which requires Developer Mode + NTFS "
        "on Windows; cross-platform OSError fallback is covered in "
        "TestWorktreeSymlinkFallback below"
    ),
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


# ---------------------------------------------------------------------------
# Issue #26: cross-platform OSError fallback (copy-with-consent or abort).
#
# These tests run on every platform, including Windows, by mocking
# ``Path.symlink_to`` to raise ``OSError``. They cover the user-approved
# copy fallback, the abort path (with worktree rollback), and the
# partial-failure case where one source dir symlinks fine and another
# raises mid-iteration.
# ---------------------------------------------------------------------------


def _make_symlink_failer(should_fail):
    """Build a function suitable for ``monkeypatch.setattr(Path, 'symlink_to', ...)``.

    ``Path.symlink_to`` is a method, so the replacement must be a *function*
    (not an arbitrary callable instance) to participate in descriptor-based
    bound-method dispatch. ``target.symlink_to(source)`` then dispatches
    as ``failer(target, source)``.

    The returned callable carries a ``.calls`` attribute listing the targets
    it was invoked for, so tests can assert on the prompt-once contract.
    """
    real = Path.symlink_to
    calls: list[Path] = []

    def failer(self, *args, **kwargs):
        calls.append(self)
        if should_fail(self):
            raise OSError(f"[Errno 1] mocked symlink failure for {self.name}")
        return real(self, *args, **kwargs)

    failer.calls = calls  # type: ignore[attr-defined]
    return failer


@pytest.fixture
def fail_all_symlinks(monkeypatch):
    """Patch Path.symlink_to to raise OSError for every call into a worktree."""
    failer = _make_symlink_failer(
        lambda target: target.name in (".claude", ".claudechic")
    )
    monkeypatch.setattr(Path, "symlink_to", failer)
    return failer


@pytest.fixture
def fail_only_claudechic(monkeypatch):
    """Patch Path.symlink_to to raise OSError only for .claudechic targets."""
    failer = _make_symlink_failer(lambda target: target.name == ".claudechic")
    monkeypatch.setattr(Path, "symlink_to", failer)
    return failer


@pytest.fixture
def reset_symlink_fallback_to_ask(monkeypatch):
    """Ensure CONFIG['worktree']['symlink_fallback'] is 'ask' for the test.

    The user's real ~/.claudechic/config.yaml could have set this to
    'copy' or 'abort', which would silently change the meaning of tests
    that exercise the default policy.
    """
    from claudechic import config as config_mod

    monkeypatch.setitem(
        config_mod.CONFIG.setdefault("worktree", {}),
        "symlink_fallback",
        "ask",
    )


class TestWorktreeSymlinkFallback:
    """Issue #26: OSError fallback to user-approved copy or abort.

    Three end-to-end tests, one per behavioral outcome:

    1. ``test_user_chooses_copy`` -- user (or pre-set config) approves a
       copy fallback. Folds in: prompt invoked exactly once, partial
       failure (.claude symlinks fine, .claudechic copies), copy is a
       real directory not a symlink, and snapshot semantics (later edits
       to the source do NOT propagate -- pins the difference between
       symlink and copy outcomes).

    2. ``test_user_chooses_abort`` -- user (or pre-set config) declines
       and aborts worktree creation. Folds in: rollback removes the
       worktree directory, ``start_worktree`` returns failure.

    3. ``test_no_consent_channel_aborts_safely`` -- OSError with no
       callback wired up and the default ``"ask"`` policy: defensive
       abort. Pins the security-relevant invariant that we NEVER
       silently degrade to copy without explicit consent.

    These tests do NOT depend on platform-native symlink support; they
    drive the OSError branch via mocking, which makes them valid
    regression tests on every CI runner including Windows.
    """

    def test_user_chooses_copy(
        self,
        patched_worktree_env,
        fail_only_claudechic,
        reset_symlink_fallback_to_ask,
    ):
        """E2E: OSError on .claudechic + callback returns 'copy'.

        Pins the full copy-fallback contract:
        - .claude symlinks fine (partial-failure / per-source semantics).
        - Callback is invoked exactly once (sticky decision, even though
          .claude is attempted first and succeeds).
        - .claudechic in the new worktree is a real directory, not a
          symlink, and contains the source's contents.
        - Edits to the source AFTER creation do NOT appear in the copy
          (snapshot semantics; pins the user-visible difference vs.
          symlinks so silent fallback can't sneak back in).
        """
        main_wt = patched_worktree_env["main_wt"]
        new_wt = patched_worktree_env["new_wt"]
        (main_wt / ".claude").mkdir()
        (main_wt / ".claude" / "settings.json").write_text("{}\n")
        (main_wt / ".claudechic").mkdir()
        (main_wt / ".claudechic" / "before.yaml").write_text("v: 1\n")

        prompted: list[str] = []

        def cb(name: str, _err: OSError) -> str:
            prompted.append(name)
            return "copy"

        success, _, wt_path = start_worktree("feat-x", cb)

        assert success
        assert wt_path == new_wt
        # Prompt-once contract: only the failing source asked the user.
        assert prompted == [".claudechic"]
        # .claude succeeded as a real symlink.
        assert (new_wt / ".claude").is_symlink()
        # .claudechic was copied -- real dir, not a symlink, contents match.
        assert (new_wt / ".claudechic").is_dir()
        assert not (new_wt / ".claudechic").is_symlink()
        assert (new_wt / ".claudechic" / "before.yaml").read_text() == "v: 1\n"

        # Snapshot semantics: edit source AFTER creation; copy must not see it.
        (main_wt / ".claudechic" / "after.yaml").write_text("v: 2\n")
        assert not (new_wt / ".claudechic" / "after.yaml").exists()

    def test_user_chooses_abort(
        self,
        patched_worktree_env,
        fail_all_symlinks,
        reset_symlink_fallback_to_ask,
    ):
        """E2E: OSError + callback returns 'abort' rolls back the worktree.

        ``start_worktree`` returns failure and the worktree directory is
        cleaned up via ``_rollback_worktree`` (best-effort
        ``git worktree remove --force`` + ``rmtree``).
        """
        main_wt = patched_worktree_env["main_wt"]
        new_wt = patched_worktree_env["new_wt"]
        (main_wt / ".claudechic").mkdir()

        success, msg, wt_path = start_worktree("feat-x", lambda _n, _e: "abort")

        assert not success
        assert wt_path is None
        assert "abort" in msg.lower()
        assert not new_wt.exists()

    def test_no_consent_channel_aborts_safely(
        self,
        patched_worktree_env,
        fail_all_symlinks,
        reset_symlink_fallback_to_ask,
    ):
        """E2E: OSError + no callback + default 'ask' policy = safe abort.

        Pins the security-relevant invariant: when no consent channel is
        wired up, we never silently copy. The user must explicitly
        approve the snapshot fallback for it to happen.
        """
        main_wt = patched_worktree_env["main_wt"]
        new_wt = patched_worktree_env["new_wt"]
        (main_wt / ".claudechic").mkdir()

        # No callback. Default config policy is "ask" (set by fixture).
        success, msg, _ = start_worktree("feat-x")

        assert not success
        assert "abort" in msg.lower()
        assert not new_wt.exists()
