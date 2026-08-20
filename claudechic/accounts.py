"""Claude account selection: the ``~/.claude-<name>`` config directories.

An "account" here is one Claude Code config directory. Claude Code reads
``CLAUDE_CONFIG_DIR`` to decide which directory to use, so keeping several
``~/.claude-<name>`` directories side by side keeps several logins side by
side. The shell helper ``use-claude <name>`` exports that variable for a
whole shell; ``claudechic --use-claude <name>`` does the same for a single
claudechic run, and for the Claude CLI it spawns, which inherits the env.

Selection FAILS CLOSED. An account that has no directory is an error, never
a silent fall back to ``~/.claude``: falling back would run the session --
and send the repository's contents -- under whichever login happened to be
configured, which is exactly the mix-up that separate accounts exist to
prevent. :func:`activate` therefore raises rather than guessing, and the
caller must abort before starting the TUI.

The naming is fixed by the rest of the codebase -- ``session_log.account_name``,
``session_log._accounts`` and ``chicsession_cmd._find_transcript`` all assume
``~/.claude-<name>``, with the account name being everything after the
``.claude-`` prefix. Plain ``~/.claude`` is the unnamed directory used when
nothing is selected at all; it is never listed as an account and can never be
reached by selecting one.

Import boundary: stdlib only. Nothing from claudechic may be imported here.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

ENV_VAR = "CLAUDE_CONFIG_DIR"
PREFIX = ".claude-"
FALLBACK_DIR_NAME = ".claude"

NO_LOGIN = "(no login yet)"

#: ``--use-claude`` with no value: list accounts instead of selecting one.
LIST_SENTINEL = "__list__"


class UnknownAccount(Exception):
    """Raised when a requested account has no ``~/.claude-<name>`` directory.

    Carries the rejected ``name`` and the ``path`` that was expected, so the
    caller can explain the failure and list the accounts that do exist.
    """

    def __init__(self, name: str, path: Path) -> None:
        super().__init__(f"no such Claude account: {name!r} (expected {path})")
        self.name = name
        self.path = path


@dataclass(frozen=True)
class Account:
    """One ``~/.claude-<name>`` config directory."""

    name: str
    path: Path
    email: str
    active: bool


def config_dir() -> Path:
    """The Claude config directory this process is using.

    ``CLAUDE_CONFIG_DIR`` when set (by the shell's ``use-claude`` or by
    ``--use-claude``), else the unnamed ``~/.claude``. This is the *reporting*
    view of the current state; it is not a fallback for a failed selection,
    which never gets this far.
    """
    env = os.environ.get(ENV_VAR)
    if env:
        return Path(env).expanduser()
    return Path.home() / FALLBACK_DIR_NAME


def account_dir(name: str, home: Path | None = None) -> Path:
    """Path of the config directory for account ``name``.

    Does not check existence. Raises ``ValueError`` for names that are empty
    or that would escape the home directory (path separators, ``.``, ``..``).
    """
    if not name or name in (".", ".."):
        raise ValueError(f"invalid account name: {name!r}")
    if "/" in name or "\\" in name or os.sep in name:
        raise ValueError(f"invalid account name: {name!r}")
    base = home if home is not None else Path.home()
    return base / f"{PREFIX}{name}"


def account_email(path: Path) -> str:
    """Email the config directory at ``path`` is logged in as.

    Reads ``<path>/.claude.json``. Returns :data:`NO_LOGIN` when the file is
    missing, unreadable, malformed, or holds no OAuth account -- this is a
    display helper for the account listing, so it never raises.
    """
    try:
        data = json.loads((Path(path) / ".claude.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return NO_LOGIN
    if not isinstance(data, dict):
        return NO_LOGIN
    oauth = data.get("oauthAccount")
    if not isinstance(oauth, dict):
        return NO_LOGIN
    return oauth.get("emailAddress") or NO_LOGIN


def _same_dir(a: Path, b: Path) -> bool:
    try:
        return a.resolve() == b.resolve()
    except OSError:
        return a == b


def list_accounts(home: Path | None = None) -> list[Account]:
    """Every ``~/.claude-<name>`` directory, sorted by name."""
    base = home if home is not None else Path.home()
    active_dir = config_dir()
    accounts: list[Account] = []
    try:
        candidates = sorted(base.glob(f"{PREFIX}*"))
    except OSError:
        return accounts
    for path in candidates:
        if not path.is_dir():
            continue
        name = path.name[len(PREFIX) :]
        if not name:
            continue
        accounts.append(
            Account(
                name=name,
                path=path,
                email=account_email(path),
                active=_same_dir(path, active_dir),
            )
        )
    return accounts


def format_accounts(accounts: list[Account], home: Path | None = None) -> str:
    """Human-readable listing; the active account is marked with ``*``."""
    base = home if home is not None else Path.home()
    if not accounts:
        return f"    (no {PREFIX}<name> accounts in {base})"
    width = max(len(a.name) for a in accounts)
    lines = [
        f"    {'*' if a.active else ' '} {a.name:<{width}} -> {a.email}  ({a.path})"
        for a in accounts
    ]
    if not any(a.active for a in accounts):
        lines.append(f"    (none selected -- using {config_dir()})")
    return "\n".join(lines)


def activate(name: str, home: Path | None = None) -> Account:
    """Select account ``name`` for this process by setting ``CLAUDE_CONFIG_DIR``.

    Raises :class:`UnknownAccount` if the directory does not exist. The
    directory is never created and there is no fallback: an unresolvable
    selection must abort the run rather than silently use another login.

    Must be called before anything reads Claude state, and always before the
    SDK spawns the ``claude`` CLI -- the child inherits the environment.
    """
    try:
        path = account_dir(name, home=home)
    except ValueError as exc:
        base = home if home is not None else Path.home()
        raise UnknownAccount(name, base / f"{PREFIX}{name}") from exc
    if not path.is_dir():
        raise UnknownAccount(name, path)
    os.environ[ENV_VAR] = str(path)
    return Account(name=name, path=path, email=account_email(path), active=True)


def handle_cli_flag(value: str) -> None:
    """Act on ``--use-claude``: list accounts, or select one, or exit non-zero.

    Lives here rather than in ``__main__`` so tests can exercise it without
    importing that module, whose import-time ``setup_logging()`` disables log
    propagation and breaks ``caplog`` for the rest of the test process.

    Exits the process on both the list path (status 0) and the unresolvable
    path (status 1); on the latter the TUI must never start.
    """
    if value == LIST_SENTINEL:
        print("Claude accounts (select with: claudechic --use-claude <name>):")
        print(format_accounts(list_accounts()))
        sys.exit(0)

    try:
        account = activate(value)
    except UnknownAccount as exc:
        print(f"No such Claude account: '{exc.name}' (expected {exc.path})")
        print("Refusing to start: there is no fallback account.")
        print("Available accounts:")
        print(format_accounts(list_accounts()))
        sys.exit(1)

    print(f"Claude account '{account.name}' -> {account.email} ({account.path})")
