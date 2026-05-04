"""Diff review screen.

DiffScreen is the controller for the diff feature. It owns the single
``DisplayTree`` plus the per-screen focus key, and coordinates the
three orthogonal axes:

  * Source data (``list[FileChange]`` from ``get_changes``).
  * Sort mode (``SortModeStore`` -- persisted per repo).
  * Hide state (``HideStore`` -- session-scoped, repo-keyed).

After mutating either axis, the controller re-runs ``apply_hide`` on
the tree and fans the change out to ``DiffSidebar`` and ``DiffView``
via parent->child method calls (s5.5.2). Sibling-to-sibling imperative
updates are forbidden by spec.
"""

from __future__ import annotations

import logging
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from claudechic.features.diff import DiffSidebar, DiffView, get_changes
from claudechic.features.diff.git import FileChange, HunkComment
from claudechic.features.diff.hide import HideStoreProtocol
from claudechic.features.diff.sort import SortModeStoreProtocol, build_tree
from claudechic.features.diff.tree import DisplayTree, apply_hide, to_prefix
from claudechic.features.diff.widgets import DiffDirectoryItem, DiffFileItem

log = logging.getLogger(__name__)

# Width threshold below which sidebar is hidden
SIDEBAR_MIN_WIDTH = 100


class DiffScreen(Screen[list[HunkComment]]):
    """Full-screen diff viewer for reviewing uncommitted changes.

    Constructor injection per SPECIFICATION s12.2: ``hide_store`` and
    ``sort_mode_store`` are mandatory keyword-only arguments. The
    screen owns the tree; widgets receive it via constructor and refresh
    on transitions through public methods on the children.
    """

    BINDINGS = [
        # Sort + hide axis (CP3, SPECIFICATION s11)
        Binding("s", "toggle_sort", "Sort"),
        Binding("f", "hide_file", "Hide file"),
        Binding("d", "hide_dir", "Hide dir"),
        Binding("r", "reset_hides", "Reset hides"),
        # Hunk navigation (migrated from on_key for footer help)
        Binding("j", "next_hunk", "Next", show=False),
        Binding("down", "next_hunk", "Next", show=False),
        Binding("k", "prev_hunk", "Prev", show=False),
        Binding("up", "prev_hunk", "Prev", show=False),
        Binding("enter", "comment", "Comment", show=False),
        Binding("o", "comment", "Comment", show=False),
        Binding("q", "go_back", "Back", show=False),
        Binding("escape", "go_back", "Back"),
    ]

    DEFAULT_CSS = """
    DiffScreen {
        background: $background;
    }

    DiffScreen #diff-container {
        width: 100%;
        height: 100%;
    }

    DiffScreen #diff-empty {
        width: 100%;
        height: 100%;
        content-align: center middle;
        color: $text-muted;
    }

    DiffScreen #diff-sidebar.hidden {
        display: none;
    }
    """

    def __init__(
        self,
        cwd: Path,
        target: str = "HEAD",
        focus_file: str | None = None,
        *,
        hide_store: HideStoreProtocol,
        sort_mode_store: SortModeStoreProtocol,
    ) -> None:
        super().__init__()
        self._cwd = cwd
        self._target = target
        self._focus_file = focus_file
        self._hide_store = hide_store
        self._sort_mode_store = sort_mode_store
        self._changes: list[FileChange] = []
        self._tree: DisplayTree = []
        self._sidebar: DiffSidebar | None = None
        self._view: DiffView | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        # Placeholder; replaced with real content on mount.
        yield Static("Loading...", id="diff-empty")
        yield Footer()

    async def on_mount(self) -> None:
        """Fetch changes and build the diff view."""
        self._changes = await get_changes(str(self._cwd), self._target)

        # Remove placeholder.
        placeholder = self.query_one("#diff-empty")
        await placeholder.remove()

        if not self._changes:
            msg = (
                f"No changes vs {self._target}"
                if self._target != "HEAD"
                else "No uncommitted changes"
            )
            self.mount(
                Static(msg, id="diff-empty", markup=False),
                before=self.query_one(Footer),
            )
            return

        # Build the DisplayTree on mount (SPECIFICATION s4 composition
        # pipeline): build_tree -> apply_hide.
        sort_mode = self._sort_mode_store.get(self._cwd)
        hide_state = self._hide_store.get(self._cwd)
        self._tree = build_tree(self._changes, sort_mode)
        apply_hide(self._tree, hide_state)
        # Surface the active sort mode in the screen sub-title (Textual
        # chrome). User-decision per CP3 review: visible sort indicator
        # via existing chrome, no new widget. The interpolated value is
        # one of the ``SortMode`` literals -- no internal terms leak.
        self.sub_title = f"sort: {sort_mode}"

        # Mount the diff UI.
        container = Horizontal(id="diff-container")
        self._sidebar = DiffSidebar(self._tree, hide_state, id="diff-sidebar")
        # cwd is passed through so FileDiffPanel can read .md files for
        # preview; without it _show_preview() returns early.
        self._view = DiffView(self._tree, cwd=self._cwd, id="diff-view")

        self.mount(container, before=self.query_one(Footer))
        container.mount(self._sidebar)
        container.mount(self._view)

        # Focus on specific file if requested (defer to allow widgets
        # to mount).
        if self._focus_file and self._view:
            self.call_after_refresh(self._focus_on_file)
        else:
            self._view.focus()

    def _focus_on_file(self) -> None:
        """Focus on the specified file after widgets are ready."""
        if self._focus_file and self._view:
            self._view.scroll_to_file(self._focus_file)
            if self._sidebar:
                self._sidebar.set_active(self._focus_file)

    # ── Hunk navigation actions (migrated from on_key, s11) ──────────

    def action_next_hunk(self) -> None:
        if self._view and not self._view.is_editing():
            self._view.action_next_file()

    def action_prev_hunk(self) -> None:
        if self._view and not self._view.is_editing():
            self._view.action_prev_file()

    def action_comment(self) -> None:
        if self._view and not self._view.is_editing():
            hunk = self._view.get_current_hunk_widget()
            if hunk:
                hunk.start_editing()

    def action_go_back(self) -> None:
        """Return to chat with collected comments."""
        comments = self._view.get_comments() if self._view else []
        self.dismiss(comments)

    # ── Sort mode action (s9.3 / s10) ────────────────────────────────

    def action_toggle_sort(self) -> None:
        """Toggle between ``alphabetical`` and ``directory`` sort modes
        and trigger an in-place reorder (s10) -- HunkWidgets are
        preserved.
        """
        if self._view and self._view.is_editing():
            return
        if not self._sidebar or not self._view:
            return
        # Save focus key BEFORE the reorder so we can restore it
        # afterward. Defensive against ``DiffView._current_idx`` going
        # stale once children move under a new ordering (the
        # ``(path, hunk_idx)`` tuple is sort-invariant; the integer
        # index is not).
        saved_focus_key = self._view.current_focus_key()
        current = self._sort_mode_store.get(self._cwd)
        new_mode = "alphabetical" if current == "directory" else "directory"
        try:
            self._sort_mode_store.set(self._cwd, new_mode)
        except Exception:
            log.warning(
                "Failed to persist sort mode; in-memory toggle continues",
                exc_info=True,
            )
        # Rebuild the DisplayTree from the current changes; re-apply
        # hide state so FileNode.hidden flags are fresh.
        new_tree = build_tree(self._changes, new_mode)
        apply_hide(new_tree, self._hide_store.get(self._cwd))
        self._tree = new_tree
        self._sidebar.reorder(new_tree)
        self._view.reorder(new_tree)
        # Update the visible sort indicator (Textual sub_title chrome).
        self.sub_title = f"sort: {new_mode}"
        # Restore focus key. If the previously focused hunk is still
        # visible (likely -- sort doesn't change visibility), focus
        # lands back on it. If the file became hidden between snapshot
        # and restore (impossible here since we don't mutate hide
        # state), set_focus_key is a no-op.
        if saved_focus_key is not None:
            self._view.set_focus_key(saved_focus_key)

    # ── Hide actions (s5.5) ─────────────────────────────────────────

    def action_hide_file(self) -> None:
        """Hide the focused file via ``hide_store.hide_file``."""
        if self._view and self._view.is_editing():
            return
        path = self._focused_path()
        if path is None:
            return
        self._hide_store.hide_file(self._cwd, path)
        self._after_hide_change(prev_focus_path=path)

    def action_hide_dir(self) -> None:
        """Hide the focused file's parent directory.

        Per s5.1: if the focused file is at the repo root
        (``to_prefix`` returns ``None``), this is a no-op and the
        screen surfaces a transient footer hint ``no parent directory
        to hide``.
        """
        if self._view and self._view.is_editing():
            return
        path = self._focused_path()
        if path is None:
            return
        prefix = to_prefix(path)
        if prefix is None:
            self.notify("no parent directory to hide", timeout=3)
            return
        self._hide_store.hide_prefix(self._cwd, prefix)
        self._after_hide_change(prev_focus_path=path)

    def action_reset_hides(self) -> None:
        """Reset hide state for the current cwd only (s5.5).

        SPECIFICATION s6.2 carve-out: ``r`` from the empty-state
        placeholder moves focus to the first hunk of the first visible
        file. Detected by ``current_focus_key() is None`` BEFORE the
        reset (the empty-state placeholder is the only state where the
        focus key is ``None`` while the screen is mounted). The
        carve-out is local to this action -- it is intentionally NOT
        widened to ``DiffView.refresh_hide``, since that would also
        change focus on click-unhide-from-empty-state which the user
        rejected at the testing-spec checkpoint.
        """
        if self._view and self._view.is_editing():
            return
        was_empty = self._view is not None and self._view.current_focus_key() is None
        self._hide_store.reset(self._cwd)
        self._after_hide_change(prev_focus_path=self._focused_path())
        if was_empty and self._view is not None:
            first_key = self._view.first_focus_key()
            if first_key is not None:
                self._view.set_focus_key(first_key)

    # ── Click-to-unhide (s5.5) ───────────────────────────────────────

    def on_diff_file_item_unhide_requested(
        self, event: DiffFileItem.UnhideRequested
    ) -> None:
        """Handle a click on a hidden DiffFileItem -- unhide just that
        file (independent-clauses semantics, s5.3 / A2).

        Per SPECIFICATION s6.2 strict reading: click-unhide does NOT
        change focus. After ``unhide_file``, the path is visible, so
        the existing "previously focused path is still visible -- leave
        focus alone" branch in ``_after_hide_change`` falls through
        cleanly when the user wasn't focused on the unhidden file.
        """
        self._hide_store.unhide_file(self._cwd, event.path)
        self._after_hide_change(prev_focus_path=event.path)

    # ── Hide-change fan-out + focus policy (s5.5.2 / s6.2) ──────────

    def _after_hide_change(self, prev_focus_path: str | None) -> None:
        """Re-run ``apply_hide`` and fan out to children once.

        Implements SPECIFICATION s5.5.2: the controller re-runs
        ``apply_hide`` on the existing DisplayTree and triggers a
        single notification (here: a parent->child method call to each
        child, which is allowed; sibling-to-sibling imperative updates
        are forbidden by spec).

        Focus policy (s6.2 strict reading): click-unhide and ``r`` do
        NOT change focus. ``f`` and ``d`` only change focus when the
        previously focused file becomes hidden -- in that case we fall
        through to ``next_visible_after`` -> ``prev_visible_before``
        -> empty-state placeholder (whose focus is owned by
        ``DiffView`` via ``DiffView._show_empty_state``).
        """
        if not self._sidebar or not self._view:
            return
        hide_state = self._hide_store.get(self._cwd)
        apply_hide(self._tree, hide_state)
        self._sidebar.refresh_hide()
        self._view.refresh_hide()
        # Focus policy.
        if prev_focus_path is None:
            return
        # If the previously focused path is still visible, leave focus
        # alone.
        if not hide_state.is_hidden(prev_focus_path):
            return
        # After ``view.refresh_hide()`` rebuilds ``_hunk_list``, the
        # hidden file's slot is gone and ``_current_idx`` has shifted to
        # the entry that was immediately after it in the list (or is
        # clamped to the last entry if the hidden file was last).
        # ``current_focus_key()`` therefore already returns the correct
        # next-visible file -- calling ``next_visible_after`` on it
        # would advance one more step and skip a file (the "f skips 2
        # files" regression: DuplicateIds-safe reorder + index shift).
        # We only need to call ``set_focus_key`` to wire up the widget
        # focus; ``_current_idx`` is already correct.
        focus_key = self._view.current_focus_key()
        if focus_key is None:
            # Every file is hidden; ``DiffView.refresh_hide`` already
            # called ``_show_empty_state`` which focuses the container
            # so keybindings continue to fire (s6.2 step 3).
            return
        self._view.set_focus_key(focus_key)

    def _focused_path(self) -> str | None:
        """Return the path of the file owning the currently focused
        hunk, or ``None`` when nothing is focused (e.g. empty-state)."""
        if self._view is None:
            return None
        key = self._view.current_focus_key()
        if key is None:
            return None
        return key[0]

    # ── Existing handlers (sidebar click + resize) ──────────────────

    def on_diff_directory_item_hide_toggled(
        self, event: DiffDirectoryItem.HideToggled
    ) -> None:
        """Handle directory-name click: toggle hide state for the prefix.

        If the prefix is currently hidden, unhide it; otherwise hide it.
        Uses the same ``_after_hide_change`` fan-out as the keyboard
        ``d`` / ``f`` actions (s5.5.2).
        """
        if self._view and self._view.is_editing():
            return
        if event.currently_hidden:
            self._hide_store.unhide_prefix(self._cwd, event.prefix)
        else:
            self._hide_store.hide_prefix(self._cwd, event.prefix)
        self._after_hide_change(prev_focus_path=self._focused_path())

    def on_diff_directory_item_fold_toggled(
        self, event: DiffDirectoryItem.FoldToggled
    ) -> None:
        """Persist fold state when glyph is clicked.

        Visual update (file-row display toggle + glyph text) is handled
        by DiffSidebar.on_diff_directory_item_fold_toggled. This handler
        persists the new state to HideStore so it survives /diff
        close/reopen within the same session.
        """
        if event.folded:
            self._hide_store.fold_prefix(self._cwd, event.prefix)
        else:
            self._hide_store.unfold_prefix(self._cwd, event.prefix)

    def on_diff_file_item_selected(self, event: DiffFileItem.Selected) -> None:
        """Handle programmatic file selection -- update sidebar highlight."""
        if self._sidebar:
            self._sidebar.set_active(event.path)

    def on_diff_file_item_clicked(self, event: DiffFileItem.Clicked) -> None:
        """Handle user click on a (non-hidden) sidebar item -- scroll
        to file and update DiffView focus so f/d act on the clicked file."""
        if self._sidebar:
            self._sidebar.set_active(event.path)
        if self._view:
            self._view.scroll_to_file(event.path)
            self._view.set_focus_key((event.path, 0))

    def on_resize(self) -> None:
        """Hide sidebar when screen is narrow."""
        if self._sidebar:
            if self.size.width < SIDEBAR_MIN_WIDTH:
                self._sidebar.add_class("hidden")
            else:
                self._sidebar.remove_class("hidden")
