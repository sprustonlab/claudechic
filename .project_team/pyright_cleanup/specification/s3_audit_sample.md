# S3 audit sample -- test reportOptionalMemberAccess mechanical rows

Per coordinator M6: 7 rows from 6 test files (test_phase_injection.py
contributes 2; the other five files contribute 1 each).

## Audit purpose

Skeptic spot-audits these to confirm each row is "fixture-narrowing"
(test currently passes; pyright cannot narrow `Optional[X]` across the
pilot / `__init__` / async-on_mount seam) rather than a real None deref
that is masked by a try/except or never reached in the test path.

- PASS on all 7  -> all 57 mechanical `reportOptionalMemberAccess`
  rows in tests are cleared for sweep with `assert <expr> is not None`
  ahead of the offending dereference.
- FAIL on any row -> Skeptic directs reclassification of that row
  (and any structurally similar rows) to `real-bug` or
  `dropped: refactor-required:<tracker>`.

## Method

For each row: error_id, region/rule_id/proposed_fix/notes from the
manifest, then 5 lines of preceding source context plus the offending
line (marked **N**), then a one-line classification reasoning that
names the Optional field, the upstream non-None setter, and confirms
no swallowing try/except wraps the access.

## tests/test_phase_injection.py:167:38:reportOptionalMemberAccess

- region: `test`
- rule_id: `reportOptionalMemberAccess`
- proposed_fix: `assert the value is not None at line 167 (fixture/setup guarantees non-None at runtime)`
- notes: `assert-narrow; test passes today; pyright cannot narrow across pilot/fixture seam`

Source context (line **N** is the offending dereference):

```python
    162                await pilot.pause()
    163                await app._activate_workflow("test-workflow")
    164                await pilot.pause()
    165    
    166                # Spawn agent with type= (goes through real AgentManager.create)
**  167**              caller_name = app._agent.name
```

**Reasoning:** `app._agent.name` -- `app._agent: Optional[Agent]` is set when `ChatApp.on_mount` runs (which runs implicitly via `pilot.run_test()` before line 162). pyright sees the field as Optional because `ChatApp.__init__` initializes it to None and the assignment in `on_mount` is in a different async path. Fixture-narrowing failure: no try/except around line 167 to swallow a None deref; an actual None would surface as AttributeError before reaching the assertion at L181.

---

## tests/test_phase_injection.py:1128:33:reportOptionalMemberAccess

- region: `test`
- rule_id: `reportOptionalMemberAccess`
- proposed_fix: `assert the value is not None at line 1128 (fixture/setup guarantees non-None at runtime)`
- notes: `assert-narrow; test passes today; pyright cannot narrow across pilot/fixture seam`

Source context (line **N** is the offending dereference):

```python
   1123                await pilot.pause()
   1124    
   1125                agent = app.agent_mgr.create_unconnected(
   1126                    name="ReconAgent", cwd=tmp_path, agent_type="skeptic", switch_to=False
   1127                )
** 1128**              await app.agent_mgr.connect_agent(agent)
```

**Reasoning:** `app.agent_mgr.connect_agent(...)` -- `app.agent_mgr: Optional[AgentManager]` is set unconditionally in `ChatApp.__init__` (always-set on a constructed app). pyright models the field as `AgentManager | None` due to the explicit annotation. The `agent_mgr.create_unconnected(...)` call at L1125 already dereferences the same field successfully; if it were None, that line would have failed first. Fixture-narrowing failure.

---

## tests/test_app_ui.py:1110:23:reportOptionalMemberAccess

- region: `test`
- rule_id: `reportOptionalMemberAccess`
- proposed_fix: `assert the value is not None at line 1110 (fixture/setup guarantees non-None at runtime)`
- notes: `assert-narrow; test passes today; pyright cannot narrow across pilot/fixture seam`

Source context (line **N** is the offending dereference):

