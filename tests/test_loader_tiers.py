"""Tests for the 3-tier loader (override resolution + disable filter).

Covers SPEC §12.1 invariants (INV-1..5, INV-8, INV-PO-1..3) and §12.4
(INV-DF-1..7). Each test builds a synthetic ``TierRoots`` in tmp_path
and asserts on the post-resolve ``LoadResult`` shape directly — no UI.

Test shim package root: ``<tmp>/package`` (mirroring the post-restructure
``claudechic/defaults/`` layout convention).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from claudechic.workflows import (
    LoadResult,
    ManifestLoader,
    TierRoots,
    register_default_parsers,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mkdir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


def _write_workflow(
    tier_root: Path,
    workflow_id: str,
    main_role: str = "coordinator",
    extra_files: dict[str, str] | None = None,
) -> Path:
    """Lay out a minimal workflow dir under ``<tier>/workflows/<id>/``."""
    wf_dir = _mkdir(tier_root / "workflows" / workflow_id)
    manifest = {
        "workflow_id": workflow_id,
        "main_role": main_role,
        "phases": [{"id": "setup"}, {"id": "build"}],
    }
    (wf_dir / f"{workflow_id}.yaml").write_text(
        yaml.safe_dump(manifest), encoding="utf-8"
    )
    role_dir = _mkdir(wf_dir / main_role)
    (role_dir / "identity.md").write_text(
        f"# {workflow_id} / {main_role}\n", encoding="utf-8"
    )
    (role_dir / "setup.md").write_text("setup\n", encoding="utf-8")
    (role_dir / "build.md").write_text("build\n", encoding="utf-8")
    if extra_files:
        for relpath, content in extra_files.items():
            target = wf_dir / relpath
            _mkdir(target.parent)
            target.write_text(content, encoding="utf-8")
    return wf_dir


def _write_global_rules(tier_root: Path, rules: list[dict[str, object]]) -> Path:
    global_dir = _mkdir(tier_root / "global")
    p = global_dir / "rules.yaml"
    p.write_text(yaml.safe_dump({"rules": rules}), encoding="utf-8")
    return p


def _write_global_hints(tier_root: Path, hints: list[dict[str, object]]) -> Path:
    global_dir = _mkdir(tier_root / "global")
    p = global_dir / "hints.yaml"
    p.write_text(yaml.safe_dump({"hints": hints}), encoding="utf-8")
    return p


def _build_loader(
    package: Path,
    user: Path | None = None,
    project: Path | None = None,
) -> ManifestLoader:
    roots = TierRoots(package=package, user=user, project=project)
    loader = ManifestLoader(tier_roots=roots)
    register_default_parsers(loader)
    return loader


def _load(
    package: Path,
    user: Path | None = None,
    project: Path | None = None,
    *,
    disabled_workflows_by_tier: dict | None = None,
    disabled_ids_by_tier: dict | None = None,
) -> LoadResult:
    loader = _build_loader(package, user, project)
    return loader.load(
        disabled_workflows_by_tier=disabled_workflows_by_tier,
        disabled_ids_by_tier=disabled_ids_by_tier,
    )


# ---------------------------------------------------------------------------
# §12.1 — Override-resolution invariants
# ---------------------------------------------------------------------------


def test_inv_1_user_overrides_package(tmp_path: Path) -> None:
    """INV-1: user-tier workflow `foo` overrides package-tier `foo`."""
    pkg = _mkdir(tmp_path / "package")
    user = _mkdir(tmp_path / "user")
    _write_workflow(pkg, "foo")
    _write_workflow(user, "foo")

    result = _load(pkg, user=user)

    wf = result.workflows["foo"]
    assert wf.tier == "user"
    assert wf.path == user / "workflows" / "foo"
    assert "user" in wf.defined_at
    assert "package" in wf.defined_at


def test_inv_2_project_overrides_user_and_package(tmp_path: Path) -> None:
    """INV-2: project-tier `foo` overrides user-tier and package-tier `foo`."""
    pkg = _mkdir(tmp_path / "package")
    user = _mkdir(tmp_path / "user")
    project = _mkdir(tmp_path / "project")
    _write_workflow(pkg, "foo")
    _write_workflow(user, "foo")
    _write_workflow(project, "foo")

    result = _load(pkg, user=user, project=project)

    wf = result.workflows["foo"]
    assert wf.tier == "project"
    assert wf.path == project / "workflows" / "foo"
    assert wf.defined_at == frozenset({"package", "user", "project"})


def test_inv_3_package_only(tmp_path: Path) -> None:
    """INV-3: ``TierRoots(package=p, user=None, project=None)`` loads
    package-only content with no errors."""
    pkg = _mkdir(tmp_path / "package")
    _write_workflow(pkg, "foo")
    _write_global_rules(
        pkg,
        [
            {
                "id": "no_rm_rf",
                "trigger": "PreToolUse/Bash",
                "enforcement": "deny",
                "detect": {"pattern": r"rm\s+-rf"},
            },
        ],
    )

    result = _load(pkg)

    assert result.errors == []
    assert "foo" in result.workflows
    assert result.workflows["foo"].tier == "package"
    rule_ids = [r.id for r in result.rules]
    assert "global:no_rm_rf" in rule_ids


def test_inv_4_rule_id_collision_project_wins(tmp_path: Path) -> None:
    """INV-4: same rule id at user and project — exactly one ``Rule`` survives,
    ``tier == "project"``."""
    pkg = _mkdir(tmp_path / "package")
    user = _mkdir(tmp_path / "user")
    project = _mkdir(tmp_path / "project")
    rule_user = {
        "id": "shared",
        "trigger": "PreToolUse/Bash",
        "enforcement": "warn",
        "message": "user-tier",
    }
    rule_project = {
        "id": "shared",
        "trigger": "PreToolUse/Bash",
        "enforcement": "deny",
        "message": "project-tier",
    }
    _write_global_rules(pkg, [])
    _write_global_rules(user, [rule_user])
    _write_global_rules(project, [rule_project])

    result = _load(pkg, user=user, project=project)

    matching = [r for r in result.rules if r.id == "global:shared"]
    assert len(matching) == 1
    assert matching[0].tier == "project"
    assert matching[0].message == "project-tier"
    assert "global:shared" in result.item_provenance
    assert "user" in result.item_provenance["global:shared"]
    assert "project" in result.item_provenance["global:shared"]


def test_inv_5_within_tier_duplicate_id(tmp_path: Path) -> None:
    """INV-5: two rules with the same id in one tier's ``rules.yaml`` — one
    survives + one ``LoadError(source="validation")`` fires."""
    pkg = _mkdir(tmp_path / "package")
    rule = {
        "id": "dupe",
        "trigger": "PreToolUse/Bash",
        "enforcement": "warn",
    }
    _write_global_rules(pkg, [rule, dict(rule)])

    result = _load(pkg)

    matching = [r for r in result.rules if r.id == "global:dupe"]
    assert len(matching) == 1
    dup_errs = [
        e
        for e in result.errors
        if e.source == "validation"
        and e.section == "rules"
        and e.item_id == "global:dupe"
    ]
    assert len(dup_errs) == 1


def test_inv_8_hint_at_multiple_tiers(tmp_path: Path) -> None:
    """INV-8: hint id at multiple tiers produces one ``HintDecl``; the
    qualified id (lifecycle key) is identical across tiers."""
    pkg = _mkdir(tmp_path / "package")
    user = _mkdir(tmp_path / "user")
    hint = {
        "id": "welcome",
        "message": "hello",
        "lifecycle": "show-once",
    }
    _write_global_hints(pkg, [dict(hint, message="package version")])
    _write_global_hints(user, [dict(hint, message="user version")])

    result = _load(pkg, user=user)

    matching = [h for h in result.hints if h.id == "global:welcome"]
    assert len(matching) == 1
    assert matching[0].tier == "user"
    # qualified id is the lifecycle key
    assert matching[0].id == "global:welcome"


# ---------------------------------------------------------------------------
# §12.1 — Partial-override invariants (INV-PO-1..3)
# ---------------------------------------------------------------------------


def test_inv_po_1_partial_falls_through(tmp_path: Path) -> None:
    """INV-PO-1: higher tier missing a file the lower tier has — partial
    override; effective workflow falls through to lower tier; LoadError
    surfaces."""
    pkg = _mkdir(tmp_path / "package")
    user = _mkdir(tmp_path / "user")
    _write_workflow(pkg, "foo")
    # User tier has the manifest + identity but is missing build.md.
    user_wf = _mkdir(user / "workflows" / "foo")
    (user_wf / "foo.yaml").write_text(
        yaml.safe_dump({"workflow_id": "foo"}), encoding="utf-8"
    )
    _mkdir(user_wf / "coordinator")
    (user_wf / "coordinator" / "identity.md").write_text("ok", encoding="utf-8")
    (user_wf / "coordinator" / "setup.md").write_text("ok", encoding="utf-8")
    # NOTE: missing build.md vs package.

    result = _load(pkg, user=user)

    # Workflow falls through to package.
    wf = result.workflows["foo"]
    assert wf.tier == "package"
    # Partial-override LoadError surfaces.
    po_errs = [
        e for e in result.errors if e.section == "workflow" and e.item_id == "foo"
    ]
    assert len(po_errs) == 1
    assert "Partial workflow override" in po_errs[0].message
    assert "build.md" in po_errs[0].message


def test_inv_po_2_user_partial_project_full(tmp_path: Path) -> None:
    """INV-PO-2: user has partial; project has full — project wins; partial
    override LoadError still surfaces; project workflow unaffected."""
    pkg = _mkdir(tmp_path / "package")
    user = _mkdir(tmp_path / "user")
    project = _mkdir(tmp_path / "project")
    _write_workflow(pkg, "foo")
    # user tier: incomplete (missing build.md)
    user_wf = _mkdir(user / "workflows" / "foo")
    (user_wf / "foo.yaml").write_text(
        yaml.safe_dump({"workflow_id": "foo"}), encoding="utf-8"
    )
    _mkdir(user_wf / "coordinator")
    (user_wf / "coordinator" / "identity.md").write_text("ok", encoding="utf-8")
    (user_wf / "coordinator" / "setup.md").write_text("ok", encoding="utf-8")
    # project tier: complete
    _write_workflow(project, "foo")

    result = _load(pkg, user=user, project=project)

    wf = result.workflows["foo"]
    assert wf.tier == "project"
    # Partial-override error still fires for the user vs package comparison.
    po_errs = [
        e for e in result.errors if e.section == "workflow" and e.item_id == "foo"
    ]
    assert len(po_errs) >= 1


def test_inv_po_3_higher_has_extras(tmp_path: Path) -> None:
    """INV-PO-3: higher tier has every lower-tier file plus extras —
    higher wins; no partial-override error."""
    pkg = _mkdir(tmp_path / "package")
    user = _mkdir(tmp_path / "user")
    _write_workflow(pkg, "foo")
    _write_workflow(
        user,
        "foo",
        extra_files={"coordinator/extra.md": "extra content\n"},
    )

    result = _load(pkg, user=user)

    wf = result.workflows["foo"]
    assert wf.tier == "user"
    po_errs = [
        e for e in result.errors if e.section == "workflow" and e.item_id == "foo"
    ]
    assert po_errs == []


# ---------------------------------------------------------------------------
# §12.4 — Disable-filter invariants
# ---------------------------------------------------------------------------


def test_inv_df_4_tier_targeted_filters_named_tier(tmp_path: Path) -> None:
    """INV-DF-4: workflow `foo` defined at package AND user; tier-targeted
    disable ``user:foo`` makes resolution pick the package version."""
    pkg = _mkdir(tmp_path / "package")
    user = _mkdir(tmp_path / "user")
    _write_workflow(pkg, "foo")
    _write_workflow(user, "foo")

    result = _load(
        pkg,
        user=user,
        disabled_workflows_by_tier={"user": frozenset({"foo"})},
    )

    assert result.workflows["foo"].tier == "package"


def test_inv_df_5_tier_targeted_id_falls_through(tmp_path: Path) -> None:
    """INV-DF-5: rule defined at user AND package; ``user:lab/onboarding-rule``
    disabled — the post-resolve rule resolves to the package version."""
    pkg = _mkdir(tmp_path / "package")
    user = _mkdir(tmp_path / "user")
    pkg_rule = {
        "id": "shared",
        "trigger": "PreToolUse/Bash",
        "enforcement": "warn",
        "message": "package",
    }
    user_rule = {
        "id": "shared",
        "trigger": "PreToolUse/Bash",
        "enforcement": "deny",
        "message": "user",
    }
    _write_global_rules(pkg, [pkg_rule])
    _write_global_rules(user, [user_rule])

    result = _load(
        pkg,
        user=user,
        disabled_ids_by_tier={"user": frozenset({"global:shared"})},
    )

    matching = [r for r in result.rules if r.id == "global:shared"]
    assert len(matching) == 1
    assert matching[0].tier == "package"
    assert matching[0].message == "package"


def test_parse_disable_entries_invalid_prefix_workflows(caplog) -> None:
    """INV-DF-6 (workflows): invalid tier prefix warns and skips."""
    from claudechic.workflows import parse_disable_entries

    bare, targeted = parse_disable_entries(["pkg:foo"], config_key="disabled_workflows")

    assert bare == frozenset()
    assert targeted == {}
    assert any("invalid tier prefix 'pkg'" in rec.message for rec in caplog.records)


def test_parse_disable_entries_qualified_id_treated_bare() -> None:
    """For ``disabled_ids``, an entry whose prefix is NOT a tier name
    is treated as a bare qualified id (``namespace:bare_id``)."""
    from claudechic.workflows import parse_disable_entries

    bare, targeted = parse_disable_entries(
        ["global:no_bare_pytest"], config_key="disabled_ids"
    )
    assert "global:no_bare_pytest" in bare
    assert targeted == {}


def test_parse_disable_entries_tier_targeted_id() -> None:
    """``user:global:no_bare_pytest`` is a tier-targeted disable on user."""
    from claudechic.workflows import parse_disable_entries

    bare, targeted = parse_disable_entries(
        ["user:global:no_bare_pytest"], config_key="disabled_ids"
    )
    assert bare == frozenset()
    assert targeted == {"user": frozenset({"global:no_bare_pytest"})}


def test_load_result_provenance_maps(tmp_path: Path) -> None:
    """``workflow_provenance`` and ``item_provenance`` are populated."""
    pkg = _mkdir(tmp_path / "package")
    user = _mkdir(tmp_path / "user")
    _write_workflow(pkg, "foo")
    _write_workflow(user, "foo")
    _write_global_rules(
        pkg,
        [{"id": "x", "trigger": "PreToolUse/Bash", "enforcement": "warn"}],
    )

    result = _load(pkg, user=user)

    assert "foo" in result.workflow_provenance
    assert "package" in result.workflow_provenance["foo"]
    assert "user" in result.workflow_provenance["foo"]
    assert "global:x" in result.item_provenance
    assert "package" in result.item_provenance["global:x"]


def test_phase_pruned_when_workflow_overridden(tmp_path: Path) -> None:
    """Phases follow workflow-tier override: when a higher tier wins, the
    losing tier's phases for the same workflow_id are pruned."""
    pkg = _mkdir(tmp_path / "package")
    user = _mkdir(tmp_path / "user")
    _write_workflow(pkg, "foo")
    _write_workflow(user, "foo")

    result = _load(pkg, user=user)

    # Both tiers declared phases; only the user-tier phases survive.
    foo_phases = [p for p in result.phases if p.namespace == "foo"]
    assert len(foo_phases) > 0
    assert all(p.tier == "user" for p in foo_phases)


