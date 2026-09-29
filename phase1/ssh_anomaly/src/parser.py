import re
from datetime import datetime
from pathlib import Path

import pandas as pd


# ============================================================
# Paths
# ============================================================

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")


# Development sample
SAMPLE_LOG = RAW_DIR / "OpenSSH_2k.log"

SAMPLE_OUTPUT = (
    PROCESSED_DIR / "ssh_events_2k.csv"
)


# Full OpenSSH dataset
FULL_LOG = RAW_DIR / "SSH.log"

FULL_OUTPUT = (
    PROCESSED_DIR / "ssh_events_full.csv"
)

# ============================================================
# Regex patterns
# ============================================================

# Example:
# Dec 10 06:55:48 LabSZ sshd[24200]: <message>
BASE_PATTERN = re.compile(
    r"^(?P<month>\w{3})\s+"
    r"(?P<day>\d{1,2})\s+"
    r"(?P<time>\d{2}:\d{2}:\d{2})\s+"
    r"(?P<hostname>\S+)\s+"
    r"sshd\[(?P<pid>\d+)\]:\s+"
    r"(?P<message>.*)$"
)


# ------------------------------------------------------------
# Authentication patterns
# ------------------------------------------------------------

FAILED_INVALID_PATTERN = re.compile(
    r"Failed password for invalid user "
    r"(?P<username>.+?) "
    r"from (?P<source_ip>\d{1,3}(?:\.\d{1,3}){3}) "
    r"port (?P<source_port>\d+)"
)


FAILED_PATTERN = re.compile(
    r"Failed password for "
    r"(?P<username>\S+) "
    r"from (?P<source_ip>\d{1,3}(?:\.\d{1,3}){3}) "
    r"port (?P<source_port>\d+)"
)


ACCEPTED_PATTERN = re.compile(
    r"Accepted \S+ for "
    r"(?P<username>\S+) "
    r"from (?P<source_ip>\d{1,3}(?:\.\d{1,3}){3}) "
    r"port (?P<source_port>\d+)"
)


INVALID_USER_PATTERN = re.compile(
    r"Invalid user "
    r"(?P<username>.+?) "
    r"from (?P<source_ip>\d{1,3}(?:\.\d{1,3}){3})"
)


# ------------------------------------------------------------
# Repeated-message pattern
#
# Example:
# message repeated 5 times:
# [ Failed password for root from 5.36.59.76 port 42393 ssh2]
# ------------------------------------------------------------

REPEATED_PATTERN = re.compile(
    r"message repeated (?P<count>\d+) times:\s*"
    r"\[\s*(?P<repeated_message>.*)\s*\]"
)


# ------------------------------------------------------------
# Generic IPv4 extraction
# ------------------------------------------------------------

IP_PATTERN = re.compile(
    r"(?P<source_ip>\d{1,3}(?:\.\d{1,3}){3})"
)


# ------------------------------------------------------------
# Authentication-failure username
#
# Example:
# authentication failure; ... rhost=5.36.59.76 user=root
# ------------------------------------------------------------

AUTH_FAILURE_USER_PATTERN = re.compile(
    r"\buser=(?P<username>\S+)"
)


# ------------------------------------------------------------
# rhost extraction
# ------------------------------------------------------------

RHOST_PATTERN = re.compile(
    r"\brhost=(?P<rhost>\S+)"
)


# ============================================================
# Helper functions
# ============================================================

def extract_ip(text):
    """
    Extract the first IPv4 address from a string.
    """

    match = IP_PATTERN.search(text)

    if match:
        return match.group("source_ip")

    return None


def extract_rhost(text):
    """
    Extract rhost=... when present.

    The rhost value may be either an IP address or hostname.
    """

    match = RHOST_PATTERN.search(text)

    if match:
        return match.group("rhost")

    return None


# ============================================================
# Parse one log line
# ============================================================

