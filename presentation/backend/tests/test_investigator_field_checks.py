"""Numeric and identity claim checks for every Evidence domain and multi-member contexts."""
from presentation.backend.app.investigator_field_checks import context_field_checks,compare

MAINT={"event_id":"MAINT-1","server_id":"SRV-B1-01","assessment":{"assessment":"AT_RISK",
       "failure_probability":0.6414665286404415,"operating_threshold":0.45,"failure_horizon_days":7}}
ENV={"event_id":"ENV-1","assessment":{"assessment":"HIGH_TEMPERATURE","measurements":{"temperature_c":38.0,"humidity_pct":50.0},
     "evidence":{"thresholds":{"temperature_high_c":35.0,"humidity_low_pct":20.0,"humidity_high_pct":80.0}}}}
PPE={"observation_id":"PPE-1","assessment":{"overall_status":"NON_COMPLIANT","person_count":2,
     "people":[{"status":"COMPLIANT"},{"status":"NON_COMPLIANT"}]}}
FACE={"observation_id":"FACE-1","assessment":{"recognition_status":"RECOGNIZED","person_id":"P005",
      "similarity":0.7130162715911865,"distance":0.2869837284088135,"threshold":0.5}}

def statuses(result):
    return {(c["field"],c["claim"]):c["status"] for c in result["checks"]}

def test_maintenance_claims_respect_rounding_and_flag_errors():
    answer=("The model estimated a failure probability of 64.15% against an operating threshold of 0.45.\n"
            "This is a 7-day prediction horizon.\nRisk score: 71%")
    result=context_field_checks(answer,[("maintenance","MAINT-1",MAINT)])
    got={c["field"]:c["status"] for c in result["checks"] if c["claim"]!="Risk score: 71%"}
    assert got=={"failure_probability":"MATCH","operating_threshold":"MATCH","failure_horizon_days":"MATCH"}
    assert any(c["claim"]=="Risk score: 71%" and c["status"]=="MISMATCH" for c in result["checks"])
    assert result["status"]=="MISMATCH"

def test_environment_temperature_and_threshold_are_not_confused():
    answer="The temperature reading was 38.0 °C, above the high-temperature threshold of 35 °C. Humidity was 50%."
    result=context_field_checks(answer,[("environment","ENV-1",ENV)])
    assert {c["field"]:c["status"] for c in result["checks"]}=={
        "temperature_c":"MATCH","temperature_high_c":"MATCH","humidity_pct":"MATCH"}
    wrong=context_field_checks("The temperature was 41 °C.",[("environment","ENV-1",ENV)])
    assert wrong["checks"][0]["status"]=="MISMATCH" and wrong["checks"][0]["source_value"]==38.0

def test_ppe_counts_accept_number_words_and_are_exact():
    answer="Two persons were detected; one person is non-compliant and 1 compliant."
    result=context_field_checks(answer,[("ppe","PPE-1",PPE)])
    assert {c["field"]:c["status"] for c in result["checks"]}=={
        "person_count":"MATCH","non_compliant_count":"MATCH","compliant_count":"MATCH"}
    wrong=context_field_checks("3 people were detected.",[("ppe","PPE-1",PPE)])
    assert wrong["status"]=="MISMATCH"

def test_face_similarity_and_identity():
    ok=context_field_checks("Recognized P005 with a similarity of 0.713 (distance: 0.287).",[("face","FACE-1",FACE)])
    assert all(c["status"]=="MATCH" for c in ok["checks"]) and len(ok["checks"])==3
    invented=context_field_checks("The person is P007.",[("face","FACE-1",FACE)])
    assert invented["checks"][0]["field"]=="person_id" and invented["checks"][0]["status"]=="MISMATCH"

def test_identity_without_face_evidence_is_flagged():
    result=context_field_checks("P005 caused the SSH failures.",[("ssh","SSH-1",{"evidence_state":"HIGH_CONFIDENCE_ANOMALY"})])
    assert result["checks"][-1]["status"]=="MISMATCH" and result["checks"][-1]["source_value"] is None

def test_pair_checks_each_member_against_its_own_record():
    answer="The temperature was 38 °C and the failure probability is 0.64."
    result=context_field_checks(answer,[("maintenance","MAINT-1",MAINT),("environment","ENV-1",ENV)])
    assert {(c["domain"],c["status"]) for c in result["checks"]}=={("maintenance","MATCH"),("environment","MATCH")}
    assert {c["evidence_id"] for c in result["checks"]}=={"MAINT-1","ENV-1"}

def test_several_members_of_one_domain_are_skipped_not_guessed():
    other={**ENV,"assessment":{**ENV["assessment"],"measurements":{"temperature_c":22.0}}}
    result=context_field_checks("The temperature was 22 °C.",[("environment","E1",ENV),("environment","E2",other)])
    assert result["checks"]==[]
    assert result["skipped"]==[{"domain":"environment","reason":"AMBIGUOUS_MULTIPLE_MEMBERS","count":2}]

def test_missing_source_field_is_never_zero():
    result=context_field_checks("The humidity was 0%.",[("environment","ENV-1",{"assessment":{}})])
    assert result["checks"][0]["status"]=="SOURCE_FIELD_UNAVAILABLE"

def test_unlabelled_numbers_are_not_assessed():
    result=context_field_checks("Around 38 things happened at 7 places.",[("environment","ENV-1",ENV)])
    assert result["status"]=="NO_RECOGNIZED_CLAIMS"

def test_ssh_checks_still_apply_in_context():
    result=context_field_checks("6 failed login attempts were recorded.",[("ssh","SSH-1",{"metrics":{"failed_login_count":6}})])
    assert result["checks"][0]["status"]=="MATCH" and result["checks"][0]["domain"]=="ssh"

def test_compare_precision_rules():
    assert compare("64%",0.6414,"ratio")=="MATCH"
    assert compare("64.1%",0.6414,"ratio")=="MATCH"
    assert compare("60%",0.6414,"ratio")=="MISMATCH"
    assert compare("7",7,"count")=="MATCH" and compare("8",7,"count")=="MISMATCH"
    assert compare("38",38.4,"value")=="MATCH" and compare("39",38.0,"value")=="MISMATCH"
