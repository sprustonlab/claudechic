# Skeptic Review -- abast accf332 cluster (Specification phase)

**Author:** Skeptic
**Date:** 2026-04-29
**Phase:** project-team:specification
**Reviews:** historian_findings.md (triage + verification), leadership_findings.md
**Re-verifies independently:** the most load-bearing claims via direct
git/tree inspection (see "Independent verifications" below).

This is the lens through which the upcoming axis-agent specs (engine-seam,
guardrails-seam, UI-surface) and the eventual per-feature recommendation
must be vetted. It is **not** the recommendation itself -- it is the bar
the recommendation must clear.

---

## TL;DR -- per-feature skeptical posture

| Sub-feature | Posture | Why |
|-------------|---------|-----|
| A. Workflow template variables (`$STATE_DIR`, `$WORKFLOW_ROOT`, `workflow_library/` relocation) | **ADAPT, do not adopt** | Adoption introduces a 3rd substitution mechanism with a 2nd syntax, AND relocates state from `<repo>/.project_team/` to `~/.claudechic/workflow_library/` -- a contract break for in-flight chicsessions without a migration story. The user-visible value (no hardcoded paths in YAML) is real but our existing `${CLAUDECHIC_ARTIFACT_DIR}` already delivers it. |
| B. Dynamic roles (no-reconnect main_role promotion, `DEFAULT_ROLE` sentinel) | **ADAPT, isolate the small delta** | Our base ALREADY HAS `_activate_workflow` / `_deactivate_workflow` / `main_role` / role-name resolution -- 17 references in `app.py` confirm. The actual delta is ~3 narrow points: `DEFAULT_ROLE = "default"` sentinel, `agent_type` defaulting to it, and `agent_manager` passing the `Agent` instance into the options factory so `agent.agent_type` can be re-read at hook time. Do NOT cherry-pick the +282-line `app.py` patch wholesale -- much of it duplicates code we already wrote. |
| C. Effort cycling | **ADOPT (verified wired)** | I independently verified our installed SDK accepts `effort: Literal['low','medium','high','max']` in `ClaudeAgentOptions` -- it is NOT a cosmetic knob. Wiring is visible in the diff (`effort=effort_level` passed at options-factory level). Clean isolated change. Smallest blast radius of the cluster. |
| D. Guardrails UI (`GuardrailsModal` + `digest.py` + footer button repurposing + `DiagnosticsModal` deletion) | **PARTIAL -- adopt `digest.py` only; SKIP the modal and button repurposing** | Abast itself ships this disabled (commit 4 stubs the handler). Adopting the modal ships dead code; adopting the stub ships a useless button labelled "guardrails" that says "not yet implemented." Neither is a release. The button repurposing also DELETES our `DiagnosticsModal` (still-present, still-useful) and renames footer labels -- two UX regressions for a feature that isn't done. |
| E. `pytest_needs_timeout` warn rule | **ADOPT WITH HARDENING** | Stowaway, but the regex `(?:^|[;&\|]\s*)(?:python\s+-m\s+)?pytest\b(?!.*--timeout)` will false-positive on every `pytest tests/test_foo.py` invocation our own CLAUDE.md prescribes -- and false-positive on commands that merely *mention* the string `pytest` (this very review's investigation triggered the existing `no_bare_pytest` rule on a `grep -c "pytest"` call). Adopt only if the regex is hardened AND we accept that warn-level rules add chat noise. |

**Composite verdict:** the cluster is NOT a single feature -- it is a
4-commit bundle where each sub-feature warrants an independent
adopt/adapt/skip decision. **Bundling them is exactly the cargo-cult
trap** that our Leadership posture (A1, A6) warned against. The
Specification axis-agents must produce per-sub-feature recommendations,
not a single cluster verdict.

---

## The four questions, applied

### Q1. Does the proposed work fully solve what the user asked for?

The user asked four questions (userprompt.md):
1. What is each commit about?
2. What is the intent?
3. Should we pick it up?
4. Can we reimplement on our base?

The historian and leadership outputs answer (1) and (2) with high
confidence. The unsolved questions are (3) and (4), and they are NOT
single-valued -- the answer is per-sub-feature. Any spec that tries to
collapse (3)/(4) into a binary "adopt the cluster vs. don't" is failing
the user's question.

**Failure mode to reject:** a Specification recommendation that says
"adopt all four commits" or "skip all four" without per-sub-feature
treatment. The user's framing ("four-commit cluster... what is it
about?") *invites* sub-feature decomposition; collapsing back to one
verdict is loss of fidelity, not simplification.

### Q2. Is this complete?

Concrete completeness gates per sub-feature -- a spec that omits any of
these is shipping shortcuts:

**A (template variables / state relocation):**
- [ ] Migration story for existing `<repo>/.project_team/<name>/` state
      that already exists on user disks (or explicit decision to break,
      with user sign-off).
- [ ] Decision matrix: which substitution mechanism is canonical
      (`${CLAUDECHIC_ARTIFACT_DIR}` vs `$STATE_DIR` vs worktree
      `${branch_name}`)? If we adopt all three, the spec must enumerate
      their non-overlapping variable namespaces.
- [ ] Concrete user benefit beyond "abast did it" -- what workflow YAML
      stops being broken / becomes editable that wasn't before?

**B (dynamic roles):**
- [ ] Line-by-line delta between abast's `app.py +282` and our existing
      `_activate_workflow` / `main_role` plumbing. The "ADAPT" verdict
      stands or falls on whether this delta is small (3-5 narrow points)
      or large (overlapping rewrite).
- [ ] Verification that our current `_activate_workflow` reconnects the
      SDK on activation (if it does, abast's no-reconnect mechanism
      adds value). If it does NOT reconnect already, abast's claim of
      "no reconnect needed" is solving a non-problem on our base.
- [ ] The 6 stranded `tests/test_phase_injection.py` tests (cited in
      `18061ec` revert): does the merged code make them pass? Historian
      flagged this as "strong inference, not verified." Specification
      must verify.

**C (effort cycling):**
- [x] SDK kwarg compatibility verified by Skeptic
      (`ClaudeAgentOptions(effort=...)` accepted on `claude-agent-sdk
      >=0.1.40`, our current pin).
- [ ] Persistence: does effort persist across sessions / per-agent /
      app-global? abast's diff shows it as an instance attr on `Agent`
      with no persistence. If we want it remembered, that's additional
      scope.
- [ ] Interaction with `/fast` command if we ever adopt that (flagged
      out-of-cluster). Don't pre-commit an architecture for a feature
      we haven't approved.

**D (guardrails UI):**
- [ ] **Authoritative reading of intent on commit 4 (`a60e3fe`).** Did
      abast halt the rollout because the modal is buggy, because the
      semantics weren't decided (toggle = `disabled_ids` write-back vs
      ephemeral?), or because some upstream feature isn't ready? Without
      this, we are guessing at intent. The simplest read: abast deemed
      it not-ready; we should respect that signal.
