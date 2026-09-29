"""
DC-Guardian Phase 1
Optimized GRU Full-Q4 Inference

Scores the complete GRU-eligible Q4 population using
vectorized NumPy sequence extraction.

Development only:
    Q4 = validation
    Q1 2026 = LOCKED
"""

import time

import numpy as np
import pandas as pd
import torch

from phase1.predictive_maintenance.src.config import (
    FEATURE_DATA_DIR,
)

from phase1.predictive_maintenance.src.gru.config import (
    GRU_CLIP_VALUE,
    GRU_EVALUATION_DIR,
    GRU_INDEX_DIR,
    GRU_LOG1P_FEATURES,
    GRU_MODEL_FILE,
    GRU_NORMALIZATION_FILE,
    GRU_Q4_EVALUATION_METADATA_FILE,
    GRU_Q4_PROBABILITY_FILE,
    GRU_SEQUENCE_LENGTH,
    GRU_SMART_FEATURES,
    GRU_VALIDATION_PERIOD,
)

from phase1.predictive_maintenance.src.gru.model import (
    MaintenanceGRU,
)


# ============================================================
# Runtime configuration
# ============================================================

# Number of sequences constructed at once on CPU.
#
# 50,000 x 30 x 8 x float32
# ~= 48 MB before temporary arrays.
#
# Safe for a normal workstation and much faster than
# constructing one sequence at a time.
CPU_CHUNK_SIZE = 50_000


# GPU inference batch inside each CPU chunk.
GPU_BATCH_SIZE = 4096


# ============================================================
# Load source period
# ============================================================

def load_period(
    period,
):

    file_path = (
        FEATURE_DATA_DIR
        / f"{period}_features.parquet"
    )

    columns = (
        [
            "date",
            "serial_number",
        ]
        + GRU_SMART_FEATURES
    )

    df = pd.read_parquet(
        file_path,
        columns=columns,
    )

    df["date"] = pd.to_datetime(
        df["date"],
        errors="raise",
    )

    df["serial_number"] = (
        df["serial_number"]
        .astype(str)
    )

    return df


# ============================================================
# Batch preprocessing
# ============================================================

def preprocess_sequences(
    x,
    median,
    scale,
    log1p_mask,
):

    x = np.asarray(
        x,
        dtype=np.float32,
    ).copy()


    # --------------------------------------------------------
    # log1p selected SMART count channels
    # --------------------------------------------------------

    for channel in np.flatnonzero(
        log1p_mask
    ):

        values = x[
            :,
            :,
            channel
        ]

        values[
            values < 0
        ] = np.nan

        x[
            :,
            :,
            channel
        ] = np.log1p(
            values
        )


    # --------------------------------------------------------
    # Training-median imputation
    # --------------------------------------------------------

    for channel in range(
        x.shape[2]
    ):

        values = x[
            :,
            :,
            channel
        ]

        missing = ~np.isfinite(
            values
        )

        if missing.any():

            values[
                missing
            ] = median[
                channel
            ]


    # --------------------------------------------------------
    # Training-derived robust normalization
    # --------------------------------------------------------

    x = (
        x
        - median[
            None,
            None,
            :
        ]
    ) / scale[
        None,
        None,
        :
    ]


    # --------------------------------------------------------
    # Extreme-value clipping
    # --------------------------------------------------------

    np.clip(
        x,
        -GRU_CLIP_VALUE,
        GRU_CLIP_VALUE,
        out=x,
    )


    return x


# ============================================================
# GPU scoring
# ============================================================

@torch.inference_mode()
def score_sequences(
    model,
    sequences,
    device,
):

    output = np.empty(
        len(sequences),
        dtype=np.float32,
    )


    for start in range(
        0,
        len(sequences),
        GPU_BATCH_SIZE,
    ):

        end = min(
            start
            + GPU_BATCH_SIZE,
            len(sequences),
        )


        tensor = torch.from_numpy(
            sequences[
                start:end
            ]
        ).to(
            device,
            non_blocking=True,
        )


        logits = model(
            tensor
        )


        probability = torch.sigmoid(
            logits
        )


        output[
            start:end
        ] = (
            probability
            .cpu()
            .numpy()
        )


    return output


