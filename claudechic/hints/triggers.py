"""Custom trigger conditions for the hints pipeline.

Contains trigger implementations beyond the basic AlwaysTrue.
Each trigger checks disk/config state and returns bool.

LEAF MODULE: stdlib only. No imports from workflow_engine/, checks/, or guardrails/.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from claudechic.hints.state import ProjectState

logger = logging.getLogger(__name__)

# Package context directory (relative to this file)
_PKG_CONTEXT_DIR = Path(__file__).resolve().parent.parent / "context"


class ContextDocsDrift:
    """Trigger: package context/ docs differ from .claude/rules/ copies.

    Logic:
    1. For each .md file in the package's context/ directory, check if a
       file with the same name exists in .claude/rules/.
    2. If NO context docs exist in .claude/rules/ at all, do NOT trigger.
       The user hasn't run /onboarding yet -- the welcome screen suggests it.
    3. If at least one context doc exists AND any file's content differs
       from the package version, trigger the hint.

    Comparison uses MD5 for efficiency -- no need to read full contents
    into memory for diff. Must stay under 50ms (pipeline requirement).
    """

    @property
    def description(self) -> str:
        return "Context docs are outdated compared to package version"

    def check(self, state: ProjectState) -> bool:
        """Return True if installed context docs are outdated."""
        rules_dir = state.root / ".claude" / "rules"
        if not rules_dir.is_dir():
            return False  # No context docs installed yet

        if not _PKG_CONTEXT_DIR.is_dir():
            return False  # Package context dir missing (shouldn't happen)

        # Check which package context docs have local copies
        any_installed = False
        any_differs = False
        for pkg_file in _PKG_CONTEXT_DIR.glob("*.md"):
            local_file = rules_dir / pkg_file.name
            if not local_file.is_file():
                continue
            any_installed = True
            try:
                pkg_hash = hashlib.md5(
                    pkg_file.read_text(encoding="utf-8").encode()
                ).hexdigest()
                local_hash = hashlib.md5(
                    local_file.read_text(encoding="utf-8").encode()
                ).hexdigest()
            except OSError:
                # Can't read a file -- skip this pair, don't crash
                logger.debug(
                    "ContextDocsDrift: failed to read %s or %s",
                    pkg_file,
                    local_file,
                    exc_info=True,
                )
                continue
            if pkg_hash != local_hash:
                any_differs = True
                break  # One mismatch is enough

        # Only trigger if user has installed at least one doc AND it's outdated
        return any_installed and any_differs
