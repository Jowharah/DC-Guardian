import hashlib
import json
from presentation.backend.app.review_integrity import FIELDS,verify_records

def entry(previous="GENESIS",**changes):
    record={"audit_id":"A1","group_id":"G1","zone_id":"ZONE-A",
            "reviewer":"operator","recorded_at":"2026-10-10T00:00:00+00:00",
            "outcome":"INCONCLUSIVE","rationale":"Requires additional verification.",
            "evidence_signature":"abc","policy_version":"v1",
            "review_status":"EVIDENCE_REVIEW_REQUIRED","previous_hash":previous}
    record.update(changes)
    record["entry_hash"]=hashlib.sha256(json.dumps(record,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return tuple(record[k] for k in FIELDS)

def test_empty_chain():
    assert verify_records([])["status"]=="PASS"

def test_valid_two_record_chain():
    first=entry()
    second=entry(first[-1],audit_id="A2")
    assert verify_records([first,second])["checked"]==2
    assert verify_records([first,second])["status"]=="PASS"

def test_changed_rationale_detected():
    row=list(entry())
    row[FIELDS.index("rationale")]="Modified rationale"
    assert verify_records([row])["reason"]=="ENTRY_HASH_MISMATCH"

def test_missing_middle_entry_detected():
    first=entry()
    second=entry(first[-1],audit_id="A2")
    third=entry(second[-1],audit_id="A3")
    assert verify_records([first,third])["reason"]=="PREVIOUS_HASH_MISMATCH"
