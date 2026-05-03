# Axis Spec — Loader Rewrite + Per-Category Override Resolution

> **REFERENCE ARCHIVE — operational content has been merged into `SPEC.md` §3. This file is preserved for trace; not for implementation reading.**

**Audience:** Implementer, Tester.
**Status:** Operational — this document is standalone executable.
**Lens:** Composability (axis spec for the 3-tier loader + override-resolution mechanics), with cross-lens UX requirements from UserAlignment integrated.
**Scope:** R1, R2, R3 of `specification/composability.md`; Seam-A, Seam-B, Seam-D; INV-1, INV-2, INV-4, INV-5, INV-8; composability lens-input §8.2; UserAlignment cross-lens MUSTs R3-UX.1–R3-UX.11 (partial-override loader enforcement; tier-agnostic disable; per-id tier provenance for discovery; unknown-id warn-not-error).
**Out of scope:** R5 boundary (different axis spec); R6 agent awareness (different axis spec); R7 artifact dirs (different axis spec); UI surfaces (consume the data this spec produces); cross-fork cherry-picks (Group F).

**User-facing terminology constraint (per R3-UX wording + L4):** code/spec uses **"tier"**; user-facing UI labels and helper text use **"level"**. Implementations of UI surfaces consuming this spec's outputs MUST follow that distinction. The loader and `LoadResult` API names use "tier".

---

## 1. Module layout

After Group A (file moves, per `vision.md` File-move inventory) is complete:

| Module | Purpose |
|---|---|
| `claudechic/workflows/loader.py` | `ManifestLoader`, tier walker, `LoadResult`, `LoadError`, tier-tagged `WorkflowData`. |
| `claudechic/workflows/parsers.py` | `PhasesParser` (gains `resolve()`). |
| `claudechic/workflows/agent_folders.py` | `assemble_phase_prompt`, `create_post_compact_hook` (tier-aware). |
| `claudechic/workflows/__init__.py` | Public API re-export and `register_default_parsers`. |
| `claudechic/guardrails/rules.py` | `Rule`, `Injection` dataclasses (gain `tier` field). |
| `claudechic/guardrails/parsers.py` | `RulesParser`, `InjectionsParser` (gain `resolve()`). |
| `claudechic/hints/types.py` | `HintDecl` (gains `tier` field). |
| `claudechic/hints/parsers.py` | `HintsParser` (gains `resolve()`). |
| `claudechic/checks/protocol.py` | `CheckDecl` (gains `tier` field). |
| `claudechic/checks/parsers.py` | `ChecksParser` (gains `resolve()`). |
| `claudechic/mcp.py` | `discover_mcp_tools` rewritten as 3-tier. |

No new files are created beyond what already exists post-restructure. All edits are in-place.

---

## 2. Types

### 2.1 `Tier`

`claudechic/workflows/loader.py` MUST declare:

```python
Tier = Literal["package", "user", "project"]

# Ascending-priority order. project beats user beats package.
TIER_PRIORITY: tuple[Tier, ...] = ("package", "user", "project")
```

`TIER_PRIORITY` is canonical; resolution code MUST iterate it (do not hard-code tier names elsewhere).

### 2.2 `TierRoots`

`claudechic/workflows/loader.py` MUST declare:

```python
@dataclass(frozen=True)
class TierRoots:
    """Filesystem roots for the three tiers.

    A tier MAY be None (absent). Only `package` is required to be a real path
    (the package always ships with defaults).

    Each root, when not None, MUST point at a directory whose layout is:
        <root>/global/rules.yaml
        <root>/global/hints.yaml
        <root>/workflows/<workflow_id>/<workflow_id>.yaml
        <root>/workflows/<workflow_id>/<role>/{identity,phase}.md
        <root>/mcp_tools/*.py
    (Subtrees MAY be missing; missing subtrees yield zero records for that
    category in that tier.)
    """
    package: Path
    user: Path | None
    project: Path | None

    def items(self) -> list[tuple[Tier, Path]]:
        """Return non-None tier roots in ascending priority order."""
        out: list[tuple[Tier, Path]] = [("package", self.package)]
        if self.user is not None:
            out.append(("user", self.user))
        if self.project is not None:
            out.append(("project", self.project))
        return out
```

The `items()` order MUST match `TIER_PRIORITY` (ascending; package first, project last).

### 2.3 Tier-tagged record dataclasses

Every typed record produced by the loader MUST carry a `tier: Tier` field (winning tier — the tier whose value survived override resolution). The mapping is:

| Dataclass | File | New field |
|---|---|---|
| `Rule` | `claudechic/guardrails/rules.py` | `tier: Tier = "package"` (default acceptable; parser sets explicitly) |
| `Injection` | `claudechic/guardrails/rules.py` | `tier: Tier = "package"` |
| `HintDecl` | `claudechic/hints/types.py` | `tier: Tier = "package"` |
| `Phase` | `claudechic/workflows/phases.py` | `tier: Tier = "package"` |
| `CheckDecl` | `claudechic/checks/protocol.py` | `tier: Tier = "package"` |
| `WorkflowData` | `claudechic/workflows/loader.py` | `tier: Tier` (no default — always set explicitly) AND `defined_at: frozenset[Tier]` (per R3-UX.3 — every tier where the workflow_id is defined, including non-winning tiers; winning tier is always a member) |

Implementation MUST:
- Add the field as the last field on each frozen dataclass.
- Update every constructor call site to pass `tier=` explicitly. Parser code (§3) is the only place that sets it.
- Update any tests that construct these dataclasses with positional args (they SHOULD be keyword args; if any are positional, the addition of `tier` may break them — fix by making them keyword args).

`HintRecord` (presentation type at `claudechic/hints/types.py:223`) does NOT gain a `tier` field — tier is a loader-time concern; the runtime hint pipeline operates on resolved records.

### 2.4 Tier-tagged MCP tool wrapper

MCP tools are SDK objects (not claudechic dataclasses), so tier provenance is carried via a wrapper:

```python
# claudechic/mcp.py
@dataclass(frozen=True)
class TieredMCPTool:
    """Wraps an SDK tool with its tier provenance.

    `name` mirrors the SDK tool's name attribute and is the resolution identity
    (R3.1). `tool` is the underlying SDK tool object passed to the MCP server.

    `tier` is the winning tier (post-resolution).
    `defined_at` is every tier where this tool name appears (per R3-UX.3 / R3-UX.5
    — discovery surface enumeration). The winning tier is always a member.
    """
    name: str
    tier: Tier
    defined_at: frozenset[Tier]
    tool: Any   # SDK tool object; treated as opaque
```

`discover_mcp_tools` (§7) returns `list[TieredMCPTool]`; consumers that previously expected raw SDK tools MUST be updated to use `.tool` to extract the SDK object after resolution.

---

## 3. ManifestSection protocol — revised

`claudechic/workflows/loader.py` MUST replace the existing `ManifestSection[T_co]` protocol with:

