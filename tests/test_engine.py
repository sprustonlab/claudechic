"""Unit tests for WorkflowEngine -- phase context injection and advance lock."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock

import pytest
from claudechic.checks.protocol import CheckDecl
from claudechic.workflows.engine import (
    WorkflowEngine,
    WorkflowManifest,
)
from claudechic.workflows.phases import Phase

pytestmark = [pytest.mark.fast, pytest.mark.asyncio]


def _make_engine(
    phases: list[Phase] | None = None,
    confirm_callback: Any = None,
) -> WorkflowEngine:
    """Build a WorkflowEngine with sensible defaults for testing."""
    if phases is None:
        phases = [
            Phase(id="proj:design", namespace="proj", file="design.md"),
            Phase(id="proj:implement", namespace="proj", file="implement.md"),
            Phase(id="proj:deploy", namespace="proj", file="deploy.md"),
        ]
    manifest = WorkflowManifest(workflow_id="proj", phases=phases)
    persist = AsyncMock()
    cb = confirm_callback or AsyncMock(return_value=True)
    return WorkflowEngine(manifest, persist, cb)


async def test_engine_injects_phase_context():
    """_run_single_check for manual-confirm includes phase_id, phase_index, phase_total, check_id."""
    captured_ctx: dict[str, Any] | None = None

    async def capture_confirm(
        question: str, context: dict[str, Any] | None = None
    ) -> bool:
        nonlocal captured_ctx
        captured_ctx = context
        return True

    engine = _make_engine(confirm_callback=capture_confirm)
    assert engine.get_current_phase() == "proj:design"

    check_decl = CheckDecl(
        id="proj:design:advance:0",
        namespace="proj",
        type="manual-confirm",
        params={"question": "Ready to advance?"},
    )

    result = await engine._run_single_check(check_decl)
    assert result.passed is True
    assert captured_ctx is not None
    assert captured_ctx["phase_id"] == "proj:design"
    # phase_index is 1-based: design is index 0 in list, +1 = 1
    assert captured_ctx["phase_index"] == 1
    assert captured_ctx["phase_total"] == 3
    assert captured_ctx["check_id"] == "proj:design:advance:0"


async def test_advance_lock_prevents_concurrent():
    """Two concurrent attempt_phase_advance calls serialize (second waits for first)."""
    call_order: list[str] = []
    gate = asyncio.Event()

    async def slow_confirm(
        question: str, context: dict[str, Any] | None = None
    ) -> bool:
        call_order.append("enter")
        await gate.wait()
        call_order.append("exit")
        return True

    phases = [
        Phase(
            id="proj:design",
            namespace="proj",
            file="design.md",
            advance_checks=[
                CheckDecl(
                    id="proj:design:advance:0",
                    namespace="proj",
                    type="manual-confirm",
                    params={"question": "Advance?"},
                )
            ],
        ),
        Phase(id="proj:implement", namespace="proj", file="implement.md"),
        Phase(id="proj:deploy", namespace="proj", file="deploy.md"),
    ]
    engine = _make_engine(phases=phases, confirm_callback=slow_confirm)

    checks = engine.get_advance_checks_for("proj:design")

    # Launch two concurrent advance attempts
    task1 = asyncio.create_task(
        engine.attempt_phase_advance("proj", "proj:design", "proj:implement", checks)
    )
    # Give task1 time to acquire the lock
    await asyncio.sleep(0.05)

    # task2 should block on the lock
    task2 = asyncio.create_task(
        engine.attempt_phase_advance("proj", "proj:design", "proj:implement", checks)
    )
    await asyncio.sleep(0.05)

    # Only one "enter" so far (task1 holds the lock, task2 is waiting)
    assert call_order.count("enter") == 1, (
        f"Expected 1 enter before gate, got: {call_order}"
    )

    # Release the gate so task1 completes
    gate.set()
    result1 = await task1

    # task2 now gets the lock but phase already advanced, so it gets mismatch
    result2 = await task2

    assert result1.success is True
    assert result2.success is False
    assert "mismatch" in result2.reason.lower()
