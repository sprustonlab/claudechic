"""Tests for the optional session-log mirror (claudechic.session_log).

Focus: the mirror produces BYTE-IDENTICAL copies of the .jsonl transcripts,
split by account, only re-copying changed files.
"""

from pathlib import Path

from claudechic import session_log


def _write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def test_sync_once_is_byte_identical(tmp_path):
    home = tmp_path / "home"
    dest = tmp_path / "log"
    # two accounts, a nested subagent transcript, and a .bak that must be ignored
    _write(home / ".claude-hhmi" / "projects" / "slugA" / "s1.jsonl",
           '{"a":1}\n{"b":2}\n')
    _write(home / ".claude-hhmi" / "projects" / "slugA" / "s1" / "subagents"
           / "sub.jsonl", '{"x":9}\n')
    _write(home / ".claude-work" / "projects" / "slugB" / "s2.jsonl", '{"c":3}\n')
    _write(home / ".claude-hhmi" / "projects" / "slugA" / "s1.jsonl.bak", "OLD\n")

    copied = session_log.sync_once(dest, home=home)
    assert copied == 3  # two top-level + one nested; the .bak is excluded

    for acct, rel in [
        ("hhmi", "projects/slugA/s1.jsonl"),
        ("hhmi", "projects/slugA/s1/subagents/sub.jsonl"),
        ("work", "projects/slugB/s2.jsonl"),
    ]:
        src = home / f".claude-{acct}" / rel
        cp = dest / acct / rel
        assert cp.read_bytes() == src.read_bytes(), f"copy differs for {rel}"

    # non-.jsonl (the .bak) is never mirrored
    assert not (dest / "hhmi" / "projects" / "slugA" / "s1.jsonl.bak").exists()


def test_sync_once_only_recopies_changed(tmp_path):
    home = tmp_path / "home"
    dest = tmp_path / "log"
    f = home / ".claude-hhmi" / "projects" / "p" / "a.jsonl"
    _write(f, '{"a":1}\n')

    assert session_log.sync_once(dest, home=home) == 1
    assert session_log.sync_once(dest, home=home) == 0  # unchanged -> skipped

    with f.open("a", encoding="utf-8") as fh:  # append a line
        fh.write('{"a":2}\n')
    assert session_log.sync_once(dest, home=home) == 1  # changed -> re-copied
    assert (dest / "hhmi" / "projects" / "p" / "a.jsonl").read_bytes() \
        == f.read_bytes()


def test_no_projects_dir_is_noop(tmp_path):
    home = tmp_path / "home"
    (home / ".claude-empty").mkdir(parents=True)  # account with no projects/
    assert session_log.sync_once(tmp_path / "log", home=home) == 0


def test_chicsessions_root_divides_by_account(tmp_path, monkeypatch):
    cfg = tmp_path / ".claudechic" / "config.yaml"
    cfg.parent.mkdir(parents=True)
    cfg.write_text("session_log_dir: /tmp/sl\n", encoding="utf-8")

    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / ".claude-work"))
    assert session_log.account_name() == "work"
    # chicsessions live under <base>/<account>, mirroring the transcript split
    assert session_log.chicsessions_root(tmp_path) == Path("/tmp/sl/work")

    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
    assert session_log.account_name() == "default"
