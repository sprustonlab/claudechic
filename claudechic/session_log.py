"""Optional session-log mirroring for claudechic.

When ``session_log_dir`` is set in config (~/.claudechic/config.yaml or a
project's <cwd>/.claudechic/config.yaml), claudechic mirrors every Claude
transcript (.jsonl) into that directory as a BYTE-IDENTICAL copy and, via
`chicsession_cmd._get_root`, stores chicsession manifests there too. The
mirror is split by Claude account (the ``~/.claude-<name>`` selected with
`use-claude`), then by Claude's own project/cwd layout:

    <session_log_dir>/<account>/projects/<cwd-slug>/<session_id>.jsonl
    <session_log_dir>/<account>/.chicsessions/<name>.json

If ``session_log_dir`` is NOT configured, every function here is inert and
claudechic behaves exactly as upstream -- so this module is safe to push
upstream; only a config value turns it on.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import subprocess
import time
from pathlib import Path

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Config resolution (user-tier, then project-tier which overrides)
# ---------------------------------------------------------------------------

def _read_yaml(path: Path) -> dict:
    try:
        import yaml

        if path.is_file():
            return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        pass
    return {}


def _config_dirs(cwd: Path | None) -> list[Path]:
    """Directories whose .claudechic/config.yaml may define session-log keys.

    User-tier first (lowest precedence), then the working dir and its git
    root (project-tier, highest precedence). ``cwd`` defaults to the process
    cwd so paths that lack an explicit app cwd still resolve consistently.
    """
    base = Path(cwd) if cwd is not None else Path.cwd()
    dirs: list[Path] = []
    dirs.append(base)
    try:
        r = subprocess.run(
            ["git", "-C", str(base), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        )
        top = Path(r.stdout.strip())
        if top != base:
            dirs.append(top)
    except Exception:
        pass
    return dirs


def merged_config(cwd: Path | None = None) -> dict:
    cfg: dict = {}
    cfg.update(_read_yaml(Path.home() / ".claudechic" / "config.yaml"))
    for d in _config_dirs(cwd):
        cfg.update(_read_yaml(d / ".claudechic" / "config.yaml"))
    return cfg


def session_log_dir(cwd: Path | None = None) -> Path | None:
    val = merged_config(cwd).get("session_log_dir")
    return Path(str(val)).expanduser() if val else None


def account_name() -> str:
    """Active Claude account = the ``~/.claude-<name>`` selected via
    ``use-claude`` (CLAUDE_CONFIG_DIR). Falls back to ``default`` when unset.
    Used to divide the session log by account, matching the transcript split.
    """
    cfg = os.environ.get("CLAUDE_CONFIG_DIR")
    if cfg:
        base = Path(cfg).name
        if base.startswith(".claude-"):
            base = base[len(".claude-"):]
        return base or "default"
    return "default"


def chicsessions_root(cwd: Path | None = None) -> Path | None:
    """Root whose ``.chicsessions/`` holds manifests, divided by account:
    ``<base>/<account>`` (so manifests land in ``<base>/<account>/.chicsessions``,
    mirroring the ``<base>/<account>/projects`` transcript split). Explicit
    ``chicsessions_root`` wins as the base; otherwise ``session_log_dir``."""
    cfg = merged_config(cwd)
    val = cfg.get("chicsessions_root") or cfg.get("session_log_dir")
    if not val:
        return None
    return Path(str(val)).expanduser() / account_name()


# ---------------------------------------------------------------------------
# Mirroring
# ---------------------------------------------------------------------------

def _accounts(home: Path | None = None):
    """Yield (account_name, projects_dir) for every ~/.claude-*/projects."""
    base = home if home is not None else Path.home()
    for cfg in sorted(base.glob(".claude-*")):
        proj = cfg / "projects"
        if proj.is_dir():
            yield cfg.name[len(".claude-"):], proj


def sync_once(dest: Path, home: Path | None = None) -> int:
    """Copy every *.jsonl transcript into ``dest`` verbatim (byte-identical).

    Only new/changed files are copied (size or mtime differs). Returns the
    number of files copied this pass. Never raises.
    """
    copied = 0
    for name, proj in _accounts(home):
        for src in proj.rglob("*.jsonl"):
            try:
                rel = src.relative_to(proj)
                out = dest / name / "projects" / rel
                s = src.stat()
                if out.exists():
                    o = out.stat()
                    if o.st_size == s.st_size and o.st_mtime >= s.st_mtime:
                        continue
                out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, out)  # byte-for-byte + mtime
                copied += 1
            except OSError:
                continue
    return copied


def git_commit(dest: Path) -> bool:
    """Commit anything new in the session-log repo. Inits the repo if needed.
    Returns True if a commit was made. Never raises."""
    try:
        dest.mkdir(parents=True, exist_ok=True)
        if not (dest / ".git").is_dir():
            subprocess.run(["git", "init", "-q"], cwd=dest, check=True,
                           capture_output=True)
        st = subprocess.run(["git", "status", "--porcelain"], cwd=dest,
                            capture_output=True, text=True)
        if not st.stdout.strip():
            return False
        subprocess.run(["git", "add", "-A"], cwd=dest, check=True,
                       capture_output=True)
        stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        subprocess.run(
            ["git", "-c", "user.name=claudechic",
             "-c", "user.email=claudechic@localhost",
             "-c", "commit.gpgsign=false",
             "commit", "-q", "-m", f"sync {stamp}"],
            cwd=dest, check=True, capture_output=True,
        )
        return True
    except Exception:
        return False


async def run_sync_loop(dest: Path, sync_interval: float = 5.0,
                        commit_interval: float = 60.0) -> None:
    """Background loop: copy every ``sync_interval`` s, commit at most every
    ``commit_interval`` s. Runs blocking IO in the default executor so the UI
    never stalls. Swallows all errors so a mirror failure never affects the
    session."""
    loop = asyncio.get_event_loop()
    last_commit = 0.0
    log.info("session-log mirror active -> %s", dest)
    while True:
        try:
            await loop.run_in_executor(None, sync_once, dest)
            now = time.time()
            if now - last_commit >= commit_interval:
                await loop.run_in_executor(None, git_commit, dest)
                last_commit = now
        except Exception:
            log.debug("session-log sync pass failed", exc_info=True)
        await asyncio.sleep(sync_interval)


if __name__ == "__main__":  # manual: python -m claudechic.session_log <dir>
    import sys

    d = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else session_log_dir()
    if d is None:
        print("no session_log_dir configured and none given")
        raise SystemExit(1)
    n = sync_once(d)
    git_commit(d)
    print(f"synced {n} file(s) -> {d}")
