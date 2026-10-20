"""
Load DC-GUARDIAN demo data into a fresh installation.

A freshly installed dashboard is empty. This loads a small, fixed set of demo
Evidence through the normal ingestion pipeline (the same path an operator's
uploads take), so a new user sees results, a correlated group and Decisions
straight away:

- ZONE-A, SRV-A1-02: an SSH brute-force burst (four public LogHub OpenSSH lines);
- ZONE-B, SRV-B1-01: two drives' SMART histories (synthetic);
- ZONE-B, SEN-B-01: two batches of room-sensor readings, one rising above 35 °C
  (synthetic).

No images are included (face photos are never committed); add camera images
yourself in Scenario Lab. Nothing is sent to OpenAI: OPENAI_API_KEY is
blanked for the run, so automatic specialist steps are reported as unavailable.

Run from the repository root with the main environment, Neo4j running and
.env configured (see docs/INSTALLATION_AND_USER_GUIDE.md):

    python demo_data/load_demo_data.py

Running it again is safe: files already ingested are skipped.
"""

from __future__ import annotations

import json
import os
import subprocess  # nosec B404: fixed interpreter and module paths only
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUTS = Path(__file__).resolve().parent / "inputs"
STATE = ROOT / "presentation" / "backend" / "data" / "demo_ingestion_state.sqlite3"
SOURCES = [
    {"kind": "ssh", "directory": str(INPUTS / "ssh"), "zone_id": "ZONE-A", "server_id": "SRV-A1-02"},
    {"kind": "maintenance", "directory": str(INPUTS / "smart"), "zone_id": "ZONE-B", "server_id": "SRV-B1-01"},
    {"kind": "environment", "directory": str(INPUTS / "sensors"), "zone_id": "ZONE-B", "sensor_id": "SEN-B-01"},
]


def main() -> int:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="dcg-demo-") as folder:
        config = Path(folder) / "demo_ingestion.json"
        config.write_text(json.dumps({"sources": SOURCES}, indent=2), encoding="utf-8")
        env = {**os.environ, "PYTHONPATH": str(ROOT), "OPENAI_API_KEY": "", "DCG_INVESTIGATOR_ENABLED": "0"}
        # A new database lacks some relationship types until events exist, so Neo4j logs
        # long "does not exist" notices for every correlation query; they are harmless here.
        runner = ("import logging, runpy, sys; "
                  "logging.getLogger('neo4j.notifications').setLevel(logging.ERROR); "
                  "sys.argv = ['continuous_ingestion'] + sys.argv[1:]; "
                  "runpy.run_module('presentation.backend.app.continuous_ingestion', run_name='__main__')")
        done = subprocess.run(  # nosec B603: fixed argv, no shell
            [sys.executable, "-c", runner, "--config", str(config), "--state", str(STATE)],
            cwd=str(ROOT), env=env, check=False)
    if done.returncode != 0:
        print("Demo data load failed. Check that Neo4j is running and .env is filled in "
              "(docs/INSTALLATION_AND_USER_GUIDE.md, Troubleshooting).")
        return done.returncode
    print("Demo data loaded. Start (or refresh) the dashboard and open the Monitoring Center.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
