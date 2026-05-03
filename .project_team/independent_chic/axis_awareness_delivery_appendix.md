# Appendix — Agent-Awareness / Context-Delivery Mechanism

**Axis:** R6 + phase_context unification.
**Companion:** `axis_awareness_delivery.md` (the operational spec).
**Audience:** Coordinator, Skeptic, UserAlignment, anyone reviewing why-this-design.
**Mode:** rationale, alternatives, trade-offs, A1-flagged inconsistencies. No operational instructions; the spec owns those.

---

## 1. Mechanism evolution: revision history

This appendix documents two mechanism choices made in sequence.

### 1.1 First-pass choice (rejected)

The first draft of this axis spec (now superseded) chose **R6.6 option A** — `SystemPromptPreset.append` for always-on + PreToolUse for first-read. The rationale was that `system_prompt.append` is in the SDK's typed-and-documented API while `SessionStart` is not in the SDK's `HookEvent` literal.

### 1.2 Cross-lens consensus (adopted)

After the first draft, the Composability lens flagged R6 mechanism choice as deferring to Skeptic + UserAlignment per §8.1. Both lenses concurred on **R6.6 option B — SessionStart-hook unification**:

- Skeptic (`specification/skeptic_review.md` §"Cross-lens: R6 risk weighting"): "CONCUR with Composability's recommendation." Skeptic's MR6.1 mandates SessionStart for both always-on and phase-context.
- UserAlignment (`specification/user_alignment.md` §"Cross-lens: UX validation" Item 1): "AGREE." UserAlignment's three-criterion check (auto-load, treated-as-authoritative, file-based) verifies the SessionStart hook satisfies each criterion.

The current spec adopts SessionStart-hook unification. The reasons documented below replace the prior draft's Option A rationale.

### 1.3 Why SessionStart-hook unification (the cross-lens consensus)

**Composability win.** The phase-context delivery and the always-on awareness delivery now share both an implementation (the `ContextDelivery` module) AND a triggering surface (the SessionStart hook). The Composability spec's INV-9 / R6.5 ("phase-context and agent-awareness deliveries share an implementation") becomes structurally enforced — adding a fourth delivery moment in the future means adding a new hook callback in the same module, not a new parallel system.

**Risk profile (per Skeptic).** SessionStart and PreToolUse are both hook surfaces; they share failure-mode patterns (timeout handling, exception isolation, payload-size budgeting). The shared shape means the failure-handling code (MR6.3, MR6.4 in the spec) covers both with one implementation.

**UX faithfulness (per UserAlignment).** The user's frame in #24 was "We want a prompt injection telling agents about claudechic." The SessionStart hook is the most direct mechanical analogue: at session start, claudechic injects content into the agent's prompt. The agent treats SessionStart-delivered content as authoritative system context (`system-reminder` envelope), satisfying the "rule-equivalent" criterion of A4's behavioral mirror.

### 1.4 Why not Option A (rejected)

`SystemPromptPreset.append` would deliver always-on text but does NOT unify with phase-context. Phase-context still needs a separate delivery channel (file + Read tool, or another hook). Two parallel mechanisms violate Composability's INV-9 / R6.5. Skeptic's §10.5 notes this exact reason: "viable, marginally simpler for the always-on piece, but does NOT unify with phase-context — leaves phase-context as a separate mechanism, violating Composability's INV-9. Reject for that reason alone."

### 1.5 Why not Option C (rejected)

A non-destructive write inside `.claude/` that Claude Code auto-loads natively is permitted by A7 but rejected by Skeptic MR6.6 because the awareness/phase-context content is **primary state** per R5.1. Even setting that aside, this option couples claudechic's behavior to Claude Code's `.claude/`-auto-load semantics, which can change between Claude versions. Highest-risk path for L10.d (intent loss) on a future Claude upgrade. The Skeptic lens rates it as "highest-risk path."

---

