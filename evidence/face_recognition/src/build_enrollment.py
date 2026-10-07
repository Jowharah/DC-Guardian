"""
DC-Guardian Phase 1
Face Recognition Enrollment Builder

Builds the authorized employee embedding database from the
controlled enrollment split only.

Pipeline:
    Enrollment image
        -> RetinaFace detection/alignment
        -> ArcFace 512-D embedding
        -> enrollment artifact

No validation or final-test images are accessed here.
"""

import json
from datetime import datetime, timezone

import deepface
import numpy as np

from evidence.face_recognition.src.config import (
    DETECTOR_BACKEND,
    DISTANCE_METRIC,
    EMPLOYEE_IDS,
    ENROLLMENT_DIR,
    EXPECTED_EMBEDDING_DIMENSION,
    MODEL_NAME,
    MODELS_DIR,
)

from evidence.face_recognition.src.face_embedding import (
    extract_face_embedding,
)


# ============================================================
# Frozen enrollment contract
# ============================================================

EXPECTED_ENROLLMENT_COUNTS = {
    "P001": 3,
    "P002": 3,
    "P003": 4,
    "P004": 4,
    "P005": 4,
}


EXPECTED_TOTAL_EMBEDDINGS = 18


SUPPORTED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
}


# ============================================================
# Output artifacts
# ============================================================

EMBEDDING_FILE = (
    MODELS_DIR
    / "employee_embeddings.npz"
)


METADATA_FILE = (
    MODELS_DIR
    / "enrollment_metadata.json"
)


# ============================================================
# Helpers
# ============================================================

def get_employee_images(
    employee_id,
):
    """
    Return the enrollment images for exactly one employee.
    """

    employee_dir = (
        ENROLLMENT_DIR
        / employee_id
    )


    if not employee_dir.is_dir():

        raise RuntimeError(
            "Enrollment directory missing: "
            f"{employee_dir}"
        )


    images = sorted(
        path
        for path
        in employee_dir.iterdir()
        if (
            path.is_file()
            and
            path.suffix.lower()
            in SUPPORTED_EXTENSIONS
        )
    )


    return images


# ============================================================
# Main builder
# ============================================================

