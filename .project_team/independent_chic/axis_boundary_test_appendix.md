# Appendix — Boundary CI Test Rationale

**Companion to:** `axis_boundary_test.md`
**Audience:** future spec authors, code reviewers, lens leads, the
Coordinator, and anyone re-litigating a decision recorded here.
**Mode:** rationale, alternatives, trade-offs. **Not operational.**
The Implementer / Tester MUST be able to execute the operational
spec without reading this file.

---

## 1. Why this axis exists at all

L3 forbids claudechic from writing inside `.claude/`. The Skeptic's
risk evaluation (§1, R1–R5; §10 top-3 risk #2) named the boundary
regression as the dominant L10.c-class lost-work risk for this
restructure. The Composability lens spec (§4 INV-6 / Seam-E)
designates a CI-resident boundary test as the load-bearing
enforcement.

A7 then softens L3: primary-state writes remain forbidden inside
`.claude/`, but non-destructive-incidental writes are permitted.
This softening is what makes the test interesting. A path-string
regex would have sufficed under strict L3; under A7 it categorizes
permitted writes as violations. The registry-based classification
in the operational spec is the response.

The boundary test is one of two CI-grade enforcements this run
needs (the other is the override-resolution test owned by the R3
axis-agent — composability spec §6 INV-1, INV-2, INV-4, INV-5,
INV-7). Both are required at implementation-phase exit.

---

## 2. Why a YAML registry, not a decorator-based registry

The two natural shapes for a write-site registry:

### 2.1 YAML registry (chosen)

A standalone YAML file at `tests/boundary/write_sites.yaml`. The
analyzer loads it, walks `claudechic/`, matches sites to entries.

**Advantages:**

- **PR review legibility.** A new write site adds a YAML entry whose
  diff is unambiguous: classification, rationale, path pattern. The
  reviewer sees the classification call as a discrete change in the
  PR.
- **Site/entry decoupling.** The registry can carry information that
  the call site doesn't (path-pattern templates, rationale text,
  `is_dotclaude_directory_entry` flag). A decorator can do this with
  arguments, but the call site becomes verbose.
- **Static-only enforcement is feasible.** No runtime import needed
  to enumerate the registry. The static analyzer parses the YAML
  and walks the AST in one pass; there is no "load the whole module
  graph to discover decorated functions" step.
- **Existing pattern in the codebase.** `tests/test_encoding_static.py`
  is precedent: a static AST walker that enforces a codebase-wide
  invariant without runtime instrumentation.
- **Stable site_id across moves.** The site_id is the durable
  handle. A decorator on a moved function silently moves with the
  function; a YAML entry stays put and forces the developer to
  update `file`/`function`/`line` consciously, surfacing the move
  in review.

**Disadvantages:**

- Two-place change for new write sites: the call site AND the
  registry. Mitigation: the static analyzer fails CI if the two are
  out of sync (§4.1.5 unregistered → §6.1 message; §4.1.6 stale →
  §6.3 message). The error is loud and self-explanatory.
- Drift risk for `line` and rationale. Mitigation: `line` is
  informational, not load-bearing for matching; matching is by
  `(file, function, call)` triple.

### 2.2 Decorator registry (rejected)

`@claudechic_write_site(classification="primary-state", path="${HOME}/...")`
on the function whose body contains the write call.

**Why rejected:**

- Tightly couples test infrastructure to production code (every
  write-callsite has a decorator that imports from
  `tests/boundary/`). LEAF discipline (per `CLAUDE.md` for
  `claudechic/checks/`, `claudechic/guardrails/`, `claudechic/hints/`)
  argues against test-package imports leaking into production
  modules.
- Decorators on functions don't capture the granularity of multi-call
  sites. `_save` in `config.py` performs `mkdir`, `mkstemp`, and
  `os.replace` — three classifiable operations with three different
  registry entries. A function-level decorator can only carry one
  classification.
- A decorator on the call expression itself is not a Python
  primitive (no `@` on expressions). Wrapping the call in a helper
  (`record_write(Path.write_text)(path, content)`) replaces every
  call site with a helper call, increasing churn for no enforcement
  gain.
- Static analysis of decorators requires either AST evaluation
  (then we're back to AST-walking, which the YAML approach already
  does) or runtime introspection (then a third-party can monkey-
  patch the decorator off, defeating CI).

### 2.3 Pure runtime instrumentation (rejected as primary)

