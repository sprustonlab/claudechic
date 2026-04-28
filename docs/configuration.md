# Configuration reference

Use the `/settings` screen for interactive editing; this page is the
ground-truth reference for every config key, environment variable, and
CLI flag.

## Overview

claudechic loads configuration from two layers:

- **User layer** (`~/.claudechic/config.yaml`) — your global preferences,
  shared across all repos.
- **Project layer** (`<launched_repo>/.claudechic/config.yaml`) — the
  per-repo feature toggles and disable lists for the project you launched
  claudechic from.

Defaults live in code (no package layer config file). Settings exposed in
the in-app `/settings` screen save live on each edit; the YAML files on
disk are the authoritative store.

User-facing labels in the in-app screen and helper text use the word
**"level"** for the three layers (package / user / project); this
reference uses **"tier"** when it matches the term used in the spec and
codebase.

## User-tier config keys

The following keys live under `~/.claudechic/config.yaml`. Keys are
shown as canonical dotted paths. All have sensible defaults.

### `default_permission_mode`

- **Type:** `string`
- **Accepted values:** `default`, `acceptEdits`, `plan`, `auto`,
  `bypassPermissions`
- **Default:** `auto`
- **Exposed in `/settings`:** yes

The startup permission mode applied to every newly-spawned agent. `auto`
is the default for new installs — safe tools are auto-approved while
write-style tools still prompt. Cycle modes at runtime with **Shift+Tab**.

```yaml
default_permission_mode: auto
```

### `theme`

- **Type:** `string`
- **Default:** unset (uses `textual-dark`)
- **Exposed in `/settings`:** yes (delegates to the existing `/theme`
  search picker)

The active Textual theme name. Set via `/theme` or by overriding for a
single run with `--theme <name>`.

```yaml
theme: textual-dark
```

### `vi-mode`

- **Type:** `boolean`
- **Default:** `false`
- **Exposed in `/settings`:** yes

Enable vi keybindings in the chat input. Toggle at runtime with `/vim`.

```yaml
vi-mode: true
```

### `show_message_metadata`

- **Type:** `boolean`
- **Default:** `true`
- **Exposed in `/settings`:** yes

Show timestamp and token count under each chat message.

```yaml
show_message_metadata: true
```

### `recent-tools-expanded`

- **Type:** `integer`
- **Range:** `0-20`
- **Default:** `2`
- **Exposed in `/settings`:** yes

Number of recent tool-use widgets to leave expanded; older widgets
auto-collapse to save vertical space.

```yaml
recent-tools-expanded: 2
```

### `worktree.path_template`

- **Type:** `string` or `null`
- **Default:** `null` (sibling-directory layout)
- **Exposed in `/settings`:** yes

Template for `/worktree` paths. Variables: `${repo_name}`,
`${branch_name}`, `$HOME`, `~`. Setting to `<default>` (or empty) reverts
to the sibling-directory layout.

Common patterns:

```yaml
worktree:
  path_template: $HOME/code/worktrees/${repo_name}/${branch_name}
```

```yaml
worktree:
  path_template: $HOME/worktrees/${repo_name}-${branch_name}
```

### `analytics.enabled`

- **Type:** `boolean`
- **Default:** `true`
- **Exposed in `/settings`:** yes

Send anonymous usage analytics. Opt out via `/analytics opt-out` or by
setting to `false`. See `docs/privacy.md` for details on what is
collected.

```yaml
analytics:
  enabled: true
```

### `analytics.id`

- **Type:** `string` (UUID)
- **Default:** auto-generated on first install
- **Exposed in `/settings`:** no (hidden from UI)

Anonymous installation identifier. Generated once on first install and
preserved across restarts. Hidden from the in-app settings UI.

### `logging.file`

- **Type:** `string` (path) or empty
- **Default:** `~/claudechic.log`
- **Exposed in `/settings`:** yes

Where claudechic writes its log file. Set to empty to disable file
logging.

```yaml
logging:
  file: ~/claudechic.log
```

### `logging.notify-level`

- **Type:** `string`
- **Accepted values:** `debug`, `info`, `warning`, `error`, `none`
- **Default:** `warning`
- **Exposed in `/settings`:** yes

Minimum severity at which logged messages also surface as Textual
notifications.

```yaml
logging:
  notify-level: warning
```

### `awareness.install`

- **Type:** `boolean`
- **Default:** `true`
- **Exposed in `/settings`:** yes (label: "Install claudechic-awareness")

