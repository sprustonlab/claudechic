"""Tests for the workflow artifact directory mechanism (Group E).

Covers SPEC §5.7 acceptance bullets and §12.3 invariants I-3 through I-12,
plus INV-12 (markdown-grep) and the symlink edge cases per the Leadership
review of ImplementerE's plan.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from claudechic.checks.builtins import ArtifactDirReadyCheck
from claudechic.checks.protocol import CheckDecl
from claudechic.workflows._substitute import (
    ARTIFACT_DIR_TOKEN as _ARTIFACT_DIR_TOKEN,
)
from claudechic.workflows._substitute import (
    substitute_artifact_dir as _substitute_artifact_dir,
)
from claudechic.workflows.engine import (
    WorkflowEngine,
    WorkflowManifest,
    _validate_artifact_path,
)
from claudechic.workflows.phases import Phase

# pytest-asyncio uses auto mode (see pyproject.toml); async tests are
# detected automatically. No file-level mark needed.


def _make_engine(
    *,
    cwd: Path | None = None,
    persist: Any = None,
    phases: list[Phase] | None = None,
) -> WorkflowEngine:
    """Build a WorkflowEngine for artifact_dir testing."""
    if phases is None:
        phases = [
            Phase(id="proj:setup", namespace="proj", file="setup.md"),
            Phase(id="proj:work", namespace="proj", file="work.md"),
        ]
    manifest = WorkflowManifest(workflow_id="proj", phases=phases)
    persist = persist if persist is not None else AsyncMock()
    confirm = AsyncMock(return_value=True)
    return WorkflowEngine(manifest, persist, confirm, cwd=cwd)


# ---------------------------------------------------------------------------
# I-5 — set_artifact_dir creates the directory and resolves
# ---------------------------------------------------------------------------


async def test_set_artifact_dir_absolute_creates_and_returns(tmp_path):
    """I-5: absolute path creates dir and is returned resolved."""
    engine = _make_engine()
    target = tmp_path / "artifacts" / "run-1"
    assert not target.exists()

    result = await engine.set_artifact_dir(str(target))

    assert result == target.resolve()
    assert target.is_dir()
    assert engine.artifact_dir == target.resolve()
    assert engine.get_artifact_dir() == target.resolve()


async def test_set_artifact_dir_relative_resolves_against_cwd(tmp_path):
    """I-5: relative paths resolve against engine cwd kwarg."""
    engine = _make_engine(cwd=tmp_path)
    result = await engine.set_artifact_dir("runs/abc")

    assert result == (tmp_path / "runs" / "abc").resolve()
    assert (tmp_path / "runs" / "abc").is_dir()


async def test_set_artifact_dir_initial_is_none(tmp_path):
    """artifact_dir starts as None; get_artifact_dir mirrors."""
    engine = _make_engine()
    assert engine.artifact_dir is None
    assert engine.get_artifact_dir() is None


# ---------------------------------------------------------------------------
# I-6 — idempotency / different-path RuntimeError
# ---------------------------------------------------------------------------


async def test_set_artifact_dir_idempotent_same_path(tmp_path):
    """I-6: re-call with same resolved path is a no-op return."""
    engine = _make_engine()
    target = tmp_path / "art"
    await engine.set_artifact_dir(str(target))
    # Second call with the same resolved path
    result = await engine.set_artifact_dir(str(target))
    assert result == target.resolve()
    assert engine.artifact_dir == target.resolve()


async def test_set_artifact_dir_idempotent_via_samefile(tmp_path):
    """I-6: same target reached via symlink is treated as same path."""
    engine = _make_engine()
    real = tmp_path / "real_art"
    real.mkdir()
    link = tmp_path / "link_art"
    link.symlink_to(real, target_is_directory=True)

    await engine.set_artifact_dir(str(real))
    # Path.samefile recognises the symlink targets the same inode.
    result = await engine.set_artifact_dir(str(link))
    # First-set path was real; engine keeps that.
    assert result == real.resolve()


async def test_set_artifact_dir_different_path_raises(tmp_path):
    """I-6: different-path re-call raises RuntimeError."""
    engine = _make_engine()
    a = tmp_path / "a"
    b = tmp_path / "b"
    await engine.set_artifact_dir(str(a))
    with pytest.raises(RuntimeError, match="already set"):
        await engine.set_artifact_dir(str(b))


# ---------------------------------------------------------------------------
# I-8 — validation rejects empty / null bytes / newlines / .claude/ ancestor
# ---------------------------------------------------------------------------


async def test_set_artifact_dir_rejects_empty(tmp_path):
    engine = _make_engine(cwd=tmp_path)
    with pytest.raises(ValueError, match="empty"):
        await engine.set_artifact_dir("")


async def test_set_artifact_dir_rejects_null_byte(tmp_path):
    engine = _make_engine(cwd=tmp_path)
    with pytest.raises(ValueError, match="null bytes"):
        await engine.set_artifact_dir("foo\x00bar")


async def test_set_artifact_dir_rejects_newline(tmp_path):
    engine = _make_engine(cwd=tmp_path)
    with pytest.raises(ValueError, match="newlines"):
        await engine.set_artifact_dir("foo\nbar")


async def test_set_artifact_dir_rejects_carriage_return(tmp_path):
    engine = _make_engine(cwd=tmp_path)
    with pytest.raises(ValueError, match="newlines"):
        await engine.set_artifact_dir("foo\rbar")


async def test_set_artifact_dir_rejects_claude_ancestor_relative(tmp_path):
    engine = _make_engine(cwd=tmp_path)
    with pytest.raises(ValueError, match=r"\.claude/"):
        await engine.set_artifact_dir(".claude/runs/x")


async def test_set_artifact_dir_rejects_claude_ancestor_absolute(tmp_path):
    engine = _make_engine()
    forbidden = tmp_path / ".claude" / "runs" / "x"
    with pytest.raises(ValueError, match=r"\.claude/"):
        await engine.set_artifact_dir(str(forbidden))


async def test_set_artifact_dir_rejects_dotdot_traversal_into_claude(tmp_path):
    """Skeptic2 ruling: .resolve() runs BEFORE .claude/ check.

    A path like ``foo/../.claude/x`` resolves to ``.claude/x`` and must
    be rejected — the resolve-first order prevents the traversal bypass.
    """
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    engine = _make_engine(cwd=tmp_path)
    with pytest.raises(ValueError, match=r"\.claude/"):
        await engine.set_artifact_dir("foo/../.claude/runs/x")


# ---------------------------------------------------------------------------
# I-12 — set triggers persist; persist failure rolls back
# ---------------------------------------------------------------------------


async def test_set_artifact_dir_triggers_persist(tmp_path):
    """I-12: persist_fn is awaited before set_artifact_dir returns."""
    persist = AsyncMock()
    engine = _make_engine(persist=persist)
    target = tmp_path / "art"
    await engine.set_artifact_dir(str(target))

    persist.assert_awaited()
    state = persist.await_args.args[0]
    assert state["artifact_dir"] == str(target.resolve())


async def test_set_artifact_dir_rollback_on_persist_failure(tmp_path):
    """Skeptic2 ruling: persist failure rolls back self._artifact_dir."""

    async def failing_persist(state: dict) -> None:
        raise RuntimeError("disk full")

    engine = _make_engine(persist=failing_persist)
    target = tmp_path / "art"

    with pytest.raises(RuntimeError, match="disk full"):
        await engine.set_artifact_dir(str(target))

    # First-call rollback restores None.
    assert engine.artifact_dir is None


async def test_set_artifact_dir_rollback_preserves_prior_value(tmp_path):
    """After a successful set, a failing same-path persist rolls back to prior."""
    persist = AsyncMock()
    engine = _make_engine(persist=persist)
    first = tmp_path / "first"
    await engine.set_artifact_dir(str(first))
    assert engine.artifact_dir == first.resolve()

    # Swap persist to fail; same-path re-call still triggers persist.
    async def fail(_state: dict) -> None:
        raise RuntimeError("io error")

    engine._persist_fn = fail

    with pytest.raises(RuntimeError):
        await engine.set_artifact_dir(str(first))

    # Rollback to the prior value (which was the same path) — engine is
    # still bound to first.
    assert engine.artifact_dir == first.resolve()


# ---------------------------------------------------------------------------
# I-7 — to_session_state / from_session_state round-trip + tampering
# ---------------------------------------------------------------------------


async def test_to_session_state_includes_artifact_dir(tmp_path):
    """I-7: to_session_state has artifact_dir as resolved string."""
    engine = _make_engine()
    target = tmp_path / "art"
    await engine.set_artifact_dir(str(target))

    state = engine.to_session_state()
    assert state["artifact_dir"] == str(target.resolve())


async def test_to_session_state_artifact_dir_null_when_unset(tmp_path):
    """I-7: artifact_dir is None when not set."""
    engine = _make_engine()
    state = engine.to_session_state()
    assert state["artifact_dir"] is None


async def test_from_session_state_restores_artifact_dir(tmp_path):
    """I-7: from_session_state applies saved artifact_dir via validation."""
    target = tmp_path / "art"
    target.mkdir()

    state = {
        "workflow_id": "proj",
        "current_phase": "proj:setup",
        "artifact_dir": str(target),
    }
    manifest = WorkflowManifest(
        workflow_id="proj",
        phases=[
            Phase(id="proj:setup", namespace="proj", file="setup.md"),
            Phase(id="proj:work", namespace="proj", file="work.md"),
        ],
    )
    engine = WorkflowEngine.from_session_state(
        state=state,
        manifest=manifest,
        persist_fn=AsyncMock(),
        confirm_callback=AsyncMock(),
        cwd=tmp_path,
    )

    assert engine.artifact_dir == target.resolve()


async def test_from_session_state_rejects_tampered_claude_path(tmp_path):
    """I-7: tampered .claude/-ancestor saved path raises on construction."""
    forbidden = tmp_path / ".claude" / "evil"
    state = {
        "workflow_id": "proj",
        "current_phase": "proj:setup",
        "artifact_dir": str(forbidden),
    }
    manifest = WorkflowManifest(
        workflow_id="proj",
        phases=[Phase(id="proj:setup", namespace="proj", file="setup.md")],
    )

    with pytest.raises(ValueError, match=r"\.claude/"):
        WorkflowEngine.from_session_state(
            state=state,
            manifest=manifest,
            persist_fn=AsyncMock(),
            confirm_callback=AsyncMock(),
            cwd=tmp_path,
        )


async def test_from_session_state_missing_on_disk_warns_and_keeps(tmp_path, caplog):
    """Option A (user direction): missing-on-disk WARNs but keeps stored."""
    import logging

    target = tmp_path / "vanished"  # never created
    state = {
        "workflow_id": "proj",
        "current_phase": "proj:setup",
        "artifact_dir": str(target),
    }
    manifest = WorkflowManifest(
        workflow_id="proj",
        phases=[Phase(id="proj:setup", namespace="proj", file="setup.md")],
    )

    with caplog.at_level(logging.WARNING, logger="claudechic.workflows.engine"):
        engine = WorkflowEngine.from_session_state(
            state=state,
            manifest=manifest,
            persist_fn=AsyncMock(),
            confirm_callback=AsyncMock(),
            cwd=tmp_path,
        )

    assert engine.artifact_dir == target.resolve()
    assert any("does not exist on disk" in rec.message for rec in caplog.records)


# ---------------------------------------------------------------------------
# I-3 — markdown substitution
# ---------------------------------------------------------------------------


def test_substitute_token_with_path(tmp_path):
    """I-3: token replaced with str(path) when set."""
    target = tmp_path / "art"
    out = _substitute_artifact_dir(f"Write to {_ARTIFACT_DIR_TOKEN}/spec.md", target)
    assert out == f"Write to {target}/spec.md"


def test_substitute_token_with_none():
    """I-3: token replaced with empty string when None."""
    out = _substitute_artifact_dir(f"Write to {_ARTIFACT_DIR_TOKEN}/spec.md", None)
    assert out == "Write to /spec.md"


def test_substitute_no_other_tokens(tmp_path):
    """I-3: only ${CLAUDECHIC_ARTIFACT_DIR} touched; no shell-style expansion."""
    out = _substitute_artifact_dir("$HOME and ~/foo and $VAR remain literal", tmp_path)
    assert out == "$HOME and ~/foo and $VAR remain literal"


def test_substitute_multiple_occurrences(tmp_path):
    """All occurrences are substituted, not just the first."""
    text = f"{_ARTIFACT_DIR_TOKEN}/a and {_ARTIFACT_DIR_TOKEN}/b"
    out = _substitute_artifact_dir(text, tmp_path)
    assert out == f"{tmp_path}/a and {tmp_path}/b"


# ---------------------------------------------------------------------------
# I-4 — resume passes Setup advance check immediately
# ---------------------------------------------------------------------------


async def test_resume_with_artifact_dir_passes_setup_check(tmp_path):
    """I-4 + I-11: a resumed engine with artifact_dir set passes the check."""
    target = tmp_path / "art"
    target.mkdir()
    state = {
        "workflow_id": "proj",
        "current_phase": "proj:setup",
        "artifact_dir": str(target),
    }
    manifest = WorkflowManifest(
        workflow_id="proj",
        phases=[
            Phase(id="proj:setup", namespace="proj", file="setup.md"),
            Phase(id="proj:work", namespace="proj", file="work.md"),
        ],
    )
    engine = WorkflowEngine.from_session_state(
        state=state,
        manifest=manifest,
        persist_fn=AsyncMock(),
        confirm_callback=AsyncMock(),
        cwd=tmp_path,
    )

    decl = CheckDecl(
        id="proj:setup:advance:0",
        namespace="proj",
        type="artifact-dir-ready-check",
        params={},
    )
    result = await engine._run_single_check(decl)
    assert result.passed is True


# ---------------------------------------------------------------------------
# I-10 — get_artifact_dir mirrors last-set
# ---------------------------------------------------------------------------


async def test_get_artifact_dir_initial_none():
    engine = _make_engine()
    assert engine.get_artifact_dir() is None


async def test_get_artifact_dir_returns_resolved_path(tmp_path):
    engine = _make_engine()
    target = tmp_path / "art"
    await engine.set_artifact_dir(str(target))
    assert engine.get_artifact_dir() == target.resolve()


# ---------------------------------------------------------------------------
# I-11 — ArtifactDirReadyCheck class
# ---------------------------------------------------------------------------


async def test_artifact_dir_ready_check_fails_when_unset():
    engine = MagicMock()
    engine.artifact_dir = None
    check = ArtifactDirReadyCheck(engine=engine)
    result = await check.check()
    assert result.passed is False
    assert "set_artifact_dir" in result.evidence


async def test_artifact_dir_ready_check_passes_when_set(tmp_path):
    engine = MagicMock()
    engine.artifact_dir = tmp_path / "art"
    check = ArtifactDirReadyCheck(engine=engine)
    result = await check.check()
    assert result.passed is True
    assert str(tmp_path / "art") in result.evidence


async def test_artifact_dir_ready_check_via_engine_run(tmp_path):
    """End-to-end: engine builds + runs the check via _run_single_check."""
    engine = _make_engine()
    decl = CheckDecl(
        id="proj:setup:advance:0",
        namespace="proj",
        type="artifact-dir-ready-check",
        params={},
    )
    # Pre-set: failing.
    fail_result = await engine._run_single_check(decl)
    assert fail_result.passed is False

    # After set: passing.
    await engine.set_artifact_dir(str(tmp_path / "art"))
    pass_result = await engine._run_single_check(decl)
    assert pass_result.passed is True


# ---------------------------------------------------------------------------
# command-output-check token substitution
# ---------------------------------------------------------------------------


async def test_command_output_check_substitutes_artifact_dir_token(tmp_path):
    """The engine substitutes ${CLAUDECHIC_ARTIFACT_DIR} in command strings."""
    engine = _make_engine()
    target = tmp_path / "art"
    target.mkdir()
    (target / "STATUS.md").write_text("hi")
    await engine.set_artifact_dir(str(target))

    decl = CheckDecl(
        id="proj:setup:advance:1",
        namespace="proj",
        type="command-output-check",
        params={
            "command": (
                'test -f "${CLAUDECHIC_ARTIFACT_DIR}/STATUS.md" && echo PRESENT'
            ),
            "pattern": "PRESENT",
        },
    )
    result = await engine._run_single_check(decl)
    assert result.passed is True


# ---------------------------------------------------------------------------
# Path.samefile + symlink edge cases (Skeptic2 / Leadership review)
# ---------------------------------------------------------------------------


async def test_set_artifact_dir_broken_symlink_target(tmp_path):
    """Symlink whose target does not exist: mkdir(exist_ok=True) creates it."""
    engine = _make_engine()
    real = tmp_path / "absent"
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)

    # Path.resolve(strict=False) returns the link target; mkdir creates it.
    result = await engine.set_artifact_dir(str(link))
    assert result.exists()


async def test_set_artifact_dir_target_is_existing_directory(tmp_path):
    """Existing directory at target is fine (mkdir exist_ok=True)."""
    engine = _make_engine()
    target = tmp_path / "existing"
    target.mkdir()
    (target / "leave-me").write_text("x")

    result = await engine.set_artifact_dir(str(target))
    assert result == target.resolve()
    # Existing files preserved.
    assert (target / "leave-me").read_text() == "x"


async def test_set_artifact_dir_symlink_loop(tmp_path):
    """Symlink loop: Path.resolve does not infinite-loop; OSError surfaces.

    On a symlink loop, ``Path.resolve(strict=False)`` may either return a
    sentinel path or raise ``OSError`` depending on the platform. Either
    way, mkdir on the resulting path errors out and the call fails — we
    assert that no infinite loop / hang occurs.
    """
    engine = _make_engine()
    a = tmp_path / "a"
    b = tmp_path / "b"
    # a -> b, b -> a
    a.symlink_to(b)
    b.symlink_to(a)

    # The exact exception type depends on platform; we only require that
    # the call returns or raises in bounded time.
    try:
        await engine.set_artifact_dir(str(a))
    except (OSError, RuntimeError, ValueError):
        pass


# ---------------------------------------------------------------------------
# _validate_artifact_path direct (catches edge cases without engine state)
# ---------------------------------------------------------------------------


def test_validate_artifact_path_pure_function(tmp_path):
    """_validate_artifact_path returns resolved Path without mkdir."""
    target = tmp_path / "not-yet"
    result = _validate_artifact_path(str(target), tmp_path)
    assert result == target.resolve()
    assert not target.exists()  # validation does not create


def test_validate_artifact_path_rejects_none():
    with pytest.raises(ValueError):
        _validate_artifact_path(None, None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# INV-12 — workflow markdown grep for hardcoded artifact-dir paths
# ---------------------------------------------------------------------------


def test_inv12_no_hardcoded_specific_artifact_paths():
    """INV-12: workflow markdown uses the substitution token, not hardcoded names.

    Convention examples (e.g., ``<working_dir>/.project_team/<project_name>/``)
    are permitted as guidance text in the Setup phase doc only.
    """
    import re

    repo_root = Path(__file__).resolve().parents[1]
    md_root = repo_root / "claudechic" / "defaults" / "workflows"
    bad: list[tuple[str, int, str]] = []
    # Hardcoded specific concrete project name — captured against the two
    # historical prefixes from §5.4. Wildcards / placeholders are allowed.
    pat = re.compile(r"\.(?:claudechic/runs|project_team)/[A-Za-z0-9_-]+/")
    placeholders = (
        "<project_name>",
        "{project_name}",
        "${project_name}",
        "<name>",
        "*/",
    )
    for md in md_root.rglob("*.md"):
        text = md.read_text(encoding="utf-8")
        for i, line in enumerate(text.splitlines(), 1):
            for m in pat.finditer(line):
                snippet = line[max(0, m.start() - 5) : m.end() + 5]
                if any(ph in snippet for ph in placeholders):
                    continue
                bad.append((str(md.relative_to(repo_root)), i, line.strip()))
    assert not bad, f"Hardcoded artifact paths in workflow markdown: {bad}"


# ---------------------------------------------------------------------------
# I-9 — MCP tool surface (no-active-workflow + success)
# ---------------------------------------------------------------------------


async def test_mcp_set_artifact_dir_no_active_workflow_errors(monkeypatch):
    """I-9: set_artifact_dir tool errors when no engine is active."""
    from claudechic import mcp as mcp_mod

    fake_app = MagicMock()
    fake_app._workflow_engine = None
    monkeypatch.setattr(mcp_mod, "_app", fake_app)

    raw_tool = mcp_mod.set_artifact_dir
    handler = getattr(raw_tool, "handler", raw_tool)
    response = await handler({"path": "/tmp/foo"})
    assert response.get("isError") is True
    text = response["content"][0]["text"]
    assert "No active workflow" in text


async def test_mcp_get_artifact_dir_no_active_workflow_errors(monkeypatch):
    """I-9: get_artifact_dir tool errors when no engine is active."""
    from claudechic import mcp as mcp_mod

    fake_app = MagicMock()
    fake_app._workflow_engine = None
    monkeypatch.setattr(mcp_mod, "_app", fake_app)

    raw_tool = mcp_mod.get_artifact_dir
    handler = getattr(raw_tool, "handler", raw_tool)
    response = await handler({})
    assert response.get("isError") is True


async def test_mcp_set_artifact_dir_success_returns_resolved_path(
    monkeypatch, tmp_path
):
    """I-9: set_artifact_dir tool returns the resolved path string."""
    from claudechic import mcp as mcp_mod

    engine = _make_engine(cwd=tmp_path)
    fake_app = MagicMock()
    fake_app._workflow_engine = engine
    fake_app.agent_mgr = None
    monkeypatch.setattr(mcp_mod, "_app", fake_app)

    raw_tool = mcp_mod.set_artifact_dir
    handler = getattr(raw_tool, "handler", raw_tool)
    target = tmp_path / "out"
    response = await handler({"path": str(target)})
    assert response.get("isError") is not True
    assert response["content"][0]["text"] == str(target.resolve())


async def test_mcp_get_artifact_dir_returns_null_when_unset(monkeypatch, tmp_path):
    """I-9: get_artifact_dir returns JSON null when no path is set."""
    from claudechic import mcp as mcp_mod

    engine = _make_engine(cwd=tmp_path)
    fake_app = MagicMock()
    fake_app._workflow_engine = engine
    fake_app.agent_mgr = None
    monkeypatch.setattr(mcp_mod, "_app", fake_app)

    raw_tool = mcp_mod.get_artifact_dir
    handler = getattr(raw_tool, "handler", raw_tool)
    response = await handler({})
    assert response.get("isError") is not True
    # Wire format: structuredContent JSON null + textual fallback.
    assert response.get("structuredContent") is None
    assert response["content"][0]["text"] == "null"


async def test_mcp_get_artifact_dir_returns_path_string(monkeypatch, tmp_path):
    from claudechic import mcp as mcp_mod

    engine = _make_engine(cwd=tmp_path)
    target = tmp_path / "art"
    await engine.set_artifact_dir(str(target))
    fake_app = MagicMock()
    fake_app._workflow_engine = engine
    fake_app.agent_mgr = None
    monkeypatch.setattr(mcp_mod, "_app", fake_app)

    raw_tool = mcp_mod.get_artifact_dir
    handler = getattr(raw_tool, "handler", raw_tool)
    response = await handler({})
    assert response.get("isError") is not True
    assert response["content"][0]["text"] == str(target.resolve())


async def test_mcp_set_artifact_dir_propagates_validation_error(monkeypatch, tmp_path):
    """ValueError from engine surfaces as MCP error response."""
    from claudechic import mcp as mcp_mod

    engine = _make_engine(cwd=tmp_path)
    fake_app = MagicMock()
    fake_app._workflow_engine = engine
    fake_app.agent_mgr = None
    monkeypatch.setattr(mcp_mod, "_app", fake_app)

    raw_tool = mcp_mod.set_artifact_dir
    handler = getattr(raw_tool, "handler", raw_tool)
    response = await handler({"path": "foo\x00bar"})
    assert response.get("isError") is True
    assert "null bytes" in response["content"][0]["text"]


# ---------------------------------------------------------------------------
# get_phase MCP tool — namespace filter (mirrors guardrails/hooks.py:91)
# ---------------------------------------------------------------------------
#
# The MCP `get_phase` diagnostic must only list rules/injections that can
# actually fire under the active workflow. The runtime hook filters by
# ``namespace == "global" or namespace == active_wf``; the display now
# applies the same predicate so non-active workflow items are not shown
# (only counted as "inactive").


def _make_loader_with(rules, injections):
    """Build a stub loader whose ``load()`` returns a LoadResult.

    Lightweight stand-in — the real ``ManifestLoader`` walks tier roots,
    but ``get_phase`` only consumes ``LoadResult.rules`` /
    ``LoadResult.injections`` / ``LoadResult.errors``.
    """
    from claudechic.workflows.loader import LoadResult

    class _StubLoader:
        def __init__(self, result: LoadResult) -> None:
            self._result = result

        def load(self, **_kwargs):
            return self._result

    return _StubLoader(LoadResult(rules=rules, injections=injections))


def _injection(*, id_: str, namespace: str, trigger: str = "PreToolUse/Bash"):
    """Build an Injection with the minimum required fields for display tests."""
    from claudechic.guardrails.rules import Injection

    return Injection(id=id_, namespace=namespace, trigger=[trigger])


def _rule(
    *,
    id_: str,
    namespace: str,
    trigger: str = "PreToolUse/Bash",
    enforcement: str = "warn",
):
    """Build a Rule with the minimum required fields for display tests."""
    from claudechic.guardrails.rules import Rule

    return Rule(id=id_, namespace=namespace, trigger=[trigger], enforcement=enforcement)


async def test_get_applicable_rules_filters_inactive_workflow_injections(
    monkeypatch, tmp_path
):
    """get_applicable_rules must NOT list an injection from an inactive workflow.

    Migrated from the former ``test_get_phase_filters_inactive_workflow_injections``
    after slot 3 narrowed ``get_phase`` (rule/injection projection moved to
    ``get_applicable_rules``). The filter semantics being verified -- namespace
    must equal "global" or the active workflow -- now live in
    ``compute_digest`` and surface through the markdown ``## Constraints``
    block this tool emits.
    """
    from claudechic import mcp as mcp_mod

    engine = _make_engine(cwd=tmp_path)  # workflow_id="proj"
    loader = _make_loader_with(
        rules=[],
        injections=[
            _injection(id_="proj:active_inj", namespace="proj"),
            _injection(id_="other:foreign_inj", namespace="other"),
            _injection(id_="global:shared_inj", namespace="global"),
        ],
    )

    fake_agent = MagicMock()
    fake_agent.agent_type = "default"
    fake_agent_mgr = MagicMock()
    fake_agent_mgr.find_by_name = MagicMock(return_value=fake_agent)

    fake_app = MagicMock()
    fake_app._workflow_engine = engine
    fake_app._manifest_loader = loader
    fake_app.agent_mgr = fake_agent_mgr
    fake_app._get_disabled_rules = None
    monkeypatch.setattr(mcp_mod, "_app", fake_app)

    raw_tool = mcp_mod._make_get_applicable_rules(caller_name="test_caller")
    handler = getattr(raw_tool, "handler", raw_tool)
    response = await handler({"agent_name": "test_caller"})
    text = response["content"][0]["text"]

    # Active items appear in the constraints projection.
    assert "proj:active_inj" in text
    assert "global:shared_inj" in text
    # Inactive workflow's injection is NOT listed (filtered by namespace).
    assert "other:foreign_inj" not in text


async def test_get_applicable_rules_filters_inactive_workflow_rules(
    monkeypatch, tmp_path
):
    """get_applicable_rules rule projection must mirror the runtime namespace filter.

    Migrated from the former ``test_get_phase_filters_inactive_workflow_rules``.
    The "N active" rendering in the ``### Rules (N active)`` header replaces the
    old ``Rules: N active (M inactive)`` summary line that ``get_phase`` used to
    emit.
    """
    from claudechic import mcp as mcp_mod

    engine = _make_engine(cwd=tmp_path)  # workflow_id="proj"
    loader = _make_loader_with(
        rules=[
            _rule(id_="proj:active_rule", namespace="proj"),
            _rule(id_="global:shared_rule", namespace="global"),
            _rule(id_="other:foreign_rule_a", namespace="other"),
            _rule(id_="other:foreign_rule_b", namespace="other"),
        ],
        injections=[],
    )

    fake_agent = MagicMock()
    fake_agent.agent_type = "default"
    fake_agent_mgr = MagicMock()
    fake_agent_mgr.find_by_name = MagicMock(return_value=fake_agent)

    fake_app = MagicMock()
    fake_app._workflow_engine = engine
    fake_app._manifest_loader = loader
    fake_app.agent_mgr = fake_agent_mgr
    fake_app._get_disabled_rules = None
    monkeypatch.setattr(mcp_mod, "_app", fake_app)

    raw_tool = mcp_mod._make_get_applicable_rules(caller_name="test_caller")
    handler = getattr(raw_tool, "handler", raw_tool)
    response = await handler({"agent_name": "test_caller"})
    text = response["content"][0]["text"]

    # Active count reflects the namespace filter (global + active workflow).
    assert "Rules (2 active)" in text
    # Active rules listed; foreign workflow rules are not.
    assert "proj:active_rule" in text
    assert "global:shared_rule" in text
    assert "other:foreign_rule_a" not in text
    assert "other:foreign_rule_b" not in text


async def test_get_phase_omits_rule_count_line(monkeypatch, tmp_path):
    """get_phase narrowing: rule/injection summary lines no longer appear.

    Migrated from the former ``test_get_phase_no_inactive_suffix_when_all_active``.
    Slot 3 removed the ``Rules: N active (...)`` and ``Injections: N active
    (...)`` lines from ``get_phase`` -- the per-agent role+phase projection
    now lives in ``get_applicable_rules``. This test guards that narrowing.
    The workflow-state assertions that survive are kept so we don't lose
    coverage of the narrow tool's actual surface.
    """
    from claudechic import mcp as mcp_mod

    engine = _make_engine(cwd=tmp_path)  # workflow_id="proj"
    loader = _make_loader_with(
        rules=[_rule(id_="proj:r1", namespace="proj")],
        injections=[_injection(id_="global:i1", namespace="global")],
    )

    fake_app = MagicMock()
    fake_app._workflow_engine = engine
    fake_app._manifest_loader = loader
    fake_app.agent_mgr = None
    monkeypatch.setattr(mcp_mod, "_app", fake_app)

    raw_tool = mcp_mod.get_phase
    handler = getattr(raw_tool, "handler", raw_tool)
    response = await handler({})
    text = response["content"][0]["text"]

    # Workflow-state surface still present (narrow contract).
    assert "Workflow: proj" in text
    # Rule/injection summary lines are gone (moved to get_applicable_rules).
    assert "Rules:" not in text
    assert "Injections:" not in text


async def test_get_phase_no_engine_reports_none_active(
    monkeypatch,
):
    """get_phase narrow shape with no engine: status only, no rule projection.

    Migrated from the former
    ``test_get_phase_no_engine_treats_all_workflow_items_as_inactive``. The
    "no active workflow" status line survives; the rule/injection counts and
    listing do not (those moved to ``get_applicable_rules``). The narrow tool
    must never list rule/injection ids in any code path.
    """
    from claudechic import mcp as mcp_mod

    loader = _make_loader_with(
        rules=[
            _rule(id_="global:r1", namespace="global"),
            _rule(id_="proj:r2", namespace="proj"),
        ],
        injections=[
            _injection(id_="proj:i1", namespace="proj"),
        ],
    )

    fake_app = MagicMock()
    fake_app._workflow_engine = None
    fake_app._manifest_loader = loader
    fake_app.agent_mgr = None
    monkeypatch.setattr(mcp_mod, "_app", fake_app)

    raw_tool = mcp_mod.get_phase
    handler = getattr(raw_tool, "handler", raw_tool)
    response = await handler({})
    text = response["content"][0]["text"]

    # No-engine path still reports the workflow status line.
    assert "Workflow: none active" in text
    # Rule/injection summary lines are gone (moved to get_applicable_rules).
    assert "Rules:" not in text
    assert "Injections:" not in text
    # Narrow shape never lists individual rule/injection ids.
    assert "proj:i1" not in text
    assert "proj:r2" not in text
    assert "global:r1" not in text


# ---------------------------------------------------------------------------
# Smoke: project_team.yaml Setup phase parses and uses the new check
# ---------------------------------------------------------------------------


def test_project_team_setup_phase_uses_artifact_dir_ready_check():
    """Sanity check: bundled YAML declares an artifact-dir-ready-check at Setup."""
    repo_root = Path(__file__).resolve().parents[1]
    yaml_path = (
        repo_root
        / "claudechic"
        / "defaults"
        / "workflows"
        / "project_team"
        / "project_team.yaml"
    )
    text = yaml_path.read_text(encoding="utf-8")
    assert "artifact-dir-ready-check" in text
    assert "${CLAUDECHIC_ARTIFACT_DIR}" in text
    # The hardcoded prefix from before the rewrite must be gone.
    assert ".project_team/*/STATUS.md" not in text


# Suppress unused import warnings for symlink fixture helpers.
_ = os
