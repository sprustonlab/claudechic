"""Agent folder utilities — prompt assembly and PostCompact hook.

Reads project-side workflows/ directory (not claudechic/) to assemble
agent prompts from identity.md + phase.md files. Pure file I/O — no
UI dependencies.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml
from claude_agent_sdk.types import HookMatcher

logger = logging.getLogger(__name__)


def _find_workflow_dir(workflows_dir: Path, workflow_id: str) -> Path | None:
    """Find the workflow directory for a given workflow_id.

    Scans subdirectories of workflows_dir and matches on the
    workflow_id field in their YAML manifest. Handles kebab-case
    workflow_id with snake_case directory names.

    Returns the directory Path, or None if not found.
    """
    if not workflows_dir.is_dir():
        return None

    for child in sorted(workflows_dir.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        manifest = child / f"{child.name}.yaml"
        if not manifest.is_file():
            continue
        try:
            with manifest.open(encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if isinstance(data, dict) and data.get("workflow_id") == workflow_id:
                return child
        except (OSError, yaml.YAMLError):
            continue
    return None


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
    workflows_dir: Path,
    workflow_id: str,
    role_name: str,
    current_phase: str | None,
) -> str | None:
    """Get full system prompt content for an agent.

    Called at agent spawn time and by PostCompact hook.
    Returns None if no agent folder exists.

    Args:
        workflows_dir: Project-side workflows/ directory path.
        workflow_id: Kebab-case workflow ID (e.g. "project-team").
        role_name: Agent role folder name (e.g. "coordinator").
        current_phase: Current phase ID, or None.
    """
    workflow_dir = _find_workflow_dir(workflows_dir, workflow_id)
    if workflow_dir is None:
        return None

    result = _assemble_agent_prompt(workflow_dir, role_name, current_phase)
    return result or None


def create_post_compact_hook(
    engine: Any,  # WorkflowEngine — avoid circular import
    agent_role: str,
    workflows_dir: Path,
) -> dict[str, Any]:
    """Create a per-agent PostCompact hook that re-injects phase context.

    The hook closure captures the engine and role at creation time.
    On /compact, it reads the current phase from the engine and
    re-assembles identity.md + phase.md content.

    Args:
        engine: WorkflowEngine instance (provides workflow_id and current phase).
        agent_role: Role name for this agent (e.g. "coordinator").
        workflows_dir: Project-side workflows/ directory path.

    Returns:
        Hook configuration dict for SDK hook registration.
    """

    async def reinject_phase_context(
        hook_input: dict, match: str | None, ctx: object
    ) -> dict:
        """Re-inject phase context after /compact."""
        current_phase = engine.get_current_phase()
        workflow_id = engine.workflow_id

        prompt = assemble_phase_prompt(
            workflows_dir, workflow_id, agent_role, current_phase
        )
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
