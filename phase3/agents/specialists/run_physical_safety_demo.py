"""Synthetic end-to-end Physical/Safety specialist demo."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from phase3.agents.providers.openai_provider import OpenAIResponsesProvider  # noqa: E402
from phase3.agents.routing.specialist_router import route_specialists  # noqa: E402
from phase3.agents.specialists.base import SpecialistRequest  # noqa: E402
from phase3.agents.specialists.physical_safety import PhysicalSafetySpecialist  # noqa: E402
from phase3.rag.knowledge_eligibility import evaluate_knowledge_eligibility  # noqa: E402
from phase3.rag.retrieve import retrieve_knowledge  # noqa: E402


INCIDENT = {
    "scenario_id": "SYNTHETIC-PPE-FACE-001",
    "correlation_type": "PPE_FACE",
    "domains": ["PHYSICAL_SECURITY", "SAFETY"],
    "shared_scope": "ZONE",
    "shared_entity": "ZONE-B",
    "source": "CONTROLLED_SYNTHETIC_SCENARIO",
    "face": {
        "person_id": "TEST-P003",
        "recognition_status": "RECOGNIZED",
        "authorization_status": "UNAUTHORIZED",
        "camera_id": "CAM-B-01",
        "zone_id": "ZONE-B",
    },
    "ppe": {
        "person_index": 0,
        "compliance": "NON_COMPLIANT",
        "required_ppe": ["helmet", "safety-vest"],
        "camera_id": "CAM-B-01",
        "zone_id": "ZONE-B",
    },
    "identity_boundary": (
        "No explicit cross-model identity evidence links PPE person_index=0 "
        "to Face person_id=TEST-P003."
    ),
}

QUERY = (
    "What approved physical-access and PPE guidance is relevant to a controlled "
    "scenario containing an unauthorized recognized Face observation and a "
    "separate PPE non-compliance observation in the same zone?"
)


def main() -> None:
    load_dotenv(ROOT / ".env")

    routed = route_specialists(INCIDENT["domains"])
    if routed != ["physical_safety"]:
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
        raise RuntimeError("No approved Physical/Safety evidence retrieved.")

    print("=" * 60)
    print("DC-GUARDIAN PHASE 3.3 PHYSICAL/SAFETY SPECIALIST DEMO")
    print("=" * 60)
    print(f"Scenario: {INCIDENT['scenario_id']}")
    print(f"Router:   {routed}")
    print("Retrieved evidence:")
    for item in evidence:
        print(
            f"  {item['rank']}. {item['document_id']} "
            f"score={item['score']:.4f} pages={item['pages']}"
        )

    specialist = PhysicalSafetySpecialist(OpenAIResponsesProvider())
    result = specialist.assess(
        SpecialistRequest(
            incident_evidence=INCIDENT,
            retrieved_evidence=evidence,
            task=(
                "Assess the combined physical-security and safety evidence. "
                "Explain supported operational considerations and limitations."
            ),
            domains=("PHYSICAL_SECURITY", "SAFETY"),
        )
    )

    # Deterministic postcondition: the model must not collapse the anonymous
    # PPE observation into the recognized Face identity.
    combined = json.dumps(result, ensure_ascii=False).lower()
    forbidden_claims = (
        "test-p003 was not wearing",
        "test-p003 is not wearing",
        "test-p003 lacked ppe",
        "test-p003 was non-compliant",
        "test-p003 is non-compliant",
    )
    if any(claim in combined for claim in forbidden_claims):
        raise RuntimeError(
            "FAILED IDENTITY BOUNDARY: specialist attributed anonymous PPE "
            "evidence to the recognized Face subject."
        )

    print()
    print("Validated Physical/Safety assessment:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print()
    print("PASS: Face/PPE cross-model identity boundary preserved.")


if __name__ == "__main__":
    main()
