"""Bug #14: project_key encoding -- colon stripped instead of replaced.

The bug: get_project_sessions_dir() strips colons (.replace(":", ""))
instead of replacing with dashes (.replace(":", "-")). On Windows,
C:\\Users\\dev -> "C-Users-dev" instead of "C--Users-dev", so sessions
written by Claude Code are never found.

These tests create a session directory using Claude Code's REAL encoding
(colon -> dash), then call get_project_sessions_dir() and check whether
it finds the directory. On unfixed code, the function computes the wrong
key and returns None.
"""

from pathlib import Path

import pytest

from claudechic.sessions import get_project_sessions_dir


@pytest.mark.parametrize(
    "cwd_str, claude_code_key",
    [
        # Claude Code replaces \ / : _ . with dashes
        ("C:\\Users\\dev\\project", "C--Users-dev-project"),
        ("E:\\DELTA", "E--DELTA"),
    ],
    ids=["windows-full-path", "windows-short-path"],
)
def test_get_project_sessions_dir_finds_claude_code_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cwd_str: str, claude_code_key: str
) -> None:
    """get_project_sessions_dir must find sessions written by Claude Code.

    Claude Code encodes colons as dashes. If our encoding strips colons
    instead, the directory lookup fails silently (returns None).
    """
    # Create the directory structure Claude Code actually writes
    sessions_dir = tmp_path / ".claude" / "projects" / claude_code_key
    sessions_dir.mkdir(parents=True)
    (sessions_dir / "00000000-0000-0000-0000-000000000001.jsonl").write_text(
        '{"type":"user","message":{"content":"hi"}}\n', encoding="utf-8"
    )

    # Point Path.home() at our temp dir
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Call the real function with a Windows-style path
    result = get_project_sessions_dir(Path(cwd_str))

    # With the bug: returns None (wrong key, directory not found)
    # With the fix: returns the sessions_dir path
    assert result is not None, (
        f"get_project_sessions_dir returned None for {cwd_str!r} -- "
        f"expected to find directory at {sessions_dir}"
    )
    assert result == sessions_dir
