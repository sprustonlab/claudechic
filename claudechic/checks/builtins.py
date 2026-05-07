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

    Order:
    1. ``~`` and ``~user`` are expanded first via ``Path.expanduser`` so
       a manifest entry like ``~/.claudechic/mcp_tools/cluster.yaml``
       resolves to the user's home dir, not ``<cwd>/~/.claudechic/...``
       (a Path with a literal ``~`` segment is NOT considered absolute,
       so the original implementation joined it onto ``base_dir`` --
       silently broken).
    2. After expansion, absolute paths are returned unchanged. This
       lets check manifests use relative paths (e.g.
       ``.project_team/*/SPECIFICATION.md``) while callers pin them
       to the workflow root.
    3. Relative paths are joined onto ``base_dir`` if it is set;
       otherwise returned as-is (so they resolve against the process
       cwd at access time).
    """
    p = Path(path).expanduser()
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


def _coerce_paths(
    path: str | Path | None,
    paths: list[str | Path] | None,
    base_dir: str | Path | None,
) -> list[Path]:
    """Build the list of resolved paths a check should walk.

    Accepts either ``path`` (single, the historical form) or ``paths``
    (a list, for tier-aware checks like cluster_setup that need to
    accept e.g. ``<cwd>/.claudechic/mcp_tools/cluster.yaml`` OR
    ``~/.claudechic/mcp_tools/cluster.yaml``). The two are mutually
    exclusive at the manifest level, but if a caller supplies both
    we concatenate ``[path] + paths`` so neither is silently dropped.
    Each entry passes through :func:`_resolve_against` for ``~``
    expansion and base_dir joining.

    The resulting list preserves declaration order. Both
    :class:`FileExistsCheck` and :class:`FileContentCheck` use it
    with first-match-wins semantics: the first path that satisfies
    the check makes the check pass.
    """
    raw: list[str | Path] = []
    if path is not None:
        raw.append(path)
    if paths is not None:
        raw.extend(paths)
    if not raw:
        raise ValueError(
            "file-exists-check / file-content-check requires either "
            "'path' or 'paths' to be set"
        )
    return [_resolve_against(p, base_dir) for p in raw]


class FileExistsCheck:
    """Passes when at least one of the configured paths exists.

    Accepts either ``path`` (single) or ``paths`` (list, first-match
    wins). ``base_dir`` pins relative path resolution to the workflow
    root so checks don't silently depend on process cwd. ``~`` is
    expanded against the running user's home dir.
    """

    def __init__(
        self,
        path: str | Path | None = None,
        base_dir: str | Path | None = None,
        paths: list[str | Path] | None = None,
    ) -> None:
        self.paths = _coerce_paths(path, paths, base_dir)

    async def check(self) -> CheckResult:
        for p in self.paths:
            if p.exists():
                return CheckResult(passed=True, evidence=f"File found: {p}")
        if len(self.paths) == 1:
            return CheckResult(
                passed=False, evidence=f"File not found: {self.paths[0]}"
            )
        listing = ", ".join(str(p) for p in self.paths)
        return CheckResult(
            passed=False, evidence=f"None of these files exist: {listing}"
        )


class FileContentCheck:
    """Passes when at least one configured file contains a regex match.

    Accepts either ``path`` (single) or ``paths`` (list, first-match
    wins). For each path that exists, scan line-by-line for the
    pattern. The first file that has a matching line makes the check
    pass; the matching line becomes the evidence string. Files that
    do not exist are skipped silently -- the check is "any of these
    is configured", not "all of these are configured".

    ``base_dir`` pins relative path resolution to the workflow root.
    ``~`` is expanded against the running user's home dir.
    """

    def __init__(
        self,
        path: str | Path | None = None,
        pattern: str = "",
        base_dir: str | Path | None = None,
        paths: list[str | Path] | None = None,
    ) -> None:
        if not pattern:
            raise ValueError("file-content-check requires 'pattern'")
        self.paths = _coerce_paths(path, paths, base_dir)
        self.compiled_pattern = re.compile(pattern)

    async def check(self) -> CheckResult:
        misses: list[str] = []
        for p in self.paths:
            if not p.exists():
                misses.append(f"not found: {p}")
                continue
            try:
                content = p.read_text(encoding="utf-8", errors="replace")
            except OSError as e:
                misses.append(f"cannot read {p}: {e}")
                continue

            for i, line in enumerate(content.splitlines(), 1):
                if self.compiled_pattern.search(line):
                    return CheckResult(
                        passed=True,
                        evidence=f"{p} line {i}: {line.strip()}"[:200],
                    )
            misses.append(f"pattern not in {p}")

        return CheckResult(
            passed=False,
            evidence=(
                f"Pattern '{self.compiled_pattern.pattern}' not matched "
                f"({'; '.join(misses)})"
            ),
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
    lambda p: FileExistsCheck(
        path=p.get("path"),
        paths=p.get("paths"),
        base_dir=p.get("base_dir"),
    ),
)
register_check_type(
    "file-content-check",
    lambda p: FileContentCheck(
        path=p.get("path"),
        paths=p.get("paths"),
        pattern=p["pattern"],
        base_dir=p.get("base_dir"),
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
