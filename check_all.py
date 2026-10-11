"""DC-GUARDIAN full project check: every layer, one command, one report.

    python check_all.py               run everything available
    python check_all.py --skip-live   do not call the running backend
    python check_all.py --only face   run checks whose name contains "face"

Writes logs/checks/<timestamp>/report.md (plus one .log per check) and copies
the report to logs/checks/latest.md. Exit code 1 if any check FAILS.

Safety: no check calls OpenAI. The live API check issues GET requests only,
never Investigator questions, evaluations or other writes (some GETs record
access-audit rows, as the dashboard does). Reasoning contracts write test
nodes to Neo4j and remove them afterwards (see reasoning/run_contract_tests.py).
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
def venv_python(name: str) -> Path:
    folder = ROOT / name
    return folder / "Scripts" / "python.exe" if os.name == "nt" else folder / "bin" / "python"


# The integrated environment when present (local Windows), else the current
# interpreter (CI or any other setup that installed requirements.txt).
MAIN_PY = venv_python(".venv-dc-guardian") if venv_python(".venv-dc-guardian").exists() else Path(sys.executable)
# Scripts that need a GPU-enabled PyTorch from their component environment.
COMPONENT_ENV = {
    "evidence/ppe_detection/tests/test_ppe_model_artifact.py": ".venv-ppe",
    "evidence/ppe_detection/tests/test_ppe_runtime_pipeline.py": ".venv-ppe",
    "evidence/ppe_detection/tests/test_ppe_final_test_artifact.py": ".venv-ppe",
    "evidence/predictive_maintenance/tests/test_gru_dataset.py": ".venv-gru",
}
# Scripts that need private/excluded local data, with the directory required.
FACE_ENROLLMENT = "evidence/face_recognition/models/employee_embeddings.npz"  # private biometric artifact
RAG_KNOWLEDGE = "response/rag/knowledge_base/chunks"  # rebuilt locally from public sources
NEEDS_DATA = {
    "evidence/face_recognition/tests/test_controlled_dataset.py": "evidence/face_recognition/data/controlled_faces",
    "evidence/face_recognition/tests/test_enrollment_artifact.py": FACE_ENROLLMENT,
    "evidence/face_recognition/tests/test_face_pipeline.py": FACE_ENROLLMENT,
    "evidence/ppe_detection/tests/test_sh17_dataset.py": "evidence/ppe_detection/data",
    "evidence/ppe_detection/tests/test_ppe_config.py": "evidence/ppe_detection/data/processed/sh17_yolo/dataset.yaml",
    "response/rag/verify_response_rag.py": RAG_KNOWLEDGE,
    "response/rag/tests/test_chunking.py": RAG_KNOWLEDGE,
    "response/rag/tests/test_parsing.py": RAG_KNOWLEDGE,
    "response/rag/tests/test_preprocessing.py": RAG_KNOWLEDGE,
    "response/rag/tests/test_retrieval_contract.py": RAG_KNOWLEDGE,
}


def python_for(rel: str) -> Path:
    env = COMPONENT_ENV.get(rel)
    return venv_python(env) if env else MAIN_PY


def script_checks() -> list[tuple[str, str, list[str], str | None]]:
    """(layer, name, command, skip_reason)."""
    checks = []

    def add(layer, rel):
        py = python_for(rel)
        reason = None
        if not py.exists():
            reason = f"environment {py.parent.parent.name} not found"
        elif rel in NEEDS_DATA and not (ROOT / NEEDS_DATA[rel]).exists():
            reason = f"local data {NEEDS_DATA[rel]} not present (excluded from Git)"
        checks.append((layer, rel, [str(py), rel], reason))

    add("Runtime", "verify_runtime.py")
    for rel in sorted(p.relative_to(ROOT).as_posix() for p in ROOT.glob("evidence/*/tests/test_*.py")):
        add("Evidence", rel)
    add("Reasoning", "reasoning/run_contract_tests.py")
    add("Reasoning", "reasoning/uncertainty/test_uncertainty_reasoning.py")
    add("Reasoning", "reasoning/uncertainty/labelling/test_labelling_pack.py")
    add("Response", "response/rag/verify_response_rag.py")
    for rel in sorted(p.relative_to(ROOT).as_posix() for p in ROOT.glob("response/*/tests/test_*.py")):
        add("Response", rel)
    for rel in ("integration/tests/test_decision_rules.py", "integration/tests/test_pipeline_contract.py",
                "integration/tests/test_service_contract.py", "integration/tests/test_real_ppe_face_reasoning.py"):
        add("Decision/Integration", rel)
    return checks


def run(command: list[str], cwd: Path, timeout: int) -> tuple[int, str, float]:
    env = {**os.environ, "PYTHONPATH": str(ROOT), "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1",
           # Never let a check reach the OpenAI provider.
           "DCG_INVESTIGATOR_ENABLED": "0"}
    start = time.perf_counter()
    try:
        result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=timeout)
        return result.returncode, result.stdout + result.stderr, time.perf_counter() - start
    except subprocess.TimeoutExpired as exc:
        return 124, f"TIMEOUT after {timeout}s\n{exc.stdout or ''}", time.perf_counter() - start
    except FileNotFoundError as exc:
        return 127, f"Command not found: {exc}", time.perf_counter() - start


def neo4j_reachable() -> str | None:
    code, out, _ = run([str(MAIN_PY), "-c",
                        "from reasoning.graph.ingest_event import create_driver as c; c().close()"], ROOT, 60)
    return None if code == 0 else "Neo4j not reachable (start Neo4j to run graph contracts)"


def summary_line(output: str) -> str:
    import re
    output = re.sub(r"\x1b\[[0-9;]*m", "", output)  # strip terminal colour codes
    noise = ("warning", "onednn", "tensorflow", "absl", "pip install", "deepface", "loading weights")
    all_lines = [l.strip() for l in output.splitlines() if l.strip() and not set(l.strip()) <= set("=-")]
    lines = [l for l in all_lines if not any(n in l.lower() for n in noise)]
    # Prefer an explicit result line (pytest totals, "PASSED", Vite's "built in"),
    # even when it mentions warnings.
    results = [l for l in all_lines if re.search(r"\d+ (passed|failed)|PASSED|FAILED|built in|Error", l)]
    chosen = results or lines
    return chosen[-1][:160] if chosen else ""


def live_api_check(log: list[str]) -> tuple[str, str]:
    """GET-only smoke test of the running backend with the local operator."""
    base = "http://127.0.0.1:8000"
    try:
        urllib.request.urlopen(base + "/api/v1/health", timeout=5)  # nosec B310: fixed local http URL
    except Exception:
        return "SKIP", "backend not running on 127.0.0.1:8000"
    sys.path.insert(0, str(ROOT))
    from presentation.backend.app.authentication import local_setting
    user, password = local_setting("DCG_LOCAL_USER"), local_setting("DCG_LOCAL_PASSWORD")
    if not (user and password):
        return "SKIP", "DCG_LOCAL_USER/DCG_LOCAL_PASSWORD not configured"
    token = base64.b64encode(f"{user}:{password}".encode()).decode()

    def get(path):
        request = urllib.request.Request(base + path, headers={"Authorization": "Basic " + token})
        start = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=60) as response:  # nosec B310: fixed local http URL
                body = response.read()
                status = response.status
        except urllib.error.HTTPError as exc:
            body, status = exc.read(), exc.code
        except Exception as exc:
            log.append(f"ERR  {path}: {type(exc).__name__}")
            return None, None
        elapsed = (time.perf_counter() - start) * 1000
        log.append(f"{status}  {elapsed:7.0f}ms  {path}")
        try:
            return status, json.loads(body)
        except ValueError:
            return status, None

    results = {}
    for path in ("/api/v1/health", "/api/v1/auth/me", "/api/v1/incidents", "/api/v1/events/standalone",
                 "/api/v1/ppe/observations", "/api/v1/face/observations", "/api/v1/ssh/published",
                 "/api/v1/maintenance/events", "/api/v1/environment/events", "/api/v1/operations/correlations",
                 "/api/v1/physical/image-correlations", "/api/v1/cyber/face-ssh/candidates",
                 "/api/v1/correlations/pairs", "/api/v1/correlations/unified", "/api/v1/evidence-reviews"):
        results[path] = get(path)
    # Per-item reads the dashboard performs (Investigator context: no model call).
    for group in (results["/api/v1/correlations/unified"][1] or []):
        for suffix in ("/review-decision", "/graph"):
            results[f"group{suffix}:{group['id']}"] = get(f"/api/v1/correlations/unified/{group['id']}{suffix}")
        results[f"ctx:{group['id']}"] = get(f"/api/v1/investigator/unified/{group['id']}/context")
    for pair in (results["/api/v1/correlations/pairs"][1] or [])[:20]:
        results[f"pair:{pair['id']}"] = get(f"/api/v1/investigator/pairs/{pair['id']}/context")
    feeds = {"ssh": ("/api/v1/ssh/published", "event_id"), "ppe": ("/api/v1/ppe/observations", "observation_id"),
             "face": ("/api/v1/face/observations", "observation_id"),
             "maintenance": ("/api/v1/maintenance/events", "event_id"),
             "environment": ("/api/v1/environment/events", "event_id")}
    for kind, (path, key) in feeds.items():
        for item in (results[path][1] or [])[:5]:
            results[f"{kind}:{item[key]}"] = get(f"/api/v1/investigator/evidence/{kind}/{item[key]}/context")
            results[f"review:{kind}:{item[key]}"] = get(f"/api/v1/evidence-reviews/{kind}/{item[key]}")
    statuses = [s for s, _ in results.values()]
    errors = sum(1 for s in statuses if s is None or s >= 500)
    expected_conflicts = sum(1 for s in statuses if s in (404, 409))
    detail = f"{len(statuses)} requests · {errors} server errors · {expected_conflicts} 404/409 (e.g. specialists not yet evaluated)"
    return ("FAIL" if errors else "PASS"), detail


def main() -> int:
    # Check output contains symbols such as ✓; never crash on a legacy console encoding.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--skip-live", action="store_true")
    parser.add_argument("--only", default="")
    args = parser.parse_args()

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = ROOT / "logs" / "checks" / stamp
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []

    def record(layer, name, status, seconds, detail, output=""):
        safe = name.replace("/", "_").replace(":", "_")
        (out_dir / f"{safe}.log").write_text(output, encoding="utf-8")
        rows.append((layer, name, status, seconds, detail))
        print(f"{status:<4} {seconds:7.1f}s  {layer:<20} {name}  {detail}", flush=True)

    neo4j_skip = neo4j_reachable()
    checks = script_checks()
    checks.append(("Presentation", "presentation backend tests (pytest)",
                   [str(MAIN_PY), "-m", "pytest", "presentation/backend/tests", "-q", "-p", "no:cacheprovider"], None))
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    if not npm:
        frontend_skip = "npm not found on PATH"
    elif not (ROOT / "presentation" / "frontend" / "node_modules").exists():
        frontend_skip = "frontend dependencies not installed (run npm ci in presentation/frontend)"
    else:
        frontend_skip = None
    checks.append(("Presentation", "frontend type-check + build (npm run build)",
                   [npm or "npm", "run", "build"], frontend_skip))
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    checks.append(("Presentation", "frontend browser tests (npx playwright test)",
                   [npx or "npx", "playwright", "test"], frontend_skip or (None if npx else "npx not found on PATH")))

    for layer, name, command, skip in checks:
        if args.only and args.only.lower() not in name.lower():
            continue
        if skip is None and name in ("reasoning/run_contract_tests.py", "integration/tests/test_real_ppe_face_reasoning.py"):
            skip = neo4j_skip
        if skip:
            record(layer, name, "SKIP", 0.0, skip)
            continue
        cwd = ROOT / "presentation" / "frontend" if name.startswith("frontend") else ROOT
        code, output, seconds = run(command, cwd, 1800)
        record(layer, name, "PASS" if code == 0 else "FAIL", seconds, summary_line(output), output)

    if not args.skip_live and (not args.only or "live" in args.only.lower()):
        log = []
        start = time.perf_counter()
        status, detail = live_api_check(log)
        record("Live API", "running backend GET smoke test", status, time.perf_counter() - start, detail, "\n".join(log))

    counts = {s: sum(1 for r in rows if r[2] == s) for s in ("PASS", "FAIL", "SKIP")}
    lines = [f"# DC-GUARDIAN full check · {stamp}", "",
             f"**{counts['PASS']} passed · {counts['FAIL']} failed · {counts['SKIP']} skipped**", "",
             "| Status | Layer | Check | Time | Detail |", "|---|---|---|---|---|"]
    lines += [f"| {s} | {l} | `{n}` | {t:.1f}s | {d.replace('|', '/')} |" for l, n, s, t, d in rows]
    lines += ["", "Per-check output: one `.log` file per check in this folder. Backend runtime logs: `logs/errors.log`, `logs/api_access.log`."]
    report = "\n".join(lines) + "\n"
    (out_dir / "report.md").write_text(report, encoding="utf-8")
    (ROOT / "logs" / "checks" / "latest.md").write_text(report, encoding="utf-8")
    if os.environ.get("GITHUB_ACTIONS"):
        # Readable on the run page without log access: one error annotation
        # per failed check, and the full report as the job summary.
        for layer, name, status, _, detail in rows:
            if status == "FAIL":
                tail = "; ".join((out_dir / (name.replace("/", "_").replace(":", "_") + ".log"))
                                 .read_text(encoding="utf-8").strip().splitlines()[-6:])
                print(f"::error title={layer}: {name}::{detail} | {tail}"[:3000].replace("\n", " "))
        summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary:
            with open(summary, "a", encoding="utf-8") as handle:
                handle.write(report)
    print(f"\n{counts['PASS']} passed, {counts['FAIL']} failed, {counts['SKIP']} skipped")
    print(f"Report: {out_dir.relative_to(ROOT) / 'report.md'}")
    return 1 if counts["FAIL"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
