"""Tests for the unified ComputerInfoModal (Component F).

The former ``DiagnosticsModal`` was deleted: the modal file
``claudechic/widgets/modals/diagnostics.py`` is gone, and the JSONL
path + last-compaction summary readers were absorbed into
``ComputerInfoModal`` so a single footer button ("info") opens one
modal showing both system info and session diagnostics.

These tests cover:

* The slot-4 handler ``ChatApp.on_diagnostics_label_requested`` forwards
  ``agent.session_id`` to ``ComputerInfoModal`` so the JSONL row
  resolves to the actual session file (Seam #6).
* The unified modal renders the Session JSONL row and the Last
  Compaction section -- the absorbed readers behave exactly like the
  ones that used to live on ``DiagnosticsModal``.

Note: F is a read-only viewer, so per the Test Specification there is
no agent-side gestalt test for this component.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from claudechic import ChatApp
from claudechic.widgets.layout.footer import DiagnosticsLabel
from claudechic.widgets.modals.computer_info import ComputerInfoModal
from textual.app import App, ComposeResult


class _ModalHostApp(App):
    """Tiny app that pushes a single ComputerInfoModal on mount.

    Used by the rendering tests so we can inspect the modal's widgets
    without spinning up the full ChatApp.
    """

    def __init__(self, cwd: Path, session_id: str | None) -> None:
        super().__init__()
        self._cwd = cwd
        self._session_id = session_id

    def compose(self) -> ComposeResult:
        return iter(())

    async def on_mount(self) -> None:
        await self.push_screen(
            ComputerInfoModal(cwd=str(self._cwd), session_id=self._session_id)
        )


def _write_jsonl(path: Path, lines: list[dict]) -> None:
    """Write a list of objects as JSON-lines to *path* (utf-8)."""
    path.write_text(
        "".join(json.dumps(line) + "\n" for line in lines),
        encoding="utf-8",
    )


@pytest.mark.asyncio
async def test_f_on_diagnostics_label_requested_forwards_session_id(
    mock_sdk, tmp_path: Path
) -> None:
    """Seam #6: handler forwards `agent.session_id` to ComputerInfoModal.

    The slot-4 ``on_diagnostics_label_requested`` handler in app.py must
    construct ``ComputerInfoModal(cwd=..., session_id=agent.session_id)``
    so the modal can render the actual JSONL path. If the handler
    forgets to forward ``session_id`` the modal renders the
    ``"(no active session)"`` sentinel even though an agent is active.
    """
    sessions_dir = tmp_path / "claude-projects-key"
    sessions_dir.mkdir()
    # Create the session jsonl file so _resolve_jsonl_path returns its path.
    session_id = "11111111-2222-3333-4444-555555555555"
    (sessions_dir / f"{session_id}.jsonl").write_text("", encoding="utf-8")

    app = ChatApp()
    async with app.run_test(size=(80, 24)) as pilot:
        # ChatApp.on_mount creates an unconnected agent in the active slot.
        await pilot.pause()
        agent = app._agent
        assert agent is not None, "ChatApp should create an unconnected agent"

        # Give the agent a session id; that's what the handler must forward.
        agent.session_id = session_id

        # The modal computes the JSONL path during __init__, so the patch
        # must be active when the handler runs.
        with patch(
            "claudechic.widgets.modals.computer_info.get_project_sessions_dir",
            return_value=sessions_dir,
        ):
            label = app.query_one("#diagnostics-label", DiagnosticsLabel)
            label.post_message(DiagnosticsLabel.Requested())
            await pilot.pause()

            modals = [s for s in app.screen_stack if isinstance(s, ComputerInfoModal)]
            assert modals, (
                "ComputerInfoModal should be pushed on the screen stack "
                "after DiagnosticsLabel.Requested fires"
            )
            modal = modals[-1]

        # The session id must have been forwarded from the active agent.
        assert modal._session_id == session_id, (
            "on_diagnostics_label_requested must forward agent.session_id "
            "to ComputerInfoModal (slot 4 review M1)"
        )
        # And the JSONL row must show the real path, not the sentinel.
        assert modal._jsonl_path != "(no active session)"
        assert modal._jsonl_path.endswith(f"{session_id}.jsonl")
        assert str(sessions_dir) in modal._jsonl_path


@pytest.mark.asyncio
async def test_f_info_button_shows_session_jsonl_in_unified_modal(
    mock_sdk, tmp_path: Path
) -> None:
    """Per-feature gestalt (user-side): clicking the info button opens
    a single modal that shows both system info and the Session JSONL row.

    This is the user-visible contract of the F merge: one button, one
    modal -- no separate diagnostics popup.
    """
    sessions_dir = tmp_path / "claude-projects-key"
    sessions_dir.mkdir()
    session_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    (sessions_dir / f"{session_id}.jsonl").write_text("", encoding="utf-8")

    app = ChatApp()
    async with app.run_test(size=(80, 30)) as pilot:
        await pilot.pause()
        agent = app._agent
        assert agent is not None
        agent.session_id = session_id

        with patch(
            "claudechic.widgets.modals.computer_info.get_project_sessions_dir",
            return_value=sessions_dir,
        ):
            label = app.query_one("#diagnostics-label", DiagnosticsLabel)
            label.post_message(DiagnosticsLabel.Requested())
            await pilot.pause()

            modals = [s for s in app.screen_stack if isinstance(s, ComputerInfoModal)]
            assert modals, "Clicking the info button must open ComputerInfoModal"
            modal = modals[-1]

            # The unified modal renders system rows AND the session row.
            from textual.widgets import Static

            label_widgets = list(modal.query(".info-label"))
            value_widgets = list(modal.query(".info-value"))
            info: dict[str, str] = {}
            for lbl, val in zip(label_widgets, value_widgets, strict=True):
                if not isinstance(lbl, Static) or not isinstance(val, Static):
                    continue
                key = lbl.render().plain.strip().rstrip(":")
                info[key] = val.render().plain.strip()

            # System rows still present (consolidation, not replacement).
            for system_key in ("Host", "OS", "Python", "CWD"):
                assert system_key in info, (
                    f"Unified modal should still show system row {system_key!r}"
                )
                assert info[system_key], f"{system_key} row must be non-empty"

            # The absorbed Session JSONL row is present and shows a real path.
            assert "Session JSONL" in info, (
                "Unified modal must show absorbed Session JSONL row"
            )
            assert info["Session JSONL"] != "(no active session)"
            assert info["Session JSONL"].endswith(f"{session_id}.jsonl")

            # Last Compaction is rendered as a scrollable section.
            scroll_titles = [
                w.render().plain.strip()
                for w in modal.query(".scroll-section-title")
                if isinstance(w, Static)
            ]
            assert "Last Compaction" in scroll_titles, (
                "Unified modal must show absorbed Last Compaction section"
            )


@pytest.mark.asyncio
async def test_f_computer_info_modal_renders_session_jsonl_path(
    tmp_path: Path,
) -> None:
    """Direct render test: with a session id and a real sessions dir,
    the Session JSONL row shows the actual file path -- never the
    "(no active session)" sentinel.
    """
    sessions_dir = tmp_path / "claude-projects-key"
    sessions_dir.mkdir()
    session_id = "12345678-1234-1234-1234-1234567890ab"
    expected = sessions_dir / f"{session_id}.jsonl"
    expected.write_text("", encoding="utf-8")

    with patch(
        "claudechic.widgets.modals.computer_info.get_project_sessions_dir",
        return_value=sessions_dir,
    ):
        app = _ModalHostApp(cwd=tmp_path, session_id=session_id)
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            modal = next(
                s for s in app.screen_stack if isinstance(s, ComputerInfoModal)
            )

            from textual.widgets import Static

            label_widgets = list(modal.query(".info-label"))
            value_widgets = list(modal.query(".info-value"))
            info: dict[str, str] = {}
            for lbl, val in zip(label_widgets, value_widgets, strict=True):
                if not isinstance(lbl, Static) or not isinstance(val, Static):
                    continue
                key = lbl.render().plain.strip().rstrip(":")
                info[key] = val.render().plain.strip()

            assert "Session JSONL" in info
            jsonl_value = info["Session JSONL"]
            assert jsonl_value != "(no active session)", (
                "JSONL row should resolve to a real path when session_id is supplied"
            )
            assert jsonl_value == str(expected), (
                f"JSONL row should equal the resolved path; got {jsonl_value!r}"
            )


@pytest.mark.asyncio
async def test_f_computer_info_modal_renders_last_compaction_section(
    tmp_path: Path,
) -> None:
    """The absorbed last-compaction reader works: when the session
    JSONL contains an ``isCompactSummary`` line, the Last Compaction
    section renders the most recent summary text. This is a
    verbatim port from the deleted ``DiagnosticsModal`` -- it must
    not have lost behaviour during the merge.
    """
    sessions_dir = tmp_path / "claude-projects-key"
    sessions_dir.mkdir()
    session_id = "feedface-dead-beef-cafe-babe1234abcd"
    jsonl_path = sessions_dir / f"{session_id}.jsonl"

    summary_text = "Compacted: removed 42 stale tool uses to free context."
    _write_jsonl(
        jsonl_path,
        [
            {"type": "user", "message": {"content": "hello"}},
            {
                "type": "user",
                "isCompactSummary": True,
                "message": {"content": "OLD summary -- should be overwritten"},
            },
            {"type": "assistant", "message": {"content": "ack"}},
            {
                "type": "user",
                "isCompactSummary": True,
                "message": {"content": summary_text},
            },
        ],
    )

    with patch(
        "claudechic.widgets.modals.computer_info.get_project_sessions_dir",
        return_value=sessions_dir,
    ):
        app = _ModalHostApp(cwd=tmp_path, session_id=session_id)
        async with app.run_test(size=(80, 30)) as pilot:
            await pilot.pause()
            modal = next(
                s for s in app.screen_stack if isinstance(s, ComputerInfoModal)
            )

            # The reader stored the most recent summary on the modal.
            assert modal._compact_summary == summary_text, (
                "Last-compaction reader must keep only the most recent "
                "isCompactSummary entry (verbatim port from DiagnosticsModal)"
            )

            # The Last Compaction section is rendered with the summary text.
            from textual.widgets import Static

            scroll_titles = [
                w.render().plain.strip()
                for w in modal.query(".scroll-section-title")
                if isinstance(w, Static)
            ]
            assert "Last Compaction" in scroll_titles, (
                "Modal must render a Last Compaction scroll section"
            )

            scroll_contents = [
                w.render().plain
                for w in modal.query(".scroll-section-content")
                if isinstance(w, Static)
            ]
            assert any(summary_text in c for c in scroll_contents), (
                f"Last Compaction section must contain the summary text; "
                f"got contents={scroll_contents!r}"
            )
