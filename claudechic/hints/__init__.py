"""Hints system -- contextual advisory delivery for claudechic.

Public API exports for use by other claudechic packages.
"""

from claudechic.hints.engine import run_pipeline
from claudechic.hints.parsers import HintsParser
from claudechic.hints.types import (
    AlwaysTrue,
    CooldownPeriod,
    HintDecl,
    HintLifecycle,
    HintRecord,
    HintSpec,
    ShowEverySession,
    ShowOnce,
    ShowUntilResolved,
    TriggerCondition,
)

__all__ = [
    "AlwaysTrue",
    "CooldownPeriod",
    "HintDecl",
    "HintLifecycle",
    "HintRecord",
    "HintSpec",
    "HintsParser",
    "ShowEverySession",
    "ShowOnce",
    "ShowUntilResolved",
    "TriggerCondition",
    "run_pipeline",
]
