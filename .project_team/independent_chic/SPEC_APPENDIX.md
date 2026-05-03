# SPEC_APPENDIX — independent_chic

**Companion to:** `SPEC.md`
**Audience:** the user (for spec-exit review); future maintainers; a possible next team if this run hands off
**NOT for:** Implementer or Tester agents (they read `SPEC.md` and the axis-spec files cross-referenced from it)

This file holds everything `SPEC.md` deliberately excludes per the operational-vs-rationale separation rule the prior team locked in:

- Why each major decision was made the way it was
- What alternatives were considered and rejected
- Which user words drove which decision
- The cross-lens disagreement history
- Vision/STATUS errors the team flagged and how each was resolved
- The "what NOT to do" list — anti-patterns to watch for
- Reversal triggers — conditions under which a locked decision should be reconsidered

The Implementer and Tester do **not** need to read this file. The spec stands alone.

---

## §1 — User-words traceability

This run was unusual in that the prior team's vision document was authoritative going in. The user gave only thirteen verbatim instructions across the run, each compact. This section maps each user input to the spec sections it shapes.

### 1.1 Run kickoff

> "see issue24 vision.md as we are picking up from another team"

The opening instruction. Established that the prior team's vision document at `.project_team/issue_24/vision.md` (since renamed to `.project_team/independent_chic/vision.md`) is authoritative. Every binding constraint L1–L17 in `STATUS.md` derives from this instruction's deference to the prior team's locks.

### 1.2 Vision-phase clarifications (Q1–Q4)

**Q1 — Authority of the prior team's vision:**

> "yes, agents can check and surface issues if they find them. we all make mistakes."

→ Captured as **A1** in STATUS.md. Drives every "vision flag" entry across the lens reports and the seven entries in SPEC.md §16.1. Agents are expected to surface vision errors rather than work around them.

**Q2 — Working directory:**

> "directly"

→ Operate in `/groups/spruston/home/moharb/claudechic`. No worktree. Influences nothing in the spec text but constrained the workflow's git baseline (HEAD `317f4244…`).

**Q3 — Disposition of the deferred-decision cherry-picks:**

> "adopt"

→ Captured as **A2** + **A6** in STATUS.md. Drives SPEC.md §6.1 cherry-pick set. Three commits that the prior team had marked "UX-decision-required" become "pull": `f9c9418` (full model ID + loosened validation), `5700ef5` (auto permission mode default), `7e30a53` (auto in Shift+Tab cycle).

**Q4 — Vision amendment on agent awareness:**

> "for #4 it needs to mirror the .claude/rule behavior"

→ Captured as **A3** in STATUS.md. Drives SPEC.md §4 (Group D). The single most-discussed user instruction in the run; produced three lens-level analyses on what "mirror" actually means in implementable form. See §4.4 below for the full mechanism rationale.

### 1.3 Vision approval

> "approved"

→ Locked the vision + A1 + A2 + A3. Triggered advance from Vision phase to Setup.

### 1.4 Project rename

> "Lets rename to somthing that fits the goals better, how about independent_chic"

→ State directory renamed `issue_24` → `independent_chic`. Captured in STATUS.md run identity.

### 1.5 Leadership-phase team shape

> "1) continue. 2) no"

→ Q1 = continue to Leadership; Q2 = no supporting agents beyond the four lenses. Drove team composition: only Composability, Terminology, Skeptic, UserAlignment. No Researcher, no LabNotebook.

### 1.6 Leadership-phase user resolution round (Q1'–Q9')

After the four lens reports landed, nine cross-cutting questions were surfaced. The user's verbatim answers and what each shaped:

**Q1' — Agent-awareness mechanism interpretation:**

> "it needs to behave the same, we can touch .claude in ways we are sure are not destructive, overwriteing a sesttings file is out. adding a symlink is out as it is not supported on windows."

→ Captured as **A4** in STATUS.md. Drives SPEC.md §4 (mechanism design constraints) + §11 (boundary allowlist) + §11.4 (symlink prohibition, scoped to agent-awareness mechanism). Combined with Q4 above, this is the most operationally-determinative user instruction in the run.

**Spec-exit follow-up:**

> "add symlink to .claudechic and make an issue in the repo about worktrees and windows."

→ Scopes A4's symlink prohibition. Symlinks are forbidden in the agent-awareness mechanism (Group D, where cross-platform is required); permitted at the worktree code site for `.claudechic/` filesystem-state propagation (mirroring the existing `.claude/` symlink, which also lacks Windows support). Windows portability tracked at [sprustonlab/claudechic#26](https://github.com/sprustonlab/claudechic/issues/26). Drives the SPEC.md §10 reversal (per-worktree fresh state → parallel symlink) + SPEC.md §11.4 scoping (no symlinks in agent-awareness only).

**Q2' — Config layering:**

> "config in 2 is what I want. everyhting is the other things."

→ Captured as **A5** in STATUS.md. Confirms L8: config keys 2-tier (user + project), no package-tier config file. "Everything in 3 levels" applies to the four content categories, not to config. Drives SPEC.md §3 (loader scope is content categories only) + §7.3 (settings UI).

**Q3' — Auto-mode startup default:**

> "yes."

→ Captured as **A6** in STATUS.md. Reaffirms `5700ef5` cherry-pick. Drives SPEC.md §6 + §7 (auto-mode footer label, Shift+Tab cycle).

**Q4' — Boundary rule strength:**

> "primary."

→ Captured as **A7** in STATUS.md. Softens L3 from absolute to primary-state-only. Drives SPEC.md §11 boundary allowlist structure (permitted/forbidden tables instead of absolute prohibition). Combined with Q1's "no symlinks, no overwrites," produces the spec's dual-classification model.

**Q5' — Selective `d55d8c0` cherry-pick:**

> "you can drop it."

