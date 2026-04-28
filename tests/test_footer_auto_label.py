"""Tests for the auto-mode footer label wording (SPEC §7.10)."""

from __future__ import annotations

import pytest
from claudechic.widgets import StatusFooter
from textual.app import App, ComposeResult
from textual.widgets import Static


class _FooterApp(App):
    def compose(self) -> ComposeResult:
        yield StatusFooter()


@pytest.mark.asyncio
async def test_auto_mode_label_per_spec():
    """``auto`` mode shows the spec-mandated label text (§7.10).

    The label MUST be visibly distinct from ``acceptEdits`` ("Auto-edit:
    on") and ``bypassPermissions`` ("Bypass: all auto-approved").
    """
    app = _FooterApp()
    async with app.run_test():
        footer = app.query_one(StatusFooter)
        footer.permission_mode = "auto"
        label = footer.query_one("#permission-mode-label", Static)
        rendered = label.render()
        text = rendered.plain if hasattr(rendered, "plain") else str(rendered)  # type: ignore[union-attr]
        assert "auto: safe tools auto-approved" in text.lower()
        # Distinguishability: must NOT collide with the other two "auto"
        # adjacent labels.
        assert "auto-edit" not in text.lower()
        assert "bypass" not in text.lower()


@pytest.mark.asyncio
async def test_settings_label_present():
    """The footer exposes a clickable settings button (SPEC §7.1 surface 2)."""
    from claudechic.widgets.layout.footer import SettingsLabel

    app = _FooterApp()
    async with app.run_test():
        footer = app.query_one(StatusFooter)
        labels = footer.query(SettingsLabel)
        assert len(labels) == 1
        rendered = labels.first().render()
        text = rendered.plain if hasattr(rendered, "plain") else str(rendered)  # type: ignore[union-attr]
        assert text == "settings"
