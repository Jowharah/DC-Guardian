"""Research P(Related) estimate attached to live correlation pairs."""
from datetime import datetime,timezone,timedelta
from presentation.backend.app import correlation_uncertainty as cu
from presentation.backend.app.correlation_pairs import node

T=datetime(2026,10,9,8,5,tzinfo=timezone.utc)

def face(state="UNAUTHORIZED"):
    return node("face","F1","ZONE-A",state,[T],"OPERATOR_DECLARED_UNVERIFIED")

def ssh(state="HIGH_CONFIDENCE_ANOMALY",at=T+timedelta(minutes=4),server="SRV-A1-01"):
    return node("ssh","S1","ZONE-A",state,[at],"X",server)

def test_unauthorized_face_and_ssh_matches_offline_model():
    from reasoning.uncertainty.bayesian_correlation import score_pair
    result=cu.score(face(),ssh())
    assert result["status"]==cu.STATUS and result["marginalized_factors"]==[]
    offline=score_pair(cu.model_event(face(),T),cu.model_event(ssh(),T+timedelta(minutes=4)))
    assert abs(result["probability_related"]-offline["probability_related"])<1e-3

def test_face_state_split_into_recognition_and_authorization():
    event=cu.model_event(face(),T)
    assert event["state"]=="RECOGNIZED" and event["authorization"]=="UNAUTHORIZED"

def test_rack_comes_from_topology():
    event=cu.model_event(ssh(),T)
    assert event["rack_id"]=="RACK-A1"

def test_unobservable_strength_is_marginalized_not_guessed():
    ppe=node("ppe","P1","ZONE-A","PPE_NON_COMPLIANT",[T],"OPERATOR_DECLARED_UNVERIFIED")
    result=cu.score(ppe,ssh())
    assert result["marginalized_factors"]==["EvidenceStrength"]
    assert "EvidenceStrength" not in {f["factor"] for f in result["factors"]}

def test_maintenance_probability_is_used():
    weak=node("maintenance","M1","ZONE-A","AT_RISK",[T],"X","SRV-A1-01",{"failure_probability":0.5})
    strong=node("maintenance","M1","ZONE-A","AT_RISK",[T],"X","SRV-A1-01",{"failure_probability":0.9})
    env=node("environment","E1","ZONE-A","HIGH_TEMPERATURE",[T],"X",attributes={"source_class":"ENVIRONMENTAL_SENSOR"})
    assert cu.score(strong,env)["probability_related"]>cu.score(weak,env)["probability_related"]

def test_normal_event_is_not_scored():
    result=cu.score(face("RECOGNIZED"),ssh())
    assert result["status"]=="NOT_SCORED" and "not abnormal" in result["reason"]

def test_missing_time_is_not_scored():
    result=cu.score(face(),ssh(at=None))
    assert result["status"]=="NOT_SCORED"

def test_estimate_is_display_only():
    pair={"members":[{"kind":"face","observation_id":"F1"},{"kind":"ssh","observation_id":"S1"}],
          "decision_severity":None}
    [scored]=cu.score_pairs([pair],[face(),ssh()])
    assert scored["decision_severity"] is None
    assert "never changes correlation" in scored["uncertainty"]["note"]
