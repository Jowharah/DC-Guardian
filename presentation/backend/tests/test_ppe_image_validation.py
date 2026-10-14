"""Image validation boundary tests; do not load CUDA or model weights."""
from io import BytesIO
import pytest
from PIL import Image
from presentation.backend.app.ppe_image_validation import validate_image

def image_bytes(format="PNG"):
    output=BytesIO()
    Image.new("RGB",(16,16)).save(output,format=format)
    return output.getvalue()

def test_valid_png():
    image=validate_image(image_bytes())
    assert image.size==(16,16)

def test_valid_jpeg():
    image=validate_image(image_bytes("JPEG"))
    assert image.mode=="RGB"

def test_invalid_bytes_rejected():
    with pytest.raises(ValueError):
        validate_image(b"not an image")

def test_oversized_bytes_rejected():
    with pytest.raises(ValueError):
        validate_image(b"x"*(8*1024*1024+1))


# Runtime detector setting (DCG_PPE_DETECTOR). The worker is stubbed: no CUDA, no weights.
from pathlib import Path
from types import SimpleNamespace
from fastapi.testclient import TestClient
from presentation.backend.app import ppe_image_validation as ppe
from presentation.backend.app.main import app

PASSWORD = "test-password-only"


def test_detector_defaults_to_v2m_and_accepts_v1(monkeypatch):
    monkeypatch.setattr(ppe, "local_setting", lambda name: "")
    assert ppe.ppe_detector() == "v2m" == ppe.DEFAULT_PPE_DETECTOR
    monkeypatch.setattr(ppe, "local_setting", lambda name: " v1 ")
    assert ppe.ppe_detector() == "v1"


@pytest.fixture
def stubbed_worker(monkeypatch):
    for name, value in (("DCG_LOCAL_USER", "ppe-test"), ("DCG_LOCAL_PASSWORD", PASSWORD),
                        ("DCG_LOCAL_ROLE", "administrator"), ("DCG_LOCAL_ZONES", "ZONE-A")):
        monkeypatch.setenv(name, value)
    calls = []

    def run(command, **kwargs):
        calls.append(kwargs["env"])
        return SimpleNamespace(returncode=0, stderr="",
                               stdout='DCG_PPE_RESULT={"overall_status": "NO_PERSON", "detections": []}')
    original_is_file = Path.is_file
    monkeypatch.setattr(Path, "is_file", lambda self: True if self.name == "python.exe" else original_is_file(self))
    monkeypatch.setattr(ppe.subprocess, "run", run)
    return calls


def post_image():
    return TestClient(app).post("/api/v1/ppe/validate-image", auth=("ppe-test", PASSWORD),
                                files={"image": ("input.png", image_bytes(), "image/png")})


@pytest.mark.parametrize("setting,expected", [("v1", "v1"), ("v2m", "v2m")])
def test_endpoint_passes_the_detector_to_the_worker(stubbed_worker, monkeypatch, setting, expected):
    monkeypatch.setenv("DCG_PPE_DETECTOR", setting)
    response = post_image()
    assert response.status_code == 200, response.text
    assert stubbed_worker[-1]["DCG_PPE_DETECTOR"] == expected


def test_endpoint_rejects_an_unknown_detector_without_running_the_worker(stubbed_worker, monkeypatch):
    monkeypatch.setenv("DCG_PPE_DETECTOR", "v9")
    response = post_image()
    assert response.status_code == 503 and response.json()["detail"] == "PPE_DETECTOR_SETTING_INVALID"
    assert stubbed_worker == []
