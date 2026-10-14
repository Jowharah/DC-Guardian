"""Restricted single-image PPE inference worker for dedicated CUDA venv.

Called only by the Presentation backend using a fixed executable and script path,
one-shot or persistent (see worker_protocol). Emits one JSON result per image on
stdout. No shell, dynamic imports or user commands.
"""
import os
import sys

from presentation.backend.app.worker_protocol import run


def load():
    from evidence.ppe_detection.src.ppe_pipeline import DETECTOR_CONFIGS, PPECompliancePipeline
    # Set by the backend from DCG_PPE_DETECTOR; only the fixed detector names are accepted.
    detector = os.environ.get("DCG_PPE_DETECTOR", "v1")
    if detector not in DETECTOR_CONFIGS:
        raise SystemExit(2)
    return PPECompliancePipeline(detector)


def handle(pipeline, path):
    return pipeline.assess(str(path))


if __name__ == "__main__":
    try:
        sys.exit(run("DCG_PPE_RESULT=", load, handle))
    except SystemExit:
        raise
    except Exception:
        print("PPE worker inference failed", file=sys.stderr)
        sys.exit(1)
