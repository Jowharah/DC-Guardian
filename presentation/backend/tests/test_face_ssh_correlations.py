from presentation.backend.app.face_ssh_correlations import eligible

FACE={"zone_id":"ZONE-B","captured_at":"2026-10-09T08:05:00Z",
      "provenance":"OPERATOR_DECLARED_UNVERIFIED"}
SSH={"zone_id":"ZONE-B","original_timestamp":"2026-10-09T08:08:00Z",
     "timestamp_uncertain":False}

def test_same_zone_close_time_candidate():
    assert eligible(FACE,SSH)==180

def test_different_zone_rejected():
    assert eligible(FACE,{**SSH,"zone_id":"ZONE-A"}) is None

def test_old_placeholder_year_rejected():
    assert eligible(FACE,{**SSH,"original_timestamp":"2000-10-09T08:05:00Z"}) is None

def test_naive_ssh_timestamp_rejected():
    assert eligible(FACE,{**SSH,"original_timestamp":"2026-10-09T08:05:00"}) is None

def test_outside_window_rejected():
    assert eligible(FACE,{**SSH,"original_timestamp":"2026-10-09T09:05:00Z"}) is None

def test_uncertain_timestamp_rejected():
    assert eligible(FACE,{**SSH,"timestamp_uncertain":True}) is None

def test_unverified_declared_context_not_identity_link():
    assert eligible(FACE,SSH)==180
