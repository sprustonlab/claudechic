# Risk Evaluation — independent_chic

**Author:** Skeptic (Leadership lens)
**Status:** Leadership phase — first pass, addressing the eight-question charge in `userprompt.md` plus run-specific amendments A1/A2/A3 and binding constraints L1–L17.

This document is rationale (per L14): it identifies failure modes, preconditions, detection signals, and mitigations. It does **not** give operational instructions. The Specification phase owns those.

Severity scale: **Low / Med / High / Critical** anchored to L10's four "lost-work" senses:

| L10 sense | Detectability | Recoverability | Severity weight |
|---|---|---|---|
| **L10.a** Commits never on main | High (git log) | High (re-cherry-pick) | Low |
| **L10.b** Features non-functional post-merge | Medium (needs tests) | Medium (debug + fix) | Med |
| **L10.c** Features reverted in conflict resolution | Low (looks intentional) | Low (needs authorial memory) | High |
| **L10.d** Intent lost even if code survives | Very low | Very low (re-derive design) | Critical |

Likelihood: **L / M / H / VH**.

---

## 0. Vision / STATUS errors flagged (per A1)

A1 says "agents discovering errors or inconsistencies in `vision.md` must surface them." Three issues found on close reading; surfacing here for the coordinator rather than working around.

### V-ERR-1 — A3 may be unsatisfiable in pure form, depending on what "mirror" means.

A3 requires the agent-awareness mechanism to "mirror Claude Code's `.claude/rules/` behavior — file-based, auto-loaded, treated by agents as rule-equivalent context — rather than relying on system-prompt presets, append parameters, or hooks alone." L3 forbids any write inside any `.claude/` directory.

The ways Claude Code makes a directory's content auto-loaded by every agent (without per-tool opt-in) are: the `.claude/rules/` location itself, Claude Code's `additionalDirectories` / project-`settings.json` extension points, or the SDK's system-prompt extension. A3 explicitly rejects the SDK system-prompt path as not-mirror-enough. The two remaining mechanisms either touch `.claude/` directly or touch `.claude/settings.json` to register an alternate directory — both are writes inside `.claude/` and so violate L3.

This is not a death sentence. There are paths that satisfy *both* — see Risk **R2** below — but the phrasing "mirror `.claude/rules/`" plus "without writing inside `.claude/`" is in tension and the Specification phase will have to pick a precise reading. Recommend the coordinator have the user confirm one of:
- (a) "Mirror" means *behavioral* equivalence (auto-loaded, file-based, treated as rule-equivalent) — even if the file lives at a path Claude Code doesn't natively scan, claudechic uses an SDK-level injection that *reads from* `.claudechic/rules/` files at session start. Acceptable; no `.claude/` write.
- (b) "Mirror" means *path* equivalence (the agent sees `.claude/rules/`-style content discovery). Then the user must accept either a one-time-by-user manual `claude config` step, or a relaxation of L3 to permit a single `.claude/settings.json` edit (under user consent) to add `.claudechic/rules/` to `additionalDirectories`.
- (c) Reject A3's "mirror" wording and accept system-prompt injection as the mechanism.

A1 is invoked here. The grading rubric should *not* penalize the spec phase for picking (a), (b)-with-consent, or (c) — but it must explicitly call out which one it picked, and how the chosen reading is consistent with both A3 and L3. A spec that quietly assumes (a) without saying so is an L14 trap (rationale leaking into spec by omission).

### V-ERR-2 — STATUS §"Phase log" lists `setup` as "✓ Complete" while `current_phase` is "`setup` (about to advance to `leadership`)."

Cosmetic, but if an agent reads only the table it will assume setup is done; if it reads only the "Run identity" cell it will think setup is in progress. Recommend the coordinator pick one and align the other before Leadership phase agents fan out further.

### V-ERR-3 — L17 "no migration logic" leaves silent state-loss for the issue-author and Arco that nobody owns.

L17 says "both can manually move files if needed." This is a genuine constraint, not an error in itself. But the vision §"Failure looks like" doesn't list "two existing users hit a silent file-loss when they pull the restructure" as a failure mode, and STATUS doesn't flag who owns telling them what to move. If the spec ships without a hand-off note in the PR description / release notes, L17's intent (manual is fine) collapses into "broken on first pull" because no one warned them. See Risk **R10** below.

---

## 1. Boundary enforcement (L3) failure modes

The user's question: how does claudechic regress into writing inside `.claude/` after this work ships?

### R1 — `phase_context.md` write site re-introduced

| Field | Value |
|---|---|
| Severity | **High (L10.b/c)** |
| Likelihood | **M** |
| Preconditions | Future feature work touches `claudechic/app.py` lines around 1623–1849, OR a new contributor copies the existing pattern. |

**Where it fires.** `claudechic/app.py:1822–1854` writes `phase_context.md` to `Path.cwd() / ".claude"`, hard-coded. It also reads (`:1925`) and unlinks (`:1927`). Any new phase-related feature (e.g., per-agent phase dispatch) is overwhelmingly likely to copy this pattern.

**Detection.** A boundary lint test that walks the repo looking for any string-literal containing `".claude/"` on a write path (`open()`, `mkdir()`, `Write` tool call, `symlink_to` whose source is under `.claude/`). A simpler-but-incomplete check: `grep -rn '"\.claude' claudechic/` and require an allowlist comment on each match. The lint must run in CI and fail the build, not just warn.

