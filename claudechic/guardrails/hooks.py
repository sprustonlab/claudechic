"""SDK hook closure creation — evaluates rules via PreToolUse hooks.

Extracted from app.py. Two-step pipeline: injections first, then enforcement.

Imports: sibling modules (rules, hits) + claude_agent_sdk.types.
NEVER imports from workflows/, app.py, or widgets/.
All engine/token/phase concerns arrive as callbacks.
"""

from __future__ import annotations

import dataclasses
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, cast

from claude_agent_sdk.types import HookCallback, HookMatcher

from claudechic.guardrails.hits import HitLogger, HitRecord
from claudechic.guardrails.rules import (
    _get_field,
    apply_injection,
    matches_trigger,
    should_skip_for_phase,
    should_skip_for_role,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from claudechic.workflows.loader import ManifestLoader

# Type aliases for callback signatures
GetPhaseCallback = Callable[[], str | None]
GetActiveWfCallback = Callable[[], str | None]
GetRoleCallback = Callable[[], str | None]
OverrideTokenConsumer = Callable[
    [str, str, dict, str], bool
]  # (rule_id, tool_name, tool_input, enforcement) -> consumed
GetOverridesCallback = Callable[
    [], "Mapping[str, str]"
]  # () -> {qualified rule_id: "on" | "off"}


def create_guardrail_hooks(
    loader: ManifestLoader,
    hit_logger: HitLogger,
    agent_role: str | None | GetRoleCallback = None,
    get_phase: GetPhaseCallback | None = None,
    get_active_wf: GetActiveWfCallback | None = None,
    consume_override: OverrideTokenConsumer | None = None,
    get_overrides: GetOverridesCallback | None = None,
) -> dict[str, list[HookMatcher]]:
    """Create PreToolUse hooks that evaluate rules (all enforcement levels).

    Args:
        loader: Shared ManifestLoader instance (created once at app init,
                reused across all hook closures — parsers registered once).
        hit_logger: Shared HitLogger for audit trail.
        agent_role: Role type for this agent. Can be a static string or a
                    callable returning the role at evaluation time (for
                    dynamic resolution, e.g. main agent resolving to
                    main_role after workflow activation).
        get_phase: Callback returning current phase (in-memory engine lookup).
                   If None, phase filtering is skipped.
        get_active_wf: Callback returning the active workflow_id (in-memory).
                       If None, all workflow rules evaluate (no namespace filter).
        consume_override: Callback that checks and consumes a one-time override
                         token for a deny rule. Returns True if token was consumed.
                         If None, no overrides are possible.
        get_overrides: Callback returning the per-agent runtime override map
                       (qualified rule_id -> "on" | "off"), read live on every
                       evaluation. "off" skips the rule entirely; "on" bypasses
                       the namespace/role/phase scope checks but STILL applies
                       trigger and exclude/detect pattern matching. Applies to
                       RULES only -- injections are not overridable. If None,
                       no runtime overrides apply (sub-agent hooks built with
                       a static role get no overrides; documented exemption).
    """

    async def evaluate(hook_input: dict, match: str | None, ctx: object) -> dict:
        tool_name = hook_input.get("tool_name", "")
        tool_input = hook_input.get("tool_input", {})
        injection_applied = False

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
        # Resolve agent_role: may be a callable for dynamic resolution
        resolved_role = agent_role() if callable(agent_role) else agent_role
        # Per-agent runtime overrides, read live so sidebar toggles take
        # effect without an SDK reconnect. Note: disabled_ids (config) beats
        # overrides -- disabled rules never reach this hook (filtered out of
        # the LoadResult upstream).
        overrides = dict(get_overrides()) if get_overrides else {}

        # Step 1: Apply injections (from `injections:` section)
        for injection in result.injections:
            if injection.namespace != "global" and injection.namespace != active_wf:
                continue
            if not matches_trigger(injection, tool_name):
                continue
            if should_skip_for_role(injection, resolved_role):
                continue
            if should_skip_for_phase(injection, current_phase):
                continue
            apply_injection(injection, tool_input)
            injection_applied = True

        # Step 2: Evaluate enforcement rules
        for rule in result.rules:
            # Runtime override: "off" skips the rule entirely (no hit logged);
            # "on" bypasses the namespace/role/phase scope checks below but
            # still requires trigger + exclude/detect pattern matches (a
            # forced-on Bash rule must not fire on Read).
            ov = overrides.get(rule.id)
            if ov == "off":
                continue
            if ov != "on":
                # Step 0: Skip rules from inactive workflows
                if rule.namespace != "global" and rule.namespace != active_wf:
                    continue
            if not matches_trigger(rule, tool_name):
                continue
            if ov != "on":
                if should_skip_for_role(rule, resolved_role):
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
                agent_role=resolved_role,
                tool_name=tool_name,
                enforcement=rule.enforcement,
                timestamp=time.time(),
            )

            if rule.enforcement == "log":
                hit_logger.record(dataclasses.replace(hit, outcome="allowed"))
                continue  # Log doesn't block — check next rule

            elif rule.enforcement == "warn":
                if consume_override and consume_override(
                    rule.id, tool_name, tool_input, "warn"
                ):
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
                if consume_override and consume_override(
                    rule.id, tool_name, tool_input, "deny"
                ):
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

        # If injections modified tool_input, return updatedInput via SDK protocol.
        # In-place mutation alone is NOT enough — SDK and CLI are separate
        # processes, so the CLI only sees changes via the hook return value.
        if injection_applied:
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "updatedInput": tool_input,
                }
            }
        return {}  # No blocking rule matched — allow

    hooks = cast("list[HookCallback]", [evaluate])
    return {"PreToolUse": [HookMatcher(matcher=None, hooks=hooks)]}
