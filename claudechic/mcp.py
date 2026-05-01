"""In-process MCP server for claudechic agent control.

Exposes tools for Claude to manage agents within claudechic:
- spawn_agent: Create new agent, optionally with initial prompt
- spawn_worktree: Create git worktree + agent
- message_agent: Send message to existing agent (expects reply by default; fire-and-forget with requires_answer=false)
- interrupt_agent: Interrupt an agent, optionally redirect with new prompt
- list_agents: List current agents and their status
- close_agent: Close an agent by name
- finish_worktree: Finish current agent's worktree (commit, rebase, merge, cleanup)
"""

from __future__ import annotations

import asyncio
import importlib.util
import logging
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from claude_agent_sdk import create_sdk_mcp_server, tool

from claudechic.agent import DEFAULT_ROLE
from claudechic.analytics import capture
from claudechic.config import CONFIG
from claudechic.enums import AgentStatus
from claudechic.workflows.loader import Tier, TierRoots
from claudechic.features.worktree.git import (
    FinishPhase,
    FinishState,
    ResolutionAction,
    clean_gitignored_files,
    determine_resolution_action,
    diagnose_worktree,
    fast_forward_merge,
    finish_cleanup,
    get_cleanup_fix_prompt,
    get_finish_info,
    get_finish_prompt,
    start_worktree,
)
from claudechic.tasks import create_safe_task

if TYPE_CHECKING:
    from claudechic.app import ChatApp

log = logging.getLogger(__name__)

_PKG_DIR = Path(__file__).parent

# Global app reference, set by ChatApp.on_mount()
_app: ChatApp | None = None


def set_app(app: ChatApp) -> None:
    """Register the app instance for MCP tools to use."""
    global _app
    _app = app


def _text_response(text: str, *, is_error: bool = False) -> dict[str, Any]:
    """Format a text response for MCP."""
    result: dict[str, Any] = {"content": [{"type": "text", "text": text}]}
    if is_error:
        result["isError"] = True
    return result


def _error_response(text: str) -> dict[str, Any]:
    """Format an error response for MCP."""
    return _text_response(text, is_error=True)


def _find_agent_by_name(name: str):
    """Find an agent by name. Returns (agent, error_message)."""
    if _app is None or _app.agent_mgr is None:
        return None, "App not initialized"
    agent = _app.agent_mgr.find_by_name(name)
    if agent:
        return agent, None
    return None, f"Agent '{name}' not found. Use list_agents to see available agents."


def _track_mcp_tool(tool_name: str) -> None:
    """Track MCP tool usage for analytics."""
    if _app and _app.agent_mgr:
        active = _app.agent_mgr.active
        _app.run_worker(
            capture(
                "mcp_tool_used",
                tool=tool_name,
                agent_id=active.analytics_id if active else "unknown",
            )
        )


def _clear_pending_reply_if_matched(
    sender_name: str | None, recipient_name: str
) -> None:
    """Clear _pending_reply_to if the sender is replying to their caller.

    Called from message_agent (requires_answer=False). If the sending agent has
    _pending_reply_to == recipient_name, it means the agent is delivering
    its required answer — clear the obligation.
    """
    if not sender_name or not _app or not _app.agent_mgr:
        return
    sender = _app.agent_mgr.find_by_name(sender_name)
    if sender and sender._pending_reply_to == recipient_name:
        sender._pending_reply_to = None
        sender._reply_nudge_count = 0
        # Bump generation to invalidate any pending nudge timers
        sender._nudge_generation += 1
        log.debug(
            "Agent '%s' fulfilled reply obligation to '%s'", sender_name, recipient_name
        )


def _send_prompt_fire_and_forget(
    agent,
    prompt: str,
    *,
    caller_name: str | None = None,
    expect_reply: bool = False,
    is_spawn: bool = False,
) -> None:
    """Fire-and-forget prompt send that doesn't block MCP handlers.

    MCP handlers have implicit timeouts - awaiting SDK operations like
    agent.send() can cause "stream closed" errors. This function schedules
    the send as a background task and returns immediately.

    Args:
        agent: The agent to send to
        prompt: The message to send
        caller_name: If set, wraps prompt with sender info
        expect_reply: If True (with caller_name), adds reply instructions
        is_spawn: If True (with caller_name), uses "Spawned by" prefix
    """
    # Wrap prompt with caller info if provided
    if caller_name:
        if expect_reply:
            prompt = f"[Question from agent '{caller_name}' - respond using message_agent with requires_answer=false, or message_agent (default) if you need more context first]\n\n{prompt}"
        elif is_spawn:
            prompt = f"[Spawned by agent '{caller_name}']\n\n{prompt}"
        else:
            prompt = f"[Message from agent '{caller_name}']\n\n{prompt}"

    async def do_send():
        if agent.client is None:
            log.warning(f"Agent '{agent.name}' not connected, skipping prompt")
            return
        await agent.send(prompt)

    # Use monotonic_ns for unique task names (helps debugging concurrent sends)
    task_id = time.monotonic_ns()
    create_safe_task(do_send(), name=f"send-prompt-{agent.name}-{task_id}")