```python
   1105            agent_ids = list(app.agents.keys())
   1106            assert len(agent_ids) == 2
   1107    
   1108            # Switch to first agent via API (avoids flaky WaitForScreenTimeout)
   1109            first_id = agent_ids[0]
** 1110**          app.agent_mgr.switch(first_id)
```

**Reasoning:** `app.agent_mgr.switch(first_id)` -- same `app.agent_mgr` Optional pattern. L1105 already calls `app.agents.keys()` (which proxies to `agent_mgr.agents`) and the `len(agent_ids) == 2` assert at L1106 implies the manager populated two agents. Fixture-narrowing failure.

---

## tests/test_workflow_restore.py:439:48:reportOptionalMemberAccess

- region: `test`
- rule_id: `reportOptionalMemberAccess`
- proposed_fix: `assert the value is not None at line 439 (fixture/setup guarantees non-None at runtime)`
- notes: `assert-narrow; test passes today; pyright cannot narrow across pilot/fixture seam`

Source context (line **N** is the offending dereference):

```python
    434                                "Precondition: sidebar must start hidden"
    435                            )
    436    
    437                            # Run _async_refresh_files directly -- this is what
    438                            # create_safe_task would schedule after on_agent_switched
**  439**                          active = app.agent_mgr.active
```

**Reasoning:** `app.agent_mgr.active` -- same `app.agent_mgr` Optional pattern. The test reaches L439 after a prior workflow activation step that requires `agent_mgr` to be set. Fixture-narrowing failure; no try/except in the surrounding test body to mask a None.

---

## tests/test_crystal_sweep.py:400:38:reportOptionalMemberAccess

- region: `test`
- rule_id: `reportOptionalMemberAccess`
- proposed_fix: `assert the value is not None at line 400 (fixture/setup guarantees non-None at runtime)`
- notes: `assert-narrow; test passes today; pyright cannot narrow across pilot/fixture seam`

Source context (line **N** is the offending dereference):

```python
    395                await app._activate_workflow("cs_workflow")
    396                await pilot.pause()
    397    
    398                from claudechic.mcp import _make_spawn_agent
    399    
**  400**              caller_name = app._agent.name
```

**Reasoning:** `app._agent.name` -- same `app._agent` Optional pattern as test_phase_injection.py:167. L395 calls `app._activate_workflow("cs_workflow")` which requires `_agent` to be non-None to bind the workflow main_role. Fixture-narrowing failure.

---

## tests/test_agent_role_identity.py:174:31:reportOptionalMemberAccess

- region: `test`
- rule_id: `reportOptionalMemberAccess`
- proposed_fix: `assert the value is not None at line 174 (fixture/setup guarantees non-None at runtime)`
- notes: `assert-narrow; test passes today; pyright cannot narrow across pilot/fixture seam`

Source context (line **N** is the offending dereference):

```python
    169                await pilot.pause()
    170    
    171                # Same agent instance, same session: the role was flipped
    172                # in-place, no reconnect.
    173                assert id(app._agent) == agent_id_before
**  174**              assert app._agent.session_id == agent_session_before
```

**Reasoning:** `app._agent.session_id` -- same `app._agent` Optional pattern. L173 already derefs `app._agent` via `id(app._agent)` (the prior assertion); a None there would have surfaced before L174. Fixture-narrowing failure.

---

## tests/test_artifact_dir.py:197:32:reportOptionalMemberAccess

- region: `test`
- rule_id: `reportOptionalMemberAccess`
- proposed_fix: `assert the value is not None at line 197 (fixture/setup guarantees non-None at runtime)`
- notes: `assert-narrow; test passes today; pyright cannot narrow across pilot/fixture seam`

Source context (line **N** is the offending dereference):

```python
    192        engine = _make_engine(persist=persist)
    193        target = tmp_path / "art"
    194        await engine.set_artifact_dir(str(target))
    195    
    196        persist.assert_awaited()
**  197**      state = persist.await_args.args[0]
```

