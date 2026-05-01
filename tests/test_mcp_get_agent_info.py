"""Tests for the D4 agent-self-awareness MCP surface.

Covers:
- Seam #5 (D-mcp <-> D-render byte-identical): the ``## Constraints`` body
  produced by ``mcp__chic__get_applicable_rules`` is the same content as
  ``assemble_constraints_block`` directly.
- ``get_agent_info`` aggregator structure: locked section headings and
  delegation to ``assemble_constraints_block``.
- D6 alignment: ``_get_disabled_rules`` is consulted by both tools so the
  registry view matches the hook view.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from claudechic.agent import DEFAULT_ROLE
from claudechic.guardrails.rules import Injection, Rule
from claudechic.workflows.agent_folders import assemble_constraints_block
from claudechic.workflows.loader import LoadResult


# ---------------------------------------------------------------------------
# Helpers (mirror tests/test_artifact_dir.py for consistency)
# ---------------------------------------------------------------------------


class _StubLoader:
    def __init__(self, result: LoadResult) -> None:
        self._result = result

    def load(self, **_kwargs):
        return self._result


def _rule(
    *,
    id_: str,
    namespace: str = "global",
    trigger: str = "PreToolUse/Bash",
    enforcement: str = "warn",
    message: str = "",
) -> Rule:
    return Rule(
        id=id_,
        namespace=namespace,
        trigger=[trigger],
        enforcement=enforcement,
        message=message,
    )


def _injection(
    *, id_: str, namespace: str = "global", trigger: str = "PreToolUse/Bash"
) -> Injection:
    return Injection(id=id_, namespace=namespace, trigger=[trigger])


def _make_fake_engine(workflow_id: str = "proj", phase: str | None = None):
    """Build a MagicMock engine compatible with the MCP tool internals."""
    engine = MagicMock()
    engine.workflow_id = workflow_id
    engine.get_current_phase.return_value = phase
    engine.get_next_phase.return_value = None
    engine.get_artifact_dir.return_value = None
    engine.project_root = None
    engine._phase_order = []
    return engine


def _make_fake_app(
    *,
    loader,
    engine,
    agent,
    disabled_rules=None,
):
    """Build a MagicMock ``ChatApp``-shaped object for the MCP tool."""
    fake_agent_mgr = MagicMock()
    fake_agent_mgr.find_by_name = MagicMock(return_value=agent)

    fake_app = MagicMock()
    fake_app._workflow_engine = engine
    fake_app._manifest_loader = loader
    fake_app.agent_mgr = fake_agent_mgr
    if disabled_rules is None:
        fake_app._get_disabled_rules = None
    else:
        fake_app._get_disabled_rules = MagicMock(return_value=disabled_rules)
    return fake_app


def _make_fake_agent(
    *,
    name: str = "test_caller",
    agent_type: str = DEFAULT_ROLE,
    cwd=None,
    session_id: str | None = None,
):
    agent = MagicMock()
    agent.name = name
    agent.agent_type = agent_type
    agent.cwd = cwd
    agent.session_id = session_id
    agent.model = None
    agent.effort = None
    agent.worktree = None
    agent.status = "idle"
    return agent


# ---------------------------------------------------------------------------
# Seam #5: byte-identical output between MCP tool and direct helper
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_d4_get_applicable_rules_matches_assemble_constraints_block(
    monkeypatch,
):
    """For the same ``(role, phase)``, ``get_applicable_rules`` returns
    markdown whose body equals a direct call to
    ``assemble_constraints_block`` (the single source of truth).

    Pins Seam #5: the MCP surface owns NO rule-resolution logic of its
    own -- it delegates to the same helper the prompt-injection sites
    use. Drift here means the agent sees a different rule projection
    when calling the MCP tool vs. reading its own launch prompt.
    """
    from claudechic import mcp as mcp_mod

    engine = _make_fake_engine(workflow_id="proj", phase=None)
    loader = _StubLoader(
        LoadResult(
            rules=[
                _rule(id_="global:shared", message="m1"),
                _rule(id_="proj:active", namespace="proj"),
            ],
            injections=[_injection(id_="global:shared_inj")],
        )
    )
    agent = _make_fake_agent(agent_type=DEFAULT_ROLE)
    fake_app = _make_fake_app(loader=loader, engine=engine, agent=agent)
    monkeypatch.setattr(mcp_mod, "_app", fake_app)

    raw_tool = mcp_mod._make_get_applicable_rules(caller_name="test_caller")
    handler = getattr(raw_tool, "handler", raw_tool)
    response = await handler({"agent_name": "test_caller"})

    mcp_text = response["content"][0]["text"]

    # Direct call with the SAME inputs the MCP tool used internally.
    direct_block = assemble_constraints_block(
        loader,
        DEFAULT_ROLE,
        None,
        engine=engine,
        active_workflow="proj",
        include_skipped=False,
        disabled_rules=None,
    )

    # Byte-identical (the MCP tool returns the helper's output verbatim).
    assert mcp_text == direct_block
    # Locked contract strings are present.
    assert "## Constraints" in mcp_text
    assert "### Rules (" in mcp_text


@pytest.mark.asyncio
async def test_d4_get_applicable_rules_include_skipped_passthrough(monkeypatch):
    """``include_skipped=True`` flows through to the helper (skip_reason
    column appears in the rendered table)."""
    from claudechic import mcp as mcp_mod

    engine = _make_fake_engine(workflow_id="proj", phase=None)
    # One rule from a foreign workflow -- it will render as inactive
    # (namespace filter) when include_skipped=True.
    loader = _StubLoader(
        LoadResult(
            rules=[
                _rule(id_="other:foreign", namespace="other"),
            ]
        )
    )
    agent = _make_fake_agent(agent_type=DEFAULT_ROLE)
    fake_app = _make_fake_app(loader=loader, engine=engine, agent=agent)
    monkeypatch.setattr(mcp_mod, "_app", fake_app)

    raw_tool = mcp_mod._make_get_applicable_rules(caller_name="test_caller")
    handler = getattr(raw_tool, "handler", raw_tool)
    response = await handler({"agent_name": "test_caller", "include_skipped": True})
    text = response["content"][0]["text"]
    # skip_reason column appears (locked include_skipped contract).
    assert "skip_reason" in text


# ---------------------------------------------------------------------------
# get_agent_info: aggregator section structure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_d4_get_agent_info_contains_locked_section_headings(monkeypatch):
    """``get_agent_info`` returns a unified markdown report with the
    locked section headings:
      - ``## Identity``
      - ``## Session``
      - ``## Active workflow + phase``
      - ``## Constraints`` (delegated to ``assemble_constraints_block``)
      - ``## Loader errors``
    """
    from claudechic import mcp as mcp_mod

    engine = _make_fake_engine(workflow_id="proj", phase=None)
    loader = _StubLoader(LoadResult(rules=[_rule(id_="global:warn_sudo")]))
    agent = _make_fake_agent(agent_type="coordinator", session_id=None)
    fake_app = _make_fake_app(loader=loader, engine=engine, agent=agent)
    monkeypatch.setattr(mcp_mod, "_app", fake_app)

    raw_tool = mcp_mod._make_get_agent_info(caller_name="test_caller")
    handler = getattr(raw_tool, "handler", raw_tool)
    response = await handler({"agent_name": "test_caller"})
    text = response["content"][0]["text"]

    # Top-level agent header.
    assert "# Agent: test_caller" in text
    # Locked section headings (verbatim per TEST_SPECIFICATION).
    assert "## Identity" in text
    assert "## Session" in text
    assert "## Active workflow + phase" in text
    assert "## Constraints" in text
    assert "## Loader errors" in text


@pytest.mark.asyncio
async def test_d4_get_agent_info_identity_uses_live_agent_type(monkeypatch):
    """The ``## Identity`` section reads ``agent.agent_type`` (the live
    role read pinned by B4), not the workflow's main_role.
    """
    from claudechic import mcp as mcp_mod

    engine = _make_fake_engine()
    loader = _StubLoader(LoadResult())
    agent = _make_fake_agent(name="skeptic_a", agent_type="skeptic")
    fake_app = _make_fake_app(loader=loader, engine=engine, agent=agent)
    monkeypatch.setattr(mcp_mod, "_app", fake_app)

    raw_tool = mcp_mod._make_get_agent_info(caller_name="skeptic_a")
    handler = getattr(raw_tool, "handler", raw_tool)
    response = await handler({})  # default to caller
    text = response["content"][0]["text"]
    # The role line in ## Identity reflects agent_type.
    assert "role (agent_type): skeptic" in text
    # Caller defaults wired through.
    assert "# Agent: skeptic_a" in text


@pytest.mark.asyncio
async def test_d4_get_agent_info_default_role_when_agent_unregistered(
    monkeypatch,
):
    """When the calling agent is not yet registered, the aggregator
    surfaces an ``(agent not registered)`` line instead of crashing.
    """
    from claudechic import mcp as mcp_mod

    engine = _make_fake_engine()
    loader = _StubLoader(LoadResult())

    # find_by_name returns None to simulate "not yet registered."
    fake_agent_mgr = MagicMock()
    fake_agent_mgr.find_by_name = MagicMock(return_value=None)
    fake_app = MagicMock()
    fake_app._workflow_engine = engine
    fake_app._manifest_loader = loader
    fake_app.agent_mgr = fake_agent_mgr
    fake_app._get_disabled_rules = None
    monkeypatch.setattr(mcp_mod, "_app", fake_app)

    raw_tool = mcp_mod._make_get_agent_info(caller_name="ghost")
    handler = getattr(raw_tool, "handler", raw_tool)
    response = await handler({})
    # Returns an error response per the resolver.
    assert response.get("isError") is True
    assert "ghost" in response["content"][0]["text"]


# ---------------------------------------------------------------------------
# D6 alignment: disabled rules dropped from MCP projections
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_d4_get_applicable_rules_consults_get_disabled_rules(monkeypatch):
    """``get_applicable_rules`` must call ``_app._get_disabled_rules`` and
    pass the merged set into ``assemble_constraints_block`` -- otherwise
    the MCP projection drifts from the hook layer.
    """
    from claudechic import mcp as mcp_mod

    engine = _make_fake_engine()
    loader = _StubLoader(
        LoadResult(
            rules=[
                _rule(id_="global:warn_sudo"),
                _rule(id_="global:no_rm_rf"),
            ]
        )
    )
    agent = _make_fake_agent(agent_type=DEFAULT_ROLE)
    disabled = frozenset({"global:warn_sudo"})
    fake_app = _make_fake_app(
        loader=loader, engine=engine, agent=agent, disabled_rules=disabled
    )
    monkeypatch.setattr(mcp_mod, "_app", fake_app)

    raw_tool = mcp_mod._make_get_applicable_rules(caller_name="test_caller")
    handler = getattr(raw_tool, "handler", raw_tool)
    response = await handler({"agent_name": "test_caller"})
    text = response["content"][0]["text"]

    # Disabled rule absent from the active table.
    assert "global:warn_sudo" not in text
    # Other rule still present.
    assert "global:no_rm_rf" in text
    # _get_disabled_rules was actually called (matches what the hook
    # layer reads -- D6 alignment).
    fake_app._get_disabled_rules.assert_called()


@pytest.mark.asyncio
async def test_d4_get_agent_info_consults_get_disabled_rules(monkeypatch):
    """``get_agent_info`` must consult ``_app._get_disabled_rules`` so its
    embedded ``## Constraints`` block surfaces the same active/inactive
    set as ``get_applicable_rules`` and the 5 prompt-injection sites.
    """
    from claudechic import mcp as mcp_mod

    engine = _make_fake_engine()
    loader = _StubLoader(LoadResult(rules=[_rule(id_="global:warn_sudo")]))
    agent = _make_fake_agent(agent_type=DEFAULT_ROLE)
    disabled = frozenset({"global:warn_sudo"})
    fake_app = _make_fake_app(
        loader=loader, engine=engine, agent=agent, disabled_rules=disabled
    )
    monkeypatch.setattr(mcp_mod, "_app", fake_app)

    raw_tool = mcp_mod._make_get_agent_info(caller_name="test_caller")
    handler = getattr(raw_tool, "handler", raw_tool)
    response = await handler({})
    text = response["content"][0]["text"]

    # Disabled rule does not appear in the aggregator's constraints body.
    assert "global:warn_sudo" not in text
    fake_app._get_disabled_rules.assert_called()


# ---------------------------------------------------------------------------
# Locked MCP tool name strings
# ---------------------------------------------------------------------------


def test_d4_mcp_tool_name_is_get_applicable_rules():
    """The MCP tool name is the locked contract string
    ``"get_applicable_rules"`` (qualified server-side as
    ``"mcp__chic__get_applicable_rules"``).
    """
    from claudechic import mcp as mcp_mod

    raw_tool = mcp_mod._make_get_applicable_rules(caller_name=None)
    assert getattr(raw_tool, "name", None) == "get_applicable_rules"


def test_d4_mcp_tool_name_is_get_agent_info():
    """The MCP tool name is the locked contract string ``"get_agent_info"``."""
    from claudechic import mcp as mcp_mod

    raw_tool = mcp_mod._make_get_agent_info(caller_name=None)
    assert getattr(raw_tool, "name", None) == "get_agent_info"


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
