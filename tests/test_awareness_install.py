"""Tests for ``claudechic.awareness_install`` (Group D §4.1, §4.2, §12.2.1).

Covers:
- INV-AW-1: enabled toggle copies every bundled doc, mkdir is idempotent
- INV-AW-2: disabled toggle performs zero file I/O (incl. no DELETE pass)
- INV-AW-3: every regular-file write basename matches ``claudechic_*.md``
- INV-AW-4: idempotent re-run yields all-SKIP
- INV-AW-5: ``ContextDocsDrift`` import raises; ``context_docs_outdated``
  hint absent from bundled hints.yaml
- INV-AW-10: orphan DELETE pass + non-prefix bystander + subdirectory
  recursion guard + toggle gating
- INV-AW-11: symlink guard — both per-bundled-file loop AND DELETE pass

Plus three additional symlink edge-case tests (per Skeptic2 mitigation):
- broken symlink (target nonexistent)
- symlink to a directory
- symlink loop

Tests use ``monkeypatch`` to redirect ``Path.home()`` and the module-level
``CLAUDE_RULES_DIR`` / ``CONFIG`` references at the awareness_install
module surface, so no real ``~/.claude/`` is touched.
"""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from claudechic import awareness_install
from claudechic.awareness_install import (
    INSTALL_PREFIX,
    InstallResult,
    install_awareness_rules,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_rules_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect awareness_install to write into ``tmp_path/.claude/rules/``.

    Patches the module-level ``CLAUDE_RULES_DIR`` constant so the install
    routine never touches the real ``~/.claude/`` namespace.
    """
    target = tmp_path / ".claude" / "rules"
    monkeypatch.setattr(awareness_install, "CLAUDE_RULES_DIR", target)
    return target


@pytest.fixture
def enabled_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force ``awareness.install`` toggle on for the test."""
    monkeypatch.setattr(awareness_install, "CONFIG", {"awareness": {"install": True}})


@pytest.fixture
def disabled_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force ``awareness.install`` toggle off for the test."""
    monkeypatch.setattr(awareness_install, "CONFIG", {"awareness": {"install": False}})


def _bundled_names() -> set[str]:
    """Names (stems) of bundled context docs."""
    return {p.stem for p in awareness_install.PKG_CONTEXT_DIR.glob("*.md")}


# ---------------------------------------------------------------------------
# INV-AW-1: enabled toggle installs every bundled doc; mkdir idempotent
# ---------------------------------------------------------------------------


def test_inv_aw_1_enabled_installs_all_bundled(
    tmp_rules_dir: Path, enabled_config: None
) -> None:
    """When enabled, every bundled doc is NEW-installed at the prefixed path."""
    assert not tmp_rules_dir.exists(), "Pre-condition: rules dir must be absent"

    result = install_awareness_rules()

    assert result.skipped_disabled is False
    bundled = _bundled_names()
    assert bundled, "Bundled catalog should be non-empty"
    assert set(result.new) == bundled
    assert result.updated == []
    assert result.skipped == []
    assert result.deleted == []

    # Every bundled name installed at the prefixed path
    assert tmp_rules_dir.is_dir(), "Install routine must mkdir the parent"
    for name in bundled:
        target = tmp_rules_dir / f"{INSTALL_PREFIX}{name}.md"
        assert target.is_file(), f"Missing install: {target}"
        bundled_path = awareness_install.PKG_CONTEXT_DIR / f"{name}.md"
        assert target.read_bytes() == bundled_path.read_bytes()

    # No unintended subdirectory creation
    children = list(tmp_rules_dir.iterdir())
    assert all(c.is_file() for c in children), "Routine must not create subdirs"


def test_inv_aw_1_mkdir_idempotent(tmp_rules_dir: Path, enabled_config: None) -> None:
    """``mkdir(parents=True, exist_ok=True)`` does not fail if rules dir exists."""
    tmp_rules_dir.mkdir(parents=True)

    # Should not raise
    install_awareness_rules()
    assert tmp_rules_dir.is_dir()


# ---------------------------------------------------------------------------
# INV-AW-2: disabled toggle performs ZERO file I/O
# ---------------------------------------------------------------------------


def test_inv_aw_2_disabled_no_file_io(
    tmp_rules_dir: Path, disabled_config: None
) -> None:
    """Disabled toggle returns ``skipped_disabled=True`` with zero file I/O."""
    # Pre-create an orphan to verify DELETE pass also doesn't fire
    tmp_rules_dir.mkdir(parents=True)
    orphan = tmp_rules_dir / f"{INSTALL_PREFIX}obsolete.md"
    orphan.write_text("orphan content", encoding="utf-8")

    with (
        patch.object(Path, "write_bytes") as mock_write,
        patch.object(Path, "write_text") as mock_write_text,
        patch.object(Path, "mkdir") as mock_mkdir,
        patch.object(Path, "unlink") as mock_unlink,
    ):
        result = install_awareness_rules()

    assert result.skipped_disabled is True
    assert result.new == []
    assert result.updated == []
    assert result.skipped == []
    assert result.deleted == []

    mock_write.assert_not_called()
    mock_write_text.assert_not_called()
    mock_mkdir.assert_not_called()
    mock_unlink.assert_not_called()

    # Orphan still on disk
    assert orphan.is_file(), "DELETE pass must NOT fire when disabled"


def test_inv_aw_2_disabled_force_overrides(
    tmp_rules_dir: Path, disabled_config: None
) -> None:
    """``force=True`` runs the install routine even when toggle is False."""
    result = install_awareness_rules(force=True)
    assert result.skipped_disabled is False
    assert set(result.new) == _bundled_names()


# ---------------------------------------------------------------------------
# INV-AW-3: every write basename matches claudechic_*.md
# ---------------------------------------------------------------------------


def test_inv_aw_3_all_writes_have_prefix(
    tmp_rules_dir: Path, enabled_config: None
) -> None:
    """Every regular-file write basename starts with ``claudechic_`` and ends with ``.md``."""
    install_awareness_rules()

    for child in tmp_rules_dir.iterdir():
        assert child.is_file()
        assert child.name.startswith(INSTALL_PREFIX), (
            f"Non-prefixed write: {child.name}"
        )
        assert child.suffix == ".md", f"Non-.md write: {child.name}"


# ---------------------------------------------------------------------------
# INV-AW-4: idempotent re-run yields all-SKIP
# ---------------------------------------------------------------------------


def test_inv_aw_4_idempotent_rerun(tmp_rules_dir: Path, enabled_config: None) -> None:
    """Second call after a successful install: all SKIP, nothing new/updated/deleted."""
    first = install_awareness_rules()
    assert set(first.new) == _bundled_names()

    second = install_awareness_rules()
    assert second.skipped_disabled is False
    assert second.new == []
    assert second.updated == []
    assert set(second.skipped) == _bundled_names()
    assert second.deleted == []


def test_inv_aw_4_update_branch(tmp_rules_dir: Path, enabled_config: None) -> None:
    """If a target file is mutated externally, second call UPDATEs it."""
    install_awareness_rules()
    bundled = _bundled_names()
    pick = sorted(bundled)[0]
    target = tmp_rules_dir / f"{INSTALL_PREFIX}{pick}.md"
    target.write_text("USER-EDITED CONTENT (will be clobbered)", encoding="utf-8")

    result = install_awareness_rules()
    assert pick in result.updated
    bundled_path = awareness_install.PKG_CONTEXT_DIR / f"{pick}.md"
    assert target.read_bytes() == bundled_path.read_bytes()


# ---------------------------------------------------------------------------
# INV-AW-5: ContextDocsDrift removed; context_docs_outdated absent
# ---------------------------------------------------------------------------


def test_inv_aw_5_context_docs_drift_removed() -> None:
    """``from claudechic.hints.triggers import ContextDocsDrift`` raises ImportError."""
    with pytest.raises(ImportError):
        from claudechic.hints.triggers import ContextDocsDrift  # noqa: F401


def test_inv_aw_5_context_docs_outdated_hint_removed() -> None:
    """``context_docs_outdated`` hint absent from bundled global hints.yaml."""
    pkg_root = Path(awareness_install.__file__).parent
    hints_path = pkg_root / "defaults" / "global" / "hints.yaml"
    assert hints_path.is_file()
    data = yaml.safe_load(hints_path.read_text(encoding="utf-8")) or []
    ids = [entry.get("id") for entry in data if isinstance(entry, dict)]
    assert "context_docs_outdated" not in ids
    # Also assert no entry has a context-docs-drift trigger
    for entry in data:
        trig = entry.get("trigger") if isinstance(entry, dict) else None
        if isinstance(trig, dict):
            assert trig.get("type") != "context-docs-drift"


# ---------------------------------------------------------------------------
# INV-AW-10: orphan DELETE pass — bounded by basename, no recursion, gated
# ---------------------------------------------------------------------------


def test_inv_aw_10_orphan_unlinked(tmp_rules_dir: Path, enabled_config: None) -> None:
    """Pre-existing ``claudechic_obsolete.md`` (not in bundled catalog) is deleted."""
    tmp_rules_dir.mkdir(parents=True)
    orphan = tmp_rules_dir / f"{INSTALL_PREFIX}obsolete.md"
    orphan.write_text("stale", encoding="utf-8")

    result = install_awareness_rules()
    assert "obsolete" in result.deleted
    assert not orphan.exists()


def test_inv_aw_10_non_prefix_bystander_untouched(
    tmp_rules_dir: Path, enabled_config: None
) -> None:
    """Files whose basename does NOT start with ``claudechic_`` are left alone."""
    tmp_rules_dir.mkdir(parents=True)
    foreign = tmp_rules_dir / "foo.md"
    foreign.write_text("user-owned", encoding="utf-8")

    install_awareness_rules()
    assert foreign.is_file(), "Non-prefix file must not be touched"
    assert foreign.read_text(encoding="utf-8") == "user-owned"


def test_inv_aw_10_no_subdirectory_recursion(
    tmp_rules_dir: Path, enabled_config: None
) -> None:
    """DELETE pass does not recurse into subdirectories of ``~/.claude/rules/``."""
    tmp_rules_dir.mkdir(parents=True)
    subdir = tmp_rules_dir / "subdir"
    subdir.mkdir()
    nested = subdir / f"{INSTALL_PREFIX}x.md"
    nested.write_text("nested", encoding="utf-8")

    install_awareness_rules()
    assert nested.is_file(), "Subdirectory contents must not be touched"


def test_inv_aw_10_delete_pass_gated_by_toggle(
    tmp_rules_dir: Path, disabled_config: None
) -> None:
    """When ``awareness.install=False``, DELETE pass MUST NOT fire even if orphans exist."""
    tmp_rules_dir.mkdir(parents=True)
    orphan = tmp_rules_dir / f"{INSTALL_PREFIX}obsolete.md"
    orphan.write_text("stale", encoding="utf-8")

    result = install_awareness_rules()
    assert result.skipped_disabled is True
    assert orphan.is_file(), "Orphan must remain when disabled"


# ---------------------------------------------------------------------------
# INV-AW-11: symlink guard — never read/write/unlink a symlink
# ---------------------------------------------------------------------------


def test_inv_aw_11_symlink_target_untouched(
    tmp_rules_dir: Path,
    enabled_config: None,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Symlink at a bundled-name path: link unchanged, target unchanged, name omitted."""
    # Pick a bundled name whose target the symlink will shadow
    bundled = sorted(_bundled_names())
    assert bundled, "Bundled catalog non-empty"
    name = bundled[0]

    # External target file (outside rules dir)
    external = tmp_path / "notes" / "important.md"
    external.parent.mkdir(parents=True)
    external_content = "USER NOTES — DO NOT TOUCH"
    external.write_text(external_content, encoding="utf-8")

    tmp_rules_dir.mkdir(parents=True)
    link = tmp_rules_dir / f"{INSTALL_PREFIX}{name}.md"
    link.symlink_to(external)

    with caplog.at_level(logging.WARNING, logger="claudechic"):
        result = install_awareness_rules()

    assert link.is_symlink(), "Symlink must remain"
    # Compare resolved paths -- on Windows ``readlink()`` may return a
    # normalized form (long-path prefix, drive-letter casing, separators)
    # that differs from the literal ``external`` Path.  Resolving both
    # sides reduces to the same target.
    assert link.readlink().resolve() == external.resolve(), (
        "Symlink target unchanged"
    )
    assert external.read_text(encoding="utf-8") == external_content
    assert name not in result.new
    assert name not in result.updated
    assert name not in result.skipped
    assert name not in result.deleted
    assert any("symlink" in rec.message.lower() for rec in caplog.records)


def test_inv_aw_11_symlink_orphan_not_unlinked(
    tmp_rules_dir: Path, enabled_config: None, tmp_path: Path
) -> None:
    """Symlink at an orphan-name path is NOT unlinked by the DELETE pass."""
    external = tmp_path / "user_owned.md"
    external.write_text("user", encoding="utf-8")

    tmp_rules_dir.mkdir(parents=True)
    orphan_link = tmp_rules_dir / f"{INSTALL_PREFIX}orphan_via_link.md"
    orphan_link.symlink_to(external)

    result = install_awareness_rules()

    assert orphan_link.is_symlink(), "Symlink at orphan path must remain"
    assert "orphan_via_link" not in result.deleted


# ---------------------------------------------------------------------------
# Skeptic2 mitigation: three additional symlink edge-case tests
# ---------------------------------------------------------------------------


def test_symlink_to_nonexistent_target_skipped(
    tmp_rules_dir: Path, enabled_config: None, tmp_path: Path
) -> None:
    """Broken symlink (target does not exist) is skipped, not crashed-on."""
    bundled = sorted(_bundled_names())
    name = bundled[0]

    nonexistent = tmp_path / "nonexistent_dir" / "missing.md"

    tmp_rules_dir.mkdir(parents=True)
    link = tmp_rules_dir / f"{INSTALL_PREFIX}{name}.md"
    link.symlink_to(nonexistent)
    assert link.is_symlink()
    assert not link.exists(), "Pre-condition: link is broken"

    # Should not raise
    result = install_awareness_rules()

    assert link.is_symlink(), "Broken symlink must remain in place"
    assert name not in result.new
    assert name not in result.updated
    assert name not in result.skipped


def test_symlink_to_directory_skipped(
    tmp_rules_dir: Path, enabled_config: None, tmp_path: Path
) -> None:
    """Symlink whose target is a directory is skipped — never read/written/unlinked."""
    bundled = sorted(_bundled_names())
    name = bundled[0]

    dir_target = tmp_path / "user_dir"
    dir_target.mkdir()
    sentinel = dir_target / "sentinel.txt"
    sentinel.write_text("dir-content", encoding="utf-8")

    tmp_rules_dir.mkdir(parents=True)
    link = tmp_rules_dir / f"{INSTALL_PREFIX}{name}.md"
    link.symlink_to(dir_target)
    assert link.is_symlink()

    # Should not raise
    result = install_awareness_rules()

    assert link.is_symlink(), "Directory symlink must remain"
    assert dir_target.is_dir(), "Target directory unchanged"
    assert sentinel.read_text(encoding="utf-8") == "dir-content"
    assert name not in result.new
    assert name not in result.updated
    assert name not in result.skipped


def test_symlink_loop_skipped(tmp_rules_dir: Path, enabled_config: None) -> None:
    """Symlink loop is skipped — never followed."""
    bundled = sorted(_bundled_names())
    name = bundled[0]

    tmp_rules_dir.mkdir(parents=True)
    link_a = tmp_rules_dir / f"{INSTALL_PREFIX}{name}.md"
    link_b = tmp_rules_dir / f"{INSTALL_PREFIX}{name}_loop.md"

    # a -> b -> a
    link_a.symlink_to(link_b)
    link_b.symlink_to(link_a)
    assert link_a.is_symlink() and link_b.is_symlink()

    # Should not raise (the symlink guard short-circuits before any follow)
    result = install_awareness_rules()

    assert link_a.is_symlink(), "Loop link a must remain"
    assert link_b.is_symlink(), "Loop link b must remain"
    assert name not in result.new
    assert name not in result.updated
    assert name not in result.skipped
    # link_b's stem (after prefix removal) is "<name>_loop" which is NOT in
    # the bundled catalog and is a symlink — DELETE pass must skip too.
    assert f"{name}_loop" not in result.deleted


# ---------------------------------------------------------------------------
# Result-shape sanity check
# ---------------------------------------------------------------------------


def test_install_result_has_five_fields() -> None:
    """``InstallResult`` carries exactly the five fields named in SPEC §4.1."""
    r = InstallResult()
    assert r.new == []
    assert r.updated == []
    assert r.skipped == []
    assert r.deleted == []
    assert r.skipped_disabled is False
    # Dataclass field count
    from dataclasses import fields

    names = {f.name for f in fields(InstallResult)}
    assert names == {"new", "updated", "skipped", "deleted", "skipped_disabled"}
