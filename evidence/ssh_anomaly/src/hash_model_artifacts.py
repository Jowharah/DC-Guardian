"""
Print SHA-256 digests for the frozen SSH model artifacts.

Run from the repository root:
    python evidence/ssh_anomaly/src/hash_model_artifacts.py

This script only reads files and prints hashes. It does not deserialize models.
"""

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.model_integrity import sha256_file


SSH_ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = SSH_ROOT / "models"

ARTIFACTS = (
    "isolation_forest.joblib",
    "isolation_forest_scaler.joblib",
    "autoencoder_log.keras",
    "autoencoder_log_scaler.joblib",
    "autoencoder_log_config.json",
)


if __name__ == "__main__":

    for name in ARTIFACTS:

        path = MODEL_DIR / name

        print(
            f"{name}  {sha256_file(path)}"
        )