def _make_spawn_agent(caller_name: str | None = None):
    """Create spawn_agent tool with optional caller name bound."""

    @tool(
        "spawn_agent",
        "Create a new Claude agent in claudechic. The agent gets its own chat view and can work independently.",
        {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "path": {"type": "string"},
                "prompt": {"type": "string"},
                "model": {
                    "type": "string",
                    "description": "Model to use (inherits caller's model if not specified)",
                },
                "type": {
                    "type": "string",
                    "description": "Workflow role folder name (e.g. 'skeptic', 'composability'). Required for the agent to receive phase updates and role-specific instructions when a workflow is active.",
                },
                "requires_answer": {
                    "type": "boolean",
                    "description": "If true, the spawned agent is expected to reply back to the caller using message_agent. It will be nudged if idle without replying.",
                },
            },
            "required": ["name", "path", "prompt"],
        },
    )
    async def spawn_agent(args: dict[str, Any]) -> dict[str, Any]:
        """Spawn a new agent, optionally with an initial prompt."""
        if _app is None or _app.agent_mgr is None:
            return _error_response("App not initialized")
        _track_mcp_tool("spawn_agent")

        name = args["name"]
        # Default to active agent's cwd (so agents inherit creator's directory)
        default_cwd = _app.agent_mgr.active.cwd if _app.agent_mgr.active else Path.cwd()
        path = Path(args.get("path", str(default_cwd))).resolve()
        prompt = args.get("prompt")
        agent_type = args.get("type")
        requires_answer = args.get("requires_answer", False)

        # BUG #2 fix: When type is provided and a workflow is active,
        # validate that the role folder exists.  The `type` parameter is
        # the explicit link to the workflow role system — we never infer
        # it from the agent name (that's fragile).  If type is not
        # provided, the agent gets no role wiring (generic agent).
        if agent_type and _app._workflow_engine:
            try:
                wf_data = (
                    _app._load_result.get_workflow(_app._workflow_engine.workflow_id)
                    if _app._load_result is not None
                    else None
                )
                wf_dir = wf_data.path if wf_data is not None else None
                if wf_dir and not (wf_dir / agent_type).is_dir():
                    available = sorted(
                        d.name
                        for d in wf_dir.iterdir()
                        if d.is_dir() and not d.name.startswith(".")
                    )
                    roles_list = ", ".join(available) if available else "(none found)"
                    return _error_response(
                        f"Role '{agent_type}' not found in workflow "
                        f"'{_app._workflow_engine.workflow_id}'. "
                        f"Available roles: {roles_list}"
                    )
            except Exception:
                pass  # Best-effort check, don't block spawn

        # Inherit caller's model if not explicitly specified
        caller_model = None
        if caller_name:
            caller_agent = _app.agent_mgr.find_by_name(caller_name)
            if caller_agent:
                caller_model = caller_agent.model
        model = args.get("model") or caller_model

        if not path.exists():
            return _error_response(f"Path '{path}' does not exist")

        # Check if agent with this name already exists (active or closed)
        if _app.agent_mgr.find_by_name(name):
            return _error_response(f"Agent '{name}' already exists")
        if _app.agent_mgr.find_closed_by_name(name):
            return _error_response(
                f"A closed agent named '{name}' exists. "
                f"Ask the user to run /agent reopen {name}"
            )

        try:
            # Create agent via AgentManager (handles SDK connection)
            agent = await _app.agent_mgr.create(
                name=name,
                cwd=path,
                switch_to=False,
                model=model,
                agent_type=agent_type,
            )
        except Exception as e:
            return _error_response(f"Error creating agent: {e}")

        # Track that this agent owes a reply to the caller
        if requires_answer and caller_name:
            agent._pending_reply_to = caller_name

        result = f"Created agent '{name}' in {path}"

        if _app._workflow_engine and not agent_type:
            result += (
                "\n\n[WARNING] No type= specified. This agent will not receive "
                "role-specific phase instructions. Set type= to a role folder "
                "name to enable agent prompt injection."
            )

        if prompt:
            # Inject agent folder prompt at spawn time if workflow is active.
            # D5 inject site (sub-agent spawn): route through assemble_agent_prompt so the
            # spawn-time prompt embeds the role+phase scoped ## Constraints
            # block. The helper IS the contract; the five inject sites do
            # not concat by hand.
            full_prompt = prompt
            if _app._workflow_engine and agent_type:
                try:
                    from claudechic.workflows.agent_folders import (
                        assemble_agent_prompt,
                    )

                    engine = _app._workflow_engine
                    wf_data = (
                        _app._load_result.get_workflow(engine.workflow_id)
                        if _app._load_result is not None
                        else None
                    )
                    if wf_data is not None:
                        # D6 alignment: pull the merged disabled_ids set
                        # from the app so spawn-time constraints match
                        # what the hook layer fires on and what the
                        # registry tools (get_applicable_rules,
                        # get_agent_info) report. Helper is exposed by
                        # slot 4 in app.py.
                        get_disabled = getattr(_app, "_get_disabled_rules", None)
                        disabled_rules = (
                            get_disabled() if callable(get_disabled) else None
                        )
                        folder_prompt = assemble_agent_prompt(
                            agent_type,
                            engine.get_current_phase(),
                            getattr(_app, "_manifest_loader", None),
                            workflow_dir=wf_data.path,
                            artifact_dir=engine.get_artifact_dir(),
                            project_root=getattr(engine, "project_root", None),
                            engine=engine,
                            active_workflow=engine.workflow_id,
                            disabled_rules=disabled_rules,
                        )
                        if folder_prompt:
                            full_prompt = f"{folder_prompt}\n\n---\n\n{prompt}"
                except Exception:
                    log.debug(
                        "Agent folder prompt assembly failed for '%s'",
                        name,
                        exc_info=True,
                    )

            _send_prompt_fire_and_forget(
                agent, full_prompt, caller_name=caller_name, is_spawn=True
            )
            result += f"\nQueued initial prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}"

        return _text_response(result)

    return spawn_agent


def _make_spawn_worktree(caller_name: str | None = None):
    """Create spawn_worktree tool with optional caller name bound."""

    @tool(
        "spawn_worktree",
        "Create a git worktree (feature branch) with a new agent. Useful for isolated feature development.",
        {"name": str, "base_branch": str, "prompt": str},
    )
    async def spawn_worktree(args: dict[str, Any]) -> dict[str, Any]:
        """Create a git worktree and spawn an agent in it."""
        if _app is None or _app.agent_mgr is None:
            return _error_response("App not initialized")
        _track_mcp_tool("spawn_worktree")

        name = args["name"]
        prompt = args.get("prompt")

        # Create the worktree
        success, message, wt_path = start_worktree(name)
        if not success or wt_path is None:
            return _error_response(f"Error creating worktree: {message}")

        try:
            # Create agent in the worktree via AgentManager
            agent = await _app.agent_mgr.create(
                name=name, cwd=wt_path, worktree=name, switch_to=False
            )
        except Exception as e:
            return _error_response(
                f"Worktree created at {wt_path}, but agent failed: {e}"
            )

        result = f"Created worktree '{name}' at {wt_path} with new agent"

        if prompt:
            _send_prompt_fire_and_forget(
                agent, prompt, caller_name=caller_name, is_spawn=True
            )
            result += f"\nQueued initial prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}"

        return _text_response(result)

    return spawn_worktree


def _make_message_agent(caller_name: str | None = None):
    """Create message_agent tool with optional caller name bound."""

    @tool(
        "message_agent",
        "Send a message to another agent. By default, expects a reply (the target is nudged if idle without responding). Set requires_answer=false for fire-and-forget messages.",
        {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "message": {"type": "string"},
                "requires_answer": {
                    "type": "boolean",
                    "description": "If true (default), the target agent is expected to reply. Set to false for fire-and-forget messages.",
                },
            },
            "required": ["name", "message"],
        },
    )
    async def message_agent(args: dict[str, Any]) -> dict[str, Any]:
        """Send message to an agent. Non-blocking."""
        if _app is None or _app.agent_mgr is None:
            return _error_response("App not initialized")
        _track_mcp_tool("message_agent")

        name = args["name"]
        message = args["message"]
        requires_answer = args.get("requires_answer", True)

        agent, error = _find_agent_by_name(name)
        if agent is None:
            return _error_response(error or "Agent not found")

        _send_prompt_fire_and_forget(
            agent, message, caller_name=caller_name, expect_reply=requires_answer
        )

        if not requires_answer:
            # Fire-and-forget: clear pending reply if this agent is
            # replying to its caller (same semantics as old tell_agent).
            _clear_pending_reply_if_matched(caller_name, name)

        preview = message[:80] + "..." if len(message) > 80 else message
        return _text_response(f"→ {name}: {preview}")

    return message_agent


def _make_whoami(caller_name: str | None = None):
    """Create whoami tool that returns this agent's name."""

    @tool(
        "whoami",
        "Returns the name of the current agent.",
        {},
    )
    async def whoami(args: dict[str, Any]) -> dict[str, Any]:  # noqa: ARG001
        return _text_response(caller_name or "unknown")

    return whoami


