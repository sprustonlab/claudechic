"""Phase dataclass — bridge type importing from checks/ and hints/.

A Phase represents a named period in a workflow's lifecycle with optional
advance checks and hints. This is a bridge type: it imports CheckDecl from
checks/protocol and HintDecl from hints/types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    pass

# Tier identity for parsed-record provenance. Kept in sync with
# claudechic/workflows/loader.py (loader.py imports this module so we cannot
# import the alias from there without a circular dependency).
Tier = Literal["package", "user", "project"]


@dataclass(frozen=True)
class Phase:
    """A named period in a workflow's lifecycle."""

    id: str
    namespace: str
    file: str
    advance_checks: list[Any] = field(
        default_factory=list
    )  # list[CheckDecl] at runtime
    hints: list[Any] = field(default_factory=list)  # list[HintDecl] at runtime
    # Tier provenance — opaque metadata for engine; UI-only consumption.
    tier: Tier = "package"
