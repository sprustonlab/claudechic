"""DisplayTree types and ``apply_hide`` for the diff feature.

Pure-data module. Imports ``FileChange`` from ``git.py``; uses
``HideState`` only as a type-checker reference (TYPE_CHECKING). Does
NOT import from ``widgets.py`` or ``screens/`` (per SPECIFICATION
s12.1 import directions).

Source-of-truth contract (SPECIFICATION s4): ``HideState.is_hidden`` is
the only visibility predicate. ``apply_hide`` calls it; no consumer in
this module (or any widget) reads ``hide_files`` / ``hide_prefixes`` /
``force_visible`` directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .git import FileChange

if TYPE_CHECKING:
    from .hide import HideState


def to_prefix(path: str) -> str | None:
    """Return ``path``'s direct-parent prefix (always ends with ``/``).

    Returns ``None`` if ``path`` is at the repo root (no ``/``
    separator). Per SPECIFICATION s5.1: prefixes never include a
    leading ``./``; empty prefix is forbidden; path strings use forward
    slashes regardless of OS, matching ``git diff`` output.

    Canonical home for prefix derivation. ``hide.py`` and ``sort.py``
    both import this helper rather than duplicating the rule.
    """
    if "/" not in path:
        return None
    return path.rsplit("/", 1)[0] + "/"


@dataclass
class FileNode:
    """One file in the DisplayTree.

    ``hidden`` is a derived flag set by ``apply_hide``; it is never
    stored on ``FileChange`` (SPECIFICATION s3.1 forbids adding
    ``.hidden`` / ``.reviewed`` / ``.sort_position`` to ``FileChange``).
    """

    file_change: FileChange
    hidden: bool = False


@dataclass
class DirectoryNode:
    """Grouping node in directory-sort mode.

    ``prefix`` always ends with ``/`` (SPECIFICATION s2: "A 'prefix'
    always ends with ``/``"). Children may be nested ``DirectoryNode``
    or ``FileNode`` instances.
    """

    prefix: str
    children: list[DisplayNode] = field(default_factory=list)


DisplayNode = FileNode | DirectoryNode
DisplayTree = list[DisplayNode]


def apply_hide(tree: DisplayTree, hide_state: HideState) -> DisplayTree:
    """Set ``FileNode.hidden`` in-place using ``hide_state.is_hidden``.

    Walks ``tree`` and, for each ``FileNode``, sets ``hidden`` to
    ``hide_state.is_hidden(file_change.path)``. Recurses into
    ``DirectoryNode.children``. Does NOT prune nodes -- widgets decide
    rendering by reading ``FileNode.hidden`` (SPECIFICATION s4). This
    preserves ``HunkWidget`` instances under sort and hide changes
    (SPECIFICATION s10, Skeptic P0).

    Returns the same tree (in-place mutation) for fluent chaining at
    call sites.
    """
    for node in tree:
        if isinstance(node, FileNode):
            node.hidden = hide_state.is_hidden(node.file_change.path)
        else:
            apply_hide(node.children, hide_state)
    return tree
