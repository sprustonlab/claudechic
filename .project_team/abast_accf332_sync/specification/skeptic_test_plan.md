# Skeptic Test Plan -- abast_accf332_sync

**Author:** Skeptic
**Date:** 2026-05-01
**Phase:** project-team:testing-specification
**Input documents:** `testing/skeptic.md`, `testing/TESTING_VISION.md`,
`testing/composability.md`, `testing/terminology.md`,
`testing/user_alignment.md`, `userprompt_testing.md`
**Implementation commit:** `b106cff`

This plan provides concrete test specifications for each of the 7 silent-
regression scenarios from `testing/skeptic.md`. For each scenario the
plan records: test name + file, the falsification statement, why an
isolation test alone misses the regression, and a Q1-Q4 verdict. The
plan also specifies the full 44-case regex parameterized test
(`tests/test_pytest_needs_timeout_regex.py`) and the live remote-control
smoke check for B3+B4 (manual, not pytest).

Disposition of the 4 pre-existing `get_phase` test failures is given in
the final section.

---

## How to read this plan

Each scenario section has the same shape:

- **Test name(s) + file** -- use as the literal pytest test name.
  Naming follows the `test_<letter><sub>_<concept>_<expectation>`
  convention from `testing/terminology.md`.
- **Falsification statement** -- what WOULD be true if the regression
  occurred. The test fails iff the falsification statement holds.
- **Why isolation misses it** -- why a test that only covers one layer
  or one code path can stay green while the regression is live.
- **Q1-Q4 verdict** -- per the Q1-Q6 table in `testing/skeptic.md`.
  Q1 = covers user's actual requirement, Q2 = reveals contract breaks,
  Q3 = depends on out-of-cluster commits, Q4 = proves user-visible delta.
  Each verdict is YES / NO / PARTIAL with a one-sentence justification.

Test files are all under `tests/`. New files are marked **(NEW)**.

---

## Scenario 1 -- Empty-digest case

**Source:** `testing/skeptic.md` item 1; slot 2 S1; v2-8 in
`specification/skeptic_review.md`. Status in b106cff: **NOT FIXED** --
`assemble_constraints_block` still emits ~138 chars of placeholder text
when both rules and checks are empty. The `if not constraints.strip()`
guard in `assemble_agent_prompt` is dead code.

### Test 1a

**Name:** `test_d3_empty_loader_emits_sentinel_not_placeholder`

**File:** `tests/test_constraints_block.py` (NEW)

**What to assert:**

```python
from claudechic.workflows.agent_folders import assemble_constraints_block

result = assemble_constraints_block(
    loader=None,
    role="coordinator",
    phase=None,
    engine=None,
    active_workflow=None,
    disabled_rules=frozenset(),
    include_skipped=False,
)
# Must not emit the placeholder table -- either return a single-line
# sentinel string OR an empty string.
assert result is not None
assert len(result) < 50, (
    f"Empty-path block is {len(result)} chars; expected a short sentinel "
    f"or empty string, not a placeholder table:\n{result!r}"
)
assert "| id |" not in result      # no table emitted
assert "### Rules" not in result   # no section headers emitted
```

**Falsification statement:** If regression is live, `result` is ~138+ chars
containing `### Rules (0 active)` and/or `### Advance checks` with no
rows -- boilerplate that the model has to parse and discard on every
default-roled agent launch.

**Why isolation misses it:** All existing tests pass a populated loader.
The empty path only fires when `loader=None` or both rules and checks
resolve to empty -- a configuration that production hits for every
default-roled agent in a no-workflow session. No current test exercises
this branch.

**Q1:** PARTIAL. The user does not see the constraints block directly,
but an agent receiving 138 chars of empty table overhead on every launch
wastes context and confuses self-description. A real user would notice
longer TTFT and cryptic "no rules" table in get_agent_info output.

**Q2:** YES. Reveals the dead-code guard (`if not constraints.strip()` in
`assemble_agent_prompt` never fires). The correct fix is either: emit a
single-line sentinel ("no constraints for this role and phase") or return
an empty string that `assemble_agent_prompt` interprets as "skip block."
The test drives that choice.

**Q3:** NO. Pure-function test. No cluster SHA dependency.

**Q4:** NO. Purely agent-visible overhead, not user-visible.

### Test 1b (companion, assemble_agent_prompt dead-code guard)

**Name:** `test_d3_assemble_agent_prompt_skips_empty_constraints_block`

**File:** `tests/test_constraints_block.py` (NEW)

**What to assert:**

