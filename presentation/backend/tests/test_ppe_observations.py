"""Local PPE observation persistence and zone authorization tests."""
from PIL import Image
from fastapi.testclient import TestClient
from presentation.backend.app.main import app
from presentation.backend.app.authentication import current_principal
from presentation.backend.app.authorization import Principal
from presentation.backend.app.ppe_observations import save_observation, get_observation, list_observations

def test_retained_image_is_separate_from_incident_and_zone_scoped(monkeypatch,tmp_path):
    monkeypatch.setenv("DCG_PRESENTATION_DB",str(tmp_path/"incidents.sqlite3"))
    record=save_observation(Image.new("RGB",(20,10)),{
        "overall_status":"COMPLIANT","person_count":1,"detections":[]
    },"ZONE-B","tester")
    assert record["pipeline_status"]=="PPE_ONLY_NOT_INTEGRATED"
    assert len(list_observations(frozenset({"ZONE-A"})))==0
    assert len(list_observations(frozenset({"ZONE-B"})))==1
    assert get_observation(record["observation_id"])["image_size"]=={"width":20,"height":10}
    client=TestClient(app)
    url=f'/api/v1/ppe/observations/{record["observation_id"]}/image'
    try:
        app.dependency_overrides[current_principal]=lambda:Principal("viewer",frozenset({"viewer"}),frozenset({"ZONE-B"}))
        assert client.get(url).status_code==403
        app.dependency_overrides[current_principal]=lambda:Principal("safety",frozenset({"safety_operator"}),frozenset({"ZONE-A"}))
        assert client.get(url).status_code==403
        app.dependency_overrides[current_principal]=lambda:Principal("safety",frozenset({"safety_operator"}),frozenset({"ZONE-B"}))
        response=client.get(url)
        assert response.status_code==200
        assert response.headers["content-type"]=="image/png"
        assert response.headers["cache-control"]=="no-store"
    finally:
        app.dependency_overrides.pop(current_principal,None)
