import asyncio
from unittest.mock import AsyncMock
from presentation.backend.app import continuous_ingestion as ingestion
from presentation.backend.app.authorization import Principal

principal=Principal("operator",frozenset({"administrator"}),frozenset({"ZONE-B"}))
src={"kind":"ssh","zone_id":"ZONE-B","server_id":"SRV-B1-01"}

def run(monkeypatch,response):
    from presentation.backend.app import ssh_log_validation
    monkeypatch.setattr(ssh_log_validation,"process_ssh_log",AsyncMock(return_value=response))
    return asyncio.run(ingestion.dispatch(src,b"sample","ssh.log",principal))

def test_normal_log_is_processed_not_published(monkeypatch):
    result=run(monkeypatch,{"events":[],"parsed_count":10,"assessment_count":2,"security_relevant_count":0})
    assert result["processing_outcome"]=="PROCESSED_NO_ANOMALY"
    assert result["events"]==0 and result["partial"]==0

def test_published_evidence_without_decision(monkeypatch):
    result=run(monkeypatch,{"events":[{"status":"CORRELATED_REVIEW_REQUIRED"}],"security_relevant_count":1})
    assert result["processing_outcome"]=="EVIDENCE_PUBLISHED"

def test_completed_decision(monkeypatch):
    result=run(monkeypatch,{"events":[{"status":"DECISION_COMPLETE"}],"security_relevant_count":1})
    assert result["processing_outcome"]=="DECISION_COMPLETE"

def test_partial_failure_not_reported_as_complete(monkeypatch):
    result=run(monkeypatch,{"events":[{"status":"PARTIAL"}],"security_relevant_count":1})
    assert result["processing_outcome"]=="PARTIAL"
    assert result["partial"]==1
