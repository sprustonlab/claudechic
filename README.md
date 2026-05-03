# Claude Chic

A stylish terminal UI for [Claude Code](https://docs.anthropic.com/en/docs/claude-code), built with [Textual](https://textual.textualize.io/).
This is the [sprustonlab](https://github.com/sprustonlab) fork of [mrocklin/claudechic](https://github.com/mrocklin/claudechic), extended with workflows, guardrails, and lab-specific tooling.

## Starting Point

If you're setting up a new project, start at **[AI_PROJECT_TEMPLATE](https://github.com/sprustonlab/AI_PROJECT_TEMPLATE)** first -- it sets up a project with claudechic already integrated. This page covers claudechic itself.

## Install

```bash
uv tool install git+https://github.com/sprustonlab/claudechic
```

Requires Claude Code to be logged in (`claude /login`). After install, run `claudechic`.

## Core Concepts

- **Workflows** -- phase-gated processes that structure multi-agent collaboration
- **Phases** -- named workflow stages with scoped rules, hints, and advance checks
- **Hints** -- contextual toast notifications surfaced to agents during workflows
- **Advance Checks** -- gate conditions that must pass before a phase transition
- **Chicsessions** -- named multi-agent session snapshots for save/restore
- **Guardrails** -- rule-based safety enforced on every tool call

## Features

### Workflows

Activate with `/{id}` (e.g., `/project_team`, `/tutorial`). Phase-gated multi-agent processes with user checkpoints and role-scoped agents. Try `/tutorial` to get started.

The `/project_team` workflow runs four phases, each ending with a user checkpoint:

1. **Vision** -- describe what you want; a coordinator agent clarifies scope and confirms before proceeding.
2. **Specification** -- leadership agents (Composability, Terminology, UserAlignment, Skeptic) draft and review a spec.
3. **Implementation** -- implementer agents write code guided by the spec and leadership roles.
4. **Testing** -- tests are written and run; leadership signs off before the workflow completes.

### Guardrails

Rule-based safety that blocks or warns before dangerous operations (e.g., `rm -rf /`, `git push --force`). Three levels: `deny`, `warn`, `log`. Enabled by default; can be disabled via `guardrails: false` in `.claudechic/config.yaml`.

### Multi-Agent

Create agents with `/agent <name>`, switch with Ctrl+1-9 or Ctrl+G. Agents communicate via `message_agent` and `interrupt_agent` MCP tools. Workflows spawn role-typed sub-agents automatically.

### Chicsessions

Named multi-agent session snapshots. Save and restore full agent state including active workflow phase. Browse via `/restore`.

### Settings

`/settings` opens the in-app config editor. Controls permission modes, "Agent prompt context", "Disabled workflows", and more.

### MCP Tools

claudechic exposes control tools (`message_agent`, `interrupt_agent`, `get_agent_info`, etc.) to agents via an in-process MCP server. You can add project-specific MCP tools by dropping Python scripts into a `mcp_tools/` folder in your project -- claudechic discovers and registers them automatically.

## 3-Tier Configuration

claudechic resolves rules, workflows, and hints by walking three tiers in order:

- **Package tier** -- bundled content under `claudechic/defaults/` (ships with claudechic)
- **User tier** -- `~/.claudechic/` (personal overrides and custom workflows)
- **Project tier** -- `<launched-repo>/.claudechic/` (per-project config, checked into the repo)

Higher tiers override lower; same-id collisions resolve by tier precedence. This makes claudechic configurable per-project without forking -- drop a `.claudechic/` folder in any repo to customize rules, disable workflows, or add new ones.

## Fork-Specific Features

- **`/clearui`** -- clear chat display when the UI becomes sluggish (session history preserved).
- **Shared permission mode** -- Shift+Tab cycles all agents together through bypassPermissions / auto / acceptEdits / plan / default.
- **`--yolo` flag** -- `claudechic --yolo` auto-approves all tool uses without prompting. Guardrail rules still apply. Use in sandboxed environments.

## Development

```bash
git clone https://github.com/sprustonlab/claudechic.git
cd claudechic
uv sync --dev
uv run claudechic
```

Run tests:

```bash
uv run python -m pytest tests/ -n auto -q --timeout=30
```

## Alpha Status

This project is young and fresh. Expect bugs.
[Report issues](https://github.com/sprustonlab/claudechic/issues/new).

## Further Reading

See [docs/](docs/) for configuration reference, architecture overview, and feature guides.
