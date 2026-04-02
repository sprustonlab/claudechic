"""Claude Chic - A stylish terminal UI for Claude Code."""

from importlib.metadata import version

# Apply monkey-patches for upstream bugs before importing anything else
from claudechic._patches import apply_all as _apply_patches
_apply_patches()

from claudechic.app import ChatApp
from claudechic.theme import CHIC_THEME
from claudechic.protocols import AgentManagerObserver, AgentObserver, PermissionHandler

__all__ = [
    "ChatApp",
    "CHIC_THEME",
    "AgentManagerObserver",
    "AgentObserver",
    "PermissionHandler",
]
__version__ = version("claudechic")
