"""Shared workflow template-variable substitution helpers.

Single source of the literal-replace logic for braced template tokens
used in workflow YAML, advance-check command strings, and assembled
agent prompts. Three tokens converge here:

- ``${CLAUDECHIC_ARTIFACT_DIR}`` -- the run-bound artifact directory
  (``WorkflowEngine.set_artifact_dir``).
- ``${WORKFLOW_ROOT}`` -- the launched-repo root, also known as the
  main agent's cwd. Python identifier ``project_root`` (avoids a
  one-letter collision with ``workflows_dir``).
- ``${COORDINATOR_NAME}`` -- the registered name of the agent
  currently filling the ``coordinator`` role. Resolved at
  prompt-assembly time from ``RenderContext.peer_agents`` so phase
  markdown can write portable ``message_agent("${COORDINATOR_NAME}",
  ...)`` calls regardless of how the main agent is named.

Consumers:

- ``claudechic.workflows.agent_folders`` -- markdown content
  (identity.md + per-phase docs) substitution at prompt-assembly time.
- ``claudechic.workflows.engine`` -- check-param string substitution
  at advance-check-evaluation time.

Pure literal ``str.replace``; no shell-style expansion (no bare
``$VAR``, no ``~``); no other tokens. Leaf module -- stdlib only.
"""

from __future__ import annotations

from pathlib import Path

ARTIFACT_DIR_TOKEN = "${CLAUDECHIC_ARTIFACT_DIR}"
WORKFLOW_ROOT_TOKEN = "${WORKFLOW_ROOT}"
COORDINATOR_NAME_TOKEN = "${COORDINATOR_NAME}"


def substitute_artifact_dir(content: str, artifact_dir: Path | None) -> str:
    """Replace ``${CLAUDECHIC_ARTIFACT_DIR}`` with the resolved path.

    When ``artifact_dir`` is ``None`` the token is replaced with the
    empty string -- a deliberate, visible failure mode (e.g.,
    ``Write to ${CLAUDECHIC_ARTIFACT_DIR}/spec.md`` becomes
    ``Write to /spec.md``).
    """
    sub = str(artifact_dir) if artifact_dir is not None else ""
    return content.replace(ARTIFACT_DIR_TOKEN, sub)


def substitute_workflow_root(content: str, project_root: Path | None) -> str:
    """Replace ``${WORKFLOW_ROOT}`` with the resolved project root.

    When ``project_root`` is ``None`` the token is replaced with the
    empty string -- a deliberate, visible failure mode that matches
    ``substitute_artifact_dir``'s behaviour.
    """
    sub = str(project_root) if project_root is not None else ""
    return content.replace(WORKFLOW_ROOT_TOKEN, sub)


def substitute_coordinator_name(content: str, coordinator_name: str | None) -> str:
    """Replace ``${COORDINATOR_NAME}`` with the registered coordinator name.

    Resolved from ``RenderContext.peer_agents`` (the ``coordinator`` row).
    When no coordinator is currently spawned (``coordinator_name`` is
    ``None`` or ``""``) the token is replaced with the empty string --
    deliberate, visible failure mode matching the other substitutes
    (e.g., ``message_agent("${COORDINATOR_NAME}", ...)`` becomes
    ``message_agent("", ...)``).
    """
    sub = coordinator_name if coordinator_name else ""
    return content.replace(COORDINATOR_NAME_TOKEN, sub)
