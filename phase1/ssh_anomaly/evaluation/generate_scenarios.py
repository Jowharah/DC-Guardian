from pathlib import Path
import csv
import random
from datetime import datetime, timedelta


# ============================================================
# Configuration
# ============================================================

RANDOM_SEED = 42
random.seed(RANDOM_SEED)

EVALUATION_DIR = Path("evaluation")
SCENARIO_DIR = EVALUATION_DIR / "scenarios"

LOG_OUTPUT = (
    SCENARIO_DIR / "labeled_openssh_scenarios.log"
)

MANIFEST_OUTPUT = (
    SCENARIO_DIR / "scenario_manifest.csv"
)

HOSTNAME = "EvalSSH"

# Use one dedicated 5-minute window per scenario.
BASE_TIME = datetime(
    2000,
    2,
    1,
    0,
    0,
    0
)

# Number of independent repetitions per scenario family.
REPETITIONS = 30


# ============================================================
# Helpers
# ============================================================

def ip_for(index):
    """
    Generate deterministic private source IPs.

    Each scenario gets a unique IP so scenarios cannot merge
    into the same source-IP/window behavior accidentally.
    """

    third = index // 250
    fourth = (index % 250) + 1

    return f"10.50.{third}.{fourth}"


def log_line(timestamp, pid, message):
    """
    Match parser.py BASE_PATTERN exactly:

    Dec 10 06:55:48 LabSZ sshd[24200]: <message>
    """

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
            f"Failed password for {username} "
            f"from {source_ip} port {port} ssh2"
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
            f"Failed password for invalid user "
            f"{username} from {source_ip} "
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
            f"Accepted password for {username} "
            f"from {source_ip} port {port} ssh2"
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
            f"Received disconnect from "
            f"{source_ip}: 11: disconnected by user"
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
            f"reverse mapping checking getaddrinfo "
            f"for attacker [{source_ip}] failed - "
            "POSSIBLE BREAK-IN ATTEMPT!"
        )
    )


# ============================================================
# Scenario builders
# ============================================================

def normal_success(
    start,
    pid,
    source_ip,
    repetition
):
    user = random.choice(
        ["alice", "bob", "deploy", "operator"]
    )

    port = 40000 + repetition

    return [
        accepted_password(
            start + timedelta(seconds=30),
            pid,
            user,
            source_ip,
            port
        ),
        disconnect(
            start + timedelta(seconds=90),
            pid,
            source_ip
        )
    ]


def normal_one_mistake(
    start,
    pid,
    source_ip,
    repetition
):
    user = random.choice(
        ["alice", "bob", "deploy", "operator"]
    )

    port = 41000 + repetition

    return [
        failed_password(
            start + timedelta(seconds=20),
            pid,
            user,
            source_ip,
            port
        ),
        accepted_password(
            start + timedelta(seconds=80),
            pid,
            user,
            source_ip,
            port
        ),
        disconnect(
            start + timedelta(seconds=120),
            pid,
            source_ip
        )
    ]


def normal_two_mistakes(
    start,
    pid,
    source_ip,
    repetition
):
    user = random.choice(
        ["alice", "bob", "deploy", "operator"]
    )

    port = 42000 + repetition

    return [
        failed_password(
            start + timedelta(seconds=20),
            pid,
            user,
            source_ip,
            port
        ),
        failed_password(
            start + timedelta(seconds=45),
            pid,
            user,
            source_ip,
            port
        ),
        accepted_password(
            start + timedelta(seconds=100),
            pid,
            user,
            source_ip,
            port
        ),
        disconnect(
            start + timedelta(seconds=150),
            pid,
            source_ip
        )
    ]


def normal_low_activity(
    start,
    pid,
    source_ip,
    repetition
):
    """
    Low-volume ordinary activity with 0-2 failures.

    Keep it below the frozen strong-rule thresholds.
    """

    user = random.choice(
        ["alice", "bob", "deploy", "operator"]
    )

    port = 43000 + repetition

    failures = random.choice([0, 1, 2])

    lines = []

    for i in range(failures):
        lines.append(
            failed_password(
                start + timedelta(
                    seconds=20 + i * 25
                ),
                pid,
                user,
                source_ip,
                port
            )
        )

    lines.append(
        accepted_password(
            start + timedelta(seconds=120),
            pid,
            user,
            source_ip,
            port
        )
    )

    return lines


def attack_repeated_failures(
    start,
    pid,
    source_ip,
    repetition
):
    """
    Existing non-root account, repeated failures.
    """

    user = random.choice(
        ["admin", "backup", "oracle", "service"]
    )

    port = 44000 + repetition

    count = random.randint(12, 30)

    return [
        failed_password(
            start + timedelta(
                seconds=5 + i * 7
            ),
            pid,
            user,
            source_ip,
            port
        )
        for i in range(count)
    ]


def attack_root_bruteforce(
    start,
    pid,
    source_ip,
    repetition
):
    port = 45000 + repetition

    count = random.randint(15, 40)

    return [
        failed_password(
            start + timedelta(
                seconds=5 + i * 5
            ),
            pid,
            "root",
            source_ip,
            port
        )
        for i in range(count)
    ]


