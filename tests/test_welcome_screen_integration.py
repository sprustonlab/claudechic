"""Integration tests for welcome screen / onboarding flow.

Boot real TUI with real check_onboarding, real HintStateStore, real filesystem.
Only mock boundary: ClaudeSDKClient, FileIndex, analytics (via mock_sdk fixture).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from claudechic.app import ChatApp

# Import the real function BEFORE the autouse fixture patches it out.
from claudechic.onboarding import check_onboarding as _real_check_onboarding


@pytest.fixture
def _cwd_to_tmp(tmp_path, monkeypatch):
    """Make ChatApp._cwd resolve to tmp_path during on_mount."""
    monkeypatch.setattr(Path, "cwd", staticmethod(lambda: tmp_path))
    return tmp_path


@pytest.fixture
def _real_onboarding(monkeypatch):
    """Re-enable the real check_onboarding (reverses autouse suppression)."""
    monkeypatch.setattr(
        "claudechic.onboarding.check_onboarding", _real_check_onboarding
    )


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(60)
async def test_welcome_screen_appears_and_dismiss_persists(
    mock_sdk, _cwd_to_tmp, _real_onboarding, tmp_path
):
    """No git remote -> welcome screen appears. Dismiss persists via HintStateStore."""
    from claudechic.screens.welcome import RESULT_DISMISS, WelcomeScreen, _ActionItem

    app = ChatApp()
    async with app.run_test(size=(100, 30)) as pilot:
        # Wait for SDK connect + onboarding worker to complete
        await pilot.pause()
        await pilot.pause()
        # Give the background worker time to push the screen
        for _ in range(20):
            await pilot.pause()
            if isinstance(app.screen, WelcomeScreen):
                break

        assert isinstance(app.screen, WelcomeScreen), (
            f"Expected WelcomeScreen, got {type(app.screen).__name__}"
        )

        # Navigate to "Dismiss permanently" action
        from textual.widgets import ListView

        lv = app.screen.query_one("#welcome-list", ListView)
        for i, child in enumerate(lv.children):
            if isinstance(child, _ActionItem) and child.action_id == RESULT_DISMISS:
                lv.index = i
                break
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        # Wait for screen to dismiss
        for _ in range(10):
            await pilot.pause()
            if not isinstance(app.screen, WelcomeScreen):
                break

    # Dismiss marker persisted to disk
    state_file = tmp_path / ".claude" / "hints_state.json"
    assert state_file.exists(), "Dismiss marker file should exist"

    # Re-checking onboarding returns None (won't show again)
    assert _real_check_onboarding(tmp_path) is None, (
        "check_onboarding should return None after dismiss"
    )


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(60)
async def test_welcome_screen_hidden_when_configured(
    mock_sdk, _cwd_to_tmp, _real_onboarding, tmp_path
):
    """Real git remote configured -> welcome screen never appears."""
    from claudechic.screens.welcome import WelcomeScreen

    # Set up a real git repo with a remote
    subprocess.run(
        ["git", "init"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "remote", "add", "origin", "https://github.com/test/repo.git"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )

    # Disable cluster_setup so only the git facet is checked (and it's configured)
    import yaml

    config_data = {"disabled_workflows": ["cluster_setup"]}
    (tmp_path / ".claudechic.yaml").write_text(yaml.dump(config_data), encoding="utf-8")

    app = ChatApp()
    async with app.run_test(size=(100, 30)) as pilot:
        # Wait for SDK connect + onboarding worker
        for _ in range(20):
            await pilot.pause()

        assert not isinstance(app.screen, WelcomeScreen), (
            "Welcome screen should NOT appear when all facets are configured"
        )

    # Verify check_onboarding agrees
    result = _real_check_onboarding(tmp_path)
    # Result is None when all facets configured or no unconfigured facets
    assert result is None, (
        f"check_onboarding should return None for configured project, got: {result}"
    )
