"""Agent folder utilities — prompt assembly and PostCompact hook.

Reads a single resolved workflow directory (the winning-tier path on
``LoadResult.workflows[wf_id].path``) to assemble agent prompts from
identity.md + phase.md files. Multi-tier scanning is the loader's job;
this module is post-resolution.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from claude_agent_sdk.types import HookMatcher

logger = logging.getLogger(__name__)


def _assemble_agent_prompt(
    workflow_dir: Path,
    role_name: str,
    current_phase: str | None,
) -> str:
    """Read identity.md + phase.md, return concatenated content.

    Args:
        workflow_dir: e.g. workflows/project_team/
        role_name: folder name, e.g. "coordinator"
        current_phase: e.g. "specification" -> reads specification.md
    """
    role_dir = workflow_dir / role_name

    identity_path = role_dir / "identity.md"
    identity = (
        identity_path.read_text(encoding="utf-8") if identity_path.is_file() else ""
    )

    phase_content = ""
    if current_phase:
        # Strip namespace prefix — qualified ID "project-team:specification" → bare "specification"
        bare_phase = (
            current_phase.split(":", 1)[1] if ":" in current_phase else current_phase
        )
        phase_path = role_dir / f"{bare_phase}.md"
        if phase_path.is_file():
            phase_content = phase_path.read_text(encoding="utf-8")

    if phase_content:
        return f"{identity}\n\n---\n\n{phase_content}"
    return identity


def assemble_phase_prompt(
    workflow_dir: Path,
    role_name: str,
    current_phase: str | None,
) -> str | None:
    """Get full system prompt content for an agent.

    Called at agent spawn time and by PostCompact hook.
    Returns None if no agent folder exists.

    Args:
        workflow_dir: Resolved workflow directory (the winning-tier path
            from ``LoadResult.workflows[wf_id].path``). Multi-tier
            resolution is the loader's job; this function is post-resolution.
        role_name: Agent role folder name (e.g. "coordinator").
        current_phase: Current phase ID, or None.
    """
    if workflow_dir is None or not workflow_dir.is_dir():
        return None
    result = _assemble_agent_prompt(workflow_dir, role_name, current_phase)
    return result or None


def create_post_compact_hook(
    engine: Any,  # WorkflowEngine — avoid circular import
    agent_role: str,
    workflow_dir: Path,
) -> dict[str, Any]:
    """Create a per-agent PostCompact hook that re-injects phase context.

    The hook closure captures the engine, role, and resolved workflow
    directory at creation time. On /compact, it reads the current phase
    from the engine and re-assembles identity.md + phase.md content from
    the captured directory.

    Args:
        engine: WorkflowEngine instance (provides current phase).
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

        prompt = assemble_phase_prompt(workflow_dir, agent_role, current_phase)
        if prompt:
            logger.debug(
                "PostCompact: re-injected phase context for %s (phase: %s)",
                agent_role,
                current_phase,
            )
            return {"reason": prompt}
        return {}

    return {
        "PostCompact": [HookMatcher(matcher=None, hooks=[reinject_phase_context])],
    }
