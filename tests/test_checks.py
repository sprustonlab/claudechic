"""Unit tests for checks system -- ManualConfirm context passing."""

from __future__ import annotations

from typing import Any

import pytest
from claudechic.checks.builtins import ManualConfirm

pytestmark = [pytest.mark.fast, pytest.mark.asyncio]


async def test_manual_confirm_passes_context():
    """ManualConfirm.check() passes context dict to callback."""
    received_ctx: dict[str, Any] | None = None

    async def capture_callback(
        question: str, context: dict[str, Any] | None = None
    ) -> bool:
        nonlocal received_ctx
        received_ctx = context
        return True

    ctx = {
        "phase_id": "proj:design",
        "phase_index": 1,
        "phase_total": 3,
        "check_id": "proj:design:advance:0",
    }
    mc = ManualConfirm(question="Ready?", confirm_fn=capture_callback, context=ctx)
    result = await mc.check()

    assert result.passed is True
    assert received_ctx is not None
    assert received_ctx["phase_id"] == "proj:design"
    assert received_ctx["phase_index"] == 1
    assert received_ctx["phase_total"] == 3
    assert received_ctx["check_id"] == "proj:design:advance:0"


async def test_manual_confirm_none_context():
    """ManualConfirm.check() works when context is None (backward compat)."""
    received_ctx = "SENTINEL"

    async def capture_callback(
        question: str, context: dict[str, Any] | None = None
    ) -> bool:
        nonlocal received_ctx
        received_ctx = context
        return True

    mc = ManualConfirm(question="Confirm?", confirm_fn=capture_callback)
    result = await mc.check()

    assert result.passed is True
    assert received_ctx is None