**What the lint must catch concretely:**
1. `open(...".claude/...", "w")` and `open(...".claude/...", "a")`
2. `Path.write_text` / `Path.write_bytes` whose path resolves under `.claude/`
3. `os.makedirs` / `Path.mkdir` whose target is under `.claude/`
4. `pathlib.Path("...").symlink_to(...)` where the *symlink itself* is under `.claude/` (BF7-class — see R6 below)
5. `shutil.copy` / `shutil.move` to under `.claude/`
6. `subprocess.run(["...", ".claude/..."])` for shell-level writes (heuristic: any subprocess argv containing `.claude/` plus `>`, `tee`, `cp`, `mv`, `touch`, `mkdir`)
7. Tool-emitted writes — agents in workflow phases that call `Write` with `.claude/...` paths. The lint can't catch these statically; only a runtime guard on the SDK's `can_use_tool` callback can. See R3.

**Mitigation.** Add the static lint plus a runtime guard in the `can_use_tool` callback that auto-denies any `Write`/`Edit`/`Bash` whose effective target is under `.claude/`, unless the path is a Claude-owned read-only target the user explicitly allowed (none in current scope). This second guard catches the cases the static lint can't see.

### R2 — A3-driven "auto-load" mechanism quietly writes back into `.claude/`

| Field | Value |
|---|---|
| Severity | **Critical (L10.d)** |
| Likelihood | **M-H** |
| Preconditions | Spec phase picks a mechanism without explicitly checking it against L3; OR mechanism is L3-clean at design but a follow-up convenience PR adds a "register with Claude" step. |

**Where it fires.** A3 says "mirror `.claude/rules/`." The path of least resistance for an Implementer is to symlink `.claude/rules/claudechic` → `~/.claudechic/rules/`, or to write a `.claude/settings.json` patch adding `additionalDirectories: ["~/.claudechic/rules"]`. Both *appear* to honor "no claudechic content inside `.claude/`" (the content is elsewhere), but **a symlink IS a directory entry** — creating it is a write into `.claude/`. Same for editing `.claude/settings.json`.

**Detection.** Easy if the lint in R1 is comprehensive. Easy to *miss* if the lint only checks for regular-file writes. The lint must explicitly include:
- `Path.symlink_to` where the *symlink* (not its target) is under `.claude/`
- Any `open(".../.claude/settings.json", "w"|"a"|"r+")` or `json.dump` to that path
- Any `subprocess` call invoking `claude config set` or `claude --add-dir` (which mutates `.claude/settings.json` indirectly)

**Mitigation.** Require the spec to name its A3 mechanism explicitly *and* state the L3 invariant it preserves, in one sentence each. Acceptable shapes (non-exhaustive):
- (a) **SDK-side injection that reads from `.claudechic/rules/`**: claudechic loads files at session start and passes them via `system_prompt_extra` or equivalent. No `.claude/` touch. *Caveat:* per A3, this might not satisfy "mirror" — see V-ERR-1.
- (b) **One-time user-consented `claude config set`**: claudechic prompts the user once to add `~/.claudechic/rules/` to Claude's `additionalDirectories`. The write is performed by `claude` (the user's tool), not by claudechic — but claudechic *requested* it. The line "claudechic must never write any file inside any `.claude/` directory" is preserved literally; the spirit is debatable. Spec must call this out, not bury it.
- (c) **Symlink inside `.claudechic/` pointing into `.claude/` for read-only access** is fine and L3-clean; the inverse (symlink inside `.claude/` pointing into `.claudechic/`) is an L3 violation.

The detectable failure: the spec writes "use `additionalDirectories`" without specifying *who* writes the settings.json line. If the answer is "claudechic does it on first run," that's an L3 violation regardless of how clean the rest of the design is.

### R3 — Workflow phase docs containing `.claude/rules/...` strings cause spawned agents to write there

| Field | Value |
|---|---|
| Severity | **High (L10.b)** |
| Likelihood | **H** |
| Preconditions | The vision's L15 / A3 work removes the `context_docs.md` phase from the onboarding workflow but leaves stale references to `.claude/rules/` elsewhere. |

**Where it fires.** Concrete instances surfaced by grep:
- `claudechic/workflows/onboarding/onboarding_helper/identity.md:10` — "Installing context docs into `.claude/rules/`"
- `claudechic/workflows/onboarding/onboarding_helper/context_docs.md:3, :14, :29` — phase instructions tell the agent to write into `.claude/rules/`
- `claudechic/workflows/onboarding/onboarding.yaml:17, :21` — hint message and `file-exists-check` keyed on `.claude/rules/claudechic-overview.md`
- `claudechic/global/hints.yaml:94` — `context_docs_outdated` hint message tells the user to "Run /onboarding to update your `.claude/rules/` files"
- `claudechic/hints/triggers.py:26–80` — `ContextDocsDrift` reads from `.claude/rules/` (read-only — fine) but the hint it raises directs the user to run a command that *writes* there

**Detection.** Three layers:
1. Lint extends to `*.md` and `*.yaml` files under `claudechic/`: any string matching `\.claude/(rules|hooks|skills|hints_state)` in workflow phase docs / hint messages is a finding.
2. Runtime guard: the `can_use_tool` deny-list catches it if a doc slips through and an agent acts on it.
3. The `file-exists-check` advance-check at `onboarding.yaml:21` must be repointed or removed; if it's left checking `.claude/rules/...` after the migration, the workflow advance-gate becomes uncrossable.

**Mitigation.** The spec must include a "phase-doc-and-hint string sweep" task with an explicit list of files to update — not "audit all docs," which is too vague to be testable. The list above is the floor; spec phase should re-grep before commit.

### R4 — `claudechic/hints/state.py:127` `_STATE_FILE` regression

| Field | Value |
|---|---|
| Severity | **Med (L10.b)** |
| Likelihood | **L** post-fix; **VH** if the constant is missed |
| Preconditions | Spec phase delivers a config-path move but doesn't audit module-level constants. |

