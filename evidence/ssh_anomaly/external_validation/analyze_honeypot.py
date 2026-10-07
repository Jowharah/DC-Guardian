from pathlib import Path
import re

import numpy as np
import pandas as pd


# ============================================================
# Paths
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "external"
    / "ssh_honeypot_dataset.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "external_validation"
    / "results"
)

WINDOW_OUTPUT = (
    OUTPUT_DIR
    / "honeypot_source_ip_5min_windows.csv"
)

IP_OUTPUT = (
    OUTPUT_DIR
    / "honeypot_source_ip_summary.csv"
)

USERNAME_OUTPUT = (
    OUTPUT_DIR
    / "honeypot_username_summary.csv"
)

SESSION_OUTPUT = (
    OUTPUT_DIR
    / "honeypot_session_summary.csv"
)


# ============================================================
# Expected schema
# ============================================================

REQUIRED_COLUMNS = [
    "timestamp",
    "session_id",
    "ip",
    "port",
    "event_type",
    "message",
    "command",
]


# ============================================================
# Username extraction
# ============================================================
#
# Example observed in this dataset:
#
# Bot entered username: root, password: test
# ============================================================

USERNAME_PATTERN = re.compile(
    r"username:\s*(?P<username>.*?),\s*password:",
    flags=re.IGNORECASE,
)


def extract_username(message):

    if pd.isna(message):
        return None

    match = USERNAME_PATTERN.search(
        str(message)
    )

    if not match:
        return None

    username = (
        match.group("username")
        .strip()
    )

    if not username:
        return None

    return username


# ============================================================
# Load and validate
# ============================================================

def load_dataset():

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"External dataset not found: {INPUT_FILE}"
        )

    df = pd.read_csv(
        INPUT_FILE,
        low_memory=False,
    )

    missing = [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            "Honeypot dataset is missing required columns: "
            + ", ".join(missing)
        )

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce",
        utc=True,
    )

    invalid_timestamps = int(
        df["timestamp"]
        .isna()
        .sum()
    )

    print(
        "\n============================================"
    )
    print(
        "EXTERNAL SSH HONEYPOT DATASET"
    )
    print(
        "============================================"
    )

    print(
        f"Rows: {len(df)}"
    )

    print(
        f"Columns: {len(df.columns)}"
    )

    print(
        f"Invalid timestamps: "
        f"{invalid_timestamps}"
    )

    if invalid_timestamps > 0:
        raise ValueError(
            "Invalid timestamps found. "
            "Stop before behavioral aggregation."
        )

    return df


# ============================================================
# Basic event analysis
# ============================================================

def analyze_events(df):

    print(
        "\n============================================"
    )
    print(
        "EVENT DISTRIBUTION"
    )
    print(
        "============================================"
    )

    event_counts = (
        df["event_type"]
        .fillna("<missing>")
        .value_counts()
    )

    print(
        event_counts.to_string()
    )

    print(
        "\nTime range:"
    )

    print(
        f"Start: {df['timestamp'].min()}"
    )

    print(
        f"End:   {df['timestamp'].max()}"
    )

    print(
        f"\nUnique source IPs: "
        f"{df['ip'].nunique(dropna=True)}"
    )

    print(
        f"Unique sessions: "
        f"{df['session_id'].nunique(dropna=True)}"
    )


# ============================================================
# Login / username analysis
# ============================================================

def prepare_login_data(df):

    result = df.copy()

    result["username"] = (
        result["message"]
        .apply(
            extract_username
        )
    )

    result["is_login"] = (
        result["event_type"]
        .eq("SSH login")
    )

    result["is_connect"] = (
        result["event_type"]
        .eq("SSH connect")
    )

    result["is_disconnect"] = (
        result["event_type"]
        .eq("SSH disconnect")
    )

    result["is_command"] = (
        result["event_type"]
        .eq("exec_command")
    )

    result["is_root_login"] = (
        result["is_login"]
        & result["username"]
        .fillna("")
        .str.lower()
        .eq("root")
    )

    return result


