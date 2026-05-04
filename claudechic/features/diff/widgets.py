"""Diff view widgets - sidebar, main view, and file panels.

Widget layer for the diff feature. Consumes a ``DisplayTree`` produced
by ``build_tree`` + ``apply_hide``; never branches on ``sort_mode`` or
reads ``hide_files`` / ``hide_prefixes`` / ``force_visible`` directly
(SPECIFICATION s3.1). Visibility is read from ``FileNode.hidden``;
visibility-derived UI strings are computed from
``HideStateProtocol`` method calls only.
"""

import difflib
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.widgets import Label, Markdown, Static, TextArea

from claudechic.widgets.content.diff import DiffWidget
from claudechic.widgets.content.markdown_preview import MAX_PREVIEW_SIZE, PreviewToggle

from .git import FileChange, Hunk, HunkComment
from .hide import HideStateProtocol
from .tree import DisplayTree, FileNode

# Hunks larger than this will be split into smaller sub-hunks
LARGE_HUNK_THRESHOLD = 10


def _split_large_hunk(hunk: Hunk, context: int = 1) -> list[Hunk]:
    """Split a large hunk into smaller sub-hunks using difflib grouping.

    Returns the original hunk in a list if it's small or can't be split.
    """
    max_lines = max(len(hunk.old_lines), len(hunk.new_lines))
    if max_lines <= LARGE_HUNK_THRESHOLD:
        return [hunk]

    sm = difflib.SequenceMatcher(None, hunk.old_lines, hunk.new_lines)
    groups = list(sm.get_grouped_opcodes(context))

    if len(groups) <= 1:
        return [hunk]

    sub_hunks = []
    for group in groups:
        # Extract line ranges for this group
        old_start_idx = group[0][1]  # i1 of first opcode
        old_end_idx = group[-1][2]  # i2 of last opcode
        new_start_idx = group[0][3]  # j1 of first opcode
        new_end_idx = group[-1][4]  # j2 of last opcode

        sub_hunks.append(
            Hunk(
                old_start=hunk.old_start + old_start_idx,
                old_count=old_end_idx - old_start_idx,
                new_start=hunk.new_start + new_start_idx,
                new_count=new_end_idx - new_start_idx,
                old_lines=hunk.old_lines[old_start_idx:old_end_idx],
                new_lines=hunk.new_lines[new_start_idx:new_end_idx],
            )
        )

    return sub_hunks


class EditFileRequested(Message):
    """Posted when user clicks edit icon to open file in editor."""

    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path = path


class EditIcon(Static):
    """Small edit icon that opens file in editor."""

    DEFAULT_CSS = """
    EditIcon {
        width: 1;
        color: $text-muted;
    }
    EditIcon:hover {
        color: $primary;
    }
    """

    def __init__(self, path: str, **kwargs) -> None:
        super().__init__("✎", **kwargs)
        self._path = path

    def on_click(self, event) -> None:
        event.stop()
        self.post_message(EditFileRequested(Path(self._path)))


