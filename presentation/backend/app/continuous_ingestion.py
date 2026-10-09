"""Opt-in local file ingestion for the three existing Evidence workflows.

Runs as a separate CLI process, not inside FastAPI. No filesystem watching
threads are started by importing this module. Source files are never deleted.
Only explicitly configured folders, zone and infrastructure identifiers are used.
"""
import argparse
import asyncio
import hashlib
import json
import logging
import os
import sqlite3
import time
from io import BytesIO
from pathlib import Path
from fastapi import UploadFile
from starlette.datastructures import Headers
from presentation.backend.app.authentication import local_setting
from presentation.backend.app.authorization import Principal,Permission,require

LOG=logging.getLogger("dcg.ingestion")
KINDS={"ssh":(".log",".txt"),"maintenance":(".csv",),"environment":(".csv",),
       "ppe":(".jpg",".jpeg",".png"),"face":(".jpg",".jpeg",".png")}
MAX_SIZE={"ssh":1024*1024,"maintenance":4*1024*1024,"environment":1024*1024,"ppe":8*1024*1024,"face":8*1024*1024}

def load_config(path):
    cfg=json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(cfg.get("sources"),list) or not cfg["sources"]:
        raise ValueError("Configuration requires nonempty sources list")
    sources=[]
    for src in cfg["sources"]:
        kind=src["kind"]
        if kind not in KINDS: raise ValueError("Unsupported ingestion kind")
        folder=Path(src["directory"]).expanduser().resolve(strict=True)
        if not folder.is_dir(): raise ValueError("Source must be a directory")
        zone=src["zone_id"]
        from presentation.backend.app.custom_scenarios import topology_options
        topology=next((z for z in topology_options() if z["zone_id"]==zone),None)
        if topology is None: raise ValueError("Unknown zone")
        field="sensor_id" if kind=="environment" else "server_id"
        choices="sensors" if kind=="environment" else "servers"
        if kind in ("ppe","face"):
            if src.get("retain_approved_images") is not True:
                raise ValueError("Image ingestion requires explicit retain_approved_images=true consent")
            sources.append({"kind":kind,"directory":folder,"zone_id":zone,
                            "retain_approved_images":True})
        else:
            if src[field] not in topology[choices]: raise ValueError("Invalid topology assignment")
            sources.append({"kind":kind,"directory":folder,"zone_id":zone,field:src[field]})
    return sources

def operator():
    user=local_setting("DCG_LOCAL_USER")
    role=local_setting("DCG_LOCAL_ROLE")
    zones=frozenset(x.strip() for x in local_setting("DCG_LOCAL_ZONES").split(",") if x.strip())
    if not user or not role or not zones: raise ValueError("Configured operator identity required")
    return Principal(user,frozenset({role}),zones)

def state_db(path):
    db=sqlite3.connect(path,timeout=15)
    db.execute("""CREATE TABLE IF NOT EXISTS ingested_files(
       source TEXT NOT NULL,sha256 TEXT NOT NULL,status TEXT NOT NULL,
       detail TEXT NOT NULL,processed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
       PRIMARY KEY(source,sha256))""")
    return db

async def dispatch(src,data,filename,principal,metadata=None):
    kind=src["kind"]
    image_type="image/png" if filename.lower().endswith(".png") else "image/jpeg"
    headers=Headers({"content-type":image_type}) if kind in ("ppe","face") else Headers()
    file=UploadFile(file=BytesIO(data),filename=filename,headers=headers)
    if kind=="ppe":
        from presentation.backend.app.ppe_image_validation import validate_ppe_image
        result=await validate_ppe_image(file,True,src["zone_id"],principal)
        observation=result.get("observation")
        if not observation or not result.get("image_stored"):
            raise RuntimeError("PPE image assessment was not retained")
        output={"events":1,"partial":0,"observation_id":observation["observation_id"],"pipeline_status":result["pipeline_status"]}
        if metadata:
            from presentation.backend.app.image_evidence_mapping import project_observation
            output["graph"]=project_observation("ppe",observation["observation_id"],result["assessment"],metadata)
        return output
    if kind=="face":
        from presentation.backend.app.face_image_validation import validate_face
        result=await validate_face(file,True,src["zone_id"],principal)
        observation=result.get("observation")
        if not observation or not result.get("image_stored"):
            raise RuntimeError("Face image assessment was not retained")
        output={"events":1,"partial":0,"observation_id":observation["observation_id"],"pipeline_status":result["pipeline_status"]}
        if metadata:
            from presentation.backend.app.image_evidence_mapping import project_observation
            output["graph"]=project_observation("face",observation["observation_id"],result["assessment"],metadata)
        return output
    if kind=="ssh":
        from presentation.backend.app.ssh_log_validation import process_ssh_log
        result=await process_ssh_log(file,src["zone_id"],src["server_id"],True,principal)
        events=result["events"]
        return {"events":len(events),"partial":sum(x["status"]=="PARTIAL" for x in events)}
    if kind=="maintenance":
        from presentation.backend.app.maintenance_workflow import validate
        result=await validate(file,src["zone_id"],src["server_id"],True,principal)
        return {"events":1 if result["published"] else 0,"partial":0}
    from presentation.backend.app.environment_workflow import validate
    result=await validate(file,src["zone_id"],src["sensor_id"],True,principal)
    return {"events":len(result["events"]),"partial":0}

