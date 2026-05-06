# Composability axis -- Testing Vision

**Author:** Composability (Lead Architect)
**Phase:** project-team:testing-vision
**Date:** 2026-05-01
**Cluster:** abast `accf332` + `8f99f03` + `2f6ba2e` + `a60e3fe` (impl commit `b106cff`)
**Frames into:** Coordinator's Testing Vision Summary (success criteria 1-6).

This memo extends the team-level success criteria with the **composability
angle**: seam-protocol tests, orthogonality crystal-point sweeps, axis
isolation, and the "what breaks composition" assertions that turn
composability smells into executable invariants.

It does NOT enumerate test files, fixtures, or pytest names -- that's
testing-specification's job. Here we name the invariants that any test
strategy must verify, regardless of framework.

---

## 1. Compositional law for this work (the contract every test rides on)

The implementation collapses to **ONE composition contract**:

```python
assemble_agent_prompt(
    role: str,
    phase: str | None,
    loader: ManifestLoader | None,
    *,
    workflow_dir: Path | None,
    artifact_dir: Path | None,
    project_root: Path | None,
    engine: WorkflowEngine | None,
    active_workflow: str | None,
    disabled_rules: frozenset[str] | None,
) -> str | None
```

Every prompt-injection site goes through this helper. Every per-agent rule
projection goes through `assemble_constraints_block`, which `assemble_agent_prompt`
internally composes with `assemble_phase_prompt` to produce the final body.

If this single law holds, the M^N space of (5 inject sites × 4 effort
levels × N rules × N agents × ...) collapses into:

- "Does each axis produce/consume the right shape?"
- "Does every inject site call the helper instead of concat-by-hand?"
- "Does every rule-projection caller go through `assemble_constraints_block`?"

Those three questions are the spine of the composability testing strategy.

---

## 2. Seam-protocol tests (per axis pair)

The implementation defines clean seams between the six components. Each
seam needs a small, focused protocol test -- not a combinatorial sweep.

### 2.1. B ↔ A (workflow engine reads `agent.agent_type` via closure)

**Seam shape:** `_guardrail_hooks(agent=)` builds `lambda: agent.agent_type`;
the workflow engine and its hook closure read role state through that
lambda on every fire.

**Protocol test:**
- Construct an Agent with `agent_type="coordinator"`.
- Build the hook closure via `_guardrail_hooks(agent=agent)`.
- Mutate `agent.agent_type = "skeptic"`.
- Re-fire the hook -- assert the role-scoped rule filter sees `"skeptic"`,
  not `"coordinator"`.
- **No SDK reconnect.** That's the point.

**What this prevents:** snapshot-binding regressions where some refactor
captures `agent.agent_type` at hook-creation time instead of via the
lambda. The composability smell would be `effective_role = agent.agent_type`
(snapshot) instead of `effective_role = lambda: agent.agent_type` (live read).

### 2.2. C ↔ B (both flow through `_make_options(agent=)`)

**Seam shape:** `_make_options(agent=...)` reads BOTH `agent.agent_type` and
`agent.effort` live; the SDK options pick up the values at every connect.

**Protocol test:**
- Mutate `agent.effort = "max"` and `agent.agent_type = "coordinator"`.
- Call `_make_options(agent=agent)` -- assert the returned `ClaudeAgentOptions`
  has `effort="max"` and `env["CLAUDE_AGENT_ROLE"] == "coordinator"`.
- Mutate again, call again, assert the new values flow.

**What this prevents:** divergence between `agent_type=` kwarg (legacy) and
`agent=` (live). After cleanup, `agent_type=` becomes redundant. Test should
pin: when `agent=` is provided, the live read wins; the kwarg-only path
still works for sub-agent legacy callers.

### 2.3. D-projection ↔ D-render (`compute_digest` and `assemble_constraints_block`)

**Seam shape:** `compute_digest(loader, ...) -> list[GuardrailEntry]` is
data; `assemble_constraints_block` is the renderer; the seam is the
GuardrailEntry / AdvanceCheckEntry shape.

**Protocol test:**
- Stub `compute_digest` to return a known `[GuardrailEntry, ...]` list.
- Call `assemble_constraints_block` with that stub backing.
- Assert the markdown output has the expected `## Constraints` heading,
  `### Rules` table with the right columns, `### Advance checks` bullets.
- Repeat with `include_skipped=True` -- assert the `skip_reason` column
  appears.

**What this prevents:** drift between digest fields and renderer reads.
Today `assemble_constraints_block` uses `getattr(entry, "id", "")` defensively;
tests should pin the exact contract so a digest field rename doesn't
silently degrade to all-empty cells.

### 2.4. D-render ↔ D-inject (`assemble_agent_prompt` is the contract)

**Seam shape:** five inject sites must call `assemble_agent_prompt`.

