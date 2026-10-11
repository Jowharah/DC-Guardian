"""HTTP-level PPE/Face Evidence access security contracts.

Uses stubbed observations and image bytes; does not load private biometric
enrollment, run frozen models, or read real image artifacts.
"""
from fastapi.testclient import TestClient
import pytest
from presentation.backend.app.main import app
from presentation.backend.app import ppe_image_validation as ppe
from presentation.backend.app import face_image_validation as face

client=TestClient(app)
PASSWORD="test-password-only"
PPE_ID="PPE-TEST-01"
FACE_ID="FACE-TEST-01"

@pytest.fixture
def setup(monkeypatch):
    monkeypatch.setenv("DCG_LOCAL_USER","image-test")
    monkeypatch.setenv("DCG_LOCAL_PASSWORD",PASSWORD)
    monkeypatch.setenv("DCG_LOCAL_ROLE","administrator")
    monkeypatch.setenv("DCG_LOCAL_ZONES","ZONE-A")
    monkeypatch.setattr(ppe,"get_observation",lambda oid:{"observation_id":oid,"zone_id":"ZONE-A"} if oid==PPE_ID else None)
    monkeypatch.setattr(ppe,"image_bytes",lambda oid,subject:b"test-image")
    monkeypatch.setattr(face.face_observations,"get",lambda oid:{"observation_id":oid,"zone_id":"ZONE-A","assessment":{"recognition_status":"UNKNOWN"}} if oid==FACE_ID else None)
    monkeypatch.setattr(face.face_observations,"image_bytes",lambda oid,subject:b"test-image")

def get(path):
    return client.get(path,auth=("image-test",PASSWORD))

@pytest.mark.parametrize("path",[
    f"/api/v1/ppe/observations/{PPE_ID}",
    f"/api/v1/ppe/observations/{PPE_ID}/image",
    f"/api/v1/face/observations/{FACE_ID}",
    f"/api/v1/face/observations/{FACE_ID}/image",
    f"/api/v1/face/observations/{FACE_ID}/authorization"])
def test_missing_authentication_denied(setup,path):
    assert client.get(path).status_code==401

@pytest.mark.parametrize("path",[
    f"/api/v1/ppe/observations/{PPE_ID}",
    f"/api/v1/ppe/observations/{PPE_ID}/image",
    f"/api/v1/face/observations/{FACE_ID}",
    f"/api/v1/face/observations/{FACE_ID}/image"])
def test_wrong_zone_denied(setup,monkeypatch,path):
    monkeypatch.setenv("DCG_LOCAL_ZONES","ZONE-B")
    assert get(path).status_code==403

@pytest.mark.parametrize("path",[
    f"/api/v1/ppe/observations/{PPE_ID}",
    f"/api/v1/ppe/observations/{PPE_ID}/image",
    f"/api/v1/face/observations/{FACE_ID}",
    f"/api/v1/face/observations/{FACE_ID}/image"])
def test_viewer_denied(setup,monkeypatch,path):
    monkeypatch.setenv("DCG_LOCAL_ROLE","viewer")
    assert get(path).status_code==403

@pytest.mark.parametrize("path",[
    f"/api/v1/ppe/observations/{PPE_ID}/image",
    f"/api/v1/face/observations/{FACE_ID}/image"])
def test_authorized_image_response_headers(setup,path):
    response=get(path)
    assert response.status_code==200
    assert response.content==b"test-image"
    assert response.headers["content-type"]=="image/png"
    assert response.headers["cache-control"]=="no-store"
    assert response.headers["x-content-type-options"]=="nosniff"

@pytest.mark.parametrize("path",[
    "/api/v1/ppe/observations/UNKNOWN/image",
    "/api/v1/face/observations/UNKNOWN/image"])
def test_missing_observation_not_exposed(setup,path):
    assert get(path).status_code==404
