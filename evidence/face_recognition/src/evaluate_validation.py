"""
DC-Guardian Phase 1
Face Recognition Validation Evaluation

Uses only:
    validation_known
    validation_unknown

Purpose:
    - extract validation embeddings
    - match against frozen enrollment database
    - inspect known/unknown distance separation
    - evaluate candidate recognition thresholds

Final-test data is NOT accessed.
"""

import csv
import json

import numpy as np

from evidence.face_recognition.src.config import (
    MODELS_DIR,
    RESULTS_DIR,
    VALIDATION_KNOWN_DIR,
    VALIDATION_UNKNOWN_DIR,
)

from evidence.face_recognition.src.face_embedding import (
    extract_face_embedding,
)

from evidence.face_recognition.src.face_recognizer import (
    FaceRecognizer,
)


# ============================================================
# Files
# ============================================================

VALIDATION_RESULTS_DIR = (
    RESULTS_DIR
    / "validation"
)

VALIDATION_MATCHES_FILE = (
    VALIDATION_RESULTS_DIR
    / "validation_matches.csv"
)

THRESHOLD_ANALYSIS_FILE = (
    VALIDATION_RESULTS_DIR
    / "threshold_analysis.csv"
)

VALIDATION_SUMMARY_FILE = (
    VALIDATION_RESULTS_DIR
    / "validation_summary.json"
)


SUPPORTED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
}


# ============================================================
# Candidate thresholds
#
# Broad exploratory range.
# We are NOT assuming DeepFace's default threshold.
# ============================================================

THRESHOLDS = np.round(
    np.arange(
        0.10,
        0.801,
        0.01,
    ),
    2,
)


# ============================================================
# Helpers
# ============================================================

def get_images(
    root,
):

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


def evaluate_threshold(
    records,
    threshold,
):
    """
    Evaluate one threshold.

    Decision:
        distance <= threshold -> nearest enrolled employee
        distance > threshold  -> UNKNOWN

    Error definitions:

    False rejection:
        known person -> UNKNOWN

    Misidentification:
        known person -> wrong enrolled employee

    False acceptance:
        unknown person -> any enrolled employee
    """

    known_total = 0
    known_correct = 0
    false_rejections = 0
    misidentifications = 0

    unknown_total = 0
    unknown_correct = 0
    false_acceptances = 0


    for record in records:

        predicted = (
            record[
                "best_employee_id"
            ]
            if (
                record[
                    "distance"
                ]
                <= threshold
            )
            else "UNKNOWN"
        )


        if record[
            "is_known"
        ]:

            known_total += 1


            if (
                predicted
                == record[
                    "actual_id"
                ]
            ):

                known_correct += 1


            elif predicted == "UNKNOWN":

                false_rejections += 1


            else:

                misidentifications += 1


        else:

            unknown_total += 1


            if predicted == "UNKNOWN":

                unknown_correct += 1


            else:

                false_acceptances += 1


    known_identification_rate = (
        known_correct
        / known_total
    )

    unknown_rejection_rate = (
        unknown_correct
        / unknown_total
    )

    false_rejection_rate = (
        false_rejections
        / known_total
    )

    misidentification_rate = (
        misidentifications
        / known_total
    )

    false_acceptance_rate = (
        false_acceptances
        / unknown_total
    )


    # Balanced treatment of the two primary populations.
    #
    # This is diagnostic only; we will inspect the actual
    # error types before selecting the threshold.

    balanced_recognition_rate = (
        known_identification_rate
        + unknown_rejection_rate
    ) / 2.0


    return {
        "threshold":
            float(
                threshold
            ),

        "known_total":
            known_total,

        "known_correct":
            known_correct,

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

        "unknown_total":
            unknown_total,

        "unknown_correct":
            unknown_correct,

        "unknown_rejection_rate":
            unknown_rejection_rate,

        "false_acceptances":
            false_acceptances,

        "false_acceptance_rate":
            false_acceptance_rate,

        "balanced_recognition_rate":
            balanced_recognition_rate,
    }


# ============================================================
# Main
# ============================================================

