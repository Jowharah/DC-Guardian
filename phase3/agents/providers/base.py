"""Provider interface for grounded reasoning."""

from __future__ import annotations

from abc import ABC, abstractmethod


class GroundedReasoningProvider(ABC):
    @abstractmethod
    def reason(self, payload: dict) -> dict:
        """Return a structured grounded assessment."""
        raise NotImplementedError
