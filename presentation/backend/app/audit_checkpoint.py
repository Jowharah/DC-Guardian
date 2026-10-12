"""External checkpoints for the three local audit hash chains.

The chains (unified group reviews, Evidence verdicts, Investigator calls, lifecycle transitions) detect
an edited record, but not deletion of the newest records or replacement of the
whole database. A checkpoint records each chain's length and head hash in a
small JSON file the operator keeps OUTSIDE the database folder (another drive,
removable media, a mailbox). `verify` then checks that every chain is intact
and still contains the checkpointed prefix: the record at the checkpointed
position must carry the checkpointed hash.

    python -m presentation.backend.app.audit_checkpoint write --out-dir <folder outside the data folder>
    python -m presentation.backend.app.audit_checkpoint verify --file <checkpoint.json>

Set DCG_CHECKPOINT_KEY to add an HMAC, so a checkpoint cannot be forged by
someone who can rewrite the database but does not hold the key.
"""
import argparse
import hashlib
import hmac
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from presentation.backend.app.incident_store import _db_path
from presentation.backend.app.review_integrity import EVIDENCE_FIELDS, FIELDS as REVIEW_FIELDS, verify_records

VERSION = "DCG-AUDIT-CHECKPOINT-v1"


def chains():
    from presentation.backend.app.investigator_audit import FIELDS as INVESTIGATOR_FIELDS, connect as investigator_connect
    from presentation.backend.app.human_review_audit import connect as review_connect
    from presentation.backend.app.evidence_review import connect as evidence_connect
    from presentation.backend.app.investigation_lifecycle import FIELDS as LIFECYCLE_FIELDS, connect as lifecycle_connect
    return {"unified_reviews": (review_connect, "human_review_audit", REVIEW_FIELDS),
            "lifecycle_transitions": (lifecycle_connect, "investigation_lifecycle", LIFECYCLE_FIELDS),
            "evidence_verdicts": (evidence_connect, "evidence_review_audit", EVIDENCE_FIELDS),
            "investigator_calls": (investigator_connect, "investigator_audit", INVESTIGATOR_FIELDS)}


def chain_rows(connect, table, fields):
    with connect() as db:
        # nosec B608: table and columns are module constants, never user input.
        return db.execute("SELECT " + ",".join(fields) + " FROM " + table + " ORDER BY rowid ASC").fetchall()  # nosec B608


def _signature(body):
    key = os.environ.get("DCG_CHECKPOINT_KEY", "")
    return hmac.new(key.encode(), json.dumps(body, sort_keys=True).encode(), hashlib.sha256).hexdigest() if key else None


def snapshot():
    body = {"version": VERSION, "created_at": datetime.now(timezone.utc).isoformat(), "chains": {}}
    for name, (connect, table, fields) in chains().items():
        result = verify_records(chain_rows(connect, table, fields), fields)
        if result["status"] != "PASS":
            raise RuntimeError(f"{name} chain fails verification ({result.get('reason')}); not checkpointing a broken chain")
        body["chains"][name] = {"length": result["checked"], "head_hash": result["head_hash"]}
    return {**body, "hmac_sha256": _signature(body)}


def write(out_dir):
    out = Path(out_dir).resolve()
    data = Path(_db_path()).resolve().parent
    if out == data or data in out.parents:
        raise ValueError("Store checkpoints outside the database folder; a copy next to the database proves nothing")
    out.mkdir(parents=True, exist_ok=True)
    checkpoint = snapshot()
    path = out / ("dcg-audit-checkpoint-" + checkpoint["created_at"][:19].replace(":", "") + ".json")
    path.write_text(json.dumps(checkpoint, indent=2), encoding="utf-8")
    return path, checkpoint


def verify(checkpoint):
    body = {k: v for k, v in checkpoint.items() if k != "hmac_sha256"}
    report = {"status": "PASS", "chains": {}, "created_at": checkpoint.get("created_at")}
    if checkpoint.get("version") != VERSION:
        return {**report, "status": "FAILED", "reason": "UNKNOWN_CHECKPOINT_VERSION"}
    expected = _signature(body)
    if expected and checkpoint.get("hmac_sha256") and not hmac.compare_digest(expected, checkpoint["hmac_sha256"]):
        return {**report, "status": "FAILED", "reason": "CHECKPOINT_SIGNATURE_INVALID"}
    report["signature"] = "VERIFIED" if expected and checkpoint.get("hmac_sha256") else "NOT_SIGNED_OR_NO_KEY"
    for name, (connect, table, fields) in chains().items():
        saved = checkpoint["chains"].get(name)
        rows = chain_rows(connect, table, fields)
        current = verify_records(rows, fields)
        if saved is None:
            result = {"status": "NOT_IN_CHECKPOINT", "length": current["checked"]}
        elif current["status"] != "PASS":
            result = {"status": "FAILED", "reason": "CHAIN_BROKEN", "detail": current.get("reason")}
        elif len(rows) < saved["length"]:
            result = {"status": "FAILED", "reason": "RECORDS_MISSING_SINCE_CHECKPOINT",
                      "checkpoint_length": saved["length"], "current_length": len(rows)}
        elif saved["length"] and rows[saved["length"] - 1][fields.index("entry_hash")] != saved["head_hash"]:
            result = {"status": "FAILED", "reason": "CHECKPOINTED_RECORD_CHANGED_OR_DATABASE_REPLACED"}
        elif not saved["length"] and saved["head_hash"] != "GENESIS":
            result = {"status": "FAILED", "reason": "CHECKPOINT_INCONSISTENT"}
        else:
            result = {"status": "PASS", "checkpoint_length": saved["length"], "current_length": len(rows),
                      "added_since": len(rows) - saved["length"]}
        report["chains"][name] = result
        if result["status"] == "FAILED":
            report["status"] = "FAILED"
    report["limitation"] = ("Records added after the checkpoint are covered only by the next checkpoint; "
                            "keep checkpoints where the database's operator cannot alter them.")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    from presentation.backend.app.backup import default_dir
    w = sub.add_parser("write"); w.add_argument("--out-dir", default=default_dir("checkpoints"),
                                                help="default: <DCG_BACKUP_DIR>/checkpoints")
    v = sub.add_parser("verify"); v.add_argument("--file", required=True)
    args = parser.parse_args(argv)
    if args.command == "write":
        if not args.out_dir:
            parser.error("give --out-dir or set DCG_BACKUP_DIR")
        path, checkpoint = write(args.out_dir)
        print(f"Checkpoint written: {path}")
        print(json.dumps(checkpoint["chains"], indent=2))
        return 0
    report = verify(json.loads(Path(args.file).read_text(encoding="utf-8")))
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
