"""One-click SSH orchestration preserves per-stage outcomes."""
import asyncio
from io import BytesIO
from fastapi import HTTPException, UploadFile
from presentation.backend.app import ssh_log_validation as workflow
from presentation.backend.app import ssh_publication as publication
from presentation.backend.app.authorization import Principal

def test_one_click_processes_detector_assessment(monkeypatch):
    principal=Principal("operator",frozenset({"administrator"}),frozenset({"ZONE-B"}))
    async def fake_validate(log,zone_id,server_id,principal):
        return {"preview_id":"SSH-PREVIEW-TEST","assessments":[{"source_ip":"192.0.2.1"}],
                "parsed_count":1,"assessment_count":1,"security_relevant_count":1}
    monkeypatch.setattr(workflow,"validate_ssh_log",fake_validate)
    monkeypatch.setattr(publication,"publish",lambda payload,principal:{"published_event_ids":["SSH-EVT-TEST"]})
    monkeypatch.setattr(publication,"ingest_graph",lambda eid,p:{"graph_event_id":eid+"-MAPPED"})
    monkeypatch.setattr(publication,"check_correlation",lambda eid,p:{"status":"NO_CORRELATION","correlation_count":0})
    monkeypatch.setattr(publication,"standalone_decision",lambda eid,p:{
        "decision":{"severity":"MEDIUM","incident_status":"REVIEW_REQUIRED"},
        "specialist":{"grounding_status":"SUPPORTED"}})
    result=asyncio.run(workflow.process_ssh_log(UploadFile(filename="test.log",file=BytesIO(b"test")),
        "ZONE-B","SRV-B1-01",True,principal))
    assert result["published"] is True
    assert result["events"][0]["status"]=="DECISION_COMPLETE"
    assert result["events"][0]["decision"]["severity"]=="MEDIUM"

def test_one_click_reports_partial_graph_failure(monkeypatch):
    principal=Principal("operator",frozenset({"administrator"}),frozenset({"ZONE-B"}))
    async def fake_validate(log,zone_id,server_id,principal):
        return {"preview_id":"SSH-PREVIEW-TEST","assessments":[{}]}
    monkeypatch.setattr(workflow,"validate_ssh_log",fake_validate)
    monkeypatch.setattr(publication,"publish",lambda payload,principal:{"published_event_ids":["SSH-EVT-TEST"]})
    def graph_failure(eid,p):
        raise HTTPException(503,"Neo4j unavailable")
    monkeypatch.setattr(publication,"ingest_graph",graph_failure)
    result=asyncio.run(workflow.process_ssh_log(UploadFile(filename="test.log",file=BytesIO(b"test")),
        "ZONE-B","SRV-B1-01",True,principal))
    assert result["events"][0]["status"]=="PARTIAL"
    assert result["events"][0]["stages"][-1]["stage"]=="NEO4J"
