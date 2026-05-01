# claudechic

A stylish terminal UI for Claude Code, built with Textual and wrapping the `claude-agent-sdk`.

## Run

```bash
uv run claudechic
uv run claudechic --resume     # Resume most recent session
uv run claudechic -s <uuid>    # Resume specific session
```

Requires Claude Code to be logged in with a Max/Pro subscription (`claude /login`).

## Development

```bash
uv sync --dev                  # Install all dependencies
source .venv/bin/activate      # Activate venv (Linux/macOS)
claudechic                     # Run after activation
```

## Commands

```bash
pytest tests/test_foo.py -v --timeout=30   # Run specific test (preferred)
TS=$(date -u +%Y-%m-%d_%H%M%S) && pytest --junitxml=.test_results/${TS}.xml --tb=short --timeout=30 2>&1 | tee .test_results/${TS}.log  # Full suite with output capture
ruff check --fix && ruff format            # Lint + format
```

## File Map

```
claudechic/
├── __init__.py        # Package entry, exports ChatApp
├── __main__.py        # CLI entry point
├── agent.py           # Agent class - SDK connection, history, permissions, state
├── analytics.py       # PostHog analytics - fire-and-forget event tracking
├── agent_manager.py   # AgentManager - coordinates multiple concurrent agents
├── app.py             # ChatApp - main application, event handlers
├── awareness_install.py # claudechic-awareness install routine (~/.claude/rules/claudechic_*.md)
├── commands.py        # Slash command routing (/agent, /shell, /clear, etc.)
├── compact.py         # Session compaction - shrink old tool uses to save context
├── config.py          # CONFIG (user-tier) + ProjectConfig (project-tier) loading
├── errors.py          # Logging infrastructure, error handling
├── file_index.py      # Fuzzy file search using git ls-files
├── formatting.py      # Tool formatting, diff rendering (pure functions)
├── history.py         # Global history loading from ~/.claude/history.jsonl
├── mcp.py             # In-process MCP server for agent control tools
├── messages.py        # Custom Textual Message types for SDK events
├── remote.py          # HTTP server for remote control (live testing)
├── permissions.py     # PermissionRequest dataclass for tool approval
├── profiling.py       # Lightweight profiling utilities (@profile decorator)
├── sampling.py        # CPU-conditional sampling profiler for high-CPU investigation
├── protocols.py       # Observer protocols (AgentObserver, AgentManagerObserver)
├── sessions.py        # Session file loading and listing (pure functions)
├── styles.tcss        # Textual CSS - visual styling
├── theme.py           # Textual theme definition
├── usage.py           # OAuth usage API fetching (rate limits)
├── features/
│   ├── __init__.py    # Feature module exports
│   └── worktree/
│       ├── __init__.py   # Public API (list_worktrees, handle_worktree_command)
│       ├── commands.py   # /worktree command handlers
│       └── git.py        # Git worktree operations
├── workflows/   # Workflow orchestration ENGINE (Python code)
│   ├── __init__.py    # Parser registration, public API
│   ├── engine.py      # WorkflowEngine - phase state, advance checks, artifact_dir
│   ├── loader.py      # ManifestLoader - 3-tier walk (package/user/project) + override resolution
│   ├── parsers.py     # Section parsers for rules, hints, phases, etc.
│   ├── phases.py      # Phase type, PhasesParser
│   └── agent_folders.py # Agent prompt assembly from workflow role dirs
├── checks/            # Check protocol (LEAF: stdlib only)
├── guardrails/        # Guardrail rules (LEAF: no upward imports)
├── hints/             # Hints pipeline (LEAF: stdlib only, no upward imports)
│   ├── __init__.py    # Package marker
│   ├── engine.py      # 6-stage hint evaluation pipeline
│   ├── parsers.py     # Manifest section parser for hints YAML
│   ├── state.py       # HintStateStore - persistence to .claudechic/hints_state.json
│   └── types.py       # HintSpec, HintDecl, HintRecord, HintLifecycle, TriggerCondition
├── defaults/          # Bundled package-tier content (data, not Python)
│   ├── global/        # Always-active manifests
│   │   ├── rules.yaml # Guardrail rules
│   │   └── hints.yaml # Hint definitions
│   ├── workflows/     # Bundled workflow YAML directories (9 workflows)
│   │   ├── audit/
│   │   ├── cluster_setup/
│   │   ├── codebase_setup/
│   │   ├── git_setup/
│   │   ├── onboarding/
│   │   ├── project_team/
│   │   ├── tutorial/
│   │   ├── tutorial_extending/
│   │   └── tutorial_toy_project/
│   └── mcp_tools/     # MCP tool scripts (cluster dispatch, etc.)
├── context/           # Claude Code context docs (data, not Python)
│   ├── CLAUDE.md      # User-facing quick reference (installed as ~/.claude/rules/claudechic_CLAUDE.md)
│   └── *.md           # System docs (checks, guardrails, hints, workflows, etc.)
├── audit/             # Audit pipeline scripts
├── processes.py       # BackgroundProcess dataclass, child process detection
├── screens/           # Full-page screens (navigation)
│   ├── chat.py        # ChatScreen - main chat UI (default screen)
│   ├── diff.py        # DiffScreen - review uncommitted changes
│   ├── session.py     # SessionScreen - session browser for /resume
│   ├── chicsession.py # ChicsessionScreen - chicsession picker and workflow activation
│   ├── rewind.py      # RewindScreen - checkpoint selection
│   ├── settings.py    # SettingsScreen - in-app config editor (per /settings)
│   ├── disabled_workflows.py # DisabledWorkflowsScreen - per-(level, id) toggle subscreen
│   ├── disabled_ids.py # DisabledIdsScreen - per-(level, id) toggle subscreen for hints + rules
│   ├── welcome.py     # WelcomeScreen - first-install onboarding
│   └── workflow_picker.py # WorkflowPickerScreen - workflow selection UI (with level badges)
└── widgets/
    ├── __init__.py    # Re-exports all widgets for backward compat
    ├── prompts.py     # All prompt widgets (Selection, Question, Model, Worktree)
    ├── base/          # Protocols and base classes
    │   ├── clickable.py # ClickableLabel base class
    │   ├── tool_base.py # ToolWidgetBase class
    │   └── tool_protocol.py # ToolWidget protocol
    ├── primitives/    # Low-level building blocks
    │   ├── button.py  # Button with click handling
    │   ├── collapsible.py # QuietCollapsible
    │   ├── scroll.py  # AutoHideScroll
    │   └── spinner.py # Animated spinner
    ├── content/       # Content display widgets
    │   ├── message.py # ChatMessage, ChatInput, ThinkingIndicator
    │   ├── tools.py   # ToolUseWidget, TaskWidget, AgentToolWidget
    │   ├── diff.py    # Syntax-highlighted diff widget
    │   ├── todo.py    # TodoPanel, TodoWidget
    │   ├── markdown_preview.py # PreviewToggle, MarkdownPreviewModal
    │   └── collapsed_turn.py   # CollapsedTurn - lightweight collapsed user+assistant turn
    ├── input/         # User input widgets
    │   ├── autocomplete.py # TextAreaAutoComplete
    │   └── history_search.py # HistorySearch (Ctrl+R)
    ├── layout/        # Structural/container widgets
    │   ├── chat_view.py # ChatView - renders agent messages
    │   ├── sidebar.py # AgentSection, AgentItem, WorktreeItem, ChicsessionLabel, etc.
    │   ├── footer.py  # StatusFooter, AutoEditLabel, ModelLabel
    │   ├── indicators.py # IndicatorWidget, CPUBar, ContextBar, ProcessIndicator
    │   └── processes.py # ProcessPanel, ProcessItem
    ├── reports/       # In-page report widgets
    │   ├── context.py # ContextReport - visual 2D grid
    │   └── usage.py   # UsageReport, UsageBar
    └── modals/        # Modal screen overlays
        ├── base.py          # InfoModal - reusable base for labeled info sections
        ├── profile.py       # ProfileModal - profiling stats
        ├── process_modal.py # ProcessModal - process list
        ├── process_detail.py # ProcessDetailModal - single process detail, kill, metrics
        ├── computer_info.py # ComputerInfoModal - host, OS, Python, SDK, CWD, JSONL path, last compaction (info button; absorbed diagnostics)
        └── agent_switcher.py # AgentSwitcher - Ctrl+G modal to search and switch agents

tests/
├── __init__.py        # Package marker
├── conftest.py        # Shared fixtures (wait_for)
├── test_app.py        # E2E tests with real SDK
├── test_app_ui.py     # App UI tests without SDK
├── test_autocomplete.py # Autocomplete widget tests
├── test_file_index.py # Fuzzy file search tests
├── test_widgets.py    # Pure widget tests
├── test_agent_switcher.py    # AgentSwitcher modal and hint tests
├── test_chicsession_actions.py # ChicsessionActions widget tests
├── test_diff_preview.py      # DiffScreen PreviewToggle tests
└── test_workflow_restore.py  # Workflow restore / chicsession integration tests

docs/
└── dev/               # Developer documentation (from .ai-docs)
```