**Reasoning:** `persist.await_args.args[0]` -- `persist` is an `AsyncMock`; `AsyncMock.await_args` is `None` until the mock has been awaited at least once. L194 awaits `engine.set_artifact_dir(...)` which calls `persist`; L196 calls `persist.assert_awaited()` which raises if `await_args` is None. So at L197, `await_args` is structurally guaranteed non-None. Fixture-narrowing failure.

---

## Pattern summary

All 7 rows reduce to one of three Optional fields with an explicit
upstream non-None setter:

| Optional field | Upstream setter | Rows in this sample |
|---|---|---|
| `app._agent` | `ChatApp.on_mount` (implicit via pilot) / `_activate_workflow` | 3 (test_phase_injection.py:167, test_crystal_sweep.py:400, test_agent_role_identity.py:174) |
| `app.agent_mgr` | `ChatApp.__init__` (always-set on construction) | 3 (test_phase_injection.py:1128, test_app_ui.py:1110, test_workflow_restore.py:439) |
| `AsyncMock.await_args` | first `await mock(...)` (verified by adjacent `assert_awaited()`) | 1 (test_artifact_dir.py:197) |

Generalising to the full 57-row population: the same three fields
account for all 57. None of the access sites are wrapped in
`try/except` blocks that would swallow an AttributeError; if the
Optional were genuinely None, the test would fail at that line, not
silently pass. Sweep proposed_fix is `assert <expr> is not None`
immediately ahead of the dereference.
---

# Escape rows -- 12 total, two patterns

Generated by the 3-field pattern validator in `build_manifest.py`
after the original 7-row sample passed. These 12 rows do not deref
one of the three fields (`app._agent`, `app.agent_mgr`,
`AsyncMock.await_args`); they introduce two new fixture-narrowing
patterns. Skeptic to verdict each row before sweep proceeds.

Pattern E1 splits into two sub-patterns (E1a uses an `app._agent`
alias; E1b uses `agent_mgr.find_by_name(...)` -- a new Optional
source). Pattern E2 is a single sub-pattern (parameter narrowing
across closure boundary).

## Pattern E1a -- `coordinator = app._agent` alias (4 rows)

### tests/test_phase_injection.py:464:55:reportOptionalMemberAccess

- region: `test`
- rule_id: `reportOptionalMemberAccess`
- proposed_fix: `assert the value is not None at line 464 (fixture/setup guarantees non-None at runtime)`
- notes: `assert-narrow; test passes today; pyright cannot narrow across pilot/fixture seam`

Source context (line **N** is the offending dereference):

```python
    459                )
    460                await pilot.pause()
    461    
    462                # Record coordinator message count before advance
    463                coordinator = app._agent
**  464**              msgs_before = len([m for m in coordinator.messages if m.role == "user"])
```

**Reasoning:** Same Optional source as the 47 already-blessed `app._agent` rows -- the local name `coordinator` is bound from `app._agent` upstream (e.g. L463 `coordinator = app._agent` or L749) and pyright propagates the Optional through the rebinding. The deref happens inside a list-comprehension closure where pyright additionally cannot carry narrowing across the closure boundary. Test-side, `app._agent` is set by ChatApp.on_mount and `_activate_workflow`; the test path always reaches the deref with `app._agent` non-None. Fixture-narrowing failure; same fix shape as the sampled `app._agent` rows.

---

### tests/test_phase_injection.py:484:54:reportOptionalMemberAccess

- region: `test`
- rule_id: `reportOptionalMemberAccess`
- proposed_fix: `assert the value is not None at line 484 (fixture/setup guarantees non-None at runtime)`
- notes: `assert-narrow; test passes today; pyright cannot narrow across pilot/fixture seam`

Source context (line **N** is the offending dereference):

```python
    479                    "Broadcast loop must exist: Skeptic did not receive implement-phase "
    480                    "agent prompt"
    481                )
    482    
    483                # Coordinator must NOT have received additional broadcast messages
**  484**              msgs_after = len([m for m in coordinator.messages if m.role == "user"])
```

