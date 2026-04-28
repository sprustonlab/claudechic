"""Manifest section parser for hints.

Implements ``ManifestSection[HintDecl]`` — parses the ``hints:`` section
of YAML manifests into ``HintDecl`` objects.

Fail-open per item: bad entries are skipped with a warning, valid ones returned.

LEAF MODULE: Only imports from hints.types. No imports from workflows/, checks/,
or guardrails/.
"""

from __future__ import annotations

import logging
from typing import Any

from claudechic.hints.types import HintDecl

logger = logging.getLogger(__name__)

# Valid lifecycle string values (matches HintLifecycle implementations)
_VALID_LIFECYCLES = frozenset(
    {
        "show-once",
        "show-until-resolved",
        "show-every-session",
        "cooldown",
    }
)


class HintsParser:
    """Parses the ``hints`` section of manifests into ``HintDecl`` objects.

    Satisfies ``ManifestSection[HintDecl]`` protocol.
    """

    @property
    def section_key(self) -> str:
        return "hints"

    def parse(
        self,
        raw: list[dict[str, Any]],
        *,
        namespace: str,
        source_path: str,
    ) -> list[HintDecl]:
        """Parse raw YAML hint entries into HintDecl objects.

        Args:
            raw: List of dicts from yaml.safe_load for the ``hints:`` key.
            namespace: ``'global'`` for global/*.yaml, workflow_id for workflow manifests.
            source_path: Path to manifest file (for error messages only).

        Returns:
            List of valid HintDecl objects. Invalid items are skipped with warnings.
        """
        results: list[HintDecl] = []

        for idx, item in enumerate(raw):
            if not isinstance(item, dict):
                logger.warning(
                    "%s: hints[%d] is not a dict — skipping", source_path, idx
                )
                continue

            try:
                decl = self._parse_item(
                    item, namespace=namespace, source_path=source_path, idx=idx
                )
            except _SkipItem as exc:
                logger.warning("%s: hints[%d]: %s — skipping", source_path, idx, exc)
                continue

            results.append(decl)

        return results

    def _parse_item(
        self,
        item: dict[str, Any],
        *,
        namespace: str,
        source_path: str,
        idx: int,
    ) -> HintDecl:
        """Parse a single hint dict into a HintDecl. Raises _SkipItem on validation failure."""
        # --- id: required, no colons in raw id ---
        raw_id = item.get("id")
        if not raw_id or not isinstance(raw_id, str):
            raise _SkipItem("missing or invalid 'id'")
        raw_id = raw_id.strip()
        if ":" in raw_id:
            raise _SkipItem(f"id {raw_id!r} must not contain ':'")

        qualified_id = f"{namespace}:{raw_id}"

        # --- message: required ---
        message = item.get("message")
        if not message or not isinstance(message, str):
            raise _SkipItem(f"id {raw_id!r}: missing or invalid 'message'")

        # --- lifecycle: default "show-once" ---
        lifecycle = item.get("lifecycle", "show-once")
        if not isinstance(lifecycle, str):
            raise _SkipItem(f"id {raw_id!r}: lifecycle must be a string")
        lifecycle = lifecycle.strip()
        if lifecycle not in _VALID_LIFECYCLES:
            raise _SkipItem(
                f"id {raw_id!r}: unknown lifecycle {lifecycle!r} "
                f"(valid: {', '.join(sorted(_VALID_LIFECYCLES))})"
            )

        # --- cooldown_seconds: optional, required if lifecycle == "cooldown" ---
        cooldown_seconds: int | None = None
        if lifecycle == "cooldown":
            raw_cooldown = item.get("cooldown_seconds")
            if raw_cooldown is None:
                raise _SkipItem(
                    f"id {raw_id!r}: lifecycle 'cooldown' requires 'cooldown_seconds'"
                )
            try:
                cooldown_seconds = int(raw_cooldown)
            except (TypeError, ValueError) as err:
                raise _SkipItem(
                    f"id {raw_id!r}: cooldown_seconds must be an integer"
                ) from err
            if cooldown_seconds <= 0:
                raise _SkipItem(f"id {raw_id!r}: cooldown_seconds must be > 0")

        # --- phase: optional, qualify bare names ---
        phase: str | None = None
        raw_phase = item.get("phase")
        if raw_phase is not None:
            if not isinstance(raw_phase, str):
                raise _SkipItem(f"id {raw_id!r}: phase must be a string")
            raw_phase = raw_phase.strip()
            if raw_phase:
                # Qualify bare phase names (no colon) for non-global namespaces
                if ":" not in raw_phase and namespace != "global":
                    phase = f"{namespace}:{raw_phase}"
                else:
                    phase = raw_phase

        # --- trigger: optional, dict with 'type' key ---
        trigger_type: str | None = None
        raw_trigger = item.get("trigger")
        if raw_trigger is not None:
            if isinstance(raw_trigger, dict):
                t = raw_trigger.get("type")
                if isinstance(t, str) and t.strip():
                    trigger_type = t.strip()
                else:
                    raise _SkipItem(
                        f"id {raw_id!r}: trigger.type must be a non-empty string"
                    )
            elif isinstance(raw_trigger, str):
                trigger_type = raw_trigger.strip()
            else:
                raise _SkipItem(f"id {raw_id!r}: trigger must be a dict or string")

        # --- severity: optional, default "info" ---
        severity = item.get("severity", "info")
        if not isinstance(severity, str) or severity not in ("info", "warning"):
            raise _SkipItem(f"id {raw_id!r}: severity must be 'info' or 'warning'")

        # --- priority: optional, default 3 ---
        priority = item.get("priority", 3)
        try:
            priority = int(priority)
        except (TypeError, ValueError) as err:
            raise _SkipItem(f"id {raw_id!r}: priority must be an integer") from err

        return HintDecl(
            id=qualified_id,
            message=message,
            lifecycle=lifecycle,
            cooldown_seconds=cooldown_seconds,
            phase=phase,
            namespace=namespace,
            trigger_type=trigger_type,
            severity=severity,
            priority=priority,
        )


class _SkipItem(Exception):
    """Internal: raised when a single hint item fails validation."""
