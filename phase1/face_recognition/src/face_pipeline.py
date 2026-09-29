"""
DC-Guardian Phase 1
Face Recognition Runtime Pipeline

Public inference interface for Face Recognition v1.

Frozen runtime:
    image
      -> RetinaFace detection/alignment
      -> ArcFace embedding
      -> frozen enrollment database
      -> cosine nearest-neighbor matching
      -> frozen threshold
      -> RECOGNIZED / UNKNOWN

No enrollment, fitting, or threshold selection occurs here.
"""

import json
import time
from pathlib import Path

from phase1.face_recognition.src.config import (
    MODELS_DIR,
)

from phase1.face_recognition.src.face_embedding import (
    MultipleFacesDetectedError,
    NoFaceDetectedError,
    extract_face_embedding,
)

from phase1.face_recognition.src.face_recognizer import (
    FaceRecognizer,
)


CONFIG_FILE = (
    MODELS_DIR
    / "face_recognition_config.json"
)


class FaceRecognitionPipeline:

    def __init__(self):

        if not CONFIG_FILE.is_file():

            raise FileNotFoundError(
                "Frozen face-recognition configuration "
                f"not found: {CONFIG_FILE}"
            )


        with CONFIG_FILE.open(
            "r",
            encoding="utf-8",
        ) as file:

            self.config = json.load(
                file
            )


        # ====================================================
        # Frozen configuration contract
        # ====================================================

        if (
            self.config[
                "configuration_frozen"
            ]
            is not True
        ):

            raise RuntimeError(
                "Face-recognition configuration "
                "is not frozen."
            )


        if (
            self.config[
                "threshold_source"
            ]
            != "validation_only"
        ):

            raise RuntimeError(
                "Recognition threshold was not "
                "derived from validation only."
            )


        self.threshold = float(
            self.config[
                "recognition_threshold"
            ]
        )


        self.recognizer = (
            FaceRecognizer()
        )


    # ========================================================
    # Base response
    # ========================================================

    def _base_result(
        self,
        image_path,
    ):

        return {
            "domain":
                "PHYSICAL_SECURITY",

            "event_type":
                "FACE_IDENTIFICATION_ASSESSMENT",

            "image":
                Path(
                    image_path
                ).name,

            "model_name":
                self.config[
                    "model_name"
                ],

            "detector_backend":
                self.config[
                    "detector_backend"
                ],

            "distance_metric":
                self.config[
                    "distance_metric"
                ],

            "threshold":
                self.threshold,

            "threshold_source":
                self.config[
                    "threshold_source"
                ],

            "configuration_frozen":
                True,
        }


    # ========================================================
    # Recognition
    # ========================================================

    def recognize(
        self,
        image_path,
    ):
        """
        Recognize exactly one face from an image.

        Possible recognition_status values:

            RECOGNIZED
            UNKNOWN
            NO_FACE
            MULTIPLE_FACES
        """

        image_path = Path(
            image_path
        )


        result = self._base_result(
            image_path
        )


        start = time.perf_counter()


        # ====================================================
        # Face extraction
        # ====================================================

        try:

            embedding_result = (
                extract_face_embedding(
                    image_path
                )
            )


        except NoFaceDetectedError:

            latency_ms = (
                (
                    time.perf_counter()
                    - start
                )
                * 1000.0
            )


            result.update(
                {
                    "person_id":
                        "UNKNOWN",

                    "recognition_status":
                        "NO_FACE",

                    "face_detected":
                        False,

                    "face_count":
                        0,

                    "distance":
                        None,

                    "similarity":
                        None,

                    "nearest_employee_id":
                        None,

                    "face_confidence":
                        None,

                    "facial_area":
                        None,

                    "latency_ms":
                        latency_ms,
                }
            )


            return result


        except MultipleFacesDetectedError as error:

            latency_ms = (
                (
                    time.perf_counter()
                    - start
                )
                * 1000.0
            )


            # Current Phase 1 contract intentionally does not
            # choose one identity from a multi-face image.

            result.update(
                {
                    "person_id":
                        "UNKNOWN",

                    "recognition_status":
                        "MULTIPLE_FACES",

                    "face_detected":
                        True,

                    "face_count":
                        None,

                    "distance":
                        None,

                    "similarity":
                        None,

                    "nearest_employee_id":
                        None,

                    "face_confidence":
                        None,

                    "facial_area":
                        None,

                    "latency_ms":
                        latency_ms,

                    "message":
                        str(
                            error
                        ),
                }
            )


            return result


        # ====================================================
        # Match against frozen enrollment database
        # ====================================================

        match = (
            self.recognizer.match_embedding(
                embedding_result[
                    "embedding"
                ]
            )
        )


        if (
            match[
                "distance"
            ]
            <= self.threshold
        ):

            person_id = (
                match[
                    "employee_id"
                ]
            )

            recognition_status = (
                "RECOGNIZED"
            )


        else:

            person_id = (
                "UNKNOWN"
            )

            recognition_status = (
                "UNKNOWN"
            )


        latency_ms = (
            (
                time.perf_counter()
                - start
            )
            * 1000.0
        )


        result.update(
            {
                "person_id":
                    person_id,

                "recognition_status":
                    recognition_status,

                "face_detected":
                    True,

                "face_count":
                    1,

                "distance":
                    float(
                        match[
                            "distance"
                        ]
                    ),

                "similarity":
                    float(
                        match[
                            "similarity"
                        ]
                    ),

                "nearest_employee_id":
                    match[
                        "employee_id"
                    ],

                "face_confidence":
                    (
                        float(
                            embedding_result[
                                "face_confidence"
                            ]
                        )
                        if (
                            embedding_result[
                                "face_confidence"
                            ]
                            is not None
                        )
                        else None
                    ),

                "facial_area":
                    embedding_result[
                        "facial_area"
                    ],

                "latency_ms":
                    latency_ms,
            }
        )


        return result