@tool(
    "list_agents",
    "List all agents currently running in claudechic with their status and working directory.",
    {},
)
async def list_agents(args: dict[str, Any]) -> dict[str, Any]:  # noqa: ARG001
    """List all agents and their status."""
    try:
        if _app is None or _app.agent_mgr is None:
            return _error_response("App not initialized")

        if len(_app.agent_mgr) == 0:
            return _text_response("No agents running")

        lines = ["Agents:"]
        for i, agent in enumerate(_app.agent_mgr, 1):
            active = "*" if agent.id == _app.agent_mgr.active_id else " "
            wt = " (worktree)" if agent.worktree else ""
            lines.append(
                f"{active}{i}. {agent.name} [{agent.status}] - {agent.cwd}{wt}"
            )

        return _text_response("\n".join(lines))
    except Exception as e:
        log.exception("list_agents failed")
        return _error_response(f"Failed to list agents: {e}")


@tool(
    "finish_worktree",
    "When you're done working in a worktree, call this to clean it up. Handles committing, rebasing onto the base branch, merging, and removing the worktree. Prefer this over manual git worktree commands.",
    {},
)
async def finish_worktree(args: dict[str, Any]) -> dict[str, Any]:  # noqa: ARG001
    """Start the worktree finish flow for the current agent."""
    try:
        if _app is None or _app.agent_mgr is None:
            return _error_response("App not initialized")
        _track_mcp_tool("finish_worktree")

        agent = _app.agent_mgr.active
        if agent is None:
            return _error_response("No active agent")

        if agent.worktree is None:
            return _error_response(
                "Current agent is not in a worktree. "
                "Use this tool only from a worktree agent."
            )

        # Get finish info
        success, message, info = get_finish_info(agent.cwd)
        if not success or info is None:
            return _error_response(message or "Failed to get finish info")

        # Diagnose current state
        status = diagnose_worktree(info)

        # Store state on agent for continuation after Claude actions
        agent.finish_state = FinishState(
            info=info,
            phase=FinishPhase.RESOLUTION,
            status=status,
        )

        # Process resolution actions, returning instructions for Claude
        return await _process_finish_resolution(agent, info, status)

    except Exception as e:
        log.exception("finish_worktree failed")
        return _error_response(str(e))


async def _process_finish_resolution(
    agent: Any, info: Any, status: Any
) -> dict[str, Any]:
    """Process the finish resolution phase, handling automatic actions.

    Returns MCP response - either success or instructions for Claude.
    """
    # Guard against infinite loops (e.g., gitignored files keep reappearing)
    max_iterations = 10

    for _ in range(max_iterations):
        action = determine_resolution_action(status)

        if action == ResolutionAction.NONE:
            return await _do_cleanup(agent, info)

        if action == ResolutionAction.CLEAN_GITIGNORED:
            success, error = clean_gitignored_files(info.worktree_dir)
            if not success:
                agent.finish_state = None
                return _error_response(f"Error cleaning gitignored files: {error}")
            # Re-diagnose and loop
            status = diagnose_worktree(info)
            agent.finish_state.status = status
            continue

        if action == ResolutionAction.PROMPT_UNCOMMITTED:
            return _text_response(
                "There are uncommitted changes. Please commit all changes with a "
                "descriptive message, then call finish_worktree again to continue."
            )

        if action == ResolutionAction.FAST_FORWARD:
            success, error = fast_forward_merge(info)
            if success:
                return await _do_cleanup(agent, info)
            # Fast-forward failed, fall through to rebase
            return _text_response(
                f"Fast-forward merge failed: {error}\n\n"
                + get_finish_prompt(info)
                + "\n\nAfter completing, call finish_worktree again."
            )

        if action == ResolutionAction.REBASE:
            return _text_response(
                get_finish_prompt(info)
                + "\n\nAfter completing the rebase and merge, call finish_worktree again."
            )

        # Unknown action
        agent.finish_state = None
        return _error_response("Unknown resolution action")

    # Max iterations reached
    agent.finish_state = None
    return _error_response("Too many resolution iterations, aborting")


async def _do_cleanup(agent: Any, info: Any) -> dict[str, Any]:
    """Attempt cleanup and return appropriate response."""

    success, warning = await asyncio.to_thread(finish_cleanup, info)
    if success:
        branch = info.branch_name
        agent.finish_state = None
        await _close_worktree_agent(agent)
        msg = f"Successfully finished worktree '{branch}'"
        if warning:
            msg += f" ({warning})"
        return _text_response(msg)

    # Cleanup failed - ask Claude to fix
    agent.finish_state.phase = FinishPhase.CLEANUP
    return _text_response(
        f"Cleanup failed: {warning}\n\n"
        + get_cleanup_fix_prompt(warning, info.worktree_dir)
        + "\n\nAfter fixing, call finish_worktree again to retry."
    )


async def _close_worktree_agent(agent: Any) -> None:
    """Close a worktree agent after successful finish."""
    if _app is None or _app.agent_mgr is None:
        return

    # Don't close if it's the last agent
    if len(_app.agent_mgr) <= 1:
        return

    # Switch to main agent first if this is the active one
    if _app.agent_mgr.active_id == agent.id:
        main = next(
            (a for a in _app.agent_mgr if a.worktree is None),
            None,
        )
        if main:
            _app.agent_mgr.switch(main.id)

    # Await directly to ensure agent is fully closed before returning
    await _app._close_agent_core(agent.id)


def _make_close_agent(caller_name: str | None = None):
    """Create close_agent tool with caller name bound for safety checks."""

    @tool(
        "close_agent",
        "Close an agent by name. Cannot close the last remaining agent or the calling agent.",
        {"name": str},
    )
    async def close_agent(args: dict[str, Any]) -> dict[str, Any]:
        """Close an agent."""
        try:
            if _app is None or _app.agent_mgr is None:
                return _error_response("App not initialized")

            name = args["name"]

            # Can't close yourself
            if caller_name and name == caller_name:
                return _error_response("An agent cannot close itself")

            # Can't close the last agent
            if len(_app.agent_mgr) <= 1:
                return _error_response("Cannot close the last agent")

            agent, error = _find_agent_by_name(name)
            if agent is None:
                return _error_response(error or "Agent not found")

            agent_id = agent.id
            agent_name = agent.name

            # Await the close directly so the agent count is accurate
            # before this tool returns (prevents race conditions with
            # rapid successive close calls).
            await _app._close_agent_core(agent_id)

            return _text_response(f"Closed agent '{agent_name}'")
        except Exception as e:
            agent_name = args.get("name", "unknown") if args else "unknown"
            log.exception(f"close_agent failed for '{agent_name}'")
            return _error_response(f"Failed to close agent '{agent_name}': {e}")

    return close_agent