# ============================================================
# Main
# ============================================================

def main():

    if not torch.cuda.is_available():

        raise RuntimeError(
            "CUDA is required for full Q4 GRU inference."
        )


    device = torch.device(
        "cuda"
    )


    start_time = time.perf_counter()


    print(
        "\n============================================"
    )
    print(
        "DC-GUARDIAN OPTIMIZED GRU FULL Q4 INFERENCE"
    )
    print(
        "============================================"
    )


    print(
        "GPU:",
        torch.cuda.get_device_name(0)
    )

    print(
        "Validation period:",
        GRU_VALIDATION_PERIOD
    )

    print(
        "CPU chunk size:",
        f"{CPU_CHUNK_SIZE:,}"
    )

    print(
        "GPU batch size:",
        f"{GPU_BATCH_SIZE:,}"
    )

    print(
        "2026 Q1: LOCKED"
    )


    # ========================================================
    # Load frozen model
    # ========================================================

    checkpoint = torch.load(
        GRU_MODEL_FILE,
        map_location=device,
    )


    model = MaintenanceGRU().to(
        device
    )


    model.load_state_dict(
        checkpoint[
            "state_dict"
        ]
    )


    model.eval()


    print(
        "Checkpoint epoch:",
        checkpoint[
            "best_epoch"
        ]
    )


    # ========================================================
    # Training-only normalization
    # ========================================================

    normalization = np.load(
        GRU_NORMALIZATION_FILE
    )


    saved_features = (
        normalization[
            "features"
        ]
        .astype(str)
        .tolist()
    )


    if saved_features != GRU_SMART_FEATURES:

        raise RuntimeError(
            "Normalization feature order mismatch."
        )


    median = (
        normalization[
            "median"
        ]
        .astype(
            np.float32
        )
    )


    scale = (
        normalization[
            "scale"
        ]
        .astype(
            np.float32
        )
    )


    log1p_mask = np.asarray(
        [
            feature
            in GRU_LOG1P_FEATURES
            for feature
            in GRU_SMART_FEATURES
        ],
        dtype=bool,
    )


    # ========================================================
    # Load Q4 sequence index
    # ========================================================

    index_file = (
        GRU_INDEX_DIR
        / (
            f"{GRU_VALIDATION_PERIOD}"
            "_sequence_index.parquet"
        )
    )


    sequence_index = pd.read_parquet(
        index_file
    )


    total_sequences = len(
        sequence_index
    )


    positive_sequences = int(
        sequence_index[
            "label"
        ]
        .sum()
    )


    positive_drives = (
        sequence_index.loc[
            sequence_index[
                "label"
            ].eq(1),
            "serial_number",
        ]
        .nunique()
    )


    print(
        "\nEligible Q4 sequences:",
        f"{total_sequences:,}"
    )

    print(
        "Positive sequences:",
        f"{positive_sequences:,}"
    )

    print(
        "Positive drives:",
        f"{positive_drives:,}"
    )


    # ========================================================
    # Load Q3 tail + Q4 exactly as index builder did
    # ========================================================

    print(
        "\nLoading Q3 history + Q4..."
    )


    q3 = load_period(
        "2025_Q3"
    )


    q4 = load_period(
        "2025_Q4"
    )


    q3_end = q3[
        "date"
    ].max()


    history_start = (
        q3_end
        - pd.Timedelta(
            days=28
        )
    )


    q3_tail = (
        q3[
            q3[
                "date"
            ]
            >= history_start
        ]
        .copy()
    )


    combined = pd.concat(
        [
            q3_tail,
            q4,
        ],
        ignore_index=True,
    )


    combined = (
        combined
        .sort_values(
            [
                "serial_number",
                "date",
            ]
        )
        .reset_index(
            drop=True
        )
    )


    del q3
    del q4
    del q3_tail


    print(
        "Combined history rows:",
        f"{len(combined):,}"
    )


    # ========================================================
    # Critical positional integrity check
    # ========================================================

    end_positions = (
        sequence_index[
            "end_position"
        ]
        .to_numpy(
            dtype=np.int64
        )
    )


    start_positions = (
        sequence_index[
            "start_position"
        ]
        .to_numpy(
            dtype=np.int64
        )
    )


    expected_start = (
        end_positions
        - GRU_SEQUENCE_LENGTH
        + 1
    )


    if not np.array_equal(
        start_positions,
        expected_start,
    ):

        raise AssertionError(
            "Stored GRU sequence positions "
            "do not match 30-observation contract."
        )


    if (
        end_positions.min() < 0
        or
        end_positions.max() >= len(
            combined
        )
    ):

        raise AssertionError(
            "Stored sequence positions are outside "
            "combined Q3/Q4 frame."
        )


    # --------------------------------------------------------
    # Verify stored endpoints against reconstructed frame
    # --------------------------------------------------------

    endpoint_dates = (
        combined[
            "date"
        ]
        .to_numpy()[
            end_positions
        ]
    )


    expected_dates = pd.to_datetime(
        sequence_index[
            "endpoint_date"
        ]
    ).to_numpy()


    if not np.array_equal(
        endpoint_dates,
        expected_dates,
    ):

        raise AssertionError(
            "Endpoint-date positional integrity failed."
        )


    endpoint_serials = (
        combined[
            "serial_number"
        ]
        .to_numpy()[
            end_positions
        ]
        .astype(str)
    )


    expected_serials = (
        sequence_index[
            "serial_number"
        ]
        .astype(str)
        .to_numpy()
    )


    if not np.array_equal(
        endpoint_serials,
        expected_serials,
    ):

        raise AssertionError(
            "Endpoint-drive positional integrity failed."
        )


    print(
        "PASS: Stored Q4 sequence positions verified."
    )


    # ========================================================
    # Convert SMART columns ONCE
    # ========================================================

    print(
        "Building contiguous SMART matrix..."
    )


    smart_frame = combined[
        GRU_SMART_FEATURES
    ].apply(
        pd.to_numeric,
        errors="coerce",
    )


    smart_matrix = smart_frame.to_numpy(
        dtype=np.float32
    )


    del smart_frame
    del combined


    print(
        "SMART matrix shape:",
        smart_matrix.shape
    )


    # ========================================================
    # Vectorized relative offsets
    # ========================================================

    offsets = np.arange(
        -GRU_SEQUENCE_LENGTH + 1,
        1,
        dtype=np.int64,
    )


    # ========================================================
    # Probability output
    # ========================================================

    GRU_EVALUATION_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


    probabilities = (
        np.lib.format.open_memmap(
            GRU_Q4_PROBABILITY_FILE,
            mode="w+",
            dtype=np.float32,
            shape=(
                total_sequences,
            ),
        )
    )


    # ========================================================
    # Chunked vectorized inference
    # ========================================================

    print(
        "\nStarting vectorized Q4 inference..."
    )


    next_progress = 1_000_000


    for chunk_start in range(
        0,
        total_sequences,
        CPU_CHUNK_SIZE,
    ):

        chunk_end = min(
            chunk_start
            + CPU_CHUNK_SIZE,
            total_sequences,
        )


        chunk_end_positions = (
            end_positions[
                chunk_start:
                chunk_end
            ]
        )


        # ----------------------------------------------------
        # Shape:
        #
        #   chunk_size x 30
        #
        # Each row contains the 30 global row positions
        # belonging to one GRU sequence.
        # ----------------------------------------------------

        position_matrix = (
            chunk_end_positions[
                :,
                None
            ]
            + offsets[
                None,
                :
            ]
        )


        # ----------------------------------------------------
        # NumPy advanced indexing:
        #
        #   (chunk, 30)
        #       ↓
        #   (chunk, 30, 8)
        # ----------------------------------------------------

        raw_sequences = smart_matrix[
            position_matrix
        ]


        processed = preprocess_sequences(
            raw_sequences,
            median,
            scale,
            log1p_mask,
        )


        chunk_probabilities = score_sequences(
            model,
            processed,
            device,
        )


        probabilities[
            chunk_start:
            chunk_end
        ] = chunk_probabilities


        scored = chunk_end


        if (
            scored >= next_progress
            or
            scored == total_sequences
        ):

            elapsed = (
                time.perf_counter()
                - start_time
            )


            rate = (
                scored
                / elapsed
            )


            remaining = (
                total_sequences
                - scored
            )


            eta_seconds = (
                remaining
                / rate
                if rate > 0
                else float("nan")
            )


            print(
                "Scored:",
                f"{scored:,}",
                "/",
                f"{total_sequences:,}",
                f"({scored / total_sequences:.1%})",
                "|",
                f"{rate:,.0f} seq/s",
                "| ETA:",
                f"{eta_seconds / 60:.1f} min"
            )


            while (
                next_progress
                <= scored
            ):

                next_progress += (
                    1_000_000
                )


    probabilities.flush()


    # ========================================================
    # Final integrity
    # ========================================================

    if not np.isfinite(
        probabilities
    ).all():

        raise AssertionError(
            "Non-finite Q4 GRU probabilities."
        )


    if (
        probabilities.min() < 0
        or
        probabilities.max() > 1
    ):

        raise AssertionError(
            "Invalid Q4 GRU probability range."
        )


    # ========================================================
    # Stable metadata
    # ========================================================

    evaluation_metadata = (
        sequence_index[
            [
                "serial_number",
                "endpoint_date",
                "label",
            ]
        ]
        .copy()
    )


    evaluation_metadata[
        "evaluation_position"
    ] = np.arange(
        total_sequences,
        dtype=np.int64,
    )


    evaluation_metadata = (
        evaluation_metadata[
            [
                "evaluation_position",
                "serial_number",
                "endpoint_date",
                "label",
            ]
        ]
    )


    evaluation_metadata.to_parquet(
        GRU_Q4_EVALUATION_METADATA_FILE,
        index=False,
    )


    elapsed = (
        time.perf_counter()
        - start_time
    )


    print(
        "\n============================================"
    )
    print(
        "OPTIMIZED GRU FULL Q4 INFERENCE SUMMARY"
    )
    print(
        "============================================"
    )


    print(
        "Sequences scored:",
        f"{total_sequences:,}"
    )

    print(
        "Runtime:",
        f"{elapsed / 60:.2f} minutes"
    )

    print(
        "Average throughput:",
        f"{total_sequences / elapsed:,.0f} sequences/sec"
    )

    print(
        "Probability range:",
        f"{float(probabilities.min()):.6f}",
        "->",
        f"{float(probabilities.max()):.6f}"
    )

    print(
        "Probability file:",
        GRU_Q4_PROBABILITY_FILE
    )

    print(
        "Metadata file:",
        GRU_Q4_EVALUATION_METADATA_FILE
    )


    print(
        "\nPASS: All eligible Q4 sequences scored."
    )

    print(
        "PASS: Training normalization reused."
    )

    print(
        "PASS: Stored sequence positions verified."
    )

    print(
        "PASS: 2026 Q1 not accessed."
    )


    print(
        "\n============================================"
    )
    print(
        "OPTIMIZED GRU FULL Q4 INFERENCE PASSED"
    )
    print(
        "============================================"
    )


if __name__ == "__main__":
    main()