**Where it fires.** `_STATE_FILE = ".claude/hints_state.json"` is a module-level constant. The vision §"`.claude/`-write sites to relocate" lists this path explicitly. If the constant moves but tests still pass against the old path, the file ships at the right path *for the test* but the wrong path for users — catch is dependent on the test setup using the production constant.

**Detection.** Boundary lint catches the literal. Tests that import `_STATE_FILE` directly catch divergence. Tests that hardcode `.claude/hints_state.json` independently are an L10.c trap (test passes, prod broken in the other direction).

**Mitigation.** Require any test in `tests/test_hints*.py` to import the constant rather than re-typing it. Add a single `test_hint_state_path_under_claudechic` test that asserts `".claudechic"` in `str(_STATE_FILE)` and `".claude/" not in str(_STATE_FILE)`.

### R5 — Future contributor adds a write-site under `.claude/` because the existing pattern is still in `git log`

| Field | Value |
|---|---|
| Severity | **High (L10.c/d)** |
| Likelihood | **M** |
| Preconditions | No CI-enforced lint; review process relies on human memory of L3. |

**Where it fires.** Six months from now, someone copies the *old* `phase_context.md` pattern from a pre-restructure commit because they're "doing what the existing code does."

**Mitigation.** L3 is a *standing* invariant, not a one-time fix. The lint test must be in CI, must fail the build, and must have a comment in `tests/test_boundary.py` (or wherever) saying "if this fails, see issue #24 and L3 in vision." Without that comment, the next person adds an `# allowlist` and moves on.

---

## 2. A3 + L3 interaction risks

Already partially covered by R1/R2/R3. The mechanism-by-mechanism breakdown:

### R6 — Mechanism enumeration table

| Mechanism | Mirrors `.claude/rules/`? | L3 clean? | Notes |
|---|---|---|---|
| Symlink `.claude/rules/claudechic` → `~/.claudechic/rules/` | Yes — Claude scans normally | **No** — the symlink is a directory entry inside `.claude/` | The symlink-creation operation is a write into `.claude/`. Strict L3 reading: violation. |
| Symlink `~/.claudechic/rules/claude_rules` → `~/.claude/rules/` | No — wrong direction | Yes | This makes claudechic *see* Claude's rules; doesn't make Claude see claudechic's. Useless for A3. |
| Edit `.claude/settings.json` `additionalDirectories` (claudechic does it) | Yes | **No** — write into `.claude/` | Same violation, in JSON form. |
| Prompt user to run `claude config set additionalDirectories ~/.claudechic/rules` | Yes — via Claude's own write | Borderline — claudechic *requested* the write but didn't perform it. Letter of L3 preserved; spirit debatable. | Requires user consent flow; one-time. |
| SDK `system_prompt_extra` from `.claudechic/rules/` files at session start | Behaviorally yes (auto-loaded, file-based) but path-different — agent doesn't see it as `.claude/rules/`. A3 explicitly says "rather than relying on system-prompt presets" — this is rejected by the A3 phrasing. | Yes | Only path that's both L3-clean and doesn't need user interaction. Tension with A3 phrasing — see V-ERR-1. |
| Hooks-based injection (Claude Code hooks reading `.claudechic/rules/`) | Behavior similar to rules but plumbing different. A3 also explicitly rejects "hooks alone." | Depends — if hook config lives in `.claude/settings.json`, see row 3. | Mostly redundant with `system_prompt_extra` plus a registration step that *itself* writes into `.claude/`. |
| Per-tool-call injection from `can_use_tool` callback / pre-tool hook | Per-call, not "auto-loaded as rules." | Yes | Doesn't satisfy L15 "session start" requirement; also doesn't mirror rules behavior. |
| **Dual-write detection** test (any time a content file appears in both `.claude/` and `.claudechic/`, fail) | N/A | Helps preserve L3 over time | A *guard rail*, not a mechanism. Recommended regardless. |

Severity: **Critical (L10.d)** if the spec picks a row marked "No" without explicit acknowledgment. **High (L10.c)** if the spec picks the "borderline" row without specifying who performs the write. **Med** for any L3-clean row that requires user-visible setup steps not in the spec.

### R7 — A3-mechanism testability gap

| Field | Value |
|---|---|
| Severity | **High (L10.b)** |
| Likelihood | **H** if not addressed in spec |

The "mirror `.claude/rules/`" requirement is a behavioral spec, not a structural one. How does the Tester verify that an agent treats `.claudechic/rules/foo.md` as "rule-equivalent context"? You can only check that:
- The content was injected into the agent's prompt at the expected time.
- The agent's behavior changes in response to a marker in that content (e.g., a sentinel rule like "if asked your name, reply 'CHIC-TEST-7'" — then run a test that asks).

The spec must include the test mechanism, not leave it to the Tester to invent. Otherwise the Implementer ships a mechanism that *looks* like rules but isn't actually loaded, and there's no way to fail the test without authorial knowledge of how rules differ from "any other prompt content."

---

## 3. Override resolution edge cases

### R8 — Same-workflow defined at multiple tiers, but partially

| Field | Value |
|---|---|
| Severity | **Critical (L10.d)** |
| Likelihood | **H** without an explicit merge policy |

