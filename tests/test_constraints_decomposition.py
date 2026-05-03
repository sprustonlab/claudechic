"""Tests for the slice/omit_heading decomposition machinery (SPEC §3.2.1).

Includes the keystone test ``slice_split_byte_identical`` -- the
slice="stable" + slice="phase" split must reassemble byte-identical to
the unsliced rendering.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from claudechic.workflows.agent_folders import (
    assemble_agent_prompt,
    assemble_constraints_block,
)
from claudechic.workflows.loader import LoadResult

pytestmark = [pytest.mark.timeout(30)]


# ---------------------------------------------------------------------------
# Helpers (copied from test_constraints_block.py -- test fixtures)
# ---------------------------------------------------------------------------


class _StubLoader:
    def __init__(self, result: LoadResult) -> None:
        self._result = result

    def load(self, **_kwargs):
        return self._result


def _entry(
    *,
    id_: str,
    namespace: str = "global",
    phases=None,
    active: bool = True,
    enforcement: str = "warn",
    trigger: str = "PreToolUse/Bash",
    message: str = "msg",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=id_,
        namespace=namespace,
        kind="rule",
        active=active,
        phases=list(phases or []),
        enforcement=enforcement,
        trigger=trigger,
        message=message,
    )


# ---------------------------------------------------------------------------
# slice="stable" / slice="phase"
# ---------------------------------------------------------------------------


def test_assemble_constraints_block_slice_stable_keeps_only_phase_agnostic_rules(
    monkeypatch,
):
    entries = [
        _entry(id_="global:agnostic"),
        _entry(id_="global:phase-only", phases=["design"]),
    ]
    monkeypatch.setattr(
        "claudechic.guardrails.digest.compute_digest", lambda *a, **k: entries
    )

    loader = _StubLoader(LoadResult())
    out = assemble_constraints_block(
        loader=loader,
        role="coordinator",
        phase="design",
        slice="stable",
    )
    assert "global:agnostic" in out
    assert "global:phase-only" not in out


def test_assemble_constraints_block_slice_phase_keeps_only_phase_qualified_rules(
    monkeypatch,
):
    entries = [
        _entry(id_="global:agnostic"),
        _entry(id_="global:phase-only", phases=["design"]),
    ]
    monkeypatch.setattr(
        "claudechic.guardrails.digest.compute_digest", lambda *a, **k: entries
    )

    loader = _StubLoader(LoadResult())
    out = assemble_constraints_block(
        loader=loader,
        role="coordinator",
        phase="design",
        slice="phase",
    )
    assert "global:phase-only" in out
    assert "global:agnostic" not in out


# ---------------------------------------------------------------------------
# omit_heading
# ---------------------------------------------------------------------------


def test_assemble_constraints_block_omit_heading_true_drops_constraints_heading(
    monkeypatch,
):
    monkeypatch.setattr(
        "claudechic.guardrails.digest.compute_digest",
        lambda *a, **k: [_entry(id_="global:foo")],
    )

    loader = _StubLoader(LoadResult())
    out = assemble_constraints_block(
        loader=loader,
        role="coordinator",
        phase="design",
        omit_heading=True,
    )
    assert "## Constraints" not in out
    assert out.lstrip().startswith("### Rules")


# ---------------------------------------------------------------------------
# KEYSTONE: slice_split_byte_identical
# ---------------------------------------------------------------------------


def test_constraints_slice_split_preserves_all_rule_ids(monkeypatch):
    """KEYSTONE: the composer (``assemble_agent_prompt``) routes both
    slices through the renderer split and produces a single output that
    contains every rule id from the monolithic rendering, with one
    ``## Constraints`` heading and one ``### Advance checks`` subsection.
    The slice split is information-preserving relative to the monolithic
    block: every id present in ``slice=None`` survives in the composed
    output, and the canonical headings appear exactly once.
    """
    entries = [
        _entry(id_="global:agnostic"),
        _entry(id_="global:phase-only", phases=["design"]),
    ]
    monkeypatch.setattr(
        "claudechic.guardrails.digest.compute_digest", lambda *a, **k: entries
    )

    loader = _StubLoader(LoadResult())
    monolithic = assemble_constraints_block(
        loader=loader, role="coordinator", phase="design", slice=None
    )

    # Stable + phase-headless: every id present in the monolithic block
    # survives somewhere in the split; the split is information-preserving.
    stable_part = assemble_constraints_block(
        loader=loader, role="coordinator", phase="design", slice="stable"
    )
    phase_part = assemble_constraints_block(
        loader=loader,
        role="coordinator",
        phase="design",
        slice="phase",
        omit_heading=True,
    )

    for rule_id in ("global:agnostic", "global:phase-only"):
        assert rule_id in monolithic
        assert rule_id in (stable_part + "\n" + phase_part), (
            f"Slice split lost rule id {rule_id!r}; "
            f"stable={stable_part!r} phase={phase_part!r}"
        )

    # Phase part with omit_heading=True drops the ## Constraints heading
    # so the two parts compose without a duplicate top-level heading.
    assert "## Constraints" not in phase_part
    assert "## Constraints" in stable_part

    # Composed output (the actual production path: assemble_agent_prompt
    # with slice split internally) emits a single ## Constraints heading.
    composed = assemble_agent_prompt(
        "coordinator",
        "design",
        loader,
        active_workflow="proj",
    )
    assert composed is not None
    assert composed.count("## Constraints") == 1
    for rule_id in ("global:agnostic", "global:phase-only"):
        assert rule_id in composed


# ---------------------------------------------------------------------------
# suppress_advance_checks
# ---------------------------------------------------------------------------


def test_assemble_constraints_block_suppress_advance_checks_drops_subsection(
    monkeypatch,
):
    monkeypatch.setattr(
        "claudechic.guardrails.digest.compute_digest",
        lambda *a, **k: [_entry(id_="global:foo")],
    )
    fake_check = SimpleNamespace(
        id="proj:design:advance:0",
        type="manual-confirm",
        command="confirm",
        summary="confirm",
        manual=True,
    )
    monkeypatch.setattr(
        "claudechic.guardrails.checks_digest.compute_advance_checks_digest",
        lambda *a, **k: [fake_check],
    )

    loader = _StubLoader(LoadResult())
    out_suppressed = assemble_constraints_block(
        loader=loader,
        role="coordinator",
        phase="design",
        engine=SimpleNamespace(),
        suppress_advance_checks=True,
    )
    out_default = assemble_constraints_block(
        loader=loader,
        role="coordinator",
        phase="design",
        engine=SimpleNamespace(),
        suppress_advance_checks=False,
    )
    # The check id appears in the default rendering and is suppressed
    # when ``suppress_advance_checks=True`` -- the row content is dropped.
    assert "proj:design:advance:0" in out_default
    assert "proj:design:advance:0" not in out_suppressed


# ---------------------------------------------------------------------------
# compact=True / False
# ---------------------------------------------------------------------------


def test_assemble_constraints_block_compact_true_yields_bullet_list(monkeypatch):
    monkeypatch.setattr(
        "claudechic.guardrails.digest.compute_digest",
        lambda *a, **k: [_entry(id_="global:foo")],
    )
    loader = _StubLoader(LoadResult())
    out = assemble_constraints_block(
        loader=loader,
        role="coordinator",
        phase=None,
        compact=True,
    )
    bullet_lines = [
        ln for ln in out.splitlines() if ln.startswith("- global:foo")
    ]
    assert bullet_lines, f"Expected bullet line for global:foo in:\n{out}"
    assert "|----" not in out


def test_assemble_constraints_block_compact_false_yields_markdown_table(
    monkeypatch,
):
    monkeypatch.setattr(
        "claudechic.guardrails.digest.compute_digest",
        lambda *a, **k: [_entry(id_="global:foo")],
    )
    loader = _StubLoader(LoadResult())
    out = assemble_constraints_block(
        loader=loader,
        role="coordinator",
        phase=None,
        compact=False,
    )
    # Alignment row is the canonical table marker.
    assert "|----" in out


# ---------------------------------------------------------------------------
# post_compact_full_refresh -- single ## Constraints heading
# ---------------------------------------------------------------------------


def test_assemble_constraints_block_post_compact_full_refresh_single_constraints_heading(
    monkeypatch, tmp_path
):
    entries = [
        _entry(id_="global:agnostic"),
        _entry(id_="global:phase-only", phases=["design"]),
    ]
    monkeypatch.setattr(
        "claudechic.guardrails.digest.compute_digest", lambda *a, **k: entries
    )

    role_dir = tmp_path / "coordinator"
    role_dir.mkdir()
    (role_dir / "identity.md").write_text("you are coord", encoding="utf-8")
    (role_dir / "design.md").write_text("design phase", encoding="utf-8")

    loader = _StubLoader(LoadResult())
    out = assemble_agent_prompt(
        "coordinator",
        "design",
        loader,
        workflow_dir=tmp_path,
        active_workflow="proj",
        time="post-compact",
    )
    assert out is not None
    # Single ## Constraints heading even though both stable + phase slices
    # render content (stable owns the heading; phase appended headless).
    assert out.count("## Constraints") == 1


# ---------------------------------------------------------------------------
# at_broadcast: phase-advance emits phase + constraints_phase only
# ---------------------------------------------------------------------------


def test_at_broadcast_emits_phase_and_constraints_phase_only(
    monkeypatch, tmp_path
):
    """At T3 (phase-advance): identity is suppressed, environment is
    suppressed, only phase + constraints_phase render. Single
    ``## Constraints`` heading.
    """
    entries = [
        _entry(id_="global:agnostic"),
        _entry(id_="global:phase-only", phases=["design"]),
    ]
    monkeypatch.setattr(
        "claudechic.guardrails.digest.compute_digest", lambda *a, **k: entries
    )

    role_dir = tmp_path / "coordinator"
    role_dir.mkdir()
    (role_dir / "identity.md").write_text(
        "IDENT-MARK", encoding="utf-8"
    )
    (role_dir / "design.md").write_text(
        "PHASE-MARK", encoding="utf-8"
    )

    loader = _StubLoader(LoadResult())
    out = assemble_agent_prompt(
        "coordinator",
        "design",
        loader,
        workflow_dir=tmp_path,
        active_workflow="proj",
        time="phase-advance",
    )
    assert out is not None
    # Identity suppressed at T3; phase content kept.
    assert "IDENT-MARK" not in out
    assert "PHASE-MARK" in out
    # constraints_phase rule id present.
    assert "global:phase-only" in out
    # Single ## Constraints heading.
    assert out.count("## Constraints") == 1


# ---------------------------------------------------------------------------
# Skeptic Gap 2 -- standing-by role at T3 (E2E through assemble_agent_prompt)
# ---------------------------------------------------------------------------


def test_at_broadcast_standing_by_role_emits_only_constraints_phase(
    monkeypatch, tmp_path
):
    """Skeptic Gap 2: a typed sub-agent at phase-advance whose
    ``<role>/<phase>.md`` does not exist (standing-by predicate True)
    receives only the ``constraints_phase`` slice. Identity and phase
    return empty. The composed output contains the rule id and no role
    markdown markers.

    Pins the gate's standing-by suppression end-to-end: even though
    workflow_dir is real and other roles have phase markdown, the
    skeptic's missing ``skeptic/design.md`` triggers the standing_by
    branch in ``gate(time="phase-advance", place="identity"|"phase",
    role="skeptic", ...)`` -> False.
    """
    entries = [_entry(id_="global:phase-only", phases=["design"])]
    monkeypatch.setattr(
        "claudechic.guardrails.digest.compute_digest", lambda *a, **k: entries
    )

    # Coordinator has phase markdown for design; skeptic does NOT.
    coord_dir = tmp_path / "coordinator"
    coord_dir.mkdir()
    (coord_dir / "identity.md").write_text("COORD-IDENT", encoding="utf-8")
    (coord_dir / "design.md").write_text("COORD-PHASE", encoding="utf-8")
    skeptic_dir = tmp_path / "skeptic"
    skeptic_dir.mkdir()
    (skeptic_dir / "identity.md").write_text("SKEPTIC-IDENT", encoding="utf-8")
    # No skeptic/design.md -> standing_by at T3.

    loader = _StubLoader(LoadResult())
    out = assemble_agent_prompt(
        "skeptic",
        "design",
        loader,
        workflow_dir=tmp_path,
        active_workflow="proj",
        time="phase-advance",
    )
    assert out is not None, "constraints_phase must still fire for standing-by recipient"
    # Identity and phase both suppressed.
    assert "SKEPTIC-IDENT" not in out
    assert "COORD-IDENT" not in out
    assert "COORD-PHASE" not in out
    # constraints_phase rule id present (the slice fires).
    assert "global:phase-only" in out
    # constraints_phase owns its heading at T3.
    assert "## Constraints" in out


# ---------------------------------------------------------------------------
# Skeptic Gap 3 -- cross-layer contract: compute_digest -> slice("phase")
# ---------------------------------------------------------------------------


def test_compute_digest_phases_field_drives_slice_phase_filter():
    """Skeptic Gap 3: the ``slice="phase"`` filter in
    ``assemble_constraints_block`` reads ``entry.phases`` from
    ``compute_digest``'s output (``GuardrailEntry.phases: list[str]``).
    A future change that drops or renames the ``phases`` field on
    ``GuardrailEntry`` would silently break the slice filter -- this
    test pins the contract.

    Uses real ``compute_digest`` against a real ``LoadResult`` with one
    phase-qualified rule and one phase-agnostic rule. Asserts:
    - The phase-qualified rule has a non-empty ``phases`` list.
    - The phase-agnostic rule has an empty ``phases`` list.
    - Slice="phase" output contains only the phase-qualified rule.
    - Slice="stable" output contains only the phase-agnostic rule.
    """
    from claudechic.guardrails.digest import GuardrailEntry, compute_digest
    from claudechic.guardrails.rules import Rule

    phase_rule = Rule(
        id="proj:phase-only",
        namespace="proj",
        trigger=["PreToolUse/Bash"],
        enforcement="warn",
        message="phase-scoped",
        phases=["design"],
    )
    stable_rule = Rule(
        id="proj:always",
        namespace="proj",
        trigger=["PreToolUse/Bash"],
        enforcement="warn",
        message="stable",
    )
    loader = _StubLoader(LoadResult(rules=[phase_rule, stable_rule]))

    entries = compute_digest(
        loader=loader,
        active_wf="proj",
        agent_role="coordinator",
        current_phase="design",
        disabled_rules=set(),
    )

    # Contract pin 1: GuardrailEntry exposes ``phases`` as a list[str].
    by_id = {e.id: e for e in entries}
    assert isinstance(by_id["proj:phase-only"], GuardrailEntry)
    assert by_id["proj:phase-only"].phases == ["design"]
    assert by_id["proj:always"].phases == []

    # Contract pin 2: slice="phase" keeps only phase-qualified rules; the
    # filter reads ``entry.phases`` (truthy iff phase-qualified).
    phase_block = assemble_constraints_block(
        loader=loader,
        role="coordinator",
        phase="design",
        active_workflow="proj",
        slice="phase",
    )
    assert "proj:phase-only" in phase_block
    assert "proj:always" not in phase_block

    # Contract pin 3: slice="stable" keeps only phase-agnostic rules.
    stable_block = assemble_constraints_block(
        loader=loader,
        role="coordinator",
        phase="design",
        active_workflow="proj",
        slice="stable",
    )
    assert "proj:always" in stable_block
    assert "proj:phase-only" not in stable_block
