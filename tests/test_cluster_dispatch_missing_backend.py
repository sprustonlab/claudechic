"""Regression test for cluster_dispatch.py missing-backend handling.

Covers manifest rows for ``claudechic/defaults/mcp_tools/cluster_dispatch.py``
at lines 123, 152, 231, 253, 290, 347 (all
``reportOptionalMemberAccess``), classified ``disposition = real-bug``.

Root cause: ``_get_backend_module(backend)`` returns ``None`` when the
sibling ``_<backend>.py`` file is missing or its importlib spec/loader
is ``None``. Six call sites previously dereferenced ``mod._<method>``
without a None guard, raising
``AttributeError: 'NoneType' object has no attribute '_<method>'``.

The fix introduces ``_require_backend_module(backend)`` which raises
``BackendNotAvailable`` with an actionable message; the existing
per-tool ``try / except Exception`` block (or one added to
``cluster_watch``) catches the exception and returns a structured error
response naming the missing backend.

This regression test forces ``_get_backend_module`` to return ``None``
and asserts each of the six tool handlers returns a structured error
response (``isError = True``) whose message names the missing backend
-- not the bare ``NoneType`` AttributeError text.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MCP_TOOLS_DIR = REPO_ROOT / "claudechic" / "defaults" / "mcp_tools"


def _load_cluster_dispatch_module() -> types.ModuleType:
    """Import ``cluster_dispatch.py`` standalone, with ``mcp_tools._cluster``
    pre-registered in ``sys.modules`` so the ``from mcp_tools._cluster import ...``
    line at module top resolves.

    Mirrors the loader pattern in ``claudechic/mcp.py`` but scoped to a
    single helper plus the dispatch module, so this test does not depend
    on the full claudechic startup path.
    """
    # Ensure namespace package exists.
    if "mcp_tools" not in sys.modules:
        sys.modules["mcp_tools"] = types.ModuleType("mcp_tools")

    # Pre-load _cluster helper if not already loaded.
    if "mcp_tools._cluster" not in sys.modules:
        helper_file = MCP_TOOLS_DIR / "_cluster.py"
        spec = importlib.util.spec_from_file_location("mcp_tools._cluster", helper_file)
        assert spec is not None and spec.loader is not None
        helper_mod = importlib.util.module_from_spec(spec)
        sys.modules["mcp_tools._cluster"] = helper_mod
        spec.loader.exec_module(helper_mod)

    # Always reload cluster_dispatch fresh so monkeypatch state from prior
    # tests does not leak. Use a unique sys.modules key so we get a clean
    # function-level module object.
    dispatch_file = MCP_TOOLS_DIR / "cluster_dispatch.py"
    spec = importlib.util.spec_from_file_location(
        "mcp_tools.cluster_dispatch_under_test", dispatch_file
    )
    assert spec is not None and spec.loader is not None
    dispatch_mod = importlib.util.module_from_spec(spec)
    sys.modules["mcp_tools.cluster_dispatch_under_test"] = dispatch_mod
    spec.loader.exec_module(dispatch_mod)
    return dispatch_mod


def _extract_error_text(response: dict) -> str:
    """Pull the human-visible text out of an MCP tool response dict."""
    content = response.get("content", [])
    if content and isinstance(content[0], dict):
        return content[0].get("text", "")
    return ""


def _tool_handlers(dispatch_mod: types.ModuleType) -> dict:
    """Instantiate the 6 tools and return a name -> handler dict.

    The ``@tool`` decorator returns ``SdkMcpTool`` instances with
    ``name`` and ``handler`` attributes. We index by name so the test
    can drive each handler directly.
    """
    tools = dispatch_mod.get_tools(
        caller_name="test-caller",
        send_notification=lambda *a, **kw: None,
        find_agent=lambda *a, **kw: None,
    )
    return {t.name: t.handler for t in tools}


@pytest.fixture
def dispatch_with_missing_backend(monkeypatch):
    """Load cluster_dispatch with a stubbed config and a backend that
    cannot be loaded (``_get_backend_module`` returns ``None``)."""
    mod = _load_cluster_dispatch_module()

    # Force the resolution path to behave as if _<backend>.py is absent.
    monkeypatch.setattr(mod, "_get_backend_module", lambda backend: None)

    # Stub config: backend is configured (so we pass the early
    # not-configured / unsupported guards) but the module load fails.
    fake_config = {
        "backend": "lsf",
        "ssh_target": "user@fake.cluster",
        "path_map": [{"local": "/local", "cluster": "/remote"}],
    }
    monkeypatch.setattr(mod, "_load_dispatch_config", lambda: fake_config)
    return mod


def test_missing_backend_module_returns_error(dispatch_with_missing_backend):
    """All 6 cluster_* tool handlers must return a structured error
    response (not raise AttributeError) when the backend module is
    unavailable, and the message must name the missing backend so the
    caller can act on it.
    """
    handlers = _tool_handlers(dispatch_with_missing_backend)

    # Every tool the spec lists must be present; if any are missing,
    # something has changed in the dispatcher and this test must be
    # re-evaluated.
    expected = {
        "cluster_jobs",
        "cluster_status",
        "cluster_submit",
        "cluster_kill",
        "cluster_logs",
        "cluster_watch",
    }
    assert expected <= handlers.keys(), (
        f"missing tool handlers: {expected - handlers.keys()}"
    )

    # Inputs sized to satisfy each tool's required args.
    invocations = {
        "cluster_jobs": {},
        "cluster_status": {"job_id": "12345"},
        "cluster_submit": {
            "queue": "normal",
            "cpus": 1,
            "walltime": "00:10",
            "command": "true",
            "job_name": "t",
            "gpus": 0,
            "stdout_path": "",
            "stderr_path": "",
        },
        "cluster_kill": {"job_id": "12345"},
        "cluster_logs": {"job_id": "12345", "tail": 10},
        "cluster_watch": {"job_id": "12345"},
    }

    for tool_name, args in invocations.items():
        handler = handlers[tool_name]
        # Each handler is async; run it to completion and capture
        # the response. It must NOT raise -- an AttributeError leaking
        # out of the tool is the original bug this test guards against.
        try:
            response = asyncio.run(handler(args))
        except AttributeError as exc:  # pragma: no cover - regression sentinel
            pytest.fail(
                f"{tool_name} leaked AttributeError to the caller: {exc!r}. "
                f"This is the original bug -- the missing-backend guard is "
                f"not in place."
            )

        assert isinstance(response, dict), (
            f"{tool_name} returned non-dict response: {response!r}"
        )
        assert response.get("isError") is True, (
            f"{tool_name} did not signal an error response: {response!r}"
        )

        text = _extract_error_text(response)
        # Message must be actionable: it must mention the backend name
        # so the caller knows which plugin is missing. The bare
        # AttributeError message ("'NoneType' object has no attribute
        # '_list_jobs'") would not contain the backend name.
        assert "lsf" in text.lower(), (
            f"{tool_name} error message does not name the missing backend: {text!r}"
        )
        assert "NoneType" not in text, (
            f"{tool_name} surfaced the raw NoneType AttributeError instead "
            f"of the actionable BackendNotAvailable message: {text!r}"
        )


def test_require_backend_module_raises_when_missing(monkeypatch):
    """Direct unit check on the helper that backs the fix."""
    mod = _load_cluster_dispatch_module()
    monkeypatch.setattr(mod, "_get_backend_module", lambda backend: None)

    with pytest.raises(mod.BackendNotAvailable) as excinfo:
        mod._require_backend_module("lsf")

    msg = str(excinfo.value)
    assert "lsf" in msg
    assert "_lsf.py" in msg


def test_require_backend_module_returns_module_when_present(monkeypatch):
    """Helper returns the module unchanged when the backend loads."""
    mod = _load_cluster_dispatch_module()
    sentinel = types.ModuleType("mcp_tools._fakebackend")
    monkeypatch.setattr(
        mod,
        "_get_backend_module",
        lambda backend: sentinel if backend == "lsf" else None,
    )

    result = mod._require_backend_module("lsf")
    assert result is sentinel


def test_response_payload_is_well_formed(dispatch_with_missing_backend):
    """Sanity: response shape matches the MCP error envelope used
    elsewhere in the dispatcher (``content[0].text`` is a non-empty
    string and ``isError`` is True)."""
    handlers = _tool_handlers(dispatch_with_missing_backend)
    response = asyncio.run(handlers["cluster_jobs"]({}))
    assert response.get("isError") is True
    content = response.get("content")
    assert isinstance(content, list) and len(content) >= 1
    assert content[0].get("type") == "text"
    text = content[0].get("text", "")
    assert isinstance(text, str) and text  # non-empty
    # Should not be JSON-encoded: this is an error envelope, not a
    # successful _json_response. (Defensive check: ensures we did not
    # accidentally route the missing-backend case through the success
    # path.)
    try:
        parsed = json.loads(text)
        # If the text happens to parse as JSON, it must not be a
        # success-shaped jobs payload.
        assert not isinstance(parsed, list), (
            "missing-backend response was JSON-encoded as a jobs list"
        )
    except (json.JSONDecodeError, ValueError):
        pass  # expected: error message is plain prose
