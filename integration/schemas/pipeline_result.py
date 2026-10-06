"""Result contract for the integrated DC-GUARDIAN pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class PipelineResult:
    scenario_id: str
    evidence: dict = field(default_factory=dict)
    reasoning: dict = field(default_factory=dict)
    response: dict = field(default_factory=dict)
    decision: dict = field(default_factory=dict)
    provenance: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)
