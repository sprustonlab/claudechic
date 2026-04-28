"""E2E tests: Audit trail (hits.jsonl) logging when rules fire.

Intent: "When a rule fires, is it logged to the JSONL audit trail?"
"""

from __future__ import annotations

import json

import pytest
import yaml
from claudechic.guardrails.hits import HitLogger
from claudechic.guardrails.hooks import create_guardrail_hooks
from claudechic.guardrails.tokens import OverrideTokenStore
from claudechic.workflows import register_default_parsers
from claudechic.workflows.loader import ManifestLoader

pytestmark = [pytest.mark.asyncio, pytest.mark.timeout(30)]


class TestWorkflowHitsLogging:
    """E2E: Rule hits produce a JSONL audit trail."""

    async def test_rule_hit_logged_to_jsonl(self, tmp_path):
        """Trigger a deny rule through the full pipeline → verify JSONL record."""
        # Set up manifests
        global_dir = tmp_path / "global"
        global_dir.mkdir(parents=True)
        rules = [
            {
                "id": "no_sudo",
                "trigger": "PreToolUse/Bash",
                "enforcement": "deny",
                "detect": {"pattern": r"\bsudo\b"},
                "message": "No sudo allowed",
            }
        ]
        (global_dir / "rules.yaml").write_text(yaml.dump(rules))
        (tmp_path / "workflows").mkdir()

        loader = ManifestLoader(global_dir, tmp_path / "workflows")
        register_default_parsers(loader)

        hits_path = tmp_path / ".claudechic" / "hits.jsonl"
        hit_logger = HitLogger(hits_path)
        token_store = OverrideTokenStore()

        try:
            hooks = create_guardrail_hooks(
                loader=loader,
                hit_logger=hit_logger,
                agent_role="coder",
                consume_override=token_store.consume,
            )

            # Trigger the deny rule
            matchers = hooks["PreToolUse"]
            hook_fn = matchers[0].hooks[0]
            result = await hook_fn(
                {"tool_name": "Bash", "tool_input": {"command": "sudo rm -rf /"}},
                None,
                None,
            )

            assert result.get("decision") == "block"

            # Verify JSONL audit file
            assert hits_path.exists(), "hits.jsonl should have been created"
            lines = hits_path.read_text().strip().split("\n")
            assert len(lines) >= 1

            record = json.loads(lines[0])
            assert record["rule_id"] == "global:no_sudo"
            assert record["agent_role"] == "coder"
            assert record["tool_name"] == "Bash"
            assert record["enforcement"] == "deny"
            assert record["outcome"] == "blocked"
            assert isinstance(record["timestamp"], float)
        finally:
            hit_logger.close()

    async def test_log_enforcement_allows_and_logs(self, tmp_path):
        """Log-level rule allows the action AND records an audit entry."""
        global_dir = tmp_path / "global"
        global_dir.mkdir(parents=True)
        rules = [
            {
                "id": "track_writes",
                "trigger": "PreToolUse/Write",
                "enforcement": "log",
                "message": "Tracking file writes",
            }
        ]
        (global_dir / "rules.yaml").write_text(yaml.dump(rules))
        (tmp_path / "workflows").mkdir()

        loader = ManifestLoader(global_dir, tmp_path / "workflows")
        register_default_parsers(loader)

        hits_path = tmp_path / ".claudechic" / "hits.jsonl"
        hit_logger = HitLogger(hits_path)

        try:
            hooks = create_guardrail_hooks(loader=loader, hit_logger=hit_logger)

            matchers = hooks["PreToolUse"]
            hook_fn = matchers[0].hooks[0]
            result = await hook_fn(
                {
                    "tool_name": "Write",
                    "tool_input": {"file_path": "/tmp/x.py", "content": "hi"},
                },
                None,
                None,
            )

            # Log enforcement should allow
            assert result == {} or result.get("decision") != "block"

            # But still logs the hit
            assert hits_path.exists()
            lines = hits_path.read_text().strip().split("\n")
            assert len(lines) >= 1
            record = json.loads(lines[0])
            assert record["rule_id"] == "global:track_writes"
            assert record["enforcement"] == "log"
            assert record["outcome"] == "allowed"
        finally:
            hit_logger.close()

    async def test_multiple_hits_append_to_same_file(self, tmp_path):
        """Multiple rule hits append correctly to the same JSONL file."""
        global_dir = tmp_path / "global"
        global_dir.mkdir(parents=True)
        rules = [
            {
                "id": "track_bash",
                "trigger": "PreToolUse/Bash",
                "enforcement": "log",
                "message": "Tracking bash",
            }
        ]
        (global_dir / "rules.yaml").write_text(yaml.dump(rules))
        (tmp_path / "workflows").mkdir()

        loader = ManifestLoader(global_dir, tmp_path / "workflows")
        register_default_parsers(loader)

        hits_path = tmp_path / ".claudechic" / "hits.jsonl"
        hit_logger = HitLogger(hits_path)

        try:
            hooks = create_guardrail_hooks(loader=loader, hit_logger=hit_logger)
            hook_fn = hooks["PreToolUse"][0].hooks[0]

            # Fire 3 times
            for cmd in ["echo one", "echo two", "echo three"]:
                await hook_fn(
                    {"tool_name": "Bash", "tool_input": {"command": cmd}},
                    None,
                    None,
                )

            lines = hits_path.read_text().strip().split("\n")
            assert len(lines) == 3
            for line in lines:
                record = json.loads(line)
                assert record["rule_id"] == "global:track_bash"
        finally:
            hit_logger.close()
