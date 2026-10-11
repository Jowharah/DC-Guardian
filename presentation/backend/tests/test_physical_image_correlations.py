from presentation.backend.app.physical_image_correlations import eligible_pair

def metadata(camera="CAM-B-01",time="2026-10-09T08:05:00Z",status="PROJECTED"):
    return {"capture_metadata":{"camera_id":camera,"zone_id":"ZONE-B",
      "captured_at":time,"provenance":"OPERATOR_DECLARED_UNVERIFIED"},
      "graph_projection":{"graph_status":status}}

def test_same_image_context_eligible():
    assert eligible_pair({}, {},metadata(),metadata())

def test_different_camera_rejected():
    assert not eligible_pair({}, {},metadata(),metadata(camera="CAM-B-02"))

def test_different_capture_time_rejected():
    assert not eligible_pair({}, {},metadata(),metadata(time="2026-10-09T09:05:00Z"))

def test_missing_graph_projection_rejected():
    assert not eligible_pair({}, {},metadata(),metadata(status="NOT_RUN"))

def test_missing_metadata_rejected():
    assert not eligible_pair({}, {},None,metadata())
