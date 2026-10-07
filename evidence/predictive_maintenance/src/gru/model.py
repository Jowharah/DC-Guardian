"""
DC-Guardian Phase 1
Predictive Maintenance GRU Model

Experimental sequence-learning challenger to the frozen
Temporal Random Forest v2.
"""

import torch
from torch import nn

from evidence.predictive_maintenance.src.gru.config import (
    GRU_DROPOUT,
    GRU_HIDDEN_SIZE,
    GRU_INPUT_SIZE,
    GRU_NUM_LAYERS,
)


class MaintenanceGRU(nn.Module):
    """
    GRU binary classifier.

    Input shape:
        batch x sequence_length x SMART_features

    Output:
        one raw failure-risk logit per sequence
    """

    def __init__(self):

        super().__init__()

        self.gru = nn.GRU(
            input_size=GRU_INPUT_SIZE,
            hidden_size=GRU_HIDDEN_SIZE,
            num_layers=GRU_NUM_LAYERS,
            batch_first=True,
            dropout=(
                GRU_DROPOUT
                if GRU_NUM_LAYERS > 1
                else 0.0
            ),
        )

        self.output = nn.Linear(
            GRU_HIDDEN_SIZE,
            1,
        )


    def forward(
        self,
        x,
    ):

        _, hidden = self.gru(
            x
        )

        final_hidden = hidden[-1]

        logits = self.output(
            final_hidden
        ).squeeze(-1)

        return logits
