"""Custom trigger conditions for the hints pipeline.

Contains trigger implementations beyond the basic AlwaysTrue.
Each trigger checks disk/config state and returns bool.

LEAF MODULE: stdlib only. No imports from workflows/, checks/, or guardrails/.

Note: ``ContextDocsDrift`` was removed in Group D (per SPEC §4.5). The
upgrade-drift detection mechanism was superseded by the idempotent
``install_awareness_rules()`` routine (see ``claudechic.awareness_install``)
which auto-installs / updates / removes claudechic-prefixed Claude rules
on every startup.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)