```python
class ManifestSection(Protocol[T_co]):
    """Protocol for typed manifest section parsers (parse + resolve)."""

    @property
    def section_key(self) -> str:
        """YAML key this parser handles (e.g. 'rules', 'checks', 'hints',
        'injections', 'phases')."""
        ...

    def parse(
        self,
        raw: list[dict[str, Any]],
        *,
        namespace: str,
        source_path: str,
        tier: Tier,
    ) -> list[T_co]:
        """Parse raw YAML section into typed records.

        Each returned record MUST have `tier` set to the `tier` argument.
        Items that fail validation are skipped (logged, not raised).
        """
        ...

    def resolve(
        self,
        items_by_tier: dict[Tier, list[T_co]],
    ) -> tuple[list[T_co], list[LoadError]]:
        """Apply override resolution across tiers.

        Input dict keys are exactly the tiers present in TierRoots.items().
        Output: (resolved_items, errors). Errors are non-fatal; they describe
        within-tier collisions (R3.5) discovered during resolve.

        For each category, the implementation MUST follow R3.1–R3.5
        (see §4 of this spec).
        """
        ...
```

Notes:
- The `parse` signature MUST gain a `tier: Tier` keyword arg. All registered parsers update accordingly.
- The `resolve` method is new. All registered parsers gain it.
- The protocol is loaded by the existing `register()` mechanism — no changes required to `register()` itself.

---

## 4. Per-category resolution (R3.1–R3.5)

Each parser's `resolve()` MUST implement the policy below. All implementations MUST:

1. Iterate `items_by_tier` keys in **ascending** `TIER_PRIORITY` order.
2. Within a single tier's list, detect duplicate identities and emit `LoadError(source="validation", section=<key>, item_id=<dup_id>, message="duplicate id within tier <tier>; lower-occurrence dropped")`. Keep the first occurrence; drop subsequent occurrences. (R3.5)
3. Then merge tiers: for each identity, keep the record from the highest tier that has it. Lower-tier records of the same identity are silently replaced (no error — cross-tier overrides are expected; R3.4).
4. Return `(merged_items, errors)`.

There MUST be a private helper available to all parsers (recommended location: `claudechic/workflows/loader.py`):

```python
def _resolve_by_id(
    items_by_tier: dict[Tier, list[T]],
    *,
    section_key: str,
    id_of: Callable[[T], str | None],
) -> tuple[list[T], list[LoadError]]:
    """Generic override-by-id resolver.

    - Within-tier duplicates -> LoadError, drop later occurrence.
    - Cross-tier duplicates  -> override (no error), winner = highest tier.
    - Items where id_of(item) is None are passed through unchanged
      (no resolution applied; included from every tier).

    Iteration order: TIER_PRIORITY ascending, so higher-tier writes win.
    """
```

All four content categories use `_resolve_by_id` with category-specific `id_of` callbacks below.

A second helper builds the per-id tier-presence map used by `LoadResult.item_provenance` (R3-UX.3, R3-UX.5):

```python
def _build_item_provenance(
    collected_by_tier: dict[Tier, dict[str, list[Any]]],
) -> dict[str, frozenset[Tier]]:
    """For every parsed record across all tiers and all sections, record which
    tiers defined an item with that id. Used by the disable filter (R3-UX.4)
    and the discovery UI (R3-UX.3, R3-UX.5).

    Iteration order is irrelevant; the result is a frozenset per id.
    Records without an `id` attribute (rare; some Phase fields lack ids)
    are skipped.
    """
    provenance: dict[str, set[Tier]] = {}
    for tier, by_section in collected_by_tier.items():
        for items in by_section.values():
            for item in items:
                iid = getattr(item, "id", None)
                if isinstance(iid, str) and iid:
                    provenance.setdefault(iid, set()).add(tier)
    return {iid: frozenset(tiers) for iid, tiers in provenance.items()}
```

This function MUST be called AFTER per-tier parse (Step 2) and BEFORE the per-category resolve (Step 6) — placement is in Step 3.5 of the load() pipeline (§5.4).

### 4.1 Workflows — `WorkflowData`

Workflows are NOT loaded by a `ManifestSection` parser; they are tracked separately on `LoadResult.workflows`. Workflow resolution is a dedicated step inside `ManifestLoader.load()` (§5), executed BEFORE the parsers' `resolve()`.

> **Partial-override pre-step (R3-UX.7).** Before the resolution described in this section runs, the loader executes `_reject_partial_overrides` (§6.5) at pipeline Step 3.5. That step removes any tier's contribution to a workflow_id where the higher tier is missing files present in the next-lower tier — those entries do not reach the resolution step below. As a result, this section's "highest-tier wins" rule operates only on tiers whose file set is structurally complete relative to lower tiers. **Implementer reading §4.1 in isolation: see §6.5 for the partial-override enforcement that runs first.**

Identity unit (R3.1): `workflow_id` (the YAML field; falls back to directory name as in current loader.py:222).

Resolution (R3.2, R3.3):

```python
def _resolve_workflows(
    workflows_by_tier: dict[Tier, dict[str, WorkflowData]],
    workflow_provenance: dict[str, frozenset[Tier]],
) -> tuple[dict[str, WorkflowData], list[LoadError]]:
    """Override workflow definitions by workflow_id; full-record replacement.

    For each workflow_id, the highest-tier WorkflowData wins. The winning
    WorkflowData's `path` field is the path to the winning tier's workflow
    directory; the engine reads role/phase markdown from there (R3.3).

    Each returned WorkflowData has:
      - `tier` = winning tier
      - `defined_at` = workflow_provenance[workflow_id]

    Lower-tier records of the same workflow_id are discarded entirely
    (no field-level merging, no role-file mixing).

    Within-tier duplicates: not possible for workflow_id (one directory =
    one manifest = one workflow_id); if discovered (e.g., two manifests
    declare the same workflow_id via the YAML `workflow_id:` key), emit a
    LoadError and keep first-discovered.
    """
```

The returned `dict` is what populates `LoadResult.workflows`. Each `WorkflowData` carries its winning `tier` and the `defined_at` set.

### 4.2 Rules — `RulesParser.resolve`

Identity unit (R3.1): `Rule.id` (already qualified as `<namespace>:<raw_id>`).

`id_of = lambda r: r.id`.

Uses `_resolve_by_id` directly. Non-conflicting ids accumulate (R3.4).

### 4.3 Injections — `InjectionsParser.resolve`

Identity unit (R3.1): `Injection.id`.

`id_of = lambda i: i.id`.

Uses `_resolve_by_id` directly.

### 4.4 Hints — `HintsParser.resolve`

Identity unit (R3.1): `HintDecl.id` (qualified `<namespace>:<raw_id>`).

`id_of = lambda h: h.id`.

Uses `_resolve_by_id` directly.

Note (Seam-D, INV-8): `HintDecl.id` is the lifecycle key that `HintStateStore` uses (`state.py:131`). Override by id MUST preserve the same id, so lifecycle records survive override. Implementation MUST NOT alter the qualified-id format.

### 4.5 Checks — `ChecksParser.resolve`