→ Captured as **A8** in STATUS.md. Removed from the cherry-pick set. Drives SPEC.md §6.1 (commit dropped from table) + §3.1 (loader rewrite framed as "small generalization of `discover_manifests`," not "fresh fallback discovery system" — Skeptic's CW-1 framing).

**Q6' — Existing-user silent loss:**

> "yes, we know what we are doing."

→ Captured as **A9** in STATUS.md. Re-classifies Skeptic's "silent state loss for issue-author and Arco" finding from a failure mode to an accepted tradeoff. Drives SPEC.md §2 (no migration warning required) + the note in this appendix's reversal triggers (§9) about when this should be reconsidered (only if a non-developer user joins the install base).

**Q7' — Vision §7 abast relationship framing:**

> "trim we cross polinate not just pull from one."

→ Captured as **A10** in STATUS.md. Retires the words "convergence" and "merge program" from spec / docs / UI prose. Drives the canonical-glossary revision (§6.4 cross-pollination) and the terminology-checklist item in SPEC.md §14.3 about zero forbidden-word occurrences.

**Q8' — Single vs two-piece agent awareness:**

> "two."

→ Captured as **A11** in STATUS.md. Reaffirms L15. Drives SPEC.md §4.2 (three hook registrations: SessionStart for always-on + first-read piece, PreToolUse for first-read tool-call trigger, PostCompact for refresh).

**Q9' — Settings UI smaller features (welcome-screen access, workflow-ID discovery, disabled-IDs listing, button-vs-command parity):**

> "let the team decide. fine to pospond if too much."

→ Captured as **A12** in STATUS.md. UIDesigner placed all four in scope (zero postponed). Drives SPEC.md §7.1 (in-scope UI surfaces).

### 1.7 Specification-phase team shape

> "B"

→ Selected the full workflow-prescribed team for Specification: existing four lens authors + UIDesigner + Composability-spawned axis-specialists. Drove the team count from five (Leadership) to ten (Specification). Did not override Q1.6's "no" on Leadership-phase supporting agents (different phase, different question).

### 1.8 Spec-exit late amendments

After the synthesis pass produced SPEC.md, four things happened at the spec-exit checkpoint that triggered substantive revisions. Recorded here for the trail.

**Item 1 — worktree symlink reversal.**

> "add symlink to .claudechic and make an issue in the repo about worktrees and windows."

→ Captured at §1.6 Q1' "Spec-exit follow-up" plus this section. Reverses the synthesis pass's "no symlink, per-worktree fresh state" decision back to the vision's original symlink approach; scopes A4's no-symlinks rule down to the agent-awareness mechanism only; tracks Windows portability at sprustonlab/claudechic#26. See §6.1 (vision-flag reclassification) and §9 (revised reversal triggers) for the full rationale.

**Item 2 — SDK uncertainty detail request.**

> "please give me more detail please."

→ Not a directive; a request for the specific mechanism by which the agent-awareness module would deliver content. The detailed answer (covered the session-start hook, the pre-tool-use hook, the additional-context field, three SDK uncertainties with degradation paths) was given in coordinator chat. Triggered the next item.

**Item 3 — rules-format mirror was not faithful.**

> "No, please read how .cluade/rules work as YAML file with a header and dir spec."

→ Pointed out that real `.claude/rules/` files use YAML frontmatter (with `paths`/`globs` for path targeting). The synthesized spec's mechanism did not reproduce this. Triggered web research on the actual format and on how to mirror it without reimplementing.

**Item 4 — research before reimplementing.**

> "is there anything we can use from the internet about how cluade code does this so we don't have to reimpliment everything? please spwqn a researched for that. the alternative IS to have this copied to the .calude/rules folder on startup and added to settings to disable"

→ Spawned researcher; finding: the Claude Agent SDK already loads `.claude/rules/*.md` natively, and claudechic already enables this at `app.py:969`. The earlier Group D mechanism was reimplementing what the SDK provides for free. User approved Option B (idempotent install of bundled context files into `~/.claude/rules/` with `claudechic_` filename prefix; SDK does the rest):

> "approve option B, fine with all answers. I want to copy as default and the settings have a way to desable that. there are no tiers here right? does claude reads from ~/.claude/rules?"

→ Captured as **A13** in STATUS.md. Drives the Group D collapse — see §4.4 in this appendix for the full rationale and §10.1 for the addition of `RESEARCH.md` to the deliverables list.

The user's two questions in that last instruction were answered: (a) yes, Claude reads from `~/.claude/rules/` (user tier in Claude's own tier system) and from `<repo>/.claude/rules/` (project tier) and from local-tier files; (b) no, claudechic's three-level tier system does not apply to this install — the install is flat (bundle ships, copies to one location). Claudechic's three-level system continues to apply to workflows, the global rules-and-hints YAML, and MCP tools — those are unchanged.

---

## §2 — Locked decisions and run amendments

`STATUS.md` is the canonical record of L1–L17 (prior team) and A1–A13 (this run). This section adds the rationale-anchor each one points to, for future maintainers tracing back why the spec is shaped the way it is.

### 2.1 Prior-team locks (L1–L17)

Rationale source: `vision.md` §"Locked constraints" + the prior run's `.project_team/issue_23_path_eval/` artifacts (RECOMMENDATION.md, the four lens evaluations, Appendix.md). The user adopted these wholesale per Q1; this run did not re-litigate them.

Of the seventeen, six produced operational consequences that needed careful handling:

- **L3 (boundary rule)** — softened to A7's primary-state-only by user instruction; spec encodes the softened form (§11) but Skeptic's appendix recommends locking the boundary lint to the strict-form allowlist anyway, treating A7's permission as latent.
- **L7 (per-tier directory layout)** — the spec follows L7 exactly; vision §1's "mechanism choice" framing about rules/hints siblings is treated as superseded (one of the seven A1 vision flags).
- **L10 (lost-work 4 senses)** — drove Skeptic's risk evaluation §4 (R11–R15 sense-by-sense sweep on the cherry-pick set) and shaped the spec's no-fallback-substitution framing for cherry-picks.
- **L14 (operational-vs-rationale separation)** — drove the two-file SPEC.md + SPEC_APPENDIX.md split; this very file exists because L14 binds.
- **L16 (cherry-pick selection)** — fully decided at run-start by Q3 = "adopt"; revised by A8's drop of `d55d8c0`. Final table in STATUS.md.
- **L17 (no migration logic)** — extended by A9 to forbid even one-line startup warnings; drives §2.6 acceptance behavior in SPEC.md.

### 2.2 Run amendments (A1–A12)

These twelve amendments distinguish this run from the prior team's hand-off. Each was either (a) a vision-phase amendment to the prior team's vision text, or (b) a Leadership-phase resolution of a cross-lens-surfaced ambiguity.

**A1 — agents-may-flag-vision-errors:** rationale-anchor: user's words "we all make mistakes." Operational consequence: every lens has a §"Vision flags" section, and the consolidated list lives at SPEC.md §16.1 (seven entries).

**A2 → A8 — cherry-pick disposition:** A2 was the initial decision; A8 revised by dropping `d55d8c0`. The combined final state is in STATUS.md's table and SPEC.md §6.1.

**A3 → A4 — agent-awareness intent → mechanism:** A3 captured the user's "mirror the .claude/rule behavior" intent; A4 captured the operational constraints ("non-destructive touches OK; overwrites and symlinks out"). Together they drive the entire awareness mechanism design (Group D + §11).

**A5 — config 2-tier:** confirms L8. Rationale-anchor: user's exact phrasing "config in 2 is what I want. everyhting is the other things."

**A6 — auto default:** confirms `5700ef5`. Rationale-anchor: user's "yes" to the explicit question about auto-mode startup default.

**A7 — boundary primary-state-only:** softens L3. Rationale-anchor: user's single word "primary."

**A9 — no startup warning for existing users:** extends L17. Rationale-anchor: user's "we know what we are doing." Reversal trigger documented in §9 below.

