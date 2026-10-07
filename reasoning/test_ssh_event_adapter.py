from pathlib import Path
import json
import sys

from jsonschema import (
    Draft202012Validator,
    FormatChecker,
)


# ============================================================
# Project paths
# ============================================================

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

ADAPTER_DIR = (
    PROJECT_ROOT
    / "reasoning"
    / "adapters"
)

if str(ADAPTER_DIR) not in sys.path:
    sys.path.insert(
        0,
        str(ADAPTER_DIR)
    )

from ssh_event_adapter import (
    adapt_ssh_assessment
)


SCHEMA_FILE = (
    PROJECT_ROOT
    / "shared"
    / "schemas"
    / "event_schema.json"
)


# ============================================================
# Load schema
# ============================================================

with open(
    SCHEMA_FILE,
    "r",
    encoding="utf-8"
) as file:

    schema = json.load(file)


validator = Draft202012Validator(
    schema,
    format_checker=FormatChecker()
)


# ============================================================
# Helper: build representative SSH assessment
# ============================================================

def build_ssh_assessment(
    *,
    source_ip,
    window_start,
    window_end,
    evidence_state,
    anomaly_detected,
    detector_votes,
    detector_combination,
    confidence,
    explicit_security_signal=False,
    security_signals=None,
    rule_prediction="NORMAL",
    rule_anomalous=False,
    rule_suspicious=False,
    rule_score=0,
    triggered_rules=None,
    rule_evidence=None,
    if_prediction="NORMAL",
    if_anomalous=False,
    if_score=-0.10,
    ae_prediction="NORMAL",
    ae_anomalous=False,
    ae_error=0.01,
):

    if security_signals is None:
        security_signals = []

    if triggered_rules is None:
        triggered_rules = []

    if rule_evidence is None:
        rule_evidence = []

    return {
        "event_type":
            "ssh_behavior_assessment",

        "source_ip":
            source_ip,

        "window_start":
            window_start,

        "window_end":
            window_end,

        "anomaly_detected":
            anomaly_detected,

        "detector_votes":
            detector_votes,

        "detector_combination":
            detector_combination,

        "confidence":
            confidence,

        "evidence_state":
            evidence_state,

        "explicit_security_signal":
            explicit_security_signal,

        "security_signals":
            security_signals,

        "security_signal_evidence":
            (
                [
                    "Explicit OpenSSH security warning"
                ]
                if explicit_security_signal
                else []
            ),

        "rule": {
            "prediction":
                rule_prediction,

            "anomalous":
                rule_anomalous,

            "suspicious":
                rule_suspicious,

            "score":
                rule_score,

            "triggered_rules":
                triggered_rules,

            "evidence":
                rule_evidence,
        },

        "isolation_forest": {
            "prediction":
                if_prediction,

            "anomalous":
                if_anomalous,

            "anomaly_score":
                if_score,
        },

        "autoencoder": {
            "prediction":
                ae_prediction,

            "anomalous":
                ae_anomalous,

            "reconstruction_error":
                ae_error,

            "threshold":
                0.0857589915394783,
        },

        "evidence": {
            "failed_login_count":
                0,

            "invalid_user_count":
                0,

            "unique_users":
                0,

            "failure_ratio":
                0.0,

            "root_attempt_ratio":
                0.0,

            "breakin_warning_count":
                (
                    1
                    if explicit_security_signal
                    else 0
                ),

            "disconnect_count":
                0,

            "no_identification_count":
                0,

            "successful_login_count":
                0,

            "success_after_failures":
                0,
        },
    }


# ============================================================
# Test cases
#
# 2026 timestamps are used here because these are controlled
# Reasoning layer contract-test scenarios, not original Loghub times.
# ============================================================

