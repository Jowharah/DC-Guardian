"""Access-management permission boundaries and transaction logic."""
from fastapi.testclient import TestClient
from presentation.backend.app.main import app
from presentation.backend.app.authentication import current_principal
from presentation.backend.app.authorization import Principal
from presentation.backend.app.employee_access import _change

def test_non_admin_cannot_manage_employees():
    app.dependency_overrides[current_principal] = lambda: Principal(
        "safety", frozenset({"safety_operator"}), frozenset({"ZONE-B"}))
    try:
        client = TestClient(app)
        assert client.get("/api/v1/access/employees").status_code == 403
        assert client.post("/api/v1/access/employees", json={"person_id":"P005","role":"TECHNICIAN"}).status_code == 403
        assert client.post("/api/v1/access/employees/P005/zones",
                           json={"zone_id":"ZONE-B","action":"GRANT"}).status_code == 403
    finally:
        app.dependency_overrides.pop(current_principal, None)

def test_admin_cannot_grant_outside_assigned_zone():
    app.dependency_overrides[current_principal] = lambda: Principal(
        "admin", frozenset({"administrator"}), frozenset({"ZONE-A"}))
    try:
        client = TestClient(app)
        assert client.post("/api/v1/access/employees/P005/zones",
                           json={"zone_id":"ZONE-B","action":"GRANT"}).status_code == 403
    finally:
        app.dependency_overrides.pop(current_principal, None)

def test_invalid_employee_id_rejected():
    app.dependency_overrides[current_principal] = lambda: Principal(
        "admin", frozenset({"administrator"}), frozenset({"ZONE-A"}))
    try:
        client = TestClient(app)
        assert client.post("/api/v1/access/employees",
                           json={"person_id":"bad-id","role":"TECHNICIAN"}).status_code == 422
    finally:
        app.dependency_overrides.pop(current_principal, None)
