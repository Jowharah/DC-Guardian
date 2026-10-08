"""Evidence projection and RBAC endpoint regression tests."""
from fastapi.testclient import TestClient
from presentation.backend.app.main import app
from presentation.backend.app.authentication import current_principal
from presentation.backend.app.authorization import Principal
from presentation.backend.app.evidence_details import project_evidence, store_evidence
from presentation.backend.app.incident_store import remember
from presentation.backend.app.schemas import IncidentView

def test_ssh_projection_does_not_expose_arbitrary_fields():
    event={"event_id":"EV-1","domain":"CYBERSECURITY",
           "entities":{"source_ip":"203.0.113.77","person_id":"private"},
           "evidence":{"behavior":{"failed_login_count":6,"secret":"private"},
                       "detector_votes":2,"detector_combination":"RULE+AE",
                       "rule":{"prediction":"ANOMALOUS","secret":"private"}},
           "provenance":{"source_type":"CONTROLLED_TEST"}}
    result=project_evidence(event)
    assert result["details"]["source_ip"]=="203.0.113.77"
    assert result["details"]["behavior"]=={"failed_login_count":6}
    assert "private" not in str(result)

def test_environment_projection():
    event={"event_id":"EV-2","domain":"ENVIRONMENTAL",
           "evidence":{"measurements":{"temperature_c":42.5,"humidity_pct":48,"unapproved":"hidden"}},
           "provenance":{"source_type":"CONTROLLED_TEST"}}
    result=project_evidence(event)
    assert result["details"]["measurements"]=={"temperature_c":42.5,"humidity_pct":48}

def test_evidence_endpoint_enforces_role(monkeypatch,tmp_path):
    monkeypatch.setenv("DCG_PRESENTATION_DB",str(tmp_path/"evidence.sqlite3"))
    incident=IncidentView(
        scenario_id="DCG-DETAIL-TEST",scenario_name="ppe_face",
        domains=["CYBERSECURITY"],shared_scope="ZONE",shared_entity="ZONE-B",
        evidence_event_ids=["EV-1"],evidence_events=[{
            "event_id":"EV-1","domain":"CYBERSECURITY","event_type":"SSH_BEHAVIOR_ASSESSMENT",
            "timestamp":"2026-10-06T14:00:00Z","state":"HIGH_CONFIDENCE_ANOMALY","component":"ssh_detector"}],
        decision={"incident_status":"REVIEW_REQUIRED","severity":"HIGH",
            "response_mode":"HUMAN_REVIEW","escalation_required":False,
            "autonomous_action_allowed":False,"decision_rules_triggered":[],
            "rationale":[],"protected_boundaries":{},"policy_version":"DCG-DECISION-v1"})
    remember(incident)
    store_evidence("DCG-DETAIL-TEST",[{"event_id":"EV-1","domain":"CYBERSECURITY",
        "entities":{"source_ip":"203.0.113.77"},"evidence":{},"provenance":{"source_type":"CONTROLLED_TEST"}}])
    client=TestClient(app)
    def set_role(role,zone="ZONE-B"):
        app.dependency_overrides[current_principal]=lambda: Principal("test",frozenset({role}),frozenset({zone}))
    try:
        assert client.get("/api/v1/incidents/DCG-DETAIL-TEST/evidence/EV-1").status_code==401
        set_role("viewer")
        assert client.get("/api/v1/incidents/DCG-DETAIL-TEST/evidence/EV-1").status_code==403
        set_role("security_operator","ZONE-A")
        assert client.get("/api/v1/incidents/DCG-DETAIL-TEST/evidence/EV-1").status_code==403
        set_role("security_operator")
        response=client.get("/api/v1/incidents/DCG-DETAIL-TEST/evidence/EV-1")
        assert response.status_code==200
        assert response.json()["details"]["source_ip"]=="203.0.113.77"
    finally:
        app.dependency_overrides.pop(current_principal,None)