## Engine code vs bundled content

The post-restructure layout splits workflow engine code from bundled
content along these two paths:

- `claudechic/workflows/` -- Python code (engine, loader, parsers). This
  is a Python package.
- `claudechic/defaults/workflows/` -- Bundled YAML manifests + role
  identity files + phase markdown for the 9 default workflows. These are
  NOT Python packages.

The 3-tier loader (Group C) walks `claudechic/defaults/` (package tier),
`~/.claudechic/` (user tier), and `<launched_repo>/.claudechic/`
(project tier) to assemble the runtime registry of workflows, rules, and
hints. Higher tiers override the same `id` from lower tiers; partial
workflow overrides surface as a loader error.

## Architecture

### Module Boundaries

**Pure functions (no UI dependencies):**
- `formatting.py` - Tool header formatting, diff rendering, language detection
- `sessions.py` - Session file I/O, listing, filtering
- `file_index.py` - Fuzzy file search, git ls-files integration
- `compact.py` - Session compaction to reduce context window usage
- `usage.py` - OAuth API for rate limit info

**Agent layer (no UI dependencies):**
- `agent.py` - `Agent` class owns SDK client, message history, permissions, state
- `agent_manager.py` - Coordinates multiple agents, switching, lifecycle
- `protocols.py` - Observer protocols (`AgentObserver`, `AgentManagerObserver`, `PermissionHandler`)