**Scenarios.**
| Scenario | What "project wins" means here? |
|---|---|
| (i) `project_team` workflow YAML at all 3 tiers | Project's manifest is loaded; user/package ignored. Fine if the spec says exactly this. |
| (ii) `project_team` at package + project; user only redefines one phase | Does the user-tier phase merge into the package manifest, then get overridden by project? Does it merge into project? Does the user manifest replace the whole workflow even though it only defines one phase? |
| (iii) `project_team` at package; project overrides one role-folder file (e.g. `coordinator/leadership.md`) but not the YAML manifest | Does the project's role file override the package's role file under the package's YAML? Or is YAML-presence-required-for-override? |
| (iv) Workflow `myflow` only at user tier, not package or project | Loads from user. Fine. But: the loader's discover function has to know to look at all 3 tiers; FDR Anomaly #3 already showed sprustonlab's loader doesn't have this. |
| (v) `rules.yaml` at package defines rule R1; user `rules.yaml` defines R2; project `rules.yaml` defines R1 with different body | Override resolution is per-rule-id, not per-file? The spec must commit. |
| (vi) `hints.yaml` at user defines hint H1; project disables H1 via `disabled_ids` | Two different mechanisms (override vs disable) interacting. Order matters. |

**Detection.** A three-tier-fixture test suite that exercises each scenario above. Scenarios (ii), (iii), (v) are silent-divergence territory: the loader produces *some* result; the question is whether it's the result the user expected. If the spec doesn't pin down the expected result, the test can't fail.

**Mitigation.** The spec must answer, in operational terms, for each of {workflows, rules, hints, MCP tools}:
- Granularity of override: per-file, per-id, per-section, per-key-within-id?
- Merge-vs-replace at granularity: "user defines X, package defines X, what happens to the parts of X user doesn't mention?"
- Tier-unique additivity: do unique items from lower tiers survive a higher-tier override of *other* items?

Without these answers, every implementation decision is a hidden override-policy decision. L14 alert: this is *exactly* the kind of question the Specification phase must answer up front, not punt to "the loader's existing behavior" — which doesn't exist for 3 tiers yet.

### R9 — Schema drift across tiers

| Field | Value |
|---|---|
| Severity | **Med (L10.b)** |
| Likelihood | **M** |

Package ships rules schema v1. User has `rules.yaml` they wrote against v0. The loader sees both, parses both with the v1 parser, fails-open per-item (per current `loader.py:62`), silently drops the user's now-malformed rules. User's "project tier project_team override" appears to be in effect, but their per-user customizations are silently gone.

**Detection.** Hard. Per-item fail-open *by design* (loader.py docstring: "fail open per-item — Items that fail validation are skipped (logged, not raised)"). Logs are easy to miss.

**Mitigation.** When loading from non-package tiers, escalate parse failures from "log and skip" to "show in the UI" — a small notification chip in the status bar, not a popup. The spec needs to call this out; the existing loader's silent-skip is a feature for package-tier (resilience) and a bug for user/project tiers (silent data loss).

### R10 — Empty tier directories vs missing tier directories

| Field | Value |
|---|---|
| Severity | **Low (L10.a)** |
| Likelihood | **M** |

Loader behavior is currently `if global_dir.is_dir(): ...` (loader.py:134) — missing directory is silently a no-op. Three tiers means three opportunities for "I created `~/.claudechic/` but forgot the `workflows/` subfolder, why aren't my workflows showing up?" Silent. No error.

**Mitigation.** Trivial: log at INFO when a tier directory is missing entirely (distinguishes "you didn't configure this tier" from "this tier is empty"). Optional: surface in the workflow picker UI ("user tier: no workflows" vs "user tier: not configured").

---

## 4. L10 lost-work analysis on the A2 cherry-pick set

The A2-locked pull set: `9fed0f3`, `8e46bca`, `d55d8c0` (selective), `f9c9418`, `5700ef5`, `7e30a53`. Skip set: `26ce198`, `0ad343b`, `fast_mode_settings.json`.

Concrete file footprint (from `git show --stat`):

| Commit | Touches |
|---|---|
| `9fed0f3` | `claudechic/defaults/workflows/project_team/coordinator/leadership.md`, `claudechic/mcp.py` |
| `8e46bca` | `claudechic/app.py` (5+/2-) |
| `d55d8c0` | `claudechic/app.py` + ~85 new files under `claudechic/defaults/...` (loader code is the selective bit; the YAML is the rest) |
| `f9c9418` | `claudechic/app.py` (71+), `claudechic/commands.py` (60+), `claudechic/formatting.py` (6+), `tests/test_model_selection.py` (new, 194) |
| `5700ef5` | `agent.py`, `agent_manager.py`, `app.py`, `commands.py`, `config.py`, `widgets/layout/footer.py`, plus 6 test files |
| `7e30a53` | `agent.py`, `app.py`, `widgets/layout/footer.py`, plus 3 test files |

### R11 — `9fed0f3` lands at a path the restructure has just created (timing-critical)

| Field | Value |
|---|---|
| Severity | **High (L10.b/c)** |
| Likelihood | **H** if cherry-pick precedes restructure; **L** if restructure precedes cherry-pick. |

**Where it fires.** `9fed0f3` modifies `claudechic/defaults/workflows/project_team/coordinator/leadership.md`. Today, on sprustonlab `main`, this file does not exist (the file lives at `claudechic/workflows/project_team/coordinator/leadership.md`). Per L16 the cherry-pick is "decided"; per the user-preferred order in vision §"Open for the new team to decide" #1 ("restructure first → cherry-pick → #23/#24"), the file *will* exist by the time the cherry-pick runs — IF the team honors the order. If the order is inverted, the cherry-pick lands at a non-existent path, applies textually as a new-file add, and creates a parallel doc that's never read by the new loader.

**L10 sense:** L10.b (feature non-functional post-merge — the doc is on disk but disconnected). Becomes L10.d (intent lost) if the original file at the old path is also missed by the restructure and the abast-improved version remains stranded at the new path while the unimproved version persists at an old path nobody uses. Reviewers see "the doc is in tree" and don't notice it's the wrong copy.

**Mitigation.** Spec must commit to the order (restructure first), state the order in the operational spec, and add an integration test that the loader actually loads `coordinator/leadership.md` from `claudechic/defaults/workflows/project_team/` — i.e., reads the bytes the cherry-pick put there.

