from pathlib import Path

import pandas as pd


# ============================================================
# Paths
# ============================================================

PROCESSED_DIR = Path("data/processed")

RULE_FILE = (
    PROCESSED_DIR / "ssh_rule_results_full.csv"
)

IF_FILE = (
    PROCESSED_DIR / "ssh_isolation_forest_raw_results_full.csv"
)

AE_FILE = (
    PROCESSED_DIR / "ssh_autoencoder_log_results_full.csv"
)

OUTPUT_FILE = (
    PROCESSED_DIR / "ssh_final_model_comparison.csv"
)


# ============================================================
# Load result files
# ============================================================

def load_results():

    for file_path in [
        RULE_FILE,
        IF_FILE,
        AE_FILE
    ]:
        if not file_path.exists():
            raise FileNotFoundError(
                f"Required file not found: {file_path}"
            )

    rules = pd.read_csv(
        RULE_FILE,
        parse_dates=[
            "window_start",
            "window_end"
        ]
    )

    isolation = pd.read_csv(
        IF_FILE,
        parse_dates=[
            "window_start",
            "window_end"
        ]
    )

    autoencoder = pd.read_csv(
        AE_FILE,
        parse_dates=[
            "window_start",
            "window_end"
        ]
    )

    print(f"Rule windows:        {len(rules)}")
    print(f"Isolation windows:   {len(isolation)}")
    print(f"Autoencoder windows: {len(autoencoder)}")

    return rules, isolation, autoencoder


# ============================================================
# Build final comparison
# ============================================================

def build_comparison(
    rules,
    isolation,
    autoencoder
):

    keys = [
        "source_ip",
        "window_start"
    ]

    # Rule file is the evidence/base table.
    rule_columns = [
        "source_ip",
        "window_start",
        "window_end",
        "failed_login_count",
        "successful_login_count",
        "invalid_user_count",
        "unique_users",
        "failure_ratio",
        "root_attempt_ratio",
        "breakin_warning_count",
        "disconnect_count",
        "no_identification_count",
        "success_after_failures",
        "prediction",
        "rule_score",
        "triggered_rules",
        "evidence"
    ]

    # Keep only columns that actually exist, so the script is
    # robust to optional evidence fields.
    rule_columns = [
        column
        for column in rule_columns
        if column in rules.columns
    ]

    base = rules[
        rule_columns
    ].copy()

    if_data = isolation[
        [
            "source_ip",
            "window_start",
            "if_prediction",
            "if_anomaly_score"
        ]
    ].copy()

    ae_data = autoencoder[
        [
            "source_ip",
            "window_start",
            "ae_prediction",
            "ae_reconstruction_error"
        ]
    ].copy()

    comparison = base.merge(
        if_data,
        on=keys,
        how="inner",
        validate="one_to_one"
    )

    comparison = comparison.merge(
        ae_data,
        on=keys,
        how="inner",
        validate="one_to_one"
    )

    print(
        f"Compared windows:    {len(comparison)}"
    )

    expected = len(rules)

    if len(comparison) != expected:
        raise ValueError(
            "Final comparison did not preserve all rule windows. "
            f"Expected {expected}, got {len(comparison)}."
        )

    return comparison


# ============================================================
# Add detector votes
# ============================================================

def add_detector_votes(
    comparison
):

    # Only a strong rule ANOMALOUS result counts as a vote.
    # Rule SUSPICIOUS remains contextual evidence.
    comparison["rule_vote"] = (
        comparison["prediction"]
        .eq("ANOMALOUS")
        .astype(int)
    )

    comparison["if_vote"] = (
        comparison["if_prediction"]
        .eq("ANOMALOUS")
        .astype(int)
    )

    comparison["ae_vote"] = (
        comparison["ae_prediction"]
        .eq("ANOMALOUS")
        .astype(int)
    )

    comparison["anomaly_votes"] = (
        comparison[
            [
                "rule_vote",
                "if_vote",
                "ae_vote"
            ]
        ]
        .sum(axis=1)
    )

    comparison["consensus"] = (
        comparison["anomaly_votes"]
        .map(
            {
                0: "0_OF_3",
                1: "1_OF_3",
                2: "2_OF_3",
                3: "3_OF_3"
            }
        )
    )

    return comparison


# ============================================================
# Add exact detector combination
# ============================================================

def detector_combination(row):

    detectors = []

    if row["rule_vote"] == 1:
        detectors.append("RULE")

    if row["if_vote"] == 1:
        detectors.append("IF")

    if row["ae_vote"] == 1:
        detectors.append("AE")

    if not detectors:
        return "NONE"

    return "+".join(detectors)


# ============================================================
# Print final summaries
# ============================================================

