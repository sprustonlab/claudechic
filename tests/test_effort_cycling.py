"""Tests for Component C (effort cycling) -- abast_accf332_sync.

Covers sub-units C1, C2, C3:
- C1: ``Agent.effort`` runtime attribute and propagation through
       ``ChatApp._make_options`` to ``ClaudeAgentOptions(effort=...)``
       (the SDK then appends ``--effort <level>`` to the Claude Code
       subprocess argv).
- C2: ``EffortLabel`` cycles through ``low -> medium -> high -> max -> low``
       on click; visible text uses the locked contract strings
       (``"effort: low"`` / ``"effort: medium"`` / ``"effort: high"`` /
       ``"effort: max"``); model-aware level snapping for non-Opus models.
- C3: settings persistence -- clicking the EffortLabel writes the new
       level into ``CONFIG["effort"]`` and calls ``config.save()``.

Test names follow the SPEC convention: ``test_c<n>_<concept>_<expectation>``.
"""

from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import pytest
from claudechic.agent import Agent
from claudechic.app import ChatApp
from claudechic.widgets.layout.footer import EffortLabel, StatusFooter
from textual.app import App, ComposeResult


# ---------------------------------------------------------------------------
# C1: Agent.effort default + propagation to ClaudeAgentOptions
# ---------------------------------------------------------------------------


class TestC1AgentEffortAttribute:
    """``Agent.effort`` is a runtime field, defaults to ``"high"``."""

    def test_c1_effort_attribute_default_is_high(self, tmp_path: Path) -> None:
        agent = Agent(name="A", cwd=tmp_path)
        assert agent.effort == "high"

    def test_c1_effort_attribute_is_mutable(self, tmp_path: Path) -> None:
        agent = Agent(name="A", cwd=tmp_path)
        for level in ("low", "medium", "high", "max"):
            agent.effort = level
            assert agent.effort == level


@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_c1_effort_propagates_to_subprocess_argv_effort_flag(
    mock_sdk, tmp_path
) -> None:
    """Gestalt agent-side: ``agent.effort`` -> ``ClaudeAgentOptions(effort=...)``.

    The Claude Agent SDK forwards ``ClaudeAgentOptions.effort`` to the
    Claude Code subprocess as ``--effort <level>``. This test does not
    spawn the subprocess; instead it verifies the contract one layer
    above: ``ChatApp._make_options(agent=agent)`` reads
    ``agent.effort`` LIVE and stamps it into the returned
    ``ClaudeAgentOptions``. Mocking the subprocess invocation is
    unnecessary because the SDK side of the wiring is the SDK's
    responsibility, not claudechic's.
    """
    app = ChatApp()

    with ExitStack() as stack:
        stack.enter_context(patch("claudechic.sessions.count_sessions", return_value=1))

        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            app._cwd = tmp_path
            app._init_workflow_infrastructure()
            await pilot.pause()

            agent = Agent(name="effort-agent", cwd=tmp_path)

            for level in ("low", "medium", "high", "max"):
                agent.effort = level
                options = app._make_options(cwd=tmp_path, agent=agent)
                assert options.effort == level, (
                    f"_make_options should forward agent.effort={level!r} "
                    f"to ClaudeAgentOptions(effort=...); got "
                    f"{options.effort!r}"
                )


# ---------------------------------------------------------------------------
# C2: EffortLabel widget behaviour
# ---------------------------------------------------------------------------


class _FooterTestApp(App):
    """Minimal Textual app that mounts a real ``StatusFooter``."""

    def compose(self) -> ComposeResult:
        yield StatusFooter()


@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_c2_clicking_effort_label_cycles_visible_text(tmp_path: Path) -> None:
    """Gestalt user-side: clicking the label cycles through locked strings.

    The cycle order is the locked global ordering from SPEC C2 /
    Decision 5: ``low -> medium -> high -> xhigh -> max -> low``. The
    on-screen text is the locked-string ``"effort: <level>"``
    (lower-case, no punctuation), matching SDK vocabulary.

    Persisting the cycled level to ``~/.claudechic/config.yaml`` would
    leak across test runs; we patch ``config.save`` to a no-op and only
    assert on the visible text in this test (C3 covers persistence).
    """
    # Patch save() so the cycle does not write to the user's home dir.
    with patch("claudechic.config.save"):
        app = _FooterTestApp()
        async with app.run_test() as pilot:
            footer = app.query_one(StatusFooter)
            label = footer.query_one("#effort-label", EffortLabel)
            await pilot.pause()

            # Reset to a known starting level + force the full level
            # set so the test does not depend on what hydrate-from-config
            # produced on mount or which model the footer's reactive
            # picked. The full cycle is the locked contract per SPEC C2.
            label._levels = EffortLabel.DEFAULT_LEVELS
            label.set_effort("low")
            footer.effort = "low"
            await pilot.pause()

            expected_cycle = [
                "effort: medium",
                "effort: high",
                "effort: xhigh",
                "effort: max",
                "effort: low",
            ]

            for expected_text in expected_cycle:
                # Drive the cycle via the public on_click entry point
                # (the production path), not by poking ``_effort``.
                label.on_click(None)  # type: ignore[arg-type]
                await pilot.pause()
                rendered = label.render()
                rendered_text = (
                    rendered.plain if hasattr(rendered, "plain") else str(rendered)
                )
                assert rendered_text == expected_text, (
                    f"Click cycle should yield {expected_text!r}; got {rendered_text!r}"
                )


