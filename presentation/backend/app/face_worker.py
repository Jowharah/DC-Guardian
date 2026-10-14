"""Isolated invocation of the frozen Face Recognition pipeline (one-shot or persistent, see worker_protocol)."""
import sys

from presentation.backend.app.worker_protocol import run


def load():
    from evidence.face_recognition.src.face_pipeline import FaceRecognitionPipeline
    return FaceRecognitionPipeline()


def handle(pipeline, path):
    result = pipeline.recognize(str(path))
    # Never return enrollment embeddings or local image paths.
    result.pop("image", None)
    result.pop("nearest_employee_id", None) if result.get("recognition_status") != "RECOGNIZED" else None
    return result


if __name__ == "__main__":
    sys.exit(run("DCG_FACE_RESULT=", load, handle))
