"""Tests for git diff feature."""

import subprocess

import pytest

from claudechic.features.diff.git import (
    MAX_UNTRACKED_FILES,
    FileChange,
    _merge_diff_content,
    _parse_hunks,
    _parse_name_status,
    get_changes,
    get_file_stats,
)


class TestParseNameStatus:
    def test_modified_file(self):
        output = "M\tpath/to/file.py"
        changes = _parse_name_status(output)
        assert len(changes) == 1
        assert changes[0].path == "path/to/file.py"
        assert changes[0].status == "modified"

    def test_added_file(self):
        output = "A\tnew_file.py"
        changes = _parse_name_status(output)
        assert len(changes) == 1
        assert changes[0].status == "added"

    def test_deleted_file(self):
        output = "D\told_file.py"
        changes = _parse_name_status(output)
        assert len(changes) == 1
        assert changes[0].status == "deleted"

    def test_multiple_files(self):
        output = "M\tfile1.py\nA\tfile2.py\nD\tfile3.py"
        changes = _parse_name_status(output)
        assert len(changes) == 3

    def test_empty_output(self):
        changes = _parse_name_status("")
        assert len(changes) == 0


class TestParseHunks:
    def test_single_hunk(self):
        diff_section = """a/file.py b/file.py
index abc123..def456 100644
--- a/file.py
+++ b/file.py
@@ -1,3 +1,4 @@
 line1
 line2
+new line
 line3
"""
        hunks = _parse_hunks(diff_section)
        assert len(hunks) == 1
        assert hunks[0].old_start == 1
        assert hunks[0].old_count == 3
        assert hunks[0].new_start == 1
        assert hunks[0].new_count == 4
        assert "new line" in hunks[0].new_lines
        assert "new line" not in hunks[0].old_lines

    def test_multiple_hunks(self):
        diff_section = """a/file.py b/file.py
@@ -1,3 +1,4 @@
 line1
+added1
 line2
 line3
@@ -10,3 +11,4 @@
 line10
+added2
 line11
 line12
"""
        hunks = _parse_hunks(diff_section)
        assert len(hunks) == 2
        assert hunks[0].old_start == 1
        assert hunks[1].old_start == 10
        assert "added1" in hunks[0].new_lines
        assert "added2" in hunks[1].new_lines

    def test_deletion_hunk(self):
        diff_section = """a/file.py b/file.py
@@ -1,4 +1,3 @@
 line1
-deleted line
 line2
 line3
"""
        hunks = _parse_hunks(diff_section)
        assert len(hunks) == 1
        assert "deleted line" in hunks[0].old_lines
        assert "deleted line" not in hunks[0].new_lines


class TestMergeDiffContent:
    def test_merges_hunks_to_files(self):
        """Use a path containing 'b/' to also cover regression #54."""
        files = [
            FileChange(path="bokehjs/src/lib/patch.ts", status="modified", hunks=[]),
        ]
        diff_text = """diff --git a/bokehjs/src/lib/patch.ts b/bokehjs/src/lib/patch.ts
index abc..def 100644
--- a/bokehjs/src/lib/patch.ts
+++ b/bokehjs/src/lib/patch.ts
@@ -1,2 +1,3 @@
 old
+new
 end
"""
        result = _merge_diff_content(files, diff_text)
        assert len(result) == 1
        assert len(result[0].hunks) == 1
        assert "new" in result[0].hunks[0].new_lines


def _init_repo(path) -> None:
    """Create a minimal git repo with one tracked commit so HEAD exists."""
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.t"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=path, check=True)
    seed = path / "seed.txt"
    seed.write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "add", "seed.txt"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "seed"], cwd=path, check=True)


class TestUntrackedCap:
    """MAX_UNTRACKED_FILES guards against pathological repos (1000s of
    untracked files in node_modules / build / data dirs) hanging the diff
    screen for tens of seconds.

    Skip-all-if-many semantics: when the cap fires, the untracked listing
    is dropped entirely; tracked changes are unaffected.
    """

    @pytest.mark.asyncio
    async def test_under_cap_includes_all_untracked(self, tmp_path):
        _init_repo(tmp_path)
        n = MAX_UNTRACKED_FILES  # exactly at the cap -> still included
        for i in range(n):
            (tmp_path / f"u{i}.txt").write_text(f"hello {i}\n", encoding="utf-8")

        changes = await get_changes(str(tmp_path))
        untracked_paths = {c.path for c in changes if c.status == "untracked"}
        assert len(untracked_paths) == n

        stats = await get_file_stats(str(tmp_path))
        untracked_stat_paths = {s.path for s in stats if s.untracked}
        assert len(untracked_stat_paths) == n

    @pytest.mark.asyncio
    async def test_over_cap_skips_all_untracked(self, tmp_path, caplog):
        _init_repo(tmp_path)
        n = MAX_UNTRACKED_FILES + 1
        for i in range(n):
            (tmp_path / f"u{i}.txt").write_text(f"hi {i}\n", encoding="utf-8")

        # Subscribe at WARNING so the cap-skip notice is captured. Attach
        # to the package logger directly because `claudechic` may have
        # propagate=False after setup_logging() runs in another test.
        import logging

        capture_logger = logging.getLogger("claudechic.features.diff.git")
        with caplog.at_level(logging.WARNING, logger=capture_logger.name):
            changes = await get_changes(str(tmp_path))
            stats = await get_file_stats(str(tmp_path))

        # No untracked entries should appear in either result.
        assert not [c for c in changes if c.status == "untracked"]
        assert not [s for s in stats if s.untracked]

        # Cap-fire should be logged so users have a breadcrumb.
        cap_msgs = [r for r in caplog.records if "exceeds cap" in r.getMessage()]
        assert cap_msgs, "Expected a WARNING log when untracked cap fires"

    @pytest.mark.asyncio
    async def test_over_cap_keeps_tracked_changes(self, tmp_path):
        """The cap on untracked files must not affect tracked-change rendering."""
        _init_repo(tmp_path)
        # One tracked modification.
        (tmp_path / "seed.txt").write_text("seed\nmod\n", encoding="utf-8")
        # And many untracked files.
        for i in range(MAX_UNTRACKED_FILES + 5):
            (tmp_path / f"u{i}.txt").write_text("x\n", encoding="utf-8")

        changes = await get_changes(str(tmp_path))
        tracked = [c for c in changes if c.status != "untracked"]
        assert len(tracked) == 1
        assert tracked[0].path == "seed.txt"
