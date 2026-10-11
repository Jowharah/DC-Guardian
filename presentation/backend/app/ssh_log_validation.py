"""Protected SSH log upload and frozen-model validation; no raw log retention."""
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from presentation.backend.app.authentication import current_principal, authorize
from presentation.backend.app.authorization import Principal, Permission
from presentation.backend.app.custom_scenarios import topology_options
from presentation.backend.app.ssh_publication import save_preview

router = APIRouter()
MAX_LOG_BYTES = 1024 * 1024

@router.post("/api/v1/ssh/validate-log")
async def validate_ssh_log(
    log: UploadFile = File(...),
    zone_id: str = Form(...),
    server_id: str = Form(...),
    principal: Principal = Depends(current_principal),
):
    authorize(principal, Permission.SSH_DETAIL, zone_id)
    authorize(principal, Permission.SCENARIO_EXECUTE, zone_id)
    topology = next((z for z in topology_options() if z["zone_id"] == zone_id), None)
    if topology is None or server_id not in topology["servers"]:
        raise HTTPException(422, "Server does not belong to selected zone")
    try:
        raw = await log.read(MAX_LOG_BYTES + 1)
    finally:
        await log.close()
    if not raw or len(raw) > MAX_LOG_BYTES or bytes([0]) in raw:
        raise HTTPException(422, "OpenSSH text log must be between 1 byte and 1 MiB")
    root = Path(__file__).resolve().parents[3]
    with tempfile.TemporaryDirectory(prefix="dcg-ssh-") as folder:
        file = Path(folder) / "input.log"
        file.write_bytes(raw)
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "presentation.backend.app.ssh_worker", str(file)],
                cwd=str(root), capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=120, check=False,
                env={**os.environ, "PYTHONPATH": str(root), "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
            )
        except subprocess.TimeoutExpired as exc:
            raise HTTPException(504, "SSH_INFERENCE_TIMEOUT") from exc
        if proc.returncode:
            raise HTTPException(503, "SSH_INFERENCE_WORKER_FAILED")
        lines = [line[len("DCG_SSH_RESULT="):] for line in proc.stdout.splitlines()
                 if line.startswith("DCG_SSH_RESULT=")]
        if len(lines) != 1:
            raise HTTPException(503, "SSH_WORKER_OUTPUT_INVALID")
        try:
            result = json.loads(lines[0])
        except ValueError as exc:
            raise HTTPException(503, "SSH_WORKER_OUTPUT_INVALID") from exc
    preview_id = save_preview(principal.subject, zone_id, server_id, result["assessments"])
    return {**result, "preview_id": preview_id, "zone_id": zone_id, "server_id": server_id, "retained": False,
            "decision_severity": None}

@router.post("/api/v1/ssh/process-log")
async def process_ssh_log(
    log: UploadFile = File(...),
    zone_id: str = Form(...),
    server_id: str = Form(...),
    publish: bool = Form(True),
    principal: Principal = Depends(current_principal),
):
    """One request: real inference -> optional publication -> graph -> correlation -> Response -> Decision.

    Each assessment is processed independently. A partial failure is returned as
    an explicit stage error, not misrepresented as completed processing.
    """
    validated = await validate_ssh_log(log, zone_id, server_id, principal)
    validated["published"] = False
    validated["events"] = []
    if not publish or not validated["assessments"]:
        return validated

    from presentation.backend.app.ssh_publication import (
        PublishRequest, publish as publish_assessments,
        ingest_graph, check_correlation, standalone_decision,
    )
    indices = list(range(len(validated["assessments"])))
    published = publish_assessments(
        PublishRequest(preview_id=validated["preview_id"], indices=indices), principal)
    validated["published"] = True
    for index, event_id in zip(indices, published["published_event_ids"]):
        item = {"event_id": event_id, "assessment_index": index,
                "status": "PUBLISHED", "stages": [
                    {"stage": "EVIDENCE", "status": "COMPLETE"},
                    {"stage": "PRESENTATION", "status": "COMPLETE"}]}
        validated["events"].append(item)
        try:
            graph = ingest_graph(event_id, principal)
            item["graph_event_id"] = graph["graph_event_id"]
            item["stages"].append({"stage": "NEO4J", "status": "COMPLETE"})
        except HTTPException as exc:
            item["status"] = "PARTIAL"
            item["stages"].append({"stage": "NEO4J", "status": "FAILED",
                                    "detail": str(exc.detail)})
            continue
        try:
            correlation = check_correlation(event_id, principal)
            item["correlation"] = correlation
            item["stages"].append({"stage": "CORRELATION", "status": "COMPLETE",
                                    "detail": correlation["status"]})
        except HTTPException as exc:
            item["status"] = "PARTIAL"
            item["stages"].append({"stage": "CORRELATION", "status": "FAILED",
                                    "detail": str(exc.detail)})
            continue
        if correlation["status"] != "NO_CORRELATION":
            item["status"] = "CORRELATED_REVIEW_REQUIRED"
            item["stages"].append({"stage": "RESPONSE", "status": "NOT_RUN",
                                    "detail": "Multi-domain Response workflow required"})
            item["stages"].append({"stage": "DECISION", "status": "NOT_RUN",
                                    "detail": "Multi-domain Decision workflow required"})
            continue
        try:
            decision = standalone_decision(event_id, principal)
            item["decision"] = decision["decision"]
            item["specialist"] = decision["specialist"]
            item["status"] = "DECISION_COMPLETE"
            item["stages"].extend([
                {"stage": "RESPONSE", "status": "COMPLETE"},
                {"stage": "DECISION", "status": "COMPLETE"}])
        except HTTPException as exc:
            item["status"] = "PARTIAL"
            item["stages"].append({"stage": "RESPONSE_OR_DECISION",
                                    "status": "FAILED", "detail": str(exc.detail)})
    return validated
