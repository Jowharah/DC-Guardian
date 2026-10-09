import pytest
from presentation.backend.app.unified_decision import evaluate

GROUP={"evidence":[{"kind":"ssh"},{"kind":"ppe"},{"kind":"face"}],
       "edges":[{"type":"FACE_SSH_CONTEXT"},{"type":"PHYSICAL_IMAGE"}]}

def test_review_never_inherits_ssh_severity():
    result=evaluate(GROUP,{"cybersecurity":{"grounding_status":"SUPPORTED","severity":"MEDIUM"},
                           "physical_security":{"grounding_status":"PARTIALLY_SUPPORTED"}})
    assert result["status"]=="EVIDENCE_REVIEW_REQUIRED"
    assert result["response_mode"]=="HUMAN_REVIEW"
    assert result["severity"] is None
    assert result["standalone_severity_inherited"] is False
    assert result["autonomous_action_allowed"] is False
    assert result["identity_to_ssh_established"] is False

def test_insufficient_grounding_adds_review_reason():
    result=evaluate(GROUP,{"cybersecurity":{"grounding_status":"INSUFFICIENT"}})
    assert "SPECIALIST_GROUNDING_INSUFFICIENT" in result["review_reasons"]

def test_empty_specialists_rejected():
    with pytest.raises(ValueError):
        evaluate(GROUP,{})

def test_invalid_grounding_rejected():
    with pytest.raises(ValueError):
        evaluate(GROUP,{"cybersecurity":{"grounding_status":"INVALID"}})

def test_no_domains_does_not_assign_severity():
    result=evaluate({"evidence":[],"edges":[]},{"cybersecurity":{"grounding_status":"SUPPORTED"}})
    assert result["status"]=="OBSERVATION_RECORDED"
    assert result["severity"] is None
