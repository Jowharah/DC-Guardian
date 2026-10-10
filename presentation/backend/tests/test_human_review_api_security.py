"""Review API security contracts, isolated from production Evidence and Neo4j."""
import pytest
from fastapi import HTTPException
from presentation.backend.app import human_review_audit as audit
from presentation.backend.app.authorization import Principal

ADMIN_A=Principal("admin-a",frozenset({"administrator"}),frozenset({"ZONE-A"}))
ADMIN_B=Principal("admin-b",frozenset({"administrator"}),frozenset({"ZONE-B"}))
VIEWER=Principal("viewer",frozenset({"viewer"}),frozenset({"ZONE-A"}))
GROUP={"id":"G1","zone_id":"ZONE-A","evidence":[{"kind":"face","observation_id":"F1"}],"edges":[]}

@pytest.fixture
def sandbox(monkeypatch,tmp_path):
    monkeypatch.setattr(audit,"_db_path",lambda:tmp_path/"reviews.sqlite3")
    monkeypatch.setattr(audit,"find_group",lambda group_id,principal:GROUP)
    monkeypatch.setattr(audit,"read_review_decision",lambda group_id,principal:{
        "decision":{"status":"EVIDENCE_REVIEW_REQUIRED","policy_version":"TEST-v1"}})

def payload():
    return audit.ReviewInput(outcome="NEEDS_FOLLOW_UP",
        rationale="Human review requires further investigation.",acknowledgment=True)

def test_cross_zone_submission_denied(sandbox):
    with pytest.raises(HTTPException) as error:
        audit.record_review("G1",payload(),ADMIN_B)
    assert error.value.status_code==403

def test_viewer_submission_denied(sandbox):
    with pytest.raises(HTTPException) as error:
        audit.record_review("G1",payload(),VIEWER)
    assert error.value.status_code==403

def test_reviewer_identity_comes_from_authenticated_principal(sandbox):
    result=audit.record_review("G1",payload(),ADMIN_A)
    assert result["reviewer"]=="admin-a"
    assert result["severity"] is None
    assert result["autonomous_action_allowed"] is False

def test_review_history_requires_group_visibility(sandbox,monkeypatch):
    original=audit.find_group
    def scoped(group_id,principal):
        if "ZONE-A" not in principal.zones:
            raise HTTPException(403,"Access denied")
        return original(group_id,principal)
    monkeypatch.setattr(audit,"find_group",scoped)
    audit.record_review("G1",payload(),ADMIN_A)
    with pytest.raises(HTTPException) as error:
        audit.list_reviews("G1",ADMIN_B)
    assert error.value.status_code==403
    records=audit.list_reviews("G1",ADMIN_A)["records"]
    assert len(records)==1 and records[0]["reviewer"]=="admin-a"

def test_invalid_outcome_and_short_rationale_rejected():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        audit.ReviewInput(outcome="APPROVE_ACCESS",
            rationale="A sufficiently long rationale.",acknowledgment=True)
    with pytest.raises(ValidationError):
        audit.ReviewInput(outcome="INCONCLUSIVE",rationale="short",acknowledgment=True)
