from pathlib import Path

import pandas as pd



# ============================================================
# Paths
# ============================================================

PROCESSED_DIR = Path(
    "data/processed"
)

# Development sample
SAMPLE_INPUT = (
    PROCESSED_DIR / "ssh_events.csv"
)

SAMPLE_OUTPUT = (
    PROCESSED_DIR / "ssh_features_2k_5min.csv"
)

# Full dataset
FULL_INPUT = (
    PROCESSED_DIR / "ssh_events_full.csv"
)

FULL_OUTPUT = (
    PROCESSED_DIR / "ssh_features_full_5min.csv"
)
# ============================================================
# Load parsed SSH events
# ============================================================

def load_events(file_path):

    df = pd.read_csv(
        file_path,
        parse_dates=["timestamp"]
    )

    print(f"Total parsed events: {len(df)}")

    return df


# ============================================================
# Prepare events for window-based analysis
# ============================================================

def prepare_events(df):

    # Keep only events where a source IP was successfully
    # extracted.
    #
    # Our behavioral analysis is based on:
    #
    #     source IP + time window
    #
    # Therefore, events without a source IP cannot currently
    # be assigned to an IP-specific behavior window.

    events = df[
        df["source_ip"].notna()
    ].copy()

    print(
        f"Events with source IP: {len(events)}"
    )

    print(
        f"Events without source IP: "
        f"{df['source_ip'].isna().sum()}"
    )


    # --------------------------------------------------------
    # Create 5-minute windows
    # --------------------------------------------------------
    #
    # Examples:
    #
    # 09:11:20 -> 09:10:00
    # 09:12:45 -> 09:10:00
    # 09:14:59 -> 09:10:00
    # 09:15:01 -> 09:15:00
    #
    # All events within the same 5-minute interval will share
    # the same window_start value.

    events["window_start"] = (
        events["timestamp"].dt.floor("5min")
    )


    # Calculate the end of the window for readability.

    events["window_end"] = (
        events["window_start"]
        + pd.Timedelta(minutes=5)
    )


    return events

def build_basic_features(events):

    # One group = one source IP during one 5-minute window
    grouped = events.groupby(
        ["source_ip", "window_start"]
    )

    feature_rows = []

    for (source_ip, window_start), group in grouped:

        # -----------------------------------------------
        # Failed logins
        # -----------------------------------------------

        failed_rows = group[
            group["event_type"] == "failed_login"
        ]

        # Sum event_count rather than counting rows,
        # because a row can represent repeated failures.
        failed_login_count = (
            failed_rows["event_count"].sum()
        )


        # -----------------------------------------------
        # Successful logins
        # -----------------------------------------------

        success_rows = group[
            group["event_type"] == "successful_login"
        ]

        successful_login_count = (
            success_rows["event_count"].sum()
        )


        # -----------------------------------------------
        # Invalid-user attempts
        # -----------------------------------------------

        invalid_rows = group[
            group["event_type"] == "invalid_user"
        ]

        invalid_user_count = (
            invalid_rows["event_count"].sum()
        )


        # -----------------------------------------------
        # Unique usernames attempted
        # -----------------------------------------------

        # We use authentication-result events here rather
        # than every SSH/PAM message so that the same
        # authentication attempt is not counted repeatedly.

        auth_attempts = group[
            group["event_type"].isin(
                [
                    "failed_login",
                    "successful_login"
                ]
            )
        ]

        # -----------------------------------------------
        # Root login attempts
        # -----------------------------------------------

        root_attempts = auth_attempts[
            auth_attempts["username"]
            .fillna("")
            .str.lower()
            == "root"
        ]

        root_attempt_count = (
            root_attempts["event_count"].sum()
        )


        # -----------------------------------------------
        # Break-in warnings
        # -----------------------------------------------

        breakin_warning_count = group.loc[
            group["event_type"] == "breakin_warning",
            "event_count"
        ].sum()


        # -----------------------------------------------
        # Maximum authentication retries exceeded
        # -----------------------------------------------

        #max_retries_exceeded_count = group.loc[
        #    group["event_type"] == "max_retries_exceeded",
        #    "event_count"
        #].sum()


        # -----------------------------------------------
        # Disconnect events
        # -----------------------------------------------

        disconnect_count = group.loc[
            group["event_type"] == "disconnect",
            "event_count"
        ].sum()


        # -----------------------------------------------
        # Missing SSH identification string
        # -----------------------------------------------

        no_identification_count = group.loc[
            group["event_type"] == "no_identification",
            "event_count"
        ].sum()

        unique_users = (
            auth_attempts["username"]
            .dropna()
            .nunique()
        )


        # -----------------------------------------------
        # Failure ratio
        # -----------------------------------------------

        total_attempts = (
            failed_login_count
            + successful_login_count
        )

        # -----------------------------------------------
        # Attempt rate
        # -----------------------------------------------

        # Number of authentication attempts per minute.
        # Our current window size is fixed at 5 minutes.

        attempt_rate = total_attempts / 5.0

        if total_attempts > 0:

            failure_ratio = (
                failed_login_count
                / total_attempts
            )

        else:

            failure_ratio = 0.0

        # -----------------------------------------------
        # Success after failures
        # -----------------------------------------------
        #
        # Detect whether a successful authentication
        # occurred AFTER at least one failed authentication
        # from the same source IP within this 5-minute
        # behavioral window.

        success_after_failures = 0


        failed_events = group[
            group["event_type"] == "failed_login"
        ]


        successful_events = group[
            group["event_type"] == "successful_login"
        ]


        if (
            not failed_events.empty
            and
            not successful_events.empty
        ):

            first_failure_time = (
                failed_events["timestamp"].min()
            )

            successful_after_failure = (
                successful_events["timestamp"]
                > first_failure_time
            ).any()


            if successful_after_failure:

                success_after_failures = 1

        # -----------------------------------------------
        # Root attempt ratio
        # -----------------------------------------------

        # Measures how strongly the failed-login activity
        # is concentrated on the root account.
        #
        # Example:
        # 90 root attempts / 100 failed logins = 0.90

        if failed_login_count > 0:
            root_attempt_ratio = (
                root_attempt_count / failed_login_count
            )
        else:
            root_attempt_ratio = 0.0

        # -----------------------------------------------
        # Build feature row
        # -----------------------------------------------

        feature_rows.append(
            {
                "source_ip": source_ip,
                "window_start": window_start,
                "window_end": (
                    window_start
                    + pd.Timedelta(minutes=5)
                ),
                "failed_login_count":
                    int(failed_login_count),

                "successful_login_count":
                    int(successful_login_count),

                "invalid_user_count":
                    int(invalid_user_count),

                "unique_users":
                    int(unique_users),

                "failure_ratio":
                    float(failure_ratio),

                "attempt_rate": 
                    float(attempt_rate),

                "root_attempt_count":
                    int(root_attempt_count),

                "breakin_warning_count":
                    int(breakin_warning_count),

                #"max_retries_exceeded_count":
                #    int(max_retries_exceeded_count),

                "disconnect_count":
                    int(disconnect_count),

                "no_identification_count":
                    int(no_identification_count),

                "success_after_failures":
                    int(success_after_failures),

                "root_attempt_ratio":
                    float(root_attempt_ratio)
            }
        )


    features = pd.DataFrame(
        feature_rows
    )

    return features

