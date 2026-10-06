"""Scenario registry for the reusable DC-GUARDIAN integration backend."""

from __future__ import annotations

from integration.runners.real_ppe_face_reasoning import run_real_ppe_face_reasoning
from integration.runners.real_ppe_face_response import run_real_ppe_face_response


SCENARIOS = {
    "ppe_face": {
        "description": "Controlled PPE non-compliance + unauthorized Face evidence.",
        "reasoning_runner": run_real_ppe_face_reasoning,
        "response_runner": run_real_ppe_face_response,
    },
}


def available_scenarios() -> list[str]:
    return sorted(SCENARIOS)


def get_scenario(name: str) -> dict:
    try:
        return SCENARIOS[name]
    except KeyError as exc:
        raise ValueError(
            f"Unknown scenario '{name}'. Available: {available_scenarios()}"
        ) from exc
