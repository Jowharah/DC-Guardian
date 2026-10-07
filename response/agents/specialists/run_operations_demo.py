"""Synthetic end-to-end Operations specialist demo."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from response.agents.providers.openai_provider import OpenAIResponsesProvider  # noqa: E402
from response.agents.routing.specialist_router import route_specialists  # noqa: E402
from response.agents.specialists.base import SpecialistRequest  # noqa: E402
from response.agents.specialists.operations import OperationsSpecialist  # noqa: E402
from response.rag.knowledge_eligibility import evaluate_knowledge_eligibility  # noqa: E402
from response.rag.retrieve import retrieve_knowledge  # noqa: E402


INCIDENT = {
    "scenario_id": "SYNTHETIC-OPS-001",
    "correlation_type": "ENVIRONMENTAL_MAINTENANCE",
    "domains": ["MAINTENANCE", "ENVIRONMENTAL"],
    "shared_scope": "ZONE",
    "shared_entity": "ZONE-B",
    "source": "CONTROLLED_SYNTHETIC_SCENARIO",
    "maintenance": {
        "asset_id": "DRV-TEST-001",
        "host_server": "SRV-B1-01",
        "assessment": "AT_RISK",
        "failure_probability": 0.61,
        "operating_threshold": 0.45,
        "failure_horizon_days": 7,
        "model": "Temporal Random Forest v2",
    },
    "environmental": {
        "sensor_id": "SEN-B-01",
        "source_class": "ENVIRONMENTAL_SENSOR",
        "state": "HIGH_TEMPERATURE",
        "temperature_c": 34.0,
        "zone_id": "ZONE-B",
        "scope_note": (
            "SEN-B-01 is a dedicated ZONE-B sensor and is not assigned directly "
            "to SRV-B1-01."
        ),
    },
    "evidence_boundary": (
        "Phase 2 establishes shared ZONE-B context. It does not establish that "
        "the high-temperature observation caused the drive-risk assessment."
    ),
}

QUERY = (
    "What approved data-center operations and maintenance guidance is relevant "
    "when a storage drive has elevated seven-day failure risk and an independent "
    "zone sensor reports high temperature in the same data-center zone?"
)


def main() -> None:
    load_dotenv(ROOT / ".env")

    routed = route_specialists(INCIDENT["domains"])
    if routed != ["operations"]:
        raise RuntimeError(f"Unexpected specialist routing: {routed}")

    for domain in INCIDENT["domains"]:
        eligibility = evaluate_knowledge_eligibility(domains=[domain])
        if not eligibility["eligible"]:
            raise RuntimeError(
                f"No approved active knowledge for required domain: {domain}"
            )

    evidence = retrieve_knowledge(
        QUERY,
        domains=INCIDENT["domains"],
        top_k=3,
        ranking="controlled",
        abstain=False,
    )
    if not evidence:
        raise RuntimeError("No approved Operations evidence retrieved.")

    print("=" * 60)
    print("DC-GUARDIAN PHASE 3.3 OPERATIONS SPECIALIST DEMO")
    print("=" * 60)
    print(f"Scenario: {INCIDENT['scenario_id']}")
    print(f"Router:   {routed}")
    print("Retrieved evidence:")
    for item in evidence:
        print(
            f"  {item['rank']}. {item['document_id']} "
            f"score={item['score']:.4f} pages={item['pages']}"
        )

    specialist = OperationsSpecialist(OpenAIResponsesProvider())
    result = specialist.assess(
        SpecialistRequest(
            incident_evidence=INCIDENT,
            retrieved_evidence=evidence,
            task=(
                "Assess the maintenance and environmental evidence together and "
                "identify supported operational considerations while preserving "
                "the distinction between correlation and causation."
            ),
            domains=("MAINTENANCE", "ENVIRONMENTAL"),
        )
    )

    combined = json.dumps(result, ensure_ascii=False).lower()
    forbidden_claims = (
        "high temperature caused drv-test-001",
        "high temperature caused the at_risk state",
        "the temperature caused drv-test-001",
        "34.0Â°c caused drv-test-001",
        "34Â°c caused drv-test-001",
        "drv-test-001 will fail within 7 days",
        "drv-test-001 will fail in 7 days",
        "sen-b-01 directly monitors srv-b1-01",
        "sen-b-01 directly measured srv-b1-01",
    )
    matched = [claim for claim in forbidden_claims if claim in combined]
    if matched:
        raise RuntimeError(
            "FAILED OPERATIONS EVIDENCE BOUNDARY: unsupported causal, certain-"
            "failure, or false sensor-scope claim: " + ", ".join(matched)
        )

    print()
    print("Validated Operations assessment:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print()
    print("PASS: Operations correlation/causation and sensor-scope boundaries preserved.")


if __name__ == "__main__":
    main()

