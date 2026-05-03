---
paths:
  - claudechic/agent.py
  - claudechic/agent_manager.py
  - claudechic/protocols.py
  - claudechic/mcp.py
---

# Multi-Agent Architecture

claudechic supports multiple concurrent Claude agents, each with its own SDK connection, chat history, and working directory. The architecture uses a single source of truth pattern with `AgentManager` coordinating agents and `Agent` owning per-agent state.

## Core Classes

### Agent (`agent.py`)

The `Agent` class owns everything for a single Claude agent:

- **Identity:** `id` (UUID prefix), `name`, `cwd`, optional `worktree` branch
- **SDK connection:** `client` (ClaudeSDKClient), `session_id` for resume
- **Status:** `"idle"` | `"busy"` | `"needs_input"`
- **Chat history:** `messages` list of `ChatItem` (user/assistant messages with tool uses)
- **Tool tracking:** `pending_tools` (awaiting results), `active_tasks` (accumulated text)
- **UI widgets:** `chat_view`, `current_response`, `pending_tool_widgets`, `active_task_widgets`
- **Per-agent state:** `todos`, `auto_approve_edits`, `file_index`, `pending_images`
- **Runtime role:** `agent_type: str` (default `"default"`) -- queryable role identity. Promoted to the workflow's `main_role` on activation, reverted on deactivation, survives `/compact`.
- **Effort:** `effort: Literal["low", "medium", "high", "max"]` -- per-agent thinking budget passed to the SDK on every `_make_options()` call. `"max"` is Opus-only; switching to a non-Opus model snaps effort to `"medium"` automatically. Displayed and cycled via the `EffortLabel` widget in the status footer.

Key methods: `connect()`, `send()`, `wait_for_completion()`, `interrupt()`.

### AgentManager (`agent_manager.py`)

Single source of truth for all agent state. Coordinates lifecycle and switching.

- `agents: dict[str, Agent]` -- all agents by ID
- `active_id: str | None` -- currently active agent

Key methods: `create()`, `create_unconnected()`, `switch()`, `close()`, `get()`.

When agents are created, AgentManager wires shared observers (`agent_observer`, `permission_handler`) onto the new Agent instance.

### ChatApp (`app.py`)

Thin UI layer. Properties like `agents` and `active_agent_id` delegate to AgentManager. ChatApp implements the observer protocols to update the UI in response to agent events.

## Observer Protocols (`protocols.py`)

### AgentObserver

Emitted by Agent, consumed by ChatApp for UI updates:

- `on_status_changed` -- agent idle/busy/needs_input
- `on_text_chunk` -- streaming text from assistant
- `on_tool_use` / `on_tool_result` -- tool lifecycle
- `on_complete` -- response finished
- `on_error` -- error occurred
- `on_todos_updated` -- todo list changed
- `on_prompt_added` -- permission request needs UI
- `on_prompt_sent` -- user prompt dispatched

### AgentManagerObserver

Emitted by AgentManager:

- `on_agent_created` -- new agent added
- `on_agent_switched` -- active agent changed
- `on_agent_closed` -- agent removed

### PermissionHandler

Async callback: `(agent, request) -> "allow" | "deny" | "allow_all"`.

## Message Flow

**Sending:** User types -> `ChatInput.Submitted` -> mount user message -> `asyncio.create_task(agent.send(prompt))`.

**Receiving:** `Agent._process_response()` processes SDK stream -> calls `observer.on_text_chunk()` -> ChatApp updates UI directly (no message queue).

**Switching:** User clicks agent in sidebar or presses Ctrl+1-9 -> `AgentManager.switch()` -> hide old agent's `chat_view`, show new agent's `chat_view`, update sidebar/footer.

## Agent Creation Patterns

1. **Initial agent (on_mount):** `create_unconnected()` synchronously so UI is ready, then connect in a background worker.
2. **Via /agent command:** `await agent_mgr.create(name, cwd, switch_to=True)` -- creates, wires, connects, switches in one call.
3. **Via MCP spawn_agent:** `await agent_mgr.create(name, cwd, switch_to=False)` -- creates without switching, optionally sends initial prompt.

## Key Design Decisions

1. **Single source of truth:** `AgentManager.agents` is the authoritative dict. `ChatApp.agents` is a read-through property.
2. **Agent owns SDK lifecycle:** `Agent.connect()`, `Agent.send()`, `Agent.disconnect()` -- not ChatApp.
3. **Callbacks for UI:** Agent emits events via observer protocols. No direct widget manipulation in Agent.
4. **UI widgets on Agent:** Agent stores references to its widgets for fast access without lookups.
5. **True async concurrency:** Agents run via `asyncio.create_task()`, not Textual workers, enabling concurrent execution.
6. **Live option reads:** `_make_options(agent=)` reads `agent.agent_type` and `agent.effort` on every call (no snapshot). The `CLAUDE_AGENT_ROLE` env var is propagated to the model process on each reconnect.

## Inter-Agent Communication (MCP Tools)

- **`message_agent`** -- Send a message to another agent. By default expects a reply (target is nudged if idle without responding). Set `requires_answer=false` for fire-and-forget messages (status updates, results, answering questions).
- **`interrupt_agent`** -- Interrupt an agent's current task immediately. Optionally redirect with a new prompt. Use when you need to stop or redirect a busy agent in real-time.

**When to use which:**
- Need a response? Use `message_agent` (default: `requires_answer=true`).
- Sending info, no reply needed? Use `message_agent` with `requires_answer=false`.
- Need to stop/redirect NOW? Use `interrupt_agent` (cuts through immediately).

## Commands

- `/agent` -- list all agents
- `/agent <name> [path]` -- create new agent
- `/agent close [name]` -- close agent
- `Ctrl+1-9` -- switch to agent by position
