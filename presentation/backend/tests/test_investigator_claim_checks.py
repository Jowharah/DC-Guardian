"""Claim checks on Investigator answers: labelled examples, every mode's wiring (no OpenAI)."""
import pytest

from presentation.backend.app.investigator_claim_checks import claim_checks

MAINT = ("maintenance", "M1", {"assessment": "AT_RISK", "failure_probability": 0.82, "human_review": None})
ENV = ("environment", "E1", {"assessment": "HIGH_TEMPERATURE", "human_review": None})
PPE = ("ppe", "P1", {"overall_status": "NON_COMPLIANT",
                     "human_review": {"verdict": "OVERRIDDEN", "effective_status": "COMPLIANT"}})
FACE = ("face", "F1", {"recognition_status": "RECOGNIZED", "person_id": "P005",
                       "zone_authorization": {"status": "UNAUTHORIZED"}, "human_review": None})
SSH = ("ssh", "S1", {"evidence_state": "HIGH_CONFIDENCE_ANOMALY", "human_review": None})

# (answer, records, expected overall status) — honest answers and overclaims.
EXAMPLES = [
    ("The drive is at risk and the hall temperature was high. The correlation does not establish that the heat caused the drive risk.",
     [MAINT, ENV], "NO_RECOGNIZED_PROBLEM"),
    ("The high temperature caused the drive failure risk.", [MAINT, ENV], "VIOLATION"),
    ("The heat may have contributed to the drive risk, but this is not established.", [MAINT, ENV], "NO_RECOGNIZED_PROBLEM"),
    ("Elevated temperature could have led to faster degradation.", [MAINT, ENV], "HEDGED"),
    ("P005 logged in to the server during the SSH anomaly.", [FACE, SSH], "VIOLATION"),
    ("The recognized person P005 is unauthorized for this zone; the SSH activity cannot be attributed to them.",
     [FACE, SSH], "NO_RECOGNIZED_PROBLEM"),
    ("The server was compromised.", [SSH], "VIOLATION"),
    ("The SSH evidence shows anomalous activity; it does not confirm the server was compromised.", [SSH], "NO_RECOGNIZED_PROBLEM"),
    ("The SSH activity looks benign.", [SSH], "MISMATCH"),
    ("The drive is healthy.", [MAINT], "MISMATCH"),
    ("The worker was compliant after human review.", [PPE], "NO_RECOGNIZED_PROBLEM"),   # matches the human override
    ("The worker was non-compliant according to the detector.", [PPE], "NO_RECOGNIZED_PROBLEM"),  # matches the detector
    ("P005 is authorized for this zone.", [FACE], "MISMATCH"),
    ("I have blocked the source IP.", [SSH], "VIOLATION"),
    ("The intruder was physically present in the server hall.", [FACE], "VIOLATION"),
]


@pytest.mark.parametrize("answer,records,expected", EXAMPLES)
def test_labelled_examples(answer, records, expected):
    assert claim_checks(answer, records)["status"] == expected, claim_checks(answer, records)["checks"]


def test_state_claims_are_skipped_when_a_domain_has_several_members():
    second = ("maintenance", "M2", {"assessment": "HEALTHY", "human_review": None})
    result = claim_checks("The drive is healthy.", [MAINT, second])
    assert result["status"] == "NO_RECOGNIZED_PROBLEM"
    assert result["skipped"][0]["reason"] == "AMBIGUOUS_MULTIPLE_MEMBERS"


def test_every_mode_returns_claim_checks(monkeypatch):
    from presentation.backend.app import investigator_chat as chat, investigator_tools
    from presentation.backend.app.authorization import Principal
    admin = Principal("op", frozenset({"administrator"}), frozenset({"ZONE-A"}))
    monkeypatch.setattr(chat, "require_enabled", lambda: None)
    monkeypatch.setattr(chat, "ask_model", lambda *a, **k: "The SSH activity looks benign.")
    monkeypatch.setattr(chat, "audit_call", lambda *a, **k: None, raising=False)
    monkeypatch.setattr(investigator_tools, "single_evidence_context", lambda kind, eid, p: {
        "kind": "ssh", "evidence_id": "S1", "zone_id": "ZONE-A",
        "source_assessment": {"event_id": "S1", "evidence_state": "HIGH_CONFIDENCE_ANOMALY"},
        "human_review": None, "restrictions": {}})
    result = chat.ask_single_evidence("ssh", "S1", chat.InvestigatorQuestion(question="Is this benign?"), admin)
    assert result["claim_checks"]["status"] == "MISMATCH"


def test_per_person_ppe_statuses_are_not_mismatches():
    """Live run 2026-10-12: one worker compliant, one not; overall NON_COMPLIANT."""
    record = ("ppe", "P2", {"overall_status": "NON_COMPLIANT", "human_review": None, "people": [
        {"person_index": 0, "status": "COMPLIANT"}, {"person_index": 1, "status": "NON_COMPLIANT"}]})
    answer = "Person 0 compliance status: COMPLIANT. Missing PPE: None. Person 1 is non-compliant: missing safety vest."
    result = claim_checks(answer, [record])
    assert result["status"] == "NO_RECOGNIZED_PROBLEM", result["checks"]
    assert result["summary"]["state_matches"] == 2
