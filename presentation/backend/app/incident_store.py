"""Local SQLite persistence for validated, browser-safe synthetic incident summaries.

Prototype only: no authentication, encryption-at-rest, or multi-tenant isolation.
Raw images, usernames, IP addresses and biometric artifacts are not persisted here.
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from threading import RLock
from datetime import datetime, timezone
from presentation.backend.app.schemas import IncidentView

DEFAULT_DB = Path(__file__).resolve().parents[1] / "data" / "incidents.sqlite3"
_lock = RLock()

def _db_path() -> Path:
    return Path(os.environ.get("DCG_PRESENTATION_DB", str(DEFAULT_DB)))

def _connect() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.execute("""CREATE TABLE IF NOT EXISTS incidents (
        scenario_id TEXT PRIMARY KEY,
        created_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
        payload TEXT NOT NULL
    )""")
    return conn

def remember(incident: IncidentView) -> IncidentView:
    if incident.received_at is None:
        incident = incident.model_copy(update={"received_at": datetime.now(timezone.utc)})
    with _lock, _connect() as conn:
        conn.execute(
            "INSERT INTO incidents (scenario_id,payload) VALUES (?,?) "
            "ON CONFLICT(scenario_id) DO UPDATE SET payload=excluded.payload",
            (incident.scenario_id, incident.model_dump_json()),
        )
    return incident

def list_incidents() -> list[IncidentView]:
    with _lock, _connect() as conn:
        rows = conn.execute(
            "SELECT payload, created_utc FROM incidents ORDER BY created_utc DESC, rowid DESC LIMIT 200"
        ).fetchall()
    return [_restore(row[0], row[1]) for row in rows]

def get_incident(scenario_id: str) -> IncidentView | None:
    with _lock, _connect() as conn:
        row = conn.execute(
            "SELECT payload, created_utc FROM incidents WHERE scenario_id=?", (scenario_id,)
        ).fetchone()
    return _restore(row[0], row[1]) if row else None

def _restore(payload: str, created_utc: str) -> IncidentView:
    incident = IncidentView.model_validate_json(payload)
    if incident.received_at is None:
        # Legacy records were created before received_at was part of the API contract.
        incident = incident.model_copy(update={"received_at": datetime.fromisoformat(created_utc.replace("Z", "+00:00"))})
    return incident
