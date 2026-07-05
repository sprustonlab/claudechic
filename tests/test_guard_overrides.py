"""Per-agent guard override tests: hooks enforcement + digest classification.

Covers the runtime override map (qualified rule_id -> "on" | "off"):
- hooks.py: get_overrides callback semantics ("off" skips entirely,
  "on" bypasses scope checks but keeps trigger/pattern matching)
- digest.py: tri-state ``state`` classification and precedence
  (disabled_rules beats overrides; injections unaffected)
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from claudechic.guardrails.digest import compute_digest
from claudechic.guardrails.hits import HitLogger
from claudechic.guardrails.hooks import create_guardrail_hooks
from claudechic.workflows import register_default_parsers
from claudechic.workflows.loader import ManifestLoader

pytestmark = pytest.mark.timeout(30)


def _setup_rules(
    root: Path, rules: list[dict], injections: list[dict] | None = None
) -> ManifestLoader:
    """Create global/rules.yaml (and optionally injections.yaml), return loader."""
    global_dir = root / "global"
    global_dir.mkdir(parents=True, exist_ok=True)
    (global_dir / "rules.yaml").write_text(yaml.dump(rules), encoding="utf-8")
    if injections:
        (global_dir / "injections.yaml").write_text(
            yaml.dump(injections), encoding="utf-8"
        )
    wf_dir = root / "workflows"
    wf_dir.mkdir(exist_ok=True)

    loader = ManifestLoader(global_dir, wf_dir)
    register_default_parsers(loader)
    return loader


def _setup_workflow_rule(root: Path, wf_id: str, rule: dict) -> ManifestLoader:
    """Create a workflow manifest containing a single rule, return loader."""
    global_dir = root / "global"
    global_dir.mkdir(parents=True, exist_ok=True)
    (global_dir / "rules.yaml").write_text(yaml.dump([]), encoding="utf-8")
    wf_dir = root / "workflows" / wf_id
    wf_dir.mkdir(parents=True, exist_ok=True)
    manifest = {"workflow_id": wf_id, "rules": [rule]}
    (wf_dir / f"{wf_id}.yaml").write_text(yaml.dump(manifest), encoding="utf-8")

    loader = ManifestLoader(global_dir, wf_dir.parent)
    register_default_parsers(loader)
    return loader


async def _call_hook(hooks: dict, tool_name: str, tool_input: dict) -> dict:
    """Invoke the PreToolUse hook evaluate function."""
    matchers = hooks.get("PreToolUse", [])
    assert len(matchers) > 0, "No PreToolUse hooks created"
    hook_fn = matchers[0].hooks[0]
    return await hook_fn(
        {"tool_name": tool_name, "tool_input": tool_input},
        None,
        None,
    )


DENY_RULE = {
    "id": "no_rm_rf",
    "trigger": "PreToolUse/Bash",
    "enforcement": "deny",
    "detect": {"pattern": r"rm\s+-rf"},
    "message": "Dangerous: rm -rf not allowed",
}


@pytest.mark.asyncio
class TestHookOverrides:
    """Runtime overrides enforced through the hook pipeline."""

    async def test_force_off_allows_and_logs_no_hit(self, tmp_path):
        """Deny rule with 'off' override: allowed through, no hit recorded."""
        loader = _setup_rules(tmp_path, [DENY_RULE])
        hits_path = tmp_path / ".claudechic" / "hits.jsonl"
        hit_logger = HitLogger(hits_path)
        overrides = {"global:no_rm_rf": "off"}

        try:
            hooks = create_guardrail_hooks(
                loader=loader,
                hit_logger=hit_logger,
                get_overrides=lambda: overrides,
            )
            result = await _call_hook(hooks, "Bash", {"command": "rm -rf /"})
            assert result == {}, "Forced-off deny rule must allow through"
        finally:
            hit_logger.close()

        # No hit logged for a forced-off rule (skipped before evaluation)
        assert (
            not hits_path.exists() or not hits_path.read_text(encoding="utf-8").strip()
        ), "Forced-off rule must not log a hit"

    async def test_force_on_dormant_workflow_rule_blocks(self, tmp_path):
        """Rule from an inactive workflow blocks when forced on (trigger+pattern match)."""
        rule = {
            "id": "no_push",
            "trigger": "PreToolUse/Bash",
            "enforcement": "deny",
            "detect": {"pattern": r"git\s+push"},
            "message": "No pushing",
        }
        loader = _setup_workflow_rule(tmp_path, "proj", rule)
        hit_logger = HitLogger(tmp_path / ".claudechic" / "hits.jsonl")
        overrides = {"proj:no_push": "on"}

        try:
            hooks = create_guardrail_hooks(
                loader=loader,
                hit_logger=hit_logger,
                get_active_wf=lambda: None,  # workflow NOT active -> naturally dormant
                get_overrides=lambda: overrides,
            )
            result = await _call_hook(hooks, "Bash", {"command": "git push origin"})
            assert result.get("decision") == "block", (
                "Forced-on dormant rule must fire on matching input"
            )
        finally:
            hit_logger.close()

    async def test_force_on_still_requires_trigger_match(self, tmp_path):
        """Forced-on Bash rule must NOT fire on a different tool (Read)."""
        rule = {
            "id": "no_push",
            "trigger": "PreToolUse/Bash",
            "enforcement": "deny",
            "detect": {"pattern": r"git\s+push"},
            "message": "No pushing",
        }
        loader = _setup_workflow_rule(tmp_path, "proj", rule)
        hit_logger = HitLogger(tmp_path / ".claudechic" / "hits.jsonl")
        overrides = {"proj:no_push": "on"}

        try:
            hooks = create_guardrail_hooks(
                loader=loader,
                hit_logger=hit_logger,
                get_active_wf=lambda: None,
                get_overrides=lambda: overrides,
            )
            result = await _call_hook(
                hooks, "Read", {"file_path": "/tmp/git push notes.txt"}
            )
            assert result == {}, "Forced-on rule must still respect trigger tool"
        finally:
            hit_logger.close()

    async def test_force_on_still_requires_detect_pattern(self, tmp_path):
        """Forced-on rule must NOT fire when detect pattern does not match."""
        rule = {
            "id": "no_push",
            "trigger": "PreToolUse/Bash",
            "enforcement": "deny",
            "detect": {"pattern": r"git\s+push"},
            "message": "No pushing",
        }
        loader = _setup_workflow_rule(tmp_path, "proj", rule)
        hit_logger = HitLogger(tmp_path / ".claudechic" / "hits.jsonl")
        overrides = {"proj:no_push": "on"}

        try:
            hooks = create_guardrail_hooks(
                loader=loader,
                hit_logger=hit_logger,
                get_active_wf=lambda: None,
                get_overrides=lambda: overrides,
            )
            result = await _call_hook(hooks, "Bash", {"command": "git status"})
            assert result == {}, "Forced-on rule must still respect detect pattern"
        finally:
            hit_logger.close()

    async def test_force_on_bypasses_role_restriction(self, tmp_path):
        """Role-restricted rule fires under force-on despite role mismatch."""
        rules = [
            {
                "id": "impl_only",
                "trigger": "PreToolUse/Bash",
                "enforcement": "deny",
                "detect": {"pattern": r"make\s+deploy"},
                "message": "No deploys",
                "roles": ["implementer"],
            }
        ]
        loader = _setup_rules(tmp_path, rules)
        hit_logger = HitLogger(tmp_path / ".claudechic" / "hits.jsonl")
        overrides = {"global:impl_only": "on"}

        try:
            # Without override: role mismatch -> rule skipped
            hooks_plain = create_guardrail_hooks(
                loader=loader,
                hit_logger=hit_logger,
                agent_role="reviewer",
            )
            result = await _call_hook(hooks_plain, "Bash", {"command": "make deploy"})
            assert result == {}, "Role-mismatched rule must not fire without override"

            # With force-on: role check bypassed -> rule fires
            hooks_forced = create_guardrail_hooks(
                loader=loader,
                hit_logger=hit_logger,
                agent_role="reviewer",
                get_overrides=lambda: overrides,
            )
            result = await _call_hook(hooks_forced, "Bash", {"command": "make deploy"})
            assert result.get("decision") == "block", (
                "Forced-on rule must bypass role restriction"
            )
        finally:
            hit_logger.close()

    async def test_no_callback_regression(self, tmp_path):
        """Without get_overrides, behavior is identical to today."""
        loader = _setup_rules(tmp_path, [DENY_RULE])
        hit_logger = HitLogger(tmp_path / ".claudechic" / "hits.jsonl")

        try:
            hooks = create_guardrail_hooks(loader=loader, hit_logger=hit_logger)
            blocked = await _call_hook(hooks, "Bash", {"command": "rm -rf /"})
            assert blocked.get("decision") == "block"
            allowed = await _call_hook(hooks, "Bash", {"command": "echo hi"})
            assert allowed == {}
        finally:
            hit_logger.close()


class TestDigestOverrides:
    """Tri-state classification in compute_digest."""

    def _loader_with_all(self, tmp_path):
        """Global rule + workflow rule + global injection."""
        loader = _setup_rules(
            tmp_path,
            [DENY_RULE],
            injections=[
                {
                    "id": "tee_output",
                    "trigger": "PreToolUse/Bash",
                    "detect": {"pattern": r"pytest"},
                    "inject_value": " | tee out.log",
                }
            ],
        )
        wf_dir = tmp_path / "workflows" / "proj"
        wf_dir.mkdir(parents=True, exist_ok=True)
        manifest = {
            "workflow_id": "proj",
            "rules": [
                {
                    "id": "no_push",
                    "trigger": "PreToolUse/Bash",
                    "enforcement": "deny",
                    "detect": {"pattern": r"git\s+push"},
                    "message": "No pushing",
                }
            ],
        }
        (wf_dir / "proj.yaml").write_text(yaml.dump(manifest), encoding="utf-8")
        return loader

    def _by_id(self, entries):
        return {e.id: e for e in entries}

    def test_all_four_states(self, tmp_path):
        loader = self._loader_with_all(tmp_path)

        # No overrides: global rule active, workflow rule dormant
        by_id = self._by_id(compute_digest(loader, None, None, None))
        assert by_id["global:no_rm_rf"].state == "active"
        assert by_id["global:no_rm_rf"].active is True
        assert by_id["proj:no_push"].state == "dormant"
        assert by_id["proj:no_push"].active is False
        assert "not active" in by_id["proj:no_push"].skip_reason

        # Overrides: force global off, force workflow on
        by_id = self._by_id(
            compute_digest(
                loader,
                None,
                None,
                None,
                overrides={"global:no_rm_rf": "off", "proj:no_push": "on"},
            )
        )
        assert by_id["global:no_rm_rf"].state == "forced_off"
        assert by_id["global:no_rm_rf"].active is False
        assert by_id["global:no_rm_rf"].skip_reason == "forced off by user"
        assert by_id["proj:no_push"].state == "forced_on"
        assert by_id["proj:no_push"].active is True
        assert by_id["proj:no_push"].skip_reason == ""

    def test_disabled_rules_beats_overrides(self, tmp_path):
        loader = self._loader_with_all(tmp_path)
        by_id = self._by_id(
            compute_digest(
                loader,
                None,
                None,
                None,
                disabled_rules={"global:no_rm_rf"},
                overrides={"global:no_rm_rf": "on"},
            )
        )
        entry = by_id["global:no_rm_rf"]
        assert entry.state == "dormant"
        assert entry.active is False
        assert entry.skip_reason == "disabled by user"

    def test_forced_states_sync_with_hook_behavior(self, tmp_path):
        """Digest forced_on/forced_off classification mirrors hook enforcement.

        The GuardsPanel renders from compute_digest while enforcement runs
        through the hook; both must agree on the same override map.
        """
        loader = self._loader_with_all(tmp_path)
        overrides = {"proj:no_push": "on"}
        by_id = self._by_id(
            compute_digest(loader, None, None, None, overrides=overrides)
        )
        assert by_id["proj:no_push"].active is True, (
            "Digest must report forced-on rule as active (hook will fire it)"
        )

    def test_injections_unaffected_by_overrides(self, tmp_path):
        loader = self._loader_with_all(tmp_path)
        by_id = self._by_id(
            compute_digest(
                loader,
                None,
                None,
                None,
                overrides={"global:tee_output": "off"},
            )
        )
        inj = by_id["global:tee_output"]
        assert inj.kind == "injection"
        assert inj.state == "active", "Injections must ignore overrides"
        assert inj.active is True


@pytest.mark.asyncio
class TestAppToggleFlow:
    """App-level: clicking a guard row sets/clears agent.guard_overrides."""

    async def test_click_cycle_sets_and_clears_override(self, mock_sdk):
        from claudechic.app import ChatApp
        from claudechic.widgets import GuardItem

        app = ChatApp()
        async with app.run_test(size=(160, 50)) as pilot:
            # Populate the panel from the app's real LoadResult (repo defaults)
            app._refresh_guards_panel()
            await pilot.pause()

            agent = app.agent_mgr.active
            assert agent is not None
            assert agent.guard_overrides == {}

            items = list(app.query(GuardItem))
            assert items, "Repo default rules should populate the panel"
            active_items = [i for i in items if i.row.state == "active"]
            assert active_items, "Expected at least one active global rule"
            rule_id = active_items[0].row.rule_id

            # Click 1: active -> forced off
            await pilot.click(active_items[0])
            await pilot.pause()
            assert agent.guard_overrides == {rule_id: "off"}

            # Panel re-rendered: the row now shows forced_off
            item = next(i for i in app.query(GuardItem) if i.row.rule_id == rule_id)
            assert item.row.state == "forced_off"

            # Click 2: forced_off -> override cleared (back to natural active)
            await pilot.click(item)
            await pilot.pause()
            assert agent.guard_overrides == {}
            item = next(i for i in app.query(GuardItem) if i.row.rule_id == rule_id)
            assert item.row.state == "active"

    async def test_overrides_do_not_leak_between_agents(self, mock_sdk):
        from claudechic.agent import Agent
        from claudechic.app import ChatApp

        app = ChatApp()
        async with app.run_test():
            first = app.agent_mgr.active
            assert first is not None
            first.guard_overrides["global:no_rm_rf"] = "off"

            second = Agent(name="other", cwd=first.cwd)
            assert second.guard_overrides == {}, (
                "Overrides are per-agent state and must not leak"
            )


@pytest.mark.asyncio
class TestGuardsPanelWidget:
    """GuardsPanel rendering and click-to-toggle message flow."""

    def _rows(self):
        from claudechic.widgets import GuardRow

        return [
            GuardRow(
                rule_id="proj:no_push",
                display_id="proj:no_push",
                enforcement="deny",
                state="dormant",
                message="No pushing",
            ),
            GuardRow(
                rule_id="global:no_rm_rf",
                display_id="no_rm_rf",
                enforcement="deny",
                state="active",
                message="Dangerous: rm -rf not allowed",
            ),
        ]

    async def test_update_guards_sorts_and_counts(self):
        from textual.app import App, ComposeResult

        from claudechic.widgets import GuardItem, GuardsPanel

        class TestApp(App):
            def compose(self) -> ComposeResult:
                yield GuardsPanel(id="guards-panel")

        app = TestApp()
        async with app.run_test() as pilot:
            panel = app.query_one(GuardsPanel)
            panel.update_guards(self._rows())
            await pilot.pause()

            assert panel.guard_count == 2
            items = list(app.query(GuardItem))
            assert len(items) == 2
            # Active rows sort before dormant rows
            assert items[0].row.rule_id == "global:no_rm_rf"
            assert items[1].row.rule_id == "proj:no_push"
            # Markers: active [x], dormant [.]
            assert "[x]" in items[0].render().plain
            assert "[.]" in items[1].render().plain

    async def test_click_posts_toggled_message(self):
        from textual.app import App, ComposeResult

        from claudechic.widgets import GuardItem, GuardsPanel

        toggled: list = []

        class TestApp(App):
            def compose(self) -> ComposeResult:
                yield GuardsPanel(id="guards-panel")

            def on_guard_item_toggled(self, event: GuardItem.Toggled) -> None:
                toggled.append(event.row)

        app = TestApp()
        async with app.run_test() as pilot:
            panel = app.query_one(GuardsPanel)
            panel.update_guards(self._rows())
            await pilot.pause()

            items = list(app.query(GuardItem))
            await pilot.click(items[0])
            await pilot.pause()

            assert len(toggled) == 1
            assert toggled[0].rule_id == "global:no_rm_rf"

    async def test_set_visible_requires_rows(self):
        from textual.app import App, ComposeResult

        from claudechic.widgets import GuardsPanel

        class TestApp(App):
            def compose(self) -> ComposeResult:
                yield GuardsPanel(id="guards-panel", classes="hidden")

        app = TestApp()
        async with app.run_test() as pilot:
            panel = app.query_one(GuardsPanel)
            panel.set_visible(True)
            assert panel.has_class("hidden"), "No rows -> stays hidden"

            panel.update_guards(self._rows())
            await pilot.pause()
            panel.set_visible(True)
            assert not panel.has_class("hidden")
            panel.set_visible(False)
            assert panel.has_class("hidden")
