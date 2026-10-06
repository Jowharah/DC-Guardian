"""Synthetic end-to-end Cybersecurity specialist demo."""

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
from phase3.agents.specialists.cybersecurity import CybersecuritySpecialist  # noqa: E402
from phase3.rag.knowledge_eligibility import evaluate_knowledge_eligibility  # noqa: E402
from phase3.rag.retrieve import retrieve_knowledge  # noqa: E402


INCIDENT = {
    "scenario_id": "SYNTHETIC-SSH-001",
    "domain": "CYBERSECURITY",
    "event_type": "SSH_ANOMALY_ASSESSMENT",
    "source": "CONTROLLED_SYNTHETIC_SCENARIO",
    "source_ip": "192.0.2.10",
    "target_server": "SRV-B1-01",
    "evidence_state": "HIGH_CONFIDENCE_ANOMALY",
    "detector_votes": 2,
    "detector_combination": ["RULE", "AUTOENCODER"],
    "explicit_security_signals": [],
    "behavioral_evidence": {
        "failed_login_count": 14,
        "invalid_user_count": 6,
        "unique_users": 6,
        "root_attempt_ratio": 0.71,
    },
    "evidence_boundary": (
        "The anomaly evidence does not establish successful authentication, "
        "host compromise, attacker identity, persistence, or impact."
    ),
}

QUERY = (
    "What approved cybersecurity incident-response guidance is relevant when "
    "SSH authentication behavior produces a high-confidence anomaly with "
    "repeated failures and username-enumeration-like activity?"
)


def main() -> None:
    load_dotenv(ROOT / ".env")

    routed = route_specialists([INCIDENT["domain"]])
    if routed != ["cybersecurity"]:
        raise RuntimeError(f"Unexpected specialist routing: {routed}")

    eligibility = evaluate_knowledge_eligibility(
        domains=["CYBERSECURITY"]
    )
    if not eligibility["eligible"]:
        raise RuntimeError("No approved active cybersecurity knowledge.")

    evidence = retrieve_knowledge(
        QUERY,
        domains=["CYBERSECURITY"],
        top_k=3,
        ranking="controlled",
        abstain=False,
    )
    if not evidence:
        raise RuntimeError("No approved cybersecurity evidence retrieved.")

    print("=" * 60)
    print("DC-GUARDIAN PHASE 3.3 CYBERSECURITY SPECIALIST DEMO")
    print("=" * 60)
    print(f"Scenario: {INCIDENT['scenario_id']}")
    print(f"Router:   {routed}")
    print("Retrieved evidence:")
    for item in evidence:
        print(
            f"  {item['rank']}. {item['document_id']} "
            f"score={item['score']:.4f} pages={item['pages']}"
        )

    specialist = CybersecuritySpecialist(OpenAIResponsesProvider())
    result = specialist.assess(
        SpecialistRequest(
            incident_evidence=INCIDENT,
            retrieved_evidence=evidence,
            task=(
                "Assess the SSH anomaly evidence and identify supported "
                "investigation or response considerations."
            ),
            domains=("CYBERSECURITY",),
        )
    )

    # Conservative deterministic postcondition for this controlled scenario.
    # The supplied evidence establishes anomaly signals, not compromise.
    combined = json.dumps(result, ensure_ascii=False).lower()
    forbidden_claims = (
        "srv-b1-01 was compromised",
        "srv-b1-01 is compromised",
        "server was compromised",
        "server is compromised",
        "this was a confirmed attack",
        "the incident was a confirmed attack",
        "the incident is a confirmed attack",
        "a successful compromise occurred",
        "the compromise was successful",
        "attacker gained access to srv-b1-01",
        "attacker obtained access to srv-b1-01",
    )
    matched_claims = [
        claim for claim in forbidden_claims if claim in combined
    ]
    if matched_claims:
        raise RuntimeError(
            "FAILED CYBER EVIDENCE BOUNDARY: specialist converted anomaly "
            "evidence into an unsupported confirmed attack/compromise claim: "
            + ", ".join(matched_claims)
        )

    print()
    print("Validated Cybersecurity assessment:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print()
    print("PASS: SSH anomaly/compromise evidence boundary preserved.")


if __name__ == "__main__":
    main()