def analyze_usernames(df):

    login_rows = df[
        df["is_login"]
    ].copy()

    print(
        "\n============================================"
    )
    print(
        "HONEYPOT LOGIN / USERNAME ANALYSIS"
    )
    print(
        "============================================"
    )

    print(
        f"SSH login events: "
        f"{len(login_rows)}"
    )

    usernames_extracted = int(
        login_rows["username"]
        .notna()
        .sum()
    )

    print(
        f"Login usernames extracted: "
        f"{usernames_extracted}"
    )

    print(
        f"Unique usernames: "
        f"{login_rows['username'].nunique(dropna=True)}"
    )

    root_count = int(
        login_rows["is_root_login"]
        .sum()
    )

    root_ratio = (
        root_count / len(login_rows)
        if len(login_rows) > 0
        else np.nan
    )

    print(
        f"Root login events: "
        f"{root_count}"
    )

    print(
        f"Root share of login events: "
        f"{root_ratio * 100:.2f}%"
        if not np.isnan(root_ratio)
        else "Root share of login events: N/A"
    )

    username_summary = (
        login_rows[
            login_rows["username"].notna()
        ]
        .groupby(
            "username"
        )
        .agg(
            login_events=(
                "username",
                "size"
            ),
            unique_source_ips=(
                "ip",
                "nunique"
            ),
            unique_sessions=(
                "session_id",
                "nunique"
            ),
        )
        .reset_index()
        .sort_values(
            "login_events",
            ascending=False
        )
    )

    print(
        "\nTop 20 usernames:"
    )

    print(
        username_summary
        .head(20)
        .to_string(
            index=False
        )
    )

    return username_summary


# ============================================================
# 5-minute source-IP behavior
# ============================================================

def build_5min_windows(df):

    work = df[
        df["ip"].notna()
    ].copy()

    work["window_start"] = (
        work["timestamp"]
        .dt.floor("5min")
    )

    work["window_end"] = (
        work["window_start"]
        + pd.Timedelta(
            minutes=5
        )
    )

    rows = []

    grouped = work.groupby(
        [
            "ip",
            "window_start",
        ],
        sort=True,
    )

    for (
        source_ip,
        window_start
    ), group in grouped:

        connect_count = int(
            group["is_connect"]
            .sum()
        )

        login_count = int(
            group["is_login"]
            .sum()
        )

        disconnect_count = int(
            group["is_disconnect"]
            .sum()
        )

        command_count = int(
            group["is_command"]
            .sum()
        )

        login_rows = group[
            group["is_login"]
        ]

        unique_users = int(
            login_rows["username"]
            .dropna()
            .nunique()
        )

        root_login_count = int(
            login_rows["is_root_login"]
            .sum()
        )

        root_login_ratio = (
            root_login_count
            / login_count
            if login_count > 0
            else 0.0
        )

        unique_sessions = int(
            group["session_id"]
            .nunique(
                dropna=True
            )
        )

        # These are honeypot-native behavioral features.
        # They are NOT renamed to failed_login_count etc.,
        # because those OpenSSH semantics are unavailable.
        rows.append(
            {
                "source_ip":
                    source_ip,

                "window_start":
                    window_start,

                "window_end":
                    (
                        window_start
                        + pd.Timedelta(
                            minutes=5
                        )
                    ),

                "event_count":
                    len(group),

                "connect_count":
                    connect_count,

                "login_count":
                    login_count,

                "disconnect_count":
                    disconnect_count,

                "command_count":
                    command_count,

                "unique_sessions":
                    unique_sessions,

                "unique_login_users":
                    unique_users,

                "root_login_count":
                    root_login_count,

                "root_login_ratio":
                    float(
                        root_login_ratio
                    ),

                "has_login":
                    int(
                        login_count > 0
                    ),

                "has_command":
                    int(
                        command_count > 0
                    ),
            }
        )

    windows = pd.DataFrame(
        rows
    )

    return windows


