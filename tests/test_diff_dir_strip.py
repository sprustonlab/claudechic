"""Diff sidebar: strip the redundant directory prefix from file rows.

In directory-sort mode, the sidebar renders a ``DiffDirectoryItem``
header (showing the prefix, e.g. ``src/``) followed by file rows.
Historical behavior re-rendered the full relative path inside each
row (``src/foo.py``), so the directory name was visually doubled --
once in the header and once in every row beneath it.

This module pins the new behavior:

1. ``DiffFileItem`` accepts an optional ``display_path`` constructor
   parameter. When set, that string drives the rendered label.
   When not set, falls back to ``self.path`` (alphabetical sort and
   root-level files).

2. ``DiffSidebar._compose_directory`` passes the basename to children
   via ``display_path = change.path[len(node.prefix):]``. So
   ``src/foo.py`` under a ``src/`` header renders as ``foo.py``.

3. Identity (``DiffFileItem.path``) is *unchanged* -- the click
   target, scroll target, edit-icon target, hide-store key, and DOM
   id all still use the full relative path. Only the visible text
   changes. Tests reach inside the widget's internal label to
   verify what the user sees.
"""

from __future__ import annotations

from claudechic.features.diff.git import FileChange
from claudechic.features.diff.tree import DirectoryNode, FileNode
from claudechic.features.diff.widgets import DiffFileItem, DiffSidebar


# ---------------------------------------------------------------------------
# Unit: DiffFileItem display_path parameter
# ---------------------------------------------------------------------------


def test_diff_file_item_defaults_display_to_path() -> None:
    """No ``display_path`` -> render text equals the canonical path.
    Back-compat for alphabetical sort and root-level files."""
    item = DiffFileItem("src/foo.py", "modified", hunk_count=1)
    assert item._display_path == "src/foo.py"
    # Identity unchanged.
    assert item.path == "src/foo.py"


def test_diff_file_item_uses_explicit_display_path() -> None:
    """Explicit ``display_path`` -> render text uses it; identity
    keeps the canonical full path so click/scroll/edit lookups still
    resolve."""
    item = DiffFileItem(
        "src/foo.py",
        "modified",
        hunk_count=1,
        display_path="foo.py",
    )
    assert item._display_path == "foo.py"
    assert item.path == "src/foo.py"


def test_diff_file_item_label_markup_uses_display_path() -> None:
    """``_label_markup`` returns Rich markup containing the display
    path (basename), not the canonical path. Catches a regression
    where ``compose`` / ``set_hidden`` start using ``self.path``
    directly again instead of the helper."""
    item = DiffFileItem(
        "src/lib/widgets/foo.py",
        "modified",
        hunk_count=1,
        display_path="foo.py",
    )
    markup = item._label_markup()
    assert "foo.py" in markup
    # The directory prefix must NOT appear -- if it does, we are
    # rendering the full path and the dir name doubles up.
    assert "src/" not in markup
    assert "lib/" not in markup


def test_diff_file_item_label_markup_truncation_uses_display_path() -> None:
    """The 22-char truncation rule applies to the display string,
    not to the canonical path. A long full path with a short
    display_path should render the short string in full."""
    item = DiffFileItem(
        "deeply/nested/very/long/directory/structure/foo.py",
        "modified",
        hunk_count=1,
        display_path="foo.py",  # short -- should NOT get truncated
    )
    markup = item._label_markup()
    assert "foo.py" in markup
    assert "…" not in markup, (
        "short display_path should not trigger the front-truncation rule"
    )


# ---------------------------------------------------------------------------
# Integration: DiffSidebar._compose_directory passes the right prefix
# ---------------------------------------------------------------------------


def _make_sidebar_with_dir(prefix: str, file_paths: list[str]) -> DiffSidebar:
    """Build a DiffSidebar containing one DirectoryNode + given files.

    The sidebar is constructed but NOT mounted; tests inspect the
    composed children via the same generator the runtime uses, so
    they don't need a Textual app context.
    """
    from claudechic.features.diff.hide import HideState

    files = [
        FileNode(file_change=FileChange(path=p, status="modified", hunks=[]))
        for p in file_paths
    ]
    tree = [DirectoryNode(prefix=prefix, children=files)]
    return DiffSidebar(tree=tree, hide_state=HideState())


