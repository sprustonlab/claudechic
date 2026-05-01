"""Per-agent guardrail digest -- enumerate rules/injections with active/skipped status.

Pure function, no UI dependencies. Given the current agent context
(role, phase, active workflow), evaluates each rule/injection and
returns whether it would fire or be skipped (and why).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from claudechic.guardrails.rules import (
    Injection,
    Rule,
    should_skip_for_phase,
    should_skip_for_role,
)

if TYPE_CHECKING:
    from claudechic.workflows.loader import ManifestLoader


@dataclass(frozen=True)
class GuardrailEntry:
    """A single rule or injection with its evaluated status."""

    id: str
    namespace: str  # "global" or workflow_id
    kind: str  # "rule" or "injection"
    trigger: list[str]
    enforcement: str  # "deny" | "warn" | "log" | "inject"
    message: str
    active: bool
    skip_reason: str  # "" if active
    # Scope metadata for display
    roles: list[str]
    exclude_roles: list[str]
    phases: list[str]
    exclude_phases: list[str]


def compute_digest(
    loader: ManifestLoader,
    active_wf: str | None,
    agent_role: str | None,
    current_phase: str | None,
    disabled_rules: set[str] | None = None,
) -> list[GuardrailEntry]:
    """Compute the full guardrail digest for a given agent context.

    Returns one ``GuardrailEntry`` per rule and injection, annotated
    with ``active`` (would evaluate) or ``skip_reason`` (why not).
    """
    result = loader.load()
    entries: list[GuardrailEntry] = []
    _disabled = disabled_rules or set()

    for rule in result.rules:
        active, reason = _evaluate_status(
            rule, active_wf, agent_role, current_phase, _disabled
        )
        entries.append(
            GuardrailEntry(
                id=rule.id,
                namespace=rule.namespace,
                kind="rule",
                trigger=rule.trigger,
                enforcement=rule.enforcement,
                message=rule.message,
                active=active,
                skip_reason=reason,
                roles=rule.roles,
                exclude_roles=rule.exclude_roles,
                phases=rule.phases,
                exclude_phases=rule.exclude_phases,
            )
        )

    for inj in result.injections:
        active, reason = _evaluate_status(
            inj, active_wf, agent_role, current_phase, _disabled
        )
        entries.append(
            GuardrailEntry(
                id=inj.id,
                namespace=inj.namespace,
                kind="injection",
                trigger=inj.trigger,
                enforcement="inject",
                message="",
                active=active,
                skip_reason=reason,
                roles=inj.roles,
                exclude_roles=inj.exclude_roles,
                phases=inj.phases,
                exclude_phases=inj.exclude_phases,
            )
        )

    return entries


def _evaluate_status(
    item: Rule | Injection,
    active_wf: str | None,
    agent_role: str | None,
    current_phase: str | None,
    disabled_rules: set[str],
) -> tuple[bool, str]:
    """Return (active, skip_reason) for a single rule or injection."""
    if item.id in disabled_rules:
        return False, "disabled by user"

    if item.namespace != "global" and item.namespace != active_wf:
        return False, f"workflow '{item.namespace}' not active"

    if should_skip_for_role(item, agent_role):
        if item.roles:
            return False, f"role '{agent_role}' not in {item.roles}"
        return False, f"role '{agent_role}' excluded"

    if should_skip_for_phase(item, current_phase):
        if item.phases:
            return False, f"phase '{current_phase}' not in {item.phases}"
        return False, f"phase '{current_phase}' excluded"

    return True, ""
