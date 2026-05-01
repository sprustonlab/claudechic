"""Workflow template-variable tests (Component A sub-units A1 + A4).

Covers ``${WORKFLOW_ROOT}`` substitution at the two consumer seams
(advance-check command params via ``WorkflowEngine`` and assembled
agent prompts via ``_assemble_agent_prompt``) plus the per-feature
gestalt assertions for A1.

A4 (two-pass executor) is covered primarily in
``tests/test_advance_check_executor.py``; a single gestalt-style
test here pins the cross-cutting expectation that substitution and
the two-pass ordering interact correctly (substituted command runs
in the auto pass before any manual confirm).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest
from claudechic.checks.protocol import CheckDecl
from claudechic.workflows._substitute import (
    WORKFLOW_ROOT_TOKEN,
    substitute_workflow_root,
)
from claudechic.workflows.agent_folders import (
    _assemble_agent_prompt,
    assemble_phase_prompt,
)
from claudechic.workflows.engine import WorkflowEngine, WorkflowManifest
from claudechic.workflows.phases import Phase

pytestmark = [pytest.mark.fast]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_engine(
    *,
    cwd: Path | None = None,
    phases: list[Phase] | None = None,
    confirm_callback: Any = None,
) -> WorkflowEngine:
    """Build a ``WorkflowEngine`` with sensible defaults for these tests."""
    if phases is None:
        phases = [
            Phase(id="proj:setup", namespace="proj", file="setup.md"),
            Phase(id="proj:work", namespace="proj", file="work.md"),
        ]
    manifest = WorkflowManifest(workflow_id="proj", phases=phases)
    persist = AsyncMock()
    confirm = (
        confirm_callback
        if confirm_callback is not None
        else AsyncMock(return_value=True)
    )
    return WorkflowEngine(manifest, persist, confirm, cwd=cwd)


def _write_role_files(
    workflow_dir: Path,
    role_name: str,
    *,
    identity: str = "",
    phase_files: dict[str, str] | None = None,
) -> Path:
    """Create a role folder under ``workflow_dir`` with identity + phase docs."""
    role_dir = workflow_dir / role_name
    role_dir.mkdir(parents=True, exist_ok=True)
    if identity:
        (role_dir / "identity.md").write_text(identity, encoding="utf-8")
    for phase_id, body in (phase_files or {}).items():
        (role_dir / f"{phase_id}.md").write_text(body, encoding="utf-8")
    return role_dir


# ---------------------------------------------------------------------------
# A1 sub-unit -- pure substitute_workflow_root behaviour
# ---------------------------------------------------------------------------


def test_a1_substitute_workflow_root_replaces_braced_token(tmp_path: Path) -> None:
    """Braced ``${WORKFLOW_ROOT}`` token is literal-replaced with the path."""
    text = f"cd {WORKFLOW_ROOT_TOKEN} && ls"
    out = substitute_workflow_root(text, tmp_path)
    assert out == f"cd {tmp_path} && ls"


def test_a1_substitute_workflow_root_none_replaces_with_empty() -> None:
    """A ``None`` project root substitutes to the empty string (visible failure)."""
    text = f"cd {WORKFLOW_ROOT_TOKEN} && ls"
    out = substitute_workflow_root(text, None)
    assert out == "cd  && ls"


def test_a1_substitute_workflow_root_no_shell_expansion(tmp_path: Path) -> None:
    """Only the braced token is touched; bare ``$VAR`` and ``~`` remain literal."""
    text = "$HOME and ~/foo and $WORKFLOW_ROOT remain literal"
    out = substitute_workflow_root(text, tmp_path)
    assert out == "$HOME and ~/foo and $WORKFLOW_ROOT remain literal"


def test_a1_substitute_workflow_root_multiple_occurrences(tmp_path: Path) -> None:
    """All occurrences of the braced token are substituted."""
    text = f"{WORKFLOW_ROOT_TOKEN}/a and {WORKFLOW_ROOT_TOKEN}/b"
    out = substitute_workflow_root(text, tmp_path)
    assert out == f"{tmp_path}/a and {tmp_path}/b"


# ---------------------------------------------------------------------------
# A1 user-side gestalt -- engine resolves ${WORKFLOW_ROOT} in command params
# ---------------------------------------------------------------------------


async def test_a1_workflow_yaml_workflow_root_resolved_in_check_command(
    tmp_path: Path,
) -> None:
    """User-side gestalt: ``${WORKFLOW_ROOT}`` in a ``command-output-check``
    command is resolved at run time to the engine's project root.

    Drives the full engine-side substitution path: the manifest declares
    a relative-style command using the braced token, the engine wires it
    through ``_run_single_check`` which calls ``substitute_workflow_root``
    before the underlying ``CommandOutputCheck`` runs. The shell command
    only succeeds if the substitution produced a real path on disk.
    """
    (tmp_path / "MARKER.txt").write_text("HERE", encoding="utf-8")
    engine = _make_engine(cwd=tmp_path)

    decl = CheckDecl(
        id="proj:setup:advance:0",
        namespace="proj",
        type="command-output-check",
        params={
            "command": (f'test -f "{WORKFLOW_ROOT_TOKEN}/MARKER.txt" && echo PRESENT'),
            "pattern": "PRESENT",
        },
    )
    result = await engine._run_single_check(decl)
    assert result.passed is True, result.evidence


async def test_a1_command_check_workflow_root_substituted_in_pattern_param(
    tmp_path: Path,
) -> None:
    """String-typed ``pattern`` param also receives ``${WORKFLOW_ROOT}`` substitution.

    The engine substitutes every string-typed param uniformly; the
    pattern param is regex-scanned against stdout, so a substituted
    project-root path must appear verbatim in the matched output.
    """
    engine = _make_engine(cwd=tmp_path)
    decl = CheckDecl(
        id="proj:setup:advance:1",
        namespace="proj",
        type="command-output-check",
        params={
            "command": f"echo {tmp_path}",
            "pattern": str(tmp_path),
        },
    )
    result = await engine._run_single_check(decl)
    assert result.passed is True, result.evidence


async def test_a1_workflow_root_substitution_when_cwd_unset_yields_empty(
    tmp_path: Path,
) -> None:
    """An engine without a configured cwd substitutes the token to empty.

    Mirrors the artifact-dir behaviour: visible failure mode rather than
    silent no-op (e.g. ``cd ${WORKFLOW_ROOT}`` becomes ``cd ``).
    """
    engine = _make_engine(cwd=None)
    decl = CheckDecl(
        id="proj:setup:advance:2",
        namespace="proj",
        type="command-output-check",
        params={
            "command": f'echo "ROOT=[{WORKFLOW_ROOT_TOKEN}]"',
            "pattern": r"ROOT=\[\]",
        },
    )
    result = await engine._run_single_check(decl)
    assert result.passed is True, result.evidence


# ---------------------------------------------------------------------------
# A1 agent-side gestalt -- assembled prompt substitutes ${WORKFLOW_ROOT}
# ---------------------------------------------------------------------------


def test_a1_assembled_agent_prompt_substitutes_workflow_root(tmp_path: Path) -> None:
    """Agent-side gestalt: ``${WORKFLOW_ROOT}`` in identity.md and the phase
    markdown is substituted to the resolved project root at prompt-assembly
    time.

    This is the seam consumed by the post-compact hook and the prompt
    composition helper -- the agent should never see the literal token.
    """
    workflow_dir = tmp_path / "workflows" / "proj"
    project_root = tmp_path / "repo"
    project_root.mkdir()

    _write_role_files(
        workflow_dir,
        "coordinator",
        identity=f"You are rooted at {WORKFLOW_ROOT_TOKEN}.",
        phase_files={
            "setup": f"Read files under {WORKFLOW_ROOT_TOKEN}/specs/.",
        },
    )

    assembled = _assemble_agent_prompt(
        workflow_dir,
        "coordinator",
        "setup",
        artifact_dir=None,
        project_root=project_root,
    )

    assert WORKFLOW_ROOT_TOKEN not in assembled
    assert f"You are rooted at {project_root}." in assembled
    assert f"Read files under {project_root}/specs/." in assembled


def test_a1_assemble_phase_prompt_substitutes_workflow_root_in_namespaced_phase(
    tmp_path: Path,
) -> None:
    """Public ``assemble_phase_prompt`` accepts a namespaced phase id and
    still substitutes ``${WORKFLOW_ROOT}`` in the resolved phase doc.
    """
    workflow_dir = tmp_path / "workflows" / "proj"
    project_root = tmp_path / "repo"
    project_root.mkdir()

    _write_role_files(
        workflow_dir,
        "coordinator",
        identity="Identity.",
        phase_files={"setup": f"At {WORKFLOW_ROOT_TOKEN}."},
    )

    assembled = assemble_phase_prompt(
        workflow_dir,
        "coordinator",
        "proj:setup",
        artifact_dir=None,
        project_root=project_root,
    )

    assert assembled is not None
    assert WORKFLOW_ROOT_TOKEN not in assembled
    assert f"At {project_root}." in assembled


def test_a1_assemble_phase_prompt_workflow_root_none_substitutes_empty(
    tmp_path: Path,
) -> None:
    """A ``None`` project_root substitutes to the empty string in markdown
    (deliberate visible failure mode mirroring artifact_dir).
    """
    workflow_dir = tmp_path / "workflows" / "proj"
    _write_role_files(
        workflow_dir,
        "coordinator",
        identity=f"Rooted at [{WORKFLOW_ROOT_TOKEN}].",
        phase_files={"setup": "Phase body."},
    )

    assembled = assemble_phase_prompt(
        workflow_dir,
        "coordinator",
        "setup",
        artifact_dir=None,
        project_root=None,
    )

    assert assembled is not None
    assert WORKFLOW_ROOT_TOKEN not in assembled
    assert "Rooted at []." in assembled


# ---------------------------------------------------------------------------
# A4 cross-cutting -- substitution happens within the two-pass ordering
# ---------------------------------------------------------------------------


async def test_a4_workflow_root_substitution_runs_in_auto_pass_before_manual(
    tmp_path: Path,
) -> None:
    """Cross-cutting A4 + A1: a substituted ``command-output-check``
    declared after a ``manual-confirm`` still runs in the auto pass and
    fails before the manual confirm prompt is shown.

    This pins the ordering invariant of A4 (auto checks before manual
    checks) while exercising A1's substitution: a failing-but-substituted
    command must short-circuit the manual prompt.
    """
    confirm_calls: list[str] = []

    async def confirm(question: str, context: dict[str, Any] | None = None) -> bool:
        confirm_calls.append(question)
        return True

    engine = _make_engine(cwd=tmp_path, confirm_callback=confirm)

    # The command uses ${WORKFLOW_ROOT} but the file does NOT exist; it
    # MUST fail after substitution, before any manual prompt fires.
    failing_auto = CheckDecl(
        id="proj:setup:advance:auto",
        namespace="proj",
        type="command-output-check",
        params={
            "command": (
                f'test -f "{WORKFLOW_ROOT_TOKEN}/never-exists.txt" && echo PRESENT'
            ),
            "pattern": "PRESENT",
        },
    )
    manual = CheckDecl(
        id="proj:setup:advance:manual",
        namespace="proj",
        type="manual-confirm",
        params={"question": "Approve?"},
    )

    # Note declaration order: manual first, auto second. The two-pass
    # executor must still run the auto check first.
    result = await engine.attempt_phase_advance(
        "proj",
        "proj:setup",
        "proj:work",
        [manual, failing_auto],
    )

    assert result.success is False
    assert result.failed_check_id == "proj:setup:advance:auto"
    assert confirm_calls == [], (
        "manual-confirm callback must not fire when an auto check is failing"
    )
