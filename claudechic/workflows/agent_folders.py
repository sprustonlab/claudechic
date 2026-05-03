"""Agent folder utilities -- prompt assembly and post-compact hook.

Reads a single resolved workflow directory (the winning-tier path on
``LoadResult.workflows[wf_id].path``) to assemble agent prompts from
identity.md + phase.md files. Multi-tier scanning is the loader's job;
this module is post-resolution.

Also exposes the ``## Constraints`` block formatter
(``assemble_constraints_block``) and the single composition helper
(``assemble_agent_prompt``) used by every prompt-injection site so the
agent's launch prompt embeds its role+phase scoped rules and
advance-checks.

This module also defines the seam types used by the gating predicate
(``GateSettings`` and ``GateManifest``). These frozen dataclasses are
constructed by the configuration / loader plumbing and consumed by the
pure ``gate(...)`` predicate that decides per (time, place, role) cell
whether a renderer's output is injected at a prompt-assembly site.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from string import Template
from typing import TYPE_CHECKING, Any, Literal

from claude_agent_sdk.types import HookMatcher

from claudechic.agent import DEFAULT_ROLE
from claudechic.workflows._substitute import (
    substitute_artifact_dir,
    substitute_coordinator_name,
    substitute_workflow_root,
)

if TYPE_CHECKING:
    from claudechic.workflows.loader import ManifestLoader

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Gate seam types -- inputs to the pure ``gate(time, place, role, phase,
# settings, manifest)`` predicate (SPEC §2). The predicate lives in this
# module; the dataclasses live here too so the seam shape is single-sourced.
# ---------------------------------------------------------------------------

InjectionSite = Literal["spawn", "activation", "phase-advance", "post-compact"]
"""The four prompt-assembly call sites (SPEC §3.1, time axis)."""

PromptSegment = Literal[
    "identity",
    "phase",
    "constraints_stable",
    "constraints_phase",
    "environment",
]
"""The five prompt segments (SPEC §3.2, place axis)."""


# Default site sets per segment family (SPEC §3.7, §3.11). Used both
# as documented defaults in ``GateSettings`` AND as the upper-bound
# allowlist for site validation in ``config.py``.
CONSTRAINTS_SEGMENT_SITES: frozenset[str] = frozenset(
    {"spawn", "activation", "phase-advance", "post-compact"}
)
ENVIRONMENT_SEGMENT_SITES: frozenset[str] = frozenset(
    {"spawn", "activation", "post-compact"}
)


@dataclass(frozen=True)
class ConstraintsSegmentSettings:
    """User/project-tier configuration for the constraints segment.

    Mirrors the ``constraints_segment:`` YAML block (SPEC §3.7). Empty
    ``sites`` is rejected at config-load time before construction; this
    dataclass simply carries the validated values to the gate predicate.
    """

    compact: bool = True
    include_skipped: bool = False
    sites: frozenset[str] = field(default_factory=lambda: CONSTRAINTS_SEGMENT_SITES)


@dataclass(frozen=True)
class EnvironmentSegmentSettings:
    """User/project-tier configuration for the environment segment.

    Mirrors the ``environment_segment:`` YAML block (SPEC §3.11).

    Per the user-approved SPEC change, the per-workflow manifest opt-in
    layer has been removed. ``enabled`` is a tri-state but the ``None``
    sentinel now resolves to ``True`` (segment enabled by default for
    every workflow). Set ``enabled=False`` to opt out explicitly.
    """

    enabled: bool | None = None
    compact: bool = False
    sites: frozenset[str] = field(default_factory=lambda: ENVIRONMENT_SEGMENT_SITES)


@dataclass(frozen=True)
class GateSettings:
    """All user-controllable gate inputs (SPEC §3.7, §3.11).

    Constructed from CONFIG (user-tier) merged with ProjectConfig
    (project-tier wins) by ``config.build_gate_settings``.
    """

    constraints_segment: ConstraintsSegmentSettings = field(
        default_factory=ConstraintsSegmentSettings
    )
    environment_segment: EnvironmentSegmentSettings = field(
        default_factory=EnvironmentSegmentSettings
    )


@dataclass(frozen=True)
class GateManifest:
    """All loader/workflow-derived gate inputs (SPEC §3.8).

    - ``role_phase_files`` -- ``frozenset`` of ``(role, bare_phase)`` pairs
      where ``<workflow_dir>/<role>/<bare_phase>.md`` EXISTS. The standing-by
      predicate (SPEC §3.8) is ``role != DEFAULT_ROLE AND
      (role, bare_phase) not in role_phase_files``.

    The previous ``environment_segment_enabled`` field has been removed
    per the user-approved SPEC change: the per-workflow manifest opt-in
    layer was dropped. ``GateSettings.environment_segment.enabled``
    (default ``None`` -> resolves to ``True``) is the sole control.
    """

    role_phase_files: frozenset[tuple[str, str]] = field(default_factory=frozenset)

    def is_standing_by(self, role: str, phase: str | None) -> bool:
        """Return True iff ``(role, phase)`` is the standing-by cell.

        Pure -- evaluated only against the captured manifest data; no
        I/O. ``DEFAULT_ROLE`` is never standing-by (SPEC §3.8). Phase
        ``None`` collapses to "no phase markdown to look for" -> not
        standing-by (the cell is decided by other places).
        """
        if not role or role == DEFAULT_ROLE:
            return False
        if phase is None:
            return False
        bare = phase.split(":", 1)[1] if ":" in phase else phase
        return (role, bare) not in self.role_phase_files


def effective_environment_enabled(
    settings: GateSettings | None,
    manifest: GateManifest | None,  # noqa: ARG001 -- retained for signature stability; manifest opt-in removed per user-approved SPEC change.
) -> bool:
    """Resolve the effective ``environment_segment.enabled`` value.

    Per the user-approved SPEC change, the per-workflow manifest opt-in
    (``GateManifest.environment_segment_enabled``) was removed. The
    environment segment is enabled by default for every workflow; only
    an explicit user-tier override (``settings.environment_segment.enabled
    = False``) disables it.

    Returns:
        ``False`` only when the user has explicitly opted out via
        ``settings.environment_segment.enabled = False``. ``True`` in all
        other cases (``None`` -- the user-tier sentinel meaning "no
        override" -- now resolves to ``True``; ``True`` -- explicit user
        opt-in -- also resolves to ``True``).

    Pure helper -- safe to call from the gate predicate.
    """
    user_value: bool | None = None
    if settings is not None:
        user_value = settings.environment_segment.enabled
    if user_value is None:
        return True
    return user_value


def build_gate_manifest(
    loader: ManifestLoader | None,  # noqa: ARG001 -- retained for signature stability; manifest opt-in lookup removed.
    active_workflow: str | None,  # noqa: ARG001 -- same.
    workflow_dir: Path | None,
) -> GateManifest:
    """Build a ``GateManifest`` from ``workflow_dir``.

    Canonical helper for the ``assemble_agent_prompt`` fallback path.
    Per the user-approved SPEC change, the per-workflow manifest opt-in
    field (``environment_segment_enabled``) was removed; this helper
    no longer consults the loader for that flag and only scans the
    workflow directory for standing-by predicate inputs (SPEC §3.8).

    The ``loader`` and ``active_workflow`` parameters are retained for
    signature stability (callers continue to pass them) but are no
    longer used.
    """
    return GateManifest(
        role_phase_files=scan_role_phase_files(workflow_dir),
    )


def scan_role_phase_files(workflow_dir: Path | None) -> frozenset[tuple[str, str]]:
    """Scan a workflow directory for ``<role>/<bare_phase>.md`` markers.

    Returns a frozenset of ``(role, bare_phase)`` tuples for every
    role-phase markdown file present under ``workflow_dir``. Used to
    build ``GateManifest.role_phase_files`` (SPEC §3.8 standing-by data).

    Returns an empty frozenset when ``workflow_dir`` is ``None`` or not a
    directory. Identity files (``identity.md``) are NOT included --
    standing-by is decided by phase-file presence only.
    """
    if workflow_dir is None or not workflow_dir.is_dir():
        return frozenset()
    pairs: set[tuple[str, str]] = set()
    for role_dir in workflow_dir.iterdir():
        if not role_dir.is_dir() or role_dir.name.startswith("."):
            continue
        role = role_dir.name
        for child in role_dir.iterdir():
            if not child.is_file() or child.suffix != ".md":
                continue
            stem = child.stem
            if stem == "identity":
                continue
            pairs.add((role, stem))
    return frozenset(pairs)


# ---------------------------------------------------------------------------
# RenderContext: frozen seam carrying inputs to every segment renderer.
# Renderers read it; they do not mutate. Same context -> same output.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RenderContext:
    """Inputs to every prompt-segment renderer (SPEC §3.2)."""

    role: str
    phase: str | None
    workflow_dir: Path | None = None
    artifact_dir: Path | None = None
    project_root: Path | None = None
    loader: "ManifestLoader | None" = None
    engine: Any | None = None
    active_workflow: str | None = None
    disabled_rules: frozenset[str] | None = None
    settings: GateSettings = field(default_factory=GateSettings)
    manifest: GateManifest = field(default_factory=GateManifest)
    time: InjectionSite | None = None
    # Optional substitution tokens for the environment renderer. Keys
    # are bare token names (no ``${}``). Remaining tokens consumed by
    # ``base.md`` after the terminology bundle revisions: ``AGENT_ROLE``,
    # ``ACTIVE_WORKFLOW``, ``WORKFLOW_ROOT``, ``CLAUDECHIC_ARTIFACT_DIR``,
    # ``PEER_ROSTER``. The first four are intrinsic (built from ctx);
    # ``PEER_ROSTER`` is built from ``peer_agents`` merged with the
    # workflow overlay's ``role | description`` table.
    environment_tokens: dict[str, str] = field(default_factory=dict)
    # Mapping ``role -> registered_name`` for currently-spawned peer
    # agents. Used by the environment renderer to build the
    # ``${PEER_ROSTER}`` table (3-col: role | registered_name |
    # description). Coordinator-only segment; rows are limited to roles
    # currently present in this map.
    peer_agents: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Pure renderers. Each returns ``str`` (never ``None``); empty when no
# source content. The composer drops empty segments.
# ---------------------------------------------------------------------------


def _coordinator_name_from(ctx: RenderContext) -> str:
    """Resolve ``${COORDINATOR_NAME}`` from ``ctx.peer_agents``.

    Returns the registered name of the agent currently filling the
    ``coordinator`` role, or ``""`` if no coordinator is spawned. Pure;
    same context produces the same value.
    """
    return (ctx.peer_agents or {}).get("coordinator", "") or ""


def _render_identity(ctx: RenderContext) -> str:
    """Read ``<workflow_dir>/<role>/identity.md`` and substitute tokens."""
    if ctx.workflow_dir is None:
        return ""
    identity_path = ctx.workflow_dir / ctx.role / "identity.md"
    if not identity_path.is_file():
        return ""
    text = identity_path.read_text(encoding="utf-8")
    text = substitute_artifact_dir(text, ctx.artifact_dir)
    text = substitute_workflow_root(text, ctx.project_root)
    text = substitute_coordinator_name(text, _coordinator_name_from(ctx))
    return text


def _render_phase(ctx: RenderContext) -> str:
    """Read ``<workflow_dir>/<role>/<bare_phase>.md`` and substitute tokens."""
    if ctx.workflow_dir is None or not ctx.phase:
        return ""
    bare_phase = ctx.phase.split(":", 1)[1] if ":" in ctx.phase else ctx.phase
    phase_path = ctx.workflow_dir / ctx.role / f"{bare_phase}.md"
    if not phase_path.is_file():
        return ""
    text = phase_path.read_text(encoding="utf-8")
    text = substitute_artifact_dir(text, ctx.artifact_dir)
    text = substitute_workflow_root(text, ctx.project_root)
    text = substitute_coordinator_name(text, _coordinator_name_from(ctx))
    return text


def _render_constraints_stable(ctx: RenderContext) -> str:
    """Render the stable (global + role-scoped, non-phase) constraints slice.

    Owns the ``## Constraints`` heading. Returns ``""`` when the slice is
    empty.
    """
    return assemble_constraints_block(
        ctx.loader,
        ctx.role,
        ctx.phase,
        engine=ctx.engine,
        active_workflow=ctx.active_workflow,
        disabled_rules=ctx.disabled_rules,
        include_skipped=ctx.settings.constraints_segment.include_skipped,
        compact=ctx.settings.constraints_segment.compact,
        slice="stable",
        omit_heading=False,
    )


def _render_constraints_phase(ctx: RenderContext, *, omit_heading: bool) -> str:
    """Render the phase-scoped constraints slice.

    Heading emission is composer-driven via ``omit_heading``. Advance-checks
    subsection is coordinator-only (SPEC §3.2.1): when ``ctx.role !=
    "coordinator"`` the subsection is suppressed.
    """
    return assemble_constraints_block(
        ctx.loader,
        ctx.role,
        ctx.phase,
        engine=ctx.engine,
        active_workflow=ctx.active_workflow,
        disabled_rules=ctx.disabled_rules,
        include_skipped=ctx.settings.constraints_segment.include_skipped,
        compact=ctx.settings.constraints_segment.compact,
        slice="phase",
        omit_heading=omit_heading,
        suppress_advance_checks=(ctx.role != "coordinator"),
    )


def _render_environment(ctx: RenderContext) -> str:
    """Render the environment segment (workflow-agnostic + workflow overlay).

    Reads ``claudechic/defaults/environment/base.md`` (workflow-agnostic
    template; ``string.Template`` substitution) and an optional workflow
    overlay ``claudechic/defaults/environment/<workflow>.md``. Returns
    ``""`` when neither file exists.

    Compact mode (``settings.environment_segment.compact=True``) drops the
    workflow overlay; only ``base.md`` renders.

    Activation is enforced by the gate predicate (which consults
    ``effective_environment_enabled(settings, manifest)``), not here --
    this renderer trusts the gate. Per the user-approved SPEC change,
    the per-workflow manifest opt-in is removed; the segment is enabled
    by default for every workflow and the user opts OUT via
    ``settings.environment_segment.enabled = False``.

    Bundle files are authored by ``impl_bundle_content``; until they
    exist, this renderer returns ``""`` and the composer drops the
    segment cleanly.

    Renderer also returns ``""`` when no real workflow context is
    available (``ctx.active_workflow`` is unset OR ``ctx.workflow_dir``
    is missing / not a directory). The segment carries workflow-context
    information; emitting it in the no-workflow baseline (or in
    contrived test paths with a workflow id but no workflow directory)
    would leak the bundled ``base.md`` content into degenerate
    assemblies. The user-facing semantics ("enabled for every workflow
    by default") are preserved -- only no-real-workflow cases are
    suppressed.
    """
    if not ctx.active_workflow:
        return ""
    if ctx.workflow_dir is None or not ctx.workflow_dir.is_dir():
        return ""

    pkg_root = Path(__file__).resolve().parent.parent
    env_dir = pkg_root / "defaults" / "environment"
    base_path = env_dir / "base.md"

    # Build ${PEER_ROSTER}: 3-column table (role | registered_name |
    # description) merged from the workflow overlay's 2-column
    # role|description table and ``ctx.peer_agents``. Coordinator-only
    # (mirrors the advance-checks coordinator-only check in
    # ``_render_constraints_phase``); empty string for any other role.
    peer_roster_value = ""
    if ctx.role == "coordinator" and ctx.peer_agents:
        overlay_path = env_dir / f"{ctx.active_workflow}.md"
        role_to_desc = _parse_role_description_table(overlay_path)
        peer_roster_value = _render_peer_roster(role_to_desc, ctx.peer_agents)

    intrinsic = {
        "AGENT_ROLE": ctx.role or "",
        "ACTIVE_WORKFLOW": ctx.active_workflow or "",
        "WORKFLOW_ROOT": str(ctx.project_root) if ctx.project_root else "",
        "CLAUDECHIC_ARTIFACT_DIR": (
            str(ctx.artifact_dir) if ctx.artifact_dir else ""
        ),
        "PEER_ROSTER": peer_roster_value,
        "COORDINATOR_NAME": _coordinator_name_from(ctx),
    }
    tokens = {**intrinsic, **(ctx.environment_tokens or {})}

    if not base_path.is_file():
        return ""
    try:
        base_text = base_path.read_text(encoding="utf-8")
    except OSError as e:
        logger.debug("environment: failed to read %s: %s", base_path, e)
        return ""
    return Template(base_text).safe_substitute(tokens).rstrip()


def _parse_role_description_table(overlay_path: Path) -> dict[str, str]:
    """Parse a 2-column ``| role | description |`` markdown table.

    Returns a ``{role: description}`` dict. Skips the header row
    (``| role | description |``) and the alignment row
    (``|------|-------------|``). Empty rows and malformed lines are
    silently dropped. Returns ``{}`` when the file is absent.
    """
    if not overlay_path.is_file():
        return {}
    try:
        text = overlay_path.read_text(encoding="utf-8")
    except OSError as e:
        logger.debug("environment: failed to read %s: %s", overlay_path, e)
        return {}
    out: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|") or not line.endswith("|"):
            continue
        # Split on '|' and trim outer empties.
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != 2:
            continue
        role, desc = cells
        # Skip header and alignment rows.
        if not role or role.lower() == "role":
            continue
        if set(role) <= set("-: "):
            continue
        out[role] = desc
    return out


def _render_peer_roster(
    role_to_desc: dict[str, str],
    peer_agents: dict[str, str],
) -> str:
    """Render the merged 3-column ``role | name | description`` table.

    Only includes rows for roles currently present in ``peer_agents``
    (the merge filter -- peers not spawned do not appear). When no
    peers are present, returns ``""``. Roles in ``peer_agents`` without
    a description in ``role_to_desc`` render with an empty
    description cell rather than being dropped (visibility over
    silence).
    """
    if not peer_agents:
        return ""
    rows: list[str] = []
    for role, name in sorted(peer_agents.items()):
        desc = role_to_desc.get(role, "")
        rows.append(f"| {role} | {name} | {desc} |")
    if not rows:
        return ""
    header = [
        "## Project team peer roster",
        "",
        "| role | name | description |",
        "|------|------|-------------|",
    ]
    return "\n".join(header + rows)


# ---------------------------------------------------------------------------
# Gate predicate: pure, single-layer (SPEC §2, §3.10). gate = user_gate.
# ---------------------------------------------------------------------------


# Default segment set per (site, place). SPEC §3.1 default segment table.
_DEFAULT_SEGMENT_SET: dict[str, frozenset[str]] = {
    "spawn": frozenset(
        {
            "identity",
            "phase",
            "constraints_stable",
            "constraints_phase",
            "environment",
        }
    ),
    "activation": frozenset(
        {
            "identity",
            "phase",
            "constraints_stable",
            "constraints_phase",
            "environment",
        }
    ),
    "phase-advance": frozenset({"phase", "constraints_phase"}),
    "post-compact": frozenset(
        {
            "identity",
            "phase",
            "constraints_stable",
            "constraints_phase",
            "environment",
        }
    ),
}


def gate(
    time: InjectionSite,
    place: PromptSegment,
    role: str,
    phase: str | None,
    settings: GateSettings,
    manifest: GateManifest,
) -> bool:
    """Return True iff segment ``place`` should render at site ``time``.

    Pure -- no I/O, no wall-clock. Same inputs -> same bool. SPEC §2 / §7.

    Single-layer composition (``gate = user_gate``); no structural floor.
    Honors ``constraints_segment.scope.sites`` and
    ``environment_segment.scope.sites``. Honors standing-by suppression
    for typed sub-agents at phase-advance whose ``<role>/<phase>.md``
    does not exist (SPEC §3.6, §3.8).

    Strictness: ``time`` must be one of the four ``InjectionSite``
    values. ``time=None`` is rejected with ``ValueError`` -- earlier
    drafts allowed an open-gate degenerate path, but that was a hidden
    bypass of the user's settings (skeptic + leadership flagged it).
    Non-injection-site callers (test paths, the coordinator's
    advance_phase synchronous return value) do not pass through
    ``gate``; they go through ``_assemble_agent_prompt_ungated`` (called
    by ``assemble_agent_prompt`` when ``time=None``) which renders every
    segment without consulting the gate.
    """
    if time is None:
        raise ValueError(
            "gate(time=None) is not a valid call -- pass one of "
            f"{list(_DEFAULT_SEGMENT_SET.keys())}. Non-injection-site "
            "callers must use assemble_agent_prompt(time=None) which "
            "routes through the explicit ungated path."
        )

    # Default segment set per (site, place).
    if place not in _DEFAULT_SEGMENT_SET[time]:
        return False

    # Standing-by suppression: typed sub-agents at phase-advance whose
    # <role>/<phase>.md is absent receive only constraints_phase (the
    # phase delta). identity/phase auto-suppress here, even though the
    # default segment set already drops identity at T3 -- this branch is
    # the future-proof anchor and the explicit phase-suppress for the
    # standing-by cell.
    if (
        time == "phase-advance"
        and place in ("identity", "phase")
        and role != DEFAULT_ROLE
        and manifest.is_standing_by(role, phase)
    ):
        return False

    # constraints_segment.scope.sites: user-tier suppression for both
    # constraints slices.
    if place in ("constraints_stable", "constraints_phase"):
        if time not in settings.constraints_segment.sites:
            return False

    # environment_segment activation + scope.sites.
    if place == "environment":
        if not effective_environment_enabled(settings, manifest):
            return False
        if time not in settings.environment_segment.sites:
            return False

    return True


# Order in which segments compose. identity + phase form the head block
# (joined by ``"\n\n---\n\n"``); the remaining segments append with
# ``"\n\n"``.
_SEGMENT_ORDER: tuple[PromptSegment, ...] = (
    "identity",
    "phase",
    "constraints_stable",
    "constraints_phase",
    "environment",
)


def _assemble_agent_prompt(
    workflow_dir: Path,
    role_name: str,
    current_phase: str | None,
    artifact_dir: Path | None = None,
    project_root: Path | None = None,
) -> str:
    """Read identity.md + phase.md, return concatenated content.

    Args:
        workflow_dir: e.g. workflows/project_team/
        role_name: folder name, e.g. "coordinator"
        current_phase: e.g. "specification" -> reads specification.md
        artifact_dir: Resolved absolute path bound via
            ``WorkflowEngine.set_artifact_dir`` for this run, or ``None``
            if unset. Substituted into the assembled markdown wherever
            the literal token ``${CLAUDECHIC_ARTIFACT_DIR}`` appears.
        project_root: Launched-repo root (the main agent's cwd) used to
            substitute the literal token ``${WORKFLOW_ROOT}`` in the
            assembled markdown. ``None`` substitutes the empty string
            (deliberate, visible failure mode matching ``artifact_dir``).
    """
    role_dir = workflow_dir / role_name

    identity_path = role_dir / "identity.md"
    identity = (
        identity_path.read_text(encoding="utf-8") if identity_path.is_file() else ""
    )

    phase_content = ""
    if current_phase:
        # Strip namespace prefix - qualified ID "project-team:specification"
        # -> bare "specification"
        bare_phase = (
            current_phase.split(":", 1)[1] if ":" in current_phase else current_phase
        )
        phase_path = role_dir / f"{bare_phase}.md"
        if phase_path.is_file():
            phase_content = phase_path.read_text(encoding="utf-8")

    if phase_content:
        combined = f"{identity}\n\n---\n\n{phase_content}"
    else:
        combined = identity

    combined = substitute_artifact_dir(combined, artifact_dir)
    combined = substitute_workflow_root(combined, project_root)
    return combined


def assemble_phase_prompt(
    workflow_dir: Path,
    role_name: str,
    current_phase: str | None,
    artifact_dir: Path | None = None,
    project_root: Path | None = None,
) -> str | None:
    """Get full system prompt content for an agent.

    Called at agent spawn time and by the post-compact hook.
    Returns None if no agent folder exists.

    Args:
        workflow_dir: Resolved workflow directory (the winning-tier path
            from ``LoadResult.workflows[wf_id].path``). Multi-tier
            resolution is the loader's job; this function is post-resolution.
        role_name: Agent role folder name (e.g. "coordinator").
        current_phase: Current phase ID, or None.
        artifact_dir: Resolved absolute path bound via
            ``WorkflowEngine.set_artifact_dir`` for this run, or ``None``
            if unset. Substituted into the assembled markdown wherever
            the literal token ``${CLAUDECHIC_ARTIFACT_DIR}`` appears.
        project_root: Launched-repo root used to substitute the literal
            token ``${WORKFLOW_ROOT}`` in the assembled markdown.
    """
    if workflow_dir is None or not workflow_dir.is_dir():
        return None
    result = _assemble_agent_prompt(
        workflow_dir, role_name, current_phase, artifact_dir, project_root
    )
    return result or None


# ---------------------------------------------------------------------------
# Constraints block (D3) -- markdown formatter for the per-agent
# rule + advance-check projection.
# ---------------------------------------------------------------------------


def assemble_constraints_block(
    loader: ManifestLoader | None,
    role: str,
    phase: str | None,
    *,
    engine: Any | None = None,
    active_workflow: str | None = None,
    disabled_rules: frozenset[str] | None = None,
    include_skipped: bool = False,
    compact: bool = False,
    slice: Literal["stable", "phase", None] = None,
    omit_heading: bool = False,
    suppress_advance_checks: bool = False,
) -> str:
    """Render a ``## Constraints`` markdown block for ``(role, phase)``.

    Single-source helper (SPEC F4): all constraints rendering routes
    through this function -> ``compute_digest`` -> ``_LoaderAdapter`` ->
    ``_filter_load_result``.

    Args:
        slice: ``"stable"`` keeps only rules without a ``phase:`` qualifier;
            ``"phase"`` keeps only rules whose phase matches ``phase``;
            ``None`` (default) keeps all rules. SPEC §3.2.1 keystone.
        omit_heading: When True, the ``## Constraints`` heading is not
            emitted. Composer-driven; used when the phase slice follows
            the stable slice in a single composition (SPEC §3.2.2).
        suppress_advance_checks: When True, advance-checks subsection is
            omitted regardless of whether checks exist. Used by
            ``_render_constraints_phase`` for non-coordinator roles
            (SPEC §3.2.1).
        compact: When True, render rules as a compact bullet list.
            When False (default), render as a markdown table. The
            ``mcp__chic__get_agent_info`` ``compact`` parameter drives
            this in inspector contexts; renderers pass through
            ``ctx.settings.constraints_segment.compact``.

    Composes two projections sourced from sibling leaf modules:

    - ``compute_digest`` (``claudechic.guardrails.digest``) -- role+phase
      scoped rules with annotated ``active`` / ``skip_reason`` fields.
    - ``compute_advance_checks_digest``
      (``claudechic.guardrails.checks_digest``) -- advance-checks for the
      active phase.

    Both modules ship in slot 3 of this implementation cycle. Until they
    land, this helper is callable but returns the empty string for the
    no-rules / no-checks degenerate case so the five D5 inject sites
    naturally skip injection (the dead-code guard in
    ``assemble_agent_prompt`` becomes live).

    Returns the empty string ``""`` when there are no active rules to
    list AND no advance-checks for the phase. Callers test
    ``constraints.strip()`` to decide whether to inject. The
    ``include_skipped=True`` flag (consumed by ``get_agent_info``) keeps
    the block non-empty by rendering the inactive-rule audit table.
    """
    # ----- Collect rules ----------------------------------------------------
    raw_entries: list[Any] = []
    skip_reason_used = include_skipped
    try:
        from claudechic.guardrails.digest import compute_digest  # type: ignore[import-not-found]
    except ImportError:
        compute_digest = None  # type: ignore[assignment]

    if compute_digest is not None and loader is not None:
        try:
            raw_entries = list(
                compute_digest(
                    loader,
                    active_workflow,
                    role if role else DEFAULT_ROLE,
                    phase,
                    disabled_rules or frozenset(),
                )
            )
        except Exception as e:
            logger.debug("compute_digest raised; skipping rules digest: %s", e)
            raw_entries = []

    # Slice filtering (SPEC §3.2.1). The digest entry's ``phases`` list
    # carries phase-required qualifiers; entries with an empty ``phases``
    # list are phase-agnostic (stable). The ``exclude_phases`` list is a
    # negative scope that does not change "is this a phase-required rule"
    # -- such entries are stable.
    def _has_phase_qualifier(entry: Any) -> bool:
        phases = getattr(entry, "phases", None) or []
        return bool(phases)

    if slice == "stable":
        raw_entries = [e for e in raw_entries if not _has_phase_qualifier(e)]
    elif slice == "phase":
        raw_entries = [e for e in raw_entries if _has_phase_qualifier(e)]

    rules_rows: list[str] = []
    bullet_rows: list[str] = []
    n_active = 0
    for entry in raw_entries:
        active = bool(getattr(entry, "active", True))
        if active:
            n_active += 1
        if not include_skipped and not active:
            continue
        iid = getattr(entry, "id", "") or ""
        ns = getattr(entry, "namespace", "") or ""
        qualified = f"{ns}:{iid}" if ns and ":" not in iid else iid
        enforcement = getattr(entry, "enforcement", "") or ""
        trigger = getattr(entry, "trigger", "") or ""
        message = getattr(entry, "message", "") or ""
        if compact:
            line = f"- {qualified} [{enforcement}] {trigger}: {message}"
            if skip_reason_used:
                reason = getattr(entry, "skip_reason", "") or ""
                if reason:
                    line += f" (skip: {reason})"
            bullet_rows.append(line)
        else:
            row = f"| {qualified} | {enforcement} | {trigger} | {message} |"
            if skip_reason_used:
                reason = getattr(entry, "skip_reason", "") or ""
                row = (
                    f"| {qualified} | {enforcement} | {trigger} | "
                    f"{message} | {reason} |"
                )
            rules_rows.append(row)

    has_rules = bool(rules_rows or bullet_rows)

    # ----- Collect advance-checks -------------------------------------------
    # The stable slice never carries advance-checks (advance-checks are
    # phase-scoped by definition). Coordinator-only enforcement is the
    # caller's responsibility via ``suppress_advance_checks``.
    check_rows: list[str] = []
    if not suppress_advance_checks and slice != "stable":
        try:
            from claudechic.guardrails.checks_digest import (  # type: ignore[import-not-found]
                compute_advance_checks_digest,
            )
        except ImportError:
            compute_advance_checks_digest = None  # type: ignore[assignment]

        if compute_advance_checks_digest is not None and engine is not None:
            try:
                check_entries = compute_advance_checks_digest(engine, phase)
            except Exception as e:
                logger.debug(
                    "compute_advance_checks_digest raised; skipping advance-checks: %s",
                    e,
                )
                check_entries = []
            for ce in check_entries:
                cid = getattr(ce, "id", "") or ""
                cmd = getattr(ce, "command", None) or getattr(ce, "summary", "") or ""
                manual = bool(getattr(ce, "manual", False))
                check_rows.append(
                    f"- {cid} -- {cmd} (manual? {'yes' if manual else 'no'})"
                )

    # Empty digest short-circuit: no rules to surface AND no advance-checks
    # to list -> empty string. Composer drops empty segments cleanly
    # (SPEC F9: no 138-char placeholder).
    if not has_rules and not check_rows:
        return ""

    # ----- Assemble markdown ------------------------------------------------
    sections: list[str] = []
    if not omit_heading:
        sections.append("## Constraints")
        sections.append("")

    sections.append(f"### Rules ({n_active} active)")
    sections.append("")
    if compact:
        if bullet_rows:
            sections.extend(bullet_rows)
        else:
            sections.append("_No rules apply to this role + phase._")
    else:
        if rules_rows:
            if skip_reason_used:
                sections.append("| id | enforcement | trigger | message | skip_reason |")
                sections.append("|----|-------------|---------|---------|-------------|")
            else:
                sections.append("| id | enforcement | trigger | message |")
                sections.append("|----|-------------|---------|---------|")
            sections.extend(rules_rows)
        else:
            sections.append("_No rules apply to this role + phase._")
    sections.append("")

    # Advance-checks subsection: dropped entirely (heading + body) when
    # the slice is "stable" OR when ``suppress_advance_checks`` is True.
    # The latter matches the docstring contract: non-coordinator roles
    # never see advance-checks, even the "_No advance checks_" fallback.
    if slice != "stable" and not suppress_advance_checks:
        sections.append(f"### Advance checks ({phase or '-'})")
        sections.append("")
        if check_rows:
            sections.extend(check_rows)
        else:
            sections.append("_No advance checks for this phase._")

    return "\n".join(sections).rstrip() + "\n"


def assemble_agent_prompt(
    role: str,
    phase: str | None,
    loader: ManifestLoader | None,
    *,
    workflow_dir: Path | None = None,
    artifact_dir: Path | None = None,
    project_root: Path | None = None,
    engine: Any | None = None,
    active_workflow: str | None = None,
    disabled_rules: frozenset[str] | None = None,
    time: InjectionSite | None = None,
    settings: GateSettings | None = None,
    manifest: GateManifest | None = None,
    environment_tokens: dict[str, str] | None = None,
    peer_agents: dict[str, str] | None = None,
) -> str | None:
    """Single composition point for every prompt-injection site.

    Thin orchestrator (SPEC §2): for each ``place`` in ``_SEGMENT_ORDER``,
    calls ``gate(time, place, role, phase, settings, manifest)``; if the
    gate returns True, invokes the corresponding renderer; composes the
    non-empty outputs.

    The four official inject sites pass ``time`` explicitly:

        T1 spawn            -> "spawn"
        T2 activation       -> "activation"
        T3 phase-advance    -> "phase-advance"  (broadcast loop)
        T4 post-compact     -> "post-compact"

    When ``time is None`` the gate is degenerate (every cell True) so
    behavior matches the prior monolithic assembly. Test paths and the
    coordinator's phase-advance update (NOT an injection site per SPEC
    §3.1) rely on this.

    Composition rules (SPEC §3.2 / §3.2.2):
    - identity + phase form the head block joined by ``"\\n\\n---\\n\\n"``.
    - constraints_stable + constraints_phase render as ONE
      ``## Constraints`` block when both emit (stable owns the heading;
      phase appended headless).
    - environment appends with ``"\\n\\n"`` after the constraints block.
    - Empty segments are dropped.

    Returns None when every segment is empty (parity with the prior
    semantics for fully unconfigured agents).
    """
    settings_eff = settings if settings is not None else GateSettings()
    if manifest is not None:
        manifest_eff = manifest
    else:
        # Build an ad-hoc GateManifest scanned from ``workflow_dir`` for
        # standing-by predicate inputs (SPEC §3.8). Per the user-approved
        # SPEC change, the per-workflow environment opt-in is removed;
        # the fallback no longer needs to consult the loader for an
        # ``environment_segment_enabled`` flag.
        manifest_eff = build_gate_manifest(
            loader=loader,
            active_workflow=active_workflow,
            workflow_dir=workflow_dir,
        )

    ctx = RenderContext(
        role=role,
        phase=phase,
        workflow_dir=workflow_dir,
        artifact_dir=artifact_dir,
        project_root=project_root,
        loader=loader,
        engine=engine,
        active_workflow=active_workflow,
        disabled_rules=disabled_rules,
        settings=settings_eff,
        manifest=manifest_eff,
        time=time,
        environment_tokens=environment_tokens or {},
        peer_agents=peer_agents or {},
    )

    rendered: dict[str, str] = {}
    constraints_stable_emitted = False

    for place in _SEGMENT_ORDER:
        # SPEC §3 + skeptic fix: ``time=None`` is the explicit ungated
        # path (test fixtures, coordinator's advance_phase synchronous
        # return). Every renderer runs without consulting the gate.
        # ``time`` set to one of the four ``InjectionSite`` values goes
        # through the strict gate; ``time=None`` here does NOT silently
        # bypass user settings (the gate would raise ValueError if we
        # called it with None).
        if time is not None:
            if not gate(time, place, role, phase, settings_eff, manifest_eff):
                rendered[place] = ""
                continue
        if place == "identity":
            rendered[place] = _render_identity(ctx)
        elif place == "phase":
            rendered[place] = _render_phase(ctx)
        elif place == "constraints_stable":
            text = _render_constraints_stable(ctx)
            rendered[place] = text
            if text.strip():
                constraints_stable_emitted = True
        elif place == "constraints_phase":
            rendered[place] = _render_constraints_phase(
                ctx, omit_heading=constraints_stable_emitted
            )
        elif place == "environment":
            # Even on the ungated path, the environment segment must
            # respect manifest/user opt-in -- it is workflow-context-
            # dependent and would otherwise leak into baseline / no-
            # workflow assemblies.
            if time is None and not effective_environment_enabled(
                settings_eff, manifest_eff
            ):
                rendered[place] = ""
            else:
                rendered[place] = _render_environment(ctx)

    identity_text = rendered.get("identity", "")
    phase_text = rendered.get("phase", "")
    cs_text = rendered.get("constraints_stable", "")
    cp_text = rendered.get("constraints_phase", "")
    env_text = rendered.get("environment", "")

    head_parts: list[str] = []
    if identity_text.strip():
        head_parts.append(identity_text.rstrip())
    if phase_text.strip():
        head_parts.append(phase_text.rstrip())
    head = "\n\n---\n\n".join(head_parts)

    tail_parts: list[str] = []
    if cs_text.strip() and cp_text.strip():
        tail_parts.append(f"{cs_text.rstrip()}\n\n{cp_text.rstrip()}")
    elif cs_text.strip():
        tail_parts.append(cs_text.rstrip())
    elif cp_text.strip():
        tail_parts.append(cp_text.rstrip())
    if env_text.strip():
        tail_parts.append(env_text.rstrip())

    composed: list[str] = []
    if head:
        composed.append(head)
    composed.extend(tail_parts)

    if not composed:
        return None
    return "\n\n".join(composed)


# ---------------------------------------------------------------------------
# Post-compact context injection via SessionStart hook with source="compact"
#
# Per the Claude Code hooks docs (https://code.claude.com/docs/en/hooks):
# ``PostCompact`` is side-effect-only and CANNOT inject context into the
# agent's post-compact session. The correct hook for re-injecting the
# constraints + identity + phase block after ``/compact`` is
# ``SessionStart`` filtered by ``source: "compact"`` -- it fires after
# compaction AND supports ``additionalContext`` for context injection
# (same shape as the spawn / activation / phase-advance inject sites).
# ---------------------------------------------------------------------------


def create_session_start_compact_hook(
    *,
    get_engine: Any,
    get_agent_role: Any,
    get_workflow_dir: Any,
    get_disabled_rules: Any | None = None,
    get_settings: Any | None = None,
    get_peer_agents: Any | None = None,
) -> dict[str, Any]:
    """Create a ``SessionStart`` hook that re-injects context after ``/compact``.

    Registers under the ``SessionStart`` hook event with a
    ``matcher="compact"`` source filter, so the hook fires only on the
    post-``/compact`` session-start path (not on ``startup`` or
    ``resume``).

    All inputs are resolved at fire-time via callables. The hook is
    typically registered on the SDK options at agent connect time --
    BEFORE any workflow activation -- so capture-time engine / role /
    workflow_dir would be stale or ``None``. The resolvers re-read the
    live caller-side state (``ChatApp._workflow_engine``,
    ``Agent.agent_type``, ``LoadResult.get_workflow``) at the moment
    /compact fires.

    When fire-time resolution yields ``engine is None`` (no workflow
    active at /compact time), or ``role`` is empty, or ``workflow_dir``
    is ``None``, the closure returns ``{}`` -- the agent receives only
    the SDK's standard post-compact summary, no extra context.

    Args:
        get_engine: Callable returning the current ``WorkflowEngine``
            (or ``None`` if no workflow active).
        get_agent_role: Callable returning the current agent role
            (e.g. the coordinator's ``main_role`` after activation
            promotes ``agent_type``).
        get_workflow_dir: Callable returning the resolved workflow
            directory for the current workflow (or ``None`` when no
            workflow is active).
        get_disabled_rules: Optional callable returning merged
            ``frozenset[str]`` of disabled rule ids (user + project
            tier).
        get_settings: Optional callable returning a ``GateSettings``
            instance.
        get_peer_agents: Optional callable returning
            ``{role -> registered_name}`` for currently spawned typed
            peer agents.

    Returns:
        Hook configuration dict for SDK hook registration.
    """

    async def reinject_phase_context(
        hook_input: dict, match: str | None, ctx: object
    ) -> dict:
        """Re-inject phase context after /compact (fire-time resolution)."""
        try:
            engine_eff = get_engine()
        except Exception as e:
            logger.debug("session-start (compact): get_engine raised: %s", e)
            return {}
        if engine_eff is None:
            return {}

        try:
            role_eff = get_agent_role() or ""
        except Exception as e:
            logger.debug("session-start (compact): get_agent_role raised: %s", e)
            return {}
        if not role_eff:
            return {}

        try:
            wf_dir_eff = get_workflow_dir()
        except Exception as e:
            logger.debug(
                "session-start (compact): get_workflow_dir raised: %s", e
            )
            return {}
        if wf_dir_eff is None:
            return {}

        current_phase = engine_eff.get_current_phase()
        artifact_dir = engine_eff.get_artifact_dir()
        project_root = getattr(engine_eff, "project_root", None)
        loader = getattr(engine_eff, "loader", None)
        wf_id = getattr(engine_eff, "workflow_id", None)

        # Resolve disabled_rules + settings + peer_agents at hook-fire
        # time so config edits / spawned-agent changes during the
        # session take effect on the next /compact (SPEC F5 + §3.7/§3.11).
        disabled_rules: frozenset[str] | None = None
        if get_disabled_rules is not None:
            try:
                disabled_rules = get_disabled_rules()
            except Exception as e:
                logger.debug(
                    "session-start (compact): get_disabled_rules raised: %s", e
                )
        settings: GateSettings | None = None
        if get_settings is not None:
            try:
                settings = get_settings()
            except Exception as e:
                logger.debug(
                    "session-start (compact): get_settings raised: %s", e
                )
        peer_agents: dict[str, str] | None = None
        if get_peer_agents is not None:
            try:
                peer_agents = get_peer_agents()
            except Exception as e:
                logger.debug(
                    "session-start (compact): get_peer_agents raised: %s", e
                )

        prompt = assemble_agent_prompt(
            role_eff,
            current_phase,
            loader,
            workflow_dir=wf_dir_eff,
            artifact_dir=artifact_dir,
            project_root=project_root,
            engine=engine_eff,
            active_workflow=wf_id,
            disabled_rules=disabled_rules,
            settings=settings,
            time="post-compact",
            peer_agents=peer_agents,
        )
        if prompt:
            logger.debug(
                "post-compact: re-injected phase context for %s (phase: %s)",
                role_eff,
                current_phase,
            )
            # Return shape: ``{"hookSpecificOutput": {"hookEventName":
            # "SessionStart", "additionalContext": ...}}``. The Claude
            # Code hook docs spell out that ``PostCompact`` is
            # side-effect-only -- it cannot inject context. ``SessionStart``
            # with ``source: "compact"`` is the documented post-compact
            # context-injection path; its ``hookSpecificOutput`` shape
            # is identical to PostToolUse / UserPromptSubmit /
            # Notification / SubagentStart (``additionalContext`` is the
            # carrier).
            return {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": prompt,
                },
            }
        return {}

    # Register under ``SessionStart`` with ``matcher="compact"`` so the
    # closure fires only on the post-/compact session-start path. The
    # matcher field on ``HookMatcher`` is a string filter -- for
    # SessionStart, it filters by the source value (``"startup"`` /
    # ``"resume"`` / ``"compact"``). Per Claude Code hooks docs, this is
    # the documented post-compact context-injection mechanism.
    return {
        "SessionStart": [
            HookMatcher(matcher="compact", hooks=[reinject_phase_context]),
        ],
    }