def print_summaries(
    comparison
):

    print(
        "\n============================================"
    )
    print(
        "THREE-MODEL CONSENSUS"
    )
    print(
        "============================================"
    )

    consensus_counts = (
        comparison["consensus"]
        .value_counts()
        .reindex(
            [
                "3_OF_3",
                "2_OF_3",
                "1_OF_3",
                "0_OF_3"
            ],
            fill_value=0
        )
    )

    print("\nConsensus counts:")
    print(consensus_counts)

    print("\nConsensus percentages:")

    print(
        (
            consensus_counts
            / len(comparison)
            * 100
        )
        .round(2)
    )

    print(
        "\n============================================"
    )
    print(
        "EXACT DETECTOR COMBINATIONS"
    )
    print(
        "============================================"
    )

    combination_counts = (
        comparison["detector_combination"]
        .value_counts()
    )

    print(combination_counts)

    print("\nCombination percentages:")

    print(
        (
            combination_counts
            / len(comparison)
            * 100
        )
        .round(2)
    )

    # --------------------------------------------------------
    # Deep-learning added-value category
    # --------------------------------------------------------

    ae_only = comparison[
        comparison["detector_combination"]
        == "AE"
    ].sort_values(
        "ae_reconstruction_error",
        ascending=False
    )

    print(
        "\n============================================"
    )
    print(
        "AUTOENCODER-ONLY ANOMALIES"
    )
    print(
        "============================================"
    )

    print(
        f"Count: {len(ae_only)}"
    )

    if not ae_only.empty:

        print(
            ae_only[
                [
                    "source_ip",
                    "window_start",
                    "failed_login_count",
                    "invalid_user_count",
                    "unique_users",
                    "failure_ratio",
                    "root_attempt_ratio",
                    "breakin_warning_count",
                    "disconnect_count",
                    "no_identification_count",
                    "prediction",
                    "if_prediction",
                    "ae_reconstruction_error"
                ]
            ]
            .head(25)
            .to_string(index=False)
        )

    # --------------------------------------------------------
    # All three detectors agree
    # --------------------------------------------------------

    all_three = comparison[
        comparison["consensus"]
        == "3_OF_3"
    ].sort_values(
        [
            "rule_score",
            "ae_reconstruction_error"
        ],
        ascending=False
    )

    print(
        "\n============================================"
    )
    print(
        "ALL THREE DETECTORS ANOMALOUS"
    )
    print(
        "============================================"
    )

    print(
        f"Count: {len(all_three)}"
    )

    if not all_three.empty:

        print(
            all_three[
                [
                    "source_ip",
                    "window_start",
                    "failed_login_count",
                    "invalid_user_count",
                    "unique_users",
                    "root_attempt_ratio",
                    "breakin_warning_count",
                    "rule_score",
                    "triggered_rules",
                    "if_anomaly_score",
                    "ae_reconstruction_error"
                ]
            ]
            .head(25)
            .to_string(index=False)
        )

    # --------------------------------------------------------
    # Exactly two detectors
    # --------------------------------------------------------

    two_votes = comparison[
        comparison["consensus"]
        == "2_OF_3"
    ]

    print(
        "\n============================================"
    )
    print(
        "TWO-OF-THREE BREAKDOWN"
    )
    print(
        "============================================"
    )

    print(
        two_votes[
            "detector_combination"
        ]
        .value_counts()
    )

    # --------------------------------------------------------
    # Exactly one detector
    # --------------------------------------------------------

    one_vote = comparison[
        comparison["consensus"]
        == "1_OF_3"
    ]

    print(
        "\n============================================"
    )
    print(
        "ONE-OF-THREE BREAKDOWN"
    )
    print(
        "============================================"
    )

    print(
        one_vote[
            "detector_combination"
        ]
        .value_counts()
    )

    # --------------------------------------------------------
    # Rule suspicious context
    # --------------------------------------------------------

    suspicious = comparison[
        comparison["prediction"]
        == "SUSPICIOUS"
    ]

    print(
        "\n============================================"
    )
    print(
        "RULE-SUSPICIOUS CONTEXT"
    )
    print(
        "============================================"
    )

    print(
        f"Rule-suspicious windows: "
        f"{len(suspicious)}"
    )

    if not suspicious.empty:

        print(
            "\nDetector combinations inside "
            "rule-suspicious windows:"
        )

        print(
            suspicious[
                "detector_combination"
            ]
            .value_counts()
        )


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":

    rules, isolation, autoencoder = (
        load_results()
    )

    comparison = build_comparison(
        rules,
        isolation,
        autoencoder
    )

    comparison = add_detector_votes(
        comparison
    )

    comparison[
        "detector_combination"
    ] = comparison.apply(
        detector_combination,
        axis=1
    )

    print_summaries(
        comparison
    )

    # Sort for easier inspection in CSV:
    # strongest consensus first, then strongest AE score.
    comparison = comparison.sort_values(
        [
            "anomaly_votes",
            "ae_reconstruction_error",
            "if_anomaly_score"
        ],
        ascending=[
            False,
            False,
            False
        ]
    )

    comparison.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print(
        f"\nSaved final three-model comparison to: "
        f"{OUTPUT_FILE}"
    )
