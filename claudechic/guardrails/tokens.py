"""One-time override tokens for warn/deny enforcement.

Leaf module — stdlib only, no claudechic imports.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass


@dataclass(frozen=True)
class OverrideToken:
    """One-time authorization for a specific blocked action."""

    rule_id: str
    tool_name: str
    command_hash: str  # Hash of the command string (detect_field value)
    enforcement: str = ""  # "warn" or "deny" — prevents cross-level bypass


def _hash_command(rule_id: str, tool_name: str, command: str) -> str:
    """Deterministic hash of rule_id + tool_name + command string."""
    canonical = f"{rule_id}:{tool_name}:{command}"
    return hashlib.sha256(canonical.encode()).hexdigest()


def _extract_command(tool_input: dict) -> str:
    """Extract the command string from tool_input.

    Uses 'command' field for Bash, falls back to sorted JSON of full dict.
    """
    if "command" in tool_input:
        return tool_input["command"]
    try:
        return json.dumps(tool_input, sort_keys=True)
    except (TypeError, ValueError):
        return str(sorted(tool_input.items()))


class OverrideTokenStore:
    """One-time override tokens for warn/deny enforcement.

    Lifecycle: created at app init, lives for app lifetime.
    Independent of workflow engine existence.

    Token matching uses hash(rule_id + tool_name + command) so extra
    fields in tool_input (description, timeout, etc.) don't break matching.
    """

    def __init__(self) -> None:
        self._tokens: list[OverrideToken] = []

    def store(
        self,
        rule_id: str,
        tool_name: str,
        tool_input: dict,
        enforcement: str = "",
    ) -> None:
        """Store a one-time override token after acknowledgment or user approval.

        Args:
            enforcement: "warn" or "deny" — tags the token so a warn-level
                token cannot be consumed by a deny-level rule (prevents
                agents from bypassing user authority via acknowledge_warning).
        """
        self._tokens.append(
            OverrideToken(
                rule_id=rule_id,
                tool_name=tool_name,
                command_hash=_hash_command(
                    rule_id, tool_name, _extract_command(tool_input)
                ),
                enforcement=enforcement,
            )
        )

    def consume(
        self,
        rule_id: str,
        tool_name: str,
        tool_input: dict,
        enforcement: str = "",
    ) -> bool:
        """Consume a one-time override token if one matches.

        Returns True if consumed. Token enforcement must match the
        requesting enforcement level — a warn token cannot satisfy
        a deny rule.
        """
        cmd_hash = _hash_command(rule_id, tool_name, _extract_command(tool_input))
        for i, token in enumerate(self._tokens):
            if (
                token.rule_id == rule_id
                and token.tool_name == tool_name
                and token.command_hash == cmd_hash
                and token.enforcement == enforcement
            ):
                self._tokens.pop(i)
                return True
        return False
