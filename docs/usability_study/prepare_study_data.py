"""
Prepare identical, fresh dashboard data for each usability-study session.

Every participant must see the same dashboard: no verdicts, no group reviews,
no investigation progress, and the same two correlated groups. Verdicts and
lifecycle transitions are append-only by design, so the honest way back is a
clean slate followed by re-ingesting the same fixed inputs.

    # once: build the fixed study inputs (private folder, never committed)
    python docs/usability_study/prepare_study_data.py build-inputs
    # before every session, with the backend STOPPED and Neo4j running
    python docs/usability_study/prepare_study_data.py prepare

`prepare`:
1. refuses to run while the backend listens on port 8000 (the reset needs it stopped);
2. backs up the local data (presentation/backend/app/backup.py);
3. clears local test Evidence with the guarded reset tool (dev_reset.py: SQLite
   Evidence, verdicts, reviews, lifecycle, retained images, and the dashboard's
   Neo4j events; topology, people, access, enrollment and RAG are kept);
4. re-ingests the fixed study inputs with the normal ingestion pipeline
   (continuous_ingestion.py), with OPENAI_API_KEY empty so no specialist ever
   calls OpenAI, and the Investigator disabled;
5. declares the same controlled test time for the SSH event as the original
   demo (2026-10-10 07:10 UTC), so it correlates with the ZONE-A images;
6. checks the result against what the tasks need and prints the answer values.

Study inputs (private, in Documents/dcg-private/study_inputs):
- ZONE-A, the HIGH group: the face and PPE images originally uploaded through
  Scenario Lab (capture time 2026-10-10 07:10, camera CAM-A-01), and the four
  OpenSSH_2k.log lines of source IP 5.36.59.76 (Dec 10 07:13, LogHub), as SSH
  evidence on SRV-A1-02;
- ZONE-B, the LOW group: the existing incoming ingestion folders.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess  # nosec B404: fixed interpreter and module paths only
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PYTHON = ROOT / ".venv-dc-guardian" / "Scripts" / "python.exe"
PRIVATE = Path.home() / "Documents" / "dcg-private"
INCOMING = PRIVATE / "incoming"
STUDY = PRIVATE / "study_inputs"
CONFIG = STUDY / "study_ingestion.json"
STATE = PRIVATE / "study_ingestion_state.sqlite3"
BACKUPS = Path(os.environ.get("DCG_BACKUP_DIR", str(Path.home() / "Documents" / "DC-Guardian Backup"))) / "study_resets"
DATA = ROOT / "presentation" / "backend" / "data"
SSH_SOURCE = ROOT / "evidence" / "ssh_anomaly" / "data" / "raw" / "OpenSSH_2k.log"
SSH_IP = "5.36.59.76"
ZONE_A_TIME = "2026-10-10T07:10:00+00:00"
# A locked-test SH17 photo of a worker (2758 x 1839), not one of the ingested demo images.
PARTICIPANT_PPE_IMAGE = ROOT / "evidence" / "ppe_detection" / "data" / "raw" / "SH17" / "images" / "pexels-photo-1028905.jpeg"
ZONE_A_IMAGES = {"face": "FACE-IMG-E61F1226667E4E12BFB10D44C5633311.png",
                 "ppe": "PPE-IMG-96D70ABF66EE40669F8A9F99C8FC8013.png"}


def build_inputs() -> None:
    """Copy the original ZONE-A demo inputs into the private study folder (run before any reset)."""
    for kind, name in ZONE_A_IMAGES.items():
        source = DATA / f"{kind}_images" / name
        target_dir = STUDY / f"{kind}_zone_a"
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"study_{kind}_zone_a.png"
        if not target.exists():
            if not source.exists():
                raise SystemExit(f"Original image missing: {source}. Run build-inputs before any reset.")
            shutil.copy2(source, target)
        (target_dir / (target.name + ".metadata.json")).write_text(
            json.dumps({"camera_id": "CAM-A-01", "captured_at": ZONE_A_TIME.replace("+00:00", "Z")}, indent=2) + "\n",
            encoding="utf-8")
    ssh_dir = STUDY / "ssh_zone_a"
    ssh_dir.mkdir(parents=True, exist_ok=True)
    lines = [line for line in SSH_SOURCE.read_text(encoding="utf-8").splitlines() if SSH_IP in line]
    (ssh_dir / "study_ssh_zone_a.log").write_text("\n".join(lines) + "\n", encoding="utf-8")
    zone_b = json.loads((PRIVATE / "ingestion.json").read_text(encoding="utf-8"))["sources"]
    zone_a = [
        {"kind": "ssh", "directory": str(ssh_dir), "zone_id": "ZONE-A", "server_id": "SRV-A1-02"},
        {"kind": "ppe", "directory": str(STUDY / "ppe_zone_a"), "zone_id": "ZONE-A", "retain_approved_images": True},
        {"kind": "face", "directory": str(STUDY / "face_zone_a"), "zone_id": "ZONE-A", "retain_approved_images": True},
    ]
    CONFIG.write_text(json.dumps({"sources": zone_a + zone_b}, indent=2) + "\n", encoding="utf-8")
    # Files a participant uploads in Scenario Lab (tasks T9, T10). Their times are far from the
    # ZONE-A scenario (07:10), so an upload cannot join the HIGH group during a session.
    uploads = STUDY / "participant_uploads"
    uploads.mkdir(exist_ok=True)
    shutil.copy2(PARTICIPANT_PPE_IMAGE, uploads / "camera_snapshot.jpg")
    rows = ["timestamp,temperature_c,humidity_pct"]
    rows += [f"2026-10-10T13:{m:02d}:00Z,{24 + m * 1.4:.1f},{45 + m // 3}" for m in range(0, 11)]
    (uploads / "sensor_readings.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"Study inputs ready in {STUDY}: {len(lines)} SSH lines, 2 ZONE-A images, {len(zone_b)} ZONE-B sources, "
          f"participant uploads in {uploads}.")


def backend_running() -> bool:
    with socket.socket() as s:
        s.settimeout(1)
        return s.connect_ex(("127.0.0.1", 8000)) == 0


def run(args: list[str], extra_env: dict[str, str]) -> None:
    env = {**os.environ, "PYTHONPATH": str(ROOT), **extra_env}
    done = subprocess.run([str(PYTHON), *args], cwd=str(ROOT), env=env, check=False)  # nosec B603: fixed argv
    if done.returncode != 0:
        raise SystemExit(f"Step failed: {' '.join(args[:3])} (exit {done.returncode})")


def prepare() -> None:
    if not CONFIG.exists():
        raise SystemExit("Run build-inputs first.")
    if backend_running():
        raise SystemExit("Stop the backend first (close the backend window); the reset needs it stopped.")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe = {"OPENAI_API_KEY": "", "DCG_INVESTIGATOR_ENABLED": "0"}
    print("1/5 Backup"); run(["-m", "presentation.backend.app.backup", "create"], safe)
    if not STATE.exists():
        import sqlite3
        sqlite3.connect(STATE).close()
    print("2/5 Reset local test Evidence")
    run(["-m", "presentation.backend.app.dev_reset", "--state", str(STATE), "--execute",
         "--confirm", "RESET-LOCAL-TEST-EVIDENCE", "--backup-dir", str(BACKUPS / stamp)],
        {**safe, "DCG_ALLOW_LOCAL_TEST_RESET": "YES"})
    print("3/5 Ingest the fixed study inputs (no OpenAI calls)")
    run(["-m", "presentation.backend.app.continuous_ingestion", "--config", str(CONFIG), "--state", str(STATE)], safe)
    print("4/5 Declare the SSH controlled test time"); declare_and_check(safe)


def declare_and_check(safe: dict[str, str]) -> None:
    os.environ.update(safe)
    sys.path.insert(0, str(ROOT))
    from fastapi.testclient import TestClient
    from presentation.backend.app.authentication import current_principal
    from presentation.backend.app.continuous_ingestion import operator
    from presentation.backend.app.main import app
    app.dependency_overrides[current_principal] = operator
    client = TestClient(app)
    ssh = [e for e in client.get("/api/v1/ssh/published").json() if e.get("zone_id") == "ZONE-A"]
    if len(ssh) != 1:
        raise SystemExit(f"Expected one ZONE-A SSH event, found {len(ssh)}")
    response = client.put(f"/api/v1/ssh/published/{ssh[0]['event_id']}/controlled-time",
                          json={"observed_at": ZONE_A_TIME, "acknowledgment": True})
    if response.status_code != 200:
        raise SystemExit(f"Controlled time not accepted: {response.status_code} {response.text[:200]}")
    print("5/5 Check the dashboard state")
    groups = client.get("/api/v1/correlations/unified").json()
    ppe = client.get("/api/v1/ppe/observations").json()
    verdicts = client.get("/api/v1/evidence-reviews").json()
    report = {
        "groups": [{"id": g["id"], "severity": g.get("decision_severity"), "domains": g.get("domains"),
                    "zone": g.get("zone_id"),
                    "state": client.get(f"/api/v1/lifecycle/group/{g['id']}").json().get("state")} for g in groups],
        "ppe_observations": [{"id": o["observation_id"], "zone": o.get("zone_id"),
                              "status": (o.get("assessment") or {}).get("overall_status")} for o in ppe],
        "verdicts": len(verdicts),
    }
    app.dependency_overrides.pop(current_principal, None)
    print(json.dumps(report, indent=2))
    problems = []
    if not any(g["severity"] == "HIGH" for g in report["groups"]):
        problems.append("no HIGH group")
    if report["verdicts"]:
        problems.append("verdicts present")
    if not report["ppe_observations"]:
        problems.append("no PPE observation")
    print("READY for the session." if not problems else f"NOT READY: {', '.join(problems)}")


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if command == "build-inputs":
        build_inputs()
    elif command == "prepare":
        prepare()
    else:
        print(__doc__)
        sys.exit(2)
