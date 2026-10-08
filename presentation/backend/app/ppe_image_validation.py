"""Local PPE image validation against the frozen runtime (not an integrated incident).

No source images are persisted by this endpoint. The endpoint validates decoded
image bytes before running the unchanged frozen model. CUDA is required by that model.
"""
from io import BytesIO
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
    try:
        import numpy as np
        from evidence.ppe_detection.src.ppe_pipeline import PPECompliancePipeline
        assessment = PPECompliancePipeline().assess(np.asarray(decoded))
    except (FileNotFoundError, RuntimeError) as exc:
        # Never pretend an inference result exists if CUDA or artifacts are absent.
        raise HTTPException(status_code=503, detail="Frozen PPE runtime unavailable; verify CUDA and model artifacts") from exc
    return {
        "source_type": "OPERATOR_UPLOADED_IMAGE",
        "inference_executed": True,
        "pipeline_status": "PPE_ONLY_NOT_INTEGRATED",
        "image_stored": False,
        "image_size": {"width": decoded.width, "height": decoded.height},
        "assessment": assessment,
    }