**Internal protocol:**
- `messages.py` - Custom `Message` subclasses for async event communication
- `permissions.py` - `PermissionRequest` dataclass bridging SDK callbacks to UI
- `mcp.py` - MCP server exposing agent control tools to Claude

**Features:**
- `features/worktree/` - Git worktree management for isolated development

**UI components:**
- `widgets/` - Textual widgets with associated styles
- `widgets/chat_view.py` - `ChatView` renders agent messages, handles streaming
- `app.py` - Main app orchestrating widgets and agents via observer pattern

### Widget Hierarchy

```
ChatApp
└── ChatScreen (default screen, owns chat-specific bindings)
    ├── Horizontal #main
    │   ├── Vertical #chat-column
    │   │   ├── ChatView (one per agent, only active visible)
    │   │   │   ├── ChatMessage (user/assistant)
    │   │   │   ├── ToolUseWidget (collapsible tool display)
    │   │   │   ├── TaskWidget (for Task tool - nested content)
    │   │   │   └── ThinkingIndicator (animated spinner)
    │   │   └── Vertical #input-container
    │   │       ├── ImageAttachments (hidden by default)
    │   │       ├── ChatInput (or SelectionPrompt/QuestionPrompt)
    │   │       └── TextAreaAutoComplete
    │   └── Vertical #right-sidebar (hidden when narrow)
    │       ├── AgentSection
    │       ├── TodoPanel
    │       └── ProcessPanel
    └── StatusFooter
```

### Observer Pattern

Agent and AgentManager emit events via protocol-based observers:

```
Agent events (AgentObserver)         ChatApp handlers
────────────────────────────         ────────────────
on_text_chunk()                  ->  ChatView.append_text()
on_tool_use()                    ->  ChatView.append_tool_use()
on_tool_result()                 ->  ChatView.update_tool_result()
on_complete()                    ->  end response, update UI
on_status_changed()              ->  update AgentSidebar indicator
on_prompt_added()                ->  show SelectionPrompt/QuestionPrompt

AgentManager events                  ChatApp handlers
───────────────────                  ────────────────
on_agent_created()               ->  create ChatView, update sidebar
on_agent_switched()              ->  show/hide ChatViews
on_agent_closed()                ->  remove ChatView, update sidebar
```

This decouples Agent (pure async) from UI (Textual widgets).

### Permission Flow

When SDK needs tool approval:
1. `can_use_tool` callback creates `PermissionRequest`
2. Request queued to `app.interactions` (for testing)
3. `SelectionPrompt` mounted, replacing input
4. User selects allow/deny/allow-all
5. Callback returns `PermissionResultAllow` or `PermissionResultDeny`

For `AskUserQuestion` tool: `QuestionPrompt` handles multi-question flow.

### Styling

Visual language uses left border bars to indicate content type:
- **Orange** (`#cc7700`) - User messages
- **Blue** (`#334455`) - Assistant messages
- **Gray** (`#333333`) - Tool uses (brightens on hover)
- **Blue-gray** (`#445566`) - Task widgets

Context/CPU bars color-code by threshold (dim -> yellow -> red).

Copy buttons appear on hover. Collapsibles auto-collapse older tool uses.

## Key SDK Usage

