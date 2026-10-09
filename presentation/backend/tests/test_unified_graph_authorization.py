"""Regression coverage for independent Person and Zone graph context."""
from presentation.backend.app import unified_graph as graph
from presentation.backend.app.authorization import Principal

ADMIN=Principal("operator",frozenset({"administrator"}),frozenset({"ZONE-A"}))

class Node:
    def __init__(self,label,**properties):
        self.labels={label}
        self.properties=properties
        self.element_id=label+":"+next(iter(properties.values()))
    def __getitem__(self,key):return self.properties[key]
    def __contains__(self,key):return key in self.properties

class Rel:
    def __init__(self,person,zone):
        self.start_node=person
        self.end_node=zone
        self.element_id="authorized-edge"
        self.type="AUTHORIZED_FOR"

class Row(dict):
    pass

def run_case(monkeypatch,authorized):
    face=Node("Event",event_id="IMG-EVT-FACE-IMG-1")
    person=Node("Person",person_id="P005")
    zone=Node("Zone",zone_id="ZONE-A")
    monkeypatch.setattr(graph,"unified_correlations",lambda p:[{
        "id":"G1","zone_id":"ZONE-A",
        "evidence":[{"kind":"face","observation_id":"FACE-IMG-1"}]}])
    monkeypatch.setattr(graph,"graph_ids",lambda g,p:["IMG-EVT-FACE-IMG-1"])
    from presentation.backend.app import face_observations
    monkeypatch.setattr(face_observations,"get",lambda oid:{
        "assessment":{"recognition_status":"RECOGNIZED","person_id":"P005"}})
    class Session:
        def __enter__(self):return self
        def __exit__(self,*args):return False
        def run(self,query,**params):
            if "OPTIONAL MATCH p=" in query:return [Row(e=face,p=None)]
            if "MATCH (p:Person)" in query:return [Row(p=person)]
            if "MATCH (z:Zone" in query:return [Row(z=zone)]
            if "AUTHORIZED_FOR" in query:
                return [Row(p=person,z=zone,r=Rel(person,zone))] if authorized else []
            raise AssertionError(query)
    class Driver:
        def session(self,**kwargs):return Session()
        def close(self):pass
    monkeypatch.setattr(graph,"create_driver",lambda:Driver())
    return graph.unified_graph("G1",ADMIN)

def test_unauthorized_person_is_visible_without_authorization_edge(monkeypatch):
    result=run_case(monkeypatch,False)
    assert {x["type"] for x in result["nodes"]}=={"Event","Person","Zone"}
    assert result["edges"]==[]

def test_existing_authorization_edge_is_returned_without_synthesis(monkeypatch):
    result=run_case(monkeypatch,True)
    assert len(result["edges"])==1
    assert result["edges"][0]["type"]=="AUTHORIZED_FOR"
    assert len(result["nodes"])==3
