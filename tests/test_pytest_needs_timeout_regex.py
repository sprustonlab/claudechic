"""Component E -- ``pytest_needs_timeout`` warn rule regex coverage.

The rule's regex pattern is loaded at runtime from
``claudechic/defaults/global/rules.yaml`` so this test fails (rather than
silently drifting) if the rule is removed, renamed, or its regex
changed without the case list also being updated.

Cases are split into three categories per TEST_SPECIFICATION.md:

* ``MUST_MATCH`` -- bare invocations the regex must flag (no ``--timeout``).
* ``MUST_NOT_MATCH`` -- invocations / strings the regex must leave alone.
* ``KNOWN_LIMIT`` -- cases that *should* match (intent: nudge the user)
  but the current regex does not. Marked ``xfail``; flip to
  ``MUST_MATCH`` when the regex is tightened.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

RULES_YAML = (
    Path(__file__).resolve().parent.parent
    / "claudechic"
    / "defaults"
    / "global"
    / "rules.yaml"
)


def _load_pytest_needs_timeout_pattern() -> str:
    """Load the live regex from ``rules.yaml``.

    Tests built on top of this loader fail loudly if the rule is missing
    or renamed -- by design.
    """
    with RULES_YAML.open(encoding="utf-8") as fh:
        rules = yaml.safe_load(fh)
    if not isinstance(rules, list):
        raise AssertionError(
            f"Expected rules.yaml to be a list of rules; got {type(rules).__name__}"
        )
    for rule in rules:
        if isinstance(rule, dict) and rule.get("id") == "pytest_needs_timeout":
            detect = rule.get("detect")
            if not isinstance(detect, dict) or "pattern" not in detect:
                raise AssertionError(
                    "pytest_needs_timeout rule is missing a 'detect.pattern' field"
                )
            return detect["pattern"]
    raise AssertionError("pytest_needs_timeout rule not found in rules.yaml")


PYTEST_NEEDS_TIMEOUT_PATTERN = _load_pytest_needs_timeout_pattern()
PYTEST_NEEDS_TIMEOUT_REGEX = re.compile(PYTEST_NEEDS_TIMEOUT_PATTERN)


# ---------------------------------------------------------------------------
# Case lists
# ---------------------------------------------------------------------------

MUST_MATCH: list[str] = [
    # Original 15 (spec)
    "pytest",
    "pytest tests/foo.py",
    "pytest -v",
    "pytest -k foo",
    "python -m pytest",
    "python3 -m pytest",
    "python3.11 -m pytest",
    "python3.12 -m pytest -v",
    "uv run pytest",
    "uv run pytest tests/",
    "uvx pytest tests/",
    "poetry run pytest",
    "cd subdir && pytest",
    "cd subdir; pytest",
    "( cd subdir && pytest )",
    # Promoted from KNOWN_LIMIT after regex was tightened by impl_data_docs:
    # wrapper invocations (time/env/xargs/hatch/nox/make) and the
    # ambiguous --timeout substring cases now match.
    "time pytest",
    "ENV=1 pytest",
    "xargs pytest",
    "hatch run pytest",
    "nox -s pytest",
    "make pytest",
    "pytest --timeout-method=signal",
    "pytest --timeoutblahblah=30",
]

MUST_NOT_MATCH: list[str] = [
    "pytest --timeout=30",
    "pytest -v --timeout=10",
    "uv run pytest --timeout=5",
    "python -m pytest --timeout=30 -v",
    "pytest --timeout=30 tests/",
    "grep pytest .",
    'grep -c "pytest"',
    "grep -rn pytest claudechic/",
    "rg pytest",
    "rg -n pytest claudechic/",
    "cat docs/pytest.md",
    "head pytest_log.txt",
    "tail -n 100 pytest_log.txt",
    "# run pytest later",
    'echo "pytest"',
    "ls pytest_helpers/",
    "pytester",
    "pytest_log.txt",
    "find . -name pytest_helper.py",
]

# Cases the regex *should* flag but still does not. xfail-marked so
# any further tightening flips them to xpass and the test then fails
# loudly -- nudging us to recategorise them.
#
# Two cases remain after the impl_data_docs tightening:
#
# * ``bash -c "pytest"`` -- the inner pytest is inside quotes; the
#   regex sees a leading ``bash -c "`` which is neither start-of-line
#   nor a [;&|] separator, and ``bash`` is not in the wrapper list.
# * ``pytest && pytest --timeout=30`` -- the second invocation has
#   ``--timeout`` and the negative lookahead is ``.*--timeout`` (still
#   spans the whole line, not just the current pytest's args), so the
#   first (untimed) pytest is also suppressed.
KNOWN_LIMIT: list[str] = [
    'bash -c "pytest"',
    "pytest && pytest --timeout=30",
]


# ---------------------------------------------------------------------------
# Sanity guards
# ---------------------------------------------------------------------------


def test_e_case_count_is_44() -> None:
    """Spec freezes 44 cases total -- guard against silent drift.

    Original split was 15 / 19 / 10 (must / must-not / known-limit).
    impl_data_docs tightened the regex so 8 of the 10 known limits now
    flag correctly and were promoted to MUST_MATCH; the new split is
    23 / 19 / 2 with the total unchanged at 44.
    """
    assert len(MUST_MATCH) == 23
    assert len(MUST_NOT_MATCH) == 19
    assert len(KNOWN_LIMIT) == 2
    assert len(MUST_MATCH) + len(MUST_NOT_MATCH) + len(KNOWN_LIMIT) == 44


def test_e_pattern_loaded_from_rules_yaml() -> None:
    """The pattern under test must come from rules.yaml (not redefined)."""
    # The string literal here is purely a redundancy check; if anyone
    # hardcodes the pattern in this test file, lint/grep will spot it.
    assert PYTEST_NEEDS_TIMEOUT_PATTERN
    assert "pytest" in PYTEST_NEEDS_TIMEOUT_PATTERN
    assert "--timeout" in PYTEST_NEEDS_TIMEOUT_PATTERN


# ---------------------------------------------------------------------------
# Parametrised regex tests (44 cases across 3 categories)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("cmd", MUST_MATCH)
def test_e_pytest_needs_timeout_regex_must_match(cmd: str) -> None:
    """The regex must flag bare pytest invocations missing ``--timeout``."""
    assert PYTEST_NEEDS_TIMEOUT_REGEX.search(cmd) is not None, (
        f"Expected MATCH but got no match for: {cmd!r}\n"
        f"Pattern: {PYTEST_NEEDS_TIMEOUT_PATTERN}"
    )


@pytest.mark.parametrize("cmd", MUST_NOT_MATCH)
def test_e_pytest_needs_timeout_regex_must_not_match(cmd: str) -> None:
    """The regex must leave timed invocations and unrelated strings alone."""
    assert PYTEST_NEEDS_TIMEOUT_REGEX.search(cmd) is None, (
        f"Expected NO match but the regex flagged: {cmd!r}\n"
        f"Pattern: {PYTEST_NEEDS_TIMEOUT_PATTERN}"
    )


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Known regex limitations: pytest invocations inside quoted "
        "wrappers (bash -c) and chained invocations where a *later* "
        "pytest carries --timeout but an *earlier* one does not. "
        "Promote to MUST_MATCH when the regex tightens."
    ),
)
@pytest.mark.parametrize("cmd", KNOWN_LIMIT)
def test_e_pytest_needs_timeout_regex_known_limit(cmd: str) -> None:
    """Cases the regex *should* eventually flag (currently xfail)."""
    assert PYTEST_NEEDS_TIMEOUT_REGEX.search(cmd) is not None, (
        f"Known limitation -- not yet flagged: {cmd!r}"
    )
