"""
DC-Guardian Phase 1
Face Recognition Matcher

Loads the frozen enrollment embeddings and performs
nearest-enrollment matching using cosine distance.

No threshold is selected in this module.
"""

import numpy as np

from phase1.face_recognition.src.config import (
    MODELS_DIR,
)


ENROLLMENT_FILE = (
    MODELS_DIR
    / "employee_embeddings.npz"
)


class FaceRecognizer:

    def __init__(self):

        if not ENROLLMENT_FILE.is_file():

            raise FileNotFoundError(
                "Enrollment artifact not found: "
                f"{ENROLLMENT_FILE}"
            )


        with np.load(
            ENROLLMENT_FILE,
            allow_pickle=False,
        ) as artifact:

            self.embeddings = (
                artifact[
                    "embeddings"
                ].astype(
                    np.float32
                )
            )

            self.employee_ids = (
                artifact[
                    "employee_ids"
                ].astype(
                    str
                )
            )


        if (
            self.embeddings.ndim != 2
            or
            self.embeddings.shape[1]
            != 512
        ):

            raise RuntimeError(
                "Invalid enrollment embedding matrix."
            )


        if not np.isfinite(
            self.embeddings
        ).all():

            raise RuntimeError(
                "Enrollment embeddings contain "
                "non-finite values."
            )


        # Pre-compute enrollment norms.

        self.enrollment_norms = (
            np.linalg.norm(
                self.embeddings,
                axis=1,
            )
        )


        if np.any(
            self.enrollment_norms
            <= 0
        ):

            raise RuntimeError(
                "Enrollment contains zero-length "
                "embedding."
            )


    def match_embedding(
        self,
        query_embedding,
    ):
        """
        Find the nearest enrolled face using cosine distance.

        Returns the nearest enrollment image and employee ID.

        No UNKNOWN decision occurs here because the recognition
        threshold has not yet been frozen.
        """

        query = np.asarray(
            query_embedding,
            dtype=np.float32,
        )


        if query.shape != (512,):

            raise ValueError(
                "Query embedding must have "
                "shape (512,)."
            )


        if not np.isfinite(
            query
        ).all():

            raise ValueError(
                "Query embedding contains "
                "non-finite values."
            )


        query_norm = np.linalg.norm(
            query
        )


        if query_norm <= 0:

            raise ValueError(
                "Query embedding has zero norm."
            )


        similarities = (
            self.embeddings
            @ query
        ) / (
            self.enrollment_norms
            * query_norm
        )


        # Numerical protection.

        similarities = np.clip(
            similarities,
            -1.0,
            1.0,
        )


        distances = (
            1.0
            - similarities
        )


        best_index = int(
            np.argmin(
                distances
            )
        )


        return {
            "employee_id":
                str(
                    self.employee_ids[
                        best_index
                    ]
                ),

            "distance":
                float(
                    distances[
                        best_index
                    ]
                ),

            "similarity":
                float(
                    similarities[
                        best_index
                    ]
                ),

            "enrollment_index":
                best_index,
        }