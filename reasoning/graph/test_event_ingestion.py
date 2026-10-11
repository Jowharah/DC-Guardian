"""SSH event Neo4j ingestion contract (pytest).

Evidence -> common event -> synthetic topology mapping -> Neo4j, ingested twice.
Verifies the cyber -> physical path, idempotency of events, source IPs and
relationships, and preserved provenance. Converted from the script contract
with the same 15 checks; the contract's nodes are removed afterwards.
"""
import pytest

from conftest import cleanup_graph, single
from ingest_event import ingest_ssh_event
from ssh_event_adapter import adapt_ssh_assessment
from topology_mapper import map_ssh_event_to_scenario

SCENARIO_ID = "SCENARIO-SSH-001"
SOURCE_IP = "203.0.113.20"

SSH_ASSESSMENT = {
    "event_type": "ssh_behavior_assessment",
    "source_ip": SOURCE_IP,
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
    "rule": {"prediction": "ANOMALOUS", "anomalous": True, "suspicious": False, "score": 1,
             "triggered_rules": ["ROOT_TARGETING"], "evidence": ["100% of failed attempts targeted root"]},
    "isolation_forest": {"prediction": "NORMAL", "anomalous": False, "anomaly_score": -0.138},
    "autoencoder": {"prediction": "ANOMALOUS", "anomalous": True, "reconstruction_error": 0.125,
                    "threshold": 0.0857589915394783},
    "evidence": {"failed_login_count": 6, "invalid_user_count": 0, "unique_users": 1, "failure_ratio": 1.0,
                 "root_attempt_ratio": 1.0, "breakin_warning_count": 0, "disconnect_count": 0,
                 "no_identification_count": 0, "successful_login_count": 0, "success_after_failures": 0},
}


@pytest.fixture(scope="module")
def ingested(neo4j_driver):
    cleanup_graph(neo4j_driver, scenarios=[SCENARIO_ID], source_ips=[SOURCE_IP])
    normalized = adapt_ssh_assessment(SSH_ASSESSMENT, dataset_name="DC-Guardian Integration Test",
                                      source_type="CONTROLLED_TEST", event_id="EVT-SSH-INTEGRATION-001")
    mapped = map_ssh_event_to_scenario(normalized, scenario_id=SCENARIO_ID,
                                       scenario_timestamp="2026-09-18T12:00:00Z", target_name="ZONE_A_SERVER")
    first = ingest_ssh_event(mapped, neo4j_driver)
    second = ingest_ssh_event(mapped, neo4j_driver)
    yield {"driver": neo4j_driver, "first": first, "second": second, "event_id": first["event_id"]}
    cleanup_graph(neo4j_driver, scenarios=[SCENARIO_ID], source_ips=[SOURCE_IP])


def test_ingestion_reports_target_server_and_source_ip(ingested):
    assert ingested["first"]["server_id"] == "SRV-A1-01"
    assert ingested["first"]["source_ip"] == SOURCE_IP


def test_repeated_ingestion_keeps_the_event_id(ingested):
    assert ingested["second"]["event_id"] == ingested["first"]["event_id"]


def test_event_node_is_idempotent(ingested):
    record = single(ingested["driver"], "MATCH (e:Event {event_id: $id}) RETURN count(e) AS count",
                    id=ingested["event_id"])
    assert record["count"] == 1


def test_source_ip_node_is_idempotent(ingested):
    record = single(ingested["driver"], "MATCH (ip:SourceIP {address: $address}) RETURN count(ip) AS count",
                    address=SOURCE_IP)
    assert record["count"] == 1


def test_cyber_to_physical_path(ingested):
    record = single(ingested["driver"], """
        MATCH (e:Event {event_id: $id})-[:TARGETS]->(s:Server)-[:LOCATED_IN]->(r:Rack)
              -[:LOCATED_IN]->(z:Zone)-[:PART_OF]->(dc:DataCenter)
        MATCH (e)-[:ORIGINATED_FROM]->(ip:SourceIP)
        RETURN s.server_id AS server_id, r.rack_id AS rack_id, z.zone_id AS zone_id,
               dc.data_center_id AS data_center_id""", id=ingested["event_id"])
    assert record is not None, "Cyber -> physical graph path was not found."
    assert record["server_id"] == "SRV-A1-01"
    assert record["rack_id"] == "RACK-A1"
    assert record["zone_id"] == "ZONE-A"
    assert record["data_center_id"] == "DC-01"


def test_targets_and_originated_from_are_unique(ingested):
    record = single(ingested["driver"], """
        MATCH (e:Event {event_id: $id})-[t:TARGETS]->(:Server)
        WITH e, count(t) AS target_count
        MATCH (e)-[o:ORIGINATED_FROM]->(:SourceIP)
        RETURN target_count, count(o) AS origin_count""", id=ingested["event_id"])
    assert record["target_count"] == 1
    assert record["origin_count"] == 1


def test_provenance_is_preserved(ingested):
    record = single(ingested["driver"], """
        MATCH (e:Event {event_id: $id})
        RETURN e.synthetic_mapping AS synthetic_mapping, e.mapping_type AS mapping_type,
               e.scenario_id AS scenario_id""", id=ingested["event_id"])
    assert record["synthetic_mapping"] is True
    assert record["mapping_type"] == "SYNTHETIC_SCENARIO"
    assert record["scenario_id"] == SCENARIO_ID
