"""Tests for config.py - configuration management.

Note: Because config.py loads CONFIG at import time using module-level globals,
we test the behaviors indirectly:
1. Direct inspection of _load() function behavior via code review
2. Integration tests via AgentManager (which reads CONFIG)
3. Verification of CONFIG values post-import

The actual config loading is validated through the test_agent_manager_permissions.py
tests which verify AgentManager correctly reads default_permission_mode from CONFIG.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestConfigModuleValues:
    """Test that CONFIG has correct values after module import."""

    def test_config_has_default_permission_mode_key(self):
        """Verify CONFIG contains default_permission_mode key."""
        from claudechic.config import CONFIG

        assert (
            "default_permission_mode" in CONFIG
            or CONFIG.get("default_permission_mode") == "auto"
        ), "CONFIG should have default_permission_mode set"

    def test_config_has_analytics_section(self):
        """Verify CONFIG contains analytics section with required keys."""
        from claudechic.config import CONFIG

        assert "analytics" in CONFIG, "CONFIG should have analytics section"
        assert "id" in CONFIG["analytics"], "analytics should have id"
        assert "enabled" in CONFIG["analytics"], "analytics should have enabled"

    def test_config_has_worktree_section(self):
        """Verify CONFIG contains worktree section."""
        from claudechic.config import CONFIG

        assert "worktree" in CONFIG or CONFIG.setdefault("worktree", {}), (
            "CONFIG should have worktree section"
        )


class TestDefaultPermissionModeValue:
    """Test the default_permission_mode constant in config.py.

    The specification requires:
    - Fresh installs should default to "auto" mode
    - Existing configs preserve their values
    """

    def test_fresh_install_default_is_auto_mode(self):
        """Verify the fresh install config uses 'auto' permission mode.

        Fresh installs should start in 'auto' mode, matching the setdefault
        fallback for existing configs.
        """
        # Read the actual config.py source to verify the default
        from pathlib import Path

        config_source = Path(__file__).parent.parent / "claudechic" / "config.py"
        source_code = config_source.read_text()

        # Verify the fresh install config sets "auto" mode
        assert '"default_permission_mode": "auto"' in source_code, (
            "Fresh install config should set default_permission_mode to 'auto'"
        )

        # Verify it's NOT using bypassPermissions as default
        # (Look for the fresh install block, not existing config handling)
        lines = source_code.split("\n")
        in_fresh_install_block = False
        for _i, line in enumerate(lines):
            if "New install" in line or "new_install = True" in line:
                in_fresh_install_block = True
            if in_fresh_install_block and "default_permission_mode" in line:
                assert '"auto"' in line, (
                    f"Fresh install should use 'auto' mode, found: {line}"
                )
                break

    def test_existing_config_fallback_is_auto_mode(self):
        """Verify existing configs without permission_mode default to 'auto'.

        This handles upgrade scenarios where older configs don't have the key.
        """
        from pathlib import Path

        config_source = Path(__file__).parent.parent / "claudechic" / "config.py"
        source_code = config_source.read_text()

        # The setdefault call should use "auto"
        assert 'setdefault("default_permission_mode", "auto")' in source_code, (
            "Missing default_permission_mode should fallback to 'auto'"
        )


class TestAgentManagerConfigIntegration:
    """Integration tests verifying AgentManager reads config correctly.

    These tests verify the complete flow from CONFIG to AgentManager.
    """

    def test_agent_manager_uses_config_auto(self):
        """Verify AgentManager initializes from CONFIG."""
        with patch.dict(
            "claudechic.agent_manager.CONFIG",
            {"default_permission_mode": "auto"},
        ):
            from claudechic.agent_manager import AgentManager

            manager = AgentManager(MagicMock())
            assert manager.global_permission_mode == "auto", (
                "AgentManager should read 'auto' mode from CONFIG"
            )

    def test_agent_manager_respects_bypass_config(self):
        """Verify existing bypass config is respected."""
        with patch.dict(
            "claudechic.agent_manager.CONFIG",
            {"default_permission_mode": "bypassPermissions"},
        ):
            from claudechic.agent_manager import AgentManager

            manager = AgentManager(MagicMock())
            assert manager.global_permission_mode == "bypassPermissions", (
                "AgentManager should respect bypassPermissions from existing config"
            )

    def test_agent_manager_respects_acceptedits_config(self):
        """Verify existing acceptEdits config is respected."""
        with patch.dict(
            "claudechic.agent_manager.CONFIG",
            {"default_permission_mode": "acceptEdits"},
        ):
            from claudechic.agent_manager import AgentManager

            manager = AgentManager(MagicMock())
            assert manager.global_permission_mode == "acceptEdits"

    def test_agent_manager_respects_plan_config(self):
        """Verify existing plan config is respected."""
        with patch.dict(
            "claudechic.agent_manager.CONFIG",
            {"default_permission_mode": "plan"},
        ):
            from claudechic.agent_manager import AgentManager

            manager = AgentManager(MagicMock())
            assert manager.global_permission_mode == "plan"

    def test_agent_manager_fallback_when_key_missing(self):
        """Verify AgentManager falls back to 'auto' when key is missing."""
        with patch.dict(
            "claudechic.agent_manager.CONFIG",
            {},
            clear=True,
        ):
            from claudechic.agent_manager import AgentManager

            manager = AgentManager(MagicMock())
            assert manager.global_permission_mode == "auto", (
                "AgentManager should fallback to 'auto' when key missing"
            )


class TestAgentInheritance:
    """Test that agents inherit global_permission_mode."""

    def test_create_unconnected_inherits_auto_mode(self):
        """Verify create_unconnected() inherits 'auto' mode."""
        from pathlib import Path

        with patch.dict(
            "claudechic.agent_manager.CONFIG",
            {"default_permission_mode": "auto"},
        ):
            from claudechic.agent_manager import AgentManager

            manager = AgentManager(MagicMock())
            agent = manager.create_unconnected("test", Path("/tmp"))

            assert agent.permission_mode == "auto", (
                "Agent should inherit 'auto' permission mode"
            )

    def test_create_unconnected_inherits_bypass_mode(self):
        """Verify create_unconnected() inherits bypassPermissions when configured."""
        from pathlib import Path

        with patch.dict(
            "claudechic.agent_manager.CONFIG",
            {"default_permission_mode": "bypassPermissions"},
        ):
            from claudechic.agent_manager import AgentManager

            manager = AgentManager(MagicMock())
            agent = manager.create_unconnected("test", Path("/tmp"))

            assert agent.permission_mode == "bypassPermissions", (
                "Agent should inherit bypassPermissions from existing config"
            )


class TestConfigLoadFunction:
    """Test the _load() function's behavior through code inspection.

    Since _load() runs at import time with global paths, we verify
    the function's logic by inspecting the source code structure.
    """

    def test_load_function_handles_missing_file(self):
        """Verify _load() creates config when file doesn't exist."""
        from pathlib import Path

        config_source = Path(__file__).parent.parent / "claudechic" / "config.py"
        source_code = config_source.read_text()

        # Verify there's a branch for when config doesn't exist
        assert "if CONFIG_PATH.exists():" in source_code, (
            "_load() should check if CONFIG_PATH exists"
        )
        assert "else:" in source_code, "_load() should have else branch for new install"
        assert "new_install = True" in source_code, (
            "_load() should set new_install flag"
        )

    def test_load_function_preserves_existing_config(self):
        """Verify _load() reads existing config without overwriting."""
        from pathlib import Path

        config_source = Path(__file__).parent.parent / "claudechic" / "config.py"
        source_code = config_source.read_text()

        # Verify existing configs are loaded, not overwritten
        assert "yaml.safe_load(f)" in source_code, (
            "_load() should read existing config with yaml.safe_load"
        )

        # Verify setdefault is used (doesn't overwrite existing values)
        assert "setdefault(" in source_code, (
            "_load() should use setdefault to preserve existing values"
        )

    def test_load_function_does_not_migrate_legacy_path(self):
        """Per SPEC §2.1, the legacy _OLD_CONFIG_PATH migration is removed.

        Pre-existing files at ``~/.claude/.claudechic.yaml`` or
        ``~/.claude/claudechic.yaml`` are left in place; claudechic does NOT
        rename, unlink, or warn about them. The user-config now lives at
        ``~/.claudechic/config.yaml`` (file-form → directory-form move).
        """
        from pathlib import Path

        config_source = Path(__file__).parent.parent / "claudechic" / "config.py"
        source_code = config_source.read_text()

        assert "_OLD_CONFIG_PATH" not in source_code, (
            "Legacy _OLD_CONFIG_PATH constant must be removed (SPEC §2.1)"
        )
        assert ".rename(CONFIG_PATH)" not in source_code, (
            "Legacy migration rename() call must be removed (SPEC §2.1)"
        )


