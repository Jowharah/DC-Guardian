"""
DC-Guardian Phase 1
Face Enrollment Artifact Contract Test
"""

import json
from pathlib import Path

import numpy as np


# ============================================================
# Paths
# ============================================================

FACE_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

MODELS_DIR = (
    FACE_ROOT
    / "models"
)

EMBEDDING_FILE = (
    MODELS_DIR
    / "employee_embeddings.npz"
)

METADATA_FILE = (
    MODELS_DIR
    / "enrollment_metadata.json"
)


# ============================================================
# Frozen contract
# ============================================================

EXPECTED_EMPLOYEES = {
    "P001",
    "P002",
    "P003",
    "P004",
    "P005",
}

EXPECTED_COUNTS = {
    "P001": 3,
    "P002": 3,
    "P003": 4,
    "P004": 4,
    "P005": 4,
}

EXPECTED_EMBEDDINGS = 18
EXPECTED_DIMENSION = 512


# ============================================================
# Test
# ============================================================

print(
    "\n============================================"
)

print(
    "DC-GUARDIAN FACE ENROLLMENT ARTIFACT TEST"
)

print(
    "============================================"
)


# ============================================================
# Files
# ============================================================

assert EMBEDDING_FILE.is_file(), (
    f"Missing enrollment artifact: "
    f"{EMBEDDING_FILE}"
)

assert METADATA_FILE.is_file(), (
    f"Missing enrollment metadata: "
    f"{METADATA_FILE}"
)


print(
    "PASS: Enrollment artifacts exist."
)


# ============================================================
# Load NPZ
# ============================================================

with np.load(
    EMBEDDING_FILE,
    allow_pickle=False,
) as artifact:

    required_keys = {
        "embeddings",
        "employee_ids",
        "source_files",
        "face_confidences",
    }

    actual_keys = set(
        artifact.files
    )


    if actual_keys != required_keys:

        raise AssertionError(
            "Enrollment NPZ key mismatch.\n"
            f"Expected: {sorted(required_keys)}\n"
            f"Actual:   {sorted(actual_keys)}"
        )


    embeddings = (
        artifact[
            "embeddings"
        ].copy()
    )

    employee_ids = (
        artifact[
            "employee_ids"
        ].copy()
    )

    source_files = (
        artifact[
            "source_files"
        ].copy()
    )

    face_confidences = (
        artifact[
            "face_confidences"
        ].copy()
    )


print(
    "PASS: Enrollment NPZ loads "
    "without pickle."
)


# ============================================================
# Matrix contract
# ============================================================

assert embeddings.shape == (
    EXPECTED_EMBEDDINGS,
    EXPECTED_DIMENSION,
), (
    "Embedding matrix shape mismatch: "
    f"{embeddings.shape}"
)


assert embeddings.dtype == np.float32


assert np.isfinite(
    embeddings
).all()


print(
    "PASS: Embedding matrix shape = "
    "(18, 512)."
)

print(
    "PASS: All enrollment embeddings finite."
)


# ============================================================
# Label contract
# ============================================================

assert len(
    employee_ids
) == EXPECTED_EMBEDDINGS


actual_employees = set(
    employee_ids.tolist()
)


assert actual_employees == (
    EXPECTED_EMPLOYEES
)


for employee_id, expected_count in (
    EXPECTED_COUNTS.items()
):

    actual_count = int(
        np.sum(
            employee_ids
            == employee_id
        )
    )


    assert (
        actual_count
        == expected_count
    ), (
        f"{employee_id} expected "
        f"{expected_count} embeddings, "
        f"found {actual_count}."
    )


print(
    "PASS: Five enrolled identities preserved."
)

print(
    "PASS: Per-employee embedding counts preserved."
)


# ============================================================
# Source-file contract
# ============================================================

assert len(
    source_files
) == EXPECTED_EMBEDDINGS


