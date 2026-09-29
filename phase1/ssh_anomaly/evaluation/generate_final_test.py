from pathlib import Path
import csv
import random
from datetime import datetime, timedelta


# ============================================================
# FINAL TEST CONFIGURATION
# ============================================================
#
# IMPORTANT:
# This is Evaluation Set B.
#
# It is intentionally separate from the development scenarios
# used earlier.
#
# After generating and evaluating this dataset, do NOT tune
# ssh_detector.py against these results and then report the
# same dataset as an independent final test.
# ============================================================

RANDOM_SEED = 20260914

random.seed(
    RANDOM_SEED
)

EVALUATION_DIR = Path(
    "evaluation"
)

FINAL_TEST_DIR = (
    EVALUATION_DIR
    / "final_test"
)

LOG_OUTPUT = (
    FINAL_TEST_DIR
    / "openssh_final_test.log"
)

MANIFEST_OUTPUT = (
    FINAL_TEST_DIR
    / "final_test_manifest.csv"
)

HOSTNAME = "FinalEvalSSH"

BASE_TIME = datetime(
    2000,
    3,
    1,
    0,
    0,
    0
)

# 20 independent examples per scenario family.
REPETITIONS = 20


# ============================================================
# Helpers
# ============================================================

def ip_for(index):

    third = (
        index // 250
    )

    fourth = (
        index % 250
    ) + 1

    return (
        f"10.80.{third}.{fourth}"
    )


def log_line(
    timestamp,
    pid,
    message
):

    return (
        f"{timestamp.strftime('%b')} "
        f"{timestamp.day:02d} "
        f"{timestamp.strftime('%H:%M:%S')} "
        f"{HOSTNAME} "
        f"sshd[{pid}]: "
        f"{message}"
    )


def failed_password(
    timestamp,
    pid,
    username,
    source_ip,
    port
):

    return log_line(
        timestamp,
        pid,
        (
            f"Failed password for "
            f"{username} "
            f"from {source_ip} "
            f"port {port} ssh2"
        )
    )


def failed_invalid_password(
    timestamp,
    pid,
    username,
    source_ip,
    port
):

    return log_line(
        timestamp,
        pid,
        (
            "Failed password for "
            f"invalid user {username} "
            f"from {source_ip} "
            f"port {port} ssh2"
        )
    )


def invalid_user(
    timestamp,
    pid,
    username,
    source_ip
):

    return log_line(
        timestamp,
        pid,
        (
            f"Invalid user {username} "
            f"from {source_ip}"
        )
    )


def accepted_password(
    timestamp,
    pid,
    username,
    source_ip,
    port
):

    return log_line(
        timestamp,
        pid,
        (
            f"Accepted password for "
            f"{username} "
            f"from {source_ip} "
            f"port {port} ssh2"
        )
    )


def disconnect(
    timestamp,
    pid,
    source_ip
):

    return log_line(
        timestamp,
        pid,
        (
            "Received disconnect from "
            f"{source_ip}: "
            "11: disconnected by user"
        )
    )


def no_identification(
    timestamp,
    pid,
    source_ip
):

    return log_line(
        timestamp,
        pid,
        (
            "Did not receive identification "
            f"string from {source_ip}"
        )
    )


def breakin_warning(
    timestamp,
    pid,
    source_ip
):

    return log_line(
        timestamp,
        pid,
        (
            "reverse mapping checking "
            "getaddrinfo for attacker "
            f"[{source_ip}] failed - "
            "POSSIBLE BREAK-IN ATTEMPT!"
        )
    )


# ============================================================
# NORMAL SCENARIOS
# ============================================================

def normal_success(
    start,
    pid,
    source_ip,
    repetition
):

    user = random.choice(
        [
            "alice",
            "bob",
            "deploy",
            "operator",
            "backup"
        ]
    )

    port = (
        30000
        + repetition
    )

    return [
        accepted_password(
            start
            + timedelta(
                seconds=40
            ),
            pid,
            user,
            source_ip,
            port
        ),

        disconnect(
            start
            + timedelta(
                seconds=150
            ),
            pid,
            source_ip
        )
    ]


def normal_one_to_three_mistakes(
    start,
    pid,
    source_ip,
    repetition
):

    user = random.choice(
        [
            "alice",
            "bob",
            "deploy",
            "operator"
        ]
    )

    port = (
        31000
        + repetition
    )

    failure_count = (
        random.randint(
            1,
            3
        )
    )

    lines = []

    for i in range(
        failure_count
    ):

        lines.append(
            failed_password(
                start
                + timedelta(
                    seconds=15
                    + i * 30
                ),
                pid,
                user,
                source_ip,
                port
            )
        )

    lines.append(
        accepted_password(
            start
            + timedelta(
                seconds=150
            ),
            pid,
            user,
            source_ip,
            port
        )
    )

    lines.append(
        disconnect(
            start
            + timedelta(
                seconds=210
            ),
            pid,
            source_ip
        )
    )

    return lines