Monkey-patching `Path.write_text` and friends in a test fixture,
exercising claudechic, recording every write.

**Why rejected as primary, retained as supplement:**

- Coverage gap. Code paths that aren't exercised by the runtime
  test go uninspected. claudechic has many off-the-happy-path
  branches (e.g., the legacy-rename branch at `config.py:30-32`,
  fired only when `_OLD_CONFIG_PATH` exists) that the static pass
  catches but a runtime pass would miss without specific test
  setup.
- Slower CI. Each runtime test must boot the app, exercise paths,
  tear down. The static gate is sub-second on a developer's
  laptop.
- Harder to reason about. A runtime failure says "this code path
  wrote here"; a static failure says "this expression at this line
  writes there." The static failure is closer to the source of
  truth.

The runtime supplement (§4.2 of the spec) catches what the static
pass cannot: dynamic paths the analyzer can't resolve (e.g., a path
constructed via a config-driven template). Hybrid is strictly
better than either alone, but the static gate is the authoritative
enforcement.

---

## 3. Why detection is hybrid (static + runtime)

The Skeptic's R1 enumerates seven detection mechanisms (R1's "What
the lint must catch concretely" list). Static AST walking covers
the first six; the seventh (tool-emitted writes from spawned agents)
requires a runtime guard on the SDK's `can_use_tool` callback.

This boundary-test axis-agent's scope is claudechic's own write
sites, NOT spawned-agent tool calls. Tool-emitted writes are
intercepted by the existing `can_use_tool` callback machinery in
`claudechic/agent.py`; that mechanism is not within R5's enforcement
surface (R5 is about claudechic's own writes — the SDK callback
is its own concern, not "did claudechic write to .claude").

So the spec scopes the test to claudechic's source code under
`claudechic/`, and uses static + runtime to cover what the source
code can do statically and what it does at runtime. Tool-emitted
writes are out of scope; the Skeptic's R3 (Workflow phase docs
containing `.claude/rules/...` strings) is out of scope for this
axis (the doc-string sweep is owned by either the R6 axis-agent or
the doc lens — not enumerated here).

---

## 4. Why the registry has two classification values, not three or one

A7 names exactly two: primary-state and non-destructive-incidental.
A third value (e.g., `pre-existing-worktree-mechanism` for the
git.py:301 symlink) was considered to keep A4's symlink prohibition
strict and the worktree symlink permissively exempt.

**Why two values won:**

- A7's text is binary. Adding a third classification re-litigates
  A7 in a way the user explicitly closed.
- The worktree-symlink case fits cleanly under
  `non-destructive-incidental` once the §8 disambiguation
  predicates are in place: the symlink is at the `.claude`
  *directory entry* of a fresh worktree (parent is the worktree
  root, not a `.claude/` ancestor), so it's not "inside `.claude/`"
  in the A4 sense.
- The `is_dotclaude_directory_entry: true` flag carries the extra
  signal where it's needed (one site, today; possibly zero sites
  post-restructure if R8 is later replaced by a cross-platform
  alternative). Adding a third classification value to encode the
  same fact is more surface area for less precision.

**Why two values, not one:**

- Collapsing to "every write must be under `.claudechic/`" is
  exactly the strict L3 reading that A7 explicitly softened. Such
  a test would block whatever mechanism the R6 axis-agent picks if
  R6 chooses an A7-permitted in-`.claude/` write. The boundary
  test's job is to encode A7 faithfully — two values is the
  minimum that does so.

---

## 5. Why `non-destructive-incidental` requires four conditions

The four conditions in §2.1.2 (newly-created, claudechic-named,
regular file, cross-platform) are the operationalization of A7's
plain-English "non-destructive, claudechic-owned, non-colliding,
cross-platform" softening. Each maps directly:

- "newly-created" → the write creates the path; it does not
  open an existing file in write mode (which could be a Claude-
  owned file the user happened to have).
- "claudechic-named" → basename is unambiguously claudechic's,
  preventing collision with future Claude additions.
