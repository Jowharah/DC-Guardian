from presentation.backend.app.investigator_grounding import check_answer_references

def test_known_evidence_reference_is_recognized():
    result=check_answer_references("See SSH-EVT-ABC123.",[{"id":"SSH-EVT-ABC123"}])
    assert result["referenced_ids"]==["SSH-EVT-ABC123"]
    assert result["unrecognized_ids"]==[]
    assert result["claim_validation"]=="NOT_PERFORMED"

def test_unknown_reference_is_flagged():
    result=check_answer_references("See FACE-IMG-UNKNOWN.",[{"id":"FACE-IMG-KNOWN"}])
    assert result["status"]=="UNVERIFIED_REFERENCES"
    assert result["unrecognized_ids"]==["FACE-IMG-UNKNOWN"]

def test_no_reference_is_not_a_verified_claim():
    result=check_answer_references("The device has definitely failed.",[])
    assert result["status"]=="REFERENCE_CHECK_ONLY"
    assert result["claim_validation"]=="NOT_PERFORMED"
