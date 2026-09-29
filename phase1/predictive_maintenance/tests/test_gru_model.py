"""
DC-Guardian Predictive Maintenance
GRU Model Contract Test
"""

import torch

from phase1.predictive_maintenance.src.gru.config import (
    GRU_BATCH_SIZE,
    GRU_INPUT_SIZE,
    GRU_SEQUENCE_LENGTH,
)

from phase1.predictive_maintenance.src.gru.model import (
    MaintenanceGRU,
)


print(
    "\n============================================"
)
print(
    "DC-GUARDIAN GRU MODEL TEST"
)
print(
    "============================================"
)


device = torch.device(
    "cuda"
    if torch.cuda.is_available()
    else "cpu"
)


print(
    "Device:",
    device
)


model = MaintenanceGRU().to(
    device
)


# ============================================================
# Small synthetic batch
# ============================================================

TEST_BATCH_SIZE = 16


x = torch.randn(
    TEST_BATCH_SIZE,
    GRU_SEQUENCE_LENGTH,
    GRU_INPUT_SIZE,
    dtype=torch.float32,
    device=device,
)


with torch.no_grad():

    logits = model(
        x
    )


assert logits.shape == (
    TEST_BATCH_SIZE,
)


assert torch.isfinite(
    logits
).all()


print(
    "PASS: GRU forward pass."
)

print(
    "PASS: Input shape accepted:",
    tuple(
        x.shape
    )
)

print(
    "PASS: Output shape:",
    tuple(
        logits.shape
    )
)


# ============================================================
# Probability conversion
# ============================================================

probabilities = torch.sigmoid(
    logits
)


assert torch.all(
    probabilities >= 0
)

assert torch.all(
    probabilities <= 1
)


print(
    "PASS: Logits convert to valid probabilities."
)


# ============================================================
# GPU contract
# ============================================================

if torch.cuda.is_available():

    assert next(
        model.parameters()
    ).is_cuda

    print(
        "PASS: Model runs on CUDA."
    )

    print(
        "GPU:",
        torch.cuda.get_device_name(0)
    )

else:

    print(
        "WARNING: CUDA unavailable; "
        "model is running on CPU."
    )


# ============================================================
# Parameter count
# ============================================================

parameter_count = sum(
    parameter.numel()
    for parameter in model.parameters()
)


print(
    "Trainable parameters:",
    f"{parameter_count:,}"
)


assert parameter_count > 0

assert parameter_count < 1_000_000


print(
    "PASS: GRU remains compact."
)


print(
    "\n============================================"
)
print(
    "GRU MODEL CONTRACT PASSED"
)
print(
    "============================================"
)