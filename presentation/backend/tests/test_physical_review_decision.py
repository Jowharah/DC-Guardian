import pytest
from presentation.backend.app.physical_review_decision import assess_review

def test_noncompliant_is_review_not_confirmed_violation():
    result=assess_review({"overall_status":"NON_COMPLIANT"},{"recognition_status":"RECOGNIZED"},"PARTIALLY_SUPPORTED")
    assert result["status"]=="EVIDENCE_REVIEW_REQUIRED"
    assert result["severity"] is None
    assert result["confirmed_ppe_violation"] is False
    assert result["identity_link_established"] is False
    assert result["autonomous_action_allowed"] is False

def test_compliant_recognized_is_observation_only():
    result=assess_review({"overall_status":"COMPLIANT"},{"recognition_status":"RECOGNIZED"},"SUPPORTED")
    assert result["status"]=="OBSERVATION_RECORDED"
    assert result["severity"] is None

def test_unrecognized_face_requires_review():
    result=assess_review({"overall_status":"COMPLIANT"},{"recognition_status":"UNKNOWN"},"SUPPORTED")
    assert "FACE_RECOGNITION_NOT_ESTABLISHED" in result["reasons"]

def test_insufficient_grounding_requires_review():
    result=assess_review({"overall_status":"COMPLIANT"},{"recognition_status":"RECOGNIZED"},"INSUFFICIENT")
    assert result["status"]=="EVIDENCE_REVIEW_REQUIRED"

def test_invalid_assessment_fails_closed():
    with pytest.raises(ValueError):
        assess_review({"overall_status":"INVALID"},{"recognition_status":"RECOGNIZED"},"SUPPORTED")
