"""Registration gate for the browser control tools (layer 1 of the gate).

The five ``browser_*`` tools must NOT be registered on the chic MCP
server unless ``experimental.browser: true`` is set in user config.
No playwright install is needed here: all playwright imports in
``features/browser/`` are lazy.
"""

from __future__ import annotations

import claudechic.mcp as mcp_mod
from claudechic.config import CONFIG

BROWSER_TOOL_NAMES = {
    "browser_navigate",
    "browser_screenshot",
    "browser_click",
    "browser_type",
    "browser_scroll",
}


def _registered_tool_names(monkeypatch) -> set[str]:
    """Build the chic server with a stubbed SDK factory; return tool names."""
    captured: dict[str, list] = {}

    def fake_create_sdk_mcp_server(name, version, tools):
        captured["tools"] = tools
        return {"name": name, "version": version}

    monkeypatch.setattr(mcp_mod, "create_sdk_mcp_server", fake_create_sdk_mcp_server)
    # Isolate from any app state other tests may have registered.
    monkeypatch.setattr(mcp_mod, "_app", None)
    mcp_mod.create_chic_server(caller_name="test-agent")
    return {t.name for t in captured["tools"]}


def test_browser_tools_absent_by_default(monkeypatch):
    """Off means invisible: no browser_* tools without the config key."""
    monkeypatch.setitem(CONFIG, "experimental", {})
    names = _registered_tool_names(monkeypatch)
    assert not (names & BROWSER_TOOL_NAMES), (
        f"browser tools registered without experimental.browser: "
        f"{names & BROWSER_TOOL_NAMES}"
    )


def test_browser_tools_absent_when_explicitly_false(monkeypatch):
    monkeypatch.setitem(CONFIG, "experimental", {"browser": False})
    names = _registered_tool_names(monkeypatch)
    assert not (names & BROWSER_TOOL_NAMES)


def test_browser_tools_registered_when_enabled(monkeypatch):
    """experimental.browser: true registers all five tools."""
    monkeypatch.setitem(CONFIG, "experimental", {"browser": True})
    names = _registered_tool_names(monkeypatch)
    missing = BROWSER_TOOL_NAMES - names
    assert not missing, f"missing browser tools despite gate on: {missing}"


def test_gate_does_not_disturb_core_tools(monkeypatch):
    """Core agent-control tools are present regardless of the gate."""
    monkeypatch.setitem(CONFIG, "experimental", {"browser": True})
    names = _registered_tool_names(monkeypatch)
    assert {"spawn_agent", "message_agent", "whoami"} <= names