def _make_interrupt_agent(caller_name: str | None = None):
    """Create interrupt_agent tool with caller name bound."""

    @tool(
        "interrupt_agent",
        "Interrupt another agent's current task and optionally redirect it "
        "with a new prompt. Awaits the interrupt to completion before sending "
        "any redirect.",
        {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the agent to interrupt",
                },
                "prompt": {
                    "type": "string",
                    "description": "New prompt to send after interrupting (optional)",
                },
            },
            "required": ["name"],
        },
    )
    async def interrupt_agent(args: dict[str, Any]) -> dict[str, Any]:
        """Interrupt an agent, optionally redirecting with a new prompt."""
        try:
            if _app is None or _app.agent_mgr is None:
                return _error_response("App not initialized")
            _track_mcp_tool("interrupt_agent")

            name = args["name"]
            prompt = args.get("prompt")

            # Self-interrupt prevention
            if caller_name and name == caller_name:
                return _error_response("An agent cannot interrupt itself")

            agent, error = _find_agent_by_name(name)
            if agent is None:
                return _error_response(error or "Agent not found")

            # Idle agent: skip interrupt, optionally send prompt
            if agent.status == AgentStatus.IDLE:
                if prompt:
                    _send_prompt_fire_and_forget(agent, prompt, caller_name=caller_name)
                    return _text_response(f"Agent '{name}' was idle; sent new prompt")
                return _text_response(f"Agent '{name}' is not currently busy")

            # Busy agent: await interrupt to completion
            try:
                await agent.interrupt()
            except Exception as exc:
                log.exception(f"interrupt_agent: interrupt failed for '{name}'")
                return _error_response(f"Failed to interrupt '{name}': {exc}")

            # Redirect with new prompt if provided
            if prompt:
                wrapped = prompt
                if caller_name:
                    wrapped = f"[Redirected by agent '{caller_name}']\n\n{prompt}"
                # Fire-and-forget: don't block MCP handler.
                # caller_name=None because we already wrapped the prefix.
                _send_prompt_fire_and_forget(agent, wrapped)
                return _text_response(f"Interrupted '{name}' and sent new prompt")

            return _text_response(f"Interrupted '{name}'")

        except Exception as exc:
            log.exception(f"interrupt_agent failed for '{args.get('name', 'unknown')}'")
            return _error_response(
                f"Failed to interrupt '{args.get('name', 'unknown')}': {exc}"
            )

    return interrupt_agent


@dataclass(frozen=True)
class TieredMCPTool:
    """An MCP tool plus the tier where it was discovered.

    The SDK ships its own tool object type (``SdkMcpTool``); this wrapper
    is the single source of tier-binding for MCP tools (which are
    SDK-owned objects we cannot stamp a ``tier`` field on).
    """

    tool: Any  # claude_agent_sdk.SdkMcpTool — kept loose to avoid imports.
    tier: Tier


def _load_one_tier_mcp_tools(
    tier: Tier,
    mcp_tools_dir: Path,
    **kwargs: Any,
) -> list[TieredMCPTool]:
    """Walk one tier's ``mcp_tools/`` and return tier-stamped tools."""
    out: list[TieredMCPTool] = []
    if not mcp_tools_dir.is_dir():
        return out

    # Pre-load helper modules (underscore-prefixed) so tool files can import
    # them. Tier-namespaced sys.modules keys avoid collisions across tiers
    # for the discovery isolation; we ALSO alias each helper under the
    # legacy `mcp_tools.<stem>` key so existing bundled scripts that do
    # `from mcp_tools._foo import bar` continue to resolve. The package
    # tier is loaded first, so its helpers win the legacy namespace.
    if "mcp_tools" not in sys.modules:
        # Lightweight namespace package so attribute access works.
        import types

        sys.modules["mcp_tools"] = types.ModuleType("mcp_tools")
    for py_file in sorted(mcp_tools_dir.glob("_*.py")):
        if py_file.name == "__init__.py":
            continue
        module_name = f"mcp_tools.{tier}.{py_file.stem}"
        legacy_name = f"mcp_tools.{py_file.stem}"
        try:
            spec = importlib.util.spec_from_file_location(module_name, py_file)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                # Alias under the legacy key only if no other tier has
                # already claimed it (highest-priority-wins for package).
                sys.modules.setdefault(legacy_name, module)
                spec.loader.exec_module(module)
        except Exception:
            log.warning(
                "mcp_tools: failed to load helper %s (tier=%s)",
                py_file.name,
                tier,
                exc_info=True,
            )

    for py_file in sorted(mcp_tools_dir.glob("*.py")):
        if py_file.name.startswith("_"):
            continue

        module_name = f"mcp_tools.{tier}.{py_file.stem}"
        try:
            spec = importlib.util.spec_from_file_location(module_name, py_file)
            if spec is None or spec.loader is None:
                log.warning(
                    "mcp_tools: could not load spec for %s (tier=%s)",
                    py_file.name,
                    tier,
                )
                continue

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            get_tools_fn = getattr(module, "get_tools", None)
            if get_tools_fn is None:
                log.debug(
                    "mcp_tools: %s has no get_tools(), skipping (tier=%s)",
                    py_file.name,
                    tier,
                )
                continue

            file_tools = get_tools_fn(**kwargs)
            for t in file_tools:
                out.append(TieredMCPTool(tool=t, tier=tier))
            log.info(
                "mcp_tools: loaded %d tool(s) from %s (tier=%s)",
                len(file_tools),
                py_file.name,
                tier,
            )

        except Exception:
            log.warning(
                "mcp_tools: failed to load %s, skipping (tier=%s)",
                py_file.name,
                tier,
                exc_info=True,
            )
            continue

    return out


def discover_mcp_tools(tier_roots: TierRoots, **kwargs: Any) -> list[TieredMCPTool]:
    """Walk every tier's ``mcp_tools/`` and resolve overrides by tool name.

    Iterates package -> user -> project. Within each tier, every ``*.py``
    that exposes a ``get_tools(**kwargs)`` callable contributes tools.
    Cross-tier collisions on ``tool.name`` resolve highest-priority-wins
    (project > user > package); lower-tier tools of the same name are
    silently dropped.

    Returns:
        Tier-stamped tools (one entry per resolved name). Caller registers
        ``[t.tool for t in result]`` with the SDK and consumes ``t.tier``
        for provenance.
    """
    by_tier: dict[Tier, list[TieredMCPTool]] = {}
    # Iterate package -> user -> project so logs are deterministic.
    for tier in ("package", "user", "project"):
        root = tier_roots.get(tier)  # type: ignore[arg-type]
        if root is None:
            continue
        by_tier[tier] = _load_one_tier_mcp_tools(  # type: ignore[arg-type]
            tier,  # type: ignore[arg-type]
            root / "mcp_tools",
            **kwargs,
        )

    # Highest-priority-wins resolution by tool.name.
    resolved: dict[str, TieredMCPTool] = {}
    for tier in ("project", "user", "package"):
        for tt in by_tier.get(tier, []):  # type: ignore[arg-type]
            name = getattr(tt.tool, "name", None)
            if name is None:
                # Tool without a name attribute — keep it (no override possible).
                resolved.setdefault(f"__unnamed:{id(tt.tool)}", tt)
                continue
            resolved.setdefault(name, tt)

    return list(resolved.values())