### R12 — `d55d8c0` "selective" pull is a hand-curated cherry-pick

| Field | Value |
|---|---|
| Severity | **Critical (L10.d)** |
| Likelihood | **H** |

**Where it fires.** A2 says "Manifest loader fallback-discovery logic only — loader code, not bundled YAML content." `d55d8c0` is one commit that bundles ~85 files of YAML *and* changes `claudechic/app.py`'s loader-discovery logic. There is no `git cherry-pick -- path/...` short form for "take this commit's app.py change but not its file additions"; the puller has to:
1. `git cherry-pick --no-commit d55d8c0`
2. Manually `git restore --staged claudechic/defaults/...` and `rm -rf claudechic/defaults/...` for the YAML
3. Verify `app.py` carries the loader change
4. Commit

This procedure is error-prone in two directions:
- **L10.a:** puller forgets step 1's `app.py` change altogether — loader regression on sprustonlab. Visible in tests *if tests cover fallback discovery*; otherwise silent.
- **L10.d:** puller takes step 1's `app.py` change but the change *assumes* the bundled YAML is at `claudechic/defaults/...`, which on sprustonlab post-restructure it *will be* (because the restructure put it there). Looks fine. But the abast `app.py` change was written against abast's loader-discovery shape, which may not match sprustonlab's restructured loader. Cherry-pick succeeds, behavior diverges silently from both forks' intent.

**Mitigation.** The spec must:
- Say explicitly which lines/hunks of `d55d8c0`'s `app.py` change are wanted.
- Require a written "design diff narrative" for this specific cherry-pick — what behavior changes, what invariants does the loader now uphold, where does it differ from abast's intended behavior because sprustonlab's restructure made the bundled YAML live at the same path the loader-fallback expects (so the "fallback" never has to fall back).
- Probably easier: **don't** cherry-pick `d55d8c0` at all. Re-implement the fallback-discovery as part of the restructure's loader rewrite. This converts a brittle cherry-pick into a clean implementation task and removes the L10.d risk. The spec should justify *not* doing this if it chooses to keep `d55d8c0` in the pull set.

### R13 — `5700ef5` collides with sprustonlab's `config.py` restructure

| Field | Value |
|---|---|
| Severity | **High (L10.c)** |
| Likelihood | **H** |

**Where it fires.** `5700ef5` modifies `claudechic/config.py` (4 lines). The restructure work on `config.py` is far larger — the entire module is changing path (`~/.claude/.claudechic.yaml` → `~/.claudechic/config.yaml`) and likely growing tier-aware loader logic. Cherry-pick of `5700ef5` after restructure means the conflict resolver is choosing between abast's "auto" default and a config.py that has been substantially rewritten. The conflict will likely be textual ("ours" vs "theirs" on a default value), and the easy resolution ("accept ours, the restructured version") may *silently revert* the auto-permission default that A2 explicitly adopted. L10.c.

`5700ef5` also touches `tests/conftest.py` and `tests/test_config.py` — the test files will conflict with whatever test infrastructure changes the restructure introduces.

**Mitigation.** The spec must call out the specific config.py merge as needing a semantic-review step. The "auto"-as-default behavior is a user-visible promise (A2/Q3); regression-test it explicitly: a test that asserts the default `permission_mode` is `auto` after a fresh-install config load. This converts L10.c into L10.b — visible at test time.

### R14 — Skip-set drift (deliberate non-pulls becoming forgotten divergence)

| Field | Value |
|---|---|
| Severity | **Med (L10.d)** |
| Likelihood | **M** |

**Where it fires.** The skip set (`26ce198`, `0ad343b`, `fast_mode_settings.json`) is deferred to issue #25. Six months from now, abast extends `/fast` with new commits whose first-line message doesn't say "/fast" — say, "feat: add priority queue for urgent tools." If sprustonlab's #25 isn't done yet and someone sees the new commit during a future pull, they may not recognize it as part of the deferred set. Pull happens; `/fast` mode lands on sprustonlab without the original `/fast` commit because the prerequisite was deferred.

**Mitigation.** Maintain a `NON_PULLED.md` (or equivalent) ledger entry naming the deferred set *and* the trigger condition (issue #25 closure). Without the ledger, the prior-team's "deferred to #25" rationale evaporates with memory.

### R15 — Sense-by-sense L10 sweep on the pull set

| L10 sense | Cherry-pick set scenario |
|---|---|
| **L10.a — never on main** | If the spec phase does not produce a pull-batch checklist, individual commits get triaged out and forgotten. `9fed0f3` (docs-only, low salience) is the most likely victim. **Detection:** post-pull, run `git log --oneline ${abast_main}..HEAD -- {paths from each cherry-picked commit}` and compare to A2's pull list. **Mitigation:** the spec includes the pull list as a checkbox in the testing phase. |
| **L10.b — non-functional post-merge** | `f9c9418` (full model ID) lands cleanly on `formatting.py` (no sprustonlab churn) but the test file `test_model_selection.py` may rely on test fixtures the restructure broke. **Detection:** the test suite runs after each cherry-pick and fails. **Mitigation:** explicit "run tests after each cherry-pick batch" step in the operational spec. |
| **L10.c — reverted in conflict resolution** | `5700ef5` config.py vs restructured config.py (R13). Also: `5700ef5` `agent.py`, `agent_manager.py` are in FDR §7d "quiet zone" — but `5700ef5` *itself* edits them, so the quiet-zone classification is broken the moment the cherry-pick lands. The restructure work *probably* doesn't touch these files (they aren't in the file-move inventory), so L10.c risk is moderate; but if any restructure-driven change does sweep through them (e.g., import path updates from `workflow_engine` → `workflows`), conflict will land. **Detection:** explicit "re-test that auto-perm is the default" + "re-test Shift+Tab cycles auto" after each cherry-pick. **Mitigation:** see R13. |
| **L10.d — intent lost even if code survives** | The dominant risk for `d55d8c0` (R12) and the dominant risk if the spec is silent about override-resolution semantics (R8). Also the dominant risk if A3 mechanism is picked without spelling out which "mirror" reading it adopts (R2 / V-ERR-1). |

