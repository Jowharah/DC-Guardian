"""Deny-by-default Presentation authorization policy.

Pure policy functions only: not an authentication system. Never accept roles
from request JSON, query parameters or unverified headers.
"""
from dataclasses import dataclass
from enum import StrEnum

class Permission(StrEnum):
    INCIDENT_READ = "incident:read"
    GRAPH_READ = "graph:read"
    SSH_DETAIL = "ssh:detail"
    PERSON_DETAIL = "person:detail"
    CAMERA_DETAIL = "camera:detail"
    MAINTENANCE_DETAIL = "maintenance:detail"
    ENVIRONMENT_DETAIL = "environment:detail"
    SCENARIO_EXECUTE = "scenario:execute"

ROLE_PERMISSIONS = {
    "viewer": frozenset({Permission.INCIDENT_READ, Permission.GRAPH_READ}),
    "security_operator": frozenset({Permission.INCIDENT_READ, Permission.GRAPH_READ, Permission.SSH_DETAIL}),
    "safety_operator": frozenset({Permission.INCIDENT_READ, Permission.GRAPH_READ, Permission.PERSON_DETAIL, Permission.CAMERA_DETAIL}),
    "operations_engineer": frozenset({Permission.INCIDENT_READ, Permission.GRAPH_READ, Permission.MAINTENANCE_DETAIL, Permission.ENVIRONMENT_DETAIL}),
    "administrator": frozenset(Permission),
}

@dataclass(frozen=True)
class Principal:
    subject: str
    roles: frozenset[str]
    zones: frozenset[str]

def allowed(principal: Principal | None, permission: Permission, zone: str | None = None) -> bool:
    if principal is None or not principal.subject or not principal.roles:
        return False
    if not principal.roles.issubset(ROLE_PERMISSIONS):
        return False
    granted = frozenset().union(*(ROLE_PERMISSIONS[role] for role in principal.roles))
    if permission not in granted:
        return False
    if zone is not None and zone not in principal.zones:
        return False
    return True

def require(principal: Principal | None, permission: Permission, zone: str | None = None) -> None:
    if not allowed(principal, permission, zone):
        raise PermissionError("Access denied")