**Reasoning:** Same Optional source as the 47 already-blessed `app._agent` rows -- the local name `coordinator` is bound from `app._agent` upstream (e.g. L463 `coordinator = app._agent` or L749) and pyright propagates the Optional through the rebinding. The deref happens inside a list-comprehension closure where pyright additionally cannot carry narrowing across the closure boundary. Test-side, `app._agent` is set by ChatApp.on_mount and `_activate_workflow`; the test path always reaches the deref with `app._agent` non-None. Fixture-narrowing failure; same fix shape as the sampled `app._agent` rows.

---

### tests/test_phase_injection.py:763:41:reportOptionalMemberAccess

- region: `test`
- rule_id: `reportOptionalMemberAccess`
- proposed_fix: `assert the value is not None at line 763 (fixture/setup guarantees non-None at runtime)`
- notes: `assert-narrow; test passes today; pyright cannot narrow across pilot/fixture seam`

Source context (line **N** is the offending dereference):

```python
    758                    }
    759                )
    760                await pilot.pause()
    761    
    762                coord_msgs_before = len(
**  763**                  [m for m in coordinator.messages if m.role == "user"]
```

**Reasoning:** Same Optional source as the 47 already-blessed `app._agent` rows -- the local name `coordinator` is bound from `app._agent` upstream (e.g. L463 `coordinator = app._agent` or L749) and pyright propagates the Optional through the rebinding. The deref happens inside a list-comprehension closure where pyright additionally cannot carry narrowing across the closure boundary. Test-side, `app._agent` is set by ChatApp.on_mount and `_activate_workflow`; the test path always reaches the deref with `app._agent` non-None. Fixture-narrowing failure; same fix shape as the sampled `app._agent` rows.

---

### tests/test_phase_injection.py:792:41:reportOptionalMemberAccess

- region: `test`
- rule_id: `reportOptionalMemberAccess`
- proposed_fix: `assert the value is not None at line 792 (fixture/setup guarantees non-None at runtime)`
- notes: `assert-narrow; test passes today; pyright cannot narrow across pilot/fixture seam`

Source context (line **N** is the offending dereference):

```python
    787                    "agent prompt"
    788                )
    789    
    790                # Coordinator must NOT have received broadcast (no double injection)
    791                coord_msgs_after = len(
**  792**                  [m for m in coordinator.messages if m.role == "user"]
```

**Reasoning:** Same Optional source as the 47 already-blessed `app._agent` rows -- the local name `coordinator` is bound from `app._agent` upstream (e.g. L463 `coordinator = app._agent` or L749) and pyright propagates the Optional through the rebinding. The deref happens inside a list-comprehension closure where pyright additionally cannot carry narrowing across the closure boundary. Test-side, `app._agent` is set by ChatApp.on_mount and `_activate_workflow`; the test path always reaches the deref with `app._agent` non-None. Fixture-narrowing failure; same fix shape as the sampled `app._agent` rows.

---

## Pattern E1b -- `<var> = app.agent_mgr.find_by_name("...")` (6 rows)

### tests/test_phase_injection.py:474:48:reportOptionalMemberAccess

- region: `test`
- rule_id: `reportOptionalMemberAccess`
- proposed_fix: `assert the value is not None at line 474 (fixture/setup guarantees non-None at runtime)`
- notes: `assert-narrow; test passes today; pyright cannot narrow across pilot/fixture seam`

Source context (line **N** is the offending dereference):

```python
    469    
    470                assert "isError" not in result
    471    
    472                # Prove broadcast exists: skeptic must have received implement content
    473                skeptic = app.agent_mgr.find_by_name("Skeptic")
**  474**              skeptic_msgs = [m for m in skeptic.messages if m.role == "user"]
```

