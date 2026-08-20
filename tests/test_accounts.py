"""Tests for Claude account selection (claudechic.accounts).

Focus: selection FAILS CLOSED. An account with no ``~/.claude-<name>``
directory must raise instead of falling back to ``~/.claude``, and the CLI
must exit non-zero before the TUI starts.

Note the CLI tests drive ``accounts.handle_cli_flag`` rather than importing
``claudechic.__main__``: that module runs ``setup_logging()`` at import,
which sets ``propagate=False`` on the claudechic logger and breaks ``caplog``
for every later test in the same process.
"""

import json
from pathlib import Path

import pytest

from claudechic import accounts


def _account(home: Path, name: str, email: str | None = None) -> Path:
    d = home / f".claude-{name}"
    d.mkdir(parents=True)
    if email is not None:
        (d / ".claude.json").write_text(
            json.dumps({"oauthAccount": {"emailAddress": email}}), encoding="utf-8"
        )
    return d


@pytest.fixture
def home(tmp_path, monkeypatch):
    """An isolated HOME with no CLAUDE_CONFIG_DIR selected."""
    monkeypatch.delenv(accounts.ENV_VAR, raising=False)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    return tmp_path


# --- selection fails closed -------------------------------------------------


def test_activate_unknown_account_raises(home):
    _account(home, "work", "a@work.example")

    with pytest.raises(accounts.UnknownAccount) as exc:
        accounts.activate("nope", home=home)

    assert exc.value.name == "nope"
    assert exc.value.path == home / ".claude-nope"


def test_activate_unknown_account_does_not_set_env(home, monkeypatch):
    """The failure must not leave a half-applied selection behind."""
    with pytest.raises(accounts.UnknownAccount):
        accounts.activate("nope", home=home)
    assert accounts.ENV_VAR not in __import__("os").environ


def test_activate_unknown_account_does_not_create_the_dir(home):
    with pytest.raises(accounts.UnknownAccount):
        accounts.activate("nope", home=home)
    assert not (home / ".claude-nope").exists()


def test_activate_never_falls_back_to_plain_claude(home, monkeypatch):
    """Even with ~/.claude present and usable, a bad name must not use it."""
    (home / ".claude").mkdir()
    monkeypatch.setenv(accounts.ENV_VAR, str(home / ".claude-work"))
    _account(home, "work", "a@work.example")

    with pytest.raises(accounts.UnknownAccount):
        accounts.activate("nope", home=home)

    # prior selection untouched, and definitely not switched to ~/.claude
    import os

    assert os.environ[accounts.ENV_VAR] == str(home / ".claude-work")


@pytest.mark.parametrize("name", ["", ".", "..", "../evil", "a/b", "a\\b"])
def test_activate_rejects_names_that_escape_home(home, name):
    with pytest.raises(accounts.UnknownAccount):
        accounts.activate(name, home=home)


def test_activate_sets_env_and_returns_account(home):
    path = _account(home, "hhmi", "basta@hhmi.example")

    acct = accounts.activate("hhmi", home=home)

    import os

    assert os.environ[accounts.ENV_VAR] == str(path)
    assert acct == accounts.Account(
        name="hhmi", path=path, email="basta@hhmi.example", active=True
    )


# --- listing ----------------------------------------------------------------


def test_list_accounts_finds_named_dirs_only(home):
    _account(home, "ant", "arco@personal.example")
    _account(home, "hhmi")  # no .claude.json -> no login yet
    (home / ".claude").mkdir()  # unnamed fallback is never an account
    (home / ".claude-file").write_text("x", encoding="utf-8")  # not a dir

    listed = accounts.list_accounts(home=home)

    assert [a.name for a in listed] == ["ant", "hhmi"]
    assert listed[0].email == "arco@personal.example"
    assert listed[1].email == accounts.NO_LOGIN
    assert not any(a.active for a in listed)


def test_list_accounts_marks_the_active_one(home, monkeypatch):
    _account(home, "ant", "arco@personal.example")
    path = _account(home, "hhmi", "basta@hhmi.example")
    monkeypatch.setenv(accounts.ENV_VAR, str(path))

    active = [a.name for a in accounts.list_accounts(home=home) if a.active]

    assert active == ["hhmi"]


def test_format_accounts_marks_active_and_notes_when_none_selected(home):
    _account(home, "ant", "arco@personal.example")

    text = accounts.format_accounts(accounts.list_accounts(home=home), home=home)

    assert "ant -> arco@personal.example" in text
    assert "none selected" in text


def test_format_accounts_with_no_accounts(home):
    assert ".claude-<name> accounts" in accounts.format_accounts([], home=home)


# --- email lookup is display-only and never raises --------------------------


@pytest.mark.parametrize(
    "content",
    [None, "not json", "[]", "{}", '{"oauthAccount": null}', '{"oauthAccount": {}}'],
)
def test_account_email_degrades_to_no_login(home, content):
    d = home / ".claude-x"
    d.mkdir()
    if content is not None:
        (d / ".claude.json").write_text(content, encoding="utf-8")
    assert accounts.account_email(d) == accounts.NO_LOGIN


# --- config_dir reporting ---------------------------------------------------


def test_config_dir_reports_selection_then_unnamed_dir(home, monkeypatch):
    assert accounts.config_dir() == home / ".claude"
    monkeypatch.setenv(accounts.ENV_VAR, str(home / ".claude-work"))
    assert accounts.config_dir() == home / ".claude-work"


# --- CLI wiring -------------------------------------------------------------