Identity unit (R3.1): `CheckDecl.id` (auto-generated `<namespace>:<phase_id>:advance:<index>` per `parsers.py:172`, or top-level `<namespace>:<raw_id>` if a top-level checks section exists).

`id_of = lambda c: c.id`.

Uses `_resolve_by_id` directly.

Note: top-level `checks:` sections are uncommon (most checks are phase-nested via `PhasesParser._parse_advance_checks`). Phase-nested checks ride along with their phase (see §4.6); they appear in `items_by_tier` only if the workflow that owns them survives workflow resolution.

### 4.6 Phases — `PhasesParser.resolve`

Identity unit (R3.1): `Phase.id` (qualified `<workflow_id>:<phase_id>`).

`id_of = lambda p: p.id`.

Uses `_resolve_by_id` directly.

**Workflow-scoped pruning:** before calling `_resolve_by_id`, the loader MUST drop any `Phase` whose `namespace` matches a workflow_id whose winning tier is NOT this phase's tier. (Workflows are resolved first; lower-tier phases of overridden workflows are stale.) This pruning is performed in `ManifestLoader.load()` (§5), not inside the parser, so the parser's `resolve()` only sees per-tier lists already filtered to surviving workflow content.

### 4.7 MCP tools

Resolution lives in `discover_mcp_tools` (§7), not in a `ManifestSection` parser. Identity unit (R3.1): `tool.name`. Same `_resolve_by_id` logic applied with `id_of = lambda t: t.name`.

---

## 5. `ManifestLoader` — post-rewrite shape

`claudechic/workflows/loader.py` MUST define:

### 5.1 Constructor

```python
class ManifestLoader:
    def __init__(self, tier_roots: TierRoots) -> None:
        self._tier_roots = tier_roots
        self._parsers: dict[str, ManifestSection[Any]] = {}

    def register(self, parser: ManifestSection[Any]) -> None:
        self._parsers[parser.section_key] = parser
```

The old `__init__(global_dir, workflows_dir)` signature is removed.

### 5.2 Tier walker

```python
def walk_tiers(
    tier_roots: TierRoots,
) -> Iterable[tuple[Tier, Path]]:
    """Yield (tier, manifest_path) pairs for every YAML manifest in every tier.

    For each (tier, root) in tier_roots.items() (ascending priority):
        For each manifest in discover_manifests_single_tier(root):
            yield (tier, manifest)

    Order within a tier matches discover_manifests_single_tier. Order across
    tiers is package -> user -> project (ascending TIER_PRIORITY).
    """
```

```python
def discover_manifests_single_tier(root: Path) -> list[Path]:
    """Discover manifests under a single tier root.

    Replaces the body of the old `discover_manifests(global_dir, workflows_dir)`
    by treating root as the tier root. Returns paths in load order:
      1. <root>/global/*.yaml (sorted, hidden files skipped)
      2. <root>/workflows/*/<dir_name>.yaml (sorted, hidden dirs skipped)
    Missing <root>/global/ or <root>/workflows/ -> that subtree contributes zero
    paths (no error). Unreadable directories raise OSError up to the caller.
    """
```

The free function `discover_manifests` (current loader.py:117) is REMOVED. Public API consumers MUST migrate to `walk_tiers` or `discover_manifests_single_tier`. Documentation files referencing `discover_manifests` (the three tutorial markdown files at `claudechic/defaults/workflows/tutorial_extending/learner/*.md`) MUST be rewritten to call `walk_tiers` against a `TierRoots`.

### 5.3 `LoadResult`

```python
@dataclass(frozen=True)
class WorkflowData:
    workflow_id: str
    path: Path                         # path to the winning tier's workflow directory
    tier: Tier                         # winning tier
    defined_at: frozenset[Tier]        # every tier where workflow_id is defined
    main_role: str | None = None
    has_errors: bool = False


@dataclass(frozen=True)
class LoadResult:
    rules: list[Any] = field(default_factory=list)
    injections: list[Any] = field(default_factory=list)
    checks: list[Any] = field(default_factory=list)
    hints: list[Any] = field(default_factory=list)
    phases: list[Phase] = field(default_factory=list)
    errors: list[LoadError] = field(default_factory=list)
    workflows: dict[str, WorkflowData] = field(default_factory=dict)

    # Per-id tier-presence maps (R3-UX.3 / R3-UX.5). Keys are qualified ids
    # (e.g., "global:no_bare_pytest", "project-team:specification") for items
    # and bare workflow_ids for workflows. Values list every tier where the id
    # is defined (regardless of which tier won resolution). Used by:
    #   - settings UI discovery surfaces (per-id "defined at:" labels)
    #   - the disable filter's unknown-id warning (R3-UX.4)
    item_provenance: dict[str, frozenset[Tier]] = field(default_factory=dict)
    workflow_provenance: dict[str, frozenset[Tier]] = field(default_factory=dict)

    def get_workflow(self, wf_id: str) -> WorkflowData | None:
        return self.workflows.get(wf_id)
```

All list/dict members EXCEPT the provenance maps hold post-resolve content (override applied; tier-tagged). The provenance maps reflect raw per-tier presence (pre-resolve), so a UI can render "defined at: package, user, project" even after resolution chose one winner.

Engine consumers MUST treat `tier` and `defined_at` as opaque metadata (Seam-B), used only for diagnostic / UI display. Engine logic (rule evaluation, hint matching, phase advance) MUST NOT branch on tier identity.

### 5.4 `load()` pipeline

`ManifestLoader.load()` MUST execute these steps in order:

