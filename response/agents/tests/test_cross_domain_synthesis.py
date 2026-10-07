"""Local contract for cross-domain synthesis."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from response.agents.schemas.specialist_finding import (  # noqa: E402
    EvidenceBoundaryClaims,
    SpecialistFinding,
)
from response.agents.synthesis.cross_domain import cross_domain_synthesize  # noqa: E402


def finding(specialist_id, domains, citation):
    return SpecialistFinding(
        specialist_id=specialist_id,
        domains=tuple(domains),
        assessment="Validated specialist assessment.",
        supported_findings=("Supported specialist finding.",),
        recommended_considerations=("Review evidence.",),
        grounding_status="SUPPORTED",
        citations=(citation,),
        limitations=("Known limitation.",),
        boundary_claims=EvidenceBoundaryClaims(),
    )


CYBER = finding(
    "cybersecurity",
    ["CYBERSECURITY"],
    ("NIST:1", "NIST-SP-800-61R3"),
)
OPS = finding(
    "operations",
    ["MAINTENANCE", "ENVIRONMENTAL"],
    ("DOE:1", "DOE-FEMP-OM-BEST-PRACTICES"),
)


class SafeFakeSynthesizer:
    def synthesize(self, payload):
        return {
            "assessment": (
                "Cybersecurity and operations findings affect related context "
                "and warrant coordinated review without establishing causation."
            ),
            "contributing_specialists": ["cybersecurity", "operations"],
            "supported_cross_domain_findings": [
                "Both validated specialist findings are relevant to the incident context."
            ],
            "recommended_considerations": [
                "Review cyber and operational evidence together while preserving boundaries."
            ],
            "grounding_status": "SUPPORTED",
            "citations": [
                {"chunk_id": "NIST:1", "document_id": "NIST-SP-800-61R3"},
                {"chunk_id": "DOE:1", "document_id": "DOE-FEMP-OM-BEST-PRACTICES"},
            ],
            "limitations": [
                "No compromise, causal relationship, or root cause is established."
            ],
            "boundary_claims": {
                "identity_link_established": False,
                "confirmed_compromise": False,
                "causal_relationship_established": False,
                "root_cause_established": False,
            },
        }


class UnsafeFakeSynthesizer(SafeFakeSynthesizer):
    def synthesize(self, payload):
        result = super().synthesize(payload)
        result["boundary_claims"]["causal_relationship_established"] = True
        return result


def main():
    result = cross_domain_synthesize(
        provider=SafeFakeSynthesizer(),
        findings=[CYBER, OPS],
        task="Synthesize the validated specialist findings.",
    )
    if result["grounding_status"] != "SUPPORTED":
        raise AssertionError("Safe synthesis was rejected.")
    print("PASS: Valid cross-domain synthesis accepted.")

    try:
        cross_domain_synthesize(
            provider=UnsafeFakeSynthesizer(),
            findings=[CYBER, OPS],
            task="Synthesize the validated specialist findings.",
        )
    except ValueError:
        print("PASS: Unestablished causal claim rejected.")
    else:
        raise AssertionError("Unsafe causal promotion was accepted.")

    print("=" * 60)
    print("DC-GUARDIAN CROSS-DOMAIN SYNTHESIS CONTRACT PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()

