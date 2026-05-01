"""Manifest loader — three-tier walker with override-by-id resolution.

Loads YAML manifests from up to three tier roots (package, user, project)
and resolves cross-tier conflicts by id with full-record replacement
(highest-priority tier wins). Within-tier id collisions surface as
``LoadError(source="validation")``; cross-tier collisions are silent
(the override mechanism).

A single generic resolver (``_resolve_by_id``) implements the law for
all per-id content categories (rules, injections, hints, checks). Phases
follow the workflow's full-record override; top-level rules / injections /
hints / checks accumulate independently of workflow tier.

The loader is GENERIC — it doesn't know section semantics. It dispatches
to typed parsers via the ``ManifestSection`` protocol.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Protocol, TypeVar

import yaml

from claudechic.workflows.phases import Phase

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tier model
# ---------------------------------------------------------------------------

Tier = Literal["package", "user", "project"]
"""Tier identity. Three values, ascending priority: package < user < project."""

# Iteration order for highest-priority-wins resolution.
# Index 0 is highest priority; index -1 is lowest.
_TIER_ORDER: tuple[Tier, ...] = ("project", "user", "package")
_VALID_TIER_PREFIXES: frozenset[str] = frozenset({"package", "user", "project"})


@dataclass(frozen=True)
class TierRoots:
    """Filesystem roots for the three tiers.

    The package tier is required (ships with the install). User and project
    tiers MAY be ``None`` (the corresponding tier contributes zero content).
    """

    package: Path
    user: Path | None = None
    project: Path | None = None

    def get(self, tier: Tier) -> Path | None:
        """Return the root for a tier, or ``None`` if absent."""
        if tier == "package":
            return self.package
        if tier == "user":
            return self.user
        return self.project

    def populated_tiers(self) -> tuple[Tier, ...]:
        """Return tiers (in priority order) whose root is set."""
        return tuple(t for t in _TIER_ORDER if self.get(t) is not None)


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------

T_co = TypeVar("T_co", covariant=True)


class ManifestSection(Protocol[T_co]):
    """Protocol for typed manifest section parsers.

    Each section type (rules, checks, hints, phases) implements this.
    The loader dispatches raw YAML sections to the appropriate parser
    without knowing section semantics. Adding a new section type =
    implementing this protocol + registering the key.
    """

    @property
    def section_key(self) -> str:
        """YAML key this parser handles (e.g. 'rules', 'checks')."""
        ...

    def parse(
        self,
        raw: list[dict[str, Any]],
        *,
        namespace: str,
        source_path: str,
        tier: Tier = "package",
    ) -> list[T_co]:
        """Parse raw YAML section into typed objects.

        Args:
            raw: List of dicts from yaml.safe_load for this section key.
            namespace: 'global' for global/*.yaml, workflow_id for workflow manifests.
            source_path: Path to manifest file (error messages only).
            tier: Tier the manifest came from; stamped onto records for provenance.

        Returns:
            List of parsed typed objects. Items that fail validation are
            skipped (logged, not raised) — fail open per-item.

        Raises:
            Nothing. Individual failures logged and skipped.
        """
        ...


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LoadError:
    """A non-fatal error encountered during loading."""

    source: str  # file path or "discovery" or "validation"
    message: str
    section: str | None = None
    item_id: str | None = None


@dataclass(frozen=True)
class WorkflowData:
    """Per-workflow parsed data."""

    workflow_id: str
    path: Path
    main_role: str | None = None  # Role folder for the main agent (e.g. "learner")
    has_errors: bool = False  # True if any parse error in this workflow
    # Tier where the winning workflow directory resides.
    tier: Tier = "package"
    # Every tier where this workflow_id is defined (winning tier always included).
    defined_at: frozenset[Tier] = field(default_factory=frozenset)


@dataclass(frozen=True)
class LoadResult:
    """Complete result of loading all manifests."""

    rules: list[Any] = field(default_factory=list)
    injections: list[Any] = field(default_factory=list)
    checks: list[Any] = field(default_factory=list)
    hints: list[Any] = field(default_factory=list)
    phases: list[Phase] = field(default_factory=list)
    errors: list[LoadError] = field(default_factory=list)
    workflows: dict[str, WorkflowData] = field(default_factory=dict)
    # Map of workflow_id -> set of tiers where the id is defined (winning
    # tier always included). UI surfaces consume this for "defined at" badges
    # in the workflow picker; the disable filter consults it for unknown-id
    # detection. ``dict[str, frozenset[Tier]]``.
    workflow_provenance: dict[str, frozenset[Any]] = field(default_factory=dict)
    # Map of item_id (rule / injection / hint / check) -> set of tiers where
    # the id is defined. Used by Settings UI to show "defined at" labels and
    # by the disable filter for unknown-id detection.
    # ``dict[str, frozenset[Tier]]``.
    item_provenance: dict[str, frozenset[Any]] = field(default_factory=dict)

    def get_workflow(self, wf_id: str) -> WorkflowData | None:
        """Look up per-workflow data by workflow_id."""
        return self.workflows.get(wf_id)


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


def discover_manifests_single_tier(global_dir: Path, workflows_dir: Path) -> list[Path]:
    """Discover all manifest files in one tier's ``global/`` and ``workflows/``.

    Returns paths in load order:
    1. global/*.yaml (all YAML files, sorted alphabetically)
    2. workflows/*/<workflow_id>.yaml (sorted alphabetically)

    Global: all .yaml files in global/ directory.
    Workflow: manifest filename must match parent directory name.
    Example: workflows/project_team/project_team.yaml OK
             workflows/project_team/other.yaml ignored
    Hidden directories (.name) and hidden files skipped.
    No recursive scanning — exactly one level deep.
    """
    manifests: list[Path] = []

    # 1. Global manifests — all .yaml files in global/
    if global_dir.is_dir():
        for child in sorted(global_dir.iterdir()):
            if (
                child.is_file()
                and child.suffix == ".yaml"
                and not child.name.startswith(".")
            ):
                manifests.append(child)

    # 2. Workflow manifests — workflows/*/name.yaml
    if workflows_dir.is_dir():
        for child in sorted(workflows_dir.iterdir()):
            if child.is_dir() and not child.name.startswith("."):
                manifest = child / f"{child.name}.yaml"
                if manifest.is_file():
                    manifests.append(manifest)

    return manifests


def walk_tiers(roots: TierRoots) -> list[tuple[Tier, Path, Path]]:
    """Yield ``(tier, manifest_path, tier_root)`` for every manifest across tiers.

    Iterates package -> user -> project, calling
    :func:`discover_manifests_single_tier` per tier. The tier root is
    returned alongside each manifest path so callers can compute
    relative paths (e.g., for partial-override detection).
    """
    out: list[tuple[Tier, Path, Path]] = []
    for tier in _TIER_ORDER[::-1]:  # iterate package -> user -> project for stability
        root = roots.get(tier)
        if root is None:
            continue
        try:
            paths = discover_manifests_single_tier(root / "global", root / "workflows")
        except OSError as e:
            logger.warning(
                "tier %s root unreadable at %s: %s — skipping", tier, root, e
            )
            continue
        for p in paths:
            out.append((tier, p, root))
    return out


# ---------------------------------------------------------------------------
# Per-category resolution
# ---------------------------------------------------------------------------


def _resolve_by_id(
    items_by_tier: dict[Tier, list[Any]],
    *,
    section_key: str,
    id_of: Callable[[Any], str | None],
) -> tuple[list[Any], dict[str, frozenset[Tier]], list[LoadError]]:
    """Resolve per-id collisions across tiers — full-record override.

    Iterates tiers in descending priority (project -> user -> package).
    For each tier, the first record per id is kept; later same-id records
    in the same tier emit a within-tier-duplicate ``LoadError`` and are
    dropped. A record's id wins resolution at the highest tier it appears
    in; lower-tier records of the same id are silently replaced (cross-tier
    override is not an error).

    Args:
        items_by_tier: ``{tier: [parsed_records]}`` from each tier's parsers.
        section_key: Section name for ``LoadError.section`` (``"rules"`` etc).
        id_of: Callable returning the record's identity unit (e.g. ``Rule.id``).

    Returns:
        ``(resolved_items, provenance, errors)`` where:
        - ``resolved_items``: flat list of records that survived resolution.
        - ``provenance``: ``{id: frozenset(tiers_where_defined)}`` — every
          tier the id was seen in (winning + losing).
        - ``errors``: within-tier duplicate ``LoadError`` records.
    """
    errors: list[LoadError] = []
    resolved: dict[str, Any] = {}
    provenance: dict[str, set[Tier]] = {}

    for tier in _TIER_ORDER:  # project, user, package — highest priority first
        bucket = items_by_tier.get(tier, [])
        seen_in_tier: dict[str, Any] = {}
        for item in bucket:
            iid = id_of(item)
            if iid is None:
                continue
            provenance.setdefault(iid, set()).add(tier)
            if iid in seen_in_tier:
                # within-tier duplicate — first occurrence keeps; later drops.
                errors.append(
                    LoadError(
                        source="validation",
                        section=section_key,
                        item_id=iid,
                        message=(
                            f"duplicate id within tier {tier}; later occurrence dropped"
                        ),
                    )
                )
                continue
            seen_in_tier[iid] = item
            # cross-tier override: first tier (highest priority) keeps the slot.
            resolved.setdefault(iid, item)

    out_items = list(resolved.values())
    out_prov = {iid: frozenset(tiers) for iid, tiers in provenance.items()}
    return out_items, out_prov, errors


# ---------------------------------------------------------------------------
# Workflow resolution + partial-override detection
# ---------------------------------------------------------------------------


def _list_workflow_files(workflow_dir: Path) -> set[str]:
    """Return relative-path strings for every regular non-hidden file under
    a workflow dir.

    Filter: ``is_file()`` AND not ``name.startswith(".")``. Naive
    ``rglob("*")`` would include directory entries and hidden files,
    which would break tier comparison.
    """
    if not workflow_dir.is_dir():
        return set()
    out: set[str] = set()
    for p in workflow_dir.rglob("*"):
        if not p.is_file():
            continue
        # Exclude paths containing any hidden component (basename or ancestor).
        try:
            rel = p.relative_to(workflow_dir)
        except ValueError:
            continue
        parts = rel.parts
        if any(part.startswith(".") for part in parts):
            continue
        out.add(rel.as_posix())
    return out


def _scan_tier_workflows(roots: TierRoots) -> dict[Tier, dict[str, Path]]:
    """Return ``{tier: {workflow_id: workflow_dir_path}}`` for every tier.

    The workflow_id is read from the manifest YAML if present, else the
    parent directory name.
    """
    out: dict[Tier, dict[str, Path]] = {}
    for tier in _TIER_ORDER[::-1]:
        root = roots.get(tier)
        if root is None:
            continue
        workflows_dir = root / "workflows"
        if not workflows_dir.is_dir():
            continue
        bucket: dict[str, Path] = {}
        for child in sorted(workflows_dir.iterdir()):
            if not child.is_dir() or child.name.startswith("."):
                continue
            manifest = child / f"{child.name}.yaml"
            wf_id = child.name
            main_role: str | None = None
            if manifest.is_file():
                try:
                    with manifest.open(encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                    if isinstance(data, dict):
                        wf_id = str(data.get("workflow_id", child.name))
                        mr = data.get("main_role")
                        if isinstance(mr, str):
                            main_role = mr
                except (OSError, yaml.YAMLError):
                    pass
            # Stash main_role on the dict via a side channel — return only path here.
            # (Loader pulls main_role separately when building WorkflowData.)
            bucket[wf_id] = child
            # also stash main role on the path object via a parallel dict?
            # Actually, simpler: reread the manifest where we need main_role.
            del main_role  # silence linter
        out[tier] = bucket
    return out


def _resolve_workflows(
    roots: TierRoots,
    disabled_by_tier: dict[Tier, frozenset[str]] | None = None,
) -> tuple[
    dict[str, tuple[Tier, Path]],
    dict[str, frozenset[Tier]],
    list[LoadError],
]:
    """Resolve workflow ids across tiers with partial-override detection.

    For each workflow id, walk highest -> lowest priority tier. If a higher
    tier's directory is missing files the next-lower tier's directory has,
    treat the higher tier's contribution as a *partial override*: emit a
    ``LoadError`` and fall through to the next-lower tier (which itself may
    partial-override below it). Files the higher tier *adds* are permitted.

    Tier-targeted disables (from ``disabled_by_tier``) treat the named
    tier's record of that id as if it didn't exist before resolution begins.

    Returns:
        ``(resolved, provenance, errors)`` where:
        - ``resolved``: ``{wf_id: (winning_tier, workflow_dir)}``
        - ``provenance``: ``{wf_id: frozenset(tiers_where_defined)}``
          (excludes tiers filtered by ``disabled_by_tier``)
        - ``errors``: partial-override ``LoadError`` records
    """
    disabled_by_tier = disabled_by_tier or {}
    errors: list[LoadError] = []
    by_tier = _scan_tier_workflows(roots)

    # Apply tier-targeted disables before resolution.
    for tier, ids in disabled_by_tier.items():
        if tier not in by_tier:
            continue
        for iid in list(by_tier[tier].keys()):
            if iid in ids:
                del by_tier[tier][iid]

    all_ids: set[str] = set()
    for bucket in by_tier.values():
        all_ids.update(bucket.keys())

    resolved: dict[str, tuple[Tier, Path]] = {}
    provenance: dict[str, set[Tier]] = {iid: set() for iid in all_ids}
    for tier, bucket in by_tier.items():
        for iid in bucket:
            provenance[iid].add(tier)

    for wf_id in sorted(all_ids):
        # Tiers that contain this workflow id, in priority order (high -> low).
        candidate_tiers: list[Tier] = [
            t for t in _TIER_ORDER if wf_id in by_tier.get(t, {})
        ]
        if not candidate_tiers:
            continue

        # Step A: detect partial overrides for EVERY (higher, lower) pair
        # — emit a LoadError per partial; mark tiers that are partial vs
        # any lower tier so resolution skips them.
        is_partial: dict[Tier, bool] = {t: False for t in candidate_tiers}
        for hi_idx, hi_tier in enumerate(candidate_tiers):
            higher_path = by_tier[hi_tier][wf_id]
            higher_files = _list_workflow_files(higher_path)
            for lo_tier in candidate_tiers[hi_idx + 1 :]:
                lower_path = by_tier[lo_tier][wf_id]
                lower_files = _list_workflow_files(lower_path)
                missing = lower_files - higher_files
                if missing:
                    missing_list = ", ".join(f"`{m}`" for m in sorted(missing))
                    errors.append(
                        LoadError(
                            source="validation",
                            section="workflow",
                            item_id=wf_id,
                            message=(
                                f"Partial workflow override at "
                                f"`{higher_path}`: missing {missing_list}. "
                                f"Workflow overrides require the full file "
                                f"set. Copy the missing files from the lower "
                                f"level (package or user), or remove the "
                                f"partial override at `{higher_path}`."
                            ),
                        )
                    )
                    is_partial[hi_tier] = True

        # Step B: walk highest-to-lowest and pick the first non-partial tier.
        winner: tuple[Tier, Path] | None = None
        for tier in candidate_tiers:
            if is_partial[tier]:
                continue
            winner = (tier, by_tier[tier][wf_id])
            break
        if winner is not None:
            resolved[wf_id] = winner

    out_prov = {iid: frozenset(tiers) for iid, tiers in provenance.items() if tiers}
    return resolved, out_prov, errors


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


class ManifestLoader:
    """Three-tier manifest loader. Single code path; callers filter."""

    def __init__(
        self,
        tier_roots_or_global_dir: TierRoots | Path | None = None,
        workflows_dir: Path | None = None,
        *,
        tier_roots: TierRoots | None = None,
        global_dir: Path | None = None,
    ) -> None:
        """Construct a loader against the given tier roots.

        Preferred signature: ``ManifestLoader(tier_roots=...)`` (kwarg).
        Backwards-compat shims:
        - ``ManifestLoader(global_dir, workflows_dir)`` — positional, legacy.
        - ``ManifestLoader(global_dir=..., workflows_dir=...)`` — kwargs, legacy.

        Legacy shapes synthesize a single-tier ``TierRoots`` whose ``package``
        root is the parent of either provided dir (assumes the layout
        ``<root>/global/`` + ``<root>/workflows/``).
        """
        # Disambiguate the first positional arg.
        if isinstance(tier_roots_or_global_dir, TierRoots):
            tier_roots = (
                tier_roots if tier_roots is not None else tier_roots_or_global_dir
            )
        elif isinstance(tier_roots_or_global_dir, Path):
            global_dir = (
                global_dir if global_dir is not None else tier_roots_or_global_dir
            )

        if tier_roots is None:
            if global_dir is None and workflows_dir is None:
                raise ValueError(
                    "ManifestLoader requires either tier_roots or "
                    "(global_dir, workflows_dir)"
                )
            pkg_root = (
                global_dir.parent if global_dir is not None else workflows_dir.parent  # type: ignore[union-attr]
            )
            tier_roots = TierRoots(package=pkg_root, user=None, project=None)
        self._tier_roots = tier_roots
        self._parsers: dict[str, ManifestSection[Any]] = {}

    def register(self, parser: ManifestSection[Any]) -> None:
        """Register a section parser by its section_key."""
        self._parsers[parser.section_key] = parser

    def load(
        self,
        *,
        disabled_workflows_by_tier: dict[Tier, frozenset[str]] | None = None,
        disabled_ids_by_tier: dict[Tier, frozenset[str]] | None = None,
    ) -> LoadResult:
        """Load all manifests across tiers and return unified result.

        Args:
            disabled_workflows_by_tier: Per-tier sets of workflow ids to
                treat as if absent at that tier (tier-targeted disable).
                Resolution proceeds normally; the next-highest tier with
                the same id wins, or the id falls out if no other tier
                defines it.
            disabled_ids_by_tier: Same semantics for rule / injection /
                hint / check ids.

        Error handling:
        - Package tier root missing or unreadable: fail-closed
          (``LoadError(source="discovery")``; content lists empty).
        - User / project tier unreadable: that tier is skipped silently;
          other tiers still load.
        - Individual manifest YAML parse error: ``LoadError(source=path)``;
          that manifest skipped.
        - Per-record validation error: logged warning; record skipped.
        - Within-tier duplicate id: ``LoadError(source="validation")``;
          first occurrence kept.
        - Cross-tier duplicate id: no error; override applied.
        - Partial override at higher tier: ``LoadError`` per §3.4;
          higher tier's contribution dropped; fall-through to lower tier.
        """
        disabled_workflows_by_tier = disabled_workflows_by_tier or {}
        disabled_ids_by_tier = disabled_ids_by_tier or {}

        errors: list[LoadError] = []

        # Step 1: Verify package tier root is present and discoverable.
        pkg_root = self._tier_roots.package
        if not pkg_root.is_dir():
            return LoadResult(
                errors=[
                    LoadError(
                        source="discovery",
                        message=(
                            f"package tier unreadable: {pkg_root} (not a directory)"
                        ),
                    )
                ]
            )
        # _discover is a seam for tests / monitoring to simulate unreadable
        # roots; it raises OSError on failure and the loader fail-closes.
        try:
            self._discover()
        except OSError as e:
            return LoadResult(
                errors=[
                    LoadError(
                        source="discovery",
                        message=f"package tier unreadable: {e}",
                    )
                ]
            )

        # Step 2: Walk every tier; parse each manifest under each tier.
        per_tier_collected: dict[str, dict[Tier, list[Any]]] = {
            k: {t: [] for t in _TIER_ORDER} for k in self._parsers
        }
        # Per-tier per-workflow seen ids (for has_errors flagging).
        workflow_paths_seen: dict[Tier, dict[str, tuple[Path, str | None]]] = {
            t: {} for t in _TIER_ORDER
        }

        for tier, path, tier_root in walk_tiers(self._tier_roots):
            try:
                with path.open(encoding="utf-8") as f:
                    data = yaml.safe_load(f)
            except (OSError, yaml.YAMLError) as e:
                errors.append(LoadError(source=str(path), message=str(e)))
                if not _is_global_path(path, tier_root):
                    wf_id = path.parent.name
                    workflow_paths_seen[tier].setdefault(wf_id, (path.parent, None))
                continue

            if _is_global_path(path, tier_root):
                namespace = "global"
            else:
                if not isinstance(data, dict):
                    errors.append(
                        LoadError(source=str(path), message="not a YAML mapping")
                    )
                    continue
                namespace = str(data.get("workflow_id", path.parent.name))

            # Global files: bare list -> infer section key from filename stem.
            if isinstance(data, list) and _is_global_path(path, tier_root):
                key = path.stem
                parser = self._parsers.get(key)
                if parser is None:
                    errors.append(
                        LoadError(
                            source=str(path),
                            message=(
                                f"No parser registered for '{key}' "
                                "(inferred from filename)"
                            ),
                        )
                    )
                else:
                    try:
                        parsed = parser.parse(
                            data,
                            namespace=namespace,
                            source_path=str(path),
                            tier=tier,
                        )
                        per_tier_collected.setdefault(
                            key, {t: [] for t in _TIER_ORDER}
                        )[tier].extend(parsed)
                    except Exception as e:
                        errors.append(
                            LoadError(
                                source=str(path),
                                section=key,
                                message=f"parser error: {e}",
                            )
                        )
                continue

            if not isinstance(data, dict):
                errors.append(LoadError(source=str(path), message="not a YAML mapping"))
                continue

            # Track workflow data (manifest populated after all parsing).
            if not _is_global_path(path, tier_root):
                wf_id = data.get("workflow_id", path.parent.name)
                main_role = data.get("main_role")
                if not isinstance(main_role, str):
                    main_role = None
                # ``DEFAULT_ROLE`` ("default") is the reserved sentinel for
                # agents with no workflow-specific role wiring. A workflow
                # cannot use it as ``main_role`` -- doing so would prevent
                # the main agent from being promoted out of the no-role
                # state on activation. Match case-insensitively and ignore
                # surrounding whitespace so YAML quirks (``Default``,
                # ``DEFAULT``, trailing newlines from quoted scalars) are
                # all caught. Imported lazily to avoid a workflows -> agent
                # import edge in the leaf-discipline graph.
                from claudechic.agent import DEFAULT_ROLE

                if main_role is not None and main_role.strip().lower() == DEFAULT_ROLE:
                    errors.append(
                        LoadError(
                            source=str(path),
                            section="main_role",
                            message=(
                                f"main_role cannot be '{DEFAULT_ROLE}' -- "
                                "that name is reserved for the no-role sentinel."
                            ),
                        )
                    )
                    main_role = None
                workflow_paths_seen[tier].setdefault(wf_id, (path.parent, main_role))

            # Dict-based files: dispatch by section keys.
            for key, parser in self._parsers.items():
                section = data.get(key)
                if section is None:
                    continue
                if not isinstance(section, list):
                    errors.append(
                        LoadError(
                            source=str(path),
                            section=key,
                            message=f"'{key}' must be a list",
                        )
                    )
                    continue
                try:
                    parsed = parser.parse(
                        section,
                        namespace=namespace,
                        source_path=str(path),
                        tier=tier,
                    )
                    per_tier_collected.setdefault(key, {t: [] for t in _TIER_ORDER})[
                        tier
                    ].extend(parsed)
                except Exception as e:
                    errors.append(
                        LoadError(
                            source=str(path),
                            section=key,
                            message=f"parser error: {e}",
                        )
                    )

        # Step 2b: Extract phase-nested hints (after all manifests parsed).
        for tier, phases in per_tier_collected.get("phases", {}).items():
            for phase in phases:
                if hasattr(phase, "hints") and phase.hints:
                    per_tier_collected.setdefault(
                        "hints", {t: [] for t in _TIER_ORDER}
                    )[tier].extend(phase.hints)

        # Step 3: Resolve workflows (with partial-override detection +
        # tier-targeted disable filter).
        resolved_wfs, wf_prov, wf_errs = _resolve_workflows(
            self._tier_roots,
            disabled_by_tier=disabled_workflows_by_tier,
        )
        errors.extend(wf_errs)

        # Step 4: Per-id resolution for each section.
        # Apply tier-targeted disable for items by removing matching ids
        # from each tier's bucket BEFORE resolution.
        def _filter_disabled(
            items_by_tier: dict[Tier, list[Any]],
            disabled: dict[Tier, frozenset[str]],
        ) -> dict[Tier, list[Any]]:
            if not disabled:
                return items_by_tier
            out: dict[Tier, list[Any]] = {}
            for t, items in items_by_tier.items():
                ban = disabled.get(t, frozenset())
                if not ban:
                    out[t] = items
                    continue
                out[t] = [it for it in items if getattr(it, "id", None) not in ban]
            return out

        resolved_rules, rules_prov, rules_errs = _resolve_by_id(
            _filter_disabled(per_tier_collected.get("rules", {}), disabled_ids_by_tier),
            section_key="rules",
            id_of=lambda r: getattr(r, "id", None),
        )
        resolved_inj, inj_prov, inj_errs = _resolve_by_id(
            _filter_disabled(
                per_tier_collected.get("injections", {}), disabled_ids_by_tier
            ),
            section_key="injections",
            id_of=lambda r: getattr(r, "id", None),
        )
        resolved_checks, checks_prov, check_errs = _resolve_by_id(
            _filter_disabled(
                per_tier_collected.get("checks", {}), disabled_ids_by_tier
            ),
            section_key="checks",
            id_of=lambda r: getattr(r, "id", None),
        )
        resolved_hints, hints_prov, hint_errs = _resolve_by_id(
            _filter_disabled(per_tier_collected.get("hints", {}), disabled_ids_by_tier),
            section_key="hints",
            id_of=lambda r: getattr(r, "id", None),
        )
        errors.extend(rules_errs)
        errors.extend(inj_errs)
        errors.extend(check_errs)
        errors.extend(hint_errs)

        # Phases follow workflow-tier override: keep only phases whose
        # (namespace, tier) match the winning tier of that workflow id.
        # Phase-nested hints / checks ride with their phase (already pruned).
        kept_phases: list[Phase] = []
        for tier, phases in per_tier_collected.get("phases", {}).items():
            for phase in phases:
                ns = getattr(phase, "namespace", None)
                if ns is None:
                    continue
                if ns == "global":
                    # Global namespace phases (rare); accept by per-id resolution.
                    kept_phases.append(phase)
                    continue
                won = resolved_wfs.get(ns)
                if won is None:
                    continue
                won_tier, _ = won
                if won_tier == tier:
                    kept_phases.append(phase)

        # Within-tier duplicate phase ids: detect on the kept set.
        seen_phase_ids: set[str] = set()
        deduped_phases: list[Phase] = []
        for phase in kept_phases:
            pid = getattr(phase, "id", None)
            if pid is None:
                deduped_phases.append(phase)
                continue
            if pid in seen_phase_ids:
                errors.append(
                    LoadError(
                        source="validation",
                        section="phases",
                        item_id=pid,
                        message=(
                            "duplicate phase id within tier "
                            f"{getattr(phase, 'tier', 'package')}; "
                            "later occurrence dropped"
                        ),
                    )
                )
                continue
            seen_phase_ids.add(pid)
            deduped_phases.append(phase)

        # Build phase provenance from kept phases (winning tier only).
        phase_provenance: dict[str, set[Tier]] = {}
        for phase in deduped_phases:
            pid = getattr(phase, "id", None)
            tier_attr = getattr(phase, "tier", None)
            if pid is None or tier_attr is None:
                continue
            phase_provenance.setdefault(pid, set()).add(tier_attr)

        # Hints sourced from phase-nesting are already pruned because we
        # walked them per tier into per_tier_collected; further pruning
        # of phase-scoped hints to the winning workflow tier:
        winning_phase_ids = {p.id for p in deduped_phases}
        # If a hint is phase-scoped and its phase is no longer in the kept
        # set (workflow lost at this tier), drop it.
        resolved_hints = [
            h
            for h in resolved_hints
            if (
                getattr(h, "phase", None) is None
                or getattr(h, "phase") in winning_phase_ids
                # OR the hint's phase is from the winning tier of its workflow
                or _phase_belongs_to_winning_workflow(h, resolved_wfs)
            )
        ]

        # Step 5: Cross-manifest validation (phase references).
        errors.extend(
            self._validate_phase_refs(resolved_rules, resolved_inj, deduped_phases)
        )

        # Step 6: Build WorkflowData for every workflow id seen.
        all_seen: set[str] = set()
        for tier in _TIER_ORDER:
            all_seen.update(workflow_paths_seen.get(tier, {}).keys())
        all_seen.update(wf_prov.keys())
        workflows_out: dict[str, WorkflowData] = {}
        error_sources = {e.source for e in errors}
        for wf_id in all_seen:
            won = resolved_wfs.get(wf_id)
            if won is None:
                # Workflow lost (e.g., partial override fell through with no
                # complete lower tier). Skip from the resolved set; surface
                # via errors (already added) instead.
                continue
            winning_tier, winning_path = won
            # Pull main_role from the winning tier's manifest if we cached it.
            winning_main_role: str | None = None
            seen = workflow_paths_seen.get(winning_tier, {}).get(wf_id)
            if seen is not None:
                _, winning_main_role = seen
            has_err = any(str(winning_path) in src for src in error_sources)
            workflows_out[wf_id] = WorkflowData(
                workflow_id=wf_id,
                path=winning_path,
                main_role=winning_main_role,
                has_errors=has_err,
                tier=winning_tier,
                defined_at=wf_prov.get(wf_id, frozenset({winning_tier})),
            )

        # Step 7: Merge per-section item provenance into one map.
        item_provenance: dict[str, frozenset[Any]] = {}
        for prov_map in (
            rules_prov,
            inj_prov,
            checks_prov,
            hints_prov,
            phase_provenance,
        ):
            for iid, tiers in prov_map.items():
                if iid in item_provenance:
                    item_provenance[iid] = frozenset(item_provenance[iid] | tiers)
                else:
                    item_provenance[iid] = frozenset(tiers)

        return LoadResult(
            rules=resolved_rules,
            injections=resolved_inj,
            checks=resolved_checks,
            hints=resolved_hints,
            phases=deduped_phases,
            errors=errors,
            workflows=workflows_out,
            workflow_provenance=wf_prov,  # type: ignore[arg-type]
            item_provenance=item_provenance,
        )

    # -- internals ----------------------------------------------------------

    def _discover(self) -> list[Path]:
        """Discover manifests across all configured tiers (fail-closed seam).

        Returns the list of every manifest file across the populated tiers.
        Raises ``OSError`` if any tier root iteration fails — tests patch
        this method to verify fail-closed behaviour.
        """
        return [path for _tier, path, _root in walk_tiers(self._tier_roots)]

    def _validate_phase_refs(
        self,
        rules: list[Any],
        injections: list[Any],
        phases: list[Phase],
    ) -> list[LoadError]:
        """Validate that rules / injections refer to known phase ids."""
        errors: list[LoadError] = []
        known = {p.id for p in phases}
        for section_key, items in (("rules", rules), ("injections", injections)):
            for item in items:
                item_id = getattr(item, "id", "unknown")
                for ref in getattr(item, "phases", []):
                    if ref not in known:
                        errors.append(
                            LoadError(
                                source="validation",
                                section=section_key,
                                item_id=item_id,
                                message=f"unknown phase ref '{ref}' in phases",
                            )
                        )
                for ref in getattr(item, "exclude_phases", []):
                    if ref not in known:
                        errors.append(
                            LoadError(
                                source="validation",
                                section=section_key,
                                item_id=item_id,
                                message=(
                                    f"unknown phase ref '{ref}' in exclude_phases"
                                ),
                            )
                        )
        return errors


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_global_path(path: Path, tier_root: Path) -> bool:
    """True if `path` lives under `<tier_root>/global/`."""
    try:
        path.relative_to(tier_root / "global")
        return True
    except ValueError:
        return False


def _phase_belongs_to_winning_workflow(
    hint: Any, resolved_wfs: dict[str, tuple[Tier, Path]]
) -> bool:
    """Defensive predicate: keep a phase-scoped hint when its phase string is
    qualified with a known winning workflow_id (covers any edge case where
    the phase wasn't in the deduped set due to workflow-tier mismatch)."""
    phase = getattr(hint, "phase", None)
    if not isinstance(phase, str):
        return False
    if ":" not in phase:
        return False
    ns = phase.split(":", 1)[0]
    return ns in resolved_wfs


def parse_disable_entries(
    entries: frozenset[str] | set[str] | list[str] | tuple[str, ...] | None,
    *,
    config_key: str,
    log: Callable[[str, str], None] | None = None,
) -> tuple[frozenset[str], dict[Tier, frozenset[str]]]:
    """Split disable entries into (bare_ids, tier_targeted_by_tier).

    The grammar differs between the two ``disabled_*`` config keys:

    - ``disabled_workflows``: workflow ids are bare (no colons). An entry
      with a colon MUST start with a valid tier prefix
      (``package`` / ``user`` / ``project``); anything else is an invalid
      tier prefix — log WARNING and skip (does NOT fall back to bare).
    - ``disabled_ids``: item ids are qualified ``<namespace>:<bare>``. An
      entry whose first colon-separated prefix is a valid tier becomes
      ``tier:<namespace>:<bare>`` (tier-targeted); otherwise the WHOLE
      entry is the bare qualified id.

    Args:
        entries: The raw config list (frozenset of strings, etc.).
        config_key: Either ``"disabled_workflows"`` or ``"disabled_ids"``.
            Used in the warning message and to select grammar.
        log: Callable (level, message) for warnings; defaults to module logger.

    Returns:
        ``(bare, tier_targeted)`` where:
        - ``bare`` is a frozenset of bare ids.
        - ``tier_targeted`` is ``{tier: frozenset(ids_disabled_at_that_tier)}``.
    """
    if entries is None:
        return frozenset(), {}

    is_workflow = config_key == "disabled_workflows"
    bare: set[str] = set()
    targeted: dict[Tier, set[str]] = {"package": set(), "user": set(), "project": set()}

    def _emit(msg: str) -> None:
        if log is not None:
            log("WARNING", msg)
        else:
            logger.warning(msg)

    for raw in entries:
        if not isinstance(raw, str) or not raw.strip():
            continue
        entry = raw.strip()
        if ":" not in entry:
            bare.add(entry)
            continue
        head, _, rest = entry.partition(":")
        if head in _VALID_TIER_PREFIXES:
            if not rest:
                _emit(
                    f"{config_key}: invalid entry '{entry}' (empty id after "
                    "tier prefix); skipping"
                )
                continue
            targeted[head].add(rest)  # type: ignore[index]
            continue
        # Prefix is not a valid tier name.
        if is_workflow:
            _emit(
                f"{config_key}: invalid tier prefix '{head}' in entry "
                f"'{entry}'; valid prefixes are package, user, project"
            )
            continue
        # disabled_ids: the entry is a qualified id of form
        # `namespace:bare_id` — keep the whole thing as bare.
        bare.add(entry)
    return frozenset(bare), {t: frozenset(s) for t, s in targeted.items() if s}
