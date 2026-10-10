"""Read-only verification of the local human-review audit hash chain.

This is a consistency check, not proof against database replacement or
deletion of a trailing suffix. An external trusted checkpoint is required
for those stronger guarantees.
"""
import hashlib
import json

FIELDS=("audit_id","group_id","zone_id","reviewer","recorded_at",
        "outcome","rationale","evidence_signature","policy_version",
        "review_status","previous_hash","entry_hash")
# Separate chain for human verdicts on individual Evidence.
EVIDENCE_FIELDS=("audit_id","kind","evidence_id","zone_id","reviewer","recorded_at",
        "verdict","corrected_status","model_status","rationale","previous_hash","entry_hash")

def verify_records(rows,fields=FIELDS):
    previous="GENESIS"
    checked=0
    for row in rows:
        record=dict(zip(fields,row))
        recorded=record.pop("entry_hash")
        calculated=hashlib.sha256(json.dumps(record,sort_keys=True,separators=(",",":")).encode()).hexdigest()
        checked+=1
        if record["previous_hash"]!=previous:
            return {"status":"FAILED","checked":checked,"reason":"PREVIOUS_HASH_MISMATCH","audit_id":record["audit_id"]}
        if recorded!=calculated:
            return {"status":"FAILED","checked":checked,"reason":"ENTRY_HASH_MISMATCH","audit_id":record["audit_id"]}
        previous=recorded
    return {"status":"PASS","checked":checked,"head_hash":previous,
            "limitation":"No trusted external checkpoint; deletion of trailing records or replacement of the database cannot be detected."}

def verify_database(db):
    rows=db.execute("SELECT "+",".join(FIELDS)+" FROM human_review_audit ORDER BY rowid ASC").fetchall()
    return verify_records(rows)

def verify_evidence_database(db):
    db.execute("""CREATE TABLE IF NOT EXISTS evidence_review_audit(
        audit_id TEXT PRIMARY KEY, kind TEXT NOT NULL, evidence_id TEXT NOT NULL,
        zone_id TEXT NOT NULL, reviewer TEXT NOT NULL, recorded_at TEXT NOT NULL,
        verdict TEXT NOT NULL, corrected_status TEXT, model_status TEXT,
        rationale TEXT NOT NULL, previous_hash TEXT NOT NULL, entry_hash TEXT NOT NULL)""")
    rows=db.execute("SELECT "+",".join(EVIDENCE_FIELDS)+" FROM evidence_review_audit ORDER BY rowid ASC").fetchall()
    return verify_records(rows,EVIDENCE_FIELDS)
