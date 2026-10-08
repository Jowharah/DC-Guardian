"""Custom scenario tests using real deterministic environmental assessment."""
import pytest
from fastapi.testclient import TestClient
from presentation.backend.app.main import app
from presentation.backend.app.custom_scenarios import topology_options

client = TestClient(app)

def test_topology_options():
    response = client.get("/api/v1/topology/options")
    assert response.status_code == 200
    assert any(z["zone_id"] == "ZONE-B" for z in response.json())

def test_custom_environment():
    zone = next(z for z in topology_options() if z["zone_id"] == "ZONE-B")
    response = client.post("/api/v1/custom-scenarios/environment", json={
        "zone_id":"ZONE-B","server_id":zone["servers"][0],
        "environmental":{"sensor_id":zone["sensors"][0],"temperature_c":38}
    })
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["source"] == "CONTROLLED_SYNTHETIC_SCENARIO"
    assert data["measurements"]["temperature_c"] == 38
    assert "SSH inference" in data["note"]

def test_wrong_sensor_zone_rejected():
    response = client.post("/api/v1/custom-scenarios/environment", json={
        "zone_id":"ZONE-B",
        "environmental":{"sensor_id":"SEN-A-01","temperature_c":38}
    })
    assert response.status_code == 422

def test_missing_measurements_rejected():
    response = client.post("/api/v1/custom-scenarios/environment", json={
        "zone_id":"ZONE-B","environmental":{"sensor_id":"SEN-B-01"}
    })
    assert response.status_code == 422
