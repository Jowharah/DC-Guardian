"""Opt-in local face observations. Biometric images are never published statically."""
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import json
import os
import sqlite3
from presentation.backend.app.incident_store import _db_path

def _root():
    return _db_path().parent / "face_images"

def _connect():
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.execute("""CREATE TABLE IF NOT EXISTS face_observations (
        observation_id TEXT PRIMARY KEY, zone_id TEXT NOT NULL,
        created_at TEXT NOT NULL, owner TEXT NOT NULL, assessment TEXT NOT NULL)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS face_image_access (
        timestamp TEXT NOT NULL, observation_id TEXT NOT NULL, subject TEXT NOT NULL)""")
    return conn

def save(image, assessment, zone, owner):
    oid = "FACE-IMG-" + uuid4().hex.upper()
    root = _root()
    root.mkdir(parents=True, exist_ok=True)
    target = root / (oid + ".png")
    image.save(target, format="PNG")
    try:
        if os.name != "nt":
            target.chmod(0o600)
        created = datetime.now(timezone.utc).isoformat()
        with _connect() as conn:
            conn.execute("INSERT INTO face_observations VALUES (?,?,?,?,?)",
                         (oid, zone, created, owner, json.dumps(assessment, allow_nan=False)))
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return {"observation_id": oid, "zone_id": zone, "created_at": created,
            "recognition_status": assessment["recognition_status"], "person_id": assessment.get("person_id"),
            "review_status": "NOT_REVIEWED", "pipeline_status": "FACE_ONLY_NOT_INTEGRATED"}

def list_items(zones):
    with _connect() as conn:
        rows = conn.execute("SELECT observation_id,zone_id,created_at,assessment FROM face_observations ORDER BY created_at DESC LIMIT 100").fetchall()
    return [{**{"observation_id": i, "zone_id": z, "created_at": t,
                 "review_status": "NOT_REVIEWED", "pipeline_status": "FACE_ONLY_NOT_INTEGRATED"},
             **{k: json.loads(a).get(k) for k in ("recognition_status", "person_id")}}
            for i,z,t,a in rows if z in zones]

def get(oid):
    with _connect() as conn:
        row = conn.execute("SELECT zone_id,created_at,assessment FROM face_observations WHERE observation_id=?", (oid,)).fetchone()
    if not row:
        return None
    z,t,a = row
    return {"observation_id": oid, "zone_id": z, "created_at": t,
            "assessment": json.loads(a), "review_status": "NOT_REVIEWED",
            "pipeline_status": "FACE_ONLY_NOT_INTEGRATED"}

def image_bytes(oid, subject):
    data = (_root() / (oid + ".png")).read_bytes()
    with _connect() as conn:
        conn.execute("INSERT INTO face_image_access VALUES (?,?,?)",
                     (datetime.now(timezone.utc).isoformat(), oid, subject))
    return data
