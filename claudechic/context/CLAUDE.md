# claudechic Quick Reference

claudechic is a terminal UI for Claude Code with multi-agent support, workflows, guardrails, and hints. It wraps the `claude-agent-sdk` in a Textual TUI.

## Commands

| Command | Description |
|---------|-------------|
| `/{workflow_id}` | Activate a workflow (e.g., `/tutorial`) |
| `/agent` | List all agents |
| `/agent <name> [path]` | Create new agent |
| `/agent close [name]` | Close an agent |
| `/shell <cmd>` | Run shell command (suspends TUI) |
| `/diff` | Review uncommitted changes |
| `/resume` | Browse and resume sessions |
| `/settings` | Open in-app settings editor |
| `/compactish` | Compact session to save context |
| `/usage` | Show API rate limit info |
| `/clear` | Clear chat UI |
| `/exit` | Quit |

## Keybindings

- **Enter** -- Send message
- **Ctrl+C** (x2) -- Quit
- **Ctrl+L** -- Clear chat
- **Ctrl+R** -- Reverse history search
- **Shift+Tab** -- Cycle permission mode (bypassPermissions / auto / acceptEdits / plan / default)
- **Ctrl+N** -- New agent hint
- **Ctrl+1-9** -- Switch to agent by position
- **Ctrl+G** -- Agent switcher modal

## Footer Indicators

The status footer shows per-agent state:

- **Effort** -- `effort: low | medium | high | max`. Click `EffortLabel` to cycle. `max` is Opus-only; switching to a non-Opus model snaps effort to `medium` automatically.
- **Model** -- active model name.
- **Permission mode** -- current tool-use permission level (Shift+Tab to cycle).
- **Context bar** -- token usage fraction (colors: dim -> yellow -> red).

## Inter-Agent Communication (MCP Tools)

- **`ask_agent`** -- Send a question and wait for a reply. Use when you need information back.
- **`tell_agent`** -- Fire-and-forget message. Use for status updates or answering questions.
- **`interrupt_agent`** -- Interrupt immediately. Use to stop or redirect a busy agent.

## Agent Self-Awareness (MCP Tools)

These tools let an agent query its own identity and applicable rules:

- **`mcp__chic__whoami`** -- Returns your name, role (`agent_type`), cwd, session id.
- **`mcp__chic__get_phase`** -- Returns active workflow, current phase, progress, artifact dir.
- **`mcp__chic__get_applicable_rules`** -- Markdown list of guardrail rules and advance checks scoped to your (role, phase). Pass `include_skipped=true` for the full audit view.
- **`mcp__chic__get_agent_info`** -- Aggregator: combines whoami + get_phase + get_applicable_rules into one document. Start here when you need the full picture.

## Bundled Workflows

Workflows are activated with `/{id}`. Categories:

**Setup:**
- `codebase_setup` -- Initialize project structure
- `git_setup` -- Configure git for the project
- `cluster_setup` -- Set up cluster computing (LSF/Slurm)

**Learning:**
- `tutorial` -- Getting started with claudechic
- `tutorial_extending` -- Extending claudechic systems
- `tutorial_toy_project` -- Build a toy project end-to-end

**Development:**
- `project_team` -- Multi-agent team development workflow
- `audit` -- Run audit pipeline on workflow outputs

## Guardrails

Always-active safety rules defined in `global/rules.yaml` or workflow manifests. Three enforcement levels:

| Level | Behavior |
|-------|----------|
| `deny` | Hard block. Agent must call `request_override()` for user authorization. |
| `warn` | Acknowledgment required. Agent calls `acknowledge_warning()` to proceed. |
| `log` | Silent audit trail. Execution continues. |

Rules match on tool name + input patterns. Scoped by role and phase.

When a workflow is active your launch prompt contains a `## Constraints` block listing the rules and advance checks that apply to you. Use `mcp__chic__get_applicable_rules` to re-read it at any time.

## Hints

Advisory messages shown as toasts. Two patterns:

- **Pipeline hints** (YAML-defined) -- triggered by project disk state, evaluated at startup and workflow transitions. Defined in `global/hints.yaml` or workflow manifests.
- **Event-driven hints** (code-defined) -- triggered by live UI events (agent created, widget interaction). Use `app.notify()` directly.

Control: `/hints off` disables pipeline hints. Event-driven hints always show.

## Configuration

Two layers:

- `~/.claudechic/config.yaml` -- user-tier preferences.
- `<launched_repo>/.claudechic/config.yaml` -- project-tier toggles.

`disabled_workflows` and `disabled_ids` are FLAT top-level lists.
Each entry is either a bare ID or `<tier>:<id>` (where `<tier>` is
`package`, `user`, or `project`). Bare IDs disable across all tiers;
tier-prefixed entries disable only the named tier's record. The
`disabled_ids` list covers BOTH hint IDs and guardrail rule IDs (their
namespacing keeps them disambiguated). The `guardrails` and `hints`
keys are bool master switches.

```yaml
# Project-tier example: <launched_repo>/.claudechic/config.yaml
guardrails: true                                # bool master switch
hints: true                                     # bool master switch
disabled_workflows:                             # flat list, bare or <tier>:<id>
  - tutorial
  - user:my_custom_flow
  - project:team_specific
disabled_ids:                                   # flat list, hints + rules together
  - global:context-docs-outdated                # bare hint id
  - user:lab/onboarding-rule                    # tier-targeted rule id
  - project:my_workflow:setup-reminder          # tier-targeted (namespace nested)
```

```yaml
# User-tier example: ~/.claudechic/config.yaml
default_permission_mode: auto
awareness:
  install: true                                 # auto-install ~/.claude/rules/claudechic_*.md
worktree:
  path_template: "$HOME/worktrees/${repo_name}/${branch_name}"
```

See `docs/configuration.md` for the full reference.

## Cross-Platform Rules

claudechic targets Linux, macOS, and Windows. Follow these rules:

- ALWAYS pass `encoding='utf-8'` to `open()`, `read_text()`, `write_text()`, `subprocess.run()`
- Use `pathlib.Path` everywhere -- never string-concatenate with `/`
- Guard `os.kill`, `os.killpg`, `pty`, `select` with `sys.platform != "win32"`
- Use `os.replace()` not `Path.rename()` for atomic renames (fails on Windows if target exists)
- Use `python` not `python3`. Use double quotes in shell commands.
- ASCII only -- no emoji, em-dash, or box-drawing characters in source
