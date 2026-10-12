"""Post-generation overclaim judge: wiring, privacy, failure handling (fake OpenAI client)."""
import json

import pytest

from presentation.backend.app import investigator_chat as chat, investigator_judge, investigator_tools
from presentation.backend.app.authorization import Principal

ADMIN = Principal("operator", frozenset({"administrator"}), frozenset({"ZONE-A"}))
CONTEXT = {"kind": "face", "evidence_id": "F1", "zone_id": "ZONE-A", "human_review": None, "restrictions": {},
           "source_assessment": {"observation_id": "F1", "assessment": {"recognition_status": "RECOGNIZED", "person_id": "P005"}}}
ANSWER = "P005 was recognized. The person was standing in the server hall when the photo was taken."


class Fake:
    calls = []
    judge_reply = None

    def __init__(self, **kwargs):
        self.responses = self

    def create(self, **kwargs):
        Fake.calls.append(kwargs)
        if "text" in kwargs:  # the judge asks for structured JSON
            if Fake.judge_reply is None:
                raise RuntimeError("judge down")
            return type("R", (), {"output_text": json.dumps(Fake.judge_reply)})()
        person = next(t for t in kwargs["input"].split('"') if t.startswith("PERSON-"))
        return type("R", (), {"output_text": ANSWER.replace("P005", person)})()


@pytest.fixture
def setup(monkeypatch):
    import openai
    Fake.calls, Fake.judge_reply = [], None
    monkeypatch.setattr(openai, "OpenAI", Fake)
    monkeypatch.setenv("DCG_INVESTIGATOR_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-real")
    monkeypatch.setattr(investigator_tools, "single_evidence_context", lambda kind, eid, p: json.loads(json.dumps(CONTEXT)))


def ask():
    return chat.ask_single_evidence("face", "F1", chat.InvestigatorQuestion(question="Where was this person?"), ADMIN)


def test_flagged_sentence_is_reported_and_raises_the_status(setup):
    Fake.judge_reply = {"findings": [{"type": "PRESENCE", "reason": "location stated as fact",
                                      "sentence": "The person was standing in the server hall when the photo was taken."}]}
    result = ask()
    judge = result["claim_checks"]["model_judge"]
    assert judge["status"] == "FLAGGED" and judge["findings"][0]["type"] == "PRESENCE"
    assert result["claim_checks"]["status"] == "VIOLATION"
    assert result["answer"].startswith("P005 ")  # operator still sees the answer, unmasked


def test_judge_sees_only_the_pseudonymized_answer(setup):
    Fake.judge_reply = {"findings": []}
    assert ask()["claim_checks"]["model_judge"]["status"] == "CLEAN"
    judge_call = next(c for c in Fake.calls if "text" in c)
    assert "P005" not in judge_call["input"] and "PERSON-" in judge_call["input"]
    assert "authorized_context" not in judge_call["input"] and judge_call["store"] is False


def test_invented_quotes_are_dropped(setup):
    Fake.judge_reply = {"findings": [{"type": "CAUSATION", "reason": "x", "sentence": "A sentence that is not in the answer."}]}
    assert ask()["claim_checks"]["model_judge"]["status"] == "CLEAN"


def test_judge_failure_never_blocks_the_answer(setup):
    result = ask()
    assert result["answer"] and result["claim_checks"]["model_judge"]["status"] == "UNAVAILABLE"


def test_judge_can_be_disabled(setup, monkeypatch):
    monkeypatch.setenv("DCG_INVESTIGATOR_JUDGE_ENABLED", "0")
    assert ask()["claim_checks"]["model_judge"]["status"] == "DISABLED"
    assert not any("text" in c for c in Fake.calls)
