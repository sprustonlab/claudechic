"""Hide state and HideStore for the diff feature.

Pure data + protocol module. Imports nothing from ``widgets.py`` or
``screens/`` (SPECIFICATION s12.1 import directions). Owns the single
source of truth for "is this path hidden?" via ``HideState.is_hidden``;
all consumers (widgets, controller, tree's ``apply_hide``) call that
method and never read the three internal sets directly (s4 / s3.1).

User-facing wording note (s3.1): the strings ``hide_files``,
``hide_prefixes``, and ``force_visible`` are implementation terms and
must NEVER appear in any tooltip, footer-help label, empty-state text,
or other user-facing surface. This module is internal-only and never
emits user-visible strings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from .tree import to_prefix as _to_prefix  # canonical helper lives in tree.py

# Re-export for any historical callers that import _to_prefix from .hide.
__all__ = [
    "HideState",
    "HideStateProtocol",
    "HideStore",
    "HideStoreProtocol",
    "_to_prefix",
]


@dataclass
class HideState:
    """Three-set hide state for one repo within one claudechic process.

    ``hide_files`` -- individually hidden file paths. Entries never end
    with ``/``.
    ``hide_prefixes`` -- hidden directory prefixes. Entries ALWAYS end
    with ``/``. Empty prefix forbidden.
    ``force_visible`` -- per-file overrides that win against prefix
    membership but NOT against ``hide_files`` membership.

    See SPECIFICATION s5.1 for the resolution rule and s5.5.1 for the
    transition truth table.
    """

    hide_files: set[str] = field(default_factory=set)
    hide_prefixes: set[str] = field(default_factory=set)
    force_visible: set[str] = field(default_factory=set)

    def is_hidden(self, path: str) -> bool:
        """Single source of truth for visibility (SPECIFICATION s4 / s5.1).

        Resolution: a file is hidden iff ``path not in force_visible``
        AND (``path in hide_files`` OR any prefix in ``hide_prefixes``
        matches ``path``). Prefix matching is ``path.startswith(prefix)``
        only -- never substring or path-component magic.
        """
        if path in self.force_visible:
            return False
        if path in self.hide_files:
            return True
        return any(path.startswith(p) for p in self.hide_prefixes)

    def longest_matching_prefix(self, path: str) -> str | None:
        """Return the longest entry of ``hide_prefixes`` that matches
        ``path``, or ``None`` if none does.

        Exposed as a method (not direct set access) so widgets can
        compute the s7 tooltip context without reading
        ``hide_prefixes`` themselves -- s3.1 forbids ``if path in
        hide_state.*`` inside any widget. Read-only convenience.
        """
        matching = [p for p in self.hide_prefixes if path.startswith(p)]
        if not matching:
            return None
        return max(matching, key=len)


class HideStateProtocol(Protocol):
    """Type-only protocol matching the public read surface of HideState.

    Widgets type their ``hide_state`` parameter against this protocol so
    they cannot accidentally read the three internal sets directly
    (s3.1: ``if path in hide_state.*`` is forbidden in widgets).
    """

    def is_hidden(self, path: str) -> bool: ...
    def longest_matching_prefix(self, path: str) -> str | None: ...


class HideStoreProtocol(Protocol):
    """Type-only protocol matching SPECIFICATION s5.3.

    The concrete implementation is ``HideStore`` below. Widgets and
    DiffScreen accept this protocol for testability and to keep widget
    layers decoupled from the in-memory storage class (s12.1: "widgets
    take protocols").
    """

    def get(self, repo_key: Path) -> HideState: ...
    def hide_file(self, repo_key: Path, path: str) -> None: ...
    def hide_prefix(self, repo_key: Path, prefix: str) -> None: ...
    def unhide_file(self, repo_key: Path, path: str) -> None: ...
    def reset(self, repo_key: Path) -> None: ...


class HideStore:
    """App-scoped, repo-keyed in-memory hide store (SPECIFICATION s5.4).

    Single instance owned by ``ChatApp``; injected into ``DiffScreen``
    via constructor. Two ``DiffScreen`` instances with the same
    ``repo_key`` (cwd ``Path``) share their ``HideState``; different
    ``repo_key`` values are independent. All entries dropped at process
    exit -- no file persistence ("session-scoped, repo-keyed").
    """

    def __init__(self) -> None:
        self._states: dict[Path, HideState] = {}

    def get(self, repo_key: Path) -> HideState:
        """Return the existing ``HideState`` for ``repo_key`` or create
        a fresh empty one (s5.3)."""
        state = self._states.get(repo_key)
        if state is None:
            state = HideState()
            self._states[repo_key] = state
        return state

    def hide_file(self, repo_key: Path, path: str) -> None:
        """Add ``path`` to ``hide_files``; remove from ``force_visible``
        if present (s5.3)."""
        state = self.get(repo_key)
        state.hide_files.add(path)
        state.force_visible.discard(path)

    def hide_prefix(self, repo_key: Path, prefix: str) -> None:
        """Add ``prefix`` to ``hide_prefixes``; remove any
        ``force_visible`` entries whose path matches the new prefix
        (s5.3). ``prefix`` must end with ``/`` and be non-empty (s5.1);
        callers are responsible for that invariant.
        """
        state = self.get(repo_key)
        state.hide_prefixes.add(prefix)
        # Drop force_visible entries shadowed by the new prefix; they
        # would otherwise unexpectedly survive the user's d-action.
        state.force_visible = {
            p for p in state.force_visible if not p.startswith(prefix)
        }

    def unhide_file(self, repo_key: Path, path: str) -> None:
        """Independent-clauses unhide (SPECIFICATION s5.3 / s5.5.1).

        Clauses fire independently:
          - if ``path in hide_files``: remove from ``hide_files``;
          - if any prefix in ``hide_prefixes`` matches ``path``: add
            ``path`` to ``force_visible``.
        Post-condition: ``state.is_hidden(path)`` is ``False``.
        """
        state = self.get(repo_key)
        state.hide_files.discard(path)
        if any(path.startswith(p) for p in state.hide_prefixes):
            state.force_visible.add(path)

    def reset(self, repo_key: Path) -> None:
        """Clear all three sets for ``repo_key``; other repo keys
        untouched (s5.3 / s5.5)."""
        state = self.get(repo_key)
        state.hide_files.clear()
        state.hide_prefixes.clear()
        state.force_visible.clear()
