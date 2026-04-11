"""Onboarding health checks and welcome screen logic.

Checks real state of facets (cluster, git, codebase) against CopierAnswers
intent, and determines whether the welcome screen should appear.

LEAF MODULE: stdlib + yaml only. No imports from workflows/, checks/, or
guardrails/.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from claudechic.hints.state import CopierAnswers, HintStateStore


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
    if not backend or not ssh_target:
        return False

    # Verify SSH connectivity (5s timeout)
    try:
        result = subprocess.run(
            ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5",
             ssh_target, "echo", "ok"],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


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


def _codebase_configured(project_root: Path) -> bool:
    """Check if at least one non-hidden directory exists in repos/."""
    repos_dir = project_root / "repos"
    if not repos_dir.is_dir():
        return False
    return any(
        child.is_dir() and not child.name.startswith(".")
        for child in repos_dir.iterdir()
    )


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
    """Return detail string for codebase, e.g. 'mypackage in repos/'."""
    repos_dir = project_root / "repos"
    if not repos_dir.is_dir():
        return "integrated"
    dirs = [
        child.name
        for child in repos_dir.iterdir()
        if child.is_dir() and not child.name.startswith(".")
    ]
    if dirs:
        return f"{', '.join(sorted(dirs))} in repos/"
    return "integrated"


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
        None if onboarding should not be shown (dismissed, no copier answers,
        or all facets configured). Otherwise returns the list of FacetStatus
        items for the welcome screen.
    """
    store = HintStateStore(project_root)

    if _is_dismissed(store):
        return None

    answers = CopierAnswers.load(project_root)
    if not answers.raw:
        # No .copier-answers.yml or empty — not a template project
        return None

    # Map of (workflow_id, directory_name) — only show facets whose
    # workflow manifest actually exists in the project.
    workflows_dir = project_root / "workflows"

    facets: list[FacetStatus] = []

    if answers.get("use_cluster") and _workflow_exists(workflows_dir, "cluster_setup"):
        configured = _cluster_configured(project_root)
        detail = _cluster_detail(project_root) if configured else "not configured"
        facets.append(FacetStatus("cluster-setup", "Cluster access", configured, detail))

    # Git is always relevant (if the workflow exists)
    if _workflow_exists(workflows_dir, "git_setup"):
        configured = _git_configured(project_root)
        detail = _git_detail(project_root) if configured else "no remote set"
        facets.append(FacetStatus("git-setup", "Git remote", configured, detail))

    if answers.get("use_existing_codebase") and _workflow_exists(workflows_dir, "codebase_setup"):
        configured = _codebase_configured(project_root)
        detail = _codebase_detail(project_root) if configured else "not integrated"
        facets.append(FacetStatus("codebase-setup", "Codebase integration", configured, detail))

    # If everything is configured, don't show
    if all(f.configured for f in facets):
        return None

    return facets
