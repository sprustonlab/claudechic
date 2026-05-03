"""Configuration management for claudechic via ~/.claudechic/config.yaml."""

from __future__ import annotations

import contextlib
import logging
import os
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

log = logging.getLogger(__name__)

CONFIG_PATH = Path.home() / ".claudechic" / "config.yaml"


class ConfigValidationError(ValueError):
    """Raised when a settings YAML value fails schema validation.

    Currently raised for (SPEC §3.7, §3.11):
    - ``constraints_segment.scope.sites: []`` (empty list, likely a typo)
    - ``environment_segment.scope.sites: []`` (same)
    """


def _load() -> tuple[dict, bool]:
    """Load config from disk, creating file atomically if missing.

    Returns (config_dict, is_new_install).
    """
    new_install = False

    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
        # Provide defaults for missing keys (don't save - preserve user's file)
        config.setdefault("analytics", {})
        config["analytics"].setdefault("id", "anonymous")
        config["analytics"].setdefault("enabled", True)
        config.setdefault("experimental", {})
        config.setdefault("worktree", {})
        config["worktree"].setdefault("path_template", None)
        config.setdefault("default_permission_mode", "auto")
        config.setdefault(
            "show_message_metadata", True
        )  # Show timestamp/tokens by default
        # claudechic-awareness install toggle (per SPEC §4.3, default True)
        config.setdefault("awareness", {})
        config["awareness"].setdefault("install", True)
        # SDK thinking-budget level (SPEC C3). Survives restart and is
        # mirrored into Agent.effort by the StatusFooter on mount + by
        # the settings re-apply path.  Valid values: low / medium / high
        # / max ("max" is Opus-only; non-Opus models snap to "medium"
        # via EffortLabel.set_available_levels).
        config.setdefault("effort", "high")
        # Migrate legacy vim key to vi-mode
        if "vim" in config:
            config["vi-mode"] = config.pop("vim")
            _save(config)
    else:
        # New install - create config with fresh ID and save.  Keep this
        # shape in sync with the setdefault block above so a fresh install
        # produces the SAME keys as a long-lived config.
        config = {
            "analytics": {"enabled": True, "id": str(uuid.uuid4())},
            "experimental": {},
            "worktree": {"path_template": None},
            "recent-tools-expanded": 2,
            "default_permission_mode": "auto",
            "show_message_metadata": True,  # Show timestamp/tokens by default
            # claudechic-awareness install toggle (per SPEC §4.3, default True)
            "awareness": {"install": True},
            # SDK thinking-budget level (SPEC C3, default "high").
            "effort": "high",
        }
        new_install = True
        _save(config)

    return config, new_install


