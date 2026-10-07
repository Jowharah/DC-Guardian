from pathlib import Path
import json

from jsonschema import (
    Draft202012Validator,
    FormatChecker,
)


# ============================================================
# Paths
# ============================================================

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

SCHEMA_FILE = (
    PROJECT_ROOT
    / "shared"
    / "schemas"
    / "event_schema.json"
)

EXAMPLE_FILE = (
    PROJECT_ROOT
    / "shared"
    / "schemas"
    / "examples"
    / "ssh_event_example.json"
)


# ============================================================
# Load JSON
# ============================================================

def load_json(file_path):

    if not file_path.exists():

        raise FileNotFoundError(
            f"File not found: {file_path}"
        )

    with open(
        file_path,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":

    print(
        "\n============================================"
    )
    print(
        "DC-GUARDIAN EVENT SCHEMA VALIDATION"
    )
    print(
        "============================================"
    )

    schema = load_json(
        SCHEMA_FILE
    )

    event = load_json(
        EXAMPLE_FILE
    )

    # --------------------------------------------------------
    # First validate the schema itself.
    # --------------------------------------------------------

    Draft202012Validator.check_schema(
        schema
    )

    print(
        "\nPASS: event_schema.json "
        "is a valid Draft 2020-12 schema."
    )

    # --------------------------------------------------------
    # Validate the event.
    #
    # FormatChecker ensures date-time fields are actually
    # checked rather than treated as plain strings.
    # --------------------------------------------------------

    validator = Draft202012Validator(
        schema,
        format_checker=FormatChecker()
    )

    errors = sorted(
        validator.iter_errors(event),
        key=lambda error: list(
            error.absolute_path
        )
    )

    if errors:

        print(
            "\nFAIL: Event validation errors:"
        )

        for error in errors:

            location = ".".join(
                str(item)
                for item
                in error.absolute_path
            )

            if not location:
                location = "<root>"

            print(
                f"\n  Field: {location}"
            )

            print(
                f"  Error: {error.message}"
            )

        raise SystemExit(1)

    print(
        "PASS: ssh_event_example.json "
        "matches schema version 1.0."
    )

    print(
        "\nEvent ID:",
        event["event_id"]
    )

    print(
        "Domain:",
        event["domain"]
    )

    print(
        "Event type:",
        event["event_type"]
    )

    print(
        "Assessment:",
        event["assessment"]["state"]
    )

    print(
        "\n============================================"
    )
    print(
        "PHASE 2 EVENT CONTRACT TEST PASSED"
    )
    print(
        "============================================"
    )