**Protocol test:** static / lint-style assertion, not behavioral:
- Grep that the project contains exactly ONE concat of the form
  `f"{phase_prompt}\n\n{constraints_block}"` -- inside `assemble_agent_prompt`.
- Grep that the five inject sites all import and call `assemble_agent_prompt`
  (or its alias). No bare `assemble_phase_prompt` calls remain in inject
  context.

**What this prevents:** the single-composition-point invariant decaying
over time. Today all five sites route through the helper; a future
refactor could re-introduce a hand-rolled concat. A small AST or grep
test pins this.

### 2.5. D-mcp ↔ D-render (`get_applicable_rules` is a thin wrapper)

**Seam shape:** the MCP tool `get_applicable_rules` returns
`assemble_constraints_block(...)` verbatim. `get_agent_info` aggregator
delegates section 5 to `assemble_constraints_block` too.

**Protocol test:**
- Call `get_applicable_rules(agent_name="X")` -- capture markdown.
- Call `assemble_constraints_block(loader, role_of_X, phase, ...)` directly.
- Assert the two outputs are byte-identical (modulo whitespace).
- Same for `get_agent_info`'s section 5: extract it from the aggregator's
  output, assert it equals the standalone helper's output.

**What this prevents:** the slot 3 violation regressing -- aggregator
re-rendering rules in a different shape than `get_applicable_rules`.
Slot 4 fixed it; tests should pin the fix.

### 2.6. D6 source-of-truth (hook layer ↔ registry layer)

**Seam shape:** `_LoaderAdapter` exposes `.load()` returning the cached
`_load_result` (which is `_filter_load_result(raw_loader.load())`). The
hook layer reads through the adapter.

**Protocol test:**
- Disable a rule by id via project config (`disabled_ids: [my_rule]`).
- Trigger the hook layer's `loader.load()` (via a tool call or directly).
- Assert `result.rules` does NOT contain `my_rule`.
- Trigger the registry layer's `loader.load()` via `get_phase` or
  `_app._load_result` directly.
- Assert the same: `my_rule` is absent.
- Both layers must agree on which rules are present.

**What this prevents:** the hook-vs-registry fork that D6 was designed
to close. If a refactor re-routes the hook layer through `self._manifest_loader`
directly (bypassing `_LoaderAdapter`), the test fails.

### 2.7. F seam (modal absorbs diagnostics)

**Seam shape:** `ComputerInfoModal` accepts `cwd=` AND `session_id=`;
slot 4's app handler now passes both.

**Protocol test:** push the modal with `session_id=agent.session_id` and
verify the JSONL path + last-compaction sections render with content.
This is the "zero info loss" gestalt SPEC §F promised.

---

## 3. Crystal-point sweep (10 representative configurations)

The full crystal for this work has these axes (illustrative, not all
equally interesting):

| Axis | Values |
|------|--------|
| workflow_active | yes / no |
| agent_kind | main / sub-agent |
| effort | low / medium / high / max |
| model_supports_max | opus / non-opus |
| rule_disabled | yes / no |
| post_compact | yes / no |

Cardinality 2 × 2 × 4 × 2 × 2 × 2 = **128**. Don't test all 128. Test
**10 representative points**:

1. `(workflow=no, main, high, opus, no_disable, no_compact)` -- baseline
   minimum: just the agent runs, no workflow, no constraints block.
2. `(workflow=yes, main, high, opus, no_disable, no_compact)` -- main agent
   gets activation kickoff with `## Constraints` block.
3. `(workflow=yes, main, max, opus, no_disable, no_compact)` -- effort=max
   reaches the SDK; `--effort max` in subprocess argv.
4. `(workflow=yes, main, max, sonnet, no_disable, no_compact)` -- model
   change snaps effort from "max" to "medium" per Decision 5.
5. `(workflow=yes, sub-agent, medium, opus, no_disable, no_compact)` --
   sub-agent spawn injects role-specific constraints block.
6. `(workflow=yes, main, high, opus, disable=my_rule, no_compact)` -- the
   disabled rule is absent from agent's constraints block AND the hook
   layer agrees (D6).
7. `(workflow=yes, main, high, opus, no_disable, post_compact)` -- after
   /compact, role + constraints block survive (no SDK reconnect, no
   role reset).
8. `(workflow=yes, sub-agent on phase-advance, medium, opus, no_disable,
   no_compact)` -- the FIFTH inject site (broadcast loop) fires with
   refreshed constraints for the new phase.
9. `(workflow=yes -> deactivate, main, high, opus, no_disable, no_compact)`
   -- after deactivation, agent.agent_type reverts to DEFAULT_ROLE; next
   hook fire sees no workflow scope.
10. `(workflow=yes, main, low, opus, no_disable, no_compact)` -- effort=low
    runs (rate-limit-conscious users); footer label reflects "effort: low".