def test_global_rules_accumulate_independent_of_workflow_override(
    tmp_path: Path,
) -> None:
    """Top-level rules at ``<tier>/global/rules.yaml`` accumulate by per-id
    resolution INDEPENDENTLY of workflow-tier override — even when a rule's
    namespace matches a workflow id whose winning tier is elsewhere."""
    pkg = _mkdir(tmp_path / "package")
    user = _mkdir(tmp_path / "user")
    project = _mkdir(tmp_path / "project")
    # Workflow `audit` at package + project (project wins).
    _write_workflow(pkg, "audit")
    _write_workflow(project, "audit")
    # Package rule with namespace=audit (via workflow manifest) is one
    # category; here we exercise top-level global rules.
    _write_global_rules(
        pkg,
        [
            {
                "id": "no_secret_keys",
                "trigger": "PreToolUse/Bash",
                "enforcement": "deny",
            }
        ],
    )
    _write_global_rules(
        user,
        [
            {
                "id": "no_todo_comments",
                "trigger": "PreToolUse/Bash",
                "enforcement": "warn",
            }
        ],
    )

    result = _load(pkg, user=user, project=project)

    rule_ids = {r.id for r in result.rules}
    # Both top-level rules survive even though `audit` is overridden at
    # project tier (workflow override does not prune top-level globals).
    assert "global:no_secret_keys" in rule_ids
    assert "global:no_todo_comments" in rule_ids


