"""Bug #12: detect_field should default based on trigger tool name.

Write/Edit/Read tools use file_path, not command. Without trigger-aware
defaults, detect patterns silently match against an empty string.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from claudechic.guardrails.hits import HitLogger
from claudechic.guardrails.hooks import create_guardrail_hooks
from claudechic.guardrails.tokens import OverrideTokenStore
from claudechic.workflow_engine import register_default_parsers
from claudechic.workflow_engine.loader import ManifestLoader

pytestmark = [pytest.mark.asyncio, pytest.mark.timeout(30)]


def _setup_rules(
    root: Path, rules: list[dict], injections: list[dict] | None = None
) -> ManifestLoader:
    """Create global/rules.yaml (and optionally injections.yaml), return loader."""
    global_dir = root / "global"
    global_dir.mkdir(parents=True, exist_ok=True)
    (global_dir / "rules.yaml").write_text(yaml.dump(rules), encoding="utf-8")
    if injections:
        (global_dir / "injections.yaml").write_text(
            yaml.dump(injections), encoding="utf-8"
        )
    wf_dir = root / "workflows"
    wf_dir.mkdir(exist_ok=True)

    loader = ManifestLoader(global_dir, wf_dir)
    register_default_parsers(loader)
    return loader


async def _call_hook(hooks: dict, tool_name: str, tool_input: dict) -> dict:
    """Invoke the PreToolUse hook evaluate function."""
    matchers = hooks.get("PreToolUse", [])
    assert len(matchers) > 0, "No PreToolUse hooks created"
    hook_fn = matchers[0].hooks[0]
    return await hook_fn(
        {"tool_name": tool_name, "tool_input": tool_input},
        None,
        None,
    )


class TestDetectFieldDefaults:
    """Bug #12: trigger-aware detect_field defaults."""

    async def test_write_rule_blocks_env_file(self, tmp_path):
        """PreToolUse/Write rule with .env pattern blocks Write to .env file."""
        rules = [
            {
                "id": "no_env_write",
                "trigger": "PreToolUse/Write",
                "enforcement": "deny",
                "detect": {"pattern": r"\.env$"},
                "message": "Do not write .env files",
            }
        ]
        loader = _setup_rules(tmp_path, rules)
        hit_logger = HitLogger(tmp_path / ".claude" / "hits.jsonl")
        token_store = OverrideTokenStore()

        try:
            hooks = create_guardrail_hooks(
                loader=loader,
                hit_logger=hit_logger,
                consume_override=token_store.consume,
            )
            result = await _call_hook(
                hooks,
                "Write",
                {"file_path": "secrets/.env", "content": "API_KEY=xxx"},
            )
            assert result.get("decision") == "block", (
                "Write rule should block .env file (detect_field should default to file_path)"
            )
        finally:
            hit_logger.close()

    async def test_edit_rule_blocks_env_file(self, tmp_path):
        """PreToolUse/Edit rule with .env pattern blocks Edit to .env file."""
        rules = [
            {
                "id": "no_env_edit",
                "trigger": "PreToolUse/Edit",
                "enforcement": "deny",
                "detect": {"pattern": r"\.env$"},
                "message": "Do not edit .env files",
            }
        ]
        loader = _setup_rules(tmp_path, rules)
        hit_logger = HitLogger(tmp_path / ".claude" / "hits.jsonl")
        token_store = OverrideTokenStore()

        try:
            hooks = create_guardrail_hooks(
                loader=loader,
                hit_logger=hit_logger,
                consume_override=token_store.consume,
            )
            result = await _call_hook(
                hooks,
                "Edit",
                {"file_path": "secrets/.env", "old_string": "x", "new_string": "y"},
            )
            assert result.get("decision") == "block", (
                "Edit rule should block .env file (detect_field should default to file_path)"
            )
        finally:
            hit_logger.close()

    async def test_bash_still_defaults_to_command(self, tmp_path):
        """PreToolUse/Bash still defaults detect_field to command (regression guard)."""
        rules = [
            {
                "id": "no_dangerous_cmd",
                "trigger": "PreToolUse/Bash",
                "enforcement": "deny",
                "detect": {"pattern": r"echo\s+DANGER"},
                "message": "No dangerous echo",
            }
        ]
        loader = _setup_rules(tmp_path, rules)
        hit_logger = HitLogger(tmp_path / ".claude" / "hits.jsonl")
        token_store = OverrideTokenStore()

        try:
            hooks = create_guardrail_hooks(
                loader=loader,
                hit_logger=hit_logger,
                consume_override=token_store.consume,
            )
            result = await _call_hook(hooks, "Bash", {"command": "echo DANGER"})
            assert result.get("decision") == "block", (
                "Bash rule should still match against command field"
            )
        finally:
            hit_logger.close()

    async def test_explicit_field_overrides_default(self, tmp_path):
        """Explicit detect.field overrides the trigger-aware default."""
        rules = [
            {
                "id": "no_secret_content",
                "trigger": "PreToolUse/Write",
                "enforcement": "deny",
                "detect": {"pattern": r"API_KEY", "field": "content"},
                "message": "No API keys in content",
            }
        ]
        loader = _setup_rules(tmp_path, rules)
        hit_logger = HitLogger(tmp_path / ".claude" / "hits.jsonl")
        token_store = OverrideTokenStore()

        try:
            hooks = create_guardrail_hooks(
                loader=loader,
                hit_logger=hit_logger,
                consume_override=token_store.consume,
            )
            result = await _call_hook(
                hooks,
                "Write",
                {"file_path": "config.txt", "content": "API_KEY=secret"},
            )
            assert result.get("decision") == "block", (
                "Explicit detect.field=content should override default file_path"
            )
        finally:
            hit_logger.close()
