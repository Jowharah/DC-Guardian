"""
DC-Guardian Phase 1
Face Recognition - Locked Final Test

Evaluates the frozen face-recognition configuration on:

    test_known   = 6 images
    test_unknown = 9 images

IMPORTANT:
    - Enrollment database is frozen.
    - Recognition threshold is frozen.
    - No threshold selection occurs here.
    - No fitting or enrollment occurs here.
"""

import csv
import json
import time

import numpy as np

from evidence.face_recognition.src.config import (
    MODELS_DIR,
    RESULTS_DIR,
    TEST_KNOWN_DIR,
    TEST_UNKNOWN_DIR,
)

from evidence.face_recognition.src.face_embedding import (
    extract_face_embedding,
)

from evidence.face_recognition.src.face_recognizer import (
    FaceRecognizer,
)


# ============================================================
# Frozen artifacts
# ============================================================

CONFIG_FILE = (
    MODELS_DIR
    / "face_recognition_config.json"
)

FINAL_RESULTS_DIR = (
    RESULTS_DIR
    / "final_test"
)

FINAL_PREDICTIONS_FILE = (
    FINAL_RESULTS_DIR
    / "final_test_predictions.csv"
)

FINAL_RESULTS_FILE = (
    FINAL_RESULTS_DIR
    / "face_recognition_final_test.json"
)


EXPECTED_KNOWN_IMAGES = 6
EXPECTED_UNKNOWN_IMAGES = 9

SUPPORTED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
}


# ============================================================
# Helpers
# ============================================================

def get_images(root):

    return sorted(
        path
        for path
        in root.rglob("*")
        if (
            path.is_file()
            and
            path.suffix.lower()
            in SUPPORTED_EXTENSIONS
        )
    )


# ============================================================
# Main
# ============================================================

