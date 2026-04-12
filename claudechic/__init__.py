"""Claude Chic - A stylish terminal UI for Claude Code."""

from importlib.metadata import version

# Apply monkey-patches for upstream bugs before importing anything else
from claudechic._patches import apply_all as _apply_patches

_apply_patches()

from claudechic.app import ChatApp  # noqa: E402
from claudechic.protocols import (  # noqa: E402
    AgentManagerObserver,
    AgentObserver,
    PermissionHandler,
)
from claudechic.theme import CHIC_THEME  # noqa: E402

__all__ = [
    "ChatApp",
    "CHIC_THEME",
    "AgentManagerObserver",
    "AgentObserver",
    "PermissionHandler",
]
__version__ = version("claudechic")
