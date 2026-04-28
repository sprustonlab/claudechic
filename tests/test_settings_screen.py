"""Tests for SettingsScreen + helpers (Group G / SPEC §7)."""

from __future__ import annotations

import pytest
from claudechic.screens.settings import (
    ALL_KEYS,
    PROJECT_KEYS,
    USER_KEYS,
    SettingKey,
    _del_dotted,
    _get_dotted,
    _set_dotted,
)


# ---------------------------------------------------------------------------
# Dotted-key helpers
# ---------------------------------------------------------------------------


class TestDottedHelpers:
    def test_get_top_level(self):
        d = {"foo": 1, "bar": 2}
        assert _get_dotted(d, "foo") == 1
        assert _get_dotted(d, "bar") == 2

    def test_get_nested(self):
        d = {"analytics": {"enabled": True, "id": "abc"}}
        assert _get_dotted(d, "analytics.enabled") is True
        assert _get_dotted(d, "analytics.id") == "abc"

    def test_get_missing(self):
        d = {"analytics": {"enabled": True}}
        assert _get_dotted(d, "analytics.missing") is None
        assert _get_dotted(d, "missing.path") is None
        assert _get_dotted(d, "analytics.enabled.deeper") is None

    def test_set_top_level(self):
        d: dict = {}
        _set_dotted(d, "foo", 42)
        assert d == {"foo": 42}

    def test_set_nested_creates_parent(self):
        d: dict = {}
        _set_dotted(d, "logging.file", "/tmp/x.log")
        assert d == {"logging": {"file": "/tmp/x.log"}}

    def test_set_overwrites_non_dict_parent(self):
        # Defensive: if a leaf was previously stored where a dict is now
        # required, we replace it (rather than crash).
        d: dict = {"logging": "broken"}
        _set_dotted(d, "logging.file", "/tmp/x.log")
        assert d == {"logging": {"file": "/tmp/x.log"}}

    def test_del_top_level(self):
        d = {"foo": 1, "bar": 2}
        _del_dotted(d, "foo")
        assert d == {"bar": 2}

    def test_del_nested(self):
        d = {"analytics": {"enabled": True, "id": "abc"}}
        _del_dotted(d, "analytics.enabled")
        assert d == {"analytics": {"id": "abc"}}

    def test_del_missing_is_noop(self):
        d = {"foo": 1}
        _del_dotted(d, "missing.path")
        assert d == {"foo": 1}


# ---------------------------------------------------------------------------
# Key registry
# ---------------------------------------------------------------------------


class TestKeyRegistry:
    def test_user_keys_have_user_tier(self):
        for spec in USER_KEYS:
            assert spec.tier == "user", f"{spec.key} must be user-tier"

    def test_project_keys_have_project_tier(self):
        for spec in PROJECT_KEYS:
            assert spec.tier == "project", f"{spec.key} must be project-tier"

    def test_all_keys_unique(self):
        keys = [spec.key for spec in ALL_KEYS]
        assert len(keys) == len(set(keys))

    def test_default_permission_mode_lists_all_modes(self):
        spec = next(s for s in USER_KEYS if s.key == "default_permission_mode")
        assert spec.editor == "enum"
        assert "auto" in spec.choices
        assert "acceptEdits" in spec.choices
        assert "bypassPermissions" in spec.choices
        assert "plan" in spec.choices
        assert "default" in spec.choices

    def test_awareness_install_helper_text_per_spec(self):
        spec = next(s for s in USER_KEYS if s.key == "awareness.install")
        # SPEC §7.4 mandates three semantic claims.
        assert "Auto-install" in spec.helper or "auto-install" in spec.helper.lower()
        assert "stops new installs" in spec.helper.lower()
        assert "rm" in spec.helper.lower()

    def test_disabled_workflows_helper_uses_level_word(self):
        # SPEC §7.11: user-facing labels use "level" (not "tier").
        spec = next(s for s in PROJECT_KEYS if s.key == "disabled_workflows")
        assert "level" in spec.helper.lower()

    def test_recent_tools_expanded_int_range(self):
        spec = next(s for s in USER_KEYS if s.key == "recent-tools-expanded")
        assert spec.editor == "int"
        assert spec.int_min == 0
        assert spec.int_max == 20

    def test_subscreen_keys(self):
        # Per §7.4: disabled_workflows, disabled_ids both subscreens.
        for key in ("disabled_workflows", "disabled_ids"):
            spec = next(s for s in PROJECT_KEYS if s.key == key)
            assert spec.editor == "subscreen"


# ---------------------------------------------------------------------------
# SettingKey dataclass smoke
# ---------------------------------------------------------------------------


class TestSettingKey:
    def test_frozen(self):
        spec = SettingKey(key="x.y", label="X", tier="user", editor="bool")
        with pytest.raises(Exception):  # FrozenInstanceError or TypeError
            spec.label = "changed"  # type: ignore[misc]

    def test_default_choices_empty(self):
        spec = SettingKey(key="x", label="X", tier="user", editor="bool")
        assert spec.choices == ()
        assert spec.presets == ()
        assert spec.helper == ""
