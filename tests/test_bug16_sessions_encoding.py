"""Bug #16: aiofiles.open missing encoding='utf-8' in load_session_messages.

The bug: aiofiles.open(session_file) without encoding= uses the platform
default. On Linux (UTF-8) this works. On Windows (cp1252) it crashes on
non-ASCII bytes that Claude actually produces (smart quotes, em dashes).

The primary test is behavioral: create a real JSONL with non-ASCII content,
call load_session_messages() through the real code path. Passes on Linux
(UTF-8 default), fails on Windows CI (cp1252 default) without the fix.
"""

import json
import re
from pathlib import Path

import pytest

from claudechic.sessions import encode_project_key, load_session_messages


@pytest.mark.asyncio
async def test_load_session_messages_with_non_ascii(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """load_session_messages loads JSONL containing non-ASCII content.

    Reproduces the real user scenario: Claude writes smart quotes,
    em dashes, and accented characters into session JSONL files.
    On Windows with cp1252 default encoding, the old code raises
    UnicodeDecodeError. The fix adds encoding='utf-8'.
    """
    project_dir = tmp_path / "myproject"
    project_dir.mkdir()
    project_key = encode_project_key(project_dir)
    session_id = "00000000-0000-0000-0000-000000000001"

    sessions_dir = tmp_path / ".claude" / "projects" / project_key
    sessions_dir.mkdir(parents=True)
    session_file = sessions_dir / f"{session_id}.jsonl"

    # Write real JSONL with non-ASCII content Claude actually produces
    lines = [
        {
            "type": "user",
            "message": {"content": "Explain the \u2018decorator\u2019 pattern"},
            "timestamp": "2025-01-15T10:00:00Z",
        },
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "text",
                        "text": "The decorator pattern \u2014 also known as \u201cwrapper\u201d \u2014 is structural. R\u00e9sum\u00e9s use it.",
                    }
                ],
                "model": "claude-sonnet-4-20250514",
            },
            "timestamp": "2025-01-15T10:00:01Z",
        },
        {
            "type": "user",
            "message": {"content": "Show me caf\u00e9-style na\u00efve co\u00f6peration"},
            "timestamp": "2025-01-15T10:00:02Z",
        },
    ]
    session_file.write_text(
        "\n".join(json.dumps(line, ensure_ascii=False) for line in lines) + "\n",
        encoding="utf-8",
    )

    # Point Path.home() at our temp dir
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Call the REAL load_session_messages through the REAL code path
    messages = await load_session_messages(session_id, cwd=project_dir)

    # Verify all messages loaded correctly
    assert len(messages) == 3, f"Expected 3 messages, got {len(messages)}"
    assert messages[0]["type"] == "user"
    assert "decorator" in messages[0]["content"]
    assert messages[1]["type"] == "assistant"
    assert "decorator pattern" in messages[1]["content"]
    assert messages[2]["type"] == "user"
    assert "caf" in messages[2]["content"]


def test_aiofiles_open_has_encoding() -> None:
    """All text-mode aiofiles.open() calls in sessions.py specify encoding.

    Static analysis safety net: ensures no future regressions.
    """
    source = Path(__file__).resolve().parent.parent / "claudechic" / "sessions.py"
    text = source.read_text(encoding="utf-8")

    pattern = re.compile(r"aiofiles\.open\([^)]*\)")
    matches = pattern.findall(text)
    assert matches, "Expected at least one aiofiles.open() call"

    for call in matches:
        if re.search(r'mode\s*=\s*"[rwa]b"', call):
            continue
        assert "encoding=" in call, (
            f"aiofiles.open() missing encoding= parameter: {call}"
        )
