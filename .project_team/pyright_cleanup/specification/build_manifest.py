#!/usr/bin/env python
"""Build manifest.jsonl from the post-config pyright snapshot.

Triage rules encoded here are the human-judgment classifications made
by the Sweep Implementer per SPECIFICATION.md s 10. Each rule maps a
(path-pattern, rule_id, optional message-pattern) to a disposition and
a one-line proposed_fix.

Output: one JSON object per line, schema per SPECIFICATION.md s 5.

Convention notes (per coordinator review M1-M7):
- M3: scoped suppression form is `# pyright: ignore[<rule_id>]` (NOT
  `# type: ignore[<mypy-code>]`). Pyright does not match the bracket
  value to its rule names, but using the pyright-native rule_id makes
  intent explicit and matches the manifest's `rule_id` field.
- M4: negative-test rows (inside `with pytest.raises(<exc>):` blocks)
  use the exact reason form
  `# pyright: ignore[<rule_id>]  # negative test: <Symbol> is the assertion subject`.
- M5: every test mechanical reportOptionalMemberAccess row carries
  `notes: assert-narrow; ...` so future audit grep can find them.
- M2: internal optional/sibling-module imports are `mechanical`, not
  `stub-ignore`; `stub-ignore` is reserved for third-party stub gaps.
- M7: a sanity validator greps the symbol name in negative-test
  proposed_fix entries against the actual source line to catch
  copy-paste regressions.

PRESERVE-ON-MERGE (per coordinator option B post-WS-C, raised by
Bug-Fix Implementer's compositional concern about overwriting
implementer state):

    Compositional Law (SPEC s 4) makes manifest.jsonl the authoritative
    artifact. This regenerator MUST preserve implementer-owned fields
    (status, audited_by, notes) when re-running over an existing
    manifest. It refreshes only the triage-derived fields (region,
    rule_id, disposition, lane, verification, proposed_fix). If the
    refreshed disposition differs from what's stored on disk, a warning
    fires and the implementer reconciles per Seam 2 -- this script does
    NOT silently flip dispositions.

    Verified by `test_merge.py` (sibling): runs the regenerator over
    the current manifest and confirms status=done and audited_by:skeptic
    survive the round-trip on representative rows.

    Pass `--force-fresh` to bypass the merge (intended only for the
    very first build, before any implementer state is recorded; once
    status=done has been written, --force-fresh would violate the
    contract and you should not use it).
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]

# ---------------------------------------------------------------------------
# Load parsed errors
# ---------------------------------------------------------------------------
errors = json.load(open("/tmp/errors.json"))


# ---------------------------------------------------------------------------
# Triage helpers
# ---------------------------------------------------------------------------


def lane_for(disp: str) -> str:
    if disp in {
        "mechanical",
        "stub-fix",
        "stub-ignore",
        "config-relax",
        "config-exclude",
    }:
        return "sweep"
    if disp == "real-bug":
        return "bugfix"
    if disp == "dropped":
        return "none"
    raise ValueError(f"unknown disposition {disp!r}")


def verification_for(disp: str, region: str, node_id: str | None = None) -> str:
    if disp in {
        "mechanical",
        "stub-fix",
        "stub-ignore",
        "config-relax",
        "config-exclude",
    }:
        return "pyright-only"
    if disp == "real-bug":
        if node_id is None:
            raise ValueError("real-bug requires node_id")
        return f"pyright+targeted:{node_id}"
    return "n/a"


def negative_test_fix(rule_id: str, symbol: str) -> str:
    """Render the M4-mandated reason wording for negative-test ignores."""
    return (
        f"add `# pyright: ignore[{rule_id}]  # negative test: "
        f"{symbol} is the assertion subject`"
    )


def extract_negative_test_symbol(proposed_fix: str) -> str | None:
    """Pull out <Symbol> from a proposed_fix that uses the M4 wording."""
    m = re.search(
        r"negative test:\s*([A-Za-z_][\w\.]*)\s+is the assertion subject",
        proposed_fix,
    )
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# Triage decisions
# ---------------------------------------------------------------------------


def triage(e: dict) -> dict:
    # `col` is part of the error_id but unused inside triage rules; the
    # error_id itself is built later by the row-construction loop.
    p, line, rule, msg, region = (
        e["path"],
        e["line"],
        e["rule"],
        e["msg"],
        e["region"],
    )
    # --- NON-TEST REGION ---------------------------------------------------
    if region == "non-test":
        # cluster_dispatch.py: real-bug at every dereference of mod.
        if (
            p == "claudechic/defaults/mcp_tools/cluster_dispatch.py"
            and rule == "reportOptionalMemberAccess"
        ):
            return {
                "disposition": "real-bug",
                "proposed_fix": "guard `mod = _get_backend_module(backend)`; on None return _error_response('backend module not loadable')",
                "notes": (
                    "_get_backend_module returns None when the sibling "
                    "_<backend>.py is missing or its importlib spec/loader is None. "
                    "runtime_intent: raise (return error response from MCP tool). "
                    "Bug-Fix should add regression test simulating missing backend file."
                ),
                "verification": "pyright+targeted:tests/test_cluster_dispatch_missing_backend.py::test_missing_backend_module_returns_error",
            }

        # M2: scripts.audit -- mechanical, not stub-ignore.
        if p == "claudechic/audit/audit.py" and rule == "reportMissingImports":
            return {
                "disposition": "mechanical",
                "proposed_fix": "add `# pyright: ignore[reportMissingImports]  # scripts.audit resolved via runtime sys.path insertion (host repo layout)`",
                "notes": "internal-runtime-resolvable; not stub-dep",
            }

        # M2: claudechic.cluster -- mechanical.
        if p == "claudechic/mcp.py" and line == 1747 and rule == "reportMissingImports":
            return {
                "disposition": "mechanical",
                "proposed_fix": "add `# pyright: ignore[reportMissingImports]  # claudechic.cluster is an optional plugin module (try/except ImportError at runtime)`",
                "notes": "internal-runtime-resolvable; not stub-dep",
            }

        # _patches.py: TextArea._chic_undo_patched runtime monkey-patch marker.
        if p == "claudechic/_patches.py" and rule == "reportAttributeAccessIssue":
            return {
                "disposition": "mechanical",
                "proposed_fix": "add `# pyright: ignore[reportAttributeAccessIssue]  # runtime monkey-patch marker on TextArea class`",
                "notes": "",
            }

        # widgets/layout/chat_view.py:247-248 -- forward-ref MessageMetadata.
        if (
            p == "claudechic/widgets/layout/chat_view.py"
            and rule == "reportUndefinedVariable"
        ):
            return {
                "disposition": "mechanical",
                "proposed_fix": "hoist `from claudechic.agent import MessageMetadata` to module scope under `if TYPE_CHECKING:`",
                "notes": "",
            }

        # screens/agent_prompt_context.py:124 -- TITLE class var override.
        if (
            p == "claudechic/screens/agent_prompt_context.py"
            and rule == "reportIncompatibleVariableOverride"
        ):
            return {
                "disposition": "mechanical",
                "proposed_fix": 'annotate as `TITLE: ClassVar[str] = ""` (matches Screen.TITLE shape)',
                "notes": "",
            }

        # shell_runner.py:260 -- read1 attribute access.
        if p == "claudechic/shell_runner.py" and rule == "reportAttributeAccessIssue":
            return {
                "disposition": "mechanical",
                "proposed_fix": "narrow via `if hasattr(proc.stdout, 'read1')` already present; cast inside branch via `cast(BufferedReader, proc.stdout).read1(4096)`",
                "notes": "",
            }

        # hints/engine.py:174 -- duck-typed _pick_command.
        if p == "claudechic/hints/engine.py" and rule == "reportAttributeAccessIssue":
            return {
                "disposition": "mechanical",
                "proposed_fix": "add `# pyright: ignore[reportAttributeAccessIssue]  # duck-typed: hasattr-guarded at line 173`",
                "notes": "",
            }

        # audit/db.py:480 -- cursor.lastrowid Optional[int].
        if p == "claudechic/audit/db.py" and rule == "reportArgumentType":
            return {
                "disposition": "mechanical",
                "proposed_fix": "assert `sid is not None  # SQLite INSERT into INTEGER PRIMARY KEY always populates lastrowid`",
                "notes": "",
            }

        # mcp.py: disabled_rules narrowing failures (4 rows).
        if p == "claudechic/mcp.py" and rule == "reportArgumentType":
            return {
                "disposition": "mechanical",
                "proposed_fix": "cast `disabled_rules` to `frozenset[str] | None` after the `callable()` guard narrows the getattr return",
                "notes": "",
            }

        # workflows/agent_folders.py:778 -- frozenset[Unknown].
        if (
            p == "claudechic/workflows/agent_folders.py"
            and line == 778
            and rule == "reportArgumentType"
        ):
            return {
                "disposition": "mechanical",
                "proposed_fix": "annotate fallback as `frozenset[str]()` or `cast(set[str], disabled_rules or frozenset())`",
                "notes": "",
            }

        # workflows/agent_folders.py:1235 -- HookMatcher hooks parameter.
        if (
            p == "claudechic/workflows/agent_folders.py"
            and line == 1235
            and rule == "reportArgumentType"
        ):
            return {
                "disposition": "mechanical",
                "proposed_fix": "cast hooks list to expected type or update HookMatcher import to use the signature pyright sees",
                "notes": "",
            }

        # guardrails/hooks.py:183.
        if p == "claudechic/guardrails/hooks.py" and rule == "reportArgumentType":
            return {
                "disposition": "mechanical",
                "proposed_fix": "cast hooks list to expected type or update HookMatcher import to use the signature pyright sees",
                "notes": "",
            }

        # app.py:904.
        if p == "claudechic/app.py" and line == 904 and rule == "reportRedeclaration":
            return {
                "disposition": "mechanical",
                "proposed_fix": "rename inner function to `_effective_role_default` and assign to effective_role; preserves runtime, removes redeclaration",
                "notes": "",
            }

        # app.py:908.
        if p == "claudechic/app.py" and line == 908 and rule == "reportAssignmentType":
            return {
                "disposition": "mechanical",
                "proposed_fix": "annotate effective_role as `Callable[[], str | None] | str` so the elif branch's str assignment is valid",
                "notes": "may resolve as side-effect of fixing the row at 904; verify via re-snapshot",
            }

        # app.py:1206.
        if p == "claudechic/app.py" and line == 1206 and rule == "reportArgumentType":
            return {
                "disposition": "mechanical",
                "proposed_fix": "cast `event` to `HookEvent` via `cast(HookEvent, event)` -- compact_hooks dict is typed dict[str, Any]",
                "notes": "",
            }

        # app.py:2005-2006.
        if (
            p == "claudechic/app.py"
            and line in (2005, 2006)
            and rule == "reportArgumentType"
        ):
            return {
                "disposition": "mechanical",
                "proposed_fix": "widen `_merge` to `dict[str, frozenset[str]]` via `.copy()` cast or change parameter to `Mapping[str, frozenset[str]]`",
                "notes": "",
            }

        # app.py:2141.
        if p == "claudechic/app.py" and line == 2141 and rule == "reportArgumentType":
            return {
                "disposition": "mechanical",
                "proposed_fix": "assert `self._chicsession_name is not None` -- control flow at 2114-2126 ensures non-None at 2141",
                "notes": "",
            }

        # app.py:2194/2222/2695 -- workflow_engine narrowing.
        if (
            p == "claudechic/app.py"
            and line in (2194, 2222, 2695)
            and rule == "reportOptionalMemberAccess"
        ):
            return {
                "disposition": "mechanical",
                "proposed_fix": "assert `self._workflow_engine is not None` immediately before the dereference",
                "notes": "narrowing failure: assignment block at 2162/2170 + try/except at 2685 leaves Optional in pyright's view",
            }

        # app.py:3368.
        if p == "claudechic/app.py" and line == 3368 and rule == "reportArgumentType":
            return {
                "disposition": "mechanical",
                "proposed_fix": "update AgentSwitcher signature to `tuple[str, str, AgentStatus | str]` OR cast tuple at call site",
                "notes": "",
            }

        return {
            "disposition": "mechanical",
            "proposed_fix": "TBD: triage gap, examine and update build_manifest.py rule for this case",
            "notes": "TRIAGE-GAP: builder catch-all hit; manual review required before sweep",
        }

    # --- TEST REGION -------------------------------------------------------
    # Negative-test rows (M1 fix: parse symbol from msg per row).
    #
    # Composability post-WS-C amendment: for negative-test
    # `reportAttributeAccessIssue` rows in `tests/`, the actual resolving
    # mechanism is C3's `reportAttributeAccessIssue = "none"` downgrade in
    # the `tests/` executionEnvironments block (the rule is silenced
    # project-wide in tests/ before the per-line ignore would even matter).
    # Per s 2.1, the disposition must reflect *what resolves* the finding,
    # not the original triage proposal -- so these rows are `config-relax`,
    # not `mechanical`. Triage history is preserved in the notes prefix.
    # The `reportMissingImports` negative-test row in `test_scope_guard.py`
    # is NOT covered by C3 (different rule_id) and stays `mechanical`.

    if p == "tests/test_awareness_install.py" and rule == "reportAttributeAccessIssue":
        sym_match = re.search(r'"([A-Za-z_]\w*)"\s+is unknown import symbol', msg)
        symbol = sym_match.group(1) if sym_match else "(symbol)"
        return {
            "disposition": "config-relax",
            "proposed_fix": f'set `{rule} = "none"` in `[[tool.pyright.executionEnvironments]] root = "tests"` (covered by C3); negative-test subject: {symbol}',
            "notes": "originally proposed mechanical+ignore; resolved by C3 rule downgrade in tests/ executionEnvironments. negative-test subject: "
            + symbol,
        }

    if p == "tests/test_scope_guard.py" and rule == "reportAttributeAccessIssue":
        sym_match = re.search(r'"([A-Za-z_]\w*)"\s+is unknown import symbol', msg)
        symbol = sym_match.group(1) if sym_match else "(symbol)"
        # Composability post-WS-C amendment: resolving mechanism is C3, not the per-line ignore.
        return {
            "disposition": "config-relax",
            "proposed_fix": f'set `{rule} = "none"` in `[[tool.pyright.executionEnvironments]] root = "tests"` (covered by C3); negative-test subject: {symbol}',
            "notes": "originally proposed mechanical+ignore; resolved by C3 rule downgrade in tests/ executionEnvironments. negative-test subject: "
            + symbol,
        }

    if p == "tests/test_scope_guard.py" and rule == "reportMissingImports":
        mod_match = re.search(r'Import\s+"([\w\.]+)"\s+could not be resolved', msg)
        symbol = mod_match.group(1) if mod_match else "(module)"
        return {
            "disposition": "mechanical",
            "proposed_fix": negative_test_fix(rule, symbol),
            "notes": "intentional negative test: pytest.raises(ImportError) verifies module absence",
        }

    # Blanket config-relax candidates (s 10 step 4).
    if rule in {"reportArgumentType", "reportAttributeAccessIssue", "reportCallIssue"}:
        return {
            "disposition": "config-relax",
            "proposed_fix": f'set `{rule} = "none"` in `[[tool.pyright.executionEnvironments]] root = "tests"`',
            "notes": "test-region noise: stub-class-as-protocol / Mock attr / SdkMcpTool callability. Group fix: one config edit resolves all rows of this rule in tests/.",
        }

    # M5: assert-narrow tag for reportOptionalMemberAccess in tests.
    if rule == "reportOptionalMemberAccess":
        return {
            "disposition": "mechanical",
            "proposed_fix": f"assert the value is not None at line {line} (fixture/setup guarantees non-None at runtime)",
            "notes": "assert-narrow; test passes today; pyright cannot narrow across pilot/fixture seam",
        }

    if rule == "reportOptionalOperand":
        return {
            "disposition": "mechanical",
            "proposed_fix": "assert `root is not None` after the if-None reassignment (line 248) so the / operator is narrowable",
            "notes": "assert-narrow",
        }

    if rule == "reportUndefinedVariable":
        return {
            "disposition": "mechanical",
            "proposed_fix": "add `from typing import Any` import at module top",
            "notes": "",
        }

    if rule == "reportMissingImports":
        return {
            "disposition": "mechanical",
            "proposed_fix": negative_test_fix(rule, "(module)"),
            "notes": "intentional negative test (catch-all)",
        }

    return {
        "disposition": "mechanical",
        "proposed_fix": "TBD: triage gap, examine and update build_manifest.py rule for this case",
        "notes": "TRIAGE-GAP: builder catch-all hit (test region); manual review required",
    }


# ---------------------------------------------------------------------------
# Build manifest rows  (with preserve-on-merge per coordinator option B)
# ---------------------------------------------------------------------------
#
# Compositional Law (SPEC s 4): the manifest is the authoritative artifact.
# `build_manifest.py` regenerates *triage-derived* fields from the snapshot
# (region, rule_id, disposition, lane, verification, proposed_fix); it MUST
# preserve *implementer-owned* fields when the row already exists in the
# manifest on disk (status, audited_by, notes). Behaviour:
#
#   - Match by error_id.
#   - For an existing row: keep status/audited_by/notes from disk, refresh
#     the triage-derived fields. If a refreshed disposition differs from the
#     stored disposition, print a warning to stderr -- triage logic has drifted
#     and the implementer must reconcile (per Seam 2, an implementer who wants
#     to re-classify sets status = pending and messages the triage worker;
#     they do NOT silently accept a regenerator's disposition flip).
#   - For a new row (snapshot has a finding the manifest does not): add it
#     with status: pending.
#   - For a stale row (manifest has a row the snapshot no longer reports):
#     keep the row as-is and warn -- the implementer/coordinator decides
#     whether to drop it (Seam 4 erasure semantics) or investigate.
#
# Pass --force-fresh to bypass the merge and rebuild from scratch (only run
# this BEFORE any implementer state has been recorded; once status=done has
# been written, --force-fresh would violate the contract).

import argparse  # noqa: E402

_argp = argparse.ArgumentParser(add_help=False)
_argp.add_argument("--force-fresh", action="store_true", help="rebuild without merge")
_args, _ = _argp.parse_known_args()

# Load the existing manifest (if any) for merge.
_existing_path = REPO / ".project_team/pyright_cleanup/specification/manifest.jsonl"
_existing_by_id: dict[str, dict] = {}
if _existing_path.exists() and not _args.force_fresh:
    for _line in _existing_path.read_text(encoding="utf-8").splitlines():
        if not _line.strip():
            continue
        _r = json.loads(_line)
        _existing_by_id[_r["error_id"]] = _r

rows = []
seen_anchors: dict[tuple, int] = {}
disposition_drift: list[str] = []
new_rows_count = 0
preserved_count = 0

for e in errors:
    base = f"{e['path']}:{e['line']}:{e['col']}:{e['rule']}"
    anchor = (e["path"], e["line"], e["col"], e["rule"])
    seen_anchors[anchor] = seen_anchors.get(anchor, 0) + 1
    seq = seen_anchors[anchor]
    error_id = base if seq == 1 else f"{base}#{seq}"

    decision = triage(e)
    disp = decision["disposition"]
    region = e["region"]
    lane = lane_for(disp)
    if disp == "real-bug":
        verification = decision.get("verification") or verification_for(
            disp, region, "TBD"
        )
    else:
        verification = verification_for(disp, region)
    notes = decision.get("notes", "")

    row = {
        "error_id": error_id,
        "region": region,
        "rule_id": e["rule"],
        "disposition": disp,
        "lane": lane,
        "verification": verification,
        "proposed_fix": decision["proposed_fix"],
        "status": "pending",
    }
    if notes:
        row["notes"] = notes

    # Merge-on-match: preserve implementer state from disk.
    existing = _existing_by_id.get(error_id)
    if existing is not None:
        preserved_count += 1
        if existing.get("disposition") != disp:
            disposition_drift.append(
                f"{error_id}: stored={existing.get('disposition')} -> triage={disp}"
            )
        # Implementer-owned fields: status, audited_by, notes (verbatim).
        row["status"] = existing.get("status", row["status"])
        if "audited_by" in existing:
            row["audited_by"] = existing["audited_by"]
        if "notes" in existing:
            row["notes"] = existing["notes"]
        elif "notes" in row and not row["notes"]:
            # triage produced empty notes; existing also empty; drop the key.
            row.pop("notes", None)
    else:
        new_rows_count += 1

    rows.append(row)

# Stale-row reporting: rows in disk manifest that the current snapshot no
# longer produces. We keep these, so the implementer record survives even
# if a stub fix or config relax erased the underlying finding (Seam 4).
_new_ids = {r["error_id"] for r in rows}
stale_rows: list[dict] = []
for eid, old in _existing_by_id.items():
    if eid not in _new_ids:
        stale_rows.append(old)
        rows.append(old)

if disposition_drift:
    print(
        f"\nWARNING: triage logic produced different disposition vs stored manifest "
        f"for {len(disposition_drift)} row(s):",
        file=sys.stderr,
    )
    for d in disposition_drift[:10]:
        print(f"  {d}", file=sys.stderr)
    if len(disposition_drift) > 10:
        print(f"  ... and {len(disposition_drift) - 10} more", file=sys.stderr)
    print(
        "  Per Seam 2, implementer reconciliation required: do NOT silently accept "
        "the new disposition. Set status=pending on the affected rows and route to "
        "the triage worker.",
        file=sys.stderr,
    )

if stale_rows:
    print(
        f"\nWARNING: {len(stale_rows)} row(s) on disk no longer appear in the snapshot "
        "(possibly erased by a config-relax / stub-fix batch). Kept verbatim per Seam 4; "
        "coordinator decides whether to mark dropped or drop from manifest.",
        file=sys.stderr,
    )
    for s in stale_rows[:5]:
        print(f"  {s['error_id']}", file=sys.stderr)

if _existing_by_id:
    print(
        f"\nMerge: {preserved_count} rows preserved from disk; {new_rows_count} fresh rows added.",
        file=sys.stderr,
    )
elif _args.force_fresh:
    print("\n--force-fresh: bypassed merge, rebuilt from scratch.", file=sys.stderr)
else:
    print("\nNo existing manifest on disk; built from scratch.", file=sys.stderr)


# ---------------------------------------------------------------------------
# Validate invariants
# ---------------------------------------------------------------------------

if len(rows) != len(errors):
    sys.exit(f"VIOLATION I1: {len(rows)} rows != {len(errors)} findings")

ids = [r["error_id"] for r in rows]
if len(set(ids)) != len(ids):
    dup = [k for k, v in Counter(ids).items() if v > 1]
    sys.exit(f"DUPLICATE error_ids: {dup[:5]}")

for r in rows:
    if r["disposition"] == "mechanical" and r["lane"] != "sweep":
        sys.exit(f"I2 violation (mech in non-sweep): {r['error_id']}")
    if r["disposition"] == "real-bug" and r["lane"] != "bugfix":
        sys.exit(f"I2 violation (real-bug in non-bugfix): {r['error_id']}")
if any(r["disposition"] == "config-exclude" for r in rows):
    sys.exit("I7 violation: config-exclude row")
if any(r["disposition"] == "dropped" and r["region"] == "non-test" for r in rows):
    sys.exit("I9 violation: dropped non-test row")
if any(r["disposition"] == "config-relax" and r["region"] == "non-test" for r in rows):
    sys.exit("I12 violation: config-relax non-test row")

# I5: any `# type: ignore` or `# pyright: ignore` must carry a non-empty
# bracket selector. Should-fix per coordinator (Skeptic): single regex
# covers both forms uniformly.
_I5_OK = re.compile(r"#\s*(type|pyright):\s*ignore\[[a-zA-Z\-_,]+\]")
for r in rows:
    pf = r["proposed_fix"]
    if "# type: ignore" in pf or "# pyright: ignore" in pf:
        if not _I5_OK.search(pf):
            sys.exit(f"I5 violation (bare ignore): {r['error_id']}")

for r in rows:
    if r["disposition"] == "dropped":
        notes = r.get("notes", "")
        if not any(
            notes.startswith(prefix)
            for prefix in (
                "wontfix:",
                "refactor-required:",
                "duplicate:",
                "false-positive:",
            )
        ):
            sys.exit(f"I4 violation: dropped row missing notes prefix: {r['error_id']}")


# ---------------------------------------------------------------------------
# M7 validator: for negative-test rows, confirm the cited symbol appears
# in the actual source line. Catches copy-paste regressions like M1.
# ---------------------------------------------------------------------------

m7_failures: list[str] = []
file_cache: dict[str, list[str]] = {}
neg_count = 0
m7_skipped_done = 0
for r in rows:
    pf = r["proposed_fix"]
    sym = extract_negative_test_symbol(pf)
    if sym is None:
        continue
    # Triage-time gate only: once status=done, the line was edited (an
    # inline comment was appended; the symbol token still survives, but
    # we don't re-validate against post-edit state to keep behaviour
    # parallel with the 5-pattern validator below.
    if r.get("status") == "done":
        m7_skipped_done += 1
        continue
    neg_count += 1
    relpath, lineno_str, *_ = r["error_id"].split(":")
    try:
        lineno = int(lineno_str)
    except ValueError:
        continue
    full = REPO / relpath
    if relpath not in file_cache:
        try:
            file_cache[relpath] = full.read_text(encoding="utf-8").splitlines()
        except OSError:
            file_cache[relpath] = []
    src_lines = file_cache[relpath]
    if lineno - 1 >= len(src_lines):
        m7_failures.append(f"{r['error_id']} -- line {lineno} out of range")
        continue
    src = src_lines[lineno - 1]
    # For module-name symbols (e.g. "claudechic.paths"), check the module
    # token; for unqualified symbols, check the bare token.
    if sym not in src:
        m7_failures.append(
            f"{r['error_id']} -- proposed_fix symbol '{sym}' NOT in source line: {src.strip()!r}"
        )

if m7_failures:
    print("M7 validator failures:", file=sys.stderr)
    for f in m7_failures:
        print(f"  {f}", file=sys.stderr)
    sys.exit("M7 validation failed")
print(
    f"M7 validator: {neg_count} pending negative-test rows checked, all symbols match source"
    + (
        f" (skipped {m7_skipped_done} status=done rows; line anchors stale post-edit)"
        if m7_skipped_done
        else ""
    ),
    file=sys.stderr,
)


# ---------------------------------------------------------------------------
# Skeptic-blessed pattern validator (coordinator post-S3 sanity gate):
# Skeptic blessed the 7-row sample plus the 12-row escape extension. The
# population of test mechanical reportOptionalMemberAccess /
# reportOptionalOperand rows is cleared IFF every row matches one of the
# four blessed sub-patterns (E1a folded into pattern 1 per Skeptic's nit):
#
#   1. `app._agent` direct deref OR via local alias `<var> = app._agent`
#      upstream (E1a alias). Source line contains `app._agent` OR `<var>`
#      where `<var>` was bound to `app._agent` in the preceding ~30 lines.
#   2. `app.agent_mgr` direct deref. Source line contains `app.agent_mgr`.
#   3. `AsyncMock.await_args` direct deref. Source line contains
#      `await_args`.
#   4. `<var> = app.agent_mgr.find_by_name("...")` upstream alias (E1b).
#      Source line contains `<var>` where `<var>` was bound to a
#      `find_by_name` call in the preceding ~30 lines.
#   5. `tests/conftest.py` `root: Path | None` parameter post-reassignment
#      (E2). File path is `tests/conftest.py` AND source line contains the
#      bare token `root`.
#
# Any escape -> STOP and route to coordinator for Skeptic re-routing.
# ---------------------------------------------------------------------------

_BIND_RE = re.compile(r"^\s*([a-zA-Z_]\w*)\s*=\s*(.+?)\s*$")
_FUNC_RE = re.compile(r"^\s*(?:async\s+)?def\s+\w+")


def _bound_aliases(src_lines: list[str], lineno: int, rhs_substr: str) -> set[str]:
    """Return LHS names from `<lhs> = <expr>` bindings whose <expr>
    contains rhs_substr, scanning back from `lineno` to the start of the
    enclosing function (or top of file). Function-scoped lookback covers
    long test bodies (rebinding at L749 used at L792 etc)."""
    out: set[str] = set()
    end = lineno - 1
    # Walk back to the nearest enclosing `def`/`async def`; stop there.
    start = 0
    for i in range(end - 1, -1, -1):
        if _FUNC_RE.match(src_lines[i]):
            start = i + 1
            break
    for i in range(start, end):
        if i >= len(src_lines):
            break
        m = _BIND_RE.match(src_lines[i])
        if m and rhs_substr in m.group(2):
            out.add(m.group(1))
    return out


def _has_word(token: str, src: str) -> bool:
    return re.search(rf"\b{re.escape(token)}\b", src) is not None


def _classify(src: str, src_lines: list[str], lineno: int, relpath: str) -> str | None:
    """Return matched pattern label, or None if the row escapes."""
    # Pattern 1: app._agent direct
    if "app._agent" in src:
        return "P1-direct"
    # Pattern 1-alias / E1a: <var> bound to `app._agent` upstream, used here.
    aliases_p1 = _bound_aliases(src_lines, lineno, "app._agent")
    if any(_has_word(a, src) for a in aliases_p1):
        return "P1-alias"
    # Pattern 2: app.agent_mgr direct (also covers .switch / .active /
    # .connect_agent / .find_by_name etc -- anything whose Optional source
    # is the manager itself).
    if "app.agent_mgr" in src:
        return "P2-direct"
    # Pattern 3: AsyncMock.await_args
    if _has_word("await_args", src):
        return "P3-await_args"
    # Pattern 4 / E1b: <var> bound to find_by_name(...) upstream, used here.
    aliases_p4 = _bound_aliases(src_lines, lineno, "find_by_name")
    if any(_has_word(a, src) for a in aliases_p4):
        return "P4-find_by_name"
    # Pattern 5 / E2: conftest.py root parameter post-reassignment.
    if relpath == "tests/conftest.py" and _has_word("root", src):
        return "P5-conftest-root"
    return None


pattern_hits: Counter = Counter()
escape_rows: list[tuple[str, str]] = []
checked_rows = 0
skipped_done = 0
for r in rows:
    if r["region"] != "test":
        continue
    if r["disposition"] != "mechanical":
        continue
    if r["rule_id"] not in ("reportOptionalMemberAccess", "reportOptionalOperand"):
        continue
    # Once a row is at status=done, the offending line has been edited and
    # the snapshot's (file, line, col) anchor no longer points to the
    # original deref site -- it now lands on a freshly-inserted assert or
    # a shifted line. Skip done rows: this validator is a triage-time gate
    # only. Re-running over an edited tree is a no-op for done rows.
    if r["status"] == "done":
        skipped_done += 1
        continue
    checked_rows += 1
    relpath, lineno_str, *_ = r["error_id"].split(":")
    lineno = int(lineno_str)
    if relpath not in file_cache:
        try:
            file_cache[relpath] = (
                (REPO / relpath).read_text(encoding="utf-8").splitlines()
            )
        except OSError:
            file_cache[relpath] = []
    src_lines = file_cache[relpath]
    src = src_lines[lineno - 1] if lineno - 1 < len(src_lines) else ""
    label = _classify(src, src_lines, lineno, relpath)
    if label is None:
        escape_rows.append((r["error_id"], src.strip()))
    else:
        pattern_hits[label] += 1

print(
    f"\n5-pattern validator: {checked_rows} pending test mechanical OMA/OOperand rows checked"
    + (
        f" (skipped {skipped_done} status=done rows; line anchors stale post-edit)"
        if skipped_done
        else ""
    ),
    file=sys.stderr,
)
for label in (
    "P1-direct",
    "P1-alias",
    "P2-direct",
    "P3-await_args",
    "P4-find_by_name",
    "P5-conftest-root",
):
    print(f"  {label:24s}  {pattern_hits.get(label, 0):4d}", file=sys.stderr)
print(f"  {'escaped':24s}  {len(escape_rows):4d}", file=sys.stderr)
if escape_rows:
    print("\n  escape-row source lines:", file=sys.stderr)
    for eid, line in escape_rows:
        print(f"    {eid}", file=sys.stderr)
        print(f"      {line!r}", file=sys.stderr)
    sys.exit("5-pattern validator: residual escapes; STOP and re-route to Skeptic")


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

print(f"\nOK: {len(rows)} rows, all invariants check passed", file=sys.stderr)

print("\n=== Disposition x Region ===", file=sys.stderr)
disp_region = Counter((r["region"], r["disposition"]) for r in rows)
for (region, disp), c in sorted(disp_region.items()):
    print(f"  {region:8s}  {disp:14s}  {c:4d}", file=sys.stderr)

print("\n=== Lane summary ===", file=sys.stderr)
lane_ctr = Counter(r["lane"] for r in rows)
for lane, c in sorted(lane_ctr.items()):
    print(f"  {lane}: {c}", file=sys.stderr)

real_bug_pct = 100 * sum(1 for r in rows if r["disposition"] == "real-bug") / len(rows)
print(f"\nReal-bug rate: {real_bug_pct:.1f}%", file=sys.stderr)

# I10 audit queue
i10_pyright = [
    r
    for r in rows
    if r["disposition"] == "mechanical" and "# pyright: ignore" in r["proposed_fix"]
]
i10_legacy = [
    r
    for r in rows
    if r["disposition"] == "mechanical" and "# type: ignore" in r["proposed_fix"]
]
print(
    f"\nI10 audit queue (mechanical rows whose fix uses scoped ignore): "
    f"{len(i10_pyright) + len(i10_legacy)}",
    file=sys.stderr,
)
print(f"  via `# pyright: ignore[...]`: {len(i10_pyright)}", file=sys.stderr)
print(
    f"  via `# type: ignore[...]`:    {len(i10_legacy)} (must be 0 after M3)",
    file=sys.stderr,
)
if i10_legacy:
    sys.exit("M3 violation: residual `# type: ignore` in proposed_fix")

# ---------------------------------------------------------------------------
# Emit JSONL
# ---------------------------------------------------------------------------

out = REPO / ".project_team/pyright_cleanup/specification/manifest.jsonl"
with out.open("w", encoding="utf-8") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

print(f"\nWrote {out} ({len(rows)} rows)", file=sys.stderr)
