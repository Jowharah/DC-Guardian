import pytest
from presentation.backend.app.operational_decision import make_decision

def candidate():
    return {"status":"CORRELATION_CANDIDATE","zone_id":"ZONE-B",
      "time_difference_seconds":360,
      "maintenance":{"zone_id":"ZONE-B","assessment":{"assessment":"AT_RISK"},
         "workflow":{"graph_event_id":"MAINT-EVT-TEST-MAPPED"}},
      "environment":{"zone_id":"ZONE-B",
         "evidence_event_ids":["ENV-EVT-TEST"]}}

def test_correlated_decision_uses_v1():
    decision=make_decision(candidate(),{"grounding_status":"SUPPORTED"})
    assert decision["severity"]=="MEDIUM"
    assert decision["incident_status"]=="REVIEW_REQUIRED"
    assert decision["autonomous_action_allowed"] is False
    assert "CORRELATED_OPERATIONAL_RISK" in decision["decision_rules_triggered"]

def test_insufficient_grounding_requires_evidence_review():
    result=make_decision(candidate(),{"grounding_status":"INSUFFICIENT"})
    assert result["incident_status"]=="EVIDENCE_REVIEW_REQUIRED"

def test_rejects_out_of_window():
    item=candidate();item["time_difference_seconds"]=901
    with pytest.raises(ValueError):make_decision(item,{"grounding_status":"SUPPORTED"})

def test_rejects_missing_graph_provenance():
    item=candidate();item["maintenance"]["workflow"]["graph_event_id"]=None
    with pytest.raises(ValueError):make_decision(item,{"grounding_status":"SUPPORTED"})

def test_rejects_unsupported_grounding():
    with pytest.raises(ValueError):make_decision(candidate(),{"grounding_status":"UNKNOWN"})
