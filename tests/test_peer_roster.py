"""Tests for ``${PEER_ROSTER}`` and ``${COORDINATOR_NAME}`` substitution.

Focused tests; do not overlap with test_env_segment.py.
"""

from __future__ import annotations

import pytest
from claudechic.workflows.agent_folders import (
    RenderContext,
    _render_environment,
    _render_phase,
)

pytestmark = [pytest.mark.timeout(30)]


# ---------------------------------------------------------------------------
# ${PEER_ROSTER}
# ---------------------------------------------------------------------------


def _coord_ctx(tmp_path, **kwargs) -> RenderContext:
    defaults = dict(
        role="coordinator",
        phase=None,
        workflow_dir=tmp_path,
        active_workflow="project_team",
    )
    defaults.update(kwargs)
    return RenderContext(**defaults)


def test_peer_roster_renders_three_column_role_name_description_table(tmp_path):
    """coordinator + peer_agents non-empty -> 3-col table with header +
    alignment row."""
    peers = {"skeptic": "sk_1", "test_engineer": "te_1"}
    out = _render_environment(_coord_ctx(tmp_path, peer_agents=peers))
    assert "| role | name | description |" in out
    assert "|------|------|-------------|" in out


def test_peer_roster_empty_peer_agents_returns_empty_table_marker(tmp_path):
    """No peers -> ``${PEER_ROSTER}`` substitutes to "" and no table
    header lands in the output."""
    out = _render_environment(_coord_ctx(tmp_path, peer_agents={}))
    assert "| role | name | description |" not in out
    assert "|------|------|-------------|" not in out


def test_peer_roster_unknown_role_renders_with_empty_description_cell(tmp_path):
    """A role not in the overlay's role table renders with an empty
    description cell rather than being dropped."""
    peers = {"made_up_role": "x_1"}
    out = _render_environment(_coord_ctx(tmp_path, peer_agents=peers))
    assert "| made_up_role | x_1 |" in out


def test_peer_roster_skeptic_role_does_not_emit_table(tmp_path):
    """Coordinator-only segment -- non-coordinator roles get no table."""
    peers = {"test_engineer": "te_1"}
    out = _render_environment(
        _coord_ctx(tmp_path, role="skeptic", peer_agents=peers)
    )
    assert "| role | name | description |" not in out


# ---------------------------------------------------------------------------
# ${COORDINATOR_NAME}
# ---------------------------------------------------------------------------


def test_coordinator_name_token_in_phase_md_substitutes_registered_name(tmp_path):
    """A phase markdown file containing ``${COORDINATOR_NAME}`` resolves
    to the registered coordinator name from ``peer_agents``."""
    role_dir = tmp_path / "coordinator"
    role_dir.mkdir()
    (role_dir / "specification.md").write_text(
        "Coordinator is ${COORDINATOR_NAME}.", encoding="utf-8"
    )
    ctx = RenderContext(
        role="coordinator",
        phase="specification",
        workflow_dir=tmp_path,
        peer_agents={"coordinator": "claudechic"},
    )
    out = _render_phase(ctx)
    assert "claudechic" in out
    assert "${COORDINATOR_NAME}" not in out
