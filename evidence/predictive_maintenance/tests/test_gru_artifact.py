"""
DC-Guardian Predictive Maintenance
GRU Frozen Artifact Contract Test
"""

import json

import torch

from evidence.predictive_maintenance.src.gru.config import (
    GRU_METADATA_FILE,
    GRU_MODEL_FILE,
    GRU_MODEL_NAME,
)

from evidence.predictive_maintenance.src.gru.model import (
    MaintenanceGRU,
)


print(
    "\n============================================"
)
print(
    "DC-GUARDIAN GRU ARTIFACT TEST"
)
print(
    "============================================"
)


# ============================================================
# Files
# ============================================================

assert GRU_MODEL_FILE.exists()

assert GRU_METADATA_FILE.exists()


print(
    "PASS: GRU artifacts exist."
)


# ============================================================
# Checkpoint
# ============================================================

checkpoint = torch.load(
    GRU_MODEL_FILE,
    map_location="cpu",
)


assert (
    checkpoint["model_name"]
    == GRU_MODEL_NAME
)


assert (
    checkpoint["best_epoch"]
    == 9
)


assert (
    abs(
        checkpoint[
            "sampled_validation_pr_auc"
        ]
        - 0.267353
    )
    < 0.001
)


print(
    "PASS: Best epoch checkpoint preserved."
)


# ============================================================
# Model state
# ============================================================

model = MaintenanceGRU()

model.load_state_dict(
    checkpoint[
        "state_dict"
    ]
)

model.eval()


print(
    "PASS: GRU state dictionary loads."
)


# ============================================================
# Metadata
# ============================================================

with open(
    GRU_METADATA_FILE,
    "r",
    encoding="utf-8",
) as file:

    metadata = json.load(
        file
    )


assert (
    metadata[
        "model_name"
    ]
    == GRU_MODEL_NAME
)


assert (
    metadata[
        "best_epoch"
    ]
    == 9
)


assert (
    metadata[
        "sampled_q4_is_final_metric"
    ]
    is False
)


assert (
    metadata[
        "final_test_period_accessed"
    ]
    is False
)


assert (
    metadata[
        "training_sequences"
    ]
    == 390405
)


assert (
    metadata[
        "development_validation_sequences"
    ]
    == 321988
)


print(
    "PASS: GRU metadata contract."
)

print(
    "PASS: Sampled-Q4 metric marked development-only."
)

print(
    "PASS: 2026 Q1 remains untouched."
)


print(
    "\n============================================"
)
print(
    "GRU MODEL ARTIFACT CONTRACT PASSED"
)
print(
    "============================================"
)
