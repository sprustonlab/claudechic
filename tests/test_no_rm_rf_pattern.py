"""Regression coverage for the bundled global ``no_rm_rf`` guardrail pattern.

Other guardrail tests use inline rule fixtures; this one asserts the actual
``claudechic/defaults/global/rules.yaml`` pattern so broadening/narrowing it
is a deliberate, test-visible change.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

_RULES = Path(__file__).resolve().parents[1] / "claudechic/defaults/global/rules.yaml"


def _pattern() -> re.Pattern[str]:
    entries = yaml.safe_load(_RULES.read_text(encoding="utf-8"))
    rule = next(e for e in entries if e["id"] == "no_rm_rf")
    return re.compile(rule["detect"]["pattern"])


BLOCK = [
    "rm -rf /",
    "rm -rf /home/moharb/data",
    "rm  -rf   /tmp/foo",
    "rm -fr /",
    "rm -Rf /",
    "rm -rfv /",
    "rm -r -f /",
    "rm -f -r /",
    "rm --recursive --force /",
    "rm --force --recursive /",
    "rm -rf ~",
    "rm -rf ~/data",
    "rm -rf $HOME",
    "rm -rf ${HOME}",
    "rm -rf ${HOME}/x",
    "sudo rm -rf /",
    "rm -rf -- /",
    "rm -rf /*",
]

ALLOW = [
    "rm -rf demo_preview/",
    "rm -rf ./demo_preview",
    "rm -rf build",
    "rm -r node_modules",
    "rm -f file.txt",
    "rm -rf $HOMELAB",  # $HOME\b must not match $HOMELAB
    "confirm -rf /path",  # \brm must not match inside 'confirm'
    "git rm -rf src/old",  # real relative target
]


def test_no_rm_rf_blocks_root_and_home_targets():
    rx = _pattern()
    for cmd in BLOCK:
        assert rx.search(cmd), f"expected {cmd!r} to be blocked"


def test_no_rm_rf_allows_relative_and_lookalikes():
    rx = _pattern()
    for cmd in ALLOW:
        assert not rx.search(cmd), f"expected {cmd!r} to be allowed"