def attack_username_enumeration(
    start,
    pid,
    source_ip,
    repetition
):
    usernames = [
        "admin",
        "oracle",
        "postgres",
        "git",
        "jenkins",
        "support",
        "backup",
        "test",
        "guest",
        "webmaster"
    ]

    random.shuffle(usernames)

    number_users = random.randint(6, 10)

    selected = usernames[
        :number_users
    ]

    lines = []

    for i, username in enumerate(selected):

        timestamp = start + timedelta(
            seconds=10 + i * 15
        )

        port = (
            46000
            + repetition * 10
            + i
        )

        # parser.py counts invalid_user_count from explicit
        # "Invalid user ..." events. It counts unique_users
        # from failed/successful authentication-result events.
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
                timestamp + timedelta(seconds=2),
                pid,
                username,
                source_ip,
                port
            )
        )

    return lines


def attack_high_volume(
    start,
    pid,
    source_ip,
    repetition
):
    """
    High-volume attack similar to the large bursts observed
    in the full Loghub data.
    """

    port = 47000 + repetition

    count = random.randint(80, 140)

    return [
        failed_password(
            start + timedelta(
                seconds=2 + i * 2
            ),
            pid,
            "root",
            source_ip,
            port
        )
        for i in range(count)
    ]


def attack_identification_probe(
    start,
    pid,
    source_ip,
    repetition
):
    count = random.randint(8, 25)

    return [
        no_identification(
            start + timedelta(
                seconds=5 + i * 8
            ),
            pid,
            source_ip
        )
        for i in range(count)
    ]


def attack_failures_then_success(
    start,
    pid,
    source_ip,
    repetition
):
    """
    Known attack scenario: repeated failures followed by a
    successful authentication within the same 5-minute window.
    """

    user = random.choice(
        ["root", "admin"]
    )

    port = 48000 + repetition

    failure_count = random.randint(
        10,
        20
    )

    lines = [
        failed_password(
            start + timedelta(
                seconds=5 + i * 8
            ),
            pid,
            user,
            source_ip,
            port
        )
        for i in range(
            failure_count
        )
    ]

    lines.append(
        accepted_password(
            start + timedelta(seconds=220),
            pid,
            user,
            source_ip,
            port
        )
    )

    return lines


def attack_breakin_probe(
    start,
    pid,
    source_ip,
    repetition
):
    """
    Supporting-warning scenario.

    Multiple warning events are used because a single warning
    is deliberately only SUSPICIOUS in the rule baseline.
    Ground truth is ATTACK because this is a controlled
    adversarial scenario.
    """

    count = random.randint(2, 6)

    lines = []

    for i in range(count):

        lines.append(
            breakin_warning(
                start + timedelta(
                    seconds=15 + i * 30
                ),
                pid,
                source_ip
            )
        )

    return lines


# ============================================================
# Scenario definitions
# ============================================================

SCENARIOS = [
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
            "normal_one_mistake",
        "ground_truth":
            "NORMAL",
        "builder":
            normal_one_mistake
    },
    {
        "scenario_type":
            "normal_two_mistakes",
        "ground_truth":
            "NORMAL",
        "builder":
            normal_two_mistakes
    },
    {
        "scenario_type":
            "normal_low_activity",
        "ground_truth":
            "NORMAL",
        "builder":
            normal_low_activity
    },
    {
        "scenario_type":
            "attack_repeated_failures",
        "ground_truth":
            "ATTACK",
        "builder":
            attack_repeated_failures
    },
    {
        "scenario_type":
            "attack_root_bruteforce",
        "ground_truth":
            "ATTACK",
        "builder":
            attack_root_bruteforce
    },
    {
        "scenario_type":
            "attack_username_enumeration",
        "ground_truth":
            "ATTACK",
        "builder":
            attack_username_enumeration
    },
    {
        "scenario_type":
            "attack_high_volume",
        "ground_truth":
            "ATTACK",
        "builder":
            attack_high_volume
    },
    {
        "scenario_type":
            "attack_identification_probe",
        "ground_truth":
            "ATTACK",
        "builder":
            attack_identification_probe
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
            "attack_breakin_probe",
        "ground_truth":
            "ATTACK",
        "builder":
            attack_breakin_probe
    }
]


# ============================================================
# Generate evaluation corpus
# ============================================================

def generate():

    SCENARIO_DIR.mkdir(
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

            # Give every scenario its own 5-minute interval.
            # Ten minutes between scenario starts ensures
            # complete separation.
            start = (
                BASE_TIME
                + timedelta(
                    minutes=10
                    * scenario_index
                )
            )

            pid = (
                20000
                + scenario_index
            )

            lines = scenario[
                "builder"
            ](
                start,
                pid,
                source_ip,
                repetition
            )

            scenario_id = (
                f"S{scenario_index:04d}"
            )

            window_start = (
                start.replace(
                    minute=(
                        start.minute // 5
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

    # Sort raw logs chronologically.
    #
    # The generator already emits them in order, but this also
    # protects us if scenario builders change later.
    def timestamp_key(line):

        prefix = " ".join(
            line.split()[:3]
        )

        return datetime.strptime(
            "2000 " + prefix,
            "%Y %b %d %H:%M:%S"
        )

    all_log_lines.sort(
        key=timestamp_key
    )

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

    with open(
        MANIFEST_OUTPUT,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        fieldnames = [
            "scenario_id",
            "scenario_type",
            "ground_truth",
            "source_ip",
            "window_start",
            "window_end",
            "raw_log_lines"
        ]

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()

        writer.writerows(
            manifest_rows
        )

    normal_count = sum(
        row["ground_truth"]
        == "NORMAL"
        for row in manifest_rows
    )

    attack_count = sum(
        row["ground_truth"]
        == "ATTACK"
        for row in manifest_rows
    )

    print(
        "\n============================================"
    )
    print(
        "LABELED OPENSSH EVALUATION DATA GENERATED"
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


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":

    generate()
