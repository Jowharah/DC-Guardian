from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# ============================================================
# Paths
# ============================================================

FEATURE_FILE = Path(
    "data/processed/ssh_features_full_5min.csv"
)


# ============================================================
# Candidate features
# ============================================================

CANDIDATE_FEATURES = [
    "failed_login_count",
    "successful_login_count",
    "invalid_user_count",
    "unique_users",
    "failure_ratio",
    "root_attempt_ratio",
    "breakin_warning_count",
    "disconnect_count",
    "no_identification_count",
    "success_after_failures"
]


COUNT_FEATURES = [
    "failed_login_count",
    "successful_login_count",
    "invalid_user_count",
    "unique_users",
    "breakin_warning_count",
    "disconnect_count",
    "no_identification_count"
]


# ============================================================
# Load full feature table
# ============================================================

df = pd.read_csv(
    FEATURE_FILE,
    parse_dates=[
        "window_start",
        "window_end"
    ]
)


print(
    f"Total behavior windows: {len(df)}"
)

print(
    f"Unique source IPs: "
    f"{df['source_ip'].nunique()}"
)


# ============================================================
# 1. Descriptive statistics
# ============================================================

print(
    "\n============================================"
)

print(
    "FEATURE SUMMARY"
)

print(
    "============================================"
)


print(
    df[CANDIDATE_FEATURES]
    .describe()
    .T
    .to_string()
)


# ============================================================
# 2. Zero-frequency analysis
# ============================================================
#
# This tells us whether a feature is present in many windows
# or is extremely sparse.
# ============================================================

print(
    "\n============================================"
)

print(
    "ZERO-FREQUENCY ANALYSIS"
)

print(
    "============================================"
)


for feature in CANDIDATE_FEATURES:

    zero_count = (
        df[feature] == 0
    ).sum()

    zero_percentage = (
        zero_count
        / len(df)
        * 100
    )

    nonzero_count = (
        df[feature] != 0
    ).sum()

    print(
        f"{feature:<30} "
        f"zero={zero_count:<6} "
        f"({zero_percentage:6.2f}%) "
        f"nonzero={nonzero_count}"
    )


# ============================================================
# 3. Detailed percentiles
# ============================================================
#
# Standard describe() stops at the 75th percentile.
#
# For anomaly detection we care about the upper tail:
#
# 90%
# 95%
# 99%
# 99.5%
# ============================================================

print(
    "\n============================================"
)

print(
    "UPPER-TAIL PERCENTILES"
)

print(
    "============================================"
)


percentiles = [
    0.50,
    0.75,
    0.90,
    0.95,
    0.99,
    0.995,
    1.00
]


for feature in COUNT_FEATURES:

    print(
        f"\n{feature}"
    )

    values = df[feature].quantile(
        percentiles
    )

    for percentile, value in values.items():

        print(
            f"  {percentile * 100:5.1f}% "
            f"= {value:.2f}"
        )


# ============================================================
# 4. Highest failed-login windows
# ============================================================

print(
    "\n============================================"
)

print(
    "TOP FAILED-LOGIN WINDOWS"
)

print(
    "============================================"
)


top_failures = (
    df.sort_values(
        "failed_login_count",
        ascending=False
    )
    .head(20)
)


print(
    top_failures[
        [
            "source_ip",
            "window_start",
            "failed_login_count",
            "successful_login_count",
            "unique_users",
            "invalid_user_count",
            "failure_ratio",
            "root_attempt_ratio",
            "breakin_warning_count",
            "disconnect_count",
            "no_identification_count"
        ]
    ]
    .to_string(index=False)
)


# ============================================================
# 5. Highest username-enumeration windows
# ============================================================

print(
    "\n============================================"
)

print(
    "TOP UNIQUE-USERNAME WINDOWS"
)

print(
    "============================================"
)


top_users = (
    df.sort_values(
        "unique_users",
        ascending=False
    )
    .head(20)
)


print(
    top_users[
        [
            "source_ip",
            "window_start",
            "failed_login_count",
            "unique_users",
            "invalid_user_count",
            "root_attempt_ratio"
        ]
    ]
    .to_string(index=False)
)


# ============================================================
# 6. Successful authentication behavior
# ============================================================

print(
    "\n============================================"
)

print(
    "SUCCESSFUL LOGIN WINDOWS"
)

print(
    "============================================"
)


success_windows = df[
    df["successful_login_count"] > 0
]


print(
    f"Windows containing successful logins: "
    f"{len(success_windows)}"
)


print(
    f"Windows with success after failures: "
    f"{df['success_after_failures'].sum()}"
)


# ============================================================
# 7. Raw failed-login histogram
# ============================================================

plt.figure(
    figsize=(9, 5)
)

plt.hist(
    df["failed_login_count"],
    bins=50
)

plt.xlabel(
    "Failed Login Count per 5-Minute Source-IP Window"
)

plt.ylabel(
    "Number of Windows"
)

plt.title(
    "Full OpenSSH Dataset - Failed Login Distribution"
)

plt.tight_layout()

plt.show()


# ============================================================
# 8. Log-transformed failed-login histogram
# ============================================================

log_failed = np.log1p(
    df["failed_login_count"]
)


plt.figure(
    figsize=(9, 5)
)

plt.hist(
    log_failed,
    bins=50
)

plt.xlabel(
    "log(1 + Failed Login Count)"
)

plt.ylabel(
    "Number of Windows"
)

plt.title(
    "Full OpenSSH Dataset - Log-Transformed Failed Logins"
)

plt.tight_layout()

plt.show()


# ============================================================
# 9. Unique-user histogram
# ============================================================

plt.figure(
    figsize=(9, 5)
)

plt.hist(
    df["unique_users"],
    bins=40
)

plt.xlabel(
    "Unique Usernames per 5-Minute Source-IP Window"
)

plt.ylabel(
    "Number of Windows"
)

plt.title(
    "Full OpenSSH Dataset - Username Diversity"
)

plt.tight_layout()

plt.show()