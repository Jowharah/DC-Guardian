import torch

from phase1.predictive_maintenance.src.gru.config import (
    GRU_CLIP_VALUE,
    GRU_INPUT_SIZE,
    GRU_SEQUENCE_LENGTH,
)

from phase1.predictive_maintenance.src.gru.dataset import (
    build_training_dataset,
    build_validation_dataset,
)


print(
    "\n============================================"
)
print(
    "DC-GUARDIAN GRU DATASET TEST"
)
print(
    "============================================"
)


train_dataset = (
    build_training_dataset()
)

validation_dataset = (
    build_validation_dataset()
)


assert len(train_dataset) == 390405

assert len(validation_dataset) == 321988


print(
    "PASS: Training dataset count."
)

print(
    "PASS: Validation dataset count."
)


# ============================================================
# Validate both datasets
# ============================================================

for name, dataset in [
    (
        "TRAIN",
        train_dataset,
    ),
    (
        "VALIDATION",
        validation_dataset,
    ),
]:

    x, y = dataset[0]

    assert x.shape == (
        GRU_SEQUENCE_LENGTH,
        GRU_INPUT_SIZE,
    )

    assert x.dtype == (
        torch.float32
    )

    assert y.dtype == (
        torch.float32
    )

    assert torch.isfinite(
        x
    ).all()

    assert (
        x.abs().max()
        <= GRU_CLIP_VALUE
    )

    assert y.item() in {
        0.0,
        1.0,
    }

    print(
        f"PASS: {name} preprocessing contract."
    )


# ============================================================
# CUDA batch transfer
# ============================================================

device = torch.device(
    "cuda"
)


x, y = train_dataset[0]


x_gpu = (
    x
    .unsqueeze(0)
    .to(device)
)


y_gpu = (
    y
    .unsqueeze(0)
    .to(device)
)


assert x_gpu.is_cuda
assert y_gpu.is_cuda


print(
    "PASS: Tensors transfer to CUDA."
)

print(
    "GPU:",
    torch.cuda.get_device_name(0)
)


print(
    "\n============================================"
)
print(
    "GRU DATASET CONTRACT PASSED"
)
print(
    "============================================"
)