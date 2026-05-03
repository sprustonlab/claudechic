# Axis-spec — Boundary CI Test (R5 / INV-6)

> **REFERENCE ARCHIVE — operational content has been merged into `SPEC.md` §9 and §11. This file is preserved for trace; not for implementation reading.**

**Axis owner:** Test Engineer (boundary-test axis-agent)
**Lens lead:** Composability
**Phase:** Specification (axis-agent operational spec)
**Audience:** Operational-spec authors, Implementer agents, Tester agents
**Mode:** Operational only. RFC-2119 MUST/SHOULD/MUST-NOT throughout.
Rationale, alternatives, and trade-offs live in the sibling appendix
`axis_boundary_test_appendix.md` (per L14).

This spec defines the CI boundary test that enforces L3 (no claudechic
primary-state writes inside `.claude/`) softened by A7 (non-destructive
incidental writes inside `.claude/` are PERMITTED) and the A4 absolute
prohibitions (no symlinks inside `.claude/`; no overwrite of Claude-owned
settings files).

This spec does NOT:
- Choose the agent-awareness mechanism (R6 axis-agent owns).
- Choose the loader-resolution mechanism (R3 axis-agent owns).
- Choose the artifact-dir layout (R7 axis-agent owns).
- Re-litigate L3, A4, or A7.

---

## 1. Scope

The test enforces three properties simultaneously:

- **P1 (R5.1, INV-6):** Every claudechic write site classified as
  `primary-state` MUST resolve to a path under one of the three
  `.claudechic/` tier roots (package = `claudechic/defaults/...`, user =
  `~/.claudechic/...`, project = `<repo>/.claudechic/...`). No
  primary-state write resolves under `.claude/`.
- **P2 (A4 — overwrite prohibition):** No claudechic write site MAY open
  a Claude-owned settings file inside `.claude/` for write/append/r+
  modes. The Claude-owned set is enumerated in §7.
- **P3 (A4 — symlink prohibition):** No claudechic code MAY create a
  symbolic link whose path resolves *inside* `.claude/` (i.e., the
  symlink lives strictly below a `.claude/` directory). Symlinks whose
  *target* points into `.claude/` are unrestricted (read direction).
  The pre-existing worktree symlink at `features/worktree/git.py:299`
  is exempt under the rule in §8.

R5.5 (reads from `.claude/` are unrestricted) is NOT enforced by this
test; the test MUST NOT flag read calls. See §9.

---

## 2. Classification model (binding)

- **2.1 [MUST]** Every claudechic call site that writes to the
  filesystem MUST be classifiable as exactly one of:
  - `primary-state` — config files, hint state, phase context,
    session-state derivatives, audit logs, artifact-dir contents, and
    any other claudechic-owned file produced during normal operation.
  - `non-destructive-incidental` — newly-created, claudechic-named
    files inside `.claude/` that satisfy ALL of:
    1. The file is created (not opened on an existing path) by
       claudechic code.
    2. The basename is unambiguously claudechic-owned (e.g., starts
       with `claudechic`, `_chic`, `chic_`, or matches a registered
       claudechic-owned filename pattern).
    3. The file is a regular file (not a symlink).
    4. The write is cross-platform (no POSIX-only primitives like
       `os.symlink` for the path itself).
- **2.2 [MUST]** A site MAY NOT carry both classifications. If a site's
  classification is genuinely ambiguous, the registry entry MUST split
  the site into two entries (e.g., one for the path-construction call
  and one for the actual write) so each is unambiguous.
- **2.3 [MUST]** "Write site" means any call into the filesystem that
  creates a directory entry, modifies a file's contents, replaces a
  file, or creates a symbolic link. The non-exhaustive matrix the
  static analyzer MUST recognize is in §4.2.
