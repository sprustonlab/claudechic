"""Ensure all claudechic source files use explicit encoding on file I/O.

On Windows, Python defaults to the system codepage (e.g. cp1252), not UTF-8.
Bare read_text() / write_text() / open() / aiofiles.open() calls work on
Linux/macOS but break on Windows for any file with non-ASCII characters.

This test scans the entire claudechic/ source tree and fails if any bare
calls are found.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

CLAUDECHIC_ROOT = Path(__file__).resolve().parent.parent / "claudechic"

# Files to skip
SKIP_FILES = {
    "test_encoding_static.py",
}


def _collect_python_files() -> list[Path]:
    """Collect all .py files under claudechic/."""
    return sorted(f for f in CLAUDECHIC_ROOT.rglob("*.py") if f.name not in SKIP_FILES)


def _is_code_line(line: str) -> bool:
    """Return True if line contains executable code (not comment/string)."""
    stripped = line.strip()
    if stripped.startswith("#"):
        return False
    if stripped.startswith(('"""', "'''", '"', "'")):
        return False
    return True


def _find_bare_read_text(path: Path) -> list[tuple[int, str]]:
    """Find .read_text() calls missing encoding parameter."""
    violations = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not _is_code_line(line):
            continue
        if ".read_text()" in line:
            violations.append((i, line.rstrip()))
    return violations


def _find_bare_write_text(path: Path) -> list[tuple[int, str]]:
    """Find .write_text(...) calls missing encoding parameter."""
    violations = []
    lines = path.read_text(encoding="utf-8").splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not _is_code_line(line):
            i += 1
            continue
        if ".write_text(" in line:
            full_call = line
            paren_depth = line.count("(") - line.count(")")
            j = i + 1
            while paren_depth > 0 and j < len(lines):
                full_call += "\n" + lines[j]
                paren_depth += lines[j].count("(") - lines[j].count(")")
                j += 1
            if "encoding" not in full_call:
                violations.append((i + 1, line.rstrip()))
        i += 1
    return violations


def _find_bare_open(path: Path) -> list[tuple[int, str]]:
    """Find open()/aiofiles.open() in text mode missing encoding."""
    violations = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not _is_code_line(line):
            continue
        if re.search(r"\bopen\s*\(", line) and "encoding" not in line:
            # Skip binary mode
            if re.search(r"""["'][rwax]+b["']""", line):
                continue
            # Skip mode="rb" / mode="wb"
            if re.search(r"""mode\s*=\s*["'][rwax]*b""", line):
                continue
            # Skip os.devnull (no encoding needed)
            if "devnull" in line:
                continue
            violations.append((i, line.rstrip()))
    return violations


@pytest.fixture(scope="module")
def python_files() -> list[Path]:
    files = _collect_python_files()
    assert files, "No Python files found under claudechic/"
    return files


def test_no_bare_read_text(python_files: list[Path]) -> None:
    """All .read_text() calls must specify encoding='utf-8'."""
    all_violations: list[str] = []
    for path in python_files:
        for lineno, line in _find_bare_read_text(path):
            rel = path.relative_to(CLAUDECHIC_ROOT.parent)
            all_violations.append(f"  {rel}:{lineno}: {line}")

    if all_violations:
        pytest.fail(
            f"Found {len(all_violations)} bare .read_text() call(s) "
            f"missing encoding='utf-8':\n" + "\n".join(all_violations)
        )


def test_no_bare_write_text(python_files: list[Path]) -> None:
    """All .write_text() calls must specify encoding='utf-8'."""
    all_violations: list[str] = []
    for path in python_files:
        for lineno, line in _find_bare_write_text(path):
            rel = path.relative_to(CLAUDECHIC_ROOT.parent)
            all_violations.append(f"  {rel}:{lineno}: {line}")

    if all_violations:
        pytest.fail(
            f"Found {len(all_violations)} bare .write_text() call(s) "
            f"missing encoding='utf-8':\n" + "\n".join(all_violations)
        )


def test_no_bare_open(python_files: list[Path]) -> None:
    """All text-mode open()/aiofiles.open() calls must specify encoding."""
    all_violations: list[str] = []
    for path in python_files:
        for lineno, line in _find_bare_open(path):
            rel = path.relative_to(CLAUDECHIC_ROOT.parent)
            all_violations.append(f"  {rel}:{lineno}: {line}")

    if all_violations:
        pytest.fail(
            f"Found {len(all_violations)} bare open() call(s) "
            f"missing encoding='utf-8':\n" + "\n".join(all_violations)
        )
