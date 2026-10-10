import pytest
from fastapi import HTTPException
from presentation.backend.app import investigator_chat as chat
from presentation.backend.app.authorization import Principal

ADMIN=Principal("operator",frozenset({"administrator"}),frozenset({"ZONE-A"}))
CONTEXT={"group_id":"G1","zone_id":"ZONE-A",
 "evidence_refs":[{"kind":"ssh","observation_id":"SSH-1"}],
 "contextual_links":[],"source_assessments":{"ssh":{"evidence_state":"HIGH_CONFIDENCE_ANOMALY"}},
 "deterministic_review":None,"restrictions":{"read_only":True},
 "human_review_records":[{"outcome":"NEEDS_FOLLOW_UP","recorded_at":"2026-10-10T00:00:00Z",
                          "rationale":"Private rationale must not be sent"}]}

def test_feature_flag_denies_without_provider(monkeypatch):
    monkeypatch.setattr(chat,"unified_context",lambda group_id,principal:CONTEXT)
    monkeypatch.delenv("DCG_INVESTIGATOR_ENABLED",raising=False)
    with pytest.raises(HTTPException) as exc:
        chat.ask_investigator("G1",chat.InvestigatorQuestion(question="Explain this anomaly"),ADMIN)
    assert exc.value.status_code==503

def test_authorization_precedes_provider(monkeypatch):
    def deny(group_id,principal):raise HTTPException(403,"Access denied")
    monkeypatch.setattr(chat,"unified_context",deny)
    monkeypatch.setenv("DCG_INVESTIGATOR_ENABLED","1")
    monkeypatch.setenv("OPENAI_API_KEY","not-a-real-key")
    with pytest.raises(HTTPException) as exc:
        chat.ask_investigator("G1",chat.InvestigatorQuestion(question="Explain this anomaly"),ADMIN)
    assert exc.value.status_code==403

def test_missing_key_fails_closed(monkeypatch):
    monkeypatch.setattr(chat,"unified_context",lambda group_id,principal:CONTEXT)
    monkeypatch.setenv("DCG_INVESTIGATOR_ENABLED","1")
    monkeypatch.delenv("OPENAI_API_KEY",raising=False)
    with pytest.raises(HTTPException) as exc:
        chat.ask_investigator("G1",chat.InvestigatorQuestion(question="Explain this anomaly"),ADMIN)
    assert exc.value.status_code==503
