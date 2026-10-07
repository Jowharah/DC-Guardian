"""Real Cybersecurity + Environmental + Maintenance Reasoning slice."""

from __future__ import annotations

from evidence.environmental_monitoring.src.sensor_monitor import assess_sensor_reading
from reasoning.adapters.environmental_event_adapter import adapt_environmental_assessment
from reasoning.adapters.maintenance_event_adapter import adapt_maintenance_assessment
from reasoning.adapters.ssh_event_adapter import adapt_ssh_assessment
from reasoning.correlation.correlation_engine import find_multi_domain_correlations
from reasoning.graph.ingest_event import (
    NEO4J_DATABASE,
    create_driver,
    ingest_environmental_event,
    ingest_maintenance_event,
    ingest_ssh_event,
)
from reasoning.topology.topology_mapper import (
    map_environmental_event_to_scenario,
    map_maintenance_event_to_scenario,
    map_ssh_event_to_scenario,
)


def _ssh() -> dict:
    return {
        "event_type": "ssh_behavior_assessment",
        "source_ip": "203.0.113.77",
        "window_start": "2000-12-17T02:25:00Z",
        "window_end": "2000-12-17T02:30:00Z",
        "anomaly_detected": True,
        "detector_votes": 2,
        "detector_combination": "RULE+AE",
        "confidence": "MEDIUM",
        "evidence_state": "HIGH_CONFIDENCE_ANOMALY",
        "explicit_security_signal": False,
        "security_signals": [],
        "security_signal_evidence": [],
        "rule": {"prediction":"ANOMALOUS","anomalous":True,"suspicious":False,
                 "score":1,"triggered_rules":["ROOT_TARGETING"],
                 "evidence":["Integrated three-domain scenario"]},
        "isolation_forest": {"prediction":"NORMAL","anomalous":False,"anomaly_score":-0.10},
        "autoencoder": {"prediction":"ANOMALOUS","anomalous":True,
                        "reconstruction_error":0.125,"threshold":0.0857589915394783},
        "evidence": {"failed_login_count":6,"invalid_user_count":0,"unique_users":1,
                     "failure_ratio":1.0,"root_attempt_ratio":1.0,
                     "breakin_warning_count":0,"disconnect_count":0,
                     "no_identification_count":0,"successful_login_count":0,
                     "success_after_failures":0},
    }


def _maintenance() -> dict:
    return {
        "domain":"MAINTENANCE","event_type":"STORAGE_FAILURE_RISK_ASSESSMENT",
        "model_name":"DC_Guardian_Temporal_RF_v2","asset_type":"HARD_DRIVE",
        "serial_number":"DRV-INTEGRATION-3D-001",
        "observation_timestamp":"2026-10-06T14:05:00Z","assessment":"AT_RISK",
        "failure_probability":0.714008,"operating_threshold":0.45,
        "failure_horizon_days":7,
        "evidence":{"smart_5_raw":20.0,"smart_198_raw":2.0,"smart_194_raw":35.0,
                    "smart_5_delta_7":20.0,"smart_198_delta_7":2.0,
                    "temperature_7obs_mean":33.8571428571},
    }


def _clear(driver, scenario_id):
    with driver.session(database=NEO4J_DATABASE) as session:
        session.run("MATCH (e:Event) WHERE e.scenario_id=$id DETACH DELETE e", id=scenario_id).consume()


def run_real_cyber_environmental_maintenance_reasoning(*, scenario_id: str) -> dict:
    cyber = map_ssh_event_to_scenario(
        adapt_ssh_assessment(_ssh(), dataset_name="Integrated 3D Scenario",
                             source_type="CONTROLLED_TEST", event_id=f"{scenario_id}-SSH"),
        scenario_id=scenario_id, scenario_timestamp="2026-10-06T14:00:00Z",
        target_name="ZONE_B_CRITICAL_SERVER",
    )
    env_assessment = assess_sensor_reading(
        sensor_id="SEN-B-01", observation_timestamp="2026-10-06T14:03:00Z",
        temperature_c=42.5, humidity_pct=48.0,
    )
    environmental = map_environmental_event_to_scenario(
        adapt_environmental_assessment(
            env_assessment, dataset_name="Integrated 3D Scenario",
            source_type="CONTROLLED_TEST", event_id=f"{scenario_id}-ENV"),
        scenario_id=scenario_id, scenario_timestamp="2026-10-06T14:03:00Z",
    )
    maintenance = map_maintenance_event_to_scenario(
        adapt_maintenance_assessment(
            _maintenance(), dataset_name="Integrated 3D Scenario",
            source_type="CONTROLLED_TEST", event_id=f"{scenario_id}-MAINT"),
        scenario_id=scenario_id, scenario_timestamp="2026-10-06T14:05:00Z",
        target_name="ZONE_B_CRITICAL_STORAGE",
    )

    driver=create_driver()
    try:
        _clear(driver, scenario_id)
        ingest_ssh_event(cyber, driver)
        ingest_environmental_event(environmental, driver)
        ingest_maintenance_event(maintenance, driver)
        correlations=find_multi_domain_correlations(
            driver, scenario_id=scenario_id, window_minutes=15, minimum_domains=3)
        if len(correlations)!=1:
            raise RuntimeError(f"Expected one three-domain correlation, found {len(correlations)}")
        correlation=correlations[0]
        domains=sorted(correlation["domains"])
        if domains != ["CYBERSECURITY","ENVIRONMENTAL","MAINTENANCE"]:
            raise RuntimeError(f"Unexpected domains: {domains}")
        return {
            "scenario_id":scenario_id,"domains":domains,"correlation":correlation,
            "shared_scope":correlation["scope"],"shared_entity":correlation["shared_entity_id"],
            "identity_link_established":False,"confirmed_compromise":False,
            "causal_relationship_established":False,"root_cause_established":False,
            "evidence_events":[cyber,environmental,maintenance],
        }
    finally:
        driver.close()