def _format_tool_input(tool_input: dict) -> str:
    """Format tool_input dict for display in override prompts."""
    import json

    try:
        return json.dumps(tool_input, indent=2, default=str)[:500]
    except Exception:
        return str(tool_input)[:500]


# --- Workflow MCP tools ---


def _make_advance_phase(caller_name: str | None = None):
    """Create advance_phase tool with caller name bound."""

    @tool(
        "advance_phase",
        "Advance the active workflow to its next phase. Engine runs advance_checks (AND semantics, short-circuit). Returns whether the transition succeeded.",
        {},
    )
    async def advance_phase(args: dict[str, Any]) -> dict[str, Any]:  # noqa: ARG001
        """Attempt to advance the active workflow to its next phase."""
        if _app is None or _app._workflow_engine is None:
            return _error_response("No active workflow")
        _track_mcp_tool("advance_phase")

        engine = _app._workflow_engine

        # Resolve calling agent for NEEDS_INPUT status
        caller_agent = None
        if caller_name and _app.agent_mgr:
            caller_agent = _app.agent_mgr.find_by_name(caller_name)

        # Temporarily set agent-aware confirm callback
        original_cb = engine._confirm_callback
        engine._confirm_callback = _app._make_confirm_callback(agent=caller_agent)
        try:
            current = engine.get_current_phase()
            if current is None:
                return _error_response("No current phase set")

            next_phase = engine.get_next_phase(current)
            if next_phase is None:
                return _error_response(
                    f"No phase after '{current}' -- already at final phase"
                )

            result = await engine.attempt_phase_advance(
                workflow_id=engine.workflow_id,
                current_phase=current,
                next_phase=next_phase,
                advance_checks=engine.get_advance_checks_for(current),
            )

            if result.success:
                # Build phase prompt content synchronously so the calling agent
                # gets the new phase instructions in the tool response (not later
                # via async broadcast, which caused BUG #1: late/out-of-order
                # phase injections).
                phase_content = ""
                main_role = getattr(engine.manifest, "main_role", None)
                if main_role:
                    try:
                        from claudechic.workflows.agent_folders import (
                            assemble_phase_prompt,
                        )

                        wf_data = (
                            _app._load_result.get_workflow(engine.workflow_id)
                            if _app._load_result is not None
                            else None
                        )
                        if wf_data is not None:
                            phase_content = (
                                assemble_phase_prompt(
                                    workflow_dir=wf_data.path,
                                    role_name=main_role,
                                    current_phase=next_phase,
                                    artifact_dir=engine.get_artifact_dir(),
                                )
                                or ""
                            )
                    except Exception:
                        log.debug(
                            "Failed to assemble phase prompt for advance_phase response",
                            exc_info=True,
                        )

                    # The coordinator (caller) already received the phase
                    # prompt inline via the tool response above, and the
                    # broadcast loop below delivers to typed sub-agents.
                    # Skip _inject_phase_prompt_to_main_agent here to
                    # avoid double-injection on the coordinator (per SPEC
                    # §4.7 + test_advance_phase_no_double_agent_prompt_for_coordinator).
                    # Sidebar phase label still needs refreshing.
                    _app._update_sidebar_workflow_info()

                # Broadcast phase prompt to typed sub-agents.
                # D5 inject site (sub-agent phase-advance broadcast): route through
                # ``assemble_agent_prompt`` so each sub-agent's phase-advance
                # prompt embeds its role+phase scoped ``## Constraints`` block
                # (symmetric with the spawn-time, activation, main-agent-advance,
                # and post-compact inject sites).
                if _app.agent_mgr:
                    from claudechic.workflows.agent_folders import (
                        assemble_agent_prompt,
                    )

                    wf_data_b = (
                        _app._load_result.get_workflow(engine.workflow_id)
                        if _app._load_result is not None
                        else None
                    )
                    loader_b = getattr(_app, "_manifest_loader", None)
                    # D6 alignment: pull the merged disabled_ids set from
                    # the app so phase-broadcast constraints match what
                    # the hook layer fires on and what the registry tools
                    # report. Computed once outside the loop -- the set
                    # is invariant across recipients.
                    get_disabled = getattr(_app, "_get_disabled_rules", None)
                    disabled_rules_b = (
                        get_disabled() if callable(get_disabled) else None
                    )
                    for agent in list(_app.agent_mgr.agents.values()):
                        # Skip coordinator (already got content in tool response)
                        if main_role and agent.agent_type == main_role:
                            continue
                        # Skip untyped agents (agents with no workflow-specific
                        # role get DEFAULT_ROLE as their sentinel; they should
                        # not receive role-scoped phase broadcasts).
                        if agent.agent_type == DEFAULT_ROLE:
                            continue
                        # Skip the calling agent (coordinator calling advance)
                        if caller_name and agent.name == caller_name:
                            continue
                        if wf_data_b is None:
                            continue
                        try:
                            agent_prompt = assemble_agent_prompt(
                                agent.agent_type,
                                next_phase,
                                loader_b,
                                workflow_dir=wf_data_b.path,
                                artifact_dir=engine.get_artifact_dir(),
                                project_root=getattr(engine, "project_root", None),
                                engine=engine,
                                active_workflow=engine.workflow_id,
                                disabled_rules=disabled_rules_b,
                            )
                            if agent_prompt:
                                _send_prompt_fire_and_forget(
                                    agent,
                                    f"--- Phase Update: {next_phase} ---\n\n{agent_prompt}",
                                    caller_name=None,
                                )
                        except Exception:
                            log.debug(
                                "Failed to broadcast phase prompt to '%s'",
                                agent.name,
                                exc_info=True,
                            )

                response = f"Advanced to phase: {next_phase}"
                if phase_content:
                    response += f"\n\n--- Phase Instructions ---\n\n{phase_content}"
                return _text_response(response)
            else:
                return _error_response(f"Advance blocked: {result.reason}")
        finally:
            engine._confirm_callback = original_cb

    return advance_phase


@tool(
    "set_artifact_dir",
    (
        "Bind an artifact directory to the active workflow run. Coordinator "
        "agents call this once during a Setup-style phase to choose the "
        "on-disk location where workflow artifacts (specs, plans, status, "
        "hand-off material) are written. Accepts an absolute path, or a "
        "relative path resolved against the launched-repo root. Rejects "
        "paths inside any '.claude/' directory. Idempotent on the same "
        "resolved path; raises on a different path once one is set. "
        "Returns the resolved absolute path string."
    ),
    {"path": str},
)
async def set_artifact_dir(args: dict[str, Any]) -> dict[str, Any]:
    """Bind an artifact directory to the active workflow."""
    if _app is None or _app._workflow_engine is None:
        return _error_response(
            "No active workflow. set_artifact_dir requires an active workflow run."
        )
    _track_mcp_tool("set_artifact_dir")

    path = args.get("path")
    if not isinstance(path, str):
        return _error_response("set_artifact_dir requires a string 'path' argument")

    try:
        resolved = await _app._workflow_engine.set_artifact_dir(path)
    except (ValueError, RuntimeError) as e:
        return _error_response(str(e))
    except Exception as e:
        log.exception("set_artifact_dir failed")
        return _error_response(f"set_artifact_dir failed: {e}")

    return _text_response(str(resolved))


