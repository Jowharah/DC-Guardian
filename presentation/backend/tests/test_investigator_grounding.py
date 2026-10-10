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

from presentation.backend.app.investigator_grounding import ssh_field_checks

def test_ssh_field_checks_match_numeric_metrics():
    source={"detector_votes":2,"metrics":{"failed_login_count":6,"failure_ratio":1.0}}
    result=ssh_field_checks("6 failed login attempts; 2 detector votes; failure ratio is 100%.",source)
    assert [c["status"] for c in result["checks"]]==["MATCH","MATCH","MATCH"]

def test_ssh_field_checks_flag_mismatch():
    result=ssh_field_checks("8 failed login attempts",{"metrics":{"failed_login_count":6}})
    assert result["status"]=="MISMATCH"
    assert result["checks"][0]["source_value"]==6

def test_ssh_field_checks_do_not_verify_unrecognized_prose():
    result=ssh_field_checks("A malicious attack occurred",{"metrics":{"failed_login_count":6}})
    assert result["status"]=="NO_RECOGNIZED_CLAIMS"
    assert result["checks"]==[]
