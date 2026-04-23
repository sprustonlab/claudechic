"""Integration tests for ProjectConfig + workflow infrastructure.

Boot real TUI (SDK mocked), real ManifestLoader, real YAML parsing.
Only mock boundary: ClaudeSDKClient, FileIndex, analytics (via mock_sdk fixture).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from claudechic.app import ChatApp


@pytest.fixture
def _cwd_to_tmp(tmp_path, monkeypatch):
    """Make ChatApp._cwd resolve to tmp_path during on_mount."""
    monkeypatch.setattr(Path, "cwd", staticmethod(lambda: tmp_path))
    return tmp_path


@pytest.mark.integration
@pytest.mark.asyncio
async def test_default_config_loads_rules_and_hints(mock_sdk, _cwd_to_tmp):
    """No .claudechic.yaml -> all bundled rules, hints, and injections load."""
    app = ChatApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        # ProjectConfig defaults
        cfg = app._project_config
        assert cfg is not None
        assert cfg.guardrails is True
        assert cfg.hints is True
        assert cfg.disabled_workflows == frozenset()
        assert cfg.disabled_ids == frozenset()

        # Bundled content loaded
        lr = app._load_result
        assert lr is not None
        assert len(lr.rules) > 0, "Expected bundled rules"
        assert len(lr.hints) > 0, "Expected bundled hints"
        assert len(lr.injections) > 0, "Expected bundled injections"
        assert lr.errors == [], f"Unexpected parse errors: {lr.errors}"

        # Workflows discovered
        assert len(app._workflow_registry) > 0, "Expected at least one workflow"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_all_toggles_off_skips_rules_and_hints(mock_sdk, _cwd_to_tmp, tmp_path):
    """guardrails:false + hints:false -> rules=[], hints=[], injections survive."""
    config_data = {"guardrails": False, "hints": False}
    (tmp_path / ".claudechic.yaml").write_text(yaml.dump(config_data), encoding="utf-8")

    app = ChatApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        cfg = app._project_config
        assert cfg.guardrails is False
        assert cfg.hints is False

        lr = app._load_result
        assert lr.rules == [], "Rules should be empty when guardrails=false"
        assert lr.hints == [], "Hints should be empty when hints=false"
        assert len(lr.injections) > 0, "Injections must survive both toggles"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_disabled_workflow_and_ids_not_available(mock_sdk, _cwd_to_tmp, tmp_path):
    """disabled_workflows + disabled_ids filter selectively."""
    config_data = {
        "disabled_workflows": ["audit", "tutorial"],
        "disabled_ids": ["global:no_bare_pytest"],
    }
    (tmp_path / ".claudechic.yaml").write_text(yaml.dump(config_data), encoding="utf-8")

    app = ChatApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        lr = app._load_result
        assert lr is not None

        # --- disabled_workflows: audit removed ---
        assert "audit" not in app._workflow_registry
        assert "audit" not in lr.workflows
        assert all(p.namespace != "audit" for p in lr.phases), (
            "Audit phases should be filtered"
        )

        # --- disabled_workflows: tutorial removed (including its injection) ---
        assert "tutorial" not in app._workflow_registry
        assert "tutorial" not in lr.workflows
        assert all(
            getattr(inj, "namespace", "") != "tutorial" for inj in lr.injections
        ), "Tutorial injection should be filtered by disabled_workflows"
        # tutorial is the only source of injections, so list should be empty
        assert lr.injections == [], (
            "All injections should be gone since tutorial (only source) is disabled"
        )

        # --- disabled_ids: global:no_bare_pytest removed ---
        rule_ids = [r.id for r in lr.rules]
        assert "global:no_bare_pytest" not in rule_ids, (
            "no_bare_pytest should be filtered by disabled_ids"
        )
        # Other global rules survive
        global_rules = [r for r in lr.rules if getattr(r, "namespace", "") == "global"]
        assert len(global_rules) > 0, (
            "Other global rules should survive selective disabled_ids"
        )

        # --- Other workflows survive ---
        assert len(app._workflow_registry) > 0, "Non-disabled workflows should remain"
        assert "project_team" in app._workflow_registry or len(lr.workflows) > 0