for employee_id, source_file in zip(
    employee_ids,
    source_files,
):

    source_path = Path(
        str(
            source_file
        )
    )


    # Must be relative.
    assert not source_path.is_absolute()


    # First path component must match employee label.
    assert (
        source_path.parts[
            0
        ]
        == employee_id
    ), (
        "Source-file identity mismatch: "
        f"{source_file} vs {employee_id}"
    )


    # Enrollment artifact must not contain references
    # to validation or final-test splits.

    source_text = str(
        source_file
    ).lower()


    assert (
        "validation"
        not in source_text
    )

    assert (
        "test_known"
        not in source_text
    )

    assert (
        "test_unknown"
        not in source_text
    )


print(
    "PASS: Source image identities match labels."
)

print(
    "PASS: Enrollment artifact contains "
    "no validation/test references."
)


# ============================================================
# Face detection confidence
# ============================================================

assert len(
    face_confidences
) == EXPECTED_EMBEDDINGS


assert np.isfinite(
    face_confidences
).all()


assert np.all(
    (
        face_confidences
        >= 0.0
    )
    &
    (
        face_confidences
        <= 1.0
    )
)


print(
    "PASS: Face-detection confidence "
    "values valid."
)


# ============================================================
# Metadata contract
# ============================================================

with METADATA_FILE.open(
    "r",
    encoding="utf-8",
) as file:

    metadata = json.load(
        file
    )


assert (
    metadata[
        "artifact_type"
    ]
    == "DC_GUARDIAN_FACE_ENROLLMENT"
)

assert (
    metadata[
        "artifact_version"
    ]
    == "1.0"
)

assert (
    metadata[
        "model_name"
    ]
    == "ArcFace"
)

assert (
    metadata[
        "detector_backend"
    ]
    == "retinaface"
)

assert (
    metadata[
        "distance_metric"
    ]
    == "cosine"
)

assert (
    metadata[
        "embedding_dimension"
    ]
    == EXPECTED_DIMENSION
)

assert (
    metadata[
        "employee_count"
    ]
    == 5
)

assert (
    metadata[
        "embedding_count"
    ]
    == EXPECTED_EMBEDDINGS
)

assert set(
    metadata[
        "employee_ids"
    ]
) == EXPECTED_EMPLOYEES


assert (
    metadata[
        "counts_by_employee"
    ]
    == EXPECTED_COUNTS
)


print(
    "PASS: ArcFace/RetinaFace "
    "configuration preserved."
)


# ============================================================
# Dataset-access boundary
# ============================================================

assert (
    metadata[
        "dataset_split"
    ]
    == "enrollment"
)

assert (
    metadata[
        "validation_accessed"
    ]
    is False
)

assert (
    metadata[
        "final_test_accessed"
    ]
    is False
)


print(
    "PASS: Enrollment-only data boundary preserved."
)


# ============================================================
# Metadata image records
# ============================================================

image_records = metadata[
    "image_records"
]


assert (
    len(
        image_records
    )
    == EXPECTED_EMBEDDINGS
)


for index, record in enumerate(
    image_records
):

    assert (
        record[
            "embedding_index"
        ]
        == index
    )

    assert (
        record[
            "employee_id"
        ]
        == employee_ids[
            index
        ]
    )

    assert (
        record[
            "source_file"
        ]
        == source_files[
            index
        ]
    )


print(
    "PASS: Enrollment metadata records "
    "align with embedding matrix."
)


# ============================================================
# Final
# ============================================================

print(
    "\n============================================"
)

print(
    "FACE ENROLLMENT ARTIFACT SUMMARY"
)

print(
    "============================================"
)

print(
    "Employees:            5"
)

print(
    "Enrollment embeddings:",
    EXPECTED_EMBEDDINGS,
)

print(
    "Embedding dimension:  ",
    EXPECTED_DIMENSION,
)

print(
    "Model:                ",
    metadata[
        "model_name"
    ],
)

print(
    "Detector:             ",
    metadata[
        "detector_backend"
    ],
)

print(
    "Distance metric:      ",
    metadata[
        "distance_metric"
    ],
)


print(
    "\n============================================"
)

print(
    "FACE ENROLLMENT ARTIFACT CONTRACT PASSED"
)

print(
    "============================================"
)