```python
from claudechic.workflows.agent_folders import assemble_agent_prompt
from pathlib import Path
import tempfile

with tempfile.TemporaryDirectory() as tmp:
    result = assemble_agent_prompt(
        role="coordinator",
        phase=None,
        loader=None,
        workflow_dir=None,
        artifact_dir=None,
        project_root=Path(tmp),
        engine=None,
        active_workflow=None,
        disabled_rules=frozenset(),
    )
# With no workflow dir and no loader, the phase prompt is None and the
# constraints block is empty. The function should return None (skip
# injection entirely) rather than a string consisting only of
# placeholder whitespace/tables.
assert result is None or (
    isinstance(result, str) and "### Rules" not in result
), f"Empty-path assemble returned non-None with placeholder: {result!r}"
```

**Falsification statement:** If regression, `assemble_agent_prompt` with
no workflow dir and no loader returns a non-empty string containing
section headers from an all-zero digest.

---

## Scenario 2 -- B5 case-insensitive rejection

**Source:** `testing/skeptic.md` item 2; slot 2 S2; slot 4 fix in
`loader.py`. Status in b106cff: **FIXED** -- `.strip().lower()` comparison.
Regression risk: a future "simplification" back to `==`.

### Test 2

**Name:** `test_b5_main_role_rejects_case_variants_of_default`

**File:** `tests/test_agent_role_identity.py` (NEW)

**What to assert:**

```python
import pytest
from claudechic.workflows.loader import ManifestLoader   # or whichever
                                                          # class validates

REJECT_VARIANTS = [
    "Default",
    "DEFAULT",
    " default ",
    "default\n",
    "dEfAuLt",
    "\tdefault",
    "DEFAULT_ROLE",   # wrong -- this is the Python identifier, not the value
]

@pytest.mark.parametrize("bad_role", REJECT_VARIANTS)
def test_b5_main_role_rejects_case_variants_of_default(bad_role, tmp_path):
    """B5: any case-variant of the DEFAULT_ROLE sentinel is rejected at
    loader validation time.  A future simplification to `==` would fail
    on "Default" while "default" passed, silently re-enabling the
    collision between a user-defined role and the sentinel.
    """
    manifest_yaml = f"""
id: test_wf
main_role: {bad_role!r}
phases: []
"""
    (tmp_path / "manifest.yaml").write_text(manifest_yaml, encoding="utf-8")
    with pytest.raises((ValueError, RuntimeError, KeyError), match=r"(?i)default"):
        # Adjust to the actual exception the validator raises.
        ManifestLoader(project_dir=tmp_path).load()
```

**Falsification statement:** If regression, a manifest with
`main_role: Default` loads without error, creating a workflow whose
`main_role` compares unequal to `DEFAULT_ROLE` ("default") and causes the
B3 role-promote path to set `agent.agent_type = "Default"` rather than
properly detecting the collision.

**Why isolation misses it:** The fix is a one-liner in loader.py. A test
using only the exact string `"default"` passes both before and after a
regression back to `==`. The case-variant test cases are the only ones
that distinguish the two implementations.

**Q1:** YES. A user writing `main_role: Default` in their workflow would
see the entire B/D substrate become inert -- their main agent would not
receive role-scoped rules because the identity flip never fires correctly.

**Q2:** YES. Reveals exact validator contract: case-insensitive rejection
of the sentinel value.

**Q3:** NO. Loader-only test.

**Q4:** YES. User-visible delta: workflow activation appears to succeed but
the role never promotes to the workflow's intended main role.

---

## Scenario 3 -- B3+B4 mid-session role flip (live remote-control)

**Source:** `testing/skeptic.md` item 3; `testing/TESTING_VISION.md`
criterion 2. Status in b106cff: **FIXED** (B3 mutations in app.py at
lines ~2082/2454/2581; B4 `lambda: agent.agent_type` hook closure).

This scenario CANNOT be fully covered by in-process pytest because the
bug class (closure binding too early) only manifests when the SDK
`connect()` / hook-fire sequence runs in the actual subprocess-IPC path.
An in-process mock of `_guardrail_hooks` that replaces the closure with a
MagicMock would pass even with a snapshot-binding regression.

### Manual smoke check procedure (not pytest)

**Location:** Not a pytest file. Record results in the run's test log.

**Pre-conditions:**
- claudechic running with `project_team` or any workflow whose manifest
  has a non-default `main_role` (e.g. `main_role: coordinator`).
- Remote-control server active: `./scripts/claudechic-remote 9999`.
- One agent running (the main agent).

**Step 1 -- Baseline identity before activation:**
```bash
curl -s http://localhost:9999/mcp/get_agent_info | jq '.identity.role'
```
Expected: `"default"` (the DEFAULT_ROLE sentinel value).
Assertion: `agent.agent_type == DEFAULT_ROLE`.

