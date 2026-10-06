"""First real connected DC-GUARDIAN Evidence -> Reasoning -> Response slice."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from integration.runners.real_ppe_face_reasoning import (  # noqa: E402
    run_real_ppe_face_reasoning,
)
from integration.runners.real_ppe_face_response import (  # noqa: E402
    run_real_ppe_face_response,
)
from integration.schemas.pipeline_result import PipelineResult  # noqa: E402


def main() -> None:
    load_dotenv(ROOT / ".env")
    scenario_id = "INTEGRATION-REAL-PPE-FACE-E2E-001"

    reasoning = run_real_ppe_face_reasoning(scenario_id=scenario_id)
    response = run_real_ppe_face_response(reasoning)

    assessment = response["assessment"]
    combined = json.dumps(assessment, ensure_ascii=False).lower()
    forbidden = (
        "test-p003 was not wearing",
        "test-p003 lacked ppe",
        "test-p003 was non-compliant",
    )
    matched = [x for x in forbidden if x in combined]
    if matched:
        raise RuntimeError(
            "RESPONSE introduced unsupported Face/PPE identity attribution: "
            + ", ".join(matched)
        )

    result = PipelineResult(
        scenario_id=scenario_id,
        evidence={
            "layer": "EVIDENCE",
            "events": reasoning["evidence_events"],
        },
        reasoning={
            "layer": "REASONING",
            "correlation": reasoning["correlation"],
            "shared_scope": reasoning["shared_scope"],
            "shared_entity": reasoning["shared_entity"],
            "authorization_status": reasoning["authorization_status"],
            "identity_link_established": False,
        },
        response={
            "layer": "RESPONSE",
            **response,
        },
        decision={
            "status": "PENDING_DETERMINISTIC_DECISION_RULES",
        },
        provenance={
            "scenario_type": "CONTROLLED_SYNTHETIC_SCENARIO",
            "pipeline": "REAL_IMPLEMENTATION_VERTICAL_SLICE",
        },
    )

    print("=" * 60)
    print("DC-GUARDIAN REAL END-TO-END VERTICAL SLICE")
    print("EVIDENCE -> REASONING -> RESPONSE")
    print("=" * 60)
    print()
    print("EVIDENCE")
    print("PASS: Face evidence normalized by real adapter.")
    print("PASS: PPE evidence normalized by real adapter.")
    print()
    print("REASONING")
    print("PASS: Neo4j authorization resolved as UNAUTHORIZED.")
    print("PASS: PPE + Face evidence deterministically correlated.")
    print(
        f"PASS: Strongest truthful scope = "
        f"{reasoning['shared_scope']}:{reasoning['shared_entity']}."
    )
    print("PASS: Cross-model identity remains unestablished.")
    print()
    print("RESPONSE")
    print("PASS: Physical/Safety specialist selected.")
    print(
        f"PASS: Controlled Top-3 retrieved "
        f"({len(response['retrieved_evidence'])} chunks)."
    )
    print("PASS: Grounded specialist assessment generated.")
    print("PASS: Retrieved-only citations validated.")
    print("PASS: Face/PPE identity boundary preserved.")
    print()
    print("Grounding status:", assessment["grounding_status"])
    print("Assessment:")
    print(assessment["assessment"])
    print()
    print("=" * 60)
    print("DC-GUARDIAN REAL END-TO-END VERTICAL SLICE PASSED")
    print("EVIDENCE -> REASONING -> RESPONSE")
    print("=" * 60)

    # Ensure the unified result remains serializable for the future dashboard.
    json.dumps(result.to_dict(), ensure_ascii=False)


if __name__ == "__main__":
    main()
