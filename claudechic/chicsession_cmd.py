"""Command handler for /chicsession slash command.

Subcommands:
    /chicsession save <name>      — Snapshot all active agents
    /chicsession list              — Show available chicsessions
    /chicsession restore <name>   — Restore all agents from a chicsession
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

    if subcommand == "list":
        _handle_list(app)
        return True

    if subcommand == "restore":
        name = parts[2] if len(parts) > 2 else None
        if not name:
            app.notify("Usage: /chicsession restore <name>", severity="error")
            return True
        app.run_worker(_handle_restore(app, name))
        return True

    _show_usage(app)
    return True


def _show_usage(app: ChatApp) -> None:
    """Display chicsession usage help."""
    from claudechic.widgets import ChatMessage

    text = (
        "**Usage:** `/chicsession <subcommand>`\n\n"
        "| Subcommand | Description |\n"
        "|------------|-------------|\n"
        "| `save <name>` | Snapshot all active agents |\n"
        "| `list` | Show available chicsessions |\n"
        "| `restore <name>` | Restore all agents from a chicsession |"
    )
    chat_view = app._chat_view
    if chat_view:
        msg = ChatMessage(text)
        msg.add_class("system-message")
        chat_view.mount(msg)
        chat_view.scroll_if_tailing()


def _get_root() -> Path:
    """Return git root if in a repo, else PWD."""
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


def _get_manager() -> ChicsessionManager:
    """Create a ChicsessionManager rooted at git root / cwd."""
    return ChicsessionManager(_get_root())


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

    cs = Chicsession(name=name, active_agent=active_name, agents=entries)
    mgr = _get_manager()
    mgr.save(cs)

    app.notify(f"Chicsession '{name}' saved — {len(entries)} agent(s)")
    log.info("Saved chicsession '%s' with %d agents", name, len(entries))


def _handle_list(app: ChatApp) -> None:
    """Show available chicsessions."""
    from claudechic.widgets import ChatMessage

    mgr = _get_manager()
    names = mgr.list_chicsessions()

    chat_view = app._chat_view
    if not chat_view:
        return

    if not names:
        msg = ChatMessage(
            "No chicsessions found. Use `/chicsession save <name>` to create one."
        )
        msg.add_class("system-message")
        chat_view.mount(msg)
        chat_view.scroll_if_tailing()
        return

    lines = [
        "**Chicsessions**\n",
        "| Name | Agents |",
        "|------|--------|",
    ]
    for cs_name in names:
        try:
            cs = mgr.load(cs_name)
            lines.append(f"| {cs_name} | {len(cs.agents)} |")
        except (ValueError, FileNotFoundError):
            lines.append(f"| {cs_name} | ? |")

    msg = ChatMessage("\n".join(lines))
    msg.add_class("system-message")
    chat_view.mount(msg)
    chat_view.scroll_if_tailing()


async def _handle_restore(app: ChatApp, name: str) -> None:
    """Load a chicsession and restore all agents."""
    mgr = _get_manager()
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
        # Skip if an agent with this name already exists
        existing = agent_mgr.find_by_name(entry.name)
        if existing:
            log.info("Agent '%s' already running, skipping restore", entry.name)
            restored += 1
            continue

        if not entry.session_id:
            log.warning("Skipping agent '%s': no session_id", entry.name)
            continue

        cwd = Path(entry.cwd) if entry.cwd else Path.cwd()

        try:
            agent = await agent_mgr.create(
                name=entry.name,
                cwd=cwd,
                resume=entry.session_id,
                switch_to=False,
            )
            await app._load_and_display_history(
                entry.session_id, cwd=cwd, agent=agent
            )
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

    msg = f"Chicsession '{name}' restored — {restored} agent(s)"
    if failed:
        msg += f", {failed} failed"
    app.notify(msg)