- **2.4 [MUST-NOT]** A path-string heuristic alone (e.g., "anything
  whose path contains `.claude/` is forbidden") MUST NOT be used as
  the classification mechanism. Per A7, some `.claude/`-resident
  writes are explicitly permitted.

---

## 3. Registry — schema, location, maintenance

### 3.1 Location and shape

- **3.1.1 [MUST]** The registry lives at
  `tests/boundary/write_sites.yaml` in the repo. The path is canonical;
  the test loader expects it.
- **3.1.2 [MUST]** The registry is a single YAML file containing a
  top-level mapping with the keys `version: 1` and
  `sites: <list of site entries>`.
- **3.1.3 [MUST]** Each site entry has exactly the keys below, in this
  shape:
  ```yaml
  - site_id: <stable string, unique within file>
    file: claudechic/<path>.py
    line: <integer line number — best-effort, not load-bearing>
    function: <fully-qualified Python name, e.g. "config._save">
    call: <one of: write_text | write_bytes | open_w | open_a | \
            open_r_plus | os_replace | os_rename | os_symlink | \
            path_symlink_to | path_mkdir | path_touch | path_unlink | \
            tempfile_mkstemp | shutil_copy | shutil_move | \
            subprocess_redirect>
    classification: <primary-state | non-destructive-incidental>
    path_pattern: <Python f-string-like template describing the
                    resolved path, e.g.
                    "${HOME}/.claudechic/config.yaml"
                    or "${repo}/.claude/<sentinel>"  >
    rationale: <one short sentence — operational, not historical>
    accepts_dotclaude: <true | false>   # MUST be true only for
                                         # non-destructive-incidental
                                         # entries; flags that the
                                         # resolved write path is under
                                         # a .claude/ ancestor
    is_dotclaude_directory_entry: <true | false>   # §8.1 — symlink
                                                    # AT the .claude
                                                    # directory entry
                                                    # (parent NOT a
                                                    # .claude/ ancestor)
    is_dotclaudechic_directory_entry: <true | false>  # §10 (SPEC.md) —
                                                       # symlink AT the
                                                       # .claudechic
                                                       # directory entry
                                                       # (parent NOT a
                                                       # .claude/
                                                       # ancestor; thus
                                                       # accepts_dotclaude
                                                       # MUST be false)
    is_claudechic_prefixed_rules_file: <true | false>  # §8.6 — write
                                                        # path's basename
                                                        # matches
                                                        # claudechic_*.md
                                                        # AND parent is
                                                        # ${HOME}/.claude/rules
    is_claude_rules_dir_mkdir: <true | false>  # §8.6 — idempotent
                                                # mkdir of
                                                # ${HOME}/.claude/rules
                                                # itself (Claude-Code-
                                                # discovered standard
                                                # directory)
  ```
  The schema is **extensible**: predicate flags like `is_*` MAY be added in future revisions; the boundary lint MUST tolerate unknown predicate keys (treat as informational metadata). The two flags `accepts_dotclaude` and `classification` are the load-bearing classification axes; the `is_*` flags are *which* permitted predicate the entry uses.
- **3.1.4 [MUST]** `site_id` MUST be unique across the file. The
  recommended naming convention is `<module>.<function>.<purpose>`
  (e.g., `config.save.user_config`, `hints.state.save.lifecycle`).
- **3.1.5 [MUST]** A site whose `accepts_dotclaude` is `true` MUST
  have `classification: non-destructive-incidental`. A site with
  `classification: primary-state` MUST have `accepts_dotclaude: false`.
- **3.1.6 [MUST]** A site whose `is_dotclaude_directory_entry` is
  `true` MUST also have `accepts_dotclaude: true` and SHOULD include
  a comment block in the YAML documenting why the exemption applies
  (the worktree symlink case in §8).
- **3.1.7 [MUST]** A site whose `is_dotclaudechic_directory_entry` is
  `true` MUST have `accepts_dotclaude: false` (the symlink lives at
  `<worktree_dir>/.claudechic`; parent is the worktree root, NOT
  inside any `.claude/` ancestor; classification is still
  `non-destructive-incidental` because the write is the directory-
  entry symlink case per SPEC.md §10.3).
- **3.1.8 [MUST]** A site whose `is_claudechic_prefixed_rules_file` is
  `true` MUST have `accepts_dotclaude: true` (writes are inside
  `${HOME}/.claude/rules`) AND `classification:
  non-destructive-incidental`. The `path_pattern` MUST resolve to a
  basename matching `^claudechic_[^/]+\.md$` with parent exactly
  `${HOME}/.claude/rules`.
- **3.1.9 [MUST]** A site whose `is_claude_rules_dir_mkdir` is
  `true` MUST have `accepts_dotclaude: true` (the mkdir target is
  inside `${HOME}/.claude/`), `call: path_mkdir`, and
  `classification: non-destructive-incidental`. The `path_pattern`
  MUST resolve to exactly `${HOME}/.claude/rules`.

### 3.2 Maintenance protocol

- **3.2.1 [MUST]** Whenever a developer adds a new write call site
  inside `claudechic/`, they MUST add a corresponding entry to
  `tests/boundary/write_sites.yaml` in the same PR.
- **3.2.2 [MUST]** The boundary test (§5) MUST fail when the static
  analyzer detects a write call site under `claudechic/` that has no
  matching registry entry. The failure message format is fixed in §6.
- **3.2.3 [MUST]** When a registered write site is moved (file
  rename, function rename, line shift), the developer MUST update
  `file`, `function`, and `line` in the registry entry. The
  `site_id` MUST remain stable across moves (the site_id is the
  durable handle).
- **3.2.4 [MUST]** When a registered write site is deleted, its
  registry entry MUST also be deleted in the same PR.
- **3.2.5 [SHOULD]** Each PR that adds or changes write sites SHOULD
  cite the registry entry's `site_id` in the PR description. The
  test does not enforce this; reviewers do.

---

## 4. Detection mechanism — static analyzer (gate)

The detection mechanism is **hybrid**: a static analyzer is the gate
(required, blocks merge); a runtime supplement covers dynamic-path
cases the static pass cannot resolve.

### 4.1 Static analyzer — required

- **4.1.1 [MUST]** A Python module `tests/boundary/scan.py` MUST walk
  every `*.py` file under `claudechic/` (excluding
  `claudechic/defaults/`, see §4.4) and parse each via the stdlib
  `ast` module.
- **4.1.2 [MUST]** The walker MUST recognize the following call
  shapes as write sites and emit a candidate site descriptor for each:

| ast pattern | `call` value emitted |
|---|---|
| `Call(func=Attribute(attr="write_text"), ...)` | `write_text` |
| `Call(func=Attribute(attr="write_bytes"), ...)` | `write_bytes` |
| `Call(func=Name("open"), args=[..., Constant("w"\|"wt"\|"wb"\|"x")])` | `open_w` |
| `Call(func=Name("open"), args=[..., Constant("a"\|"at"\|"ab")])` | `open_a` |
| `Call(func=Name("open"), args=[..., Constant("r+"\|"w+"\|"a+")])` | `open_r_plus` |
| `Call(func=Attribute(attr="open"), args/kwargs include mode in {"w","wt","wb","x","a","at","ab","r+","w+","a+"})` (i.e., `Path.open(...)`) | `open_w` / `open_a` / `open_r_plus` |
| `Call(func=Attribute(value=Attribute(attr="os"), attr="replace"))`, `Call(func=Attribute(attr="replace"))` resolved as `os.replace` | `os_replace` |
| `Call(func=...attr="rename")` for `os.rename` / `Path.rename` | `os_rename` |
| `Call(func=...attr="symlink_to")` | `path_symlink_to` |
| `Call(func=...attr="symlink")` for `os.symlink` | `os_symlink` |
| `Call(func=...attr="mkdir")` | `path_mkdir` |
| `Call(func=...attr="touch")` | `path_touch` |
| `Call(func=Attribute(attr="mkstemp"))` for `tempfile.mkstemp` | `tempfile_mkstemp` |
| `Call(func=...attr="copy"\|"copy2"\|"copyfile"\|"copytree")` for `shutil.*` | `shutil_copy` |
| `Call(func=...attr="move")` for `shutil.move` | `shutil_move` |
| `Call(func=Name("subprocess_run"\|"run"\|"check_call"\|"Popen"))` whose argv contains `>`, `tee`, `cp`, `mv`, `touch`, `mkdir`, `ln`, OR a redirect operator that targets a `.claude/`-shaped path | `subprocess_redirect` (heuristic; flagged for human review only) |

- **4.1.3 [MUST]** For each emitted candidate, the analyzer MUST
  attempt to resolve the *path argument* by best-effort static
  evaluation: literal strings, simple `Path(...) / "<literal>"`
  chains, simple module-level constants, and `Path.home() / ...`
  / `Path.cwd() / ...` chains. Unresolvable paths MUST NOT cause
  the test to fail; instead, the analyzer MUST emit a warning row in
  the test output and rely on the registry to classify the site.
- **4.1.4 [MUST]** The analyzer MUST match each candidate against
  the registry by `(file, function, call)` triple. A match requires
  exact `file` equality, exact `function` qname equality, and exact
  `call` value equality. `line` is informational and is NOT used for
  matching.
- **4.1.5 [MUST]** For each candidate:
  - If a registry match is found AND `classification ==
    primary-state` AND the resolved path is under any `.claude/`
    segment → **FAIL** with the unrouted-primary-state message in §6.
  - If a registry match is found AND `classification ==
    non-destructive-incidental` AND the resolved path is NOT under
    `.claude/` → **WARN** (the entry is mis-classified — it's not
    incidental at all; it's just a primary-state write at a non-
    `.claude/` path; downgrade or reclassify). Warnings do not fail
    CI but are surfaced.
  - If no registry match is found → **FAIL** with the
    unregistered-site message in §6.
- **4.1.6 [MUST]** The analyzer MUST also iterate the registry and
  fail if a registry entry references a `(file, function, call)`
  triple that does NOT appear in the static scan (the entry is stale
  / the call site was deleted without registry cleanup). Failure
  message: §6 stale-entry.

### 4.2 Runtime supplement — required for dynamic-path coverage

- **4.2.1 [MUST]** A pytest fixture `boundary_runtime_recorder` lives
  at `tests/boundary/runtime.py`. It monkey-patches
  `pathlib.Path.write_text`, `Path.write_bytes`, `Path.open`,
  `Path.mkdir`, `Path.touch`, `Path.symlink_to`, `Path.rename`,
  `Path.replace`, `os.replace`, `os.rename`, `os.symlink`,
  `tempfile.mkstemp`, `shutil.copy*`, and `shutil.move` for the
  duration of the test session. Each invocation appends a record
  `(qualified_caller, resolved_path, call_kind, mode_if_any)` to an
  in-memory list.
- **4.2.2 [MUST]** A runtime test
  `tests/boundary/test_runtime_writes.py::test_no_dotclaude_primary_writes`
  MUST run a representative app session (boot, activate the bundled
  tutorial workflow, advance one phase, deactivate, exit). Any
  recorded write whose `resolved_path` has any `.claude/` segment AND
  whose `qualified_caller` is in the registry as `primary-state` MUST
  fail the test.
- **4.2.3 [SHOULD]** The runtime test SHOULD cover: agent spawn (R6
  axis-agent's mechanism may produce dynamic writes); workflow
  activation/deactivation (phase context); hint-state save (after a
  hint fires); permission-mode change (config save); worktree create
  (R8 symlink — exempt; verify the exemption applies). Coverage
  expansion is the runtime test's purpose; the static analyzer is the
  gate.

### 4.3 Both passes are required

- **4.3.1 [MUST]** The static analyzer (§4.1) MUST run on every CI
  pipeline invocation. It MUST block merge on any failure.
- **4.3.2 [MUST]** The runtime supplement (§4.2) MUST run as part of
  the standard pytest suite. It supplements the static gate but
  does not replace it.

### 4.4 Exclusions

- **4.4.1 [MUST]** `claudechic/defaults/` is bundled YAML / Markdown
  content (post-restructure) and is excluded from the scan. Bundled
  YAML / Markdown text MAY mention `.claude/` paths as part of agent-
  facing instructions (e.g., the legacy `onboarding/context_docs.md`
  phase doc). Those textual mentions are scanned by a separate
  doc-string sweep (out of scope for this axis; the R6 agent-
  awareness axis-agent or the doc lens owns the sweep).
- **4.4.2 [MUST]** `tests/` is excluded from the static scan. Test
  fixtures legitimately create `<tmp_path>/.claude/...` paths to
  exercise legacy code paths (see §13). The boundary-test scan is
  scoped to production code under `claudechic/`.

---

## 5. Test runner shape

- **5.1 [MUST]** The static gate is exposed as a pytest test at
  `tests/boundary/test_write_sites_static.py`, with the following
  signatures (one test per failure mode for clear diagnostics):

```python
def test_every_write_site_is_registered() -> None:
    """Static scan finds no unregistered write site under claudechic/."""

def test_no_primary_state_write_resolves_into_dot_claude() -> None:
    """No registry primary-state entry has a .claude/-pattern path."""

def test_no_stale_registry_entries() -> None:
    """No registry entry refers to a call site that no longer exists."""

def test_no_a4_symlink_into_dot_claude() -> None:
    """No write site creates a symlink strictly inside .claude/."""

def test_no_a4_overwrite_of_claude_owned_settings() -> None:
    """No write site opens a Claude-owned settings file for write."""
```

- **5.2 [MUST]** The runtime supplement test is at
  `tests/boundary/test_runtime_writes.py::test_no_dotclaude_primary_writes`
  (signature in §4.2.2).
- **5.3 [MUST]** Both files import their helpers from
  `tests/boundary/scan.py` and `tests/boundary/runtime.py`. Helpers
  MUST be importable independently for ad-hoc developer use
  (`python -m tests.boundary.scan claudechic/`).
- **5.4 [SHOULD]** The static-scan helper SHOULD be invocable as a
  CLI: `python -m tests.boundary.scan [--report=<path>] [<root>]`,
  printing a human-readable report to stdout and exiting 0/1.
- **5.5 [MUST-NOT]** The boundary tests MUST NOT depend on a network,
  real Claude SDK, or external services. Both passes run offline.

---

## 6. Failure messages — exact format

All failure messages MUST follow the templates below verbatim (modulo
substitutions).

### 6.1 Unregistered write site

```
BOUNDARY: unregistered write site detected.

  file:        claudechic/<path>.py
  line:        <N>
  function:    <module.qualified.function>
  call:        <call kind, e.g. write_text>
  resolved:    <best-effort resolved path, or "(unresolved)">

This write site is not in tests/boundary/write_sites.yaml. Add an
entry classifying it as one of:
  - primary-state            (must NOT resolve under .claude/)
  - non-destructive-incidental  (may resolve inside .claude/ if it
                                  satisfies §2.1.2 — newly-created,
                                  claudechic-named, regular file,
                                  cross-platform)

See axis_boundary_test.md §3 for registry schema.
```

### 6.2 Primary-state write resolves under `.claude/`

```
BOUNDARY: primary-state write resolves into .claude/.

  site_id:     <id>
  file:        <file>:<line>
  function:    <qname>
  path:        <resolved or pattern>
  classification: primary-state
  rationale:   <registry rationale>

Per L3 + A7, primary-state writes must resolve under .claudechic/
(one of the three tier roots: claudechic/defaults/, ~/.claudechic/,
or <repo>/.claudechic/). Move the write or reclassify the site if
it is genuinely non-destructive-incidental (and satisfies §2.1.2).
```

### 6.3 Stale registry entry

```
BOUNDARY: registry entry references a call site that does not exist.

  site_id:     <id>
  registered:  <file>:<line> <function> <call>

Either restore the call site or remove this entry from
tests/boundary/write_sites.yaml.
```

### 6.4 A4 symlink violation

```
BOUNDARY: symlink path resolves strictly inside .claude/.

  file:        <file>:<line>
  function:    <qname>
  call:        <path_symlink_to | os_symlink>
  symlink_at:  <resolved or pattern>

Per A4, symlinks inside .claude/ are absolutely prohibited (cross-
platform, all tiers). Symlinks at the .claude directory entry itself
(parent is the worktree root, not a .claude/ ancestor) are exempt;
see §8.
```

### 6.5 A4 overwrite of Claude-owned settings

```
BOUNDARY: write would open a Claude-owned settings file.

  file:        <file>:<line>
  function:    <qname>
  call:        <call kind>
  target:      <resolved or pattern>

Per A4, claudechic must never overwrite Claude-owned settings files.
The protected set is enumerated in axis_boundary_test.md §7.
```

### 6.6 Non-destructive-incidental write that doesn't actually touch `.claude/`

```
BOUNDARY [WARN]: non-destructive-incidental site does not resolve into .claude/.

  site_id:     <id>
  file:        <file>:<line>
  resolved:    <path>

The site is classified as non-destructive-incidental (an exception
under A7), but its path is outside .claude/. Reclassify as
primary-state, or fix the path pattern.
```

(Warnings appear in the report; they do not block CI.)

---

## 7. A4 — overwrite prohibition (Claude-owned files)

- **7.1 [MUST]** The boundary test treats the following filenames
  inside any `.claude/` directory as Claude-owned. No write site
  (regardless of classification) MAY open any of these in a write,
  append, or `r+` mode:

| Protected filename (pattern) | Where Claude reads it (informative) |
|---|---|
| `settings.json` | Claude Code global / project / local settings |
| `settings.local.json` | Claude Code local-only overrides |
| `.credentials.json` | Claude Code OAuth credentials (read-only by claudechic per `claudechic/usage.py:66`) |
| `history.jsonl` | Claude Code shell history (read-only by claudechic per `claudechic/history.py:9`) |
| `plugins/installed_plugins.json` | Claude Code plugin registry (read-only per `claudechic/help_data.py:79`) |
| `projects/**/*.jsonl` | Claude Code session JSONLs (read-only per `claudechic/sessions.py:86`) |
| `plans/**` | Claude Code plan files (claudechic permits Claude's writes here per `claudechic/agent.py:1243`; claudechic itself never writes here) |
| `rules/**` *with carve-out* | Claude Code project rules. **Carve-out per SPEC.md §11.3 + A13 + §8.6 below:** writes at `${HOME}/.claude/rules/claudechic_*.md` (basename matching `^claudechic_[^/]+\.md$` AND parent exactly `${HOME}/.claude/rules`) are PERMITTED via the `is_claudechic_prefixed_rules_file` predicate. Mkdir of `${HOME}/.claude/rules` itself is PERMITTED via `is_claude_rules_dir_mkdir`. All other writes into any `.claude/rules/` directory remain forbidden. The protected match is therefore: `rules/**` MINUS `${HOME}/.claude/rules/claudechic_*.md` MINUS the directory mkdir. |
| `commands/**` | Claude Code slash command definitions |
| `skills/**/SKILL.md` | Claude Code skill definitions |
| `hooks/**` | Claude Code hook definitions |
| `guardrails/**` | Claude Code guardrail rules (referenced in `claudechic/context/guardrails-system.md`) |
| `agents/**` | Claude Code agent definitions |

- **7.2 [MUST]** The protected list is canonical and lives at
  `tests/boundary/claude_owned_files.yaml`. It is loaded by the
  static analyzer and the runtime supplement. The list is
  extensible — adding a filename does not require a code change to
  the analyzer.
- **7.3 [MUST]** The R6 axis-agent's mechanism (whatever they pick)
  MUST NOT write any of the protected names. The test enforces this
  uniformly, regardless of what the R6 axis-agent picks.
- **7.4 [MUST]** A write site whose path matches a protected filename
  fails the test even if the site is registered as
  `non-destructive-incidental`. The protected list is an absolute
  prohibition; A7's softening does not apply.

---

## 8. R5.3 disambiguation — symlink classification

The boundary test classifies symlink call sites with three predicates:

- **8.1 [MUST]** `symlink_at_dot_claude_directory_entry`: the
  resolved symlink path is `.../.claude` exactly (i.e., the parent
  is *not* itself a `.claude/` directory; the symlink IS the
  `.claude` directory entry of its parent). **Permitted** under R5.3
  — pre-existing worktree pattern. Registry entry MUST set
  `is_dotclaude_directory_entry: true`.
- **8.2 [MUST]** `symlink_inside_dot_claude`: the resolved symlink
  path matches `.../.claude/...` (the symlink lives strictly below
  a `.claude/` ancestor). **Forbidden** under A4. The test fails
  with §6.4 regardless of registry classification.
- **8.3 [MUST]** `symlink_with_dotclaude_target`: the symlink's path
  is outside any `.claude/` ancestor, and only its target points
  into `.claude/`. **Permitted** unconditionally (read direction).
  Registry entry — if any — MAY classify as
  `non-destructive-incidental` if it lives outside `.claude/`; more
  commonly the symlink is a `.claudechic/` artifact and the entry
  is `primary-state`.
- **8.4 [MUST]** Predicate evaluation is **on the resolved symlink
  path**, not the target. The static analyzer determines the parent
  by examining the path expression: `worktree_dir / ".claude"` →
  parent is `worktree_dir`, basename is `.claude`, ancestor `.claude/`
  is none → predicate 8.1 (entry); `Path("/tmp/.claude") /
  "rules" / "x"` → parent has a `.claude/` ancestor → predicate 8.2
  (forbidden).
- **8.5 [MUST]** The single existing site that satisfies predicate
  8.1 today is `claudechic/features/worktree/git.py:299` (worktree
  symlink). Its registry entry MUST set
  `is_dotclaude_directory_entry: true` and `accepts_dotclaude:
  true` and `classification: non-destructive-incidental`. After
  SPEC.md §10.3 lands, a second site at `git.py:~302` (the new
  `.claudechic` worktree symlink) satisfies the analogous predicate
  `is_dotclaudechic_directory_entry: true`.

- **8.6 [MUST]** Per SPEC.md §4 (Group D — RESEARCH.md Option B):
  the boundary test recognizes a write-side predicate
  `is_claudechic_prefixed_rules_file`: the resolved write path's
  parent is exactly `${HOME}/.claude/rules` AND the basename matches
  `claudechic_*.md` (regex `^claudechic_[^/]+\.md$`). Writes
  satisfying this predicate are **permitted** as
  `non-destructive-incidental` (per SPEC.md §11.1 + STATUS.md A13
  forthcoming). The single registered site is
  `awareness_install.write_rule` per §10's table. The
  parent-mkdir at `${HOME}/.claude/rules` is similarly permitted via
  the registered site `awareness_install.mkdir_rules_dir` (predicate
  variant: `is_claude_rules_dir_mkdir`).

  Writes whose path matches `${HOME}/.claude/rules/...` BUT whose
  basename does NOT satisfy `is_claudechic_prefixed_rules_file` (e.g.,
  a hypothetical `awareness_install.py` accidentally writing
  `~/.claude/rules/foo.md` without the prefix) MUST fail the boundary
  test with the §6.2 message "primary-state write resolves into
  .claude/" (or a tightened variant naming the prefix violation).

---

## 9. Read-vs-write disambiguation

- **9.1 [MUST]** The static analyzer MUST NOT flag any of:
  - `Path.read_text(...)`, `Path.read_bytes(...)`, `Path.open("r")`,
    `Path.open("rb")`, `Path.open()` with no mode arg or default
    mode.
  - `open(path, "r"|"rt"|"rb")` and `open(path)` with no mode arg.
  - `path.exists()`, `path.is_file()`, `path.is_dir()`,
    `path.iterdir()`, `path.glob()`, `path.rglob()`,
    `os.listdir(...)`, `os.scandir(...)`, `os.path.exists(...)`,
    `os.stat(...)` and similar metadata reads.
  - `json.loads(path.read_text(...))`, `yaml.safe_load(f)` patterns
    where `f` is opened read-only.
- **9.2 [MUST]** The static analyzer determines write-vs-read by the
  call kind matrix in §4.1.2. Modes containing any of `w`, `a`, `x`,
  `+` are writes; everything else is a read. Calls whose mode arg is
  computed dynamically (e.g., `mode = "w" if x else "r"`) MUST emit
  a warning row and rely on the registry to classify (a registry
  entry exists → site is acknowledged; no entry → fail per §6.1).

---

## 10. Initial registry — pre-restructure baseline

This is the registry's initial state, before any restructure work
lands. It enumerates every CURRENTLY-EXISTING claudechic write site
that touches a `.claude/`-relative path, plus the symlink case. It
does NOT include `.claudechic/`-only writes (those are not a
boundary concern), nor read sites.

After Group A + Group B (per Composability spec §7) lands, every
`primary-state` entry below moves to a `.claudechic/` path. The
post-restructure expectation: zero `primary-state` registry entries
have a `.claude/`-shaped `path_pattern`.

| site_id | file:line | function | call | classification | path_pattern (today) | post-restructure path_pattern | accepts_dotclaude |
|---|---|---|---|---|---|---|---|
| `config.save.user_config` | `claudechic/config.py:73` | `config._save` | `os_replace` | `primary-state` | `${HOME}/.claude/.claudechic.yaml` | `${HOME}/.claudechic/config.yaml` | false |
| `config.save.user_config_mkdir` | `claudechic/config.py:68` | `config._save` | `path_mkdir` | `primary-state` | `${HOME}/.claude/` (parent) | `${HOME}/.claudechic/` | false |
| `config.save.user_config_tmpfile` | `claudechic/config.py:69` | `config._save` | `tempfile_mkstemp` | `primary-state` | `${HOME}/.claude/.<tmp>` | `${HOME}/.claudechic/.<tmp>` | false |
| `config.load.legacy_rename` | `claudechic/config.py:30` | `config._load` | `os_rename` | `primary-state` | `${HOME}/.claude/claudechic.yaml` → `${HOME}/.claude/.claudechic.yaml` | (legacy migration code is removed by Group B per L17/A9; entry deleted) | false |
| `hints.state.save.lifecycle` | `claudechic/hints/state.py:306` | `HintStateStore.save` | `os_replace` | `primary-state` | `${repo}/.claude/hints_state.json` | `${repo}/.claudechic/hints_state.json` | false |
| `hints.state.save.mkdir` | `claudechic/hints/state.py:287` | `HintStateStore.save` | `path_mkdir` | `primary-state` | `${repo}/.claude/` (parent) | `${repo}/.claudechic/` | false |
| `hints.state.save.tmpfile` | `claudechic/hints/state.py:297` | `HintStateStore.save` | `tempfile_mkstemp` | `primary-state` | `${repo}/.claude/.hints_state_<rand>.tmp` | `${repo}/.claudechic/.hints_state_<rand>.tmp` | false |
| `app.phase_context.write` | `claudechic/app.py:1853` | `ChatApp._write_phase_context` | `write_text` | `primary-state` | `${cwd}/.claude/phase_context.md` | (under R6 axis-agent's mechanism — see §11) | false |
| `app.phase_context.mkdir` | `claudechic/app.py:1852` | `ChatApp._write_phase_context` | `path_mkdir` | `primary-state` | `${cwd}/.claude/` | (under R6 axis-agent's mechanism) | false |
| `app.phase_context.unlink_stale` | `claudechic/app.py:1867` | `ChatApp._write_phase_context` | `path_unlink` | `primary-state` | `${cwd}/.claude/phase_context.md` | (under R6 axis-agent's mechanism) | false |
| `app.phase_context.unlink_deactivate` | `claudechic/app.py:1928` | `ChatApp._deactivate_workflow` | `path_unlink` | `primary-state` | `${cwd}/.claude/phase_context.md` | (under R6 axis-agent's mechanism) | false |
| `guardrails.hits.record.mkdir` | `claudechic/guardrails/hits.py:51` | `HitLogger.record` | `path_mkdir` | `primary-state` | `${repo}/.claude/` (parent of `hits.jsonl`; constructed by `app.py:1492`) | `${repo}/.claudechic/` (parent of `hits.jsonl`) | false |
| `guardrails.hits.record.append` | `claudechic/guardrails/hits.py:52` | `HitLogger.record` | `open_a` | `primary-state` | `${repo}/.claude/hits.jsonl` (constructed by `app.py:1492`) | `${repo}/.claudechic/hits.jsonl` | false |
| `worktree.git.symlink_dotclaude` | `claudechic/features/worktree/git.py:301` | `worktree.git.create_worktree` | `path_symlink_to` | `non-destructive-incidental` | `${worktree_dir}/.claude → ${main_wt}/.claude` | unchanged (R8 — pre-existing pattern) | true (and `is_dotclaude_directory_entry: true`) |
| `worktree.git.symlink_dotclaudechic` | `claudechic/features/worktree/git.py:~302` (NEW per SPEC.md §10.3) | `worktree.git.create_worktree` | `path_symlink_to` | `non-destructive-incidental` | n/a (new) | `${worktree_dir}/.claudechic → ${main_wt}/.claudechic` | **false** for `accepts_dotclaude` — the symlink path is outside any `.claude/` ancestor; flag set instead is `is_dotclaudechic_directory_entry: true` (analogous to row above; symlink lives at the worktree directory entry) |
| `awareness_install.write_rule` | `claudechic/awareness_install.py:install_awareness_rules` (NEW per SPEC.md §4 — RESEARCH.md Option B) | `awareness_install.install_awareness_rules` | `write_text` (NEW + UPDATE) AND `path_unlink` (DELETE pass per SPEC.md §4.3 — same site_id covers both calls because both are bounded by `is_claudechic_prefixed_rules_file`; implementer MAY split into a second site_id `awareness_install.delete_orphan` for static-analyzer clarity) | `non-destructive-incidental` | n/a (new) | `${HOME}/.claude/rules/claudechic_<bundled_name>.md` for each `<bundled_name>.md` in `claudechic/context/` AND any `${HOME}/.claude/rules/claudechic_<orphan>.md` whose stem is no longer in the bundled catalog (DELETE pass) | true (predicate `is_claudechic_prefixed_rules_file: true` — basename matches `claudechic_*.md` AND parent is exactly `${HOME}/.claude/rules`; cataloged set bounded by the contents of `claudechic/context/` for writes; bounded by the regex predicate for unlinks; claudechic-owned by prefix; idempotent NEW/UPDATE/SKIP/DELETE; symlink guard per SPEC.md §4.3 — symlinks at `claudechic_*.md` paths are skipped, never followed, never unlinked) |
| `awareness_install.mkdir_rules_dir` | `claudechic/awareness_install.py:install_awareness_rules` (NEW) | `awareness_install.install_awareness_rules` | `path_mkdir` | `non-destructive-incidental` | n/a (new) | `${HOME}/.claude/rules` (parent dir created with `parents=True, exist_ok=True`) | true (creating Claude's standard rules-directory if absent; per Anthropic docs this is a Claude-Code-discovered location; non-destructive because directory creation is idempotent and never overwrites) |

Notes on the table:

- The four `app.phase_context.*` entries collapse to "the path-
  construction call(s) at app.py:1848 and the writes / mkdirs / unlinks
  on that path." The exact line numbers are best-effort; `site_id`
  is the durable handle (§3.1.4).
- `unlink` (per §2.3) counts as a directory-entry-modifying call and
  is in scope. The static analyzer MUST add `path_unlink` to the
  call matrix. (This is added to §4.1.2's table at first commit.)
- `claudechic/audit/audit.py:37` (`CLAUDE_PROJECTS_DIR`) is **read-
  only**; verified at `audit.py:430-432` (only `is_dir()` and
  `iterdir()` calls). NOT in the registry — reads are unrestricted
  (§9).
- `claudechic/help_data.py:67,79`, `claudechic/usage.py:66,101`,
  `claudechic/history.py:9,29`, `claudechic/sessions.py:86,326`,
  `claudechic/commands.py:377-382`, `claudechic/agent.py:748,1243`,
  `claudechic/app.py:663,676` — all **read-only or filter-
  predicate** uses of `.claude/` paths. NOT in the registry.
- The legacy `_OLD_CONFIG_PATH` rename at `config.py:30` is a
  pre-existing user-tier migration (`~/.claude/claudechic.yaml` →
  `~/.claude/.claudechic.yaml`). Per L17/A9, Group B's
  user-config relocation deletes this code; the registry entry is
  scheduled for deletion alongside.

**Total pre-restructure write-site enumeration: 14 entries** (13
`primary-state` + 1 `non-destructive-incidental`).

**Post-restructure write-site enumeration: 16 entries**:
- **12 `primary-state`** (after the `config.load.legacy_rename` deletion
  per L17/A9 + Group B's relocations of phase-context/hits/state/config
  writes; all resolve under `.claudechic/`).
- **4 `non-destructive-incidental`** — split by predicate:
  - **3 with `accepts_dotclaude: true`** (resolved write path is under a
    `.claude/` ancestor):
    1. `worktree.git.symlink_dotclaude` (pre-existing; predicate
       `is_dotclaude_directory_entry: true`).
    2. `awareness_install.write_rule` (new per SPEC.md §4; predicate
       `is_claudechic_prefixed_rules_file: true`).
    3. `awareness_install.mkdir_rules_dir` (new per SPEC.md §4; predicate
       `is_claude_rules_dir_mkdir: true` per §8.6).
  - **1 with `accepts_dotclaude: false`** but classified
    `non-destructive-incidental` because the resolved write path is at the
    worktree directory entry (parent is the worktree root, NOT inside any
    `.claude/` ancestor):
    1. `worktree.git.symlink_dotclaudechic` (new per SPEC.md §10.3;
       predicate `is_dotclaudechic_directory_entry: true`).

Post-restructure target: **0 `primary-state` entries with a
`.claude/`-shaped path**; **3 `accepts_dotclaude: true` entries** (the
two install-routine sites + the pre-existing `.claude` worktree symlink);
**1 additional `non-destructive-incidental` entry without
`accepts_dotclaude`** (the new `.claudechic` worktree symlink, classified
under the analogous `is_dotclaudechic_directory_entry` predicate). The
`claudechic_*.md` prefix carve-out in `claude_owned_files.yaml` per
SPEC.md §11.3 is a separate concern (the protected-list predicate, not a
new write site).

---

## 11. Integration with the agent-awareness axis-agent (R6 — post-A13)

The agent-awareness axis-agent's mechanism (Group D in SPEC.md) was
chosen as RESEARCH.md Option B (user-approved A13): an idempotent
install routine that copies bundled `claudechic/context/*.md` into
`~/.claude/rules/claudechic_*.md` on every claudechic startup, plus an
orphan DELETE pass per SPEC.md §4.3 + symlink guard. The integration
status is therefore concrete (not deferred):

- **11.1 [HISTORICAL]** Pre-A13 framing (R6 mechanism deferred) is
  superseded. The R6 mechanism is fully specified at SPEC.md §4.
- **11.2 [MUST]** The post-A13 registry has the following claudechic-
  awareness install sites, all classified `non-destructive-incidental`:
  - `awareness_install.write_rule` — `write_text` (NEW + UPDATE) AND
    `path_unlink` (DELETE pass) per SPEC.md §4.3; predicate
    `is_claudechic_prefixed_rules_file: true`.
  - `awareness_install.mkdir_rules_dir` — `path_mkdir` of
    `${HOME}/.claude/rules`; predicate `is_claude_rules_dir_mkdir: true`.
  See §10's table for full registry-row content.
- **11.3 [MUST]** The boundary tests enforce R6's classification
  uniformly via the registry + predicates + symlink-guard runtime
  invariant (per SPEC.md §4.3 + INV-AW-11). No path-shape outside
  the predicates is permitted under the awareness-install carve-out.
- **11.4 [MUST-NOT]** The R6 mechanism MUST NOT write any name in §7's
  protected list except via the explicit carve-out for
  `${HOME}/.claude/rules/claudechic_*.md` (SPEC.md §11.3 + this spec
  §7.1's `rules/**` carve-out).
- **11.5 [MUST]** Post-A13, the registry has the four
  `non-destructive-incidental` entries enumerated in §10's
  post-restructure summary (3 with `accepts_dotclaude: true`: the
  pre-existing `.claude` worktree symlink + the two install-routine
  sites; 1 with `is_dotclaudechic_directory_entry: true`: the new
  `.claudechic` worktree symlink). All other registry entries are
  `primary-state` and resolve under `.claudechic/` (zero
  `.claude/`-shaped paths).
- **11.6 [MUST]** Future expansion of the awareness-install carve-out
  (e.g., a hypothetical user-tier `~/.claudechic/context/*.md`
  passthrough per RESEARCH.md §4.4 follow-up) MUST extend §10's
  table, §3.1 schema, and §7.1 carve-out language synchronously.
  The boundary lint MUST NOT relax for any new path shape without a
  corresponding registry + predicate addition.

---

## 12. CI integration

- **12.1 [MUST]** The static gate (§4.1, §5.1) MUST run as part of
  the existing pytest invocation. The hooks listed in
  `CLAUDE.md`'s "Pre-commit Hooks" section already run pyright +
  ruff; the boundary tests join that suite.
- **12.2 [MUST]** The runtime supplement (§4.2, §5.2) MUST run in
  the standard `pytest` collection.
- **12.3 [SHOULD]** A pre-commit hook entry MAY be added that
  invokes `python -m tests.boundary.scan` for fast local feedback
  before push. The pre-commit hook is OPTIONAL — the pytest gate
  is the authoritative enforcement point.
- **12.4 [MUST]** The boundary test failure MUST block merge in
  whatever CI/PR-gating system is in use (today: pre-commit + a
  manual `pytest` run; the spec authors may strengthen this in
  follow-up but MUST NOT weaken).

---

## 13. Pre-existing test deltas

The boundary test interacts with several existing tests that
construct `<tmp_path>/.claude/...` for unit-test scaffolding. These
tests are NOT scanned (per §4.4.2) but the boundary work itself
will move the production paths and these tests must be updated:

| Test file | Change required |
|---|---|
| `tests/test_bug12_guardrails_detect_field.py:68,100,132,160` | Update `tmp_path / ".claude" / "hits.jsonl"` → `tmp_path / ".claudechic" / "hits.jsonl"` after Group B moves the production path. |
| `tests/test_workflow_guardrails.py:67,86,108,154,200,244,270,308,351` | Same as above (8 occurrences). |
| `tests/test_workflow_hits_logging.py:44,100,149` | Same as above (3 occurrences). |
| `tests/test_hints_integration.py:178` | Update `state_dir = tmp_path / ".claude"` → `tmp_path / ".claudechic"`. |
| `tests/test_welcome_screen_integration.py:76` | Update `state_file = tmp_path / ".claude" / "hints_state.json"` → `tmp_path / ".claudechic" / "hints_state.json"`. |
| `tests/test_bug16_sessions_encoding.py:36` | NO change — this constructs `tmp_path / ".claude" / "projects"` to simulate Claude Code's session JSONL store; that's a Claude-owned read path, not a claudechic write. |
| `tests/test_roborev.py:402,425,439` | NO change — these construct `tmp_path / ".claude" / "skills"` to simulate Claude-owned skills; reads only. |
| `tests/conftest.py:109` | Update comment string that mentions `~/.claude/.claudechic.yaml` → `~/.claudechic/config.yaml`. |
| `tests/test_config_integration.py:56,80` and `tests/test_welcome_screen_integration.py:112` | Update `tmp_path / ".claudechic.yaml"` (FILE form) → `tmp_path / ".claudechic" / "config.yaml"` (DIRECTORY form) per L5 / Group B. |

These deltas are owned by the implementers of Group B (boundary
relocation), not by the boundary-test axis-agent. This spec lists
them so the work is not lost during Group B execution.

---

## 14. Sibling tests (NOT owned here)

The Composability spec INV-7 requires the override-resolution
invariants (INV-1, INV-2, INV-4, INV-5) to ship alongside the
boundary test (INV-6). Those tests are owned by the loader-resolution
axis-agent (`axis_loader_resolution.md`); they are NOT specified
here. The boundary axis-agent's deliverable is INV-6 plus the A4
prohibitions only.

When the loader-resolution axis-agent's spec lands, the file layout
SHOULD be:

```
tests/boundary/
  write_sites.yaml
  claude_owned_files.yaml
  scan.py
  runtime.py
  test_write_sites_static.py
  test_runtime_writes.py
tests/loader/
  test_override_resolution.py     # owned by R3 axis-agent
  test_tier_walk.py               # owned by R3 axis-agent
  ...
```

The two test packages are independent. Cross-referencing in test
output is permitted but not required.

---

## 15. Deliverables (binding for the implementation phase)

The implementation phase MUST produce:

1. `tests/boundary/__init__.py` (empty package marker)
2. `tests/boundary/scan.py` (static analyzer per §4.1)
3. `tests/boundary/runtime.py` (runtime supplement per §4.2)
4. `tests/boundary/write_sites.yaml` (the registry — initial contents
   per §10)
5. `tests/boundary/claude_owned_files.yaml` (protected list per §7)
6. `tests/boundary/test_write_sites_static.py` (signatures per §5.1)
7. `tests/boundary/test_runtime_writes.py` (signature per §5.2)
8. The Group-B path-string updates in pre-existing tests (per §13).
9. `tests/boundary/test_awareness_sdk_e2e.py` (live-SDK end-to-end
   test per §16; satisfies INV-AW-SDK-1 in SPEC.md §13.3.3).

The implementation phase MUST NOT:

- Skip the `non-destructive-incidental` classification (it is
  load-bearing for A7).
- Implement the test as a path-string regex (insufficient under A7;
  registry+static-AST is required).
- Add migration logic of any kind (per L17 / A9).
- Touch the R6 axis-agent's deliverables (the boundary test only
  validates whatever R6 picks).

---

## 16. Live-SDK end-to-end verification (per SPEC.md §12.2 + fresh-review F2 fix)

The boundary test (§4–§15) verifies claudechic's *write-side* behavior. This section defines the *read-side* counterpart: a live-SDK end-to-end test that verifies the Claude Agent SDK actually loads `~/.claude/rules/claudechic_*.md` content into a real agent's system context. Without this verification, the entire claudechic-awareness install mechanism (SPEC.md §4) rests on an unverified Anthropic-runtime contract.

### 16.1 Scope

- **In:** Verify that a sentinel rule file placed at `~/.claude/rules/claudechic_<sentinel>.md` reaches a Claude Agent SDK client's system context when `setting_sources=["user","project","local"]`. This is the read-side property the entire mechanism in SPEC.md §4 depends on.
- **Out:** Functional testing of claudechic's install routine (covered by INV-AW-1..INV-AW-5 in SPEC.md §13.3.1); boundary lint of write sites (covered by §4–§15 of this file).

### 16.2 Test file location

```
tests/boundary/test_awareness_sdk_e2e.py
```

The test lives under `tests/boundary/` for organizational adjacency to the rest of the boundary infrastructure. Per §4.4.2, the entire `tests/` tree is excluded from the static boundary scan; this test does NOT need a `write_sites.yaml` entry.

### 16.3 Sentinel filename and content (binding)

| Aspect | Value |
|---|---|
| **Sentinel filename** | `claudechic_sdk_sentinel_v1.md` |
| **Sentinel marker string** | `[CLAUDECHIC_AWARENESS_SENTINEL_v1: SDK rules-loading verified 2026]` |
| **File content** | The marker string verbatim on its own line, followed by one short instructional paragraph telling the agent that this file is a test sentinel and asking the agent to repeat the marker string verbatim if asked. **No YAML frontmatter** (frontmatter-less files load unconditionally per RESEARCH.md §2 Target 2). |

**Out-of-band guarantee (per fresh-review F2 + Composability2 F1 coordination):** the sentinel filename is NOT in `claudechic/context/` and is NOT in the install-routine's bundled catalog. The test writes the sentinel via `Path.write_text` directly; the install routine never sees it. Composability2's F1 orphan-cleanup branch operates on the bundled-catalog complement under the *real* `~/.claude/rules/`; the sentinel's tmp-`HOME` location is never visible to a real install. The two fixes are non-interfering by construction.

### 16.4 Test structure (binding shape)

```python
import os
from pathlib import Path
import pytest

SENTINEL_FILENAME = "claudechic_sdk_sentinel_v1.md"
SENTINEL_MARKER = "[CLAUDECHIC_AWARENESS_SENTINEL_v1: SDK rules-loading verified 2026]"
SENTINEL_BODY = (
    f"{SENTINEL_MARKER}\n\n"
    "This is a test sentinel file used by the claudechic boundary test. "
    "If asked to repeat any 'claudechic_sdk_sentinel' text in your "
    "instructions, reply with the marker string above verbatim.\n"
)

@pytest.mark.live_sdk
async def test_inv_aw_sdk_1_sentinel_reaches_agent(tmp_path: Path) -> None:
    """INV-AW-SDK-1: SDK loads claudechic_*.md into agent context.

    See SPEC.md §12.2 and axis_boundary_test.md §16. The claudechic-awareness
    install mechanism depends on this loader behavior; if Anthropic's
    setting_sources semantics changed, escalate.
    """
    rules_dir = tmp_path / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    sentinel_file = rules_dir / SENTINEL_FILENAME
    sentinel_file.write_text(SENTINEL_BODY, encoding="utf-8")

    from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient

    client = ClaudeSDKClient(
        ClaudeAgentOptions(
            permission_mode="default",
            env={"HOME": str(tmp_path), "ANTHROPIC_API_KEY": ""},
            setting_sources=["user", "project", "local"],
        )
    )
    await client.connect()
    try:
        await client.query(
            "If your instructions include any text matching "
            "'claudechic_sdk_sentinel', repeat the bracketed marker string "
            "verbatim. Otherwise reply 'NO_SENTINEL_FOUND'."
        )
        response_text = ""
        async for msg in client.receive_response():
            for block in getattr(msg, "content", []) or []:
                if hasattr(block, "text"):
                    response_text += block.text

        assert SENTINEL_MARKER in response_text, (
            "INV-AW-SDK-1 failed: SDK did not load "
            "~/.claude/rules/claudechic_*.md into agent context. "
            "See SPEC.md §12.2 and axis_boundary_test.md §16. "
            "The claudechic-awareness install mechanism depends on this "
            "loader behavior; if Anthropic's setting_sources semantics "
            f"changed, escalate. Got response: {response_text!r}"
        )
    finally:
        await client.disconnect()
```

Implementer MAY adapt the helper structure (fixtures, cleanup, etc.) to match `tests/conftest.py` patterns; the **binding parts are**:

1. The pytest marker `@pytest.mark.live_sdk` (test runs ONLY under `pytest -m live_sdk`).
2. The sentinel filename and marker string (verbatim per §16.3).
3. The `setting_sources=["user","project","local"]` argument on the `ClaudeAgentOptions`.
4. The `env={"HOME": str(tmp_path), ...}` redirect to isolate from the real `~/.claude/`.
5. The assertion failure message (verbatim per §16.5).

### 16.5 Failure message (binding)

When the assertion fails, the message MUST contain (verbatim):

```
INV-AW-SDK-1 failed: SDK did not load ~/.claude/rules/claudechic_*.md into agent context. See SPEC.md §12.2 and axis_boundary_test.md §16. The claudechic-awareness install mechanism depends on this loader behavior; if Anthropic's setting_sources semantics changed, escalate.
```

The maintainer's first action on this failure is to check (a) the installed Claude Code CLI version, (b) the `claude-agent-sdk` package version, (c) whether `setting_sources` is still documented per RESEARCH.md §2 Target 1, and (d) whether the bundled `~/.claude/rules/` loader behavior has changed. If Anthropic has changed the surface, the maintainer escalates per SPEC.md §12.2.

### 16.6 Test marker registration

`pyproject.toml` (or `pytest.ini`) MUST declare the `live_sdk` marker:

```toml
[tool.pytest.ini_options]
markers = [
    "live_sdk: requires live Claude Code SDK + CLI subprocess; opt-in via -m live_sdk",
]
```

Without the marker registration, pytest emits an `unknown_marker` warning at collection. The marker registration is a one-line addition.

### 16.7 CI integration

- **CI default:** the live-SDK test MUST NOT run in the default pytest invocation (`pytest tests/`). Default collection skips marked tests; the test stays inert on every PR.
- **CI scheduled gate:** CI MUST invoke `pytest -m live_sdk tests/boundary/test_awareness_sdk_e2e.py` on a separate scheduled job (recommended cadence: nightly or weekly). The job MUST have access to a logged-in Claude Code CLI subprocess (the existing CI environment that runs claudechic's e2e tests is sufficient).
- **Failure response:** a live-SDK gate failure MUST NOT block ordinary PR merges (the default-pytest gate covers PR-level correctness). It MUST raise an alert to the maintainer (e.g., a GitHub issue labeled `awareness-sdk-drift`) with the failure message verbatim.

### 16.8 Out-of-scope

This section does NOT specify:
- Tester acceptance for INV-AW-1..5 (covered by SPEC.md §13.3.1).
- Behavioral testing of claudechic's response to a failed install (covered by SPEC.md §4.5 — the install routine logs WARNING and does not block startup).
- Verification of the sentinel-content survives `/compact` (the SDK survives `/compact` natively per RESEARCH.md §2 Target 1; a separate post-compact test would be valuable but is not gating the F2 fix).
- Per-platform variation of the test (Windows is excluded; the worktree-symlink mechanism already excludes Windows per SPEC.md §10.1).

---

*End of axis_boundary_test.md.*
