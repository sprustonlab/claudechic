"""Rule and Injection dataclasses, matching functions, and YAML loader.

Leaf module within guardrails/ — no imports from workflows/, checks/, or hints/.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class Rule:
    """A single guardrail rule parsed from a manifest."""

    id: str  # Qualified: "project-team:pip_block"
    namespace: str  # Required, no default: "global" or workflow_id
    trigger: list[str]  # e.g. ["PreToolUse/Bash"]
    enforcement: str  # "deny" | "warn" | "log"
    detect_pattern: re.Pattern[str] | None = None
    detect_field: str = "command"  # which tool_input field to match against
    exclude_pattern: re.Pattern[str] | None = None
    message: str = ""
    roles: list[str] = field(default_factory=list)
    exclude_roles: list[str] = field(default_factory=list)
    phases: list[str] = field(default_factory=list)
    exclude_phases: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Injection:
    """A tool-input modification declared in the injections: manifest section.

    Separate from Rule — not an enforcement level. Processed BEFORE
    enforcement rules in the hook pipeline.
    """

    id: str  # Qualified: "project-team:force_tee"
    namespace: str
    trigger: list[str]  # Same trigger format as rules
    detect_pattern: re.Pattern[str] | None = None
    detect_field: str = "command"
    inject_value: str = ""  # What to inject
    roles: list[str] = field(default_factory=list)
    exclude_roles: list[str] = field(default_factory=list)
    phases: list[str] = field(default_factory=list)
    exclude_phases: list[str] = field(default_factory=list)


# DEPRECATED: This function is unused. Rules are now loaded via ManifestLoader
# and RulesParser. This legacy loader does not support trigger-aware detect_field
# defaults (DETECT_FIELD_DEFAULTS). Do not use for new code.
def load_rules(rules_path: Path) -> list[Rule]:
    """Parse rules.yaml into Rule objects. Returns empty list if file missing.

    Legacy loader — will be replaced by ManifestLoader in workflows/loader.py.
    """
    if not rules_path.is_file():
        return []

    with rules_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data or "rules" not in data:
        return []

    rules: list[Rule] = []
    for entry in data["rules"]:
        # Parse trigger — can be string or list
        raw_trigger = entry.get("trigger", "")
        triggers = [raw_trigger] if isinstance(raw_trigger, str) else list(raw_trigger)

        # Parse detect pattern
        detect = entry.get("detect", {})
        detect_pattern = None
        detect_field = "command"
        if detect:
            pattern_str = detect.get("pattern", "")
            if pattern_str:
                detect_pattern = re.compile(pattern_str)
            detect_field = detect.get("field", "command")

        # Parse exclude pattern
        exclude_pattern = None
        exclude_str = entry.get("exclude_if_matches", "")
        if exclude_str:
            exclude_pattern = re.compile(exclude_str)

        # Parse role restrictions (new field names)
        roles = _as_list(entry.get("roles", []))
        exclude_roles = _as_list(entry.get("exclude_roles", []))

        # Parse phase restrictions (new field names)
        phases = _as_list(entry.get("phases", []))
        exclude_phases = _as_list(entry.get("exclude_phases", []))

        rules.append(
            Rule(
                id=entry.get("id", ""),
                namespace=entry.get("namespace", "global"),
                trigger=triggers,
                enforcement=entry.get("enforcement", "deny"),
                detect_pattern=detect_pattern,
                detect_field=detect_field,
                exclude_pattern=exclude_pattern,
                message=entry.get("message", ""),
                roles=roles,
                exclude_roles=exclude_roles,
                phases=phases,
                exclude_phases=exclude_phases,
            )
        )

    return rules


def _as_list(value: Any) -> list[str]:
    """Normalize a value to a list of strings."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return list(value)
    return []


def matches_trigger(rule: Rule | Injection, tool_name: str) -> bool:
    """Check if rule's trigger matches the tool event.

    Trigger format: "PreToolUse/Bash" — we extract the tool name part after '/'.
    """
    for trigger in rule.trigger:
        parts = trigger.split("/", 1)
        if len(parts) == 2:
            trigger_tool = parts[1]
            if trigger_tool == tool_name:
                return True
        elif len(parts) == 1:
            # Bare trigger like "PreToolUse" matches all tools
            if parts[0] == "PreToolUse":
                return True
    return False


def match_rule(rule: Rule, tool_name: str, tool_input: dict[str, Any]) -> bool:
    """Check exclude pattern first, then detect pattern.

    Returns True if the rule matches (i.e., should fire).
    """
    if rule.detect_pattern is None:
        # No detect pattern = always matches (after trigger check)
        return True

    # Get the field to match against
    text = _get_field(tool_input, rule.detect_field)

    # Check exclude first — if exclude matches, rule does NOT fire
    if rule.exclude_pattern and rule.exclude_pattern.search(text):
        return False

    # Check detect pattern
    return bool(rule.detect_pattern.search(text))


def _get_field(tool_input: dict, field: str) -> str:
    """Extract a field from tool_input for pattern matching.

    Simple dict lookup, returns empty string for missing keys.
    """
    return str(tool_input.get(field, ""))


def should_skip_for_role(rule: Rule | Injection, agent_role: str | None) -> bool:
    """Return True if the rule should be skipped for this agent role.

    - roles: rule only fires for these roles (skip if role not in list)
    - exclude_roles: rule never fires for these roles (skip if role in list)
    """
    if rule.roles and (agent_role is None or agent_role not in rule.roles):
        # Rule only applies to specific roles
        return True
    return bool(rule.exclude_roles and agent_role and agent_role in rule.exclude_roles)


def should_skip_for_phase(rule: Rule | Injection, current_phase: str | None) -> bool:
    """Return True if rule should be skipped based on current phase.

    Takes the current qualified phase ID string directly (from engine).
    """
    if not rule.phases and not rule.exclude_phases:
        return False  # No phase restrictions

    if current_phase is None:
        return bool(
            rule.phases
        )  # Skip if rule requires specific phases; don't skip if only exclude_phases

    if rule.phases and current_phase not in rule.phases:
        return True  # Skip: not in allowed phase

    return bool(rule.exclude_phases and current_phase in rule.exclude_phases)


def apply_injection(injection: Injection, tool_input: dict) -> dict:
    """Apply an injection rule to tool_input, mutating it in-place.

    The injection's detect pattern identifies what to modify, and
    inject_value specifies what to inject.  The dict is mutated
    in-place so the SDK executes the modified command — returning
    via hookSpecificOutput.updatedInput alone is NOT sufficient
    because the CLI does not apply updatedInput.

    Args:
        injection: An Injection with detect pattern and inject_value.
        tool_input: The current tool input dict (mutated in-place).

    Returns:
        The same tool_input dict (for chaining / back-compat).
    """
    field = injection.detect_field
    current_value = _get_field(tool_input, field)
    if not current_value:
        return tool_input

    # Check detect pattern if present
    if injection.detect_pattern and not injection.detect_pattern.search(current_value):
        return tool_input

    # Apply injection — mutate in-place so the SDK uses the modified value
    if injection.inject_value:
        tool_input[field] = f"{current_value}{injection.inject_value}"
    return tool_input


def read_phase_state(phase_state_path: Path) -> dict[str, Any] | None:
    """Read phase state from JSON file. Returns None if missing.

    Legacy — will be replaced by in-memory engine state via Chicsession.
    """
    if not phase_state_path.is_file():
        return None
    try:
        with phase_state_path.open(encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
