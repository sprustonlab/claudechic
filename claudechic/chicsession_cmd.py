"""Command handler for /chicsession slash command.

Subcommands:
    /chicsession save <name>       — Snapshot all active agents
    /chicsession restore [name]    — Restore agents (shows picker if no name)
    /chicsession fork <new-name>   — Fork the active chicsession (duplicate
                                     each agent's transcript to a fresh id)
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from claudechic.chicsessions import (
    Chicsession,
    ChicsessionEntry,
    ChicsessionManager,
)

if TYPE_CHECKING:
    from claudechic.app import ChatApp

log = logging.getLogger(__name__)


def handle_chicsession_command(app: ChatApp, command: str) -> bool:
    """Route /chicsession subcommands. Returns True if handled."""
    parts = command.split(maxsplit=2)

    if len(parts) < 2:
        _show_usage(app)
        return True

    subcommand = parts[1]

    if subcommand == "save":
        name = parts[2] if len(parts) > 2 else None
        if not name:
            app.notify("Usage: /chicsession save <name>", severity="error")
            return True
        _handle_save(app, name)
        return True

    if subcommand == "restore":
        name = parts[2] if len(parts) > 2 else None
        if name:
            app.run_worker(_handle_restore(app, name))
        else:
            _show_restore_picker(app)
        return True

    if subcommand == "fork":
        name = parts[2] if len(parts) > 2 else None
        if not name:
            app.notify("Usage: /chicsession fork <new-name>", severity="error")
            return True
        _handle_fork(app, name)
        return True

    _show_usage(app)
    return True


def _handle_fork(app: ChatApp, new_name: str) -> None:
    """Fork the ACTIVE chicsession into a new one.

    Each agent's transcript is duplicated byte-for-byte to a fresh session
    id (so the fork carries full history yet diverges independently), and a
    new manifest is written. The current live session is left untouched.
    """
    current = getattr(app, "_chicsession_name", None)
    if not current:
        app.notify(
            "No active chicsession to fork — save one first with "
            "/chicsession save <name>",
            severity="error",
        )
        return
    mgr = _get_manager(app)
    try:
        src = mgr.load(current)
    except (FileNotFoundError, ValueError) as e:
        app.notify(str(e), severity="error")
        return
    try:
        _new_cs, forked, missing = fork_chicsession(mgr, src, new_name)
    except ValueError as e:
        app.notify(str(e), severity="error")
        return
    msg = f"Forked '{current}' → '{new_name}' ({forked} agent(s)"
    if missing:
        msg += f", {missing} without a transcript kept shared"
    msg += f"). Open it with /chicsession restore {new_name}."
    app.notify(msg)


def _find_transcript(session_id: str, home: Path | None = None) -> Path | None:
    """Locate the live JSONL transcript for a session id at
    ~/.claude-*/projects/<slug>/<session_id>.jsonl. Returns None if absent."""
    base = home if home is not None else Path.home()
    try:
        for cfg in sorted(base.glob(".claude-*")):
            proj = cfg / "projects"
            if not proj.is_dir():
                continue
            for cand in proj.glob(f"*/{session_id}.jsonl"):
                return cand
    except OSError:
        pass
    return None


def fork_chicsession(
    mgr: ChicsessionManager,
    src: Chicsession,
    new_name: str,
    home: Path | None = None,
) -> tuple[Chicsession, int, int]:
    """Duplicate ``src`` into a new chicsession ``new_name``.

    Every agent's transcript is copied byte-for-byte to a fresh UUID (same
    history, new id -> diverges on resume) and the new manifest is saved.
    Agents whose transcript can't be found keep their original id (shared
    history). Returns ``(new_chicsession, forked, missing)``. Raises
    ValueError if ``new_name`` already exists.
    """
    import shutil
    import uuid

    if new_name in mgr.list_chicsessions():
        raise ValueError(f"Chicsession '{new_name}' already exists")
    new_entries: list[ChicsessionEntry] = []
    forked = missing = 0
    for a in src.agents:
        tpath = _find_transcript(a.session_id, home)
        if tpath is None:
            new_entries.append(ChicsessionEntry(a.name, a.session_id, a.cwd))
            missing += 1
            continue
        new_id = str(uuid.uuid4())
        try:
            shutil.copy2(tpath, tpath.parent / f"{new_id}.jsonl")
        except OSError:
            new_entries.append(ChicsessionEntry(a.name, a.session_id, a.cwd))
            missing += 1
            continue
        new_entries.append(ChicsessionEntry(a.name, new_id, a.cwd))
        forked += 1
    new_cs = Chicsession(
        name=new_name,
        active_agent=src.active_agent,
        agents=new_entries,
        workflow_state=src.workflow_state,
    )
    mgr.save(new_cs)
    return new_cs, forked, missing


def _show_usage(app: ChatApp) -> None:
    """Display chicsession usage help."""
    from claudechic.widgets import ChatMessage

    text = (
        "**Usage:** `/chicsession <subcommand>`\n\n"
        "| Subcommand | Description |\n"
        "|------------|-------------|\n"
        "| `save <name>` | Snapshot all active agents |\n"
        "| `restore [name]` | Restore agents (shows picker if no name) |\n"
        "| `fork <new-name>` | Fork the active chicsession into a new one |"
    )
    chat_view = app._chat_view
    if chat_view:
        msg = ChatMessage(text)
        msg.add_class("system-message")
        chat_view.mount(msg)
        chat_view.scroll_if_tailing()


def _update_sidebar_label(
    app: ChatApp,
    name: str | None,
    workflow: str | None = None,
    phase: str | None = None,
) -> None:
    """Update the ChicsessionLabel in the sidebar."""
    from claudechic.widgets.layout.sidebar import ChicsessionLabel

    try:
        label = app.query_one("#chicsession-label", ChicsessionLabel)
        label.name_text = name or ""
        label.workflow_text = workflow or ""
        label.phase_text = phase or ""
    except Exception:
        pass  # Widget not mounted yet


def _get_root(app: ChatApp | None = None) -> Path:
    """Return the directory whose ``.chicsessions/`` holds the manifests.

    If ``session_log_dir`` / ``chicsessions_root`` is configured (see
    ``claudechic.session_log`` -- user-tier ~/.claudechic/config.yaml or a
    project's <cwd>/.claudechic/config.yaml), that single directory is used
    for every session: a flat namespace, independent of the launch dir.
    Otherwise fall back to the legacy per-project root (app._cwd, git root,
    or PWD). With NO config set, behavior is unchanged from upstream.
    """
    cwd = getattr(app, "_cwd", None) if app is not None else None
    try:
        from claudechic.session_log import chicsessions_root

        root = chicsessions_root(cwd)
        if root is not None:
            try:
                root.mkdir(parents=True, exist_ok=True)
            except OSError:
                pass
            return root
    except Exception:
        pass
    # Legacy per-launch-directory behavior:
    # Prefer the app's tracked cwd — it's set at startup from the correct dir
    if app is not None and hasattr(app, "_cwd"):
        return app._cwd
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return Path.cwd()


def _get_manager(app: ChatApp | None = None) -> ChicsessionManager:
    """Create a ChicsessionManager rooted at project root."""
    return ChicsessionManager(_get_root(app))


def _handle_save(app: ChatApp, name: str) -> None:
    """Snapshot all active agents into a chicsession."""
    agent_mgr = app.agent_mgr
    if not agent_mgr:
        app.notify("Agent manager not initialized", severity="error")
        return

    # Build entries from all active agents
    entries: list[ChicsessionEntry] = []
    for agent in agent_mgr.agents.values():
        if not agent.session_id:
            log.warning("Skipping agent '%s': no session_id yet", agent.name)
            continue
        entries.append(
            ChicsessionEntry(
                name=agent.name,
                session_id=agent.session_id,
                cwd=str(agent.cwd),
            )
        )

    if not entries:
        app.notify("No agents with sessions to save", severity="error")
        return

    # Determine active agent name
    active = agent_mgr.active
    active_name = active.name if active else entries[0].name

    # Capture workflow engine state so save doesn't destroy it
    workflow_state = None
    engine = getattr(app, "_workflow_engine", None)
    if engine is not None:
        try:
            workflow_state = engine.to_session_state()
        except Exception:
            log.debug("Failed to capture workflow state during save", exc_info=True)

    # If engine is None but a saved chicsession exists, preserve its
    # workflow_state instead of overwriting with None.  This handles the
    # restore-then-save scenario where the engine hasn't been reconstructed
    # yet but the persisted state should survive.
    mgr = _get_manager(app)
    if workflow_state is None:
        try:
            existing = mgr.load(name)
            if existing and existing.workflow_state:
                workflow_state = existing.workflow_state
        except Exception:
            pass  # File doesn't exist yet — nothing to preserve

    cs = Chicsession(
        name=name,
        active_agent=active_name,
        agents=entries,
        workflow_state=workflow_state,
    )
    mgr.save(cs)

    # Activate auto-save: future agent create/close will update this file
    app._chicsession_name = name
    _update_sidebar_label(app, name)

    app.notify(f"Chicsession '{name}' saved — {len(entries)} agent(s)")
    log.info("Saved chicsession '%s' with %d agents", name, len(entries))


def _show_restore_picker(app: ChatApp) -> None:
    """Show the chicsession picker screen."""
    from claudechic.screens import ChicsessionScreen

    root = _get_root(app)

    def on_dismiss(name: str | None) -> None:
        if name:
            app.run_worker(_handle_restore(app, name))
        if hasattr(app, "chat_input") and app.chat_input:
            app.chat_input.focus()

    app.push_screen(ChicsessionScreen(root), on_dismiss)


async def _handle_restore(app: ChatApp, name: str) -> None:
    """Load a chicsession and restore all agents."""
    mgr = _get_manager(app)
    try:
        cs = mgr.load(name)
    except FileNotFoundError:
        app.notify(f"Chicsession '{name}' not found", severity="error")
        return
    except ValueError as e:
        app.notify(str(e), severity="error")
        return

    agent_mgr = app.agent_mgr
    if agent_mgr is None:
        app.notify("Agent manager not initialized", severity="error")
        return

    restored = 0
    failed = 0
    for entry in cs.agents:
        if not entry.session_id:
            log.warning("Skipping agent '%s': no session_id", entry.name)
            continue

        cwd = Path(entry.cwd) if entry.cwd else Path.cwd()

        # If an agent with this name already exists, reconnect it to the saved session
        existing = agent_mgr.find_by_name(entry.name)
        if existing:
            try:
                await app._reconnect_agent(existing, entry.session_id)
                existing.session_id = entry.session_id
                # Clear and reload history in the chat view
                chat_view = app._chat_views.get(existing.id)
                if chat_view:
                    chat_view.clear()
                await app._load_and_display_history(
                    entry.session_id, cwd=cwd, agent=existing
                )
                restored += 1
                log.info("Reconnected existing agent '%s' to saved session", entry.name)
            except Exception as exc:
                log.warning("Failed to reconnect agent '%s': %s", entry.name, exc)
                failed += 1
            continue

        try:
            agent = await agent_mgr.create(
                name=entry.name,
                cwd=cwd,
                resume=entry.session_id,
                switch_to=False,
            )
            await app._load_and_display_history(entry.session_id, cwd=cwd, agent=agent)
            restored += 1
            log.info("Restored agent '%s' from chicsession", entry.name)
        except Exception as exc:
            log.warning("Failed to restore agent '%s': %s", entry.name, exc)
            failed += 1

    # Switch to the originally-active agent
    if cs.active_agent:
        target = agent_mgr.find_by_name(cs.active_agent)
        if target:
            agent_mgr.switch(target.id)

    # Activate auto-save: future agent create/close will update this file
    app._chicsession_name = name
    _update_sidebar_label(app, name)

    # Restore workflow engine from chicsession state
    if cs.workflow_state:
        app._restore_workflow_from_session()

    # Update sidebar with workflow/phase info (Issue #9)
    app._update_sidebar_workflow_info()

    msg = f"Chicsession '{name}' restored — {restored} agent(s)"
    if failed:
        msg += f", {failed} failed"
    app.notify(msg)


def auto_save_chicsession(app: ChatApp) -> None:
    """Re-snapshot all active agents and save to the active chicsession.

    Called from app.py hooks (on_agent_created, on_agent_closed, on_system_message)
    when ``app._chicsession_name`` is set. No-op otherwise.
    """
    name = getattr(app, "_chicsession_name", None)
    if not name:
        return

    agent_mgr = app.agent_mgr
    if not agent_mgr:
        return

    entries: list[ChicsessionEntry] = []
    for agent in agent_mgr.agents.values():
        if not agent.session_id:
            continue
        entries.append(
            ChicsessionEntry(
                name=agent.name,
                session_id=agent.session_id,
                cwd=str(agent.cwd),
            )
        )

    if not entries:
        return

    active = agent_mgr.active
    active_name = active.name if active else entries[0].name

    # Capture workflow engine state so auto-save doesn't destroy it
    workflow_state = None
    engine = getattr(app, "_workflow_engine", None)
    if engine is not None:
        try:
            workflow_state = engine.to_session_state()
        except Exception:
            log.debug(
                "Failed to capture workflow state during auto-save", exc_info=True
            )

    # If engine is None but a saved chicsession exists, preserve its
    # workflow_state instead of overwriting with None.  This handles the
    # restore-then-save scenario where the engine hasn't been reconstructed
    # yet but the persisted state should survive.
    mgr = _get_manager(app)
    if workflow_state is None:
        try:
            existing = mgr.load(name)
            if existing and existing.workflow_state:
                workflow_state = existing.workflow_state
        except Exception:
            pass  # File doesn't exist yet — nothing to preserve

    cs = Chicsession(
        name=name,
        active_agent=active_name,
        agents=entries,
        workflow_state=workflow_state,
    )
    try:
        mgr.save(cs)
        log.debug("Auto-saved chicsession '%s' (%d agents)", name, len(entries))
    except Exception as exc:
        log.warning("Failed to auto-save chicsession '%s': %s", name, exc)
