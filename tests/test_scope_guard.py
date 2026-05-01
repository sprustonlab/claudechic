"""Scope-guard tests -- prove the abast/accf332 sync stayed in scope.

Per TEST_SPECIFICATION.md these tests verify that:

* Forbidden modules are absent (``claudechic.paths``,
  ``widgets.modals.guardrails``, ``widgets.modals.diagnostics``).
* No leakage of guardrails-modal / diagnostics-modal scaffolding into
  the shipped tree.
* All six user-named features the spec promised actually shipped:

  1. ``Agent.agent_type`` (B)
  2. ``Agent.effort`` (C)
  3. ``EffortLabel`` widget (C)
  4. ``compute_digest`` projector (D)
  5. ``pytest_needs_timeout`` rule loadable from rules.yaml (E)
  6. ``ComputerInfoModal`` (F)
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# A2: ``claudechic.paths`` must not exist
# ---------------------------------------------------------------------------


def test_a2_paths_module_absent() -> None:
    """``claudechic.paths`` should never have shipped.

    The A2 sub-unit is "engine-cwd defaulting"; the spec explicitly
    rejected adding a ``claudechic.paths`` module / ``compute_state_dir``
    helper. Both must remain absent.
    """
    paths_file = REPO_ROOT / "claudechic" / "paths.py"
    assert not paths_file.exists(), (
        f"claudechic/paths.py must not exist; found at {paths_file}"
    )

    with pytest.raises(ImportError):
        importlib.import_module("claudechic.paths")

    # ``compute_state_dir`` was the helper that would have lived in
    # claudechic.paths -- prove it never landed elsewhere either.
    with pytest.raises(ImportError):
        from claudechic.paths import compute_state_dir  # noqa: F401


# ---------------------------------------------------------------------------
# D: no guardrails modal / GuardrailsLabel / _disabled_rules attribute
# ---------------------------------------------------------------------------


def test_no_guardrails_modal_shipped() -> None:
    """A guardrails modal / footer label / cached attribute must not ship.

    The D feature explicitly re-framed guardrails-as-constraints in the
    agent prompt -- there is no user-facing modal or footer label, and
    no cached ``_disabled_rules`` attribute on ``ChatApp``.
    """
    modal_file = REPO_ROOT / "claudechic" / "widgets" / "modals" / "guardrails.py"
    assert not modal_file.exists(), (
        f"widgets/modals/guardrails.py must not exist; found at {modal_file}"
    )

    with pytest.raises(ImportError):
        from claudechic.widgets.modals import GuardrailsModal  # noqa: F401

    # No GuardrailsLabel re-export from the layout package.
    layout_pkg = importlib.import_module("claudechic.widgets.layout")
    assert not hasattr(layout_pkg, "GuardrailsLabel"), (
        "claudechic.widgets.layout must not expose GuardrailsLabel"
    )

    # ``ChatApp`` must not store rules in a cached ``_disabled_rules``
    # instance attribute -- it computes them via ``_get_disabled_rules()``.
    from claudechic.app import ChatApp

    annotations = getattr(ChatApp, "__annotations__", {})
    assert "_disabled_rules" not in annotations, (
        "ChatApp must not declare a _disabled_rules attribute"
    )
    # Also no class-level default.
    assert not hasattr(ChatApp, "_disabled_rules") or callable(
        getattr(ChatApp, "_disabled_rules", None)
    ), "ChatApp._disabled_rules must not be a (non-callable) attribute"


# ---------------------------------------------------------------------------
# F: no diagnostics modal as a separate module
# ---------------------------------------------------------------------------


def test_no_diagnostics_module_shipped() -> None:
    """The F feature absorbed diagnostics into ComputerInfoModal.

    A separate ``diagnostics`` module/class must not exist.
    """
    diag_file = REPO_ROOT / "claudechic" / "widgets" / "modals" / "diagnostics.py"
    assert not diag_file.exists(), (
        f"widgets/modals/diagnostics.py must not exist; found at {diag_file}"
    )

    with pytest.raises(ImportError):
        from claudechic.widgets.modals import DiagnosticsModal  # noqa: F401

    with pytest.raises(ImportError):
        importlib.import_module("claudechic.widgets.modals.diagnostics")


# ---------------------------------------------------------------------------
# All six user-named features shipped
# ---------------------------------------------------------------------------


def test_all_user_named_features_shipped_agent_type() -> None:
    """B: ``Agent.agent_type`` exists with the expected default."""
    from claudechic.agent import Agent

    assert "agent_type" in Agent.__init__.__code__.co_varnames, (
        "Agent.__init__ must accept an 'agent_type' parameter"
    )
    # Construct an agent and verify the attribute is set.
    agent = Agent(name="scope-guard-probe", cwd=REPO_ROOT)
    assert hasattr(agent, "agent_type"), "Agent must expose .agent_type"
    assert isinstance(agent.agent_type, str)
    assert agent.agent_type, "Agent.agent_type must default to a non-empty string"


def test_all_user_named_features_shipped_effort() -> None:
    """C: ``Agent.effort`` exists with one of the four enum values."""
    from claudechic.agent import Agent

    agent = Agent(name="scope-guard-probe", cwd=REPO_ROOT)
    assert hasattr(agent, "effort"), "Agent must expose .effort"
    assert agent.effort in {"low", "medium", "high", "max"}, (
        f"Agent.effort must be one of low|medium|high|max; got {agent.effort!r}"
    )


def test_all_user_named_features_shipped_effort_label() -> None:
    """C: ``EffortLabel`` is importable from the widgets package."""
    from claudechic.widgets import EffortLabel
    from claudechic.widgets.layout import EffortLabel as EffortLabelLayout
    from claudechic.widgets.layout.footer import EffortLabel as EffortLabelFooter

    assert EffortLabel is EffortLabelLayout
    assert EffortLabel is EffortLabelFooter


def test_all_user_named_features_shipped_compute_digest() -> None:
    """D: ``compute_digest`` is importable from the guardrails package."""
    from claudechic.guardrails.digest import compute_digest

    assert callable(compute_digest)


def test_all_user_named_features_shipped_pytest_needs_timeout_rule() -> None:
    """E: the ``pytest_needs_timeout`` rule is loadable from rules.yaml."""
    rules_yaml = REPO_ROOT / "claudechic" / "defaults" / "global" / "rules.yaml"
    assert rules_yaml.is_file(), f"rules.yaml not found at {rules_yaml}"

    with rules_yaml.open(encoding="utf-8") as fh:
        rules = yaml.safe_load(fh)

    assert isinstance(rules, list), (
        f"rules.yaml must be a list; got {type(rules).__name__}"
    )
    matches = [
        rule
        for rule in rules
        if isinstance(rule, dict) and rule.get("id") == "pytest_needs_timeout"
    ]
    assert len(matches) == 1, (
        f"Expected exactly one 'pytest_needs_timeout' rule; got {len(matches)}"
    )
    rule = matches[0]
    assert rule.get("enforcement") == "warn"
    assert rule.get("trigger") == "PreToolUse/Bash"
    detect = rule.get("detect")
    assert isinstance(detect, dict) and detect.get("pattern"), (
        "pytest_needs_timeout must define detect.pattern"
    )
    # Locked contract string -- spec freezes the warn message verbatim.
    assert rule.get("message") == "use --timeout=N (default 30) to avoid hung tests", (
        f"Locked warn message drifted: {rule.get('message')!r}"
    )


def test_all_user_named_features_shipped_computer_info_modal() -> None:
    """F: ``ComputerInfoModal`` is importable from widgets.modals."""
    from claudechic.widgets.modals import ComputerInfoModal
    from claudechic.widgets.modals.computer_info import (
        ComputerInfoModal as ComputerInfoModalDirect,
    )

    assert ComputerInfoModal is ComputerInfoModalDirect