```
Step 1. Discover
  paths_by_tier: dict[Tier, list[Path]] = {}
  for tier, root in self._tier_roots.items():
      try:
          paths_by_tier[tier] = discover_manifests_single_tier(root)
      except OSError as e:
          if tier == "package":
              return LoadResult(errors=[LoadError(source="discovery",
                                                  message=f"package tier unreadable: {e}")])
          # user/project unreadable -> log, skip that tier (fail open for non-package tiers)
          errors.append(LoadError(source="discovery",
                                   message=f"{tier} tier unreadable: {e}"))
          paths_by_tier[tier] = []

Step 2. Per-tier parse
  collected_by_tier: dict[Tier, dict[str, list]] = {tier: {k: [] for k in self._parsers}
                                                     for tier in paths_by_tier}
  workflows_by_tier: dict[Tier, dict[str, WorkflowData]] = {tier: {} for tier in paths_by_tier}

  for tier, paths in paths_by_tier.items():
      for path in paths:
          # YAML load (existing error handling preserved):
          #   - file unreadable / yaml.YAMLError -> LoadError, skip path
          #   - non-mapping file (except global bare-list case) -> LoadError, skip
          # Determine namespace ('global' vs workflow_id) — same rules as today.
          # Track WorkflowData if non-global; populate workflows_by_tier[tier][wf_id].
          # Dispatch sections to parsers; parser.parse(..., tier=tier) returns
          #   tier-tagged records; append to collected_by_tier[tier][key].

Step 3. Phase-nested hints expansion (preserve existing logic, loader.py:296-299)
  for tier, by_key in collected_by_tier.items():
      for phase in by_key.get("phases", []):
          if hasattr(phase, "hints") and phase.hints:
              # Phase-nested hints inherit phase's tier
              tier_tagged = [_with_tier(h, tier) for h in phase.hints]
              by_key.setdefault("hints", []).extend(tier_tagged)

Step 3.5. Partial-override detection (R3-UX.7 / R3-UX.9)
  # Reject any tier's contribution to a workflow_id when that tier's directory
  # is missing files present in the next-lower tier's directory for the same
  # workflow_id. See §6.5 for the detection rule.
  workflows_by_tier, partial_errors = _reject_partial_overrides(
      workflows_by_tier, tier_roots
  )
  errors.extend(partial_errors)

  # Build per-id provenance maps (R3-UX.3 / R3-UX.5).
  # NOTE: workflow_provenance reflects only tiers that survive partial-override
  # rejection (a partial-override tier is not "defined at" — it's broken).
  workflow_provenance = {
      wf_id: frozenset(tier for tier, by_id in workflows_by_tier.items() if wf_id in by_id)
      for wf_id in {wid for by_id in workflows_by_tier.values() for wid in by_id}
  }
  item_provenance: dict[str, frozenset[Tier]] = _build_item_provenance(collected_by_tier)

Step 4. Workflow resolution (R3.3)
  resolved_workflows, wf_errors = _resolve_workflows(workflows_by_tier, workflow_provenance)
  errors.extend(wf_errors)

Step 5. Workflow-scoped content pruning (§4.6 + R3.3)
  # For each workflow_id, only the winning tier's namespace-scoped content
  # contributes. Drop records whose namespace == any wf_id but tier != that
  # workflow's winning tier.
  for tier, by_key in collected_by_tier.items():
      for key, items in by_key.items():
          by_key[key] = [
              item for item in items
              if not _is_pruned(item, tier, resolved_workflows)
          ]

  # _is_pruned(item, tier, resolved):
  #   ns = getattr(item, "namespace", None)
  #   if ns is None or ns == "global": return False
  #   wf = resolved.get(ns)
  #   if wf is None: return False  # workflow didn't survive at any tier
  #                                  (wf was filtered or had errors); keep
  #                                  records as today (no change)
  #   return wf.tier != tier        # prune if this item is from a non-winning tier

Step 6. Per-category resolve
  per_section_by_tier = {
      key: {tier: collected_by_tier[tier].get(key, []) for tier in collected_by_tier}
      for key in self._parsers
  }
  resolved: dict[str, list] = {}
  for key, parser in self._parsers.items():
      items, parser_errors = parser.resolve(per_section_by_tier[key])
      resolved[key] = items
      errors.extend(parser_errors)

Step 7. Cross-manifest validation (preserve loader.py:362-385 phase-ref check)
  # Phase-reference validation runs against resolved.phases.
  # Duplicate-id detection is REMOVED from this step (it now lives in
  # parser.resolve, scoped per-tier and per-category).
  errors.extend(self._validate_phase_refs(resolved))

Step 8. Apply has_errors to workflows whose source paths produced errors
  # (preserve loader.py:304-314 logic, but operate on resolved_workflows)

Step 9. Return LoadResult(
      rules=resolved.get("rules", []),
      injections=resolved.get("injections", []),
      checks=resolved.get("checks", []),
      hints=resolved.get("hints", []),
      phases=resolved.get("phases", []),
      errors=errors,
      workflows=resolved_workflows,
      workflow_provenance=workflow_provenance,
      item_provenance=item_provenance,
  )
```

**Determinism:** Steps 1–2 MUST process tiers in ascending `TIER_PRIORITY` order; Step 6's per-category resolve iterates the same order. Repeated invocations against identical filesystem state MUST produce identical `LoadResult`.

---

## 6. Within-tier vs cross-tier duplicates

The current `_validate` (loader.py:338) emits a `LoadError` for ALL duplicate ids across the entire collection. This is REPLACED by:

| Where it lives | Scope | Behavior |
|---|---|---|
| `_resolve_by_id` (helper, §4) | Within one tier's list | LoadError emitted; first occurrence kept; later occurrence dropped. (R3.5) |
| `_resolve_by_id` (helper, §4) | Across tiers | No error. Override applied; higher tier wins. (R3.4 / INV-4) |
| `ManifestLoader._validate_phase_refs` | Across the resolved `phases` list | Phase-reference validation preserved (loader.py:362-385). |

The current `_validate` method MUST be split: phase-ref validation moves to `_validate_phase_refs`; duplicate-id validation moves into `_resolve_by_id` (per-tier scope only).

`LoadError` schema (unchanged): `LoadError(source: str, message: str, section: str | None, item_id: str | None)`. New within-tier error MUST set:
- `source = "validation"`
- `section = <parser.section_key>`
- `item_id = <duplicate_id>`
- `message = f"duplicate id within tier {tier}; later occurrence dropped"`

---

## 6.5 Partial-override detection (R3-UX.7, R3-UX.8, R3-UX.9, R3-UX.10)

**Purpose:** Catch the foot-gun where a user drops a single file (e.g., `~/.claudechic/workflows/foo/foo_helper/identity.md`) into a higher tier expecting a per-file override, while the lower tier has more files. R3.3 forbids partial overrides; R3-UX.7 requires the loader to enforce that prohibition rather than rely on documentation.

### 6.5.1 Definition

For a given `workflow_id`, the **canonical file set at tier T** is the set of file paths (relative to `<tier_root>/workflows/<workflow_id>/`) that exist under that tier's workflow directory, recursively. A higher-tier directory presents a **partial override** when the next-lower tier (in priority) that defines the same `workflow_id` has files that the higher tier is missing.

Formally, with `T_high > T_low` in priority:

```
files(tier, wf_id) = {
    p.relative_to(<tier>/workflows/<wf_id>/)
    for p in (<tier>/workflows/<wf_id>/).rglob("*")
    if p.is_file() and not p.name.startswith(".")
}

partial_override(T_high, wf_id) ⇔
    files(T_high, wf_id) is non-empty
    AND there exists T_low < T_high (in priority) with files(T_low, wf_id) non-empty
    AND files(T_low, wf_id) - files(T_high, wf_id) is non-empty
```

In words: T_high "has any files at all" AND a lower tier "has files too" AND "lower tier has at least one file the higher tier is missing".

Notes on this definition:
- Files higher tier ADDS (present in `T_high` but not `T_low`) are permitted — overrides may extend the file set.
- The lower tier reference is the **next** lower priority tier that has the workflow, not the package tier specifically. (E.g., comparing user-tier against package-tier when user-tier is the higher; or project-tier against user-tier when both have the workflow.)
- Hidden files (`.name.startswith(".")`) are excluded from comparison.

### 6.5.2 Detection function

`claudechic/workflows/loader.py` MUST provide:

