from fastapi import HTTPException
import pytest
from presentation.backend.app import standalone_graph as graph
from presentation.backend.app.authorization import Principal

OPERATOR=Principal("operator",frozenset({"administrator"}),frozenset({"ZONE-B"}))

def test_maintenance_graph_id_resolved(monkeypatch):
    monkeypatch.setattr(graph,"maintenance_events",lambda p:[{
        "event_id":"MAINT-EVT-1","zone_id":"ZONE-B",
        "workflow":{"graph_event_id":"MAINT-EVT-1-MAPPED"}}])
    assert graph.resolve("maintenance","MAINT-EVT-1",OPERATOR)==(
        "ZONE-B",["MAINT-EVT-1-MAPPED"])

def test_environment_batch_resolves_only_actual_events(monkeypatch):
    monkeypatch.setattr(graph,"environmental_events",lambda p:[{
        "event_id":"ENV-BATCH-1","zone_id":"ZONE-B",
        "evidence_event_ids":["ENV-EVT-1","ENV-EVT-2"]}])
    assert graph.resolve("environment","ENV-BATCH-1",OPERATOR)==(
        "ZONE-B",["ENV-EVT-1-MAPPED","ENV-EVT-2-MAPPED"])

def test_unknown_event_is_not_exposed(monkeypatch):
    monkeypatch.setattr(graph,"maintenance_events",lambda p:[])
    with pytest.raises(HTTPException) as err:
        graph.resolve("maintenance","MISSING",OPERATOR)
    assert err.value.status_code==404

def test_missing_mapped_ids_fail_closed():
    with pytest.raises(HTTPException) as err:
        graph.read_graph([],OPERATOR,"ZONE-B","MISSING")
    assert err.value.status_code==409