def main():

    print(
        "\n============================================"
    )
    print(
        "DC-GUARDIAN FACE RECOGNITION"
    )
    print(
        "LOCKED FINAL TEST"
    )
    print(
        "============================================"
    )


    # ========================================================
    # Load frozen configuration
    # ========================================================

    if not CONFIG_FILE.is_file():

        raise FileNotFoundError(
            f"Frozen configuration missing: "
            f"{CONFIG_FILE}"
        )


    with CONFIG_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:

        config = json.load(file)


    if (
        config[
            "configuration_frozen"
        ]
        is not True
    ):

        raise RuntimeError(
            "Face configuration is not frozen."
        )


    if (
        config[
            "threshold_source"
        ]
        != "validation_only"
    ):

        raise RuntimeError(
            "Recognition threshold was not "
            "derived from validation only."
        )


    threshold = float(
        config[
            "recognition_threshold"
        ]
    )


    print(
        "Model:",
        config[
            "model_name"
        ],
    )

    print(
        "Detector:",
        config[
            "detector_backend"
        ],
    )

    print(
        "Distance metric:",
        config[
            "distance_metric"
        ],
    )

    print(
        "Frozen threshold:",
        threshold,
    )


    print(
        "\nIMPORTANT:"
    )

    print(
        "No enrollment, fitting, or threshold "
        "selection will occur."
    )


    # ========================================================
    # Load frozen enrollment database
    # ========================================================

    recognizer = FaceRecognizer()


    print(
        "\nPASS: Frozen enrollment database loaded."
    )


    # ========================================================
    # Final-test population
    # ========================================================

    known_images = get_images(
        TEST_KNOWN_DIR
    )

    unknown_images = get_images(
        TEST_UNKNOWN_DIR
    )


    if (
        len(
            known_images
        )
        != EXPECTED_KNOWN_IMAGES
    ):

        raise RuntimeError(
            "Known final-test population changed. "
            f"Expected {EXPECTED_KNOWN_IMAGES}, "
            f"found {len(known_images)}."
        )


    if (
        len(
            unknown_images
        )
        != EXPECTED_UNKNOWN_IMAGES
    ):

        raise RuntimeError(
            "Unknown final-test population changed. "
            f"Expected {EXPECTED_UNKNOWN_IMAGES}, "
            f"found {len(unknown_images)}."
        )


    print(
        "Known final-test images:",
        len(
            known_images
        ),
    )

    print(
        "Unknown final-test images:",
        len(
            unknown_images
        ),
    )

    print(
        "Total final-test images:",
        (
            len(
                known_images
            )
            +
            len(
                unknown_images
            )
        ),
    )


    FINAL_RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


    records = []


    # ========================================================
    # Evaluation helper
    # ========================================================

    def evaluate_image(
        image_path,
        *,
        is_known,
    ):

        actual_id = (
            image_path.parent.name
        )


        start = time.perf_counter()


        embedding_result = (
            extract_face_embedding(
                image_path
            )
        )


        match = (
            recognizer.match_embedding(
                embedding_result[
                    "embedding"
                ]
            )
        )


        elapsed_ms = (
            (
                time.perf_counter()
                - start
            )
            * 1000.0
        )


        predicted_id = (
            match[
                "employee_id"
            ]
            if (
                match[
                    "distance"
                ]
                <= threshold
            )
            else "UNKNOWN"
        )


        if is_known:

            if (
                predicted_id
                == actual_id
            ):

                outcome = (
                    "CORRECT_IDENTIFICATION"
                )


            elif (
                predicted_id
                == "UNKNOWN"
            ):

                outcome = (
                    "FALSE_REJECTION"
                )


            else:

                outcome = (
                    "MISIDENTIFICATION"
                )


        else:

            if (
                predicted_id
                == "UNKNOWN"
            ):

                outcome = (
                    "CORRECT_UNKNOWN_REJECTION"
                )


            else:

                outcome = (
                    "FALSE_ACCEPTANCE"
                )


        return {
            "split":
                (
                    "test_known"
                    if is_known
                    else "test_unknown"
                ),

            "image":
                image_path.name,

            "actual_id":
                actual_id,

            "is_known":
                is_known,

            "nearest_employee_id":
                match[
                    "employee_id"
                ],

            "distance":
                match[
                    "distance"
                ],

            "similarity":
                match[
                    "similarity"
                ],

            "threshold":
                threshold,

            "predicted_id":
                predicted_id,

            "outcome":
                outcome,

            "latency_ms":
                elapsed_ms,

            "face_confidence":
                embedding_result[
                    "face_confidence"
                ],
        }


    # ========================================================
    # Known final test
    # ========================================================

    print(
        "\nProcessing locked known test..."
    )


    for image_path in known_images:

        record = evaluate_image(
            image_path,
            is_known=True,
        )

        records.append(
            record
        )


        print(
            f"  {record['image']} | "
            f"actual={record['actual_id']} | "
            f"nearest={record['nearest_employee_id']} | "
            f"distance={record['distance']:.6f} | "
            f"prediction={record['predicted_id']} | "
            f"{record['outcome']}"
        )


    # ========================================================
    # Unknown final test
    # ========================================================

    print(
        "\nProcessing locked unknown test..."
    )


    for image_path in unknown_images:

        record = evaluate_image(
            image_path,
            is_known=False,
        )

        records.append(
            record
        )


        print(
            f"  {record['image']} | "
            f"nearest={record['nearest_employee_id']} | "
            f"distance={record['distance']:.6f} | "
            f"prediction={record['predicted_id']} | "
            f"{record['outcome']}"
        )


    # ========================================================
    # Metrics
    # ========================================================

    known_records = [
        record
        for record
        in records
        if record[
            "is_known"
        ]
    ]

    unknown_records = [
        record
        for record
        in records
        if not record[
            "is_known"
        ]
    ]


    correct_known = sum(
        record[
            "outcome"
        ]
        == "CORRECT_IDENTIFICATION"

        for record
        in known_records
    )


    false_rejections = sum(
        record[
            "outcome"
        ]
        == "FALSE_REJECTION"

        for record
        in known_records
    )


    misidentifications = sum(
        record[
            "outcome"
        ]
        == "MISIDENTIFICATION"

        for record
        in known_records
    )


    correct_unknown = sum(
        record[
            "outcome"
        ]
        == "CORRECT_UNKNOWN_REJECTION"

        for record
        in unknown_records
    )


    false_acceptances = sum(
        record[
            "outcome"
        ]
        == "FALSE_ACCEPTANCE"

        for record
        in unknown_records
    )


    known_identification_rate = (
        correct_known
        / len(
            known_records
        )
    )


    false_rejection_rate = (
        false_rejections
        / len(
            known_records
        )
    )


    misidentification_rate = (
        misidentifications
        / len(
            known_records
        )
    )


    unknown_rejection_rate = (
        correct_unknown
        / len(
            unknown_records
        )
    )


    false_acceptance_rate = (
        false_acceptances
        / len(
            unknown_records
        )
    )


    latencies = np.asarray(
        [
            record[
                "latency_ms"
            ]
            for record
            in records
        ],
        dtype=np.float64,
    )


    known_distances = np.asarray(
        [
            record[
                "distance"
            ]
            for record
            in known_records
        ],
        dtype=np.float64,
    )


    unknown_distances = np.asarray(
        [
            record[
                "distance"
            ]
            for record
            in unknown_records
        ],
        dtype=np.float64,
    )


    # ========================================================
    # Save predictions
    # ========================================================

    with FINAL_PREDICTIONS_FILE.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=list(
                records[
                    0
                ].keys()
            ),
        )

        writer.writeheader()

        writer.writerows(
            records
        )


    # ========================================================
    # Final result artifact
    # ========================================================

    result = {
        "artifact_type":
            "DC_GUARDIAN_FACE_FINAL_TEST",

        "artifact_version":
            "1.0",

        "model_name":
            config[
                "model_name"
            ],

        "detector_backend":
            config[
                "detector_backend"
            ],

        "distance_metric":
            config[
                "distance_metric"
            ],

        "recognition_threshold":
            threshold,

        "threshold_source":
            config[
                "threshold_source"
            ],

        "threshold_changed_during_final_test":
            False,

        "enrollment_changed_during_final_test":
            False,

        "known_test_images":
            len(
                known_records
            ),

        "unknown_test_images":
            len(
                unknown_records
            ),

        "total_test_images":
            len(
                records
            ),

        "correct_known_identifications":
            correct_known,

        "known_identification_rate":
            known_identification_rate,

        "false_rejections":
            false_rejections,

        "false_rejection_rate":
            false_rejection_rate,

        "misidentifications":
            misidentifications,

        "misidentification_rate":
            misidentification_rate,

        "correct_unknown_rejections":
            correct_unknown,

        "unknown_rejection_rate":
            unknown_rejection_rate,

        "false_acceptances":
            false_acceptances,

        "false_acceptance_rate":
            false_acceptance_rate,

        "known_distance_min":
            float(
                known_distances.min()
            ),

        "known_distance_max":
            float(
                known_distances.max()
            ),

        "known_distance_mean":
            float(
                known_distances.mean()
            ),

        "unknown_distance_min":
            float(
                unknown_distances.min()
            ),

        "unknown_distance_max":
            float(
                unknown_distances.max()
            ),

        "unknown_distance_mean":
            float(
                unknown_distances.mean()
            ),

        "mean_latency_ms":
            float(
                latencies.mean()
            ),

        "median_latency_ms":
            float(
                np.median(
                    latencies
                )
            ),

        "final_test_completed":
            True,
    }


    with FINAL_RESULTS_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            result,
            file,
            indent=2,
        )


    # ========================================================
    # Display
    # ========================================================

    print(
        "\n============================================"
    )
    print(
        "FINAL CONTROLLED FACE RESULTS"
    )
    print(
        "============================================"
    )


    print(
        "\nKnown identities"
    )

    print(
        "Correct identification:",
        f"{correct_known}/"
        f"{len(known_records)}",
    )

    print(
        "Known identification rate:",
        f"{known_identification_rate:.2%}",
    )

    print(
        "False rejections:",
        false_rejections,
    )

    print(
        "False rejection rate:",
        f"{false_rejection_rate:.2%}",
    )

    print(
        "Misidentifications:",
        misidentifications,
    )

    print(
        "Misidentification rate:",
        f"{misidentification_rate:.2%}",
    )


    print(
        "\nUnknown identities"
    )

    print(
        "Correct rejection:",
        f"{correct_unknown}/"
        f"{len(unknown_records)}",
    )

    print(
        "Unknown rejection rate:",
        f"{unknown_rejection_rate:.2%}",
    )

    print(
        "False acceptances:",
        false_acceptances,
    )

    print(
        "False acceptance rate:",
        f"{false_acceptance_rate:.2%}",
    )


    print(
        "\nDistance diagnostics"
    )

    print(
        "Known:",
        f"{known_distances.min():.6f}",
        "->",
        f"{known_distances.max():.6f}",
    )

    print(
        "Unknown:",
        f"{unknown_distances.min():.6f}",
        "->",
        f"{unknown_distances.max():.6f}",
    )


    print(
        "\nLatency"
    )

    print(
        "Mean:",
        f"{latencies.mean():.2f} ms",
    )

    print(
        "Median:",
        f"{np.median(latencies):.2f} ms",
    )


    print(
        "\nFrozen threshold:",
        threshold,
    )

    print(
        "Threshold changed: NO"
    )

    print(
        "Enrollment changed: NO"
    )


    print(
        "\nSaved:",
        FINAL_PREDICTIONS_FILE,
    )

    print(
        "Saved:",
        FINAL_RESULTS_FILE,
    )


    print(
        "\n============================================"
    )
    print(
        "LOCKED FACE FINAL EVALUATION COMPLETE"
    )
    print(
        "============================================"
    )


if __name__ == "__main__":

    main()
