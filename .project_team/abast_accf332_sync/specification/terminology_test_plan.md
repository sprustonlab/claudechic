# Terminology Test Plan -- abast_accf332_sync

**Author:** TerminologyGuardian (`terminology_review` seat)
**Phase:** testing-specification
**Authority:** This plan is prescriptive for test-axis agents writing or
reviewing test files. Composability has final say on naming-architecture
conflicts; Skeptic has final say on failure-cost classifications.

Reference documents (read before implementing):
- `testing/terminology.md` -- the terminology testing-vision memo (naming
  conventions, forbidden synonyms, contract strings, 5-site vocabulary).
- `testing/TESTING_VISION.md` -- gates 13-15 (terminology gates).
- This document is the concrete task list that satisfies those gates.

---

## Overview

Four work areas, each producing one test artifact:

| # | Work area | Output artifact | Gate |
|---|---|---|---|
| 1 | Naming-convention lint | `tests/test_terminology_lint.py` | Gate 13 |
| 2 | Contract-string assertions | Parametrized cases in per-component test files | Gate 14 |
| 3 | Forbidden-synonym lint | `tests/test_terminology_lint.py` (same file) | Gate 13 + 14 |
| 4 | Five-site vocabulary | `tests/test_constraints_block.py` (D5 tests) | Gate 15 |

---

## 1. Test naming convention enforcement

### 1.1 What to enforce

Every test name in the abast_accf332_sync test files must:

1. Start with `test_`.
2. Carry a component coordinate: the second token after `test_` must match
   `[a-f][0-9]*` (component letter A-F, optional sub-unit digit).
3. Map to a known component letter (`a`, `b`, `c`, `d`, `e`, `f`).
4. Not use any forbidden synonym (see §3).

### 1.2 Test file scope

The lint applies to these files (the abast_accf332_sync test surface):

```
tests/test_workflow_engine_seam.py      # A
tests/test_agent_role_identity.py       # B  (NEW)
tests/test_effort_cycling.py            # C  (NEW)
tests/test_constraints_block.py         # D  (NEW)
tests/test_mcp_agent_info.py            # D  (NEW)
tests/test_global_rules.py              # E  (existing or NEW)
tests/test_computer_info_modal.py       # F  (NEW)
```

Tests in `test_app.py`, `test_widgets.py`, `test_app_ui.py` etc. are
**not** in scope for the naming lint (they predate this run).

### 1.3 Implementation: `tests/test_terminology_lint.py`

