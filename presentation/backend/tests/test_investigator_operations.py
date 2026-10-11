import pytest
from fastapi import HTTPException
from presentation.backend.app import investigator_tools as tools
from presentation.backend.app import investigator_chat as chat
from presentation.backend.app.authorization import Principal

ADMIN=Principal("operator",frozenset({"administrator"}),frozenset({"ZONE-B"}))
OTHER=Principal("other",frozenset({"administrator"}),frozenset({"ZONE-A"}))
CANDIDATE={"id":"OP1","zone_id":"ZONE-B",
 "maintenance":{"event_id":"M1","assessment":{"risk":"AT_RISK"}},
 "environment":{"event_id":"E1","assessment":{"temperature_c":38.0}},
 "shared_scope":"ZONE","shared_entity":"ZONE-B","time_difference_seconds":360}

def test_existing_operational_context(monkeypatch):
    from presentation.backend.app import operational_decision
    monkeypatch.setattr(operational_decision,"get_candidate",lambda cid,p:CANDIDATE)
    monkeypatch.setattr(operational_decision,"read_decision",lambda cid,p:{
        "specialist":{"grounding_status":"SUPPORTED"},
        "decision":{"severity":"MEDIUM"},
        "evidence_event_ids":["M1","E1"]})
    result=tools.operational_context("OP1",ADMIN)
    assert result["maintenance"]["assessment"]["risk"]=="AT_RISK"
    assert result["saved_decision"]["severity"]=="MEDIUM"
    assert result["restrictions"]["causation_established"] is False

def test_denied_before_evidence_and_provider(monkeypatch):
    from presentation.backend.app import operational_decision
    def deny(cid,p):raise HTTPException(403,"Access denied")
    monkeypatch.setattr(operational_decision,"get_candidate",deny)
    with pytest.raises(HTTPException) as exc:
        tools.operational_context("OP1",OTHER)
    assert exc.value.status_code==403

def test_disabled_provider_does_not_call_openai(monkeypatch):
    monkeypatch.setattr(tools,"operational_context",lambda cid,p:{
        **CANDIDATE,"correlation":{},"saved_specialist":None,
        "saved_decision":None,"evidence_event_ids":[],"restrictions":{}})
    monkeypatch.setattr(chat,"local_setting",lambda key:"0" if key=="DCG_INVESTIGATOR_ENABLED" else "")
    with pytest.raises(HTTPException) as exc:
        chat.ask_operations("OP1",chat.InvestigatorQuestion(question="Explain operational risk"),ADMIN)
    assert exc.value.status_code==503
