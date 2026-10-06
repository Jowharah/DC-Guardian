"""Local contracts for the Phase 3.3 Cybersecurity specialist."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from phase3.agents.specialists.base import SpecialistRequest  # noqa: E402
from phase3.agents.specialists.cybersecurity import CybersecuritySpecialist  # noqa: E402


EVIDENCE = [{
    "chunk_id": "NIST:IR:1",
    "document_id": "NIST-SP-800-61R3",
    "title": "NIST SP 800-61 Rev. 3",
    "authority_type": "GOVERNMENT_GUIDANCE",
    "publisher": "NIST",
    "version": "Rev. 3",
    "pages": [20],
    "text": "Incident response includes analysis and actions based on available evidence.",
}]


class SafeCyberProvider:
    def reason(self, payload):
        task = payload["task"]
        required = (
            "not proof of a confirmed attack",
            "must not be called malicious activity",
            "does not by itself prove compromise",
        )
        if not all(item in task for item in required):
            raise AssertionError("Cybersecurity evidence-boundary instructions missing.")
        return {
            "assessment": (
                "The supplied SSH evidence is a high-confidence anomaly signal, "
                "not proof of confirmed compromise."
            ),
            "supported_findings": [
                "Multiple frozen detector components voted anomalous."
            ],
            "recommended_considerations": [
                "Review the supporting authentication evidence and affected asset context."
            ],
            "grounding_status": "SUPPORTED",
            "citations": [{
                "chunk_id": "NIST:IR:1",
                "document_id": "NIST-SP-800-61R3",
            }],
            "limitations": [
                "The supplied evidence does not establish successful compromise or attacker identity."
            ],
        }


def main():
    specialist = CybersecuritySpecialist(SafeCyberProvider())
    result = specialist.assess(
        SpecialistRequest(
            incident_evidence={
                "domain": "CYBERSECURITY",
                "event_type": "SSH_ANOMALY_ASSESSMENT",
                "evidence_state": "HIGH_CONFIDENCE_ANOMALY",
                "detector_votes": 2,
                "source_ip": "192.0.2.10",
                "target_server": "SRV-B1-01",
            },
            retrieved_evidence=EVIDENCE,
            task="Assess the SSH security evidence.",
            domains=("CYBERSECURITY",),
        )
    )
    if result["grounding_status"] != "SUPPORTED":
        raise AssertionError("Expected SUPPORTED result.")
    text = " ".join(
        [result["assessment"]]
        + result["supported_findings"]
        + result["limitations"]
    ).lower()
    if "not proof" not in text and "does not establish" not in text:
        raise AssertionError("Attack/compromise boundary was not preserved.")
    print("PASS: SSH anomaly remains evidence, not a confirmed attack.")

    try:
        specialist.assess(
            SpecialistRequest(
                incident_evidence={},
                retrieved_evidence=[],
                task="Invalid domain test.",
                domains=("MAINTENANCE",),
            )
        )
    except ValueError:
        print("PASS: Unsupported specialist domain rejected.")
    else:
        raise AssertionError("Cybersecurity specialist accepted MAINTENANCE.")

    print("=" * 60)
    print("DC-GUARDIAN PHASE 3.3 CYBERSECURITY SPECIALIST CONTRACT PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
