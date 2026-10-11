"""HTTP RBAC contracts for SSH, maintenance, and environmental feeds.

Synthetic database rows are returned by stubs. No frozen model, Neo4j, or
private Evidence files are read.
"""
import pytest
from fastapi.testclient import TestClient
from presentation.backend.app.main import app
from presentation.backend.app import ssh_publication as ssh
from presentation.backend.app import maintenance_workflow as maint
from presentation.backend.app import environment_workflow as env

client=TestClient(app)
PASSWORD="test-only-password"
AUTH=("feed-test",PASSWORD)

class StubConnection:
    def __init__(self,rows):self.rows=rows
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def execute(self,*args,**kwargs):return self
    def fetchall(self):return self.rows

@pytest.fixture
def setup(monkeypatch):
    monkeypatch.setenv("DCG_LOCAL_USER","feed-test")
    monkeypatch.setenv("DCG_LOCAL_PASSWORD",PASSWORD)
    monkeypatch.setenv("DCG_LOCAL_ROLE","administrator")
    monkeypatch.setenv("DCG_LOCAL_ZONES","ZONE-A")
    monkeypatch.setattr(ssh,"connect",lambda:StubConnection([
        ("SSH-A","2026-10-10T01:00:00Z","ZONE-A","SRV-A","{}"),
        ("SSH-B","2026-10-10T01:00:00Z","ZONE-B","SRV-B","{}")]))
    monkeypatch.setattr(ssh,"load_decision",lambda eid:None)
    monkeypatch.setattr(maint,"db",lambda:StubConnection([
        ("MAINT-A","2026-10-10T01:00:00Z","ZONE-A","SRV-A","{}","{}","{}"),
        ("MAINT-B","2026-10-10T01:00:00Z","ZONE-B","SRV-B","{}","{}","{}")]))
    class EnvironmentDB:
        def __enter__(self):return self
        def __exit__(self,*args):return False
        def execute(self,sql,*args):
            if "environmental_batches" in sql:
                return StubConnection([
                    ("ENV-A","2026-10-10T01:00:00Z","ZONE-A","SEN-A","{}","{}","{}","[]"),
                    ("ENV-B","2026-10-10T01:00:00Z","ZONE-B","SEN-B","{}","{}","{}","[]")])
            return StubConnection([])
    monkeypatch.setattr(env,"db",lambda:EnvironmentDB())

PATHS=("/api/v1/ssh/published","/api/v1/maintenance/events","/api/v1/environment/events")

@pytest.mark.parametrize("path",PATHS)
def test_missing_authentication_rejected(setup,path):
    assert client.get(path).status_code==401

@pytest.mark.parametrize("path",PATHS)
def test_zone_filtered_feed(setup,path):
    response=client.get(path,auth=AUTH)
    assert response.status_code==200
    rows=response.json()
    assert len(rows)==1
    assert rows[0]["zone_id"]=="ZONE-A"

def test_viewer_cannot_read_ssh_feed(setup,monkeypatch):
    monkeypatch.setenv("DCG_LOCAL_ROLE","viewer")
    assert client.get(PATHS[0],auth=AUTH).status_code==403

@pytest.mark.parametrize("path",PATHS[1:])
def test_viewer_read_is_zone_filtered(setup,monkeypatch,path):
    monkeypatch.setenv("DCG_LOCAL_ROLE","viewer")
    response=client.get(path,auth=AUTH)
    assert response.status_code==200
    assert [x["zone_id"] for x in response.json()]==["ZONE-A"]
