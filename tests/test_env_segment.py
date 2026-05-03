"""Tests for the environment segment renderer (SPEC §3.11).

Reads the real bundle files at
``claudechic/defaults/environment/{base.md,project_team.md}``. We do not
stub those; they are the canonical content under test.
"""

from __future__ import annotations

import pytest
from claudechic.workflows.agent_folders import (
    EnvironmentSegmentSettings,
    GateSettings,
    RenderContext,
    _render_environment,
)

pytestmark = [pytest.mark.timeout(30)]


def _ctx(tmp_path, **kwargs) -> RenderContext:
    """Build a RenderContext suitable for environment rendering tests.

    Defaults: role=coordinator, active_workflow=project_team, workflow_dir
    is a real directory under tmp_path so the renderer's guard passes.
    """
    defaults = dict(
        role="coordinator",
        phase=None,
        workflow_dir=tmp_path,
        active_workflow="project_team",
    )
    defaults.update(kwargs)
    return RenderContext(**defaults)


# ---------------------------------------------------------------------------
# Token substitution
# ---------------------------------------------------------------------------


def test_render_environment_substitutes_agent_role_token(tmp_path):
    out = _render_environment(_ctx(tmp_path, role="implementer"))
    assert "${AGENT_ROLE}" not in out
    assert "implementer" in out


def test_render_environment_substitutes_active_workflow_token(tmp_path):
    out = _render_environment(_ctx(tmp_path, active_workflow="project_team"))
    assert "${ACTIVE_WORKFLOW}" not in out
    assert "project_team" in out


def test_render_environment_substitutes_workflow_root_token(tmp_path):
    proj = tmp_path / "myproj"
    proj.mkdir()
    out = _render_environment(_ctx(tmp_path, project_root=proj))
    assert "${WORKFLOW_ROOT}" not in out
    assert str(proj) in out


def test_render_environment_substitutes_artifact_dir_token(tmp_path):
    artifact = tmp_path / "artifacts"
    artifact.mkdir()
    out = _render_environment(_ctx(tmp_path, artifact_dir=artifact))
    assert "${CLAUDECHIC_ARTIFACT_DIR}" not in out
    assert str(artifact) in out


# ---------------------------------------------------------------------------
# Guards: empty when no workflow / no dir
# ---------------------------------------------------------------------------


def test_render_environment_active_workflow_unset_returns_empty_string(tmp_path):
    ctx = RenderContext(
        role="coordinator",
        phase=None,
        workflow_dir=tmp_path,
        active_workflow=None,
    )
    assert _render_environment(ctx) == ""


def test_render_environment_workflow_dir_none_returns_empty_string(tmp_path):
    ctx = RenderContext(
        role="coordinator",
        phase=None,
        workflow_dir=None,
        active_workflow="project_team",
    )
    assert _render_environment(ctx) == ""


# ---------------------------------------------------------------------------
# Bundle content lands in the rendered output
# ---------------------------------------------------------------------------


def test_render_environment_returns_base_md_content(tmp_path):
    """Bundle file ``base.md`` content (the ``## Tools`` section and the
    ``message_agent`` description) appears in the rendered output when
    ``active_workflow`` + ``workflow_dir`` are set. Asserts on stable
    content-bearing markers, not on a specific heading title.
    """
    out = _render_environment(_ctx(tmp_path))
    assert "## Tools" in out
    assert "message_agent" in out


# ---------------------------------------------------------------------------
# Peer roster: coordinator-only
# ---------------------------------------------------------------------------


def test_render_environment_peer_roster_coordinator_only(tmp_path):
    """When role=coordinator and peer_agents is non-empty, the roster
    table heading appears. When role=skeptic, the roster heading is
    absent (coordinator-only segment).
    """
    peers = {"skeptic": "sk_1", "test_engineer": "te_1"}
    coord_out = _render_environment(
        _ctx(tmp_path, role="coordinator", peer_agents=peers)
    )
    assert "| role | name | description |" in coord_out

    skep_out = _render_environment(
        _ctx(tmp_path, role="skeptic", peer_agents=peers)
    )
    assert "| role | name | description |" not in skep_out


def test_render_environment_peer_roster_renders_provided_peers_only(tmp_path):
    peers = {"skeptic": "sk_1"}
    out = _render_environment(
        _ctx(tmp_path, role="coordinator", peer_agents=peers)
    )
    # Provided peer name is present.
    assert "sk_1" in out
    # Roles NOT in peer_agents do not appear as roster rows. The overlay
    # bundles ``composability`` as a known role, but the roster filter
    # excludes any role not in peer_agents.
    # Build the canonical row text we expect to NOT appear.
    composability_row = "| composability |"
    assert composability_row not in out


# ---------------------------------------------------------------------------
# Sanity: settings-default GateSettings does not break renderer
# ---------------------------------------------------------------------------


def test_render_environment_runs_with_default_settings(tmp_path):
    settings = GateSettings(
        environment_segment=EnvironmentSegmentSettings(enabled=True)
    )
    out = _render_environment(_ctx(tmp_path, settings=settings))
    assert out
