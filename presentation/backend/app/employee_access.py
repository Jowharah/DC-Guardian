"""Administrator-only access directory for the controlled synthetic Neo4j topology.

No biometric enrollment or face-model data is changed. All grants and revocations
are recorded in the same Neo4j transaction as the relationship mutation.
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Literal
from reasoning.graph.ingest_event import create_driver, NEO4J_DATABASE
from presentation.backend.app.authentication import current_principal, authorize
from presentation.backend.app.authorization import Principal, Permission

router = APIRouter()
PERSON_PATTERN = r"^P[0-9]{3,8}$"
ZONE_PATTERN = r"^ZONE-[A-Z0-9_-]{1,30}$"

class EmployeeCreate(BaseModel):
    person_id: str = Field(pattern=PERSON_PATTERN)
    role: str = Field(min_length=1, max_length=64, pattern=r"^[A-Z][A-Z0-9_]*$")

class AccessChange(BaseModel):
    zone_id: str = Field(pattern=ZONE_PATTERN)
    action: Literal["GRANT", "REVOKE"]

def require_admin(principal):
    authorize(principal, Permission.PERSON_DETAIL)
    if "administrator" not in principal.roles:
        raise HTTPException(403, "Administrator role required")

def _read(tx):
    return [dict(r) for r in tx.run("""
        MATCH (p:Person)
        OPTIONAL MATCH (p)-[:AUTHORIZED_FOR]->(z:Zone)
        RETURN p.person_id AS person_id, p.role AS role,
               [zone IN collect(DISTINCT z.zone_id) WHERE zone IS NOT NULL] AS authorized_zones
        ORDER BY person_id LIMIT 200
    """)]

def _create(tx, pid, role, actor, timestamp):
    if tx.run("MATCH (p:Person {person_id:$pid}) RETURN p.person_id AS id", pid=pid).single():
        return "EXISTS"
    tx.run("""
        CREATE (p:Person {person_id:$pid, role:$role})
        CREATE (:AccessAudit {person_id:$pid, action:'REGISTER', actor:$actor, timestamp:$timestamp})
    """, pid=pid, role=role, actor=actor, timestamp=timestamp).consume()
    return "CREATED"

def _change(tx, pid, zone, action, actor, timestamp):
    person = tx.run("MATCH (p:Person {person_id:$pid}) RETURN p.person_id AS id", pid=pid).single()
    target = tx.run("MATCH (z:Zone {zone_id:$zone}) RETURN z.zone_id AS id", zone=zone).single()
    if not person or not target:
        return "MISSING"
    existing = tx.run("""
        MATCH (p:Person {person_id:$pid}), (z:Zone {zone_id:$zone})
        OPTIONAL MATCH (p)-[r:AUTHORIZED_FOR]->(z)
        RETURN count(r)>0 AS linked
    """, pid=pid, zone=zone).single()["linked"]
    if (action == "GRANT" and existing) or (action == "REVOKE" and not existing):
        return "UNCHANGED"
    if action == "GRANT":
        tx.run("""
            MATCH (p:Person {person_id:$pid}), (z:Zone {zone_id:$zone})
            MERGE (p)-[:AUTHORIZED_FOR]->(z)
        """, pid=pid, zone=zone).consume()
    else:
        tx.run("""
            MATCH (p:Person {person_id:$pid})-[r:AUTHORIZED_FOR]->(z:Zone {zone_id:$zone})
            DELETE r
        """, pid=pid, zone=zone).consume()
    tx.run("""
        CREATE (:AccessAudit {person_id:$pid, zone_id:$zone,
               action:$action, actor:$actor, timestamp:$timestamp})
    """, pid=pid, zone=zone, action=action, actor=actor, timestamp=timestamp).consume()
    return "UPDATED"

@router.get("/api/v1/access/employees")
def employees(principal: Principal = Depends(current_principal)):
    require_admin(principal)
    try:
        driver = create_driver()
        try:
            with driver.session(database=NEO4J_DATABASE, default_access_mode="READ") as session:
                return session.execute_read(_read)
        finally:
            driver.close()
    except Exception as exc:
        raise HTTPException(503, "Employee directory unavailable") from exc

@router.post("/api/v1/access/employees")
def register(payload: EmployeeCreate, principal: Principal = Depends(current_principal)):
    require_admin(principal)
    try:
        driver = create_driver()
        try:
            with driver.session(database=NEO4J_DATABASE) as session:
                result = session.execute_write(_create, payload.person_id, payload.role,
                                               principal.subject, datetime.now(timezone.utc).isoformat())
        finally:
            driver.close()
    except Exception as exc:
        raise HTTPException(503, "Employee registration unavailable") from exc
    if result == "EXISTS":
        raise HTTPException(409, "Employee already exists")
    return {"status": result, "person_id": payload.person_id}

@router.post("/api/v1/access/employees/{person_id}/zones")
def change_access(person_id: str, payload: AccessChange, principal: Principal = Depends(current_principal)):
    require_admin(principal)
    if not __import__("re").fullmatch(PERSON_PATTERN, person_id):
        raise HTTPException(422, "Invalid employee ID")
    authorize(principal, Permission.PERSON_DETAIL, payload.zone_id)
    try:
        driver = create_driver()
        try:
            with driver.session(database=NEO4J_DATABASE) as session:
                result = session.execute_write(_change, person_id, payload.zone_id, payload.action,
                                               principal.subject, datetime.now(timezone.utc).isoformat())
        finally:
            driver.close()
    except Exception as exc:
        raise HTTPException(503, "Access update unavailable") from exc
    if result == "MISSING":
        raise HTTPException(404, "Employee or zone not found")
    return {"status": result, "person_id": person_id, "zone_id": payload.zone_id, "action": payload.action}
