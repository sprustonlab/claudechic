"""Agent folder utilities -- prompt assembly and post-compact hook.

Reads a single resolved workflow directory (the winning-tier path on
``LoadResult.workflows[wf_id].path``) to assemble agent prompts from
identity.md + phase.md files. Multi-tier scanning is the loader's job;
this module is post-resolution.

Also exposes the ``## Constraints`` block formatter
(``assemble_constraints_block``) and the single composition helper
(``assemble_agent_prompt``) used by every prompt-injection site so the
agent's launch prompt embeds its role+phase scoped rules and
advance-checks.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from claude_agent_sdk.types import HookMatcher

from claudechic.agent import DEFAULT_ROLE
from claudechic.workflows._substitute import (
    substitute_artifact_dir,
    substitute_workflow_root,
)

if TYPE_CHECKING:
    from claudechic.workflows.loader import ManifestLoader

logger = logging.getLogger(__name__)


def _assemble_agent_prompt(
    workflow_dir: Path,
    role_name: str,
    current_phase: str | None,
    artifact_dir: Path | None = None,
    project_root: Path | None = None,
) -> str:
    """Read identity.md + phase.md, return concatenated content.

    Args:
        workflow_dir: e.g. workflows/project_team/
        role_name: folder name, e.g. "coordinator"
        current_phase: e.g. "specification" -> reads specification.md
        artifact_dir: Resolved absolute path bound via
            ``WorkflowEngine.set_artifact_dir`` for this run, or ``None``
            if unset. Substituted into the assembled markdown wherever
            the literal token ``${CLAUDECHIC_ARTIFACT_DIR}`` appears.
        project_root: Launched-repo root (the main agent's cwd) used to
            substitute the literal token ``${WORKFLOW_ROOT}`` in the
            assembled markdown. ``None`` substitutes the empty string
            (deliberate, visible failure mode matching ``artifact_dir``).
    """
    role_dir = workflow_dir / role_name

    identity_path = role_dir / "identity.md"
    identity = (
        identity_path.read_text(encoding="utf-8") if identity_path.is_file() else ""
    )

    phase_content = ""
    if current_phase:
        # Strip namespace prefix - qualified ID "project-team:specification"
        # -> bare "specification"
        bare_phase = (
            current_phase.split(":", 1)[1] if ":" in current_phase else current_phase
        )
        phase_path = role_dir / f"{bare_phase}.md"
        if phase_path.is_file():
            phase_content = phase_path.read_text(encoding="utf-8")

    if phase_content:
        combined = f"{identity}\n\n---\n\n{phase_content}"
    else:
        combined = identity

    combined = substitute_artifact_dir(combined, artifact_dir)
    combined = substitute_workflow_root(combined, project_root)
    return combined


def assemble_phase_prompt(
    workflow_dir: Path,
    role_name: str,
    current_phase: str | None,
    artifact_dir: Path | None = None,
    project_root: Path | None = None,
) -> str | None:
    """Get full system prompt content for an agent.

    Called at agent spawn time and by the post-compact hook.
    Returns None if no agent folder exists.

    Args:
        workflow_dir: Resolved workflow directory (the winning-tier path
            from ``LoadResult.workflows[wf_id].path``). Multi-tier
            resolution is the loader's job; this function is post-resolution.
        role_name: Agent role folder name (e.g. "coordinator").
        current_phase: Current phase ID, or None.
        artifact_dir: Resolved absolute path bound via
            ``WorkflowEngine.set_artifact_dir`` for this run, or ``None``
            if unset. Substituted into the assembled markdown wherever
            the literal token ``${CLAUDECHIC_ARTIFACT_DIR}`` appears.
        project_root: Launched-repo root used to substitute the literal
            token ``${WORKFLOW_ROOT}`` in the assembled markdown.
    """
    if workflow_dir is None or not workflow_dir.is_dir():
        return None
    result = _assemble_agent_prompt(
        workflow_dir, role_name, current_phase, artifact_dir, project_root
    )
    return result or None


# ---------------------------------------------------------------------------
# Constraints block (D3) -- markdown formatter for the per-agent
# rule + advance-check projection.
# ---------------------------------------------------------------------------


def assemble_constraints_block(
    loader: ManifestLoader | None,
    role: str,
    phase: str | None,
    *,
    engine: Any | None = None,
    active_workflow: str | None = None,
    disabled_rules: frozenset[str] | None = None,
    include_skipped: bool = False,
) -> str:
    """Render a ``## Constraints`` markdown block for ``(role, phase)``.

    Composes two projections sourced from sibling leaf modules:

    - ``compute_digest`` (``claudechic.guardrails.digest``) -- role+phase
      scoped rules with annotated ``active`` / ``skip_reason`` fields.
    - ``compute_advance_checks_digest``
      (``claudechic.guardrails.checks_digest``) -- advance-checks for the
      active phase.

    Both modules ship in slot 3 of this implementation cycle. Until they
    land, this helper is callable but returns the empty string for the
    no-rules / no-checks degenerate case so the four D5 inject sites
    naturally skip injection (the dead-code guard in
    ``assemble_agent_prompt`` becomes live).

    Returns the empty string ``""`` when there are no active rules to
    list AND no advance-checks for the phase. Callers test
    ``constraints.strip()`` to decide whether to inject. The
    ``include_skipped=True`` flag (consumed by ``get_agent_info``) keeps
    the block non-empty by rendering the inactive-rule audit table.
    """
    # ----- Collect rules ----------------------------------------------------
    rules_rows: list[str] = []
    n_active = 0
    skip_reason_used = include_skipped
    try:
        from claudechic.guardrails.digest import compute_digest  # type: ignore[import-not-found]
    except ImportError:
        compute_digest = None  # type: ignore[assignment]

    if compute_digest is not None and loader is not None:
        try:
            entries = compute_digest(
                loader,
                active_workflow,
                role if role else DEFAULT_ROLE,
                phase,
                disabled_rules or frozenset(),
            )
        except Exception as e:
            logger.debug("compute_digest raised; skipping rules digest: %s", e)
            entries = []
        for entry in entries:
            active = bool(getattr(entry, "active", True))
            if active:
                n_active += 1
            if not include_skipped and not active:
                continue
            iid = getattr(entry, "id", "") or ""
            ns = getattr(entry, "namespace", "") or ""
            qualified = f"{ns}:{iid}" if ns and ":" not in iid else iid
            enforcement = getattr(entry, "enforcement", "") or ""
            trigger = getattr(entry, "trigger", "") or ""
            message = getattr(entry, "message", "") or ""
            row = f"| {qualified} | {enforcement} | {trigger} | {message} |"
            if skip_reason_used:
                reason = getattr(entry, "skip_reason", "") or ""
                row = f"| {qualified} | {enforcement} | {trigger} | {message} | {reason} |"
            rules_rows.append(row)

    # ----- Collect advance-checks -------------------------------------------
    try:
        from claudechic.guardrails.checks_digest import (  # type: ignore[import-not-found]
            compute_advance_checks_digest,
        )
    except ImportError:
        compute_advance_checks_digest = None  # type: ignore[assignment]

    check_rows: list[str] = []
    if compute_advance_checks_digest is not None and engine is not None:
        try:
            check_entries = compute_advance_checks_digest(engine, phase)
        except Exception as e:
            logger.debug(
                "compute_advance_checks_digest raised; skipping advance-checks: %s", e
            )
            check_entries = []
        for ce in check_entries:
            cid = getattr(ce, "id", "") or ""
            cmd = getattr(ce, "command", None) or getattr(ce, "summary", "") or ""
            manual = bool(getattr(ce, "manual", False))
            check_rows.append(f"- {cid} -- {cmd} (manual? {'yes' if manual else 'no'})")

    # Empty digest short-circuit: no rules to surface AND no advance-checks
    # to list -> no constraints block at all. Callers' empty-string check
    # then skips injection cleanly.
    if not rules_rows and not check_rows:
        return ""

    # ----- Assemble markdown ------------------------------------------------
    sections: list[str] = ["## Constraints", ""]

    sections.append(f"### Rules ({n_active} active)")
    sections.append("")
    if rules_rows:
        if skip_reason_used:
            sections.append("| id | enforcement | trigger | message | skip_reason |")
            sections.append("|----|-------------|---------|---------|-------------|")
        else:
            sections.append("| id | enforcement | trigger | message |")
            sections.append("|----|-------------|---------|---------|")
        sections.extend(rules_rows)
    else:
        sections.append("_No rules apply to this role + phase._")
    sections.append("")

    sections.append(f"### Advance checks ({phase or '-'})")
    sections.append("")
    if check_rows:
        sections.extend(check_rows)
    else:
        sections.append("_No advance checks for this phase._")

    return "\n".join(sections).rstrip() + "\n"


def assemble_agent_prompt(
    role: str,
    phase: str | None,
    loader: ManifestLoader | None,
    *,
    workflow_dir: Path | None = None,
    artifact_dir: Path | None = None,
    project_root: Path | None = None,
    engine: Any | None = None,
    active_workflow: str | None = None,
    disabled_rules: frozenset[str] | None = None,
) -> str | None:
    """Single composition point for every D5 prompt-injection site.

    Wraps ``assemble_phase_prompt`` (identity.md + phase.md) with a
    trailing ``assemble_constraints_block`` so the agent's launch prompt
    always includes its role+phase scoped rules and advance-checks.

    The composition shape is the SPEC-locked
    ``f"{phase_prompt}\\n\\n{constraints_block}"`` when both halves
    exist. Special cases:

    - When ``phase_prompt`` is ``None`` (no role dir, e.g. a default-
      roled agent) but ``assemble_constraints_block`` returns content
      (global-namespace rules apply regardless of role), the helper
      returns the constraints block alone. This guarantees default-
      roled agents still see the rules that actually fire on them.
    - When both halves are empty, the helper returns ``None`` (parity
      with the prior ``assemble_phase_prompt`` semantics for fully
      unconfigured agents).

    Inject sites: main-agent activation, sub-agent spawn (slot 3),
    main-agent phase-advance (slot 4), and post-compact (this module's
    ``create_post_compact_hook``). All four call this helper -- they do
    not concat by hand.
    """
    phase_prompt: str | None = None
    if workflow_dir is not None:
        phase_prompt = assemble_phase_prompt(
            workflow_dir, role, phase, artifact_dir, project_root
        )

    constraints = assemble_constraints_block(
        loader,
        role,
        phase,
        engine=engine,
        active_workflow=active_workflow,
        disabled_rules=disabled_rules,
    )

    has_constraints = bool(constraints.strip())

    if phase_prompt is None:
        # No role dir / unconfigured agent. Default-roled agents that
        # still match global-namespace rules get the constraints block
        # alone; otherwise nothing to inject.
        return constraints if has_constraints else None

    if has_constraints:
        return f"{phase_prompt}\n\n{constraints}"
    return phase_prompt


# ---------------------------------------------------------------------------
# post-compact hook (D5 inject site #3)
# ---------------------------------------------------------------------------


def create_post_compact_hook(
    engine: Any,  # WorkflowEngine -- avoid circular import
    agent_role: str,
    workflow_dir: Path,
) -> dict[str, Any]:
    """Create a per-agent post-compact hook that re-injects phase context.

    The hook closure captures the engine, role, and resolved workflow
    directory at creation time. On /compact, it reads the current phase
    from the engine and re-assembles identity.md + phase.md content from
    the captured directory, then appends the role+phase scoped
    ``## Constraints`` block (D5 inject site #3) so the post-compact
    prompt matches the launch-time prompt shape.

    The constraints-block projection needs a ``ManifestLoader`` and the
    ``active_workflow`` id; both are resolved off the engine at hook-fire
    time (via ``getattr(engine, "loader", None)`` and
    ``getattr(engine, "workflow_id", None)``). slot 4 attaches the
    loader to the engine when constructing it; until then the closure
    falls back to a degenerate constraints block.

    Args:
        engine: WorkflowEngine instance.
        agent_role: Role name for this agent (e.g. "coordinator").
        workflow_dir: Resolved workflow directory for this engine's
            workflow_id. Single path; multi-tier resolution happens
            upstream in the loader.

    Returns:
        Hook configuration dict for SDK hook registration.
    """

    async def reinject_phase_context(
        hook_input: dict, match: str | None, ctx: object
    ) -> dict:
        """Re-inject phase context after /compact."""
        current_phase = engine.get_current_phase()
        artifact_dir = engine.get_artifact_dir()
        project_root = getattr(engine, "project_root", None)
        loader = getattr(engine, "loader", None)
        wf_id = getattr(engine, "workflow_id", None)

        prompt = assemble_agent_prompt(
            agent_role,
            current_phase,
            loader,
            workflow_dir=workflow_dir,
            artifact_dir=artifact_dir,
            project_root=project_root,
            engine=engine,
            active_workflow=wf_id,
        )
        if prompt:
            logger.debug(
                "post-compact: re-injected phase context for %s (phase: %s)",
                agent_role,
                current_phase,
            )
            return {"reason": prompt}
        return {}

    return {
        "PostCompact": [HookMatcher(matcher=None, hooks=[reinject_phase_context])],
    }