def normal_admin_root_login(
    start,
    pid,
    source_ip,
    repetition
):

    port = (
        32000
        + repetition
    )

    # Legitimate root authentication.
    #
    # No failed-login burst is present.

    return [
        accepted_password(
            start
            + timedelta(
                seconds=45
            ),
            pid,
            "root",
            source_ip,
            port
        ),

        disconnect(
            start
            + timedelta(
                seconds=180
            ),
            pid,
            source_ip
        )
    ]


def normal_multiple_users(
    start,
    pid,
    source_ip,
    repetition
):

    # Several legitimate successful sessions from a shared
    # administrative source such as a jump host.

    users = [
        "alice",
        "bob",
        "deploy"
    ]

    lines = []

    for i, user in enumerate(
        users
    ):

        port = (
            33000
            + repetition * 10
            + i
        )

        lines.append(
            accepted_password(
                start
                + timedelta(
                    seconds=30
                    + i * 60
                ),
                pid,
                user,
                source_ip,
                port
            )
        )

    return lines


def normal_borderline_failures(
    start,
    pid,
    source_ip,
    repetition
):

    # A deliberately difficult benign scenario:
    #
    # 3-4 failed attempts followed by success.
    #
    # This remains below the strong repeated-failure rule.

    user = random.choice(
        [
            "alice",
            "operator",
            "deploy"
        ]
    )

    port = (
        34000
        + repetition
    )

    failure_count = (
        random.randint(
            3,
            4
        )
    )

    lines = []

    for i in range(
        failure_count
    ):

        lines.append(
            failed_password(
                start
                + timedelta(
                    seconds=10
                    + i * 30
                ),
                pid,
                user,
                source_ip,
                port
            )
        )

    lines.append(
        accepted_password(
            start
            + timedelta(
                seconds=190
            ),
            pid,
            user,
            source_ip,
            port
        )
    )

    return lines


def normal_single_identification_failure(
    start,
    pid,
    source_ip,
    repetition
):

    # One incomplete SSH handshake can happen for benign
    # reasons such as health checks or interrupted clients.

    return [
        no_identification(
            start
            + timedelta(
                seconds=60
            ),
            pid,
            source_ip
        )
    ]


# ============================================================
# ATTACK SCENARIOS
# ============================================================

def attack_moderate_bruteforce(
    start,
    pid,
    source_ip,
    repetition
):

    user = random.choice(
        [
            "admin",
            "backup",
            "oracle",
            "service"
        ]
    )

    port = (
        40000
        + repetition
    )

    count = (
        random.randint(
            10,
            18
        )
    )

    return [
        failed_password(
            start
            + timedelta(
                seconds=10
                + i * 12
            ),
            pid,
            user,
            source_ip,
            port
        )
        for i in range(
            count
        )
    ]


def attack_root_mixed(
    start,
    pid,
    source_ip,
    repetition
):

    # Mixed targeting instead of 100% root.
    #
    # This is harder than the development root-bruteforce
    # scenario.

    count = (
        random.randint(
            12,
            20
        )
    )

    lines = []

    for i in range(
        count
    ):

        if (
            i
            < int(
                count * 0.75
            )
        ):

            user = "root"

        else:

            user = random.choice(
                [
                    "admin",
                    "oracle"
                ]
            )

        lines.append(
            failed_password(
                start
                + timedelta(
                    seconds=5
                    + i * 11
                ),
                pid,
                user,
                source_ip,
                41000
                + repetition
            )
        )

    return lines


def attack_low_username_enumeration(
    start,
    pid,
    source_ip,
    repetition
):

    # Five or six usernames puts this close to the frozen
    # username-enumeration boundary.

    usernames = [
        "admin",
        "oracle",
        "postgres",
        "git",
        "jenkins",
        "support"
    ]

    number_users = (
        random.randint(
            5,
            6
        )
    )

    selected = (
        usernames[
            :number_users
        ]
    )

    lines = []

    for i, username in enumerate(
        selected
    ):

        timestamp = (
            start
            + timedelta(
                seconds=15
                + i * 30
            )
        )

        port = (
            42000
            + repetition * 10
            + i
        )

        lines.append(
            invalid_user(
                timestamp,
                pid,
                username,
                source_ip
            )
        )

        lines.append(
            failed_invalid_password(
                timestamp
                + timedelta(
                    seconds=2
                ),
                pid,
                username,
                source_ip,
                port
            )
        )

    return lines


def attack_identification_probe_low(
    start,
    pid,
    source_ip,
    repetition
):

    # Lower-rate identification probing than Set A.

    count = (
        random.randint(
            3,
            7
        )
    )

    return [
        no_identification(
            start
            + timedelta(
                seconds=15
                + i * 35
            ),
            pid,
            source_ip
        )
        for i in range(
            count
        )
    ]


