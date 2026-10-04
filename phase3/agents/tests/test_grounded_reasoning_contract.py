"""Local contract tests for Phase 3.2 grounded reasoning."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from phase3.agents.grounded_reasoning import grounded_reason  # noqa: E402


EVIDENCE = [{
    "chunk_id": "TEST:chunk:1",
    "document_id": "TEST-DOC",
    "title": "Test approved guidance",
    "authority_type": "GOVERNMENT_GUIDANCE",
    "publisher": "Test Publisher",
    "version": "1",
    "pages": [1],
    "text": "Authorized access should be verified before entry.",
}]


class ValidFakeProvider:
    def reason(self, payload):
        return {
            "assessment": "Access authorization requires verification.",
            "supported_findings": [
                "The supplied evidence supports authorization verification."
            ],
            "recommended_considerations": [
                "Verify the observed person's current authorization."
            ],
            "evidence_sufficient": True,
            "citations": [{
                "chunk_id": "TEST:chunk:1",
                "document_id": "TEST-DOC",
            }],
            "limitations": [],
        }


class HallucinatedCitationProvider:
    def reason(self, payload):
        return {
            "assessment": "Unsupported.",
            "supported_findings": [],
            "recommended_considerations": [],
            "evidence_sufficient": True,
            "citations": [{
                "chunk_id": "INVENTED",
                "document_id": "INVENTED-DOC",
            }],
            "limitations": [],
        }


def main():
    result = grounded_reason(
        provider=ValidFakeProvider(),
        incident_evidence={"authorization": "UNAUTHORIZED"},
        retrieved_evidence=EVIDENCE,
        task="Assess the access concern.",
    )
    if not result["evidence_sufficient"]:
        raise AssertionError("Valid grounded result was rejected.")
    print("PASS: Valid grounded assessment.")

    try:
        grounded_reason(
            provider=HallucinatedCitationProvider(),
            incident_evidence={"authorization": "UNAUTHORIZED"},
            retrieved_evidence=EVIDENCE,
            task="Assess the access concern.",
        )
    except ValueError:
        print("PASS: Hallucinated citation rejected.")
    else:
        raise AssertionError("Hallucinated citation was accepted.")

    print("=" * 60)
    print("DC-GUARDIAN PHASE 3.2 GROUNDED REASONING CONTRACT PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