- "regular file" → not a symlink (A4 absolute prohibition; restated
  here for the analyzer's matrix).
- "cross-platform" → no POSIX-only call kinds for this category;
  Windows users are not silently regressed.

A site that fails any one of the four conditions is not
non-destructive-incidental. A site that satisfies all four is.

---

## 6. Why the registry holds rationale (and why "operational, not
   historical")

A registry entry's `rationale` field is a one-sentence operational
statement: "why is this site classified this way?" — not "why does
this code exist?" or "what is the history of this design?"

Operational rationale: "primary-state because phase context is
claudechic-owned session-state derivative." That's enough to make
the classification self-checking when reviewing a registry diff.

Historical rationale ("we used to write to `.claude/phase_context.md`
because Claude Code reads it as system prompt context, but A7
softened the boundary so we kept the write through the transition")
belongs in this appendix, not in the registry. Registry entries
must be useful to a reviewer reading the YAML in isolation.

---

## 7. Why `line` is informational, not load-bearing

Line numbers shift with every refactor. If the static analyzer
matched on `(file, function, line)`, every cosmetic change would
trigger a registry-entry update. If the analyzer matched on file +
line alone, function renames would silently re-key entries.

The chosen triple `(file, function, call)` is stable across line
shifts and call-kind-preserving refactors. It does drift on file
moves and function renames; that drift is detected by the
unregistered-site failure (§6.1) on the new path and the stale-
entry failure (§6.3) on the old path, surfacing the move loudly in
review.

This trades a small amount of false-fail noise (after a move,
there's a CI run where both failures fire, and the developer
updates the entry) for stability against the dominant churn case.

---

## 8. Why the worktree symlink is non-destructive-incidental

The Composability spec's §2 R8 disambiguation, the Skeptic's R6
table row 1 ("Symlink `.claude/rules/claudechic` → `~/.claudechic/
rules/`"), and A4's "no symlinks anywhere in the mechanism"
appear to collide on the worktree symlink at git.py:301. The
collision dissolves once one is precise about what "inside
`.claude/`" means.

Precise reading: the worktree symlink's *path* is
`<worktree_dir>/.claude` — the parent is the worktree directory
itself. There is no `.claude/` ancestor of this path. The symlink
IS the `.claude/` directory entry of its parent (the new
worktree). It is not "inside" any pre-existing `.claude/`
directory.

A4's prohibition reads "no symbolic links anywhere in the
mechanism" with R6 as its referent (per the Composability spec
§2's R8/A4 disambiguation: "A4's 'no symlinks anywhere in the
mechanism' applies to R6 (agent-awareness delivery) specifically").
The worktree symlink is R8 (state propagation), not R6.

The §8 predicates in the operational spec encode this distinction
mechanically: predicate 8.1 (the directory-entry case) is the
worktree exemption; predicate 8.2 (the strictly-inside case) is the
A4 prohibition; predicate 8.3 (target points in) is unrestricted.
The static analyzer determines which predicate applies by examining
the path expression at the symlink call site, not by inspecting the
filesystem at test time.

Result: the worktree symlink is registered as
`non-destructive-incidental` with `is_dotclaude_directory_entry:
true`, and it passes the test. Any future symlink whose path lies
inside a `.claude/` directory fails predicate 8.2 and the test,
regardless of registry classification.

---

## 9. Why `path_unlink` is in scope

A registered classification on a write site naturally includes the
`mkdir`, `mkstemp`, `replace`, and `write_text` calls that produce
the file. It is less obvious that `unlink` calls (the `_remove_phase_
context` path at app.py:1925-1928 and the stale-cleanup at
app.py:1867) should be in scope.

The spec includes them because deleting a file from inside `.claude/`
is itself a write — a directory-entry modification. Without scope
coverage, claudechic could pass the boundary test while still
mutating `.claude/` via deletes. The Skeptic's R1 lint enumeration
does not include `unlink`; the Composability spec's R5.1 says
"every claudechic write site MUST be classified" — which the
operational spec interprets to include any directory-entry mutation,
including unlinks.

Practically: the four `app.phase_context.*` registry entries cover
the lifecycle (mkdir, write, unlink-stale, unlink-deactivate). After
Group B + Group D move phase-context delivery to the R6 mechanism,
all four entries either delete (if the new mechanism doesn't use
the filesystem) or migrate to `.claudechic/`-shaped path patterns
(if the new mechanism stores phase context as a file).

---

## 10. Trade-offs in registry maintenance

### 10.1 Manual entry vs auto-detection

A manual-entry registry forces the developer to think about
classification when adding a write site. The classification choice
goes through code review.

An auto-detected registry (e.g., "any write under `.claudechic/` is
implicitly primary-state; any write under `.claude/` is implicitly
forbidden unless tagged") would skip the classification step and
miss A7's softening.

The manual-entry approach is the chosen one. The cost is one YAML
entry per write site; the benefit is that classification is
a discrete reviewable decision, not a path-string heuristic.

### 10.2 Per-call vs per-function granularity

Registry entries are per-call, not per-function. A function with
three writes has three entries. The cost is registry verbosity; the
benefit is precise classification (a function might have one
primary-state write and one non-destructive-incidental write, e.g.,
if the R6 mechanism's implementer picks a hybrid).

The granularity choice tracks the analyzer's matching key
`(file, function, call)`. Aggregating to per-function would lose
the call-kind dimension and force the registry to either over-
specify (single classification across multiple calls, accepting
false positives) or under-specify (no classification, accepting
unregistered-site fails on every call).

### 10.3 Registry vs distributed comments

An alternative was: each write site carries a `# boundary-allowlist:
non-destructive-incidental` comment, and the analyzer reads the
comment. This is the "in-file annotation" pattern.

Rejected because:

- The annotation is at the call site; the rationale and path-
  pattern are not. The reviewer reading the comment doesn't see
  what classification was justified.
- Comment formats drift (`# boundary-allowlist:foo`,
  `# allowlist: foo`, `# boundary: foo` — the analyzer must accept
  one canonical form).
- Comments are easy to add (low friction); the friction is the
  point. Classification should be reviewable, not nodded-through.

---

## 11. Why two classification values are sufficient for R6
   integration

The agent-awareness axis-agent (R6) has not chosen its mechanism at
the time of this writing. The spec must be agnostic to whichever
mechanism R6 picks — including the A7-permitted in-`.claude/` write
option (Composability spec §3 R6.6 third bullet).

The two classification values cover all R6 mechanism choices:

- SDK `append_system_prompt` — no filesystem write; no registry
  entries.
- SDK SessionStart hook reading from `~/.claudechic/context/...` —
  no `.claude/` write; primary-state read of `.claudechic/` files.
- SDK PreToolUse hook on Read — no filesystem write; in-memory
  per-agent-session tracking.
- A7-permitted non-destructive write at `.claude/<chic-named-file>`
  — `non-destructive-incidental`, registered, passes the test if
  the four conditions hold.

In every case, the R6 axis-agent's deliverable is "name your write
sites and add them to the registry." The boundary test enforces
the same rules regardless of which combination R6 picks. The §11
integration protocol in the operational spec encodes this
agnosticism.

---

## 12. Vision / STATUS / spec inconsistencies surfaced (per A1)

Three items found during the boundary-test analysis. None require
re-litigation; flagging here for the Coordinator.

### 12.1 STATUS A4's "no overwrites of Claude-owned settings" — list is not enumerated

A4 says: "Prohibited: overwriting any Claude-owned settings/config
file inside `.claude/`." The text does not enumerate what files
qualify. The Composability spec §3 R5.2 cites "e.g., `settings.json`,
`settings.local.json`" with no canonical list.

The boundary-test operational spec's §7 enumerates a list (loaded
from `tests/boundary/claude_owned_files.yaml`), proposing
`settings.json`, `settings.local.json`, `.credentials.json`,
`history.jsonl`, and several read-only paths. The list is grounded
in `claudechic/help_data.py`, `claudechic/usage.py`, and
`claudechic/sessions.py` (the existing read-call sites are the
informative source).

This is not a vision/STATUS error; it is an under-specification.
The spec resolves it by externalizing the list (so it can grow
without code changes). If the Coordinator (or the user) wants a
shorter or longer canonical list, the change is to
`claude_owned_files.yaml`, not to this spec.

### 12.2 Composability spec §6 INV-7 wording vs ownership split

INV-7 says "the boundary test (INV-6) and the override-resolution
tests (INV-1, INV-2, INV-4, INV-5) MUST exist in the test suite at
the close of the implementation phase." The phrasing implies a
single owner.

In practice, INV-6 is owned by this axis-agent; INV-1/2/4/5 are
owned by the loader-resolution axis-agent (per `axis_loader_
resolution.md`). The two test packages are independent (per §14 of
this spec).

The operational spec's §14 documents the split. Not blocking; flag
to the Coordinator that INV-7 is a multi-axis deliverable, not a
single-axis one.

### 12.3 vision §"`.claude/`-write sites to relocate" omits `hits.jsonl`

The vision File-move inventory enumerates three claudechic state-
file write sites (config, hints state, phase context) but omits
`<repo>/.claude/hits.jsonl` (the guardrail audit log, constructed
in `app.py:1492` and written by `claudechic/guardrails/hits.py:52`).

The Composability eval §1 mentions it explicitly (cited as `app.py:
~1492`), and the boundary registry's §10 includes it as
`guardrails.hits.record.append`. So the spec phase has it captured.

This is a vision-document under-enumeration, not an error in the
binding constraints. Group B's boundary-relocation deliverable
should add `hits.jsonl` to its move list explicitly. Flag to the
Coordinator: when assembling the operational spec from the lens
spec inputs, ensure Group B's task list includes the `hits.jsonl`
move alongside the three sites in the vision inventory.

---

## 13. A1 — what this axis-agent did NOT silently work around

Per A1: surface, don't work around. Three items the spec phase
makes explicit rather than absorbing:

- **A7's softening is ENCODED, not RELAXED.** The `non-destructive-
  incidental` classification is permitted; the four conditions in
  §2.1.2 keep the relaxation tightly bounded. A future contributor
  cannot quietly tag any write as `non-destructive-incidental` to
  bypass the test — the conditions are mechanically enforced in the
  static analyzer.
- **The R5.3 disambiguation is mechanically encoded** (§8 predicates),
  not asserted as a comment. The worktree exemption survives because
  the predicate is precise about parent vs ancestor; if a future
  refactor moves the worktree symlink to a path that fails predicate
  8.1, the test fails — exactly as A4 wants.
- **The R6 axis-agent's freedom is preserved.** This spec does not
  prescribe R6's mechanism; the §11 integration protocol accepts
  whatever R6 picks, validates it against the same rules.

---

## 14. Failure modes this test does NOT catch (and why)

Honesty about the test's coverage gaps:

- **Tool-emitted writes** (Skeptic R3). An agent in a workflow
  phase whose role markdown says "write context_docs into
  .claude/rules/" calls `Write` on a `.claude/` path. The boundary
  test scans claudechic's source, not phase markdown. Mitigation:
  the runtime guard in `can_use_tool` (already in `claudechic/
  agent.py`); tightening that guard is the R6 axis-agent's
  problem (per Composability spec §3 axis 6 / Skeptic R3
  mitigation).
- **Subprocess writes** (Skeptic R1 item 6). A `subprocess.run(
  ["sh", "-c", "echo x > ~/.claude/foo"])` is heuristically
  flagged (per §4.1.2 row `subprocess_redirect`) but not
  authoritatively. claudechic does not currently perform subprocess
  writes into `.claude/`; if a future contributor adds one, the
  heuristic is a *warning*, not a failure. A subsequent code-review
  is the gate.
- **Indirect writes via third-party libraries.** A library
  claudechic depends on writes into `~/.claude/...` on its own
  initiative. The static analyzer doesn't see into third-party
  packages. The runtime supplement catches the actual filesystem
  write (since the monkey-patches are at `pathlib.Path` /
  `os.replace` / etc., they fire regardless of caller). So the
  hybrid catches this case where pure static would miss it; the
  runtime test must exercise the relevant code path.
- **Race conditions / TOCTOU.** A write that resolves correctly at
  test time but races with another writer in production. Not in
  scope; this is a concurrency test, not a path-classification test.

The test's promise is: *every claudechic-owned write call site
under `claudechic/`, classified at code-review time, is enforced to
respect L3+A4+A7.* That is the load-bearing property; the gaps
above are out of scope for this axis.

---

## 15. Reversal triggers

If any of the following becomes true, the operational spec should
be revisited:

- A future user-provided amendment relaxes A4's symlink prohibition
  for a specific R6 mechanism. The §8 predicates assume A4 is
  absolute; relaxing it requires re-reading the predicate logic.
- A future user-provided amendment expands the protected filename
  list in §7 in a way that overlaps with `.claudechic/` paths. (No
  current overlap; flagging as a reversal trigger.)
- The static analyzer's resolved-path heuristic (§4.1.3) misses a
  pattern that becomes common in claudechic code (e.g., a new
  `Path(...) / config_template_string` idiom). Mitigation: extend
  the analyzer; not a spec change.
- Group B's boundary-relocation lands a path layout that does NOT
  match `.claudechic/<...>` (e.g., the loader-resolution axis-agent
  picks `<repo>/.config/claudechic/...` instead). The operational
  spec's path-pattern checks need to absorb the alternative root.

None of these are anticipated; they are documented as reversal
triggers per the spec's L14 discipline.

---

*End of axis_boundary_test_appendix.md.*
