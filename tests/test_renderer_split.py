"""Tests for the segment-renderer split (SPEC §3.2 / §3.2.1).

Each ``_render_*`` helper is a pure function of a ``RenderContext``; it
reads only the fields it needs and never mutates the context.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from claudechic.workflows.agent_folders import (
    RenderContext,
    _render_constraints_phase,
    _render_constraints_stable,
    _render_environment,
    _render_identity,
    _render_phase,
)
from claudechic.workflows.loader import LoadResult

pytestmark = [pytest.mark.timeout(30)]


# ---------------------------------------------------------------------------
# Helpers (reused from test_constraints_block.py -- test fixtures, not SUT)
# ---------------------------------------------------------------------------


class _StubLoader:
    """Minimal loader returning a fixed ``LoadResult``."""

    def __init__(self, result: LoadResult) -> None:
        self._result = result

    def load(self, **_kwargs):
        return self._result


def _make_ctx(**kwargs) -> RenderContext:
    """Build a RenderContext with sensible defaults for renderer tests."""
    defaults = dict(role="coordinator", phase=None)
    defaults.update(kwargs)
    return RenderContext(**defaults)


# ---------------------------------------------------------------------------
# _render_identity
# ---------------------------------------------------------------------------


def test_render_identity_returns_empty_string_when_workflow_dir_none():
    ctx = _make_ctx(workflow_dir=None)
    assert _render_identity(ctx) == ""


def test_render_identity_reads_role_identity_md(tmp_path):
    role_dir = tmp_path / "coordinator"
    role_dir.mkdir()
    (role_dir / "identity.md").write_text("IDENTITY-A", encoding="utf-8")
    ctx = _make_ctx(role="coordinator", workflow_dir=tmp_path)
    out = _render_identity(ctx)
    assert "IDENTITY-A" in out


# ---------------------------------------------------------------------------
# _render_phase
# ---------------------------------------------------------------------------


def test_render_phase_returns_empty_string_when_phase_md_missing(tmp_path):
    role_dir = tmp_path / "coordinator"
    role_dir.mkdir()
    # No specification.md exists.
    ctx = _make_ctx(
        role="coordinator", phase="specification", workflow_dir=tmp_path
    )
    assert _render_phase(ctx) == ""


def test_render_phase_strips_namespace_from_qualified_phase(tmp_path):
    role_dir = tmp_path / "coordinator"
    role_dir.mkdir()
    (role_dir / "specification.md").write_text(
        "PHASE-CONTENT-X", encoding="utf-8"
    )
    # Qualified phase ID -- bare name "specification" should be looked up.
    ctx = _make_ctx(
        role="coordinator",
        phase="project-team:specification",
        workflow_dir=tmp_path,
    )
    out = _render_phase(ctx)
    assert "PHASE-CONTENT-X" in out


# ---------------------------------------------------------------------------
# _render_constraints_phase / stable
# ---------------------------------------------------------------------------


def _stub_entry(
    *, id_: str, namespace: str = "global", phases=None, active: bool = True
) -> SimpleNamespace:
    return SimpleNamespace(
        id=id_,
        namespace=namespace,
        kind="rule",
        active=active,
        phases=list(phases or []),
        enforcement="warn",
        trigger="PreToolUse/Bash",
        message="msg",
    )


def test_render_constraints_phase_purity_same_inputs_same_output(monkeypatch):
    """Same RenderContext -> same bytes from _render_constraints_phase."""

    def fake_digest(*_args, **_kwargs):
        return [_stub_entry(id_="global:foo", phases=["design"])]

    monkeypatch.setattr(
        "claudechic.guardrails.digest.compute_digest", fake_digest
    )

    loader = _StubLoader(LoadResult())
    ctx = _make_ctx(
        role="coordinator",
        phase="design",
        loader=loader,
        active_workflow="proj",
    )
    a = _render_constraints_phase(ctx, omit_heading=False)
    b = _render_constraints_phase(ctx, omit_heading=False)
    assert a == b
    assert a != ""


def test_render_constraints_phase_advance_checks_coordinator_only(monkeypatch):
    """Advance-checks subsection appears for ``coordinator`` only."""

    def fake_digest(*_args, **_kwargs):
        return []

    fake_check = SimpleNamespace(
        id="proj:design:advance:0",
        type="manual-confirm",
        command="confirm design done",
        summary="confirm design done",
        manual=True,
    )

    def fake_checks_digest(*_args, **_kwargs):
        return [fake_check]

    monkeypatch.setattr(
        "claudechic.guardrails.digest.compute_digest", fake_digest
    )
    monkeypatch.setattr(
        "claudechic.guardrails.checks_digest.compute_advance_checks_digest",
        fake_checks_digest,
    )

    loader = _StubLoader(LoadResult())
    fake_engine = SimpleNamespace()

    coord_ctx = _make_ctx(
        role="coordinator",
        phase="design",
        loader=loader,
        engine=fake_engine,
        active_workflow="proj",
    )
    coord_out = _render_constraints_phase(coord_ctx, omit_heading=False)
    assert "Advance checks" in coord_out
    assert "proj:design:advance:0" in coord_out

    skeptic_ctx = _make_ctx(
        role="skeptic",
        phase="design",
        loader=loader,
        engine=fake_engine,
        active_workflow="proj",
    )
    skeptic_out = _render_constraints_phase(skeptic_ctx, omit_heading=False)
    assert "Advance checks" not in skeptic_out
    assert "proj:design:advance:0" not in skeptic_out


def test_render_constraints_stable_omits_phase_only_rules(monkeypatch):
    """Stable slice drops phase-qualified rules."""
    entries = [
        _stub_entry(id_="global:agnostic", phases=[]),
        _stub_entry(id_="global:phase-only", phases=["design"]),
    ]

    def fake_digest(*_args, **_kwargs):
        return entries

    monkeypatch.setattr(
        "claudechic.guardrails.digest.compute_digest", fake_digest
    )

    loader = _StubLoader(LoadResult())
    ctx = _make_ctx(
        role="coordinator",
        phase="design",
        loader=loader,
        active_workflow="proj",
    )
    out = _render_constraints_stable(ctx)
    assert "global:agnostic" in out
    assert "global:phase-only" not in out


# ---------------------------------------------------------------------------
# _render_environment
# ---------------------------------------------------------------------------


def test_render_environment_returns_empty_string_when_active_workflow_unset(
    tmp_path,
):
    ctx = _make_ctx(
        role="coordinator",
        workflow_dir=tmp_path,
        active_workflow=None,
    )
    assert _render_environment(ctx) == ""


def test_render_environment_returns_empty_string_when_workflow_dir_missing(
    tmp_path,
):
    bogus = tmp_path / "no_such_dir"
    ctx = _make_ctx(
        role="coordinator",
        workflow_dir=bogus,
        active_workflow="project_team",
    )
    assert _render_environment(ctx) == ""
