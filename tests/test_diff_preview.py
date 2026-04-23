"""Tests for DiffButton and Markdown preview toggle.

Coverage:
  - DiffButton posts DiffRequested when clicked (sidebar integration)
  - PreviewToggle appears only on .md panels, not .py panels
  - PreviewToggle hides hunks and shows rendered Markdown on click, and reverses on second click
  - Large .md files (> 50KB) are rejected with a toast, toggle resets to [Preview]
  - Full DiffScreen with a real git repo mounts PreviewToggle with correct region/render
  - PreviewToggle DOM region is non-zero and on-screen when mounted in FileDiffPanel
  - Rendered Markdown DOM contains MarkdownH1/MarkdownParagraph (not raw ** syntax)
  - DiffScreen passes cwd through DiffView so FileDiffPanel._cwd is not None
"""

from pathlib import Path

import pytest
from claudechic.features.diff.git import FileChange, Hunk
from claudechic.features.diff.widgets import (
    DiffSidebar,
    DiffView,
    FileDiffPanel,
    HunkWidget,
)
from claudechic.widgets.content.markdown_preview import PreviewToggle
from claudechic.widgets.layout.sidebar import DiffButton, FilesSection
from textual.app import App, ComposeResult


class WidgetTestApp(App):
    """Minimal app for testing individual widgets."""

    def __init__(self, widget_factory):
        super().__init__()
        self._widget_factory = widget_factory

    def compose(self) -> ComposeResult:
        yield self._widget_factory()


# ---------------------------------------------------------------------------
# Test 7 Part A: DiffButton posts DiffRequested
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_diff_button_posts_diff_requested():
    """DiffButton click posts DiffRequested message."""
    messages_received = []

    class TestApp(App):
        def compose(self) -> ComposeResult:
            yield FilesSection()

        def on_diff_button_diff_requested(self, event: DiffButton.DiffRequested):
            messages_received.append(event)

    app = TestApp()
    async with app.run_test(size=(120, 40)) as pilot:
        # FilesSection should contain a DiffButton
        diff_btn = app.query_one("#diff-btn", DiffButton)
        assert diff_btn is not None

        # Click the DiffButton
        await pilot.click(DiffButton)
        assert len(messages_received) == 1


# ---------------------------------------------------------------------------
# Test 7 Part B: Preview toggle in DiffScreen
# ---------------------------------------------------------------------------


def _make_changes(tmp_path: Path) -> list[FileChange]:
    """Create a FileChange list with one .md file and one .py file."""
    # Write a real .md file
    md_file = tmp_path / "README.md"
    md_file.write_text("# Hello\n\nThis is a test markdown file.\n", encoding="utf-8")

    # Write a real .py file
    py_file = tmp_path / "main.py"
    py_file.write_text("print('hello')\n", encoding="utf-8")

    md_change = FileChange(
        path="README.md",
        status="modified",
        hunks=[
            Hunk(
                old_start=1,
                old_count=2,
                new_start=1,
                new_count=3,
                old_lines=["# Hello", ""],
                new_lines=["# Hello", "", "This is a test markdown file."],
            )
        ],
    )
    py_change = FileChange(
        path="main.py",
        status="modified",
        hunks=[
            Hunk(
                old_start=1,
                old_count=1,
                new_start=1,
                new_count=1,
                old_lines=["print('hi')"],
                new_lines=["print('hello')"],
            )
        ],
    )
    return [md_change, py_change]


@pytest.mark.asyncio
async def test_diff_button_and_md_preview_toggle(tmp_path: Path):
    """Preview toggle shows/hides markdown vs hunks for .md files."""
    changes = _make_changes(tmp_path)

    class DiffTestApp(App):
        """App that directly mounts DiffView and DiffSidebar with injected changes."""

        def compose(self) -> ComposeResult:
            from textual.containers import Horizontal

            with Horizontal():
                yield DiffSidebar(changes, id="diff-sidebar")
                yield DiffView(changes, cwd=tmp_path, id="diff-view")

    app = DiffTestApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        # The .md file's FileDiffPanel should have a PreviewToggle
        md_panel = app.query_one("#panel-README-md", FileDiffPanel)
        preview_toggle = md_panel.query_one(PreviewToggle)
        assert preview_toggle is not None

        # The .py file's panel should NOT have a PreviewToggle
        py_panel = app.query_one("#panel-main-py", FileDiffPanel)
        py_toggles = py_panel.query(PreviewToggle)
        assert len(py_toggles) == 0

        # Hunks should be visible initially
        md_hunks = md_panel.query(HunkWidget)
        assert len(md_hunks) > 0
        for hunk in md_hunks:
            assert hunk.display is True

        # Click [Preview] toggle
        await pilot.click(PreviewToggle)
        await pilot.pause()

        # After clicking Preview: hunks should be hidden
        for hunk in md_panel.query(HunkWidget):
            assert hunk.display is False

        # Markdown widget should be visible
        md_preview = md_panel.query_one(".md-preview")
        assert md_preview.display is True

        # Click [Diff] toggle (same button, now labeled [Diff])
        await pilot.click(PreviewToggle)
        await pilot.pause()

        # Hunks should be visible again
        for hunk in md_panel.query(HunkWidget):
            assert hunk.display is True

        # Markdown preview should be hidden
        md_preview = md_panel.query_one(".md-preview")
        assert md_preview.display is False