```python
# tests/test_terminology_lint.py
"""
Terminology lint for the abast_accf332_sync test surface.

Gate 13 (TESTING_VISION.md): Every test maps to a SPEC component letter.
Gate 14 sub-rule: No forbidden synonyms in test names or docstrings.
"""

import ast
import re
from pathlib import Path

import pytest

# Files in scope for the naming lint
IN_SCOPE_FILES = [
    "tests/test_workflow_engine_seam.py",
    "tests/test_agent_role_identity.py",
    "tests/test_effort_cycling.py",
    "tests/test_constraints_block.py",
    "tests/test_mcp_agent_info.py",
    "tests/test_global_rules.py",
    "tests/test_computer_info_modal.py",
]

# Pattern: test_<component_letter><optional_digit(s)>_<rest>
NAME_PATTERN = re.compile(r"^test_([a-f][0-9]*)_[a-z]")

VALID_LETTERS = set("abcdef")

# Forbidden substrings in test *names* (not production imports)
FORBIDDEN_IN_NAMES = [
    "role_promotes",       # must be agent_type_promotes
    "compute_budget",      # must be effort
    "thinking_budget",     # must be effort
    "kickoff",             # must be spawn or activation
    "diagnostics_modal",   # must be computer_info_modal
    "workflow_root_identifier",  # must be project_root_identifier
    "get_phase_returns_rules",   # post-narrowing forbidden
    "three_inject_sites",  # stale count
    "four_inject_sites",   # stale count
    "postcompact_",        # mixed-case; must be post_compact_
]

# Forbidden substrings in test *docstrings and inline comments*
FORBIDDEN_IN_PROSE = [
    r"\bthinking\b",       # must be effort
    r"\bkickoff\b",        # must be spawn or activation
    r"the four inject sites",
    r"the three inject sites",
    r"DiagnosticsModal",   # must be ComputerInfoModal
    r"\bmax=high\b",       # stale Opus phrasing
    # Note: accf332 / 8f99f03 / 2f6ba2e / a60e3fe sha references are allowed
    # in comments that specifically discuss cherry-pick artifacts (Rule 2.3
    # allows them; the prohibition is on *non-cherry-pick* prose).
]


def _collect_test_functions(path: Path):
    """Parse a Python source file and return all test function AST nodes."""
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    ]


def _get_docstring(node) -> str:
    """Return the docstring of a function node, or empty string."""
    if (
        node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
        and isinstance(node.body[0].value.value, str)
    ):
        return node.body[0].value.value
    return ""


@pytest.mark.parametrize("rel_path", IN_SCOPE_FILES)
def test_terminology_lint_naming_pattern(rel_path):
    """Gate 13: every test in scope maps to a SPEC component letter.

    Test names must match test_<letter><digit(s)>_<concept>_<expectation>.
    """
    path = Path(rel_path)
    if not path.exists():
        pytest.skip(f"{rel_path} does not exist yet")

    bad = []
    for node in _collect_test_functions(path):
        if not NAME_PATTERN.match(node.name):
            bad.append(node.name)

    assert not bad, (
        f"{rel_path}: test names do not carry a SPEC component coordinate:\n"
        + "\n".join(f"  {n}" for n in bad)
        + "\nExpected pattern: test_<letter><digit(s)>_<concept>_<expectation>"
        + "\nExample: test_b3_agent_type_promotes_to_main_role_on_activation"
    )


@pytest.mark.parametrize("rel_path", IN_SCOPE_FILES)
def test_terminology_lint_no_forbidden_name_fragments(rel_path):
    """Gate 13 + 14: no forbidden synonyms appear in test function names."""
    path = Path(rel_path)
    if not path.exists():
        pytest.skip(f"{rel_path} does not exist yet")

    bad = []
    for node in _collect_test_functions(path):
        for fragment in FORBIDDEN_IN_NAMES:
            if fragment in node.name:
                bad.append((node.name, fragment))

    assert not bad, (
        f"{rel_path}: forbidden synonym fragment in test names:\n"
        + "\n".join(f"  {name!r} contains {frag!r}" for name, frag in bad)
    )


@pytest.mark.parametrize("rel_path", IN_SCOPE_FILES)
def test_terminology_lint_no_forbidden_prose(rel_path):
    """Gate 14: no forbidden synonyms in test docstrings or inline comments."""
    path = Path(rel_path)
    if not path.exists():
        pytest.skip(f"{rel_path} does not exist yet")

    source = path.read_text(encoding="utf-8")
    hits = []
    for pattern in FORBIDDEN_IN_PROSE:
        for i, line in enumerate(source.splitlines(), start=1):
            # Only match in comments and string literals (not production imports)
            stripped = line.lstrip()
            if stripped.startswith("#") or stripped.startswith(('"""', "'''")):
                if re.search(pattern, line, re.IGNORECASE):
                    hits.append((i, pattern, line.rstrip()))

    assert not hits, (
        f"{rel_path}: forbidden synonym in test prose:\n"
        + "\n".join(f"  line {i}: {pat!r} matched: {line!r}" for i, pat, line in hits)
    )
```

### 1.4 Required test names (from `testing/terminology.md` §1.1 + §4)

The naming-convention lint verifies the *pattern*. These specific names are
the REQUIRED test names the test-axis agents must use:

**Component B (test_agent_role_identity.py)**

| Test purpose | Required test name |
|---|---|
| agent_type defaults to DEFAULT_ROLE | `test_b2_agent_type_defaults_to_default_role` |
| promotion on activation | `test_b3_agent_type_promotes_to_main_role_on_activation` |
| revert on deactivation | `test_b3_agent_type_reverts_to_default_role_on_deactivation` |
| hook closure reads live agent_type | `test_b4_guardrail_hook_reads_agent_type_live` |
| B5 loader rejects main_role=default | `test_b5_loader_rejects_manifest_with_main_role_equal_to_default` |

**Component C (test_effort_cycling.py)**

