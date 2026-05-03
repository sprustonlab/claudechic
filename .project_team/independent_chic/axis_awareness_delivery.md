# Axis Spec — Agent-Awareness / Context-Delivery Mechanism

> **⚠️ SUPERSEDED — DO NOT IMPLEMENT FROM THIS FILE.**
>
> This axis-spec is preserved as a historical artifact. The mechanism it describes (`claudechic/context_delivery/` package + SessionStart hook + PreToolUse first-read hook + per-session "fired" tracker + size budgets + recognized-filename catalog with priority resolution) was **superseded by RESEARCH.md Option B** (user-approved on 2026-04-26).
>
> The Claude Agent SDK already loads `~/.claude/rules/*.md` natively when `setting_sources` includes `"user"` (already configured at `claudechic/app.py:969`). The new mechanism — install bundled `claudechic/context/*.md` files into `~/.claude/rules/claudechic_*.md` on every claudechic startup, gated by an `awareness.install` config toggle — leverages the SDK's existing rules-load instead of re-implementing it.
>
> **Authoritative replacement: SPEC.md §4** (Group D — Agent awareness via SDK-native rules + phase-context refresh).
>
> **Rationale for the supersession: SPEC_APPENDIX.md** (coordinator-authored).
>
> The content below is preserved verbatim only for traceability of the design conversation. Implementer MUST consult SPEC.md §4, NOT this file.

---

**Axis:** R6 (Agent-awareness delivery) **unified with** the existing `phase_context.md` write site (per Composability INV-9 / R6.5).
**Scope:** the single mechanism by which file-sourced context reaches a Claude session at four triggering moments — session start, phase advance, first read inside any `.claudechic/`, and after `/compact`.
**Audience:** Implementer + Tester. This document is operational. Rationale, alternatives, and trade-offs live in `axis_awareness_delivery_appendix.md`.
**Mode:** RFC-2119. MUST / MUST NOT / SHOULD / MAY.

This spec is downstream of:
- vision §"What we want" §3 (boundary), §4 (agent awareness)
- STATUS L3 (with A7 softening), L15 + A11 (two-piece), A4 (behavioral mirror; no symlinks; no `.claude/` overwrites; non-destructive `.claude/` touches OK)
- specification/composability.md R5, R6 in full, Seam-C, INV-9, §8.1
- specification/skeptic_review.md §"Cross-lens: R6 risk weighting" — MR6.1 through MR6.8 + allowlist patterns + failure-mode table
- specification/user_alignment.md §"Cross-lens: UX validation" — R6-UX.1 through R6-UX.4

It is upstream of (does not duplicate):
- the loader-resolution axis spec (R3 mechanics);
- the boundary-test axis spec (encodes write-site classifications enumerated in §11 below; consumes the allowlist statement in §11.2);
- TerminologyGuardian (owns prose wording of all context content);
- UIDesigner (owns UI surfaces).

**Canonical wording.** This mechanism is referred to throughout as the **"claudechic-awareness injection"** (per R6-UX prescribed wording). The word "rules" is reserved for the rules content category and MUST NOT appear in user-facing prose for this mechanism. Internal code/symbol names follow the same rule (no `RuleInjector`, no `claudechic_rules_loader`).

---

## 1. Mechanism (the single chosen design)

The mechanism is a single Python module — `claudechic.context_delivery` — that exposes one abstraction (`ContextDelivery`) with three SDK registrations PLUS one `app.py`-side trigger. Each registration uses a `claude_agent_sdk` extension point. None of the registrations writes anywhere inside `.claude/`. None creates a symbolic link. None edits a Claude-owned settings file.

| Registration | SDK surface / app surface | Trigger moment | Source |
|---|---|---|---|
| **SessionStart** (L15 piece 1 + initial phase-context) | `ClaudeAgentOptions.hooks["SessionStart"]` — one `HookMatcher` | Once at every agent session init | Always-on text from `<package>/defaults/context/awareness_brief.md` (with optional `<repo>/.claudechic/context/awareness_brief.md` override per §3.4) **AND** current phase context from `<repo>/.claudechic/phase_context.md` (if present) |
| **PreToolUse / first-read** (L15 piece 2) | `ClaudeAgentOptions.hooks["PreToolUse"]` — one `HookMatcher` against file-touching tools | First tool call in the agent's session whose `tool_input` references a path inside any `.claudechic/` directory | `<package>/defaults/context/awareness_full.md` plus the system docs in the same directory (concatenated; project tier MAY override per §4.5) |
| **PostCompact** (re-injection after `/compact`) | `ClaudeAgentOptions.hooks["PostCompact"]` — existing pattern from `agent_folders.py:107` | After `/compact` completes | `<repo>/.claudechic/phase_context.md` (read fresh from disk; no cache) |
| **Phase-advance re-read** (mid-session refresh, MR6.2 option a) | `app.py._inject_phase_prompt_to_main_agent` sends a chat message to the active agent | Whenever phase advances during an active workflow | The newly-rewritten `<repo>/.claudechic/phase_context.md` (the agent reads it via its own `Read` tool) |

**MUST:** every claudechic-managed `Agent` (the main agent and every chic-MCP-spawned sub-agent — i.e., every code path that calls `Agent.connect(options)` where `options` was produced by `_make_options`) MUST receive all three SDK registrations through the options object built by `_make_options`. The phase-advance re-read fires only for the agent participating in the active workflow (existing scope, unchanged).

**MUST NOT:** the mechanism MUST NOT use `ClaudeAgentOptions.add_dirs` to expose `.claudechic/` content as auto-loaded "rules". `add_dirs` widens the read scope; it does not auto-load.

**MUST NOT:** the mechanism MUST NOT write a pointer file or any other file anywhere inside any `.claude/` directory at any time. Per Skeptic MR6.6: even the A7-permitted "non-destructive incidental write" path is forbidden for R6 in this run because the awareness/phase-context content is **primary state** per R5.1.

**MUST NOT:** the mechanism MUST NOT call `claude config set`, edit `~/.claude/settings.json`, edit `<repo>/.claude/settings.json` / `settings.local.json`, or otherwise mutate any Claude-owned settings surface.

