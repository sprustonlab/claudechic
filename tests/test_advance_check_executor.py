"""Advance-check executor tests (Component A sub-units A3 + A4).

A3: engine cwd is the default for command/file-check resolution; a
manifest-supplied ``cwd`` / ``base_dir`` overrides it.

A4: ``WorkflowEngine.attempt_phase_advance`` runs all auto checks
before any ``manual-confirm`` check, regardless of declaration order.
Short-circuit semantics are preserved (AND across the combined
sequence; first failure wins).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest
from claudechic.checks.protocol import CheckDecl
from claudechic.workflows.engine import WorkflowEngine, WorkflowManifest
from claudechic.workflows.phases import Phase

pytestmark = [pytest.mark.fast, pytest.mark.asyncio]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_engine(
    *,
    cwd: Path | None = None,
    phases: list[Phase] | None = None,
    confirm_callback: Any = None,
) -> WorkflowEngine:
    """Build a ``WorkflowEngine`` with sensible defaults for these tests."""
    if phases is None:
        phases = [
            Phase(id="proj:setup", namespace="proj", file="setup.md"),
            Phase(id="proj:work", namespace="proj", file="work.md"),
        ]
    manifest = WorkflowManifest(workflow_id="proj", phases=phases)
    persist = AsyncMock()
    confirm = (
        confirm_callback
        if confirm_callback is not None
        else AsyncMock(return_value=True)
    )
    return WorkflowEngine(manifest, persist, confirm, cwd=cwd)


# ---------------------------------------------------------------------------
# A3 -- engine cwd default applied to command-output-check
# ---------------------------------------------------------------------------


async def test_a3_engine_cwd_default_applied_to_command_output_check(
    tmp_path: Path,
) -> None:
    """When the manifest omits ``cwd``, the engine's cwd is applied as default.

    The command runs ``pwd`` in the subprocess and we assert the engine's
    cwd appears in the captured stdout -- proves the engine pinned the
    subprocess working directory rather than letting it inherit the
    Python process cwd.
    """
    engine = _make_engine(cwd=tmp_path)
    decl = CheckDecl(
        id="proj:setup:advance:0",
        namespace="proj",
        type="command-output-check",
        params={
            "command": "pwd",
            "pattern": str(tmp_path.resolve()),
        },
    )
    result = await engine._run_single_check(decl)
    assert result.passed is True, result.evidence


async def test_a3_manifest_cwd_overrides_engine_cwd_for_command_output_check(
    tmp_path: Path,
) -> None:
    """A manifest-supplied ``cwd`` wins over the engine cwd default.

    Engine cwd is ``tmp_path``; manifest pins to a sibling ``other`` dir.
    ``pwd`` must report the manifest cwd, never the engine cwd.
    """
    other = tmp_path / "other"
    other.mkdir()
    engine = _make_engine(cwd=tmp_path)

    decl = CheckDecl(
        id="proj:setup:advance:1",
        namespace="proj",
        type="command-output-check",
        params={
            "command": "pwd",
            "pattern": str(other.resolve()),
            "cwd": str(other),
        },
    )
    result = await engine._run_single_check(decl)
    assert result.passed is True, result.evidence


async def test_a3_engine_cwd_unset_does_not_pin_command_check(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the engine has no cwd, no default is injected.

    The manifest also omits ``cwd``; the underlying ``CommandOutputCheck``
    therefore inherits the Python process cwd. We pin process cwd to
    ``tmp_path`` via monkeypatch and assert ``pwd`` reports it -- proving
    the engine did NOT rewrite ``params['cwd']`` when its own cwd is
    ``None``.
    """
    monkeypatch.chdir(tmp_path)
    engine = _make_engine(cwd=None)
    decl = CheckDecl(
        id="proj:setup:advance:2",
        namespace="proj",
        type="command-output-check",
        params={
            "command": "pwd",
            "pattern": str(tmp_path.resolve()),
        },
    )
    result = await engine._run_single_check(decl)
    assert result.passed is True, result.evidence


# ---------------------------------------------------------------------------
# A3 -- engine cwd default applied to file-exists-check
# ---------------------------------------------------------------------------


async def test_a3_engine_cwd_default_applied_to_file_exists_check(
    tmp_path: Path,
) -> None:
    """Relative ``path`` resolves against engine cwd via injected ``base_dir``."""
    (tmp_path / "PRESENT.txt").write_text("hi", encoding="utf-8")
    engine = _make_engine(cwd=tmp_path)

    decl = CheckDecl(
        id="proj:setup:advance:0",
        namespace="proj",
        type="file-exists-check",
        params={"path": "PRESENT.txt"},
    )
    result = await engine._run_single_check(decl)
    assert result.passed is True, result.evidence


async def test_a3_manifest_base_dir_overrides_engine_cwd_for_file_exists_check(
    tmp_path: Path,
) -> None:
    """A manifest-supplied ``base_dir`` wins over the engine cwd default."""
    other = tmp_path / "other"
    other.mkdir()
    (other / "PRESENT.txt").write_text("hi", encoding="utf-8")

    # File is NOT at engine cwd; only at the manifest-supplied base_dir.
    engine = _make_engine(cwd=tmp_path)
    decl = CheckDecl(
        id="proj:setup:advance:1",
        namespace="proj",
        type="file-exists-check",
        params={"path": "PRESENT.txt", "base_dir": str(other)},
    )
    result = await engine._run_single_check(decl)
    assert result.passed is True, result.evidence