def parse_line(line, year=2000):

    # OpenSSH syslog timestamps in this dataset do not contain
    # a year.
    #
    # A constant placeholder year is therefore used only to
    # construct datetime objects.
    #
    # The anomaly model will use relative timing/window
    # behavior, not the calendar year.

    line = line.strip()

    base_match = BASE_PATTERN.match(line)

    if not base_match:
        return None

    data = base_match.groupdict()

    # --------------------------------------------------------
    # Construct timestamp
    # --------------------------------------------------------

    timestamp = datetime.strptime(
        f"{year} {data['month']} {data['day']} {data['time']}",
        "%Y %b %d %H:%M:%S"
    )

    message = data["message"]

    # --------------------------------------------------------
    # Default event
    # --------------------------------------------------------

    event = {
        "timestamp": timestamp,
        "hostname": data["hostname"],
        "pid": int(data["pid"]),
        "event_type": "other",
        "username": None,
        "source_ip": None,
        "source_port": None,
        "invalid_user": False,
        "success": False,
        "event_count": 1,
        "message": message
    }


    # ========================================================
    # 1. Repeated messages
    # ========================================================

    repeated_match = REPEATED_PATTERN.search(message)

    if repeated_match:

        count = int(repeated_match.group("count"))
        repeated_message = repeated_match.group(
            "repeated_message"
        )

        # Check whether the repeated message was a failed
        # password event.
        failed_invalid = FAILED_INVALID_PATTERN.search(
            repeated_message
        )

        if failed_invalid:

            event["event_type"] = "failed_login"
            event["username"] = failed_invalid.group(
                "username"
            )
            event["source_ip"] = failed_invalid.group(
                "source_ip"
            )
            event["source_port"] = int(
                failed_invalid.group("source_port")
            )
            event["invalid_user"] = True
            event["event_count"] = count

            return event


        failed = FAILED_PATTERN.search(
            repeated_message
        )

        if failed:

            event["event_type"] = "failed_login"
            event["username"] = failed.group(
                "username"
            )
            event["source_ip"] = failed.group(
                "source_ip"
            )
            event["source_port"] = int(
                failed.group("source_port")
            )
            event["event_count"] = count

            return event


        # A repeated message that we do not yet understand.
        event["event_type"] = "repeated_message"
        event["event_count"] = count

        return event


    # ========================================================
    # 2. Failed login - invalid user
    # ========================================================

    match = FAILED_INVALID_PATTERN.search(message)

    if match:

        event["event_type"] = "failed_login"
        event["username"] = match.group("username")
        event["source_ip"] = match.group("source_ip")
        event["source_port"] = int(
            match.group("source_port")
        )
        event["invalid_user"] = True

        return event


    # ========================================================
    # 3. Failed login - existing/normal username
    # ========================================================

    match = FAILED_PATTERN.search(message)

    if match:

        event["event_type"] = "failed_login"
        event["username"] = match.group("username")
        event["source_ip"] = match.group("source_ip")
        event["source_port"] = int(
            match.group("source_port")
        )

        return event


    # ========================================================
    # 4. Successful login
    # ========================================================

    match = ACCEPTED_PATTERN.search(message)

    if match:

        event["event_type"] = "successful_login"
        event["username"] = match.group("username")
        event["source_ip"] = match.group("source_ip")
        event["source_port"] = int(
            match.group("source_port")
        )
        event["success"] = True

        return event


    # ========================================================
    # 5. Invalid user
    # ========================================================

    match = INVALID_USER_PATTERN.search(message)

    if match:

        event["event_type"] = "invalid_user"
        event["username"] = match.group("username")
        event["source_ip"] = match.group("source_ip")
        event["invalid_user"] = True

        return event


    # ========================================================
    # 6. PAM authentication failure
    # ========================================================

    if "authentication failure" in message.lower():

        event["event_type"] = "auth_failure"

        # Try extracting username.
        user_match = AUTH_FAILURE_USER_PATTERN.search(
            message
        )

        if user_match:
            event["username"] = user_match.group(
                "username"
            )

        # rhost may be IP or hostname.
        rhost = extract_rhost(message)

        if rhost:

            # If rhost itself is an IP, store it.
            ip = extract_ip(rhost)

            if ip:
                event["source_ip"] = ip

        # Fallback: search entire message for IP.
        if event["source_ip"] is None:
            event["source_ip"] = extract_ip(message)

        return event


    # ========================================================
    # 7. Possible break-in warning
    # ========================================================

    if "POSSIBLE BREAK-IN ATTEMPT" in message:

        event["event_type"] = "breakin_warning"
        event["source_ip"] = extract_ip(message)

        return event


    # ========================================================
    # 8. Too many authentication failures
    # ========================================================

    if "Too many authentication failures" in message:

        event["event_type"] = "too_many_auth_failures"
        event["source_ip"] = extract_ip(message)

        # Some messages contain:
        # "for root"
        user_match = re.search(
            r"failures for (?P<username>\S+)",
            message
        )

        if user_match:
            event["username"] = user_match.group(
                "username"
            )

        return event


    # ========================================================
    # 9. PAM additional authentication failures
    # ========================================================

    pam_more_match = re.search(
        r"PAM (?P<count>\d+) more authentication failures",
        message
    )

    if pam_more_match:

        event["event_type"] = "pam_more_failures"
        event["event_count"] = int(
            pam_more_match.group("count")
        )

        event["source_ip"] = extract_ip(message)

        user_match = AUTH_FAILURE_USER_PATTERN.search(
            message
        )

        if user_match:
            event["username"] = user_match.group(
                "username"
            )

        return event


    # ========================================================
    # 10. Connection closed
    # ========================================================

    if "Connection closed by" in message:

        event["event_type"] = "connection_closed"
        event["source_ip"] = extract_ip(message)

        return event


    # ========================================================
    # 11. Received disconnect
    # ========================================================

    if "Received disconnect from" in message:

        event["event_type"] = "disconnect"
        event["source_ip"] = extract_ip(message)

        return event


    # ========================================================
    # 12. No SSH identification string
    # ========================================================

    if "Did not receive identification string from" in message:

        event["event_type"] = "no_identification"
        event["source_ip"] = extract_ip(message)

        return event

    # ========================================================
    # 13. PAM maximum retries exceeded
    # ========================================================

    if "PAM service(sshd) ignoring max retries" in message:

        event["event_type"] = "max_retries_exceeded"

        return event
    
    # ========================================================
    # Anything not yet classified
    # ========================================================

    return event