def attack_breakin_warning(
    start,
    pid,
    source_ip,
    repetition
):

    # Explicit OpenSSH security signal.
    #
    # Some scenarios contain only one warning to ensure the
    # operational security-signal path is tested.

    count = (
        random.randint(
            1,
            3
        )
    )

    return [
        breakin_warning(
            start
            + timedelta(
                seconds=30
                + i * 60
            ),
            pid,
            source_ip
        )
        for i in range(
            count
        )
    ]


def attack_failures_then_success(
    start,
    pid,
    source_ip,
    repetition
):

    user = random.choice(
        [
            "root",
            "admin",
            "deploy"
        ]
    )

    port = (
        43000
        + repetition
    )

    failure_count = (
        random.randint(
            8,
            14
        )
    )

    lines = []

    for i in range(
        failure_count
    ):

        lines.append(
            failed_password(
                start
                + timedelta(
                    seconds=10
                    + i * 12
                ),
                pid,
                user,
                source_ip,
                port
            )
        )

    lines.append(
        accepted_password(
            start
            + timedelta(
                seconds=220
            ),
            pid,
            user,
            source_ip,
            port
        )
    )

    return lines


def attack_distributed_style_single_ip_window(
    start,
    pid,
    source_ip,
    repetition
):

    # Lower-volume attack-like behavior intended to challenge
    # a detector trained on large bursts.
    #
    # 6-9 failures from this source in the current window.

    user = random.choice(
        [
            "admin",
            "oracle",
            "backup"
        ]
    )

    count = (
        random.randint(
            6,
            9
        )
    )

    port = (
        44000
        + repetition
    )

    return [
        failed_password(
            start
            + timedelta(
                seconds=15
                + i * 25
            ),
            pid,
            user,
            source_ip,
            port
        )
        for i in range(
            count
        )
    ]


def attack_mixed_enumeration_root(
    start,
    pid,
    source_ip,
    repetition
):

    usernames = [
        "root",
        "admin",
        "oracle",
        "postgres",
        "support"
    ]

    lines = []

    for i, username in enumerate(
        usernames
    ):

        timestamp = (
            start
            + timedelta(
                seconds=10
                + i * 35
            )
        )

        port = (
            45000
            + repetition * 10
            + i
        )

        if username == "root":

            lines.append(
                failed_password(
                    timestamp,
                    pid,
                    username,
                    source_ip,
                    port
                )
            )

        else:

            lines.append(
                invalid_user(
                    timestamp,
                    pid,
                    username,
                    source_ip
                )
            )

            lines.append(
                failed_invalid_password(
                    timestamp
                    + timedelta(
                        seconds=2
                    ),
                    pid,
                    username,
                    source_ip,
                    port
                )
            )

    return lines


# ============================================================
# Scenario definitions
# ============================================================

SCENARIOS = [

    # --------------------------------------------------------
    # NORMAL
    # --------------------------------------------------------

    {
        "scenario_type":
            "normal_success",

        "ground_truth":
            "NORMAL",

        "builder":
            normal_success
    },

    {
        "scenario_type":
            "normal_one_to_three_mistakes",

        "ground_truth":
            "NORMAL",

        "builder":
            normal_one_to_three_mistakes
    },

    {
        "scenario_type":
            "normal_admin_root_login",

        "ground_truth":
            "NORMAL",

        "builder":
            normal_admin_root_login
    },

    {
        "scenario_type":
            "normal_multiple_users",

        "ground_truth":
            "NORMAL",

        "builder":
            normal_multiple_users
    },

    {
        "scenario_type":
            "normal_borderline_failures",

        "ground_truth":
            "NORMAL",

        "builder":
            normal_borderline_failures
    },

    {
        "scenario_type":
            "normal_single_identification_failure",

        "ground_truth":
            "NORMAL",

        "builder":
            normal_single_identification_failure
    },


    # --------------------------------------------------------
    # ATTACK
    # --------------------------------------------------------

    {
        "scenario_type":
            "attack_moderate_bruteforce",

        "ground_truth":
            "ATTACK",

        "builder":
            attack_moderate_bruteforce
    },

    {
        "scenario_type":
            "attack_root_mixed",

        "ground_truth":
            "ATTACK",

        "builder":
            attack_root_mixed
    },

    {
        "scenario_type":
            "attack_low_username_enumeration",

        "ground_truth":
            "ATTACK",

        "builder":
            attack_low_username_enumeration
    },

    {
        "scenario_type":
            "attack_identification_probe_low",

        "ground_truth":
            "ATTACK",

        "builder":
            attack_identification_probe_low
    },

    {
        "scenario_type":
            "attack_breakin_warning",

        "ground_truth":
            "ATTACK",

        "builder":
            attack_breakin_warning
    },

    {
        "scenario_type":
            "attack_failures_then_success",

        "ground_truth":
            "ATTACK",

        "builder":
            attack_failures_then_success
    },

    {
        "scenario_type":
            "attack_distributed_style",

        "ground_truth":
            "ATTACK",

        "builder":
            attack_distributed_style_single_ip_window
    },

    {
        "scenario_type":
            "attack_mixed_enumeration_root",

        "ground_truth":
            "ATTACK",

        "builder":
            attack_mixed_enumeration_root
    }
]


