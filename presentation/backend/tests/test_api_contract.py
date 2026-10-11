"""Presentation API contract tests without live Neo4j or model execution."""
from fastapi.testclient import TestClient
from presentation.backend.app.main import app
from presentation.backend.app.schemas import IncidentView
from presentation.backend.app import main

client = TestClient(app)

def test_health():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "mode": "CONTROLLED_PROTOTYPE"}

def test_scenario_registry():
    response = client.get("/api/v1/scenarios")
    assert response.status_code == 200
    names = {item["name"] for item in response.json()}
    assert names == {"ppe_face", "environmental_maintenance", "cyber_environmental_maintenance"}

def test_unknown_scenario():
    response = client.post("/api/v1/scenarios/not_registered/run")
    assert response.status_code == 404

def test_controlled_incident_contract(monkeypatch):
    def fake_execute(name):
        assert name == "ppe_face"
        return IncidentView(
            scenario_id="DCG-TEST-001",
            scenario_name="ppe_face",
            domains=["PHYSICAL_SECURITY", "SAFETY"],
            shared_scope="ZONE",
            shared_entity="ZONE-B",
            evidence_event_ids=["EVT-001"],
            decision={
                "incident_status": "REVIEW_REQUIRED",
                "severity": "MEDIUM",
                "response_mode": "HUMAN_REVIEW",
                "escalation_required": False,
                "autonomous_action_allowed": False,
                "decision_rules_triggered": ["UNAUTHORIZED_PHYSICAL_ACCESS_EVIDENCE"],
                "rationale": ["Controlled test"],
                "protected_boundaries": {
                    "identity_link_established": False,
                    "confirmed_compromise": False,
                    "causal_relationship_established": False,
                    "root_cause_established": False,
                },
                "policy_version": "DCG-DECISION-v1",
            },
        )
    monkeypatch.setattr(main, "execute_scenario", fake_execute)
    response = client.post("/api/v1/scenarios/ppe_face/run")
    assert response.status_code == 200
    payload = response.json()
    assert payload["data_origin"] == "CONTROLLED_SYNTHETIC_SCENARIO"
    assert payload["decision"]["autonomous_action_allowed"] is False
    assert payload["decision"]["severity"] == "MEDIUM"
    assert "evidence" not in payload
    assert "response" not in payload

def test_reject_autonomous_action():
    from pydantic import ValidationError
    from presentation.backend.app.schemas import DecisionView
    import pytest
    with pytest.raises(ValidationError):
        DecisionView(
            incident_status="REVIEW_REQUIRED",
            severity="HIGH",
            response_mode="HUMAN_REVIEW",
            escalation_required=True,
            autonomous_action_allowed=True,
            decision_rules_triggered=[],
            rationale=[],
            protected_boundaries={},
            policy_version="DCG-DECISION-v1",
        )
