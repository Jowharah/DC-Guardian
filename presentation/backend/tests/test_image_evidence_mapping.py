from datetime import datetime,timezone,timedelta
import pytest
from presentation.backend.app.image_evidence_mapping import validate_metadata

def test_declared_camera_zone_and_utc():
    result=validate_metadata({"camera_id":"CAM-B-01",
        "captured_at":"2026-10-09T08:05:00Z"},"ZONE-B")
    assert result["camera_id"]=="CAM-B-01"
    assert result["provenance"]=="OPERATOR_DECLARED_UNVERIFIED"
    assert result["captured_at"].endswith("+00:00")

def test_wrong_camera_zone_rejected():
    with pytest.raises(ValueError):
        validate_metadata({"camera_id":"CAM-B-01",
            "captured_at":"2026-10-09T08:05:00Z"},"ZONE-A")

def test_naive_time_rejected():
    with pytest.raises(ValueError,match="timezone"):
        validate_metadata({"camera_id":"CAM-B-01",
            "captured_at":"2026-10-09T08:05:00"},"ZONE-B")

def test_future_time_rejected():
    future=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()
    with pytest.raises(ValueError,match="future"):
        validate_metadata({"camera_id":"CAM-B-01","captured_at":future},"ZONE-B")
