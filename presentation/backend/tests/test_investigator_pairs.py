"""Investigator pair mode: any two correlated events, authorization before Evidence."""
import pytest
from fastapi import HTTPException
from presentation.backend.app import investigator_tools as tools
from presentation.backend.app import investigator_chat as chat
from presentation.backend.app import correlation_pairs,unified_specialists
from presentation.backend.app.authorization import Principal
from presentation.backend.app.investigator_sources import pair_sources

ADMIN=Principal("operator",frozenset({"administrator"}),frozenset({"ZONE-B"}))
PAIR={"id":"DCG-PAIR-1","type":"REASONING_CONTEXT","zone_id":"ZONE-B",
      "members":[{"kind":"maintenance","domain":"MAINTENANCE","observation_id":"M1"},
                 {"kind":"ssh","domain":"CYBERSECURITY","observation_id":"S1"}],
      "details":{"scope":"SERVER","time_difference_seconds":360},"explanation":"Contextual only."}

@pytest.fixture(autouse=True)
def block_external_openai(monkeypatch):
    from openai import OpenAI
    def forbidden(*args,**kwargs):
        raise AssertionError("Unexpected live OpenAI call from Investigator test")
    monkeypatch.setattr(OpenAI,"__init__",forbidden)

def test_pair_context_reads_both_members(monkeypatch):
    monkeypatch.setattr(correlation_pairs,"find_pair",lambda pid,p:PAIR)
    monkeypatch.setattr(unified_specialists,"member_evidence",
                        lambda kind,oid,zone:{"observation_id":oid,"kind_seen":kind})
    result=tools.pair_context("DCG-PAIR-1",ADMIN)
    assert [m["assessment"]["kind_seen"] for m in result["members"]]==["maintenance","ssh"]
    assert result["saved_decision"] is None
    assert result["restrictions"]["causation_established"] is False
    assert pair_sources(result)==[
        {"kind":"maintenance","id":"M1","role":"saved_source_evidence"},
        {"kind":"ssh","id":"S1","role":"saved_source_evidence"}]

def test_pair_denied_before_evidence_read(monkeypatch):
    def deny(pid,p):raise HTTPException(403,"Access denied")
    def never(*args):raise AssertionError("Evidence must not be read")
    monkeypatch.setattr(correlation_pairs,"find_pair",deny)
    monkeypatch.setattr(unified_specialists,"member_evidence",never)
    with pytest.raises(HTTPException) as exc:
        tools.pair_context("DCG-PAIR-1",ADMIN)
    assert exc.value.status_code==403

def test_pair_ask_disabled_does_not_call_provider(monkeypatch):
    monkeypatch.setattr(tools,"pair_context",lambda pid,p:{"members":[]})
    monkeypatch.setattr(chat,"local_setting",lambda key:"0" if key=="DCG_INVESTIGATOR_ENABLED" else "")
    with pytest.raises(HTTPException) as exc:
        chat.ask_pair("DCG-PAIR-1",chat.InvestigatorQuestion(question="Explain this pair"),ADMIN)
    assert exc.value.status_code==503

def test_source_evidence_keeps_every_member_per_domain(monkeypatch):
    monkeypatch.setattr(unified_specialists,"member_evidence",
                        lambda kind,oid,zone:{"observation_id":oid})
    group={"zone_id":"ZONE-B","evidence":[{"kind":"ssh","observation_id":"S1"},
           {"kind":"ssh","observation_id":"S2"},{"kind":"environment","observation_id":"E1"}]}
    result=unified_specialists.source_evidence(group)
    assert [x["observation_id"] for x in result["ssh"]]==["S1","S2"]
    assert result["environment"]==[{"observation_id":"E1"}]

def test_unified_review_flags_any_unauthorized_face_and_operations_members():
    from presentation.backend.app.unified_decision import evaluate
    group={"evidence":[{"kind":"face"},{"kind":"face"},{"kind":"maintenance"},{"kind":"environment"}],
           "edges":[{"type":"REASONING_CONTEXT"}]}
    unauthorized={"status":"UNAUTHORIZED","source":"NEO4J_READ_ONLY","reason":"GRAPH_RELATIONSHIP_CHECK"}
    faces=[{"recognition_status":"RECOGNIZED","zone_authorization":{"status":"AUTHORIZED"}},
           {"recognition_status":"RECOGNIZED","zone_authorization":unauthorized}]
    result=evaluate(group,{"operations":{"grounding_status":"SUPPORTED"}},faces)
    assert "RECOGNIZED_IDENTITY_NOT_AUTHORIZED_FOR_DECLARED_ZONE" in result["review_reasons"]
    assert "MAINTENANCE_RISK_REQUIRES_SOURCE_REVIEW" in result["review_reasons"]
    assert "ENVIRONMENTAL_CONDITION_REQUIRES_SOURCE_REVIEW" in result["review_reasons"]
    assert result["severity"] is None
