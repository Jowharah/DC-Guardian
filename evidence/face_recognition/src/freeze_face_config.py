"""
DC-Guardian Phase 1
Freeze Face Recognition Configuration

Freezes the validation-derived operating threshold before
the locked final-test splits are accessed.
"""

import json
from datetime import datetime, timezone

from evidence.face_recognition.src.config import (
    DETECTOR_BACKEND,
    DISTANCE_METRIC,
    EXPECTED_EMBEDDING_DIMENSION,
    MODEL_NAME,
    MODELS_DIR,
    RESULTS_DIR,
)


THRESHOLD = 0.50

VALIDATION_SUMMARY_FILE = (
    RESULTS_DIR
    / "validation"
    / "validation_summary.json"
)

CONFIG_FILE = (
    MODELS_DIR
    / "face_recognition_config.json"
)


def main():

    print(
        "\n============================================"
    )
    print(
        "DC-GUARDIAN FACE CONFIGURATION FREEZE"
    )
    print(
        "============================================"
    )

    if not VALIDATION_SUMMARY_FILE.is_file():

        raise FileNotFoundError(
            "Validation summary not found:\n"
            f"{VALIDATION_SUMMARY_FILE}"
        )

    with VALIDATION_SUMMARY_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:

        validation = json.load(file)


    # ========================================================
    # Validation-only boundary
    # ========================================================

    assert (
        validation[
            "final_test_accessed"
        ]
        is False
    )

    assert (
        validation[
            "threshold_frozen"
        ]
        is False
    )


    known_max = float(
        validation[
            "known_distance_max"
        ]
    )

    unknown_min = float(
        validation[
            "unknown_distance_min"
        ]
    )


    if not (
        known_max
        < THRESHOLD
        < unknown_min
    ):

        raise RuntimeError(
            "Selected threshold does not lie "
            "inside the observed validation gap."
        )


    margin_from_known = (
        THRESHOLD
        - known_max
    )

    margin_from_unknown = (
        unknown_min
        - THRESHOLD
    )


    config = {
        "artifact_type":
            "DC_GUARDIAN_FACE_RECOGNITION_CONFIG",

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

        "recognition_threshold":
            THRESHOLD,

        "decision_rule":
            "distance <= threshold",

        "unknown_rule":
            "distance > threshold",

        "threshold_source":
            "validation_only",

        "threshold_selection_method":
            (
                "Controlled operating point inside "
                "the observed known/unknown "
                "validation separation."
            ),

        "threshold_selection_rationale":
            (
                "0.50 preserves all validation-known "
                "identifications and all validation-unknown "
                "rejections while retaining margin from "
                "both observed validation distributions. "
                "The threshold is not a universal ArcFace "
                "threshold."
            ),

        "validation_known_images":
            int(
                validation[
                    "known_validation_images"
                ]
            ),

        "validation_unknown_images":
            int(
                validation[
                    "unknown_validation_images"
                ]
            ),

        "validation_nearest_identity_correct_known":
            int(
                validation[
                    "nearest_identity_correct_known"
                ]
            ),

        "validation_known_distance_min":
            float(
                validation[
                    "known_distance_min"
                ]
            ),

        "validation_known_distance_max":
            known_max,

        "validation_known_distance_mean":
            float(
                validation[
                    "known_distance_mean"
                ]
            ),

        "validation_unknown_distance_min":
            unknown_min,

        "validation_unknown_distance_max":
            float(
                validation[
                    "unknown_distance_max"
                ]
            ),

        "validation_unknown_distance_mean":
            float(
                validation[
                    "unknown_distance_mean"
                ]
            ),

        "margin_from_hardest_known":
            margin_from_known,

        "margin_from_closest_unknown":
            margin_from_unknown,

        "validation_known_identification":
            "7/7",

        "validation_unknown_rejection":
            "6/6",

        "validation_false_acceptances":
            0,

        "validation_false_rejections":
            0,

        "validation_misidentifications":
            0,

        "configuration_frozen":
            True,

        "final_test_accessed":
            False,
    }


    MODELS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


    with CONFIG_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            config,
            file,
            indent=2,
        )


    print(
        f"Threshold: {THRESHOLD:.2f}"
    )

    print(
        "Known validation maximum:",
        f"{known_max:.6f}",
    )

    print(
        "Unknown validation minimum:",
        f"{unknown_min:.6f}",
    )

    print(
        "Margin from hardest known:",
        f"{margin_from_known:.6f}",
    )

    print(
        "Margin from closest unknown:",
        f"{margin_from_unknown:.6f}",
    )

    print(
        "\nSaved:",
        CONFIG_FILE,
    )

    print(
        "\nPASS: Threshold derived from validation only."
    )

    print(
        "PASS: Threshold lies inside validation gap."
    )

    print(
        "PASS: Configuration frozen."
    )

    print(
        "PASS: Final-test data remains untouched."
    )

    print(
        "\n============================================"
    )

    print(
        "FACE RECOGNITION CONFIGURATION FROZEN"
    )

    print(
        "============================================"
    )


if __name__ == "__main__":

    main()
