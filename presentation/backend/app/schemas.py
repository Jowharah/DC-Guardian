"""Versioned Presentation contracts: controlled research scenarios only."""
from typing import Any, Literal
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class ScenarioInfo(BaseModel):
    name: str
    description: str

class DecisionView(BaseModel):
    model_config = ConfigDict(extra="forbid")
    incident_status: str
    severity: Literal["LOW", "MEDIUM", "HIGH"]
    response_mode: str
    escalation_required: bool
    autonomous_action_allowed: Literal[False]
    decision_rules_triggered: list[str]
    rationale: list[str]
    protected_boundaries: dict[str, bool]
    policy_version: str

class IncidentView(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1.0"] = "1.0"
    scenario_id: str
    received_at: datetime | None = None
    event_time: datetime | None = None
    scenario_name: str
    data_origin: Literal["CONTROLLED_SYNTHETIC_SCENARIO"] = "CONTROLLED_SYNTHETIC_SCENARIO"
    domains: list[str] = Field(default_factory=list)
    shared_scope: Any = None
    shared_entity: Any = None
    evidence_event_ids: list[str] = Field(default_factory=list)
    decision: DecisionView
