"""SortMode, SortModeStore, and ``build_tree`` for the diff feature.

Imports ``tree.py`` and ``git.py``; does NOT import ``widgets.py`` or
``screens/`` (SPECIFICATION s12.1). Persistence lives at
``<repo_key>/.claudechic/diff.yaml`` -- a dedicated file with NO
co-tenancy with ``config.yaml`` in v1 (s9.2).
"""

from __future__ import annotations

import contextlib
import logging
import os
import tempfile
from pathlib import Path
from typing import Literal, Protocol, get_args

import yaml

from .git import FileChange
from .tree import DirectoryNode, DisplayTree, FileNode, to_prefix

log = logging.getLogger(__name__)


SortMode = Literal["alphabetical", "directory"]
DEFAULT_SORT_MODE: SortMode = "directory"

_VALID_SORT_MODES: frozenset[str] = frozenset(get_args(SortMode))


class SortModeStoreProtocol(Protocol):
    """Type-only protocol matching SPECIFICATION s9.1.

    Concrete implementation is ``SortModeStore``. Widgets receive the
    protocol type to keep them decoupled from on-disk persistence
    (s12.1: "widgets take protocols").
    """

    def get(self, repo_key: Path) -> SortMode: ...
    def set(self, repo_key: Path, mode: SortMode) -> None: ...


class SortModeStore:
    """Per-repo persistent sort-mode store.

    Reads/writes ``<repo_key>/.claudechic/diff.yaml`` under the
    top-level key ``sort_mode``. Reads are NOT cached across DiffScreen
    instances (SPECIFICATION s9.2); ``set`` always persists.

    Failure modes (s9.2):
      - file absent or key missing -> default ``"directory"``;
      - invalid value -> ``log.warning`` and return ``"directory"``;
      - read I/O error -> ``log.warning`` and return ``"directory"``.

    All file I/O uses ``encoding="utf-8"``.
    """

    _FILE_NAME = "diff.yaml"

    def _config_path(self, repo_key: Path) -> Path:
        return repo_key / ".claudechic" / self._FILE_NAME

    def get(self, repo_key: Path) -> SortMode:
        """Return the persisted sort mode, or ``"directory"`` on absence
        / invalidity / I/O failure."""
        path = self._config_path(repo_key)
        if not path.exists():
            return DEFAULT_SORT_MODE
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except (OSError, yaml.YAMLError):
            log.warning(
                "Failed to read %s; falling back to default sort mode",
                path,
                exc_info=True,
            )
            return DEFAULT_SORT_MODE
        if not isinstance(data, dict):
            log.warning(
                "Expected mapping in %s; falling back to default sort mode", path
            )
            return DEFAULT_SORT_MODE
        value = data.get("sort_mode")
        if value in _VALID_SORT_MODES:
            # ``value`` is one of the SortMode literals at this point;
            # the cast keeps pyright happy without runtime cost.
            return value  # type: ignore[return-value]
        if value is not None:
            log.warning(
                "Invalid sort_mode=%r in %s; falling back to default", value, path
            )
        return DEFAULT_SORT_MODE

    def set(self, repo_key: Path, mode: SortMode) -> None:
        """Persist ``mode`` atomically. Creates ``.claudechic/`` if
        absent (SPECIFICATION s9.2)."""
        if mode not in _VALID_SORT_MODES:
            # Defensive: the SortMode Literal already prevents this
            # statically, but the runtime guard makes the contract
            # explicit and protects against bad callers.
            raise ValueError(f"Invalid sort_mode: {mode!r}")
        path = self._config_path(repo_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".yaml")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                yaml.safe_dump({"sort_mode": mode}, f, default_flow_style=False)
            os.replace(tmp_path, path)
        except Exception:
            with contextlib.suppress(OSError):
                os.unlink(tmp_path)
            raise


def build_tree(changes: list[FileChange], sort_mode: SortMode) -> DisplayTree:
    """Build a DisplayTree from changes per ``sort_mode`` (SPECIFICATION s4.2).

    ``alphabetical`` -- flat list of ``FileNode``, sorted by
    ``file_change.path`` lexicographic.

    ``directory`` -- flat list at the top level whose elements are
    ``FileNode`` (for files at the repo root) and ``DirectoryNode``
    (one per unique direct parent prefix; each containing only the
    ``FileNode``s whose direct parent is that prefix). Directory order:
    lexicographic on ``prefix``. File order inside a directory:
    lexicographic on ``file_change.path``. Files at the repo root
    interleave with directories in lexicographic order on the directory
    prefix vs. the root file path.

    Untracked files participate uniformly in both modes (no special
    bucket; SPECIFICATION s4.2).

    Note on shape: ``DirectoryNode`` is type-recursively able to nest
    other ``DirectoryNode``s, but v1 ``build_tree`` produces only
    direct-parent grouping (one level). The recursive type leaves the
    door open for future deeper nesting without changing the data
    model. ``apply_hide`` already handles arbitrary nesting.
    """
    if sort_mode == "alphabetical":
        return [
            FileNode(file_change=fc) for fc in sorted(changes, key=lambda c: c.path)
        ]

    # directory mode: bucket by direct-parent prefix; root files float
    # at the top level alongside directory nodes.
    by_prefix: dict[str, list[FileChange]] = {}
    root_files: list[FileChange] = []
    for fc in changes:
        prefix = to_prefix(fc.path)
        if prefix is None:
            root_files.append(fc)
        else:
            by_prefix.setdefault(prefix, []).append(fc)

    # Build directory nodes in lexicographic prefix order, with files
    # inside each directory sorted by full path.
    dir_nodes: list[DirectoryNode] = [
        DirectoryNode(
            prefix=prefix,
            children=[
                FileNode(file_change=fc)
                for fc in sorted(by_prefix[prefix], key=lambda c: c.path)
            ],
        )
        for prefix in sorted(by_prefix)
    ]
    root_nodes: list[FileNode] = [
        FileNode(file_change=fc) for fc in sorted(root_files, key=lambda c: c.path)
    ]

    # Interleave directory nodes and root files lexicographically using
    # the prefix vs. the root path as the comparison key. This makes
    # the top-level ordering consistent with the alphabetical view --
    # users see a stable left-to-right order regardless of whether a
    # given entry is a root file or a directory.
    def sort_key(node: DirectoryNode | FileNode) -> str:
        return node.prefix if isinstance(node, DirectoryNode) else node.file_change.path

    merged: list[DirectoryNode | FileNode] = [*dir_nodes, *root_nodes]
    merged.sort(key=sort_key)
    # Cast to DisplayTree (list[DisplayNode]); the union element type
    # narrows automatically.
    return list(merged)
