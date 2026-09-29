"""
DC-Guardian Phase 1
GRU Training Normalization

Computes robust normalization statistics using TRAINING
sequences only.

No validation or final-test observations are used.

For each SMART channel:
    center = median
    scale  = IQR = Q75 - Q25

Missing values are represented separately and are not used
when estimating statistics.
"""

import numpy as np

from phase1.predictive_maintenance.src.gru.config import (
    GRU_NORMALIZATION_FILE,
    GRU_SMART_FEATURES,
    GRU_TRAIN_SEQUENCE_FILE,
)

from phase1.predictive_maintenance.src.gru.config import (
    GRU_LOG1P_FEATURES,
    GRU_NORMALIZATION_FILE,
    GRU_SMART_FEATURES,
    GRU_TRAIN_SEQUENCE_FILE,
)



def main():

    print(
        "\n============================================"
    )
    print(
        "DC-GUARDIAN GRU NORMALIZATION"
    )
    print(
        "============================================"
    )

    if not GRU_TRAIN_SEQUENCE_FILE.exists():

        raise FileNotFoundError(
            f"Training sequence store missing: "
            f"{GRU_TRAIN_SEQUENCE_FILE}"
        )


    sequences = np.load(
        GRU_TRAIN_SEQUENCE_FILE,
        mmap_mode="r",
    )


    print(
        "Training tensor:",
        sequences.shape
    )


    if sequences.ndim != 3:

        raise AssertionError(
            "Expected three-dimensional GRU tensor."
        )


    if sequences.shape[2] != len(
        GRU_SMART_FEATURES
    ):

        raise AssertionError(
            "SMART channel count mismatch."
        )


    medians = []

    q25_values = []

    q75_values = []

    scales = []

    missing_rates = []


    # ========================================================
    # Calculate each channel independently
    # ========================================================

    for channel_index, feature in enumerate(
        GRU_SMART_FEATURES
    ):

        print(
            f"\nAnalyzing {feature}..."
        )


        values = np.asarray(
            sequences[
                :,
                :,
                channel_index,
            ]
        ).reshape(-1)

        # ========================================================
        # Frozen feature transformation
        # ========================================================

        if feature in GRU_LOG1P_FEATURES:

            # SMART raw counts should be non-negative.
            # Invalid negative values are treated as missing.
            values = values.copy()

            values[
                values < 0
            ] = np.nan

            values = np.log1p(
                values
            )


        finite = values[
            np.isfinite(values)
        ]


        if len(finite) == 0:

            raise RuntimeError(
                f"No finite training values "
                f"for {feature}."
            )


        median = float(
            np.median(
                finite
            )
        )


        q25 = float(
            np.percentile(
                finite,
                25,
            )
        )


        q75 = float(
            np.percentile(
                finite,
                75,
            )
        )


        iqr = (
            q75
            - q25
        )


        # Constant / near-constant channels must not
        # create division by zero.
        scale = (
            float(iqr)
            if iqr > 0
            else 1.0
        )


        missing_rate = (
            1.0
            - (
                len(finite)
                / len(values)
            )
        )


        medians.append(
            median
        )

        q25_values.append(
            q25
        )

        q75_values.append(
            q75
        )

        scales.append(
            scale
        )

        missing_rates.append(
            missing_rate
        )


        print(
            "  median:",
            median
        )

        print(
            "  q25:",
            q25
        )

        print(
            "  q75:",
            q75
        )

        print(
            "  scale:",
            scale
        )

        print(
            "  missing:",
            f"{missing_rate:.4%}"
        )


    # ========================================================
    # Save training-only normalization contract
    # ========================================================

    np.savez(
        GRU_NORMALIZATION_FILE,

        features=np.asarray(
            GRU_SMART_FEATURES
        ),

        median=np.asarray(
            medians,
            dtype=np.float32,
        ),

        q25=np.asarray(
            q25_values,
            dtype=np.float32,
        ),

        q75=np.asarray(
            q75_values,
            dtype=np.float32,
        ),

        scale=np.asarray(
            scales,
            dtype=np.float32,
        ),

        missing_rate=np.asarray(
            missing_rates,
            dtype=np.float32,
        ),
    )


    print(
        "\n============================================"
    )
    print(
        "GRU NORMALIZATION SUMMARY"
    )
    print(
        "============================================"
    )


    for index, feature in enumerate(
        GRU_SMART_FEATURES
    ):

        print(
            f"{feature:<20} "
            f"median={medians[index]:>12.3f} "
            f"scale={scales[index]:>12.3f} "
            f"missing={missing_rates[index]:.4%}"
        )


    print(
        "\nSaved:",
        GRU_NORMALIZATION_FILE
    )


    print(
        "\nPASS: Statistics derived from "
        "training sequences only."
    )


    print(
        "\n============================================"
    )
    print(
        "GRU NORMALIZATION PASSED"
    )
    print(
        "============================================"
    )


if __name__ == "__main__":
    main()