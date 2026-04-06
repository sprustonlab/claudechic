"""E2E tests: Rules block/warn the agent through the hook pipeline.

Intent: "When the agent tries something forbidden, does the user see
the right enforcement response?"
"""

from __future__ import annotations

import json
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from claudechic.app import ChatApp
from claudechic.guardrails.hits import HitLogger
from claudechic.guardrails.tokens import OverrideTokenStore
from claudechic.workflows.loader import ManifestLoader
from claudechic.workflows import register_default_parsers
from claudechic.guardrails.hooks import create_guardrail_hooks

pytestmark = [pytest.mark.asyncio, pytest.mark.timeout(30)]


def _setup_rules(root: Path, rules: list[dict], injections: list[dict] | None = None) -> ManifestLoader:
    """Create global/rules.yaml (and optionally injections.yaml), return loader."""
    global_dir = root / "global"
    global_dir.mkdir(parents=True, exist_ok=True)
    (global_dir / "rules.yaml").write_text(yaml.dump(rules))
    if injections:
        (global_dir / "injections.yaml").write_text(yaml.dump(injections))
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


class TestGuardrailRules:
    """E2E: Rules evaluated through the full hook pipeline."""

    async def test_deny_rule_blocks_tool_use(self, tmp_path):
        """Deny rule returns block decision for matching tool input."""
        rules = [
            {
                "id": "no_rm_rf",
                "trigger": "PreToolUse/Bash",
                "enforcement": "deny",
                "detect": {"pattern": r"rm\s+-rf"},
                "message": "Dangerous: rm -rf not allowed",
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

            result = await _call_hook(hooks, "Bash", {"command": "rm -rf /"})

            assert result.get("decision") == "block"
            assert "rm -rf" in result.get("reason", "").lower() or "Dangerous" in result.get("reason", "")

            # Verify hit logged
            lines = (tmp_path / ".claude" / "hits.jsonl").read_text().strip().split("\n")
            assert len(lines) >= 1
            record = json.loads(lines[0])
            assert record["rule_id"] == "global:no_rm_rf"
            assert record["enforcement"] == "deny"
            assert record["outcome"] == "blocked"
        finally:
            hit_logger.close()

    async def test_warn_rule_blocks_without_token(self, tmp_path):
        """Warn rule blocks when no override token is available."""
        rules = [
            {
                "id": "warn_pip",
                "trigger": "PreToolUse/Bash",
                "enforcement": "warn",
                "detect": {"pattern": r"\bpip\b"},
                "message": "Prefer uv over pip",
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

            result = await _call_hook(hooks, "Bash", {"command": "pip install requests"})
            assert result.get("decision") == "block"
            assert "acknowledge_warning" in result.get("reason", "")
        finally:
            hit_logger.close()

    async def test_phase_scoped_rule_fires_only_in_correct_phase(self, tmp_path):
        """Rule with phases=['design'] fires in design, not in implement."""
        global_dir = tmp_path / "global"
        global_dir.mkdir(parents=True)
        wf_dir = tmp_path / "workflows" / "proj"
        wf_dir.mkdir(parents=True)

        wf_manifest = {
            "workflow_id": "proj",
            "phases": [
                {"id": "design"},
                {"id": "implement"},
            ],
            "rules": [
                {
                    "id": "design_only",
                    "trigger": "PreToolUse/Bash",
                    "enforcement": "deny",
                    "detect": {"pattern": r"make build"},
                    "message": "No building in design phase",
                    "phases": ["design"],
                }
            ],
        }
        (wf_dir / "proj.yaml").write_text(yaml.dump(wf_manifest))

        loader = ManifestLoader(global_dir, wf_dir.parent)
        register_default_parsers(loader)
        hit_logger = HitLogger(tmp_path / ".claude" / "hits.jsonl")
        token_store = OverrideTokenStore()

        try:
            # In design phase → rule should fire
            hooks_design = create_guardrail_hooks(
                loader=loader,
                hit_logger=hit_logger,
                get_phase=lambda: "proj:design",
                get_active_wf=lambda: "proj",
                consume_override=token_store.consume,
            )
            result = await _call_hook(hooks_design, "Bash", {"command": "make build"})
            assert result.get("decision") == "block", "Rule should fire in design phase"

            # In implement phase → rule should NOT fire
            hooks_impl = create_guardrail_hooks(
                loader=loader,
                hit_logger=hit_logger,
                get_phase=lambda: "proj:implement",
                get_active_wf=lambda: "proj",
                consume_override=token_store.consume,
            )
            result = await _call_hook(hooks_impl, "Bash", {"command": "make build"})
            assert result.get("decision") != "block", "Rule should NOT fire in implement phase"
        finally:
            hit_logger.close()

    async def test_injection_modifies_tool_input(self, tmp_path):
        """Injection appends to tool_input through the full hook pipeline."""
        injections = [
            {
                "id": "tee_output",
                "trigger": "PreToolUse/Bash",
                "detect": {"pattern": r"pytest"},
                "inject_value": " 2>&1 | tee test_output.log",
            }
        ]
        loader = _setup_rules(tmp_path, rules=[], injections=injections)
        hit_logger = HitLogger(tmp_path / ".claude" / "hits.jsonl")
        token_store = OverrideTokenStore()

        try:
            hooks = create_guardrail_hooks(
                loader=loader,
                hit_logger=hit_logger,
                consume_override=token_store.consume,
            )

            # The hook modifies tool_input via injections and returns updatedInput
            result = await _call_hook(hooks, "Bash", {"command": "pytest tests/"})
            assert result.get("decision") != "block", "Injection should not block"

            # Verify: injection returns modified tool_input via SDK protocol
            hook_output = result.get("hookSpecificOutput", {})
            assert hook_output.get("hookEventName") == "PreToolUse"
            updated = hook_output.get("updatedInput", {})
            assert updated["command"] == "pytest tests/ 2>&1 | tee test_output.log"
        finally:
            hit_logger.close()

    async def test_non_matching_rule_allows_through(self, tmp_path):
        """Rule that doesn't match the tool input allows the action."""
        rules = [
            {
                "id": "no_rm_rf",
                "trigger": "PreToolUse/Bash",
                "enforcement": "deny",
                "detect": {"pattern": r"rm\s+-rf"},
                "message": "Dangerous",
            }
        ]
        loader = _setup_rules(tmp_path, rules)
        hit_logger = HitLogger(tmp_path / ".claude" / "hits.jsonl")

        try:
            hooks = create_guardrail_hooks(loader=loader, hit_logger=hit_logger)
            result = await _call_hook(hooks, "Bash", {"command": "echo hello"})
            assert result == {}, "Non-matching rule should allow through"
        finally:
            hit_logger.close()

    async def test_fail_closed_on_unreadable_global_dir(self, tmp_path):
        """R2: When global/ is unreadable, hook blocks ALL tool calls.

        This is the most important safety property — if it fails open,
        rules are silently disabled. The hook must detect the fatal
        discovery error and block everything.
        """
        from unittest.mock import patch

        # Create a loader pointing to a valid-looking but rigged setup
        global_dir = tmp_path / "global"
        global_dir.mkdir()
        wf_dir = tmp_path / "workflows"
        wf_dir.mkdir()

        loader = ManifestLoader(global_dir, wf_dir)
        register_default_parsers(loader)
        hit_logger = HitLogger(tmp_path / ".claude" / "hits.jsonl")

        try:
            # Patch _discover to raise OSError (simulates unreadable dir)
            with patch.object(loader, "_discover", side_effect=OSError("Permission denied")):
                hooks = create_guardrail_hooks(
                    loader=loader,
                    hit_logger=hit_logger,
                )

                # Even a benign tool call should be blocked
                result = await _call_hook(hooks, "Bash", {"command": "echo hello"})
                assert result.get("decision") == "block", (
                    "Fatal discovery error must block ALL tool calls (fail-closed)"
                )
                assert "unavailable" in result.get("message", "").lower()
        finally:
            hit_logger.close()


class TestTokenEnforcementIsolation:
    """SEC1: Warn-level tokens cannot satisfy deny-level rules."""

    def test_warn_token_cannot_satisfy_deny(self):
        """SEC1 regression: store with enforcement='warn', consume with 'deny' → False."""
        store = OverrideTokenStore()
        tool_input = {"command": "rm -rf /"}
        store.store("rule1", "Bash", tool_input, enforcement="warn")

        # Attempting to consume at deny level must fail
        consumed = store.consume("rule1", "Bash", tool_input, enforcement="deny")
        assert consumed is False, (
            "SECURITY: warn-level token must NOT satisfy deny-level rule"
        )

    def test_deny_token_satisfies_deny(self):
        """Happy path: store with enforcement='deny', consume with 'deny' → True."""
        store = OverrideTokenStore()
        tool_input = {"command": "rm -rf /"}
        store.store("rule1", "Bash", tool_input, enforcement="deny")

        consumed = store.consume("rule1", "Bash", tool_input, enforcement="deny")
        assert consumed is True, "Deny-level token should satisfy deny-level rule"

    def test_token_is_one_time_use(self):
        """Override token consumed once cannot be reused."""
        store = OverrideTokenStore()
        tool_input = {"command": "dangerous"}
        store.store("rule1", "Bash", tool_input, enforcement="deny")

        assert store.consume("rule1", "Bash", tool_input, enforcement="deny") is True
        assert store.consume("rule1", "Bash", tool_input, enforcement="deny") is False
