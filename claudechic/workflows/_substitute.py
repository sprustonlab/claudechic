"""Shared ``${CLAUDECHIC_ARTIFACT_DIR}`` substitution helper.

Single source of the literal-replace logic used by:

- ``claudechic.workflows.agent_folders`` — markdown content (identity.md
  + per-phase docs) substitution at prompt-assembly time.
- ``claudechic.workflows.engine`` — command-output-check ``command``
  string substitution at advance-check-evaluation time.

Pure literal ``str.replace``; no shell-style expansion (no ``$VAR``,
no ``~``); no other tokens. Leaf module — stdlib only.
"""

from __future__ import annotations

from pathlib import Path

ARTIFACT_DIR_TOKEN = "${CLAUDECHIC_ARTIFACT_DIR}"


def substitute_artifact_dir(content: str, artifact_dir: Path | None) -> str:
    """Replace ``${CLAUDECHIC_ARTIFACT_DIR}`` with the resolved path.

    When ``artifact_dir`` is ``None`` the token is replaced with the
    empty string — a deliberate, visible failure mode (e.g.,
    ``Write to ${CLAUDECHIC_ARTIFACT_DIR}/spec.md`` becomes
    ``Write to /spec.md``).
    """
    sub = str(artifact_dir) if artifact_dir is not None else ""
    return content.replace(ARTIFACT_DIR_TOKEN, sub)
