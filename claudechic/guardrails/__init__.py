"""SDK-based guardrail hook system — evaluates rules.yaml via PreToolUse hooks."""

from claudechic.guardrails.hits import HitLogger, HitRecord
from claudechic.guardrails.hooks import (
    GetActiveWfCallback,
    GetPhaseCallback,
    OverrideTokenConsumer,
    create_guardrail_hooks,
)
from claudechic.guardrails.parsers import InjectionsParser, RulesParser
from claudechic.guardrails.rules import (
    Injection,
    Rule,
    apply_injection,
    load_rules,
    match_rule,
    matches_trigger,
    should_skip_for_phase,
    should_skip_for_role,
)
from claudechic.guardrails.tokens import OverrideToken, OverrideTokenStore

__all__ = [
    # rules.py
    "Rule",
    "Injection",
    "load_rules",
    "matches_trigger",
    "match_rule",
    "should_skip_for_role",
    "should_skip_for_phase",
    "apply_injection",
    # hooks.py
    "create_guardrail_hooks",
    "GetPhaseCallback",
    "GetActiveWfCallback",
    "OverrideTokenConsumer",
    # hits.py
    "HitRecord",
    "HitLogger",
    # parsers.py
    "RulesParser",
    "InjectionsParser",
    # tokens.py
    "OverrideToken",
    "OverrideTokenStore",
]