| Test purpose | Required test name |
|---|---|
| effort passed to ClaudeAgentOptions | `test_c1_effort_passed_to_claude_agent_options` |
| EffortLabel cycles low/medium/high/max | `test_c2_effort_label_cycles_low_medium_high_max` |
| non-Opus snap to medium | `test_c2_effort_snaps_to_medium_on_non_opus_model` |
| persistence to config yaml | `test_c3_effort_persists_to_config_yaml` |

**Component D (test_constraints_block.py, test_mcp_agent_info.py)**

| Test purpose | Required test name |
|---|---|
| constraints block includes role/phase scoped rules | `test_d3_assemble_constraints_block_includes_role_phase_scoped_rules` |
| get_agent_info returns 8-section markdown | `test_d4_get_agent_info_returns_eight_section_markdown` |
| activation site routes through helper | `test_d5_activation_routes_through_assemble_agent_prompt` |
| spawn site routes through helper | `test_d5_spawn_routes_through_assemble_agent_prompt` |
| phase-advance site routes through helper | `test_d5_phase_advance_routes_through_assemble_agent_prompt` |
| broadcast site reaches other agents | `test_d5_broadcast_delivers_to_other_agents` |
| post-compact site re-injects on /compact | `test_d5_post_compact_reinjects_constraints_block` |

**Component E (test_global_rules.py)**

| Test purpose | Required test name |
|---|---|
| warn fires on bare pytest run | `test_e_pytest_needs_timeout_warn_fires_on_bare_pytest_run` |
| no false positive on grep/cat/doc | `test_e_pytest_needs_timeout_no_false_positive_on_grep_cat_doc` |

**Component F (test_computer_info_modal.py)**

| Test purpose | Required test name |
|---|---|
| modal renders session JSONL path | `test_f_computer_info_modal_renders_session_jsonl_path` |
| modal renders last compaction section | `test_f_computer_info_modal_renders_last_compaction_section` |

---

## 2. Contract-string assertions

A contract string is a literal that crosses the runtime boundary -- it is
either visible to users on screen or consumed by the model in prompts.
Production code generates it; a regression that changes it silently breaks
downstream consumers. Tests MUST assert on the EXACT literal.

### 2.1 Locked contract strings

The following strings are locked for this run. Test assertions must use
these exact bytes, including capitalization, spacing, and punctuation.

#### EffortLabel display strings (Component C)

Source of truth: `claudechic/widgets/layout/footer.py::EffortLabel.EFFORT_DISPLAY`

```python
# REQUIRED assertions in test_effort_cycling.py
assert label.renderable == "effort: low"
assert label.renderable == "effort: medium"
assert label.renderable == "effort: high"
assert label.renderable == "effort: max"      # Opus only
```

**Forbidden paraphrases:**
- `"thinking: high"` -- wrong prefix
- `"high"` alone -- incomplete; passes if prefix changes
- `"budget: low"` -- wrong prefix

Tests must import `EffortLabel.EFFORT_DISPLAY` and assert against its values
rather than redefining the dict locally.

#### Constraints block headings (Component D)

Source of truth: `claudechic/workflows/agent_folders.py::assemble_constraints_block`

```python
# REQUIRED assertions in test_constraints_block.py
assert block.startswith("## Constraints")
assert "### Rules (" in block           # followed by "{n_active} active)"
assert "### Advance checks (" in block  # followed by "{phase})"
```

**Forbidden paraphrases:**
- `"# Constraints"` -- wrong heading level
- `"## Rules"` -- missing "Constraints" parent
- `"rules:"` -- not the section heading

#### get_agent_info section headings (Component D)

Source of truth: `claudechic/mcp.py::_make_get_agent_info`
Reference: SPEC lines 359-368 (8-section structure).

```python
# REQUIRED assertions in test_mcp_agent_info.py
assert "## Identity" in agent_info
assert "## Session" in agent_info
assert "## Active workflow + phase" in agent_info
assert "## Applicable guardrail rules" in agent_info   # NOT "## Rules"
assert "## Applicable injections" in agent_info
assert "## Advance checks for the current phase" in agent_info
assert "## Loader errors" in agent_info
# The overall block has an h1 header:
assert agent_info.startswith("# Agent")  # or contains it at top
```

**Forbidden paraphrases:**
- `"## Rules"` -- must be `"## Applicable guardrail rules"`
- `"## Checks"` -- must be `"## Advance checks for the current phase"`
- `"## Workflow"` -- must be `"## Active workflow + phase"`

