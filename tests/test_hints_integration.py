"""Integration tests: hints system running inside the real ChatApp.

Proves that ChatApp._run_hints() discovers the project-local hints/ package,
evaluates hints, and produces visible toast notifications — or gracefully
handles errors and missing packages.

Uses the same mock_sdk fixture as other ClaudeChic tests.

Strategy: start the app with mock_sdk, then manually set app._cwd to our
tmp_path and call app._run_hints() directly. This tests the real integration
code path (dynamic import, discovery, evaluate, notify → Toast) without
relying on background task timing.
"""

from __future__ import annotations

import asyncio
import json
import shutil
import sys
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from claudechic.app import ChatApp
from tests.conftest import wait_for_workers

pytestmark = [pytest.mark.asyncio, pytest.mark.timeout(30)]

# ---------------------------------------------------------------------------
# Locate the template hints source
# ---------------------------------------------------------------------------

# Look for hints/ in the claudechic repo root first, then fall back to template
_REPO_ROOT = Path(__file__).resolve().parent.parent
_HINTS_SOURCE = _REPO_ROOT / "hints"
if not _HINTS_SOURCE.is_dir():
    # Fall back to template location when running from AI_PROJECT_TEMPLATE
    _TEMPLATE_ROOT = _REPO_ROOT.parent.parent
    _HINTS_SOURCE = _TEMPLATE_ROOT / "template" / "hints"


def _install_hints(dest: Path) -> None:
    """Copy the template hints/ package into dest (the project root)."""
    shutil.copytree(_HINTS_SOURCE, dest / "hints")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestHintsInChatApp:
    """Real ChatApp E2E tests for the hints system."""

    def test_hints_source_exists(self):
        """Sanity check: template hints source is available for copying."""
        assert _HINTS_SOURCE.is_dir(), f"Missing: {_HINTS_SOURCE}"
        assert (_HINTS_SOURCE / "__init__.py").is_file()

    async def test_startup_hint_appears_as_toast(self, mock_sdk, tmp_path):
        """ChatApp discovers hints/, evaluates, and shows git-setup toast.

        A fresh tmp_path has no .git → git-setup hint (priority 1) fires.
        """
        _install_hints(tmp_path)
        app = ChatApp()

        with ExitStack() as stack:
            # Suppress the auto-fired hints-startup task from on_chat_screen_ready
            stack.enter_context(
                patch("claudechic.tasks.create_safe_task", return_value=MagicMock())
            )
            stack.enter_context(
                patch("claudechic.sessions.count_sessions", return_value=1)
            )

            async with app.run_test(size=(120, 40), notifications=True) as pilot:
                await pilot.pause()

                # Point app at our tmp_path with hints/ installed
                app._cwd = tmp_path

                # Replace real sleep with instant yield for hints pipeline
                original_sleep = asyncio.sleep

                async def fast_sleep(delay, *args, **kwargs):
                    await original_sleep(0)

                with patch.object(asyncio, "sleep", side_effect=fast_sleep):
                    await app._run_hints(is_startup=True, budget=2)

                await pilot.pause()

                # Verify: at least one notification was created
                notif_count = len(app._notifications)
                assert notif_count > 0, "No toast notifications from hints"

                # Verify: git-setup hint is among the notifications
                messages = [n.message for n in app._notifications]
                assert any("git" in m.lower() for m in messages), (
                    f"Expected git-setup hint, got: {messages}"
                )

                # Verify: Toast widgets are rendered in the DOM
                from textual.widgets._toast import Toast

                toasts = list(app.screen.query(Toast))
                assert len(toasts) > 0, "No Toast widgets found in DOM"

    async def test_no_hints_when_folder_missing(self, mock_sdk, tmp_path):
        """ChatApp with no hints/ folder → zero hint notifications."""
        app = ChatApp()

        with ExitStack() as stack:
            stack.enter_context(
                patch("claudechic.tasks.create_safe_task", return_value=MagicMock())
            )
            stack.enter_context(
                patch("claudechic.sessions.count_sessions", return_value=1)
            )

            async with app.run_test(size=(120, 40), notifications=True) as pilot:
                await pilot.pause()

                app._cwd = tmp_path

                # Call _run_hints — should return early (no hints/ dir)
                await app._run_hints(is_startup=True, budget=2)
                await pilot.pause()

                # Filter: only check for hint-related notifications
                hint_keywords = [
                    "git repo", "guardrails", "project_team", "pattern miner",
                    "mcp_tools", "cluster", "/diff", "/resume", "/worktree",
                    "/compact", "/model", "/shell", "/hints off",
                ]
                messages = [n.message for n in app._notifications]
                hint_msgs = [
                    m for m in messages
                    if any(kw in m.lower() for kw in hint_keywords)
                ]
                assert len(hint_msgs) == 0, (
                    f"Unexpected hint notifications without hints/ folder: {hint_msgs}"
                )

    async def test_activation_killswitch(self, mock_sdk, tmp_path):
        """Hints globally disabled → no hint toasts even with hints/ present."""
        _install_hints(tmp_path)

        # Pre-create state file with hints disabled
        state_dir = tmp_path / ".claude"
        state_dir.mkdir()
        (state_dir / "hints_state.json").write_text(
            json.dumps({
                "version": 1,
                "activation": {"enabled": False, "disabled_hints": []},
                "lifecycle": {},
            })
        )

        app = ChatApp()

        with ExitStack() as stack:
            stack.enter_context(
                patch("claudechic.tasks.create_safe_task", return_value=MagicMock())
            )
            stack.enter_context(
                patch("claudechic.sessions.count_sessions", return_value=1)
            )

            async with app.run_test(size=(120, 40), notifications=True) as pilot:
                await pilot.pause()

                app._cwd = tmp_path

                original_sleep = asyncio.sleep

                async def fast_sleep(delay, *args, **kwargs):
                    await original_sleep(0)

                with patch.object(asyncio, "sleep", side_effect=fast_sleep):
                    await app._run_hints(is_startup=True, budget=2)

                await pilot.pause()

                # No hint notifications should appear
                hint_keywords = [
                    "git repo", "guardrails", "project_team", "pattern miner",
                    "mcp_tools", "cluster", "/diff", "/resume", "/worktree",
                    "/compact", "/model", "/shell",
                ]
                messages = [n.message for n in app._notifications]
                hint_msgs = [
                    m for m in messages
                    if any(kw in m.lower() for kw in hint_keywords)
                ]
                assert len(hint_msgs) == 0, (
                    f"Hints should be disabled but got: {hint_msgs}"
                )

    async def test_broken_hints_dont_crash_app(self, mock_sdk, tmp_path):
        """Broken hints/__init__.py → app._run_hints() returns without crash."""
        hints_dir = tmp_path / "hints"
        hints_dir.mkdir()
        (hints_dir / "__init__.py").write_text(
            "raise ImportError('intentionally broken hints module')\n"
        )

        app = ChatApp()

        with ExitStack() as stack:
            stack.enter_context(
                patch("claudechic.tasks.create_safe_task", return_value=MagicMock())
            )
            stack.enter_context(
                patch("claudechic.sessions.count_sessions", return_value=1)
            )

            async with app.run_test(size=(120, 40), notifications=True) as pilot:
                await pilot.pause()

                app._cwd = tmp_path

                # Should not raise — iron rule
                await app._run_hints(is_startup=True, budget=2)
                await pilot.pause()

                # App is alive and functional
                from claudechic.widgets import ChatInput

                input_widget = app.query_one("#input", ChatInput)
                assert input_widget is not None, (
                    "App should be functional despite broken hints"
                )