async def test_a3_engine_cwd_default_does_not_apply_to_absolute_path(
    tmp_path: Path,
) -> None:
    """Absolute ``path`` is unaffected by the engine cwd default.

    The engine still injects ``base_dir`` via ``setdefault``, but the
    underlying ``FileExistsCheck`` uses ``_resolve_against`` which leaves
    absolute paths unchanged.
    """
    target = tmp_path / "deep" / "ABSOLUTE.txt"
    target.parent.mkdir(parents=True)
    target.write_text("hi", encoding="utf-8")

    other = tmp_path / "different_root"
    other.mkdir()
    engine = _make_engine(cwd=other)

    decl = CheckDecl(
        id="proj:setup:advance:2",
        namespace="proj",
        type="file-exists-check",
        params={"path": str(target)},
    )
    result = await engine._run_single_check(decl)
    assert result.passed is True, result.evidence


# ---------------------------------------------------------------------------
# A3 -- engine cwd default applied to file-content-check
# ---------------------------------------------------------------------------


async def test_a3_engine_cwd_default_applied_to_file_content_check(
    tmp_path: Path,
) -> None:
    """Relative ``path`` of a content check resolves against engine cwd."""
    (tmp_path / "DOC.md").write_text("hello world\nfoo bar\n", encoding="utf-8")
    engine = _make_engine(cwd=tmp_path)

    decl = CheckDecl(
        id="proj:setup:advance:0",
        namespace="proj",
        type="file-content-check",
        params={"path": "DOC.md", "pattern": "hello"},
    )
    result = await engine._run_single_check(decl)
    assert result.passed is True, result.evidence


async def test_a3_manifest_base_dir_overrides_engine_cwd_for_file_content_check(
    tmp_path: Path,
) -> None:
    """A manifest-supplied ``base_dir`` wins for ``file-content-check`` too."""
    other = tmp_path / "other"
    other.mkdir()
    (other / "DOC.md").write_text("hello world\n", encoding="utf-8")

    engine = _make_engine(cwd=tmp_path)
    decl = CheckDecl(
        id="proj:setup:advance:1",
        namespace="proj",
        type="file-content-check",
        params={
            "path": "DOC.md",
            "pattern": "hello",
            "base_dir": str(other),
        },
    )
    result = await engine._run_single_check(decl)
    assert result.passed is True, result.evidence


# ---------------------------------------------------------------------------
# A4 -- two-pass executor: auto checks before manual checks
# ---------------------------------------------------------------------------


async def test_a4_auto_checks_run_before_manual_checks_regardless_of_order(
    tmp_path: Path,
) -> None:
    """When all checks pass, the auto pass executes before the manual pass
    even if ``manual-confirm`` is declared first in the advance-checks list.

    The auto check stamps a sentinel file; the manual-confirm callback
    records whether the sentinel is present by the time it fires. In a
    naive single-pass executor (declaration order), the manual callback
    would fire BEFORE the auto check ran -- the sentinel would be
    missing. With two-pass ordering, the sentinel must be present.
    """
    sentinel = tmp_path / "AUTO_RAN"
    seen_sentinel: list[bool] = []

    async def confirm(question: str, context: dict[str, Any] | None = None) -> bool:
        seen_sentinel.append(sentinel.exists())
        return True

    engine = _make_engine(cwd=tmp_path, confirm_callback=confirm)

    auto = CheckDecl(
        id="proj:setup:advance:auto",
        namespace="proj",
        type="command-output-check",
        params={
            "command": f'touch "{sentinel}" && echo OK',
            "pattern": "OK",
        },
    )
    manual = CheckDecl(
        id="proj:setup:advance:manual",
        namespace="proj",
        type="manual-confirm",
        params={"question": "Confirm?"},
    )

    # Manual declared first; auto second. Two-pass must reorder.
    result = await engine.attempt_phase_advance(
        "proj",
        "proj:setup",
        "proj:work",
        [manual, auto],
    )

    assert result.success is True, result.reason
    assert seen_sentinel == [True], (
        "manual-confirm callback fired before the auto check stamped the "
        "sentinel -- two-pass ordering is not enforced"
    )