# ============================================================
# Parse entire log file
# ============================================================

def parse_log_file(file_path, year=2000):

    events = []

    total_lines = 0
    unparsed_lines = 0

    with open(
        file_path,
        "r",
        encoding="utf-8",
        errors="replace"
    ) as file:

        for line_number, line in enumerate(
            file,
            start=1
        ):

            total_lines += 1

            event = parse_line(
                line,
                year=year
            )

            if event is None:

                unparsed_lines += 1

                continue

            # Preserve original line number so that every
            # processed event can be traced back to the raw log.
            event["line_number"] = line_number

            events.append(event)

    df = pd.DataFrame(events)

    print(
        f"Total lines: {total_lines}"
    )

    print(
        f"Parsed lines: {len(events)}"
    )

    print(
        f"Unparsed lines: {unparsed_lines}"
    )

    return df


# ============================================================
# Main
# ============================================================
if __name__ == "__main__":

    # ========================================================
    # Choose dataset
    # ========================================================
    #
    # "sample" -> OpenSSH_2k.log
    # "full"   -> SSH.log
    #

    DATASET = "full"


    if DATASET == "sample":

        input_file = SAMPLE_LOG
        output_file = SAMPLE_OUTPUT

    elif DATASET == "full":

        input_file = FULL_LOG
        output_file = FULL_OUTPUT

    else:

        raise ValueError(
            "DATASET must be 'sample' or 'full'."
        )


    # ========================================================
    # Check input exists
    # ========================================================

    if not input_file.exists():

        raise FileNotFoundError(
            f"Input log not found: {input_file}"
        )


    # ========================================================
    # Prepare output directory
    # ========================================================

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    print(
        f"\nDataset: {DATASET}"
    )

    print(
        f"Input:   {input_file}"
    )

    print(
        f"Output:  {output_file}"
    )


    # ========================================================
    # Parse
    # ========================================================

    df = parse_log_file(
        input_file,
        year=2000
    )


    # ========================================================
    # Event distribution
    # ========================================================

    print("\nEvent types:")

    print(
        df["event_type"]
        .value_counts()
    )


    # ========================================================
    # Actual event occurrences
    # ========================================================

    print("\nEvent occurrences:")

    print(
        df.groupby(
            "event_type"
        )["event_count"]
        .sum()
        .sort_values(
            ascending=False
        )
    )


    # ========================================================
    # Remaining other messages
    # ========================================================

    other_df = df[
        df["event_type"] == "other"
    ]

    print(
        f"\nRemaining 'other' events: "
        f"{len(other_df)}"
    )


    print(
        "\nExample remaining 'other' messages:"
    )

    print(
        other_df["message"]
        .head(20)
        .to_string(index=False)
    )


    # ========================================================
    # Save
    # ========================================================

    df.to_csv(
        output_file,
        index=False
    )


    print(
        f"\nSaved parsed events to: "
        f"{output_file}"
    )