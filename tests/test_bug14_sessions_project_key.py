"""Bug #14: project_key encoding -- colon stripped instead of replaced.

The bug: encode_project_key() strips colons (.replace(":", ""))
instead of replacing with dashes (.replace(":", "-")). On Windows,
C:\\Users\\dev -> "C-Users-dev" instead of "C--Users-dev", so sessions
written by Claude Code are never found.

Tests call the REAL encode_project_key() pure function with Windows-style
paths containing colons. No filesystem, no monkeypatch -- just input/output.
"""

from pathlib import Path

import pytest

from claudechic.sessions import encode_project_key


@pytest.mark.parametrize(
    "cwd_str, expected_key",
    [
        # Claude Code replaces \ / : _ . with dashes
        ("C:\\Users\\dev\\project", "C--Users-dev-project"),
        ("E:\\DELTA", "E--DELTA"),
        ("/home/user/project", "-home-user-project"),
        ("/home/user/.local/share", "-home-user--local-share"),
        ("/home/user/my_project", "-home-user-my-project"),
    ],
    ids=["windows-full", "windows-short", "unix-basic", "dot-kept", "underscore-kept"],
)
def test_encode_project_key_replaces_colons(cwd_str: str, expected_key: str) -> None:
    """encode_project_key replaces colons with dashes, not strips them.

    With the bug:  C:\\Users -> C-Users  (colon vanishes)
    With the fix:  C:\\Users -> C--Users (colon becomes dash)
    """
    result = encode_project_key(Path(cwd_str))
    assert result == expected_key
