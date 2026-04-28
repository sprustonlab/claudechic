"""Manifest loader — discovers, parses, and validates YAML manifests.

Single code path: loads all manifests (global + workflow), dispatches each
YAML section to registered ManifestSection[T] parsers, and returns a unified
LoadResult. Callers filter by what they need.

The loader is GENERIC — it doesn't know section semantics. It dispatches
to typed parsers via the ManifestSection protocol. Adding a new section type
means implementing ManifestSection[T] and calling loader.register().
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, TypeVar

import yaml

from claudechic.workflows.phases import Phase

logger = logging.getLogger(__name__)

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
    ) -> list[T_co]:
        """Parse raw YAML section into typed objects.

        Args:
            raw: List of dicts from yaml.safe_load for this section key.
            namespace: 'global' for global/*.yaml, workflow_id for workflow manifests.
            source_path: Path to manifest file (error messages only).

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

    def get_workflow(self, wf_id: str) -> WorkflowData | None:
        """Look up per-workflow data by workflow_id."""
        return self.workflows.get(wf_id)


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


def discover_manifests(global_dir: Path, workflows_dir: Path) -> list[Path]:
    """Discover all manifest files in global/ and workflows/.

    Returns paths in load order:
    1. global/*.yaml (all YAML files, sorted alphabetically)
    2. workflows/*/workflow_name.yaml (sorted alphabetically)

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


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


class ManifestLoader:
    """Unified manifest loader — single code path, callers filter."""

    def __init__(self, global_dir: Path, workflows_dir: Path) -> None:
        self._global_dir = global_dir
        self._workflows_dir = workflows_dir
        self._parsers: dict[str, ManifestSection[Any]] = {}

    def register(self, parser: ManifestSection[Any]) -> None:
        """Register a section parser by its section_key."""
        self._parsers[parser.section_key] = parser

    def load(self) -> LoadResult:
        """Load all manifests and return unified result.

        Error handling:
        - global/ or workflows/ unreadable -> fail closed (empty rules + fatal error;
          callers treat this as "block everything")
        - Individual manifest malformed -> skip and log error
        - Individual item malformed -> skip and log error
        """
        errors: list[LoadError] = []
        workflows: dict[str, WorkflowData] = {}

        # Step 1: Discover
        try:
            paths = self._discover()
        except OSError as e:
            return LoadResult(
                errors=[
                    LoadError(
                        source="discovery",
                        message=f"Cannot read global/ or workflows/: {e}",
                    )
                ]
            )

        # Step 2: Parse each manifest through registered parsers
        collected: dict[str, list[Any]] = {k: [] for k in self._parsers}

        for path in paths:
            try:
                with path.open(encoding="utf-8") as f:
                    data = yaml.safe_load(f)
            except (OSError, yaml.YAMLError) as e:
                errors.append(LoadError(source=str(path), message=str(e)))
                if not self._is_global_path(path):
                    wf_id = path.parent.name
                    workflows[wf_id] = WorkflowData(
                        workflow_id=wf_id, path=path.parent, has_errors=True
                    )
                continue

            # Determine namespace — global files get "global", workflow files
            # use workflow_id from YAML if present, else fallback to dir name
            if self._is_global_path(path):
                namespace = "global"
            else:
                if not isinstance(data, dict):
                    errors.append(
                        LoadError(source=str(path), message="not a YAML mapping")
                    )
                    continue
                namespace = str(data.get("workflow_id", path.parent.name))

            # Global files: bare list -> infer section key from filename stem
            if isinstance(data, list) and self._is_global_path(path):
                key = path.stem  # "rules", "checks", "hints", "injections"
                parser = self._parsers.get(key)
                if parser is None:
                    errors.append(
                        LoadError(
                            source=str(path),
                            message=f"No parser registered for '{key}' (inferred from filename)",
                        )
                    )
                else:
                    try:
                        parsed = parser.parse(
                            data, namespace=namespace, source_path=str(path)
                        )
                        collected.setdefault(key, []).extend(parsed)
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

            # Track workflow data (manifest populated after all parsing)
            if not self._is_global_path(path):
                wf_id = data.get("workflow_id", path.parent.name)
                main_role = data.get("main_role")
                workflows.setdefault(
                    wf_id,
                    WorkflowData(
                        workflow_id=wf_id,
                        path=path.parent,
                        main_role=main_role,
                    ),
                )

            # Dict-based files: dispatch by section keys
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
                        section, namespace=namespace, source_path=str(path)
                    )
                    collected.setdefault(key, []).extend(parsed)
                except Exception as e:
                    errors.append(
                        LoadError(
                            source=str(path),
                            section=key,
                            message=f"parser error: {e}",
                        )
                    )

        # Step 2b: Extract phase-nested hints (after all manifests parsed)
        for phase in collected.get("phases", []):
            if hasattr(phase, "hints") and phase.hints:
                collected.setdefault("hints", []).extend(phase.hints)

        # Step 3: Cross-manifest validation
        errors.extend(self._validate(collected))

        # Step 4: Update has_errors for workflows with validation/parse errors
        error_sources = {e.source for e in errors}
        for wf_id, wf_data in list(workflows.items()):
            if not wf_data.has_errors and any(
                str(wf_data.path) in src for src in error_sources
            ):
                workflows[wf_id] = WorkflowData(
                    workflow_id=wf_id,
                    path=wf_data.path,
                    has_errors=True,
                )

        return LoadResult(
            rules=collected.get("rules", []),
            injections=collected.get("injections", []),
            checks=collected.get("checks", []),
            hints=collected.get("hints", []),
            phases=collected.get("phases", []),
            errors=errors,
            workflows=workflows,
        )

    def _discover(self) -> list[Path]:
        """Discover manifest files. Raises OSError if dirs unreadable."""
        return discover_manifests(self._global_dir, self._workflows_dir)

    def _is_global_path(self, path: Path) -> bool:
        """Check if a manifest path is under the global directory."""
        try:
            path.relative_to(self._global_dir)
            return True
        except ValueError:
            return False

    def _validate(self, collected: dict[str, list[Any]]) -> list[LoadError]:
        """Cross-manifest validation: duplicate IDs, phase references."""
        errors: list[LoadError] = []

        # 1. Duplicate ID detection (after namespace prefixing)
        seen: dict[str, str] = {}
        for key, items in collected.items():
            for item in items:
                iid = getattr(item, "id", None)
                if iid is None:
                    continue
                if iid in seen:
                    errors.append(
                        LoadError(
                            source="validation",
                            section=key,
                            item_id=iid,
                            message=f"duplicate ID (first in {seen[iid]})",
                        )
                    )
                else:
                    seen[iid] = key

        # 2. Phase reference validation (rules and injections)
        known_phases = {p.id for p in collected.get("phases", [])}
        for section_key in ("rules", "injections"):
            for item in collected.get(section_key, []):
                item_id = getattr(item, "id", "unknown")
                for ref in getattr(item, "phases", []):
                    if ref not in known_phases:
                        errors.append(
                            LoadError(
                                source="validation",
                                section=section_key,
                                item_id=item_id,
                                message=f"unknown phase ref '{ref}' in phases",
                            )
                        )
                for ref in getattr(item, "exclude_phases", []):
                    if ref not in known_phases:
                        errors.append(
                            LoadError(
                                source="validation",
                                section=section_key,
                                item_id=item_id,
                                message=f"unknown phase ref '{ref}' in exclude_phases",
                            )
                        )

        return errors
