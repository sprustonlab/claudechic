# claudechic

A stylish terminal UI for Claude Code, built with Textual and wrapping the `claude-agent-sdk`.

## Run

```bash
uv run claudechic
uv run claudechic --resume     # Resume most recent session
uv run claudechic -s <uuid>    # Resume specific session
```

Dev setup: `uv sync --dev && source .venv/bin/activate` (Linux/macOS).

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
    ├── primitives/    # Low-level building blocks
    ├── content/       # Content display widgets
    ├── input/         # User input widgets
    ├── layout/        # Structural/container widgets (chat_view, sidebar, footer, indicators)
    ├── reports/       # In-page report widgets
    └── modals/        # Modal screen overlays

tests/                 # Test suite (pytest -- see Testing section)

docs/
└── dev/               # Developer documentation (from .ai-docs)
```

## Engine code vs bundled content

- `claudechic/workflows/` -- Python engine (loader, parsers, WorkflowEngine). Python package.
- `claudechic/defaults/workflows/` -- Bundled YAML manifests + role identity + phase markdown. Not Python packages.

3-tier loader: package (`claudechic/defaults/`) -> user (`~/.claudechic/`) -> project (`<repo>/.claudechic/`). Higher tiers override lower; partial workflow overrides are a loader error.

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

Widget hierarchy and styling: see `claudechic/context/widget-system.md` (auto-loaded when editing widgets/ or screens/).

## Commands and Keybindings

Canonical slash-command reference and keybindings: [claudechic/context/CLAUDE.md](claudechic/context/CLAUDE.md) (auto-installed as `~/.claude/rules/claudechic_CLAUDE.md`).

## Configuration

Two layers: `~/.claudechic/config.yaml` (user-tier) and `<repo>/.claudechic/config.yaml` (project-tier). Edit via `/settings` or directly. See [docs/configuration.md](docs/configuration.md).

### claudechic-awareness install

The `awareness.install` user-tier toggle (default `true`) controls
auto-install of bundled context docs from `claudechic/context/*.md` to
`~/.claude/rules/claudechic_*.md` on every claudechic startup. The SDK
loads these as Claude rules in every session. Disabling stops new
installs but does NOT remove already-installed files; manage them
manually via `rm ~/.claude/rules/claudechic_*.md`.

### Worktree Path Templates

Set `worktree.path_template` in `~/.claudechic/config.yaml`. Variables: `${repo_name}`, `${branch_name}`, `$HOME`. Default (`null`) places worktrees as siblings. See [docs/configuration.md](docs/configuration.md) for examples.

## Testing

```bash
pytest tests/test_foo.py -v --timeout=30   # single test (preferred)
pytest tests/ -n auto -q --timeout=30      # parallel (default)
TS=$(date -u +%Y-%m-%d_%H%M%S) && pytest --junitxml=.test_results/${TS}.xml --tb=short --timeout=30 2>&1 | tee .test_results/${TS}.log  # full suite
ruff check --fix && ruff format            # lint + format
```

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
- **CLI:** `gh` authenticated as `mrocklin-ai`
