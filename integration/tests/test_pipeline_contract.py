"""Contract for one connected Evidence -> Reasoning -> Response flow."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from integration.pipeline import run_dc_guardian_scenario  # noqa: E402
from integration.scenarios.controlled_scenarios import ppe_face_scenario  # noqa: E402


def evidence_runner(scenario):
    inputs = scenario["evidence_inputs"]
    return [
        {
            "event_id": "EVT-FACE-INTEGRATION-001",
            "domain": "PHYSICAL_SECURITY",
            "event_type": "FACE_IDENTIFICATION_ASSESSMENT",
            **inputs["face"],
        },
        {
            "event_id": "EVT-PPE-INTEGRATION-001",
            "domain": "SAFETY",
            "event_type": "PPE_COMPLIANCE_ASSESSMENT",
            **inputs["ppe"],
        },
    ]


def reasoning_runner(events, scenario_id):
    if len(events) != 2:
        raise AssertionError("Reasoning did not receive Evidence events.")
    return {
        "correlation_id": "CORR-PPE-FACE-INTEGRATION-001",
        "correlation_type": "PPE_FACE",
        "domains": ["PHYSICAL_SECURITY", "SAFETY"],
        "shared_scope": "ZONE",
        "shared_entity": "ZONE-B",
        "scenario_id": scenario_id,
        "authorization_status": "UNAUTHORIZED",
        "identity_link_established": False,
    }


def response_runner(payload):
    reasoning = payload["reasoning"]
    if reasoning["routed_specialists"] != ["physical_safety"]:
        raise AssertionError("Response received incorrect specialist route.")
    if reasoning["identity_link_established"]:
        raise AssertionError("Identity boundary was lost before Response.")
    return {
        "specialists": reasoning["routed_specialists"],
        "grounding_status": "PARTIALLY_SUPPORTED",
        "assessment": (
            "Physical-security and PPE evidence are relevant in shared ZONE-B "
            "context without establishing cross-model person identity."
        ),
        "identity_link_established": False,
    }


def main():
    result = run_dc_guardian_scenario(
        scenario=ppe_face_scenario(),
        evidence_runner=evidence_runner,
        reasoning_runner=reasoning_runner,
        response_runner=response_runner,
    )
    data = result.to_dict()

    if data["evidence"]["layer"] != "EVIDENCE":
        raise AssertionError("Evidence layer missing.")
    if data["reasoning"]["layer"] != "REASONING":
        raise AssertionError("Reasoning layer missing.")
    if data["response"]["layer"] != "RESPONSE":
        raise AssertionError("Response layer missing.")
    if data["response"]["specialists"] != ["physical_safety"]:
        raise AssertionError("Physical/Safety route was not preserved.")
    if data["response"]["identity_link_established"]:
        raise AssertionError("Unsupported Face/PPE identity link was introduced.")

    print("=" * 60)
    print("DC-GUARDIAN CONNECTED PIPELINE CONTRACT")
    print("EVIDENCE -> REASONING -> RESPONSE")
    print("=" * 60)
    print("PASS: Evidence events flowed into Reasoning.")
    print("PASS: Reasoning context flowed into Response.")
    print("PASS: Deterministic specialist routing preserved.")
    print("PASS: Face/PPE identity boundary preserved end-to-end.")
    print("PASS: Unified PipelineResult produced.")
    print("=" * 60)
    print("DC-GUARDIAN CONNECTED PIPELINE CONTRACT PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
