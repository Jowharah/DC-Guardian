"""Local PPE image validation against the frozen runtime (not an integrated incident).

No source images are persisted by this endpoint. The endpoint validates decoded
image bytes before running the unchanged frozen model. CUDA is required by that model.
"""
from io import BytesIO
import json
import os
import subprocess
import tempfile
from pathlib import Path
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError
from presentation.backend.app.authentication import current_principal, authorize
from presentation.backend.app.authorization import Principal, Permission

router = APIRouter()
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_PIXELS = 16_000_000
ALLOWED_FORMATS = {"JPEG", "PNG"}

def validate_image(data: bytes) -> Image.Image:
    if not data or len(data) > MAX_IMAGE_BYTES:
        raise ValueError("Image must be between 1 byte and 8 MiB")
    try:
        with Image.open(BytesIO(data)) as image:
            if image.format not in ALLOWED_FORMATS:
                raise ValueError("Only JPEG and PNG images are supported")
            if image.width * image.height > MAX_PIXELS:
                raise ValueError("Image dimensions exceed the allowed limit")
            image.load()
            return image.convert("RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError("Invalid or unsafe image") from exc

@router.post("/api/v1/ppe/validate-image")
async def validate_ppe_image(
    image: UploadFile = File(...),
    principal: Principal = Depends(current_principal),
) -> dict:
    # Local-only validation: no identity matching and no zone claim.
    authorize(principal, Permission.CAMERA_DETAIL)
    if image.content_type not in {"image/jpeg", "image/png"}:
        raise HTTPException(status_code=415, detail="JPEG or PNG required")
    try:
        data = await image.read(MAX_IMAGE_BYTES + 1)
        decoded = validate_image(data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        await image.close()
    project_root = Path(__file__).resolve().parents[3]
    python_executable = project_root / ".venv-ppe" / "Scripts" / "python.exe"
    worker = Path(__file__).with_name("ppe_worker.py")
    if not python_executable.is_file():
        raise HTTPException(status_code=503, detail="PPE_GPU_ENVIRONMENT_MISSING")
    if not worker.is_file():
        raise HTTPException(status_code=503, detail="PPE_WORKER_MISSING")
    # The uploaded image is decoded and rewritten to a controlled temporary PNG.
    # No client-supplied filename or command is passed to the subprocess.
    with tempfile.TemporaryDirectory(prefix="dcg-ppe-") as temp_dir:
        image_path = Path(temp_dir) / "input.png"
        decoded.save(image_path, format="PNG")
        try:
            completed = subprocess.run(
                [str(python_executable), "-m", "presentation.backend.app.ppe_worker", str(image_path)],
                cwd=str(project_root),
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
                env={**os.environ, "PYTHONPATH": str(project_root)},
            )
        except subprocess.TimeoutExpired as exc:
            raise HTTPException(status_code=504, detail="PPE_INFERENCE_TIMEOUT") from exc
        if completed.returncode != 0:
            raise HTTPException(status_code=503, detail="PPE_INFERENCE_WORKER_FAILED")
        marker = "DCG_PPE_RESULT="
        lines = [line[len(marker):] for line in completed.stdout.splitlines() if line.startswith(marker)]
        if len(lines) != 1:
            raise HTTPException(status_code=503, detail="PPE_WORKER_OUTPUT_INVALID")
        try:
            assessment = json.loads(lines[0])
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=503, detail="PPE_WORKER_OUTPUT_INVALID") from exc
    return {
        "source_type": "OPERATOR_UPLOADED_IMAGE",
        "inference_executed": True,
        "pipeline_status": "PPE_ONLY_NOT_INTEGRATED",
        "image_stored": False,
        "image_size": {"width": decoded.width, "height": decoded.height},
        "assessment": assessment,
    }
