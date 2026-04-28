"""Tests for DisabledWorkflowsScreen and DisabledIdsScreen encoding logic.

Per SPEC §7.6 and §7.7: tier-targeted entries take the form ``<tier>:<id>``
(or ``<tier>:<namespace>:<bare_id>`` for ``disabled_ids``). Bare entries
have no leading tier prefix. The screens collapse to bare when every
tier-instance of an id is disabled.
"""

from __future__ import annotations

from claudechic.screens.disabled_ids import (
    _split_id_entry,
    encode_disabled_id_set,
)
from claudechic.screens.disabled_workflows import (
    _split_entry,
    encode_disabled_set,
)


class TestWorkflowEntryParsing:
    def test_bare_id(self):
        assert _split_entry("project_team") == ("*", "project_team")

    def test_tier_prefixed_package(self):
        assert _split_entry("package:project_team") == ("package", "project_team")

    def test_tier_prefixed_user(self):
        assert _split_entry("user:my_flow") == ("user", "my_flow")

    def test_tier_prefixed_project(self):
        assert _split_entry("project:team_specific") == ("project", "team_specific")

    def test_unknown_prefix_treated_as_bare(self):
        # Per SPEC §3.6: unknown prefixes fall back to bare semantics.
        assert _split_entry("unknown:thing") == ("*", "unknown:thing")


class TestIdEntryParsing:
    def test_bare_qualified_id(self):
        # Item ids are namespace:bare_id; without leading tier prefix it's bare.
        assert _split_id_entry("global:context-docs-outdated") == (
            "*",
            "global:context-docs-outdated",
        )

    def test_tier_prefixed_user(self):
        # tier:namespace:bare_id
        assert _split_id_entry("user:lab/onboarding-rule") == (
            "user",
            "lab/onboarding-rule",
        )

    def test_tier_prefixed_project_with_nested_namespace(self):
        assert _split_id_entry("project:my_workflow:setup-reminder") == (
            "project",
            "my_workflow:setup-reminder",
        )

    def test_tier_prefixed_package(self):
        assert _split_id_entry("package:global:no-rm-rf") == (
            "package",
            "global:no-rm-rf",
        )

    def test_no_colon(self):
        # Defensive — disabled_ids entries should always have at least
        # namespace:id form, but the parser handles bare strings.
        assert _split_id_entry("orphan") == ("*", "orphan")


# ---------------------------------------------------------------------------
# Workflow encoding (SPEC §7.6)
# ---------------------------------------------------------------------------


class TestWorkflowEncoding:
    def test_no_rows_disabled_returns_empty(self):
        rows = [
            ("project", "wf_a", False),
            ("user", "wf_a", False),
        ]
        assert encode_disabled_set(rows) == frozenset()

    def test_single_tier_targeted(self):
        rows = [
            ("project", "wf_a", True),
            ("user", "wf_a", False),
            ("package", "wf_a", False),
        ]
        assert encode_disabled_set(rows) == frozenset({"project:wf_a"})

    def test_two_tiers_targeted_no_collapse(self):
        rows = [
            ("project", "wf_a", True),
            ("user", "wf_a", True),
            ("package", "wf_a", False),
        ]
        assert encode_disabled_set(rows) == frozenset({"project:wf_a", "user:wf_a"})

    def test_all_tiers_disabled_collapses_to_bare(self):
        rows = [
            ("project", "wf_a", True),
            ("user", "wf_a", True),
            ("package", "wf_a", True),
        ]
        assert encode_disabled_set(rows) == frozenset({"wf_a"})

    def test_workflow_with_only_one_tier_collapses(self):
        # If a workflow exists at only one tier and that tier is disabled,
        # "every tier-instance disabled" => bare collapse.
        rows = [("user", "lone_wf", True)]
        assert encode_disabled_set(rows) == frozenset({"lone_wf"})

    def test_independent_workflows(self):
        # wf_a has TWO tier-instances, only one disabled → tier-targeted.
        # wf_b has THREE tier-instances, all disabled → bare collapse.
        rows = [
            ("project", "wf_a", True),
            ("user", "wf_a", False),
            ("user", "wf_b", True),
            ("package", "wf_b", True),
            ("project", "wf_b", True),
        ]
        result = encode_disabled_set(rows)
        assert "project:wf_a" in result
        assert "wf_b" in result
        assert "wf_a" not in result  # not every wf_a instance disabled


# ---------------------------------------------------------------------------
# ID encoding (SPEC §7.7)
# ---------------------------------------------------------------------------


class TestIdEncoding:
    def test_namespace_preserved(self):
        rows = [
            ("user", "lab/onboarding-rule", True),
            ("package", "lab/onboarding-rule", False),
        ]
        assert encode_disabled_id_set(rows) == frozenset({"user:lab/onboarding-rule"})

    def test_bare_collapse_with_namespace(self):
        rows = [
            ("user", "global:context-docs-outdated", True),
            ("package", "global:context-docs-outdated", True),
        ]
        # All tier-instances disabled → bare collapse retains namespace.
        assert encode_disabled_id_set(rows) == frozenset(
            {"global:context-docs-outdated"}
        )

    def test_tier_prefixed_with_nested_namespace(self):
        # Per SPEC §8.2: tier-targeted disabled_ids has shape
        # <tier>:<namespace>:<bare_id>; ensure encoder forms it correctly.
        rows = [
            ("project", "my_workflow:setup-reminder", True),
            ("user", "my_workflow:setup-reminder", False),
        ]
        assert encode_disabled_id_set(rows) == frozenset(
            {"project:my_workflow:setup-reminder"}
        )

    def test_no_rows_disabled(self):
        rows = [
            ("project", "global:rule-a", False),
            ("user", "global:rule-a", False),
        ]
        assert encode_disabled_id_set(rows) == frozenset()