```python
def _reject_partial_overrides(
    workflows_by_tier: dict[Tier, dict[str, WorkflowData]],
    tier_roots: TierRoots,
) -> tuple[dict[str, dict[str, WorkflowData]], list[LoadError]]:
    """Detect partial overrides; drop offending tier's contribution; emit errors.

    For each workflow_id, walk tiers in DESCENDING priority (project → user →
    package). For each tier T_high that has the workflow_id:
        Find next-lower tier T_low (also has workflow_id; lower priority).
        If T_low exists:
            Compute missing = files(T_low, wf_id) - files(T_high, wf_id).
            If missing is non-empty:
                Emit LoadError per R3-UX.7 (see §6.5.4).
                Remove workflow_id from workflows_by_tier[T_high]
                  (fall-through to T_low per R3-UX.9).
                Continue checking lower tiers (T_low may itself have a partial
                  override against an even lower tier).

    Returns (filtered_workflows_by_tier, errors).
    """
```

The function MUST iterate `TIER_PRIORITY` in descending order (project first) so that a user-tier partial override is not invalidated by a package-tier check that hasn't run yet.

### 6.5.3 Fall-through behavior (R3-UX.9)

When a partial override is rejected at tier T_high:
- That tier's `WorkflowData` for the workflow_id is removed from `workflows_by_tier[T_high]`.
- The workflow_id's effective winner becomes the next-lower tier that has the workflow (and is not itself a partial override). Resolution continues normally with the remaining tiers.
- Per-tier records (rules/hints/etc.) parsed from the rejected tier's manifest YAML — if the manifest exists at all — are also dropped from `collected_by_tier[T_high]` for that workflow_id's namespace. Implementation: after `_reject_partial_overrides` returns, prune from `collected_by_tier` any record whose `namespace == wf_id` and whose `tier` was rejected for that wf_id.

The rejected tier's contribution is treated as if it never existed for that workflow. The system stays usable on the next-lower tier; the user is alerted via the LoadError (surfaced to the TUI per R3-UX.8).

### 6.5.4 Error format (R3-UX.7 + R3-UX.10)

The emitted LoadError MUST satisfy:

```python
LoadError(
    source="validation",
    section="workflow",
    item_id=workflow_id,
    message=(
        f"Partial workflow override at {tier_path}: missing "
        f"{', '.join(sorted(missing_files))}. Workflow overrides require "
        f"the full file set. Copy the missing files from the lower level "
        f"({lower_tier_label}), or remove the partial override."
    ),
)
```

Where:
- `tier_path` is the absolute path to the higher tier's workflow directory.
- `missing_files` is the sorted list of relative paths the higher tier is missing.
- `lower_tier_label` is the user-facing label `"package"` / `"user"` / `"project"` (the spec uses `Tier` literals which double as user-facing labels here per R3-UX.7 verbatim wording — the code value `"package"` is also the wording shown to the user).

The wording matches R3-UX.7 verbatim. UI surfaces displaying this LoadError MUST use the `LoadError.message` text directly (do not paraphrase).

### 6.5.5 TUI surfacing (R3-UX.8 — out of scope for this axis)

R3-UX.8 mandates the loud error surface in the TUI. Implementation of the TUI surface is delegated to the UI axis. THIS axis spec MUST guarantee: the LoadError is on `LoadResult.errors`, with `source="validation"` and `section="workflow"`, so the TUI's diagnostic surface (existing pattern at `app.py:1524-1529`) can render it without additional plumbing.

### 6.5.6 INV — partial-override invariant

Add to the test surface (§13):

