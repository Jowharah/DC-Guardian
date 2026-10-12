"""Contract for the reusable integrated scenario service."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from integration.schemas.pipeline_result import PipelineResult  # noqa: E402
from integration.service import run_integrated_scenario  # noqa: E402


def fake_reasoning(*, scenario_id):
    return {
        "scenario_id": scenario_id,
        "domains": ["PHYSICAL_SECURITY", "SAFETY"],
        "correlation": {"correlation_type": "TEST", "events": []},
        "shared_scope": "ZONE",
        "shared_entity": "ZONE-B",
        "authorization_status": "UNAUTHORIZED",
        "identity_link_established": False,
        "evidence_events": [{"event_id": "E1"}, {"event_id": "E2"}],
    }


def fake_response(reasoning):
    return {
        "specialists": ["physical_safety"],
        "retrieved_evidence": [],
        "assessment": {
            "grounding_status": "PARTIALLY_SUPPORTED",
            "assessment": "Test assessment.",
        },
        "boundary_claims": {"identity_link_established": False},
    }


def service_result():
    fake_config = {"reasoning_runner": fake_reasoning, "response_runner": fake_response}
    with patch("integration.service.get_scenario", return_value=fake_config):
        return run_integrated_scenario("ppe_face", scenario_id="SERVICE-CONTRACT-001")


def test_service_returns_a_pipeline_result_with_every_trace():
    result = service_result()
    assert isinstance(result, PipelineResult)
    data = result.to_dict()
    assert data["evidence"]["layer"] == "EVIDENCE"
    assert data["reasoning"]["layer"] == "REASONING"
    assert data["response"]["layer"] == "RESPONSE"


def test_decision_rules_v1_applied_without_autonomous_action():
    # The service applies deterministic Decision Rules v1 (since d4cb326).
    decision = service_result().to_dict()["decision"]
    assert decision.get("policy_version") == "DCG-DECISION-v1"
    assert decision["autonomous_action_allowed"] is False
    assert decision["severity"] in ("LOW", "MEDIUM", "HIGH")
    assert decision["protected_boundaries"]["identity_link_established"] is False


def main():
    test_service_returns_a_pipeline_result_with_every_trace()
    print("PASS: Reusable scenario service returns unified PipelineResult.")
    print("PASS: Evidence, Reasoning, and Response traces preserved.")
    test_decision_rules_v1_applied_without_autonomous_action()
    print("PASS: Deterministic Decision Rules v1 applied; no autonomous action.")
    print("=" * 60)
    print("DC-GUARDIAN INTEGRATION SERVICE CONTRACT PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
