"""Pure RBAC policy contract tests; no forged HTTP identity or role selector."""
import pytest
from presentation.backend.app.authorization import Principal, Permission, allowed, require

VIEWER = Principal("viewer-1", frozenset({"viewer"}), frozenset({"ZONE-B"}))
SECURITY = Principal("security-1", frozenset({"security_operator"}), frozenset({"ZONE-B"}))
SAFETY = Principal("safety-1", frozenset({"safety_operator"}), frozenset({"ZONE-A"}))

def test_missing_principal_denied():
    assert not allowed(None, Permission.INCIDENT_READ)

def test_viewer_cannot_read_sensitive_properties():
    assert allowed(VIEWER, Permission.GRAPH_READ, "ZONE-B")
    assert not allowed(VIEWER, Permission.SSH_DETAIL, "ZONE-B")
    assert not allowed(VIEWER, Permission.PERSON_DETAIL, "ZONE-B")

def test_domain_permissions():
    assert allowed(SECURITY, Permission.SSH_DETAIL, "ZONE-B")
    assert not allowed(SECURITY, Permission.PERSON_DETAIL, "ZONE-B")
    assert allowed(SAFETY, Permission.CAMERA_DETAIL, "ZONE-A")
    assert not allowed(SAFETY, Permission.SSH_DETAIL, "ZONE-A")

def test_zone_scope_denies_cross_zone():
    assert not allowed(SECURITY, Permission.SSH_DETAIL, "ZONE-A")
    assert not allowed(SAFETY, Permission.CAMERA_DETAIL, "ZONE-B")

def test_unknown_role_denied():
    forged = Principal("x", frozenset({"superuser"}), frozenset({"ZONE-B"}))
    assert not allowed(forged, Permission.INCIDENT_READ)

def test_require_raises():
    with pytest.raises(PermissionError):
        require(VIEWER, Permission.SSH_DETAIL, "ZONE-B")

def test_no_role_has_implicit_scenario_execution():
    for role in ("viewer","security_operator","safety_operator","operations_engineer"):
        principal = Principal("x", frozenset({role}), frozenset({"ZONE-B"}))
        assert not allowed(principal, Permission.SCENARIO_EXECUTE, "ZONE-B")