- [ ] Decision on the `DiagnosticsModal` deletion. We still have it on
      our HEAD; deleting it is a UX regression unless its content moves
      somewhere visible. abast moves it into the unified Info modal --
      is that ergonomically better for our users? No data either way;
      cargo-culting risk.
- [ ] If we adopt `digest.py` standalone (without the modal), specify
      what consumes it. A pure function with no caller is dead code.

**E (pytest_needs_timeout):**
- [ ] Regex hardening so that *running* pytest is matched but
      *referencing* pytest in a non-execution context is not.
      Provisional fix: anchor on shell command word-start AND require
      that the line is a test invocation (e.g., not within a `git log`,
      `grep`, or message-body argument). The existing
      `no_bare_pytest` rule has the same class of bug -- it fires on
      `grep -c "pytest"` (verified during this review).
- [ ] Sample-run on our actual test commands from `CLAUDE.md` to
      confirm no regression: `pytest tests/test_foo.py -v` should NOT
      warn (per our docs this is a legitimate command), but
      `pytest --timeout=60 tests/test_foo.py -v` is the future-state
      we should be steering toward.
- [ ] Decision: do we want every `pytest` line to nag with a warn? If
      yes, follow-up issue to add `--timeout=N` to our prescribed
      commands. If no, skip the rule.

### Q3. Is complexity obscuring correctness?

**Pattern-by-pattern review of accidental complexity introduced by the cluster:**

1. **Three substitution mechanisms** (`${CLAUDECHIC_ARTIFACT_DIR}`,
   `$STATE_DIR`/`$WORKFLOW_ROOT`, `${branch_name}`/`${repo_name}`).
   Two syntaxes (`${VAR}` vs `$VAR`). Three resolvers. This is
   *accidental* complexity born of independent evolution. The spec must
   either (a) converge to one resolver+syntax (essential effort but
   one-time), or (b) document the three domains as non-overlapping with
   reserved variable namespaces (lighter but adds vocabulary load).
   Doing neither is the worst option -- and is what naive adoption
   produces.

