"""Runtime monkey-patches for upstream bugs.

Each patch is version-gated so it auto-disables once the upstream fix lands.
"""

import inspect
import logging

log = logging.getLogger(__name__)


def _patch_textarea_undo_crash() -> None:
    """Fix TextArea undo/redo crash (ValueError: line index out of bounds).

    In both _undo_batch() and _redo_batch(), _refresh_size() is called before
    edit.after(), which updates the cursor position. The refresh triggers a
    scrollbar update chain that reads the (now stale) cursor location, crashing
    when an undo reduces the document to fewer lines than the cursor points to.

    Fix: swap the order so edit.after() runs before _refresh_size().

    Affects: textual 7.4.0 through at least 8.2.1.
    Upstream: https://github.com/Textualize/textual — not yet fixed.
    """
    try:
        import textual
        from packaging.version import Version
    except ImportError:
        return

    version = Version(textual.__version__)

    # Once upstream ships the fix, disable this patch.
    # Bump the ceiling when the fix version is known.
    if version >= Version("9.0.0"):
        log.debug(
            "Textual %s — textarea undo patch skipped (likely fixed upstream)",
            version,
        )
        return

    from textual.widgets._text_area import TextArea

    # Check if already patched (idempotent)
    if getattr(TextArea, "_chic_undo_patched", False):
        return

    # Detect whether the bug is present by inspecting source order.
    # The bug has `_refresh_size()` BEFORE the `edit.after()` loop.
    # If the source already has the correct order, skip patching.
    try:
        src = inspect.getsource(TextArea._undo_batch)
        refresh_pos = src.index("_refresh_size")
        after_pos = src.index("edit.after")
        if after_pos < refresh_pos:
            log.debug(
                "Textual %s — textarea undo bug already fixed in source, skipping patch",
                version,
            )
            TextArea._chic_undo_patched = True
            return
    except (TypeError, ValueError, OSError):
        # Can't inspect source — apply patch defensively
        pass

    # The actual fix: for each method, we replace it with a version
    # that calls edit.after() before _refresh_size().
    from collections.abc import Sequence

    _orig_undo = TextArea._undo_batch
    _orig_redo = TextArea._redo_batch

    def _patched_undo_batch(self, edits: Sequence) -> None:
        if not edits:
            return

        old_gutter_width = self.gutter_width
        minimum_top = edits[-1].top
        maximum_old_bottom = (0, 0)
        maximum_new_bottom = (0, 0)
        for edit in reversed(edits):
            edit.undo(self)
            end_location = (
                edit._edit_result.end_location if edit._edit_result else (0, 0)
            )
            if edit.top < minimum_top:
                minimum_top = edit.top
            if end_location > maximum_old_bottom:
                maximum_old_bottom = end_location
            if edit.bottom > maximum_new_bottom:
                maximum_new_bottom = edit.bottom

        new_gutter_width = self.gutter_width
        if old_gutter_width != new_gutter_width:
            self.wrapped_document.wrap(self.wrap_width, self.indent_width)
        else:
            self.wrapped_document.wrap_range(
                minimum_top, maximum_old_bottom, maximum_new_bottom
            )

        # FIX: edit.after() BEFORE _refresh_size()
        for edit in reversed(edits):
            edit.after(self)
        self._refresh_size()
        self._build_highlight_map()
        self.post_message(self.Changed(self))
        self.update_suggestion()

    def _patched_redo_batch(self, edits: Sequence) -> None:
        if not edits:
            return

        old_gutter_width = self.gutter_width
        minimum_top = edits[0].top
        maximum_old_bottom = (0, 0)
        maximum_new_bottom = (0, 0)
        for edit in edits:
            edit.do(self, record_selection=False)
            end_location = (
                edit._edit_result.end_location if edit._edit_result else (0, 0)
            )
            if edit.top < minimum_top:
                minimum_top = edit.top
            if end_location > maximum_new_bottom:
                maximum_new_bottom = end_location
            if edit.bottom > maximum_old_bottom:
                maximum_old_bottom = edit.bottom

        new_gutter_width = self.gutter_width
        if old_gutter_width != new_gutter_width:
            self.wrapped_document.wrap(self.wrap_width, self.indent_width)
        else:
            self.wrapped_document.wrap_range(
                minimum_top,
                maximum_old_bottom,
                maximum_new_bottom,
            )

        # FIX: edit.after() BEFORE _refresh_size()
        for edit in edits:
            edit.after(self)
        self._refresh_size()
        self._build_highlight_map()
        self.post_message(self.Changed(self))
        self.update_suggestion()

    TextArea._undo_batch = _patched_undo_batch
    TextArea._redo_batch = _patched_redo_batch
    TextArea._chic_undo_patched = True
    log.debug("Textual %s — textarea undo/redo crash patch applied", version)


def apply_all() -> None:
    """Apply all monkey-patches."""
    _patch_textarea_undo_crash()
