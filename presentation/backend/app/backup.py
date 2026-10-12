"""Backup and restore check for the operator's local data (operations routine, 2026-10-12).

    python -m presentation.backend.app.backup create  --out-dir E:\\dcg-backups [--state <ingestion_state.sqlite3>]
    python -m presentation.backend.app.backup verify  --backup E:\\dcg-backups\\dcg-backup-<time>

`create` writes one timestamped folder OUTSIDE presentation/backend/data containing:
- presentation.sqlite3: a consistent copy of the live database made with SQLite's
  online backup API (safe while the backend runs);
- the ingestion state database when given (same method);
- ppe_images/ and face_images/ (retained Evidence images; private data);
- graph.jsonl: a read-only export of every Neo4j node and relationship (labels,
  properties, element IDs), for inspection and manual recovery;
- manifest.json: SHA-256 of every file, row counts per table, the audit chains'
  head hashes (an audit checkpoint of the copy).

`verify` checks the manifest hashes, runs SQLite's integrity check on the copies
and verifies every audit hash chain inside the copied database, i.e. that the
backup could be restored. It never touches the live data.

Restore (manual, with the backend and ingestion stopped): copy presentation.sqlite3
back to presentation/backend/data/incidents.sqlite3 (keep the current file aside
first) and the image folders beside it. For a full Neo4j restore, prefer
`neo4j-admin database dump` / `load` with Neo4j stopped; graph.jsonl is the
fallback record. Backups contain private Evidence: store them encrypted and
never in the repository.
"""
import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from presentation.backend.app.incident_store import _db_path

VERSION = "DCG-BACKUP-v1"


def default_dir(sub):
    """<DCG_BACKUP_DIR>/<sub> when the operator has set a backup folder, else None."""
    from presentation.backend.app.authentication import local_setting
    base = local_setting("DCG_BACKUP_DIR")
    return str(Path(base) / sub) if base else None


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def sqlite_copy(source, target):
    with sqlite3.connect(source) as src, sqlite3.connect(target) as dst:
        src.backup(dst)


def table_counts(path):
    with sqlite3.connect(path) as db:
        tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        # nosec B608: table names come from sqlite_master of the copy, quoted.
        return {t: db.execute('SELECT count(*) FROM "' + t.replace('"', '""') + '"').fetchone()[0] for t in sorted(tables)}  # nosec B608


def export_graph(target):
    """Read-only export of the whole graph; returns (nodes, relationships) or None if Neo4j is down."""
    try:
        from reasoning.graph.ingest_event import NEO4J_DATABASE, create_driver
        driver = create_driver()
    except Exception:  # noqa: BLE001 - backup continues without the graph, and says so
        return None
    nodes = rels = 0
    try:
        with driver.session(database=NEO4J_DATABASE, default_access_mode="READ") as session, \
                open(target, "w", encoding="utf-8") as out:
            for record in session.run("MATCH (n) RETURN elementId(n) AS id, labels(n) AS labels, properties(n) AS props"):
                out.write(json.dumps({"type": "node", "id": record["id"], "labels": record["labels"],
                                      "properties": record["props"]}, default=str) + "\n")
                nodes += 1
            for record in session.run("MATCH (a)-[r]->(b) RETURN elementId(r) AS id, type(r) AS type, "
                                      "elementId(a) AS start, elementId(b) AS end, properties(r) AS props"):
                out.write(json.dumps({"type": "relationship", "id": record["id"], "rel_type": record["type"],
                                      "start": record["start"], "end": record["end"],
                                      "properties": record["props"]}, default=str) + "\n")
                rels += 1
    finally:
        driver.close()
    return nodes, rels


