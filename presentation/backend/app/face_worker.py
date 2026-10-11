"""Isolated invocation of the frozen Face Recognition pipeline."""
import json
import sys
from evidence.face_recognition.src.face_pipeline import FaceRecognitionPipeline

def main():
    result = FaceRecognitionPipeline().recognize(sys.argv[1])
    # Never return enrollment embeddings or local image paths.
    result.pop("image", None)
    result.pop("nearest_employee_id", None) if result.get("recognition_status") != "RECOGNIZED" else None
    print("DCG_FACE_RESULT=" + json.dumps(result, allow_nan=False))

if __name__ == "__main__":
    main()
