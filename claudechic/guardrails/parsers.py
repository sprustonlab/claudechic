"""ManifestSection parsers for rules and injections.

Implements ManifestSection[Rule] and ManifestSection[Injection] protocols.
These parsers are registered with the ManifestLoader at app init.

Leaf within guardrails/ — imports only from sibling rules.py.
"""

from __future__ import annotations

import logging
import re
from functools import lru_cache
from typing import Any

from claudechic.guardrails.rules import Injection, Rule

logger = logging.getLogger(__name__)

# Default detect_field per trigger tool name. Tools not listed default to "command".
DETECT_FIELD_DEFAULTS: dict[str, str] = {
    "Bash": "command",
    "Write": "file_path",
    "Edit": "file_path",
    "Read": "file_path",
    "NotebookEdit": "notebook_path",
}


# Module-level cache, never cleared. 256 entries is sufficient for any realistic manifest set.
@lru_cache(maxsize=256)
def _cached_compile(pattern: str) -> re.Pattern[str]:
    """Compile and cache a regex pattern."""
    return re.compile(pattern)


def _as_list(value: Any) -> list[str]:
    """Normalize a value to a list of strings."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(v) for v in value]
    return []


def _qualify_phases(phases: list[str], namespace: str) -> list[str]:
    """Qualify bare phase names with namespace prefix.

    Bare names (no ':') in non-global namespaces get qualified as
    '{namespace}:{phase}'. Already-qualified names and global namespace
    names pass through unchanged.
    """
    result: list[str] = []
    for phase in phases:
        if ":" in phase or namespace == "global":
            result.append(phase)
        else:
            result.append(f"{namespace}:{phase}")
    return result


class RulesParser:
    """Parses the 'rules' section of manifests into Rule objects.

    Implements ManifestSection[Rule] protocol.
    """

    @property
    def section_key(self) -> str:
        return "rules"

    def parse(
        self,
        raw: list[dict[str, Any]],
        *,
        namespace: str,
        source_path: str,
    ) -> list[Rule]:
        rules: list[Rule] = []
        for i, entry in enumerate(raw):
            if not isinstance(entry, dict):
                logger.warning("Skipping non-dict rule #%d in %s", i, source_path)
                continue
            result = self._parse_one(entry, namespace, source_path)
            if isinstance(result, Rule):
                rules.append(result)
            else:
                logger.warning("Skipping rule in %s: %s", source_path, result)
        return rules

    def _parse_one(self, entry: dict, namespace: str, source_path: str) -> Rule | str:
        raw_id = entry.get("id")
        if not raw_id or not isinstance(raw_id, str):
            return "missing 'id' field"
        if ":" in raw_id:
            return f"raw ID '{raw_id}' contains ':' — use bare IDs only"

        qualified_id = f"{namespace}:{raw_id}"

        raw_trigger = entry.get("trigger") or ""
        triggers = (
            [raw_trigger]
            if isinstance(raw_trigger, str)
            else [str(t) for t in raw_trigger]
            if isinstance(raw_trigger, list)
            else []
        )
        if not any(triggers):
            return f"rule '{raw_id}' has no trigger"

        enforcement = entry.get("enforcement", "deny")
        if enforcement not in ("deny", "warn", "log"):
            return f"unknown enforcement '{enforcement}'"

        # Infer default detect_field from first trigger's tool name
        trigger_tool = ""
        for t in triggers:
            parts = t.split("/", 1)
            if len(parts) == 2:
                trigger_tool = parts[1]
                break
        default_field = DETECT_FIELD_DEFAULTS.get(trigger_tool, "command")

        detect = entry.get("detect", {})
        detect_pattern = None
        detect_field = default_field
        if isinstance(detect, dict) and detect.get("pattern"):
            try:
                detect_pattern = _cached_compile(detect["pattern"])
            except re.error as e:
                return f"invalid detect regex: {e}"
            detect_field = detect.get("field", default_field)

        exclude_pattern = None
        exclude_str = entry.get("exclude_if_matches", "")
        if exclude_str:
            try:
                exclude_pattern = _cached_compile(exclude_str)
            except re.error as e:
                return f"invalid exclude regex: {e}"

        phases = _qualify_phases(_as_list(entry.get("phases", [])), namespace)
        exclude_phases = _qualify_phases(
            _as_list(entry.get("exclude_phases", [])), namespace
        )

        return Rule(
            id=qualified_id,
            namespace=namespace,
            trigger=triggers,
            enforcement=enforcement,
            detect_pattern=detect_pattern,
            detect_field=detect_field,
            exclude_pattern=exclude_pattern,
            message=entry.get("message", ""),
            roles=_as_list(entry.get("roles", [])),
            exclude_roles=_as_list(entry.get("exclude_roles", [])),
            phases=phases,
            exclude_phases=exclude_phases,
        )


class InjectionsParser:
    """Parses the 'injections' section of manifests into Injection objects.

    Implements ManifestSection[Injection] protocol.
    """

    @property
    def section_key(self) -> str:
        return "injections"

    def parse(
        self,
        raw: list[dict[str, Any]],
        *,
        namespace: str,
        source_path: str,
    ) -> list[Injection]:
        injections: list[Injection] = []
        for i, entry in enumerate(raw):
            if not isinstance(entry, dict):
                logger.warning("Skipping non-dict injection #%d in %s", i, source_path)
                continue
            result = self._parse_one(entry, namespace, source_path)
            if isinstance(result, Injection):
                injections.append(result)
            else:
                logger.warning("Skipping injection in %s: %s", source_path, result)
        return injections

    def _parse_one(
        self, entry: dict, namespace: str, source_path: str
    ) -> Injection | str:
        raw_id = entry.get("id")
        if not raw_id or not isinstance(raw_id, str):
            return "missing 'id' field"
        if ":" in raw_id:
            return f"raw ID '{raw_id}' contains ':' — use bare IDs only"

        qualified_id = f"{namespace}:{raw_id}"

        raw_trigger = entry.get("trigger") or ""
        triggers = (
            [raw_trigger]
            if isinstance(raw_trigger, str)
            else [str(t) for t in raw_trigger]
            if isinstance(raw_trigger, list)
            else []
        )
        if not any(triggers):
            return f"injection '{raw_id}' has no trigger"

        # Infer default detect_field from first trigger's tool name
        trigger_tool = ""
        for t in triggers:
            parts = t.split("/", 1)
            if len(parts) == 2:
                trigger_tool = parts[1]
                break
        default_field = DETECT_FIELD_DEFAULTS.get(trigger_tool, "command")

        detect = entry.get("detect", {})
        detect_pattern = None
        detect_field = default_field
        if isinstance(detect, dict) and detect.get("pattern"):
            try:
                detect_pattern = _cached_compile(detect["pattern"])
            except re.error as e:
                return f"invalid detect regex: {e}"
            detect_field = detect.get("field", default_field)

        phases = _qualify_phases(_as_list(entry.get("phases", [])), namespace)
        exclude_phases = _qualify_phases(
            _as_list(entry.get("exclude_phases", [])), namespace
        )

        return Injection(
            id=qualified_id,
            namespace=namespace,
            trigger=triggers,
            detect_pattern=detect_pattern,
            detect_field=detect_field,
            inject_value=entry.get("inject_value", ""),
            roles=_as_list(entry.get("roles", [])),
            exclude_roles=_as_list(entry.get("exclude_roles", [])),
            phases=phases,
            exclude_phases=exclude_phases,
        )
