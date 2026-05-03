# Skeptic Review — Appendix

**Companion to:** `specification/skeptic_review.md` (operational MUSTs/SHOULDs only, per L14)
**Audience:** Coordinator, Composability+UserAlignment lens authors, anyone re-litigating decisions

This file holds rationale, alternatives weighed, and "why not." It is NOT operational. The Implementer + Tester do not need to read it; the spec stands alone.

---

## A1 — R6 mechanism choice: full alternatives weighed

### A1.1 Frame

`composability.md` §8.1 lists three permitted mechanisms for R6 (agent-awareness delivery, two-piece per L15 + A11) under R6.6 + A4 + A7:

| Option | Always-on (L15 piece 1) | First-read (L15 piece 2) | Phase context |
|---|---|---|---|
| **1** | `append_system_prompt` (SDK init) | PreToolUse hook on Read | separate (legacy app.py:1822 site, redirected to `.claudechic/`) |
| **2** ✓ Composability rec | SessionStart hook reading `.claudechic/rules/*` | PreToolUse hook on Read | SessionStart hook reading `<repo>/.claudechic/phase_context.md` (unified with always-on) |
| **3** | Non-destructive write inside `.claude/` claudechic-namespaced; Claude auto-loads | PreToolUse hook on Read | Same write site |

UserAlignment's three-criteria check for "behave the same as `.claude/rules/`":
- (a) **auto-load** (no agent action required): all 3 options satisfy.
- (b) **treated-as-authoritative** (system-prompt-tier, not chat content): all 3 options satisfy if they inject into the system prompt; option 1's `append_system_prompt` does this directly; options 2 and 3 do this by virtue of the hook/auto-load placing content there.
- (c) **file-based** (the source of truth lives in `.md` files, not in code): all 3 options satisfy.

So all three options pass UserAlignment's behavioral mirror test in principle. The differentiator is failure-mode and complexity, which is Skeptic's lane.

### A1.2 Why option 2 (SessionStart-hook unification) wins

**Composability concordance.** Option 2 is the only option that satisfies INV-9 (phase-context delivery and agent-awareness delivery share an implementation). Option 1 leaves phase-context as a separate path; option 3 unifies them but at the cost of `.claude/` coupling. The unification matters operationally: future contributors maintaining one delivery path will diverge two delivery paths over time (cf. R-S2 in skeptic_review.md, the "two parallel injection systems" carryover risk).

**Boundary cleanliness.** Option 2 produces a boundary lint with **zero `.claude/` write allowlist entries**. The lint enforces strict L3-equivalent ("no claudechic writes inside `.claude/`"); A7's "non-destructive incidental writes are permitted" stays as a latent permission. This is the cleanest signal to future contributors: don't write inside `.claude/` *at all*. Adding the first allowlist entry later is a deliberate, reviewable act.

**Cross-platform.** SessionStart hook is Python code running in claudechic's process; no symlinks, no platform-specific filesystem features. A4 satisfied trivially.

**Decoupled from Claude Code internals.** SessionStart hooks are a documented SDK extension surface. `.claude/`-auto-load (option 3) is internal to Claude Code; its semantics can change between Claude versions without notice. Skeptic L10.d concern: if Claude Code 4.7.x changes how `.claude/` files are scoped, claudechic option 3 silently breaks; option 2 is unaffected.

### A1.3 Why option 1 (append_system_prompt + PreToolUse) is the next-best

**Where it wins:** marginally simpler for the always-on piece. `append_system_prompt` is a one-line SDK init kwarg; no hook implementation needed. Reduces the "moving parts" count by one (one hook + one append vs two hooks).

**Where it loses:** does not unify with phase-context. Phase-context still requires *some* mechanism — either a separate hook, or the legacy `app.py:1822`-style write (redirected to `.claudechic/phase_context.md`) plus a separate "tell the agent to re-read" message. Either way, claudechic now has two awareness-delivery code paths instead of one.

**Verdict:** option 1's simplicity is real but is consumed by the duplication it forces in phase-context. Option 2 amortizes one hook implementation across both concerns. Net: option 2 has *fewer* moving parts in steady state, even though the hook itself is a touch more complex than `append_system_prompt`.

### A1.4 Why option 3 (non-destructive write inside `.claude/`) is rejected