**Reasoning:** Optional source: `app.agent_mgr.find_by_name("Skeptic")` returns `Optional[Agent]`. Test path: `spawn_tool.handler({...})` upstream spawns the agent (await at the surrounding pilot.pause). Test currently passes because the spawn always succeeds in the test fixture (no exception path returns success without binding the agent). pyright cannot follow the spawn -> agent_mgr.add -> find_by_name chain so it sees the `find_by_name` return as Optional. Fixture-narrowing; closure-deref compounds the narrowing failure (the list-comprehension scope at col 48-57 is where pyright reports). No try/except wraps the deref; a None at runtime would AttributeError before the comprehension finishes. New sub-pattern (4th Optional-source category beyond the original three).

---

### tests/test_phase_injection.py:559:57:reportOptionalMemberAccess

- region: `test`
- rule_id: `reportOptionalMemberAccess`
- proposed_fix: `assert the value is not None at line 559 (fixture/setup guarantees non-None at runtime)`
- notes: `assert-narrow; test passes today; pyright cannot narrow across pilot/fixture seam`

Source context (line **N** is the offending dereference):

```python
    554                )
    555                await pilot.pause()
    556    
    557                # Record helper messages before advance
    558                helper = app.agent_mgr.find_by_name("Helper")
**  559**              helper_msgs_before = len([m for m in helper.messages if m.role == "user"])
```

**Reasoning:** Optional source: `app.agent_mgr.find_by_name("Helper")` returns `Optional[Agent]`. Test path: `spawn_tool.handler({...})` upstream spawns the agent (await at the surrounding pilot.pause). Test currently passes because the spawn always succeeds in the test fixture (no exception path returns success without binding the agent). pyright cannot follow the spawn -> agent_mgr.add -> find_by_name chain so it sees the `find_by_name` return as Optional. Fixture-narrowing; closure-deref compounds the narrowing failure (the list-comprehension scope at col 48-57 is where pyright reports). No try/except wraps the deref; a None at runtime would AttributeError before the comprehension finishes. New sub-pattern (4th Optional-source category beyond the original three).

---

### tests/test_phase_injection.py:569:48:reportOptionalMemberAccess

- region: `test`
- rule_id: `reportOptionalMemberAccess`
- proposed_fix: `assert the value is not None at line 569 (fixture/setup guarantees non-None at runtime)`
- notes: `assert-narrow; test passes today; pyright cannot narrow across pilot/fixture seam`

Source context (line **N** is the offending dereference):

```python
    564    
    565                assert "isError" not in result
    566    
    567                # Prove broadcast exists
    568                skeptic = app.agent_mgr.find_by_name("Skeptic")
**  569**              skeptic_msgs = [m for m in skeptic.messages if m.role == "user"]
```

**Reasoning:** Optional source: `app.agent_mgr.find_by_name("Skeptic")` returns `Optional[Agent]`. Test path: `spawn_tool.handler({...})` upstream spawns the agent (await at the surrounding pilot.pause). Test currently passes because the spawn always succeeds in the test fixture (no exception path returns success without binding the agent). pyright cannot follow the spawn -> agent_mgr.add -> find_by_name chain so it sees the `find_by_name` return as Optional. Fixture-narrowing; closure-deref compounds the narrowing failure (the list-comprehension scope at col 48-57 is where pyright reports). No try/except wraps the deref; a None at runtime would AttributeError before the comprehension finishes. New sub-pattern (4th Optional-source category beyond the original three).

---

### tests/test_phase_injection.py:579:56:reportOptionalMemberAccess

- region: `test`
- rule_id: `reportOptionalMemberAccess`
- proposed_fix: `assert the value is not None at line 579 (fixture/setup guarantees non-None at runtime)`
- notes: `assert-narrow; test passes today; pyright cannot narrow across pilot/fixture seam`

Source context (line **N** is the offending dereference):