class TestConfigSaveFunction:
    """Test the _save() function's behavior."""

    def test_save_function_writes_atomically(self):
        """Verify _save() uses atomic write pattern."""
        from pathlib import Path

        config_source = Path(__file__).parent.parent / "claudechic" / "config.py"
        source_code = config_source.read_text()

        # Verify atomic write pattern (tempfile + rename)
        assert "tempfile.mkstemp" in source_code, (
            "_save() should use tempfile for atomic write"
        )
        assert "os.replace" in source_code, (
            "_save() should use os.replace for atomic rename"
        )


class TestVimMigration:
    """Test vim -> vi-mode migration logic."""

    def test_vim_migration_logic_exists(self):
        """Verify vim to vi-mode migration code exists."""
        from pathlib import Path

        config_source = Path(__file__).parent.parent / "claudechic" / "config.py"
        source_code = config_source.read_text()

        # Verify migration from vim to vi-mode
        assert '"vim" in config' in source_code, "Should check for legacy 'vim' key"
        assert 'config["vi-mode"]' in source_code or "vi-mode" in source_code, (
            "Should migrate to 'vi-mode' key"
        )


# ---------------------------------------------------------------------------
# constraints_segment / environment_segment parsing (SPEC §3.7, §3.11)
# Scenario 6 coverage: project-tier YAML round-trip + ConfigValidationError
# on empty scope.sites.
# ---------------------------------------------------------------------------