2. **Two state-dir locations** (`<repo>/.project_team/<name>/` ours;
   `~/.claudechic/workflow_library/<key>/<name>/` abast's). This is a
   semantic change to "where workflow state lives" with implications for
   git ignorability, multi-machine sync, and existing-state migration.
   The historian flagged it; the spec must make a deliberate call.

3. **Five meanings of "guardrails"** (per Terminology):
   enforcement-system / rule-set / bool master switch / disable-list /
   *plus* abast's runtime per-rule toggle. Adopting feature D adds the
   5th meaning. The toggle's persistence semantics (write back to
   `disabled_ids`? ephemeral session state?) determine whether it's a
   distinct concept or a UI over an existing one. Both terminology and
   the historian flagged this; the spec must pin it.

4. **`agent_type` default sentinel.** abast changes `Agent.agent_type`
   from `None` to `"default"`. Tests on our base that assert
   `agent.agent_type is None` (e.g., `test_agent_type_defaults_to_none`)
   will break. abast renames the test to
   `test_agent_type_defaults_to_default_sentinel`. This is a contract
   break for any external code (or test, or hook) that does
   `if agent.agent_type is None`. Must be inventoried.

5. **`app.py` overlap** is the highest-risk merge surface (their +282
   on top of our +779 since merge-base). Both diverged in the same
   region: workflow activation, main_role plumbing, hooks setup. If the
   spec proposes "cherry-pick `accf332`," it is implicitly accepting
   substantial human merge work that may equal a reimplementation. Be
   honest about this in the spec.

6. **`computer_info.py` rewrite** absorbs `DiagnosticsModal` content.
   Historian verified zero drift on our side -- clean apply *if* we
   adopt. But: this conflates two information surfaces (system info +
   session diagnostics) into one modal. Under "everything is two
   clicks" this is fine; under "each modal has one job" it's a
   regression. The spec needs a UX rationale, not a code rationale.

### Q4. Is simplicity masking incompleteness?

**Five places where a "simple" spec would be hiding the hard part:**

