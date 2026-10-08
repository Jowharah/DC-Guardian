"""Local authentication boundary tests (never use credentials committed to Git)."""
from fastapi.testclient import TestClient
from presentation.backend.app.main import app

client = TestClient(app)

def test_missing_credentials_rejected(monkeypatch):
    monkeypatch.setenv("DCG_LOCAL_USER","test-admin")
    monkeypatch.setenv("DCG_LOCAL_PASSWORD","not-a-real-password")
    monkeypatch.setenv("DCG_LOCAL_ROLE","administrator")
    monkeypatch.setenv("DCG_LOCAL_ZONES","ZONE-B")
    assert client.get("/api/v1/incidents").status_code == 401

def test_bad_credentials_rejected(monkeypatch):
    monkeypatch.setenv("DCG_LOCAL_USER","test-admin")
    monkeypatch.setenv("DCG_LOCAL_PASSWORD","not-a-real-password")
    monkeypatch.setenv("DCG_LOCAL_ROLE","administrator")
    monkeypatch.setenv("DCG_LOCAL_ZONES","ZONE-B")
    assert client.get("/api/v1/incidents",auth=("test-admin","wrong")).status_code == 401

def test_authenticated_viewer_cannot_run_scenario(monkeypatch):
    monkeypatch.setenv("DCG_LOCAL_USER","test-viewer")
    monkeypatch.setenv("DCG_LOCAL_PASSWORD","not-a-real-password")
    monkeypatch.setenv("DCG_LOCAL_ROLE","viewer")
    monkeypatch.setenv("DCG_LOCAL_ZONES","ZONE-B")
    assert client.get("/api/v1/auth/me",auth=("test-viewer","not-a-real-password")).status_code == 200
    assert client.post("/api/v1/scenarios/ppe_face/run",auth=("test-viewer","not-a-real-password")).status_code == 403

def test_unknown_role_denied(monkeypatch):
    monkeypatch.setenv("DCG_LOCAL_USER","test-user")
    monkeypatch.setenv("DCG_LOCAL_PASSWORD","not-a-real-password")
    monkeypatch.setenv("DCG_LOCAL_ROLE","superuser")
    monkeypatch.setenv("DCG_LOCAL_ZONES","ZONE-B")
    assert client.get("/api/v1/incidents",auth=("test-user","not-a-real-password")).status_code == 403
