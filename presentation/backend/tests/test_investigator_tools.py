"""Investigator tool contracts over existing Evidence adapters, without model calls."""
import pytest
from fastapi import HTTPException
from presentation.backend.app import investigator_tools as tools
from presentation.backend.app.authorization import Principal

ADMIN=Principal("operator",frozenset({"administrator"}),frozenset({"ZONE-A"}))
OTHER=Principal("operator",frozenset({"administrator"}),frozenset({"ZONE-B"}))
GROUP={"id":"G1","zone_id":"ZONE-A","evidence":[{"kind":"ssh","observation_id":"S1"}],
       "edges":[{"type":"FACE_SSH_CONTEXT","source_id":"L1"}]}

@pytest.fixture
def sources(monkeypatch):
    def group(group_id,principal):
        if "ZONE-A" not in principal.zones:raise HTTPException(403,"Access denied")
        return GROUP
    monkeypatch.setattr(tools,"find_group",group)
    monkeypatch.setattr(tools,"source_evidence",lambda group:{"ssh":{"evidence_state":"HIGH_CONFIDENCE_ANOMALY"}})
    monkeypatch.setattr(tools,"read_specialists",lambda group_id,principal:{"specialists":{"cybersecurity":{"grounding_status":"SUPPORTED"}}})
    monkeypatch.setattr(tools,"read_review_decision",lambda group_id,principal:{"decision":{"status":"EVIDENCE_REVIEW_REQUIRED","severity":None}})
    monkeypatch.setattr(tools,"list_reviews",lambda group_id,principal:{"records":[{"outcome":"NEEDS_FOLLOW_UP"}]})

def test_existing_evidence_context(sources):
    result=tools.unified_context("G1",ADMIN)
    assert result["source_assessments"]["ssh"]["evidence_state"]=="HIGH_CONFIDENCE_ANOMALY"
    assert result["human_review_records"][0]["outcome"]=="NEEDS_FOLLOW_UP"
    assert result["restrictions"]["autonomous_action_allowed"] is False
    assert result["restrictions"]["severity_assigned"] is False

def test_zone_isolation_before_evidence_read(sources,monkeypatch):
    def denied(group):
        raise AssertionError("Evidence must not be read")
    monkeypatch.setattr(tools,"source_evidence",denied)
    with pytest.raises(HTTPException) as error:
        tools.unified_context("G1",OTHER)
    assert error.value.status_code==403

def test_graph_delegates_existing_read_only_projection(monkeypatch):
    monkeypatch.setattr(tools,"unified_graph",lambda group_id,principal:{"nodes":[],"edges":[]})
    assert tools.unified_graph_context("G1",ADMIN)=={"nodes":[],"edges":[]}
