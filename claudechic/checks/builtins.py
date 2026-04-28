"""Built-in check types and registry."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from claudechic.checks.protocol import (
    AsyncConfirmCallback,
    Check,
    CheckDecl,
    CheckResult,
)

_CHECK_REGISTRY: dict[str, Callable[[dict], Check]] = {}


def register_check_type(name: str, factory: Callable[[dict], Check]) -> None:
    """Register a check type factory by name."""
    _CHECK_REGISTRY[name] = factory


def _build_check(decl: CheckDecl) -> Check:
    """Map CheckDecl to Check objects via registry."""
    factory = _CHECK_REGISTRY.get(decl.type)
    if factory is None:
        raise ValueError(f"Unknown check type: {decl.type}")
    return factory(decl.params)


# ---------------------------------------------------------------------------
# Built-in check types
# ---------------------------------------------------------------------------


class CommandOutputCheck:
    """Passes when command stdout matches regex."""

    def __init__(self, command: str, pattern: str) -> None:
        self.command = command
        self.compiled_pattern = re.compile(pattern)

    async def check(self) -> CheckResult:
        try:
            proc = await asyncio.create_subprocess_shell(
                self.command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_bytes, _ = await asyncio.wait_for(proc.communicate(), timeout=30.0)
            stdout = stdout_bytes.decode("utf-8", errors="replace")

            match = self.compiled_pattern.search(stdout)
            if match:
                return CheckResult(
                    passed=True, evidence=f"Pattern matched: {match.group(0)[:200]}"
                )
            excerpt = "\n".join(stdout.strip().splitlines()[:3])
            return CheckResult(
                passed=False,
                evidence=f"Pattern '{self.compiled_pattern.pattern}' not found in output: {excerpt}"[
                    :300
                ],
            )
        except asyncio.TimeoutError:
            return CheckResult(
                passed=False, evidence=f"Command timed out after 30s: {self.command}"
            )
        except OSError as e:
            return CheckResult(passed=False, evidence=f"Command failed: {e}")


class FileExistsCheck:
    """Passes when file exists."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    async def check(self) -> CheckResult:
        if self.path.exists():
            return CheckResult(passed=True, evidence=f"File found: {self.path}")
        return CheckResult(passed=False, evidence=f"File not found: {self.path}")


class FileContentCheck:
    """Passes when file content matches regex."""

    def __init__(self, path: str | Path, pattern: str) -> None:
        self.path = Path(path)
        self.compiled_pattern = re.compile(pattern)

    async def check(self) -> CheckResult:
        if not self.path.exists():
            return CheckResult(passed=False, evidence=f"File not found: {self.path}")
        try:
            content = self.path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            return CheckResult(passed=False, evidence=f"Cannot read {self.path}: {e}")

        for i, line in enumerate(content.splitlines(), 1):
            if self.compiled_pattern.search(line):
                return CheckResult(
                    passed=True, evidence=f"Line {i}: {line.strip()}"[:200]
                )

        return CheckResult(
            passed=False,
            evidence=f"Pattern '{self.compiled_pattern.pattern}' not found in {self.path}",
        )


class ManualConfirm:
    """Passes when user confirms via injected callback.

    The ONLY check type requiring user interaction. Receives an
    AsyncConfirmCallback at construction -- never sees the TUI.
    """

    def __init__(
        self,
        question: str,
        confirm_fn: AsyncConfirmCallback,
        context: dict[str, Any] | None = None,
    ) -> None:
        self.question = question
        self.confirm_fn = confirm_fn
        self.context = context

    async def check(self) -> CheckResult:
        try:
            confirmed = await self.confirm_fn(self.question, self.context)
            if confirmed:
                return CheckResult(passed=True, evidence="User confirmed")
            return CheckResult(passed=False, evidence="User declined")
        except Exception as e:
            return CheckResult(passed=False, evidence=f"Confirmation failed: {e}")


# ---------------------------------------------------------------------------
# Register built-in types at module level
# ---------------------------------------------------------------------------

register_check_type(
    "command-output-check",
    lambda p: CommandOutputCheck(command=p["command"], pattern=p["pattern"]),
)
register_check_type(
    "file-exists-check",
    lambda p: FileExistsCheck(path=p["path"]),
)
register_check_type(
    "file-content-check",
    lambda p: FileContentCheck(path=p["path"], pattern=p["pattern"]),
)
register_check_type(
    "manual-confirm",
    lambda p: ManualConfirm(
        question=p.get("question") or p.get("prompt", "Confirm?"),
        confirm_fn=p["confirm_fn"],
        context=p.get("context"),
    ),
)
