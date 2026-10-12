"""Investigation lifecycle: transitions, who may act, auto-reopen on changed Evidence, audit chain."""
import pytest
from fastapi import HTTPException

from presentation.backend.app import investigation_lifecycle as lc, single_specialists
from presentation.backend.app.authorization import Principal

ADMIN = Principal("admin", frozenset({"administrator"}), frozenset({"ZONE-A"}))
SAFETY = Principal("safety-1", frozenset({"safety_operator"}), frozenset({"ZONE-A"}))
SAFETY2 = Principal("safety-2", frozenset({"safety_operator"}), frozenset({"ZONE-A"}))
SECURITY = Principal("security", frozenset({"security_operator"}), frozenset({"ZONE-A"}))


@pytest.fixture
def evidence(monkeypatch):
    state = {"verdict": None}

    def authorized(kind, eid, principal):
        from presentation.backend.app.authentication import authorize
        from presentation.backend.app.authorization import Permission
        authorize(principal, Permission.CAMERA_DETAIL, "ZONE-A")
        return "ZONE-A", {"observation_id": eid, "overall_status": "NON_COMPLIANT", "human_review": state["verdict"]}
    monkeypatch.setattr(single_specialists, "authorized_evidence", authorized)
    return state


def act(principal, action, **kw):
    return lc.transition("ppe", "P1", lc.TransitionInput(action=action, **kw), principal)


RESOLVE = dict(resolution="FALSE_POSITIVE", rationale="Vest visible on second camera angle.", acknowledgment=True)


def test_open_review_resolve_reopen(evidence):
    assert lc.view("ppe", "P1", SAFETY)["state"] == "OPEN"
    assert act(SAFETY, "START_REVIEW")["state"] == "IN_REVIEW"
    resolved = act(SAFETY, "RESOLVE", **RESOLVE)
    assert resolved["state"] == "RESOLVED" and resolved["resolution"] == "FALSE_POSITIVE"
    reopened = act(SAFETY2, "REOPEN", rationale="New footage shows the vest was removed.")
    assert reopened["state"] == "REOPENED"
    assert act(SAFETY2, "START_REVIEW")["assignee"] == "safety-2"
    assert len(lc.view("ppe", "P1", SAFETY)["transitions"]) == 4
    assert lc.verify()["status"] == "PASS"


def test_invalid_transitions_are_refused(evidence):
    with pytest.raises(HTTPException) as e:
        act(SAFETY, "RESOLVE", **RESOLVE)
    assert e.value.status_code == 409
    act(SAFETY, "START_REVIEW")
    with pytest.raises(HTTPException) as e:
        act(SAFETY, "START_REVIEW")
    assert e.value.status_code == 409


def test_only_the_assignee_or_an_administrator_resolves(evidence):
    act(SAFETY, "START_REVIEW")
    with pytest.raises(HTTPException) as e:
        act(SAFETY2, "RESOLVE", **RESOLVE)
    assert e.value.status_code == 403
    assert act(ADMIN, "RESOLVE", **RESOLVE)["state"] == "RESOLVED"


def test_resolve_needs_resolution_rationale_and_acknowledgment(evidence):
    act(SAFETY, "START_REVIEW")
    for bad in (dict(RESOLVE, resolution=None), dict(RESOLVE, rationale="short"), dict(RESOLVE, acknowledgment=False)):
        with pytest.raises(HTTPException) as e:
            act(SAFETY, "RESOLVE", **bad)
        assert e.value.status_code == 422


def test_other_domains_cannot_act(evidence):
    with pytest.raises(HTTPException) as e:
        act(SECURITY, "START_REVIEW")
    assert e.value.status_code == 403


def test_changed_evidence_reopens_a_resolved_investigation(evidence):
    act(SAFETY, "START_REVIEW")
    act(SAFETY, "RESOLVE", **RESOLVE)
    evidence["verdict"] = {"verdict": "OVERRIDDEN", "effective_status": "COMPLIANT"}
    view = lc.view("ppe", "P1", SAFETY)
    assert view["state"] == "REOPENED_EVIDENCE_CHANGED"
    assert act(SAFETY2, "START_REVIEW")["state"] == "IN_REVIEW"


def test_tampering_breaks_the_lifecycle_chain(evidence):
    act(SAFETY, "START_REVIEW")
    with lc.connect() as db:
        db.execute("UPDATE investigation_lifecycle SET actor='someone-else'")
    assert lc.verify()["status"] == "FAILED"
    with pytest.raises(HTTPException) as e:
        act(SAFETY, "RESOLVE", **RESOLVE)
    assert e.value.status_code == 409