@tool(
    "get_artifact_dir",
    (
        "Return the active workflow's artifact directory as an absolute "
        "path string, or JSON null if no artifact directory has been set "
        "yet. Any agent may call this at any time during their turn."
    ),
    {},
)
async def get_artifact_dir(args: dict[str, Any]) -> dict[str, Any]:  # noqa: ARG001
    """Return the active workflow's artifact directory or null."""
    if _app is None or _app._workflow_engine is None:
        return _error_response(
            "No active workflow. get_artifact_dir requires an active workflow run."
        )
    _track_mcp_tool("get_artifact_dir")

    artifact_dir = _app._workflow_engine.get_artifact_dir()
    if artifact_dir is None:
        # JSON null on the wire — separate content type from text so
        # callers can distinguish "not set" from the literal string "null".
        return {
            "content": [{"type": "text", "text": "null"}],
            "structuredContent": None,
        }
    return _text_response(str(artifact_dir))


def _render_phase_status_lines(engine: Any) -> list[str]:
    """Return plain-text status lines describing the active workflow phase.

    Shared between ``get_phase`` (narrow tool) and ``get_agent_info``
    (aggregator) so both tools agree on what "current phase" means.
    """
    lines: list[str] = []
    if engine is None:
        lines.append("Workflow: none active")
        return lines

    current = engine.get_current_phase()
    next_phase = engine.get_next_phase(current) if current else None
    phase_order = getattr(engine, "_phase_order", None) or []

    lines.append(f"Workflow: {engine.workflow_id}")
    lines.append(f"Phase: {current or '(none)'}")
    if next_phase:
        lines.append(f"Next phase: {next_phase}")
    if phase_order:
        idx = (
            phase_order.index(current) + 1 if current and current in phase_order else 0
        )
        lines.append(f"Progress: {idx}/{len(phase_order)} ({', '.join(phase_order)})")
    artifact_dir = getattr(engine, "get_artifact_dir", lambda: None)()
    if artifact_dir is not None:
        lines.append(f"Artifact dir: {artifact_dir}")
    return lines


def _render_loader_error_lines(loader: Any) -> list[str]:
    """Return plain-text loader-error lines, or a single status line.

    Shared between ``get_phase`` and ``get_agent_info``. Reads
    ``loader.load().errors`` and surfaces up to five errors. Uses the same
    source of truth (``loader.load()``) the guardrail hook layer reads
    from -- both layers see the same set of loader errors per the D6
    source-of-truth alignment.
    """
    if loader is None:
        return ["Loader: not initialized"]
    try:
        result = loader.load()
    except Exception as e:
        return [f"Loader: load() raised: {e}"]
    if not result.errors:
        return []
    out: list[str] = [f"Errors: {len(result.errors)}"]
    for err in result.errors[:5]:
        out.append(f"  - {err.source}: {err.message}")
    return out


@tool(
    "get_phase",
    (
        "Get the narrow workflow state: active workflow id, current phase, "
        "next phase, progress index, artifact directory, and any loader "
        "errors. The per-agent role+phase projection of rules and "
        "advance-checks lives in mcp__chic__get_applicable_rules; this "
        "tool stays narrow."
    ),
    {},
)
async def get_phase(args: dict[str, Any]) -> dict[str, Any]:  # noqa: ARG001
    """Get current workflow state -- narrow shape (no rule projection)."""
    if _app is None:
        return _text_response("No app context.")
    _track_mcp_tool("get_phase")

    engine = getattr(_app, "_workflow_engine", None)
    loader = getattr(_app, "_manifest_loader", None)

    lines: list[str] = list(_render_phase_status_lines(engine))
    lines.extend(_render_loader_error_lines(loader))

    return _text_response("\n".join(lines))


# ---------------------------------------------------------------------------
# Agent-self-awareness MCP surface (D4)
#
# Three tools compose to deliver "what applies to me right now?":
# - ``whoami``             -- existing, narrow, retained verbatim.
# - ``get_phase``          -- existing, narrow, just lost the rule-count line.
# - ``get_applicable_rules``  -- NEW, narrow, per-agent rule + advance-check
#   projection as the markdown ``## Constraints`` block.
# - ``get_agent_info``     -- NEW, aggregator. Calls the three narrow tools
#   internally and concatenates their output into a unified markdown report.
# ---------------------------------------------------------------------------


def _resolve_agent_for_tool(agent_name: str | None, caller_name: str | None):
    """Resolve which agent a tool is operating on.

    Mirrors the closure-bound resolution pattern used by ``whoami`` /
    ``spawn_agent``: when ``agent_name`` is omitted, falls back to the
    calling agent's name; otherwise looks up via ``find_by_name``.

    Returns ``(agent, name, error)`` -- ``agent`` may be ``None`` even
    on success when the calling agent has not been registered yet.
    """
    if _app is None or _app.agent_mgr is None:
        return None, None, "App not initialized"

    target_name = agent_name or caller_name
    if not target_name:
        return None, None, "No agent name available (caller unknown)"

    agent = _app.agent_mgr.find_by_name(target_name)
    if agent is None:
        return (
            None,
            target_name,
            f"Agent '{target_name}' not found. Use list_agents to see "
            "available agents.",
        )
    return agent, target_name, None


