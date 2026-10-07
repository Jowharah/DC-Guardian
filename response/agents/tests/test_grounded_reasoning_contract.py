"""Local contract tests for Grounded Reasoning grounded reasoning."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from response.agents.grounded_reasoning import grounded_reason  # noqa: E402


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
            "grounding_status": "SUPPORTED",
            "citations": [{
                "chunk_id": "TEST:chunk:1",
                "document_id": "TEST-DOC",
            }],
            "limitations": [],
        }




class PartialFakeProvider:
    def reason(self, payload):
        return {
            "assessment": "Authorization concern is supported, but entry outcome is unknown.",
            "supported_findings": [
                "The supplied evidence supports an authorization concern."
            ],
            "recommended_considerations": [
                "Verify whether physical entry was attempted or granted."
            ],
            "grounding_status": "PARTIALLY_SUPPORTED",
            "citations": [{
                "chunk_id": "TEST:chunk:1",
                "document_id": "TEST-DOC",
            }],
            "limitations": [
                "The supplied incident evidence does not establish whether entry occurred."
            ],
        }


class InsufficientFakeProvider:
    def reason(self, payload):
        return {
            "assessment": "The requested conclusion is not supported.",
            "supported_findings": [],
            "recommended_considerations": [],
            "grounding_status": "INSUFFICIENT",
            "citations": [],
            "limitations": [
                "No approved retrieved evidence supports the requested conclusion."
            ],
        }


class HallucinatedCitationProvider:
    def reason(self, payload):
        return {
            "assessment": "Unsupported.",
            "supported_findings": [],
            "recommended_considerations": [],
            "grounding_status": "SUPPORTED",
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
    if result["grounding_status"] != "SUPPORTED":
        raise AssertionError("Valid grounded result was rejected.")
    print("PASS: Valid grounded assessment.")

    partial = grounded_reason(
        provider=PartialFakeProvider(),
        incident_evidence={"authorization": "UNAUTHORIZED"},
        retrieved_evidence=EVIDENCE,
        task="Assess the access concern.",
    )
    if partial["grounding_status"] != "PARTIALLY_SUPPORTED":
        raise AssertionError("Partial grounding status failed.")
    print("PASS: Partially supported assessment.")

    insufficient = grounded_reason(
        provider=InsufficientFakeProvider(),
        incident_evidence={"authorization": "UNKNOWN"},
        retrieved_evidence=[],
        task="Determine unsupported internal policy.",
    )
    if insufficient["grounding_status"] != "INSUFFICIENT":
        raise AssertionError("Insufficient grounding status failed.")
    print("PASS: Insufficient assessment.")

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
    print("DC-GUARDIAN GROUNDED REASONING GROUNDED REASONING CONTRACT PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()

