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

class EvidenceEventView(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: str
    domain: str
    event_type: str
    timestamp: datetime
    state: str
    component: str
    zone_id: str | None = None
    server_id: str | None = None
    sensor_id: str | None = None
    camera_id: str | None = None
    source_type: str | None = None

class SpecialistAssessmentView(BaseModel):
    model_config = ConfigDict(extra="forbid")
    specialist_id: str
    assessment: str
    grounding_status: Literal["SUPPORTED", "PARTIALLY_SUPPORTED", "INSUFFICIENT"]
    supported_findings: list[str] = Field(default_factory=list)
    recommended_considerations: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    citations: list[dict[str, str]] = Field(default_factory=list)

class SynthesisView(BaseModel):
    model_config = ConfigDict(extra="forbid")
    assessment: str
    grounding_status: Literal["SUPPORTED", "PARTIALLY_SUPPORTED", "INSUFFICIENT"]
    contributing_specialists: list[str] = Field(default_factory=list)
    supported_cross_domain_findings: list[str] = Field(default_factory=list)
    recommended_considerations: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    citations: list[dict[str, str]] = Field(default_factory=list)

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
    evidence_events: list[EvidenceEventView] = Field(default_factory=list)
    specialist_assessments: list[SpecialistAssessmentView] = Field(default_factory=list)
    synthesis: SynthesisView | None = None
    decision: DecisionView
