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
| `/compactish` | Compact session to save context |
| `/usage` | Show API rate limit info |
| `/clear` | Clear chat UI |
| `/exit` | Quit |

## Keybindings

- **Enter** -- Send message
- **Ctrl+C** (x2) -- Quit
- **Ctrl+L** -- Clear chat
- **Ctrl+R** -- Reverse history search
- **Shift+Tab** -- Cycle permission mode (default / auto-edit / plan)
- **Ctrl+N** -- New agent hint
- **Ctrl+1-9** -- Switch to agent by position
- **Ctrl+G** -- Agent switcher modal

## Inter-Agent Communication (MCP Tools)

- **`ask_agent`** -- Send a question and wait for a reply. Use when you need information back.
- **`tell_agent`** -- Fire-and-forget message. Use for status updates or answering questions.
- **`interrupt_agent`** -- Interrupt immediately. Use to stop or redirect a busy agent.

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

## Hints

Advisory messages shown as toasts. Two patterns:

- **Pipeline hints** (YAML-defined) -- triggered by project disk state, evaluated at startup and workflow transitions. Defined in `global/hints.yaml` or workflow manifests.
- **Event-driven hints** (code-defined) -- triggered by live UI events (agent created, widget interaction). Use `app.notify()` directly.

Control: `/hints off` disables pipeline hints. Event-driven hints always show.

## Configuration

Stored in `~/.claude/.claudechic.yaml`:

```yaml
guardrails:
  disabled_ids: ["global:some_rule"]   # Disable specific rules
hints:
  disabled_ids: ["global:some_hint"]   # Disable specific hints
disabled_workflows: ["tutorial"]        # Hide workflows from picker
worktree:
  path_template: "$HOME/worktrees/${repo_name}/${branch_name}"
```

## Cross-Platform Rules

claudechic targets Linux, macOS, and Windows. Follow these rules:

- ALWAYS pass `encoding='utf-8'` to `open()`, `read_text()`, `write_text()`, `subprocess.run()`
- Use `pathlib.Path` everywhere -- never string-concatenate with `/`
- Guard `os.kill`, `os.killpg`, `pty`, `select` with `sys.platform != "win32"`
- Use `os.replace()` not `Path.rename()` for atomic renames (fails on Windows if target exists)
- Use `python` not `python3`. Use double quotes in shell commands.
- ASCII only -- no emoji, em-dash, or box-drawing characters in source
