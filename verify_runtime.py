"""
DC-GUARDIAN integrated runtime smoke test.

This verifies that the public/frozen Phase 1 runtime stacks can initialize
from the repository environment without running training or requiring private
Face enrollment images/embeddings.

Run from the repository root:
    python verify_runtime.py
"""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent


def check_maintenance():
    from phase1.predictive_maintenance.src.maintenance_detector import (
        load_model,
    )

    model = load_model()

    if model.__class__.__name__ != "Pipeline":
        raise RuntimeError(
            "Unexpected Predictive Maintenance artifact type: "
            f"{type(model)}"
        )

    print("PASS: Predictive Maintenance frozen pipeline.")


def check_ssh():
    from phase1.ssh_anomaly.src.ssh_detector import (
        SSHAnomalyDetector,
    )

    detector = SSHAnomalyDetector()

    if detector is None:
        raise RuntimeError(
            "SSH detector initialization returned None."
        )

    print("PASS: SSH frozen detector and artifact integrity.")


def check_ppe():
    from ultralytics import YOLO

    model_path = (
        PROJECT_ROOT
        / "phase1"
        / "ppe_detection"
        / "models"
        / "ppe_yolov8_best.pt"
    )

    if not model_path.is_file():
        raise FileNotFoundError(
            f"PPE frozen model not found: {model_path}"
        )

    YOLO(str(model_path))

    print("PASS: PPE frozen YOLO model.")


def check_face_stack():
    # Do not initialize FaceRecognitionPipeline here because the private
    # employee_embeddings.npz artifact is intentionally excluded from Git.
    from deepface import DeepFace  # noqa: F401
    from phase1.face_recognition.src.face_embedding import (
        extract_face_embedding,  # noqa: F401
    )

    print(
        "PASS: Face DeepFace/ArcFace runtime stack "
        "(private enrollment artifact not required)."
    )


def main():
    checks = (
        check_maintenance,
        check_ssh,
        check_ppe,
        check_face_stack,
    )

    print("=" * 60)
    print("DC-GUARDIAN INTEGRATED RUNTIME SMOKE TEST")
    print("=" * 60)

    for check in checks:
        check()

    print()
    print("=" * 60)
    print("DC-GUARDIAN RUNTIME SMOKE TEST PASSED: 4/4")
    print("=" * 60)


if __name__ == "__main__":
    main()
