from fastapi import HTTPException
import pytest
from presentation.backend.app import physical_image_graph as graph
from presentation.backend.app.authorization import Principal

def test_missing_candidate_returns_404(monkeypatch):
    principal=Principal("operator",frozenset({"administrator"}),frozenset({"ZONE-B"}))
    monkeypatch.setattr(graph,"image_correlations",lambda p:[])
    with pytest.raises(HTTPException) as error:
        graph.physical_graph("MISSING",principal)
    assert error.value.status_code==404

def test_graph_only_uses_selected_candidate(monkeypatch):
    principal=Principal("operator",frozenset({"administrator"}),frozenset({"ZONE-B"}))
    monkeypatch.setattr(graph,"image_correlations",lambda p:[{
      "id":"DCG-PHYSICAL-TEST","zone_id":"ZONE-B",
      "ppe_observation_id":"PPE-IMG-1","face_observation_id":"FACE-IMG-1"}])
    class Session:
        def __enter__(self):return self
        def __exit__(self,*args):return False
        def run(self,query,**params):
            assert params["ids"]==["IMG-EVT-PPE-IMG-1","IMG-EVT-FACE-IMG-1"]
            assert "OBSERVED_BY" in query
            return []
    class Driver:
        def session(self,**kwargs):return Session()
        def close(self):pass
    monkeypatch.setattr(graph,"create_driver",lambda:Driver())
    with pytest.raises(HTTPException) as error:
        graph.physical_graph("DCG-PHYSICAL-TEST",principal)
    assert error.value.status_code==409
