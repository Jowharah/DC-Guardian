"""Validated custom synthetic environmental observations, no invented SSH inference."""
from datetime import datetime, timezone
from pathlib import Path
import json
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from evidence.environmental_monitoring.src.environmental_detector import assess_environmental_condition

TOPOLOGY_FILE = Path(__file__).resolve().parents[3] / "shared" / "topology" / "data_center_topology.json"

class EnvironmentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sensor_id: str
    temperature_c: float | None = Field(default=None, ge=-100, le=150)
    humidity_pct: float | None = Field(default=None, ge=0, le=100)
    @model_validator(mode="after")
    def require_measurement(self):
        if self.temperature_c is None and self.humidity_pct is None:
            raise ValueError("Provide temperature or humidity")
        return self

class CustomScenarioInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    zone_id: str
    server_id: str | None = None
    environmental: EnvironmentInput
    source: Literal["CONTROLLED_SYNTHETIC_SCENARIO"] = "CONTROLLED_SYNTHETIC_SCENARIO"

class CustomScenarioResult(BaseModel):
    source: Literal["CONTROLLED_SYNTHETIC_SCENARIO"]
    zone_id: str
    server_id: str | None
    sensor_id: str
    environmental_assessment: str
    anomaly_detected: bool
    measurements: dict
    thresholds: dict
    note: str = "Environmental detector only. No SSH inference, cross-domain correlation, or Decision evaluation performed."

def topology_options() -> list[dict]:
    with TOPOLOGY_FILE.open(encoding="utf-8-sig") as handle:
        zones = json.load(handle)["data_center"]["zones"]
    return [
        {"zone_id": zone["zone_id"],
         "servers": [s["server_id"] for rack in zone.get("racks", []) for s in rack.get("servers", [])],
         "sensors": [s["sensor_id"] for s in zone.get("sensors", [])]}
        for zone in zones
    ]

def assess_custom_environment(payload: CustomScenarioInput) -> CustomScenarioResult:
    options = next((z for z in topology_options() if z["zone_id"] == payload.zone_id), None)
    if options is None:
        raise ValueError("Unknown zone")
    if payload.server_id is not None and payload.server_id not in options["servers"]:
        raise ValueError("Server does not belong to selected zone")
    if payload.environmental.sensor_id not in options["sensors"]:
        raise ValueError("Sensor does not belong to selected zone")
    result = assess_environmental_condition(
        source_class="ENVIRONMENTAL_SENSOR",
        source_id=payload.environmental.sensor_id,
        observation_timestamp=datetime.now(timezone.utc),
        temperature_c=payload.environmental.temperature_c,
        humidity_pct=payload.environmental.humidity_pct,
    )
    return CustomScenarioResult(
        source="CONTROLLED_SYNTHETIC_SCENARIO",
        zone_id=payload.zone_id, server_id=payload.server_id,
        sensor_id=payload.environmental.sensor_id,
        environmental_assessment=result["assessment"],
        anomaly_detected=result["anomaly_detected"],
        measurements=result["measurements"],
        thresholds=result["evidence"]["thresholds"],
    )
