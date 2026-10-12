"""Predictive-maintenance event Neo4j ingestion contract (pytest).

Evidence -> common event -> synthetic topology mapping -> Neo4j, ingested twice.
Verifies the Event -> Drive -> Server -> Rack -> Zone -> DC path, preserved
model values, idempotency, and the drive's HOSTED_BY relationship. Converted
from the script contract with the same 15 checks; the contract's nodes,
including its test-only drive, are removed afterwards.
"""
import pytest

from graph_test_support import cleanup_graph, single
from ingest_event import ingest_maintenance_event
from maintenance_event_adapter import adapt_maintenance_assessment
from topology_mapper import map_maintenance_event_to_scenario

SCENARIO_ID = "SCENARIO-MAINT-001"
DRIVE_ID = "DRV-MAINT-GRAPH-001"

ASSESSMENT = {
    "domain": "MAINTENANCE",
    "event_type": "STORAGE_FAILURE_RISK_ASSESSMENT",
    "model_name": "DC_Guardian_Temporal_RF_v2",
    "asset_type": "HARD_DRIVE",
    "serial_number": DRIVE_ID,
    "observation_timestamp": "2026-03-20T00:00:00Z",
    "assessment": "AT_RISK",
    "failure_probability": 0.714008,
    "operating_threshold": 0.45,
    "failure_horizon_days": 7,
    "evidence": {"smart_5_raw": 20.0, "smart_198_raw": 2.0, "smart_194_raw": 35.0, "smart_5_delta_7": 20.0,
                 "smart_198_delta_7": 2.0, "temperature_7obs_mean": 33.8571428571},
}


@pytest.fixture(scope="module")
def ingested(neo4j_driver):
    cleanup_graph(neo4j_driver, scenarios=[SCENARIO_ID], assets=[DRIVE_ID])
    normalized = adapt_maintenance_assessment(ASSESSMENT, dataset_name="DC-Guardian Maintenance Integration Test",
                                              source_type="CONTROLLED_TEST", event_id="EVT-MAINT-INTEGRATION-001")
    mapped = map_maintenance_event_to_scenario(normalized, scenario_id=SCENARIO_ID,
                                               scenario_timestamp="2026-09-18T12:05:00Z",
                                               target_name="ZONE_B_CRITICAL_STORAGE")
    first = ingest_maintenance_event(mapped, neo4j_driver)
    second = ingest_maintenance_event(mapped, neo4j_driver)
    yield {"driver": neo4j_driver, "first": first, "second": second, "event_id": first["event_id"]}
    cleanup_graph(neo4j_driver, scenarios=[SCENARIO_ID], assets=[DRIVE_ID])


def test_ingestion_reports_drive_and_server(ingested):
    assert ingested["first"]["asset_id"] == DRIVE_ID
    assert ingested["first"]["server_id"] == "SRV-B1-01"


def test_repeated_ingestion_keeps_the_event_id(ingested):
    assert ingested["second"]["event_id"] == ingested["first"]["event_id"]


def test_maintenance_to_physical_path(ingested):
    context = single(ingested["driver"], """
        MATCH (e:Event {event_id: $id})-[:TARGETS]->(a:Asset)-[:HOSTED_BY]->(s:Server)
              -[:LOCATED_IN]->(r:Rack)-[:LOCATED_IN]->(z:Zone)-[:PART_OF]->(dc:DataCenter)
        RETURN e.failure_probability AS failure_probability, a.asset_id AS asset_id,
               a.asset_type AS asset_type, s.server_id AS server_id, r.rack_id AS rack_id,
               z.zone_id AS zone_id, dc.data_center_id AS data_center_id""", id=ingested["event_id"])
    assert context is not None, "Maintenance -> physical graph path not found."
    assert context["asset_id"] == DRIVE_ID
    assert context["asset_type"] == "HARD_DRIVE"
    assert context["server_id"] == "SRV-B1-01"
    assert context["rack_id"] == "RACK-B1"
    assert context["zone_id"] == "ZONE-B"
    assert context["data_center_id"] == "DC-01"
    assert abs(context["failure_probability"] - 0.714008) < 1e-9


def test_event_and_targets_are_idempotent(ingested):
    record = single(ingested["driver"], """
        MATCH (e:Event {event_id: $id})
        OPTIONAL MATCH (e)-[t:TARGETS]->(:Asset)
        RETURN count(DISTINCT e) AS event_count, count(t) AS target_count""", id=ingested["event_id"])
    assert record["event_count"] == 1
    assert record["target_count"] == 1


def test_drive_is_hosted_by_exactly_one_server(ingested):
    record = single(ingested["driver"], """
        MATCH (a:Asset {asset_id: $asset_id})-[h:HOSTED_BY]->(s:Server)
        RETURN count(h) AS hosted_by_count, collect(s.server_id) AS servers""", asset_id=DRIVE_ID)
    assert record["hosted_by_count"] == 1
    assert record["servers"] == ["SRV-B1-01"]
