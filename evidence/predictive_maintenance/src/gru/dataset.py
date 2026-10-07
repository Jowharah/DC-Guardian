"""
DC-Guardian Evidence
Predictive Maintenance GRU Dataset

Shared preprocessing for training and validation sequence stores.

Normalization statistics are ALWAYS loaded from training data.
"""

from pathlib import Path

import numpy as np
import torch
from torch.utils.data import Dataset

from evidence.predictive_maintenance.src.gru.config import (
    GRU_CLIP_VALUE,
    GRU_LOG1P_FEATURES,
    GRU_NORMALIZATION_FILE,
    GRU_SMART_FEATURES,
    GRU_TRAIN_LABEL_FILE,
    GRU_TRAIN_SEQUENCE_FILE,
    GRU_VALIDATION_LABEL_FILE,
    GRU_VALIDATION_SEQUENCE_FILE,
)


class GRUSequenceDataset(Dataset):

    def __init__(
        self,
        sequence_file,
        label_file,
    ):

        self.sequence_file = Path(
            sequence_file
        )

        self.label_file = Path(
            label_file
        )

        if not self.sequence_file.exists():

            raise FileNotFoundError(
                f"Sequence file missing: "
                f"{self.sequence_file}"
            )

        if not self.label_file.exists():

            raise FileNotFoundError(
                f"Label file missing: "
                f"{self.label_file}"
            )

        self.sequences = np.load(
            self.sequence_file,
            mmap_mode="r",
        )

        self.labels = np.load(
            self.label_file,
            mmap_mode="r",
        )

        normalization = np.load(
            GRU_NORMALIZATION_FILE,
        )

        saved_features = (
            normalization[
                "features"
            ]
            .astype(str)
            .tolist()
        )

        if saved_features != GRU_SMART_FEATURES:

            raise RuntimeError(
                "Normalization feature order "
                "does not match GRU contract."
            )

        self.median = (
            normalization[
                "median"
            ]
            .astype(
                np.float32
            )
        )

        self.scale = (
            normalization[
                "scale"
            ]
            .astype(
                np.float32
            )
        )

        self.log1p_mask = np.asarray(
            [
                feature
                in GRU_LOG1P_FEATURES
                for feature
                in GRU_SMART_FEATURES
            ],
            dtype=bool,
        )

        if len(
            self.sequences
        ) != len(
            self.labels
        ):

            raise RuntimeError(
                "Sequence/label count mismatch."
            )


    def __len__(self):

        return len(
            self.labels
        )


    def __getitem__(
        self,
        index,
    ):

        x = np.array(
            self.sequences[
                index
            ],
            dtype=np.float32,
            copy=True,
        )

        y = float(
            self.labels[
                index
            ]
        )

        # ====================================================
        # log1p transformed SMART count channels
        # ====================================================

        for channel in np.flatnonzero(
            self.log1p_mask
        ):

            values = x[
                :,
                channel
            ]

            values[
                values < 0
            ] = np.nan

            x[
                :,
                channel
            ] = np.log1p(
                values
            )

        # ====================================================
        # Training-median imputation
        # ====================================================

        missing = ~np.isfinite(
            x
        )

        if missing.any():

            row_index, channel_index = np.where(
                missing
            )

            x[
                row_index,
                channel_index
            ] = self.median[
                channel_index
            ]

        # ====================================================
        # Training-only robust normalization
        # ====================================================

        x = (
            x
            - self.median
        ) / self.scale

        # ====================================================
        # Extreme-value clipping
        # ====================================================

        x = np.clip(
            x,
            -GRU_CLIP_VALUE,
            GRU_CLIP_VALUE,
        )

        return (
            torch.from_numpy(
                x.astype(
                    np.float32,
                    copy=False,
                )
            ),

            torch.tensor(
                y,
                dtype=torch.float32,
            ),
        )


def build_training_dataset():

    return GRUSequenceDataset(
        sequence_file=
            GRU_TRAIN_SEQUENCE_FILE,

        label_file=
            GRU_TRAIN_LABEL_FILE,
    )


def build_validation_dataset():

    return GRUSequenceDataset(
        sequence_file=
            GRU_VALIDATION_SEQUENCE_FILE,

        label_file=
            GRU_VALIDATION_LABEL_FILE,
    )
