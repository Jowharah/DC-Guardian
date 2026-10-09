"""Maintenance mapping, idempotent event identities, and Decision boundary."""
from datetime import datetime, timezone
from presentation.backend.app.maintenance_workflow import mapped_event

def test_frozen_assessment_maps_without_changing_drive_identity():
    assessment={
        "domain":"MAINTENANCE","event_type":"STORAGE_FAILURE_RISK_ASSESSMENT",
        "model_name":"DC_Guardian_Temporal_RF_v2","asset_type":"HARD_DRIVE",
        "serial_number":"TEST-DRIVE-01","observation_timestamp":"2026-10-06T13:00:00+00:00",
        "assessment":"AT_RISK","failure_probability":0.61,
        "operating_threshold":0.45,"failure_horizon_days":7,
        "evidence":{"smart_5_raw":20.0,"smart_198_raw":2.0,"smart_194_raw":35.0,
                    "smart_5_delta_7":20.0,"smart_198_delta_7":2.0,
                    "temperature_7obs_mean":33.86},
    }
    mapped=mapped_event("MAINT-EVT-TEST",assessment,"SRV-B1-01","ZONE-B")
    assert mapped["entities"]["asset_id"]=="TEST-DRIVE-01"
    assert mapped["entities"]["server_id"]=="SRV-B1-01"
    assert mapped["location"]["zone_id"]=="ZONE-B"
    assert mapped["assessment"]["state"]=="AT_RISK"
    assert mapped["provenance"]["original_event_id"]=="MAINT-EVT-TEST"
    assert mapped["provenance"]["synthetic_mapping"] is True
    assert assessment["serial_number"]=="TEST-DRIVE-01"

def test_mismatched_zone_rejected():
    try:
        mapped_event("MAINT-EVT-TEST",{},"SRV-B1-01","ZONE-A")
    except ValueError:
        pass
    else:
        raise AssertionError("Cross-zone mapping allowed")
