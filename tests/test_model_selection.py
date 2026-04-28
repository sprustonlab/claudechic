"""Tests for model-selection helpers: the SDK/extras merge and the loosened
``/model`` and ``/agent --model=X`` validation.

These cover the change that lets users pick full model IDs (e.g.
``claude-opus-4-6``) in addition to the short aliases ``opus|sonnet|haiku`` and
the curated entries the CLI advertises via ``get_server_info()``.
"""

from __future__ import annotations

from types import SimpleNamespace

from claudechic.app import (
    DEFAULT_EXTRA_MODEL_ENTRIES,
    _merge_model_extras,
)
from claudechic.commands import _is_valid_model, _invalid_model_message
from claudechic.formatting import get_context_window


# ── _merge_model_extras ────────────────────────────────────────────────────


def test_merge_appends_default_extras():
    """Default extras are appended to an SDK list they don't overlap with."""
    sdk = [
        {"value": "default", "displayName": "Default"},
        {"value": "opus[1m]", "displayName": "Opus 4.7 (1M context)"},
    ]
    merged = _merge_model_extras(sdk)

    # SDK entries are preserved in order at the front.
    assert merged[0]["value"] == "default"
    assert merged[1]["value"] == "opus[1m]"

    # All default extras appear.
    values = [m["value"] for m in merged]
    for extra in DEFAULT_EXTRA_MODEL_ENTRIES:
        assert extra["value"] in values

    # The user's target versions are present (including 1M variants).
    assert "claude-opus-4-5" in values
    assert "claude-opus-4-6" in values
    assert "claude-opus-4-6[1m]" in values
    assert "claude-opus-4-7" in values
    assert "claude-opus-4-7[1m]" in values
    assert "claude-sonnet-4-6[1m]" in values


def test_merge_dedupes_by_value_sdk_wins():
    """If the SDK already lists a value, we don't duplicate it."""
    sdk = [
        {
            "value": "claude-opus-4-6",
            "displayName": "SDK-Opus 4.6",
            "description": "from sdk",
        },
    ]
    merged = _merge_model_extras(sdk)

    opus_4_6 = [m for m in merged if m["value"] == "claude-opus-4-6"]
    assert len(opus_4_6) == 1
    # SDK entry is kept, not overwritten by the extra.
    assert opus_4_6[0]["displayName"] == "SDK-Opus 4.6"


def test_merge_accepts_user_override():
    """Passing ``extras=[...]`` replaces the built-in list entirely."""
    sdk = [{"value": "default", "displayName": "Default"}]
    extras = [{"value": "claude-opus-4-6", "displayName": "Only this"}]
    merged = _merge_model_extras(sdk, extras=extras)

    values = [m["value"] for m in merged]
    assert values == ["default", "claude-opus-4-6"]


def test_merge_skips_entries_without_value():
    """Malformed extras without a ``value`` are ignored, not raised on."""
    sdk = [{"value": "default", "displayName": "Default"}]
    extras = [{"displayName": "Missing value"}, {"value": "claude-opus-4-6"}]
    merged = _merge_model_extras(sdk, extras=extras)

    values = [m["value"] for m in merged]
    assert values == ["default", "claude-opus-4-6"]


def test_merge_empty_extras_returns_sdk_list():
    """An empty extras list leaves the SDK list untouched."""
    sdk = [{"value": "default", "displayName": "Default"}]
    merged = _merge_model_extras(sdk, extras=[])
    assert merged == sdk


# ── _is_valid_model / _invalid_model_message ───────────────────────────────


def _fake_app(model_values: list[str]) -> SimpleNamespace:
    """A stand-in for ChatApp with only ``_available_models`` populated."""
    return SimpleNamespace(
        _available_models=[{"value": v} for v in model_values],
    )


def test_is_valid_model_accepts_short_aliases():
    app = _fake_app([])
    assert _is_valid_model(app, "opus")
    assert _is_valid_model(app, "sonnet")
    assert _is_valid_model(app, "haiku")
    # Case-insensitive for the aliases.
    assert _is_valid_model(app, "Opus")


def test_is_valid_model_accepts_advertised_values():
    """Any ``value`` from ``_available_models`` is accepted."""
    app = _fake_app(["default", "opus[1m]", "claude-opus-4-6"])
    assert _is_valid_model(app, "default")
    assert _is_valid_model(app, "opus[1m]")
    assert _is_valid_model(app, "claude-opus-4-6")


def test_is_valid_model_accepts_full_ids_even_if_not_listed():
    """Escape hatch: any ``claude-*`` ID is accepted so the user can target
    IDs we haven't baked into the default extras list."""
    app = _fake_app([])  # Empty available list.
    assert _is_valid_model(app, "claude-opus-4-5-20251101")
    assert _is_valid_model(app, "claude-sonnet-4-5")


def test_is_valid_model_rejects_garbage():
    app = _fake_app(["default"])
    assert not _is_valid_model(app, "gpt-4")
    assert not _is_valid_model(app, "")
    assert not _is_valid_model(app, "nonsense")


def test_is_valid_model_handles_missing_available_models_attr():
    """If the app hasn't finished connecting, ``_available_models`` may be
    missing or None -- the helper should still accept aliases and full IDs."""
    app = SimpleNamespace()  # No _available_models attribute at all.
    assert _is_valid_model(app, "opus")
    assert _is_valid_model(app, "claude-opus-4-6")
    assert not _is_valid_model(app, "gpt-4")


def test_invalid_model_message_shows_sample_ids():
    """The error message lists some real examples so the user knows what to
    type. Sample is capped, so we don't paste the whole list."""
    app = _fake_app(
        [
            "default",
            "sonnet[1m]",
            "opus[1m]",
            "haiku",
            "claude-opus-4-7",
            "claude-opus-4-6",
            "claude-opus-4-5",
            "claude-sonnet-4-6",
        ]
    )
    msg = _invalid_model_message(app, "bogus")
    assert "bogus" in msg
    assert "opus" in msg and "sonnet" in msg and "haiku" in msg
    # Sample is capped at 6 entries -- later ones shouldn't appear.
    assert "claude-sonnet-4-6" not in msg


def test_invalid_model_message_falls_back_without_available_models():
    app = _fake_app([])
    msg = _invalid_model_message(app, "bogus")
    assert "bogus" in msg
    assert "opus, sonnet, haiku" in msg


# ── get_context_window for [1m] variants ───────────────────────────────────


def test_context_window_1m_suffix():
    """The ``[1m]`` suffix on any model value should report 1M context."""
    assert get_context_window("claude-opus-4-6[1m]") == 1_000_000
    assert get_context_window("claude-sonnet-4-6[1m]") == 1_000_000
    assert get_context_window("opus[1m]") == 1_000_000
    assert get_context_window("anything[1m]") == 1_000_000


def test_context_window_plain_models_unchanged():
    """Non-[1m] models keep their existing behavior."""
    assert get_context_window("opus") == 1_000_000  # opus was already 1M
    assert get_context_window("sonnet") == 200_000
    assert get_context_window("haiku") == 200_000
    assert get_context_window("claude-opus-4-6") == 1_000_000  # substring "opus"
    assert get_context_window("claude-sonnet-4-5") == 200_000  # substring "sonnet"
    assert get_context_window(None) == 200_000  # default
