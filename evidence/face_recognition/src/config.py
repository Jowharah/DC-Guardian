from pathlib import Path


FACE_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

DATA_ROOT = (
    FACE_ROOT
    / "data"
    / "controlled_faces"
)

ENROLLMENT_DIR = (
    DATA_ROOT
    / "enrollment"
)

VALIDATION_KNOWN_DIR = (
    DATA_ROOT
    / "validation_known"
)

VALIDATION_UNKNOWN_DIR = (
    DATA_ROOT
    / "validation_unknown"
)

TEST_KNOWN_DIR = (
    DATA_ROOT
    / "test_known"
)

TEST_UNKNOWN_DIR = (
    DATA_ROOT
    / "test_unknown"
)

MODELS_DIR = (
    FACE_ROOT
    / "models"
)

RESULTS_DIR = (
    FACE_ROOT
    / "results"
)


EMPLOYEE_IDS = (
    "P001",
    "P002",
    "P003",
    "P004",
    "P005",
)


MODEL_NAME = "ArcFace"

DETECTOR_BACKEND = "retinaface"

DISTANCE_METRIC = "cosine"

EXPECTED_EMBEDDING_DIMENSION = 512