#### Environment variable names (Component B)

Source of truth: `claudechic/app.py::_make_options` (CLAUDE_AGENT_ROLE wiring)

```python
# REQUIRED assertions in test_agent_role_identity.py
assert env["CLAUDE_AGENT_ROLE"] == agent.agent_type
assert "CLAUDE_AGENT_NAME" in env
assert "CLAUDECHIC_APP_PID" in env
```

**Forbidden:**
- `env["AGENT_ROLE"]` -- missing CLAUDE_ prefix
- `env["CLAUDE_ROLE"]` -- missing AGENT_
- `env["ROLE"]` -- entirely wrong

#### Template variable tokens (Component A)

Source of truth: `claudechic/workflows/engine.py` + `claudechic/workflows/_substitute.py`

```python
# REQUIRED assertions in test_workflow_engine_seam.py
assert "${WORKFLOW_ROOT}" in raw_yaml              # braced
assert "${CLAUDECHIC_ARTIFACT_DIR}" in raw_yaml    # braced
```

**Forbidden:**
- `"$WORKFLOW_ROOT"` -- bare; not the convergence target
- `"${PROJECT_ROOT}"` -- PROJECT_ROOT is the Python identifier, not the YAML token

#### MCP tool names (Component D)

Source of truth: `claudechic/mcp.py::create_chic_server`

```python
# REQUIRED assertions in test_mcp_agent_info.py or test_constraints_block.py
assert "mcp__chic__whoami" in registered_tools
assert "mcp__chic__get_phase" in registered_tools
assert "mcp__chic__get_applicable_rules" in registered_tools
assert "mcp__chic__get_agent_info" in registered_tools
```

**Forbidden:**
- `"mcp__chic__get_rules"` -- not the canonical name
- `"mcp__chic__agent_info"` -- missing get_ prefix
- `"mcp__chic__constraints"` -- does not exist

#### DEFAULT_ROLE sentinel (Component B)

Source of truth: `claudechic/agent.py::DEFAULT_ROLE`

```python
# REQUIRED pattern in test_agent_role_identity.py
from claudechic.agent import DEFAULT_ROLE
assert DEFAULT_ROLE == "default"
assert agent.agent_type == DEFAULT_ROLE
```

**Forbidden:**
- `assert agent.agent_type == "default"` -- bypasses the sentinel; if the
  value changes, the test still passes silently
- `assert agent.agent_type is None` -- pre-B1 shape; should fail post-B1

#### pytest_needs_timeout rule strings (Component E)

Source of truth: `claudechic/defaults/global/rules.yaml`

```python
# REQUIRED assertions in test_global_rules.py
rule_ids = {r.id for r in loaded_rules}
assert "pytest_needs_timeout" in rule_ids

rule = next(r for r in loaded_rules if r.id == "pytest_needs_timeout")
assert rule.enforcement == "warn"
assert rule.message == "use --timeout=N (default 30) to avoid hung tests"
```

The message string is lowercase with no terminal period. Assert verbatim.

### 2.2 Parametrized contract-string test design

For contract strings that have multiple values (EffortLabel display strings,
inject-site names), use `pytest.mark.parametrize` rather than repeating
similar assertions:

```python
# Example for EffortLabel -- test_effort_cycling.py
@pytest.mark.parametrize("level,expected", [
    ("low",    "effort: low"),
    ("medium", "effort: medium"),
    ("high",   "effort: high"),
    ("max",    "effort: max"),
])
def test_c2_effort_display_string_matches_level(level, expected):
    """C2: EffortLabel.EFFORT_DISPLAY maps each level to exact display text."""
    from claudechic.widgets.layout.footer import EffortLabel
    assert EffortLabel.EFFORT_DISPLAY[level] == expected
```

```python
# Example for get_agent_info sections -- test_mcp_agent_info.py
REQUIRED_SECTIONS = [
    "## Identity",
    "## Session",
    "## Active workflow + phase",
    "## Applicable guardrail rules",
    "## Applicable injections",
    "## Advance checks for the current phase",
    "## Loader errors",
]

@pytest.mark.parametrize("heading", REQUIRED_SECTIONS)
def test_d4_get_agent_info_contains_section(heading, mock_agent_info_context):
    """D4: get_agent_info output contains all 8 section headings verbatim."""
    result = call_get_agent_info(mock_agent_info_context)
    assert heading in result, (
        f"get_agent_info output missing section heading {heading!r}"
    )
```

