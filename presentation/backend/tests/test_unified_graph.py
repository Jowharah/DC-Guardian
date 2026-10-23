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


class FakeNode(dict):
    def __init__(self, element_id, labels, **props):
        super().__init__(props)
        self.element_id = element_id
        self.labels = frozenset(labels)


class FakeRel:
    def __init__(self, element_id, start, end, type_):
        self.element_id, self.start_node, self.end_node, self.type = element_id, start, end, type_


class FakePath:
    def __init__(self, nodes, relationships):
        self.nodes, self.relationships = nodes, relationships


def test_infrastructure_is_linked_to_its_zone_through_existing_topology_only(monkeypatch):
    """Usability study: the group graph showed servers without their zone. Follow only the
    topology links (LOCATED_IN, HOSTED_BY, MONITORS) from touched infrastructure to the group's zone."""
    monkeypatch.setattr(graph, "unified_correlations", lambda p: [group()])
    monkeypatch.setattr(graph, "graph_ids", lambda g, p: ["SSH-EVT-1-MAPPED"])
    event = FakeNode("e1", {"Event"}, event_id="SSH-EVT-1-MAPPED")
    server = FakeNode("s1", {"Server"}, server_id="SRV-B1-01")
    rack = FakeNode("r1", {"Rack"}, rack_id="RACK-B1")
    zone = FakeNode("z1", {"Zone"}, zone_id="ZONE-B")
    seen = []

    class Session:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def run(self, query, **params):
            seen.append((query, params))
            if "elementId(n) IN $infra" in query:
                assert params == {"infra": ["s1"], "zone": "ZONE-B"}
                assert "[:LOCATED_IN|HOSTED_BY|MONITORS*1..3]" in query and "LIMIT" in query
                return [{"path": FakePath([server, rack, zone],
                                          [FakeRel("x1", server, rack, "LOCATED_IN"), FakeRel("x2", rack, zone, "LOCATED_IN")])}]
            return [{"e": event, "p": FakePath([event, server], [FakeRel("t1", event, server, "TARGETS")])}]

    class Driver:
        def session(self, **kwargs): return Session()
        def close(self): pass

    monkeypatch.setattr(graph, "create_driver", lambda: Driver())
    result = graph.unified_graph("DCG-UNIFIED-TEST", ADMIN)
    assert {n["type"] for n in result["nodes"]} == {"Event", "Server", "Rack", "Zone"}
    assert sorted(e["type"] for e in result["edges"]) == ["LOCATED_IN", "LOCATED_IN", "TARGETS"]
    assert any("elementId(n) IN $infra" in q for q, _ in seen)