def test_compose_directory_strips_prefix_from_children() -> None:
    """End-to-end: a directory with two files yields one
    DiffDirectoryItem header and two DiffFileItems whose
    ``_display_path`` is the basename, not the full path."""
    sidebar = _make_sidebar_with_dir("src/", ["src/foo.py", "src/bar.py"])
    node = sidebar._tree[0]  # the DirectoryNode
    assert isinstance(node, DirectoryNode)

    items = list(sidebar._compose_directory(node))
    # First yield is the header; subsequent yields are file rows.
    file_items = [i for i in items if isinstance(i, DiffFileItem)]
    assert len(file_items) == 2

    by_canonical = {i.path: i for i in file_items}
    # Identity is the full path -- preserved for click/scroll/edit.
    assert set(by_canonical) == {"src/foo.py", "src/bar.py"}
    # Rendered display is the directory-relative basename.
    assert by_canonical["src/foo.py"]._display_path == "foo.py"
    assert by_canonical["src/bar.py"]._display_path == "bar.py"


def test_compose_directory_handles_nested_prefix() -> None:
    """Multi-segment prefix like ``src/lib/`` still strips correctly,
    leaving the remainder regardless of depth."""
    sidebar = _make_sidebar_with_dir("src/lib/", ["src/lib/widgets/foo.py"])
    node = sidebar._tree[0]
    assert isinstance(node, DirectoryNode)

    items = [i for i in sidebar._compose_directory(node) if isinstance(i, DiffFileItem)]
    assert len(items) == 1
    assert items[0].path == "src/lib/widgets/foo.py"
    assert items[0]._display_path == "widgets/foo.py", (
        "stripping is whole-prefix, not greedy basename -- the file's "
        "remaining sub-path under the directory header should show in full"
    )


def test_compose_file_item_no_prefix_keeps_full_path() -> None:
    """Top-level call (alphabetical sort or root-level files in
    directory mode) -- no display_prefix passed, so the file row
    keeps the full canonical path as its display string."""
    from claudechic.features.diff.hide import HideState

    file_change = FileChange(path="README.md", status="modified", hunks=[])
    file_node = FileNode(file_change=file_change)
    sidebar = DiffSidebar(tree=[file_node], hide_state=HideState())

    items = list(sidebar._compose_file_item(file_node, indent=False))
    assert len(items) == 1
    item = items[0]
    assert item.path == "README.md"
    assert item._display_path == "README.md"


def test_compose_file_item_defensive_when_path_does_not_start_with_prefix() -> None:
    """Defensive: if the file path does not actually start with the
    directory prefix (shouldn't happen in well-formed trees, but
    guard against it) the row falls back to the full path so the
    user always sees something accurate."""
    from claudechic.features.diff.hide import HideState

    file_change = FileChange(path="other/foo.py", status="modified", hunks=[])
    file_node = FileNode(file_change=file_change)
    sidebar = DiffSidebar(tree=[file_node], hide_state=HideState())

    items = list(
        sidebar._compose_file_item(file_node, indent=True, display_prefix="src/")
    )
    assert len(items) == 1
    assert items[0]._display_path == "other/foo.py", (
        "when path doesn't start with the prefix, we must NOT silently "
        "produce a misleading label -- fall back to the full canonical path"
    )


def test_compose_file_item_defensive_when_strip_would_be_empty() -> None:
    """Edge case: if the prefix matches the entire path (a directory
    node whose only child has the same exact name), stripping would
    leave an empty string. The renderer must NOT show an empty
    label -- fall back to the full path."""
    from claudechic.features.diff.hide import HideState

    file_change = FileChange(path="src/", status="modified", hunks=[])
    file_node = FileNode(file_change=file_change)
    sidebar = DiffSidebar(tree=[file_node], hide_state=HideState())

    items = list(
        sidebar._compose_file_item(file_node, indent=True, display_prefix="src/")
    )
    assert len(items) == 1
    assert items[0]._display_path == "src/"