# ---------------------------------------------------------------------------
# Test 8: Large file rejection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_md_preview_rejects_large_files(tmp_path: Path):
    """Preview toggle rejects .md files > 50KB with a toast."""
    from claudechic.widgets.content.markdown_preview import PreviewToggle

    # Write a .md file > 50KB
    md_file = tmp_path / "BIGFILE.md"
    md_file.write_text("x" * (51 * 1024), encoding="utf-8")

    big_change = FileChange(
        path="BIGFILE.md",
        status="modified",
        hunks=[
            Hunk(
                old_start=1,
                old_count=1,
                new_start=1,
                new_count=1,
                old_lines=["old content"],
                new_lines=["x" * 100],
            )
        ],
    )

    class DiffTestApp(App):
        def compose(self) -> ComposeResult:
            from textual.containers import Horizontal

            with Horizontal():
                yield DiffSidebar([big_change], id="diff-sidebar")
                yield DiffView([big_change], cwd=tmp_path, id="diff-view")

    app = DiffTestApp()
    async with app.run_test(size=(120, 40), notifications=True) as pilot:
        await pilot.pause()

        panel = app.query_one("#panel-BIGFILE-md", FileDiffPanel)
        panel.query_one(PreviewToggle)

        # Click [Preview] on the large file
        await pilot.click(PreviewToggle)
        await pilot.pause()

        # Hunks should still be visible (preview NOT activated)
        for hunk in panel.query(HunkWidget):
            assert hunk.display is True

        # Check that a notification was sent with "too large"
        assert len(app._notifications) > 0
        assert any("too large" in str(n.message).lower() for n in app._notifications)


# ---------------------------------------------------------------------------
# Test: Full DiffScreen with real git repo -- PreviewToggle visible for .md
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_diffscreen_shows_preview_toggle_for_md(tmp_path: Path):
    """Full DiffScreen end-to-end: PreviewToggle exists, is visible, and renders correctly.

    Uses a real git repo (init + commit + modify) so get_changes runs the actual
    git subprocess. Verifies that the toggle has a non-zero region and renders
    '[Preview]' text -- catching the Rich markup escaping bug where '[Preview]'
    was consumed as an unknown tag and rendered as an empty string (width=2).
    """
    import subprocess

    from claudechic.screens.diff import DiffScreen

    cwd = tmp_path
    # Init git repo
    subprocess.run(["git", "init"], cwd=str(cwd), capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=str(cwd),
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=str(cwd),
        capture_output=True,
    )

    md_file = cwd / "readme.md"
    md_file.write_text("# Hello\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=str(cwd), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=str(cwd),
        capture_output=True,
    )

    # Modify the .md file so it shows up as a diff
    md_file.write_text("# Hello\n\n**bold text**\n", encoding="utf-8")

    class TestApp(App):
        def compose(self) -> ComposeResult:
            from textual.widgets import Label

            yield Label("")  # empty placeholder

        async def on_mount(self) -> None:
            await self.push_screen(DiffScreen(cwd, "HEAD"))

    app = TestApp()
    async with app.run_test(size=(120, 40)) as pilot:
        # DiffScreen.on_mount calls get_changes (async git subprocess) then mounts
        # widgets, so we need multiple pauses to let everything settle.
        for _ in range(6):
            await pilot.pause()

        screen = pilot.app.screen
        print(f"\nActive screen type: {type(screen).__name__}")

        panels = screen.query(FileDiffPanel)
        print(f"FileDiffPanels found: {[p.change.path for p in panels]}")

        md_panels = [p for p in panels if p.change.path.endswith(".md")]
        assert len(md_panels) > 0, (
            f"No .md panels found! All panels: {[p.change.path for p in panels]}"
        )

        md_panel = md_panels[0]
        print(f"md_panel._cwd: {md_panel._cwd}")
        print(f"md_panel._is_md: {md_panel._is_md}")

        toggles = md_panel.query(PreviewToggle)
        print(f"PreviewToggle count in md_panel: {len(toggles)}")
        assert len(toggles) > 0, (
            f"PreviewToggle NOT found in {md_panel.change.path} panel!"
        )

        toggle = toggles[0]
        rendered = str(toggle.render())
        print(f"Toggle region: {toggle.region}")
        print(f"Toggle render(): {rendered!r}")
        print(f"Toggle display: {toggle.display}")
        print(f"Toggle visible: {toggle.visible}")
        print(f"Toggle parent type: {type(toggle.parent).__name__}")

        assert toggle.display is True, f"Toggle display={toggle.display}"
        assert toggle.region.height > 0, f"Toggle has zero height: {toggle.region}"
        assert toggle.region.width > 0, (
            f"Toggle has zero width: {toggle.region} -- likely Rich markup bug"
        )
        assert toggle.region.y < 40, f"Toggle off-screen at y={toggle.region.y}"
        assert "[Preview]" in rendered, (
            f"Toggle renders empty/wrong content: {rendered!r}\n"
            "Check: is '[Preview]' being consumed as Rich markup?"
        )