**The R5.1 trap.** Phase context is primary state per R5.1: claudechic generates it on workflow activation, updates it on phase advance, deletes it on workflow stop. R5.1 forbids primary-state writes inside `.claude/`. Even if always-on awareness content (which is more static — it's bundled with the package) could be classified as "non-destructive incidental," phase context cannot. Mixing these into one mechanism (which the unification goal requires) means the *whole mechanism* is doing primary-state writes, which option 3 cannot legally do.

**Even if R5.1 were relaxed:** option 3 makes claudechic depend on Claude Code's `.claude/`-auto-load behavior. Two known coupling risks:

1. **Naming collision.** Claudechic writes `.claude/claudechic_rules.md`. Future Claude Code release adds support for `.claude/<vendor>_rules.md` namespacing with conflicting semantics. Silent behavior change for users.
2. **Visibility to the user.** A user opening `.claude/` sees claudechic-owned files mixed with their own. They may delete them ("what's this `claudechic_phase_context.md`?"), getting silent-loss-on-next-session.

These are L10.d (intent loss) failure modes that option 2 doesn't have.

### A1.5 Failure modes I considered for option 2 and how the operational MUSTs address each

**F1 — phase advance mid-session.** This is the largest concrete failure mode. The current `app.py:1822` mechanism survives phase advance because it (a) writes the file, (b) Claude Code auto-loads `.claude/phase_context.md` on next turn (or does it? See A1.6 below — there's some uncertainty about this). Under option 2, the SessionStart hook fires *once*, at session init. Mid-session phase advances do not re-fire it.

MR6.2 in the operational spec demands the spec author pick a remediation:
- **(a) Explicit re-read message:** when `app.py` writes the new phase context to disk, it sends a turn to the active agent saying "re-read your phase context." The agent's Read tool fires; the file's contents enter the chat (not system prompt); the agent uses them as instructions. *Tradeoff:* this is what claudechic does TODAY in spirit (`app.py:1648` literally tells the agent "Read .claude/phase_context.md"). It's familiar but it puts phase content in the conversation, not the system prompt.
- **(b) Per-turn rehydration via UserPromptSubmit hook:** every turn the user submits, a hook re-reads `<repo>/.claudechic/phase_context.md` and injects a system-prompt-equivalent. Always fresh. *Tradeoff:* every turn pays the file-read cost; the hook surface might not exist in the SDK as cleanly as SessionStart.

Skeptic preference: **(a)** — it's the existing pattern, well-tested in claudechic, and preserves the simplicity of "SessionStart is one-shot." The spec MUSTs leave the choice to the spec author but require *one* be picked.

**F2 — hook crashes silently.** Hooks can throw exceptions. SDK behavior on hook exception varies by surface. MR6.3 requires the implementation to (a) catch all hook exceptions, (b) log at WARNING, (c) surface a UI indicator. The claudechic StatusFooter has indicator widgets per `widgets/layout/footer.py`; adding a "context degraded" indicator is a small extension.

**F3 — context-window exhaustion.** A long workflow with detailed phase docs plus several `.claudechic/rules/` files plus the always-on awareness statement plus user-tier and project-tier rules can sum to thousands of tokens — easily a noticeable chunk of context budget. MR6.4 budgets 8000 tokens (round number; spec authors may tune) and requires truncation of fuller-context content first. Always-on statement is preserved because losing it leaves the agent with no claudechic awareness at all.

**F4 — first-read tracking scope.** If the PreToolUse hook tracks "first read fired" globally (e.g., a module-level dict), then agent B's first read is suppressed because agent A already triggered. MR6.5 requires per-`Agent` (per-`ClaudeSDKClient`) tracking. Implementation hint: the existing `Agent` class in `claudechic/agent.py` is the natural place.

**F5 — collision with user's `.claude/rules/`.** If user has a `.claude/rules/foo.md` saying "always reply in French" and claudechic injects via SessionStart hook a `.claudechic/rules/foo.md` saying "always reply concisely," both reach the system prompt. The agent sees both; behavior is undefined ("French AND concise" probably; the model sorts it out at inference time). This is a UX problem, not a correctness bug. UserAlignment / TerminologyGuardian own the user-facing explanation of precedence. Skeptic flags it but does not require a code-level resolution.

### A1.6 An open question about today's phase-context mechanism

The current `app.py:1822` writes `phase_context.md` to `.claude/`. Code comments at `app.py:1822` say "Writes phase prompt to .claude/phase_context.md so it becomes part of the system prompt on the next turn" — implying Claude Code auto-loads it. But `app.py:1648` *tells the agent* to "Read .claude/phase_context.md for your full phase instructions" — implying the agent reads it explicitly.

These two are not consistent. Either:
- Claude Code does auto-load `.claude/phase_context.md` (in which case the explicit "Read" instruction is redundant), or
- Claude Code does NOT auto-load it (in which case the comment about "system prompt on the next turn" is wrong, and phase context has been chat-content all along, not system prompt).

The Implementer phase should determine which is true (test on a current Claude Code version) before implementing the SessionStart-hook replacement. **If phase context has actually been chat-content all along**, then MR6.2's option (a) (explicit re-read message) is the only behavior preservation; option (b) (per-turn rehydration into system prompt) would be a behavior *upgrade*, not just a relocation.

Skeptic does not adjudicate this; it surfaces it for the Implementer phase. Either resolution is fine; clarity is what matters.

---

## A2 — Composability decomposition: where the lenses agree and disagree

| Item | Composability says | Skeptic concurs? | Notes |
|---|---|---|---|
| 7-group work decomposition (A–G) | Use it | Partially | skeptic_review.md §6 CW-5 already noted that several items collapse: D1–D6 → 1 hook + 1 string + 1 removal; A1–A7 → one phase one test gate; per-parser `resolve()` → one generic function; tier provenance → workflows only. The 7-group framing is fine as a high-level dependency map; the within-group item count should drop. |
| INV-9 (phase + awareness share impl) | Required | Yes | This is precisely Skeptic's CW-5 / R-S2 simplification. Composability INV-9 makes it a testable invariant. Win. |
| Tier provenance on every parsed item (R3.6) | Required | Concur with caveat | Skeptic's R-S3 said "workflows only" was sufficient. Composability's R3.6 makes it universal, justified by "diagnostic tools." Acceptable: provenance is a single field; the cost is small; diagnostic value is real. Skeptic withdraws R-S3 in favor of R3.6's universal application. |
| Per-category `resolve()` method (R2.2 + R3.1) | Each parser implements its own | Skeptic prefers one generic function | R-S4 still stands as a Skeptic preference. R3.1 fixes the identity unit per category; R2.2 says each category has a "single, dedicated parser implementing the parse/resolve law." A generic `resolve_by_id(items_per_tier, key_fn)` called by all four parsers satisfies the law without per-parser code duplication. The parsers still each implement their own `parse()`. The spec author can pick either shape; they are behaviorally identical. Skeptic flags but does not block. |
| Worktree symlink for `.claudechic/` (R8.1, INV-10) | Add it | Concur | I had concerns earlier about A4's no-symlink prohibition. Composability's R8 disambiguation (R8 vs A4) resolves: A4 applies to R6 (agent-awareness mechanism); R8's filesystem-state-propagation symlink is pre-existing and a separate concern. Skeptic concurs. |

---

## A3 — Why option 2 also dovetails with the boundary lint allowlist (R-S1) cleanly

If the spec adopts option 2, the boundary lint allowlist contains:

```
# Reads (unrestricted)
read: .claude/**

# Writes (claudechic owns)
write: ~/.claudechic/**
write: <repo>/.claudechic/**

# Worktree symlink target (R8.1)
write: <worktree>/.claude   # symlink, pre-existing pattern
write: <worktree>/.claudechic  # symlink, new per R8.1
```

That's the entire allowlist. Anything else in `.claude/` is a finding. The lint reads the allowlist as a YAML file (or hardcodes it as a Python list — implementation choice).

**Compare to option 3's allowlist:**

```
# All of the above, PLUS
write: .claude/claudechic_*.md       # always-on awareness file
write: .claude/claudechic_phase_*.md # phase context file
# (And as new claudechic-namespaced files emerge, more entries)
```

Each new entry is an opportunity for collision with future Claude Code naming conventions. The allowlist grows over time. Option 2's allowlist is *closed*: it has the entries it needs and no more.

This is a clean simplification, not a shortcut. Skeptic recommends locking the allowlist as the option-2 set above.

---

*End of Skeptic review appendix.*
