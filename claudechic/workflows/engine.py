"""Workflow engine — phase state, transitions, and check execution.

Manages in-memory phase state, executes advance checks with AND semantics
(sequential, short-circuit on first failure), and persists state via callback.
This is the orchestration layer — imports from checks/ and hints/.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from claudechic.checks.adapter import check_failed_to_hint
from claudechic.checks.builtins import _build_check
from claudechic.checks.protocol import (
    AsyncConfirmCallback,
    CheckDecl,
    CheckResult,
    OnFailureConfig,
)
from claudechic.workflows.phases import Phase

logger = logging.getLogger(__name__)


def _validate_artifact_path(path: str | Path, cwd: Path | None) -> Path:
    """Validate and resolve an artifact directory path.

    Pure validation — does NOT mkdir or persist. Used by both
    ``set_artifact_dir`` (which then mkdirs + persists) and
    ``from_session_state`` (which conditionally mkdirs + WARNs).

    Validation rules (all raise ``ValueError``):
    - Not empty.
    - No null bytes (``\\x00``).
    - No embedded newlines (``\\n`` or ``\\r``).
    - Resolved path MUST NOT have any path component named ``.claude``.

    Resolution: ``Path.resolve(strict=False)`` is applied BEFORE the
    ``.claude/``-ancestor check so ``..``-traversal attempts cannot
    bypass the boundary rule. Relative paths resolve against ``cwd``
    when supplied, else ``Path.cwd()`` (best-effort fallback).
    """
    if path is None:
        raise ValueError("artifact_dir path must not be None")
    raw = str(path)
    if raw == "":
        raise ValueError("artifact_dir path must not be empty")
    if "\x00" in raw:
        raise ValueError("artifact_dir path must not contain null bytes")
    if "\n" in raw or "\r" in raw:
        raise ValueError("artifact_dir path must not contain embedded newlines")

    p = Path(raw)
    if not p.is_absolute():
        base = cwd if cwd is not None else Path.cwd()
        p = base / p
    resolved = p.resolve(strict=False)

    if ".claude" in resolved.parts:
        raise ValueError(
            f"artifact_dir path may not resolve inside any '.claude/' "
            f"directory: {resolved}"
        )

    return resolved


# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

PersistFn = Callable[[dict[str, Any]], Awaitable[None] | None]
"""Callback to persist workflow state to chicsession.
Engine calls this on every phase transition. Never does direct file I/O."""


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WorkflowManifest:
    """Parsed workflow manifest — phases and metadata.

    Passed to WorkflowEngine at construction. Immutable snapshot
    of the manifest as parsed by the loader. Canonical definition
    lives here in engine.py — the integration layer constructs it
    from LoadResult at workflow activation time.
    """

    workflow_id: str
    phases: list[Phase] = field(default_factory=list)
    main_role: str | None = None  # Role folder for the main agent


@dataclass(frozen=True)
class PhaseAdvanceResult:
    """Outcome of a phase advance attempt."""

    success: bool
    reason: str
    failed_check_id: str | None = None
    hint_data: dict | None = None  # CheckFailed adapter output


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class WorkflowEngine:
    """Manages workflow state, phase transitions, and check execution.

    In-memory phase state, persisted via callback to chicsession.
    Sequential check execution (not parallel) — ManualConfirm shows TUI prompts.
    """

    def __init__(
        self,
        manifest: WorkflowManifest,
        persist_fn: PersistFn,
        confirm_callback: AsyncConfirmCallback,
        cwd: Path | None = None,
    ) -> None:
        self._manifest = manifest
        self._persist_fn = persist_fn
        self._confirm_callback = confirm_callback
        # Launched-repo root used to resolve relative paths supplied to
        # ``set_artifact_dir``. Absolute paths bypass it; ``None`` falls
        # back to ``Path.cwd()`` at validation time.
        self._cwd: Path | None = cwd
        self._advance_lock = asyncio.Lock()  # Prevent concurrent advance

        # Artifact directory — coordinator-set during a Setup-style phase
        # via ``set_artifact_dir``. ``None`` until set; resolved absolute
        # ``Path`` afterward. Persisted in chicsession state.
        self._artifact_dir: Path | None = None

        # Phase state — in-memory, persisted via callback
        self._current_phase: str | None = None
        if manifest.phases:
            self._current_phase = manifest.phases[0].id

        # Index phases by qualified ID for fast lookup
        self._phase_index: dict[str, Phase] = {p.id: p for p in manifest.phases}
        self._phase_order: list[str] = [p.id for p in manifest.phases]

    @property
    def workflow_id(self) -> str:
        return self._manifest.workflow_id

    @property
    def manifest(self) -> WorkflowManifest:
        return self._manifest

    @property
    def artifact_dir(self) -> Path | None:
        """Resolved absolute path to this run's artifact directory, or None.

        Read-only surface; the value is established via
        ``set_artifact_dir`` (during a Setup-style phase) or restored from
        chicsession state via ``from_session_state``. Equivalent to
        ``get_artifact_dir()``.
        """
        return self._artifact_dir

    # ------------------------------------------------------------------
    # Artifact directory API
    # ------------------------------------------------------------------

    async def set_artifact_dir(self, path: str | Path) -> Path:
        """Bind an artifact directory to this workflow run.

        Validates ``path`` (per ``_validate_artifact_path``), creates the
        directory at the resolved absolute location, stores it on the
        engine, and triggers a chicsession persist before returning.

        Idempotent on the same resolved path (re-calling with a path that
        resolves to the existing artifact_dir is a no-op return; persist
        still fires — write is idempotent). Raises ``RuntimeError`` on
        re-call with a different resolved path. Same-path comparison uses
        ``Path.samefile`` when both paths exist on disk; falls back to
        string compare on the resolved paths otherwise (handles deleted
        targets and case-insensitive filesystems).

        Persist failure semantics: if ``persist_fn`` raises, the prior
        ``self._artifact_dir`` value is restored before the exception
        propagates (rollback). For the first successful call this means
        ``self._artifact_dir`` returns to ``None``.
        """
        resolved = _validate_artifact_path(path, self._cwd)

        if self._artifact_dir is not None:
            same = False
            try:
                if self._artifact_dir.exists() and resolved.exists():
                    same = self._artifact_dir.samefile(resolved)
                else:
                    same = str(self._artifact_dir) == str(resolved)
            except OSError:
                same = str(self._artifact_dir) == str(resolved)
            if not same:
                raise RuntimeError(
                    f"artifact_dir already set to {self._artifact_dir}; "
                    f"cannot rebind to {resolved} (one artifact dir per "
                    f"workflow run)"
                )

        resolved.mkdir(parents=True, exist_ok=True)

        prior = self._artifact_dir
        self._artifact_dir = resolved
        try:
            # Persist directly (NOT via ``_persist()`` which swallows
            # exceptions for fire-and-forget phase-advance writes). Here
            # we want the failure to propagate so the rollback below can
            # restore engine state symmetric to the persisted state.
            state = self.to_session_state()
            result = self._persist_fn(state)
            if result is not None:
                await result
        except Exception:
            # Rollback so the engine surface matches the persisted state
            # (Skeptic2 ruling). Re-raise so callers see the failure.
            self._artifact_dir = prior
            raise
        return resolved

    def get_artifact_dir(self) -> Path | None:
        """Return the engine's artifact directory, or None if unset.

        Equivalent to the ``artifact_dir`` property.
        """
        return self._artifact_dir

    # ------------------------------------------------------------------
    # Phase queries (in-memory, no I/O)
    # ------------------------------------------------------------------

    def get_current_phase(self) -> str | None:
        """Return the current phase ID, or None if no phases defined."""
        return self._current_phase

    def get_next_phase(self, current: str) -> str | None:
        """Return the next phase after `current`, or None if last."""
        try:
            idx = self._phase_order.index(current)
        except ValueError:
            return None
        next_idx = idx + 1
        if next_idx >= len(self._phase_order):
            return None
        return self._phase_order[next_idx]

    def get_advance_checks_for(self, phase_id: str) -> list[CheckDecl]:
        """Return advance_checks for a phase, or empty list if unknown."""
        phase = self._phase_index.get(phase_id)
        if phase is None:
            return []
        return list(phase.advance_checks)

    # ------------------------------------------------------------------
    # Phase transition
    # ------------------------------------------------------------------

    async def attempt_phase_advance(
        self,
        workflow_id: str,
        current_phase: str,
        next_phase: str,
        advance_checks: list[CheckDecl],
    ) -> PhaseAdvanceResult:
        """Attempt to advance from current_phase to next_phase.

        AND semantics: all checks must pass. Sequential execution,
        short-circuit on first failure. On failure, bridges to hints
        pipeline via CheckFailed adapter.

        Uses asyncio.Lock to prevent concurrent advance attempts from
        showing double prompts.

        Args:
            workflow_id: Must match this engine's workflow_id.
            current_phase: Expected current phase (validated).
            next_phase: Target phase to advance to.
            advance_checks: CheckDecl list to evaluate.

        Returns:
            PhaseAdvanceResult with success/failure and details.
        """
        async with self._advance_lock:
            # Validate preconditions
            if workflow_id != self._manifest.workflow_id:
                return PhaseAdvanceResult(
                    success=False,
                    reason=f"Workflow mismatch: expected {self._manifest.workflow_id}, got {workflow_id}",
                )

            if self._current_phase != current_phase:
                return PhaseAdvanceResult(
                    success=False,
                    reason=f"Phase mismatch: engine is at {self._current_phase}, not {current_phase}",
                )

            if next_phase not in self._phase_index:
                return PhaseAdvanceResult(
                    success=False,
                    reason=f"Unknown target phase: {next_phase}",
                )

            # Execute checks sequentially — AND semantics, short-circuit
            for check_decl in advance_checks:
                result = await self._run_single_check(check_decl)
                if not result.passed:
                    # Bridge failure to hints pipeline
                    hint_data = None
                    if check_decl.on_failure:
                        on_failure = OnFailureConfig(
                            message=check_decl.on_failure.get(
                                "message", "Check failed"
                            ),
                            severity=check_decl.on_failure.get("severity", "warning"),
                            lifecycle=check_decl.on_failure.get(
                                "lifecycle", "show-until-resolved"
                            ),
                        )
                        hint_data = check_failed_to_hint(
                            result, on_failure, check_decl.id
                        )

                    logger.info(
                        "Phase advance blocked: %s failed -- %s",
                        check_decl.id,
                        result.evidence,
                    )
                    return PhaseAdvanceResult(
                        success=False,
                        reason=f"Check '{check_decl.id}' failed: {result.evidence}",
                        failed_check_id=check_decl.id,
                        hint_data=hint_data,
                    )

            # All checks passed — advance phase
            self._current_phase = next_phase
            logger.info(
                "Phase advanced: %s -> %s (workflow: %s)",
                current_phase,
                next_phase,
                workflow_id,
            )

            # Persist via callback
            await self._persist()

            return PhaseAdvanceResult(success=True, reason=f"Advanced to {next_phase}")

    # ------------------------------------------------------------------
    # Setup checks (global, no short-circuit)
    # ------------------------------------------------------------------

    async def run_setup_checks(self, check_specs: list[CheckDecl]) -> list[CheckResult]:
        """Run all setup checks. No short-circuit — all checks run, all failures reported.

        Returns list of CheckResult in same order as check_specs.
        """
        results: list[CheckResult] = []
        for check_decl in check_specs:
            result = await self._run_single_check(check_decl)
            results.append(result)
            if not result.passed:
                logger.warning(
                    "Setup check failed: %s — %s",
                    check_decl.id,
                    result.evidence,
                )
        return results

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_session_state(self) -> dict[str, Any]:
        """Serialize engine state for chicsession persistence.

        Returns opaque dict — only from_session_state knows the format.
        """
        state: dict[str, Any] = {
            "workflow_id": self._manifest.workflow_id,
            "current_phase": self._current_phase,
            "artifact_dir": (
                str(self._artifact_dir) if self._artifact_dir is not None else None
            ),
        }
        return state

    @classmethod
    def from_session_state(
        cls,
        state: dict[str, Any] | None,
        manifest: WorkflowManifest,
        persist_fn: PersistFn,
        confirm_callback: AsyncConfirmCallback,
        cwd: Path | None = None,
    ) -> WorkflowEngine:
        """Restore engine from persisted session state.

        Args:
            state: Dict from to_session_state(), or None for fresh start.
            manifest: Parsed workflow manifest (re-loaded, not persisted).
            persist_fn: Callback for future state persistence.
            confirm_callback: Callback for ManualConfirm checks.
            cwd: Launched-repo root for relative-path resolution. Forwarded
                to ``__init__``.

        Returns:
            Restored WorkflowEngine with phase state from session.

        Raises:
            ValueError: If the saved ``artifact_dir`` is invalid (null
                bytes, embedded newlines, ``.claude/``-ancestor) — the
                chicsession state is corrupt.
        """
        engine = cls(manifest, persist_fn, confirm_callback, cwd=cwd)

        if state is None:
            return engine  # Keep default first phase from __init__

        # Restore phase state — validate against current manifest
        saved_phase = state.get("current_phase")
        if saved_phase and saved_phase in engine._phase_index:
            engine._current_phase = saved_phase
        else:
            logger.warning(
                "Saved phase '%s' not in manifest, defaulting to first phase",
                saved_phase,
            )
            # Keep default (first phase), already set in __init__

        # Restore artifact_dir — re-validate via the same pipeline as
        # set_artifact_dir. Tampered/invalid saved paths raise. Missing
        # on disk WARNs but keeps the path stored (deviation from the
        # spec §5.2 "forward to __init__" wording per user direction —
        # spec text will be cleaned up in a follow-up).
        saved_artifact = state.get("artifact_dir")
        if saved_artifact:
            resolved = _validate_artifact_path(saved_artifact, cwd)
            if not resolved.exists():
                logger.warning(
                    "Saved artifact_dir does not exist on disk: %s "
                    "(keeping path stored; coordinator may restore or "
                    "re-create)",
                    resolved,
                )
            engine._artifact_dir = resolved

        return engine

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _run_single_check(self, check_decl: CheckDecl) -> CheckResult:
        """Build and execute a single check from its declaration."""
        try:
            # Inject confirm_fn for ManualConfirm checks
            params = dict(check_decl.params)
            if check_decl.type == "manual-confirm":
                params["confirm_fn"] = self._confirm_callback
                # Inject phase context at invocation time (not closure time)
                current = self._current_phase
                phase_order = self._phase_order
                phase_index = (
                    phase_order.index(current) + 1 if current in phase_order else 0
                )
                params["context"] = {
                    "phase_id": current,
                    "phase_index": phase_index,
                    "phase_total": len(phase_order),
                    "check_id": check_decl.id,
                }
            elif check_decl.type == "artifact-dir-ready-check":
                # Inject engine reference so the check can read
                # ``engine.artifact_dir`` without builtins.py importing
                # the engine module (leaf-module discipline).
                params["engine"] = self
            elif check_decl.type == "command-output-check":
                # Substitute ${CLAUDECHIC_ARTIFACT_DIR} in the command
                # string so workflow YAML can reference the run-bound
                # path without hardcoding a prefix. Empty string when
                # unset (deliberate, visible failure mode — matches the
                # markdown substitution rule in §5.3).
                cmd = params.get("command")
                if isinstance(cmd, str) and "${CLAUDECHIC_ARTIFACT_DIR}" in cmd:
                    sub = (
                        str(self._artifact_dir)
                        if self._artifact_dir is not None
                        else ""
                    )
                    params["command"] = cmd.replace("${CLAUDECHIC_ARTIFACT_DIR}", sub)

            # Build check from registry using potentially modified params
            augmented_decl = CheckDecl(
                id=check_decl.id,
                namespace=check_decl.namespace,
                type=check_decl.type,
                params=params,
                on_failure=check_decl.on_failure,
                when=check_decl.when,
            )
            check = _build_check(augmented_decl)
            return await check.check()
        except Exception as e:
            logger.error("Check '%s' raised: %s", check_decl.id, e)
            return CheckResult(passed=False, evidence=f"Check error: {e}")

    async def _persist(self) -> None:
        """Persist current state via callback."""
        state = self.to_session_state()
        try:
            result = self._persist_fn(state)
            if result is not None:
                await result
        except Exception as e:
            logger.error("Failed to persist workflow state: %s", e)