# ---------------------------------------------------------------------------
# Test: PreviewToggle DOM visibility check (position, display, region)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_preview_toggle_visible_in_dom(tmp_path: Path):
    """PreviewToggle must exist in DOM, be visible, and have a non-zero on-screen region.

    Directly mounts FileDiffPanel (no git required). Checks display, visible,
    region dimensions, on-screen position, and that render() produces '[Preview]'
    literal text. The region width=0 / empty-render failure mode indicates the
    Rich markup escaping bug (brackets consumed as markup tags).
    """
    md_file = tmp_path / "readme.md"
    md_file.write_text("# Test\n\n**bold**\n", encoding="utf-8")

    change = FileChange(
        path="readme.md",
        status="modified",
        hunks=[
            Hunk(
                old_start=1,
                old_count=1,
                new_start=1,
                new_count=3,
                old_lines=["old content"],
                new_lines=["# Test", "", "**bold**"],
            )
        ],
    )

    class TestApp(App):
        def compose(self) -> ComposeResult:
            yield FileDiffPanel(change, cwd=tmp_path)

    app = TestApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        panel = app.query_one(FileDiffPanel)

        # 1. Does PreviewToggle exist in DOM?
        toggles = panel.query(PreviewToggle)
        assert len(toggles) > 0, "PreviewToggle NOT in DOM at all!"

        toggle = toggles[0]

        # 2. Is it visible (not display:none, not hidden)?
        assert toggle.display is True, f"PreviewToggle display={toggle.display}"
        assert toggle.visible is True, f"PreviewToggle visible={toggle.visible}"
        assert not toggle.has_class("hidden"), "PreviewToggle has 'hidden' class"

        # 3. Does it have a non-zero region (not collapsed)?
        assert toggle.region.width > 0, f"PreviewToggle width=0, region={toggle.region}"
        assert toggle.region.height > 0, (
            f"PreviewToggle height=0, region={toggle.region}"
        )

        # 4. Is it on-screen (not pushed off)?
        assert toggle.region.y < 40, (
            f"PreviewToggle at y={toggle.region.y}, off-screen (height=40)!"
        )
        assert toggle.region.x < 120, (
            f"PreviewToggle at x={toggle.region.x}, off-screen (width=120)!"
        )

        # 5. Debug info
        rendered = str(toggle.render())
        print(f"\nPreviewToggle region: {toggle.region}")
        print(f"PreviewToggle render(): {rendered!r}")
        print(f"PreviewToggle parent: {toggle.parent.__class__.__name__}")
        print(
            f"PreviewToggle styles: display={toggle.styles.display}, "
            f"height={toggle.styles.height}"
        )

        # 6. Verify the rendered content actually contains "[Preview]" text
        assert "[Preview]" in rendered, (
            f"PreviewToggle renders empty or wrong content: {rendered!r}\n"
            f"Likely caused by Rich treating [Preview] as a markup tag."
        )


