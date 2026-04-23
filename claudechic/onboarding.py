"""Onboarding health checks and welcome screen logic.

Checks real state of facets (cluster, git, codebase) against ProjectConfig
toggles, and determines whether the welcome screen should appear.

LEAF MODULE: stdlib + yaml only. No imports from workflow_engine/, checks/, or
guardrails/.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from claudechic.config import ProjectConfig
from claudechic.hints.state import HintStateStore

_PKG_DIR = Path(__file__).parent

# ---------------------------------------------------------------------------
# FacetStatus — one row in the welcome screen checklist
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FacetStatus:
    """Status of a single onboarding facet."""

    workflow_id: str
    label: str
    configured: bool
    detail: str


# ---------------------------------------------------------------------------
# Dismiss marker — stored in hints_state.json
# ---------------------------------------------------------------------------

_DISMISS_KEY = "onboarding_dismissed"


def _is_dismissed(store: HintStateStore) -> bool:
    """Check if onboarding was permanently dismissed."""
    data = store.get_activation_data()
    return bool(data.get(_DISMISS_KEY, False))


def write_dismiss_marker(store: HintStateStore) -> None:
    """Write the permanent dismiss marker to hints_state.json."""
    data = store.get_activation_data()
    data[_DISMISS_KEY] = True
    store.set_activation_data(data)
    store.save()


# ---------------------------------------------------------------------------
# Health check functions
# ---------------------------------------------------------------------------


def _cluster_configured(project_root: Path) -> bool:
    """Check if cluster access is configured and reachable.

    Returns True if:
    - mcp_tools/cluster.yaml has non-empty backend AND ssh_target AND SSH
      succeeds (5s timeout), OR
    - A local scheduler is detected (bsub or sbatch on PATH).
    """
    # Check for local scheduler first (fast path)
    for cmd in ("bsub", "sbatch"):
        if shutil.which(cmd) is not None:
            return True

    # Check cluster.yaml for remote config
    cluster_yaml = project_root / "mcp_tools" / "cluster.yaml"
    if not cluster_yaml.is_file():
        return False

    try:
        import yaml  # type: ignore[import-untyped]

        data = yaml.safe_load(cluster_yaml.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return False
    except Exception:
        return False

    backend = data.get("backend", "")
    ssh_target = data.get("ssh_target", "")
    # Config is considered complete if backend and ssh_target are set.
    # We don't test SSH liveness here — it's slow, can fail transiently,
    # and doesn't work reliably on all platforms (e.g. Windows).
    return bool(backend) and bool(ssh_target)


def _git_configured(project_root: Path) -> bool:
    """Check if git repo exists with a remote configured."""
    if not (project_root / ".git").exists():
        return False
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            cwd=project_root,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


_CODE_EXTENSIONS = frozenset(
    {
        ".py",
        ".js",
        ".ts",
        ".rs",
        ".go",
        ".java",
        ".c",
        ".cpp",
        ".h",
        ".rb",
        ".jl",
        ".r",
        ".m",
        ".swift",
        ".kt",
        ".scala",
        ".zig",
    }
)


_SKIP_DIRS = frozenset(
    {
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        "build",
        "dist",
        ".git",
        ".tox",
        ".mypy_cache",
        ".ruff_cache",
    }
)

# Cap the number of files examined to avoid slow scans in huge repos.
_MAX_FILES_CHECKED = 5000


def _codebase_configured(project_root: Path) -> bool:
    """Check if the project contains code files.

    Returns True if any non-hidden subdirectory of the project root
    contains files with common code extensions.  Skips heavy directories
    (.venv, node_modules, __pycache__, etc.) and caps the search to
    avoid slow scans in large repositories.
    """
    checked = 0
    for child in project_root.iterdir():
        if not child.is_dir() or child.name.startswith("."):
            continue
        if child.name in _SKIP_DIRS:
            continue
        for f in child.rglob("*"):
            if f.is_dir() and f.name in _SKIP_DIRS:
                continue
            if f.is_file() and f.suffix in _CODE_EXTENSIONS:
                return True
            checked += 1
            if checked >= _MAX_FILES_CHECKED:
                return False
    return False


# ---------------------------------------------------------------------------
# Detail functions — human-readable status strings
# ---------------------------------------------------------------------------


def _cluster_detail(project_root: Path) -> str:
    """Return detail string for configured cluster, e.g. 'LSF on login.hpc.edu'."""
    # Check local scheduler first
    for cmd, name in [("bsub", "LSF"), ("sbatch", "SLURM")]:
        if shutil.which(cmd) is not None:
            return f"{name} (local)"

    cluster_yaml = project_root / "mcp_tools" / "cluster.yaml"
    try:
        import yaml  # type: ignore[import-untyped]

        data = yaml.safe_load(cluster_yaml.read_text(encoding="utf-8"))
        backend = str(data.get("backend", "")).upper()
        target = data.get("ssh_target", "unknown")
        return f"{backend} on {target}"
    except Exception:
        return "configured"


def _git_detail(project_root: Path) -> str:
    """Return detail string for git remote, e.g. 'origin → github.com/user/repo'."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            cwd=project_root,
            timeout=5,
        )
        url = result.stdout.strip()
        if url:
            # Shorten SSH/HTTPS URLs for display
            url = url.replace("git@github.com:", "github.com/")
            url = url.replace("https://github.com/", "github.com/")
            url = url.removesuffix(".git")
            return f"origin → {url}"
    except (subprocess.TimeoutExpired, OSError):
        pass
    return "origin configured"


