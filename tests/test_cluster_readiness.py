"""Regression tests for ``_check_config_readiness``.

The historical behavior treated ``path_map: []`` (an explicit empty
list) as ``"incomplete"`` because ``not config.get("path_map")`` is
truthy for an empty list in Python. That conflated two distinct
states:

  - "User ran cluster_setup and decided no path mapping is needed"
    -- e.g. shared-filesystem setups where local paths and cluster
    paths are identical (NFS-mounted home dirs visible from both
    the workstation and the compute nodes). ``path_map: []`` is
    the correct end state here.
  - "User has not yet thought about path mapping" -- the key is
    absent from the config entirely.

The fix uses ``"path_map" not in config`` instead, so the first case
returns ``"ready"`` and the second still returns ``"incomplete"``.

Why it matters: every successful ``cluster_submit`` /
``cluster_status`` / ``cluster_logs`` response carried a misleading
``setup_needed: "run cluster_setup workflow"`` field for shared-FS
users, even though everything was working. The tool description for
``cluster_submit`` instructs consumer agents to interrupt the user
and re-run setup on ``incomplete`` -- so the bug surfaced as
spurious "do you want to run cluster_setup?" prompts after every
successful job.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
PKG_MCP_TOOLS_DIR = REPO_ROOT / "claudechic" / "defaults" / "mcp_tools"


def _load_cluster_helper() -> types.ModuleType:
    """Import ``_cluster.py`` standalone (mirrors the production
    loader path in ``claudechic/mcp.py``). Caches under a unique
    sys.modules key so repeated calls within one test session reuse
    the same module object."""
    if "mcp_tools" not in sys.modules:
        sys.modules["mcp_tools"] = types.ModuleType("mcp_tools")
    if "mcp_tools._cluster" in sys.modules:
        return sys.modules["mcp_tools._cluster"]
    helper_file = PKG_MCP_TOOLS_DIR / "_cluster.py"
    spec = importlib.util.spec_from_file_location("mcp_tools._cluster", helper_file)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["mcp_tools._cluster"] = module
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# The bug under test: empty path_map is "ready", not "incomplete"
# ---------------------------------------------------------------------------


def test_empty_path_map_is_ready_when_ssh_target_set() -> None:
    """The headline case: ``path_map: []`` with a real ssh_target is
    a fully-configured shared-filesystem setup, not incomplete.

    Historical behavior (pre-fix): returned ``"incomplete"`` because
    ``not config.get("path_map")`` is truthy for an empty list. That
    surfaced a false ``setup_needed`` flag on every successful tool
    call.
    """
    mod = _load_cluster_helper()
    config = {
        "ssh_target": "submit.example.org",
        "backend": "lsf",
        "path_map": [],  # explicit empty list -- shared-FS setup
    }
    # Force has_local=False so the path_map branch is the only thing
    # that could mark this incomplete.
    with patch.object(mod.shutil, "which", return_value=None):
        result = mod._check_config_readiness(config)
    assert result == "ready", (
        "an explicit empty path_map with ssh_target set must be 'ready' "
        "-- this is the shared-filesystem case (NFS, etc.) where local "
        "paths == cluster paths and no translation is needed"
    )


def test_path_map_absent_is_incomplete() -> None:
    """The key-absent case: a config without a ``path_map`` key has
    not been through cluster_setup yet and still warrants the
    incomplete signal."""
    mod = _load_cluster_helper()
    config = {
        "ssh_target": "submit.example.org",
        # no path_map key
    }
    with patch.object(mod.shutil, "which", return_value=None):
        result = mod._check_config_readiness(config)
    assert result == "incomplete", (
        "a config missing path_map entirely should signal incomplete so "
        "the user is prompted to run cluster_setup"
    )


def test_populated_path_map_is_ready() -> None:
    """A non-empty path_map with ssh_target set is the canonical
    fully-configured case."""
    mod = _load_cluster_helper()
    config = {
        "ssh_target": "submit.example.org",
        "path_map": [{"local": "/Volumes/data", "cluster": "/nrs/data"}],
    }
    with patch.object(mod.shutil, "which", return_value=None):
        result = mod._check_config_readiness(config)
    assert result == "ready"


# ---------------------------------------------------------------------------
# Other readiness branches -- regression coverage so the fix doesn't
# accidentally change behavior outside its scope
# ---------------------------------------------------------------------------


def test_no_ssh_target_no_local_scheduler_needs_setup() -> None:
    """Empty config with no local bsub/sbatch -> the user has not
    started setup at all."""
    mod = _load_cluster_helper()
    with patch.object(mod.shutil, "which", return_value=None):
        result = mod._check_config_readiness({})
    assert result == "needs_setup"


def test_no_ssh_target_but_local_scheduler_is_ready() -> None:
    """Local scheduler available -> we can submit jobs without an SSH
    hop. ssh_target empty is fine. (path_map gate only fires when
    ssh_target is set, so an empty path_map here doesn't matter.)"""
    mod = _load_cluster_helper()
    with patch.object(mod.shutil, "which", return_value="/usr/bin/bsub"):
        result = mod._check_config_readiness({})
    assert result == "ready"


# ---------------------------------------------------------------------------
# Empty ``path_map`` round-trip via YAML (the user-tier shape)
# ---------------------------------------------------------------------------


def test_empty_path_map_via_yaml_roundtrip(tmp_path) -> None:
    """End-to-end: write a YAML config matching the cluster_setup
    workflow's apply phase output (``path_map: []`` for shared-FS
    setups), load it back, run readiness. Catches a regression where
    YAML's parse of ``[]`` produces something other than a list and
    the key-presence check stops working."""
    import yaml

    yaml_text = (
        "ssh_target: submit.example.org\n"
        "backend: lsf\n"
        "lsf_profile: /misc/lsf/conf/profile.lsf\n"
        "path_map: []\n"
        'remote_cwd: ""\n'
        "log_access: auto\n"
    )
    cfg_path = tmp_path / "cluster.yaml"
    cfg_path.write_text(yaml_text, encoding="utf-8")

    config = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    assert "path_map" in config
    assert config["path_map"] == []

    mod = _load_cluster_helper()
    with patch.object(mod.shutil, "which", return_value=None):
        result = mod._check_config_readiness(config)
    assert result == "ready", (
        "YAML round-trip of a real shared-FS config produced "
        f"readiness={result!r}; expected 'ready'"
    )