def _read_last_compact_summary(jsonl_path: Path) -> str | None:
    """Return the last ``isCompactSummary`` content from a session JSONL.

    Local helper so this module does not import the
    (about-to-be-deleted) ``widgets.modals.diagnostics`` module. Same
    semantics as that module's reader.
    """
    import json

    if not jsonl_path.is_file():
        return None
    try:
        last_summary: str | None = None
        with jsonl_path.open(encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or "isCompactSummary" not in line:
                    continue
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if msg.get("isCompactSummary"):
                    content = msg.get("message", {}).get("content", "")
                    if isinstance(content, str) and content:
                        last_summary = content
        return last_summary
    except OSError:
        return None


def _make_get_applicable_rules(caller_name: str | None = None):
    """Create the ``get_applicable_rules`` tool with caller bound."""

    @tool(
        "get_applicable_rules",
        (
            "Return the role+phase scoped projection of guardrail rules and "
            "advance-checks for an agent, rendered as the markdown ## Constraints "
            "block. When agent_name is omitted, projects against the calling "
            "agent. include_skipped=true adds a skip_reason column and inactive "
            "rows for audit views."
        ),
        {
            "type": "object",
            "properties": {
                "agent_name": {
                    "type": "string",
                    "description": (
                        "Name of the agent to project against. Defaults to the "
                        "calling agent."
                    ),
                },
                "include_skipped": {
                    "type": "boolean",
                    "description": (
                        "If true, include inactive rules with a skip_reason "
                        "column. Default false (active rules only)."
                    ),
                },
            },
            "required": [],
        },
    )
    async def get_applicable_rules(args: dict[str, Any]) -> dict[str, Any]:
        if _app is None:
            return _error_response("App not initialized")
        _track_mcp_tool("get_applicable_rules")

        agent_name = args.get("agent_name")
        include_skipped = bool(args.get("include_skipped", False))

        agent, _resolved, error = _resolve_agent_for_tool(agent_name, caller_name)
        if error and agent is None:
            return _error_response(error)

        engine = getattr(_app, "_workflow_engine", None)
        loader = getattr(_app, "_manifest_loader", None)
        active_workflow = engine.workflow_id if engine is not None else None
        current_phase = engine.get_current_phase() if engine is not None else None
        role = (
            getattr(agent, "agent_type", DEFAULT_ROLE)
            if agent is not None
            else DEFAULT_ROLE
        )

        try:
            from claudechic.workflows.agent_folders import (
                assemble_constraints_block,
            )
        except Exception as e:
            log.exception("get_applicable_rules: failed to import helper")
            return _error_response(f"assemble_constraints_block unavailable: {e}")

        try:
            # D6 alignment: pull the merged disabled_ids set from the
            # app so this tool's projection matches what the hook layer
            # fires on, what the four prompt-injection sites embed, and
            # what get_agent_info aggregates. Helper is exposed by slot 4.
            get_disabled = getattr(_app, "_get_disabled_rules", None)
            disabled_rules_app = get_disabled() if callable(get_disabled) else None
            block = assemble_constraints_block(
                loader,
                role,
                current_phase,
                engine=engine,
                active_workflow=active_workflow,
                include_skipped=include_skipped,
                disabled_rules=disabled_rules_app,
            )
        except Exception as e:
            log.exception("get_applicable_rules: assembly failed")
            return _error_response(f"Failed to assemble constraints block: {e}")

        return _text_response(block)

    return get_applicable_rules


def _render_identity_section(agent: Any, name: str) -> list[str]:
    """Render the ``## Identity`` markdown lines for ``get_agent_info``."""
    lines: list[str] = ["## Identity", ""]
    if agent is None:
        lines.append(f"- name: {name}")
        lines.append("- (agent not registered)")
        return lines

    role = getattr(agent, "agent_type", DEFAULT_ROLE) or DEFAULT_ROLE
    cwd = getattr(agent, "cwd", None)
    model = getattr(agent, "model", None)
    effort = getattr(agent, "effort", None)
    worktree = getattr(agent, "worktree", None)
    status = getattr(agent, "status", None)

    lines.append(f"- name: {name}")
    lines.append(f"- role (agent_type): {role}")
    lines.append(f"- cwd: {cwd if cwd is not None else '(unknown)'}")
    lines.append(f"- model: {model if model is not None else '(default)'}")
    lines.append(f"- effort: {effort if effort is not None else '(default)'}")
    lines.append(f"- worktree: {worktree if worktree else '(none)'}")
    lines.append(f"- status: {status if status is not None else '(unknown)'}")
    return lines


def _render_session_section(agent: Any) -> list[str]:
    """Render the ``## Session`` markdown lines for ``get_agent_info``."""
    lines: list[str] = ["## Session", ""]
    if agent is None:
        lines.append("- (agent not registered)")
        return lines

    session_id = getattr(agent, "session_id", None)
    cwd = getattr(agent, "cwd", None)

    jsonl_path: Path | None = None
    if session_id:
        try:
            from claudechic.sessions import get_project_sessions_dir

            sessions_dir = get_project_sessions_dir(cwd)
            if sessions_dir is not None:
                jsonl_path = sessions_dir / f"{session_id}.jsonl"
        except Exception:
            log.debug("Failed to resolve session JSONL path", exc_info=True)
            jsonl_path = None

    lines.append(f"- session_id: {session_id or '(no active session)'}")
    lines.append(
        f"- jsonl_path: {jsonl_path if jsonl_path is not None else '(unknown)'}"
    )

    last_summary: str | None = None
    if jsonl_path is not None:
        last_summary = _read_last_compact_summary(jsonl_path)
    if last_summary:
        preview = last_summary[:200]
        suffix = "..." if len(last_summary) > 200 else ""
        lines.append(f"- last compaction: {preview}{suffix}")
    else:
        lines.append("- last compaction: (none)")
    return lines


def _make_get_agent_info(caller_name: str | None = None):
    """Create the ``get_agent_info`` aggregator tool with caller bound."""

    @tool(
        "get_agent_info",
        (
            "Aggregator: returns a unified markdown report for an agent, "
            "concatenating identity, session, active workflow + phase, the "
            "## Constraints block (rules + advance-checks scoped to the "
            "agent's role + phase), and loader errors. When agent_name is "
            "omitted, reports on the calling agent. Owns no rule-resolution "
            "logic of its own -- delegates to assemble_constraints_block, "
            "the same helper get_applicable_rules and the prompt-injection "
            "sites use."
        ),
        {
            "type": "object",
            "properties": {
                "agent_name": {
                    "type": "string",
                    "description": (
                        "Name of the agent to report on. Defaults to the calling agent."
                    ),
                },
            },
            "required": [],
        },
    )
    async def get_agent_info(args: dict[str, Any]) -> dict[str, Any]:
        if _app is None:
            return _error_response("App not initialized")
        _track_mcp_tool("get_agent_info")

        agent_name = args.get("agent_name")
        agent, resolved_name, error = _resolve_agent_for_tool(agent_name, caller_name)
        if error and agent is None:
            return _error_response(error)
        display_name = resolved_name or "(unknown)"

        engine = getattr(_app, "_workflow_engine", None)
        loader = getattr(_app, "_manifest_loader", None)
        active_workflow = engine.workflow_id if engine is not None else None
        current_phase = engine.get_current_phase() if engine is not None else None
        role = (
            getattr(agent, "agent_type", DEFAULT_ROLE)
            if agent is not None
            else DEFAULT_ROLE
        )

        sections: list[str] = []

        # 1. # Agent: <name>
        sections.append(f"# Agent: {display_name}")
        sections.append("")

        # 2. ## Identity
        sections.extend(_render_identity_section(agent, display_name))
        sections.append("")

        # 3. ## Session
        sections.extend(_render_session_section(agent))
        sections.append("")

        # 4. ## Active workflow + phase
        sections.append("## Active workflow + phase")
        sections.append("")
        for line in _render_phase_status_lines(engine):
            sections.append(f"- {line}")
        sections.append("")

        # 5. ## Constraints (rules + advance-checks)
        # Delegate to ``assemble_constraints_block`` so the aggregator
        # cannot fork on rule-projection logic. Same source of truth as
        # ``get_applicable_rules`` and the four prompt-injection sites.
        # Option (a) wrapper: keep the helper's outer ``## Constraints``
        # heading and drop the three separate aggregator headings
        # (Applicable guardrail rules / Applicable injections / Advance
        # checks for the current phase). The constraints block already
        # interleaves rules + injections in one table and surfaces the
        # advance-checks subsection.
        try:
            from claudechic.workflows.agent_folders import (
                assemble_constraints_block,
            )

            # D6 alignment: pull the merged disabled_ids set from the
            # app so the get_agent_info aggregator surfaces the same
            # active/inactive set as get_applicable_rules and the four
            # prompt-injection sites. Helper is exposed by slot 4.
            get_disabled = getattr(_app, "_get_disabled_rules", None)
            disabled_rules_info = get_disabled() if callable(get_disabled) else None
            constraints_block = assemble_constraints_block(
                loader,
                role,
                current_phase,
                engine=engine,
                active_workflow=active_workflow,
                disabled_rules=disabled_rules_info,
            )
        except Exception:
            log.debug(
                "get_agent_info: assemble_constraints_block failed", exc_info=True
            )
            constraints_block = ""

        if constraints_block.strip():
            sections.append(constraints_block.rstrip())
        else:
            # Degenerate: no rules and no advance-checks. Emit the
            # outer heading so the section is visibly present.
            sections.append("## Constraints")
            sections.append("")
            sections.append("_No rules apply and no advance checks for this phase._")
        sections.append("")

        # 6. ## Loader errors
        sections.append("## Loader errors")
        sections.append("")
        err_lines = _render_loader_error_lines(loader)
        if err_lines:
            for line in err_lines:
                sections.append(f"- {line}")
        else:
            sections.append("_No loader errors._")

        return _text_response("\n".join(sections).rstrip() + "\n")

    return get_agent_info


def _make_request_override(caller_name: str | None = None):
    """Create request_override tool with caller name bound."""

    @tool(
        "request_override",
        "Request user approval to override a deny-level rule. User sees the exact command. If approved, stores a one-time token -- retry the exact same command to execute it.",
        {
            "type": "object",
            "properties": {
                "rule_id": {
                    "type": "string",
                    "description": "The qualified ID of the blocking rule (from block message)",
                },
                "tool_name": {
                    "type": "string",
                    "description": "The tool that was blocked",
                },
                "tool_input": {
                    "type": "object",
                    "description": "The exact tool input dict that was blocked",
                },
            },
            "required": ["rule_id", "tool_name", "tool_input"],
        },
    )
    async def request_override(args: dict[str, Any]) -> dict[str, Any]:
        """Request user approval to override a deny-level rule."""
        if _app is None or _app._token_store is None:
            return _error_response("App not initialized")
        _track_mcp_tool("request_override")

        rule_id = args["rule_id"]
        tool_name = args["tool_name"]
        tool_input = args.get("tool_input", {})

        description = (
            f"Agent wants to run blocked action:\n"
            f"  Tool: {tool_name}\n"
            f"  Input: {_format_tool_input(tool_input)}\n"
            f"  Blocked by: {rule_id}\n"
            f"Approve this specific action?"
        )

        # Resolve calling agent for NEEDS_INPUT status
        caller_agent = None
        if caller_name and _app.agent_mgr:
            caller_agent = _app.agent_mgr.find_by_name(caller_name)

        approved = await _app._show_override_prompt(
            rule_id,
            description,
            agent=caller_agent,
        )

        if approved:
            _app._token_store.store(rule_id, tool_name, tool_input, enforcement="deny")
            return _text_response(
                f"Override approved for rule {rule_id}. Retry the exact same command."
            )
        else:
            return _text_response("Override denied.")

    return request_override


@tool(
    "acknowledge_warning",
    "Acknowledge a warn-level rule to proceed past it. Stores a one-time token. Retry the exact same command to execute it. No user interaction required.",
    {
        "type": "object",
        "properties": {
            "rule_id": {
                "type": "string",
                "description": "The qualified ID of the warning rule (from block message)",
            },
            "tool_name": {
                "type": "string",
                "description": "The tool that was blocked",
            },
            "tool_input": {
                "type": "object",
                "description": "The exact tool input dict that was blocked",
            },
        },
        "required": ["rule_id", "tool_name", "tool_input"],
    },
)
async def acknowledge_warning(args: dict[str, Any]) -> dict[str, Any]:
    """Acknowledge a warn-level rule to proceed past it."""
    if _app is None or _app._token_store is None:
        return _error_response("App not initialized")
    _track_mcp_tool("acknowledge_warning")

    rule_id = args["rule_id"]
    tool_name = args["tool_name"]
    tool_input = args.get("tool_input", {})

    _app._token_store.store(rule_id, tool_name, tool_input, enforcement="warn")
    return _text_response(
        f"Warning acknowledged for rule {rule_id}. Retry the exact same command."
    )


def create_chic_server(
    caller_name: str | None = None,
    tier_roots: TierRoots | None = None,
):
    """Create the chic MCP server with all tools.

    Args:
        caller_name: Name of the agent that will use this server.
            Used to identify the sender in spawn/message agent calls.
        tier_roots: Three-tier roots for ``mcp_tools/`` discovery. If
            ``None``, falls back to ``_app._tier_roots`` (set at app
            startup) — preserves the convenience API for tests.
    """
    tools = [
        _make_spawn_agent(caller_name),
        _make_spawn_worktree(caller_name),
        _make_message_agent(caller_name),
        _make_whoami(caller_name),
        list_agents,
        _make_close_agent(caller_name),
        _make_interrupt_agent(caller_name),
        # Workflow guidance tools
        _make_advance_phase(caller_name),
        get_phase,
        _make_get_applicable_rules(caller_name),
        _make_get_agent_info(caller_name),
        set_artifact_dir,
        get_artifact_dir,
        _make_request_override(caller_name),
        acknowledge_warning,
    ]

    # finish_worktree is experimental - enable with experimental.finish_worktree: true
    if CONFIG.get("experimental", {}).get("finish_worktree", False):
        tools.append(finish_worktree)

    # LSF cluster tools (always registered; LSF availability checked at runtime)
    try:
        from claudechic.cluster import (
            _make_cluster_watch,
            cluster_jobs,
            cluster_kill,
            cluster_status,
            cluster_submit,
        )

        tools.extend(
            [
                cluster_jobs,
                cluster_status,
                cluster_submit,
                cluster_kill,
                _make_cluster_watch(
                    caller_name=caller_name,
                    send_notification=_send_prompt_fire_and_forget,
                    find_agent=_find_agent_by_name,
                ),
            ]
        )
    except ImportError:
        log.debug("Cluster tools not available (missing dependencies)")

    # Discover mcp_tools/ plugins across all three tiers.
    effective_tier_roots = tier_roots
    if effective_tier_roots is None and _app is not None:
        effective_tier_roots = getattr(_app, "_tier_roots", None)
    if effective_tier_roots is not None:
        discovered_tools = discover_mcp_tools(
            effective_tier_roots,
            caller_name=caller_name,
            send_notification=_send_prompt_fire_and_forget,
            find_agent=_find_agent_by_name,
        )
        tools.extend(t.tool for t in discovered_tools)

    return create_sdk_mcp_server(
        name="chic",
        version="1.0.0",
        tools=tools,
    )
