from pathlib import Path
import json

import joblib
import numpy as np
import pandas as pd
import tensorflow as tf

from shared.model_integrity import verify_sha256


# ============================================================
# Paths
# ============================================================

SSH_ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = SSH_ROOT / "models"

IF_MODEL_FILE = (
    MODEL_DIR / "isolation_forest.joblib"
)

IF_SCALER_FILE = (
    MODEL_DIR / "isolation_forest_scaler.joblib"
)

AE_MODEL_FILE = (
    MODEL_DIR / "autoencoder_log.keras"
)

AE_SCALER_FILE = (
    MODEL_DIR / "autoencoder_log_scaler.joblib"
)

AE_CONFIG_FILE = (
    MODEL_DIR / "autoencoder_log_config.json"
)


# ============================================================
# Frozen artifact integrity
# ============================================================
#
# joblib uses pickle-compatible deserialization. Keras model
# files are also executable model artifacts. Verify every
# frozen artifact before loading/deserializing it.
# ============================================================

ARTIFACT_SHA256 = {
    IF_MODEL_FILE:
        "91215800c9cb7828ec9e42dc6edd2446"
        "3eb967d03c4b1813cb44c9731f5c0ec9",

    IF_SCALER_FILE:
        "a4605e3df5c8dac74accdcf7fb0e5159"
        "875890d376b39bc8461df2046331812d",

    AE_MODEL_FILE:
        "29856de98e5eaed7e6d1e49f6767e483"
        "51302d8e521f642cfdd61d0a87880cc5",

    AE_SCALER_FILE:
        "96110d5bd70f53e02ca083215e763311"
        "9fd3305c315dbe121906daefd194e82e",

    AE_CONFIG_FILE:
        "ff210d210167833edcf18eb6da462917"
        "c88f1f529805b767d81d15d85620ba1e",
}


# ============================================================
# Isolation Forest feature order
# ============================================================
#
# Must exactly match Isolation Forest training.
# ============================================================

IF_FEATURES = [
    "failed_login_count",
    "invalid_user_count",
    "unique_users",
    "failure_ratio",
    "root_attempt_ratio",
    "breakin_warning_count",
    "disconnect_count",
    "no_identification_count"
]


# ============================================================
# Rule Baseline v1 configuration
# ============================================================
#
# These are the frozen rule thresholds used during the
# full-data experiment.
# ============================================================

FAILED_LOGIN_THRESHOLD = 10

UNIQUE_USERS_THRESHOLD = 5

ROOT_MIN_FAILURES = 5

ROOT_RATIO_THRESHOLD = 0.80


# ============================================================
# SSH Detector
# ============================================================

