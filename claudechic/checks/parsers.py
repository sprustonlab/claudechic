"""ManifestSection parser for checks.

Implements ManifestSection[CheckDecl] protocol.
Registered with the ManifestLoader at app init.

Leaf within checks/ — imports only from sibling protocol.py.
"""

from __future__ import annotations

import logging
from typing import Any

from claudechic.checks.protocol import CheckDecl

logger = logging.getLogger(__name__)


class ChecksParser:
    """Parses the 'checks' section of manifests into CheckDecl objects.

    Implements ManifestSection[CheckDecl] protocol.
    Produces declarations (CheckDecl), NOT executable Check objects.
    The conversion CheckDecl -> Check happens in the engine via
    _build_check() + registry.
    """

    @property
    def section_key(self) -> str:
        return "checks"

    def parse(
        self,
        raw: list[dict[str, Any]],
        *,
        namespace: str,
        source_path: str,
    ) -> list[CheckDecl]:
        checks: list[CheckDecl] = []
        for i, entry in enumerate(raw):
            if not isinstance(entry, dict):
                logger.warning("Skipping non-dict check #%d in %s", i, source_path)
                continue
            result = self._parse_one(entry, namespace, source_path)
            if isinstance(result, CheckDecl):
                checks.append(result)
            else:
                logger.warning("Skipping check in %s: %s", source_path, result)
        return checks

    def _parse_one(
        self, entry: dict, namespace: str, source_path: str
    ) -> CheckDecl | str:
        """Parse one check entry. Returns CheckDecl or error string."""

        # --- ID ---
        raw_id = entry.get("id")
        if not raw_id or not isinstance(raw_id, str):
            return "missing 'id' field"
        if ":" in raw_id:
            return f"raw ID '{raw_id}' contains ':' — use bare IDs only"

        qualified_id = f"{namespace}:{raw_id}"

        # --- Type ---
        check_type = entry.get("type")
        if not check_type or not isinstance(check_type, str):
            return f"check '{raw_id}' has no 'type' field or type is not a string"

        # --- Params ---
        params = entry.get("params", {})
        if not isinstance(params, dict):
            return f"check '{raw_id}' params must be a dict"

        # --- on_failure (optional) ---
        on_failure = entry.get("on_failure")
        if on_failure is not None and not isinstance(on_failure, dict):
            return f"check '{raw_id}' on_failure must be a dict"

        # --- when (optional, conditional activation) ---
        when = entry.get("when")
        if when is not None and not isinstance(when, dict):
            return f"check '{raw_id}' when must be a dict"

        return CheckDecl(
            id=qualified_id,
            namespace=namespace,
            type=check_type,
            params=params,
            on_failure=on_failure,
            when=when,
        )
