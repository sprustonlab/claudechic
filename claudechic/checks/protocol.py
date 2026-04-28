"""Check protocol, CheckResult, and CheckDecl — leaf module (stdlib only)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Literal, Protocol, runtime_checkable

# Tier identity for parsed-record provenance. Kept in sync with
# claudechic/workflows/loader.py (this leaf module cannot import from there).
Tier = Literal["package", "user", "project"]


@dataclass(frozen=True)
class CheckResult:
    """Outcome of a check. Crosses the Check-Engine seam."""

    passed: bool
    evidence: str


AsyncConfirmCallback = Callable[[str, dict[str, Any] | None], Awaitable[bool]]
"""The seam between ManualConfirm and the TUI.

ManualConfirm calls: await callback(question, context) -> bool
  - question: the prompt string from YAML
  - context: optional dict with phase metadata (may be None)
    Keys when present: "phase_id", "phase_index", "phase_total", "check_id"

The engine creates the callback, closing over app methods.
ManualConfirm never imports anything from claudechic.widgets or app.
"""


@runtime_checkable
class Check(Protocol):
    """Async protocol for all verification checks.

    Compositional law: every check type implements this.
    The engine calls check() without knowing the implementation.
    """

    async def check(self) -> CheckResult: ...


@dataclass(frozen=True)
class CheckDecl:
    """Check declaration — type + params, not the executable check itself."""

    id: str
    namespace: str
    type: str  # "command-output-check", "file-exists-check", etc.
    params: dict[str, Any]
    on_failure: dict | None = None
    when: dict | None = None
    # Tier provenance — opaque metadata for engine; UI-only consumption.
    tier: Tier = "package"


@dataclass(frozen=True)
class OnFailureConfig:
    """Parsed on_failure configuration from manifest YAML."""

    message: str
    severity: str = "warning"
    lifecycle: str = "show-until-resolved"
