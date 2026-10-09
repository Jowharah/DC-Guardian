"""Environmental batch validates actual sensor identity and preserves timestamps."""
from presentation.backend.app.environment_workflow import map_sensor,process_sensor_batch
from evidence.environmental_monitoring.src.sensor_monitor import assess_sensor_reading
import pytest

def test_sensor_mapping_preserves_source_time():
    assessment=assess_sensor_reading(sensor_id="SEN-B-01",
        observation_timestamp="2026-10-06T13:03:00Z",temperature_c=34,humidity_pct=48)
    mapped=map_sensor("ENV-EVT-TEST",assessment,"ZONE-B")
    assert mapped["entities"]["sensor_id"]=="SEN-B-01"
    assert mapped["location"]["zone_id"]=="ZONE-B"
    assert mapped["provenance"]["original_event_id"]=="ENV-EVT-TEST"
    assert mapped["provenance"]["synthetic_mapping"] is True
    assert mapped["timestamp"]=="2026-10-06T13:03:00Z"

def test_sensor_wrong_zone_rejected():
    assessment=assess_sensor_reading(sensor_id="SEN-B-01",
        observation_timestamp="2026-10-06T13:03:00Z",temperature_c=34)
    with pytest.raises(ValueError):
        map_sensor("ENV-EVT-TEST",assessment,"ZONE-A")

def test_preview_never_writes_graph():
    rows=[{"timestamp":"2026-10-06T13:03:00Z","temperature_c":34,"humidity_pct":48}]
    result=process_sensor_batch(rows,"ZONE-B","SEN-B-01",False)
    assert result["published"] is False
    assert result["events"]==[]
    assert result["assessments"][0]["assessment"]=="HIGH_TEMPERATURE"
