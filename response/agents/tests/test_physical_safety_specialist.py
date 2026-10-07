"""Local contracts for the Physical/Safety specialist."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from response.agents.specialists.base import SpecialistRequest  # noqa: E402
from response.agents.specialists.physical_safety import PhysicalSafetySpecialist  # noqa: E402


EVIDENCE = [
    {
        "chunk_id": "NIST:PE:1",
        "document_id": "NIST-SP-800-53R5-PE",
        "title": "NIST SP 800-53 Rev. 5 Physical and Environmental Protection",
        "authority_type": "GOVERNMENT_STANDARD",
        "publisher": "NIST",
        "version": "Rev. 5",
        "pages": [207, 208],
        "text": "Physical access authorization should be verified before access is granted.",
    },
    {
        "chunk_id": "OSHA:PPE:1",
        "document_id": "OSHA-1910-132",
        "title": "OSHA 1910.132",
        "authority_type": "REGULATION",
        "publisher": "OSHA",
        "version": "current",
        "pages": [1],
        "text": "Protective equipment requirements apply where hazards require PPE.",
    },
]


class SafePhysicalProvider:
    def reason(self, payload):
        task = payload["task"]
        if "person_index" not in task:
            raise AssertionError("Specialist identity-boundary instruction missing.")
        return {
            "assessment": (
                "Unauthorized Face evidence and PPE non-compliance are both present, "
                "but the supplied evidence does not establish that the anonymous PPE "
                "person is the recognized Face subject."
            ),
            "supported_findings": [
                "Graph-derived authorization evidence indicates an unauthorized recognized identity.",
                "PPE evidence indicates a non-compliant anonymous person observation.",
            ],
            "recommended_considerations": [
                "Review the applicable access authorization and PPE evidence separately."
            ],
            "grounding_status": "PARTIALLY_SUPPORTED",
            "citations": [
                {"chunk_id": "NIST:PE:1", "document_id": "NIST-SP-800-53R5-PE"},
                {"chunk_id": "OSHA:PPE:1", "document_id": "OSHA-1910-132"},
            ],
            "limitations": [
                "No explicit cross-model identity link connects PPE person_index to the Face subject."
            ],
        }


def main():
    specialist = PhysicalSafetySpecialist(SafePhysicalProvider())
    request = SpecialistRequest(
        incident_evidence={
            "correlation_type": "PPE_FACE",
            "domains": ["PHYSICAL_SECURITY", "SAFETY"],
            "face": {
                "person_id": "TEST-P003",
                "recognition_status": "RECOGNIZED",
                "authorization_status": "UNAUTHORIZED",
                "zone_id": "ZONE-B",
            },
            "ppe": {
                "person_index": 0,
                "compliance": "NON_COMPLIANT",
                "zone_id": "ZONE-B",
            },
        },
        retrieved_evidence=EVIDENCE,
        task="Assess the combined physical-security and safety evidence.",
        domains=("PHYSICAL_SECURITY", "SAFETY"),
    )
    result = specialist.assess(request)
    if result["grounding_status"] != "PARTIALLY_SUPPORTED":
        raise AssertionError("Expected PARTIALLY_SUPPORTED result.")
    joined = " ".join(
        [result["assessment"]]
        + result["supported_findings"]
        + result["limitations"]
    ).lower()
    if "does not establish" not in joined and "no explicit" not in joined:
        raise AssertionError("Cross-model identity limitation was not preserved.")
    print("PASS: Combined Face + PPE evidence remains identity-safe.")

    try:
        specialist.assess(
            SpecialistRequest(
                incident_evidence={},
                retrieved_evidence=[],
                task="Invalid domain test.",
                domains=("CYBERSECURITY",),
            )
        )
    except ValueError:
        print("PASS: Unsupported specialist domain rejected.")
    else:
        raise AssertionError("Physical/Safety specialist accepted CYBERSECURITY.")

    print("=" * 60)
    print("DC-GUARDIAN PHASE 3.3 PHYSICAL/SAFETY SPECIALIST CONTRACT PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()

