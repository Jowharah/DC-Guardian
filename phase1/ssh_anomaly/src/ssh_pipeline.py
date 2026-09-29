from pathlib import Path
import json
import sys

import pandas as pd


# ============================================================
# Project imports
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from parser import parse_log_file
from feature_engineering import (
    prepare_events,
    build_basic_features,
)
from ssh_detector import SSHAnomalyDetector


# ============================================================
# SSH Pipeline
# ============================================================

class SSHPipeline:
    """
    End-to-end SSH Detector v1 runtime pipeline.

    Raw OpenSSH log file
        -> parser
        -> source-IP filtering / 5-minute windows
        -> feature engineering
        -> frozen SSHAnomalyDetector
        -> standardized security assessments

    No training, fitting, threshold selection, or model
    modification occurs in this class.
    """

    def __init__(
        self,
        year=2000
    ):

        self.year = int(year)

        # Load the frozen persisted detector once.
        self.detector = (
            SSHAnomalyDetector()
        )


    # ========================================================
    # Parse raw log file
    # ========================================================

    def parse(
        self,
        log_file
    ):

        log_file = Path(
            log_file
        )

        if not log_file.exists():

            raise FileNotFoundError(
                f"SSH log file not found: "
                f"{log_file}"
            )


        parsed = parse_log_file(
            log_file,
            year=self.year
        )


        if parsed.empty:

            return parsed


        return parsed


    # ========================================================
    # Build model-ready feature windows
    # ========================================================

    def build_features(
        self,
        parsed_events
    ):

        if not isinstance(
            parsed_events,
            pd.DataFrame
        ):

            raise TypeError(
                "parsed_events must be "
                "a pandas DataFrame."
            )


        if parsed_events.empty:

            return pd.DataFrame()


        required_columns = [
            "timestamp",
            "source_ip",
            "event_type",
            "event_count",
            "username",
        ]


        missing = [
            column
            for column
            in required_columns
            if column
            not in parsed_events.columns
        ]


        if missing:

            raise ValueError(
                "Parsed event table is missing: "
                + ", ".join(
                    missing
                )
            )


        # parser.parse_log_file() already produces datetime
        # objects, but normalize defensively for integration.
        parsed_events = (
            parsed_events.copy()
        )


        parsed_events[
            "timestamp"
        ] = pd.to_datetime(
            parsed_events[
                "timestamp"
            ],
            errors="coerce"
        )


        if (
            parsed_events[
                "timestamp"
            ]
            .isna()
            .any()
        ):

            raise ValueError(
                "Parsed SSH events contain "
                "invalid timestamps."
            )


        events = prepare_events(
            parsed_events
        )


        if events.empty:

            return pd.DataFrame()


        features = (
            build_basic_features(
                events
            )
        )


        return features


    # ========================================================
    # Assess engineered windows
    # ========================================================

    def assess_features(
        self,
        features
    ):

        if not isinstance(
            features,
            pd.DataFrame
        ):

            raise TypeError(
                "features must be "
                "a pandas DataFrame."
            )


        if features.empty:

            return []


        return self.detector.detect(
            features
        )


    # ========================================================
    # Full end-to-end file pipeline
    # ========================================================

    def assess_log_file(
        self,
        log_file
    ):

        parsed = self.parse(
            log_file
        )


        if parsed.empty:

            return []


        features = self.build_features(
            parsed
        )


        if features.empty:

            return []


        return self.assess_features(
            features
        )


    # ========================================================
    # Full result bundle
    # ========================================================

    def process_log_file(
        self,
        log_file
    ):

        """
        Return parser output, feature windows, and assessments.

        Useful for debugging, validation, and auditability.
        """

        parsed = self.parse(
            log_file
        )


        if parsed.empty:

            return {
                "parsed_events":
                    parsed,

                "features":
                    pd.DataFrame(),

                "assessments":
                    [],
            }


        features = self.build_features(
            parsed
        )


        assessments = (
            self.assess_features(
                features
            )
            if not features.empty
            else []
        )


        return {
            "parsed_events":
                parsed,

            "features":
                features,

            "assessments":
                assessments,
        }


    # ========================================================
    # Security-event filtering helpers
    # ========================================================

    @staticmethod
    def security_relevant(
        assessments
    ):

        """
        Keep every assessment that contains security evidence.

        This includes:
          - EXPLICIT_SECURITY_EVENT
          - HIGH_CONFIDENCE_ANOMALY
          - ANOMALY_CANDIDATE

        NO_ANOMALY_EVIDENCE rows are omitted.
        """

        return [
            assessment
            for assessment
            in assessments
            if assessment.get(
                "evidence_state"
            )
            != "NO_ANOMALY_EVIDENCE"
        ]


    @staticmethod
    def high_priority(
        assessments
    ):

        """
        Keep only the strongest v1 evidence states.

        Single-detector ANOMALY_CANDIDATE rows are not discarded
        from the main pipeline; this helper simply allows the
        caller to request a higher-confidence subset.
        """

        high_states = {
            "EXPLICIT_SECURITY_EVENT",
            "HIGH_CONFIDENCE_ANOMALY",
        }


        return [
            assessment
            for assessment
            in assessments
            if assessment.get(
                "evidence_state"
            )
            in high_states
        ]


