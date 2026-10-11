"""Outbound Investigator payload minimization and the hash-chained call audit (fake OpenAI client)."""
import hashlib
import json

import pytest
from fastapi import HTTPException

from presentation.backend.app import investigator_audit, investigator_chat as chat, investigator_tools
from presentation.backend.app.authorization import Principal

ADMIN = Principal("operator", frozenset({"administrator"}), frozenset({"ZONE-A"}))
FACE_CONTEXT = {
    "kind": "face", "evidence_id": "F1", "zone_id": "ZONE-A",
    "source_assessment": {"observation_id": "F1", "zone_id": "ZONE-A", "assessment": {
        "recognition_status": "RECOGNIZED", "person_id": "P005", "similarity": 0.81,
        "facial_area": {"x": 10, "y": 12, "w": 80, "h": 90, "left_eye": [30, 40], "right_eye": [60, 40]},
        "embedding": [0.1, 0.2]}},
    "human_review": {"verdict": "CONFIRMED", "effective_status": "RECOGNIZED", "reviewer": "should-not-leave",
                     "rationale": "private note"},
    "restrictions": {"read_only": True},
}


class FakeClient:
    sent = []
    fail = False

    def __init__(self, **kwargs):
        self.responses = self

    def create(self, **kwargs):
        FakeClient.sent.append(kwargs)
        if FakeClient.fail:
            raise RuntimeError("provider down")
        return type("R", (), {"output_text": "P005 is recognized; the record does not establish presence."})()


@pytest.fixture
def fake_openai(monkeypatch):
    import openai
    FakeClient.sent, FakeClient.fail = [], False
    monkeypatch.setattr(openai, "OpenAI", FakeClient)
    monkeypatch.setenv("DCG_INVESTIGATOR_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-real")
    monkeypatch.setattr(investigator_tools, "single_evidence_context", lambda kind, eid, p: json.loads(json.dumps(FACE_CONTEXT)))
    return FakeClient


def ask():
    return chat.ask_single_evidence("face", "F1", chat.InvestigatorQuestion(question="Who is this?"), ADMIN)


def test_outbound_payload_has_no_biometric_or_reviewer_fields(fake_openai):
    result = ask()
    sent = fake_openai.sent[0]
    payload = json.loads(sent["input"])
    text = json.dumps(payload)
    for denied in ("facial_area", "left_eye", "embedding", "reviewer", "rationale", "should-not-leave", "private note"):
        assert denied not in text, denied
    assert payload["authorized_context"]["source_assessment"]["assessment"]["person_id"] == "P005"
    assert sent["store"] is False
    assert result["claim_checks"]["status"] == "NO_RECOGNIZED_PROBLEM"


def test_every_call_is_audited_with_the_exact_payload_hash(fake_openai):
    ask()
    with investigator_audit.connect() as db:
        row = db.execute("SELECT subject,mode,target_id,outcome,payload_sha256,answer_sha256,claim_status "
                         "FROM investigator_audit").fetchone()
    expected = hashlib.sha256(fake_openai.sent[0]["input"].encode("utf-8")).hexdigest()
    assert row == ("operator", "single", "face:F1", "ANSWERED", expected, row[5], "NO_RECOGNIZED_PROBLEM")
    assert row[5] is not None


def test_provider_failure_is_audited_and_the_chain_verifies(fake_openai):
    ask()
    fake_openai.fail = True
    with pytest.raises(HTTPException):
        ask()
    with investigator_audit.connect() as db:
        outcomes = [r[0] for r in db.execute("SELECT outcome FROM investigator_audit ORDER BY rowid")]
    assert outcomes == ["ANSWERED", "PROVIDER_FAILED"]
    assert investigator_audit.verify()["status"] == "PASS"


def test_tampering_breaks_the_chain(fake_openai):
    ask()
    ask()
    with investigator_audit.connect() as db:
        db.execute("UPDATE investigator_audit SET subject='someone-else' WHERE rowid=1")
    assert investigator_audit.verify()["status"] == "FAILED"
