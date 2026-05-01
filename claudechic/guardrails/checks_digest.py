"""Per-phase advance-check digest -- enumerate advance checks for the current phase.

Pure function, no UI dependencies. Sibling of ``digest.py``: where
``compute_digest`` returns the rule+injection projection for a (role,
phase), this returns the advance-check projection for a phase.

Used by the ``## Constraints`` block formatter
(``assemble_constraints_block``) and by ``mcp__chic__get_applicable_rules``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from claudechic.workflows.engine import WorkflowEngine


@dataclass(frozen=True)
class AdvanceCheckEntry:
    """A single advance check declaration projected for display."""

    id: str
    type: str  # "command-output-check", "file-exists-check", ...
    command: str  # human-readable summary; "" if not applicable
    summary: str  # alias / fallback for ``command`` -- consumers may read either
    manual: bool  # True for ``manual-confirm`` checks


def compute_advance_checks_digest(
    engine: WorkflowEngine,
    phase_id: str | None = None,
) -> list[AdvanceCheckEntry]:
    """Return the advance checks declared for ``phase_id``.

    When ``phase_id`` is omitted, defaults to the engine's current phase.
    Returns an empty list if no engine, no current phase, or no checks.

    The returned entries are display-only projections of ``CheckDecl``;
    the engine remains the authority on execution semantics.
    """
    if engine is None:
        return []

    target_phase = phase_id if phase_id is not None else engine.get_current_phase()
    if not target_phase:
        return []

    try:
        decls = engine.get_advance_checks_for(target_phase)
    except Exception:
        return []

    out: list[AdvanceCheckEntry] = []
    for decl in decls:
        summary = _summarize(decl)
        manual = getattr(decl, "type", "") == "manual-confirm"
        out.append(
            AdvanceCheckEntry(
                id=getattr(decl, "id", "") or "",
                type=getattr(decl, "type", "") or "",
                command=summary,
                summary=summary,
                manual=manual,
            )
        )
    return out


def _summarize(decl: Any) -> str:
    """Produce a human-readable one-line summary of a ``CheckDecl``.

    Falls back gracefully across check types: command-output prints the
    command; file-exists/file-content print the path; manual-confirm
    prints the question. Unknown types print ``type(params)``.
    """
    params = getattr(decl, "params", None) or {}
    ctype = getattr(decl, "type", "") or ""

    if ctype == "command-output-check":
        cmd = params.get("command", "")
        return str(cmd)
    if ctype in ("file-exists-check", "file-content-check"):
        path = params.get("path", "")
        return str(path)
    if ctype == "manual-confirm":
        return str(params.get("question") or params.get("prompt", ""))
    if ctype == "artifact-dir-ready-check":
        return "artifact_dir is set"

    # Fallback: type label only (params may contain unprintable callables).
    return ctype