| Invariant | Test sketch |
|---|---|
| INV-PO-1 | Place `package/workflows/foo/foo.yaml` + `package/workflows/foo/role/identity.md`; place ONLY `user/workflows/foo/role/identity.md` (no `foo.yaml`); assert effective workflow `foo` resolves to `tier == "package"`; assert `LoadResult.errors` contains a LoadError with `source="validation"`, `section="workflow"`, `item_id="foo"`, message containing `"foo.yaml"`. |
| INV-PO-2 | Place full set at package; place partial set at user; place full set at project; assert project wins (project's full set is intact); user-tier partial-override LoadError still emitted; the project-tier outcome is unaffected. |
| INV-PO-3 | Place full set at package; place SUPERSET (extra files) at user; assert user wins; no partial-override error. |

---

## 7. MCP-tool tier walk

`claudechic/mcp.py` `discover_mcp_tools` (currently mcp.py:732) MUST be replaced with:

### 7.1 New signature

```python
def discover_mcp_tools(
    tier_roots: TierRoots,
    **kwargs: Any,
) -> list[TieredMCPTool]:
    """Walk mcp_tools/ in every tier; load each .py via importlib; collect
    tools via get_tools(**kwargs); resolve overrides by tool.name.

    Returns the post-resolve list (project beats user beats package; non-
    conflicting names accumulate; same-name within-tier collisions dropped
    with a logged warning — not surfaced via LoadError because MCP tools
    are not part of LoadResult).
    """
```

### 7.2 Module-name namespacing (import isolation)

The current code uses `module_name = f"mcp_tools.{py_file.stem}"` and writes to `sys.modules[module_name]`. With three tiers, two tiers may both define `cluster.py`. Both modules MUST be importable simultaneously without `sys.modules` collisions. The new module name MUST be:

```python
module_name = f"claudechic._mcp_tools_loaded.{tier}.{py_file.stem}"
```

Helper modules (underscore-prefixed) MUST also be tier-namespaced:

```python
helper_module_name = f"claudechic._mcp_tools_loaded.{tier}.{py_file.stem}"
```

The `claudechic._mcp_tools_loaded.<tier>` namespace MUST NOT be importable from anywhere else; it is a synthetic load-time namespace owned by `discover_mcp_tools`.

### 7.3 Pipeline

```
For tier, root in tier_roots.items():     # ascending TIER_PRIORITY
    mcp_dir = root / "mcp_tools"
    if not mcp_dir.is_dir():
        continue
    # Pre-load helpers (existing pattern preserved, with new module_name)
    for py_file in sorted(mcp_dir.glob("_*.py")):
        if py_file.name == "__init__.py": continue
        load module under module_name = f"claudechic._mcp_tools_loaded.{tier}.{py_file.stem}"
    # Load tool files
    for py_file in sorted(mcp_dir.glob("*.py")):
        if py_file.name.startswith("_"): continue
        load module; call get_tools(**kwargs)
        for tool in get_tools_result:
            tools_by_tier[tier].append(TieredMCPTool(name=tool.name, tier=tier, tool=tool))

# Resolve
resolved, _errors = _resolve_by_id(
    tools_by_tier, section_key="mcp_tools", id_of=lambda t: t.name
)
# _resolve_by_id's LoadErrors for within-tier dups are not surfaced via
# LoadResult (MCP tools are off the LoadResult path); log them at WARNING
# level instead. Use the same id-collision text shape.
return resolved
```

### 7.4 Behavior in collision scenarios

- Project tier defines `cluster.py` with a tool named `cluster_dispatch`; package tier also defines `cluster.py` with a tool named `cluster_dispatch`. Both modules import successfully. After resolution, only the project-tier `TieredMCPTool` remains. The package-tier module remains in `sys.modules` (under its tier-namespaced name) but its tool is not registered with the MCP server.
- Within-tier collision (one tier's `mcp_tools/` has two files that produce tools with the same name): WARNING logged; first-discovered tool kept; later occurrences dropped.

### 7.5 Caller migration

The single existing caller of `discover_mcp_tools` (located by Implementer via grep) MUST be updated to:
- Pass a `TierRoots` instead of a single `Path`.
- Extract `t.tool` from each `TieredMCPTool` before passing to the SDK MCP server registration.

---

## 8. `agent_folders.py` post-restructure

### 8.1 `assemble_phase_prompt` — new signature

```python
def assemble_phase_prompt(
    workflow_dir: Path,
    role_name: str,
    current_phase: str | None,
) -> str | None:
    """Assemble identity.md + <phase>.md from `workflow_dir`.

    The caller MUST resolve workflow_dir from LoadResult.workflows[wf_id].path
    BEFORE invoking. This function does not perform tier walking; tier
    resolution has already happened (R3.3 — winning tier owns the full file
    set).

    Returns None if workflow_dir is not a directory.
    """
```

The previous `workflows_dir` argument is REMOVED. The function no longer scans for the workflow; the caller passes the resolved directory directly.

### 8.2 `_find_workflow_dir` — REMOVED

Workflow-id → directory lookup is now the loader's responsibility (`LoadResult.workflows[wf_id].path`). The standalone `_find_workflow_dir(workflows_dir, workflow_id)` (current agent_folders.py:20) MUST be deleted.

If a non-loader caller needs the same lookup, it MUST consult `LoadResult.workflows`. There is exactly one consumer of `_find_workflow_dir` today (`assemble_phase_prompt`), and it is rewritten above; deletion is straightforward.

### 8.3 `create_post_compact_hook` — new signature

Per SPEC.md §4.8, the post-compact hook reads the phase-context file directly from disk; it does NOT call `assemble_phase_prompt` or capture an engine/workflow-dir reference. The single producer of `phase_context.md` is `_write_phase_context` (which still uses `assemble_phase_prompt` internally); the hook is a single consumer.

```python
def create_post_compact_hook(
    phase_context_path: Path,   # absolute path to <repo>/.claudechic/phase_context.md
) -> dict[str, Any]:
    """Create a PostCompact hook that re-injects the phase-context file content.

    `phase_context_path` is captured at hook-creation time. On each /compact,
    the hook reads the file fresh from disk and returns:
        {"reason": <file contents>}   if file exists and is non-empty
        {}                             if file is absent or empty

    The hook does NOT consult the engine, the workflow directory, or
    `assemble_phase_prompt`. The file on disk is the source of truth.
    """
```

The previous `workflows_dir` argument is REMOVED. The previous `engine` and `agent_role` arguments are also REMOVED (the file already contains the assembled prompt; no re-assembly is needed).

`assemble_phase_prompt` is retained as the helper that `_write_phase_context` uses to build the file content (Group A keeps the function in `agent_folders.py`); it is not invoked from inside the hook closure.

### 8.4 Caller migration (`app.py`)

`app.py` currently calls these functions at:

| Site | Existing call | New call |
|---|---|---|
| `app.py:917-923` | `create_post_compact_hook(engine=..., agent_role=..., workflows_dir=self._cwd / "workflows")` | `create_post_compact_hook(phase_context_path=self._cwd / ".claudechic" / "phase_context.md")` (per §8.3 + SPEC.md §4.8 — hook reads file directly; no engine/workflow_dir capture) |
| `app.py:1840-1843` | `assemble_phase_prompt(workflows_dir=self._workflows_dir, workflow_id=..., ...)` | `assemble_phase_prompt(workflow_dir=self._load_result.workflows[wf_id].path, role_name=..., current_phase=...)` (this call is from `_write_phase_context`, which still uses the helper to assemble file content; the hook does not call this function) |

The instance attribute `self._workflows_dir` (set at `app.py:1493`) is REMOVED from `app.py`. Any other reads of it MUST be replaced by lookups against `self._load_result.workflows`.

---

## 9. `disabled_workflows` / `disabled_ids` interaction with tier resolution

Per composability lens-input §8.2 and UserAlignment R3-UX.1–R3-UX.6: disable-by-id is **tier-agnostic**. Implementation:

### 9.1 Schema: flat list, no per-tier sub-keys (R3-UX.1)

Configuration schema MUST remain as today:

```yaml
# .claudechic/config.yaml
disabled_workflows: [foo, bar]   # flat list of workflow_ids
disabled_ids: ["global:no_bare_pytest"]  # flat list of qualified ids
```

The schema MUST NOT introduce per-tier sub-keys (e.g., `disabled_workflows: {package: [...], user: [...]}`). The disable action is a feature-toggle on the id; tier is irrelevant.

### 9.2 Filter is applied AFTER resolution (R3-UX.2)

The existing `_filter_load_result(result, config)` (currently at `app.py:150`) MUST be applied AFTER `ManifestLoader.load()` returns — the loader does NOT consult `ProjectConfig`. This preserves separation-of-concerns (Seam-B): the loader returns the full effective content (with per-id tier provenance maps); the app layer filters by user preference.

### 9.3 Filter operates on the post-resolve `LoadResult`

`_filter_load_result` operates on the post-resolve `LoadResult.workflows` and `LoadResult.<category>` lists. Behavior:

- A `workflow_id` in `config.disabled_workflows` is removed from `LoadResult.workflows` regardless of which tier it came from. (If a project-tier override exists, the project's override wins resolution and is then filtered out — the user-tier or package-tier copy of the same id is NOT promoted as a "fallback"; disabled means disabled across all tiers.)
- An item id in `config.disabled_ids` is removed from `LoadResult.<category>` regardless of source tier.
- Items whose `namespace` matches an entry in `config.disabled_workflows` are removed (per current behavior, `app.py:162`).

### 9.4 No fallback promotion

The spec MUST NOT introduce a "if project-tier is disabled, fall through to user-tier or package-tier" rule. Disabling is removal, not de-prioritization.

### 9.5 INV-3 still holds

A project-only `disabled_workflows: [foo]` removes `foo` from the effective set even if `foo` is defined only at the package tier. Removed workflows are not visible in the workflow picker, and any related rules/injections/hints with `namespace == foo` are also removed (existing `_filter_load_result` behavior).

### 9.6 Unknown-id warn-don't-error (R3-UX.4)

When `_filter_load_result` runs and `config.disabled_workflows` contains an id not present in `LoadResult.workflow_provenance`, the filter MUST:

- NOT raise an error.
- NOT prevent app startup.
- Log a WARNING via `claudechic.errors.log` of the form: `disabled_workflows: unknown workflow_id '<id>' (not defined at any tier)`.
- The `disabled_workflows` entry is silently ineffective at load time (no records to filter).

Symmetric behavior for `config.disabled_ids` against `LoadResult.item_provenance`.

The contract this places on the implementation:

```python
def _filter_load_result(result: LoadResult, config: ProjectConfig) -> LoadResult:
    # ... existing filter logic ...

    # R3-UX.4: warn-don't-error on unknown ids in the disable lists.
    for wf_id in config.disabled_workflows:
        if wf_id not in result.workflow_provenance:
            log.warning("disabled_workflows: unknown workflow_id %r (not defined at any tier)", wf_id)
    for item_id in config.disabled_ids:
        if item_id not in result.item_provenance:
            log.warning("disabled_ids: unknown id %r (not defined at any tier)", item_id)

    return LoadResult(...)  # filtered as today
```

The warning is for diagnostics only; it MUST NOT appear on `LoadResult.errors` (those are reserved for actionable load-time errors that block content; an unknown disable-list entry is not blocking).

### 9.7 Discovery surfaces consume `LoadResult.workflow_provenance` / `item_provenance` (R3-UX.3, R3-UX.5)

UI surfaces (workflow picker, settings UI) that present available ids for the user to disable MUST source per-id tier provenance from `LoadResult.workflow_provenance` and `LoadResult.item_provenance`. The loader exposes these maps; UI rendering is delegated to the UI axis spec.

User-facing wording (per R3-UX wording, prescribed verbatim — UI implementations MUST follow):

- Workflow row: `<workflow_id> (defined at: <levels>)` where `<levels>` is the comma-joined tier set rendered with the user-facing label **"level"** (i.e., display `"package"`, `"user"`, `"project"` — the same string values, but the surrounding helper text uses "level").
- Helper / tooltip text on the disable control: *"Disabling a workflow by ID hides it from this project regardless of which level (package / user / project) defines it."* (verbatim from R3-UX wording).
- The control is labeled **"Disabled workflows"** (not "Workflow disable list" / "ID blacklist" — these violate L4 / R3-UX wording).
- "Tier" MUST NOT appear in user-facing labels. "Tier" is reserved for spec/code (per L4 + R3-UX wording).

---

## 10. Public API

### 10.1 `claudechic/workflows/__init__.py` exports

```python
__all__ = [
    "LoadError",
    "LoadResult",
    "ManifestLoader",
    "ManifestSection",
    "Phase",
    "PhaseAdvanceResult",
    "Tier",
    "TIER_PRIORITY",
    "TierRoots",
    "WorkflowData",
    "WorkflowEngine",
    "WorkflowManifest",
    "assemble_phase_prompt",
    "create_post_compact_hook",
    "register_default_parsers",
    "walk_tiers",
]
```

`register_default_parsers(loader)` is unchanged in shape; it registers the same five parsers (`RulesParser`, `InjectionsParser`, `ChecksParser`, `HintsParser`, `PhasesParser`).

### 10.2 Removed public symbols

- `discover_manifests(global_dir, workflows_dir)` — removed; callers use `walk_tiers(tier_roots)` or `discover_manifests_single_tier(root)`.

### 10.3 Test surface migration

Tests that construct `ManifestLoader` directly (located by Implementer via grep — current call sites listed in §11.1) MUST migrate to `ManifestLoader(tier_roots=TierRoots(package=..., user=None, project=None))`. Tests that exercise the loader against a single directory MUST place that directory's `global/` and `workflows/` subdirs under a tier root.

---

## 11. Error semantics

### 11.1 Tier-walking errors

| Condition | Behavior |
|---|---|
| `tier_roots.package` is None | TypeError at `TierRoots` construction (`package: Path` is non-Optional). |
| `tier_roots.package` does not exist as a directory | LoadResult with one fatal LoadError(source="discovery", message="package tier unreadable: ..."); empty content. **Fail closed for package tier.** |
| `tier_roots.package` exists but is unreadable (OSError) | Same as above (fail closed). |
| `tier_roots.user` is None or not a directory | Skip this tier silently; no error. |
| `tier_roots.project` is None or not a directory | Skip this tier silently; no error. |
| `tier_roots.user` exists but is unreadable (OSError) | LoadError(source="discovery", message="user tier unreadable: ..."); continue with empty user-tier content. **Fail open for non-package tiers.** |
| `tier_roots.project` exists but is unreadable (OSError) | Same fail-open behavior. |
| Individual manifest YAML parse error | LoadError(source=str(path), message=...); skip that manifest; continue. (Existing pattern preserved.) |
| Individual record validation error | Logged warning (parser-specific); record skipped; no LoadError surfaced. (Existing per-item fail-open preserved.) |
| Within-tier duplicate id | LoadError(source="validation", section=<key>, item_id=<id>, message=...); duplicate dropped; first occurrence kept. |
| Cross-tier duplicate id | No error; override applied. |
| Partial workflow override at higher tier (R3-UX.7) | LoadError(source="validation", section="workflow", item_id=<workflow_id>, message=verbatim R3-UX.7 wording with missing-file list and lower-level label). The offending tier's contribution to that workflow_id is dropped (§6.5.3 fall-through). Lower-tier copy of the workflow becomes the effective winner. App startup is NOT blocked. The error appears on `LoadResult.errors` and is rendered through the existing `app.py:1524-1529` toast pattern (R3-UX.8). |

### 11.2 Preservation of existing patterns

- Per-item fail-open in parsers (skip + log) MUST be preserved.
- Per-manifest fail-open (skip + LoadError) MUST be preserved.
- Package-tier fail-closed (return empty LoadResult with fatal error) MUST be preserved (current behavior at loader.py:186-194; the boundary is "the floor of fallback defaults" — without package tier the system has nothing).

### 11.3 Boundary between user-config and loader

The loader MUST NOT read `ProjectConfig` (no consultation of `disabled_workflows` / `disabled_ids` inside `ManifestLoader.load()`). Filtering is the caller's responsibility (`_filter_load_result` in `app.py`).

---

## 12. Fallback-discovery reimplementation (A8)

### 12.1 Pattern (re-implemented from scratch; no cherry-pick)

The pattern that abast's `d55d8c0` introduced (project-overrides-or-defaults; 2-tier) is generalized here to 3 tiers. There is NO selective git extraction; the implementation is part of §5 above. Specifically:

- The fallback selector at `app.py:1493-1497` is REMOVED. `app.py` constructs a `TierRoots` instead:

```python
tier_roots = TierRoots(
    package=_PKG_DIR / "defaults",
    user=Path.home() / ".claudechic" if (Path.home() / ".claudechic").is_dir() else None,
    project=self._cwd / ".claudechic" if (self._cwd / ".claudechic").is_dir() else None,
)
self._manifest_loader = ManifestLoader(tier_roots=tier_roots)
```

- The 2-tier "if cwd has it, use cwd; else defaults" branch in abast's commit is replaced by the 3-tier `walk_tiers` traversal (§5.2). Lower-tier content is no longer "discarded if higher tier present"; lower-tier content **contributes** to non-conflicting ids (R3.4) and is **overridden** for conflicting ids (R3.2).

### 12.2 No selective adoption

The implementer MUST NOT consult `git cherry-pick`, `git show d55d8c0 -- claudechic/workflow_engine/loader.py`, or any partial-extraction approach. The reimplementation is from scratch, following §5 above.

### 12.3 Behavior parity with abast's intent

In the degenerate case where `~/.claudechic/` is absent and `<repo>/.claudechic/` is absent, behavior MUST match abast's commit: only `claudechic/defaults/` is consulted; the system works "out of the box" with no user-level or project-level overrides. INV-3 is the test for this.

---

## 13. Test surface (Implementer/Tester contract)

The implementation MUST add tests that cover at least the following invariants. Test file placement is at the Tester's discretion; recommended is a new `tests/test_loader_tiers.py`.

| Invariant | Test sketch |
|---|---|
| INV-1 | Set up `package/workflows/foo/foo.yaml` and `user/workflows/foo/foo.yaml`; assert `LoadResult.workflows["foo"].tier == "user"` and `.path` points at user-tier. |
| INV-2 | Add `project/workflows/foo/foo.yaml`; assert tier == "project". |
| INV-3 | `TierRoots(package=p, user=None, project=None)`; assert system loads package-only content; no errors. |
| INV-4 | Same rule id at user and project; assert exactly one `Rule` in `LoadResult.rules`, `tier == "project"`. |
| INV-5 | Two rules with the same id in one tier's `rules.yaml`; assert one survives + one LoadError with `source == "validation"`. |
| INV-8 | Rule out: belongs to Seam-D / hint state — covered separately in hints axis tests. (Loader-side invariant: same hint id at multiple tiers produces one HintDecl with project tier; lifecycle key is identical.) |
| Phase pruning (§4.6) | Workflow `foo` defined at package and overridden at project; assert `LoadResult.phases` contains only project-tier phases for namespace `foo`. |
| MCP override (§7) | Place `cluster.py` in package and project; assert tool returned by `discover_mcp_tools` is the project version (`TieredMCPTool.tier == "project"`). |
| MCP within-tier collision (§7.4) | Same tier produces two tools with name `dispatch`; assert only one survives; warning logged. |
| disabled_workflows tier-agnostic (§9.5) | Workflow `foo` only at package; `config.disabled_workflows = ["foo"]`; assert `foo` absent from `LoadResult.workflows` after `_filter_load_result`. |
| disabled_workflows unknown-id warn (§9.6) | `config.disabled_workflows = ["nonexistent"]`; no workflow `nonexistent` at any tier; assert `_filter_load_result` returns successfully (no exception); assert WARNING logged via `claudechic.errors.log`; assert `LoadResult.errors` does NOT contain a related entry. |
| disabled_ids unknown-id warn (§9.6) | Symmetric for `disabled_ids` against `LoadResult.item_provenance`. |
| Workflow provenance multi-tier (§5.3) | Workflow `foo` defined at package AND user; assert `LoadResult.workflow_provenance["foo"] == frozenset({"package", "user"})`; `LoadResult.workflows["foo"].defined_at == frozenset({"package", "user"})`; `.tier == "user"`. |
| Item provenance multi-tier (§5.3) | Rule `global:no_bare_pytest` defined at package AND project; assert `LoadResult.item_provenance["global:no_bare_pytest"] == frozenset({"package", "project"})`. |
| INV-PO-1 partial override fall-through (§6.5.6) | Higher-tier directory missing files relative to lower; assert effective workflow falls through to lower tier; assert LoadError on `LoadResult.errors` with `source="validation"`, `section="workflow"`, message contains the missing file name. |
| INV-PO-2 partial override does not affect higher tier (§6.5.6) | User has partial; project has full; assert project wins, partial-override LoadError still surfaces, project workflow unaffected. |
| INV-PO-3 superset is not partial (§6.5.6) | Higher tier has every lower-tier file plus extras; assert no partial-override error; higher tier wins. |
| Fail-closed package tier (§11.1) | `package` does not exist; assert single fatal LoadError, empty content. |
| Fail-open user tier (§11.1) | `user` exists but `chmod 000`; assert LoadError logged, package content still loads. |

---

## 14. Cross-references to lens inputs

This spec is consistent with `specification/composability.md` AND with UserAlignment's cross-lens MUSTs (`specification/user_alignment.md` §"Cross-lens: UX validation").

### 14.1 Composability lens-input

| Composability clause | Where addressed |
|---|---|
| R1.1, R1.2 | §2.2 `TierRoots`; §5.2 `walk_tiers` |
| R1.3 | §11.1 fail-open for non-package tiers; §13 INV-3 test |
| R1.4 | §2.1 `TIER_PRIORITY`; §4 ascending iteration |
| R2.1 | §3 protocol; §4 four resolution policies |
| R2.2 | §3 `ManifestSection` mandates parse + resolve |
| R2.3 | §7 MCP tool walk follows parse-then-resolve shape |
| R2.4 | §3 protocol-only contract; §10 register_default_parsers unchanged |
| R3.1 | §4.1–§4.7 identity units enumerated |
| R3.2 | §4 + §6 full-record replacement; no field-level merging |
| R3.3 | §4.1 + §4.6 + §5.4 step 5 workflow-scoped pruning + §6.5 partial-override detection |
| R3.4 | §4 non-conflicting ids accumulate (default `_resolve_by_id` behavior) |
| R3.5 | §6 within-tier vs cross-tier split |
| R3.6 | §2.3 + §2.4 tier-tagged dataclasses + TieredMCPTool |
| Seam-A | §3 (parse/resolve) + §5.2 (walk_tiers) |
| Seam-B | §5.3 LoadResult; §11.3 loader does not read ProjectConfig |
| Seam-D | §4.4 hint id preservation; INV-8 |
| INV-1, INV-2, INV-4, INV-5 | §13 test surface |
| §8.2 disabled_workflows | §9 |

### 14.2 UserAlignment cross-lens MUSTs

| UserAlignment clause | Where addressed |
|---|---|
| R3-UX.1 (flat list, no per-tier sub-keys) | §9.1 |
| R3-UX.2 (filter post-resolution) | §9.2 |
| R3-UX.3 (discovery shows tier provenance per workflow_id) | §2.3 (`WorkflowData.defined_at`); §5.3 (`LoadResult.workflow_provenance`); §9.7 (UI consumes); §13 test |
| R3-UX.4 (unknown-id warn-don't-error) | §9.6 |
| R3-UX.5 (symmetric for `disabled_ids`) | §9.6 (item_provenance); §5.3 |
| R3-UX.6 (A12 postponement allowed for discovery UX, not for disable action) | UI spec scope; loader produces the data, postponement-vs-not is a UI decision |
| R3-UX.7 (loader-level loud error on partial override; verbatim message wording) | §6.5.4 |
| R3-UX.8 (TUI surfacing) | §6.5.5 — loader places LoadError on `LoadResult.errors`; TUI surface delegated |
| R3-UX.9 (fall-through behavior) | §6.5.3 |
| R3-UX.10 (docs document full-file-set rule) | docs scope; loader emits the wording in the LoadError |
| R3-UX.11 (one-click "Override this workflow" affordance) | UI spec scope; out of scope for this axis |
| User-facing wording: "level" not "tier" | spec preamble + §9.7 (loader/code uses "tier"; UI uses "level") |

---

*End of axis spec.*
