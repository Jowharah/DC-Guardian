"""
DC-Guardian Evidence
Face Embedding

Frozen embedding stack:
    RetinaFace -> detection/alignment
    ArcFace -> 512-dimensional face embedding

This module does not perform identity matching or threshold
selection.
"""

from pathlib import Path

import numpy as np

from deepface import DeepFace

from evidence.face_recognition.src.config import (
    DETECTOR_BACKEND,
    EXPECTED_EMBEDDING_DIMENSION,
    MODEL_NAME,
)


class FaceEmbeddingError(
    RuntimeError
):
    """Base face-embedding error."""


class NoFaceDetectedError(
    FaceEmbeddingError
):
    """No valid face could be extracted."""


class MultipleFacesDetectedError(
    FaceEmbeddingError
):
    """More than one face was detected."""


def extract_face_embedding(
    image_path,
):
    """
    Extract exactly one ArcFace embedding from one image.

    Returns a dictionary containing the embedding and
    detection metadata.

    The function deliberately rejects zero-face and
    multi-face images because enrollment identity must be
    unambiguous.
    """

    image_path = Path(
        image_path
    )


    if not image_path.is_file():

        raise FileNotFoundError(
            f"Image not found: {image_path}"
        )


    try:

        representations = (
            DeepFace.represent(
                img_path=
                    str(
                        image_path
                    ),

                model_name=
                    MODEL_NAME,

                detector_backend=
                    DETECTOR_BACKEND,

                enforce_detection=
                    True,

                align=
                    True,
            )
        )

    except ValueError as error:

        raise NoFaceDetectedError(
            f"No valid face detected in "
            f"{image_path.name}"
        ) from error


    if not isinstance(
        representations,
        list,
    ):

        raise FaceEmbeddingError(
            "DeepFace.represent() returned "
            "an unexpected result type."
        )


    if len(
        representations
    ) == 0:

        raise NoFaceDetectedError(
            f"No face detected in "
            f"{image_path.name}"
        )


    if len(
        representations
    ) != 1:

        raise MultipleFacesDetectedError(
            f"Expected exactly one face in "
            f"{image_path.name}; "
            f"detected {len(representations)}."
        )


    representation = (
        representations[0]
    )


    embedding = np.asarray(
        representation[
            "embedding"
        ],
        dtype=np.float32,
    )


    if embedding.ndim != 1:

        raise FaceEmbeddingError(
            "Face embedding must be "
            "one-dimensional."
        )


    if (
        embedding.shape[0]
        != EXPECTED_EMBEDDING_DIMENSION
    ):

        raise FaceEmbeddingError(
            "Unexpected ArcFace embedding "
            "dimension: "
            f"{embedding.shape[0]}"
        )


    if not np.isfinite(
        embedding
    ).all():

        raise FaceEmbeddingError(
            "Face embedding contains "
            "NaN or infinite values."
        )


    facial_area = (
        representation.get(
            "facial_area"
        )
    )


    face_confidence = (
        representation.get(
            "face_confidence"
        )
    )


    return {
        "image_path":
            str(
                image_path
            ),

        "model_name":
            MODEL_NAME,

        "detector_backend":
            DETECTOR_BACKEND,

        "embedding":
            embedding,

        "embedding_dimension":
            int(
                embedding.shape[0]
            ),

        "facial_area":
            facial_area,

        "face_confidence":
            face_confidence,
    }