class SSHAnomalyDetector:

    def __init__(self):

        # ----------------------------------------------------
        # Validate required artifacts
        # ----------------------------------------------------

        required_files = [
            IF_MODEL_FILE,
            IF_SCALER_FILE,
            AE_MODEL_FILE,
            AE_SCALER_FILE,
            AE_CONFIG_FILE
        ]

        missing_files = [
            str(file_path)
            for file_path in required_files
            if not file_path.exists()
        ]

        if missing_files:

            raise FileNotFoundError(
                "Missing model artifacts: "
                + ", ".join(
                    missing_files
                )
            )


        # ----------------------------------------------------
        # Verify frozen artifacts before any deserialization
        # ----------------------------------------------------

        for (
            artifact_path,
            expected_sha256,
        ) in ARTIFACT_SHA256.items():

            verify_sha256(
                artifact_path,
                expected_sha256,
            )


        # ----------------------------------------------------
        # Load Isolation Forest
        # ----------------------------------------------------

        self.if_model = joblib.load(
            IF_MODEL_FILE
        )

        self.if_scaler = joblib.load(
            IF_SCALER_FILE
        )


        # ----------------------------------------------------
        # Load Autoencoder
        # ----------------------------------------------------

        self.ae_model = (
            tf.keras.models.load_model(
                AE_MODEL_FILE
            )
        )

        self.ae_scaler = joblib.load(
            AE_SCALER_FILE
        )


        # ----------------------------------------------------
        # Load Autoencoder configuration
        # ----------------------------------------------------

        with open(
            AE_CONFIG_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            self.ae_config = json.load(
                file
            )


        self.ae_features = (
            self.ae_config[
                "model_features"
            ]
        )

        self.ae_count_features = (
            self.ae_config[
                "count_features"
            ]
        )

        self.ae_threshold = float(
            self.ae_config[
                "threshold"
            ]
        )


        # ----------------------------------------------------
        # Validate persisted artifact dimensions
        # ----------------------------------------------------

        self._validate_artifacts()


    # ========================================================
    # Validate persisted models
    # ========================================================

    def _validate_artifacts(self):

        if hasattr(
            self.if_scaler,
            "n_features_in_"
        ):

            if (
                self.if_scaler.n_features_in_
                != len(IF_FEATURES)
            ):

                raise ValueError(
                    "Isolation Forest scaler "
                    "feature mismatch."
                )


        if hasattr(
            self.if_model,
            "n_features_in_"
        ):

            if (
                self.if_model.n_features_in_
                != len(IF_FEATURES)
            ):

                raise ValueError(
                    "Isolation Forest model "
                    "feature mismatch."
                )


        if hasattr(
            self.ae_scaler,
            "n_features_in_"
        ):

            if (
                self.ae_scaler.n_features_in_
                != len(self.ae_features)
            ):

                raise ValueError(
                    "Autoencoder scaler "
                    "feature mismatch."
                )


        if (
            self.ae_model.input_shape[-1]
            != len(self.ae_features)
        ):

            raise ValueError(
                "Autoencoder input dimension "
                "does not match configuration."
            )


        if (
            self.ae_model.output_shape[-1]
            != len(self.ae_features)
        ):

            raise ValueError(
                "Autoencoder output dimension "
                "does not match configuration."
            )


    # ========================================================
    # Validate incoming feature table
    # ========================================================

    def _validate_input(
        self,
        df
    ):

        required_features = set(
            IF_FEATURES
        )

        required_features.update(
            self.ae_features
        )

        missing_features = [
            feature
            for feature in required_features
            if feature not in df.columns
        ]

        if missing_features:

            raise ValueError(
                "Missing required SSH features: "
                + ", ".join(
                    missing_features
                )
            )


        feature_columns = list(
            required_features
        )


        if (
            df[feature_columns]
            .isna()
            .any()
            .any()
        ):

            raise ValueError(
                "Input contains missing "
                "model feature values."
            )


    # ========================================================
    # Rule detector
    # ========================================================

    def _run_rules(
        self,
        row
    ):

        failed_logins = int(
            row[
                "failed_login_count"
            ]
        )

        unique_users = int(
            row[
                "unique_users"
            ]
        )

        root_ratio = float(
            row[
                "root_attempt_ratio"
            ]
        )

        breakin_warnings = int(
            row[
                "breakin_warning_count"
            ]
        )


        triggered_rules = []

        evidence = []


        # ----------------------------------------------------
        # Rule 1:
        # Repeated authentication failures
        # ----------------------------------------------------

        if (
            failed_logins
            >= FAILED_LOGIN_THRESHOLD
        ):

            triggered_rules.append(
                "REPEATED_FAILURES"
            )

            evidence.append(
                f"{failed_logins} failed "
                "logins in 5 minutes"
            )


        # ----------------------------------------------------
        # Rule 2:
        # Username enumeration
        # ----------------------------------------------------

        if (
            unique_users
            >= UNIQUE_USERS_THRESHOLD
        ):

            triggered_rules.append(
                "USERNAME_ENUMERATION"
            )

            evidence.append(
                f"{unique_users} unique "
                "usernames attempted"
            )


        # ----------------------------------------------------
        # Rule 3:
        # Root targeting
        # ----------------------------------------------------

        if (
            failed_logins
            >= ROOT_MIN_FAILURES
            and
            root_ratio
            >= ROOT_RATIO_THRESHOLD
        ):

            triggered_rules.append(
                "ROOT_TARGETING"
            )

            evidence.append(
                f"{root_ratio * 100:.0f}% "
                "of failed attempts "
                "targeted root"
            )


        # ----------------------------------------------------
        # Break-in warnings are supporting evidence.
        #
        # They do not count toward the strong rule score,
        # matching our frozen Rule Baseline v1.
        # ----------------------------------------------------

        if breakin_warnings > 0:

            evidence.append(
                f"{breakin_warnings} "
                "OpenSSH break-in warning(s)"
            )


        rule_score = len(
            triggered_rules
        )


        # ----------------------------------------------------
        # Preserve the three-state rule output.
        # ----------------------------------------------------

        if rule_score >= 1:

            prediction = "ANOMALOUS"

        elif breakin_warnings > 0:

            prediction = "SUSPICIOUS"

        else:

            prediction = "NORMAL"


        return {
            "prediction":
                prediction,

            "anomalous":
                prediction
                == "ANOMALOUS",

            "suspicious":
                prediction
                == "SUSPICIOUS",

            "score":
                rule_score,

            "triggered_rules":
                triggered_rules,

            "evidence":
                evidence
        }


    # ========================================================
    # Isolation Forest inference
    # ========================================================

    def _run_isolation_forest(
        self,
        df
    ):

        X = df[
            IF_FEATURES
        ].copy()


        # ----------------------------------------------------
        # IMPORTANT:
        # transform(), never fit_transform().
        # ----------------------------------------------------

        X_scaled = (
            self.if_scaler.transform(
                X
            )
        )


        raw_predictions = (
            self.if_model.predict(
                X_scaled
            )
        )


        decision_scores = (
            self.if_model
            .decision_function(
                X_scaled
            )
        )


        predictions = np.where(
            raw_predictions == -1,
            "ANOMALOUS",
            "NORMAL"
        )


        anomaly_scores = (
            -decision_scores
        )


        return (
            predictions,
            anomaly_scores
        )


    # ========================================================
    # Autoencoder preprocessing
    # ========================================================

    def _prepare_autoencoder_input(
        self,
        df
    ):

        X = df[
            self.ae_features
        ].copy()


        # ----------------------------------------------------
        # Reproduce training preprocessing exactly:
        #
        # count features -> log1p
        # ratio features -> unchanged
        # then saved RobustScaler
        # ----------------------------------------------------

        for feature in (
            self.ae_count_features
        ):

            if (
                X[feature] < 0
            ).any():

                raise ValueError(
                    f"{feature} contains "
                    "negative values."
                )


            X[feature] = np.log1p(
                X[feature]
            )


        X_scaled = (
            self.ae_scaler.transform(
                X
            )
        )


        return X_scaled.astype(
            np.float32
        )


    # ========================================================
    # Autoencoder inference
    # ========================================================

    def _run_autoencoder(
        self,
        df
    ):

        X_scaled = (
            self._prepare_autoencoder_input(
                df
            )
        )


        reconstructed = (
            self.ae_model.predict(
                X_scaled,
                verbose=0
            )
        )


        reconstruction_errors = (
            np.mean(
                np.square(
                    X_scaled
                    - reconstructed
                ),
                axis=1
            )
        )


        predictions = np.where(
            reconstruction_errors
            > self.ae_threshold,
            "ANOMALOUS",
            "NORMAL"
        )


        return (
            predictions,
            reconstruction_errors
        )


    # ========================================================
    # Explicit OpenSSH security signals
    # ========================================================

    @staticmethod
    def _run_explicit_security_signals(row):

        """
        Operational security signals emitted directly by
        OpenSSH or derived from high-confidence event context.

        These signals are kept separate from the three model
        votes so historical Rule/IF/AE comparisons remain
        reproducible.
        """

        signals = []
        evidence = []

        breakin_warnings = int(
            row["breakin_warning_count"]
        )

        if breakin_warnings > 0:

            signals.append(
                "OPENSSH_BREAKIN_WARNING"
            )

            evidence.append(
                f"{breakin_warnings} explicit "
                "OpenSSH POSSIBLE BREAK-IN "
                "ATTEMPT warning(s)"
            )

        return {
            "detected": bool(signals),
            "signals": signals,
            "evidence": evidence
        }


    # ========================================================
    # Confidence from detector agreement
    # ========================================================

    @staticmethod
    def _confidence_from_votes(
        votes
    ):

        if votes == 3:

            return "HIGH"

        if votes == 2:

            return "MEDIUM"

        if votes == 1:

            return "LOW"

        return "NONE"


    # ========================================================
    # Exact detector combination
    # ========================================================

    @staticmethod
    def _detector_combination(
        rule_anomalous,
        if_anomalous,
        ae_anomalous
    ):

        detectors = []


        if rule_anomalous:

            detectors.append(
                "RULE"
            )


        if if_anomalous:

            detectors.append(
                "IF"
            )


        if ae_anomalous:

            detectors.append(
                "AE"
            )


        if not detectors:

            return "NONE"


        return "+".join(
            detectors
        )


    # ========================================================
    # Operational evidence state
    # ========================================================

    @staticmethod
    def _evidence_state(
        votes,
        explicit_security_signal
    ):

        """
        Convert detector evidence into the v1 integration
        contract without treating every anomaly as equivalent.

        Priority:
          1. Explicit OpenSSH security signal
          2. Two-or-more detector consensus
          3. Single-detector anomaly candidate
          4. No anomaly evidence
        """

        if explicit_security_signal:
            return "EXPLICIT_SECURITY_EVENT"

        if votes >= 2:
            return "HIGH_CONFIDENCE_ANOMALY"

        if votes == 1:
            return "ANOMALY_CANDIDATE"

        return "NO_ANOMALY_EVIDENCE"


    # ========================================================
    # Detect a DataFrame of feature windows
    # ========================================================

    def detect(
        self,
        df
    ):

        if not isinstance(
            df,
            pd.DataFrame
        ):

            raise TypeError(
                "detect() expects "
                "a pandas DataFrame."
            )


        if df.empty:

            return []


        df = df.copy()


        # ----------------------------------------------------
        # Validate schema
        # ----------------------------------------------------

        self._validate_input(
            df
        )


        # ----------------------------------------------------
        # Run ML detectors in batches
        # ----------------------------------------------------

        (
            if_predictions,
            if_scores
        ) = self._run_isolation_forest(
            df
        )


        (
            ae_predictions,
            ae_errors
        ) = self._run_autoencoder(
            df
        )


        # ----------------------------------------------------
        # Build standardized output
        # ----------------------------------------------------

        outputs = []


        for position, (
            index,
            row
        ) in enumerate(
            df.iterrows()
        ):

            rule_result = (
                self._run_rules(
                    row
                )
            )


            if_prediction = (
                if_predictions[
                    position
                ]
            )

            ae_prediction = (
                ae_predictions[
                    position
                ]
            )


            if_anomalous = (
                if_prediction
                == "ANOMALOUS"
            )

            ae_anomalous = (
                ae_prediction
                == "ANOMALOUS"
            )

            rule_anomalous = (
                rule_result[
                    "anomalous"
                ]
            )


            votes = (
                int(rule_anomalous)
                + int(if_anomalous)
                + int(ae_anomalous)
            )


            # ------------------------------------------------
            # Explicit OpenSSH security signals are operational
            # evidence, not additional model votes.
            # ------------------------------------------------

            security_signal_result = (
                self._run_explicit_security_signals(
                    row
                )
            )

            explicit_security_signal = bool(
                security_signal_result[
                    "detected"
                ]
            )


            # ------------------------------------------------
            # Operational detection policy
            #
            # Detect when:
            #   - at least one strong detector votes anomaly, OR
            #   - OpenSSH emits an explicit security signal.
            #
            # detector_votes remains strictly RULE + IF + AE.
            # ------------------------------------------------

            anomaly_detected = (
                votes > 0
                or explicit_security_signal
            )


            confidence = (
                self._confidence_from_votes(
                    votes
                )
            )

            # An explicit OpenSSH warning should never be
            # represented as "NONE" confidence simply because
            # the three anomaly models did not vote.
            if (
                explicit_security_signal
                and confidence == "NONE"
            ):

                confidence = (
                    "EXPLICIT_SECURITY_SIGNAL"
                )


            combination = (
                self._detector_combination(
                    rule_anomalous,
                    if_anomalous,
                    ae_anomalous
                )
            )


            evidence_state = (
                self._evidence_state(
                    votes,
                    explicit_security_signal
                )
            )


            # ------------------------------------------------
            # Standardized evidence
            # ------------------------------------------------

            evidence = {
                "failed_login_count":
                    int(
                        row[
                            "failed_login_count"
                        ]
                    ),

                "invalid_user_count":
                    int(
                        row[
                            "invalid_user_count"
                        ]
                    ),

                "unique_users":
                    int(
                        row[
                            "unique_users"
                        ]
                    ),

                "failure_ratio":
                    float(
                        row[
                            "failure_ratio"
                        ]
                    ),

                "root_attempt_ratio":
                    float(
                        row[
                            "root_attempt_ratio"
                        ]
                    ),

                "breakin_warning_count":
                    int(
                        row[
                            "breakin_warning_count"
                        ]
                    ),

                "disconnect_count":
                    int(
                        row[
                            "disconnect_count"
                        ]
                    ),

                "no_identification_count":
                    int(
                        row[
                            "no_identification_count"
                        ]
                    )
            }


            # ------------------------------------------------
            # Optional contextual features
            # ------------------------------------------------

            if (
                "successful_login_count"
                in row.index
            ):

                evidence[
                    "successful_login_count"
                ] = int(
                    row[
                        "successful_login_count"
                    ]
                )


            if (
                "success_after_failures"
                in row.index
            ):

                evidence[
                    "success_after_failures"
                ] = int(
                    row[
                        "success_after_failures"
                    ]
                )


            # ------------------------------------------------
            # Source IP / time metadata
            # ------------------------------------------------

            source_ip = None

            if "source_ip" in row.index:

                source_ip = str(
                    row["source_ip"]
                )


            window_start = None

            if (
                "window_start"
                in row.index
            ):

                value = row[
                    "window_start"
                ]

                if pd.notna(
                    value
                ):

                    window_start = (
                        pd.Timestamp(
                            value
                        )
                        .isoformat()
                    )


            window_end = None

            if (
                "window_end"
                in row.index
            ):

                value = row[
                    "window_end"
                ]

                if pd.notna(
                    value
                ):

                    window_end = (
                        pd.Timestamp(
                            value
                        )
                        .isoformat()
                    )


            # ------------------------------------------------
            # Final structured event
            # ------------------------------------------------

            output = {

                "event_type":
                    "ssh_behavior_assessment",

                "source_ip":
                    source_ip,

                "window_start":
                    window_start,

                "window_end":
                    window_end,

                "anomaly_detected":
                    bool(
                        anomaly_detected
                    ),

                "detector_votes":
                    int(
                        votes
                    ),

                "detector_combination":
                    combination,

                "confidence":
                    confidence,

                # --------------------------------------------
                # DC-Guardian v1 integration contract
                # --------------------------------------------

                "evidence_state":
                    evidence_state,

                "high_confidence_anomaly":
                    bool(
                        votes >= 2
                    ),

                "anomaly_candidate":
                    bool(
                        votes == 1
                        and not explicit_security_signal
                    ),

                # --------------------------------------------
                # Explicit OpenSSH security context
                # --------------------------------------------

                "explicit_security_signal":
                    bool(
                        explicit_security_signal
                    ),

                "security_signals":
                    security_signal_result[
                        "signals"
                    ],

                "security_signal_evidence":
                    security_signal_result[
                        "evidence"
                    ],


                # --------------------------------------------
                # Rule detector
                # --------------------------------------------

                "rule": {

                    "prediction":
                        rule_result[
                            "prediction"
                        ],

                    "anomalous":
                        bool(
                            rule_result[
                                "anomalous"
                            ]
                        ),

                    "suspicious":
                        bool(
                            rule_result[
                                "suspicious"
                            ]
                        ),

                    "score":
                        int(
                            rule_result[
                                "score"
                            ]
                        ),

                    "triggered_rules":
                        rule_result[
                            "triggered_rules"
                        ],

                    "evidence":
                        rule_result[
                            "evidence"
                        ]
                },


                # --------------------------------------------
                # Isolation Forest
                # --------------------------------------------

                "isolation_forest": {

                    "prediction":
                        str(
                            if_prediction
                        ),

                    "anomalous":
                        bool(
                            if_anomalous
                        ),

                    "anomaly_score":
                        float(
                            if_scores[
                                position
                            ]
                        )
                },


                # --------------------------------------------
                # Autoencoder
                # --------------------------------------------

                "autoencoder": {

                    "prediction":
                        str(
                            ae_prediction
                        ),

                    "anomalous":
                        bool(
                            ae_anomalous
                        ),

                    "reconstruction_error":
                        float(
                            ae_errors[
                                position
                            ]
                        ),

                    "threshold":
                        float(
                            self.ae_threshold
                        )
                },


                # --------------------------------------------
                # Behavioral evidence
                # --------------------------------------------

                "evidence":
                    evidence
            }


            outputs.append(
                output
            )


        return outputs


    # ========================================================
    # Detect a single feature window
    # ========================================================

    def detect_one(
        self,
        feature_window
    ):

        if isinstance(
            feature_window,
            dict
        ):

            df = pd.DataFrame(
                [
                    feature_window
                ]
            )


        elif isinstance(
            feature_window,
            pd.Series
        ):

            df = pd.DataFrame(
                [
                    feature_window
                    .to_dict()
                ]
            )


        elif isinstance(
            feature_window,
            pd.DataFrame
        ):

            if len(
                feature_window
            ) != 1:

                raise ValueError(
                    "detect_one() requires "
                    "exactly one row."
                )

            df = feature_window.copy()


        else:

            raise TypeError(
                "detect_one() expects "
                "dict, pandas Series, "
                "or one-row DataFrame."
            )


        results = self.detect(
            df
        )


        return results[0]


    # ========================================================
    # Integration entry point
    # ========================================================

    def assess_window(
        self,
        feature_window
    ):

        """
        Public integration entry point for DC-Guardian.

        Accepts one already-engineered SSH behavioral window
        (dict, Series, or one-row DataFrame) and returns the
        standardized JSON-serializable security assessment.
        """

        return self.detect_one(
            feature_window
        )


# ============================================================
# Example / smoke test
# ============================================================
#
# Running this file directly performs inference on several
# existing feature windows.
#
# It does NOT train or fit anything.
# ============================================================

if __name__ == "__main__":

    FEATURE_FILE = Path(
        "data/processed/"
        "ssh_features_full_5min.csv"
    )


    if not FEATURE_FILE.exists():

        raise FileNotFoundError(
            f"Feature file not found: "
            f"{FEATURE_FILE}"
        )


    print(
        "\n============================================"
    )

    print(
        "DC-GUARDIAN SSH ANOMALY DETECTOR"
    )

    print(
        "============================================"
    )


    # --------------------------------------------------------
    # Load detector ONCE
    # --------------------------------------------------------

    detector = SSHAnomalyDetector()


    print(
        "\nPASS: Persisted models loaded."
    )


    # --------------------------------------------------------
    # Load feature windows for smoke test
    # --------------------------------------------------------

    features = pd.read_csv(
        FEATURE_FILE,
        parse_dates=[
            "window_start",
            "window_end"
        ]
    )


    # Use five highest-failure windows plus five
    # lowest-failure windows to exercise different behavior.

    high_activity = (
        features
        .sort_values(
            "failed_login_count",
            ascending=False
        )
        .head(5)
    )


    low_activity = (
        features
        .sort_values(
            "failed_login_count",
            ascending=True
        )
        .head(5)
    )


    test_windows = pd.concat(
        [
            high_activity,
            low_activity
        ],
        ignore_index=True
    )


    # --------------------------------------------------------
    # Run inference
    # --------------------------------------------------------

    results = detector.detect(
        test_windows
    )


    print(
        f"\nWindows assessed: "
        f"{len(results)}"
    )


    # --------------------------------------------------------
    # Print JSON results
    # --------------------------------------------------------

    for result in results:

        print(
            "\n--------------------------------------------"
        )

        print(
            json.dumps(
                result,
                indent=2
            )
        )


    print(
        "\n============================================"
    )

    print(
        "SSH DETECTOR INFERENCE PASSED"
    )

    print(
        "============================================"
    )