def _save(config: dict) -> None:
    """Write config to disk atomically."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=CONFIG_PATH.parent, suffix=".yaml")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False)
        os.replace(tmp_path, CONFIG_PATH)
    except Exception:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise


# Load config once at import time
CONFIG, NEW_INSTALL = _load()


def save() -> None:
    """Save current CONFIG to disk."""
    _save(CONFIG)


# ---------------------------------------------------------------------------
# ProjectConfig -- per-project feature toggles from .claudechic.yaml
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# constraints_segment / environment_segment parsing (SPEC §3.7, §3.11)
#
# Both segments share a "scope.sites" sub-key with identical validation
# semantics: empty list -> ConfigValidationError; missing/non-list ->
# defaults applied. The site allowlist differs (constraints has 4 sites,
# environment has 3); the canonical sets live in
# ``claudechic.workflows.agent_folders`` so the gate predicate and the
# config validator agree on the same enumeration.
# ---------------------------------------------------------------------------


def _parse_scope_sites(
    raw_block: Any,
    *,
    allowed: frozenset[str],
    config_key: str,
    source: str,
) -> frozenset[str] | None:
    """Validate and parse a ``scope.sites`` list.

    Returns ``None`` when the key is absent or not a dict (caller falls
    back to defaults). Returns a frozenset of validated site tokens
    otherwise. Raises ``ConfigValidationError`` when the list is empty
    (typo guard, SPEC §3.7 / §3.11). Unknown tokens are dropped with a
    WARNING -- they are likely user typos but not severe enough to fail
    config load.
    """
    if not isinstance(raw_block, dict):
        return None
    raw_sites = raw_block.get("sites")
    if raw_sites is None:
        return None
    if not isinstance(raw_sites, list):
        log.warning(
            "%s: %s.scope.sites is not a list (got %r); using default",
            source,
            config_key,
            type(raw_sites).__name__,
        )
        return None
    if len(raw_sites) == 0:
        raise ConfigValidationError(
            f"{config_key}.scope.sites is empty. "
            f"Provide at least one of {sorted(allowed)}, "
            "or remove the key to use the default."
        )
    cleaned: set[str] = set()
    for entry in raw_sites:
        if not isinstance(entry, str):
            log.warning(
                "%s: %s.scope.sites entry %r is not a string; skipping",
                source,
                config_key,
                entry,
            )
            continue
        token = entry.strip()
        if token not in allowed:
            log.warning(
                "%s: %s.scope.sites unknown token %r; valid tokens: %s",
                source,
                config_key,
                token,
                sorted(allowed),
            )
            continue
        cleaned.add(token)
    if not cleaned:
        raise ConfigValidationError(
            f"{config_key}.scope.sites: every entry was rejected as unknown. "
            f"Provide at least one of {sorted(allowed)}, "
            "or remove the key to use the default."
        )
    return frozenset(cleaned)


def parse_constraints_segment(
    data: dict | None,
    *,
    source: str = "<config>",
) -> dict[str, Any]:
    """Parse the ``constraints_segment:`` block (SPEC §3.7).

    Returns a dict with whichever of ``compact`` / ``include_skipped`` /
    ``sites`` were present (typed). Missing keys are absent from the
    returned dict so the merge step (project tier wins) can layer
    cleanly. Raises ``ConfigValidationError`` on empty ``scope.sites``.
    """
    if not isinstance(data, dict):
        return {}
    raw = data.get("constraints_segment")
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        log.warning(
            "%s: 'constraints_segment' must be a mapping; ignoring", source
        )
        return {}
    out: dict[str, Any] = {}
    if "compact" in raw:
        out["compact"] = bool(raw["compact"])
    if "include_skipped" in raw:
        out["include_skipped"] = bool(raw["include_skipped"])
    # Lazy import: ``agent_folders`` lives in the orchestration layer
    # and depends on this module being importable for ``build_gate_settings``;
    # importing it at module-load time here would create an import cycle.
    from claudechic.workflows.agent_folders import CONSTRAINTS_SEGMENT_SITES

    sites = _parse_scope_sites(
        raw.get("scope"),
        allowed=CONSTRAINTS_SEGMENT_SITES,
        config_key="constraints_segment",
        source=source,
    )
    if sites is not None:
        out["sites"] = sites
    return out


def parse_environment_segment(
    data: dict | None,
    *,
    source: str = "<config>",
) -> dict[str, Any]:
    """Parse the ``environment_segment:`` block (SPEC §3.11).

    ``enabled`` is preserved as a tri-state value: when present it is
    coerced to bool; when absent it is left out of the returned dict so
    the caller can defer to the workflow manifest opt-in (SPEC §3.11
    "User-tier `environment_segment.enabled` overrides the manifest
    default in either direction"). Raises ``ConfigValidationError`` on
    empty ``scope.sites``.
    """
    if not isinstance(data, dict):
        return {}
    raw = data.get("environment_segment")
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        log.warning(
            "%s: 'environment_segment' must be a mapping; ignoring", source
        )
        return {}
    out: dict[str, Any] = {}
    if "enabled" in raw:
        out["enabled"] = bool(raw["enabled"])
    if "compact" in raw:
        out["compact"] = bool(raw["compact"])
    from claudechic.workflows.agent_folders import ENVIRONMENT_SEGMENT_SITES

    sites = _parse_scope_sites(
        raw.get("scope"),
        allowed=ENVIRONMENT_SEGMENT_SITES,
        config_key="environment_segment",
        source=source,
    )
    if sites is not None:
        out["sites"] = sites
    return out


@dataclass(frozen=True)
class ProjectConfig:
    """Per-project configuration from .claudechic.yaml.

    Replaces the former CopierAnswers class. Loaded once at app startup.
    All fields have sensible defaults so claudechic works with no config file.

    The ``constraints_segment`` and ``environment_segment`` fields hold
    dict-form overrides (only the keys actually present in the project
    YAML). They are merged on top of the user-tier values by
    :func:`build_gate_settings`. Empty dicts mean "no project-tier
    override".
    """

    guardrails: bool = True
    hints: bool = True
    disabled_workflows: frozenset[str] = field(default_factory=frozenset)
    disabled_ids: frozenset[str] = field(default_factory=frozenset)
    constraints_segment: dict[str, Any] = field(default_factory=dict)
    environment_segment: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, project_dir: Path) -> ProjectConfig:
        """Load from <project_dir>/.claudechic/config.yaml, or return defaults if missing/corrupt."""
        config_path = project_dir / ".claudechic" / "config.yaml"
        if not config_path.is_file():
            return cls()
        try:
            with config_path.open(encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            if not isinstance(data, dict):
                return cls()
            raw_wf = data.get("disabled_workflows", [])
            raw_ids = data.get("disabled_ids", [])
            return cls(
                guardrails=bool(data.get("guardrails", True)),
                hints=bool(data.get("hints", True)),
                disabled_workflows=frozenset(raw_wf)
                if isinstance(raw_wf, list)
                else frozenset(),
                disabled_ids=frozenset(raw_ids)
                if isinstance(raw_ids, list)
                else frozenset(),
                constraints_segment=parse_constraints_segment(
                    data, source=str(config_path)
                ),
                environment_segment=parse_environment_segment(
                    data, source=str(config_path)
                ),
            )
        except ConfigValidationError:
            # Validation errors must not be silently swallowed -- they
            # signal a user typo (empty scope.sites). Bubble up so the
            # caller (or test) sees the explicit failure.
            raise
        except (yaml.YAMLError, OSError):
            log.debug(
                "Corrupt or unreadable .claudechic/config.yaml at %s, using defaults",
                config_path,
                exc_info=True,
            )
            return cls()

    def save(self, project_dir: Path) -> None:
        """Atomically write this config to <project_dir>/.claudechic/config.yaml.

        Symmetric with :meth:`load`. Creates the parent ``.claudechic/``
        directory if absent.
        """
        config_path = project_dir / ".claudechic" / "config.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        data: dict[str, Any] = {
            "guardrails": self.guardrails,
            "hints": self.hints,
            "disabled_workflows": sorted(self.disabled_workflows),
            "disabled_ids": sorted(self.disabled_ids),
        }
        if self.constraints_segment:
            data["constraints_segment"] = _segment_to_yaml(self.constraints_segment)
        if self.environment_segment:
            data["environment_segment"] = _segment_to_yaml(self.environment_segment)
        fd, tmp_path = tempfile.mkstemp(dir=config_path.parent, suffix=".yaml")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                yaml.dump(data, f, default_flow_style=False)
            os.replace(tmp_path, config_path)
        except Exception:
            with contextlib.suppress(OSError):
                os.unlink(tmp_path)
            raise


def _segment_to_yaml(seg: dict[str, Any]) -> dict[str, Any]:
    """Convert an in-memory segment dict back to YAML-friendly form.

    The in-memory form stores ``sites`` as a frozenset; YAML wants a
    sorted list. Other keys pass through unchanged.
    """
    out: dict[str, Any] = {}
    for k, v in seg.items():
        if k == "sites":
            out.setdefault("scope", {})["sites"] = sorted(v)
        else:
            out[k] = v
    return out


def build_gate_settings(
    user_config: dict | None = None,
    project_config: ProjectConfig | None = None,
):
    """Build a ``GateSettings`` instance from user + project tiers.

    Project tier wins per-key (SPEC §3.7, §3.11). Imported lazily to
    keep ``claudechic.config`` free of any leaf-package -> orchestration
    upward import; ``GateSettings`` lives in
    ``claudechic.workflows.agent_folders``.
    """
    from claudechic.workflows.agent_folders import (  # local import: avoids cycle
        ConstraintsSegmentSettings,
        EnvironmentSegmentSettings,
        GateSettings,
    )

    user_cs: dict[str, Any] = {}
    user_es: dict[str, Any] = {}
    if isinstance(user_config, dict):
        user_cs = parse_constraints_segment(user_config, source=str(CONFIG_PATH))
        user_es = parse_environment_segment(user_config, source=str(CONFIG_PATH))

    proj_cs: dict[str, Any] = {}
    proj_es: dict[str, Any] = {}
    if project_config is not None:
        proj_cs = project_config.constraints_segment or {}
        proj_es = project_config.environment_segment or {}

    # Project tier wins per-key.
    cs = {**user_cs, **proj_cs}
    es = {**user_es, **proj_es}

    cs_kwargs: dict[str, Any] = {}
    if "compact" in cs:
        cs_kwargs["compact"] = cs["compact"]
    if "include_skipped" in cs:
        cs_kwargs["include_skipped"] = cs["include_skipped"]
    if "sites" in cs:
        cs_kwargs["sites"] = cs["sites"]

    es_kwargs: dict[str, Any] = {}
    if "enabled" in es:
        es_kwargs["enabled"] = es["enabled"]
    if "compact" in es:
        es_kwargs["compact"] = es["compact"]
    if "sites" in es:
        es_kwargs["sites"] = es["sites"]

    return GateSettings(
        constraints_segment=ConstraintsSegmentSettings(**cs_kwargs),
        environment_segment=EnvironmentSegmentSettings(**es_kwargs),
    )