---

## 5. Hot-file collision risks

### R16 — `claudechic/app.py` triple-collision

| Field | Value |
|---|---|
| Severity | **High (L10.c)** |
| Likelihood | **H** |

**Where it fires.** `app.py` is hit by:
1. The restructure (rewrite the `phase_context.md` write sites at lines 1623, 1635, 1648, 1822, 1834, 1849, 1925; update workflow-discovery import paths from `workflow_engine` → `workflows`).
2. `8e46bca` (5+/2− on line range that contains `_PKG_DIR` / workflows resolution).
3. `f9c9418` (71+ on model-id selection startup wiring).
4. `5700ef5` (11+ on permission-mode startup default).
5. `7e30a53` (5+ on Shift+Tab cycle handler).
6. `d55d8c0` (14 lines on loader-fallback init — but only "selective" per A2).
7. The #23 settings-screen wiring (registers the `/settings` modal).
8. The A3 mechanism (probably injects something at session start).

**Eight separate concerns, three of them adding code to the same `app.py` startup region.** Mechanical merge is plausible if each touches a different function (FDR §5 commentary: "abast's `app.py` edits touch *different functions* than sprustonlab's"), but the *cumulative* state of `app.py` after all eight is a function nobody designed.

**The semantic risk** is not the mechanical conflicts — those will be loud. The risk is the cumulative *initialization order*: if #23 settings registration must happen before A3 injection, but `f9c9418`'s model-id setup runs in between, and `5700ef5`'s permission-default setting depends on the model being selected first, and... at some point an integration test fails for a reason no one can quickly pin to a single change.

**Mitigation.** The spec should commit to a *single* canonical init sequence in `app.py` and document it as a numbered list. Each cherry-pick gets re-applied against that canonical sequence, not blindly merged. After the canonical sequence is in place, future hot-file PRs touch it consciously (a code review checklist item: "if you're modifying `_init_*` in app.py, update the canonical-sequence comment").

### R17 — `claudechic/commands.py` collision: settings registration vs `f9c9418` vs `5700ef5`

| Field | Value |
|---|---|
| Severity | **Med (L10.b)** |
| Likelihood | **H** |

**Where it fires.** `commands.py` gets a `/settings` registration from #23 plus `f9c9418`'s model-related command additions (60 lines) plus `5700ef5`'s small touch (4 lines). All three are almost certainly insertion-collisions — adding new entries to a dispatch table or new handlers — rather than edit-collisions. Mechanical merge is fine *if* the merged dispatch table doesn't accidentally drop an entry. Drops here are silent (the command becomes "unknown" and the user sees a generic error rather than a regression).

**Detection.** Smoke test: invoke each registered command after merge and confirm it routes to a handler. The /commands listing test should be updated to include all newly-added commands.

**Mitigation.** A single "commands manifest" test that asserts the set of registered commands matches an expected list (one item per cherry-picked feature plus the existing baseline). Easy to add; catches drops.

### R18 — `tests/conftest.py` collision

| Field | Value |
|---|---|
| Severity | **Med (L10.b)** |
| Likelihood | **M** |

**Where it fires.** `5700ef5` touches `tests/conftest.py` to set `permission_mode="auto"` in the default fixture. The restructure work plausibly extends the fixture set (new fixtures for tier directories, boundary-lint, etc.). Conflict at the fixture level can produce tests that pass individually but fail in suite ordering (a fixture override unexpectedly applied).

**Mitigation.** Standard. Keep fixture changes small and localized. If conflict, prefer additive over replacement.

### R19 — "Mechanical" merges that destroy semantics

| Field | Value |
|---|---|
| Severity | **High (L10.c/d)** |
| Likelihood | **M** |

The general pattern: a textually-clean merge produces a function that, *after merge*, calls things in an order neither side intended. This is not a hypothetical for `app.py` — see R16. Specific scenario: `8e46bca` ("use resolved `workflows_dir`") relies on `workflows_dir` being a particular resolved value at the call site; the restructure's loader rewrite changes how `workflows_dir` is resolved (now it walks 3 tiers); the cherry-pick textually applies but the *resolved value* it consumes is the new walking resolver's output rather than the simple resolver abast was fixing. Possibly correct, possibly subtly wrong (does the 3-tier resolver return the package tier when the caller expected the project tier?). The merge looks fine; the behavior shifts.

**Detection.** Every cherry-pick gets a "design diff narrative": one paragraph per pull, naming what observable behavior changed and which invariant it now maintains. The spec must mandate this artifact — without it, R19 is undetectable until a user reports a bug.

---

## 6. Worktree symlink (BF7) — `claudechic/features/worktree/git.py:293–301`

### R20 — Silent regression: `.claudechic/` state stops following worktrees

| Field | Value |
|---|---|
| Severity | **High (L10.b/c)** |
| Likelihood | **H** if not added; **L** if added |

**Where it fires.** Lines 293–301 currently symlink `<main_wt>/.claude` into each new worktree, so hooks/skills/local Claude settings carry over. Vision §"Worktree symlink (BF7)" says the parallel `.claudechic/` symlink must be added in the same code site, or the worktree feature silently regresses (`hints_state.json`, `phase_context.md`, project config, A3 rule files all stop carrying over).

