"""Prototype PPE image observations, separate from pipeline-derived incidents.

Local-only, RBAC-protected, opt-in retention. Do not store real employee images.
"""
from __future__ import annotations
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from uuid import uuid4
import json
import os
import sqlite3
from PIL import Image
from presentation.backend.app.incident_store import _db_path

def _image_root() -> Path:
    return _db_path().parent / "ppe_images"

def _connect():
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.execute("""CREATE TABLE IF NOT EXISTS ppe_observations (
        observation_id TEXT PRIMARY KEY, zone_id TEXT NOT NULL,
        created_at TEXT NOT NULL, owner TEXT NOT NULL, assessment TEXT NOT NULL
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS ppe_image_access (
        timestamp TEXT NOT NULL, observation_id TEXT NOT NULL, subject TEXT NOT NULL
    )""")
    return conn

def save_observation(image: Image.Image, assessment: dict, zone: str, owner: str) -> dict:
    observation_id = "PPE-IMG-" + uuid4().hex.upper()
    root = _image_root()
    root.mkdir(parents=True, exist_ok=True)
    filename = root / (observation_id + ".png")
    # Images are intentionally outside any static web directory.
    image.save(filename, format="PNG")
    try:
        if os.name != "nt":
            filename.chmod(0o600)
        created = datetime.now(timezone.utc).isoformat()
        with _connect() as conn:
            conn.execute("INSERT INTO ppe_observations VALUES (?,?,?,?,?)",
                         (observation_id, zone, created, owner, json.dumps(assessment, allow_nan=False)))
    except Exception:
        filename.unlink(missing_ok=True)
        raise
    return {"observation_id": observation_id, "zone_id": zone, "created_at": created,
            "status": assessment["overall_status"], "person_count": assessment["person_count"],
            "detections": assessment.get("detections", []), "source_type": "OPERATOR_UPLOADED_IMAGE",
            "pipeline_status": "PPE_ONLY_NOT_INTEGRATED", "review_status": "NOT_REVIEWED"}

def list_observations(zones: frozenset[str]) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute("SELECT observation_id,zone_id,created_at,assessment FROM ppe_observations ORDER BY created_at DESC LIMIT 100").fetchall()
    return [{"observation_id": i, "zone_id": z, "created_at": t,
             "status": json.loads(a)["overall_status"], "person_count": json.loads(a)["person_count"],
             "source_type": "OPERATOR_UPLOADED_IMAGE", "pipeline_status": "PPE_ONLY_NOT_INTEGRATED",
             "review_status": "NOT_REVIEWED"} for i,z,t,a in rows if z in zones]

def get_observation(observation_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT zone_id,created_at,assessment FROM ppe_observations WHERE observation_id=?", (observation_id,)).fetchone()
    if row is None:
        return None
    zone, created, assessment = row
    return {"observation_id": observation_id, "zone_id": zone, "created_at": created,
            "assessment": json.loads(assessment), "pipeline_status": "PPE_ONLY_NOT_INTEGRATED",
            "review_status": "NOT_REVIEWED"}

def image_bytes(observation_id: str, subject: str) -> bytes:
    path = _image_root() / (observation_id + ".png")
    data = path.read_bytes()
    with _connect() as conn:
        conn.execute("INSERT INTO ppe_image_access VALUES (?,?,?)",
                     (datetime.now(timezone.utc).isoformat(), observation_id, subject))
    return data
