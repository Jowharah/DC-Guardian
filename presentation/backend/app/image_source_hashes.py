"""Private SHA-256 linkage for approved images; hashes are not exposed publicly."""
import sqlite3
from presentation.backend.app.incident_store import _db_path

def connect():
    path=_db_path()
    path.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(path,timeout=15)
    db.execute("""CREATE TABLE IF NOT EXISTS image_source_hashes(
      observation_id TEXT PRIMARY KEY,kind TEXT NOT NULL,zone_id TEXT NOT NULL,
      source_sha256 TEXT NOT NULL)""")
    return db

def save(kind,observation_id,zone,sha):
    if kind not in ("ppe","face") or len(sha)!=64 or any(c not in "0123456789abcdef" for c in sha):
        raise ValueError("Invalid source hash contract")
    with connect() as db:
        db.execute("""INSERT INTO image_source_hashes VALUES (?,?,?,?)
          ON CONFLICT(observation_id) DO UPDATE SET source_sha256=excluded.source_sha256""",
          (observation_id,kind,zone,sha))

def pairs(zones):
    with connect() as db:
        rows=db.execute("""SELECT observation_id,kind,zone_id,source_sha256
          FROM image_source_hashes ORDER BY observation_id""").fetchall()
    grouped={}
    for oid,kind,zone,sha in rows:
        if zone not in zones:continue
        grouped.setdefault((zone,sha),{}).setdefault(kind,[]).append(oid)
    return [(zone,sha,groups["ppe"][0],groups["face"][0])
            for (zone,sha),groups in grouped.items()
            if "ppe" in groups and "face" in groups]