@pytest.mark.parametrize("path_kwarg", ["disabled_workflows_by_tier"])
def test_unknown_workflow_id_in_filter_is_silent_at_loader(
    tmp_path: Path, path_kwarg: str
) -> None:
    """The loader does NOT itself validate disable lists; unknown-id warns
    happen in ``_filter_load_result`` (covered by app-level tests). Here
    we verify a tier-targeted disable on an unknown id is a no-op."""
    pkg = _mkdir(tmp_path / "package")
    _write_workflow(pkg, "foo")

    result = _load(pkg, **{path_kwarg: {"package": frozenset({"nonexistent"})}})

    # `foo` survives; no error about `nonexistent`.
    assert "foo" in result.workflows
    assert all(
        e.section != "workflow" or e.item_id != "nonexistent" for e in result.errors
    )


def test_tier_provenance_maps_use_frozenset(tmp_path: Path) -> None:
    """Provenance maps contain frozensets for hashable use in UI."""
    pkg = _mkdir(tmp_path / "package")
    user = _mkdir(tmp_path / "user")
    _write_workflow(pkg, "foo")
    _write_workflow(user, "foo")

    result = _load(pkg, user=user)

    assert isinstance(result.workflow_provenance["foo"], frozenset)


# ---------------------------------------------------------------------------
# §12.4 — INV-DF-1/2/3/7 (bare-ID disable behaviors via _filter_load_result)
# ---------------------------------------------------------------------------
#
# The tier-targeted disable invariants (INV-DF-4/5/6) live in the loader
# itself and are covered above. The bare-ID invariants exercise
# ``app._filter_load_result``, which post-processes ``LoadResult`` with the
# union of user-config and project-config bare-ID disable lists per §3.6.


