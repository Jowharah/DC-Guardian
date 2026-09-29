"""
DC-GUARDIAN frozen model artifact integrity helpers.

Serialized model files (for example joblib/pickle-compatible artifacts) must be
treated as trusted code-bearing artifacts. This module verifies SHA-256 hashes
before deserialization when an expected digest is supplied.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


CHUNK_SIZE = 1024 * 1024


def sha256_file(path: Path) -> str:
    """Return the lowercase SHA-256 digest for a file."""

    path = Path(path)

    if not path.is_file():
        raise FileNotFoundError(
            f"Artifact not found: {path}"
        )

    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(CHUNK_SIZE),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def verify_sha256(
    path: Path,
    expected_sha256: str,
) -> None:
    """Fail closed when an artifact does not match its frozen digest."""

    if not isinstance(expected_sha256, str):
        raise TypeError(
            "expected_sha256 must be a string."
        )

    expected = expected_sha256.strip().lower()

    if (
        len(expected) != 64
        or any(
            character not in "0123456789abcdef"
            for character in expected
        )
    ):
        raise ValueError(
            "expected_sha256 must be a 64-character "
            "hexadecimal SHA-256 digest."
        )

    actual = sha256_file(path)

    if actual != expected:
        raise RuntimeError(
            "Frozen model artifact integrity check failed: "
            f"{path}. Expected SHA-256 {expected}, "
            f"received {actual}. Refusing to deserialize "
            "the artifact."
        )
