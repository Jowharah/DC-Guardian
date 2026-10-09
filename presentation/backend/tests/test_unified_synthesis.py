from presentation.backend.app.unified_synthesis import synthesize

GROUP={"edges":[{"type":"FACE_SSH_CONTEXT","source_id":"FS-1"},
                {"type":"PHYSICAL_IMAGE","source_id":"PF-1"}]}
def test_synthesis_preserves_limits_and_no_decision():
    result=synthesize(GROUP,{
      "cybersecurity":{"grounding_status":"SUPPORTED","supported_findings":["Six failed logins"],"limitations":["No compromise proven"],"citations":[]},
      "physical_security":{"grounding_status":"PARTIALLY_SUPPORTED","supported_findings":["PPE detector non-compliance"],"limitations":["No identity link"],"citations":[]}})
    assert result["grounding_status"]=="PARTIALLY_SUPPORTED"
    assert len(result["supported_source_findings"])==2
    assert len(result["validated_contextual_links"])==2
    assert result["decision_severity"] is None
    assert result["identity_to_ssh_established"] is False
    assert result["identity_to_ppe_verified"] is False
    assert result["causal_relationship_established"] is False

def test_insufficient_specialist_not_used_as_supported_finding():
    result=synthesize(GROUP,{"cybersecurity":{"grounding_status":"INSUFFICIENT",
        "supported_findings":["Unsupported assertion"],"limitations":[],"citations":[]}})
    assert result["grounding_status"]=="INSUFFICIENT"
    assert result["supported_source_findings"]==[]

def test_empty_specialists_rejected():
    import pytest
    with pytest.raises(ValueError):
        synthesize(GROUP,{})
