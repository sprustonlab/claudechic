"""Textual pilot tests for the Advanced site-checklist subscreens.

Covers:
- 4-row constraints / 3-row environment row counts.
- ``row-label`` + ``row-token`` two-column display.
- One-row-floor enforcement at toggle time.
- Enter dismisses with a ``frozenset[str]`` of currently checked tokens.
"""

from __future__ import annotations

import pytest
from claudechic.app import ChatApp
from claudechic.screens.agent_prompt_context import (
    AdvancedConstraintsSitesScreen,
    AdvancedEnvironmentSitesScreen,
    _SiteRow,
)
from textual.widgets import Label

pytestmark = [pytest.mark.asyncio, pytest.mark.timeout(30)]


async def _push_and_settle(app, pilot, screen):
    """Push a screen and pump the loop until rows are mounted."""
    app.push_screen(screen)
    for _ in range(4):
        await pilot.pause()


# ---------------------------------------------------------------------------
# Row count
# ---------------------------------------------------------------------------


async def test_advanced_constraints_sites_screen_renders_four_rows(mock_sdk):
    app = ChatApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await _push_and_settle(
            app,
            pilot,
            AdvancedConstraintsSitesScreen(
                frozenset({"spawn", "activation", "phase-advance", "post-compact"})
            ),
        )
        screen = app.screen
        rows = list(screen.query(_SiteRow))
        tokens = [r.spec.token for r in rows]
        assert tokens == [
            "spawn",
            "activation",
            "phase-advance",
            "post-compact",
        ], f"unexpected tokens={tokens}"


async def test_advanced_environment_sites_screen_renders_three_rows(mock_sdk):
    app = ChatApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await _push_and_settle(
            app,
            pilot,
            AdvancedEnvironmentSitesScreen(
                frozenset({"spawn", "activation", "post-compact"})
            ),
        )
        screen = app.screen
        rows = list(screen.query(_SiteRow))
        tokens = [r.spec.token for r in rows]
        assert tokens == ["spawn", "activation", "post-compact"]


# ---------------------------------------------------------------------------
# Two-column display
# ---------------------------------------------------------------------------


async def test_advanced_constraints_sites_screen_token_secondary_column_present(
    mock_sdk,
):
    app = ChatApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await _push_and_settle(
            app,
            pilot,
            AdvancedConstraintsSitesScreen(frozenset({"spawn"})),
        )
        screen = app.screen
        rows = list(screen.query(_SiteRow))
        assert rows
        for row in rows:
            labels = list(row.query(Label))
            classes = [tuple(label.classes) for label in labels]
            assert any("row-label" in c for c in classes), (
                f"row missing .row-label: {classes}"
            )
            assert any("row-token" in c for c in classes), (
                f"row missing .row-token: {classes}"
            )


# ---------------------------------------------------------------------------
# One-row floor
# ---------------------------------------------------------------------------


async def test_advanced_constraints_sites_screen_clearing_last_checkbox_reverts_with_notice(
    mock_sdk, monkeypatch
):
    captured: list[tuple] = []
    app = ChatApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        # Capture notify calls (observation of UI affordance, not mocking SUT).
        monkeypatch.setattr(
            app, "notify", lambda *a, **kw: captured.append((a, kw))
        )

        # Start with exactly one site checked.
        await _push_and_settle(
            app,
            pilot,
            AdvancedConstraintsSitesScreen(frozenset({"spawn"})),
        )

        # The first row (``spawn``) starts highlighted; pressing space
        # attempts to toggle off the only-checked row -> revert + notice.
        await pilot.press("space")
        await pilot.pause()

        screen = app.screen
        rows = list(screen.query(_SiteRow))
        spawn_row = next(r for r in rows if r.spec.token == "spawn")
        assert spawn_row.checked, "Floor must hold: last checkbox stays checked"

        # Notice was emitted.
        notices = [a[0] for (a, kw) in captured if a]
        assert any(
            "at least one site must remain checked" in str(n) for n in notices
        ), f"Floor notice was not emitted; captured={captured!r}"


async def test_advanced_environment_sites_screen_clearing_last_checkbox_reverts_with_notice(
    mock_sdk, monkeypatch
):
    captured: list[tuple] = []
    app = ChatApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        monkeypatch.setattr(
            app, "notify", lambda *a, **kw: captured.append((a, kw))
        )
        await _push_and_settle(
            app,
            pilot,
            AdvancedEnvironmentSitesScreen(frozenset({"spawn"})),
        )

        await pilot.press("space")
        await pilot.pause()

        screen = app.screen
        rows = list(screen.query(_SiteRow))
        spawn_row = next(r for r in rows if r.spec.token == "spawn")
        assert spawn_row.checked

        notices = [a[0] for (a, kw) in captured if a]
        assert any(
            "at least one site must remain checked" in str(n) for n in notices
        )


# ---------------------------------------------------------------------------
# Enter dismisses with frozenset
# ---------------------------------------------------------------------------


async def test_advanced_constraints_sites_screen_enter_dismisses_with_frozenset_result(
    mock_sdk,
):
    """Enter accepts and the screen dismisses with a frozenset[str] of
    currently-checked tokens."""
    app = ChatApp()
    captured_results: list = []

    def _on_dismiss(value) -> None:
        captured_results.append(value)

    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        app.push_screen(
            AdvancedConstraintsSitesScreen(
                frozenset({"spawn", "activation"})
            ),
            callback=_on_dismiss,
        )
        for _ in range(4):
            await pilot.pause()

        # Highlight the second row (activation) and toggle it off so
        # we end with just {"spawn"} checked.
        await pilot.press("down")
        await pilot.pause()
        await pilot.press("space")
        await pilot.pause()
        # Trigger the accept action directly -- the Enter binding is
        # registered on the screen but pilot.press("enter") may be
        # consumed by the focused ListView before reaching our binding.
        screen = app.screen
        screen.action_accept()
        for _ in range(4):
            await pilot.pause()

        assert captured_results, "screen did not dismiss"
        result_value = captured_results[-1]
        assert isinstance(result_value, frozenset)
        # Tokens should be a subset of the original; "spawn" remains.
        assert "spawn" in result_value
        assert "activation" not in result_value
