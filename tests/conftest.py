"""Shared test fixtures."""

from __future__ import annotations

import json
from contextlib import ExitStack
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from claudechic.features.roborev.models import ReviewJob
from claudechic.widgets.layout.reviews import ReviewItem


async def empty_async_gen():
    """Empty async generator for mocking receive_response."""
    return
    yield  # unreachable - makes this an async generator


@pytest.fixture(autouse=True)
def _suppress_welcome_screen(monkeypatch):
    """Prevent welcome screen from showing during tests."""
    monkeypatch.setattr("claudechic.onboarding.check_onboarding", lambda *a, **kw: None)


@pytest.fixture
def real_agent_with_mock_sdk(tmp_path):
    """Create a real Agent with a mock ClaudeSDKClient.

    Returns a (agent, mock_client) tuple. The agent is connected with a
    mock SDK that supports connect/interrupt/query/receive_response as
    minimal stubs. This lets integration tests exercise real Agent state
    machine logic without needing a live SDK connection.
    """
    from claudechic.agent import Agent

    mock_client = MagicMock()
    mock_client.connect = AsyncMock()
    mock_client.interrupt = AsyncMock()
    mock_client.query = AsyncMock()
    mock_client.receive_response = lambda: empty_async_gen()
    mock_client.get_server_info = AsyncMock(return_value={"commands": [], "models": []})
    mock_client.set_permission_mode = AsyncMock()
    mock_client._transport = None

    agent = Agent(name="test-agent", cwd=tmp_path)
    # Inject mock client directly (bypass connect() which needs real SDK)
    agent.client = mock_client
    agent.session_id = "mock-session-001"

    return agent, mock_client


async def wait_for_workers(app):
    """Wait for all workers to complete."""
    await app.workers.wait_for_complete()


async def submit_command(app, pilot, command: str):
    """Submit a command, handling autocomplete properly.

    When setting input text directly, autocomplete may activate.
    This helper hides it before submitting to ensure the command goes through.
    """
    from claudechic.widgets import ChatInput

    input_widget = app.query_one("#input", ChatInput)
    input_widget.text = command
    await pilot.pause()

    # Hide autocomplete if it's showing (triggered by / or @)
    if input_widget._autocomplete and input_widget._autocomplete.display:
        input_widget._autocomplete.action_hide()
        await pilot.pause()

    input_widget.action_submit()
    await pilot.pause()


@pytest.fixture
def mock_sdk():
    """Patch SDK to not actually connect.

    Patches both app.py and agent.py imports since agents create their own clients.
    Also patches FileIndex to avoid subprocess transport leaks during test cleanup.
    Disables analytics to avoid httpx connection leaks.
    """
    mock_client = MagicMock()
    mock_client.connect = AsyncMock()
    mock_client.query = AsyncMock()
    mock_client.interrupt = AsyncMock()
    mock_client.get_server_info = AsyncMock(return_value={"commands": [], "models": []})
    mock_client.set_permission_mode = AsyncMock()
    mock_client.receive_response = lambda: empty_async_gen()
    mock_client._transport = None  # For get_claude_pid_from_client

    # Mock FileIndex to avoid git subprocess transport leaks
    # The subprocess transports try to close after the event loop is closed
    from claudechic.file_index import FileIndex

    mock_file_index = MagicMock(spec=FileIndex)
    mock_file_index.refresh = AsyncMock()
    mock_file_index.files = []

    # Use ExitStack to avoid deep nesting
    with ExitStack() as stack:
        # Clear local config first so tests get fresh-install defaults
        # (prevents developer's ~/.claude/.claudechic.yaml from leaking in).
        # Must come before the analytics patch since they share the same dict.
        stack.enter_context(
            patch.dict("claudechic.agent_manager.CONFIG", {}, clear=True)
        )
        # Disable analytics to avoid httpx AsyncClient connection leaks
        stack.enter_context(
            patch.dict("claudechic.analytics.CONFIG", {"analytics": {"enabled": False}})
        )
        stack.enter_context(
            patch("claudechic.app.ClaudeSDKClient", return_value=mock_client)
        )
        stack.enter_context(
            patch("claudechic.agent.ClaudeSDKClient", return_value=mock_client)
        )
        stack.enter_context(
            patch("claudechic.agent.FileIndex", return_value=mock_file_index)
        )
        stack.enter_context(
            patch("claudechic.app.FileIndex", return_value=mock_file_index)
        )
        yield mock_client


@pytest.fixture
def mock_roborev_output():
    """Mock roborev CLI subprocess output.

    Returns a callable that patches is_roborev_available and subprocess.run
    so that the CLI functions receive the given data as JSON stdout.

    Usage::

        def test_example(mock_roborev_output, tmp_path):
            mock_roborev_output([{"id": 1, "branch": "main"}])
            reviews = list_reviews(tmp_path)
    """
    stack = ExitStack()

    def _mock(data: Any, *, returncode: int = 0, stderr: str = "") -> MagicMock:
        stdout = json.dumps(data) if not isinstance(data, str) else data
        mock_result = MagicMock(returncode=returncode, stdout=stdout, stderr=stderr)
        stack.enter_context(
            patch(
                "claudechic.features.roborev.cli.is_roborev_available",
                return_value=True,
            )
        )
        stack.enter_context(patch("subprocess.run", return_value=mock_result))
        return mock_result

    yield _mock
    stack.close()


@pytest.fixture
def mock_roborev_unavailable():
    """Simulate roborev CLI not being installed."""
    with patch(
        "claudechic.features.roborev.cli.is_roborev_available", return_value=False
    ):
        yield


@pytest.fixture
def review_job_factory():
    """Create ReviewJob instances with sensible defaults.

    Usage::

        def test_example(review_job_factory):
            job = review_job_factory(status="running")
    """

    def _factory(**overrides: Any) -> ReviewJob:
        defaults: dict[str, Any] = {
            "id": "1",
            "git_ref": "abc1234",
            "commit_subject": "test",
            "status": "done",
            "verdict": "",
        }
        defaults.update(overrides)
        return ReviewJob(**defaults)

    return _factory


@pytest.fixture
def review_item_factory(review_job_factory):
    """Create ReviewItem instances (unmounted) with sensible defaults.

    Usage::

        def test_example(review_item_factory):
            item = review_item_factory(verdict="pass")
    """

    def _factory(**overrides: Any) -> ReviewItem:
        return ReviewItem(review_job_factory(**overrides))

    return _factory
