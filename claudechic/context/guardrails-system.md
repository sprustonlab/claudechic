---
paths:
  - claudechic/guardrails/**
  - .claude/guardrails/**
---

# Guardrails System

LEAF MODULE: `rules.py` imports no other claudechic systems. `hooks.py` imports `ManifestLoader` under `TYPE_CHECKING` only. Never import from workflows/, checks/, or hints/.

## Terminology

- **Guardrail rule** — always-active safety rules in `.claude/guardrails/rules.yaml`.
- **Global rule** — rules in `global/rules.yaml`, always active when claudechic is running.
- **Workflow rule** — rules in workflow YAML, active only when that workflow is running.
- Both use the same `Rule` frozen dataclass and evaluation pipeline.

## Enforcement Levels

| Level | Behavior |
|-------|----------|
| `deny` | Hard block. Agent must call `request_override()` for user authorization. |
| `warn` | Acknowledgment required. Agent calls `acknowledge_warning()` to consume token. |
| `log` | Silent audit. Hit logged, execution continues. |

## Two-Step Hook Pipeline

`create_guardrail_hooks()` returns a `PreToolUse` hook closure. On every tool call:

1. **Injections first** — iterate `Injection` objects, call `apply_injection()` to mutate `tool_input` in-place. Return `updatedInput` via SDK hook protocol.
2. **Enforcement rules** — iterate `Rule` objects, check trigger → role → phase → exclude → detect pattern. First matching rule applies its enforcement level.

## Rule Scoping

- `roles` / `exclude_roles` — restrict which agent roles a rule applies to.
- `phases` / `exclude_phases` — restrict which workflow phases a rule applies to.
- Namespace filtering: rules from inactive workflows are skipped (namespace must be `"global"` or match `active_wf`).

## Rule Matching

Use `matches_trigger(rule, tool_name)` to check trigger events (format: `PreToolUse/Bash`). Use `match_rule(rule, tool_name, tool_input)` to check detect/exclude patterns against the `detect_field` (default: `"command"`).

## Override Tokens

One-time authorization via `consume_override` callback. Warn tokens consumed by `acknowledge_warning()`. Deny tokens consumed by `request_override()`. A warn token cannot satisfy a deny rule.

## Hit Logging

`HitLogger` records an append-only JSONL audit trail. Every rule match produces a `HitRecord` with outcome: `allowed`, `ack`, `blocked`, or `overridden`.

## Loader Integration

`hooks.py` receives a shared `ManifestLoader` instance. Rules are loaded fresh on every hook call (no mtime caching — NFS safe). Fail-closed: if discovery errors exist and no rules loaded, block everything.

## Always-Active Guardrails

Edit `.claude/guardrails/rules.yaml` for always-active guardrail rules. Run `generate_hooks.py` after editing to regenerate Claude Code hook files.

## ## Constraints Block

When a workflow is active, each agent's launch prompt contains a `## Constraints` markdown section listing the guardrail rules and advance checks that are scoped to that agent's (role, phase). The block is rendered by `assemble_constraints_block()` and injected at five sites via `assemble_agent_prompt()`. Agents should treat this block as their authoritative view of active rules -- it is role+phase filtered and reflects `disabled_ids` exactly.

## Agent Self-Awareness MCP Tools

Four MCP tools give agents a read-only view of their own identity and applicable rules:

| Tool | Purpose |
|------|---------|
| `mcp__chic__whoami` | Returns agent name, role, cwd, session id. |
| `mcp__chic__get_phase` | Returns active workflow id, current phase, progress fraction, artifact dir, loader errors. |
| `mcp__chic__get_applicable_rules` | Returns markdown projection of guardrail rules and advance checks scoped to the calling agent's (role, phase). Accepts `include_skipped=true` for an audit view that also shows inactive rules. |
| `mcp__chic__get_agent_info` | Aggregator: delegates to `whoami` + `get_phase` + `get_applicable_rules` and returns a single markdown document. |

`get_phase` no longer emits a rule-count summary line; use `get_applicable_rules` for rule enumeration.

**Freshness:** If you modify source files matched by this rule, verify this
document still accurately describes the system behavior. Update if needed.
