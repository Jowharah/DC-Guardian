"""Controlled LOCAL TEST Evidence reset; never a general-purpose Neo4j wipe.

Stop API and ingestion before running. Dry-run by default. The SQLite DB is
backed up before changes. Only explicitly identified Evidence Event IDs are
removed from Neo4j; topology, enrollment, and approved RAG remain untouched.
"""
import argparse
import json
import os
import shutil
import sqlite3
from datetime import datetime,timezone
from pathlib import Path
from presentation.backend.app.incident_store import _db_path

TABLES=("incidents","standalone_events","ssh_validation_previews","ssh_published_evidence","ssh_decisions",
        "maintenance_evidence","environmental_batches","environmental_evidence",
        "ppe_observations","face_observations","ppe_image_access","face_image_access",
        "image_observation_metadata","image_source_hashes",
        "physical_specialist_results","operational_decisions")

def tables(conn):
    return {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}

def event_ids(conn):
    existing=tables(conn);ids=set()
    if "ssh_published_evidence" in existing:
        ids.update(r[0]+"-MAPPED" for r in conn.execute("SELECT event_id FROM ssh_published_evidence"))
    if "maintenance_evidence" in existing:
        for (raw,) in conn.execute("SELECT workflow_json FROM maintenance_evidence"):
            try:
                eid=json.loads(raw).get("graph_event_id")
                if eid:ids.add(eid)
            except (ValueError,TypeError):pass
    for table in ("environmental_batches","environmental_evidence"):
        if table not in existing:continue
        if table=="environmental_batches":
            for (raw,) in conn.execute("SELECT event_ids_json FROM environmental_batches"):
                try:ids.update(x+"-MAPPED" for x in json.loads(raw) if x.startswith("ENV-EVT-"))
                except (ValueError,TypeError):pass
        else:
            ids.update(r[0]+"-MAPPED" for r in conn.execute("SELECT event_id FROM environmental_evidence"))
    for table in ("ppe_observations","face_observations"):
        if table in existing:
            ids.update("IMG-EVT-"+r[0] for r in conn.execute("SELECT observation_id FROM "+table))
    return sorted(ids)

def inventory(db_path,state_path):
    result={"presentation_db":str(db_path),"ingestion_state":str(state_path),
            "tables":{},"mapped_event_ids":[],"image_files":[]}
    if db_path.is_file():
        with sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro",uri=True) as conn:
            existing=tables(conn)
            result["tables"]={name:conn.execute("SELECT COUNT(*) FROM "+name).fetchone()[0]
                              for name in TABLES if name in existing}
            result["mapped_event_ids"]=event_ids(conn)
    for folder in ("ppe_images","face_images"):
        root=db_path.parent/folder
        if root.is_dir():
            result["image_files"].extend(str(p) for p in root.glob("*.png") if p.is_file() and not p.is_symlink())
    return result

def backup_database(src,target):
    if not src.is_file():return
    with sqlite3.connect(str(src)) as source,sqlite3.connect(str(target)) as dest:
        source.backup(dest)

def reset(args):
    db_path=_db_path().resolve()
    state_path=Path(args.state).expanduser().resolve()
    if db_path==state_path:raise ValueError("Presentation and ingestion state must be separate databases")
    if args.execute and os.environ.get("DCG_ALLOW_LOCAL_TEST_RESET")!="YES":
        raise ValueError("Set DCG_ALLOW_LOCAL_TEST_RESET=YES only for disposable local test data")
    report=inventory(db_path,state_path)
    report["mode"]="DRY_RUN" if not args.execute else "EXECUTE"
    print(json.dumps({k:v for k,v in report.items() if k!="image_files"},indent=2))
    print("Retained image files:",len(report["image_files"]))
    if not args.execute:return
    if not args.confirm or args.confirm!="RESET-LOCAL-TEST-EVIDENCE":
        raise ValueError("Explicit --confirm RESET-LOCAL-TEST-EVIDENCE required")
    if not db_path.is_file():raise ValueError("Presentation database not found")
    backup=Path(args.backup_dir).expanduser().resolve()
    if backup==db_path.parent or backup==state_path.parent:
        raise ValueError("Use a dedicated backup directory, not an active data directory")
    backup.mkdir(parents=True,exist_ok=False)
    backup_database(db_path,backup/db_path.name)
    backup_database(state_path,backup/state_path.name)
    for folder in ("ppe_images","face_images"):
        root=db_path.parent/folder
        if root.is_dir():shutil.copytree(root,backup/folder,symlinks=False)
    (backup/"reset_manifest.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print("Backups created:",backup)
    # Delete only graph Event nodes with IDs derived from locally stored Evidence.
    # Abort before SQLite changes if Neo4j is unavailable or a graph write fails.
    from reasoning.graph.ingest_event import create_driver,NEO4J_DATABASE
    driver=create_driver()
    try:
        with driver.session(database=NEO4J_DATABASE) as session:
            ids=report["mapped_event_ids"]
            if ids:
                session.run("""MATCH (e:Event) WHERE e.event_id IN $ids
                    DETACH DELETE e""",ids=ids).consume()
    finally:driver.close()
    with sqlite3.connect(str(db_path)) as conn:
        existing=tables(conn)
        for table in TABLES:
            if table in existing:conn.execute("DELETE FROM "+table)
    if state_path.is_file():
        with sqlite3.connect(str(state_path)) as conn:
            if "ingested_files" in tables(conn):
                conn.execute("DELETE FROM ingested_files")
    for filename in report["image_files"]:
        Path(filename).unlink()
    print("Local test Evidence reset complete. Source incoming files were preserved.")
    print("Backup:",backup)

def main():
    parser=argparse.ArgumentParser(description="Dry-run-first local test Evidence reset")
    parser.add_argument("--state",required=True,help="Path to ingestion_state.sqlite3")
    parser.add_argument("--execute",action="store_true")
    parser.add_argument("--confirm",default="")
    parser.add_argument("--backup-dir",default="")
    args=parser.parse_args()
    if args.execute and not args.backup_dir:parser.error("--backup-dir required for execute")
    reset(args)

if __name__=="__main__":main()
