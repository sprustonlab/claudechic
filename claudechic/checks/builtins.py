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


def _resolve_against(path: str | Path, base_dir: str | Path | None) -> Path:
    """Resolve ``path`` against ``base_dir`` if it is relative.

    Absolute paths are returned unchanged. This lets check manifests use
    relative paths (e.g. ``.project_team/*/SPECIFICATION.md``) while
    callers pin them to the workflow root. If ``base_dir`` is ``None``
    the value is returned as a bare ``Path`` (relative paths then
    resolve against the process cwd at access time).
    """
    p = Path(path)
    if p.is_absolute() or base_dir is None:
        return p
    return Path(base_dir) / p


class CommandOutputCheck:
    """Passes when command stdout matches regex.

    ``cwd`` pins the subprocess working directory. When the check is
    executed via :class:`WorkflowEngine`, the engine sets this to the
    workflow root (the main agent's cwd) so relative paths in the shell
    command resolve against a stable location -- not whatever the Python
    process happened to have as its cwd.
    """

    def __init__(
        self,
        command: str,
        pattern: str,
        cwd: str | Path | None = None,
    ) -> None:
        self.command = command
        self.compiled_pattern = re.compile(pattern)
        self.cwd = str(cwd) if cwd is not None else None

    async def check(self) -> CheckResult:
        try:
            proc = await asyncio.create_subprocess_shell(
                self.command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.cwd,
            )
            stdout_bytes, _ = await asyncio.wait_for(proc.communicate(), timeout=30.0)
            stdout = stdout_bytes.decode("utf-8", errors="replace")

            match = self.compiled_pattern.search(stdout)
            if match:
                return CheckResult(
                    passed=True, evidence=f"Pattern matched: {match.group(0)[:200]}"
                )
            excerpt = "\n".join(stdout.strip().splitlines()[:3])
            where = f" (cwd={self.cwd})" if self.cwd else ""
            return CheckResult(
                passed=False,
                evidence=f"Pattern '{self.compiled_pattern.pattern}' not found in output{where}: {excerpt}"[
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
    """Passes when file exists.

    ``base_dir`` pins relative ``path`` resolution to the workflow root
    so checks don't silently depend on process cwd.
    """

    def __init__(
        self,
        path: str | Path,
        base_dir: str | Path | None = None,
    ) -> None:
        self.path = _resolve_against(path, base_dir)

    async def check(self) -> CheckResult:
        if self.path.exists():
            return CheckResult(passed=True, evidence=f"File found: {self.path}")
        return CheckResult(passed=False, evidence=f"File not found: {self.path}")


class FileContentCheck:
    """Passes when file content matches regex.

    ``base_dir`` pins relative ``path`` resolution to the workflow root.
    """

    def __init__(
        self,
        path: str | Path,
        pattern: str,
        base_dir: str | Path | None = None,
    ) -> None:
        self.path = _resolve_against(path, base_dir)
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


class ArtifactDirReadyCheck:
    """Passes when the engine has an artifact directory bound.

    Reads ``engine.artifact_dir``. Returns failure when ``None`` (i.e.,
    ``set_artifact_dir`` has not yet been called for this run); success
    otherwise — whether the value came from a fresh ``set_artifact_dir``
    call or from a chicsession resume.

    The engine reference is injected at check-build time by
    ``WorkflowEngine._run_single_check`` so this leaf module does not
    import the engine class.
    """

    def __init__(self, engine: Any) -> None:
        self.engine = engine

    async def check(self) -> CheckResult:
        artifact_dir = getattr(self.engine, "artifact_dir", None)
        if artifact_dir is None:
            return CheckResult(
                passed=False,
                evidence=(
                    "Artifact directory not set — call "
                    "`set_artifact_dir(...)` MCP tool before advancing."
                ),
            )
        return CheckResult(passed=True, evidence=f"artifact_dir set: {artifact_dir}")


# ---------------------------------------------------------------------------
# Register built-in types at module level
# ---------------------------------------------------------------------------

register_check_type(
    "command-output-check",
    lambda p: CommandOutputCheck(
        command=p["command"], pattern=p["pattern"], cwd=p.get("cwd")
    ),
)
register_check_type(
    "file-exists-check",
    lambda p: FileExistsCheck(path=p["path"], base_dir=p.get("base_dir")),
)
register_check_type(
    "file-content-check",
    lambda p: FileContentCheck(
        path=p["path"], pattern=p["pattern"], base_dir=p.get("base_dir")
    ),
)
register_check_type(
    "manual-confirm",
    lambda p: ManualConfirm(
        question=p.get("question") or p.get("prompt", "Confirm?"),
        confirm_fn=p["confirm_fn"],
        context=p.get("context"),
    ),
)
register_check_type(
    "artifact-dir-ready-check",
    lambda p: ArtifactDirReadyCheck(engine=p["engine"]),
)