# ---------------------------------------------------------------------------
# Test: Preview toggle renders real markdown DOM and toggles back to diff
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_preview_toggle_renders_markdown_and_toggles_back(tmp_path: Path):
    """PreviewToggle renders markdown into a real Textual widget tree and reverts on second click.

    Verifies:
    - Initial state: hunks visible, Markdown widget hidden, toggle inactive
    - After first click: hunks hidden, Markdown visible, MarkdownH1 and
      MarkdownParagraph child widgets exist (proving actual rendering, not raw text)
    - Raw '**bold text**' syntax does NOT appear in rendered paragraph output
    - After second click: hunks visible again, Markdown hidden, toggle reset
    """
    from textual.widgets import Markdown
    from textual.widgets._markdown import MarkdownH1, MarkdownParagraph

    # Create a real .md file with rich markdown content
    md_file = tmp_path / "doc.md"
    md_file.write_text(
        "# Hello\n\n**bold text** and normal text\n",
        encoding="utf-8",
    )

    change = FileChange(
        path="doc.md",
        status="modified",
        hunks=[
            Hunk(
                old_start=1,
                old_count=1,
                new_start=1,
                new_count=3,
                old_lines=["# Old title"],
                new_lines=["# Hello", "", "**bold text** and normal text"],
            )
        ],
    )

    class PanelApp(App):
        def compose(self) -> ComposeResult:
            yield FileDiffPanel(change, cwd=tmp_path)

    app = PanelApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        panel = app.query_one(FileDiffPanel)

        # -- Initial state: diff hunks visible, preview hidden --
        toggle = panel.query_one(PreviewToggle)
        assert toggle.display is True
        assert not toggle._preview_active

        hunks = panel.query(HunkWidget)
        assert len(hunks) > 0
        for hunk in hunks:
            assert hunk.display is True

        md_widget = panel.query_one(".md-preview", Markdown)
        assert md_widget.display is False

        # -- Click [Preview]: switch to rendered markdown --
        await pilot.click(PreviewToggle)
        await pilot.pause()

        # Hunks should be hidden
        for hunk in panel.query(HunkWidget):
            assert hunk.display is False, "Hunk still visible after Preview click"

        # Markdown widget should be visible
        assert md_widget.display is True

        # Toggle label should now say [Diff]
        assert toggle._preview_active is True

        # Verify rendered DOM: Markdown widget should contain MarkdownH1 and
        # MarkdownParagraph children (not raw ** syntax)
        await pilot.pause()  # extra pause for markdown rendering
        h1_blocks = md_widget.query(MarkdownH1)
        assert len(h1_blocks) > 0, "No MarkdownH1 found -- markdown not rendered"

        paragraphs = md_widget.query(MarkdownParagraph)
        assert len(paragraphs) > 0, (
            "No MarkdownParagraph found -- markdown not rendered"
        )

        # The raw "**bold text**" should NOT appear as literal asterisks in the
        # rendered output -- it should be styled text without the ** markers
        for para in paragraphs:
            rendered = para.render()
            rendered_str = str(rendered)
            assert "**bold text**" not in rendered_str, (
                f"Raw markdown syntax found in rendered output: {rendered_str}"
            )

        # -- Click [Diff]: toggle back to diff view --
        await pilot.click(PreviewToggle)
        await pilot.pause()

        # Hunks should be visible again
        for hunk in panel.query(HunkWidget):
            assert hunk.display is True, "Hunk not restored after toggling back to Diff"

        # Markdown widget should be hidden
        assert md_widget.display is False

        # Toggle state should be back to preview-inactive
        assert toggle._preview_active is False


# ---------------------------------------------------------------------------
# Test: DiffScreen passes cwd to DiffView so PreviewToggle works
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_diffscreen_passes_cwd_to_diffview(tmp_path: Path):
    """DiffScreen must pass cwd through DiffView to FileDiffPanel.

    Uses a mocked get_changes so no real git repo is needed. Asserts that
    FileDiffPanel._cwd is not None after mount and that clicking PreviewToggle
    actually hides the hunks (proving the cwd guard in _show_preview passes).

    Without this fix: DiffView(changes, id='diff-view') -- missing cwd --
    causes FileDiffPanel._cwd=None and _show_preview() returns early silently.
    """
    from unittest.mock import AsyncMock, patch

    changes = _make_changes(tmp_path)

    # Patch get_changes to return our test data without needing a real git repo
    with patch(
        "claudechic.screens.diff.get_changes",
        new_callable=AsyncMock,
        return_value=changes,
    ):
        from claudechic.screens.diff import DiffScreen

        class ScreenTestApp(App):
            def on_mount(self):
                self.push_screen(DiffScreen(cwd=tmp_path))

        app = ScreenTestApp()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.pause()  # extra pause for async mount

            # Verify PreviewToggle exists and is visible for .md file
            screen = app.screen
            md_panel = screen.query_one("#panel-README-md", FileDiffPanel)
            toggle = md_panel.query_one(PreviewToggle)
            assert toggle.display is True

            # Verify cwd was passed through: FileDiffPanel._cwd should not be None
            assert md_panel._cwd is not None, (
                "FileDiffPanel._cwd is None -- DiffScreen did not pass cwd to DiffView"
            )

            # Click preview toggle and verify it actually works (hunks hidden)
            await pilot.click(PreviewToggle)
            await pilot.pause()

            for hunk in md_panel.query(HunkWidget):
                assert hunk.display is False, (
                    "Hunks still visible after Preview click -- cwd not propagated"
                )
