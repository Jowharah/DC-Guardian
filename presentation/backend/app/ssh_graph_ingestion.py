"""Ingest published frozen SSH evidence with controlled operator topology assignment.

Preserves original detector window; does not fabricate correlation or severity.
"""
from copy import deepcopy
from datetime import datetime, timezone
from reasoning.adapters.ssh_event_adapter import adapt_ssh_assessment
from reasoning.topology.topology_mapper import load_topology, build_server_index
from reasoning.graph.ingest_event import create_driver, ingest_ssh_event

def prepare_mapped_ssh(event_id: str, assessment: dict, server_id: str, zone_id: str) -> dict:
    topology = load_topology()
    target = build_server_index(topology).get(server_id)
    if target is None or target["zone_id"] != zone_id:
        raise ValueError("Selected server and zone do not match controlled topology")
    normalized = adapt_ssh_assessment(
        assessment, dataset_name="Operator uploaded OpenSSH log",
        source_type="CONTROLLED_TEST", event_id=event_id)
    original_time = normalized["timestamp"]
    if not original_time or not normalized["entities"]["source_ip"]:
        raise ValueError("SSH event requires original timestamp and source IP")
    # Syslog's placeholder year is retained. Do not silently replace it with now.
    timestamp = datetime.fromisoformat(original_time.replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        # Explicit controlled-test convention only; original syslog has no timezone.
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    normalized["timestamp"] = timestamp.isoformat()
    normalized["window"]["start"] = timestamp.isoformat()
    end = datetime.fromisoformat(normalized["window"]["end"].replace("Z", "+00:00"))
    normalized["window"]["end"] = (end.replace(tzinfo=timezone.utc) if end.tzinfo is None else end).isoformat()
    mapped = deepcopy(normalized)
    scenario_id = "DCG-SSH-" + event_id.removeprefix("SSH-EVT-")
    mapped["event_id"] = event_id + "-MAPPED"
    mapped["entities"]["server_id"] = server_id
    mapped["entities"]["asset_id"] = server_id
    mapped["location"].update({
        "data_center_id": target["data_center_id"],
        "zone_id": zone_id, "rack_id": target["rack_id"]})
    mapped["provenance"].update({
        "original_event_id": event_id,
        "original_timestamp": original_time,
        "synthetic_mapping": True, "mapping_type": "SYNTHETIC_SCENARIO",
        "scenario_id": scenario_id})
    return mapped

def ingest_published_ssh(event_id: str, assessment: dict, server_id: str, zone_id: str) -> dict:
    mapped = prepare_mapped_ssh(event_id, assessment, server_id, zone_id)
    driver = create_driver()
    try:
        result = ingest_ssh_event(mapped, driver)
    finally:
        driver.close()
    return {**result, "scenario_id": mapped["provenance"]["scenario_id"],
            "original_timestamp": mapped["provenance"]["original_timestamp"]}