**If all 10 work, the architecture composes.** If any one fails, the
composability rubric says: it's either a leaky seam (clean it) or wrong
decomposition (reconsider the axis).

These 10 points are the testing-vision goal; testing-specification turns
each into one or more concrete pytest cases.

---

## 4. Axis isolation tests (each axis testable without the others)

Composability mandates each axis be testable in isolation -- if you need
the full TUI to test the constraints block, the seam is dirty.

| Axis | Isolation test stance |
|------|------------------------|
| **B (agent_type)** | `Agent(name=..., cwd=...)` with no SDK, no app, no workflow. Assert `agent_type == DEFAULT_ROLE`. Mutate. No mocks needed. |
| **C (effort)** | Same: `Agent(...).effort == "high"`. Mutate. `EffortLabel.set_available_levels(("low","medium","high"))` snaps "max" -> "medium" without spawning an app. |
| **D-projection** | `compute_digest(stub_loader, "global", "coordinator", "specification", set())` -- pure function over a stub loader. No Agent, no app, no SDK. |
| **D-render** | `assemble_constraints_block(stub_loader, "role", "phase")` -- pure function, returns markdown string. |
| **D-inject** | `assemble_agent_prompt(role, phase, loader, workflow_dir=tmp_path, ...)` -- pure function, returns string. No SDK, no app. |
| **D-MCP** | `get_applicable_rules` and `get_agent_info` should be testable with a stub `_app` whose `_workflow_engine` and `_manifest_loader` are MagicMock-shaped. No SDK connect, no live agent. |
| **D6 adapter** | `_LoaderAdapter(get_load_result=lambda: my_stub).load()` returns the stub. No app, no engine. |
| **A1 substitution** | `substitute_workflow_root("foo${WORKFLOW_ROOT}/bar", Path("/tmp"))` -- pure function. |
| **A3 cwd default** | Verify `engine._run_single_check` setdefault behavior with a mock CheckDecl, no real subprocess. |
| **A4 two-pass** | Verify ordering: pass a list of check decls with mixed `manual-confirm`/auto types; assert auto checks fire first. |
| **E rule** | The regex itself is testable: feed it `pytest tests/foo.py` (matches), `grep -c "pytest"` (does NOT match), `pytest --timeout=30 tests/` (does NOT match), etc. |
| **F modal** | `ComputerInfoModal(cwd=..., session_id=...)` constructible without an app; assert sections list has the right shape. |

**Test that does NOT pass these isolation criteria** = a seam is dirty.
Either fix the seam, or accept the coupling and document it.

---

## 5. Composability invariants made executable (smells as assertions)

The composability rubric lists smells. Here they become executable
assertions in the testing-vision -- "this should never appear in the
codebase":

| Smell (rubric) | Executable invariant for this work |
|----------------|-------------------------------------|
| Axis-specific branches | Grep test: zero `if format == ...` / `if backend == ...` patterns; zero `if agent.agent_type == "coordinator"` outside resolver code |
| Cross-axis type checks | Grep test: zero `if isinstance(loader, _LoaderAdapter)` style branches in `guardrails/`. Adapter is duck-typed -- callers must not type-check it. |
| Profile branches | Grep test: zero `if effort == "max"` outside `EffortLabel`'s display logic. Effort is a parameter, not a code switch. |
| Untestable in isolation | Each module in §4 above has at least one test that runs without instantiating ChatApp |
| Special-case composition | Grep: zero `f"{phase_prompt}\n\n{constraints_block}"` outside `assemble_agent_prompt`. The helper IS the contract |
| Giant single file | `agent_folders.py` line count baseline -- if it grows past ~500, suggest split (informational, not failing) |
| Circular imports | `python -c "import claudechic"` passes from a clean interpreter; no module-level cycles |
| Missing abstraction layers | `assemble_constraints_block` does no I/O -- can be invoked with `loader=None` and produces a degenerate block. Test pins this. |
| UI-only operations | `compute_digest`, `assemble_constraints_block`, `assemble_agent_prompt` are all callable without spawning Textual or a TUI |

These are NOT all blocking gates; the giant-file and circular-import ones
are advisory health checks. The first five are real invariants whose
violation indicates a real composability regression.

---

## 6. What the team-level success criteria miss (composability angle)

Coordinator's frame already covers (1) suite passes, (2) B3+B4 mid-session
flip, (3) D5 sites fire, (4) E warn rule fires, (5) F info parity, (6) no
regressions. Composability adds:

- **(7) Seam-protocol tests for the six seams in §2.** Each seam either
  has a focused test or the seam is implicitly fine because both sides
  are pure data crossing it.
- **(8) The 10-point crystal sweep in §3.** If even one combination fails,
  that's a hole in the architecture -- not just a missing test case.
- **(9) Single-composition-point lint:** zero hand-rolled
  `f"{phase_prompt}\n\n{constraints_block}"` concats outside the helper.
