from presentation.backend.app.face_ssh_specialists import signature

def test_signature_stable_for_same_context():
    item={"face_observation_id":"F1","ssh_event_id":"S1","zone_id":"ZONE-A",
          "face_capture_time":"2026-10-09T13:39:00Z",
          "ssh_context_time":"2026-10-09T13:35:00Z",
          "ssh_time_provenance":"OPERATOR_DECLARED_UNVERIFIED_TEST_TIME"}
    assert signature(item)==signature(dict(reversed(list(item.items()))))

def test_changed_context_invalidates_saved_result():
    item={"face_observation_id":"F1","ssh_event_id":"S1","zone_id":"ZONE-A",
          "face_capture_time":"2026-10-09T13:39:00Z",
          "ssh_context_time":"2026-10-09T13:35:00Z",
          "ssh_time_provenance":"OPERATOR_DECLARED_UNVERIFIED_TEST_TIME"}
    assert signature(item)!=signature({**item,"ssh_context_time":"2026-10-09T13:37:00Z"})
