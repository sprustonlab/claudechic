# independent_chic — released 2026-04-28

## What's new

- 3-tier override system (package / user / project) for workflows,
  rules, hints, MCP tools.
- claudechic-awareness install: bundled context docs auto-install to
  `~/.claude/rules/claudechic_*.md` every startup; SDK loads them as
  Claude rules.
- New `/settings` UI: footer button, `/settings` command,
  welcome-screen access.
- Workflow picker: level badges + "(defined at: ...)" override display.
- Auto permission mode is the new default; included in Shift+Tab cycle.
- Workflow artifact directories at
  `<repo>/.claudechic/runs/<chicsession>/` via `set_artifact_dir` /
  `get_artifact_dir` MCP tools.
- Tier-aware disable: `disabled_workflows` / `disabled_ids` accept
  bare and `<tier>:<id>` entries.

## Boundary changes

- claudechic state moves out of `.claude/` into `.claudechic/` (config,
  hints state, phase context, audit log).
- No migration; pre-existing files left in place.

## See

- `/settings` for interactive editing.
- `docs/configuration.md` for the full reference.
