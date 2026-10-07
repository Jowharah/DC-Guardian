"""
DC-Guardian Evidence
PPE Compliance Runtime Pipeline

Frozen YOLOv8n detector
    -> normalized detections
    -> person/PPE association
    -> frozen PPE policy
    -> structured assessment
"""

from pathlib import Path
import json
import time

import torch
from ultralytics import YOLO

from evidence.ppe_detection.src.ppe_association import (
    associate_ppe_to_people,
)

from evidence.ppe_detection.src.ppe_policy import (
    POLICY_NAME,
    POLICY_VERSION,
    REQUIRED_PPE,
    evaluate_ppe_policy,
)


# ============================================================
# Paths
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

PPE_ROOT = (
    PROJECT_ROOT
    / "evidence"
    / "ppe_detection"
)

MODEL_FILE = (
    PPE_ROOT
    / "models"
    / "ppe_yolov8_best.pt"
)

CONFIG_FILE = (
    PPE_ROOT
    / "models"
    / "ppe_config.json"
)


# ============================================================
# Runtime pipeline
# ============================================================

class PPECompliancePipeline:

    def __init__(self):

        # ----------------------------------------------------
        # Required frozen artifacts
        # ----------------------------------------------------

        if not MODEL_FILE.exists():
            raise FileNotFoundError(
                f"Frozen PPE model not found: {MODEL_FILE}"
            )

        if not CONFIG_FILE.exists():
            raise FileNotFoundError(
                f"Frozen PPE config not found: {CONFIG_FILE}"
            )


        # ----------------------------------------------------
        # Frozen configuration
        # ----------------------------------------------------

        self.config = json.loads(
            CONFIG_FILE.read_text(
                encoding="utf-8"
            )
        )


        if (
            self.config[
                "configuration_frozen"
            ]
            is not True
        ):
            raise AssertionError(
                "PPE detector configuration is not frozen."
            )


        if (
            self.config[
                "compliance_policy_frozen"
            ]
            is not True
        ):
            raise AssertionError(
                "PPE compliance policy is not frozen."
            )


        # ----------------------------------------------------
        # Policy identity contract
        # ----------------------------------------------------

        if (
            self.config[
                "policy_version"
            ]
            != POLICY_VERSION
        ):
            raise AssertionError(
                "PPE policy version mismatch."
            )


        if (
            self.config[
                "policy_name"
            ]
            != POLICY_NAME
        ):
            raise AssertionError(
                "PPE policy name mismatch."
            )


        if (
            self.config[
                "required_ppe"
            ]
            != list(
                REQUIRED_PPE
            )
        ):
            raise AssertionError(
                "Frozen required-PPE policy mismatch."
            )


        # ----------------------------------------------------
        # Frozen runtime operating point
        # ----------------------------------------------------

        self.confidence_threshold = float(
            self.config[
                "confidence_threshold"
            ]
        )

        self.iou_threshold = float(
            self.config[
                "iou_threshold"
            ]
        )

        self.association_minimum_containment = float(
            self.config[
                "association_minimum_containment"
            ]
        )


        if not (
            0.0
            <= self.confidence_threshold
            <= 1.0
        ):
            raise AssertionError(
                "Invalid frozen confidence threshold."
            )


        if not (
            0.0
            <= self.iou_threshold
            <= 1.0
        ):
            raise AssertionError(
                "Invalid frozen IoU threshold."
            )


        if not (
            0.0
            <= self.association_minimum_containment
            <= 1.0
        ):
            raise AssertionError(
                "Invalid frozen association threshold."
            )


        # ----------------------------------------------------
        # Runtime environment
        # ----------------------------------------------------

        if not torch.cuda.is_available():
            raise RuntimeError(
                "CUDA unavailable for PPE runtime."
            )


        # ----------------------------------------------------
        # Frozen detector
        # ----------------------------------------------------

        self.model = YOLO(
            str(
                MODEL_FILE
            )
        )


        self.model_names = {
            int(class_id):
                str(class_name)

            for class_id, class_name
            in self.model.names.items()
        }


        if len(
            self.model_names
        ) != 17:
            raise AssertionError(
                "Frozen PPE model must contain 17 classes."
            )


    # ========================================================
    # Detection normalization
    # ========================================================

    def _normalize_results(
        self,
        result,
    ):
        """
        Convert Ultralytics detections into project-standard
        dictionaries.
        """

        detections = []


        if result.boxes is None:
            return detections


        for box in result.boxes:

            class_id = int(
                box.cls[
                    0
                ].item()
            )

            confidence = float(
                box.conf[
                    0
                ].item()
            )

            coordinates = (
                box.xyxy[
                    0
                ]
                .detach()
                .cpu()
                .tolist()
            )


            detections.append(
                {
                    "class_id":
                        class_id,

                    "class_name":
                        self.model_names[
                            class_id
                        ],

                    "confidence":
                        confidence,

                    "bbox_xyxy": [
                        float(
                            value
                        )
                        for value
                        in coordinates
                    ],
                }
            )


        return detections


    # ========================================================
    # Complete PPE assessment
    # ========================================================

    def assess(
        self,
        image,
    ):
        """
        Run the frozen DC-Guardian PPE-v1 runtime pipeline.

        Runtime thresholds and association parameters are loaded
        exclusively from the frozen PPE configuration.

        They cannot be overridden by the caller.
        """

        start = time.perf_counter()


        # ----------------------------------------------------
        # Frozen YOLO inference
        # ----------------------------------------------------

        results = self.model.predict(
            source=image,

            conf=
                self.confidence_threshold,

            iou=
                self.iou_threshold,

            imgsz=
                self.config[
                    "image_size"
                ],

            device=0,

            verbose=False,
        )


        if len(
            results
        ) != 1:
            raise RuntimeError(
                "PPE runtime expects one input image/frame."
            )


        # ----------------------------------------------------
        # Normalize detector evidence
        # ----------------------------------------------------

        detections = self._normalize_results(
            results[
                0
            ]
        )


        # ----------------------------------------------------
        # Person/PPE association
        # ----------------------------------------------------

        association = associate_ppe_to_people(
            detections,

            minimum_containment=
                self.association_minimum_containment,
        )


        # ----------------------------------------------------
        # Frozen PPE policy
        # ----------------------------------------------------

        policy_result = evaluate_ppe_policy(
            association
        )


        # ----------------------------------------------------
        # Runtime
        # ----------------------------------------------------

        latency_ms = (
            time.perf_counter()
            - start
        ) * 1000.0


        # ----------------------------------------------------
        # Structured Evidence layer assessment
        # ----------------------------------------------------

        return {
            "domain":
                "PHYSICAL_SECURITY",

            "event_type":
                "PPE_COMPLIANCE_ASSESSMENT",

            # Detector
            "model_family":
                self.config[
                    "model_family"
                ],

            "architecture":
                self.config[
                    "architecture"
                ],

            "model_weights":
                self.config[
                    "weights"
                ],

            "detector_configuration":
                self.config[
                    "configuration_version"
                ],

            "detector_configuration_frozen":
                True,

            # Policy
            "policy_version":
                POLICY_VERSION,

            "policy_name":
                POLICY_NAME,

            "policy_frozen":
                bool(
                    self.config[
                        "compliance_policy_frozen"
                    ]
                ),

            "policy_source":
                self.config[
                    "policy_source"
                ],

            "required_ppe":
                list(
                    REQUIRED_PPE
                ),

            # Frozen operating point
            "confidence_threshold":
                self.confidence_threshold,

            "iou_threshold":
                self.iou_threshold,

            "association_method":
                self.config[
                    "association_method"
                ],

            "association_minimum_containment":
                self.association_minimum_containment,

            "person_assignment":
                self.config[
                    "person_assignment"
                ],

            # Assessment
            "person_detected":
                policy_result[
                    "person_detected"
                ],

            "person_count":
                policy_result[
                    "person_count"
                ],

            "overall_status":
                policy_result[
                    "overall_status"
                ],

            "people":
                policy_result[
                    "people"
                ],

            # Evidence
            "detections":
                detections,

            "unassigned_detections":
                association[
                    "unassigned_detections"
                ],

            # Runtime
            "latency_ms":
                latency_ms,
        }


# ============================================================
# Project-level inference wrapper
# ============================================================

def infer_ppe(
    image,
):
    """
    Simple callable PPE inference wrapper.

    Returns one frozen DC-Guardian PPE-v1 assessment.
    """

    pipeline = PPECompliancePipeline()

    return pipeline.assess(
        image
    )