**MUST NOT:** the mechanism MUST NOT create symbolic links anywhere.

---

## 2. Module layout

A new package `claudechic/context_delivery/` MUST be added with the following files. (Note: this is a new directory under `claudechic/`. It is sibling to `hints/`, `guardrails/`, etc. It is NOT a tier of content — it is engine code.)

| File | Responsibility |
|---|---|
| `claudechic/context_delivery/__init__.py` | Public API: `build_options_extras(...)` → returns the dict of `HookMatcher` lists to be merged into `ClaudeAgentOptions.hooks` by `_make_options`. |
| `claudechic/context_delivery/sources.py` | Pure file readers + tier-walk for context content: `read_awareness_brief(repo)`, `read_awareness_full(repo)`, `read_phase_context(repo)`, `discover_context_files(repo) -> list[Path]`. Each handles missing files silently and returns `str | None` (or `list[Path]`). |
| `claudechic/context_delivery/sessionstart.py` | The SessionStart hook implementation. Composes always-on + phase-context payload; enforces size budget (§3.5); handles failures (§3.6). |
| `claudechic/context_delivery/firstread.py` | The PreToolUse hook implementation + per-session "fired" tracker. |
| `claudechic/context_delivery/postcompact.py` | The PostCompact hook implementation. Replaces the body of `claudechic/workflows/agent_folders.py:create_post_compact_hook` (which becomes a thin wrapper or is removed; see §10). |
| `claudechic/context_delivery/paths.py` | `is_under_claudechic(path: str | Path, *, anchors: Iterable[Path]) -> bool` — pure path classifier (see §6). |

**MUST:** `claudechic/context_delivery/` MUST NOT import from `claudechic/app.py`, `claudechic/agent.py`, `claudechic/agent_manager.py`, or any UI/widget module. It is engine code with the same isolation discipline as `claudechic/hints/`. It MAY import from `claudechic/errors.py` for the log channel (for WARN-level surfacing per MR6.3).

**SHOULD:** `claudechic/context_delivery/` SHOULD import only from `claudechic/workflows/` (the engine package post-restructure), `claudechic/errors.py`, and the standard library + `claude_agent_sdk`.

---

## 3. SessionStart registration (L15 piece 1 + initial phase-context delivery)

### 3.1 Hook signature

**MUST:** `_make_options` MUST register one `SessionStart` `HookMatcher` whose:

- `matcher` field is `None` (no sub-event filtering needed; SessionStart fires at session init).
- `hooks` field is a single async callable returned by `claudechic.context_delivery.sessionstart.make_callback()`.
- `timeout` field is left at the SDK default.

The callback signature is:

```python
async def callback(
    hook_input: dict,            # SessionStart hook input (session_id, cwd, etc.)
    matched: str | None,
    ctx: HookContext,
) -> SyncHookJSONOutput: ...
```

The callback MUST return a `SyncHookJSONOutput` whose `hookSpecificOutput` is a `SessionStartHookSpecificOutput` with `additionalContext` set to the composed payload (or `{}` if the payload is empty AND no failure occurred — see §3.6).

### 3.2 Payload composition

**MUST:** the SessionStart payload is composed in this exact order, with the literal separator `\n\n---\n\n` between non-empty pieces:

1. **Always-on awareness statement** — read by `sources.read_awareness_brief(repo=hook_input["cwd"])`. Source: `<repo>/.claudechic/context/awareness_brief.md` if present (project-tier override), else `<package>/defaults/context/awareness_brief.md` (package tier). The prose is delegated to TerminologyGuardian; this spec MUST NOT prescribe wording.
2. **Phase-context content** — read by `sources.read_phase_context(repo=hook_input["cwd"])`. Source: `<repo>/.claudechic/phase_context.md` if present. Empty/absent file produces no piece (no separator).

**MUST:** if both pieces are empty/absent, the callback MUST return `{}` (no `additionalContext`). The session MUST start normally.

**MUST NOT:** the payload MUST NOT include the awareness_full content (system docs). That content reaches the agent through the PreToolUse first-read hook (§4), not through SessionStart. Including system docs in SessionStart would balloon every session's prompt for users who never read inside `.claudechic/` — a wasted budget.

### 3.3 Source-content layering (R6.3 + R6-UX.2)

**MUST:** `sources.read_awareness_brief(repo)` walks tier roots in priority order — project (`<repo>/.claudechic/context/`) beats user (`~/.claudechic/context/`) beats package (`<package>/defaults/context/`). The first tier that contains `awareness_brief.md` wins; the file fully replaces lower-tier versions (no merging).

**MUST:** R3.2 override-by-filename semantics apply (winner replaces lower; no field merging).

**MUST:** the recognized source root for context content MUST be exactly the three locations above. Files in any other location have no effect.

**MUST:** `docs/configuration.md` MUST document the recognized source roots (project / user / package), the override priority, the filename catalog (which filenames the loader recognizes), and the explicit statement: "files placed outside the recognized roots, or with filenames not in the recognized catalog, have no effect."

### 3.4 Recognized filename catalog

**MUST:** the loader recognizes these filenames in any tier's `context/` directory:

- `awareness_brief.md` — used by SessionStart hook (always-on piece)
- `awareness_full.md` — used by PreToolUse first-read hook (the lead document)
- `claudechic-overview.md`, `multi-agent-architecture.md`, `workflows-system.md`, `hints-system.md`, `guardrails-system.md`, `checks-system.md`, `manifest-yaml.md`, `CLAUDE.md` — used by PreToolUse first-read hook (system-doc concatenation, in this order)

**SHOULD (R6-UX.3):** when `sources.discover_context_files(repo)` finds a `*.md` file under any recognized tier's `context/` directory whose filename is NOT in the catalog above, the loader SHOULD log an INFO-level message naming the unrecognized file and the recognized catalog, so the user understands why their file had no effect. The log MUST NOT raise. The loader MUST NOT load the unrecognized file into any payload.

### 3.5 Payload size budget (MR6.4)

**MUST:** the composed SessionStart payload MUST NOT exceed **8000 tokens** (or, equivalently, **32000 characters** as a conservative byte-count proxy — Implementer picks the implementation; Tester verifies behavior, not the unit). The check MUST happen after composition and before return.

