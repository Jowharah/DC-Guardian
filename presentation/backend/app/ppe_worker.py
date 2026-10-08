"""Restricted single-image PPE inference worker for dedicated CUDA venv.

Called only by the Presentation backend using a fixed executable and script path.
Emits one JSON result on stdout. No shell, dynamic imports or user commands.
"""
import json
import sys
from pathlib import Path

def main() -> int:
    if len(sys.argv) != 2:
        return 2
    image_path = Path(sys.argv[1]).resolve()
    if not image_path.is_file():
        return 2
    from evidence.ppe_detection.src.ppe_pipeline import PPECompliancePipeline
    assessment = PPECompliancePipeline().assess(str(image_path))
    print("DCG_PPE_RESULT=" + json.dumps(assessment, allow_nan=False))
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        print("PPE worker inference failed", file=sys.stderr)
        sys.exit(1)
