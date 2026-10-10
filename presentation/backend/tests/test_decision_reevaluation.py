"""Decisions re-evaluated on human-verified inputs; originals never modified."""
import json
import pytest
from fastapi import HTTPException
from presentation.backend.app import decision_reevaluation as reeval
from presentation.backend.app import evidence_review as review
from presentation.backend.app.authorization import Principal

ADMIN=Principal("operator",frozenset({"administrator"}),frozenset({"ZONE-B"}))
SECURITY=Principal("sec",frozenset({"security_operator"}),frozenset({"ZONE-B"}))
SSH_ID="SSH-EVT-1"
ORIGINAL={"incident_status":"REVIEW_REQUIRED","severity":"MEDIUM","response_mode":"HUMAN_REVIEW",
          "escalation_required":False,"autonomous_action_allowed":False,
          "decision_rules_triggered":["CYBERSECURITY_ANOMALY_EVIDENCE"],"rationale":[]}
PAYLOAD={"evidence_state":"HIGH_CONFIDENCE_ANOMALY","source_ip":"203.0.113.9","window_start":"2026-10-09T08:00:00+00:00"}

@pytest.fixture
def saved_ssh(monkeypatch):
    from presentation.backend.app import ssh_publication
    with ssh_publication.connect() as db:
        db.execute("INSERT INTO ssh_published_evidence VALUES (?,?,?,?,?,?,?)",
                   (SSH_ID,"PV1",0,"2026-10-09T08:01:00+00:00","ZONE-B","SRV-B1-01",json.dumps(PAYLOAD)))
    ssh_publication.save_decision(SSH_ID,ORIGINAL,
        {"specialist_id":"cybersecurity","grounding_status":"SUPPORTED","confirmed_compromise":False},
        {"status":"NO_CORRELATION"})
    monkeypatch.setattr(review,"authorized_context",lambda kind,eid,p:{
        "kind":"ssh","evidence_id":eid,"zone_id":"ZONE-B","source_assessment":PAYLOAD})

def override(status="BENIGN",verdict="OVERRIDDEN"):
    review.record_evidence_review("ssh",SSH_ID,review.EvidenceReviewInput(
        verdict=verdict,corrected_status=status if verdict=="OVERRIDDEN" else None,
        rationale="Known administrator mistyping the password.",acknowledgment=True),ADMIN)

def view():
    from presentation.backend.app.ssh_publication import load_decision
    return reeval.ssh_view(SSH_ID,load_decision(SSH_ID))

def test_no_verdict_means_no_flag(saved_ssh):
    v=view()
    assert v["decision"]["severity"]=="MEDIUM"
    assert v["input_review"]["reevaluation_required"] is False

def test_override_flags_but_does_not_change_decision(saved_ssh):
    override()
    v=view()
    assert v["input_review"]["reevaluation_required"] is True
    assert v["input_review"]["changed_inputs"]==["ssh:"+SSH_ID]
    assert v["decision"]["severity"]=="MEDIUM"

def test_reevaluation_on_cleared_input_has_no_severity_and_keeps_original(saved_ssh):
    override()
    result=reeval.reevaluate_ssh(SSH_ID,ADMIN)
    assert result["decision"]["severity"] is None
    assert result["decision"]["incident_status"]=="INPUT_CLEARED_BY_HUMAN_VERDICT"
    assert result["inputs"]["ssh:"+SSH_ID]["verdict_audit_id"].startswith("DCG-ER-")
    v=view()
    assert v["decision"]["severity"] is None
    assert v["original_decision"]["severity"]=="MEDIUM"
    assert v["input_review"]["reevaluation_required"] is False
    from presentation.backend.app.ssh_publication import load_decision
    assert load_decision(SSH_ID)["decision"]==ORIGINAL

def test_reversing_override_flags_again_and_restores_rule_result(saved_ssh):
    override();reeval.reevaluate_ssh(SSH_ID,ADMIN)
    override(verdict="CONFIRMED")
    assert view()["input_review"]["reevaluation_required"] is True
    result=reeval.reevaluate_ssh(SSH_ID,ADMIN)
    assert result["decision"]["severity"]=="MEDIUM"
    assert "CYBERSECURITY_ANOMALY_EVIDENCE" in result["decision"]["decision_rules_triggered"]

def test_reevaluation_requires_decision_authority(saved_ssh):
    with pytest.raises(HTTPException) as exc:
        reeval.reevaluate_ssh(SSH_ID,SECURITY)
    assert exc.value.status_code==403

def test_reevaluation_without_saved_decision_conflicts(saved_ssh):
    with pytest.raises(HTTPException) as exc:
        reeval.reevaluate_ssh("SSH-EVT-MISSING",ADMIN)
    assert exc.value.status_code==404

def test_physical_disposition_uses_human_ppe_verdict():
    from presentation.backend.app.physical_review_decision import assess_review
    ppe={"overall_status":"NON_COMPLIANT"};face={"recognition_status":"RECOGNIZED"}
    detector=assess_review(ppe,face,"SUPPORTED")
    assert detector["reasons"]==["PPE_NON_COMPLIANT_DETECTOR_ASSESSMENT"]
    human=assess_review(ppe,face,"SUPPORTED",{"source":"HUMAN_OVERRIDE","effective_status":"COMPLIANT"})
    assert human["reasons"]==[] and human["status"]=="OBSERVATION_RECORDED"
    assert human["ppe_status_source"]=="HUMAN_OVERRIDE"
    escalated=assess_review({"overall_status":"COMPLIANT"},face,"SUPPORTED",
                            {"source":"HUMAN_OVERRIDE","effective_status":"NON_COMPLIANT"})
    assert escalated["reasons"]==["PPE_NON_COMPLIANT_HUMAN_VERDICT"]
    confirmed=assess_review(ppe,face,"SUPPORTED",{"source":"HUMAN_CONFIRMED","effective_status":"NON_COMPLIANT"})
    assert confirmed["ppe_status_source"]=="DETECTOR"
