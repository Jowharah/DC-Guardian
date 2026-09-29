"""
DC-Guardian Phase 1
Predictive Maintenance GRU Training

Experimental GRU challenger to the frozen Temporal RF v2.

TRAIN:
    2025 Q2 + Q3 sampled sequence population

DEVELOPMENT VALIDATION:
    Fixed sampled 2025 Q4 sequence population

IMPORTANT:
    Sampled-Q4 PR-AUC is used for early stopping only.
    It is NOT the final comparable Q4 metric.

    2026 Q1 remains locked.
"""

import copy
import json
import random
from datetime import datetime, timezone

import numpy as np
import torch

from sklearn.metrics import (
    average_precision_score,
    roc_auc_score,
)

from torch import nn
from torch.optim import AdamW
from torch.utils.data import DataLoader

from phase1.predictive_maintenance.src.gru.config import (
    GRU_BATCH_SIZE,
    GRU_EARLY_STOPPING_PATIENCE,
    GRU_LEARNING_RATE,
    GRU_MAX_EPOCHS,
    GRU_METADATA_FILE,
    GRU_MODEL_DIR,
    GRU_MODEL_FILE,
    GRU_MODEL_NAME,
    GRU_RANDOM_STATE,
    GRU_VALIDATION_PERIOD,
    GRU_WEIGHT_DECAY,
)

from phase1.predictive_maintenance.src.gru.dataset import (
    build_training_dataset,
    build_validation_dataset,
)

from phase1.predictive_maintenance.src.gru.model import (
    MaintenanceGRU,
)


# ============================================================
# Reproducibility
# ============================================================

def set_random_seeds():

    random.seed(
        GRU_RANDOM_STATE
    )

    np.random.seed(
        GRU_RANDOM_STATE
    )

    torch.manual_seed(
        GRU_RANDOM_STATE
    )

    torch.cuda.manual_seed_all(
        GRU_RANDOM_STATE
    )


# ============================================================
# Training epoch
# ============================================================

def train_one_epoch(
    model,
    loader,
    optimizer,
    loss_function,
    device,
):

    model.train()

    running_loss = 0.0

    sample_count = 0


    for x, y in loader:

        x = x.to(
            device,
            non_blocking=True,
        )

        y = y.to(
            device,
            non_blocking=True,
        )


        optimizer.zero_grad(
            set_to_none=True
        )


        logits = model(
            x
        )


        loss = loss_function(
            logits,
            y,
        )


        loss.backward()


        # Prevent rare exploding gradients.
        torch.nn.utils.clip_grad_norm_(
            model.parameters(),
            max_norm=5.0,
        )


        optimizer.step()


        batch_size = x.size(0)


        running_loss += (
            loss.item()
            * batch_size
        )


        sample_count += (
            batch_size
        )


    return (
        running_loss
        / sample_count
    )


# ============================================================
# Development validation
# ============================================================

@torch.no_grad()
def evaluate_sampled_validation(
    model,
    loader,
    loss_function,
    device,
):

    model.eval()


    running_loss = 0.0

    sample_count = 0


    probability_parts = []

    label_parts = []


    for x, y in loader:

        x = x.to(
            device,
            non_blocking=True,
        )

        y = y.to(
            device,
            non_blocking=True,
        )


        logits = model(
            x
        )


        loss = loss_function(
            logits,
            y,
        )


        probability = torch.sigmoid(
            logits
        )


        batch_size = x.size(0)


        running_loss += (
            loss.item()
            * batch_size
        )


        sample_count += (
            batch_size
        )


        probability_parts.append(
            probability
            .cpu()
            .numpy()
        )


        label_parts.append(
            y
            .cpu()
            .numpy()
        )


    probabilities = np.concatenate(
        probability_parts
    )


    labels = np.concatenate(
        label_parts
    ).astype(
        int
    )


    pr_auc = average_precision_score(
        labels,
        probabilities,
    )


    roc_auc = roc_auc_score(
        labels,
        probabilities,
    )


    validation_loss = (
        running_loss
        / sample_count
    )


    return {
        "loss":
            validation_loss,

        "pr_auc":
            pr_auc,

        "roc_auc":
            roc_auc,
    }


# ============================================================
# Main training
# ============================================================

