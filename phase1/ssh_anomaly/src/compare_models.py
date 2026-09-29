from pathlib import Path

import pandas as pd


# ============================================================
# Paths
# ============================================================

PROCESSED_DIR = Path("data/processed")

# 2k development sample
SAMPLE_RULE_FILE = (
    PROCESSED_DIR / "ssh_rule_results_2k.csv"
)

SAMPLE_IF_FILE = (
    PROCESSED_DIR / "ssh_isolation_forest_raw_results_2k.csv"
)

SAMPLE_OUTPUT_FILE = (
    PROCESSED_DIR / "ssh_model_comparison_2k.csv"
)

# Full OpenSSH dataset
FULL_RULE_FILE = (
    PROCESSED_DIR / "ssh_rule_results_full.csv"
)

FULL_IF_FILE = (
    PROCESSED_DIR / "ssh_isolation_forest_raw_results_full.csv"
)

FULL_OUTPUT_FILE = (
    PROCESSED_DIR / "ssh_model_comparison_full.csv"
)


# ============================================================
# Agreement classification
# ============================================================

def agreement_type(row):

    rule = row["prediction"]
    model = row["if_prediction"]

    if rule == "ANOMALOUS" and model == "ANOMALOUS":
        return "BOTH_ANOMALOUS"

    if rule == "ANOMALOUS" and model == "NORMAL":
        return "RULE_ONLY"

    if rule == "SUSPICIOUS" and model == "ANOMALOUS":
        return "SUSPICIOUS_AND_IF_ANOMALOUS"

    if rule == "SUSPICIOUS" and model == "NORMAL":
        return "RULE_SUSPICIOUS_ONLY"

    if rule == "NORMAL" and model == "ANOMALOUS":
        return "IF_ONLY"

    return "BOTH_NORMAL"


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":

    # ========================================================
    # Select dataset
    # ========================================================

    DATASET = "full"

    if DATASET == "sample":
        rule_file = SAMPLE_RULE_FILE
        if_file = SAMPLE_IF_FILE
        output_file = SAMPLE_OUTPUT_FILE

    elif DATASET == "full":
        rule_file = FULL_RULE_FILE
        if_file = FULL_IF_FILE
        output_file = FULL_OUTPUT_FILE

    else:
        raise ValueError(
            "DATASET must be 'sample' or 'full'."
        )

    for file_path in [rule_file, if_file]:

        if not file_path.exists():
            raise FileNotFoundError(
                f"Required result file not found: {file_path}"
            )

    print(f"Dataset: {DATASET}")
    print(f"Rule results: {rule_file}")
    print(f"IF results:   {if_file}")
    print(f"Output:       {output_file}")

    # ========================================================
    # Load results
    # ========================================================

    rules = pd.read_csv(
        rule_file,
        parse_dates=[
            "window_start",
            "window_end"
        ]
    )

    isolation = pd.read_csv(
        if_file,
        parse_dates=[
            "window_start",
            "window_end"
        ]
    )

    print(
        f"\nRule windows: {len(rules)}"
    )

    print(
        f"Isolation Forest windows: {len(isolation)}"
    )

    # ========================================================
    # Keep only IF-specific columns before merge
    # ========================================================

    if_results = isolation[
        [
            "source_ip",
            "window_start",
            "if_prediction",
            "if_decision_score",
            "if_anomaly_score"
        ]
    ].copy()

    # ========================================================
    # Merge using source IP + 5-minute window
    # ========================================================

    comparison = rules.merge(
        if_results,
        on=[
            "source_ip",
            "window_start"
        ],
        how="inner",
        validate="one_to_one"
    )

    print(
        f"Compared windows: {len(comparison)}"
    )

    if len(comparison) != len(rules):
        print(
            "\nWARNING: Not every rule window matched "
            "an Isolation Forest window."
        )

    # ========================================================
    # Agreement categories
    # ========================================================

    comparison["agreement"] = (
        comparison.apply(
            agreement_type,
            axis=1
        )
    )

    # ========================================================
    # Summary counts
    # ========================================================

    print(
        "\n============================================"
    )
    print(
        "FULL MODEL AGREEMENT SUMMARY"
    )
    print(
        "============================================"
    )

    agreement_counts = (
        comparison["agreement"]
        .value_counts()
    )

    print("\nAgreement counts:")

    print(
        agreement_counts
    )

    print("\nAgreement percentages:")

    print(
        (
            agreement_counts
            / len(comparison)
            * 100
        )
        .round(2)
    )

    # ========================================================
    # Cross-tab
    # ========================================================

    print(
        "\nRule vs Isolation Forest cross-tab:"
    )

    cross_tab = pd.crosstab(
        comparison["prediction"],
        comparison["if_prediction"],
        margins=True
    )

    print(
        cross_tab.to_string()
    )

    # ========================================================
    # Special case:
    # Rule SUSPICIOUS + IF ANOMALOUS
    # ========================================================

    suspicious_if = comparison[
        comparison["agreement"]
        == "SUSPICIOUS_AND_IF_ANOMALOUS"
    ].sort_values(
        "if_anomaly_score",
        ascending=False
    )

    print(
        "\n============================================"
    )
    print(
        "RULE SUSPICIOUS + IF ANOMALOUS"
    )
    print(
        "============================================"
    )

    print(
        f"Count: {len(suspicious_if)}"
    )

    if suspicious_if.empty:

        print(
            "No windows in this category."
        )

    else:

        print(
            suspicious_if[
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
                    "rule_score",
                    "triggered_rules",
                    "evidence",
                    "if_anomaly_score"
                ]
            ]
            .head(25)
            .to_string(index=False)
        )

    # ========================================================
    # IF-only anomalies
    # ========================================================

    if_only = comparison[
        comparison["agreement"] == "IF_ONLY"
    ].sort_values(
        "if_anomaly_score",
        ascending=False
    )

    print(
        "\n============================================"
    )
    print(
        "IF-ONLY ANOMALIES"
    )
    print(
        "============================================"
    )

    print(
        f"Count: {len(if_only)}"
    )

    if if_only.empty:

        print(
            "No IF-only anomalies."
        )

    else:

        print(
            if_only[
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
                    "if_anomaly_score"
                ]
            ]
            .head(25)
            .to_string(index=False)
        )

    # ========================================================
    # Rule-only anomalies
    # ========================================================

    rule_only = comparison[
        comparison["agreement"] == "RULE_ONLY"
    ].sort_values(
        [
            "rule_score",
            "failed_login_count"
        ],
        ascending=False
    )

    print(
        "\n============================================"
    )
    print(
        "RULE-ONLY ANOMALIES"
    )
    print(
        "============================================"
    )

    print(
        f"Count: {len(rule_only)}"
    )

    if rule_only.empty:

        print(
            "No rule-only anomalies."
        )

    else:

        print(
            rule_only[
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
                    "if_anomaly_score"
                ]
            ]
            .head(25)
            .to_string(index=False)
        )

    # ========================================================
    # Both anomalous
    # ========================================================

    both_anomalous = comparison[
        comparison["agreement"]
        == "BOTH_ANOMALOUS"
    ].sort_values(
        "if_anomaly_score",
        ascending=False
    )

    print(
        "\n============================================"
    )
    print(
        "BOTH MODELS ANOMALOUS"
    )
    print(
        "============================================"
    )

    print(
        f"Count: {len(both_anomalous)}"
    )

    print(
        both_anomalous[
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
                "if_anomaly_score"
            ]
        ]
        .head(25)
        .to_string(index=False)
    )

    # ========================================================
    # Save complete comparison
    # ========================================================

    comparison.to_csv(
        output_file,
        index=False
    )

    print(
        f"\nSaved complete model comparison to: "
        f"{output_file}"
    )