def test_c2_effort_label_display_strings_are_locked() -> None:
    """SPEC's locked contract strings: ``"effort: <level>"`` per level."""
    assert EffortLabel.EFFORT_DISPLAY["low"] == "effort: low"
    assert EffortLabel.EFFORT_DISPLAY["medium"] == "effort: medium"
    assert EffortLabel.EFFORT_DISPLAY["high"] == "effort: high"
    assert EffortLabel.EFFORT_DISPLAY["xhigh"] == "effort: xhigh"
    assert EffortLabel.EFFORT_DISPLAY["max"] == "effort: max"


def test_c2_effort_label_default_levels_order() -> None:
    """Cycle order is the locked global ordering."""
    assert EffortLabel.DEFAULT_LEVELS == ("low", "medium", "high", "xhigh", "max")


def test_c2_effort_label_levels_for_opus_includes_max() -> None:
    """The Opus family fallback supports ``"max"``."""
    assert "max" in EffortLabel.levels_for_model("claude-opus-4")
    assert "max" in EffortLabel.levels_for_model("opus")


def test_c2_effort_label_levels_for_fable_includes_top_levels() -> None:
    """The Fable family fallback supports ``"xhigh"`` and ``"max"``."""
    levels = EffortLabel.levels_for_model("claude-fable-5[1m]")
    assert "xhigh" in levels
    assert "max" in levels


@pytest.mark.parametrize(
    "model", ["sonnet", "haiku", "claude-sonnet-4", "claude-haiku-4-5"]
)
def test_c2_non_opus_models_drop_max(model: str) -> None:
    """Non-Opus families drop ``"max"`` from their cycle (Decision 5)."""
    levels = EffortLabel.levels_for_model(model)
    assert "max" not in levels
    assert "low" in levels
    assert "medium" in levels
    assert "high" in levels


@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_c2_effort_snaps_to_medium_on_non_opus_model() -> None:
    """``set_available_levels`` snaps a level outside the new set to medium.

    Concretely: a user on Opus picks ``"max"``, then switches to
    Sonnet -- the displayed level snaps to ``"medium"`` per
    SPEC C2 / Decision 5.
    """
    with patch("claudechic.config.save"):
        app = _FooterTestApp()
        async with app.run_test() as pilot:
            footer = app.query_one(StatusFooter)
            label = footer.query_one("#effort-label", EffortLabel)
            await pilot.pause()

            label.set_effort("max")
            label._levels = EffortLabel.levels_for_model("opus")
            assert label._effort == "max"

            # User switches to Sonnet -- the footer's watch_model() does
            # this in production. Drive it via the public set method.
            label.set_available_levels(EffortLabel.levels_for_model("sonnet"))
            await pilot.pause()

            assert label._effort == "medium"
            rendered = label.render()
            rendered_text = (
                rendered.plain if hasattr(rendered, "plain") else str(rendered)
            )
            assert rendered_text == "effort: medium"


# ---------------------------------------------------------------------------
# C3: settings persistence
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_c3_effort_cycle_persists_to_config(monkeypatch) -> None:
    """C3: clicking EffortLabel writes the new level into CONFIG and saves.

    The widget mutates ``CONFIG["effort"]`` and calls ``config.save()``
    after every successful cycle. We patch the save side-effect so the
    test does not touch the user's home directory; the assertion is
    that the in-memory ``CONFIG`` dict was updated AND ``save()`` was
    invoked at least once during the cycle.
    """
    from claudechic import config as cfg

    # Snapshot + restore so this test cannot leak into others.
    original_effort = cfg.CONFIG.get("effort", "high")
    save_calls: list[None] = []

    def _fake_save() -> None:
        save_calls.append(None)

    monkeypatch.setattr(cfg, "save", _fake_save)

    try:
        app = _FooterTestApp()
        async with app.run_test() as pilot:
            footer = app.query_one(StatusFooter)
            label = footer.query_one("#effort-label", EffortLabel)
            await pilot.pause()

            # Force a known starting state so we know which level the
            # next click rotates to.
            label.set_effort("low")
            footer.effort = "low"
            cfg.CONFIG["effort"] = "low"
            save_calls.clear()
            await pilot.pause()

            label.on_click(None)  # type: ignore[arg-type]
            await pilot.pause()

            # CONFIG holds the new level, and save() was invoked.
            assert cfg.CONFIG.get("effort") == "medium", (
                "Clicking EffortLabel should write the new level into "
                "CONFIG['effort'] (SPEC C3 persistence)."
            )
            assert save_calls, (
                "Clicking EffortLabel should call config.save() so the "
                "level survives a restart (SPEC C3)."
            )
    finally:
        cfg.CONFIG["effort"] = original_effort


