"""Tests for the pure ``gate(time, place, role, phase, settings, manifest)``
predicate in ``claudechic.workflows.agent_folders``.

The gate is a pure boolean function of (time, place, role, phase,
settings, manifest). These tests exercise the matrix per SPEC §2 / §3.10.
"""

from __future__ import annotations

import pytest
from claudechic.agent import DEFAULT_ROLE
from claudechic.workflows.agent_folders import (
    CONSTRAINTS_SEGMENT_SITES,
    ENVIRONMENT_SEGMENT_SITES,
    ConstraintsSegmentSettings,
    EnvironmentSegmentSettings,
    GateManifest,
    GateSettings,
    gate,
)

pytestmark = [pytest.mark.timeout(30)]


# ---------------------------------------------------------------------------
# time=None rejection
# ---------------------------------------------------------------------------


def test_gate_time_none_raises_value_error():
    with pytest.raises(ValueError):
        gate(
            time=None,  # type: ignore[arg-type]
            place="identity",
            role="coordinator",
            phase=None,
            settings=GateSettings(),
            manifest=GateManifest(),
        )


# ---------------------------------------------------------------------------
# Default segment set per site
# ---------------------------------------------------------------------------


def test_gate_default_segment_set_at_spawn_includes_all_five_places():
    settings = GateSettings()
    manifest = GateManifest()
    for place in (
        "identity",
        "phase",
        "constraints_stable",
        "constraints_phase",
        "environment",
    ):
        assert (
            gate(
                time="spawn",
                place=place,  # type: ignore[arg-type]
                role="coordinator",
                phase="design",
                settings=settings,
                manifest=manifest,
            )
            is True
        ), f"spawn / {place} should be True under defaults"


def test_gate_phase_advance_default_set_excludes_identity_and_environment():
    settings = GateSettings()
    # Make this NOT a standing-by cell so the standing-by branch is moot
    # and we exercise only the default-segment-set + sites layers.
    manifest = GateManifest(
        role_phase_files=frozenset({("coordinator", "design")})
    )
    # Excluded
    for place in ("identity", "environment", "constraints_stable"):
        assert (
            gate(
                time="phase-advance",
                place=place,  # type: ignore[arg-type]
                role="coordinator",
                phase="design",
                settings=settings,
                manifest=manifest,
            )
            is False
        ), f"phase-advance / {place} should be False under defaults"
    # Included
    for place in ("phase", "constraints_phase"):
        assert (
            gate(
                time="phase-advance",
                place=place,  # type: ignore[arg-type]
                role="coordinator",
                phase="design",
                settings=settings,
                manifest=manifest,
            )
            is True
        ), f"phase-advance / {place} should be True under defaults"


# ---------------------------------------------------------------------------
# constraints_segment.scope.sites suppression
# ---------------------------------------------------------------------------


def test_gate_constraints_segment_scope_sites_excluded_returns_false():
    # Drop ``post-compact`` from constraints sites. Both stable + phase
    # should suppress at that site.
    cs = ConstraintsSegmentSettings(sites=frozenset({"spawn", "activation"}))
    settings = GateSettings(constraints_segment=cs)
    manifest = GateManifest()
    for place in ("constraints_stable", "constraints_phase"):
        assert (
            gate(
                time="post-compact",
                place=place,  # type: ignore[arg-type]
                role="coordinator",
                phase="design",
                settings=settings,
                manifest=manifest,
            )
            is False
        ), f"post-compact / {place} should be suppressed by sites override"


# ---------------------------------------------------------------------------
# environment_segment.enabled tri-state
# ---------------------------------------------------------------------------


def test_gate_environment_segment_enabled_false_returns_false_at_all_three_sites():
    es = EnvironmentSegmentSettings(enabled=False)
    settings = GateSettings(environment_segment=es)
    manifest = GateManifest()
    for time_ in ("spawn", "activation", "post-compact"):
        assert (
            gate(
                time=time_,  # type: ignore[arg-type]
                place="environment",
                role="coordinator",
                phase=None,
                settings=settings,
                manifest=manifest,
            )
            is False
        ), f"environment must be suppressed at {time_} when enabled=False"


def test_gate_environment_segment_enabled_none_resolves_to_true():
    # None is the user-tier sentinel meaning "no override"; resolves True.
    es = EnvironmentSegmentSettings(enabled=None)
    settings = GateSettings(environment_segment=es)
    manifest = GateManifest()
    assert (
        gate(
            time="spawn",
            place="environment",
            role="coordinator",
            phase=None,
            settings=settings,
            manifest=manifest,
        )
        is True
    )


# ---------------------------------------------------------------------------
# Standing-by suppression (SPEC §3.6, §3.8)
# ---------------------------------------------------------------------------


def test_gate_standing_by_predicate_true_when_role_phase_md_missing():
    # Empty role_phase_files -> any non-default role / non-None phase is
    # standing-by.
    settings = GateSettings()
    manifest = GateManifest(role_phase_files=frozenset())
    # identity + phase suppressed at phase-advance for standing-by cell.
    # (Default segment set already drops identity at phase-advance, but
    # the standing-by branch is also active -- both yield False.)
    assert (
        gate(
            time="phase-advance",
            place="identity",
            role="skeptic",
            phase="design",
            settings=settings,
            manifest=manifest,
        )
        is False
    )
    assert (
        gate(
            time="phase-advance",
            place="phase",
            role="skeptic",
            phase="design",
            settings=settings,
            manifest=manifest,
        )
        is False
    )
    # constraints_phase still True (the phase delta is the whole point).
    assert (
        gate(
            time="phase-advance",
            place="constraints_phase",
            role="skeptic",
            phase="design",
            settings=settings,
            manifest=manifest,
        )
        is True
    )


def test_gate_default_role_never_standing_by():
    # DEFAULT_ROLE is excluded from the standing-by branch even if no
    # phase markdown exists. The default segment set still drops phase at
    # phase-advance only via the standing-by branch -- so for default role
    # the ``phase`` slot follows the default segment set: True.
    settings = GateSettings()
    manifest = GateManifest(role_phase_files=frozenset())
    assert (
        gate(
            time="phase-advance",
            place="phase",
            role=DEFAULT_ROLE,
            phase="design",
            settings=settings,
            manifest=manifest,
        )
        is True
    )


# ---------------------------------------------------------------------------
# Purity
# ---------------------------------------------------------------------------


def test_gate_purity_same_inputs_same_output(monkeypatch):
    # Pin: gate is pure. Patching wall-clock between calls must not
    # change behavior; same inputs -> same bool.
    settings = GateSettings()
    manifest = GateManifest(
        role_phase_files=frozenset({("coordinator", "design")})
    )
    first = gate(
        time="spawn",
        place="phase",
        role="coordinator",
        phase="design",
        settings=settings,
        manifest=manifest,
    )

    import time as time_mod

    monkeypatch.setattr(time_mod, "time", lambda: 0.0)

    second = gate(
        time="spawn",
        place="phase",
        role="coordinator",
        phase="design",
        settings=settings,
        manifest=manifest,
    )
    assert first == second
    # Sanity: this particular cell is True under defaults.
    assert first is True


# Sanity assertion for the bundled site-set constants (SPEC §3.7, §3.11).
def test_gate_site_set_constants_match_defaults():
    assert CONSTRAINTS_SEGMENT_SITES == frozenset(
        {"spawn", "activation", "phase-advance", "post-compact"}
    )
    assert ENVIRONMENT_SEGMENT_SITES == frozenset(
        {"spawn", "activation", "post-compact"}
    )
