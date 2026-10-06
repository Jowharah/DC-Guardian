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


def main():
    fake_config = {
        "reasoning_runner": fake_reasoning,
        "response_runner": fake_response,
    }
    with patch("integration.service.get_scenario", return_value=fake_config):
        result = run_integrated_scenario(
            "ppe_face",
            scenario_id="SERVICE-CONTRACT-001",
        )

    if not isinstance(result, PipelineResult):
        raise AssertionError("Service did not return PipelineResult.")
    data = result.to_dict()
    if data["evidence"]["layer"] != "EVIDENCE":
        raise AssertionError("Evidence trace missing.")
    if data["reasoning"]["layer"] != "REASONING":
        raise AssertionError("Reasoning trace missing.")
    if data["response"]["layer"] != "RESPONSE":
        raise AssertionError("Response trace missing.")
    if data["decision"]["status"] != "PENDING_DETERMINISTIC_DECISION_RULES":
        raise AssertionError("Decision boundary changed unexpectedly.")

    print("PASS: Reusable scenario service returns unified PipelineResult.")
    print("PASS: Evidence, Reasoning, and Response traces preserved.")
    print("PASS: Decision layer remains explicitly pending.")
    print("=" * 60)
    print("DC-GUARDIAN INTEGRATION SERVICE CONTRACT PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
