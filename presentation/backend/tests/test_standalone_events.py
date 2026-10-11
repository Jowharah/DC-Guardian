"""Standalone evidence remains independent of incident Decision severity."""
from fastapi.testclient import TestClient
from presentation.backend.app.main import app
from presentation.backend.app.authentication import current_principal
from presentation.backend.app.authorization import Principal

def test_standalone_event_zone_scoping_and_no_severity(monkeypatch, tmp_path):
    monkeypatch.setenv("DCG_PRESENTATION_DB", str(tmp_path/"events.sqlite3"))
    client = TestClient(app)
    payload = {"domain":"CYBERSECURITY", "zone_id":"ZONE-B", "state":"REVIEW_REQUIRED",
               "title":"Synthetic SSH assessment", "asset_id":"SRV-B1-01", "description":"Controlled test"}
    try:
        app.dependency_overrides[current_principal] = lambda: Principal(
            "viewer",frozenset({"viewer"}),frozenset({"ZONE-B"}))
        assert client.post("/api/v1/events/standalone",json=payload).status_code == 403
        app.dependency_overrides[current_principal] = lambda: Principal(
            "admin",frozenset({"administrator"}),frozenset({"ZONE-B"}))
        response = client.post("/api/v1/events/standalone",json=payload)
        assert response.status_code == 201
        assert response.json()["decision_severity"] is None
        assert len(client.get("/api/v1/events/standalone").json()) == 1
        app.dependency_overrides[current_principal] = lambda: Principal(
            "viewer",frozenset({"viewer"}),frozenset({"ZONE-A"}))
        assert client.get("/api/v1/events/standalone").json() == []
    finally:
        app.dependency_overrides.pop(current_principal,None)

def test_asset_zone_mismatch_rejected(monkeypatch,tmp_path):
    monkeypatch.setenv("DCG_PRESENTATION_DB",str(tmp_path/"events.sqlite3"))
    client=TestClient(app)
    app.dependency_overrides[current_principal]=lambda:Principal(
        "admin",frozenset({"administrator"}),frozenset({"ZONE-A","ZONE-B"}))
    try:
        response=client.post("/api/v1/events/standalone",json={
            "domain":"CYBERSECURITY","zone_id":"ZONE-A","state":"REVIEW_REQUIRED",
            "title":"Controlled SSH test","asset_id":"SRV-B1-01","description":"Mismatch"})
        assert response.status_code==422
    finally:
        app.dependency_overrides.pop(current_principal,None)
