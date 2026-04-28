"""claudechic-awareness install routine.

Idempotent NEW / UPDATE / SKIP / DELETE install of bundled context docs
into ``~/.claude/rules/claudechic_<name>.md``. Runs at every claudechic
startup so that every Claude Code session in every project auto-loads
claudechic's bundled rules via the SDK ``setting_sources`` loader.

LEAF MODULE: stdlib + ``claudechic.config`` + ``claudechic.errors`` only.
No imports from ``app.py``, agent code, UI widgets, or workflow engine.

Boundary classification (per SPEC §4.8 and §9): the writes (NEW + UPDATE)
and unlinks (DELETE pass) of this module are one of the three explicit
``.claude/``-area exceptions allowed by the boundary rule. The routine
MUST NOT write or unlink any path in ``~/.claude/rules/`` whose basename
does not match ``claudechic_*.md``; symlinks at any matching basename are
NEVER read, written, or unlinked (user-managed inodes).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from claudechic.config import CONFIG
from claudechic.errors import log

CLAUDE_RULES_DIR = Path.home() / ".claude" / "rules"
PKG_CONTEXT_DIR = Path(__file__).parent / "context"
INSTALL_PREFIX = "claudechic_"

# Regex that bounds the DELETE pass to claudechic-prefixed markdown files
# at the immediate child level of ``~/.claude/rules/``. The pattern
# explicitly forbids path separators so the predicate is basename-only.
_PREFIXED_BASENAME_RE = re.compile(r"^claudechic_[^/]+\.md$")


@dataclass(frozen=True)
class InstallResult:
    """Outcome of one ``install_awareness_rules()`` call.

    Per SPEC §4.1: five fields. The four ``list[str]`` fields contain the
    bundled ``<name>`` (``Path.stem`` of the bundled ``<name>.md``) for
    each branch. ``skipped_disabled`` is ``True`` iff the routine
    short-circuited because ``awareness.install`` is ``False`` and
    ``force=False``; in that case all four lists are empty and the routine
    performed zero file I/O.
    """

    new: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)
    skipped_disabled: bool = False


def _toggle_enabled() -> bool:
    """Read the ``awareness.install`` user-tier toggle (default ``True``)."""
    awareness = CONFIG.get("awareness")
    if not isinstance(awareness, dict):
        return True
    value = awareness.get("install", True)
    return bool(value)


def _bundled_target(name: str) -> Path:
    """Resolve the install target for a bundled ``<name>.md`` file."""
    return CLAUDE_RULES_DIR / f"{INSTALL_PREFIX}{name}.md"


def install_awareness_rules(force: bool = False) -> InstallResult:
    """Install bundled context docs into ``~/.claude/rules/``.

    Args:
        force: If ``True``, ignore the ``awareness.install`` config toggle
            and run the full install routine. Used by the
            ``/onboarding context_docs`` phase to re-install on demand.

    Returns:
        :class:`InstallResult` with per-branch ``<name>`` lists.

    Behavior (per SPEC §4.2):

    - When ``awareness.install`` is ``False`` and ``force=False``: returns
      immediately with ``skipped_disabled=True`` and performs ZERO file
      I/O (no read, no write, no unlink, no mkdir).
    - Otherwise creates ``~/.claude/rules/`` if absent (idempotent
      ``parents=True, exist_ok=True``).
    - For each ``<name>.md`` in ``claudechic/context/`` (top-level only,
      no recursion): NEW (target absent) / UPDATE (target differs) /
      SKIP (target identical) at ``~/.claude/rules/claudechic_<name>.md``.
    - DELETE pass: any ``~/.claude/rules/claudechic_*.md`` whose stem-
      minus-prefix is NOT in the bundled catalog is unlinked. The pass
      is bounded to direct children of ``~/.claude/rules/`` and to the
      ``claudechic_*.md`` basename pattern.
    - Symlink guard: any target path that ``is_symlink()`` is skipped
      (no read, no write, no unlink) with a WARNING log. Applies to
      both the per-bundled-file loop AND the DELETE pass.
    """
    if not force and not _toggle_enabled():
        log.info("awareness install: skipped (awareness.install=False; no file I/O)")
        return InstallResult(skipped_disabled=True)

    result = InstallResult()

    # Idempotent parent-directory mkdir. Safe whether ~/.claude/ exists or not.
    CLAUDE_RULES_DIR.mkdir(parents=True, exist_ok=True)

    # Bundled catalog: top-level *.md files in the package context dir.
    # No recursion into subdirectories.
    bundled_files = sorted(PKG_CONTEXT_DIR.glob("*.md"))
    bundled_names = {p.stem for p in bundled_files}

    # Per-bundled-file loop: NEW / UPDATE / SKIP.
    for bundled in bundled_files:
        name = bundled.stem
        target = _bundled_target(name)

        # Symlink guard MUST run before any read/write/unlink at the path.
        if target.is_symlink():
            log.warning(
                "awareness install: target ~/.claude/rules/%s is a symlink; "
                "treating as user-managed; skipping",
                target.name,
            )
            continue

        try:
            bundled_bytes = bundled.read_bytes()
        except OSError:
            log.warning(
                "awareness install: failed to read bundled %s; skipping",
                bundled,
                exc_info=True,
            )
            continue

        if not target.exists():
            # NEW
            try:
                target.write_bytes(bundled_bytes)
                result.new.append(name)
            except OSError:
                log.warning(
                    "awareness install: failed to install %s",
                    target,
                    exc_info=True,
                )
            continue

        # Target exists and is a regular file (symlink already filtered).
        try:
            target_bytes = target.read_bytes()
        except OSError:
            log.warning(
                "awareness install: failed to read existing %s; skipping",
                target,
                exc_info=True,
            )
            continue

        if target_bytes == bundled_bytes:
            # SKIP
            result.skipped.append(name)
        else:
            # UPDATE
            try:
                target.write_bytes(bundled_bytes)
                result.updated.append(name)
            except OSError:
                log.warning(
                    "awareness install: failed to update %s",
                    target,
                    exc_info=True,
                )

    # DELETE pass: orphan cleanup. Direct children only; symlinks skipped;
    # only basenames matching ``claudechic_*.md``.
    if CLAUDE_RULES_DIR.is_dir():
        for child in sorted(CLAUDE_RULES_DIR.iterdir()):
            if not _PREFIXED_BASENAME_RE.match(child.name):
                continue
            if child.is_symlink():
                # Symlink guard also applies to the DELETE pass: never
                # unlink a user-managed symlink, even at a stale name.
                log.warning(
                    "awareness install: orphan candidate %s is a symlink; "
                    "treating as user-managed; skipping DELETE",
                    child.name,
                )
                continue
            orphan = child.stem.removeprefix(INSTALL_PREFIX)
            if orphan in bundled_names:
                # Already handled by the per-bundled-file loop above.
                continue
            try:
                child.unlink()
                result.deleted.append(orphan)
            except OSError:
                log.warning(
                    "awareness install: failed to remove orphan %s",
                    child,
                    exc_info=True,
                )

    log.info(
        "awareness install: NEW=%d UPDATE=%d SKIP=%d DELETE=%d",
        len(result.new),
        len(result.updated),
        len(result.skipped),
        len(result.deleted),
    )
    return result