```python
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

client = ClaudeSDKClient(ClaudeAgentOptions(
    permission_mode="default",
    env={"ANTHROPIC_API_KEY": ""},
    can_use_tool=permission_callback,
    resume=session_id,
))
await client.connect()
await client.query("prompt")
async for message in client.receive_response():
    # Handle AssistantMessage, TextBlock, ToolUseBlock, ToolResultBlock, ResultMessage
```

## Keybindings

- Enter: Send message
- Ctrl+C (x2): Quit
- Ctrl+L: Clear chat (UI only)
- Ctrl+R: Reverse history search
- Shift+Tab: Cycle permission mode (bypassPermissions / auto / acceptEdits / plan / default)
- Ctrl+N: New agent (hint)
- Ctrl+1-9: Switch to agent by position

## Commands

### Multi-Agent
- `/agent` - List all agents
- `/agent <name>` - Create new agent in current directory
- `/agent <name> <path>` - Create new agent in specified directory
- `/agent close` - Close current agent
- `/agent close <name>` - Close agent by name

Agent status indicators: (idle), gray (busy), orange (needs input)

### Inter-Agent Communication (MCP Tools)

These tools let agents communicate programmatically:

- **`message_agent`** -- Send a message to another agent. By default expects a reply (target is nudged if idle without responding). Set `requires_answer=false` for fire-and-forget messages (status updates, results, answering questions).
- **`interrupt_agent`** -- Interrupt an agent's current task immediately. Optionally redirect with a new prompt. Use when you need to stop or redirect a busy agent in real-time.

**When to use which:**
- Need a response? Use `message_agent` (default: `requires_answer=true`).
- Sending info, no reply needed? Use `message_agent` with `requires_answer=false`.
- Need to stop/redirect NOW? Use `interrupt_agent` (cuts through immediately).

### Session Management
- `/resume` - Show session picker
- `/resume <id>` - Resume specific session
- `/settings` - Open settings screen (also accessible via footer "settings" button or welcome screen)
- `/compactish` - Compact session to reduce context (dry run with `-n`)
- `/usage` - Show API rate limit usage
- `/clear` - Clear chat UI
- `/shell <cmd>` - Suspend TUI and run shell command
- `/exit` - Quit

## Configuration

Configuration is stored in two layers:

- `~/.claudechic/config.yaml` -- user-tier preferences (theme, vi-mode,
  default permission mode, `awareness.install`, etc.).
- `<launched_repo>/.claudechic/config.yaml` -- project-tier toggles
  (`guardrails`, `hints`, `disabled_workflows`, `disabled_ids`).

Edit interactively via `/settings`. See
[docs/configuration.md](docs/configuration.md) for the full reference.

### claudechic-awareness install

The `awareness.install` user-tier toggle (default `true`) controls
auto-install of bundled context docs from `claudechic/context/*.md` to
`~/.claude/rules/claudechic_*.md` on every claudechic startup. The SDK
loads these as Claude rules in every session. Disabling stops new
installs but does NOT remove already-installed files; manage them
manually via `rm ~/.claude/rules/claudechic_*.md`.

### Worktree Path Templates

Customize worktree locations in `~/.claudechic/config.yaml` using template variables:

```yaml
worktree:
  path_template: "$HOME/code/worktrees/${repo_name}/${branch_name}"
```

**Variables:** `${repo_name}`, `${branch_name}`, `$HOME`, `~`

**Common patterns:**
```yaml
path_template: "$HOME/code/worktrees/${repo_name}/${branch_name}"  # By repo/branch
path_template: "$HOME/worktrees/${repo_name}-${branch_name}"       # Flat structure
path_template: null                                                # Sibling dirs (default)
```

## Testing

```bash
pytest tests/test_foo.py -v --timeout=30 # Run specific test (preferred)
pytest tests/ -n auto -q --timeout=30    # Parallel (fast, ~3s)
pytest tests/ -v --timeout=30            # Sequential with verbose output
```

Use parallel testing by default.

## Remote Testing

For live testing by AI agents, run with remote control enabled:

```bash
./scripts/claudechic-remote 9999
```

This starts an HTTP server on port 9999 with endpoints for sending messages, taking screenshots, and checking state. See [docs/dev/remote-testing.md](docs/dev/remote-testing.md) for full API documentation.

## Pre-commit Hooks

```bash
uv run pre-commit install  # Install hooks (one-time)
uv run pre-commit run --all-files  # Run manually
```

Hooks: ruff (lint + fix), ruff-format, pyright. Run automatically on commit.

## GitHub

- **Repo:** https://github.com/mrocklin/claudechic
- **CLI:** `gh` is installed and authenticated as `mrocklin-ai`
- Use `gh issue list/view`, `gh pr list/view/create`, etc. for GitHub operations