import pytest  # noqa: E402  -- module-level top-half is class-only; tests below use pytest


pytestmark_segment = [pytest.mark.timeout(30)]


def _write_project_yaml(project_dir, body: str):
    """Write <project_dir>/.claudechic/config.yaml with the given body."""
    cfg_dir = project_dir / ".claudechic"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "config.yaml").write_text(body, encoding="utf-8")


@pytest.mark.timeout(30)
def test_project_config_constraints_segment_round_trips_through_save_load(tmp_path):
    """Project-tier config.yaml: write constraints_segment, load it back, get the same data."""
    from claudechic.config import ProjectConfig

    yaml_body = (
        "constraints_segment:\n"
        "  compact: false\n"
        "  include_skipped: true\n"
        "  scope:\n"
        "    sites:\n"
        "      - spawn\n"
        "      - activation\n"
    )
    _write_project_yaml(tmp_path, yaml_body)

    pc = ProjectConfig.load(tmp_path)
    assert pc.constraints_segment.get("compact") is False
    assert pc.constraints_segment.get("include_skipped") is True
    assert pc.constraints_segment.get("sites") == frozenset({"spawn", "activation"})


@pytest.mark.timeout(30)
def test_project_config_environment_segment_round_trips_through_save_load(tmp_path):
    """Project-tier environment_segment is parsed into the in-memory dict shape."""
    from claudechic.config import ProjectConfig

    yaml_body = (
        "environment_segment:\n"
        "  enabled: false\n"
        "  compact: true\n"
        "  scope:\n"
        "    sites:\n"
        "      - spawn\n"
    )
    _write_project_yaml(tmp_path, yaml_body)

    pc = ProjectConfig.load(tmp_path)
    assert pc.environment_segment.get("enabled") is False
    assert pc.environment_segment.get("compact") is True
    assert pc.environment_segment.get("sites") == frozenset({"spawn"})


@pytest.mark.timeout(30)
def test_project_config_constraints_segment_empty_scope_sites_raises_config_validation_error(
    tmp_path,
):
    """Empty constraints_segment.scope.sites at load time raises ConfigValidationError."""
    from claudechic.config import ConfigValidationError, ProjectConfig

    yaml_body = "constraints_segment:\n  scope:\n    sites: []\n"
    _write_project_yaml(tmp_path, yaml_body)

    with pytest.raises(ConfigValidationError):
        ProjectConfig.load(tmp_path)


@pytest.mark.timeout(30)
def test_project_config_environment_segment_empty_scope_sites_raises_config_validation_error(
    tmp_path,
):
    """Empty environment_segment.scope.sites at load time raises ConfigValidationError."""
    from claudechic.config import ConfigValidationError, ProjectConfig

    yaml_body = "environment_segment:\n  scope:\n    sites: []\n"
    _write_project_yaml(tmp_path, yaml_body)

    with pytest.raises(ConfigValidationError):
        ProjectConfig.load(tmp_path)


@pytest.mark.timeout(30)
def test_project_config_unknown_site_token_dropped_with_warning(tmp_path):
    """An unknown site token is dropped with a WARNING; valid tokens survive."""
    from claudechic.config import ProjectConfig

    yaml_body = (
        "constraints_segment:\n"
        "  scope:\n"
        "    sites:\n"
        "      - spawn\n"
        "      - bogus_site\n"
    )
    _write_project_yaml(tmp_path, yaml_body)

    pc = ProjectConfig.load(tmp_path)
    sites = pc.constraints_segment.get("sites")
    assert sites == frozenset({"spawn"}), (
        f"Unknown token must be dropped; got {sites}"
    )


@pytest.mark.timeout(30)
def test_project_config_constraints_segment_missing_uses_empty_dict(tmp_path):
    """When the YAML omits constraints_segment, ProjectConfig.constraints_segment is {}."""
    from claudechic.config import ProjectConfig

    yaml_body = "guardrails: true\n"
    _write_project_yaml(tmp_path, yaml_body)

    pc = ProjectConfig.load(tmp_path)
    assert pc.constraints_segment == {}
    assert pc.environment_segment == {}


@pytest.mark.timeout(30)
def test_build_gate_settings_project_tier_overrides_user_tier(tmp_path):
    """build_gate_settings: project tier wins per-key (SPEC §3.7, §3.11)."""
    from claudechic.config import ProjectConfig, build_gate_settings

    user_config = {
        "constraints_segment": {
            "compact": True,
            "scope": {"sites": ["spawn", "activation", "phase-advance", "post-compact"]},
        },
    }
    yaml_body = (
        "constraints_segment:\n"
        "  compact: false\n"
        "  scope:\n"
        "    sites:\n"
        "      - spawn\n"
    )
    _write_project_yaml(tmp_path, yaml_body)
    pc = ProjectConfig.load(tmp_path)

    settings = build_gate_settings(user_config=user_config, project_config=pc)
    # Project tier wins: compact=False overrides user's True; sites narrowed to {spawn}.
    assert settings.constraints_segment.compact is False
    assert settings.constraints_segment.sites == frozenset({"spawn"})
