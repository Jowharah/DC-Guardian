from pathlib import Path

import pandas as pd


# ============================================================
# Paths
# ============================================================

PROCESSED_DIR = Path("data/processed")

# Development sample
SAMPLE_FEATURE_FILE = (
    PROCESSED_DIR / "ssh_features_2k_5min.csv"
)

SAMPLE_OUTPUT_FILE = (
    PROCESSED_DIR / "ssh_rule_results_2k.csv"
)

# Full OpenSSH dataset
FULL_FEATURE_FILE = (
    PROCESSED_DIR / "ssh_features_full_5min.csv"
)

FULL_OUTPUT_FILE = (
    PROCESSED_DIR / "ssh_rule_results_full.csv"
)


# ============================================================
# Initial rule thresholds
# ============================================================
#
# These are baseline experimental thresholds.
# They are NOT ground-truth attack labels.
#
# We will inspect their behavior and later evaluate them
# against controlled scenarios.

FAILED_LOGIN_THRESHOLD = 10

UNIQUE_USERS_THRESHOLD = 5

ROOT_RATIO_THRESHOLD = 0.80

BREAKIN_WARNING_THRESHOLD = 1


# ============================================================
# Analyze one source-IP window
# ============================================================

def analyze_window(
    row,
    failed_login_threshold=10
):

    triggered_rules = []
    evidence = []

    # --------------------------------------------------------
    # Rule 1: Repeated failed authentication
    # --------------------------------------------------------

    if row["failed_login_count"] >= failed_login_threshold:

        triggered_rules.append(
            "REPEATED_FAILURES"
        )

        evidence.append(
            f"{int(row['failed_login_count'])} "
            f"failed logins in 5 minutes"
        )


    # --------------------------------------------------------
    # Rule 2: Username enumeration
    # --------------------------------------------------------

    if row["unique_users"] >= UNIQUE_USERS_THRESHOLD:

        triggered_rules.append(
            "USERNAME_ENUMERATION"
        )

        evidence.append(
            f"{int(row['unique_users'])} "
            f"unique usernames attempted"
        )


    # --------------------------------------------------------
    # Rule 3: Root-focused attack
    # --------------------------------------------------------
    #
    # Require both:
    #   - multiple failures
    #   - high concentration on root
    #
    # This avoids flagging something simply because
    # 1 out of 1 failed attempts happened to target root.

    if (
        row["failed_login_count"] >= 5
        and
        row["root_attempt_ratio"] >= ROOT_RATIO_THRESHOLD
    ):

        triggered_rules.append(
            "ROOT_TARGETING"
        )

        evidence.append(
            f"{row['root_attempt_ratio']:.0%} "
            f"of failed attempts targeted root"
        )


    # --------------------------------------------------------
    # Supporting signal: OpenSSH break-in warning
    # --------------------------------------------------------
    #
    # A reverse-DNS break-in warning alone is not treated as
    # sufficient evidence of an anomaly.
    #
    # We preserve it as supporting evidence.

    has_breakin_warning = (
        row["breakin_warning_count"] >= 1
    )

    if has_breakin_warning:

        evidence.append(
            f"{int(row['breakin_warning_count'])} "
            f"OpenSSH break-in warning(s)"
        )
    
    # --------------------------------------------------------
    # Overall decision
    # --------------------------------------------------------

    rule_score = len(triggered_rules)


    if rule_score >= 1:

        prediction = "ANOMALOUS"

    elif has_breakin_warning:

        prediction = "SUSPICIOUS"

    else:

        prediction = "NORMAL"

    return pd.Series(
        {
            "prediction": prediction,
            "rule_score": rule_score,
            "triggered_rules": "; ".join(
                triggered_rules
            ),
            "evidence": "; ".join(
                evidence
            )
        }
    )


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":

    # ========================================================
    # Select dataset
    # ========================================================
    #
    # "sample" -> 2k development feature table
    # "full"   -> full OpenSSH feature table
    #
    # Each dataset writes to a separate result CSV.

    DATASET = "full"

    if DATASET == "sample":
        feature_file = SAMPLE_FEATURE_FILE
        output_file = SAMPLE_OUTPUT_FILE
        thresholds = [5, 10, 20]

    elif DATASET == "full":
        feature_file = FULL_FEATURE_FILE
        output_file = FULL_OUTPUT_FILE
        thresholds = [5, 10, 20, 50, 100, 150]

    else:
        raise ValueError(
            "DATASET must be 'sample' or 'full'."
        )

    if not feature_file.exists():
        raise FileNotFoundError(
            f"Feature file not found: {feature_file}"
        )

    print(f"Dataset: {DATASET}")
    print(f"Input:   {feature_file}")
    print(f"Output:  {output_file}")

    # ========================================================
    # Load feature table
    # ========================================================

    df = pd.read_csv(
        feature_file,
        parse_dates=[
            "window_start",
            "window_end"
        ]
    )

    print(
        f"Total source-IP windows: {len(df)}"
    )

    # ========================================================
    # Threshold sensitivity experiment
    # ========================================================

    print("\nFailed-login threshold sensitivity:")

    for threshold in thresholds:

        test_results = df.apply(
            lambda row: analyze_window(
                row,
                failed_login_threshold=threshold
            ),
            axis=1
        )

        counts = (
            test_results["prediction"]
            .value_counts()
        )

        normal_count = counts.get("NORMAL", 0)
        suspicious_count = counts.get("SUSPICIOUS", 0)
        anomalous_count = counts.get("ANOMALOUS", 0)

        anomalous_pct = (
            anomalous_count / len(df) * 100
        )

        print(
            f"\nThreshold >= {threshold} "
            f"failed logins / 5 min"
        )
        print(f"  NORMAL:     {normal_count}")
        print(f"  SUSPICIOUS: {suspicious_count}")
        print(
            f"  ANOMALOUS:  {anomalous_count} "
            f"({anomalous_pct:.2f}%)"
        )

    # ========================================================
    # Apply frozen Rule Baseline v1
    # ========================================================
    #
    # Threshold 10 is retained as the original security-rule
    # baseline. The sensitivity experiment above shows how
    # results change at other thresholds; it does not redefine
    # ground-truth attacks.

    results = df.apply(
        lambda row: analyze_window(
            row,
            failed_login_threshold=FAILED_LOGIN_THRESHOLD
        ),
        axis=1
    )

    df = pd.concat(
        [df, results],
        axis=1
    )

    # ========================================================
    # Summary
    # ========================================================

    print("\nPrediction counts:")

    prediction_counts = (
        df["prediction"].value_counts()
    )

    print(prediction_counts)

    print("\nPrediction percentages:")

    print(
        (
            prediction_counts / len(df) * 100
        )
        .round(2)
    )

    print("\nRule trigger counts:")

    all_rules = (
        df["triggered_rules"]
        .str.split("; ")
        .explode()
    )

    all_rules = all_rules[
        all_rules.notna()
        & (all_rules != "")
    ]

    print(
        all_rules.value_counts()
    )

    # ========================================================
    # Show top anomalous windows only
    # ========================================================
    #
    # The full dataset can contain thousands of alerts, so
    # avoid printing every anomalous row to the terminal.

    anomalous = (
        df[
            df["prediction"] == "ANOMALOUS"
        ]
        .sort_values(
            [
                "rule_score",
                "failed_login_count"
            ],
            ascending=False
        )
    )

    print("\nTop 25 anomalous windows:")

    print(
        anomalous[
            [
                "source_ip",
                "window_start",
                "failed_login_count",
                "unique_users",
                "root_attempt_ratio",
                "breakin_warning_count",
                "rule_score",
                "triggered_rules",
                "evidence"
            ]
        ]
        .head(25)
        .to_string(index=False)
    )

    # ========================================================
    # Show top suspicious windows
    # ========================================================

    suspicious_only = (
        df[
            df["prediction"] == "SUSPICIOUS"
        ]
        .sort_values(
            "breakin_warning_count",
            ascending=False
        )
    )

    print("\nTop 25 suspicious windows:")

    print(
        suspicious_only[
            [
                "source_ip",
                "window_start",
                "failed_login_count",
                "unique_users",
                "breakin_warning_count",
                "evidence"
            ]
        ]
        .head(25)
        .to_string(index=False)
    )

    # ========================================================
    # Save complete results
    # ========================================================

    df.to_csv(
        output_file,
        index=False
    )

    print(
        f"\nSaved rule results to: {output_file}"
    )
