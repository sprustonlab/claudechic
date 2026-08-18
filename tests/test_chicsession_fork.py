"""Tests for chicsession forking (claudechic.chicsession_cmd.fork_chicsession).

A fork duplicates each agent's transcript byte-for-byte to a fresh session
id and writes a new manifest -- same history, new ids, diverges on resume.
"""

from pathlib import Path

import pytest

from claudechic import chicsession_cmd
from claudechic.chicsessions import (
    Chicsession,
    ChicsessionEntry,
    ChicsessionManager,
)


def _mk_transcript(home: Path, acct: str, slug: str, sid: str, text: str) -> Path:
    p = home / f".claude-{acct}" / "projects" / slug / f"{sid}.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def test_fork_duplicates_transcripts_and_mints_new_ids(tmp_path):
    home = tmp_path / "home"
    root = tmp_path / "log"
    a1 = _mk_transcript(home, "hhmi", "slugA",
                        "aaaaaaaa-0000-0000-0000-000000000001", '{"l":1}\n{"l":2}\n')
    a2 = _mk_transcript(home, "work", "slugB",
                        "bbbbbbbb-0000-0000-0000-000000000002", '{"m":1}\n')
    mgr = ChicsessionManager(root)
    src = Chicsession(
        name="orig",
        active_agent="A",
        agents=[
            ChicsessionEntry("A", "aaaaaaaa-0000-0000-0000-000000000001", "/x"),
            ChicsessionEntry("B", "bbbbbbbb-0000-0000-0000-000000000002", "/y"),
        ],
        workflow_state={"phase": "impl"},
    )
    mgr.save(src)

    _new, forked, missing = chicsession_cmd.fork_chicsession(
        mgr, src, "forked", home=home
    )
    assert (forked, missing) == (2, 0)

    loaded = mgr.load("forked")
    assert loaded.active_agent == "A"
    assert loaded.workflow_state == {"phase": "impl"}
    assert [e.name for e in loaded.agents] == ["A", "B"]
    assert [e.cwd for e in loaded.agents] == ["/x", "/y"]

    for orig, new, src_path in zip(src.agents, loaded.agents, [a1, a2]):
        assert new.session_id != orig.session_id  # a fresh id
        new_path = src_path.parent / f"{new.session_id}.jsonl"
        assert new_path.exists()
        assert new_path.read_bytes() == src_path.read_bytes()  # byte-identical
        assert src_path.exists()  # original untouched


def test_fork_rejects_existing_name(tmp_path):
    mgr = ChicsessionManager(tmp_path / "log")
    src = Chicsession(name="orig", active_agent="A", agents=[])
    mgr.save(src)
    mgr.save(Chicsession(name="taken", active_agent="A", agents=[]))
    with pytest.raises(ValueError):
        chicsession_cmd.fork_chicsession(mgr, src, "taken", home=tmp_path / "home")


def test_fork_keeps_missing_transcript_shared(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    mgr = ChicsessionManager(tmp_path / "log")
    src = Chicsession(
        name="orig",
        active_agent="A",
        agents=[ChicsessionEntry("A", "no-such-session-id", "/x")],
    )
    mgr.save(src)
    _new, forked, missing = chicsession_cmd.fork_chicsession(
        mgr, src, "forked", home=home
    )
    assert (forked, missing) == (0, 1)
    assert mgr.load("forked").agents[0].session_id == "no-such-session-id"
