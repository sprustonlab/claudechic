"""Regression test for issue #50: cluster.yaml tier-aware loading.

The cluster MCP tools (cluster_submit, cluster_jobs, etc.) used to read
their backend YAML from ``Path(__file__).parent / "cluster.yaml"`` --
always the bundled file inside the install dir. Site-specific config
drops at ``<cwd>/.claudechic/mcp_tools/cluster.yaml`` were silently
ignored, and ``uv tool upgrade claudechic`` would clobber any in-place
edits.

This test launches the real TUI in a temp directory that contains a
project-tier ``.claudechic/mcp_tools/cluster.yaml`` and asserts that
the loader picks up the project YAML rather than the bundled fallback.
The bundled package YAML always exists (it ships with the install), so
"both YAMLs are there" is satisfied by construction; the test is
concerned with which one wins.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest
import yaml
from claudechic.app import ChatApp

REPO_ROOT = Path(__file__).resolve().parents[1]
PKG_MCP_TOOLS_DIR = REPO_ROOT / "claudechic" / "defaults" / "mcp_tools"
BUNDLED_YAML = PKG_MCP_TOOLS_DIR / "cluster.yaml"


# Distinctive project-tier config -- nothing in the bundled YAML should
# match these values, so a successful read proves the project file won.
PROJECT_CONFIG = {
    "backend": "lsf",
    "ssh_target": "submit.example.org",
    "lsf_profile": "/misc/lsf/conf/profile.lsf",
    "watch_poll_interval": 7,
    "remote_cwd": "/scratch/test-project-tier",
    "path_map": [{"local": "/data", "cluster": "/nrs/data"}],
    "log_access": "ssh",
}


def _write_project_cluster_yaml(project_root: Path) -> Path:
    """Create ``<project_root>/.claudechic/mcp_tools/cluster.yaml``."""
    project_yaml_dir = project_root / ".claudechic" / "mcp_tools"
    project_yaml_dir.mkdir(parents=True, exist_ok=True)
    project_yaml = project_yaml_dir / "cluster.yaml"
    project_yaml.write_text(yaml.safe_dump(PROJECT_CONFIG), encoding="utf-8")
    return project_yaml


def _load_cluster_dispatch_module() -> types.ModuleType:
    """Import the bundled ``cluster_dispatch.py`` against the in-test
    helper namespace, mirroring the production loader in ``mcp.py``."""
    if "mcp_tools" not in sys.modules:
        sys.modules["mcp_tools"] = types.ModuleType("mcp_tools")

    if "mcp_tools._cluster" not in sys.modules:
        helper_file = PKG_MCP_TOOLS_DIR / "_cluster.py"
        spec = importlib.util.spec_from_file_location("mcp_tools._cluster", helper_file)
        assert spec is not None and spec.loader is not None
        helper_mod = importlib.util.module_from_spec(spec)
        sys.modules["mcp_tools._cluster"] = helper_mod
        spec.loader.exec_module(helper_mod)

    dispatch_file = PKG_MCP_TOOLS_DIR / "cluster_dispatch.py"
    spec = importlib.util.spec_from_file_location(
        "mcp_tools.cluster_dispatch_tier_test", dispatch_file
    )
    assert spec is not None and spec.loader is not None
    dispatch_mod = importlib.util.module_from_spec(spec)
    sys.modules["mcp_tools.cluster_dispatch_tier_test"] = dispatch_mod
    spec.loader.exec_module(dispatch_mod)
    return dispatch_mod


# ---------------------------------------------------------------------------
# Pre-flight sanity (unit level)
# ---------------------------------------------------------------------------


def test_bundled_yaml_has_distinct_content() -> None:
    """Sanity: the bundled YAML must not coincidentally match the
    project-tier fixture, otherwise downstream assertions cannot tell
    which file was loaded."""
    assert BUNDLED_YAML.is_file(), "bundled cluster.yaml must ship in defaults/"
    bundled = yaml.safe_load(BUNDLED_YAML.read_text(encoding="utf-8")) or {}
    # The shipped default leaves all site-specific keys empty.
    assert bundled.get("backend", "") != PROJECT_CONFIG["backend"]
    assert bundled.get("ssh_target", "") != PROJECT_CONFIG["ssh_target"]


def test_config_candidates_priority_order(monkeypatch, tmp_path) -> None:
    """``_config_candidates()`` lists project tier first, then user. The
    bundled package YAML is intentionally NOT a candidate (issue #50):
    it is a schema reference, not a runtime config source, because
    ``uv tool upgrade claudechic`` clobbers any in-place edits."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(tmp_path)

    mod = _load_cluster_dispatch_module()
    candidates = mod._config_candidates()

    assert candidates == [
        tmp_path / ".claudechic" / "mcp_tools" / "cluster.yaml",
        home / ".claudechic" / "mcp_tools" / "cluster.yaml",
    ]
    # Belt-and-suspenders: prove the bundled path is not snuck in.
    assert PKG_MCP_TOOLS_DIR / "cluster.yaml" not in candidates


def test_load_dispatch_config_returns_empty_when_no_tier_config(
    monkeypatch, tmp_path
) -> None:
    """With no project- and no user-tier file, the loader returns ``{}``
    -- NOT the bundled placeholder. This is the contract that lets the
    cluster tools surface "not configured" cleanly instead of silently
    loading stale install-dir state.

    The bundled YAML on disk has empty placeholder values, so a buggy
    fallback would also produce an empty-ish dict but with the schema
    keys (``backend: ""``, ``log_access: "auto"``, etc.) populated.
    Asserting equality with ``{}`` distinguishes the two cases."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(tmp_path)

    mod = _load_cluster_dispatch_module()
    config = mod._load_dispatch_config()

    assert config == {}, (
        "loader must NOT fall back to the bundled YAML; got "
        f"{config!r}. The bundled file is a schema reference only."
    )


def test_bundled_yaml_is_documented_as_schema_only() -> None:
    """The bundled cluster.yaml must declare itself a schema reference
    so a future contributor reading the install dir does not assume it
    is loaded. Pins the disclaimer text so silent edits get caught."""
    text = BUNDLED_YAML.read_text(encoding="utf-8")
    assert "SCHEMA REFERENCE ONLY" in text
    assert "NOT loaded at runtime" in text


# ---------------------------------------------------------------------------
# Real TUI launch -- the integration test the user explicitly requested
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_real_tui_launch_loads_project_tier_cluster_yaml(
    mock_sdk, monkeypatch, tmp_path
) -> None:
    """Real TUI launch in a directory containing a project-tier
    ``.claudechic/mcp_tools/cluster.yaml``: the bundled YAML at
    ``<install>/defaults/mcp_tools/cluster.yaml`` also exists (it ships
    with the install) so both files are present. The dispatcher must
    pick the project tier.

    This is the end-to-end shape of issue #50: the user sets up a site
    config, launches the TUI from the project root, and expects the
    cluster MCP tools to honor that config rather than the bundled
    placeholder.
    """
    # Isolate $HOME so a real ~/.claudechic/mcp_tools/cluster.yaml on
    # the developer's machine doesn't override the project tier and
    # invalidate the test premise.
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(tmp_path)

    project_yaml = _write_project_cluster_yaml(tmp_path)
    assert project_yaml.is_file()
    assert BUNDLED_YAML.is_file(), (
        "test premise broken: bundled cluster.yaml must exist alongside "
        "the project tier file so we can prove which one was chosen"
    )

    app = ChatApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        # Sanity: the TUI launched in our temp project root.
        assert app._cwd == tmp_path

        # The TUI's MCP discovery loads cluster_dispatch.py from the
        # package tier under the namespaced key ``mcp_tools.package.
        # cluster_dispatch``. Reach into sys.modules to grab the exact
        # module instance the live MCP server is bound to, so we test
        # the same loader path the agent would hit at tool-call time.
        dispatch_mod = sys.modules.get("mcp_tools.package.cluster_dispatch")
        if dispatch_mod is None:
            # Older / alt loader paths may stash it under the legacy
            # alias. Either is fine -- both refer to the same source
            # file, so the layered loader logic under test is identical.
            dispatch_mod = sys.modules.get("mcp_tools.cluster_dispatch")
        assert dispatch_mod is not None, (
            "cluster_dispatch.py was not loaded by the TUI's MCP "
            "discovery; the test cannot verify the layered loader. "
            "sys.modules keys: "
            + ", ".join(k for k in sys.modules if "cluster_dispatch" in k)
        )

        # Drive the loader exactly like the live cluster_* tools do.
        config = dispatch_mod._load_dispatch_config()

    # Outside the run_test context the app is torn down, but the loader
    # result is a plain dict so we can keep asserting on it.
    assert config == PROJECT_CONFIG, (
        "project-tier cluster.yaml was not honored by _load_dispatch_config; "
        "this is exactly the bug from issue #50. "
        f"Loaded config: {config!r}"
    )

    # Spot-checks against the most operationally significant fields, in
    # case a future refactor merges configs across tiers (in which case
    # equality may not hold but project values must still win).
    assert config["backend"] == "lsf"
    assert config["ssh_target"] == "submit.example.org"
    assert config["remote_cwd"] == "/scratch/test-project-tier"


@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_real_tui_launch_without_tier_config_returns_empty(
    mock_sdk, monkeypatch, tmp_path
) -> None:
    """Negative companion: launching the TUI in a directory with NO
    project- or user-tier ``cluster.yaml`` yields ``{}`` from
    ``_load_dispatch_config()`` -- explicitly NOT the bundled YAML.

    The bundled file still exists on disk inside the install dir (it
    ships with the package as a schema reference). This test pins the
    contract that the live MCP server does not consult it: the cluster
    tools must surface "not configured" via empty config, not silently
    load whatever happens to be in the install dir.

    Asserting ``config == {}`` rather than just falsiness catches a
    regression where the bundled placeholder (``backend: ""``,
    ``log_access: "auto"``, etc.) sneaks back in -- that dict is also
    falsy-ish but populated, so equality is the discriminating check."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(tmp_path)

    # Deliberately NO project- or user-tier file written.
    assert not (tmp_path / ".claudechic" / "mcp_tools" / "cluster.yaml").exists()
    assert not (home / ".claudechic" / "mcp_tools" / "cluster.yaml").exists()
    # Bundled file still on disk -- this is the file the loader is
    # required NOT to read.
    assert BUNDLED_YAML.is_file()

    app = ChatApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        dispatch_mod = sys.modules.get(
            "mcp_tools.package.cluster_dispatch"
        ) or sys.modules.get("mcp_tools.cluster_dispatch")
        assert dispatch_mod is not None
        config = dispatch_mod._load_dispatch_config()

    assert config == {}, (
        "loader must NOT fall back to bundled YAML when no tier config "
        f"exists; got {config!r}. Issue #50 -- the bundled file is a "
        "schema reference, never a runtime config source."
    )
