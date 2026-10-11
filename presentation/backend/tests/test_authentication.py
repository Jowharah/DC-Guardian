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

def test_env_file_fallback(monkeypatch, tmp_path):
    from presentation.backend.app import authentication
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DCG_LOCAL_USER=file-user\n"
        "DCG_LOCAL_PASSWORD=file-password\n"
        "DCG_LOCAL_ROLE=viewer\n"
        "DCG_LOCAL_ZONES=ZONE-B\n", encoding="utf-8"
    )
    monkeypatch.setattr(authentication, "PROJECT_ENV", env_file)
    for name in ("DCG_LOCAL_USER", "DCG_LOCAL_PASSWORD", "DCG_LOCAL_ROLE", "DCG_LOCAL_ZONES"):
        monkeypatch.delenv(name, raising=False)
    response = client.get("/api/v1/auth/me", auth=("file-user", "file-password"))
    assert response.status_code == 200
    assert response.json()["roles"] == ["viewer"]

def test_process_env_overrides_file(monkeypatch, tmp_path):
    from presentation.backend.app import authentication
    env_file = tmp_path / ".env"
    env_file.write_text("DCG_LOCAL_USER=file-user\n", encoding="utf-8")
    monkeypatch.setattr(authentication, "PROJECT_ENV", env_file)
    monkeypatch.setenv("DCG_LOCAL_USER", "process-user")
    assert authentication.local_setting("DCG_LOCAL_USER") == "process-user"
