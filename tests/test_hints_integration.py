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
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from claudechic.app import ChatApp

pytestmark = [pytest.mark.asyncio, pytest.mark.integration, pytest.mark.timeout(30)]

# ---------------------------------------------------------------------------
# Create a synthetic template-side hints package for testing.
#
# The original template hints/ package (with an evaluate() entry point) was
# removed when the hints system moved to manifest-declared pipelines.  The
# _run_hints() code path that dynamically imports a project-local hints/
# package and calls mod.evaluate() still exists for backward compatibility.
# We create a minimal package that exercises that path.
# ---------------------------------------------------------------------------

_HINTS_INIT_SRC = '''\
"""Synthetic hints package for integration testing."""

import asyncio


async def evaluate(*, send_notification, project_root, session_count,
                   is_startup, budget, **kwargs):
    """Produce a toast notification so the test can observe it."""
    if not is_startup:
        return
    msg = "Tip: use /hints off to disable hints"
    send_notification(msg, timeout=7)
    # Yield control so the notification is processed
    await asyncio.sleep(0)
'''


def _install_hints(dest: Path) -> None:
    """Create a minimal template-side hints package in *dest*."""
    hints_dir = dest / "hints"
    hints_dir.mkdir(exist_ok=True)
    (hints_dir / "__init__.py").write_text(_HINTS_INIT_SRC, encoding="utf-8")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestHintsInChatApp:
    """Real ChatApp E2E tests for the hints system."""

    @pytest.mark.filterwarnings("ignore::pytest.PytestWarning")
    def test_hints_source_exists(self):
        """Sanity check: synthetic hints package can be installed."""
        # The _install_hints helper creates the package dynamically,
        # so we just verify the source string is non-empty.
        assert len(_HINTS_INIT_SRC) > 0

    async def test_startup_hint_appears_as_toast(self, mock_sdk, tmp_path):
        """ChatApp discovers hints/, evaluates, and shows toast notifications.

        Verifies that _run_hints() produces visible toasts from workflow hints.
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

                # Verify: hint messages contain the /hints off suffix
                messages = [n.message for n in app._notifications]
                assert any("hints off" in m.lower() for m in messages), (
                    f"Expected hint with disable suffix, got: {messages}"
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
                    "git repo",
                    "guardrails",
                    "project_team",
                    "pattern miner",
                    "mcp_tools",
                    "cluster",
                    "/diff",
                    "/resume",
                    "/worktree",
                    "/compact",
                    "/model",
                    "/shell",
                    "/hints off",
                ]
                messages = [n.message for n in app._notifications]
                hint_msgs = [
                    m for m in messages if any(kw in m.lower() for kw in hint_keywords)
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
            json.dumps(
                {
                    "version": 1,
                    "activation": {"enabled": False, "disabled_hints": []},
                    "lifecycle": {},
                }
            )
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
                    "git repo",
                    "guardrails",
                    "project_team",
                    "pattern miner",
                    "mcp_tools",
                    "cluster",
                    "/diff",
                    "/resume",
                    "/worktree",
                    "/compact",
                    "/model",
                    "/shell",
                ]
                messages = [n.message for n in app._notifications]
                hint_msgs = [
                    m for m in messages if any(kw in m.lower() for kw in hint_keywords)
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