def analyze_windows(windows):

    print(
        "\n============================================"
    )
    print(
        "5-MINUTE SOURCE-IP BEHAVIOR"
    )
    print(
        "============================================"
    )

    print(
        f"Source-IP/window combinations: "
        f"{len(windows)}"
    )

    print(
        f"Unique source IPs in windows: "
        f"{windows['source_ip'].nunique()}"
    )

    columns = [
        "event_count",
        "connect_count",
        "login_count",
        "disconnect_count",
        "command_count",
        "unique_sessions",
        "unique_login_users",
        "root_login_count",
        "root_login_ratio",
    ]

    print(
        "\nBehavioral summary:"
    )

    print(
        windows[
            columns
        ]
        .describe(
            percentiles=[
                0.50,
                0.75,
                0.90,
                0.95,
                0.99,
                0.995,
            ]
        )
        .round(3)
        .to_string()
    )

    print(
        "\nWindows containing a honeypot login:"
    )

    print(
        int(
            windows["has_login"]
            .sum()
        )
    )

    print(
        "\nWindows containing command execution:"
    )

    print(
        int(
            windows["has_command"]
            .sum()
        )
    )

    print(
        "\nTop 20 windows by connection count:"
    )

    print(
        windows
        .sort_values(
            [
                "connect_count",
                "login_count",
            ],
            ascending=False
        )
        .head(20)
        .to_string(
            index=False
        )
    )


# ============================================================
# Source-IP summary
# ============================================================

def build_ip_summary(df):

    grouped = (
        df[
            df["ip"].notna()
        ]
        .groupby(
            "ip"
        )
    )

    rows = []

    for source_ip, group in grouped:

        login_rows = group[
            group["is_login"]
        ]

        rows.append(
            {
                "source_ip":
                    source_ip,

                "first_seen":
                    group["timestamp"]
                    .min(),

                "last_seen":
                    group["timestamp"]
                    .max(),

                "total_events":
                    len(group),

                "connect_events":
                    int(
                        group["is_connect"]
                        .sum()
                    ),

                "login_events":
                    int(
                        group["is_login"]
                        .sum()
                    ),

                "disconnect_events":
                    int(
                        group["is_disconnect"]
                        .sum()
                    ),

                "command_events":
                    int(
                        group["is_command"]
                        .sum()
                    ),

                "unique_sessions":
                    int(
                        group["session_id"]
                        .nunique(
                            dropna=True
                        )
                    ),

                "unique_login_users":
                    int(
                        login_rows["username"]
                        .dropna()
                        .nunique()
                    ),

                "root_login_events":
                    int(
                        login_rows[
                            "is_root_login"
                        ]
                        .sum()
                    ),
            }
        )

    summary = pd.DataFrame(
        rows
    )

    summary["active_minutes"] = (
        (
            summary["last_seen"]
            - summary["first_seen"]
        )
        .dt.total_seconds()
        / 60.0
    )

    return summary.sort_values(
        "total_events",
        ascending=False
    )


def analyze_ips(summary):

    print(
        "\n============================================"
    )
    print(
        "SOURCE-IP CONCENTRATION"
    )
    print(
        "============================================"
    )

    print(
        f"Unique source IPs: "
        f"{len(summary)}"
    )

    print(
        "\nTop 20 source IPs by total events:"
    )

    print(
        summary
        .head(20)
        .to_string(
            index=False
        )
    )

    total_events = (
        summary["total_events"]
        .sum()
    )

    for n in [
        1,
        10,
        100,
    ]:

        top_events = (
            summary
            .head(n)[
                "total_events"
            ]
            .sum()
        )

        share = (
            top_events
            / total_events
            * 100
            if total_events > 0
            else 0.0
        )

        print(
            f"\nTop {n} IP(s) share of "
            f"all events: {share:.2f}%"
        )


# ============================================================
# Session analysis
# ============================================================