test_cases = [

    # --------------------------------------------------------
    # 1. Explicit OpenSSH security event
    # --------------------------------------------------------

    {
        "name":
            "EXPLICIT_SECURITY_EVENT",

        "assessment":
            build_ssh_assessment(
                source_ip=
                    "203.0.113.10",

                window_start=
                    "2026-09-16T14:00:00Z",

                window_end=
                    "2026-09-16T14:05:00Z",

                evidence_state=
                    "EXPLICIT_SECURITY_EVENT",

                anomaly_detected=
                    True,

                detector_votes=
                    0,

                detector_combination=
                    "NONE",

                confidence=
                    "EXPLICIT_SECURITY_SIGNAL",

                explicit_security_signal=
                    True,

                security_signals=[
                    "OPENSSH_BREAKIN_WARNING"
                ],

                rule_prediction=
                    "SUSPICIOUS",

                rule_suspicious=
                    True,
            ),
    },


    # --------------------------------------------------------
    # 2. High-confidence anomaly
    #
    # RULE + AUTOENCODER
    # --------------------------------------------------------

    {
        "name":
            "HIGH_CONFIDENCE_ANOMALY",

        "assessment":
            build_ssh_assessment(
                source_ip=
                    "203.0.113.20",

                window_start=
                    "2026-09-16T14:10:00Z",

                window_end=
                    "2026-09-16T14:15:00Z",

                evidence_state=
                    "HIGH_CONFIDENCE_ANOMALY",

                anomaly_detected=
                    True,

                detector_votes=
                    2,

                detector_combination=
                    "RULE+AE",

                confidence=
                    "MEDIUM",

                rule_prediction=
                    "ANOMALOUS",

                rule_anomalous=
                    True,

                rule_score=
                    1,

                triggered_rules=[
                    "ROOT_TARGETING"
                ],

                rule_evidence=[
                    "100% of failed attempts targeted root"
                ],

                ae_prediction=
                    "ANOMALOUS",

                ae_anomalous=
                    True,

                ae_error=
                    0.125,
            ),
    },


    # --------------------------------------------------------
    # 3. Single-detector anomaly candidate
    #
    # Isolation Forest only
    # --------------------------------------------------------

    {
        "name":
            "ANOMALY_CANDIDATE",

        "assessment":
            build_ssh_assessment(
                source_ip=
                    "203.0.113.30",

                window_start=
                    "2026-09-16T14:20:00Z",

                window_end=
                    "2026-09-16T14:25:00Z",

                evidence_state=
                    "ANOMALY_CANDIDATE",

                anomaly_detected=
                    True,

                detector_votes=
                    1,

                detector_combination=
                    "IF",

                confidence=
                    "LOW",

                if_prediction=
                    "ANOMALOUS",

                if_anomalous=
                    True,

                if_score=
                    0.12,
            ),
    },


    # --------------------------------------------------------
    # 4. No anomaly evidence
    # --------------------------------------------------------

    {
        "name":
            "NO_ANOMALY_EVIDENCE",

        "assessment":
            build_ssh_assessment(
                source_ip=
                    "203.0.113.40",

                window_start=
                    "2026-09-16T14:30:00Z",

                window_end=
                    "2026-09-16T14:35:00Z",

                evidence_state=
                    "NO_ANOMALY_EVIDENCE",

                anomaly_detected=
                    False,

                detector_votes=
                    0,

                detector_combination=
                    "NONE",

                confidence=
                    "NONE",
            ),
    },
]


# ============================================================
# Execute tests
# ============================================================

print(
    "\n============================================"
)

print(
    "SSH ADAPTER - ALL EVIDENCE STATES"
)

print(
    "============================================"
)


passed = 0