## 2. Why MR6.2 option (a) — explicit re-read message — over option (b) — UserPromptSubmit re-injection

Skeptic's MR6.2 names two acceptable shapes for handling phase-advance mid-session refresh:

- **(a) Explicit re-read message** at phase-advance time. Engine writes the new file AND sends a chat message to the active agent prompting a re-read.
- **(b) Per-turn UserPromptSubmit hook** that re-evaluates the file each turn and injects fresh content.

The spec adopts (a). Reasons:

### 2.1 (a) preserves today's `app.py:1822` pattern

Today's code already does this: `_inject_phase_prompt_to_main_agent` rewrites the file, then the user (or workflow) sends a message. The agent reads the file via its own Read tool. The pattern works; the only change in this spec is the file path. Choosing (a) is a localized edit; choosing (b) is a new mechanism.

### 2.2 (b) costs prompt budget every turn

UserPromptSubmit fires on every user turn. If the hook injects phase-context content per turn, every turn pays the prompt-tax for content the agent already has in its conversation history (from the prior re-read). The prompt cache may absorb most of the cost on warm runs, but cold cache turns and post-compact turns pay full cost.

### 2.3 (b) requires "did the agent already see this version?" state

To avoid duplicate injection, (b) needs per-turn state ("has this version been delivered?"), keyed by phase id or content hash. That state is similar shape to the first-read tracker but with different invalidation semantics (phase advance invalidates; first-read tracker doesn't). Adding a second tracker with overlapping responsibility is exactly the smell §1.3 of the spec is trying to avoid.

### 2.4 (a) makes the agent's read explicit and auditable

When the engine sends the re-read message, the user sees the message in the chat history. The agent's Read of `.claudechic/phase_context.md` shows up as a tool use. The flow is auditable. (b) is invisible — content is injected by the SDK without a chat-history footprint.

### 2.5 (a) handles the edge case where the agent is busy

If the engine sends the message while the agent is mid-tool-use, the message queues until the agent's next turn (per the existing `_send_to_active_agent` semantics). The agent picks up the new phase context as soon as it's free. (b) would inject on the next user turn, which may be later still. (a) is at least as responsive.

### 2.6 Trade-off accepted

Choosing (a) means: if the engine crashes between the file write and the message dispatch, the agent stays on stale phase-context until the next user turn happens to mention the phase. This is a real failure mode but a small one — the file itself is up to date, so the agent just hasn't been told to re-read. The user can mention "we advanced phases — re-read .claudechic/phase_context.md" and recover. (b) would be more robust against this specific failure but at a permanent prompt-budget cost. Skeptic explicitly leaves the choice to the spec author; the spec author picks (a) because the recovery mode is cheap and the budget cost of (b) is permanent.

---

## 3. Why phase context is also delivered via SessionStart (in addition to the file)

A user might ask: "if `<repo>/.claudechic/phase_context.md` is the source of truth and the agent reads it via Read, why also deliver it via SessionStart?"

Two reasons:

### 3.1 First-turn responsiveness

Without SessionStart delivery, a fresh agent in an active workflow does not know what phase it's in until the kick-off message tells it to read the file. This is fine for the main agent (the kick-off message exists) but fragile for chic-MCP-spawned sub-agents that may not receive a kick-off message. SessionStart delivery makes the phase-context available the moment the agent is alive, with no message dependency.

### 3.2 The behavioral-mirror argument

A4 + L15 say "agents experience `.claudechic/` content the same way they experience `.claude/rules/` content." `.claude/rules/` content is loaded at session start. Phase-context is `.claudechic/`-located content. Therefore phase-context should also be loaded at session start, not just on demand. The SessionStart payload contains both pieces — always-on + phase-context — to honor this mirror.

The mid-session phase-advance mechanism (§5.3 of the spec) is the necessary additional path because SessionStart fires once. It is not a redundant duplicate; it complements SessionStart (which handles first delivery) with a second delivery path (explicit re-read on phase change).

---

## 4. Project-tier override for context content (reversed from first draft)

The first draft disallowed project-tier overrides of context content; the current spec permits them. The change was driven by UserAlignment R6-UX.2: "the recognized source root for content files MUST be documented in `docs/configuration.md` (the canonical location: `claudechic/defaults/context/`, with optional `<repo>/.claudechic/context/` override)."

UserAlignment's reasoning: a user's natural mental model under "everything in 3 levels" (#24) is that EVERY content category supports tier override, including context content. Carving out context content as package-tier-only would surprise the user. The marginal complexity to support tier override for context content is small (the same per-filename override semantics apply) and the carve-out's only justification was scope-control, which is overruled by the cross-lens UX rule.

User-tier (`~/.claudechic/context/`) is also permitted for symmetry with the rest of the 3-tier model. R3.4 (non-conflicting items accumulate) and R3.2 (override-by-id replaces) apply.

---

## 5. Why retire `ContextDocsDrift` and the `context_docs` phase

The mechanism here is hook-mediated injection from package-tier files (with optional user/project overrides). There is no installed copy on the user's disk. There is nothing to drift away from.

The current design's logic:
- Package ships `claudechic/context/*.md`.
- `/onboarding context_docs` phase copies them to `<repo>/.claude/rules/`.
- Claude Code auto-loads `.claude/rules/`, so the agent sees them.
- Over time, the package's docs update; the installed copies don't. `ContextDocsDrift` detects the mismatch by hash. The `context_docs_outdated` hint nudges the user to re-run `/onboarding`.

Under the new mechanism:
- Package ships `claudechic/defaults/context/*.md`.
- The SessionStart and first-read hooks read them at hook-fire time and inject them.
- The user has no installed copy on disk. There is no copy to drift.
- Re-running `/onboarding` is a no-op (the phase is gone).

`ContextDocsDrift` would, post-restructure, return False unconditionally for every project (the trigger reads `<repo>/.claude/rules/`, finds no claudechic docs there, returns False per its existing line 48 logic). The hint never fires. Keeping the dead code is worse than removing it.

Removal also removes a coupling from the new design to the old `.claude/rules/` install path. Per Composability lens Hole 6 (composability_eval.md §5): "ContextDocsDrift trigger no longer makes sense under A3 hook-mediated awareness." The recommendation there is "retire the trigger." This spec takes that recommendation.

---

## 6. Trade-offs

### 6.1 What is sacrificed for compositional cleanliness

- **No literal `.claude/rules/` mirror.** A user who already understands `.claude/rules/` and expects to `cat <repo>/.claude/rules/claudechic-overview.md` will find no such file. They have to learn that claudechic's documentation reaches the agent through SDK-level hook injection, not through a directory of installed files. UserAlignment (`alignment_audit.md` §3) flagged this reading divergence; the spec accepts the "behavioral mirror" reading.
- **No upgrade-drift detection.** Today's `ContextDocsDrift` told users when their installed docs were stale. Under the new design there is no on-disk install, so there is no detection. Users see whatever the package ships with. This is acceptable because (a) the package is the source of truth, (b) upgrade is `pip install -U claudechic` (then everything is fresh), and (c) the prior detection only fired for users who had already run `/onboarding`, which is itself going away.
- **Coupling to two SDK type fields not in the literal.** The mechanism relies on `SessionStart` hook event acceptance and `PreToolUseHookSpecificOutput.additionalContext`. The `SessionStart` event is not in the SDK's `HookEvent` literal but is documented via `SessionStartHookSpecificOutput`. The existing `PostCompact` precedent shows the CLI accepts these. Risk of CLI version drift exists; the spec §17 records the fallback (UserPromptSubmit one-shot at first turn).
- **Mid-session phase advances depend on the chat-message dispatch path.** If `_send_to_active_agent` fails (engine bug), the agent stays on stale phase-context until the next user turn. The `<repo>/.claudechic/phase_context.md` file is still up to date, so recovery is "user reminds the agent to re-read." Documented as a small, recoverable failure mode in §2.6.

### 6.2 What is gained

- **One module owns context delivery.** `claudechic/context_delivery/` is the single answer to "where does this content come from and how does it reach Claude?" Future extensions land in one place.
- **One mechanism, two registrations + an existing post-compact registration** unifies R6 + phase-context delivery (INV-9 satisfied by structural construction, not by convention).
- **No `.claude/` writes anywhere.** The boundary test becomes simpler — the only primary-state writes from this axis are unambiguously under `.claudechic/`. No A7 "non-destructive incidental" judgement calls required. Boundary lint allowlist is empty for this axis (spec §11.2).
- **No symlinks.** Cross-platform clean. Windows works.
- **No collision risk with Claude-owned settings.** `~/.claude/settings.json`, `<repo>/.claude/settings.json`, and `<repo>/.claude/settings.local.json` are read-only from claudechic's perspective.
- **Project-tier and user-tier override of awareness content** matches the user's "everything in 3 levels" mental model.

---

## 7. Why the boundary test will pass

Every primary-state write in this axis (§11 of the spec) resolves to a path under `.claudechic/`. The boundary CI test (encoded by the boundary-test axis-agent per Seam-E / R5.4) consumes the table at §11 and asserts:

1. Every entry classified `primary-state` produces a path with `".claudechic"` as a path segment AND no `".claude"` path segment outside the `".claudechic"` segment.
2. No write site introduced or modified by this axis appears in the test's "found writing inside `.claude/`" output.

The legacy unlinks at `app.py:1925` (the `<repo>/.claude/phase_context.md` cleanup) is repathed, not retained. There is no fallback "cleanup the old path too" branch. This is intentional per L17 + A9. The boundary test does not see a `.claude/` path.

The SessionStart, PreToolUse, and PostCompact hooks all communicate with Claude through SDK return values, not filesystem writes. None of them creates a path-classified write site.

The first-read tracker dict is in-memory only.

The boundary-lint allowlist requires zero `.claude/` patterns from this axis (§11.2 of the spec). `axis_boundary_test` adds nothing on R6's behalf.

---

## 8. A1 inconsistencies surfaced

Per the run's A1 amendment ("agents discovering errors or inconsistencies in `vision.md` must surface them"). Three items found in the course of writing this spec:

### 8.1 Vision §"What we want" §4 says "fuller context — the package's own documentation about workflows, hints, guardrails — injected the first time"

This list ("workflows, hints, guardrails") matches three of the existing `claudechic/context/*.md` files. The package actually ships nine recognized files (per spec §3.4): `awareness_brief.md`, `awareness_full.md`, `claudechic-overview.md`, `multi-agent-architecture.md`, `workflows-system.md`, `hints-system.md`, `guardrails-system.md`, `checks-system.md`, `manifest-yaml.md`, `CLAUDE.md`. The spec adopts the broader set; if the user wants a narrower set, TerminologyGuardian (who owns the prose) can curate by adjusting which files exist.

### 8.2 STATUS A4 prohibits overwriting "Claude-owned settings/config file inside `.claude/`" but does not name "rules files" specifically

`.claude/rules/*.md` files are user-authored content, not Claude Code-installed settings — yet R6.7 tightens the rule to forbid writes to `.claude/rules/` specifically. The R6.7 reasoning is collision-risk, not Claude-owned-settings. STATUS A4 covers settings/config; R6.7 extends to rule content; both are honored by this axis (no writes anywhere in `.claude/`).

### 8.3 Vision §"Failure looks like" lists "the prompt injection either doesn't fire or contains too much / too little"

"Too much / too little" is a quality bar. The Implementer can verify the mechanism fires (INV-AW-1 through INV-AW-4) but cannot test "the content is the right amount." That judgement belongs to TerminologyGuardian (who owns prose) and to live testing.

The size-budget MUSTs (§3.5, §4.6) operationalize "not too much" as a hard cap. "Not too little" is by-construction (the always-on file is required to exist; INV-AW-1 verifies it reaches the agent). The sentinel-directive integration test (INV-AW-12) verifies "the agent treats it as authoritative."

---

## 9. Reversal triggers

Conditions under which the spec's choices SHOULD be revisited:

- **CLI rejects `SessionStart` hook registration.** Trigger: agent spawns produce CLI errors mentioning hook event. Action: switch to the documented fallback in spec §17(1) — emit a one-shot UserPromptSubmit hook on the agent's first turn, self-deregistering after first fire. The first-read and post-compact registrations are unaffected.
- **CLI ignores `PreToolUseHookSpecificOutput.additionalContext`.** Trigger: first-read sentinel test (INV-AW-12 second sentinel) fails repeatedly. Action: switch first-read injection to a UserPromptSubmit hook that fires once per session conditional on a `did-read-claudechic` marker the PreToolUse hook sets in a side dict.
- **A user need surfaces for non-overriding content layering.** Trigger: a user wants to ADD context content at user/project tier without replacing package content. Action: extend `sources.read_awareness_full` to support an `additional/` subdirectory at user/project tiers whose contents accumulate (R3.4 semantics) rather than override (R3.2). Localized change to `sources.py`.
- **`.claude/` becomes user-owned in some future Claude Code release.** Trigger: explicit Claude Code documentation change. Action: A7 softens further; the spec MAY revisit Option C (non-destructive `.claude/` write) if it offers materially better UX. Likely no.
- **Per-turn rehydration becomes necessary** (e.g., phase-context drift between file and agent memory becomes a recurring user complaint). Trigger: bug reports about agents acting on stale phase-context after a phase advance. Action: switch from MR6.2(a) to MR6.2(b) — a UserPromptSubmit hook that injects fresh phase-context per turn. The decision was made for (a); switching to (b) is a follow-up if the (a) failure mode bites.

None of these reversals require redesigning the mechanism — they extend or swap one registration of the existing module. That is the algebraic property §3 of the composability spec asked for.

---

## 10. Coordinator-facing summary

**One mechanism, three SDK registrations + one app-side trigger.** `claudechic/context_delivery/` ships:

- **SessionStart hook** delivering the always-on awareness statement AND current phase-context at session start.
- **PreToolUse hook** delivering fuller context on first read inside any `.claudechic/`.
- **PostCompact hook** re-injecting phase context after `/compact`.
- **Phase-advance re-read message** (in `app.py._inject_phase_prompt_to_main_agent`) handling mid-session phase changes.

All four read from package-tier (and, for awareness content, project-tier `<repo>/.claudechic/context/` and user-tier `~/.claudechic/context/`) files. None writes inside `.claude/`. No symlinks. No Claude-owned settings overwrites. A4 and A7 both clean. Skeptic MR6.6 honored.

**`ContextDocsDrift` and `/onboarding context_docs` retire.** No installed copy means no drift; the trigger and the install phase are removed in the same change set.

**The boundary test inputs are clean.** Four primary-state write sites, all under `<repo>/.claudechic/phase_context.md`. The boundary axis-agent encodes; this axis enumerates. The allowlist for `.claude/` write patterns required by this axis is **empty** — `axis_boundary_test` adds nothing on R6's behalf.

**MR6.2 mitigation chosen: option (a) — explicit re-read message.** Preserves today's pattern; lower long-term cost than per-turn rehydration.

**Three SDK API uncertainties** (`SessionStart` event registration, `PostCompact` event registration both not in `HookEvent` literal but supported in production; `PreToolUseHookSpecificOutput.additionalContext` honoring across CLI versions) are recorded in spec §17 with documented fallbacks.

**Wording.** The mechanism is "claudechic-awareness injection." The word "rules" is reserved for the rules content category.

---

*End of appendix.*
