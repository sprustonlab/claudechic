"""Tier-aware behavior for file-exists-check and file-content-check.

Originally driven by an asymmetry between the runtime cluster MCP
loader (project tier > user tier, see issue #50) and the
cluster_setup workflow's advance checks, which only accepted a
single hardcoded project-tier path. A user who wrote their cluster
config to ``~/.claudechic/mcp_tools/cluster.yaml`` would have a
working runtime but a workflow that refused to advance.

Three behaviors covered here:

1. ``_resolve_against`` expands ``~`` BEFORE deciding whether the
   path is absolute, so a manifest entry like
   ``~/.claudechic/mcp_tools/cluster.yaml`` resolves to the user's
   home dir, not ``<base_dir>/~/...`` (the original behavior --
   silently broken).

2. ``FileExistsCheck`` and ``FileContentCheck`` accept either
   ``path`` (single, the historical form) or ``paths`` (list, new).
   First-match-wins semantics: the first path that satisfies the
   check makes the check pass.

3. Single-path back-compat: existing manifests that pass ``path:``
   work unchanged.
"""

from __future__ import annotations

import pytest
from claudechic.checks.builtins import (
    FileContentCheck,
    FileExistsCheck,
    _resolve_against,
)

# pytest-asyncio is configured in mode=auto so async test functions are
# picked up without an explicit marker. We only need pytest imported
# above for ``pytest.raises`` in the sync tests.
_ = pytest  # silence unused-import warning when only ``raises`` is used


# ---------------------------------------------------------------------------
# _resolve_against
# ---------------------------------------------------------------------------


