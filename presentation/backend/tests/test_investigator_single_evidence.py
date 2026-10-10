import pytest
from fastapi import HTTPException
from presentation.backend.app import investigator_tools as tools
from presentation.backend.app import investigator_chat as chat
from presentation.backend.app.authorization import Principal

ADMIN=Principal("operator",frozenset({"administrator"}),frozenset({"ZONE-A"}))
OTHER=Principal("other",frozenset({"administrator"}),frozenset({"ZONE-B"}))

def test_single_ppe_uses_existing_detail(monkeypatch):
    from presentation.backend.app import ppe_image_validation
    monkeypatch.setattr(ppe_image_validation,"ppe_observation_detail",lambda eid,p:{
        "observation_id":eid,"zone_id":"ZONE-A","assessment":{"overall_status":"NON_COMPLIANT"}})
    result=tools.single_evidence_context("ppe","P1",ADMIN)
    assert result["source_assessment"]["assessment"]["overall_status"]=="NON_COMPLIANT"
    assert result["correlation_status"]=="NOT_ASSESSED_BY_SINGLE_EVIDENCE_TOOL"

def test_unknown_kind_rejected():
    with pytest.raises(HTTPException) as exc:
        tools.single_evidence_context("invalid","X",ADMIN)
    assert exc.value.status_code==404

def test_zone_denied_after_record_lookup(monkeypatch):
    from presentation.backend.app import ppe_image_validation
    monkeypatch.setattr(ppe_image_validation,"ppe_observation_detail",lambda eid,p:{
        "observation_id":eid,"zone_id":"ZONE-A","assessment":{}})
    with pytest.raises(HTTPException) as exc:
        tools.single_evidence_context("ppe","P1",OTHER)
    assert exc.value.status_code==403

def test_provider_disabled(monkeypatch):
    monkeypatch.setattr(tools,"single_evidence_context",lambda kind,eid,p:{
        "kind":kind,"evidence_id":eid,"source_assessment":{}})
    monkeypatch.setattr(chat,"local_setting",lambda key:"0" if key=="DCG_INVESTIGATOR_ENABLED" else "")
    with pytest.raises(HTTPException) as exc:
        chat.ask_single_evidence("ppe","P1",chat.InvestigatorQuestion(question="Explain this evidence"),ADMIN)
    assert exc.value.status_code==503
