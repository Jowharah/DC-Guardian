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


import pytest  # noqa: E402


def run(provider, incident, evidence, task):
    return grounded_reason(provider=provider, incident_evidence=incident, retrieved_evidence=evidence, task=task)


def test_valid_grounded_assessment_is_accepted():
    result = run(ValidFakeProvider(), {"authorization": "UNAUTHORIZED"}, EVIDENCE, "Assess the access concern.")
    assert result["grounding_status"] == "SUPPORTED"


def test_partially_supported_assessment_is_accepted():
    result = run(PartialFakeProvider(), {"authorization": "UNAUTHORIZED"}, EVIDENCE, "Assess the access concern.")
    assert result["grounding_status"] == "PARTIALLY_SUPPORTED"


def test_insufficient_assessment_is_accepted():
    result = run(InsufficientFakeProvider(), {"authorization": "UNKNOWN"}, [], "Determine unsupported internal policy.")
    assert result["grounding_status"] == "INSUFFICIENT"


def test_hallucinated_citation_is_rejected():
    with pytest.raises(ValueError):
        run(HallucinatedCitationProvider(), {"authorization": "UNAUTHORIZED"}, EVIDENCE, "Assess the access concern.")


def main():
    test_valid_grounded_assessment_is_accepted()
    print("PASS: Valid grounded assessment.")
    test_partially_supported_assessment_is_accepted()
    print("PASS: Partially supported assessment.")
    test_insufficient_assessment_is_accepted()
    print("PASS: Insufficient assessment.")
    test_hallucinated_citation_is_rejected()
    print("PASS: Hallucinated citation rejected.")
    print("=" * 60)
    print("DC-GUARDIAN GROUNDED REASONING GROUNDED REASONING CONTRACT PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
