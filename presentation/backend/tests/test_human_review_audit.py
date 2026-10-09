"""No AI calls or Neo4j required for local audit-contract tests."""
import sqlite3
import pytest
from fastapi import HTTPException
from presentation.backend.app import human_review_audit as audit
from presentation.backend.app.authorization import Principal

ADMIN=Principal("operator",frozenset({"administrator"}),frozenset({"ZONE-A"}))
VIEWER=Principal("viewer",frozenset({"viewer"}),frozenset({"ZONE-A"}))
GROUP={"id":"G1","zone_id":"ZONE-A","evidence":[{"kind":"face","observation_id":"F1"}],"edges":[]}

@pytest.fixture
def isolated(monkeypatch,tmp_path):
    monkeypatch.setattr(audit,"_db_path",lambda:tmp_path/"review.sqlite3")
    monkeypatch.setattr(audit,"find_group",lambda gid,p:GROUP)
    monkeypatch.setattr(audit,"read_review_decision",lambda gid,p:{
        "decision":{"status":"EVIDENCE_REVIEW_REQUIRED","policy_version":"TEST-v1"}})

def test_viewer_cannot_record_review(isolated):
    with pytest.raises(HTTPException) as exc:
        audit.review_record("G1",audit.ReviewInput(outcome="INCONCLUSIVE",
            rationale="Requires further verification.",acknowledgment=True),VIEWER)
    assert exc.value.status_code==403

def test_acknowledgment_is_required(isolated):
    with pytest.raises(HTTPException) as exc:
        audit.review_record("G1",audit.ReviewInput(outcome="INCONCLUSIVE",
            rationale="Requires further verification.",acknowledgment=False),ADMIN)
    assert exc.value.status_code==422

def test_append_only_records_and_hash_chain(isolated):
    payload=audit.ReviewInput(outcome="INCONCLUSIVE",
        rationale="Evidence requires operator follow-up.",acknowledgment=True)
    first=audit.review_record("G1",payload,ADMIN)
    second=audit.review_record("G1",payload,ADMIN)
    assert first["previous_hash"]=="GENESIS"
    assert second["previous_hash"]==first["entry_hash"]
    assert first["audit_id"]!=second["audit_id"]
    assert second["severity"] is None
    assert not second["autonomous_action_allowed"]
    with audit.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM human_review_audit").fetchone()[0]==2

def test_out_of_zone_admin_denied(isolated):
    other=Principal("other",frozenset({"administrator"}),frozenset({"ZONE-B"}))
    with pytest.raises(HTTPException) as exc:
        audit.review_record("G1",audit.ReviewInput(outcome="INCONCLUSIVE",
            rationale="Requires further verification.",acknowledgment=True),other)
    assert exc.value.status_code==403
