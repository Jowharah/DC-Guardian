"""Reasoning-contract pair rule for domain combinations without a dedicated matcher."""
from datetime import datetime,timezone,timedelta
from presentation.backend.app import correlation_pairs as pairs
from presentation.backend.app.correlation_pairs import node,generic_pairs,instant,as_pair

T=datetime(2026,10,9,8,5,tzinfo=timezone.utc)

def ssh(oid="S1",zone="ZONE-B",state="HIGH_CONFIDENCE_ANOMALY",at=T,server="SRV-1"):
    return node("ssh",oid,zone,state,[at],"OPERATOR_DECLARED_UNVERIFIED_TEST_TIME",server)

def maint(oid="M1",zone="ZONE-B",state="AT_RISK",at=T+timedelta(minutes=6),server="SRV-1"):
    return node("maintenance",oid,zone,state,[at],"MODEL_OBSERVATION_TIMESTAMP",server)

def test_abnormal_events_in_zone_window_form_a_pair():
    [e]=generic_pairs([ssh(),maint()])
    assert e["type"]=="REASONING_CONTEXT"
    assert e["details"]["scope"]=="SERVER"
    assert e["details"]["time_difference_seconds"]==360
    assert e["source_id"].startswith("DCG-PAIR-")

def test_different_servers_fall_back_to_zone_scope():
    [e]=generic_pairs([ssh(),maint(server="SRV-2")])
    assert e["details"]["scope"]=="ZONE"

def test_normal_state_zone_mismatch_and_window_are_rejected():
    assert generic_pairs([ssh(state="NO_ANOMALY_EVIDENCE"),maint()])==[]
    assert generic_pairs([ssh(),maint(state="HEALTHY")])==[]
    assert generic_pairs([ssh(),maint(zone="ZONE-A")])==[]
    assert generic_pairs([ssh(),maint(at=T+timedelta(minutes=15,seconds=1))])==[]

def test_events_without_trustworthy_time_never_pair():
    assert generic_pairs([ssh(at=None),maint()])==[]
    # Naive timestamps are never assumed to be UTC.
    assert instant("2026-10-09T08:05:00") is None
    assert instant("2026-10-09T08:05:00Z")==T

def test_dedicated_matcher_combinations_are_not_duplicated():
    face=node("face","F1","ZONE-B","UNKNOWN_PERSON",[T],"OPERATOR_DECLARED_UNVERIFIED")
    ppe=node("ppe","P1","ZONE-B","PPE_NON_COMPLIANT",[T],"OPERATOR_DECLARED_UNVERIFIED")
    env=node("environment","E1","ZONE-B","HIGH_TEMPERATURE",[T],"SENSOR_READING_TIMESTAMP")
    kinds={frozenset((e["left"][0],e["right"][0])) for e in generic_pairs([face,ppe,ssh(),maint(),env])}
    assert not kinds & pairs.SPECIALIZED
    assert frozenset(("face","maintenance")) in kinds
    assert frozenset(("ppe","ssh")) in kinds

def test_same_domain_events_do_not_pair():
    assert generic_pairs([ssh("S1"),ssh("S2")])==[]

def test_closest_abnormal_reading_is_used():
    env=node("environment","E1","ZONE-B","HIGH_TEMPERATURE",
             [T-timedelta(hours=2),T+timedelta(minutes=10)],"SENSOR_READING_TIMESTAMP")
    [e]=generic_pairs([ssh(),env])
    assert e["details"]["time_difference_seconds"]==600

def test_pair_id_is_order_independent():
    a=generic_pairs([ssh(),maint()]);b=generic_pairs([maint(),ssh()])
    assert a==b

def test_pair_view_never_carries_severity_except_operational():
    [e]=generic_pairs([ssh(),maint()])
    view=as_pair(e,{e["source_id"]:"HIGH"})
    assert view["decision_severity"] is None
    assert view["causal_relationship_established"] is False
    assert [m["kind"] for m in view["members"]]==["maintenance","ssh"]

def test_face_graph_failure_is_never_unauthorized(monkeypatch):
    from presentation.backend.app import face_zone_authorization
    monkeypatch.setattr(face_zone_authorization,"assess",lambda p,z:{"status":"UNKNOWN"})
    assert pairs.face_state({"recognition_status":"RECOGNIZED","person_id":"P1"},"ZONE-B")=="RECOGNIZED"
    monkeypatch.setattr(face_zone_authorization,"assess",lambda p,z:{"status":"UNAUTHORIZED"})
    assert pairs.face_state({"recognition_status":"RECOGNIZED","person_id":"P1"},"ZONE-B")=="UNAUTHORIZED"
    assert pairs.face_state({"recognition_status":"UNKNOWN"},"ZONE-B")=="UNKNOWN_PERSON"