**A10 — cross-pollination not convergence:** drives the terminology contract. Rationale-anchor: user's "trim we cross polinate not just pull from one."

**A11 — two-piece confirmed:** reaffirms L15. Rationale-anchor: user's single word "two" against the literal three-options framing.

**A12 — UI smaller features delegated:** drives UIDesigner's scope decisions. Rationale-anchor: user's "let the team decide. fine to pospond if too much." All four ended up in scope; no postponements.

---

## §3 — Architecture rationale: the meta-shape

This section explains why the spec's overall shape looks the way it does. Per-group mechanism rationale follows in §4.

### 3.1 Why three tiers for content, two for config

Three tiers (package / user / project) for the four content categories — workflows, rules, hints, MCP tools — because the user explicitly said "everything in 3 levels" referring to those four categories (vision §1 + Q2'). Three tiers express the natural override hierarchy: defaults that ship with the package; per-user customizations that apply across all projects; per-project overrides that apply only inside one repo.

Two tiers (user + project) for config keys because the user explicitly carved config out: "config in 2 is what I want." Defaults live in code, not in a `claudechic/defaults/config.yaml` file. The rationale: config keys are typed key/value pairs with code-level defaults; the package-tier "default" is the dataclass field default in Python source. Adding a third tier (a YAML file shipping with the package) would be redundant — same intent expressed twice in different syntaxes. The user spotted this; the prior team had already locked it as L8.

### 3.2 Why one mechanism for agent awareness AND phase-context

Composability flagged it (R6.5 / INV-9). Skeptic confirmed (R-S2). The two needs are functionally identical:

- Both deliver file-based content from `.claudechic/` to a Claude session
- Both operate at the same SDK extension surface (hooks)
- Both have the same boundary-class concern (must not write inside `.claude/`)
- Both are first-firing-on-session-start with refresh-on-events

Maintaining them as two parallel injection systems would let them diverge over time. The unification (one module, three registrations) collapses what Composability's earliest decomposition called Group D's six items down to two hooks plus one removal line. Skeptic's appendix §A1.2 lays out the full reasoning.

### 3.3 Why the boundary test uses a YAML registry

Two alternatives were considered (axis_boundary_test_appendix.md):

1. Hardcode the protected-file list in Python — simple, fast, but requires a code change for every new protected file.
2. Externalize to YAML — allows the protected list to grow without code changes; the list is data, not logic.

Choice: YAML registry (`tests/boundary/claude_owned_files.yaml`). Rationale: the protected-file list will grow as Claude Code adds new conventions; making it data lets a future maintainer add an entry without touching the test code. The same YAML approach extends to the write-site registry (`tests/boundary/write_sites.yaml`), giving the boundary test a uniform configuration shape.

### 3.4 Why per-chicsession (not per-activation) artifact dirs

axis_artifact_dirs_appendix.md weighs the alternatives. Per-activation (a fresh dir each time the user starts a workflow) would force the user to re-locate artifacts after every activation; per-chicsession (one dir per chicsession, reused across resumes and re-activations of the same workflow run) preserves continuity. The user model treats a chicsession as the unit of "this work I'm doing"; the artifact dir is the natural file-system expression of that unit.

### 3.5 Why "restructure first, then cherry-pick"

The user's stated preference (vision §"Open for the new team to decide" + the prior run's recommendation). Two reasons make it stick:

1. The 3-tier layout is the agreed-upon target; cherry-picks against the old layout introduce conflicts that the restructure would erase anyway.
2. abast's commits assume their own layered-defaults pattern, which differs from this run's post-restructure layout. Re-pathing cherry-picks during the merge is cleaner if the destination layout already exists.

The prior team's recommendation document at `.project_team/issue_23_path_eval/RECOMMENDATION.md` analyzed alternatives in depth. Treat that document as the rationale source for any future maintainer wanting the full alternatives-weighed analysis.

---

## §4 — Mechanism rationale per spec group

For each of the spec's eight groups (A–H), this section captures the why behind the operational what.

### 4.1 Group A — Restructure (file moves + import rewrites)

**Decision: pure file moves with `git mv` + mechanical import rewrites; no semantic changes in this group.**

