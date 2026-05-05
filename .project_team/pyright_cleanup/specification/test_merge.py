#!/usr/bin/env python
"""Test for build_manifest.py preserve-on-merge contract (option B).

Per coordinator review post-WS-C: regenerating manifest.jsonl must NOT
overwrite implementer-owned fields (status, audited_by, notes). This
test verifies that contract by:

  1. Snapshotting the current manifest.jsonl into a temp file.
  2. Re-running build_manifest.py (no --force-fresh).
  3. Asserting that on representative rows, status=done and
     audited_by:skeptic survive the regeneration.

Run from the repo root:

    python .project_team/pyright_cleanup/specification/test_merge.py

Exits non-zero if any assertion fails.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
MANIFEST = REPO / ".project_team/pyright_cleanup/specification/manifest.jsonl"
BUILDER = REPO / ".project_team/pyright_cleanup/specification/build_manifest.py"


def load_rows(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def by_id(rows: list[dict]) -> dict[str, dict]:
    return {r["error_id"]: r for r in rows}


def main() -> int:
    if not MANIFEST.exists():
        print(f"FAIL: manifest not found at {MANIFEST}")
        return 1

    # Snapshot the live manifest.
    backup = MANIFEST.with_suffix(".jsonl.test_merge_bak")
    shutil.copyfile(MANIFEST, backup)
    try:
        before = load_rows(backup)
        before_idx = by_id(before)

        # Pre-flight invariants we'll re-check post-merge.
        done_before = [r["error_id"] for r in before if r.get("status") == "done"]
        audited_before = [r["error_id"] for r in before if r.get("audited_by")]
        # Need at least a handful of each to make the test meaningful.
        assert len(done_before) > 0, (
            "no status=done rows in current manifest -- nothing to test"
        )
        assert len(audited_before) > 0, (
            "no audited_by rows in current manifest -- nothing to test"
        )

        print(
            f"Before regeneration: {len(before)} rows, "
            f"{len(done_before)} done, {len(audited_before)} audited"
        )

        # Re-run the regenerator (no --force-fresh, so merge applies).
        result = subprocess.run(
            [sys.executable, str(BUILDER)],
            capture_output=True,
            text=True,
            cwd=REPO,
        )
        if result.returncode != 0:
            print("FAIL: build_manifest.py exited non-zero")
            print(result.stderr)
            return 1

        after = load_rows(MANIFEST)
        after_idx = by_id(after)

        failures: list[str] = []

        # 1. Same row count.
        if len(after) != len(before):
            failures.append(
                f"row count changed: before={len(before)}, after={len(after)}"
            )

        # 2. Every row that was status=done before is still status=done.
        regressed_status: list[str] = []
        for eid in done_before:
            if eid not in after_idx:
                regressed_status.append(f"{eid}: missing post-merge")
            elif after_idx[eid].get("status") != "done":
                regressed_status.append(
                    f"{eid}: status flipped from done -> {after_idx[eid].get('status')}"
                )
        if regressed_status:
            failures.append(
                f"{len(regressed_status)} done-status rows lost their status"
            )
            for r in regressed_status[:5]:
                failures.append(f"  {r}")

        # 3. Every row that had audited_by:<x> before still has it.
        regressed_audit: list[str] = []
        for eid in audited_before:
            if eid not in after_idx:
                regressed_audit.append(f"{eid}: missing post-merge")
            else:
                pre_aud = before_idx[eid].get("audited_by")
                post_aud = after_idx[eid].get("audited_by")
                if pre_aud != post_aud:
                    regressed_audit.append(
                        f"{eid}: audited_by changed {pre_aud!r} -> {post_aud!r}"
                    )
        if regressed_audit:
            failures.append(
                f"{len(regressed_audit)} audited rows lost their audit attestation"
            )
            for r in regressed_audit[:5]:
                failures.append(f"  {r}")

        # 4. The 3 Composability-reclassified rows: stay config-relax post-merge.
        reclassified_rows = [
            "tests/test_awareness_install.py:223:47:reportAttributeAccessIssue",
            "tests/test_scope_guard.py:74:47:reportAttributeAccessIssue",
            "tests/test_scope_guard.py:112:47:reportAttributeAccessIssue",
        ]
        for eid in reclassified_rows:
            if eid not in before_idx:
                continue  # not in current manifest yet; skip
            if before_idx[eid].get("disposition") != "config-relax":
                continue  # not yet reclassified; skip
            after_disp = after_idx.get(eid, {}).get("disposition")
            if after_disp != "config-relax":
                failures.append(
                    f"{eid}: disposition flipped from config-relax to {after_disp!r} post-merge"
                )
            after_notes = after_idx.get(eid, {}).get("notes", "")
            if "originally proposed mechanical+ignore" not in after_notes:
                failures.append(
                    f"{eid}: triage-history notes prefix stripped post-merge"
                )

        if failures:
            print("\nFAIL:")
            for f in failures:
                print(f"  {f}")
            return 1

        print(
            f"\nPASS: regeneration preserved {len(done_before)} done rows + "
            f"{len(audited_before)} audited rows + C3-erased notes."
        )
        return 0
    finally:
        # Always restore from backup so the live manifest reflects whatever
        # state we started in (the regenerator should be idempotent at this
        # point, but we restore for safety -- pre-existing backup file gets
        # cleaned up).
        shutil.copyfile(backup, MANIFEST)
        backup.unlink()


if __name__ == "__main__":
    sys.exit(main())