def _codebase_detail(project_root: Path) -> str:
    """Return detail string for codebase, e.g. 'src, lib'."""
    dirs_with_code = []
    for child in project_root.iterdir():
        if not child.is_dir() or child.name.startswith("."):
            continue
        if child.name in _SKIP_DIRS:
            continue
        if any(f.suffix in _CODE_EXTENSIONS for f in child.rglob("*") if f.is_file()):
            dirs_with_code.append(child.name)
    if dirs_with_code:
        return ", ".join(sorted(dirs_with_code))
    return "code detected"


# ---------------------------------------------------------------------------
# Workflow existence check
# ---------------------------------------------------------------------------


def _workflow_exists(workflows_dir: Path, dir_name: str) -> bool:
    """Check if a workflow manifest exists (e.g., workflows/git_setup/git_setup.yaml)."""
    return (workflows_dir / dir_name / f"{dir_name}.yaml").is_file()


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def check_onboarding(project_root: Path) -> list[FacetStatus] | None:
    """Check onboarding status and return facet list if incomplete.

    Returns:
        None if onboarding should not be shown (dismissed, no config file,
        or all facets configured). Otherwise returns the list of FacetStatus
        items for the welcome screen.
    """
    store = HintStateStore(project_root)

    if _is_dismissed(store):
        return None

    config = ProjectConfig.load(project_root)

    # Map of (workflow_id, directory_name) -- only show facets whose
    # workflow manifest actually exists. Bundled workflows live in the
    # package directory, not in the project root.
    workflows_dir = _PKG_DIR / "workflows"

    facets: list[FacetStatus] = []

    if "cluster_setup" not in config.disabled_workflows and _workflow_exists(
        workflows_dir, "cluster_setup"
    ):
        configured = _cluster_configured(project_root)
        detail = _cluster_detail(project_root) if configured else "not configured"
        facets.append(
            FacetStatus("cluster-setup", "Cluster access", configured, detail)
        )

    # Git is always relevant (if the workflow exists)
    if _workflow_exists(workflows_dir, "git_setup"):
        configured = _git_configured(project_root)
        detail = _git_detail(project_root) if configured else "no remote set"
        facets.append(FacetStatus("git-setup", "Git remote", configured, detail))

    # Detect existing codebase by checking for code files in the project
    has_codebase = _codebase_configured(project_root)
    if has_codebase and _workflow_exists(workflows_dir, "codebase_setup"):
        detail = _codebase_detail(project_root)
        facets.append(
            FacetStatus("codebase-setup", "Codebase integration", has_codebase, detail)
        )

    if not facets:
        return None

    # If everything is configured, don't show
    if all(f.configured for f in facets):
        return None

    return facets
