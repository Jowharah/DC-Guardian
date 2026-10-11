"""Unified specialists: domain-specific retrieval and one retry on a failed grounding check (no OpenAI)."""
import pytest
from fastapi import HTTPException

from presentation.backend.app import unified_specialists as us


class Agent:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0

    def assess(self, request):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def test_query_names_every_domain_instead_of_a_generic_phrase():
    query = us.knowledge_query(["MAINTENANCE", "ENVIRONMENTAL"])
    assert "SMART" in query and "temperature" in query
    assert "evidence review" not in query


def test_one_failed_grounding_check_is_retried():
    agent = Agent([ValueError("must cite retrieved evidence"), {"grounding_status": "SUPPORTED"}])
    assert us.assess_grounded("operations", agent, object()) == {"grounding_status": "SUPPORTED"}
    assert agent.calls == 2


def test_two_failed_grounding_checks_explain_the_503():
    agent = Agent([ValueError("must cite retrieved evidence")] * 2)
    with pytest.raises(HTTPException) as error:
        us.assess_grounded("operations", agent, object())
    assert error.value.status_code == 503
    assert "Operations specialist" in error.value.detail and "grounding check" in error.value.detail
    assert agent.calls == 2


def test_provider_errors_are_not_retried():
    agent = Agent([RuntimeError("provider down")])
    with pytest.raises(RuntimeError):
        us.assess_grounded("operations", agent, object())
    assert agent.calls == 1
