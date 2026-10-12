import json
import sqlite3
from presentation.backend.app.dev_reset import event_ids,inventory

def test_event_ids_from_stored_evidence():
    db=sqlite3.connect(":memory:")
    db.execute("CREATE TABLE ssh_published_evidence(event_id TEXT)")
    db.execute("INSERT INTO ssh_published_evidence VALUES ('SSH-EVT-ONE')")
    db.execute("CREATE TABLE maintenance_evidence(workflow_json TEXT)")
    db.execute("INSERT INTO maintenance_evidence VALUES (?)",(json.dumps({"graph_event_id":"MAINT-EVT-ONE-MAPPED"}),))
    db.execute("CREATE TABLE environmental_batches(event_ids_json TEXT)")
    db.execute("INSERT INTO environmental_batches VALUES (?)",(json.dumps(["ENV-EVT-ONE"]),))
    db.execute("CREATE TABLE face_observations(observation_id TEXT)")
    db.execute("INSERT INTO face_observations VALUES ('FACE-IMG-ONE')")
    assert event_ids(db)==sorted(["SSH-EVT-ONE-MAPPED","MAINT-EVT-ONE-MAPPED",
                                  "ENV-EVT-ONE-MAPPED","IMG-EVT-FACE-IMG-ONE"])

def test_inventory_does_not_modify_database(tmp_path):
    path=tmp_path/"presentation.sqlite3"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE ppe_observations(observation_id TEXT)")
        db.execute("INSERT INTO ppe_observations VALUES ('PPE-IMG-ONE')")
    report=inventory(path,tmp_path/"state.sqlite3")
    assert report["tables"]["ppe_observations"]==1
    assert report["mapped_event_ids"]==["IMG-EVT-PPE-IMG-ONE"]
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT COUNT(*) FROM ppe_observations").fetchone()[0]==1


def test_reset_covers_every_presentation_table():
    """A new feature table must be added to TABLES (or deliberately excluded)."""
    import sqlite3 as _sqlite3
    from presentation.backend.app import dev_reset
    from presentation.backend.app.main import app  # noqa: F401  creates nothing by itself
    from presentation.backend.app.incident_store import _db_path
    # Exercise every store so its CREATE TABLE IF NOT EXISTS runs in the test DB.
    from presentation.backend.app import (evidence_review, decision_reevaluation, human_review_audit,
        investigator_history, unified_specialists, operational_decision, ssh_publication,
        maintenance_workflow, environment_workflow, image_metadata_store, image_source_hashes,
        ssh_temporal_context, face_observations, ppe_observations)
    evidence_review.connect().close(); decision_reevaluation.storage().close()
    human_review_audit.connect().close(); investigator_history.connect().close()
    unified_specialists.storage().close(); operational_decision.storage().close()
    ssh_publication.connect().close(); maintenance_workflow.db().close(); environment_workflow.db().close()
    image_metadata_store.connect().close(); image_source_hashes.connect().close()
    ssh_temporal_context.context_db().close(); face_observations._connect().close(); ppe_observations._connect().close()
    from presentation.backend.app import single_specialists, investigator_audit; single_specialists.storage().close(); investigator_audit.connect().close()
    from presentation.backend.app import investigation_lifecycle; investigation_lifecycle.connect().close()
    with _sqlite3.connect(_db_path()) as db:
        existing={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert existing - set(dev_reset.TABLES) == set(), existing - set(dev_reset.TABLES)

def test_graph_cleanup_never_targets_topology_or_people():
    from presentation.backend.app.dev_reset import GRAPH_CLEANUP
    text=" ".join(match for _,match in GRAPH_CLEANUP)
    for protected in ("Zone","Rack","Server","Camera","Sensor","Person","AccessAudit","DataCenter"):
        assert f":{protected}" not in text.replace("(:Event)","")
