"""SDK hook closure creation — evaluates rules via PreToolUse hooks.

Extracted from app.py. Two-step pipeline: injections first, then enforcement.

Imports: sibling modules (rules, hits) + claude_agent_sdk.types.
NEVER imports from workflows/, app.py, or widgets/.
All engine/token/phase concerns arrive as callbacks.
"""

from __future__ import annotations

import dataclasses
import time
from typing import TYPE_CHECKING, Any, Callable

from claude_agent_sdk.types import HookMatcher

from claudechic.guardrails.hits import HitLogger, HitRecord
from claudechic.guardrails.rules import (
    _get_field,
    apply_injection,
    matches_trigger,
    should_skip_for_phase,
    should_skip_for_role,
)

if TYPE_CHECKING:
    from claudechic.workflows.loader import ManifestLoader

# Type aliases for callback signatures
GetPhaseCallback = Callable[[], str | None]
GetActiveWfCallback = Callable[[], str | None]
OverrideTokenConsumer = Callable[[str, str, dict, str], bool]  # (rule_id, tool_name, tool_input, enforcement) -> consumed


def create_guardrail_hooks(
    loader: ManifestLoader,
    hit_logger: HitLogger,
    agent_role: str | None = None,
    get_phase: GetPhaseCallback | None = None,
    get_active_wf: GetActiveWfCallback | None = None,
    consume_override: OverrideTokenConsumer | None = None,
) -> dict[str, list[HookMatcher]]:
    """Create PreToolUse hooks that evaluate rules (all enforcement levels).

    Args:
        loader: Shared ManifestLoader instance (created once at app init,
                reused across all hook closures — parsers registered once).
        hit_logger: Shared HitLogger for audit trail.
        agent_role: Role type captured at agent creation time.
        get_phase: Callback returning current phase (in-memory engine lookup).
                   If None, phase filtering is skipped.
        get_active_wf: Callback returning the active workflow_id (in-memory).
                       If None, all workflow rules evaluate (no namespace filter).
        consume_override: Callback that checks and consumes a one-time override
                         token for a deny rule. Returns True if token was consumed.
                         If None, no overrides are possible.
    """

    async def evaluate(hook_input: dict, match: str | None, ctx: object) -> dict:
        tool_name = hook_input.get("tool_name", "")
        tool_input = hook_input.get("tool_input", {})
        original_tool_input = tool_input  # Track for injection detection

        # Load rules fresh every call (no mtime caching — NFS safe)
        result = loader.load()

        # Fail-closed check
        if result.errors and not result.rules:
            fatal = any(e.source == "discovery" for e in result.errors)
            if fatal:
                return {
                    "decision": "block",
                    "message": "Rules unavailable — global/ or workflows/ unreadable",
                }

        current_phase = get_phase() if get_phase else None
        active_wf = get_active_wf() if get_active_wf else None

        # Step 1: Apply injections (from `injections:` section)
        for injection in result.injections:
            if injection.namespace != "global" and injection.namespace != active_wf:
                continue
            if not matches_trigger(injection, tool_name):
                continue
            if should_skip_for_role(injection, agent_role):
                continue
            if should_skip_for_phase(injection, current_phase):
                continue
            tool_input = apply_injection(injection, tool_input)

        # Step 2: Evaluate enforcement rules
        for rule in result.rules:
            # Step 0: Skip rules from inactive workflows
            if rule.namespace != "global" and rule.namespace != active_wf:
                continue
            if not matches_trigger(rule, tool_name):
                continue
            if should_skip_for_role(rule, agent_role):
                continue
            if should_skip_for_phase(rule, current_phase):
                continue
            # Check exclude pattern
            if rule.exclude_pattern:
                field_value = _get_field(tool_input, rule.detect_field)
                if rule.exclude_pattern.search(field_value):
                    continue
            # Check detect pattern
            if rule.detect_pattern:
                field_value = _get_field(tool_input, rule.detect_field)
                if not rule.detect_pattern.search(field_value):
                    continue

            # Rule matches — log hit, then apply enforcement
            hit = HitRecord(
                rule_id=rule.id,
                agent_role=agent_role,
                tool_name=tool_name,
                enforcement=rule.enforcement,
                timestamp=time.time(),
            )

            if rule.enforcement == "log":
                hit_logger.record(dataclasses.replace(hit, outcome="allowed"))
                continue  # Log doesn't block — check next rule

            elif rule.enforcement == "warn":
                if consume_override and consume_override(rule.id, tool_name, tool_input, "warn"):
                    hit_logger.record(dataclasses.replace(hit, outcome="ack"))
                    continue  # Token consumed — allow, check next rule
                else:
                    hit_logger.record(dataclasses.replace(hit, outcome="blocked"))
                    return {
                        "decision": "block",
                        "reason": (
                            f"{rule.message}\n"
                            f'To acknowledge: acknowledge_warning(rule_id="{rule.id}", '
                            f'tool_name="{tool_name}", tool_input={{...}})'
                        ),
                    }

            elif rule.enforcement == "deny":
                if consume_override and consume_override(rule.id, tool_name, tool_input, "deny"):
                    hit_logger.record(dataclasses.replace(hit, outcome="overridden"))
                    continue  # Token consumed — allow, check next rule
                else:
                    hit_logger.record(dataclasses.replace(hit, outcome="blocked"))
                    return {
                        "decision": "block",
                        "reason": (
                            f"{rule.message}\n"
                            f'To request user override: request_override(rule_id="{rule.id}", '
                            f'tool_name="{tool_name}", tool_input={{...}})'
                        ),
                    }

        # If injections modified tool_input, return updated input via SDK protocol
        if tool_input is not original_tool_input:
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "updatedInput": tool_input,
                }
            }
        return {}  # No blocking rule matched — allow

    return {"PreToolUse": [HookMatcher(matcher=None, hooks=[evaluate])]}