def _make_project_config(
    *,
    disabled_workflows: list[str] | None = None,
    disabled_ids: list[str] | None = None,
    guardrails: bool = True,
    hints: bool = True,
):
    """Build a ProjectConfig with the requested disable lists.

    Local helper to keep INV-DF tests self-contained — avoids reaching
    into the full ``claudechic.config.ProjectConfig.load()`` path which
    requires an on-disk YAML file.
    """
    from claudechic.config import ProjectConfig

    return ProjectConfig(
        guardrails=guardrails,
        hints=hints,
        disabled_workflows=disabled_workflows or [],
        disabled_ids=disabled_ids or [],
    )


def test_inv_df_1_bare_id_disable_removes_workflow_and_namespaced_records(
    tmp_path: Path,
) -> None:
    """INV-DF-1: bare-ID disable applies across ALL tiers, including any
    rules/hints/checks whose namespace matches the disabled workflow_id.
    """
    from claudechic.app import _filter_load_result

    pkg = _mkdir(tmp_path / "package")
    # Workflow `foo` plus an in-workflow rule whose namespace == workflow_id.
    _write_workflow(pkg, "foo")
    foo_yaml = pkg / "workflows" / "foo" / "foo.yaml"
    foo_yaml.write_text(
        yaml.safe_dump(
            {
                "workflow_id": "foo",
                "main_role": "coordinator",
                "phases": [{"id": "setup"}, {"id": "build"}],
                "rules": [
                    {
                        "id": "foo_rule",
                        "trigger": "PreToolUse/Bash",
                        "enforcement": "warn",
                        "message": "namespace=foo",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    # An unrelated workflow `bar` so we can confirm it survives.
    _write_workflow(pkg, "bar")

    result = _load(pkg)
    assert "foo" in result.workflows
    assert "bar" in result.workflows
    foo_rules_pre = [r for r in result.rules if r.namespace == "foo"]
    assert foo_rules_pre, (
        "Pre-filter sanity: namespace=foo rule must be present before disable"
    )

    config = _make_project_config(disabled_workflows=["foo"])
    filtered = _filter_load_result(result, config)

    # Workflow removed
    assert "foo" not in filtered.workflows
    # Sibling workflow untouched
    assert "bar" in filtered.workflows
    # Rules whose namespace matches the disabled workflow are also pruned
    assert not [r for r in filtered.rules if r.namespace == "foo"]
    # Phases keyed under that namespace are pruned (mirrors workflow scope)
    assert not [p for p in filtered.phases if p.namespace == "foo"]


def test_inv_df_2_unknown_bare_workflow_id_warns_no_error(
    tmp_path: Path, caplog
) -> None:
    """INV-DF-2: unknown bare workflow_id in ``disabled_workflows`` → WARN
    log, no error/exception, LoadResult.errors unchanged."""
    import logging

    from claudechic.app import _filter_load_result

    pkg = _mkdir(tmp_path / "package")
    _write_workflow(pkg, "foo")

    result = _load(pkg)
    config = _make_project_config(disabled_workflows=["nonexistent_workflow"])

    with caplog.at_level(logging.WARNING, logger="claudechic.app"):
        filtered = _filter_load_result(result, config)

    # No exception; foo still present (filter ran cleanly).
    assert "foo" in filtered.workflows
    # WARN was emitted referencing the unknown id.
    assert any(
        "nonexistent_workflow" in rec.message and rec.levelname == "WARNING"
        for rec in caplog.records
    ), f"No WARN for unknown workflow_id: {[r.message for r in caplog.records]}"
    # LoadResult.errors does NOT contain a related entry (per §3.6 +
    # spec wording: "LoadResult.errors does NOT contain a related entry").
    assert all("nonexistent_workflow" not in (e.item_id or "") for e in filtered.errors)


def test_inv_df_3_unknown_bare_id_in_disabled_ids_warns_no_error(
    tmp_path: Path, caplog
) -> None:
    """INV-DF-3: unknown bare id in ``disabled_ids`` → WARN log, no error.

    Symmetric to INV-DF-2 but for individual rule/hint/check IDs rather
    than workflow_ids.
    """
    import logging

    from claudechic.app import _filter_load_result

    pkg = _mkdir(tmp_path / "package")
    _write_workflow(pkg, "foo")
    _write_global_rules(
        pkg,
        [{"id": "real_rule", "trigger": "PreToolUse/Bash", "enforcement": "warn"}],
    )

    result = _load(pkg)
    config = _make_project_config(disabled_ids=["global:does_not_exist"])

    with caplog.at_level(logging.WARNING, logger="claudechic.app"):
        filtered = _filter_load_result(result, config)

    # The real rule is still present.
    assert any(r.id == "global:real_rule" for r in filtered.rules)
    # WARN was emitted referencing the unknown id.
    assert any(
        "global:does_not_exist" in rec.message and rec.levelname == "WARNING"
        for rec in caplog.records
    ), f"No WARN for unknown disabled_id: {[r.message for r in caplog.records]}"
    # LoadResult.errors does NOT contain a related entry.
    assert all("does_not_exist" not in (e.item_id or "") for e in filtered.errors)


def test_inv_df_7_union_user_and_project_disable_lists(tmp_path: Path) -> None:
    """INV-DF-7: union of user-config and project-config disable lists.

    User-config ``disabled_workflows = ["foo"]`` AND project-config
    ``disabled_workflows = ["bar"]`` — both honored additively. Symmetric
    for ``disabled_ids``.
    """
    from claudechic.app import _filter_load_result

    pkg = _mkdir(tmp_path / "package")
    _write_workflow(pkg, "foo")
    _write_workflow(pkg, "bar")
    _write_workflow(pkg, "baz")  # control: should survive
    _write_global_rules(
        pkg,
        [
            {"id": "rule_a", "trigger": "PreToolUse/Bash", "enforcement": "warn"},
            {"id": "rule_b", "trigger": "PreToolUse/Bash", "enforcement": "warn"},
            {"id": "rule_c", "trigger": "PreToolUse/Bash", "enforcement": "warn"},
        ],
    )

    result = _load(pkg)
    assert {"foo", "bar", "baz"}.issubset(result.workflows.keys())

    # Project config disables "foo"; user config disables "bar". Both
    # honored additively; baz survives.
    config = _make_project_config(
        disabled_workflows=["foo"], disabled_ids=["global:rule_a"]
    )
    filtered = _filter_load_result(
        result,
        config,
        user_disabled_workflows=frozenset({"bar"}),
        user_disabled_ids=frozenset({"global:rule_b"}),
    )

    # Workflows: foo + bar gone; baz remains.
    assert "foo" not in filtered.workflows
    assert "bar" not in filtered.workflows
    assert "baz" in filtered.workflows
    # Rules: rule_a + rule_b gone; rule_c remains.
    rule_ids_after = {r.id for r in filtered.rules}
    assert "global:rule_a" not in rule_ids_after
    assert "global:rule_b" not in rule_ids_after
    assert "global:rule_c" in rule_ids_after
