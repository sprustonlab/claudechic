"""Workflow orchestration layer.

Public API for manifest loading, phase management, and workflow engine.
This is the orchestration layer — it imports from guardrails/, checks/, hints/.
"""

from __future__ import annotations

from claudechic.workflows.agent_folders import (
    assemble_phase_prompt,
    create_session_start_compact_hook,
)
from claudechic.workflows.engine import (
    PhaseAdvanceResult,
    WorkflowEngine,
    WorkflowManifest,
)
from claudechic.workflows.loader import (
    LoadError,
    LoadResult,
    ManifestLoader,
    Tier,
    TierRoots,
    WorkflowData,
    discover_manifests_single_tier,
    parse_disable_entries,
    walk_tiers,
)
from claudechic.workflows.phases import Phase

__all__ = [
    "LoadError",
    "LoadResult",
    "ManifestLoader",
    "Phase",
    "PhaseAdvanceResult",
    "Tier",
    "TierRoots",
    "WorkflowData",
    "WorkflowEngine",
    "WorkflowManifest",
    "assemble_phase_prompt",
    "create_session_start_compact_hook",
    "discover_manifests_single_tier",
    "parse_disable_entries",
    "register_default_parsers",
    "walk_tiers",
]


def register_default_parsers(loader: ManifestLoader) -> None:
    """Register all built-in ManifestSection parsers with the loader.

    Call this once at app init before loader.load(). Registers parsers
    for: rules, injections, checks, hints, phases.
    """
    from claudechic.checks.parsers import ChecksParser
    from claudechic.guardrails.parsers import InjectionsParser, RulesParser
    from claudechic.hints.parsers import HintsParser
    from claudechic.workflows.parsers import PhasesParser

    loader.register(RulesParser())
    loader.register(InjectionsParser())
    loader.register(ChecksParser())
    loader.register(HintsParser())
    loader.register(PhasesParser())
