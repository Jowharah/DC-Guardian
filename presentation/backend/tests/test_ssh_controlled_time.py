from fastapi import HTTPException
import pytest
from presentation.backend.app.face_ssh_correlations import eligible
from presentation.backend.app.ssh_temporal_context import parse_aware

FACE={"zone_id":"ZONE-B","captured_at":"2026-10-09T08:05:00Z",
      "provenance":"OPERATOR_DECLARED_UNVERIFIED"}
SSH={"zone_id":"ZONE-B","original_timestamp":"2000-12-10T07:10:00",
     "timestamp_uncertain":True}

def test_historical_ssh_not_matched_without_declaration():
    assert eligible(FACE,SSH) is None

def test_explicit_test_context_matches_only_as_candidate():
    ssh={**SSH,"controlled_time":{"observed_at":"2026-10-09T08:08:00Z",
                                "provenance":"OPERATOR_DECLARED_UNVERIFIED_TEST_TIME"}}
    assert eligible(FACE,ssh)==180

def test_wrong_provenance_does_not_override_historical_time():
    ssh={**SSH,"controlled_time":{"observed_at":"2026-10-09T08:08:00Z",
                                "provenance":"UNVERIFIED_OTHER"}}
    assert eligible(FACE,ssh) is None

def test_naive_test_timestamp_rejected():
    with pytest.raises(HTTPException) as exc:
        parse_aware("2026-10-09T08:08:00")
    assert exc.value.status_code==422

def test_cross_zone_still_rejected():
    ssh={**SSH,"zone_id":"ZONE-A","controlled_time":{
        "observed_at":"2026-10-09T08:08:00Z",
        "provenance":"OPERATOR_DECLARED_UNVERIFIED_TEST_TIME"}}
    assert eligible(FACE,ssh) is None