def test_resolve_against_expands_tilde_before_absolute_check(
    monkeypatch, tmp_path
) -> None:
    """``~`` resolves to ``$HOME``, not to ``<base_dir>/~``. The original
    implementation called ``Path.is_absolute()`` BEFORE expanding ``~``,
    so a literal ``~`` segment failed the absolute check and got
    joined onto base_dir."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    # USERPROFILE matters on Windows -- harmless on POSIX.
    monkeypatch.setenv("USERPROFILE", str(home))

    base_dir = tmp_path / "project_root"
    base_dir.mkdir()

    resolved = _resolve_against("~/.claudechic/cluster.yaml", base_dir)

    assert resolved == home / ".claudechic" / "cluster.yaml"
    assert str(base_dir) not in str(resolved), (
        f"~ should NOT have been joined onto base_dir; got {resolved}"
    )


def test_resolve_against_relative_paths_still_join_base_dir(tmp_path) -> None:
    """Plain relative paths (no ~) still join onto ``base_dir`` -- the
    historical behavior. This is the back-compat sanity test."""
    resolved = _resolve_against(".claudechic/cluster.yaml", tmp_path)
    assert resolved == tmp_path / ".claudechic" / "cluster.yaml"


def test_resolve_against_absolute_paths_are_unchanged(tmp_path) -> None:
    """Absolute paths bypass base_dir entirely."""
    abs_path = tmp_path / "absolute" / "file.yaml"
    resolved = _resolve_against(abs_path, tmp_path / "ignored_base")
    assert resolved == abs_path


# ---------------------------------------------------------------------------
# FileExistsCheck -- multi-path
# ---------------------------------------------------------------------------


async def test_file_exists_check_accepts_paths_list_first_wins(tmp_path) -> None:
    """When multiple paths are given, the first-existing one passes."""
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    b.write_text("hello", encoding="utf-8")  # only b exists

    check = FileExistsCheck(paths=[a, b])
    result = await check.check()

    assert result.passed is True
    assert str(b) in result.evidence


async def test_file_exists_check_paths_all_missing_fails(tmp_path) -> None:
    """When no path exists, the failure message lists all candidates so
    the user can see which tiers were probed."""
    a = tmp_path / "missing_a.txt"
    b = tmp_path / "missing_b.txt"

    check = FileExistsCheck(paths=[a, b])
    result = await check.check()

    assert result.passed is False
    assert str(a) in result.evidence
    assert str(b) in result.evidence


async def test_file_exists_check_single_path_back_compat(tmp_path) -> None:
    """Existing manifests using ``path:`` keep working unchanged."""
    f = tmp_path / "file.txt"
    f.write_text("hi", encoding="utf-8")

    check = FileExistsCheck(path=f)
    result = await check.check()

    assert result.passed is True


def test_file_exists_check_requires_path_or_paths() -> None:
    """Sanity that omitting both raises a clear error rather than
    silently passing."""
    with pytest.raises(ValueError, match="path"):
        FileExistsCheck()


# ---------------------------------------------------------------------------
# FileContentCheck -- multi-path
# ---------------------------------------------------------------------------


async def test_file_content_check_paths_first_match_wins(tmp_path) -> None:
    """First file containing the pattern wins. Files that don't exist or
    don't match are skipped silently -- the contract is "any of these"
    not "all of these"."""
    project = tmp_path / "project" / "cluster.yaml"
    project.parent.mkdir()
    user = tmp_path / "user" / "cluster.yaml"
    user.parent.mkdir()

    # Project file exists but does NOT match.
    project.write_text("ssh_target:\nbackend: lsf\n", encoding="utf-8")
    # User file exists AND matches.
    user.write_text("ssh_target: submit.example.org\n", encoding="utf-8")

    check = FileContentCheck(
        paths=[project, user],
        pattern=r"ssh_target:\s+\S+",
    )
    result = await check.check()

    assert result.passed is True
    assert "submit.example.org" in result.evidence
    assert str(user) in result.evidence


async def test_file_content_check_paths_project_wins_when_both_match(
    tmp_path,
) -> None:
    """When multiple files satisfy the pattern, the FIRST listed wins.
    This pins the priority order: project tier > user tier (or
    whatever order the manifest declares)."""
    project = tmp_path / "project" / "cluster.yaml"
    project.parent.mkdir()
    user = tmp_path / "user" / "cluster.yaml"
    user.parent.mkdir()

    project.write_text("ssh_target: project.example.org\n", encoding="utf-8")
    user.write_text("ssh_target: user.example.org\n", encoding="utf-8")

    check = FileContentCheck(
        paths=[project, user],
        pattern=r"ssh_target:\s+\S+",
    )
    result = await check.check()

    assert result.passed is True
    assert "project.example.org" in result.evidence
    assert "user.example.org" not in result.evidence


async def test_file_content_check_all_missing_fails_with_diagnostic(
    tmp_path,
) -> None:
    """Failure message must list each probed path so the user can see
    why -- 'pattern not in X; not found: Y' style diagnostics rather
    than a single bare path."""
    a = tmp_path / "a.yaml"
    b = tmp_path / "b.yaml"
    a.write_text("nope\n", encoding="utf-8")
    # b does NOT exist.

    check = FileContentCheck(paths=[a, b], pattern=r"ssh_target:")
    result = await check.check()

    assert result.passed is False
    assert "ssh_target:" in result.evidence
    assert str(a) in result.evidence
    assert str(b) in result.evidence


async def test_file_content_check_single_path_back_compat(tmp_path) -> None:
    """``path:`` form (the historical YAML shape) still works."""
    f = tmp_path / "file.yaml"
    f.write_text("ssh_target: example.org\n", encoding="utf-8")

    check = FileContentCheck(path=f, pattern=r"ssh_target:")
    result = await check.check()
    assert result.passed is True


def test_file_content_check_requires_pattern() -> None:
    """Empty pattern is meaningless -- raise rather than silently match
    every line."""
    with pytest.raises(ValueError, match="pattern"):
        FileContentCheck(path="foo", pattern="")


# ---------------------------------------------------------------------------
# Manifest registration smoke test -- the parser passes ``paths`` through
# ---------------------------------------------------------------------------


async def test_check_registry_passes_paths_through(tmp_path) -> None:
    """End-to-end: a YAML-style param dict with ``paths`` reaches the
    check class. Catches a regression where the registry lambdas drop
    the new key."""
    from claudechic.checks.builtins import _CHECK_REGISTRY

    a = tmp_path / "a.yaml"
    b = tmp_path / "b.yaml"
    b.write_text("ssh_target: example.org\n", encoding="utf-8")

    factory = _CHECK_REGISTRY["file-content-check"]
    check = factory(
        {
            "paths": [str(a), str(b)],
            "pattern": r"ssh_target:",
            "base_dir": str(tmp_path),
        }
    )

    result = await check.check()
    assert result.passed is True


async def test_check_registry_resolves_tilde_and_relative_for_paths(
    monkeypatch, tmp_path
) -> None:
    """The registry path resolves both ``~/...`` and bare-relative
    entries through ``_resolve_against``. End-to-end coverage for the
    cluster_setup advance-check shape:
        paths:
          - .claudechic/mcp_tools/cluster.yaml
          - ~/.claudechic/mcp_tools/cluster.yaml
    """
    from claudechic.checks.builtins import _CHECK_REGISTRY

    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))

    base_dir = tmp_path / "workflow_root"
    base_dir.mkdir()

    # Only the user-tier file exists -- mirrors the user's setup.
    user_yaml = home / ".claudechic" / "mcp_tools" / "cluster.yaml"
    user_yaml.parent.mkdir(parents=True)
    user_yaml.write_text("ssh_target: submit.int.janelia.org\n", encoding="utf-8")

    factory = _CHECK_REGISTRY["file-content-check"]
    check = factory(
        {
            "paths": [
                ".claudechic/mcp_tools/cluster.yaml",  # project tier (missing)
                "~/.claudechic/mcp_tools/cluster.yaml",  # user tier (exists)
            ],
            "pattern": r"ssh_target:\s+\S+",
            "base_dir": str(base_dir),
        }
    )
    result = await check.check()

    assert result.passed is True, (
        "tier-aware advance check failed to find user-tier config; "
        f"evidence: {result.evidence}"
    )
    assert "submit.int.janelia.org" in result.evidence
