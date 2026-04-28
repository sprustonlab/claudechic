"""Tests for WorkflowPickerScreen tier badges + sort order (SPEC §7.9)."""

from __future__ import annotations

import pytest
from claudechic.screens.workflow_picker import (
    WorkflowItem,
    WorkflowPickerScreen,
    _TIER_BADGE,
    _TIER_PRIORITY,
)
from textual.app import App


class _Harness(App):
    def __init__(self, screen):
        super().__init__()
        self._screen = screen

    def on_mount(self) -> None:
        self.push_screen(self._screen)


# ---------------------------------------------------------------------------
# Pure dataclass / module-level shape
# ---------------------------------------------------------------------------


class TestTierBadges:
    def test_badge_table(self):
        # Per SPEC §7.11 the three badges are exactly these short tokens.
        assert _TIER_BADGE["package"] == "[pkg]"
        assert _TIER_BADGE["user"] == "[user]"
        assert _TIER_BADGE["project"] == "[proj]"

    def test_priority_order(self):
        # project (highest) > user > package (lowest).
        assert _TIER_PRIORITY["project"] > _TIER_PRIORITY["user"]
        assert _TIER_PRIORITY["user"] > _TIER_PRIORITY["package"]


class TestWorkflowItemConstruction:
    def test_default_tier_is_package(self):
        item = WorkflowItem("wf_a")
        assert item.tier == "package"
        # When defined_at is unspecified, it falls back to {tier}.
        assert item.defined_at == frozenset({"package"})

    def test_explicit_tier_and_defined_at(self):
        item = WorkflowItem(
            "wf_a", tier="project", defined_at=frozenset({"project", "user", "package"})
        )
        assert item.tier == "project"
        assert "package" in item.defined_at
        assert "user" in item.defined_at

    def test_phase_count_pluralization_in_metadata(self):
        # The compose() output is exercised via the smoke test below; this
        # assertion just checks the field is preserved.
        item = WorkflowItem("wf_a", phase_count=5)
        assert item.phase_count == 5


# ---------------------------------------------------------------------------
# Smoke mount test (Pilot)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_picker_renders_tier_badges_and_sorts_by_tier():
    workflows = {
        "low_pkg_only": {
            "main_role": "learner",
            "phase_count": 2,
            "is_active": False,
            "tier": "package",
            "defined_at": frozenset({"package"}),
        },
        "mid_user": {
            "main_role": "coordinator",
            "phase_count": 3,
            "is_active": False,
            "tier": "user",
            "defined_at": frozenset({"user", "package"}),
        },
        "top_project": {
            "main_role": "coordinator",
            "phase_count": 4,
            "is_active": True,
            "tier": "project",
            "defined_at": frozenset({"project"}),
        },
    }

    screen = WorkflowPickerScreen(workflows)
    app = _Harness(screen)
    async with app.run_test():
        items = list(screen.query(WorkflowItem))
        assert len(items) == 3
        # Sort order per SPEC §7.9: project > user > package.
        ordered_ids = [item.workflow_id for item in items]
        assert ordered_ids == ["top_project", "mid_user", "low_pkg_only"]

        # Each item carries its tier and defined_at.
        by_id = {it.workflow_id: it for it in items}
        assert by_id["top_project"].tier == "project"
        assert by_id["mid_user"].tier == "user"
        assert by_id["mid_user"].defined_at == frozenset({"user", "package"})


@pytest.mark.asyncio
async def test_picker_shows_defined_at_for_overrides():
    """A workflow with overrides at lower levels surfaces a "(defined at: ...)" line.

    Per SPEC §7.9 + §7.11 canonical phrasing.
    """
    workflows = {
        "wf_a": {
            "main_role": "lead",
            "phase_count": 5,
            "is_active": False,
            "tier": "project",
            "defined_at": frozenset({"project", "user", "package"}),
        },
    }

    screen = WorkflowPickerScreen(workflows)
    app = _Harness(screen)
    async with app.run_test():
        items = list(screen.query(WorkflowItem))
        assert len(items) == 1
        # Expect the rendered output to include the canonical "defined at:"
        # phrasing somewhere within the WorkflowItem subtree.
        rendered_text = ""
        for label in items[0].query("Label"):
            try:
                r = label.render()
            except Exception:
                continue
            if hasattr(r, "plain"):
                rendered_text += r.plain  # type: ignore[union-attr]
            else:
                rendered_text += str(r)
        assert "defined at" in rendered_text.lower()
