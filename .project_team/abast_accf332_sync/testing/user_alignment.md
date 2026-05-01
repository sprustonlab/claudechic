# Testing-Vision -- UserAlignment axis memo

**Author:** UserAlignment agent
**Date:** 2026-05-01
**Phase:** testing-vision
**Sources of truth:** `userprompt.md` (verbatim), `SPEC.md` (locked), STATUS.md
(decisions), prior `specification/user_alignment.md` (C1-C8 standing
checks), 6-slot review trail.

This memo answers the coordinator's testing-vision frame from the
user-alignment axis: **does the test plan actually verify what the user
asked for, or does it verify only what the implementer thinks they
asked for?**

The team's coordinator-level success criteria are sound for technical
correctness (pytest suite, smoke tests, inject-site coverage, regression
check). What follows is the user-intent-level overlay: per-feature
gestalts that testing MUST verify, and the user-intent failure modes a
typical pytest run will quietly miss.

---

## 1. The two-axis gestalt grid (binding per C8)

For every user-named feature, both gestalts MUST be verified, not just
one. The user's redirect (2026-04-29) is a permanent standing reminder:
**features have an agent-side reality the team kept under-weighting**.
Testing-vision is the last gate where we catch that.

### A -- "workflow template variables"

| Axis | Gestalt the user expects after this lands | Testing-vision MUST verify |
|------|--------------------------------------------|-----------------------------|
| User-side | "I can write `${WORKFLOW_ROOT}/.git/HEAD` in workflow YAML and the engine resolves it; sub-agents in worktree subdirs stop hitting false-failing relative-path advance checks." | A workflow manifest with `${WORKFLOW_ROOT}` in a check param resolves correctly when run from the engine; an advance check executed under a sub-agent cwd different from the workflow root still passes against an absolute path. |
| Agent-side | "My phase prompt and check params come pre-substituted with absolute paths -- I don't have to spell out the workflow root." | Inject a `${WORKFLOW_ROOT}` token into a role's identity.md or phase.md; the rendered prompt the agent receives contains the resolved absolute path, NOT the literal token. |

**Quiet-failure-mode the static suite may miss:** a unit test of
`substitute_workflow_root()` proves the substitution function works.
It does NOT prove the substituted output reaches the agent's actual
SDK turn. **Testing must include an end-to-end path** from engine
`${WORKFLOW_ROOT}` -> `assemble_agent_prompt` -> `_send_to_active_agent`
or `spawn_agent` -> what the agent sees in the SDK transcript.

---

### B -- "dynamic roles"

| Axis | Gestalt | Testing-vision MUST verify |
|------|---------|-----------------------------|
| User-side | "I activate a workflow and my main agent's role flips to `main_role` without an SDK reconnect; deactivation restores the default; my session stays connected through the flip." | Activate a workflow on an existing main agent; verify NO SDK reconnect occurs (transport stays alive) AND `agent.agent_type` flips to the workflow's `main_role`. Deactivate; verify it reverts to `DEFAULT_ROLE`. |
| Agent-side | "I have a queryable runtime self-identity (`agent.agent_type`) that survives `/compact` and is exposed in `CLAUDE_AGENT_ROLE` env; guardrail hooks read this live, so role-scoped rules apply to ME specifically." | (a) `mcp__chic__whoami` and `mcp__chic__get_agent_info` return the new role post-activation. (b) After `/compact`, the role is preserved (not lost). (c) `CLAUDE_AGENT_ROLE` env var matches `agent.agent_type` at next SDK turn. (d) A role-scoped rule fires on the agent's tool call when its role is in the rule's `roles:` list, and DOES NOT fire when its role isn't. (e) Critical: the falsy-check sweep at `mcp.py:980,983` -- agents whose `agent_type == DEFAULT_ROLE` are correctly skipped from broadcast routing (NOT incorrectly receiving phase prompts intended for typed sub-agents). |

**Quiet-failure-mode the static suite may miss:** a test that calls
`agent.agent_type = "coordinator"` and asserts on the attribute proves
the SETTER works. It does NOT prove the WHOLE substrate (env var, hook
closures, post-compact restoration, broadcast filtering) flows from
that mutation. **Testing must include a B3 mid-session role flip via
the remote-control smoke** the coordinator's frame already calls for --
which is exactly right; please ensure that smoke checks ALL FIVE
downstream consumption sites, not just the attribute mutation.

---

### C -- "effort cycling"