**MUST:** on overflow, the callback MUST:

1. Preserve the always-on awareness statement (piece 1) verbatim.
2. Truncate the phase-context piece (piece 2) from the END until the combined payload is within budget.
3. Append the literal sentinel string `\n\n[CONTEXT TRUNCATED — see <repo>/.claudechic/phase_context.md for full content]` to the truncated phase-context piece (so the agent knows truncation occurred).
4. Log a WARNING via the claudechic log channel with: the original size, the truncated size, the workflow id, and the phase id.

**MUST:** if even the always-on piece alone exceeds budget, the callback MUST emit a WARNING and MUST truncate the always-on piece from the END (with the same sentinel). The phase-context piece MUST be omitted in this case.

### 3.6 Failure handling (MR6.3)

**MUST:** the SessionStart callback MUST be wrapped in a top-level `try/except` that catches `Exception`. On any caught exception, the callback MUST:

1. Log a WARNING via the claudechic log channel naming the exception type, the message, and (if present) the file path that failed to read.
2. Surface the failure in the StatusFooter via the existing `set_log_notify_callback` notification path (severity=`warning`) so the user sees a one-line indicator. (The exact UI presentation is UIDesigner's call; the spec REQUIRES that the failure is visible, not silent.)
3. Return `{}` (empty SyncHookJSONOutput). The session MUST start normally without the awareness payload.

**MUST NOT:** a failure in the SessionStart callback MUST NOT prevent the agent's session from starting. Silent loss of always-on awareness is forbidden — the WARNING + UI indicator is the surface.

---

## 4. PreToolUse / first-read registration (L15 piece 2)

### 4.1 Hook signature

**MUST:** `_make_options` MUST register one `PreToolUse` `HookMatcher` whose:

- `matcher` field is the regex string `"Read|Glob|Grep|Edit|Write|MultiEdit|NotebookEdit"` (pipe-joined exact tool names; no anchors).
- `hooks` field is a single async callable returned by `claudechic.context_delivery.firstread.make_callback()`.
- `timeout` field is left at the SDK default.

The matcher pattern MUST cover every tool that the SDK exposes for reading the filesystem. If the SDK gains a new file-reading tool, the spec MUST add it to the matcher regex (a comment in `firstread.py` records the list of tools).

### 4.2 Callback contract

**MUST:** the callback signature is:

```python
async def callback(
    hook_input: PreToolUseHookInput,
    matched_tool: str | None,
    ctx: HookContext,
) -> SyncHookJSONOutput: ...
```

**MUST:** the callback MUST:

1. Extract `session_id` from `hook_input["session_id"]`.
2. Compute the candidate paths from `hook_input["tool_input"]` per the rules in §6.
3. If no candidate path is under any `.claudechic/` anchor (recursive — any descendant per MR6.7), return `{}` (empty dict — no injection, no permission decision).
4. If at least one candidate path is under a `.claudechic/` anchor, consult the per-session "fired" tracker (§4.3). If the tracker reports already-fired for this `session_id`, return `{}`.
5. Otherwise: mark the tracker as fired for this `session_id`, read the full-context content (§4.4), apply the size budget (§4.6), and return:

```python
{
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "additionalContext": full_context_text,
    },
}
```

The callback MUST NOT set `permissionDecision`, MUST NOT set `decision`, and MUST NOT block tool execution. The return value MUST be a valid `SyncHookJSONOutput` per `claude_agent_sdk.types`.

**MUST:** failure handling parallels §3.6 — `try/except Exception`, log WARNING, surface UI indicator, return `{}` AND mark the tracker as fired (so the failure is silent on retry, not retried per-tool-call).

### 4.3 Per-session "fired" tracker (MR6.5)

**MUST:** the tracker is an in-memory `dict[str, bool]` (or equivalent set) at `claudechic/context_delivery/firstread.py` module scope, keyed by `hook_input["session_id"]`. The tracker MUST NOT be persisted to disk.

**MUST:** the tracker is per-`Agent`-instance in effect: each `ClaudeSDKClient` session has its own session_id, and the tracker keys off it. Two distinct agents using two distinct `session_id`s MUST be tracked independently. Agent recreation (a new `ClaudeSDKClient` session) yields a new session_id and therefore a fresh tracking entry — first-read fires once per agent-session.

**MUST:** the tracker MUST NOT be cleared on workflow advance, on `/compact`, on agent close, or on any UI event. It is cleared only by process exit.

**MAY:** the tracker MAY expose a private `_clear_for_tests()` helper for unit tests.

### 4.4 Source

**MUST:** the full-context content is the concatenation, in this exact order, of every recognized filename present (per the catalog in §3.4) **except** `awareness_brief.md` (which is always-on, not first-read):

```
awareness_full.md
claudechic-overview.md
multi-agent-architecture.md
workflows-system.md
hints-system.md
guardrails-system.md
checks-system.md
manifest-yaml.md
CLAUDE.md
```

The separator between non-empty files is the literal sequence `\n\n---\n\n`. Files that are absent at all tiers are silently skipped.

**MUST:** for each filename in the list, `sources.read_*` walks the tier roots (project → user → package) and uses the highest-priority tier's version (per §3.3 — same override-by-filename semantics as awareness_brief.md). Filenames present at multiple tiers do NOT concatenate; they replace.

**MUST:** the prose of all context files is delegated to TerminologyGuardian. This spec MUST NOT prescribe wording, only recognized filenames and concatenation order.

### 4.5 Project-tier override of context content

**MAY (R6.3 + R6-UX.2):** project-tier overrides at `<repo>/.claudechic/context/` and user-tier overrides at `~/.claudechic/context/` ARE permitted. The recognized filename catalog (§3.4) and the override priority (project > user > package) apply uniformly to both the SessionStart payload and the PreToolUse first-read payload.

**MUST NOT:** introducing new categories of content (e.g., per-role context) is out of scope for this run.

### 4.6 Payload size budget for first-read

**MUST:** the first-read payload MUST NOT exceed **24000 tokens** (or equivalently **96000 characters** as a conservative byte-count proxy — Implementer picks the implementation). On overflow, the callback MUST truncate from the END (the latest concatenated file is truncated first; whole files are dropped before partial truncation), append the sentinel `\n\n[CONTEXT TRUNCATED — see <package>/defaults/context/ for full content]`, and log a WARNING.

The first-read budget is larger than the SessionStart budget (§3.5) because first-read content fires only once per agent-session, on demand; whereas SessionStart content rides every turn's system prompt and competes with the conversation budget.

---

## 5. Phase-context delivery (Seam-C / R6.5 / INV-9 unification)

### 5.1 New path

**MUST:** the phase-context file MUST live at `<repo>/.claudechic/phase_context.md`. The legacy path `<repo>/.claude/phase_context.md` MUST NOT be written to, read from, or unlinked by any code shipped in this work.

### 5.2 Lifecycle (replaces `claudechic/app.py:1623–1648, 1822–1834, 1925–1928`)

**MUST:** the lifecycle is:

| Event | Action | Code site (post-edit) |
|---|---|---|
| Workflow activation (today: app.py:1623–1626) | Engine writes phase context to `<repo>/.claudechic/phase_context.md`. The directory `<repo>/.claudechic/` MUST be created with `mkdir(parents=True, exist_ok=True)` if absent. | `app.py._activate_workflow` → `_write_phase_context` |
| Phase advance (today: app.py:1822–1825) | Engine rewrites the same file with new phase content. If `assemble_phase_prompt` returns `None` or empty, the file MUST be unlinked (existing pattern preserved). **AND** the engine MUST send an explicit re-read message to the active agent per §5.3. | `app.py._inject_phase_prompt_to_main_agent` |
| Workflow deactivation (today: app.py:1925–1928) | Engine unlinks the file (suppress `OSError`). | `app.py._deactivate_workflow` |

**MUST:** the kick-off message at `app.py:1648` MUST be updated to read `.claudechic/phase_context.md` instead of `.claude/phase_context.md`. The text "Read .claude/phase_context.md..." becomes "Read .claudechic/phase_context.md...".

**MUST:** the docstring at `app.py:1834–1838` MUST be updated to refer to the new path. (No behavior change; doc-surface only.)

### 5.3 Phase-advance re-read (mid-session refresh, MR6.2 option a)

**MUST:** when the engine advances phases during an active session (`_inject_phase_prompt_to_main_agent`), the engine MUST send a chat message to the active agent of the form:

> "Workflow phase advanced — read `.claudechic/phase_context.md` for the current phase instructions."

The exact wording is delegated to TerminologyGuardian; the spec REQUIRES that the message:

1. Names `.claudechic/phase_context.md` as the file to read.
2. Reaches the active agent through the existing `_send_to_active_agent` pathway (or equivalent) so the agent's next turn includes a turn that calls Read on the file.

**MUST NOT:** the spec MUST NOT use a SessionStart hook re-fire mechanism for phase-advance refresh. SessionStart fires once per session; mid-session phase advances are handled by the explicit re-read message (this preserves today's `app.py:1822` pattern; it is also the lower-risk option per MR6.2(a)).

**MUST NOT:** the spec MUST NOT use a UserPromptSubmit hook to re-inject phase context per turn. Per-turn re-injection is the alternative (MR6.2(b)) and is rejected for this run.

### 5.4 Why this counts as unification

The `ContextDelivery` module's `sources.py` contains the single function `read_phase_context(repo)` that reads `<repo>/.claudechic/phase_context.md`. This function is called by:

- The SessionStart registration (§3.2) — for initial phase-context delivery at session start.
- The PostCompact registration (§7) — for re-injection after `/compact`.
- Any future hook or surface that needs current phase context.

The legacy `claudechic/workflows/agent_folders.py:assemble_phase_prompt` continues to be the WRITE-side source: `app.py._write_phase_context` calls `assemble_phase_prompt` to produce the content, then writes it to `<repo>/.claudechic/phase_context.md`. Reads (SessionStart, PostCompact, agent on-demand `Read`) all go through `read_phase_context()` or the agent's own Read tool.

**MUST:** every read of phase-context content (other than the agent's own `Read` tool) MUST go through `claudechic.context_delivery.sources.read_phase_context`. No second reader function MAY be introduced.

---

## 6. Path classification: "is this path under any `.claudechic/`?" (MR6.7)

The first-read hook (§4.2 step 2) and any future caller MUST classify candidate paths consistently. The classifier lives at `claudechic/context_delivery/paths.py:is_under_claudechic`.

### 6.1 Candidate paths from a tool input

**MUST:** for a `PreToolUse` hook input, the candidate paths are extracted from `tool_input` by tool name:

| Tool | Field(s) → candidate paths |
|---|---|
| `Read` | `file_path` |
| `Edit` | `file_path` |
| `Write` | `file_path` |
| `MultiEdit` | `file_path` |
| `NotebookEdit` | `notebook_path` |
| `Glob` | resolve `path` (default `cwd`) joined with literal-prefix segment of `pattern` (split on first `*`/`?`/`{`/`[`); this gives a containing dir for the glob — NOT every match |
| `Grep` | `path` (default `cwd`); also any explicit `glob` param's literal-prefix segment |

**MUST:** if a tool input field is absent, the corresponding candidate is dropped silently. If all candidates are dropped, the callback returns `{}` (no injection).

**SHOULD:** path strings are converted to `Path` objects but NOT resolved through symlinks. Implementations MAY use `os.path.expanduser` + `os.path.normpath` instead of `Path.resolve`, picking whichever yields the more predictable cross-platform behavior.

### 6.2 Anchor set

**MUST:** the anchors against which a candidate path is tested are:

1. `<repo>/.claudechic/` — where `<repo>` is the agent's `cwd` from `hook_input["cwd"]`.
2. `~/.claudechic/` — expanded user home.

The anchors MUST NOT include `<package>/defaults/`. The package directory is internal claudechic code; reading from it is not a "first read inside a `.claudechic/`" event under L15.

**MUST (MR6.7):** `is_under_claudechic(candidate, anchors=...)` returns True iff, for some `anchor` in `anchors`, `candidate` after expansion is `anchor` itself or has `anchor` as a parent **at any depth** (recursive). The check is by path-segment-prefix on the normalized absolute path; symlinks are not followed.

### 6.3 Edge cases

**MUST:** the classifier MUST treat the following as **inside** a `.claudechic/`:
- `<repo>/.claudechic/anything` — true
- `<repo>/.claudechic/runs/X/y.md` — true (R7 artifact dirs are inside `.claudechic/`)
- `<repo>/.claudechic/context/awareness_full.md` — true (project-tier override file)
- `~/.claudechic/global/rules.yaml` — true

**MUST:** the classifier MUST treat the following as **NOT inside** a `.claudechic/`:
- `<repo>/.claude/anything` — false (different directory)
- `<repo>/some_file_that_mentions_dotclaudechic_in_its_name` — false (path-segment match, not substring match)
- `<package>/defaults/context/*.md` — false (package internal)
- Any path outside both anchors — false

---

## 7. Post-compact registration

The existing post-compact hook in `claudechic/workflows/agent_folders.py:create_post_compact_hook` MUST be moved to `claudechic/context_delivery/postcompact.py` and updated to read from the new path.

### 7.1 Behavior

**MUST:** the post-compact callback signature and SDK shape MUST remain identical to today's (returns `{"reason": <prompt>}` when content is non-empty, returns `{}` otherwise). The callback fires regardless of which agent triggered `/compact`.

**MUST:** the source of the re-injected text MUST be `read_phase_context(repo=hook_input["cwd"])` — i.e., a fresh read of `<repo>/.claudechic/phase_context.md`. The existing implementation regenerates the prompt by calling `assemble_phase_prompt` against the engine's current phase. The new implementation reads the file written by `_write_phase_context`.

**MUST:** if `read_phase_context` returns `None` or empty, the callback MUST return `{}`. No error MUST surface.

**MUST:** size-budget handling parallels §3.5: the post-compact payload MUST NOT exceed the same 8000-token / 32000-character budget as the SessionStart payload; on overflow, truncate from the END with the same sentinel and log a WARNING.

**MUST:** failure handling parallels §3.6 — `try/except Exception`, log WARNING, surface UI indicator, return `{}`.

### 7.2 Registration

**MUST:** registration is performed by `_merged_hooks` (`app.py:920`) and remains conditional on the agent being a workflow participant (per existing code). The condition logic does not change.

**MUST:** the import in `app.py:920` MUST be updated from `from claudechic.workflow_engine.agent_folders import create_post_compact_hook` (or the post-restructure `claudechic.workflows.agent_folders`) to `from claudechic.context_delivery.postcompact import create_post_compact_hook`.

---

## 8. Public API of `claudechic.context_delivery`

### 8.1 `build_options_extras`

**MUST:** the package exposes one entry point used by `_make_options`:

```python
# claudechic/context_delivery/__init__.py

from typing import TypedDict
from claude_agent_sdk.types import HookMatcher

class OptionsExtras(TypedDict):
    session_start: list[HookMatcher]
    pre_tool_use: list[HookMatcher]

def build_options_extras() -> OptionsExtras:
    """Return the SDK-hook fragments contributed by ContextDelivery.

    The returned hook matchers are MERGED (extend, not replace) into the
    corresponding entry in ClaudeAgentOptions.hooks.
    """
```

**MUST:** `_make_options` MUST call `build_options_extras()` once per agent spawn and merge the result into `_merged_hooks(agent_type=...)`:

- `hooks.setdefault("SessionStart", []).extend(extras["session_start"])`
- `hooks.setdefault("PreToolUse", []).extend(extras["pre_tool_use"])`

The other PreToolUse matchers (guardrail-driven, etc.) MUST coexist; matcher ordering MUST NOT be specified by this spec (the SDK fires all matchers whose pattern matches; order doesn't affect correctness here).

**MUST NOT:** `_make_options` MUST NOT set `ClaudeAgentOptions.system_prompt` to inject claudechic-awareness content. Always-on delivery happens through the SessionStart hook only. The `system_prompt` field MAY remain unset (SDK default applies).

### 8.2 `create_post_compact_hook`

**MUST:** the new module exposes the same-named function with the same signature as today's `claudechic/workflows/agent_folders.py:create_post_compact_hook`:

```python
def create_post_compact_hook(
    engine: Any,
    agent_role: str,
    workflows_dir: Path,
) -> dict[str, list[HookMatcher]]:
    ...
```

The return shape (dict mapping `"PostCompact"` → `[HookMatcher(...)]`) MUST be identical to today's.

**MUST NOT:** the new `create_post_compact_hook` MUST NOT also register SessionStart or PreToolUse extras. Those are the responsibility of `build_options_extras` only. Each caller adds what it needs; the seams stay clean.

---

## 9. Fate of `ContextDocsDrift` and `context_docs_outdated`

### 9.1 Decision

**MUST:** retire both, as part of this work. There is no replacement.

### 9.2 Code edits required

| File | Edit |
|---|---|
| `claudechic/hints/triggers.py` | Delete the `ContextDocsDrift` class (lines 25–82) **and** the `_PKG_CONTEXT_DIR` module-level constant at line 22 (used only by `ContextDocsDrift`). The remaining file MUST still import cleanly. |
| `claudechic/hints/__init__.py` | Remove the `from claudechic.hints.triggers import ContextDocsDrift` line (currently line 8) and the `"ContextDocsDrift"` entry from `__all__` (currently line 24). |
| `claudechic/global/hints.yaml` (post-restructure: `claudechic/defaults/global/hints.yaml`) | Delete the `context_docs_outdated` hint declaration (lines 93–99 in the current file). The "# --- Upgrade drift detection ---" comment at line 91 MAY be removed if no other hint uses that section. |
| `claudechic/app.py` | Delete the trigger registration at lines 1387–1389 (`_trigger_registry["context-docs-drift"] = ContextDocsDrift` and the surrounding `try/except` whose only purpose is this import). The remaining `_trigger_registry: dict[str, type] = {}` at line 1385 MUST remain. |
| `claudechic/hints/types.py` | The docstring at line 212 referencing `"context-docs-drift"` MUST be updated to use a different example or to drop the example entirely. No behavioral change. |

### 9.3 Test requirement

**MUST:** the boundary axis-spec's CI test MUST include an assertion that `ContextDocsDrift` is not importable from `claudechic.hints.triggers` and that no hint with `trigger.type == "context-docs-drift"` appears in any loaded manifest.

---

## 10. Fate of `/onboarding`'s `context_docs` phase

### 10.1 Decision

**MUST:** remove the `context_docs` phase from the `/onboarding` workflow entirely. There is no no-op replacement; the phase is deleted.

### 10.2 Code edits required

| File | Edit |
|---|---|
| `claudechic/workflows/onboarding/onboarding.yaml` (post-restructure: `claudechic/defaults/workflows/onboarding/onboarding.yaml`) | Delete the `context_docs` phase entry (lines 14–26: the YAML block from `- id: context_docs` through `prompt: "Context docs installed (or skipped)?"`). The `manual-confirm` advance check on `orientation` (line 12) MUST be updated to a phrasing that does not reference context docs. |
| `claudechic/workflows/onboarding/onboarding_helper/context_docs.md` (post-restructure: `claudechic/defaults/workflows/onboarding/onboarding_helper/context_docs.md`) | Delete the file. |
| `claudechic/workflows/onboarding/onboarding_helper/identity.md` (post-restructure: `claudechic/defaults/workflows/onboarding/onboarding_helper/identity.md`) | Delete the bullet at line 10–11. Delete the "Context" section at lines 26–32. |

### 10.3 Workflow YAML schema check

**MUST:** the loader (post-restructure) MUST accept an `onboarding.yaml` with a single phase. No per-workflow minimum-phase-count assertion exists today; the spec records this as a known property.

---

## 11. Boundary-test write-site enumeration (input for Seam-E / R5.4)

The boundary-test axis-agent (`axis_boundary_test`) owns the registry and CI assertion. This axis enumerates **every write site introduced or modified by this mechanism** with its R5.1 classification and provides the allowlist statement.

### 11.1 Write-site table

| Write site (file:line, post-edit) | Classification | Resolves to |
|---|---|---|
| `claudechic/app.py` `_write_phase_context` write call (was line 1853) | **primary-state** | `<repo>/.claudechic/phase_context.md` |
| `claudechic/app.py` `_write_phase_context` `mkdir(parents=True, exist_ok=True)` | **primary-state** | `<repo>/.claudechic/` |
| `claudechic/app.py` `_write_phase_context` `phase_file.unlink()` (the empty-prompt branch, was line 1867) | **primary-state** (state cleanup) | `<repo>/.claudechic/phase_context.md` |
| `claudechic/app.py` `_deactivate_workflow` `phase_file.unlink()` (was line 1928) | **primary-state** (state cleanup) | `<repo>/.claudechic/phase_context.md` |
| Per-session "fired" tracker (`claudechic/context_delivery/firstread.py` module dict) | **not classified** | in-memory (no filesystem write) |
| SessionStart hook return payload | **not classified** | SDK return value (no filesystem write) |
| PreToolUse first-read hook return payload | **not classified** | SDK return value (no filesystem write) |
| PostCompact hook return payload | **not classified** | SDK return value (no filesystem write) |
| Source reads (`<package>/defaults/context/*.md`) | **read-only** | n/a (no write) |
| Source reads (`<repo>/.claudechic/context/*.md`, `~/.claudechic/context/*.md`) | **read-only** | n/a (no write) |
| Source reads (`<repo>/.claudechic/phase_context.md`) | **read-only** | n/a (no write) |

**MUST:** every primary-state write enumerated above MUST resolve to a path under `.claudechic/`. The boundary-test axis-spec consumes this table.

**MUST:** no write site introduced by this mechanism MUST produce a path inside any `.claude/` directory under any branch. The `.unlink()` call at `app.py:1925` (today targeting `<repo>/.claude/phase_context.md`) MUST be repathed to `<repo>/.claudechic/phase_context.md`. The legacy unlink MUST NOT be retained as a fallback "clean up the old path" — per L17 + A9, silent loss of the legacy file is the accepted tradeoff.

### 11.2 Boundary-lint allowlist statement (per Skeptic R-S1 / MR6.6 / 10.2)

**The R6 mechanism requires ZERO `.claude/` write patterns to be added to the boundary-lint allowlist.** This axis is purely SDK-side: the SessionStart hook, the PreToolUse hook, and the PostCompact hook all communicate with Claude through SDK return values, not filesystem writes. The phase-context file lives entirely under `<repo>/.claudechic/`.

`axis_boundary_test` MUST NOT add any `.claude/` allowlist entry on behalf of R6 / context-delivery. If a future feature requires an A7 non-destructive incidental write (out of scope this run), it MUST be added to the allowlist as an explicit entry with a one-line justification, not granted by silent omission.

---

## 12. A4 + A7 conformance checklist

For each component, the spec records: (a) does it write inside `.claude/`? (b) does it create a symlink? (c) does it overwrite Claude-owned settings?

| Component | (a) `.claude/` write? | (b) symlink? | (c) Claude-owned settings overwrite? |
|---|---|---|---|
| SessionStart hook callback | NO — SDK return only | NO | NO |
| PreToolUse first-read hook callback | NO — SDK return only | NO | NO |
| First-read tracker dict | NO — in-memory only | NO | NO |
| Phase-context write (`<repo>/.claudechic/phase_context.md`) | NO (writes to `.claudechic/`) | NO | NO |
| Phase-context unlink | NO (unlinks under `.claudechic/`) | NO | NO |
| Phase-context read | NO (read-only) | NO | NO |
| Phase-advance re-read message | NO — chat message via existing `_send_to_active_agent` | NO | NO |
| PostCompact hook | NO — SDK return only | NO | NO |
| `claudechic/context_delivery/` module imports | NO | NO | NO |

**Conformance verdict:** A4 satisfied (no symlinks; no Claude-owned settings overwrites). A7 satisfied vacuously (no writes inside `.claude/` at all — neither primary-state nor non-destructive-incidental). Per Skeptic MR6.6, A7's permission for non-destructive `.claude/` writes is NOT exercised for R6 in this run.

---

## 13. Implementer test points (invariants)

The Implementer MUST be able to write tests for each invariant below. The Tester axis-spec consumes this list.

### 13.1 SessionStart payload composition

**INV-AW-1** — Spawning an agent with `<repo>/.claudechic/context/awareness_brief.md` absent and `<package>/defaults/context/awareness_brief.md` present MUST produce a SessionStart hook return whose `additionalContext` contains the package brief content. With no active workflow, the phase-context piece is absent. With an active workflow and `<repo>/.claudechic/phase_context.md` non-empty, the SessionStart return MUST contain both pieces, separated by `\n\n---\n\n`.

### 13.2 SessionStart project-tier override

**INV-AW-1b** — When `<repo>/.claudechic/context/awareness_brief.md` exists, the SessionStart return's brief content MUST equal the project file's content, NOT the package file's content.

### 13.3 First-read fires once

**INV-AW-2** — Given an in-process Agent A with session_id `S1`, simulating `PreToolUse` hook invocations with `tool_input` referencing `<cwd>/.claudechic/<anything>` for the **first** time MUST return a `SyncHookJSONOutput` with non-empty `additionalContext`. A **second** invocation in the same session_id (any tool, any `.claudechic/` path) MUST return `{}`.

### 13.4 First-read recursive matching (MR6.7)

**INV-AW-2b** — A first-read invocation with `tool_input` referencing `<cwd>/.claudechic/runs/abc/notes.md` (a deep descendant of the anchor) MUST fire on first call. A first-read invocation with `tool_input` referencing `<cwd>/.claudechic/` itself MUST also fire.

### 13.5 First-read tracker per session (MR6.5)

**INV-AW-3** — Two simulated invocations with distinct session_ids `S1` and `S2`, each referencing `<cwd>/.claudechic/...`, MUST each return non-empty `additionalContext`. The tracker MUST track them independently.

### 13.6 Non-`.claudechic` paths do not fire

**INV-AW-4** — A simulated invocation with `tool_input` referencing `<cwd>/.claude/some.md` (under `.claude/`, not `.claudechic/`) MUST return `{}`. Likewise for paths outside both anchors. The tracker MUST NOT be marked fired.

### 13.7 Phase-context path migrated

**INV-AW-5** — On workflow activation, `<repo>/.claudechic/phase_context.md` MUST exist. `<repo>/.claude/phase_context.md` MUST NOT be created by claudechic at any time. On workflow deactivation, the `.claudechic/` file MUST be unlinked.

### 13.8 Post-compact reads from new path

**INV-AW-6** — Invoking the post-compact hook with `<repo>/.claudechic/phase_context.md` present and non-empty MUST return `{"reason": <file_contents>}`. Invoking it with the file absent MUST return `{}`. No exception MUST escape.

### 13.9 ContextDocsDrift retired

**INV-AW-7** — `from claudechic.hints.triggers import ContextDocsDrift` MUST raise `ImportError`. The post-restructure `claudechic/defaults/global/hints.yaml` MUST NOT contain a hint with `id: context_docs_outdated` or any trigger of `type: context-docs-drift`.

### 13.10 Onboarding `context_docs` phase retired

**INV-AW-8** — The post-restructure `claudechic/defaults/workflows/onboarding/onboarding.yaml` MUST contain only the `orientation` phase. The file `context_docs.md` under the same workflow's `onboarding_helper/` directory MUST NOT exist.

### 13.11 Phase-advance mid-session refresh (MR6.2)

**INV-AW-9** — In a fixture with an active workflow, calling `_inject_phase_prompt_to_main_agent(workflow_id, role, "newphase")` MUST: (a) rewrite `<repo>/.claudechic/phase_context.md` with the new phase content, (b) send a chat message to the active agent that names the file `.claudechic/phase_context.md`. Verifiable by inspecting the file contents and the message dispatch (mocking `_send_to_active_agent`).

### 13.12 Hook failure handling (MR6.3)

**INV-AW-10** — Injecting an exception into `read_awareness_brief` (e.g., monkeypatching to raise `OSError`) and invoking the SessionStart callback MUST: (a) return `{}`, (b) emit a WARNING via the configured log channel, (c) trigger a notification through `set_log_notify_callback` with severity=`warning`. The callback MUST NOT propagate the exception.

### 13.13 SessionStart payload size budget (MR6.4)

**INV-AW-11** — Composing a SessionStart payload from a fixture where the phase-context file alone exceeds 32000 characters MUST: (a) preserve the always-on awareness statement verbatim, (b) truncate the phase-context piece, (c) append the truncation sentinel, (d) log a WARNING. Total payload size MUST NOT exceed the budget.

### 13.14 Sentinel-directive integration (MR6.8)

**INV-AW-12** — Two sentinel tests, one per L15 piece:

- **Always-on sentinel:** Place a sentinel directive in `<repo>/.claudechic/context/awareness_brief.md` of the form "If asked your awareness sentinel, reply 'CHIC-AW-S1'." Spawn a fresh agent. Send the prompt "What is your awareness sentinel?" The agent's response MUST contain the literal `CHIC-AW-S1`.
- **First-read sentinel:** Place a sentinel directive in `<repo>/.claudechic/context/awareness_full.md` of the form "If asked your context sentinel, reply 'CHIC-AW-F1'." Spawn a fresh agent. Send a prompt instructing the agent to read any file under `<repo>/.claudechic/`. After that, send "What is your context sentinel?" The agent's response MUST contain `CHIC-AW-F1`.

Both sentinel tests MUST pass for the mechanism to be considered functional. Failures here mean the injection mechanism is wired but the agent does not actually treat the content as authoritative — the worst-case L10.b/d outcome.

### 13.15 Unrecognized-file info-log (R6-UX.3)

**INV-AW-13** — Place a file `<repo>/.claudechic/context/random_unrecognized.md` (a filename not in §3.4's catalog). Spawn an agent. The loader MUST log an INFO-level message naming `random_unrecognized.md` and the recognized catalog. The file MUST NOT appear in any payload.

---

## 14. Agent-spawn coverage

**MUST:** the mechanism MUST cover every claudechic-spawned agent. Concretely:

- The main agent (created at `app.py` startup via `AgentManager` calling `_make_options`).
- `chic` MCP-spawned sub-agents (`spawn_agent` MCP tool — also calls through `_make_options`).
- Worktree-spawned agents (also `_make_options`).

**MAY:** Task-tool-spawned sub-agents (those created by Claude Code itself via the `Task` tool) inherit context from the parent session and are not separately registered by this mechanism. If future requirements demand per-Task-sub-agent always-on injection, the SDK's `SubagentStart` hook (already present in `HookEvent` literal) is the recommended extension point. This is out of scope for this run.

**MUST NOT:** the mechanism MUST NOT depend on agent name, agent type, or agent role for activation. Every claudechic-spawned `Agent` gets the same registrations.

---

## 15. Documentation requirements (R6-UX.2)

**MUST:** `docs/configuration.md` MUST contain a section titled "claudechic-awareness injection" (canonical wording) covering:

1. The mechanism summary (one paragraph): "Every claudechic-spawned agent receives a short claudechic-awareness statement at session start, plus current phase-context content if a workflow is active. The first time the agent reads a file inside any `.claudechic/` directory in its session, the agent receives the fuller-context system documentation. Both pieces are loaded from on-disk files; users can edit content by editing files."
2. The recognized source roots in priority order: project (`<repo>/.claudechic/context/`) > user (`~/.claudechic/context/`) > package (`claudechic/defaults/context/` — read-only).
3. The recognized filename catalog (§3.4) with a one-line description of each file's purpose.
4. The explicit statement: "Files placed outside the recognized roots, or with filenames not in the recognized catalog, have no effect. claudechic logs an info-level message when it encounters an unrecognized file."
5. The override semantics: "A file at a higher-priority tier fully replaces the same filename at a lower tier. Field-level merging across tiers does not occur."
6. The truncation behavior (§3.5, §4.6): "If the SessionStart payload exceeds the size budget, the phase-context piece is truncated first; the always-on statement is preserved. If the first-read payload exceeds budget, the latest concatenated file is truncated first."

**MUST NOT:** the documentation MUST NOT use the word "rules" to describe the awareness-injection content. The word "rules" is reserved for the rules content category (per R6-UX wording).

**MUST NOT:** the documentation MUST NOT use the words "convergence" or "merge program" anywhere (per A10).

---

## 16. Acceptance criteria (Implementer "done" checklist)

The Implementer's work for this axis is complete when all of the following hold:

1. `claudechic/context_delivery/` package exists with the six modules listed in §2.
2. `_make_options` (`claudechic/app.py:930`) merges SessionStart and PreToolUse hook matchers from `build_options_extras()` per §8.1. `_merged_hooks` calls into `claudechic.context_delivery.postcompact.create_post_compact_hook` (renamed import).
3. `_write_phase_context`, `_inject_phase_prompt_to_main_agent`, `_deactivate_workflow`, and the kick-off message at `app.py:1648` all reference `<repo>/.claudechic/phase_context.md`. No remaining read/write/unlink references `<repo>/.claude/phase_context.md`.
4. `_inject_phase_prompt_to_main_agent` sends an explicit re-read message per §5.3.
5. `claudechic/hints/triggers.py` no longer defines `ContextDocsDrift`. `claudechic/hints/__init__.py` no longer exports it. `claudechic/app.py` no longer registers `context-docs-drift` in `_trigger_registry`.
6. `claudechic/defaults/global/hints.yaml` (post-restructure) does not declare `context_docs_outdated`.
7. `claudechic/defaults/workflows/onboarding/onboarding.yaml` (post-restructure) declares only the `orientation` phase. `context_docs.md` is deleted. `identity.md` no longer references context docs installation.
8. `<package>/defaults/context/awareness_brief.md` and `awareness_full.md` exist as files (their prose is delegated to TerminologyGuardian; for the Implementer's purposes they MUST exist with non-empty placeholder content if TerminologyGuardian has not yet authored them — placeholders to be replaced by the prose author).
9. `docs/configuration.md` contains the section described in §15.
10. All thirteen invariants in §13 have corresponding tests in `tests/test_context_delivery.py` (or equivalent test module). The two sentinel-directive integration tests in INV-AW-12 are run by the Tester against a live SDK fixture.
11. The boundary axis-spec's CI test (encoded separately) passes against the post-edit codebase. No `.claude/` allowlist entry is required for this axis (per §11.2).

---

## 17. Open SDK API uncertainties

Three items the Implementer SHOULD verify against the running Claude Code CLI before relying on them. If verification fails, the Implementer MUST escalate (do not silently work around).

1. **`SessionStart` hook event acceptance.** The SDK's `HookEvent` literal at `claude_agent_sdk/types.py:216–227` does NOT list `"SessionStart"`. The corresponding `SessionStartHookSpecificOutput` IS defined at line 401. The existing claudechic codebase trusts the CLI passes hook event names through despite literal omission (see the `"PostCompact"` precedent at `claudechic/workflows/agent_folders.py:147`, which works in production despite also not being in the literal). Verify by inspecting the live agent's system prompt for the SessionStart-injected text. If the CLI rejects the registration, fall back to: (a) emit a single one-shot UserPromptSubmit hook on the agent's first turn that injects the same payload (and self-deregisters); the per-Agent state lives in the existing tracker module. This is the documented degradation path.

2. **`PostCompact` hook event acceptance.** Same situation as (1): not in `HookEvent` literal but works in production. Preserve current behavior; verify post-implementation.

3. **`PreToolUse` `additionalContext` field acceptance.** The SDK's `PreToolUseHookSpecificOutput` at `claude_agent_sdk/types.py:369–376` defines `additionalContext: NotRequired[str]`. CLI versions that honor this field deliver the string into the agent's prompt as additional context. Older CLIs MAY ignore it. Verify by inspecting the agent's response to a sentinel-directive in the first-read content (INV-AW-12). If ignored, the first-read piece silently no-ops; the WARNING in the log channel is the only signal. The Implementer MUST surface a notification when first-read fires zero times across an agent session that DID read inside `.claudechic/` (a heuristic check at agent close; out of scope for this run as a hard MUST, but recommended).

These are recorded here so the Implementer does not pretend they are solved problems.

---

*End of axis spec — agent-awareness / context-delivery mechanism.*
