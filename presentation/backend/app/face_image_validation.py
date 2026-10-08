"""Authenticated, local-only face image inference and opt-in retention."""
from pathlib import Path
import json
import logging
import os
import subprocess
import tempfile
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Response
from presentation.backend.app.authentication import current_principal, authorize
from presentation.backend.app.authorization import Principal, Permission
from presentation.backend.app.ppe_image_validation import MAX_IMAGE_BYTES, validate_image
from presentation.backend.app import face_observations

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/api/v1/face/validate-image")
async def validate_face(image: UploadFile = File(...), retain: bool = Form(False),
                        zone_id: str | None = Form(None),
                        principal: Principal = Depends(current_principal)):
    authorize(principal, Permission.PERSON_DETAIL)
    if retain:
        if not zone_id:
            raise HTTPException(422, "Zone required to retain an image")
        authorize(principal, Permission.PERSON_DETAIL, zone_id)
    if image.content_type not in ("image/jpeg", "image/png"):
        raise HTTPException(415, "JPEG or PNG required")
    try:
        decoded = validate_image(await image.read(MAX_IMAGE_BYTES + 1))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    finally:
        await image.close()
    project_root = Path(__file__).resolve().parents[3]
    worker = Path(__file__).with_name("face_worker.py")
    enrollment = project_root / "evidence/face_recognition/models/employee_embeddings.npz"
    if not enrollment.is_file():
        raise HTTPException(503, "FACE_ENROLLMENT_MISSING")
    face_python = project_root / ".venv-face" / "Scripts" / "python.exe"
    if not face_python.is_file():
        raise HTTPException(503, "FACE_ENVIRONMENT_MISSING")
    with tempfile.TemporaryDirectory(prefix="dcg-face-") as folder:
        path = Path(folder) / "input.png"
        decoded.save(path, format="PNG")
        try:
            run = subprocess.run(
                [
                    str(face_python),
                    "-m",
                    "presentation.backend.app.face_worker",
                    str(path),
                ],
                cwd=str(project_root),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,
                check=False,
                env={
                    **os.environ,
                    "PYTHONPATH": str(project_root),
                    "PYTHONIOENCODING": "utf-8",
                    "PYTHONUTF8": "1",
                },
            )
        except subprocess.TimeoutExpired as exc:
            raise HTTPException(504, "FACE_INFERENCE_TIMEOUT") from exc
        if run.returncode:
            # Avoid recording raw stderr: model libraries may print private paths.
            logger.error("Face inference worker failed (exit code %d)", run.returncode)
            raise HTTPException(503, "FACE_INFERENCE_WORKER_FAILED")
        lines = [x.removeprefix("DCG_FACE_RESULT=") for x in run.stdout.splitlines()
                 if x.startswith("DCG_FACE_RESULT=")]
        if len(lines) != 1:
            raise HTTPException(503, "FACE_WORKER_OUTPUT_INVALID")
        try:
            assessment = json.loads(lines[0])
        except (ValueError, TypeError) as exc:
            raise HTTPException(503, "FACE_WORKER_OUTPUT_INVALID") from exc
    if assessment.get("recognition_status") not in {"RECOGNIZED", "UNKNOWN", "NO_FACE", "MULTIPLE_FACES"}:
        raise HTTPException(503, "FACE_WORKER_OUTPUT_INVALID")
    observation = face_observations.save(decoded, assessment, zone_id, principal.subject) if retain and zone_id else None
    return {"assessment": assessment, "observation": observation, "image_stored": observation is not None,
            "pipeline_status": "FACE_ONLY_NOT_INTEGRATED", "authorization_status": "NOT_EVALUATED"}

@router.get("/api/v1/face/observations")
def list_face(principal: Principal = Depends(current_principal)):
    authorize(principal, Permission.PERSON_DETAIL)
    return face_observations.list_items(principal.zones)

@router.get("/api/v1/face/observations/{oid}")
def face_detail(oid: str, principal: Principal = Depends(current_principal)):
    authorize(principal, Permission.PERSON_DETAIL)
    item = face_observations.get(oid)
    if item is None:
        raise HTTPException(404, "Observation not found")
    authorize(principal, Permission.PERSON_DETAIL, item["zone_id"])
    return item

@router.get("/api/v1/face/observations/{oid}/image")
def face_image(oid: str, principal: Principal = Depends(current_principal)):
    authorize(principal, Permission.PERSON_DETAIL)
    item = face_observations.get(oid)
    if item is None:
        raise HTTPException(404, "Observation not found")
    authorize(principal, Permission.PERSON_DETAIL, item["zone_id"])
    try:
        data = face_observations.image_bytes(oid, principal.subject)
    except FileNotFoundError as exc:
        raise HTTPException(404, "Image unavailable") from exc
    return Response(data, media_type="image/png", headers={"Cache-Control":"no-store", "X-Content-Type-Options":"nosniff"})