async def test_a4_failing_auto_check_short_circuits_before_manual_prompt(
    tmp_path: Path,
) -> None:
    """A failing auto check stops the advance before the manual prompt fires.

    Even though the ``manual-confirm`` check is declared first, two-pass
    ordering plus AND-semantics short-circuit means the manual callback
    is never invoked when an auto check is going to fail.
    """
    confirm_calls: list[str] = []

    async def confirm(question: str, context: dict[str, Any] | None = None) -> bool:
        confirm_calls.append(question)
        return True

    engine = _make_engine(cwd=tmp_path, confirm_callback=confirm)

    failing_auto = CheckDecl(
        id="proj:setup:advance:fail",
        namespace="proj",
        type="file-exists-check",
        params={"path": "DOES_NOT_EXIST.txt"},
    )
    manual = CheckDecl(
        id="proj:setup:advance:manual",
        namespace="proj",
        type="manual-confirm",
        params={"question": "Confirm?"},
    )

    result = await engine.attempt_phase_advance(
        "proj",
        "proj:setup",
        "proj:work",
        [manual, failing_auto],
    )

    assert result.success is False
    assert result.failed_check_id == "proj:setup:advance:fail"
    assert confirm_calls == [], (
        "manual-confirm callback must not fire when an auto check fails"
    )


async def test_a4_multiple_autos_run_before_any_manual(tmp_path: Path) -> None:
    """All auto checks run before any manual check, in original auto order.

    Two auto checks (both passing) interleaved with two manual checks in
    declaration order. The first manual callback must observe both auto
    side effects.
    """
    sentinel_a = tmp_path / "A_RAN"
    sentinel_b = tmp_path / "B_RAN"

    confirm_observations: list[tuple[bool, bool]] = []

    async def confirm(question: str, context: dict[str, Any] | None = None) -> bool:
        confirm_observations.append((sentinel_a.exists(), sentinel_b.exists()))
        return True

    engine = _make_engine(cwd=tmp_path, confirm_callback=confirm)

    auto_a = CheckDecl(
        id="proj:setup:advance:auto-a",
        namespace="proj",
        type="command-output-check",
        params={"command": f'touch "{sentinel_a}" && echo OK', "pattern": "OK"},
    )
    auto_b = CheckDecl(
        id="proj:setup:advance:auto-b",
        namespace="proj",
        type="command-output-check",
        params={"command": f'touch "{sentinel_b}" && echo OK', "pattern": "OK"},
    )
    manual_1 = CheckDecl(
        id="proj:setup:advance:manual-1",
        namespace="proj",
        type="manual-confirm",
        params={"question": "First?"},
    )
    manual_2 = CheckDecl(
        id="proj:setup:advance:manual-2",
        namespace="proj",
        type="manual-confirm",
        params={"question": "Second?"},
    )

    result = await engine.attempt_phase_advance(
        "proj",
        "proj:setup",
        "proj:work",
        [manual_1, auto_a, manual_2, auto_b],
    )

    assert result.success is True, result.reason
    # Both manual confirms saw both auto sentinels already in place.
    assert confirm_observations == [(True, True), (True, True)]


async def test_a4_manual_check_only_runs_when_all_autos_pass(
    tmp_path: Path,
) -> None:
    """If any auto check fails, no manual check runs even if some autos pass."""
    confirm_calls: list[str] = []

    async def confirm(question: str, context: dict[str, Any] | None = None) -> bool:
        confirm_calls.append(question)
        return True

    engine = _make_engine(cwd=tmp_path, confirm_callback=confirm)

    passing_auto = CheckDecl(
        id="proj:setup:advance:pass",
        namespace="proj",
        type="command-output-check",
        params={"command": "echo OK", "pattern": "OK"},
    )
    failing_auto = CheckDecl(
        id="proj:setup:advance:fail",
        namespace="proj",
        type="file-exists-check",
        params={"path": "MISSING.txt"},
    )
    manual = CheckDecl(
        id="proj:setup:advance:manual",
        namespace="proj",
        type="manual-confirm",
        params={"question": "Confirm?"},
    )

    result = await engine.attempt_phase_advance(
        "proj",
        "proj:setup",
        "proj:work",
        [passing_auto, manual, failing_auto],
    )

    assert result.success is False
    assert result.failed_check_id == "proj:setup:advance:fail"
    assert confirm_calls == []


async def test_a4_all_manual_no_auto_executes_in_declaration_order(
    tmp_path: Path,
) -> None:
    """When the advance list is all manual-confirm, declaration order is
    preserved (the auto pass is empty and the manual pass runs as-is).
    """
    seen: list[str] = []

    async def confirm(question: str, context: dict[str, Any] | None = None) -> bool:
        seen.append(question)
        return True

    engine = _make_engine(cwd=tmp_path, confirm_callback=confirm)

    m1 = CheckDecl(
        id="proj:setup:advance:m1",
        namespace="proj",
        type="manual-confirm",
        params={"question": "First?"},
    )
    m2 = CheckDecl(
        id="proj:setup:advance:m2",
        namespace="proj",
        type="manual-confirm",
        params={"question": "Second?"},
    )

    result = await engine.attempt_phase_advance(
        "proj",
        "proj:setup",
        "proj:work",
        [m1, m2],
    )

    assert result.success is True, result.reason
    assert seen == ["First?", "Second?"]


async def test_a4_no_auto_no_manual_advances_immediately(tmp_path: Path) -> None:
    """An empty advance-checks list advances unconditionally."""
    engine = _make_engine(cwd=tmp_path)
    result = await engine.attempt_phase_advance(
        "proj",
        "proj:setup",
        "proj:work",
        [],
    )
    assert result.success is True
    assert engine.get_current_phase() == "proj:work"
