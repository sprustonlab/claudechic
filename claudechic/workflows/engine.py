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
    ) -> None:
        self._manifest = manifest
        self._persist_fn = persist_fn
        self._confirm_callback = confirm_callback
        self._advance_lock = asyncio.Lock()  # Prevent concurrent advance

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
        return {
            "workflow_id": self._manifest.workflow_id,
            "current_phase": self._current_phase,
        }

    @classmethod
    def from_session_state(
        cls,
        state: dict[str, Any] | None,
        manifest: WorkflowManifest,
        persist_fn: PersistFn,
        confirm_callback: AsyncConfirmCallback,
    ) -> WorkflowEngine:
        """Restore engine from persisted session state.

        Args:
            state: Dict from to_session_state(), or None for fresh start.
            manifest: Parsed workflow manifest (re-loaded, not persisted).
            persist_fn: Callback for future state persistence.
            confirm_callback: Callback for ManualConfirm checks.

        Returns:
            Restored WorkflowEngine with phase state from session.
        """
        engine = cls(manifest, persist_fn, confirm_callback)

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
