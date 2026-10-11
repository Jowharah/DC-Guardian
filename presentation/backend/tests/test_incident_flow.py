"""Validate incident snapshots originate from pipeline result projections."""
from fastapi.testclient import TestClient
from presentation.backend.app.main import app
from presentation.backend.app.schemas import IncidentView
from presentation.backend.app import main
from presentation.backend.app.incident_store import get_incident

client = TestClient(app)

def test_pipeline_snapshot_lifecycle(monkeypatch, tmp_path):
    monkeypatch.setenv('DCG_PRESENTATION_DB', str(tmp_path / 'incidents.sqlite3'))
    assert client.get("/api/v1/incidents").json() == []
    assert client.get("/api/v1/incidents/DCG-TEST-FLOW-01").status_code == 404
    def fake_execute(name):
        assert name == "ppe_face"
        return IncidentView(
            scenario_id="DCG-TEST-FLOW-01",
            scenario_name=name,
            domains=["PHYSICAL_SECURITY","SAFETY"],
            shared_scope="ZONE",shared_entity="ZONE-B",
            evidence_event_ids=["EVT-PPE","EVT-FACE"],
            decision={
                "incident_status":"REVIEW_REQUIRED","severity":"MEDIUM",
                "response_mode":"HUMAN_REVIEW","escalation_required":False,
                "autonomous_action_allowed":False,
                "decision_rules_triggered":["UNAUTHORIZED_PHYSICAL_ACCESS_EVIDENCE"],
                "rationale":["Deterministic contract test"],
                "protected_boundaries":{
                    "identity_link_established":False,"confirmed_compromise":False,
                    "causal_relationship_established":False,"root_cause_established":False,
                },
                "policy_version":"DCG-DECISION-v1",
            }
        )
    monkeypatch.setattr(main,"execute_scenario",fake_execute)
    response=client.post("/api/v1/scenarios/ppe_face/run")
    assert response.status_code==200
    assert response.json()["data_origin"]=="CONTROLLED_SYNTHETIC_SCENARIO"
    listed=client.get("/api/v1/incidents").json()
    assert len(listed)==1
    assert listed[0]["decision"]["autonomous_action_allowed"] is False
    assert len(listed[0]["evidence_event_ids"])==2
    detail=client.get("/api/v1/incidents/DCG-TEST-FLOW-01")
    assert detail.status_code==200
    assert detail.json()==listed[0]