async def scan_once(sources,db,principal):
    counts={"processed":0,"skipped":0,"failed":0,"partial":0}
    for src in sources:
        kind=src["kind"]
        perm={"ssh":Permission.SSH_DETAIL,"maintenance":Permission.MAINTENANCE_DETAIL,
              "environment":Permission.ENVIRONMENT_DETAIL,
              "ppe":Permission.CAMERA_DETAIL,"face":Permission.PERSON_DETAIL}[kind]
        require(principal,perm,src["zone_id"])
        require(principal,Permission.SCENARIO_EXECUTE,src["zone_id"])
        for path in sorted(src["directory"].iterdir()):
            if path.is_symlink() or not path.is_file() or path.suffix.lower() not in KINDS[kind]:
                continue
            # Only stable snapshots: do not process files currently being written.
            stat=path.stat()
            if stat.st_size==0 or stat.st_size>MAX_SIZE[kind] or time.time()-stat.st_mtime<5:
                continue
            data=path.read_bytes()
            if len(data)!=stat.st_size or path.stat().st_mtime_ns!=stat.st_mtime_ns:
                continue
            metadata=None
            if kind in ("ppe","face"):
                sidecar=path.with_suffix(path.suffix+".metadata.json")
                if sidecar.is_file() and not sidecar.is_symlink() and sidecar.stat().st_size<=4096:
                    from presentation.backend.app.image_evidence_mapping import validate_metadata
                    try:
                        metadata=validate_metadata(json.loads(sidecar.read_text(encoding="utf-8")),src["zone_id"])
                    except (ValueError,TypeError,json.JSONDecodeError):
                        counts["failed"]+=1
                        LOG.warning("Invalid image metadata: %s",path.name)
                        continue
            key=str(path.resolve())
            digest=hashlib.sha256(data+(json.dumps(metadata,sort_keys=True).encode() if metadata else b'')).hexdigest()
            if db.execute("SELECT 1 FROM ingested_files WHERE source=? AND sha256=? AND status IN ('COMPLETE','PARTIAL')",
                          (key,digest)).fetchone():
                counts["skipped"]+=1
                continue
            try:
                output=await dispatch(src,data,path.name,principal,metadata)
                status="PARTIAL" if output["partial"] else "COMPLETE"
                counts["partial" if status=="PARTIAL" else "processed"]+=1
                detail=json.dumps(output)
            except Exception as exc:
                status="FAILED"
                counts["failed"]+=1
                detail=type(exc).__name__
                LOG.exception("Ingestion failed: %s",path.name)
            with db:
                db.execute("""INSERT INTO ingested_files(source,sha256,status,detail)
                   VALUES (?,?,?,?) ON CONFLICT(source,sha256) DO UPDATE SET
                   status=excluded.status,detail=excluded.detail,processed_at=CURRENT_TIMESTAMP""",
                   (key,digest,status,detail))
            LOG.info("%s: %s",path.name,status)
    return counts

def main():
    parser=argparse.ArgumentParser(description="DC-Guardian opt-in local ingestion")
    parser.add_argument("--config",required=True)
    parser.add_argument("--state",default="presentation/backend/data/ingestion_state.sqlite3")
    parser.add_argument("--interval",type=int,default=0,
                        help="Polling seconds; 0 processes one batch then exits")
    args=parser.parse_args()
    if args.interval and args.interval<10: parser.error("Interval must be >=10 seconds")
    logging.basicConfig(level=logging.INFO)
    sources=load_config(args.config)
    principal=operator()
    state=Path(args.state);state.parent.mkdir(parents=True,exist_ok=True)
    with state_db(state) as db:
        while True:
            print(json.dumps(asyncio.run(scan_once(sources,db,principal))))
            if not args.interval:break
            time.sleep(args.interval)

if __name__=="__main__":
    main()
