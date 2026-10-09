"""Offline regression contracts: RBAC, duplicate publishing, and correlation boundaries."""
import pytest
from fastapi import HTTPException
from presentation.backend.app.authorization import Principal,Permission,allowed
from presentation.backend.app.authentication import authorize
from presentation.backend.app.unified_correlations import edge,group_edges
from presentation.backend.app.unified_decision import evaluate
from presentation.backend.app.face_ssh_specialists import signature

ADMIN=Principal("admin",frozenset({"administrator"}),frozenset({"ZONE-A","ZONE-B"}))
VIEWER=Principal("viewer",frozenset({"viewer"}),frozenset({"ZONE-A"}))
SECURITY=Principal("security",frozenset({"security_operator"}),frozenset({"ZONE-A"}))

@pytest.mark.parametrize("permission",[
    Permission.SSH_DETAIL,Permission.PERSON_DETAIL,Permission.CAMERA_DETAIL,
    Permission.MAINTENANCE_DETAIL,Permission.ENVIRONMENT_DETAIL,
    Permission.SCENARIO_EXECUTE])
def test_viewer_cannot_access_protected_evidence(permission):
    assert not allowed(VIEWER,permission,"ZONE-A")
    with pytest.raises(HTTPException) as exc:
        authorize(VIEWER,permission,"ZONE-A")
    assert exc.value.status_code==403

def test_zone_isolation_and_deny_unknown_role():
    assert not allowed(SECURITY,Permission.SSH_DETAIL,"ZONE-B")
    assert not allowed(Principal("x",frozenset({"unknown"}),frozenset({"ZONE-A"})),Permission.INCIDENT_READ,"ZONE-A")
    assert allowed(ADMIN,Permission.SSH_DETAIL,"ZONE-B")

def test_duplicate_edges_produce_one_stable_group():
    e=edge("FACE_SSH_CONTEXT",("face","F1"),("ssh","S1"),"FS1","ZONE-A")
    p=edge("PHYSICAL_IMAGE",("ppe","P1"),("face","F1"),"PF1","ZONE-A")
    original=group_edges([e,p])
    assert original==group_edges([p,e])
    assert len(original)==1
    assert len(original[0]["evidence"])==3
    assert original[0]["decision_severity"] is None

def test_zone_separation_prevents_cross_zone_grouping():
    a=edge("FACE_SSH_CONTEXT",("face","F1"),("ssh","S1"),"FS1","ZONE-A")
    b=edge("PHYSICAL_IMAGE",("ppe","P1"),("face","F1"),"PF1","ZONE-B")
    groups=group_edges([a,b])
    assert len(groups)==2
    assert {g["zone_id"] for g in groups}=={"ZONE-A","ZONE-B"}

def test_provisional_review_does_not_inherit_severity():
    group={"evidence":[{"kind":"ssh"},{"kind":"face"},{"kind":"ppe"}],
           "edges":[{"type":"FACE_SSH_CONTEXT"}]}
    result=evaluate(group,{"cybersecurity":{"grounding_status":"SUPPORTED","severity":"HIGH"}},
       {"recognition_status":"RECOGNIZED","zone_authorization":{
         "status":"UNAUTHORIZED","source":"NEO4J_READ_ONLY","reason":"GRAPH_RELATIONSHIP_CHECK"}})
    assert result["severity"] is None
    assert result["autonomous_action_allowed"] is False
    assert "RECOGNIZED_IDENTITY_NOT_AUTHORIZED_FOR_DECLARED_ZONE" in result["review_reasons"]

def test_saved_specialist_signature_changes_with_declared_context():
    item={"face_observation_id":"F1","ssh_event_id":"S1","zone_id":"ZONE-A",
          "face_capture_time":"2026-10-09T13:39:00Z",
          "ssh_context_time":"2026-10-09T13:35:00Z",
          "ssh_time_provenance":"OPERATOR_DECLARED_UNVERIFIED_TEST_TIME"}
    assert signature(item)!=signature({**item,"ssh_context_time":"2026-10-09T13:40:00Z"})
