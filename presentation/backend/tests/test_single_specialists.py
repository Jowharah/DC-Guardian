"""Single-event specialist evaluation: consent, authorization before Evidence, staleness (no OpenAI)."""
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from presentation.backend.app import investigator_tools, single_specialists, unified_specialists
from presentation.backend.app.authentication import current_principal
from presentation.backend.app.authorization import Principal
from presentation.backend.app.main import app

ADMIN = Principal("admin", frozenset({"administrator"}), frozenset({"ZONE-B"}))
SAFETY = Principal("safety", frozenset({"safety_operator"}), frozenset({"ZONE-B"}))
URL = "/api/v1/evidence/ppe/PPE-1/specialist"


@pytest.fixture(autouse=True)
def block_external_openai(monkeypatch):
    from openai import OpenAI
    def forbidden(*args, **kwargs):
        raise AssertionError("Unexpected live OpenAI call")
    monkeypatch.setattr(OpenAI, "__init__", forbidden)


@pytest.fixture
def evidence(monkeypatch):
    state = {"verdict": None, "calls": []}
    monkeypatch.setattr(investigator_tools, "single_evidence_context",
                        lambda kind, eid, p: {"zone_id": "ZONE-B"})
    monkeypatch.setattr(unified_specialists, "member_evidence",
                        lambda kind, eid, zone: {"observation_id": eid, "overall_status": "NON_COMPLIANT",
                                                 "human_review": state["verdict"]})
    def agents(group, evidence):
        state["calls"].append((group, evidence))
        return {"physical_security": {"grounding_status": "SUPPORTED", "assessment": "ok",
                                      "supported_findings": [], "recommended_considerations": [],
                                      "limitations": [], "citations": []}}
    monkeypatch.setattr(unified_specialists, "run_agents", agents)
    return state


def client_as(principal):
    app.dependency_overrides[current_principal] = lambda: principal
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_overrides():
    yield
    app.dependency_overrides.pop(current_principal, None)


def test_consent_is_required_and_nothing_is_sent_without_it(evidence):
    client = client_as(ADMIN)
    assert client.post(URL, json={}).status_code == 400
    assert client.post(URL, json={"acknowledgment": False}).status_code == 400
    assert evidence["calls"] == []


def test_evaluation_is_saved_without_links_or_severity(evidence):
    client = client_as(ADMIN)
    assert client.get(URL).status_code == 404
    saved = client.post(URL, json={"acknowledgment": True})
    assert saved.status_code == 200 and saved.json()["decision_severity"] is None
    group, sent = evidence["calls"][0]
    assert group == {"zone_id": "ZONE-B", "edges": []} and list(sent) == ["ppe"]
    read = client.get(URL).json()
    assert read["specialists"]["physical_security"]["grounding_status"] == "SUPPORTED"
    assert read["evidence_changed_since"] is False


def test_a_later_human_verdict_marks_the_result_outdated(evidence):
    client = client_as(ADMIN)
    client.post(URL, json={"acknowledgment": True})
    evidence["verdict"] = {"verdict": "OVERRIDDEN", "effective_status": "COMPLIANT"}
    assert client.get(URL).json()["evidence_changed_since"] is True


def test_only_administrators_may_run_it(evidence):
    response = client_as(SAFETY).post(URL, json={"acknowledgment": True})
    assert response.status_code == 403 and evidence["calls"] == []


def test_authorization_happens_before_evidence_is_read(monkeypatch):
    def deny(kind, eid, p):
        raise HTTPException(403, "Access denied")
    def never(*args):
        raise AssertionError("Evidence must not be read")
    monkeypatch.setattr(investigator_tools, "single_evidence_context", deny)
    monkeypatch.setattr(unified_specialists, "member_evidence", never)
    assert client_as(ADMIN).post(URL, json={"acknowledgment": True}).status_code == 403


def test_unknown_domain_is_rejected():
    assert client_as(ADMIN).get("/api/v1/evidence/badge/X/specialist").status_code == 404
