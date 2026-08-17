"""Guardrail deny rule for browser control (layer 2 of the gate).

Parses the bundled ``claudechic/defaults/global/rules.yaml`` with the
real RulesParser and asserts the ``global:browser_control`` rule:

* exists, enforcement ``deny``;
* has NO detect pattern, so it fires on EVERY invocation;
* triggers on all five ``mcp__chic__browser_*`` tool names and on
  nothing else.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from claudechic.guardrails.parsers import RulesParser
from claudechic.guardrails.rules import match_rule, matches_trigger

RULES_YAML = (
    Path(__file__).resolve().parents[1]
    / "claudechic"
    / "defaults"
    / "global"
    / "rules.yaml"
)

BROWSER_MCP_TOOL_NAMES = [
    "mcp__chic__browser_navigate",
    "mcp__chic__browser_screenshot",
    "mcp__chic__browser_click",
    "mcp__chic__browser_type",
    "mcp__chic__browser_scroll",
]


def _load_browser_control_rule():
    with RULES_YAML.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    assert isinstance(raw, list), "rules.yaml must be a bare list of rules"
    rules = RulesParser().parse(raw, namespace="global", source_path=str(RULES_YAML))
    for rule in rules:
        if rule.id == "global:browser_control":
            return rule
    raise AssertionError("global:browser_control rule not found in rules.yaml")


def test_rule_exists_and_denies():
    rule = _load_browser_control_rule()
    assert rule.enforcement == "deny"
    assert rule.namespace == "global"
    assert rule.message, "rule must carry a user-facing message"
    # Message must point at the per-session enable path (Guards sidebar
    # toggle); the phrase wraps across YAML lines, so match its anchor.
    assert "global:browser_control" in rule.message
    assert "Guards" in rule.message


def test_rule_has_no_detect_pattern():
    """No detect block: the rule must fire on every invocation."""
    rule = _load_browser_control_rule()
    assert rule.detect_pattern is None


def test_rule_triggers_on_all_five_browser_tools():
    rule = _load_browser_control_rule()
    for tool_name in BROWSER_MCP_TOOL_NAMES:
        assert matches_trigger(rule, tool_name), f"trigger missing: {tool_name}"


def test_rule_does_not_trigger_on_other_tools():
    rule = _load_browser_control_rule()
    for tool_name in ("mcp__chic__whoami", "Bash", "mcp__chic__message_agent"):
        assert not matches_trigger(rule, tool_name), (
            f"rule over-triggers on {tool_name}"
        )


def test_rule_matches_arbitrary_input():
    """With no detect pattern, match_rule is True for any tool_input."""
    rule = _load_browser_control_rule()
    assert match_rule(rule, "mcp__chic__browser_navigate", {})
    assert match_rule(
        rule, "mcp__chic__browser_navigate", {"url": "https://example.com"}
    )
    assert match_rule(rule, "mcp__chic__browser_click", {"selector": "#a"})
