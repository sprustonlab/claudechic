# JSONL Forensic Analysis -- Harness Reminders

**Scope.** 9 Claude Code session transcripts (JSONL, one event per line) for a multi-agent claudechic run on 2026-05-01 / 2026-05-02. Files read with `grep` / line-counting / targeted `sed` / `python3` line-by-line JSON parse. No file was too large to enumerate in full.

**Key structural finding (overrides naive string searches).** The literal strings `## Auto Mode Active`, `Auto mode is active`, and `TodoWrite tool hasn't been used recently` do NOT appear in the JSONL transcript files as harness-injected content. Searching for them by `grep` finds them only inside ASSISTANT-authored discussion turns or inside the prompt body of an `Agent` tool-call (e.g., the prompt that launched this very forensic task quoted those strings).

The actual harness-injection mechanism is recorded as standalone JSONL events of `type: "attachment"` with `attachment.type: "auto_mode"` and `attachment.type: "todo_reminder"`. These events store ONLY a marker (`reminderType`, `itemCount`, `content`) -- the full reminder text is materialized by the harness elsewhere when serializing the conversation to the model. So the proper unit of analysis is the attachment event count, not the string count. This report uses both.

---

## Q1. Auto-mode reminder

### String-occurrence counts (literal `## Auto Mode Active` / `Auto mode is active`)

| Agent (role) | session | `## Auto Mode Active` | `Auto mode is active` |
|---|---|---:|---:|
| coordinator | 7cda1c83 | 3 | 1 |
| composability | 1d5568eb | 0 | 0 |
| skeptic | 93cfa471 | 0 | 0 |
| terminology | 73554ac4 | 0 | 0 |
| user_alignment | 0bd46d13 | 0 | 0 |
| time_axis | 84e11e26 | 0 | 0 |
| place_axis | 901195fa | 0 | 0 |
| role_axis | dcde9f2d | 0 | 0 |
| gating_axis | 15036b5b | 0 | 0 |

### Coordinator string-occurrence locations

| Line | Role | What it actually is |
|---|---|---|
| 610 | `assistant` (text) | Coordinator explaining Auto mode to user. Excerpt: `"You've seen the reminder appear several times in this session as <system-reminder> blocks beginning with ## Auto Mode Active."` |
| 616 | `assistant` (text) | Coordinator partially walking back the previous claim. Excerpt: `"Looking back at this session, the full ## Auto Mode Active block appeared maybe 5–6 times across a much longer conversation."` |
| 666 | `assistant` (`tool_use` `name=Agent`) | Tool call launching the forensic task. The literal strings appear inside the `prompt` argument because this report's brief quoted them as search targets. |

None of these are harness-injected reminders. They are assistant-authored mentions of the strings.

### Authoritative count: `auto_mode` attachment events

These are the actual harness injection markers. JSON path: `event.type == "attachment"` and `event.attachment.type == "auto_mode"`. Payload keys: `type`, `reminderType` (`"full"` or `"sparse"`).

| Agent | session | total auto_mode | full | sparse |
|---|---|---:|---:|---:|
| coordinator | 7cda1c83 | 12 | 3 | 9 |
| composability | 1d5568eb | 3 | 1 | 2 |
| skeptic | 93cfa471 | 1 | 1 | 0 |
| terminology | 73554ac4 | 3 | 1 | 2 |
| user_alignment | 0bd46d13 | 1 | 1 | 0 |
| time_axis | 84e11e26 | 2 | 1 | 1 |
| place_axis | 901195fa | 2 | 1 | 1 |
| role_axis | dcde9f2d | 2 | 1 | 1 |
| gating_axis | 15036b5b | 2 | 1 | 1 |

**Every agent receives exactly one `reminderType: "full"` injection.** Beyond that, additional injections are `"sparse"` and vary by session length. Agents with shorter transcripts (skeptic 163 lines, user_alignment 89 lines) receive only the single full injection; longer transcripts receive incremental sparse injections.

### Coordinator: per-injection event-index gap and wall-clock gap

