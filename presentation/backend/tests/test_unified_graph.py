import pytest
from fastapi import HTTPException
from presentation.backend.app import unified_graph as graph
from presentation.backend.app.authorization import Principal

ADMIN=Principal("operator",frozenset({"administrator"}),frozenset({"ZONE-B"}))

def group():
    return {"id":"DCG-UNIFIED-TEST","zone_id":"ZONE-B",
      "evidence":[{"kind":"ppe","observation_id":"PPE-IMG-1"},
                  {"kind":"face","observation_id":"FACE-IMG-1"},
                  {"kind":"ssh","observation_id":"SSH-EVT-1"}]}

def test_graph_id_mapping_for_image_and_ssh(monkeypatch):
    from presentation.backend.app import maintenance_workflow,environment_workflow
    monkeypatch.setattr(maintenance_workflow,"list_events",lambda p:[])
    monkeypatch.setattr(environment_workflow,"list_events",lambda p:[])
    assert graph.graph_ids(group(),ADMIN)==[
      "IMG-EVT-FACE-IMG-1","IMG-EVT-PPE-IMG-1","SSH-EVT-1-MAPPED"]

def test_missing_candidate_returns_404(monkeypatch):
    monkeypatch.setattr(graph,"unified_correlations",lambda p:[])
    with pytest.raises(HTTPException) as exc:
        graph.unified_graph("missing",ADMIN)
    assert exc.value.status_code==404

def test_missing_graph_events_fail_closed(monkeypatch):
    monkeypatch.setattr(graph,"unified_correlations",lambda p:[group()])
    monkeypatch.setattr(graph,"graph_ids",lambda g,p:["IMG-EVT-FACE-IMG-1","IMG-EVT-PPE-IMG-1"])
    class Session:
        def __enter__(self):return self
        def __exit__(self,*args):return False
        def run(self,query,**params):
            assert "NOT n:Event" in query
            assert params["ids"]==["IMG-EVT-FACE-IMG-1","IMG-EVT-PPE-IMG-1"]
            return []
    class Driver:
        def session(self,**kwargs):return Session()
        def close(self):pass
    monkeypatch.setattr(graph,"create_driver",lambda:Driver())
    with pytest.raises(HTTPException) as exc:
        graph.unified_graph("DCG-UNIFIED-TEST",ADMIN)
    assert exc.value.status_code==409

def test_out_of_zone_denied(monkeypatch):
    monkeypatch.setattr(graph,"unified_correlations",lambda p:[group()])
    other=Principal("operator",frozenset({"administrator"}),frozenset({"ZONE-A"}))
    with pytest.raises(HTTPException) as exc:
        graph.unified_graph("DCG-UNIFIED-TEST",other)
    assert exc.value.status_code==403
