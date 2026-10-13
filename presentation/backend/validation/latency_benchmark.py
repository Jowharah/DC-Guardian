"""
End-to-end latency of the DC-GUARDIAN pipeline on the operator workstation.

Two sources, reported separately:

A. Controlled benchmark (this run). Every stage between an upload and the
   operator's screen, timed REPEATS times after one warm-up:
   1. Evidence: each upload endpoint with publish/retain off (validation and
      detector inference, including the component worker process), through the
      FastAPI app in-process against a temporary database.
   2. Reasoning: Neo4j connection, ingestion of a controlled SSH event and a
      controlled drive-risk event, and cross-domain correlation, in a
      SCENARIO-LATENCY-* scope that is removed afterwards (topology untouched).
   3. Decision: DCG-DECISION-v2 on a linked group.
   The dashboard then shows the result on its next refresh (every 5 s).
B. Observed use: per-route latency of successful requests in the backend
   access logs (logs/api_access.log*), written while the operator used the
   system, including the language-model calls that this benchmark never makes.

No OpenAI call is made: nothing is published, and the investigator is disabled.

    python presentation/backend/validation/latency_benchmark.py [--repeats N]

Writes results/latency_benchmark.{md,json}. Needs the local component
environments, the face enrollment and Neo4j; a missing piece is reported as
skipped, not guessed.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import statistics
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
for path in (PROJECT_ROOT, *(PROJECT_ROOT / "reasoning" / d for d in ("adapters", "topology", "graph", "correlation"))):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

RESULTS = Path(__file__).resolve().parent / "results"
LOGS = PROJECT_ROOT / "logs"
DASHBOARD_REFRESH_SECONDS = 5  # App.tsx feed refresh interval
FACE_IMAGE = PROJECT_ROOT / "evidence/face_recognition/data/controlled_faces/test_unknown/U001/U001_test_01.jpg"
PPE_IMAGE = PROJECT_ROOT / "evidence/ppe_detection/data/raw/SH17/images/pexels-photo-1028905.jpeg"  # SH17 test split, 2758 x 1839
SSH_LOG = PROJECT_ROOT / "evidence/ssh_anomaly/data/raw/OpenSSH_2k.log"


def summary(values: list[float]) -> dict:
    ordered = sorted(values)
    p95 = ordered[min(len(ordered) - 1, round(0.95 * (len(ordered) - 1)))]
    return {"n": len(values), "median_ms": round(statistics.median(values), 1), "p95_ms": round(p95, 1),
            "min_ms": round(ordered[0], 1), "max_ms": round(ordered[-1], 1)}


def timed(fn, repeats: int) -> list[float]:
    out = []
    for _ in range(repeats):
        start = time.perf_counter()
        fn()
        out.append((time.perf_counter() - start) * 1000)
    return out


# ------------------------------------------------------------------ A1 Evidence
def smart_csv() -> bytes:
    from evidence.predictive_maintenance.src.config import BASE_SMART_FEATURES
    lines = ["date,serial_number," + ",".join(BASE_SMART_FEATURES)]
    for day in range(30):
        values = [str(day * 3 if f == "smart_5_raw" else 40 if f == "smart_194_raw" else 1000 + day) for f in BASE_SMART_FEATURES]
        lines.append(f"2026-09-{day + 1:02d},DRV-LATENCY-CSV," + ",".join(values))
    return "\n".join(lines).encode()


def sensor_csv() -> bytes:
    rows = ["timestamp,temperature_c,humidity_pct"]
    rows += [f"2026-10-01T02:{m:02d}:00Z,{22 + (m % 5) * 0.4:.1f},{45 + m % 7}" for m in range(60)]
    return "\n".join(rows).encode()


def evidence_stage(repeats: int) -> dict:
    from fastapi.testclient import TestClient
    from presentation.backend.app.authentication import current_principal
    from presentation.backend.app.authorization import Principal
    from presentation.backend.app.custom_scenarios import topology_options
    from presentation.backend.app.main import app

    zone = next(z for z in topology_options() if z["zone_id"] == "ZONE-A")
    app.dependency_overrides[current_principal] = lambda: Principal(
        "latency-benchmark", frozenset({"administrator"}), frozenset({"ZONE-A", "ZONE-B", "ZONE-C"}))
    client = TestClient(app)
    cases = {
        "SSH log (OpenSSH_2k, 2,000 lines)": (
            SSH_LOG, lambda: client.post("/api/v1/ssh/validate-log",
                                         files={"log": ("input.log", SSH_LOG.read_bytes(), "text/plain")},
                                         data={"zone_id": "ZONE-A", "server_id": zone["servers"][0]})),
        "PPE image (YOLOv8n, 2758 x 1839)": (
            PPE_IMAGE, lambda: client.post("/api/v1/ppe/validate-image",
                                           files={"image": ("input.jpg", PPE_IMAGE.read_bytes(), "image/jpeg")})),
        "Face image (ArcFace)": (
            FACE_IMAGE, lambda: client.post("/api/v1/face/validate-image",
                                            files={"image": ("input.jpg", FACE_IMAGE.read_bytes(), "image/jpeg")})),
        "Drive SMART history (30 days, Temporal RF v2)": (
            None, lambda: client.post("/api/v1/maintenance/validate",
                                      files={"file": ("smart.csv", smart_csv(), "text/csv")},
                                      data={"zone_id": "ZONE-A", "server_id": zone["servers"][0], "publish": "false"})),
        "Sensor readings (60 rows, thresholds)": (
            None, lambda: client.post("/api/v1/environment/validate",
                                      files={"file": ("sensor.csv", sensor_csv(), "text/csv")},
                                      data={"zone_id": "ZONE-A", "sensor_id": zone["sensors"][0], "publish": "false"})),
    }
    results = {}
    try:
        for name, (needs, call) in cases.items():
            if needs is not None and not needs.exists():
                results[name] = {"skipped": "local input not present"}
            elif (status := call().status_code) != 200:  # also the warm-up
                results[name] = {"skipped": f"endpoint answered {status} (component environment or data missing?)"}
            else:
                results[name] = summary(timed(call, repeats))
            print(f"  {name}: {results[name]}")
    finally:
        app.dependency_overrides.pop(current_principal, None)
    return results


# ------------------------------------------------------------------ A2 Reasoning
SSH_ASSESSMENT = {
    "event_type": "ssh_behavior_assessment", "source_ip": "203.0.113.77",
    "window_start": "2000-12-17T02:25:00Z", "window_end": "2000-12-17T02:30:00Z",
    "anomaly_detected": True, "detector_votes": 2, "detector_combination": "RULE+AE", "confidence": "MEDIUM",
    "evidence_state": "HIGH_CONFIDENCE_ANOMALY", "explicit_security_signal": False,
    "security_signals": [], "security_signal_evidence": [],
    "rule": {"prediction": "ANOMALOUS", "anomalous": True, "suspicious": False, "score": 1,
             "triggered_rules": ["ROOT_TARGETING"], "evidence": ["Latency benchmark"]},
    "isolation_forest": {"prediction": "NORMAL", "anomalous": False, "anomaly_score": -0.10},
    "autoencoder": {"prediction": "ANOMALOUS", "anomalous": True, "reconstruction_error": 0.125,
                    "threshold": 0.0857589915394783},
    "evidence": {"failed_login_count": 6, "invalid_user_count": 0, "unique_users": 1, "failure_ratio": 1.0,
                 "root_attempt_ratio": 1.0, "breakin_warning_count": 0, "disconnect_count": 0,
                 "no_identification_count": 0, "successful_login_count": 0, "success_after_failures": 0},
}


def maintenance_assessment(serial: str) -> dict:
    return {"domain": "MAINTENANCE", "event_type": "STORAGE_FAILURE_RISK_ASSESSMENT",
            "model_name": "DC_Guardian_Temporal_RF_v2", "asset_type": "HARD_DRIVE", "serial_number": serial,
            "observation_timestamp": "2026-03-20T00:00:00Z", "assessment": "AT_RISK",
            "failure_probability": 0.714008, "operating_threshold": 0.45, "failure_horizon_days": 7,
            "evidence": {"smart_5_raw": 20.0, "smart_198_raw": 2.0, "smart_194_raw": 35.0, "smart_5_delta_7": 20.0,
                         "smart_198_delta_7": 2.0, "temperature_7obs_mean": 33.8571428571}}


def reasoning_stage(repeats: int) -> dict:
    from correlation_engine import find_cross_domain_correlations
    from graph_test_support import cleanup_graph
    from ingest_event import create_driver, ingest_maintenance_event, ingest_ssh_event
    from maintenance_event_adapter import adapt_maintenance_assessment
    from ssh_event_adapter import adapt_ssh_assessment
    from topology_mapper import map_maintenance_event_to_scenario, map_ssh_event_to_scenario

    try:
        probe = create_driver()
        probe.verify_connectivity()
        probe.close()
    except Exception as exc:  # noqa: BLE001 - reported, not guessed
        return {"skipped": f"Neo4j not reachable ({type(exc).__name__})"}

    timings = {"Neo4j connection (one per upload)": [], "Ingest SSH event": [],
               "Ingest drive-risk event": [], "Cross-domain correlation (scenario)": []}
    scenarios, assets = [], []
    correlated = 0
    try:
        for i in range(repeats + 1):
            scenario, serial = f"SCENARIO-LATENCY-{i:03d}", f"DRV-LATENCY-{i:03d}"
            scenarios.append(scenario); assets.append(serial)
            ssh = map_ssh_event_to_scenario(
                adapt_ssh_assessment(SSH_ASSESSMENT, dataset_name="DC-Guardian Latency Benchmark",
                                     source_type="CONTROLLED_TEST", event_id=f"EVT-LAT-SSH-{i:03d}"),
                scenario_id=scenario, scenario_timestamp="2026-09-18T12:00:00Z", target_name="ZONE_B_CRITICAL_SERVER")
            drive = map_maintenance_event_to_scenario(
                adapt_maintenance_assessment(maintenance_assessment(serial), dataset_name="DC-Guardian Latency Benchmark",
                                             source_type="CONTROLLED_TEST", event_id=f"EVT-LAT-MAINT-{i:03d}"),
                scenario_id=scenario, scenario_timestamp="2026-09-18T12:05:00Z", target_name="ZONE_B_CRITICAL_STORAGE")
            t0 = time.perf_counter()
            driver = create_driver()
            driver.verify_connectivity()
            t1 = time.perf_counter()
            try:
                ingest_ssh_event(ssh, driver)
                t2 = time.perf_counter()
                ingest_maintenance_event(drive, driver)
                t3 = time.perf_counter()
                found = find_cross_domain_correlations(driver, scenario_id=scenario, window_minutes=15)
                t4 = time.perf_counter()
            finally:
                driver.close()
            if i == 0:
                continue  # warm-up
            correlated += bool(found)
            for key, (a, b) in zip(timings, ((t0, t1), (t1, t2), (t2, t3), (t3, t4))):
                timings[key].append((b - a) * 1000)
    finally:
        driver = create_driver()
        try:
            cleanup_graph(driver, scenarios=scenarios, assets=assets, source_ips=[SSH_ASSESSMENT["source_ip"]])
        finally:
            driver.close()
    result = {k: summary(v) for k, v in timings.items()}
    result["_correlated_runs"] = f"{correlated} of {repeats}"
    print(f"  reasoning: {result}")
    return result


# ------------------------------------------------------------------ A3 Decision
def decision_stage(repeats: int) -> dict:
    from decision import rules_v2
    group = [{"domain": "CYBERSECURITY", "state": "HIGH_CONFIDENCE_ANOMALY", "timestamp": "2026-09-18T12:00:00+00:00",
              "server_id": "SRV-B1-01"},
             {"domain": "MAINTENANCE", "state": "AT_RISK", "timestamp": "2026-09-18T12:05:00+00:00",
              "server_id": "SRV-B1-01"}]
    per_call_us = []
    for _ in range(repeats):
        start = time.perf_counter()
        for _ in range(1000):
            rules_v2.decide_group(group)
        per_call_us.append((time.perf_counter() - start) * 1000)  # µs per call = ms per 1000 calls
    s = summary(per_call_us)
    return {"DCG-DECISION-v2 group decision (per call, µs)": {**s, "unit": "microseconds"}}


# ------------------------------------------------------------------ B Observed
LINE = re.compile(r"^(\S+ \S+) INFO dcg\.access: (GET|POST|PUT|DELETE|PATCH) (\S+) (\d{3}) (\d+)ms$")


def observed_stage() -> dict:
    from presentation.backend.app.main import app
    # OpenAPI path templates: stable across FastAPI versions (0.143 wraps included routers).
    routes = [(re.compile("^" + re.sub(r"\\\{[^/]+?\\\}", "[^/]+", re.escape(p)) + "$"), p)
              for p in app.openapi()["paths"] if p.startswith("/api/")]
    by_route: dict[str, list[float]] = {}
    first = last = None
    for log in sorted(LOGS.glob("api_access.log*")):
        for raw in log.read_text(encoding="utf-8", errors="replace").splitlines():
            m = LINE.match(raw)
            if not m or not m.group(4).startswith("2"):
                continue
            when, method, path = m.group(1), m.group(2), m.group(3).split("?")[0]
            template = next((p for rx, p in routes if rx.match(path)), None)
            if template is None:
                continue
            by_route.setdefault(f"{method} {template}", []).append(float(m.group(5)))
            first = min(first or when, when); last = max(last or when, when)
    return {"period": [first, last], "requests": sum(map(len, by_route.values())),
            "routes": {k: summary(v) for k, v in sorted(by_route.items())}}


# ------------------------------------------------------------------ report
KEY_ROUTES = {
    "GET /api/v1/correlations/unified": "Unified correlation feed (computed per request)",
    "GET /api/v1/correlations/pairs": "Pair correlation feed",
    "GET /api/v1/operations/correlations": "Operational correlation feed",
    "GET /api/v1/decisions/standalone": "Single-event Decisions (v2)",
    "GET /api/v1/correlations/unified/{group_id}/review-decision": "Group Decision (v2)",
    "GET /api/v1/correlations/unified/{group_id}/graph": "Group graph view",
    "POST /api/v1/correlations/unified/{group_id}/specialists": "Three specialists (OpenAI, RAG)",
    "POST /api/v1/evidence/{kind}/{evidence_id}/specialist": "Single-event specialist (OpenAI, RAG)",
    "POST /api/v1/investigator/evidence/{kind}/{evidence_id}/ask": "Investigator question, single event (OpenAI)",
    "POST /api/v1/investigator/unified/{group_id}/ask": "Investigator question, group (OpenAI)",
}


def row(name: str, s: dict) -> str:
    if "skipped" in s:
        return f"| {name} | – | – | – | skipped: {s['skipped']} |"
    return f"| {name} | {s['n']} | {s['median_ms']:,.1f} | {s['p95_ms']:,.1f} | max {s['max_ms']:,.1f} |"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=10)
    args = parser.parse_args()
    os.environ["DCG_INVESTIGATOR_ENABLED"] = "0"
    with tempfile.TemporaryDirectory(prefix="dcg-latency-") as folder:
        os.environ["DCG_PRESENTATION_DB"] = str(Path(folder) / "presentation.sqlite3")
        print("A1 Evidence"); evidence = evidence_stage(args.repeats)
        print("A2 Reasoning"); reasoning = reasoning_stage(args.repeats)
        print("A3 Decision"); decision = decision_stage(args.repeats)
    print("B Observed"); observed = observed_stage()

    def med(stage: dict, key: str) -> float:
        return stage.get(key, {}).get("median_ms", 0.0)

    graph_path = sum(med(reasoning, k) for k in ("Neo4j connection (one per upload)", "Ingest SSH event",
                                                  "Ingest drive-risk event", "Cross-domain correlation (scenario)"))
    feed = observed["routes"].get("GET /api/v1/correlations/unified", {}).get("median_ms", 0.0)
    ssh_total = med(evidence, "SSH log (OpenSSH_2k, 2,000 lines)") + graph_path + feed
    report = {"run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "repeats": args.repeats,
              "machine": "operator workstation (Windows 11, single user, uvicorn --reload for observed use)",
              "evidence": evidence, "reasoning": reasoning, "decision": decision, "observed": observed,
              "estimate_ssh_upload_to_dashboard_ms": {"processing_median": round(ssh_total, 1),
                                                      "plus_refresh_wait_up_to": DASHBOARD_REFRESH_SECONDS * 1000}}
    lines = ["# Pipeline latency", "",
             f"Generated by `presentation/backend/validation/latency_benchmark.py` on {report['run_at']} "
             f"({args.repeats} timed runs per stage after one warm-up), on the operator workstation. "
             "No OpenAI call is made by the benchmark; language-model latency comes from observed use (part B).", "",
             "## A. Controlled benchmark", "",
             "### Evidence: upload endpoint, validation and detector inference", "",
             "Each upload starts a fresh component worker process, so model loading is included in every call.", "",
             "| Upload | Runs | Median (ms) | p95 (ms) | Note |", "|---|---:|---:|---:|---|",
             *(row(k, v) for k, v in evidence.items()), "",
             "### Reasoning: Neo4j ingestion and correlation", "",
             "| Stage | Runs | Median (ms) | p95 (ms) | Note |", "|---|---:|---:|---:|---|"]
    if "skipped" in reasoning:
        lines.append(row("Neo4j stages", reasoning))
    else:
        lines += [row(k, v) for k, v in reasoning.items() if not k.startswith("_")]
        lines += ["", f"A correlation was found in {reasoning['_correlated_runs']} runs (controlled SSH and drive-risk "
                      "events on the same server, five minutes apart)."]
    lines += ["", "### Decision", "", "| Stage | Runs | Median (µs) | p95 (µs) | Note |", "|---|---:|---:|---:|---|",
              *(row(k, v) for k, v in decision.items()), "",
              "### Upload to dashboard (SSH example)", "",
              f"Median processing ≈ **{ssh_total / 1000:.1f} s**: SSH inference "
              f"{med(evidence, 'SSH log (OpenSSH_2k, 2,000 lines)') / 1000:.1f} s + graph and correlation "
              f"{graph_path / 1000:.2f} s + unified feed {feed / 1000:.2f} s (observed median). The dashboard refreshes "
              f"every {DASHBOARD_REFRESH_SECONDS} s, so the operator sees the result within about "
              f"{(ssh_total / 1000) + DASHBOARD_REFRESH_SECONDS:.0f} s. The publish path makes separate requests "
              "(publish, ingest, correlation check); their HTTP overhead is small next to inference.", "",
              "## B. Observed during use", "",
              f"{observed['requests']:,} successful requests from {observed['period'][0]} to {observed['period'][1]} "
              "(single user, development server with auto-reload).", "",
              "| Route | Purpose | Requests | Median (ms) | p95 (ms) | Max (ms) |", "|---|---|---:|---:|---:|---:|"]
    for route, purpose in KEY_ROUTES.items():
        s = observed["routes"].get(route)
        if s:
            lines.append(f"| `{route}` | {purpose} | {s['n']} | {s['median_ms']:,.0f} | {s['p95_ms']:,.0f} | {s['max_ms']:,.0f} |")
    lines += ["", "All routes are in `latency_benchmark.json`.", "",
              "## Caveats", "",
              "- One workstation, one user, small data: no concurrency or load test; production latency depends on hosting.",
              "- Inference runs in a new worker process per upload (isolation of the component environments); a "
              "long-running model service would remove most of the model-loading time.",
              "- Observed language-model latency depends on the provider and network at the time, and the specialist "
              "routes have few samples (each call needs operator consent).",
              "- The access logs rotate, so part B covers only the period shown.", ""]
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "latency_benchmark.md").write_text("\n".join(lines), encoding="utf-8")
    (RESULTS / "latency_benchmark.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Report: presentation/backend/validation/results/latency_benchmark.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