def build_enrollment_database():

    print(
        "\n============================================"
    )

    print(
        "DC-GUARDIAN FACE ENROLLMENT BUILDER"
    )

    print(
        "============================================"
    )


    if not ENROLLMENT_DIR.is_dir():

        raise RuntimeError(
            "Enrollment dataset not found:\n"
            f"{ENROLLMENT_DIR}"
        )


    MODELS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


    embeddings = []

    employee_labels = []

    source_files = []

    face_confidences = []

    facial_areas = []


    # ========================================================
    # Process each authorized identity
    # ========================================================

    for employee_id in EMPLOYEE_IDS:

        print(
            f"\nProcessing {employee_id}..."
        )


        images = get_employee_images(
            employee_id
        )


        expected_count = (
            EXPECTED_ENROLLMENT_COUNTS[
                employee_id
            ]
        )


        if len(images) != expected_count:

            raise RuntimeError(
                f"{employee_id} enrollment image "
                "count mismatch. "
                f"Expected {expected_count}, "
                f"found {len(images)}."
            )


        for image_path in images:

            print(
                f"  Embedding: {image_path.name}"
            )


            result = (
                extract_face_embedding(
                    image_path
                )
            )


            embedding = result[
                "embedding"
            ]


            if (
                embedding.shape
                != (
                    EXPECTED_EMBEDDING_DIMENSION,
                )
            ):

                raise RuntimeError(
                    "Unexpected embedding shape "
                    f"for {image_path.name}: "
                    f"{embedding.shape}"
                )


            embeddings.append(
                embedding
            )


            employee_labels.append(
                employee_id
            )


            # Store relative enrollment path rather than
            # machine-specific absolute path.

            source_files.append(
                str(
                    image_path.relative_to(
                        ENROLLMENT_DIR
                    )
                ).replace(
                    "\\",
                    "/",
                )
            )


            confidence = result.get(
                "face_confidence"
            )


            face_confidences.append(
                (
                    float(
                        confidence
                    )
                    if confidence
                    is not None
                    else np.nan
                )
            )


            facial_areas.append(
                result.get(
                    "facial_area"
                )
            )


            print(
                "    PASS: "
                f"{embedding.shape[0]}-D embedding"
            )


    # ========================================================
    # Materialize numeric database
    # ========================================================

    embedding_matrix = np.stack(
        embeddings
    ).astype(
        np.float32
    )


    employee_labels = np.asarray(
        employee_labels,
        dtype="<U16",
    )


    source_files = np.asarray(
        source_files,
        dtype="<U256",
    )


    face_confidences = np.asarray(
        face_confidences,
        dtype=np.float32,
    )


    # ========================================================
    # Contract checks before saving
    # ========================================================

    if (
        embedding_matrix.shape
        != (
            EXPECTED_TOTAL_EMBEDDINGS,
            EXPECTED_EMBEDDING_DIMENSION,
        )
    ):

        raise RuntimeError(
            "Enrollment matrix shape mismatch. "
            "Expected "
            f"({EXPECTED_TOTAL_EMBEDDINGS}, "
            f"{EXPECTED_EMBEDDING_DIMENSION}), "
            f"found {embedding_matrix.shape}."
        )


    if not np.isfinite(
        embedding_matrix
    ).all():

        raise RuntimeError(
            "Enrollment database contains "
            "NaN or infinite embeddings."
        )


    if (
        len(
            employee_labels
        )
        != EXPECTED_TOTAL_EMBEDDINGS
    ):

        raise RuntimeError(
            "Enrollment labels are incomplete."
        )


    unique_ids = set(
        employee_labels.tolist()
    )


    if unique_ids != set(
        EMPLOYEE_IDS
    ):

        raise RuntimeError(
            "Enrollment employee identity "
            "contract failed."
        )


    # ========================================================
    # Save NPZ
    # ========================================================

    np.savez_compressed(
        EMBEDDING_FILE,

        embeddings=
            embedding_matrix,

        employee_ids=
            employee_labels,

        source_files=
            source_files,

        face_confidences=
            face_confidences,
    )


    # ========================================================
    # Metadata
    # ========================================================

    counts_by_employee = {
        employee_id:
            int(
                np.sum(
                    employee_labels
                    == employee_id
                )
            )

        for employee_id
        in EMPLOYEE_IDS
    }


    image_records = []


    for index in range(
        EXPECTED_TOTAL_EMBEDDINGS
    ):

        image_records.append(
            {
                "embedding_index":
                    index,

                "employee_id":
                    str(
                        employee_labels[
                            index
                        ]
                    ),

                "source_file":
                    str(
                        source_files[
                            index
                        ]
                    ),

                "face_confidence":
                    (
                        float(
                            face_confidences[
                                index
                            ]
                        )
                        if np.isfinite(
                            face_confidences[
                                index
                            ]
                        )
                        else None
                    ),

                "facial_area":
                    facial_areas[
                        index
                    ],
            }
        )


    metadata = {
        "artifact_type":
            "DC_GUARDIAN_FACE_ENROLLMENT",

        "artifact_version":
            "1.0",

        "created_utc":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "model_name":
            MODEL_NAME,

        "detector_backend":
            DETECTOR_BACKEND,

        "distance_metric":
            DISTANCE_METRIC,

        "embedding_dimension":
            EXPECTED_EMBEDDING_DIMENSION,

        "employee_count":
            len(
                EMPLOYEE_IDS
            ),

        "employee_ids":
            list(
                EMPLOYEE_IDS
            ),

        "embedding_count":
            EXPECTED_TOTAL_EMBEDDINGS,

        "counts_by_employee":
            counts_by_employee,

        "deepface_version":
            getattr(
                deepface,
                "__version__",
                "UNKNOWN",
            ),

        "dataset_split":
            "enrollment",

        "validation_accessed":
            False,

        "final_test_accessed":
            False,

        "image_records":
            image_records,
    }


    with METADATA_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            metadata,
            file,
            indent=2,
        )


    # ========================================================
    # Summary
    # ========================================================

    print(
        "\n============================================"
    )

    print(
        "FACE ENROLLMENT SUMMARY"
    )

    print(
        "============================================"
    )


    print(
        "Employees:",
        len(
            EMPLOYEE_IDS
        ),
    )


    for employee_id in EMPLOYEE_IDS:

        print(
            f"{employee_id}: "
            f"{counts_by_employee[employee_id]} "
            "embeddings"
        )


    print(
        "\nEmbedding matrix:",
        embedding_matrix.shape,
    )


    finite_confidences = (
        face_confidences[
            np.isfinite(
                face_confidences
            )
        ]
    )


    if len(
        finite_confidences
    ) > 0:

        print(
            "Face confidence range:",
            f"{finite_confidences.min():.6f}",
            "->",
            f"{finite_confidences.max():.6f}",
        )


    print(
        "\nSaved:",
        EMBEDDING_FILE,
    )


    print(
        "Saved:",
        METADATA_FILE,
    )


    print(
        "\nPASS: Enrollment split only accessed."
    )

    print(
        "PASS: Validation data not accessed."
    )

    print(
        "PASS: Final-test data not accessed."
    )


    print(
        "\n============================================"
    )

    print(
        "FACE ENROLLMENT BUILD PASSED"
    )

    print(
        "============================================"
    )


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":

    build_enrollment_database()