Gate the auto-install of bundled context docs into
`~/.claude/rules/claudechic_*.md`. See the
[claudechic-awareness install](#claudechic-awareness-install) section
below for details. Default `true` — disabling stops new installs but does
NOT remove already-installed files.

```yaml
awareness:
  install: true
```

### `experimental.*`

- **Type:** mixed
- **Default:** unset
- **Exposed in `/settings`:** no (hidden from UI)

Reserved namespace for experimental flags. Keys here may change without
notice; consult release notes before relying on any.

## Project-tier config keys

The following keys live under
`<launched_repo>/.claudechic/config.yaml` and apply only to the launched
repository.

### `guardrails`

- **Type:** `boolean`
- **Default:** `true`
- **Exposed in `/settings`:** yes

Enable guardrail rule enforcement (PreToolUse hooks). When `false`, no
deny / warn / log rules fire for this project. Changes apply to new
agents; restart claudechic to apply to existing agents.

```yaml
guardrails: true
```

### `hints`

- **Type:** `boolean`
- **Default:** `true`
- **Exposed in `/settings`:** yes

Enable advisory hint toasts evaluated through the 6-stage hints pipeline.

```yaml
hints: true
```

### `disabled_workflows`

- **Type:** `list[string]`
- **Default:** `[]`
- **Exposed in `/settings`:** yes (subscreen)

List of workflow IDs to hide from the workflow picker and slash-command
activation. Each entry is **either** a bare ID (`<workflow_id>`) **or** a
tier-targeted entry (`<tier>:<workflow_id>` where `<tier>` is one of
`package`, `user`, `project`).

- **Bare ID** disables the workflow at every tier where it is defined.
- **Tier-targeted** disables only the named tier's record; lower-priority
  tiers' records of the same id (if any) take effect via override
  resolution.
- An invalid prefix (anything other than `package` / `user` / `project`)
  is treated as a bare entry; the loader logs a warning so typos surface.
- User-config and project-config disable entries are **additive**; an
  entry in either file disables the workflow for the launched repo.

```yaml
disabled_workflows:
  - tutorial
  - user:my_custom_flow
  - project:team_specific
```

### `disabled_ids`

- **Type:** `list[string]`
- **Default:** `[]`
- **Exposed in `/settings`:** yes (subscreen)

List of hint IDs and guardrail rule IDs to disable. Item IDs are
namespaced (`namespace:bare_id`, e.g. `global:context-docs-outdated`);
tier-targeted entries take the form
`<tier>:<namespace>:<bare_id>`.

- **Bare ID** (e.g. `global:permission-mode-tip`) disables the item at
  every tier where it is defined.
- **Tier-targeted** (e.g. `user:lab/onboarding-rule`) disables only the
  named tier's record.
- An invalid prefix is treated as a bare qualified id; the loader logs a
  warning.
- User-config and project-config disable entries are **additive**.

```yaml
disabled_ids:
  - global:context-docs-outdated
  - user:lab/onboarding-rule
  - project:my_workflow:setup-reminder
```

## Environment variables

| Variable | Scope | Default | Description |
|---|---|---|---|
| `CLAUDECHIC_REMOTE_PORT` | runtime | unset | If set to an integer port, start the remote-control HTTP server on that port. Equivalent to `--remote-port`. |
| `CLAUDECHIC_APP_PID` | inherited | claudechic's PID | Set by claudechic for child processes; lets MCP tools detect the running app. |
| `CLAUDECHIC_ARTIFACT_DIR` | inherited | unset | Workflow artifact-dir token, set by the engine after `set_artifact_dir(path)` is invoked. Workflow markdown substitutes `${CLAUDECHIC_ARTIFACT_DIR}` with this value. |
| `CHIC_PROFILE` | runtime | unset | When set, enables `@profile`-decorated profiling output to the log. |
| `CHIC_SAMPLE_THRESHOLD` | runtime | unset | CPU-percent threshold above which the sampling profiler activates. |
| `CLAUDE_AGENT_NAME` | inherited | unset | Set by claudechic for spawn-agent processes; the SDK reads it for agent identity. |
| `CLAUDE_AGENT_ROLE` | inherited | unset | Same as above for the agent's role within a workflow. |
| `ANTHROPIC_BASE_URL` | runtime | unset | Override the Anthropic API base URL (rarely needed). |

## CLI flags

| Flag | Type | Default | Description |
|---|---|---|---|
| `--version`, `-V` | flag | n/a | Print version and exit. |
| `--resume`, `-r` | flag | off | Resume the most recent session. |
| `--session`, `-s <id>` | string | unset | Resume a specific session by ID prefix. |
| `--theme`, `-t [name]` | string | unset | Use a specific theme for this session; pass without value to list available themes. |
| `--remote-port <port>` | integer | `0` | Start HTTP server for remote control. Falls back to `CLAUDECHIC_REMOTE_PORT` env var. |
| `--dangerously-skip-permissions`, `--yolo` | flag | off | Auto-approve all tool uses without prompting. Use only in sandboxed environments. |
| `prompt` | positional | unset | Initial prompt to send (joins all positional args with spaces). |

## claudechic-awareness install

On every claudechic startup, the bundled context docs in
`claudechic/context/*.md` are copied into
`~/.claude/rules/claudechic_*.md` so the Claude Agent SDK loads them as
Claude rules in every session (claudechic-spawned or not). The install
is idempotent: files that already match are skipped (SKIP); files that
differ are updated (UPDATE); new files are added (NEW); orphan
`claudechic_*.md` files no longer in the bundled catalog are removed
(DELETE). The `claudechic_` prefix prevents collision with user-authored
rules in the same directory.

### The toggle

The `awareness.install` user-tier config key (default `true`) gates the
install. When set to `false`, the install routine no-ops on startup —
including no DELETE pass; existing installed `claudechic_*` files are NOT
removed by claudechic. The toggle is "should claudechic maintain
`~/.claude/rules/claudechic_*.md`" — NOT "is the agent's awareness
disabled." **Disabling stops new installs but does NOT remove
already-installed files.** To actually stop the agent from loading
claudechic-awareness content, you MUST manually
`rm ~/.claude/rules/claudechic_*.md` after disabling the toggle.

### What gets installed

The bundled context docs in `claudechic/context/`:

- `claudechic-overview.md`
- `workflows-system.md`
- `hints-system.md`
- `guardrails-system.md`
- `checks-system.md`
- `manifest-yaml.md`
- `multi-agent-architecture.md`
- `CLAUDE.md`

Each is installed as `~/.claude/rules/claudechic_<name>.md` (with the
`claudechic_` prefix).

### Manual re-install

The `/onboarding` workflow's `context_docs` phase invokes the same
install routine with `force=True`, providing an explicit user-driven
trigger separate from the automatic startup install. Useful when
`awareness.install` is `false` but you want a one-time refresh.

### Editing the installed copies

Manual user edits to `claudechic_*` regular files are clobbered on the
next startup (when `awareness.install` is `true`). claudechic owns the
`claudechic_` prefix namespace inside `~/.claude/rules/`. To manage
rules manually, you have three options:

1. Disable `awareness.install`.
2. Author files with any filename NOT matching `claudechic_*` (those are
   user-owned and not touched by claudechic).
3. Replace a `claudechic_*.md` regular file with a symlink — the symlink
   guard leaves any symlink at a `claudechic_*.md` path untouched (no
   NEW / UPDATE / SKIP / DELETE applies; a WARNING is logged once per
   startup per such file).

### Removing claudechic-awareness install

If you want to fully remove claudechic's influence on
`~/.claude/rules/`:

1. Set `awareness.install: false` in `~/.claudechic/config.yaml` (stops
   future installs and the DELETE pass).
2. `rm ~/.claude/rules/claudechic_*.md` (removes already-installed
   files).

Step (1) without step (2) leaves stale files loading in every Claude
session; step (2) without step (1) is a one-shot — the next claudechic
startup re-installs the deleted files.

### Orphan cleanup is automatic when toggle is on

When claudechic ships a smaller bundle or renames a context doc across
versions, the next startup's DELETE pass automatically removes orphan
`claudechic_*.md` files no longer in the bundled catalog. You do NOT
need to manually clean up after upgrades.

### No drift hint

The install is idempotent on every claudechic startup, so when
`awareness.install` is `true` the installed copies stay in sync with the
bundled versions automatically — both forward-drift (bundle newer than
installed) AND orphan-drift (installed file dropped from bundle) are
repaired silently. No user action required, no hint fires.

## Overriding workflows

claudechic resolves workflows across three layers (package / user /
project) with project taking precedence over user, and user over
package. To override a bundled workflow, copy its full contents into
your layer's `workflows/<id>/` directory:

- User overrides live at `~/.claudechic/workflows/<id>/`.
- Project overrides live at
  `<launched_repo>/.claudechic/workflows/<id>/`.

### Why partial overrides are not supported

To override a workflow at the user or project layer, copy **all** files
of the workflow into your layer's `workflows/<id>/` directory. Partial
overrides — some files in your layer, others falling back to the lower
layer — are not supported and will surface as a loader error.

A higher-tier directory missing files the lower-tier defines is a
partial override; the loader rejects it with a
`LoadError(section="workflow")` and falls through to the next-lower
complete tier.

### Artifact-directory token

Workflow markdown can reference the engine's artifact-dir via the
`${CLAUDECHIC_ARTIFACT_DIR}` token. Once a coordinator agent calls
`set_artifact_dir(path)` (an MCP tool), subsequent agents see the
resolved path baked into their workflow markdown via substitution. The
path persists in chicsession state, so resume restores it without
coordinator re-call.

The `ArtifactDirReadyCheck` advance check (registered in workflow YAML
as `artifact-dir-ready-check`) blocks phase advancement until
`set_artifact_dir(...)` has been called and the engine's `artifact_dir`
is non-`None` — use it on Setup-style phases that produce the path so
downstream phases never run with the token unresolved.

## Cross-references

- `claudechic/context/claudechic-overview.md` — system overview.
- `claudechic/context/workflows-system.md` — workflow engine details.
- `/settings` — interactive editing of every key listed above.
- `docs/privacy.md` — analytics scope and privacy details.
