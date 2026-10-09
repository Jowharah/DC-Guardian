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