def main():

    set_random_seeds()


    if not torch.cuda.is_available():

        raise RuntimeError(
            "CUDA is required for this GRU experiment."
        )


    device = torch.device(
        "cuda"
    )


    print(
        "\n============================================"
    )
    print(
        "DC-GUARDIAN GRU TRAINING"
    )
    print(
        "============================================"
    )


    print(
        "Model:",
        GRU_MODEL_NAME
    )

    print(
        "Device:",
        torch.cuda.get_device_name(0)
    )

    print(
        "Development validation:",
        GRU_VALIDATION_PERIOD
    )

    print(
        "Batch size:",
        GRU_BATCH_SIZE
    )

    print(
        "Maximum epochs:",
        GRU_MAX_EPOCHS
    )

    print(
        "Early-stopping patience:",
        GRU_EARLY_STOPPING_PATIENCE
    )


    # ========================================================
    # Datasets
    # ========================================================

    train_dataset = (
        build_training_dataset()
    )


    validation_dataset = (
        build_validation_dataset()
    )


    print(
        "\nTraining sequences:",
        f"{len(train_dataset):,}"
    )

    print(
        "Validation sequences:",
        f"{len(validation_dataset):,}"
    )


    # ========================================================
    # DataLoaders
    # ========================================================

    train_loader = DataLoader(
        train_dataset,

        batch_size=
            GRU_BATCH_SIZE,

        shuffle=True,

        num_workers=0,

        pin_memory=True,

        drop_last=False,
    )


    validation_loader = DataLoader(
        validation_dataset,

        batch_size=
            GRU_BATCH_SIZE * 2,

        shuffle=False,

        num_workers=0,

        pin_memory=True,

        drop_last=False,
    )


    # ========================================================
    # Model
    # ========================================================

    model = MaintenanceGRU().to(
        device
    )


    parameter_count = sum(
        parameter.numel()
        for parameter
        in model.parameters()
        if parameter.requires_grad
    )


    print(
        "Trainable parameters:",
        f"{parameter_count:,}"
    )


    # ========================================================
    # Optimization
    # ========================================================

    loss_function = (
        nn.BCEWithLogitsLoss()
    )


    optimizer = AdamW(
        model.parameters(),

        lr=
            GRU_LEARNING_RATE,

        weight_decay=
            GRU_WEIGHT_DECAY,
    )


    # ========================================================
    # Early stopping
    # ========================================================

    best_pr_auc = (
        float("-inf")
    )


    best_epoch = None

    best_state = None

    epochs_without_improvement = 0


    history = []


    # ========================================================
    # Epoch loop
    # ========================================================

    for epoch in range(
        1,
        GRU_MAX_EPOCHS + 1,
    ):

        train_loss = train_one_epoch(
            model=model,
            loader=train_loader,
            optimizer=optimizer,
            loss_function=loss_function,
            device=device,
        )


        validation_metrics = (
            evaluate_sampled_validation(
                model=model,
                loader=validation_loader,
                loss_function=loss_function,
                device=device,
            )
        )


        validation_loss = (
            validation_metrics[
                "loss"
            ]
        )

        validation_pr_auc = (
            validation_metrics[
                "pr_auc"
            ]
        )

        validation_roc_auc = (
            validation_metrics[
                "roc_auc"
            ]
        )


        history.append(
            {
                "epoch":
                    epoch,

                "train_loss":
                    train_loss,

                "sampled_validation_loss":
                    validation_loss,

                "sampled_validation_pr_auc":
                    validation_pr_auc,

                "sampled_validation_roc_auc":
                    validation_roc_auc,
            }
        )


        print(
            f"\nEpoch {epoch:02d} | "
            f"train_loss={train_loss:.6f} | "
            f"val_loss={validation_loss:.6f} | "
            f"sampled_PR_AUC={validation_pr_auc:.6f} | "
            f"sampled_ROC_AUC={validation_roc_auc:.6f}"
        )


        # ====================================================
        # Improvement
        # ====================================================

        if (
            validation_pr_auc
            > best_pr_auc
        ):

            best_pr_auc = (
                validation_pr_auc
            )

            best_epoch = epoch

            best_state = copy.deepcopy(
                model.state_dict()
            )

            epochs_without_improvement = 0


            print(
                "  PASS: New best sampled-Q4 PR-AUC."
            )


        else:

            epochs_without_improvement += 1


            print(
                "  No improvement:",
                f"{epochs_without_improvement}"
                f"/{GRU_EARLY_STOPPING_PATIENCE}"
            )


        # ====================================================
        # Early stopping
        # ====================================================

        if (
            epochs_without_improvement
            >= GRU_EARLY_STOPPING_PATIENCE
        ):

            print(
                "\nEarly stopping triggered."
            )

            break


    # ========================================================
    # Restore best model
    # ========================================================

    if best_state is None:

        raise RuntimeError(
            "No GRU checkpoint was selected."
        )


    model.load_state_dict(
        best_state
    )


    # ========================================================
    # Save
    # ========================================================

    GRU_MODEL_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


    torch.save(
        {
            "model_name":
                GRU_MODEL_NAME,

            "state_dict":
                model.state_dict(),

            "best_epoch":
                best_epoch,

            "sampled_validation_pr_auc":
                best_pr_auc,
        },
        GRU_MODEL_FILE,
    )


    metadata = {
        "model_name":
            GRU_MODEL_NAME,

        "created_utc":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "best_epoch":
            best_epoch,

        "sampled_q4_pr_auc":
            best_pr_auc,

        "sampled_q4_is_final_metric":
            False,

        "training_sequences":
            len(train_dataset),

        "development_validation_sequences":
            len(validation_dataset),

        "batch_size":
            GRU_BATCH_SIZE,

        "learning_rate":
            GRU_LEARNING_RATE,

        "weight_decay":
            GRU_WEIGHT_DECAY,

        "max_epochs":
            GRU_MAX_EPOCHS,

        "early_stopping_patience":
            GRU_EARLY_STOPPING_PATIENCE,

        "training_history":
            history,

        "final_test_period_accessed":
            False,
    }


    with open(
        GRU_METADATA_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            metadata,
            file,
            indent=2,
        )


    print(
        "\n============================================"
    )
    print(
        "GRU TRAINING SUMMARY"
    )
    print(
        "============================================"
    )


    print(
        "Best epoch:",
        best_epoch
    )

    print(
        "Best sampled-Q4 PR-AUC:",
        f"{best_pr_auc:.6f}"
    )

    print(
        "Model saved:",
        GRU_MODEL_FILE
    )

    print(
        "Metadata saved:",
        GRU_METADATA_FILE
    )


    print(
        "\nIMPORTANT:"
    )

    print(
        "Sampled-Q4 PR-AUC is an early-stopping "
        "metric only."
    )

    print(
        "It must NOT be compared directly with "
        "the RF full-Q4 PR-AUC."
    )


    print(
        "\nPASS: 2026 Q1 was not accessed."
    )


    print(
        "\n============================================"
    )
    print(
        "GRU TRAINING PASSED"
    )
    print(
        "============================================"
    )


if __name__ == "__main__":
    main()