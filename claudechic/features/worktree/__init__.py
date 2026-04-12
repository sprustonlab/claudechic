# ruff: noqa: I001  — git must load before commands to avoid circular import via widgets
"""Git worktree management feature.

Provides isolated feature development via git worktrees.
"""

# Public API - only what app.py needs
from claudechic.features.worktree.git import list_worktrees
from claudechic.features.worktree.commands import handle_worktree_command

__all__ = [
    "list_worktrees",
    "handle_worktree_command",
]