---

## 3. Forbidden-synonym lint

### 3.1 Grep-based test (in test_terminology_lint.py)

This is a separate test from the AST-based lint in §1.3. It uses raw
text search over the in-scope test files and catches synonyms that
appear anywhere in the file (in parametrize argument lists, in
string fixtures, in assert messages, etc.).

```python
# Additional tests to add to tests/test_terminology_lint.py

# Patterns that must have ZERO matches in any in-scope test file.
# Each tuple: (pattern, reason, files_to_check)
GREP_FORBIDDEN = [
    # Test name fragments (also caught by AST lint, but belt-and-suspenders)
    (r"def test_role_promotes", "must be test_agent_type_promotes"),
    (r"def test_compute_budget", "must be test_effort"),
    (r"def test_thinking_budget", "must be test_effort"),
    (r"def test_kickoff", "must be test_spawn or test_activation"),
    (r"def test_diagnostics_modal", "must be test_computer_info_modal"),
    # Prose in assertions and docstrings
    (r"DiagnosticsModal", "replaced by ComputerInfoModal; assert on the new class"),
    (r"GuardrailsLabel", "not part of the reframed D surface; do not assert on it"),
    (r'"thinking"', "effort label is 'effort: <level>', not 'thinking'"),
    (r"'thinking'", "effort label is 'effort: <level>', not 'thinking'"),
    (r"four inject sites", "SPEC Decision 4 locks FIVE inject sites"),
    (r"three inject sites", "SPEC Decision 4 locks FIVE inject sites"),
    (r'"kickoff"', "overloaded; use 'spawn' or 'activation'"),
    # Stale snap target (non-Opus was updated from high to medium in SPEC)
    (r"snaps.*to.*high", "non-Opus snap target is 'medium', not 'high'"),
    (r"snap.*medium.*high", "non-Opus snap target is 'medium', not 'high'"),
]


@pytest.mark.parametrize("pattern,reason", [(p, r) for p, r, *_ in GREP_FORBIDDEN])
@pytest.mark.parametrize("rel_path", IN_SCOPE_FILES)
def test_terminology_lint_no_forbidden_grep_pattern(rel_path, pattern, reason):
    """Gate 14: no forbidden synonym patterns appear anywhere in test files."""
    path = Path(rel_path)
    if not path.exists():
        pytest.skip(f"{rel_path} does not exist yet")

    source = path.read_text(encoding="utf-8")
    import re as _re
    matches = [
        (i + 1, line.rstrip())
        for i, line in enumerate(source.splitlines())
        if _re.search(pattern, line)
    ]
    assert not matches, (
        f"{rel_path}: forbidden synonym pattern {pattern!r} ({reason}):\n"
        + "\n".join(f"  line {i}: {line}" for i, line in matches)
    )
```

### 3.2 Manual newcomer grep (run before merge)

Per `testing/terminology.md` §6, before merging any test file run:

```bash
rg -i 'thinking|kickoff|workflow_root\b|DiagnosticsModal' \
    tests/test_agent_role_identity.py \
    tests/test_effort_cycling.py \
    tests/test_constraints_block.py \
    tests/test_mcp_agent_info.py \
    tests/test_global_rules.py \
    tests/test_computer_info_modal.py \
    tests/test_workflow_engine_seam.py
```

Expected output: no matches (exit code 1 from rg means no matches = pass).

Note: hits **inside** imported production code strings (e.g., a fixture
that calls `assemble_constraints_block` and inspects its return value) are
acceptable -- the prohibition is on test-side prose only.

---

## 4. Five-site vocabulary verification

SPEC Decision 4 locks five prompt-injection sites. Tests for sub-unit D5
must use the canonical site names and verify each site calls
`assemble_agent_prompt`.

### 4.1 Canonical site table

| # | Site name | Wired in | Code location |
|---|---|---|---|
| 1 | **activation** | `app.py::_activate_workflow` | inline `assemble_agent_prompt` call |
| 2 | **spawn** | `mcp.py::_make_spawn_agent` | `spawn_agent` MCP tool |
| 3 | **phase-advance** | `app.py::_inject_phase_prompt_to_main_agent` | called from `advance_phase` MCP tool |
| 4 | **broadcast** | `mcp.py::_make_advance_phase` (~line 986-1000) | broadcast loop on phase advance |
| 5 | **post-compact** | `agent_folders.py::create_post_compact_hook` | SDK PostCompact hook |

