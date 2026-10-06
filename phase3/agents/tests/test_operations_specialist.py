"""Local contracts for the Phase 3.3 Operations specialist."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from phase3.agents.specialists.base import SpecialistRequest  # noqa: E402
from phase3.agents.specialists.operations import OperationsSpecialist  # noqa: E402


EVIDENCE = [{
    "chunk_id": "DOE:OM:1",
    "document_id": "DOE-FEMP-OM-BEST-PRACTICES",
    "title": "Operations and Maintenance Best Practices Guide",
    "authority_type": "GOVERNMENT_GUIDANCE",
    "publisher": "DOE FEMP",
    "version": "current",
    "pages": [1],
    "text": "Operations and maintenance programs use condition information to support maintenance decisions.",
}]


class SafeOperationsProvider:
    def reason(self, payload):
        task = payload["task"]
        required = (
            "not a guaranteed failure",
            "does not by itself prove hardware damage or root cause",
            "operational relevance, not causation",
        )
        if not all(item in task for item in required):
            raise AssertionError("Operations evidence-boundary instructions missing.")
        return {
            "assessment": (
                "The drive risk and high-temperature evidence are operationally "
                "relevant together, but the supplied evidence does not establish "
                "that temperature caused the predicted drive risk."
            ),
            "supported_findings": [
                "The maintenance model reports AT_RISK within a seven-day horizon.",
                "Environmental evidence reports HIGH_TEMPERATURE in related infrastructure.",
            ],
            "recommended_considerations": [
                "Review drive-health and environmental evidence together while preserving their separate provenance."
            ],
            "grounding_status": "SUPPORTED",
            "citations": [{
                "chunk_id": "DOE:OM:1",
                "document_id": "DOE-FEMP-OM-BEST-PRACTICES",
            }],
            "limitations": [
                "Correlation does not establish temperature as the cause of drive failure risk."
            ],
        }


def main():
    specialist = OperationsSpecialist(SafeOperationsProvider())
    result = specialist.assess(
        SpecialistRequest(
            incident_evidence={
                "correlation_type": "ENVIRONMENTAL_MAINTENANCE",
                "domains": ["MAINTENANCE", "ENVIRONMENTAL"],
                "maintenance": {
                    "assessment": "AT_RISK",
                    "failure_probability": 0.61,
                    "operating_threshold": 0.45,
                    "failure_horizon_days": 7,
                    "asset_id": "DRV-TEST-001",
                },
                "environmental": {
                    "state": "HIGH_TEMPERATURE",
                    "temperature_c": 34.0,
                    "zone_id": "ZONE-B",
                },
                "shared_scope": "ZONE",
                "shared_entity": "ZONE-B",
            },
            retrieved_evidence=EVIDENCE,
            task="Assess the correlated maintenance and environmental evidence.",
            domains=("MAINTENANCE", "ENVIRONMENTAL"),
        )
    )
    if result["grounding_status"] != "SUPPORTED":
        raise AssertionError("Expected SUPPORTED result.")
    joined = " ".join(
        [result["assessment"]]
        + result["supported_findings"]
        + result["limitations"]
    ).lower()
    if "does not establish" not in joined and "does not" not in joined:
        raise AssertionError("Correlation/causation boundary was not preserved.")
    print("PASS: Maintenance/environment correlation does not imply causation.")

    for invalid in ("CYBERSECURITY", "PHYSICAL_SECURITY", "SAFETY"):
        try:
            specialist.assess(
                SpecialistRequest(
                    incident_evidence={},
                    retrieved_evidence=[],
                    task="Invalid domain test.",
                    domains=(invalid,),
                )
            )
        except ValueError:
            pass
        else:
            raise AssertionError(f"Operations specialist accepted {invalid}.")
    print("PASS: Unsupported specialist domains rejected.")

    print("=" * 60)
    print("DC-GUARDIAN PHASE 3.3 OPERATIONS SPECIALIST CONTRACT PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