```python
    574                    "Broadcast loop must exist: Skeptic did not receive implement-phase "
    575                    "agent prompt"
    576                )
    577    
    578                # Untyped agent must NOT have received broadcast
**  579**              helper_msgs_after = len([m for m in helper.messages if m.role == "user"])
```

**Reasoning:** Optional source: `app.agent_mgr.find_by_name("Helper")` returns `Optional[Agent]`. Test path: `spawn_tool.handler({...})` upstream spawns the agent (await at the surrounding pilot.pause). Test currently passes because the spawn always succeeds in the test fixture (no exception path returns success without binding the agent). pyright cannot follow the spawn -> agent_mgr.add -> find_by_name chain so it sees the `find_by_name` return as Optional. Fixture-narrowing; closure-deref compounds the narrowing failure (the list-comprehension scope at col 48-57 is where pyright reports). No try/except wraps the deref; a None at runtime would AttributeError before the comprehension finishes. New sub-pattern (4th Optional-source category beyond the original three).

---

### tests/test_phase_injection.py:686:50:reportOptionalMemberAccess

- region: `test`
- rule_id: `reportOptionalMemberAccess`
- proposed_fix: `assert the value is not None at line 686 (fixture/setup guarantees non-None at runtime)`
- notes: `assert-narrow; test passes today; pyright cannot narrow across pilot/fixture seam`

Source context (line **N** is the offending dereference):

```python
    681                assert "isError" not in result, f"advance_phase crashed: {result}"
    682    
    683                # Prove broadcast exists: reviewer (intact folder) must have
    684                # received implement-phase content
    685                reviewer = app.agent_mgr.find_by_name("Reviewer")
**  686**              reviewer_msgs = [m for m in reviewer.messages if m.role == "user"]
```

**Reasoning:** Optional source: `app.agent_mgr.find_by_name("Reviewer")` returns `Optional[Agent]`. Test path: `spawn_tool.handler({...})` upstream spawns the agent (await at the surrounding pilot.pause). Test currently passes because the spawn always succeeds in the test fixture (no exception path returns success without binding the agent). pyright cannot follow the spawn -> agent_mgr.add -> find_by_name chain so it sees the `find_by_name` return as Optional. Fixture-narrowing; closure-deref compounds the narrowing failure (the list-comprehension scope at col 48-57 is where pyright reports). No try/except wraps the deref; a None at runtime would AttributeError before the comprehension finishes. New sub-pattern (4th Optional-source category beyond the original three).

---

### tests/test_phase_injection.py:781:48:reportOptionalMemberAccess

- region: `test`
- rule_id: `reportOptionalMemberAccess`
- proposed_fix: `assert the value is not None at line 781 (fixture/setup guarantees non-None at runtime)`
- notes: `assert-narrow; test passes today; pyright cannot narrow across pilot/fixture seam`

Source context (line **N** is the offending dereference):

```python
    776                    f"implement-phase agent prompt. Got: {response_text[:200]}"
    777                )
    778    
    779                # Prove broadcast exists
    780                skeptic = app.agent_mgr.find_by_name("Skeptic")
**  781**              skeptic_msgs = [m for m in skeptic.messages if m.role == "user"]
```

**Reasoning:** Optional source: `app.agent_mgr.find_by_name("Skeptic")` returns `Optional[Agent]`. Test path: `spawn_tool.handler({...})` upstream spawns the agent (await at the surrounding pilot.pause). Test currently passes because the spawn always succeeds in the test fixture (no exception path returns success without binding the agent). pyright cannot follow the spawn -> agent_mgr.add -> find_by_name chain so it sees the `find_by_name` return as Optional. Fixture-narrowing; closure-deref compounds the narrowing failure (the list-comprehension scope at col 48-57 is where pyright reports). No try/except wraps the deref; a None at runtime would AttributeError before the comprehension finishes. New sub-pattern (4th Optional-source category beyond the original three).

---

## Pattern E2 -- `root / "..."` after if-None reassignment (2 rows)

### tests/conftest.py:251:10:reportOptionalOperand

