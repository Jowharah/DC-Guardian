"""Run one synthetic end-to-end DC-GUARDIAN grounded reasoning demo.

This sends only synthetic incident evidence plus locally retrieved approved
knowledge to the configured OpenAI model.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from response.agents.grounded_reasoning import grounded_reason  # noqa: E402
from response.agents.providers.openai_provider import OpenAIResponsesProvider  # noqa: E402
from response.rag.knowledge_eligibility import evaluate_knowledge_eligibility  # noqa: E402
from response.rag.retrieve import retrieve_knowledge  # noqa: E402


INCIDENT = {
    "event_type": "PHYSICAL_ACCESS",
    "subject_id": "TEST-EMPLOYEE",
    "zone": "ZONE-B",
    "identity_status": "RECOGNIZED",
    "authorization_status": "UNAUTHORIZED",
    "source": "SYNTHETIC_RESPONSE_TEST",
}

TASK = (
    "Assess the operational significance of the synthetic unauthorized "
    "physical-access observation. Identify only considerations supported by "
    "the supplied approved knowledge. Do not assign final severity or claim "
    "DC-GUARDIAN internal policy that is not supplied."
)


def main() -> None:
    load_dotenv(ROOT / ".env")

    eligibility = evaluate_knowledge_eligibility(
        domains=["PHYSICAL_SECURITY"]
    )
    if not eligibility["eligible"]:
        print(json.dumps(eligibility, indent=2))
        raise SystemExit(2)

    evidence = retrieve_knowledge(
        "recognized person is not authorized for the observed physical zone",
        domains=["PHYSICAL_SECURITY"],
        top_k=3,
        ranking="controlled",
        abstain=False,
    )

    if not evidence:
        raise RuntimeError("No approved physical-security evidence retrieved.")

    print("=" * 60)
    print("DC-GUARDIAN GROUNDED REASONING GROUNDED REASONING DEMO")
    print("=" * 60)
    print("Incident: SYNTHETIC_RESPONSE_TEST")
    print("Knowledge eligibility: ELIGIBLE")
    print("Retrieved evidence:")
    for item in evidence:
        print(
            f"  {item['rank']}. {item['document_id']} "
            f"score={item['score']:.4f} pages={item['pages']}"
        )

    provider = OpenAIResponsesProvider()
    assessment = grounded_reason(
        provider=provider,
        incident_evidence=INCIDENT,
        retrieved_evidence=evidence,
        task=TASK,
    )

    print()
    print("Validated grounded assessment:")
    print(json.dumps(assessment, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()