# ============================================================
# Main
# ============================================================

if __name__ == "__main__":

    # ========================================================
    # Select dataset
    # ========================================================
    #
    # Change DATASET to:
    #   "sample" -> generate the 2k feature CSV
    #   "full"   -> generate the full-data feature CSV
    #
    # The two outputs have different filenames and will not
    # overwrite each other.

    DATASET = "full"

    if DATASET == "sample":
        input_file = SAMPLE_INPUT
        output_file = SAMPLE_OUTPUT

    elif DATASET == "full":
        input_file = FULL_INPUT
        output_file = FULL_OUTPUT

    else:
        raise ValueError(
            "DATASET must be 'sample' or 'full'."
        )

    if not input_file.exists():
        raise FileNotFoundError(
            f"Input event file not found: {input_file}"
        )

    print(f"\nDataset: {DATASET}")
    print(f"Input:   {input_file}")
    print(f"Output:  {output_file}")

    # ========================================================
    # Load and prepare events
    # ========================================================

    df = load_events(input_file)
    events = prepare_events(df)
    features = build_basic_features(events)

    # ========================================================
    # Save selected dataset feature table
    # ========================================================

    features.to_csv(
        output_file,
        index=False
    )

    print(
        f"\nSaved feature table to: {output_file}"
    )

    # ========================================================
    # Window statistics
    # ========================================================

    print("\nNumber of unique source IPs:")
    print(events["source_ip"].nunique())

    print("\nNumber of 5-minute windows:")
    print(events["window_start"].nunique())

    print("\nNumber of source-IP/window combinations:")
    print(
        events[
            ["source_ip", "window_start"]
        ]
        .drop_duplicates()
        .shape[0]
    )

    # ========================================================
    # Candidate feature analysis
    # ========================================================

    candidate_features = [
        "failed_login_count",
        "successful_login_count",
        "invalid_user_count",
        "unique_users",
        "failure_ratio",
        "attempt_rate",
        "root_attempt_count",
        "breakin_warning_count",
        "disconnect_count",
        "no_identification_count",
        "success_after_failures",
        "root_attempt_ratio"
    ]

    print("\nFeature unique values:")

    for column in candidate_features:
        print(
            f"{column}: "
            f"{features[column].nunique()} unique values"
        )

    print("\nFeature correlations:")

    correlation_matrix = (
        features[candidate_features]
        .corr()
        .round(2)
    )

    print(
        correlation_matrix.to_string()
    )
