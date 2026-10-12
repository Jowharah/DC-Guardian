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


import pytest  # noqa: E402

TASK = "Synthesize the validated specialist findings."


def test_valid_cross_domain_synthesis_is_accepted():
    result = cross_domain_synthesize(provider=SafeFakeSynthesizer(), findings=[CYBER, OPS], task=TASK)
    assert result["grounding_status"] == "SUPPORTED"


def test_unestablished_causal_claim_is_rejected():
    with pytest.raises(ValueError):
        cross_domain_synthesize(provider=UnsafeFakeSynthesizer(), findings=[CYBER, OPS], task=TASK)


def main():
    test_valid_cross_domain_synthesis_is_accepted()
    print("PASS: Valid cross-domain synthesis accepted.")
    test_unestablished_causal_claim_is_rejected()
    print("PASS: Unestablished causal claim rejected.")
    print("=" * 60)
    print("DC-GUARDIAN CROSS-DOMAIN SYNTHESIS CONTRACT PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