S1. **"Cherry-pick the cluster" is NOT simpler than "per-feature
adapt."** It looks shorter on paper but ships dead code (D's modal),
breaks contracts (A's state location, B's `agent_type` sentinel
default), and creates an inferior UX (D's button repurposing for a
feature abast didn't ship). The historian's verdict ("naive cherry-pick
will conflict heavily and require human merge work that effectively *is*
a reimplementation of feature B on top of our base") is correct.

S2. **"Skip the cluster entirely" is NOT simpler than per-feature
adopt.** It abandons the SDK-ready effort cycling (clean win, low
effort), the `digest.py` building block (useful future-proofing), and
the trivial stowaway rule. Skipping these is leaving free value on the
table because the bundled features include hard ones.

S3. **"Reimplement everything from scratch" is NOT simpler than
per-feature adapt.** A and E are essentially clean adds; reimplementing
them is cargo-culting in reverse. C is a clean adopt because the SDK
already supports it. Only B requires meaningful adapt work; only D
requires a real decision.

S4. **"Just adopt commit 4 to get the stub" is a shortcut.** It ships a
button that does nothing and leaves the modal class + digest as
orphaned dead code in the tree. If we don't ship the modal, we should
delete the modal class + digest, not leave them orphaned. abast's
half-built state on `abast/main` is NOT a model to copy.

S5. **"Adopt rule E -- it's just 7 lines" is a shortcut.** A warn-level
rule that fires on every legitimate test invocation is net-negative UX.
The size of the patch is not the size of the impact.

---

## Moving-parts test

> "If a proposal has more than 2 moving parts, ask: can this be done with 1?"

| Sub-feature | Moving parts | Can it be one? |
|-------------|--------------|----------------|
| A | 4 (variables resolver in engine.py, variables expansion in agent_folders.py, `paths.py`/`compute_state_dir`, YAML rewrites in 12 files) | Yes -- collapse to ONE substitution pass at workflow-load time, applied uniformly to all loaded strings, with one variable namespace. Skip `paths.py` if we keep state in-tree. |
| B | 3 (`DEFAULT_ROLE` sentinel, `agent_type` default-to-sentinel, agent-into-options-factory) | Already minimal. The 3 are interlocking; cannot reduce without losing the no-reconnect property. **Essential complexity.** |
| C | 2 (footer widget, agent attr -> options pass-through) | Already minimal. **Essential.** |
| D | 5 (modal, digest, footer label rename, app.py handlers, computer_info rewrite, diagnostics deletion) | Yes -- the modal and digest can be lifted independently of the footer/diagnostics restructure. The bundled refactor is *accidental* complexity from abast's commit boundary, not from the feature. **Decompose.** |
| E | 1 (rules.yaml entry) | Already minimal but the regex itself has internal moving parts. Verify pattern correctness counts. |

Conclusion: features B, C, E are at minimum moving parts already. Feature
A and feature D each contain accidental bundling that the spec should
unbundle.

---

## Independent verifications (not just trusting historian)

I re-verified the load-bearing claims directly:

| Claim | Verified | Method |
|-------|----------|--------|
| Our `app.py` already has `_activate_workflow` / `_deactivate_workflow` / `main_role` / `_token_store` | YES | `grep -n` on `claudechic/app.py` returned 17 hits across the predicted lines (401, 833-840, 855, 1655, 1787, 1928, 1935, 2168, 2203, 2216, 2250, 2344, 2410, 3731, 3782) |
| Our installed `claude-agent-sdk` accepts `effort=` kwarg | YES | `inspect.signature(ClaudeAgentOptions)` shows `effort: Literal['low','medium','high','max'] \| None = None` |
| `accf332`'s `digest.py` imports symbols already on our base | YES | `should_skip_for_role`, `should_skip_for_phase`, `Rule`, `Injection` all present in `claudechic/guardrails/rules.py` and re-exported from `claudechic/guardrails/__init__.py` |
| `pytest_needs_timeout` regex would false-positive | YES | While running this review, my own `grep -c "pytest"` invocation triggered the existing `no_bare_pytest` rule (same regex family), proving false-positive risk is real, not theoretical |
| `accf332` does not import `003408a`'s `_resolve_against` helper | YES | `git show accf332 -- claudechic/checks/builtins.py` returns empty (file untouched in cluster) |
| `accf332` introduces `effort=` wire-through to `ClaudeAgentOptions(...)` | YES | `git show accf332 -- claudechic/app.py` shows `effort=effort_level,` at line ~1042 (within the options factory) |
| Cluster is non-contiguous on `abast/main` (commits 1-3 then `1d6d432`+`ff1c5ae` then commit 4) | YES | `git log abast/main` shows the interleaving |

These verifications strengthen the historian's report; nothing
contradicted.

---

## Falsification questions, answered per sub-feature

| Sub-feature | Q1 (no context fit) | Q2 (breaks contract) | Q3 (out-of-cluster dep) | Q4 (no user-visible delta) | Q5 (simpler in-tree) | Q6 (regression) | Verdict |
|-------------|------|------|------|------|------|------|---------|
| A | no | **YES** (state location, no migration) | no | no (real benefit) | **YES** (`${CLAUDECHIC_ARTIFACT_DIR}`) | **YES** (state location) | **ADAPT, do not adopt verbatim** |
| B | no | partial (`agent_type` default sentinel breaks `is None` checks) | no | no (latency win on `/tutorial` activation -- if our path reconnects today) | partial (we have most of the machinery) | no | **ADAPT (small delta)** |
| C | no | no | no | no (real -- effort actually wires to SDK) | no (this IS the simplest) | no | **ADOPT** |
| D | no | **YES** (deletes `DiagnosticsModal` we use) | no | **YES** (abast itself stubbed it) | **YES** (`disabled_ids` already does the toggle) | **YES** (loss of `DiagnosticsModal`) | **SKIP modal; consider digest.py only if a caller is identified** |
| E | no | partial (false-positive UX) | no | partial (warn on missing flag is minor) | no | partial (chat noise on legit tests) | **ADOPT IF regex is hardened** |

---

## Carryover-from-prior-revisions check

This is a fresh investigation; no prior spec revision exists for the
abast_accf332_sync run. **However**, the prior run
(`issue_23_path_eval`) produced an executive summary, fork diff report,
and recommendation that the historian and leadership treat as
"input, not authority." Two carryover risks to monitor:

C-Risk-1. The earlier `RECOMMENDATION.md` may have proposed an
integration approach that the user accepted-in-principle but that was
not yet executed when `accf332` landed on abast. If a Specification
axis-agent imports that earlier recommendation as a starting point, it
may also import its assumptions about abast's state. Specification must
re-derive against `abast/main` HEAD = `7dcd488`, not against
`abast/main` as it existed when the prior reports were written.

C-Risk-2. The cherry-pick / revert history (`8abb2f9` cherry of
`003408a`, then `18061ec` revert) is itself a prior revision of the
"adopt abast guardrail/advance-check fixes" work. It was reverted for a
specific reason. The historian's claim that "if accf332 is adopted, the
prerequisites are now satisfied and 003408a becomes safe to re-cherry"
is correct on the dependency analysis but is **scope creep** vs the
user's explicit scope guard ("strictly inside the 4-commit cluster;
flag-don't-chase"). Specification must NOT silently bundle 003408a back
into the cluster. If 003408a is desirable, it is a separate user
decision.

---

## Concrete demands on the upcoming axis-agent specs

Each axis-agent spec must, before claiming completion:

1. State the user-visible "before vs after" for its sub-feature(s) in
   one sentence with a concrete user. If they cannot, the
   recommendation defaults to SKIP.
2. Inventory the contract-surface impact (settings.json schema, MCP API,
   observer protocols, workflow YAML schema, on-disk state file format,
   public exception classes, public type aliases). Even one
   uninventoried contract break is grounds to push the spec back.
3. State the moving-parts count and justify any count > 2.
4. Articulate the simplest *complete* implementation, not the simplest
   partial one (Q4 -- "is simplicity masking incompleteness?").
5. Express the recommendation as
   `(sub-feature, outcome in {adopt, adapt, skip, partial}, blocking-deps)`
   per the Composability contract from leadership_findings.md §9.
6. Stay strictly inside the 4-commit cluster. Flag, don't chase. In
   particular, do NOT silently bundle `003408a` re-application.
7. For any "ADAPT" verdict, name the SPECIFIC narrow delta to apply --
   do not punt with "merge as-needed."

---

## Specific shortcuts I will reject

- "Cherry-pick the cluster, see what conflicts, then resolve." This is
  abdicating the spec to the merge tool. Conflicts in `app.py` are 779
  lines on our side meeting 282 on theirs in the same logical region;
  resolution is a design decision, not a mechanical one.
- "Adopt commit 4 because it's the latest abast state." Commit 4 ships
  a non-functional button; copying it to be "in sync" is cargo-culting.
- "Skip D because abast skipped it." abast left dead code in the tree;
  the answer is to either ship the modal properly OR delete the modal +
  digest. Skipping must be a complete skip.
- "Adopt all template variables to be future-proof." We don't add
  variables we don't use; the spec must enumerate which YAML strings
  *today* would benefit, not aspirationally.
- "Reimplement B on our base from scratch -- our existing
  `_activate_workflow` is similar." If our existing path reconnects the
  SDK and abast's doesn't, "similar" is wrong. Spec must verify.
- "Adopt E -- it's just 7 lines." 7 lines that fire on every
  `pytest tests/test_foo.py` invocation is net-negative.

---

## What "complete + correct + simple" looks like for the recommendation

A recommendation that satisfies my bar:

- Per-sub-feature outcome (A/B/C/D/E) with one-line user-visible delta
  and contract-surface impact summary.
- For each "ADAPT": named narrow delta + named files + named symbols.
- For each "ADOPT": file list + verification that imports/symbols exist
  on our base + test plan.
- For each "SKIP": positive reason (not "abast skipped it") + handling
  of related artifacts (e.g., delete-or-orphan decision for D).
- One unified treatment of substitution mechanisms across A and our
  existing `${CLAUDECHIC_ARTIFACT_DIR}` -- not three uncoordinated
  systems.
- Migration story for any state-location change.
- Explicit exclusion of out-of-cluster commits (especially `003408a`)
  unless the user has separately approved their inclusion.

A recommendation that fails my bar:

- "Adopt the cluster" / "skip the cluster" without per-feature breakdown.
- "Cherry-pick `accf332` then `8f99f03` then `2f6ba2e` then `a60e3fe`"
  with no per-file conflict-resolution plan.
- Anything that quietly re-introduces `003408a`.
- Anything that ships dead code (modal class without UI exposure;
  digest.py without a caller).

---

# v2 Review -- against SPEC.md (post-reframe, six-component bundle)

**Date:** 2026-04-30
**Phase:** project-team:specification (v2 round)
**Reviews:** SPEC.md + SPEC_APPENDIX.md (the six-component A/B/C/D/E/F
spec produced after the 2026-04-29 user redirect that expanded scope and
reframed D from SKIP to ADAPT).

The v1 review above stands. This section adds what changed and what the
v2 spec gets right or leaves underspecified, applying the four questions
freshly.

## TL;DR -- v2 posture

The v2 spec is a substantial improvement over v1's open questions:
component decomposition is clean, "do not cherry-pick wholesale" is
internalized, and per-component contracts/deps are enumerated. Three
classes of issue remain that I would push back on before sign-off:

1. **Underspecified work disguised as locked.** Several "binding"
   constraints defer the actual decision (E's regex; D's source-of-truth
   alignment; D's `get_phase` overstatement); B3 is named as the riskiest
   slice but no conflict map exists; C3 is "follow-up" but flagged as a
   "real functional gap." These are shortcuts disguised as completeness.
2. **Quiet bundling against the user's scope guard.** Decision 6(a) ports
   a ~30-line slice of `003408a` inline as part of A3. The user
   explicitly said "flag, don't chase" on out-of-cluster commits in
   userprompt.md (4); v1 skeptic explicitly named 003408a bundling as
   scope creep. The lock claims user authority; the audit trail for that
   authority should be explicit, not assumed.
3. **Six-component bundle hides three independent strands.** A+B+D+E
   form the agent-self-awareness substrate. C (effort cycling) and F
   (modal restructure) are independent and could ship separately to
   limit blast radius. The "substrate" framing creates apparent cohesion
   that doesn't exist in the dependency graph.

---

## v2 issues, prioritized

### Critical -- block sign-off until resolved

**v2-1. Component E ships without a regex.** SPEC §E names the
contract as `pattern: "<hardened pytest invocation regex>"`. The
constraint says "Regex hardening is mandatory; ship without and the warn
channel pollutes." But the spec then ships without specifying *what
hardening looks like.* The implementer is left to design the regex
unaided.

This is the exact failure mode v1 §S5 flagged. The regex IS the rule.
Saying "must be hardened" is delegating the hard part. Spec must include
the literal regex, OR explicit test cases that the regex must pass and
fail (e.g., "must match `pytest tests/`, must NOT match
`grep -c \"pytest\"`, must NOT match `pytest --timeout=60 ...`").

Pre-existing fact, not addressed: the existing `no_bare_pytest` rule
has the same false-positive bug (v1 verified empirically). Adding E
without fixing or replacing `no_bare_pytest` ships two rules in the same
broken regex family. Spec should either delete `no_bare_pytest` (E
supersedes it), update `no_bare_pytest` to use the same hardened regex,
or document why both coexist.

**v2-2. D's "binding" constraints defer their decisions.** SPEC §D
"Constraints" lists four "compositional landing conditions (binding
regardless of D1 path)":

- Item 1 (source-of-truth alignment): says "align hook reads to the same
  filtered result." No file, no symbol, no owner. Either it's part of D
  (then it's a sub-unit D6, with files/LOC) or it's a prerequisite
  (then it blocks D, with its own scope). "Binding" without scope is
  not binding.
- Item 2 (refresh policy): "pick ONE consistent story." Then,
  parenthetically: "Recommended: at each of the three inject sites...
  and live on every MCP call." A recommendation buried in a constraint
  is not a decision. Lock it.
- Item 4 (`get_phase` rule-count overstatement): "Decide and document:
  leave as-is, or update to use the same projection." A locked spec
  that says "decide later" is incomplete by my bar.

These three items either ship with concrete decisions or move to
follow-up. Both are fine; the current "binding-but-undecided" framing is
not.

**v2-3. Decision 6(a) bundles 003408a-derived work against the user
scope guard.** A3's Files list includes
`claudechic/checks/builtins.py (for A3 -- ctor + factory; ~30 LOC,
sourced from 003408a)`. SPEC §A Dependencies confirms: "A3 requires a
~30-line ctor + factory diff... that is **NOT in `accf332`**. Per locked
Decision 6: port the diff inline as part of A3 adoption in this run."

userprompt.md (4) is explicit: "Flag any other interesting abast
commits encountered in passing -- do not chase them." v1 skeptic §C-Risk-2
named 003408a re-bundling as the most likely violation. Decision 6
appears to override that scope guard.

If the user explicitly approved 6(a) at the 2026-04-29 redirect, fine
-- but the spec should cite the exact user statement that authorized it,
not just "locked Decision 6." Otherwise this is the team overriding the
user's stated scope guard via process language.

### Substantive -- fix or explicitly defer

**v2-4. B3 is the riskiest slice and has no implementation map.** SPEC
§B Constraints: "No wholesale cherry-pick of the +282 `app.py` patch
from `accf332`." Appendix §2 Component B: "B3 deserves its own
line-by-line conflict map." That map does not exist in this spec or
appendix. Implementer reads "hand-merge surgically into existing
methods" and gets no guidance on what specifically to insert where.
Either include the map or split B3 out as a smaller spec round of its
own.

**v2-5. C3 (effort persistence) is "follow-up" but flagged as "a real
functional gap if skipped."** SPEC §C Constraints, verbatim:
"Persistence (C3) is a small follow-up but a real functional gap if
skipped: cost-conscious users on `low` lose their setting on restart."

A real functional gap is in scope or it isn't. The pattern "we can add
it later" is on my own red-flag list. Either:
- Promote C3 into the v2 cluster (it's ~30 LOC per spec), or
- Drop the "real functional gap" framing and accept session-ephemeral
  as the v1 contract.

The current language has it both ways.

**v2-6. MCP tool name inconsistency in §D.** §D "WHAT" and "Interfaces /
contracts" specify `mcp__chic__get_agent_info`. §D "WHY (Agent)" says
"Can call `mcp__chic__get_applicable_rules` mid-session to re-query when
state may have changed." These are different tool names. Pick one (the
locked Decision 5 says `get_agent_info`). Update the WHY paragraph.

**v2-7. C1's `Literal["low","medium","high"]` drops `max`.** v1 §C
verified empirically: `ClaudeAgentOptions` accepts
`Literal['low','medium','high','max'] | None`. The v2 SPEC uses
`Literal["low","medium","high"]` without `max`. C2 says "max=high on
Opus only" which contradicts (or muddles) what `max` even means here.
Either:
- Add `max` to the literal (matches SDK), document Opus-gating in the
  cycler, or
- Document why `max` is intentionally excluded.

The current text equates "max=high on Opus" inside the cycler logic
with omitting `max` from the type. That's a mismatch between the type
and the logic.

**v2-8. D injection has no specified behavior for empty digests.**
`assemble_constraints_block(loader, role, phase) -> str` -- if
`compute_digest` returns 0 active rules and there are 0 advance checks,
what does this return? Empty string? `## Constraints` header with empty
tables? §D Inject contract: "always begins with `## Constraints`."
Always? Even when empty? This adds noise to every prompt for workflows
with no role-scoped rules. Specify the empty-case behavior (recommended:
return empty string; only inject if non-empty).

**v2-9. `get_phase` -> `get_agent_info` migration scope is vague.** §D4:
"Migrate ~50 LOC of mechanical caller edits in 9 bundled workflow role
markdowns and `test_workflow_*.py`." Which 9 workflows? Which test
files? Implementer enumerates from scratch, risking misses. The
9 workflows are likely the bundled set under
`claudechic/defaults/workflows/` -- spec should list them by name and
file path so the implementer's grep is verifiable.

Also: "deprecated when get_agent_info lands; deleted one release later."
What does "deprecated" mean concretely? A logger warning on call? A
toast? A docstring note? Spec should say.

### Tactical -- worth tightening

**v2-10. A4 within-pass ordering undefined.** "Two-pass executor:
partition by manual-flag, run auto pass first, then manual pass." Order
within each pass? Declaration order? Sorted? Failure-aggregating
(run-all-collect) or short-circuit (stop on first failure)? Both are
defensible; pick one.

**v2-11. A3 fail-mode if `workflow_root` is None.** The spec defaults
`cwd` via `params.setdefault("cwd", workflow_root)`. If
`workflow_root` is `None` (e.g., check fired outside an active workflow,
or during unit tests), `subprocess.run(cwd=None)` falls back to the
process cwd silently. That's the exact ambiguity A3 is meant to solve.
Spec should specify: error if `workflow_root` is None, or fall back to
process cwd explicitly with a log line.

**v2-12. B5 validation case-sensitivity / whitespace.** "rejects
manifests where `main_role: default`." What about `Default`, `DEFAULT`,
` default `, or fully-qualified `global:default`? The 5 LOC budget
suggests a single equality check; harden it to lower+strip OR document
what's intentionally not caught.

**v2-13. F's UX flow is muddled.** §F WHY: "the existing `session_info`
button now consolidates JSONL path + last-compaction summary in one
scrollable modal." But CLAUDE.md and the in-tree filename are
`computer_info.py` (mapped to the **sys** button). Is the
`session_info` button removed? Repurposed? Renamed? The data move from
DiagnosticsModal -> ComputerInfoModal is clear; the button-level
navigation that the user actually clicks is not. Trace the user's path
end-to-end (which button -> which modal -> what's visible) in one
sentence.

**v2-14. `whoami` retention rationale absent.** §D: "`whoami` retained
-- degenerate one-shot, unchanged." Why keep it once `get_agent_info`
covers the same data plus more? The v1 review's S4 pattern applies in
reverse: retaining a tool because it's there is not a positive reason.
Either:
- Justify whoami retention with a concrete use case (e.g., "agents
  that need just the name without the markdown overhead"), or
- Add whoami to the deprecation list with `get_phase`.

**v2-15. Token-cost / context-budget impact of D5 not modeled.** §D
re-injects a `## Constraints` block at three sites per agent per phase.
For a 5-phase workflow with two sub-agents, that's 5 phases x 3 agents x
3 sites = 45 injections of the same (or similar) block. Each inject
adds tokens. No cache-friendliness analysis (does the block hash to a
stable cache key?). At minimum: state the upper-bound token cost of an
expected `assemble_constraints_block` output and confirm it's
acceptable for our typical model context.

**v2-16. The 6-component bundle hides 3 independent strands.** Of the
6 components:
- A + B + D + E = the agent-self-awareness substrate (the user's
  reframed intent). Internally coupled.
- C = effort cycling. Independent of all others (per §C Dependencies:
  "C requires the rename `${WORKFLOW_ROOT}` etc. from A1 only if
  workflow YAML refers to effort, which it does not. So C is
  effectively decoupled.")
- F = modal restructure. Independent (per §F Dependencies:
  "Independent of A, B, C, D, E.")

Bundling C and F into the same merge as the substrate work increases
blast radius (one bad merge backs out everything) without buying
coupling that doesn't exist. Recommendation: ship C and F as separate
PRs, even if planned together. The "agent self-awareness" framing is
real for A/B/D/E; it doesn't apply to C or F.

---

## What v2 gets right (worth preserving)

- Per-component decomposition with explicit dependencies (no return to
  the v1 anti-pattern of "adopt the cluster").
- Explicit "do not cherry-pick wholesale" guards, with named files for
  surgical inserts.
- Naming convention shift to `abast` / `sprustonlab` (away from
  "ours" / "theirs").
- "Out of scope" + "Follow-up" + "Closed out" sections that draw a
  clean line around the run.
- Decision 2 lock on "effort" verbatim (matches SDK vocabulary; resists
  paraphrase drift).
- D-reframe modal-skip is preserved; SPEC explicitly enumerates what
  is NOT in scope from `accf332`'s D bundle.
- F's "zero info loss" via verbatim absorption of
  `jsonl_path` + `last_compaction` readers (clean approach).

---

## v2 sign-off bar

A v3 spec that addresses these would clear my bar:

1. Concrete regex (or test cases) for E.
2. `no_bare_pytest` disposition (delete / update / coexist) stated.
3. D's four "binding" constraints either lock decisions or move to
   prerequisites/follow-up.
4. Explicit user-citation for Decision 6(a)'s 003408a slice (or
   follow-up demotion).
5. B3 conflict map included, OR B3 split out into its own round.
6. C3 either in scope or its "real functional gap" framing dropped.
7. MCP tool name unified.
8. C1 literal aligned with SDK or `max` exclusion documented.
9. D empty-digest behavior specified.
10. D4 caller list enumerated with exact file paths.
11. F user-path traced end-to-end.
12. C and F either justified as bundled with the substrate, or split
    into separate PRs.

The remaining tactical items (v2-10/11/12/14/15) are improvements but
not blocking.

---

*End of skeptic_review.md v2 section. Reporting completion to coordinator
(claudechic) via message_agent.*
