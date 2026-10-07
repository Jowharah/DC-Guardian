"""CLI for the reusable DC-GUARDIAN integration backend."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from integration.scenario_registry import available_scenarios  # noqa: E402
from integration.service import run_integrated_scenario  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a controlled DC-GUARDIAN integrated scenario."
    )
    parser.add_argument(
        "scenario",
        choices=available_scenarios(),
    )
    parser.add_argument("--scenario-id")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the complete dashboard-ready PipelineResult.",
    )
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    result = run_integrated_scenario(
        args.scenario,
        scenario_id=args.scenario_id,
    )
    data = result.to_dict()

    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return

    print("=" * 60)
    print("DC-GUARDIAN INTEGRATED SCENARIO")
    print("EVIDENCE -> REASONING -> RESPONSE -> DECISION")
    print("=" * 60)
    print(f"Scenario: {args.scenario}")
    print(f"Scenario ID: {result.scenario_id}")
    print(f"Evidence events: {len(data['evidence']['events'])}")
    print(
        "Reasoning: "
        f"{data['reasoning']['shared_scope']}:"
        f"{data['reasoning']['shared_entity']}"
    )
    print(
        "Response specialists: "
        + ", ".join(data["response"]["specialists"])
    )
    print(
        "Grounding status: "
        + data["response"]["assessment"]["grounding_status"]
    )
    decision = data["decision"]
    print(
        "Decision: "
        f"{decision['incident_status']} | "
        f"severity={decision['severity']} | "
        f"mode={decision['response_mode']}"
    )
    print(
        "Escalation required: "
        + str(decision["escalation_required"])
    )
    print(
        "Autonomous action allowed: "
        + str(decision["autonomous_action_allowed"])
    )
    print("=" * 60)


if __name__ == "__main__":
    main()