### 4.2 Required test names for D5

From `testing/terminology.md` §4:

```
test_d5_activation_routes_through_assemble_agent_prompt
test_d5_spawn_routes_through_assemble_agent_prompt
test_d5_phase_advance_routes_through_assemble_agent_prompt
test_d5_broadcast_delivers_to_other_agents
test_d5_post_compact_reinjects_constraints_block
```

### 4.3 Broadcast site status (xfail marker required)

Per `testing/terminology.md` §7 and the TESTING_VISION Reading Guide: the
broadcast site (#4) is **not yet wired through `assemble_agent_prompt`**.
SPEC Decision 4 says 5 sites; production has 4 wired.

The test for the broadcast site MUST use:

```python
@pytest.mark.xfail(
    reason=(
        "broadcast site (#4 of 5) not yet wired through assemble_agent_prompt; "
        "tracked as follow-up per testing/terminology.md §7"
    ),
    strict=False,
)
def test_d5_broadcast_delivers_to_other_agents(...):
    ...
```

This keeps the test in the suite (it will appear as `xfail` or `xpass`
rather than a false-green skip) and documents the known gap explicitly.
Composability decides whether to wire it in this run or carry the xfail.

### 4.4 Site-name lint in test prose

The five-site vocabulary is also enforced by the grep lint in §3. To make
the enforcement complete, add the following patterns to `GREP_FORBIDDEN`:

```python
# (Already included in §3.1 table; repeated here for clarity)
(r"def test_kickoff", "overloaded; use spawn or activation"),
(r"def test_three_inject_sites", "stale count -- must be five"),
(r"def test_four_inject_sites",  "stale count -- must be five"),
(r"def test_postcompact_",       "must be test_post_compact_ (underscore)"),
```

### 4.5 Parametrized site-vocabulary assertion

To guard against silent count drift, add one meta-test that asserts the
five canonical site names appear in the D5 test file:

```python
# In test_terminology_lint.py (or test_constraints_block.py)

FIVE_SITE_NAMES = ["activation", "spawn", "phase-advance", "broadcast", "post-compact"]

def test_d5_five_site_names_all_present_in_test_file():
    """Gate 15: D5 test file uses all five canonical inject-site names."""
    path = Path("tests/test_constraints_block.py")
    if not path.exists():
        pytest.skip("test_constraints_block.py does not exist yet")
    source = path.read_text(encoding="utf-8")
    missing = [name for name in FIVE_SITE_NAMES if name not in source]
    assert not missing, (
        "test_constraints_block.py is missing canonical inject-site names:\n"
        + "\n".join(f"  {n!r}" for n in missing)
        + "\nAll five must appear: activation / spawn / phase-advance / "
        "broadcast / post-compact"
    )
```

---

## 5. Complete contract-string table (locked for this run)

This table is the single source of truth for Gate 14. Any test that asserts
a runtime string must assert on the EXACT value in the "Required literal"
column.

| Surface | Required literal | Source file | Asserted in |
|---|---|---|---|
| Effort footer low | `"effort: low"` | `widgets/layout/footer.py::EFFORT_DISPLAY` | `test_effort_cycling.py` |
| Effort footer medium | `"effort: medium"` | same | same |
| Effort footer high | `"effort: high"` | same | same |
| Effort footer max | `"effort: max"` | same | same |
| Constraints heading | `"## Constraints"` | `workflows/agent_folders.py` | `test_constraints_block.py` |
| Rules sub-heading | `"### Rules ("` | same | same |
| Advance checks sub-heading | `"### Advance checks ("` | same | same |
| Agent info identity | `"## Identity"` | `mcp.py` | `test_mcp_agent_info.py` |
| Agent info session | `"## Session"` | same | same |
| Agent info workflow | `"## Active workflow + phase"` | same | same |
| Agent info rules | `"## Applicable guardrail rules"` | same | same |
| Agent info injections | `"## Applicable injections"` | same | same |
| Agent info checks | `"## Advance checks for the current phase"` | same | same |
| Agent info errors | `"## Loader errors"` | same | same |
| Env var role | `"CLAUDE_AGENT_ROLE"` | `app.py::_make_options` | `test_agent_role_identity.py` |
| Env var name | `"CLAUDE_AGENT_NAME"` | same | same |
| Env var pid | `"CLAUDECHIC_APP_PID"` | same | same |
| YAML token root | `"${WORKFLOW_ROOT}"` | `workflows/engine.py` | `test_workflow_engine_seam.py` |
| YAML token artifact | `"${CLAUDECHIC_ARTIFACT_DIR}"` | `workflows/_substitute.py` | same |
| MCP tool whoami | `"mcp__chic__whoami"` | `mcp.py::create_chic_server` | `test_mcp_agent_info.py` |
| MCP tool get_phase | `"mcp__chic__get_phase"` | same | same |
| MCP tool get_applicable_rules | `"mcp__chic__get_applicable_rules"` | same | same |
| MCP tool get_agent_info | `"mcp__chic__get_agent_info"` | same | same |
| DEFAULT_ROLE value | `"default"` | `claudechic/agent.py::DEFAULT_ROLE` | `test_agent_role_identity.py` |
| Rule id E | `"pytest_needs_timeout"` | `defaults/global/rules.yaml` | `test_global_rules.py` |
| Rule message E | `"use --timeout=N (default 30) to avoid hung tests"` | same | same |
| Rule enforcement E | `"warn"` | same | same |
| PostCompact hook key | `"PostCompact"` | SDK proper noun | `test_constraints_block.py` |

---

## 6. Unresolved references and known gaps

These items are tracked but NOT blocking test-axis entry. They are handed
off to composability or the documentation phase.

### 6.1 Broadcast site wiring (known gap, xfail required)

`test_d5_broadcast_delivers_to_other_agents` will fail unless the broadcast
site is wired through `assemble_agent_prompt` in this run. Use the `xfail`
marker described in §4.3. Composability decides whether to wire it.

### 6.2 snap-to-medium comment in agent.py (stale, documentation-phase)

`claudechic/agent.py` line 251-252 still says "non-Opus models snap to
'high'". This was updated in the SPEC to "medium" but the comment was not
patched. The grep lint in §3.1 includes `snaps.*to.*high` -- if that
pattern appears in TEST FILES it fails, but production-code comments are
out of scope for the lint. Flag for the documentation phase.

### 6.3 Inject-site numbering in production comments (stale, documentation-phase)

Several comments in `app.py` and `mcp.py` still refer to the old 3-site or
4-site numbering ("D5 inject site #1", "#3", etc.). These are production
comments, not test prose; the terminology lint does not reach them. Flag for
the documentation phase.

### 6.4 DEFAULT_ROLE type annotation (documentation-phase)

`agent.py` declares `DEFAULT_ROLE: str = "default"`. The SPEC suggests
`Literal["default"]`. This is a type-annotation tightening, not a
behavioral change. The existing tests that import `DEFAULT_ROLE` and compare
with `==` will pass either way. Flag for the documentation phase.

### 6.5 active_wf vs active_workflow in compute_digest (cosmetic)

`claudechic/guardrails/digest.py::compute_digest` parameter is named
`active_wf`; the SPEC uses `active_workflow`. The inconsistency is cosmetic
and does not affect test assertions. Flag for documentation phase.

---

## 7. Sign-off checklist (terminology axis)

Before the terminology axis approves testing-implementation exit:

- [ ] `tests/test_terminology_lint.py` exists and all parametrized cases
      pass (or are appropriately skipped for not-yet-created files).
- [ ] All required test names from §1.4 are present in their respective
      files (check with `pytest --collect-only -q`).
- [ ] Every contract string in §5 is asserted verbatim in at least one
      test (cross-check by grep for the literal in the test files).
- [ ] The broadcast site test is present with the xfail marker; it does
      not show as a bare `FAILED` in the suite output.
- [ ] Manual newcomer grep (§3.2) returns no matches.
- [ ] No test file contains `"default"` as a bare string comparison for
      `agent.agent_type` (must import and compare via `DEFAULT_ROLE`).
- [ ] Gates 13, 14, and 15 from TESTING_VISION.md are all satisfied.

---

*End of terminology test plan.*
*Reply with unresolvable references or newly discovered contract strings
to TerminologyGuardian via message_agent before implementing test files.*