# ============================================================
# Generate Final Test Set B
# ============================================================

def generate():

    FINAL_TEST_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    all_log_lines = []

    manifest_rows = []

    scenario_index = 0


    for scenario in SCENARIOS:

        for repetition in range(
            REPETITIONS
        ):

            source_ip = ip_for(
                scenario_index
            )

            # Give every scenario its own isolated window.
            #
            # 10-minute spacing ensures scenarios cannot
            # overlap into the same five-minute bucket.

            start = (
                BASE_TIME
                + timedelta(
                    minutes=(
                        scenario_index
                        * 10
                    )
                )
            )

            pid = (
                30000
                + scenario_index
            )


            lines = (
                scenario[
                    "builder"
                ](
                    start,
                    pid,
                    source_ip,
                    repetition
                )
            )


            scenario_id = (
                f"FINAL_{scenario_index:04d}"
            )


            window_start = (
                start.replace(
                    minute=(
                        start.minute
                        // 5
                    ) * 5,
                    second=0,
                    microsecond=0
                )
            )


            manifest_rows.append(
                {
                    "scenario_id":
                        scenario_id,

                    "scenario_type":
                        scenario[
                            "scenario_type"
                        ],

                    "ground_truth":
                        scenario[
                            "ground_truth"
                        ],

                    "source_ip":
                        source_ip,

                    "window_start":
                        window_start.isoformat(),

                    "window_end":
                        (
                            window_start
                            + timedelta(
                                minutes=5
                            )
                        ).isoformat(),

                    "raw_log_lines":
                        len(lines)
                }
            )


            all_log_lines.extend(
                lines
            )


            scenario_index += 1


    # --------------------------------------------------------
    # Sort log lines chronologically
    # --------------------------------------------------------

    def timestamp_key(line):

        prefix = " ".join(
            line.split()[
                :3
            ]
        )

        return datetime.strptime(
            "2000 "
            + prefix,
            "%Y %b %d %H:%M:%S"
        )


    all_log_lines.sort(
        key=timestamp_key
    )


    # --------------------------------------------------------
    # Save raw OpenSSH log
    # --------------------------------------------------------

    with open(
        LOG_OUTPUT,
        "w",
        encoding="utf-8"
    ) as file:

        for line in all_log_lines:

            file.write(
                line
                + "\n"
            )


    # --------------------------------------------------------
    # Save independent ground-truth manifest
    # --------------------------------------------------------

    fieldnames = [
        "scenario_id",
        "scenario_type",
        "ground_truth",
        "source_ip",
        "window_start",
        "window_end",
        "raw_log_lines"
    ]


    with open(
        MANIFEST_OUTPUT,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = (
            csv.DictWriter(
                file,
                fieldnames=fieldnames
            )
        )

        writer.writeheader()

        writer.writerows(
            manifest_rows
        )


    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    normal_count = sum(
        row[
            "ground_truth"
        ]
        == "NORMAL"
        for row in manifest_rows
    )


    attack_count = sum(
        row[
            "ground_truth"
        ]
        == "ATTACK"
        for row in manifest_rows
    )


    print(
        "\n============================================"
    )

    print(
        "FINAL LABELED OPENSSH TEST SET GENERATED"
    )

    print(
        "============================================"
    )


    print(
        f"Scenario families: "
        f"{len(SCENARIOS)}"
    )


    print(
        f"Repetitions per family: "
        f"{REPETITIONS}"
    )


    print(
        f"Total labeled scenarios: "
        f"{len(manifest_rows)}"
    )


    print(
        f"NORMAL scenarios: "
        f"{normal_count}"
    )


    print(
        f"ATTACK scenarios: "
        f"{attack_count}"
    )


    print(
        f"Raw OpenSSH log lines: "
        f"{len(all_log_lines)}"
    )


    print(
        f"\nRaw log: "
        f"{LOG_OUTPUT}"
    )


    print(
        f"Manifest: "
        f"{MANIFEST_OUTPUT}"
    )


    print(
        "\nIMPORTANT:"
    )

    print(
        "This is Final Evaluation Set B."
    )

    print(
        "Do not modify the frozen detector based "
        "on this test and then reuse these results "
        "as independent final-test metrics."
    )


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":

    generate()