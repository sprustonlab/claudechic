# Skeptic Testing-Vision Memo -- abast_accf332_sync

**Author:** Skeptic
**Date:** 2026-05-01
**Phase:** project-team:testing-vision
**Reviews:** SPEC.md (locked), per-slot implementation reviews 1-6,
b106cff (the landed commit).

This memo is the bar a test plan must clear, not the plan itself.
The team-level Testing Vision Summary (coordinator's draft) frames the
ambition; this memo names the falsification surface, the highest-cost
silent-failure modes, and the shortcuts I will reject in test design.

## TL;DR -- skeptic posture for testing-vision

The b106cff commit landed almost all the must-fixes my slot reviews
flagged. The remaining test-vision risk is NOT "did the implementer
follow the spec" -- the substrate is wired. The remaining risk is
**silent semantic divergence between the layers we now run in parallel**:
hooks vs MCP vs constraints block vs phase prompt -- four projections
of one rule set. Tests that pass each layer in isolation can pass while
the layers disagree. Cross-layer assertions are the highest-value test
shape this run.

## Q1-Q6 falsification questions, adapted for testing

Adapted from the v1 skeptic review's Q1-Q6 falsification matrix. Each
test the team writes should make at least one Q falsifiable.

| Q | Falsification target | Concrete test signal |
|---|---|---|
| Q1. Does the test cover the user's actual requirement? | Tests assert on the user-visible "before vs after" sentence in SPEC §X WHY (User). | E.g. SPEC §B WHY says "activating a workflow promotes the main agent to its role without an SDK reconnect" -- the test must NOT reconnect; assert `agent.client is the same object` before + after activation. |
| Q2. Does the test reveal contract breaks? | Inventory the new contract surface (DEFAULT_ROLE sentinel; `agent.effort` literal; `agent.agent_type: str`; `_LoaderAdapter`; new MCP tool names; SetTrigger surface for E). | E.g. `assert agent.agent_type is not None` (was `None` before). E.g. `Agent(name=..., cwd=...).effort in {"low","medium","high","max"}`. |
| Q3. Does the test depend on out-of-cluster commits? | If a test passes only because `003408a`'s `_resolve_against` is present, it's testing the dependency, not the cluster. | Cite the SHA the test exercises in the test docstring; reject vague "this checks the integration" framing. |
| Q4. Does the test prove a user-visible delta? | "I would notice this break" check. A regression in `compute_digest` filtering on disabled_rules causes the constraints block to advertise rules that hooks don't fire on -- the agent self-corrects on a non-existent rule. Concrete user notices: agent's behavior changes. | Test must assert observable agent behavior change, not just internal-state change. |
| Q5. Is the test simpler in-tree than its proxy? | The pytest-needs-timeout regex test should NOT mock the hook pipeline; it should run the regex directly against ~44 strings (the set I built in the slot 6 review). | Pure-function tests beat integration tests when the function is pure. |
| Q6. Does the test guard against regressions in adjacent code? | A change to `_filter_load_result` (registry layer) should be caught by a test asserting `_LoaderAdapter().load() == _filter_load_result(loader.load(), config)`. | Pin the source-of-truth alignment with one assertion. |

## Must-fix items deferred / verified-fixed in b106cff

Status of the 6 must-fix items I flagged across slot reviews:

| Slot | Must-fix | Status in b106cff | Test required |
|---|---|---|---|
| 1 | mcp.py:983 falsy-check on agent.agent_type | FIXED (uses `== DEFAULT_ROLE`) | Activate workflow, advance_phase, assert default-roled agent NOT broadcast-to. |
| 1 | `test_agent_type_defaults_to_none` regression | FIXED (renamed + asserts DEFAULT_ROLE) | Already in suite. |
| 3 | advance_phase broadcast asymmetry (sub-agents miss constraints) | FIXED (D5 inject site #5 routes via `assemble_agent_prompt`) | Spawn sub-agent in workflow; advance phase; assert broadcast prompt contains `## Constraints`. |
| 4 | mcp.py disabled_rules unwired | FIXED (`parse_disable_entries` + `_get_disabled_rules` at 4 sites) | Set `disabled_ids: ["global:no_rm_rf"]` in project config; call `get_applicable_rules`; assert `no_rm_rf` is excluded from active rules AND that hooks also don't fire on it. |
| 5 | F session_id unwired at footer click | FIXED (`session_id=session_id` passed to ComputerInfoModal) | Open modal with active session; assert Session JSONL row reads the actual JSONL path. |
| 5 | EffortLabel snap-on-model-change unwired | FIXED (`watch_model` calls `set_available_levels`) | Set effort=max on Opus; switch model to Sonnet; assert `agent.effort == "medium"`. |
| 6 | CLAUDE.md inconsistent with new pytest_needs_timeout rule | FIXED (`pytest tests/... -v --timeout=30` everywhere in CLAUDE.md) | Run regex against the 5 documented forms in CLAUDE.md; assert no match. |
| 5 | Two buttons -> same modal | FIXED (`ComputerInfoLabel` removed from footer) | Test the single InfoLabel renders + click opens modal. |

## Items NOT covered by the existing test suite (regression-risk items)

Even after b106cff's fixes, these pieces could regress silently:

1. **Empty-digest case** (slot 2 S1 / v2-8): `assemble_constraints_block` still emits 138 chars on the empty-rules empty-checks path. The token cost is bounded but the helper has dead-code in `assemble_agent_prompt` (the `if not constraints.strip()` guard never fires). Test: assert `assemble_constraints_block(loader=None, role='default', phase=None)` returns a single-line "no constraints" sentinel OR that no inject site emits the placeholder text into a real prompt.

2. **B5 case-insensitive rejection** (slot 2 S2, fixed in slot 4): one test per `Default`, `DEFAULT`, ` default `, `default\n`. Otherwise a future contributor "simplifies" the validator back to `==` and silently regresses.

3. **B3+B4 mid-session role flip** (slot 4 O2): closure-binding bugs pass code review. Live remote-control test required: activate -> assert env+hook see new role; deactivate -> assert env+hook see DEFAULT_ROLE; /compact -> assert role survives.

4. **Source-of-truth alignment between hooks and MCP** (Slot 4 docstring claim): a regression in `_LoaderAdapter` (e.g. fallback path returning unfiltered result) silently restores the bug class. Test: disable a rule; assert hooks AND `get_applicable_rules` AND constraints block ALL omit it.

5. **`assemble_agent_prompt` returns `None` for default-roled agents (no role dir)** (slot 2 S4 unresolved): SPEC §D says "every agent's launch prompt"; impl says "every agent with a role dir." Test: spawn a default-roled sub-agent; assert it gets ZERO constraints injection (current behavior) AND that this is the documented decision.

## Failure-cost matrix

What breaks if X silently regresses:

| Silent regression | User-visible | Agent-visible | Cost |
|---|---|---|---|
| Constraints block contradicts hooks | Agent self-corrects on a rule that doesn't fire (or vice versa); user sees confusing agent behavior | Agent's `## Constraints` block is wrong | **HIGH** -- erodes agent trust in the substrate. |
| `agent.agent_type` doesn't flip on activation | Workflow's role-scoped rules silently don't apply to main agent | Main agent claims to be `default` after activation | **HIGH** -- the entire B/D substrate becomes inert. |
| `effort=max` on non-Opus | SDK rejects (?) or behavior undefined | Agent thinks it's running max-effort but isn't | **MEDIUM** -- per-turn correctness; user sees latency or cost surprise. |
| pytest_needs_timeout false-positive | Warn fires on documented commands | Agent learns to ignore warns | **HIGH** -- trains the agent to ignore the entire warn channel. |
| `${WORKFLOW_ROOT}` left unsubstituted in prompt | Agent reads literal `${WORKFLOW_ROOT}/foo` and tries to resolve it as a path | Agent action fails with confusing error | **MEDIUM** -- recoverable but surprising. |
| F modal "session_id missing" | User clicks "info" sees `(no active session)` despite an active session | n/a | **LOW** -- read-only view; cosmetic confusion. |
| advance_phase broadcast misses constraints | Sub-agents on phase advance lack the rules that apply to the new phase | Sub-agents work without their role+phase scoped guardrails | **HIGH** -- partial-substrate failure. |

The HIGH-cost items are where I want belt-and-suspenders testing.

## Composition combinations most likely to expose bugs

The substrate has 4 axes that compose: workflow active/inactive,
agent role (default vs main_role vs sub-agent role), model family
(opus/sonnet/haiku), and disabled_ids state (empty / has-id / has-tier-id).
2 x 3 x 3 x 3 = 54 combinations -- not all are interesting.

**Highest-yield combinations** (likely to expose composition bugs):

1. **(workflow active, role=main_role, model=opus, disabled_ids has bare `global:X`)** -- exercises B activation + D disabled-rules-filtering + C max-eligible. Most layered combination.
2. **(workflow active, role=DEFAULT_ROLE before promotion, model=sonnet, disabled_ids has `<tier>:X`)** -- exercises the deactivation revert path + tier-prefix parsing.
3. **(workflow inactive, role=DEFAULT_ROLE, model=opus, disabled_ids empty)** -- the no-workflow baseline. Test that `get_agent_info` returns sensible content for a "fresh new agent in no workflow."
4. **(workflow active, sub-agent with explicit role, model=opus, disabled_ids has both bare + tier)** -- exercises the broadcast + spawn-time constraints injection paths simultaneously.
5. **(workflow active, mid-session model switch from opus to sonnet, effort=max)** -- the C snap path. (Already covered above.)
6. **(workflow active, /compact called, role=main_role, disabled_ids has tier-prefixed rule)** -- the post-compact re-injection path with filtered rules.

## Specific shortcuts I will reject in the test suite

1. **"The test mocks `assemble_agent_prompt` and asserts it gets called"** -- not a test, a tautology. Mock the SDK boundary, not the helper under test.
2. **"The test passes `disabled_rules=set()` and asserts the unfiltered path works"** -- doesn't test the filter. The whole point is the filter; tests must set non-default values and verify the filter applies (red flag from my own playbook: "Tests pass with default values").
3. **"The test runs the regex against the implementer's 22 cases"** -- circular. Tests must include cases the IMPLEMENTER didn't think of (use my 44-case set from the slot 6 review).
4. **"The test asserts `get_phase` returns the same shape as before"** -- it doesn't; `get_phase` was narrowed. Tests asserting on the old shape are testing the regression. Update or delete.
5. **"The test simulates a workflow with one rule and one phase"** -- toy data hides composition bugs. Use a real bundled workflow (e.g. `project_team`) with its actual rules + phases.
6. **"Integration test that uses an in-process AgentManager and bypasses the SDK"** -- doesn't test the SDK seam. The B4 closure-binding bug class lives in the SDK call; the test must exercise `agent.connect()` or the equivalent options-factory path.
7. **"Test the constraints block by stringly-asserting the markdown"** -- table format may shift; the assertion would over-fit. Assert structurally: section headers exist, rows include expected rule IDs.

## Pre-existing flakes to track-but-not-fix this run

These flakes are unrelated to abast_accf332_sync's substrate; tracking
them helps identify post-merge regressions but they don't block sign-off:

- `test_agent_switch_keybinding` -- intermittent on async race in agent-switch hook. Pre-dates this work; surfaced in `a743423` era.
- The 4 pre-existing `test_workflow_*.py` failures noted by impl_guardrails_and_mcp ("4 fail on the deprecated rule-count line in get_phase output"). These need disposition: either update the assertions (rule-count line is gone by design) or roll back the `get_phase` narrowing if Decision 5 changes. **Pick one and document.**
- Windows-only flakes addressed by `a2c3779`, `fd42c3c`, `3ac11b2` -- these are pre-existing and orthogonal.
- The `no_bare_pytest` regex still false-positives on `grep -c "pytest"` (verified in slot 6 review). Fixing it is out-of-scope for this run; track for follow-up.

## Cross-axis coordination notes

- **Composability overlap**: their axis owns "do the parts compose without surprise." My HIGH-cost composition combinations (above) are useful inputs to their composition matrix.
- **UserAlignment overlap**: their axis owns "is this what the user asked for." My Q1 falsification (asserting on the user-visible "before vs after" sentence) is the testable form of their UserAlignment check.
- I did NOT wait for their memos. Submitting this in parallel.

## Sign-off bar (binding for testing-vision)

A test plan that satisfies my bar:

- One test per HIGH-cost silent-regression item in the failure-cost matrix.
- One cross-layer assertion that pins source-of-truth alignment (`_LoaderAdapter` ≡ `_filter_load_result(loader.load(), config)`).
- The 44-case regex test set for E (reusable as `tests/test_pytest_needs_timeout_regex.py`).
- A live remote-control session for B3+B4 mid-session role flip (the closure-binding bug class).
- Explicit disposition on the 4 pre-existing `get_phase` test failures.
- No tests that pass with default values (red flag); every test sets non-default state and verifies it reaches the service layer.

A test plan that fails my bar:

- Tests on individual layers in isolation with no cross-layer assertion.
- Tests that re-use the implementer's case set without adding skeptic edge cases.
- "Smoke tests pass" without naming what the smoke test actually exercises end-to-end.
- Mocks at the helper boundary that hide closure-binding bugs.

---

*End of skeptic testing-vision memo. Reporting completion to coordinator
via message_agent.*