| # | line | timestamp (UTC) | reminderType | gap_idx (lines since prev) | gap_sec (since prev) |
|---|---:|---|---|---:|---:|
| 1 | 7   | 2026-05-01T21:42:31.072Z | full   | -    | -       |
| 2 | 54  | 2026-05-01T23:36:24.677Z | sparse | 47   | 6833.6  |
| 3 | 154 | 2026-05-01T23:46:29.003Z | sparse | 100  | 604.3   |
| 4 | 230 | 2026-05-01T23:52:08.960Z | sparse | 76   | 340.0   |
| 5 | 281 | 2026-05-01T23:54:36.204Z | sparse | 51   | 147.2   |
| 6 | 323 | 2026-05-01T23:56:53.380Z | full   | 42   | 137.2   |
| 7 | 368 | 2026-05-02T00:00:43.026Z | sparse | 45   | 229.6   |
| 8 | 424 | 2026-05-02T00:05:52.760Z | sparse | 56   | 309.7   |
| 9 | 482 | 2026-05-02T00:06:18.921Z | sparse | 58   | 26.2    |
| 10| 528 | 2026-05-02T00:17:52.633Z | sparse | 46   | 693.7   |
| 11| 589 | 2026-05-02T00:24:19.186Z | full   | 61   | 386.6   |
| 12| 636 | 2026-05-02T00:29:46.913Z | sparse | 47   | 327.7   |

