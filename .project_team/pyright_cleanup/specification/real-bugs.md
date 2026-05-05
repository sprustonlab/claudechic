# Real Bugs -- pyright_cleanup

One entry per `disposition = real-bug` manifest row. Required columns per
SPECIFICATION.md s 13: `error_id`, `bug`, `fix`, `regression_test_node_id`,
`runtime_intent`. `runtime_intent` is required for all
`reportOptionalMemberAccess` / None-narrowing rows (and recommended for the
rest); allowed values: `raise`, `skip`, `default:<v>`, `propagate`.

This file is owned by the Bug-Fix Implementer; the Sweep Implementer
populated the rows below from the triage notes so the bug description and
intended runtime semantics are pre-recorded. The Bug-Fix Implementer
fills in the actual `fix` description after the patch lands.

## Cluster dispatch -- missing backend module

Root cause: `_get_backend_module(backend)` in
`claudechic/defaults/mcp_tools/cluster_dispatch.py` returns `None` when
the sibling `_<backend>.py` file is missing or its importlib spec/loader
is `None` (lines 87, 91). Six call sites dereference
`mod._<method>(...)` without a None guard. If the sibling file is absent
at runtime (e.g. user's claudechic install is missing the `_lsf.py`
plugin), the MCP tool raises `AttributeError: 'NoneType' object has no
attribute '_list_jobs'` instead of returning a clean error response to
the caller. The `try / except Exception` block in each tool catches it
and returns `_error_response(str(e))`, but the message is "'NoneType'
object has no attribute '_list_jobs'" rather than something
actionable.

### Shared fix (all 6 rows)

Introduced a `BackendNotAvailable(RuntimeError)` exception class and a
`_require_backend_module(backend)` helper that wraps
`_get_backend_module` and raises `BackendNotAvailable` with an
actionable message ("Cluster backend `<name>` module is not available
(missing sibling file `_<name>.py` next to cluster_dispatch.py). Run
cluster_setup to reconfigure or reinstall the cluster plugin.") when
the underlying lookup returns `None`.

For the five tools whose backend usage already sits inside a
`try / except Exception as e: return _error_response(str(e))` block
(`cluster_jobs`, `cluster_status`, `cluster_submit`, `cluster_kill`,
`cluster_logs`), the `mod = _get_backend_module(backend)` assignment
was moved INSIDE the existing `try` block and rewritten as
`mod = _require_backend_module(backend)`. The existing handler then
catches the `BackendNotAvailable` (it inherits `Exception`) and
surfaces its descriptive message via `_error_response`.

For `cluster_watch` (which had no surrounding `try / except`), an
explicit `try: mod = _require_backend_module(backend) except
BackendNotAvailable as e: return _error_response(str(e))` block was
added immediately after the `_BACKENDS` membership check.

Net runtime effect: when a backend module is missing, all six tools
now return a structured MCP error response (`isError = True`) whose
text names the backend and points the caller at `cluster_setup`,
instead of raising `AttributeError: 'NoneType' object has no attribute
'_<method>'` (or surfacing the same string through `_error_response`
as before).

| error_id | bug | fix | regression_test_node_id | runtime_intent |
|---|---|---|---|---|
| `claudechic/defaults/mcp_tools/cluster_dispatch.py:123:48:reportOptionalMemberAccess` | `cluster_jobs` derefs `mod._list_jobs` after `mod = _get_backend_module(backend)` returns None when sibling `_<backend>.py` is missing | Replaced with `_require_backend_module(backend)` inside the existing `try` block; `BackendNotAvailable` is caught by the existing `except Exception` and surfaced via `_error_response` (see "Shared fix" above) | `tests/test_cluster_dispatch_missing_backend.py::test_missing_backend_module_returns_error` | `raise` (raises `BackendNotAvailable`; per-tool `except` returns a structured `_error_response` to the MCP caller) |
| `claudechic/defaults/mcp_tools/cluster_dispatch.py:152:50:reportOptionalMemberAccess` | `cluster_status` derefs `mod._get_job_status` after `mod = _get_backend_module(backend)` returns None | Same shared fix: `_require_backend_module(backend)` moved into the existing `try` block | `tests/test_cluster_dispatch_missing_backend.py::test_missing_backend_module_returns_error` | `raise` |
| `claudechic/defaults/mcp_tools/cluster_dispatch.py:231:50:reportOptionalMemberAccess` | `cluster_submit` derefs `mod._submit_job` after `mod = _get_backend_module(backend)` returns None | Same shared fix: `_require_backend_module(backend)` moved into the existing `try` block | `tests/test_cluster_dispatch_missing_backend.py::test_missing_backend_module_returns_error` | `raise` |
| `claudechic/defaults/mcp_tools/cluster_dispatch.py:253:50:reportOptionalMemberAccess` | `cluster_kill` derefs `mod._kill_job` after `mod = _get_backend_module(backend)` returns None | Same shared fix: `_require_backend_module(backend)` moved into the existing `try` block | `tests/test_cluster_dispatch_missing_backend.py::test_missing_backend_module_returns_error` | `raise` |
| `claudechic/defaults/mcp_tools/cluster_dispatch.py:290:33:reportOptionalMemberAccess` | `cluster_logs` derefs `mod._get_job_status` after `mod = _get_backend_module(backend)` returns None | Same shared fix: `_require_backend_module(backend)` moved into the existing `try` block | `tests/test_cluster_dispatch_missing_backend.py::test_missing_backend_module_returns_error` | `raise` |
| `claudechic/defaults/mcp_tools/cluster_dispatch.py:347:51:reportOptionalMemberAccess` | `cluster_watch` derefs `mod._get_job_status` (inside the background `_run_watch` lambda) after `mod = _get_backend_module(backend)` returns None | `cluster_watch` had no enclosing `try`; added a dedicated `try / except BackendNotAvailable` around `mod = _require_backend_module(backend)` that returns `_error_response(str(e))` before scheduling the watcher task | `tests/test_cluster_dispatch_missing_backend.py::test_missing_backend_module_returns_error` | `raise` |

Notes for Bug-Fix Implementer:
- All six rows share one regression test node. The test
  monkeypatches `_get_backend_module` to return `None`, calls each of
  the six tool handlers, and asserts each returns the error-response
  shape (`{"isError": True, ...}` with a message that names the
  missing backend and does not contain the substring `NoneType`).
- Per "err toward real-bug" guidance, all six rows are classified
  `real-bug` rather than `mechanical` even though the surrounding
  `try / except Exception` block masks the AttributeError at runtime.
  The bug is not "code crashes"; it is "code returns an unhelpful
  AttributeError message instead of a configuration-friendly error".
  Fix changes runtime behaviour (different message + earlier exit
  path) so it qualifies as `real-bug`.
- After the fix, re-running pyright on
  `claudechic/defaults/mcp_tools/cluster_dispatch.py` produces 0
  errors (was 6).
