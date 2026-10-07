"""Real Environmental + Maintenance Reasoning vertical slice."""

from __future__ import annotations

from reasoning.adapters.environmental_event_adapter import adapt_environmental_assessment
from reasoning.adapters.maintenance_event_adapter import adapt_maintenance_assessment
from reasoning.correlation.correlation_engine import find_cross_domain_correlations
from reasoning.graph.ingest_event import (
    NEO4J_DATABASE,
    create_driver,
    ingest_environmental_event,
    ingest_maintenance_event,
)
from reasoning.topology.topology_mapper import (
    map_environmental_event_to_scenario,
    map_maintenance_event_to_scenario,
)


TARGET = "ZONE_B_CRITICAL_STORAGE"


def _maintenance_assessment() -> dict:
    return {
        "domain": "MAINTENANCE",
        "event_type": "STORAGE_FAILURE_RISK_ASSESSMENT",
        "model_name": "DC_Guardian_Temporal_RF_v2",
        "asset_type": "HARD_DRIVE",
        "serial_number": "DRV-OPS-001",
        "observation_timestamp": "2026-10-06T13:00:00Z",
        "assessment": "AT_RISK",
        "failure_probability": 0.61,
        "operating_threshold": 0.45,
        "failure_horizon_days": 7,
        "evidence": {
            "smart_5_raw": 20.0,
            "smart_198_raw": 2.0,
            "smart_194_raw": 35.0,
            "smart_5_delta_7": 20.0,
            "smart_198_delta_7": 2.0,
            "temperature_7obs_mean": 33.86,
        },
    }


def _environmental_assessment() -> dict:
    return {
        "domain": "ENVIRONMENTAL",
        "event_type": "ENVIRONMENTAL_CONDITION_ASSESSMENT",
        "component": "environmental_detector",
        "component_version": "1.0",
        "source_class": "ENVIRONMENTAL_SENSOR",
        "source_id": "SEN-B-01",
        "source_asset_type": "ENVIRONMENTAL_SENSOR",
        "observation_timestamp": "2026-10-06T13:03:00Z",
        "assessment": "HIGH_TEMPERATURE",
        "anomaly_detected": True,
        "measurements": {"temperature_c": 34.0, "humidity_pct": 48.0},
        "evidence": {
            "triggered_conditions": ["HIGH_TEMPERATURE"],
            "measurements": {"temperature_c": 34.0, "humidity_pct": 48.0},
            "thresholds": {"temperature_high_c": 30.0},
        },
    }


def _clear(driver, scenario_id: str) -> None:
    with driver.session(database=NEO4J_DATABASE) as session:
        session.run(
            "MATCH (event:Event) WHERE event.scenario_id = $scenario_id "
            "DETACH DELETE event",
            scenario_id=scenario_id,
        ).consume()


def run_real_environmental_maintenance_reasoning(*, scenario_id: str) -> dict:
    maintenance = adapt_maintenance_assessment(
        _maintenance_assessment(),
        dataset_name="Controlled Temporal RF Integration Evidence",
        source_type="CONTROLLED_TEST",
        event_id=f"{scenario_id}-MAINT",
    )
    maintenance = map_maintenance_event_to_scenario(
        maintenance,
        scenario_id=scenario_id,
        scenario_timestamp="2026-10-06T13:00:00Z",
        target_name=TARGET,
    )

    environmental = adapt_environmental_assessment(
        _environmental_assessment(),
        dataset_name="Controlled Environmental Integration Evidence",
        source_type="CONTROLLED_TEST",
        event_id=f"{scenario_id}-ENV",
    )
    environmental = map_environmental_event_to_scenario(
        environmental,
        scenario_id=scenario_id,
        scenario_timestamp="2026-10-06T13:03:00Z",
    )

    driver = create_driver()
    try:
        _clear(driver, scenario_id)
        maint_result = ingest_maintenance_event(maintenance, driver)
        env_result = ingest_environmental_event(environmental, driver)

        correlations = find_cross_domain_correlations(
            driver, scenario_id=scenario_id, window_minutes=15
        )
        if len(correlations) != 1:
            raise RuntimeError(
                f"Expected one Environmental/Maintenance correlation; "
                f"found {len(correlations)}."
            )
        correlation = correlations[0]
        domains = sorted({x["domain"] for x in correlation["events"]})
        if domains != ["ENVIRONMENTAL", "MAINTENANCE"]:
            raise RuntimeError(f"Unexpected correlated domains: {domains}")

        return {
            "scenario_id": scenario_id,
            "domains": domains,
            "correlation": correlation,
            "shared_scope": correlation["scope"],
            "shared_entity": correlation["shared_entity_id"],
            "identity_link_established": False,
            "causal_relationship_established": False,
            "root_cause_established": False,
            "evidence_events": [maintenance, environmental],
            "ingestion": {
                "maintenance": maint_result,
                "environmental": env_result,
            },
        }
    finally:
        driver.close()