def main():

    print(
        "\n============================================"
    )

    print(
        "DC-GUARDIAN FACE VALIDATION EVALUATION"
    )

    print(
        "============================================"
    )


    if not VALIDATION_KNOWN_DIR.is_dir():

        raise RuntimeError(
            "validation_known not found."
        )


    if not VALIDATION_UNKNOWN_DIR.is_dir():

        raise RuntimeError(
            "validation_unknown not found."
        )


    VALIDATION_RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


    recognizer = (
        FaceRecognizer()
    )


    print(
        "PASS: Frozen enrollment database loaded."
    )


    # ========================================================
    # Collect validation images
    # ========================================================

    known_images = get_images(
        VALIDATION_KNOWN_DIR
    )

    unknown_images = get_images(
        VALIDATION_UNKNOWN_DIR
    )


    if len(
        known_images
    ) != 7:

        raise RuntimeError(
            "Expected 7 validation-known images; "
            f"found {len(known_images)}."
        )


    if len(
        unknown_images
    ) != 6:

        raise RuntimeError(
            "Expected 6 validation-unknown images; "
            f"found {len(unknown_images)}."
        )


    print(
        "Validation-known images:",
        len(
            known_images
        ),
    )

    print(
        "Validation-unknown images:",
        len(
            unknown_images
        ),
    )


    records = []


    # ========================================================
    # Known validation
    # ========================================================

    print(
        "\nProcessing validation-known..."
    )


    for image_path in known_images:

        actual_id = (
            image_path.parent.name
        )


        result = (
            extract_face_embedding(
                image_path
            )
        )


        match = (
            recognizer.match_embedding(
                result[
                    "embedding"
                ]
            )
        )


        record = {
            "split":
                "validation_known",

            "image":
                image_path.name,

            "actual_id":
                actual_id,

            "is_known":
                True,

            "best_employee_id":
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

            "nearest_identity_correct":
                (
                    match[
                        "employee_id"
                    ]
                    == actual_id
                ),
        }


        records.append(
            record
        )


        print(
            f"  {image_path.name} | "
            f"actual={actual_id} | "
            f"nearest={match['employee_id']} | "
            f"distance={match['distance']:.6f}"
        )


    # ========================================================
    # Unknown validation
    # ========================================================

    print(
        "\nProcessing validation-unknown..."
    )


    for image_path in unknown_images:

        actual_id = (
            image_path.parent.name
        )


        result = (
            extract_face_embedding(
                image_path
            )
        )


        match = (
            recognizer.match_embedding(
                result[
                    "embedding"
                ]
            )
        )


        record = {
            "split":
                "validation_unknown",

            "image":
                image_path.name,

            "actual_id":
                actual_id,

            "is_known":
                False,

            "best_employee_id":
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

            "nearest_identity_correct":
                False,
        }


        records.append(
            record
        )


        print(
            f"  {image_path.name} | "
            f"actual={actual_id} | "
            f"nearest={match['employee_id']} | "
            f"distance={match['distance']:.6f}"
        )


    # ========================================================
    # Save raw validation matches
    # ========================================================

    with VALIDATION_MATCHES_FILE.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=[
                "split",
                "image",
                "actual_id",
                "is_known",
                "best_employee_id",
                "distance",
                "similarity",
                "nearest_identity_correct",
            ],
        )

        writer.writeheader()

        writer.writerows(
            records
        )


    # ========================================================
    # Distance diagnostics
    # ========================================================

    known_distances = np.asarray(
        [
            record[
                "distance"
            ]
            for record
            in records
            if record[
                "is_known"
            ]
        ],
        dtype=np.float64,
    )


    unknown_distances = np.asarray(
        [
            record[
                "distance"
            ]
            for record
            in records
            if not record[
                "is_known"
            ]
        ],
        dtype=np.float64,
    )


    nearest_known_correct = sum(
        1
        for record
        in records
        if (
            record[
                "is_known"
            ]
            and
            record[
                "nearest_identity_correct"
            ]
        )
    )


    print(
        "\n============================================"
    )

    print(
        "VALIDATION DISTANCE DIAGNOSTICS"
    )

    print(
        "============================================"
    )


    print(
        "Known nearest-ID correct:",
        f"{nearest_known_correct}/7",
    )


    print(
        "\nKnown distance range:",
        f"{known_distances.min():.6f}",
        "->",
        f"{known_distances.max():.6f}",
    )


    print(
        "Known mean distance:",
        f"{known_distances.mean():.6f}",
    )


    print(
        "\nUnknown distance range:",
        f"{unknown_distances.min():.6f}",
        "->",
        f"{unknown_distances.max():.6f}",
    )


    print(
        "Unknown mean distance:",
        f"{unknown_distances.mean():.6f}",
    )


    # ========================================================
    # Threshold sweep
    # ========================================================

    threshold_results = [
        evaluate_threshold(
            records,
            threshold,
        )
        for threshold
        in THRESHOLDS
    ]


    with THRESHOLD_ANALYSIS_FILE.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=list(
                threshold_results[
                    0
                ].keys()
            ),
        )

        writer.writeheader()

        writer.writerows(
            threshold_results
        )


    # ========================================================
    # Find diagnostic operating points
    #
    # We are NOT freezing a threshold in this script.
    # ========================================================

    best_balanced = max(
        threshold_results,
        key=lambda item: (
            item[
                "balanced_recognition_rate"
            ],

            -item[
                "false_acceptance_rate"
            ],

            -item[
                "false_rejection_rate"
            ],
        ),
    )


    zero_fa_candidates = [
        item
        for item
        in threshold_results
        if (
            item[
                "false_acceptances"
            ]
            == 0
        )
    ]


    best_zero_fa = None


    if zero_fa_candidates:

        best_zero_fa = max(
            zero_fa_candidates,
            key=lambda item: (
                item[
                    "known_identification_rate"
                ],

                -item[
                    "false_rejection_rate"
                ],

                item[
                    "threshold"
                ],
            ),
        )


    # ========================================================
    # Summary artifact
    # ========================================================

    summary = {
        "artifact_type":
            "DC_GUARDIAN_FACE_VALIDATION",

        "enrollment_artifact":
            "employee_embeddings.npz",

        "known_validation_images":
            len(
                known_images
            ),

        "unknown_validation_images":
            len(
                unknown_images
            ),

        "nearest_identity_correct_known":
            nearest_known_correct,

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

        "best_balanced_operating_point":
            best_balanced,

        "best_zero_false_acceptance_operating_point":
            best_zero_fa,

        "final_test_accessed":
            False,

        "threshold_frozen":
            False,
    }


    with VALIDATION_SUMMARY_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            summary,
            file,
            indent=2,
        )


    # ========================================================
    # Display candidate operating points
    # ========================================================

    print(
        "\n============================================"
    )

    print(
        "VALIDATION OPERATING POINTS"
    )

    print(
        "============================================"
    )


    print(
        "\nBest balanced diagnostic point:"
    )

    print(
        "Threshold:",
        best_balanced[
            "threshold"
        ],
    )

    print(
        "Known identification:",
        f"{best_balanced['known_correct']}/"
        f"{best_balanced['known_total']}",
    )

    print(
        "Unknown rejection:",
        f"{best_balanced['unknown_correct']}/"
        f"{best_balanced['unknown_total']}",
    )

    print(
        "False acceptances:",
        best_balanced[
            "false_acceptances"
        ],
    )

    print(
        "False rejections:",
        best_balanced[
            "false_rejections"
        ],
    )

    print(
        "Misidentifications:",
        best_balanced[
            "misidentifications"
        ],
    )


    if best_zero_fa is not None:

        print(
            "\nBest zero-false-acceptance "
            "diagnostic point:"
        )

        print(
            "Threshold:",
            best_zero_fa[
                "threshold"
            ],
        )

        print(
            "Known identification:",
            f"{best_zero_fa['known_correct']}/"
            f"{best_zero_fa['known_total']}",
        )

        print(
            "Unknown rejection:",
            f"{best_zero_fa['unknown_correct']}/"
            f"{best_zero_fa['unknown_total']}",
        )

        print(
            "False acceptances:",
            best_zero_fa[
                "false_acceptances"
        ],
    )


    print(
        "\nSaved:",
        VALIDATION_MATCHES_FILE,
    )

    print(
        "Saved:",
        THRESHOLD_ANALYSIS_FILE,
    )

    print(
        "Saved:",
        VALIDATION_SUMMARY_FILE,
    )


    print(
        "\nPASS: Enrollment database unchanged."
    )

    print(
        "PASS: Validation-known accessed."
    )

    print(
        "PASS: Validation-unknown accessed."
    )

    print(
        "PASS: Final-test data not accessed."
    )

    print(
        "PASS: Recognition threshold NOT frozen yet."
    )


    print(
        "\n============================================"
    )

    print(
        "FACE VALIDATION EVALUATION PASSED"
    )

    print(
        "============================================"
    )


if __name__ == "__main__":

    main()