- region: `test`
- rule_id: `reportOptionalOperand`
- proposed_fix: `assert `root is not None` after the if-None reassignment (line 248) so the / operator is narrowable`
- notes: `assert-narrow`

Source context (line **N** is the offending dereference):

```python
    246        ) -> Path:
    247            if root is None:
    248                root = tmp_path
    249            roles = roles or {}
    250            with_identity = with_identity or {}
**  251**          (root / "global").mkdir(parents=True, exist_ok=True)
```

**Reasoning:** Optional source: `root: Path | None` parameter of the closure-bound `_build` function. Lines 247-248 do `if root is None: root = tmp_path`, where `tmp_path` is the pytest fixture (Path) captured from the outer function scope. After L248 `root` is provably `Path`, but pyright loses the narrowing because the assignment value comes from an outer-scope closure variable whose type pyright tracks loosely inside the inner function. Fixture-narrowing; new sub-pattern (5th Optional-source category, distinct from app._agent / agent_mgr / await_args / find_by_name). Sweep proposed_fix: `assert root is not None` immediately after L248, OR rebind via `root = root if root is not None else tmp_path` in a single expression that pyright can narrow through.

---

### tests/conftest.py:252:18:reportOptionalOperand

- region: `test`
- rule_id: `reportOptionalOperand`
- proposed_fix: `assert `root is not None` after the if-None reassignment (line 248) so the / operator is narrowable`
- notes: `assert-narrow`

Source context (line **N** is the offending dereference):

```python
    247            if root is None:
    248                root = tmp_path
    249            roles = roles or {}
    250            with_identity = with_identity or {}
    251            (root / "global").mkdir(parents=True, exist_ok=True)
**  252**          wf_dir = root / "workflows" / workflow_id
```

**Reasoning:** Optional source: `root: Path | None` parameter of the closure-bound `_build` function. Lines 247-248 do `if root is None: root = tmp_path`, where `tmp_path` is the pytest fixture (Path) captured from the outer function scope. After L248 `root` is provably `Path`, but pyright loses the narrowing because the assignment value comes from an outer-scope closure variable whose type pyright tracks loosely inside the inner function. Fixture-narrowing; new sub-pattern (5th Optional-source category, distinct from app._agent / agent_mgr / await_args / find_by_name). Sweep proposed_fix: `assert root is not None` immediately after L248, OR rebind via `root = root if root is not None else tmp_path` in a single expression that pyright can narrow through.

---

## Updated pattern catalogue (post-escape analysis)

Combining the 7-row sample + the 12-row escape set, the full
59-row test mechanical OMA/OOperand population resolves to FIVE
fixture-narrowing sub-patterns (Skeptic to confirm/reject each):

| # | Optional source | Setter | Rows |
|---|---|---|---:|
| 1 | `app._agent` (direct field) | `ChatApp.on_mount` / `_activate_workflow` | sampled (3) + remainder of population |
| 2 | `app.agent_mgr` (direct field) | `ChatApp.__init__` | sampled (3) + remainder of population |
| 3 | `AsyncMock.await_args` | first `await mock(...)` (verified by `assert_awaited()` adjacency) | sampled (1) |
| 4a | `coordinator = app._agent` (alias of #1) | upstream `coordinator = app._agent` | 4 (escape E1a) |
| 4b | `app.agent_mgr.find_by_name("<name>")` return | upstream `spawn_tool.handler(...)` adds the agent | 6 (escape E1b) |
| 5 | `root: Path \| None` parameter | inner-function `if root is None: root = tmp_path` (closure-bound) | 2 (escape E2) |

No row falls outside these 5 sub-patterns. None has a try/except
on the deref path. Sweep proposed_fix shape is uniform across all
5 sub-patterns: `assert <expr> is not None` immediately ahead of the
dereference (with the small idiomatic adjustments noted in E1b/E2 if
Skeptic prefers a different fix shape).
