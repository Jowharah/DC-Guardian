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

def verify_records(rows):
    previous="GENESIS"
    checked=0
    for row in rows:
        record=dict(zip(FIELDS,row))
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
