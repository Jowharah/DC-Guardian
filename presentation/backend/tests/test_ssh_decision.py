"""Standalone SSH decisions reuse unchanged deterministic policy."""
import pytest
from presentation.backend.app.ssh_decision import decide_standalone_ssh

ASSESSMENT={"evidence_state":"HIGH_CONFIDENCE_ANOMALY","source_ip":"192.0.2.1",
            "window_start":"2000-12-10T07:10:00"}
CORRELATION={"status":"NO_CORRELATION"}
SPECIALIST={"specialist_id":"cybersecurity","grounding_status":"PARTIALLY_SUPPORTED",
            "confirmed_compromise":False}

def test_standalone_ssh_decision_uses_v1_rules():
    result=decide_standalone_ssh(ASSESSMENT,CORRELATION,SPECIALIST)
    assert result["severity"]=="MEDIUM"
    assert result["autonomous_action_allowed"] is False
    assert result["response_mode"]=="HUMAN_REVIEW"
    assert "CYBERSECURITY_ANOMALY_EVIDENCE" in result["decision_rules_triggered"]

def test_no_correlation_not_assumed():
    with pytest.raises(ValueError):
        decide_standalone_ssh(ASSESSMENT,{"status":"NOT_RUN"},SPECIALIST)

def test_compromise_not_inferred():
    with pytest.raises(ValueError):
        decide_standalone_ssh(ASSESSMENT,CORRELATION,{**SPECIALIST,"confirmed_compromise":True})

def test_normal_state_not_eligible():
    with pytest.raises(ValueError):
        decide_standalone_ssh({**ASSESSMENT,"evidence_state":"NO_ANOMALY_EVIDENCE"},
                              CORRELATION,SPECIALIST)

def test_insufficient_grounding_requires_evidence_review():
    result=decide_standalone_ssh(ASSESSMENT,CORRELATION,{**SPECIALIST,"grounding_status":"INSUFFICIENT"})
    assert result["incident_status"]=="EVIDENCE_REVIEW_REQUIRED"