def build_session_summary(df):

    session_rows = df[
        df["session_id"].notna()
    ].copy()

    grouped = session_rows.groupby(
        "session_id"
    )

    rows = []

    for session_id, group in grouped:

        login_rows = group[
            group["is_login"]
        ]

        usernames = (
            login_rows["username"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        rows.append(
            {
                "session_id":
                    session_id,

                "source_ip":
                    (
                        group["ip"]
                        .dropna()
                        .astype(str)
                        .iloc[0]
                        if group["ip"]
                        .notna()
                        .any()
                        else None
                    ),

                "first_seen":
                    group["timestamp"]
                    .min(),

                "last_seen":
                    group["timestamp"]
                    .max(),

                "event_count":
                    len(group),

                "connect_events":
                    int(
                        group["is_connect"]
                        .sum()
                    ),

                "login_events":
                    int(
                        group["is_login"]
                        .sum()
                    ),

                "disconnect_events":
                    int(
                        group["is_disconnect"]
                        .sum()
                    ),

                "command_events":
                    int(
                        group["is_command"]
                        .sum()
                    ),

                "usernames":
                    ";".join(
                        usernames
                    ),

                "root_login":
                    int(
                        login_rows[
                            "is_root_login"
                        ]
                        .any()
                    ),
            }
        )

    sessions = pd.DataFrame(
        rows
    )

    sessions["duration_seconds"] = (
        sessions["last_seen"]
        - sessions["first_seen"]
    ).dt.total_seconds()

    return sessions


def analyze_sessions(sessions):

    print(
        "\n============================================"
    )
    print(
        "SESSION ANALYSIS"
    )
    print(
        "============================================"
    )

    print(
        f"Sessions: "
        f"{len(sessions)}"
    )

    print(
        f"Sessions with login event: "
        f"{int((sessions['login_events'] > 0).sum())}"
    )

    print(
        f"Sessions with command execution: "
        f"{int((sessions['command_events'] > 0).sum())}"
    )

    print(
        f"Sessions with root login: "
        f"{int((sessions['root_login'] > 0).sum())}"
    )

    print(
        "\nSession duration summary (seconds):"
    )

    print(
        sessions[
            "duration_seconds"
        ]
        .describe(
            percentiles=[
                0.50,
                0.75,
                0.90,
                0.95,
                0.99,
            ]
        )
        .round(3)
        .to_string()
    )

    command_sessions = (
        sessions[
            sessions[
                "command_events"
            ] > 0
        ]
        .sort_values(
            "command_events",
            ascending=False
        )
    )

    print(
        "\nSessions reaching command execution:"
    )

    if command_sessions.empty:
        print(
            "None"
        )
    else:
        print(
            command_sessions
            .head(30)
            .to_string(
                index=False
            )
        )


# ============================================================
# Coverage against our SSH detector feature space
# ============================================================

def print_feature_coverage():

    print(
        "\n============================================"
    )
    print(
        "EXTERNAL FEATURE-SPACE COVERAGE"
    )
    print(
        "============================================"
    )

    print(
        """
Directly or defensibly observable in this honeypot dataset:
  YES  source_ip / temporal source-IP behavior
  YES  connection intensity
  YES  login activity
  YES  username diversity among honeypot login events
  YES  root targeting among honeypot login events
  YES  disconnect behavior
  YES  session behavior
  YES  command execution

Not directly equivalent to our OpenSSH server-log features:
  NO   failed_login_count
  NO   failure_ratio
  NO   invalid_user_count
  NO   breakin_warning_count
  NO   no_identification_count

IMPORTANT:
No unavailable OpenSSH feature is fabricated or filled with
a guessed value. This dataset is therefore used for external
behavioral validation, not for classification accuracy of the
frozen detector.
""".strip()
    )


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    df = load_dataset()

    analyze_events(
        df
    )

    df = prepare_login_data(
        df
    )

    username_summary = (
        analyze_usernames(
            df
        )
    )

    windows = build_5min_windows(
        df
    )

    analyze_windows(
        windows
    )

    ip_summary = build_ip_summary(
        df
    )

    analyze_ips(
        ip_summary
    )

    session_summary = (
        build_session_summary(
            df
        )
    )

    analyze_sessions(
        session_summary
    )

    print_feature_coverage()

    # --------------------------------------------------------
    # Save external-validation artifacts
    # --------------------------------------------------------

    windows.to_csv(
        WINDOW_OUTPUT,
        index=False
    )

    ip_summary.to_csv(
        IP_OUTPUT,
        index=False
    )

    username_summary.to_csv(
        USERNAME_OUTPUT,
        index=False
    )

    session_summary.to_csv(
        SESSION_OUTPUT,
        index=False
    )

    print(
        "\n============================================"
    )
    print(
        "EXTERNAL HONEYPOT ANALYSIS COMPLETE"
    )
    print(
        "============================================"
    )

    print(
        f"\n5-minute windows: "
        f"{WINDOW_OUTPUT}"
    )

    print(
        f"Source-IP summary: "
        f"{IP_OUTPUT}"
    )

    print(
        f"Username summary: "
        f"{USERNAME_OUTPUT}"
    )

    print(
        f"Session summary: "
        f"{SESSION_OUTPUT}"
    )