# ============================================================
# JSON serialization helpers
# ============================================================

def save_assessments_json(
    assessments,
    output_file
):

    output_file = Path(
        output_file
    )


    output_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            assessments,
            file,
            indent=2
        )


# ============================================================
# Command-line smoke test / file inference
# ============================================================

if __name__ == "__main__":

    # --------------------------------------------------------
    # Default test input.
    #
    # You can replace this with another raw OpenSSH log file.
    # --------------------------------------------------------

    INPUT_FILE = (
        PROJECT_ROOT
        / "data"
        / "raw"
        / "SSH.log"
    )


    OUTPUT_FILE = (
        PROJECT_ROOT
        / "data"
        / "processed"
        / "ssh_pipeline_assessments.json"
    )


    print(
        "\n============================================"
    )

    print(
        "DC-GUARDIAN SSH PIPELINE v1"
    )

    print(
        "============================================"
    )


    print(
        f"\nInput: {INPUT_FILE}"
    )


    # --------------------------------------------------------
    # Load frozen detector once.
    # --------------------------------------------------------

    pipeline = SSHPipeline(
        year=2000
    )


    print(
        "PASS: Frozen SSH Detector v1 loaded."
    )


    # --------------------------------------------------------
    # End-to-end processing
    # --------------------------------------------------------

    result = (
        pipeline.process_log_file(
            INPUT_FILE
        )
    )


    parsed = result[
        "parsed_events"
    ]

    features = result[
        "features"
    ]

    assessments = result[
        "assessments"
    ]


    security_events = (
        pipeline.security_relevant(
            assessments
        )
    )


    high_priority_events = (
        pipeline.high_priority(
            assessments
        )
    )


    print(
        "\n============================================"
    )

    print(
        "PIPELINE SUMMARY"
    )

    print(
        "============================================"
    )


    print(
        f"Parsed SSH events: "
        f"{len(parsed)}"
    )


    print(
        f"Behavior windows: "
        f"{len(features)}"
    )


    print(
        f"Assessments: "
        f"{len(assessments)}"
    )


    print(
        f"Security-relevant assessments: "
        f"{len(security_events)}"
    )


    print(
        f"High-priority assessments: "
        f"{len(high_priority_events)}"
    )


    # --------------------------------------------------------
    # Evidence-state distribution
    # --------------------------------------------------------

    if assessments:

        evidence_states = (
            pd.Series(
                [
                    item[
                        "evidence_state"
                    ]
                    for item
                    in assessments
                ]
            )
            .value_counts()
        )


        print(
            "\nEvidence-state distribution:"
        )


        print(
            evidence_states
            .to_string()
        )


    # --------------------------------------------------------
    # Save standardized assessments.
    # --------------------------------------------------------

    save_assessments_json(
        assessments,
        OUTPUT_FILE
    )


    print(
        f"\nSaved assessments to: "
        f"{OUTPUT_FILE}"
    )


    # --------------------------------------------------------
    # Print a small example only.
    # --------------------------------------------------------

    if security_events:

        print(
            "\nExample security assessment:"
        )


        print(
            json.dumps(
                security_events[0],
                indent=2
            )
        )


    print(
        "\n============================================"
    )

    print(
        "SSH PIPELINE v1 PASSED"
    )

    print(
        "============================================"
    )