| Axis | Gestalt | Testing-vision MUST verify |
|------|---------|-----------------------------|
| User-side | "I click the 'effort' label in the footer and the level cycles; on Opus I cycle through 4 levels including 'max'; on Sonnet/Haiku I cycle through 3 and the level snaps to 'medium' when I switch from Opus mid-session; the level survives a restart." | (a) Click cycle works on each model class; (b) model-change snap behavior fires (max -> medium on switch to Sonnet), per **SPEC C2 verbatim "non-Opus snaps to medium"**; (c) restart preserves the level via `~/.claudechic/config.yaml`; (d) `/settings` knob and footer click are equivalent paths to the same persisted state. |
| Agent-side | "Each Agent instance carries its own `effort` level read live by the options factory; different agents in the multi-agent UI can run with different budgets; mid-session changes take effect on the next response without reconnect." | (a) Two agents in the multi-agent UI with different `effort` values both reach the SDK with their own value (verify by inspecting `subprocess_cli.py`'s `--effort <level>` argv passthrough or the SDK's options on connect); (b) clicking the footer mid-session changes the next turn's effort without reconnecting the transport. |

**Quiet-failure-mode the static suite may miss:** a unit test of
`EffortLabel.on_click` cycling through levels proves the WIDGET works.
It does NOT prove the chosen level reaches the SDK subprocess argv.
**Testing-vision must include the SDK-trace verification** I can't do
in unit tests alone -- somewhere we need to confirm
`agent.effort = "low"` actually produces `--effort low` in the
subprocess argv (or whatever the SDK transport is doing today).

**[WARNING] Carry-forward: SPEC C1 Interfaces still locks
`Literal["low","medium","high"]` (3 values), but the implementation
ships 4 ("max" added across 4 modules). User has NOT ratified the 3->4
widening per the per-feature gate (clarification 3). Testing-vision
should verify the user has explicitly blessed the 4-value contract OR
the implementation has been reverted to 3 values. Without that
ratification, the widening is per-feature scope expansion shipped
silently.**

---

### D -- "guardrails UI" (reframed-implementation: agent-aware constraints)

This is THE feature that must be tested most carefully because it is the
one that was reframed mid-Specification. The user explicitly redirected
on 2026-04-29: "the point of D is NOT UI it is to make the current
state of guardrail rules and advance checks transparent to the AGENT."