Pattern observable in evidence: line-index gaps cluster in the 42-100 range; wall-clock gaps cluster in 130-700 sec range, with two outliers (a 6833 sec idle period between #1 and #2, and a 26 sec rapid re-injection between #8 and #9). The `"full"` variant fires at indices 1, 6, 11 -- approximately every 5th injection -- but `[NO EVIDENCE]` of any deterministic counter inside the JSONL events themselves.

---

## Q2. TodoWrite reminder

### String-occurrence counts (literal `TodoWrite tool hasn't been used recently`)

| Agent | session | string count |
|---|---|---:|
| coordinator | 7cda1c83 | 1 (line 666 only -- inside Agent tool prompt, see Q1 note) |
| all 8 other agents | -- | 0 |

### Authoritative count: `todo_reminder` attachment events

JSON path: `event.type == "attachment"` and `event.attachment.type == "todo_reminder"`. Payload keys: `type`, `content` (list of todos), `itemCount`.

| Agent | session | todo_reminder count |
|---|---|---:|
| coordinator | 7cda1c83 | 14 |
| composability | 1d5568eb | 9 |
| skeptic | 93cfa471 | 5 |
| terminology | 73554ac4 | 10 |
| user_alignment | 0bd46d13 | 2 |
| time_axis | 84e11e26 | 6 |
| place_axis | 901195fa | 11 |
| role_axis | dcde9f2d | 9 |
| gating_axis | 15036b5b | 5 |

### Coordinator: per-injection table

| # | line | timestamp (UTC) | itemCount | gap_idx | gap_sec |
|---|---:|---|---:|---:|---:|
| 1 | 61  | 2026-05-01T23:38:10.609Z | 0 | -  | -      |
| 2 | 95  | 2026-05-01T23:42:13.989Z | 7 | 34 | 243.4  |
| 3 | 123 | 2026-05-01T23:45:00.425Z | 7 | 28 | 166.4  |
| 4 | 195 | 2026-05-01T23:50:47.141Z | 7 | 72 | 346.7  |
| 5 | 231 | 2026-05-01T23:52:08.960Z | 7 | 36 | 81.8   |
| 6 | 273 | 2026-05-01T23:54:13.740Z | 7 | 42 | 124.8  |
| 7 | 328 | 2026-05-01T23:57:00.937Z | 7 | 55 | 167.2  |
| 8 | 372 | 2026-05-02T00:00:46.957Z | 7 | 44 | 226.0  |
| 9 | 411 | 2026-05-02T00:05:05.102Z | 7 | 39 | 258.1  |
| 10| 498 | 2026-05-02T00:06:46.672Z | 7 | 87 | 101.6  |
| 11| 550 | 2026-05-02T00:18:42.798Z | 7 | 52 | 716.1  |
| 12| 590 | 2026-05-02T00:24:19.186Z | 7 | 40 | 336.4  |
| 13| 631 | 2026-05-02T00:29:39.400Z | 7 | 41 | 320.2  |
| 14| 662 | 2026-05-02T00:30:36.903Z | 7 | 31 | 57.5   |

The first injection (line 61) carries `itemCount: 0` (empty list); all subsequent carry `itemCount: 7`. `[NO EVIDENCE]` in the transcript of what changed at line 61 to flip the state, since only the marker is recorded, not the rendered text.

### Coordinator: preceding-event types for `todo_reminder`

Aggregate counter (using a python pass over `events[ln-2]`):

| Preceding event type | count |
|---|---:|
| user / tool_result | 7 |
| user / text         | 4 |
| attachment           | 3 |

---

## Q3. What injects them?

These reminders are NOT `<system-reminder>` blocks inside `user` content arrays. They are stored as their own JSONL events, ONE event per injection. JSON shape:

```json
{
  "parentUuid": "...",
  "isSidechain": false,
  "attachment": {"type": "auto_mode", "reminderType": "full"},
  "type": "attachment",
  "uuid": "...",
  "timestamp": "...",
  "userType": "external",
  "entrypoint": "sdk-py",
  "cwd": "...",
  "sessionId": "...",
  "version": "2.1.119",
  "gitBranch": "..."
}
```

JSON key path of the discriminator: `event.type` == `"attachment"`, then `event.attachment.type`. The reminder *body text* (e.g. the markdown that begins with `## Auto Mode Active`) is NOT present in the JSONL event -- only the marker fields:

- `auto_mode`: `attachment.reminderType` (`"full"` or `"sparse"`)
- `todo_reminder`: `attachment.content` (list) + `attachment.itemCount` (int)

The full text body must be re-materialized by the harness from these markers when constructing the model context. `[NO EVIDENCE]` in the transcripts of where that materialization happens.

There is no `system` role event for these injections, and there are no `<system-reminder>` substrings in any user-content payloads in the 9 files (the only matches for that string are inside the Agent-tool prompt at line 666 of the coordinator, which quotes it as a search target).

---

## Q4. Differences across agents

| Agent (role)    | session  | auto_mode (full / sparse) | todo_reminder | transcript lines |
|---|---|---|---:|---:|
| coordinator     | 7cda1c83 | 12 (3 / 9) | 14 | 666 |
| composability   | 1d5568eb | 3 (1 / 2)  |  9 | 316 |
| skeptic         | 93cfa471 | 1 (1 / 0)  |  5 | 163 |
| terminology     | 73554ac4 | 3 (1 / 2)  | 10 | 320 |
| user_alignment  | 0bd46d13 | 1 (1 / 0)  |  2 |  89 |
| time_axis       | 84e11e26 | 2 (1 / 1)  |  6 | 198 |
| place_axis      | 901195fa | 2 (1 / 1)  | 11 | 333 |
| role_axis       | dcde9f2d | 2 (1 / 1)  |  9 | 285 |
| gating_axis     | 15036b5b | 2 (1 / 1)  |  5 | 189 |

**All 9 agents receive the auto-mode reminder** -- every transcript contains at least one `auto_mode` attachment event (always exactly one `"full"` variant; `"sparse"` variants accumulate in longer sessions). **All 9 agents receive todo_reminder events** as well; counts scale roughly with transcript length but not perfectly (e.g. place_axis at 333 lines has 11 reminders, terminology at 320 lines has 10, while role_axis at 285 lines has 9).

---

## Q5. Other harness-injected reminders

The 9 transcripts contain the following `attachment.type` values across all events. Counts are per-agent.

| attachment.type           | coord | comp | skep | term | user_align | time | place | role | gate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `auto_mode`               | 12 | 3 | 1 | 3 | 1 | 2 | 2 | 2 | 2 |
| `todo_reminder`           | 14 | 9 | 5 |10 | 2 | 6 |11 | 9 | 5 |
| `skill_listing`           |  1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `nested_memory`           |  1 | 2 | 2 | 2 | 1 | 3 | 3 | 2 | 2 |
| `mcp_instructions_delta`  |  1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `deferred_tools_delta`    |  1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `edited_text_file`        |  0 | 0 | 1 | 0 | 0 | 0 | 1 | 0 | 0 |
| `hook_blocking_error`     |  0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |

Sample payloads (truncated, first 80 chars where applicable):

- `skill_listing`: keys `[type, content, skillCount, isInitial]`. Initial content begins: `"- update-config: Use this skill to configure the Claude Code harness via setting"`. `skillCount: 10`.
- `nested_memory`: keys `[type, path, content, displayPath]`. Each event references a `~/.claude/rules/claudechic_*.md` doc; example `displayPath: "../.claude/rules/claudechic_claudechic-overview.md"`.
- `mcp_instructions_delta`: keys `[type, addedNames, addedBlocks, removedNames]`. In every agent: `addedNames: ["claude.ai bioRxiv"]` with a multi-paragraph block describing bioRxiv tool selection.
- `deferred_tools_delta`: keys `[type, addedNames, addedLines, removedNames]`. Lists ~110 deferred tool names (Cron*, Worktree, mcp__chic__*, mcp__claude_ai_*).
- `edited_text_file`: present only in skeptic (1) and place_axis (1). `[NO EVIDENCE]` of payload contents inspected here beyond confirming presence.
- `hook_blocking_error`: present only in role_axis (1). `[NO EVIDENCE]` of payload contents inspected here beyond confirming presence.

`<system-reminder>` literal substrings: 0 occurrences in any user-content payload across all 9 files. The only matches in the entire 9-file corpus are the 3 inside the coordinator's lines 610 and 666 (assistant text and Agent-tool prompt body, respectively).

---

## Q6. Cross-references with workflow events (coordinator only)

For each `auto_mode` injection, the immediately-preceding event (line N-1):

| # | auto_mode line | prev line | prev type / role | prev content snippet (chars 0-120) |
|---|---:|---:|---|---|
| 1 | 7   | 6   | attachment / `skill_listing`     | (initial skill listing during session bootstrap) |
| 2 | 54  | 53  | user / user (text)               | `"I don't think it is needed. We just want to tighten the workflow..."` (user typed prompt) |
| 3 | 154 | 153 | user / user (text)               | `"[Message from agent 'skeptic']"` -- inter-agent message via `mcp__chic__message_agent` |
| 4 | 230 | 229 | user / user (`tool_result`)      | `"→ composability: Update: I already spawned all four axis-agents..."` -- result of an `mcp__chic__message_agent` send |
| 5 | 281 | 280 | user / user (text)               | `"[Message from agent 'gating_axis']"` -- inter-agent message |
| 6 | 323 | 322 | user / user (text)               | `"[Message from agent 'composability']"` -- inter-agent message |
| 7 | 368 | 367 | user / user (`tool_result`)      | `"→ skeptic: Composability's integration pass flagged that..."` |
| 8 | 424 | 423 | user / user (text)               | `"[Message from agent 'place_axis']"` -- inter-agent message |
| 9 | 482 | 481 | user / user (`tool_result` / `tool_reference`) | `tool_use_id: toolu_012dUAqP3xqHmh3ut2Ccc5Uh` referencing `mcp__chic__interrupt_agent` |
| 10| 528 | 527 | user / user (text)               | `"did agents review not when asked? why is this added?..."` (user typed prompt) |
| 11| 589 | 588 | user / user (text)               | `"[Message from agent 'composability']  meta reply on disk at..."` |
| 12| 636 | 635 | user / user (`tool_result`)      | `"# Agent: claudechic ## Identity ..."` -- result of `mcp__chic__whoami` |

**Observations from evidence:**

- 11 of 12 auto_mode injections in the coordinator are immediately preceded by a `user` event. The single exception (#1) is preceded by a `skill_listing` attachment at the very start of the session.
- The injection ALWAYS sits at the boundary BEFORE the model's next assistant turn -- never mid-tool-result-stream.
- Of the 152 total user events in the coordinator file, only 12 (~7.9%) are followed by an auto_mode attachment. So it is NOT per-user-event.
- Of the 60 distinct `promptId` values in the coordinator, only 12 trigger an auto_mode injection. Whether the triggering user event is the FIRST occurrence of its promptId is mixed: 6 of 11 inspected cases are first-occurrence, 5 are not. So it is NOT strictly per-new-prompt.
- `[NO EVIDENCE]` in the JSONL of an explicit timer field, turn counter, or rule that selects which user events get an injection. Wall-clock gaps range 26 sec to 6833 sec; line-index gaps range 42 to 100 (excluding the bootstrap event). The `"full"` variant appears at injections #1, #6, #11 (every 5th).
- Phase advances: `[NO EVIDENCE]` examined here. The transcript does not contain explicit phase-advance markers in the events I sampled; advances happen via `mcp__chic__advance_phase` tool calls but I did not correlate those tool-call line numbers to the auto_mode injection lines in this pass.
- Permission prompts: `[NO EVIDENCE]` of explicit permission-prompt event types in the coordinator transcript that I observed during this analysis.
- Agent spawns: spawns happen via `mcp__chic__spawn_agent` / Task tool calls; `[NO EVIDENCE]` of a 1:1 correlation with auto_mode injections (the inter-agent `[Message from agent ...]` events that precede injections #3, #5, #6, #8, #11 are inbound messages from already-spawned agents, not spawns).

---

## Sampling and method notes

- Files were read end-to-end; no truncation or sampling was used to obtain counts.
- All counts derived from `grep -c` on the literal JSON marker substrings (e.g. `'"attachment":{"type":"auto_mode"'`), cross-checked with a `python3` line-by-line `json.loads` pass for the coordinator file.
- Line numbers in this report are 1-based, matching `sed -n 'Np'` and `grep -n` conventions.
- Timestamps are taken verbatim from the events' `"timestamp"` field (RFC3339 UTC).
- No JSONL line was modified; this is read-only forensics.