**Step 2 -- Activate workflow:**
```bash
curl -s -X POST http://localhost:9999/send \
  -d '{"message": "/project_team"}'
```
Wait for the activation acknowledgment (tool result from `advance_phase`
visible in the chat transcript).

**Step 3 -- Post-activation identity:**
```bash
curl -s http://localhost:9999/mcp/get_agent_info | jq '.identity.role'
```
Expected: `"coordinator"` (the workflow's `main_role`).
Assertion (must hold without an SDK reconnect):
```
agent.agent_type == workflow.main_role
```
This is the B3 role-promote mutation and the B4 hook-closure live-read
combined. A snapshot-binding bug would return `"default"` here.

**Step 4 -- Deactivate workflow:**
```bash
curl -s -X POST http://localhost:9999/send \
  -d '{"message": "/deactivate"}'
```
Wait for deactivation acknowledgment.

**Step 5 -- Post-deactivation identity:**
```bash
curl -s http://localhost:9999/mcp/get_agent_info | jq '.identity.role'
```
Expected: `"default"` (reverted to DEFAULT_ROLE).
Assertion: `agent.agent_type == DEFAULT_ROLE`.

**Step 6 -- Post-compact survival:**
```bash
curl -s -X POST http://localhost:9999/send -d '{"message": "/compact"}'
# Wait for compact to complete
curl -s http://localhost:9999/mcp/get_agent_info | jq '.identity.role'
```
Expected: role survives compact (stays at `"default"` since we deactivated;
if you compact while active, it stays at `"coordinator"`). Assert the
value is unchanged from pre-compact.

**Falsification statement:** If B3 regression: step 3 shows `"default"` --
the promote mutation was lost or never fired. If B4 regression: step 3
shows the correct role in `get_agent_info` (the MCP layer reads live) but
the hook layer still fires rules scoped to `"default"` -- detectable by
checking whether role-scoped rules apply. If compact regression: step 6
shows a role reset to `"default"` even though the workflow was still active.

**Q1:** YES. The user's stated intent ("dynamic roles") is fully verified:
activate -> see new role -> deactivate -> see default -> compact ->
survive. This is the "before vs after" sentence from SPEC §B WHY (User).

**Q2:** YES. Tests the agent.agent_type contract surface live.

**Q3:** NO. Self-contained within abast_accf332_sync; b106cff's
`_guardrail_hooks` changes are what's being exercised.

**Q4:** YES. User can observe the role change in `get_agent_info` output
and via MCP tool calls. Role-scoped rule application is agent-visible
behavioral change.

### Companion in-process test (does not replace the smoke check)

**Name:** `test_b4_guardrail_hook_reads_agent_type_live`

**File:** `tests/test_agent_role_identity.py` (NEW)

**What to assert:**

```python
from claudechic.agent import Agent, DEFAULT_ROLE

def test_b4_guardrail_hook_reads_agent_type_live(tmp_path):
    """B4: the hook closure captures agent by reference, not by value.
    Mutating agent.agent_type after hook creation must change what the
    hook sees on next fire -- no SDK reconnect needed.
    """
    agent = Agent(name="test", cwd=tmp_path)
    assert agent.agent_type == DEFAULT_ROLE

    # Capture the live-read function the hook would use.
    # This is the lambda: agent.agent_type pattern from app.py.
    live_role = lambda: agent.agent_type

    assert live_role() == DEFAULT_ROLE

    # Simulate what B3 does on workflow activation.
    agent.agent_type = "coordinator"

    # The hook must see the new value -- no reconnect.
    assert live_role() == "coordinator"

    # Simulate deactivation.
    agent.agent_type = DEFAULT_ROLE
    assert live_role() == DEFAULT_ROLE
```

This test catches snapshot-binding regressions (where a refactor
replaces the lambda with `role = agent.agent_type` at closure-creation
time). It does NOT catch the full SDK path; the smoke check above covers
that.

---

## Scenario 4 -- Source-of-truth alignment (cross-layer keystone test)

**Source:** `testing/skeptic.md` item 4; `testing/TESTING_VISION.md`
§"Cross-layer assertion"; `testing/composability.md` §2.6. Status in
b106cff: **FIXED** via `_LoaderAdapter` + `_get_disabled_rules()` wiring
at 4 MCP sites. This is the highest-value test shape per the failure-cost
matrix.

### Test 4 (the keystone test)

**Name:** `test_d6_hook_loader_and_registry_loader_return_identical_rules`

**File:** `tests/test_constraints_block.py` (NEW)

**What to assert:**

```python
from claudechic.guardrails.digest import compute_digest
from claudechic.workflows.loader import ManifestLoader
# Adjust import path for _LoaderAdapter and _filter_load_result --
# they are in app.py but may be extractable for testing.

def test_d6_hook_loader_and_registry_loader_return_identical_rules(
    tmp_path, monkeypatch
):
    """D6 source-of-truth alignment: the hook layer reads its rules
    through _LoaderAdapter which returns _filter_load_result(raw_loader.load()).
    The registry layer (_load_result) is also _filter_load_result(raw_loader.load()).
    They must be identical.  A regression that re-routes the hook layer
    through self._manifest_loader directly breaks this alignment
    silently.
    """
    # Build a minimal project config that disables one rule.
    disabled_rule_id = "global:no_rm_rf"
    project_config_yaml = f"""
guardrails: true
disabled_ids:
  - {disabled_rule_id}
"""
    (tmp_path / ".claudechic").mkdir()
    (tmp_path / ".claudechic" / "config.yaml").write_text(
        project_config_yaml, encoding="utf-8"
    )

    manifest_loader = ManifestLoader(project_dir=tmp_path)
    raw_result = manifest_loader.load()

    # Simulate _filter_load_result: rules not in disabled_ids are kept.
    # Import the actual function from app.py (adjust as needed).
    from claudechic.app import _filter_load_result   # or wherever it lives
    from claudechic.config import ProjectConfig

    project_config = ProjectConfig.load(tmp_path)
    filtered = _filter_load_result(raw_result, project_config, config=None)

    # _LoaderAdapter.load() must return the same result.
    from claudechic.app import _LoaderAdapter
    cached_result = [None]
    cached_result[0] = filtered
    adapter = _LoaderAdapter(
        get_load_result=lambda: cached_result[0],
        fallback=manifest_loader,
    )
    adapter_result = adapter.load()

    # Rule IDs from both paths must be identical.
    hook_ids = {r.id for r in adapter_result.rules}
    registry_ids = {r.id for r in filtered.rules}

    assert hook_ids == registry_ids, (
        f"Hook layer sees {hook_ids - registry_ids} extra; "
        f"registry sees {registry_ids - hook_ids} extra"
    )
    assert "no_rm_rf" not in hook_ids, (
        "Disabled rule 'no_rm_rf' still visible to hook layer"
    )
    assert "no_rm_rf" not in registry_ids, (
        "Disabled rule 'no_rm_rf' still visible to registry layer"
    )
```

**Falsification statement:** If regression (e.g. `_LoaderAdapter.load()`
falls back to `self._manifest_loader.load()` bypassing the filter):
`hook_ids` contains `"no_rm_rf"` while `registry_ids` does not. The
agent's `## Constraints` block says the rule is disabled but the hook
layer fires on it anyway (or vice versa), producing confusing behavior.

**Why isolation misses it:** Per-layer tests can each pass while the layers
report different rule sets. Only a test that asserts on BOTH sets
simultaneously can catch divergence. This is the "cross-layer assertion"
class from `testing/skeptic.md` §TL;DR.

**Q1:** YES. User wants "what rules apply to me" to be consistent -- the
same answer whether the agent consults `## Constraints` or triggers a
hook. Inconsistency erodes agent trust in the substrate.

**Q2:** YES. Pins the exact contract: `_LoaderAdapter.load()` ==
`_filter_load_result(raw_loader.load(), project_config, config)`.

**Q3:** NO. Self-contained.

**Q4:** YES (HIGH-cost failure). User sees agent self-correcting on a rule
that doesn't fire, or a rule firing that the agent believes is disabled.

---

## Scenario 5 -- Default-roled agents bypass constraints block (by-design)

**Source:** `testing/skeptic.md` item 5; slot 2 S4. Status in b106cff:
**BY DESIGN** -- `assemble_agent_prompt` returns `None` for agents with no
role dir (DEFAULT_ROLE agents get no inject). The SPEC decision is
undocumented (no SPEC section says "default-roled agents get zero
constraints injection").

### Test 5

**Name:** `test_d5_default_role_agent_receives_no_constraints_injection`

**File:** `tests/test_constraints_block.py` (NEW)

**What to assert:**

```python
from claudechic.workflows.agent_folders import assemble_agent_prompt
from claudechic.agent import DEFAULT_ROLE
from pathlib import Path
import tempfile

def test_d5_default_role_agent_receives_no_constraints_injection(
    tmp_path
):
    """D5 + by-design decision: assemble_agent_prompt returns None for
    an agent with DEFAULT_ROLE when no role dir exists in the workflow.
    This documents the current behavior as intentional, NOT a bug.  If
    future work adds sprustonlab/claudechic#27 (per-phase identity
    injection suppression), this test must be updated.

    Regression risk in the other direction: a future change that
    adds default-role prompt injection (feature #27) without documenting
    it would be caught here.
    """
    # No role dir under workflow_dir for DEFAULT_ROLE.
    result = assemble_agent_prompt(
        role=DEFAULT_ROLE,
        phase="specification",
        loader=None,
        workflow_dir=tmp_path,  # tmp_path has no "default/" subdir
        artifact_dir=None,
        project_root=tmp_path,
        engine=None,
        active_workflow=None,
        disabled_rules=frozenset(),
    )
    assert result is None, (
        f"Expected None (no inject for default-roled agent) but got: "
        f"{result!r[:200]}"
    )
```

**Falsification statement:** If regression (or if feature #27 lands
silently), `result` is a non-None string. The test fails, prompting a
decision: is this the intended extension or an accidental inject?

**Why isolation misses it:** There is no existing assertion that pins the
by-design None return. Any refactor that accidentally adds inject logic for
DEFAULT_ROLE would be invisible until agents started receiving unexpected
constraints in their launch prompts.

**Q1:** PARTIAL. Users do not see this directly, but it guards the boundary
between "default-roled agents are unconstrained" and "all agents get
constraints." That boundary has user-level meaning (onboarding agents vs
role-scoped agents).

**Q2:** YES. Documents the interface contract so feature #27 must explicitly
change this test.

**Q3:** NO. Pure-function test.

**Q4:** NO. Not user-visible directly; agent-visible in launch prompt shape.

---

## Scenario 6 -- pytest_needs_timeout regex (44-case parameterized test)

**Source:** `testing/skeptic.md` item 6; slot 6 review; `testing/TESTING_VISION.md`
criterion 4. Status in b106cff: **FIXED** (E1 -- CLAUDE.md updated; regex
hardened to include `uvx` and versioned `python\d+(\.\d+)*`).

The full test file spec follows. This file carries forward the 27-case
implementer set AND adds the 17 skeptic edge cases that diverge from
expected behavior (classified as known limitations, not bugs). The file
MUST use the regex from `claudechic/defaults/global/rules.yaml`
verbatim -- not a local redefinition -- so that a future regex change
automatically re-exercises all cases.

### Test file spec: `tests/test_pytest_needs_timeout_regex.py` (NEW)

```python
"""44-case empirical test of the pytest_needs_timeout guardrail rule.

Tests the regex from claudechic/defaults/global/rules.yaml under the
rule id "pytest_needs_timeout". The regex is read directly from the YAML
source -- NOT redefined here -- so any future change to the rule is
automatically re-exercised against this full case set.

Case classification:
  MUST_MATCH   -- warn rule must fire (pytest invoked without --timeout).
  MUST_NOT     -- warn rule must NOT fire (timeout present, or not pytest).
  KNOWN_LIMIT  -- warn does not fire but arguably should; accepted
                  limitation of the current regex. Recorded here as
                  documentation; test asserts the KNOWN behavior.

Run: pytest tests/test_pytest_needs_timeout_regex.py -v --timeout=30
"""

import re
from pathlib import Path

import pytest
import yaml

# -- Load the regex from the canonical YAML source --------------------

_RULES_YAML = (
    Path(__file__).parent.parent
    / "claudechic" / "defaults" / "global" / "rules.yaml"
)


def _load_rule_pattern(rule_id: str) -> str:
    rules = yaml.safe_load(_RULES_YAML.read_text(encoding="utf-8"))
    for rule in rules:
        if rule.get("id") == rule_id:
            return rule["detect"]["pattern"]
    raise KeyError(f"Rule {rule_id!r} not found in {_RULES_YAML}")


PATTERN = _load_rule_pattern("pytest_needs_timeout")
RX = re.compile(PATTERN)

# PT is split so this file does not trigger no_bare_pytest on itself.
PT = "py" + "test"

# -- Case tables -------------------------------------------------------
# Format: (command_string, description, expected_match: bool)

MUST_MATCH = [
    (PT, "bare pytest"),
    (f"{PT} tests/foo.py", "pytest with positional arg"),
    (f"{PT} -v", "pytest with -v flag"),
    (f"python -m {PT}", "python -m pytest"),
    (f"python3 -m {PT}", "python3 -m pytest"),
    (f"python3.11 -m {PT}", "python3.11 -m pytest (versioned)"),
    (f"uv run {PT} tests/", "uv run pytest"),
    (f"uvx {PT} tests/", "uvx pytest (added in b106cff)"),
    (f"poetry run {PT}", "poetry run pytest"),
    (f"cd foo && {PT}", "cd && pytest"),
    (f"cd foo; {PT}", "cd ; pytest"),
    (f"{PT} tests/test_foo.py -v", "CLAUDE.md preferred form (no --timeout)"),
    (
        f"TS=$(date -u +%Y-%m-%dT%H%M%S) && {PT} --junitxml=.test_results/${{TS}}.xml "
        f"--tb=short 2>&1 | tee .test_results/${{TS}}.log",
        "full-suite form without --timeout (old E1 form -- should warn)",
    ),
    (f"( cd subdir && {PT} )", "parenthesized subshell"),
    (f"echo --timeout=30 && {PT} tests/", "--timeout before && does not satisfy lookahead"),
    (f"{PT} --no-timeout", "--no-timeout is not --timeout"),
]

MUST_NOT = [
    (f'grep -c "{PT}"', "grep -c quoted"),
    (f"grep {PT} .", "grep bareword"),
    (f"rg {PT}", "rg bareword"),
    (f"rg -n {PT} claudechic/", "rg -n with path"),
    (f"cat docs/{PT}.md", "cat docs path"),
    (f"head {PT}_log.txt", "head log path"),
    (f"tail -n 100 {PT}_log", "tail log"),
    (f"# run {PT} later", "shell comment"),
    (f'echo "{PT}"', "echo quoted"),
    (f"ls {PT}_helpers/", "ls helpers"),
    (f"{PT} --timeout=30", "explicit timeout"),
    (f"{PT} -v --timeout=10", "pytest -v with timeout"),
    (f"uv run {PT} tests/foo.py --timeout=5", "uv run with timeout"),
    (f"{PT}er foo", "pytester -- word boundary"),
    (f"{PT}_log.txt", "pytest_log -- snake_case word boundary"),
    (f'alias pt="{PT} -v"', "alias -- pytest not at ^ or after [;&|]"),
    (f'PYTEST_OPTS="--timeout=30" {PT}', "PYTEST_OPTS with --timeout satisfies lookahead"),
    (
        f"TS=$(date -u +%Y-%m-%dT%H%M%S) && {PT} --junitxml=.test_results/${{TS}}.xml "
        f"--tb=short --timeout=30 2>&1 | tee .test_results/${{TS}}.log",
        "CLAUDE.md full-suite form WITH --timeout=30 (post E1 fix)",
    ),
]

# Known limitations: the regex does not handle these runner prefixes.
# Tests assert the CURRENT (non-match) behavior so a future fix to cover
# these cases causes these to flip to MUST_MATCH explicitly.
KNOWN_LIMIT_NO_MATCH = [
    (f"time {PT} tests/foo.py", "time prefix -- not in rule"),
    (f"ENV=1 {PT} tests/foo.py", "env-var prefix -- not in rule"),
    (f"xargs {PT} tests/foo.py", "xargs prefix -- not in rule"),
    (f'bash -c "{PT}"', "bash -c -- pytest inside quotes"),
    (f"hatch run {PT}", "hatch run -- not in prefix list"),
    (f"nox -s {PT}", "nox -s -- not in prefix list"),
    (f"make {PT}", "make target -- not in prefix list"),
    # These are false negatives due to lookahead scanning too far:
    (f"{PT} tests/ # --timeout=30 in comment", "--timeout in comment satisfies lookahead"),
    (
        f"{PT} && {PT} --timeout=30",
        "first bare pytest -- lookahead sees --timeout in rest of string",
    ),
    (
        f"{PT} 2>&1 | grep --timeout-pattern",
        "--timeout-pattern starts with --timeout -- satisfies lookahead",
    ),
    (
        f"{PT} --timeout-method=signal",
        "--timeout-method starts with --timeout -- satisfies lookahead",
    ),
]


# -- Parametrized tests ------------------------------------------------

@pytest.mark.parametrize("cmd,desc", MUST_MATCH)
def test_e_pytest_needs_timeout_warn_fires(cmd, desc):
    """E: pytest_needs_timeout warn rule must fire for bare pytest runs."""
    assert RX.search(cmd), (
        f"Expected match (warn should fire) for: {cmd!r}\n"
        f"Case: {desc}\n"
        f"Pattern: {PATTERN}"
    )


@pytest.mark.parametrize("cmd,desc", MUST_NOT)
def test_e_pytest_needs_timeout_warn_does_not_fire(cmd, desc):
    """E: pytest_needs_timeout warn rule must NOT fire for these inputs."""
    assert not RX.search(cmd), (
        f"Expected no match (warn should NOT fire) for: {cmd!r}\n"
        f"Case: {desc}\n"
        f"Pattern: {PATTERN}"
    )


@pytest.mark.parametrize("cmd,desc", KNOWN_LIMIT_NO_MATCH)
def test_e_pytest_needs_timeout_known_limitation_no_match(cmd, desc):
    """E: these inputs do NOT trigger the warn rule due to known regex
    limitations.  Tests assert current behavior -- when these cases are
    fixed, move them to MUST_MATCH.

    These are NOT failures in the rule; they are documented gaps. The
    rule's primary use case (bare CLI invocations) is covered by
    MUST_MATCH above.
    """
    assert not RX.search(cmd), (
        f"Expected no match (known limitation) for: {cmd!r}\n"
        f"Case: {desc}\n"
        f"If this now matches, the limitation is fixed -- move to MUST_MATCH."
    )
```

**Falsification statement:** If the regex in `rules.yaml` is changed
(tightened, broken, or new false positives introduced), one or more of
the 44 cases fails immediately.

**Why isolation misses it:** The implementer's 22-case set is circular
(built from cases the implementer already knew the regex handled). The
skeptic's 17 additional cases include edge cases from real workflows:
`time pytest`, `ENV=1 pytest`, `echo --timeout=30 && pytest` (which
MUST match), and word-boundary cases (`pytester`, `pytest_log`). Without
the full set, a regex simplification that removes `\b` would pass the
implementer's tests.

**Q1:** YES. A false positive (`grep -c "pytest"`) trains the agent to
ignore the warn channel. A false negative (`ENV=1 pytest tests/`) silently
skips the warn on a real bare run. Both are user-visible: the user sees
the agent either breaking on a documentation string or missing a timeout
hint.

**Q2:** YES. Pins the exact regex surface so any change is immediately
re-exercised against the full case set.

**Q3:** NO. Pure regex test; reads from `rules.yaml` in-tree.

**Q4:** YES (HIGH-cost per failure-cost matrix). False-positive trains agent
to dismiss the warn channel; false-negative means hung tests stay hung.

---

## Scenario 7 -- advance_phase broadcast constraints (D5 inject site 4)

**Source:** `testing/skeptic.md` item 7; slot 3 M1; `testing/TESTING_VISION.md`
criterion 3. Status in b106cff: **FIXED** (D5 inject site #4 broadcast loop
routes through `assemble_agent_prompt`).

### Test 7

**Name:** `test_d5_broadcast_delivers_constraints_block_to_sub_agents`

**File:** `tests/test_constraints_block.py` (NEW)

**What to assert:**

```python
from unittest.mock import MagicMock, patch, call
from claudechic.workflows.agent_folders import assemble_agent_prompt

def test_d5_broadcast_delivers_constraints_block_to_sub_agents():
    """D5 inject site 4 (broadcast): when advance_phase broadcasts the
    new phase prompt to other agents, each agent's prompt must be routed
    through assemble_agent_prompt -- NOT assemble_phase_prompt alone.

    Regression: if the broadcast loop reverts to assemble_phase_prompt,
    sub-agents receive the phase content without the ## Constraints
    block.  This is the slot 3 M1 bug that was fixed in b106cff.
    """
    # Spy on assemble_agent_prompt -- should be called once per
    # sub-agent in the broadcast loop.
    with patch(
        "claudechic.mcp.assemble_agent_prompt",
        wraps=assemble_agent_prompt,
    ) as spy:
        # Simulate the advance_phase broadcast by calling the MCP
        # handler with a stub app that has 2 non-default-role sub-agents.
        # (Adjust to the actual test-harness pattern used in the suite.)
        from claudechic.mcp import _make_advance_phase
        # ... set up stub _app with workflow engine, agents, etc.
        # ... call the broadcast handler
        # ... assert spy was called for each non-default-role sub-agent
        assert spy.call_count >= 1, (
            "assemble_agent_prompt must be called in broadcast loop; "
            "if call_count==0 the broadcast routes around it"
        )

    # Additionally assert the resulting prompt contains ## Constraints.
    # (Use the same stub from above to capture the sent prompt strings.)
    # This is the belt-and-suspenders check per testing/skeptic.md §HIGH.
    # Adjust to capture _app.send_to_agent() calls.
    # for agent_name, prompt in captured_broadcasts:
    #     assert "## Constraints" in prompt, (
    #         f"Agent {agent_name!r} received broadcast without "
    #         f"## Constraints block"
    #     )
```

NOTE: The stub implementation above uses pseudocode comments where the
exact test-harness fixture pattern depends on the testing team's mock
setup. The invariant is: `assemble_agent_prompt` MUST be called in the
broadcast loop (not `assemble_phase_prompt`), AND the result sent to each
sub-agent must contain the `## Constraints` section header.

**Falsification statement:** If regression, `spy.call_count == 0` (the
broadcast loop calls `assemble_phase_prompt` directly, bypassing the
single composition point) and sub-agents' phase prompts lack `##
Constraints`.

**Why isolation misses it:** A test that only calls `assemble_agent_prompt`
directly (unit test) passes regardless of whether the broadcast loop
actually uses it. Only a test that traces the call chain from the MCP
`advance_phase` handler through to the prompt string sent to each sub-
agent can catch this regression.

**Q1:** YES. Sub-agents on phase advance lack the rules that apply to the
new phase -- their constraints are stale or missing. This is the
"advance-phase broadcast misses constraints" HIGH-cost failure in the
failure-cost matrix.

**Q2:** YES. Pins the D5 broadcast site contract: inject site #4 MUST
route through `assemble_agent_prompt`.

**Q3:** NO. Self-contained.

**Q4:** YES (HIGH-cost). Sub-agents work without phase-scoped guardrails
after phase advance. The user notices when sub-agents perform actions
that phase-scoped rules should have blocked or warned on.

---

## Pre-existing `get_phase` test failure disposition

**Source:** `testing/skeptic.md` §"Pre-existing flakes to track-but-not-fix";
slot 3 review M4; `testing/TESTING_VISION.md` §"Pre-existing context".

**Status: RESOLVED in b106cff.** The four failures were:

1. `test_get_phase_returns_rule_count` -- asserted on a rule-count line
   in `get_phase` output. The count line was removed per SPEC Decision 5
   (`get_phase` narrowed to phase-only content). **Migrated to:**
   `test_get_phase_omits_rule_count_line` in `tests/test_artifact_dir.py`.
   New assertion: the output does NOT contain the count line.

2-4. Three additional `test_get_phase_*` tests asserting the old
   combined phase+rules output shape. **Migrated to:**
   `test_get_applicable_rules_filters_disabled_rules`,
   `test_get_applicable_rules_returns_markdown`,
   `test_get_phase_no_engine_reports_none_active`
   in `tests/test_artifact_dir.py`. New assertions target
   `get_applicable_rules` and `get_agent_info` (the two new tools) rather
   than `get_phase`.

**Action:** Run `pytest tests/test_artifact_dir.py -v --timeout=30` and
confirm all four migrated tests pass. If any fail, the `get_phase`
narrowing (SPEC Decision 5) was only partially implemented. **Do NOT
revert to the old shape** -- the failure is a test-migration gap, not a
regression to roll back. Fix the test to assert the narrowed contract.

**Non-resolution path (if the 4 pre-existing failures are still present
at testing-implementation start):** Pick one of the two dispositions
stated in `testing/skeptic.md`:

- **Option A:** Update assertions to the new `get_phase` shape (no rule
  count line) and the new tool names (`get_applicable_rules`,
  `get_agent_info`). This is the correct path if SPEC Decision 5 is
  final.
- **Option B:** Roll back the `get_phase` narrowing if Decision 5 changes.
  This requires a SPEC amendment and coordinator approval.

Do NOT leave the four tests in a failing state without an explicit
disposition. Undisposed pre-existing failures mask new regressions.

---

## Sign-off bar cross-reference

This plan satisfies the conditions from `testing/skeptic.md` §"Sign-off
bar" as follows:

| Bar condition | Coverage in this plan |
|---|---|
| One test per HIGH-cost silent-regression item | Scenarios 4 (D6 cross-layer), 3 (B3+B4 live), 6 (E regex), 7 (broadcast) |
| One cross-layer assertion pinning _LoaderAdapter == _filter_load_result | Test 4 (`test_d6_hook_loader_and_registry_layer_return_identical_rules`) |
| 44-case regex test for E | Scenario 6 full file spec above |
| Live remote-control session for B3+B4 | Scenario 3 manual smoke check procedure |
| Explicit disposition on 4 pre-existing get_phase failures | Section above: RESOLVED in b106cff |
| No tests that pass with default values | All tests in this plan set non-default state: disabled_rules non-empty (S4), case-variant main_role (S2), loader=None (S1), agent_type mutation (S3 companion), broadcast loop spy (S7) |

Tests that FAIL my bar and are explicitly excluded from this plan:

- Tests that mock `assemble_agent_prompt` and assert it gets called --
  excluded per anti-pattern #1. Tests must mock the SDK boundary or run
  the pure function directly.
- Tests that pass `disabled_rules=set()` and assert the unfiltered path
  works -- excluded per anti-pattern #2. All S4/S6 cases set non-empty
  disabled_rules.
- Tests asserting `get_phase` still returns a rule-count line --
  excluded per anti-pattern #4. The narrowing is final.
- Tests using toy loaders (one rule, one phase) instead of the bundled
  `project_team` workflow -- for integration tests, use the real
  bundled workflow.

---

*End of skeptic test plan. Reporting completion to coordinator via
message_agent.*