**Final-report contract reminder:** the user-facing pass/fail row uses
the user's verbatim label "guardrails UI" with a reframed-implementation
note ("delivered as agent-aware constraints injected into launch prompts
and exposed via MCP, per user's 2026-04-29 redirect"). Do NOT silently
rename to "agent-aware constraints" in the user-facing report -- the
user said "guardrails UI" and the report must echo their wording.

| Axis | Gestalt | Testing-vision MUST verify |
|------|---------|-----------------------------|
| User-side | "No new modal or footer button. I keep managing persistent rule disables via `/settings` and `disabled_ids`. My agents become more useful because they self-correct earlier." | (a) NO `GuardrailsModal` class exists; (b) NO `_disabled_rules` runtime in-memory store; (c) NO `GuardrailsLabel` footer slot; (d) `/settings` `disabled_ids` flow still works as before. |
| Agent-side | "When I spawn / when my role activates / when my phase advances / after `/compact` -- my launch prompt has a `## Constraints` block listing the rules and advance-checks scoped to MY role and MY phase. Mid-session I can call `mcp__chic__get_applicable_rules` or `mcp__chic__get_agent_info` and get the same answer." | (a) ALL FOUR inject sites (workflow activation, sub-agent kickoff in spawn_agent, phase advance, post-compact hook) actually emit the `## Constraints` block in the agent's prompt; (b) the block contents match `mcp__chic__get_applicable_rules` for the same `(role, phase)`; (c) the block contents match `mcp__chic__get_agent_info`'s rules section for the same agent; (d) when a rule is `disabled_ids`-disabled, BOTH the launch-prompt path AND the MCP path drop it identically -- THIS IS WHERE THE SOURCE-OF-TRUTH BUG I FLAGGED IN SLOT 4 WILL SURFACE. |

**Quiet-failure-mode the static suite may miss:** a unit test of
`assemble_constraints_block()` proves the block formatter works. It
does NOT prove the block reaches the agent at all four inject sites,
NOR does it prove the launch-prompt and MCP paths agree on
`disabled_rules` filtering. **The slot-4 source-of-truth bug
(`mcp.py` passes `disabled_rules=None` while app.py passes
`_get_disabled_rules()`) means the agent gets contradictory answers
from launch prompt vs `get_applicable_rules`** -- this is exactly the
failure mode the user's redirect targets, and a unit test running
both paths against the same `disabled_ids` config will catch it.
Testing-vision should require this specific equivalence test before
declaring D verified.

**[WARNING] Carry-forward: SPEC Decision 5 locks "Single tool"
(`get_agent_info` only). Implementation ships TWO new tools
(`get_applicable_rules` AND `get_agent_info`) and `get_phase` is
narrowed but NOT deprecated. Testing-vision should verify the user has
ratified the 4-tool composite OR the implementation has been brought
back to single-tool + deprecated-get_phase. Until ratified, this is
unsanctioned scope expansion.**

---

### E -- `pytest_needs_timeout` warn rule (stowaway, not user-named)

**Final-report contract reminder:** E gets its own row in the
per-feature pass/fail report with explicit "stowaway -- discovered by
team, user did not name" type-tag. Do NOT bundle into D.

| Axis | Gestalt | Testing-vision MUST verify |
|------|---------|-----------------------------|
| User-side | "I see the warn channel surface a nudge when the agent runs `pytest` without `--timeout`. The agent retries with the recommended fix." | (a) Real `pytest tests/foo.py` -> warn fires; (b) `grep -c "pytest"` -> warn does NOT fire (Skeptic's empirically-verified prior false-positive failure mode for `no_bare_pytest`); (c) `cat pytest_help.md` and other read-only commands containing the literal string "pytest" -> warn does NOT fire. |
| Agent-side | "When I run `pytest` without `--timeout`, my injected `## Constraints` block already mentioned this rule, AND when I run anyway the warn fires and I know how to acknowledge and retry." | After E ships, the constraints block emitted at agent launch time contains a row for `global:pytest_needs_timeout` (verifies E's content actually flows into D's projection). This is the cluster's tightest internal validation: E + D together prove the agent learns the rule pre-failure. |

**Quiet-failure-mode the static suite may miss:** a regex unit test
proves the regex matches/doesn't-match strings. It does NOT prove the
rule fires on a real Bash invocation through the actual hook pipeline,
nor that the rule's prescribed fix (`--timeout=N`) actually works
in this project. **Slot 6 review empirically discovered the prescribed
fix doesn't work today** -- `pytest-timeout` is not in dev deps.
Testing-vision MUST acknowledge this gap: either the rule's message
is updated, or `pytest-timeout` is added, before sign-off. As written
the rule is "you must `acknowledge_warning` each pytest run" -- not
satisfiable.

---

### F -- modal restructure / diagnostics deletion (architectural by-product, not user-named)

**Final-report contract reminder:** F gets its own row with the same
"stowaway -- discovered by team, user did not name" type-tag as E.
Currently SPEC labels F as "architectural by-product" without the
stowaway tag; this should be reconciled before the user-facing report
goes to the user.

| Axis | Gestalt | Testing-vision MUST verify |
|------|---------|-----------------------------|
| User-side | "The 'session_info' button (now 'info') still shows me JSONL path + last compaction summary. The unified Info modal has zero info loss vs the deleted DiagnosticsModal." | (a) Click the footer `info` label -> modal opens with JSONL path filled (matching the active session's actual jsonl path) AND last compaction summary if present; (b) NOTHING the deleted DiagnosticsModal showed has gone missing. |
| Agent-side | "(none -- agent does not consult read-only viewers)" -- per SPEC §F. | Stated explicitly per C8: F has no agent-side gestalt. Testing should NOT spend cycles looking for one. |

**Quiet-failure-mode the static suite may miss:** a unit test of
`ComputerInfoModal._get_sections()` against a hand-constructed
`session_id` proves the modal renders the rows. It does NOT prove the
footer-click path actually FORWARDS `session_id` to the modal --
**slot 4's call site at `app.py:3866` only forwards `cwd`**, leaving
`session_id=None` so the unified modal renders "(no active session)"
and empty Last Compaction. **This is a real user-visible regression
vs the deleted DiagnosticsModal.** Testing-vision must include a
click-the-footer-button-and-inspect-the-modal smoke that catches this
exact gap. The unit test on the modal alone would not.

---

## 2. Cross-feature user-intent failure modes a typical pytest suite will miss

The coordinator's success criteria (pytest passes, B3 smoke, D5 inject
sites, E warn rule, F info parity, no regressions) cover most of the
ground. From the user-intent axis, here are the failure modes that
fall between the criteria:

### 2.1 "The agent self-knows what applies to it" -- runtime-only verification

**Why static tests miss it:** the user's reframe is fundamentally about
runtime experience. The agent has to actually receive the constraints
block and (ideally) act on it. Static tests prove the formatter works;
they don't prove the agent ever sees the rendered output.

**Test addition recommended:** an end-to-end test where (a) a workflow
activates with a `roles:` -scoped rule, (b) the active agent's launch
prompt is captured, (c) the prompt contains the rule in its
`## Constraints` block, (d) `mcp__chic__get_applicable_rules` returns
the same rule when called by the same agent, (e) the rule fires on a
matching tool call. **One scenario, five assertions.** Not in the
typical pytest suite.

### 2.2 Source-of-truth alignment between the launch-prompt and MCP paths

**Why static tests miss it:** unit tests typically test ONE caller,
not parity between callers. The slot-4 finding -- launch prompt uses
`_get_disabled_rules()`, MCP tools pass `disabled_rules=None` -- means
an agent that reads its launch prompt sees a filtered set, an agent
that calls `get_applicable_rules` sees the unfiltered set. The agent
gets two answers to the same question.

**Test addition recommended:** parametrize a test that disables a rule
via `disabled_ids`, then verifies BOTH the launch prompt's `## Constraints`
block AND `get_applicable_rules`'s output drop the rule identically.
Currently this test would FAIL (slot 4 source-of-truth gap I flagged).

### 2.3 Dynamic-roles WITHOUT SDK reconnect

**Why static tests miss it:** a unit test setting `agent.agent_type`
proves the attribute. It doesn't prove the SDK transport DID NOT
reconnect during a workflow activation. The user's experienced gestalt
("I activate the workflow and stay connected") is harder to verify
than the attribute mutation.

**Test addition recommended:** the smoke test should explicitly assert
that the `client` reference's `_connected` (or transport equivalent)
state is preserved across `_activate_workflow`. If a reconnect happens
but the role still flips to `main_role`, the unit tests pass but the
user gestalt fails.

### 2.4 Effort cycling actually changes SDK behavior

**Why static tests miss it:** `agent.effort` is an attribute. The SDK
consumes it via `ClaudeAgentOptions(effort=...)` -> subprocess argv
`--effort <level>`. A pytest test of the attribute proves storage. It
does not prove the model behavior changes (extended thinking on/off).

**Test addition recommended:** at minimum, a test that mocks the SDK
transport and asserts the argv contains `--effort <expected>`.
Behavior verification (does Claude actually think more on `max`?) is
out of scope; argv passthrough is the testable contract.

### 2.5 The "scope guard" was honored at code level but should be re-verified

**Why static tests miss it:** the scope guard ("stay strictly inside
the 4-commit cluster") is a process check, not a code check. There's
no test asserting "no out-of-cluster code shipped." The signal is
indirect: locked Decision 6-1 carved out the 30-line `003408a` slice
as the ONLY exception; if anything else from `1d6d432`, `ff1c5ae`,
`7dcd488`, or other abast commits leaked in, the user's R9 would be
violated.

**Test addition recommended:** during testing-vision, run a final
`git log --oneline HEAD ^merge-base` and verify the diff content
maps to (a) the locked decisions, (b) the explicit D6-1 carve-out,
and (c) nothing else. Manual gate, not pytest.

### 2.6 The user's per-feature ratification gate (R8)

**Why static tests miss it:** R8 is a process gate, not a runtime
property. Three implementation-time deviations shipped without explicit
user yes/no (C1 4-value, D4 2-tool, F 5-label). Testing cannot
"verify" ratification -- only the user can. But testing-vision should
flag the gate as unmet so sign-off doesn't proceed past it.

**Action recommended:** sign-off MUST surface the 3 unratified
deviations to the user as an explicit "amended decisions to ratify"
list. This is not a test addition; it's a sign-off prerequisite.

---

## 3. Final-report contract reminder (binding)

The user-facing pass/fail report (Documentation phase output) MUST:

1. **Use the user's verbatim feature labels** in the per-feature pass/fail
   table -- "workflow template variables", "dynamic roles", "effort
   cycling", "guardrails UI". NOT the implementer-internal terms
   "agent-self-awareness substrate", "agent-aware constraints",
   "compute budget", etc.
   - Where the implementation diverges from the user's label (D was
     reframed away from a UI), include a one-sentence
     reframed-implementation note alongside the label.
2. **Mark E and F as "stowaway -- not user-named"** in the same
   per-feature table. Currently F is labelled "architectural
   by-product" -- this should be reconciled to the same stowaway tag
   E carries.
3. **Use R4-R7 as named section headers** ("What is it about?", "What
   is the intent?", "Should we pick it up here?", "Can we reimplement
   on our base?"). The current SPEC.md and APPENDIX are
   implementer-facing and structured around components; the user-facing
   report has not been assembled yet.
4. **Distinguish per component**: cherry-pick mechanical / human merge /
   reimplement-from-scratch fraction. Per the C5 binding standing
   check.
5. **Surface the 3 unratified deviations** as a separate "amended
   decisions to ratify" list (per R8 gate above): C1 4-value Literal,
   D4 2-tool design, F 5-label footer.
6. **Surface the open closure items** per the 6-slot review trail:
   `agent.py:251` docstring fix, 4 broken tests in
   `tests/test_artifact_dir.py` (D4 caller migration), `mcp.py`
   `disabled_rules` source-of-truth wiring (3 sites), E rule's
   prescribed fix `--timeout=N` requires `pytest-timeout` not in dev
   deps.

The user gets ONE document. It must speak the user's language.

---

## 4. Coordination notes

### 4.1 With Skeptic

Skeptic owns "is this implementation correctly tested by these
specific tests?". UserAlignment owns "do these tests verify what the
user actually asked for?". Overlap on:

- **D source-of-truth equivalence test** (§2.2 above): Skeptic likely
  wants this anyway as a regression test for slot 4's bug. UserAlignment
  endorses it for vision-level reasons. Single test, two motivations.
- **Effort SDK argv passthrough test** (§2.4 above): Skeptic verifies
  the SDK contract. UserAlignment verifies the user-side gestalt
  reaches the SDK. Same test serves both.

### 4.2 With Composability

Composability owns architectural seams. The cross-cutting concerns I
flag here (source-of-truth alignment, runtime vs static gestalt
verification) are seam concerns. Specifically:

- **Hooks vs registry alignment** (slot 4 `_LoaderAdapter` work).
  Composability's compositional landing condition #1 IS the seam
  Test 2.2 covers.
- **Refresh policy** (composability's compositional landing condition #2).
  Testing-vision should verify ONE consistent story: the constraints
  block emitted at spawn (frozen) vs at MCP call (live) vs at PostCompact
  (refresh). All three should produce the same output for the same
  state. Three-call equivalence test.

### 4.3 With test infrastructure

The 4 failing tests in `tests/test_artifact_dir.py` (D4 caller
migration gap from slot 6 review) are blockers for the coordinator's
success criterion #1 ("full pytest suite passes") AND for the
user-named feature D's pass/fail row. **Must be migrated or deleted
with equivalent coverage on the new tools before testing-vision can
declare green.**

---

## 5. Summary checklist for testing-vision

The team-level success criteria (SC) plus the user-intent additions:

- [ ] SC1: full pytest suite passes
- [ ] SC1a: 4 broken tests in `tests/test_artifact_dir.py` migrated/deleted
- [ ] SC2: B3+B4 mid-session role flip smoke (5 downstream sites covered)
- [ ] SC3: D5 inject sites all 4 fire correctly (note: 4 sites, not 5 -- SPEC has internal ambiguity but implementation ships activation kickoff + sub-agent spawn + phase advance + post-compact)
- [ ] SC3a: D source-of-truth equivalence -- launch prompt and MCP paths drop the same `disabled_ids`-disabled rules
- [ ] SC3b: D refresh policy -- spawn / MCP / PostCompact produce the same output for the same state
- [ ] SC4: E warn rule fires on real pytest, not on grep/cat etc. (already empirically verified during slot 6 review)
- [ ] SC4a: E rule's prescribed fix actually works in this project, OR rule message is updated
- [ ] SC5: F modal info parity (session_id wired at app.py:3866 -- currently NOT, regression vs deleted DiagnosticsModal)
- [ ] SC6: zero new test regressions vs HEAD~1
- [ ] SC7: scope guard re-verification -- `git log` content maps to locked decisions only
- [ ] SC8: 3 unratified deviations (C1 4-value, D4 2-tool, F 5-label) surfaced to user before sign-off

If any of SC1a / SC3a / SC4a / SC5 / SC8 are unmet at testing-vision
exit, the user-facing pass/fail report cannot honestly mark the
corresponding feature as PASS.

---

*End of UserAlignment testing-vision memo. Standing by for testing-spec
phase: I will then verify the test plan covers the locked SPEC contracts
(value sets, MCP shapes, footer layout) per SPEC.md verbatim, in
addition to the user-intent overlay above.*