class DiffFileItem(Static):
    """A file entry in the diff sidebar. Click to scroll to that file's panel.

    When ``hidden`` is True, the item renders the **hidden render
    variant** per SPECIFICATION s7: status letter replaced by a ``.``
    dot in ``$text-muted``; path text in ``$text-muted`` with
    ``text-style: strike``; hunk count ``(N)`` in ``$text-muted`` (no
    strike). The ``.hidden-entry`` class flags the variant for CSS.
    """

    DEFAULT_CSS = """
    DiffFileItem {
        padding: 0 1;
        height: 1;
    }
    DiffFileItem Horizontal {
        height: 1;
    }
    DiffFileItem .file-label {
        width: 1fr;
    }
    """

    class Selected(Message):
        """Posted when file should be highlighted (programmatic, no scroll)."""

        def __init__(self, path: str) -> None:
            super().__init__()
            self.path = path

    class Clicked(Message):
        """Posted when file is clicked by user (should scroll)."""

        def __init__(self, path: str) -> None:
            super().__init__()
            self.path = path

    class UnhideRequested(Message):
        """Posted when a hidden DiffFileItem is clicked.

        DiffScreen handles this by calling
        ``hide_store.unhide_file(cwd, path)`` per SPECIFICATION s5.5.
        Distinct from ``Clicked`` so the controller does not have to
        branch on ``hidden`` itself.
        """

        def __init__(self, path: str) -> None:
            super().__init__()
            self.path = path

    def __init__(
        self,
        path: str,
        status: str,
        hunk_count: int,
        hidden: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.path = path
        self.status = status
        self.hunk_count = hunk_count
        self.hidden = hidden
        if hidden:
            self.add_class("hidden-entry")

    def compose(self) -> ComposeResult:
        # Show hunk count if > 1
        count_str = f" ({self.hunk_count})" if self.hunk_count > 1 else ""
        # Truncate path from front if too long (leave room for indicator + count + edit icon)
        max_path_len = 22
        display_path = self.path
        if len(display_path) > max_path_len:
            display_path = "…" + display_path[-(max_path_len - 1) :]

        if self.hidden:
            # Hidden render variant (s7): dot status, muted+strike path,
            # muted (no-strike) hunk count. EditIcon unchanged.
            label_markup = (
                f"[$text-muted].[/] "
                f"[$text-muted strike]{display_path}[/]"
                f"[$text-muted]{count_str}[/]"
            )
        else:
            # Normal status indicator -- primary color, red for deleted.
            indicator = {
                "modified": "M",
                "added": "A",
                "deleted": "D",
                "renamed": "R",
                "untracked": "U",
            }.get(self.status, "?")
            color = "$primary" if self.status != "deleted" else "$error"
            label_markup = f"[{color}]{indicator}[/] {display_path}[dim]{count_str}[/]"

        with Horizontal():
            yield Label(label_markup, classes="file-label")
            yield EditIcon(self.path)

    def set_hidden(self, hidden: bool, tooltip: str | None = None) -> None:
        """Switch between normal and hidden render variants in place.

        Called by DiffSidebar.refresh_hide() after a hide-state
        transition. Re-runs ``compose`` lazily by re-mounting the inner
        label; outer DiffFileItem instance is preserved (preserves the
        widget id and DOM identity).
        """
        if hidden == self.hidden:
            # Tooltip may still need refresh even if visibility didn't
            # flip (e.g. prefix added/removed while file remained
            # hidden via hide_files membership).
            self.tooltip = tooltip
            return
        self.hidden = hidden
        self.set_class(hidden, "hidden-entry")
        if hidden:
            # Hidden entries must not carry the active highlight (s7).
            self.remove_class("active")
        # Rebuild the inner row to pick up the new markup.
        for label in list(self.query(Label)):
            label.remove()
        for icon in list(self.query(EditIcon)):
            icon.remove()
        for hbox in list(self.query(Horizontal)):
            hbox.remove()
        # Re-mount via mount() since compose() is only called at first
        # mount; mounting the children manually applies the new render
        # variant immediately.
        count_str = f" ({self.hunk_count})" if self.hunk_count > 1 else ""
        max_path_len = 22
        display_path = self.path
        if len(display_path) > max_path_len:
            display_path = "…" + display_path[-(max_path_len - 1) :]
        if hidden:
            label_markup = (
                f"[$text-muted].[/] "
                f"[$text-muted strike]{display_path}[/]"
                f"[$text-muted]{count_str}[/]"
            )
        else:
            indicator = {
                "modified": "M",
                "added": "A",
                "deleted": "D",
                "renamed": "R",
                "untracked": "U",
            }.get(self.status, "?")
            color = "$primary" if self.status != "deleted" else "$error"
            label_markup = f"[{color}]{indicator}[/] {display_path}[dim]{count_str}[/]"
        hbox = Horizontal()
        self.mount(hbox)
        hbox.mount(Label(label_markup, classes="file-label"))
        hbox.mount(EditIcon(self.path))
        self.tooltip = tooltip

    def on_click(self) -> None:
        # Hidden -> the click means "un-hide me" (s5.5). Otherwise the
        # click means "scroll to my panel" (existing behavior).
        if self.hidden:
            self.post_message(self.UnhideRequested(self.path))
        else:
            self.post_message(self.Clicked(self.path))


def _flatten_files(tree: DisplayTree) -> list[FileNode]:
    """Yield ``FileNode``s in tree order, recursing into ``DirectoryNode``s.

    Pure helper. Used by both ``DiffSidebar`` and ``DiffView`` to walk
    the tree without re-implementing the recursion in two places.
    Order is preserved: directory mode produces a flat list whose order
    matches the visual top-to-bottom order. Alphabetical mode is
    already flat at the top level.
    """
    out: list[FileNode] = []
    for node in tree:
        if isinstance(node, FileNode):
            out.append(node)
        else:
            out.extend(_flatten_files(node.children))
    return out


def _hidden_tooltip(path: str, hide_state: HideStateProtocol) -> str:
    """Compute the s7 tooltip text for a hidden DiffFileItem.

    Per SPECIFICATION s7:
      - Hidden by ``hide_files`` only (no matching prefix):
        ``"click to un-hide"``.
      - Hidden by prefix membership (with or without simultaneous
        ``hide_files`` membership): ``"click to un-hide just this file
        (<prefix> stays hidden)"`` where ``<prefix>`` is the longest
        matching prefix.

    Reads the hide state via ``longest_matching_prefix`` only -- never
    indexes the three sets directly (s3.1).
    """
    prefix = hide_state.longest_matching_prefix(path)
    if prefix is not None:
        return f"click to un-hide just this file ({prefix} stays hidden)"
    return "click to un-hide"


class DiffSidebar(Vertical):
    """Left sidebar listing all changed files.

    Constructor takes a ``DisplayTree`` (built by ``build_tree`` and
    ``apply_hide`` upstream) and a ``HideStateProtocol`` for tooltip
    computation. Reads ``FileNode.hidden`` for visibility; never reads
    the three internal hide sets (s3.1).
    """

    DEFAULT_CSS = """
    DiffSidebar {
        width: 30;
        border-right: solid $surface-darken-1;
        padding: 1 0;
    }
    DiffSidebar .section-header {
        padding: 0 1;
        text-style: bold;
        margin-bottom: 1;
    }
    """

    def __init__(
        self,
        tree: DisplayTree,
        hide_state: HideStateProtocol,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._tree = tree
        self._hide_state = hide_state
        self._active_path: str | None = None

    @property
    def display_tree(self) -> DisplayTree:
        """Current DisplayTree reference (read-only).

        Named ``display_tree`` rather than ``tree`` to avoid shadowing
        ``DOMNode.tree`` (Textual's per-node debug tree).
        """
        return self._tree

    def compose(self) -> ComposeResult:
        yield Label("Changed Files", classes="section-header")
        for file_node in _flatten_files(self._tree):
            change = file_node.file_change
            tooltip = (
                _hidden_tooltip(change.path, self._hide_state)
                if file_node.hidden
                else None
            )
            item = DiffFileItem(
                change.path,
                change.status,
                len(change.hunks),
                hidden=file_node.hidden,
                id=_path_to_id(change.path),
            )
            if tooltip is not None:
                item.tooltip = tooltip
            yield item

    def set_active(self, path: str) -> None:
        """Highlight the active file in the sidebar."""
        if self._active_path and (
            old_item := self.query_one_optional(
                f"#{_path_to_id(self._active_path)}", DiffFileItem
            )
        ):
            old_item.remove_class("active")
        self._active_path = path
        if new_item := self.query_one_optional(f"#{_path_to_id(path)}", DiffFileItem):
            # Hidden entries never carry the active class (s7).
            if not new_item.hidden:
                new_item.add_class("active")

    def refresh_hide(self) -> None:
        """Re-read each ``FileNode.hidden`` and apply the s7 render
        variant + tooltip to the corresponding ``DiffFileItem``.

        Called by the controller (DiffScreen) after every hide-state
        transition (s5.5.2 update fan-out). Parent->child orchestration:
        DiffScreen invokes this on its child sidebar; sibling-to-sibling
        imperative updates are forbidden, this is not one.
        """
        for file_node in _flatten_files(self._tree):
            change = file_node.file_change
            item = self.query_one_optional(f"#{_path_to_id(change.path)}", DiffFileItem)
            if item is None:
                continue
            tooltip = (
                _hidden_tooltip(change.path, self._hide_state)
                if file_node.hidden
                else None
            )
            item.set_hidden(file_node.hidden, tooltip=tooltip)

    def reorder(self, new_tree: DisplayTree) -> None:
        """Re-order existing ``DiffFileItem`` children to match
        ``new_tree``'s order.

        Per SPECIFICATION s10: in-place reorder via ``move_child``;
        children are NOT re-mounted. Updates the internal ``_tree``
        reference and refreshes hide state on each row (the new tree
        already carries fresh ``hidden`` flags from ``apply_hide``).
        """
        self._tree = new_tree
        ordered_paths = [n.file_change.path for n in _flatten_files(new_tree)]
        # Refresh hidden flags first so styling matches the new tree.
        self.refresh_hide()
        # Chain-reorder: move the first file just after the section
        # header, then chain each subsequent file after the previous.
        # Textual ``move_child`` requires exactly one of before/after.
        section_label = self.query_one_optional(".section-header", Label)
        prev: Static | None = section_label
        for path in ordered_paths:
            item = self.query_one_optional(f"#{_path_to_id(path)}", DiffFileItem)
            if item is None:
                continue
            if prev is None:
                # No section header found (defensive); fall back to
                # moving each item to the start.
                self.move_child(item, before=0)
            else:
                self.move_child(item, after=prev)
            prev = item


class CommentInput(TextArea):
    """Multi-line input for adding comments to hunks. Enter submits, Ctrl+J for newline."""

    BINDINGS = [
        Binding("enter", "submit", "Submit", priority=True, show=False),
        Binding("ctrl+j", "newline", "Newline", priority=True, show=False),
        Binding("escape", "cancel", "Cancel", priority=True, show=False),
    ]

    DEFAULT_CSS = """
    CommentInput {
        height: auto;
        max-height: 10;
        min-height: 3;
        max-width: 80;
        margin-top: 1;
        background: $surface;
        border: solid $primary;
    }
    """

    class CommentSubmitted(Message):
        """Posted when comment is submitted (Enter pressed)."""

        def __init__(self, comment: str) -> None:
            super().__init__()
            self.comment = comment

    class CommentCancelled(Message):
        """Posted when comment is cancelled (Escape pressed)."""

    def __init__(self, value: str = "", **kwargs) -> None:
        kwargs.setdefault("soft_wrap", True)
        kwargs.setdefault("show_line_numbers", False)
        super().__init__(**kwargs)
        if value:
            self.text = value

    def action_submit(self) -> None:
        self.post_message(self.CommentSubmitted(self.text))

    def action_newline(self) -> None:
        self.insert("\n")

    def action_cancel(self) -> None:
        self.post_message(self.CommentCancelled())


class CommentLabel(Static):
    """Label showing a saved comment on a hunk."""

    DEFAULT_CSS = """
    CommentLabel {
        margin-top: 1;
        padding: 0 1;
        color: $warning;
    }
    """


class HunkSeparator(Static):
    """Full-width horizontal rule between hunks."""

    DEFAULT_CSS = """
    HunkSeparator {
        height: 1;
        width: 100%;
        margin: 1 0;
        color: #444444;
    }
    """

    def render(self):
        return "─" * (self.size.width or 80)


class HunkWidget(Static, can_focus=True):
    """Widget displaying a single hunk with syntax-highlighted diff."""

    DEFAULT_CSS = """
    HunkWidget {
        height: auto;
        border-left: tall $panel;
        padding-left: 1;
    }
    HunkWidget.has-comment {
        border-left: tall $warning;
    }
    HunkWidget:focus {
        border-left: tall $secondary;
        background: $secondary 10%;
    }
    """

    def __init__(self, hunk: Hunk, path: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.hunk = hunk
        self.path = path
        self.comment: str | None = None
        self._input: CommentInput | None = None
        self._label: CommentLabel | None = None

    def on_mouse_down(self) -> None:
        """Focus this hunk on click."""
        self.focus()

    def compose(self) -> ComposeResult:
        old_content = "\n".join(self.hunk.old_lines)
        new_content = "\n".join(self.hunk.new_lines)
        # Use hunk size as context_lines to preserve already-trimmed context
        max_lines = max(len(self.hunk.old_lines), len(self.hunk.new_lines))
        yield DiffWidget(
            old=old_content,
            new=new_content,
            path=self.path,
            old_start=self.hunk.old_start,
            new_start=self.hunk.new_start,
            context_lines=max_lines,
        )

    @property
    def editing(self) -> bool:
        """Return True if comment input is active."""
        return self._input is not None

    def start_editing(self) -> None:
        """Show comment input below the diff."""
        if self._input is not None:
            return
        # Hide label while editing
        if self._label:
            self._label.remove()
            self._label = None
        self._input = CommentInput(
            placeholder="Add comment...",
            value=self.comment or "",
        )
        self.mount(self._input)
        self._input.focus()

    def stop_editing(self, save: bool = True) -> None:
        """Hide comment input and optionally save the comment."""
        if self._input is None:
            return
        if save:
            self.comment = self._input.text.strip() or None
            if self.comment:
                self.add_class("has-comment")
            else:
                self.remove_class("has-comment")
        self._input.remove()
        self._input = None
        # Show label with comment text
        self._update_label()
        self.focus()

    def _update_label(self) -> None:
        """Show or hide the comment label based on current comment."""
        if self._label:
            self._label.remove()
            self._label = None
        if self.comment:
            self._label = CommentLabel(f"💬 {self.comment}")
            self.mount(self._label)

    def on_comment_input_comment_submitted(
        self, event: CommentInput.CommentSubmitted
    ) -> None:
        """Handle comment submission."""
        event.stop()
        self.stop_editing(save=True)

    def on_comment_input_comment_cancelled(
        self, event: CommentInput.CommentCancelled
    ) -> None:
        """Handle comment cancellation."""
        event.stop()
        self.stop_editing(save=False)


class FileHeaderLabel(Static):
    """Clickable file header that opens file in editor."""

    DEFAULT_CSS = """
    FileHeaderLabel {
        background: $surface;
        padding: 0 1;
        text-style: bold;
        margin-bottom: 1;
    }
    FileHeaderLabel:hover {
        text-style: bold underline;
    }
    """

    def __init__(self, path: str, status: str, **kwargs) -> None:
        color = "$primary" if status != "deleted" else "$error"
        super().__init__(f"[{color}]{path}[/]", **kwargs)
        self._path = path

    def on_click(self, event) -> None:
        event.stop()
        self.post_message(EditFileRequested(Path(self._path)))


class FileDiffPanel(Vertical):
    """Panel showing all hunks for a single file."""

    DEFAULT_CSS = """
    FileDiffPanel {
        margin-bottom: 2;
        height: auto;
    }
    FileDiffPanel .md-preview {
        height: auto;
        padding: 1;
    }
    """

    def __init__(self, change: FileChange, cwd: Path | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.change = change
        self._cwd = cwd
        self._is_md = change.path.endswith(".md")
        self._preview_active = False

    def compose(self) -> ComposeResult:
        yield FileHeaderLabel(self.change.path, self.change.status)

        # Add preview toggle for markdown files
        if self._is_md:
            yield PreviewToggle(self.change.path)

        # Show each hunk as a separate widget with separators between
        # Large hunks are split into smaller sub-hunks for easier navigation
        if self.change.hunks:
            widget_idx = 0
            for hunk in self.change.hunks:
                sub_hunks = _split_large_hunk(hunk)
                for sub_hunk in sub_hunks:
                    if widget_idx > 0:
                        yield HunkSeparator()
                    yield HunkWidget(
                        sub_hunk,
                        self.change.path,
                        id=_path_to_id(self.change.path, widget_idx),
                    )
                    widget_idx += 1
        else:
            yield Label("[dim]Binary file or no diff available[/]")

        # Hidden markdown preview (only for .md files)
        if self._is_md:
            md_widget = Markdown("", classes="md-preview")
            md_widget.display = False
            yield md_widget

    def on_preview_toggle_toggled(self, event: PreviewToggle.Toggled) -> None:
        """Handle preview toggle clicks."""
        event.stop()
        if event.show_preview:
            self._show_preview()
        else:
            self._show_hunks()

    def _show_preview(self) -> None:
        """Show markdown preview, hide hunks.

        Reads the current file from disk (not the diff) so the preview reflects
        the working-tree state. Requires cwd to resolve the path; if cwd is not
        set the method is a no-op (toggle click is silently ignored).
        """
        # cwd is required to resolve the file path. If DiffScreen did not pass
        # cwd down through DiffView, this is None and we cannot read the file.
        if not self._cwd:
            return
        full_path = self._cwd / self.change.path
        try:
            if full_path.stat().st_size > MAX_PREVIEW_SIZE:
                self.app.notify(
                    "File too large for preview (> 50KB)", severity="warning"
                )
                # Reset the toggle back to [Preview] state.
                # Use r"\[Preview]" -- bare "[Preview]" is consumed as a Rich
                # markup tag and renders as empty string.
                toggle = self.query_one(PreviewToggle)
                toggle._preview_active = False
                toggle.update(r"\[Preview]")
                return
            content = full_path.read_text(encoding="utf-8")
        except (FileNotFoundError, UnicodeDecodeError):
            self.app.notify("Cannot preview file", severity="warning")
            toggle = self.query_one(PreviewToggle)
            toggle._preview_active = False
            toggle.update(r"\[Preview]")
            return

        # Hide hunks and separators
        for hunk in self.query(HunkWidget):
            hunk.display = False
        for sep in self.query(HunkSeparator):
            sep.display = False

        # Show markdown preview
        md_widget = self.query_one(".md-preview", Markdown)
        md_widget.update(content)
        md_widget.display = True
        self._preview_active = True

    def _show_hunks(self) -> None:
        """Show hunks, hide markdown preview."""
        for hunk in self.query(HunkWidget):
            hunk.display = True
        for sep in self.query(HunkSeparator):
            sep.display = True

        md_widget = self.query_one(".md-preview", Markdown)
        md_widget.display = False
        self._preview_active = False


_EMPTY_STATE_ID = "diff-view-empty-state"


class DiffView(VerticalScroll):
    """Main scrollable container of file diff panels with hunk navigation.

    Constructor takes a ``DisplayTree`` and produces one
    ``FileDiffPanel`` per ``FileNode`` (DirectoryNodes are recursed for
    file collection). Hidden files render as ``display: false``
    (s6.3); navigation skips them. The empty-state placeholder (s6.4)
    appears when every file is hidden.
    """

    DEFAULT_CSS = """
    DiffView {
        padding: 1;
    }
    DiffView .diff-empty-state {
        padding: 2;
        color: $text-muted;
        text-align: center;
    }
    """

    def __init__(
        self,
        tree: DisplayTree,
        cwd: Path | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._tree = tree
        self._cwd = cwd
        self._files: list[FileNode] = _flatten_files(tree)
        self._hunk_list: list[tuple[str, int]] = self._build_hunk_list(self._files)
        self._current_idx = 0

    @property
    def display_tree(self) -> DisplayTree:
        """Current DisplayTree reference (read-only).

        Named ``display_tree`` rather than ``tree`` to avoid shadowing
        ``DOMNode.tree`` (Textual's per-node debug tree).
        """
        return self._tree

    @staticmethod
    def _build_hunk_list(files: list[FileNode]) -> list[tuple[str, int]]:
        """Build the flat list of focus keys ``(path, hunk_idx)``.

        Skips files where ``FileNode.hidden`` is True so j/k navigation
        does not visit hidden panels (s6.3). Each large hunk contributes
        ``len(_split_large_hunk(hunk))`` focus keys (one per sub-hunk).
        Binary files (no hunks) get a single entry with ``hunk_idx ==
        -1``.
        """
        keys: list[tuple[str, int]] = []
        for file_node in files:
            if file_node.hidden:
                continue
            change = file_node.file_change
            if change.hunks:
                widget_idx = 0
                for hunk in change.hunks:
                    sub_hunk_count = len(_split_large_hunk(hunk))
                    for _ in range(sub_hunk_count):
                        keys.append((change.path, widget_idx))
                        widget_idx += 1
            else:
                keys.append((change.path, -1))
        return keys

    def compose(self) -> ComposeResult:
        if not self._files:
            yield Label("[dim]No changes to display[/]")
            return

        for file_node in self._files:
            change = file_node.file_change
            panel = FileDiffPanel(
                change, cwd=self._cwd, id=f"panel-{_path_to_hex(change.path)}"
            )
            if file_node.hidden:
                panel.display = False
            yield panel

    def on_mount(self) -> None:
        """Focus the first visible hunk on mount, or the empty-state
        placeholder if every file is hidden."""
        if not self._hunk_list:
            self._show_empty_state()
        else:
            self._focus_idx(0)

    # ── Visibility & focus contract (s6.1, s6.2) ─────────────────────

    def current_focus_key(self) -> tuple[str, int] | None:
        """Return the currently focused ``(path, hunk_idx)`` pair, or
        ``None`` when nothing is focused (e.g. empty-state)."""
        if not self._hunk_list or self._current_idx >= len(self._hunk_list):
            return None
        return self._hunk_list[self._current_idx]

    def first_focus_key(self) -> tuple[str, int] | None:
        """Return the first visible focus key, or ``None`` if every
        file is hidden.

        Used by the controller's ``r``-from-empty-state carve-out
        (SPECIFICATION s6.2): when the user resets hides while in the
        empty-state placeholder, focus moves to the first hunk of the
        first visible file. Exposed as a public read so DiffScreen
        does not have to index ``_hunk_list`` directly.
        """
        return self._hunk_list[0] if self._hunk_list else None

    def set_focus_key(self, key: tuple[str, int]) -> None:
        """Focus the hunk identified by ``key``, if it is in the
        currently visible hunk list."""
        try:
            idx = self._hunk_list.index(key)
        except ValueError:
            return
        self._focus_idx(idx)

    def next_visible_after(self, key: tuple[str, int]) -> tuple[str, int] | None:
        """Return the smallest ``(path, hunk_idx)`` strictly greater
        (in list order) than ``key``, or ``None`` if there is none."""
        try:
            idx = self._hunk_list.index(key)
        except ValueError:
            # ``key`` is no longer visible; find the first key whose
            # original list-position would have been after the previous
            # location of ``key``. Fall back to the first visible.
            return self._hunk_list[0] if self._hunk_list else None
        if idx + 1 < len(self._hunk_list):
            return self._hunk_list[idx + 1]
        return None

    def prev_visible_before(self, key: tuple[str, int]) -> tuple[str, int] | None:
        """Return the largest ``(path, hunk_idx)`` strictly less (in
        list order) than ``key``, or ``None`` if there is none."""
        try:
            idx = self._hunk_list.index(key)
        except ValueError:
            return self._hunk_list[-1] if self._hunk_list else None
        if idx > 0:
            return self._hunk_list[idx - 1]
        return None

    # ── Hide / sort fan-out ─────────────────────────────────────────

    def refresh_hide(self) -> None:
        """Re-read each ``FileNode.hidden`` and toggle the matching
        ``FileDiffPanel.display`` (s6.3). Rebuilds the navigation list
        so j/k skips hidden panels.

        Empty-state placeholder is shown / removed in response to the
        new visibility set (s6.4).

        Called by DiffScreen as parent->child orchestration (allowed by
        s5.5.2; sibling-to-sibling imperative updates are forbidden).
        """
        for file_node in self._files:
            change = file_node.file_change
            panel = self.query_one_optional(
                f"#panel-{_path_to_hex(change.path)}", FileDiffPanel
            )
            if panel is not None:
                panel.display = not file_node.hidden
        self._hunk_list = self._build_hunk_list(self._files)
        if not self._hunk_list:
            self._show_empty_state()
        else:
            self._hide_empty_state()
            # Clamp focus index defensively.
            if self._current_idx >= len(self._hunk_list):
                self._current_idx = len(self._hunk_list) - 1

    def reorder(self, new_tree: DisplayTree) -> None:
        """In-place reorder of ``FileDiffPanel`` children to match
        ``new_tree``'s order (s10). Preserves all ``HunkWidget``
        instances and their attached comments (Skeptic P0).
        """
        self._tree = new_tree
        new_files = _flatten_files(new_tree)
        # Chain-move panels into the new order.
        prev: FileDiffPanel | None = None
        for file_node in new_files:
            change = file_node.file_change
            panel = self.query_one_optional(
                f"#panel-{_path_to_hex(change.path)}", FileDiffPanel
            )
            if panel is None:
                continue
            if prev is None:
                self.move_child(panel, before=0)
            else:
                self.move_child(panel, after=prev)
            prev = panel
        self._files = new_files
        self.refresh_hide()

    # ── Empty-state placeholder (s6.4) ──────────────────────────────

    def _show_empty_state(self) -> None:
        """Render the s6.4 placeholder when every file is hidden."""
        if self.query_one_optional(f"#{_EMPTY_STATE_ID}", Static) is not None:
            return
        total = len(self._files)
        placeholder_text = (
            f"All {total} files hidden.\n"
            f"Click any greyed entry in the sidebar to un-hide it,\n"
            f"or press r to reset all hides."
        )
        self.mount(
            Static(
                placeholder_text,
                id=_EMPTY_STATE_ID,
                classes="diff-empty-state",
                markup=False,
            )
        )
        # Keep keybindings working: focus the DiffView container itself
        # (s6.2 step 3).
        self.focus()

    def _hide_empty_state(self) -> None:
        """Remove the empty-state placeholder if it is mounted."""
        if existing := self.query_one_optional(f"#{_EMPTY_STATE_ID}", Static):
            existing.remove()

    # ── Focus / navigation ──────────────────────────────────────────

    def on_descendant_focus(self, event) -> None:
        """Sync ``_current_idx`` when a hunk is focused."""
        widget = event.widget
        if isinstance(widget, HunkWidget) and widget.id:
            for i, (path, hunk_idx) in enumerate(self._hunk_list):
                if hunk_idx >= 0 and _path_to_id(path, hunk_idx) == widget.id:
                    self._current_idx = i
                    self.post_message(DiffFileItem.Selected(path))
                    return

    def scroll_to_file(self, path: str) -> None:
        """Scroll to bring the specified file's panel into view."""
        for i, (p, hunk_idx) in enumerate(self._hunk_list):
            if p == path and hunk_idx >= 0:
                self._focus_idx(i)
                return

    def action_next_file(self) -> None:
        """Navigate to next visible hunk (j/down key)."""
        if self._hunk_list:
            self._focus_idx(min(self._current_idx + 1, len(self._hunk_list) - 1))

    def action_prev_file(self) -> None:
        """Navigate to previous visible hunk (k/up key)."""
        if self._hunk_list:
            self._focus_idx(max(self._current_idx - 1, 0))

    def _focus_idx(self, idx: int) -> None:
        """Focus hunk at given index in ``_hunk_list``."""
        if not self._hunk_list or idx < 0 or idx >= len(self._hunk_list):
            return
        self._current_idx = idx
        path, hunk_idx = self._hunk_list[idx]
        if hunk_idx >= 0:
            hunk_id = _path_to_id(path, hunk_idx)
            if widget := self.query_one_optional(f"#{hunk_id}", HunkWidget):
                widget.focus()
        else:
            # Binary file with no hunks.
            self.post_message(DiffFileItem.Selected(path))

    def get_current_hunk_widget(self) -> HunkWidget | None:
        """Return the currently focused hunk widget (or None)."""
        if not self._hunk_list:
            return None
        path, hunk_idx = self._hunk_list[self._current_idx]
        if hunk_idx < 0:
            return None
        hunk_id = _path_to_id(path, hunk_idx)
        return self.query_one_optional(f"#{hunk_id}", HunkWidget)

    def get_comments(self) -> list[HunkComment]:
        """Collect all non-empty comments from every mounted hunk.

        Per SPECIFICATION s15: hide does NOT filter comments.
        ``display: False`` keeps the HunkWidget mounted, so its comment
        is collected here regardless of its hidden file's render state.
        Implementers must NOT add a "skip hidden" filter.
        """
        comments = []
        for hunk_widget in self.query(HunkWidget):
            if hunk_widget.comment:
                comments.append(
                    HunkComment(
                        path=hunk_widget.path,
                        hunk=hunk_widget.hunk,
                        comment=hunk_widget.comment,
                    )
                )
        return comments

    def is_editing(self) -> bool:
        """Return True if any hunk is in editing mode."""
        return any(hunk_widget.editing for hunk_widget in self.query(HunkWidget))


def _path_to_hex(path: str) -> str:
    """Encode a path to a CSS-id-safe hex string.

    Bijective with the path: ``bytes.fromhex(encoded).decode("utf-8")``
    round-trips. The hex alphabet ``[0-9a-f]+`` is a valid CSS id
    suffix, so the result is collision-free across distinct paths
    (unlike the prior sanitizer that collapsed ``/``, ``.``, and `` ``
    to ``-`` and aliased ``a/b.py`` with ``a-b-py``). See SPECIFICATION
    s13 / SPEC_APPENDIX C.8.

    Private to this module; the public encoding API is ``_path_to_id``.
    """
    return path.encode("utf-8").hex()


def _path_to_id(path: str, hunk_idx: int | None = None) -> str:
    """Build a DOM id for a path-keyed widget.

    Returns ``f"hunk-{encoded}-{hunk_idx}"`` when ``hunk_idx`` is given,
    else ``f"sidebar-{encoded}"``. Encoding is via ``_path_to_hex``;
    matches SPECIFICATION s13 verbatim.
    """
    encoded = _path_to_hex(path)
    return (
        f"hunk-{encoded}-{hunk_idx}" if hunk_idx is not None else f"sidebar-{encoded}"
    )