**The user's question is about silent failure modes.** Concretely:
1. `worktree_dir / ".claude"` symlink exists. `worktree_dir / ".claudechic"` does not (post-restructure, before the BF7 fix). User opens claudechic in the new worktree:
   - `ProjectConfig.load(worktree_dir)` finds no `.claudechic/config.yaml`, returns defaults (config.py:111). User's project-tier customizations are silently absent.
   - `HintStateStore(worktree_dir)._path = worktree_dir/.claudechic/hints_state.json` — file absent, hints fresh-start (state.py:144 `_load`). All "show-once" hints fire again. All `dismissed=True` markers reset.
   - The phase context file (currently `.claude/phase_context.md`, post-restructure `.claudechic/phase_context.md`) is absent — agent loses awareness of its current workflow phase.
2. Worse: the symlink is *added* but points at a path that no longer exists because the restructure of the *main* worktree's `.claudechic/` happened mid-feature. Dangling symlink. `is_dir()` returns False. Same as case 1, but harder to diagnose because `ls` shows the symlink.

**Other code paths that assume `.claude/` symlinks exist** (the user's specific question):
Grep for `.claude` access patterns:
- `claudechic/config.py:17` — old global config path under `~/.claude/`. After restructure, moves to `~/.claudechic/`. Worktree-irrelevant.
- `claudechic/app.py:1848–1925` — `phase_context.md` write/read sites under `Path.cwd() / ".claude"`. After restructure these become `.claudechic/` writes. They write to *cwd*, not main-worktree, so the symlink isn't in the path — but the user *expects* the file to exist in worktrees. Without the BF7 symlink for `.claudechic/`, each worktree gets its own `phase_context.md` which is fine for "this worktree's current phase" but breaks if the user expects phase to be a project-wide notion.
- `claudechic/hints/state.py:127, :146` — `_STATE_FILE = ".claude/hints_state.json"`, joined to `project_root` (not `cwd`). `HintStateStore` is constructed with whatever directory the caller passes. If the caller passes the worktree path, hint state is per-worktree. If main worktree, shared. The current symlink approach made it shared even when called per-worktree — *the symlink hides whether the code's design intent is shared or per-worktree*. Removing the symlink and not adding a parallel reveals the underlying coupling.
- `claudechic/hints/triggers.py:46` — `state.root / ".claude" / "rules"` for `ContextDocsDrift`. Read-only; survives the symlink loss because every worktree can re-read the symlink target. After A3 / R3 mitigation removes this trigger entirely, moot.
- `claudechic/onboarding.py:265` — `HintStateStore(project_root)` for the dismiss marker. Same as state.py concerns above.

**The BF7 fix is non-optional and has a non-trivial design question:** is `.claudechic/` per-worktree or per-repo? Per-repo (symlink, like `.claude/` today) means project config edits in one worktree show up in all worktrees — usually what users want. Per-worktree (no symlink, fresh `.claudechic/` per worktree) means hint dismissals don't bleed across worktrees and you can A/B test claudechic configs — sometimes what users want. The spec must commit to one.

**Mitigation.** Spec commits to per-repo (symlink, matching current `.claude/` behavior — least surprise). Adds an integration test: `git_worktree_add → expect target_worktree/.claudechic exists and resolves to source/.claudechic`. The test must cover the dangling-symlink case (source's `.claudechic` doesn't exist yet because user hasn't created the dir).

---

## 7. Migration absence (L17)

### R21 — Issue-author and Arco hit silent file-loss on first pull

| Field | Value |
|---|---|
| Severity | **Med (L10.b)** |
| Likelihood | **H** |

**Where it fires.** L17 says no migration logic. After this work ships:
- Issue-author's `~/.claude/.claudechic.yaml` is read by neither old nor new code path (old path: deprecated; new path: missing). User's analytics ID, theme, default permission mode, worktree path template — all silently revert to defaults. `_load()` (config.py:21) sees `CONFIG_PATH.exists() == False`, takes the "new install" branch (config.py:52), generates a fresh UUID for analytics ID. **Analytics history is broken** because the new ID is different. Worktree path template reverts to `null`. Default permission mode reverts to `default` (or `auto` post-A2 — but in either case, not the user's customization).
- Arco (abast fork) similarly. Plus: their existing `~/.claude/.claudechic.yaml` may have user-tier-only keys (e.g., `analytics.id`) that are now expected at user tier under the new layout but the code is now looking at `~/.claudechic/config.yaml`.
- Both users' `<repo>/.claude/hints_state.json` is invisible to the new `_STATE_FILE`. All hints they've dismissed re-appear. Welcome-screen `onboarding_dismissed` (onboarding.py:41) marker is lost — welcome screen reappears.
- Both users' `<repo>/.claude/phase_context.md` (if any active workflow) is invisible. The active agent loses its current-phase awareness silently — *and* the new code's `_remove_phase_context` (app.py:1925) never cleans up the old file because it's looking at the new path. The old `.claude/phase_context.md` lingers as orphan state.

**What manual steps must be documented?** Concretely:
1. `mv ~/.claude/.claudechic.yaml ~/.claudechic/config.yaml` (after creating `~/.claudechic/`).
2. `mv <repo>/.claude/hints_state.json <repo>/.claudechic/hints_state.json` per repo.
3. `rm <repo>/.claude/phase_context.md` if present (or move; either fine — phase context is regenerable on next workflow advance).
4. After all of above: verify `~/.claude/.claudechic.yaml` and `<repo>/.claude/hints_state.json` no longer exist (so the L3 boundary lint will keep passing).

**What state is silently lost or duplicated?**
- Analytics ID: **lost** unless the user manually moves the file. New ID generated on next launch.
- Hints dismissals: **lost** without manual move. All dismissed hints re-fire.
- `onboarding_dismissed`: **lost** without manual move.
- Worktree path template, theme, default permission mode: **lost** without manual move.
- Phase context: lost; harmless because it's regenerable.
- Old paths: **duplicated** (the file exists in `.claude/` *and* nothing exists in `.claudechic/`; on first run that creates `.claudechic/config.yaml`, both files exist). The boundary lint will fail in CI because `.claude/.claudechic.yaml` still exists in the user's home dir — but that's the user's home, not a CI surface, so probably moot. Still, if anyone runs the lint locally, it lights up.

**Mitigation.** The spec must:
- Include in the PR description / release notes a four-line user-facing migration block: the four `mv` / `rm` lines above.
- *Prefer*: add a *one-shot* startup-time check that detects `~/.claude/.claudechic.yaml` and either (a) prints a one-line message "claudechic settings have moved; run: `mv ~/.claude/.claudechic.yaml ~/.claudechic/config.yaml`" or (b) does the move automatically on the user's behalf. (b) might violate L17's "no migration logic" letter; the coordinator should clarify whether L17 means "no auto-migration code" or "no design effort on migration." A startup print is *not* migration code; it's a one-line warning. Recommended floor.

L17 was reasonable; it stops short of nothing-at-all. A spec that ships *with* the silent file-loss listed above is honoring L17 by the letter but failing the issue-author and Arco in spirit. A1 invocation: this is a place where the spec phase should escalate, not silently absorb.

---

## 8. The L14 trap

### R22 — Spec phase mixes rationale into operational instructions

| Field | Value |
|---|---|
| Severity | **High (L10.d for the project)** |
| Likelihood | **H** without explicit guard |

**The concrete test the team should apply to spec docs.** The spec is L14-clean if and only if both of the following are true:

1. **Diff test:** Take any paragraph from the spec. Delete the *first sentence*. Does the rest of the paragraph still tell the Implementer / Tester *what to do*? If yes, the first sentence was probably rationale. (Heuristic, not bulletproof. Most spec paragraphs should survive this test trivially because they shouldn't have a "this matters because..." opener.)

2. **Standalone test:** Hand the spec to an Implementer who has read *only* the spec and not the appendix, vision, STATUS, or this risk evaluation. Have them describe in one sentence each:
   - "What file do I create / edit?"
   - "What goes in it?"
   - "How do I know I'm done?"
   For *every* deliverable. If any deliverable can't be answered in one sentence per question without reading the appendix, the spec has rationale-shaped gaps — operational steps that depend on understanding *why*, when they should depend only on *what*.

The Implementer test is the harder one. The reason it's harder: rationale leaks not by adding sentences but by *omitting* operational specificity that the author thought "any reasonable implementer would know." When the author thinks that, the operational answer is in the rationale, and the spec is incomplete.

### R23 — The "test" itself becomes a process gate that nobody runs

The diff test and standalone test are pointless if the rubric says "run these tests" and no one does. The test must be a deliverable — an artifact the spec author produces and the coordinator reviews — not a process the coordinator hopes was followed.

**Mitigation.** The grading rubric for the spec phase requires the spec author to attach a 1-paragraph "L14 self-check" that names which paragraphs of the spec they considered cutting and why they kept them. If the self-check is missing or empty, the spec fails the rubric. This converts a procedural test into a written artifact.

---

## 9. Cross-cutting: detection infrastructure

A summary of detection mechanisms named above, for the spec phase to consolidate into a "test infrastructure" section:

| Infrastructure | Catches |
|---|---|
| Static lint: `\.claude/[^ ]+` write patterns in `claudechic/`, `tests/`, `*.md`, `*.yaml` | R1, R2, R3, R4, R5 |
| Runtime guard: `can_use_tool` deny on `Write`/`Edit`/`Bash` whose effective target is under `.claude/` | R3 (agent-emitted writes) |
| Three-tier-fixture test suite (six scenarios in R8 + tier-unique + missing-tier) | R8, R9, R10 |
| Loader-loads-restructured-paths integration test | R11, R12 |
| Cherry-pick design-diff narrative artifact (one paragraph per cherry-pick) | R12, R13, R19 |
| Commands manifest assertion test | R17 |
| Worktree symlink integration test (with dangling-symlink case) | R20 |
| Boundary lint + cherry-pick narratives + commands-manifest test in CI | All of L3 + L10 |
| Spec L14 self-check artifact | R22 |

Each row is a deliverable. The spec phase should commit to which rows are in scope and which are deferred.

---

## 10. Top-3 risks summary (for the user)

1. **R2 + V-ERR-1: A3 mechanism choice.** The "mirror `.claude/rules/`" requirement and "no writes inside `.claude/`" constraint are in tension. The spec phase will have to pick a precise reading of "mirror." Without explicit user confirmation of which reading is acceptable, the Implementer will pick the one that's easiest to ship — likely a symlink or settings.json edit — which is an L3 violation. **Highest-leverage user clarification.**
2. **R12: `d55d8c0` selective cherry-pick.** A2 locked this commit in, but the "selective" extraction (loader code only, not bundled YAML) is a hand-curated procedure with no clean git command. Easier and cleaner: re-implement the loader's fallback-discovery as part of the restructure, skip `d55d8c0` entirely. The spec should justify keeping the cherry-pick if it does.
3. **R20 + R21: Worktree symlink + migration silence.** Two separate "silent regression" risks for the existing users (issue-author, Arco). The worktree symlink is a code task with a clear fix; the migration question is whether L17 means "no auto-migration code" or "no design effort on migration at all." Recommend the user confirm — a one-line startup warning ("your config has moved; run `mv ...`") is cheap, prevents silent data loss, and may or may not violate L17 depending on intent.

---

*End of risk evaluation (Leadership phase, first pass).*
