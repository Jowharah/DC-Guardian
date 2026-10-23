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


def _capture_queries(monkeypatch, single_result):
    from presentation.backend.app import image_evidence_mapping as mapping
    queries = []

    class Result:
        def single(self): return single_result

    class Session:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def run(self, query, **params):
            queries.append((query, params))
            return Result()

    class Driver:
        def session(self, **kwargs): return Session()
        def close(self): pass

    monkeypatch.setattr(mapping, "create_driver", lambda: Driver())
    return mapping, queries


def test_recognized_face_identifies_an_existing_person_only(monkeypatch):
    """A recognized face links the Event to the existing Person (as face ingestion does); no Person is created."""
    mapping, queries = _capture_queries(monkeypatch, {"id": "IMG-EVT-FACE-1"})
    metadata = {"camera_id": "CAM-A-01", "captured_at": "2026-10-10T07:00:00+00:00"}
    mapping.project_observation("face", "FACE-1", {"recognition_status": "RECOGNIZED", "person_id": "P005"}, metadata)
    link = [q for q in queries if "IDENTIFIES" in q[0]]
    assert len(link) == 1
    assert "MATCH (person:Person {person_id:$person_id})" in link[0][0] and "MERGE (person" not in link[0][0]
    assert link[0][1] == {"event_id": "IMG-EVT-FACE-1", "person_id": "P005"}


def test_unknown_face_and_ppe_get_no_identity_link(monkeypatch):
    mapping, queries = _capture_queries(monkeypatch, {"id": "x"})
    metadata = {"camera_id": "CAM-A-01", "captured_at": "2026-10-10T07:00:00+00:00"}
    mapping.project_observation("face", "FACE-2", {"recognition_status": "UNKNOWN"}, metadata)
    mapping.project_observation("ppe", "PPE-1", {"overall_status": "NON_COMPLIANT"}, metadata)
    assert not any("IDENTIFIES" in q for q, _ in queries)
