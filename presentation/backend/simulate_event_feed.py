"""Controlled DC-GUARDIAN event generator. Run separately from FastAPI.

Uses only the existing allowlisted integration scenarios. The API and Neo4j
must be running. All results remain labeled synthetic, not live telemetry.
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4

SCENARIOS = ("ppe_face", "environmental_maintenance", "cyber_environmental_maintenance")
BASE_URL = "http://127.0.0.1:8000/api/v1"

def run_one(scenario: str) -> dict:
    run_id = f"DCG-{scenario.upper()}-{uuid4().hex[:12].upper()}"
    url = f"{BASE_URL}/scenarios/{scenario}/run?" + urlencode({"run_id": run_id})
    request = Request(url, method="POST")
    with urlopen(request, timeout=120) as response:
        return json.load(response)

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate controlled synthetic DC-GUARDIAN incidents")
    parser.add_argument("--interval", type=int, default=60, help="Seconds between runs (minimum 15)")
    parser.add_argument("--count", type=int, default=3, help="Number of runs; 0 means until Ctrl+C")
    args = parser.parse_args()
    if args.interval < 15 or args.count < 0:
        parser.error("interval must be at least 15 seconds and count cannot be negative")
    print("CONTROLLED SYNTHETIC FEED ONLY - not live monitoring")
    print(f"Started at {datetime.now(timezone.utc).isoformat()}")
    index = 0
    try:
        while args.count == 0 or index < args.count:
            scenario = SCENARIOS[index % len(SCENARIOS)]
            try:
                incident = run_one(scenario)
                print(f"PASS {incident['scenario_id']} severity={incident['decision']['severity']}", flush=True)
            except Exception as error:
                print(f"FAIL {scenario}: {type(error).__name__}: {error}", flush=True)
            index += 1
            if args.count == 0 or index < args.count:
                time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nStopped synthetic event generator.")

if __name__ == "__main__":
    main()
