"""Manifest section parser for phases.

Implements ``ManifestSection[Phase]`` — parses the ``phases:`` section
of YAML manifests into ``Phase`` objects.

Fail-open per item: bad entries are skipped with a warning, valid ones returned.

Phase-nested advance_checks are parsed into CheckDecl objects.
Phase-nested hints are parsed into HintDecl objects with auto-generated IDs
and phase scope metadata attached.

ORCHESTRATION LAYER: imports from checks/ and hints/ (by design — phases.py
is a bridge type).
"""

from __future__ import annotations

import logging
from typing import Any

from claudechic.checks.protocol import CheckDecl
from claudechic.hints.types import HintDecl
from claudechic.workflows.phases import Phase, Tier

logger = logging.getLogger(__name__)


class PhasesParser:
    """Parses the ``phases`` section of manifests into ``Phase`` objects.

    Satisfies ``ManifestSection[Phase]`` protocol.
    """

    @property
    def section_key(self) -> str:
        return "phases"

    def parse(
        self,
        raw: list[dict[str, Any]],
        *,
        namespace: str,
        source_path: str,
        tier: Tier = "package",
    ) -> list[Phase]:
        """Parse raw YAML phase entries into Phase objects.

        Args:
            raw: List of dicts from yaml.safe_load for the ``phases:`` key.
            namespace: workflow_id for workflow manifests (phases are not expected
                in global/ manifests, but handled gracefully if present).
            source_path: Path to manifest file (for error messages only).
            tier: Provenance tier — stamped onto each Phase and onto
                phase-nested CheckDecl/HintDecl records.

        Returns:
            List of valid Phase objects. Invalid items are skipped with warnings.
        """
        results: list[Phase] = []

        for idx, entry in enumerate(raw):
            if not isinstance(entry, dict):
                logger.warning(
                    "%s: phases[%d] is not a dict — skipping", source_path, idx
                )
                continue

            try:
                phase = self._parse_one(
                    entry,
                    namespace=namespace,
                    source_path=source_path,
                    idx=idx,
                    tier=tier,
                )
            except _SkipItem as exc:
                logger.warning("%s: phases[%d]: %s — skipping", source_path, idx, exc)
                continue

            results.append(phase)

        return results

    def _parse_one(
        self,
        entry: dict[str, Any],
        *,
        namespace: str,
        source_path: str,
        idx: int,
        tier: Tier = "package",
    ) -> Phase:
        """Parse a single phase dict into a Phase. Raises _SkipItem on failure."""
        # --- id: required, no colons in raw id ---
        raw_id = entry.get("id")
        if not raw_id or not isinstance(raw_id, str):
            raise _SkipItem("missing or invalid 'id'")
        raw_id = raw_id.strip()
        if ":" in raw_id:
            raise _SkipItem(f"id {raw_id!r} must not contain ':'")

        qualified_id = f"{namespace}:{raw_id}"

        # --- file: defaults to bare id if not specified ---
        file = entry.get("file", raw_id)
        if not isinstance(file, str):
            raise _SkipItem(f"id {raw_id!r}: 'file' must be a string")

        # --- advance_checks: optional list of check declarations ---
        advance_checks = self._parse_advance_checks(
            entry.get("advance_checks", []),
            namespace=namespace,
            phase_id=raw_id,
            source_path=source_path,
            tier=tier,
        )

        # --- hints: optional list of hint declarations ---
        hints = self._parse_nested_hints(
            entry.get("hints", []),
            namespace=namespace,
            phase_id=raw_id,
            qualified_phase_id=qualified_id,
            source_path=source_path,
            tier=tier,
        )

        return Phase(
            id=qualified_id,
            namespace=namespace,
            file=file,
            advance_checks=advance_checks,
            hints=hints,
            tier=tier,
        )

    def _parse_advance_checks(
        self,
        raw_checks: Any,
        *,
        namespace: str,
        phase_id: str,
        source_path: str,
        tier: Tier = "package",
    ) -> list[CheckDecl]:
        """Parse advance_checks list into CheckDecl objects."""
        if not isinstance(raw_checks, list):
            if raw_checks:
                logger.warning(
                    "%s: phase '%s' advance_checks is not a list — ignoring",
                    source_path,
                    phase_id,
                )
            return []

        results: list[CheckDecl] = []
        for i, check_entry in enumerate(raw_checks):
            if not isinstance(check_entry, dict):
                logger.warning(
                    "%s: phase '%s' advance_checks[%d] is not a dict — skipping",
                    source_path,
                    phase_id,
                    i,
                )
                continue

            check_type = check_entry.get("type")
            if not check_type or not isinstance(check_type, str):
                logger.warning(
                    "%s: phase '%s' advance_checks[%d] missing 'type' — skipping",
                    source_path,
                    phase_id,
                    i,
                )
                continue

            # All fields except 'type' and 'on_failure' and 'when' are params
            params = {
                k: v
                for k, v in check_entry.items()
                if k not in ("type", "on_failure", "when")
            }

            check_id = f"{namespace}:{phase_id}:advance:{i}"

            results.append(
                CheckDecl(
                    id=check_id,
                    namespace=namespace,
                    type=check_type,
                    params=params,
                    on_failure=check_entry.get("on_failure"),
                    when=check_entry.get("when"),
                    tier=tier,
                )
            )

        return results

    def _parse_nested_hints(
        self,
        raw_hints: Any,
        *,
        namespace: str,
        phase_id: str,
        qualified_phase_id: str,
        source_path: str,
        tier: Tier = "package",
    ) -> list[HintDecl]:
        """Parse phase-nested hints into HintDecl objects with phase scope.

        Hints without explicit IDs get auto-generated IDs:
        ``{namespace}:{phase_id}:hint:{index}``
        """
        if not isinstance(raw_hints, list):
            if raw_hints:
                logger.warning(
                    "%s: phase '%s' hints is not a list — ignoring",
                    source_path,
                    phase_id,
                )
            return []

        results: list[HintDecl] = []
        for i, hint_entry in enumerate(raw_hints):
            if not isinstance(hint_entry, dict):
                logger.warning(
                    "%s: phase '%s' hints[%d] is not a dict — skipping",
                    source_path,
                    phase_id,
                    i,
                )
                continue

            message = hint_entry.get("message")
            if not message or not isinstance(message, str):
                logger.warning(
                    "%s: phase '%s' hints[%d] missing 'message' — skipping",
                    source_path,
                    phase_id,
                    i,
                )
                continue

            # Auto-generate ID if not provided
            raw_id = hint_entry.get("id")
            if raw_id and isinstance(raw_id, str):
                raw_id = raw_id.strip()
                if ":" in raw_id:
                    logger.warning(
                        "%s: phase '%s' hints[%d] id %r contains ':' — skipping",
                        source_path,
                        phase_id,
                        i,
                        raw_id,
                    )
                    continue
                hint_id = f"{namespace}:{raw_id}"
            else:
                hint_id = f"{namespace}:{phase_id}:hint:{i}"

            lifecycle = hint_entry.get("lifecycle", "show-once")

            cooldown_seconds: int | None = None
            if lifecycle == "cooldown":
                raw_cooldown = hint_entry.get("cooldown_seconds")
                if raw_cooldown is not None:
                    try:
                        cooldown_seconds = int(raw_cooldown)
                    except (TypeError, ValueError):
                        logger.warning(
                            "%s: phase '%s' hints[%d] cooldown_seconds not an int — skipping",
                            source_path,
                            phase_id,
                            i,
                        )
                        continue

            results.append(
                HintDecl(
                    id=hint_id,
                    message=message,
                    lifecycle=lifecycle,
                    cooldown_seconds=cooldown_seconds,
                    phase=qualified_phase_id,
                    namespace=namespace,
                    tier=tier,
                )
            )

        return results


class _SkipItem(Exception):
    """Internal: raised when a single phase item fails validation."""
