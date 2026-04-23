"""Ensure os.killpg() and os.kill(SIGKILL) calls have platform guards.

os.killpg() does not exist on Windows. signal.SIGKILL does not exist on
Windows. Any call to these must be inside a ``sys.platform != "win32"``
guard or equivalent, otherwise the code will crash on Windows.

This test scans claudechic source files for unguarded calls.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

CLAUDECHIC_ROOT = Path(__file__).resolve().parent.parent / "claudechic"

# Patterns that are Windows-unsafe
KILL_PATTERNS = [
    re.compile(r"\bos\.killpg\s*\("),
    re.compile(r"\bos\.kill\s*\(.*SIGKILL"),
]

# What counts as a platform guard in surrounding context
GUARD_PATTERNS = [
    re.compile(r"""sys\.platform\s*[!=]=\s*["']win32["']"""),
    re.compile(r"\bplatform\.system\s*\(\)"),
]

# How many lines above the violation to search for a guard
GUARD_SEARCH_LINES = 30


def _collect_python_files() -> list[Path]:
    return sorted(CLAUDECHIC_ROOT.rglob("*.py"))


def _find_unguarded_kills(path: Path) -> list[tuple[int, str]]:
    """Find os.killpg/os.kill(SIGKILL) calls without a platform guard."""
    violations = []
    lines = path.read_text(encoding="utf-8").splitlines()

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue

        is_kill = any(p.search(line) for p in KILL_PATTERNS)
        if not is_kill:
            continue

        # Search backward for a platform guard
        start = max(0, i - GUARD_SEARCH_LINES)
        context = "\n".join(lines[start:i])
        has_guard = any(p.search(context) for p in GUARD_PATTERNS)

        if not has_guard:
            violations.append((i + 1, line.rstrip()))

    return violations


def test_no_unguarded_os_kill() -> None:
    """All os.killpg()/os.kill(SIGKILL) calls must have a platform guard."""
    all_violations: list[str] = []
    for path in _collect_python_files():
        for lineno, line in _find_unguarded_kills(path):
            rel = path.relative_to(CLAUDECHIC_ROOT.parent)
            all_violations.append(f"  {rel}:{lineno}: {line}")

    if all_violations:
        pytest.fail(
            f"Found {len(all_violations)} unguarded os.killpg/os.kill(SIGKILL) "
            f"call(s) -- will crash on Windows:\n"
            + "\n".join(all_violations)
            + "\n\nWrap in: if sys.platform != 'win32':"
        )