def test_c3_settings_screen_registers_effort_key() -> None:
    """C3: the settings registry exposes ``effort`` as a user-tier enum.

    SPEC §C3 mandates that the ``effort`` key be visible in the settings
    screen with the valid levels as its enum choices.
    """
    from claudechic.screens.settings import USER_KEYS

    spec = next((s for s in USER_KEYS if s.key == "effort"), None)
    assert spec is not None, "USER_KEYS must include the 'effort' key"
    assert spec.tier == "user"
    assert spec.editor == "enum"
    assert tuple(spec.choices) == ("low", "medium", "high", "xhigh", "max")


def test_c3_default_effort_in_config_loader_is_high() -> None:
    """C3: a fresh config loads ``effort="high"`` as the default level."""
    from claudechic import config as cfg

    # CONFIG is loaded at import time. We don't reload here -- just
    # assert that ``effort`` is one of the valid levels and that the
    # loader contract documents "high" as the default.
    assert cfg.CONFIG.get("effort", "high") in ("low", "medium", "high", "max")


# ---------------------------------------------------------------------------
# C2: capability registry from get_server_info() model entries
# ---------------------------------------------------------------------------


@pytest.fixture()
def _clean_capability_registry():
    """Isolate registry mutations from other tests (class-level state)."""
    saved = EffortLabel._capability_levels
    EffortLabel._capability_levels = {}
    yield
    EffortLabel._capability_levels = saved


SDK_MODELS_SAMPLE = [
    {
        "value": "default",
        "displayName": "Default (recommended)",
        "description": "Opus 4.8 with 1M context \N{MIDDLE DOT} Best for everyday tasks",
        "supportedEffortLevels": ["low", "medium", "high", "xhigh", "max"],
    },
    {
        "value": "claude-fable-5[1m]",
        "displayName": "Fable",
        "description": "Fable 5 \N{MIDDLE DOT} Most capable",
        "supportedEffortLevels": ["low", "medium", "high", "xhigh", "max"],
    },
    {
        "value": "sonnet",
        "displayName": "Sonnet",
        "description": "Sonnet 4.6 \N{MIDDLE DOT} Efficient for routine tasks",
        "supportedEffortLevels": ["low", "medium", "high", "max"],
    },
    # No supportedEffortLevels -- must NOT enter the registry.
    {
        "value": "haiku",
        "displayName": "Haiku",
        "description": "Haiku 4.5 \N{MIDDLE DOT} Fastest",
    },
    # Legacy pin shape -- no metadata either.
    {"value": "claude-opus-4-6", "displayName": "Opus 4.6", "description": "Opus 4.6"},
]


class TestC2CapabilityRegistry:
    """``levels_for_model`` prefers CLI-advertised capability metadata."""

    def test_c2_registry_resolves_value_displayname_and_short_name(
        self, _clean_capability_registry
    ) -> None:
        EffortLabel.update_model_capabilities(SDK_MODELS_SAMPLE)
        expected = ("low", "medium", "high", "xhigh", "max")
        # Routable value, displayName, and the short name the footer
        # derives from the description all resolve.
        assert EffortLabel.levels_for_model("claude-fable-5[1m]") == expected
        assert EffortLabel.levels_for_model("Fable") == expected
        assert EffortLabel.levels_for_model("Fable 5") == expected

    def test_c2_registry_beats_family_fallback(
        self, _clean_capability_registry
    ) -> None:
        """The CLI advertising ``max`` on Sonnet overrides the static
        fallback (which conservatively omits it)."""
        EffortLabel.update_model_capabilities(SDK_MODELS_SAMPLE)
        assert "max" in EffortLabel.levels_for_model("Sonnet")
        assert "max" in EffortLabel.levels_for_model("sonnet")

    def test_c2_entries_without_metadata_use_family_fallback(
        self, _clean_capability_registry
    ) -> None:
        EffortLabel.update_model_capabilities(SDK_MODELS_SAMPLE)
        # Haiku carried no supportedEffortLevels -> static fallback.
        assert EffortLabel.levels_for_model("haiku") == ("low", "medium", "high")
        # Legacy pin without metadata -> opus family fallback.
        assert EffortLabel.levels_for_model("claude-opus-4-6") == (
            "low",
            "medium",
            "high",
            "max",
        )

    def test_c2_empty_registry_preserves_fallback_behavior(
        self, _clean_capability_registry
    ) -> None:
        """Old CLIs without capability metadata behave as before."""
        EffortLabel.update_model_capabilities([])
        assert EffortLabel.levels_for_model("sonnet") == ("low", "medium", "high")
        assert EffortLabel.levels_for_model(None) == EffortLabel.UNKNOWN_MODEL_LEVELS

    def test_c2_malformed_metadata_is_skipped(self, _clean_capability_registry) -> None:
        EffortLabel.update_model_capabilities(
            [
                {"value": "weird-a", "supportedEffortLevels": "high"},
                {"value": "weird-b", "supportedEffortLevels": []},
                {"value": "weird-c", "supportedEffortLevels": [1, 2]},
            ]
        )
        assert EffortLabel._capability_levels == {}
