"""HTTP-level RBAC regression for local human-review endpoints.

Uses temporary credentials and a stubbed group lookup; never touches private
Evidence, model artifacts, or the real audit database.
"""
import pytest
from fastapi.testclient import TestClient
from presentation.backend.app.main import app
from presentation.backend.app import human_review_audit as audit

client=TestClient(app)
GROUP={"id":"G1","zone_id":"ZONE-A","evidence":[{"kind":"face","observation_id":"F1"}],"edges":[]}
PASSWORD="local-test-only-password"
PAYLOAD={"outcome":"NEEDS_FOLLOW_UP","rationale":"Requires further investigation of source evidence.",
         "acknowledgment":True}

@pytest.fixture
def setup(monkeypatch,tmp_path):
    monkeypatch.setenv("DCG_LOCAL_USER","test-operator")
    monkeypatch.setenv("DCG_LOCAL_PASSWORD",PASSWORD)
    monkeypatch.setenv("DCG_LOCAL_ROLE","administrator")
    monkeypatch.setenv("DCG_LOCAL_ZONES","ZONE-A")
    monkeypatch.setattr(audit,"_db_path",lambda:tmp_path/"reviews.sqlite3")
    monkeypatch.setattr(audit,"find_group",lambda gid,principal:GROUP)
    monkeypatch.setattr(audit,"read_review_decision",lambda gid,principal:{
        "decision":{"status":"EVIDENCE_REVIEW_REQUIRED","policy_version":"TEST-v1"}})

def request(method,path,**kwargs):
    return client.request(method,path,auth=("test-operator",PASSWORD),**kwargs)

def test_review_routes_require_login(setup):
    path="/api/v1/reviews/unified/G1/records"
    assert client.get(path).status_code==401
    assert client.post(path,json=PAYLOAD).status_code==401
    assert client.get("/api/v1/reviews/audit-integrity").status_code==401

def test_review_post_rejects_viewer_and_wrong_zone(setup,monkeypatch):
    path="/api/v1/reviews/unified/G1/records"
    monkeypatch.setenv("DCG_LOCAL_ROLE","viewer")
    assert request("POST",path,json=PAYLOAD).status_code==403
    monkeypatch.setenv("DCG_LOCAL_ROLE","administrator")
    monkeypatch.setenv("DCG_LOCAL_ZONES","ZONE-B")
    assert request("POST",path,json=PAYLOAD).status_code==403
    assert request("GET",path).status_code==403

def test_integrity_route_is_admin_only(setup,monkeypatch):
    monkeypatch.setenv("DCG_LOCAL_ROLE","security_operator")
    assert request("GET","/api/v1/reviews/audit-integrity").status_code==403
    monkeypatch.setenv("DCG_LOCAL_ROLE","administrator")
    result=request("GET","/api/v1/reviews/audit-integrity")
    assert result.status_code==200
    assert result.json()["status"]=="PASS"

def test_authenticated_review_round_trip(setup):
    path="/api/v1/reviews/unified/G1/records"
    response=request("POST",path,json=PAYLOAD)
    assert response.status_code==201
    record=response.json()
    assert record["reviewer"]=="test-operator"
    assert record["severity"] is None
    assert record["autonomous_action_allowed"] is False
    history=request("GET",path)
    assert history.status_code==200
    assert len(history.json()["records"])==1
    assert history.json()["records"][0]["audit_id"]==record["audit_id"]
    assert request("GET","/api/v1/reviews/audit-integrity").json()["status"]=="PASS"