- **(10) Source-of-truth lint:** zero `compute_digest(...)` or
  `compute_advance_checks_digest(...)` calls outside `assemble_constraints_block`,
  the inject sites, and the MCP tools. If anyone else starts calling
  these directly, they're forking the projection.

(7)-(10) are testing-vision adds; testing-specification turns them into
concrete tests.

---

## 7. Coordination notes (where my axis overlaps with others)

### With **Skeptic** (falsification angle)

Skeptic's "what could break, and how would we know?" overlaps heavily
with my "what's the seam, and what crosses it?" The natural division:

- **Skeptic owns:** Q1 (real problem solved?) Q4 (concrete user observable?),
  Q5 (cheaper alternative?), Q6 (negative-evidence framing).
- **Composability owns:** Q2 (real seam? clean?), Q3 (orthogonality?
  crystal complete?).

If we both flag the same invariant from different angles, that's a strong
test signal. Specifically: B3+B4 mid-session flip (criterion 2) is BOTH
a Skeptic Q4 user-visible test AND a Composability seam-protocol test
(2.1 above). Test it once with both framings cited.

### With **UserAlignment** (gestalt angle)

UserAlignment's gestalt rule "user sees X / agent sees X" is the user-side
view of my orthogonality crystal. End-to-end tests that verify "user
clicks effort, agent's next SDK call uses new effort" are the
composability-meets-gestalt sweet spot.

The 10-point crystal in §3 is also a 10-point gestalt sweep -- each
combination has a one-sentence "what does the user / agent observe?"
that UserAlignment can verify.

### With **Terminology** (canonical-name angle)

Terminology's glossary defines what canonical names mean. My
composability tests assume those names ARE canonical:
- `agent.agent_type` (not `agent.role`, not `agent.type`)
- `Agent.effort` (not `Agent.thinking_budget`)
- `assemble_agent_prompt` (not `assemble_full_prompt`, not
  `compose_prompt`)
- `_LoaderAdapter` (the adapter class name)
- `compute_digest`, `compute_advance_checks_digest`, `GuardrailEntry`,
  `AdvanceCheckEntry` (shapes Slot 3 ships)

If any of these change, all my seam-protocol tests need rewiring.
Recommendation: terminology should pin canonical names in their
testing-vision memo so the test suite has stable handles.

---

## 8. Open questions for testing-specification phase

These bubble up from the testing-vision pass and need testing-specification
to resolve:

1. **What's the test for "single composition point"?** A grep-based
   integration test? An AST walk? A static lint rule? Pick one. Without a
   mechanism, the invariant decays.

2. **What level of model-string testing for `EffortLabel.levels_for_model`?**
   The current substring match works for known model families. Should we
   pin the test to a specific model id list (claude-opus-4-5, claude-sonnet-4-5,
   claude-haiku-3-5) or leave it heuristic?

3. **`_LoaderAdapter` Protocol typing -- should testing-specification
   add the Protocol class** (per my slot 4 review minor) so callers can
   type-check the adapter without `# type: ignore`? If yes, the leaf
   `guardrails/hooks.py` gets a small Protocol type addition (zero
   behavior change).

4. **Disabled-rules testing:** the `_get_disabled_rules` helper has a
   bug today (raw entries vs `compute_digest`'s direct-membership check
   -- see slot 4 SHOULD-FIX (1)). Testing-specification needs a test
   that pins behavior with a tier-prefixed entry like `user:my_rule`.
   Either the test reflects the current bug (entries don't match) and
   the bug is filed as known, or the bug is fixed first.

5. **Five-vs-four inject site enumeration:** SPEC.md now lists 5 sites.
   Tests should enumerate them by name and assert each fires. If a
   future SPEC adds a 6th, the test catalogue needs updating in
   lockstep.

6. **Crystal-point coverage targets:** are the 10 points in §3 sufficient?
   Or do we want a parametrized sweep that runs all 128 combinations as
   smoke (with most being one-line assertions)? The composability rubric
   says "test the edges" -- but for an architecture this small, full
   parametrization may be cheap enough to do.

---

## 9. Bottom line

The composability axis testing-vision is:

- **Test the law (`assemble_agent_prompt`), not the M^N combinations.**
- **Test the six seams with focused protocol assertions, not end-to-end.**
- **Sweep 10 representative crystal points to verify orthogonality.**
- **Pin the smells as executable lint** (no hand-rolled concats; no
  axis-type branches; no special-case composition).
- **Each axis testable in isolation** -- if the test needs a TUI, the
  seam is dirty.

These extend the team-level success criteria with the architectural
guarantees that make the implementation composable, not just functional.
A passing pytest suite proves the code runs; a passing composability
test suite proves the architecture survives future changes.

---

*End of Composability axis Testing Vision memo.*
