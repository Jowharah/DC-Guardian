"""Human verdicts on individual Evidence: audit chain, validation and downstream effect."""
import sqlite3
import pytest
from fastapi import HTTPException
from presentation.backend.app import evidence_review as review
from presentation.backend.app import correlation_pairs as pairs
from presentation.backend.app.authorization import Principal
from presentation.backend.app.incident_store import _db_path

ADMIN=Principal("operator",frozenset({"administrator"}),frozenset({"ZONE-B"}))
SAFETY=Principal("safety",frozenset({"safety_operator"}),frozenset({"ZONE-B"}))
VIEWER=Principal("viewer",frozenset({"viewer"}),frozenset({"ZONE-B"}))
PPE={"kind":"ppe","evidence_id":"PPE-IMG-1","zone_id":"ZONE-B",
     "source_assessment":{"assessment":{"overall_status":"NON_COMPLIANT"}}}

@pytest.fixture(autouse=True)
def ppe_evidence(monkeypatch):
    monkeypatch.setattr(review,"authorized_context",lambda kind,eid,p:PPE)

def verdict(principal=ADMIN,**fields):
    payload={"verdict":"OVERRIDDEN","corrected_status":"COMPLIANT",
             "rationale":"Vest visible under jacket; model missed it.","acknowledgment":True,**fields}
    return review.record_evidence_review("ppe","PPE-IMG-1",review.EvidenceReviewInput(**payload),principal)

def test_override_keeps_model_output_and_sets_effective_status():
    entry=verdict()
    assert entry["model_status"]=="NON_COMPLIANT"
    assert entry["detector_output_modified"] is False
    result=review.list_evidence_reviews("ppe","PPE-IMG-1",ADMIN)
    assert result["effective"]["effective_status"]=="COMPLIANT"
    assert result["effective"]["abnormal"] is False
    assert result["effective"]["source"]=="HUMAN_OVERRIDE"
    assert review.overrides()=={("ppe","PPE-IMG-1"):False}

def test_latest_verdict_wins_and_confirmation_removes_override():
    verdict()
    verdict(verdict="CONFIRMED",corrected_status=None,rationale="Second look: vest really is missing.")
    assert review.overrides()=={}
    effective=review.list_evidence_reviews("ppe","PPE-IMG-1",ADMIN)["effective"]
    assert effective["effective_status"]=="NON_COMPLIANT"
    assert len(review.rows())==2

@pytest.mark.parametrize("fields,status",[
    ({"corrected_status":"WEARING_HAT"},422),
    ({"corrected_status":"NON_COMPLIANT"},422),
    ({"verdict":"CONFIRMED","corrected_status":"COMPLIANT"},422),
    ({"acknowledgment":False},422)])
def test_invalid_verdicts_rejected(fields,status):
    with pytest.raises(HTTPException) as exc:
        verdict(**fields)
    assert exc.value.status_code==status
    assert review.rows()==[]

def test_domain_operator_can_review_but_viewer_cannot():
    verdict(SAFETY)
    with pytest.raises(HTTPException) as exc:
        verdict(VIEWER)
    assert exc.value.status_code==403

def test_tampered_chain_blocks_new_verdicts():
    verdict()
    with sqlite3.connect(_db_path()) as db:
        db.execute("UPDATE evidence_review_audit SET corrected_status='NON_COMPLIANT'")
    from presentation.backend.app.review_integrity import verify_evidence_database
    with review.connect() as db:
        assert verify_evidence_database(db)["reason"]=="ENTRY_HASH_MISMATCH"
    with pytest.raises(HTTPException) as exc:
        verdict()
    assert exc.value.status_code==409

def test_audit_integrity_reports_both_chains():
    from presentation.backend.app.human_review_audit import audit_integrity
    verdict()
    result=audit_integrity(ADMIN)
    assert result["status"]=="PASS"
    assert result["evidence_chain"]["checked"]==1
    assert result["unified_chain"]["checked"]==0

def test_cleared_evidence_leaves_pairs_but_keeps_group_links(monkeypatch):
    from presentation.backend.app.unified_correlations import edge
    monkeypatch.setattr(pairs,"specialized_edges",lambda p:[
        edge("PHYSICAL_IMAGE",("ppe","PPE-IMG-1"),("face","F1"),"PF1","ZONE-B"),
        edge("FACE_SSH_CONTEXT",("face","F1"),("ssh","S1"),"FS1","ZONE-B")])
    monkeypatch.setattr(pairs,"generic_edges",lambda p,h,n=None:[])
    assert len(pairs.all_edges(ADMIN))==2
    verdict()
    assert [e["source_id"] for e in pairs.all_edges(ADMIN)]==["FS1"]
    # Unified groups keep the cleared member's links so the group survives.
    assert len(pairs.all_edges(ADMIN,include_cleared=True))==2

def test_human_verdict_controls_generic_eligibility():
    from datetime import datetime,timezone
    t=datetime(2026,10,9,8,5,tzinfo=timezone.utc)
    ppe=pairs.node("ppe","P1","ZONE-B","PPE_NON_COMPLIANT",[t],"OPERATOR_DECLARED_UNVERIFIED")
    ssh=pairs.node("ssh","S1","ZONE-B","HIGH_CONFIDENCE_ANOMALY",[t],"X","SRV-1")
    assert len(pairs.generic_pairs([ppe,ssh]))==1
    # Clearing does not unlink here; all_edges filters cleared pairs.
    ppe["human_abnormal"]=False
    assert len(pairs.generic_pairs([ppe,ssh]))==1
    # A human can also escalate an event the detector judged normal.
    compliant=pairs.node("ppe","P2","ZONE-B","COMPLIANT",[t],"OPERATOR_DECLARED_UNVERIFIED")
    assert pairs.generic_pairs([compliant,ssh])==[]
    compliant["human_abnormal"]=True
    assert len(pairs.generic_pairs([compliant,ssh]))==1

def test_model_input_summary_excludes_rationale_and_reviewer():
    verdict()
    summary=review.summary("ppe","PPE-IMG-1")
    assert summary["effective_status"]=="COMPLIANT"
    assert "rationale" not in summary and "reviewer" not in summary