Rationale: the restructure is the foundation everything else builds on. Mixing semantic changes into the move would make the rebase against `main` (or against any fork that's also moving) into a multi-axis merge instead of a single-axis path rewrite. The seven `git mv` operations are mechanically obvious; the twenty-two import rewrites are find-and-replace. By keeping Group A surgically small, the boundary test (Group H) can verify "post-Group-A state is just A1's state at new paths" — a simple, testable invariant.

### 4.2 Group B — Boundary relocation

**Decision: every claudechic-primary write site that lives inside `.claude/` today moves to `.claudechic/`; the worktree symlink for `.claude/` stays (predates A4) but the proposed parallel `.claudechic/` symlink is NOT created.**

The relocation list (per axis_boundary_test.md §10's enumerated registry) covers fourteen write-sites. Thirteen are primary-state and move; one is the worktree symlink (incidental, classification preserved).

The notable case is `<repo>/.claude/hits.jsonl` — the guardrail audit log. The prior team's vision file-move inventory missed it; the boundary-test axis-specialist caught it during scope sweep. Adding it to Group B cost nothing operationally (one more entry in the move table); leaving it out would have been a silent boundary regression.

The worktree-symlink decision deserves its own subsection (4.3 below).

### 4.3 Group C — 3-tier loader

**Decision: structural rewrite of `discover_manifests` into `walk_tiers` + `discover_manifests_single_tier`; per-category resolution through one generic `_resolve_by_id` helper; partial-override detection runs as a pipeline pre-step.**

Three sub-decisions worth recording:

**Why a structural rewrite, not a port of `d55d8c0`:** Skeptic's CW-1 finding. The dropped cherry-pick (`d55d8c0`, per A8) had hand-extracted "loader-only, not the YAML" surgery that was both brittle and committed-against-different-layout. A future Implementer reading "implement 3-tier fallback discovery" might transcribe `d55d8c0`'s logic line-by-line. To prevent that, axis_loader_resolution.md §10 explicitly forbids consulting the dropped commit. The new loader is framed as a small generalization: "today walks one (global, workflows) pair; new walks N tier-pairs and tags paths with their tier."

**Why one generic `_resolve_by_id` instead of per-parser `resolve()`:** Skeptic's R-S4 preference. All four content categories override by ID; the resolution logic is identical across them (highest-tier wins; within-tier duplicate is an error; cross-tier duplicate is the override mechanism). A single generic function called by all four parsers with a `key_fn` callback satisfies the resolution law without per-parser duplication. Composability concedes this in skeptic_review_appendix.md §A2.

**Why partial-override gets loud-loader-error + fall-through (not doc-only forbid):** the cross-lens disagreement from the user-resolution round, resolved in UserAlignment's favor (§5 below). UserAlignment argued doc-only is a foot-gun where users put one role file in `~/.claudechic/workflows/foo/role_x/` and silently get no effect. The agreed enforcement: detect partial overrides via set-difference on `Path.rglob("*")` per tier per workflow_id; loud LoadError surfaced in the TUI; fall through to the next-lower tier so the user's broken partial doesn't blow up the whole workflow; one-click "Override this workflow" affordance in the UI as the happy path.

### 4.4 Group D — Agent awareness + phase context (the most-iterated mechanism)

**Final decision (per A13): Idempotent startup install of bundled context files into `~/.claude/rules/` with `claudechic_` filename prefix, gated by a settings toggle. Claude Agent SDK auto-loads them; phase-context delivery stays as a separate dynamic mechanism.**

This section took the most iteration of any in the run. The full path:

1. **Original draft (rejected during synthesis):** custom session-start hook + pre-tool-use hook + first-read tracker, all in a new `claudechic/context_delivery/` module — claudechic implementing its own rule-equivalent injection on top of the SDK.
2. **Spec-exit user pushback:** two challenges in sequence — the rules-format mirror was actually not faithful (no YAML frontmatter / glob targeting); and we were reimplementing what already existed.
3. **Research finding:** the Claude Agent SDK ALREADY loads `.claude/rules/*.md` from user/project/local tiers natively. Claudechic enabled this at `app.py:969`. The right move: lean on the SDK, don't reinvent.
4. **Final mechanism (A13):** install-and-let-the-SDK-do-the-rest.

**Why this mechanism wins on every dimension:**

- **Behavioral mirror is exact** — we don't approximate `.claude/rules/` behavior, we ARE rules in `.claude/rules/`. Frontmatter, glob targeting, post-compact survival, all of it: handled by Claude Code itself.
- **Boundary-clean** — the writes are claudechic-prefixed file creations into `~/.claude/rules/`, classified as non-destructive incidental under A7. Distinct prefix prevents any collision with user-authored or Claude-owned files.
- **No SDK uncertainty risk** — the earlier mechanism depended on three undocumented-or-buggy SDK features (`SessionStart` not in `HookEvent` literal; `PostCompact` not in literal; `PreToolUse additionalContext` field acceptance). The new mechanism uses only the SDK's well-attested rules-loading path that's been in production for everyone since Claude Code launched.
- **Cross-platform** — regular file writes; no symlinks (A4-clean for Group D).
- **Toggle-able** — settings-screen entry lets the user disable the install if they want to manage `~/.claude/rules/` manually.
- **Self-healing on drift** — when bundled-with-claudechic versions change between releases, the next startup's idempotent install detects the difference (UPDATE branch) and refreshes the installed copies silently. No user action required, no nudge needed. The previously-discussed "restore the ContextDocsDrift trigger and the context_docs_outdated hint" idea was rejected on the grounds that hints are user-facing nudges; the auto-install removes the user action that the hint would have prompted toward, leaving the hint with no purpose.
- **Scope reduction** — net new code: ~600 lines (custom mechanism) → ~50 lines (idempotent install routine + drift trigger restoration). Test invariants: ~13 → ~5.

**Why phase context stays separate:**

Claude rules are static — they load at session start and don't refresh. Phase context is dynamic — workflow phases advance mid-session and the agent must see the new phase's instructions. Cramming phase context into the rules-loading mechanism would either (a) miss mid-session phase advances, or (b) require re-loading the rule set, which the SDK doesn't support and shouldn't.

So phase context keeps the existing write-file-and-tell-agent-to-read pattern from the original codebase, just relocated out of `.claude/` to comply with the boundary rule. The `app.py:1822` write site moves to `<repo>/.claudechic/phase_context.md`. The `app.py:1648` instruction-to-the-agent is preserved verbatim except for the path change.

**The user-tier install choice (not project-tier):**

The researcher's original recommendation suggested `<repo>/.claude/rules/` (project-tier) install — matching the existing `/onboarding` flow's pattern. The user redirected to user-tier (`~/.claude/rules/`):

> "I want to copy as default and the settings have a way to desable that. there are no tiers here right? does claude reads from ~/.claude/rules?"

User-tier wins because:
- **One-time install per user**, applies across every project they ever open with claudechic. Project-tier would require re-install in every new project.
- **Claudechic's three-level tier system doesn't apply to the agent-awareness install** — there's only one install location. (The three-tier system continues to apply to workflows, the global rules-and-hints YAML, and MCP tools — those still layer.)
- **Per-project overrides** (if a user wants them) go into `<repo>/.claude/rules/` directly via Claude's own surface, not via claudechic. We don't add complexity for a use case the SDK already serves.

**Why the `claudechic_` filename prefix:**

`~/.claude/rules/` is a shared namespace — the user's own rule files live there, and so do any other tools' that play in the same surface. Prefixing every claudechic-installed file with `claudechic_` (e.g., `claudechic_workflows-system.md`, `claudechic_overview.md`) means:
- Zero collision risk with user-authored files
- The install routine can confidently apply NEW/UPDATE/SKIP semantics by inspecting only `claudechic_`-prefixed files
- A user who wants to inspect "what did claudechic install?" can `ls ~/.claude/rules/claudechic_*.md`
- Uninstall is trivial: delete files matching the prefix; nothing else touched

**Historical note for future maintainers asking "why did this change late?":**

The original Group D design was thorough and well-engineered — it just answered the wrong question. The team correctly identified the boundary constraints and the L15 two-piece semantics, but didn't verify the SDK's existing rules-loading capability before designing a parallel mechanism. The user's question at spec-exit ("read how .claude/rules works") triggered the verification step that should have happened earlier. The lesson is in §9 (reversal triggers) — when a spec describes "claudechic does X," ALWAYS first check whether Claude Code already does X.

**The starting point.** The user instruction was "for #4 it needs to mirror the .claude/rule behavior" (Q4 / A3) plus "behave the same; non-destructive touches OK; overwriting Claude settings out; symlinks out" (Q1' / A4). Three lenses interpreted "mirror" three different ways before reaching agreement:

- UserAlignment defined "mirror" operationally as three criteria: auto-load + treated-as-authoritative + file-based.
- Composability initially recommended SessionStart-hook unification (composability.md §8.1).
- Skeptic recommended SessionStart hook + UserPromptSubmit-hook fallback for the mid-session-stale-context case (MR6.1–MR6.8).

**The interim flip-flop (worth recording for transparency).** During axis-specialist work, the agent verified that `SessionStart` is not in the SDK's `HookEvent` literal type. An interim status report from Composability characterized this as "mechanism switched to `SystemPromptPreset.append`" because that field IS typed. On closer inspection — finding `SessionStartHookSpecificOutput` defined at `claude_agent_sdk/types.py:401` and the `PostCompact` precedent already in production at `claudechic/workflows/agent_folders.py:147` despite not being in the literal — the team confirmed the SDK literal type lags behind the runtime CLI's accepted events. The original SessionStart-hook recommendation is **adopted directly**; no fallback substitution required. Composability self-flagged this in its self-correction message; SPEC.md §16.1 #4 records it.

**Why this mechanism satisfies all four user constraints:**

- **"Behave the same":** the SessionStart hook makes the always-on awareness content auto-load at session start, exactly as Claude's `.claude/rules/` files auto-load. The PreToolUse hook fires the first-read fuller context the moment the agent reads inside `.claudechic/`. Both pieces enter the system prompt; from the agent's perspective, the content is rule-equivalent. UserAlignment's three-criteria check passes for all three.
- **"Non-destructive touches OK":** the mechanism uses zero `.claude/` writes. The boundary lint allowlist contains zero `.claude/` write patterns from this axis. A7's permission for incidental writes stays as a latent permission this run does not exercise.
- **"Overwrites out":** trivially satisfied — no writes at all.
- **"Symlinks out":** trivially satisfied — the mechanism is Python code in claudechic's process; no filesystem features beyond reading.

**The mid-session phase-advance failure mode.** The largest concrete failure mode (Skeptic F1, axis_awareness_delivery_appendix.md §2): SessionStart fires once at session init, but workflow phases can advance mid-session. The hook does not re-fire on phase advance, so the agent runs on stale phase context.

Two mitigation options:
- **(a) explicit re-read message at phase advance.** When `app.py` writes the new phase context to `<repo>/.claudechic/phase_context.md`, it sends the agent a turn saying "re-read your phase context." The agent's Read tool fires; the file's contents enter chat. Preserves today's `app.py:1648`–`app.py:1822` pattern. Familiar; well-tested in claudechic.
- **(b) per-turn rehydration via UserPromptSubmit hook.** Every user turn, a hook re-reads phase context and injects system-prompt-equivalent. Always fresh. Costs prompt budget every turn.

axis_awareness_delivery picked (a). Rationale (axis_awareness_delivery_appendix.md §2): preserves the existing pattern; cheaper in prompt budget; makes the agent's read explicit and auditable; handles the busy-agent edge case naturally. Trade-off accepted: the agent acknowledges the re-read message, which adds one-half-turn of overhead per phase advance.

**The three deletions.** The unified mechanism replaces three pieces of legacy code:
- `ContextDocsDrift` trigger class (in `claudechic/hints/triggers.py`) — was detecting drift between bundled context docs and what's installed in `.claude/rules/`. With no `.claude/rules/` install pattern, the drift detector has no purpose.
- `context_docs_outdated` hint (in `claudechic/global/hints.yaml`) — fired by the trigger above.
- `/onboarding context_docs` phase — was the mechanism by which claudechic context docs got installed into `<launched_repo>/.claude/rules/`. With agent awareness delivered via SDK hooks instead, the install phase is obsolete.

These are deletions, not refactors. axis_awareness_delivery_appendix.md §5 explains: keeping them as "deprecated" leaves dead code that the next contributor would have to delete anyway, and makes the unified-mechanism story incoherent (why is there both an SDK-hook delivery and a `.claude/rules/` install path?).

### 4.5 Group E — Workflow artifact directories

**Decision: per-chicsession dir at `<repo>/.claudechic/runs/<chicsession_name>/`; `CLAUDECHIC_ARTIFACT_DIR` env var + `${CLAUDECHIC_ARTIFACT_DIR}` markdown placeholder; never auto-cleaned.**

axis_artifact_dirs_appendix.md weighs the alternatives. The two non-trivial decisions:

- **Identity = chicsession.name, not a fresh run_id.** A fresh run_id per workflow activation would force the user to re-locate artifacts after every resume; chicsession.name preserves continuity across resume/re-activation of the same chicsession. The user's mental model treats the chicsession as the unit of work.
- **Both env var and placeholder substitution.** Either alone would work; both together reinforce. The env var lets spawned sub-agents inherit the path automatically through `_make_options`. The placeholder lets workflow markdown files reference the path explicitly. INV-12 enforces no hard-coded paths in workflow role markdown.

### 4.6 Group F — Cherry-picks

**Decision: pull `9fed0f3`, `8e46bca`, `f9c9418`, `5700ef5`, `7e30a53`; skip `d55d8c0`, `26ce198`, `0ad343b`, `fast_mode_settings.json`.**

The full table is in STATUS.md (the cherry-pick decision-of-record) and SPEC.md §6.1 (the operational form).

The interesting decisions:

- **`d55d8c0` dropped (A8).** Skeptic CW-1 surfaced the brittleness; the user assented; the loader rewrite re-implements the fallback-discovery logic from scratch as a "small generalization of `discover_manifests`." Rationale-anchor: user's "you can drop it."
- **`5700ef5` + `7e30a53` adopted as a unit.** They're behaviorally coupled (the auto-mode default + Shift+Tab cycle inclusion); pulling one without the other would leave the UX in an inconsistent state. UserAlignment's medium-drift flag about whether the user weighed the auto-mode UX shift was resolved by the user's "yes" to the explicit Q3' question.

### 4.7 Group G — UI surfaces

**Decision: settings screen + footer button + `/settings` command + welcome-screen access; workflow picker tier badges; auto-mode footer label; disabled-workflows + disabled-IDs subscreens; reuse existing widgets where they exist.**

ui_design_appendix.md weighs the alternatives. Two notable decisions:

- **One screen with both levels visible (not two separate screens).** Vision was ambiguous; UIDesigner picked one screen with level indicators per row. Rationale: matches the user's "workflow button can show all 3" mental model — they expect to see all levels at once, not navigate between screens.
- **Themes editor reuses `/theme` flow** (not a new picker). Issue #23 didn't specify; the existing `/theme` flow already covers theme selection adequately. Building a parallel picker would add complexity without functional gain.

UIDesigner placed all four A12-delegated smaller features in scope (zero postponed). Rationale (ui_design_appendix.md): each was small enough to include without bloating the spec, and postponement would create an unstable user-facing surface where some features work in scope and others are deferred.

### 4.8 Group H — Boundary CI test

**Decision: hybrid static AST + runtime monkey-patch detection; two YAML config files (`write_sites.yaml` + `claude_owned_files.yaml`); covers writes AND deletes.**

axis_boundary_test_appendix.md weighs detection mechanisms. Three were considered:

- **Pure static AST analysis** — fast, deterministic, but can't resolve dynamic paths (e.g., `Path(some_var) / "foo"` where `some_var` is computed at runtime).
- **Pure runtime instrumentation** — catches everything, but slow and requires the test suite to exercise every code path.
- **Hybrid** — static is the CI gate (fast, deterministic); runtime is a supplement that catches dynamic paths during the existing test suite's runs.

Choice: hybrid. Static covers ~90% of real cases (claudechic's path construction is mostly literal); runtime catches the remaining edge cases without slowing CI to a crawl.

The "covers deletes too" decision matters: claudechic's existing phase-context unlinks at `app.py:1867` and `app.py:1925` would otherwise pass a write-only boundary check while still mutating `.claude/` via deletion. The registry's `call` field includes `path_unlink` precisely to close this gap.

---

## §5 — Cross-lens disagreement history

One real disagreement surfaced during the run. Worth recording for future maintainers asking "why is this enforcement so heavy?"

### 5.1 Partial-override enforcement

**Composability's position (composability.md §R3 partial-override):** forbid partial workflow overrides; require the full file set; document loudly.

**UserAlignment's position (user_alignment.md §"Cross-lens: UX validation"):** doc-only is a foot-gun. Users will put one role file in `~/.claudechic/workflows/foo/role_x/` and silently get no effect, then debug for hours wondering why their override "isn't applying." UserAlignment required:

1. Loud loader error (not just doc text).
2. Surfaced in the TUI (not just logs).
3. Fall-through to next-lower tier on detection (so the broken partial doesn't blow up the whole workflow).
4. Documentation explains the rationale.
5. UI affordance: a "Override this workflow" command that copies the full file set as the happy path.

**Resolution:** in UserAlignment's favor. axis_loader_resolution.md §6.5 encodes the loud-loader-error + fall-through; SPEC.md §3.6 references §6.5 of the axis-spec; ui_design.md §1.7 covers the "Override this workflow" command.

**Why UserAlignment won:** UserAlignment's argument was about user UX safety; Composability's was about loader simplicity. The cost of loader-level enforcement is small (one set-difference operation per tier per workflow_id at load time) and the user-experience cost of the foot-gun is large (silent debugging hell). The five-cost-units-vs-fifty argument is asymmetric enough that the stricter enforcement wins on simple expected-cost weighing.

axis_loader_resolution_appendix.md §4.5.2 records the disagreement and rationale.

---

## §6 — Vision/STATUS errors flagged per A1

Seven errors were flagged across the lens reports. SPEC.md §16.1 has the operational dispositions; this section adds the rationale for each.

### 6.1 Worktree symlink — vision was correct; spec deviation reversed at user direction

**Source:** Composability self-flag during synthesis (initial deviation) + user reversal at spec-exit checkpoint.

**Initial conflict (resolved by reversal):** vision file-move inventory §"Worktree symlink (BF7)" prescribed adding a parallel `.claudechic` symlink at `claudechic/features/worktree/git.py:293–301`. A4 (from user's Q1' answer "adding a symlink is out as it is not supported on windows") was initially read as ruling that out.

**The first synthesis attempt** picked per-worktree fresh state (no symlink), reading A4 as a global no-symlinks rule. Documented as a vision-vs-A4 inconsistency.

**Reversal at spec-exit checkpoint:**

> User said: "add symlink to .claudechic and make an issue in the repo about worktrees and windows."

The user's reversal scopes A4 down: A4 still forbids symlinks for the **agent-awareness mechanism** (Group D), where cross-platform behavior is required. A4 does NOT forbid filesystem-state-propagation symlinks at the worktree code site, where the existing `.claude/` symlink already lacks Windows support and adding a parallel `.claudechic/` symlink does not introduce a regression.

**Resolution:** SPEC.md §10 reverted to add the parallel `.claudechic/` symlink. SPEC.md §11.4 scoped to forbid symlinks in the agent-awareness mechanism only. Windows portability tracked at [sprustonlab/claudechic#26](https://github.com/sprustonlab/claudechic/issues/26).

**What this means for new worktrees:** project-tier `.claudechic/` propagates from the main worktree to new worktrees via symlink, matching today's `.claude/` behavior. Windows users currently have no working cross-platform path for either symlink; resolved when issue #26 is addressed.

**Vision-flag classification updated:** this is no longer a vision/spec inconsistency. The vision's original prescription was correct; the synthesis pass's deviation has been reverted. Issue #26 captures the residual portability question.

### 6.2 Missing `.claude/hits.jsonl` from file-move inventory

**Source:** axis_boundary_test.md §10's write-site sweep.

**The conflict:** the vision's file-move inventory listed three primary-state write sites in `.claude/` (`.claudechic.yaml`, `hints_state.json`, `phase_context.md`). The boundary-test specialist's full-codebase sweep found a fourth: the guardrail audit log at `<repo>/.claude/hits.jsonl` (written by `app.py:1492` and `claudechic/guardrails/hits.py:52`).

**Why missed:** the prior team's inventory walk was probably done before the guardrail audit log was added, or the audit log's path wasn't considered claudechic-primary. Either way, the spec's boundary test would have caught it post-hoc; surfacing it now adds it to Group B's relocation task list explicitly.

**Resolution:** SPEC.md §2.5 adds `<repo>/.claude/hits.jsonl` → `<repo>/.claudechic/hits.jsonl` to Group B.

### 6.3 Vision §1 "mechanism choice" framing inconsistent with L7

**Source:** Composability synthesis review.

**The conflict:** vision §"What we want" §1 says "Whether [rules and hints] are a single directory or two siblings is a mechanism choice." But L7 already locks the layout to `global/{rules,hints}.yaml` (two siblings).

**Why both exist:** the vision drafted §1 as an open design question; L7 then locked the answer in the same vision document. The §1 framing wasn't scrubbed after the lock.

**Resolution:** SPEC follows L7 (locked); the §1 "mechanism choice" framing is treated as superseded. Future vision authors should remove the open-question phrasing once the answer is locked in the same document.

### 6.4 Composability §8.1 SessionStart recommendation status

**Source:** Composability self-flag + axis_awareness_delivery verification.

**The conflict:** Composability's lens-input §8.1 recommended SessionStart-hook unification before verifying SDK API surface. The agent verified during axis-spec work and initially reported the recommendation was "superseded" by SDK reality. On closer inspection (see §4.4 above), the recommendation is actually adopted directly — the SDK literal type just lags behind runtime CLI acceptance.

**Why it surfaced:** Composability hadn't run the SDK verification step before recommending. A1 asks agents to flag their own errors; Composability did.

**Resolution:** SPEC.md §16.1 #4 documents the adopt-directly framing; §12.1 surfaces the SDK lag as a known risk with documented degradation path.

### 6.5–6.7 Settings UI ambiguities resolved by UIDesigner

Three smaller items: single-vs-dual-screen settings (resolved: one screen), themes editor scope (resolved: reuse `/theme`), `disabled_ids` covers what (resolved: both hints and guardrail rules with category headers). UIDesigner's appendix has the rationale.

### 6.8 Operational disposition map (relocated from SPEC.md §16.1)

Each vision/STATUS error and how the operational spec resolved it:

> **Note on the worktree symlink (formerly listed as a vision flag):** the synthesis initially deviated from the vision File-move inventory's prescribed `.claudechic` symlink at `git.py:293-301`, citing A4 (no symlinks). User direction reverses this: the symlink approach is restored (SPEC.md §10); A4's no-symlinks rule is scoped to the agent-awareness mechanism (Group D / §11.4); Windows portability for both `.claude` and `.claudechic` symlinks is tracked at https://github.com/sprustonlab/claudechic/issues/26. The vision was correct; no flag entry is needed.

1. **Vision File-move inventory does NOT enumerate `<repo>/.claude/hits.jsonl` as a `.claude/`-write site.** `axis_boundary_test.md` §10 caught this. Resolved: SPEC.md §2.5 adds the relocation to Group B.

2. **Vision §"What we want" §1 says "Whether [rules and hints] are a single directory or two siblings is a mechanism choice"** but L7 already locks the layout to `global/{rules,hints}.yaml`. The §1 framing is inconsistent with L7. Resolved: SPEC follows L7 (locked); the §1 "mechanism choice" framing is treated as superseded.

3. **Group D agent-awareness mechanism — RESEARCH.md Option B adopted.** The earlier synthesis specified an SDK-hook-based mechanism (SessionStart + PreToolUse + PostCompact under `claudechic/context_delivery/`); RESEARCH.md surfaced that the Claude Agent SDK already loads `~/.claude/rules/*.md` natively per `setting_sources` (already configured at `app.py:969`). User approved Option B verbatim ("approve option B, fine with all answers. I want to copy as default and the settings have a way to desable that"). Resolved: SPEC.md §4 rewritten to install bundled context docs into `~/.claude/rules/claudechic_*.md` on every startup (gated by `awareness.install` user-tier config; default `True`). The `/onboarding context_docs` phase is RESTORED and adapted as a manual re-install trigger; the `ContextDocsDrift` trigger and `context_docs_outdated` hint stay DELETED — under the idempotent install routine there is no user action to nudge toward, so a hint would be noise (per user's correction: hints are a user-facing mechanism). Three SDK uncertainties (SessionStart in HookEvent literal, PostCompact in literal, PreToolUse `additionalContext`) eliminated. `axis_awareness_delivery.md` superseded with banner. STATUS.md A13 records the A7 reclassification of `~/.claude/rules/claudechic_*.md` writes as `non-destructive incidental`.

4. **Composability INV-9 reframed.** The previous "unified ContextDelivery" goal (one mechanism for both phase-context and awareness) is satisfied differently under Option B: phase-context retains its own delivery (engine writes to `<repo>/.claudechic/phase_context.md`; agent reads via Read tool when instructed; existing `PostCompact` hook re-injects on `/compact`); awareness uses the SDK's native rules-load. The "unification" goal aimed at avoiding two parallel claudechic-built injection systems; Option B avoids that more strongly by building zero injection systems for awareness (the SDK does it) and keeping the existing minimal phase-context pattern. Resolved: SPEC.md §13.4 INV-9 marked superseded with explanation.

5. **Vision §"Success looks like" — single-vs-dual config edit ambiguity.** The vision says `/settings` "applies to every project" but doesn't say whether one screen or two. `ui_design.md` §11.1 picks "one screen with both tiers visible" (per §1.4 mock). Resolved: SPEC.md §7 / Group G inherits this; rationale in §3.

6. **Issue #23 — `themes` editor under-specified.** `ui_design.md` §11.2 routes to existing `/theme` flow. Resolved: SPEC.md §7.3 references `/theme`.

7. **Issue #23 — `disabled_ids` ambiguity (hints? rules? both?).** `ui_design.md` §11.3 covers both with category headers. Resolved: SPEC.md §7.1 #6 (`DisabledIdsScreen`).

---

## §7 — Rejected alternatives ("what NOT to do")

This is the section the Implementer might be tempted to read but should not — these are anti-patterns the team explicitly considered and rejected. Recorded here so a future maintainer reading the spec doesn't propose them as "improvements."

1. **DO NOT transcribe `d55d8c0`'s loader logic line-by-line.** The cherry-pick was dropped (A8) precisely because hand-extracting "loader code without YAML" is brittle. The new loader is a small generalization of the existing `discover_manifests`, not a port of the dropped commit. axis_loader_resolution.md §10 forbids consulting the dropped commit during implementation.
2. **DO NOT add symlinks in the agent-awareness mechanism (Group D).** A4 is binding for the agent-awareness mechanism: cross-platform support is required, and symlinks fail on Windows. Use SDK hooks (which is what Group D does). Worktree filesystem-state-propagation symlinks at `git.py:293-301` are a separate case explicitly permitted; see SPEC.md §10 + §11.4 + sprustonlab/claudechic#26 for the Windows-portability tracking.
3. **DO NOT overwrite Claude-owned settings or config files inside `.claude/`.** Listed in `tests/boundary/claude_owned_files.yaml`. The boundary lint catches violations.
4. **DO NOT add automatic migration logic.** L17 binds. The existing user count is two (issue-author and Arco); both can move their own files manually. A9 extends this to forbid even one-line startup warnings.
5. **DO NOT mix rationale into the operational spec.** L14 binds. Rationale lives in this appendix and the team's `*_appendix.md` files. The Implementer's spec must read cleanly without rationale paragraphs.
6. **DO NOT use "convergence" or "merge program" in any user-facing prose.** A10 retired both terms. Canonical replacements: "cross-pollination" (the bidirectional flow), "selective integration" (the act of cherry-picking), "coordination" (the ongoing dialogue). The terminology checklist (SPEC.md §14.3) enforces zero occurrences.
7. **DO NOT introduce a `claudechic/defaults/config.yaml` package-tier config file.** Config is 2-tier (A5 + L8). Defaults live in code (Python dataclass field defaults). A package-tier YAML would express the same intent twice in different syntaxes.
8. **DO NOT design custom claudechic-internal mechanisms when the Claude Agent SDK already provides the capability.** A13's lesson: the original Group D design built session-start + pre-tool-use + post-compact hooks before verifying the SDK's existing `.claude/rules/` loader could serve the same purpose. ALWAYS run an SDK-capability check before designing an injection / hook / extension mechanism. The SDK's capabilities are listed in `claude_agent_sdk.types`; the runtime CLI's capabilities are inspectable via the existing claudechic precedents in `app.py`.

9. **DO NOT split phase-context delivery and agent-awareness install into the same mechanism.** They have fundamentally different lifecycles (static-load-once vs dynamic-mid-session-update). The earlier "INV-9 unification" temptation was based on the assumption that both pieces are static; once you accept that phase-context advances during a session and rules don't refresh, the unification falls apart. Keep them separate. (Note: this reverses guidance the original synthesis spec emitted under INV-9; A13's redesign supersedes.)
9. **DO NOT extend the boundary allowlist for `.claude/` writes from this run.** The boundary lint allowlist starts with zero `.claude/` write patterns (from any axis). A7's permission for incidental writes is latent — adding the first allowlist entry should be a deliberate, reviewable act in a future change, not a default-on growth path.

---

## §8 — Risk register (severity-rated; full text in `risk_evaluation.md`)

Skeptic enumerated twenty-three numbered risks plus three vision/STATUS errors. The top items by severity:

**Critical (6 total in the risk register):**
- R1 — phase_context.md write site re-introduced after relocation (boundary lint catches; CI gate enforces)
- R2 — A3-driven mechanism quietly writes back into `.claude/` (boundary lint catches; mitigated to "no .claude/ writes from awareness axis" in SPEC.md §11.5)
- R5 — future contributor adds a write-site under `.claude/` because the existing pattern is still in `git log` (boundary lint catches; documentation in SPEC.md §11 explains the rule)
- R12 — `d55d8c0` selective cherry-pick brittleness (resolved by A8 dropping the cherry-pick)
- R20 — silent regression: `.claudechic/` state stops following worktrees (resolved by SPEC.md §10 picking per-worktree fresh state and documenting the behavioral change as accepted tradeoff)
- R22 — spec phase mixes rationale into operational instructions (resolved by L14's two-file split + the three exit checklists)

**High (10 total) and Medium (6 total):** in `risk_evaluation.md` §1–9 and the spec-phase Skeptic review. The boundary CI test (Group H) addresses many; the cross-lens disagreement resolution (§5 above) addresses partial-override; the SDK uncertainty fallbacks address SessionStart/PreToolUse/PostCompact runtime acceptance.

**Low (1 total):** the residual long-tail item; not on the spec-exit critical path.

The "lost work" four-sense sweep on the cherry-pick set (Skeptic §4) found no commits dropping into category 1 (commits never on main) or category 4 (intent lost even if code survives). Categories 2 and 3 are addressed by the cherry-pick ordering in SPEC.md §0.4 and the per-commit acceptance criteria in §6.

---

## §9 — Reversal triggers

Conditions under which a locked decision should be reconsidered. These are not invitations to re-litigate now; they're future-maintainer guidance.

**Reconsider A7 (boundary primary-state-only) → tighten back to absolute** if:
- The boundary lint never adds a `.claude/` write allowlist entry across multiple subsequent changes (suggesting A7's permission was unneeded)
- A future feature requires a `.claude/` write that turns out to be impossible to do non-destructively (suggesting the soft-form was over-permissive)

**Reconsider A9 (no startup warning for existing users) → add a one-line warning** if:
- The user base grows beyond developers who know what they're doing
- A non-developer user joins claudechic's installs and hits silent state loss

**Reconsider A4's symlink prohibition (currently scoped to the agent-awareness mechanism only)** if:
- A future agent-awareness delivery mechanism becomes possible only with symlinks (low likelihood; SDK hooks cover the current mechanism cleanly)
- Windows symlink support stabilizes; track at sprustonlab/claudechic#26

**Reconsider the worktree symlink approach (now restored per user direction at spec-exit)** if:
- A Windows user joins the install base and hits the symlink limitation (issue #26 covers this contingency)
- The cost of maintaining symlink-based worktree propagation proves higher than copy or per-worktree fresh state for any platform

**Reconsider the SessionStart-hook mechanism (Group D) → switch to one-shot UserPromptSubmit** if:
- A future Claude Code release explicitly rejects events not in the typed `HookEvent` literal
- The PostCompact precedent stops working in production
- SDK verification step during implementation finds SessionStart no longer fires

**Reconsider the "cross-pollination not convergence" terminology (A10) → relax** if:
- The cross-fork relationship transitions from coordination to actual unification (e.g., one fork absorbs the other)
- "Cross-pollination" becomes culturally awkward as a term in the broader claudechic ecosystem

**Reconsider the "config 2-tier" decision (A5 + L8) → expand to 3-tier** if:
- A real use case emerges for shipping config defaults in YAML rather than code (e.g., user-tunable defaults that need to ship pre-customized to specific lab environments)

**Reconsider the "drop `d55d8c0`" decision (A8) → reinstate as a port** if:
- The structural rewrite turns out to drop behavior that `d55d8c0` had captured
- A future maintainer wants attribution preserved for the abast contribution

---

## §10 — Reference materials

### 10.1 This run's deliverables (authoritative)

- `SPEC.md` — operational specification (Implementer + Tester read this)
- `SPEC_APPENDIX.md` — this file
- `STATUS.md` — workflow state of record (locks, amendments A1–A13, phase log)
- `userprompt.md` — user's verbatim words (kickoff + Q1–Q9 + spec-exit redirections)
- `vision.md` — prior team's hand-off; authoritative input
- `RESEARCH.md` — researcher's spec-exit investigation that drove the A13 redesign

### 10.2 Spec-phase contributions (cross-referenced from SPEC.md)

In `specification/`:
- `composability.md` — normative axes, seam protocols, invariants
- `terminology.md` — terminology contract for spec phase
- `skeptic_review.md` + `skeptic_review_appendix.md` — risk and simplification analysis
- `user_alignment.md` — alignment audit + cross-lens UX validation

In the run dir:
- `axis_loader_resolution.md` + `_appendix.md` — 3-tier loader axis
- `axis_awareness_delivery.md` + `_appendix.md` — agent awareness axis
- `axis_artifact_dirs.md` + `_appendix.md` — artifact dirs axis
- `axis_boundary_test.md` + `_appendix.md` — boundary CI test axis
- `ui_design.md` + `ui_design_appendix.md` — UI surfaces
- `terminology_glossary.md` — canonical glossary (revised; "cross-pollination" is canonical)

### 10.3 Leadership-phase contributions

- `composability_eval.md` — Composability lens evaluation (10 axes, 7-group decomposition)
- `terminology_glossary.md` (also a spec-phase artifact)
- `risk_evaluation.md` — Skeptic risk evaluation (23 risks + 3 vision flags)
- `alignment_audit.md` — UserAlignment audit (drift items by severity)

### 10.4 Prior run (reference; not required reading)

`.project_team/issue_23_path_eval/`:
- `RECOMMENDATION.md` — prior cross-lens recommendation
- `fork_diff_report.md` + `fork_file_map.csv` — fork delta data
- `composability_eval.md`, `terminology_glossary.md`, `risk_evaluation.md`, `alignment_audit.md` — prior run's lens reports
- `STATUS.md` — prior decisions (D1–D22)
- `Appendix.md` — prior run's rationale + rejected paths
- `abast_executive_summary.md` — coordination artifact (superseded)

### 10.5 GitHub issues

- sprustonlab/claudechic#23 — settings UI deliverables
- sprustonlab/claudechic#24 — 3-tier architecture, boundary, workflow button, agent awareness
- sprustonlab/claudechic#25 — `/fast` mode (deferred from this run)

---

*End of SPEC_APPENDIX.md.*
