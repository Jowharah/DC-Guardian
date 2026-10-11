"""Authorization must fail unknown and never infer access from recognition alone."""
from presentation.backend.app import face_zone_authorization as auth

class FakeRecord(dict):
    pass

class FakeSession:
    def __init__(self, record): self.record = record
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def run(self, query, **kwargs):
        assert "AUTHORIZED_FOR" in query
        return self
    def single(self): return self.record

class FakeDriver:
    def __init__(self, record): self.record = record
    def session(self, **kwargs):
        assert kwargs["default_access_mode"] == "READ"
        return FakeSession(self.record)
    def close(self): pass

def test_missing_person_is_unknown(monkeypatch):
    monkeypatch.setattr(auth, "create_driver", lambda: FakeDriver(FakeRecord(person_exists=False,zone_exists=True,authorized=False)))
    result = auth.assess("P005", "ZONE-B")
    assert result["status"] == "UNKNOWN"
    assert result["reason"] == "PERSON_NOT_IN_TOPOLOGY"

def test_known_person_without_link_is_unauthorized(monkeypatch):
    monkeypatch.setattr(auth, "create_driver", lambda: FakeDriver(FakeRecord(person_exists=True,zone_exists=True,authorized=False)))
    assert auth.assess("P003", "ZONE-B")["status"] == "UNAUTHORIZED"

def test_authorized_relationship(monkeypatch):
    monkeypatch.setattr(auth, "create_driver", lambda: FakeDriver(FakeRecord(person_exists=True,zone_exists=True,authorized=True)))
    assert auth.assess("P001", "ZONE-B")["status"] == "AUTHORIZED"

def test_graph_failure_is_unknown(monkeypatch):
    def fail(): raise RuntimeError("connection error")
    monkeypatch.setattr(auth, "create_driver", fail)
    assert auth.assess("P001", "ZONE-B")["status"] == "UNKNOWN"
