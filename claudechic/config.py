"""Configuration management for claudechic via ~/.claude/.claudechic.yaml."""

from __future__ import annotations

import contextlib
import logging
import os
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import yaml

log = logging.getLogger(__name__)

CONFIG_PATH = Path.home() / ".claude" / ".claudechic.yaml"
_OLD_CONFIG_PATH = Path.home() / ".claude" / "claudechic.yaml"


def _load() -> tuple[dict, bool]:
    """Load config from disk, creating file atomically if missing.

    Returns (config_dict, is_new_install).
    """
    new_install = False

    # Migrate from old config path if it exists and new doesn't
    if not CONFIG_PATH.exists() and _OLD_CONFIG_PATH.exists():
        _OLD_CONFIG_PATH.rename(CONFIG_PATH)
    elif _OLD_CONFIG_PATH.exists():
        _OLD_CONFIG_PATH.unlink()

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
        config.setdefault("default_permission_mode", "default")
        config.setdefault(
            "show_message_metadata", True
        )  # Show timestamp/tokens by default
        # Migrate legacy vim key to vi-mode
        if "vim" in config:
            config["vi-mode"] = config.pop("vim")
            _save(config)
    else:
        # New install - create config with fresh ID and save
        config = {
            "analytics": {"enabled": True, "id": str(uuid.uuid4())},
            "recent-tools-expanded": 2,
            "default_permission_mode": "default",
            "show_message_metadata": True,  # Show timestamp/tokens by default
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


@dataclass(frozen=True)
class ProjectConfig:
    """Per-project configuration from .claudechic.yaml.

    Replaces the former CopierAnswers class. Loaded once at app startup.
    All fields have sensible defaults so claudechic works with no config file.
    """

    guardrails: bool = True
    hints: bool = True
    disabled_workflows: frozenset[str] = field(default_factory=frozenset)
    disabled_ids: frozenset[str] = field(default_factory=frozenset)

    @classmethod
    def load(cls, project_dir: Path) -> ProjectConfig:
        """Load from .claudechic.yaml, or return defaults if missing/corrupt."""
        config_path = project_dir / ".claudechic.yaml"
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
            )
        except (yaml.YAMLError, OSError):
            log.debug(
                "Corrupt or unreadable .claudechic.yaml at %s, using defaults",
                config_path,
                exc_info=True,
            )
            return cls()
