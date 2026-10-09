"""Protected metadata references for approved retained image observations."""
import json
import sqlite3
from presentation.backend.app.incident_store import _db_path

def connect():
    path=_db_path()
    path.parent.mkdir(parents=True,exist_ok=True)
    conn=sqlite3.connect(path,timeout=15)
    conn.execute("""CREATE TABLE IF NOT EXISTS image_observation_metadata(
      observation_id TEXT PRIMARY KEY,kind TEXT NOT NULL,zone_id TEXT NOT NULL,
      metadata_json TEXT NOT NULL,graph_json TEXT NOT NULL)""")
    return conn

def save(kind,observation_id,zone_id,metadata,graph):
    if kind not in ("ppe","face") or metadata["zone_id"]!=zone_id:
        raise ValueError("Invalid image metadata scope")
    with connect() as db:
        db.execute("""INSERT INTO image_observation_metadata VALUES (?,?,?,?,?)
          ON CONFLICT(observation_id) DO UPDATE SET
          metadata_json=excluded.metadata_json,graph_json=excluded.graph_json""",
          (observation_id,kind,zone_id,json.dumps(metadata),json.dumps(graph)))

def get(kind,observation_id,zone_id):
    with connect() as db:
        row=db.execute("""SELECT metadata_json,graph_json FROM image_observation_metadata
          WHERE kind=? AND observation_id=? AND zone_id=?""",
          (kind,observation_id,zone_id)).fetchone()
    return {"capture_metadata":json.loads(row[0]),"graph_projection":json.loads(row[1])} if row else None