for index, test_case in enumerate(
    test_cases,
    start=1
):

    name = test_case[
        "name"
    ]

    ssh_assessment = test_case[
        "assessment"
    ]

    event_id = (
        f"EVT-SSH-STATE-TEST-{index:03d}"
    )

    # --------------------------------------------------------
    # Convert Evidence layer -> Reasoning layer
    # --------------------------------------------------------

    common_event = (
        adapt_ssh_assessment(
            ssh_assessment,

            dataset_name=
                "DC-Guardian Reasoning layer "
                "Controlled Contract Test",

            source_type=
                "CONTROLLED_TEST",

            event_id=
                event_id,
        )
    )


    # --------------------------------------------------------
    # Validate against common schema
    # --------------------------------------------------------

    errors = sorted(
        validator.iter_errors(
            common_event
        ),
        key=lambda error: list(
            error.absolute_path
        )
    )


    if errors:

        print(
            f"\nFAIL: {name}"
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
                f"  Field: {location}"
            )

            print(
                f"  Error: {error.message}"
            )

        continue


    # --------------------------------------------------------
    # Semantic checks
    #
    # JSON Schema validates structure.
    # These assertions validate that the adapter preserved
    # the actual SSH meaning.
    # --------------------------------------------------------

    assert (
        common_event[
            "assessment"
        ][
            "state"
        ]
        == name
    )


    assert (
        common_event[
            "assessment"
        ][
            "anomaly_detected"
        ]
        ==
        ssh_assessment[
            "anomaly_detected"
        ]
    )


    assert (
        common_event[
            "evidence"
        ][
            "detector_votes"
        ]
        ==
        ssh_assessment[
            "detector_votes"
        ]
    )


    assert (
        common_event[
            "evidence"
        ][
            "detector_combination"
        ]
        ==
        ssh_assessment[
            "detector_combination"
        ]
    )


    assert (
        common_event[
            "entities"
        ][
            "source_ip"
        ]
        ==
        ssh_assessment[
            "source_ip"
        ]
    )


    # --------------------------------------------------------
    # No topology should have been invented yet.
    # --------------------------------------------------------

    assert (
        common_event[
            "entities"
        ][
            "server_id"
        ]
        is None
    )


    assert (
        common_event[
            "location"
        ][
            "zone_id"
        ]
        is None
    )


    assert (
        common_event[
            "provenance"
        ][
            "synthetic_mapping"
        ]
        is False
    )


    # --------------------------------------------------------
    # State-specific checks
    # --------------------------------------------------------

    if (
        name
        == "EXPLICIT_SECURITY_EVENT"
    ):

        assert (
            common_event[
                "evidence"
            ][
                "detector_votes"
            ]
            == 0
        )

        assert (
            common_event[
                "evidence"
            ][
                "explicit_security_signal"
            ]
            is True
        )


    elif (
        name
        == "HIGH_CONFIDENCE_ANOMALY"
    ):

        assert (
            common_event[
                "evidence"
            ][
                "detector_votes"
            ]
            >= 2
        )


    elif (
        name
        == "ANOMALY_CANDIDATE"
    ):

        assert (
            common_event[
                "evidence"
            ][
                "detector_votes"
            ]
            == 1
        )


    elif (
        name
        == "NO_ANOMALY_EVIDENCE"
    ):

        assert (
            common_event[
                "evidence"
            ][
                "detector_votes"
            ]
            == 0
        )

        assert (
            common_event[
                "assessment"
            ][
                "anomaly_detected"
            ]
            is False
        )


    print(
        f"\nPASS: {name}"
    )

    print(
        f"  Event ID: "
        f"{common_event['event_id']}"
    )

    print(
        f"  Votes: "
        f"{common_event['evidence']['detector_votes']}"
    )

    print(
        f"  Combination: "
        f"{common_event['evidence']['detector_combination']}"
    )

    print(
        f"  Anomaly detected: "
        f"{common_event['assessment']['anomaly_detected']}"
    )


    passed += 1


# ============================================================
# Final result
# ============================================================

print(
    "\n============================================"
)

print(
    "TEST SUMMARY"
)

print(
    "============================================"
)


print(
    f"Passed: {passed}/{len(test_cases)}"
)


if passed != len(
    test_cases
):

    raise SystemExit(
        "One or more SSH adapter "
        "state tests failed."
    )


print(
    "\nPASS: All four frozen SSH evidence "
    "states map correctly to "
    "DC-Guardian schema v1.0."
)


print(
    "PASS: Adapter did not introduce "
    "synthetic topology mappings."
)


print(
    "\n============================================"
)

print(
    "SSH REASONING LAYER ADAPTER CONTRACT PASSED"
)

print(
    "============================================"
)