def chain_heads(db_path):
    """Verify each audit chain inside a database file, on a scratch copy.

    The store helpers create missing tables when they connect, so they never
    open the backup itself: its recorded hash must stay valid.
    """
    import tempfile
    from presentation.backend.app import audit_checkpoint
    scratch = Path(tempfile.mkdtemp(prefix="dcg-backup-check-")) / "copy.sqlite3"
    sqlite_copy(db_path, scratch)
    previous = os.environ.get("DCG_PRESENTATION_DB")
    os.environ["DCG_PRESENTATION_DB"] = str(scratch)
    try:
        from presentation.backend.app.review_integrity import verify_records
        result = {}
        for name, (connect, table, fields) in audit_checkpoint.chains().items():
            check = verify_records(audit_checkpoint.chain_rows(connect, table, fields), fields)
            result[name] = {"status": check["status"], "length": check["checked"],
                            "head_hash": check.get("head_hash"), "reason": check.get("reason")}
        return result
    finally:
        if previous is None:
            os.environ.pop("DCG_PRESENTATION_DB", None)
        else:
            os.environ["DCG_PRESENTATION_DB"] = previous
        shutil.rmtree(scratch.parent, ignore_errors=True)


def create(out_dir, state=None, include_graph=True):
    live = Path(_db_path()).resolve()
    out = Path(out_dir).resolve()
    if out == live.parent or live.parent in out.parents:
        raise ValueError("Write backups outside the data folder")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    folder = out / f"dcg-backup-{stamp}"
    folder.mkdir(parents=True)
    sqlite_copy(live, folder / "presentation.sqlite3")
    if state:
        sqlite_copy(Path(state), folder / "ingestion_state.sqlite3")
    for images in ("ppe_images", "face_images"):
        if (live.parent / images).exists():
            shutil.copytree(live.parent / images, folder / images)
    graph = export_graph(folder / "graph.jsonl") if include_graph else None
    files = {p.relative_to(folder).as_posix(): sha256(p) for p in sorted(folder.rglob("*")) if p.is_file()}
    manifest = {"version": VERSION, "created_at": datetime.now(timezone.utc).isoformat(),
                "source_database": str(live), "files": files,
                "tables": table_counts(folder / "presentation.sqlite3"),
                "graph": {"nodes": graph[0], "relationships": graph[1]} if graph else "NOT_EXPORTED (Neo4j unreachable or skipped)",
                "audit_chains": chain_heads(folder / "presentation.sqlite3")}
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return folder, manifest


def verify(folder):
    folder = Path(folder)
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    problems = []
    for rel, digest in manifest["files"].items():
        path = folder / rel
        if not path.exists():
            problems.append(f"missing {rel}")
        elif sha256(path) != digest:
            problems.append(f"changed {rel}")
    for name in ("presentation.sqlite3", "ingestion_state.sqlite3"):
        if (folder / name).exists():
            with sqlite3.connect(folder / name) as db:
                if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    problems.append(f"SQLite integrity check failed: {name}")
    chains = chain_heads(folder / "presentation.sqlite3")
    for name, result in chains.items():
        if result["status"] != "PASS":
            problems.append(f"audit chain {name}: {result['reason']}")
    return {"status": "PASS" if not problems else "FAILED", "problems": problems,
            "created_at": manifest["created_at"], "audit_chains": chains}


def main(argv=None):
    parser = argparse.ArgumentParser(description="DC-GUARDIAN local backup and restore check")
    sub = parser.add_subparsers(dest="command", required=True)
    c = sub.add_parser("create")
    c.add_argument("--out-dir", default=default_dir("backups"),
                   help="default: <DCG_BACKUP_DIR>/backups")
    c.add_argument("--state", help="ingestion_state.sqlite3 to include")
    c.add_argument("--no-graph", action="store_true", help="skip the Neo4j export")
    v = sub.add_parser("verify")
    v.add_argument("--backup", required=True)
    args = parser.parse_args(argv)
    if args.command == "create":
        if not args.out_dir:
            parser.error("give --out-dir or set DCG_BACKUP_DIR")
        folder, manifest = create(args.out_dir, args.state, not args.no_graph)
        print(f"Backup written: {folder}")
        print(json.dumps({"tables": len(manifest["tables"]), "graph": manifest["graph"],
                          "audit_chains": {k: v["status"] for k, v in manifest["audit_chains"].items()}}, indent=2))
        return 0
    report = verify(args.backup)
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