def test_cli_unknown_account_exits_before_the_tui(home, capsys):
    _account(home, "ant", "arco@personal.example")

    with pytest.raises(SystemExit) as exc:
        accounts.handle_cli_flag("nope")

    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "No such Claude account: 'nope'" in out
    assert "no fallback" in out
    assert "ant" in out  # the real accounts are offered


def test_cli_lists_accounts_and_exits_zero(home, capsys):
    _account(home, "ant", "arco@personal.example")
    with pytest.raises(SystemExit) as exc:
        accounts.handle_cli_flag("__list__")

    assert exc.value.code == 0
    assert "ant -> arco@personal.example" in capsys.readouterr().out


def test_cli_selects_account(home, capsys):
    path = _account(home, "hhmi", "basta@hhmi.example")
    accounts.handle_cli_flag("hhmi")

    import os

    assert os.environ[accounts.ENV_VAR] == str(path)
    assert "basta@hhmi.example" in capsys.readouterr().out


# --- consumers follow the selected account ----------------------------------
#
# Each of these read Claude's own state. Before account support they were
# hardcoded to ~/.claude, so selecting an account changed which login the
# session ran under while these kept reading another account's data.


def test_session_dir_follows_selected_account(home, monkeypatch, tmp_path):
    from claudechic import sessions

    monkeypatch.setenv(accounts.ENV_VAR, str(home / ".claude-hhmi"))
    project = tmp_path / "repo"
    project.mkdir()
    key = sessions.encode_project_key(project.absolute())
    wanted = home / ".claude-hhmi" / "projects" / key
    wanted.mkdir(parents=True)
    (home / ".claude" / "projects" / key).mkdir(parents=True)  # other account

    assert sessions.get_project_sessions_dir(project) == wanted


async def test_plan_path_follows_selected_account(home, monkeypatch, tmp_path):
    from claudechic import sessions

    monkeypatch.setenv(accounts.ENV_VAR, str(home / ".claude-hhmi"))
    project = tmp_path / "repo"
    project.mkdir()
    key = sessions.encode_project_key(project.absolute())
    sess_dir = home / ".claude-hhmi" / "projects" / key
    sess_dir.mkdir(parents=True)
    sid = "11111111-2222-3333-4444-555555555555"
    (sess_dir / f"{sid}.jsonl").write_text(
        json.dumps({"slug": "my-plan"}) + "\n", encoding="utf-8"
    )

    plan = await sessions.get_plan_path_for_session(sid, project, must_exist=False)

    assert plan == home / ".claude-hhmi" / "plans" / "my-plan.md"


def test_history_file_follows_selected_account(home, monkeypatch):
    from claudechic import history

    assert history.history_file() == home / ".claude" / "history.jsonl"
    monkeypatch.setenv(accounts.ENV_VAR, str(home / ".claude-hhmi"))
    assert history.history_file() == home / ".claude-hhmi" / "history.jsonl"


def test_awareness_rules_dir_follows_selected_account(home, monkeypatch):
    from claudechic import awareness_install

    assert awareness_install.claude_rules_dir() == home / ".claude" / "rules"
    monkeypatch.setenv(accounts.ENV_VAR, str(home / ".claude-hhmi"))
    assert awareness_install.claude_rules_dir() == home / ".claude-hhmi" / "rules"


def test_audit_projects_dir_follows_selected_account(home, monkeypatch):
    from claudechic.audit import audit

    monkeypatch.setenv(accounts.ENV_VAR, str(home / ".claude-hhmi"))
    assert audit.claude_projects_dir() == home / ".claude-hhmi" / "projects"


def test_credentials_path_follows_selected_account(home, monkeypatch):
    """The usage/rate-limit token must come from the account in use."""
    from claudechic import usage

    monkeypatch.setenv(accounts.ENV_VAR, str(home / ".claude-hhmi"))
    creds = home / ".claude-hhmi"
    creds.mkdir()
    (creds / ".credentials.json").write_text(
        json.dumps({"claudeAiOauth": {"accessToken": "tok-hhmi"}}), encoding="utf-8"
    )
    other = home / ".claude"
    other.mkdir()
    (other / ".credentials.json").write_text(
        json.dumps({"claudeAiOauth": {"accessToken": "tok-wrong"}}), encoding="utf-8"
    )

    assert usage._get_oauth_token_file() == "tok-hhmi"


def test_user_command_lookup_follows_selected_account(home, monkeypatch, tmp_path):
    from claudechic import commands

    monkeypatch.setenv(accounts.ENV_VAR, str(home / ".claude-hhmi"))
    cwd = tmp_path / "repo"
    cwd.mkdir()
    cmd_dir = home / ".claude-hhmi" / "commands"
    cmd_dir.mkdir(parents=True)
    (cmd_dir / "mine.md").write_text("x", encoding="utf-8")

    assert commands._is_user_command("/mine", cwd) is True
    assert commands._is_user_command("/absent", cwd) is False


def test_user_command_lookup_ignores_other_accounts(home, monkeypatch, tmp_path):
    from claudechic import commands

    monkeypatch.setenv(accounts.ENV_VAR, str(home / ".claude-hhmi"))
    (home / ".claude-hhmi").mkdir()
    cwd = tmp_path / "repo"
    cwd.mkdir()
    other = home / ".claude" / "commands"
    other.mkdir(parents=True)
    (other / "theirs.md").write_text("x", encoding="utf-8")

    assert commands._is_user_command("/theirs", cwd) is False
