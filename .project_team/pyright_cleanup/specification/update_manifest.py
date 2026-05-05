#!/usr/bin/env python
"""Apply post-build status updates to manifest.jsonl.

This is the persistence layer for sweep progress. `build_manifest.py`
emits a fresh manifest from the post-config snapshot; `update_manifest.py`
mutates per-row `status` (and adds `audited_by` / `notes` augmentations)
as sweep batches land. Run with `--batch <id>` to apply a named batch.

Batches:
- batch-c3      : C3 config-relax. Mark 197 config-relax rows + 3 incidentally-
                  erased mechanical rows in negative-test files as `status=done`.
                  Also augment notes on the 3 erased mechanical rows to
                  record C3 as the actual resolution mechanism.

Idempotent: re-running a batch over an already-updated manifest leaves
it unchanged (rows are matched by error_id; no-op if already at target
state).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
MANIFEST = REPO / ".project_team/pyright_cleanup/specification/manifest.jsonl"


def load() -> list[dict]:
    return [
        json.loads(line) for line in MANIFEST.read_text().splitlines() if line.strip()
    ]


def save(rows: list[dict]) -> None:
    with MANIFEST.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def batch_c3(rows: list[dict]) -> tuple[int, int]:
    """Mark all 197 config-relax rows + 3 erased mechanical rows as done.

    Returns (config_relax_marked, mechanical_erased_marked).
    """
    erased_negative_test = {
        "tests/test_awareness_install.py:223:47:reportAttributeAccessIssue",
        "tests/test_scope_guard.py:74:47:reportAttributeAccessIssue",
        "tests/test_scope_guard.py:112:47:reportAttributeAccessIssue",
    }
    cr = 0
    erased = 0
    for r in rows:
        if r["disposition"] == "config-relax" and r["status"] != "done":
            r["status"] = "done"
            cr += 1
        elif r["error_id"] in erased_negative_test and r["status"] != "done":
            r["status"] = "done"
            note = r.get("notes", "")
            tag = "C3-erased: rule downgraded in tests/ executionEnvironments; per-line ignore not applied"
            if tag not in note:
                r["notes"] = (note + "; " + tag).lstrip("; ") if note else tag
            erased += 1
    return cr, erased


def batch_c3_reclassify(rows: list[dict]) -> tuple[int, int]:
    """Composability post-WS-C amendment: reclassify the 3 C3-erased rows
    from `mechanical` to `config-relax`.

    Per s 2.1, disposition reflects what *actually* resolves the finding;
    for these 3 rows the resolving mechanism is C3's
    `reportAttributeAccessIssue = "none"` downgrade in the tests/
    executionEnvironments, not the per-line ignore originally proposed.

    Mechanical edit (NOT a regenerator run, per coordinator):
      - disposition: mechanical -> config-relax
      - lane: stays sweep (config-relax routes to sweep)
      - verification: stays pyright-only
      - notes: prefixed with the triage-history wording
      - audited_by: cleared if present (config-relax doesn't trigger I10)

    Returns (rows_reclassified, rows_audit_cleared).
    """
    target_ids = {
        "tests/test_awareness_install.py:223:47:reportAttributeAccessIssue",
        "tests/test_scope_guard.py:74:47:reportAttributeAccessIssue",
        "tests/test_scope_guard.py:112:47:reportAttributeAccessIssue",
    }
    notes_prefix = (
        "originally proposed mechanical+ignore; resolved by C3 rule downgrade "
        "in tests/ executionEnvironments"
    )
    flipped = 0
    audit_cleared = 0
    for r in rows:
        if r["error_id"] not in target_ids:
            continue
        if r["disposition"] == "config-relax":
            continue  # idempotent
        r["disposition"] = "config-relax"
        # lane and verification unchanged: sweep + pyright-only are correct
        # for both mechanical and config-relax in this region.
        old_notes = r.get("notes", "")
        # Strip the prior C3-erased marker (if present) since the new prefix
        # subsumes it; otherwise keep the rest of the notes verbatim.
        cleaned = old_notes
        for token in [
            "; C3-erased: rule downgraded in tests/ executionEnvironments; per-line ignore not applied",
            "C3-erased: rule downgraded in tests/ executionEnvironments; per-line ignore not applied",
        ]:
            if token in cleaned:
                cleaned = cleaned.replace(token, "").strip("; ").strip()
        r["notes"] = (notes_prefix + ". " + cleaned).rstrip(". ").strip()
        flipped += 1
        if "audited_by" in r:
            del r["audited_by"]
            audit_cleared += 1
    return flipped, audit_cleared


def batch_mech_sweep_done(rows: list[dict]) -> tuple[int, int]:
    """Mark all remaining mechanical sweep-lane rows as done.

    For rows whose `proposed_fix` contains `# pyright: ignore` (the I10
    audit set), populate `audited_by: skeptic` per coordinator's verdict
    table (Skeptic blessed all 19 originally; 3 were erased by C3, so 16
    remain). Without `audited_by` populated, status would not flip.

    Returns (mechanical_marked_done, i10_audited).
    """
    marked = 0
    audited = 0
    for r in rows:
        if r["disposition"] != "mechanical":
            continue
        if r["status"] == "done":
            continue
        # I10 gate
        if "# pyright: ignore" in r["proposed_fix"]:
            r["audited_by"] = "skeptic"
            audited += 1
        r["status"] = "done"
        marked += 1
    return marked, audited


BATCHES = {
    "batch-c3": batch_c3,
    "batch-mech-sweep-done": batch_mech_sweep_done,
    "batch-c3-reclassify": batch_c3_reclassify,
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", required=True, choices=list(BATCHES))
    args = ap.parse_args()
    rows = load()
    pre_done = sum(1 for r in rows if r["status"] == "done")
    a, b = BATCHES[args.batch](rows)
    save(rows)
    post_done = sum(1 for r in rows if r["status"] == "done")
    if args.batch == "batch-c3":
        print(
            f"Batch {args.batch}: marked {a} config-relax + {b} erased-mechanical rows done"
        )
    elif args.batch == "batch-mech-sweep-done":
        print(
            f"Batch {args.batch}: marked {a} mechanical rows done; {b} I10 rows received `audited_by: skeptic`"
        )
    elif args.batch == "batch-c3-reclassify":
        print(
            f"Batch {args.batch}: reclassified {a} rows mechanical -> config-relax; cleared audited_by on {b}"
        )
    print(f"Total status=done in manifest: {pre_done} -> {post_done}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
