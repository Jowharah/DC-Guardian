"""Graph integrity checks against mocked read-only Neo4j records."""
from unittest.mock import patch
from presentation.backend.app.graph_integrity import check_graph_integrity

class Result:
    def __init__(self, rows): self.rows=rows
    def data(self): return self.rows

class Session:
    def __init__(self, rows): self.rows=rows
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def run(self, query, **kwargs): return Result(self.rows)

class Driver:
    def __init__(self, rows): self.rows=rows
    def session(self, **kwargs): return Session(self.rows)
    def close(self): pass

def row(event_id, domain, relation, labels):
    return {"event_id":event_id, "domain":domain, "relationship":relation, "neighbor_labels":labels}

def test_complete_ssh_graph():
    rows=[row("EVT-SSH","CYBERSECURITY","TARGETS",["Server"]),
          row("EVT-SSH","CYBERSECURITY","ORIGINATED_FROM",["SourceIP"]),
          row("EVT-ENV","ENVIRONMENTAL","TARGETS",["Sensor"])]
    with patch("presentation.backend.app.graph_integrity.create_driver",return_value=Driver(rows)):
        result=check_graph_integrity("DCG-TEST",["EVT-SSH","EVT-ENV"])
    assert result["status"]=="PASS"
    assert result["missing_ssh_source_relationships"]==[]

def test_missing_source_ip_link():
    with patch("presentation.backend.app.graph_integrity.create_driver",
               return_value=Driver([row("EVT-SSH","CYBERSECURITY","TARGETS",["Server"])])):
        result=check_graph_integrity("DCG-TEST",["EVT-SSH"])
    assert result["status"]=="INCOMPLETE"
    assert result["missing_ssh_source_relationships"]==["EVT-SSH"]

def test_missing_event():
    with patch("presentation.backend.app.graph_integrity.create_driver",return_value=Driver([])):
        result=check_graph_integrity("DCG-TEST",["EVT-SSH"])
    assert result["status"]=="INCOMPLETE"
    assert result["missing_event_ids"]==["EVT-SSH"]
